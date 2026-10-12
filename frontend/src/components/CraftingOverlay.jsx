// Crafting menu — toggled by C in first-person view.
// Minecraft/Terraria recipe structure, Sims-depth spec sheets on crafted items.
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { X, Hammer, Loader2, CheckCircle2, AlertTriangle, FlaskConical, Armchair, Wrench, Castle, Factory } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CAT_ICONS = { station: Factory, tool: Wrench, furniture: Armchair, scientific: FlaskConical, structure: Castle };
const QUALITY_COLORS = {
  crude: 'text-zinc-400', common: 'text-foreground', fine: 'text-cyan-300',
  superior: 'text-purple-300', masterwork: 'text-amber-300',
};

export const CraftingOverlay = ({ userId, onClose }) => {
  const [recipes, setRecipes] = useState([]);
  const [playerMats, setPlayerMats] = useState({});
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [crafting, setCrafting] = useState(null);
  const [result, setResult] = useState(null);
  const [view, setView] = useState('recipes');

  const load = useCallback(async () => {
    try {
      const [recRes, itemsRes] = await Promise.all([
        axios.get(`${API}/crafting/recipes/${userId}`),
        axios.get(`${API}/crafting/items/${userId}`),
      ]);
      setRecipes(recRes.data.recipes || []);
      setPlayerMats(recRes.data.player_materials || {});
      setItems(itemsRes.data.items || []);
    } catch {
      toast.error('Failed to load crafting data');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { if (userId) load(); }, [userId, load]);

  const craft = async (recipeId) => {
    setCrafting(recipeId);
    try {
      const res = await axios.post(`${API}/crafting/craft`, { user_id: userId, recipe_id: recipeId });
      setResult(res.data.item);
      toast.success(`Crafted ${res.data.item.quality.toUpperCase()} ${res.data.item.name}!`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Crafting failed');
    } finally {
      setCrafting(null);
    }
  };

  const SpecSheet = ({ item }) => (
    <div className="space-y-1 font-mono text-[11px]">
      <div className="flex justify-between"><span className="text-muted-foreground">Durability</span><span>{item.specs.durability} / {item.specs.max_durability}</span></div>
      <div className="flex justify-between"><span className="text-muted-foreground">Weight</span><span>{item.specs.weight_kg} kg</span></div>
      <div className="flex justify-between"><span className="text-muted-foreground">Aesthetics</span><span>{item.specs.aesthetics}/10</span></div>
      <div className="flex justify-between"><span className="text-muted-foreground">Utility</span><span>{item.specs.utility}/10</span></div>
      {item.specs.comfort != null && <div className="flex justify-between"><span className="text-muted-foreground">Comfort</span><span>{item.specs.comfort}/10</span></div>}
      {item.specs.precision != null && <div className="flex justify-between"><span className="text-muted-foreground">Precision</span><span>{item.specs.precision}/10</span></div>}
      <div className="flex justify-between"><span className="text-muted-foreground">Composition</span><span>{Object.entries(item.specs.material_composition).map(([m, n]) => `${m}×${n}`).join(' ')}</span></div>
    </div>
  );

  return (
    <div className="absolute inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4" data-testid="crafting-overlay">
      <div className="w-full max-w-3xl bg-obsidian/95 border border-border/40 rounded-sm shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border/30 sticky top-0 bg-obsidian/95 z-10">
          <div className="flex items-center gap-2">
            <Hammer className="w-5 h-5 text-gold" />
            <h2 className="font-cinzel text-lg">Crafting Workshop</h2>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
              {Object.entries(playerMats).map(([m, n]) => <span key={m}>{m}: <span className="text-gold">{n}</span></span>)}
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">C / ESC to close</Badge>
            <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-sm" data-testid="crafting-close-btn">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex gap-2 p-3 border-b border-border/20">
          <Button size="sm" variant={view === 'recipes' ? 'default' : 'ghost'} onClick={() => setView('recipes')}
            className="rounded-sm" data-testid="crafting-view-recipes">Recipes</Button>
          <Button size="sm" variant={view === 'items' ? 'default' : 'ghost'} onClick={() => setView('items')}
            className="rounded-sm" data-testid="crafting-view-items">My Items ({items.length})</Button>
        </div>

        {loading ? (
          <div className="p-12 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-gold" /></div>
        ) : view === 'recipes' ? (
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="recipe-grid">
            {recipes.map(r => {
              const Icon = CAT_ICONS[r.category] || Hammer;
              return (
                <div key={r.recipe_id} className={`p-3 border rounded-sm ${r.craftable ? 'border-gold/30 bg-gold/5' : 'border-border/20 bg-surface/30 opacity-80'}`}
                  data-testid={`recipe-${r.recipe_id}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-4 h-4 text-gold" />
                    <span className="text-sm font-medium">{r.name}</span>
                    <Badge variant="outline" className="text-[9px] ml-auto uppercase">{r.category}</Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground mb-2">{r.desc}</p>
                  <div className="font-mono text-[11px] mb-2">
                    {Object.entries(r.materials).map(([m, n]) => (
                      <span key={m} className={`mr-2 ${(playerMats[m] || 0) >= n ? 'text-emerald-400' : 'text-red-400'}`}>{m}×{n}</span>
                    ))}
                    {r.station && (
                      <span className={r.station_owned ? 'text-emerald-400' : 'text-red-400'}>
                        · needs {r.station}
                      </span>
                    )}
                  </div>
                  <Button size="sm" onClick={() => craft(r.recipe_id)} disabled={!r.craftable || crafting === r.recipe_id}
                    className="w-full rounded-sm bg-gold/80 text-black hover:bg-gold disabled:opacity-40"
                    data-testid={`craft-btn-${r.recipe_id}`}>
                    {crafting === r.recipe_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> :
                      r.craftable ? <><CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />Craft</> :
                        <><AlertTriangle className="w-3.5 h-3.5 mr-1.5" />{r.station_owned ? 'Missing materials' : 'Station required'}</>}
                  </Button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="items-grid">
            {items.length === 0 && <p className="text-xs text-muted-foreground col-span-2">Nothing crafted yet. Start with a Workbench.</p>}
            {items.map(item => (
              <div key={item.item_id} className="p-3 border border-border/20 bg-surface/30 rounded-sm">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{item.name}</span>
                  <span className={`text-[10px] font-cinzel uppercase ${QUALITY_COLORS[item.quality]}`}>{item.quality}</span>
                </div>
                <p className="text-[10px] italic text-muted-foreground mb-2">"{item.flavor}"</p>
                <SpecSheet item={item} />
              </div>
            ))}
          </div>
        )}

        {/* Craft result modal */}
        {result && (
          <div className="absolute inset-0 bg-black/80 z-20 flex items-center justify-center p-4" onClick={() => setResult(null)}>
            <div className="w-full max-w-sm bg-obsidian border border-gold/40 rounded-sm p-5" onClick={e => e.stopPropagation()}
              data-testid="craft-result-modal">
              <div className="text-center mb-3">
                <Hammer className="w-8 h-8 mx-auto text-gold mb-2" />
                <h3 className="font-cinzel">{result.name}</h3>
                <span className={`text-xs font-cinzel uppercase ${QUALITY_COLORS[result.quality]}`}>{result.quality} quality</span>
                <p className="text-[11px] italic text-muted-foreground mt-1">"{result.flavor}"</p>
              </div>
              <SpecSheet item={result} />
              <Button onClick={() => setResult(null)} size="sm" className="w-full mt-4 rounded-sm" data-testid="craft-result-close">
                Collect
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CraftingOverlay;
