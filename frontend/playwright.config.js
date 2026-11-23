import { defineConfig } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const reports = resolve(here, '../reports');

export default defineConfig({
  testDir: './tests',
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: [['list'], ['junit', { outputFile: resolve(reports, 'browser-results.xml') }]],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    viewport: { width: 1440, height: 980 },
    browserName: 'chromium',
    actionTimeout: 6000,
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run preview -- --port 4173 --strictPort',
    cwd: here,
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
  },
});
