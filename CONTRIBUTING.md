# การร่วมพัฒนา TeaSmart AI

Phase 1 MVP สาธิตในแฮกกาธอน **2026-10-22** ลงงานวันละหนึ่งสไลซ์แนวตั้ง
อ่าน `docs/STATE.md` เพื่อดูว่างานอยู่ตรงไหน แล้วอ่าน `docs/DESIGN.md` ก่อนแตะโค้ด

ผู้ร่วมพัฒนาฝั่ง frontend: อ่าน [frontend/README.md](frontend/README.md) เพื่อดู
แผนที่ซอร์ส และ [docs/DESIGN.md](docs/DESIGN.md) หัวข้อ 8 ซึ่งเป็นสัญญา API
และเป็นขอบเขตระหว่าง frontend กับ backend ทำงานใน `frontend/` ที่ root
AI ทุกตัวต้องทำตามเพดานการใช้งานต่อวันใน `AGENTS.md`

| เอกสาร | คืออะไร |
|---|---|
| `docs/STATE.md` | งานอยู่ตรงไหนแล้ว — **อัปเดตเมื่อคุณปิดสไลซ์** |
| `docs/DESIGN.md` | การออกแบบ สัญญา API และเหตุผลเบื้องหลัง — **เป็นผู้มีอำนาจผูกพัน** เมื่ออะไรขัดกัน |
| `docs/EVIDENCE.md` | ตัวเลขที่วัดได้ พร้อมคำสั่งที่ผลิตมัน |
| `docs/PHONE-TH.md` | เปิดแอปบนมือถือจริง เขียนให้อ่านบนมือถือ |
| [docs/HANDOFF-CODEX.md](docs/HANDOFF-CODEX.md) | ส่งงานต่อให้ Codex: ลำดับไฟล์ที่ต้องอ่าน ปัญหาที่เหลือ และกับดักเรื่อง branch |
| `AGENTS.md` | กฎที่ AI agent ทุกตัวต้องทำตาม |

## ติดตั้ง

```bash
git clone https://github.com/mntoyg/TeaSmart-AI.git && cd TeaSmart-AI
./scripts/setup.sh --cpu     # Windows: ./scripts/setup.ps1 -Cpu
./scripts/test.sh            # Windows: ./scripts/test.ps1
```

ตัด `--cpu` ออกถ้ามีการ์ด NVIDIA และตั้งใจจะเทรน ทุกอย่างในชุดทดสอบรันบน CPU
ดังนั้น wheel ของ CPU เพียงพอสำหรับการร่วมพัฒนา

`test.sh` ต้องจบด้วย `All green.` มันรันสิ่งเดียวกับที่ CI รัน ในลำดับเดียวกัน
ดังนั้นรันผ่านในเครื่องคือผ่านบน pull request ขณะที่เขียนนี้คือ
**153 backend tests, 120 ML tests และ 63 frontend tests**

ต้องมี Python 3.12 และ Node 22 ไม่มีอะไรต้องใช้ `.env` เพื่อรัน คัดลอก
`.env.example` ไปเป็น `backend/.env` เฉพาะเมื่อต้องการเปลี่ยนค่าตั้งต้น

## รันบริการ

```bash
cd backend && .venv/bin/python -m uvicorn app.main:create_app --factory --reload
```

บน Windows ตัวแปลภาษาคือ `.venv/Scripts/python.exe` **virtualenv ไม่เคยถูก activate**
การระบุตัวแปลภาษาตรง ๆ ยาวกว่าหนึ่งบรรทัดแต่กำจัดความผิดพลาดประเภท
"อยู่ environment ผิด" ไปทั้งกลุ่ม

```bash
curl http://127.0.0.1:8000/health && curl http://127.0.0.1:8000/api/v1/config
```

## แพ็กเกจ ML

```bash
cd ml
.venv/bin/python -m teasmart_ml.cli --help
.venv/bin/python -m teasmart_ml.cli prepare     # rebuild the corpus
.venv/bin/python -m teasmart_ml.cli train       # ~35 min on a 4 GB card
.venv/bin/python -m teasmart_ml.cli evaluate --split test
.venv/bin/python -m teasmart_ml.cli export      # ONNX for the browser
.venv/bin/python -m teasmart_ml.cli fixtures    # browser parity fixtures
```

## กฎบ้าน

**เขียน test ก่อน** เขียน test ที่ยังพัง ดูมันพัง แล้วค่อยเขียนโค้ด test ที่ผ่าน
ตั้งแต่วินาทีที่เขียนไม่ได้พิสูจน์อะไรเลย ถ้าคุณเพิ่ม test ที่พังไม่ได้
ให้ไปแก้ค่าคงที่ที่มันเฝ้าให้มันพัง ยืนยันว่ามันพังจริง แล้วแก้กลับ

**ชุดทดสอบถือว่า warning คือ error** รันผ่านต้องหมายถึงรันสะอาดด้วย ถ้ามี warning
จาก third-party ให้เพิ่ม ignore แบบเจาะจงใน `filterwarnings` ของ `pyproject.toml`
ในแพ็กเกจนั้น — ระบุ message, category และ module — **ห้ามใส่แบบครอบจักรวาล**

**lint เป็นส่วนหนึ่งของชุดทดสอบ ไม่ใช่งานแยก** `ruff check` รันก่อน test ใน
`scripts/test.*` และใน CI ตอนนี้สะอาด รักษาให้สะอาดแทนที่จะปล่อยให้มีงานค้างสะสม

**threshold อยู่ใน config ไม่ใช่ที่จุดเรียกใช้** ทุกอย่างที่ปรับได้เป็น field บน
`Settings` ใน `backend/app/core/config.py` และ `tests/test_config.py` ตรึงค่าที่ spec
กำหนดไว้ ใน test ให้อ่านจาก `get_settings()` แทนการเขียนตัวเลขซ้ำ

**ฐานความรู้เป็นข้อมูล** `backend/app/kb/diseases.json` เก็บคำแนะนำภาษาไทยที่เกษตรกร
จะลงมือทำตาม **record 0-3 เป็นข้อความที่ได้รับมา ห้ามเรียบเรียงใหม่** record ใช้คลาส
`canonical` แบบ snake_case ที่ตัวจำแนกส่งออกเป็นกุญแจ ไม่ใช่ชื่อแสดงภาษาอังกฤษ

**ภาษาไทยสำหรับคน อังกฤษสำหรับเครื่อง** ข้อความที่ผู้ใช้เห็น เนื้อหาฐานความรู้
และ**เอกสาร** เป็นภาษาไทย ส่วนโค้ด คอมเมนต์ docstring และ commit message
เป็นภาษาอังกฤษ (เอกสารเปลี่ยนเป็นไทยเมื่อ 2026-10-20 ดู `AGENTS.md` ข้อ 1
ว่าครอบคลุมอะไรและไม่ครอบคลุมอะไร)

**ทุกด่านของ pipeline เป็นฟังก์ชันบริสุทธิ์** หนึ่งโมดูลต่อหนึ่งด่านใต้
`backend/app/services/` **ไม่มีด่านไหนเอื้อมเข้าไปในไส้ของอีกด่าน** ถ้าด่านหนึ่ง
ต้องใช้ค่า ให้รับค่านั้นเป็นอาร์กิวเมนต์

**ของที่อัปโหลดเข้ามาเป็นศัตรูจนพิสูจน์ได้ว่าไม่ใช่** `backend/app/core/images.py`
เป็นประตูบานเดียวที่ภาพจากภายนอกผ่าน และทุกด่านหลังจากนั้นเชื่อผลของมัน
การแก้ที่นั่นต้องมี test สำหรับประเภท input ที่คุณกังวล

## Branch และ commit

หนึ่ง branch ต่อหนึ่งสไลซ์ แตกจาก `main`: `feat/d2-dataset-ingest`, `fix/...`,
`docs/...` **ห้าม commit ลง `main` ตรง ๆ** มี AI สองตัวทำงานที่นี่พร้อมกันและแบ่งงาน
ตามไดเรกทอรี — `docs/DESIGN.md` หัวข้อ 14 บอกว่าใครดูแลอะไร
**หนึ่ง branch ต่อหนึ่งสไลซ์ ห้ามสองคนอยู่ branch เดียวกัน**

หัวข้อ commit แบบ conventional (`feat(kb):`, `fix:`, `docs:`) ใช้รูปคำสั่ง
แล้วเขียนเนื้อหาอธิบาย **ว่าทำไม** — diff บอกอยู่แล้วว่าทำอะไร ใส่ผลการทดสอบด้วย
เมื่อผลนั้นคือประเด็นของการเปลี่ยนแปลง

เปิด PR เข้า `main` และให้มีคนอ่าน เนื้อหา PR บอกว่าอะไรลงไป การตัดสินใจไหนที่ควรรู้
และผลการตรวจสอบ

## ก่อนจะบอกว่ามันทำงานได้

รันชุดทดสอบและวาง output จริงลงไป **"น่าจะทำงานได้" ไม่ใช่หลักฐาน**
ถ้าอะไรยังไม่เสร็จหรือคุณข้ามขั้นตอนไหน ให้บอกไว้ใน PR
