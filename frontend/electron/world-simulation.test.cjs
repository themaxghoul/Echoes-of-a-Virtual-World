const test = require('node:test');
const assert = require('node:assert/strict');
const { MAX_CATCHUP_TICKS, ACTIONS, initialSimulation, advanceSimulation, catchUpSimulation, acceptWorkOrder, playerAct, setProductionPriority, validateAction } = require('../src/lib/worldSimulation.cjs');

function acceptedSimulation() {
  const negotiated = advanceSimulation(initialSimulation(0), 24);
  assert.equal(negotiated.workOrder.status, 'negotiated');
  const accepted = acceptWorkOrder(negotiated);
  assert.equal(accepted.ok, true);
  return accepted.state;
}

function runSettlement(ticks = 600) {
  let state = acceptedSimulation();
  for (let remaining = ticks; remaining > 0; remaining -= MAX_CATCHUP_TICKS) state = advanceSimulation(state, Math.min(remaining, MAX_CATCHUP_TICKS));
  return state;
}

test('NPC work advances and completes the measurement workshop', () => {
  const state = runSettlement();
  assert.equal(state.workOrder.status, 'completed');
  assert.ok(state.workOrder.provisionalCU > 0);
  assert.ok(state.evidenceRecords.length > 0);
});

test('offline catch-up is bounded', () => {
  const state = initialSimulation(1);
  const caughtUp = catchUpSimulation(state, 1 + (MAX_CATCHUP_TICKS + 50) * 15000);
  assert.equal(caughtUp.clock.tick, MAX_CATCHUP_TICKS);
});

test('world clock and lived state survive a version migration before catch-up', () => {
  const legacy = initialSimulation(1_000_000);
  legacy.schema = 2;
  legacy.clock.tick = 777;
  legacy.clock.minute = 913;
  legacy.lastTickAt = 1_000_000;
  legacy.workOrder.status = 'completed';
  legacy.workOrder.stage = 3;
  legacy.npcs[0].x = 14;
  legacy.npcs[0].memories.push({ tick: 700, kind: 'completed_work', text: 'Preserve me.' });
  legacy.economy.accounts.ada = 42;
  const resumed = catchUpSimulation(legacy, 1_000_000 + 2 * 15000);
  assert.equal(resumed.schema, 3);
  assert.equal(resumed.clock.tick, 779);
  assert.equal(resumed.clock.minute, 923);
  assert.equal(resumed.workOrder.status, 'completed');
  assert.equal(resumed.npcs[0].x, 12); // Preserved at 14, then moved two catch-up ticks toward work.
  assert.ok(resumed.npcs[0].memories.some((memory) => memory.text === 'Preserve me.'));
  assert.equal(resumed.economy.accounts.ada, 42);
  assert.ok(resumed.events.some((event) => event.type === 'migration'));
});

test('an incomplete same-schema alpha save is repaired before rendering', () => {
  const damaged = initialSimulation(1_000_000);
  delete damaged.failures;
  delete damaged.economy.claims;
  delete damaged.workOrder.negotiation.responses;
  const resumed = catchUpSimulation(damaged, 1_000_000);
  assert.ok(Array.isArray(resumed.failures));
  assert.ok(Array.isArray(resumed.economy.claims));
  assert.ok(Array.isArray(resumed.workOrder.negotiation.responses));
  assert.equal(resumed.clock.tick, damaged.clock.tick);
});

test('player actions must match the current competency domain', () => {
  let state = acceptedSimulation();
  for (let index = 0; index < 80 && state.workOrder.status !== 'supplied'; index += 1) state = advanceSimulation(state, 1);
  assert.equal(state.workOrder.status, 'supplied');
  assert.equal(playerAct(state, 'engineering').ok, false);
  const result = playerAct(state, 'measurement');
  assert.equal(result.ok, true);
  assert.ok(result.state.workOrder.progress > 0);
});

test('shadow ledger remains double-entry balanced during continuous production', () => {
  const state = runSettlement();
  const balance = Object.values(state.economy.accounts).reduce((sum, amount) => sum + amount, 0);
  assert.ok(Math.abs(balance) < 0.001);
  assert.ok(state.economy.journal.length > 0);
  assert.ok(state.economy.claims.every((claim) => claim.status === 'verified'));
  assert.ok(Object.values(state.resources).every((amount) => amount >= 0));
  assert.ok(Object.values(state.economy.naturalStocks).every((amount) => amount >= 0));
});

test('work order cannot be accepted before all NPC negotiations', () => {
  const proposed = initialSimulation();
  assert.equal(acceptWorkOrder(proposed).ok, false);
  const negotiated = advanceSimulation(proposed, 24);
  assert.equal(negotiated.workOrder.negotiation.responses.length, 3);
  assert.equal(acceptWorkOrder(negotiated).ok, true);
});

test('NPCs retain schedules, inventories, intentions, and completed-work memories', () => {
  const state = runSettlement();
  state.npcs.forEach((npc) => {
    assert.ok(npc.schedule.shiftEnd > npc.schedule.shiftStart);
    assert.equal(typeof npc.inventory, 'object');
    assert.ok(npc.intentions.length > 0);
    assert.ok(npc.memories.some((memory) => memory.kind === 'completed_work'));
  });
});

test('all foundational actions declare time, access, tools, materials, and knowledge gates', () => {
  ['observe', 'measure', 'survey', 'carry', 'assemble', 'inspect', 'document', 'teach', 'eat', 'rest'].forEach((action) => {
    assert.ok(ACTIONS[action].time >= 1);
    assert.ok(ACTIONS[action].access);
    assert.ok(Array.isArray(ACTIONS[action].tools));
    assert.ok(Object.hasOwn(ACTIONS[action], 'competence'));
  });
});

test('tool and evidence shortages stop actions', () => {
  const state = initialSimulation();
  state.tools.tape_measure.location = 'storehouse';
  assert.equal(validateAction(state, state.npcs[0], 'measure', [7, 7]).ok, false);
  assert.equal(validateAction(state, state.npcs[2], 'inspect', [8, 7]).ok, false);
});

test('physical evidence identifies actors, inputs, tools, measurements, and inspector', () => {
  const state = runSettlement();
  const physical = state.evidenceRecords.filter((record) => record.physical);
  assert.ok(physical.length > 0);
  assert.ok(physical.every((record) => record.actors.length > 0 && Array.isArray(record.tools) && record.inspector === 'mira'));
  assert.ok(physical.some((record) => Object.keys(record.inputs).length > 0));
  assert.ok(state.evidenceRecords.some((record) => Object.keys(record.measurements).length > 0));
});

test('public production priority changes through an explicit contract choice', () => {
  const state = setProductionPriority(initialSimulation(), 'water');
  assert.equal(state.economy.productionPriority, 'water');
  assert.ok(state.events.some((event) => event.type === 'contract_priority'));
});
