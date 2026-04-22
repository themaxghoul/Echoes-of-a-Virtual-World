import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Sword, Wand2, Hammer, Leaf, Users, BookOpen,
  Crown, Star, Award, Zap, Shield, Target,
  Sparkles, ChevronRight, Check, Lock
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory, GameNavigation } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_ICONS = {
  combat: Sword,
  magic: Wand2,
  crafting: Hammer,
  gathering: Leaf,
  social: Users,
  knowledge: BookOpen
};

const CATEGORY_COLORS = {
  combat: '#EF4444',
  magic: '#8B5CF6',
  crafting: '#F59E0B',
  gathering: '#10B981',
  social: '#3B82F6',
  knowledge: '#6366F1'
};

const SkillsPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState(null);
  const [titlesCatalog, setTitlesCatalog] = useState(null);
  const [playerSkills, setPlayerSkills] = useState(null);
  const [playerTitles, setPlayerTitles] = useState(null);
  const [activeCategory, setActiveCategory] = useState('combat');
  
  const userId = localStorage.getItem('userId');

  useEffect(() => {
    pushNavHistory('/skills');
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [catalogRes, titlesRes, skillsRes, playerTitlesRes] = await Promise.all([
        axios.get(`${API}/skill-system/catalog`),
        axios.get(`${API}/skill-system/titles/catalog`),
        axios.get(`${API}/skill-system/entity/player/${userId}`),
        axios.get(`${API}/skill-system/entity/player/${userId}/titles`)
      ]);
      
      setCatalog(catalogRes.data);
      setTitlesCatalog(titlesRes.data);
      setPlayerSkills(skillsRes.data);
      setPlayerTitles(playerTitlesRes.data);
    } catch (error) {
      console.error('Failed to load skills data:', error);
      toast.error('Failed to load skills');
    }
    setLoading(false);
  };

  const setActiveTitle = async (titleId) => {
    try {
      const res = await axios.post(`${API}/skill-system/titles/set-active`, {
        entity_id: userId,
        title_id: titleId
      });
      
      if (res.data.active_title) {
        toast.success(`Title set: ${res.data.title_info.name}`);
        loadData();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to set title');
    }
  };

  const getSkillProgress = (skillId) => {
    const skill = playerSkills?.skills?.[skillId];
    if (!skill) return { level: 0, xp: 0, progress: 0 };
    
    const xp = skill.xp || 0;
    const level = skill.level || 1;
    // Approximate progress to next level
    const xpNeeded = Math.pow(1.15, level - 1) * 100;
    const progress = Math.min(100, (xp % xpNeeded) / xpNeeded * 100);
    
    return { level, xp, progress };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="w-16 h-16 mx-auto text-gold animate-pulse mb-4" />
          <p className="font-cinzel text-gold">Loading Skills...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian flex flex-col">
      <div className="fixed inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-obsidian to-blue-900/20" />
      </div>

      <GameNavigation 
        title="Skills & Titles" 
        showBack={true} 
        showHome={true}
      />

      <main className="relative z-10 flex-1 p-4 sm:p-6 overflow-y-auto">
        <div className="max-w-5xl mx-auto space-y-6">
          
          {/* Active Title Display */}
          <Card className="bg-gradient-to-r from-gold/10 to-amber-500/10 border-gold/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-full bg-gold/20 border border-gold/50 flex items-center justify-center">
                    <Crown className="w-7 h-7 text-gold" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Active Title</p>
                    <h2 className="font-cinzel text-xl text-gold">
                      {playerTitles?.active_title_info?.name || 'No Title'}
                    </h2>
                    {playerTitles?.stat_boosts && Object.keys(playerTitles.stat_boosts).length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-1">
                        {Object.entries(playerTitles.stat_boosts).map(([stat, value]) => (
                          <Badge key={stat} className="bg-gold/20 text-gold text-xs">
                            +{value} {stat}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">Total Points</p>
                  <p className="font-mono text-2xl text-foreground">
                    {playerSkills?.total_skill_points?.toLocaleString() || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="skills" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-surface/50">
              <TabsTrigger value="skills" className="font-cinzel">
                <Zap className="w-4 h-4 mr-2" />
                Skills
              </TabsTrigger>
              <TabsTrigger value="titles" className="font-cinzel">
                <Crown className="w-4 h-4 mr-2" />
                Titles
              </TabsTrigger>
            </TabsList>

            {/* Skills Tab */}
            <TabsContent value="skills" className="mt-6">
              {/* Category Tabs */}
              <div className="flex flex-wrap gap-2 mb-6">
                {catalog?.categories && Object.entries(catalog.categories).map(([catId, category]) => {
                  const Icon = CATEGORY_ICONS[catId] || BookOpen;
                  const color = CATEGORY_COLORS[catId] || '#888';
                  return (
                    <Button
                      key={catId}
                      variant={activeCategory === catId ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setActiveCategory(catId)}
                      style={{
                        backgroundColor: activeCategory === catId ? color : 'transparent',
                        borderColor: color,
                        color: activeCategory === catId ? 'white' : color
                      }}
                      className="rounded-sm"
                    >
                      <Icon className="w-4 h-4 mr-1" />
                      {category.name}
                    </Button>
                  );
                })}
              </div>

              {/* Skills Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {catalog?.categories?.[activeCategory]?.skills && 
                  Object.entries(catalog.categories[activeCategory].skills).map(([skillId, skill]) => {
                    const { level, xp, progress } = getSkillProgress(skillId);
                    const color = CATEGORY_COLORS[activeCategory];
                    
                    return (
                      <Card key={skillId} className="bg-surface/80 border-border/50">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <h3 className="font-cinzel text-foreground">{skill.name}</h3>
                              <p className="text-xs text-muted-foreground">{skill.description}</p>
                            </div>
                            <div className="text-right">
                              <span 
                                className="font-mono text-lg font-bold"
                                style={{ color }}
                              >
                                Lv.{level}
                              </span>
                              <p className="text-xs text-muted-foreground">/ {skill.max_level}</p>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs">
                              <span className="text-muted-foreground">XP: {xp}</span>
                              <span className="text-muted-foreground">{Math.round(progress)}%</span>
                            </div>
                            <Progress 
                              value={progress} 
                              className="h-2"
                              style={{ '--progress-color': color }}
                            />
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })
                }
              </div>
            </TabsContent>

            {/* Titles Tab */}
            <TabsContent value="titles" className="mt-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {titlesCatalog?.titles && Object.entries(titlesCatalog.titles).map(([titleId, title]) => {
                  const isUnlocked = playerTitles?.unlocked_titles?.includes(titleId);
                  const isActive = playerTitles?.active_title === titleId;
                  const categoryColor = CATEGORY_COLORS[title.category] || '#888';
                  
                  return (
                    <Card 
                      key={titleId}
                      className={`bg-surface/80 border-border/50 transition-all ${
                        isActive ? 'ring-2 ring-gold' : 
                        isUnlocked ? 'hover:border-gold/30' : 'opacity-60'
                      }`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {isActive ? (
                              <Crown className="w-5 h-5 text-gold" />
                            ) : isUnlocked ? (
                              <Award className="w-5 h-5" style={{ color: categoryColor }} />
                            ) : (
                              <Lock className="w-5 h-5 text-muted-foreground" />
                            )}
                            <div>
                              <h3 className="font-cinzel text-foreground">{title.name}</h3>
                              <Badge 
                                variant="outline" 
                                className="text-xs capitalize"
                                style={{ borderColor: categoryColor, color: categoryColor }}
                              >
                                {title.category}
                              </Badge>
                            </div>
                          </div>
                          {isActive && (
                            <Badge className="bg-gold text-black text-xs">Active</Badge>
                          )}
                        </div>
                        
                        {/* Requirements */}
                        <div className="text-xs text-muted-foreground mb-3">
                          {title.requirement.skill ? (
                            <span>Requires: {title.requirement.skill} Lv.{title.requirement.level}</span>
                          ) : (
                            <span>Requires: {title.requirement.action} x{title.requirement.count}</span>
                          )}
                        </div>
                        
                        {/* Boosts */}
                        <div className="flex flex-wrap gap-1 mb-3">
                          {Object.entries(title.boosts || {}).map(([stat, value]) => (
                            <Badge key={stat} variant="outline" className="text-xs bg-surface">
                              +{value} {stat}
                            </Badge>
                          ))}
                        </div>
                        
                        {isUnlocked && !isActive && (
                          <Button
                            size="sm"
                            className="w-full bg-gold/20 text-gold hover:bg-gold/30"
                            onClick={() => setActiveTitle(titleId)}
                          >
                            Set as Active
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </TabsContent>
          </Tabs>

          {/* Back to Game */}
          <div className="flex justify-center pt-4">
            <Button
              variant="outline"
              onClick={() => navigate('/village')}
              className="border-gold/30 text-gold hover:bg-gold/10"
            >
              Return to Village
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SkillsPage;
