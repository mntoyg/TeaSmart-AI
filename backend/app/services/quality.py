"""Stage 1: the image quality gate.

A phone photo taken in a tea field can be smeared by motion, shot into the sun,
or taken at dusk. Guessing a diagnosis from such a frame is worse than refusing
it, so this stage rejects the frame and tells the worker what to change.
"""

from dataclasses import dataclass

import cv2
import numpy

_BLURRY_TH = "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"
_DARK_TH = "ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ"
_BRIGHT_TH = "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงแดดจัดส่องตรง"


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    blur_score: float
    exposure_mean: float
    clipped_pct: float
    reason: str | None
    reason_th: str | None


def assess_quality(
    image: numpy.ndarray,
    *,
    blur_threshold: float,
    exposure_min_mean: float,
    exposure_max_mean: float,
    clip_max_pct: float,
) -> QualityResult:
    """Judge an RGB frame, always reporting all three scores."""
    grey = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(grey, cv2.CV_64F).var())
    exposure_mean = float(grey.mean())
    # Counted across channels rather than on the grey: a frame whose green
    # channel is blown still averages mid-grey, while the colour the lesion
    # analyser depends on is already gone.
    clipped_pct = float(numpy.count_nonzero((image == 0) | (image == 255)) / image.size)
    scores = (blur_score, exposure_mean, clipped_pct)

    # Exposure is judged before blur on purpose. Darkness flattens the Laplacian
    # as surely as motion does, so checking blur first would call every dusk
    # photo "blurry" and send the worker off to hold the phone steadier when
    # what they actually need is light.
    if exposure_mean < exposure_min_mean:
        return QualityResult(False, *scores, "underexposed", _DARK_TH)
    if exposure_mean > exposure_max_mean or clipped_pct > clip_max_pct:
        return QualityResult(False, *scores, "overexposed", _BRIGHT_TH)
    if blur_score < blur_threshold:
        return QualityResult(False, *scores, "blurry", _BLURRY_TH)
    return QualityResult(True, *scores, None, None)
