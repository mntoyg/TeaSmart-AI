import cv2
import numpy

from app.core.config import get_settings
from app.services.quality import assess_quality


def thresholds() -> dict[str, float]:
    """Read the thresholds from config, so the tests and the service agree."""
    settings = get_settings()
    return dict(
        blur_threshold=settings.blur_threshold,
        exposure_min_mean=settings.exposure_min_mean,
        exposure_max_mean=settings.exposure_max_mean,
        clip_max_pct=settings.clip_max_pct,
    )


def sharp_leaf_image() -> numpy.ndarray:
    """A green canvas with hard-edged dark speckles, so the Laplacian bites."""
    rng = numpy.random.default_rng(7)
    image = numpy.full((256, 256, 3), (34, 139, 34), dtype=numpy.uint8)
    for y, x in rng.integers(0, 250, size=(260, 2)):
        image[y : y + 3, x : x + 3] = (20, 20, 20)
    return image


def crushed_blacks_image() -> numpy.ndarray:
    """Sharp and mid-exposed on average, but a fifth of it is clipped to black.

    A leaf in deep shade under the canopy, or shot into the light: an ordinary
    frame on a mountain plot.
    """
    image = sharp_leaf_image()
    image[:, :52] = (0, 0, 0)
    return image


def blur(image: numpy.ndarray, *, ksize: int) -> numpy.ndarray:
    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def scale_brightness(image: numpy.ndarray, factor: float) -> numpy.ndarray:
    return numpy.clip(image.astype(numpy.float32) * factor, 0, 255).astype(numpy.uint8)


def test_a_sharp_well_exposed_leaf_passes():
    result = assess_quality(sharp_leaf_image(), **thresholds())
    assert result.passed is True
    assert result.reason_th is None


def test_a_blurred_image_fails_with_the_thai_blur_message():
    result = assess_quality(blur(sharp_leaf_image(), ksize=31), **thresholds())
    assert result.passed is False
    assert result.reason == "blurry"
    assert result.reason_th == "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"


def test_a_dark_image_fails_as_underexposed_not_as_blurry():
    # Darkness also depresses the Laplacian variance, so exposure must be judged first.
    result = assess_quality(scale_brightness(sharp_leaf_image(), 0.08), **thresholds())
    assert result.passed is False
    assert result.reason == "underexposed"
    assert result.reason_th == "ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ"


def test_a_blown_out_image_fails_as_overexposed():
    # 8.0 rather than 4.0 since 2026-10-19: at 4.0 this fixture has a grey mean
    # of 201.6, inside the band, and used to be rejected by the high-clipping
    # check. That check now reports without deciding - see assess_quality - so
    # the fixture has to be genuinely blown for the mean to carry it.
    result = assess_quality(scale_brightness(sharp_leaf_image(), 8.0), **thresholds())
    assert result.passed is False
    assert result.reason == "overexposed"
    assert result.reason_th == "ภาพสว่างเกินไป กรุณาหลีกเลี่ยงแสงแดดจัดส่องตรง"


def test_a_deeply_shaded_frame_is_called_underexposed_not_overexposed():
    # Telling a worker standing in shade to avoid direct sun sends them the wrong
    # way, and the next frame fails for the same reason.
    result = assess_quality(crushed_blacks_image(), **thresholds())
    assert result.passed is False
    assert result.reason == "underexposed"
    assert result.reason_th == "ภาพมืดเกินไป กรุณาถ่ายในที่ที่มีแสงเพียงพอ"
    # The mean alone would have let this frame through; the clipping is the signal.
    assert 40.0 < result.exposure_mean < 215.0


def test_clipping_is_reported_separately_for_each_end_of_the_histogram():
    shaded = assess_quality(crushed_blacks_image(), **thresholds())
    blown = assess_quality(scale_brightness(sharp_leaf_image(), 8.0), **thresholds())
    assert shaded.clipped_low_pct > 0.10
    assert shaded.clipped_high_pct == 0.0
    assert blown.clipped_high_pct > 0.10
    assert blown.clipped_low_pct == 0.0


def test_blur_score_is_the_variance_of_the_laplacian_and_drops_when_blurred():
    sharp = assess_quality(sharp_leaf_image(), **thresholds()).blur_score
    soft = assess_quality(blur(sharp_leaf_image(), ksize=31), **thresholds()).blur_score
    assert sharp > 80.0 > soft


def test_scores_are_reported_even_when_the_image_passes():
    result = assess_quality(sharp_leaf_image(), **thresholds())
    assert 40.0 < result.exposure_mean < 215.0
    assert 0.0 <= result.clipped_pct <= 1.0
