# TeaSmart Frontend

หน้าเว็บช่วยคัดกรองโรคใบชา สร้างด้วย React, TypeScript และ Vite

ตอนนี้ยังไม่มีโมเดล AI ผลวิเคราะห์เป็นโหมด Demo และมีป้ายบอกชัดเจนว่าไม่ใช่การวินิจฉัยจริง

## รันในเครื่อง

```bash
npm install
npm run dev
```

เปิด http://localhost:5173

## เชื่อม Backend ภายหลัง

คัดลอก `.env.example` เป็น `.env.local` แล้วตั้ง

```
VITE_API_BASE_URL=http://localhost:8000
```

หน้าเว็บส่งภาพเป็น `multipart/form-data` ฟิลด์ชื่อ `image` ไปที่ `POST /predict`

รูปแบบที่รับได้:

```json
{ "class_id": 1, "confidence": 0.924 }
```

`class_id` ต้องตรงกับ `src/data/diseases.ts`

- 0 Tea Grey Blight
- 1 Tea Brown Blight
- 2 Algal Leaf Spot
- 3 Healthy

ถ้าไม่ส่ง `VITE_API_BASE_URL` ระบบจะคงอยู่ที่โหมด Demo
