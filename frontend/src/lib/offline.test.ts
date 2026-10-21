import { expect, it, vi } from 'vitest';
import { inferOffline, isOfflineReady } from './offline';
import { configShape } from './scan-contract';

it('derives offline readiness from the cached model, not from a button press', async () => {
  // No Cache API at all: jsdom has none, and neither does an insecure context.
  expect(await isOfflineReady(configShape)).toBe(false);
  const match = vi.fn(async (path: string) =>
    path === `/models/${configShape.onnx.file}` ? new Response('graph') : undefined);
  vi.stubGlobal('caches', { match });
  expect(await isOfflineReady(configShape)).toBe(true);
  expect(match).toHaveBeenCalledWith(`/models/${configShape.onnx.file}`);
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
