# TeaSmart AI — Phase 1 MVP Design Spec

- **Date:** 2026-10-13
- **Deadline:** 2026-10-22 (hackathon submission) — 9 working days
- **Status:** Approved design, pending written-spec review

## 1. Purpose

TeaSmart AI is a smart-farming assistant for large-scale Oolong tea estates
(reference site: Singha Park, Chiang Rai). A worker photographs a tea leaf with
a phone (or uploads a drone frame), and the system returns:

1. the disease class and its severity,
2. an explicit judgement of whether the damage is **biological disease** or
   **physical burn** (sun scorch / chemical burn), and
3. actionable Thai-language treatment advice from a curated expert knowledge
   base.

**Success criterion for the demo:** a judge picks up a phone, photographs a tea
leaf, and gets a correct, readable Thai result in a few seconds — *with the
network switched off*.

## 2. Scope

### In scope (Phase 1)

- Image quality gating (blur / exposure) with actionable Thai feedback
- Leaf segmentation and lesion localisation
- 5-class disease classifier (MobileNetV3-Large, transfer learning)
- Rule-based burn-vs-disease discriminator
- Severity estimation from lesion-to-leaf area ratio
- Rule-based expert system returning Thai advice
- PWA web app (camera capture, on-device ONNX inference, offline queue)
- Android `.apk` via Capacitor wrapping the same frontend

### Out of scope (Phase 2+)

- Yield forecasting (stated in the project vision, deliberately deferred)
- Multi-user accounts, estate/plot management, server-side history
- Drone flight planning or orthomosaic stitching
- Weather-anomaly modelling

## 3. Constraints

| Constraint | Consequence for the design |
|---|---|
| RTX 3050 Laptop, 4 GB VRAM | MobileNetV3-Large at 224 px, batch 32, mixed precision. No ViT, no high-res backbone. |
| Unstable mountain internet | On-device ONNX inference is the primary path; the server is an enhancement, not a dependency. |
| 9 days, capped daily AI usage | One vertical slice per day, each independently testable and committed. |
| No labelled burn images exist | Burn detection is **rule-based computer vision**, never a trained class. |
| Variable phone image quality | A quality gate runs before inference and rejects unusable frames instead of guessing. |

## 4. Repository layout

```
TeaSmart AI/
├─ ml/                      Python training package (teasmart_ml)
│  ├─ teasmart_ml/
│  │  ├─ datasets/sources.py     source registry + downloaders
│  │  ├─ datasets/ingest.py      normalise every source to canonical classes
│  │  ├─ datasets/dedup.py       perceptual-hash dedup across sources
│  │  ├─ datasets/manifest.py    manifest.csv (path, class, source, split, phash)
│  │  ├─ transforms.py           train/eval augmentation
│  │  ├─ train.py                transfer learning loop
│  │  ├─ evaluate.py             confusion matrix, per-class P/R/F1
│  │  └─ export_onnx.py          ONNX for the browser, with parity measurement
│  └─ tests/
├─ backend/                 FastAPI service
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/v1/scan.py, api/v1/kb.py, api/v1/sync.py
│  │  ├─ core/config.py, core/images.py (safe decode)
│  │  ├─ services/quality.py     stage 1
│  │  ├─ services/segment.py     stage 2
│  │  ├─ services/classify.py    stage 3 (onnxruntime)
│  │  ├─ services/lesion.py      stage 4 burn-vs-disease
│  │  ├─ services/severity.py    stage 5
│  │  ├─ services/expert.py      stage 6
│  │  └─ kb/diseases.json        knowledge base (6 records)
│  └─ tests/
├─ frontend/                React + Vite + TypeScript + Tailwind (PWA)
│  ├─ src/features/scan/, result/, history/, kb/
│  ├─ src/lib/onnx.ts            onnxruntime-web on-device inference
│  ├─ src/lib/queue.ts           IndexedDB offline queue + sync
│  └─ public/models/             teasmart-v1.onnx (fp32, 16.8 MB)
├─ mobile/                  Capacitor project (added D8)
├─ data/                    gitignored
│  ├─ raw/<source-id>/           untouched downloads
│  ├─ interim/<source-id>/       extracted
│  └─ processed/{train,val,test}/<class>/
└─ docs/
   ├─ superpowers/specs/         this document
   └─ eval/                      model evaluation reports
```

## 5. Canonical class taxonomy

Five **trained** classes. `physical_burn` is produced by stage 4, not by the
model.

| id | canonical class | KB record |
|---|---|---|
| 0 | `grey_blight` | Tea Grey Blight (given) |
| 1 | `brown_blight` | Tea Brown Blight (given) |
| 2 | `algal_spot` | Algal Leaf Spot (given) |
| 3 | `healthy` | Healthy (given) |
| 4 | `other_disease` | **new** — abnormality outside the three primary diseases |
| — | `physical_burn` | **new** — emitted by the rule engine only |

### Source label mapping

| source label | canonical |
|---|---|
| `gray_blight`, `gray_light`, `Gray Blight` | `grey_blight` |
| `brown_blight`, `Brown Blight` | `brown_blight` |
| `algal_spot`, `algal_leaf`, `Algal Leaf Spot` | `algal_spot` |
| `healthy`, `Healthy` | `healthy` |
| `anthracnose`, `bird_eye_spot`, `red_spot`, `red_leaf_spot`, `Red Leaf Spot`, `helopeltis`, `Helopeltis`, `white_spot` | `other_disease` |

Rationale for `other_disease`: every source dataset carries disease classes
absent from the knowledge base. Dropping them would make the model answer
"Brown Blight" with high confidence when shown a real Red Leaf Spot leaf in the
field. Merging them into one class lets the system say "an abnormality was
detected but it is not one of the three primary diseases — have an agronomist
inspect it", which is honest and materially safer advice.

## 6. Data sources

Probed 2026-10-13. Only no-authentication sources are used in Phase 1.

| id | source | status | size | role |
|---|---|---|---|---|
| `agml` | HF `Project-AgML/tea_leaf_disease_classification` | public parquet | 32 MB / 5,867 img / 6 classes | primary classifier training set |
| `yunusserhat` | HF `yunusserhat/tea_sickness_dataset` | public parquet | 780 MB / 885 img / 8 classes | high-resolution variety; lesion-feature tuning |
| `mendeley_mz598` | Mendeley `mz598gxfw9` | public zip (Roboflow YOLO) | 108 MB / 6 classes + bboxes | lesion localisation and severity validation |
| `mendeley_d2xy` | Mendeley `d2xybhfw59` | public zip, 3.07 GB | deferred | optional extra volume |
| `mendeley_94fz` | Mendeley `94fzcdz8gz` | public rar, 964 MB | deferred | optional extra volume |
| `mendeley_sjmy` | Mendeley `sjmy6k24d6` | **HTTP 451, unavailable** | — | dropped |
| `kaggle_*` x2, `hf_ttkqwe123` | Kaggle / gated HF | needs credentials | deferred | `sources.py` keeps the entries so they can be enabled later by dropping in a token |

Usable immediately: **11,853 labelled images plus bounding-box annotations**, which deduplicate to a corpus of **8,316**. Counted on 2026-10-13; the
estimate here before the sources were opened was 6,752, which missed that
`mendeley_mz598` carries 5,180 images of its own rather than annotations alone.

### Leakage control

A duplicate is defined by pixels: two images are the same photograph when the
mean absolute difference of their 32x32 greyscale thumbnails is at most 8.0 of
255. Every pair is compared, made tractable by an exact lower bound (the mean
absolute difference of 4x4 block means can never exceed that of the pixels they
average), so nothing is discarded on an approximation. Confirmed duplicates
collapse to the highest-resolution copy; a group spanning two classes is
dropped rather than resolved. Splits are then stratified 70/15/15 **after**
dedup. The manifest records each image's source and perceptual hash so the
result is auditable, and its paths are relative to the interim root.

A perceptual hash is **not** used to decide anything, and this is the most
expensive lesson of D2. Using pHash within a Hamming distance of 5 as the test
collapsed pairs that were not the same photograph 24% of the time. Using it to
generate candidates for a pixel confirmation looked right and was worse in the
way that matters: it silently capped recall, and the manifest it produced
contained 127 cross-split duplicate pairs, leaving 3.24% of the evaluation set
with a twin in training. pHash thresholds DCT coefficients at their median, so a
low-contrast image has many coefficients sitting on it and a near-identical copy
flips them - two images measured 0.01 of 255 apart hashed 26 bits apart.

**Verified, not asserted.** After each build, every pair of manifest rows is
compared in pixel terms, and the check is stated without reference to how
candidates are generated: the earlier version only examined pairs the hash had
proposed, which is why it reported zero while those 127 pairs existed. The
current corpus reports 0 cross-split duplicate pairs out of 8,316 rows. See
`docs/eval/2026-10-13-dataset-summary.md` for the numbers and the two wrong
answers that preceded them.

## 7. Inference pipeline

```
image -> [1] quality gate -> [2] leaf segment -> [3] classifier
      -> [4] lesion analyser -> [5] severity -> [6] expert system -> result
```

Every stage is a pure function over a well-defined input, independently
testable, with no knowledge of any other stage's internals.

### Stage 1 — Quality gate (`services/quality.py`)

- **Blur:** variance of the Laplacian; reject below a calibrated threshold.
- **Exposure:** mean luminance plus the fraction of clipped pixels at both ends
  of the histogram; reject over/under-exposed frames.
- Returns `{passed, blur_score, exposure_score, reason_th}`. On failure the API
  returns `422` with a Thai instruction ("ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น")
  rather than a guessed diagnosis.

Thresholds are calibrated against the training corpus plus synthetically
blurred and re-exposed copies, and are stored in config, not hard-coded at call
sites.

### Stage 2 — Leaf segmentation (`services/segment.py`)

Excess-green index combined with an HSV green mask, morphological cleanup, then
the largest connected contour. Outputs the leaf mask, a tight crop, and the
leaf's pixel area. Without this step the severity ratio is meaningless and the
background drives false positives.

### Stage 3 — Classifier (`services/classify.py`)

MobileNetV3-Large, ImageNet-pretrained, head replaced with 5 outputs. Input
224x224 on the segmented crop. Training: AdamW, cosine schedule, label
smoothing 0.05, class-balanced sampling, mixed precision, early stopping on
validation macro-F1. Augmentation targets the real failure modes: random
resized crop, rotation, horizontal/vertical flip, colour jitter, motion blur,
and brightness/contrast shifts standing in for field lighting.

Outputs `{class_id, class_name, confidence, top_k}`. Confidence below a
configured floor downgrades the result to `other_disease` with an explicit
low-confidence flag.

### Stage 4 — Burn-vs-disease discriminator (`services/lesion.py`)

This is the project's differentiator and it uses **no labelled burn data**. From
the lesion mask (threshold within the leaf mask on the non-green residual), five
normalised features are computed:

| feature | computation | burn | disease |
|---|---|---|---|
| `edge_sharpness` | mean Sobel gradient magnitude in a band along the lesion boundary | low (diffuse) | high (crisp dark margin) |
| `ring_score` | sign changes / dominant frequency of the radial intensity profile from the lesion centroid | low (absent) | high (concentric zonation) |
| `acervuli_score` | bottom-hat morphology plus blob detection, size-filtered to 2-8 px, density per lesion area | low (absent) | high (black fruiting dots) |
| `edge_affinity` | fraction of lesion pixels within k px of the leaf contour | high (tip/margin, sun-facing) | low (scattered over the lamina) |
| `colour_zonation` | number of distinct hue/value clusters inside the lesion (k-means, inertia drop) and mean saturation | low (uniform straw, desaturated) | high (multi-band brown to grey) |

Each feature is normalised by percentiles measured on the training corpus, then
combined as a weighted logistic score into `burn_likelihood` in the range 0 to
1. Above a configured threshold (initially 0.6) the result is overridden to
`physical_burn`, the disease confidence is reported as suppressed, and the
expert system returns burn advice (adjust shade, review spray concentration,
irrigate — explicitly **no fungicide**).

**Honest evaluation.** With no real burn photographs, the claim is not "we
detect burns with X% accuracy". We measure and report two things:

- **Specificity:** the rate at which confirmed-disease test images are wrongly
  flagged as burn. Target below 5%. This is measurable on real data and is the
  metric that matters, because the feature exists to cut false positives.
- **Sensitivity on synthetic burns:** burn-like lesions rendered onto healthy
  leaves (soft-edged tan gradient blotches seeded at leaf margins, no
  micro-dots, no rings). Reported as indicative only, clearly labelled as
  synthetic.

Weights and thresholds live in config so they can be tuned without code changes.

### Stage 5 — Severity (`services/severity.py`)

`affected_pct = lesion_area / leaf_area`, mapped to mild (below 5%), moderate
(5-20%), severe (above 20%). Bounding boxes from `mendeley_mz598` are used to
sanity-check that the lesion mask overlaps the annotated lesions (IoU report in
`docs/eval/`).

### Stage 6 — Expert system (`services/expert.py`)

A pure lookup from the resolved class into `kb/diseases.json`, returning the
Thai advice fields verbatim. Severity selects the emphasis (severe escalates to
the chemical treatment; mild leads with cultural control). The knowledge base is
data, never code, and is served to the frontend so it can be cached for offline
use.

**Knowledge base schema** (per record): `class_id`, `canonical`,
`class_name`, `disease_name_th`, `pathogen`, `symptoms`, `immediate_action`,
`cultural_control`, `chemical_treatment`, `preventive_measures`. Records 0-3
carry the four supplied advice texts verbatim; records 4 (`other_disease`) and 5
(`physical_burn`) are added by this design and written in the same voice.

`canonical` is the snake_case name from section 5 and is the key the lookup
uses, because that is the name stage 3 emits and the name section 8 puts in the
response. `class_name` remains the English display name.

## 8. API contract

This section is the interface between the backend and the PWA. Neither side
changes it alone: a change is written here first, noted in `docs/STATE.md`, and
raised with the user.

| method | path | purpose |
|---|---|---|
| `GET` | `/health` | liveness, model version |
| `POST` | `/api/v1/scan` | one image, full result |
| `GET` | `/api/v1/kb` | the knowledge base, for offline caching |
| `GET` | `/api/v1/config` | the constants both sides need, for offline caching |
| `POST` | `/api/v1/sync/batch` | replay scans queued while offline |

### 8.1 `POST /api/v1/scan`

`Content-Type: multipart/form-data` with these parts:

| part | required | type | notes |
|---|---|---|---|
| `image` | yes | file | The field name is **`image`**. The declared content type and the filename are ignored; the format is decided by magic bytes. JPEG, PNG and WebP only. |
| `scan_id` | no | text | A client-generated UUIDv4. Supply it: it is the idempotency key (8.3) and it is what ties a queued scan to its result. When absent the server generates one. |
| `captured_at` | no | text | ISO 8601 with offset, from the device clock. Recorded, never trusted. |

Limits, from `Settings`: `max_upload_bytes` 8388608 (8 MiB) and
`max_image_pixels` 40000000. Over either one the request is refused before the
image is decoded.

Responses:

| status | when | body |
|---|---|---|
| `200` | analysed | the result object below |
| `422` | the quality gate rejected the frame | `{"detail", "detail_th", "quality"}` |
| `415` | not a JPEG, PNG or WebP | `{"detail", "detail_th"}` |
| `413` | over the byte or pixel cap | `{"detail", "detail_th"}` |
| `400` | truncated or undecodable | `{"detail", "detail_th"}` |

Only `detail_th` is ever shown to a worker. `detail` is English, for logs.

A `422` is not an error page: it carries the Thai instruction that tells the
worker what to change, and the UI offers an immediate retake.

```json
{
  "scan_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "captured_at": "2026-10-13T09:12:04+07:00",
  "quality": {
    "passed": true,
    "blur_score": 704.5,
    "exposure_mean": 93.4,
    "clipped_low_pct": 0.0,
    "clipped_high_pct": 0.0
  },
  "prediction": {
    "class_id": 0,
    "class_name": "grey_blight",
    "confidence": 0.93,
    "top_k": [
      { "class_name": "grey_blight", "confidence": 0.93 },
      { "class_name": "brown_blight", "confidence": 0.04 }
    ],
    "low_confidence": false
  },
  "burn_analysis": {
    "verdict": "disease",
    "burn_likelihood": 0.12,
    "features": {
      "edge_sharpness": 0.81,
      "ring_score": 0.74,
      "acervuli_score": 0.66,
      "edge_affinity": 0.19,
      "colour_zonation": 0.71
    }
  },
  "severity": { "affected_pct": 0.11, "level": "moderate" },
  "advice": {
    "canonical": "grey_blight",
    "disease_name_th": "โรคใบไหม้เทา",
    "immediate_action": "...",
    "cultural_control": "...",
    "chemical_treatment": "...",
    "preventive_measures": "..."
  },
  "analysis_mode": "full",
  "model_version": "teasmart-v1",
  "processing_ms": 412
}
```

`verdict` is `"disease"` or `"physical_burn"`. `level` is `"mild"`,
`"moderate"` or `"severe"`. `analysis_mode` is `"full"` or
`"classifier_only"`, and the result card states which: a worker must never be
left thinking an on-device answer was a complete analysis.

When `verdict` is `"physical_burn"`, `advice` comes from knowledge-base record 5
and prescribes no fungicide. The UI shows that distinction prominently; it is
the feature the product exists for.

### 8.2 `POST /api/v1/sync/batch`

Replays scans the browser queued while offline, each of which already has a
local classifier-only result. The server redoes them in full.

`Content-Type: multipart/form-data`:

| part | required | notes |
|---|---|---|
| `items` | yes | a JSON array, one object per queued scan: `{"scan_id", "captured_at", "local_prediction": {"class_name", "confidence"}}`. `local_prediction` is optional and is recorded for comparison, never used as an answer. |
| `images` | yes | one file part per item, repeated. **Each part's filename must be its `scan_id`.** |

Items and files are matched by `scan_id`, not by position: an off-by-one would
attach a diagnosis to the wrong photograph, and a worker would treat the wrong
plot. A `scan_id` in `items` with no matching file, or a file with no matching
item, is a `422` for the whole request.

Limits, from `Settings`: `max_batch_items` 20 and `max_batch_bytes` 33554432
(32 MiB). A longer queue is sent as several requests; the client chunks it.

`200` with a per-item outcome, so one unusable frame does not fail the batch:

```json
{
  "results": [ { "scan_id": "...", "...": "the full scan result object" } ],
  "failed": [
    {
      "scan_id": "9f1c...",
      "status": 422,
      "detail": "blurry",
      "detail_th": "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"
    }
  ]
}
```

Every `scan_id` sent appears in exactly one of the two arrays. `422` is returned
for the envelope only: a malformed `items`, a mismatch, or over the limits.

### 8.3 Idempotency

`scan_id` is the idempotency key for both endpoints. A dropped connection on a
mountain plot means retries are normal, and a retry must not produce a second
diagnosis or a second history entry.

- The client generates a UUIDv4 at capture time, stores it with the queued
  image, and sends it on every attempt including retries.
- The server keeps a bounded in-memory map of recently completed `scan_id`s to
  their results (`Settings.idempotency_cache_size`, 512). A repeat returns the
  stored result with `200` and `"replayed": true` on the result object.
- **This cache does not survive a restart, and that is deliberate for Phase 1:**
  there is no database (section 2). The client is the durable record and must
  dedupe locally by `scan_id` as well. The server-side cache only covers the
  common case of a retry seconds later.

### 8.5 `GET /api/v1/config`

Everything the PWA needs that also exists in the backend, in one cacheable
document. The browser fetches it alongside the knowledge base and keeps both in
the service-worker cache.

It exists because two things are necessarily implemented twice - the quality
gate, because it is cheap and must work offline, and the classifier
preprocessing, because onnxruntime-web runs the model in the browser - and a
second copy of each constant in TypeScript drifts the first time one is retuned.

```json
{
  "model_version": "teasmart-v1",
  "min_confidence": 0.6,
  "class_order": ["grey_blight", "brown_blight", "algal_spot", "healthy", "other_disease"],
  "preprocessing": {
    "size": [224, 224],
    "resize": "bilinear",
    "preserve_aspect_ratio": false,
    "scale": 255.0,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "layout": "NCHW",
    "dtype": "float32"
  },
  "onnx": {
    "file": "teasmart-v1.onnx",
    "input": "input",
    "output": "logits",
    "output_is_logits": true
  },
  "quality": {
    "blur_threshold": 80.0,
    "exposure_min_mean": 40.0,
    "exposure_max_mean": 215.0,
    "clip_max_pct": 0.1
  }
}
```

`class_order` is derived from the knowledge base in `class_id` order, with
`physical_burn` excluded because the classifier never emits it. It is derived
rather than listed a second time, so it cannot disagree with the records the
advice is looked up by.

`min_confidence` is **0.60, measured** on 2026-10-19 and no longer
provisional. The criterion D3 was given - the smallest floor reaching 0.90
accuracy among accepted predictions - returns 0.20 against a model already at
0.987, which switches the `other_disease` safety net off. The operative
criterion is **0.99 accuracy among accepted**, which asks for 0.55 on the
validation split and 0.63 on the test split. At 0.60 the held-out split gives
0.9895 accuracy and declines 0.72% of photographs.

The floor does not catch every confident error: one test image is wrong at
0.983. No UI may imply that a result above the floor is certain.

### 8.4 ONNX model contract

The browser and the server must agree on preprocessing or their answers diverge
for reasons nobody can see. Both sides implement exactly this:

1. decode to RGB `uint8`
2. resize to **224x224, bilinear, aspect ratio not preserved**
3. divide by 255 into `[0, 1]`
4. normalise per channel, ImageNet statistics: mean `(0.485, 0.456, 0.406)`,
   std `(0.229, 0.224, 0.225)`
5. transpose to NCHW, `float32`, batch 1

| | |
|---|---|
| file | `frontend/public/models/teasmart-v1.onnx` — **fp32** |
| input | `input`, `float32[1, 3, 224, 224]`, NCHW |
| output | `logits`, `float32[1, 5]` — **raw logits, not probabilities** |
| class order | `grey_blight`, `brown_blight`, `algal_spot`, `healthy`, `other_disease` |

Softmax is applied by the caller. `low_confidence` is set when the top
probability falls below `min_confidence`, and the result is then reported as
`other_disease` with the flag set. **Read that floor from
`GET /api/v1/config`; do not hard-code it.** It is provisional until D3
measures it, and a copy in TypeScript would drift the moment it is retuned -
silently, because neither codebase can see the other.

**The browser does not segment.** Stage 2 exists only in Python, so an
on-device run preprocesses the whole frame while the server preprocesses the
segmented crop. The two therefore disagree on some images, which is part of why
an on-device result is labelled `classifier_only` rather than presented as
equivalent. The quality gate is duplicated in JavaScript because it is cheap;
nothing else is.

**Parity test**, required before D7 is called done: over a fixed set of 50
manifest images, the browser and Python pipelines must agree on top-1 for every
image, and no class probability may differ by more than 0.05.

**Int8 failed that bound and is not shipped** (2026-10-19). Statically
calibrated int8 agreed on top-1 for all 50 images but moved a probability by
**0.248**. Top-1 agreement alone is not the acceptance test, because the
product thresholds on the probability: a shift that size moves predictions
across `min_confidence` in both directions, and neither side can see the
disagreement. The file to load is `teasmart-v1.onnx`, fp32, 16.8 MB.
Measurements in `docs/eval/2026-10-19-d3-model.md` section 5.

## 9. Frontend and offline behaviour

- **Online:** the image is posted to the backend and the full six-stage pipeline
  runs server-side.
- **Offline:** `onnxruntime-web` runs the int8 model in the browser, giving the
  class and confidence immediately; the quality gate also runs client-side in
  JavaScript (it is cheap). The image plus its local result is queued in
  IndexedDB and replayed through `/api/v1/sync/batch` when connectivity returns,
  at which point the full lesion analysis and severity are filled in.
- The result card states plainly which mode produced it, so a field worker is
  never misled about how complete the analysis is.
- A service worker precaches the shell, the ONNX model, and the knowledge base.
- Routes: `/scan`, `/result/:id`, `/history`, `/kb`.

The duplication is deliberate and bounded: only the classifier and the quality
gate exist twice. The lesion analyser, severity and expert system have exactly
one implementation, in Python.

## 10. Security (OWASP-aligned)

- Accept uploads by **magic-byte sniffing**, never by file extension.
- Hard request-size cap; reject early.
- Decode through Pillow with `MAX_IMAGE_PIXELS` set, guarding decompression
  bombs, then **re-encode** to strip EXIF and any embedded payload before the
  image touches any other code.
- Stored filenames are server-generated UUIDs; no user-supplied path component
  ever reaches the filesystem.
- Strict Pydantic models on every request and response.
- CORS restricted to an explicit allowlist; rate limiting on `/api/v1/scan`.
- Configuration via `.env` with a committed `.env.example`; no secrets in the
  repository. `data/` and model weights are gitignored.
- The knowledge base is read-only at runtime and loaded once at startup.

## 11. Testing strategy

- **ml:** pytest over the label mapping, dedup behaviour, split stratification,
  and manifest integrity. A tiny fixture corpus keeps these fast.
- **backend:** pytest per stage. The lesion analyser is tested against
  **synthetic fixtures** generated by code — disease-like lesions (sharp margin,
  concentric rings, micro-dots) and burn-like lesions (soft tan gradient at the
  leaf margin) — so the discriminator has deterministic, reviewable tests rather
  than depending on hand-picked photographs. Security tests cover a polyglot
  file, an oversized upload, and a decompression bomb.
- **frontend:** vitest over the offline queue and the ONNX pre/post-processing,
  asserting that the browser pipeline and the Python pipeline agree on the same
  input within tolerance.
- **model:** `docs/eval/` holds the confusion matrix, per-class precision /
  recall / F1, and the burn-specificity figure. No accuracy claim is made in the
  README or the pitch without a committed report behind it.

## 12. Nine-day plan

| day | date | deliverable |
|---|---|---|
| D1 | 10-13 | repo scaffold, git + private GitHub, knowledge base (6 records), backend skeleton, quality gate + tests |
| D2 | 10-14 | `sources.py` downloaders, ingest + dedup + manifest for the three live sources |
| D3 | 10-15 | training pipeline, first trained model, evaluation report committed |
| D4 | 10-16 | leaf segmentation, lesion analyser, severity, synthetic fixtures + tests |
| D5 | 10-17 | expert system, `/api/v1/scan` end to end, ONNX int8 export |
| D6 | 10-18 | frontend scan UI, camera capture, Thai result cards |
| D7 | 10-19 | PWA offline, on-device ONNX, history, sync endpoint |
| D8 | 10-20 | Capacitor `.apk`, polish, accessibility pass |
| D9 | 10-21 | demo dataset, pitch script, buffer. Submit 10-22. |

Each day ends with a committed, pushed, independently testable slice. If a day
slips, the following day's scope is cut rather than the testing.

## 13. Risks

| risk | mitigation |
|---|---|
| The burn discriminator misfires on real disease photographs | Specificity is the headline metric and is measured on real data; the threshold is configurable and can be raised until specificity is acceptable. |
| Cross-source duplicates inflate the test score | pHash dedup before splitting; the manifest makes it auditable. |
| ONNX int8 drifts from the Python result | A parity test asserts agreement on a fixed input set within tolerance. |
| `other_disease` becomes a dumping ground that hides real misses | The evaluation reports it as its own row with its own precision and recall. |
| 4 GB VRAM limits the backbone | The architecture is fixed to MobileNetV3-Large up front rather than discovered by running out of memory on D3. |
| Capacitor build problems on D8 | The PWA is already installable and demoable on a phone, so the `.apk` is an enhancement, not the demo's critical path. |

## 14. Assumptions

1. Two knowledge-base records are added beyond the four supplied
   (`other_disease`, `physical_burn`); the four given records are used verbatim.
2. Yield forecasting is Phase 2 and absent from this spec.
3. Kaggle and gated-HuggingFace sources stay disabled until credentials are
   provided; `sources.py` is written so enabling them is a configuration change.
4. The repository is private, matching the project default.
