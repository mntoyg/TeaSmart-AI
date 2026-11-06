# HANDOFF (เขียนทับทุกครั้งที่จบ session)

## session ล่าสุด
วันที่: 2026-11-06
ใคร: Nathakorn + Cursor
branch: feat/api-backend-service

## ทำอะไรไป (ไฟล์ที่แก้)
- `vercel.json` เพิ่ม service backend และ rewrite `/api` กับ `/health`
- `backend/app/asgi.py`, `backend/scripts/stage_model.py`, CORS ใน `config.py` / `main.py`, `active_model_path` ใน `scan.py`
- `frontend/src/lib/api.ts` ให้ 404/405 ที่ไม่มีคำอธิบายภาษาไทยตกไปโมเดลบนเครื่อง
- ยังไม่ได้ขึ้น production จนกว่า preview จะตอบ `/health` และ `POST /api/v1/scan`

## ค้างอยู่ / ติดอะไร
- ทดสอบภาพจริงบนมือถือ และตัดสินค่า min_confidence หลังเห็นผลโมเดล
- ยังไม่ได้ลอง Ctrl/Cmd+V, ติดตั้ง PWA และโหมดมืดกลางแดดบนเครื่องจริง (รายการเต็มใน CURRENT_STATUS)

## คำสั่งทดสอบ
cd frontend && npm ci && npm run dev
cd frontend && npm test && npm run build

## สิ่งที่คนถัดไปต้องรู้ก่อนแตะ
- เว็บสาธารณะ build จาก `frontend/` (DECISIONS D-008) และส่ง `/api` ไปที่ backend (D-011) หน้าตัวอย่างที่ราก repo ไม่ใช่ตัวที่ขึ้นเว็บ
- บนดิสก์ E: ต้องใช้ `git -c safe.directory=E:/TeaSmart ...` หรือเพิ่ม safe.directory เองครั้งเดียว

## เปิด session ใหม่ใน Cursor ให้พิมพ์
"อ่าน AGENTS.md, project-brain/CURRENT_STATUS.md และ HANDOFF.md แล้วสรุปว่าเราอยู่ตรงไหน ยังไม่ต้องแก้โค้ด"
