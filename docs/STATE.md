# Project state

- **Last updated:** 2026-10-13
- **Demo deadline:** 2026-10-22
- **Claude Code:** D2 dataset pipeline finished on `feat/d2-dataset-pipeline`;
  D3 model training is next. See that branch's dataset report and handoff.
- **Codex:** D6 UI ready on `feat/d6-scan-ui` in a separate worktree.
  Four routes, camera/file capture, Thai result cards, IndexedDB history and KB.
  Evidence: 22 Vitest tests pass; contract check and production build pass;
  scan/history/KB browser smoke checks at desktop and 390px viewport.
- **D6 PR:** https://github.com/mntoyg/TeaSmart-AI/pull/2 (human merge only).
- **D7:** in progress on `feat/d7-offline`; includes D6 as a dependency.
  Preprocessing, client quality gate, durable queue and validated batch replay
  are implemented with ONNX worker and PWA shell. 47 Vitest tests, contract check
  and production build pass. D7 remains incomplete pending the actual model.
- **Daily ceilings:** Claude Code 15%, Codex 13.5% of weekly capacity.
  Codex session baseline: 19% consumed weekly; 81% remains.

## Done

| slice | evidence |
|---|---|
| D1 backend foundation | 40 tests, merged PR #1 |
| D2 dataset pipeline (Claude branch, awaiting human merge) | 74 tests, 8,316 deduplicated images |
| D6 scan UI | 22 Vitest tests and 1 contract test, production build, browser route checks |

## Next

Codex: D7 IndexedDB queue, per-item sync, offline shell and ONNX runtime wiring.
User confirmed `c53d9a0`: inference settings now come from `/api/v1/config`.
The prior defaults generator has been removed. Config types come from section 8.5.
Service-worker caches, ONNX worker and scan/replay UI integration are implemented.
Production build precaches 11 entries including local WASM (~14 MB).
Browser reload and scan/history navigation succeeded after the preview server
was stopped. A reconnect-before-inference-completes regression is covered.
D6 uses fixtures until the server
scan endpoint lands. Actual camera capture on the demo phone is still unverified.

Claude Code: D3 training, then D4 segmentation/lesion/severity and D5 scan API.
The model target remains `frontend/public/models/teasmart-v1-int8.onnx`.

## Integration contract

- User confirmed Claude Code commit `4fe7263`. The exact spec from that commit
  is included here; Codex has not changed the shared contract.
- Sections 8.1-8.4 now pin `image`, client UUID, timestamps, per-item batch sync,
  idempotency, ImageNet normalization and the required 50-image parity check.
- ONNX model and Python parity evidence still depend on D3-D5 delivery.

## Remaining

D6 live API/phone validation; D7 offline shell, model caching, ONNX inference and sync;
D8 Capacitor; D9 demo validation. Burn is rule-based, never a trained class.
