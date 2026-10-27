import { readDurable, writeDurable } from '@/lib/desktopStorage';

const FALLBACK_KEY = 'eov-causal-ledger-alpha';

export async function readLedger() {
  return readDurable('ledger', FALLBACK_KEY, []);
}

export async function appendCausalEvent(event) {
  const current = await readLedger();
  const previous = current[current.length - 1];
  const record = {
    eventId: crypto.randomUUID(),
    sequence: current.length + 1,
    recordedAt: new Date().toISOString(),
    previousEventId: previous?.eventId || null,
    ...event,
  };
  const next = [...current, record].slice(-500);
  await writeDurable('ledger', FALLBACK_KEY, next);
  window.dispatchEvent(new CustomEvent('eov:ledger-updated', { detail: record }));
  return record;
}
