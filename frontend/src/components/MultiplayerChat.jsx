import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  MessageCircle, Send, Users, Globe, Building, 
  Crown, Shield, X, ChevronDown, Volume2, VolumeX
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WS_URL = process.env.REACT_APP_BACKEND_URL?.replace('https://', 'wss://').replace('http://', 'ws://');

const CHANNEL_ICONS = {
  local: Building,
  guild: Shield,
  city: Crown,
  state: Crown,
  country: Crown,
  global: Globe
};

const CHANNEL_COLORS = {
  local: 'text-green-400',
  guild: 'text-purple-400',
  city: 'text-blue-400',
  state: 'text-yellow-400',
  country: 'text-orange-400',
  global: 'text-red-400'
};

const MultiplayerChat = ({ userId, characterId, location, availableChannels = [], isOpen, onClose }) => {
  const wsRef = useRef(null);
  const scrollRef = useRef(null);
  
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [currentChannel, setCurrentChannel] = useState('local');
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  
  // Connect to WebSocket
  useEffect(() => {
    if (!isOpen || !userId || !location) return;
    
    const connectWs = () => {
      try {
        const ws = new WebSocket(`${WS_URL}/ws/${location}/${userId}`);
        
        ws.onopen = () => {
          setIsConnected(true);
          toast.success('Connected to chat');
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'chat') {
              setMessages(prev => [...prev.slice(-99), {
                id: Date.now(),
                sender: data.sender_name || 'Unknown',
                senderId: data.sender_id,
                message: data.message,
                channel: data.channel || 'local',
                timestamp: new Date().toLocaleTimeString()
              }]);
            } else if (data.type === 'player_joined') {
              setOnlinePlayers(prev => [...prev, { id: data.user_id, name: data.user_name }]);
              if (!isMuted) {
                setMessages(prev => [...prev, {
                  id: Date.now(),
                  system: true,
                  message: `${data.user_name} joined the area`,
                  timestamp: new Date().toLocaleTimeString()
                }]);
              }
            } else if (data.type === 'player_left') {
              setOnlinePlayers(prev => prev.filter(p => p.id !== data.user_id));
              if (!isMuted) {
                setMessages(prev => [...prev, {
                  id: Date.now(),
                  system: true,
                  message: `${data.user_name} left the area`,
                  timestamp: new Date().toLocaleTimeString()
                }]);
              }
            } else if (data.type === 'players_list') {
              setOnlinePlayers(data.players || []);
            }
          } catch (e) {
            console.error('Failed to parse message:', e);
          }
        };
        
        ws.onclose = () => {
          setIsConnected(false);
          // Reconnect after 3 seconds
          setTimeout(connectWs, 3000);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        
        wsRef.current = ws;
      } catch (error) {
        console.error('Failed to connect:', error);
      }
    };
    
    connectWs();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isOpen, userId, location, isMuted]);
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);
  
  const sendMessage = useCallback(() => {
    if (!inputMessage.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    wsRef.current.send(JSON.stringify({
      type: 'chat',
      message: inputMessage,
      channel: currentChannel
    }));
    
    setInputMessage('');
  }, [inputMessage, currentChannel]);
  
  if (!isOpen) return null;
  
  const ChannelIcon = CHANNEL_ICONS[currentChannel] || MessageCircle;
  
  return (
    <Card className="fixed bottom-4 right-4 w-96 h-[500px] bg-surface/95 backdrop-blur-sm border-gold/30 rounded-sm shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-border/30 flex items-center justify-between bg-obsidian/50">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-gold" />
          <span className="font-cinzel text-gold">Multiplayer Chat</span>
          <Badge className={`${isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'} text-xs`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setIsMuted(!isMuted)} className="h-8 w-8">
            {isMuted ? <VolumeX className="w-4 h-4 text-muted-foreground" /> : <Volume2 className="w-4 h-4 text-foreground" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {/* Channel Selector */}
      <div className="p-2 border-b border-border/30 flex gap-1 overflow-x-auto">
        {['local', ...availableChannels].filter((v, i, a) => a.indexOf(v) === i).map(channel => {
          const Icon = CHANNEL_ICONS[channel] || MessageCircle;
          return (
            <Button
              key={channel}
              variant={currentChannel === channel ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setCurrentChannel(channel)}
              className={`text-xs ${currentChannel === channel ? 'bg-gold/20 text-gold' : CHANNEL_COLORS[channel]}`}
            >
              <Icon className="w-3 h-3 mr-1" />
              {channel}
            </Button>
          );
        })}
      </div>
      
      {/* Online Players */}
      {onlinePlayers.length > 0 && (
        <div className="px-3 py-1 border-b border-border/30 bg-surface/30">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Users className="w-3 h-3" />
            <span>{onlinePlayers.length} online:</span>
            <span className="truncate">{onlinePlayers.map(p => p.name).join(', ')}</span>
          </div>
        </div>
      )}
      
      {/* Messages */}
      <ScrollArea className="flex-1 p-3" ref={scrollRef}>
        <div className="space-y-2">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground text-sm py-8">
              No messages yet. Say hello!
            </div>
          ) : (
            messages.map(msg => (
              <div 
                key={msg.id}
                className={`text-sm ${msg.system ? 'text-center text-muted-foreground italic' : ''}`}
              >
                {msg.system ? (
                  <span>{msg.message}</span>
                ) : (
                  <div>
                    <span className="text-xs text-muted-foreground">[{msg.timestamp}]</span>
                    <Badge className={`${CHANNEL_COLORS[msg.channel]} bg-transparent text-xs ml-1`}>
                      [{msg.channel}]
                    </Badge>
                    <span className={`font-semibold ${msg.senderId === userId ? 'text-gold' : 'text-foreground'}`}>
                      {' '}{msg.sender}:
                    </span>
                    <span className="text-foreground/90"> {msg.message}</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </ScrollArea>
      
      {/* Input */}
      <div className="p-3 border-t border-border/30 flex gap-2">
        <div className="flex items-center">
          <ChannelIcon className={`w-4 h-4 ${CHANNEL_COLORS[currentChannel]}`} />
        </div>
        <Input
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder={`Message ${currentChannel}...`}
          className="bg-obsidian border-border/50 rounded-sm text-sm"
          disabled={!isConnected}
        />
        <Button
          onClick={sendMessage}
          disabled={!isConnected || !inputMessage.trim()}
          size="sm"
          className="bg-gold text-black hover:bg-gold-light rounded-sm"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
};

export default MultiplayerChat;
