import 'fake-indexeddb/auto';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import { store } from './lib/storage';
import { scanFixture } from './test/fixtures';
import { configShape } from './lib/scan-contract';
import { localFixture } from './test/local-fixture';
import { inferOffline, isOfflineReady } from './lib/offline';
vi.mock('./lib/offline', () => ({ inferOffline: vi.fn(), prepareOffline: vi.fn(), isOfflineReady: vi.fn(async () => false) }));

it('says offline is prepared after a reload that found the model still cached', async () => {
  await store.saveConfig(configShape);
  vi.mocked(isOfflineReady).mockResolvedValue(true);
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);
  expect(await screen.findByText(/เตรียมออฟไลน์แล้ว/)).toBeInTheDocument();
  expect(screen.queryByText('ยังไม่ได้เตรียมใช้งานออฟไลน์')).not.toBeInTheDocument();
  vi.mocked(isOfflineReady).mockResolvedValue(false);
  vi.unstubAllGlobals();
});

it('loads a persisted result by its URL after refresh', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  await store.save(scanFixture());
  render(<MemoryRouter initialEntries={[`/result/${scanFixture().scan_id}`]}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'โรคใบไหม้เทา' })).toBeInTheDocument();
  vi.unstubAllGlobals();
});
it('replays a newly queued scan when connectivity returned before inference completed', async () => {
  await store.saveConfig(configShape);
  vi.mocked(inferOffline).mockImplementation(async (_file, id, at) => ({ ...localFixture(id), captured_at: at }));
  const requests = vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
    if (url === '/api/v1/sync/batch') {
      const items = JSON.parse((init.body as FormData).get('items') as string);
      return new Response(JSON.stringify({ results: [scanFixture({ scan_id: items[0].scan_id, captured_at: items[0].captured_at })], failed: [] }));
    }
    throw new TypeError('Unavailable');
  });
  vi.stubGlobal('fetch', requests);
  const createUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
  const revokeUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('เลือกภาพใบชา'), { target: { files: [new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' })] } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'ประเมินบนอุปกรณ์' })).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: 'ประเมินบนอุปกรณ์' }));
  await waitFor(() => expect(requests.mock.calls.some(([url]) => url === '/api/v1/sync/batch')).toBe(true));
  createUrl.mockRestore(); revokeUrl.mockRestore(); vi.unstubAllGlobals();
});
it('offers a scan link when a result ID is absent', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/result/missing']}><App /></MemoryRouter>);
  expect(await screen.findByText('ไม่พบผลตรวจนี้ในอุปกรณ์')).toBeInTheDocument();
  expect(screen.getAllByRole('link', { name: 'ตรวจใบชา' })[0]).toHaveAttribute('href', '/scan');
  vi.unstubAllGlobals();
});
