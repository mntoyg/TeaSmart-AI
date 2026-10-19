# TeaSmart AI — measured evidence

Numbers that were produced by a command, with the command. Nothing here is an
estimate; where something is unknown it says so.

| section | what it covers |
|---|---|
| 1 | the training corpus: sources, deduplication, splits |
| 2 | the classifier: training, held-out scores, `min_confidence`, ONNX parity |
| 3 | the frontend: test suites, contract check, PWA build |
| 4 | the quality gate, recalibrated against real photographs |
| 5 | burn versus disease: measured specificity, unmeasurable sensitivity |
| 6 | browser and Python preprocessing parity: the D7 gate |

---

# 1. Dataset
The corpus every accuracy figure from D3 onward is measured against. Reproduce
it with:

```bash
cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare
```

Seed `42`, stratified 70/15/15, manifest at `data/processed/manifest.csv`. Its
`path` column is relative to the interim root (`data/interim/` by default), so
the file still resolves on another machine or in a container.

## Sources

Three of the nine candidate sources need no credentials and are the only ones
enabled. Probed 2026-10-13.

| source | origin | ingested | corrupt | unlabelled | ambiguous |
|---|---|---|---|---|---|
| `agml` | HF `Project-AgML/tea_leaf_disease_classification` | 5,867 | 0 | 0 | 0 |
| `yunusserhat` | HF `yunusserhat/tea_sickness_dataset` | 885 | 0 | 0 | 0 |
| `mendeley_mz598` | Mendeley `mz598gxfw9` v1 (Roboflow YOLO export) | 5,101 | 0 | 79 | 0 |
| **total** | | **11,853** | **0** | **79** | **0** |

`agml` ingested 5,867 images matching the per-class counts its dataset card
states, which is the check that the ClassLabel order in the registry is right.

`mendeley_mz598` holds 5,180 images and 5,180 label files. 79 of those label
files are **empty** — in a Roboflow export that means a deliberate background or
negative sample, not a missing annotation — and no image lacks a label file at
all. Those 79 are skipped because a classification target cannot be derived from
them. No image in the archive is annotated with two different classes.

Not used: `mendeley_sjmy` (`sjmy6k24d6`) answers HTTP 451 and is dropped; two
Kaggle sources and the gated `ttkqwe123` need credentials and stay registered
but disabled; `mendeley_d2xy` (3.07 GB) and `mendeley_94fz` (964 MB, .rar) are
deferred extra volume.

## Deduplication

| | count |
|---|---|
| ingested | 11,853 |
| duplicate copies collapsed | 3,505 |
| cross-class conflicts dropped | 32 |
| **usable corpus** | **8,316** |

The sources overlap heavily: `agml` and `mendeley_mz598` substantially share
photographs, which is the leakage this step exists to prevent.

Each group keeps its highest-resolution copy. That is why `agml`'s healthy count
falls from 1,000 ingested to 104 in the manifest: `mendeley_mz598` holds the same
photographs at 640×640 against agml's 256×256, so the larger copies win.

A duplicate group spanning two classes is dropped rather than resolved by sort
order, because keeping either side would train the model on a label no annotator
gave. 32 groups are affected.

### What counts as a duplicate

**Two images are the same photograph when the mean absolute difference of their
32×32 greyscale thumbnails is at most 8.0 of 255.** Pixels are the definition;
no hash decides anything. `phash` remains a manifest column for auditing only.

Every pair is compared. That is made tractable by an exact lower bound rather
than by a filter that can be wrong: the mean absolute difference of 4×4 block
means can never exceed the mean absolute difference of the pixels those blocks
average, so a pair whose block bound exceeds the threshold cannot pass the full
comparison and is skipped. Nothing is discarded on an approximation, and a
property test over 200 random pairs pins the bound, because if the bound could
ever exceed the true difference, duplicates would go missing with nothing
reporting it.

### How this was arrived at — and two wrong answers along the way

Recorded because the first two methods both looked correct and both produced
numbers that were committed before being checked.

| method | usable corpus | cross-split duplicate pairs |
|---|---|---|
| perceptual hash ≤ 5, transitive grouping | 6,829 | not measured |
| perceptual hash ≤ 5, leader-based | 7,164 | not measured |
| hash ≤ 5 as candidate gate, pixels confirm | 8,541 | **127** |
| **pixels alone, exhaustive** | **8,316** | **0** |

1. **Transitive grouping chained near misses** into a single group of 866
   images, discarding hundreds of distinct photographs. Membership is judged
   against a group leader instead.
2. **A hash threshold is not a duplicate test.** At a Hamming distance of 5,
   24% of the pairs the hash collapsed had a pixel difference above 15 of 255 —
   two different leaves centred on the same background share a coarse layout,
   and a 64-bit hash sees little else. Adding a pixel confirmation fixed that
   precision problem.
3. **But using the hash to generate candidates silently capped recall.** A
   review of the resulting manifest found **127 cross-split pairs under the
   pixel threshold whose hashes were 6 to 30 apart**, so they were never offered
   as candidates: 83 images, 3.24% of the evaluation set, had a twin in
   training. The mechanism is that pHash thresholds DCT coefficients at their
   median, so a low-contrast image has many coefficients on that median and a
   near-identical copy flips them. Measured here: two images differing by 0.01
   of 255 hash **26 bits** apart.

An earlier version of this document claimed the duplicate and non-duplicate
populations did not overlap, on the strength of a 40-pair sample. Across all
pairs they are adjacent, not separated, which is why the threshold is a stated
definition rather than a discovered gap. The choice is not delicate: the
accepted population has a median difference of 0.07 of 255 and the band from 5
to 8 holds geometric and tonal variants of one base photograph, which are
duplicates for leakage purposes. These occur within a single source as well as
across sources, so they are not explained by one exporter's augmentation.

### Verification

Checked on the built manifest, in pixel terms, over every pair — not only over
pairs some filter proposed:

- duplicate groups among the 8,316 survivors: **8,316**, so no two surviving
  images are duplicates of each other at all
- **cross-split duplicate pairs: 0** (was 127)
- duplicate pairs inside a single split: 0

## The corpus

| class | train | val | test | total |
|---|---|---|---|---|
| `grey_blight` | 966 | 207 | 207 | 1,380 |
| `brown_blight` | 832 | 177 | 177 | 1,186 |
| `algal_spot` | 937 | 200 | 200 | 1,337 |
| `healthy` | 1,009 | 215 | 215 | 1,439 |
| `other_disease` | 2,082 | 446 | 446 | 2,974 |
| **total** | **5,826** | **1,245** | **1,245** | **8,316** |

Per-class shares are 70.0–70.2% / 14.9–15.0% / 14.9–15.0%.

`other_disease` is 36% of the corpus because it absorbs five source classes
(Anthracnose, Bird Eye Spot, Red Leaf Spot, Helopeltis, White Spot). Training
uses class-balanced sampling, and the evaluation reports it as its own row with
its own precision and recall so it cannot hide misses.

### By source and class

| source | grey_blight | brown_blight | algal_spot | healthy | other_disease | total |
|---|---|---|---|---|---|---|
| `mendeley_mz598` | 785 | 559 | 658 | 1,274 | 1,420 | 4,696 |
| `agml` | 502 | 514 | 566 | 104 | 1,080 | 2,766 |
| `yunusserhat` | 93 | 113 | 113 | 61 | 474 | 854 |

### Resolutions

| size | images |
|---|---|
| 640×640 | 4,696 |
| 256×256 | 2,751 |
| 768×1024 | 545 |
| 3120×4160 | 168 |
| other | 156 |

The classifier trains at 224×224, so every source is downscaled. The 3120×4160
phone photographs come from `yunusserhat` and are the closest thing in the
corpus to what a worker will actually photograph.

## What this corpus does not contain

No physical burn or sun-scorch images. None of the nine candidate sources has
such a class, which is why burn detection is a rule-based lesion analyser rather
than a sixth trained class, and why its headline metric is specificity on
confirmed-disease images rather than burn accuracy.

## Known limitations

- The duplicate test is greyscale, so two images identical in shape but
  differing only in colour would be treated as the same photograph.
- Which copy of a duplicate group survives depends on the ordering key
  (`-pixel_area`, then path string). Measured earlier at the ~0.4% level: a
  different tie-break changes which images survive, not how many.
- The 32 dropped cross-class conflicts are photographs two sources label
  differently. Reviewing them by hand would recover real training data.

---

# 2. Model
**Date:** 2026-10-19
**Checkpoint:** `data/artifacts/teasmart-v1.pt`, epoch 10 of 15 (early stopped)
**Corpus:** `data/processed/manifest.csv`, 8,316 images, five classes, 70/15/15

Reproduce with:

```
cd ml
./.venv/Scripts/python.exe -m teasmart_ml.cli train
./.venv/Scripts/python.exe -m teasmart_ml.cli evaluate --split test
./.venv/Scripts/python.exe -m teasmart_ml.cli export
```

## 1. Training

MobileNetV3-Large, ImageNet-pretrained, five outputs, 224x224, batch 32, AdamW
at 3e-4 with cosine decay, label smoothing 0.05, mixed precision, inverse
frequency sampling, early stopping on validation macro-F1 with patience 5.

| epoch | train loss | val loss | val accuracy | val macro-F1 |
|---|---|---|---|---|
| 1 | 0.5245 | 0.4102 | 0.9253 | 0.9255 |
| 5 | 0.2793 | 0.2883 | 0.9775 | 0.9769 |
| 7 | 0.2706 | 0.2792 | 0.9799 | 0.9804 |
| **10** | **0.2598** | **0.2591** | **0.9880** | **0.9885** |
| 14 | 0.2398 | 0.2570 | 0.9863 | 0.9868 |
| 15 | 0.2494 | 0.2763 | 0.9815 | 0.9823 |

Stopped at epoch 15: no improvement for five epochs. The checkpoint is epoch 10.

The architecture is the 4 GB laptop card, not a preference - and the same
constraint happens to be the product requirement, because this model also has to
run in a browser on a phone.

## 2. Held-out test split

**This is the number to quote.** The validation split chose the epoch, so it is
optimistic by construction; the test split was not consulted until here.

- images: **1,245**
- accuracy: **0.9871**
- macro-F1: **0.9873**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| `grey_blight` | 0.9854 | 0.9758 | 0.9806 | 207 |
| `brown_blight` | 0.9778 | 0.9944 | 0.9860 | 177 |
| `algal_spot` | 0.9852 | 1.0000 | 0.9926 | 200 |
| `healthy` | 0.9953 | 0.9860 | 0.9907 | 215 |
| `other_disease` | 0.9887 | 0.9843 | 0.9865 | 446 |

### Confusion matrix, test split

Rows are the true class.

| true \ predicted | `grey_blight` | `brown_blight` | `algal_spot` | `healthy` | `other_disease` |
|---|---|---|---|---|---|
| `grey_blight` | 202 | 1 | 2 | 0 | 2 |
| `brown_blight` | 1 | 176 | 0 | 0 | 0 |
| `algal_spot` | 0 | 0 | 200 | 0 | 0 |
| `healthy` | 0 | 0 | 0 | 212 | 3 |
| `other_disease` | 2 | 3 | 1 | 1 | 439 |

### The three errors that matter to a farmer

An aggregate F1 hides which mistakes cost money. These are the ones that do:

| failure | meaning | test | val |
|---|---|---|---|
| diseased leaf called `healthy` | an outbreak goes untreated | **0 of 584** | **0 of 584** |
| `healthy` leaf given a disease name | fungicide sprayed for nothing | **0 of 215** | **0 of 215** |
| `other_disease` given a disease name | **the wrong fungicide** | 6 of 446 (1.35%) | 9 of 446 (2.02%) |

No leaf with a disease was called healthy, and no healthy leaf was given a
disease name, on either split. The remaining failure is the one the
`other_disease` class was added for: an unfamiliar disease being confidently
named as one of the three the model knows. It happens to roughly one in seventy
of them, and it is the reason the confidence floor exists.

The three healthy leaves called `other_disease` are a cheap error: the advice
record for `other_disease` says to consult, not to spray.

## 3. Validation split, for comparison

- images: 1,245 · accuracy **0.9880** · macro-F1 **0.9885**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| `grey_blight` | 0.9855 | 0.9855 | 0.9855 | 207 |
| `brown_blight` | 0.9725 | 1.0000 | 0.9861 | 177 |
| `algal_spot` | 0.9852 | 1.0000 | 0.9926 | 200 |
| `healthy` | 0.9953 | 0.9907 | 0.9930 | 215 |
| `other_disease` | 0.9932 | 0.9776 | 0.9853 | 446 |

Validation and test agree to within 0.001 macro-F1, so the epoch choice did not
overfit the selection split.

## 4. `min_confidence`: 0.60, and why the stated criterion was the wrong one

D3 was supposed to deliver "the smallest floor at which accepted predictions
reach 0.90 accuracy on validation". **That criterion is useless against this
model, and specifying it was my mistake.** The model is already at 0.988, so the
search returns the lowest value on the grid:

| target accuracy | val floor | val downgraded | test floor | test downgraded |
|---|---|---|---|---|
| 0.90 | 0.20 | 0.00% | 0.20 | 0.00% |
| 0.95 | 0.20 | 0.00% | 0.20 | 0.00% |
| 0.98 | 0.20 | 0.00% | 0.20 | 0.00% |
| **0.99** | **0.55** | **1.04%** | **0.63** | **1.20%** |
| 0.995 | 0.66 | 2.01% | 0.82 | 4.18% |

A floor of 0.20 means never declining to answer, which switches the
`other_disease` safety net off entirely. The criterion only asked the floor to
rescue the model from being bad on average; it never asked it to catch the
individual prediction that is about to be wrong.

**Operative criterion, amended: 0.99 accuracy among accepted predictions.** At
that target the two splits ask for 0.55 and 0.63. What a fixed floor actually
costs, measured:

| floor | val accuracy / downgraded | test accuracy / downgraded |
|---|---|---|
| 0.50 | 0.9887 / 0.40% | 0.9871 / 0.08% |
| **0.60** | **0.9927 / 1.45%** | **0.9895 / 0.72%** |
| 0.70 | 0.9967 / 2.41% | 0.9926 / 1.85% |
| 0.80 | 0.9983 / 3.53% | 0.9942 / 3.45% |

**`min_confidence` stays at 0.60.** It sits between what the two splits ask for,
it buys 0.9895 accuracy on held-out data, and it declines on 0.72% of
photographs - under one in a hundred, which a worker will tolerate. It is no
longer a provisional guess; `backend/app/core/config.py` and
`GET /api/v1/config` now carry a measured value.

### What the floor does not do

The wrong predictions are not all unconfident:

| | val | test |
|---|---|---|
| mean top probability when wrong | 0.645 | 0.755 |
| **highest top probability when wrong** | 0.839 | **0.983** |

One test image is wrong at 0.983. **No usable floor catches it.** The floor
reduces confident errors; it does not eliminate them, and nothing in the UI
should imply that a result above the floor is certain. This is a second reason
the burn-versus-disease analyser in D4 matters: it is independent evidence about
the same leaf, derived from lesion geometry rather than from the classifier.

## 5. ONNX export: ship fp32, not int8

| graph | size | top-1 agreement | max probability delta | inside the 0.05 bound |
|---|---|---|---|---|
| fp32 `teasmart-v1.onnx` | 16.8 MB | 50/50 | **0.00000** | yes |
| int8 `teasmart-v1-int8.onnx` | 4.7 MB | 50/50 | **0.24819** | **no** |

Measured over a fixed, evenly spaced 50 images of the test split, each fed the
identical preprocessed array to both the Python model and the graph.

Int8 was calibrated statically on 200 validation images and still moves a
probability by up to 0.248. Top-1 happens to agree on all 50, which is exactly
why top-1 agreement alone is not the acceptance test: **the product thresholds
on the probability.** A shift of 0.248 moves predictions across
`min_confidence` in both directions, so the browser would decline to answer
where the server answers, and answer where the server declines, with no way for
either side to see the disagreement.

This was anticipated - MobileNetV3 is a known-hard int8 case, because depthwise
convolutions have few weights per channel to quantise and hard-swish is
piecewise - which is why the export measures rather than assumes.

**Contract change:** spec section 8.4 named `teasmart-v1-int8.onnx`. The file to
load is now **`teasmart-v1.onnx`**, 16.8 MB. The int8 graph is not committed, so
it cannot be shipped by accident. fp16 is the obvious next thing to measure
(roughly 8.4 MB, and typically within 1e-3) but it is not on the critical path
before 2026-10-22.

## 6. Known limitations

**The split is not grouped by photography session.** D2 removed cross-split
duplicates in pixel terms and verified zero remained over every pair. It did not
group several shots of the same leaf or the same bush taken minutes apart - those
are not duplicates by any pixel measure, and they can land on both sides of the
split. **0.987 is therefore an upper bound on field accuracy**, not an estimate
of it. The honest way to find the real number is a few hundred photographs from
Singha Park that the model has never seen, which the deadline does not allow.

**Five classes is what the corpus has, not what a farm has.** Anything that is
not grey blight, brown blight, algal spot or a healthy leaf is `other_disease`,
including red leaf spot, nutrient deficiency and insect damage, which a farmer
would treat differently from each other.

**No burn or sun-scorch images exist in any source.** Physical burn is not a
classifier output at all; it is the rule-based analyser in D4, and its headline
metric is specificity on confirmed-disease images.

**Every image in the corpus is a close-up of a leaf.** Drone frames at altitude
are a different distribution, and the quality gate will reject most of them
before the classifier is reached.

---

# 3. Frontend

D6 PR: https://github.com/mntoyg/TeaSmart-AI/pull/2
D7 draft PR: https://github.com/mntoyg/TeaSmart-AI/pull/3

## Scope and contract

D6 implements the four routes, camera/file capture, Thai retake feedback,
ordered result cards, IndexedDB history and KB presentation. D7 adds the shell,
local ONNX/WASM worker, quality gate, classifier-only presentation, image/result
queue and per-item batch replay. The contract is section 8 of `docs/DESIGN.md`, confirmed by the user in
`4fe7263` and `c53d9a0`; no backend or ML code was edited.

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
```

**Superseded on 2026-10-19**, once the model existed. Measured in CI on the
merge commit, which is the figure that ships:

```text
Scan contract matches section 8
precache  12 entries (30736.26 KiB)

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

## 3.1 What the first visit costs

The precache is **30.7 MB over 12 entries**: 14.2 MB of onnxruntime-web WASM and
16.8 MB of fp32 model, and the rest is noise by comparison. That is the download
before the app works offline, on a connection chosen for being unreliable.

It is a known cost, not an accident. The int8 graph would have taken the model
from 16.8 MB to 4.7 MB and was rejected on accuracy grounds (section 2.5). fp16
is the untested middle at roughly 8.4 MB. A local run measures 13 entries and
35 MB only when a stale `teasmart-v1-int8.onnx` is left in
`frontend/public/models/` - it is gitignored for this reason as well as the
accuracy one, because anything in that folder gets precached.

---

# 4. Stage 1 quality gate, recalibrated

**Measured 2026-10-19 over 400 corpus images**, sampled every 20th manifest row,
after the 4 MP downscale the scan endpoint applies — downscaling smooths, and so
lowers the Laplacian variance the gate reads.

## 4.1 The gate rejected 70% of real photographs

The first live scans of corpus leaves came back `blurry` with scores of **13.3**
and **52.1** against a threshold of 80. At the D1 settings, **279 of 400 images
(69.8%)** were rejected. A demo would have shown "ภาพเบลอ" almost every time.

The threshold was set during D1 from a single synthetic fixture and had never
been compared with the corpus.

| blur score (variance of Laplacian) | |
|---|---|
| min | 4.6 |
| p1 | 9.8 |
| p2 | 15.8 |
| p5 | 22.3 |
| median | **75.9** |
| p75 | 169.2 |
| max | 590.9 |

80 sat just above the median of the distribution it was meant to be the floor
of. By source: agml median 212.8, mendeley_mz598 55.2, yunusserhat 45.4 — one
number has to clear the softest source.

## 4.2 blur_threshold: 80 to 15

| candidate | rejects |
|---|---|
| 10 | 1.2% |
| **15** | **2.0%** |
| 20 | 4.0% |
| 50 | 29.0% |
| 80 | 52.8% |

15 keeps 98% of real photographs and still catches real blur. The 20 sharpest
images, re-measured after a Gaussian blur:

| blur applied | median | max |
|---|---|---|
| 5x5 | 27.4 | 41.4 |
| **9x9** | **7.9** | **11.6** |
| 15x15 | 3.0 | 4.2 |

A 9x9 blur tops out at 11.6, below the threshold, and the 2nd percentile of
untouched images is 15.8. That gap is the discrimination margin. A 5x5 blur
passes, so **mild camera shake is accepted on purpose**: catching it would mean
rejecting about a third of good photographs.

## 4.3 exposure_max_mean: 215 to 235

215 rejected 6.0% of the corpus. Nothing in 400 images exceeds a mean of 232.3;
a tea leaf on white paper in daylight is legitimately bright. 235 rejects none
of them and still catches a frame that is essentially white.

## 4.4 High clipping now reports without deciding

With blur and exposure fixed, three of three `agml` images still failed, as
`overexposed`. The cause was the per-channel high-clipping check: **the median
corpus image has 11% of one channel at or above 250**, and the 90th percentile
has 72%, because these are leaves photographed on white backgrounds.

All 24 images above a 215 mean also exceeded 10% channel clipping — both checks
were firing on the same thing, and that thing was the background.

**A blown background says nothing about whether the leaf lost detail.** Judging
it properly means measuring inside the leaf mask, which needs stage 2, which
stage 1 deliberately runs before so that it stays cheap and portable to the
browser. Measuring the wrong thing or measuring nothing were the only options,
so high clipping is now **measured and reported but not a rejection reason**.

Low clipping stays decisive: a frame crushed to black has genuinely lost the
shadow detail the lesion analyser reads, and nothing in 400 images trips it.

## 4.5 Live result after the change

15 real corpus images, one per class per source, through the running endpoint:

| source / class | prediction | confidence | verdict | severity | time |
|---|---|---|---|---|---|
| mendeley / grey_blight | other_disease | 0.50 | disease | mild | 26 ms |
| yunusserhat / brown_blight | brown_blight | 0.99 | disease | mild | 66 ms |
| mendeley / brown_blight | brown_blight | 0.88 | disease | moderate | 35 ms |
| agml / brown_blight | brown_blight | 0.96 | disease | mild | 9 ms |
| mendeley / algal_spot | algal_spot | 0.91 | disease | mild | 23 ms |
| yunusserhat / healthy | healthy | 0.91 | disease | mild | 84 ms |
| mendeley / healthy | healthy | 0.87 | disease | mild | 24 ms |
| yunusserhat / other_disease | other_disease | 0.87 | disease | mild | 540 ms |
| mendeley / other_disease | other_disease | 0.92 | disease | mild | 50 ms |
| agml / other_disease | other_disease | 0.95 | disease | mild | 9 ms |

**3 of 15 scanned before this change; 10 of 15 after the thresholds and 13 of 15
after the clipping fix.** The two that remain rejected are genuinely soft
`yunusserhat` frames below the blur floor, which is the gate working.

**No disease image was called a physical burn.** That is the specificity the
burn analyser is judged on, and on this sample it is 0 false positives in 10 —
indicative only, because ten images is not a measurement. The full test-split
run is still owed.

The grey blight image downgraded to `other_disease` at 0.50 is the confidence
floor declining to name a disease it is unsure of.

## 4.6 Frontend to backend, live

Through the Vite dev proxy on port 5173, which is the path the browser uses:

```text
GET  /api/v1/config  -> 200   blur 15.0, exposure 40-235, min_confidence 0.60
GET  /api/v1/kb      -> 200   6 records
POST /api/v1/scan    -> 200   brown_blight 0.88, disease, moderate 6.8%, 69 ms
```

The `/scan` screen loads in Thai, fetches `/api/v1/kb` and `/api/v1/config` on
mount — both 200, no console errors — and a `FormData` POST issued from inside
the page returns all ten contract fields with Thai advice.

The full chain: browser origin, dev proxy, FastAPI, decode, downscale, quality
gate, segmentation, ONNX, lesion analysis, severity, knowledge base.

Reproduce:

```bash
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
cd frontend && npm run dev
curl -s -X POST http://localhost:5173/api/v1/scan \
  -F "image=@data/interim/mendeley_mz598/brown_blight/mendeley_mz598-000001.jpg"
```

---

# 5. Burn versus disease: what can and cannot be claimed

**Measured 2026-10-20 on the test split**, 1,245 images, 1,030 of them with a
disease. Reproduce with the analyser against the manifest; the script is a
one-off measurement and the behaviour it established is pinned by tests in
`backend/tests/test_lesion.py`.

## 5.1 The headline, and why the first version of it was misleading

**Specificity on confirmed-disease images: 97.18%** — 29 of 1,030 wrongly
called `physical_burn`, a false-burn rate of **2.82%** against the spec's target
of below 5%.

The first run of this measurement reported **99.22%**, and that number was
worthless. The analyser was finding **no measurable lesion on 610 of 1,030
diseased leaves (59%)**, and a non-finding returns `disease` with a likelihood
of 0.0. The median `burn_likelihood` over disease images was exactly 0.000.
Specificity was high because the analyser was not looking, not because it was
discriminating — the same censoring that made "the two populations no longer
overlap" wrong during D2.

## 5.2 Two structural faults, found by measuring

**The leaf rim was being read as a lesion.** The rim just inside the leaf
outline is where green fades: antialiasing, the shadow at the leaf edge, a
little blur. It is less green than the interior on *every* leaf, so it crossed
any fractional cut-off. Swept over four reference percentiles and five
fractions, **every single combination had negative separation** — the mask
fired on healthy leaves more often than on diseased ones:

| rim excluded | cut-off | lesion on disease | lesion on healthy | separation |
|---|---|---|---|---|
| 0 px | 0.55 | 75.9% | 96.0% | **−0.201** |
| 0 px | 0.75 | 99.3% | 100.0% | −0.007 |
| **8 px** | **0.55** | **65.2%** | **30.0%** | **+0.352** |
| 14 px | 0.55 | 59.6% | 27.0% | +0.326 |

**Marginal damage was outside the leaf mask entirely.** The mask was the filled
external contour of the green region. Straw-coloured sun scorch fails the hue
test, so it is not green; and because it reaches the leaf edge it is a concavity
open to the frame rather than an enclosed hole, so filling the contour did not
recover it. Measured directly on the burn fixture: the blotch contributed **0
pixels** to the leaf mask and 0 to the lesion search.

**The burn case — the one thing this product exists to detect — was
structurally invisible.** The convex hull of the green region fixes it:

| leaf mask | lesion on disease | lesion on healthy | area |
|---|---|---|---|
| filled contour | 65.2% | 30.0% | x1.000 |
| **convex hull** | **85.8%** | 61.0% | x1.051 |

The hull is the right trade despite the worse separation, because what has to
stay rare is the burn **verdict**, not a measured lesion. A lesion found on a
healthy leaf reports a few percent of severity under a `healthy` prediction; an
unreachable verdict means the feature does not work at all.

An earlier test compared the filled contour against filling only enclosed
holes and found them identical, which was the wrong pair: both exclude a
concavity that is open to the frame.

## 5.3 After both fixes

| | before | after |
|---|---|---|
| diseased leaves with no measurable lesion | 610 of 1,030 (59%) | **325 of 1,030 (32%)** |
| specificity on disease images | 99.22% (censored) | **97.18%** |
| false burn rate | 0.78% (censored) | **2.82%**, target < 5% |
| median `burn_likelihood` on disease | 0.000 | 0.080 |
| synthetic burns flagged | 1 of 112 (0.9%) | 8 of 145 (5.5%) |
| untouched healthy leaves called burn | 3 of 200 | 5 of 200 |

By class, false burns: `grey_blight` 4/207 (1.93%), `brown_blight` 4/177
(2.26%), `algal_spot` 2/200 (1.00%), `other_disease` 19/446 (4.26%).

## 5.4 The features do discriminate

On the fixtures, with every feature in its intended direction:

| | edge_sharpness | ring_score | acervuli | edge_affinity | colour_zonation | score | likelihood |
|---|---|---|---|---|---|---|---|
| disease | 1.00 | 1.00 | 1.00 | 0.00 | 0.83 | −6.07 | 0.002 |
| burn | 0.04 | 0.00 | 0.00 | 0.21 | 0.34 | −0.73 | 0.325 |

A gap of 5.3 score units. The features are not reading noise.

## 5.5 Sensitivity is unknown, and that is the honest answer

**Synthetic burns score a median likelihood of 0.254, while real disease images
reach 0.714 at the 99th percentile. The two overlap.** Only 5.5% of synthetic
burns clear the 0.60 threshold.

Two explanations fit this data equally well:

1. the features do not capture real burns, or
2. the synthetic burns are not burn-like enough — they were painted from the
   same feature definitions they are being tested against, which cannot
   independently confirm anything.

**Nothing in the available data distinguishes those two.** No labelled burn
photograph exists in any of the nine sources surveyed, so there is no ground
truth to calibrate against. **No sensitivity figure should be quoted for this
feature, in a demo or anywhere else.**

What can be said: the analyser is heavily biased toward reporting `disease`,
and that is the safe direction. A false burn tells a farmer not to spray a leaf
that may be infected; a missed burn tells them to spray a leaf that did not
need it. The first is the expensive error, so `burn_threshold` stays at 0.60
even though it means the burn verdict is rare.

The threshold is deliberately above the fixture's 0.325. Lowering it to catch
that case would pull in real disease images, whose 90th percentile is 0.430 —
specificity would collapse. That trade is recorded rather than taken.

## 5.6 What would settle it

A few hundred photographs of real sun-scorched and spray-damaged tea leaves,
labelled. Two hundred would be enough to fit the five weights properly and to
quote a sensitivity. Until then this feature is a conservative prior with a
measured specificity and an unmeasurable sensitivity, and the demo should say
exactly that.

---

# 6. Browser and Python agree: the parity gate passes

**Measured 2026-10-20.** `docs/DESIGN.md` section 8.4 makes this the condition
for calling D7 done: over a fixed set of 50 manifest images, the browser and
Python pipelines must agree on top-1 for every image, and no class probability
may differ by more than **0.05**.

```text
images              50
top-1 agreement     50/50
max prob delta      0.00283      (bound 0.05)
mean prob delta     0.00021
worst image         12.jpg
passes              true
```

**Eighteen times inside the bound.** The measurement includes the whole chain:
JPEG decoding, the canvas round-trip the app uses to get pixels from a file,
the resize, the ImageNet normalisation and the fp32 ONNX graph. Pillow and the
browser do not decode a JPEG identically, and that difference is inside this
number rather than assumed away.

## 6.1 What it took

The browser sampled four neighbours; PIL scales its triangle filter's support
by the reduction factor. Over twelve corpus images the two preprocessing paths
differed by **up to 101 of 255** in a channel, worst on a 3120x4160 phone
photograph - the input the demo uses.

| image | size | max channel difference |
|---|---|---|
| agml-005147 | 256x256 | 12 |
| mendeley_mz598-004194 | 640x640 | 49 |
| yunusserhat-000096 | 768x1024 | 53 |
| **yunusserhat-000415** | **3120x4160** | **101** |

Python could not move: the classifier was trained on PIL's output. So the
browser now implements PIL's algorithm, and the missing step was one line -
the filter support growing with the reduction factor. When scaling up it stays
at 1 and the whole thing reduces to ordinary bilinear, which is why the
256x256 case agreed even before the fix and why a fixture set of small images
would have certified the bug as fixed.

## 6.2 Reproducing it

```bash
backend/.venv/Scripts/python.exe scripts/prepare_parity.py   # 50 images + answers
cd frontend && npm run dev
```

Open `http://localhost:5173/scan` and paste `scripts/parity_browser.js` into
the console, then `await runParity()`.

The sample is every 24th row of the test split rather than random, so the
number means the same thing on every machine and before and after a re-export.
The images and the answer sheet are gitignored: they are corpus photographs.

## 6.3 The unit-level fixtures underneath it

`frontend/src/test/fixtures/preprocess/` holds five sources both languages
build from a coordinate hash, and the exact bytes PIL produces for each. The
Vitest suite checks the browser against them and the pytest suite checks the
server, so all three implementations answer to one definition. Reductions span
1.14x to 18.6x deliberately: the defect is proportional to the reduction
factor.

All five pass within **2 of 255** per channel and **0.30** mean.

Two tests guard that result beyond the fixtures themselves. One runs the old
four-neighbour sampler against the large-reduction fixture and requires it to
miss by more than 30, so the fixtures cannot quietly stop testing what they
were built for. The other puts a single bright row at a position no output
centre lands on and requires it to survive a 9x reduction, which states the
filter-widening property directly rather than leaving it implied.

## 6.4 What this does and does not license

It licenses the offline path: an on-device result now differs from a server
result only by what the browser genuinely cannot do, not by an accident of
resampling.

It does **not** make an on-device result equivalent to a server one. The
browser does not segment, so it has no lesion analysis and no severity, and the
result card still has to say `classifier_only`. That is a product difference,
not a defect, and the parity gate was never about it.
