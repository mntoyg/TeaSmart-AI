import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

test('generated scan types reproduce the binding section 8 sample', () => {
  execFileSync(process.execPath, ['scripts/generate-contract.mjs', '--check']);
  const generated = readFileSync('src/lib/scan-contract.ts', 'utf8');
  assert.match(generated, /"scan_id": string/);
  assert.match(generated, /"passed": boolean/);
  assert.match(generated, /"confidence": number/);
  assert.match(generated, /"top_k": \{/);
  assert.match(generated, /"edge_sharpness": number/);
  assert.match(generated, /"affected_pct": number/);
});
