// Economy Nexus — The hybrid-growth VE economy: VE0 (proto) → VE Vouchers → VE$ (final).
// BTC-indexed via CoinGecko, simulation-native mining, Quantum Awakening milestone.
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  ArrowLeft, Atom, Coins, Lock, Ticket, Sparkles, TrendingUp, Zap,
  Bitcoin, ShoppingBag, Palette, ShoppingCart, Award, Loader2, ChevronRight,
  BookOpen, Pickaxe, ShieldCheck, Settings2, Radio, Footprints, Brain, Timer
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { pushNavHistory } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_STYLE = {
  bronze: { color: 'text-orange-400', border: 'border-orange-500/40', bg: 'bg-orange-500/10' },
  silver: { color: 'text-zinc-300', border: 'border-zinc-400/40', bg: 'bg-zinc-400/10' },
  gold: { color: 'text-amber-300', border: 'border-amber-400/40', bg: 'bg-amber-400/10' },
  quantum: { color: 'text-cyan-300', border: 'border-cyan-400/40', bg: 'bg-cyan-400/10' },
  systemic: { color: 'text-fuchsia-300', border: 'border-fuchsia-400/40', bg: 'bg-fuchsia-400/10' },
};

const CHANNEL_ICONS = {
  presence: Timer,
  xr_spatial: Footprints,
  ai_cognitive: Brain,
  quantum_entropy: Atom,
};

const SPEND_LINKS = [
  { path: '/store', icon: ShoppingCart, title: 'In-App Store', body: 'Stripe top-ups, compute subscriptions, civilization structures.' },
  { path: '/boutique', icon: ShoppingBag, title: 'VE$ Boutique', body: 'Frames, colors, titles and boosts — spend VE$ once it activates.' },
  { path: '/avatar-studio', icon: Palette, title: 'Avatar Studio', body: '64×64 pixel identity canvas with premium palettes.' },
  { path: '/leaderboard', icon: Award, title: 'Leaderboard', body: 'See who climbs the rankings.' },
];

const EconomyNexus = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const isAdmin = userId === 'sirix_1_supreme';

  const [status, setStatus] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stabilizing, setStabilizing] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [adminForm, setAdminForm] = useState({});
  const [savingConfig, setSavingConfig] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [statusRes, walletRes, ledgerRes] = await Promise.all([
        axios.get(`${API}/hybrid-economy/status`),
        axios.get(`${API}/hybrid-economy/wallet/${userId}`),
        axios.get(`${API}/hybrid-economy/ledger/${userId}?limit=15`).catch(() => ({ data: { entries: [] } })),
      ]);
      setStatus(statusRes.data);
      setWallet(walletRes.data);
      setLedger(ledgerRes.data.entries || []);
    } catch {
      toast.error('Failed to load economy data');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    pushNavHistory('/economy');
    if (!userId) { navigate('/auth'); return; }
    loadAll();
  }, [userId, navigate, loadAll]);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const t = setTimeout(() => setCooldown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const stabilize = async () => {
    setStabilizing(true);
    try {
      const amount = 3 + Math.random() * 5;
      const res = await axios.post(`${API}/hybrid-economy/mine`, {
        entity_id: userId, channel: 'quantum_entropy', amount, source: 'stabilizer',
      });
      const d = res.data;
      if (d.minted > 0) {
        toast.success(`Quantum field stabilized: +${d.minted} ${d.currency} · entropy +${d.entropy_contributed}`);
        if (d.vouchers_awarded?.length) {
          d.vouchers_awarded.forEach(v => toast.success(`VE Voucher earned: ${v.tier.toUpperCase()}!`, { duration: 6000 }));
        }
      } else {
        toast.info('Daily quantum cap reached — the field rests until tomorrow.');
      }
      setCooldown(20);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Stabilization failed');
    } finally {
      setStabilizing(false);
    }
  };

  const saveConfig = async () => {
    setSavingConfig(true);
    try {
      const payload = { admin_id: userId };
      Object.entries(adminForm).forEach(([k, v]) => {
        if (v !== '' && v !== undefined) payload[k] = k === 'clear_btc_override' ? v : parseFloat(v);
      });
      await axios.put(`${API}/hybrid-economy/config`, payload);
      toast.success('Economy parameters updated');
      setAdminForm({});
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Config update failed');
    } finally {
      setSavingConfig(false);
    }
  };

  const forceLaunch = async () => {
    if (!window.confirm('Force the Quantum Awakening NOW? VE0 converts, vouchers evaluate, the Gold Mine springs. This cannot be undone.')) return;
    try {
      const res = await axios.post(`${API}/hybrid-economy/launch/force`, { admin_id: userId });
      toast.success(`ECONOMY LAUNCHED — VE index ${res.data.ve_index} @ BTC $${res.data.btc_price.toLocaleString()}`);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Launch failed');
    }
  };

  if (loading || !status || !wallet) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center" data-testid="economy-nexus-loading">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    );
  }

  const launched = status.launched;
  const pct = status.progress_pct || 0;

  return (
    <div className="min-h-screen bg-obsidian text-foreground" data-testid="economy-nexus-page">
      <header className="sticky top-0 z-30 bg-obsidian/90 backdrop-blur-md border-b border-border/30">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <button onClick={() => navigate('/select-mode')}
            className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition"
            data-testid="nexus-back-btn">
            <ArrowLeft className="w-5 h-5" />
            <span className="font-cinzel text-sm hidden sm:inline">Modes</span>
          </button>
          <div className="flex items-center gap-2">
            <Atom className="w-5 h-5 text-amber-400" />
            <h1 className="font-cinzel text-lg sm:text-xl tracking-wide">Economy Nexus</h1>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-sm">
            <Coins className="w-4 h-4 text-amber-400" />
            <span className="font-mono text-sm text-amber-300" data-testid="nexus-ve0-balance">
              {wallet.balance_ve0.toFixed(2)} VE₀
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-5">
        {/* Awakening banner / milestone */}
        {launched ? (
          <Card className="bg-gradient-to-r from-amber-500/20 via-yellow-500/10 to-amber-500/20 border-amber-400/50 rounded-sm" data-testid="awakening-banner">
            <CardContent className="p-5 text-center">
              <Sparkles className="w-8 h-8 mx-auto text-amber-300 mb-2" />
              <h2 className="font-cinzel text-xl text-amber-200">THE QUANTUM AWAKENING HAS OCCURRED</h2>
              <p className="text-sm text-amber-100/80 mt-1">
                {status.gold_mine?.name || 'The Gold Mine'} sprang from the digital landscape at {status.gold_mine?.location_id}.
                VE$ is live — launch index {status.launch_ve_value} @ BTC ${Number(status.launch_btc_price || 0).toLocaleString()}.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-gradient-to-br from-cyan-500/10 via-indigo-500/5 to-transparent border-cyan-500/30 rounded-sm" data-testid="milestone-card">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
                  <h2 className="font-cinzel text-sm tracking-wider">QUANTUM COMPUTATIONS — THE AWAKENING</h2>
                </div>
                <span className="font-mono text-xs text-cyan-300" data-testid="milestone-pct">{pct.toFixed(1)}%</span>
              </div>
              <Progress value={pct} className="h-2 mb-2" />
              <p className="text-xs text-muted-foreground">
                When the quantum computations complete ({Math.round(status.quantum_progress).toLocaleString()} / {Math.round(status.milestone_target).toLocaleString()} entropy),
                a huge gold mine springs from the digital landscape. VE₀ converts to VE$, and every voucher pays out against the BTC index. Every action you take feeds the field.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Currency triptych */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Card className="bg-gradient-to-br from-amber-500/10 to-transparent border-amber-500/30 rounded-sm" data-testid="currency-ve0">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <Coins className="w-4 h-4 text-amber-400" />
                <h3 className="font-cinzel text-sm">VE₀ — Proto-Currency</h3>
                <Badge className="bg-amber-500/20 text-amber-300 text-[10px] ml-auto">{launched ? 'CONVERTED' : 'ACTIVE'}</Badge>
              </div>
              <p className="font-mono text-2xl text-amber-300">{wallet.balance_ve0.toFixed(2)}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Earned right now through presence, movement, AI chat and quantum work.
                Converts to VE$ at {status.params.ve0_conversion_ratio}:1 on launch.
              </p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-indigo-500/10 to-transparent border-indigo-500/30 rounded-sm" data-testid="currency-vouchers">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <Ticket className="w-4 h-4 text-indigo-400" />
                <h3 className="font-cinzel text-sm">VE Vouchers</h3>
                <Badge className="bg-indigo-500/20 text-indigo-300 text-[10px] ml-auto">FUTURE-VALUE</Badge>
              </div>
              <p className="font-mono text-2xl text-indigo-300">{wallet.voucher_count}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                BTC-indexed certificates. Sealed until launch, then each pays f(BTC) × its BTC percentage in VE$.
              </p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-emerald-500/10 to-transparent border-emerald-500/30 rounded-sm" data-testid="currency-ve">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                {launched ? <Coins className="w-4 h-4 text-emerald-400" /> : <Lock className="w-4 h-4 text-emerald-400" />}
                <h3 className="font-cinzel text-sm">VE$ — Final Currency</h3>
                <Badge className="bg-emerald-500/20 text-emerald-300 text-[10px] ml-auto">{launched ? 'LIVE' : 'LOCKED'}</Badge>
              </div>
              <p className="font-mono text-2xl text-emerald-300">{wallet.balance_ve.toFixed(2)}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                {launched ? 'Simulation-native currency, scaling with BTC momentum. Spend it below.' : 'Activates at the Quantum Awakening. Not pegged, not mined — simulation-native.'}
              </p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="bg-surface/60 border border-border/30 rounded-sm flex flex-wrap h-auto w-full sm:w-auto">
            <TabsTrigger value="overview" data-testid="tab-overview"><TrendingUp className="w-4 h-4 mr-1.5" />Overview</TabsTrigger>
            <TabsTrigger value="mining" data-testid="tab-mining"><Pickaxe className="w-4 h-4 mr-1.5" />Mining</TabsTrigger>
            <TabsTrigger value="vouchers" data-testid="tab-vouchers"><Ticket className="w-4 h-4 mr-1.5" />Vouchers</TabsTrigger>
            <TabsTrigger value="guide" data-testid="tab-guide"><BookOpen className="w-4 h-4 mr-1.5" />Guide</TabsTrigger>
            <TabsTrigger value="spend" data-testid="tab-spend"><ShoppingBag className="w-4 h-4 mr-1.5" />Spend</TabsTrigger>
            {isAdmin && <TabsTrigger value="admin" data-testid="tab-admin"><Settings2 className="w-4 h-4 mr-1.5" />Admin</TabsTrigger>}
          </TabsList>

          {/* OVERVIEW */}
          <TabsContent value="overview" className="mt-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="bg-surface/50 border-border/30 rounded-sm" data-testid="btc-index-card">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Bitcoin className="w-4 h-4 text-orange-400" />
                    <h3 className="font-cinzel text-sm">BTC-Indexed Valuation</h3>
                    <Badge variant="outline" className="text-[10px] ml-auto">{status.btc.source}</Badge>
                  </div>
                  <div className="flex items-end gap-6">
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Bitcoin</p>
                      <p className="font-mono text-xl text-orange-300" data-testid="btc-price">
                        ${Number(status.btc.price).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">VE$ Index f(BTC)</p>
                      <p className="font-mono text-xl text-emerald-300" data-testid="ve-index">{status.ve_index.value}</p>
                    </div>
                  </div>
                  <div className="mt-3 p-2 bg-black/30 rounded-sm font-mono text-[11px] text-muted-foreground">
                    f(BTC) = α·ln(BTC) + β + γ·BTC^δ<br />
                    = {status.ve_index.log_term} (log stability) + {status.ve_index.beta} (floor) + {status.ve_index.poly_term} (hype surge)
                    {status.ve_index.capped && <span className="text-red-400"> · capped at 1% BTC</span>}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-2" data-testid="coingecko-attribution">
                    {status.btc.attribution}
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-cyan-500/10 to-transparent border-cyan-500/30 rounded-sm" data-testid="stabilizer-card">
                <CardContent className="p-4 flex flex-col h-full">
                  <div className="flex items-center gap-2 mb-2">
                    <Atom className="w-4 h-4 text-cyan-400" />
                    <h3 className="font-cinzel text-sm">Quantum Field Stabilizer</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3 flex-1">
                    Extract entropy from quantum events. Each stabilization mints {launched ? 'VE$' : 'VE₀'} and
                    pushes the world toward the Awakening. Today: {wallet.today.quantum_entropy.used} / {wallet.today.quantum_entropy.cap} VE₀.
                  </p>
                  <Button onClick={stabilize} disabled={stabilizing || cooldown > 0}
                    className="bg-gradient-to-r from-cyan-500 to-indigo-500 text-black font-cinzel rounded-sm hover:opacity-90"
                    data-testid="stabilize-btn">
                    {stabilizing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                    {cooldown > 0 ? `Re-charging (${cooldown}s)` : 'Stabilize Quantum Field'}
                  </Button>
                </CardContent>
              </Card>
            </div>

            <Card className="bg-surface/50 border-border/30 rounded-sm">
              <CardContent className="p-4">
                <h3 className="font-cinzel text-sm mb-3">Network Supply</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div data-testid="supply-ve0">
                    <p className="text-[10px] text-muted-foreground uppercase">Total VE₀</p>
                    <p className="font-mono text-lg text-amber-300">{Math.round(status.supply.total_ve0).toLocaleString()}</p>
                  </div>
                  <div data-testid="supply-ve">
                    <p className="text-[10px] text-muted-foreground uppercase">Total VE$</p>
                    <p className="font-mono text-lg text-emerald-300">{Math.round(status.supply.total_ve).toLocaleString()}</p>
                  </div>
                  <div data-testid="supply-vouchers">
                    <p className="text-[10px] text-muted-foreground uppercase">Vouchers Issued</p>
                    <p className="font-mono text-lg text-indigo-300">
                      {Object.values(status.supply.vouchers_by_tier || {}).reduce((a, b) => a + b, 0)}
                    </p>
                  </div>
                  <div data-testid="supply-miners">
                    <p className="text-[10px] text-muted-foreground uppercase">Active Miners</p>
                    <p className="font-mono text-lg text-cyan-300">{status.supply.active_miners}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* MINING */}
          <TabsContent value="mining" className="mt-5 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="mining-channels">
              {Object.entries(status.channels).map(([key, ch]) => {
                const Icon = CHANNEL_ICONS[key] || Zap;
                const today = wallet.today[key] || { used: 0, cap: ch.daily_cap };
                const lifetime = wallet.mining_totals[key] || 0;
                return (
                  <Card key={key} className="bg-surface/50 border-border/30 rounded-sm" data-testid={`channel-${key}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className="w-4 h-4 text-cyan-400" />
                        <h3 className="font-cinzel text-sm">{ch.label}</h3>
                        <span className="font-mono text-[10px] text-muted-foreground ml-auto">entropy ×{ch.entropy}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mb-2">{ch.how}</p>
                      <Progress value={(today.used / today.cap) * 100} className="h-1.5 mb-1" />
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-amber-300">Today: {today.used} / {today.cap}</span>
                        <span className="text-muted-foreground">Lifetime: {lifetime.toFixed(1)}</span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            <Card className="bg-surface/50 border-border/30 rounded-sm">
              <CardContent className="p-4">
                <h3 className="font-cinzel text-sm mb-3">Recent Mining Ledger</h3>
                {ledger.length === 0 ? (
                  <p className="text-xs text-muted-foreground" data-testid="ledger-empty">
                    No entries yet. Enter the world, talk to NPCs, or stabilize the quantum field to begin minting VE₀.
                  </p>
                ) : (
                  <div className="space-y-1.5" data-testid="ledger-list">
                    {ledger.map(e => (
                      <div key={e.entry_id} className="flex items-center justify-between text-[11px] font-mono border-b border-border/20 pb-1.5">
                        <span className="text-muted-foreground">{status.channels[e.channel]?.label || e.channel}</span>
                        <span className="text-cyan-400">entropy +{e.entropy}</span>
                        <span className="text-amber-300">+{e.ve0} {e.currency}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* VOUCHERS */}
          <TabsContent value="vouchers" className="mt-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2" data-testid="voucher-tiers">
              {Object.entries(status.voucher_tiers).map(([tier, info]) => {
                const s = TIER_STYLE[tier];
                const owned = (wallet.vouchers || []).filter(v => v.tier === tier).length;
                return (
                  <Card key={tier} className={`${s.bg} ${s.border} rounded-sm`} data-testid={`tier-${tier}`}>
                    <CardContent className="p-3 text-center">
                      <Ticket className={`w-5 h-5 mx-auto mb-1 ${s.color}`} />
                      <p className={`font-cinzel text-xs ${s.color}`}>{info.label}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{info.btc_units} BTC-unit</p>
                      <p className="font-mono text-lg mt-1">{owned}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            <Card className="bg-surface/50 border-border/30 rounded-sm">
              <CardContent className="p-4">
                <h3 className="font-cinzel text-sm mb-2">How Vouchers Are Earned</h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Vouchers auto-mint when your lifetime mining in any channel crosses these thresholds — rewarding
                  infrastructure building, quantum stabilization, XR world presence and AI cognition:
                </p>
                <div className="flex flex-wrap gap-2">
                  {status.voucher_ladder.map(l => (
                    <Badge key={l.tier} variant="outline" className={`${TIER_STYLE[l.tier].color} text-[10px]`}>
                      {l.threshold} VE₀ → {l.tier.toUpperCase()}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {(wallet.vouchers || []).length > 0 && (
              <Card className="bg-surface/50 border-border/30 rounded-sm">
                <CardContent className="p-4">
                  <h3 className="font-cinzel text-sm mb-3">Your Vouchers ({wallet.voucher_count})</h3>
                  <div className="space-y-1.5" data-testid="voucher-list">
                    {wallet.vouchers.map(v => (
                      <div key={v.voucher_id} className="flex items-center justify-between text-[11px] font-mono border-b border-border/20 pb-1.5">
                        <span className={TIER_STYLE[v.tier]?.color}>{v.tier.toUpperCase()}</span>
                        <span className="text-muted-foreground">{v.earned_via}</span>
                        <span className={v.redeemed ? 'text-emerald-300' : 'text-muted-foreground'}>
                          {v.redeemed ? `paid ${v.ve_payout} VE$` : 'sealed until launch'}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* GUIDE */}
          <TabsContent value="guide" className="mt-5">
            <Card className="bg-surface/50 border-border/30 rounded-sm" data-testid="guide-card">
              <CardContent className="p-5 space-y-4 text-sm leading-relaxed">
                <div>
                  <h3 className="font-cinzel text-amber-300 mb-1">1. The Three Currencies</h3>
                  <p className="text-muted-foreground text-xs">
                    <strong className="text-amber-300">VE₀</strong> is the warm-up currency — you earn it right now just by playing.
                    <strong className="text-indigo-300"> VE Vouchers</strong> are sealed golden tickets whose value is decided later by Bitcoin's price.
                    <strong className="text-emerald-300"> VE$</strong> is the real deal — it switches on when the Quantum Awakening happens.
                    Your old VE$ was converted 1:1 into VE₀, so nothing was lost.
                  </p>
                </div>
                <div>
                  <h3 className="font-cinzel text-cyan-300 mb-1">2. How To Earn (no tasks, no gigs — just play)</h3>
                  <p className="text-muted-foreground text-xs">
                    Be in the world (XR Presence), move and interact (Spatial Work), talk to NPCs (AI Cognitive Yield),
                    and press the Stabilizer here (Quantum Entropy). Daily caps keep it fair. There is no hashing,
                    no proof-of-work — "mining" means contributing to the simulation's stability and intelligence.
                  </p>
                </div>
                <div>
                  <h3 className="font-cinzel text-orange-300 mb-1">3. The Bitcoin Connection (without the risk)</h3>
                  <p className="text-muted-foreground text-xs">
                    VE$'s value follows the formula f(BTC) = α·ln(BTC) + β + γ·BTC^δ. The log part keeps it calm and stable,
                    the power part lets it surge when Bitcoin hypes. It can never exceed 1% of BTC, is never pegged,
                    never collateralized, and no crypto is ever touched. {status.btc.attribution}.
                  </p>
                </div>
                <div>
                  <h3 className="font-cinzel text-fuchsia-300 mb-1">4. The Quantum Awakening</h3>
                  <p className="text-muted-foreground text-xs">
                    Every bit of entropy the whole community generates fills the milestone bar. When quantum computations
                    complete, a giant gold mine — The Aurum Breach — erupts from the landscape. At that instant: VE₀ converts to
                    VE$ ({status.params.ve0_conversion_ratio}:1), and each voucher pays f(BTC at launch) × its BTC percentage.
                  </p>
                </div>
                <div>
                  <h3 className="font-cinzel text-emerald-300 mb-1">5. Why It Can't Be Copied</h3>
                  <p className="text-muted-foreground text-xs">
                    No ASIC farm or quantum computer can farm this — value only emerges from presence, cognition and
                    contribution inside this simulation. External speculation is impossible before launch because
                    nothing is tradeable until the Awakening.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* SPEND */}
          <TabsContent value="spend" className="mt-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="spend-links">
              {SPEND_LINKS.map(e => {
                const Icon = e.icon;
                return (
                  <Card key={e.path} onClick={() => { pushNavHistory(e.path); navigate(e.path); }}
                    className="bg-gradient-to-br from-fuchsia-500/10 to-transparent border-fuchsia-500/30 rounded-sm hover:scale-[1.01] transition cursor-pointer"
                    data-testid={`spend-${e.path.replace('/', '')}`}>
                    <CardContent className="p-4 flex items-start gap-3">
                      <div className="p-2 rounded-sm bg-black/40 text-fuchsia-300"><Icon className="w-5 h-5" /></div>
                      <div className="flex-1">
                        <h3 className="font-cinzel text-sm">{e.title}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">{e.body}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-muted-foreground/40 self-center" />
                    </CardContent>
                  </Card>
                );
              })}
            </div>
            {!launched && (
              <p className="text-[11px] text-muted-foreground mt-3 flex items-center gap-1.5">
                <Lock className="w-3 h-3" /> VE$ spending unlocks at the Quantum Awakening. Stripe top-ups remain available.
              </p>
            )}
          </TabsContent>

          {/* ADMIN */}
          {isAdmin && (
            <TabsContent value="admin" className="mt-5 space-y-4">
              <Card className="bg-surface/50 border-red-500/30 rounded-sm" data-testid="admin-panel">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-red-400" />
                    <h3 className="font-cinzel text-sm">Economy Control — Sirix Supreme</h3>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {[
                      ['alpha', 'α baseline'], ['beta', 'β floor'], ['gamma', 'γ multiplier'], ['delta', 'δ exponent'],
                      ['ve0_conversion_ratio', 'VE₀→VE$ ratio'], ['voucher_unit_multiplier', 'Voucher mult'],
                      ['milestone_target', 'Milestone target'], ['btc_override', 'BTC override'],
                    ].map(([key, label]) => (
                      <div key={key}>
                        <label className="text-[10px] text-muted-foreground uppercase">{label}</label>
                        <Input type="number" step="any"
                          placeholder={String(key === 'milestone_target' ? status.milestone_target : (status.params[key] ?? ''))}
                          value={adminForm[key] ?? ''}
                          onChange={e => setAdminForm(f => ({ ...f, [key]: e.target.value }))}
                          className="h-8 font-mono text-xs rounded-sm"
                          data-testid={`admin-input-${key}`} />
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={saveConfig} disabled={savingConfig} size="sm"
                      className="bg-cyan-600 hover:bg-cyan-500 rounded-sm" data-testid="admin-save-btn">
                      {savingConfig ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : null} Save Parameters
                    </Button>
                    <Button onClick={() => { setAdminForm(f => ({ ...f, clear_btc_override: true })); toast.info('Override will clear on save'); }}
                      size="sm" variant="outline" className="rounded-sm" data-testid="admin-clear-override-btn">
                      Clear BTC Override
                    </Button>
                    {!launched && (
                      <Button onClick={forceLaunch} size="sm"
                        className="bg-gradient-to-r from-amber-500 to-red-500 text-black font-cinzel rounded-sm ml-auto"
                        data-testid="admin-force-launch-btn">
                        <Sparkles className="w-3 h-3 mr-1" /> Force Quantum Awakening
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </main>
    </div>
  );
};

export default EconomyNexus;
