import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    trace: 'on-first-retry',
    baseURL: 'https://127.0.0.1:8443', // HTTPS frontend
  },
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        ignoreHTTPSErrors: true, // Allow self-signed certs
      },
    },
  ],
  webServer: {
    command: 'VITE_API_BASE_URL=http://127.0.0.1:8000 OWLIN_SINGLE_PORT=1 bash scripts/run_single_port.sh',
    url: 'http://127.0.0.1:8000',
    timeout: 60 * 1000, // 60 seconds
    reuseExistingServer: !process.env.CI,
  },
});
