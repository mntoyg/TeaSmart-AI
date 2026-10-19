/**
 * PIL-compatible resizing, because the model was trained on PIL output.
 *
 * The browser used to sample the four nearest neighbours. PIL scales its
 * triangle filter's support by the reduction factor, so going from 4160 px to
 * 224 averages roughly nineteen source rows per output row while four-neighbour
 * sampling at that reduction is very nearly point sampling. Measured over
 * twelve corpus images the two differed by up to 101 of 255 in a channel, worst
 * on a full-resolution phone photograph, which is the input the demo uses.
 *
 * Python cannot move: the classifier learned on PIL's output. So this side
 * matches PIL, and `src/test/fixtures/preprocess/` holds the bytes it has to
 * reproduce.
 */

const TRIANGLE_SUPPORT = 1.0;

export type HashConstants = {
  hash_x: number;
  hash_y: number;
  hash_c: number;
  mix_1: number;
  mix_2: number;
};

export type SourceSpec = {
  width: number;
  height: number;
  pattern: string;
  seed: number;
};

/**
 * One byte of a fixture source, from its coordinates alone.
 *
 * A coordinate hash rather than a sequential generator, so neither language can
 * disagree about stream order: only about the arithmetic, which is what the
 * fixtures check. Every multiply truncates to 32 bits, which is `Math.imul`.
 */
export function pixelByte(
  seed: number,
  y: number,
  x: number,
  c: number,
  constants: HashConstants,
): number {
  let value =
    (seed ^ Math.imul(x, constants.hash_x) ^ Math.imul(y, constants.hash_y) ^
      Math.imul(c, constants.hash_c)) >>> 0;
  value = Math.imul(value ^ (value >>> 15), constants.mix_1) >>> 0;
  value = Math.imul(value ^ (value >>> 13), constants.mix_2) >>> 0;
  return ((value ^ (value >>> 16)) >>> 0) >>> 24;
}

/** Rebuild a fixture source image. Test-only; the app never calls this. */
export function sourceImage(spec: SourceSpec, constants: HashConstants): Uint8Array {
  const { width, height, pattern, seed } = spec;
  const out = new Uint8Array(width * height * 3);

  if (pattern === 'noise') {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const base = (y * width + x) * 3;
        for (let c = 0; c < 3; c++) out[base + c] = pixelByte(seed, y, x, c, constants);
      }
    }
    return out;
  }

  if (pattern === 'gradient') {
    for (let y = 0; y < height; y++) {
      const green = Math.floor((y * 255) / Math.max(height - 1, 1));
      for (let x = 0; x < width; x++) {
        const red = Math.floor((x * 255) / Math.max(width - 1, 1));
        const base = (y * width + x) * 3;
        out[base] = red;
        out[base + 1] = green;
        out[base + 2] = (red + green) >> 1;
      }
    }
    return out;
  }

  if (pattern === 'blocks') {
    const block = new Uint8Array(8 * 8 * 3);
    for (let by = 0; by < 8; by++) {
      for (let bx = 0; bx < 8; bx++) {
        for (let c = 0; c < 3; c++) {
          block[(by * 8 + bx) * 3 + c] = pixelByte(seed, by, bx, c, constants);
        }
      }
    }
    for (let y = 0; y < height; y++) {
      const by = Math.floor((y * 8) / height);
      for (let x = 0; x < width; x++) {
        const bx = Math.floor((x * 8) / width);
        const base = (y * width + x) * 3;
        const from = (by * 8 + bx) * 3;
        out[base] = block[from];
        out[base + 1] = block[from + 1];
        out[base + 2] = block[from + 2];
      }
    }
    return out;
  }

  throw new Error(`unknown fixture pattern ${pattern}`);
}

type Weights = {
  starts: Int32Array;
  counts: Int32Array;
  values: Float64Array;
  stride: number;
};

/**
 * Filter taps for one axis.
 *
 * `support` is the step everyone misses: it grows with the reduction factor,
 * which is the whole difference between this and ordinary bilinear. When
 * scaling up it stays at 1 and this reduces to ordinary bilinear, which is why
 * the small fixture agreed even before the fix.
 */
function buildWeights(inSize: number, outSize: number): Weights {
  const scale = inSize / outSize;
  const filterScale = scale > 1 ? scale : 1.0;
  const support = TRIANGLE_SUPPORT * filterScale;
  const stride = Math.ceil(support) * 2 + 1;

  const starts = new Int32Array(outSize);
  const counts = new Int32Array(outSize);
  const values = new Float64Array(outSize * stride);

  for (let i = 0; i < outSize; i++) {
    const center = (i + 0.5) * scale;
    const start = Math.max(Math.floor(center - support + 0.5), 0);
    const end = Math.min(Math.floor(center + support + 0.5), inSize);

    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      const distance = Math.abs((j + 0.5 - center) / filterScale);
      const weight = distance < 1.0 ? 1.0 - distance : 0.0;
      values[i * stride + count] = weight;
      sum += weight;
      count++;
    }
    // Normalised so the taps sum to one, which is what keeps a flat region
    // flat rather than drifting with the filter width.
    if (sum !== 0) {
      for (let k = 0; k < count; k++) values[i * stride + k] /= sum;
    }
    starts[i] = start;
    counts[i] = count;
  }

  return { starts, counts, values, stride };
}

function clamp8(value: number): number {
  // Round half away from zero, then clamp, matching Pillow's clip8.
  const rounded = Math.floor(value + 0.5);
  return rounded < 0 ? 0 : rounded > 255 ? 255 : rounded;
}

/**
 * Resize RGB bytes to `size` x `size`, stretching rather than cropping.
 *
 * Two separable passes, horizontal then vertical, in Pillow's order. The
 * intermediate is rounded back to bytes between the passes because Pillow's
 * 8-bit path does the same, and skipping it leaves a visible drift against the
 * fixtures.
 */
export function resizeToSquare(
  rgb: Uint8Array,
  width: number,
  height: number,
  size: number,
): Uint8Array {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) {
    throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  }
  if (rgb.length !== width * height * 3) {
    throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  }

  const horizontal = buildWeights(width, size);
  const afterHorizontal = new Uint8Array(size * height * 3);
  for (let y = 0; y < height; y++) {
    const rowIn = y * width * 3;
    const rowOut = y * size * 3;
    for (let x = 0; x < size; x++) {
      const start = horizontal.starts[x];
      const count = horizontal.counts[x];
      const taps = x * horizontal.stride;
      let r = 0;
      let g = 0;
      let b = 0;
      for (let k = 0; k < count; k++) {
        const weight = horizontal.values[taps + k];
        const at = rowIn + (start + k) * 3;
        r += weight * rgb[at];
        g += weight * rgb[at + 1];
        b += weight * rgb[at + 2];
      }
      const out = rowOut + x * 3;
      afterHorizontal[out] = clamp8(r);
      afterHorizontal[out + 1] = clamp8(g);
      afterHorizontal[out + 2] = clamp8(b);
    }
  }

  const vertical = buildWeights(height, size);
  const result = new Uint8Array(size * size * 3);
  for (let y = 0; y < size; y++) {
    const start = vertical.starts[y];
    const count = vertical.counts[y];
    const taps = y * vertical.stride;
    for (let x = 0; x < size; x++) {
      let r = 0;
      let g = 0;
      let b = 0;
      for (let k = 0; k < count; k++) {
        const weight = vertical.values[taps + k];
        const at = ((start + k) * size + x) * 3;
        r += weight * afterHorizontal[at];
        g += weight * afterHorizontal[at + 1];
        b += weight * afterHorizontal[at + 2];
      }
      const out = (y * size + x) * 3;
      result[out] = clamp8(r);
      result[out + 1] = clamp8(g);
      result[out + 2] = clamp8(b);
    }
  }

  return result;
}
