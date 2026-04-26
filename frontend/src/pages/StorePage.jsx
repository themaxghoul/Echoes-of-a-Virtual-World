import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Store, DollarSign, Zap, Package, Cpu, Building2, 
  ArrowLeft, Star, Shield, Flame, Home, Users, Wheat,
  Hammer, ChevronRight, Sparkles, RefreshCw, Check, Crown,
  Wallet, CreditCard, Droplet, Eye, Beer, Church
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Icon mapping for structures
const STRUCTURE_ICONS = {
  flame: Flame,
  home: Home,
  droplet: Droplet,
  fence: Shield,
  'door-open': Building2,
  brick: Building2,
  shield: Shield,
  eye: Eye,
  'shield-check': Shield,
  wheat: Wheat,
  hammer: Hammer,
  anvil: Hammer,
  users: Users,
  beer: Beer,
  church: Church
};

const StorePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [presets, setPresets] = useState([]);
  const [subscriptions, setSubscriptions] = useState({});
  const [structures, setStructures] = useState({});
  const [structureCategories, setStructureCategories] = useState({});
  const [storeStatus, setStoreStatus] = useState(null);
  const [userBalance, setUserBalance] = useState(0);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [customAmount, setCustomAmount] = useState('');
  const [purchaseLoading, setPurchaseLoading] = useState(null);
  
  // Load store data
  useEffect(() => {
    loadStoreData();
    
    // Check for return from payment
    const status = searchParams.get('status');
    if (status === 'cancelled') {
      toast.info('Purchase cancelled');
      navigate('/store', { replace: true });
    }
  }, [searchParams, navigate]);
  
  const loadStoreData = async () => {
    setLoading(true);
    try {
      const [statusRes, presetsRes, subsRes, structRes, balanceRes, subStatusRes] = await Promise.all([
        axios.get(`${API}/store/status`),
        axios.get(`${API}/store/presets`),
        axios.get(`${API}/store/compute-subscriptions`),
        axios.get(`${API}/store/structures`),
        axios.get(`${API}/payments/balance/${userId}`).catch(() => ({ data: { balance: { available_ve: 0 } } })),
        axios.get(`${API}/store/user/${userId}/subscription`).catch(() => ({ data: { active: false } }))
      ]);
      
      setStoreStatus(statusRes.data);
      setPresets(presetsRes.data.presets || []);
      setSubscriptions(subsRes.data.subscriptions || {});
      setStructures(structRes.data.structures || {});
      setStructureCategories(structRes.data.by_category || {});
      setUserBalance(balanceRes.data.balance?.available_ve || 0);
      setCurrentSubscription(subStatusRes.data);
    } catch (error) {
      console.error('Failed to load store:', error);
      toast.error('Failed to load store data');
    }
    setLoading(false);
  };
  
  // Purchase preset package
  const purchasePreset = async (presetId) => {
    if (!userId) {
      toast.error('Please login first');
      navigate('/auth');
      return;
    }
    
    setPurchaseLoading(presetId);
    try {
      const res = await axios.post(`${API}/store/purchase-preset`, {
        user_id: userId,
        preset_id: presetId,
        origin_url: window.location.origin
      });
      
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Purchase failed');
      setPurchaseLoading(null);
    }
  };
  
  // Convert custom amount
  const convertCurrency = async () => {
    const amount = parseFloat(customAmount);
    if (isNaN(amount) || amount < 1) {
      toast.error('Minimum purchase is $1.00');
      return;
    }
    
    setPurchaseLoading('custom');
    try {
      const res = await axios.post(`${API}/store/convert-currency`, {
        user_id: userId,
        amount_usd: amount,
        origin_url: window.location.origin
      });
      
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Conversion failed');
      setPurchaseLoading(null);
    }
  };
  
  // Subscribe to compute
  const subscribeCompute = async (tier) => {
    if (!userId) {
      toast.error('Please login first');
      navigate('/auth');
      return;
    }
    
    setPurchaseLoading(`sub-${tier}`);
    try {
      const res = await axios.post(`${API}/store/subscribe-compute`, {
        user_id: userId,
        subscription_tier: tier,
        origin_url: window.location.origin
      });
      
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Subscription failed');
      setPurchaseLoading(null);
    }
  };
  
  // Purchase structure
  const purchaseStructure = async (structureId, paymentMethod) => {
    if (!userId) {
      toast.error('Please login first');
      navigate('/auth');
      return;
    }
    
    setPurchaseLoading(`struct-${structureId}`);
    try {
      const res = await axios.post(`${API}/store/purchase-structure`, {
        user_id: userId,
        structure_id: structureId,
        payment_method: paymentMethod,
        origin_url: window.location.origin
      });
      
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      } else if (res.data.success) {
        toast.success(res.data.message);
        loadStoreData(); // Refresh balance
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Purchase failed');
    }
    setPurchaseLoading(null);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Store...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="bg-gradient-to-b from-gold/10 to-transparent border-b border-gold/20 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn">
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="font-cinzel text-3xl text-gold flex items-center gap-3">
                  <Store className="w-8 h-8" />
                  Village Store
                </h1>
                <p className="text-muted-foreground mt-1">Currency, Compute Power & Civilization Essentials</p>
              </div>
            </div>
            
            {/* Balance Display */}
            <Card className="bg-surface/50 border-gold/30 px-6 py-3">
              <div className="flex items-center gap-3">
                <Wallet className="w-5 h-5 text-gold" />
                <div>
                  <p className="text-xs text-muted-foreground">Your Balance</p>
                  <p className="font-mono text-xl text-gold">VE${userBalance.toFixed(2)}</p>
                </div>
              </div>
            </Card>
          </div>
          
          {/* Status Banner */}
          {storeStatus?.enabled && (
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <Check className="w-4 h-4" />
              <span>Store is open • Secure payments via Stripe</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Main Content */}
      <div className="max-w-6xl mx-auto p-6">
        <Tabs defaultValue="currency" className="space-y-6">
          <TabsList className="bg-surface/50 border border-border/30">
            <TabsTrigger value="currency" className="data-[state=active]:bg-gold/20 data-[state=active]:text-gold" data-testid="tab-currency">
              <DollarSign className="w-4 h-4 mr-2" />
              Currency
            </TabsTrigger>
            <TabsTrigger value="compute" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400" data-testid="tab-compute">
              <Cpu className="w-4 h-4 mr-2" />
              Compute Power
            </TabsTrigger>
            <TabsTrigger value="structures" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400" data-testid="tab-structures">
              <Building2 className="w-4 h-4 mr-2" />
              Structures
            </TabsTrigger>
          </TabsList>
          
          {/* Currency Tab */}
          <TabsContent value="currency" className="space-y-8">
            <div>
              <h2 className="font-cinzel text-2xl text-gold mb-2">Buy VE$ Currency</h2>
              <p className="text-muted-foreground">1 USD = 1 VE$ • Higher packages include bonus VE$</p>
            </div>
            
            {/* Preset Packages */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {presets.map((preset) => (
                <Card 
                  key={preset.id}
                  className={`relative p-6 bg-surface/50 border transition-all hover:border-gold/50 ${
                    preset.popular ? 'border-gold/50 ring-2 ring-gold/20' : 'border-border/30'
                  }`}
                  data-testid={`preset-${preset.id}`}
                >
                  {preset.popular && (
                    <Badge className="absolute -top-2 -right-2 bg-gold text-black">
                      <Star className="w-3 h-3 mr-1" /> Popular
                    </Badge>
                  )}
                  
                  <div className="text-center mb-4">
                    <Package className="w-10 h-10 text-gold mx-auto mb-2" />
                    <h3 className="font-cinzel text-lg">{preset.label}</h3>
                  </div>
                  
                  <div className="text-center mb-4">
                    <p className="text-3xl font-bold text-gold">VE${preset.ve_received.toFixed(2)}</p>
                    <p className="text-sm text-muted-foreground">for ${preset.amount_usd.toFixed(2)} USD</p>
                    {preset.bonus > 0 && (
                      <Badge variant="outline" className="mt-2 text-green-400 border-green-400/30">
                        +{preset.bonus}% Bonus
                      </Badge>
                    )}
                  </div>
                  
                  <Button 
                    onClick={() => purchasePreset(preset.id)}
                    disabled={purchaseLoading === preset.id}
                    className="w-full bg-gold text-black hover:bg-gold-light"
                    data-testid={`buy-${preset.id}`}
                  >
                    {purchaseLoading === preset.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4 mr-2" />
                        Buy Now
                      </>
                    )}
                  </Button>
                </Card>
              ))}
            </div>
            
            {/* Custom Amount */}
            <Card className="p-6 bg-surface/30 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Custom Amount
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Enter any amount (minimum $1.00). You'll receive the exact amount in VE$.
              </p>
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input 
                    type="number"
                    min="1"
                    step="0.01"
                    placeholder="Enter amount..."
                    value={customAmount}
                    onChange={(e) => setCustomAmount(e.target.value)}
                    className="pl-10 bg-obsidian border-border/50"
                    data-testid="custom-amount-input"
                  />
                </div>
                <Button 
                  onClick={convertCurrency}
                  disabled={purchaseLoading === 'custom' || !customAmount}
                  className="bg-gold text-black hover:bg-gold-light px-8"
                  data-testid="convert-btn"
                >
                  {purchaseLoading === 'custom' ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    'Convert to VE$'
                  )}
                </Button>
              </div>
              {customAmount && parseFloat(customAmount) >= 1 && (
                <p className="mt-2 text-sm text-green-400">
                  You'll receive: VE${parseFloat(customAmount).toFixed(2)}
                </p>
              )}
            </Card>
          </TabsContent>
          
          {/* Compute Power Tab */}
          <TabsContent value="compute" className="space-y-8">
            <div>
              <h2 className="font-cinzel text-2xl text-purple-400 mb-2">Compute Power Subscriptions</h2>
              <p className="text-muted-foreground">Power scales exponentially • More compute = more AI programs running</p>
            </div>
            
            {/* Current Subscription */}
            {currentSubscription?.active && (
              <Card className="p-6 bg-purple-500/10 border-purple-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <Crown className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Current Subscription</p>
                      <p className="text-xl font-cinzel text-purple-400">{currentSubscription.tier_name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-mono text-purple-400">{currentSubscription.compute_units}</p>
                    <p className="text-sm text-muted-foreground">compute units/month</p>
                  </div>
                </div>
              </Card>
            )}
            
            {/* Subscription Tiers */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(subscriptions).map(([tierId, sub]) => {
                const isActive = currentSubscription?.tier === tierId;
                return (
                  <Card 
                    key={tierId}
                    className={`p-6 bg-surface/50 border transition-all hover:border-purple-500/50 ${
                      isActive ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-border/30'
                    }`}
                    data-testid={`sub-${tierId}`}
                  >
                    {isActive && (
                      <Badge className="mb-2 bg-purple-500 text-white">Current Plan</Badge>
                    )}
                    
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <Zap className="w-5 h-5 text-purple-400" />
                      </div>
                      <div>
                        <h3 className="font-cinzel text-lg">{sub.name}</h3>
                        <p className="text-sm text-muted-foreground">Tier {sub.tier}</p>
                      </div>
                    </div>
                    
                    <p className="text-sm text-muted-foreground mb-4">{sub.description}</p>
                    
                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Compute Units</span>
                        <span className="font-mono text-purple-400">{sub.compute_units.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">AI Program Slots</span>
                        <span className="font-mono text-purple-400">{sub.ai_program_slots}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Power Multiplier</span>
                        <span className="font-mono text-green-400">{sub.multiplier}x</span>
                      </div>
                    </div>
                    
                    <div className="text-center mb-4">
                      <p className="text-2xl font-bold">${sub.monthly_usd.toFixed(2)}</p>
                      <p className="text-xs text-muted-foreground">per month</p>
                    </div>
                    
                    <Button 
                      onClick={() => subscribeCompute(tierId)}
                      disabled={isActive || purchaseLoading === `sub-${tierId}`}
                      className="w-full bg-purple-500 hover:bg-purple-600 text-white"
                      data-testid={`subscribe-${tierId}`}
                    >
                      {purchaseLoading === `sub-${tierId}` ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : isActive ? (
                        'Active'
                      ) : (
                        <>
                          Subscribe
                          <ChevronRight className="w-4 h-4 ml-1" />
                        </>
                      )}
                    </Button>
                  </Card>
                );
              })}
            </div>
          </TabsContent>
          
          {/* Structures Tab */}
          <TabsContent value="structures" className="space-y-8">
            <div>
              <h2 className="font-cinzel text-2xl text-amber-400 mb-2">Civilization Structures</h2>
              <p className="text-muted-foreground">
                Essential buildings for starting and maintaining your settlement. 
                At small civilization sizes, guards defend gates rather than patrol streets.
              </p>
            </div>
            
            <ScrollArea className="h-[600px]">
              {Object.entries(structureCategories).map(([category, categoryStructures]) => (
                <div key={category} className="mb-8">
                  <h3 className="font-cinzel text-xl text-amber-400 capitalize mb-4 flex items-center gap-2">
                    {category === 'essential' && <Home className="w-5 h-5" />}
                    {category === 'defense' && <Shield className="w-5 h-5" />}
                    {category === 'production' && <Hammer className="w-5 h-5" />}
                    {category === 'community' && <Users className="w-5 h-5" />}
                    {category} Structures
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {categoryStructures.map((structure) => {
                      const IconComponent = STRUCTURE_ICONS[structure.icon] || Building2;
                      const canAffordVE = userBalance >= structure.cost_ve;
                      
                      return (
                        <Card 
                          key={structure.id}
                          className="p-5 bg-surface/50 border-border/30 hover:border-amber-500/30 transition-all"
                          data-testid={`structure-${structure.id}`}
                        >
                          <div className="flex items-start gap-4">
                            <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                              <IconComponent className="w-6 h-6 text-amber-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-cinzel text-lg truncate">{structure.name}</h4>
                              <p className="text-sm text-muted-foreground line-clamp-2">{structure.description}</p>
                            </div>
                          </div>
                          
                          {/* Stats */}
                          <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                            {structure.defense > 0 && (
                              <div className="flex items-center gap-1">
                                <Shield className="w-3 h-3 text-blue-400" />
                                <span className="text-muted-foreground">Defense:</span>
                                <span className="text-blue-400">{structure.defense}</span>
                              </div>
                            )}
                            {structure.capacity > 0 && (
                              <div className="flex items-center gap-1">
                                <Users className="w-3 h-3 text-green-400" />
                                <span className="text-muted-foreground">Capacity:</span>
                                <span className="text-green-400">{structure.capacity}</span>
                              </div>
                            )}
                          </div>
                          
                          {/* Purchase Options */}
                          <div className="mt-4 flex gap-2">
                            <Button
                              onClick={() => purchaseStructure(structure.id, 've')}
                              disabled={!canAffordVE || purchaseLoading === `struct-${structure.id}`}
                              size="sm"
                              className={`flex-1 ${canAffordVE ? 'bg-gold text-black hover:bg-gold-light' : 'bg-gray-600'}`}
                              data-testid={`buy-ve-${structure.id}`}
                            >
                              {purchaseLoading === `struct-${structure.id}` ? (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              ) : (
                                <>VE${structure.cost_ve}</>
                              )}
                            </Button>
                            <Button
                              onClick={() => purchaseStructure(structure.id, 'usd')}
                              disabled={purchaseLoading === `struct-${structure.id}`}
                              size="sm"
                              variant="outline"
                              className="flex-1 border-border/50"
                              data-testid={`buy-usd-${structure.id}`}
                            >
                              <CreditCard className="w-3 h-3 mr-1" />
                              ${structure.cost_usd}
                            </Button>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              ))}
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default StorePage;
