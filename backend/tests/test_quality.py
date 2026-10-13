import cv2
import numpy

from app.services.quality import assess_quality

THRESHOLDS = dict(
    blur_threshold=80.0,
    exposure_min_mean=40.0,
    exposure_max_mean=215.0,
    clip_max_pct=0.10,
)


def sharp_leaf_image() -> numpy.ndarray:
    """A green canvas with hard-edged dark speckles, so the Laplacian bites."""
    rng = numpy.random.default_rng(7)
    image = numpy.full((256, 256, 3), (34, 139, 34), dtype=numpy.uint8)
    for y, x in rng.integers(0, 250, size=(260, 2)):
        image[y : y + 3, x : x + 3] = (20, 20, 20)
    return image


def blur(image: numpy.ndarray, *, ksize: int) -> numpy.ndarray:
    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def scale_brightness(image: numpy.ndarray, factor: float) -> numpy.ndarray:
    return numpy.clip(image.astype(numpy.float32) * factor, 0, 255).astype(numpy.uint8)


def test_a_sharp_well_exposed_leaf_passes():
    result = assess_quality(sharp_leaf_image(), **THRESHOLDS)
    assert result.passed is True
    assert result.reason_th is None


def test_a_blurred_image_fails_with_the_thai_blur_message():
    result = assess_quality(blur(sharp_leaf_image(), ksize=31), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "blurry"
    assert result.reason_th == "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"


def test_a_dark_image_fails_as_underexposed_not_as_blurry():
    # Darkness also depresses the Laplacian variance, so exposure must be judged first.
    result = assess_quality(scale_brightness(sharp_leaf_image(), 0.08), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "underexposed"
    assert result.reason_th == "ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ"


def test_a_blown_out_image_fails_as_overexposed():
    result = assess_quality(scale_brightness(sharp_leaf_image(), 4.0), **THRESHOLDS)
    assert result.passed is False
    assert result.reason == "overexposed"
    assert result.reason_th == "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงแดดจัดส่องตรง"


def test_blur_score_is_the_variance_of_the_laplacian_and_drops_when_blurred():
    sharp = assess_quality(sharp_leaf_image(), **THRESHOLDS).blur_score
    soft = assess_quality(blur(sharp_leaf_image(), ksize=31), **THRESHOLDS).blur_score
    assert sharp > 80.0 > soft


def test_scores_are_reported_even_when_the_image_passes():
    result = assess_quality(sharp_leaf_image(), **THRESHOLDS)
    assert 40.0 < result.exposure_mean < 215.0
    assert 0.0 <= result.clipped_pct <= 1.0
