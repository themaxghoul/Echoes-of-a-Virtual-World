import { useEffect, useState } from 'react';
import { GitBranch } from 'lucide-react';
import { readLedger } from '@/lib/causalLedger';

export default function CausalLedgerPanel() {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    const refresh = () => readLedger().then((value) => setEvents(Array.isArray(value) ? value.slice(-8).reverse() : []));
    refresh();
    window.addEventListener('eov:ledger-updated', refresh);
    return () => window.removeEventListener('eov:ledger-updated', refresh);
  }, []);
  return (
    <section className="causal-ledger-panel">
      <h3><GitBranch size={15} /> CAUSAL LEDGER</h3>
      {events.length === 0 && <p>No consequential actions recorded.</p>}
      {events.map((event) => <article key={event.eventId}><strong>{event.state}</strong><span>{event.intent}</span><small>#{event.sequence} Â· {event.actorId}</small></article>)}
    </section>
  );
}
