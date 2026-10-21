# CLAUDE.md

**อ่าน [AGENTS.md](AGENTS.md)** ซึ่งเป็นแหล่งข้อมูลหลักเพียงแห่งเดียวของโครงการนี้ ทั้งกฎ สถาปัตยกรรม ข้อจำกัด และวินัยการใช้โควตา จากนั้นอ่าน [docs/STATE.md](docs/STATE.md) เพื่อดูสถานะปัจจุบันของงาน

ไฟล์นี้เพิ่มเฉพาะข้อกำหนดของ Claude Code

## กฎสามข้อที่มักลืม

1. ตอบผู้ใช้เป็น **ภาษาไทย** และเขียนเอกสารเป็น **ภาษาไทย** (เปลี่ยนเมื่อ 2026-10-20 ดูข้อ 1 ใน `AGENTS.md` สำหรับขอบเขต) โค้ดและ commit ใช้ภาษาอังกฤษ
2. **Commit และ push หลังจบแต่ละขั้น** อย่ารอจนจบ session
3. รัน test ผ่าน virtualenv ของแพ็กเกจ: จาก `backend/` หรือ `ml/` ใช้ `./.venv/Scripts/python.exe -m pytest -q` คำสั่ง `python` เปล่าไม่มี dependency ที่ต้องใช้

## ขั้นตอนทำงาน

โครงการนี้ใช้ superpowers skills ตามลำดับต่อไปนี้:

| สถานการณ์ | skill |
|---|---|
| เริ่มสไลซ์หรืองานใหม่ | `superpowers:brainstorming` → `writing-plans` → `executing-plans` |
| พบ bug หรือผลที่ไม่คาดคิด | `superpowers:systematic-debugging` |
| ก่อนยืนยันว่าบางอย่างทำงานได้ | `superpowers:verification-before-completion` |
| branch เสร็จแล้ว | `superpowers:requesting-code-review` แล้วตามด้วย `finishing-a-development-branch` |

ตอนนี้ไม่มีไฟล์แผนแยกแล้ว เมื่อทำสไลซ์ให้อ่านเอกสารย่อของงานนั้นแทนการอ่านแผนทั้งหมด และบันทึกบรรทัดสถานะใน tool call เดียวกับ commit เพราะ context ไม่อยู่ข้ามการย่อบทสนทนา แต่บันทึกสถานะอยู่

**เมื่อใช้ context ไปประมาณ 70%** ให้จบงานปัจจุบันก่อน แล้วเขียน prompt ส่งต่อ session ถัดไป อัปเดต `docs/STATE.md` และ push เพื่อนำไปทำต่อ เพดานการใช้ต่อวันใน `AGENTS.md` สำคัญกว่าคำแนะนำเรื่อง context: AI ทุกตัวต้องหยุดที่จุดที่ push แล้ว ก่อนใช้เกิน 14% ของ weekly capacity ต่อวันตามปฏิทินกรุงเทพฯ

## บันทึกสภาพแวดล้อมที่ช่วยลดการลองผิดซ้ำ

- Bash heredoc ในสภาพแวดล้อมนี้พังเมื่อเนื้อหามี apostrophe ใช้เครื่องมือเขียนไฟล์ หรือเขียน patch script ใน scratchpad แล้วรัน
- `grep -rn` จาก root จะเดินเข้า virtualenv ทั้งสองและ `data/` จนคำสั่งหมดเวลา จำกัดขอบเขตค้นหาไว้ที่ `ml/teasmart_ml` หรือ `backend/app`
- test สองชุดใช้ virtualenv แยกกัน
- Mendeley ปฏิเสธ urllib3 แต่ตอบ curl ได้ จึงให้ shell ของ `ml` เรียก curl เพื่อดาวน์โหลดตามที่กำหนดไว้ ดูเหตุผลใน `docs/DESIGN.md` หัวข้อ 13
- งานที่ใช้เวลานาน เช่น เตรียมชุดข้อมูลและ train ให้รันเบื้องหลัง

## สิ่งที่ไม่ควรอ่าน

`data/`, virtualenv ทั้งสอง (`.venv/`) และ `*.onnx` ไม่ช่วยให้เข้าใจงาน และระบุไว้ใน `.claudeignore` ข้อมูลรับรองถูกปิดกั้นใน `.claude/settings.json` หากเห็นว่าจำเป็นต้องใช้ไฟล์เหล่านี้ ให้ถามก่อน
