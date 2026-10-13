# Dataset summary — 2026-10-13

The corpus every accuracy figure from D3 onward is measured against. Reproduce
it with:

```bash
cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare
```

Seed `42`, stratified 70/15/15, manifest at `data/processed/manifest.csv`.

## Sources

Three of the nine candidate sources need no credentials and are the only ones
enabled. Probed 2026-10-13.

| source | origin | ingested | corrupt | unlabelled | ambiguous |
|---|---|---|---|---|---|
| `agml` | HF `Project-AgML/tea_leaf_disease_classification` | 5,867 | 0 | — | — |
| `yunusserhat` | HF `yunusserhat/tea_sickness_dataset` | 885 | 0 | — | — |
| `mendeley_mz598` | Mendeley `mz598gxfw9` v1 (Roboflow YOLO export) | 5,101 | 0 | 79 | 0 |
| **total** | | **11,853** | **0** | **79** | **0** |

`agml` ingested 5,867 images matching its README exactly per class, which is the
check that the ClassLabel order in the registry is right. `mendeley_mz598` holds
5,180 images; 79 carry no label file and none is annotated with two different
classes, so all 5,180 are accounted for.

Not used: `mendeley_sjmy` (`sjmy6k24d6`) answers HTTP 451 and is dropped; two
Kaggle sources and the gated `ttkqwe123` need credentials and stay registered
but disabled; `mendeley_d2xy` (3.07 GB) and `mendeley_94fz` (964 MB, .rar) are
deferred extra volume.

## Deduplication

| | count |
|---|---|
| ingested | 11,853 |
| duplicate copies collapsed | 3,311 |
| cross-class conflicts dropped | 1 |
| **usable corpus** | **8,541** |

3,245 of the 3,261 duplicate groups span two sources: `agml` and
`mendeley_mz598` substantially overlap, which is the leakage this step exists to
prevent. Only 16 groups are duplicates inside a single source.

Each group keeps its highest-resolution copy. That is why `agml`'s healthy count
falls from 1,000 ingested to 106 in the manifest: `mendeley_mz598` holds the
same photographs at 640×640 against agml's 256×256, so the larger copies win.

The single remaining cross-class conflict is one photograph labelled as two
different classes across sources. It is dropped rather than resolved by sort
order, because keeping either side would train the model on a label no
annotator gave.

### How the threshold was chosen

Measured, not assumed. A perceptual hash alone was tried first at the Hamming
distance of 5 the spec named, and 24% of the pairs it collapsed were not the
same photograph — two different leaves centred on the same background share a
coarse layout, and a 64-bit hash sees little else. Transitive grouping made it
worse, chaining near misses into a single group of 866 images.

| approach | usable corpus | biggest group | worst in-group pixel MAE |
|---|---|---|---|
| transitive, distance ≤ 5 | 6,829 | 866 | 43.3 |
| leader-based, distance ≤ 5 | 7,164 | 44 | 48.1 |
| **leader-based + pixel confirmation** | **8,541** | **16** | **0.2** |

The shipped method uses the hash to find candidates and a 32×32 greyscale mean
absolute difference of at most 8.0 (of 255) to confirm them. Sampled
in-group pairs now measure 0.1 to 0.2, while unrelated images measure at least
16.0 — the two populations no longer overlap. It also recovered 1,712 images the
spec's method would have thrown away, and revealed that 438 of the 439
apparent cross-class conflicts were hash false positives rather than real
labelling disagreements.

## The corpus

| class | train | val | test | total |
|---|---|---|---|---|
| `grey_blight` | 983 | 210 | 210 | 1,403 |
| `brown_blight` | 845 | 181 | 181 | 1,207 |
| `algal_spot` | 953 | 204 | 204 | 1,361 |
| `healthy` | 1,051 | 225 | 225 | 1,501 |
| `other_disease` | 2,149 | 460 | 460 | 3,069 |
| **total** | **5,981** | **1,280** | **1,280** | **8,541** |

`other_disease` is 36% of the corpus because it absorbs five source classes
(Anthracnose, Bird Eye Spot, Red Leaf Spot, Helopeltis, White Spot). Training
uses class-balanced sampling, and the evaluation reports it as its own row with
its own precision and recall so it cannot hide misses.

### By source and class

| source | grey_blight | brown_blight | algal_spot | healthy | other_disease | total |
|---|---|---|---|---|---|---|
| `mendeley_mz598` | 794 | 567 | 672 | 1,330 | 1,473 | 4,836 |
| `agml` | 511 | 527 | 576 | 106 | 1,118 | 2,838 |
| `yunusserhat` | 98 | 113 | 113 | 65 | 478 | 867 |

### Resolutions

| size | images |
|---|---|
| 640×640 | 4,836 |
| 256×256 | 2,823 |
| 768×1024 | 547 |
| 3120×4160 | 173 |
| other | 162 |

The classifier trains at 224×224, so every source is downscaled. The 3120×4160
phone photographs come from `yunusserhat` and are the closest thing in the
corpus to what a worker will actually photograph.

## What this corpus does not contain

No physical burn or sun-scorch images. None of the nine candidate sources has
such a class, which is why burn detection is a rule-based lesion analyser rather
than a sixth trained class, and why its headline metric is specificity on
confirmed-disease images rather than burn accuracy.
