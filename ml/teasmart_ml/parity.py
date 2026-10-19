"""Cross-language preprocessing fixtures for the browser.

Spec 8.4 says "resize to 224x224, bilinear". That was underspecified, and the
two sides implemented different things:

- Python calls PIL `Image.resize(..., BILINEAR)`, whose triangle filter support
  widens with the reduction factor. Downscaling 4160 to 224 averages roughly
  nineteen source rows per output row.
- The browser samples the four nearest neighbours, which at that reduction is
  very nearly point sampling.

Measured over twelve corpus images, the two differ by up to 101 of 255 in a
channel, worst on a 3120x4160 phone photograph - the input the demo uses.

**Python is the side that cannot change**: the classifier was trained on PIL
output, so PIL is the definition and the browser has to match it. These fixtures
publish the definition in a form a Vitest suite can check without a Python
process: a source image both languages can generate from a seed, and the
expected 224x224 result as a lossless PNG.

The algorithm the browser must implement is in the generated README.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = (224, 224)

# Source pixels come from a 32-bit coordinate hash rather than a sequential
# generator, so that neither language can disagree about stream order: every
# pixel is a pure function of (x, y, channel, seed). All multiplies truncate to
# 32 bits, which is `Math.imul` in JavaScript followed by `>>> 0`.
HASH_X = 374761393
HASH_Y = 668265263
HASH_C = 2246822519
HASH_MIX_1 = 2246822519
HASH_MIX_2 = 3266489917

# Per-channel tolerance against the fixture. Pillow resizes uint8 with
# fixed-point integer coefficients, so a float implementation will not be
# bit-identical; one level of rounding either way is expected and harmless. The
# naive four-neighbour resize misses by thirty or more, so this is loose enough
# to be implementable and tight enough to catch the real defect.
TOLERANCE_MAX = 2.0
TOLERANCE_MEAN = 0.30


@dataclass(frozen=True)
class FixtureCase:
    name: str
    width: int
    height: int
    pattern: str
    seed: int


FIXTURE_CASES: tuple[FixtureCase, ...] = (
    # A phone photograph, portrait, 18.6x reduction. The demo case and the worst
    # case; noise is the hardest content for a resampler to agree on.
    FixtureCase("phone-noise-3120x4160", 3120, 4160, "noise", 12345),
    # The yunusserhat corpus shape, 4.6x.
    FixtureCase("corpus-noise-768x1024", 768, 1024, "noise", 777),
    # The mendeley corpus shape, square, 2.9x.
    FixtureCase("corpus-blocks-640x640", 640, 640, "blocks", 4242),
    # Landscape, non-square: catches an implementation that preserves aspect
    # ratio, which the contract says it must not.
    FixtureCase("landscape-gradient-1920x1080", 1920, 1080, "gradient", 31337),
    # The agml corpus shape, 1.14x. Barely a reduction, where the two
    # implementations genuinely do agree - included so the suite proves the
    # fixtures are not simply strict everywhere.
    FixtureCase("corpus-noise-256x256", 256, 256, "noise", 99),
)


def _mix(value: np.ndarray) -> np.ndarray:
    """The 32-bit avalanche. Every step is expressible with Math.imul."""
    mask = np.uint64(0xFFFFFFFF)
    value = value.astype(np.uint64) & mask
    value = (value ^ (value >> np.uint64(15))) * np.uint64(HASH_MIX_1) & mask
    value = (value ^ (value >> np.uint64(13))) * np.uint64(HASH_MIX_2) & mask
    return value ^ (value >> np.uint64(16))


def pixel_bytes(seed: int, height: int, width: int, channels: int = 3) -> np.ndarray:
    """Hash-derived bytes for every (y, x, channel), shaped (h, w, c).

    Order-free by construction: pixel (y, x, c) does not depend on any other
    pixel, so a browser implementation cannot get the sequence wrong - only the
    arithmetic, which the fixtures check.
    """
    mask = np.uint64(0xFFFFFFFF)
    y = np.arange(height, dtype=np.uint64).reshape(height, 1, 1)
    x = np.arange(width, dtype=np.uint64).reshape(1, width, 1)
    c = np.arange(channels, dtype=np.uint64).reshape(1, 1, channels)

    value = (
        np.uint64(seed)
        ^ (x * np.uint64(HASH_X) & mask)
        ^ (y * np.uint64(HASH_Y) & mask)
        ^ (c * np.uint64(HASH_C) & mask)
    ) & mask
    return (_mix(value) >> np.uint64(24)).astype(np.uint8)


def generate_source(case: FixtureCase) -> np.ndarray:
    """Build a case's source image. Must be reproducible in JavaScript."""
    height, width = case.height, case.width

    if case.pattern == "noise":
        return pixel_bytes(case.seed, height, width)

    if case.pattern == "gradient":
        # Smooth and separable: red rises with x, green with y, blue is their
        # mean. Integer arithmetic only, so there is nothing to round.
        x = (np.arange(width, dtype=np.uint32) * 255 // max(width - 1, 1)).astype(
            np.uint16
        )
        y = (np.arange(height, dtype=np.uint32) * 255 // max(height - 1, 1)).astype(
            np.uint16
        )
        red = np.broadcast_to(x[None, :], (height, width))
        green = np.broadcast_to(y[:, None], (height, width))
        blue = (red.astype(np.uint16) + green.astype(np.uint16)) // 2
        return np.stack([red, green, blue], axis=-1).astype(np.uint8)

    if case.pattern == "blocks":
        # 8x8 blocks of flat colour from the hash: hard edges at known positions,
        # which is where a resampler disagreement is largest and most visible.
        blocks = pixel_bytes(case.seed, 8, 8)
        rows = np.arange(height) * 8 // height
        cols = np.arange(width) * 8 // width
        return blocks[rows[:, None], cols[None, :]]

    raise ValueError(f"unknown pattern {case.pattern!r}")


def reference_resize(source: np.ndarray) -> np.ndarray:
    """The definition: PIL bilinear to 224x224, aspect ratio not preserved.

    This is step 2 of spec 8.4 and the only step the two sides disagree on.
    Steps 3 to 5 are three multiplies per channel.
    """
    with Image.fromarray(source, mode="RGB") as image:
        return np.asarray(image.resize(SIZE, resample=Image.BILINEAR))


def naive_bilinear(source: np.ndarray) -> np.ndarray:
    """What the browser does today, for the test that proves fixtures bite.

    Four nearest neighbours with a half-pixel centre offset - a direct
    transcription of frontend/src/lib/inference.ts. Correct for upscaling and
    for small reductions; at a 10x reduction it is point sampling.
    """
    height, width, _ = source.shape
    out = np.empty((*SIZE, 3), dtype=np.uint8)
    pixels = source.astype(np.float64)
    for y in range(SIZE[1]):
        sy = min(max((y + 0.5) * height / SIZE[1] - 0.5, 0.0), height - 1)
        y0 = int(np.floor(sy))
        y1 = min(y0 + 1, height - 1)
        dy = sy - y0
        for x in range(SIZE[0]):
            sx = min(max((x + 0.5) * width / SIZE[0] - 0.5, 0.0), width - 1)
            x0 = int(np.floor(sx))
            x1 = min(x0 + 1, width - 1)
            dx = sx - x0
            top = pixels[y0, x0] * (1 - dx) + pixels[y0, x1] * dx
            bottom = pixels[y1, x0] * (1 - dx) + pixels[y1, x1] * dx
            out[y, x] = np.round(top * (1 - dy) + bottom * dy).astype(np.uint8)
    return out


_README = """# Preprocessing parity fixtures

**Generated. Do not edit by hand.** Rebuild with:

```
cd ml && ./.venv/Scripts/python.exe -m teasmart_ml.cli fixtures
```

## Why these exist

Spec section 8.4 says "resize to 224x224, bilinear". That was underspecified,
and the two sides of the contract implemented different things. Measured over
twelve corpus images, they differ by up to **101 of 255** in a channel, worst on
a full-resolution phone photograph - which is the input the demo uses.

**Python cannot move.** The classifier was trained on PIL output, so PIL is the
definition. These fixtures publish it.

## What to do with them

For each case in `manifest.json`:

1. build the source image from `source` (see the generators below),
2. resize it to 224x224 with the algorithm below,
3. compare against `expected`: raw RGB bytes, row-major, channel last, so
   `expected[(y * 224 + x) * 3 + c]`. 224*224*3 = 150,528 bytes, no decoder
   needed on either side.

Pass when **every channel is within `tolerance.max`** and the **mean absolute
difference is within `tolerance.mean`**. Pillow uses fixed-point integer
coefficients, so a float implementation will not be bit-identical; one level of
rounding is fine. The current four-neighbour implementation misses by thirty or
more, so there is no risk of a wrong implementation sneaking through.

## The algorithm: PIL bilinear, which is a scaled triangle filter

The part everyone gets wrong is that **the filter widens when you downscale**.
Separable, so do it in two passes - horizontal, then vertical.

For one axis, with `inSize` source pixels and `outSize` output pixels:

```
scale   = inSize / outSize
support = scale > 1 ? scale : 1.0        // THIS is the step that is missed
```

For each output index `i`:

```
centre = (i + 0.5) * scale
start  = max(0, floor(centre - support + 0.5))
stop   = min(inSize, ceil(centre + support + 0.5))

for j in [start, stop):
    // triangle filter, argument normalised by the support
    t = abs((j + 0.5 - centre) / support)
    w = t < 1.0 ? 1.0 - t : 0.0
    weights.push(w)

normalise weights so they sum to 1
output[i] = sum(weights[k] * input[start + k])
```

Clamp to `[0, 255]` and round half away from zero only at the very end, after
both passes. Keep the intermediate pass in float.

When `scale <= 1` (upscaling, or the 256x256 case) `support` is 1.0 and this
reduces to ordinary bilinear, which is why the small case already agrees.

## The source generators

A seed rather than a committed JPEG, so the fixture set stays small. Pixels come
from a **coordinate hash**, not a sequential generator: pixel `(y, x, c)` is a
pure function of its own coordinates, so there is no stream order for the two
languages to disagree about.

Every multiply truncates to 32 bits. In JavaScript that is `Math.imul` followed
by `>>> 0`; shifts must be the unsigned `>>>`.

```js
function pixelByte(seed, y, x, c) {
  let v = (seed ^ Math.imul(x, HASH_X) ^ Math.imul(y, HASH_Y) ^ Math.imul(c, HASH_C)) >>> 0;
  v = Math.imul(v ^ (v >>> 15), MIX_1) >>> 0;
  v = Math.imul(v ^ (v >>> 13), MIX_2) >>> 0;
  v = (v ^ (v >>> 16)) >>> 0;
  return v >>> 24;
}
```

Constants are in `manifest.json` under `generator`.

- **`noise`** - `source[y][x][c] = pixelByte(seed, y, x, c)`.
- **`gradient`** - integers only, no rounding to disagree about:
  `red = Math.floor(x * 255 / (width - 1))`,
  `green = Math.floor(y * 255 / (height - 1))`, `blue = (red + green) >> 1`.
- **`blocks`** - build an 8x8x3 block of `pixelByte(seed, by, bx, c)`, then
  `source[y][x] = block[Math.floor(y * 8 / height)][Math.floor(x * 8 / width)]`.

## Cases

The reduction factor is what matters; the set spans 1.14x to 18.6x on purpose.
A fixture set of small images would have shipped the bug.
"""


def write_fixtures(out_dir: Path) -> Path:
    """Write every case plus a manifest, and return the manifest path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = []
    for case in FIXTURE_CASES:
        expected = reference_resize(generate_source(case))
        # Raw RGB bytes rather than a PNG. The Vitest suite has to read these,
        # and a decoder would be a dependency added to the frontend for the
        # sake of a test fixture. 224*224*3 is 147 KB, which is a fair price
        # for both sides reading the file with no library at all.
        filename = f"{case.name}.bin"
        (out_dir / filename).write_bytes(
            np.ascontiguousarray(expected, dtype=np.uint8).tobytes()
        )
        cases.append(
            {
                "name": case.name,
                "source": {
                    "width": case.width,
                    "height": case.height,
                    "pattern": case.pattern,
                    "seed": case.seed,
                },
                "reduction": round(max(case.width, case.height) / SIZE[0], 2),
                "expected": filename,
            }
        )

    manifest = {
        "note": (
            "Generated by ml/teasmart_ml/parity.py. PIL bilinear is the "
            "definition because the model was trained on it. See README.md."
        ),
        "size": list(SIZE),
        "tolerance": {"max": TOLERANCE_MAX, "mean": TOLERANCE_MEAN},
        "generator": {
            "kind": "coord-hash-32",
            "hash_x": HASH_X,
            "hash_y": HASH_Y,
            "hash_c": HASH_C,
            "mix_1": HASH_MIX_1,
            "mix_2": HASH_MIX_2,
            "output": "top 8 bits of the mixed value",
        },
        "cases": cases,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(_README, encoding="utf-8")
    return manifest_path
