const { test, expect } = require('@playwright/test');

async function connectWorld(page) {
  const snapshot = { viewer_id: 'player-test', viewer_is_owner: false, revision: 10, tick: 80, state: {
    name: "Founders' Settlement", clock: { minute: 600 },
    players: { 'player-test': { id: 'player-test', location: [24, 24], current_region: 'settlement', inventory: {}, energy: 90 } },
    npcs: {
      ada: { id: 'ada', name: 'Ada', role: 'engineer', current_region: 'settlement', location: [25, 24], route: { status: 'traveling', index: 0, path: [[25, 24], [25, 25]], destination_name: 'Meeting Hall' }, inventory: {}, needs: {}, intention: 'walk to the meeting hall' },
      traveler: { id: 'traveler', name: 'Rae', current_region: 'north_woods', location: [8, 9], inventory: {}, needs: {}, intention: 'gather timber' },
    },
    frontier: { size: 64 }, observed_tiles: {}, resource_sites: {}, communications: { messages: [] },
    event: { title: 'The Founding Table', phase: 0, priorities: ['water'] }, institutions: {},
    resources: {}, survival: {}, cooking: {},
  } };
  for (let x = 18; x <= 32; x++) for (let y = 18; y <= 32; y++) snapshot.state.observed_tiles[`${x},${y}`] = { position: [x, y], terrain: 'grassland', elevation: (x + y) % 3 };
  await page.addInitScript(() => {
    localStorage.setItem('userId', 'local-test');
    localStorage.setItem('currentCharacterId', 'character-test');
    localStorage.setItem('characterName', 'Traveler');
    sessionStorage.setItem('eovAccessToken', 'test-token');
    localStorage.setItem('eov-game-settings', JSON.stringify({ worldServerUrl: 'http://world.test' }));
  });
  await page.route('http://world.test/**', async route => {
    const request = route.request();
    if (request.url().endsWith('/health')) return route.fulfill({ json: { tick_seconds: 1, uptime_seconds: 7200 } });
    if (request.url().endsWith('/actions')) {
      expect(request.headers().authorization).toBe('Bearer test-token');
      const { action } = request.postDataJSON();
      if (action.type === 'speak') {
        expect(action.target_id).toBe('ada');
        const reply = { id: `reply-${++snapshot.revision}`, tick: 80, speaker: 'Ada', kind: 'reply', content: 'Hello. I can talk while I check the water.' };
        snapshot.state.communications.messages.push(reply);
        return route.fulfill({ json: { revision: snapshot.revision, result: { accepted: true, replies: [reply] } } });
      }
      if (action.type === 'travel_route') {
        snapshot.state.players['player-test'].location = action.destination;
        snapshot.revision++;
      }
      return route.fulfill({ json: { revision: snapshot.revision, result: { accepted: true } } });
    }
    return route.fulfill({ json: snapshot });
  });
  return snapshot;
}

test('a world tick racing speech is retried once without duplicating the action', async ({ page }) => {
  const snapshot = await connectWorld(page);
  const requests = [];
  await page.route('http://world.test/worlds/founders-settlement/actions', async route => {
    requests.push(route.request().postDataJSON());
    if (requests.length === 1) {
      snapshot.revision = 11;
      return route.fulfill({ status: 409, json: { detail: 'expected revision 10, current 11' } });
    }
    return route.fulfill({ json: { revision: 11, result: { accepted: true, replies: [{ id: 'raced-reply', speaker: 'Ada', content: 'I heard you despite the passing time.' }] } } });
  });
  await page.goto('/village');
  await expect(page.getByLabel('Story message')).toBeEnabled();
  await page.getByLabel('Story message').fill('Hello Ada');
  await page.getByRole('button', { name: 'Speak', exact: true }).click();
  await expect(page.getByText('I heard you despite the passing time.')).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1].action_id).toBe(requests[0].action_id);
});

test('only supported play modes are offered; legacy Unity links lead to isometric play', async ({ page }) => {
  await connectWorld(page);
  await page.goto('/select-mode');
  await expect(page.getByRole('button', { name: /Enter settlement/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Story chat/i })).toBeVisible();
  await expect(page.getByText(/Unity|First.Person|VR Embodiment|Earn VE\$/i)).toHaveCount(0);
  await page.goto('/unity');
  await expect(page).toHaveURL(/\/play$/);
});

for (const [path, label] of [['/village', 'Story message'], ['/play', 'Proximity chat message']]) {
  test(`${path} addresses a nearby Samaritan and shows the actual reply once`, async ({ page }) => {
    await connectWorld(page);
    await page.goto(path);
    if (path === '/play') await page.getByRole('button', { name: 'Open chat (T)' }).click();
    await expect(page.getByRole('textbox', { name: label })).toBeEnabled();
    await page.getByRole('textbox', { name: label }).fill('Hello Ada');
    await page.getByRole('button', { name: 'Speak', exact: true }).click();
    await expect(page.getByText('Hello. I can talk while I check the water.')).toHaveCount(1);
    await expect(page.getByText(/may respond when they choose|retains the ability|your words do not directly/i)).toHaveCount(0);
  });
}

test('zoom stays bounded and clicks use the follow camera beyond the starter plots', async ({ page }) => {
  await connectWorld(page);
  await page.goto('/play');
  await expect(page.getByLabel('Player position')).toHaveText('24, 24');
  await expect(page.locator('canvas')).toHaveAttribute('data-visible-npc-ids', 'ada');
  await expect(page.getByRole('button', { name: 'Inspect Ada' })).toContainText('Walking to Meeting Hall');
  await expect(page.getByRole('button', { name: 'Inspect Ada' })).toContainText('25, 24');
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  await expect(page.getByLabel('Map zoom')).toHaveText('75%');
  const canvas = page.locator('canvas');
  await expect.poll(() => canvas.evaluate(el => el.dataset.cameraX)).toBe('24.000');
  const box = await canvas.boundingBox();
  // From (24,24), tile (26,26) lies 64 world pixels south, scaled to 48.
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2 + 48);
  await expect(page.getByLabel('Player position')).toHaveText('26, 26');
  await expect.poll(() => canvas.evaluate(el => el.dataset.cameraX)).toBe('26.000');
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  await expect(page.getByLabel('Map zoom')).toHaveText('50%');
  await expect(page.getByRole('button', { name: 'Zoom out', exact: true })).toBeDisabled();
  await page.screenshot({ path: '../.superpowers/sdd/2026-09-10-alpha35-living-workshop/playable-isometric.png' });
});

test('T toggles proximity chat from the world and stays text while composing', async ({ page }) => {
  await connectWorld(page);
  await page.goto('/play');
  const canvas = page.locator('canvas');
  const chatToggle = page.getByRole('button', { name: 'Open chat (T)' });
  await expect(chatToggle).toHaveAttribute('aria-expanded', 'false');

  await canvas.focus();
  await page.keyboard.press('t');
  const message = page.getByRole('textbox', { name: 'Proximity chat message' });
  await expect(message).toBeVisible();
  await expect(page.getByRole('button', { name: 'Close chat (T)' })).toHaveAttribute('aria-expanded', 'true');

  await message.fill('');
  await page.keyboard.press('t');
  await expect(message).toHaveValue('t');
  await expect(message).toBeVisible();

  await page.getByRole('button', { name: 'Close chat', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Proximity chat message' })).toHaveCount(0);
});
