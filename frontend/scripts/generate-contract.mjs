import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// docs/ was collapsed to three files; the spec moved here and the section
// numbering did not change. Kept as a path into the document rather than a
// copy of the contract, which is the point of generating this.
const source = new URL('../../docs/DESIGN.md', import.meta.url);
const spec = readFileSync(source, 'utf8').split('## 8. API contract')[1]?.split('## 9.')[0];
const example = spec?.match(/```json\s*([\s\S]*?)```/)?.[1];
if (!example) throw new Error('Section 8 scan response sample is missing');
const sample = JSON.parse(example);
const configExample = spec?.split('### 8.5')[1]?.match(/```json\s*([\s\S]*?)```/)?.[1];
if (!configExample) throw new Error('Section 8.5 config sample is missing');
const config = JSON.parse(configExample);
function typeOf(value, depth = 0) {
  if (Array.isArray(value)) return value.length ? `${typeOf(value[0], depth)}[]` : 'unknown[]';
  if (value === null) return 'unknown';
  if (typeof value !== 'object') return typeof value;
  if (!Object.keys(value).length) return 'Record<string, unknown>';
  const indent = '  '.repeat(depth + 1);
  return `{\n${Object.entries(value).map(([key, entry]) => `${indent}${JSON.stringify(key)}: ${typeOf(entry, depth + 1)};`).join('\n')}\n${'  '.repeat(depth)}}`;
}
const output = '// Generated from design spec section 8. Run npm run generate:contract.\n'
  + '// Empty arrays and objects in the sample deliberately remain unknown.\n'
  + `export type ScanResponse = ${typeOf(sample)} & { replayed?: boolean };\n`
  + `export const scanShape = ${JSON.stringify(sample, null, 2)};\n`
  + `export type ClientConfig = ${typeOf(config)};\n`
  + `export const configShape = ${JSON.stringify(config, null, 2)};\n`
  + `export const transportLimits = ${JSON.stringify({
    max_upload_bytes: Number(spec.match(/max_upload_bytes` (\d+)/)?.[1]),
    max_image_pixels: Number(spec.match(/max_image_pixels` (\d+)/)?.[1]),
    max_batch_items: Number(spec.match(/max_batch_items` (\d+)/)?.[1]),
    max_batch_bytes: Number(spec.match(/max_batch_bytes` (\d+)/)?.[1]),
  }, null, 2)};\n`;
const target = new URL('../src/lib/scan-contract.ts', import.meta.url);
if (process.argv.includes('--check')) {
  if (readFileSync(target, 'utf8') !== output) throw new Error('Scan contract types are stale');
  console.log('Scan contract matches section 8');
} else {
  mkdirSync(fileURLToPath(new URL('../src/lib/', import.meta.url)), { recursive: true });
  writeFileSync(target, output);
}
