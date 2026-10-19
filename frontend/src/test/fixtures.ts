import { scanShape, type ScanResponse } from '../lib/scan-contract';

export function scanFixture(overrides: Partial<ScanResponse> = {}): ScanResponse {
  return {
    ...structuredClone(scanShape), scan_id: '00000000-0000-4000-8000-000000000001',
    severity: { affected_pct: 0.12, level: 'moderate' },
    advice: { ...scanShape.advice, disease_name_th: 'โรคใบไหม้เทา', immediate_action: 'คำแนะนำจากระบบ' },
    ...overrides,
  };
}
