import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true, // so a judge's phone on the same Wi-Fi can open it
    allowedHosts: true, // reachable through a tunnel hostname
    proxy: { '/api': API, '/uploads': API },
  },
  preview: { port: 4173, host: true, allowedHosts: true, proxy: { '/api': API, '/uploads': API } },
})
