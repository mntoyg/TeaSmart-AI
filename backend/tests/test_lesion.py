"""Stage 4: burn versus disease, the feature the product exists for.

There is no labelled burn data anywhere, so there is no model here and no
accuracy claim. What there is: five features with a physical justification, a
weighted score, and synthetic fixtures that exercise each feature in the
direction the spec says it should move.

Synthetic fixtures prove the features measure what they claim on cases built to
contain it. They do not prove the analyser works on a tea farm. The number that
speaks to that is specificity on real confirmed-disease photographs, reported in
docs/EVIDENCE.md, and it is measured separately.
"""

import cv2
import numpy as np

from app.core.config import get_settings
from app.services.lesion import analyse_lesion
from app.services.segment import segment_leaf

LEAF_GREEN = (54, 122, 58)
SOIL = (92, 74, 62)


def _leaf_frame(size: int = 360) -> np.ndarray:
    frame = np.full((size, size, 3), SOIL, dtype=np.uint8)
    cv2.ellipse(frame, (size // 2, size // 2), (140, 95), 0, 0, 360, LEAF_GREEN, -1)
    return frame


def _analyse(frame: np.ndarray):
    settings = get_settings()
    return analyse_lesion(frame, segment_leaf(frame, settings), settings)


def _disease_lesion(frame: np.ndarray, centre=(180, 180)) -> np.ndarray:
    """Crisp margin, concentric rings, black dots: the three disease cues."""
    for radius, colour in ((34, (92, 74, 40)), (24, (150, 128, 86)), (14, (108, 86, 52))):
        cv2.circle(frame, centre, radius, colour, -1)
    cv2.circle(frame, centre, 35, (46, 34, 24), thickness=2)  # dark margin
    rng = np.random.default_rng(4)
    for _ in range(40):
        angle, distance = rng.uniform(0, 2 * np.pi), rng.uniform(0, 30)
        point = (
            int(centre[0] + distance * np.cos(angle)),
            int(centre[1] + distance * np.sin(angle)),
        )
        cv2.circle(frame, point, 1, (20, 16, 12), -1)  # acervuli
    return frame


def _burn_lesion(frame: np.ndarray) -> np.ndarray:
    """Diffuse, uniform straw, at the margin: the three burn cues.

    Sized and placed from the physical case, after an earlier version put a
    36x30 blotch centred 15 px from the leaf edge. That one vanished entirely
    once the lesion search started excluding an 8 px rim - and it deserved to,
    because the blur also ate the leaf boundary and left the whole blotch
    inside the rim. Real sun scorch covers a fifth to a third of the leaf
    width and reaches well inward from the margin, which is what this draws:
    high edge affinity and still a measurable core.
    """
    overlay = frame.copy()
    cv2.ellipse(overlay, (288, 180), (52, 44), 0, 0, 360, (196, 176, 128), -1)
    blurred = cv2.GaussianBlur(overlay, (41, 41), 0)
    # Only where the burn was drawn, so the rest of the leaf stays sharp.
    region = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.ellipse(region, (288, 180), (70, 62), 0, 0, 360, 1, -1)
    frame[region == 1] = blurred[region == 1]
    return frame


def test_a_healthy_leaf_has_almost_no_lesion() -> None:
    result = _analyse(_leaf_frame())

    assert result.lesion_area_px < 0.02 * result.leaf_area_px
    assert result.verdict == "disease"  # nothing to call a burn
    assert 0.0 <= result.burn_likelihood <= 1.0


def test_a_disease_lesion_is_called_disease() -> None:
    result = _analyse(_disease_lesion(_leaf_frame()))

    assert result.lesion_area_px > 1_000
    assert result.verdict == "disease"
    assert result.burn_likelihood < get_settings().burn_threshold


def test_a_burn_lesion_scores_far_above_a_disease_lesion() -> None:
    """Separation, not a verdict - and the distinction is the honest part.

    This used to assert `verdict == "physical_burn"`. It no longer does, and
    the reason is in docs/EVIDENCE.md section 5.5: synthetic burns score a
    median likelihood of 0.254 while real disease images reach 0.714 at the
    99th percentile, so the populations overlap. The threshold stays at 0.60,
    above this fixture, because lowering it to catch the fixture would pull in
    real disease images whose 90th percentile is 0.430 and specificity would
    collapse.

    Making this test pass by tuning the weights until one synthetic fixture
    clears the threshold would be fitting to a fixture built from the same
    feature definitions it is testing. What is defensible is that the burn case
    scores far higher than the disease case, which is what this asserts.
    """
    settings = get_settings()
    burn = _analyse(_burn_lesion(_leaf_frame()))
    disease = _analyse(_disease_lesion(_leaf_frame()))

    assert burn.lesion_area_px > settings.lesion_min_area_px
    assert burn.insufficient_lesion is False
    # Two orders of magnitude apart on the fixtures, about 5 score units.
    assert burn.burn_likelihood > disease.burn_likelihood * 20
    assert burn.burn_likelihood > 0.25
    # And the conservative threshold is deliberately above it.
    assert burn.burn_likelihood < settings.burn_threshold


def test_each_feature_moves_the_way_the_spec_says() -> None:
    """The features have to differ, not just the verdict.

    If the verdict were right while every feature sat at the same value, the
    score would be reading noise and the next fixture would flip it.
    """
    disease = _analyse(_disease_lesion(_leaf_frame())).features
    burn = _analyse(_burn_lesion(_leaf_frame())).features

    assert disease.edge_sharpness > burn.edge_sharpness
    assert disease.acervuli_score > burn.acervuli_score
    assert burn.edge_affinity > disease.edge_affinity
    assert disease.colour_zonation > burn.colour_zonation


def test_every_feature_is_normalised_into_the_unit_range() -> None:
    # The score is a weighted sum, so a feature that can reach 50 would drown
    # the other four whatever its weight.
    for frame in (_leaf_frame(), _disease_lesion(_leaf_frame()), _burn_lesion(_leaf_frame())):
        features = _analyse(frame).features
        for name, value in features.as_dict().items():
            assert 0.0 <= value <= 1.0, f"{name} = {value}"


def test_the_verdict_follows_the_configured_threshold() -> None:
    # Tunable without code changes, per the spec, and this is what proves the
    # setting is wired to the decision rather than decorative.
    settings = get_settings()
    frame = _disease_lesion(_leaf_frame())
    leaf = segment_leaf(frame, settings)

    permissive = settings.model_copy(update={"burn_threshold": 0.0})
    assert analyse_lesion(frame, leaf, permissive).verdict == "physical_burn"

    strict = settings.model_copy(update={"burn_threshold": 1.01})
    assert analyse_lesion(frame, leaf, strict).verdict == "disease"


def test_a_lesion_too_small_to_measure_does_not_get_a_verdict() -> None:
    # Three brown pixels are not evidence of anything, and the features that
    # read a boundary band or a radial profile are undefined on them. Claiming
    # a burn from that would be the worst possible failure: it tells a farmer
    # not to spray a leaf that may well be diseased.
    frame = _leaf_frame()
    cv2.circle(frame, (180, 180), 2, (120, 86, 44), -1)

    result = _analyse(frame)

    assert result.verdict == "disease"
    assert result.burn_likelihood == 0.0
    assert result.insufficient_lesion is True
