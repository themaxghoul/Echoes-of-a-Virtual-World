const { test, expect } = require('@playwright/test');

test('story chat uses the persistent world and keeps the speech rule pinned once', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('currentCharacterId', 'character-1');
    localStorage.setItem('characterName', 'Luciferous');
    localStorage.setItem('userId', 'player-1');
    localStorage.setItem('eov-game-settings', JSON.stringify({ worldServerUrl: 'http://world.test' }));
    sessionStorage.setItem('eovAccessToken', 'signed-test-session');
  });

  const snapshot = {
    world_id: 'founders-settlement',
    revision: 17,
    tick: 144,
    state: {
      name: "Founders' Settlement",
      clock: { tick: 144, minute: 600, tick_seconds: 15, paused: false },
      players: {
        'player-1': { id: 'player-1', location: [8, 5], inventory: {}, energy: 100 },
      },
      npcs: {
        imani: { id: 'imani', name: 'Imani', location: [7, 5], intention: 'check the recovery room', reason: 'The clinic needs a dependable inventory.', memories: [] },
      },
      communications: { messages: [] },
      event: { title: 'The Founding Table', phase: 0, priorities: ['settlement_meeting'] },
    },
  };

  await page.route('http://world.test/health', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, tick: 144, tick_seconds: 15, uptime_seconds: 7384, revision: 17 }),
  }));
  await page.route('http://world.test/worlds/founders-settlement', (route) => route.fulfill({
    contentType: 'application/json', body: JSON.stringify(snapshot),
  }));
  await page.route('http://world.test/worlds/founders-settlement/actions', async (route) => {
    const body = route.request().postDataJSON();
    expect(body.action).toEqual({ type: 'speak', content: 'Hello, Imani.', target_id: 'imani' });
    expect(route.request().headers().authorization).toBe('Bearer signed-test-session');
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        world_id: 'founders-settlement', revision: 18, tick: 144,
        result: {
          accepted: true,
          type: 'speak',
          physical_change: false,
          replies: [{ id: 'reply-1', speaker_id: 'imani', speaker: 'Imani', content: 'Hello. I can listen while I finish the clinic inventory.' }],
        },
      }),
    });
  });

  await page.goto('/village');

  const authority = page.getByRole('status', { name: 'Persistent world status' });
  await expect(authority).toContainText('Persistent world connected');
  await expect(authority).toContainText('Tick 144');
  await expect(authority).toContainText('15s per tick');
  await expect(authority).toContainText('Uptime 2h 3m');

  const rule = 'Speech may influence memory, trust, rumor, coordination, and later decisions. Physical terrain changes require physical action.';
  await expect(page.getByText(rule, { exact: true })).toHaveCount(1);

  await page.getByLabel('Directed Samaritan').selectOption('imani');
  await page.getByTestId('chat-input').fill('Hello, Imani.');
  await page.getByTestId('send-message-btn').click();
  await expect(page.getByText('Hello. I can listen while I finish the clinic inventory.')).toBeVisible();
  await expect(page.getByText(rule, { exact: true })).toHaveCount(1);
  await expect(page.getByText(/responds on their own terms/i)).toHaveCount(0);
  await expect(page.getByText(/offline world snapshot/i)).toHaveCount(0);
});
