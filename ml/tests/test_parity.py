"""The cross-language preprocessing fixtures.

These exist because the two sides of spec 8.4 disagree today. Python resizes
with PIL, whose bilinear filter widens with the reduction factor; the browser
samples four neighbours. On a 3120x4160 phone photograph - the case the demo
uses - that is a difference of up to 101 of 255 in a channel.

Python is the side that cannot move: the model was trained on PIL output. So
these fixtures publish what PIL produces, and the browser is measured against
them.

A fixture that a wrong implementation would also pass is worthless, so the
important test here is the one asserting the naive four-neighbour resize fails.
"""

import json

import numpy as np
import pytest
from PIL import Image

from teasmart_ml.parity import (
    FIXTURE_CASES,
    HASH_C,
    HASH_MIX_1,
    HASH_MIX_2,
    HASH_X,
    HASH_Y,
    TOLERANCE_MAX,
    TOLERANCE_MEAN,
    generate_source,
    naive_bilinear,
    pixel_bytes,
    reference_resize,
    write_fixtures,
)


def test_pixel_hash_matches_the_arithmetic_the_browser_has_to_use() -> None:
    # Written out longhand rather than compared against a literal, so the
    # constants, the shifts and the 32-bit truncation are the thing under test.
    # Each step is one Math.imul followed by >>> 0 in JavaScript.
    mask = 0xFFFFFFFF

    def expected(seed: int, y: int, x: int, c: int) -> int:
        value = (
            seed
            ^ (x * HASH_X & mask)
            ^ (y * HASH_Y & mask)
            ^ (c * HASH_C & mask)
        ) & mask
        value = (value ^ (value >> 15)) * HASH_MIX_1 & mask
        value = (value ^ (value >> 13)) * HASH_MIX_2 & mask
        return ((value ^ (value >> 16)) & mask) >> 24

    out = pixel_bytes(12345, 3, 4)
    for y in range(3):
        for x in range(4):
            for c in range(3):
                assert out[y, x, c] == expected(12345, y, x, c), (y, x, c)


def test_pixel_hash_is_order_free_and_covers_the_byte_range() -> None:
    # Order-free is the point: a pixel depends on its own coordinates only, so
    # a cropped or differently iterated implementation still gets the same
    # bytes. A sequential generator would not have that property.
    full = pixel_bytes(7, 64, 64)
    assert np.array_equal(full, pixel_bytes(7, 64, 64))
    assert np.array_equal(full[:8, :8], pixel_bytes(7, 8, 8))
    assert not np.array_equal(full, pixel_bytes(8, 64, 64))
    assert full.min() < 4 and full.max() > 251
    assert 120 < full.mean() < 136


@pytest.mark.parametrize("case", FIXTURE_CASES, ids=lambda case: case.name)
def test_every_case_generates_the_shape_it_declares(case) -> None:
    source = generate_source(case)
    assert source.shape == (case.height, case.width, 3)
    assert source.dtype == np.uint8


def test_reference_resize_is_the_eval_transform_before_normalisation() -> None:
    # The fixtures pin the resize, not the normalisation: the normalisation is
    # three multiplies that nobody gets wrong, and pinning uint8 keeps the
    # fixture a 150 KB image instead of a 600 KB float dump.
    from teasmart_ml.transforms import IMAGENET_MEAN, IMAGENET_STD, eval_array

    source = generate_source(FIXTURE_CASES[0])
    resized = reference_resize(source)
    normalised = eval_array(Image.fromarray(source))

    undone = np.stack(
        [
            (normalised[channel] * IMAGENET_STD[channel] + IMAGENET_MEAN[channel])
            * 255.0
            for channel in range(3)
        ]
    )
    assert np.abs(undone - resized.transpose(2, 0, 1)).max() < 0.51


def test_the_naive_four_neighbour_resize_fails_the_fixtures() -> None:
    """The mutation check: a wrong implementation must not pass.

    If this ever starts passing, the fixtures have stopped testing anything and
    the tolerance is too loose to catch the defect they were built for.

    Only the high-frequency patterns discriminate, and that is worth knowing: a
    smooth test image agrees to within one level however wide the filter is,
    because averaging a linear ramp gives its midpoint. A fixture set built
    from gradients would have certified the bug as fixed.
    """
    worst = 0.0
    discriminating = 0
    for case in FIXTURE_CASES:
        source = generate_source(case)
        difference = np.abs(
            reference_resize(source).astype(np.float32)
            - naive_bilinear(source).astype(np.float32)
        )
        if case.pattern == "gradient":
            assert difference.max() <= 1.0, "a gradient should not discriminate"
            continue
        if max(case.width, case.height) <= 448:
            continue  # small reductions genuinely do agree; nothing to catch
        assert difference.max() > TOLERANCE_MAX, case.name
        assert difference.mean() > TOLERANCE_MEAN, case.name
        worst = max(worst, float(difference.max()))
        discriminating += 1

    assert discriminating >= 2
    # The number that made this a P0 rather than a style note.
    assert worst > 30.0


def test_write_fixtures_emits_a_manifest_and_exact_bytes(tmp_path) -> None:
    manifest_path = write_fixtures(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["size"] == [224, 224]
    assert manifest["tolerance"] == {"max": TOLERANCE_MAX, "mean": TOLERANCE_MEAN}
    assert manifest["generator"]["hash_x"] == HASH_X
    assert manifest["generator"]["mix_2"] == HASH_MIX_2
    assert len(manifest["cases"]) == len(FIXTURE_CASES)

    for entry, case in zip(manifest["cases"], FIXTURE_CASES, strict=False):
        assert entry["name"] == case.name
        assert entry["source"] == {
            "width": case.width,
            "height": case.height,
            "pattern": case.pattern,
            "seed": case.seed,
        }
        raw = (tmp_path / entry["expected"]).read_bytes()
        assert len(raw) == 224 * 224 * 3
        stored = np.frombuffer(raw, dtype=np.uint8).reshape(224, 224, 3)
        # Raw bytes, so the stored fixture must be bit-identical to what the
        # reference produces. Anything else means the fixture drifted.
        assert np.array_equal(stored, reference_resize(generate_source(case)))


def test_fixtures_cover_a_phone_sized_reduction(tmp_path) -> None:
    # The defect is proportional to the reduction factor, so a fixture set made
    # only of small images would have shipped the bug.
    reductions = [max(case.width, case.height) / 224 for case in FIXTURE_CASES]
    assert max(reductions) > 10.0
    assert min(reductions) < 1.5
