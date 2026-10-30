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
  fireEvent.change(screen.getByLabelText('เลือกรูปภาพ'), { target: { files: [new File(['leaf'], 'leaf.jpg', { type: 'image/jpeg' })] } });
  // There is no on-device button to press any more: the scan POST above throws,
  // which is what an estate with no route out looks like, and the page falls
  // through to the device model on its own.
  await waitFor(() => expect(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' })).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: 'เริ่มวิเคราะห์ใบชา' }));
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

it('opens the before-reading checklist and persists today\'s plan across app reloads', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  const user = userEvent.setup();
  const firstRender = render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);

  const beforeReadingTabs = await screen.findAllByRole('button', { name: 'ก่อนอ่าน' });
  await user.click(beforeReadingTabs[0]);
  expect(await screen.findByRole('heading', { name: 'เช็กก่อนอ่านผล' })).toBeInTheDocument();
  await user.click(screen.getByLabelText('แสงธรรมชาติ มองสีแผลชัด'));
  await user.click(screen.getByLabelText('มีหลายใบและเห็นแผลชัด'));
  await user.click(screen.getByLabelText('มากกว่า 20 นาที'));
  await user.click(screen.getByLabelText('แยกได้ และจะเปิดคลังความรู้เทียบถ้าสงสัย'));
  await user.click(screen.getByRole('button', { name: 'บันทึกแผนวันนี้' }));
  expect(await screen.findByText(/บันทึกวันนี้แล้ว/)).toBeInTheDocument();

  firstRender.unmount();
  render(<MemoryRouter initialEntries={['/readiness']}><App /></MemoryRouter>);
  expect(await screen.findByText(/บันทึกวันนี้แล้ว/)).toBeInTheDocument();
  vi.unstubAllGlobals();
});

it('shows the today plan card on the scan page', async () => {
  localStorage.clear();
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'วันนี้ยังไม่ได้เช็กก่อนอ่านผล' })).toBeInTheDocument();
  vi.unstubAllGlobals();
});

it('keeps offline status visible while omitting the queue area when no images are pending', async () => {
  const pending = vi.spyOn(store, 'pending').mockResolvedValue([]);
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));
  render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);

  const panel = await screen.findByRole('region', { name: 'สถานะออฟไลน์และคิว' });
  expect(within(panel).getByRole('status')).toHaveTextContent('ยังไม่ได้เตรียมใช้งานออฟไลน์');
  expect(within(panel).queryByRole('group', { name: 'ภาพที่รอส่ง' })).not.toBeInTheDocument();

  pending.mockRestore();
  vi.unstubAllGlobals();
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
  expect(screen.getByRole('group', { name: 'ภาพที่รอส่ง' })).toHaveTextContent('เก็บไว้ในอุปกรณ์แล้ว 1 ภาพ');
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

it('shows the offline and queue panel on the scan page only', async () => {
  const panel = 'สถานะออฟไลน์และคิว';
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));

  const scan = render(<MemoryRouter initialEntries={['/scan']}><App /></MemoryRouter>);
  expect(await screen.findByRole('region', { name: panel })).toBeInTheDocument();
  scan.unmount();

  const knowledge = render(<MemoryRouter initialEntries={['/kb']}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'ความรู้เรื่องใบชา' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: panel })).not.toBeInTheDocument();
  knowledge.unmount();

  const history = render(<MemoryRouter initialEntries={['/history']}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'ประวัติการตรวจ' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: panel })).not.toBeInTheDocument();
  history.unmount();

  const readiness = render(<MemoryRouter initialEntries={['/readiness']}><App /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'เช็กก่อนอ่านผล' })).toBeInTheDocument();
  expect(screen.queryByRole('region', { name: panel })).not.toBeInTheDocument();
  readiness.unmount();

  vi.unstubAllGlobals();
});
