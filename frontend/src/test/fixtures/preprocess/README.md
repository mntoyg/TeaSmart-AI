# Preprocessing parity fixtures

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
3. compare against `expected`, a lossless PNG of what PIL produces.

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
