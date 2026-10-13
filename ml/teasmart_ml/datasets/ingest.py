"""Normalise every source into data/interim/<source_id>/<canonical>/.

Nothing downstream reads the raw archives. Each source has its own idea of what
a label is - a ClassLabel index in a parquet column, a YOLO detection file
beside the image - and this module is the only place that knows the difference.

Both paths generate their own output filenames. A member path from a downloaded
archive never reaches the filesystem, so a traversal entry has nowhere to land.
"""

import io
import json
import shutil
import zipfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
import yaml
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from teasmart_ml.classes import to_canonical
from teasmart_ml.datasets.sources import (
    HFParquetSource,
    LabelDriftError,
    MendeleyZipSource,
)

_JPEG_QUALITY = 95
_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
_PARQUET_BATCH = 64
_MARKER = ".teasmart-interim"


class InterimRootError(RuntimeError):
    """The interim root is not ours to clear."""


@dataclass(frozen=True)
class IngestReport:
    source_id: str
    written: int
    skipped_corrupt: int
    skipped_unlabelled: int
    skipped_ambiguous: int
    per_class: Mapping[str, int]


def embedded_parquet_labels(path: Path) -> tuple[str, ...] | None:
    """The ClassLabel names HuggingFace stores in the parquet schema metadata."""
    metadata = pq.ParquetFile(path).schema_arrow.metadata or {}
    raw = metadata.get(b"huggingface")
    if raw is None:
        return None
    features = json.loads(raw).get("info", {}).get("features", {})
    names = features.get("label", {}).get("names")
    return tuple(names) if names else None


def _verify_labels(
    source_id: str, found: Sequence[str] | None, expected: Sequence[str]
) -> None:
    """Fail closed. An unverifiable label order is as dangerous as a wrong one.

    If a source reorders its classes, every label in it is wrong together, and
    the model trained on it would name the wrong disease with full confidence.
    """
    if found is None:
        raise LabelDriftError(
            f"{source_id}: no embedded label names, so the registry order "
            f"cannot be verified"
        )
    if tuple(found) != tuple(expected):
        raise LabelDriftError(
            f"{source_id}: embedded labels {tuple(found)} do not match the "
            f"registry {tuple(expected)}"
        )


def _reset(target: Path) -> None:
    """Clear this output folder, which is what makes a second run idempotent.

    A marker file in the interim root is required before anything is removed. A
    mistyped --interim pointing at a directory that happens to contain a folder
    named after a source would otherwise have it deleted without a word.
    """
    root = target.parent
    marker = root / _MARKER
    if root.exists() and any(root.iterdir()) and not marker.exists():
        raise InterimRootError(
            f"{root} is not empty and has no {_MARKER} marker; refusing to clear "
            f"{target}. Point --interim at a new directory, or add the marker if "
            f"this really is a TeaSmart interim tree."
        )
    root.mkdir(parents=True, exist_ok=True)
    marker.touch()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)


def _write_jpeg(payload: bytes, dest: Path) -> bool:
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            rgb = opened.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, DecompressionBombError):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dest, format="JPEG", quality=_JPEG_QUALITY)
    return True


def ingest_parquet_source(
    source: HFParquetSource, files: Sequence[Path], interim_root: Path
) -> IngestReport:
    target = Path(interim_root) / source.source_id
    _reset(target)
    per_class: Counter[str] = Counter()
    written = corrupt = unlabelled = index = 0

    for file in files:
        _verify_labels(
            source.source_id, embedded_parquet_labels(file), source.label_names
        )
        # Streamed in batches: one of these files holds 390MB of image bytes, and
        # reading the column whole would hold all of it in Python at once.
        reader = pq.ParquetFile(file)
        for batch in reader.iter_batches(
            batch_size=_PARQUET_BATCH, columns=["image", "label"]
        ):
            payloads = batch.column("image").to_pylist()
            labels = batch.column("label").to_pylist()
            for payload, label in zip(payloads, labels):
                index += 1
                # HuggingFace writes -1 for "no label", and Python would index
                # that as the LAST class, with nothing to show anything was wrong.
                if label is None or not 0 <= label < len(source.label_names):
                    unlabelled += 1
                    continue
                canonical = to_canonical(source.label_names[label])
                data = payload["bytes"] if isinstance(payload, dict) else payload
                dest = target / canonical / f"{source.source_id}-{index:06d}.jpg"
                if data is not None and _write_jpeg(data, dest):
                    written += 1
                    per_class[canonical] += 1
                else:
                    corrupt += 1

    return IngestReport(
        source.source_id, written, corrupt, unlabelled, 0, dict(per_class)
    )


def _yolo_class_names(archive: zipfile.ZipFile) -> tuple[str, ...] | None:
    for member in archive.namelist():
        if Path(member).name == "data.yaml":
            names = yaml.safe_load(archive.read(member)).get("names")
            return tuple(names) if names else None
    return None


def _class_ids(body: bytes) -> tuple[int, ...]:
    """The class column of a YOLO label file, ignoring unparseable lines."""
    ids = []
    for line in body.decode("utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            ids.append(int(parts[0]))
        except ValueError:
            continue
    return tuple(ids)


def ingest_yolo_zip_source(
    source: MendeleyZipSource, archive_path: Path, interim_root: Path
) -> IngestReport:
    target = Path(interim_root) / source.source_id
    _reset(target)
    per_class: Counter[str] = Counter()
    written = corrupt = unlabelled = ambiguous = index = 0

    with zipfile.ZipFile(archive_path) as archive:
        names = _yolo_class_names(archive)
        _verify_labels(source.source_id, names, source.label_names)
        # Keyed by split directory as well as stem. Matching on the bare stem
        # attaches the boxes of one split to the image of another; the real
        # archive escapes this only because Roboflow appends a hash to every
        # filename, and two disabled archives are one flag away from ingestion.
        labels_by_key = {
            (member.split("/labels/", 1)[0], Path(member).stem): member
            for member in archive.namelist()
            if "/labels/" in member and member.endswith(".txt")
        }

        for member in archive.namelist():
            if (
                "/images/" not in member
                or Path(member).suffix.lower() not in _IMAGE_SUFFIXES
            ):
                continue
            index += 1
            label_member = labels_by_key.get(
                (member.split("/images/", 1)[0], Path(member).stem)
            )
            if label_member is None:
                unlabelled += 1
                continue
            class_ids = set(_class_ids(archive.read(label_member)))
            if not class_ids:
                unlabelled += 1
                continue
            # Two diseases boxed on one leaf has no single classification target,
            # and an id outside data.yaml cannot be resolved at all. Picking one
            # would invent a label the annotator never gave.
            if len(class_ids) != 1 or not all(
                0 <= cid < len(names) for cid in class_ids
            ):
                ambiguous += 1
                continue
            canonical = to_canonical(names[class_ids.pop()])
            dest = target / canonical / f"{source.source_id}-{index:06d}.jpg"
            if _write_jpeg(archive.read(member), dest):
                written += 1
                per_class[canonical] += 1
            else:
                corrupt += 1

    return IngestReport(
        source.source_id, written, corrupt, unlabelled, ambiguous, dict(per_class)
    )
