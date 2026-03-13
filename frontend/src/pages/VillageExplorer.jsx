import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { 
  MapPin, Send, Menu, X, User, BookOpen, 
  ChevronRight, Loader2, Home, Sparkles 
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
        const [charRes, locRes] = await Promise.all([
          axios.get(`${API}/character/${charId}`),
          axios.get(`${API}/locations`)
        ]);
        
        setCharacter(charRes.data);
        setLocations(locRes.data);
        
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
    
    setCurrentLocation(location);
    setConversationId(null);
    
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
      {/* Sidebar */}
      <aside 
        className={`fixed lg:relative z-40 h-full bg-surface/95 backdrop-blur-xl border-r border-border/30 transition-all duration-300 ${
          sidebarOpen ? 'w-80 translate-x-0' : 'w-0 -translate-x-full lg:w-0'
        }`}
      >
        <div className="h-full flex flex-col w-80">
          {/* Character Info */}
          <div className="p-6 border-b border-border/30">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-sm bg-gold/20 border border-gold/30 flex items-center justify-center">
                <User className="w-6 h-6 text-gold" />
              </div>
              <div>
                <h2 className="font-cinzel text-lg text-foreground">{character.name}</h2>
                <p className="font-mono text-xs text-muted-foreground">
                  {character.traits.slice(0, 2).join(' • ')}
                </p>
              </div>
            </div>
            <button
              data-testid="close-sidebar-btn"
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Locations */}
          <ScrollArea className="flex-1 p-4">
            <h3 className="font-cinzel text-sm text-muted-foreground mb-4 uppercase tracking-wider">
              Explore The Village
            </h3>
            <div className="space-y-2">
              {locations.map((location) => (
                <button
                  key={location.id}
                  data-testid={`location-${location.id}-btn`}
                  onClick={() => handleLocationChange(location)}
                  className={`w-full text-left p-4 rounded-sm border transition-all duration-300 location-card ${
                    currentLocation?.id === location.id
                      ? 'border-gold bg-gold/10'
                      : 'border-border/30 hover:border-slate-blue/50 bg-obsidian/30'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <MapPin className={`w-4 h-4 mt-1 ${
                      currentLocation?.id === location.id ? 'text-gold' : 'text-muted-foreground'
                    }`} />
                    <div>
                      <div className="font-cinzel text-sm text-foreground">{location.name}</div>
                      <div className="font-manrope text-xs text-muted-foreground mt-1 line-clamp-2">
                        {location.npcs.length > 0 && `NPCs: ${location.npcs.join(', ')}`}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
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
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 glass border-b border-border/30 px-6 py-4 flex items-center justify-between">
          <button
            data-testid="open-sidebar-btn"
            onClick={() => setSidebarOpen(true)}
            className={`text-muted-foreground hover:text-foreground transition-colors ${sidebarOpen ? 'lg:hidden' : ''}`}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="text-center">
            <h1 className="font-cinzel text-lg text-gold">{currentLocation.name}</h1>
            <p className="font-mono text-xs text-muted-foreground">
              {currentLocation.npcs.length} souls present
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-slate-blue animate-pulse" />
          </div>
        </header>

        {/* Location Image */}
        <div className="relative h-48 flex-shrink-0 overflow-hidden">
          <div 
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage: `url('https://images.unsplash.com/photo-1607223090232-57bd27efa9cd?crop=entropy&cs=srgb&fm=jpg&q=85')`
            }}
          >
            <div className="atmosphere-overlay" />
          </div>
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
          <div className="max-w-3xl mx-auto flex gap-3">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                data-testid="chat-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="What do you do? What do you say?"
                disabled={isLoading}
                className="bg-obsidian border-border/50 focus:ring-gold/50 focus:border-gold/50 font-manrope rounded-sm pr-12 py-6"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {currentLocation.available_actions.slice(0, 2).map((action, i) => (
                  <button
                    key={i}
                    onClick={() => setInputMessage(action)}
                    className="text-xs text-muted-foreground hover:text-gold px-2 py-1 bg-surface rounded-sm"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
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
          <p className="text-center font-mono text-xs text-muted-foreground/50 mt-2">
            Press Enter to send • Type any action or dialogue
          </p>
        </div>
      </main>
    </div>
  );
};

export default VillageExplorer;
