# TeaSmart `/predict`

เซิร์ฟเวอร์นี้รับรูปใบชาแล้วตอบตามสัญญาที่หน้าสแกนใช้ ไม่เก็บริปลงดิสก์

พอร์ตนี้คือ `uvicorn main:app` ชุด API เดิมของโปรเจกต์ยังอยู่ที่ `app.main:create_app` และไม่ได้ถูกแทนที่

## โมเดล

วางไฟล์ที่ `backend/model/tea_leaf.onnx` หรือตั้ง `MODEL_PATH`

ถ้าไม่ตั้งค่า และยังไม่มีไฟล์นั้น เซิร์ฟเวอร์จะใช้กราฟที่มีอยู่แล้วที่ `frontend/public/models/teasmart-v1.onnx`

กราฟนั้นเป็น ONNX 224×224 ใช้ค่า normalize แบบ ImageNet และมี 5 ค่าออก ค่าที่ห้าคือ `other_disease` ซึ่งไม่อยู่ในสัญญา 4 คลาส จึงไม่ถูกส่งกลับ และไม่ถูกปรับสัดส่วนใหม่

## รัน

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

บน macOS หรือ Linux ใช้ `source .venv/bin/activate` แทนบรรทัด activate

`requirements.txt` ของโฟลเดอร์นี้มี fastapi, uvicorn, python-multipart, pillow, numpy และ onnxruntime อยู่แล้ว จึงไม่ได้เขียนทับรายการของชุด API เดิม

## ตัวแปร

- `MODEL_PATH` ค่าเริ่มต้น `model/tea_leaf.onnx`
- `IMG_SIZE` ค่าเริ่มต้น `224`
- `ALLOWED_ORIGINS` คั่นด้วยจุลภาค ไม่ใช้ `*`

## ทดสอบ

```powershell
curl http://localhost:8000/health
curl -F image=@leaf.jpg http://localhost:8000/predict
```

`/health` ตอบ `{ "ok": true, "model_loaded": true }` เมื่อโหลดไฟล์โมเดลได้ ถ้าไม่มีไฟล์ `model_loaded` เป็น `false` และ `/predict` ตอบ 503

## Deploy

หน้าเว็บเป็น HTTPS จึงเรียก backend ที่เป็น HTTP ไม่ได้ ตัวเลือกสำหรับเดโมคือ `cloudflared tunnel --url http://localhost:8000` แล้วนำลิงก์ `https://....trycloudflare.com` ไปใส่ `VITE_API_BASE_URL` และใส่โดเมนเว็บใน `ALLOWED_ORIGINS`

สำหรับเครื่องถาวร ใช้ `backend/Dockerfile` บน Hugging Face Spaces, Render หรือ Railway แล้วใส่ไฟล์โมเดลผ่าน `MODEL_PATH`
