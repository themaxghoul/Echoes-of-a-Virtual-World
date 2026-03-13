import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  MapPin, Send, Menu, X, User, BookOpen, 
  ChevronRight, Loader2, Home, Sparkles, Lock, Unlock,
  Crown, Shield, Flame, Eye, Moon, Star, Globe
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// NPC Avatar configurations with visual appearances
const NPC_AVATARS = {
  'Elder Morvain': { icon: Crown, color: 'text-gold', bg: 'bg-gold/20', image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop' },
  'Lyra the Wanderer': { icon: Moon, color: 'text-slate-blue', bg: 'bg-slate-blue/20', image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop' },
  'Kael Ironbrand': { icon: Flame, color: 'text-orange-500', bg: 'bg-orange-500/20', image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&h=100&fit=crop' },
  'Archivist Nyx': { icon: Eye, color: 'text-purple-400', bg: 'bg-purple-400/20', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop' },
  'Innkeeper Mara': { icon: Star, color: 'text-amber-400', bg: 'bg-amber-400/20', image: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop' },
  'The Hooded Stranger': { icon: Shield, color: 'text-gray-400', bg: 'bg-gray-400/20', image: null },
  'The Grove Keeper': { icon: Moon, color: 'text-emerald-400', bg: 'bg-emerald-400/20', image: 'https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?w=100&h=100&fit=crop' },
  'Sentinel Vex': { icon: Shield, color: 'text-red-400', bg: 'bg-red-400/20', image: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop' },
};

// Location images for each area
const LOCATION_IMAGES = {
  'village_square': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&h=400&fit=crop',
  'the_forge': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=400&fit=crop',
  'ancient_library': 'https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=800&h=400&fit=crop',
  'wanderers_rest': 'https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=800&h=400&fit=crop',
  'shadow_grove': 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&h=400&fit=crop',
  'watchtower': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&h=400&fit=crop',
};

// Milestone system for world progression
const MILESTONES = [
  { id: 1, name: 'First Steps', description: 'Enter The Echoes', xpRequired: 0, unlocks: ['village_square'] },
  { id: 2, name: 'Seeker', description: 'Visit 3 locations', xpRequired: 50, unlocks: ['the_forge', 'ancient_library'] },
  { id: 3, name: 'Conversationalist', description: 'Have 10 conversations', xpRequired: 150, unlocks: ['wanderers_rest'] },
  { id: 4, name: 'Explorer', description: 'Discover all initial areas', xpRequired: 300, unlocks: ['shadow_grove'] },
  { id: 5, name: 'Trusted', description: 'Build relationships', xpRequired: 500, unlocks: ['watchtower'] },
  { id: 6, name: 'Awakened', description: 'Unlock the outer realms', xpRequired: 1000, unlocks: ['outer_realms'] },
];

const VillageExplorer = () => {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [character, setCharacter] = useState(null);
  const [locations, setLocations] = useState([]);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  
  // Milestone & progression state
  const [playerXP, setPlayerXP] = useState(0);
  const [currentMilestone, setCurrentMilestone] = useState(MILESTONES[0]);
  const [unlockedLocations, setUnlockedLocations] = useState(['village_square']);
  const [conversationCount, setConversationCount] = useState(0);
  const [visitedLocations, setVisitedLocations] = useState(new Set(['village_square']));
  const [worldNews, setWorldNews] = useState([]);

  // Load progression from localStorage
  useEffect(() => {
    const savedXP = parseInt(localStorage.getItem('playerXP') || '0');
    const savedConvCount = parseInt(localStorage.getItem('conversationCount') || '0');
    const savedVisited = JSON.parse(localStorage.getItem('visitedLocations') || '["village_square"]');
    
    setPlayerXP(savedXP);
    setConversationCount(savedConvCount);
    setVisitedLocations(new Set(savedVisited));
    
    // Calculate unlocked locations based on XP
    const unlocked = ['village_square'];
    MILESTONES.forEach(m => {
      if (savedXP >= m.xpRequired) {
        unlocked.push(...m.unlocks);
      }
    });
    setUnlockedLocations([...new Set(unlocked)]);
    
    // Set current milestone
    const milestone = [...MILESTONES].reverse().find(m => savedXP >= m.xpRequired) || MILESTONES[0];
    setCurrentMilestone(milestone);
  }, []);

  // Save progression
  const saveProgression = (xp, convCount, visited) => {
    localStorage.setItem('playerXP', xp.toString());
    localStorage.setItem('conversationCount', convCount.toString());
    localStorage.setItem('visitedLocations', JSON.stringify([...visited]));
  };

  // Award XP and check milestones
  const awardXP = (amount, reason) => {
    const newXP = playerXP + amount;
    setPlayerXP(newXP);
    
    // Check for new milestone
    const newMilestone = [...MILESTONES].reverse().find(m => newXP >= m.xpRequired);
    if (newMilestone && newMilestone.id > currentMilestone.id) {
      setCurrentMilestone(newMilestone);
      const newUnlocks = newMilestone.unlocks.filter(l => !unlockedLocations.includes(l));
      if (newUnlocks.length > 0) {
        setUnlockedLocations(prev => [...prev, ...newUnlocks]);
        toast.success(`Milestone Reached: ${newMilestone.name}! New areas unlocked.`);
      }
    }
    
    saveProgression(newXP, conversationCount, visitedLocations);
  };

  // Load character and locations on mount
  useEffect(() => {
    const loadData = async () => {
      const charId = localStorage.getItem('currentCharacterId');
      if (!charId) {
        toast.error('No character found. Please create one first.');
        navigate('/create-character');
        return;
      }

      try {
        const [charRes, locRes, newsRes] = await Promise.all([
          axios.get(`${API}/character/${charId}`),
          axios.get(`${API}/locations`),
          axios.get(`${API}/news`).catch(() => ({ data: { headlines: [] } }))
        ]);
        
        setCharacter(charRes.data);
        setLocations(locRes.data);
        setWorldNews(newsRes.data.headlines || []);
        
        const startLoc = locRes.data.find(l => l.id === charRes.data.current_location) || locRes.data[0];
        setCurrentLocation(startLoc);
        
        // Initial narrative
        setMessages([{
          role: 'narrator',
          content: `You find yourself in ${startLoc.name}. ${startLoc.description}\n\n${startLoc.atmosphere}`
        }]);
      } catch (error) {
        console.error('Failed to load data:', error);
        toast.error('Failed to connect to The Echoes');
      }
    };

    loadData();
  }, [navigate]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleLocationChange = async (location) => {
    if (location.id === currentLocation?.id) return;
    
    // Check if location is unlocked
    if (!unlockedLocations.includes(location.id)) {
      const requiredMilestone = MILESTONES.find(m => m.unlocks.includes(location.id));
      toast.error(`This area requires: ${requiredMilestone?.name || 'Unknown milestone'}`);
      return;
    }
    
    setCurrentLocation(location);
    setConversationId(null);
    
    // Track visited locations
    if (!visitedLocations.has(location.id)) {
      const newVisited = new Set([...visitedLocations, location.id]);
      setVisitedLocations(newVisited);
      awardXP(20, 'New location discovered');
      saveProgression(playerXP + 20, conversationCount, newVisited);
    }
    
    // Update character location
    if (character) {
      try {
        await axios.put(`${API}/character/${character.id}/location?location_id=${location.id}`);
      } catch (error) {
        console.error('Failed to update location:', error);
      }
    }

    // Add transition narrative
    setMessages(prev => [...prev, {
      role: 'narrator',
      content: `You travel to ${location.name}...\n\n${location.description}\n\n${location.atmosphere}`
    }]);
    
    setSidebarOpen(false);
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !character || !currentLocation) return;

    const userMsg = inputMessage.trim();
    setInputMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsThinking(true);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, {
        character_id: character.id,
        location_id: currentLocation.id,
        message: userMsg,
        conversation_id: conversationId
      });

      setConversationId(response.data.conversation_id);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.data.response 
      }]);
      
      // Award XP for conversation
      const newConvCount = conversationCount + 1;
      setConversationCount(newConvCount);
      awardXP(10, 'Conversation');
      saveProgression(playerXP + 10, newConvCount, visitedLocations);
    } catch (error) {
      console.error('Chat error:', error);
      toast.error('The mists interfere with your words...');
      setMessages(prev => [...prev, { 
        role: 'narrator', 
        content: '*The air shimmers, your words lost in the ethereal void. Try speaking again.*' 
      }]);
    } finally {
      setIsThinking(false);
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!character || !currentLocation) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="font-manrope text-muted-foreground">Entering The Echoes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-obsidian flex overflow-hidden">
      {/* Sidebar Backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <aside 
        className={`fixed lg:relative z-40 h-full bg-surface/95 backdrop-blur-xl border-r border-border/30 transition-all duration-300 overflow-hidden ${
          sidebarOpen ? 'w-80' : 'w-0'
        }`}
      >
        {sidebarOpen && (
          <div className="h-full flex flex-col w-80">
            {/* Character Info */}
            <div className="p-6 border-b border-border/30">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-sm bg-gold/20 border border-gold/30 flex items-center justify-center overflow-hidden">
                  {character?.appearance ? (
                    <div className="w-full h-full bg-gradient-to-br from-gold/30 to-slate-blue/30 flex items-center justify-center">
                      <User className="w-6 h-6 text-gold" />
                    </div>
                  ) : (
                    <User className="w-6 h-6 text-gold" />
                  )}
                </div>
                <div className="flex-1">
                  <h2 className="font-cinzel text-lg text-foreground">{character?.name}</h2>
                  <p className="font-mono text-xs text-muted-foreground">
                    {character?.traits?.slice(0, 2).join(' • ')}
                  </p>
                </div>
                <button
                  data-testid="close-sidebar-btn"
                  onClick={() => setSidebarOpen(false)}
                  className="text-muted-foreground hover:text-foreground p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              {/* XP Progress */}
              <div className="mt-4 p-3 bg-obsidian/50 rounded-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs text-muted-foreground">
                    {currentMilestone.name}
                  </span>
                  <span className="font-mono text-xs text-gold">{playerXP} XP</span>
                </div>
                <Progress 
                  value={(playerXP / (MILESTONES.find(m => m.xpRequired > playerXP)?.xpRequired || 1000)) * 100} 
                  className="h-1.5 bg-border"
                />
                <p className="font-manrope text-xs text-muted-foreground mt-2">
                  Next: {MILESTONES.find(m => m.xpRequired > playerXP)?.name || 'All unlocked'}
                </p>
              </div>
            </div>

            {/* Locations */}
            <ScrollArea className="flex-1 p-4">
              <h3 className="font-cinzel text-sm text-muted-foreground mb-4 uppercase tracking-wider">
                Explore The Village
              </h3>
              <div className="space-y-2">
                {locations.map((location) => {
                  const isUnlocked = unlockedLocations.includes(location.id);
                  const isCurrentLocation = currentLocation?.id === location.id;
                  
                  return (
                    <button
                      key={location.id}
                      data-testid={`location-${location.id}-btn`}
                      onClick={() => handleLocationChange(location)}
                      disabled={!isUnlocked}
                      className={`w-full text-left p-4 rounded-sm border transition-all duration-300 location-card ${
                        isCurrentLocation
                          ? 'border-gold bg-gold/10'
                          : isUnlocked
                            ? 'border-border/30 hover:border-slate-blue/50 bg-obsidian/30'
                            : 'border-border/20 bg-obsidian/20 opacity-50 cursor-not-allowed'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {isUnlocked ? (
                          <MapPin className={`w-4 h-4 mt-1 ${isCurrentLocation ? 'text-gold' : 'text-muted-foreground'}`} />
                        ) : (
                          <Lock className="w-4 h-4 mt-1 text-muted-foreground/50" />
                        )}
                        <div className="flex-1">
                          <div className="font-cinzel text-sm text-foreground flex items-center gap-2">
                            {location.name}
                            {!isUnlocked && (
                              <Badge variant="outline" className="text-xs font-mono">
                                Locked
                              </Badge>
                            )}
                          </div>
                          {isUnlocked && location.npcs.length > 0 && (
                            <div className="flex items-center gap-1 mt-2">
                              {location.npcs.slice(0, 3).map((npc, i) => {
                                const avatar = NPC_AVATARS[npc];
                                const Icon = avatar?.icon || User;
                                return (
                                  <div 
                                    key={i}
                                    className={`w-6 h-6 rounded-full ${avatar?.bg || 'bg-surface'} flex items-center justify-center overflow-hidden border border-border/30`}
                                    title={npc}
                                  >
                                    {avatar?.image ? (
                                      <img src={avatar.image} alt={npc} className="w-full h-full object-cover" />
                                    ) : (
                                      <Icon className={`w-3 h-3 ${avatar?.color || 'text-muted-foreground'}`} />
                                    )}
                                  </div>
                                );
                              })}
                              <span className="font-manrope text-xs text-muted-foreground ml-1">
                                {location.npcs.length} present
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
              
              {/* Locked Areas Hint */}
              {unlockedLocations.length < 6 && (
                <div className="mt-6 p-4 border border-dashed border-border/30 rounded-sm">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <Lock className="w-4 h-4" />
                    <span className="font-cinzel text-sm">Locked Areas</span>
                  </div>
                  <p className="font-manrope text-xs text-muted-foreground">
                    Explore and interact to unlock new regions. Progress: {unlockedLocations.length}/6
                  </p>
                </div>
              )}
            </ScrollArea>

            {/* Bottom Nav */}
            <div className="p-4 border-t border-border/30 space-y-2">
              <button
                data-testid="nav-home-btn"
                onClick={() => navigate('/')}
                className="w-full flex items-center gap-2 p-3 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Home className="w-4 h-4" />
                <span className="font-manrope text-sm">Return Home</span>
              </button>
              <button
                data-testid="nav-dataspace-btn"
                onClick={() => navigate('/dataspace')}
                className="w-full flex items-center gap-2 p-3 text-muted-foreground hover:text-slate-blue transition-colors"
              >
                <BookOpen className="w-4 h-4" />
                <span className="font-manrope text-sm">Global Dataspace</span>
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 glass border-b border-border/30 px-6 py-4 flex items-center justify-between">
          <button
            data-testid="open-sidebar-btn"
            onClick={() => setSidebarOpen(true)}
            className={`text-muted-foreground hover:text-foreground transition-colors ${sidebarOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="text-center">
            <h1 className="font-cinzel text-lg text-gold">{currentLocation.name}</h1>
            <p className="font-mono text-xs text-muted-foreground">
              {currentLocation.npcs.length} souls present
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-surface/50 rounded-sm">
              <Sparkles className="w-3 h-3 text-gold" />
              <span className="font-mono text-xs text-gold">{playerXP} XP</span>
            </div>
            {worldNews.length > 0 && (
              <button
                data-testid="news-indicator-btn"
                onClick={() => setInputMessage("What news from the outer world?")}
                className="hidden sm:flex items-center gap-2 px-3 py-1 bg-slate-blue/20 hover:bg-slate-blue/30 rounded-sm transition-colors"
                title="Ask about world news"
              >
                <Globe className="w-3 h-3 text-slate-blue" />
                <span className="font-mono text-xs text-slate-blue">News</span>
              </button>
            )}
            <Sparkles className="w-4 h-4 text-slate-blue animate-pulse sm:hidden" />
          </div>
        </header>

        {/* Location Image */}
        <div className="relative h-48 flex-shrink-0 overflow-hidden">
          <div 
            className="absolute inset-0 bg-cover bg-center transition-all duration-500"
            style={{
              backgroundImage: `url('${LOCATION_IMAGES[currentLocation.id] || 'https://images.unsplash.com/photo-1607223090232-57bd27efa9cd?w=800&h=400&fit=crop'}')`
            }}
          >
            <div className="atmosphere-overlay" />
          </div>
          
          {/* NPCs Present Overlay */}
          {currentLocation.npcs.length > 0 && (
            <div className="absolute top-4 right-4 flex flex-col gap-2">
              {currentLocation.npcs.map((npc, i) => {
                const avatar = NPC_AVATARS[npc];
                const Icon = avatar?.icon || User;
                return (
                  <div 
                    key={i}
                    className="flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-sm px-3 py-2"
                  >
                    <div className={`w-8 h-8 rounded-full ${avatar?.bg || 'bg-surface'} flex items-center justify-center overflow-hidden border border-white/20`}>
                      {avatar?.image ? (
                        <img src={avatar.image} alt={npc} className="w-full h-full object-cover" />
                      ) : (
                        <Icon className={`w-4 h-4 ${avatar?.color || 'text-muted-foreground'}`} />
                      )}
                    </div>
                    <span className="font-cinzel text-xs text-foreground">{npc}</span>
                  </div>
                );
              })}
            </div>
          )}
          
          <div className="absolute bottom-4 left-6 right-6">
            <p className="font-manrope text-sm text-foreground/80 italic line-clamp-2">
              {currentLocation.atmosphere}
            </p>
          </div>
        </div>

        {/* Chat Area */}
        <ScrollArea className="flex-1 p-6 chat-scroll">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg, i) => (
              <div 
                key={i} 
                className={`chat-message ${
                  msg.role === 'user' ? 'flex justify-end' : ''
                }`}
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {msg.role === 'narrator' ? (
                  <Card className="bg-slate-blue/10 border-slate-blue/30 rounded-sm p-4">
                    <p className="font-manrope text-sm text-foreground/90 italic whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </p>
                  </Card>
                ) : msg.role === 'user' ? (
                  <div className="max-w-[80%]">
                    <Card className="bg-gold/10 border-gold/30 rounded-sm p-4">
                      <p className="font-manrope text-sm text-foreground">
                        <span className="text-gold font-cinzel mr-2">{character.name}:</span>
                        {msg.content}
                      </p>
                    </Card>
                  </div>
                ) : (
                  <Card className="bg-surface/80 border-border/50 rounded-sm p-4">
                    <p className="font-manrope text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </p>
                  </Card>
                )}
              </div>
            ))}
            
            {/* Thinking Indicator */}
            {isThinking && (
              <Card className="bg-surface/80 border-border/50 rounded-sm p-4 w-fit">
                <div className="thinking-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </Card>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="flex-shrink-0 border-t border-border/30 bg-surface/50 backdrop-blur-sm p-4">
          <div className="max-w-3xl mx-auto">
            {/* Main Input Row */}
            <div className="flex gap-3">
              <Input
                ref={inputRef}
                data-testid="chat-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="What do you do? What do you say?"
                disabled={isLoading}
                className="flex-1 bg-obsidian border-border/50 focus:ring-gold/50 focus:border-gold/50 font-manrope rounded-sm py-6"
              />
              <Button
                data-testid="send-message-btn"
                onClick={handleSendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="bg-gold text-black hover:bg-gold-light rounded-sm px-6 disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </div>
            
            {/* Action Buttons - Outside and Below */}
            <div className="flex items-center justify-between mt-3">
              <p className="font-mono text-xs text-muted-foreground/50">
                Press Enter to send
              </p>
              
              {/* Quick Actions - Bottom Right Corner */}
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-muted-foreground/40 mr-2">Quick:</span>
                {currentLocation.available_actions.slice(0, 4).map((action, i) => (
                  <button
                    key={i}
                    data-testid={`quick-action-${action}-btn`}
                    onClick={() => setInputMessage(action)}
                    className="text-xs text-muted-foreground hover:text-gold px-3 py-1.5 bg-obsidian/80 border border-border/30 hover:border-gold/50 rounded-sm transition-all duration-200"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default VillageExplorer;
