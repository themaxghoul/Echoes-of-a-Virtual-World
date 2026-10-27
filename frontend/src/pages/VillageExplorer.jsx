import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { GameNavigation } from '@/components/GameNavigation';
import { fetchWorldHealth, fetchWorldSnapshot, submitWorldAction, worldServerConfigured } from '@/lib/worldServer';

const { nearbyResidents, speechAction, mergeMessages } = require('@/lib/worldConversation.cjs');

export default function VillageExplorer() {
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState(null);
  const [health, setHealth] = useState(null);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [recipientId, setRecipientId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sendError, setSendError] = useState('');
  const endRef = useRef(null);
  const receive = (next) => {
    setSnapshot(current => !current || next.revision >= current.revision ? next : current);
    setMessages(current => mergeMessages(current, next.state?.communications?.messages || []));
  };
  useEffect(() => {
    const userId = localStorage.getItem('userId');
    if (userId) localStorage.setItem(`eovLastRoute:${userId}`, '/village');
    if (!worldServerConfigured) {
      setError('Set the persistent world address in Settings, then sign in to that server.');
      return undefined;
    }
    const controller = new AbortController();
    let active = true;
    let inFlight = false;
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        let next = await fetchWorldSnapshot(undefined, controller.signal);
        if (next.viewer_id && !next.state?.players?.[next.viewer_id]) {
          await submitWorldAction({ type: 'join' }, next.revision);
          next = await fetchWorldSnapshot(undefined, controller.signal);
        }
        if (!active) return;
        receive(next);
        setError('');
        // Health failure must not suppress a valid conversation snapshot.
        try {
          const status = await fetchWorldHealth(controller.signal);
          if (active) setHealth(status);
        } catch { /* Retry on the next poll. */ }
      } catch (failure) {
        if (active && failure.name !== 'AbortError') setError(failure.message);
      } finally { inFlight = false; }
    };
    refresh();
    const timer = window.setInterval(refresh, 1000);
    return () => { active = false; controller.abort(); window.clearInterval(timer); };
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }); }, [messages]);
  const residents = nearbyResidents(snapshot);
  const actor = snapshot?.state?.players?.[snapshot.viewer_id];
  const connected = Boolean(snapshot && !error);
  const effectiveRecipient = residents.some(r => r.id === recipientId) ? recipientId : '';
  const speak = async (event) => {
    event.preventDefault();
    if (busy || !message.trim() || !connected) return;
    setBusy(true);
    try {
      const response = await submitWorldAction(speechAction(snapshot, message, effectiveRecipient), snapshot.revision);
      if (!response.result?.accepted) throw new Error(response.result?.reason || 'Message not accepted.');
      setMessages(current => mergeMessages(current, response.result.replies || []));
      setMessage('');
      setSendError('');
      receive(await fetchWorldSnapshot());
    } catch (failure) { setSendError(failure.message); }
    finally { setBusy(false); }
  };
  return <div className="h-screen flex flex-col bg-obsidian text-foreground">
    <GameNavigation title="Settlement conversation" />
    <header className="px-6 py-3 border-b border-border flex flex-wrap items-center gap-4">
      <strong>{snapshot?.state?.name || 'Connecting to your world'}</strong>
      <span role="status" aria-label="Persistent world status" className="text-sm text-muted-foreground">
        {connected ? `Connected · Tick ${snapshot.tick}` : 'Disconnected'}
        {health && ` · ${health.tick_seconds}s per tick · uptime ${Math.floor(health.uptime_seconds / 60)}m`}
      </span>
      <Button variant="outline" onClick={() => navigate('/play')}>Explore isometric world</Button>
    </header>
    {error && <div role="alert" className="px-6 py-3 text-amber-200 bg-amber-900/20">{error} <button className="underline" onClick={() => navigate('/settings')}>Connection settings</button></div>}
    <main className="flex-1 min-h-0 overflow-y-auto px-6 py-4" aria-label="Settlement conversation history" aria-live="polite">
      {!messages.length && <p className="text-muted-foreground">Move near a resident in the isometric world, then say hello. Both perspectives share your position.</p>}
      {messages.map(item => <article key={item.id} className="max-w-3xl mx-auto border-b border-border/40 py-4">
        <strong className="text-gold">{item.speaker}</strong>
        <p className="whitespace-pre-wrap mt-1">{item.content}</p>
        <small className="text-muted-foreground">Tick {item.tick}</small>
      </article>)}
      <div ref={endRef} />
    </main>
    <footer className="border-t border-border p-4 sm:px-6">
      <p className="text-sm text-muted-foreground mb-2">{actor?.location ? `At ${actor.location.join(', ')} · ` : ''}{residents.length} Samaritans within hearing</p>
      {sendError && <p role="alert" className="text-amber-200 mb-2">{sendError}</p>}
      <form onSubmit={speak} className="flex flex-wrap gap-2">
        <select aria-label="Speak to" className="bg-surface border border-border rounded-sm p-2" value={effectiveRecipient} onChange={event => setRecipientId(event.target.value)}>
          <option value="">Nearest resident{residents[0] ? ` · ${residents[0].name}` : ''}</option>
          {residents.map(resident => <option key={resident.id} value={resident.id}>{resident.name}</option>)}
        </select>
        <input aria-label="Story message" className="flex-1 min-w-40 bg-surface border border-border p-3 rounded-sm" value={message} onChange={event => setMessage(event.target.value)} maxLength={500} disabled={!connected || busy} placeholder="Say hello, ask about work, share an idea…" />
        <Button type="submit" disabled={!connected || busy || !message.trim()}>{busy ? 'Sending…' : 'Speak'}</Button>
      </form>
      <details className="mt-2 text-xs text-muted-foreground"><summary>About conversation</summary><p>Words can shape memories and decisions. Changes to land and materials still require physical work.</p></details>
    </footer>
  </div>;
}
