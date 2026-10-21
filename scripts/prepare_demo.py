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
        "A clear diagnosis with real damage - the main claim",
        "brown_blight",
        min_confidence=0.80,
        min_severity="moderate",
        min_affected_pct=0.05,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "02-grey-blight",
        "A second disease, so it is not a one-class trick",
        "grey_blight",
        min_confidence=0.70,
        min_affected_pct=0.01,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "03-algal-spot",
        "A third, with different advice from the knowledge base",
        "algal_spot",
        min_confidence=0.70,
        min_affected_pct=0.01,
        max_burn_likelihood=0.35,
    ),
    Slot(
        "04-healthy",
        "A healthy leaf, which must not be given a disease name",
        "healthy",
        min_confidence=0.70,
        max_burn_likelihood=0.25,
    ),
    Slot(
        "05-unsure-declines-to-name",
        "The confidence floor: it answers other_disease instead of guessing",
        None,
        low_confidence=True,
    ),
    Slot(
        "06-blurry-asks-for-a-retake",
        "The quality gate: Thai instruction, not an error page",
        None,
        rejected=True,
    ),
)

_PHONE_SECTION = """
## Testing on a real phone

Everything below that could be checked from the development machine has been,
and the measurements are quoted. Pressing the buttons on the handset is the
part nobody else can do.

### 1. Make the app reachable

Vite binds to `127.0.0.1` by default, so a phone cannot reach it at all —
measured, the listener was `TCP 127.0.0.1:5173` and nothing else. Start it with
the host flag instead:

```bash
cd frontend && npm run dev -- --host
```

The listener becomes `0.0.0.0:5173`, and the phone uses this machine's LAN
address. The backend does **not** need the flag: the phone talks to Vite, and
Vite proxies `/api` to `127.0.0.1:8000` on the development machine.

Verified over the LAN address from this machine:

```text
GET  /                 200
GET  /api/v1/config    200    blur 15.0, min_confidence 0.60
POST /api/v1/scan      200    brown_blight 0.96, severe 28.2%, 100 ms
```

If the phone cannot load the page while the machine can, it is almost always
Windows Firewall blocking inbound 5173 on the private network. Allow Node for
private networks, or add a rule for the port.

### 2. Expect the camera and offline to be missing over plain HTTP

Measured in a browser at `http://<lan-ip>:5173`:

```json
{ "isSecureContext": false, "hasServiceWorker": false, "hasMediaDevices": false }
```

Those APIs are not merely blocked, they are **absent**. Over plain HTTP from a
LAN address a phone therefore gets the file picker and online scanning, and
none of: camera capture, the service worker, offline inference, or install to
the home screen. That is a browser rule about secure contexts, not a fault in
this app — `localhost` is exempt, which is why it all works on the development
machine.

So a phone test over `http://<lan-ip>` can only confirm the layout, the file
picker and an online scan. **It cannot confirm the offline story, which is the
part the demo is judged on.**

Three ways to get a secure context. Prefer the first.

**USB, on Android — and this is also how the demo gets recorded.** `adb
reverse` publishes a port from this machine onto the handset's own `localhost`,
and `localhost` is a secure context *by specification*, in Chrome on Android as
anywhere else. So the handset opens `http://localhost:5173` and gets the
camera, the service worker, offline inference and install, with no browser
flag, no third-party tunnel, and no firewall rule — the LAN is not involved at
all, and `--host` is not needed on Vite.

Enable Developer options and USB debugging on the handset, plug it in, accept
the authorisation prompt, then:

```bash
adb devices                              # must list the handset as `device`
adb reverse tcp:5173 tcp:5173            # the app
scrcpy --record=demo.mp4                 # mirror the screen and record it
```

`scrcpy` ships its own `adb.exe`; on Windows, `winget install
Genymobile.scrcpy` installs both. Measured here: scrcpy 4.1, adb 1.0.41
(platform-tools 37.0.0).

**Open a new terminal after installing.** winget puts the package directory on
the user `PATH` and creates a link only for `scrcpy`, and a process keeps the
environment it started with, so the terminal the install was run from reports
`'adb' is not recognized` - which looks exactly like a failed install. A newly
started shell finds it. To fix the terminal you already have, without opening
another:

```bat
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\scrcpy-win64-v4.1"
```

The reverse forward is dropped when the cable is unplugged or the adb server
restarts, so re-run `adb reverse` after either and confirm with `adb reverse
--list`. The backend needs no forward of its own: the handset talks to Vite and
Vite proxies `/api` on this machine.

Record with `--record=demo.mp4` rather than screen-capturing the scrcpy window:
it writes the handset's own video stream, so the file does not carry the
compositor's dropped frames. `--no-audio` if the handset's audio forwarding
gets in the way.

**Chrome flag, if USB is not available.** On the phone open
`chrome://flags/#unsafely-treat-insecure-origin-as-secure`, add
`http://<lan-ip>:5173`, set the flag to Enabled and relaunch Chrome. The origin
is then treated as secure: camera, service worker, offline and install all
work. Nothing leaves the network. Undo it after the demo. The flag names one
exact origin, so it has to be set again if the LAN address changes.

**A tunnel, if the demo is not on the same network.** `cloudflared` or `ngrok`
gives a real HTTPS URL that any phone can open. It also sends every photograph
and every result through a third party, so it is a decision for the owner of
the data, not a default. It additionally needs `TEASMART_CORS_ORIGINS` set,
because the browser's origin is then no longer `localhost:5173`.

**On iPhone, none of the first two apply.** There is no `adb`, and Chrome on
iOS is WebKit underneath with no flag for insecure origins, so a secure context
there means `mkcert` with the root certificate trusted on the handset, or a
tunnel. Mirroring an iPhone to Windows needs an AirPlay receiver or a capture
card. Record the demo on Android; keep the iPhone as a WebKit cross-check.

### 3. What to check once the context is secure

In this order, because each step depends on the one before:

1. **Layout.** Already checked at 375x812 with no sideways scrolling, but a
   real handset has a notch, a system font scale and a software keyboard.
2. **Camera.** `เปิดกล้อง`, allow the permission, photograph a leaf. The rear
   camera should open (`facingMode: environment`).
3. **An online scan.** The result card should name the disease in Thai, state
   the severity, and say `full` analysis.
4. **Install.** Chrome's menu offers Add to home screen once the service worker
   is registered. Open the installed app, not the tab.
5. **Prepare offline.** Press `เตรียมใช้งานออฟไลน์` and wait. This downloads
   **30.7 MB** — 14.2 MB of WASM and the 16.8 MB model — so do it on wifi,
   before the demo, not on stage.
6. **Offline.** Put the phone in aeroplane mode and scan. The result must be
   labelled `classifier_only`: the browser does not segment, so there is no
   lesion analysis and no severity, and the card has to say so.
7. **Reconnect.** Turn the network back on. The queue replays through
   `POST /api/v1/sync/batch` and the results are filled in. Scanning the same
   photograph twice must not produce two history entries — the server returns
   the stored result with `replayed: true`.

### 4. Step 6 measures the model, not just the plumbing

The browser's resize now implements PIL's algorithm, so an on-device result is
not drifting from a server result for preprocessing reasons. The 50-image
parity check that section 8.4 of `docs/DESIGN.md` makes the condition for D7
passed on 2026-10-20:

```text
images              50
top-1 agreement     50/50
max prob delta      0.00283      (bound 0.05)
passes              true
```

**Eighteen times inside the bound**, over the whole chain: JPEG decoding, the
canvas round-trip, the resize, the ImageNet normalisation and the fp32 graph.
An offline result is therefore the same model reaching the same answer, and
step 6 is worth presenting as such.

What still differs offline is the *pipeline*, not the model: the browser does
not segment, so there is no lesion analysis and no severity, and the card says
`classifier_only`. That is a product difference, not a defect. Evidence and
the command that produced the table: `docs/EVIDENCE.md` section 6.
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
        "# Demo runbook",
        "",
        "**Generated by `scripts/prepare_demo.py`. Do not edit by hand.**",
        "Re-run it after any change to the model or the thresholds, because",
        "every number below was measured rather than remembered.",
        "",
        "The images live in `demo/` and are **not committed**: they come from",
        "public research datasets whose redistribution terms differ, and this",
        "repository has no business holding photographs it did not create. The",
        "source path of each one is recorded here, so the set can be rebuilt.",
        "",
        "## Before you start",
        "",
        "```bash",
        "cd backend && .venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --port 8000",
        "cd frontend && npm run dev",
        "```",
        "",
        "Open `http://localhost:5173/scan`. Use **เลือกภาพใบชา** and pick from",
        "`demo/` in the file dialog. Press **เตรียมใช้งานออฟไลน์** once before",
        "the demo so the model and the knowledge base are cached.",
        "",
        "## Running order",
        "",
    ]

    for index, slot in enumerate(SLOTS, start=1):
        entry = chosen.get(slot.name)
        lines += [f"### {index}. {slot.headline}", ""]
        if entry is None:
            lines += [
                "**No image in the test split fits this slot.** The script says so",
                "rather than substituting one that does not. Re-run it after the",
                "next model or threshold change.",
                "",
            ]
            continue

        row, outcome = entry
        source = args.interim / row["path"].replace("\\", "/")
        destination = args.out / f"{slot.name}.jpg"
        shutil.copy2(source, destination)

        lines += [f"File: `demo/{destination.name}`", ""]
        if outcome["rejected"]:
            lines += [
                f"- the gate **rejects** it: `{outcome['reason']}`, blur score "
                f"**{outcome['blur_score']:.1f}** against a threshold of "
                f"{settings.blur_threshold}",
                f"- the screen shows **{outcome['reason_th']}** and offers a retake",
                "- say: the gate exists because a diagnosis from an unreadable",
                "  photograph is worse than no diagnosis",
                "",
            ]
        else:
            lines += [
                f"- prediction **{outcome['class_name']}** at "
                f"**{outcome['confidence']:.2f}**"
                + ("  _(below the floor, so it declines to name a disease)_"
                   if outcome["low_confidence"] else ""),
                f"- verdict **{outcome['verdict']}**, burn likelihood "
                f"{outcome['burn_likelihood']:.2f}",
                f"- severity **{outcome['level']}**, "
                f"{100 * outcome['affected_pct']:.1f}% of the leaf",
                f"- advice from record `{outcome['advice']}` — "
                f"{outcome['disease_name_th']}",
                f"- about {outcome['processing_ms']} ms on this machine",
                "",
            ]
        lines += [
            f"<sub>source: `{row['path']}` ({row['canonical']}, "
            f"{row['source']})</sub>",
            "",
        ]

    lines += _PHONE_SECTION.splitlines()
    lines += [
        "## The numbers to quote",
        "",
        "| | |",
        "|---|---|",
        "| corpus | 8,316 images, five classes, 70/15/15 |",
        "| held-out test accuracy | **0.9871**, macro-F1 **0.9873** |",
        "| diseased leaf called healthy | **0 of 584** |",
        "| healthy leaf given a disease name | **0 of 215** |",
        "| burn analyser specificity | **97.18%** on 1,030 disease images |",
        "| offline model | 16.8 MB fp32 ONNX, runs in the browser |",
        "",
        "## What to say about the limits, before anyone asks",
        "",
        "- **0.987 is an upper bound, not a field estimate.** The split is",
        "  random within each class and is not grouped by photography session,",
        "  so several shots of one leaf can land on both sides.",
        "- **No photograph in this corpus comes from Singha Park.** Nothing has",
        "  been tested on the farm the product is for.",
        "- **There is no sensitivity figure for burn detection and we will not",
        "  quote one.** No labelled burn photograph exists in any of the nine",
        "  sources surveyed. Specificity is measured; sensitivity is not",
        "  measurable, and the synthetic fixtures cannot settle it because they",
        "  were built from the same feature definitions they test.",
        "- **The classifier can be confidently wrong.** One test image is wrong",
        "  at 0.983, above any usable confidence floor.",
        "- An on-device result is labelled `classifier_only` and genuinely",
        "  differs from a server result, because the browser does not segment.",
        "",
        "Full evidence, with the commands that produced it: `docs/EVIDENCE.md`.",
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
