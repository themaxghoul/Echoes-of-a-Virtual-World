import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Hammer, Sword, Sparkles, MessageCircle, BookOpen, Leaf,
  RefreshCw, Clock, Star, Coins, CheckCircle, XCircle, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const NPCServices = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState({});
  const [trainedNPCs, setTrainedNPCs] = useState([]);
  const [selectedNPC, setSelectedNPC] = useState(null);
  const [npcServices, setNpcServices] = useState([]);
  const [serviceHistory, setServiceHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [activeTab, setActiveTab] = useState('browse');
  
  const userId = localStorage.getItem('userId') || 'guest';

  const categoryIcons = {
    combat: Sword,
    crafting: Hammer,
    magic: Sparkles,
    social: MessageCircle,
    knowledge: BookOpen,
    survival: Leaf
  };

  const categoryColors = {
    combat: 'from-red-500/20 to-red-600/10 border-red-500/30',
    crafting: 'from-amber-500/20 to-amber-600/10 border-amber-500/30',
    magic: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
    social: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
    knowledge: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30',
    survival: 'from-green-500/20 to-green-600/10 border-green-500/30'
  };

  const masteryColors = {
    novice: 'text-zinc-400',
    student: 'text-green-400',
    apprentice: 'text-blue-400',
    journeyman: 'text-purple-400',
    expert: 'text-yellow-400',
    master: 'text-orange-400',
    grandmaster: 'text-red-400'
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [catRes, histRes] = await Promise.all([
        fetch(`${API}/api/npc-services/categories`),
        fetch(`${API}/api/npc-services/history/${userId}`)
      ]);
      
      if (catRes.ok) {
        const data = await catRes.json();
        setCategories(data.categories || {});
      }
      if (histRes.ok) {
        const data = await histRes.json();
        setServiceHistory(data.history || []);
      }
      
      // Get trained NPCs from AI training system
      await fetchTrainedNPCs();
    } catch (err) {
      toast.error('Failed to load services');
    } finally {
      setLoading(false);
    }
  };

  const fetchTrainedNPCs = async () => {
    try {
      // Get leaderboard of top service providers
      const res = await fetch(`${API}/api/npc-services/leaderboard?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setTrainedNPCs(data.leaderboard || []);
      }
    } catch (err) {
      // Fallback to empty list
    }
  };

  const fetchNPCServices = async (npcId) => {
    try {
      const res = await fetch(`${API}/api/npc-services/npc/${npcId}/available`);
      if (res.ok) {
        const data = await res.json();
        setNpcServices(data.available_services || []);
      }
    } catch (err) {
      toast.error('Failed to load NPC services');
    }
  };

  const selectNPC = async (npc) => {
    setSelectedNPC(npc);
    await fetchNPCServices(npc._id);
  };

  const requestService = async (serviceType) => {
    if (!selectedNPC) return;
    
    setRequesting(true);
    try {
      const res = await fetch(`${API}/api/npc-services/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_id: userId,
          npc_id: selectedNPC._id,
          service_type: serviceType,
          payment_method: 've'
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(`Service completed! Quality: ${(data.quality_rating * 100).toFixed(0)}%`);
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Service request failed');
      }
    } catch (err) {
      toast.error('Failed to request service');
    } finally {
      setRequesting(false);
    }
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-black flex items-center justify-center">
        <div className="text-amber-400 animate-pulse text-xl">Loading Services...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-black text-white">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-amber-900/30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-amber-400 hover:text-amber-300 transition-colors"
            data-testid="back-button"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="hidden sm:inline">Back</span>
          </button>
          
          <h1 className="text-xl font-bold text-amber-400">NPC Services</h1>
          
          <button
            onClick={fetchData}
            className="p-2 text-zinc-400 hover:text-amber-400 transition-colors"
            data-testid="refresh-button"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="pt-20 pb-8 px-4 max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('browse')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'browse'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-zinc-800/50 text-zinc-400 hover:text-zinc-300'
            }`}
            data-testid="tab-browse"
          >
            Browse Services
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'history'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-zinc-800/50 text-zinc-400 hover:text-zinc-300'
            }`}
            data-testid="tab-history"
          >
            My History
          </button>
        </div>

        {activeTab === 'browse' && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left Panel - Categories */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300 mb-3">Service Categories</h2>
              
              {Object.entries(categories).map(([catName, services]) => {
                const Icon = categoryIcons[catName] || Sparkles;
                const colorClass = categoryColors[catName] || 'from-zinc-500/20 to-zinc-600/10 border-zinc-500/30';
                
                return (
                  <div 
                    key={catName}
                    className={`p-4 rounded-xl bg-gradient-to-br ${colorClass} border`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-black/30 rounded-lg">
                        <Icon className="w-5 h-5 text-white/70" />
                      </div>
                      <h3 className="text-white font-medium capitalize">{catName}</h3>
                      <span className="ml-auto text-sm text-zinc-400">{services.length} services</span>
                    </div>
                    
                    <div className="space-y-2">
                      {services.slice(0, 3).map((service, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <span className="text-zinc-300">{service.name}</span>
                          <span className="text-amber-400">VE${service.base_cost_ve.toFixed(2)}</span>
                        </div>
                      ))}
                      {services.length > 3 && (
                        <div className="text-xs text-zinc-500">+{services.length - 3} more...</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Middle Panel - Trained NPCs */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300 mb-3">Top Service Providers</h2>
              
              {trainedNPCs.length === 0 ? (
                <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                  <Sparkles className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">No trained NPCs yet</p>
                  <p className="text-sm text-zinc-500 mt-1">Train NPCs using the AI Training system</p>
                </div>
              ) : (
                trainedNPCs.map((npc, idx) => (
                  <button
                    key={npc._id}
                    onClick={() => selectNPC(npc)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      selectedNPC?._id === npc._id
                        ? 'bg-amber-500/20 border-2 border-amber-500/50'
                        : 'bg-zinc-800/50 border border-zinc-700/50 hover:border-amber-500/30'
                    }`}
                    data-testid={`npc-${idx}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-white">{npc.npc_name}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                        #{idx + 1}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-zinc-400">
                        {npc.services} services
                      </span>
                      <span className="text-amber-400">
                        VE${npc.revenue.toFixed(2)}
                      </span>
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Star className="w-3 h-3" />
                        <span>{(npc.avg_quality * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </button>
                ))
              )}
              
              {/* Manual NPC ID input */}
              <div className="p-4 rounded-xl bg-zinc-800/30 border border-zinc-700/30">
                <p className="text-sm text-zinc-400 mb-2">Check specific NPC services:</p>
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  const npcId = e.target.npcId.value;
                  if (npcId) {
                    setSelectedNPC({ _id: npcId, npc_name: npcId });
                    await fetchNPCServices(npcId);
                  }
                }} className="flex gap-2">
                  <input
                    type="text"
                    name="npcId"
                    placeholder="NPC ID..."
                    className="flex-1 px-3 py-2 rounded-lg bg-black/50 border border-zinc-700 text-white text-sm focus:border-amber-500/50 outline-none"
                    data-testid="npc-id-input"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-black font-medium rounded-lg text-sm"
                    data-testid="check-npc-button"
                  >
                    Check
                  </button>
                </form>
              </div>
            </div>

            {/* Right Panel - NPC Services */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="text-lg font-semibold text-zinc-300 mb-3">
                {selectedNPC ? `${selectedNPC.npc_name}'s Services` : 'Select an NPC'}
              </h2>
              
              {!selectedNPC ? (
                <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                  <ChevronRight className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">Select an NPC to view their services</p>
                </div>
              ) : npcServices.length === 0 ? (
                <div className="p-6 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                  <XCircle className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">This NPC has no trained skills yet</p>
                  <p className="text-sm text-zinc-500 mt-1">Train them using the AI Training system</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {npcServices.map((service, idx) => {
                    const Icon = categoryIcons[service.category] || Sparkles;
                    
                    return (
                      <div 
                        key={idx}
                        className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Icon className="w-4 h-4 text-amber-400" />
                            <span className="font-medium text-white">{service.name}</span>
                          </div>
                          <span className={`text-xs font-medium ${masteryColors[service.npc_mastery]}`}>
                            {service.npc_mastery}
                          </span>
                        </div>
                        
                        <p className="text-sm text-zinc-400 mb-3">{service.description}</p>
                        
                        <div className="flex items-center gap-4 text-xs text-zinc-500 mb-3">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {service.duration_minutes}min
                          </span>
                          <span className="flex items-center gap-1">
                            <Star className="w-3 h-3" />
                            {(service.quality_rating * 100).toFixed(0)}%
                          </span>
                          {service.cooldown_hours > 0 && (
                            <span>CD: {service.cooldown_hours}h</span>
                          )}
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span className="text-amber-400 font-medium">
                            VE${service.cost_ve.toFixed(2)}
                          </span>
                          <button
                            onClick={() => requestService(service.service_id)}
                            disabled={requesting}
                            className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-black font-medium rounded-lg text-sm transition-colors"
                            data-testid={`request-service-${idx}`}
                          >
                            {requesting ? 'Requesting...' : 'Request'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-zinc-300">Service History</h2>
              <span className="text-sm text-zinc-500">{serviceHistory.length} total</span>
            </div>
            
            {serviceHistory.length === 0 ? (
              <div className="p-8 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                <Clock className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                <p className="text-zinc-400">No services used yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {serviceHistory.map((entry, idx) => (
                  <div 
                    key={idx}
                    className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-400" />
                        <span className="font-medium text-white">{entry.service_type}</span>
                      </div>
                      <div className="text-sm text-zinc-400 mt-1">
                        NPC: {entry.npc_id} • {formatTime(entry.completed_at)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-amber-400 font-medium">VE${entry.cost_paid.toFixed(2)}</div>
                      <div className="text-sm text-zinc-500">
                        Quality: {(entry.quality_rating * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default NPCServices;
