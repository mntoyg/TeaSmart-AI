import { openDB, type DBSchema } from 'idb';
import { parseKnowledge, parseConfig, type KnowledgeRecord } from './api';
import type { ClientConfig, ScanResponse } from './scan-contract';
import { parseStored, type StoredResult, type LocalResult } from './local-result';
export type QueueEntry = { scan_id: string; result: LocalResult; image: Blob; state: 'pending' | 'failed'; attempts: number; status?: number; detail_th?: string };
type DurableQueueEntry = Omit<QueueEntry, 'image'> & { imageBytes: ArrayBuffer; imageType: string };
const MAX_SYNC_ATTEMPTS = 3;

interface TeaDatabase extends DBSchema {
  scans: { key: string; value: StoredResult };
  metadata: { key: string; value: KnowledgeRecord[] };
  config: { key: string; value: ClientConfig };
  queue: { key: string; value: DurableQueueEntry };
}
export function createStore(name = 'teasmart') {
  const database = openDB<TeaDatabase>(name, 3, { upgrade(db) {
    if (!db.objectStoreNames.contains('scans')) db.createObjectStore('scans', { keyPath: 'scan_id' });
    if (!db.objectStoreNames.contains('metadata')) db.createObjectStore('metadata');
    if (!db.objectStoreNames.contains('config')) db.createObjectStore('config');
    if (!db.objectStoreNames.contains('queue')) db.createObjectStore('queue', { keyPath: 'scan_id' });
  } });
  return {
    async save(result: StoredResult) { await (await database).put('scans', parseStored(result)); },
    async get(id: string) {
      const result = await (await database).get('scans', id);
      return result ? parseStored(result) : undefined;
    },
    async list() {
      const results = await (await database).getAll('scans');
      return results.map(parseStored).sort((a, b) => b.captured_at.localeCompare(a.captured_at));
    },
    async saveKnowledge(records: KnowledgeRecord[]) { await (await database).put('metadata', parseKnowledge(records), 'kb'); },
    async knowledge() {
      const records = await (await database).get('metadata', 'kb');
      return records ? parseKnowledge(records) : [];
    },
    async close() { (await database).close(); },
    async saveConfig(config: ClientConfig) { await (await database).put('config', parseConfig(config), 'client'); },
    async config() { const config = await (await database).get('config', 'client'); return config ? parseConfig(config) : undefined; },
    async enqueue(image: Blob, result: LocalResult) {
      const parsed = parseStored(result) as LocalResult;
      const imageBytes = image.arrayBuffer ? await image.arrayBuffer() : await new Promise<ArrayBuffer>((resolve, reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result as ArrayBuffer);
        reader.onerror = () => reject(new Error('อ่านภาพไม่ได้')); reader.readAsArrayBuffer(image);
      });
      const tx = (await database).transaction(['scans', 'queue'], 'readwrite');
      await tx.objectStore('scans').put(parsed);
      await tx.objectStore('queue').put({ scan_id: parsed.scan_id, result: parsed, imageBytes, imageType: image.type, state: 'pending', attempts: 0 });
      await tx.done;
    },
    async pending(): Promise<QueueEntry[]> { return (await (await database).getAll('queue')).filter((entry) => entry.state === 'pending')
      .map((entry) => ({ ...entry, attempts: entry.attempts ?? 0, image: new Blob([entry.imageBytes], { type: entry.imageType }) })); },
    async queueStatus(id: string) { return (await database).get('queue', id); },
    async applyBatch(results: ScanResponse[], failures: { scan_id: string; status: number; detail_th: string }[]) {
      const parsedResults = results.map(parseStored);
      const tx = (await database).transaction(['scans', 'queue'], 'readwrite');
      for (const result of parsedResults) {
        await tx.objectStore('scans').put(result);
        await tx.objectStore('queue').delete(result.scan_id);
      }
      for (const failure of failures) {
        const entry = await tx.objectStore('queue').get(failure.scan_id);
        if (entry) {
          const attempts = (entry.attempts ?? 0) + 1;
          const terminal = [400, 413, 415, 422].includes(failure.status);
          const exhausted = attempts >= MAX_SYNC_ATTEMPTS;
          const detail_th = exhausted && !terminal
            ? `ระบบวิเคราะห์ขัดข้องหลังลองส่งซ้ำไม่สำเร็จ ${MAX_SYNC_ATTEMPTS} ครั้ง ภาพยังบันทึกอยู่ในอุปกรณ์`
            : failure.detail_th;
          await tx.objectStore('queue').put({ ...entry, attempts, status: failure.status,
            state: terminal || exhausted ? 'failed' : 'pending', detail_th });
        }
      }
      await tx.done;
    },
  };
}
export const store = createStore();
