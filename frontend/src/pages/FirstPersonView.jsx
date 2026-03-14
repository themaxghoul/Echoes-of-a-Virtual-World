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
  MapPin, Compass, Crown, Shield, Zap
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import AIHelperPanel from '@/components/AIHelperPanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Location visual data
const LOCATION_SCENES = {
  'village_square': {
    background: 'linear-gradient(to bottom, #1a1a2e 0%, #16213e 50%, #0f0f23 100%)',
    groundColor: '#2d2d44',
    skyColor: '#1a1a2e',
    objects: ['fountain', 'market_stalls', 'cobblestones'],
    interactables: [
      { id: 'fountain', name: 'Ancient Fountain', x: 50, y: 60, type: 'examine' },
      { id: 'elder', name: 'Elder Morvain', x: 30, y: 50, type: 'talk', npc: 'Elder Morvain' },
      { id: 'lyra', name: 'Lyra the Wanderer', x: 70, y: 45, type: 'talk', npc: 'Lyra the Wanderer' },
    ],
    exits: [
      { id: 'to_forge', name: 'The Ember Forge', x: 10, y: 50, direction: 'west', target: 'the_forge' },
      { id: 'to_oracle', name: "Oracle's Sanctum", x: 90, y: 50, direction: 'east', target: 'oracle_sanctum' },
    ]
  },
  'oracle_sanctum': {
    background: 'linear-gradient(to bottom, #0d1b2a 0%, #1b263b 50%, #0d1b2a 100%)',
    groundColor: '#1b263b',
    skyColor: '#0d1b2a',
    objects: ['crystals', 'mist', 'altar'],
    interactables: [
      { id: 'oracle', name: 'Oracle Veythra', x: 50, y: 40, type: 'talk', npc: 'Oracle Veythra', isOracle: true },
      { id: 'crystal', name: 'Vision Crystal', x: 70, y: 60, type: 'examine' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 50, y: 90, direction: 'south', target: 'village_square' },
    ]
  },
  'the_forge': {
    background: 'linear-gradient(to bottom, #1a0a0a 0%, #2d1810 50%, #1a0a0a 100%)',
    groundColor: '#2d1810',
    skyColor: '#1a0a0a',
    objects: ['anvil', 'flames', 'weapons'],
    interactables: [
      { id: 'kael', name: 'Kael Ironbrand', x: 50, y: 45, type: 'talk', npc: 'Kael Ironbrand' },
      { id: 'anvil', name: 'Forge Anvil', x: 60, y: 55, type: 'craft' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 90, y: 50, direction: 'east', target: 'village_square' },
    ]
  },
  'ancient_library': {
    background: 'linear-gradient(to bottom, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%)',
    groundColor: '#2d2d2d',
    skyColor: '#1a1a1a',
    objects: ['shelves', 'books', 'candles'],
    interactables: [
      { id: 'nyx', name: 'Archivist Nyx', x: 40, y: 50, type: 'talk', npc: 'Archivist Nyx' },
      { id: 'tome', name: 'Ancient Tome', x: 70, y: 40, type: 'read' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 50, y: 90, direction: 'south', target: 'village_square' },
    ]
  },
  'wanderers_rest': {
    background: 'linear-gradient(to bottom, #2d1810 0%, #3d2820 50%, #2d1810 100%)',
    groundColor: '#3d2820',
    skyColor: '#2d1810',
    objects: ['tables', 'fireplace', 'bar'],
    interactables: [
      { id: 'mara', name: 'Innkeeper Mara', x: 30, y: 50, type: 'talk', npc: 'Innkeeper Mara' },
      { id: 'stranger', name: 'Hooded Stranger', x: 80, y: 60, type: 'talk', npc: 'The Hooded Stranger' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 50, y: 90, direction: 'south', target: 'village_square' },
    ]
  },
  'shadow_grove': {
    background: 'linear-gradient(to bottom, #0a1a0a 0%, #1a2d1a 50%, #0a1a0a 100%)',
    groundColor: '#1a2d1a',
    skyColor: '#0a1a0a',
    objects: ['trees', 'spirits', 'mushrooms'],
    interactables: [
      { id: 'keeper', name: 'The Grove Keeper', x: 50, y: 40, type: 'talk', npc: 'The Grove Keeper' },
      { id: 'shrine', name: 'Spirit Shrine', x: 30, y: 60, type: 'meditate' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 50, y: 90, direction: 'south', target: 'village_square' },
    ]
  },
  'watchtower': {
    background: 'linear-gradient(to bottom, #0f0f1a 0%, #1a1a2d 50%, #0f0f1a 100%)',
    groundColor: '#1a1a2d',
    skyColor: '#0f0f1a',
    objects: ['battlements', 'telescope', 'flags'],
    interactables: [
      { id: 'vex', name: 'Sentinel Vex', x: 50, y: 50, type: 'talk', npc: 'Sentinel Vex' },
      { id: 'telescope', name: 'Far-Seeing Glass', x: 70, y: 40, type: 'observe' },
    ],
    exits: [
      { id: 'to_square', name: 'Village Square', x: 50, y: 90, direction: 'south', target: 'village_square' },
    ]
  },
};

const FirstPersonView = () => {
  const navigate = useNavigate();
  const gameLoopRef = useRef(null);
  const wsRef = useRef(null);
  const staminaRegenRef = useRef(null);
  
  // Game state
  const [character, setCharacter] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [currentLocation, setCurrentLocation] = useState('village_square');
  const [playerPosition, setPlayerPosition] = useState({ x: 50, y: 70 });
  const [playerRotation, setPlayerRotation] = useState(0);
  const [nearbyInteractable, setNearbyInteractable] = useState(null);
  
  // Combat state
  const [combatStats, setCombatStats] = useState({
    health: 100, maxHealth: 100,
    stamina: 100, maxStamina: 100,
    strength: 10, endurance: 10, agility: 10, vitality: 10
  });
  const [isBlocking, setIsBlocking] = useState(false);
  const [isSprinting, setIsSprinting] = useState(false);
  const [inCombat, setInCombat] = useState(false);
  const [activeDemons, setActiveDemons] = useState([]);
  const [combatLog, setCombatLog] = useState([]);
  
  // UI state
  const [isPaused, setIsPaused] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showCombatUI, setShowCombatUI] = useState(false);
  const [showAIHelper, setShowAIHelper] = useState(false);
  const [chatChannel, setChatChannel] = useState('local');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [availableChannels, setAvailableChannels] = useState([]);
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  
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
        const [charRes, userRes, channelsRes, combatRes, demonsRes] = await Promise.all([
          axios.get(`${API}/character/${charId}`),
          userId ? axios.get(`${API}/users/id/${userId}`) : null,
          userId ? axios.get(`${API}/chat/channels/${userId}`).catch(() => null) : null,
          axios.get(`${API}/character/${charId}/combat-stats`).catch(() => null),
          axios.get(`${API}/demons/active/${charRes?.data?.current_location || 'village_square'}`).catch(() => null),
        ]);
        
        setCharacter(charRes.data);
        setCurrentLocation(charRes.data.current_location || 'village_square');
        if (charRes.data.position) {
          setPlayerPosition({ x: charRes.data.position.x || 50, y: charRes.data.position.y || 70 });
        }
        
        if (userRes?.data) setUserProfile(userRes.data);
        if (channelsRes?.data) setAvailableChannels(channelsRes.data.channels || []);
        
        // Load combat stats
        if (combatRes?.data) {
          setCombatStats({
            health: combatRes.data.health || 100,
            maxHealth: combatRes.data.max_health || 100,
            stamina: combatRes.data.stamina || 100,
            maxStamina: combatRes.data.max_stamina || 100,
            strength: combatRes.data.stats?.strength || 10,
            endurance: combatRes.data.stats?.endurance || 10,
            agility: combatRes.data.stats?.agility || 10,
            vitality: combatRes.data.stats?.vitality || 10,
            sprintDrain: combatRes.data.derived_stats?.sprint_stamina_drain_per_second || 2
          });
          setIsBlocking(combatRes.data.combat_state?.is_blocking || false);
          setIsSprinting(combatRes.data.combat_state?.is_sprinting || false);
          setInCombat(combatRes.data.combat_state?.in_combat || false);
        }
        
        // Load active demons
        if (demonsRes?.data && demonsRes.data.length > 0) {
          setActiveDemons(demonsRes.data);
          setInCombat(true);
          setShowCombatUI(true);
        }
      } catch (error) {
        console.error('Failed to load:', error);
      }
    };
    
    loadData();
  }, [navigate]);
  
  // Game loop with sprint stamina drain
  useEffect(() => {
    if (isPaused) return;
    
    const baseMoveSpeed = 0.5;
    const sprintMultiplier = 2.0;
    
    gameLoopRef.current = setInterval(() => {
      const isMoving = movement.up || movement.down || movement.left || movement.right || joystickActive;
      const currentSpeed = (isSprinting && combatStats.stamina > 0) ? baseMoveSpeed * sprintMultiplier : baseMoveSpeed;
      
      // Drain stamina while sprinting and moving
      if (isSprinting && isMoving && combatStats.stamina > 0) {
        const drainRate = combatStats.sprintDrain || 2;
        setCombatStats(prev => ({
          ...prev,
          stamina: Math.max(0, prev.stamina - (drainRate * 0.016)) // ~60fps
        }));
      }
      
      // Regenerate stamina when not sprinting (and not in combat)
      if (!isSprinting && !inCombat && combatStats.stamina < combatStats.maxStamina) {
        const regenRate = combatStats.endurance * 0.05;
        setCombatStats(prev => ({
          ...prev,
          stamina: Math.min(prev.maxStamina, prev.stamina + (regenRate * 0.016))
        }));
      }
      
      setPlayerPosition(prev => {
        let newX = prev.x;
        let newY = prev.y;
        
        if (movement.up) newY = Math.max(10, prev.y - currentSpeed);
        if (movement.down) newY = Math.min(90, prev.y + currentSpeed);
        if (movement.left) newX = Math.max(5, prev.x - currentSpeed);
        if (movement.right) newX = Math.min(95, prev.x + currentSpeed);
        
        // Joystick movement
        if (joystickActive) {
          newX = Math.max(5, Math.min(95, prev.x + joystickPosition.x * currentSpeed));
          newY = Math.max(10, Math.min(90, prev.y + joystickPosition.y * currentSpeed));
        }
        
        return { x: newX, y: newY };
      });
    }, 16);
    
    return () => clearInterval(gameLoopRef.current);
  }, [movement, joystickActive, joystickPosition, isPaused, isSprinting, combatStats.stamina, combatStats.sprintDrain, combatStats.endurance, combatStats.maxStamina, inCombat]);
  
  // Check for nearby interactables
  useEffect(() => {
    const scene = LOCATION_SCENES[currentLocation];
    if (!scene) return;
    
    const allInteractables = [...scene.interactables, ...scene.exits];
    const nearby = allInteractables.find(obj => {
      const dist = Math.sqrt(Math.pow(obj.x - playerPosition.x, 2) + Math.pow(obj.y - playerPosition.y, 2));
      return dist < 12;
    });
    
    setNearbyInteractable(nearby || null);
  }, [playerPosition, currentLocation]);
  
  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (showChat) return;
      
      switch(e.key.toLowerCase()) {
        case 'w': case 'arrowup': setMovement(m => ({ ...m, up: true })); break;
        case 's': case 'arrowdown': setMovement(m => ({ ...m, down: true })); break;
        case 'a': case 'arrowleft': setMovement(m => ({ ...m, left: true })); break;
        case 'd': case 'arrowright': setMovement(m => ({ ...m, right: true })); break;
        case 'e': case ' ': handleInteract(); break;
        case 'escape': setIsPaused(p => !p); break;
      }
    };
    
    const handleKeyUp = (e) => {
      switch(e.key.toLowerCase()) {
        case 'w': case 'arrowup': setMovement(m => ({ ...m, up: false })); break;
        case 's': case 'arrowdown': setMovement(m => ({ ...m, down: false })); break;
        case 'a': case 'arrowleft': setMovement(m => ({ ...m, left: false })); break;
        case 'd': case 'arrowright': setMovement(m => ({ ...m, right: false })); break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [showChat]);
  
  // Handle interaction
  const handleInteract = useCallback(async () => {
    if (!nearbyInteractable) return;
    
    if (nearbyInteractable.target) {
      // It's an exit - change location
      setCurrentLocation(nearbyInteractable.target);
      setPlayerPosition({ x: 50, y: 70 });
      
      if (character) {
        await axios.put(`${API}/character/${character.id}/location?location_id=${nearbyInteractable.target}`);
      }
      
      toast.success(`Entering ${nearbyInteractable.name}...`);
    } else if (nearbyInteractable.npc) {
      // It's an NPC - open chat
      setIsPaused(true);
      setShowChat(true);
      toast.info(`Speaking with ${nearbyInteractable.npc}`);
    } else {
      // Other interactable
      toast.info(`Examining ${nearbyInteractable.name}`);
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
  
  // Combat action handlers
  const handleAttack = async (isHeavy = false) => {
    if (!character) return;
    const action = isHeavy ? 'heavy_attack' : 'attack';
    const staminaCost = isHeavy ? 25 : 10;
    
    if (combatStats.stamina < staminaCost) {
      toast.error('Not enough stamina!');
      return;
    }
    
    try {
      const targetId = activeDemons.length > 0 ? activeDemons[0].id : null;
      const res = await axios.post(`${API}/character/${character.id}/action`, {
        character_id: character.id,
        action: action,
        target_id: targetId
      });
      
      setCombatStats(prev => ({ ...prev, stamina: res.data.remaining_stamina }));
      
      const logMsg = res.data.is_critical 
        ? `⚔️ CRITICAL HIT! ${res.data.damage_dealt} damage!`
        : `⚔️ Attack dealt ${res.data.damage_dealt} damage`;
      setCombatLog(prev => [...prev.slice(-4), logMsg]);
      
      if (res.data.target_defeated) {
        toast.success(`Victory! Drops: ${JSON.stringify(res.data.drops)}`);
        setActiveDemons(prev => prev.filter(d => d.id !== targetId));
        if (activeDemons.length <= 1) {
          setInCombat(false);
          setShowCombatUI(false);
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Attack failed');
    }
  };
  
  const handleBlock = async (start = true) => {
    if (!character) return;
    
    try {
      if (start) {
        await axios.post(`${API}/character/${character.id}/action`, {
          character_id: character.id,
          action: 'block'
        });
        setIsBlocking(true);
        setCombatLog(prev => [...prev.slice(-4), '🛡️ Blocking...']);
      } else {
        await axios.post(`${API}/character/${character.id}/stop-action?action=block`);
        setIsBlocking(false);
      }
    } catch (error) {
      console.error('Block action failed:', error);
    }
  };
  
  const handleDodge = async () => {
    if (!character) return;
    const staminaCost = 15;
    
    if (combatStats.stamina < staminaCost) {
      toast.error('Not enough stamina to dodge!');
      return;
    }
    
    try {
      const res = await axios.post(`${API}/character/${character.id}/action`, {
        character_id: character.id,
        action: 'dodge'
      });
      
      setCombatStats(prev => ({ ...prev, stamina: res.data.remaining_stamina }));
      
      const logMsg = res.data.dodge_success 
        ? '💨 Dodge successful!'
        : '💨 Dodge failed!';
      setCombatLog(prev => [...prev.slice(-4), logMsg]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Dodge failed');
    }
  };
  
  const handleSprint = (start = true) => {
    if (start && combatStats.stamina < 5) {
      toast.error('Not enough stamina to sprint!');
      return;
    }
    setIsSprinting(start);
  };
  
  // Check for demon encounters when entering new locations
  useEffect(() => {
    const checkForDemons = async () => {
      if (!currentLocation) return;
      try {
        const res = await axios.get(`${API}/demons/active/${currentLocation}`);
        if (res.data && res.data.length > 0) {
          setActiveDemons(res.data);
          setInCombat(true);
          setShowCombatUI(true);
          toast.warning(`⚠️ ${res.data.length} demon(s) detected!`);
        }
      } catch (error) {
        console.error('Failed to check demons:', error);
      }
    };
    checkForDemons();
  }, [currentLocation]);
  
  // Send chat message
  const handleSendChat = async () => {
    if (!chatInput.trim() || !character) return;
    
    const msg = {
      id: Date.now(),
      sender: character.name,
      channel: chatChannel,
      content: chatInput,
      timestamp: new Date().toISOString()
    };
    
    setChatMessages(prev => [...prev, msg]);
    setChatInput('');
    
    // Send to server
    try {
      await axios.post(`${API}/chat/location/${currentLocation}?sender_id=${userProfile?.id}&sender_name=${character.name}&content=${encodeURIComponent(chatInput)}&message_type=${chatChannel}`);
    } catch (error) {
      console.error('Chat send error:', error);
    }
  };
  
  const scene = LOCATION_SCENES[currentLocation] || LOCATION_SCENES['village_square'];
  
  return (
    <div className="h-screen w-screen overflow-hidden bg-obsidian relative">
      {/* Game View */}
      <div 
        className="absolute inset-0"
        style={{ background: scene.background }}
      >
        {/* Sky/Ceiling gradient */}
        <div className="absolute top-0 left-0 right-0 h-1/3 bg-gradient-to-b from-black/50 to-transparent" />
        
        {/* Ground/Floor */}
        <div 
          className="absolute bottom-0 left-0 right-0 h-1/2"
          style={{ 
            background: `linear-gradient(to bottom, transparent, ${scene.groundColor})`,
            perspective: '500px',
            transformStyle: 'preserve-3d'
          }}
        />
        
        {/* Interactables */}
        {[...scene.interactables, ...scene.exits].map((obj) => {
          const isNearby = nearbyInteractable?.id === obj.id;
          const distance = Math.sqrt(Math.pow(obj.x - playerPosition.x, 2) + Math.pow(obj.y - playerPosition.y, 2));
          const scale = Math.max(0.3, 1 - distance / 100);
          
          return (
            <div
              key={obj.id}
              className={`absolute transition-all duration-200 ${isNearby ? 'z-20' : 'z-10'}`}
              style={{
                left: `${obj.x}%`,
                top: `${obj.y}%`,
                transform: `translate(-50%, -50%) scale(${scale})`,
              }}
            >
              <div className={`relative flex flex-col items-center ${isNearby ? 'animate-pulse' : ''}`}>
                {/* Marker */}
                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-2 ${
                  obj.target ? 'bg-gold/30 border-gold' : 
                  obj.npc ? 'bg-slate-blue/30 border-slate-blue' : 
                  'bg-emerald-500/30 border-emerald-500'
                }`}>
                  {obj.target ? <Compass className="w-6 h-6 text-gold" /> :
                   obj.npc ? <Users className="w-6 h-6 text-slate-blue" /> :
                   <Eye className="w-6 h-6 text-emerald-400" />}
                </div>
                
                {/* Label */}
                {isNearby && (
                  <div className="absolute -bottom-8 whitespace-nowrap">
                    <Badge className="bg-black/80 text-foreground font-mono text-xs">
                      {obj.name} [E]
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {/* Player indicator (center) */}
        <div 
          className="absolute z-30 w-8 h-8 rounded-full bg-gold border-2 border-white shadow-lg"
          style={{
            left: `${playerPosition.x}%`,
            top: `${playerPosition.y}%`,
            transform: 'translate(-50%, -50%)'
          }}
        >
          <div className="absolute inset-0 rounded-full bg-gold animate-ping opacity-30" />
        </div>
      </div>
      
      {/* HUD - Top */}
      <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start z-40">
        <div className="glass rounded-sm px-4 py-2">
          <div className="flex items-center gap-3">
            <MapPin className="w-4 h-4 text-gold" />
            <span className="font-cinzel text-sm text-foreground">
              {scene ? Object.keys(LOCATION_SCENES).find(k => k === currentLocation)?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'}
            </span>
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
      
      {/* Health & Stamina Bars */}
      <div className="absolute top-16 left-4 z-40 space-y-2 w-64">
        {/* Health Bar */}
        <div className="glass rounded-sm p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-red-400">HP</span>
            <span className="text-xs font-mono text-foreground">{Math.round(combatStats.health)}/{combatStats.maxHealth}</span>
          </div>
          <div className="h-3 bg-black/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-red-700 to-red-500 transition-all duration-300"
              style={{ width: `${(combatStats.health / combatStats.maxHealth) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Stamina Bar */}
        <div className="glass rounded-sm p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-green-400">STAMINA</span>
            <span className="text-xs font-mono text-foreground">{Math.round(combatStats.stamina)}/{combatStats.maxStamina}</span>
          </div>
          <div className="h-3 bg-black/50 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-100 ${isSprinting ? 'bg-gradient-to-r from-yellow-600 to-yellow-400' : 'bg-gradient-to-r from-green-700 to-green-500'}`}
              style={{ width: `${(combatStats.stamina / combatStats.maxStamina) * 100}%` }}
            />
          </div>
          {isSprinting && <span className="text-xs text-yellow-400 mt-1">SPRINTING</span>}
        </div>
        
        {/* Combat Status */}
        {inCombat && (
          <div className="glass rounded-sm p-2 border border-red-500/50">
            <div className="text-xs font-mono text-red-400 flex items-center gap-2">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              IN COMBAT - {activeDemons.length} threat(s)
            </div>
          </div>
        )}
        
        {/* Blocking Status */}
        {isBlocking && (
          <Badge className="bg-blue-500/30 text-blue-300 border border-blue-500">
            <Shield className="w-3 h-3 mr-1" /> BLOCKING
          </Badge>
        )}
      </div>
      
      {/* Combat Log */}
      {showCombatUI && combatLog.length > 0 && (
        <div className="absolute top-16 right-4 z-40 w-64 glass rounded-sm p-2">
          <div className="text-xs font-mono text-gold mb-1">Combat Log</div>
          <div className="space-y-1">
            {combatLog.map((log, i) => (
              <div key={i} className="text-xs font-mono text-foreground/80">{log}</div>
            ))}
          </div>
        </div>
      )}
      
      {/* Active Demon Display */}
      {activeDemons.length > 0 && (
        <div className="absolute top-40 left-1/2 -translate-x-1/2 z-40 glass rounded-sm p-3 border border-red-500/50">
          <div className="text-center">
            <div className="text-red-400 font-cinzel text-lg">{activeDemons[0].demon_details?.name || 'Unknown Demon'}</div>
            <div className="text-xs text-muted-foreground">{activeDemons[0].demon_details?.rank} demon</div>
            <div className="mt-2 w-48 h-2 bg-black/50 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-700 to-red-500 transition-all"
                style={{ width: `${(activeDemons[0].health_remaining / (activeDemons[0].demon_details?.health || 100)) * 100}%` }}
              />
            </div>
            <div className="text-xs font-mono mt-1">{activeDemons[0].health_remaining} HP</div>
          </div>
        </div>
      )}
      
      {/* HUD - Bottom Controls */}
      <div className="absolute bottom-0 left-0 right-0 p-4 flex justify-between items-end z-40">
        {/* D-Pad / Joystick */}
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
          {/* D-Pad buttons */}
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
        
        {/* Action Buttons */}
        <div className="flex flex-col gap-3 items-end">
          {/* Interact Button */}
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
              {nearbyInteractable.target ? 'Enter' : nearbyInteractable.npc ? 'Talk' : 'Examine'}
            </Badge>
          )}
          
          {/* Sprint Button */}
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
      </div>
      
      {/* Combat Action Buttons - Right side */}
      <div className="absolute bottom-4 right-4 z-40 flex flex-col gap-2 items-center">
        {/* Attack Button */}
        <Button
          data-testid="attack-btn"
          onClick={() => handleAttack(false)}
          disabled={combatStats.stamina < 10}
          className="w-16 h-16 rounded-full bg-red-600 hover:bg-red-500 text-white"
        >
          <span className="text-lg">⚔️</span>
        </Button>
        <span className="text-xs font-mono text-foreground/50">Attack</span>
        
        {/* Heavy Attack Button */}
        <Button
          data-testid="heavy-attack-btn"
          onClick={() => handleAttack(true)}
          disabled={combatStats.stamina < 25}
          className="w-14 h-14 rounded-full bg-red-800 hover:bg-red-700 text-white"
        >
          <span className="text-sm">💥</span>
        </Button>
        <span className="text-xs font-mono text-foreground/50">Heavy</span>
        
        {/* Block Button */}
        <Button
          data-testid="block-btn"
          onMouseDown={() => handleBlock(true)}
          onMouseUp={() => handleBlock(false)}
          onTouchStart={() => handleBlock(true)}
          onTouchEnd={() => handleBlock(false)}
          className={`w-14 h-14 rounded-full ${
            isBlocking 
              ? 'bg-blue-500 text-white' 
              : 'bg-blue-800 hover:bg-blue-700 text-white'
          }`}
        >
          <Shield className="w-6 h-6" />
        </Button>
        <span className="text-xs font-mono text-foreground/50">Block</span>
        
        {/* Dodge Button */}
        <Button
          data-testid="dodge-btn"
          onClick={handleDodge}
          disabled={combatStats.stamina < 15}
          className="w-14 h-14 rounded-full bg-purple-700 hover:bg-purple-600 text-white"
        >
          <span className="text-lg">💨</span>
        </Button>
        <span className="text-xs font-mono text-foreground/50">Dodge</span>
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
                  onClick={() => { setIsPaused(false); setShowChat(false); }}
                  variant="ghost"
                  size="icon"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              
              {/* Character Info */}
              {character && (
                <div className="mb-6 p-4 bg-obsidian/50 rounded-sm">
                  <div className="font-cinzel text-lg text-foreground">{character.name}</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {character.traits?.join(' • ')}
                  </div>
                  {userProfile && (
                    <div className="flex items-center gap-2 mt-2">
                      <Badge className="bg-gold/20 text-gold text-xs">
                        <Crown className="w-3 h-3 mr-1" />
                        {userProfile.official_rank || 'Citizen'}
                      </Badge>
                    </div>
                  )}
                </div>
              )}
              
              {/* Menu Options */}
              <div className="space-y-2">
                <Button
                  data-testid="open-chat-btn"
                  onClick={() => setShowChat(true)}
                  className="w-full justify-start bg-slate-blue/20 text-slate-blue hover:bg-slate-blue/30 rounded-sm"
                >
                  <MessageCircle className="w-5 h-5 mr-3" />
                  Multiplayer Chat
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
                  onClick={() => navigate('/profile')}
                  className="w-full justify-start bg-white/10 text-foreground hover:bg-white/20 rounded-sm"
                >
                  <Crown className="w-5 h-5 mr-3" />
                  Profile
                </Button>
                
                <Button
                  onClick={() => setIsMuted(!isMuted)}
                  variant="ghost"
                  className="w-full justify-start rounded-sm"
                >
                  {isMuted ? <VolumeX className="w-5 h-5 mr-3" /> : <Volume2 className="w-5 h-5 mr-3" />}
                  {isMuted ? 'Unmute' : 'Mute'} Sound
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
              
              <Button
                data-testid="resume-game-btn"
                onClick={() => { setIsPaused(false); setShowChat(false); }}
                className="w-full mt-6 bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
              >
                <Play className="w-5 h-5 mr-2" />
                Resume
              </Button>
            </div>
          </Card>
        </div>
      )}
      
      {/* Chat Panel */}
      {showChat && (
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="bg-surface/95 border-border/50 rounded-sm w-full max-w-2xl h-[80vh] flex flex-col">
            {/* Chat Header */}
            <div className="p-4 border-b border-border/30 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h3 className="font-cinzel text-lg text-foreground">Multiplayer Chat</h3>
                {/* Channel selector */}
                <div className="flex gap-1">
                  {availableChannels.map(ch => (
                    <Button
                      key={ch.id}
                      onClick={() => setChatChannel(ch.id)}
                      size="sm"
                      className={`text-xs rounded-sm ${
                        chatChannel === ch.id 
                          ? 'bg-white/20' 
                          : 'bg-transparent hover:bg-white/10'
                      }`}
                      style={{ color: ch.color }}
                    >
                      {ch.name}
                    </Button>
                  ))}
                </div>
              </div>
              <Button
                onClick={() => setShowChat(false)}
                variant="ghost"
                size="icon"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            {/* Messages */}
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-3">
                {chatMessages.length === 0 ? (
                  <p className="text-center text-muted-foreground font-manrope text-sm">
                    No messages yet. Start the conversation!
                  </p>
                ) : (
                  chatMessages.map(msg => (
                    <div key={msg.id} className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-slate-blue/20 flex items-center justify-center">
                        <Users className="w-4 h-4 text-slate-blue" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-cinzel text-sm text-foreground">{msg.sender}</span>
                          <Badge className="text-xs" style={{ 
                            backgroundColor: availableChannels.find(c => c.id === msg.channel)?.color + '20',
                            color: availableChannels.find(c => c.id === msg.channel)?.color
                          }}>
                            {msg.channel}
                          </Badge>
                        </div>
                        <p className="font-manrope text-sm text-muted-foreground">{msg.content}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
            
            {/* Input */}
            <div className="p-4 border-t border-border/30 flex gap-2">
              <Input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendChat()}
                placeholder={`Send to ${chatChannel}...`}
                className="bg-obsidian border-border/50 rounded-sm"
              />
              <Button
                onClick={handleSendChat}
                className="bg-gold text-black hover:bg-gold-light rounded-sm"
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </Card>
        </div>
      )}
      
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

export default FirstPersonView;
