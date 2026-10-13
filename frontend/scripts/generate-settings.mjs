import { readFileSync, writeFileSync } from 'node:fs';
const config = readFileSync(new URL('../../backend/app/core/config.py', import.meta.url), 'utf8');
const required = ['max_upload_bytes', 'max_image_pixels', 'blur_threshold', 'exposure_min_mean', 'exposure_max_mean', 'clip_max_pct'];
const fields = [...required, 'min_confidence', 'max_batch_items', 'max_batch_bytes'];
const settings = Object.fromEntries(fields.map((field) => {
  const match = config.match(new RegExp(`^    ${field}: (?:float|int) = ([0-9.]+)$`, 'm'));
  if (!match && required.includes(field)) throw new Error(`Missing Settings.${field}`);
  return [field, match ? Number(match[1]) : null];
}));
const output = '// Generated from backend Settings defaults; null means the setting is not pinned yet.\n'
  + `export const offlineSettings = ${JSON.stringify(settings, null, 2)} as const;\n`;
const target = new URL('../src/lib/offline-settings.ts', import.meta.url);
if (process.argv.includes('--check')) {
  if (readFileSync(target, 'utf8') !== output) throw new Error('Offline settings are stale');
  console.log('Offline settings match backend defaults');
} else writeFileSync(target, output);
