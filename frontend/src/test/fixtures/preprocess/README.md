# Fixture ตรวจความตรงกันของ preprocessing

**สร้างอัตโนมัติ ห้ามแก้ด้วยมือ** สร้างใหม่ด้วยคำสั่ง:

```
cd ml && ./.venv/Scripts/python.exe -m teasmart_ml.cli fixtures
```

## สร้างไว้ทำไม

หัวข้อ 8.4 ของ spec ระบุว่า “ปรับขนาดเป็น 224x224 ด้วย bilinear” แต่คำอธิบายยังไม่ละเอียดพอ ทำให้สองฝั่งของสัญญา implement คนละแบบ เมื่อวัดจากภาพในคลัง 12 ภาพ พบว่าค่าพิกเซลต่างกันได้ถึง **101 จาก 255** ในหนึ่ง channel โดยต่างมากที่สุดในภาพถ่ายโทรศัพท์ความละเอียดเต็ม ซึ่งเป็น input ที่ใช้สาธิต

**ห้ามเปลี่ยนฝั่ง Python** classifier ฝึกจาก output ของ PIL ดังนั้น PIL คือข้อกำหนด fixture เหล่านี้เผยแพร่ผลลัพธ์นั้นให้ทั้งสองฝั่งเทียบกัน

## วิธีใช้ fixture

สำหรับแต่ละกรณีใน `manifest.json`:

1. สร้างภาพต้นทางจาก `source` (ดูตัวสร้างด้านล่าง)
2. ปรับขนาดเป็น 224x224 ด้วยอัลกอริทึมด้านล่าง
3. เทียบกับ `expected`: byte ของ RGB ดิบ เรียงตามแถวและให้ channel อยู่ท้ายสุด ดังนั้นตำแหน่งคือ `expected[(y * 224 + x) * 3 + c]` มีทั้งหมด 224*224*3 = 150,528 bytes ทั้งสองฝั่งจึงไม่ต้องใช้ decoder

ถือว่าผ่านเมื่อ **ทุก channel ต่างไม่เกิน `tolerance.max`** และ **ค่าเฉลี่ยความต่างสัมบูรณ์ไม่เกิน `tolerance.mean`** Pillow ใช้สัมประสิทธิ์จำนวนเต็มแบบ fixed-point จึงไม่ตรงกับ implementation ที่ใช้ float ทุกบิต อนุญาตให้ต่างจากการปัดเศษได้หนึ่งระดับ implementation แบบเพื่อนบ้านสี่จุดปัจจุบันต่างกันอย่างน้อย 30 จึงไม่มีโอกาสที่ implementation ผิดจะผ่านโดยบังเอิญ

## อัลกอริทึม: PIL bilinear ซึ่งเป็น triangle filter ที่ปรับขนาดได้

จุดที่มักพลาดคือ **filter จะขยาย support เมื่อย่อภาพ** อัลกอริทึมแยกตามแกนได้ จึงทำสองรอบ คือแนวนอนแล้วตามด้วยแนวตั้ง

สำหรับหนึ่งแกน เมื่อ `inSize` คือจำนวนพิกเซลต้นทางและ `outSize` คือจำนวนพิกเซลปลายทาง:

```
scale   = inSize / outSize
support = scale > 1 ? scale : 1.0        // THIS is the step that is missed
```

สำหรับ output index `i` แต่ละค่า:

```
centre = (i + 0.5) * scale
start  = max(0, floor(centre - support + 0.5))
stop   = min(inSize, ceil(centre + support + 0.5))

for j in [start, stop):
    // triangle filter, argument normalised by the support
    t = abs((j + 0.5 - centre) / support)
    w = t < 1.0 ? 1.0 - t : 0.0
    weights.push(w)

normalise weights so they sum to 1
output[i] = sum(weights[k] * input[start + k])
```

จำกัดค่าให้อยู่ใน `[0, 255]` และปัดครึ่งออกจากศูนย์เมื่อจบทั้งสองรอบเท่านั้น เก็บผลระหว่างรอบเป็น float

เมื่อ `scale <= 1` (ขยายภาพ หรือกรณี 256x256) ค่า `support` เท่ากับ 1.0 จึงลดรูปเป็น bilinear ปกติ ซึ่งเป็นเหตุผลว่าทำไมกรณีขนาดเล็กจึงตรงกันอยู่แล้ว

## ตัวสร้างภาพต้นทาง

ใช้ seed แทนการ commit JPEG เพื่อให้ชุด fixture มีขนาดเล็ก พิกเซลสร้างจาก **hash ของพิกัด** ไม่ใช่ตัวสร้างเลขแบบไล่ลำดับ ดังนั้นพิกเซล `(y, x, c)` เป็นฟังก์ชันจากพิกัดของตัวเอง ไม่มีลำดับของ stream ที่สองภาษาจะตีความไม่ตรงกัน

การคูณทุกครั้งตัดเหลือ 32 บิต ใน JavaScript ใช้ `Math.imul` แล้วตามด้วย `>>> 0`; การเลื่อนบิตต้องใช้ `>>>` แบบ unsigned

```js
function pixelByte(seed, y, x, c) {
  let v = (seed ^ Math.imul(x, HASH_X) ^ Math.imul(y, HASH_Y) ^ Math.imul(c, HASH_C)) >>> 0;
  v = Math.imul(v ^ (v >>> 15), MIX_1) >>> 0;
  v = Math.imul(v ^ (v >>> 13), MIX_2) >>> 0;
  v = (v ^ (v >>> 16)) >>> 0;
  return v >>> 24;
}
```

ค่าคงที่อยู่ใน `manifest.json` ใต้ `generator`

- **`noise`** — `source[y][x][c] = pixelByte(seed, y, x, c)`
- **`gradient`** — ใช้จำนวนเต็มเท่านั้นเพื่อไม่ให้การปัดเศษต่างกัน: `red = Math.floor(x * 255 / (width - 1))`, `green = Math.floor(y * 255 / (height - 1))`, `blue = (red + green) >> 1`
- **`blocks`** — สร้าง block ขนาด 8x8x3 จาก `pixelByte(seed, by, bx, c)` แล้วกำหนด `source[y][x] = block[Math.floor(y * 8 / height)][Math.floor(x * 8 / width)]`

## กรณีทดสอบ

ปัจจัยสำคัญคืออัตราการย่อ ชุดนี้ตั้งใจครอบคลุมตั้งแต่ 1.14x ถึง 18.6x หากใช้แต่ภาพต้นทางขนาดเล็ก bug นี้คงถูกส่งต่อไปแล้ว
