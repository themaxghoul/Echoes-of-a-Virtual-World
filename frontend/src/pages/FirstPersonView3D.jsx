import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { 
  Menu, X, Hand, MessageCircle, Users, Settings,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  Pause, Play, Volume2, VolumeX, Eye, Send,
  MapPin, Compass, Crown, Shield, Zap, Package, Swords,
  Sparkles, Terminal
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import AIHelperPanel from '@/components/AIHelperPanel';
import MultiplayerChat from '@/components/MultiplayerChat';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Enhanced 3D scene configuration with textures and depth
const LOCATION_SCENES_3D = {
  'village_square': {
    name: 'Village Square',
    skyGradient: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 30%, #0f3460 60%, #1a1a2e 100%)',
    floorTexture: 'cobblestone',
    floorColor: '#3d3d5c',
    wallColor: '#2d2d44',
    ambientLight: 0.7,
    fog: 'rgba(26, 26, 46, 0.3)',
    structures: [
      { type: 'fountain', x: 50, z: 40, scale: 1.2, model: 'fountain' },
      { type: 'building', x: 15, z: 20, width: 20, height: 40, texture: 'stone_wall', label: 'The Forge' },
      { type: 'building', x: 85, z: 20, width: 18, height: 35, texture: 'marble', label: "Oracle's Sanctum" },
      { type: 'building', x: 15, z: 70, width: 22, height: 38, texture: 'wood', label: "Wanderer's Rest" },
      { type: 'building', x: 85, z: 70, width: 20, height: 45, texture: 'ancient', label: 'Ancient Library' },
      { type: 'stall', x: 35, z: 55, scale: 0.8 },
      { type: 'stall', x: 65, z: 55, scale: 0.8 },
    ],
    npcs: [
      { id: 'elder', name: 'Elder Morvain', x: 30, z: 45, sprite: 'elder', dialogue: true },
      { id: 'lyra', name: 'Lyra the Wanderer', x: 70, z: 50, sprite: 'wanderer', dialogue: true },
      { id: 'guard1', name: 'Town Guard', x: 50, z: 75, sprite: 'guard', patrol: true },
    ],
    exits: [
      { id: 'to_forge', label: 'The Ember Forge', x: 5, z: 25, direction: 'west', target: 'the_forge' },
      { id: 'to_oracle', label: "Oracle's Sanctum", x: 95, z: 25, direction: 'east', target: 'oracle_sanctum' },
      { id: 'to_library', label: 'Ancient Library', x: 95, z: 70, direction: 'east', target: 'ancient_library' },
      { id: 'to_inn', label: "Wanderer's Rest", x: 5, z: 70, direction: 'west', target: 'wanderers_rest' },
    ]
  },
  'oracle_sanctum': {
    name: "Oracle's Sanctum",
    skyGradient: 'linear-gradient(180deg, #0d1b2a 0%, #1b263b 40%, #415a77 70%, #0d1b2a 100%)',
    floorTexture: 'crystal',
    floorColor: '#1b263b',
    wallColor: '#0d1b2a',
    ambientLight: 0.4,
    fog: 'rgba(13, 27, 42, 0.5)',
    mystical: true,
    structures: [
      { type: 'altar', x: 50, z: 30, scale: 1.5, glow: true },
      { type: 'crystal', x: 30, z: 40, scale: 1.0, color: '#6c63ff' },
      { type: 'crystal', x: 70, z: 40, scale: 1.2, color: '#00d4ff' },
      { type: 'pillar', x: 20, z: 20, height: 60 },
      { type: 'pillar', x: 80, z: 20, height: 60 },
    ],
    npcs: [
      { id: 'oracle', name: 'Oracle Veythra', x: 50, z: 35, sprite: 'oracle', isOracle: true, glow: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 50, z: 95, direction: 'south', target: 'village_square' },
    ]
  },
  'the_forge': {
    name: 'The Ember Forge',
    skyGradient: 'linear-gradient(180deg, #1a0a0a 0%, #2d1810 40%, #4a2c1c 70%, #1a0a0a 100%)',
    floorTexture: 'metal',
    floorColor: '#2d1810',
    wallColor: '#1a0a0a',
    ambientLight: 0.6,
    fog: 'rgba(45, 24, 16, 0.4)',
    fireGlow: true,
    structures: [
      { type: 'anvil', x: 50, z: 40, scale: 1.0 },
      { type: 'forge', x: 30, z: 30, scale: 1.5, animated: true },
      { type: 'weapon_rack', x: 70, z: 35, scale: 1.0 },
      { type: 'barrel', x: 25, z: 60, scale: 0.8 },
      { type: 'barrel', x: 75, z: 55, scale: 0.7 },
    ],
    npcs: [
      { id: 'kael', name: 'Kael Ironbrand', x: 45, z: 45, sprite: 'blacksmith', dialogue: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 95, z: 50, direction: 'east', target: 'village_square' },
    ]
  },
  'ancient_library': {
    name: 'Ancient Library',
    skyGradient: 'linear-gradient(180deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%)',
    floorTexture: 'wood',
    floorColor: '#2d2d2d',
    wallColor: '#1a1a1a',
    ambientLight: 0.5,
    fog: 'rgba(26, 26, 26, 0.3)',
    structures: [
      { type: 'bookshelf', x: 20, z: 20, width: 15, height: 50 },
      { type: 'bookshelf', x: 80, z: 20, width: 15, height: 50 },
      { type: 'bookshelf', x: 20, z: 60, width: 15, height: 50 },
      { type: 'bookshelf', x: 80, z: 60, width: 15, height: 50 },
      { type: 'desk', x: 50, z: 40, scale: 1.2 },
      { type: 'candle', x: 45, z: 38, scale: 0.5, glow: true },
      { type: 'candle', x: 55, z: 38, scale: 0.5, glow: true },
    ],
    npcs: [
      { id: 'nyx', name: 'Archivist Nyx', x: 50, z: 45, sprite: 'scholar', dialogue: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 50, z: 95, direction: 'south', target: 'village_square' },
    ]
  },
  'wanderers_rest': {
    name: "Wanderer's Rest",
    skyGradient: 'linear-gradient(180deg, #2d1810 0%, #3d2820 50%, #2d1810 100%)',
    floorTexture: 'wood',
    floorColor: '#3d2820',
    wallColor: '#2d1810',
    ambientLight: 0.6,
    fog: 'rgba(45, 24, 16, 0.2)',
    structures: [
      { type: 'bar', x: 30, z: 25, width: 30, height: 20 },
      { type: 'table', x: 60, z: 40, scale: 1.0 },
      { type: 'table', x: 40, z: 60, scale: 1.0 },
      { type: 'fireplace', x: 80, z: 30, scale: 1.5, animated: true },
      { type: 'chair', x: 55, z: 42, scale: 0.6 },
      { type: 'chair', x: 65, z: 42, scale: 0.6 },
    ],
    npcs: [
      { id: 'mara', name: 'Innkeeper Mara', x: 30, z: 30, sprite: 'innkeeper', dialogue: true },
      { id: 'stranger', name: 'Hooded Stranger', x: 75, z: 55, sprite: 'hooded', dialogue: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 95, z: 50, direction: 'east', target: 'village_square' },
    ]
  },
  'shadow_grove': {
    name: 'Shadow Grove',
    skyGradient: 'linear-gradient(180deg, #0a1a0a 0%, #1a2d1a 40%, #0a1a0a 100%)',
    floorTexture: 'grass',
    floorColor: '#1a2d1a',
    wallColor: '#0a1a0a',
    ambientLight: 0.3,
    fog: 'rgba(10, 26, 10, 0.6)',
    mystical: true,
    structures: [
      { type: 'tree', x: 20, z: 30, scale: 2.0 },
      { type: 'tree', x: 80, z: 25, scale: 1.8 },
      { type: 'tree', x: 15, z: 70, scale: 2.2 },
      { type: 'tree', x: 85, z: 65, scale: 1.9 },
      { type: 'shrine', x: 50, z: 40, scale: 1.2, glow: true },
      { type: 'mushroom', x: 35, z: 55, scale: 0.6, glow: true },
      { type: 'mushroom', x: 65, z: 50, scale: 0.5, glow: true },
    ],
    npcs: [
      { id: 'keeper', name: 'The Grove Keeper', x: 50, z: 45, sprite: 'druid', dialogue: true, glow: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 50, z: 95, direction: 'south', target: 'village_square' },
    ]
  },
  'watchtower': {
    name: 'The Watchtower',
    skyGradient: 'linear-gradient(180deg, #0f0f1a 0%, #1a1a2d 30%, #2a2a4d 60%, #0f0f1a 100%)',
    floorTexture: 'stone',
    floorColor: '#1a1a2d',
    wallColor: '#0f0f1a',
    ambientLight: 0.8,
    fog: 'rgba(15, 15, 26, 0.2)',
    elevated: true,
    structures: [
      { type: 'battlement', x: 20, z: 10, width: 60, height: 15 },
      { type: 'telescope', x: 50, z: 30, scale: 1.0 },
      { type: 'flag', x: 25, z: 15, scale: 1.5, animated: true },
      { type: 'flag', x: 75, z: 15, scale: 1.5, animated: true },
      { type: 'torch', x: 30, z: 40, scale: 0.8, glow: true },
      { type: 'torch', x: 70, z: 40, scale: 0.8, glow: true },
    ],
    npcs: [
      { id: 'vex', name: 'Sentinel Vex', x: 50, z: 35, sprite: 'sentinel', dialogue: true },
    ],
    exits: [
      { id: 'to_square', label: 'Village Square', x: 50, z: 95, direction: 'south', target: 'village_square' },
    ]
  },
};

// 3D Structure renderer component
const Structure3D = ({ structure, playerPos, viewAngle }) => {
  const distance = Math.sqrt(
    Math.pow(structure.x - playerPos.x, 2) + 
    Math.pow(structure.z - playerPos.z, 2)
  );
  const scale = Math.max(0.1, 1 - distance / 150);
  const opacity = Math.max(0.3, 1 - distance / 200);
  
  // Calculate perspective position
  const perspectiveX = 50 + (structure.x - playerPos.x) * (1 - distance / 200);
  const perspectiveY = 50 + (structure.z - 50) * scale * 0.5;
  
  const getStructureStyle = () => {
    const baseStyle = {
      position: 'absolute',
      left: `${perspectiveX}%`,
      top: `${perspectiveY}%`,
      transform: `translate(-50%, -100%) scale(${scale})`,
      opacity,
      transition: 'all 0.1s ease-out',
      zIndex: Math.floor(100 - distance),
    };
    
    switch (structure.type) {
      case 'building':
        return {
          ...baseStyle,
          width: `${structure.width || 20}px`,
          height: `${structure.height || 40}px`,
          background: structure.texture === 'stone_wall' 
            ? 'linear-gradient(180deg, #4a4a6a 0%, #3d3d5c 50%, #2d2d44 100%)'
            : structure.texture === 'wood'
            ? 'linear-gradient(180deg, #5c4033 0%, #4a3728 50%, #3d2d1f 100%)'
            : structure.texture === 'marble'
            ? 'linear-gradient(180deg, #e8e8e8 0%, #c0c0c0 50%, #a0a0a0 100%)'
            : 'linear-gradient(180deg, #3d3d5c 0%, #2d2d44 100%)',
          border: '2px solid rgba(255,215,0,0.3)',
          borderRadius: '4px 4px 0 0',
          boxShadow: '0 4px 20px rgba(0,0,0,0.5), inset 0 -10px 30px rgba(0,0,0,0.3)',
        };
      case 'fountain':
        return {
          ...baseStyle,
          width: '60px',
          height: '50px',
          background: 'radial-gradient(ellipse at center, #4a9eff 0%, #2d5a8c 50%, #1a3d5c 100%)',
          borderRadius: '50% 50% 0 0',
          boxShadow: '0 0 30px rgba(74,158,255,0.5)',
        };
      case 'crystal':
        return {
          ...baseStyle,
          width: '30px',
          height: '50px',
          background: `linear-gradient(180deg, ${structure.color || '#6c63ff'} 0%, transparent 100%)`,
          clipPath: 'polygon(50% 0%, 100% 100%, 0% 100%)',
          boxShadow: `0 0 20px ${structure.color || '#6c63ff'}`,
          animation: structure.glow ? 'pulse 2s infinite' : 'none',
        };
      case 'altar':
        return {
          ...baseStyle,
          width: '80px',
          height: '40px',
          background: 'linear-gradient(180deg, #6c63ff 0%, #4a4a8a 50%, #2d2d5c 100%)',
          borderRadius: '4px',
          boxShadow: structure.glow ? '0 0 40px rgba(108,99,255,0.7)' : 'none',
        };
      case 'tree':
        return {
          ...baseStyle,
          width: '40px',
          height: '80px',
          background: 'linear-gradient(180deg, #2d5a2d 0%, #1a3d1a 50%, #3d2d1f 100%)',
          borderRadius: '50% 50% 0 0',
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        };
      case 'pillar':
        return {
          ...baseStyle,
          width: '20px',
          height: `${structure.height || 50}px`,
          background: 'linear-gradient(90deg, #4a4a6a 0%, #3d3d5c 50%, #2d2d44 100%)',
          borderRadius: '4px',
        };
      case 'bookshelf':
        return {
          ...baseStyle,
          width: `${structure.width || 15}px`,
          height: `${structure.height || 50}px`,
          background: 'linear-gradient(180deg, #5c4033 0%, #4a3728 100%)',
          boxShadow: 'inset 0 0 10px rgba(0,0,0,0.5)',
        };
      case 'anvil':
        return {
          ...baseStyle,
          width: '40px',
          height: '30px',
          background: 'linear-gradient(180deg, #555 0%, #333 100%)',
          borderRadius: '4px',
        };
      case 'forge':
        return {
          ...baseStyle,
          width: '60px',
          height: '45px',
          background: 'linear-gradient(180deg, #ff6b35 0%, #8b0000 100%)',
          borderRadius: '4px',
          boxShadow: '0 0 30px rgba(255,107,53,0.7)',
          animation: 'flicker 0.5s infinite alternate',
        };
      default:
        return {
          ...baseStyle,
          width: '30px',
          height: '30px',
          background: 'rgba(100,100,100,0.5)',
          borderRadius: '4px',
        };
    }
  };
  
  return (
    <div style={getStructureStyle()}>
      {structure.label && scale > 0.3 && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs font-mono text-gold bg-black/60 px-2 py-0.5 rounded">
          {structure.label}
        </div>
      )}
    </div>
  );
};

// NPC Sprite renderer
const NPCSprite = ({ npc, playerPos, isNearby, onClick }) => {
  const distance = Math.sqrt(
    Math.pow(npc.x - playerPos.x, 2) + 
    Math.pow(npc.z - playerPos.z, 2)
  );
  const scale = Math.max(0.2, 1 - distance / 120);
  const opacity = Math.max(0.4, 1 - distance / 150);
  
  const perspectiveX = 50 + (npc.x - playerPos.x) * (1 - distance / 150);
  const perspectiveY = 45 + (npc.z - 50) * scale * 0.4;
  
  const spriteColors = {
    elder: { primary: '#8b7355', accent: '#ffd700' },
    wanderer: { primary: '#4a6741', accent: '#90EE90' },
    guard: { primary: '#4a4a6a', accent: '#c0c0c0' },
    oracle: { primary: '#6c63ff', accent: '#00d4ff' },
    blacksmith: { primary: '#8b4513', accent: '#ff6b35' },
    scholar: { primary: '#2d2d44', accent: '#ffd700' },
    innkeeper: { primary: '#8b5a2b', accent: '#daa520' },
    hooded: { primary: '#1a1a1a', accent: '#4a4a4a' },
    druid: { primary: '#2d5a2d', accent: '#90EE90' },
    sentinel: { primary: '#4a4a6a', accent: '#87CEEB' },
  };
  
  const colors = spriteColors[npc.sprite] || { primary: '#555', accent: '#888' };
  
  return (
    <div
      data-testid={`npc-${npc.id}`}
      onClick={onClick}
      className={`absolute cursor-pointer transition-all duration-100 ${isNearby ? 'animate-pulse' : ''}`}
      style={{
        left: `${perspectiveX}%`,
        top: `${perspectiveY}%`,
        transform: `translate(-50%, -100%) scale(${scale})`,
        opacity,
        zIndex: Math.floor(110 - distance),
      }}
    >
      {/* NPC Body */}
      <div 
        className="relative"
        style={{
          width: '40px',
          height: '60px',
        }}
      >
        {/* Head */}
        <div 
          className="absolute top-0 left-1/2 -translate-x-1/2 rounded-full"
          style={{
            width: '20px',
            height: '20px',
            background: '#d4a574',
            border: `2px solid ${colors.accent}`,
          }}
        />
        {/* Body */}
        <div 
          className="absolute top-[18px] left-1/2 -translate-x-1/2"
          style={{
            width: '30px',
            height: '35px',
            background: `linear-gradient(180deg, ${colors.primary} 0%, ${colors.accent} 100%)`,
            borderRadius: '4px 4px 0 0',
            boxShadow: npc.glow ? `0 0 20px ${colors.accent}` : 'none',
          }}
        />
        
        {/* Glow effect for special NPCs */}
        {npc.glow && (
          <div 
            className="absolute inset-0 rounded-full animate-ping"
            style={{
              background: `radial-gradient(circle, ${colors.accent}40 0%, transparent 70%)`,
            }}
          />
        )}
      </div>
      
      {/* Name tag */}
      {(isNearby || scale > 0.5) && (
        <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <Badge 
            className={`text-xs ${isNearby ? 'bg-gold/30 text-gold border-gold' : 'bg-black/60 text-white'}`}
          >
            {npc.name} {isNearby && '[E]'}
          </Badge>
        </div>
      )}
    </div>
  );
};

// Exit portal renderer
const ExitPortal = ({ exit, playerPos, isNearby, onClick }) => {
  const distance = Math.sqrt(
    Math.pow(exit.x - playerPos.x, 2) + 
    Math.pow(exit.z - playerPos.z, 2)
  );
  const scale = Math.max(0.3, 1 - distance / 100);
  
  const perspectiveX = 50 + (exit.x - playerPos.x) * (1 - distance / 120);
  const perspectiveY = 50 + (exit.z - 50) * scale * 0.3;
  
  return (
    <div
      data-testid={`exit-${exit.id}`}
      onClick={onClick}
      className={`absolute cursor-pointer transition-all ${isNearby ? 'z-50' : ''}`}
      style={{
        left: `${perspectiveX}%`,
        top: `${perspectiveY}%`,
        transform: `translate(-50%, -50%) scale(${scale})`,
        zIndex: Math.floor(90 - distance),
      }}
    >
      <div className={`relative ${isNearby ? 'animate-pulse' : ''}`}>
        {/* Portal arch */}
        <div 
          className="w-16 h-24 rounded-t-full border-4 flex items-center justify-center"
          style={{
            borderColor: isNearby ? '#ffd700' : '#4a4a6a',
            background: 'linear-gradient(180deg, rgba(108,99,255,0.3) 0%, rgba(0,0,0,0.8) 100%)',
            boxShadow: isNearby ? '0 0 30px rgba(255,215,0,0.5)' : '0 0 15px rgba(108,99,255,0.3)',
          }}
        >
          <Compass className={`w-6 h-6 ${isNearby ? 'text-gold' : 'text-slate-blue'}`} />
        </div>
        
        {/* Label */}
        {isNearby && (
          <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
            <Badge className="bg-gold/30 text-gold border-gold text-xs">
              {exit.label} [E]
            </Badge>
          </div>
        )}
      </div>
    </div>
  );
};

const FirstPersonView3D = () => {
  const navigate = useNavigate();
  const gameLoopRef = useRef(null);
  
  // Game state
  const [character, setCharacter] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [currentLocation, setCurrentLocation] = useState('village_square');
  const [playerPosition, setPlayerPosition] = useState({ x: 50, z: 70 });
  const [nearbyInteractable, setNearbyInteractable] = useState(null);
  
  // Combat state
  const [combatStats, setCombatStats] = useState({
    health: 100, maxHealth: 100,
    stamina: 100, maxStamina: 100,
    mana: 50, maxMana: 50,
  });
  const [isBlocking, setIsBlocking] = useState(false);
  const [isSprinting, setIsSprinting] = useState(false);
  const [inCombat, setInCombat] = useState(false);
  const [activeDemons, setActiveDemons] = useState([]);
  const [combatLog, setCombatLog] = useState([]);
  
  // UI state
  const [isPaused, setIsPaused] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showMultiplayerChat, setShowMultiplayerChat] = useState(false);
  const [showAIHelper, setShowAIHelper] = useState(false);
  const [showCommands, setShowCommands] = useState(false);
  const [availableCommands, setAvailableCommands] = useState({});
  const [availableChannels, setAvailableChannels] = useState([]);
  
  // Time state
  const [timePhase, setTimePhase] = useState('morning');
  const [dangerLevel, setDangerLevel] = useState(0.1);
  
  // Movement state
  const [movement, setMovement] = useState({ up: false, down: false, left: false, right: false });
  const [joystickActive, setJoystickActive] = useState(false);
  const [joystickPosition, setJoystickPosition] = useState({ x: 0, y: 0 });
  
  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      const charId = localStorage.getItem('currentCharacterId');
      const userId = localStorage.getItem('userId');
      
      if (!charId) {
        toast.error('No character found');
        navigate('/create-character');
        return;
      }
      
      try {
        const [charRes, userRes, combatRes, commandsRes] = await Promise.all([
          axios.get(`${API}/character/${charId}`),
          userId ? axios.get(`${API}/users/id/${userId}`) : null,
          axios.get(`${API}/character/${charId}/combat-stats`).catch(() => null),
          userId ? axios.get(`${API}/commands?user_id=${userId}`).catch(() => null) : null,
        ]);
        
        setCharacter(charRes.data);
        setCurrentLocation(charRes.data.current_location || 'village_square');
        if (charRes.data.position) {
          setPlayerPosition({ x: charRes.data.position.x || 50, z: charRes.data.position.y || 70 });
        }
        
        if (userRes?.data) setUserProfile(userRes.data);
        if (combatRes?.data) {
          setCombatStats({
            health: combatRes.data.health || 100,
            maxHealth: combatRes.data.max_health || 100,
            stamina: combatRes.data.stamina || 100,
            maxStamina: combatRes.data.max_stamina || 100,
            mana: combatRes.data.mana || 50,
            maxMana: combatRes.data.max_mana || 50,
          });
        }
        if (commandsRes?.data) {
          setAvailableCommands(commandsRes.data.commands || {});
        }
        
        // Get time phase
        const timezoneOffset = new Date().getTimezoneOffset() / -60;
        const timeRes = await axios.post(`${API}/time/phase`, { timezone_offset: timezoneOffset });
        if (timeRes?.data) {
          setTimePhase(timeRes.data.phase);
          setDangerLevel(timeRes.data.danger_level);
        }
      } catch (error) {
        console.error('Failed to load:', error);
      }
    };
    
    loadData();
  }, [navigate]);
  
  // Game loop
  useEffect(() => {
    if (isPaused) return;
    
    const baseMoveSpeed = 0.8;
    const sprintMultiplier = 2.0;
    
    gameLoopRef.current = setInterval(() => {
      const isMoving = movement.up || movement.down || movement.left || movement.right || joystickActive;
      const currentSpeed = (isSprinting && combatStats.stamina > 0) ? baseMoveSpeed * sprintMultiplier : baseMoveSpeed;
      
      // Stamina drain while sprinting
      if (isSprinting && isMoving && combatStats.stamina > 0) {
        setCombatStats(prev => ({
          ...prev,
          stamina: Math.max(0, prev.stamina - 0.05)
        }));
      }
      
      // Stamina regen when not sprinting
      if (!isSprinting && combatStats.stamina < combatStats.maxStamina) {
        setCombatStats(prev => ({
          ...prev,
          stamina: Math.min(prev.maxStamina, prev.stamina + 0.03)
        }));
      }
      
      setPlayerPosition(prev => {
        let newX = prev.x;
        let newZ = prev.z;
        
        if (movement.up) newZ = Math.max(5, prev.z - currentSpeed);
        if (movement.down) newZ = Math.min(95, prev.z + currentSpeed);
        if (movement.left) newX = Math.max(5, prev.x - currentSpeed);
        if (movement.right) newX = Math.min(95, prev.x + currentSpeed);
        
        if (joystickActive) {
          newX = Math.max(5, Math.min(95, prev.x + joystickPosition.x * currentSpeed));
          newZ = Math.max(5, Math.min(95, prev.z + joystickPosition.y * currentSpeed));
        }
        
        return { x: newX, z: newZ };
      });
    }, 16);
    
    return () => clearInterval(gameLoopRef.current);
  }, [movement, joystickActive, joystickPosition, isPaused, isSprinting, combatStats.stamina, combatStats.maxStamina]);
  
  // Check for nearby interactables
  useEffect(() => {
    const scene = LOCATION_SCENES_3D[currentLocation];
    if (!scene) return;
    
    const npcs = scene.npcs || [];
    const exits = scene.exits || [];
    
    const allInteractables = [
      ...npcs.map(n => ({ ...n, type: 'npc' })),
      ...exits.map(e => ({ ...e, type: 'exit' })),
    ];
    
    const nearby = allInteractables.find(obj => {
      const dist = Math.sqrt(Math.pow(obj.x - playerPosition.x, 2) + Math.pow(obj.z - playerPosition.z, 2));
      return dist < 15;
    });
    
    setNearbyInteractable(nearby || null);
  }, [playerPosition, currentLocation]);
  
  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (showChat || showCommands) return;
      
      switch(e.key.toLowerCase()) {
        case 'w': case 'arrowup': setMovement(m => ({ ...m, up: true })); break;
        case 's': case 'arrowdown': setMovement(m => ({ ...m, down: true })); break;
        case 'a': case 'arrowleft': setMovement(m => ({ ...m, left: true })); break;
        case 'd': case 'arrowright': setMovement(m => ({ ...m, right: true })); break;
        case 'e': case ' ': handleInteract(); break;
        case 'escape': setIsPaused(p => !p); break;
        case 'shift': setIsSprinting(true); break;
      }
    };
    
    const handleKeyUp = (e) => {
      switch(e.key.toLowerCase()) {
        case 'w': case 'arrowup': setMovement(m => ({ ...m, up: false })); break;
        case 's': case 'arrowdown': setMovement(m => ({ ...m, down: false })); break;
        case 'a': case 'arrowleft': setMovement(m => ({ ...m, left: false })); break;
        case 'd': case 'arrowright': setMovement(m => ({ ...m, right: false })); break;
        case 'shift': setIsSprinting(false); break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [showChat, showCommands]);
  
  // Handle interaction
  const handleInteract = useCallback(async () => {
    if (!nearbyInteractable) return;
    
    if (nearbyInteractable.type === 'exit') {
      setCurrentLocation(nearbyInteractable.target);
      setPlayerPosition({ x: 50, z: 70 });
      
      if (character) {
        await axios.put(`${API}/character/${character.id}/location?location_id=${nearbyInteractable.target}`);
      }
      
      toast.success(`Entering ${nearbyInteractable.label}...`);
    } else if (nearbyInteractable.type === 'npc') {
      setIsPaused(true);
      
      // Check if it's the Oracle for world monitoring
      if (nearbyInteractable.isOracle) {
        toast.info(`Oracle Veythra's eyes glow with otherworldly light...`);
      } else {
        toast.info(`Speaking with ${nearbyInteractable.name}`);
      }
    }
  }, [nearbyInteractable, character]);
  
  // Joystick handlers
  const handleJoystickStart = (e) => {
    e.preventDefault();
    setJoystickActive(true);
  };
  
  const handleJoystickMove = (e) => {
    if (!joystickActive) return;
    const touch = e.touches ? e.touches[0] : e;
    const joystickArea = e.currentTarget.getBoundingClientRect();
    const centerX = joystickArea.left + joystickArea.width / 2;
    const centerY = joystickArea.top + joystickArea.height / 2;
    const deltaX = (touch.clientX - centerX) / (joystickArea.width / 2);
    const deltaY = (touch.clientY - centerY) / (joystickArea.height / 2);
    setJoystickPosition({
      x: Math.max(-1, Math.min(1, deltaX)),
      y: Math.max(-1, Math.min(1, deltaY))
    });
  };
  
  const handleJoystickEnd = () => {
    setJoystickActive(false);
    setJoystickPosition({ x: 0, y: 0 });
  };
  
  const handleSprint = (start = true) => {
    if (start && combatStats.stamina < 5) {
      toast.error('Not enough stamina!');
      return;
    }
    setIsSprinting(start);
  };
  
  const scene = LOCATION_SCENES_3D[currentLocation] || LOCATION_SCENES_3D['village_square'];
  
  // Time-based lighting
  const getTimeOverlay = () => {
    const overlays = {
      dawn: 'from-orange-900/30 via-purple-900/20 to-transparent',
      morning: 'from-blue-400/10 via-transparent to-transparent',
      afternoon: 'from-yellow-200/5 via-transparent to-transparent',
      dusk: 'from-orange-600/30 via-purple-900/30 to-transparent',
      night: 'from-indigo-900/50 via-blue-900/40 to-black/60',
      witching_hour: 'from-purple-900/60 via-red-900/30 to-black/70',
      pre_dawn: 'from-indigo-900/40 via-purple-900/30 to-black/50',
    };
    return overlays[timePhase] || '';
  };
  
  return (
    <div className="h-screen w-screen overflow-hidden bg-obsidian relative select-none">
      <style>{`
        @keyframes flicker {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.8; }
          50% { transform: scale(1.1); opacity: 1; }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
      `}</style>
      
      {/* 3D Game View */}
      <div 
        className="absolute inset-0 overflow-hidden"
        style={{ 
          background: scene.skyGradient,
          perspective: '1000px',
        }}
      >
        {/* Time overlay */}
        <div className={`absolute inset-0 pointer-events-none z-10 bg-gradient-to-b ${getTimeOverlay()} transition-all duration-1000`} />
        
        {/* Fog layer */}
        {scene.fog && (
          <div 
            className="absolute inset-0 pointer-events-none z-5"
            style={{ background: scene.fog }}
          />
        )}
        
        {/* Ground plane with perspective */}
        <div 
          className="absolute bottom-0 left-0 right-0 h-1/2"
          style={{
            background: `linear-gradient(to top, ${scene.floorColor} 0%, transparent 100%)`,
            transform: 'rotateX(60deg)',
            transformOrigin: 'bottom center',
          }}
        >
          {/* Floor grid pattern */}
          <div 
            className="absolute inset-0 opacity-20"
            style={{
              backgroundImage: `
                linear-gradient(rgba(255,215,0,0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,215,0,0.1) 1px, transparent 1px)
              `,
              backgroundSize: '50px 50px',
            }}
          />
        </div>
        
        {/* Structures */}
        {scene.structures?.map((structure, idx) => (
          <Structure3D 
            key={`${structure.type}-${idx}`}
            structure={structure}
            playerPos={playerPosition}
          />
        ))}
        
        {/* NPCs */}
        {scene.npcs?.map((npc) => (
          <NPCSprite
            key={npc.id}
            npc={npc}
            playerPos={playerPosition}
            isNearby={nearbyInteractable?.id === npc.id}
            onClick={() => {
              if (nearbyInteractable?.id === npc.id) handleInteract();
            }}
          />
        ))}
        
        {/* Exit portals */}
        {scene.exits?.map((exit) => (
          <ExitPortal
            key={exit.id}
            exit={exit}
            playerPos={playerPosition}
            isNearby={nearbyInteractable?.id === exit.id}
            onClick={() => {
              if (nearbyInteractable?.id === exit.id) handleInteract();
            }}
          />
        ))}
        
        {/* Player position indicator */}
        <div 
          className="absolute z-40 pointer-events-none"
          style={{
            left: '50%',
            bottom: '20%',
            transform: 'translate(-50%, 0)',
          }}
        >
          <div className="w-4 h-4 rounded-full bg-gold border-2 border-white shadow-lg">
            <div className="absolute inset-0 rounded-full bg-gold animate-ping opacity-40" />
          </div>
        </div>
      </div>
      
      {/* HUD - Top */}
      <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start z-40">
        <div className="glass rounded-sm px-4 py-2">
          <div className="flex items-center gap-3">
            <MapPin className="w-4 h-4 text-gold" />
            <span className="font-cinzel text-sm text-foreground">{scene.name}</span>
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button
            data-testid="pause-btn"
            onClick={() => setIsPaused(true)}
            variant="ghost"
            size="icon"
            className="glass rounded-sm"
          >
            <Pause className="w-5 h-5 text-foreground" />
          </Button>
        </div>
      </div>
      
      {/* Health/Stamina/Mana Bars */}
      <div className="absolute top-16 left-4 z-40 space-y-2 w-64">
        {/* Health */}
        <div className="glass rounded-sm p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-red-400">HP</span>
            <span className="text-xs font-mono text-foreground">{Math.round(combatStats.health)}/{combatStats.maxHealth}</span>
          </div>
          <div className="h-3 bg-black/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-red-700 to-red-500 transition-all"
              style={{ width: `${(combatStats.health / combatStats.maxHealth) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Stamina */}
        <div className="glass rounded-sm p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-green-400">STAMINA</span>
            <span className="text-xs font-mono text-foreground">{Math.round(combatStats.stamina)}/{combatStats.maxStamina}</span>
          </div>
          <div className="h-3 bg-black/50 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all ${isSprinting ? 'bg-gradient-to-r from-yellow-600 to-yellow-400' : 'bg-gradient-to-r from-green-700 to-green-500'}`}
              style={{ width: `${(combatStats.stamina / combatStats.maxStamina) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Mana */}
        <div className="glass rounded-sm p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-blue-400">MANA</span>
            <span className="text-xs font-mono text-foreground">{Math.round(combatStats.mana)}/{combatStats.maxMana}</span>
          </div>
          <div className="h-3 bg-black/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-blue-700 to-blue-400 transition-all"
              style={{ width: `${(combatStats.mana / combatStats.maxMana) * 100}%` }}
            />
          </div>
        </div>
        
        {isSprinting && <Badge className="bg-yellow-500/30 text-yellow-300">SPRINTING</Badge>}
      </div>
      
      {/* D-Pad / Joystick */}
      <div className="absolute bottom-4 left-4 z-40">
        <div 
          className="relative w-32 h-32 glass rounded-full"
          onTouchStart={handleJoystickStart}
          onTouchMove={handleJoystickMove}
          onTouchEnd={handleJoystickEnd}
          onMouseDown={handleJoystickStart}
          onMouseMove={handleJoystickMove}
          onMouseUp={handleJoystickEnd}
          onMouseLeave={handleJoystickEnd}
        >
          <button
            data-testid="dpad-up"
            onMouseDown={() => setMovement(m => ({ ...m, up: true }))}
            onMouseUp={() => setMovement(m => ({ ...m, up: false }))}
            onTouchStart={() => setMovement(m => ({ ...m, up: true }))}
            onTouchEnd={() => setMovement(m => ({ ...m, up: false }))}
            className="absolute top-2 left-1/2 -translate-x-1/2 w-10 h-10 rounded-sm bg-white/10 hover:bg-white/20 flex items-center justify-center"
          >
            <ChevronUp className="w-6 h-6 text-foreground" />
          </button>
          <button
            data-testid="dpad-down"
            onMouseDown={() => setMovement(m => ({ ...m, down: true }))}
            onMouseUp={() => setMovement(m => ({ ...m, down: false }))}
            onTouchStart={() => setMovement(m => ({ ...m, down: true }))}
            onTouchEnd={() => setMovement(m => ({ ...m, down: false }))}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 w-10 h-10 rounded-sm bg-white/10 hover:bg-white/20 flex items-center justify-center"
          >
            <ChevronDown className="w-6 h-6 text-foreground" />
          </button>
          <button
            data-testid="dpad-left"
            onMouseDown={() => setMovement(m => ({ ...m, left: true }))}
            onMouseUp={() => setMovement(m => ({ ...m, left: false }))}
            onTouchStart={() => setMovement(m => ({ ...m, left: true }))}
            onTouchEnd={() => setMovement(m => ({ ...m, left: false }))}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-sm bg-white/10 hover:bg-white/20 flex items-center justify-center"
          >
            <ChevronLeft className="w-6 h-6 text-foreground" />
          </button>
          <button
            data-testid="dpad-right"
            onMouseDown={() => setMovement(m => ({ ...m, right: true }))}
            onMouseUp={() => setMovement(m => ({ ...m, right: false }))}
            onTouchStart={() => setMovement(m => ({ ...m, right: true }))}
            onTouchEnd={() => setMovement(m => ({ ...m, right: false }))}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-sm bg-white/10 hover:bg-white/20 flex items-center justify-center"
          >
            <ChevronRight className="w-6 h-6 text-foreground" />
          </button>
          
          {/* Joystick knob */}
          <div 
            className="absolute top-1/2 left-1/2 w-10 h-10 rounded-full bg-gold/50 border-2 border-gold transition-transform"
            style={{
              transform: `translate(-50%, -50%) translate(${joystickPosition.x * 30}px, ${joystickPosition.y * 30}px)`
            }}
          />
        </div>
      </div>
      
      {/* Action buttons - Right side */}
      <div className="absolute bottom-4 right-4 z-40 flex flex-col gap-3 items-end">
        {/* Interact */}
        <Button
          data-testid="interact-btn"
          onClick={handleInteract}
          disabled={!nearbyInteractable}
          className={`w-16 h-16 rounded-full font-cinzel text-lg ${
            nearbyInteractable 
              ? 'bg-gold text-black hover:bg-gold-light animate-pulse' 
              : 'bg-white/10 text-muted-foreground'
          }`}
        >
          <Hand className="w-8 h-8" />
        </Button>
        
        {nearbyInteractable && (
          <Badge className="bg-black/80 text-gold font-mono text-xs">
            {nearbyInteractable.type === 'exit' ? 'Enter' : 'Talk'}
          </Badge>
        )}
        
        {/* Sprint */}
        <Button
          data-testid="sprint-btn"
          onMouseDown={() => handleSprint(true)}
          onMouseUp={() => handleSprint(false)}
          onTouchStart={() => handleSprint(true)}
          onTouchEnd={() => handleSprint(false)}
          className={`w-14 h-14 rounded-full ${
            isSprinting 
              ? 'bg-yellow-500 text-black' 
              : 'bg-white/10 text-foreground hover:bg-white/20'
          }`}
        >
          <span className="text-xs font-bold">RUN</span>
        </Button>
      </div>
      
      {/* Combat buttons */}
      <div className="absolute bottom-32 right-4 z-40 flex flex-col gap-2 items-center">
        <Button
          data-testid="attack-btn"
          onClick={() => toast.info('Combat requires a target')}
          disabled={combatStats.stamina < 10}
          className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-500 text-white"
        >
          <Swords className="w-6 h-6" />
        </Button>
        <span className="text-xs font-mono text-foreground/50">Attack</span>
        
        <Button
          data-testid="block-btn"
          className={`w-12 h-12 rounded-full ${isBlocking ? 'bg-blue-500' : 'bg-blue-800 hover:bg-blue-700'} text-white`}
        >
          <Shield className="w-5 h-5" />
        </Button>
        <span className="text-xs font-mono text-foreground/50">Block</span>
        
        <Button
          data-testid="magic-btn"
          disabled={combatStats.mana < 10}
          className="w-12 h-12 rounded-full bg-purple-700 hover:bg-purple-600 text-white"
        >
          <Sparkles className="w-5 h-5" />
        </Button>
        <span className="text-xs font-mono text-foreground/50">Magic</span>
      </div>
      
      {/* Pause Menu */}
      {isPaused && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <Card className="bg-surface/95 border-border/50 rounded-sm w-full max-w-md mx-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-cinzel text-2xl text-gold">Paused</h2>
                <Button
                  data-testid="resume-btn"
                  onClick={() => setIsPaused(false)}
                  variant="ghost"
                  size="icon"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              {character && (
                <div className="mb-6 p-4 bg-obsidian/50 rounded-sm">
                  <div className="font-cinzel text-lg text-foreground">{character.name}</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {character.traits?.join(' • ')}
                  </div>
                  {userProfile && (
                    <Badge className="bg-gold/20 text-gold text-xs mt-2">
                      <Crown className="w-3 h-3 mr-1" />
                      {userProfile.official_rank || 'Citizen'}
                    </Badge>
                  )}
                </div>
              )}
              
              <div className="space-y-2">
                <Button
                  onClick={() => setShowMultiplayerChat(true)}
                  className="w-full justify-start bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 rounded-sm"
                >
                  <MessageCircle className="w-5 h-5 mr-3" />
                  Multiplayer Chat
                </Button>
                
                <Button
                  onClick={() => setShowCommands(true)}
                  className="w-full justify-start bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-sm"
                >
                  <Terminal className="w-5 h-5 mr-3" />
                  Commands
                  {Object.keys(availableCommands).length > 2 && (
                    <Badge className="ml-auto bg-purple-500/30 text-purple-300 text-xs">
                      {Object.keys(availableCommands).length}
                    </Badge>
                  )}
                </Button>
                
                <Button
                  onClick={() => navigate('/quests')}
                  className="w-full justify-start bg-gold/20 text-gold hover:bg-gold/30 rounded-sm"
                >
                  <Shield className="w-5 h-5 mr-3" />
                  Quest Board
                </Button>
                
                <Button
                  onClick={() => navigate('/guilds')}
                  className="w-full justify-start bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-sm"
                >
                  <Users className="w-5 h-5 mr-3" />
                  Guild Hall
                </Button>
                
                <Button
                  data-testid="ai-helper-btn"
                  onClick={() => setShowAIHelper(true)}
                  className="w-full justify-start bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 rounded-sm"
                >
                  <Zap className="w-5 h-5 mr-3" />
                  AI Helper
                  <Badge className="ml-auto bg-yellow-500/30 text-yellow-300 text-xs">TEST</Badge>
                </Button>
                
                <Button
                  onClick={() => navigate('/inventory')}
                  className="w-full justify-start bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 rounded-sm"
                >
                  <Package className="w-5 h-5 mr-3" />
                  Inventory & Equipment
                </Button>
                
                <Button
                  onClick={() => navigate('/village')}
                  className="w-full justify-start bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded-sm"
                >
                  <Eye className="w-5 h-5 mr-3" />
                  Switch to Text Mode
                </Button>
                
                <Button
                  onClick={() => navigate('/profile')}
                  className="w-full justify-start bg-white/10 text-foreground hover:bg-white/20 rounded-sm"
                >
                  <Crown className="w-5 h-5 mr-3" />
                  Profile
                </Button>
                
                <Button
                  onClick={() => navigate('/')}
                  variant="ghost"
                  className="w-full justify-start text-red-400 hover:text-red-300 rounded-sm"
                >
                  <X className="w-5 h-5 mr-3" />
                  Exit Game
                </Button>
              </div>
              
              {/* Time Phase Info */}
              <div className={`mt-4 p-3 rounded-sm border ${
                dangerLevel > 0.5 ? 'bg-red-900/20 border-red-500/30' : 'bg-surface/30 border-border/30'
              }`}>
                <div className="text-xs text-muted-foreground mb-1">Current Time</div>
                <div className="font-cinzel capitalize text-foreground">{timePhase.replace('_', ' ')}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Danger: <span className={dangerLevel > 0.5 ? 'text-red-400' : 'text-green-400'}>
                    {Math.round(dangerLevel * 100)}%
                  </span>
                </div>
              </div>
              
              <Button
                data-testid="resume-game-btn"
                onClick={() => setIsPaused(false)}
                className="w-full mt-6 bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
              >
                <Play className="w-5 h-5 mr-2" />
                Resume
              </Button>
            </div>
          </Card>
        </div>
      )}
      
      {/* Commands Panel */}
      {showCommands && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="bg-surface/95 border-border/50 rounded-sm w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-5 h-5 text-purple-400" />
                <h3 className="font-cinzel text-lg text-foreground">Available Commands</h3>
              </div>
              <Button onClick={() => setShowCommands(false)} variant="ghost" size="icon">
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                {Object.entries(availableCommands).map(([cmd, info]) => (
                  <div key={cmd} className="p-3 bg-obsidian/50 rounded-sm">
                    <div className="flex items-center gap-2">
                      <code className="text-purple-400 font-mono">{cmd}</code>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{info.description}</p>
                    <code className="text-xs text-foreground/50 font-mono mt-1 block">{info.usage}</code>
                  </div>
                ))}
                
                {Object.keys(availableCommands).length === 0 && (
                  <p className="text-center text-muted-foreground">No commands available at your rank.</p>
                )}
              </div>
            </ScrollArea>
          </Card>
        </div>
      )}
      
      {/* Multiplayer Chat */}
      <MultiplayerChat 
        userId={userProfile?.id}
        characterId={character?.id}
        location={currentLocation}
        availableChannels={availableChannels}
        isOpen={showMultiplayerChat}
        onClose={() => setShowMultiplayerChat(false)}
      />
      
      {/* AI Helper Panel */}
      {showAIHelper && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg">
            <AIHelperPanel 
              userId={userProfile?.id} 
              onClose={() => setShowAIHelper(false)} 
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FirstPersonView3D;
