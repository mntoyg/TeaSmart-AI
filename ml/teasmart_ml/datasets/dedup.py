"""Collapse duplicate photographs across sources.

Several of the sources derive from the same Roboflow upload, so the duplicates
differ in bytes while being the same photograph: hashing bytes or MD5 would miss
every one of them. A duplicate that straddles the train and test sets inflates
the reported accuracy with images the model has already seen, which is the one
error no later metric can reveal.

Grouping is single-linkage, so a chain of recompressions collapses to one group
rather than leaving the ends in different splits.
"""

from collections.abc import Iterator, Sequence
from pathlib import Path

import imagehash
import numpy
from PIL import Image

DUPLICATE_DISTANCE = 5

_HASH_BYTES = 8
_CHUNK_ROWS = 512
_POPCOUNT = numpy.array([bin(value).count("1") for value in range(256)], dtype=numpy.uint8)


def phash_hex(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image))


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _pixel_area(path: Path) -> int:
    with Image.open(path) as image:
        return image.width * image.height


def _pack(hashes: Sequence[str]) -> numpy.ndarray:
    return numpy.array(
        [
            [int(value[index : index + 2], 16) for index in range(0, _HASH_BYTES * 2, 2)]
            for value in hashes
        ],
        dtype=numpy.uint8,
    )


def _near_pairs(hashes: Sequence[str], max_distance: int) -> Iterator[tuple[int, int]]:
    """Every (i, j) with i < j whose hashes are within max_distance.

    Chunked numpy rather than a Python double loop: the real corpus is around
    12,000 images, which is 70 million pairs.
    """
    packed = _pack(hashes)
    count = len(hashes)
    for start in range(0, count, _CHUNK_ROWS):
        stop = min(start + _CHUNK_ROWS, count)
        differences = numpy.bitwise_xor(packed[start:stop, None, :], packed[None, :, :])
        distances = _POPCOUNT[differences].sum(axis=2)
        rows, columns = numpy.nonzero(distances <= max_distance)
        for row, column in zip(rows.tolist(), columns.tolist()):
            left = start + row
            if left < column:
                yield left, column


def group_duplicates(
    paths: Sequence[Path], *, max_distance: int = DUPLICATE_DISTANCE
) -> tuple[tuple[Path, ...], ...]:
    """Partition paths into duplicate groups, highest-resolution copy first."""
    items = list(paths)
    hashes = [phash_hex(path) for path in items]

    parent = list(range(len(items)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left, right in _near_pairs(hashes, max_distance):
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    grouped: dict[int, list[int]] = {}
    for index in range(len(items)):
        grouped.setdefault(find(index), []).append(index)

    return tuple(
        tuple(
            sorted(
                (items[index] for index in members),
                key=lambda path: (-_pixel_area(path), str(path)),
            )
        )
        for members in grouped.values()
    )
