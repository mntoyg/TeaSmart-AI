"""Stage 2, and the trap in it.

A green mask finds the leaf. It does not find the *lesion*, because a lesion is
brown. If the leaf mask were the green pixels, every diseased patch would fall
outside the leaf, the severity denominator would shrink as the disease grew, and
a severe infection would report a smaller affected percentage than a mild one.

So the mask is the filled outline of the largest green region, and the test that
matters is the one with a brown blotch in the middle.
"""

import numpy as np

from app.core.config import get_settings
from app.services.segment import segment_leaf, vegetation_fraction

LEAF_GREEN = (54, 122, 58)
BROWN = (120, 86, 44)
SOIL = (92, 74, 62)


def _frame(size: int = 320) -> np.ndarray:
    return np.full((size, size, 3), SOIL, dtype=np.uint8)


def _add_leaf(frame: np.ndarray, centre=(160, 160), axes=(90, 60)) -> np.ndarray:
    import cv2

    cv2.ellipse(frame, centre, axes, 0, 0, 360, LEAF_GREEN, thickness=-1)
    return frame


def test_a_leaf_on_soil_is_found_and_the_background_is_not() -> None:
    leaf = segment_leaf(_add_leaf(_frame()), get_settings())

    assert leaf.fallback is False
    # An ellipse of 90x60 has area pi*a*b, about 16,965 px.
    assert 15_000 < leaf.area_px < 19_000
    assert leaf.mask[160, 160]
    assert not leaf.mask[5, 5]


def test_a_brown_lesion_stays_inside_the_leaf_mask() -> None:
    """The one that stops severity from being nonsense."""
    import cv2

    frame = _add_leaf(_frame())
    cv2.circle(frame, (160, 160), 25, BROWN, thickness=-1)

    leaf = segment_leaf(frame, get_settings())

    assert leaf.mask[160, 160], "the lesion was excluded from the leaf"
    assert leaf.mask[160, 175]
    # And the area is still the whole leaf, not the leaf minus the lesion.
    assert 15_000 < leaf.area_px < 19_000


def test_the_crop_is_the_leaf_and_nothing_much_else() -> None:
    leaf = segment_leaf(_add_leaf(_frame()), get_settings())

    x, y, width, height = leaf.bbox
    assert 150 < width < 200 and 100 < height < 140
    assert leaf.crop.shape == (height, width, 3)
    assert leaf.crop.dtype == np.uint8


def test_the_largest_leaf_wins_when_two_are_in_frame() -> None:
    frame = _add_leaf(_frame(), centre=(90, 90), axes=(30, 20))
    frame = _add_leaf(frame, centre=(220, 220), axes=(80, 55))

    leaf = segment_leaf(frame, get_settings())

    assert leaf.mask[220, 220]
    assert not leaf.mask[90, 90]


def test_a_frame_with_no_leaf_falls_back_to_the_whole_image() -> None:
    # A macro shot can fill the frame, and a grey test card has no green at
    # all. Refusing to answer would be worse than analysing the whole frame
    # and saying that is what happened.
    leaf = segment_leaf(_frame(), get_settings())

    assert leaf.fallback is True
    assert leaf.area_px == 320 * 320
    assert leaf.mask.all()


def test_a_leaf_filling_the_frame_is_not_treated_as_a_failure() -> None:
    frame = np.full((256, 256, 3), LEAF_GREEN, dtype=np.uint8)

    leaf = segment_leaf(frame, get_settings())

    assert leaf.fallback is False
    assert leaf.area_px > 256 * 256 * 0.9


# The vegetation fraction, which is a different question from stage 2 and has
# its own test for the reason it exists: the corpus contains real leaves that
# stage 2's absolute rule scores at zero.

DARK_LEAF = (31, 40, 33)  # measured from a Mendeley photograph
LILAC = (199, 176, 232)  # the backdrop those photographs are taken on
SKIN = (198, 152, 124)


def _solid(colour, size: int = 64) -> np.ndarray:
    return np.full((size, size, 3), colour, dtype=np.uint8)


def test_a_sunlit_leaf_is_all_vegetation() -> None:
    assert vegetation_fraction(_solid(LEAF_GREEN), get_settings()) == 1.0


def test_a_dark_leaf_is_vegetation_even_though_stage_two_cannot_see_it() -> None:
    """The case the whole function exists for.

    A third of the corpus is dark leaves on a lilac backdrop. Stage 2's
    absolute excess-green floor scores them at zero, so a threshold built on
    that rule would refuse real labelled leaves. Normalising by intensity is
    what makes a floor above zero possible at all.
    """
    settings = get_settings()

    assert vegetation_fraction(_solid(DARK_LEAF), settings) == 1.0
    assert plant_fraction_of(_solid(DARK_LEAF), settings) == 0.0


def plant_fraction_of(rgb: np.ndarray, settings) -> float:
    """Stage 2's rule as a bare ratio, for the contrast above only."""
    from app.services.segment import _green_mask

    return float(_green_mask(rgb, settings).mean())


def test_neither_the_backdrop_nor_a_hand_counts_as_vegetation() -> None:
    settings = get_settings()

    assert vegetation_fraction(_solid(LILAC), settings) == 0.0
    assert vegetation_fraction(_solid(SKIN), settings) == 0.0
    assert vegetation_fraction(_solid(SOIL), settings) == 0.0


def test_the_fraction_is_measured_against_the_whole_frame() -> None:
    frame = _solid(SOIL, size=64)
    frame[:32, :, :] = LEAF_GREEN

    assert vegetation_fraction(frame, get_settings()) == 0.5


def test_the_index_floor_comes_from_settings() -> None:
    """Served to the browser, so it cannot be a literal in either copy."""
    settings = get_settings()
    strict = settings.model_copy(update={"veg_index_min": 0.9})

    assert vegetation_fraction(_solid(LEAF_GREEN), strict) == 0.0
