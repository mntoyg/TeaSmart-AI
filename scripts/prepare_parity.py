"""Stage the 50-image parity check from docs/DESIGN.md section 8.4.

Copies a fixed, evenly spaced sample of the test split into
`frontend/public/parity/` and records what the Python pipeline makes of each
one. A page-side script then runs onnxruntime-web over the same files and
compares - the browser half cannot be done from Python, so this prepares it and
publishes the answer sheet.

Evenly spaced rather than random, so the number means the same thing on every
machine and before and after a re-export. Both the copies and the answer sheet
are gitignored: these are corpus images.

The acceptance bar, from the spec: top-1 must agree on every image, and no
class probability may differ by more than 0.05.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.classify import CLASS_ORDER, load_session, preprocess  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=REPO / "data/processed/manifest.csv")
    parser.add_argument("--interim", type=Path, default=REPO / "data/interim")
    parser.add_argument("--out", type=Path, default=REPO / "frontend/public/parity")
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.model_path.is_file():
        print(f"no model at {settings.model_path}")
        return 1

    rows = [
        row
        for row in csv.DictReader(args.manifest.open(encoding="utf-8"))
        if row["split"] == "test"
    ]
    step = max(1, len(rows) // args.count)
    sample = rows[::step][: args.count]
    print(f"{len(sample)} images, every {step}th row of the test split")

    runner = load_session(settings.model_path)
    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.iterdir():
        if stale.is_file():
            stale.unlink()

    entries = []
    for index, row in enumerate(sample):
        source = args.interim / row["path"].replace("\\", "/")
        name = f"{index:02d}{source.suffix.lower()}"
        shutil.copy2(source, args.out / name)

        with Image.open(source) as image:
            image.load()
            rgb = np.asarray(image.convert("RGB"))

        logits = np.asarray(runner(preprocess(rgb)), dtype=np.float32).reshape(-1)
        shifted = logits - logits.max()
        exponentiated = np.exp(shifted)
        probabilities = exponentiated / exponentiated.sum()

        entries.append(
            {
                "file": name,
                "canonical": row["canonical"],
                "width": int(rgb.shape[1]),
                "height": int(rgb.shape[0]),
                "probabilities": [round(float(value), 6) for value in probabilities],
                "top1": CLASS_ORDER[int(probabilities.argmax())],
            }
        )

    (args.out / "answers.json").write_text(
        json.dumps(
            {
                "bound": 0.05,
                "class_order": list(CLASS_ORDER),
                "model": settings.model_path.name,
                "preprocessing": "PIL bilinear, 224x224, ImageNet normalisation",
                "entries": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(entries)} images and answers.json to "
          f"{args.out.relative_to(REPO)}")
    print("now run the page-side half against /parity/answers.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
