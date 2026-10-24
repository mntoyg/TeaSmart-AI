# Prompt สำหรับสั่ง Cursor

ทำงานต่อจากโค้ดปัจจุบัน อย่าสร้างโปรเจกต์ใหม่ทับทั้งหมด

- `src/services/predictService.ts` เป็นจุดเดียวที่เรียก Backend
- ถ้าไม่มี `VITE_API_BASE_URL` ให้ใช้โหมด Demo และต้องบอกว่าไม่ใช่ผลจาก AI จริง
- อย่าเปลี่ยน class ID หรือชื่อคลาสใน `src/data/diseases.ts` โดยไม่ยืนยันว่าตรงกับ label ของโมเดล
- อย่าลบคำเตือนเรื่องผล Demo และข้อควรระวังการใช้สารเคมี
- 0 Tea Grey Blight, 1 Tea Brown Blight, 2 Algal Leaf Spot, 3 Healthy
