"""Synthetic dataset fixtures, so every ingest test runs offline."""

import io
import json
import zipfile
from pathlib import Path

import numpy
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from PIL import Image

HF_METADATA_KEY = "huggingface"


_BASE_SIZE = (512, 512)


def leaf_image(*, size: tuple[int, int] = (64, 64), seed: int = 0) -> Image.Image:
    """A textured green patch, rendered at a fixed base size then resized.

    The blotches scale with the canvas because a perceptual hash downsamples to
    32x32 before its DCT: speckles a few pixels wide vanish, and two different
    seeds would then hash identically, making a dedup test prove nothing.

    Rendering at one base size and resizing is what makes a smaller copy the
    same photograph rather than a differently textured one.
    """
    rng = numpy.random.default_rng(seed)
    width, height = _BASE_SIZE
    pixels = numpy.full((height, width, 3), (34, 139, 34), dtype=numpy.uint8)
    block = width // 8
    for y, x in rng.integers(0, width - block, size=(14, 2)):
        pixels[y : y + block, x : x + block] = rng.integers(40, 210, size=3)
    image = Image.fromarray(pixels, mode="RGB")
    return image if size == _BASE_SIZE else image.resize(size, Image.LANCZOS)


def write_leaf_photo(
    path, *, size: tuple[int, int] = (512, 512), quality: int = 95, seed: int = 0
) -> Path:
    """Save a deterministic leaf photo as JPEG. Same seed means same photograph."""
    leaf_image(size=size, seed=seed).save(path, format="JPEG", quality=quality)
    return Path(path)


def _encode(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def green_png(**kwargs) -> bytes:
    return _encode(leaf_image(**kwargs), "PNG")


def green_jpeg(**kwargs) -> bytes:
    return _encode(leaf_image(**kwargs), "JPEG")


def make_parquet(*, rows, label_names, path) -> Path:
    """Write an HF-shaped parquet: image struct, int label, features in metadata."""
    table = pa.table(
        {
            "image": [{"bytes": payload, "path": None} for payload, _ in rows],
            "label": pa.array([label for _, label in rows], type=pa.int64()),
        }
    )
    features = {
        "info": {
            "features": {
                "image": {"_type": "Image"},
                "label": {"names": list(label_names), "_type": "ClassLabel"},
            }
        }
    }
    table = table.replace_schema_metadata({HF_METADATA_KEY: json.dumps(features)})
    pq.write_table(table, path)
    return Path(path)


def make_yolo_zip(*, entries, names, path, extra_members=()) -> Path:
    """Write a Roboflow-shaped YOLO archive.

    entries are (stem, image_bytes, class_ids); class_ids of None writes no
    label file at all, and an empty tuple writes an empty one.
    """
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("data.yaml", yaml.safe_dump({"names": list(names), "nc": len(names)}))
        for stem, payload, class_ids in entries:
            archive.writestr(f"train/images/{stem}.jpg", payload)
            if class_ids is not None:
                archive.writestr(
                    f"train/labels/{stem}.txt",
                    "".join(f"{cid} 0.5 0.5 0.2 0.2\n" for cid in class_ids),
                )
        for member, payload in extra_members:
            archive.writestr(member, payload)
    return Path(path)
