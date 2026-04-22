import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { 
  ArrowLeft, Hammer, Home, Factory, Flower, Route, Sparkles,
  RefreshCw, Move, Trash2, RotateCw, DollarSign, Grid3X3,
  ZoomIn, ZoomOut, MapPin, Eye, EyeOff, Layers, CheckCircle,
  Save, Undo, ChevronLeft, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatVE = (amount) => {
  if (amount === null || amount === undefined) return 'VE$0';
  return `VE$${parseFloat(amount).toFixed(0)}`;
};

// Category icons
const CATEGORY_ICONS = {
  basic_structures: Home,
  functional_buildings: Factory,
  decorative: Flower,
  paths: Route,
  special: Sparkles
};

// Category colors for grid display
const CATEGORY_COLORS = {
  basic_structures: '#8B5A2B',
  functional_buildings: '#D97706',
  decorative: '#10B981',
  paths: '#6B7280',
  special: '#8B5CF6'
};

// Grid constants
const CELL_SIZE = 32;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2;

const BuildingGrid = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const canvasRef = useRef(null);
  
  const userId = localStorage.getItem('userId');
  const worldId = searchParams.get('world') || 'main-story-realm';
  const regionId = searchParams.get('region') || 'hollow_square';
  
  // State
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState({});
  const [gridData, setGridData] = useState(null);
  const [buildings, setBuildings] = useState([]);
  const [wallet, setWallet] = useState(null);
  const [ownedBuildings, setOwnedBuildings] = useState([]);
  
  // UI state
  const [selectedCategory, setSelectedCategory] = useState('basic_structures');
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [placementMode, setPlacementMode] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [showGrid, setShowGrid] = useState(true);
  const [hoveredCell, setHoveredCell] = useState(null);
  const [selectedPlacedBuilding, setSelectedPlacedBuilding] = useState(null);
  const [moveMode, setMoveMode] = useState(false);
  
  // Drag state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [catalogRes, gridRes, walletRes, ownedRes] = await Promise.all([
        axios.get(`${API}/building/catalog`),
        axios.get(`${API}/building/grid/${worldId}/${regionId}`),
        axios.get(`${API}/entity-earnings/wallet/player/${userId}`).catch(() => ({ data: null })),
        axios.get(`${API}/building/owned/${userId}?world_id=${worldId}`).catch(() => ({ data: { buildings: [] } }))
      ]);
      
      setCatalog(catalogRes.data.categories || {});
      setGridData(gridRes.data.grid);
      setBuildings(gridRes.data.buildings || []);
      setWallet(walletRes.data);
      setOwnedBuildings(ownedRes.data.buildings || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load building data');
    }
    setLoading(false);
  }, [userId, worldId, regionId]);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate, loadData]);

  // Draw grid on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || loading) return;
    
    const ctx = canvas.getContext('2d');
    const gridSize = gridData?.size?.[0] || 100;
    const canvasSize = gridSize * CELL_SIZE * zoom;
    
    canvas.width = canvasSize;
    canvas.height = canvasSize;
    
    ctx.clearRect(0, 0, canvasSize, canvasSize);
    
    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = 'rgba(255,215,0,0.1)';
      ctx.lineWidth = 1;
      
      for (let i = 0; i <= gridSize; i++) {
        const pos = i * CELL_SIZE * zoom;
        ctx.beginPath();
        ctx.moveTo(pos, 0);
        ctx.lineTo(pos, canvasSize);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, pos);
        ctx.lineTo(canvasSize, pos);
        ctx.stroke();
      }
    }
    
    // Draw placed buildings
    buildings.forEach(building => {
      const [bx, by] = building.position;
      const [bw, bh] = building.size || [1, 1];
      const color = CATEGORY_COLORS[building.category] || '#666';
      
      const x = bx * CELL_SIZE * zoom;
      const y = by * CELL_SIZE * zoom;
      const w = bw * CELL_SIZE * zoom;
      const h = bh * CELL_SIZE * zoom;
      
      // Building fill
      ctx.fillStyle = color + '80';
      ctx.fillRect(x, y, w, h);
      
      // Building border
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
      
      // Building name
      if (zoom >= 0.5) {
        ctx.fillStyle = '#fff';
        ctx.font = `${Math.max(10, 12 * zoom)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const name = building.custom_name || building.name;
        const maxWidth = w - 4;
        const displayName = name.length > 10 && zoom < 1 ? name.substring(0, 8) + '...' : name;
        ctx.fillText(displayName, x + w/2, y + h/2, maxWidth);
      }
      
      // Highlight selected
      if (selectedPlacedBuilding?.building_id === building.building_id) {
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 3;
        ctx.strokeRect(x - 2, y - 2, w + 4, h + 4);
      }
    });
    
    // Draw placement preview
    if (placementMode && selectedBuilding && hoveredCell) {
      const item = catalog[selectedCategory]?.items?.[selectedBuilding];
      if (item) {
        const [px, py] = hoveredCell;
        let [pw, ph] = item.size;
        
        // Handle rotation
        if (rotation === 90 || rotation === 270) {
          [pw, ph] = [ph, pw];
        }
        
        const x = px * CELL_SIZE * zoom;
        const y = py * CELL_SIZE * zoom;
        const w = pw * CELL_SIZE * zoom;
        const h = ph * CELL_SIZE * zoom;
        
        // Check if valid placement
        const isValid = px >= 0 && py >= 0 && px + pw <= gridSize && py + ph <= gridSize &&
          !buildings.some(b => {
            const [bx, by] = b.position;
            const [bw, bh] = b.size || [1, 1];
            return !(px + pw <= bx || px >= bx + bw || py + ph <= by || py >= by + bh);
          });
        
        ctx.fillStyle = isValid ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
        ctx.fillRect(x, y, w, h);
        
        ctx.strokeStyle = isValid ? '#10B981' : '#EF4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
      }
    }
  }, [buildings, showGrid, zoom, placementMode, selectedBuilding, selectedCategory, hoveredCell, rotation, catalog, loading, selectedPlacedBuilding, gridData]);

  // Handle canvas mouse events
  const handleCanvasMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / (CELL_SIZE * zoom));
    const y = Math.floor((e.clientY - rect.top) / (CELL_SIZE * zoom));
    setHoveredCell([x, y]);
    
    if (isDragging) {
      setOffset({
        x: offset.x + e.clientX - dragStart.x,
        y: offset.y + e.clientY - dragStart.y
      });
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleCanvasClick = async (e) => {
    if (!hoveredCell) return;
    const [x, y] = hoveredCell;
    
    if (placementMode && selectedBuilding) {
      // Place building
      await placeBuilding(x, y);
    } else if (moveMode && selectedPlacedBuilding) {
      // Move building
      await moveBuilding(x, y);
    } else {
      // Select existing building
      const clicked = buildings.find(b => {
        const [bx, by] = b.position;
        const [bw, bh] = b.size || [1, 1];
        return x >= bx && x < bx + bw && y >= by && y < by + bh;
      });
      setSelectedPlacedBuilding(clicked || null);
    }
  };

  const handleCanvasMouseDown = (e) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
  };

  // Place building
  const placeBuilding = async (x, y) => {
    if (!selectedBuilding || !selectedCategory) return;
    
    const item = catalog[selectedCategory]?.items?.[selectedBuilding];
    if (!item) return;
    
    try {
      const res = await axios.post(`${API}/building/place?owner_id=${userId}&owner_type=player`, {
        building_type: selectedBuilding,
        position: [x, y],
        rotation: rotation,
        world_id: worldId,
        region_id: regionId
      });
      
      toast.success(`Built ${item.name}!`);
      setPlacementMode(false);
      setSelectedBuilding(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to place building');
    }
  };

  // Move building
  const moveBuilding = async (newX, newY) => {
    if (!selectedPlacedBuilding) return;
    
    try {
      await axios.post(`${API}/building/move?owner_id=${userId}`, {
        building_id: selectedPlacedBuilding.building_id,
        new_position: [newX, newY],
        new_rotation: rotation
      });
      
      toast.success('Building moved!');
      setMoveMode(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to move building');
    }
  };

  // Demolish building
  const demolishBuilding = async () => {
    if (!selectedPlacedBuilding) return;
    
    try {
      const res = await axios.delete(`${API}/building/${selectedPlacedBuilding.building_id}?owner_id=${userId}`);
      
      toast.success(`Demolished! Refund: ${formatVE(res.data.refund)}`);
      setSelectedPlacedBuilding(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to demolish');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Building Grid...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground flex">
      {/* Left Sidebar - Building Catalog */}
      <div className="w-80 bg-surface/50 border-r border-border/30 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border/30">
          <div className="flex items-center gap-3 mb-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-xl text-gold flex items-center gap-2">
                <Grid3X3 className="w-5 h-5" />
                Building Grid
              </h1>
              <p className="text-xs text-muted-foreground">{regionId.replace(/_/g, ' ')}</p>
            </div>
          </div>
          
          {/* Balance */}
          <div className="flex items-center justify-between p-3 bg-gold/10 rounded-lg">
            <span className="text-sm text-muted-foreground">Balance</span>
            <span className="font-bold text-gold">{formatVE(wallet?.balance_ve || 0)}</span>
          </div>
        </div>
        
        {/* Category Tabs */}
        <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1 flex flex-col">
          <TabsList className="grid grid-cols-5 mx-4 mt-4 bg-surface">
            {Object.entries(CATEGORY_ICONS).map(([cat, Icon]) => (
              <TabsTrigger 
                key={cat} 
                value={cat}
                className="p-2"
                title={catalog[cat]?.name || cat}
              >
                <Icon className="w-4 h-4" />
              </TabsTrigger>
            ))}
          </TabsList>
          
          {/* Building Items */}
          <ScrollArea className="flex-1 p-4">
            {Object.entries(catalog).map(([catId, category]) => (
              <TabsContent key={catId} value={catId} className="mt-0 space-y-2">
                <h3 className="font-cinzel text-sm text-gold mb-3">{category.name}</h3>
                {Object.entries(category.items || {}).map(([itemId, item]) => {
                  const isSelected = selectedBuilding === itemId && placementMode;
                  const canAfford = (wallet?.balance_ve || 0) >= item.cost;
                  
                  return (
                    <Card 
                      key={itemId}
                      className={`p-3 cursor-pointer transition-all ${
                        isSelected ? 'border-gold bg-gold/10' : 
                        canAfford ? 'border-border/30 hover:border-gold/50' : 'border-border/30 opacity-50'
                      }`}
                      onClick={() => {
                        if (canAfford) {
                          setSelectedBuilding(itemId);
                          setPlacementMode(true);
                          setSelectedPlacedBuilding(null);
                          setMoveMode(false);
                        }
                      }}
                      data-testid={`building-item-${itemId}`}
                    >
                      <div className="flex items-start gap-3">
                        <div 
                          className="w-10 h-10 rounded flex items-center justify-center text-white text-xs font-bold"
                          style={{ backgroundColor: category.color }}
                        >
                          {item.size[0]}x{item.size[1]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm">{item.name}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge className="bg-gold/20 text-gold text-xs">
                              {formatVE(item.cost)}
                            </Badge>
                            {item.function && (
                              <Badge variant="outline" className="text-xs">
                                {item.function}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </TabsContent>
            ))}
          </ScrollArea>
        </Tabs>
      </div>

      {/* Main Grid Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="bg-surface/50 border-b border-border/30 p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Zoom controls */}
            <Button 
              variant="outline" 
              size="icon"
              onClick={() => setZoom(Math.max(MIN_ZOOM, zoom - 0.25))}
              disabled={zoom <= MIN_ZOOM}
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="w-16 text-center text-sm">{Math.round(zoom * 100)}%</span>
            <Button 
              variant="outline" 
              size="icon"
              onClick={() => setZoom(Math.min(MAX_ZOOM, zoom + 0.25))}
              disabled={zoom >= MAX_ZOOM}
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            
            <div className="w-px h-6 bg-border/30 mx-2" />
            
            {/* Grid toggle */}
            <Button 
              variant={showGrid ? "default" : "outline"}
              size="icon"
              onClick={() => setShowGrid(!showGrid)}
              title="Toggle grid"
            >
              {showGrid ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </Button>
            
            {/* Rotation */}
            <Button 
              variant="outline"
              size="icon"
              onClick={() => setRotation((rotation + 90) % 360)}
              title={`Rotation: ${rotation}°`}
            >
              <RotateCw className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Current mode */}
          <div className="flex items-center gap-2">
            {placementMode && selectedBuilding && (
              <Badge className="bg-green-500/20 text-green-400">
                Placing: {catalog[selectedCategory]?.items?.[selectedBuilding]?.name}
              </Badge>
            )}
            {moveMode && selectedPlacedBuilding && (
              <Badge className="bg-blue-500/20 text-blue-400">
                Moving: {selectedPlacedBuilding.name}
              </Badge>
            )}
            
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => {
                setPlacementMode(false);
                setMoveMode(false);
                setSelectedBuilding(null);
              }}
              disabled={!placementMode && !moveMode}
            >
              <Undo className="w-4 h-4 mr-1" />
              Cancel
            </Button>
          </div>
          
          {/* Coordinates */}
          <div className="text-sm text-muted-foreground font-mono">
            {hoveredCell ? `(${hoveredCell[0]}, ${hoveredCell[1]})` : '---'}
          </div>
        </div>

        {/* Canvas Container */}
        <div 
          className="flex-1 overflow-auto bg-obsidian/50 p-4"
          style={{ 
            backgroundImage: 'radial-gradient(circle, rgba(255,215,0,0.05) 1px, transparent 1px)',
            backgroundSize: '20px 20px'
          }}
        >
          <canvas
            ref={canvasRef}
            className="border border-gold/20 rounded cursor-crosshair"
            onMouseMove={handleCanvasMouseMove}
            onClick={handleCanvasClick}
            onMouseDown={handleCanvasMouseDown}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={() => { setHoveredCell(null); setIsDragging(false); }}
            data-testid="building-grid-canvas"
          />
        </div>
      </div>

      {/* Right Sidebar - Selected Building Info */}
      {selectedPlacedBuilding && (
        <div className="w-72 bg-surface/50 border-l border-border/30 p-4">
          <h3 className="font-cinzel text-lg text-gold mb-4">Selected Building</h3>
          
          <Card className="p-4 bg-black/20 border-border/30 mb-4">
            <div 
              className="w-full h-20 rounded mb-3 flex items-center justify-center"
              style={{ backgroundColor: CATEGORY_COLORS[selectedPlacedBuilding.category] + '40' }}
            >
              <span className="text-3xl font-bold text-white/80">
                {selectedPlacedBuilding.size?.[0]}x{selectedPlacedBuilding.size?.[1]}
              </span>
            </div>
            
            <h4 className="font-cinzel text-lg">{selectedPlacedBuilding.custom_name || selectedPlacedBuilding.name}</h4>
            <p className="text-sm text-muted-foreground mt-1">{selectedPlacedBuilding.category.replace(/_/g, ' ')}</p>
            
            <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
              <div>
                <span className="text-muted-foreground">Position</span>
                <div className="font-mono">({selectedPlacedBuilding.position.join(', ')})</div>
              </div>
              <div>
                <span className="text-muted-foreground">Rotation</span>
                <div className="font-mono">{selectedPlacedBuilding.rotation}°</div>
              </div>
              <div>
                <span className="text-muted-foreground">Health</span>
                <div className="font-mono">{selectedPlacedBuilding.health}%</div>
              </div>
              {selectedPlacedBuilding.function && (
                <div>
                  <span className="text-muted-foreground">Function</span>
                  <div className="capitalize">{selectedPlacedBuilding.function}</div>
                </div>
              )}
            </div>
          </Card>
          
          {/* Actions */}
          {selectedPlacedBuilding.owner_id === userId && (
            <div className="space-y-2">
              <Button 
                className="w-full"
                variant="outline"
                onClick={() => {
                  setMoveMode(true);
                  setPlacementMode(false);
                }}
                data-testid="move-building-btn"
              >
                <Move className="w-4 h-4 mr-2" />
                Move Building
              </Button>
              
              <Button 
                className="w-full bg-red-600 hover:bg-red-500"
                onClick={demolishBuilding}
                data-testid="demolish-building-btn"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Demolish (50% refund)
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BuildingGrid;
