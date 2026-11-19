---
name: frontend-design
description: ออกแบบและปรับหน้าเว็บ TeaSmart ให้ตรง design system เดิม ใช้เมื่อสร้างหรือแก้ component, CSS, เลย์เอาต์ หรือสถานะ UI ใน frontend/src
---

# frontend-design

อ่าน `project-brain/DESIGN_SYSTEM.md` และ `project-brain/ARCHITECTURE.md` ก่อนทุกครั้ง

## ขั้นตอน
1. ดูคลาสและ token ที่มีใน `frontend/src/index.css` ก่อน ถ้ามีของใกล้เคียงให้ใช้ซ้ำ
2. ร่างสถานะทั้งหมดของ UI ก่อนเขียน: ว่าง, กำลังโหลด, สำเร็จ, ผิดพลาด, ออฟไลน์, ไม่มั่นใจ
3. เขียน component เป็น function component + `type Props` ไอคอนจาก `lucide-react` ขนาด 15–23
4. เพิ่ม CSS ท้าย `index.css` เป็นกลุ่มตามชื่อ component ไม่แก้กฎเดิม
5. ตรวจที่ 320px และ 1280px, ปุ่มสูง ≥44px, focus ring เดิมยังอยู่, แอนิเมชันเคารพ `prefers-reduced-motion`
6. ทุก action ที่ผู้ใช้กดได้ต้องมาจาก `frontend/src/commands/registry.ts` ถ้าเป็นคำสั่งที่ควรเรียกจากคีย์ลัดหรือ palette ได้

## ห้าม
- เพิ่มฟอนต์ ไลบรารี UI หรือเปลี่ยนโทนสีโดยไม่บันทึกใน DECISIONS
- แสดงชื่อโรคแบบฟันธงเมื่อผลไม่มั่นใจ หรือแสดงสารเคมีกับใบปกติ
- แต่งข้อความโรค สารเคมี หรือเบอร์ติดต่อขึ้นเอง

## ตรวจก่อนส่ง
`cd frontend && npm test && npm run build` แล้วแปะผล และระบุสิ่งที่ยังไม่ได้ทดสอบด้วยมือ (เช่น มือถือจริง)
