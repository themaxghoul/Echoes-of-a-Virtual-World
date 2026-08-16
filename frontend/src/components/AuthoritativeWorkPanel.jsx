import React from 'react';
import authoritativeWorldView from '@/lib/authoritativeWorldView.cjs';

const { projectAuthoritativeWork } = authoritativeWorldView;

function Tile({ value }) {
  return value ? <>{value[0]},{value[1]}</> : <>unknown</>;
}

export default function AuthoritativeWorkPanel({ state }) {
  const view = projectAuthoritativeWork(state);
  if (!view.stewardship.length && !view.teaching.length && !view.practices.length && !view.capabilities.length && !view.maintenance.length && !view.extraction.length) return null;
  return <section className="iso-authoritative-work" aria-label="Persistent work and learning consequences">
    <p className="iso-kicker">CONSEQUENCE-DRIVEN WORK</p>
    {view.maintenance.length > 0 && <div>
      <h3>Infrastructure maintenance</h3>
      {view.maintenance.map((order) => <article key={order.id} data-status={order.status}>
        <b>{order.title}</b><strong>{order.status} · {order.actionState}</strong>
        <span>Field site <Tile value={order.location} /> · performer {order.performer || 'unassigned'}{order.verifier ? ` · verifier ${order.verifier}` : ''}</span>
        {order.commitment && <small>{order.performer} is committed to {order.commitment.action_id} as {order.commitment.role}.</small>}
        {order.missing && <em>Blocked: missing {order.missing}</em>}
        {order.conditionBefore != null && <span>Measured condition {Number(order.conditionBefore).toFixed(2)}{order.conditionAfter != null ? ` → ${Number(order.conditionAfter).toFixed(2)}` : ''}</span>}
        {order.evidenceActionId && <small>Causal action: {order.evidenceActionId}</small>}
        <small>Next consequence: {order.next}</small>
      </article>)}
    </div>}
    {view.extraction.length > 0 && <div>
      <h3>Finite extraction</h3>
      {view.extraction.map((item) => <article key={item.id} data-status={item.state}>
        <b>{item.resource} at {item.siteName}</b><strong>{item.state}</strong>
        <span>{item.actorId} · field tile <Tile value={item.location} />{item.verifierId ? ` · verified by ${item.verifierId}` : ''}</span>
        {item.stockBefore != null && <span>Site stock {item.stockBefore} → {item.stockAfter} · observed yield {item.observedYield} · conserved {item.conserved ? 'yes' : 'no'}</span>}
        <small>Output custody: {String(item.custody || 'unknown').replaceAll('_', ' ')}{item.custody === 'actor_inventory' ? ' · transport is still required before communal use' : ''}</small>
      </article>)}
    </div>}
    {view.stewardship.length > 0 && <div>
      <h3>Environmental stewardship</h3>
      {view.stewardship.map((order) => <article key={order.id} data-status={order.status}>
        <b>{order.title}</b><strong>{order.status}</strong>
        <span>{order.cause}</span>
        <small>{order.worker} at <Tile value={order.workerLocation} /> · inspected by {order.inspector} at <Tile value={order.inspectorLocation} /></small>
        {order.missing && <em>Blocked: missing {order.missing}</em>}
        {order.outcome && <span>{order.outcome}</span>}
        {order.contract && <span>Provisional contract {order.contract.id} · {order.contract.status} · {Object.entries(order.contract.agreed || {}).map(([actor, amount]) => `${actor} ${Number(amount).toFixed(2)} CU`).join(' · ')}{order.contract.multiplier ? ` · scarcity/urgency ×${Number(order.contract.multiplier).toFixed(2)}` : ''} · non-spendable</span>}
        <small>Next consequence: {order.next}</small>
      </article>)}
    </div>}
    {view.teaching.length > 0 && <div>
      <h3>Teaching and capability</h3>
      {view.teaching.map((order) => <article key={order.id} data-status={order.status}>
        <b>{order.title}</b><strong>{order.status}</strong>
        <span>Evidence source: {order.source}</span>
        {order.learning && <span>Instruction gained theory {Number(order.learning.theory || 0).toFixed(2)}, observation {Number(order.learning.observation || 0).toFixed(2)}, and procedure {Number(order.learning.procedure || 0).toFixed(2)}. Demonstrated competence remains {Number(order.learning.demonstrated_after || 0).toFixed(2)}.</span>}
        {order.after != null && <span>Demonstrated competency: {Number(order.before || 0).toFixed(2)} → {Number(order.after).toFixed(2)}</span>}
        <small>Next consequence: {order.next}</small>
      </article>)}
      {view.practices.map((order) => <article key={order.id} data-status={order.status}>
        <b>Supervised practice · {order.domain}</b><strong>{order.status}</strong>
        <span>{order.learner} supervised by {order.supervisor}{order.workOrderId ? ` through ${order.workOrderId}` : ''}</span>
        {order.demonstrated != null && <small>Verified demonstrated competence: {Number(order.demonstrated).toFixed(2)}</small>}
      </article>)}
      {view.capabilities.length > 0 && <div className="iso-capability-list" aria-label="Demonstrated resident capabilities">
        {view.capabilities.map((item) => <small key={`${item.npcId}-${item.domain}`}><b>{item.name}</b> · {item.domain} {Number(item.level).toFixed(2)}</small>)}
      </div>}
    </div>}
  </section>;
}
