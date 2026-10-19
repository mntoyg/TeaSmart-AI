"""Stage 2: find the leaf.

Two things depend on this and both break quietly if it is wrong. Severity is
lesion area over *leaf* area, so the denominator has to be the whole leaf. And
the lesion search is confined to the leaf, so anything left in the background -
soil, shadow, a sleeve - becomes a false lesion.

The mask is the **filled outline** of the largest green region, not the green
pixels themselves. A lesion is brown: if the mask were the green pixels, every
diseased patch would sit outside the leaf, the denominator would shrink as the
disease spread, and a severe infection would report a lower affected percentage
than a mild one.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.core.config import Settings


@dataclass(frozen=True)
class Leaf:
    """The leaf, as the later stages need it."""

    mask: np.ndarray
    area_px: int
    bbox: tuple[int, int, int, int]
    crop: np.ndarray
    fallback: bool


def _green_mask(rgb: np.ndarray, settings: Settings) -> np.ndarray:
    """Excess green combined with an HSV green band.

    Excess green (2G - R - B) is robust to brightness, which matters under a
    canopy. It also fires on bright soil, so an HSV hue band removes what is
    merely pale rather than green.
    """
    channels = rgb.astype(np.int16)
    excess_green = 2 * channels[:, :, 1] - channels[:, :, 0] - channels[:, :, 2]

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue, saturation, value = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # OpenCV hue is 0-179, so green sits around 35-85.
    hue_ok = (hue >= 25) & (hue <= 95)

    return (
        (excess_green > settings.excess_green_min)
        & hue_ok
        & (saturation > settings.leaf_saturation_min)
        & (value > 20)
    ).astype(np.uint8)


def segment_leaf(rgb: np.ndarray, settings: Settings) -> Leaf:
    """The largest leaf in the frame, or the whole frame if there is none."""
    height, width = rgb.shape[:2]
    mask = _green_mask(rgb, settings)

    # Close first, then open: closing joins a leaf split by a vein highlight or
    # a lesion that reaches the edge, opening then drops speckle. The other
    # order would delete the speckle and then grow it back.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [
        contour
        for contour in contours
        if cv2.contourArea(contour) >= settings.leaf_min_area_frac * height * width
    ]

    if not contours:
        # No leaf found. A macro shot that fills the frame, or a grey card, or a
        # photograph of something else entirely. Analysing the whole frame and
        # saying so is more useful than refusing, and `fallback` travels with
        # the result so nothing downstream mistakes it for a real segmentation.
        whole = np.ones((height, width), dtype=bool)
        return Leaf(
            mask=whole,
            area_px=height * width,
            bbox=(0, 0, width, height),
            crop=rgb,
            fallback=True,
        )

    largest = max(contours, key=cv2.contourArea)
    filled = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(filled, [largest], -1, 1, thickness=cv2.FILLED)

    x, y, box_width, box_height = cv2.boundingRect(largest)
    return Leaf(
        mask=filled.astype(bool),
        area_px=int(filled.sum()),
        bbox=(x, y, box_width, box_height),
        crop=np.ascontiguousarray(rgb[y : y + box_height, x : x + box_width]),
        fallback=False,
    )
