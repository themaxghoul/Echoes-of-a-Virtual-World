import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft, Gem, Crown, Zap, Palette, Frame, Type, Check,
  Sparkles, RefreshCw, Clock
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import PixelAvatar, { FRAME_CLASSES } from '@/components/PixelAvatar';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RARITY_STYLES = {
  common: 'border-zinc-500/40 text-zinc-400',
  uncommon: 'border-green-500/40 text-green-400',
  rare: 'border-blue-500/40 text-blue-400',
  epic: 'border-purple-500/40 text-purple-400',
  legendary: 'border-yellow-500/40 text-yellow-400',
};

const CATEGORIES = [
  { id: 'frame', label: 'Frames', icon: Frame },
  { id: 'name_color', label: 'Name Colors', icon: Type },
  { id: 'title', label: 'Titles', icon: Crown },
  { id: 'boost', label: 'Boosts', icon: Zap },
  { id: 'palette', label: 'Palettes', icon: Palette },
];

const VEBoutique = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const [items, setItems] = useState([]);
  const [balance, setBalance] = useState(0);
  const [equipped, setEquipped] = useState({});
  const [boosts, setBoosts] = useState([]);
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [packColors, setPackColors] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [catRes, ownRes, avRes, palRes] = await Promise.all([
        axios.get(`${API}/cosmetics/catalog?user_id=${userId}`),
        axios.get(`${API}/cosmetics/owned/${userId}`),
        axios.get(`${API}/avatar/user/${userId}`),
        axios.get(`${API}/avatar/palettes?user_id=${userId}`)
      ]);
      setItems(catRes.data.items || []);
      setBalance(catRes.data.balance_ve || 0);
      setEquipped(ownRes.data.equipped || {});
      setBoosts(ownRes.data.active_boosts || []);
      setAvatarUrl(avRes.data.data_url);
      const colors = {};
      (palRes.data.packs || []).forEach(p => { colors[p.pack_id] = p.colors; });
      setPackColors(colors);
    } catch (e) {
      toast.error('Failed to load boutique');
    }
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    if (!userId) { navigate('/auth'); return; }
    loadData();
  }, [userId, navigate, loadData]);

  const purchase = async (itemId) => {
    setBusy(itemId);
    try {
      const res = await axios.post(`${API}/cosmetics/purchase`, { user_id: userId, item_id: itemId });
      toast.success(`Purchased ${res.data.name}! (-${res.data.spent_ve} VE$)`);
      await loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Purchase failed');
    }
    setBusy(null);
  };

  const equip = async (itemId) => {
    setBusy(itemId);
    try {
      await axios.post(`${API}/cosmetics/equip`, { user_id: userId, item_id: itemId });
      toast.success(itemId.startsWith('none:') ? 'Unequipped' : 'Equipped!');
      await loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Equip failed');
    }
    setBusy(null);
  };

  const renderPreview = (item) => {
    switch (item.category) {
      case 'frame':
        return <PixelAvatar dataUrl={avatarUrl} frame={item.item_id} size={56} className="mx-auto" testId={`preview-${item.item_id}`} />;
      case 'name_color':
        return <p className="text-center font-bold text-lg" style={{ color: item.hex }}>YourName</p>;
      case 'title':
        return <Badge className="mx-auto block w-fit bg-gold/10 text-gold border-gold/30"><Crown className="w-3 h-3 mr-1 inline" />{item.title_text}</Badge>;
      case 'boost':
        return <Zap className="w-10 h-10 mx-auto text-amber-400" />;
      case 'palette':
        return (
          <div className="flex justify-center gap-1">
            {(packColors[item.item_id] || []).map(c => (
              <div key={c} className="w-4 h-4 rounded-sm border border-black/40" style={{ backgroundColor: c }} />
            ))}
          </div>
        );
      default:
        return <Sparkles className="w-10 h-10 mx-auto text-gold" />;
    }
  };

  const equippableSlot = (item) => item.category === 'frame' ? 'frame' : item.category === 'name_color' ? 'name_color' : item.category === 'title' ? 'title' : null;

  if (loading) {
    return <div className="min-h-screen bg-obsidian flex items-center justify-center"><RefreshCw className="w-8 h-8 text-gold animate-spin" /></div>;
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="boutique-back-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Gem className="w-6 h-6" /> VE$ Boutique
              </h1>
              <p className="text-sm text-muted-foreground">Spend your VE$ on frames, colors, titles &amp; boosts</p>
            </div>
          </div>
          <Badge className="bg-green-500/10 text-green-400 border-green-500/30 text-base px-3 py-1" data-testid="boutique-ve-balance">
            {balance.toFixed(2)} VE$
          </Badge>
        </div>
      </div>

      <div className="max-w-5xl mx-auto p-4">
        {boosts.length > 0 && (
          <Card className="p-3 mb-4 bg-amber-500/5 border-amber-500/30" data-testid="active-boosts-banner">
            <div className="flex items-center gap-2 flex-wrap">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-amber-400 font-medium">Active boosts:</span>
              {boosts.map((b, i) => (
                <Badge key={i} variant="outline" className="border-amber-500/40 text-amber-300">
                  <Clock className="w-3 h-3 mr-1" />
                  {b.boost_type === 'task_reward' ? 'Forge Surge ×1.5' : 'Mind Amplifier ×2'} until {new Date(b.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Badge>
              ))}
            </div>
          </Card>
        )}

        <Tabs defaultValue="frame">
          <TabsList className="bg-surface/50 flex-wrap h-auto">
            {CATEGORIES.map(cat => (
              <TabsTrigger key={cat.id} value={cat.id} data-testid={`tab-${cat.id}`}>
                <cat.icon className="w-4 h-4 mr-1.5" />{cat.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {CATEGORIES.map(cat => (
            <TabsContent key={cat.id} value={cat.id}>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                {items.filter(i => i.category === cat.id).map(item => {
                  const slot = equippableSlot(item);
                  const isEquipped = slot && equipped[slot] === item.item_id;
                  return (
                    <Card key={item.item_id} className={`p-4 bg-surface/50 border ${RARITY_STYLES[item.rarity]?.split(' ')[0] || 'border-border/30'}`} data-testid={`item-${item.item_id}`}>
                      <div className="h-16 flex items-center justify-center mb-3">{renderPreview(item)}</div>
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="font-medium">{item.name}</h3>
                        <Badge variant="outline" className={`text-[10px] capitalize ${RARITY_STYLES[item.rarity]}`}>{item.rarity}</Badge>
                      </div>
                      {item.description && <p className="text-xs text-muted-foreground mb-3">{item.description}</p>}
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-green-400 font-bold">{item.price} VE$</span>
                        {item.consumable ? (
                          <Button size="sm" onClick={() => purchase(item.item_id)} disabled={busy === item.item_id}
                            className="bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30"
                            data-testid={`buy-${item.item_id}`}>
                            {busy === item.item_id ? <RefreshCw className="w-3 h-3 animate-spin" /> : 'Activate'}
                          </Button>
                        ) : !item.owned ? (
                          <Button size="sm" onClick={() => purchase(item.item_id)} disabled={busy === item.item_id || balance < item.price}
                            className="bg-gold text-black hover:bg-gold-light"
                            data-testid={`buy-${item.item_id}`}>
                            {busy === item.item_id ? <RefreshCw className="w-3 h-3 animate-spin" /> : 'Buy'}
                          </Button>
                        ) : isEquipped ? (
                          <Button size="sm" variant="outline" onClick={() => equip(`none:${slot}`)} disabled={busy === item.item_id}
                            className="border-green-500/40 text-green-400" data-testid={`equipped-${item.item_id}`}>
                            <Check className="w-3 h-3 mr-1" /> Equipped
                          </Button>
                        ) : slot ? (
                          <Button size="sm" variant="outline" onClick={() => equip(item.item_id)} disabled={busy === item.item_id}
                            className="border-border/40" data-testid={`equip-${item.item_id}`}>
                            Equip
                          </Button>
                        ) : (
                          <Badge className="bg-green-500/10 text-green-400 border-green-500/30">Owned</Badge>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
              {cat.id === 'palette' && (
                <p className="text-xs text-muted-foreground mt-4">Palette packs unlock new colors in the <button onClick={() => navigate('/avatar-studio')} className="text-gold underline">Avatar Studio</button>.</p>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  );
};

export default VEBoutique;
