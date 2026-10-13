import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [react(), tailwindcss(), VitePWA({
    strategies: 'injectManifest', srcDir: 'src', filename: 'sw.ts', injectRegister: false,
    manifest: { name: 'ผู้ช่วยดูแลใบชา', short_name: 'ตรวจใบชา', lang: 'th', start_url: '/scan',
      display: 'standalone', background_color: '#f5f7f1', theme_color: '#174e36',
      icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }] },
    injectManifest: { globPatterns: ['**/*.{js,css,html,svg,webmanifest,wasm,mjs,onnx}'], maximumFileSizeToCacheInBytes: 64 * 1024 * 1024 },
  })],
  worker: { format: 'es' },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { include: ['src/**/*.test.{ts,tsx}'], maxWorkers: 1,
    environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] },
});
