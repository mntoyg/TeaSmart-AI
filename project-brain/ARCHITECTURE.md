# ARCHITECTURE

## โครงสร้างปัจจุบัน (ตามโค้ดจริงใน `frontend/`)
```
frontend/src/
  main.tsx                ErrorBoundary + BrowserRouter + service worker
  App.tsx                 เส้นทาง, ฐานความรู้, config, คิวออฟไลน์, แผนวันนี้
  index.css               สไตล์ดีไซน์ใหม่ + design tokens (:root)
  styles.css              สไตล์เดิมของ repo (โหลดก่อน index.css)
  types.ts                Disease, PredictionResult
  components/
    AppHeader.tsx         เมนูบน/ล่าง + สถานะโมเดล
    ScanPanel.tsx         อัปโหลด/กล้อง/วิเคราะห์ + คู่มือถ่ายรูป
    DiagnosisResult.tsx   ผลวิเคราะห์ + คัดลอก/ส่งต่อ/พิมพ์
    KnowledgePanel.tsx    คลังความรู้ + ค้นหา/กรอง
    ReadinessPanel.tsx    เช็กก่อนอ่าน
    TodayPlanCard.tsx     แผนวันนี้
    OfflinePanel.tsx      สถานะออฟไลน์และคิว
    Onboarding.tsx, PhotoGuide.tsx, SiteFooter.tsx
  pages/ScanPage.tsx      ฟลว์สแกน: เซิร์ฟเวอร์ก่อน ตกไปอุปกรณ์เมื่อไม่ตอบ
  lib/
    api.ts                /api/v1/scan, /kb, /config
    storage.ts            IndexedDB (idb): scans, metadata, config, queue
    offline.ts, onnx-worker.ts, inference.ts, quality.ts, leaf.ts
    queue.ts              ส่งคิวซ้ำผ่าน /api/v1/sync/batch
    readiness.ts, result-view.ts, todaySummary.ts
  data/contacts.ts        เบอร์เจ้าหน้าที่ (ว่างจนกว่าทีมกรอก)
```

## โครงสร้างที่เพิ่มรอบนี้
```
frontend/src/
  commands/
    registry.ts           รายการคำสั่งทั้งหมด (id, label, keywords, shortcut, run, enabled)
    useShortcuts.ts       hook ฟังคีย์ลัดทั้งแอป
  components/
    CommandPalette.tsx    หน้าต่าง Ctrl/Cmd+K
    ShortcutHelp.tsx      หน้าช่วยเหลือ (กด ?)
    ToastHost.tsx
  lib/
    exportCsv.ts          แปลงประวัติเป็น CSV
    theme.ts              อ่าน/เขียนธีม + data-theme
    toast.ts              คิว toast แบบไม่พึ่ง state library
```

## หลักการ
1. คำสั่งทุกอย่าง (ปุ่ม, คีย์ลัด, palette) เรียก action ตัวเดียวกันจาก registry — ห้ามเขียนซ้ำ 3 ที่
2. คีย์ลัดตัวอักษรเดี่ยวต้องไม่ทำงานเมื่อโฟกัสอยู่ใน input/textarea/select/contenteditable
3. state ข้ามหน้าจอยังอยู่ใน App.tsx จนกว่าจะเจ็บจริงค่อยย้ายเข้า context (ไม่ใส่ state library)
4. ข้อมูลโรคมาจากฐานความรู้ที่ backend เสิร์ฟ ไม่คัดลอกไว้ใน TypeScript
5. API contract: `POST /api/v1/scan` multipart field `image` ตอบตาม `docs/DESIGN.md` หัวข้อ 8
   และ `frontend/src/lib/scan-contract.ts` ที่ generate จาก backend ห้ามแก้ฝ่ายเดียว
6. ไม่มีค่าลับในโค้ดฝั่งหน้าเว็บ (ทุกอย่างใน VITE_* เปิดดูได้)
