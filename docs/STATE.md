# Project state

**Read this before anything else.** It says where the work is, not how it got
here. Whoever finishes a slice updates this file in the same push.

- **Last updated:** 2026-10-13
- **Demo deadline:** 2026-10-22
- **Open branch:** `feat/d2-dataset-pipeline` — finished and reviewed, waiting
  on a human to merge
- **Next slice:** D3, model training

## Done

| day | slice | evidence |
|---|---|---|
| D1 | Backend foundation: `/health`, `/api/v1/kb`, hardened image decoding, stage-1 quality gate | 40 tests, merged in `mntoyg/TeaSmart-AI#1` |
| D2 | Dataset pipeline: source registry, ingest, pixel-exact dedup, stratified manifest, `prepare` CLI | 74 tests, `docs/eval/2026-10-13-dataset-summary.md` |

**Corpus on disk:** 11,853 images ingested from three credential-free sources,
deduplicated to **8,316** across five classes, split 70/15/15, with **0**
cross-split duplicate pairs verified in pixel terms over every pair. Rebuild
with `cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare`.

## Next: D3 — training

Build `ml/teasmart_ml/train.py`, `transforms.py`, `evaluate.py` and
`export_onnx.py` against `data/processed/manifest.csv`.

- MobileNetV3-Large, ImageNet-pretrained, 5 outputs, 224×224, batch 32, mixed
  precision — the 4 GB card is the reason for every one of those choices
- class-balanced sampling (`other_disease` is 36% of the corpus)
- early stopping on validation macro-F1
- commit a report to `docs/eval/`: confusion matrix, per-class precision /
  recall / F1, with `other_disease` as its own row so it cannot hide misses
- export int8 ONNX and assert parity with the Python path on a fixed input set

PyTorch is **not installed yet** in `ml/.venv`. Install the CUDA build, not the
CPU wheel.

## Then

| day | slice |
|---|---|
| D4 | leaf segmentation, lesion analyser (burn vs disease), severity, synthetic fixtures |
| D5 | expert system wiring, `/api/v1/scan` end to end, ONNX int8 export |
| D6 | frontend scan UI, camera capture, Thai result cards |
| D7 | PWA offline, on-device ONNX, history, sync endpoint |
| D8 | Capacitor `.apk`, polish |
| D9 | demo data, pitch script, buffer |

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

- **No burn images exist in any dataset.** Burn detection is rule-based CV and
  its headline metric is specificity on confirmed-disease images.
- **`other_disease` is deliberate.** It lets the model decline to name a disease
  it was never shown.
- **The manifest `path` column is relative to the interim root**, not absolute
  and not relative to the repository.
- **A duplicate is defined by pixels** (32×32 greyscale MAE ≤ 8.0), not by a
  perceptual hash. The hash is an audit column. The reason this matters is in
  `docs/superpowers/decisions/2026-10-13-d2-rulings.md`.
- **`data/interim/` needs its `.teasmart-interim` marker file** before the
  pipeline will clear anything inside it.
