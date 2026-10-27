const { test, expect } = require('@playwright/test');
test('desktop can join a hosted account without a duplicate local account', async ({ page }) => {
  await page.addInitScript(() => {
    window.eovDesktop = { login: () => { throw new Error('Hosted login must not require a local account'); } };
    localStorage.setItem('eov-game-settings', JSON.stringify({ authServerUrl: 'http://auth.test:8000' }));
  });
  await page.route('http://auth.test:8000/api/auth/login', route => route.fulfill({ json: {
    user: { id: 'hosted-user', username: 'traveler', display_name: 'Traveler' }, session: { access_token: 'hosted-token' },
  } }));
  await page.route('http://auth.test:8000/api/characters/hosted-user', route => {
    expect(route.request().headers().authorization).toBe('Bearer hosted-token');
    return route.fulfill({ json: [{ id: 'character-hosted', name: 'Traveler' }] });
  });
  await page.goto('/#/auth');
  await page.getByTestId('login-username').fill('traveler');
  await page.getByTestId('login-password').fill('example-test-password');
  await page.getByTestId('login-submit').click();
  await expect(page.getByRole('button', { name: 'Enter settlement' })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('eovNetworkUserId'))).toBe('hosted-user');
});
