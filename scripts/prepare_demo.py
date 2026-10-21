"""Pick the demo set, and record exactly what each image will do on stage.

Run it before a demo:

    backend/.venv/Scripts/python.exe scripts/prepare_demo.py        # Windows
    backend/.venv/bin/python scripts/prepare_demo.py                # otherwise

It searches the test split with the real pipeline - the real ONNX graph, the
real thresholds - and fills a fixed list of demo slots with images that behave
the way each slot needs. Then it copies them into `demo/` and writes
`docs/DEMO.md` with the measured outcome for every one.

Why it works this way rather than someone picking files by eye: on stage,
nobody wants to discover that the "severe brown blight" photograph is the one
the quality gate rejects. Every image here has been through the pipeline and
its result is written down. If a slot cannot be filled, the script says so
instead of substituting something that does not fit.

Nothing it copies is committed. The corpus images come from public research
datasets whose redistribution terms differ, and the repository has no business
holding photographs it did not create. `demo/` is gitignored; `docs/DEMO.md`
records which file went in each slot so the set is reproducible.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.api.v1.scan import QualityRejected, analyse, downscale_for_analysis  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.classify import load_session  # noqa: E402
from app.services.quality import assess_quality  # noqa: E402


@dataclass(frozen=True)
class Slot:
    name: str
    headline: str
    wants_class: str | None
    rejected: bool = False
    low_confidence: bool = False
    min_confidence: float = 0.0
    min_severity: str | None = None
    # Demo robustness, both learned from the first run of this script.
    #
    # A diseased leaf reported at "mild, 0.0%" invites the obvious question,
    # and the honest answer is that the lesion analyser found nothing
    # measurable - true of 32% of diseased leaves. That is in EVIDENCE.md where
    # it belongs; a demo slot should show the feature working.
    min_affected_pct: float = 0.0
    # The first healthy pick scored 0.46 against a burn threshold of 0.60. Not
    # wrong, but one tweak away from announcing sun scorch on a healthy leaf in
    # front of judges.
    max_burn_likelihood: float = 1.0


# The running order. It builds: it works, it is careful, it knows what it does
# not know.
SLOTS: tuple[Slot, ...] = (
    Slot(
        "01-brown-blight-severe",
        "วินิจฉัยชัดบนใบที่เสียหายจริง — ข้อกล่าวอ้างหลัก",
        "brown_blight",
        min_confidence=0.80,
        min_severity="moderate",
        min_affected_pct=0.05,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "02-grey-blight",
        "โรคที่สอง เพื่อให้เห็นว่าไม่ใช่กลลวงคลาสเดียว",
        "grey_blight",
        min_confidence=0.70,
        min_affected_pct=0.01,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "03-algal-spot",
        "โรคที่สาม พร้อมคำแนะนำคนละชุดจากฐานความรู้",
        "algal_spot",
        min_confidence=0.70,
        min_affected_pct=0.01,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "04-healthy",
        "ใบปกติ ซึ่งห้ามถูกตั้งชื่อโรคให้",
        "healthy",
        min_confidence=0.70,
        max_burn_likelihood=0.25,
    ),
    Slot(
        "05-unsure-declines-to-name",
        "เพดานความเชื่อมั่น: ตอบ other_disease แทนการเดา",
        None,
        low_confidence=True,
    ),
    Slot(
        "06-blurry-asks-for-a-retake",
        "ด่านคุณภาพ: บอกเป็นภาษาไทยให้ถ่ายใหม่ ไม่ใช่หน้า error",
        None,
        rejected=True,
    ),
)

_PHONE_SECTION = """
## ทดสอบบนมือถือจริง

ทุกอย่างข้างล่างที่ตรวจได้จากเครื่องพัฒนา ตรวจแล้วและมีตัวเลขกำกับ
ส่วนที่เหลือคือการกดปุ่มบนเครื่องจริง ซึ่งไม่มีใครทำแทนได้

### 1. กรรมการเปิดจาก URL สาธารณะ ไม่ต้องตั้งอะไรเลย

**https://teasmart-ai.pages.dev**

เป็น HTTPS จริงบนโดเมนสาธารณะ จึงเป็น secure context ตามสเปก — กล้อง
service worker ใช้งานออฟไลน์ และติดตั้งลงหน้าโฮม ทำงานครบโดย**ไม่ต้องลงใบรับรอง
ไม่ต้องตั้ง flag ไม่ต้องต่อสาย และไม่ต้องอยู่ wifi วงเดียวกัน**

**deploy เฉพาะ frontend ไม่มี backend** ภาพที่กรรมการถ่ายจึงไม่ออกจากเครื่องตัวเอง
และผลที่ได้เป็น `classifier_only` — **ไม่มีคำตัดสินโรค-กับ-ใบไหม้ และไม่มีความรุนแรง**
สองอย่างนั้นสาธิตจากโน้ตบุ๊กที่รัน pipeline เต็ม **ต้องพูดความต่างนี้ออกมาให้ชัด**
ขั้นตอน deploy อยู่ใน `docs/DEPLOY-TH.md`

### 2. ตรวจเจ็ดข้อนี้ตามลำดับ

แต่ละข้อขึ้นกับข้อก่อนหน้า

1. **เลย์เอาต์** ตรวจที่ 375x812 แล้วไม่มีการเลื่อนแนวนอน แต่เครื่องจริงมีรอยบาก
   มีขนาดฟอนต์ของระบบ และมีคีย์บอร์ด
2. **กล้อง** กด `เปิดกล้อง` อนุญาตสิทธิ์ แล้วถ่ายใบชา ต้องได้กล้องหลัง
   (`facingMode: environment`)
3. **สแกนออนไลน์** การ์ดผลต้องบอกชื่อโรคเป็นภาษาไทย
   **บน URL สาธารณะผลจะเป็น `classifier_only` เสมอ ไม่ใช่ `full`**
   และความรุนแรงจะขึ้นว่า `รอการวิเคราะห์เพิ่มเติม` เพราะ deploy ไม่มี backend
   ยืนยันบน iPhone สองเครื่องเมื่อ 2026-10-21 **นั่นคือพฤติกรรมที่ถูกต้อง
   ไม่ใช่ข้อผิดพลาด** จะได้ `full` ก็ต่อเมื่อรันคู่กับ backend บนโน้ตบุ๊ก
4. **ติดตั้ง** เมนูของเบราว์เซอร์จะเสนอ Add to home screen เมื่อ service worker
   ลงทะเบียนแล้ว **เปิดจากไอคอนที่ติดตั้ง ไม่ใช่จากแท็บ**
5. **เตรียมออฟไลน์** กด `เตรียมใช้งานออฟไลน์` แล้วรอ ขั้นนี้ดาวน์โหลด
   **30.7 MB** — WASM 14.2 MB และโมเดล 16.8 MB — ทำบน wifi ก่อนวันงาน ไม่ใช่บนเวที
6. **ออฟไลน์** เปิดโหมดเครื่องบินแล้วสแกน ผลต้องถูกกำกับว่า `classifier_only`
   เพราะเบราว์เซอร์ไม่แยกใบออกจากพื้น จึงไม่มีการวิเคราะห์แผลและไม่มีความรุนแรง
   **และการ์ดต้องบอกแบบนั้น**
7. **ต่อเน็ตกลับ** คิวจะส่งซ้ำผ่าน `POST /api/v1/sync/batch` แล้วผลถูกเติมให้ครบ
   **สแกนภาพเดิมซ้ำต้องไม่เกิดรายการประวัติสองอัน** เซิร์ฟเวอร์จะคืนผลที่เก็บไว้
   พร้อม `replayed: true`

### 3. ข้อ 6 วัดตัวโมเดล ไม่ใช่แค่วัดท่อ

การย่อภาพของเบราว์เซอร์ใช้อัลกอริทึมเดียวกับ PIL แล้ว ผลบนเครื่องจึงไม่ได้เพี้ยน
จากผลเซิร์ฟเวอร์ด้วยเหตุผลเรื่องการเตรียมภาพ การตรวจ parity 50 ภาพที่
`docs/DESIGN.md` หัวข้อ 8.4 กำหนดเป็นเงื่อนไขของ D7 **ผ่านเมื่อ 2026-10-20**

```text
images              50
top-1 agreement     50/50
max prob delta      0.00283      (bound 0.05)
passes              true
```

**ห่างจากขอบสิบแปดเท่า** ครอบคลุมทั้งสาย: การถอดรหัส JPEG, การวนผ่าน canvas,
การย่อภาพ, การ normalise แบบ ImageNet และกราฟ fp32 ผลออฟไลน์จึงเป็นโมเดลตัวเดียวกัน
ที่ให้คำตอบเดียวกัน และข้อ 6 ควรนำเสนอแบบนั้น

สิ่งที่ยังต่างกันตอนออฟไลน์คือ *pipeline* ไม่ใช่โมเดล — เบราว์เซอร์ไม่แยกใบ
จึงไม่มีการวิเคราะห์แผลและไม่มีความรุนแรง การ์ดจึงบอกว่า `classifier_only`
**นั่นคือความต่างเชิงสินค้า ไม่ใช่ข้อบกพร่อง** หลักฐานและคำสั่งที่ผลิตตารางข้างบน:
`docs/EVIDENCE.md` หัวข้อ 6

### 4. ถ้าต้องทดสอบ build ของเครื่องพัฒนาบนมือถือ

ขั้นตอนเต็มเป็นภาษาไทยอยู่ใน `docs/PHONE-TH.md` ซึ่งเขียนให้อ่านบนมือถือและกดลิงก์ได้
สรุปสิ่งที่วัดไว้:

- **Vite ผูกกับ `127.0.0.1` โดยปริยาย** มือถือจึงเข้าไม่ถึงเลย — วัดแล้ว ตัวรับฟัง
  คือ `TCP 127.0.0.1:5173` เท่านั้น ต้องรัน `npm run dev -- --host`
  ส่วน backend ไม่ต้องใช้ flag เพราะมือถือคุยกับ Vite แล้ว Vite proxy `/api` ต่อ
- **ผ่าน HTTP ธรรมดาจาก LAN กล้องกับออฟไลน์จะไม่มีอยู่** วัดในเบราว์เซอร์ที่
  `http://<lan-ip>:5173` ได้
  `{ "isSecureContext": false, "hasServiceWorker": false, "hasMediaDevices": false }`
  — ไม่ใช่ถูกบล็อก แต่ **ไม่มีอยู่** เป็นกฎของเบราว์เซอร์เรื่อง secure context
  ไม่ใช่ข้อบกพร่องของแอป (`localhost` ได้รับการยกเว้น)
- **Android: `adb reverse tcp:5173 tcp:5173`** ยกพอร์ตขึ้นเป็น `localhost` ของมือถือ
  ซึ่งได้รับการยกเว้น จึงได้ครบโดยไม่ต้องใช้ใบรับรองเลย และ
  `scrcpy --record=demo.mp4` อัดวิดีโอจากสายเดียวกัน
  วัดไว้: scrcpy 4.1, adb 1.0.41 (platform-tools 37.0.0)
- **เปิด terminal ใหม่หลังติดตั้ง scrcpy** winget ใส่โฟลเดอร์ลง user PATH และสร้าง
  link ให้แค่ `scrcpy` ส่วน process ที่รันอยู่แล้วถือ environment เดิม terminal ที่
  รัน install จึงขึ้น `'adb' is not recognized` ซึ่งดูเหมือนติดตั้งพลาด
- **iPhone ใช้สองทางแรกไม่ได้** ไม่มี `adb` และ Chrome บน iOS เป็น WebKit ที่ไม่มี
  flag สำหรับ insecure origin จึงต้องใช้ `mkcert` แล้วตั้งให้เชื่อ root certificate
  บนเครื่อง หรือใช้ tunnel
- **ห้ามใช้ mkcert หรือ tunnel กับมือถือของกรรมการ** การขอให้กรรมการเชื่อ CA ของเรา
  บนเครื่องส่วนตัวเป็นสิ่งที่ไม่ควรขอ และ tunnel ส่งทุกภาพผ่านบุคคลที่สาม
  ทางสำหรับกรรมการคือข้อ 1 ข้างบน
"""

_SEVERITY_ORDER = {"mild": 0, "moderate": 1, "severe": 2}


def load_rgb(path: Path, limit: int) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        rgb = np.asarray(image.convert("RGB"))
    return downscale_for_analysis(rgb, get_settings()) if rgb.size else rgb


def fits(slot: Slot, outcome: dict[str, Any]) -> bool:
    if slot.rejected:
        return outcome["rejected"]
    if outcome["rejected"]:
        return False
    if slot.low_confidence:
        return bool(outcome["low_confidence"])
    if outcome["low_confidence"]:
        return False
    if slot.wants_class and outcome["class_name"] != slot.wants_class:
        return False
    if outcome["confidence"] < slot.min_confidence:
        return False
    if slot.min_severity and (
        _SEVERITY_ORDER[outcome["level"]] < _SEVERITY_ORDER[slot.min_severity]
    ):
        return False
    if outcome["affected_pct"] < slot.min_affected_pct:
        return False
    if outcome["burn_likelihood"] > slot.max_burn_likelihood:
        return False
    # A demo image should look like the thing it is demonstrating, so the
    # verdict has to agree with the class: a burn verdict on a slot that says
    # brown blight would contradict the slide.
    return not (slot.wants_class and outcome["verdict"] == "physical_burn")


def measure(path: Path, runner, settings) -> dict[str, Any] | None:
    try:
        payload = path.read_bytes()
        rgb = load_rgb(path, settings.max_analysis_pixels)
        quality = assess_quality(
            rgb,
            blur_threshold=settings.blur_threshold,
            exposure_min_mean=settings.exposure_min_mean,
            exposure_max_mean=settings.exposure_max_mean,
            clip_max_pct=settings.clip_max_pct,
        )
        if not quality.passed:
            return {
                "rejected": True,
                "reason": quality.reason,
                "reason_th": quality.reason_th,
                "blur_score": quality.blur_score,
                "low_confidence": False,
            }
        result = analyse(
            payload,
            scan_id=None,
            captured_at=None,
            settings=settings,
            runner=runner,
        )
    except QualityRejected as rejection:
        return {
            "rejected": True,
            "reason": rejection.detail,
            "reason_th": rejection.detail_th,
            "blur_score": rejection.quality.blur_score,
            "low_confidence": False,
        }
    except Exception:  # noqa: BLE001 - a corrupt corpus file is not interesting
        return None

    return {
        "rejected": False,
        "class_name": result.prediction.class_name,
        "confidence": result.prediction.confidence,
        "low_confidence": result.prediction.low_confidence,
        "verdict": result.burn_analysis.verdict,
        "burn_likelihood": result.burn_analysis.burn_likelihood,
        "level": result.severity.level,
        "affected_pct": result.severity.affected_pct,
        "advice": result.advice.canonical,
        "disease_name_th": result.advice.disease_name_th,
        "processing_ms": result.processing_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=REPO / "data/processed/manifest.csv")
    parser.add_argument("--interim", type=Path, default=REPO / "data/interim")
    parser.add_argument("--out", type=Path, default=REPO / "demo")
    parser.add_argument("--doc", type=Path, default=REPO / "docs/DEMO.md")
    parser.add_argument("--candidates", type=int, default=140,
                        help="images to try per slot before giving up")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.model_path.is_file():
        print(f"no model at {settings.model_path}. Export it first:")
        print("  cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli export")
        return 1
    if not args.manifest.is_file():
        print(f"no manifest at {args.manifest}. Build the corpus first:")
        print("  cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli prepare")
        return 1

    runner = load_session(settings.model_path)
    rows = [
        row
        for row in csv.DictReader(args.manifest.open(encoding="utf-8"))
        if row["split"] == "test"
    ]
    print(f"searching {len(rows)} test-split images for {len(SLOTS)} slots")

    chosen: dict[str, tuple[dict[str, str], dict[str, Any]]] = {}
    for slot in SLOTS:
        # Prefer rows of the class the slot wants, then fall back to everything:
        # the low-confidence and rejected slots can come from any class.
        preferred = [r for r in rows if r["canonical"] == slot.wants_class] if slot.wants_class else []
        order = preferred + [r for r in rows if r not in preferred]
        for row in order[: args.candidates]:
            path = args.interim / row["path"].replace("\\", "/")
            if not path.is_file():
                continue
            outcome = measure(path, runner, settings)
            if outcome and fits(slot, outcome):
                chosen[slot.name] = (row, outcome)
                break
        state = "ok" if slot.name in chosen else "NOT FILLED"
        print(f"  {slot.name:34} {state}")

    args.out.mkdir(parents=True, exist_ok=True)
    for existing in args.out.glob("*.jpg"):
        existing.unlink()

    lines = [
        "# คู่มือสาธิต",
        "",
        "**ไฟล์นี้ generate โดย `scripts/prepare_demo.py` ห้ามแก้ด้วยมือ**",
        "รัน script ใหม่หลังเปลี่ยนโมเดลหรือ threshold เพราะทุกตัวเลขข้างล่าง",
        "มาจากการวัด ไม่ได้มาจากความจำ",
        "",
        "ภาพอยู่ใน `demo/` และ **ไม่ถูก commit** — มาจากชุดข้อมูลวิจัยสาธารณะ",
        "ที่เงื่อนไขการเผยแพร่ซ้ำต่างกัน repository นี้ไม่มีเหตุผลที่จะถือภาพ",
        "ที่ตัวเองไม่ได้ถ่าย ที่มาของแต่ละภาพบันทึกไว้ที่นี่ จึงสร้างชุดใหม่ได้",
        "",
        "## ก่อนเริ่ม",
        "",
        "```bash",
        "cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000",
        "cd frontend && npm run dev",
        "```",
        "",
        "เปิด `http://localhost:5173/scan` กด **เลือกภาพใบชา** แล้วเลือกจาก",
        "โฟลเดอร์ `demo/` · กด **เตรียมใช้งานออฟไลน์** หนึ่งครั้งก่อนสาธิต",
        "เพื่อให้โมเดลและฐานความรู้ถูกแคชไว้",
        "",
        "## ลำดับการเล่น",
        "",
    ]

    for index, slot in enumerate(SLOTS, start=1):
        entry = chosen.get(slot.name)
        lines += [f"### {index}. {slot.headline}", ""]
        if entry is None:
            lines += [
                "**ไม่มีภาพในชุดทดสอบที่เข้าช่องนี้** script บอกตรง ๆ แทนที่จะ",
                "เอาภาพที่ไม่เข้าเกณฑ์มาใส่แทน รันใหม่หลังเปลี่ยนโมเดลหรือ threshold",
                "",
            ]
            continue

        row, outcome = entry
        source = args.interim / row["path"].replace("\\", "/")
        destination = args.out / f"{slot.name}.jpg"
        shutil.copy2(source, destination)

        lines += [f"ไฟล์: `demo/{destination.name}`", ""]
        if outcome["rejected"]:
            lines += [
                f"- ด่านคุณภาพ **ปฏิเสธ** ภาพนี้: `{outcome['reason']}` ค่าความเบลอ "
                f"**{outcome['blur_score']:.1f}** เทียบ threshold "
                f"{settings.blur_threshold}",
                f"- หน้าจอขึ้นว่า **{outcome['reason_th']}** และให้ถ่ายใหม่",
                "- พูดว่า: ด่านนี้มีอยู่เพราะการวินิจฉัยจากภาพที่อ่านไม่ออก",
                "  แย่กว่าการไม่วินิจฉัยเลย",
                "",
            ]
        else:
            lines += [
                f"- ทำนาย **{outcome['class_name']}** ที่ความเชื่อมั่น "
                f"**{outcome['confidence']:.2f}**"
                + ("  _(ต่ำกว่าเพดาน จึงปฏิเสธที่จะตั้งชื่อโรค)_"
                   if outcome["low_confidence"] else ""),
                f"- คำตัดสิน **{outcome['verdict']}** ความน่าจะเป็นใบไหม้ "
                f"{outcome['burn_likelihood']:.2f}",
                f"- ความรุนแรง **{outcome['level']}** "
                f"{100 * outcome['affected_pct']:.1f}% ของพื้นที่ใบ",
                f"- คำแนะนำจาก record `{outcome['advice']}` — "
                f"{outcome['disease_name_th']}",
                f"- ประมาณ {outcome['processing_ms']} ms บนเครื่องนี้",
                "",
            ]
        lines += [
            f"<sub>ที่มา: `{row['path']}` ({row['canonical']}, "
            f"{row['source']})</sub>",
            "",
        ]

    lines += _PHONE_SECTION.splitlines()
    lines += [
        "## ตัวเลขที่อ้างได้",
        "",
        "| | |",
        "|---|---|",
        "| คลังภาพ | 8,316 ภาพ ห้าคลาส แบ่ง 70/15/15 |",
        "| ความแม่นบนชุดทดสอบที่กันไว้ | **0.9871** macro-F1 **0.9873** |",
        "| ใบเป็นโรคถูกเรียกว่าปกติ | **0 จาก 584** |",
        "| ใบปกติถูกตั้งชื่อโรค | **0 จาก 215** |",
        "| specificity ของตัววิเคราะห์ใบไหม้ | **97.18%** บนภาพโรค 1,030 ภาพ |",
        "| โมเดลออฟไลน์ | ONNX fp32 16.8 MB รันในเบราว์เซอร์ |",
        "",
        "## ข้อจำกัดที่ต้องพูดเอง ก่อนมีคนถาม",
        "",
        "- **ใบที่ปกติดีถูกตั้งชื่อโรคได้ที่ความมั่นใจสูงมาก และนี่คือข้อที่",
        "  อันตรายที่สุดบนเวที** วัดบน iPhone XS เมื่อ 2026-10-21: ภาพมือกำยอดชา",
        "  สดเขียวสมบูรณ์ ได้ `brown_blight` ที่ **92.4%**",
        "  ตารางข้างบนบอกว่าใบปกติถูกตั้งชื่อโรค 0 จาก 215 **ตัวเลขนั้นจริงเฉพาะ",
        "  บนชุดทดสอบที่เป็นภาพโคลสอัพใบเดี่ยว** ภาพจริงที่มีหลายใบ มีมือ และมี",
        "  พุ่มชาเป็นฉากหลัง อยู่นอกการกระจายนั้น เบราว์เซอร์ไม่มีด่านแยกใบ",
        "  ทั้งเฟรมจึงถูกย่อเป็น 224x224 รวมมือและฉากหลังไปด้วย",
        "  **อย่าถ่ายพุ่มชาหรือกำใบโชว์บนเวที ใช้ภาพใบเดี่ยวจาก `demo/`**",
        "  และถ้ามีกรรมการถ่ายเอง ให้พูดข้อนี้ก่อนกดดูผล",
        "- **ภาพที่ไม่ใช่ใบชาก็ได้ชื่อโรคเหมือนกัน พูดข้อนี้ก่อนมีคนลอง**",
        "  วัดบน iPhone เมื่อ 2026-10-21: ภาพถ่ายหน้าจอโน้ตบุ๊กที่มีโค้ด ได้",
        "  `brown_blight` ที่ความมั่นใจ **76.8%** สูงกว่าเพดาน 0.60 จึงผ่าน",
        "  ตะแกรง `other_disease` ไปพร้อมคำแนะนำการเกษตรเต็มหน้า",
        "  สาเหตุสามอย่างประกอบกัน: ด่านคุณภาพวัดความเบลอกับแสง **ไม่ได้วัดว่า",
        "  ในภาพเป็นใบไม้** เบราว์เซอร์ไม่มีด่านแยกใบ และตัวจำแนกมีห้าคลาสปิด",
        "  จึงไม่มีทางปฏิเสธ **ทุกภาพถูกบังคับให้เป็นหนึ่งในห้าคลาสเสมอ**",
        "  ทางแก้คือ open-set rejection หรือตัวตรวจใบไม้ ซึ่งเป็นงานของโมเดล",
        "  ไม่ใช่การปรับ threshold **อย่ายื่นมือถือให้คนถ่ายอะไรก็ได้โดยไม่พูดข้อนี้**",
        "- **0.987 เป็นขอบบน ไม่ใช่ค่าประมาณความแม่นในสนาม** การแบ่งชุดสุ่ม",
        "  ภายในแต่ละคลาสและไม่ได้จัดกลุ่มตามครั้งที่ถ่าย ภาพใบเดียวกันหลายช็อต",
        "  จึงไปอยู่ได้ทั้งสองฝั่ง",
        "- **ไม่มีภาพใดในคลังนี้มาจากสิงห์ปาร์ค** ยังไม่เคยทดสอบบนไร่ที่สินค้านี้",
        "  ถูกสร้างขึ้นมาเพื่อมันเลย",
        "- **ไม่มีค่า sensitivity ของการตรวจใบไหม้ และเราจะไม่อ้างตัวเลขนั้น**",
        "  ไม่มีภาพใบไหม้ที่มีป้ายกำกับในแหล่งข้อมูลทั้งเก้าที่สำรวจ specificity",
        "  วัดได้ ส่วน sensitivity วัดไม่ได้ และ fixture สังเคราะห์ตัดสินแทนไม่ได้",
        "  เพราะมันถูกสร้างจากนิยามคุณลักษณะชุดเดียวกับที่มันทดสอบ",
        "- **ตัวจำแนกผิดได้แบบมั่นใจ** มีภาพทดสอบหนึ่งภาพผิดที่ความเชื่อมั่น",
        "  0.983 ซึ่งสูงกว่าเพดานใด ๆ ที่ใช้ได้จริง",
        "- ผลที่รันบนเครื่องผู้ใช้ถูกกำกับว่า `classifier_only` และ**ต่างจาก**",
        "  ผลจากเซิร์ฟเวอร์จริง ๆ เพราะเบราว์เซอร์ไม่แยกใบออกจากพื้น",
        "",
        "หลักฐานเต็มพร้อมคำสั่งที่ผลิตมัน: `docs/EVIDENCE.md`",
        "",
    ]

    args.doc.write_text("\n".join(lines), encoding="utf-8")
    filled = len(chosen)
    print(f"\nwrote {args.doc.relative_to(REPO)} and {filled} images to "
          f"{args.out.relative_to(REPO)}")
    if filled < len(SLOTS):
        print(f"WARNING: {len(SLOTS) - filled} slot(s) could not be filled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
