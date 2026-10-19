"""Stage 5: severity as a fraction of the leaf.

The denominator is the whole leaf including its lesions, which is what stage 2
guarantees. If it were only the healthy tissue, the ratio would grow twice as
fast as the damage and a severe case would be unreadable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class Severity:
    affected_pct: float
    level: str


def assess_severity(
    lesion_area_px: int, leaf_area_px: int, settings: Settings
) -> Severity:
    """Affected fraction, banded mild / moderate / severe.

    Band boundaries belong to the higher band: exactly 5% is moderate, not
    mild. Under-reporting damage is the costlier direction.
    """
    if leaf_area_px <= 0:
        return Severity(affected_pct=0.0, level="mild")

    fraction = min(lesion_area_px / leaf_area_px, 1.0)
    if fraction >= settings.severity_severe_pct:
        level = "severe"
    elif fraction >= settings.severity_moderate_pct:
        level = "moderate"
    else:
        level = "mild"
    return Severity(affected_pct=fraction, level=level)
