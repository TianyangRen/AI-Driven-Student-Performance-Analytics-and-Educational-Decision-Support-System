import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 业务后端 web-platform/backend 跑在 8001（ML 服务 backend/ 占用 8000）
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});
