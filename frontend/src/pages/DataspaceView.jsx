import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, Brain, Network, Clock, User, 
  Zap, Heart, BookOpen, Loader2 
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_ICONS = {
  memory: Brain,
  skill: Zap,
  relationship: Heart,
  world_knowledge: BookOpen,
};

const CATEGORY_COLORS = {
  memory: 'bg-slate-blue/20 text-slate-blue border-slate-blue/30',
  skill: 'bg-gold/20 text-gold border-gold/30',
  relationship: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  world_knowledge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
};

const DataspaceView = () => {
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({ total_entries: 0, categories: {} });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    const loadDataspace = async () => {
      try {
        const [entriesRes, statsRes] = await Promise.all([
          axios.get(`${API}/dataspace`),
          axios.get(`${API}/dataspace/stats`)
        ]);
        setEntries(entriesRes.data);
        setStats(statsRes.data);
      } catch (error) {
        console.error('Failed to load dataspace:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadDataspace();
  }, []);

  const filteredEntries = selectedCategory === 'all' 
    ? entries 
    : entries.filter(e => e.category === selectedCategory);

  const categories = ['all', 'memory', 'skill', 'relationship', 'world_knowledge'];

  return (
    <div className="min-h-screen bg-obsidian">
      {/* Background Effect */}
      <div 
        className="fixed inset-0 opacity-30"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1762279388956-1c098163a2a8?crop=entropy&cs=srgb&fm=jpg&q=85')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/80 to-obsidian" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <button
              data-testid="back-to-village-btn"
              onClick={() => navigate('/village')}
              className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="font-manrope text-sm">Back to Village</span>
            </button>
            <h1 className="font-cinzel text-lg text-slate-blue tracking-wider flex items-center gap-2">
              <Network className="w-5 h-5" />
              Global Dataspace
            </h1>
            <div className="w-24" />
          </div>
        </header>

        {/* Main */}
        <main className="pt-24 pb-12 px-6">
          <div className="max-w-6xl mx-auto">
            {/* Intro */}
            <div className="text-center mb-12">
              <h2 className="font-cinzel text-3xl sm:text-4xl text-foreground mb-4">
                The Collective Memory
              </h2>
              <p className="font-manrope text-muted-foreground max-w-2xl mx-auto">
                Every interaction within The Echoes is woven into this neural tapestry. 
                The village learns, remembers, and evolves through the experiences of all who visit.
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
              <Card className="bg-surface/80 border-border/50 rounded-sm">
                <CardContent className="p-6 text-center">
                  <div className="font-mono text-3xl text-gold mb-2">{stats.total_entries}</div>
                  <div className="font-manrope text-sm text-muted-foreground">Total Memories</div>
                </CardContent>
              </Card>
              {Object.entries(stats.categories || {}).map(([cat, count]) => {
                const Icon = CATEGORY_ICONS[cat] || Brain;
                return (
                  <Card key={cat} className="bg-surface/80 border-border/50 rounded-sm">
                    <CardContent className="p-6 text-center">
                      <Icon className="w-6 h-6 mx-auto mb-2 text-slate-blue" />
                      <div className="font-mono text-2xl text-foreground mb-1">{count}</div>
                      <div className="font-manrope text-xs text-muted-foreground capitalize">{cat.replace('_', ' ')}</div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-2 mb-8 justify-center">
              {categories.map((cat) => (
                <Button
                  key={cat}
                  data-testid={`filter-${cat}-btn`}
                  onClick={() => setSelectedCategory(cat)}
                  variant={selectedCategory === cat ? 'default' : 'ghost'}
                  className={`font-manrope text-sm rounded-sm capitalize ${
                    selectedCategory === cat 
                      ? 'bg-gold text-black hover:bg-gold-light' 
                      : 'border-border/50 hover:border-slate-blue/50'
                  }`}
                >
                  {cat === 'all' ? 'All' : cat.replace('_', ' ')}
                </Button>
              ))}
            </div>

            {/* Entries */}
            {isLoading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 text-slate-blue animate-spin mx-auto mb-4" />
                <p className="font-manrope text-muted-foreground">Loading collective memory...</p>
              </div>
            ) : filteredEntries.length === 0 ? (
              <Card className="bg-surface/80 border-border/50 rounded-sm max-w-lg mx-auto">
                <CardContent className="p-12 text-center">
                  <Network className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="font-cinzel text-lg text-foreground mb-2">The Dataspace Awaits</h3>
                  <p className="font-manrope text-sm text-muted-foreground mb-6">
                    No memories have been woven yet. Explore the village and interact with its inhabitants 
                    to begin building the collective consciousness.
                  </p>
                  <Button
                    data-testid="explore-village-btn"
                    onClick={() => navigate('/village')}
                    className="bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm"
                  >
                    Explore The Village
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredEntries.map((entry, i) => {
                  const Icon = CATEGORY_ICONS[entry.category] || Brain;
                  const colorClass = CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.memory;
                  
                  return (
                    <Card 
                      key={entry.id || i}
                      className="bg-surface/80 border-border/50 rounded-sm hover:border-slate-blue/50 transition-colors duration-300"
                      style={{ animationDelay: `${i * 50}ms` }}
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center justify-between">
                          <Badge className={`${colorClass} font-mono text-xs rounded-sm`}>
                            <Icon className="w-3 h-3 mr-1" />
                            {entry.category?.replace('_', ' ')}
                          </Badge>
                          <span className="font-mono text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(entry.created_at).toLocaleDateString()}
                          </span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="font-manrope text-sm text-foreground/90 line-clamp-3 mb-3">
                          {entry.value}
                        </p>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <User className="w-3 h-3" />
                          <span className="font-mono text-xs truncate">
                            Learned from: {entry.learned_from?.slice(0, 8)}...
                          </span>
                        </div>
                        {entry.strength && (
                          <div className="mt-2 h-1 bg-obsidian rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-gold to-gold-light"
                              style={{ width: `${(entry.strength / 10) * 100}%` }}
                            />
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Visualization Placeholder */}
            <div className="mt-16">
              <Card className="bg-surface/50 border-border/50 rounded-sm overflow-hidden">
                <div 
                  className="h-64 relative"
                  style={{
                    backgroundImage: `url('https://images.unsplash.com/photo-1762278804798-dd7e493051?crop=entropy&cs=srgb&fm=jpg&q=85')`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-obsidian/60 to-transparent" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <Network className="w-16 h-16 text-slate-blue mx-auto mb-4 animate-pulse" />
                      <h3 className="font-cinzel text-xl text-foreground mb-2">Neural Network Visualization</h3>
                      <p className="font-manrope text-sm text-muted-foreground">
                        Coming in Phase II: Full-Dive Interface
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default DataspaceView;
