import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  ArrowLeft, User, Shield, Coins, Star, Sparkles, 
  Crown, Eye, Loader2, Users
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PERMISSION_ICONS = {
  basic: Shield,
  advanced: Star,
  admin: Crown,
  sirix_1: Eye,
};

const PERMISSION_COLORS = {
  basic: 'text-slate-400',
  advanced: 'text-amber-400',
  admin: 'text-purple-400',
  sirix_1: 'text-cyan-400',
};

const UserProfilePage = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [permissions, setPermissions] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingProfile, setIsCreatingProfile] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    const userId = localStorage.getItem('userId');
    
    if (!userId) {
      setIsLoading(false);
      setIsCreatingProfile(true);
      return;
    }

    try {
      const [profileRes, charsRes, permsRes] = await Promise.all([
        axios.get(`${API}/users/id/${userId}`),
        axios.get(`${API}/characters/${userId}`),
        axios.get(`${API}/permissions/${userId}`)
      ]);
      
      setProfile(profileRes.data);
      setCharacters(charsRes.data);
      setPermissions(permsRes.data);
    } catch (error) {
      console.error('Failed to load profile:', error);
      setIsCreatingProfile(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProfile = async () => {
    if (!newUsername.trim() || !newDisplayName.trim()) {
      toast.error('Please enter a username and display name');
      return;
    }

    try {
      const response = await axios.post(`${API}/users`, {
        username: newUsername.toLowerCase(),
        display_name: newDisplayName,
        permission_level: 'basic'
      });
      
      localStorage.setItem('userId', response.data.id);
      toast.success('Profile created! Welcome to The Echoes.');
      setIsCreatingProfile(false);
      loadProfile();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create profile');
    }
  };

  const PermIcon = profile ? PERMISSION_ICONS[profile.permission_level] || Shield : Shield;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  if (isCreatingProfile) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center px-6">
        <Card className="bg-surface/80 border-border/50 rounded-sm max-w-md w-full">
          <CardHeader>
            <CardTitle className="font-cinzel text-2xl text-gold text-center">
              Create Your Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="font-manrope text-sm text-muted-foreground text-center">
              Join The Echoes and begin your journey. Your profile persists across all characters.
            </p>
            
            <div>
              <label className="font-manrope text-sm text-muted-foreground">Username</label>
              <Input
                data-testid="username-input"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder="Choose a unique username"
                className="bg-obsidian border-border/50 rounded-sm mt-1"
              />
            </div>
            
            <div>
              <label className="font-manrope text-sm text-muted-foreground">Display Name</label>
              <Input
                data-testid="display-name-input"
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                placeholder="How should others see you?"
                className="bg-obsidian border-border/50 rounded-sm mt-1"
              />
            </div>

            <Button
              data-testid="create-profile-btn"
              onClick={handleCreateProfile}
              className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm py-6"
            >
              Create Profile
            </Button>
            
            <button
              onClick={() => navigate('/')}
              className="w-full text-center text-muted-foreground hover:text-foreground text-sm"
            >
              Return Home
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            data-testid="back-btn"
            onClick={() => navigate('/village')}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back</span>
          </button>
          <h1 className="font-cinzel text-lg text-gold tracking-wider">Profile</h1>
          <div className="w-16" />
        </div>
      </header>

      {/* Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Profile Card */}
          <Card className="bg-surface/80 border-border/50 rounded-sm">
            <CardContent className="p-8">
              <div className="flex items-start gap-6">
                <div className="w-24 h-24 rounded-sm bg-gold/20 border-2 border-gold/30 flex items-center justify-center">
                  <User className="w-12 h-12 text-gold" />
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="font-cinzel text-2xl text-foreground">
                      {profile?.display_name}
                    </h2>
                    {profile?.is_immutable && (
                      <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 rounded-sm">
                        IMMUTABLE
                      </Badge>
                    )}
                  </div>
                  <p className="font-mono text-sm text-muted-foreground mb-4">
                    @{profile?.username}
                  </p>
                  
                  <div className="flex items-center gap-4">
                    <Badge className={`${PERMISSION_COLORS[profile?.permission_level]} bg-transparent border rounded-sm`}>
                      <PermIcon className="w-4 h-4 mr-1" />
                      {profile?.permission_level?.toUpperCase()}
                    </Badge>
                    <span className="font-mono text-xs text-muted-foreground">
                      Joined {new Date(profile?.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Resources */}
          <Card className="bg-surface/80 border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg text-foreground">Resources</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-6">
                <div className="text-center p-4 bg-obsidian/50 rounded-sm">
                  <Coins className="w-8 h-8 text-gold mx-auto mb-2" />
                  <div className="font-mono text-2xl text-gold">{profile?.resources?.gold || 0}</div>
                  <div className="font-manrope text-xs text-muted-foreground">Gold</div>
                </div>
                <div className="text-center p-4 bg-obsidian/50 rounded-sm">
                  <Sparkles className="w-8 h-8 text-slate-blue mx-auto mb-2" />
                  <div className="font-mono text-2xl text-slate-blue">{profile?.resources?.essence || 0}</div>
                  <div className="font-manrope text-xs text-muted-foreground">Essence</div>
                </div>
                <div className="text-center p-4 bg-obsidian/50 rounded-sm">
                  <Star className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                  <div className="font-mono text-2xl text-purple-400">{profile?.resources?.artifacts || 0}</div>
                  <div className="font-manrope text-xs text-muted-foreground">Artifacts</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* XP Progress */}
          <Card className="bg-surface/80 border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg text-foreground flex items-center justify-between">
                <span>Experience</span>
                <span className="font-mono text-gold">{profile?.xp || 0} XP</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Progress 
                value={((profile?.xp || 0) % 1000) / 10} 
                className="h-3 bg-obsidian"
              />
              <p className="font-manrope text-xs text-muted-foreground mt-2">
                {1000 - ((profile?.xp || 0) % 1000)} XP to next level
              </p>
            </CardContent>
          </Card>

          {/* Permissions */}
          {permissions && (
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardHeader>
                <CardTitle className="font-cinzel text-lg text-foreground">Abilities</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {permissions.abilities?.map((ability, i) => (
                    <Badge 
                      key={i}
                      className="bg-gold/10 text-gold border-gold/30 rounded-sm font-mono text-xs"
                    >
                      {ability}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Characters */}
          <Card className="bg-surface/80 border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg text-foreground flex items-center gap-2">
                <Users className="w-5 h-5" />
                Characters ({characters.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {characters.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">No characters yet</p>
              ) : (
                <div className="space-y-3">
                  {characters.map((char) => (
                    <div 
                      key={char.id}
                      className="flex items-center justify-between p-4 bg-obsidian/50 rounded-sm"
                    >
                      <div>
                        <div className="font-cinzel text-foreground">{char.name}</div>
                        <div className="font-manrope text-xs text-muted-foreground">
                          {char.traits?.join(' • ')}
                        </div>
                      </div>
                      <Badge className="bg-surface border-border/50 rounded-sm font-mono text-xs">
                        {char.current_location}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
              
              <Button
                data-testid="create-character-btn"
                onClick={() => navigate('/create-character')}
                className="w-full mt-4 bg-gold/20 text-gold hover:bg-gold/30 border border-gold/30 font-cinzel rounded-sm"
              >
                Create New Character
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default UserProfilePage;
