# TeaSmart AI — D1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the TeaSmart AI backend foundation — a running FastAPI service, the Thai knowledge base behind an endpoint, hardened image loading, and the stage-1 quality gate — pushed to a private GitHub repository.

**Architecture:** A FastAPI app assembled by a `create_app()` factory, with configuration in one `Settings` object and each pipeline stage as a pure function in `app/services/`. D1 delivers stages 1 (quality gate) and 6 (expert system) plus the hardened decode path every later stage consumes; stages 2-5 arrive on D4-D5.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2 + pydantic-settings, Pillow, NumPy, opencv-python-headless, pytest + httpx.

**Spec:** `docs/superpowers/specs/2026-10-13-teasmart-ai-design.md`

## Global Constraints

- Python 3.12; dependencies pinned in `backend/requirements.txt`.
- Code, comments and docstrings in English. Thai appears only in knowledge-base content and in user-facing messages.
- Uploads are accepted by magic-byte sniffing, never by file extension or the client-supplied content type.
- Byte cap `max_upload_bytes = 8388608` (8 MiB); pixel cap `max_image_pixels = 40000000`.
- Blur threshold `80.0` (variance of Laplacian); exposure mean band `40.0`-`215.0`; clipped-pixel ceiling `0.10`.
- Every decoded image is re-encoded through Pillow so EXIF and any embedded payload are dropped before it reaches other code.
- Knowledge-base records 0-3 use the supplied Thai text verbatim, byte for byte.
- No secrets in the repository: `.env` is gitignored, `.env.example` is committed.
- `data/`, `*.onnx`, `*.pt` and `*.pth` are gitignored.
- CORS is restricted to an explicit allowlist from configuration; never `*`.
- `model_version` is `teasmart-v1`.

## Review Focus

Input classes the spec implies but which no stage's happy path exercises. Each has a test pinned to the task that owns the code.

1. A non-image file renamed to `.jpg` (text, zip, or a polyglot) must be rejected on magic bytes, not decoded — Task 3.
2. A JPEG carrying EXIF orientation must come out visually upright, or every later crop and lesion measurement is rotated — Task 3.
3. Grayscale, RGBA, palette and CMYK inputs must convert to 3-channel RGB rather than crash a downstream shape assumption — Task 3.
4. A truncated or corrupt image must surface as a client error, never an unhandled 500 — Task 3.
5. A small file that decodes to enormous dimensions (decompression bomb) must be refused on the pixel cap even though it passes the byte cap — Task 3.
6. A dark image and a blurry image both depress the Laplacian variance, so exposure must be judged before blur or every night photo is reported as "blurry" — Task 4.

---

### Task 1: Project scaffold, health endpoint, private repository

**Files:**
- Create: `.gitignore`, `README.md`, `.env.example`
- Create: `backend/requirements.txt`, `backend/pytest.ini`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/main.py`
- Create: `backend/tests/__init__.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Settings` (pydantic-settings `BaseSettings`, env prefix `TEASMART_`) with fields `app_name: str = "TeaSmart AI"`, `model_version: str = "teasmart-v1"`, `cors_origins: list[str] = ["http://localhost:5173"]`, `max_upload_bytes: int = 8388608`, `max_image_pixels: int = 40000000`, `blur_threshold: float = 80.0`, `exposure_min_mean: float = 40.0`, `exposure_max_mean: float = 215.0`, `clip_max_pct: float = 0.10`, `kb_path: Path = Path("app/kb/diseases.json")`
  - `get_settings() -> Settings` — `functools.lru_cache`d
  - `create_app() -> FastAPI` in `app/main.py`, with `CORSMiddleware` from `settings.cors_origins`
  - `client` pytest fixture in `conftest.py` returning `fastapi.testclient.TestClient(create_app())`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_health.py
def test_health_reports_app_and_model_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "TeaSmart AI",
        "model_version": "teasmart-v1",
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: collection error — `app.main` does not exist.

- [ ] **Step 3: Write `backend/requirements.txt`**

Pin: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `pillow`, `numpy`, `opencv-python-headless`, `pytest`, `httpx`. Create the virtualenv at `backend/.venv` and install.

- [ ] **Step 4: Implement `Settings` and `get_settings()` in `backend/app/core/config.py`**

Field defaults exactly as in the Interfaces block above.

- [ ] **Step 5: Implement `create_app()` and `GET /health` in `backend/app/main.py`**

`/health` returns the three keys the test asserts, reading `app_name` and `model_version` from `get_settings()`.

- [ ] **Step 6: Write `.gitignore`**

Ignore: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.env`, `data/`, `*.onnx`, `*.pt`, `*.pth`, `node_modules/`, `dist/`, `.DS_Store`.

- [ ] **Step 7: Write `.env.example` and `README.md`**

`.env.example` lists every `TEASMART_`-prefixed variable with safe placeholder values and no real secrets. `README.md` covers the project purpose in two sentences, the setup commands, and how to run the tests.

- [ ] **Step 8: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: 1 passed.

- [ ] **Step 9: Commit**

```bash
git add .gitignore README.md .env.example backend/
git commit -m "feat(backend): add app factory, settings and health endpoint"
```

- [ ] **Step 10: Create the private GitHub repository and push**

```bash
gh repo create mntoyg/TeaSmart-AI --private --source=. --remote=origin --push
```

Then confirm the remote and that the repository is private:

```bash
git remote -v && gh repo view mntoyg/TeaSmart-AI --json isPrivate,url
```

Expected: `isPrivate` is `true`.

---

### Task 2: Knowledge base and `/api/v1/kb`

**Files:**
- Create: `backend/app/kb/diseases.json`
- Create: `backend/app/services/__init__.py`, `backend/app/services/expert.py`
- Create: `backend/app/api/__init__.py`, `backend/app/api/v1/__init__.py`, `backend/app/api/v1/kb.py`
- Modify: `backend/app/main.py` (register the router)
- Test: `backend/tests/test_expert.py`, `backend/tests/test_kb_api.py`

**Interfaces:**
- Consumes: `get_settings()` from Task 1.
- Produces:
  - `DiseaseRecord` (Pydantic `BaseModel`, `model_config = ConfigDict(extra="forbid")`) with fields `class_id: int`, `class_name: str`, `disease_name_th: str`, `pathogen: str`, `symptoms: str`, `immediate_action: str`, `cultural_control: str`, `chemical_treatment: str`, `preventive_measures: str`
  - `load_kb(path: Path) -> dict[str, DiseaseRecord]` — keyed by `class_name`, cached, raises `KeyError` on a duplicate `class_name`
  - `get_advice(class_name: str, kb: dict[str, DiseaseRecord]) -> DiseaseRecord` — raises `UnknownClassError` for an unmapped class
  - `GET /api/v1/kb` returning `list[DiseaseRecord]` ordered by `class_id`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_expert.py
def test_kb_has_six_records_covering_every_canonical_class():
    kb = load_kb(get_settings().kb_path)
    assert len(kb) == 6
    assert {r.class_id for r in kb.values()} == {0, 1, 2, 3, 4, 5}

def test_grey_blight_advice_is_the_supplied_thai_text():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("Tea Grey Blight", kb)
    assert record.pathogen == "Pestalotiopsis theae"
    assert record.disease_name_th == "โรคใบไหม้เทา"

def test_physical_burn_advice_prescribes_no_fungicide():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("Physical Burn / Sun Scorch", kb)
    assert record.pathogen.startswith("ไม่มีเชื้อก่อโรค")
    assert "ไม่ต้องพ่นสาร" in record.immediate_action

def test_unknown_class_raises():
    kb = load_kb(get_settings().kb_path)
    with pytest.raises(UnknownClassError):
        get_advice("Nonexistent Blight", kb)
```

```python
# backend/tests/test_kb_api.py
def test_kb_endpoint_returns_all_records_ordered_by_class_id(client):
    response = client.get("/api/v1/kb")
    assert response.status_code == 200
    body = response.json()
    assert [r["class_id"] for r in body] == [0, 1, 2, 3, 4, 5]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_expert.py tests/test_kb_api.py -v`
Expected: collection error — `app.services.expert` does not exist.

- [ ] **Step 3: Create `backend/app/kb/diseases.json` with exactly these six records**

Records 0-3 are the supplied text, unmodified. Records 4-5 are new.

```json
[
  {
    "class_id": 0,
    "class_name": "Tea Grey Blight",
    "disease_name_th": "โรคใบไหม้เทา",
    "pathogen": "Pestalotiopsis theae",
    "symptoms": "แผลจุดสีน้ำตาลขยายตัวเป็นวงสีน้ำตาลเทา ศูนย์กลางแผลสีเทาอ่อน มีจุดสีดำเล็กๆ (Acervuli) เรียงเป็นวง และขอบแผลสีน้ำตาลเข้ม",
    "immediate_action": "ตัดแต่งใบและกิ่งที่ติดเชื้อออกจากแปลงทันที และรวบรวมนำไปเผาทำลายภายนอกแปลง",
    "cultural_control": "ลดความบอบช้ำของใบจากการเก็บเกี่ยวด้วยเครื่องจักร ทำความสะอาดเครื่องมือตัดแต่ง และปรับการตัดแต่งกิ่งช่วงปลายฤดูหนาว",
    "chemical_treatment": "ฉีดพ่น สารผสมบอร์โด (Bordeaux mixture) หรือ คอปเปอร์ ออกซีคลอไรด์ (Copper Oxychloride) ความเข้มข้น 0.25%",
    "preventive_measures": "หลีกเลี่ยงการปล่อยให้แปลงชื้นแฉะและดินอัดแน่น ปรับปรุงระบบระบายน้ำในดิน"
  },
  {
    "class_id": 1,
    "class_name": "Tea Brown Blight",
    "disease_name_th": "โรคใบไหม้น้ำตาล",
    "pathogen": "Colletotrichum camelliae / Glomerella cingulata",
    "symptoms": "จุดแผลสีน้ำตาลเหลืองถึงสีน้ำตาลช็อกโกแลต เริ่มเกิดที่ขอบใบหรือปลายใบ แล้วลุกลามเป็นเนื้อเยื่อตายขนาดใหญ่",
    "immediate_action": "เก็บรวบรวมใบแห้งและใบที่ร่วงหล่นใต้ทรงพุ่มออกจากแปลงเพื่อลดปริมาณเชื้อสะสม",
    "cultural_control": "ตัดแต่งทรงพุ่มให้ลมถ่ายเทสะดวก ลดความอับชื้นในทรงพุ่ม และหลีกเลี่ยงการใส่ปุ๋ยไนโตรเจนสูงเกินไป",
    "chemical_treatment": "ฉีดพ่นด้วย คอปเปอร์ ออกซีคลอไรด์ (0.25%), คาร์เบนดาซิม (Carbendazim) หรือกลุ่มสาร DMI เช่น เฮกซาโคนาโซล (Hexaconazole)",
    "preventive_measures": "เว้นระยะปลูกให้เหมาะสม ปรับการบังร่มเงาไม่ให้แน่นทึบเกินไป"
  },
  {
    "class_id": 2,
    "class_name": "Algal Leaf Spot",
    "disease_name_th": "โรคจุดสาหร่าย / สนิมสาหร่าย",
    "pathogen": "Cephaleuros virescens",
    "symptoms": "จุดแผลนูนนูนสีส้มหรือสีน้ำตาลแดง ลักษณะคล้ายกำมะหยี่บนผิวหน้าใบ",
    "immediate_action": "ตัดแต่งกิ่งและใบที่เป็นโรคออกเพื่อเปิดให้แสงแดดส่องถึงทรงพุ่ม",
    "cultural_control": "จัดการไม้ยืนต้นบังร่มเงาให้แสงแดดส่องลงมายังทรงพุ่มชาอย่างเพียงพอ เนื่องจากสาหร่ายเจริญได้ดีในที่ร่มทึบ",
    "chemical_treatment": "ฉีดพ่นด้วย คอปเปอร์ ออกซีคลอไรด์ (0.25%) หลังการตัดแต่งกิ่ง",
    "preventive_measures": "บำรุงต้นชาให้สมบูรณ์ด้วยการใส่ปุ๋ยธาตุอาหารครบถ้วน (NPK และธาตุอาหารรอง) เนื่องจากพืชที่อ่อนแอจะติดเชื้อง่าย"
  },
  {
    "class_id": 3,
    "class_name": "Healthy",
    "disease_name_th": "ใบปกติ / สุขภาพดี",
    "pathogen": "None",
    "symptoms": "ใบสีเขียวสดใส ผิวใบเรียบ ไม่มีรอยแผลหรือจุดผิดปกติ",
    "immediate_action": "ไม่ต้องดำเนินการรักษา",
    "cultural_control": "ตรวจแปลงอย่างสม่ำเสมอ รักษาระดับความชื้นและการระบายอากาศ",
    "chemical_treatment": "ไม่ต้องใช้สารเคมีกำจัดโรคพืช",
    "preventive_measures": "ใส่ปุ๋ยบำรุงตามระยะและเฝ้าระวังด้วยระบบ AI สแกนแปลงประจำสัปดาห์"
  },
  {
    "class_id": 4,
    "class_name": "Other Disease",
    "disease_name_th": "ความผิดปกติอื่น ๆ (ไม่ตรงโรคหลัก)",
    "pathogen": "ไม่ระบุ (อาจเป็น Anthracnose, Bird Eye Spot, Red Leaf Spot, Helopeltis หรือความเสียหายจากแมลงศัตรูพืช)",
    "symptoms": "พบความผิดปกติบนใบ แต่ลักษณะแผลไม่ตรงกับโรคใบไหม้เทา ใบไหม้น้ำตาล หรือจุดสาหร่าย",
    "immediate_action": "เก็บตัวอย่างใบที่มีอาการใส่ถุงซิป บันทึกตำแหน่งแปลงและวันที่ แล้วส่งให้นักวิชาการเกษตรวินิจฉัยก่อนตัดสินใจใช้สารเคมี",
    "cultural_control": "แยกต้นที่มีอาการและเฝ้าระวังการลุกลาม ตัดแต่งใบที่มีอาการรุนแรงออกจากแปลง",
    "chemical_treatment": "ยังไม่แนะนำให้พ่นสารเคมี เนื่องจากยังไม่ทราบสาเหตุที่แท้จริง การพ่นผิดชนิดจะสิ้นเปลืองและเร่งให้เชื้อดื้อยา",
    "preventive_measures": "สแกนซ้ำทุก 3-5 วันเพื่อติดตามการเปลี่ยนแปลง และเก็บภาพเปรียบเทียบไว้ประกอบการวินิจฉัย"
  },
  {
    "class_id": 5,
    "class_name": "Physical Burn / Sun Scorch",
    "disease_name_th": "รอยไหม้ทางกายภาพ (แดดเผา / สารเคมี)",
    "pathogen": "ไม่มีเชื้อก่อโรค เกิดจากสภาพแวดล้อมหรือการจัดการแปลง",
    "symptoms": "แผลสีน้ำตาลฟางหรือสีแทนค่อนข้างสม่ำเสมอ ขอบแผลไล่เฉดนุ่มไม่มีขอบคม มักอยู่ที่ปลายใบหรือขอบใบด้านที่รับแดด ไม่มีวงซ้อนและไม่มีจุดดำเล็ก ๆ",
    "immediate_action": "ไม่ต้องพ่นสารป้องกันกำจัดโรคพืช ให้ตรวจสอบการให้น้ำและร่มเงาของแปลงบริเวณนั้นก่อน",
    "cultural_control": "เพิ่มร่มเงาในช่วงแดดจัด ให้น้ำช่วงเช้าหรือเย็นเพื่อลดความเครียดจากความร้อน และหลีกเลี่ยงการพ่นสารกลางวันที่แดดแรง",
    "chemical_treatment": "ไม่ต้องใช้สารกำจัดโรคพืช หากสาเหตุมาจากสารเคมี ให้ทบทวนชนิดสารและอัตราผสมที่ใช้ครั้งล่าสุด",
    "preventive_measures": "ตรวจสอบอัตราผสมสารทุกครั้งก่อนพ่น พ่นช่วงเช้าหรือเย็น และจัดการไม้บังร่มเงาให้เหมาะกับฤดูกาล"
  }
]
```

- [ ] **Step 4: Implement `DiseaseRecord`, `UnknownClassError`, `load_kb()` and `get_advice()` in `backend/app/services/expert.py`**

`load_kb` reads the file as UTF-8, validates each record through `DiseaseRecord`, and raises on a duplicate `class_name`.

- [ ] **Step 5: Implement the router in `backend/app/api/v1/kb.py` and register it in `create_app()`**

Router prefix `/api/v1`, `response_model=list[DiseaseRecord]`, sorted by `class_id`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_expert.py tests/test_kb_api.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit and push**

```bash
git add backend/app/kb backend/app/services backend/app/api backend/app/main.py backend/tests
git commit -m "feat(kb): add six-record Thai knowledge base and /api/v1/kb"
git push
```

---

### Task 3: Hardened image loading

**Files:**
- Create: `backend/app/core/images.py`
- Modify: `backend/app/main.py` (exception handlers)
- Test: `backend/tests/test_images.py`, `backend/tests/fixtures.py`

**Interfaces:**
- Consumes: `get_settings()` from Task 1.
- Produces:
  - `SUPPORTED_MIME: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp"})`
  - `sniff_mime(data: bytes) -> str | None` — magic bytes only; ignores any declared content type
  - `decode_image(data: bytes, *, max_bytes: int, max_pixels: int) -> numpy.ndarray` — returns a C-contiguous `uint8` array of shape `(H, W, 3)` in RGB, with EXIF orientation applied and all metadata dropped
  - `UnsupportedImageError`, `ImageTooLargeError`, `CorruptImageError` — all subclasses of `ImageLoadError`
  - `make_test_image(...) -> bytes` in `tests/fixtures.py`, the fixture factory Task 4 also uses

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_images.py
def test_rejects_a_text_file_renamed_as_an_image():
    with pytest.raises(UnsupportedImageError):
        decode_image(b"#!/bin/sh\necho pwned\n", max_bytes=8388608, max_pixels=40000000)

def test_rejects_a_zip_polyglot():
    with pytest.raises(UnsupportedImageError):
        decode_image(b"PK\x03\x04" + b"\x00" * 64, max_bytes=8388608, max_pixels=40000000)

def test_rejects_payload_over_the_byte_cap():
    with pytest.raises(ImageTooLargeError):
        decode_image(make_test_image(size=(64, 64)), max_bytes=10, max_pixels=40000000)

def test_rejects_a_decompression_bomb_within_the_byte_cap():
    bomb = make_test_image(size=(12000, 12000), colour=(0, 0, 0))
    assert len(bomb) < 8388608
    with pytest.raises(ImageTooLargeError):
        decode_image(bomb, max_bytes=8388608, max_pixels=40000000)

def test_rejects_a_truncated_jpeg():
    data = make_test_image(size=(256, 256), fmt="JPEG")
    with pytest.raises(CorruptImageError):
        decode_image(data[: len(data) // 3], max_bytes=8388608, max_pixels=40000000)

@pytest.mark.parametrize("mode", ["L", "RGBA", "P", "CMYK"])
def test_every_colour_mode_decodes_to_three_channel_rgb(mode):
    image = decode_image(
        make_test_image(size=(32, 48), mode=mode), max_bytes=8388608, max_pixels=40000000
    )
    assert image.shape == (48, 32, 3)
    assert image.dtype == numpy.uint8

def test_applies_exif_orientation():
    # A 64x32 landscape JPEG tagged Orientation=6 must come back 32 wide by 64 tall.
    image = decode_image(
        make_test_image(size=(64, 32), fmt="JPEG", exif_orientation=6),
        max_bytes=8388608,
        max_pixels=40000000,
    )
    assert image.shape[:2] == (64, 32)

def test_strips_exif_so_no_metadata_survives():
    data = make_test_image(size=(32, 32), fmt="JPEG", exif_orientation=6)
    assert PIL.Image.open(io.BytesIO(data)).getexif()
    decoded = decode_image(data, max_bytes=8388608, max_pixels=40000000)
    assert isinstance(decoded, numpy.ndarray)  # no PIL object, so no metadata, escapes
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_images.py -v`
Expected: collection error — `app.core.images` does not exist.

- [ ] **Step 3: Implement `make_test_image()` in `backend/tests/fixtures.py`**

Signature: `make_test_image(*, size=(64, 64), mode="RGB", fmt="PNG", colour=(34, 139, 34), exif_orientation=None) -> bytes`. Builds the image with Pillow and returns the encoded bytes; when `exif_orientation` is given it writes tag `0x0112` into the saved EXIF.

- [ ] **Step 4: Implement `sniff_mime()`, the error classes and `decode_image()` in `backend/app/core/images.py`**

Order matters and is the point of the tests: check the byte cap, then sniff magic bytes, then open with Pillow under `Image.MAX_IMAGE_PIXELS = max_pixels`, then `ImageOps.exif_transpose`, then convert to `RGB`, then `numpy.asarray`. Pillow's `DecompressionBombError` maps to `ImageTooLargeError`; `UnidentifiedImageError` and `OSError` map to `CorruptImageError`.

- [ ] **Step 5: Register exception handlers in `create_app()`**

`UnsupportedImageError` to `415`, `ImageTooLargeError` to `413`, `CorruptImageError` to `400`. Each body is `{"detail": "<english reason>", "detail_th": "<thai message>"}`. No traceback or internal path reaches the client.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_images.py -v`
Expected: 11 passed.

- [ ] **Step 7: Commit and push**

```bash
git add backend/app/core/images.py backend/app/main.py backend/tests
git commit -m "feat(core): add magic-byte, bomb-safe image decoding"
git push
```

---

### Task 4: Stage 1 — quality gate

**Files:**
- Create: `backend/app/services/quality.py`
- Test: `backend/tests/test_quality.py`

**Interfaces:**
- Consumes: `decode_image()` and `make_test_image()` from Task 3; thresholds from `Settings` (Task 1).
- Produces:
  - `QualityResult` (frozen dataclass) with fields `passed: bool`, `blur_score: float`, `exposure_mean: float`, `clipped_pct: float`, `reason: str | None`, `reason_th: str | None`
  - `assess_quality(image: numpy.ndarray, *, blur_threshold: float, exposure_min_mean: float, exposure_max_mean: float, clip_max_pct: float) -> QualityResult`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_quality.py
THRESHOLDS = dict(
    blur_threshold=80.0,
    exposure_min_mean=40.0,
    exposure_max_mean=215.0,
    clip_max_pct=0.10,
)

def test_a_sharp_well_exposed_leaf_passes():
    result = assess_quality(sharp_leaf_image(), **THRESHOLDS)
    assert result.passed is True
    assert result.reason_th is None

def test_a_blurred_image_fails_with_the_thai_blur_message():
    result = assess_quality(blur(sharp_leaf_image(), ksize=31), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "blurry"
    assert result.reason_th == "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"

def test_a_dark_image_fails_as_underexposed_not_as_blurry():
    # Darkness also depresses the Laplacian variance, so exposure must be judged first.
    result = assess_quality(scale_brightness(sharp_leaf_image(), 0.08), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "underexposed"
    assert result.reason_th == "ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ"

def test_a_blown_out_image_fails_as_overexposed():
    result = assess_quality(scale_brightness(sharp_leaf_image(), 4.0), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "overexposed"
    assert result.reason_th == "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงแดดจัดส่องตรง"

def test_blur_score_is_the_variance_of_the_laplacian_and_drops_when_blurred():
    sharp = assess_quality(sharp_leaf_image(), **THRESHOLDS).blur_score
    soft = assess_quality(blur(sharp_leaf_image(), ksize=31), **THRESHOLDS).blur_score
    assert sharp > 80.0 > soft

def test_scores_are_reported_even_when_the_image_passes():
    result = assess_quality(sharp_leaf_image(), **THRESHOLDS)
    assert 40.0 < result.exposure_mean < 215.0
    assert 0.0 <= result.clipped_pct <= 1.0
```

Helpers live in `tests/test_quality.py`: `sharp_leaf_image()` renders a green leaf-like blob with hard-edged brown speckles so the Laplacian variance is comfortably above the threshold; `blur()` wraps `cv2.GaussianBlur`; `scale_brightness()` multiplies and clips.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_quality.py -v`
Expected: collection error — `app.services.quality` does not exist.

- [ ] **Step 3: Implement `QualityResult` and `assess_quality()` in `backend/app/services/quality.py`**

Evaluation order is fixed and is what the tests pin: exposure first (mean luminance outside the band, or clipped fraction above `clip_max_pct`), then blur. `blur_score` is `cv2.Laplacian(grey, cv2.CV_64F).var()`; `exposure_mean` is the mean of the grayscale channel; `clipped_pct` is the fraction of pixels at 0 or 255. All three scores are always populated, whether or not the image passes.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_quality.py -v`
Expected: 6 passed.

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python -m pytest -v`
Expected: 23 passed.

- [ ] **Step 6: Commit and push**

```bash
git add backend/app/services/quality.py backend/tests/test_quality.py
git commit -m "feat(quality): add stage-1 blur and exposure gate with Thai feedback"
git push
```

---

## D1 Done When

- `cd backend && python -m pytest -v` is green.
- `curl http://127.0.0.1:8000/health` and `curl http://127.0.0.1:8000/api/v1/kb` both answer.
- `gh repo view mntoyg/TeaSmart-AI --json isPrivate` reports `true`, and `main` is pushed.
