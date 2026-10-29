# สถาปัตยกรรม TeaSmart AI

เอกสารนี้สรุปโครงสร้างที่ตรวจพบใน source และแยกสถานะการ deploy ที่บันทึกไว้ในเอกสาร readiness ออกจากสิ่งที่ยืนยันได้จากโค้ด ไฟล์นี้ไม่ใช่สัญญา API; ให้ยึด [DESIGN.md หัวข้อ 8](DESIGN.md) เป็น interface ระหว่าง frontend กับ backend

## ภาพรวม

~~~mermaid
flowchart LR
  subgraph Device["อุปกรณ์ผู้ใช้ · PWA"]
    UI["React SPA<br/>/scan · /result/:id · /history · /kb"]
    SW["Service worker<br/>shell และ model cache"]
    Worker["Web Worker<br/>quality gate + ONNX classifier"]
    IDB[("IndexedDB<br/>ผล · KB · config · sync queue")]
    UI --> Worker
    UI --> IDB
    UI -->|asset fetch และ cache| SW
  end

  subgraph OptionalServer["Backend เมื่อมีการตั้งค่า endpoint"]
    API["FastAPI<br/>/health · /api/v1/scan · /api/v1/kb · /api/v1/config · /api/v1/sync/batch"]
    Gate["ตรวจและ decode ภาพ"]
    Pipeline["quality → segmentation → classification<br/>lesion → severity → expert system"]
    KB["KB แบบ read-only"]
    API --> Gate --> Pipeline
    Pipeline --> KB
  end

  subgraph ML["งานเตรียมโมเดล"]
    Data["ingest → deduplicate → manifest"]
    Train["PyTorch · MobileNetV3-Large"]
    Export["export ONNX + parity checks"]
    Data --> Train --> Export
  end

  UI -->|"ออนไลน์: scan / config / KB"| API
  IDB -->|"ออนไลน์อีกครั้ง: sync queue"| API
  Export -. "artifact ที่เผยแพร่" .-> Worker
~~~

เส้นทาง server ในภาพเป็นความสามารถของระบบ ไม่ได้ยืนยันว่า backend มี public deployment อยู่แล้ว สถานะ deployment ให้ดูหัวข้อ [ช่องว่างก่อนผู้ใช้จริง](#ช่องว่างก่อนผู้ใช้จริงและขนาดใหญ่) และ [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md)

## องค์ประกอบและเทคโนโลยี

| ส่วน | เทคโนโลยีที่ประกาศใช้ | หน้าที่และหลักฐานใน repository |
|---|---|---|
| Frontend | React 19, TypeScript, Vite 8, React Router 7, Tailwind CSS 4 | SPA และหน้าสแกน/ผล/ประวัติ/ฐานความรู้ใน [App.tsx](../frontend/src/App.tsx); versions ที่ประกาศใน [package.json](../frontend/package.json) และที่ resolve ใน [package-lock.json](../frontend/package-lock.json) |
| PWA และ offline | vite-plugin-pwa แบบ injectManifest, service worker, Web Worker, onnxruntime-web | precache และ manifest ใน [vite.config.ts](../frontend/vite.config.ts); registration ใน [main.tsx](../frontend/src/main.tsx); inference ใน [offline.ts](../frontend/src/lib/offline.ts) และ [onnx-worker.ts](../frontend/src/lib/onnx-worker.ts) |
| ที่เก็บในอุปกรณ์ | IndexedDB ผ่าน idb | [storage.ts](../frontend/src/lib/storage.ts) แยก object store สำหรับผลสแกน, metadata/KB, config และคิวภาพ |
| Backend API | Python 3.12+, FastAPI, Pydantic Settings, Uvicorn | application factory และ router ใน [main.py](../backend/app/main.py); เวอร์ชันที่ pin ใน [requirements.txt](../backend/requirements.txt) |
| วิเคราะห์ภาพฝั่ง server | NumPy, Pillow, OpenCV และ ONNX Runtime | ด่านรับภาพและขั้น pipeline ใน [core/images.py](../backend/app/core/images.py), [scan.py](../backend/app/api/v1/scan.py) และ [services/](../backend/app/services/) |
| เตรียมและฝึกโมเดล | Python 3.12+, PyTorch, torchvision, ONNX | ingestion, manifest, training, evaluation และ export อยู่ใน [ml/teasmart_ml/](../ml/teasmart_ml/); dependency ที่ pin อยู่ใน [requirements.txt](../ml/requirements.txt) |
| Contract และ CI | ตัวสร้าง contract จากตัวอย่าง API, pytest, Vitest, Ruff, GitHub Actions | [generate-contract.mjs](../frontend/scripts/generate-contract.mjs), [ci.yml](../.github/workflows/ci.yml) และชุดคำสั่งใน [test.ps1](../scripts/test.ps1) |

ค่าที่แสดงเป็นเวอร์ชันที่ประกาศใน manifest ไม่ใช่ผลตรวจ dependency ที่ติดตั้งใน runtime ปัจจุบัน

## เส้นทางข้อมูล

### สแกนออนไลน์

1. PWA ส่งภาพไป POST /api/v1/scan; backend ตรวจชนิดจาก magic bytes, ขนาดและจำนวนพิกเซล แล้ว decode ภาพก่อนเข้าขั้นวิเคราะห์
2. Pipeline ฝั่ง Python ทำ quality gate, แยกใบ, จำแนกคลาส, วิเคราะห์ลักษณะแผล, ประเมินความรุนแรง และเลือกคำแนะนำจาก KB ตามลำดับที่กำหนด
3. Frontend ตรวจรูปทรง response และบันทึกผลตาม scan_id ลง IndexedDB เพื่อเปิดหน้า /result/:id และแสดงใน /history

ชื่อ endpoint, fields, response และ error behavior ที่เป็น interface ให้ยึด [DESIGN.md หัวข้อ 8](DESIGN.md) เท่านั้น การเปลี่ยนต้องทำร่วมกันทั้งสองฝั่งและอัปเดต spec ก่อน

### สแกนออฟไลน์และซิงก์

1. service worker เก็บ shell และไฟล์ที่กำหนดใน precache; เมื่อมี model/config ที่ใช้ได้ Web Worker รัน quality gate และ ONNX classifier ในเบราว์เซอร์
2. ผลในโหมดออฟไลน์เป็น classifier_only; ภาพกับผลประเมินถูกเก็บใน IndexedDB queue และประวัติยังผูกกับอุปกรณ์/เบราว์เซอร์นี้
3. เมื่อกลับมาออนไลน์ client ส่ง queue ไป POST /api/v1/sync/batch; backend วิเคราะห์ภาพใหม่เต็ม pipeline และ client จัดเก็บผลตาม scan_id

เส้นทางออฟไลน์จึงไม่ใช่ผลวิเคราะห์ครบทุกขั้น การ์ดผลต้องคงการระบุ analysis_mode ตามสัญญา

### เตรียมโมเดล

ML package แยกงานนำเข้าและ deduplicate ภาพ สร้าง manifest ฝึก/ประเมิน classifier แล้ว export ONNX และตรวจ parity สำหรับ preprocessing ที่ต้องตรงกับฝั่ง browser และ server สถาปัตยกรรมที่ระบุคือ MobileNetV3-Large ขนาด 224×224; คลาสที่เรียนรู้และการตัดสิน physical_burn แบบ rule-based อ้างอิง [DESIGN.md หัวข้อ 5 และ 7](DESIGN.md) และ implementation ใน [train.py](../ml/teasmart_ml/train.py) กับ [export_onnx.py](../ml/teasmart_ml/export_onnx.py) หลักฐานตัวเลขที่วัดแล้วให้อ้าง [EVIDENCE.md](EVIDENCE.md) โดยไม่อนุมานจาก architecture นี้

## ขอบเขตความเชื่อถือและข้อมูล

- ภาพที่อัปโหลดเป็น input ภายนอก; backend ตรวจ format, byte/pixel limits และ decode ผ่านประตูรับภาพก่อน pipeline รายละเอียดอยู่ใน [images.py](../backend/app/core/images.py) และ [DESIGN.md หัวข้อ 10](DESIGN.md)
- ผล ประวัติ KB/config ที่ cache และภาพในคิวซิงก์อยู่ใน IndexedDB ของเบราว์เซอร์ ไม่ใช่ฐานข้อมูลกลาง; การล้างข้อมูล browser หรือเปลี่ยนอุปกรณ์จึงไม่ใช่การย้ายประวัติ
- KB ที่ backend โหลดมาจาก [diseases.json](../backend/app/kb/diseases.json) และ endpoint อ่านเพื่อส่งให้ client cache; เนื้อหา KB เป็นข้อมูลที่มีผลต่อการตัดสินใจและอยู่นอกขอบเขตการแก้ของเอกสารนี้
- scan_id ใช้ผูกการ retry และ sync; server idempotency cache ถูกกำหนดเป็น in-memory ขนาดจำกัดในระยะนี้ จึงไม่ใช่ durable storage
- ภาพที่ส่งเข้า backend ออกจากอุปกรณ์ผู้ใช้; การเปิด backend สู่สาธารณะต้องมีการตัดสินใจ privacy และการตั้งค่า deployment/CORS ตาม readiness checklist

## การ build, deploy และตรวจสอบ

Frontend สร้างเป็น static assets ด้วย Vite; [DEPLOY-TH.md](DEPLOY-TH.md) บันทึกขั้นตอน snapshot API, build แล้วอัปโหลด frontend/dist ไป Cloudflare Pages หรือ Netlify ด้วยมือ ส่วน workflow [ci.yml](../.github/workflows/ci.yml) ตรวจ lint/test ของ backend และ ML รวมถึง typecheck/test/build ของ frontend เมื่อมี frontend ใน ref นั้น CI ไม่ได้ deploy backend หรือเว็บ

เอกสาร readiness ระบุว่า public deployment ที่ตรวจเป็น frontend-only และการสแกนบน deployment นั้นเป็น classifier_only; โค้ดใน repository แสดง API server ได้ แต่ไม่ได้ยืนยัน URL หรือสถานะบริการที่ออนไลน์อยู่ ก่อนสาธิตหรือเปิดใช้งานต้องตรวจ deployment จริงและทดสอบบนอุปกรณ์เป้าหมาย

## ช่องว่างก่อนผู้ใช้จริงและขนาดใหญ่

รายการต่อไปนี้เป็นข้อจำกัดที่ระบุไว้ใน [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md) ไม่ใช่ข้อสรุปจากการรันระบบ production:

- ยังไม่มี backend ที่ deploy ให้ public frontend เรียก; เมื่อใช้งาน frontend-only จะไม่มีผลวิเคราะห์เต็มขั้นบน server
- ยังไม่มี rate limit, load test, worker queue/autoscaling, monitoring และ centralized alerting; จึงไม่มีหลักฐานรองรับจำนวนผู้ใช้พร้อมกันหรือ SLA
- ไม่มีฐานข้อมูลกลาง/ประวัติข้ามอุปกรณ์ และ idempotency cache ฝั่ง server อยู่ในหน่วยความจำ จึงไม่รองรับ durability หลัง process restart
- เอกสาร deploy ระบุว่าขนาดดาวน์โหลดก่อน offline มีนัยสำคัญ และ config/KB precache กับการใช้งานจริงหลังติดตั้งยังต้องตรวจบนมือถือ/URL ที่ใช้จริง
- การส่งภาพขึ้น backend เปลี่ยนขอบเขตข้อมูลจากอุปกรณ์ไปยังบริการ ต้องกำหนด privacy, retention, access และการปฏิบัติการก่อนเปิดให้ผู้ใช้จริง

ตัวเลข throughput, latency production, จำนวนผู้ใช้ที่รองรับ และ uptime ยังไม่มีหลักฐานในเอกสารที่อ้างข้างต้น จึงไม่ระบุค่าแทนการวัด
