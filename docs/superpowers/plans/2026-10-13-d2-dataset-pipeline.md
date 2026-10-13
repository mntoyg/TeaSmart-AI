# TeaSmart AI — D2 Dataset Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the three credential-free sources into one deduplicated, stratified, auditable training corpus of five canonical classes.

**Architecture:** A separate `ml/` package with its own venv, so training dependencies never reach the service. Four pure stages behind a single CLI: download into `data/raw/`, normalise into `data/interim/<source>/<canonical>/`, perceptual-hash to collapse cross-source duplicates, then write `data/processed/manifest.csv` with the split assignment. Nothing downstream reads the raw archives; the manifest is the contract.

**Tech Stack:** Python 3.12, huggingface_hub, pyarrow, requests, Pillow, NumPy, imagehash, pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-teasmart-ai-design.md` (sections 4, 5, 6)

## Global Constraints

- Python 3.12; `ml/` gets its own `ml/requirements.txt` and `ml/.venv`, separate from `backend/`.
- Five canonical trained classes: `grey_blight`, `brown_blight`, `algal_spot`, `healthy`, `other_disease`. `physical_burn` is never a trained class.
- Source label mapping, verbatim from spec section 5:
  - `gray_blight`, `gray_light`, `Gray Blight` → `grey_blight`
  - `brown_blight`, `Brown Blight` → `brown_blight`
  - `algal_spot`, `algal_leaf`, `Algal Leaf Spot` → `algal_spot`
  - `healthy`, `Healthy` → `healthy`
  - `anthracnose`, `bird_eye_spot`, `red_spot`, `red_leaf_spot`, `Red Leaf Spot`, `helopeltis`, `Helopeltis`, `white_spot` → `other_disease`
- Sources in scope: `agml`, `yunusserhat`, `mendeley_mz598`. `mendeley_d2xy`, `mendeley_94fz`, both Kaggle sources and `hf_ttkqwe123` are registered but disabled; `mendeley_sjmy` is dropped (HTTP 451).
- pHash with Hamming distance ≤ 5 counts as a duplicate; duplicates collapse to the highest-resolution copy.
- Splits are stratified 70/15/15 **after** dedup, seed `42`.
- Everything under `data/` stays gitignored. Only a committed summary under `docs/eval/` leaves the machine.
- The suite runs with `filterwarnings = error`, as `backend/` does.

## Review Focus

1. A source label absent from the mapping must raise, never fall through to `other_disease` — a silent fallback would hide an upstream dataset change behind plausible-looking advice — Task 1.
2. A near-duplicate across sources (the same photo recompressed or resized) must group; hashing bytes or MD5 would miss it and leak the test set into training — Task 4.
3. A duplicate group must land entirely inside one split, or the reported accuracy is inflated by images the model already saw — Task 5.
4. A corrupt or unreadable image inside a downloaded archive must be skipped and counted, not abort an ingest that cost 900 MB of download — Task 3.
5. Re-running the CLI must be idempotent: no re-download of a complete archive, no doubled corpus — Task 6.
6. A canonical class with fewer images than the split needs (3 or fewer) must still produce a usable split rather than an empty validation or test set — Task 5.
7. The label order embedded in a parquet file must be verified against the registry, because every label in that source is wrong together if upstream reorders them — Task 2.

---

### Task 1: `ml/` scaffold and the canonical class map

**Files:**
- Create: `ml/requirements.txt`, `ml/pytest.ini`, `ml/teasmart_ml/__init__.py`, `ml/teasmart_ml/classes.py`
- Create: `ml/tests/__init__.py`
- Modify: `.gitignore` (add `ml/.venv/`)
- Test: `ml/tests/test_classes.py`

**Interfaces:**
- Consumes: `backend/app/kb/diseases.json` (read-only, for the drift test).
- Produces:
  - `CANONICAL_CLASSES: tuple[str, ...]` — the five names in `class_id` order: `("grey_blight", "brown_blight", "algal_spot", "healthy", "other_disease")`
  - `SOURCE_LABEL_MAP: Mapping[str, str]` — every source label from Global Constraints to its canonical name
  - `UnmappedLabelError(KeyError)`
  - `to_canonical(label: str) -> str` — raises `UnmappedLabelError` on anything unmapped

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_classes.py
def test_the_five_canonical_classes_are_in_class_id_order():
    assert CANONICAL_CLASSES == (
        "grey_blight", "brown_blight", "algal_spot", "healthy", "other_disease",
    )

@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("gray_blight", "grey_blight"), ("gray_light", "grey_blight"),
        ("Gray Blight", "grey_blight"), ("brown_blight", "brown_blight"),
        ("Brown Blight", "brown_blight"), ("algal_spot", "algal_spot"),
        ("algal_leaf", "algal_spot"), ("Algal Leaf Spot", "algal_spot"),
        ("healthy", "healthy"), ("Healthy", "healthy"),
        ("anthracnose", "other_disease"), ("bird_eye_spot", "other_disease"),
        ("red_spot", "other_disease"), ("red_leaf_spot", "other_disease"),
        ("Red Leaf Spot", "other_disease"), ("helopeltis", "other_disease"),
        ("Helopeltis", "other_disease"), ("white_spot", "other_disease"),
    ],
)
def test_every_source_label_maps_to_its_canonical_class(label, expected):
    assert to_canonical(label) == expected

def test_an_unmapped_label_raises_instead_of_becoming_other_disease():
    # A silent fallback would absorb an upstream relabelling and keep answering
    # confidently with advice derived from the wrong class.
    with pytest.raises(UnmappedLabelError):
        to_canonical("tea_mosquito_bug")

def test_the_canonical_classes_match_the_backend_knowledge_base():
    # Stage 6 looks advice up by these names. If the two drift apart, the
    # classifier emits a class the expert system cannot answer.
    kb = json.loads(Path("../backend/app/kb/diseases.json").read_text(encoding="utf-8"))
    kb_trainable = {r["canonical"] for r in kb} - {"physical_burn"}
    assert kb_trainable == set(CANONICAL_CLASSES)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_classes.py -v`
Expected: collection error — `teasmart_ml.classes` does not exist.

- [ ] **Step 3: Write `ml/requirements.txt`, `ml/pytest.ini`, create `ml/.venv` and install**

Pin: `huggingface_hub`, `pyarrow`, `requests`, `pillow`, `numpy`, `imagehash`, `pytest`. `pytest.ini` mirrors `backend/pytest.ini`: `pythonpath = .`, `testpaths = tests`, `filterwarnings = error`.

- [ ] **Step 4: Implement `CANONICAL_CLASSES`, `SOURCE_LABEL_MAP`, `UnmappedLabelError` and `to_canonical()` in `ml/teasmart_ml/classes.py`**

Resolve the knowledge-base path relative to this file, not the process cwd.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_classes.py -v`
Expected: 21 passed.

- [ ] **Step 6: Commit**

```bash
git add ml .gitignore
git commit -m "feat(ml): add canonical class map checked against the knowledge base"
```

---

### Task 2: Source registry and downloaders

**Files:**
- Create: `ml/teasmart_ml/datasets/__init__.py`, `ml/teasmart_ml/datasets/sources.py`
- Test: `ml/tests/test_sources.py`

**Interfaces:**
- Consumes: `CANONICAL_CLASSES` from Task 1.
- Produces:
  - `@dataclass(frozen=True) HFParquetSource` with fields `source_id: str`, `repo_id: str`, `files: tuple[str, ...]`, `label_names: tuple[str, ...]`, `enabled: bool = True`
  - `@dataclass(frozen=True) MendeleyZipSource` with fields `source_id: str`, `dataset_id: str`, `version: int`, `filename: str`, `enabled: bool = True`
  - `SOURCES: Mapping[str, HFParquetSource | MendeleyZipSource]` — keyed by `source_id`
  - `enabled_sources() -> tuple[str, ...]`
  - `resolve_mendeley_download(dataset_id: str, version: int, filename: str, *, fetch_json) -> str` — returns the file's `download_url`; raises `SourceUnavailableError` when the API errors or the filename is absent
  - `download_source(source_id: str, raw_root: Path, *, fetch_json=..., fetch_file=..., hf_download=...) -> tuple[Path, ...]` — the local paths it put in `raw_root/<source_id>/`, skipping any that already exist
  - `SourceUnavailableError(RuntimeError)`, `LabelDriftError(RuntimeError)`

  Registry contents, from the 2026-10-13 probe:
  - `agml`: `Project-AgML/tea_leaf_disease_classification`, files `("data/train-00000-of-00001.parquet",)`, labels `("algal_spot", "brown_blight", "gray_blight", "healthy", "helopeltis", "red_spot")`
  - `yunusserhat`: `yunusserhat/tea_sickness_dataset`, files `("data/train-00000-of-00002.parquet", "data/train-00001-of-00002.parquet", "data/validation-00000-of-00001.parquet", "data/test-00000-of-00001.parquet")`, labels `("Anthracnose", "algal_leaf", "bird_eye_spot", "brown_blight", "gray_light", "healthy", "red_leaf_spot", "white_spot")`
  - `mendeley_mz598`: dataset `mz598gxfw9`, version `1`, filename `Tea Leaf Diseases.zip`
  - disabled: `mendeley_d2xy` (`d2xybhfw59` v1, `Tea Leaf Dataset.zip`), `mendeley_94fz` (`94fzcdz8gz` v1, `Tea Leaf Dataset.rar`)

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_sources.py
def test_only_the_three_credential_free_sources_are_enabled():
    assert set(enabled_sources()) == {"agml", "yunusserhat", "mendeley_mz598"}

def test_every_registry_label_is_mappable_to_a_canonical_class():
    # A label in the registry that to_canonical cannot resolve is a registry bug
    # that would otherwise surface only after a 900MB download.
    for source in SOURCES.values():
        for label in getattr(source, "label_names", ()):
            assert to_canonical(label) in CANONICAL_CLASSES

def test_resolve_mendeley_download_picks_the_url_for_the_named_file():
    payload = [
        {"filename": "data.yaml", "content_details": {"download_url": "https://x/yaml"}},
        {"filename": "Tea Leaf Diseases.zip", "content_details": {"download_url": "https://x/zip"}},
    ]
    url = resolve_mendeley_download("mz598gxfw9", 1, "Tea Leaf Diseases.zip", fetch_json=lambda _: payload)
    assert url == "https://x/zip"

def test_resolve_mendeley_download_raises_when_the_api_returns_an_error():
    # The probe found sjmy6k24d6 answering {"error": 451}; that must be a clear
    # failure, not a crash deep inside a download loop.
    with pytest.raises(SourceUnavailableError):
        resolve_mendeley_download("sjmy6k24d6", 3, "whatever.zip", fetch_json=lambda _: {"error": 451})

def test_resolve_mendeley_download_raises_when_the_filename_is_absent():
    with pytest.raises(SourceUnavailableError):
        resolve_mendeley_download("mz598gxfw9", 1, "absent.zip", fetch_json=lambda _: [])

def test_download_skips_a_file_that_is_already_present(tmp_path):
    existing = tmp_path / "agml" / "data" / "train-00000-of-00001.parquet"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already here")
    def fail(*_a, **_k):
        raise AssertionError("should not download an existing file")
    paths = download_source("agml", tmp_path, hf_download=fail)
    assert paths == (existing,)
    assert existing.read_bytes() == b"already here"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_sources.py -v`
Expected: collection error — `teasmart_ml.datasets.sources` does not exist.

- [ ] **Step 3: Implement the dataclasses, `SOURCES`, `enabled_sources()`, `resolve_mendeley_download()` and `download_source()` in `ml/teasmart_ml/datasets/sources.py`**

`resolve_mendeley_download` reads `https://data.mendeley.com/public-api/datasets/{dataset_id}/files?folder_id=root&version={version}` and takes the matching entry's `content_details.download_url`; the file id is resolved at call time rather than pinned, so an upstream re-upload does not silently 404. The network calls are injected as `fetch_json` / `fetch_file` / `hf_download` parameters, which is what lets every test above run offline.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_sources.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add ml/teasmart_ml/datasets ml/tests/test_sources.py
git commit -m "feat(ml): add source registry with injectable downloaders"
```

---

### Task 3: Normalise every source into canonical class folders

**Files:**
- Create: `ml/teasmart_ml/datasets/ingest.py`
- Test: `ml/tests/test_ingest.py`, `ml/tests/fixtures.py`

**Interfaces:**
- Consumes: `to_canonical()` (Task 1), `SOURCES`, `LabelDriftError` (Task 2).
- Produces:
  - `@dataclass(frozen=True) IngestReport` with fields `source_id: str`, `written: int`, `skipped_corrupt: int`, `per_class: Mapping[str, int]`
  - `ingest_parquet_source(source: HFParquetSource, files: Sequence[Path], interim_root: Path) -> IngestReport`
  - `ingest_yolo_zip_source(source: MendeleyZipSource, archive: Path, interim_root: Path) -> IngestReport`
  - `make_parquet(rows, label_names, path)` and `make_yolo_zip(entries, path)` in `ml/tests/fixtures.py`

  Both writers put files at `interim_root/<source_id>/<canonical>/<source_id>-<index>.jpg`.

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_ingest.py
def test_parquet_rows_land_in_their_canonical_class_folder(tmp_path):
    parquet = make_parquet(
        rows=[(green_png(), 2), (green_png(), 3), (green_png(), 4)],
        label_names=("algal_spot", "brown_blight", "gray_blight", "healthy", "helopeltis", "red_spot"),
        path=tmp_path / "t.parquet",
    )
    report = ingest_parquet_source(SOURCES["agml"], [parquet], tmp_path / "interim")
    assert report.written == 3
    assert report.per_class == {"grey_blight": 1, "healthy": 1, "other_disease": 1}
    assert (tmp_path / "interim" / "agml" / "grey_blight").is_dir()

def test_a_parquet_whose_embedded_labels_disagree_with_the_registry_raises(tmp_path):
    # If upstream reorders its ClassLabel, every label in that source is wrong
    # together, and nothing downstream could tell.
    parquet = make_parquet(
        rows=[(green_png(), 0)],
        label_names=("healthy", "algal_spot", "brown_blight", "gray_blight", "helopeltis", "red_spot"),
        path=tmp_path / "t.parquet",
    )
    with pytest.raises(LabelDriftError):
        ingest_parquet_source(SOURCES["agml"], [parquet], tmp_path / "interim")

def test_a_corrupt_image_is_skipped_and_counted_not_fatal(tmp_path):
    parquet = make_parquet(
        rows=[(green_png(), 3), (b"not an image at all", 3), (green_png(), 3)],
        label_names=SOURCES["agml"].label_names,
        path=tmp_path / "t.parquet",
    )
    report = ingest_parquet_source(SOURCES["agml"], [parquet], tmp_path / "interim")
    assert report.written == 2
    assert report.skipped_corrupt == 1

def test_a_yolo_archive_maps_its_class_folders(tmp_path):
    archive = make_yolo_zip(
        entries=[("train/images/a.jpg", green_jpeg(), "Gray Blight"),
                 ("valid/images/b.jpg", green_jpeg(), "Healthy")],
        path=tmp_path / "t.zip",
    )
    report = ingest_yolo_zip_source(SOURCES["mendeley_mz598"], archive, tmp_path / "interim")
    assert report.per_class == {"grey_blight": 1, "healthy": 1}

def test_an_archive_entry_escaping_the_extract_root_is_refused(tmp_path):
    # A zip from the internet is untrusted input; a "../" member must not write
    # outside the directory we chose for it.
    archive = make_yolo_zip(entries=[("../../escaped.jpg", green_jpeg(), "Healthy")], path=tmp_path / "evil.zip")
    with pytest.raises(ValueError):
        ingest_yolo_zip_source(SOURCES["mendeley_mz598"], archive, tmp_path / "interim")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_ingest.py -v`
Expected: collection error — `teasmart_ml.datasets.ingest` does not exist.

- [ ] **Step 3: Implement `make_parquet()`, `make_yolo_zip()`, `green_png()`, `green_jpeg()` in `ml/tests/fixtures.py`**

`make_parquet` writes an `image`/`label` table and stores `label_names` in the parquet schema metadata under the key `huggingface`, shaped as the HF `features` JSON, which is what the drift check reads.

- [ ] **Step 4: Implement `IngestReport`, `ingest_parquet_source()` and `ingest_yolo_zip_source()` in `ml/teasmart_ml/datasets/ingest.py`**

The YOLO source carries its class in the path, so derive the label from the archive member's directory and resolve each member against the extract root before writing — reject any member that lands outside it. Decode every image through Pillow, convert to RGB, re-encode as JPEG quality 95.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_ingest.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add ml/teasmart_ml/datasets/ingest.py ml/tests
git commit -m "feat(ml): normalise every source into canonical class folders"
```

---

### Task 4: Perceptual-hash dedup

**Files:**
- Create: `ml/teasmart_ml/datasets/dedup.py`
- Test: `ml/tests/test_dedup.py`

**Interfaces:**
- Consumes: the fixture helpers from Task 3.
- Produces:
  - `phash_hex(path: Path) -> str`
  - `group_duplicates(paths: Sequence[Path], *, max_distance: int = 5) -> tuple[tuple[Path, ...], ...]` — every input appears in exactly one group, ordered highest-resolution first, so `group[0]` is the copy to keep
  - `hamming(a: str, b: str) -> int`

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_dedup.py
def test_the_same_photo_recompressed_is_detected_as_a_duplicate(tmp_path):
    # This is the real case: several sources derive from one Roboflow upload, so
    # the duplicates differ in bytes while being the same image. Hashing bytes
    # or MD5 would miss every one of them.
    original = write_leaf_photo(tmp_path / "a.jpg", size=(512, 512), quality=95)
    recompressed = write_leaf_photo(tmp_path / "b.jpg", size=(512, 512), quality=40)
    assert original.read_bytes() != recompressed.read_bytes()
    assert hamming(phash_hex(original), phash_hex(recompressed)) <= 5

def test_a_resized_copy_is_detected_as_a_duplicate(tmp_path):
    big = write_leaf_photo(tmp_path / "big.jpg", size=(512, 512))
    small = write_leaf_photo(tmp_path / "small.jpg", size=(256, 256))
    assert hamming(phash_hex(big), phash_hex(small)) <= 5

def test_two_different_leaves_are_not_grouped(tmp_path):
    a = write_leaf_photo(tmp_path / "a.jpg", seed=1)
    b = write_leaf_photo(tmp_path / "b.jpg", seed=2)
    assert len(group_duplicates([a, b])) == 2

def test_a_group_keeps_the_highest_resolution_copy_first(tmp_path):
    small = write_leaf_photo(tmp_path / "small.jpg", size=(256, 256))
    big = write_leaf_photo(tmp_path / "big.jpg", size=(512, 512))
    (group,) = group_duplicates([small, big])
    assert group[0] == big

def test_every_input_appears_in_exactly_one_group(tmp_path):
    paths = [write_leaf_photo(tmp_path / f"{i}.jpg", seed=i) for i in range(5)]
    groups = group_duplicates(paths)
    assert sorted(p for g in groups for p in g) == sorted(paths)
```

`write_leaf_photo(path, *, size=(512, 512), quality=95, seed=0)` lives in `ml/tests/fixtures.py` and renders a deterministic textured leaf — a flat colour hashes identically for every seed and would make these tests meaningless.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_dedup.py -v`
Expected: collection error — `teasmart_ml.datasets.dedup` does not exist.

- [ ] **Step 3: Implement `write_leaf_photo()` in `ml/tests/fixtures.py`, then `phash_hex()`, `hamming()` and `group_duplicates()` in `ml/teasmart_ml/datasets/dedup.py`**

`imagehash.phash` for the hash. Group by single-linkage over the distance threshold, so A-B and B-C put all three together; sort each group by pixel area descending.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_dedup.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add ml/teasmart_ml/datasets/dedup.py ml/tests
git commit -m "feat(ml): group cross-source duplicates by perceptual hash"
```

---

### Task 5: Manifest and the stratified split

**Files:**
- Create: `ml/teasmart_ml/datasets/manifest.py`
- Test: `ml/tests/test_manifest.py`

**Interfaces:**
- Consumes: `group_duplicates()`, `phash_hex()` (Task 4); `CANONICAL_CLASSES` (Task 1).
- Produces:
  - `@dataclass(frozen=True) ManifestRow` with fields `path: str`, `canonical: str`, `source: str`, `phash: str`, `width: int`, `height: int`, `split: str`
  - `build_manifest(interim_root: Path, *, seed: int = 42, ratios: tuple[float, float, float] = (0.70, 0.15, 0.15)) -> tuple[ManifestRow, ...]`
  - `write_manifest(rows: Sequence[ManifestRow], out_csv: Path) -> None` — header `path,canonical,source,phash,width,height,split`
  - `summarise(rows: Sequence[ManifestRow]) -> Mapping[str, Mapping[str, int]]` — per canonical class, counts per split

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_manifest.py
def test_duplicates_are_collapsed_before_the_split(tmp_path):
    root = build_interim(tmp_path, {"healthy": [("a", 512), ("a", 256), ("b", 512)]})
    rows = build_manifest(root)
    assert len(rows) == 2                      # one of the two copies of "a" is dropped
    assert {r.width for r in rows} == {512}    # and the survivor is the larger one

def test_each_class_is_split_seventy_fifteen_fifteen(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(100), "grey_blight": distinct(100)})
    rows = build_manifest(root)
    for canonical in ("healthy", "grey_blight"):
        counts = Counter(r.split for r in rows if r.canonical == canonical)
        assert counts == {"train": 70, "val": 15, "test": 15}

def test_no_perceptual_hash_appears_in_two_splits(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(40)})
    rows = build_manifest(root)
    by_hash = defaultdict(set)
    for row in rows:
        by_hash[row.phash].add(row.split)
    assert all(len(splits) == 1 for splits in by_hash.values())

def test_the_split_is_deterministic_for_a_given_seed(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(30)})
    first = {(r.path, r.split) for r in build_manifest(root, seed=42)}
    assert first == {(r.path, r.split) for r in build_manifest(root, seed=42)}
    assert first != {(r.path, r.split) for r in build_manifest(root, seed=7)}

def test_a_class_with_three_images_still_gets_one_in_every_split(tmp_path):
    # 70/15/15 of three rounds validation and test to zero. An empty test split
    # would silently drop that class from every metric we report.
    root = build_interim(tmp_path, {"other_disease": distinct(3)})
    counts = Counter(r.split for r in build_manifest(root))
    assert counts == {"train": 1, "val": 1, "test": 1}

def test_a_class_with_one_image_puts_it_in_train(tmp_path):
    root = build_interim(tmp_path, {"other_disease": distinct(1)})
    assert [r.split for r in build_manifest(root)] == ["train"]

def test_the_manifest_csv_carries_the_agreed_header(tmp_path):
    rows = build_manifest(build_interim(tmp_path, {"healthy": distinct(4)}))
    out = tmp_path / "manifest.csv"
    write_manifest(rows, out)
    assert out.read_text(encoding="utf-8").splitlines()[0] == (
        "path,canonical,source,phash,width,height,split"
    )
```

`build_interim(root, spec)` and `distinct(n)` live in `ml/tests/fixtures.py`: `build_interim` lays out `root/<source>/<canonical>/` files from a mapping of canonical name to a list of `(image_key, size)` pairs, where the same key renders the same photo, and `distinct(n)` returns `n` pairs with distinct keys.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_manifest.py -v`
Expected: collection error — `teasmart_ml.datasets.manifest` does not exist.

- [ ] **Step 3: Implement `build_interim()` and `distinct()` in `ml/tests/fixtures.py`, then `ManifestRow`, `build_manifest()`, `write_manifest()` and `summarise()` in `ml/teasmart_ml/datasets/manifest.py`**

Dedup first over all sources at once, keeping each group's first member; then, per canonical class, shuffle with `numpy.random.default_rng(seed)` and slice by the ratios. Allocate the small classes by filling train, val, test in that order so one image goes to train, two go to train and val, and three fill all of them.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_manifest.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add ml/teasmart_ml/datasets/manifest.py ml/tests
git commit -m "feat(ml): build the deduplicated stratified manifest"
```

---

### Task 6: CLI, and the real corpus

**Files:**
- Create: `ml/teasmart_ml/cli.py`
- Create: `docs/eval/2026-10-13-dataset-summary.md`
- Test: `ml/tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `python -m teasmart_ml.cli prepare [--raw data/raw] [--interim data/interim] [--out data/processed/manifest.csv] [--seed 42]`, and `prepare(raw_root, interim_root, out_csv, *, seed=42, downloader=download_source) -> Mapping[str, Mapping[str, int]]`

- [ ] **Step 1: Write the failing tests**

```python
# ml/tests/test_cli.py
def test_prepare_is_idempotent(tmp_path):
    # A second run must not re-download a complete archive or double the corpus:
    # the first run costs 900MB and twenty minutes.
    calls = []
    def downloader(source_id, raw_root, **_):
        calls.append(source_id)
        return seed_fake_source(source_id, raw_root)
    first = prepare(tmp_path / "raw", tmp_path / "interim", tmp_path / "m.csv", downloader=downloader)
    first_csv = (tmp_path / "m.csv").read_text(encoding="utf-8")
    second = prepare(tmp_path / "raw", tmp_path / "interim", tmp_path / "m.csv", downloader=downloader)
    second_csv = (tmp_path / "m.csv").read_text(encoding="utf-8")
    assert first == second
    assert first_csv == second_csv
    assert calls == ["agml", "yunusserhat", "mendeley_mz598"] * 2  # asked twice, downloaded once

def test_prepare_reports_counts_per_class_and_split(tmp_path):
    summary = prepare(
        tmp_path / "raw", tmp_path / "interim", tmp_path / "m.csv", downloader=seed_fake_source_for
    )
    assert set(summary) <= set(CANONICAL_CLASSES)
    assert all(set(splits) == {"train", "val", "test"} for splits in summary.values())
```

`seed_fake_source_for(source_id, raw_root, **_)` lives in `ml/tests/fixtures.py`: it
writes a small synthetic archive or parquet for that source into `raw_root` and
returns the paths, so the CLI runs end to end offline. The idempotency test wraps
it to record the calls. Note what the assertion pins: `prepare` may *ask* for
every source on both runs, but `download_source` must skip a file already on
disk, which Task 2 already tests.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: collection error — `teasmart_ml.cli` does not exist.

- [ ] **Step 3: Implement `prepare()` and the `argparse` entry point in `ml/teasmart_ml/cli.py`**

Download, ingest each enabled source, build the manifest, write it, and return the summary. Ingest writes into a per-source folder it clears first, which is what makes a second run produce the same corpus rather than a doubled one.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ml && .venv/Scripts/python.exe -m pytest tests/test_cli.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the whole `ml` suite**

Run: `cd ml && .venv/Scripts/python.exe -m pytest -v`
Expected: 46 passed.

- [ ] **Step 6: Run the real pipeline**

Run: `cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare`
Expected: roughly 920 MB downloaded across the three sources, and a printed summary whose five classes each have train, val and test counts. Record the actual numbers — including how many duplicates were collapsed and how many corrupt images were skipped — rather than the numbers this plan guessed.

- [ ] **Step 7: Write `docs/eval/2026-10-13-dataset-summary.md`**

The real counts per class per split, the duplicate and corrupt tallies, the three source versions, and the seed. This is the evidence behind every accuracy figure D3 reports.

- [ ] **Step 8: Commit and push**

```bash
git add ml/teasmart_ml/cli.py ml/tests/test_cli.py docs/eval
git commit -m "feat(ml): add the prepare CLI and record the real corpus"
git push
```

---

## D2 Done When

- `cd ml && .venv/Scripts/python.exe -m pytest -v` is green, and `backend`'s 40 still are.
- `data/processed/manifest.csv` exists, every row has a split, and no pHash spans two splits.
- `docs/eval/2026-10-13-dataset-summary.md` holds the real counts.
- `data/` is still absent from `git status`.
