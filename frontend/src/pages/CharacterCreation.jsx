import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Wand2, X, User, Scroll, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TRAIT_OPTIONS = [
  'Brave', 'Curious', 'Wise', 'Cunning', 'Kind', 'Mysterious',
  'Fierce', 'Gentle', 'Stubborn', 'Patient', 'Reckless', 'Cautious'
];

const BACKGROUND_TEMPLATES = [
  { name: 'Wanderer', desc: 'A traveler from distant lands, seeking purpose in The Echoes.' },
  { name: 'Scholar', desc: 'A seeker of forbidden knowledge, drawn by whispers of ancient secrets.' },
  { name: 'Outcast', desc: 'Rejected by your homeland, you found refuge in this mysterious village.' },
  { name: 'Visionary', desc: 'Plagued by prophetic dreams, you follow visions to this place.' },
];

const CharacterCreation = () => {
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [character, setCharacter] = useState({
    name: '',
    background: '',
    traits: [],
    appearance: '',
  });

  const toggleTrait = (trait) => {
    setCharacter(prev => ({
      ...prev,
      traits: prev.traits.includes(trait)
        ? prev.traits.filter(t => t !== trait)
        : prev.traits.length < 3
          ? [...prev.traits, trait]
          : prev.traits
    }));
  };

  const selectBackground = (bg) => {
    setCharacter(prev => ({
      ...prev,
      background: bg.desc
    }));
  };

  const handleCreate = async () => {
    if (!character.name.trim()) {
      toast.error('Your character needs a name to enter The Echoes');
      return;
    }
    if (!character.background.trim()) {
      toast.error('Every soul has a story. Please provide a background.');
      return;
    }

    setIsCreating(true);
    try {
      const userId = localStorage.getItem('userId') || `user_${Date.now()}`;
      localStorage.setItem('userId', userId);

      const response = await axios.post(`${API}/characters`, {
        user_id: userId,
        name: character.name,
        background: character.background,
        traits: character.traits,
        appearance: character.appearance,
      });

      localStorage.setItem('currentCharacterId', response.data.id);
      toast.success(`${character.name} awakens in The Echoes...`);
      navigate('/village');
    } catch (error) {
      console.error('Failed to create character:', error);
      toast.error('The mists rejected your form. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian bg-pattern">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            data-testid="back-to-landing-btn"
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back</span>
          </button>
          <h1 className="font-cinzel text-lg text-gold tracking-wider">Character Creation</h1>
          <div className="w-16" />
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Intro */}
          <div className="text-center mb-12">
            <h2 className="font-cinzel text-3xl sm:text-4xl text-foreground mb-4">
              Who Are You?
            </h2>
            <p className="font-manrope text-muted-foreground max-w-lg mx-auto">
              Before you enter The Echoes, the mists must know your essence. 
              Shape your identity, and the village will remember.
            </p>
          </div>

          {/* Form */}
          <div className="space-y-8">
            {/* Name */}
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardHeader className="pb-4">
                <CardTitle className="font-cinzel text-lg text-foreground flex items-center gap-2">
                  <User className="w-5 h-5 text-gold" />
                  Name
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Input
                  data-testid="character-name-input"
                  value={character.name}
                  onChange={(e) => setCharacter(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="What shall The Echoes call you?"
                  className="bg-obsidian border-border/50 focus:ring-gold/50 focus:border-gold/50 font-manrope rounded-sm"
                  maxLength={30}
                />
              </CardContent>
            </Card>

            {/* Background */}
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardHeader className="pb-4">
                <CardTitle className="font-cinzel text-lg text-foreground flex items-center gap-2">
                  <Scroll className="w-5 h-5 text-gold" />
                  Background
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Templates */}
                <div className="grid grid-cols-2 gap-3">
                  {BACKGROUND_TEMPLATES.map((bg) => (
                    <button
                      key={bg.name}
                      data-testid={`background-${bg.name.toLowerCase()}-btn`}
                      onClick={() => selectBackground(bg)}
                      className={`p-4 text-left rounded-sm border transition-all duration-300 ${
                        character.background === bg.desc
                          ? 'border-gold bg-gold/10'
                          : 'border-border/50 hover:border-slate-blue/50 bg-obsidian/50'
                      }`}
                    >
                      <div className="font-cinzel text-sm text-foreground mb-1">{bg.name}</div>
                      <div className="font-manrope text-xs text-muted-foreground line-clamp-2">{bg.desc}</div>
                    </button>
                  ))}
                </div>
                {/* Custom */}
                <div>
                  <Label className="font-manrope text-sm text-muted-foreground mb-2 block">
                    Or write your own story...
                  </Label>
                  <Textarea
                    data-testid="character-background-input"
                    value={character.background}
                    onChange={(e) => setCharacter(prev => ({ ...prev, background: e.target.value }))}
                    placeholder="What brings you to The Echoes? What secrets do you carry?"
                    className="bg-obsidian border-border/50 focus:ring-gold/50 focus:border-gold/50 font-manrope rounded-sm min-h-[100px]"
                    maxLength={500}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Traits */}
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardHeader className="pb-4">
                <CardTitle className="font-cinzel text-lg text-foreground flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-gold" />
                  Traits
                  <span className="font-manrope text-xs text-muted-foreground ml-2">
                    (Choose up to 3)
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {TRAIT_OPTIONS.map((trait) => (
                    <Badge
                      key={trait}
                      data-testid={`trait-${trait.toLowerCase()}-btn`}
                      onClick={() => toggleTrait(trait)}
                      className={`cursor-pointer transition-all duration-300 rounded-sm ${
                        character.traits.includes(trait)
                          ? 'bg-gold text-black hover:bg-gold-light'
                          : 'bg-surface-highlight text-muted-foreground hover:text-foreground hover:bg-slate-blue/20'
                      }`}
                    >
                      {character.traits.includes(trait) && <X className="w-3 h-3 mr-1" />}
                      {trait}
                    </Badge>
                  ))}
                </div>
                {character.traits.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border/30">
                    <span className="font-manrope text-sm text-muted-foreground">Selected: </span>
                    <span className="font-cinzel text-sm text-gold">{character.traits.join(' • ')}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Appearance */}
            <Card className="bg-surface/80 border-border/50 rounded-sm">
              <CardHeader className="pb-4">
                <CardTitle className="font-cinzel text-lg text-foreground">
                  Appearance
                  <span className="font-manrope text-xs text-muted-foreground ml-2">(Optional)</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  data-testid="character-appearance-input"
                  value={character.appearance}
                  onChange={(e) => setCharacter(prev => ({ ...prev, appearance: e.target.value }))}
                  placeholder="Describe how you appear to others in The Echoes..."
                  className="bg-obsidian border-border/50 focus:ring-gold/50 focus:border-gold/50 font-manrope rounded-sm"
                  maxLength={300}
                />
              </CardContent>
            </Card>

            {/* Create Button */}
            <div className="flex justify-center pt-8">
              <Button
                data-testid="create-character-btn"
                onClick={handleCreate}
                disabled={isCreating || !character.name.trim() || !character.background.trim()}
                className="bg-gold text-black font-cinzel font-bold text-lg uppercase tracking-widest px-12 py-6 hover:bg-gold-light transition-all duration-300 shadow-[0_0_20px_rgba(212,175,55,0.3)] hover:shadow-[0_0_40px_rgba(212,175,55,0.5)] rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Wand2 className="w-5 h-5 mr-3" />
                {isCreating ? 'Awakening...' : 'Awaken Character'}
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CharacterCreation;
