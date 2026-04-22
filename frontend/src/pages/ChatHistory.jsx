import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  MessageSquare, Search, Calendar, User, MapPin, Clock,
  ChevronRight, Play, ArrowLeft, History, Filter, X,
  Loader2, MessageCircle, Users, Globe, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory, GameNavigation } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// NPC Avatar colors
const NPC_COLORS = {
  'Elder Morvain': 'bg-gold/20 text-gold border-gold/30',
  'Lyra the Wanderer': 'bg-slate-blue/20 text-slate-blue border-slate-blue/30',
  'Kael Ironbrand': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'Archivist Nyx': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  'Innkeeper Mara': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  'Oracle Veythra': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  'The Grove Keeper': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  'default': 'bg-surface text-muted-foreground border-border/30'
};

const ChatHistory = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [groupBy, setGroupBy] = useState('npc'); // 'npc' or 'session'
  const [conversations, setConversations] = useState([]);
  const [stats, setStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  
  const userId = localStorage.getItem('userId');

  useEffect(() => {
    pushNavHistory('/chat-history');
    loadData();
  }, [groupBy]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [convsRes, statsRes] = await Promise.all([
        axios.get(`${API}/conversations/player/${userId}?group_by=${groupBy}`),
        axios.get(`${API}/conversations/player/${userId}/stats`)
      ]);
      
      setConversations(convsRes.data.groups || []);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      toast.error('Failed to load chat history');
    }
    setLoading(false);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    
    try {
      const res = await axios.get(`${API}/conversations/player/${userId}/search?query=${encodeURIComponent(searchQuery)}`);
      setSearchResults(res.data);
    } catch (error) {
      toast.error('Search failed');
    }
  };

  const loadConversationDetail = async (conversationId) => {
    setLoadingMessages(true);
    try {
      const res = await axios.get(`${API}/conversations/${conversationId}`);
      setSelectedConversation(res.data.conversation);
      setConversationMessages(res.data.conversation.messages || []);
    } catch (error) {
      toast.error('Failed to load conversation');
    }
    setLoadingMessages(false);
  };

  const resumeConversation = async (conversationId) => {
    try {
      const res = await axios.post(`${API}/conversations/resume`, {
        conversation_id: conversationId,
        player_id: userId
      });
      
      if (res.data.resumed) {
        // Store resume context in localStorage
        localStorage.setItem('resumeConversation', JSON.stringify(res.data));
        toast.success('Resuming conversation...');
        
        // Navigate to village explorer
        navigate('/village');
      }
    } catch (error) {
      toast.error('Failed to resume conversation');
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    });
  };

  const formatTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const getRelativeTime = (isoString) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(isoString);
  };

  const getNpcColor = (npcName) => {
    return NPC_COLORS[npcName] || NPC_COLORS.default;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <History className="w-16 h-16 mx-auto text-gold animate-pulse mb-4" />
          <p className="font-cinzel text-gold">Loading Chat History...</p>
        </div>
      </div>
    );
  }

  // Conversation Detail View
  if (selectedConversation) {
    return (
      <div className="min-h-screen bg-obsidian flex flex-col">
        <div className="fixed inset-0 opacity-10">
          <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/90 to-obsidian" />
        </div>

        {/* Header */}
        <header className="relative z-10 glass border-b border-border/30 p-4">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setSelectedConversation(null);
                  setConversationMessages([]);
                }}
                className="rounded-sm"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="font-cinzel text-lg text-foreground">
                  {selectedConversation.npc_name || 'Conversation'}
                </h1>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {selectedConversation.location_name}
                </p>
              </div>
            </div>
            <Button
              onClick={() => resumeConversation(selectedConversation.conversation_id)}
              className="bg-gold text-black hover:bg-gold-light"
              data-testid="resume-conversation-btn"
            >
              <Play className="w-4 h-4 mr-2" />
              Resume
            </Button>
          </div>
        </header>

        {/* Messages */}
        <ScrollArea className="flex-1 p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Conversation Info */}
            <Card className="bg-surface/50 border-border/30">
              <CardContent className="p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    Started {formatDate(selectedConversation.started_at)} at {formatTime(selectedConversation.started_at)}
                  </span>
                  <Badge className="bg-surface text-muted-foreground">
                    {conversationMessages.length} messages
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Messages List */}
            {loadingMessages ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-gold" />
              </div>
            ) : (
              conversationMessages.map((msg, index) => (
                <div
                  key={msg.message_id || index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <Card className={`max-w-[80%] ${
                    msg.role === 'user' 
                      ? 'bg-gold/10 border-gold/30' 
                      : msg.role === 'narrator'
                        ? 'bg-slate-blue/10 border-slate-blue/30'
                        : 'bg-surface/80 border-border/50'
                  }`}>
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-cinzel ${
                          msg.role === 'user' ? 'text-gold' : 
                          msg.role === 'narrator' ? 'text-slate-blue' : 'text-muted-foreground'
                        }`}>
                          {msg.role === 'user' ? 'You' : 
                           msg.role === 'narrator' ? 'Narrator' : 
                           selectedConversation.npc_name || 'NPC'}
                        </span>
                        <span className="text-xs text-muted-foreground/50">
                          {formatTime(msg.timestamp)}
                        </span>
                      </div>
                      <p className={`text-sm whitespace-pre-wrap ${
                        msg.role === 'narrator' ? 'italic text-foreground/80' : 'text-foreground'
                      }`}>
                        {msg.content}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              ))
            )}

            {/* Resume Button at Bottom */}
            <div className="flex justify-center py-6">
              <Button
                onClick={() => resumeConversation(selectedConversation.conversation_id)}
                className="bg-gold text-black hover:bg-gold-light"
                size="lg"
              >
                <Play className="w-5 h-5 mr-2" />
                Continue This Conversation
              </Button>
            </div>
          </div>
        </ScrollArea>
      </div>
    );
  }

  // Main List View
  return (
    <div className="min-h-screen bg-obsidian flex flex-col">
      <div className="fixed inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/90 to-obsidian" />
      </div>

      <GameNavigation 
        title="Chat History" 
        showBack={true} 
        showHome={true}
      />

      <main className="relative z-10 flex-1 p-4 sm:p-6 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Card className="bg-surface/50 border-border/30">
                <CardContent className="p-4 text-center">
                  <MessageSquare className="w-6 h-6 mx-auto text-gold mb-2" />
                  <p className="font-mono text-xl text-foreground">{stats.total_conversations || 0}</p>
                  <p className="text-xs text-muted-foreground">Conversations</p>
                </CardContent>
              </Card>
              <Card className="bg-surface/50 border-border/30">
                <CardContent className="p-4 text-center">
                  <MessageCircle className="w-6 h-6 mx-auto text-slate-blue mb-2" />
                  <p className="font-mono text-xl text-foreground">{stats.total_messages || 0}</p>
                  <p className="text-xs text-muted-foreground">Messages</p>
                </CardContent>
              </Card>
              <Card className="bg-surface/50 border-border/30">
                <CardContent className="p-4 text-center">
                  <Users className="w-6 h-6 mx-auto text-purple-400 mb-2" />
                  <p className="font-mono text-xl text-foreground">{stats.unique_npcs_count || 0}</p>
                  <p className="text-xs text-muted-foreground">NPCs Met</p>
                </CardContent>
              </Card>
              <Card className="bg-surface/50 border-border/30">
                <CardContent className="p-4 text-center">
                  <Globe className="w-6 h-6 mx-auto text-green-400 mb-2" />
                  <p className="font-mono text-xl text-foreground">{stats.unique_locations_count || 0}</p>
                  <p className="text-xs text-muted-foreground">Locations</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Search Bar */}
          <Card className="bg-surface/50 border-border/30">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="Search conversations..."
                    className="pl-10 bg-obsidian/50 border-border/50"
                    data-testid="search-conversations-input"
                  />
                </div>
                <Button 
                  onClick={handleSearch}
                  className="bg-slate-blue hover:bg-slate-blue-light"
                >
                  Search
                </Button>
                {searchResults && (
                  <Button 
                    variant="ghost"
                    onClick={() => {
                      setSearchResults(null);
                      setSearchQuery('');
                    }}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Search Results */}
          {searchResults && (
            <Card className="bg-surface/80 border-border/50">
              <CardHeader>
                <CardTitle className="font-cinzel text-lg flex items-center justify-between">
                  <span>Search Results for "{searchResults.query}"</span>
                  <Badge>{searchResults.total_results} found</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {searchResults.results.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No conversations found</p>
                ) : (
                  searchResults.results.map((result) => (
                    <button
                      key={result.conversation_id}
                      onClick={() => loadConversationDetail(result.conversation_id)}
                      className="w-full text-left p-3 bg-obsidian/30 rounded-sm border border-border/30 hover:border-gold/30 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-cinzel text-foreground">{result.npc_name}</span>
                        <Badge className="text-xs">{result.total_matches} matches</Badge>
                      </div>
                      {result.matching_messages.slice(0, 2).map((msg, i) => (
                        <p key={i} className="text-sm text-muted-foreground line-clamp-1">
                          ...{msg.content.slice(0, 100)}...
                        </p>
                      ))}
                    </button>
                  ))
                )}
              </CardContent>
            </Card>
          )}

          {/* Group Toggle */}
          {!searchResults && (
            <Tabs value={groupBy} onValueChange={setGroupBy} className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-surface/50">
                <TabsTrigger value="npc" className="font-cinzel">
                  <Users className="w-4 h-4 mr-2" />
                  By NPC
                </TabsTrigger>
                <TabsTrigger value="session" className="font-cinzel">
                  <Calendar className="w-4 h-4 mr-2" />
                  By Date
                </TabsTrigger>
              </TabsList>

              {/* NPC Grouped View */}
              <TabsContent value="npc" className="mt-6 space-y-4">
                {conversations.length === 0 ? (
                  <Card className="bg-surface/50 border-border/30">
                    <CardContent className="p-8 text-center">
                      <History className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                      <h3 className="font-cinzel text-lg text-foreground mb-2">No Conversations Yet</h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        Start chatting with NPCs in Story Mode to build your history
                      </p>
                      <Button onClick={() => navigate('/village')} className="bg-gold text-black hover:bg-gold-light">
                        Enter Story Mode
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  conversations.map((group) => (
                    <Card key={group.npc_id || group.npc_name} className="bg-surface/80 border-border/50">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center border ${getNpcColor(group.npc_name)}`}>
                              <User className="w-5 h-5" />
                            </div>
                            <div>
                              <CardTitle className="font-cinzel text-lg">{group.npc_name}</CardTitle>
                              <p className="text-xs text-muted-foreground">
                                {group.total_messages} messages across {group.conversations.length} conversations
                              </p>
                            </div>
                          </div>
                          <Badge className="bg-surface text-muted-foreground">
                            {getRelativeTime(group.last_interaction)}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {group.conversations.slice(0, 3).map((conv) => (
                          <button
                            key={conv.conversation_id}
                            onClick={() => loadConversationDetail(conv.conversation_id)}
                            className="w-full text-left p-3 bg-obsidian/30 rounded-sm border border-border/30 hover:border-gold/30 transition-colors group"
                            data-testid={`conversation-${conv.conversation_id}`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm text-muted-foreground flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                {conv.location_name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(conv.last_message_at)}
                              </span>
                            </div>
                            <p className="text-sm text-foreground/80 line-clamp-1">
                              {conv.preview || 'No messages'}
                            </p>
                            <div className="flex items-center justify-between mt-2">
                              <Badge variant="outline" className="text-xs">
                                {conv.message_count} messages
                              </Badge>
                              <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-gold transition-colors" />
                            </div>
                          </button>
                        ))}
                        {group.conversations.length > 3 && (
                          <p className="text-xs text-muted-foreground text-center py-2">
                            +{group.conversations.length - 3} more conversations
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ))
                )}
              </TabsContent>

              {/* Session/Date Grouped View */}
              <TabsContent value="session" className="mt-6 space-y-4">
                {conversations.length === 0 ? (
                  <Card className="bg-surface/50 border-border/30">
                    <CardContent className="p-8 text-center">
                      <Calendar className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                      <h3 className="font-cinzel text-lg text-foreground mb-2">No Sessions Yet</h3>
                      <p className="text-sm text-muted-foreground">
                        Your conversation history will appear here
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  conversations.map((group) => (
                    <Card key={group.date} className="bg-surface/80 border-border/50">
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="font-cinzel text-lg flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-gold" />
                            {new Date(group.date).toLocaleDateString('en-US', { 
                              weekday: 'long', 
                              month: 'long', 
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </CardTitle>
                          <Badge className="bg-surface text-muted-foreground">
                            {group.total_messages} messages
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {group.conversations.map((conv) => (
                          <button
                            key={conv.conversation_id}
                            onClick={() => loadConversationDetail(conv.conversation_id)}
                            className="w-full text-left p-3 bg-obsidian/30 rounded-sm border border-border/30 hover:border-gold/30 transition-colors group"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-cinzel text-sm text-foreground">
                                {conv.npc_name || 'Unknown NPC'}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatTime(conv.started_at)}
                              </span>
                            </div>
                            <p className="text-sm text-muted-foreground flex items-center gap-1 mb-1">
                              <MapPin className="w-3 h-3" />
                              {conv.location_name}
                            </p>
                            <p className="text-sm text-foreground/80 line-clamp-1">
                              {conv.preview || 'No messages'}
                            </p>
                            <div className="flex items-center justify-between mt-2">
                              <Badge variant="outline" className="text-xs">
                                {conv.message_count} messages
                              </Badge>
                              <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-gold transition-colors" />
                            </div>
                          </button>
                        ))}
                      </CardContent>
                    </Card>
                  ))
                )}
              </TabsContent>
            </Tabs>
          )}

          {/* Quick Action */}
          <div className="flex justify-center pt-4">
            <Button
              variant="outline"
              onClick={() => navigate('/village')}
              className="border-gold/30 text-gold hover:bg-gold/10"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Start New Conversation
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ChatHistory;
