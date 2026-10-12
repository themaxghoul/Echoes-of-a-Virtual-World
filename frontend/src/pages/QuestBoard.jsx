import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Coins, Clock, Scroll, FlaskConical,
  Compass, Swords, X, ChevronRight, Star, Flag, CheckCircle, Heart, Hammer
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// ============ QUEST CATEGORIES ============
const QUEST_CATEGORIES = {
  story: { name: "Story", icon: Scroll, color: "#9b59b6" },
  faction: { name: "Faction", icon: Flag, color: "#e74c3c" },
  daily: { name: "Daily", icon: Clock, color: "#3498db" },
  exploration: { name: "Exploration", icon: Compass, color: "#2ecc71" },
  combat: { name: "Combat", icon: Swords, color: "#e67e22" },
  crafting: { name: "Crafting", icon: Hammer, color: "#f39c12" },
  social: { name: "Social", icon: Heart, color: "#e91e63" }
};

const QuestBoard = () => {
  const navigate = useNavigate();
  const [quests, setQuests] = useState({ available: [], active: [] });
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState(null);
  const [filter, setFilter] = useState('all');

  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const questsRes = await fetch(`${API}/api/quests/available/${userId}`);
      if (questsRes.ok) {
        const d = await questsRes.json();
        setQuests({ available: d.available_quests || [], active: d.active_quests || [] });
      }
    } catch (err) { console.error('Failed to fetch:', err); }
    finally { setLoading(false); }
  };

  const acceptQuest = async (templateId) => {
    try { await fetch(`${API}/api/quests/accept`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: userId, quest_template: templateId }) }); }
    catch (err) {}
    toast.success('Quest accepted!'); setSelectedItem(null); fetchData();
  };

  const filteredQuests = quests.available.filter(q => filter === 'all' || q.category === filter);

  return (
    <div className="min-h-screen bg-[#1a1510] text-amber-50">
      <div className="fixed inset-0 pointer-events-none opacity-20" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.02' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`, backgroundColor: '#0d2818' }} />
      <div className="fixed inset-0 pointer-events-none" style={{ background: 'linear-gradient(180deg, #0d2818 0%, #1a3d2b 30%, #0d2818 100%)' }} />

      <header className="relative z-10 border-b-4 border-amber-900/50 bg-gradient-to-b from-amber-950/80 to-transparent">
        <div className="max-w-7xl mx-auto px-4 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/select-mode')} className="p-2 hover:bg-amber-900/30 rounded-lg" data-testid="quest-back-btn"><ArrowLeft className="w-6 h-6 text-amber-400" /></button>
            <div>
              <h1 className="text-3xl font-bold text-amber-200 tracking-wide" style={{ fontFamily: 'serif' }}>QUEST BOARD</h1>
              <p className="text-amber-600 text-sm">Contracts, missions, and adventures</p>
            </div>
          </div>
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-700 to-purple-900 flex items-center justify-center shadow-lg border-2 border-purple-950">
            <Scroll className="w-8 h-8 text-purple-300" />
          </div>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6 p-4 rounded-lg bg-amber-900/20 border border-amber-800/30">
          <p className="text-purple-400 text-sm flex items-center gap-2"><Scroll className="w-4 h-4" /><span><strong>Standard Quests</strong> can be completed at your pace. Some delegable to AI Partners.</span></p>
        </div>

        <div className="flex flex-wrap gap-2 mb-8">
          <FilterPlaque active={filter === 'all'} onClick={() => setFilter('all')} label="All" />
          {Object.entries(QUEST_CATEGORIES).map(([k, c]) => <FilterPlaque key={k} active={filter === k} onClick={() => setFilter(k)} label={c.name} icon={c.icon} color={c.color} />)}
        </div>

        {loading ? (
          <div className="text-center py-20"><Scroll className="w-12 h-12 mx-auto mb-4 text-amber-600 animate-pulse" /><p className="text-amber-600">Checking the board...</p></div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="quest-grid">
            {filteredQuests.map((q, i) => <QuestPaper key={q.template_id} quest={q} onClick={() => setSelectedItem({ type: 'quest', data: q })} rotation={((i % 5) - 2) * 1.5} />)}
          </div>
        )}

        {!loading && !filteredQuests.length && (
          <div className="text-center py-20">
            <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-amber-900/30 flex items-center justify-center"><Scroll className="w-12 h-12 text-amber-700" /></div>
            <p className="text-amber-600 text-lg">No quests available</p>
          </div>
        )}

        {quests.active.length > 0 && (
          <div className="mt-12">
            <h2 className="text-xl font-bold text-amber-300 mb-4 flex items-center gap-2"><CheckCircle className="w-5 h-5" />Active Quests ({quests.active.length})</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {quests.active.map(q => <QuestPaper key={q.quest_id} quest={q} isActive onClick={() => setSelectedItem({ type: 'quest', data: q, isActive: true })} rotation={0} />)}
            </div>
          </div>
        )}
      </main>

      {selectedItem && (
        <QuestModal quest={selectedItem.data} isActive={selectedItem.isActive} onClose={() => setSelectedItem(null)} onAccept={() => acceptQuest(selectedItem.data.template_id)} />
      )}
    </div>
  );
};

const FilterPlaque = ({ active, onClick, label, icon: Icon, color }) => (
  <button onClick={onClick} className={`px-4 py-2 rounded transition-all ${active ? 'bg-amber-800/80 text-amber-100 shadow-lg scale-105' : 'bg-amber-950/50 text-amber-500 hover:bg-amber-900/50'}`} style={{ borderBottom: active ? `3px solid ${color || '#d4a574'}` : '3px solid transparent' }}>
    <div className="flex items-center gap-2">{Icon && <Icon className="w-4 h-4" style={{ color }} />}<span className="text-sm font-medium">{label}</span></div>
  </button>
);

const tornEdge = `polygon(2% 0%, 5% 2%, 10% 0%, 15% 1%, 20% 0%, 25% 2%, 30% 0%, 35% 1%, 40% 0%, 45% 2%, 50% 0%, 55% 1%, 60% 0%, 65% 2%, 70% 0%, 75% 1%, 80% 0%, 85% 2%, 90% 0%, 95% 1%, 98% 0%, 100% 2%, 100% 5%, 98% 10%, 100% 15%, 99% 20%, 100% 25%, 98% 30%, 100% 35%, 99% 40%, 100% 45%, 98% 50%, 100% 55%, 99% 60%, 100% 65%, 98% 70%, 100% 75%, 99% 80%, 100% 85%, 98% 90%, 100% 95%, 99% 98%, 100% 100%, 98% 100%, 95% 98%, 90% 100%, 85% 99%, 80% 100%, 75% 98%, 70% 100%, 65% 99%, 60% 100%, 55% 98%, 50% 100%, 45% 99%, 40% 100%, 35% 98%, 30% 100%, 25% 99%, 20% 100%, 15% 98%, 10% 100%, 5% 99%, 2% 100%, 0% 98%, 0% 95%, 2% 90%, 0% 85%, 1% 80%, 0% 75%, 2% 70%, 0% 65%, 1% 60%, 0% 55%, 2% 50%, 0% 45%, 1% 40%, 0% 35%, 2% 30%, 0% 25%, 1% 20%, 0% 15%, 2% 10%, 0% 5%, 1% 2%)`;

const QuestPaper = ({ quest, onClick, rotation, isActive }) => {
  const cat = QUEST_CATEGORIES[quest.category] || QUEST_CATEGORIES.story;
  const Icon = cat.icon;
  const done = isActive && quest.objectives?.every(o => o.completed);
  return (
    <div onClick={onClick} className="cursor-pointer group" style={{ transform: `rotate(${rotation}deg)` }}>
      <div className={`relative bg-gradient-to-br from-amber-100 via-amber-50 to-amber-100 p-1 transition-all duration-300 group-hover:scale-105 group-hover:shadow-2xl ${done ? 'ring-2 ring-green-500' : ''}`} style={{ clipPath: tornEdge, boxShadow: '4px 4px 8px rgba(0,0,0,0.4)' }}>
        <div className="bg-gradient-to-br from-[#f4e4bc] via-[#e8d5a3] to-[#dcc68f] p-5 min-h-[240px]">
          <div className="absolute -top-2 -right-2 w-12 h-12 rounded-full flex items-center justify-center shadow-lg z-10" style={{ background: `radial-gradient(circle at 30% 30%, ${cat.color}dd, ${cat.color}88)` }}><Icon className="w-6 h-6 text-white/90" /></div>
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-gradient-to-br from-zinc-400 to-zinc-600 shadow-md border border-zinc-700" />
          <div className="text-amber-950">
            <div className="border-b-2 border-amber-800/30 pb-3 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded" style={{ backgroundColor: `${cat.color}20`, color: cat.color }}>{cat.name}</span>
              {done && <span className="ml-2 text-xs bg-green-500/20 text-green-700 px-2 py-0.5 rounded">Ready!</span>}
              <h3 className="text-lg font-bold leading-tight mt-1" style={{ fontFamily: 'serif' }}>{quest.name}</h3>
            </div>
            <p className="text-sm text-amber-900/80 mb-4 line-clamp-2" style={{ fontFamily: 'serif' }}>{quest.description}</p>
            {isActive && quest.objectives && <div className="space-y-1 mb-3">{quest.objectives.slice(0, 2).map((o, i) => <div key={i} className="flex items-center gap-2 text-xs"><div className={`w-3 h-3 rounded border ${o.completed ? 'bg-green-500 border-green-500' : 'border-amber-700'}`} /><span className={o.completed ? 'line-through text-amber-600' : ''}>{o.type}: {o.current || 0}/{o.count}</span></div>)}</div>}
            {quest.time_limit_hours && <div className="flex items-center gap-1 text-xs text-amber-700 mb-2"><Clock className="w-3 h-3" />Max {quest.time_limit_hours}h</div>}
            <div className="mt-4 pt-3 border-t-2 border-amber-800/30 flex items-center gap-3 text-xs">
              {quest.rewards?.gold > 0 && <span className="flex items-center gap-1 text-amber-700 font-bold"><Coins className="w-3 h-3" />{quest.rewards.gold}</span>}
              {quest.rewards?.exp > 0 && <span className="flex items-center gap-1 text-blue-700 font-bold"><Star className="w-3 h-3" />{quest.rewards.exp} XP</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const QuestModal = ({ quest, isActive, onClose, onAccept }) => {
  const cat = QUEST_CATEGORIES[quest.category] || QUEST_CATEGORIES.story;
  const Icon = cat.icon;
  const done = isActive && quest.objectives?.every(o => o.completed);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div className="relative max-w-2xl w-full animate-unfurl" onClick={e => e.stopPropagation()}>
        <div className="bg-gradient-to-br from-[#f4e4bc] via-[#e8d5a3] to-[#dcc68f] rounded-lg overflow-hidden" style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.5)', border: '4px solid #8b5a2b' }}>
          <div className="h-4 bg-gradient-to-r from-purple-800 via-purple-700 to-purple-800" />
          <div className="relative p-6 pb-4 border-b-2 border-amber-800/30">
            <div className="absolute -top-6 right-6 w-20 h-20 rounded-full flex items-center justify-center shadow-xl" style={{ background: `radial-gradient(circle at 30% 30%, ${cat.color}, ${cat.color}aa)` }}><Icon className="w-10 h-10 text-white/90" /></div>
            <button onClick={onClose} className="absolute top-4 left-4 p-2 hover:bg-amber-800/20 rounded-full"><X className="w-5 h-5 text-amber-800" /></button>
            <div className="text-center mt-4">
              <span className="text-sm font-bold uppercase tracking-widest px-3 py-1 rounded-full" style={{ backgroundColor: `${cat.color}20`, color: cat.color }}>{cat.name}</span>
              <h2 className="text-3xl font-bold text-amber-950 mt-3" style={{ fontFamily: 'serif' }}>{quest.name}</h2>
            </div>
          </div>
          <div className="p-6 text-amber-950">
            <p className="text-lg leading-relaxed mb-6" style={{ fontFamily: 'serif' }}>{quest.description}</p>
            {quest.objectives && <div className="mb-6"><h3 className="text-sm font-bold uppercase tracking-wider text-amber-800 mb-3">Objectives</h3><div className="space-y-2">{quest.objectives.map((o, i) => <div key={i} className={`flex items-center gap-3 p-3 rounded-lg ${o.completed ? 'bg-green-500/10 border border-green-500/30' : 'bg-amber-900/10'}`}><div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${o.completed ? 'bg-green-500 border-green-500' : 'border-amber-600'}`}>{o.completed && <CheckCircle className="w-4 h-4 text-white" />}</div><div className="flex-1"><div className="text-sm capitalize">{o.type?.replace('_', ' ')}: {o.target}</div><div className="text-xs text-amber-600">{o.current || 0}/{o.count}</div></div></div>)}</div></div>}
            <div className="bg-gradient-to-r from-purple-800/20 via-purple-700/20 to-purple-800/20 rounded-lg p-5 mb-6">
              <h3 className="text-center text-sm font-bold uppercase tracking-widest text-amber-800 mb-4">═══ Rewards ═══</h3>
              <div className="flex items-center justify-center gap-8">
                {quest.rewards?.gold > 0 && <div className="text-center"><Coins className="w-8 h-8 mx-auto mb-2 text-amber-600" /><p className="text-2xl font-bold text-amber-700">{quest.rewards.gold}</p><p className="text-xs text-amber-600 uppercase">Gold</p></div>}
                {quest.rewards?.exp > 0 && <div className="text-center"><Star className="w-8 h-8 mx-auto mb-2 text-blue-600" /><p className="text-2xl font-bold text-blue-700">{quest.rewards.exp}</p><p className="text-xs text-blue-600 uppercase">XP</p></div>}
              </div>
            </div>
            {!isActive ? <button onClick={onAccept} className="w-full py-4 bg-gradient-to-r from-purple-700 via-purple-600 to-purple-700 text-white font-bold text-lg rounded-lg shadow-lg flex items-center justify-center gap-3" data-testid="accept-quest-btn">Accept Quest <ChevronRight className="w-5 h-5" /></button>
            : done ? <button className="w-full py-4 bg-gradient-to-r from-green-700 via-green-600 to-green-700 text-white font-bold text-lg rounded-lg shadow-lg flex items-center justify-center gap-3"><CheckCircle className="w-5 h-5" />Complete Quest</button>
            : <div className="w-full py-4 bg-amber-800/50 text-amber-200 font-bold text-lg rounded-lg text-center">In Progress...</div>}
          </div>
          <div className="h-4 bg-gradient-to-r from-purple-800 via-purple-700 to-purple-800" />
        </div>
      </div>
      <style>{`@keyframes unfurl{from{opacity:0;transform:scale(0.8) rotateX(10deg)}to{opacity:1;transform:scale(1) rotateX(0)}}.animate-unfurl{animation:unfurl 0.3s ease-out}`}</style>
    </div>
  );
};

export default QuestBoard;
