import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, Home, Store, Factory, Wheat, Landmark,
  Plus, Minus, RotateCw, Trash2, DollarSign, RefreshCw,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, Move, Grid3X3, Info
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Category icons
const CATEGORY_ICONS = {
  residential: Home,
  commercial: Store,
  industrial: Factory,
  agricultural: Wheat,
  civic: Landmark
};

// Isometric helpers
const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;

const toIso = (x, y) => ({
  isoX: (x - y) * (TILE_WIDTH / 2),
  isoY: (x + y) * (TILE_HEIGHT / 2)
});

const fromIso = (isoX, isoY) => ({
  x: Math.floor((isoX / (TILE_WIDTH / 2) + isoY / (TILE_HEIGHT / 2)) / 2),
  y: Math.floor((isoY / (TILE_HEIGHT / 2) - isoX / (TILE_WIDTH / 2)) / 2)
});

const IsometricBuilder = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [plots, setPlots] = useState([]);
  const [prefabs, setPrefabs] = useState({});
  const [plotSizes, setPlotSizes] = useState({});
  const [selectedCategory, setSelectedCategory] = useState('residential');
  const [selectedPrefab, setSelectedPrefab] = useState(null);
  const [selectedPlot, setSelectedPlot] = useState(null);
  const [selectedVariant, setSelectedVariant] = useState(0);
  const [rotation, setRotation] = useState(0);
  const [balance, setBalance] = useState(0);
  const [stats, setStats] = useState(null);
  
  // Camera/view state
  const [viewOffset, setViewOffset] = useState({ x: 400, y: 100 });
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  
  // Mode state
  const [mode, setMode] = useState('view'); // view, place_plot, place_building

  // Load data
  const loadData = useCallback(async () => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    
    setLoading(true);
    try {
      const [plotsRes, prefabsRes, sizesRes, balanceRes, statsRes] = await Promise.all([
        axios.get(`${API}/isometric-building/plots/${userId}`),
        axios.get(`${API}/isometric-building/prefabs`),
        axios.get(`${API}/isometric-building/plot-sizes`),
        axios.get(`${API}/earnings/account/${userId}`).catch(() => ({ data: { available_balance_usd: 0 } })),
        axios.get(`${API}/isometric-building/stats/${userId}`).catch(() => ({ data: null }))
      ]);
      
      setPlots(plotsRes.data.plots || []);
      setPrefabs(prefabsRes.data.categories || {});
      setPlotSizes(sizesRes.data.plot_sizes || {});
      setBalance(balanceRes.data.available_balance_usd || 0);
      if (statsRes.data) setStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load:', error);
      toast.error('Failed to load building data');
    }
    setLoading(false);
  }, [userId, navigate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Purchase plot
  const purchasePlot = async (size, x, y) => {
    try {
      const res = await axios.post(`${API}/isometric-building/plot/purchase`, {
        user_id: userId,
        plot_size: size,
        position_x: x,
        position_y: y
      });
      
      toast.success(`Purchased ${plotSizes[size]?.name}!`);
      setBalance(res.data.remaining_balance);
      loadData();
      setMode('view');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to purchase plot');
    }
  };

  // Place building
  const placeBuilding = async () => {
    if (!selectedPlot || !selectedPrefab) return;
    
    try {
      const res = await axios.post(`${API}/isometric-building/building/place`, {
        user_id: userId,
        plot_id: selectedPlot.plot_id,
        category: selectedCategory,
        prefab_id: selectedPrefab,
        variant: selectedVariant,
        position_x: 0,
        position_y: 0,
        rotation: rotation
      });
      
      toast.success(`Built ${res.data.prefab_data.name}!`);
      setBalance(res.data.remaining_balance);
      loadData();
      setSelectedPrefab(null);
      setMode('view');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to place building');
    }
  };

  // Remove building
  const removeBuilding = async (plotId, buildingId) => {
    try {
      const res = await axios.delete(
        `${API}/isometric-building/building/${plotId}/${buildingId}?user_id=${userId}`
      );
      
      toast.success(`Building removed. Refund: VE$${res.data.refund.toFixed(2)}`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove building');
    }
  };

  // Render isometric grid
  const renderGrid = () => {
    const gridSize = 20;
    const tiles = [];
    
    for (let y = 0; y < gridSize; y++) {
      for (let x = 0; x < gridSize; x++) {
        const { isoX, isoY } = toIso(x, y);
        const screenX = viewOffset.x + isoX * zoom;
        const screenY = viewOffset.y + isoY * zoom;
        
        // Check if this tile is part of a plot
        const plot = plots.find(p => 
          x >= p.position_x && x < p.position_x + p.dimensions[0] &&
          y >= p.position_y && y < p.position_y + p.dimensions[1]
        );
        
        tiles.push(
          <div
            key={`${x}-${y}`}
            className={`absolute cursor-pointer transition-all duration-150 ${
              plot 
                ? 'hover:brightness-110' 
                : 'hover:bg-gold/20'
            }`}
            style={{
              left: screenX,
              top: screenY,
              width: TILE_WIDTH * zoom,
              height: TILE_HEIGHT * zoom,
              transform: 'rotateX(60deg) rotateZ(-45deg)',
              transformStyle: 'preserve-3d',
              backgroundColor: plot 
                ? plotSizes[plot.plot_size]?.color + '40'
                : '#1a1a1a',
              border: plot 
                ? `2px solid ${plotSizes[plot.plot_size]?.color}60`
                : '1px solid #333',
            }}
            onClick={() => {
              if (mode === 'place_plot') {
                purchasePlot('small', x, y);
              } else if (plot) {
                setSelectedPlot(plot);
              }
            }}
          />
        );
      }
    }
    
    return tiles;
  };

  // Render buildings on plots
  const renderBuildings = () => {
    const buildings = [];
    
    for (const plot of plots) {
      for (const building of plot.buildings || []) {
        const prefabData = prefabs[building.category]?.prefabs?.[building.prefab_id];
        if (!prefabData) continue;
        
        const x = plot.position_x + building.position_x;
        const y = plot.position_y + building.position_y;
        const { isoX, isoY } = toIso(x, y);
        
        const screenX = viewOffset.x + isoX * zoom;
        const screenY = viewOffset.y + isoY * zoom - (prefabData.size[1] * 20 * zoom);
        
        const CategoryIcon = CATEGORY_ICONS[building.category] || Home;
        
        buildings.push(
          <div
            key={building.building_id}
            className="absolute flex flex-col items-center cursor-pointer hover:scale-105 transition-transform"
            style={{
              left: screenX,
              top: screenY,
              zIndex: Math.floor(isoY + 100)
            }}
            onClick={() => setSelectedPlot(plot)}
          >
            <div 
              className="rounded-lg flex items-center justify-center shadow-lg"
              style={{
                width: prefabData.size[0] * 30 * zoom,
                height: prefabData.size[1] * 25 * zoom,
                backgroundColor: prefabs[building.category]?.color + 'CC',
                border: `2px solid ${prefabs[building.category]?.color}`
              }}
            >
              <CategoryIcon 
                className="text-white" 
                style={{ width: 20 * zoom, height: 20 * zoom }} 
              />
            </div>
            <span 
              className="text-white text-center mt-1 bg-black/60 px-1 rounded"
              style={{ fontSize: 10 * zoom }}
            >
              {prefabData.name}
            </span>
          </div>
        );
      }
    }
    
    return buildings;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  const currentPrefabs = prefabs[selectedCategory]?.prefabs || {};
  const CategoryIcon = CATEGORY_ICONS[selectedCategory] || Home;

  return (
    <div className="min-h-screen bg-obsidian text-foreground overflow-hidden">
      {/* Header */}
      <div className="bg-surface/80 border-b border-border/30 p-3 flex items-center justify-between z-50 relative">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-cinzel text-xl text-gold flex items-center gap-2">
              <Grid3X3 className="w-5 h-5" />
              2D Builder
            </h1>
            <p className="text-xs text-muted-foreground">Isometric View • v0.1.0</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <Badge className="bg-gold/20 text-gold px-3 py-1">
            <DollarSign className="w-4 h-4 mr-1" />
            VE${balance.toFixed(2)}
          </Badge>
          
          <div className="flex gap-1">
            <Button 
              size="sm" 
              variant={mode === 'view' ? 'default' : 'outline'}
              onClick={() => setMode('view')}
            >
              <Move className="w-4 h-4" />
            </Button>
            <Button 
              size="sm" 
              variant={mode === 'place_plot' ? 'default' : 'outline'}
              onClick={() => setMode('place_plot')}
              className="bg-green-600 hover:bg-green-500"
            >
              <Plus className="w-4 h-4 mr-1" />
              Plot
            </Button>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-60px)]">
        {/* Left Panel - Categories & Prefabs */}
        <div className="w-72 bg-surface/50 border-r border-border/30 flex flex-col">
          <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1 flex flex-col">
            <TabsList className="grid grid-cols-5 m-2 h-auto">
              {Object.entries(CATEGORY_ICONS).map(([cat, Icon]) => (
                <TabsTrigger 
                  key={cat} 
                  value={cat}
                  className="p-2"
                  data-testid={`cat-${cat}`}
                >
                  <Icon className="w-4 h-4" style={{ color: prefabs[cat]?.color }} />
                </TabsTrigger>
              ))}
            </TabsList>
            
            <div className="px-3 py-2 border-b border-border/30">
              <h3 className="font-cinzel text-sm" style={{ color: prefabs[selectedCategory]?.color }}>
                {prefabs[selectedCategory]?.name}
              </h3>
              <p className="text-xs text-muted-foreground">
                {prefabs[selectedCategory]?.description}
              </p>
            </div>
            
            <ScrollArea className="flex-1 p-2">
              <div className="space-y-2">
                {Object.entries(currentPrefabs).map(([prefabId, prefab]) => (
                  <Card
                    key={prefabId}
                    className={`p-3 cursor-pointer transition-all ${
                      selectedPrefab === prefabId 
                        ? 'ring-2 ring-gold bg-gold/10' 
                        : 'hover:bg-surface/80'
                    }`}
                    onClick={() => {
                      setSelectedPrefab(prefabId);
                      setSelectedVariant(0);
                      setMode('place_building');
                    }}
                    data-testid={`prefab-${prefabId}`}
                  >
                    <div className="flex items-start gap-3">
                      <div 
                        className="w-10 h-10 rounded flex items-center justify-center"
                        style={{ backgroundColor: prefabs[selectedCategory]?.color + '30' }}
                      >
                        <CategoryIcon className="w-5 h-5" style={{ color: prefabs[selectedCategory]?.color }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-sm truncate">{prefab.name}</h4>
                        <p className="text-xs text-muted-foreground line-clamp-1">{prefab.description}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge className="text-xs bg-gold/20 text-gold">
                            VE${prefab.cost}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {prefab.size[0]}x{prefab.size[1]}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </Tabs>
          
          {/* Stats */}
          {stats && (
            <div className="p-3 border-t border-border/30 bg-surface/30">
              <h4 className="font-cinzel text-sm text-gold mb-2">Your Empire</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Plots:</span>
                  <span className="ml-1 text-foreground">{stats.total_plots}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Buildings:</span>
                  <span className="ml-1 text-foreground">{stats.total_buildings}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Value:</span>
                  <span className="ml-1 text-gold">VE${stats.total_value}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Income:</span>
                  <span className="ml-1 text-green-400">+${stats.daily_income}/day</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Canvas Area */}
        <div 
          className="flex-1 relative overflow-hidden bg-gradient-to-b from-obsidian to-surface/20"
          onMouseDown={(e) => {
            if (mode === 'view') {
              setIsDragging(true);
              setDragStart({ x: e.clientX - viewOffset.x, y: e.clientY - viewOffset.y });
            }
          }}
          onMouseMove={(e) => {
            if (isDragging) {
              setViewOffset({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
              });
            }
          }}
          onMouseUp={() => setIsDragging(false)}
          onMouseLeave={() => setIsDragging(false)}
        >
          {/* Grid and Buildings */}
          <div className="absolute inset-0" style={{ perspective: '1000px' }}>
            {renderGrid()}
            {renderBuildings()}
          </div>
          
          {/* Zoom Controls */}
          <div className="absolute bottom-4 right-4 flex flex-col gap-2">
            <Button size="sm" variant="outline" onClick={() => setZoom(z => Math.min(z + 0.2, 2))}>
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}>
              <ZoomOut className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Navigation Controls */}
          <div className="absolute bottom-4 left-4 grid grid-cols-3 gap-1">
            <div />
            <Button size="sm" variant="outline" onClick={() => setViewOffset(v => ({ ...v, y: v.y + 50 }))}>
              <ChevronUp className="w-4 h-4" />
            </Button>
            <div />
            <Button size="sm" variant="outline" onClick={() => setViewOffset(v => ({ ...v, x: v.x + 50 }))}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={() => setViewOffset({ x: 400, y: 100 })}>
              <Move className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={() => setViewOffset(v => ({ ...v, x: v.x - 50 }))}>
              <ChevronRight className="w-4 h-4" />
            </Button>
            <div />
            <Button size="sm" variant="outline" onClick={() => setViewOffset(v => ({ ...v, y: v.y - 50 }))}>
              <ChevronDown className="w-4 h-4" />
            </Button>
            <div />
          </div>
          
          {/* Mode Indicator */}
          {mode !== 'view' && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-surface/90 border border-gold/50 rounded-lg px-4 py-2">
              <p className="text-sm text-gold font-cinzel">
                {mode === 'place_plot' && 'Click to place a Small Plot (VE$500)'}
                {mode === 'place_building' && selectedPrefab && `Click plot to build: ${currentPrefabs[selectedPrefab]?.name}`}
              </p>
            </div>
          )}
        </div>

        {/* Right Panel - Selected Plot Details */}
        {selectedPlot && (
          <div className="w-80 bg-surface/50 border-l border-border/30 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-cinzel text-lg text-gold">{selectedPlot.name}</h3>
              <Button size="sm" variant="ghost" onClick={() => setSelectedPlot(null)}>
                ×
              </Button>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge style={{ backgroundColor: plotSizes[selectedPlot.plot_size]?.color + '40' }}>
                  {plotSizes[selectedPlot.plot_size]?.name}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {selectedPlot.dimensions[0]}x{selectedPlot.dimensions[1]} tiles
                </span>
              </div>
              
              <div className="text-sm">
                <span className="text-muted-foreground">Buildings: </span>
                <span>{selectedPlot.buildings?.length || 0} / {selectedPlot.max_buildings}</span>
              </div>
              
              <div className="text-sm">
                <span className="text-muted-foreground">Position: </span>
                <span>({selectedPlot.position_x}, {selectedPlot.position_y})</span>
              </div>
              
              {/* Buildings List */}
              {selectedPlot.buildings?.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-cinzel text-sm mb-2">Buildings</h4>
                  <ScrollArea className="h-[200px]">
                    <div className="space-y-2">
                      {selectedPlot.buildings.map(building => {
                        const prefabData = prefabs[building.category]?.prefabs?.[building.prefab_id];
                        return (
                          <Card key={building.building_id} className="p-2">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-medium">{prefabData?.name}</p>
                                <p className="text-xs text-muted-foreground">
                                  +${prefabData?.income_per_day || 0}/day
                                </p>
                              </div>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-400 hover:text-red-300"
                                onClick={() => removeBuilding(selectedPlot.plot_id, building.building_id)}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </div>
              )}
              
              {/* Build Button */}
              {selectedPrefab && selectedPlot.buildings?.length < selectedPlot.max_buildings && (
                <Button 
                  className="w-full mt-4 bg-gold text-black hover:bg-gold-light"
                  onClick={placeBuilding}
                  data-testid="build-btn"
                >
                  Build {currentPrefabs[selectedPrefab]?.name}
                </Button>
              )}
              
              {/* Upgrade Plot */}
              {selectedPlot.plot_size !== 'large' && (
                <Button 
                  variant="outline" 
                  className="w-full border-blue-400 text-blue-400"
                  onClick={async () => {
                    const nextSize = selectedPlot.plot_size === 'small' ? 'medium' : 'large';
                    try {
                      const res = await axios.post(`${API}/isometric-building/plot/upgrade`, {
                        user_id: userId,
                        plot_id: selectedPlot.plot_id,
                        target_size: nextSize
                      });
                      toast.success(`Upgraded to ${plotSizes[nextSize]?.name}!`);
                      setBalance(res.data.remaining_balance);
                      loadData();
                    } catch (error) {
                      toast.error(error.response?.data?.detail || 'Upgrade failed');
                    }
                  }}
                >
                  Upgrade to {selectedPlot.plot_size === 'small' ? 'Medium' : 'Large'}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IsometricBuilder;
