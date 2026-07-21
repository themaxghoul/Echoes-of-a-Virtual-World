import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, Swords, Sparkles, Hammer, MessageCircle, Compass,
  Lock, Unlock, Check, Star, Zap, Clock, Shield, Crown,
  RefreshCw, ChevronRight, Award, Target
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Tree icons and colors
const TREE_CONFIG = {
  combat: { icon: Swords, color: '#EF4444', bgClass: 'from-red-500/20 to-red-500/5', borderClass: 'border-red-500/30' },
  magic: { icon: Sparkles, color: '#8B5CF6', bgClass: 'from-purple-500/20 to-purple-500/5', borderClass: 'border-purple-500/30' },
  crafting: { icon: Hammer, color: '#F59E0B', bgClass: 'from-amber-500/20 to-amber-500/5', borderClass: 'border-amber-500/30' },
  social: { icon: MessageCircle, color: '#EC4899', bgClass: 'from-pink-500/20 to-pink-500/5', borderClass: 'border-pink-500/30' },
  survival: { icon: Compass, color: '#22C55E', bgClass: 'from-green-500/20 to-green-500/5', borderClass: 'border-green-500/30' },
};

const SkillTrees = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [skillTrees, setSkillTrees] = useState({});
  const [playerData, setPlayerData] = useState(null);
  const [titlePassives, setTitlePassives] = useState({});
  const [activeTree, setActiveTree] = useState('combat');
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [unlocking, setUnlocking] = useState(false);

  // Load skill data
  const loadData = useCallback(async () => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    
    setLoading(true);
    try {
      const [treesRes, playerRes, titlesRes] = await Promise.all([
        axios.get(`${API}/skill-trees/trees`),
        axios.get(`${API}/skill-trees/player/${userId}`),
        axios.get(`${API}/skill-trees/title-passives`)
      ]);
      
      setSkillTrees(treesRes.data.skill_trees || {});
      setPlayerData(playerRes.data);
      setTitlePassives(titlesRes.data.title_passives || {});
    } catch (error) {
      console.error('Failed to load skill trees:', error);
      toast.error('Failed to load skill data');
    }
    setLoading(false);
  }, [userId, navigate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Unlock skill
  const unlockSkill = async (treeId, skillId) => {
    if (!playerData || playerData.skill_points < 1) {
      toast.error('Not enough skill points!');
      return;
    }
    
    setUnlocking(true);
    try {
      const res = await axios.post(`${API}/skill-trees/unlock?player_id=${userId}`, {
        skill_tree: treeId,
        skill_id: skillId
      });
      
      toast.success(`Unlocked ${res.data.skill_name}!`);
      loadData();
      setSelectedSkill(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unlock skill');
    }
    setUnlocking(false);
  };

  // Check if skill is unlocked
  const isSkillUnlocked = (treeId, skillId) => {
    return playerData?.unlocked_skills?.[treeId]?.includes(skillId) || false;
  };

  // Check if skill can be unlocked
  const canUnlockSkill = (treeId, skill, skillId) => {
    if (isSkillUnlocked(treeId, skillId)) return false;
    if ((playerData?.skill_points || 0) < 1) return false;
    
    // Check requirements
    const requires = skill.requires || [];
    for (const req of requires) {
      if (!isSkillUnlocked(treeId, req)) return false;
    }
    
    return true;
  };

  // Render skill node
  const renderSkillNode = (treeId, skillId, skill, tier) => {
    const unlocked = isSkillUnlocked(treeId, skillId);
    const canUnlock = canUnlockSkill(treeId, skill, skillId);
    const config = TREE_CONFIG[treeId];
    
    return (
      <Card
        key={skillId}
        className={`p-4 cursor-pointer transition-all duration-200 ${
          unlocked 
            ? `bg-gradient-to-br ${config.bgClass} ${config.borderClass} border-2` 
            : canUnlock 
              ? 'bg-surface/80 border-gold/50 border hover:border-gold hover:scale-105' 
              : 'bg-surface/30 border-border/30 opacity-60'
        }`}
        onClick={() => setSelectedSkill({ treeId, skillId, skill, tier, unlocked, canUnlock })}
        data-testid={`skill-${skillId}`}
      >
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            unlocked 
              ? 'bg-black/30' 
              : canUnlock 
                ? 'bg-gold/20' 
                : 'bg-black/20'
          }`}>
            {unlocked ? (
              <Check className="w-5 h-5" style={{ color: config.color }} />
            ) : canUnlock ? (
              <Unlock className="w-5 h-5 text-gold" />
            ) : (
              <Lock className="w-5 h-5 text-muted-foreground" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className={`font-medium truncate ${unlocked ? 'text-foreground' : 'text-muted-foreground'}`}>
                {skill.name}
              </h4>
              <Badge className={`text-xs ${
                skill.type === 'active' 
                  ? 'bg-blue-500/20 text-blue-400' 
                  : 'bg-green-500/20 text-green-400'
              }`}>
                {skill.type}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{skill.description}</p>
          </div>
        </div>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Skill Trees...</p>
        </div>
      </div>
    );
  }

  const currentTree = skillTrees[activeTree];
  const TreeIcon = TREE_CONFIG[activeTree]?.icon || Star;

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
                <Award className="w-6 h-6" />
                Skill Trees
              </h1>
              <p className="text-sm text-muted-foreground">Unlock abilities and passive bonuses</p>
            </div>
          </div>
          
          {/* Skill Points */}
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 bg-gold/10 border border-gold/30 rounded-lg">
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-gold" />
                <span className="font-bold text-gold">{playerData?.skill_points || 0}</span>
                <span className="text-sm text-muted-foreground">Skill Points</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tree Selection Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <Card className="p-4 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4">Skill Trees</h3>
              <div className="space-y-2">
                {Object.entries(skillTrees).map(([treeId, tree]) => {
                  const config = TREE_CONFIG[treeId];
                  const Icon = config?.icon || Star;
                  const unlockedCount = playerData?.unlocked_skills?.[treeId]?.length || 0;
                  const totalCount = Object.values(tree.tiers || {}).reduce((acc, tier) => acc + Object.keys(tier).length, 0);
                  
                  return (
                    <Button
                      key={treeId}
                      variant={activeTree === treeId ? 'default' : 'ghost'}
                      className={`w-full justify-start ${
                        activeTree === treeId 
                          ? `bg-gradient-to-r ${config?.bgClass}` 
                          : ''
                      }`}
                      onClick={() => setActiveTree(treeId)}
                      data-testid={`tree-${treeId}`}
                    >
                      <Icon className="w-5 h-5 mr-3" style={{ color: config?.color }} />
                      <div className="flex-1 text-left">
                        <div>{tree.name}</div>
                        <div className="text-xs text-muted-foreground">{unlockedCount}/{totalCount} unlocked</div>
                      </div>
                    </Button>
                  );
                })}
              </div>
            </Card>

            {/* Title Passives */}
            <Card className="p-4 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Crown className="w-5 h-5" />
                Title Passives
              </h3>
              <ScrollArea className="h-[200px]">
                <div className="space-y-3">
                  {playerData?.title_passives?.length > 0 ? (
                    playerData.title_passives.map((passive, idx) => (
                      <div key={idx} className="p-3 bg-black/30 rounded-lg">
                        <div className="font-medium text-sm">{passive.name}</div>
                        <div className="text-xs text-muted-foreground mt-1">{passive.description}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      <Crown className="w-8 h-8 mx-auto mb-2 opacity-30" />
                      <p>Earn titles to unlock passive bonuses</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </Card>
          </div>

          {/* Main Skill Tree View */}
          <div className="lg:col-span-3">
            {currentTree && (
              <Card className={`p-6 bg-gradient-to-br ${TREE_CONFIG[activeTree]?.bgClass} ${TREE_CONFIG[activeTree]?.borderClass} border`}>
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 rounded-lg bg-black/30 flex items-center justify-center">
                    <TreeIcon className="w-7 h-7" style={{ color: TREE_CONFIG[activeTree]?.color }} />
                  </div>
                  <div>
                    <h2 className="font-cinzel text-xl" style={{ color: TREE_CONFIG[activeTree]?.color }}>
                      {currentTree.name}
                    </h2>
                    <p className="text-sm text-muted-foreground">{currentTree.description}</p>
                  </div>
                </div>

                {/* Tiers */}
                <div className="space-y-8">
                  {Object.entries(currentTree.tiers || {}).map(([tierNum, tierSkills]) => (
                    <div key={tierNum}>
                      <div className="flex items-center gap-2 mb-4">
                        <Badge className="bg-black/30" style={{ color: TREE_CONFIG[activeTree]?.color }}>
                          Tier {tierNum}
                        </Badge>
                        <div className="flex-1 h-px bg-border/30" />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {Object.entries(tierSkills).map(([skillId, skill]) => 
                          renderSkillNode(activeTree, skillId, skill, tierNum)
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Skill Detail Modal */}
      {selectedSkill && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg bg-surface border-border/30">
            <div className="p-6">
              <div className="flex items-start gap-4 mb-6">
                <div 
                  className="w-14 h-14 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${TREE_CONFIG[selectedSkill.treeId]?.color}20` }}
                >
                  {selectedSkill.unlocked ? (
                    <Check className="w-7 h-7" style={{ color: TREE_CONFIG[selectedSkill.treeId]?.color }} />
                  ) : selectedSkill.canUnlock ? (
                    <Unlock className="w-7 h-7 text-gold" />
                  ) : (
                    <Lock className="w-7 h-7 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="font-cinzel text-xl">{selectedSkill.skill.name}</h2>
                    <Badge className={`${
                      selectedSkill.skill.type === 'active' 
                        ? 'bg-blue-500/20 text-blue-400' 
                        : 'bg-green-500/20 text-green-400'
                    }`}>
                      {selectedSkill.skill.type}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground mt-1">{selectedSkill.skill.description}</p>
                </div>
              </div>

              {/* Skill Details */}
              <div className="space-y-4 mb-6">
                {selectedSkill.skill.type === 'active' && (
                  <>
                    {selectedSkill.skill.cooldown_seconds && (
                      <div className="flex items-center gap-2 text-sm">
                        <Clock className="w-4 h-4 text-blue-400" />
                        <span className="text-muted-foreground">Cooldown:</span>
                        <span>{selectedSkill.skill.cooldown_seconds}s</span>
                      </div>
                    )}
                    {selectedSkill.skill.resource_cost && (
                      <div className="flex items-center gap-2 text-sm">
                        <Zap className="w-4 h-4 text-yellow-400" />
                        <span className="text-muted-foreground">Cost:</span>
                        <span>
                          {Object.entries(selectedSkill.skill.resource_cost).map(([res, amt]) => 
                            `${amt} ${res}`
                          ).join(', ')}
                        </span>
                      </div>
                    )}
                  </>
                )}

                {/* Effects */}
                {selectedSkill.skill.effects && (
                  <div className="p-3 bg-black/30 rounded-lg">
                    <div className="text-sm font-medium mb-2">Effects:</div>
                    <div className="space-y-1">
                      {Object.entries(selectedSkill.skill.effects).map(([effect, value]) => (
                        <div key={effect} className="flex justify-between text-sm">
                          <span className="text-muted-foreground capitalize">{effect.replace(/_/g, ' ')}</span>
                          <span className="text-gold">
                            {typeof value === 'number' && value < 1 && value > 0 
                              ? `${(value * 100).toFixed(0)}%` 
                              : typeof value === 'boolean'
                                ? (value ? 'Yes' : 'No')
                                : value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Requirements */}
                {selectedSkill.skill.requires && selectedSkill.skill.requires.length > 0 && (
                  <div className="p-3 bg-black/30 rounded-lg">
                    <div className="text-sm font-medium mb-2">Requires:</div>
                    <div className="flex flex-wrap gap-2">
                      {selectedSkill.skill.requires.map(req => {
                        const reqUnlocked = isSkillUnlocked(selectedSkill.treeId, req);
                        return (
                          <Badge 
                            key={req}
                            className={reqUnlocked ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}
                          >
                            {reqUnlocked ? <Check className="w-3 h-3 mr-1" /> : <Lock className="w-3 h-3 mr-1" />}
                            {req.replace(/_/g, ' ')}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}

                {selectedSkill.skill.unlocks_at_skill_level && (
                  <div className="flex items-center gap-2 text-sm">
                    <Target className="w-4 h-4 text-purple-400" />
                    <span className="text-muted-foreground">Unlocks at level:</span>
                    <span>{selectedSkill.skill.unlocks_at_skill_level}</span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                {selectedSkill.unlocked ? (
                  <Button disabled className="flex-1 bg-green-600">
                    <Check className="w-4 h-4 mr-2" />
                    Already Unlocked
                  </Button>
                ) : selectedSkill.canUnlock ? (
                  <Button 
                    onClick={() => unlockSkill(selectedSkill.treeId, selectedSkill.skillId)}
                    disabled={unlocking}
                    className="flex-1 bg-gold text-black hover:bg-gold-light"
                    data-testid="unlock-skill-btn"
                  >
                    {unlocking ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Unlock className="w-4 h-4 mr-2" />
                    )}
                    Unlock (1 Point)
                  </Button>
                ) : (
                  <Button disabled className="flex-1">
                    <Lock className="w-4 h-4 mr-2" />
                    Requirements Not Met
                  </Button>
                )}
                <Button 
                  variant="outline" 
                  onClick={() => setSelectedSkill(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SkillTrees;
