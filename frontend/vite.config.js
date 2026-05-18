import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  // Server configuration for development
  server: {
    port: 3000,
    strictPort: false,
    host: true, // Listen on all addresses
    // Proxy API requests to FastAPI backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },

  // Build configuration for production
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'terser',
    target: 'es2015',
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks: {
          'match-renderer': ['./src/match-renderer.js'],
          'telegram-sdk': ['@telegram-apps/sdk'],
        },
      },
    },
    // Asset size warnings
    chunkSizeWarningLimit: 1000,
  },

  // Base public path
  base: './',

  // Preview server configuration
  preview: {
    port: 4173,
    strictPort: false,
    host: true,
  },

  // Optimize dependencies
  optimizeDeps: {
    include: ['@telegram-apps/sdk'],
  },
});
