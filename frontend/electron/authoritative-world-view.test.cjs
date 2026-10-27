const test = require('node:test');
const assert = require('node:assert/strict');
const { projectAuthoritativeWork } = require('../src/lib/authoritativeWorldView.cjs');

test('projects blockers, spatial actors, teaching provenance, and learned capability', () => {
  const view = projectAuthoritativeWork({
    environment: { stewardship_orders: [{ id: 'stewardship-1', kind: 'reforestation', site_id: 'old-oak', status: 'blocked_inputs', cause_stock: 2, worker: 'cal', inspector: 'mira', contract_id: 'contract-1', blockers: [{ status: 'unresolved', missing: { tested_water: 2 } }] }] },
    economy: { work_contracts: [{ id: 'contract-1', status: 'accepted', agreed: { cal: 9.5, mira: 4.75 }, spendable: false, valuation_basis: { regional_timber_scarcity: 0.2, multiplier: 1.25 } }] },
    education: { teaching_orders: [{ id: 'teaching-1', domain: 'environmental_stewardship', status: 'completed', instructor: 'cal', learner: 'rae', source_order_id: 'stewardship-1', demonstration: { before: 0, after: 0 }, learning: { theory: 0.05, observation: 0.04, procedure: 0.03, demonstrated_after: 0, requires_verified_practice: true } }], practice_orders: [{ id: 'practice-1', domain: 'environmental_stewardship', status: 'awaiting_real_work', learner: 'rae', supervisor: 'cal' }] },
    npcs: {
      cal: { id: 'cal', name: 'Cal', location: [8, 9], competency_records: { environmental_stewardship: { demonstrated: 0.65 } } },
      mira: { id: 'mira', name: 'Mira', location: [8, 8], competency_records: { ecological_inspection: { demonstrated: 0.7 } } },
      rae: { id: 'rae', name: 'Rae', location: [8, 5], competency_records: { environmental_stewardship: { demonstrated: 0 } } },
    },
  });
  assert.equal(view.stewardship[0].missing, '2 tested water');
  assert.deepEqual(view.stewardship[0].workerLocation, [8, 9]);
  assert.equal(view.teaching[0].source, 'stewardship-1');
  assert.equal(view.teaching[0].after, 0);
  assert.equal(view.teaching[0].learning.requires_verified_practice, true);
  assert.equal(view.practices[0].status, 'awaiting real work');
  assert.equal(view.stewardship[0].contract.agreed.cal, 9.5);
  assert.equal(view.stewardship[0].contract.spendable, false);
  assert.deepEqual(view.capabilities.map((item) => item.npcId), ['mira', 'cal', 'rae']);
});

test('returns no fabricated work for an older sparse world', () => {
  assert.deepEqual(projectAuthoritativeWork({ npcs: {} }), { stewardship: [], teaching: [], practices: [], capabilities: [], maintenance: [], commitments: [], extraction: [] });
});

test('projects canonical field repair evidence and actor custody', () => {
  const view = projectAuthoritativeWork({
    npcs: { ada: { id: 'ada', name: 'Ada', location: [10, 12], competency_records: {} } },
    resource_sites: { 'well-site': { id: 'well-site', name: 'Shallow well', location: [11, 13], installed_pump: { condition: 0.84 } } },
    institutions: { governance: { maintenance_orders: [{ id: 'maintenance-1', site_id: 'well-site', status: 'open', condition: 0.3, assigned_to: 'ada', canonical_action_id: 'repair-1', blockers: [{ status: 'unresolved', missing: ['containers'] }] }] } },
    shared_actions: {
      actor_commitments: { ada: { action_id: 'repair-1', role: 'performer', since_tick: 8 } },
      records: { 'repair-1': { id: 'repair-1', state: 'submitted', actor_id: 'ada', verifier_id: null, output: { condition_before: 0.3, condition_after: 0.84 } } },
    },
  });
  assert.equal(view.maintenance[0].actionState, 'submitted');
  assert.equal(view.maintenance[0].missing, 'containers');
  assert.equal(view.maintenance[0].conditionAfter, 0.84);
  assert.equal(view.maintenance[0].commitment.action_id, 'repair-1');
  assert.deepEqual(view.commitments.map((item) => item.actorId), ['ada']);
});

test('projects finite extraction separately from later transport custody', () => {
  const view = projectAuthoritativeWork({
    npcs: {}, resource_sites: { oak: { name: 'Old oak', location: [8, 9] } },
    shared_actions: { actor_commitments: {}, records: { gather: { id: 'gather', state: 'commissioned', actor_id: 'cal', verifier_id: 'mira', target_id: 'oak', definition: { action_type: 'extract_site_resource', output_item: 'timber', output_amount: 2, output_custody: 'actor_inventory' }, output: { stock_before: 10, stock_after: 8, observed_yield: 2, conserved: true } } } },
  });
  assert.equal(view.extraction[0].resource, 'timber');
  assert.equal(view.extraction[0].custody, 'actor_inventory');
  assert.equal(view.extraction[0].conserved, true);
});
