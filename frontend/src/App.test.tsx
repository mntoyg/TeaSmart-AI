import 'fake-indexeddb/auto';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
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
  const message = await screen.findByText('ไม่พบผลตรวจนี้ในอุปกรณ์');
  const link = within(message.closest('section')!).getByRole('link', { name: 'ตรวจใบชา' });
  expect(link).toHaveAttribute('href', '/scan');
  expect(link).toHaveClass('button');
  vi.unstubAllGlobals();
});

it('offers a button-styled scan link when history is empty', async () => {
  const list = vi.spyOn(store, 'list').mockResolvedValue([]);
  render(<MemoryRouter initialEntries={['/history']}><App /></MemoryRouter>);
  const message = await screen.findByText('ยังไม่มีประวัติการตรวจใบชา');
  const link = within(message.closest('section')!).getByRole('link', { name: 'ตรวจใบชา' });
  expect(link).toHaveAttribute('href', '/scan');
  expect(link).toHaveClass('button');
  list.mockRestore();
});

it('keeps the local queue visible without offering a pointless retry on the static demo', async () => {
  await store.saveConfig(configShape);
  const id = crypto.randomUUID();
  await store.enqueue(new Blob(['leaf']), localFixture(id));
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => {
    if (url === '/api/v1/sync/batch') return new Response('{}', { status: 404 });
    throw new TypeError('Unavailable');
  }));

  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);

  expect(await screen.findByText(/ภาพถูกเก็บไว้ในอุปกรณ์แล้ว แต่รุ่นสาธิตนี้ไม่มีเซิร์ฟเวอร์สำหรับวิเคราะห์เต็มรูปแบบ/))
    .toBeInTheDocument();
  expect(screen.getByText(/เก็บไว้ในอุปกรณ์แล้ว 1 ภาพ/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'ส่งคิวอีกครั้ง' })).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});

it('refreshes the visible queue after repeated transport failures exhaust retries', async () => {
  await store.saveConfig(configShape);
  const id = crypto.randomUUID();
  await store.enqueue(new Blob(['leaf']), localFixture(id));
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));

  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);
  await waitFor(async () => expect(await store.queueStatus(id)).toMatchObject({ attempts: 1, state: 'pending' }));
  for (const attempts of [2, 3]) {
    const retry = await screen.findByRole('button', { name: 'ส่งคิวอีกครั้ง' });
    await waitFor(() => expect(retry).toBeEnabled());
    await userEvent.click(retry);
    await waitFor(async () => expect(await store.queueStatus(id)).toMatchObject({ attempts,
      state: attempts === 3 ? 'failed' : 'pending' }));
  }
  await waitFor(() => expect(screen.queryByText(/เก็บไว้ในอุปกรณ์แล้ว/)).not.toBeInTheDocument());
  vi.unstubAllGlobals();
});

it('offers the before-reading check and daily plan from the PWA routes', async () => {
  localStorage.clear();
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);

  const readinessLink = await screen.findByRole('link', { name: 'ก่อนอ่าน' });
  expect(readinessLink).toHaveAttribute('href', '/readiness');
  await userEvent.click(readinessLink);
  expect(await screen.findByRole('heading', { name: 'เช็กก่อนอ่านผล' })).toBeInTheDocument();

  for (const label of [
    'แสงธรรมชาติ มองสีแผลชัด',
    'มีหลายใบและเห็นแผลชัด',
    'มากกว่า 20 นาที',
    'แยกได้ และจะเปิดคลังความรู้เทียบถ้าสงสัย',
  ]) {
    await userEvent.click(screen.getByLabelText(label));
  }
  await userEvent.click(screen.getByRole('button', { name: 'บันทึกแผนวันนี้' }));
  expect(await screen.findByText(/บันทึกวันนี้แล้ว/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: 'ไปสแกนใบชา' }));
  expect(await screen.findByRole('heading', { name: 'แผนวันนี้' })).toBeInTheDocument();
  expect(screen.getByText('ใบที่สแกนวันนี้เทียบกับแผน')).toBeInTheDocument();
  vi.unstubAllGlobals();
  localStorage.clear();
});
