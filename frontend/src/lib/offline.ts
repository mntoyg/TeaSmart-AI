import { parseConfig } from './api';
import { transportLimits, type ClientConfig } from './scan-contract';
import type { LocalResult } from './local-result';
let worker: Worker | undefined;
let sequence = 0;
const pending = new Map<number, { resolve: (value: WorkerResponse) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>();
type WorkerResponse = { id: number; error?: string; ready?: boolean; quality: LocalResult['quality']; prediction: LocalResult['prediction'] };
function send(config: ClientConfig, image?: { rgb: Uint8Array; width: number; height: number }): Promise<WorkerResponse> {
  if (!worker) {
    worker = new Worker(new URL('./onnx-worker.ts', import.meta.url), { type: 'module' });
    worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const entry = pending.get(event.data.id);
      if (!entry) return;
      clearTimeout(entry.timer); pending.delete(event.data.id);
      if (event.data.error) entry.reject(new Error(event.data.error)); else entry.resolve(event.data);
    };
    worker.onerror = () => {
      for (const entry of pending.values()) { clearTimeout(entry.timer); entry.reject(new Error('เริ่มโมเดลออฟไลน์ไม่ได้ กรุณาลองใหม่')); }
      pending.clear(); worker?.terminate(); worker = undefined;
    };
  }
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id); reject(new Error('ประเมินออฟไลน์นานเกินไป กรุณาลองใหม่'));
      worker?.terminate(); worker = undefined;
      for (const entry of pending.values()) { clearTimeout(entry.timer); entry.reject(new Error('ประเมินออฟไลน์ไม่สำเร็จ')); }
      pending.clear();
    }, 90_000);
    pending.set(id, { resolve, reject, timer });
    worker!.postMessage({ id, config, ...image }, image ? [image.rgb.buffer] : []);
  });
}
export async function prepareOffline(config?: ClientConfig) {
  if (!config) throw new Error('ยังไม่มีการตั้งค่าออฟไลน์ กรุณาเชื่อมต่อก่อน');
  await send(parseConfig(config));
}
// Whether an on-device scan can run right now, asked of the cache rather than
// of this session's history. The service worker precaches the graph on install,
// so a reload - online or offline - starts with it already there and nothing to
// prepare. `caches` is absent in an insecure context and throws in some
// browsers with storage disabled; either way the honest answer is "not ready".
export async function isOfflineReady(config?: ClientConfig) {
  if (!config || typeof caches === 'undefined') return false;
  try { return Boolean(await caches.match(`/models/${parseConfig(config).onnx.file}`)); }
  catch { return false; }
}
export async function inferOffline(image: File, scanId: string, capturedAt: string, config?: ClientConfig): Promise<LocalResult> {
  if (!config) throw new Error('ยังไม่มีการตั้งค่าออฟไลน์ กรุณาเชื่อมต่อก่อน');
  parseConfig(config);
  if (!image.size || image.size > transportLimits.max_upload_bytes) throw new Error('ภาพมีขนาดไม่ถูกต้อง กรุณาเลือกภาพใหม่');
  let bitmap: ImageBitmap;
  try { bitmap = await createImageBitmap(image, { imageOrientation: 'from-image' }); }
  catch { throw new Error('อ่านภาพไม่ได้ กรุณาเลือกภาพใหม่'); }
  try {
    if (bitmap.width * bitmap.height > transportLimits.max_image_pixels) throw new Error('ภาพมีขนาดใหญ่เกินไป กรุณาเลือกภาพที่เล็กลง');
    const canvas = document.createElement('canvas'); canvas.width = bitmap.width; canvas.height = bitmap.height;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) throw new Error('อ่านภาพบนอุปกรณ์ไม่ได้');
    context.drawImage(bitmap, 0, 0);
    const rgba = context.getImageData(0, 0, bitmap.width, bitmap.height).data;
    const rgb = new Uint8Array(bitmap.width * bitmap.height * 3);
    for (let index = 0; index < rgb.length / 3; index++) rgb.set(rgba.subarray(index * 4, index * 4 + 3), index * 3);
    const output = await send(config, { rgb, width: bitmap.width, height: bitmap.height });
    return { scan_id: scanId, captured_at: capturedAt, model_version: config.model_version,
      analysis_mode: 'classifier_only', quality: output.quality, prediction: output.prediction };
  } finally { bitmap.close(); }
}
