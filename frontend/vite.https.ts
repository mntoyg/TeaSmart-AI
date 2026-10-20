/**
 * Opt-in TLS for the dev server, so a real handset gets a secure context.
 *
 * The camera, the service worker, offline inference and install do not merely
 * fail without a secure context - they are absent from the browser. `localhost`
 * is exempt by specification, which is why everything works on this machine and
 * nothing works from a LAN address over plain HTTP.
 *
 * Point this at an mkcert pair and the dev server serves the LAN address over
 * HTTPS instead. It stays opt-in so that CI, the unit suites and an ordinary
 * `npm run dev` keep working with no certificate on disk.
 *
 *   mkcert -cert-file .certs/dev-cert.pem -key-file .certs/dev-key.pem \
 *     <lan-ip> localhost 127.0.0.1 ::1
 *   TEASMART_DEV_CERT_DIR=../.certs npm run dev -- --host
 *
 * A wrong path throws rather than quietly serving plain HTTP: the only symptom
 * of that on the handset is a camera button that does nothing.
 */

import { readFileSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';

export const DEV_CERT_DIR_ENV = 'TEASMART_DEV_CERT_DIR';

export const DEV_CERT_FILE = 'dev-cert.pem';
export const DEV_KEY_FILE = 'dev-key.pem';

export interface DevHttps {
  cert: string;
  key: string;
}

function read(dir: string, file: string): string {
  const path = join(dir, file);
  try {
    return readFileSync(path, 'utf8');
  } catch (cause) {
    throw new Error(
      `${DEV_CERT_DIR_ENV} is set to ${dir}, but ${path} could not be read. ` +
        `Generate the pair with mkcert, or unset ${DEV_CERT_DIR_ENV} to serve ` +
        'plain HTTP. Refusing to fall back silently: without TLS the handset ' +
        'has no camera, no service worker and no install, with no error shown.',
      { cause },
    );
  }
}

/**
 * The `server.https` value for Vite, or `undefined` to leave the dev server on
 * plain HTTP.
 *
 * `env` is passed in rather than read from `process.env` so this is testable
 * without mutating the process.
 */
export function devHttps(env: Record<string, string | undefined>): DevHttps | undefined {
  const raw = env[DEV_CERT_DIR_ENV];
  if (raw === undefined || raw.trim() === '') return undefined;
  const dir = isAbsolute(raw) ? raw : resolve(raw);
  return { cert: read(dir, DEV_CERT_FILE), key: read(dir, DEV_KEY_FILE) };
}
