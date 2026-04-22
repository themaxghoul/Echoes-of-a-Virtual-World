import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Slider } from '@/components/ui/slider';
import { 
  ArrowLeft, Wand2, X, User, Scroll, Sparkles, Save,
  Palette, Eye, Shirt, Crown, Swords, Shield, Loader2,
  Check, ChevronRight, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory, GameNavigation } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Trait options
const TRAIT_OPTIONS = [
  'Brave', 'Curious', 'Wise', 'Cunning', 'Kind', 'Mysterious',
  'Fierce', 'Gentle', 'Stubborn', 'Patient', 'Reckless', 'Cautious',
  'Ambitious', 'Loyal', 'Skeptical', 'Optimistic'
];

// Background templates
const BACKGROUND_TEMPLATES = [
  { name: 'Wanderer', desc: 'A traveler from distant lands, seeking purpose in The Echoes.' },
  { name: 'Scholar', desc: 'A seeker of forbidden knowledge, drawn by whispers of ancient secrets.' },
  { name: 'Outcast', desc: 'Rejected by your homeland, you found refuge in this mysterious village.' },
  { name: 'Visionary', desc: 'Plagued by prophetic dreams, you follow visions to this place.' },
  { name: 'Merchant', desc: 'A trader seeking fortune in the mystical markets of The Echoes.' },
  { name: 'Guardian', desc: 'A protector sworn to defend the innocent from shadow threats.' },
];

// 3D Model Descriptors (for Unity/engine interpretation)
const BODY_TYPES = [
  { id: 'athletic', name: 'Athletic', desc: 'Lean and agile build' },
  { id: 'muscular', name: 'Muscular', desc: 'Strong and powerful frame' },
  { id: 'slender', name: 'Slender', desc: 'Graceful and elegant form' },
  { id: 'stocky', name: 'Stocky', desc: 'Sturdy and compact build' },
  { id: 'average', name: 'Average', desc: 'Balanced proportions' },
];

const FACE_TYPES = [
  { id: 'angular', name: 'Angular', desc: 'Sharp, defined features' },
  { id: 'round', name: 'Round', desc: 'Soft, youthful appearance' },
  { id: 'oval', name: 'Oval', desc: 'Classic balanced face' },
  { id: 'square', name: 'Square', desc: 'Strong jaw, commanding' },
  { id: 'heart', name: 'Heart', desc: 'Wide forehead, pointed chin' },
];

const SKIN_TONES = [
  { id: 'pale', name: 'Pale', color: '#FFE4D1' },
  { id: 'fair', name: 'Fair', color: '#F5D0B5' },
  { id: 'medium', name: 'Medium', color: '#D4A574' },
  { id: 'olive', name: 'Olive', color: '#C4A35A' },
  { id: 'tan', name: 'Tan', color: '#A67C52' },
  { id: 'brown', name: 'Brown', color: '#8B5A2B' },
  { id: 'dark', name: 'Dark', color: '#5D4037' },
  { id: 'ebony', name: 'Ebony', color: '#3E2723' },
];

const HAIR_STYLES = [
  { id: 'short', name: 'Short' },
  { id: 'medium', name: 'Medium' },
  { id: 'long', name: 'Long' },
  { id: 'bald', name: 'Bald' },
  { id: 'braided', name: 'Braided' },
  { id: 'ponytail', name: 'Ponytail' },
  { id: 'mohawk', name: 'Mohawk' },
  { id: 'curly', name: 'Curly' },
];

const HAIR_COLORS = [
  { id: 'black', name: 'Black', color: '#1A1A1A' },
  { id: 'brown', name: 'Brown', color: '#654321' },
  { id: 'blonde', name: 'Blonde', color: '#E8D5B0' },
  { id: 'red', name: 'Red', color: '#B03B21' },
  { id: 'gray', name: 'Gray', color: '#9E9E9E' },
  { id: 'white', name: 'White', color: '#F5F5F5' },
  { id: 'blue', name: 'Blue', color: '#4682B4' },
  { id: 'purple', name: 'Purple', color: '#8B5CF6' },
];

const EYE_COLORS = [
  { id: 'brown', name: 'Brown', color: '#654321' },
  { id: 'blue', name: 'Blue', color: '#4682B4' },
  { id: 'green', name: 'Green', color: '#228B22' },
  { id: 'hazel', name: 'Hazel', color: '#8B7355' },
  { id: 'gray', name: 'Gray', color: '#708090' },
  { id: 'amber', name: 'Amber', color: '#FFBF00' },
  { id: 'violet', name: 'Violet', color: '#8B5CF6' },
  { id: 'heterochromia', name: 'Heterochromia', color: 'linear-gradient(90deg, #4682B4, #228B22)' },
];

const CLOTHING_STYLES = [
  { id: 'adventurer', name: 'Adventurer', desc: 'Practical travel gear' },
  { id: 'noble', name: 'Noble', desc: 'Elegant court attire' },
  { id: 'mage', name: 'Mage', desc: 'Mystical robes and staff' },
  { id: 'warrior', name: 'Warrior', desc: 'Battle-ready armor' },
  { id: 'merchant', name: 'Merchant', desc: 'Fine trading clothes' },
  { id: 'peasant', name: 'Peasant', desc: 'Simple humble garments' },
  { id: 'rogue', name: 'Rogue', desc: 'Dark, stealthy attire' },
  { id: 'tribal', name: 'Tribal', desc: 'Ancestral cultural dress' },
];

const CharacterCustomization = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editMode = searchParams.get('edit') === 'true';
  const charIdParam = searchParams.get('id');
  
  const [isLoading, setIsLoading] = useState(editMode);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  
  const [character, setCharacter] = useState({
    name: '',
    background: '',
    traits: [],
    appearance: '',
    // 3D Model Descriptors
    model: {
      bodyType: 'average',
      faceType: 'oval',
      skinTone: 'medium',
      hairStyle: 'medium',
      hairColor: 'brown',
      eyeColor: 'brown',
      clothingStyle: 'adventurer',
      height: 170, // cm
      age: 25,
      scars: false,
      tattoos: false,
      beard: false,
      accessories: []
    }
  });

  useEffect(() => {
    pushNavHistory('/customize-character');
    if (editMode) {
      loadExistingCharacter();
    }
  }, [editMode]);

  const loadExistingCharacter = async () => {
    const charId = charIdParam || localStorage.getItem('currentCharacterId');
    if (!charId) {
      navigate('/create-character');
      return;
    }

    try {
      const res = await axios.get(`${API}/character/${charId}`);
      const existingChar = res.data;
      
      setCharacter({
        id: existingChar.id,
        name: existingChar.name || '',
        background: existingChar.background || '',
        traits: existingChar.traits || [],
        appearance: existingChar.appearance || '',
        model: existingChar.model || {
          bodyType: 'average',
          faceType: 'oval',
          skinTone: 'medium',
          hairStyle: 'medium',
          hairColor: 'brown',
          eyeColor: 'brown',
          clothingStyle: 'adventurer',
          height: 170,
          age: 25,
          scars: false,
          tattoos: false,
          beard: false,
          accessories: []
        }
      });
    } catch (error) {
      toast.error('Failed to load character');
      navigate('/create-character');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTrait = (trait) => {
    setCharacter(prev => ({
      ...prev,
      traits: prev.traits.includes(trait)
        ? prev.traits.filter(t => t !== trait)
        : prev.traits.length < 4
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

  const updateModel = (key, value) => {
    setCharacter(prev => ({
      ...prev,
      model: { ...prev.model, [key]: value }
    }));
  };

  const handleSave = async () => {
    if (!character.name.trim()) {
      toast.error('Your character needs a name');
      return;
    }
    if (!character.background.trim()) {
      toast.error('Please provide a background story');
      return;
    }

    setIsSaving(true);
    try {
      const userId = localStorage.getItem('userId');
      if (!userId) {
        toast.error('Please log in first');
        navigate('/auth');
        return;
      }

      if (editMode && character.id) {
        // Update existing character
        await axios.put(`${API}/character/${character.id}`, {
          name: character.name,
          background: character.background,
          traits: character.traits,
          appearance: character.appearance,
          model: character.model
        });
        toast.success(`${character.name} has been updated!`);
      } else {
        // Create new character
        const response = await axios.post(`${API}/characters`, {
          user_id: userId,
          name: character.name,
          background: character.background,
          traits: character.traits,
          appearance: character.appearance,
          model: character.model
        });
        localStorage.setItem('currentCharacterId', response.data.id);
        localStorage.setItem('characterName', character.name);
        toast.success(`${character.name} awakens in The Echoes...`);
      }
      
      navigate('/select-mode');
    } catch (error) {
      console.error('Failed to save character:', error);
      toast.error('Failed to save character. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-16 h-16 mx-auto text-gold animate-spin mb-4" />
          <p className="font-cinzel text-gold">Loading character...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Background */}
      <div className="fixed inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-obsidian to-gold/10" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(editMode ? '/select-mode' : '/')}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-manrope text-sm">Back</span>
          </button>
          <h1 className="font-cinzel text-xl text-gold">
            {editMode ? 'Customize Character' : 'Create Character'}
          </h1>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-gold text-black hover:bg-gold-light font-cinzel"
            data-testid="save-character-btn"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {editMode ? 'Save Changes' : 'Create'}
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 pt-24 pb-12 px-4">
        <div className="max-w-5xl mx-auto">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-surface/50 mb-6">
              <TabsTrigger value="basic" className="font-cinzel">
                <User className="w-4 h-4 mr-2" />
                Basic
              </TabsTrigger>
              <TabsTrigger value="appearance" className="font-cinzel">
                <Eye className="w-4 h-4 mr-2" />
                Appearance
              </TabsTrigger>
              <TabsTrigger value="body" className="font-cinzel">
                <Shirt className="w-4 h-4 mr-2" />
                Body
              </TabsTrigger>
              <TabsTrigger value="style" className="font-cinzel">
                <Crown className="w-4 h-4 mr-2" />
                Style
              </TabsTrigger>
            </TabsList>

            {/* Basic Info Tab */}
            <TabsContent value="basic">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Name & Background */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel flex items-center gap-2">
                      <User className="w-5 h-5 text-gold" />
                      Identity
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label className="font-cinzel text-sm text-muted-foreground">Character Name</Label>
                      <Input
                        value={character.name}
                        onChange={(e) => setCharacter(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Enter your character's name"
                        className="bg-obsidian/50 border-border/50 mt-1"
                        data-testid="character-name-input"
                      />
                    </div>
                    
                    <div>
                      <Label className="font-cinzel text-sm text-muted-foreground">Age</Label>
                      <div className="flex items-center gap-4 mt-1">
                        <Slider
                          value={[character.model.age]}
                          onValueChange={([v]) => updateModel('age', v)}
                          min={16}
                          max={100}
                          step={1}
                          className="flex-1"
                        />
                        <span className="font-mono text-gold w-12">{character.model.age}</span>
                      </div>
                    </div>

                    <div>
                      <Label className="font-cinzel text-sm text-muted-foreground">Background Story</Label>
                      <Textarea
                        value={character.background}
                        onChange={(e) => setCharacter(prev => ({ ...prev, background: e.target.value }))}
                        placeholder="What brought you to The Echoes?"
                        className="bg-obsidian/50 border-border/50 mt-1 min-h-[100px]"
                        data-testid="character-background-input"
                      />
                    </div>

                    {/* Background Templates */}
                    <div>
                      <Label className="font-cinzel text-sm text-muted-foreground mb-2 block">Quick Backgrounds</Label>
                      <div className="grid grid-cols-2 gap-2">
                        {BACKGROUND_TEMPLATES.map((bg) => (
                          <Button
                            key={bg.name}
                            variant="outline"
                            size="sm"
                            onClick={() => selectBackground(bg)}
                            className="text-xs justify-start"
                          >
                            {bg.name}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Traits */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-gold" />
                      Personality Traits
                      <span className="text-sm text-muted-foreground ml-auto">
                        {character.traits.length}/4
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {TRAIT_OPTIONS.map((trait) => (
                        <Badge
                          key={trait}
                          variant={character.traits.includes(trait) ? 'default' : 'outline'}
                          className={`cursor-pointer transition-all ${
                            character.traits.includes(trait)
                              ? 'bg-gold text-black hover:bg-gold-light'
                              : 'hover:border-gold hover:text-gold'
                          }`}
                          onClick={() => toggleTrait(trait)}
                          data-testid={`trait-${trait.toLowerCase()}`}
                        >
                          {trait}
                          {character.traits.includes(trait) && <X className="w-3 h-3 ml-1" />}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Appearance Tab */}
            <TabsContent value="appearance">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Face */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Face Type</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-2">
                      {FACE_TYPES.map((face) => (
                        <Button
                          key={face.id}
                          variant={character.model.faceType === face.id ? 'default' : 'outline'}
                          onClick={() => updateModel('faceType', face.id)}
                          className={character.model.faceType === face.id ? 'bg-gold text-black' : ''}
                        >
                          {face.name}
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Skin Tone */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Skin Tone</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {SKIN_TONES.map((skin) => (
                        <button
                          key={skin.id}
                          onClick={() => updateModel('skinTone', skin.id)}
                          className={`w-12 h-12 rounded-full border-2 transition-all ${
                            character.model.skinTone === skin.id
                              ? 'border-gold scale-110'
                              : 'border-transparent hover:border-muted-foreground'
                          }`}
                          style={{ backgroundColor: skin.color }}
                          title={skin.name}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Hair Style */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Hair Style</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-4 gap-2">
                      {HAIR_STYLES.map((hair) => (
                        <Button
                          key={hair.id}
                          variant={character.model.hairStyle === hair.id ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => updateModel('hairStyle', hair.id)}
                          className={character.model.hairStyle === hair.id ? 'bg-gold text-black' : ''}
                        >
                          {hair.name}
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Hair Color */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Hair Color</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {HAIR_COLORS.map((color) => (
                        <button
                          key={color.id}
                          onClick={() => updateModel('hairColor', color.id)}
                          className={`w-10 h-10 rounded-full border-2 transition-all ${
                            character.model.hairColor === color.id
                              ? 'border-gold scale-110'
                              : 'border-transparent hover:border-muted-foreground'
                          }`}
                          style={{ backgroundColor: color.color }}
                          title={color.name}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Eye Color */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Eye Color</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {EYE_COLORS.map((color) => (
                        <button
                          key={color.id}
                          onClick={() => updateModel('eyeColor', color.id)}
                          className={`w-10 h-10 rounded-full border-2 transition-all ${
                            character.model.eyeColor === color.id
                              ? 'border-gold scale-110'
                              : 'border-transparent hover:border-muted-foreground'
                          }`}
                          style={{ background: color.color }}
                          title={color.name}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Features */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Features</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-3">
                      {[
                        { key: 'scars', label: 'Scars' },
                        { key: 'tattoos', label: 'Tattoos' },
                        { key: 'beard', label: 'Facial Hair' },
                      ].map((feature) => (
                        <Badge
                          key={feature.key}
                          variant={character.model[feature.key] ? 'default' : 'outline'}
                          className={`cursor-pointer ${
                            character.model[feature.key] ? 'bg-gold text-black' : ''
                          }`}
                          onClick={() => updateModel(feature.key, !character.model[feature.key])}
                        >
                          {character.model[feature.key] && <Check className="w-3 h-3 mr-1" />}
                          {feature.label}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Body Tab */}
            <TabsContent value="body">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Body Type */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Body Type</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {BODY_TYPES.map((body) => (
                        <Button
                          key={body.id}
                          variant={character.model.bodyType === body.id ? 'default' : 'outline'}
                          className={`w-full justify-start ${
                            character.model.bodyType === body.id ? 'bg-gold text-black' : ''
                          }`}
                          onClick={() => updateModel('bodyType', body.id)}
                        >
                          <span className="font-cinzel">{body.name}</span>
                          <span className="text-xs ml-auto opacity-70">{body.desc}</span>
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Height */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Height</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <Slider
                        value={[character.model.height]}
                        onValueChange={([v]) => updateModel('height', v)}
                        min={140}
                        max={220}
                        step={1}
                      />
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">140 cm</span>
                        <span className="font-mono text-gold text-lg">{character.model.height} cm</span>
                        <span className="text-muted-foreground">220 cm</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Style Tab */}
            <TabsContent value="style">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Clothing Style */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Clothing Style</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-2">
                      {CLOTHING_STYLES.map((style) => (
                        <Button
                          key={style.id}
                          variant={character.model.clothingStyle === style.id ? 'default' : 'outline'}
                          className={`flex-col h-auto py-3 ${
                            character.model.clothingStyle === style.id ? 'bg-gold text-black' : ''
                          }`}
                          onClick={() => updateModel('clothingStyle', style.id)}
                        >
                          <span className="font-cinzel">{style.name}</span>
                          <span className="text-xs opacity-70">{style.desc}</span>
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Additional Appearance Description */}
                <Card className="bg-surface/80 border-border/50">
                  <CardHeader>
                    <CardTitle className="font-cinzel">Additional Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Textarea
                      value={character.appearance}
                      onChange={(e) => setCharacter(prev => ({ ...prev, appearance: e.target.value }))}
                      placeholder="Describe any additional appearance details (scars, tattoos, unique features, etc.)"
                      className="bg-obsidian/50 border-border/50 min-h-[150px]"
                    />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>

          {/* Model Preview Card */}
          <Card className="bg-surface/80 border-border/50 mt-6">
            <CardHeader>
              <CardTitle className="font-cinzel">3D Model Descriptor (Engine Export)</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-obsidian/50 p-4 rounded-sm text-xs text-muted-foreground overflow-x-auto">
{JSON.stringify({
  name: character.name || 'Unnamed',
  model: character.model,
  traits: character.traits
}, null, 2)}
              </pre>
              <p className="text-xs text-muted-foreground mt-2">
                This descriptor can be used by Unity or other 3D engines to generate your character model.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default CharacterCustomization;
