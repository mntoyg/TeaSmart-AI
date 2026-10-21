import { expect, it } from 'vitest';
import { assessQuality } from './quality';
import { configShape } from './scan-contract';
const settings = configShape.quality;
it('reports exposure before blur and distinguishes dark from bright frames', () => {
  expect(assessQuality(new Uint8Array(3 * 4 * 4), 4, 4, settings).detail_th).toContain('มืด');
  expect(assessQuality(new Uint8Array(3 * 4 * 4).fill(255), 4, 4, settings).detail_th).toContain('สว่าง');
  expect(assessQuality(new Uint8Array(3 * 4 * 4).fill(100), 4, 4, settings).detail_th).toContain('เบลอ');
});
it('matches an independently computed reflected-border Laplacian and RGB clipping', () => {
  const rgb = new Uint8Array([50,50,50, 150,150,150, 150,150,150, 50,50,50]);
  const result = assessQuality(rgb, 2, 2, settings);
  expect(result.blur_score).toBe(160000);
  expect(result.exposure_mean).toBe(100);
  expect(result.passed).toBe(true);
  expect(result.clipped_low_pct).toBe(0);
});
it('counts clipping per RGB channel, even when mean gray looks acceptable', () => {
  const image = new Uint8Array(12).fill(100); image[0] = 255; image[3] = 255;
  const result = assessQuality(image, 2, 2, settings);
  expect(result.clipped_high_pct).toBeGreaterThan(settings.clip_max_pct);
  expect(result.passed).toBe(true);
});
it('reports bright clipping without rejecting a frame whose exposure is acceptable', () => {
  const image = new Uint8Array(3 * 4 * 4).fill(100);
  image.fill(255, 0, 6);
  const result = assessQuality(image, 4, 4, { ...settings, blur_threshold: 0 });
  expect(result.passed).toBe(true);
  expect(result.clipped_high_pct).toBeGreaterThan(settings.clip_max_pct);
  expect(result.detail_th).toBeUndefined();
});
