import { openDB, type DBSchema } from 'idb';
import { parseKnowledge, parseScan, type KnowledgeRecord } from './api';
import type { ScanResponse } from './scan-contract';

interface TeaDatabase extends DBSchema {
  scans: { key: string; value: ScanResponse };
  metadata: { key: string; value: KnowledgeRecord[] };
}
export function createStore(name = 'teasmart') {
  const database = openDB<TeaDatabase>(name, 1, { upgrade(db) {
    db.createObjectStore('scans', { keyPath: 'scan_id' });
    db.createObjectStore('metadata');
  } });
  return {
    async save(result: ScanResponse) { await (await database).put('scans', parseScan(result)); },
    async get(id: string) {
      const result = await (await database).get('scans', id);
      return result ? parseScan(result) : undefined;
    },
    async list() {
      const results = await (await database).getAll('scans');
      return results.map(parseScan).sort((a, b) => b.captured_at.localeCompare(a.captured_at));
    },
    async saveKnowledge(records: KnowledgeRecord[]) { await (await database).put('metadata', parseKnowledge(records), 'kb'); },
    async knowledge() {
      const records = await (await database).get('metadata', 'kb');
      return records ? parseKnowledge(records) : [];
    },
    async close() { (await database).close(); },
  };
}
export const store = createStore();
