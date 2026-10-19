import type { LocalResult } from '../lib/local-result';
import { scanFixture } from './fixtures';
export function localFixture(id = '00000000-0000-4000-8000-000000000001'): LocalResult {
  const scan = scanFixture();
  return { scan_id: id, captured_at: scan.captured_at, quality: scan.quality,
    prediction: scan.prediction, model_version: scan.model_version, analysis_mode: 'classifier_only' };
}
