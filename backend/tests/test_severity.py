"""Stage 5: how much of the leaf is damaged."""

import pytest

from app.core.config import get_settings
from app.services.severity import assess_severity


@pytest.mark.parametrize(
    ("lesion", "leaf", "level"),
    [
        (0, 10_000, "mild"),
        (400, 10_000, "mild"),  # 4%
        (500, 10_000, "moderate"),  # 5%, the boundary belongs to moderate
        (1_999, 10_000, "moderate"),
        (2_000, 10_000, "severe"),  # 20%, the boundary belongs to severe
        (9_000, 10_000, "severe"),
    ],
)
def test_bands_follow_the_spec(lesion: int, leaf: int, level: str) -> None:
    result = assess_severity(lesion, leaf, get_settings())
    assert result.level == level
    assert result.affected_pct == pytest.approx(lesion / leaf)


def test_a_zero_area_leaf_does_not_divide_by_zero() -> None:
    # Reachable: segmentation can return an empty mask on a frame with no
    # green at all, and a ZeroDivisionError inside a request would surface as
    # a 500 with no Thai message for the worker.
    result = assess_severity(0, 0, get_settings())
    assert result.affected_pct == 0.0
    assert result.level == "mild"


def test_a_lesion_larger_than_the_leaf_is_clamped() -> None:
    # Should not happen, because the lesion mask is intersected with the leaf
    # mask. If it ever does, a percentage above 100 would be rendered to a
    # worker, so it is clamped here rather than trusted.
    result = assess_severity(500, 100, get_settings())
    assert result.affected_pct == 1.0
    assert result.level == "severe"
