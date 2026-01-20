import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Dev server settings
  server: {
    port: 5173,
    open: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      // In production, build the separate webview entry points
      input: mode === 'development' 
        ? resolve(__dirname, 'index.html')
        : {
            sidebar: resolve(__dirname, 'sidebar.html'),
            logViewer: resolve(__dirname, 'log-viewer.html'),
          },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name].[ext]',
      },
    },
  },
}));
