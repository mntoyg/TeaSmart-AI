# Project state

**Read this before anything else.** It says where the work is, not how it got
here. Whoever finishes a slice updates this file in the same push.

- **Last updated:** 2026-10-19 (D3 and the frontend both on `main`)
- **Demo deadline:** 2026-10-22 — three days
- **Open branch:** none. PR #5 (frontend) and PR #6 (model, repository
  structure) are both merged.
- **Next slice:** D4 lesion analyser (burn vs disease), then D5
  `POST /api/v1/scan`. **Nothing renders end to end until D5 exists**: the
  frontend's `parseScan` requires `burn_analysis`, `severity` and `advice`.
- **Ownership:** by directory, in `docs/DESIGN.md` section 14. Claude Code has
  `backend/` and `ml/`; Codex has `frontend/`.
- **Daily usage ceilings:** Every AI: at most 14% of its own weekly capacity per day

## Done

| day | slice | evidence |
|---|---|---|
| D1 | Backend foundation: `/health`, `/api/v1/kb`, hardened image decoding, stage-1 quality gate | 40 tests, merged in `mntoyg/TeaSmart-AI#1` |
| D2 (PR #4) | Dataset pipeline: source registry, ingest, pixel-exact dedup, stratified manifest, `prepare` CLI | 74 tests, `docs/EVIDENCE.md` section 1 |
| D3 (PR #6) | Classifier: training, evaluation, measured `min_confidence`, ONNX export with parity | 120 ml tests, test macro-F1 **0.9873**, `docs/EVIDENCE.md` section 2 |
| D6/D7 (PR #5) | Frontend: scan UI, Thai result cards, PWA shell, on-device ONNX worker, offline queue | 47 Vitest, `docs/EVIDENCE.md` section 3. **D7 is not certified**: parity, live endpoints and a demo phone are still owed |
| — (PR #6) | Repository: CI, `scripts/setup` and `scripts/test`, `pyproject.toml`, ruff clean, docs down to three files | `./scripts/test.sh` ends in `All green.` |

**Corpus on disk:** 11,853 images ingested from three credential-free sources,
deduplicated to **8,316** across five classes, split 70/15/15, with **0**
cross-split duplicate pairs verified in pixel terms over every pair. Rebuild
with `cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare`.

## Next: D4 — burn versus disease

The feature the product exists for, and the only one no dataset can help with.
Rule-based CV on the lesion, in `backend/app/services/`:

- leaf segmentation, then lesion mask
- features: edge sharpness, concentric rings, acervuli, affinity to the leaf
  edge, colour zonation (spec section 7, stage 4)
- severity as affected area percentage, banded mild / moderate / severe
- synthetic fixtures for both cases, because there are no real burn photographs

Its headline metric is **specificity on confirmed-disease images**: of the 1,245
test images whose class is a disease, how many does the analyser wrongly call
physical burn. Burn accuracy cannot be measured at all without burn images, and
claiming a number for it would be inventing one.

D3 left this behind for it: the classifier is right 98.7% of the time but can be
wrong at 0.983 confidence, so the analyser is independent evidence about the
same leaf rather than a second opinion from the same source.

## Model artifacts, on disk and in git

- checkpoint: `data/artifacts/teasmart-v1.pt` — **gitignored**, rebuild with
  `python -m teasmart_ml.cli train` (15 epochs, about 35 minutes on the 3050)
- browser graph: `frontend/public/models/teasmart-v1.onnx` — **committed**
  (16.8 MB) so a fresh checkout can run the demo without a GPU
- `frontend/public/models/teasmart-v1-int8.onnx` — **not committed on purpose.**
  It fails the parity bound. If it is on your disk, delete it.

## Then

| day | slice |
|---|---|
| D4 | leaf segmentation, lesion analyser (burn vs disease), severity, synthetic fixtures |
| D5 | expert system wiring, `/api/v1/scan` end to end, downscale after decode |
| D6 | frontend scan UI, camera capture, Thai result cards |
| D7 | PWA offline, on-device ONNX, history, sync endpoint |
| ~~D8~~ | ~~Capacitor `.apk`~~ — **cut 2026-10-19.** PWA installed from Chrome demos the same thing; the time goes to D4. |
| D9 | demo data, pitch script, buffer |

## Contract changes (read if you own either side)

**2026-10-13 — spec section 8 rewritten.** Codex asked for the parts a client
cannot be written without, and it was right that they were missing. Now pinned:

- `POST /api/v1/scan` multipart field name is **`image`**, plus optional
  `scan_id` and `captured_at`
- `POST /api/v1/sync/batch` request and per-item response, with items and files
  matched by `scan_id` rather than by position
- `scan_id` is the idempotency key; the server cache is in-memory and does not
  survive a restart, so the client must dedupe locally too
- ONNX preprocessing, input and output names, class order, and the parity test
  that has to pass before D7 is done
- the browser does not segment, so an on-device result is `classifier_only` and
  genuinely differs from a server result

**2026-10-13 — `GET /api/v1/config` added** (44 backend tests). Codex pointed out
that `min_confidence` was specified but did not exist. It does now, at **0.60
provisionally**, and rather than confirming a number for the frontend to copy,
the backend serves every constant both sides share: the confidence floor, the
class order (derived from the knowledge base, not listed again), the ONNX
preprocessing, and the quality thresholds the browser duplicates. Read them from
the endpoint; do not hard-code them.

**2026-10-19 — `min_confidence` measured, and the ONNX file renamed.** Two
contract changes, both from D3:

1. **`min_confidence` stays 0.60, now measured rather than provisional.** The
   criterion D3 was given (0.90 accuracy among accepted) returns 0.20 against a
   model at 0.987, which would switch the `other_disease` safety net off
   entirely. Specifying that criterion was the mistake, not the measurement. The
   operative criterion is 0.99 accuracy among accepted: 0.55 on validation, 0.63
   on test, so 0.60 sits between them and declines 0.72% of photographs.
2. **The browser loads `teasmart-v1.onnx` (fp32, 16.8 MB), not
   `teasmart-v1-int8.onnx`.** Int8 agreed on top-1 for all 50 parity images but
   moved a probability by 0.248 against a bound of 0.05. Top-1 agreement is not
   the acceptance test because the product thresholds on the probability.

Both are served from `GET /api/v1/config`, so a client that reads the endpoint
needed no change. Evidence: `docs/EVIDENCE.md` section 2.

Still open: `Settings` does not yet carry `max_batch_items`, `max_batch_bytes`
or `idempotency_cache_size`. They land with D5, when the endpoints do.

## Open decisions for the user

1. **`max_image_pixels` is 40,000,000.** A 738 KB JPEG decodes to 7000×5600 and
   peaks at 235 MB — real amplification on the only untrusted door, with rate
   limiting still to come on D5. Lowering the cap would reject a 48 MP phone
   photo outright, so the intended fix is to downscale immediately after decode,
   alongside the scan endpoint. Not yet done.
2. **Kaggle ×2 and the gated HuggingFace source are disabled** for want of
   credentials. Three sources were enough; enabling the others is a flag plus a
   token.
3. **32 photographs are labelled differently by two sources** and are dropped
   rather than guessed. Reviewing them by hand would recover real training data.

## Things that are true and easy to get wrong

- **0.987 test accuracy is an upper bound on field accuracy, not an estimate.**
  The split is random within each class and is not grouped by photography
  session: several shots of the same leaf can land on both sides. D2 removed
  pixel duplicates, which is a different thing.
- **The classifier can be confidently wrong.** One test image is wrong at 0.983,
  above any usable floor. No screen may present a result as certain.
- **A DataLoader with `num_workers > 0` needs an `if __name__ == "__main__"`
  guard** in any script that uses it. Windows spawns workers by re-importing the
  file, and without the guard the re-import starts more workers until the
  process wedges. `teasmart_ml.cli` has the guard; a quick script will not.

- **No burn images exist in any dataset.** Burn detection is rule-based CV and
  its headline metric is specificity on confirmed-disease images.
- **`other_disease` is deliberate.** It lets the model decline to name a disease
  it was never shown.
- **The manifest `path` column is relative to the interim root**, not absolute
  and not relative to the repository.
- **A duplicate is defined by pixels** (32×32 greyscale MAE ≤ 8.0), not by a
  perceptual hash. The hash is an audit column. The reason this matters is in
  `docs/DESIGN.md` section 13.
- **`data/interim/` needs its `.teasmart-interim` marker file** before the
  pipeline will clear anything inside it.
## Frontend team handoff — 2026-10-19

- D2 merged to main in PR #4. D3-D5 delivery is still pending: no trained model,
  scan endpoint or sync endpoint has been delivered in the tracked source.
- D6 UI and D7 infrastructure are consolidated into root `frontend/` on
  `codex/team-onboarding`. PR #2 remains open and PR #3 remains draft; this
  integration branch includes their existing commits for a single team checkout.
- Previously measured frontend evidence: 47 Vitest tests, contract check and PWA
  build; see `docs/eval/2026-10-13-frontend-validation.md`.
- Team entrypoint: `frontend/README.md`; project map: `docs/PROJECT_STRUCTURE.md`.
- D7 is incomplete until the actual model, 50-image parity check, live API/sync
  integration and demo-phone checks pass. No fabricated diagnosis is shipped.
- Historical `.superpowers/worktrees/d6` and `d7` checkouts remain intact.
  Team members work in normal `frontend/` after checking out the team branch;
  do not copy source files between worktrees.
- Usage check at return: 11% weekly consumed; daily usage is unavailable. Use a
  conservative allowance of at most 3 additional percentage points this run.
- Fresh verification from root `frontend/` on 2026-10-19: 47 tests passed,
  contract test passed (1/1), PWA build passed with 11 precache entries. The
  existing VitePWA inlineDynamicImports deprecation warning is still present.
- Latest usage reading this run: 13% weekly consumed, up from 11%; daily usage
  remains unknown. Stop after the committed/pushed onboarding boundary.
