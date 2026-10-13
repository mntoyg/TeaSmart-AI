"""Collapse duplicate photographs across sources.

Several of the sources derive from the same upload - measured on the real
corpus, 3,245 of 3,261 duplicate groups span two sources - so duplicates differ
in bytes while being the same photograph. Hashing bytes or MD5 would miss every
one of them, and a duplicate straddling the train and test boundary inflates the
reported accuracy with images the model has already seen, which is the one error
no later metric can reveal.

**A duplicate is defined by pixels, not by a hash.** Two images are the same
photograph when the mean absolute difference of their 32x32 greyscale
thumbnails is at most DUPLICATE_MAE of 255.

A perceptual hash was tried as the gate first and was wrong twice over. Judging
membership transitively chained near misses into a group of 866 images. Worse,
using the hash to generate candidates silently capped recall: a review of the
resulting manifest found 127 cross-split pairs under the pixel threshold whose
hashes were 6 to 30 apart, leaving 3.24% of the evaluation set with a twin in
training. The mechanism is that pHash thresholds DCT coefficients at their
median, so a low-contrast image has many coefficients near that median and a
near-identical copy flips them: two images measured here at a pixel difference
of 0.01 hash 26 bits apart.

So the comparison is exhaustive, made tractable by an exact lower bound rather
than by a filter that can be wrong. The mean absolute difference of 4x4 block
means can never exceed the mean absolute difference of the pixels those blocks
average (Jensen), so a pair whose block bound exceeds the threshold cannot pass
the full comparison and is skipped without ever being decoded further. Nothing
is discarded on an approximation.
"""

from collections.abc import Sequence
from pathlib import Path

import imagehash
import numpy
from PIL import Image

DUPLICATE_MAE = 8.0

_THUMBNAIL = (32, 32)
_BLOCK_GRID = 4


def phash_hex(path: Path) -> str:
    """Kept as a manifest column for auditing. It does not decide anything."""
    with Image.open(path) as image:
        return str(imagehash.phash(image))


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def thumbnail(path: Path) -> numpy.ndarray:
    """The 32x32 greyscale array that every duplicate decision is made on."""
    with Image.open(path) as image:
        return numpy.asarray(
            image.convert("L").resize(_THUMBNAIL), dtype=numpy.float32
        )


def pixel_mae(left: numpy.ndarray, right: numpy.ndarray) -> float:
    return float(numpy.abs(left - right).mean())


def block_means(thumbnails: numpy.ndarray) -> numpy.ndarray:
    """Mean of each 4x4 block, flattened. Shape (..., 16).

    The mean absolute difference of these is a lower bound on the mean absolute
    difference of the pixels, which is what makes the prefilter exact.
    """
    side = _THUMBNAIL[0] // _BLOCK_GRID
    reshaped = thumbnails.reshape(
        *thumbnails.shape[:-2], _BLOCK_GRID, side, _BLOCK_GRID, side
    )
    return reshaped.mean(axis=(-3, -1)).reshape(*thumbnails.shape[:-2], -1)


def _pixel_area(path: Path) -> int:
    with Image.open(path) as image:
        return image.width * image.height


def group_thumbnail_indices(
    thumbnails: numpy.ndarray, *, max_pixel_mae: float = DUPLICATE_MAE
) -> tuple[tuple[int, ...], ...]:
    """Partition thumbnail indices into duplicate groups.

    Input order is the leader preference: the first unassigned index becomes a
    leader and claims every unassigned thumbnail within max_pixel_mae of it.
    Callers that care which copy survives sort before calling.
    """
    count = len(thumbnails)
    if count == 0:
        return ()

    bounds = block_means(thumbnails)
    assigned = numpy.zeros(count, dtype=bool)
    groups: list[tuple[int, ...]] = []

    for leader in range(count):
        if assigned[leader]:
            continue
        lower_bound = numpy.abs(bounds - bounds[leader]).mean(axis=1)
        candidates = numpy.nonzero((lower_bound <= max_pixel_mae) & ~assigned)[0]
        differences = numpy.abs(thumbnails[candidates] - thumbnails[leader]).mean(
            axis=(1, 2)
        )
        members = candidates[differences <= max_pixel_mae]
        assigned[members] = True
        groups.append(tuple(int(index) for index in members))

    return tuple(groups)


def group_duplicates(
    paths: Sequence[Path], *, max_pixel_mae: float = DUPLICATE_MAE
) -> tuple[tuple[Path, ...], ...]:
    """Partition paths into duplicate groups, highest-resolution copy first."""
    ordered = sorted(paths, key=lambda path: (-_pixel_area(path), str(path)))
    if not ordered:
        return ()
    thumbnails = numpy.stack([thumbnail(path) for path in ordered])
    return tuple(
        tuple(ordered[index] for index in group)
        for group in group_thumbnail_indices(thumbnails, max_pixel_mae=max_pixel_mae)
    )
