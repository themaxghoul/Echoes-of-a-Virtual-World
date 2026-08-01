import { useEffect, useMemo, useState } from 'react';
import { Bot, Brain, Pin, Send, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { readDurable, writeDurable } from '@/lib/desktopStorage';

const MEMORY_KEY = 'eov-jarvis-owner-memory-alpha';

const importanceFor = (text) => {
  const normalized = text.toLowerCase();
  const signals = ['remember', 'important', 'decision', 'always', 'never', 'owner', 'cu', 'work order'];
  return Math.min(100, 35 + signals.filter((signal) => normalized.includes(signal)).length * 13 + Math.min(26, text.length / 8));
};

export default function JarvisPanel({ activity }) {
  const [messages, setMessages] = useState([{ id: 'hello', role: 'jarvis', text: 'Owner workspace online. I can follow settlement context while tasks are active.' }]);
  const [memories, setMemories] = useState([]);
  const [draft, setDraft] = useState('');
  const [view, setView] = useState('chat');
  const relevantMemories = useMemo(() => [...memories].sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.importance - a.importance), [memories]);

  useEffect(() => {
    readDurable('jarvis', MEMORY_KEY, []).then((value) => setMemories(Array.isArray(value) ? value : []));
  }, []);

  const persist = (next) => {
    setMemories(next);
    writeDurable('jarvis', MEMORY_KEY, next);
  };

  const send = (event) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    const importance = Math.round(importanceFor(text));
    setMessages((current) => [...current,
      { id: crypto.randomUUID(), role: 'owner', text },
      { id: crypto.randomUUID(), role: 'jarvis', text: `Context received. I scored its current subjective importance at ${importance}/100. Live model responses connect after owner-authenticated server integration.` },
    ]);
    persist([...memories, { id: crypto.randomUUID(), text, importance, pinned: false, createdAt: Date.now() }]);
    setDraft('');
  };

  return (
    <section className="jarvis-panel" aria-label="Private Jarvis owner workspace">
      <div className="jarvis-title"><span><Bot size={17} /> JARVIS</span><Badge variant="outline">OWNER ONLY</Badge></div>
      <div className="jarvis-activity"><i /> {activity}</div>
      <div className="jarvis-tabs">
        <button className={view === 'chat' ? 'active' : ''} onClick={() => setView('chat')}>Live chat</button>
        <button className={view === 'memory' ? 'active' : ''} onClick={() => setView('memory')}><Brain size={13} /> Memory ({memories.length})</button>
      </div>
      {view === 'chat' ? (
        <>
          <div className="jarvis-messages">{messages.map((message) => <p key={message.id} className={message.role}><strong>{message.role === 'owner' ? 'YOU' : 'JARVIS'}</strong>{message.text}</p>)}</div>
          <form onSubmit={send} className="jarvis-input"><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Chat while Jarvis works..." aria-label="Message Jarvis" /><Button size="icon" type="submit" aria-label="Send"><Send size={15} /></Button></form>
        </>
      ) : (
        <div className="jarvis-memory">
          {relevantMemories.length === 0 && <p>No owner memories captured yet.</p>}
          {relevantMemories.map((memory) => (
            <article key={memory.id}>
              <span>{memory.text}</span><small>importance {memory.importance}/100</small>
              <button aria-label="Pin memory" onClick={() => persist(memories.map((item) => item.id === memory.id ? { ...item, pinned: !item.pinned } : item))}><Pin size={13} fill={memory.pinned ? 'currentColor' : 'none'} /></button>
              <button aria-label="Forget memory" onClick={() => persist(memories.filter((item) => item.id !== memory.id))}><Trash2 size={13} /></button>
            </article>
          ))}
        </div>
      )}
      <p className="jarvis-security">Desktop memory uses recoverable local revisions. Production still requires server-enforced owner authorization, encryption, and an audit trail.</p>
    </section>
  );
}
