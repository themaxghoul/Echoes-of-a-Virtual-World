import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Scroll, Coins, Star, Clock, CheckCircle, Flag, Compass, Sword, Hammer, Heart, RefreshCw, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const QuestLog = () => {
  const navigate = useNavigate();
  const [availableQuests, setAvailableQuests] = useState([]);
  const [activeQuests, setActiveQuests] = useState([]);
  const [categories, setCategories] = useState({});
  const [factions, setFactions] = useState({});
  const [reputation, setReputation] = useState({});
  const [wallet, setWallet] = useState({ gold: 0 });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('available');
  const [selectedQuest, setSelectedQuest] = useState(null);
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [questsRes, categoriesRes, factionsRes, repRes, walletRes] = await Promise.all([
        fetch(`${API}/api/quests/available/${userId}`),
        fetch(`${API}/api/quests/categories`),
        fetch(`${API}/api/quests/factions`),
        fetch(`${API}/api/quests/reputation/${userId}`),
        fetch(`${API}/api/quests/wallet/${userId}`)
      ]);
      
      if (questsRes.ok) {
        const data = await questsRes.json();
        setAvailableQuests(data.available_quests || []);
        setActiveQuests(data.active_quests || []);
      }
      if (categoriesRes.ok) setCategories((await categoriesRes.json()).categories || {});
      if (factionsRes.ok) setFactions((await factionsRes.json()).factions || {});
      if (repRes.ok) setReputation((await repRes.json()).factions || {});
      if (walletRes.ok) setWallet(await walletRes.json());
    } catch (err) {
      console.error('Failed to fetch quest data:', err);
    } finally {
      setLoading(false);
    }
  };

  const acceptQuest = async (templateId) => {
    try {
      const res = await fetch(`${API}/api/quests/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, quest_template: templateId })
      });
      
      if (res.ok) {
        toast.success('Quest accepted! Check your active quests.');
        fetchData();
        setSelectedQuest(null);
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to accept quest');
      }
    } catch (err) {
      toast.error('Failed to accept quest');
    }
  };

  const completeQuest = async (questId) => {
    try {
      const res = await fetch(`${API}/api/quests/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, quest_id: questId })
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(`Quest complete! Earned ${data.rewards_claimed.gold} Gold + ${data.rewards_claimed.exp} XP`);
        fetchData();
        setSelectedQuest(null);
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Cannot complete quest yet');
      }
    } catch (err) {
      toast.error('Failed to complete quest');
    }
  };

  const categoryIcons = {
    story: Scroll,
    faction: Flag,
    daily: Clock,
    exploration: Compass,
    combat: Sword,
    crafting: Hammer,
    social: Heart
  };

  const getCategoryIcon = (category) => categoryIcons[category] || Scroll;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-[#0f0f15]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/select-mode')} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold">Quest Log</h1>
              <p className="text-sm text-zinc-400">Complete quests for Gold and reputation</p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-amber-500/20 px-4 py-2 rounded-lg">
            <Coins className="w-5 h-5 text-amber-400" />
            <span className="font-bold text-amber-400">{wallet.gold?.toFixed(0) || 0} Gold</span>
          </div>
        </div>
      </header>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
        </div>
      ) : (
        <main className="max-w-7xl mx-auto px-4 py-6">
          {/* Faction Reputation */}
          <div className="mb-8">
            <h2 className="text-lg font-bold mb-4">Faction Standing</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {Object.entries(reputation).map(([factionId, rep]) => {
                const faction = factions[factionId] || {};
                return (
                  <div 
                    key={factionId}
                    className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-3"
                  >
                    <div className="text-xs text-zinc-400 mb-1">{rep.faction_name}</div>
                    <div className={`text-sm font-medium capitalize ${
                      rep.tier === 'exalted' ? 'text-purple-400' :
                      rep.tier === 'revered' ? 'text-blue-400' :
                      rep.tier === 'honored' ? 'text-green-400' :
                      rep.tier === 'friendly' ? 'text-emerald-400' :
                      rep.tier === 'neutral' ? 'text-zinc-400' :
                      'text-red-400'
                    }`}>
                      {rep.tier}
                    </div>
                    <div className="text-xs text-zinc-500">{rep.reputation} rep</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-4">
            {[
              { id: 'available', label: 'Available', count: availableQuests.length },
              { id: 'active', label: 'Active', count: activeQuests.length }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === tab.id 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                {tab.label}
                <span className="px-2 py-0.5 bg-black/30 rounded-full text-xs">{tab.count}</span>
              </button>
            ))}
          </div>

          {/* Quest Categories */}
          {activeTab === 'available' && (
            <div className="mb-6">
              <div className="flex flex-wrap gap-2">
                {Object.entries(categories).map(([key, cat]) => {
                  const questCount = availableQuests.filter(q => q.category === key).length;
                  if (questCount === 0) return null;
                  
                  const IconComponent = categoryIcons[key] || Scroll;
                  return (
                    <div
                      key={key}
                      className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800/50 rounded-lg text-sm"
                      style={{ borderLeft: `3px solid ${cat.color}` }}
                    >
                      <IconComponent className="w-4 h-4" style={{ color: cat.color }} />
                      <span>{cat.name}</span>
                      <span className="text-zinc-500">({questCount})</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quest List */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(activeTab === 'available' ? availableQuests : activeQuests).map(quest => {
              const cat = categories[quest.category] || {};
              const IconComponent = getCategoryIcon(quest.category);
              const isActive = activeTab === 'active';
              const allComplete = isActive && quest.objectives?.every(obj => obj.completed);
              
              return (
                <div
                  key={quest.template_id || quest.quest_id}
                  className={`bg-zinc-900/50 border rounded-xl p-5 cursor-pointer transition-all hover:border-purple-500/50 ${
                    isActive && allComplete ? 'border-green-500/50' : 'border-zinc-800'
                  }`}
                  onClick={() => setSelectedQuest(quest)}
                  data-testid={`quest-${quest.template_id || quest.quest_id}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div 
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${cat.color}20` }}
                    >
                      <IconComponent className="w-5 h-5" style={{ color: cat.color }} />
                    </div>
                    {isActive && allComplete && (
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Ready
                      </span>
                    )}
                  </div>
                  
                  <h3 className="font-semibold mb-1">{quest.name}</h3>
                  <p className="text-sm text-zinc-400 mb-4 line-clamp-2">{quest.description}</p>
                  
                  {/* Objectives for active quests */}
                  {isActive && quest.objectives && (
                    <div className="space-y-1 mb-4">
                      {quest.objectives.map((obj, i) => (
                        <div key={obj.id || `obj-${obj.description?.slice(0,20) || i}`} className="flex items-center gap-2 text-xs">
                          <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                            obj.completed ? 'bg-green-500 border-green-500' : 'border-zinc-600'
                          }`}>
                            {obj.completed && <CheckCircle className="w-3 h-3" />}
                          </div>
                          <span className={obj.completed ? 'text-zinc-500 line-through' : 'text-zinc-300'}>
                            {obj.type}: {obj.current || 0}/{obj.count}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Rewards */}
                  <div className="flex items-center gap-3 text-xs">
                    {quest.rewards?.gold > 0 && (
                      <span className="flex items-center gap-1 text-amber-400">
                        <Coins className="w-3 h-3" />
                        {quest.rewards.gold}
                      </span>
                    )}
                    {quest.rewards?.exp > 0 && (
                      <span className="flex items-center gap-1 text-blue-400">
                        <Star className="w-3 h-3" />
                        {quest.rewards.exp} XP
                      </span>
                    )}
                    {quest.rep_reward?.faction && (
                      <span className="flex items-center gap-1 text-purple-400">
                        <Flag className="w-3 h-3" />
                        +{quest.rep_reward.amount}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
            
            {(activeTab === 'available' ? availableQuests : activeQuests).length === 0 && (
              <div className="col-span-full text-center py-12">
                <Scroll className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
                <p className="text-zinc-400">
                  {activeTab === 'available' 
                    ? 'No quests available. Check back later!' 
                    : 'No active quests. Accept some quests to get started!'}
                </p>
              </div>
            )}
          </div>
        </main>
      )}

      {/* Quest Detail Modal */}
      {selectedQuest && (
        <QuestDetailModal
          quest={selectedQuest}
          categories={categories}
          factions={factions}
          isActive={activeTab === 'active'}
          onClose={() => setSelectedQuest(null)}
          onAccept={() => acceptQuest(selectedQuest.template_id)}
          onComplete={() => completeQuest(selectedQuest.quest_id)}
        />
      )}
    </div>
  );
};

// Quest Detail Modal
const QuestDetailModal = ({ quest, categories, factions, isActive, onClose, onAccept, onComplete }) => {
  const cat = categories[quest.category] || {};
  const allComplete = isActive && quest.objectives?.every(obj => obj.completed);
  
  const categoryIcons = {
    story: Scroll,
    faction: Flag,
    daily: Clock,
    exploration: Compass,
    combat: Sword,
    crafting: Hammer,
    social: Heart
  };
  
  const IconComponent = categoryIcons[quest.category] || Scroll;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-start gap-4">
            <div 
              className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${cat.color}20` }}
            >
              <IconComponent className="w-7 h-7" style={{ color: cat.color }} />
            </div>
            <div className="flex-1">
              <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ backgroundColor: `${cat.color}20`, color: cat.color }}>
                {cat.name}
              </span>
              <h2 className="text-xl font-bold mt-1">{quest.name}</h2>
            </div>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          <div>
            <h3 className="font-semibold mb-2">Description</h3>
            <p className="text-zinc-300">{quest.description}</p>
          </div>
          
          {/* Objectives */}
          {quest.objectives && quest.objectives.length > 0 && (
            <div>
              <h3 className="font-semibold mb-3">Objectives</h3>
              <div className="space-y-2">
                {quest.objectives.map((obj, i) => (
                  <div 
                    key={obj.id || `detail-obj-${obj.description?.slice(0,20) || i}`}
                    className={`flex items-center gap-3 p-3 rounded-lg ${
                      obj.completed ? 'bg-green-500/10 border border-green-500/30' : 'bg-zinc-800/50'
                    }`}
                  >
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                      obj.completed ? 'bg-green-500 border-green-500' : 'border-zinc-600'
                    }`}>
                      {obj.completed && <CheckCircle className="w-4 h-4" />}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm capitalize">{obj.type.replace('_', ' ')}: {obj.target}</div>
                      <div className="text-xs text-zinc-400">
                        Progress: {obj.current || 0} / {obj.count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Rewards */}
          <div>
            <h3 className="font-semibold mb-3">Rewards</h3>
            <div className="grid grid-cols-3 gap-3">
              {quest.rewards?.gold > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-center">
                  <Coins className="w-6 h-6 mx-auto mb-1 text-amber-400" />
                  <div className="font-bold text-amber-400">{quest.rewards.gold}</div>
                  <div className="text-xs text-zinc-400">Gold</div>
                </div>
              )}
              {quest.rewards?.exp > 0 && (
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-center">
                  <Star className="w-6 h-6 mx-auto mb-1 text-blue-400" />
                  <div className="font-bold text-blue-400">{quest.rewards.exp}</div>
                  <div className="text-xs text-zinc-400">Experience</div>
                </div>
              )}
              {quest.rep_reward?.faction && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 text-center">
                  <Flag className="w-6 h-6 mx-auto mb-1 text-purple-400" />
                  <div className="font-bold text-purple-400">+{quest.rep_reward.amount}</div>
                  <div className="text-xs text-zinc-400">{factions[quest.rep_reward.faction]?.name || 'Rep'}</div>
                </div>
              )}
            </div>
          </div>
          
          {/* Time Info */}
          {quest.time_limit_hours && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <Clock className="w-4 h-4" />
              <span>Time limit: {quest.time_limit_hours} hours</span>
            </div>
          )}
        </div>
        
        <div className="p-6 border-t border-zinc-800 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 bg-zinc-800 rounded-lg font-medium hover:bg-zinc-700"
          >
            Close
          </button>
          {!isActive ? (
            <button
              onClick={onAccept}
              className="flex-1 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium hover:opacity-90 flex items-center justify-center gap-2"
              data-testid="accept-quest-btn"
            >
              Accept Quest
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : allComplete ? (
            <button
              onClick={onComplete}
              className="flex-1 py-3 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg font-medium hover:opacity-90 flex items-center justify-center gap-2"
              data-testid="complete-quest-btn"
            >
              <CheckCircle className="w-4 h-4" />
              Complete Quest
            </button>
          ) : (
            <button
              disabled
              className="flex-1 py-3 bg-zinc-700 rounded-lg font-medium opacity-50 cursor-not-allowed"
            >
              In Progress...
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestLog;
