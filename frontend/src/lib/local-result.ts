import { classes, matches, parseScan } from './api';
import { scanShape, type ScanResponse } from './scan-contract';
export type LocalResult = Pick<ScanResponse, 'scan_id' | 'captured_at' | 'quality' | 'prediction' | 'model_version'> & { analysis_mode: 'classifier_only' };
export type StoredResult = ScanResponse | LocalResult;
export function isFull(result: StoredResult): result is ScanResponse {
  return result.analysis_mode === 'full' && 'burn_analysis' in result;
}
export function parseStored(value: unknown): StoredResult {
  if (typeof value !== 'object' || value === null) throw new Error('ผลวิเคราะห์ไม่ถูกต้อง');
  if ('analysis_mode' in value && value.analysis_mode === 'classifier_only') {
    const shape = { scan_id: '', captured_at: '', quality: scanShape.quality,
      prediction: scanShape.prediction, model_version: '', analysis_mode: '' };
    if (!matches(value, shape)) throw new Error('ผลวิเคราะห์เบื้องต้นไม่ครบถ้วน');
    const result = value as LocalResult;
    if (!result.quality.passed || !result.scan_id || !Number.isFinite(Date.parse(result.captured_at))
      || !classes.includes(result.prediction.class_name as typeof classes[number])
      || !Number.isInteger(result.prediction.class_id) || result.prediction.class_id < 0
      || result.prediction.class_id >= classes.length
      || result.prediction.confidence < 0 || result.prediction.confidence > 1) throw new Error('ผลวิเคราะห์เบื้องต้นไม่ถูกต้อง');
    return result;
  }
  return parseScan(value);
}
