# ส่งงานต่อให้ Codex — 2026-10-20

เขียนโดย Claude Code หลังทำงานทั้งวันของ 2026-10-20 **สาธิต 2026-10-22 เหลือสองวัน**

---

## 0. อ่านตามลำดับนี้ก่อนแตะอะไร

| ลำดับ | ไฟล์ | ทำไม |
|---|---|---|
| 1 | `AGENTS.md` | กฎที่ผูกพัน รวมเพดานการใช้งานต่อวัน และการแบ่งงานตามไดเรกทอรี |
| 2 | [docs/STATE.md](STATE.md) | **เริ่มที่นี่** งานอยู่ตรงไหน เขียนใหม่ทั้งไฟล์วันนี้ |
| 3 | [docs/DESIGN.md](DESIGN.md) หัวข้อ **8** และ **14** | 8 = สัญญา API ซึ่งเป็นขอบเขตของคุณกับ backend / 14 = ใครดูแลอะไร |
| 4 | [frontend/README.md](../frontend/README.md) | แผนที่ซอร์สฝั่งคุณ |
| 5 | `CONTRIBUTING.md` | กฎบ้าน: test ก่อน, warning คือ error, branch, commit |

อ่านเพิ่มเมื่อถึงงานนั้น:
- [docs/DEPLOY-TH.md](DEPLOY-TH.md) — ถ้าจะ deploy
- [docs/PHONE-TH.md](PHONE-TH.md) — ถ้าจะทดสอบบนมือถือ
- [docs/EVIDENCE.md](EVIDENCE.md) — **อ่านเฉพาะหัวข้อที่เกี่ยวข้อง** และ**ห้ามอ้างตัวเลขที่ไม่มีในไฟล์นี้**
- [docs/DEMO.md](DEMO.md) — คู่มือสาธิต **เป็นไฟล์ generate** แก้ที่ `scripts/prepare_demo.py` แล้วรัน script ใหม่ ห้ามแก้ `.md` ตรง ๆ

**หมายเหตุภาษา:** ผู้ใช้กำหนดให้เอกสารเป็นภาษาไทย (`AGENTS.md` ข้อ 1) ส่วนโค้ด
คอมเมนต์ docstring และ commit message ยังคงเป็นภาษาอังกฤษ `docs/DEMO.md`
สร้างจาก `scripts/prepare_demo.py` และ `docs/EVIDENCE.md` ต้องคงคำสั่งกับ output block
ตามต้นฉบับระหว่างแปล

---

## 1. กับดักที่จะทำให้คุณเสียงานทั้งวัน — อ่านข้อนี้ก่อนทุกอย่าง

**งานของวันที่ 2026-10-20 ทั้ง 13 commits ยังไม่อยู่บน `main`** อยู่บน branch
`fix/demo-parity-section` = **PR #16 ที่ยังเปิดอยู่**

ตรวจแล้ว: `git merge-base --is-ancestor HEAD origin/main` → ไม่ใช่ ancestor

**ถ้าคุณแตก branch จาก `main` คุณจะไม่มี:**

- การแก้ fallback ใน `ScanPage` (`ServerUnreachableError`)
- ไฟล์ snapshot `public/api/v1/config` และ `public/api/v1/kb`
  — **ขาดสองไฟล์นี้ static deploy ตายทั้งใบ**
- `public/_redirects`
- TLS แบบ opt-in (`vite.https.ts`)
- เอกสารภาษาไทยทั้งหมด รวมหน้าที่คุณกำลังอ่าน

**ให้เลือกหนึ่งทาง:**

1. ขอให้มนุษย์ merge PR #16 เข้า `main` ก่อน แล้วคุณแตกจาก `main` ตามปกติ — **แนะนำ**
2. หรือแตก branch จาก `fix/demo-parity-section` แล้วบอกไว้ใน PR ของคุณว่าฐานคือ branch นั้น

PR #14 (เอกสารความพร้อมสาธิต ของคุณเอง) และ PR #15 (prompt ส่งต่อ) ก็ยังเปิดอยู่
ทั้งสามอิสระต่อกัน

---

## 2. Claude Code เข้าไปแก้ `frontend/` ซึ่งเป็นสไลซ์ของคุณ — สองครั้ง

ผิดจากการแบ่งงานใน `AGENTS.md` หัวข้อ 1a โดยรู้ตัว เหตุผลและขอบเขตบันทึกไว้ใน
`docs/STATE.md` แล้ว ตอนนั้นไม่มีงานของคุณค้างอยู่ (PR #14 เป็น docs เท่านั้น)
**ต่อจากนี้ไฟล์เหล่านี้เป็นของคุณ**

| ไฟล์ | เปลี่ยนอะไร |
|---|---|
| `src/lib/api.ts` | เพิ่ม `ServerUnreachableError` และ `isServerUnreachable` แก้ `catch` ของ `fetch` ให้ปล่อย `AbortError` ผ่าน |
| `src/pages/ScanPage.tsx` | `submit()` ย้อนไปรันบนเครื่องเฉพาะเมื่อต่อเซิร์ฟเวอร์ไม่ถึง |
| `src/lib/server-unreachable.test.ts` | ใหม่ 8 tests |
| `src/pages/ScanPage.test.tsx` | เพิ่ม 2 tests และ mock ของ `offline` / `storage` |
| `vite.https.ts` | ใหม่ TLS แบบ opt-in ผ่าน `TEASMART_DEV_CERT_DIR` |
| `src/test/vite-https.test.ts` | ใหม่ 5 tests |
| `vite.config.ts` | เพิ่ม 3 บรรทัด — import กับ `https: devHttps(process.env)` **ไม่แตะ `server.proxy`** |
| `public/_redirects` | ใหม่ SPA fallback |
| `public/api/v1/config`, `public/api/v1/kb` | ใหม่ **เป็นไฟล์ generate** โดย `scripts/snapshot_api.py` ห้ามแก้ด้วยมือ |
| `README.md` | ลบการอ้างถึง worktree ที่ถูกลบแล้ว และลิงก์ที่เสีย |

การเปลี่ยนที่ `vite.config.ts` เป็นแบบ **เพิ่มเข้าไปและ opt-in** — ถ้าไม่ตั้ง
`TEASMART_DEV_CERT_DIR` ทั้ง dev server, build และ CI ทำงานเหมือนเดิมทุกอย่าง

---

## 3. ปัญหาที่ยังเหลือก่อนสาธิต เรียงตามความสำคัญ

### ต้องเสร็จก่อนขึ้นเวที

**P0-1 · deploy static — เตรียมครบ รอเลือก host · เจ้าของ: ผู้ใช้ + คุณ**
ขั้นตอนครบใน [docs/DEPLOY-TH.md](DEPLOY-TH.md) ตัดสินใจแล้วว่า deploy
**เฉพาะ frontend ไม่ deploy backend** เพื่อให้กรรมการสแกน QR เปิดบนมือถือตัวเอง
ไม่ต้องติดตั้งอะไร และรูปไม่ออกจากเครื่องกรรมการ
ลำดับคือ: รัน backend → `python scripts/snapshot_api.py` → `npm run build` → อัปโหลด `dist`
**ห้าม build โดยไม่ snapshot ก่อน**

**P0-2 · สแกนหลังติดตั้ง PWA แล้วปิดเน็ต ยังไม่มีใครวัด · เจ้าของ: คุณ**
นี่คือสไลซ์ของคุณตรง ๆ และเป็นข้อที่กรรมการตัดสิน
ไฟล์ snapshot ไม่มีนามสกุล จึงไม่เข้า `globPatterns` ของ VitePWA และ build ยังรายงาน
**precache 13 entries** เท่าเดิม service worker จึงไม่ได้ precache `config` กับ `kb`
ผลขึ้นกับว่าปุ่ม `เตรียมใช้งานออฟไลน์` เก็บ config ไว้เองหรือไม่ — **ยังไม่มีใครกดวัด**
ถ้าไม่ผ่าน ทางแก้คือเพิ่มสองไฟล์เข้า precache หรือให้ปุ่มนั้นเก็บลง IndexedDB
**วัดก่อนแก้** และถ้าเพิ่มเข้า precache ให้ตรวจว่าจำนวน entries เปลี่ยนจริง

**P0-3 · `_redirects` ยังไม่ยืนยัน · เจ้าของ: คุณ หลัง deploy**
`python -m http.server` ไม่อ่านไฟล์นี้ `/kb` จึงตอบ 404 ตอนทดสอบในเครื่อง
Cloudflare Pages และ Netlify อ่านเอง แต่ยืนยันได้หลัง deploy จริงเท่านั้น
ทางเข้าหลักไม่พึ่งมันเพราะ `App.tsx` ส่ง route `*` ไป `/scan` อยู่แล้ว
**QR ต้องชี้ไป root ไม่ใช่ `/scan`**

**P0-4 · รันบนมือถือจริง ยังไม่มีผล · เจ้าของ: ผู้ใช้**
ผู้ใช้ติดตั้ง root CA บน iPhone แล้วและกำลังเปิดแอปตอนจบวัน
ยืนยันจากเครื่องผู้ใช้แล้วว่า `/scan` = 200, `/api/v1/config` = 200, CA server = 200
แต่**ข้อ 1-7 ใน [docs/PHONE-TH.md](PHONE-TH.md) ยังไม่มีใครยืนยันแม้ข้อเดียว**

### P2 — เป็นของ `frontend/` ทั้งสองข้อ

**P2-1 · `src/lib/api.ts` hard-code รายชื่อคลาส**
ซ้ำกับที่ `GET /api/v1/config` เสิร์ฟ วันนี้ค่าตรงกัน **การมีสำเนาที่สองคือตัวปัญหา**
`docs/DESIGN.md` หัวข้อ 8 บอกให้อ่านจาก endpoint

**P2-2 · `parseKnowledge` บังคับให้มี record เท่ากับ 6 รายการพอดี**
โรคที่เจ็ดจะทำให้ client พัง `scripts/snapshot_api.py` มี test ที่เฝ้าเรื่องนี้ฝั่ง backend แล้ว
แต่ฝั่ง client ยังพัง

**P2-3 · `TEASMART_CORS_ORIGINS`**
ต้องตั้งถ้า PWA ที่ build ถูกเสิร์ฟจาก origin อื่นที่ไม่ใช่ `localhost:5173`
**แผนที่เลือกไว้คือ static-only จึงไม่มี backend และข้อนี้ไม่มีผล** แต่ถ้าเปลี่ยนใจ
ไป deploy backend ด้วย ข้อนี้กลับมาทันที dev proxy ปิดปัญหานี้ไว้ จะไม่เห็นในเครื่อง

### P3 — ไม่ต้องทำก่อนสาธิต

- fp16 ONNX จะลดโมเดลจาก 16.8 MB เหลือราว 8.4 MB **ยังไม่ทดสอบ**
- แหล่ง Kaggle สองแหล่งและ HuggingFace ที่ต้องขออนุญาต ปิดอยู่เพราะไม่มี credential
- 32 ภาพถูกสองแหล่งติดป้ายไม่เหมือนกัน ถูกตัดทิ้งแทนที่จะเดา
- warning `inlineDynamicImports` ของ VitePWA ยังค้างอยู่ตอน build

---

## 4. ตัวเลขที่พูดผิดแล้วเสียหาย

- **ไม่มีค่า sensitivity ของการตรวจใบไหม้ และห้ามอ้าง รวมถึงบนเวที**
  มีแต่ specificity ที่วัดได้ **97.18%** — `docs/EVIDENCE.md` หัวข้อ 5.5
- **specificity สูงอาจหมายความว่าตัววิเคราะห์ไม่ได้มอง** การรันครั้งแรกได้ 99.22%
  ขณะที่หาแผลไม่เจอบนใบที่เป็นโรค **59%** ดูจำนวน no-measurable-lesion ก่อนเชื่ออัตราใด ๆ
- **accuracy 0.987 เป็นขอบบน ไม่ใช่ค่าประมาณความแม่นในสนาม** การแบ่งชุดไม่ได้จัดกลุ่ม
  ตามครั้งที่ถ่าย
- **ตัวจำแนกผิดได้แบบมั่นใจ** มีภาพทดสอบหนึ่งภาพผิดที่ความเชื่อมั่น **0.983**
  ไม่มีหน้าจอไหนนำเสนอผลว่าแน่นอนได้
- **ไม่มีภาพใดในคลังมาจากสิงห์ปาร์ค**
- **threshold ของด่าน 1 และ `min_confidence` วัดมาแล้ว — วัดใหม่ ห้ามขยับมือ**

---

## 5. ตรวจงานอย่างไร

```bash
./scripts/test.sh
```

ต้องจบด้วย `All green.` ขณะส่งงานนี้คือ **163 backend, 120 ml, 73 frontend** และ ruff สะอาด
`test.sh` รันสิ่งเดียวกับที่ CI รันในลำดับเดียวกัน

**รันทั้งชุดก่อน push ทุกครั้ง** CI จับของที่พังมาแล้วครั้งหนึ่ง จากการรันแค่ชุดเดียว
หลังแก้ fixture ที่สองชุดอ่านร่วมกัน

สองชุดใช้ virtualenv แยกกันและ**ไม่เคย activate**:

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
cd ml && ./.venv/Scripts/python.exe -m pytest -q
```

**ห้าม `grep -rn` จาก root ของ repository** มันเดินเข้า `.venv` ทั้งสองต้นและ `data/`
แล้วชน timeout ให้จำกัดขอบเขต เช่น `grep -rn pattern frontend/src`

**`npm run build` ไม่พอที่จะบอกว่า static deploy ใช้ได้** ต้องเสิร์ฟ `dist`
โดยไม่มี backend แล้วดู network จริง วันนี้วิธีนี้คือสิ่งที่เจอว่า `/api/v1/config`
กับ `/api/v1/kb` ตอบ 404 ทั้งที่หน้าเว็บเรนเดอร์ปกติ
