import 'fake-indexeddb/auto';
import { openDB } from 'idb';
import { expect, it, vi } from 'vitest';

vi.mock('./local-result', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./local-result')>();
  return { ...actual, parseStored: (value: unknown) => ({
    ...actual.parseStored(value), parsed_by_test: true,
  }) as unknown as ReturnType<typeof actual.parseStored> };
});

import { createStore } from './storage';
import { localFixture } from '../test/local-fixture';
import { scanFixture } from '../test/fixtures';
import { parseStored } from './local-result';

it('persists the normalized result from save, enqueue, and applyBatch', async () => {
  const name = `normalized-${crypto.randomUUID()}`;
  const saved = scanFixture({ scan_id: crypto.randomUUID() });
  const queued = localFixture(crypto.randomUUID());
  const batched = scanFixture({ scan_id: crypto.randomUUID() });
  expect(parseStored(saved)).toHaveProperty('parsed_by_test', true);
  const store = createStore(name);
  await store.save(saved);
  await store.enqueue(new Blob(['image']), queued);
  await store.applyBatch([batched], []);

  const database = await openDB(name);
  for (const scanId of [saved.scan_id, queued.scan_id, batched.scan_id]) {
    const persisted = await database.get('scans', scanId) as unknown as Record<string, unknown>;
    expect(persisted.parsed_by_test, String([saved.scan_id, queued.scan_id, batched.scan_id].indexOf(scanId))).toBe(true);
  }
  database.close();
  await store.close();
});
