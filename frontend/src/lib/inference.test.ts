import { expect, it } from 'vitest';
import { preprocess, classifyLogits, runClassifier } from './inference';
import { configShape } from './scan-contract';

it('normalizes RGB into separate float32 NCHW channels at 224 square', () => {
  const output = preprocess(new Uint8Array([255, 0, 128]), 1, 1, configShape);
  expect(output).toBeInstanceOf(Float32Array);
  expect(output.length).toBe(3 * 224 * 224);
  expect(output[0]).toBeCloseTo((1 - 0.485) / 0.229, 6);
  expect(output[224 * 224]).toBeCloseTo(-0.456 / 0.224, 6);
  expect(output[2 * 224 * 224]).toBeCloseTo((128 / 255 - 0.406) / 0.225, 6);
});
it('resizes with bilinear pixel-center interpolation rather than a nearest-neighbor copy', () => {
  const output = preprocess(new Uint8Array([0, 0, 0, 255, 255, 255]), 2, 1, configShape);
  const x = 112;
  const sourceX = (x + 0.5) * 2 / 224 - 0.5;
  expect(output[x]).toBeCloseTo((Math.round(sourceX * 255) / 255 - 0.485) / 0.229, 6);
});
it('uses stable softmax over the specified five-class order', () => {
  const result = classifyLogits(new Float32Array([1000, 1001, 1002, 1003, 1004]), { ...configShape, min_confidence: 0.5 });
  expect(result.class_name).toBe('other_disease');
  expect(result.low_confidence).toBe(false);
  expect(result.confidence).toBeCloseTo(1 / (1 + Math.exp(-1) + Math.exp(-2) + Math.exp(-3) + Math.exp(-4)), 6);
});
it('downgrades uncertain disease names and flags low confidence', () => {
  const result = classifyLogits(new Float32Array([1, 0, 0, 0, 0]), { ...configShape, min_confidence: 0.8 });
  expect(result.class_name).toBe('other_disease');
  expect(result.class_id).toBe(4);
  expect(result.low_confidence).toBe(true);
  expect(result.top_k[0].class_name).toBe('grey_blight');
});
it.each([new Float32Array([1, 2]), new Float32Array([NaN, 1, 2, 3, 4])])('rejects invalid logits', (logits) => {
  expect(() => classifyLogits(logits, configShape)).toThrow();
});
it('tests a shape-compatible stub runner without shipping fabricated diagnoses', async () => {
  const prediction = await runClassifier(new Uint8Array([20, 120, 30]), 1, 1, configShape, async (input) => {
    expect(input.length).toBe(1 * 3 * 224 * 224);
    return new Float32Array([8, 0, 0, 0, 0]);
  });
  expect(prediction.class_name).toBe('grey_blight');
});
