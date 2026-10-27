import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, it } from 'vitest';
import { assessVegetation } from './leaf';
import { configShape } from './scan-contract';

/**
 * The expected fractions come from `scripts/make_leaf_fixtures.py`, which runs
 * the same images through `vegetation_fraction` in `backend/app/services/segment.py`.
 * Two of the nine cases sit a thousandth apart on either side of the floor, so a
 * port that rounds, or that compares with `>=`, fails here rather than in a field.
 */
type FixtureCase = {
  name: string;
  why: string;
  width: number;
  height: number;
  rgb: number[];
  fraction: number;
};

const fixture: { settings: { veg_index_min: number }; cases: FixtureCase[] } = JSON.parse(
  readFileSync(join(__dirname, '../test/fixtures/leaf-fraction.json'), 'utf8'),
);
const settings = { ...configShape.leaf, veg_index_min: fixture.settings.veg_index_min };

it('measures the fraction Python measured, for every fixture case', () => {
  expect(fixture.cases).toHaveLength(9);
  for (const entry of fixture.cases) {
    const result = assessVegetation(new Uint8Array(entry.rgb), entry.width, entry.height, settings);
    expect(result.veg_fraction, `${entry.name}: ${entry.why}`).toBeCloseTo(entry.fraction, 6);
  }
});

it('rejects a frame whose green fraction falls below the measured floor', () => {
  const rgb = new Uint8Array(1000 * 3);
  for (let pixel = 0; pixel < 1000; pixel++) rgb.set([92, 74, 62], pixel * 3);
  rgb.set([54, 122, 58], 0);

  const result = assessVegetation(rgb, 1000, 1, settings);

  expect(result.veg_fraction).toBe(0.001);
  expect(result.passed).toBe(false);
  expect(result.detail_th).toBe('ไม่พบใบชาในภาพ กรุณาถ่ายใบชาใบเดียวให้เต็มกรอบ');
});

it('accepts a frame sitting exactly on the floor, because the floor rejects below it', () => {
  const rgb = new Uint8Array(500 * 3);
  for (let pixel = 0; pixel < 500; pixel++) rgb.set([92, 74, 62], pixel * 3);
  rgb.set([54, 122, 58], 0);

  const result = assessVegetation(rgb, 500, 1, settings);

  expect(result.veg_fraction).toBe(settings.min_fraction);
  expect(result.passed).toBe(true);
  expect(result.detail_th).toBeUndefined();
});

it('refuses a buffer whose length disagrees with the frame it claims to be', () => {
  expect(() => assessVegetation(new Uint8Array(11), 2, 2, settings)).toThrow('ข้อมูลภาพไม่ถูกต้อง');
  expect(() => assessVegetation(new Uint8Array(0), 0, 1, settings)).toThrow('ข้อมูลภาพไม่ถูกต้อง');
});
