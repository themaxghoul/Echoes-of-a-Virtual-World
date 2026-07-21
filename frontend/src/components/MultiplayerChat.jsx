import { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  MessageSquare, Users, Globe, MapPin, UserPlus, Send,
  ExternalLink, X, Minimize2, Maximize2, Volume2, VolumeX,
  UserX, MoreVertical, Crown, Circle, MessageCircle
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WS_URL = process.env.REACT_APP_BACKEND_URL?.replace('https://', 'wss://').replace('http://', 'ws://');

// Message colors by channel
const CHANNEL_COLORS = {
  global: 'text-yellow-400',
  region: 'text-green-400',
  party: 'text-purple-400',
  whisper: 'text-pink-400'
};

const CHANNEL_ICONS = {
  global: Globe,
  region: MapPin,
  party: Users,
  whisper: MessageCircle
};

const MultiplayerChat = ({ 
  isOpen, 
  onClose, 
  onPopOut,
  isPopOut = false,
  currentRegion = null,
  userId: propUserId,
  characterId,
  location
}) => {
  const userId = propUserId || localStorage.getItem('userId');
  const username = localStorage.getItem('username');
  
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [activeChannel, setActiveChannel] = useState('global');
  const [messages, setMessages] = useState({
    global: [],
    region: [],
    party: [],
    whisper: []
  });
  const [inputValue, setInputValue] = useState('');
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});
  const [whisperTarget, setWhisperTarget] = useState(null);
  const [partyId, setPartyId] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [unreadCounts, setUnreadCounts] = useState({ global: 0, region: 0, party: 0, whisper: 0 });
  const [isMinimized, setIsMinimized] = useState(false);
  
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const effectiveRegion = currentRegion || location;

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!userId || ws?.readyState === WebSocket.OPEN) return;
    
    try {
      const socket = new WebSocket(`${WS_URL}/api/chat/ws/${userId}`);
      
      socket.onopen = () => {
        setConnected(true);
        
        // Join current region if any
        if (effectiveRegion) {
          socket.send(JSON.stringify({
            type: 'join_region',
            region_id: effectiveRegion
          }));
        }
      };
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };
      
      socket.onclose = () => {
        setConnected(false);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };
      
      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      };
      
      setWs(socket);
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [userId, effectiveRegion]);

  useEffect(() => {
    if (isOpen && userId) {
      connectWebSocket();
    }
    
    return () => {
      ws?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isOpen, userId]);

  // Handle WebSocket messages
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'connected':
        setOnlineUsers(data.online_users || []);
        break;
        
      case 'message':
        const channel = data.channel;
        setMessages(prev => ({
          ...prev,
          [channel]: [...(prev[channel] || []), data].slice(-100)
        }));
        
        // Update unread if not active channel
        if (channel !== activeChannel && !isMinimized) {
          setUnreadCounts(prev => ({
            ...prev,
            [channel]: (prev[channel] || 0) + 1
          }));
        }
        break;
        
      case 'presence':
        if (data.status === 'online') {
          setOnlineUsers(prev => {
            if (prev.find(u => u.user_id === data.user_id)) return prev;
            return [...prev, {
              user_id: data.user_id,
              username: data.username,
              display_name: data.display_name,
              region: data.region,
              status: 'online'
            }];
          });
        } else {
          setOnlineUsers(prev => prev.filter(u => u.user_id !== data.user_id));
        }
        break;
        
      case 'typing':
        if (data.is_typing) {
          setTypingUsers(prev => ({
            ...prev,
            [`${data.channel}_${data.user_id}`]: data.display_name
          }));
        } else {
          setTypingUsers(prev => {
            const next = { ...prev };
            delete next[`${data.channel}_${data.user_id}`];
            return next;
          });
        }
        break;
        
      case 'online_users':
        setOnlineUsers(data.users || []);
        break;
        
      case 'party_invite':
        toast.info(`${data.inviter_name} invited you to party: ${data.party_name}`, {
          action: {
            label: 'Join',
            onClick: () => joinParty(data.party_id)
          }
        });
        break;
        
      case 'user_joined_region':
        toast.info(`${data.display_name} entered the area`);
        break;
        
      case 'user_left_region':
        // Silent notification
        break;
        
      case 'error':
        toast.error(data.message);
        break;
    }
  };

  // Send message
  const sendMessage = () => {
    if (!inputValue.trim() || !ws || !connected) return;
    
    const messageData = {
      type: 'message',
      channel: activeChannel,
      content: inputValue.trim(),
      region_id: activeChannel === 'region' ? effectiveRegion : undefined,
      party_id: activeChannel === 'party' ? partyId : undefined,
      recipient_id: activeChannel === 'whisper' ? whisperTarget?.user_id : undefined
    };
    
    ws.send(JSON.stringify(messageData));
    setInputValue('');
    sendTypingIndicator(false);
  };

  // Typing indicator
  const sendTypingIndicator = (isTyping) => {
    if (!ws || !connected) return;
    
    ws.send(JSON.stringify({
      type: 'typing',
      channel: activeChannel,
      is_typing: isTyping,
      recipient_id: whisperTarget?.user_id,
      party_id: partyId
    }));
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    sendTypingIndicator(true);
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      sendTypingIndicator(false);
    }, 2000);
  };

  // Join party
  const joinParty = async (pId) => {
    try {
      await fetch(`${API}/chat/party/${pId}/join?user_id=${userId}`, { method: 'POST' });
      setPartyId(pId);
      toast.success('Joined party!');
    } catch (error) {
      toast.error('Failed to join party');
    }
  };

  // Start whisper
  const startWhisper = (user) => {
    setWhisperTarget(user);
    setActiveChannel('whisper');
  };

  // Clear unread when switching channels
  useEffect(() => {
    setUnreadCounts(prev => ({ ...prev, [activeChannel]: 0 }));
  }, [activeChannel]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeChannel]);

  // Get typing indicator text
  const getTypingText = () => {
    const channelTypers = Object.entries(typingUsers)
      .filter(([key]) => key.startsWith(activeChannel))
      .map(([, name]) => name);
    
    if (channelTypers.length === 0) return null;
    if (channelTypers.length === 1) return `${channelTypers[0]} is typing...`;
    return `${channelTypers.length} people are typing...`;
  };

  // Get total unread
  const totalUnread = Object.values(unreadCounts).reduce((a, b) => a + b, 0);

  if (!isOpen) return null;

  const ChannelIcon = CHANNEL_ICONS[activeChannel];

  // Minimized view
  if (isMinimized && !isPopOut) {
    return (
      <div 
        className="fixed bottom-4 right-4 z-50 cursor-pointer"
        onClick={() => setIsMinimized(false)}
      >
        <Card className="p-3 bg-surface/95 border-gold/30 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-gold" />
          <span className="font-medium">Chat</span>
          {totalUnread > 0 && (
            <Badge className="bg-red-500">{totalUnread}</Badge>
          )}
          <Circle className={`w-2 h-2 ${connected ? 'fill-green-400 text-green-400' : 'fill-red-400 text-red-400'}`} />
        </Card>
      </div>
    );
  }

  return (
    <Card className={`
      ${isPopOut ? 'fixed inset-4 z-50' : 'h-full max-h-[500px]'}
      bg-surface/95 backdrop-blur border-border/50 flex flex-col
    `}>
      {/* Header */}
      <div className="p-3 border-b border-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-gold" />
          <span className="font-cinzel text-gold">Multiplayer Chat</span>
          <Badge className={connected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
            <Circle className={`w-2 h-2 mr-1 ${connected ? 'fill-green-400' : 'fill-red-400'}`} />
            {connected ? `${onlineUsers.length} online` : 'Offline'}
          </Badge>
        </div>
        
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setIsMuted(!isMuted)} title={isMuted ? 'Unmute' : 'Mute'}>
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </Button>
          {!isPopOut && onPopOut && (
            <Button variant="ghost" size="icon" onClick={onPopOut} title="Pop out">
              <ExternalLink className="w-4 h-4" />
            </Button>
          )}
          {!isPopOut && (
            <Button variant="ghost" size="icon" onClick={() => setIsMinimized(true)} title="Minimize">
              <Minimize2 className="w-4 h-4" />
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose} title="Close">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Channel Tabs */}
      <Tabs value={activeChannel} onValueChange={setActiveChannel} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="mx-2 mt-2 bg-surface grid grid-cols-4">
          {['global', 'region', 'party', 'whisper'].map(channel => {
            const Icon = CHANNEL_ICONS[channel];
            const unread = unreadCounts[channel];
            return (
              <TabsTrigger key={channel} value={channel} className="relative text-xs">
                <Icon className="w-3 h-3 mr-1" />
                <span className="capitalize">{channel}</span>
                {unread > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center text-white">
                    {unread > 9 ? '9+' : unread}
                  </span>
                )}
              </TabsTrigger>
            );
          })}
        </TabsList>

        {/* Messages */}
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 flex flex-col overflow-hidden">
            <ScrollArea className="flex-1 p-3">
              <div className="space-y-2">
                {(messages[activeChannel] || []).map((msg, idx) => (
                  <div key={msg.message_id || idx} className="group">
                    <div className="flex items-start gap-2">
                      <div className="w-6 h-6 rounded-full bg-gold/20 flex items-center justify-center text-xs font-bold text-gold flex-shrink-0">
                        {msg.sender_display_name?.[0]?.toUpperCase() || '?'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span 
                            className={`font-medium text-sm cursor-pointer hover:underline ${CHANNEL_COLORS[activeChannel]}`}
                            onClick={() => msg.sender_id !== userId && startWhisper({ 
                              user_id: msg.sender_id, 
                              username: msg.sender_username,
                              display_name: msg.sender_display_name 
                            })}
                          >
                            {msg.sender_username}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          {activeChannel === 'whisper' && msg.sender_id === userId && (
                            <Badge variant="outline" className="text-xs">to {whisperTarget?.username}</Badge>
                          )}
                        </div>
                        <p className="text-sm text-foreground break-words">{msg.content}</p>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              {(messages[activeChannel] || []).length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <ChannelIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No messages in {activeChannel} chat</p>
                  {activeChannel === 'region' && !effectiveRegion && (
                    <p className="text-xs mt-1">Enter a region to chat locally</p>
                  )}
                </div>
              )}
            </ScrollArea>

            {/* Typing indicator */}
            {getTypingText() && (
              <div className="px-3 py-1 text-xs text-muted-foreground italic border-t border-border/30">
                {getTypingText()}
              </div>
            )}

            {/* Whisper target indicator */}
            {activeChannel === 'whisper' && whisperTarget && (
              <div className="px-3 py-1 bg-pink-500/10 border-t border-pink-500/20 flex items-center justify-between">
                <span className="text-xs text-pink-400">
                  Whispering to: <strong>{whisperTarget.display_name || whisperTarget.username}</strong>
                </span>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => setWhisperTarget(null)}>
                  <X className="w-3 h-3" />
                </Button>
              </div>
            )}

            {/* Input */}
            <div className="p-2 border-t border-border/30">
              <div className="flex gap-2">
                <Input
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder={
                    activeChannel === 'whisper' && !whisperTarget 
                      ? 'Click a name to whisper...'
                      : activeChannel === 'party' && !partyId
                      ? 'Join a party first...'
                      : `Message ${activeChannel}...`
                  }
                  disabled={!connected || (activeChannel === 'whisper' && !whisperTarget) || (activeChannel === 'party' && !partyId)}
                  className="flex-1 h-8 text-sm"
                  data-testid="chat-input"
                />
                <Button 
                  onClick={sendMessage}
                  disabled={!connected || !inputValue.trim()}
                  size="sm"
                  className="bg-gold text-black hover:bg-gold-light h-8 px-3"
                  data-testid="send-message-btn"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Online Users Sidebar (only in popout) */}
          {isPopOut && (
            <div className="w-48 border-l border-border/30 flex flex-col">
              <div className="p-2 border-b border-border/30">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Online ({onlineUsers.length})
                </h4>
              </div>
              <ScrollArea className="flex-1 p-2">
                <div className="space-y-1">
                  {onlineUsers.map(user => (
                    <div 
                      key={user.user_id}
                      className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                        user.user_id === userId ? 'bg-gold/10' : 'hover:bg-black/20'
                      }`}
                      onClick={() => user.user_id !== userId && startWhisper(user)}
                    >
                      <Circle className="w-2 h-2 fill-green-400 text-green-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm truncate">
                          {user.username}
                          {user.user_id === userId && <span className="text-xs text-muted-foreground"> (you)</span>}
                        </div>
                        {user.region && (
                          <div className="text-xs text-muted-foreground truncate">
                            {user.region.replace(/_/g, ' ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {onlineUsers.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-4">No other players online</p>
                  )}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>
      </Tabs>
    </Card>
  );
};

export default MultiplayerChat;
