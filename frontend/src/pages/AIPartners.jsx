import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Cpu, Coins, TrendingUp, Clock, Heart, Zap, Play, Square, Gift, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const AIPartners = () => {
  const navigate = useNavigate();
  const [programs, setPrograms] = useState({});
  const [userStatus, setUserStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [deployModal, setDeployModal] = useState(null);
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchUserStatus, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [programsRes, statusRes] = await Promise.all([
        fetch(`${API}/api/ai-partner/programs`),
        fetch(`${API}/api/ai-partner/user/${userId}/status`)
      ]);
      
      if (programsRes.ok) {
        const data = await programsRes.json();
        setPrograms(data.programs || {});
      }
      if (statusRes.ok) {
        setUserStatus(await statusRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch AI partner data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserStatus = async () => {
    try {
      const res = await fetch(`${API}/api/ai-partner/user/${userId}/status`);
      if (res.ok) setUserStatus(await res.json());
    } catch (err) {
      console.error('Failed to refresh status:', err);
    }
  };

  const claimEarnings = async () => {
    try {
      const res = await fetch(`${API}/api/ai-partner/claim/${userId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Claimed ${data.claimed.gold.toFixed(0)} Gold + ${data.claimed.ve.toFixed(4)} VE$!`);
        fetchUserStatus();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to claim');
      }
    } catch (err) {
      toast.error('Failed to claim earnings');
    }
  };

  const shutdownProgram = async (deploymentId) => {
    try {
      const res = await fetch(`${API}/api/ai-partner/shutdown/${deploymentId}?user_id=${userId}`, { 
        method: 'DELETE' 
      });
      if (res.ok) {
        toast.success('Program shut down. Compute returned.');
        fetchUserStatus();
      }
    } catch (err) {
      toast.error('Failed to shutdown');
    }
  };

  const getTrustTier = (trustLevel) => {
    if (trustLevel >= 90) return { name: 'Soulbound', color: 'text-purple-400', bonus: '1.5x' };
    if (trustLevel >= 75) return { name: 'Trusted Ally', color: 'text-blue-400', bonus: '1.35x' };
    if (trustLevel >= 60) return { name: 'Partner', color: 'text-green-400', bonus: '1.2x' };
    if (trustLevel >= 40) return { name: 'Associate', color: 'text-yellow-400', bonus: '1.0x' };
    if (trustLevel >= 20) return { name: 'Acquaintance', color: 'text-orange-400', bonus: '0.8x' };
    return { name: 'Stranger', color: 'text-zinc-400', bonus: '0.6x' };
  };

  const programIcons = {
    'chart-line': TrendingUp,
    'pickaxe': Cpu,
    'hammer': Cpu,
    'scroll': Cpu,
    'store': Cpu,
    'wheat': Cpu,
    'dungeon': Cpu,
    'flask': Cpu,
    'shield': Cpu,
    'zap': Zap
  };

  const relationship = userStatus?.relationship || { trust_level: 50 };
  const trustTier = getTrustTier(relationship.trust_level || 50);
  const pendingEarnings = userStatus?.pending_earnings || { gold: 0, ve: 0 };
  const deployedPrograms = userStatus?.deployed_programs || [];

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
              <h1 className="text-xl font-bold">AI Partners</h1>
              <p className="text-sm text-zinc-400">Deploy AI programs for passive income</p>
            </div>
          </div>
        </div>
      </header>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
        </div>
      ) : (
        <main className="max-w-7xl mx-auto px-4 py-6">
          {/* Trust & Earnings Section */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {/* Trust Level */}
            <div className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-500/30 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                  <Heart className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <div className="text-sm text-zinc-400">Trust Level</div>
                  <div className={`font-bold ${trustTier.color}`}>{trustTier.name}</div>
                </div>
              </div>
              <div className="mb-2">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-zinc-400">Trust</span>
                  <span>{Math.min(100, relationship.trust_level || 50).toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all"
                    style={{ width: `${Math.min(100, relationship.trust_level || 50)}%` }}
                  />
                </div>
              </div>
              <div className="text-xs text-zinc-500">
                Earnings Bonus: <span className="text-purple-400 font-medium">{trustTier.bonus}</span>
              </div>
            </div>

            {/* Pending Earnings */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
              <div className="text-sm text-zinc-400 mb-4">Pending Earnings</div>
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-amber-400">
                    <Coins className="w-4 h-4" />
                    Gold
                  </span>
                  <span className="font-bold text-amber-400">{pendingEarnings.gold.toFixed(0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-green-400">
                    <TrendingUp className="w-4 h-4" />
                    VE$
                  </span>
                  <span className="font-bold text-green-400">{pendingEarnings.ve.toFixed(4)}</span>
                </div>
              </div>
              <button
                onClick={claimEarnings}
                disabled={pendingEarnings.gold === 0 && pendingEarnings.ve === 0}
                className="w-full py-2 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="claim-earnings-btn"
              >
                Claim All
              </button>
            </div>

            {/* Active Programs */}
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
              <div className="text-sm text-zinc-400 mb-2">Active Programs</div>
              <div className="text-4xl font-bold mb-2">{deployedPrograms.length}</div>
              <div className="text-xs text-zinc-500">
                Total compute allocated: {deployedPrograms.reduce((sum, p) => sum + (p.compute_allocation || 0), 0)} units
              </div>
            </div>
          </div>

          {/* Deployed Programs */}
          {deployedPrograms.length > 0 && (
            <div className="mb-8">
              <h2 className="text-lg font-bold mb-4">Active AI Programs</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {deployedPrograms.map(prog => {
                  const config = programs[prog.program_type] || {};
                  const IconComponent = programIcons[config.icon] || Cpu;
                  
                  return (
                    <div 
                      key={prog.deployment_id}
                      className="bg-zinc-900/50 border border-green-500/30 rounded-xl p-4"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                            <IconComponent className="w-5 h-5 text-green-400" />
                          </div>
                          <div>
                            <div className="font-medium">{config.name || prog.program_type}</div>
                            <div className="text-xs text-zinc-400">{prog.compute_allocation} compute</div>
                          </div>
                        </div>
                        <span className="flex items-center gap-1 text-xs text-green-400">
                          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                          Running
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-xs text-zinc-400">Pending Gold</div>
                          <div className="font-medium text-amber-400">{(prog.pending_gold || 0).toFixed(1)}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-xs text-zinc-400">Pending VE$</div>
                          <div className="font-medium text-green-400">{(prog.pending_ve || 0).toFixed(4)}</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between text-xs text-zinc-500 mb-3">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Running {(prog.hours_running || 0).toFixed(1)}h
                        </span>
                        <span>Total: {(prog.total_gold_earned || 0).toFixed(0)} Gold</span>
                      </div>
                      
                      <button
                        onClick={() => shutdownProgram(prog.deployment_id)}
                        className="w-full py-2 bg-zinc-800 hover:bg-red-900/50 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                        data-testid={`shutdown-${prog.deployment_id}`}
                      >
                        <Square className="w-3 h-3" />
                        Shutdown
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Available Programs */}
          <div>
            <h2 className="text-lg font-bold mb-4">Deploy AI Programs</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(programs).map(([key, prog]) => {
                const IconComponent = programIcons[prog.icon] || Cpu;
                const isDeployed = deployedPrograms.some(d => d.program_type === key);
                
                return (
                  <div 
                    key={key}
                    className={`bg-zinc-900/50 border rounded-xl p-5 transition-colors cursor-pointer ${
                      selectedProgram === key ? 'border-purple-500' : 'border-zinc-800 hover:border-zinc-700'
                    }`}
                    onClick={() => setSelectedProgram(selectedProgram === key ? null : key)}
                    data-testid={`program-${key}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-12 h-12 bg-zinc-800 rounded-xl flex items-center justify-center">
                        <IconComponent className="w-6 h-6 text-purple-400" />
                      </div>
                      {isDeployed && (
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">Active</span>
                      )}
                    </div>
                    
                    <h3 className="font-semibold mb-1">{prog.name}</h3>
                    <p className="text-sm text-zinc-400 mb-4 line-clamp-2">{prog.description}</p>
                    
                    <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                      <div className="bg-zinc-800/50 rounded p-2">
                        <div className="text-zinc-500">Min Compute</div>
                        <div className="font-medium">{prog.compute_required}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded p-2">
                        <div className="text-zinc-500">Gold/hr</div>
                        <div className="font-medium text-amber-400">{prog.base_gold_per_hour}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded p-2">
                        <div className="text-zinc-500">VE$/hr</div>
                        <div className="font-medium text-green-400">{prog.base_ve_per_hour}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded p-2">
                        <div className="text-zinc-500">Max Mult</div>
                        <div className="font-medium text-purple-400">{prog.max_multiplier}x</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-xs px-2 py-1 rounded ${
                        prog.risk_level === 'none' ? 'bg-green-500/20 text-green-400' :
                        prog.risk_level === 'very_low' ? 'bg-emerald-500/20 text-emerald-400' :
                        prog.risk_level === 'low' ? 'bg-blue-500/20 text-blue-400' :
                        prog.risk_level === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {prog.risk_level?.replace('_', ' ')} risk
                      </span>
                      <span className="text-xs text-zinc-500">{prog.category}</span>
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeployModal(key);
                      }}
                      className="w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium text-sm hover:opacity-90 flex items-center justify-center gap-2"
                      data-testid={`deploy-${key}-btn`}
                    >
                      <Play className="w-4 h-4" />
                      Deploy
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </main>
      )}

      {/* Deploy Modal */}
      {deployModal && (
        <DeployModal
          programKey={deployModal}
          program={programs[deployModal]}
          userId={userId}
          onClose={() => setDeployModal(null)}
          onDeployed={() => {
            setDeployModal(null);
            fetchUserStatus();
            toast.success('AI program deployed successfully!');
          }}
        />
      )}
    </div>
  );
};

// Deploy Modal Component
const DeployModal = ({ programKey, program, userId, onClose, onDeployed }) => {
  const [computeAllocation, setComputeAllocation] = useState(program.compute_required);
  const [autoReinvest, setAutoReinvest] = useState(false);
  const [deploying, setDeploying] = useState(false);

  const handleDeploy = async () => {
    setDeploying(true);
    try {
      const res = await fetch(`${API}/api/ai-partner/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          program_type: programKey,
          compute_allocation: computeAllocation,
          auto_reinvest: autoReinvest
        })
      });
      
      if (res.ok) {
        onDeployed();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to deploy');
      }
    } catch (err) {
      toast.error('Failed to deploy program');
    } finally {
      setDeploying(false);
    }
  };

  // Calculate estimated earnings
  const computeRatio = computeAllocation / program.compute_required;
  const computeMult = Math.min(1 + Math.log10(computeRatio + 1) * program.scaling_factor, program.max_multiplier);
  const estGoldPerHour = program.base_gold_per_hour * computeMult;
  const estVePerHour = program.base_ve_per_hour * computeMult;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md">
        <div className="p-6 border-b border-zinc-800">
          <h2 className="text-xl font-bold">Deploy {program.name}</h2>
          <p className="text-sm text-zinc-400">{program.description}</p>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Compute Allocation</label>
            <input
              type="range"
              min={program.compute_required}
              max={program.compute_required * 5}
              step={10}
              value={computeAllocation}
              onChange={e => setComputeAllocation(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-sm mt-1">
              <span className="text-zinc-400">Min: {program.compute_required}</span>
              <span className="text-purple-400 font-medium">{computeAllocation} units</span>
            </div>
          </div>
          
          <div className="bg-zinc-800/50 rounded-lg p-4">
            <div className="text-sm font-medium mb-3">Estimated Hourly Earnings</div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-zinc-400">Gold</div>
                <div className="text-xl font-bold text-amber-400">{estGoldPerHour.toFixed(1)}</div>
              </div>
              <div>
                <div className="text-xs text-zinc-400">VE$</div>
                <div className="text-xl font-bold text-green-400">{estVePerHour.toFixed(4)}</div>
              </div>
            </div>
            <div className="text-xs text-zinc-500 mt-2">
              Multiplier: {computeMult.toFixed(2)}x (max {program.max_multiplier}x)
            </div>
          </div>
          
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={autoReinvest}
              onChange={e => setAutoReinvest(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm">Auto-reinvest earnings into compute</span>
          </label>
        </div>
        
        <div className="p-6 border-t border-zinc-800 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-zinc-800 rounded-lg font-medium hover:bg-zinc-700"
          >
            Cancel
          </button>
          <button
            onClick={handleDeploy}
            disabled={deploying}
            className="flex-1 py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium hover:opacity-90 disabled:opacity-50"
            data-testid="confirm-deploy-btn"
          >
            {deploying ? 'Deploying...' : 'Deploy'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIPartners;
