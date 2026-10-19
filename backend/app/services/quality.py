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
    clipped_low_pct: float
    clipped_high_pct: float
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
    """Judge an RGB frame, always reporting every score."""
    grey = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(grey, cv2.CV_64F).var())
    exposure_mean = float(grey.mean())

    # Clipping is counted per channel rather than on the grey: a frame whose
    # green channel is blown still averages mid-grey, while the colour the lesion
    # analyser depends on is already gone. The two ends are counted separately
    # because they call for opposite corrections - a frame crushed to black needs
    # more light, not less.
    #
    # HIGH clipping is measured and reported but is NOT a rejection reason, as
    # of 2026-10-19. It was, and it rejected every leaf photographed on white
    # paper - three of three agml images, live, against the real endpoint. On
    # such a frame the blown pixels are the background, and a blown background
    # says nothing about whether the leaf lost detail. Judging it properly means
    # measuring inside the leaf mask, which needs stage 2, which this stage
    # deliberately runs before so that it stays cheap and portable to the
    # browser. So the honest options were to measure the wrong thing or to
    # measure nothing, and reporting without deciding is the second.
    #
    # LOW clipping stays decisive: a frame crushed to black has genuinely lost
    # the shadow detail the lesion analyser reads, and nothing in 400 corpus
    # images trips it.
    clipped_low_pct = float(numpy.count_nonzero(image == 0) / image.size)
    clipped_high_pct = float(numpy.count_nonzero(image == 255) / image.size)
    scores = (
        blur_score,
        exposure_mean,
        clipped_low_pct + clipped_high_pct,
        clipped_low_pct,
        clipped_high_pct,
    )

    # Exposure is judged before blur on purpose. Darkness flattens the Laplacian
    # as surely as motion does, so checking blur first would call every dusk
    # photo "blurry" and send the worker off to hold the phone steadier when what
    # they actually need is light.
    if exposure_mean < exposure_min_mean or clipped_low_pct > clip_max_pct:
        return QualityResult(False, *scores, "underexposed", _DARK_TH)
    if exposure_mean > exposure_max_mean:
        return QualityResult(False, *scores, "overexposed", _BRIGHT_TH)
    if blur_score < blur_threshold:
        return QualityResult(False, *scores, "blurry", _BLURRY_TH)
    return QualityResult(True, *scores, None, None)
