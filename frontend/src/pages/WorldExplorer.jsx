import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ArrowLeft, Compass, Map, ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  Maximize2, Minimize2, Eye, Flag, Home, Mountain, TreePine, Flame,
  Snowflake, Droplets, Sparkles, Skull, MapPin, Navigation, Layers,
  Box, RotateCcw, ZoomIn, ZoomOut, Settings, User
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Biome icons mapping
const BIOME_ICONS = {
  plains: TreePine,
  forest: TreePine,
  shadow_forest: Skull,
  mountains: Mountain,
  volcanic: Flame,
  desert: Sparkles,
  tundra: Snowflake,
  swamp: Droplets,
  crystal_caves: Sparkles,
  ethereal: Sparkles
};

// View modes
const VIEW_MODES = {
  explorer: { name: 'Explorer', icon: Compass, description: 'Compass-based exploration' },
  map_2d: { name: '2D Map', icon: Map, description: 'Top-down world view' },
  isometric: { name: 'Isometric', icon: Box, description: '2.5D building view' },
  first_person: { name: '3D View', icon: Eye, description: 'First-person exploration' }
};

const WorldExplorer = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const userId = localStorage.getItem('userId');
  const characterName = localStorage.getItem('characterName');
  
  const [loading, setLoading] = useState(true);
  const [position, setPosition] = useState({ x: 0, y: 0, z: 70 });
  const [facing, setFacing] = useState('north');
  const [currentTile, setCurrentTile] = useState(null);
  const [surroundings, setSurroundings] = useState([]);
  const [areaData, setAreaData] = useState(null);
  const [discoveries, setDiscoveries] = useState([]);
  const [worldStats, setWorldStats] = useState(null);
  const [viewMode, setViewMode] = useState('explorer');
  const [viewRadius, setViewRadius] = useState(5);
  const [isMoving, setIsMoving] = useState(false);
  const [showMinimap, setShowMinimap] = useState(true);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    pushNavHistory('/world-explorer');
    loadInitialData();
  }, [userId, navigate]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [posRes, statsRes, discRes] = await Promise.all([
        axios.get(`${API}/world/player/${userId}/position`),
        axios.get(`${API}/world/stats`),
        axios.get(`${API}/world/player/${userId}/discoveries?limit=50`)
      ]);
      
      const pos = posRes.data;
      setPosition({ x: pos.x, y: pos.y, z: pos.z });
      setFacing(pos.facing || 'north');
      setCurrentTile(pos.current_tile);
      setWorldStats(statsRes.data);
      setDiscoveries(discRes.data.discoveries || []);
      
      // Load area data
      await loadAreaData(pos.x, pos.y);
    } catch (error) {
      console.error('Failed to load world data:', error);
      toast.error('Failed to load world');
    }
    setLoading(false);
  };

  const loadAreaData = async (x, y) => {
    try {
      const res = await axios.get(`${API}/world/area/${x}/${y}/${viewRadius}`);
      setAreaData(res.data);
    } catch (error) {
      console.error('Failed to load area:', error);
    }
  };

  const explore = async (direction) => {
    if (isMoving) return;
    setIsMoving(true);
    
    try {
      const res = await axios.post(`${API}/world/explore`, {
        user_id: userId,
        direction: direction,
        distance: 1
      });
      
      if (res.data.success) {
        const newPos = res.data.moved.to;
        setPosition(newPos);
        setFacing(direction);
        setCurrentTile(res.data.current_tile);
        setSurroundings(res.data.surroundings || []);
        
        // Reload area data
        await loadAreaData(newPos.x, newPos.y);
        
        // Update discoveries
        setDiscoveries(prev => {
          const exists = prev.find(d => d.x === newPos.x && d.y === newPos.y);
          if (exists) return prev;
          return [{
            x: newPos.x,
            y: newPos.y,
            biome: res.data.current_tile.biome,
            discovered_at: new Date().toISOString()
          }, ...prev.slice(0, 49)];
        });
      } else {
        toast.error(res.data.message || 'Cannot move there');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to explore');
    }
    
    setIsMoving(false);
  };

  const claimLand = async () => {
    try {
      const res = await axios.post(`${API}/world/claim`, {
        user_id: userId,
        x: position.x,
        y: position.y
      });
      
      if (res.data.success) {
        toast.success('Land claimed!');
        setCurrentTile(prev => ({ ...prev, owner_id: userId }));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim land');
    }
  };

  const teleportHome = async () => {
    try {
      await axios.post(`${API}/world/teleport`, {
        user_id: userId,
        x: 0,
        y: 0
      });
      
      setPosition({ x: 0, y: 0, z: 70 });
      await loadAreaData(0, 0);
      toast.success('Teleported to The Hollow Square');
    } catch (error) {
      toast.error('Failed to teleport');
    }
  };

  // Render minimap
  const renderMinimap = useCallback(() => {
    if (!areaData || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const tileSize = 8;
    const size = areaData.size * tileSize;
    
    canvas.width = size;
    canvas.height = size;
    
    // Draw tiles
    areaData.tiles.forEach((row, dy) => {
      row.forEach((tile, dx) => {
        ctx.fillStyle = tile.color_2d || '#333';
        ctx.fillRect(dx * tileSize, dy * tileSize, tileSize, tileSize);
        
        // Draw features
        if (tile.feature) {
          ctx.fillStyle = tile.feature === 'tree' ? '#0a5' : 
                         tile.feature === 'ore_vein' ? '#888' : '#555';
          ctx.beginPath();
          ctx.arc(
            dx * tileSize + tileSize / 2,
            dy * tileSize + tileSize / 2,
            tileSize / 4,
            0, Math.PI * 2
          );
          ctx.fill();
        }
      });
    });
    
    // Draw player position (center)
    const centerX = Math.floor(areaData.size / 2) * tileSize + tileSize / 2;
    const centerY = Math.floor(areaData.size / 2) * tileSize + tileSize / 2;
    
    ctx.fillStyle = '#FFD700';
    ctx.beginPath();
    ctx.arc(centerX, centerY, tileSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw direction indicator
    ctx.strokeStyle = '#FFF';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    const dirAngles = {
      north: -Math.PI / 2,
      south: Math.PI / 2,
      east: 0,
      west: Math.PI,
      northeast: -Math.PI / 4,
      northwest: -3 * Math.PI / 4,
      southeast: Math.PI / 4,
      southwest: 3 * Math.PI / 4
    };
    const angle = dirAngles[facing] || 0;
    ctx.lineTo(
      centerX + Math.cos(angle) * tileSize,
      centerY + Math.sin(angle) * tileSize
    );
    ctx.stroke();
  }, [areaData, facing]);

  useEffect(() => {
    renderMinimap();
  }, [renderMinimap]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      
      switch (e.key.toLowerCase()) {
        case 'w':
        case 'arrowup':
          explore('south');  // Inverted: Up moves south (down on map)
          break;
        case 's':
        case 'arrowdown':
          explore('north');  // Inverted: Down moves north (up on map)
          break;
        case 'a':
        case 'arrowleft':
          explore('west');
          break;
        case 'd':
        case 'arrowright':
          explore('east');
          break;
        case 'q':
          explore('southwest');  // Inverted diagonal
          break;
        case 'e':
          explore('southeast');  // Inverted diagonal
          break;
        case 'z':
          explore('northwest');  // Inverted diagonal
          break;
        case 'c':
          explore('northeast');  // Inverted diagonal
          break;
        default:
          break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMoving]);

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Compass className="w-12 h-12 text-gold animate-spin" />
      </div>
    );
  }

  const BiomeIcon = currentTile ? (BIOME_ICONS[currentTile.biome] || MapPin) : MapPin;

  return (
    <div className="min-h-screen bg-obsidian text-foreground flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 bg-surface/50 border-b border-border/30 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/select-mode')}
            className="rounded-sm"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-cinzel text-lg text-gold flex items-center gap-2">
              <Compass className="w-5 h-5" />
              World Explorer
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              The Echoes • Unified Seed World
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* View Mode Selector */}
          <div className="hidden md:flex items-center gap-1 bg-surface/50 rounded-sm p-1">
            {Object.entries(VIEW_MODES).map(([mode, config]) => {
              const Icon = config.icon;
              return (
                <Button
                  key={mode}
                  variant={viewMode === mode ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode(mode)}
                  className={`px-2 ${viewMode === mode ? 'bg-gold text-black' : ''}`}
                  title={config.description}
                  data-testid={`view-mode-${mode}`}
                >
                  <Icon className="w-4 h-4" />
                </Button>
              );
            })}
          </div>
          
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/settings')}
            className="rounded-sm"
          >
            <User className="w-4 h-4 text-muted-foreground" />
          </Button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Location Info */}
        <aside className="w-64 lg:w-80 bg-surface/30 border-r border-border/30 flex flex-col overflow-hidden hidden md:flex">
          {/* Current Location */}
          <div className="p-4 border-b border-border/30">
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center`}
                   style={{ backgroundColor: currentTile?.color_2d || '#333' }}>
                <BiomeIcon className="w-6 h-6 text-white drop-shadow" />
              </div>
              <div>
                <h3 className="font-cinzel text-lg">{currentTile?.biome_name || 'Unknown'}</h3>
                <p className="text-xs text-muted-foreground font-mono">
                  ({position.x}, {position.y}) • Alt: {position.z}
                </p>
              </div>
            </div>
            
            {/* Danger Level */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-muted-foreground">Danger:</span>
              <div className="flex-1">
                <Progress 
                  value={(currentTile?.danger_level || 0) * 16.67} 
                  className="h-2"
                />
              </div>
              <span className="text-xs font-mono">{currentTile?.danger_level || 0}/6</span>
            </div>
            
            {/* Features */}
            {currentTile?.feature && (
              <Badge variant="outline" className="mr-2">
                {currentTile.feature.replace('_', ' ')}
              </Badge>
            )}
            {currentTile?.resource && (
              <Badge className="bg-gold/20 text-gold">
                {currentTile.resource}
              </Badge>
            )}
          </div>
          
          {/* Quick Actions */}
          <div className="p-4 border-b border-border/30">
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={teleportHome}
                className="text-xs"
                data-testid="teleport-home-btn"
              >
                <Home className="w-3 h-3 mr-1" />
                Home
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={claimLand}
                disabled={currentTile?.owner_id}
                className="text-xs"
                data-testid="claim-land-btn"
              >
                <Flag className="w-3 h-3 mr-1" />
                Claim
              </Button>
            </div>
            {currentTile?.owner_id && (
              <p className="text-xs text-muted-foreground mt-2">
                Owned by: {currentTile.owner_name || 'Unknown'}
              </p>
            )}
          </div>
          
          {/* Discoveries */}
          <div className="flex-1 overflow-hidden">
            <div className="p-4 pb-2">
              <h4 className="font-cinzel text-sm text-gold mb-2">Recent Discoveries</h4>
              <p className="text-xs text-muted-foreground">
                {discoveries.length} tiles explored
              </p>
            </div>
            <ScrollArea className="h-48 px-4">
              <div className="space-y-1">
                {discoveries.slice(0, 20).map((d, i) => (
                  <div
                    key={`${d.x}-${d.y}-${i}`}
                    className="flex items-center justify-between text-xs p-2 bg-obsidian/50 rounded"
                  >
                    <span className="capitalize">{d.biome?.replace('_', ' ')}</span>
                    <span className="text-muted-foreground font-mono">
                      ({d.x}, {d.y})
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col items-center justify-center p-4 relative">
          {/* Minimap Toggle */}
          {showMinimap && (
            <div className="absolute top-4 right-4 z-10">
              <Card className="p-2 bg-surface/80 backdrop-blur-sm border-gold/30">
                <canvas 
                  ref={canvasRef} 
                  className="rounded-sm"
                  style={{ imageRendering: 'pixelated' }}
                />
                <p className="text-xs text-center text-muted-foreground mt-1 font-mono">
                  Radius: {viewRadius}
                </p>
              </Card>
            </div>
          )}

          {/* Explorer View - Compass Navigation */}
          {viewMode === 'explorer' && (
            <div className="flex flex-col items-center">
              {/* Current Biome Display */}
              <Card 
                className="w-64 h-64 mb-8 flex items-center justify-center relative overflow-hidden"
                style={{ backgroundColor: currentTile?.color_2d || '#333' }}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                <div className="relative text-center text-white">
                  <BiomeIcon className="w-16 h-16 mx-auto mb-2 drop-shadow-lg" />
                  <h2 className="font-cinzel text-xl drop-shadow">{currentTile?.biome_name}</h2>
                  {currentTile?.feature && (
                    <p className="text-sm opacity-80 mt-1">{currentTile.feature.replace('_', ' ')}</p>
                  )}
                </div>
              </Card>

              {/* Compass Navigation - Inverted Y-axis (Up button moves South on map) */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('southwest')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-sw"
                >
                  <ChevronUp className="w-4 h-4 -rotate-45" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('south')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-s"
                >
                  <ChevronUp className="w-6 h-6" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('southeast')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-se"
                >
                  <ChevronUp className="w-4 h-4 rotate-45" />
                </Button>
                
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('west')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-w"
                >
                  <ChevronLeft className="w-6 h-6" />
                </Button>
                <div className="w-16 h-16 flex items-center justify-center">
                  <Compass className={`w-8 h-8 text-gold ${isMoving ? 'animate-spin' : ''}`} />
                </div>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('east')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-e"
                >
                  <ChevronRight className="w-6 h-6" />
                </Button>
                
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('northwest')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-nw"
                >
                  <ChevronDown className="w-4 h-4 rotate-45" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('north')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-n"
                >
                  <ChevronDown className="w-6 h-6" />
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => explore('northeast')}
                  disabled={isMoving}
                  className="w-16 h-16"
                  data-testid="explore-ne"
                >
                  <ChevronDown className="w-4 h-4 -rotate-45" />
                </Button>
              </div>

              {/* Keyboard Hints */}
              <p className="text-xs text-muted-foreground text-center">
                Controls inverted: W/↑ moves South • S/↓ moves North
              </p>
            </div>
          )}

          {/* 2D Map View */}
          {viewMode === 'map_2d' && (
            <div className="flex flex-col items-center">
              <Card className="p-4 bg-surface/50">
                <canvas 
                  ref={canvasRef}
                  width={400}
                  height={400}
                  className="rounded-sm"
                  style={{ imageRendering: 'pixelated' }}
                />
              </Card>
              <div className="flex gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setViewRadius(Math.max(3, viewRadius - 2))}
                  disabled={viewRadius <= 3}
                >
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setViewRadius(Math.min(15, viewRadius + 2))}
                  disabled={viewRadius >= 15}
                >
                  <ZoomIn className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Isometric View Placeholder */}
          {viewMode === 'isometric' && (
            <div className="text-center">
              <Box className="w-24 h-24 text-gold mx-auto mb-4" />
              <h2 className="font-cinzel text-2xl mb-2">Isometric Building Mode</h2>
              <p className="text-muted-foreground mb-4">
                Same world coordinates, isometric perspective
              </p>
              <Button onClick={() => navigate('/isometric-builder')}>
                Open Isometric Builder
              </Button>
            </div>
          )}

          {/* First Person View Placeholder */}
          {viewMode === 'first_person' && (
            <div className="text-center">
              <Eye className="w-24 h-24 text-gold mx-auto mb-4" />
              <h2 className="font-cinzel text-2xl mb-2">3D Exploration</h2>
              <p className="text-muted-foreground mb-4">
                First-person view of the same world
              </p>
              <div className="flex gap-2 justify-center">
                <Badge variant="outline">WebGL Preview</Badge>
                <Badge className="bg-slate-blue">Unity Client Coming Soon</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Both clients share the same coordinates and world state
              </p>
            </div>
          )}
        </main>

        {/* Right Sidebar - World Stats */}
        <aside className="w-64 bg-surface/30 border-l border-border/30 p-4 hidden lg:block">
          <h3 className="font-cinzel text-gold mb-4">World Statistics</h3>
          
          {worldStats && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-muted-foreground">World Seed</p>
                <p className="font-mono text-sm">{worldStats.world_seed_id}</p>
              </div>
              
              <div>
                <p className="text-xs text-muted-foreground">Global Discoveries</p>
                <p className="font-mono text-2xl text-gold">
                  {worldStats.total_tile_discoveries?.toLocaleString() || 0}
                </p>
              </div>
              
              <div>
                <p className="text-xs text-muted-foreground">Land Claims</p>
                <p className="font-mono text-lg">
                  {worldStats.total_land_claims?.toLocaleString() || 0}
                </p>
              </div>
              
              <div>
                <p className="text-xs text-muted-foreground">Biomes</p>
                <p className="font-mono">{worldStats.biome_count} types</p>
              </div>
              
              {worldStats.top_explored_biomes && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2">Most Explored</p>
                  <div className="space-y-1">
                    {worldStats.top_explored_biomes.map((b, i) => (
                      <div key={i} className="flex justify-between text-xs">
                        <span className="capitalize">{b.biome?.replace('_', ' ')}</span>
                        <span className="text-muted-foreground">{b.discoveries}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <div className="mt-6 p-3 bg-gold/10 border border-gold/30 rounded-lg">
            <h4 className="font-cinzel text-sm text-gold mb-2">Unified World</h4>
            <p className="text-xs text-muted-foreground">
              This world is generated from a single seed. All views (2D, Isometric, 3D) 
              share the same coordinates and state.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default WorldExplorer;
