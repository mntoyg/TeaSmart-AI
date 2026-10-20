# deploy ให้กรรมการใช้ได้โดยไม่ต้องติดตั้งอะไร

เป้าหมาย: กรรมการสแกน QR เปิดบนมือถือตัวเอง ได้กล้อง ติดตั้งลงหน้าโฮมได้ ใช้ออฟไลน์ได้
**ไม่ต้องลงใบรับรอง ไม่ต้องตั้ง flag ไม่ต้องต่อสาย** และรูปไม่ออกจากเครื่องกรรมการ

เราจึง deploy **เฉพาะ frontend** ไม่ deploy backend ผลที่กรรมการได้คือ `classifier_only`
ส่วนคำตัดสินโรค-กับ-ใบไหม้และความรุนแรง สาธิตจากโน้ตบุ๊กที่รัน pipeline เต็ม

---

## ทำไมต้อง snapshot ก่อน build

วัดแล้วบน bundle ที่ build โดยไม่มี backend: `GET /api/v1/config` และ
`GET /api/v1/kb` ตอบ **404** ทั้งคู่ และทั้งคู่ถึงตาย ไม่ใช่แค่ขัดใจ

- ไม่มี `config` → โมเดลบนเครื่องไม่ยอมรันเลย ขึ้นว่า "ยังไม่มีการตั้งค่าออฟไลน์"
- ไม่มี `kb` → ไม่มีคำแนะนำภาษาไทย ซึ่งคือผลลัพธ์ทั้งหมดของสินค้า

หน้าเว็บยังเรนเดอร์ได้ ซึ่งคือสิ่งที่ทำให้มันอันตราย — ดูเหมือนปกติจนกว่าจะมีคนกดปุ่ม

`scripts/snapshot_api.py` ดึงค่าจาก backend ที่รันอยู่จริงแล้วเขียนเป็นไฟล์ static
ที่ path เดิมที่ client เรียก **ไม่ hard-code และไม่มีแหล่งความจริงที่สอง**

---

## ขั้นตอน

**1. รัน backend ไว้ก่อน** (หน้าต่างหนึ่ง)

```bash
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
```

**2. snapshot แล้ว build** (อีกหน้าต่าง)

```bash
python scripts/snapshot_api.py
```

```bash
cd frontend && npm run build
```

ได้ `frontend/dist` ขนาดราว 39 MB (รวมโมเดล 16.8 MB และ WASM 14.2 MB)
ถ้า snapshot ล้มเหลว script จะ**ไม่เขียนอะไรเลย** เพราะ snapshot ที่ว่างเปล่า
จะ deploy เว็บที่พังแบบเงียบ ๆ

**3. ขึ้น Cloudflare Pages** — ฟรี ไม่จำกัด bandwidth และอ่าน `_redirects` ที่เราใส่ไว้

1. สมัคร / เข้า https://dash.cloudflare.com
2. เมนูซ้าย **Workers & Pages** → **Create** → แท็บ **Pages**
   → **Upload assets** (เลือกแบบอัปโหลดตรง ไม่ต้องต่อ GitHub เพราะ repo เป็น private)
3. ตั้งชื่อโปรเจกต์ เช่น `teasmart` แล้วลากโฟลเดอร์ **`frontend/dist`** ทั้งโฟลเดอร์ลงไป
4. กด **Deploy site** รอจนขึ้น URL รูปแบบ `https://teasmart.pages.dev`

ทางเลือกอื่นที่อ่าน `_redirects` เหมือนกันคือ Netlify (ลาก `dist` ลงหน้า
https://app.netlify.com/drop) ใช้ได้เท่ากัน

> **GitHub Pages ใช้ไม่ได้** repo นี้เป็น private และ Pages สำหรับ private repo
> ต้องมี GitHub Pro นอกจากนั้น GitHub Pages ไม่อ่าน `_redirects` ด้วย

**4. สร้าง QR ตัวจริง**

```bash
python scripts/make_qr.py https://teasmart.pages.dev/
```

**ชี้ไป root ไม่ใช่ `/scan`** เพราะ `App.tsx` ส่ง route `*` ไป `/scan` อยู่แล้ว
root จึงใช้ได้แม้ host ไม่อ่าน `_redirects` — ทนทานกว่า

คำสั่งนี้เขียนทับ `docs/img/app-qr.png` และ README ชี้ไป path คงที่ ไม่ต้องแก้ README
แล้ว commit QR ใหม่

**5. ทดสอบด้วยมือถือตัวเองก่อนวันงาน**

เปิด URL นั้นบนมือถือที่ **ไม่ได้** ต่อ wifi บ้าน (ใช้เน็ตมือถือ) เพื่อให้แน่ใจว่า
ไม่ได้เผลอพึ่งเครื่องในบ้าน แล้วไล่ตามข้อ 1-7 ใน [docs/PHONE-TH.md](PHONE-TH.md)

---

## ที่ยังไม่ได้วัด และต้องวัดก่อนขึ้นเวที

ไฟล์ snapshot ไม่มีนามสกุล จึงไม่เข้า `globPatterns` ของ PWA — build ยังรายงาน
**precache 13 entries** เท่าเดิม แปลว่า service worker ไม่ได้ precache `config`
กับ `kb` ไว้

**ยังไม่รู้ว่าสแกนหลังติดตั้งแล้วปิดเน็ตจะได้ผลหรือไม่** ขึ้นกับว่าปุ่ม
"เตรียมใช้งานออฟไลน์" เก็บ config ไว้เองหรือเปล่า **ต้องกดวัดจริง** ไม่ใช่เดา
ถ้าไม่ผ่าน ทางแก้คือเพิ่มสองไฟล์นี้เข้า precache หรือให้ปุ่มนั้นเก็บลง IndexedDB
