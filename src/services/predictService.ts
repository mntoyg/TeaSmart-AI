import { diseases, getDiseaseByClassName, getDiseaseById } from '../data/diseases'
import type { PredictionCandidate, PredictionResult, PredictionStatus } from '../types'

const apiBase = import.meta.env?.VITE_API_BASE_URL
const API_BASE_URL = typeof apiBase === 'string' ? apiBase.replace(/\/$/, '') : ''

export const isDemoMode = !API_BASE_URL
export const CONFIDENCE_MIN = 0.7
const PREDICT_TIMEOUT_MS = 30_000
const HEALTH_TIMEOUT_MS = 4_000

export type BackendStatus = 'demo' | 'checking' | 'online' | 'offline'

function timeoutSignal(ms: number): AbortSignal {
  const timeout = (AbortSignal as { timeout?: (milliseconds: number) => AbortSignal }).timeout
  if (timeout) return timeout(ms)
  const controller = new AbortController()
  window.setTimeout(() => controller.abort(), ms)
  return controller.signal
}

function isTimeoutError(error: unknown) {
  return error instanceof DOMException && (error.name === 'TimeoutError' || error.name === 'AbortError')
}

/** เช็กว่า backend ตอบ /health และโหลดโมเดลแล้ว ไม่ใช่แค่มี URL */
export async function checkBackend(): Promise<boolean> {
  if (!API_BASE_URL) return false
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { signal: timeoutSignal(HEALTH_TIMEOUT_MS) })
    if (!response.ok) return false
    const body = (await response.json()) as { ok?: boolean; model_loaded?: boolean }
    return body.ok === true && body.model_loaded !== false
  } catch {
    return false
  }
}

async function readApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    /* ไม่ใช่ JSON */
  }
  if (response.status === 413) return 'ไฟล์ใหญ่เกินที่ระบบรับได้'
  if (response.status === 503) return 'ระบบโมเดลยังไม่พร้อม กรุณาลองใหม่ภายหลัง'
  return `API ตอบกลับผิดพลาด (${response.status})`
}

export function isConnectionFailure(error: unknown) {
  return error instanceof Error && error.message.startsWith('เชื่อมต่อระบบวิเคราะห์ไม่ได้')
}

type ApiCandidate = { class_id?: number; classId?: number; confidence?: number }

export type ApiPrediction = {
  class_id?: number
  classId?: number
  class_name?: string
  className?: string
  disease_name_th?: string
  confidence?: number
  top_k?: ApiCandidate[]
}

export function normalizeConfidence(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  const scaled = value > 1 ? value / 100 : value
  return Math.min(1, Math.max(0, scaled))
}

function parseCandidates(list: ApiCandidate[] | undefined): PredictionCandidate[] {
  if (!Array.isArray(list)) return []
  return list
    .map((item) => {
      const id = item.class_id ?? item.classId
      const disease = typeof id === 'number' ? getDiseaseById(id) : undefined
      const confidence = normalizeConfidence(item.confidence)
      return disease && confidence !== null ? { disease, confidence } : null
    })
    .filter((item): item is PredictionCandidate => item !== null)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3)
}

export function statusForConfidence(confidence: number | null): PredictionStatus {
  return confidence !== null && confidence < CONFIDENCE_MIN ? 'uncertain' : 'ok'
}

/** แปลง JSON จาก POST /predict ให้เป็นผลที่ใช้บนหน้าจอ คลาสที่ไม่รู้จักถือว่าผิดพลาด */
export function mapApiPrediction(payload: ApiPrediction, createdAt = new Date().toISOString()): PredictionResult {
  const classId = payload.class_id ?? payload.classId
  const className = payload.class_name ?? payload.className ?? payload.disease_name_th
  const disease =
    (typeof classId === 'number' ? getDiseaseById(classId) : undefined) ||
    (typeof className === 'string' ? getDiseaseByClassName(className) : undefined)

  if (!disease) {
    throw new Error('คลาสที่ API ส่งกลับมายังไม่มีใน src/data/diseases.ts')
  }

  const confidence = normalizeConfidence(payload.confidence)
  return {
    disease,
    confidence,
    status: statusForConfidence(confidence),
    candidates: parseCandidates(payload.top_k),
    isDemo: false,
    createdAt,
  }
}

export async function predictTeaLeaf(file: File): Promise<PredictionResult> {
  if (!API_BASE_URL) {
    void file
    await new Promise((resolve) => window.setTimeout(resolve, 900))
    const disease = diseases[Math.floor(Math.random() * diseases.length)]
    if (!disease) throw new Error('ไม่พบข้อมูลโรคตัวอย่าง')
    return {
      disease,
      confidence: null,
      status: 'demo',
      candidates: [],
      isDemo: true,
      createdAt: new Date().toISOString(),
    }
  }

  const formData = new FormData()
  formData.append('image', file)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/predict`, {
      method: 'POST',
      body: formData,
      signal: timeoutSignal(PREDICT_TIMEOUT_MS),
    })
  } catch (caught) {
    if (isTimeoutError(caught)) throw new Error('ระบบใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง')
    throw new Error('เชื่อมต่อระบบวิเคราะห์ไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตหรือลองใหม่ภายหลัง')
  }

  if (!response.ok) throw new Error(await readApiError(response))

  return mapApiPrediction((await response.json()) as ApiPrediction)
}
