import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { pixelByte, resizeToSquare, sourceImage } from './resize';

/**
 * The browser side of the preprocessing contract.
 *
 * The model was trained on PIL output, so PIL is the definition and this side
 * has to match it. `src/test/fixtures/preprocess/` holds that definition:
 * sources both languages can build from a seed, and the exact bytes PIL
 * produces. The Python suite checks the server against the same files.
 *
 * Rebuild them with `cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli fixtures`.
 */

type Case = {
  name: string;
  source: { width: number; height: number; pattern: string; seed: number };
  reduction: number;
  expected: string;
};

type Manifest = {
  size: [number, number];
  tolerance: { max: number; mean: number };
  generator: { hash_x: number; hash_y: number; hash_c: number; mix_1: number; mix_2: number };
  cases: Case[];
};

const FIXTURES = join(__dirname, '../test/fixtures/preprocess');
const manifest: Manifest = JSON.parse(readFileSync(join(FIXTURES, 'manifest.json'), 'utf8'));

function expectedBytes(entry: Case, size: number): Uint8Array {
  const raw = readFileSync(join(FIXTURES, entry.expected));
  expect(raw.length).toBe(size * size * 3);
  return new Uint8Array(raw.buffer, raw.byteOffset, raw.length);
}

describe('the coordinate hash both languages generate sources from', () => {
  it('is a pure function of the coordinates, so cropping cannot change it', () => {
    const g = manifest.generator;
    const a = pixelByte(99, 7, 11, 2, g);
    const b = pixelByte(99, 7, 11, 2, g);
    expect(a).toBe(b);
    expect(pixelByte(100, 7, 11, 2, g)).not.toBe(a);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThanOrEqual(255);
  });

  it('covers the byte range rather than clustering', () => {
    const g = manifest.generator;
    const values: number[] = [];
    for (let y = 0; y < 48; y++) {
      for (let x = 0; x < 48; x++) values.push(pixelByte(7, y, x, 0, g));
    }
    const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
    expect(Math.min(...values)).toBeLessThan(6);
    expect(Math.max(...values)).toBeGreaterThan(249);
    expect(mean).toBeGreaterThan(118);
    expect(mean).toBeLessThan(138);
  });
});

describe('resizeToSquare matches PIL', () => {
  const size = manifest.size[0];

  it.each(manifest.cases.map((entry) => [entry.name, entry] as const))(
    '%s',
    (_name, entry) => {
      const source = sourceImage(entry.source, manifest.generator);
      const produced = resizeToSquare(source, entry.source.width, entry.source.height, size);
      const expectedPixels = expectedBytes(entry, size);

      expect(produced.length).toBe(expectedPixels.length);

      let worst = 0;
      let total = 0;
      for (let i = 0; i < produced.length; i++) {
        const delta = Math.abs(produced[i] - expectedPixels[i]);
        if (delta > worst) worst = delta;
        total += delta;
      }
      const mean = total / produced.length;

      expect(worst).toBeLessThanOrEqual(manifest.tolerance.max);
      expect(mean).toBeLessThanOrEqual(manifest.tolerance.mean);
    },
  );

  it('fails loudly on the naive four-neighbour resize it replaced', () => {
    // The mutation check. If a 2x2 sampler could pass these fixtures, they
    // would not be testing the thing they were built for: the filter widening
    // with the reduction factor.
    const entry = manifest.cases.find((c) => c.reduction > 10);
    expect(entry, 'a large-reduction case must exist').toBeDefined();
    const { width, height } = entry!.source;
    const source = sourceImage(entry!.source, manifest.generator);
    const expectedPixels = expectedBytes(entry!, size);

    const naive = new Uint8Array(size * size * 3);
    for (let y = 0; y < size; y++) {
      const sy = Math.max(0, Math.min(height - 1, ((y + 0.5) * height) / size - 0.5));
      const y0 = Math.floor(sy);
      const y1 = Math.min(y0 + 1, height - 1);
      const dy = sy - y0;
      for (let x = 0; x < size; x++) {
        const sx = Math.max(0, Math.min(width - 1, ((x + 0.5) * width) / size - 0.5));
        const x0 = Math.floor(sx);
        const x1 = Math.min(x0 + 1, width - 1);
        const dx = sx - x0;
        for (let c = 0; c < 3; c++) {
          const at = (yy: number, xx: number) => source[(yy * width + xx) * 3 + c];
          const top = at(y0, x0) * (1 - dx) + at(y0, x1) * dx;
          const bottom = at(y1, x0) * (1 - dx) + at(y1, x1) * dx;
          naive[(y * size + x) * 3 + c] = Math.round(top * (1 - dy) + bottom * dy);
        }
      }
    }

    let worst = 0;
    for (let i = 0; i < naive.length; i++) {
      worst = Math.max(worst, Math.abs(naive[i] - expectedPixels[i]));
    }
    expect(worst).toBeGreaterThan(30);
  });

  it('widens its filter with the reduction factor', () => {
    // The property the whole fix is about, stated directly rather than only
    // implied by the fixtures: a single bright source row must still show up
    // after a large reduction, because the filter averages over it. A 2x2
    // sampler misses it entirely unless it happens to land on it.
    const width = 2048;
    const height = 2048;
    const source = new Uint8Array(width * height * 3);
    const brightRow = 1001; // not aligned to any output centre
    for (let x = 0; x < width; x++) {
      for (let c = 0; c < 3; c++) source[(brightRow * width + x) * 3 + c] = 255;
    }

    const produced = resizeToSquare(source, width, height, size);
    const rowSums = Array.from({ length: size }, (_, y) => {
      let sum = 0;
      for (let x = 0; x < size; x++) sum += produced[(y * size + x) * 3];
      return sum;
    });

    expect(Math.max(...rowSums)).toBeGreaterThan(0);
  });

  it('stretches rather than cropping, as the contract requires', () => {
    const width = 400;
    const height = 100;
    const source = new Uint8Array(width * height * 3);
    for (let y = 0; y < height; y++) {
      for (let x = width - 40; x < width; x++) {
        for (let c = 0; c < 3; c++) source[(y * width + x) * 3 + c] = 255;
      }
    }

    const produced = resizeToSquare(source, width, height, size);
    const rightEdge = produced[(10 * size + size - 1) * 3];
    const middle = produced[(10 * size + Math.floor(size / 2)) * 3];

    expect(rightEdge).toBeGreaterThan(200);
    expect(middle).toBeLessThan(40);
  });

  it('refuses an array that does not match the dimensions', () => {
    expect(() => resizeToSquare(new Uint8Array(10), 4, 4, size)).toThrow();
  });
});
