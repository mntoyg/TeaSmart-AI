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
D7 model inference, offline shell and replay are separate work. Do not describe
this D6 build as an offline scanner. Real-camera behavior must also be checked on
the demo phone before release; unit tests simulate browser permission handling.
