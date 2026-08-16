const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:3000', headless: true },
  webServer: {
    command: 'pnpm start',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: { BROWSER: 'none', PORT: '3000' },
  },
});
