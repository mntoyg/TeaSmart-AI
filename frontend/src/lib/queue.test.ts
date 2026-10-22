import 'fake-indexeddb/auto';
import { expect, it, vi, afterEach } from 'vitest';
import { createStore } from './storage';
import { syncQueue, chunkQueue } from './queue';
import { localFixture } from '../test/local-fixture';
import { scanFixture } from '../test/fixtures';
import { transportLimits } from './scan-contract';
afterEach(() => vi.unstubAllGlobals());
const id = '00000000-0000-4000-8000-000000000001';

it('durably queues image and result atomically, deduplicating by capture UUID', async () => {
  const name = `queue-${crypto.randomUUID()}`;
  const first = createStore(name), result = localFixture(id);
  await first.enqueue(new Blob(['image']), result);
  await first.enqueue(new Blob(['image']), result);
  await first.close();
  const next = createStore(name);
  expect(await next.pending()).toHaveLength(1);
  expect((await next.get(id))?.analysis_mode).toBe('classifier_only');
  await next.close();
});
it('chunks by item count and total payload bytes, including multipart headroom', () => {
  const pending = Array.from({ length: 21 }, (_, index) => ({
    scan_id: String(index), result: localFixture(id), image: new Blob(['x']), state: 'pending' as const, attempts: 0,
  }));
  expect(chunkQueue(pending).map((batch) => batch.length)).toEqual([transportLimits.max_batch_items, 1]);
  const large = pending.slice(0, 5).map((item) => ({ ...item, image: new Blob([new Uint8Array(transportLimits.max_upload_bytes)]) }));
  expect(chunkQueue(large).map((batch) => batch.length)).toEqual([3, 2]);
});
it('matches returned IDs, replaces local history, and keeps per-item failures for retake', async () => {
  const repository = createStore(`queue-${crypto.randomUUID()}`);
  const rejected = '00000000-0000-4000-8000-000000000002';
  await repository.enqueue(new Blob(['first']), localFixture(id));
  await repository.enqueue(new Blob(['second']), localFixture(rejected));
  const mocked = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [scanFixture()], failed: [
    { scan_id: rejected, status: 422, detail: 'blur', detail_th: 'ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น' },
  ] })));
  vi.stubGlobal('fetch', mocked);
  await syncQueue(repository);
  const body = mocked.mock.calls[0][1].body as FormData;
  expect(JSON.parse(body.get('items') as string).map((item: {scan_id:string}) => item.scan_id)).toEqual([id, rejected]);
  expect(body.getAll('images').map((file) => (file as File).name)).toEqual([id, rejected]);
  expect(await repository.pending()).toHaveLength(0);
  expect((await repository.get(id))?.analysis_mode).toBe('full');
  expect((await repository.queueStatus(rejected))?.detail_th).toContain('ภาพเบลอ');
  expect(await repository.list()).toHaveLength(2);
  await repository.close();
});
it('applies complete results and keeps classifier-only results queued', async () => {
  const repository = createStore(`queue-${crypto.randomUUID()}`);
  const second = '00000000-0000-4000-8000-000000000003';
  const partial = '00000000-0000-4000-8000-000000000004';
  await repository.enqueue(new Blob(['first']), localFixture(id));
  await repository.enqueue(new Blob(['second']), localFixture(second));
  await repository.enqueue(new Blob(['partial']), localFixture(partial));
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [
    scanFixture({ scan_id: id }), scanFixture({ scan_id: second }),
    scanFixture({ scan_id: partial, analysis_mode: 'classifier_only' }),
  ], failed: [] }))));

  await syncQueue(repository);

  expect((await repository.get(id))?.analysis_mode).toBe('full');
  expect((await repository.get(second))?.analysis_mode).toBe('full');
  expect((await repository.get(partial))?.analysis_mode).toBe('classifier_only');
  expect((await repository.pending()).map((entry) => entry.scan_id)).toEqual([partial]);
  expect(await repository.queueStatus(partial)).toMatchObject({ attempts: 1, status: 503, state: 'pending' });
  await repository.close();
});
it('caps repeated transient server failures and records a Thai terminal message', async () => {
  const repository = createStore(`queue-${crypto.randomUUID()}`);
  const maxAttempts = 3;
  await repository.enqueue(new Blob(['image']), localFixture(id));

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    await repository.applyBatch([], [{ scan_id: id, status: 503, detail_th: 'เซิร์ฟเวอร์ขัดข้องชั่วคราว' }]);
    const status = await repository.queueStatus(id);
    expect(status?.attempts).toBe(attempt);
    if (attempt < maxAttempts) {
      expect(status?.state).toBe('pending');
      expect(await repository.pending()).toHaveLength(1);
    } else {
      expect(status?.state).toBe('failed');
      expect(status?.status).toBe(503);
      expect(status?.detail_th).toContain('ลองส่งซ้ำไม่สำเร็จ');
      expect(await repository.pending()).toHaveLength(0);
    }
  }
  await repository.close();
});
it.each(['network', 'missing', 'duplicate', 'foreign'])('keeps queued scans intact on %s outcomes', async (kind) => {
  const repository = createStore(`queue-${crypto.randomUUID()}`);
  await repository.enqueue(new Blob(['image']), localFixture(id));
  const results = kind === 'missing' ? [] : kind === 'duplicate' ? [scanFixture(), scanFixture()]
    : [scanFixture({ scan_id: 'foreign-id' })];
  vi.stubGlobal('fetch', kind === 'network' ? vi.fn().mockRejectedValue(new TypeError('Offline'))
    : vi.fn().mockResolvedValue(new Response(JSON.stringify({ results, failed: [] }))));
  await expect(syncQueue(repository)).rejects.toThrow();
  expect(await repository.pending()).toHaveLength(1);
  expect((await repository.get(id))?.analysis_mode).toBe('classifier_only');
  await repository.close();
});

it('counts transport failures and stops retrying after the shared attempt limit', async () => {
  const repository = createStore(`queue-${crypto.randomUUID()}`);
  await repository.enqueue(new Blob(['image']), localFixture(id));
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')));

  for (let attempt = 1; attempt <= 3; attempt++) {
    await expect(syncQueue(repository)).rejects.toThrow();
    const status = await repository.queueStatus(id);
    expect(status?.attempts).toBe(attempt);
    expect(status?.state).toBe(attempt < 3 ? 'pending' : 'failed');
  }
  expect(await repository.pending()).toHaveLength(0);
  expect((await repository.get(id))?.analysis_mode).toBe('classifier_only');
  await repository.close();
});
