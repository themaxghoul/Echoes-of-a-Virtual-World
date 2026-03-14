import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Users, Crown, Shield, Sword, ArrowLeft, Plus, 
  LogOut, Settings, Star, Gem
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GUILD_TYPE_ICONS = {
  trade: '💰',
  combat: '⚔️',
  crafting: '🔨',
  exploration: '🗺️',
  mystical: '✨'
};

const GUILD_TYPE_COLORS = {
  trade: 'from-yellow-600 to-amber-500',
  combat: 'from-red-600 to-orange-500',
  crafting: 'from-blue-600 to-cyan-500',
  exploration: 'from-green-600 to-emerald-500',
  mystical: 'from-purple-600 to-pink-500'
};

const GuildPage = () => {
  const navigate = useNavigate();
  const [guilds, setGuilds] = useState([]);
  const [guildTypes, setGuildTypes] = useState({});
  const [userProfile, setUserProfile] = useState(null);
  const [userGuild, setUserGuild] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Create guild form
  const [newGuild, setNewGuild] = useState({
    name: '',
    tag: '',
    guild_type: 'trade',
    description: ''
  });
  
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    const userId = localStorage.getItem('userId');
    if (!userId) {
      navigate('/auth');
      return;
    }
    
    try {
      const [guildsRes, typesRes, userRes] = await Promise.all([
        axios.get(`${API}/guilds`),
        axios.get(`${API}/guild-types`),
        axios.get(`${API}/users/id/${userId}`)
      ]);
      
      setGuilds(guildsRes.data || []);
      setGuildTypes(typesRes.data || {});
      setUserProfile(userRes.data);
      
      // Check if user is in a guild
      if (userRes.data?.guild_id) {
        const guildRes = await axios.get(`${API}/guilds/${userRes.data.guild_id}`);
        setUserGuild(guildRes.data);
      }
    } catch (error) {
      console.error('Failed to load guilds:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleCreateGuild = async () => {
    if (!newGuild.name || !newGuild.tag) {
      toast.error('Please fill in guild name and tag');
      return;
    }
    
    try {
      const res = await axios.post(`${API}/guilds`, {
        ...newGuild,
        founder_id: userProfile.id
      });
      
      toast.success(`Guild "${res.data.name}" created!`);
      setShowCreateModal(false);
      setUserGuild(res.data);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create guild');
    }
  };
  
  const handleJoinGuild = async (guildId) => {
    try {
      await axios.post(`${API}/guilds/${guildId}/join?user_id=${userProfile.id}`);
      toast.success('Joined guild!');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join guild');
    }
  };
  
  const handleLeaveGuild = async () => {
    if (!userGuild) return;
    
    try {
      await axios.post(`${API}/guilds/${userGuild.id}/leave?user_id=${userProfile.id}`);
      toast.success('Left guild');
      setUserGuild(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to leave guild');
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-gold font-cinzel text-xl animate-pulse">Loading guilds...</div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="border-b border-border/30 bg-surface/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              data-testid="back-btn"
              onClick={() => navigate(-1)}
              variant="ghost"
              size="icon"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Users className="w-6 h-6" />
                Guild Hall
              </h1>
              <p className="text-sm text-muted-foreground">Join forces, conquer together</p>
            </div>
          </div>
          
          {!userGuild && (
            <Button
              data-testid="create-guild-btn"
              onClick={() => setShowCreateModal(true)}
              className="bg-gold text-black hover:bg-gold-light"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Guild
            </Button>
          )}
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-8">
        {/* User's Guild */}
        {userGuild && (
          <div className="mb-8">
            <h2 className="font-cinzel text-xl text-gold mb-4">Your Guild</h2>
            <Card className={`bg-gradient-to-br ${GUILD_TYPE_COLORS[userGuild.guild_type]} p-6 rounded-sm`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{GUILD_TYPE_ICONS[userGuild.guild_type]}</span>
                    <div>
                      <h3 className="font-cinzel text-2xl text-white">{userGuild.name}</h3>
                      <Badge className="bg-black/30 text-white">[{userGuild.tag}]</Badge>
                    </div>
                  </div>
                  <p className="text-white/80 mt-2">{userGuild.description || 'No description'}</p>
                  
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{Object.keys(userGuild.members || {}).length}</div>
                      <div className="text-xs text-white/60">Members</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{userGuild.level || 1}</div>
                      <div className="text-xs text-white/60">Level</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-white">{userGuild.treasury || 0}</div>
                      <div className="text-xs text-white/60">Treasury</div>
                    </div>
                  </div>
                  
                  {/* Bonuses */}
                  <div className="mt-4 p-3 bg-black/20 rounded-sm">
                    <div className="text-xs text-white/60 mb-2">Guild Bonuses</div>
                    <div className="flex flex-wrap gap-2">
                      {userGuild.bonuses && Object.entries(userGuild.bonuses).map(([key, value]) => (
                        <Badge key={key} className="bg-white/20 text-white text-xs">
                          {key.replace(/_/g, ' ')}: {value > 1 ? `+${Math.round((value - 1) * 100)}%` : `-${Math.round((1 - value) * 100)}%`}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-col gap-2">
                  <Badge className="bg-white/20 text-white">
                    <Crown className="w-3 h-3 mr-1" />
                    {userProfile?.guild_rank || 'Member'}
                  </Badge>
                  <Button
                    data-testid="leave-guild-btn"
                    onClick={handleLeaveGuild}
                    variant="outline"
                    size="sm"
                    className="text-white border-white/30 hover:bg-white/10"
                  >
                    <LogOut className="w-4 h-4 mr-1" />
                    Leave
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
        
        {/* Available Guilds */}
        <div>
          <h2 className="font-cinzel text-xl text-gold mb-4">
            {userGuild ? 'Other Guilds' : 'Available Guilds'}
          </h2>
          
          {guilds.length === 0 ? (
            <Card className="bg-surface/50 border-border/30 p-8 text-center rounded-sm">
              <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No guilds exist yet. Be the first to create one!</p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {guilds.filter(g => g.id !== userGuild?.id).map((guild) => (
                <Card 
                  key={guild.id}
                  className="bg-surface/50 border-border/30 p-4 rounded-sm hover:border-gold/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-12 h-12 rounded-sm bg-gradient-to-br ${GUILD_TYPE_COLORS[guild.guild_type]} flex items-center justify-center text-2xl`}>
                      {GUILD_TYPE_ICONS[guild.guild_type]}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-cinzel text-lg text-foreground">{guild.name}</h3>
                        <Badge className="bg-gold/20 text-gold text-xs">[{guild.tag}]</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {guild.description || `A ${guild.guild_type} guild`}
                      </p>
                      
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span><Users className="w-3 h-3 inline mr-1" />{Object.keys(guild.members || {}).length} members</span>
                        <span><Star className="w-3 h-3 inline mr-1" />Lvl {guild.level || 1}</span>
                      </div>
                      
                      {!userGuild && (
                        <Button
                          data-testid={`join-guild-${guild.id}`}
                          onClick={() => handleJoinGuild(guild.id)}
                          size="sm"
                          className="mt-3 bg-gold/20 text-gold hover:bg-gold/30"
                        >
                          Join Guild
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
        
        {/* Guild Types Info */}
        <div className="mt-12">
          <h2 className="font-cinzel text-xl text-gold mb-4">Guild Types</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
            {Object.entries(guildTypes).map(([type, data]) => (
              <Card key={type} className="bg-surface/30 border-border/30 p-4 rounded-sm">
                <div className="text-3xl mb-2">{GUILD_TYPE_ICONS[type]}</div>
                <h3 className="font-cinzel text-foreground capitalize">{type}</h3>
                <p className="text-xs text-muted-foreground">Focus: {data.focus}</p>
                <div className="mt-2 space-y-1">
                  {data.bonuses && Object.entries(data.bonuses).map(([key, value]) => (
                    <div key={key} className="text-xs text-gold">
                      {key.replace(/_/g, ' ')}: {value > 1 ? `+${Math.round((value - 1) * 100)}%` : `-${Math.round((1 - value) * 100)}%`}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
      
      {/* Create Guild Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <Card className="bg-surface border-border/50 w-full max-w-md mx-4 p-6 rounded-sm">
            <h2 className="font-cinzel text-2xl text-gold mb-6">Create a Guild</h2>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground">Guild Name</label>
                <Input
                  data-testid="guild-name-input"
                  value={newGuild.name}
                  onChange={(e) => setNewGuild(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter guild name..."
                  className="bg-obsidian border-border/50"
                />
              </div>
              
              <div>
                <label className="text-sm text-muted-foreground">Tag (3-5 characters)</label>
                <Input
                  data-testid="guild-tag-input"
                  value={newGuild.tag}
                  onChange={(e) => setNewGuild(prev => ({ ...prev, tag: e.target.value.toUpperCase().slice(0, 5) }))}
                  placeholder="ABC"
                  maxLength={5}
                  className="bg-obsidian border-border/50"
                />
              </div>
              
              <div>
                <label className="text-sm text-muted-foreground">Guild Type</label>
                <div className="grid grid-cols-5 gap-2 mt-2">
                  {Object.keys(guildTypes).map((type) => (
                    <button
                      key={type}
                      data-testid={`type-${type}`}
                      onClick={() => setNewGuild(prev => ({ ...prev, guild_type: type }))}
                      className={`p-3 rounded-sm text-2xl transition-all ${
                        newGuild.guild_type === type 
                          ? `bg-gradient-to-br ${GUILD_TYPE_COLORS[type]} ring-2 ring-gold` 
                          : 'bg-surface/50 hover:bg-surface'
                      }`}
                    >
                      {GUILD_TYPE_ICONS[type]}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="text-sm text-muted-foreground">Description (optional)</label>
                <Input
                  data-testid="guild-desc-input"
                  value={newGuild.description}
                  onChange={(e) => setNewGuild(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe your guild..."
                  className="bg-obsidian border-border/50"
                />
              </div>
              
              <div className="flex gap-3 mt-6">
                <Button
                  data-testid="cancel-create-btn"
                  onClick={() => setShowCreateModal(false)}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  data-testid="confirm-create-btn"
                  onClick={handleCreateGuild}
                  className="flex-1 bg-gold text-black hover:bg-gold-light"
                >
                  Create Guild
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default GuildPage;
