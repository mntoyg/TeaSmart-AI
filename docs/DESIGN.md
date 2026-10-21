# TeaSmart AI — การออกแบบและสัญญา

**เอกสารอ้างอิงที่มีผลผูกพัน** หากไฟล์นี้ขัดกับไฟล์อื่น ให้ยึดไฟล์นี้ สัญญา API ในหัวข้อ 8 เป็น interface ร่วมระหว่าง backend กับ PWA ห้ามฝ่ายใดเปลี่ยนฝ่ายเดียว หากต้องแก้ ให้บันทึกในไฟล์นี้ก่อน ระบุใน `docs/STATE.md` และแจ้งผู้ใช้

เอกสารหลักสามไฟล์ใน `docs/`:

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `docs/STATE.md` | สถานะปัจจุบันของงาน **อ่านก่อน** |
| `docs/DESIGN.md` | ไฟล์นี้: ขอบเขต pipeline สัญญา และการตัดสินใจ |
| `docs/EVIDENCE.md` | ผลที่วัดได้พร้อมวิธีที่ใช้สร้างผลนั้น |

- **วันที่:** 2026-10-13
- **กำหนดส่ง:** 2026-10-22 (ส่งงานแฮกกาธอน) — เหลือเวลาทำงาน 9 วัน
- **สถานะ:** อนุมัติการออกแบบแล้ว รอตรวจทานข้อกำหนดที่เขียนไว้

## 1. จุดประสงค์

TeaSmart AI เป็นผู้ช่วยเกษตรอัจฉริยะสำหรับไร่ชาอู่หลงขนาดใหญ่ (พื้นที่อ้างอิง: สิงห์ปาร์ค เชียงราย) คนงานถ่ายรูปใบชาด้วยโทรศัพท์หรืออัปโหลดภาพจากโดรน แล้วระบบส่งผลดังนี้:

1. คลาสของโรคและระดับความรุนแรง
2. คำตัดสินอย่างชัดเจนว่าความเสียหายเป็น **โรคทางชีวภาพ** หรือ **แผลไหม้ทางกายภาพ** (แดดเผาหรือสารเคมีไหม้)
3. คำแนะนำการรักษาภาษาไทยที่นำไปทำตามได้ จากฐานความรู้ผู้เชี่ยวชาญที่คัดมา

**เกณฑ์ความสำเร็จของการสาธิต:** กรรมการหยิบโทรศัพท์ขึ้นมาถ่ายใบชา แล้วได้ผลภาษาไทยที่ถูกต้องและอ่านเข้าใจภายในไม่กี่วินาที — *แม้ปิดเครือข่ายอยู่*

## 2. ขอบเขต

### อยู่ในขอบเขต (ระยะที่ 1)

- ด่านตรวจคุณภาพภาพ (ความเบลอ/การรับแสง) พร้อมคำแนะนำภาษาไทยที่ทำตามได้
- แยกใบชาออกจากพื้นหลังและระบุตำแหน่งรอยโรค
- ตัวจำแนกโรค 5 คลาส (MobileNetV3-Large, transfer learning)
- ตัวแยกแผลไหม้กับโรคโดยใช้กฎ
- ประเมินความรุนแรงจากสัดส่วนพื้นที่รอยโรคต่อพื้นที่ใบ
- ระบบผู้เชี่ยวชาญแบบกฎเกณฑ์ที่ให้คำแนะนำภาษาไทย
- เว็บแอป PWA (ถ่ายภาพด้วยกล้อง รัน ONNX บนอุปกรณ์ และคิวออฟไลน์)
- ~~แอป Android `.apk` ผ่าน Capacitor~~ — **ตัดออกเมื่อ 2026-10-19** PWA ที่ติดตั้งจาก Chrome สาธิตสิ่งเดียวกันบนโทรศัพท์เครื่องเดียวกัน เวลาที่ได้คืนมานำไปทำตัววิเคราะห์แผลไหม้กับโรค ซึ่งเป็นคุณสมบัติหลักของผลิตภัณฑ์ ไม่มีส่วนใดใน codebase พึ่งพา Capacitor

### อยู่นอกขอบเขต (ระยะที่ 2 เป็นต้นไป)

- พยากรณ์ผลผลิต (อยู่ในวิสัยทัศน์โครงการ แต่เลื่อนออกไปโดยตั้งใจ)
- บัญชีหลายผู้ใช้ การจัดการไร่/แปลง และประวัติฝั่งเซิร์ฟเวอร์
- วางแผนเส้นทางบินโดรนหรือประกอบภาพ orthomosaic
- สร้างแบบจำลองความผิดปกติของสภาพอากาศ

## 3. ข้อจำกัด

| ข้อจำกัด | ผลต่อการออกแบบ |
|---|---|
| RTX 3050 Laptop, VRAM 4 GB | ใช้ MobileNetV3-Large ที่ 224 px, batch 32 และ mixed precision ห้ามใช้ ViT หรือ backbone ความละเอียดสูง |
| อินเทอร์เน็ตบนภูเขาไม่เสถียร | ONNX บนอุปกรณ์เป็นเส้นทางหลัก เซิร์ฟเวอร์เป็นส่วนเพิ่ม ไม่ใช่ dependency |
| เหลือ 9 วันและมีเพดานการใช้ AI ต่อวัน | ทำงานแนวตั้งวันละหนึ่งสไลซ์ โดยแต่ละสไลซ์ทดสอบและ commit แยกได้ |
| ไม่มีภาพใบไหม้ที่ติดป้ายกำกับ | ตรวจใบไหม้ด้วย **computer vision แบบกฎเกณฑ์** ห้ามฝึกเป็นคลาส |
| คุณภาพภาพจากโทรศัพท์ไม่คงที่ | ตรวจคุณภาพก่อน inference และปฏิเสธภาพที่ใช้ไม่ได้แทนการเดา |

## 4. โครงสร้าง repository

```
TeaSmart AI/
├─ ml/                      แพ็กเกจ Python สำหรับ train (teasmart_ml)
│  ├─ teasmart_ml/
│  │  ├─ datasets/sources.py     รายการแหล่งข้อมูลและตัวดาวน์โหลด
│  │  ├─ datasets/ingest.py      ปรับชื่อคลาสทุกแหล่งให้เป็น canonical classes
│  │  ├─ datasets/dedup.py       ลบข้อมูลซ้ำข้ามแหล่งด้วย perceptual hash
│  │  ├─ datasets/manifest.py    manifest.csv (path, class, source, split, phash)
│  │  ├─ transforms.py           augmentation สำหรับ train/eval
│  │  ├─ train.py                วงรอบ transfer learning
│  │  ├─ evaluate.py             confusion matrix และ P/R/F1 รายคลาส
│  │  └─ export_onnx.py          ส่งออก ONNX สำหรับเบราว์เซอร์พร้อมวัด parity
│  └─ tests/
├─ backend/                 บริการ FastAPI
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/v1/scan.py, api/v1/kb.py, api/v1/sync.py
│  │  ├─ core/config.py, core/images.py (ถอดรหัสภาพอย่างปลอดภัย)
│  │  ├─ services/quality.py     ขั้นที่ 1
│  │  ├─ services/segment.py     ขั้นที่ 2
│  │  ├─ services/classify.py    ขั้นที่ 3 (onnxruntime)
│  │  ├─ services/lesion.py      ขั้นที่ 4 แยกแผลไหม้กับโรค
│  │  ├─ services/severity.py    ขั้นที่ 5
│  │  ├─ services/expert.py      ขั้นที่ 6
│  │  └─ kb/diseases.json        ฐานความรู้ (6 records)
│  └─ tests/
├─ frontend/                React + Vite + TypeScript + Tailwind (PWA)
│  ├─ src/features/scan/, result/, history/, kb/
│  ├─ src/lib/onnx.ts            inference บนอุปกรณ์ด้วย onnxruntime-web
│  ├─ src/lib/queue.ts           คิวออฟไลน์และ sync ผ่าน IndexedDB
│  └─ public/models/             teasmart-v1.onnx (fp32, 16.8 MB)
├─ data/                    ถูก gitignore
│  ├─ raw/<source-id>/           untouched downloads
│  ├─ interim/<source-id>/       extracted
│  └─ processed/{train,val,test}/<class>/
└─ docs/                   เอกสารสามไฟล์ ไม่มีโฟลเดอร์ย่อย
   ├─ STATE.md                   สถานะงาน; อ่านก่อน
   ├─ DESIGN.md                  เอกสารนี้
   └─ EVIDENCE.md                ผลที่วัดได้
```

## 5. รายการคลาส canonical

มีคลาสที่ **นำไป train** ห้าคลาส ส่วน `physical_burn` เป็นผลจากขั้นที่ 4 ไม่ใช่คลาสของโมเดล

| id | คลาส canonical | ระเบียนใน KB |
|---|---|---|
| 0 | `grey_blight` | Tea Grey Blight (ได้รับมา) |
| 1 | `brown_blight` | Tea Brown Blight (ได้รับมา) |
| 2 | `algal_spot` | Algal Leaf Spot (ได้รับมา) |
| 3 | `healthy` | Healthy (ได้รับมา) |
| 4 | `other_disease` | **ใหม่** — ความผิดปกตินอกเหนือจากโรคหลักสามชนิด |
| — | `physical_burn` | **ใหม่** — สร้างจาก rule engine เท่านั้น |

### การจับคู่ป้ายชื่อจากแหล่งข้อมูล

| ป้ายชื่อจากแหล่ง | canonical |
|---|---|
| `gray_blight`, `gray_light`, `Gray Blight` | `grey_blight` |
| `brown_blight`, `Brown Blight` | `brown_blight` |
| `algal_spot`, `algal_leaf`, `Algal Leaf Spot` | `algal_spot` |
| `healthy`, `Healthy` | `healthy` |
| `anthracnose`, `bird_eye_spot`, `red_spot`, `red_leaf_spot`, `Red Leaf Spot`, `helopeltis`, `Helopeltis`, `white_spot` | `other_disease` |

เหตุผลที่มี `other_disease`: ทุกชุดข้อมูลจากแหล่งภายนอกมีคลาสโรคที่ไม่มีในฐานความรู้ หากตัดคลาสเหล่านี้ทิ้ง โมเดลอาจตอบ “Brown Blight” ด้วยความมั่นใจสูงเมื่อเห็นใบ Red Leaf Spot จริงในไร่ การรวมคลาสเหล่านี้ไว้ด้วยกันทำให้ระบบบอกได้ว่า “พบความผิดปกติ แต่ไม่ใช่โรคหลักสามชนิด ควรให้นักวิชาการเกษตรตรวจ” ซึ่งซื่อตรงและปลอดภัยกว่าอย่างมีนัยสำคัญ

## 6. แหล่งข้อมูล

ตรวจสอบเมื่อ 2026-10-13 ระยะที่ 1 ใช้เฉพาะแหล่งที่ไม่ต้องยืนยันตัวตน

| id | แหล่งข้อมูล | สถานะ | ขนาด | บทบาท |
|---|---|---|---|---|
| `agml` | HF `Project-AgML/tea_leaf_disease_classification` | parquet สาธารณะ | 32 MB / 5,867 ภาพ / 6 คลาส | ชุดหลักสำหรับ train classifier |
| `yunusserhat` | HF `yunusserhat/tea_sickness_dataset` | parquet สาธารณะ | 780 MB / 885 ภาพ / 8 คลาส | ภาพความละเอียดสูง; ปรับคุณลักษณะของรอยโรค |
| `mendeley_mz598` | Mendeley `mz598gxfw9` | zip สาธารณะ (Roboflow YOLO) | 108 MB / 6 คลาส + bounding box | ระบุตำแหน่งรอยโรคและตรวจสอบความรุนแรง |
| `mendeley_d2xy` | Mendeley `d2xybhfw59` | zip สาธารณะ, 3.07 GB | เลื่อนออกไป | เพิ่มปริมาณข้อมูลตามต้องการ |
| `mendeley_94fz` | Mendeley `94fzcdz8gz` | rar สาธารณะ, 964 MB | เลื่อนออกไป | เพิ่มปริมาณข้อมูลตามต้องการ |
| `mendeley_sjmy` | Mendeley `sjmy6k24d6` | **HTTP 451, ใช้ไม่ได้** | — | ตัดออก |
| `kaggle_*` 2 แหล่ง, `hf_ttkqwe123` | Kaggle / HF ที่จำกัดสิทธิ์ | ต้องใช้ credential | เลื่อนออกไป | `sources.py` เก็บรายการไว้ เพื่อเปิดใช้ภายหลังเมื่อนำ token มาใส่ |

นำมาใช้ได้ทันที: **ภาพที่ติดป้ายกำกับ 11,853 ภาพ พร้อม bounding-box annotations** เมื่อลบข้อมูลซ้ำแล้วเหลือ **8,316 ภาพ** นับเมื่อ 2026-10-13; ก่อนเปิดดูแหล่งข้อมูลคาดไว้ 6,752 ภาพ ซึ่งนับ `mendeley_mz598` เป็นเพียง annotation และพลาดภาพ 5,180 ภาพที่แหล่งนี้มีอยู่ด้วย

### การควบคุมข้อมูลรั่วไหลระหว่างชุด

นิยามภาพซ้ำอิงพิกเซล: ภาพสองใบเป็นภาพถ่ายเดียวกันเมื่อค่าเฉลี่ยความต่างสัมบูรณ์ของภาพย่อขาวดำขนาด 32x32 ไม่เกิน 8.0 จาก 255 เปรียบเทียบทุกคู่ โดยลดจำนวนคู่ที่ต้องคำนวณด้วยขอบเขตล่างแบบ exact (ค่าเฉลี่ยความต่างสัมบูรณ์ของค่าเฉลี่ยบล็อก 4x4 ไม่มีทางมากกว่าค่าของพิกเซลที่นำมาเฉลี่ย) จึงไม่มีภาพใดถูกตัดสินจากค่าประมาณ ภาพซ้ำที่ยืนยันแล้วจะยุบเหลือภาพที่ความละเอียดสูงสุด หากกลุ่มภาพซ้ำมีมากกว่าหนึ่งคลาส ให้ตัดทั้งกลุ่มทิ้งแทนการเดาคลาส จากนั้นแบ่งชุดแบบ stratified 70/15/15 **หลังลบข้อมูลซ้ำ** manifest บันทึกแหล่งที่มาและ perceptual hash ของแต่ละภาพเพื่อให้ตรวจสอบย้อนหลังได้ และ path อ้างอิงจาก interim root

**ห้ามใช้ perceptual hash ตัดสินคู่ภาพ** นี่คือบทเรียนที่มีต้นทุนสูงที่สุดของ D2 การใช้ pHash ที่ Hamming distance ไม่เกิน 5 เป็นเกณฑ์ทำให้ 24% ของคู่ที่ไม่ใช่ภาพเดียวกันถูกรวมเข้าด้วยกัน การใช้มันสร้างรายการ candidate แล้วค่อยยืนยันด้วยพิกเซลดูเหมือนถูกต้อง แต่กลับพลาดในจุดสำคัญ: มันจำกัด recall อย่างเงียบ ๆ และ manifest ที่ได้มีคู่ภาพซ้ำข้ามชุด 127 คู่ ทำให้ข้อมูลประเมิน 3.24% มีภาพคู่แฝดอยู่ในชุด train ด้วย pHash ใช้ค่ามัธยฐานของสัมประสิทธิ์ DCT เป็น threshold ภาพ contrast ต่ำจึงมีสัมประสิทธิ์หลายค่าค้างอยู่ตรงนั้น และสำเนาที่แทบเหมือนกันอาจพลิกบิตได้ ภาพสองใบที่ค่าพิกเซลต่างกัน 0.01 จาก 255 กลับมี hash ต่างกัน 26 บิต

**ตรวจสอบแล้ว ไม่ใช่แค่กล่าวอ้าง** หลังสร้างแต่ละครั้ง จะเปรียบเทียบทุกคู่ของแถวใน manifest ด้วยค่าพิกเซล และกำหนดเงื่อนไขตรวจโดยไม่อ้างวิธีสร้าง candidate: รุ่นก่อนหน้าตรวจเฉพาะคู่ที่ hash เสนอมา จึงรายงานศูนย์ทั้งที่มีคู่ข้ามชุด 127 คู่ corpus ปัจจุบันรายงานคู่ภาพซ้ำข้ามชุด 0 คู่ จากทั้งหมด 8,316 แถว ดูตัวเลขและผลผิดสองครั้งก่อนหน้านั้นใน `docs/EVIDENCE.md` หัวข้อ 1

## 7. Pipeline การวิเคราะห์

```
image -> [1] quality gate -> [2] leaf segment -> [3] classifier
      -> [4] lesion analyser -> [5] severity -> [6] expert system -> result
```

ทุกขั้นเป็น pure function ที่รับ input ซึ่งระบุชัด ทดสอบแยกกันได้ และไม่ต้องรู้รายละเอียดภายในของขั้นอื่น

### ขั้นที่ 1 — ด่านตรวจคุณภาพ (`services/quality.py`)

- **ความเบลอ:** วัด variance ของ Laplacian และปฏิเสธภาพที่ต่ำกว่า threshold ซึ่งปรับเทียบไว้
- **การรับแสง:** ดูค่า luminance เฉลี่ยและสัดส่วนพิกเซลที่ถูก clip ที่ปลายทั้งสองด้านของ histogram แล้วปฏิเสธภาพที่สว่างหรือมืดเกินไป
- ส่งคืน `{passed, blur_score, exposure_score, reason_th}` หากไม่ผ่าน API ตอบ `422` พร้อมคำแนะนำภาษาไทย (เช่น “ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น”) แทนการเดาผลวินิจฉัย

ปรับเทียบ threshold จาก training corpus รวมกับสำเนาที่สร้างให้เบลอหรือปรับ exposure แล้ว และเก็บไว้ใน config ห้าม hard-code ณ จุดเรียกใช้

### ขั้นที่ 2 — แยกใบชาออกจากพื้นหลัง (`services/segment.py`)

ใช้ excess-green index ร่วมกับ HSV green mask ทำ morphological cleanup แล้วเลือก contour ที่เชื่อมต่อกันและมีขนาดใหญ่ที่สุด ส่งออก leaf mask, crop ที่กระชับ และพื้นที่พิกเซลของใบ หากไม่มีขั้นนี้ severity ratio จะไม่มีความหมายและพื้นหลังจะทำให้เกิด false positive

### ขั้นที่ 3 — ตัวจำแนก (`services/classify.py`)

ใช้ MobileNetV3-Large ที่ pretrain ด้วย ImageNet และเปลี่ยน head ให้มี output 5 คลาส ใช้ภาพ crop ที่แยกใบแล้ว ขนาด input 224x224 วิธี train: AdamW, cosine schedule, label smoothing 0.05, sampling ให้สมดุลตามคลาส, mixed precision และ early stopping โดยดู validation macro-F1 การเพิ่มข้อมูลจำลองจุดพลาดจริง ได้แก่ crop แล้วปรับขนาดแบบสุ่ม หมุน พลิกแนวนอน/แนวตั้ง ปรับสี จำลอง motion blur และปรับ brightness/contrast เพื่อแทนแสงในไร่

ส่งออก `{class_id, class_name, confidence, top_k}` หาก confidence ต่ำกว่าเกณฑ์ใน config ให้ลดผลเป็น `other_disease` พร้อมตั้ง flag ว่าความเชื่อมั่นต่ำ

### ขั้นที่ 4 — ตัวแยกแผลไหม้กับโรค (`services/lesion.py`)

นี่คือคุณสมบัติที่ทำให้โครงการแตกต่าง และใช้ **ข้อมูลใบไหม้ที่ติดป้ายกำกับเป็นศูนย์ภาพ** จาก lesion mask (threshold ภายใน leaf mask บนส่วนสีที่ไม่เขียว) จะคำนวณคุณลักษณะที่ปรับสเกลแล้วห้าค่า:

| คุณลักษณะ | วิธีคำนวณ | ใบไหม้ | โรค |
|---|---|---|---|
| `edge_sharpness` | ค่าเฉลี่ย Sobel gradient magnitude ในแถบตามขอบรอยโรค | ต่ำ (ขอบกระจาย) | สูง (ขอบเข้มคมชัด) |
| `ring_score` | จำนวนครั้งที่สัญญาณเปลี่ยนเครื่องหมาย / ความถี่เด่นของ radial intensity profile จากจุดศูนย์กลางรอยโรค | ต่ำ (ไม่มีวง) | สูง (วงซ้อนกัน) |
| `acervuli_score` | bottom-hat morphology กับการหา blob กรองขนาด 2-8 px แล้วหาความหนาแน่นต่อพื้นที่รอยโรค | ต่ำ (ไม่มี) | สูง (จุดสร้างสปอร์สีดำ) |
| `edge_affinity` | สัดส่วนพิกเซลของรอยโรคที่อยู่ห่างจากขอบใบไม่เกิน k px | สูง (ปลายใบ/ขอบใบที่หันรับแดด) | ต่ำ (กระจายทั่วแผ่นใบ) |
| `colour_zonation` | จำนวนกลุ่ม hue/value ที่ต่างกันภายในรอยโรค (k-means, inertia drop) และค่า saturation เฉลี่ย | ต่ำ (สีฟางสม่ำเสมอและจาง) | สูง (หลายเฉดจากน้ำตาลถึงเทา) |

ปรับแต่ละคุณลักษณะตาม percentile ที่วัดจาก training corpus แล้วรวมเป็น weighted logistic score ชื่อ `burn_likelihood` อยู่ระหว่าง 0 ถึง 1 หากสูงกว่า threshold ใน config (ค่าเริ่มต้น 0.6) ให้เปลี่ยนผลเป็น `physical_burn` ระบุว่าระงับ confidence ของโรค และให้ระบบผู้เชี่ยวชาญส่งคำแนะนำสำหรับใบไหม้ (ปรับร่มเงา ตรวจความเข้มข้นของสารพ่น ให้น้ำ — ระบุชัดเจนว่า **ห้ามใช้สารฆ่าเชื้อรา**)

**ประเมินอย่างตรงไปตรงมา** เมื่อไม่มีภาพใบไหม้จริง ห้ามอ้างว่า “ตรวจใบไหม้ได้แม่น X%” ให้วัดและรายงานสองรายการนี้:

- **Specificity:** อัตราที่ภาพทดสอบซึ่งยืนยันว่าเป็นโรคถูกระบุผิดว่าเป็นใบไหม้ เป้าหมายต่ำกว่า 5% วัดได้จากข้อมูลจริงและเป็นตัวชี้วัดสำคัญ เพราะคุณสมบัตินี้มีไว้ลด false positive
- **Sensitivity บนใบไหม้สังเคราะห์:** สร้างรอยคล้ายใบไหม้บนใบสุขภาพดี (ปื้นไล่สีแทน ขอบนุ่ม อยู่ริมใบ ไม่มีจุดเล็กหรือวง) รายงานเพื่อใช้อ้างอิงเท่านั้นและต้องระบุชัดว่าเป็นข้อมูลสังเคราะห์

น้ำหนักและ threshold อยู่ใน config เพื่อปรับค่าได้โดยไม่ต้องแก้โค้ด

### ขั้นที่ 5 — ความรุนแรง (`services/severity.py`)

คำนวณ `affected_pct = lesion_area / leaf_area` แล้วจัดเป็น mild (ต่ำกว่า 5%), moderate (5-20%) หรือ severe (มากกว่า 20%) ใช้ bounding box จาก `mendeley_mz598` ตรวจคร่าว ๆ ว่า lesion mask ซ้อนกับรอยโรคที่ทำ annotation ไว้หรือไม่ (รายงาน IoU ใน `docs/EVIDENCE.md`)

### ขั้นที่ 6 — ระบบผู้เชี่ยวชาญ (`services/expert.py`)

ค้น `kb/diseases.json` ด้วยคลาสที่สรุปแล้ว และส่งคืนช่องคำแนะนำภาษาไทยตามต้นฉบับ ระดับความรุนแรงเป็นตัวกำหนดจุดเน้น (ระดับ severe เน้นการรักษาด้วยสารเคมี ส่วน mild เริ่มจากวิธีดูแลแปลง) ฐานความรู้เป็นข้อมูล ไม่ใช่โค้ด และส่งให้ frontend เพื่อ cache ใช้ออฟไลน์ได้

**schema ของฐานความรู้** (ต่อหนึ่ง record): `class_id`, `canonical`, `class_name`, `disease_name_th`, `pathogen`, `symptoms`, `immediate_action`, `cultural_control`, `chemical_treatment`, `preventive_measures` ระเบียน 0-3 เก็บข้อความคำแนะนำสี่รายการที่ได้รับมาตามต้นฉบับ ส่วนระเบียน 4 (`other_disease`) และ 5 (`physical_burn`) เพิ่มโดยการออกแบบนี้และเขียนด้วยน้ำเสียงเดียวกัน

`canonical` คือชื่อ snake_case จากหัวข้อ 5 และเป็น key ที่ใช้ค้น เพราะเป็นชื่อที่ขั้น 3 ส่งออกและหัวข้อ 8 ระบุใน response ส่วน `class_name` ยังคงเป็นชื่อแสดงภาษาอังกฤษ

## 8. สัญญา API

หัวข้อนี้เป็น interface ระหว่าง backend กับ PWA ห้ามฝ่ายใดเปลี่ยนตามลำพัง หากต้องแก้ ให้เขียนลงที่นี่ก่อน ระบุใน `docs/STATE.md` และแจ้งผู้ใช้

| method | path | จุดประสงค์ |
|---|---|---|
| `GET` | `/health` | ตรวจ liveness และรุ่นโมเดล |
| `POST` | `/api/v1/scan` | ภาพหนึ่งใบและผลวิเคราะห์เต็มรูปแบบ |
| `GET` | `/api/v1/kb` | ฐานความรู้สำหรับ cache ใช้ออฟไลน์ |
| `GET` | `/api/v1/config` | ค่าที่ทั้งสองฝั่งต้องใช้สำหรับ cache ใช้ออฟไลน์ |
| `POST` | `/api/v1/sync/batch` | ส่ง scan ที่เข้าคิวระหว่างออฟไลน์กลับไปประมวลผล |

### 8.1 `POST /api/v1/scan`

`Content-Type: multipart/form-data` with these parts:

| part | จำเป็น | type | หมายเหตุ |
|---|---|---|---|
| `image` | ใช่ | file | ชื่อ field คือ **`image`** ไม่ใช้ content type ที่ประกาศหรือชื่อไฟล์ตัดสิน format แต่ตรวจจาก magic bytes รองรับเฉพาะ JPEG, PNG และ WebP |
| `scan_id` | ไม่ | text | UUIDv4 ที่ client สร้าง แนะนำให้ส่งมา เพราะเป็น idempotency key (8.3) และใช้ผูก scan ที่เข้าคิวกับผลลัพธ์ หากไม่ส่ง server จะสร้างให้ |
| `captured_at` | ไม่ | text | ISO 8601 ที่มี offset จากนาฬิกาอุปกรณ์ บันทึกไว้แต่ไม่เชื่อถือเป็นข้อมูลยืนยันเวลา |

ขีดจำกัดจาก `Settings`: `max_upload_bytes` 8388608 (8 MiB) และ `max_image_pixels` 40000000 หากเกินข้อใดข้อหนึ่ง จะปฏิเสธ request ก่อนถอดรหัสภาพ

Responses:

| status | เงื่อนไข | body |
|---|---|---|
| `200` | analysed | the result object below |
| `422` | the quality gate rejected the frame | `{"detail", "detail_th", "quality"}` |
| `415` | not a JPEG, PNG or WebP | `{"detail", "detail_th"}` |
| `413` | over the byte or pixel cap | `{"detail", "detail_th"}` |
| `400` | truncated or undecodable | `{"detail", "detail_th"}` |

แสดงให้คนงานเห็นเฉพาะ `detail_th` ส่วน `detail` เป็นภาษาอังกฤษสำหรับ log

`422` ไม่ใช่หน้า error แต่มีคำแนะนำภาษาไทยบอกคนงานว่าควรแก้อะไร และ UI ให้ถ่ายใหม่ได้ทันที

```json
{
  "scan_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "captured_at": "2026-10-13T09:12:04+07:00",
  "quality": {
    "passed": true,
    "blur_score": 704.5,
    "exposure_mean": 93.4,
    "clipped_low_pct": 0.0,
    "clipped_high_pct": 0.0
  },
  "prediction": {
    "class_id": 0,
    "class_name": "grey_blight",
    "confidence": 0.93,
    "top_k": [
      { "class_name": "grey_blight", "confidence": 0.93 },
      { "class_name": "brown_blight", "confidence": 0.04 }
    ],
    "low_confidence": false
  },
  "burn_analysis": {
    "verdict": "disease",
    "burn_likelihood": 0.12,
    "features": {
      "edge_sharpness": 0.81,
      "ring_score": 0.74,
      "acervuli_score": 0.66,
      "edge_affinity": 0.19,
      "colour_zonation": 0.71
    }
  },
  "severity": { "affected_pct": 0.11, "level": "moderate" },
  "advice": {
    "canonical": "grey_blight",
    "disease_name_th": "โรคใบไหม้เทา",
    "immediate_action": "...",
    "cultural_control": "...",
    "chemical_treatment": "...",
    "preventive_measures": "..."
  },
  "analysis_mode": "full",
  "model_version": "teasmart-v1",
  "processing_ms": 412
}
```

`verdict` เป็น `"disease"` หรือ `"physical_burn"`; `level` เป็น `"mild"`, `"moderate"` หรือ `"severe"`; `analysis_mode` เป็น `"full"` หรือ `"classifier_only"` การ์ดผลลัพธ์ต้องระบุโหมดที่ใช้เสมอ เพื่อไม่ให้คนงานเข้าใจว่าผลจากอุปกรณ์เป็นการวิเคราะห์ครบทุกขั้น

เมื่อ `verdict` เป็น `"physical_burn"` ค่า `advice` มาจากระเบียน 5 ของฐานความรู้และห้ามแนะนำสารฆ่าเชื้อรา UI ต้องแสดงความแตกต่างนี้อย่างเด่นชัด เพราะเป็นคุณสมบัติหลักของผลิตภัณฑ์

### 8.2 `POST /api/v1/sync/batch`

ส่ง scan ที่เบราว์เซอร์เข้าคิวไว้ระหว่างออฟไลน์ โดยแต่ละรายการมีผล classifier-only จากเครื่องอยู่แล้ว server จะวิเคราะห์ใหม่แบบเต็มขั้น

`Content-Type: multipart/form-data`:

| part | จำเป็น | หมายเหตุ |
|---|---|---|
| `items` | ใช่ | JSON array มีหนึ่ง object ต่อ scan ที่เข้าคิว: `{"scan_id", "captured_at", "local_prediction": {"class_name", "confidence"}}` `local_prediction` ไม่บังคับ ใช้บันทึกเพื่อเปรียบเทียบเท่านั้น ห้ามใช้เป็นคำตอบ |
| `images` | ใช่ | มี file part ต่อรายการและส่งซ้ำได้ **ชื่อไฟล์ของแต่ละ part ต้องเป็น `scan_id` ของรายการนั้น** |

จับคู่รายการกับไฟล์ด้วย `scan_id` ไม่ใช่ตำแหน่ง เพราะการเลื่อนเพียงหนึ่งรายการอาจผูกผลวินิจฉัยกับภาพผิดใบและทำให้คนงานดูแลผิดแปลง หากมี `scan_id` ใน `items` แต่ไม่มีไฟล์คู่กัน หรือมีไฟล์ที่ไม่มีรายการคู่กัน ให้ตอบ `422` สำหรับทั้ง request

ขีดจำกัดจาก `Settings`: `max_batch_items` 20 และ `max_batch_bytes` 33554432 (32 MiB) หากคิวยาวกว่านี้ client จะแบ่งส่งเป็นหลาย request

ตอบ `200` พร้อมผลแยกแต่ละรายการ เพื่อให้ภาพเสียหนึ่งใบไม่ทำให้ทั้ง batch ล้มเหลว:

```json
{
  "results": [ { "scan_id": "...", "...": "the full scan result object" } ],
  "failed": [
    {
      "scan_id": "9f1c...",
      "status": 422,
      "detail": "blurry",
      "detail_th": "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"
    }
  ]
}
```

`scan_id` ที่ส่งมาต้องปรากฏใน array ใด array หนึ่งเพียงครั้งเดียวเท่านั้น `422` ใช้กับ request ทั้งชุดในกรณี `items` ผิดรูปแบบ จับคู่ไม่ตรงกัน หรือเกินขีดจำกัด

### 8.3 การป้องกันการประมวลผลซ้ำ (Idempotency)

`scan_id` เป็น idempotency key ของทั้งสอง endpoint เมื่อสัญญาณหลุดในแปลงบนภูเขา การ retry เป็นเรื่องปกติและต้องไม่สร้างผลวินิจฉัยหรือรายการประวัติซ้ำ

- client สร้าง UUIDv4 ตอนถ่ายภาพ เก็บไว้กับภาพที่เข้าคิว และส่งไปทุกครั้งรวมทั้งการ retry
- server เก็บ map ในหน่วยความจำที่จำกัดขนาด โดยจับคู่ `scan_id` ที่เพิ่งประมวลผลกับผลลัพธ์ (`Settings.idempotency_cache_size`, 512) หากส่งซ้ำ จะคืนผลเดิมพร้อมสถานะ `200` และ `"replayed": true` ใน result object
- **cache นี้ไม่อยู่ต่อหลัง restart และตั้งใจให้เป็นเช่นนั้นในระยะที่ 1:** ไม่มีฐานข้อมูล (หัวข้อ 2) client เป็นบันทึกถาวร จึงต้องลบรายการซ้ำด้วย `scan_id` ในเครื่องด้วย cache ฝั่ง server ครอบคลุมเพียงกรณีทั่วไปที่ retry หลังจากนั้นไม่กี่วินาที

### 8.4 สัญญาโมเดล ONNX

เบราว์เซอร์กับ server ต้อง preprocess เหมือนกัน มิฉะนั้นผลจะต่างกันโดยไม่มีใครรู้สาเหตุ ทั้งสองฝั่งต้องทำตามขั้นตอนนี้ตรงกัน:

1. decode to RGB `uint8`
2. ปรับขนาดเป็น **224x224 ด้วย bilinear โดยไม่รักษา aspect ratio**
3. divide by 255 into `[0, 1]`
4. normalize แยกแต่ละ channel ด้วยค่าสถิติ ImageNet: mean `(0.485, 0.456, 0.406)`, std `(0.229, 0.224, 0.225)`
5. transpose เป็น NCHW, `float32`, batch 1

| | |
|---|---|
| ไฟล์ | `frontend/public/models/teasmart-v1.onnx` — **fp32** |
| input | `input`, `float32[1, 3, 224, 224]`, NCHW |
| output | `logits`, `float32[1, 5]` — **raw logits ไม่ใช่ probabilities** |
| ลำดับคลาส | `grey_blight`, `brown_blight`, `algal_spot`, `healthy`, `other_disease` |

ผู้เรียกเป็นผู้คำนวณ Softmax หาก probability สูงสุดต่ำกว่า `min_confidence` ให้ตั้ง `low_confidence` และรายงานคลาสเป็น `other_disease` พร้อม flag ดังกล่าว **อ่านเกณฑ์นี้จาก `GET /api/v1/config`; ห้าม hard-code** ค่าเป็นค่าชั่วคราวจนกว่า D3 จะวัด และหากคัดลอกไว้ใน TypeScript ค่าจะคลาดทันทีที่ปรับใหม่โดยไม่มีใครสังเกต เพราะ codebase ทั้งสองมองไม่เห็นกัน

**เบราว์เซอร์ไม่แยกใบออกจากพื้นหลัง** ขั้นที่ 2 มีเฉพาะใน Python ดังนั้นการรันบนอุปกรณ์ preprocess ทั้งภาพ ขณะที่ server preprocess เฉพาะ crop ที่แยกใบแล้ว ผลจึงต่างกันในบางภาพ และเป็นเหตุผลหนึ่งที่ต้องระบุผลจากอุปกรณ์ว่า `classifier_only` แทนการนำเสนอว่าเทียบเท่ากัน มีเพียง quality gate ที่ทำซ้ำใน JavaScript เพราะมีต้นทุนต่ำ

**Parity test** ซึ่งต้องผ่านก่อนถือว่า D7 เสร็จ: ใช้ภาพ 50 ภาพชุดเดิมจาก manifest แล้ว pipeline ของเบราว์เซอร์กับ Python ต้องเลือก top-1 ตรงกันทุกภาพ และ probability ของทุกคลาสต้องต่างกันไม่เกิน 0.05

**Int8 ไม่ผ่านเกณฑ์ดังกล่าวและไม่ได้ส่งมอบ** (2026-10-19) int8 ที่ calibrate แบบคงที่เลือก top-1 ตรงกันทั้ง 50 ภาพ แต่ทำให้ probability ขยับได้ถึง **0.248** การเลือก top-1 ตรงกันอย่างเดียวไม่ใช่เกณฑ์ผ่าน เพราะผลิตภัณฑ์ใช้ threshold กับ probability การขยับขนาดนี้อาจทำให้ผลข้าม `min_confidence` ได้ทั้งสองทิศทางโดยไม่มีฝั่งใดเห็นความไม่ตรงกัน ไฟล์ที่ต้องโหลดคือ `teasmart-v1.onnx`, fp32, 16.8 MB ดูผลวัดใน `docs/EVIDENCE.md` หัวข้อ 2.5

### 8.5 `GET /api/v1/config`

รวมค่าทุกอย่างที่ PWA ต้องใช้และมีอยู่ใน backend ไว้ในเอกสารเดียวที่ cache ได้ เบราว์เซอร์ดึงมาพร้อมฐานความรู้และเก็บทั้งคู่ใน service-worker cache

endpoint นี้มีขึ้นเพราะจำเป็นต้อง implement สองส่วนซ้ำ: quality gate เพราะทำได้ต้นทุนต่ำและต้องใช้ตอนออฟไลน์ และ preprocessing ของ classifier เพราะ `onnxruntime-web` รันโมเดลในเบราว์เซอร์ หากมีสำเนาค่าคงที่ใน TypeScript ค่าเหล่านั้นจะคลาดทันทีที่มีการปรับ

```json
{
  "model_version": "teasmart-v1",
  "min_confidence": 0.6,
  "class_order": ["grey_blight", "brown_blight", "algal_spot", "healthy", "other_disease"],
  "preprocessing": {
    "size": [224, 224],
    "resize": "bilinear",
    "preserve_aspect_ratio": false,
    "scale": 255.0,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "layout": "NCHW",
    "dtype": "float32"
  },
  "onnx": {
    "file": "teasmart-v1.onnx",
    "input": "input",
    "output": "logits",
    "output_is_logits": true
  },
  "quality": {
    "blur_threshold": 15.0,
    "exposure_min_mean": 40.0,
    "exposure_max_mean": 235.0,
    "clip_max_pct": 0.1
  }
}
```

สร้าง `class_order` จากฐานความรู้ตามลำดับ `class_id` โดยตัด `physical_burn` ออกเพราะ classifier ไม่ส่งคลาสนี้ สร้างจากแหล่งเดียวแทนการเขียนซ้ำ จึงไม่ขัดกับ record ที่ใช้ค้นคำแนะนำ

`min_confidence` คือ **0.60 ซึ่งวัดแล้ว** เมื่อ 2026-10-19 และไม่ใช่ค่าชั่วคราวอีกต่อไป เกณฑ์ที่ D3 ได้รับคือเลือก threshold ต่ำสุดที่ทำ accuracy ได้ 0.90 ในรายการที่ยอมรับ เกณฑ์นี้ให้ค่า 0.20 ทั้งที่โมเดลมี accuracy 0.987 อยู่แล้ว จึงปิด safety net ของ `other_disease` เกณฑ์ที่ใช้จริงคือ **accuracy 0.99 ในรายการที่ยอมรับ** ซึ่งต้องใช้ค่า 0.55 บน validation split และ 0.63 บน test split เมื่อใช้ 0.60 ชุด held-out ได้ accuracy 0.9895 และปฏิเสธภาพ 0.72%

เกณฑ์นี้จับข้อผิดพลาดที่มั่นใจสูงไม่ได้ทั้งหมด: ภาพทดสอบหนึ่งภาพทำนายผิดที่ 0.983 ห้าม UI สื่อว่าผลที่สูงกว่าเกณฑ์นี้ถูกต้องแน่นอน

## 9. Frontend และการทำงานออฟไลน์

- **ออนไลน์:** ส่งภาพไป backend และรัน pipeline ครบหกขั้นบน server
- **ออฟไลน์:** `onnxruntime-web` รันโมเดล int8 ในเบราว์เซอร์เพื่อให้ผลคลาสและ confidence ทันที quality gate ก็รันฝั่ง client ด้วย JavaScript เพราะมีต้นทุนต่ำ ภาพและผลจากเครื่องเข้าคิวใน IndexedDB เมื่อเครือข่ายกลับมา จะส่งผ่าน `/api/v1/sync/batch` เพื่อเติมผลวิเคราะห์รอยโรคและความรุนแรงแบบเต็ม
- การ์ดผลลัพธ์ระบุชัดเจนว่าใช้โหมดใด เพื่อไม่ให้คนทำงานในไร่เข้าใจผิดว่าผลสมบูรณ์แค่ไหน
- service worker precache shell, ONNX model และฐานความรู้
- Routes: `/scan`, `/result/:id`, `/history`, `/kb`

การทำซ้ำนี้ตั้งใจและจำกัดขอบเขตไว้ เฉพาะ classifier กับ quality gate ที่มีสองชุด ส่วนตัววิเคราะห์รอยโรค การประเมินความรุนแรง และระบบผู้เชี่ยวชาญมี implementation เดียวใน Python

## 10. ความปลอดภัย (สอดคล้องกับ OWASP)

- ตรวจไฟล์อัปโหลดด้วย **magic byte** ห้ามใช้ file extension ตัดสิน
- จำกัดขนาด request อย่างเคร่งครัดและปฏิเสธก่อนประมวลผล
- ถอดรหัสด้วย Pillow ที่ตั้ง `MAX_IMAGE_PIXELS` เพื่อป้องกัน decompression bomb แล้ว **เข้ารหัสภาพใหม่** เพื่อลบ EXIF และ payload ที่ฝังอยู่ก่อนส่งภาพไปยังโค้ดส่วนอื่น
- ชื่อไฟล์ที่บันทึกใช้ UUID ที่ server สร้างเอง ไม่มีส่วนใดของ path ที่ผู้ใช้ส่งไปถึง filesystem
- ใช้ Pydantic model ที่เข้มงวดกับทุก request และ response
- จำกัด CORS ด้วย allowlist ที่ระบุชัด และจำกัดอัตราการเรียก `/api/v1/scan`
- ตั้งค่าผ่าน `.env` พร้อม commit `.env.example`; ห้ามมี secret ใน repository `data/` และ model weights ถูก gitignore
- ฐานความรู้เป็น read-only ขณะ runtime และโหลดครั้งเดียวตอนเริ่มระบบ

## 11. กลยุทธ์การทดสอบ

- **ml:** ใช้ pytest ตรวจการจับคู่ label พฤติกรรม dedup การแบ่งชุดแบบ stratified และความสมบูรณ์ของ manifest ใช้ fixture corpus ขนาดเล็กเพื่อให้ test ทำงานเร็ว
- **backend:** ใช้ pytest แยกตามขั้น ทดสอบตัววิเคราะห์รอยโรคด้วย **fixture สังเคราะห์** ที่สร้างจากโค้ด — รอยคล้ายโรค (ขอบคม วงซ้อน จุดเล็ก) และรอยคล้ายใบไหม้ (ไล่สีแทนนุ่ม ๆ บริเวณขอบใบ) ทำให้ test ตรวจซ้ำได้และทบทวนง่าย โดยไม่ต้องพึ่งภาพที่เลือกด้วยมือ ส่วน security test ครอบคลุมไฟล์ polyglot, upload ที่ใหญ่เกินไป และ decompression bomb
- **frontend:** ใช้ vitest ตรวจคิวออฟไลน์และ ONNX pre/post-processing โดยยืนยันว่า pipeline ของเบราว์เซอร์กับ Python ให้ผลใน tolerance เมื่อใช้ input เดียวกัน
- **โมเดล:** `docs/EVIDENCE.md` เก็บ confusion matrix, precision/recall/F1 รายคลาส และตัวเลข burn-specificity ห้ามกล่าวอ้าง accuracy ใน README หรือ pitch หากไม่มีรายงานที่ commit ไว้รองรับ

## 12. สมมติฐาน

1. เพิ่มระเบียนฐานความรู้สองรายการจากสี่รายการที่ได้รับ (`other_disease`, `physical_burn`); ใช้ข้อความสี่รายการเดิมตามต้นฉบับ
2. การพยากรณ์ผลผลิตอยู่ในระยะที่ 2 และไม่อยู่ใน spec นี้
3. ปิดแหล่ง Kaggle และ Hugging Face ที่จำกัดสิทธิ์ไว้จนกว่าจะมี credential; เขียน `sources.py` ให้เปิดใช้ได้ด้วยการเปลี่ยน config
4. Repository เป็น private ตามค่าเริ่มต้นของโครงการ

## 13. การตัดสินใจที่เผลอเปลี่ยนกลับได้ง่าย

แต่ละข้อใช้การวัดผลเพื่อยืนยัน การเปลี่ยนกลับอาจดูเหมือนไม่มีผล แต่จริง ๆ แล้วมีผล

**นิยามภาพซ้ำจากพิกเซล ไม่ใช่ perceptual hash** ใช้ mean absolute error ของภาพย่อขาวดำ 32x32 ไม่เกิน 8.0 เปรียบเทียบทุกคู่ และใช้ขอบเขตล่างจากค่าเฉลี่ยบล็อก 4x4 เพื่อให้คำนวณได้จริง เก็บ hash ไว้ตรวจสอบเท่านั้น การใช้ hash สร้าง candidate pairs จำกัด recall: มีคู่ข้ามชุด 127 คู่ที่ pixel MAE ต่ำกว่าเกณฑ์ แต่ Hamming distance อยู่ระหว่าง 6 ถึง 30 จึงมีภาพ 83 ภาพ (3.24% ของชุดประเมิน) ที่มีภาพคล้ายกันมากอยู่ในชุด train การตรวจเดิมพลาดเพราะตรวจเฉพาะคู่ที่ hash บอกว่าใกล้กัน ทำให้เป็นการตรวจแบบวนกลับมายืนยันวิธีของตัวเอง ดูตัวเลขใน `EVIDENCE.md`

**จัดกลุ่มภาพซ้ำโดยยึดภาพ leader ไม่ใช่ single-linkage** เพราะ transitive closure เคยต่อภาพที่เกือบเหมือนกันเข้าด้วยกันจนเป็นกลุ่มใหญ่ 866 ภาพ

**ตรวจ exposure ก่อน blur** ภาพมืดมี Laplacian variance ต่ำ หากตรวจ blur ก่อนจะรายงานว่าเบลอและบอกให้คนงานถือกล้องให้นิ่งขึ้น ทั้งที่ปัญหาจริงคือแสงไม่พอ วัดแล้ว: dark fixture ได้ 4.39 เทียบกับ blur threshold 80

**วัด clipping แยกแต่ละ channel ทั้งค่าต่ำและสูง** ภาพหนึ่งอาจมีค่า exposure เฉลี่ยอยู่ในช่วง แต่ channel หนึ่งสว่างจนล้น: fixture ที่เพิ่มความสว่าง 4 เท่ามีค่าเฉลี่ยสีเทา 201.6 ซึ่งอยู่ในช่วง แต่มี channel หนึ่งถูก clip 0.322

**ตั้งใจเพิ่ม `other_disease` เป็นคลาสที่ห้า** เพื่อให้โมเดลไม่ระบุชื่อโรคที่ไม่เคยเห็น แทนการเรียก red leaf spot ว่า grey blight ด้วยความมั่นใจสูง

**ONNX graph ใช้ fp32 ไม่ใช่ int8** int8 ให้ top-1 ตรงกันในภาพ parity ทั้ง 50 ใบ แต่ทำให้ probability ต่าง 0.248 เทียบกับขอบเขต 0.05 การตรงกันของ top-1 ไม่ใช่เกณฑ์ยอมรับ เพราะผลิตภัณฑ์ใช้ probability เป็น threshold

**ใช้ PIL เป็นข้อกำหนดของการ resize** classifier train จาก output ของ PIL เบราว์เซอร์จึงต้องทำให้ตรงกับ PIL ไม่ใช่เปลี่ยน PIL ให้ตรงกับเบราว์เซอร์ fixture อยู่ใน `frontend/src/test/fixtures/preprocess/`

**`data/interim/` ต้องมี marker `.teasmart-interim`** ก่อน pipeline จะลบสิ่งใดข้างใน marker guard มีไว้เพราะ pipeline ทำการลบ

**ภาพ 32 ใบมีป้ายกำกับจากสองแหล่งไม่ตรงกัน จึงตัดออก** แทนการตัดสินด้วยการเดา

## 14. ใครรับผิดชอบส่วนใด

มี agent สองตัวทำงานใน repository นี้พร้อมกัน แบ่งตามไดเรกทอรีเพื่อไม่ต้องรอกัน

| agent | รับผิดชอบ | ประสานกันที่ |
|---|---|---|
| Claude Code | `ml/`, `backend/` — โมเดล ขั้น pipeline และ API | สัญญาในหัวข้อ 8 |
| Codex | `frontend/` — PWA กล้อง และการ์ดผลภาษาไทย | สัญญาเดียวกัน |

- หนึ่ง branch ต่อหนึ่งสไลซ์ ห้าม agent สองตัวใช้ branch เดียวกัน
- ตรวจ `docs/STATE.md` ก่อนเริ่ม หากสไลซ์ของคุณมีคนทำแล้ว ให้เลือกงานถัดไปที่แยกทำได้
- ผู้ที่ปิดสไลซ์ต้องอัปเดต `docs/STATE.md` ใน push เดียวกัน
- สร้าง TypeScript types จากหัวข้อ 8 แทนการเขียนเองจากสรุป
- **ห้าม hard-code ค่าที่ backend มีอยู่แล้ว** `GET /api/v1/config` ส่ง confidence floor, class order, ONNX preprocessing และ quality thresholds ให้ดึงครั้งเดียว cache ใน service worker ไว้ข้างฐานความรู้ แล้วอ่านจาก cache
- ข้อความทั้งหมดที่คนงานเห็นเป็นภาษาไทย โค้ด คอมเมนต์ และ commit ใช้ภาษาอังกฤษ
