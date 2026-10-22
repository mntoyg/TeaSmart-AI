"""Measure the plant fraction over the whole corpus, to set one threshold.

The browser has no leaf segmentation, so a photograph of a hand, a wall or a
computer screen is forced into one of five disease classes and comes back
confident: a laptop screen measured 76.8% `brown_blight`. The gate that stops
that needs a floor on how much of the frame is plant at all.

The floor cannot be chosen by eye, and this script exists because of what goes
wrong if it is. **A severely diseased leaf is brown almost edge to edge**, so it
carries a *lower* plant fraction than a hand holding a healthy shoot. A
threshold set from a few photographs would refuse the case the product exists
for, silently, with every test still passing. So the floor is read off the
corpus: below the lowest fraction a real labelled leaf achieves.

    ./backend/.venv/Scripts/python.exe scripts/measure_leaf_fraction.py

It writes a CSV of every measurement next to the manifest, prints the
distribution per class and the candidate floors, and refuses to recommend a
threshold it has not measured the cost of.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import numpy
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.core.config import Settings  # noqa: E402
from app.services.segment import segment_leaf, vegetation_fraction  # noqa: E402
from app.services.segment import _green_mask  # noqa: E402

MANIFEST = REPO / "data" / "processed" / "manifest.csv"
INTERIM = REPO / "data" / "interim"
OUT = REPO / "data" / "artifacts" / "leaf_fraction.csv"
# The classes whose photographs are of damaged leaves. The floor has to clear
# these, not the healthy ones: brown is what costs plant fraction.
DISEASED = ("grey_blight", "brown_blight", "algal_spot", "other_disease")


def measure(limit: int | None = None) -> list[dict[str, str | float]]:
    settings = Settings()
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    if limit:
        rows = rows[:limit]
    measured: list[dict[str, str | float]] = []
    for index, row in enumerate(rows, start=1):
        path = INTERIM / row["path"]
        with Image.open(path) as opened:
            rgb = numpy.asarray(ImageOps.exif_transpose(opened).convert("RGB"))
        # Stage 2 as well, because the same rule feeds it. If the mask is too
        # weak to find a leaf, `fallback` is how often severity and the lesion
        # search are running on the whole frame instead of on a leaf, and that
        # is worth knowing before any threshold is set on top of it.
        leaf = segment_leaf(rgb, settings)
        measured.append(
            {
                "path": row["path"],
                "canonical": row["canonical"],
                "source": row["source"],
                "split": row["split"],
                "fraction": vegetation_fraction(rgb, settings),
                "stage2_fraction": float(_green_mask(rgb, settings).mean()),
                "fallback": int(leaf.fallback),
            }
        )
        if index % 500 == 0:
            print(f"  {index}/{len(rows)}", flush=True)
    return measured


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))]


def report(measured: list[dict[str, str | float]]) -> float:
    fractions = [float(row["fraction"]) for row in measured]
    print(f"\n{len(measured)} images measured\n")
    print(f"{'class':<16}{'n':>6}{'min':>9}{'p0.1':>9}{'p1':>9}{'p5':>9}{'median':>9}")
    for canonical in sorted({str(row['canonical']) for row in measured}):
        values = [float(r["fraction"]) for r in measured if r["canonical"] == canonical]
        print(
            f"{canonical:<16}{len(values):>6}{min(values):>9.4f}"
            f"{_quantile(values, 0.001):>9.4f}{_quantile(values, 0.01):>9.4f}"
            f"{_quantile(values, 0.05):>9.4f}{statistics.median(values):>9.4f}"
        )
    print(
        f"\n{'ALL':<16}{len(fractions):>6}{min(fractions):>9.4f}"
        f"{_quantile(fractions, 0.001):>9.4f}{_quantile(fractions, 0.01):>9.4f}"
        f"{_quantile(fractions, 0.05):>9.4f}{statistics.median(fractions):>9.4f}"
    )

    diseased = [float(r["fraction"]) for r in measured if r["canonical"] in DISEASED]
    print(f"\nlowest fraction on a labelled leaf:          {min(fractions):.4f}")
    print(f"lowest on a diseased leaf ({len(diseased)} images):  {min(diseased):.4f}")

    stage2 = [float(row["stage2_fraction"]) for row in measured]
    zeros = sum(1 for value in stage2 if value == 0.0)
    print(
        f"\nstage 2's absolute rule on the same images: min {min(stage2):.4f} "
        f"median {statistics.median(stage2):.4f}, {zeros} of {len(stage2)} at exactly zero"
    )

    print("\nstage 2 falling back to the whole frame, by source:")
    print(f"{'source':<18}{'n':>6}{'fallback':>10}{'rate':>9}{'median frac':>13}")
    for source in sorted({str(row["source"]) for row in measured}):
        group = [row for row in measured if row["source"] == source]
        fell = sum(int(row["fallback"]) for row in group)
        median = statistics.median(float(row["fraction"]) for row in group)
        print(f"{source:<18}{len(group):>6}{fell:>10}{fell / len(group):>8.1%}{median:>13.4f}")
    fell_total = sum(int(row["fallback"]) for row in measured)
    print(f"{'ALL':<18}{len(measured):>6}{fell_total:>10}{fell_total / len(measured):>8.1%}")

    print("\ncost of each candidate floor, in real leaves it would refuse:")
    print(f"{'floor':>8}{'refused':>10}{'of corpus':>12}{'diseased':>10}")
    for floor in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10):
        refused = sum(1 for value in fractions if value < floor)
        refused_ill = sum(1 for value in diseased if value < floor)
        print(f"{floor:>8.3f}{refused:>10}{refused / len(fractions):>11.2%}{refused_ill:>10}")
    return min(fractions)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="measure only the first N rows, for a smoke run")
    arguments = parser.parse_args()

    measured = measure(arguments.limit)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "canonical", "source", "split", "fraction", "stage2_fraction", "fallback"])
        writer.writeheader()
        writer.writerows(measured)
    report(measured)
    print(f"\nevery measurement written to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
