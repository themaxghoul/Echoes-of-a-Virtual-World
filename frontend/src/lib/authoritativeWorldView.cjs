function words(value) {
  return String(value || 'unknown').replaceAll('_', ' ');
}

function missingText(order) {
  const blocker = [...(order.blockers || [])].reverse().find((item) => item.status === 'unresolved');
  if (!blocker) return null;
  if (Array.isArray(blocker.missing)) return blocker.missing.map(words).join(', ');
  return Object.entries(blocker.missing || {}).map(([resource, amount]) => `${amount} ${words(resource)}`).join(', ');
}

function projectAuthoritativeWork(state = {}) {
  const npcs = state.npcs || {};
  const contracts = new Map((state.economy?.work_contracts || []).map((contract) => [contract.id, contract]));
  const stewardship = [...(state.environment?.stewardship_orders || [])].reverse().slice(0, 4).map((order) => ({
    id: order.id,
    title: `${words(order.kind)} at ${words(order.site_id)}`,
    status: words(order.status),
    worker: order.worker,
    inspector: order.inspector,
    workerLocation: npcs[order.worker]?.location || null,
    inspectorLocation: npcs[order.inspector]?.location || null,
    missing: missingText(order),
    cause: `Local stock fell to ${order.cause_stock} unit${order.cause_stock === 1 ? '' : 's'}.`,
    outcome: order.restored_amount != null ? `${order.restored_amount} timber units survived restoration.` : null,
    contract: contracts.has(order.contract_id) ? {
      id: order.contract_id,
      status: words(contracts.get(order.contract_id).status),
      agreed: contracts.get(order.contract_id).agreed || null,
      scarcity: contracts.get(order.contract_id).valuation_basis?.regional_timber_scarcity,
      multiplier: contracts.get(order.contract_id).valuation_basis?.multiplier,
      spendable: Boolean(contracts.get(order.contract_id).spendable),
    } : null,
    next: order.status === 'blocked_inputs' ? 'Supply the missing inputs.'
      : order.status === 'traveling' ? 'Worker and inspector are traveling to the physical site.'
      : order.status === 'recovering' ? `Ecological inspection is due at tick ${order.recovery_due_tick}.`
      : order.status === 'returning' ? 'The work closes after both residents return home.'
      : order.status === 'completed' ? 'The verified stock and valuation now affect later decisions.'
      : 'The obligation is awaiting assignment and supply.',
  }));
  const teaching = [...(state.education?.teaching_orders || [])].reverse().slice(0, 4).map((order) => ({
    id: order.id,
    title: `${words(order.domain)}: ${order.instructor} → ${order.learner}`,
    status: words(order.status),
    source: order.source_order_id,
    dueTick: order.demonstration_due_tick,
    before: order.demonstration?.before,
    after: order.demonstration?.after,
    learning: order.learning || null,
    consent: order.consent || null,
    next: order.status === 'proposed' ? 'Both participants must consent before instruction.'
      : order.status === 'awaiting_learner_consent' ? 'The learner may accept or refuse the instruction.'
      : order.status === 'instruction' ? `Demonstration is due at tick ${order.demonstration_due_tick}.`
      : order.status === 'paused_needs' ? 'A survival need must recover before instruction resumes.'
      : order.status === 'completed' ? 'Instruction is recorded; demonstrated competence still requires verified real work.'
      : 'The teaching record remains persistent.',
  }));
  const practices = [...(state.education?.practice_orders || [])].reverse().slice(0, 4).map((order) => ({
    id: order.id, domain: words(order.domain), status: words(order.status), learner: order.learner,
    supervisor: order.supervisor, workOrderId: order.work_order_id || order.verified_work_order_id || null,
    demonstrated: order.demonstrated,
  }));
  const records = state.shared_actions?.records || {};
  const maintenance = [...(state.institutions?.governance?.maintenance_orders || [])].reverse().slice(0, 4).map((order) => {
    const action = records[order.canonical_action_id] || null;
    const site = state.resource_sites?.[order.site_id];
    return {
      id: order.id, title: `pump maintenance at ${site?.name || words(order.site_id)}`,
      status: words(order.status), actionState: action ? words(action.state) : 'awaiting canonical action',
      performer: action?.actor_id || order.assigned_to, verifier: action?.verifier_id || order.verified_by,
      location: site?.location || null, missing: missingText(order), commitment: action ? state.shared_actions?.actor_commitments?.[action.actor_id] || null : null,
      conditionBefore: action?.output?.condition_before ?? order.condition,
      conditionAfter: action?.output?.condition_after ?? site?.installed_pump?.condition,
      evidenceActionId: action?.id || null,
      next: !action ? 'A perceived maintenance need must create canonical work.'
        : action.state === 'accepted' ? 'The committed performer must reach the pump and reserve finite inputs and tools.'
        : action.state === 'reserved' ? 'Measured repair work can begin.'
        : action.state === 'submitted' ? 'A distinct competent observer must inspect the pump at this site.'
        : action.state === 'verified' ? 'The independent verifier may commission the measured result.'
        : action.state === 'commissioned' ? 'The verified condition now affects water production.'
        : `The causal action remains ${words(action.state)}.`,
    };
  });
  const commitments = Object.entries(state.shared_actions?.actor_commitments || {}).map(([actorId, item]) => ({ actorId, ...item }));
  const extraction = Object.values(records).filter((record) => record.definition?.action_type === 'extract_site_resource').slice(-6).reverse().map((record) => ({
    id: record.id, state: words(record.state), actorId: record.actor_id, verifierId: record.verifier_id,
    siteId: record.target_id, siteName: state.resource_sites?.[record.target_id]?.name || words(record.target_id),
    location: state.resource_sites?.[record.target_id]?.location || null,
    resource: words(record.definition?.output_item), amount: record.definition?.output_amount,
    stockBefore: record.output?.stock_before, stockAfter: record.output?.stock_after,
    observedYield: record.output?.observed_yield, conserved: record.output?.conserved,
    custody: record.definition?.output_custody, commitment: state.shared_actions?.actor_commitments?.[record.actor_id] || null,
  }));
  const capabilities = Object.values(npcs).flatMap((npc) => Object.entries(npc.competency_records || {})
    .filter(([domain]) => ['environmental_stewardship', 'ecological_inspection'].includes(domain))
    .map(([domain, record]) => ({ npcId: npc.id, name: npc.name, domain: words(domain), level: Number(record.demonstrated || 0) }))
  ).sort((a, b) => b.level - a.level || a.npcId.localeCompare(b.npcId));
  return { stewardship, teaching, practices, capabilities, maintenance, commitments, extraction };
}

module.exports = { projectAuthoritativeWork };
