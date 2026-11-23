
import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';
import regression from './playwright.config.js';

const output = resolve('../build/manual-audit/browser');

export default defineConfig({
  ...regression,
  testDir: './audit',
  outputDir: resolve(output, 'diagnostics'),
  reporter: [['list'], ['json', { outputFile: resolve(output, 'observations.json') }]],
  use: { ...regression.use, baseURL: 'http://127.0.0.1:4183' },
  webServer: {
    ...regression.webServer,
    command: 'npm run preview -- --port 4183 --strictPort',
    url: 'http://127.0.0.1:4183',
  },
});
