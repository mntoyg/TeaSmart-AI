import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

// The extension is required: without it Vite's native config loader warns.
import { devHttps } from './vite.https.ts';

export default defineConfig({
  plugins: [react(), tailwindcss(), VitePWA({
    strategies: 'injectManifest', srcDir: 'src', filename: 'sw.ts', injectRegister: false,
    manifest: { name: 'ผู้ช่วยดูแลใบชา', short_name: 'ตรวจใบชา', lang: 'th', start_url: '/scan',
      display: 'standalone', background_color: '#f5f7f1', theme_color: '#174e36',
      icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }] },
    injectManifest: { globPatterns: ['**/*.{js,css,html,svg,webmanifest,wasm,mjs,onnx}'], maximumFileSizeToCacheInBytes: 64 * 1024 * 1024 },
  })],
  worker: { format: 'es' },
  // `https` is undefined unless TEASMART_DEV_CERT_DIR points at an mkcert pair;
  // see vite.https.ts for why a handset on a LAN address needs it.
  server: { proxy: { '/api': 'http://127.0.0.1:8000' }, https: devHttps(process.env) },
  test: { include: ['src/**/*.test.{ts,tsx}'], maxWorkers: 1,
    environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] },
});
