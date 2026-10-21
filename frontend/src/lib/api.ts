import { scanShape, configShape, type ScanResponse, type ClientConfig } from './scan-contract';

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
export function matches(value: unknown, shape: unknown): boolean {
  if (Array.isArray(shape)) return Array.isArray(value) && (!shape.length || value.every((item) => matches(item, shape[0])));
  if (object(shape)) return object(value) && Object.entries(shape).every(([key, entry]) => matches(value[key], entry));
  if (typeof shape === 'number') return typeof value === 'number' && Number.isFinite(value);
  return typeof value === typeof shape;
}
function unit(value: number) { return value >= 0 && value <= 1; }
export function parseScan(value: unknown, classOrder?: readonly string[]): ScanResponse {
  if (!matches(value, scanShape)) throw new Error('ผลวิเคราะห์ไม่ครบถ้วน กรุณาลองใหม่');
  const result = value as ScanResponse;
  if (!result.quality.passed || !classes.includes(result.prediction.class_name as typeof classes[number])
    || !Number.isInteger(result.prediction.class_id) || result.prediction.class_id < 0
    || result.prediction.class_id >= (classOrder?.length ?? classes.length)
    || (classOrder && classOrder[result.prediction.class_id] !== result.prediction.class_name)
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
  const required = [...classes, 'physical_burn'];
  if (!Array.isArray(value) || value.length < required.length || !value.every((entry) => object(entry)
    && Number.isInteger(entry.class_id) && fields.every((field) => typeof entry[field] === 'string'))
    || new Set(value.map((entry) => entry.canonical)).size !== value.length
    || !required.every((canonical) => value.some((entry) => entry.canonical === canonical))) {
    throw new Error('ข้อมูลความรู้ไม่ครบถ้วน กรุณาลองใหม่');
  }
  return value as KnowledgeRecord[];
}
/**
 * The request never got an answer: no route, DNS failure, refused connection,
 * a dev server that is not running, or the 30-second timeout below.
 *
 * Distinct from an ordinary Error, which is how a server that *did* answer and
 * refused arrives. A caller may fall back to the on-device model for this one
 * and must not for the other: re-running the classifier locally on a photograph
 * the quality gate rejected would replace a deliberate "take it again" with a
 * result the server declined to give.
 */
export class ServerUnreachableError extends Error {
  constructor(cause?: unknown) {
    super('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่', { cause });
    this.name = 'ServerUnreachableError';
  }
}

/** Whether `failure` means the server was never reached. */
export function isServerUnreachable(failure: unknown): boolean {
  return failure instanceof ServerUnreachableError;
}

export class SyncUnavailableError extends Error {
  constructor() {
    super('ภาพถูกเก็บไว้ในอุปกรณ์แล้ว แต่รุ่นสาธิตนี้ไม่มีเซิร์ฟเวอร์สำหรับวิเคราะห์เต็มรูปแบบ');
    this.name = 'SyncUnavailableError';
  }
}

async function request(url: string, init?: RequestInit): Promise<unknown> {
  let response: Response;
  try { response = await fetch(url, { ...init, signal: init?.signal ?? AbortSignal.timeout(30_000) }); }
  catch (cause) {
    // A user who pressed cancel wants nothing to happen, not a second attempt
    // by another route, so an abort is passed through as itself. A timeout is
    // not an abort: no answer came back, which is what unreachable means.
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause;
    throw new ServerUnreachableError(cause);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = object(body) && typeof body.detail_th === 'string' && body.detail_th.trim();
    if (!detail && url === '/api/v1/sync/batch' && [404, 405].includes(response.status)) {
      throw new SyncUnavailableError();
    }
    throw new Error(detail || 'ระบบยังไม่พร้อม กรุณาลองใหม่');
  }
  return body;
}
export async function scanImage(image: File, field = 'image', scanId?: string, capturedAt?: string,
  signal?: AbortSignal, classOrder?: readonly string[]) {
  const body = new FormData();
  body.append(field, image);
  if (scanId) body.append('scan_id', scanId);
  if (capturedAt) body.append('captured_at', capturedAt);
  return parseScan(await request('/api/v1/scan', { method: 'POST', body, signal }), classOrder);
}
export async function readKnowledgeBase() { return parseKnowledge(await request('/api/v1/kb')); }
export function parseConfig(value: unknown): ClientConfig {
  if (!matches(value, configShape)) throw new Error('การตั้งค่าออฟไลน์ไม่ครบถ้วน');
  const config = value as ClientConfig, prep = config.preprocessing;
  if (!unit(config.min_confidence) || config.class_order.length !== 5
    || new Set(config.class_order).size !== 5 || !classes.every((entry) => config.class_order.includes(entry))
    || prep.size.length !== 2 || !prep.size.every((side) => side === 224)
    || prep.mean.length !== 3 || prep.std.length !== 3 || !prep.std.every((value) => value > 0)
    || prep.resize !== 'bilinear' || prep.preserve_aspect_ratio || prep.layout !== 'NCHW'
    || prep.dtype !== 'float32' || prep.scale <= 0 || !config.onnx.output_is_logits
    || !/^teasmart-[a-z0-9-]+\.onnx$/.test(config.onnx.file)
    || !config.onnx.input || !config.onnx.output
    || config.quality.blur_threshold < 0 || !unit(config.quality.clip_max_pct)
    || config.quality.exposure_min_mean < 0 || config.quality.exposure_max_mean > 255
    || config.quality.exposure_min_mean >= config.quality.exposure_max_mean) throw new Error('การตั้งค่าออฟไลน์ไม่ถูกต้อง');
  return config;
}
export async function readClientConfig() { return parseConfig(await request('/api/v1/config')); }
export { request };
