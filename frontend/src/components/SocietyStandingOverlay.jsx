// Societal Standing menu — toggled by Tab in first-person view.
// Social / Political / Economic / Undercover standing with cover identity controls.
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { X, Users, Landmark, Coins, VenetianMask, Loader2, UserCheck, UserMinus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_META = {
  social: { icon: Users, color: 'text-cyan-400', bar: 'bg-cyan-400', label: 'Social Standing' },
  political: { icon: Landmark, color: 'text-purple-400', bar: 'bg-purple-400', label: 'Political Standing' },
  economic: { icon: Coins, color: 'text-amber-400', bar: 'bg-amber-400', label: 'Economic Standing' },
  undercover: { icon: VenetianMask, color: 'text-red-400', bar: 'bg-red-400', label: 'Undercover Standing' },
};

export const SocietyStandingOverlay = ({ userId, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alias, setAlias] = useState('');
  const [persona, setPersona] = useState('');
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/society/standing/${userId}`);
      setData(res.data);
    } catch {
      toast.error('Failed to load standings');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { if (userId) load(); }, [userId, load]);

  const adoptCover = async () => {
    if (!alias.trim()) { toast.error('Choose an alias first'); return; }
    setWorking(true);
    try {
      await axios.post(`${API}/society/cover/adopt`, { user_id: userId, alias: alias.trim(), persona: persona.trim() });
      toast.success(`You are now undercover as "${alias.trim()}"`);
      setAlias(''); setPersona('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Cover adoption failed');
    } finally { setWorking(false); }
  };

  const dropCover = async () => {
    setWorking(true);
    try {
      await axios.post(`${API}/society/cover/drop`, { user_id: userId });
      toast.success('Cover identity dropped');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to drop cover');
    } finally { setWorking(false); }
  };

  return (
    <div className="absolute inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4" data-testid="society-overlay">
      <div className="w-full max-w-2xl bg-obsidian/95 border border-border/40 rounded-sm shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border/30 sticky top-0 bg-obsidian/95 z-10">
          <div>
            <h2 className="font-cinzel text-lg">Societal Standing</h2>
            {data && (
              <p className="text-xs text-muted-foreground">
                Overall: <span className="text-gold">{data.overall.rank}</span> ({data.overall.score})
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] font-mono">TAB / ESC to close</Badge>
            <button onClick={onClose} className="p-1.5 hover:bg-white/10 rounded-sm" data-testid="society-close-btn">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading || !data ? (
          <div className="p-12 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-gold" /></div>
        ) : (
          <div className="p-4 space-y-4">
            {Object.entries(data.standings).map(([key, s]) => {
              const meta = CATEGORY_META[key];
              const Icon = meta.icon;
              return (
                <div key={key} className="p-3 bg-surface/40 border border-border/20 rounded-sm" data-testid={`standing-${key}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${meta.color}`} />
                      <span className="text-sm font-medium">{meta.label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-cinzel ${meta.color}`}>{s.rank}</span>
                      <span className="font-mono text-xs text-muted-foreground">{s.score}</span>
                    </div>
                  </div>
                  <Progress value={s.score} className="h-1.5 mb-1.5" />
                  <p className="text-[11px] text-muted-foreground">{s.detail}</p>
                </div>
              );
            })}

            {/* Cover identity controls */}
            <div className="p-3 bg-red-500/5 border border-red-500/20 rounded-sm" data-testid="cover-identity-section">
              <div className="flex items-center gap-2 mb-2">
                <VenetianMask className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium">Disguise / Undercover Operations</span>
              </div>
              {data.cover_identity ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Operating as <span className="text-red-300 font-cinzel">"{data.cover_identity.alias}"</span>
                    {data.cover_identity.persona && <> — {data.cover_identity.persona}</>}
                    <span className="font-mono"> · integrity {data.cover_identity.integrity}</span>
                  </p>
                  <Button onClick={dropCover} disabled={working} size="sm" variant="outline"
                    className="border-red-500/40 text-red-400 hover:bg-red-500/10 rounded-sm" data-testid="drop-cover-btn">
                    <UserMinus className="w-3.5 h-3.5 mr-1.5" /> Drop Cover
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-[11px] text-muted-foreground">
                    Adopt a false identity to move unseen. Exposure actions erode integrity.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input value={alias} onChange={e => setAlias(e.target.value)} placeholder="Alias name"
                      className="h-8 text-xs rounded-sm" data-testid="cover-alias-input" />
                    <Input value={persona} onChange={e => setPersona(e.target.value)} placeholder="Persona (optional)"
                      className="h-8 text-xs rounded-sm" data-testid="cover-persona-input" />
                    <Button onClick={adoptCover} disabled={working} size="sm"
                      className="bg-red-600/80 hover:bg-red-600 rounded-sm shrink-0" data-testid="adopt-cover-btn">
                      <UserCheck className="w-3.5 h-3.5 mr-1.5" /> Go Undercover
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SocietyStandingOverlay;
