import fs from 'fs'
import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const certDir = path.resolve(__dirname, '../../.certs')
const httpsConfig = fs.existsSync(path.join(certDir, 'cert.pem'))
  ? { cert: fs.readFileSync(path.join(certDir, 'cert.pem')), key: fs.readFileSync(path.join(certDir, 'key.pem')) }
  : undefined

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          maplibre: ['maplibre-gl'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5174,
    https: httpsConfig,
    proxy: {
      '/api/raster': {
        target: 'http://127.0.0.1:8020',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/raster/, '/api/upload-plan'),
      },
      '/api/tscm': {
        target: 'http://127.0.0.1:8450',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/tscm/, '/api'),
      },
    },
  },
})
