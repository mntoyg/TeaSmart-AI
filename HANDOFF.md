# HANDOFF (เขียนทับทุกครั้งที่จบ session)

## session ล่าสุด
วันที่: 2026-11-03
ใคร: Nathakorn + Cursor
branch: feat/frontend-command-palette

## ทำอะไรไป (ไฟล์ที่แก้)
- ดู project-brain/CURRENT_STATUS.md
- ใหม่: `frontend/src/commands/*`, `components/CommandPalette.tsx`, `ShortcutHelp.tsx`, `ToastHost.tsx`,
  `lib/theme.ts`, `lib/toast.ts`, `lib/exportCsv.ts` (+ เทสต์คู่กัน)
- แก้: `App.tsx`, `components/AppHeader.tsx`, `pages/ScanPage.tsx`, `components/ScanPanel.tsx`,
  `components/KnowledgePanel.tsx`, `index.css`, `styles.css`

## ค้างอยู่ / ติดอะไร
- ทดสอบภาพจริงบนมือถือ และตัดสินค่า min_confidence หลังเห็นผลโมเดล
- ยังไม่ได้ลอง Ctrl/Cmd+V, ติดตั้ง PWA และโหมดมืดกลางแดดบนเครื่องจริง (รายการเต็มใน CURRENT_STATUS)

## คำสั่งทดสอบ
cd frontend && npm ci && npm run dev
cd frontend && npm test && npm run build

## สิ่งที่คนถัดไปต้องรู้ก่อนแตะ
- เว็บสาธารณะ build จาก `frontend/` (DECISIONS D-008) หน้าตัวอย่างที่ราก repo ไม่ใช่ตัวที่ขึ้นเว็บ
- บนดิสก์ E: ต้องใช้ `git -c safe.directory=E:/TeaSmart ...` หรือเพิ่ม safe.directory เองครั้งเดียว

## เปิด session ใหม่ใน Cursor ให้พิมพ์
"อ่าน AGENTS.md, project-brain/CURRENT_STATUS.md และ HANDOFF.md แล้วสรุปว่าเราอยู่ตรงไหน ยังไม่ต้องแก้โค้ด"
