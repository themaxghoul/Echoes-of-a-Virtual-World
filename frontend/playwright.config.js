const { defineConfig } = require('@playwright/test');
const port = process.env.EOV_TEST_PORT || '3107';

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: { baseURL: `http://127.0.0.1:${port}`, headless: true },
  webServer: {
    command: 'pnpm start',
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    timeout: 300000,
    env: { BROWSER: 'none', PORT: port, REACT_APP_WORLD_SERVER_URL: '', REACT_APP_BACKEND_URL: '', REACT_APP_ENABLE_LOCAL_PRACTICE: 'false' },
  },
});
