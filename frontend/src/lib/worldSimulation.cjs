const TICK_MS = 15000;
const MAX_CATCHUP_TICKS = 240;
const WORKSHOP_REQUIREMENTS = { timber: 8, stone: 6, components: 4 };

const ACTIONS = {
  observe: { time: 1, domain: 'measurement', competence: 0, tools: [], access: 'worksite' },
  measure: { time: 2, domain: 'measurement', competence: 0.25, tools: ['tape_measure'], access: 'worksite' },
  survey: { time: 3, domain: 'measurement', competence: 0.35, tools: ['tape_measure', 'survey_stakes'], access: 'worksite' },
  carry: { time: 2, domain: 'logistics', competence: 0.2, tools: ['handcart'], access: 'storehouse' },
  assemble: { time: 4, domain: 'engineering', competence: 0.4, tools: ['hammer', 'wrench'], access: 'worksite' },
  inspect: { time: 3, domain: 'science', competence: 0.5, tools: ['inspection_gauge'], access: 'worksite', evidence: 'performed' },
  document: { time: 2, domain: 'science', competence: 0.25, tools: ['notebook'], access: 'worksite' },
  teach: { time: 3, domain: 'science', competence: 0.6, tools: ['manual'], access: 'worksite' },
  eat: { time: 2, domain: null, competence: 0, tools: [], access: 'storehouse', materials: { food: 1 } },
  rest: { time: 4, domain: null, competence: 0, tools: [], access: 'hall' },
};

const STAGES = [
  { id: 'observe', action: 'observe', label: 'Observe site conditions', domain: 'measurement', target: [7, 7], effort: 8 },
  { id: 'measure', action: 'measure', label: 'Measure site geometry', domain: 'measurement', target: [7, 7], effort: 14 },
  { id: 'survey', action: 'survey', label: 'Survey and mark foundations', domain: 'measurement', target: [8, 7], effort: 18 },
  { id: 'assemble', action: 'assemble', label: 'Assemble measured workbench', domain: 'engineering', target: [8, 7], effort: 36 },
  { id: 'document', action: 'document', label: 'Document methods and results', domain: 'science', target: [8, 7], effort: 16 },
];

const clamp = (value, min = 0, max = 100) => Math.max(min, Math.min(max, value));
const clone = (value) => JSON.parse(JSON.stringify(value));
const ECONOMIC_TARGETS = { timber: 20, stone: 15, components: 8, food: 30, water: 40, researchEvidence: 4 };

function initialEconomy() {
  return { mode: 'shadow', productionPriority: 'food', naturalStocks: { timber: 240, stone: 180, foodPotential: 360, waterTable: 600 }, prices: { timber: 3, stone: 4, components: 12, food: 2, water: 1, researchEvidence: 18 }, accounts: { treasury: 0, ada: 0, orin: 0, mira: 0, sirix_1: 0 }, journal: [], claims: [], totalOutputValue: 0 };
}

function newWorkOrder() {
  return {
    id: 'measurement-workshop-002', title: 'Construct measurement workshop', status: 'proposed',
    lifecycle: [{ status: 'proposed', tick: 0, actor: 'Treasury', evidence: 'public-need:measurement-capacity' }],
    negotiation: { responses: [] }, requirements: clone(WORKSHOP_REQUIREMENTS), supplied: { timber: 0, stone: 0, components: 0 },
    stage: 0, progress: 0, inspectionProgress: 0, provisionalCU: 0, contributions: {},
  };
}

function newNpc(id, name, role, x, y, color, needs, competencies, schedule) {
  return { id, name, role, x, y, color, needs, competencies, knowledge: Object.keys(competencies).filter((domain) => competencies[domain] >= 0.3), access: ['hall', 'storehouse', 'worksite'], schedule, inventory: {}, inventoryCapacity: 8, task: null, intentions: [], memories: [] };
}

function initialSimulation(now = Date.now()) {
  return {
    schema: 3, lastTickAt: now, clock: { tick: 0, minute: 8 * 60, paused: false },
    resources: { timber: 24, stone: 18, components: 10, food: 36, water: 48, researchEvidence: 0 }, economy: initialEconomy(),
    tools: {
      tape_measure: { location: 'worksite', condition: 0.95 }, survey_stakes: { location: 'worksite', condition: 1 },
      handcart: { location: 'storehouse', condition: 0.9 }, hammer: { location: 'worksite', condition: 0.92 }, wrench: { location: 'worksite', condition: 0.9 },
      inspection_gauge: { location: 'worksite', condition: 0.96 }, notebook: { location: 'worksite', condition: 1 }, manual: { location: 'worksite', condition: 1 },
    },
    player: { competencies: { measurement: 0.35, logistics: 0.3, engineering: 0.2, science: 0.25 }, access: ['hall', 'storehouse', 'worksite'] }, workOrder: newWorkOrder(),
    npcs: [
      newNpc('ada', 'Ada', 'AI Engineer', 10, 7, '#67e8f9', { nutrition: 82, hydration: 84, rest: 76, belonging: 70 }, { measurement: 0.8, logistics: 0.3, engineering: 0.75, science: 0.65 }, { shiftStart: 8, shiftEnd: 18, restLocation: [8, 5] }),
      newNpc('orin', 'Orin', 'Builder', 6, 9, '#fbbf24', { nutrition: 76, hydration: 78, rest: 84, belonging: 62 }, { measurement: 0.35, logistics: 0.8, engineering: 0.7, science: 0.2 }, { shiftStart: 7, shiftEnd: 17, restLocation: [8, 5] }),
      newNpc('mira', 'Mira', 'Researcher', 11, 11, '#c084fc', { nutrition: 88, hydration: 82, rest: 68, belonging: 74 }, { measurement: 0.7, logistics: 0.25, engineering: 0.3, science: 0.85 }, { shiftStart: 9, shiftEnd: 19, restLocation: [8, 5] }),
    ],
    evidenceRecords: [], failures: [],
    events: [{ tick: 0, type: 'work_order', actor: 'Treasury', text: 'Measurement workshop proposed for negotiation.' }],
  };
}

function ensureSimulation(input) {
  if (!input || typeof input !== 'object') return initialSimulation();
  const isComplete = input.schema === 3
    && input.clock && Array.isArray(input.npcs) && Array.isArray(input.events)
    && Array.isArray(input.evidenceRecords) && Array.isArray(input.failures)
    && input.workOrder?.lifecycle && Array.isArray(input.workOrder?.negotiation?.responses)
    && input.economy?.accounts && Array.isArray(input.economy?.journal)
    && Array.isArray(input.economy?.claims);
  if (isComplete) return input;
  const migrated = initialSimulation(input.lastTickAt || Date.now());
  migrated.lastTickAt = input.lastTickAt || migrated.lastTickAt;
  migrated.clock = { ...migrated.clock, ...(input.clock || {}) };
  migrated.resources = { ...migrated.resources, ...(input.resources || {}) };
  migrated.economy = input.economy ? { ...migrated.economy, ...input.economy, naturalStocks: { ...migrated.economy.naturalStocks, ...(input.economy.naturalStocks || {}) }, prices: { ...migrated.economy.prices, ...(input.economy.prices || {}) }, accounts: { ...migrated.economy.accounts, ...(input.economy.accounts || {}) }, journal: Array.isArray(input.economy.journal) ? input.economy.journal : [], claims: Array.isArray(input.economy.claims) ? input.economy.claims : [] } : migrated.economy;
  migrated.player = { ...migrated.player, ...(input.player || {}), competencies: { ...migrated.player.competencies, ...(input.player?.competencies || {}) }, access: input.player?.access || migrated.player.access };
  migrated.tools = { ...migrated.tools, ...(input.tools || {}) };
  if (input.workOrder) {
    const legacyStageMap = { 0: 2, 1: 3, 2: 4 };
    const preservedStage = input.workOrder.status === 'completed' ? STAGES.length : (input.schema < 3 ? (legacyStageMap[input.workOrder.stage] ?? input.workOrder.stage ?? 0) : input.workOrder.stage);
    migrated.workOrder = {
      ...migrated.workOrder, ...input.workOrder, stage: preservedStage,
      lifecycle: input.workOrder.lifecycle || migrated.workOrder.lifecycle,
      negotiation: { ...migrated.workOrder.negotiation, ...(input.workOrder.negotiation || {}), responses: Array.isArray(input.workOrder.negotiation?.responses) ? input.workOrder.negotiation.responses : [] },
      requirements: { ...migrated.workOrder.requirements, ...(input.workOrder.requirements || {}) },
      supplied: { ...migrated.workOrder.supplied, ...(input.workOrder.supplied || {}) },
      contributions: input.workOrder.contributions || {},
    };
  }
  const oldNpcs = new Map((input.npcs || []).map((npc) => [npc.id, npc]));
  migrated.npcs = migrated.npcs.map((baseNpc) => {
    const old = oldNpcs.get(baseNpc.id); if (!old) return baseNpc;
    return { ...baseNpc, ...old, needs: { ...baseNpc.needs, ...(old.needs || {}) }, competencies: { ...baseNpc.competencies, ...(old.competencies || {}) }, schedule: { ...baseNpc.schedule, ...(old.schedule || {}) }, inventory: old.inventory || {}, intentions: old.intentions || [], memories: old.memories || [], knowledge: old.knowledge || baseNpc.knowledge, access: old.access || baseNpc.access };
  });
  migrated.evidenceRecords = input.evidenceRecords || [];
  migrated.failures = input.failures || [];
  migrated.events = [{ tick: migrated.clock.tick, type: 'migration', actor: 'Ledger', text: `World schema upgraded in place at tick ${migrated.clock.tick}; simulation continuity preserved.` }, ...(input.events || [])].slice(0, 60);
  return migrated;
}

function addEvent(state, type, actor, text) { state.events.unshift({ tick: state.clock.tick, type, actor, text }); state.events = state.events.slice(0, 60); }
function remember(npc, kind, text, tick) { npc.memories.unshift({ tick, kind, text }); npc.memories = npc.memories.slice(0, 30); }
function transition(state, status, actor, evidence) { state.workOrder.status = status; state.workOrder.lifecycle.push({ status, tick: state.clock.tick, actor, evidence }); addEvent(state, 'work_order', actor, `Workshop ${status}.`); }
function moveToward(npc, target) { if (npc.x !== target[0]) npc.x += Math.sign(target[0] - npc.x); else if (npc.y !== target[1]) npc.y += Math.sign(target[1] - npc.y); }
function atTarget(npc, target) { return npc.x === target[0] && npc.y === target[1]; }
function inventoryTotal(npc) { return Object.values(npc.inventory).reduce((sum, value) => sum + value, 0); }
function locationForTarget(target) { if (target[0] === 5 && target[1] === 11) return 'storehouse'; if (target[0] === 8 && target[1] === 5) return 'hall'; return 'worksite'; }
function addFailure(state, actor, action, reason) {
  const last = state.failures[0];
  if (last?.actor === actor && last?.action === action && last?.reason === reason && state.clock.tick - last.tick < 6) return;
  state.failures.unshift({ tick: state.clock.tick, actor, action, reason, recovered: false }); state.failures = state.failures.slice(0, 40);
  addEvent(state, 'work_stopped', actor, `${action} stopped: ${reason}`);
}
function validateAction(state, actor, actionId, target) {
  const action = ACTIONS[actionId]; if (!action) return { ok: false, reason: 'unknown action' };
  const location = locationForTarget(target);
  if (!(actor.access || []).includes(action.access || location)) return { ok: false, reason: `no ${action.access || location} access` };
  if (actor.needs && (actor.needs.rest < 18 || actor.needs.nutrition < 18 || actor.needs.hydration < 18) && !['eat', 'rest'].includes(actionId)) return { ok: false, reason: 'insufficient energy, food, or water' };
  if (action.domain && (actor.competencies[action.domain] || 0) < action.competence) return { ok: false, reason: `${action.domain} competence below ${action.competence}` };
  const missingTool = action.tools.find((tool) => state.tools[tool]?.condition <= 0 || (state.tools[tool]?.location !== location && !actor.inventory[tool]));
  if (missingTool) return { ok: false, reason: `${missingTool} unavailable at ${location}` };
  if (action.materials) { const missing = Object.entries(action.materials).find(([item, amount]) => state.resources[item] < amount); if (missing) return { ok: false, reason: `${missing[0]} shortage` }; }
  if (action.evidence && state.workOrder.status !== action.evidence) return { ok: false, reason: `${action.evidence} evidence required` };
  return { ok: true, action, location };
}
function recordEvidence(state, record) { state.evidenceRecords.unshift({ id: `evidence-${state.clock.tick}-${state.evidenceRecords.length}`, tick: state.clock.tick, ...record }); state.evidenceRecords = state.evidenceRecords.slice(0, 100); }
function actionReady(state, npc) { const duration = ACTIONS[npc.task.action]?.time || 1; const since = npc.task.lastCompletedTick ?? npc.task.startedTick; return state.clock.tick - since + 1 >= duration; }
function completeAction(state, npc) { npc.task.lastCompletedTick = state.clock.tick; state.failures.forEach((failure) => { if (!failure.recovered && failure.actor === npc.name && failure.action === npc.task.action) { failure.recovered = true; failure.recoveredAtTick = state.clock.tick; } }); }

function postTransfer(state, from, to, amount, memo, evidence) {
  const value = Math.max(0, Math.round(amount * 100) / 100); if (!value) return;
  state.economy.accounts[from] = (state.economy.accounts[from] || 0) - value; state.economy.accounts[to] = (state.economy.accounts[to] || 0) + value;
  state.economy.journal.unshift({ id: `tx-${state.clock.tick}-${state.economy.journal.length}`, tick: state.clock.tick, from, to, amount: value, memo, evidence }); state.economy.journal = state.economy.journal.slice(0, 100);
}
function recordClaim(state, actor, kind, quantity, unitValue, evidence) {
  const amount = Math.round(quantity * unitValue * 100) / 100; state.economy.claims.unshift({ id: `claim-${state.clock.tick}-${actor}-${kind}`, tick: state.clock.tick, actor, kind, quantity, unitValue, amount, status: 'verified', evidence }); state.economy.claims = state.economy.claims.slice(0, 100);
  postTransfer(state, 'treasury', actor, amount, `${kind} verified output`, evidence); state.economy.totalOutputValue += amount;
}
function updatePrices(state) { Object.keys(state.economy.prices).forEach((commodity) => { const stock = state.resources[commodity] || 0; const target = ECONOMIC_TARGETS[commodity] || 1; const scarcity = clamp((target - stock) / target, -0.5, 1); state.economy.prices[commodity] = Math.round(clamp(state.economy.prices[commodity] * (1 + scarcity * 0.025), 0.25, 100) * 100) / 100; }); }

function onShift(state, npc) { const hour = Math.floor(state.clock.minute / 60); return hour >= npc.schedule.shiftStart && hour < npc.schedule.shiftEnd; }

function chooseTask(state, npc) {
  if (npc.needs.nutrition < 28) return { type: 'eat', action: 'eat', label: 'Eat a meal', target: [5, 11] };
  if (npc.needs.hydration < 32 && state.resources.water > 0) return { type: 'drink', label: 'Collect water', target: [5, 11] };
  if (!onShift(state, npc) || npc.needs.rest < 24) return { type: 'rest', action: 'rest', label: onShift(state, npc) ? 'Recover from fatigue' : 'Off shift', target: npc.schedule.restLocation };
  const order = state.workOrder;
  if (order.status === 'proposed' && !order.negotiation.responses.some((response) => response.npcId === npc.id)) return { type: 'negotiate', label: 'Review workshop terms', target: [8, 5] };
  if (order.status === 'negotiated') return { type: 'idle', label: 'Await contract acceptance', target: [8, 5] };
  if (order.status === 'accepted') {
    if (npc.id !== 'orin') return { type: 'idle', label: 'Await supplied worksite', target: [8, 5] };
    return inventoryTotal(npc) > 0 ? { type: 'deliver', action: 'carry', label: 'Deliver workshop supplies', target: [8, 7] } : { type: 'collect', action: 'carry', label: 'Collect workshop supplies', target: [5, 11] };
  }
  const stage = STAGES[order.stage];
  if (order.status === 'supplied' && stage) {
    const requirement = ACTIONS[stage.action].competence;
    const learner = state.npcs.find((candidate) => (candidate.competencies[stage.domain] || 0) < requirement);
    if (learner && learner.id !== npc.id && (npc.competencies[stage.domain] || 0) >= requirement + 0.2 && (npc.competencies.science || 0) >= ACTIONS.teach.competence && state.clock.tick % 10 < 3) return { type: 'teach', action: 'teach', learnerId: learner.id, domain: stage.domain, label: `Teach ${learner.name} ${stage.domain}`, target: stage.target };
    return (npc.competencies[stage.domain] || 0) >= requirement ? { type: 'work', action: stage.action, label: stage.label, target: stage.target } : { type: 'observe', action: 'observe', label: `Observe ${stage.label.toLowerCase()}`, target: stage.target };
  }
  if (order.status === 'performed') return npc.id === 'mira' ? { type: 'inspect', action: 'inspect', label: 'Reproduce and inspect results', target: [8, 7] } : { type: 'idle', label: 'Await independent inspection', target: [8, 5] };
  if (order.status === 'inspected') return { type: 'idle', label: 'Await completion record', target: [8, 5] };
  if (order.status === 'completed') {
    const tasks = { ada: { type: 'produce', output: 'components', label: 'Fabricate measured components', target: [8, 7] }, orin: { type: 'produce', output: state.economy.productionPriority === 'water' ? 'water' : 'food', label: state.economy.productionPriority === 'water' ? 'Draw and test water' : 'Cultivate and deliver food', target: [5, 11] }, mira: { type: 'produce', output: 'researchEvidence', label: 'Reproduce workshop research', target: [8, 7] } };
    return tasks[npc.id];
  }
  return { type: 'idle', label: 'Observe settlement', target: [8, 9] };
}

function processNegotiation(state, npc) {
  if (npc.task.type !== 'negotiate' || !atTarget(npc, npc.task.target)) return;
  if (state.workOrder.negotiation.responses.some((response) => response.npcId === npc.id)) return;
  const domain = npc.id === 'ada' ? 'engineering' : npc.id === 'orin' ? 'logistics' : 'science';
  const response = { npcId: npc.id, actor: npc.name, domain, requestedRate: Math.round((4 + (npc.competencies[domain] || 0) * 8) * 100) / 100, condition: npc.id === 'mira' ? 'Independent reproduction required' : npc.id === 'orin' ? 'Materials supplied before labor' : 'Measurements recorded before assembly', tick: state.clock.tick };
  state.workOrder.negotiation.responses.push(response); remember(npc, 'negotiation', `Proposed ${domain} terms for the measurement workshop.`, state.clock.tick); addEvent(state, 'negotiation', npc.name, response.condition);
  if (state.workOrder.negotiation.responses.length === state.npcs.length) transition(state, 'negotiated', 'Ada, Orin, and Mira', 'three-recorded-responses');
}

function processSupply(state, npc) {
  if (npc.id !== 'orin') return;
  if (npc.task.type === 'collect' && atTarget(npc, npc.task.target)) {
    const check = validateAction(state, npc, 'carry', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'carry', check.reason); return; }
    let collected = false;
    for (const [material, required] of Object.entries(state.workOrder.requirements)) {
      const remaining = required - state.workOrder.supplied[material] - (npc.inventory[material] || 0);
      if (remaining <= 0 || state.resources[material] <= 0 || inventoryTotal(npc) >= npc.inventoryCapacity) continue;
      const amount = Math.min(remaining, state.resources[material], npc.inventoryCapacity - inventoryTotal(npc)); npc.inventory[material] = (npc.inventory[material] || 0) + amount; state.resources[material] -= amount; collected = true; completeAction(state, npc); break;
    }
    if (!collected && inventoryTotal(npc) === 0) addFailure(state, npc.name, 'carry', 'required workshop materials are unavailable');
  } else if (npc.task.type === 'deliver' && atTarget(npc, npc.task.target)) {
    completeAction(state, npc);
    Object.entries(npc.inventory).forEach(([material, amount]) => { state.workOrder.supplied[material] += amount; }); npc.inventory = {};
    addEvent(state, 'supply', npc.name, 'Delivered traceable workshop materials.');
    const complete = Object.entries(state.workOrder.requirements).every(([material, required]) => state.workOrder.supplied[material] >= required);
    if (complete) { remember(npc, 'completed_work', 'Supplied the measurement workshop with recorded materials.', state.clock.tick); transition(state, 'supplied', npc.name, 'inventory-transfer:workshop'); }
  }
}

function tickSimulation(input) {
  const state = ensureSimulation(clone(input)); state.clock.tick += 1; state.clock.minute = (state.clock.minute + 5) % 1440;
  const stage = STAGES[state.workOrder.stage];
  state.npcs.forEach((npc) => {
    npc.needs.nutrition = clamp(npc.needs.nutrition - 0.45); npc.needs.hydration = clamp(npc.needs.hydration - 0.55); npc.needs.rest = clamp(npc.needs.rest - 0.28); npc.needs.belonging = clamp(npc.needs.belonging - 0.08);
    const previousTask = npc.task; const oldTask = previousTask?.label; npc.task = chooseTask(state, npc);
    if (previousTask?.type === npc.task.type && previousTask?.action === npc.task.action && previousTask?.label === npc.task.label) { npc.task.startedTick = previousTask.startedTick; npc.task.lastCompletedTick = previousTask.lastCompletedTick; } else npc.task.startedTick = state.clock.tick;
    npc.task.reason = npc.task.type === 'eat' ? 'Nutrition fell below the safe threshold.' : npc.task.type === 'drink' ? 'Hydration fell below the safe threshold.' : npc.task.type === 'rest' ? (onShift(state, npc) ? 'Fatigue interrupted work.' : 'The scheduled shift ended.') : npc.task.type === 'collect' || npc.task.type === 'deliver' ? 'The accepted contract is not fully supplied.' : npc.task.type === 'work' ? `Competence and tools permit ${npc.task.action}.` : npc.task.type === 'inspect' ? 'Performed work requires independent evidence.' : npc.task.type === 'teach' ? 'A nearby participant lacks required competence.' : `Workshop status is ${state.workOrder.status}.`;
    if (npc.task.label !== oldTask) { npc.intentions.unshift({ tick: state.clock.tick, text: npc.task.label }); npc.intentions = npc.intentions.slice(0, 20); addEvent(state, 'intent', npc.name, npc.task.label); }
    moveToward(npc, npc.task.target); if (!atTarget(npc, npc.task.target)) return;
    if (npc.task.action && !actionReady(state, npc)) return;
    if (npc.task.type === 'eat') { const check = validateAction(state, npc, 'eat', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'eat', check.reason); return; } completeAction(state, npc); state.resources.food -= 1; npc.needs.nutrition = clamp(npc.needs.nutrition + 28); postTransfer(state, npc.id, 'treasury', state.economy.prices.food, 'Settlement meal', `need:${npc.id}:nutrition`); return; }
    if (npc.task.type === 'drink' && state.resources.water > 0) { state.resources.water -= 1; npc.needs.hydration = clamp(npc.needs.hydration + 34); postTransfer(state, npc.id, 'treasury', state.economy.prices.water, 'Settlement water', `need:${npc.id}:hydration`); return; }
    if (npc.task.type === 'rest') { const check = validateAction(state, npc, 'rest', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'rest', check.reason); return; } completeAction(state, npc); npc.needs.rest = clamp(npc.needs.rest + 7); return; }
    processNegotiation(state, npc); processSupply(state, npc);
    if (npc.task.type === 'observe' && stage) { const check = validateAction(state, npc, 'observe', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'observe', check.reason); return; } completeAction(state, npc); npc.competencies[stage.domain] = clamp((npc.competencies[stage.domain] || 0) + 0.004, 0, 1); return; }
    if (npc.task.type === 'teach' && stage) { const check = validateAction(state, npc, 'teach', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'teach', check.reason); return; } completeAction(state, npc); const learner = state.npcs.find((candidate) => candidate.id === npc.task.learnerId); learner.competencies[npc.task.domain] = clamp((learner.competencies[npc.task.domain] || 0) + 0.012, 0, 1); remember(learner, 'teaching', `${npc.name} taught ${npc.task.domain} at the worksite.`, state.clock.tick); return; }
    if (npc.task.type === 'work' && stage) { const check = validateAction(state, npc, stage.action, npc.task.target); if (!check.ok) { addFailure(state, npc.name, stage.action, check.reason); return; } completeAction(state, npc); const contribution = 0.75 + (npc.competencies[stage.domain] || 0) * 1.5; state.workOrder.progress += contribution; state.workOrder.contributions[npc.id] = (state.workOrder.contributions[npc.id] || 0) + contribution; npc.competencies[stage.domain] = clamp((npc.competencies[stage.domain] || 0) + 0.002, 0, 1); }
    if (npc.task.type === 'inspect') { const check = validateAction(state, npc, 'inspect', npc.task.target); if (!check.ok) { addFailure(state, npc.name, 'inspect', check.reason); return; } completeAction(state, npc); state.workOrder.inspectionProgress += 0.8 + npc.competencies.science * 1.4; }
  });

  if (state.clock.tick % 18 === 0) {
    for (let first = 0; first < state.npcs.length; first += 1) for (let second = first + 1; second < state.npcs.length; second += 1) {
      const a = state.npcs[first]; const b = state.npcs[second]; if (a.x === b.x && a.y === b.y) { a.needs.belonging = clamp(a.needs.belonging + 5); b.needs.belonging = clamp(b.needs.belonging + 5); remember(a, 'conversation', `Discussed ${state.workOrder.status} workshop work with ${b.name}.`, state.clock.tick); remember(b, 'conversation', `Discussed ${state.workOrder.status} workshop work with ${a.name}.`, state.clock.tick); addEvent(state, 'conversation', `${a.name} and ${b.name}`, `Compared plans and evidence for the ${state.workOrder.status} workshop.`); }
    }
  }

  if (state.workOrder.status === 'supplied' && stage && state.workOrder.progress >= stage.effort) {
    const stageValue = Math.round(stage.effort * 1.5); state.workOrder.provisionalCU += stageValue; const contributions = state.workOrder.contributions; const totalContribution = Object.values(contributions).reduce((sum, value) => sum + value, 0);
    Object.entries(contributions).forEach(([actorId, contribution]) => { const share = totalContribution ? stageValue * contribution / totalContribution : 0; recordClaim(state, actorId, stage.id, contribution, share / contribution, `work-order:${state.workOrder.id}:${stage.id}`); const npc = state.npcs.find((candidate) => candidate.id === actorId); if (npc) remember(npc, 'completed_work', `${stage.label} completed and recorded.`, state.clock.tick); });
    const tools = ACTIONS[stage.action].tools; const measurements = stage.action === 'measure' || stage.action === 'survey' ? { unit: 'tile', uncertainty: 0.05, method: stage.action } : {};
    recordEvidence(state, { change: stage.label, physical: ['survey', 'assemble'].includes(stage.action), actors: Object.keys(contributions), inputs: stage.action === 'assemble' ? clone(state.workOrder.supplied) : {}, tools, measurements, inspector: null, status: 'performed' });
    addEvent(state, 'verified_work', 'Settlement', `${stage.label} performed with recorded participants.`); state.workOrder.stage += 1; state.workOrder.progress = 0;
    state.workOrder.contributions = {};
    if (state.workOrder.stage >= STAGES.length) transition(state, 'performed', 'Qualified participants', 'stage-evidence-complete');
  }
  if (state.workOrder.status === 'performed' && state.workOrder.inspectionProgress >= 20) { const mira = state.npcs.find((npc) => npc.id === 'mira'); remember(mira, 'completed_work', 'Independently reproduced and inspected workshop measurements.', state.clock.tick); state.evidenceRecords.forEach((record) => { if (!record.inspector) { record.inspector = 'mira'; record.inspectionTool = 'inspection_gauge'; record.inspectedAtTick = state.clock.tick; } }); recordClaim(state, 'mira', 'inspection', 1, 12, `inspection:${state.workOrder.id}`); transition(state, 'inspected', 'Mira', 'independent-reproduction'); }
  else if (state.workOrder.status === 'inspected') { state.npcs.forEach((npc) => remember(npc, 'completed_work', 'Measurement workshop contract completed.', state.clock.tick)); transition(state, 'completed', 'Causal Ledger', 'lifecycle-and-evidence-complete'); }

  if (state.workOrder.status === 'completed' && state.clock.tick % 12 === 0) {
    state.npcs.forEach((npc) => { if (npc.task?.type !== 'produce' || !atTarget(npc, npc.task.target)) return;
      if (npc.task.output === 'components' && state.resources.timber >= 2 && state.resources.stone >= 1) { state.resources.timber -= 2; state.resources.stone -= 1; state.resources.components += 2; recordClaim(state, npc.id, 'components', 2, state.economy.prices.components, 'recipe:2_timber+1_stone'); }
      else if (npc.task.output === 'food' && state.economy.naturalStocks.foodPotential >= 4) { state.economy.naturalStocks.foodPotential -= 4; state.resources.food += 4; recordClaim(state, npc.id, 'food', 4, state.economy.prices.food, 'harvest:foodPotential'); }
      else if (npc.task.output === 'water' && state.economy.naturalStocks.waterTable >= 6) { state.economy.naturalStocks.waterTable -= 6; state.resources.water += 6; recordClaim(state, npc.id, 'water', 6, state.economy.prices.water, 'source:waterTable'); }
      else if (npc.task.output === 'researchEvidence') { state.resources.researchEvidence += 1; recordClaim(state, npc.id, 'researchEvidence', 1, state.economy.prices.researchEvidence, 'reproduction:measurement-workshop'); }
    }); updatePrices(state); addEvent(state, 'economy_cycle', 'Ledger', 'Production, consumption, prices, and verified claims reconciled.');
  }
  return state;
}

function advanceSimulation(input, ticks = 1) { let state = ensureSimulation(clone(input)); if (state.clock.paused) return state; for (let index = 0; index < Math.min(ticks, MAX_CATCHUP_TICKS); index += 1) state = tickSimulation(state); state.lastTickAt = Date.now(); return state; }
function catchUpSimulation(input, now = Date.now()) { const elapsed = Math.max(0, now - (input.lastTickAt || now)); return advanceSimulation(input, Math.floor(elapsed / TICK_MS)); }
function acceptWorkOrder(input) { const state = ensureSimulation(clone(input)); if (state.workOrder.status !== 'negotiated') return { state, ok: false, reason: 'All three NPC terms must be recorded first.' }; transition(state, 'accepted', 'sirix_1', 'explicit-owner-acceptance'); return { state, ok: true }; }
function playerAct(input, domain) { const state = ensureSimulation(clone(input)); const stage = STAGES[state.workOrder.stage]; if (!stage || state.workOrder.status !== 'supplied') return { state, ok: false, reason: 'The contract must be accepted and physically supplied first.' }; if (domain !== stage.domain) return { state, ok: false, reason: `${stage.label} currently requires ${stage.domain}.` }; const check = validateAction(state, state.player, stage.action, stage.target); if (!check.ok) return { state, ok: false, reason: check.reason }; const competence = state.player.competencies[domain] || 0; const contribution = 1 + competence * 2; state.workOrder.progress += contribution; state.workOrder.contributions.sirix_1 = (state.workOrder.contributions.sirix_1 || 0) + contribution; state.player.competencies[domain] = clamp(competence + 0.003, 0, 1); addEvent(state, 'player_work', 'sirix_1', `${stage.label}: timed participation recorded for later verification.`); return { state, ok: true };
}
function setProductionPriority(input, priority) { const state = ensureSimulation(clone(input)); if (!['food', 'water'].includes(priority)) return state; state.economy.productionPriority = priority; addEvent(state, 'contract_priority', 'Treasury', `Public production priority negotiated: ${priority}.`); return state; }

module.exports = { TICK_MS, MAX_CATCHUP_TICKS, ACTIONS, STAGES, initialSimulation, tickSimulation, advanceSimulation, catchUpSimulation, acceptWorkOrder, playerAct, setProductionPriority, validateAction };
