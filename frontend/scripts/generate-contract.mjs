import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const source = new URL('../../docs/superpowers/specs/2026-10-13-teasmart-ai-design.md', import.meta.url);
const spec = readFileSync(source, 'utf8').split('## 8. API contract')[1]?.split('## 9.')[0];
const example = spec?.match(/```json\s*([\s\S]*?)```/)?.[1];
if (!example) throw new Error('Section 8 scan response sample is missing');
const sample = JSON.parse(example);
function typeOf(value, depth = 0) {
  if (Array.isArray(value)) return 'unknown[]';
  if (value === null) return 'unknown';
  if (typeof value !== 'object') return typeof value;
  if (!Object.keys(value).length) return 'Record<string, unknown>';
  const indent = '  '.repeat(depth + 1);
  return `{\n${Object.entries(value).map(([key, entry]) => `${indent}${JSON.stringify(key)}: ${typeOf(entry, depth + 1)};`).join('\n')}\n${'  '.repeat(depth)}}`;
}
const output = '// Generated from design spec section 8. Run npm run generate:contract.\n'
  + '// Empty arrays and objects in the sample deliberately remain unknown.\n'
  + `export type ScanResponse = ${typeOf(sample)};\n`;
const target = new URL('../src/lib/scan-contract.ts', import.meta.url);
if (process.argv.includes('--check')) {
  if (readFileSync(target, 'utf8') !== output) throw new Error('Scan contract types are stale');
  console.log('Scan contract matches section 8');
} else {
  mkdirSync(fileURLToPath(new URL('../src/lib/', import.meta.url)), { recursive: true });
  writeFileSync(target, output);
}
