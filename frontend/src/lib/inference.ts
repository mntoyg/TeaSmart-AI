import { resizeToSquare } from './resize';
import type { ClientConfig, ScanResponse } from './scan-contract';

export function preprocess(rgb: Uint8Array, width: number, height: number, config: ClientConfig): Float32Array {
  const size = config.preprocessing.size[0], mean = config.preprocessing.mean, standardDeviation = config.preprocessing.std;
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || rgb.length !== width * height * 3) {
    throw new Error('ข้อมูลภาพไม่ถูกต้อง');
  }
  // PIL-compatible, because the model was trained on PIL output. The previous
  // version sampled four neighbours, which at a phone photograph's reduction
  // factor is nearly point sampling and differed from Python by up to 101 of
  // 255 in a channel. See resize.ts and src/test/fixtures/preprocess/.
  const resized = resizeToSquare(rgb, width, height, size);
  const output = new Float32Array(3 * size * size);
  const plane = size * size;
  for (let i = 0; i < plane; i++) {
    const at = i * 3;
    for (let channel = 0; channel < 3; channel++) {
      output[channel * plane + i] =
        (resized[at + channel] / config.preprocessing.scale - mean[channel]) / standardDeviation[channel];
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
