# DESIGN SYSTEM

ยึดของเดิมใน `frontend/src/index.css` — ห้ามเปลี่ยนฟอนต์/โทนโดยไม่ได้รับอนุมัติ

## ฟอนต์
"IBM Plex Sans Thai", "Noto Sans Thai", Tahoma, sans-serif (พื้นฐาน เรียบ ไม่เพิ่มฟอนต์ตกแต่ง)

## สี (tokens ใน `:root`)
--green-900 #193c2b · --green-800 #24533a · --green-700 #2f6a49
--green-100 #e8f0e6 · --green-50 #f0f5ed · --cream #f6f7f1
--muted #78877b · --line #e5e9df
เตือน = โทนเหลืองอำพัน (#fff6df / #87652e), ผิดพลาด = โทนแดงอ่อน (#fff0ed / #a53c2e)

## รูปทรง
มุมโค้ง 12–23px, เงานุ่ม `--shadow`, การ์ดขาวบนพื้นครีม, ไอคอน lucide-react ขนาด 15–23

## คลาสที่มีแล้ว (ใช้ซ้ำก่อนสร้างใหม่)
`.ts-button .button-primary .button-secondary` · `.alert .alert-error .alert-warning` ·
`.plan-card` · `.knowledge-card` · `.history-chip` · `.demo-notice` · `.ts-eyebrow` · `.card`
คลาสที่ชนกับสไตล์เดิมของ repo ใช้ prefix `ts-` (ดู docs/STATE.md สไลซ์ 1.1)

## โหมดมืด
สีที่ขึ้นกับธีมอยู่ใน token ของ `:root` และชุดมืดใน `:root[data-theme="dark"]`
ตัวเลือกผู้ใช้เก็บใน localStorage `teasmart.theme.v1` ค่า `light | dark | system`
ถ้าเป็น `system` ให้ตาม `prefers-color-scheme` ย้าย hex ที่ฝังตรงไปเป็น token ทีละส่วน
ห้ามแก้ทั้งไฟล์ในครั้งเดียว

## Command Palette / Toast / Help — สไตล์
- overlay `rgba(25,60,43,.35)` + blur เบา, กล่องกลางจอกว้างสูงสุด 560px, มุม 20px
- แถวคำสั่งสูง ≥44px (นิ้วแตะได้), แสดงคีย์ลัดเป็นแท็กเล็กทางขวา
- แถวที่เลือก: พื้น --green-50 + ขอบ --green-100
- Toast อยู่มุมล่างขวาบนเดสก์ท็อป เต็มความกว้างเหนือเมนูล่างบนมือถือ มี role="status"

## การเข้าถึง
- focus ring เดิม (3px #9fc9a8) ห้ามลบ
- ข้อความภาษาไทย line-height ≥ 1.7
- สีไม่ใช่ตัวบอกความหมายอย่างเดียว (ต้องมีไอคอน/ข้อความ)
