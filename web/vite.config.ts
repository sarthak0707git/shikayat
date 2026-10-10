import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true, // so a judge's phone on the same Wi-Fi can open it
    proxy: { '/api': API, '/uploads': API },
  },
  preview: { port: 4173, proxy: { '/api': API, '/uploads': API } },
})
