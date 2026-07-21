import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ArrowLeft, Map, MapPin, Users, Building2, Compass,
  RefreshCw, ZoomIn, ZoomOut, Eye, Layers, Navigation,
  Home, Trees, Mountain, Waves, Sparkles, Flame, Moon,
  ChevronRight, User, Bot, Sword
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Terrain colors matching backend
const TERRAIN_COLORS = {
  grass: '#4ADE80',
  forest: '#166534',
  dark_forest: '#1E3A2F',
  water: '#3B82F6',
  shallow_water: '#60A5FA',
  mountain: '#78716C',
  highland: '#A1A1AA',
  cobblestone: '#57534E',
  marble: '#E5E7EB',
  volcanic: '#B91C1C',
  mystical_stone: '#7C3AED',
  forest_clearing: '#6EE7B7',
  ethereal: '#F9A8D4',
  sand: '#FDE68A',
  snow: '#F1F5F9',
};

// Region icons
const REGION_ICONS = {
  village_square: Home,
  oracle_sanctum: Sparkles,
  the_forge: Flame,
  ancient_library: Building2,
  wanderers_rest: Trees,
  shadow_grove: Moon,
  watchtower: Mountain,
  outer_realms: Compass
};

const WorldMapUI = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  
  const userId = localStorage.getItem('userId');
  const worldId = 'main-story-realm';
  
  const [loading, setLoading] = useState(true);
  const [mapConfig, setMapConfig] = useState(null);
  const [worldMap, setWorldMap] = useState(null);
  const [entities, setEntities] = useState([]);
  const [mapStats, setMapStats] = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [regionDetails, setRegionDetails] = useState(null);
  
  // View state
  const [zoom, setZoom] = useState(4);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [showEntities, setShowEntities] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const [hoveredRegion, setHoveredRegion] = useState(null);
  
  // Drag state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [configRes, mapRes, entitiesRes, statsRes] = await Promise.all([
        axios.get(`${API}/world-map/config`),
        axios.get(`${API}/world-map/${worldId}`).catch(() => ({ data: null })),
        axios.get(`${API}/world-map/${worldId}/entities`).catch(() => ({ data: { entities: [] } })),
        axios.get(`${API}/world-map/${worldId}/stats`).catch(() => ({ data: null }))
      ]);
      
      setMapConfig(configRes.data);
      setWorldMap(mapRes.data);
      setEntities(entitiesRes.data.entities || []);
      setMapStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load map data:', error);
      toast.error('Failed to load world map');
    }
    setLoading(false);
  }, [worldId]);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate, loadData]);

  // Load region details when selected
  useEffect(() => {
    if (selectedRegion) {
      loadRegionDetails(selectedRegion);
    }
  }, [selectedRegion]);

  const loadRegionDetails = async (regionId) => {
    try {
      const res = await axios.get(`${API}/world-map/${worldId}/region/${regionId}`);
      setRegionDetails(res.data);
    } catch (error) {
      console.error('Failed to load region details:', error);
    }
  };

  // Draw map on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !mapConfig || loading) return;
    
    const ctx = canvas.getContext('2d');
    const regions = mapConfig.regions || {};
    const cellSize = zoom;
    const mapSize = 100;
    
    canvas.width = mapSize * cellSize;
    canvas.height = mapSize * cellSize;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw base terrain (simplified - just fill with grass)
    ctx.fillStyle = TERRAIN_COLORS.grass;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw terrain from worldMap if available
    if (worldMap?.terrain_grid && zoom >= 2) {
      // Only draw detailed terrain at higher zoom levels
      for (let x = 0; x < mapSize; x++) {
        for (let y = 0; y < mapSize; y++) {
          const terrain = worldMap.terrain_grid[`${x},${y}`];
          if (terrain && terrain !== 'grass') {
            ctx.fillStyle = TERRAIN_COLORS[terrain] || TERRAIN_COLORS.grass;
            ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
          }
        }
      }
    }
    
    // Draw roads
    if (showRoads && worldMap?.roads) {
      ctx.strokeStyle = '#8B7355';
      ctx.lineWidth = Math.max(2, zoom * 0.5);
      ctx.setLineDash([]);
      
      worldMap.roads.forEach(road => {
        const [fx, fy] = road.from_pos;
        const [tx, ty] = road.to_pos;
        
        ctx.beginPath();
        ctx.moveTo((fx + 5) * cellSize, (fy + 5) * cellSize);
        ctx.lineTo((tx + 5) * cellSize, (ty + 5) * cellSize);
        ctx.stroke();
      });
    }
    
    // Draw regions
    Object.entries(regions).forEach(([regionId, region]) => {
      const [rx, ry] = region.position;
      const [rw, rh] = region.size;
      
      const x = rx * cellSize;
      const y = ry * cellSize;
      const w = rw * cellSize;
      const h = rh * cellSize;
      
      // Fill region
      ctx.fillStyle = region.color + '60';
      ctx.fillRect(x, y, w, h);
      
      // Border
      const isHovered = hoveredRegion === regionId;
      const isSelected = selectedRegion === regionId;
      
      ctx.strokeStyle = isSelected ? '#FFD700' : isHovered ? '#FFF' : region.color;
      ctx.lineWidth = isSelected ? 3 : isHovered ? 2 : 1;
      ctx.strokeRect(x, y, w, h);
      
      // Region name (only at sufficient zoom)
      if (zoom >= 3) {
        ctx.fillStyle = '#FFF';
        ctx.font = `bold ${Math.max(10, zoom * 2)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(region.name, x + w/2, y + h/2);
      }
    });
    
    // Draw entities
    if (showEntities && entities.length > 0) {
      entities.forEach(entity => {
        const [ex, ey] = entity.position || [0, 0];
        const px = ex * cellSize;
        const py = ey * cellSize;
        const size = Math.max(4, zoom);
        
        // Entity dot
        ctx.beginPath();
        ctx.arc(px, py, size/2, 0, Math.PI * 2);
        ctx.fillStyle = entity.entity_type === 'player' ? '#3B82F6' : 
                        entity.entity_type === 'npc' ? '#10B981' : '#EF4444';
        ctx.fill();
        
        // Border
        ctx.strokeStyle = '#FFF';
        ctx.lineWidth = 1;
        ctx.stroke();
      });
    }
    
    // Draw grid overlay
    if (showGrid && zoom >= 4) {
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 0.5;
      
      for (let i = 0; i <= mapSize; i += 10) {
        const pos = i * cellSize;
        ctx.beginPath();
        ctx.moveTo(pos, 0);
        ctx.lineTo(pos, canvas.height);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, pos);
        ctx.lineTo(canvas.width, pos);
        ctx.stroke();
      }
    }
  }, [mapConfig, worldMap, entities, zoom, showEntities, showRoads, showGrid, hoveredRegion, selectedRegion, loading]);

  // Handle canvas mouse events
  const handleCanvasMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / zoom);
    const y = Math.floor((e.clientY - rect.top) / zoom);
    
    // Check if hovering over a region
    let foundRegion = null;
    if (mapConfig?.regions) {
      for (const [regionId, region] of Object.entries(mapConfig.regions)) {
        const [rx, ry] = region.position;
        const [rw, rh] = region.size;
        if (x >= rx && x < rx + rw && y >= ry && y < ry + rh) {
          foundRegion = regionId;
          break;
        }
      }
    }
    setHoveredRegion(foundRegion);
    
    // Handle dragging
    if (isDragging) {
      const container = containerRef.current;
      if (container) {
        container.scrollLeft -= e.movementX;
        container.scrollTop -= e.movementY;
      }
    }
  };

  const handleCanvasClick = () => {
    if (hoveredRegion) {
      setSelectedRegion(hoveredRegion);
    }
  };

  const handleCanvasMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
  };

  // Navigate to region
  const navigateToRegion = (regionId) => {
    // Store selected region and navigate to village explorer
    localStorage.setItem('currentLocation', regionId);
    navigate('/village');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading World Map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground flex">
      {/* Main Map Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-surface/50 border-b border-border/30 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={() => navigate('/select-mode')}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                  <Map className="w-6 h-6" />
                  World of The Echoes
                </h1>
                <p className="text-sm text-muted-foreground">8 Regions • Seed: {worldMap?.seed || 42}</p>
              </div>
            </div>
            
            {/* Stats */}
            <div className="flex items-center gap-4">
              <Badge className="bg-blue-500/20 text-blue-400">
                <Users className="w-3 h-3 mr-1" />
                {mapStats?.total_entities || 0} Entities
              </Badge>
              <Badge className="bg-purple-500/20 text-purple-400">
                <Building2 className="w-3 h-3 mr-1" />
                {mapStats?.total_buildings || 0} Buildings
              </Badge>
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="bg-surface/30 border-b border-border/30 p-2 flex items-center gap-2">
          {/* Zoom */}
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => setZoom(Math.max(1, zoom - 1))}
            disabled={zoom <= 1}
          >
            <ZoomOut className="w-4 h-4" />
          </Button>
          <span className="w-16 text-center text-sm">{zoom}x</span>
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => setZoom(Math.min(10, zoom + 1))}
            disabled={zoom >= 10}
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          
          <div className="w-px h-6 bg-border/30 mx-2" />
          
          {/* Toggle buttons */}
          <Button 
            variant={showEntities ? "default" : "outline"}
            size="sm"
            onClick={() => setShowEntities(!showEntities)}
          >
            <Users className="w-4 h-4 mr-1" />
            Entities
          </Button>
          <Button 
            variant={showRoads ? "default" : "outline"}
            size="sm"
            onClick={() => setShowRoads(!showRoads)}
          >
            <Navigation className="w-4 h-4 mr-1" />
            Roads
          </Button>
          <Button 
            variant={showGrid ? "default" : "outline"}
            size="sm"
            onClick={() => setShowGrid(!showGrid)}
          >
            <Layers className="w-4 h-4 mr-1" />
            Grid
          </Button>
          
          <div className="flex-1" />
          
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
        </div>

        {/* Map Canvas */}
        <div 
          ref={containerRef}
          className="flex-1 overflow-auto bg-obsidian/50 cursor-grab active:cursor-grabbing"
          style={{ 
            backgroundImage: 'radial-gradient(circle, rgba(255,215,0,0.03) 1px, transparent 1px)',
            backgroundSize: '40px 40px'
          }}
        >
          <canvas
            ref={canvasRef}
            className="m-4"
            onMouseMove={handleCanvasMouseMove}
            onClick={handleCanvasClick}
            onMouseDown={handleCanvasMouseDown}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={() => { setHoveredRegion(null); setIsDragging(false); }}
            style={{ cursor: hoveredRegion ? 'pointer' : isDragging ? 'grabbing' : 'grab' }}
            data-testid="world-map-canvas"
          />
        </div>

        {/* Hovered Region Tooltip */}
        {hoveredRegion && mapConfig?.regions?.[hoveredRegion] && (
          <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-surface border border-gold/30 rounded-lg p-3 shadow-xl pointer-events-none">
            <div className="font-cinzel text-gold">{mapConfig.regions[hoveredRegion].name}</div>
            <div className="text-xs text-muted-foreground">{mapConfig.regions[hoveredRegion].terrain}</div>
          </div>
        )}
      </div>

      {/* Right Sidebar - Region Details */}
      <div className="w-80 bg-surface/50 border-l border-border/30 flex flex-col">
        {/* Region List */}
        <div className="p-4 border-b border-border/30">
          <h3 className="font-cinzel text-lg text-gold mb-3">Regions</h3>
          <ScrollArea className="h-[200px]">
            <div className="space-y-2">
              {mapConfig?.regions && Object.entries(mapConfig.regions).map(([regionId, region]) => {
                const Icon = REGION_ICONS[regionId] || MapPin;
                const isSelected = selectedRegion === regionId;
                
                return (
                  <Card 
                    key={regionId}
                    className={`p-3 cursor-pointer transition-all ${
                      isSelected ? 'border-gold bg-gold/10' : 'border-border/30 hover:border-gold/50'
                    }`}
                    onClick={() => setSelectedRegion(regionId)}
                    data-testid={`region-${regionId}`}
                  >
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-8 h-8 rounded flex items-center justify-center"
                        style={{ backgroundColor: region.color + '40' }}
                      >
                        <Icon className="w-4 h-4" style={{ color: region.color }} />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{region.name}</div>
                        <div className="text-xs text-muted-foreground">{region.terrain}</div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </Card>
                );
              })}
            </div>
          </ScrollArea>
        </div>

        {/* Selected Region Details */}
        {selectedRegion && regionDetails && (
          <div className="flex-1 p-4 overflow-auto">
            <div className="flex items-center gap-3 mb-4">
              {(() => {
                const Icon = REGION_ICONS[selectedRegion] || MapPin;
                const region = mapConfig?.regions?.[selectedRegion];
                return (
                  <>
                    <div 
                      className="w-12 h-12 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: region?.color + '40' }}
                    >
                      <Icon className="w-6 h-6" style={{ color: region?.color }} />
                    </div>
                    <div>
                      <h4 className="font-cinzel text-lg">{regionDetails.region?.name}</h4>
                      <p className="text-sm text-muted-foreground capitalize">
                        {regionDetails.region?.terrain?.replace(/_/g, ' ')}
                      </p>
                    </div>
                  </>
                );
              })()}
            </div>

            {/* Region Stats */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <Card className="p-3 bg-black/20 border-border/20">
                <div className="text-2xl font-bold text-blue-400">{regionDetails.entity_count}</div>
                <div className="text-xs text-muted-foreground">Entities</div>
              </Card>
              <Card className="p-3 bg-black/20 border-border/20">
                <div className="text-2xl font-bold text-purple-400">{regionDetails.building_count}</div>
                <div className="text-xs text-muted-foreground">Buildings</div>
              </Card>
            </div>

            {/* Connected Regions */}
            <div className="mb-4">
              <h5 className="text-sm font-medium text-muted-foreground mb-2">Connected To</h5>
              <div className="flex flex-wrap gap-1">
                {regionDetails.region?.connectedTo?.map(connId => {
                  const connRegion = mapConfig?.regions?.[connId];
                  return (
                    <Badge 
                      key={connId}
                      className="cursor-pointer hover:bg-gold/20"
                      style={{ backgroundColor: connRegion?.color + '20', color: connRegion?.color }}
                      onClick={() => setSelectedRegion(connId)}
                    >
                      {connRegion?.name || connId}
                    </Badge>
                  );
                })}
              </div>
            </div>

            {/* NPCs in Region */}
            {regionDetails.npcs?.length > 0 && (
              <div className="mb-4">
                <h5 className="text-sm font-medium text-muted-foreground mb-2">NPCs Present</h5>
                <div className="space-y-2">
                  {regionDetails.npcs.map(npc => (
                    <div key={npc.villager_id} className="flex items-center gap-2 p-2 bg-black/20 rounded">
                      <Bot className="w-4 h-4 text-green-400" />
                      <div>
                        <div className="text-sm font-medium">{npc.name}</div>
                        <div className="text-xs text-muted-foreground">{npc.role}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Entities in Region */}
            {regionDetails.entities?.length > 0 && (
              <div className="mb-4">
                <h5 className="text-sm font-medium text-muted-foreground mb-2">Active Entities</h5>
                <div className="space-y-2">
                  {regionDetails.entities.slice(0, 5).map(entity => (
                    <div key={entity.entity_id} className="flex items-center gap-2 p-2 bg-black/20 rounded">
                      {entity.entity_type === 'player' ? (
                        <User className="w-4 h-4 text-blue-400" />
                      ) : (
                        <Sword className="w-4 h-4 text-red-400" />
                      )}
                      <div className="text-sm">{entity.entity_name}</div>
                      <Badge variant="outline" className="text-xs ml-auto">
                        {entity.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Navigate Button */}
            <Button 
              className="w-full bg-gold text-black hover:bg-gold-light"
              onClick={() => navigateToRegion(selectedRegion)}
              data-testid="navigate-to-region-btn"
            >
              <Navigation className="w-4 h-4 mr-2" />
              Travel to {regionDetails.region?.name}
            </Button>
          </div>
        )}

        {/* No Region Selected */}
        {!selectedRegion && (
          <div className="flex-1 p-4 flex items-center justify-center text-center">
            <div>
              <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-muted-foreground">Select a region on the map to view details</p>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="p-4 border-t border-border/30">
          <h5 className="text-sm font-medium text-muted-foreground mb-2">Legend</h5>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span>Player</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>NPC</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span>Creature</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-amber-800" />
              <span>Road</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorldMapUI;
