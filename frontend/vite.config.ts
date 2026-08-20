import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    allowedHosts: ["partner-sklad.ru"],
    proxy: {
      '/api': {
        target: 'http://backend',
        changeOrigin: true,
      },
    },
    hmr: {
      host: 'partner-sklad.ru',
      port: 443,
      protocol: 'wss'
    }
  },
})
