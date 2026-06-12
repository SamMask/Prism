import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to the Go primary backend.
      '/api': {
        target: 'http://127.0.0.1:5004',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:5004',
        changeOrigin: true,
      },
      // Proxy legacy static routes to the active backend.
      '/prompt-builder.html': {
        target: 'http://127.0.0.1:5004',
        changeOrigin: true,
      },
      '/templates': {
        target: 'http://127.0.0.1:5004',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
