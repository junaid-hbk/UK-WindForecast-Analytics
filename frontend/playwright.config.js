import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end configuration.
 *
 * These journeys run against the real FastAPI backend: start it on
 * http://127.0.0.1:8000 first (see README), then `npm run e2e`.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      // Use the full Chromium build that `npx playwright install chromium` ships,
      // rather than the separate headless-shell download.
      use: { ...devices['Desktop Chrome'], channel: 'chromium' },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
