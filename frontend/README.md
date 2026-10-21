# TeaSmart frontend

This directory is the frontend source. There is no other copy: the two
historical hidden worktrees were removed on 2026-10-20, their branches having
already been merged into `main`.

The boundary with the backend is the API contract in
[docs/DESIGN.md](../docs/DESIGN.md) section 8. Runtime constants come from
`GET /api/v1/config`; do not hard-code them.

## Source map

| path | edit here for |
|---|---|
| `src/main.tsx` | React bootstrap and service-worker registration |
| `src/App.tsx` | routes, navigation, history/KB views and offline status |
| `src/pages/ScanPage.tsx` | camera capture, image picker and retakes |
| `src/components/ResultCard.tsx` | Thai result presentation and analysis-mode label |
| `src/lib/api.ts` | validated API/config/KB boundary |
| `src/lib/storage.ts`, `src/lib/queue.ts` | IndexedDB and replay |
| `src/lib/offline.ts`, `src/lib/onnx-worker.ts` | local inference orchestration |
| `src/lib/inference.ts`, `src/lib/quality.ts` | numerical preprocessing and quality gate |
| `src/lib/scan-contract.ts` | generated types; change the agreed spec, then regenerate |
| `src/styles.css` | shared visual styles |
| `src/sw.ts` | offline caching policy |
| `src/test/`, adjacent `*.test.ts(x)` | fixtures, setup and regression coverage |
| `public/` | icons and separately delivered model assets |
| `scripts/` | contract generation/checking |

## Run and verify

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

---

# Working here as a team

Moved from `docs/FRONTEND_TEAM.md`, which no longer exists: `docs/` is three
files, and guidance about this directory belongs next to it. The clone
instructions it carried are gone because the integration branch is merged -
branch from `main`, and set up with `./scripts/setup.ps1` or `./scripts/setup.sh`
from the repository root.

## Pick a task without colliding

| task | primary files | coordinate before editing |
|---|---|---|
| scan/camera UX | `frontend/src/pages/ScanPage.tsx` | capture IDs, queue behavior |
| result cards | `frontend/src/components/ResultCard.tsx` | analysis mode and supplied advice |
| styles/accessibility | `frontend/src/styles.css`, relevant components | shared navigation/layout |
| history/knowledge views | `frontend/src/App.tsx` | routing and app coordinator changes |
| offline/sync | `frontend/src/lib/`, `frontend/src/sw.ts` | API/model contract and parity |

Call out shared files in your PR description and keep branches short. Tests live
beside the code they cover; shared fixtures are in `frontend/src/test/`.
The [frontend source map](../frontend/README.md#source-map) explains each module.

## Before opening a PR

```bash
cd frontend
npm run test:contract
npm test
npm run build
```

Or `./scripts/test.*` from the root, which runs these plus the Python suites and
the linter - the same steps CI runs, in the same order.

Write the regression test before changing behaviour and watch it fail. UI text
is Thai; code, comments, commits and documentation are English. Update
`docs/STATE.md` when a slice is done, in the same push. Every AI follows the 14%
hard daily ceiling in the root `AGENTS.md`.

## Integration boundaries

The contract in [section 8 of docs/DESIGN.md](../docs/DESIGN.md)
is shared with Claude Code's backend/ML work. Do not change it alone. API types
are generated; inference thresholds and preprocessing come from `/api/v1/config`.
Advice comes from the curated KB and must not be rewritten casually.

D6 UI and D7 infrastructure exist, but D7 is not certified complete. The real
model, 50-image Python/browser parity, live endpoint/reconnect checks and demo
phone validation are still required. A classifier-only result must never claim
that burn analysis or severity was computed. The app ships no fake model.
