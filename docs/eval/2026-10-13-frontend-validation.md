# Frontend validation — 2026-10-13

D6 PR: https://github.com/mntoyg/TeaSmart-AI/pull/2
D7 draft PR: https://github.com/mntoyg/TeaSmart-AI/pull/3

## Scope and contract

D6 implements the four routes, camera/file capture, Thai retake feedback,
ordered result cards, IndexedDB history and KB presentation. D7 adds the shell,
local ONNX/WASM worker, quality gate, classifier-only presentation, image/result
queue and per-item batch replay. The spec is the exact contract confirmed by the
user in `4fe7263` and `c53d9a0`; no backend or ML code was edited.

Runtime settings are fetched from `/api/v1/config`. The source generator creates
types and structural examples from sections 8.1 and 8.5, and transport limits
from section 8. There is no runtime fallback to the example's confidence floor.

## Command evidence

From the D7 `frontend/` directory:

```text
npm test
Test Files  10 passed (10)
Tests       47 passed (47)

npm run test:contract
tests 1
pass 1
fail 0

npm run build
Scan contract matches section 8
vite v8.3.4 building client environment for production...
dist/assets/ort-wasm-simd-threaded-DcHrbrbl.wasm  14,239.89 kB
PWA v2.0.0
mode      injectManifest
format:   es
precache  11 entries (14306.59 KiB)
files generated
  dist/sw.js

npm audit --omit=dev --audit-level=high
found 0 vulnerabilities

Test-Path frontend/public/models/teasmart-v1-int8.onnx
False
```

VitePWA's service-worker build emits an `inlineDynamicImports` deprecation
warning with Vite 8. The build exits successfully; this is recorded rather than
described as a warning-free build.

## Red evidence

- Contract generator test failed before the generator existed.
- API/camera/card suites failed before those modules existed.
- Persistence, queue, inference, quality and offline tests failed before their
  implementations existed.
- Temporarily bypassing config guards produced four test failures; guards were
  restored before commit.
- Temporarily mislabelling classifier-only output as full produced a failure;
  the correct Thai label was restored before commit.
- The reconnect-before-inference-completes regression failed with a pending
  image and no replay request, then passed after the trigger was corrected.

## Browser observations

Using the Codex browser, the D6 shell was checked at desktop and 390px width.
Scan/history/KB routes rendered Thai content. The camera unit test covers denied
permission and track cleanup; real camera capture was not performed.

The D7 production preview was opened at `http://localhost:4173/scan`, then its
server was stopped. A direct HTTP request failed as expected:

```text
Preview server stopped: request failed as expected
```

Browser reload still rendered the scan shell, and navigating to history still
rendered its empty state. This verifies shell caching with the server absent.
It does not verify model inference with the device network disabled. The prepare
button correctly refused readiness when KB/config were unavailable. Screenshots
are local review artifacts, not committed private imagery.

## Required before D7 is complete

1. Supply the actual D5 ONNX file in this worktree's `frontend/public/models/`.
   Ignored model files are not copied between worktrees or included by Git.
2. Use the measured confidence floor from the live config endpoint. Confirm
   class order, input/output names and preprocessing against the exported model.
3. Execute the contract's 50-image browser/Python parity check: identical top-1,
   absolute per-class probability difference no greater than 0.05. Record whether
   Python uses the same whole-frame input; server segmentation is a separate
   difference explicitly documented in section 8.4.
4. Exercise actual scan/config/KB/sync endpoints, partial quality failures,
   reconnect replay and persistence on the demo phone, with network disabled for
   the local scan. Confirm no local card claims burn or severity analysis.
5. Package the ignored model alongside the production assets and repeat the
   preparation/reload flow with that artifact.

Merge D6 first. Combine `docs/STATE.md` with Claude Code's parallel state when
merging either PR; preserve both agents' completed work and remaining tasks.
