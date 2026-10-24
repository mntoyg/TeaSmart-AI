import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const pagesBase = process.env.PAGES_BASE ?? '/'

export default defineConfig({
  base: pagesBase,
  plugins: [react()],
  server: { host: true, port: 5173, strictPort: true },
})
