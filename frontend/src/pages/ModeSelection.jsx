import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Gamepad2, MessageSquare, User, Sparkles, Crown,
  ArrowRight, Settings, LogOut, Hammer, ArrowLeftRight,
  Heart, Zap, Shield, Swords, DollarSign, TrendingUp, Briefcase
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ModeSelection = () => {
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [playerStats, setPlayerStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    pushNavHistory('/select-mode');
    loadData();
  }, []);

  const loadData = async () => {
    const charId = localStorage.getItem('currentCharacterId');
    const userId = localStorage.getItem('userId');
    
    if (!userId) {
      navigate('/auth');
      return;
    }

    if (!charId) {
      navigate('/create-character');
      return;
    }

    try {
      const [charRes, userRes, statsRes] = await Promise.all([
        axios.get(`${API}/character/${charId}`),
        axios.get(`${API}/users/id/${userId}`),
        axios.get(`${API}/users/stats/${userId}`).catch(() => ({ data: null }))
      ]);
      
      setCharacter(charRes.data);
      setUserProfile(userRes.data);
      if (statsRes?.data) setPlayerStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load:', error);
      if (error.response?.status === 404) {
        navigate('/create-character');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    toast.success('Logged out successfully');
    navigate('/auth');
  };

  const selectMode = (mode, path) => {
    localStorage.setItem('gameMode', mode);
    pushNavHistory(path);
    navigate(path);
  };

  const isTranscendent = userProfile?.is_transcendent || localStorage.getItem('isTranscendent') === 'true';

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-gold border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="font-cinzel text-gold">Loading your journey...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian flex flex-col">
      {/* Background */}
      <div 
        className="fixed inset-0 bg-cover bg-center opacity-20"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1920&q=80')`,
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/90 to-obsidian" />
      </div>

      {/* Header */}
      <header className="relative z-10 p-4 sm:p-6 flex justify-between items-center border-b border-border/30">
        <div className="flex items-center gap-3">
          {userProfile && (
            <>
              <div className={`w-10 h-10 rounded-sm flex items-center justify-center ${
                isTranscendent 
                  ? 'bg-gradient-to-br from-purple-500/30 to-gold/30 border border-purple-500/50' 
                  : 'bg-gold/20 border border-gold/30'
              }`}>
                {isTranscendent ? (
                  <Crown className="w-5 h-5 text-purple-400" />
                ) : (
                  <User className="w-5 h-5 text-gold" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-cinzel text-sm text-foreground">{userProfile.display_name}</p>
                  {isTranscendent && (
                    <Badge className="bg-purple-500/20 text-purple-400 text-xs px-1">SIRIX-1</Badge>
                  )}
                </div>
                <p className="font-mono text-xs text-muted-foreground">@{userProfile.username}</p>
              </div>
            </>
          )}
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              pushNavHistory('/profile');
              navigate('/profile');
            }}
            className="rounded-sm"
            data-testid="profile-btn"
          >
            <Settings className="w-5 h-5 text-muted-foreground" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="rounded-sm text-red-400 hover:text-red-300 hover:bg-red-400/10"
            data-testid="logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center px-4 sm:px-6 py-8 overflow-y-auto">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="font-cinzel text-2xl sm:text-3xl text-foreground mb-2">
            Choose Your Path
          </h1>
          <p className="font-manrope text-sm text-muted-foreground">
            How would you like to experience The Echoes?
          </p>
        </div>

        {/* Character & Stats Card */}
        {character && (
          <Card className="bg-surface/80 border-border/50 rounded-sm mb-8 max-w-md w-full">
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-start gap-4">
                {/* Character Avatar */}
                <div className="w-16 h-16 sm:w-20 sm:h-20 relative flex-shrink-0">
                  <svg viewBox="0 0 100 100" className="w-full h-full">
                    <polygon 
                      points="50,10 80,35 75,70 50,90 25,70 20,35" 
                      fill={isTranscendent ? '#8B5CF6' : '#D4AF37'}
                      fillOpacity="0.3"
                      stroke={isTranscendent ? '#8B5CF6' : '#D4AF37'}
                      strokeWidth="2"
                    />
                    <circle cx="50" cy="40" r="15" fill="#0F0F11" stroke={isTranscendent ? '#8B5CF6' : '#D4AF37'} strokeWidth="1" />
                    <circle cx="44" cy="38" r="2" fill={isTranscendent ? '#8B5CF6' : '#D4AF37'} />
                    <circle cx="56" cy="38" r="2" fill={isTranscendent ? '#8B5CF6' : '#D4AF37'} />
                  </svg>
                </div>
                
                <div className="flex-1 min-w-0">
                  <h3 className="font-cinzel text-lg text-gold truncate">{character.name}</h3>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {character.traits?.slice(0, 2).map((trait, i) => (
                      <Badge key={i} className="bg-gold/10 text-gold/80 text-xs rounded-sm">
                        {trait}
                      </Badge>
                    ))}
                  </div>
                  
                  {/* Stats Bars */}
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <Heart className="w-3 h-3 text-red-400" />
                      <Progress 
                        value={(character.health / character.max_health) * 100} 
                        className="h-1.5 flex-1" 
                      />
                      <span className="text-xs text-muted-foreground w-12 text-right">
                        {isTranscendent ? '∞' : `${character.health}/${character.max_health}`}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Zap className="w-3 h-3 text-yellow-400" />
                      <Progress 
                        value={(character.stamina / character.max_stamina) * 100} 
                        className="h-1.5 flex-1" 
                      />
                      <span className="text-xs text-muted-foreground w-12 text-right">
                        {isTranscendent ? '∞' : `${Math.round(character.stamina)}/${character.max_stamina}`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Quick Stats */}
              <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-border/30">
                <div className="text-center">
                  <Swords className="w-4 h-4 mx-auto text-red-400 mb-1" />
                  <span className="text-xs text-muted-foreground">STR</span>
                  <p className="font-mono text-sm text-foreground">{isTranscendent ? '∞' : character.strength}</p>
                </div>
                <div className="text-center">
                  <Shield className="w-4 h-4 mx-auto text-blue-400 mb-1" />
                  <span className="text-xs text-muted-foreground">DEF</span>
                  <p className="font-mono text-sm text-foreground">{isTranscendent ? '∞' : character.endurance}</p>
                </div>
                <div className="text-center">
                  <Zap className="w-4 h-4 mx-auto text-yellow-400 mb-1" />
                  <span className="text-xs text-muted-foreground">AGI</span>
                  <p className="font-mono text-sm text-foreground">{isTranscendent ? '∞' : character.agility}</p>
                </div>
                <div className="text-center">
                  <Sparkles className="w-4 h-4 mx-auto text-purple-400 mb-1" />
                  <span className="text-xs text-muted-foreground">INT</span>
                  <p className="font-mono text-sm text-foreground">{isTranscendent ? '∞' : character.intelligence}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Mode Selection */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 max-w-5xl w-full">
          {/* 2D Story Mode - Text Adventure with Building */}
          <Card 
            className="bg-surface/80 border-border/50 rounded-sm hover:border-gold/50 transition-all duration-300 cursor-pointer group"
            onClick={() => selectMode('story', '/village')}
            data-testid="story-mode-card"
          >
            <CardContent className="p-6 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gold/20 border border-gold/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <MessageSquare className="w-8 h-8 text-gold" />
              </div>
              <h3 className="font-cinzel text-lg text-foreground mb-2">Story Mode</h3>
              <p className="font-manrope text-sm text-muted-foreground mb-4">
                Text adventure with AI storytelling. Build your 2D world, chat with NPCs.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-4">
                <Badge className="bg-gold/10 text-gold text-xs rounded-sm">AI Narrator</Badge>
                <Badge className="bg-gold/10 text-gold text-xs rounded-sm">All Maps Open</Badge>
              </div>
              <Button 
                data-testid="select-storymode-btn"
                className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
              >
                <MessageSquare className="w-5 h-5 mr-2" />
                Enter Story Mode
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>

          {/* 3D First Person Mode (Web) */}
          <Card 
            className="bg-surface/80 border-border/50 rounded-sm hover:border-slate-blue/50 transition-all duration-300 cursor-pointer group"
            onClick={() => selectMode('firstperson', '/play')}
            data-testid="firstperson-mode-card"
          >
            <CardContent className="p-6 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-blue/20 border border-slate-blue/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Gamepad2 className="w-8 h-8 text-slate-blue" />
              </div>
              <h3 className="font-cinzel text-lg text-foreground mb-2">First Person 3D</h3>
              <p className="font-manrope text-sm text-muted-foreground mb-4">
                Immersive 3D in browser. Walk through the village, interact with NPCs.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-4">
                <Badge className="bg-slate-blue/10 text-slate-blue text-xs rounded-sm">Web 3D</Badge>
                <Badge className="bg-slate-blue/10 text-slate-blue text-xs rounded-sm">D-Pad</Badge>
              </div>
              <Button 
                data-testid="select-firstperson-btn"
                className="w-full bg-slate-blue text-white hover:bg-slate-blue-light font-cinzel rounded-sm"
              >
                <Gamepad2 className="w-5 h-5 mr-2" />
                Enter 3D Web
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>

          {/* Unity First Person Mode */}
          <Card 
            className="bg-surface/80 border-border/50 rounded-sm hover:border-purple-500/50 transition-all duration-300 cursor-pointer group"
            onClick={() => selectMode('unity', '/unity')}
            data-testid="unity-mode-card"
          >
            <CardContent className="p-6 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Gamepad2 className="w-8 h-8 text-purple-400" />
              </div>
              <h3 className="font-cinzel text-lg text-foreground mb-2">Unity 3D</h3>
              <p className="font-manrope text-sm text-muted-foreground mb-4">
                High-fidelity Unity client. Download and play with full graphics.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-4">
                <Badge className="bg-purple-500/10 text-purple-400 text-xs rounded-sm">Hi-Fi 3D</Badge>
                <Badge className="bg-purple-500/10 text-purple-400 text-xs rounded-sm">Sync</Badge>
              </div>
              <Button 
                data-testid="select-unity-btn"
                className="w-full bg-purple-600 text-white hover:bg-purple-500 font-cinzel rounded-sm"
              >
                <Gamepad2 className="w-5 h-5 mr-2" />
                Unity Offload
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Quick Access */}
        <div className="flex flex-wrap gap-3 mt-8 justify-center">
          <Button
            variant="outline"
            onClick={() => {
              pushNavHistory('/jobs');
              navigate('/jobs');
            }}
            className="border-blue-400/30 text-blue-400 hover:bg-blue-400/10 rounded-sm"
            data-testid="jobs-btn"
          >
            <Briefcase className="w-4 h-4 mr-2" />
            Career Hub
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              pushNavHistory('/building');
              navigate('/building');
            }}
            className="border-gold/30 text-gold hover:bg-gold/10 rounded-sm"
            data-testid="building-btn"
          >
            <Hammer className="w-4 h-4 mr-2" />
            2D Builder
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              pushNavHistory('/trading');
              navigate('/trading');
            }}
            className="border-amber-400/30 text-amber-400 hover:bg-amber-400/10 rounded-sm"
          >
            <ArrowLeftRight className="w-4 h-4 mr-2" />
            Trading
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              pushNavHistory('/earnings');
              navigate('/earnings');
            }}
            className="border-green-400/30 text-green-400 hover:bg-green-400/10 rounded-sm"
            data-testid="earnings-btn"
          >
            <DollarSign className="w-4 h-4 mr-2" />
            Earn VE$
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              pushNavHistory('/quests');
              navigate('/quests');
            }}
            className="border-purple-400/30 text-purple-400 hover:bg-purple-400/10 rounded-sm"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Quests
          </Button>
        </div>

        {/* Player Stats Summary */}
        {playerStats && (
          <Card className="bg-surface/50 border-border/30 rounded-sm mt-8 max-w-md w-full">
            <CardContent className="p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Session Stats
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 mt-3">
                <div className="text-center">
                  <p className="font-mono text-lg text-foreground">{playerStats.total_logins || 0}</p>
                  <p className="text-xs text-muted-foreground">Logins</p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-lg text-foreground">{playerStats.quests_completed || 0}</p>
                  <p className="text-xs text-muted-foreground">Quests</p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-lg text-foreground">{playerStats.npcs_talked || 0}</p>
                  <p className="text-xs text-muted-foreground">NPCs Met</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 p-4 text-center border-t border-border/30">
        <p className="font-mono text-xs text-muted-foreground/50">
          Story Mode = 2D Chat + Building | First Person = 3D Models
        </p>
      </footer>
    </div>
  );
};

export default ModeSelection;
