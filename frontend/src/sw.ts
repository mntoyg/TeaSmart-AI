/// <reference lib="webworker" />
import { clientsClaim } from 'workbox-core';
import { precacheAndRoute, createHandlerBoundToURL } from 'workbox-precaching';
import { NavigationRoute, registerRoute } from 'workbox-routing';
import { CacheFirst } from 'workbox-strategies';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { parseConfig, parseKnowledge } from './lib/api';
declare const self: ServiceWorkerGlobalScope & { __WB_MANIFEST: { url: string; revision: string | null }[] };
const resourceCache = 'teasmart-resources-v1';
precacheAndRoute(self.__WB_MANIFEST);
clientsClaim();
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html'), { denylist: [/^\/api\//] }));
async function cacheResource(path: string, validate: (value: unknown) => unknown) {
  const cache = await caches.open(resourceCache);
  try {
    const response = await fetch(path, { signal: AbortSignal.timeout(10_000) });
    if (!response.ok) throw new Error('Resource unavailable');
    validate(await response.clone().json());
    await cache.put(path, response.clone());
    return response;
  } catch {
    const cached = await cache.match(path);
    return cached ?? new Response('{}', { status: 503, headers: { 'Content-Type': 'application/json' } });
  }
}
self.addEventListener('install', (event) => event.waitUntil(Promise.all([
  cacheResource('/api/v1/config', parseConfig), cacheResource('/api/v1/kb', parseKnowledge),
])));
registerRoute(({ url }) => url.pathname === '/api/v1/config', () => cacheResource('/api/v1/config', parseConfig));
registerRoute(({ url }) => url.pathname === '/api/v1/kb', () => cacheResource('/api/v1/kb', parseKnowledge));
registerRoute(({ url }) => url.origin === self.location.origin && /^\/models\/teasmart-[a-z0-9-]+\.onnx$/.test(url.pathname),
  new CacheFirst({ cacheName: 'teasmart-models-v1', plugins: [new CacheableResponsePlugin({ statuses: [200] })] }));
// POST scans and sync batches are deliberately never cached by this worker.
