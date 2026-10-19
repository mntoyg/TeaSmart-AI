"""Stage 4: is the damage a disease, or is it a burn?

**No labelled burn photograph exists in any dataset we could find.** This
module is therefore not a model and makes no accuracy claim. It is five
measurements with a physical justification, normalised and combined with
hand-set weights, and the weights are hand-set because there is nothing to fit
them to. They live in `Settings` so they can be tuned without a code change.

| feature | high when | because |
|---|---|---|
| `edge_sharpness` | disease | a fungal margin is a crisp dark line; sun damage fades out |
| `ring_score` | disease | blight expands in flushes, leaving concentric zones |
| `acervuli_score` | disease | fruiting bodies are black dots, 2-8 px at this scale |
| `edge_affinity` | burn | sun and spray damage start at the tip and margin |
| `colour_zonation` | disease | multi-band brown to grey, versus uniform straw |

The honest metric is **specificity on confirmed-disease images**: how often a
real diseased leaf is wrongly called a burn. Sensitivity to actual burns cannot
be measured without burn photographs, and no number for it is reported.

Nothing here reports a burn from a lesion too small to measure. A boundary band
and a radial profile are undefined on a few pixels, and a false burn verdict is
the worst failure this product has: it tells a farmer not to spray a leaf that
may be diseased.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from app.core.config import Settings
from app.services.segment import Leaf


@dataclass(frozen=True)
class LesionFeatures:
    edge_sharpness: float
    ring_score: float
    acervuli_score: float
    edge_affinity: float
    colour_zonation: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class LesionAnalysis:
    verdict: str
    burn_likelihood: float
    features: LesionFeatures
    lesion_mask: np.ndarray
    lesion_area_px: int
    leaf_area_px: int
    insufficient_lesion: bool


_ZERO_FEATURES = LesionFeatures(0.0, 0.0, 0.0, 0.0, 0.0)


def _lesion_mask(rgb: np.ndarray, leaf: Leaf, settings: Settings) -> np.ndarray:
    """Tissue inside the leaf that is markedly less green than the leaf is.

    Three measured decisions, in the order they were found:

    **Measured against this leaf, not a constant.** A fixed excess-green
    cut-off finds nothing: brown and tan lesions score slightly POSITIVE on
    2G - R - B, because green sits between red and blue in them, so a constant
    low enough to exclude healthy tissue excludes the lesion too.

    **The reference is the 75th percentile, not the median.** A leaf that is a
    third damaged drags its own median down, below the lesion it is meant to
    find. A high percentile is healthy tissue even when much of the leaf is not.

    **A rim just inside the leaf outline is excluded from the search.** That rim
    is where green fades - antialiasing, the shadow at the leaf edge, a little
    blur - so it is less green than the interior on EVERY leaf and crosses any
    fractional cut-off. With it included the mask fired on 96% of HEALTHY test
    leaves and separation was negative at every parameter choice measured;
    excluding 8 px moved separation from -0.201 to +0.352. The rim is a
    segmentation artefact, not tissue.

    The rim is excluded from the SEARCH only. Severity still divides by the
    whole leaf, and 8 px is narrow enough to leave a marginal burn measurable -
    a burn blotch is tens of pixels across.
    """
    search = leaf.mask
    if settings.lesion_search_erode_px > 0:
        size = 2 * settings.lesion_search_erode_px + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        search = cv2.erode(leaf.mask.astype(np.uint8), kernel).astype(bool)
        if not search.any():
            # A leaf thinner than the rim. Nothing can be measured in it.
            return np.zeros(rgb.shape[:2], dtype=bool)

    channels = rgb.astype(np.int16)
    excess_green = 2 * channels[:, :, 1] - channels[:, :, 0] - channels[:, :, 2]

    inside = excess_green[search]
    healthy = float(np.percentile(inside, settings.lesion_reference_pct))
    # A leaf whose reference is already near zero is not green at all - a
    # fallback frame, or a photograph of something else. Nothing is called a
    # lesion there, because everything would be.
    if healthy < settings.lesion_min_healthy_green:
        return np.zeros(rgb.shape[:2], dtype=bool)

    cutoff = healthy * settings.lesion_green_fraction
    mask = (search & (excess_green < cutoff)).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask.astype(bool)


def _edge_sharpness(grey: np.ndarray, mask: np.ndarray) -> float:
    """How tightly the lesion boundary's gradient is concentrated.

    Not the size of the gradient. The first version measured the mean gradient
    in a boundary band against the 95th percentile of the frame, and it
    returned 1.0 for a crisp fungal margin and 1.0 for a deliberately blurred
    burn - because the band is by construction where the largest gradients are,
    whatever shape the transition has.

    What separates the two is the *width* of the transition. A crisp margin
    puts all of its gradient in a two-pixel line; sun damage spreads the same
    total over ten. So this compares a narrow band against a wide one: for a
    step edge the wide band is mostly flat tissue and the ratio is high, and
    for a gradual edge both bands look alike and the ratio approaches one.
    Scale-free, and independent of exposure.
    """
    solid = mask.astype(np.uint8)
    narrow_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    wide_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    narrow = (cv2.dilate(solid, narrow_kernel) - cv2.erode(solid, narrow_kernel)).astype(bool)
    wide = (cv2.dilate(solid, wide_kernel) - cv2.erode(solid, wide_kernel)).astype(bool)
    if not narrow.any() or not wide.any():
        return 0.0

    gradient = cv2.magnitude(
        cv2.Sobel(grey, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(grey, cv2.CV_32F, 0, 1, ksize=3),
    )
    ratio = float(gradient[narrow].mean()) / (float(gradient[wide].mean()) + 1e-6)
    # A step edge concentrates into the narrow band by roughly the band width
    # ratio, about 4x here. Mapped so 1.0 (no concentration) is 0 and 3.5 or
    # more is 1.0.
    return float(np.clip((ratio - 1.0) / 2.5, 0.0, 1.0))


def _ring_score(grey: np.ndarray, mask: np.ndarray) -> float:
    """Direction changes in the radial intensity profile from the centroid.

    A target-shaped lesion rises and falls as the radius grows. A uniform one
    does not. Counting sign changes of the smoothed derivative is cruder than a
    frequency analysis and needs no window choice to defend.
    """
    points = np.argwhere(mask)
    if points.shape[0] < 50:
        return 0.0

    centre_y, centre_x = points.mean(axis=0)
    distances = np.hypot(points[:, 0] - centre_y, points[:, 1] - centre_x)
    radius = distances.max()
    if radius < 6:
        return 0.0

    bins = 12
    index = np.minimum((distances / radius * bins).astype(int), bins - 1)
    values = grey[mask].astype(np.float32)
    profile = np.array(
        [values[index == step].mean() if (index == step).any() else np.nan
         for step in range(bins)]
    )
    profile = profile[~np.isnan(profile)]
    if profile.shape[0] < 5:
        return 0.0

    derivative = np.diff(profile)
    significant = derivative[np.abs(derivative) > 2.0]
    if significant.shape[0] < 2:
        return 0.0

    changes = int((np.diff(np.sign(significant)) != 0).sum())
    return float(min(changes / 3.0, 1.0))


def _acervuli_score(grey: np.ndarray, mask: np.ndarray, settings: Settings) -> float:
    """Density of small dark blobs inside the lesion.

    Black-hat finds features darker than their neighbourhood at a chosen scale,
    which is exactly what a fruiting body is. The size filter is what keeps it
    from counting the lesion's own dark margin.
    """
    area = int(mask.sum())
    if area < settings.lesion_min_area_px:
        return 0.0

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    blackhat = cv2.morphologyEx(grey, cv2.MORPH_BLACKHAT, kernel)
    dots = ((blackhat > 18) & mask).astype(np.uint8)

    count, _, stats, _ = cv2.connectedComponentsWithStats(dots, connectivity=8)
    sized = sum(
        1
        for index in range(1, count)
        if 2 <= stats[index, cv2.CC_STAT_AREA] <= 40
    )
    # Normalised against a density that already looks heavily speckled, so a
    # moderately spotted lesion does not saturate the feature.
    return float(min(sized / (area / 400.0 + 1e-9), 1.0))


def _edge_affinity(mask: np.ndarray, leaf: Leaf, settings: Settings) -> float:
    """Fraction of lesion pixels close to the leaf outline."""
    area = int(mask.sum())
    if area == 0:
        return 0.0

    leaf_solid = leaf.mask.astype(np.uint8)
    distance = cv2.distanceTransform(leaf_solid, cv2.DIST_L2, 5)
    near_edge = (distance <= settings.leaf_edge_band_px) & mask
    return float(min(int(near_edge.sum()) / area, 1.0))


def _colour_zonation(hsv: np.ndarray, mask: np.ndarray, settings: Settings) -> float:
    """How many distinct tones the lesion contains, and how saturated it is.

    The spec called for k-means with an inertia drop. This counts peaks in the
    value histogram instead: deterministic, a great deal cheaper, and good
    enough for one of five inputs to a weighted score. Recorded as a deviation
    in docs/DESIGN.md section 13 rather than left as a silent difference.
    """
    area = int(mask.sum())
    if area < settings.lesion_min_area_px:
        return 0.0

    values = hsv[:, :, 2][mask]
    histogram = cv2.calcHist([values], [0], None, [16], [0, 256]).flatten()
    histogram = histogram / max(histogram.sum(), 1.0)
    peaks = sum(
        1
        for index in range(1, 15)
        if histogram[index] > 0.05
        and histogram[index] >= histogram[index - 1]
        and histogram[index] >= histogram[index + 1]
    )

    saturation = float(hsv[:, :, 1][mask].mean()) / 255.0
    bands = min(peaks / 3.0, 1.0)
    return float(min(0.65 * bands + 0.35 * saturation, 1.0))


def analyse_lesion(
    rgb: np.ndarray, leaf: Leaf, settings: Settings
) -> LesionAnalysis:
    """Measure the lesion and decide between disease and physical burn."""
    mask = _lesion_mask(rgb, leaf, settings)
    area = int(mask.sum())

    if area < settings.lesion_min_area_px:
        return LesionAnalysis(
            verdict="disease",
            burn_likelihood=0.0,
            features=_ZERO_FEATURES,
            lesion_mask=mask,
            lesion_area_px=area,
            leaf_area_px=leaf.area_px,
            insufficient_lesion=True,
        )

    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    features = LesionFeatures(
        edge_sharpness=_edge_sharpness(grey, mask),
        ring_score=_ring_score(grey, mask),
        acervuli_score=_acervuli_score(grey, mask, settings),
        edge_affinity=_edge_affinity(mask, leaf, settings),
        colour_zonation=_colour_zonation(hsv, mask, settings),
    )

    # Disease evidence pushes the score down, burn evidence pushes it up. The
    # weights are expert priors, not fitted values, because there is nothing to
    # fit them to.
    weights = settings.burn_weights
    score = (
        settings.burn_bias
        - weights["edge_sharpness"] * features.edge_sharpness
        - weights["ring_score"] * features.ring_score
        - weights["acervuli_score"] * features.acervuli_score
        + weights["edge_affinity"] * features.edge_affinity
        - weights["colour_zonation"] * features.colour_zonation
    )
    burn_likelihood = float(1.0 / (1.0 + np.exp(-score)))

    return LesionAnalysis(
        verdict="physical_burn"
        if burn_likelihood >= settings.burn_threshold
        else "disease",
        burn_likelihood=burn_likelihood,
        features=features,
        lesion_mask=mask,
        lesion_area_px=area,
        leaf_area_px=leaf.area_px,
        insufficient_lesion=False,
    )
