"""Synthetic dataset fixtures, so every ingest test runs offline."""

import hashlib
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
_GRID = 8


def leaf_image(*, size: tuple[int, int] = (64, 64), seed: int = 0) -> Image.Image:
    """A seeded blocky green texture, rendered at a base size then resized.

    The pattern covers the whole canvas on purpose. An earlier version drew a
    few blotches on a flat green field, which left 78% of any two images
    identical: different seeds then measured a pixel difference of 7.7 of 255,
    under the threshold that defines a duplicate, so the fixtures deduped into
    each other and the split tests measured nothing.

    Rendering at one base size and resizing is what makes a smaller copy the
    same photograph rather than a differently textured one.
    """
    rng = numpy.random.default_rng(seed)
    width, height = _BASE_SIZE
    block = width // _GRID
    cells = numpy.empty((_GRID, _GRID, 3), dtype=numpy.uint8)
    cells[..., 0] = rng.integers(20, 80, size=(_GRID, _GRID))
    cells[..., 1] = rng.integers(70, 200, size=(_GRID, _GRID))
    cells[..., 2] = rng.integers(20, 80, size=(_GRID, _GRID))
    pixels = numpy.repeat(numpy.repeat(cells, block, axis=0), block, axis=1)
    image = Image.fromarray(pixels[:height, :width], mode="RGB")
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
        for entry in entries:
            stem, payload, class_ids = entry[:3]
            split_dir = entry[3] if len(entry) > 3 else "train"
            archive.writestr(f"{split_dir}/images/{stem}.jpg", payload)
            if class_ids is not None:
                archive.writestr(
                    f"{split_dir}/labels/{stem}.txt",
                    "".join(f"{cid} 0.5 0.5 0.2 0.2\n" for cid in class_ids),
                )
        for member, payload in extra_members:
            archive.writestr(member, payload)
    return Path(path)


def _seed_for(key: str) -> int:
    """A stable seed per key, so the same key always renders the same photo."""
    return int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)


def distinct(count: int, *, size: int = 256) -> list[tuple[str, int]]:
    return [(f"img{index}", size) for index in range(count)]


def build_interim(root, spec, *, source_id: str = "agml") -> Path:
    """Lay out an interim tree from {canonical: [(image_key, size), ...]}.

    Entries sharing an image_key render the same photograph, which is how the
    duplicate cases are built. The key is namespaced by class, so the same key
    under two classes is two different photos - otherwise every class would
    dedup into whichever one sorts first.
    """
    interim = Path(root) / "interim"
    for canonical, entries in spec.items():
        for index, (key, size) in enumerate(entries):
            dest = interim / source_id / canonical / f"{key}-{index}-{size}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_leaf_photo(dest, size=(size, size), seed=_seed_for(f"{canonical}/{key}"))
    return interim


def seed_fake_source_for(source_id: str, raw_root, **_kwargs) -> tuple[Path, ...]:
    """Write a tiny stand-in archive for a real source, one image per label.

    Seeds are derived from the file and row, never from a counter, so a second
    prepare run over the same raw tree produces byte-identical inputs and the
    images never collide into a duplicate group.
    """
    from teasmart_ml.datasets.sources import SOURCES, HFParquetSource

    source = SOURCES[source_id]
    target = Path(raw_root) / source_id

    if isinstance(source, HFParquetSource):
        paths = []
        for relative in source.files:
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                make_parquet(
                    rows=[
                        (green_png(seed=_seed_for(f"{source_id}:{relative}:{index}")), index)
                        for index in range(len(source.label_names))
                    ],
                    label_names=source.label_names,
                    path=dest,
                )
            paths.append(dest)
        return tuple(paths)

    dest = target / source.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        make_yolo_zip(
            entries=[
                (
                    f"{source_id}-{index}",
                    green_jpeg(seed=_seed_for(f"{source_id}:{index}")),
                    (index,),
                )
                for index in range(len(source.label_names))
            ],
            names=source.label_names,
            path=dest,
        )
    return (dest,)


def flat_noise_photo(path, *, seed: int = 0, amplitude: int = 3) -> Path:
    """A near-uniform grey image with faint noise.

    Two of these are the same picture for any practical purpose, and yet their
    perceptual hashes are tens of bits apart: pHash thresholds DCT coefficients
    at their median, and a low-contrast image has many coefficients sitting on
    it. This is the shape of image that made a hash-gated search miss real
    duplicates.
    """
    rng = numpy.random.default_rng(seed)
    pixels = numpy.full((256, 256, 3), 128, dtype=numpy.int16)
    pixels += rng.integers(-amplitude, amplitude + 1, size=(256, 256, 3))
    Image.fromarray(numpy.clip(pixels, 0, 255).astype(numpy.uint8), mode="RGB").save(path)
    return Path(path)
