import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const groqKey = env.GROQ_API_KEY || process.env.GROQ_API_KEY || '';

  return {
    plugins: [react(), tailwindcss()],
    define: {
      '__GROQ_API_KEY__': JSON.stringify(groqKey),
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      strictPort: true,
      hmr: false,
      cors: true,
    },
    preview: {
      host: '0.0.0.0',
      port: 3000,
      strictPort: true,
    },
  };
});
