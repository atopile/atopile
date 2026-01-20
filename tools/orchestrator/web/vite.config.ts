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
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split heavy dependencies into separate chunks
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'flow': ['@xyflow/react'],
          'markdown': ['react-markdown', 'remark-gfm'],
          'diff': ['diff2html'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8765',
        ws: true,
      },
    },
  },
})
