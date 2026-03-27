import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  X, Map, MapPin, Navigation, Compass, Users, 
  Building, TreeDeciduous, BookOpen, Flame, Eye, 
  Shield, Home, Lock, Unlock
} from 'lucide-react';
import { toast } from 'sonner';

const LOCATION_DATA = {
  village_square: {
    name: 'Village Square',
    icon: Home,
    color: 'bg-gold/30 border-gold',
    position: { x: 50, y: 50 },
    description: 'The heart of the village',
    npcs: ['Elder Morvain', 'Lyra the Wanderer', 'Town Guard'],
    connections: ['the_forge', 'oracle_sanctum', 'ancient_library', 'wanderers_rest'],
    accessible: true,
  },
  the_forge: {
    name: 'The Ember Forge',
    icon: Flame,
    color: 'bg-orange-500/30 border-orange-500',
    position: { x: 20, y: 30 },
    description: 'Where weapons are born',
    npcs: ['Kael Ironbrand'],
    connections: ['village_square'],
    accessible: true,
  },
  oracle_sanctum: {
    name: "Oracle's Sanctum",
    icon: Eye,
    color: 'bg-purple-500/30 border-purple-500',
    position: { x: 80, y: 30 },
    description: 'Home of mystic visions',
    npcs: ['Oracle Veythra'],
    connections: ['village_square'],
    accessible: true,
    matrixTheme: true,
  },
  ancient_library: {
    name: 'Ancient Library',
    icon: BookOpen,
    color: 'bg-amber-500/30 border-amber-500',
    position: { x: 80, y: 70 },
    description: 'Repository of knowledge',
    npcs: ['Archivist Nyx'],
    connections: ['village_square'],
    accessible: true,
  },
  wanderers_rest: {
    name: "Wanderer's Rest",
    icon: Building,
    color: 'bg-amber-700/30 border-amber-700',
    position: { x: 20, y: 70 },
    description: 'Tavern and inn',
    npcs: ['Innkeeper Mara', 'Hooded Stranger'],
    connections: ['village_square'],
    accessible: true,
  },
  shadow_grove: {
    name: 'Shadow Grove',
    icon: TreeDeciduous,
    color: 'bg-emerald-500/30 border-emerald-500',
    position: { x: 10, y: 50 },
    description: 'Mystical forest',
    npcs: ['The Grove Keeper'],
    connections: ['village_square'],
    accessible: true,
    matrixTheme: true,
  },
  watchtower: {
    name: 'The Watchtower',
    icon: Shield,
    color: 'bg-slate-500/30 border-slate-500',
    position: { x: 90, y: 50 },
    description: 'Sentinel outpost',
    npcs: ['Sentinel Vex'],
    connections: ['village_square'],
    accessible: true,
  },
};

const InteractiveMap = ({ currentLocation, onLocationSelect, isOpen, onClose, isTranscendent = false }) => {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [hoveredLocation, setHoveredLocation] = useState(null);
  
  if (!isOpen) return null;
  
  const handleLocationClick = (locId, locData) => {
    if (locData.accessible || isTranscendent) {
      setSelectedLocation(locId);
    } else {
      toast.error('This area is not yet accessible');
    }
  };
  
  const handleTravel = () => {
    if (selectedLocation && selectedLocation !== currentLocation) {
      onLocationSelect(selectedLocation);
      onClose();
      toast.success(`Traveling to ${LOCATION_DATA[selectedLocation].name}...`);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="bg-surface/95 border-gold/30 rounded-sm w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border/30 flex items-center justify-between bg-obsidian/50">
          <div className="flex items-center gap-2">
            <Map className="w-5 h-5 text-gold" />
            <span className="font-cinzel text-lg text-gold">Village Map</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        {/* Map Area */}
        <div className="relative w-full h-[400px] bg-obsidian/80 overflow-hidden">
          {/* Grid background */}
          <div 
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(rgba(255,215,0,0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,215,0,0.1) 1px, transparent 1px)
              `,
              backgroundSize: '40px 40px',
            }}
          />
          
          {/* Connection lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {Object.entries(LOCATION_DATA).map(([locId, loc]) => 
              loc.connections.map(connId => {
                const conn = LOCATION_DATA[connId];
                if (!conn) return null;
                return (
                  <line
                    key={`${locId}-${connId}`}
                    x1={`${loc.position.x}%`}
                    y1={`${loc.position.y}%`}
                    x2={`${conn.position.x}%`}
                    y2={`${conn.position.y}%`}
                    stroke="rgba(255,215,0,0.3)"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                );
              })
            )}
          </svg>
          
          {/* Location markers */}
          {Object.entries(LOCATION_DATA).map(([locId, loc]) => {
            const Icon = loc.icon;
            const isAccessible = loc.accessible || isTranscendent;
            const isCurrent = locId === currentLocation;
            const isSelected = locId === selectedLocation;
            const isHovered = locId === hoveredLocation;
            
            return (
              <div
                key={locId}
                className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-200 ${
                  isHovered || isSelected ? 'scale-125 z-20' : 'z-10'
                }`}
                style={{ left: `${loc.position.x}%`, top: `${loc.position.y}%` }}
                onClick={() => handleLocationClick(locId, loc)}
                onMouseEnter={() => setHoveredLocation(locId)}
                onMouseLeave={() => setHoveredLocation(null)}
              >
                <div className={`relative w-14 h-14 rounded-full border-2 flex items-center justify-center ${loc.color} ${
                  isCurrent ? 'ring-2 ring-gold ring-offset-2 ring-offset-obsidian' : ''
                } ${isSelected ? 'ring-2 ring-white' : ''} ${!isAccessible ? 'opacity-50' : ''}`}>
                  <Icon className={`w-6 h-6 ${isCurrent ? 'text-gold' : 'text-foreground'}`} />
                  
                  {/* Current location pulse */}
                  {isCurrent && (
                    <div className="absolute inset-0 rounded-full bg-gold/30 animate-ping" />
                  )}
                  
                  {/* Lock icon for inaccessible */}
                  {!isAccessible && (
                    <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
                      <Lock className="w-3 h-3 text-white" />
                    </div>
                  )}
                  
                  {/* Matrix theme indicator */}
                  {loc.matrixTheme && (
                    <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                      <span className="text-[8px] font-mono text-black">M</span>
                    </div>
                  )}
                </div>
                
                {/* Label */}
                <div className={`absolute top-full mt-1 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs font-mono ${
                  isCurrent ? 'text-gold' : 'text-foreground/70'
                }`}>
                  {loc.name}
                </div>
              </div>
            );
          })}
          
          {/* Compass */}
          <div className="absolute top-4 right-4 w-12 h-12 rounded-full bg-obsidian/80 border border-gold/30 flex items-center justify-center">
            <Compass className="w-6 h-6 text-gold" />
          </div>
        </div>
        
        {/* Info Panel */}
        <div className="p-4 border-t border-border/30 bg-obsidian/50">
          {selectedLocation ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-cinzel text-lg text-foreground">
                    {LOCATION_DATA[selectedLocation].name}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {LOCATION_DATA[selectedLocation].description}
                  </p>
                </div>
                {LOCATION_DATA[selectedLocation].matrixTheme && (
                  <Badge className="bg-green-500/20 text-green-400 border-green-500">
                    Virtual-scape
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-2 text-sm">
                <Users className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">NPCs:</span>
                <span className="text-foreground">
                  {LOCATION_DATA[selectedLocation].npcs.join(', ')}
                </span>
              </div>
              
              {selectedLocation !== currentLocation && (
                <Button 
                  onClick={handleTravel}
                  className="w-full bg-gold text-black hover:bg-gold-light"
                  disabled={!LOCATION_DATA[selectedLocation].accessible && !isTranscendent}
                >
                  <Navigation className="w-4 h-4 mr-2" />
                  Travel Here
                </Button>
              )}
              
              {selectedLocation === currentLocation && (
                <Badge className="w-full justify-center bg-gold/20 text-gold py-2">
                  <MapPin className="w-4 h-4 mr-2" />
                  You are here
                </Badge>
              )}
            </div>
          ) : (
            <p className="text-center text-muted-foreground">
              Select a location to view details
            </p>
          )}
        </div>
      </Card>
    </div>
  );
};

export default InteractiveMap;
