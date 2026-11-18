import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * Vite + Vitest configuration.
 *
 * Tailwind CSS 4 is wired through the official Vite plugin, so there is no
 * PostCSS pipeline and no `tailwind.config.js`: theme tokens live in
 * `src/index.css` under `@theme`.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    css: false,
    clearMocks: true,
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'src/main.jsx',
        'src/test/**',
        'src/**/*.test.{js,jsx}',
      ],
    },
  },
})
