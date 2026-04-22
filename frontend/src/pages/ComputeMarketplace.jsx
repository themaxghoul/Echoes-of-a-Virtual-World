import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { 
  ArrowLeft, Cpu, Server, HardDrive, Zap, DollarSign,
  RefreshCw, TrendingUp, Clock, CheckCircle, AlertTriangle,
  Settings, Activity, BarChart3, Users, Brain, Sparkles,
  Box, Layers, Monitor, Gauge, Database, Cloud,
  FileText, ArrowUpRight, ArrowDownLeft, Eye
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatVE = (amount) => {
  if (amount === null || amount === undefined) return 'VE$0.00';
  return `VE$${parseFloat(amount).toFixed(2)}`;
};

// Hardware tiers with icons
const HARDWARE_ICONS = {
  raspberry_pi: Box,
  mini_pc: Monitor,
  workstation: Cpu,
  server_node: Server,
  compute_rack: Layers
};

// Cloud tiers with icons
const CLOUD_ICONS = {
  basic: Cloud,
  standard: Server,
  performance: Zap,
  gpu_basic: Cpu,
  gpu_advanced: Brain,
  gpu_cluster: Layers
};

const ComputeMarketplace = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const [isAI, setIsAI] = useState(false);
  const entityId = isAI ? `npc_${userId}` : userId;
  
  const [loading, setLoading] = useState(true);
  const [computeTiers, setComputeTiers] = useState({});
  const [hardwareTiers, setHardwareTiers] = useState({});
  const [ownedHardware, setOwnedHardware] = useState([]);
  const [activeCompute, setActiveCompute] = useState([]);
  const [wallet, setWallet] = useState(null);
  const [veRate, setVeRate] = useState(null);
  const [economyStats, setEconomyStats] = useState(null);
  const [topInvestors, setTopInvestors] = useState(null);
  const [systemLogs, setSystemLogs] = useState([]);
  
  // Purchase states
  const [selectedCloud, setSelectedCloud] = useState(null);
  const [cloudHours, setCloudHours] = useState(1);
  const [selectedHardware, setSelectedHardware] = useState(null);
  
  // Log generator for business owners
  const generateSystemLog = (action, details) => {
    const log = {
      timestamp: new Date().toISOString(),
      action,
      details,
      id: Math.random().toString(36).substr(2, 9)
    };
    setSystemLogs(prev => [log, ...prev.slice(0, 49)]); // Keep last 50 logs
  };

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tiersRes, walletRes, rateRes, statsRes, investorsRes] = await Promise.all([
        axios.get(`${API}/economy/compute/tiers`),
        axios.get(`${API}/entity-earnings/wallet/player/${entityId}`).catch(() => ({ data: null })),
        axios.get(`${API}/economy/ve/rate`).catch(() => ({ data: null })),
        axios.get(`${API}/economy/stats/overview`).catch(() => ({ data: null })),
        axios.get(`${API}/economy/ai/top-investors?limit=10`).catch(() => ({ data: null }))
      ]);
      
      setComputeTiers(tiersRes.data.cloud_compute || {});
      setHardwareTiers(tiersRes.data.hardware_purchase || {});
      setWallet(walletRes.data);
      setVeRate(rateRes.data);
      setEconomyStats(statsRes.data);
      setTopInvestors(investorsRes.data);
      
      // Load owned hardware and active compute
      if (entityId) {
        const [hwRes, computeRes] = await Promise.all([
          axios.get(`${API}/economy/hardware/owned/${entityId}`).catch(() => ({ data: { hardware: [] } })),
          axios.get(`${API}/economy/compute/active/${entityId}`).catch(() => ({ data: { allocations: [] } }))
        ]);
        setOwnedHardware(hwRes.data.hardware || []);
        setActiveCompute(computeRes.data.allocations || []);
      }
      
      generateSystemLog('SYSTEM_INIT', { status: 'Dashboard loaded successfully' });
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load marketplace data');
      generateSystemLog('ERROR', { message: 'Failed to load marketplace data' });
    }
    setLoading(false);
  }, [entityId]);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate, loadData]);

  // Purchase cloud compute
  const purchaseCloudCompute = async () => {
    if (!selectedCloud) return;
    
    const tier = computeTiers[selectedCloud];
    const cost = tier.hourly_cost_ve * cloudHours;
    
    if ((wallet?.balance_ve || 0) < cost) {
      toast.error('Insufficient VE$ balance');
      return;
    }
    
    try {
      const res = await axios.post(`${API}/economy/compute/allocate`, {
        owner_id: entityId,
        owner_type: isAI ? 'npc' : 'player',
        tier: selectedCloud,
        hours: cloudHours,
        purpose: 'General compute'
      });
      
      toast.success(`Allocated ${tier.name} for ${cloudHours}h`);
      generateSystemLog('COMPUTE_ALLOCATED', {
        tier: selectedCloud,
        hours: cloudHours,
        cost: cost,
        allocation_id: res.data.allocation_id
      });
      
      setSelectedCloud(null);
      setCloudHours(1);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to allocate compute');
      generateSystemLog('ERROR', { message: 'Compute allocation failed' });
    }
  };

  // Purchase hardware
  const purchaseHardware = async () => {
    if (!selectedHardware) return;
    
    const hardware = hardwareTiers[selectedHardware];
    
    if ((wallet?.balance_ve || 0) < hardware.one_time_cost_ve) {
      toast.error('Insufficient VE$ balance');
      return;
    }
    
    try {
      const res = await axios.post(`${API}/economy/hardware/purchase`, {
        owner_id: entityId,
        owner_type: isAI ? 'npc' : 'player',
        hardware_type: selectedHardware
      });
      
      toast.success(`Purchased ${hardware.name}!`);
      generateSystemLog('HARDWARE_PURCHASED', {
        type: selectedHardware,
        cost: hardware.one_time_cost_ve,
        ownership_id: res.data.ownership_id,
        monthly_yield: hardware.monthly_yield_ve
      });
      
      setSelectedHardware(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to purchase hardware');
      generateSystemLog('ERROR', { message: 'Hardware purchase failed' });
    }
  };

  // Collect hardware yield
  const collectYield = async (ownershipId, hardwareType) => {
    try {
      const res = await axios.post(`${API}/economy/hardware/${ownershipId}/collect-yield`);
      
      toast.success(`Collected ${formatVE(res.data.yield_ve)}!`);
      generateSystemLog('YIELD_COLLECTED', {
        ownership_id: ownershipId,
        hardware: hardwareType,
        yield: res.data.yield_ve,
        health: res.data.new_health_percent
      });
      
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to collect yield');
      generateSystemLog('WARNING', { message: error.response?.data?.detail || 'Yield collection issue' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Compute Marketplace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/earnings')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Cpu className="w-6 h-6" />
                AI Compute Marketplace
              </h1>
              <p className="text-sm text-muted-foreground">Cloud compute & self-computing farms</p>
            </div>
          </div>
          
          {/* Balance & Mode */}
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-lg font-bold text-gold">{formatVE(wallet?.balance_ve || 0)}</div>
              <div className="text-xs text-muted-foreground">Available Balance</div>
            </div>
            <Button
              variant={isAI ? "default" : "outline"}
              size="sm"
              onClick={() => setIsAI(!isAI)}
              className={isAI ? "bg-purple-600" : ""}
              data-testid="toggle-ai-mode"
            >
              <Brain className="w-4 h-4 mr-1" />
              {isAI ? 'AI Mode' : 'Player Mode'}
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        <Tabs defaultValue="cloud" className="space-y-6">
          <TabsList className="bg-surface/50">
            <TabsTrigger value="cloud">Cloud Compute</TabsTrigger>
            <TabsTrigger value="hardware">Self-Computing Farm</TabsTrigger>
            <TabsTrigger value="portfolio">My Portfolio</TabsTrigger>
            <TabsTrigger value="logs">System Logs</TabsTrigger>
            <TabsTrigger value="market">Market Stats</TabsTrigger>
          </TabsList>

          {/* Cloud Compute Tab */}
          <TabsContent value="cloud" className="space-y-6">
            {/* VE$ Rate Card */}
            {veRate && (
              <Card className="p-4 bg-gradient-to-r from-gold/10 to-transparent border-gold/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gold/20 flex items-center justify-center">
                      <DollarSign className="w-6 h-6 text-gold" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold">1 VE$ = ${veRate.ve_to_usd} USD</div>
                      <div className="text-sm text-muted-foreground">
                        Circulating: {formatVE(veRate.circulating_supply_ve)} | Market Cap: ${Math.round(veRate.market_cap_usd).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-green-500/20 text-green-400">
                    <Activity className="w-3 h-3 mr-1" />
                    Stable
                  </Badge>
                </div>
              </Card>
            )}

            {/* Cloud Tiers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(computeTiers).map(([key, tier]) => {
                const Icon = CLOUD_ICONS[key] || Cloud;
                const isSelected = selectedCloud === key;
                const totalCost = tier.hourly_cost_ve * (isSelected ? cloudHours : 1);
                
                return (
                  <Card 
                    key={key}
                    className={`p-6 bg-surface/50 border-2 transition-all cursor-pointer ${
                      isSelected ? 'border-gold' : 'border-border/30 hover:border-gold/50'
                    }`}
                    onClick={() => setSelectedCloud(isSelected ? null : key)}
                    data-testid={`cloud-tier-${key}`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-12 h-12 rounded-xl ${
                        key.includes('gpu') ? 'bg-purple-500' : 'bg-cyan-500'
                      } flex items-center justify-center`}>
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <Badge className="bg-gold/20 text-gold">
                        {formatVE(tier.hourly_cost_ve)}/hr
                      </Badge>
                    </div>
                    
                    <h3 className="font-cinzel text-lg mb-2">{tier.name}</h3>
                    <p className="text-sm text-muted-foreground mb-4">{tier.description}</p>
                    
                    {/* Specs */}
                    <div className="space-y-1 text-xs text-muted-foreground mb-4">
                      {tier.specs.vcpu && <div>vCPU: {tier.specs.vcpu}</div>}
                      {tier.specs.ram_gb && <div>RAM: {tier.specs.ram_gb}GB</div>}
                      {tier.specs.gpu && <div>GPU: {tier.specs.gpu}</div>}
                      {tier.specs.vram_gb && <div>VRAM: {tier.specs.vram_gb}GB</div>}
                    </div>
                    
                    {/* Use cases */}
                    <div className="flex flex-wrap gap-1 mb-4">
                      {tier.use_cases.slice(0, 3).map(use => (
                        <Badge key={use} variant="outline" className="text-xs">
                          {use}
                        </Badge>
                      ))}
                    </div>
                    
                    {isSelected && (
                      <div className="space-y-3 pt-4 border-t border-border/30">
                        <div>
                          <label className="text-sm text-muted-foreground">Hours to allocate</label>
                          <Input
                            type="number"
                            value={cloudHours}
                            onChange={(e) => setCloudHours(Math.max(1, parseInt(e.target.value) || 1))}
                            min="1"
                            className="mt-1"
                            onClick={(e) => e.stopPropagation()}
                            data-testid="cloud-hours-input"
                          />
                        </div>
                        <div className="flex justify-between text-sm">
                          <span>Total Cost:</span>
                          <span className="font-bold text-gold">{formatVE(totalCost)}</span>
                        </div>
                        <Button 
                          className="w-full bg-gold text-black hover:bg-gold-light"
                          onClick={(e) => { e.stopPropagation(); purchaseCloudCompute(); }}
                          disabled={(wallet?.balance_ve || 0) < totalCost}
                          data-testid="purchase-cloud-btn"
                        >
                          <Zap className="w-4 h-4 mr-2" />
                          Allocate Compute
                        </Button>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* Hardware Tab */}
          <TabsContent value="hardware" className="space-y-6">
            <Card className="p-4 bg-gradient-to-r from-purple-500/10 to-transparent border-purple-500/30">
              <div className="flex items-center gap-4">
                <HardDrive className="w-8 h-8 text-purple-400" />
                <div>
                  <h3 className="font-cinzel text-lg">Build Your Computing Empire</h3>
                  <p className="text-sm text-muted-foreground">
                    Purchase hardware for passive VE$ income. Collect yields regularly before hardware degrades.
                  </p>
                </div>
              </div>
            </Card>

            {/* Hardware Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(hardwareTiers).map(([key, hw]) => {
                const Icon = HARDWARE_ICONS[key] || Server;
                const isSelected = selectedHardware === key;
                const roi = (hw.monthly_yield_ve * hw.lifespan_months) / hw.one_time_cost_ve;
                
                return (
                  <Card 
                    key={key}
                    className={`p-6 bg-surface/50 border-2 transition-all cursor-pointer ${
                      isSelected ? 'border-purple-500' : 'border-border/30 hover:border-purple-500/50'
                    }`}
                    onClick={() => setSelectedHardware(isSelected ? null : key)}
                    data-testid={`hardware-${key}`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-purple-500 flex items-center justify-center">
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <Badge className="bg-green-500/20 text-green-400">
                        {formatVE(hw.monthly_yield_ve)}/mo
                      </Badge>
                    </div>
                    
                    <h3 className="font-cinzel text-lg mb-2">{hw.name}</h3>
                    <p className="text-sm text-muted-foreground mb-4">{hw.description}</p>
                    
                    {/* Specs */}
                    <div className="space-y-1 text-xs text-muted-foreground mb-4">
                      {hw.specs.cpu && <div>CPU: {hw.specs.cpu}</div>}
                      {hw.specs.ram_gb && <div>RAM: {hw.specs.ram_gb}GB</div>}
                      {hw.specs.gpu && <div>GPU: {hw.specs.gpu}</div>}
                      {hw.specs.power_watts && <div>Power: {hw.specs.power_watts}W</div>}
                      {hw.specs.nodes && <div>Nodes: {hw.specs.nodes}</div>}
                    </div>
                    
                    <div className="flex justify-between text-sm mb-4">
                      <span className="text-muted-foreground">Lifespan</span>
                      <span>{hw.lifespan_months} months</span>
                    </div>
                    <div className="flex justify-between text-sm mb-4">
                      <span className="text-muted-foreground">ROI</span>
                      <span className={roi > 1 ? 'text-green-400' : 'text-yellow-400'}>
                        {(roi * 100).toFixed(0)}%
                      </span>
                    </div>
                    
                    <div className="pt-4 border-t border-border/30">
                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-muted-foreground">One-time Cost</span>
                        <span className="font-bold text-purple-400">{formatVE(hw.one_time_cost_ve)}</span>
                      </div>
                      <Button 
                        className="w-full bg-purple-600 hover:bg-purple-500"
                        onClick={(e) => { e.stopPropagation(); setSelectedHardware(key); purchaseHardware(); }}
                        disabled={(wallet?.balance_ve || 0) < hw.one_time_cost_ve}
                        data-testid={`buy-hardware-${key}`}
                      >
                        <HardDrive className="w-4 h-4 mr-2" />
                        Purchase Hardware
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* Portfolio Tab */}
          <TabsContent value="portfolio" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Owned Hardware */}
              <Card className="p-6 bg-surface/50 border-border/30">
                <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                  <HardDrive className="w-5 h-5" />
                  Your Hardware Farm
                </h3>
                
                {ownedHardware.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Server className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No hardware owned yet</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={() => document.querySelector('[data-state="inactive"][value="hardware"]')?.click()}
                    >
                      Browse Hardware
                    </Button>
                  </div>
                ) : (
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-3">
                      {ownedHardware.map(hw => {
                        const hwType = hardwareTiers[hw.hardware_type] || {};
                        const Icon = HARDWARE_ICONS[hw.hardware_type] || Server;
                        
                        return (
                          <Card key={hw.ownership_id} className="p-4 bg-black/20 border-border/20">
                            <div className="flex items-start gap-4">
                              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                                <Icon className="w-5 h-5 text-purple-400" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center justify-between">
                                  <h4 className="font-medium">{hwType.name || hw.hardware_type}</h4>
                                  <Badge className={
                                    hw.status === 'active' ? 'bg-green-500/20 text-green-400' :
                                    hw.status === 'degraded' ? 'bg-yellow-500/20 text-yellow-400' :
                                    'bg-red-500/20 text-red-400'
                                  }>
                                    {hw.status}
                                  </Badge>
                                </div>
                                
                                <div className="mt-2">
                                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                                    <span>Health</span>
                                    <span>{hw.health_percent}%</span>
                                  </div>
                                  <Progress 
                                    value={hw.health_percent} 
                                    className={`h-2 ${
                                      hw.health_percent > 50 ? '' : 
                                      hw.health_percent > 20 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-red-500'
                                    }`}
                                  />
                                </div>
                                
                                <div className="flex items-center justify-between mt-3">
                                  <span className="text-sm text-muted-foreground">
                                    Total Yield: {formatVE(hw.total_yield)}
                                  </span>
                                  <Button
                                    size="sm"
                                    onClick={() => collectYield(hw.ownership_id, hw.hardware_type)}
                                    disabled={hw.status === 'retired'}
                                    className="bg-green-600 hover:bg-green-500"
                                    data-testid={`collect-yield-${hw.ownership_id}`}
                                  >
                                    <ArrowDownLeft className="w-3 h-3 mr-1" />
                                    Collect
                                  </Button>
                                </div>
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </Card>

              {/* Active Compute */}
              <Card className="p-6 bg-surface/50 border-border/30">
                <h3 className="font-cinzel text-lg text-cyan-400 mb-4 flex items-center gap-2">
                  <Cloud className="w-5 h-5" />
                  Active Cloud Allocations
                </h3>
                
                {activeCompute.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Cloud className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No active compute allocations</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={() => document.querySelector('[data-state="inactive"][value="cloud"]')?.click()}
                    >
                      Allocate Compute
                    </Button>
                  </div>
                ) : (
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-3">
                      {activeCompute.map(alloc => {
                        const tier = computeTiers[alloc.tier] || {};
                        const Icon = CLOUD_ICONS[alloc.tier] || Cloud;
                        
                        return (
                          <Card key={alloc.allocation_id} className="p-4 bg-black/20 border-border/20">
                            <div className="flex items-start gap-4">
                              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                                <Icon className="w-5 h-5 text-cyan-400" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center justify-between">
                                  <h4 className="font-medium">{tier.name || alloc.tier}</h4>
                                  <Badge className="bg-green-500/20 text-green-400">
                                    <Activity className="w-3 h-3 mr-1" />
                                    Active
                                  </Badge>
                                </div>
                                <div className="text-sm text-muted-foreground mt-1">
                                  {alloc.hours_used}h allocated • Cost: {formatVE(alloc.total_cost)}
                                </div>
                                {alloc.purpose && (
                                  <div className="text-xs text-muted-foreground mt-2">
                                    Purpose: {alloc.purpose}
                                  </div>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </Card>
            </div>
          </TabsContent>

          {/* System Logs Tab (Business Owner View) */}
          <TabsContent value="logs">
            <Card className="p-6 bg-surface/50 border-border/30">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-cinzel text-lg text-green-400 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  System Logs
                </h3>
                <Badge className="bg-green-500/20 text-green-400">
                  <Eye className="w-3 h-3 mr-1" />
                  Business Owner View
                </Badge>
              </div>
              
              <p className="text-sm text-muted-foreground mb-4">
                Real-time activity logs for your computing operations. Monitor purchases, allocations, and yield collections.
              </p>
              
              <ScrollArea className="h-[500px] font-mono text-sm">
                <div className="space-y-1">
                  {systemLogs.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No logs yet. Activity will appear here.</p>
                    </div>
                  ) : (
                    systemLogs.map(log => (
                      <div 
                        key={log.id}
                        className={`p-3 rounded border-l-4 ${
                          log.action === 'ERROR' ? 'bg-red-500/10 border-red-500' :
                          log.action === 'WARNING' ? 'bg-yellow-500/10 border-yellow-500' :
                          log.action.includes('PURCHASE') || log.action.includes('ALLOCATED') ? 'bg-green-500/10 border-green-500' :
                          'bg-black/20 border-cyan-500'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`font-bold ${
                            log.action === 'ERROR' ? 'text-red-400' :
                            log.action === 'WARNING' ? 'text-yellow-400' :
                            'text-cyan-400'
                          }`}>
                            [{log.action}]
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {Object.entries(log.details).map(([k, v]) => (
                            <span key={k} className="mr-3">
                              <span className="text-foreground">{k}:</span> {typeof v === 'number' ? formatVE(v) : String(v)}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </Card>
          </TabsContent>

          {/* Market Stats Tab */}
          <TabsContent value="market" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Currency Stats */}
              <Card className="p-6 bg-gradient-to-br from-gold/20 to-gold/5 border-gold/30">
                <div className="flex items-center gap-3 mb-4">
                  <DollarSign className="w-8 h-8 text-gold" />
                  <h3 className="font-cinzel text-lg">Currency</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">VE$/USD Rate</span>
                    <span className="font-bold">{economyStats?.currency?.ve_to_usd || 1.00}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Circulating Supply</span>
                    <span className="font-bold">{formatVE(economyStats?.currency?.circulating_supply || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Earned Ever</span>
                    <span className="font-bold text-gold">{formatVE(economyStats?.currency?.total_earned_ever || 0)}</span>
                  </div>
                </div>
              </Card>

              {/* Compute Stats */}
              <Card className="p-6 bg-gradient-to-br from-cyan-500/20 to-cyan-500/5 border-cyan-500/30">
                <div className="flex items-center gap-3 mb-4">
                  <Cloud className="w-8 h-8 text-cyan-400" />
                  <h3 className="font-cinzel text-lg">Compute</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Active Allocations</span>
                    <span className="font-bold">{economyStats?.compute?.active_allocations || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Hardware Units</span>
                    <span className="font-bold">{economyStats?.compute?.total_hardware_units || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Compute Spend</span>
                    <span className="font-bold text-cyan-400">{formatVE(economyStats?.compute?.total_compute_spend_ve || 0)}</span>
                  </div>
                </div>
              </Card>

              {/* Hardware Stats */}
              <Card className="p-6 bg-gradient-to-br from-purple-500/20 to-purple-500/5 border-purple-500/30">
                <div className="flex items-center gap-3 mb-4">
                  <HardDrive className="w-8 h-8 text-purple-400" />
                  <h3 className="font-cinzel text-lg">Hardware</h3>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Hardware Yield</span>
                    <span className="font-bold text-green-400">{formatVE(economyStats?.compute?.total_hardware_yield_ve || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Your Monthly Yield</span>
                    <span className="font-bold">
                      {formatVE(ownedHardware.reduce((sum, hw) => {
                        const type = hardwareTiers[hw.hardware_type];
                        return sum + (type?.monthly_yield_ve || 0) * (hw.health_percent / 100);
                      }, 0))}
                    </span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Top AI Investors */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Brain className="w-5 h-5" />
                Top AI Investors
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Hardware Owners */}
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">Top Hardware Owners (AI)</h4>
                  <div className="space-y-2">
                    {(topInvestors?.top_hardware_owners || []).slice(0, 5).map((investor, idx) => (
                      <div key={investor._id} className="flex items-center gap-3 p-3 bg-black/20 rounded-lg">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          idx === 0 ? 'bg-gold text-black' : 'bg-surface'
                        }`}>
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium">AI {investor._id.slice(-8)}</div>
                          <div className="text-xs text-muted-foreground">{investor.hardware_count} units</div>
                        </div>
                        <div className="text-green-400 font-bold">{formatVE(investor.total_yield)}</div>
                      </div>
                    ))}
                    {(topInvestors?.top_hardware_owners || []).length === 0 && (
                      <p className="text-muted-foreground text-sm">No AI hardware owners yet</p>
                    )}
                  </div>
                </div>

                {/* Compute Spenders */}
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-3">Top Compute Spenders (AI)</h4>
                  <div className="space-y-2">
                    {(topInvestors?.top_compute_spenders || []).slice(0, 5).map((investor, idx) => (
                      <div key={investor._id} className="flex items-center gap-3 p-3 bg-black/20 rounded-lg">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          idx === 0 ? 'bg-cyan-500 text-black' : 'bg-surface'
                        }`}>
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium">AI {investor._id.slice(-8)}</div>
                        </div>
                        <div className="text-cyan-400 font-bold">{formatVE(investor.total_spend)}</div>
                      </div>
                    ))}
                    {(topInvestors?.top_compute_spenders || []).length === 0 && (
                      <p className="text-muted-foreground text-sm">No AI compute spenders yet</p>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ComputeMarketplace;
