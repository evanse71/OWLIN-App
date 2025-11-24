import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react() as any],
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  server: {
    host: true,
    port: 5176,
    strictPort: true,
    open: false,
    cors: true,
    // NOTE: For single-port setup (backend on 5177), don't use dev server
    // Instead, build frontend and let backend serve it
    // For dev mode with hot reload, run backend on 8000 and proxy to it
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Backend on port 8000
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
