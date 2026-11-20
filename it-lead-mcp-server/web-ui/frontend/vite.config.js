import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

// self-signed cert: system Notifications (and other secure-context APIs)
// are auto-denied by Chrome on plain http over the LAN
const https = fs.existsSync('/root/certs/dash.key') ? {
  key: fs.readFileSync('/root/certs/dash.key'),
  cert: fs.readFileSync('/root/certs/dash.crt'),
} : undefined

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,  // Listen on all interfaces
    port: 5173,
    https,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/shots': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      }
    }
  }
})