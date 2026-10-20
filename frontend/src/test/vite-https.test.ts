/**
 * The dev server serves TLS only when it is asked to, and says so when it
 * cannot.
 *
 * A real handset needs a secure context before the camera, the service worker,
 * offline inference and install exist at all. On localhost that is free; from a
 * LAN address it is not, so the dev server can serve the mkcert pair instead.
 * It is opt-in because CI, the unit suites and the everyday `npm run dev` must
 * keep working with no certificate on disk.
 *
 * The failure this guards against is silent: a misspelt path would leave the
 * server on plain HTTP, and the only symptom on the handset is that the camera
 * button does nothing - hours from the demo, with no error anywhere.
 */

import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';

import { devHttps, DEV_CERT_DIR_ENV } from '../../vite.https';

const made: string[] = [];

function certDir(files: Record<string, string>): string {
  const dir = mkdtempSync(join(tmpdir(), 'teasmart-cert-'));
  made.push(dir);
  for (const [name, body] of Object.entries(files)) {
    writeFileSync(join(dir, name), body);
  }
  return dir;
}

afterEach(() => {
  while (made.length) rmSync(made.pop()!, { recursive: true, force: true });
});

describe('devHttps', () => {
  it('is off when the environment does not ask for it', () => {
    expect(devHttps({})).toBeUndefined();
  });

  it('is off for an empty or whitespace value, rather than reading the cwd', () => {
    expect(devHttps({ [DEV_CERT_DIR_ENV]: '' })).toBeUndefined();
    expect(devHttps({ [DEV_CERT_DIR_ENV]: '   ' })).toBeUndefined();
  });

  it('serves the pair it was pointed at', () => {
    const dir = certDir({
      'dev-cert.pem': 'CERT BODY',
      'dev-key.pem': 'KEY BODY',
    });
    expect(devHttps({ [DEV_CERT_DIR_ENV]: dir })).toEqual({
      cert: 'CERT BODY',
      key: 'KEY BODY',
    });
  });

  it('names the missing file instead of falling back to plain HTTP', () => {
    const dir = certDir({ 'dev-cert.pem': 'CERT BODY' });
    expect(() => devHttps({ [DEV_CERT_DIR_ENV]: dir })).toThrow(/dev-key\.pem/);
  });

  it('names the directory that does not exist', () => {
    const missing = join(tmpdir(), 'teasmart-cert-does-not-exist');
    expect(() => devHttps({ [DEV_CERT_DIR_ENV]: missing })).toThrow(
      /teasmart-cert-does-not-exist/,
    );
  });
});
