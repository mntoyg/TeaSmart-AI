# TeaSmart frontend

Requires Node 22.12+ and npm. From this directory:

```powershell
npm ci
npm run dev
npm run test:contract
npm test
npm run build
```

Open `http://localhost:5173/scan`. Vite proxies `/api` to
`http://127.0.0.1:8000`. Production hosting must serve the built `dist/` with a
fallback to `index.html` for client routes and forward `/api` to the backend.
Camera access requires HTTPS (or localhost). No external font or image is fetched.

Scan types are generated from design spec section 8, confirmed in `4fe7263`.
Run `npm run generate:contract` after an agreed spec update. The build rejects
stale generated types. Runtime validation treats API and stored data as untrusted.

History and the last validated KB are stored in IndexedDB. Retrying an image
preserves its UUID and timestamp. A new capture gets a new UUID. The frontend
does not infer burn or severity: the server owns those stages.

D6 is tested against fixtures because D5 `/api/v1/scan` has not landed yet.
D7 includes a service worker, local WASM assets, an ONNX Web Worker, client
quality gate, atomic image/result queue, and UUID-matched batch replay. Config is
fetched from `/api/v1/config`, validated, and cached with the KB. Thresholds,
normalization and class order are read from that document, never copied into
runtime defaults. Scan POSTs and sync POSTs are never cached.

To test the PWA, run `npm run build` then `npm run preview`. Development mode
does not register a service worker. Select **Prepare offline** while online;
the UI only reports preparation success after an actual model session loads.
Supply the model at `public/models/teasmart-v1-int8.onnx` before building. Models
are gitignored: deployment packaging must include this file separately. Models
present at build time are precached; preparing later also caches a fetched model.
All WASM, module and worker assets are bundled locally; no CDN is required.

The real D5 model is currently absent. The production app cannot issue a local
diagnosis until it is supplied. Shape-compatible stubs exist only in unit tests.
Do not call D7 complete until the required 50-image browser/Python parity check
passes, the offline scan/reconnect flow is exercised with the actual endpoints,
and real-camera behavior is checked on the demo phone.
