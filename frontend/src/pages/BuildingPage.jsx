import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, Hammer, Package, Lock, Unlock, Star,
  Building2, Loader2, CheckCircle, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_COLORS = {
  basic: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  intermediate: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  advanced: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  master: 'bg-gold/20 text-gold border-gold/30',
};

const CATEGORY_ICONS = {
  decoration: '🔥',
  utility: '📜',
  furniture: '🪑',
  structure: '🧱',
  storage: '📦',
  building: '🏠',
  fortification: '🏰',
};

const BuildingPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [inventory, setInventory] = useState(null);
  const [schematics, setSchematics] = useState({ available: {}, locked: {} });
  const [buildings, setBuildings] = useState([]);
  const [contributionStatus, setContributionStatus] = useState(null);
  const [selectedSchematic, setSelectedSchematic] = useState(null);
  const [isBuilding, setIsBuilding] = useState(false);

  const userId = localStorage.getItem('userId');
  const currentLocation = localStorage.getItem('currentLocation') || 'village_square';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    if (!userId) {
      navigate('/auth');
      return;
    }

    try {
      const [invRes, schematicRes, buildingsRes, contribRes] = await Promise.all([
        axios.get(`${API}/inventory/${userId}`),
        axios.get(`${API}/schematics/available/${userId}`),
        axios.get(`${API}/buildings/global`),
        axios.get(`${API}/contribution/${userId}`)
      ]);

      setInventory(invRes.data);
      setSchematics(schematicRes.data);
      setBuildings(buildingsRes.data);
      setContributionStatus(contribRes.data);
    } catch (error) {
      console.error('Failed to load:', error);
      toast.error('Failed to load building data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBuild = async (schematicId) => {
    setIsBuilding(true);
    try {
      const response = await axios.post(`${API}/build`, {
        schematic_id: schematicId,
        user_id: userId,
        location_id: currentLocation,
        position_x: 50 + Math.random() * 30 - 15,
        position_y: 50 + Math.random() * 30 - 15
      });

      toast.success(`Built ${schematics.available[schematicId]?.name}! +${response.data.contribution_gained} contribution`);
      loadData();
      setSelectedSchematic(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to build');
    } finally {
      setIsBuilding(false);
    }
  };

  const canBuild = (schematic) => {
    if (!inventory) return false;
    for (const [mat, required] of Object.entries(schematic.materials)) {
      if ((inventory.materials[mat]?.amount || 0) < required) return false;
    }
    return true;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back</span>
          </button>
          <h1 className="font-cinzel text-lg text-gold tracking-wider flex items-center gap-2">
            <Hammer className="w-5 h-5" />
            Building Workshop
          </h1>
          <div className="flex items-center gap-2">
            <Badge className="bg-gold/20 text-gold rounded-sm font-mono">
              {contributionStatus?.contribution_points || 0} CP
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Contribution Progress */}
          <Card className="bg-surface/80 border-border/50 rounded-sm mb-8">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-cinzel text-lg text-foreground">Contribution Progress</h3>
                  <p className="font-manrope text-sm text-muted-foreground">
                    Build more to unlock advanced schematics
                  </p>
                </div>
                <div className="text-right">
                  <div className="font-mono text-2xl text-gold">{contributionStatus?.schematics_unlocked || 0}</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    / {contributionStatus?.total_schematics} schematics
                  </div>
                </div>
              </div>
              <Progress 
                value={(contributionStatus?.schematics_unlocked / contributionStatus?.total_schematics) * 100 || 0}
                className="h-2 bg-obsidian"
              />
              {contributionStatus?.next_unlock && (
                <p className="font-manrope text-xs text-muted-foreground mt-2">
                  Next unlock: <span className="text-gold">{contributionStatus.next_unlock}</span> 
                  ({contributionStatus.contribution_to_next} CP needed)
                </p>
              )}
            </CardContent>
          </Card>

          <Tabs defaultValue="inventory" className="w-full">
            <TabsList className="grid w-full grid-cols-3 bg-surface/50 rounded-sm mb-6">
              <TabsTrigger value="inventory" className="font-cinzel rounded-sm">
                <Package className="w-4 h-4 mr-2" />
                Materials
              </TabsTrigger>
              <TabsTrigger value="schematics" className="font-cinzel rounded-sm">
                <Hammer className="w-4 h-4 mr-2" />
                Schematics
              </TabsTrigger>
              <TabsTrigger value="world" className="font-cinzel rounded-sm">
                <Building2 className="w-4 h-4 mr-2" />
                World
              </TabsTrigger>
            </TabsList>

            {/* Materials Tab */}
            <TabsContent value="inventory">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {inventory?.materials && Object.entries(inventory.materials).map(([matId, mat]) => (
                  <Card key={matId} className="bg-surface/80 border-border/50 rounded-sm">
                    <CardContent className="p-4 text-center">
                      <div 
                        className="w-12 h-12 mx-auto rounded-sm mb-3"
                        style={{ backgroundColor: mat.color + '40', border: `2px solid ${mat.color}` }}
                      />
                      <h4 className="font-cinzel text-sm text-foreground">{mat.name}</h4>
                      <div className="font-mono text-2xl text-gold mt-2">{mat.amount}</div>
                      <div className="flex items-center justify-center gap-2 mt-2">
                        <Badge className="text-xs bg-obsidian/50 rounded-sm">
                          STR {mat.strength}
                        </Badge>
                        <Badge className="text-xs bg-obsidian/50 rounded-sm">
                          DUR {mat.durability}
                        </Badge>
                      </div>
                      <p className="font-manrope text-xs text-muted-foreground mt-2 capitalize">
                        {mat.rarity}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Schematics Tab */}
            <TabsContent value="schematics">
              <div className="space-y-6">
                {/* Available */}
                <div>
                  <h3 className="font-cinzel text-lg text-foreground mb-4 flex items-center gap-2">
                    <Unlock className="w-5 h-5 text-emerald-400" />
                    Available Schematics
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(schematics.available).map(([id, schematic]) => (
                      <Card 
                        key={id} 
                        className={`bg-surface/80 border-border/50 rounded-sm cursor-pointer transition-all ${
                          selectedSchematic === id ? 'border-gold' : 'hover:border-gold/50'
                        }`}
                        onClick={() => setSelectedSchematic(id)}
                      >
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="font-cinzel text-base text-foreground flex items-center gap-2">
                              <span>{CATEGORY_ICONS[schematic.category] || '🔨'}</span>
                              {schematic.name}
                            </CardTitle>
                            <Badge className={`${TIER_COLORS[schematic.tier]} rounded-sm text-xs`}>
                              {schematic.tier}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="font-manrope text-xs text-muted-foreground mb-3">
                            {schematic.description}
                          </p>
                          <div className="flex flex-wrap gap-1 mb-3">
                            {Object.entries(schematic.materials).map(([mat, amount]) => (
                              <Badge 
                                key={mat}
                                className={`text-xs rounded-sm ${
                                  (inventory?.materials[mat]?.amount || 0) >= amount
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-red-500/20 text-red-400'
                                }`}
                              >
                                {mat}: {amount}
                              </Badge>
                            ))}
                          </div>
                          {selectedSchematic === id && (
                            <Button
                              onClick={(e) => { e.stopPropagation(); handleBuild(id); }}
                              disabled={!canBuild(schematic) || isBuilding}
                              className="w-full bg-gold text-black hover:bg-gold-light rounded-sm"
                            >
                              {isBuilding ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : canBuild(schematic) ? (
                                <>
                                  <Hammer className="w-4 h-4 mr-2" />
                                  Build
                                </>
                              ) : (
                                'Insufficient Materials'
                              )}
                            </Button>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Locked */}
                <div>
                  <h3 className="font-cinzel text-lg text-foreground mb-4 flex items-center gap-2">
                    <Lock className="w-5 h-5 text-muted-foreground" />
                    Locked Schematics
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 opacity-60">
                    {Object.entries(schematics.locked).map(([id, schematic]) => (
                      <Card key={id} className="bg-surface/50 border-border/30 rounded-sm">
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="font-cinzel text-base text-muted-foreground">
                              {schematic.name}
                            </CardTitle>
                            <Badge className="bg-muted text-muted-foreground rounded-sm text-xs">
                              {schematic.contribution_required} CP
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="font-manrope text-xs text-muted-foreground">
                            {schematic.description}
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* World Buildings Tab */}
            <TabsContent value="world">
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <div className="font-mono text-4xl text-gold mb-2">{buildings.total || 0}</div>
                  <p className="font-manrope text-muted-foreground">Structures built in The Echoes</p>
                </div>
                
                {buildings.by_location && Object.entries(buildings.by_location).map(([location, locationBuildings]) => (
                  <Card key={location} className="bg-surface/80 border-border/50 rounded-sm">
                    <CardHeader>
                      <CardTitle className="font-cinzel text-lg text-foreground capitalize">
                        {location.replace(/_/g, ' ')}
                        <Badge className="ml-2 bg-gold/20 text-gold rounded-sm">
                          {locationBuildings.length} structures
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {locationBuildings.slice(0, 8).map((building) => (
                          <div 
                            key={building.id}
                            className="p-3 bg-obsidian/50 rounded-sm text-center"
                          >
                            <div className="font-cinzel text-sm text-foreground">
                              {building.schematic?.name || building.schematic_id}
                            </div>
                            <div className="font-mono text-xs text-muted-foreground mt-1">
                              by {building.builder_name}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {(!buildings.by_location || Object.keys(buildings.by_location).length === 0) && (
                  <Card className="bg-surface/80 border-border/50 rounded-sm">
                    <CardContent className="p-12 text-center">
                      <Building2 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                      <h3 className="font-cinzel text-lg text-foreground mb-2">No Structures Yet</h3>
                      <p className="font-manrope text-sm text-muted-foreground">
                        Be the first to build in The Echoes!
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
};

export default BuildingPage;
