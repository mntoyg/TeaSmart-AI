import { parseScan, request } from './api';
import { transportLimits, type ScanResponse } from './scan-contract';
import type { createStore, QueueEntry } from './storage';
export function chunkQueue(entries: QueueEntry[]) {
  const batches: QueueEntry[][] = [];
  let batch: QueueEntry[] = [], bytes = 0;
  const payloadLimit = transportLimits.max_batch_bytes - 65_536;
  for (const entry of entries) {
    if (!entry.image.size || entry.image.size > transportLimits.max_upload_bytes) throw new Error('ภาพในคิวมีขนาดไม่ถูกต้อง');
    if (batch.length >= transportLimits.max_batch_items || bytes + entry.image.size > payloadLimit) {
      batches.push(batch); batch = []; bytes = 0;
    }
    batch.push(entry); bytes += entry.image.size;
  }
  if (batch.length) batches.push(batch);
  return batches;
}
export async function syncQueue(repository: ReturnType<typeof createStore>) {
  const config = await repository.config();
  for (const batch of chunkQueue(await repository.pending())) {
    const form = new FormData();
    form.append('items', JSON.stringify(batch.map((entry) => ({ scan_id: entry.scan_id,
      captured_at: entry.result.captured_at, local_prediction: {
        class_name: entry.result.prediction.class_name, confidence: entry.result.prediction.confidence,
      } }))));
    for (const entry of batch) form.append('images', entry.image, entry.scan_id);
    let response: unknown;
    try {
      response = await request('/api/v1/sync/batch', { method: 'POST', body: form });
    } catch (failure) {
      const detail_th = failure instanceof Error ? failure.message : 'เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่';
      await repository.applyBatch([], batch.map((entry) => ({ scan_id: entry.scan_id, status: 503, detail_th })));
      throw failure;
    }
    if (!response || typeof response !== 'object' || !('results' in response) || !('failed' in response)
      || !Array.isArray(response.results) || !Array.isArray(response.failed)) throw new Error('ผลการส่งคิวไม่ครบถ้วน');
    const parsedResults: ScanResponse[] = response.results.map((result: unknown) => parseScan(result, config?.class_order));
    const results = parsedResults.filter((result) => result.analysis_mode === 'full');
    const incomplete = parsedResults.filter((result) => result.analysis_mode === 'classifier_only').map((result) => ({
      scan_id: result.scan_id,
      status: 503,
      detail_th: 'เซิร์ฟเวอร์ยังวิเคราะห์ภาพนี้ได้ไม่ครบ ภาพยังอยู่ในคิวเพื่อลองส่งใหม่',
    }));
    const failed = response.failed.map((entry: unknown) => {
      if (!entry || typeof entry !== 'object' || !('scan_id' in entry) || typeof entry.scan_id !== 'string'
        || !('status' in entry) || typeof entry.status !== 'number' || !Number.isInteger(entry.status)
        || entry.status < 400 || entry.status > 599 || !('detail_th' in entry) || typeof entry.detail_th !== 'string') {
        throw new Error('ข้อมูลภาพที่ส่งไม่สำเร็จไม่ถูกต้อง');
      }
      return { scan_id: entry.scan_id, status: entry.status, detail_th: entry.detail_th };
    });
    const sent = new Set(batch.map((entry) => entry.scan_id));
    const returned = [...parsedResults, ...failed].map((entry) => entry.scan_id);
    if (returned.length !== batch.length || new Set(returned).size !== returned.length || returned.some((id) => !sent.has(id))) {
      throw new Error('ผลการส่งคิวไม่ตรงกับภาพ กรุณาลองใหม่');
    }
    await repository.applyBatch(results, [...failed, ...incomplete]);
  }
}
