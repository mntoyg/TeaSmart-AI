import 'fake-indexeddb/auto';
import { expect, it } from 'vitest';
import { createStore } from './storage';
import { scanFixture } from '../test/fixtures';

it('persists results across reopening and deduplicates retries by scan_id', async () => {
  const name = `test-${crypto.randomUUID()}`;
  const first = createStore(name);
  await first.save(scanFixture());
  await first.save(scanFixture({ processing_ms: 99 }));
  await first.close();
  const second = createStore(name);
  expect(await second.list()).toHaveLength(1);
  expect((await second.get(scanFixture().scan_id))?.processing_ms).toBe(99);
  await second.close();
});
it('refuses invalid persisted diagnoses rather than showing misleading advice', async () => {
  const store = createStore(`test-${crypto.randomUUID()}`);
  await expect(store.save({ ...scanFixture(), severity: undefined } as never)).rejects.toThrow('ผลวิเคราะห์');
  expect(await store.list()).toEqual([]);
  await store.close();
});
