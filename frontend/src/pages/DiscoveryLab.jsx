import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { 
  ArrowLeft, Beaker, Sparkles, Plus, X, Play, Lock, Unlock,
  Trophy, AlertTriangle, CheckCircle, Clock, Flame, Zap
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EXPERIMENT_TYPES = {
  material_fusion: {
    name: 'Material Fusion',
    description: 'Combine materials to create new compounds',
    icon: Flame,
    color: 'text-orange-400',
    bgColor: 'bg-orange-400/10'
  },
  spell_synthesis: {
    name: 'Spell Synthesis',
    description: 'Merge spell essences to forge new magic',
    icon: Sparkles,
    color: 'text-purple-400',
    bgColor: 'bg-purple-400/10'
  },
  enchantment_binding: {
    name: 'Enchantment Binding',
    description: 'Bind magical properties to items',
    icon: Zap,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-400/10'
  }
};

const DiscoveryLab = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const displayName = localStorage.getItem('displayName');
  
  const [loading, setLoading] = useState(true);
  const [materials, setMaterials] = useState([]);
  const [components, setComponents] = useState([]);
  const [discoveries, setDiscoveries] = useState([]);
  const [myDiscoveries, setMyDiscoveries] = useState([]);
  
  const [selectedType, setSelectedType] = useState('material_fusion');
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [experimentName, setExperimentName] = useState('');
  const [isExperimenting, setIsExperimenting] = useState(false);
  const [experimentProgress, setExperimentProgress] = useState(0);
  const [experimentResult, setExperimentResult] = useState(null);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [materialsRes, discoveriesRes, myDiscRes] = await Promise.all([
        axios.get(`${API}/materials/list`),
        axios.get(`${API}/discovery/recent`).catch(() => ({ data: { discoveries: [] } })),
        axios.get(`${API}/discovery/user/${userId}`).catch(() => ({ data: { discoveries: [] } }))
      ]);
      
      setMaterials(Object.values(materialsRes.data.materials || {}));
      setDiscoveries(discoveriesRes.data.discoveries || []);
      setMyDiscoveries(myDiscRes.data.discoveries || []);
    } catch (error) {
      console.error('Failed to load lab data:', error);
    }
    setLoading(false);
  };

  const addIngredient = (material) => {
    if (selectedIngredients.length >= 4) {
      toast.error('Maximum 4 ingredients per experiment');
      return;
    }
    if (selectedIngredients.find(i => i.id === material.id)) {
      toast.error('Already added');
      return;
    }
    setSelectedIngredients([...selectedIngredients, material]);
  };

  const removeIngredient = (materialId) => {
    setSelectedIngredients(selectedIngredients.filter(i => i.id !== materialId));
  };

  const runExperiment = async () => {
    if (selectedIngredients.length < 2) {
      toast.error('Select at least 2 ingredients');
      return;
    }
    
    setIsExperimenting(true);
    setExperimentProgress(0);
    setExperimentResult(null);
    
    // Simulate experiment progress
    const progressInterval = setInterval(() => {
      setExperimentProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + Math.random() * 15;
      });
    }, 300);
    
    try {
      const response = await axios.post(`${API}/discovery/experiment`, {
        user_id: userId,
        user_name: displayName,
        experiment_type: selectedType,
        experiment_name: experimentName || `Experiment #${Date.now()}`,
        ingredients: selectedIngredients.map(i => i.id)
      });
      
      clearInterval(progressInterval);
      setExperimentProgress(100);
      
      setTimeout(() => {
        setExperimentResult(response.data);
        setIsExperimenting(false);
        
        if (response.data.is_first_discovery) {
          toast.success('🎉 FIRST DISCOVERY! You are the pioneer!', {
            duration: 5000,
            description: `You discovered: ${response.data.discovery_name}`
          });
        } else if (response.data.success) {
          toast.success('Experiment successful!');
        } else {
          toast.error('Experiment failed. Try different combinations.');
        }
        
        // Refresh discoveries
        loadData();
      }, 500);
      
    } catch (error) {
      clearInterval(progressInterval);
      setExperimentProgress(0);
      setIsExperimenting(false);
      toast.error(error.response?.data?.detail || 'Experiment failed');
    }
  };

  const resetExperiment = () => {
    setSelectedIngredients([]);
    setExperimentName('');
    setExperimentResult(null);
    setExperimentProgress(0);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Beaker className="w-12 h-12 text-gold animate-pulse" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Beaker className="w-6 h-6" />
                Discovery Lab
              </h1>
              <p className="text-sm text-muted-foreground">
                Pioneer new materials, spells, and enchantments
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="border-gold/30 text-gold">
              <Trophy className="w-3 h-3 mr-1" />
              {myDiscoveries.length} Discoveries
            </Badge>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Experiment Type & Ingredients */}
        <div className="lg:col-span-2 space-y-6">
          {/* Experiment Type Selection */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-lg text-gold mb-4">Experiment Type</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(EXPERIMENT_TYPES).map(([key, type]) => {
                const Icon = type.icon;
                return (
                  <Card
                    key={key}
                    className={`p-4 cursor-pointer transition-all ${
                      selectedType === key
                        ? 'border-gold bg-gold/10'
                        : 'border-border/30 hover:border-gold/50'
                    }`}
                    onClick={() => setSelectedType(key)}
                    data-testid={`experiment-type-${key}`}
                  >
                    <div className={`w-10 h-10 rounded-full ${type.bgColor} flex items-center justify-center mb-2`}>
                      <Icon className={`w-5 h-5 ${type.color}`} />
                    </div>
                    <h4 className="font-medium text-sm">{type.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{type.description}</p>
                  </Card>
                );
              })}
            </div>
          </Card>

          {/* Experiment Workbench */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-cinzel text-lg text-gold">Experiment Workbench</h3>
              <Button variant="outline" size="sm" onClick={resetExperiment}>
                <X className="w-4 h-4 mr-1" />
                Clear
              </Button>
            </div>
            
            {/* Experiment Name */}
            <div className="mb-4">
              <Input
                value={experimentName}
                onChange={(e) => setExperimentName(e.target.value)}
                placeholder="Name your experiment (optional)"
                className="bg-obsidian"
                data-testid="experiment-name-input"
              />
            </div>
            
            {/* Selected Ingredients */}
            <div className="grid grid-cols-4 gap-3 mb-4">
              {[0, 1, 2, 3].map(slot => {
                const ingredient = selectedIngredients[slot];
                return (
                  <div
                    key={slot}
                    className={`aspect-square rounded-lg border-2 border-dashed flex items-center justify-center ${
                      ingredient 
                        ? 'border-gold bg-gold/5' 
                        : 'border-border/30 bg-obsidian/50'
                    }`}
                  >
                    {ingredient ? (
                      <div className="text-center p-2 relative w-full h-full flex flex-col items-center justify-center">
                        <button
                          onClick={() => removeIngredient(ingredient.id)}
                          className="absolute top-1 right-1 p-1 hover:bg-red-500/20 rounded"
                        >
                          <X className="w-3 h-3 text-red-400" />
                        </button>
                        <div 
                          className="w-8 h-8 rounded-full mb-1"
                          style={{ backgroundColor: ingredient.color || '#888' }}
                        />
                        <span className="text-xs font-medium truncate w-full">
                          {ingredient.name}
                        </span>
                      </div>
                    ) : (
                      <Plus className="w-6 h-6 text-muted-foreground/30" />
                    )}
                  </div>
                );
              })}
            </div>
            
            {/* First Discovery Warning */}
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg mb-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-400">First Discovery System</p>
                  <p className="text-xs text-muted-foreground">
                    Untested combinations require YOUR presence. You cannot automate first discoveries.
                    If successful, you'll receive permanent credit, bonus VE$, and potential royalties!
                  </p>
                </div>
              </div>
            </div>
            
            {/* Experiment Progress / Result */}
            {isExperimenting && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Beaker className="w-4 h-4 text-gold animate-pulse" />
                  <span className="text-sm">Experimenting...</span>
                </div>
                <Progress value={experimentProgress} className="h-2" />
              </div>
            )}
            
            {experimentResult && (
              <div className={`p-4 rounded-lg mb-4 ${
                experimentResult.success 
                  ? 'bg-green-500/10 border border-green-500/30' 
                  : 'bg-red-500/10 border border-red-500/30'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {experimentResult.success ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : (
                    <X className="w-5 h-5 text-red-400" />
                  )}
                  <span className={`font-medium ${experimentResult.success ? 'text-green-400' : 'text-red-400'}`}>
                    {experimentResult.success ? 'Success!' : 'Failed'}
                  </span>
                  {experimentResult.is_first_discovery && (
                    <Badge className="bg-gold text-black ml-2">
                      <Trophy className="w-3 h-3 mr-1" />
                      FIRST DISCOVERY
                    </Badge>
                  )}
                </div>
                {experimentResult.discovery_name && (
                  <p className="text-sm">
                    Discovered: <span className="text-gold font-medium">{experimentResult.discovery_name}</span>
                  </p>
                )}
                {experimentResult.rewards && (
                  <div className="mt-2 flex gap-2">
                    {experimentResult.rewards.ve_bonus && (
                      <Badge variant="outline">+{experimentResult.rewards.ve_bonus} VE$</Badge>
                    )}
                    {experimentResult.rewards.xp && (
                      <Badge variant="outline">+{experimentResult.rewards.xp} XP</Badge>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* Run Experiment Button */}
            <Button
              onClick={runExperiment}
              disabled={selectedIngredients.length < 2 || isExperimenting}
              className="w-full bg-gold text-black hover:bg-gold-light"
              data-testid="run-experiment-btn"
            >
              {isExperimenting ? (
                <>
                  <Beaker className="w-4 h-4 mr-2 animate-pulse" />
                  Experimenting...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Experiment
                </>
              )}
            </Button>
          </Card>

          {/* Available Materials */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-lg text-gold mb-4">Available Materials</h3>
            <ScrollArea className="h-64">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {materials.map(material => (
                  <Card
                    key={material.id}
                    className="p-3 cursor-pointer border-border/30 hover:border-gold/50 transition-all"
                    onClick={() => addIngredient(material)}
                    data-testid={`material-${material.id}`}
                  >
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-6 h-6 rounded-full"
                        style={{ backgroundColor: material.color || '#888' }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">{material.name}</p>
                        <p className="text-xs text-muted-foreground capitalize">{material.rarity}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </Card>
        </div>

        {/* Right Column - Discoveries */}
        <div className="space-y-6">
          {/* My Discoveries */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5" />
              My Discoveries
            </h3>
            <ScrollArea className="h-48">
              {myDiscoveries.length > 0 ? (
                <div className="space-y-2">
                  {myDiscoveries.map((discovery, i) => (
                    <div key={i} className="p-3 bg-gold/5 border border-gold/20 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{discovery.name}</span>
                        {discovery.is_first && (
                          <Badge className="bg-gold/20 text-gold text-xs">Pioneer</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{discovery.type}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <Beaker className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No discoveries yet</p>
                  <p className="text-xs">Start experimenting!</p>
                </div>
              )}
            </ScrollArea>
          </Card>

          {/* Recent World Discoveries */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Recent World Discoveries
            </h3>
            <ScrollArea className="h-64">
              {discoveries.length > 0 ? (
                <div className="space-y-2">
                  {discoveries.map((discovery, i) => (
                    <div key={i} className="p-3 bg-surface border border-border/30 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{discovery.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {discovery.type}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>by {discovery.discoverer}</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {discovery.time_ago || 'Recently'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No discoveries recorded</p>
                </div>
              )}
            </ScrollArea>
          </Card>

          {/* First Discovery Rules */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5" />
              First Discovery Rules
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center mt-0.5">
                  <Lock className="w-3 h-3 text-red-400" />
                </div>
                <p className="text-muted-foreground">
                  <span className="text-foreground font-medium">Cannot automate</span> first attempts of any combination
                </p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center mt-0.5">
                  <Unlock className="w-3 h-3 text-green-400" />
                </div>
                <p className="text-muted-foreground">
                  <span className="text-foreground font-medium">After discovery</span>, AI Partners can reproduce it
                </p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-gold/20 flex items-center justify-center mt-0.5">
                  <Trophy className="w-3 h-3 text-gold" />
                </div>
                <p className="text-muted-foreground">
                  <span className="text-foreground font-medium">First Discoverer</span> gets permanent credit + royalties
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DiscoveryLab;
