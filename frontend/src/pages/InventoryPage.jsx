import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  ArrowLeft, Sword, Shield, Zap, Heart, 
  Wind, Target, Package, Check
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const WEAPON_ICONS = {
  fists: '👊',
  dagger: '🗡️',
  sword: '⚔️',
  greatsword: '🔪',
  mace: '🔨',
  spear: '🔱',
  staff: '🪄'
};

const ARMOR_ICONS = {
  none: '👤',
  cloth: '👕',
  leather: '🥋',
  chain: '⛓️',
  plate: '🛡️',
  legendary: '✨'
};

const InventoryPage = () => {
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [combatStats, setCombatStats] = useState(null);
  const [weaponTypes, setWeaponTypes] = useState({});
  const [armorTypes, setArmorTypes] = useState({});
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    const charId = localStorage.getItem('currentCharacterId');
    if (!charId) {
      navigate('/create-character');
      return;
    }
    
    try {
      const [charRes, combatRes, statsRes] = await Promise.all([
        axios.get(`${API}/character/${charId}`),
        axios.get(`${API}/character/${charId}/combat-stats`),
        axios.get(`${API}/combat/stats`)
      ]);
      
      setCharacter(charRes.data);
      setCombatStats(combatRes.data);
      setWeaponTypes(statsRes.data.weapon_types);
      setArmorTypes(statsRes.data.armor_types);
    } catch (error) {
      console.error('Failed to load inventory:', error);
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };
  
  const equipItem = async (slot, itemType) => {
    if (!character) return;
    
    try {
      await axios.post(`${API}/character/${character.id}/equip`, {
        character_id: character.id,
        slot: slot,
        item_type: itemType
      });
      
      toast.success(`Equipped ${itemType}!`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to equip');
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-gold font-cinzel text-xl animate-pulse">Loading inventory...</div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="border-b border-border/30 bg-surface/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Package className="w-6 h-6" />
                Equipment & Inventory
              </h1>
              <p className="text-sm text-muted-foreground">{character?.name}'s Gear</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-8">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Character Stats */}
          <Card className="bg-surface/50 border-border/30 p-6 rounded-sm">
            <h2 className="font-cinzel text-xl text-gold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5" />
              Combat Stats
            </h2>
            
            <div className="space-y-4">
              {/* Health */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="flex items-center gap-1"><Heart className="w-4 h-4 text-red-400" /> Health</span>
                  <span>{combatStats?.health || 100}/{combatStats?.max_health || 100}</span>
                </div>
                <Progress value={(combatStats?.health / combatStats?.max_health) * 100} className="h-2 bg-red-900" />
              </div>
              
              {/* Stamina */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="flex items-center gap-1"><Zap className="w-4 h-4 text-green-400" /> Stamina</span>
                  <span>{Math.round(combatStats?.stamina || 100)}/{combatStats?.max_stamina || 100}</span>
                </div>
                <Progress value={(combatStats?.stamina / combatStats?.max_stamina) * 100} className="h-2 bg-green-900" />
              </div>
              
              {/* Attributes */}
              <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-border/30">
                <div className="flex items-center gap-2">
                  <Sword className="w-4 h-4 text-red-400" />
                  <span className="text-sm">Strength: {combatStats?.stats?.strength || 10}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Wind className="w-4 h-4 text-green-400" />
                  <span className="text-sm">Endurance: {combatStats?.stats?.endurance || 10}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm">Agility: {combatStats?.stats?.agility || 10}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Heart className="w-4 h-4 text-pink-400" />
                  <span className="text-sm">Vitality: {combatStats?.stats?.vitality || 10}</span>
                </div>
              </div>
              
              {/* Derived Stats */}
              <div className="mt-4 pt-4 border-t border-border/30 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Damage:</span>
                  <span className="text-red-400">{Math.round(combatStats?.derived_stats?.total_damage || 0)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Defense:</span>
                  <span className="text-blue-400">{combatStats?.derived_stats?.total_defense || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Sprint Drain/sec:</span>
                  <span className="text-yellow-400">{combatStats?.derived_stats?.sprint_stamina_drain_per_second?.toFixed(2) || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Dodge Chance:</span>
                  <span className="text-purple-400">{Math.round((combatStats?.derived_stats?.dodge_chance || 0) * 100)}%</span>
                </div>
              </div>
            </div>
          </Card>
          
          {/* Current Equipment */}
          <Card className="bg-surface/50 border-border/30 p-6 rounded-sm">
            <h2 className="font-cinzel text-xl text-gold mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Equipped Gear
            </h2>
            
            <div className="space-y-6">
              {/* Weapon */}
              <div className="p-4 bg-obsidian/50 rounded-sm border border-border/30">
                <div className="flex items-center gap-4">
                  <div className="text-4xl">{WEAPON_ICONS[combatStats?.equipment?.weapon_key] || '⚔️'}</div>
                  <div>
                    <div className="font-cinzel text-lg">{combatStats?.equipment?.weapon?.name || 'None'}</div>
                    <div className="text-sm text-muted-foreground">
                      Damage: {combatStats?.equipment?.weapon?.damage || 0} | 
                      Speed: {combatStats?.equipment?.weapon?.speed || 1}x
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Armor */}
              <div className="p-4 bg-obsidian/50 rounded-sm border border-border/30">
                <div className="flex items-center gap-4">
                  <div className="text-4xl">{ARMOR_ICONS[combatStats?.equipment?.armor_key] || '👤'}</div>
                  <div>
                    <div className="font-cinzel text-lg">{combatStats?.equipment?.armor?.name || 'None'}</div>
                    <div className="text-sm text-muted-foreground">
                      Defense: {combatStats?.equipment?.armor?.defense || 0} | 
                      Weight: {combatStats?.equipment?.armor?.weight || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
        
        {/* Available Weapons */}
        <Card className="bg-surface/50 border-border/30 p-6 rounded-sm mt-8">
          <h2 className="font-cinzel text-xl text-gold mb-4 flex items-center gap-2">
            <Sword className="w-5 h-5" />
            Available Weapons
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {Object.entries(weaponTypes).map(([key, weapon]) => {
              const isEquipped = combatStats?.equipment?.weapon_key === key;
              return (
                <div 
                  key={key}
                  className={`p-4 rounded-sm border transition-all cursor-pointer ${
                    isEquipped 
                      ? 'bg-gold/20 border-gold' 
                      : 'bg-obsidian/50 border-border/30 hover:border-gold/50'
                  }`}
                  onClick={() => !isEquipped && equipItem('weapon', key)}
                >
                  <div className="text-3xl text-center mb-2">{WEAPON_ICONS[key] || '⚔️'}</div>
                  <div className="text-center">
                    <div className="font-cinzel text-sm">{weapon.name}</div>
                    <div className="text-xs text-muted-foreground">
                      DMG: {weapon.damage}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      SPD: {weapon.speed}x
                    </div>
                  </div>
                  {isEquipped && (
                    <Badge className="w-full mt-2 justify-center bg-gold/30 text-gold">
                      <Check className="w-3 h-3 mr-1" /> Equipped
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
        
        {/* Available Armor */}
        <Card className="bg-surface/50 border-border/30 p-6 rounded-sm mt-8">
          <h2 className="font-cinzel text-xl text-gold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Available Armor
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Object.entries(armorTypes).map(([key, armor]) => {
              const isEquipped = combatStats?.equipment?.armor_key === key;
              return (
                <div 
                  key={key}
                  className={`p-4 rounded-sm border transition-all cursor-pointer ${
                    isEquipped 
                      ? 'bg-blue-500/20 border-blue-500' 
                      : 'bg-obsidian/50 border-border/30 hover:border-blue-500/50'
                  }`}
                  onClick={() => !isEquipped && equipItem('armor', key)}
                >
                  <div className="text-3xl text-center mb-2">{ARMOR_ICONS[key] || '👤'}</div>
                  <div className="text-center">
                    <div className="font-cinzel text-sm">{armor.name}</div>
                    <div className="text-xs text-muted-foreground">
                      DEF: {armor.defense}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Weight: {armor.weight}
                    </div>
                  </div>
                  {isEquipped && (
                    <Badge className="w-full mt-2 justify-center bg-blue-500/30 text-blue-400">
                      <Check className="w-3 h-3 mr-1" /> Equipped
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
        
        {/* Travel Stats */}
        <Card className="bg-surface/50 border-border/30 p-6 rounded-sm mt-8">
          <h2 className="font-cinzel text-xl text-gold mb-4">Exploration Progress</h2>
          <div className="text-lg">
            Total Distance Traveled: <span className="text-gold font-bold">{Math.round(character?.total_distance_traveled || 0)}</span> units
          </div>
          <div className="text-sm text-muted-foreground mt-2">
            Travel more to discover new lands! Different regions unlock at various distances.
          </div>
        </Card>
      </div>
    </div>
  );
};

export default InventoryPage;
