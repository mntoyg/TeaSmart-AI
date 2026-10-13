import type { ClientConfig, ScanResponse } from './scan-contract';

export function preprocess(rgb: Uint8Array, width: number, height: number, config: ClientConfig): Float32Array {
  const size = config.preprocessing.size[0], mean = config.preprocessing.mean, standardDeviation = config.preprocessing.std;
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || rgb.length !== width * height * 3) {
    throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  }
  const output = new Float32Array(3 * size * size);
  for (let y = 0; y < size; y++) {
    const sy = Math.max(0, Math.min(height - 1, (y + 0.5) * height / size - 0.5));
    const y0 = Math.floor(sy), y1 = Math.min(y0 + 1, height - 1), dy = sy - y0;
    for (let x = 0; x < size; x++) {
      const sx = Math.max(0, Math.min(width - 1, (x + 0.5) * width / size - 0.5));
      const x0 = Math.floor(sx), x1 = Math.min(x0 + 1, width - 1), dx = sx - x0;
      for (let channel = 0; channel < 3; channel++) {
        const sample = (xx: number, yy: number) => rgb[(yy * width + xx) * 3 + channel];
        const top = sample(x0, y0) * (1 - dx) + sample(x1, y0) * dx;
        const bottom = sample(x0, y1) * (1 - dx) + sample(x1, y1) * dx;
        const pixel = Math.round(top * (1 - dy) + bottom * dy);
        output[channel * size * size + y * size + x] = (pixel / config.preprocessing.scale - mean[channel]) / standardDeviation[channel];
      }
    }
  }
  return output;
}
export function classifyLogits(logits: Float32Array, config: ClientConfig): ScanResponse['prediction'] {
  const classes = config.class_order, minConfidence = config.min_confidence;
  if (logits.length !== classes.length || !Array.from(logits).every(Number.isFinite)
    || !Number.isFinite(minConfidence) || minConfidence < 0 || minConfidence > 1) throw new Error('ข้อมูลโมเดลไม่ถูกต้อง');
  const maximum = Math.max(...logits);
  const exponentials = Array.from(logits, (logit) => Math.exp(logit - maximum));
  const total = exponentials.reduce((sum, value) => sum + value, 0);
  const top = exponentials.map((value, index) => ({ class_name: classes[index], confidence: value / total }))
    .sort((a, b) => b.confidence - a.confidence);
  const lowConfidence = top[0].confidence < minConfidence;
  const className = lowConfidence ? 'other_disease' : top[0].class_name;
  return { class_name: className, class_id: classes.indexOf(className), confidence: top[0].confidence,
    low_confidence: lowConfidence, top_k: top.slice(0, 3) };
}
export async function runClassifier(rgb: Uint8Array, width: number, height: number, config: ClientConfig,
  runner: (input: Float32Array) => Promise<Float32Array>) {
  return classifyLogits(await runner(preprocess(rgb, width, height, config)), config);
}
