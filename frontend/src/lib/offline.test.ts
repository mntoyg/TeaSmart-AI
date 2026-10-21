import { expect, it, vi } from 'vitest';
import { inferOffline, isOfflineReady } from './offline';
import { configShape } from './scan-contract';

// Keyed the way production is keyed, read off https://teasmart-ai.pages.dev on
// 2026-10-21, not the way a bare path would be. A stub that answers the bare
// path makes any implementation pass and proves nothing.
const precachedModel = (file: string) =>
  `/models/${file}?__WB_REVISION__=abaadc472a4be7dcf36e1722778b4843`;

function precacheStub(file: string) {
  const stored = precachedModel(file);
  return vi.fn(async (path: string, options?: CacheQueryOptions) => {
    if (path === stored) return new Response('graph');
    if (options?.ignoreSearch && stored.startsWith(`${path}?`)) return new Response('graph');
    return undefined;
  });
}

it('finds the precached model although workbox keys it behind a revision query', async () => {
  // No Cache API at all: jsdom has none, and neither does an insecure context.
  expect(await isOfflineReady(configShape)).toBe(false);
  const match = precacheStub(configShape.onnx.file);
  vi.stubGlobal('caches', { match });
  expect(await isOfflineReady(configShape)).toBe(true);
  // Without a config there is nothing to run the cached graph against.
  expect(await isOfflineReady(undefined)).toBe(false);
  vi.unstubAllGlobals();
});

it('reports not ready when the cache holds everything except the model', async () => {
  vi.stubGlobal('caches', { match: vi.fn(async () => undefined) });
  expect(await isOfflineReady(configShape)).toBe(false);
  vi.unstubAllGlobals();
});
it('refuses offline inference without a validated cached config', async () => {
  await expect(inferOffline(new File(['leaf'], 'leaf.jpg'), crypto.randomUUID(), new Date().toISOString(), undefined))
    .rejects.toThrow('การตั้งค่า');
});
