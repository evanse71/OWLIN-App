import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react() as any],
  define: {
    "global": "window",
    "__dirname": JSON.stringify("")
  },
  optimizeDeps: {
    include: ['nspell', 'dictionary-en', 'dictionary-cy'],
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  server: {
    host: true,
    port: 5176,
    strictPort: false, // Allow using next available port if 5176 is busy
    open: false,
    cors: true,
    // NOTE: For single-port setup (backend on 5177), don't use dev server
    // Instead, build frontend and let backend serve it
    // For dev mode with hot reload, run backend on 8000 and proxy to it
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Backend on port 8000
        changeOrigin: true,
        secure: false,
        ws: true, // Enable WebSocket proxying
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, res) => {
            console.log('Proxy error:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Proxying request:', req.method, req.url);
          });
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
