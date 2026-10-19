"""The manifest: one row per usable image, with its class, source and split.

This file is the contract between data preparation and training. Nothing
downstream reads the raw archives or the interim tree directly, so every claim
about the corpus can be checked against one CSV.

Duplicates are collapsed before the split, not after. Doing it the other way
leaves the same photograph on both sides of the train and test boundary, which
inflates every reported figure in a way no later metric can reveal.
"""

import csv
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy
from PIL import Image

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.datasets.dedup import group_duplicates, phash_hex
from teasmart_ml.datasets.sources import SOURCES

# path is relative to the interim root the manifest was built from, so the
# file still resolves on another machine, checkout or container.
HEADER = ("path", "canonical", "source", "phash", "width", "height", "split")
SPLITS = ("train", "val", "test")
DEFAULT_RATIOS = (0.70, 0.15, 0.15)


class UnknownCanonicalError(ValueError):
    """A class folder in the interim tree is not a canonical class."""


class UnknownSourceError(ValueError):
    """A source folder in the interim tree is not in the registry."""


@dataclass(frozen=True)
class Manifest:
    """The rows, plus what was thrown away reaching them.

    The counts travel with the rows because the committed dataset summary has to
    report them, and recomputing would mean hashing twelve thousand images twice.
    """

    rows: tuple["ManifestRow", ...]
    collapsed_duplicates: int
    conflicting_groups: int


@dataclass(frozen=True)
class ManifestRow:
    path: str
    canonical: str
    source: str
    phash: str
    width: int
    height: int
    split: str


def _split_sizes(count: int, ratios: Sequence[float]) -> tuple[int, int, int]:
    """How many of count images go to train, val and test.

    A class with only a handful of images still gets one in every split: the
    plain ratio rounds validation and test to zero below seven images, which
    would drop that class out of every metric without saying so.
    """
    if count <= 1:
        return count, 0, 0
    if count == 2:
        return 1, 1, 0
    validation = max(1, int(count * ratios[1]))
    test = max(1, int(count * ratios[2]))
    return count - validation - test, validation, test


def build_manifest(
    interim_root: Path,
    *,
    seed: int = 42,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
) -> Manifest:
    """Deduplicate the interim tree, then split each class independently."""
    interim_root = Path(interim_root)
    images = sorted(interim_root.rglob("*.jpg"))
    # to_canonical guards the ingest, but this file is the contract training
    # reads. A stale or renamed source folder left in the interim tree used to be
    # picked up silently under whatever its folder happened to be called.
    for path in images:
        if path.parent.name not in CANONICAL_CLASSES:
            raise UnknownCanonicalError(
                f"{path.parent} is not one of {CANONICAL_CLASSES}"
            )
        if path.parent.parent.name not in SOURCES:
            raise UnknownSourceError(f"{path.parent.parent} is not a known source")
    groups = group_duplicates(images)

    by_class: dict[str, list[Path]] = defaultdict(list)
    collapsed = 0
    conflicting = 0
    for group in groups:
        collapsed += len(group) - 1
        classes = {path.parent.name for path in group}
        if len(classes) > 1:
            # One photograph carrying two different labels across sources cannot
            # be resolved by keeping whichever copy sorts first: that trains the
            # model on a label no annotator agreed with.
            conflicting += 1
            continue
        by_class[group[0].parent.name].append(group[0])

    rows: list[ManifestRow] = []
    rng = numpy.random.default_rng(seed)
    for canonical in sorted(by_class):
        paths = sorted(by_class[canonical])
        order = rng.permutation(len(paths))
        shuffled = [paths[index] for index in order]
        train, validation, test = _split_sizes(len(shuffled), ratios)
        assignment = (
            ["train"] * train + ["val"] * validation + ["test"] * test
        )
        for path, split in zip(shuffled, assignment, strict=False):
            with Image.open(path) as image:
                width, height = image.width, image.height
            rows.append(
                ManifestRow(
                    path=str(path.relative_to(interim_root)),
                    canonical=canonical,
                    source=path.parent.parent.name,
                    phash=phash_hex(path),
                    width=width,
                    height=height,
                    split=split,
                )
            )
    return Manifest(tuple(rows), collapsed, conflicting)


def write_manifest(rows: Sequence[ManifestRow], out_csv: Path) -> None:
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HEADER))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def summarise(rows: Sequence[ManifestRow]) -> Mapping[str, Mapping[str, int]]:
    """Counts per class per split, with every split present even at zero."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[row.canonical][row.split] += 1
    return {
        canonical: {split: per_split.get(split, 0) for split in SPLITS}
        for canonical, per_split in sorted(counts.items())
    }
