import { scanShape, type ScanResponse } from './scan-contract';

export const classes = ['grey_blight', 'brown_blight', 'algal_spot', 'healthy', 'other_disease'] as const;
export const adviceFields = [
  ['immediate_action', 'สิ่งที่ควรทำทันที'], ['cultural_control', 'การดูแลแปลง'],
  ['chemical_treatment', 'การใช้สารป้องกันกำจัด'], ['preventive_measures', 'การป้องกัน'],
] as const;
export type KnowledgeRecord = {
  class_id: number; canonical: string; class_name: string; disease_name_th: string;
  pathogen: string; symptoms: string; immediate_action: string; cultural_control: string;
  chemical_treatment: string; preventive_measures: string;
};

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function matches(value: unknown, shape: unknown): boolean {
  if (Array.isArray(shape)) return Array.isArray(value) && (!shape.length || value.every((item) => matches(item, shape[0])));
  if (object(shape)) return object(value) && Object.entries(shape).every(([key, entry]) => matches(value[key], entry));
  if (typeof shape === 'number') return typeof value === 'number' && Number.isFinite(value);
  return typeof value === typeof shape;
}
function unit(value: number) { return value >= 0 && value <= 1; }
export function parseScan(value: unknown): ScanResponse {
  if (!matches(value, scanShape)) throw new Error('ผลวิเคราะห์ไม่ครบถ้วน กรุณาลองใหม่');
  const result = value as ScanResponse;
  if (!result.quality.passed || !classes.includes(result.prediction.class_name as typeof classes[number])
    || classes[result.prediction.class_id] !== result.prediction.class_name
    || !unit(result.prediction.confidence) || !unit(result.burn_analysis.burn_likelihood)
    || !unit(result.severity.affected_pct) || !['mild', 'moderate', 'severe'].includes(result.severity.level)
    || !['disease', 'physical_burn'].includes(result.burn_analysis.verdict)
    || !['full', 'classifier_only'].includes(result.analysis_mode)
    || !result.scan_id || !result.advice.disease_name_th
    || !result.prediction.top_k.every((entry) => unit(entry.confidence))) {
    throw new Error('ผลวิเคราะห์ไม่ถูกต้อง กรุณาลองใหม่');
  }
  return result;
}

export function parseKnowledge(value: unknown): KnowledgeRecord[] {
  const fields = ['canonical', 'class_name', 'disease_name_th', 'pathogen', 'symptoms', ...adviceFields.map(([field]) => field)];
  if (!Array.isArray(value) || value.length !== 6 || !value.every((entry) => object(entry)
    && Number.isInteger(entry.class_id) && fields.every((field) => typeof entry[field] === 'string'))
    || new Set(value.map((entry) => entry.canonical)).size !== 6
    || ![...classes, 'physical_burn'].every((canonical) => value.some((entry) => entry.canonical === canonical))) {
    throw new Error('ข้อมูลความรู้ไม่ครบถ้วน กรุณาลองใหม่');
  }
  return value as KnowledgeRecord[];
}
async function request(url: string, init?: RequestInit): Promise<unknown> {
  let response: Response;
  try { response = await fetch(url, { ...init, signal: init?.signal ?? AbortSignal.timeout(30_000) }); }
  catch { throw new Error('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่'); }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = object(body) && typeof body.detail_th === 'string' && body.detail_th.trim();
    throw new Error(detail || 'ระบบยังไม่พร้อม กรุณาลองใหม่');
  }
  return body;
}
export async function scanImage(image: File, field = 'image', scanId?: string, capturedAt?: string, signal?: AbortSignal) {
  const body = new FormData();
  body.append(field, image);
  if (scanId) body.append('scan_id', scanId);
  if (capturedAt) body.append('captured_at', capturedAt);
  return parseScan(await request('/api/v1/scan', { method: 'POST', body, signal }));
}
export async function readKnowledgeBase() { return parseKnowledge(await request('/api/v1/kb')); }
