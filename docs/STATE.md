# Project state

- **Last updated:** 2026-10-13
- **Demo deadline:** 2026-10-22
- **Claude Code:** D2 dataset pipeline finished on `feat/d2-dataset-pipeline`;
  D3 model training is next. See that branch's dataset report and handoff.
- **Codex:** D6 in progress on `feat/d6-scan-ui` in a separate worktree.
  Frontend foundation and spec-generated scan response types are ready.
- **Daily ceilings:** Claude Code 15%, Codex 13.5% of weekly capacity.
  Codex session baseline: 19% consumed weekly; 81% remains.

## Done

| slice | evidence |
|---|---|
| D1 backend foundation | 40 tests, merged PR #1 |
| D2 dataset pipeline (Claude branch, awaiting human merge) | 74 tests, 8,316 deduplicated images |
| D6 frontend foundation | Contract test observed red before generator; production build checked |

## Next

Codex: D6 camera/file scan flow, Thai result cards, history and KB routes.
Use section 8 unchanged. Server scan endpoint is not implemented yet.

Claude Code: D3 training, then D4 segmentation/lesion/severity and D5 scan API.
The model target remains `frontend/public/models/teasmart-v1-int8.onnx`.

## Integration questions before D7

- Section 8 lists `/api/v1/sync/batch` but has no batch request/response or
  idempotency schema. Claude Code and Codex must agree before queue replay.
- Confirm ONNX normalization, resize/crop policy and low-confidence semantics.
  Shape alone (`[1,3,224,224]` to `[1,5]`) cannot establish numerical parity.
- Confirm scan multipart field name and supported verdict/severity values.
  D6 can render the published sample and preserve unknown values safely.

## Remaining

D6 UI; D7 offline shell, model/KB caching, ONNX inference, IndexedDB and sync;
D8 Capacitor; D9 demo validation. Burn is rule-based, never a trained class.
