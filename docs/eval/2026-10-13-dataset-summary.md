# Dataset summary — 2026-10-13

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
