# TeaSmart AI — หลักฐานจากการวัด

ตัวเลขทุกค่ามาจากคำสั่งที่ระบุไว้ ไม่มีค่าใดเป็นการคาดเดา หากยังไม่ทราบจะแจ้งไว้ตามจริง

| หัวข้อ | เนื้อหา |
|---|---|
| 1 | corpus สำหรับ train: แหล่งข้อมูล การลบข้อมูลซ้ำ และการแบ่งชุด |
| 2 | classifier: การ train คะแนนชุด held-out, `min_confidence` และ ONNX parity |
| 3 | frontend: ชุด test การตรวจสัญญา และ PWA build |
| 4 | quality gate ที่ปรับเทียบใหม่กับภาพจริง |
| 5 | แยกใบไหม้กับโรค: วัด specificity ได้ แต่ sensitivity วัดไม่ได้ |
| 6 | preprocessing parity ระหว่างเบราว์เซอร์กับ Python: เกณฑ์ D7 |

---

# 1. ชุดข้อมูล
corpus ที่ใช้วัดตัวเลข accuracy ทั้งหมดตั้งแต่ D3 เป็นต้นไป ทำซ้ำได้ด้วยคำสั่ง:

```bash
cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare
```

ใช้ seed `42`, แบ่งแบบ stratified 70/15/15 และเก็บ manifest ที่ `data/processed/manifest.csv` คอลัมน์ `path` อ้างอิงจาก interim root (ค่าเริ่มต้นคือ `data/interim/`) จึงยังเปิดไฟล์ได้บนเครื่องอื่นหรือใน container

## แหล่งข้อมูล

จากแหล่งที่พิจารณาเก้าแห่ง มีสามแห่งที่ไม่ต้องใช้ credential และเปิดใช้เพียงสามแห่งนี้ ตรวจสอบเมื่อ 2026-10-13

| แหล่งข้อมูล | ต้นทาง | นำเข้าแล้ว | เสียหาย | ไม่มี label | กำกวม |
|---|---|---|---|---|---|
| `agml` | HF `Project-AgML/tea_leaf_disease_classification` | 5,867 | 0 | 0 | 0 |
| `yunusserhat` | HF `yunusserhat/tea_sickness_dataset` | 885 | 0 | 0 | 0 |
| `mendeley_mz598` | Mendeley `mz598gxfw9` v1 (Roboflow YOLO export) | 5,101 | 0 | 79 | 0 |
| **total** | | **11,853** | **0** | **79** | **0** |

`agml` นำเข้าภาพ 5,867 ภาพ ตรงกับจำนวนแยกคลาสใน dataset card จึงยืนยันว่าลำดับ ClassLabel ใน registry ถูกต้อง

`mendeley_mz598` มีภาพ 5,180 ภาพและไฟล์ label 5,180 ไฟล์ ในจำนวนนี้ไฟล์ label 79 ไฟล์ **ว่าง** — สำหรับ Roboflow export หมายถึงตัวอย่างพื้นหลังหรือ negative ที่ตั้งใจทำไว้ ไม่ใช่ annotation หาย — และไม่มีภาพใดขาดไฟล์ label ทั้ง 79 ภาพถูกข้ามเพราะไม่สามารถสร้าง target สำหรับ classification ได้ ไม่มีภาพใน archive ที่ถูก annotate เป็นสองคลาสต่างกัน

แหล่งที่ไม่ใช้: `mendeley_sjmy` (`sjmy6k24d6`) ตอบ HTTP 451 จึงตัดออก; แหล่ง Kaggle สองแห่งและ `ttkqwe123` ซึ่งเป็นแหล่ง gated ต้องใช้ credential จึงคงรายการไว้แต่ปิดใช้งาน; เลื่อน `mendeley_d2xy` (3.07 GB) และ `mendeley_94fz` (964 MB, .rar) ไว้เป็นข้อมูลเพิ่ม

## การลบข้อมูลซ้ำ

| | count |
|---|---|
| นำเข้าแล้ว | 11,853 |
| สำเนาซ้ำที่ยุบรวม | 3,505 |
| กลุ่มขัดแย้งข้ามคลาสที่ตัดออก | 32 |
| **corpus ที่ใช้ได้** | **8,316** |

แหล่งข้อมูลมีภาพซ้ำกันมาก: `agml` กับ `mendeley_mz598` มีภาพถ่ายร่วมกันจำนวนมาก ขั้นตอนนี้มีไว้ป้องกันข้อมูลรั่วไหลดังกล่าว

แต่ละกลุ่มเก็บสำเนาที่มีความละเอียดสูงที่สุด นี่คือเหตุผลที่จำนวนภาพ healthy ของ `agml` ลดจาก 1,000 ภาพที่นำเข้า เหลือ 104 ภาพใน manifest: `mendeley_mz598` มีภาพเดียวกันที่ขนาด 640×640 เทียบกับ 256×256 ของ agml จึงเลือกสำเนาที่ใหญ่กว่า

หากกลุ่มภาพซ้ำครอบคลุมสองคลาส จะตัดทั้งกลุ่มแทนการเลือกตามลำดับ sort เพราะการเก็บฝั่งใดฝั่งหนึ่งจะทำให้โมเดล train ด้วย label ที่ไม่มีผู้ annotate ให้ มี 32 กลุ่มที่ได้รับผล

### นิยามภาพซ้ำ

**ภาพสองใบเป็นภาพถ่ายเดียวกันเมื่อ mean absolute difference ของภาพย่อขาวดำขนาด 32×32 ไม่เกิน 8.0 จาก 255** นิยามอิงพิกเซล ไม่มี hash ใช้ตัดสิน `phash` คงไว้ในคอลัมน์ manifest เพื่อ audit เท่านั้น

เปรียบเทียบทุกคู่ โดยใช้ขอบเขตล่างแบบ exact เพื่อให้คำนวณได้จริง แทน filter ที่อาจตัดสินผิด: mean absolute difference ของค่าเฉลี่ยบล็อก 4×4 ไม่มีทางมากกว่า mean absolute difference ของพิกเซลที่บล็อกนั้นเฉลี่ย ดังนั้นถ้าขอบเขตจากบล็อกสูงกว่า threshold คู่นั้นก็ไม่มีทางผ่านการเทียบเต็มและข้ามได้ ไม่มีสิ่งใดถูกทิ้งเพราะค่าประมาณ และมี property test กับคู่สุ่ม 200 คู่ยืนยันขอบเขตนี้ เพราะถ้าขอบเขตเคยสูงกว่าค่าจริง ภาพซ้ำอาจหายไปโดยไม่มีรายงาน

### ที่มาของวิธีนี้และคำตอบผิดสองครั้งก่อนหน้า

บันทึกไว้เพราะสองวิธีแรกดูเหมือนถูกต้องและทั้งคู่สร้างตัวเลขที่ commit ก่อนตรวจสอบ

| method | usable corpus | cross-split duplicate pairs |
|---|---|---|
| perceptual hash ≤ 5, transitive grouping | 6,829 | not measured |
| perceptual hash ≤ 5, leader-based | 7,164 | not measured |
| hash ≤ 5 as candidate gate, pixels confirm | 8,541 | **127** |
| **pixels alone, exhaustive** | **8,316** | **0** |

1. **Transitive grouping chained near misses** into a single group of 866
   images, discarding hundreds of distinct photographs. Membership is judged
   against a group leader instead.
2. **A hash threshold is not a duplicate test.** At a Hamming distance of 5,
   24% of the pairs the hash collapsed had a pixel difference above 15 of 255 —
   two different leaves centred on the same background share a coarse layout,
   and a 64-bit hash sees little else. Adding a pixel confirmation fixed that
   precision problem.
3. **But using the hash to generate candidates silently capped recall.** A
   review of the resulting manifest found **127 cross-split pairs under the
   pixel threshold whose hashes were 6 to 30 apart**, so they were never offered
   as candidates: 83 images, 3.24% of the evaluation set, had a twin in
   training. The mechanism is that pHash thresholds DCT coefficients at their
   median, so a low-contrast image has many coefficients on that median and a
   near-identical copy flips them. Measured here: two images differing by 0.01
   of 255 hash **26 bits** apart.

เอกสารรุ่นก่อนระบุว่ากลุ่มภาพซ้ำกับไม่ซ้ำไม่มีส่วนทับซ้อน โดยอ้างอิงตัวอย่าง 40 คู่ แต่เมื่อตรวจทุกคู่พบว่าทั้งสองกลุ่มอยู่ติดกัน ไม่ได้แยกจากกัน นี่คือเหตุผลที่ threshold เป็นนิยามที่ระบุไว้ ไม่ใช่ช่องว่างที่ค้นพบ ค่านี้เลือกได้อย่างมั่นคง: กลุ่มที่ยอมรับมีค่าความต่างมัธยฐาน 0.07 จาก 255 และช่วง 5 ถึง 8 มีภาพที่รูปทรงหรือโทนสีเปลี่ยนจากภาพฐาน ซึ่งนับเป็นภาพซ้ำเพื่อป้องกัน leakage ภาพลักษณะนี้พบทั้งภายในแหล่งเดียวกันและข้ามแหล่ง จึงอธิบายด้วย augmentation ของผู้ส่งออกแหล่งเดียวไม่ได้

### การตรวจสอบ

ตรวจ manifest ที่สร้างเสร็จแล้วด้วยค่าพิกเซล โดยเทียบทุกคู่ ไม่ใช่เฉพาะคู่ที่ filter บางตัวเสนอมา:

- กลุ่มภาพซ้ำในภาพที่เหลือ 8,316 ภาพ: **8,316 กลุ่ม** จึงไม่มีภาพที่เหลือคู่ใดซ้ำกัน
- **คู่ภาพซ้ำข้ามชุด: 0** (เดิม 127)
- คู่ภาพซ้ำภายในชุดเดียวกัน: 0

## ภาพใน corpus

| คลาส | train | val | test | รวม |
|---|---|---|---|---|
| `grey_blight` | 966 | 207 | 207 | 1,380 |
| `brown_blight` | 832 | 177 | 177 | 1,186 |
| `algal_spot` | 937 | 200 | 200 | 1,337 |
| `healthy` | 1,009 | 215 | 215 | 1,439 |
| `other_disease` | 2,082 | 446 | 446 | 2,974 |
| **total** | **5,826** | **1,245** | **1,245** | **8,316** |

สัดส่วนต่อคลาสอยู่ที่ 70.0–70.2% / 14.9–15.0% / 14.9–15.0%

`other_disease` มีสัดส่วน 36% ของ corpus เพราะรวมคลาสจากแหล่งข้อมูลห้าชนิด (Anthracnose, Bird Eye Spot, Red Leaf Spot, Helopeltis, White Spot) การ train ใช้ sampling ให้สมดุลตามคลาส และรายงานผลประเมินเป็นแถวแยกพร้อม precision และ recall ของตัวเอง เพื่อไม่ให้ผลที่พลาดถูกซ่อนไว้

### แยกตามแหล่งข้อมูลและคลาส

| แหล่งข้อมูล | grey_blight | brown_blight | algal_spot | healthy | other_disease | รวม |
|---|---|---|---|---|---|---|
| `mendeley_mz598` | 785 | 559 | 658 | 1,274 | 1,420 | 4,696 |
| `agml` | 502 | 514 | 566 | 104 | 1,080 | 2,766 |
| `yunusserhat` | 93 | 113 | 113 | 61 | 474 | 854 |

### ความละเอียดภาพ

| ขนาด | จำนวนภาพ |
|---|---|
| 640×640 | 4,696 |
| 256×256 | 2,751 |
| 768×1024 | 545 |
| 3120×4160 | 168 |
| other | 156 |

classifier train ที่ 224×224 จึงลดขนาดภาพจากทุกแหล่ง ภาพถ่ายโทรศัพท์ขนาด 3120×4160 มาจาก `yunusserhat` และใกล้เคียงกับภาพที่คนงานจะถ่ายจริงที่สุดใน corpus

## สิ่งที่ไม่มีใน corpus นี้

ไม่มีภาพใบไหม้ทางกายภาพหรือแดดเผา แหล่งข้อมูลทั้งเก้าแห่งไม่มีคลาสประเภทนี้ จึงตรวจใบไหม้ด้วยตัววิเคราะห์รอยโรคแบบกฎเกณฑ์แทนการเพิ่มเป็นคลาสที่หก และใช้ specificity บนภาพที่ยืนยันว่าเป็นโรคเป็นตัวชี้วัดหลัก แทน accuracy ของการตรวจใบไหม้

## ข้อจำกัดที่ทราบ

- การตรวจภาพซ้ำใช้ภาพขาวดำ ดังนั้นภาพสองใบที่มีรูปทรงเหมือนกันแต่ต่างเฉพาะสีจะถูกมองเป็นภาพเดียวกัน
- สำเนาใดในกลุ่มภาพซ้ำจะถูกเก็บขึ้นกับ key ที่ใช้เรียง (`-pixel_area` แล้วตามด้วย path) เคยวัดแล้วว่าการเปลี่ยนลำดับกรณีเสมอกันกระทบราว 0.4% โดยเปลี่ยนว่าภาพใดเหลืออยู่ ไม่ใช่จำนวนภาพ
- ภาพ 32 ใบที่ตัดออกเพราะคลาสขัดแย้ง คือภาพที่สองแหล่งติดป้ายไม่ตรงกัน หากทบทวนด้วยมืออาจกู้ข้อมูล train จริงกลับมาได้

---

# 2. โมเดล
**วันที่:** 2026-10-19
**Checkpoint:** `data/artifacts/teasmart-v1.pt`, epoch 10 จาก 15 (หยุดก่อนกำหนด)
**Corpus:** `data/processed/manifest.csv`, 8,316 ภาพ, 5 คลาส, แบ่ง 70/15/15

ทำซ้ำได้ด้วยคำสั่ง:

```
cd ml
./.venv/Scripts/python.exe -m teasmart_ml.cli train
./.venv/Scripts/python.exe -m teasmart_ml.cli evaluate --split test
./.venv/Scripts/python.exe -m teasmart_ml.cli export
```

## 1. การ train

MobileNetV3-Large, ImageNet-pretrained, five outputs, 224x224, batch 32, AdamW
at 3e-4 with cosine decay, label smoothing 0.05, mixed precision, inverse
frequency sampling, early stopping on validation macro-F1 with patience 5.

| epoch | train loss | val loss | val accuracy | val macro-F1 |
|---|---|---|---|---|
| 1 | 0.5245 | 0.4102 | 0.9253 | 0.9255 |
| 5 | 0.2793 | 0.2883 | 0.9775 | 0.9769 |
| 7 | 0.2706 | 0.2792 | 0.9799 | 0.9804 |
| **10** | **0.2598** | **0.2591** | **0.9880** | **0.9885** |
| 14 | 0.2398 | 0.2570 | 0.9863 | 0.9868 |
| 15 | 0.2494 | 0.2763 | 0.9815 | 0.9823 |

หยุดที่ epoch 15 เพราะไม่มีการพัฒนาติดต่อกันห้า epoch โดย checkpoint มาจาก epoch 10

เลือกสถาปัตยกรรมจากข้อจำกัดของการ์ดจอบนแล็ปท็อป VRAM 4 GB ไม่ใช่ความชอบส่วนตัว และข้อจำกัดเดียวกันนี้ตรงกับข้อกำหนดผลิตภัณฑ์ เพราะโมเดลต้องรันในเบราว์เซอร์บนโทรศัพท์ด้วย

## 2. ชุดทดสอบ held-out

**ตัวเลขนี้คือตัวเลขที่ควรอ้าง** validation split ใช้เลือก epoch จึงมีแนวโน้มสูงกว่าความจริงตั้งแต่ต้น ส่วน test split ไม่ได้ถูกดูจนถึงขั้นตอนนี้

- images: **1,245**
- accuracy: **0.9871**
- macro-F1: **0.9873**

| คลาส | precision | recall | F1 | จำนวนตัวอย่าง |
|---|---|---|---|---|
| `grey_blight` | 0.9854 | 0.9758 | 0.9806 | 207 |
| `brown_blight` | 0.9778 | 0.9944 | 0.9860 | 177 |
| `algal_spot` | 0.9852 | 1.0000 | 0.9926 | 200 |
| `healthy` | 0.9953 | 0.9860 | 0.9907 | 215 |
| `other_disease` | 0.9887 | 0.9843 | 0.9865 | 446 |

### ตารางความสับสน (confusion matrix) ของ test split

แถวคือคลาสจริง

| คลาสจริง \ คลาสที่ทำนาย | `grey_blight` | `brown_blight` | `algal_spot` | `healthy` | `other_disease` |
|---|---|---|---|---|---|
| `grey_blight` | 202 | 1 | 2 | 0 | 2 |
| `brown_blight` | 1 | 176 | 0 | 0 | 0 |
| `algal_spot` | 0 | 0 | 200 | 0 | 0 |
| `healthy` | 0 | 0 | 0 | 212 | 3 |
| `other_disease` | 2 | 3 | 1 | 1 | 439 |

### ข้อผิดพลาดสามแบบที่กระทบเกษตรกร

ค่า F1 รวมซ่อนว่าความผิดพลาดใดสร้างต้นทุน รายการเหล่านี้คือแบบที่มีผลจริง:

| ความผิดพลาด | ความหมาย | test | val |
|---|---|---|---|
| diseased leaf called `healthy` | an outbreak goes untreated | **0 of 584** | **0 of 584** |
| `healthy` leaf given a disease name | fungicide sprayed for nothing | **0 of 215** | **0 of 215** |
| `other_disease` given a disease name | **the wrong fungicide** | 6 of 446 (1.35%) | 9 of 446 (2.02%) |

ไม่มีใบที่เป็นโรคถูกเรียกว่า healthy และไม่มีใบ healthy ได้ชื่อโรคในทั้งสอง split ความผิดพลาดที่เหลือคือเหตุผลที่เพิ่มคลาส `other_disease`: โรคที่ไม่คุ้นเคยถูกเรียกอย่างมั่นใจว่าเป็นหนึ่งในสามโรคที่โมเดลรู้จัก เกิดกับประมาณหนึ่งในเจ็ดสิบกรณี และเป็นเหตุผลที่ต้องมี confidence floor

ใบ healthy สามใบที่ถูกเรียกว่า `other_disease` เป็นความผิดพลาดที่ต้นทุนต่ำ: ระเบียนคำแนะนำของ `other_disease` ให้ปรึกษาผู้เชี่ยวชาญ ไม่ใช่ให้ฉีดพ่น

## 3. ชุด validation สำหรับเปรียบเทียบ

- images: 1,245 · accuracy **0.9880** · macro-F1 **0.9885**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| `grey_blight` | 0.9855 | 0.9855 | 0.9855 | 207 |
| `brown_blight` | 0.9725 | 1.0000 | 0.9861 | 177 |
| `algal_spot` | 0.9852 | 1.0000 | 0.9926 | 200 |
| `healthy` | 0.9953 | 0.9907 | 0.9930 | 215 |
| `other_disease` | 0.9932 | 0.9776 | 0.9853 | 446 |

ค่า macro-F1 ของ validation และ test ต่างกันไม่เกิน 0.001 แสดงว่าการเลือก epoch ไม่ได้ overfit กับชุดที่ใช้เลือก

## 4. `min_confidence`: 0.60 และเหตุผลที่เกณฑ์เดิมไม่เหมาะ

D3 ตั้งเป้าให้ได้ “floor ต่ำสุดที่ทำให้ prediction ที่ยอมรับมี accuracy 0.90 บน validation” **เกณฑ์นี้ใช้กับโมเดลนี้ไม่ได้ และการกำหนดเกณฑ์นี้เป็นความผิดพลาดของผู้เขียน** โมเดลมี accuracy 0.988 อยู่แล้ว การค้นหาจึงคืนค่าต่ำสุดใน grid:

| accuracy เป้าหมาย | floor ของ val | ลดระดับผลใน val | floor ของ test | ลดระดับผลใน test |
|---|---|---|---|---|
| 0.90 | 0.20 | 0.00% | 0.20 | 0.00% |
| 0.95 | 0.20 | 0.00% | 0.20 | 0.00% |
| 0.98 | 0.20 | 0.00% | 0.20 | 0.00% |
| **0.99** | **0.55** | **1.04%** | **0.63** | **1.20%** |
| 0.995 | 0.66 | 2.01% | 0.82 | 4.18% |

floor 0.20 หมายถึงไม่ปฏิเสธตอบเลย และปิด safety net ของ `other_disease` ทั้งหมด เกณฑ์นี้ถามเพียงให้ floor แก้ accuracy โดยเฉลี่ย แต่ไม่ได้ถามให้ตรวจจับ prediction รายตัวที่กำลังจะผิด

**แก้เกณฑ์ที่ใช้จริงเป็น accuracy 0.99 ใน prediction ที่ยอมรับ** เป้าหมายนี้ต้องใช้ floor 0.55 และ 0.63 ในสอง split ตามลำดับ ผลที่วัดได้เมื่อใช้ floor คงที่:

| floor | accuracy ใน val / สัดส่วนที่ลดระดับ | accuracy ใน test / สัดส่วนที่ลดระดับ |
|---|---|---|
| 0.50 | 0.9887 / 0.40% | 0.9871 / 0.08% |
| **0.60** | **0.9927 / 1.45%** | **0.9895 / 0.72%** |
| 0.70 | 0.9967 / 2.41% | 0.9926 / 1.85% |
| 0.80 | 0.9983 / 3.53% | 0.9942 / 3.45% |

**คง `min_confidence` ไว้ที่ 0.60** ค่านี้อยู่ระหว่างค่าที่สอง split ต้องการ ให้ accuracy 0.9895 บนข้อมูล held-out และปฏิเสธภาพ 0.72% ซึ่งน้อยกว่าหนึ่งในร้อยและผู้ใช้รับได้ ไม่ใช่ค่าคาดเดาชั่วคราวอีกต่อไป ตอนนี้ `backend/app/core/config.py` และ `GET /api/v1/config` ใช้ค่าที่วัดแล้ว

### สิ่งที่ floor นี้ทำไม่ได้

prediction ที่ผิดไม่ได้มี confidence ต่ำทั้งหมด:

| | val | test |
|---|---|---|
| mean top probability when wrong | 0.645 | 0.755 |
| **highest top probability when wrong** | 0.839 | **0.983** |

ภาพ test หนึ่งใบผิดที่ 0.983 **ไม่มี floor ที่ใช้งานได้จับข้อผิดพลาดนี้** floor ช่วยลดข้อผิดพลาดที่มั่นใจสูงแต่กำจัดไม่ได้ทั้งหมด และ UI ต้องไม่สื่อว่าผลที่สูงกว่า floor ถูกต้องแน่นอน นี่เป็นอีกเหตุผลที่ตัววิเคราะห์แผลไหม้กับโรคใน D4 สำคัญ เพราะเป็นหลักฐานอิสระจากใบเดียวกัน ซึ่งคำนวณจากรูปทรงรอยโรคแทน classifier

## 5. การส่งออก ONNX: ใช้ fp32 ไม่ใช่ int8

| graph | ขนาด | top-1 ที่ตรงกัน | probability ที่ต่างสูงสุด | อยู่ในขอบเขต 0.05 |
|---|---|---|---|---|
| fp32 `teasmart-v1.onnx` | 16.8 MB | 50/50 | **0.00000** | yes |
| int8 `teasmart-v1-int8.onnx` | 4.7 MB | 50/50 | **0.24819** | **no** |

วัดจากภาพ test 50 ภาพชุดเดิมที่กระจายสม่ำเสมอ โดยป้อน array หลัง preprocess ชุดเดียวกันให้โมเดล Python และ ONNX graph

calibrate int8 แบบคงที่ด้วยภาพ validation 200 ภาพแล้ว แต่ probability ยังขยับได้ถึง 0.248 บังเอิญที่ top-1 ตรงกันทั้ง 50 ภาพ ซึ่งแสดงว่าการตรงกันของ top-1 อย่างเดียวใช้เป็นเกณฑ์ผ่านไม่ได้: **ผลิตภัณฑ์ตั้ง threshold จาก probability** การขยับ 0.248 ทำให้ผลข้าม `min_confidence` ได้ทั้งสองทิศทาง เบราว์เซอร์จึงอาจปฏิเสธผลที่ server รับ หรือรับผลที่ server ปฏิเสธ โดยไม่มีฝั่งใดตรวจพบความไม่ตรงกัน

คาดการณ์ปัญหานี้ไว้แล้ว: MobileNetV3 เป็นกรณีที่แปลงเป็น int8 ได้ยาก เพราะ depthwise convolution มี weight ต่อ channel ให้ quantize น้อย และ hard-swish เป็นฟังก์ชันแบบแบ่งช่วง จึงต้องวัดผล export แทนการคาดเดา

**เปลี่ยนสัญญา:** หัวข้อ 8.4 ใน spec เคยระบุ `teasmart-v1-int8.onnx` ไฟล์ที่ต้องโหลดตอนนี้คือ **`teasmart-v1.onnx`**, 16.8 MB ไม่ commit int8 graph เพื่อไม่ให้เผลอส่งขึ้นระบบ สิ่งถัดไปที่ควรวัดคือ fp16 (ขนาดราว 8.4 MB และโดยทั่วไปคลาดไม่เกิน 1e-3) แต่ไม่ใช่งานสำคัญก่อน 2026-11-21

## 6. ข้อจำกัดที่ทราบ

**การแบ่งชุดไม่ได้จัดกลุ่มตามรอบถ่ายภาพ** D2 ลบภาพซ้ำข้าม split ด้วยการเทียบพิกเซลและตรวจทุกคู่แล้วว่าเหลือศูนย์ แต่ไม่ได้จัดภาพหลายช็อตของใบเดียวกันหรือพุ่มเดียวกันที่ถ่ายห่างกันไม่กี่นาทีเป็นกลุ่ม เพราะภาพเหล่านั้นไม่ใช่ภาพซ้ำตามการวัดพิกเซลและอาจอยู่คนละฝั่งของ split ดังนั้น **0.987 เป็นขอบบนของ accuracy ในไร่** ไม่ใช่ค่าประมาณ วิธีหาตัวเลขจริงอย่างตรงไปตรงมาคือใช้ภาพหลายร้อยภาพจากสิงห์ปาร์คที่โมเดลไม่เคยเห็น ซึ่งทำไม่ทันกำหนดส่ง

**ห้าคลาสคือสิ่งที่ corpus มี ไม่ใช่สิ่งที่พบได้ในไร่ทั้งหมด** ทุกอย่างที่ไม่ใช่ grey blight, brown blight, algal spot หรือใบสุขภาพดี จะเป็น `other_disease` รวมถึง red leaf spot, การขาดสารอาหาร และความเสียหายจากแมลง ซึ่งเกษตรกรต้องจัดการต่างกัน

**ไม่มีภาพใบไหม้หรือแดดเผาในแหล่งข้อมูลใดเลย** physical burn ไม่ใช่ output ของ classifier แต่เป็นผลจากตัววิเคราะห์แบบกฎใน D4 และใช้ specificity บนภาพที่ยืนยันว่าเป็นโรคเป็นตัวชี้วัดหลัก

**ภาพทุกภาพใน corpus เป็นภาพใบชาแบบระยะใกล้** ภาพจากโดรนที่ถ่ายจากที่สูงมี distribution ต่างกัน และ quality gate จะปฏิเสธภาพส่วนใหญ่ก่อนถึง classifier

---

# 3. Frontend

D6 PR: https://github.com/mntoyg/TeaSmart-AI/pull/2
D7 draft PR: https://github.com/mntoyg/TeaSmart-AI/pull/3

## ขอบเขตและสัญญา

D6 ทำ 4 route, ถ่ายภาพ/เลือกไฟล์, แสดงคำแนะนำภาษาไทยให้ถ่ายใหม่, การ์ดผลเรียงลำดับ, ประวัติใน IndexedDB และหน้า KB ส่วน D7 เพิ่ม app shell, ONNX/WASM worker ในเครื่อง, quality gate, การแสดงผล classifier-only, คิวภาพและผลลัพธ์ และการ replay batch แยกแต่ละรายการ สัญญาอยู่ในหัวข้อ 8 ของ `docs/DESIGN.md` และผู้ใช้ยืนยันใน `4fe7263` กับ `c53d9a0`; ไม่มีการแก้โค้ด backend หรือ ML

ดึงค่าตั้งตอน runtime จาก `/api/v1/config` ตัวสร้าง source สร้าง types และตัวอย่างโครงสร้างจากหัวข้อ 8.1 และ 8.5 รวมทั้งข้อจำกัดการส่งข้อมูลจากหัวข้อ 8 ไม่มีการ fallback ไปใช้ confidence floor ในตัวอย่างขณะ runtime

## หลักฐานจากคำสั่ง

รันจากไดเรกทอรี `frontend/` ของ D7:

```text
npm test
Test Files  10 passed (10)
Tests       47 passed (47)

npm run test:contract
tests 1
pass 1
fail 0

npm run build
Scan contract matches section 8
vite v8.3.4 building client environment for production...
dist/assets/ort-wasm-simd-threaded-DcHrbrbl.wasm  14,239.89 kB
PWA v2.0.0
mode      injectManifest
format:   es
precache  11 entries (14306.59 KiB)
files generated
```

**ผลนี้ถูกแทนที่เมื่อ 2026-10-19** หลังมีโมเดลแล้ว ตัวเลขต่อไปนี้วัดใน CI บน merge commit ซึ่งเป็นชุดที่จะส่งมอบ:

```text
Scan contract matches section 8
precache  12 entries (30736.26 KiB)

  dist/sw.js

npm audit --omit=dev --audit-level=high
found 0 vulnerabilities

Test-Path frontend/public/models/teasmart-v1-int8.onnx
False
```

การ build service worker ของ VitePWA แสดง deprecation warning `inlineDynamicImports` เมื่อใช้ Vite 8 แต่ build จบสำเร็จ บันทึกตามผลจริงและไม่เรียกว่า build ที่ไม่มี warning

## หลักฐานตอน test ล้มเหลว

- test ของ contract generator ล้มเหลวก่อนมี generator
- ชุด test API/camera/card ล้มเหลวก่อนมีโมดูลเหล่านั้น
- test ของ persistence, queue, inference, quality และ offline ล้มเหลวก่อนมี implementation
- Temporarily bypassing config guards produced four test failures; guards were
  restored before commit.
- Temporarily mislabelling classifier-only output as full produced a failure;
  the correct Thai label was restored before commit.
- The reconnect-before-inference-completes regression failed with a pending
  image and no replay request, then passed after the trigger was corrected.

## ข้อสังเกตจากเบราว์เซอร์

Using the Codex browser, the D6 shell was checked at desktop and 390px width.
Scan/history/KB routes rendered Thai content. The camera unit test covers denied
permission and track cleanup; real camera capture was not performed.

เปิด production preview ของ D7 ที่ `http://localhost:4173/scan` แล้วหยุด server จากนั้น request HTTP โดยตรงล้มเหลวตามที่คาด:

```text
Preview server stopped: request failed as expected
```

เมื่อ reload เบราว์เซอร์ยังแสดง scan shell ได้ และเมื่อไปหน้า history ก็ยังแสดงสถานะว่างได้ เป็นการยืนยันว่า shell ถูก cache เมื่อไม่มี server แต่ไม่ได้ยืนยัน inference ของโมเดลเมื่อปิดเครือข่ายบนอุปกรณ์ ปุ่มเตรียมใช้งานปฏิเสธสถานะพร้อมอย่างถูกต้องเมื่อ KB/config ใช้ไม่ได้ ภาพหน้าจอเป็นไฟล์ทบทวนในเครื่องและไม่มีการ commit ภาพส่วนตัว

## สิ่งที่ต้องทำก่อนถือว่า D7 เสร็จ

1. วางไฟล์ ONNX จริงจาก D5 ไว้ใน `frontend/public/models/` ของ worktree นี้ ไฟล์โมเดลที่ถูก ignore จะไม่ถูกคัดลอกข้าม worktree หรือรวมใน Git
2. ใช้ confidence floor ที่วัดจาก config endpoint จริง ยืนยัน class order, ชื่อ input/output และ preprocessing เทียบกับโมเดลที่ export แล้ว
3. รัน browser/Python parity ตามสัญญาด้วยภาพ 50 ใบ: top-1 ต้องตรงกันและความต่างสัมบูรณ์ของ probability แต่ละคลาสไม่เกิน 0.05 บันทึกว่า Python ใช้ input ทั้งภาพเหมือนกันหรือไม่; การแยกใบฝั่ง server เป็นความต่างอีกข้อที่อธิบายไว้ในหัวข้อ 8.4
4. ทดสอบ endpoint scan/config/KB/sync จริง รวมกรณี quality ไม่ผ่านบางรายการ การ replay หลังเชื่อมต่อกลับมา และ persistence บนโทรศัพท์สาธิต โดยปิดเครือข่ายตอน scan ในเครื่อง ยืนยันว่าการ์ดผลในเครื่องไม่อ้างว่าตรวจใบไหม้หรือความรุนแรงแล้ว
5. รวมโมเดลที่ถูก ignore เข้ากับ production assets แล้วทดสอบขั้นตอนเตรียมและ reload ซ้ำด้วย artifact นั้น

Merge D6 ก่อน เมื่อ merge PR ใดก็ตาม ให้รวมสถานะใน `docs/STATE.md` กับสถานะคู่ขนานของ Claude Code โดยเก็บทั้งงานที่เสร็จและงานที่เหลือของ agent ทั้งสองฝั่ง

## 3.1 ต้นทุนของการเปิดครั้งแรก

precache มีขนาด **30.7 MB จาก 12 รายการ**: WASM ของ onnxruntime-web 14.2 MB และโมเดล fp32 16.8 MB ที่เหลือมีขนาดเล็กเมื่อเทียบกัน นี่คือสิ่งที่ต้องดาวน์โหลดก่อนแอปจะทำงานออฟไลน์ได้ บนเครือข่ายที่ไม่เสถียรเป็นทุนเดิม

นี่คือต้นทุนที่ทราบและยอมรับ int8 graph จะลดโมเดลจาก 16.8 MB เหลือ 4.7 MB แต่ไม่ผ่านเกณฑ์ accuracy (หัวข้อ 2.5) ส่วน fp16 ที่ยังไม่ทดสอบมีขนาดกลางราว 8.4 MB การรันในเครื่องจะพบ 13 รายการและ 35 MB ก็ต่อเมื่อมีไฟล์เก่า `teasmart-v1-int8.onnx` ค้างใน `frontend/public/models/` จึง ignore ไฟล์นี้ทั้งด้วยเหตุผลด้านความแม่นยำและเพราะทุกไฟล์ในโฟลเดอร์ดังกล่าวจะถูก precache

---

# 4. ปรับเทียบด่านคุณภาพขั้นที่ 1 ใหม่

**วัดเมื่อ 2026-10-19 จากภาพใน corpus 400 ภาพ** โดยสุ่มทุกแถวที่ 20 ใน manifest หลัง endpoint scan ลดภาพเหลือ 4 MP — การลดขนาดทำให้ภาพเรียบขึ้น จึงลด Laplacian variance ที่ด่านตรวจอ่าน

## 4.1 ด่านตรวจปฏิเสธภาพจริง 70%

การ scan ใบจาก corpus ครั้งแรกผ่าน endpoint จริงได้ผล `blurry` ด้วยคะแนน **13.3** และ **52.1** เทียบกับ threshold 80 เมื่อใช้ค่าตั้ง D1 ระบบปฏิเสธภาพ **279 จาก 400 ภาพ (69.8%)** เดโมจะแสดง “ภาพเบลอ” เกือบทุกครั้ง

ตั้ง threshold ระหว่าง D1 โดยใช้ fixture สังเคราะห์เพียงภาพเดียวและไม่เคยเทียบกับ corpus

| คะแนน blur (variance of Laplacian) | |
|---|---|
| min | 4.6 |
| p1 | 9.8 |
| p2 | 15.8 |
| p5 | 22.3 |
| median | **75.9** |
| p75 | 169.2 |
| max | 590.9 |

ค่า 80 อยู่สูงกว่ามัธยฐานของ distribution ที่ควรใช้เป็นเกณฑ์ต่ำสุดเล็กน้อย แยกตามแหล่ง: agml มี median 212.8, mendeley_mz598 55.2, yunusserhat 45.4 — threshold เดียวต้องรองรับแหล่งที่ภาพนุ่มที่สุดด้วย

## 4.2 ลด blur_threshold จาก 80 เหลือ 15

| ค่าที่ลอง | สัดส่วนที่ปฏิเสธ |
|---|---|
| 10 | 1.2% |
| **15** | **2.0%** |
| 20 | 4.0% |
| 50 | 29.0% |
| 80 | 52.8% |

ค่า 15 ยอมรับภาพจริง 98% และยังตรวจจับภาพที่เบลอได้ เมื่อนำภาพที่คมที่สุด 20 ภาพมาวัดใหม่หลัง Gaussian blur:

| blur ที่ใช้ | median | max |
|---|---|---|
| 5x5 | 27.4 | 41.4 |
| **9x9** | **7.9** | **11.6** |
| 15x15 | 3.0 | 4.2 |

blur ขนาด 9x9 มีค่าสูงสุด 11.6 ซึ่งต่ำกว่า threshold ส่วน percentile ที่ 2 ของภาพที่ไม่แตะต้องคือ 15.8 ช่องว่างนี้เป็นระยะที่ใช้แยกภาพเบลอ blur 5x5 ยังผ่าน ดังนั้น **ตั้งใจยอมรับภาพที่สั่นเล็กน้อย** เพราะหากตรวจจับได้จะต้องปฏิเสธภาพดีประมาณหนึ่งในสาม

## 4.3 ปรับ exposure_max_mean จาก 215 เป็น 235

ค่า 215 ปฏิเสธภาพใน corpus 6.0% ไม่มีภาพใดใน 400 ภาพมีค่าเฉลี่ยเกิน 232.3; ใบชาบนกระดาษขาวกลางวันสว่างได้ตามปกติ ค่า 235 ไม่ปฏิเสธภาพเหล่านั้นและยังจับภาพที่เกือบขาวทั้งภาพได้

## 4.4 รายงาน high clipping แต่ไม่ใช้ตัดสิน

หลังแก้ blur และ exposure แล้ว ภาพ `agml` ทั้งสามใบยังไม่ผ่านด้วยเหตุ `overexposed` สาเหตุคือการตรวจ high-clipping แยก channel: **ภาพ corpus ค่ามัธยฐานมี channel หนึ่งอย่างน้อย 11% ที่ค่า 250 ขึ้นไป** และ percentile ที่ 90 มีถึง 72% เพราะถ่ายใบชาบนพื้นหลังสีขาว

ภาพทั้ง 24 ใบที่ค่าเฉลี่ยเกิน 215 มี channel clipping มากกว่า 10% เช่นกัน — การตรวจทั้งสองกำลังจับสิ่งเดียวกัน ซึ่งก็คือพื้นหลัง

**พื้นหลังที่สว่างล้นไม่ได้บอกว่าใบไม้สูญเสียรายละเอียดหรือไม่** การประเมินให้ถูกต้องต้องวัดภายใน leaf mask ซึ่งต้องใช้ขั้นที่ 2 แต่ขั้นที่ 1 ตั้งใจรันก่อนเพื่อให้ทำงานเร็วและย้ายไปรันในเบราว์เซอร์ได้ ทางเลือกมีเพียงวัดสิ่งที่ผิดหรือไม่วัดเลย ดังนั้น high clipping จึง **ยังวัดและรายงาน แต่ไม่ใช้เป็นเหตุปฏิเสธภาพ**

low clipping ยังคงเป็นเหตุปฏิเสธภาพ: ภาพที่ดำสนิทสูญเสียรายละเอียดในเงาที่ตัววิเคราะห์รอยโรคใช้จริง และไม่มีภาพใดใน 400 ภาพกระตุ้นเงื่อนไขนี้

## 4.5 ผลจาก endpoint จริงหลังการเปลี่ยน

ส่งภาพจาก corpus จริง 15 ภาพ ผ่าน endpoint ที่กำลังทำงาน โดยใช้หนึ่งภาพต่อคลาสต่อแหล่ง:

| แหล่ง / คลาส | ผลทำนาย | confidence | คำตัดสิน | ความรุนแรง | เวลา |
|---|---|---|---|---|---|
| mendeley / grey_blight | other_disease | 0.50 | disease | mild | 26 ms |
| yunusserhat / brown_blight | brown_blight | 0.99 | disease | mild | 66 ms |
| mendeley / brown_blight | brown_blight | 0.88 | disease | moderate | 35 ms |
| agml / brown_blight | brown_blight | 0.96 | disease | mild | 9 ms |
| mendeley / algal_spot | algal_spot | 0.91 | disease | mild | 23 ms |
| yunusserhat / healthy | healthy | 0.91 | disease | mild | 84 ms |
| mendeley / healthy | healthy | 0.87 | disease | mild | 24 ms |
| yunusserhat / other_disease | other_disease | 0.87 | disease | mild | 540 ms |
| mendeley / other_disease | other_disease | 0.92 | disease | mild | 50 ms |
| agml / other_disease | other_disease | 0.95 | disease | mild | 9 ms |

**ก่อนเปลี่ยนนี้ scan ผ่าน 3 จาก 15 ภาพ; หลังปรับ threshold ผ่าน 10 จาก 15 และหลังแก้ clipping ผ่าน 13 จาก 15** สองภาพที่ยังถูกปฏิเสธเป็นภาพ `yunusserhat` ที่นุ่มจริงและต่ำกว่า blur floor ซึ่งแสดงว่าด่านทำงานตามที่ตั้งใจ

**ไม่มีภาพโรคใดถูกเรียกว่า physical burn** นี่คือ specificity ที่ใช้ประเมินตัววิเคราะห์ใบไหม้ และในตัวอย่างนี้มี false positive 0 จาก 10 — เป็นเพียงข้อมูลประกอบ เพราะภาพสิบภาพยังไม่ใช่การวัดที่เพียงพอ ยังต้องรันกับ test split เต็มชุด

ภาพ grey blight ที่ลดระดับเป็น `other_disease` เมื่อ confidence 0.50 แสดงว่า confidence floor ปฏิเสธการระบุชื่อโรคที่ระบบไม่มั่นใจ

## 4.6 Frontend ติดต่อ backend จริง

Through the Vite dev proxy on port 5173, which is the path the browser uses:

```text
GET  /api/v1/config  -> 200   blur 15.0, exposure 40-235, min_confidence 0.60
GET  /api/v1/kb      -> 200   6 records
POST /api/v1/scan    -> 200   brown_blight 0.88, disease, moderate 6.8%, 69 ms
```

หน้า `/scan` โหลดเป็นภาษาไทย และดึง `/api/v1/kb` กับ `/api/v1/config` ตอน mount — ทั้งคู่ตอบ 200 ไม่มี console error — จากนั้นส่ง `FormData` POST จากในหน้าเว็บและได้ field ตามสัญญาครบสิบรายการพร้อมคำแนะนำภาษาไทย

ลำดับการทำงานครบ: browser origin, dev proxy, FastAPI, ถอดรหัส, ลดขนาด, quality gate, segmentation, ONNX, วิเคราะห์รอยโรค, ประเมินความรุนแรง และฐานความรู้

ทำซ้ำได้ด้วยคำสั่ง:

```bash
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000
cd frontend && npm run dev
curl -s -X POST http://localhost:5173/api/v1/scan \
  -F "image=@data/interim/mendeley_mz598/brown_blight/mendeley_mz598-000001.jpg"
```

---

# 5. ใบไหม้กับโรค: สิ่งที่กล่าวอ้างได้และไม่ได้

**วัดเมื่อ 2026-10-20 บน test split** จำนวน 1,245 ภาพ โดย 1,030 ภาพเป็นโรค ทำซ้ำได้โดยรันตัววิเคราะห์กับ manifest; script นี้ใช้วัดครั้งเดียว ส่วนพฤติกรรมที่ได้ถูกตรึงไว้ด้วย test ใน `backend/tests/test_lesion.py`

## 5.1 ตัวเลขหลักและเหตุผลที่ตัวเลขแรกทำให้เข้าใจผิด

**Specificity บนภาพที่ยืนยันว่าเป็นโรค: 97.18%** — มี 29 จาก 1,030 ภาพที่ถูกเรียกผิดว่า `physical_burn` คิดเป็น false-burn rate **2.82%** ต่ำกว่าเป้าหมายใน spec ที่กำหนดไว้น้อยกว่า 5%

การวัดครั้งแรกได้ **99.22%** แต่ตัวเลขนี้ไม่มีความหมาย ตัววิเคราะห์หา **รอยโรคที่วัดได้ไม่พบในใบที่เป็นโรค 610 จาก 1,030 ใบ (59%)** และกรณีที่ไม่พบจะคืนค่า `disease` พร้อม likelihood 0.0 ค่ามัธยฐาน `burn_likelihood` ของภาพโรคเท่ากับ 0.000 specificity สูงเพราะตัววิเคราะห์ไม่ได้ตรวจหา ไม่ใช่เพราะแยกได้ — เป็นการตัดข้อมูลลักษณะเดียวกับที่ทำให้ข้อสรุป “ประชากรสองกลุ่มไม่ทับซ้อนกันแล้ว” ใน D2 ผิด

## 5.2 พบข้อบกพร่องเชิงโครงสร้างสองข้อจากการวัด

**ขอบใบถูกอ่านเป็นรอยโรค** สีเขียวจางลงบริเวณขอบด้านในของใบจาก antialiasing เงาตามขอบ และความเบลอเล็กน้อย ใบ *ทุกใบ* มีสีเขียวน้อยกว่าบริเวณกลางใบ จึงผ่าน fractional cut-off ทุกค่า เมื่อลอง percentile อ้างอิงสี่ค่าและสัดส่วนห้าค่า **ทุกชุดให้ separation ติดลบ** — mask ทำงานกับใบ healthy บ่อยกว่าใบที่เป็นโรค:

| ตัดขอบออก | cut-off | พบ lesion บนใบโรค | พบ lesion บนใบ healthy | separation |
|---|---|---|---|---|
| 0 px | 0.55 | 75.9% | 96.0% | **−0.201** |
| 0 px | 0.75 | 99.3% | 100.0% | −0.007 |
| **8 px** | **0.55** | **65.2%** | **30.0%** | **+0.352** |
| 14 px | 0.55 | 59.6% | 27.0% | +0.326 |

**ความเสียหายริมใบอยู่นอก leaf mask ทั้งหมด** mask สร้างจากการเติมบริเวณภายใน contour ภายนอกของพื้นที่สีเขียว รอยแดดเผาสีฟางไม่ผ่านการตรวจ hue จึงไม่ใช่สีเขียว และเมื่อรอยเชื่อมถึงขอบใบจะเป็น concavity ที่เปิดออกสู่กรอบภาพ ไม่ใช่รูที่ปิดล้อม การเติม contour จึงกู้รอยนี้กลับมาไม่ได้ วัดตรงจาก burn fixture พบว่าปื้นดังกล่าวเพิ่ม **0 พิกเซล** ให้ leaf mask และไม่เพิ่มพิกเซลในการค้นหารอยโรค

**กรณีใบไหม้ — สิ่งที่ผลิตภัณฑ์นี้สร้างมาเพื่อตรวจจับ — มองไม่เห็นจากโครงสร้างเดิม** การใช้ convex hull ของบริเวณสีเขียวช่วยแก้ปัญหา:

| leaf mask | พบ lesion บนใบโรค | พบ lesion บนใบ healthy | พื้นที่ |
|---|---|---|---|
| filled contour | 65.2% | 30.0% | x1.000 |
| **convex hull** | **85.8%** | 61.0% | x1.051 |

การใช้ hull เป็น trade-off ที่เหมาะ แม้ separation แย่ลง เพราะสิ่งที่ต้องเกิดน้อยคือ **คำตัดสิน** ว่าใบไหม้ ไม่ใช่การพบรอยโรค หากพบรอยบนใบ healthy ระบบรายงานความรุนแรงเพียงไม่กี่เปอร์เซ็นต์ภายใต้ผลทำนาย `healthy` แต่ถ้าระบบไม่มีทางให้คำตัดสินว่าไหม้ได้เลย คุณสมบัตินี้ก็ไม่ทำงาน

test ก่อนหน้านี้เปรียบเทียบการเติม contour กับการเติมเฉพาะรูที่ปิดล้อมและพบว่าเหมือนกัน ซึ่งเป็นคู่เปรียบเทียบที่ผิด เพราะทั้งสองวิธีตัด concavity ที่เปิดถึงกรอบภาพออกเหมือนกัน

## 5.3 ผลหลังแก้ทั้งสองข้อ

| ตัวชี้วัด | ก่อนแก้ | หลังแก้ |
|---|---|---|
| diseased leaves with no measurable lesion | 610 of 1,030 (59%) | **325 of 1,030 (32%)** |
| specificity on disease images | 99.22% (censored) | **97.18%** |
| false burn rate | 0.78% (censored) | **2.82%**, target < 5% |
| median `burn_likelihood` on disease | 0.000 | 0.080 |
| synthetic burns flagged | 1 of 112 (0.9%) | 8 of 145 (5.5%) |
| untouched healthy leaves called burn | 3 of 200 | 5 of 200 |

แยกตามคลาส false burn: `grey_blight` 4/207 (1.93%), `brown_blight` 4/177 (2.26%), `algal_spot` 2/200 (1.00%), `other_disease` 19/446 (4.26%)

## 5.4 คุณลักษณะช่วยแยกประเภทได้

ทดสอบกับ fixture โดยคุณลักษณะทุกค่ามีทิศทางตามที่คาด:

| | edge_sharpness | ring_score | acervuli | edge_affinity | colour_zonation | score | likelihood |
|---|---|---|---|---|---|---|---|
| disease | 1.00 | 1.00 | 1.00 | 0.00 | 0.83 | −6.07 | 0.002 |
| burn | 0.04 | 0.00 | 0.00 | 0.21 | 0.34 | −0.73 | 0.325 |

คะแนนห่างกัน 5.3 หน่วย คุณลักษณะเหล่านี้ไม่ได้อ่านเพียง noise

## 5.5 ยังไม่ทราบ sensitivity และนี่คือคำตอบที่ตรงไปตรงมา

**ภาพไหม้สังเคราะห์มี median likelihood 0.254 ส่วนภาพโรคจริงสูงถึง 0.714 ที่ percentile 99 ทั้งสองกลุ่มทับซ้อนกัน** ภาพไหม้สังเคราะห์มีเพียง 5.5% ที่ผ่าน threshold 0.60

ข้อมูลนี้อธิบายได้ด้วยสองสมมติฐานที่มีน้ำหนักเท่ากัน:

1. คุณลักษณะเหล่านี้จับลักษณะใบไหม้จริงไม่ได้ หรือ
2. ภาพไหม้สังเคราะห์ไม่เหมือนใบไหม้จริงพอ — สร้างขึ้นจากนิยามคุณลักษณะเดียวกับที่ใช้ทดสอบ จึงยืนยันผลอย่างอิสระไม่ได้

**ข้อมูลที่มีแยกสองสมมติฐานนี้ไม่ได้** ไม่มีภาพใบไหม้ที่ติด label ในแหล่งข้อมูลเก้าแห่งที่สำรวจ จึงไม่มี ground truth สำหรับ calibrate **ห้ามกล่าวอ้างตัวเลข sensitivity ของคุณสมบัตินี้ ไม่ว่าจะบนเวทีสาธิตหรือที่ใด**

สิ่งที่กล่าวได้คือ ตัววิเคราะห์มีแนวโน้มสูงที่จะรายงาน `disease` ซึ่งเป็นทิศทางที่ปลอดภัยกว่า หากบอกว่าไหม้ผิดจะทำให้เกษตรกรไม่พ่นยาบนใบที่อาจติดเชื้อ ส่วนการพลาดใบไหม้จะทำให้พ่นยาบนใบที่ไม่จำเป็น ข้อผิดพลาดแรกมีต้นทุนสูงกว่า จึงคง `burn_threshold` ไว้ที่ 0.60 แม้ทำให้คำตัดสินว่าไหม้เกิดขึ้นน้อย

ตั้ง threshold ให้สูงกว่าค่า 0.325 ของ fixture โดยตั้งใจ หากลดลงเพื่อจับกรณีนั้น จะรวมภาพโรคจริงเข้ามาด้วย ซึ่งมี percentile ที่ 90 เท่ากับ 0.430 และ specificity จะลดลงอย่างมาก จึงบันทึก trade-off นี้ไว้แทนการยอมรับ

## 5.6 หลักฐานแบบใดจะช่วยหาคำตอบ

ต้องมีภาพใบชาจริงที่ถูกแดดเผาหรือเสียหายจากการพ่นสารหลายร้อยภาพและติด label ให้ถูกต้อง ภาพ 200 ใบก็เพียงพอสำหรับปรับน้ำหนักทั้งห้าและรายงาน sensitivity ได้ จนกว่าจะมีข้อมูลดังกล่าว คุณสมบัตินี้เป็น prior แบบระมัดระวังที่วัด specificity ได้แต่ยังวัด sensitivity ไม่ได้ และการสาธิตต้องบอกตามนี้ตรง ๆ

---

# 6. เบราว์เซอร์กับ Python ให้ผลตรงกัน: ผ่าน parity gate

**วัดเมื่อ 2026-10-20** หัวข้อ 8.4 ของ `docs/DESIGN.md` กำหนดเงื่อนไขนี้ก่อนเรียก D7 ว่าเสร็จ: ใช้ภาพ 50 ภาพชุดเดิมจาก manifest แล้ว pipeline ของเบราว์เซอร์กับ Python ต้องเลือก top-1 ตรงกันทุกภาพ และ probability ของทุกคลาสต้องต่างกันไม่เกิน **0.05**

```text
images              50
top-1 agreement     50/50
max prob delta      0.00283      (bound 0.05)
mean prob delta     0.00021
worst image         12.jpg
passes              true
```

**ผลต่างต่ำกว่าขอบเขตถึง 18 เท่า** การวัดครอบคลุมทั้งลำดับ: ถอดรหัส JPEG, ผ่าน canvas เพื่อให้แอปอ่านพิกเซลจากไฟล์, resize, ImageNet normalization และ fp32 ONNX graph Pillow กับเบราว์เซอร์ถอดรหัส JPEG ไม่เหมือนกันทุกประการ และความต่างนี้ถูกรวมอยู่ในตัวเลขแทนการละไว้

## 6.1 สิ่งที่ต้องแก้

เบราว์เซอร์ sample เพื่อนบ้านสี่พิกเซล ส่วน PIL ปรับ support ของ triangle filter ตามอัตราการย่อ เมื่อทดสอบภาพ corpus 12 ภาพ preprocessing ทั้งสองทางต่างกันได้ถึง **101 จาก 255** ในหนึ่ง channel โดยต่างที่สุดกับภาพถ่ายโทรศัพท์ 3120x4160 ซึ่งเป็น input ที่ใช้สาธิต

| ภาพ | ขนาด | ความต่างสูงสุดของ channel |
|---|---|---|
| agml-005147 | 256x256 | 12 |
| mendeley_mz598-004194 | 640x640 | 49 |
| yunusserhat-000096 | 768x1024 | 53 |
| **yunusserhat-000415** | **3120x4160** | **101** |

เปลี่ยนฝั่ง Python ไม่ได้ เพราะ classifier train จาก output ของ PIL เบราว์เซอร์จึง implement อัลกอริทึมของ PIL และบรรทัดที่ขาดคือการเพิ่ม filter support ตามอัตราการย่อ เมื่อขยายภาพ support คงที่ที่ 1 และลดรูปเป็น bilinear ปกติ นี่คือเหตุผลที่กรณี 256x256 ตรงกันก่อนแก้แล้ว และเหตุผลว่าทำไม fixture ที่มีแต่ภาพเล็กอาจทำให้เข้าใจผิดว่าแก้ bug แล้ว

## 6.2 วิธีทำซ้ำ

```bash
backend/.venv/Scripts/python.exe scripts/prepare_parity.py   # 50 images + answers
cd frontend && npm run dev
```

เปิด `http://localhost:5173/scan` แล้ววาง `scripts/parity_browser.js` ใน console จากนั้นรัน `await runParity()`

เลือกทุกแถวที่ 24 ของ test split แทนการสุ่ม เพื่อให้ได้ตัวเลขชุดเดียวกันทุกเครื่องและก่อน/หลัง export ใหม่ ภาพและไฟล์เฉลยถูก gitignore เพราะเป็นภาพจาก corpus

## 6.3 Fixture ระดับ unit ที่รองรับการตรวจนี้

`frontend/src/test/fixtures/preprocess/` มีภาพต้นทางห้ารูปที่ทั้งสองภาษา generate จาก coordinate hash พร้อม byte ที่ PIL สร้างให้แต่ละรูป Vitest ตรวจฝั่งเบราว์เซอร์ ส่วน pytest ตรวจฝั่ง server ทั้งสาม implementation จึงอิงนิยามเดียวกัน ตั้งใจให้การย่อครอบคลุม 1.14x ถึง 18.6x เพราะข้อบกพร่องแปรตามอัตราการย่อ

ทั้งห้ากรณีผ่าน โดยความต่างไม่เกิน **2 จาก 255** ต่อ channel และค่าเฉลี่ยไม่เกิน **0.30**

มี test อีกสองรายการตรวจคุณสมบัตินอกเหนือจาก fixture: รายการแรกลองใช้ sampler แบบสี่เพื่อนบ้านเดิมกับ fixture ที่ลดภาพมาก และบังคับให้ต่างเกิน 30 เพื่อไม่ให้ fixture หยุดตรวจข้อผิดพลาดที่สร้างมาโดยไม่รู้ตัว อีกรายการวางแถวสว่างหนึ่งแถวในตำแหน่งที่ไม่มี output centre ผ่าน แล้วตรวจว่าแถวนั้นยังอยู่หลังลดภาพ 9 เท่า เพื่อระบุคุณสมบัติที่ filter ต้องขยายตรง ๆ

## 6.4 ผลนี้ยืนยันอะไรได้บ้าง

ผลนี้ยืนยันเส้นทางออฟไลน์: ผลบนอุปกรณ์ต่างจากผล server เฉพาะในส่วนที่เบราว์เซอร์ทำไม่ได้จริง ไม่ใช่เพราะความผิดพลาดจากการ resize

ผลนี้ **ไม่ได้ทำให้ผลบนอุปกรณ์เทียบเท่าผลจาก server** เบราว์เซอร์ไม่แยกใบ จึงไม่มีผลวิเคราะห์รอยโรคหรือความรุนแรง และการ์ดผลยังต้องระบุ `classifier_only` นี่เป็นความแตกต่างของผลิตภัณฑ์ ไม่ใช่ข้อบกพร่อง และ parity gate ไม่ได้ตรวจเรื่องนี้
