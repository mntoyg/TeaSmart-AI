# Project state

- **Last updated:** 2026-10-13
- **Demo deadline:** 2026-10-22
- **Claude Code:** D2 dataset pipeline finished on `feat/d2-dataset-pipeline`;
  D3 model training is next. See that branch's dataset report and handoff.
- **Codex:** D6 in progress on `feat/d6-scan-ui` in a separate worktree.
  Foundation, upload client, camera/file capture and Thai result cards are ready.
  Evidence: 18 Vitest tests pass; contract check and production build pass.
- **Daily ceilings:** Claude Code 15%, Codex 13.5% of weekly capacity.
  Codex session baseline: 19% consumed weekly; 81% remains.

## Done

| slice | evidence |
|---|---|
| D1 backend foundation | 40 tests, merged PR #1 |
| D2 dataset pipeline (Claude branch, awaiting human merge) | 74 tests, 8,316 deduplicated images |
| D6 frontend foundation | Contract test observed red before generator; production build checked |

## Next

Codex: D6 history and KB routes, IndexedDB persistence and browser checks.
Use section 8 unchanged. Server scan endpoint is not implemented yet.

Claude Code: D3 training, then D4 segmentation/lesion/severity and D5 scan API.
The model target remains `frontend/public/models/teasmart-v1-int8.onnx`.

## Integration contract

- User confirmed Claude Code commit `4fe7263`. The exact spec from that commit
  is included here; Codex has not changed the shared contract.
- Sections 8.1-8.4 now pin `image`, client UUID, timestamps, per-item batch sync,
  idempotency, ImageNet normalization and the required 50-image parity check.
- ONNX model and Python parity evidence still depend on D3-D5 delivery.

## Remaining

D6 UI; D7 offline shell, model/KB caching, ONNX inference, IndexedDB and sync;
D8 Capacitor; D9 demo validation. Burn is rule-based, never a trained class.
