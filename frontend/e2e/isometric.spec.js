const { test, expect } = require('@playwright/test');

test('isometric world renders, responds, and restores persistent clock state', async ({ page }) => {
  await page.goto('/play');
  await expect(page.getByRole('region', { name: 'Private Jarvis owner workspace' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: "Founders' Settlement" })).toBeVisible();
  const canvas = page.getByRole('region', { name: 'Isometric settlement viewport' }).locator('canvas');
  await expect(canvas).toBeVisible();
  const visual = await canvas.evaluate((element) => {
    const context = element.getContext('2d');
    const colors = new Set();
    for (let y = 20; y < element.height; y += Math.max(20, Math.floor(element.height / 8))) {
      for (let x = 20; x < element.width; x += Math.max(20, Math.floor(element.width / 8))) {
        colors.add(Array.from(context.getImageData(x, y, 1, 1).data).join(','));
      }
    }
    return { width: element.width, height: element.height, distinctColors: colors.size };
  });
  expect(visual.width).toBeGreaterThan(700);
  expect(visual.height).toBeGreaterThan(500);
  expect(visual.distinctColors).toBeGreaterThan(2);
  await canvas.evaluate((element) => {
    const box = element.getBoundingClientRect();
    const clientX = box.left + box.width / 2 + (7 - 9) * 32;
    const clientY = box.top + 72 + (7 + 9) * 16;
    element.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX, clientY }));
  });
  await page.waitForTimeout(50);
  await canvas.evaluate((element) => {
    const box = element.getBoundingClientRect();
    const clientX = box.left + box.width / 2 + (7 - 9) * 32;
    const clientY = box.top + 72 + (7 + 9) * 16;
    element.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX, clientY }));
  });
  await expect(page.getByRole('heading', { name: 'Dev’s tool counter' })).toBeVisible();
  await page.getByRole('button', { name: /checkout.*Dev.*tool counter/i }).click();
  await expect(page.getByText(/Inventory axe 1/)).toBeVisible();
  await page.getByRole('textbox', { name: 'Proximity chat message' }).fill('Hello, what resources can we gather?');
  await page.getByRole('button', { name: 'Speak', exact: true }).click();
  await expect(page.getByText(/trees need an axe, seams need a pick/i).first()).toBeVisible();
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
});

test('Jarvis workspace is rendered only for the owner session profile', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('userId', 'owner-test-id');
    localStorage.setItem('isOwner', 'true');
    localStorage.setItem('permissionLevel', 'sirix_1');
  });
  await page.goto('/play');
  const jarvis = page.getByRole('region', { name: 'Private Jarvis owner workspace' });
  await expect(jarvis).toBeVisible();
  await jarvis.getByRole('button', { name: /Directives/ }).click();
  await expect(jarvis.getByText(/Connect the authenticated persistent-world server/)).toBeVisible();
  await expect(jarvis.getByRole('button', { name: 'Propose to council' })).toBeDisabled();
});

test('login does not advertise owner identity and continue requires a valid session', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('continue-journey-btn').click();
  await expect(page).toHaveURL(/\/auth$/);
  await expect(page.getByTestId('login-username')).toBeVisible();
  await expect(page.getByText(/sirix_1|luciferous/i)).toHaveCount(0);
});

test('authoritative stewardship and teaching consequences are visible with reasons and next actions', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('eov-game-settings', JSON.stringify({ worldServerUrl: 'http://world.test' }));
  });
  await page.route('http://world.test/worlds/founders-settlement', async (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ world_id: 'founders-settlement', revision: 44, tick: 80, state: {
      clock: { tick: 80, minute: 600 }, players: {},
      npcs: {
        cal: { id: 'cal', name: 'Cal', location: [8, 9], schedule: { shift_start: 7, shift_end: 17 }, needs: { nutrition: 70, hydration: 70, rest: 70 }, competency_records: { environmental_stewardship: { demonstrated: 0.65 } }, intention: 'teach Rae', reason: 'Verified work became teachable.' },
        mira: { id: 'mira', name: 'Mira', location: [8, 8], schedule: { shift_start: 8, shift_end: 17 }, needs: { nutrition: 70, hydration: 70, rest: 70 }, competency_records: { ecological_inspection: { demonstrated: 0.7 } }, intention: 'inspect teaching', reason: 'Learning requires evidence.' },
        rae: { id: 'rae', name: 'Rae', location: [8, 5], schedule: { shift_start: 8, shift_end: 18 }, needs: { nutrition: 70, hydration: 70, rest: 70 }, competency_records: { environmental_stewardship: { demonstrated: 0 } }, intention: 'seek supervised practice', reason: 'Instruction is not demonstrated competence.' },
      },
      resource_sites: {}, technology: { tool_catalog: {} }, communications: { messages: [] },
      event: { title: 'The Founding Table', phase: 0, priorities: ['settlement_meeting'] },
      environment: { regions: { settlement: { name: "Founders' Settlement", adjacent: [], stocks: {} } }, stewardship_orders: [{ id: 'stewardship-2', kind: 'reforestation', site_id: 'pine-stand', status: 'blocked_inputs', cause_stock: 2, worker: 'rae', inspector: 'mira', contract_id: 'contract-2', blockers: [{ status: 'unresolved', missing: { tested_water: 2 } }] }] },
      economy: { work_contracts: [{ id: 'contract-2', status: 'accepted', agreed: { rae: 9.5, mira: 4.75 }, spendable: false, valuation_basis: { multiplier: 1.25, regional_timber_scarcity: 0.2 } }] },
      education: { teaching_orders: [{ id: 'teaching-1', domain: 'environmental_stewardship', status: 'completed', instructor: 'cal', learner: 'rae', source_order_id: 'stewardship-1', demonstration: { before: 0, after: 0 }, learning: { theory: 0.05, observation: 0.04, procedure: 0.03, demonstrated_after: 0, requires_verified_practice: true } }], practice_orders: [{ id: 'practice-1', domain: 'environmental_stewardship', status: 'awaiting_real_work', learner: 'rae', supervisor: 'cal' }] },
      institutions: { council: { agenda: [], current_initiative: null }, governance: { resource_access: { mode: 'open_stores' }, checkouts: [] }, justice: { bounties: [], cases: [] } },
      resources: { safe_meals: 4, tested_water: 0 }, survival: { meal_history: [], rest_history: [], shortages: [] },
      cooking: { waste_portions: 0, work_orders: [], meal_batches: [], preservation_program: null }, water_system: { batches: [], work_orders: [] }, research: { designs: [] },
      shared_actions: {
        tools: { marked_measure: { condition: 0.98 } }, demands: [{ id: 'calibration-need', status: 'resolved', reason: 'verified calibration restored tool condition' }],
        records: { 'calibration-1': { id: 'calibration-1', state: 'commissioned', actor_id: 'ada', verifier_id: 'mira', intent: 'restore trustworthy settlement measurement', observations: ['measured drift'], output: { sample_count: 3, spread: 0.004 } } },
      },
    } }),
  }));
  await page.goto('/play');
  const panel = page.getByRole('region', { name: 'Persistent work and learning consequences' });
  await expect(panel).toBeVisible();
  await expect(panel.getByText('reforestation at pine-stand')).toBeVisible();
  await expect(panel.getByText('Blocked: missing 2 tested water')).toBeVisible();
  await expect(panel.getByText(/Next consequence: Supply the missing inputs/)).toBeVisible();
  await expect(panel.getByText(/contract-2.*rae 9.50 CU.*non-spendable/)).toBeVisible();
  await expect(panel.getByText(/Instruction gained theory 0.05.*Demonstrated competence remains 0.00/)).toBeVisible();
  await expect(panel.getByText(/rae supervised by cal/)).toBeVisible();
  await expect(page.getByText(/Canonical production work/)).toBeVisible();
  await expect(page.getByTestId('shared-action-record').getByText(/calibration-1.*commissioned/)).toBeVisible();
  await expect(page.getByTestId('shared-action-record').getByText(/performer ada.*verifier mira/)).toBeVisible();
});
