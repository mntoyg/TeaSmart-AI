# CURRENT STATUS (อัปเดตทุกครั้งที่จบงาน)

วันที่: 2026-11-03
เว็บสาธารณะ: https://teasmart-ai.vercel.app (build จาก `frontend/`)
branch งานล่าสุด: feat/frontend-command-palette

## ทำอะไรไปล่าสุด
- ลิงก์สาธารณะกลับมาใช้แอป `frontend/` ที่โหลดโมเดลบนเครื่อง (PR #42)
- เพิ่ม onboarding, คู่มือถ่ายรูป, สรุปใบวันนี้, ส่งต่อ/พิมพ์, ค้นคลังความรู้, โหมดนำเสนอ (PR #40)
- รอบนี้: command registry, Command Palette, คีย์ลัด, หน้าช่วยเหลือ, วางภาพจากคลิปบอร์ด, Toast, ส่งออก CSV, โหมดมืด

## ค้างอยู่
- ทดสอบบนมือถือจริงกับภาพทุกคลาส และปรับ `min_confidence` ตามผลโมเดลจริง
- กรอก `frontend/src/data/contacts.ts` และภาพตัวอย่างใน `frontend/public/samples/`

## คำสั่งทดสอบ
cd frontend && npm ci && npm test && npm run build
