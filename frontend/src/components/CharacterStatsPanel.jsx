import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { 
  X, Star, Heart, Zap, Shield, Swords, Brain, 
  Eye, Flame, Crown, Sparkles, MapPin, Clock
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CharacterStatsPanel = ({ characterId, userId, isOpen, onClose }) => {
  const [character, setCharacter] = useState(null);
  const [combatStats, setCombatStats] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (!isOpen || !characterId) return;
    
    const loadStats = async () => {
      setLoading(true);
      try {
        const [charRes, combatRes, userRes] = await Promise.all([
          axios.get(`${API}/character/${characterId}`),
          axios.get(`${API}/character/${characterId}/combat-stats`).catch(() => null),
          userId ? axios.get(`${API}/users/id/${userId}`).catch(() => null) : null,
        ]);
        
        setCharacter(charRes.data);
        if (combatRes?.data) setCombatStats(combatRes.data);
        if (userRes?.data) setUserProfile(userRes.data);
      } catch (error) {
        console.error('Failed to load stats:', error);
      }
      setLoading(false);
    };
    
    loadStats();
  }, [isOpen, characterId, userId]);
  
  if (!isOpen) return null;
  
  const isTranscendent = userProfile?.is_transcendent || userProfile?.permission_level === 'sirix_1';
  
  // Format stat value - show ∞ for Sirix-1, hide for others viewing Sirix-1
  const formatStat = (value, isResource = false) => {
    if (value === null || value === undefined) {
      return isTranscendent ? '∞' : '???';
    }
    return value;
  };
  
  const StatBar = ({ label, current, max, color, icon: Icon }) => {
    const percentage = max ? (current / max) * 100 : 100;
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1 text-muted-foreground">
            <Icon className="w-3 h-3" />
            {label}
          </span>
          <span className="font-mono">{formatStat(current)}/{formatStat(max)}</span>
        </div>
        <div className="h-2 bg-black/50 rounded-full overflow-hidden">
          <div 
            className={`h-full ${color} transition-all duration-300`}
            style={{ width: `${isTranscendent && current === null ? 100 : percentage}%` }}
          />
        </div>
      </div>
    );
  };
  
  const StatItem = ({ label, value, icon: Icon, color = 'text-foreground' }) => (
    <div className="flex items-center justify-between p-2 bg-black/20 rounded">
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className={`w-4 h-4 ${color}`} />
        {label}
      </span>
      <span className="font-mono text-sm">{formatStat(value)}</span>
    </div>
  );
  
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="bg-surface/95 border-gold/30 rounded-sm w-full max-w-md max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border/30 flex items-center justify-between bg-obsidian/50">
          <div className="flex items-center gap-2">
            <Star className="w-5 h-5 text-purple-400" />
            <span className="font-cinzel text-lg text-gold">Character Stats</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        {loading ? (
          <div className="p-8 text-center text-muted-foreground">Loading stats...</div>
        ) : (
          <ScrollArea className="max-h-[calc(90vh-80px)]">
            <div className="p-4 space-y-6">
              {/* Character Identity */}
              <div className="text-center space-y-2">
                <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-gold/30 to-purple-500/30 border-2 border-gold flex items-center justify-center">
                  <Crown className="w-10 h-10 text-gold" />
                </div>
                <h2 className="font-cinzel text-xl text-foreground">{character?.name}</h2>
                <div className="flex justify-center gap-2">
                  {character?.traits?.map(trait => (
                    <Badge key={trait} className="bg-purple-500/20 text-purple-300 text-xs">
                      {trait}
                    </Badge>
                  ))}
                </div>
                {userProfile?.official_rank && (
                  <Badge className="bg-gold/20 text-gold">
                    <Crown className="w-3 h-3 mr-1" />
                    {userProfile.official_rank}
                  </Badge>
                )}
                {isTranscendent && (
                  <Badge className="bg-purple-900/50 text-purple-300 border border-purple-500/50">
                    <Sparkles className="w-3 h-3 mr-1" />
                    Transcendent
                  </Badge>
                )}
              </div>
              
              {/* Vital Stats */}
              <div className="space-y-3">
                <h3 className="font-cinzel text-sm text-gold border-b border-gold/30 pb-1">Vitals</h3>
                <StatBar 
                  label="Health" 
                  current={combatStats?.health || character?.health} 
                  max={combatStats?.max_health || character?.max_health}
                  color="bg-gradient-to-r from-red-700 to-red-500"
                  icon={Heart}
                />
                <StatBar 
                  label="Stamina" 
                  current={combatStats?.stamina || character?.stamina} 
                  max={combatStats?.max_stamina || character?.max_stamina}
                  color="bg-gradient-to-r from-green-700 to-green-500"
                  icon={Zap}
                />
                <StatBar 
                  label="Mana" 
                  current={combatStats?.mana || character?.mana} 
                  max={combatStats?.max_mana || character?.max_mana}
                  color="bg-gradient-to-r from-blue-700 to-blue-400"
                  icon={Sparkles}
                />
              </div>
              
              {/* Combat Stats */}
              <div className="space-y-2">
                <h3 className="font-cinzel text-sm text-gold border-b border-gold/30 pb-1">Combat</h3>
                <div className="grid grid-cols-2 gap-2">
                  <StatItem label="Strength" value={combatStats?.stats?.strength || character?.strength} icon={Swords} color="text-red-400" />
                  <StatItem label="Endurance" value={combatStats?.stats?.endurance || character?.endurance} icon={Shield} color="text-green-400" />
                  <StatItem label="Agility" value={combatStats?.stats?.agility || character?.agility} icon={Zap} color="text-yellow-400" />
                  <StatItem label="Vitality" value={combatStats?.stats?.vitality || character?.vitality} icon={Heart} color="text-pink-400" />
                  <StatItem label="Intelligence" value={character?.intelligence} icon={Brain} color="text-blue-400" />
                  <StatItem label="Wisdom" value={character?.wisdom} icon={Eye} color="text-purple-400" />
                </div>
              </div>
              
              {/* Equipment */}
              <div className="space-y-2">
                <h3 className="font-cinzel text-sm text-gold border-b border-gold/30 pb-1">Equipment</h3>
                <div className="grid grid-cols-2 gap-2">
                  <StatItem label="Weapon" value={character?.equipped_weapon || 'Fists'} icon={Swords} color="text-orange-400" />
                  <StatItem label="Armor" value={character?.equipped_armor || 'None'} icon={Shield} color="text-slate-400" />
                </div>
              </div>
              
              {/* Resources (for Sirix-1) */}
              {isTranscendent && userProfile?.resources && (
                <div className="space-y-2">
                  <h3 className="font-cinzel text-sm text-gold border-b border-gold/30 pb-1">Resources</h3>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-black/20 rounded">
                      <div className="text-lg font-mono text-gold">∞</div>
                      <div className="text-xs text-muted-foreground">Gold</div>
                    </div>
                    <div className="p-2 bg-black/20 rounded">
                      <div className="text-lg font-mono text-purple-400">∞</div>
                      <div className="text-xs text-muted-foreground">Essence</div>
                    </div>
                    <div className="p-2 bg-black/20 rounded">
                      <div className="text-lg font-mono text-cyan-400">∞</div>
                      <div className="text-xs text-muted-foreground">Artifacts</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Location */}
              <div className="flex items-center justify-between p-3 bg-obsidian/50 rounded">
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <MapPin className="w-4 h-4 text-gold" />
                  Current Location
                </span>
                <span className="font-mono text-sm text-foreground capitalize">
                  {character?.current_location?.replace(/_/g, ' ') || 'Unknown'}
                </span>
              </div>
            </div>
          </ScrollArea>
        )}
      </Card>
    </div>
  );
};

export default CharacterStatsPanel;
