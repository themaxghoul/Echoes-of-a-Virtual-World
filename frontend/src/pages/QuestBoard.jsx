import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  ArrowLeft, Scroll, Plus, Coins, Star, Clock, 
  User, CheckCircle, AlertCircle, Loader2 
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const QuestBoard = () => {
  const navigate = useNavigate();
  const [quests, setQuests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [userProfile, setUserProfile] = useState(null);
  const [characterId, setCharacterId] = useState(null);
  
  const [newQuest, setNewQuest] = useState({
    title: '',
    description: '',
    goldReward: 50,
    xpReward: 25,
    location_id: 'village_square'
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        const charId = localStorage.getItem('currentCharacterId');
        const userId = localStorage.getItem('userId');
        setCharacterId(charId);
        
        const [questsRes, userRes] = await Promise.all([
          axios.get(`${API}/quests`),
          userId ? axios.get(`${API}/users/id/${userId}`).catch(() => null) : null
        ]);
        
        setQuests(questsRes.data);
        if (userRes?.data) setUserProfile(userRes.data);
      } catch (error) {
        console.error('Failed to load quests:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  const handleCreateQuest = async () => {
    if (!newQuest.title.trim() || !newQuest.description.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      const userId = localStorage.getItem('userId');
      await axios.post(`${API}/quests`, {
        title: newQuest.title,
        description: newQuest.description,
        creator_id: userId,
        creator_type: 'player',
        location_id: newQuest.location_id,
        rewards: { gold: newQuest.goldReward, xp: newQuest.xpReward },
        use_personal_resources: true
      });
      
      toast.success('Quest posted to the board!');
      setShowCreateDialog(false);
      setNewQuest({ title: '', description: '', goldReward: 50, xpReward: 25, location_id: 'village_square' });
      
      // Refresh quests
      const res = await axios.get(`${API}/quests`);
      setQuests(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create quest');
    }
  };

  const handleAcceptQuest = async (questId) => {
    if (!characterId) {
      toast.error('No character found');
      return;
    }

    try {
      await axios.put(`${API}/quest/${questId}/accept?character_id=${characterId}`);
      toast.success('Quest accepted! Check your journal.');
      
      const res = await axios.get(`${API}/quests`);
      setQuests(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept quest');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'in_progress': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'completed': return 'bg-slate-blue/20 text-slate-blue border-slate-blue/30';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            data-testid="back-btn"
            onClick={() => navigate('/village')}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back to Village</span>
          </button>
          <h1 className="font-cinzel text-lg text-gold tracking-wider flex items-center gap-2">
            <Scroll className="w-5 h-5" />
            Quest Board
          </h1>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button 
                data-testid="create-quest-btn"
                className="bg-gold text-black hover:bg-gold-light font-cinzel text-sm rounded-sm"
              >
                <Plus className="w-4 h-4 mr-2" />
                Post Quest
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-surface border-border/50 rounded-sm">
              <DialogHeader>
                <DialogTitle className="font-cinzel text-gold">Post a New Quest</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div>
                  <label className="font-manrope text-sm text-muted-foreground">Title</label>
                  <Input
                    data-testid="quest-title-input"
                    value={newQuest.title}
                    onChange={(e) => setNewQuest(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="What do you need help with?"
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                  />
                </div>
                <div>
                  <label className="font-manrope text-sm text-muted-foreground">Description</label>
                  <Textarea
                    data-testid="quest-desc-input"
                    value={newQuest.description}
                    onChange={(e) => setNewQuest(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Describe the task in detail..."
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="font-manrope text-sm text-muted-foreground">Gold Reward</label>
                    <Input
                      type="number"
                      value={newQuest.goldReward}
                      onChange={(e) => setNewQuest(prev => ({ ...prev, goldReward: parseInt(e.target.value) || 0 }))}
                      className="bg-obsidian border-border/50 rounded-sm mt-1"
                    />
                  </div>
                  <div>
                    <label className="font-manrope text-sm text-muted-foreground">XP Reward</label>
                    <Input
                      type="number"
                      value={newQuest.xpReward}
                      onChange={(e) => setNewQuest(prev => ({ ...prev, xpReward: parseInt(e.target.value) || 0 }))}
                      className="bg-obsidian border-border/50 rounded-sm mt-1"
                    />
                  </div>
                </div>
                {userProfile && (
                  <p className="font-mono text-xs text-muted-foreground">
                    Your gold: {userProfile.resources?.gold || 0} (will be deducted)
                  </p>
                )}
                <Button
                  data-testid="submit-quest-btn"
                  onClick={handleCreateQuest}
                  className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
                >
                  Post Quest
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-5xl mx-auto">
          {isLoading ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
              <p className="font-manrope text-muted-foreground">Loading quests...</p>
            </div>
          ) : quests.length === 0 ? (
            <Card className="bg-surface/80 border-border/50 rounded-sm max-w-lg mx-auto">
              <CardContent className="p-12 text-center">
                <Scroll className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-cinzel text-lg text-foreground mb-2">No Quests Available</h3>
                <p className="font-manrope text-sm text-muted-foreground mb-6">
                  Be the first to post a quest and help shape The Echoes!
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quests.map((quest) => (
                <Card 
                  key={quest.id}
                  className="bg-surface/80 border-border/50 rounded-sm hover:border-gold/30 transition-colors"
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="font-cinzel text-lg text-foreground">
                        {quest.title}
                      </CardTitle>
                      <Badge className={`${getStatusColor(quest.status)} rounded-sm font-mono text-xs`}>
                        {quest.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="font-manrope text-sm text-muted-foreground mb-4 line-clamp-3">
                      {quest.description}
                    </p>
                    
                    <div className="flex items-center gap-4 mb-4">
                      <div className="flex items-center gap-1 text-gold">
                        <Coins className="w-4 h-4" />
                        <span className="font-mono text-sm">{quest.rewards?.gold || 0}</span>
                      </div>
                      <div className="flex items-center gap-1 text-slate-blue">
                        <Star className="w-4 h-4" />
                        <span className="font-mono text-sm">{quest.rewards?.xp || 0} XP</span>
                      </div>
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <User className="w-4 h-4" />
                        <span className="font-mono text-xs">{quest.creator_type}</span>
                      </div>
                    </div>

                    {quest.status === 'open' && (
                      <Button
                        data-testid={`accept-quest-${quest.id}-btn`}
                        onClick={() => handleAcceptQuest(quest.id)}
                        className="w-full bg-gold/20 text-gold hover:bg-gold/30 border border-gold/30 font-cinzel rounded-sm"
                      >
                        Accept Quest
                      </Button>
                    )}
                    {quest.status === 'in_progress' && quest.assigned_to === characterId && (
                      <Badge className="w-full justify-center py-2 bg-amber-500/20 text-amber-400 border-amber-500/30">
                        <AlertCircle className="w-4 h-4 mr-2" />
                        In Progress
                      </Badge>
                    )}
                    {quest.status === 'completed' && (
                      <Badge className="w-full justify-center py-2 bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Completed
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default QuestBoard;
