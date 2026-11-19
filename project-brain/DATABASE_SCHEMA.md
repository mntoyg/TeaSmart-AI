# DATABASE_SCHEMA

## ไม่มีฐานข้อมูลฝั่งเซิร์ฟเวอร์
- ผลสแกนที่เซิร์ฟเวอร์ตอบถูกเก็บในหน่วยความจำชั่วคราวเพื่อกัน idempotency เท่านั้น
- บันทึกถาวรอยู่ในเบราว์เซอร์ของผู้ใช้

## IndexedDB ฝั่งเบราว์เซอร์ (มีแล้ว — `frontend/src/lib/storage.ts`)
DB name: `teasmart` version 3 (ไลบรารี `idb`)

### store `scans` (keyPath: scan_id)
เก็บ `StoredResult` ทั้งระเบียน (ScanResponse จากเซิร์ฟเวอร์ หรือ LocalResult จากอุปกรณ์)
ไม่มีภาพต้นฉบับ (ดู DECISIONS D-007)

### store `queue` (keyPath: scan_id)
ภาพที่รอส่งเซิร์ฟเวอร์ `imageBytes`, `imageType`, `state: pending | failed`, `attempts`, `detail_th`
ลบออกเมื่อเซิร์ฟเวอร์ตอบ

### store `metadata` (key `kb`) และ `config` (key `client`)
สำเนาฐานความรู้และการตั้งค่าโมเดลสำหรับใช้ออฟไลน์

## localStorage
- `teasmart.readiness.v1` แผนวันนี้ (รีเซ็ตตามวันเวลาไทย)
- `teasmart.onboarded.v1` เคยเห็นหน้าแนะนำแล้ว
- `teasmart.theme.v1` ธีม `light | dark | system`

## ส่งออก CSV
คอลัมน์: scan_id, captured_at, result_th, class_name, confidence, analysis_mode, severity_level
สร้างจาก `store.list()` ในเบราว์เซอร์ ไม่ส่งไปที่ไหน

กฎ: ถ้า IndexedDB ใช้ไม่ได้ (โหมดส่วนตัว) แจ้งด้วย toast ว่าประวัติจะไม่ถูกบันทึก

## แผนอนาคต (ยังไม่ทำ — ต้องตัดสินใจก่อน ดู DECISIONS)
ถ้าจะทำ sync หลายอุปกรณ์/หลายคน ต้องมีข้อตกลงเรื่องข้อมูลภาพ/ความเป็นส่วนตัวก่อน
