import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Gamepad2, MessageSquare, User, Sparkles, 
  ArrowRight, Settings, LogOut, Hammer, ArrowLeftRight
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ModeSelection = () => {
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      const charId = localStorage.getItem('currentCharacterId');
      const userId = localStorage.getItem('userId');
      
      if (!charId) {
        navigate('/create-character');
        return;
      }

      try {
        const [charRes, userRes] = await Promise.all([
          axios.get(`${API}/character/${charId}`),
          userId ? axios.get(`${API}/users/id/${userId}`) : null
        ]);
        
        setCharacter(charRes.data);
        if (userRes?.data) setUserProfile(userRes.data);
      } catch (error) {
        console.error('Failed to load:', error);
        navigate('/create-character');
      }
    };
    
    loadData();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('userId');
    localStorage.removeItem('username');
    localStorage.removeItem('displayName');
    localStorage.removeItem('currentCharacterId');
    navigate('/auth');
  };

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
      <header className="relative z-10 p-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          {userProfile && (
            <>
              <div className="w-10 h-10 rounded-sm bg-gold/20 border border-gold/30 flex items-center justify-center">
                <User className="w-5 h-5 text-gold" />
              </div>
              <div>
                <p className="font-cinzel text-sm text-foreground">{userProfile.display_name}</p>
                <p className="font-mono text-xs text-muted-foreground">@{userProfile.username}</p>
              </div>
            </>
          )}
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/profile')}
            className="rounded-sm"
          >
            <Settings className="w-5 h-5 text-muted-foreground" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="rounded-sm text-red-400 hover:text-red-300"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pb-12">
        {/* Title */}
        <div className="text-center mb-12">
          <h1 className="font-cinzel text-3xl sm:text-4xl text-foreground mb-2">
            Choose Your Path
          </h1>
          <p className="font-manrope text-muted-foreground">
            How would you like to experience The Echoes?
          </p>
        </div>

        {/* Character Preview */}
        {character && (
          <Card className="bg-surface/80 border-border/50 rounded-sm mb-12 max-w-sm w-full">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                {/* Low-poly character avatar */}
                <div className="w-20 h-20 relative">
                  <svg viewBox="0 0 100 100" className="w-full h-full">
                    {/* Simple low-poly character shape */}
                    <polygon 
                      points="50,10 80,35 75,70 50,90 25,70 20,35" 
                      fill="#D4AF37" 
                      fillOpacity="0.3"
                      stroke="#D4AF37"
                      strokeWidth="2"
                    />
                    {/* Face area */}
                    <circle cx="50" cy="40" r="15" fill="#0F0F11" stroke="#D4AF37" strokeWidth="1" />
                    {/* Eyes */}
                    <circle cx="44" cy="38" r="2" fill="#D4AF37" />
                    <circle cx="56" cy="38" r="2" fill="#D4AF37" />
                  </svg>
                </div>
                
                <div className="flex-1">
                  <h3 className="font-cinzel text-lg text-gold">{character.name}</h3>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {character.traits?.slice(0, 2).map((trait, i) => (
                      <Badge key={i} className="bg-gold/10 text-gold/80 text-xs rounded-sm">
                        {trait}
                      </Badge>
                    ))}
                  </div>
                  <p className="font-mono text-xs text-muted-foreground mt-2">
                    Ready to explore
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Mode Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl w-full">
          {/* First Person Mode */}
          <Card 
            className="bg-surface/80 border-border/50 rounded-sm hover:border-slate-blue/50 transition-all duration-300 cursor-pointer group"
            onClick={() => navigate('/play')}
          >
            <CardContent className="p-8 text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-slate-blue/20 border border-slate-blue/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Gamepad2 className="w-10 h-10 text-slate-blue" />
              </div>
              <h3 className="font-cinzel text-xl text-foreground mb-2">First Person</h3>
              <p className="font-manrope text-sm text-muted-foreground mb-6">
                Explore the village with immersive controls. Move with D-pad, interact with objects and NPCs.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-6">
                <Badge className="bg-slate-blue/10 text-slate-blue text-xs rounded-sm">D-Pad Controls</Badge>
                <Badge className="bg-slate-blue/10 text-slate-blue text-xs rounded-sm">Visual World</Badge>
                <Badge className="bg-slate-blue/10 text-slate-blue text-xs rounded-sm">Interact Button</Badge>
              </div>
              <Button 
                data-testid="select-firstperson-btn"
                className="w-full bg-slate-blue text-white hover:bg-slate-blue-light font-cinzel rounded-sm"
              >
                <Gamepad2 className="w-5 h-5 mr-2" />
                Play First Person
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>

          {/* Text Mode */}
          <Card 
            className="bg-surface/80 border-border/50 rounded-sm hover:border-gold/50 transition-all duration-300 cursor-pointer group"
            onClick={() => navigate('/village')}
          >
            <CardContent className="p-8 text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gold/20 border border-gold/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <MessageSquare className="w-10 h-10 text-gold" />
              </div>
              <h3 className="font-cinzel text-xl text-foreground mb-2">Story Mode</h3>
              <p className="font-manrope text-sm text-muted-foreground mb-6">
                Classic text adventure with AI storytelling. Rich narratives, detailed descriptions.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-6">
                <Badge className="bg-gold/10 text-gold text-xs rounded-sm">AI Narrator</Badge>
                <Badge className="bg-gold/10 text-gold text-xs rounded-sm">Rich Text</Badge>
                <Badge className="bg-gold/10 text-gold text-xs rounded-sm">Deep Story</Badge>
              </div>
              <Button 
                data-testid="select-textmode-btn"
                className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
              >
                <MessageSquare className="w-5 h-5 mr-2" />
                Play Story Mode
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Additional Options */}
        <div className="flex flex-wrap gap-4 mt-12 justify-center">
          <Button
            variant="ghost"
            onClick={() => navigate('/building')}
            className="text-muted-foreground hover:text-gold"
          >
            <Hammer className="w-4 h-4 mr-2" />
            Building Workshop
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate('/trading')}
            className="text-muted-foreground hover:text-amber-400"
          >
            <ArrowLeftRight className="w-4 h-4 mr-2" />
            Trading Post
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate('/quests')}
            className="text-muted-foreground hover:text-purple-400"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Quest Board
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate('/dataspace')}
            className="text-muted-foreground hover:text-slate-blue"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Global Dataspace
          </Button>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 p-4 text-center">
        <p className="font-mono text-xs text-muted-foreground/50">
          Low-poly models optimized for all devices
        </p>
      </footer>
    </div>
  );
};

export default ModeSelection;
