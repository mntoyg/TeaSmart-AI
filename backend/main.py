import io
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps

MAX_BYTES = 10 * 1024 * 1024
IMG_SIZE = int(os.getenv("IMG_SIZE", "224"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://teasmart-ai.pages.dev,https://teasmart-ai.vercel.app,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# ลำดับต้องตรงกับ src/data/diseases.ts
CLASSES = [
    (0, "Tea Grey Blight", "โรคใบไหม้เทา"),
    (1, "Tea Brown Blight", "โรคใบไหม้น้ำตาล"),
    (2, "Algal Leaf Spot", "โรคจุดสาหร่าย / สนิมสาหร่าย"),
    (3, "Healthy", "ใบปกติ / สุขภาพดี"),
]

# ค่า mean/std ต้องตรงกับตอนเทรน (ด้านล่างคือ ImageNet ตาม teasmart-v1.onnx)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

SHIPPED_MODEL = Path(__file__).resolve().parent.parent / "frontend" / "public" / "models" / "teasmart-v1.onnx"
state: dict = {"session": None}


def model_path() -> str:
    configured = os.getenv("MODEL_PATH", "model/tea_leaf.onnx")
    if os.path.exists(configured):
        return configured
    if configured == "model/tea_leaf.onnx" and SHIPPED_MODEL.is_file():
        return str(SHIPPED_MODEL)
    return configured


def load_model():
    """โหลดโมเดลครั้งเดียวตอนเริ่มเซิร์ฟเวอร์"""
    import onnxruntime as ort

    path = model_path()
    if not os.path.exists(path):
        return None
    return ort.InferenceSession(path, providers=["CPUExecutionProvider"])


def predict_probs(image: Image.Image) -> list[float]:
    session = state["session"]
    if session is None:
        raise HTTPException(503, "ระบบโมเดลยังไม่พร้อม กรุณาลองใหม่ภายหลัง")
    img = ImageOps.exif_transpose(image).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
    arr = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    arr = np.transpose(arr, (2, 0, 1))[None, ...]
    input_name = session.get_inputs()[0].name
    logits = np.asarray(session.run(None, {input_name: arr})[0][0], dtype=np.float32)
    exp = np.exp(logits - np.max(logits))
    probs = (exp / exp.sum()).tolist()
    # teasmart-v1.onnx มีคลาสที่ 5 คือ other_disease ซึ่งไม่อยู่ในสัญญา 4 คลาส
    # ไม่ปรับสัดส่วนใหม่ เพื่อให้ความมั่นใจต่ำยังขึ้นว่ายังสรุปไม่ได้
    if len(probs) == 5:
        probs = probs[:4]
    return probs


@asynccontextmanager
async def lifespan(_: FastAPI):
    state["session"] = load_model()
    yield


app = FastAPI(title="TeaSmart API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": state["session"] is not None}


@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(400, "ไฟล์ต้องเป็นรูปภาพ JPG, PNG หรือ WEBP")
    data = await image.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "ไฟล์ใหญ่เกิน 10 MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise HTTPException(400, "เปิดไฟล์ภาพนี้ไม่ได้")

    probs = predict_probs(img)
    if len(probs) != len(CLASSES):
        raise HTTPException(500, "จำนวนคลาสของโมเดลไม่ตรงกับระบบ (ต้องเป็น 4 คลาส)")

    ranked = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    top = ranked[0]
    return {
        "class_id": CLASSES[top][0],
        "class_name": CLASSES[top][1],
        "disease_name_th": CLASSES[top][2],
        "confidence": round(float(probs[top]), 4),
        "top_k": [
            {"class_id": CLASSES[i][0], "confidence": round(float(probs[i]), 4)} for i in ranked[:3]
        ],
    }
