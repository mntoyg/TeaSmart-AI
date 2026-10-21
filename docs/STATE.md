# สถานะโครงการ

**อ่านไฟล์นี้ก่อนอย่างอื่น** ไฟล์นี้บอกว่างานอยู่ตรงไหน ไม่ได้บอกว่ามาถึงจุดนี้ได้อย่างไร
ใครปิดสไลซ์ได้ อัปเดตไฟล์นี้ใน push เดียวกันกับงานนั้น

> **Codex เริ่มที่ [docs/HANDOFF-CODEX.md](HANDOFF-CODEX.md)** — ลำดับไฟล์ที่ต้องอ่าน
> ปัญหาที่เหลือก่อนสาธิตพร้อมเจ้าของ และกับดักเรื่อง branch ที่จะทำให้เสียงานทั้งวัน

- **อัปเดตล่าสุด:** 2026-10-21
- **กำหนดสาธิต:** 2026-10-22 — **พรุ่งนี้**
- **PR ที่เปิดอยู่:** #14 (เอกสารความพร้อมสาธิต), #15 (prompt ส่งต่อ) และ **#16**
  ซึ่งตอนนี้รวมงานทั้งหมด: คู่มือสาธิต, TLS, หน้าไทย, QR, ทำความสะอาด, fallback,
  static deploy และ #17 ที่ merge เข้ามาแล้ว **#5–#13 และ #17 merge แล้ว**
  **2026-10-21: merge #17 แล้วพบว่า base ของมันคือ `fix/demo-parity-section` ไม่ใช่
  `main`** งานจึงยังไม่ถึง `main` — `main` ยังอยู่ที่ PR #13
  **ต้อง merge #16 เข้า `main` จึงจะถึง** branch ปัจจุบันคือ `fix/demo-parity-section`
- **เจ้าของตามไดเรกทอรี:** `docs/DESIGN.md` หัวข้อ 14 — Claude Code ดูแล `backend/`
  และ `ml/` ส่วน Codex ดูแล `frontend/`
  **2026-10-20 Claude Code ข้ามเข้า `frontend/`** เพิ่ม `vite.https.ts`,
  `src/test/vite-https.test.ts` และสามบรรทัดใน `vite.config.ts`
  เหตุผล: TLS เป็นทางเดียวที่ iPhone จะได้ secure context และผู้ใช้สั่งมาเอง
  การเปลี่ยนเป็นแบบเพิ่มเข้าไปและ opt-in — ถ้าไม่ตั้ง `TEASMART_DEV_CERT_DIR`
  ทั้ง dev server, build และ CI ทำงานเหมือนเดิมทุกอย่าง และไม่แตะ `server.proxy`
  ตอนนั้นไม่มีงานของ Codex ค้างอยู่ (PR #14 เป็น docs เท่านั้น) ต่อจากนี้ไฟล์เหล่านี้
  เป็นของ Codex
- **เพดานการใช้งานต่อวัน:** AI ทุกตัว ไม่เกิน 14% ของ weekly capacity ของตัวเองต่อวัน
  (2026-10-20 ผู้ใช้ยกเพดานเฉพาะวันนั้นเป็น 50% ไม่ใช่กฎใหม่)

---

## สามอย่างที่เหลือก่อนวันสาธิต เรียงตามความสำคัญ

1. ~~แก้ fallback เมื่อต่อเซิร์ฟเวอร์ไม่ได้~~ **เสร็จแล้ว 2026-10-20**
   `api.ts` แยก `ServerUnreachableError` ออกจาก error ธรรมดา และ `ScanPage`
   ย้อนไปรันบนเครื่องเฉพาะกรณีนั้น แล้วเข้าคิวให้ sync ทีหลัง
   **ไม่ย้อน**เมื่อเซิร์ฟเวอร์ตอบมาว่าปฏิเสธภาพ (422 คือคำตัดสินเรื่องภาพ ต้องถึงจอ)
   และ**ไม่ย้อน**เมื่อผู้ใช้กดยกเลิก ส่วน timeout นับเป็นต่อไม่ถึง เพราะไม่มีคำตอบกลับมา
2. **deploy frontend แบบ static — เตรียมครบแล้ว รอเลือก host**
   ขั้นตอนทั้งหมดเป็นภาษาไทยใน [docs/DEPLOY-TH.md](DEPLOY-TH.md)
   ทำแล้ว: `scripts/snapshot_api.py` แช่ `GET /api/v1/config` และ
   `GET /api/v1/kb` เป็นไฟล์ static (วัดแล้วว่าทั้งคู่ 404 บน bundle ที่ไม่มี
   backend และ**ทั้งคู่ถึงตาย** — ไม่มี config โมเดลบนเครื่องไม่ยอมรันเลย
   ไม่มี kb ก็ไม่มีคำแนะนำภาษาไทย) `_redirects` สำหรับ SPA fallback
   และ `scripts/make_qr.py` สำหรับ QR ตัวจริง
   **ยังไม่ทำ: เลือก host และอัปโหลด** แนะนำ Cloudflare Pages แบบ upload
   ตรง เพราะ repo เป็น private และ GitHub Pages ไม่อ่าน `_redirects`
   **QR ต้องชี้ไป root ไม่ใช่ `/scan`** เพราะ `App.tsx` ส่ง route `*` ไป
   `/scan` อยู่แล้ว root จึงใช้ได้แม้ host ไม่อ่าน `_redirects`
3. **รันบนมือถือจริง — กำลังทำ ยังไม่มีผลรายงาน**
   2026-10-20 ผู้ใช้ติดตั้ง root CA บน iPhone แล้วและกำลังเปิดแอป
   ยืนยันจากเครื่องผู้ใช้เองแล้วว่า `GET /scan` = 200, `GET /api/v1/config` = 200,
   CA server = 200 **ยังไม่มีผลจากการกดบนมือถือจริง** — ข้อ 1-7 ใน
   `docs/PHONE-TH.md` ยังไม่มีใครยืนยัน

---

## วิธีเปิดแอปบนมือถือ

[docs/PHONE-TH.md](PHONE-TH.md) เป็นภาษาไทย เขียนให้อ่านบนมือถือและกดลิงก์ได้

มีสามทางไปสู่ secure context ซึ่งจำเป็นก่อนจะมีกล้อง offline หรือ install:

| ทาง | ใช้กับ | ข้อเสีย |
|---|---|---|
| `adb reverse` + USB | Android | ต้องต่อสาย แต่ได้ mirror + อัดวิดีโอบน PC ด้วย |
| mkcert + TLS | **iPhone และ Android** | ต้องติดตั้ง root CA บนมือถือครั้งเดียว |
| Chrome flag | Android เท่านั้น | **ไม่มีบน iOS** เพราะ Chrome บน iOS เป็น WebKit |

`scripts/serve_ca.py` ส่ง root certificate สาธารณะให้มือถือ และ**เสิร์ฟ CA private key
ไม่ได้ในทางโครงสร้าง** เพราะ handler ไม่อ่าน request path เลย — ไม่มี path ไหนไปถึง key
เพราะ path ไม่ใช่ input (14 tests เฝ้าคุณสมบัตินี้)

**ห้ามใช้ mkcert หรือ tunnel กับมือถือของกรรมการ** การขอให้กรรมการเชื่อ CA ของเรา
บนเครื่องส่วนตัวเป็นสิ่งที่ไม่ควรขอ และบางคนจะไม่ทำ ทางสำหรับกรรมการคือข้อ 2 ข้างบน

---

## QR code

`docs/img/app-qr-local.png` ที่ README แสดงอยู่ **ชี้ไปเครื่องพัฒนา**
(`https://192.168.0.32:5173/scan`) ใช้ได้เฉพาะ wifi วงเดียวกัน หลัง deploy แล้วสร้างใหม่:

```bash
python scripts/make_qr.py https://<โฮสต์ที่ deploy>/scan
```

script **ปฏิเสธ** URL ที่เป็น loopback, วง private, link-local หรือลงท้าย
`.local` / `.localhost` / `.internal` โดยอัตโนมัติ เว้นแต่ส่ง `--allow-local`
เพราะ QR ของ LAN ทำงานบนมือถือคนทำแต่พังสำหรับคนอื่น ซึ่งแย่กว่าไม่มี QR —
คนสแกนจะสรุปว่าแอปเสีย ไม่ใช่ว่าลิงก์เป็นของเครื่องใครคนหนึ่ง

---

## ที่ทำเสร็จแล้ว

| วัน | สไลซ์ | หลักฐาน |
|---|---|---|
| D1 | รากฐาน backend: `/health`, `/api/v1/kb`, ถอดรหัสภาพแบบแข็งแรง, ด่านคุณภาพ (ด่าน 1) | 40 tests, merge ใน `mntoyg/TeaSmart-AI#1` |
| D2 (PR #4) | ท่อชุดข้อมูล: ทะเบียนแหล่ง, นำเข้า, ตัดซ้ำระดับพิกเซล, manifest แบบ stratified, CLI `prepare` | 74 tests, `docs/EVIDENCE.md` หัวข้อ 1 |
| D3 (PR #6) | ตัวจำแนก: เทรน, ประเมิน, วัด `min_confidence`, ส่งออก ONNX พร้อมตรวจ parity | 120 ml tests, macro-F1 ชุดทดสอบ **0.9873**, `docs/EVIDENCE.md` หัวข้อ 2 |
| D6/D7 (PR #5) | frontend: หน้าสแกน, การ์ดผลภาษาไทย, เปลือก PWA, ONNX worker บนเครื่อง, คิวออฟไลน์ | 47 Vitest, `docs/EVIDENCE.md` หัวข้อ 3 |
| — (PR #6) | repository: CI, `scripts/setup`, `scripts/test`, `pyproject.toml`, ruff สะอาด | `./scripts/test.sh` จบด้วย `All green.` |
| D4/D5 (PR #8) | ด่าน 2-5 และ `POST /api/v1/scan`: แยกใบ, จำแนกด้วย ONNX, วิเคราะห์แผล, ความรุนแรง, คำแนะนำผู้เชี่ยวชาญ, ย่อภาพหลังถอดรหัส | 84 backend tests, ทดสอบสดครบวง, `docs/EVIDENCE.md` หัวข้อ 4 |
| D4 แก้ (PR #9) | mask ของแผล: ตัดขอบใบและใช้ convex hull **ก่อนหน้านี้กรณีใบไหม้มองไม่เห็นในเชิงโครงสร้าง** | specificity 97.18%, `docs/EVIDENCE.md` หัวข้อ 5 |
| D5 (PR #10) | `POST /api/v1/sync/batch` และ idempotency ด้วย `scan_id` ทั้งสอง endpoint | 102 backend tests, ทดสอบสด |
| D9 (PR #11) | คู่มือสาธิตสร้างจาก pipeline จริง หกช่อง | `docs/DEMO.md` |
| D7 gate (PR #13) | จับ resize ของเบราว์เซอร์ให้ตรงกับ PIL — การตรวจ parity 50 ภาพ **ผ่าน** | 58 frontend tests, `docs/EVIDENCE.md` หัวข้อ 6 |
| docs (PR #16) | `docs/DEMO.md` หัวข้อ 4 ยังบอกว่า parity gate เปิดอยู่หลัง PR #13 ปิดไปแล้ว สั่งให้ผู้อ่านนำเสนอผลออฟไลน์ที่ทำงานได้ว่าเป็นแค่ท่อ แก้ที่ generator และมี test ที่อ่านคำตัดสินออกจาก `docs/EVIDENCE.md` เฝ้าไว้ PR เดียวกัน: บันทึก `adb reverse` เป็นทางแรกสู่ secure context ซึ่ง mirror และอัดวิดีโอได้ด้วย | 107 backend tests |
| TLS (PR #16) | `frontend/vite.https.ts` เสิร์ฟคู่ cert ของ mkcert เมื่อตั้ง `TEASMART_DEV_CERT_DIR` ทำให้ LAN address เป็น secure context บน **iPhone ไม่ใช่แค่ Android** `scripts/serve_ca.py` ส่ง root สาธารณะ หน้าไทย `docs/PHONE-TH.md` | 121 backend, 63 frontend tests |
| ทำความสะอาด (PR #16) | ลบ worktree `.superpowers/worktrees/d6` และ `d7` (ทั้งสอง branch เป็น ancestor ของ `origin/main` แล้ว ไม่มี commit หาย และ branch ref ยังอยู่) ลบ `.mypy_cache`, `.ruff_cache` แก้ลิงก์เอกสารเสีย 3 จุด มี `test_docs_links.py` เฝ้าทุกลิงก์และ `<img src>` ถาวร | 134 backend tests |
| QR + README ไทย (PR #16) | `scripts/make_qr.py` พร้อมการ์ดกัน URL วง LAN, README เป็นไทยและเพิ่มหัวข้อสถาปัตยกรรม | 153 backend tests |
| fallback (PR #16) | `ScanPage` ย้อนไปรันโมเดลบนเครื่องเมื่อต่อเซิร์ฟเวอร์ไม่ถึง แต่ไม่ย้อนเมื่อเซิร์ฟเวอร์ปฏิเสธภาพหรือผู้ใช้กดยกเลิก **เงื่อนไขที่ทำให้ deploy แบบ static ใช้งานได้** | 73 frontend tests |
| static deploy (PR #16) | `scripts/snapshot_api.py` แช่ config กับ kb เป็นไฟล์ static ที่ path เดิม (วัดแล้ว: จาก 404/404 เป็น 200/200 บนเซิร์ฟเวอร์ static ที่ไม่มี backend), `_redirects` สำหรับ SPA fallback, ขั้นตอน deploy เป็นไทยใน `docs/DEPLOY-TH.md` | 163 backend tests |

**คลังภาพบนดิสก์:** นำเข้า 11,853 ภาพจากสามแหล่งที่ไม่ต้องใช้ credential
ตัดซ้ำเหลือ **8,316** ภาพใน 5 คลาส แบ่ง 70/15/15 และตรวจทุกคู่ในเชิงพิกเซลแล้วพบ
คู่ซ้ำข้ามชุด **0** คู่ สร้างใหม่ด้วย
`cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare`

**การทดสอบตอนนี้:** 163 backend, 120 ml, 73 frontend, ruff สะอาด, `All green.`

---

## สิ่งที่โมเดลเก็บไว้ที่ไหน

- checkpoint: `data/artifacts/teasmart-v1.pt` — **gitignored** สร้างใหม่ด้วย
  `python -m teasmart_ml.cli train` (15 epochs ประมาณ 35 นาทีบน RTX 3050)
- กราฟสำหรับเบราว์เซอร์: `frontend/public/models/teasmart-v1.onnx` — **commit ไว้**
  (16.8 MB) เพื่อให้ checkout ใหม่สาธิตได้โดยไม่ต้องมี GPU
- `frontend/public/models/teasmart-v1-int8.onnx` — **ไม่ commit โดยเจตนา**
  มันไม่ผ่านขอบ parity ถ้ามีอยู่ในดิสก์ของคุณ ให้ลบ

---

## การเปลี่ยนสัญญา API (อ่านถ้าคุณดูแลฝั่งใดฝั่งหนึ่ง)

**2026-10-13 — เขียนหัวข้อ 8 ของ spec ใหม่** Codex ขอส่วนที่เขียน client ไม่ได้
ถ้าไม่มี และมันถูกที่ว่าส่วนนั้นขาดอยู่ ตอนนี้ตรึงแล้ว:

- ชื่อ field ของ `POST /api/v1/scan` ในแบบ multipart คือ **`image`** บวก `scan_id`
  และ `captured_at` ที่ใส่หรือไม่ใส่ก็ได้
- คำขอและคำตอบรายรายการของ `POST /api/v1/sync/batch` จับคู่ item กับไฟล์ด้วย
  `scan_id` ไม่ใช่ด้วยลำดับ
- `scan_id` เป็นกุญแจ idempotency แคชของเซิร์ฟเวอร์อยู่ในหน่วยความจำและไม่รอดการ
  restart ดังนั้น client ต้องตัดซ้ำในเครื่องตัวเองด้วย
- การเตรียมภาพของ ONNX ชื่อ input/output ลำดับคลาส และการตรวจ parity ที่ต้องผ่าน
  ก่อนจะเรียกว่า D7 เสร็จ
- เบราว์เซอร์ไม่แยกใบออกจากพื้น ผลบนเครื่องจึงเป็น `classifier_only` และ**ต่างจาก**
  ผลจากเซิร์ฟเวอร์จริง ๆ

**2026-10-13 — เพิ่ม `GET /api/v1/config`** (44 backend tests) Codex ชี้ว่า
`min_confidence` ถูกระบุไว้แต่ไม่มีอยู่จริง ตอนนี้มีแล้วที่ **0.60** และแทนที่จะยืนยัน
ตัวเลขให้ frontend ไปคัดลอก backend เสิร์ฟค่าคงที่ทุกตัวที่สองฝั่งใช้ร่วมกัน:
เพดานความเชื่อมั่น ลำดับคลาส (ดึงจากฐานความรู้ ไม่ได้เขียนซ้ำ) การเตรียมภาพของ ONNX
และ threshold คุณภาพที่เบราว์เซอร์ทำซ้ำ **อ่านจาก endpoint อย่า hard-code**

**2026-10-19 — วัด `min_confidence` แล้ว และเปลี่ยนไฟล์ ONNX ที่ใช้**

1. **`min_confidence` ยังเป็น 0.60 แต่ตอนนี้วัดมาแล้ว ไม่ใช่ค่าชั่วคราว** เกณฑ์ที่
   D3 ได้รับมา (accuracy 0.90 ในกลุ่มที่รับ) ให้คำตอบ 0.20 กับโมเดลที่แม่น 0.987
   ซึ่งจะปิดตะแกรงนิรภัย `other_disease` ทิ้งทั้งหมด **เกณฑ์นั้นเองคือความผิดพลาด
   ไม่ใช่การวัด** เกณฑ์ที่ใช้จริงคือ accuracy 0.99 ในกลุ่มที่รับ: ได้ 0.55 บน
   validation และ 0.63 บน test ดังนั้น 0.60 อยู่ระหว่างสองค่า และปฏิเสธภาพ 0.72%
2. **เบราว์เซอร์โหลด `teasmart-v1.onnx` (fp32, 16.8 MB) ไม่ใช่ int8** int8 ให้
   top-1 ตรงกันทั้ง 50 ภาพ แต่ขยับความน่าจะเป็นไป 0.248 เทียบขอบ 0.05
   **top-1 ตรงกันไม่ใช่เกณฑ์ตอบรับ** เพราะสินค้าตัดสินใจจากค่าความน่าจะเป็น

ทั้งสองเสิร์ฟจาก `GET /api/v1/config` client ที่อ่าน endpoint จึงไม่ต้องแก้อะไร
หลักฐาน: `docs/EVIDENCE.md` หัวข้อ 2

**2026-10-20 — สัญญาถูก implement ครบ** `max_batch_items` 20,
`max_batch_bytes` 33554432 และ `idempotency_cache_size` 512 อยู่ใน `Settings`
`POST /api/v1/sync/batch` มีแล้ว และ idempotency ด้วย `scan_id` ครอบทั้งสอง endpoint
พร้อมส่ง `replayed` กลับมา ไม่มีอะไรในหัวข้อ 8 ที่ยังไม่ implement

`replayed` ถูกส่งทุกครั้ง และ**ไม่มี**ในตัวอย่างหัวข้อ 8.1 โดยเจตนา เพราะตัวอย่างนั้น
กลายเป็น `scanShape` ใน client ที่ generate ออกมา และ key ที่อยู่ในนั้นคือ key ที่
client บังคับให้ต้องมี

---

## 2026-10-21 — ของที่ไม่มีใครตกลงให้เผยแพร่ เกือบขึ้นเว็บไปด้วย

Vite ก็อปทุกไฟล์ใต้ `frontend/public/` ลง `dist` ตรง ๆ และ `dist` คือสิ่งที่อัปขึ้นเว็บ
สาธารณะ **การ track ด้วย git คือประตูตรวจเดียวที่ไฟล์เหล่านั้นผ่าน** วัดก่อน deploy
ไม่กี่ชั่วโมง พบ untracked 52 ไฟล์ใต้ `public/`:

- `models/teasmart-v1-int8.onnx` 4.7 MB โมเดลที่**ไม่ผ่านขอบ parity** และ
  **ถูก precache อยู่จริง** เอาออกแล้ว service worker ลดจาก 13 เหลือ 12 entries
  และยอดดาวน์โหลดออฟไลน์กลับมาเป็น 30,737 KiB ตรงกับ 30.7 MB ที่ `docs/DEMO.md`
  ระบุไว้ แปลว่าตัวเลขที่วัดเมื่อ 2026-10-20 (13 entries, 35.3 MB) ปนไฟล์นี้อยู่
- `parity/` ภาพถ่าย 50 ใบจากคลัง Kaggle, Mendeley, AGML บวกเฉลย 3.7 MB
  `.gitignore` กันไว้ด้วยเหตุผลเรื่อง**การเผยแพร่ซ้ำ** ถ้า deploy คือเอาภาพจาก
  ชุดข้อมูลของบุคคลที่สามขึ้นเว็บสาธารณะ

ทั้งสอง gitignored จึงไม่โผล่ใน `git status` และ checkout ใหม่สะอาด
**เฉพาะเครื่องที่ generate มันเท่านั้นที่มีปัญหา** ย้ายออกแล้ว ไม่ลบ
`backend/tests/test_shipped_models.py` เฝ้าไว้แล้ว และขั้นตอนอยู่ใน
[docs/DEPLOY-TH.md](DEPLOY-TH.md) ข้อ 2

**test ตัวนี้เขียนผิดรอบแรก** ใส่ `--exclude-standard` ซึ่งทำให้ git ตัดไฟล์
gitignored ออกจากผลลัพธ์ ตรงข้ามกับที่ต้องการ — มันผ่านทั้งที่มี 52 ไฟล์ค้างอยู่
และพิสูจน์อะไรไม่ได้เลย

**bundle ที่สะอาดแล้ว:** 31 MB, precache 12 entries, ไม่มีโฟลเดอร์ `parity`
มีแต่โมเดลที่สัญญาระบุ พร้อมอัปโหลด

## Remaining verification before the demo

**P0-2 — Service-worker offline scan measured successfully with the static server stopped.**
On 2026-10-20, the static preview was prepared for offline use until the UI reported
"offline ready." After stopping its preview server, `/scan` reloaded through the service
worker. With `frontend/public/parity/49.jpg`, both the on-device button and the normal
scan button completed. The normal scan path fell back to local ONNX, returned
`classifier_only` at 95.4% confidence, and queued the result; two local scans left two
items waiting to sync.

Scope: this was a service-worker-controlled browser preview, not a PWA installed to a
home screen. `navigator.onLine` still reported connected; the static server was stopped
so API requests could not reach it. Repeat on an installed iPhone/Android PWA with the
device network disabled before closing P0-2 for the demo.

UX follow-up: after offline reload, the panel resets to "offline not prepared" even
though the cached model and config still support scans. Make the initial status reflect
the available cache before the demo.

Codex usage check, 2026-10-20 15:49 Asia/Bangkok: the usage tool reports 1% used in the
weekly window; a daily counter is unavailable. The session baseline was 0% weekly, so
count 1 percentage point of weekly capacity conservatively for today's work, within the
14% daily ceiling. Native Windows validation passed with `./scripts/test.ps1`: backend
165, ML 120, frontend 73; all lint and frontend build steps passed, ending in `All green.`
`bash.exe ./scripts/test.sh` ran the suites but its scripts-lint path was translated
incorrectly by WSL; use the repository's PowerShell runner on this Windows host.

**`_redirects` ยังไม่ได้ยืนยัน** `python -m http.server` ไม่อ่านไฟล์นี้ จึงทดสอบ
ในเครื่องไม่ได้ — `/kb` ตอบ 404 ที่นี่เพราะเหตุนี้ Cloudflare Pages และ Netlify
อ่านเอง แต่ยืนยันได้หลัง deploy จริงเท่านั้น ทางเข้าหลักไม่พึ่งมัน เพราะ root ใช้ได้อยู่แล้ว

## เรื่องที่รอผู้ใช้ตัดสินใจ

1. **`max_image_pixels` เป็น 40,000,000** ไฟล์ JPEG 738 KB ถอดรหัสออกเป็น 7000×5600
   และกินหน่วยความจำสูงสุด 235 MB — เป็นการขยายขนาดจริงบนประตูเดียวที่รับของจาก
   ภายนอก ลดเพดานลงจะปฏิเสธรูปจากมือถือ 48 MP ไปเลย ทางแก้ที่ตั้งใจไว้คือย่อภาพ
   ทันทีหลังถอดรหัส **ทำแล้วใน PR #8**
2. **แหล่ง Kaggle สองแหล่งและ HuggingFace ที่ต้องขออนุญาต ถูกปิดอยู่** เพราะไม่มี
   credential สามแหล่งที่ใช้ก็เพียงพอ เปิดเพิ่มคือแค่ flag กับ token
3. **32 ภาพถูกสองแหล่งติดป้ายไม่เหมือนกัน** และถูกตัดทิ้งแทนที่จะเดา
   ถ้าตรวจด้วยตาจะได้ข้อมูลเทรนจริงกลับมา

---

## เรื่องที่เป็นจริงและพลาดง่าย

- **ไม่มีค่า sensitivity ของการตรวจใบไหม้ และห้ามอ้างตัวเลขนั้น รวมถึงบนเวที**
  specificity วัดได้ 97.18% ส่วน sensitivity วัดไม่ได้ถ้าไม่มีรูปใบไหม้จริง และ
  fixture สังเคราะห์ตัดสินแทนไม่ได้ เพราะมันถูกวาดขึ้นจากนิยามคุณลักษณะที่มันทดสอบ
  `docs/EVIDENCE.md` หัวข้อ 5.5
- **specificity ที่สูงอาจหมายความว่าตัววิเคราะห์ไม่ได้มอง** การรันครั้งแรกรายงาน
  99.22% ขณะที่หาแผลไม่เจอบนใบที่เป็นโรค 59% **ดูจำนวน no-measurable-lesion
  ก่อนเชื่ออัตราใด ๆ**
- **threshold ของด่าน 1 วัดมาแล้ว ไม่ได้เดา** ตั้งแต่ 2026-10-19 ค่าเดิมปฏิเสธภาพจริง
  ไปถึง 69.8%
- **accuracy 0.987 บนชุดทดสอบเป็นขอบบนของความแม่นในสนาม ไม่ใช่ค่าประมาณ**
  การแบ่งชุดสุ่มภายในแต่ละคลาสและไม่จัดกลุ่มตามครั้งที่ถ่าย ภาพใบเดียวกันหลายช็อต
  จึงไปอยู่ได้ทั้งสองฝั่ง D2 ตัดภาพซ้ำระดับพิกเซลออก ซึ่งเป็นเรื่องคนละอย่าง
- **ตัวจำแนกผิดได้แบบมั่นใจ** มีภาพทดสอบหนึ่งภาพที่ผิดที่ความเชื่อมั่น 0.983
  ซึ่งสูงกว่าเพดานใด ๆ ที่ใช้ได้จริง **ไม่มีหน้าจอไหนนำเสนอผลว่าแน่นอนได้**
- **`DataLoader` ที่ `num_workers > 0` ต้องมี `if __name__ == "__main__"` ครอบ**
  ใน script ที่ใช้มัน Windows สร้าง worker ด้วยการ import ไฟล์ใหม่ ถ้าไม่มีตัวครอบ
  การ import ซ้ำจะสร้าง worker เพิ่มไปเรื่อย ๆ จนโพรเซสค้าง `teasmart_ml.cli`
  มีตัวครอบแล้ว แต่ script เขียนเร็ว ๆ จะไม่มี
- **ไม่มีภาพใบไหม้ในชุดข้อมูลใดเลย** การตรวจใบไหม้เป็น CV แบบกฎเกณฑ์ และตัวชี้วัด
  หลักของมันคือ specificity บนภาพที่ยืนยันว่าเป็นโรค
- **`other_disease` มีไว้โดยเจตนา** ให้โมเดลปฏิเสธการตั้งชื่อโรคที่มันไม่เคยเห็น
- **คอลัมน์ `path` ใน manifest อ้างอิงจาก interim root** ไม่ใช่ absolute และไม่ใช่
  เทียบกับ repository
- **นิยามของภาพซ้ำคือพิกเซล** (greyscale 32×32, MAE ≤ 8.0) ไม่ใช่ perceptual hash
  ตัว hash เป็นคอลัมน์สำหรับตรวจสอบ เหตุผลที่เรื่องนี้สำคัญอยู่ใน
  `docs/DESIGN.md` หัวข้อ 13
- **`data/interim/` ต้องมีไฟล์หมาย `.teasmart-interim`** ก่อน pipeline จะยอมล้าง
  อะไรข้างใน
- **shell ของ AI agent อาจเขียนไฟล์ลงที่ที่ shell ของผู้ใช้อ่านไม่เห็น** วัดเมื่อ
  2026-10-20: ไฟล์ที่เขียน**ใน** repository ลงดิสก์จริง แต่ CA ของ mkcert ใต้
  `%LOCALAPPDATA%` เห็นได้แค่จาก shell ของ agent — `is_dir()` ตอบ True จากฝั่ง agent
  และ False จาก PowerShell ของผู้ใช้ สำหรับ path เดียวกัน ของที่โพรเซสของผู้ใช้
  ต้องอ่าน (CA, trust store, credential, ไดเรกทอรีสถานะของเครื่องมือ) **ต้องสร้างใน
  terminal บนเครื่องผู้ใช้** แล้วตรวจจากที่นั่น ผลตรวจที่ผ่านในฝั่ง agent ไม่ใช่
  หลักฐานว่าเครื่องผู้ใช้มีไฟล์นั้น

---

## บันทึกส่งต่อฝั่ง frontend

- `frontend/` ที่ root เป็น source ชุดเดียว **ไม่มีสำเนาอื่น** worktree ที่ซ่อนอยู่
  สองชุดถูกลบไปเมื่อ 2026-10-20 หลังจาก branch ของทั้งสอง merge เข้า `main` แล้ว
- ขอบเขตกับ backend คือสัญญา API ใน `docs/DESIGN.md` หัวข้อ 8 ค่า runtime มาจาก
  `GET /api/v1/config` **อย่า hard-code**
- จุดเริ่มอ่าน: [frontend/README.md](../frontend/README.md)
- ยังมี warning `inlineDynamicImports` ของ VitePWA ค้างอยู่ตอน build ยังไม่แก้
- **ค้างอยู่สองข้อ P2 ที่เป็นของ `frontend/`:**
  `src/lib/api.ts` hard-code รายชื่อคลาสซ้ำกับที่ `GET /api/v1/config` เสิร์ฟ
  (วันนี้ค่าตรงกัน การมีสำเนาที่สองคือตัวปัญหา) และ `parseKnowledge` บังคับให้มี
  record ในฐานความรู้ **เท่ากับ 6 รายการพอดี** โรคที่เจ็ดจะทำให้ client พัง
