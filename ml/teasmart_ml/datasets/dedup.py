"""Collapse duplicate photographs across sources.

Several of the sources derive from the same Roboflow upload, so the duplicates
differ in bytes while being the same photograph. Hashing bytes or MD5 would miss
every one of them, and a duplicate straddling the train and test boundary
inflates the reported accuracy with images the model has already seen, which is
the one error no later metric can reveal.

Two decisions here were made from measurements on the real corpus, not from
first principles:

Membership is judged against a group leader, never transitively. Transitive
grouping was tried first and chained near misses into a group of 866 images,
discarding hundreds of distinct photographs: a is close to b and b to c, while a
and c are nothing alike.

And a hash match alone is not enough. At a Hamming distance of 5, 24% of
collapsed pairs turned out not to be the same photograph - two different leaves
centred on the same background share a coarse layout, and a 64-bit perceptual
hash sees little else. So the hash finds candidates and a greyscale comparison
decides.

PIXEL_CONFIRM_MAE is a judgement at a boundary, not a natural gap. Across the
real corpus, accepted pairs have a median difference of 0.07 of 255 and a 99th
percentile of 4.93, while the closest rejected pair measures 8.2 - but the
accepted distribution runs right up to the threshold, so the two populations are
adjacent rather than separated. The band from 5 to 8 is most likely Roboflow
brightness augmentation of one base image, which counts as a duplicate for
leakage purposes, so the threshold sits above it. Moving it to 4.93 would change
the corpus by 33 images out of 8,541.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import imagehash
import numpy
from PIL import Image

DUPLICATE_DISTANCE = 5
PIXEL_CONFIRM_MAE = 8.0

_HASH_BYTES = 8
_THUMBNAIL = (32, 32)
_POPCOUNT = numpy.array(
    [bin(value).count("1") for value in range(256)], dtype=numpy.uint8
)


def phash_hex(path: Path) -> str:
    with Image.open(path) as image:
        return str(imagehash.phash(image))


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def thumbnail(path: Path) -> numpy.ndarray:
    """A small greyscale array, the unit the pixel confirmation compares."""
    with Image.open(path) as image:
        return numpy.asarray(
            image.convert("L").resize(_THUMBNAIL), dtype=numpy.float32
        )


def pixel_mae(left: numpy.ndarray, right: numpy.ndarray) -> float:
    return float(numpy.abs(left - right).mean())


def _pixel_area(path: Path) -> int:
    with Image.open(path) as image:
        return image.width * image.height


def _pack(hashes: Sequence[str]) -> numpy.ndarray:
    return numpy.array(
        [
            [
                int(value[index : index + 2], 16)
                for index in range(0, _HASH_BYTES * 2, 2)
            ]
            for value in hashes
        ],
        dtype=numpy.uint8,
    )


def group_hash_indices(
    hashes: Sequence[str],
    *,
    max_distance: int = DUPLICATE_DISTANCE,
    confirm: Callable[[int, int], bool] | None = None,
) -> tuple[tuple[int, ...], ...]:
    """Partition hash indices into groups, each member confirmed against its leader.

    Input order is the leader preference: the first unassigned hash becomes a
    leader and claims the unassigned hashes within max_distance that `confirm`
    accepts. Callers that care which copy survives sort before calling. Without
    a `confirm`, every hash match is accepted.
    """
    if not hashes:
        return ()

    packed = _pack(hashes)
    count = len(hashes)
    assigned = numpy.zeros(count, dtype=bool)
    groups: list[tuple[int, ...]] = []

    for leader in range(count):
        if assigned[leader]:
            continue
        # One vectorised sweep per leader: the real corpus is about 12,000
        # images, and a Python pairwise loop over it is 70 million comparisons.
        differences = numpy.bitwise_xor(packed[leader], packed)
        distances = _POPCOUNT[differences].sum(axis=1)
        candidates = numpy.nonzero((distances <= max_distance) & ~assigned)[0]
        members = [
            int(candidate)
            for candidate in candidates
            if candidate == leader or confirm is None or confirm(leader, int(candidate))
        ]
        assigned[members] = True
        groups.append(tuple(members))

    return tuple(groups)


def group_duplicates(
    paths: Sequence[Path],
    *,
    max_distance: int = DUPLICATE_DISTANCE,
    max_pixel_mae: float = PIXEL_CONFIRM_MAE,
) -> tuple[tuple[Path, ...], ...]:
    """Partition paths into duplicate groups, highest-resolution copy first."""
    ordered = sorted(paths, key=lambda path: (-_pixel_area(path), str(path)))
    hashes = [phash_hex(path) for path in ordered]
    thumbnails = [thumbnail(path) for path in ordered]

    def confirm(leader: int, candidate: int) -> bool:
        return pixel_mae(thumbnails[leader], thumbnails[candidate]) <= max_pixel_mae

    return tuple(
        tuple(ordered[index] for index in group)
        for group in group_hash_indices(
            hashes, max_distance=max_distance, confirm=confirm
        )
    )
