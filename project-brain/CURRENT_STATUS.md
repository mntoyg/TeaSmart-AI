# CURRENT STATUS (อัปเดตทุกครั้งที่จบงาน)

วันที่: 2026-11-03
เว็บสาธารณะ: https://teasmart-ai.vercel.app (build จาก `frontend/`)
branch งานล่าสุด: feat/frontend-command-palette

## ทำอะไรไปล่าสุด
- ลิงก์สาธารณะกลับมาใช้แอป `frontend/` ที่โหลดโมเดลบนเครื่อง (PR #42)
- เพิ่ม onboarding, คู่มือถ่ายรูป, สรุปใบวันนี้, ส่งต่อ/พิมพ์, ค้นคลังความรู้, โหมดนำเสนอ (PR #40)
- รอบนี้ (3 commit บน branch นี้):
  - เฟส 1: `src/commands/registry.ts` + `useShortcuts.ts`, `CommandPalette.tsx`, `ShortcutHelp.tsx`,
    วางภาพจากคลิปบอร์ดลงหน้าสแกน, ปุ่มค้นหาคำสั่งใน header (ลอยมุมล่างขวาบนมือถือ)
  - เฟส 2: `lib/toast.ts` + `ToastHost.tsx`, `lib/exportCsv.ts` (ปุ่ม "ส่งออก CSV" บนหน้าประวัติ, คำสั่ง e),
    `lib/theme.ts` + ปุ่มสลับธีมใน header (คำสั่ง t), token สีใหม่ `--surface --surface-soft --text`
    และชุดมืดใน `:root[data-theme="dark"]` ทั้ง `index.css` และ `styles.css`
  - แก้บั๊กเดิม: เมนูล่างบนมือถือเคยไปเกาะใต้ header เพราะ `backdrop-filter` (DECISIONS D-009)

## ตรวจแล้ว
- `npx tsc -b` ผ่าน, `npx vitest run` 140 เทสต์ผ่าน (24 ไฟล์), `npm run build` ผ่าน
- เปิดใน Cursor browser: palette เปิดด้วย Ctrl+K, กรองคำไทย, Enter สั่งงาน; ธีมมืดจำค่าและเปลี่ยน meta theme-color;
  toast แสดงเหนือเมนูล่าง; จอ 320px ไม่มี scroll แนวนอน

## ยังไม่ได้ตรวจ (ต้องทำด้วยมือ)
- บนมือถือจริง: วางภาพ Ctrl/Cmd+V, ติดตั้ง PWA, เปิดออฟไลน์, อ่านจอกลางแดด
- ความรู้สึกของคีย์ลัดเมื่อใช้งานจริง และ contrast ของตัวอักษรรอง (`--muted`) บนพื้นสว่าง
- ทดสอบภาพจริงทุกคลาส แล้วปรับ `min_confidence` (0.60) ตามผลโมเดล
- ใน dev `/api/v1/*` proxy ไป `127.0.0.1:8000` ถ้า backend ไม่รัน คำสั่ง "เปิดความรู้: <โรค>" จะไม่ขึ้นใน palette
  (บนเว็บจริงใช้สำเนาใน `frontend/public/api/v1/` จึงขึ้นครบ)

## ค้างอยู่
- กรอก `frontend/src/data/contacts.ts` และภาพตัวอย่างใน `frontend/public/samples/`

## คำสั่งทดสอบ
cd frontend && npm ci && npm test && npm run build
