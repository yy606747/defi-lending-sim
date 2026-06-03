import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    css: false,
    restoreMocks: true,
    exclude: ['node_modules/**', 'dist/**', 'tests/e2e/**'],
  },
})
