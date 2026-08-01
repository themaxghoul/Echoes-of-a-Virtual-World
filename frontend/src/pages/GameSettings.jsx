import { useState } from 'react';
import { Accessibility, ArrowLeft, Gamepad2, Monitor, Settings2, Volume2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

const KEY = 'eov-game-settings';
const defaults = { textSpeed: 'normal', autosave: true, reduceMotion: false, highContrast: false, textScale: 100, masterVolume: 80, movement: 'WASD / Arrow keys', interaction: 'E' };

const load = () => {
  try { return { ...defaults, ...JSON.parse(localStorage.getItem(KEY)) }; } catch { return defaults; }
};

export default function GameSettings() {
  const navigate = useNavigate();
  const [value, setValue] = useState(load);
  const update = (key, next) => {
    const settings = { ...value, [key]: next };
    setValue(settings);
    localStorage.setItem(KEY, JSON.stringify(settings));
    document.documentElement.style.fontSize = `${settings.textScale}%`;
    document.documentElement.classList.toggle('eov-reduce-motion', settings.reduceMotion);
    document.documentElement.classList.toggle('eov-high-contrast', settings.highContrast);
  };

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      <header className="flex items-center gap-3 border-b border-border/40 p-5">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Back"><ArrowLeft /></Button>
        <Settings2 className="text-gold" /><div><h1 className="font-cinzel text-xl">Game Settings</h1><p className="text-xs text-muted-foreground">Local device preferences</p></div>
      </header>
      <main className="mx-auto grid max-w-5xl gap-5 p-5 md:grid-cols-2">
        <section className="rounded-sm border border-border/40 bg-surface/70 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-cinzel text-gold"><Settings2 size={18} /> Game</h2>
          <Label htmlFor="text-speed">Story text speed</Label>
          <select id="text-speed" value={value.textSpeed} onChange={(e) => update('textSpeed', e.target.value)} className="mt-2 w-full border border-border bg-obsidian p-3">
            <option value="instant">Instant</option><option value="fast">Fast</option><option value="normal">Normal</option><option value="slow">Slow</option>
          </select>
          <label className="mt-5 flex items-center justify-between"><span>Automatic save revisions</span><input type="checkbox" checked={value.autosave} onChange={(e) => update('autosave', e.target.checked)} /></label>
        </section>
        <section className="rounded-sm border border-border/40 bg-surface/70 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-cinzel text-gold"><Monitor size={18} /> Display</h2>
          <Label htmlFor="volume"><Volume2 className="mr-2 inline" size={15} />Master volume: {value.masterVolume}%</Label>
          <input id="volume" className="mt-3 w-full" type="range" min="0" max="100" value={value.masterVolume} onChange={(e) => update('masterVolume', Number(e.target.value))} />
        </section>
        <section className="rounded-sm border border-border/40 bg-surface/70 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-cinzel text-gold"><Accessibility size={18} /> Accessibility</h2>
          <Label htmlFor="text-scale">Text scale: {value.textScale}%</Label>
          <input id="text-scale" className="my-3 w-full" type="range" min="85" max="150" step="5" value={value.textScale} onChange={(e) => update('textScale', Number(e.target.value))} />
          <label className="flex items-center justify-between py-2"><span>Reduce motion</span><input type="checkbox" checked={value.reduceMotion} onChange={(e) => update('reduceMotion', e.target.checked)} /></label>
          <label className="flex items-center justify-between py-2"><span>High contrast interface</span><input type="checkbox" checked={value.highContrast} onChange={(e) => update('highContrast', e.target.checked)} /></label>
        </section>
        <section className="rounded-sm border border-border/40 bg-surface/70 p-5">
          <h2 className="mb-4 flex items-center gap-2 font-cinzel text-gold"><Gamepad2 size={18} /> Controls</h2>
          <dl className="space-y-3"><div className="flex justify-between"><dt>Movement</dt><dd className="font-mono text-gold">{value.movement}</dd></div><div className="flex justify-between"><dt>Interact</dt><dd className="font-mono text-gold">{value.interaction}</dd></div><div className="flex justify-between"><dt>Build mode</dt><dd className="font-mono text-gold">Mouse / pointer</dd></div></dl>
          <p className="mt-5 text-xs text-muted-foreground">Remapping and controller profiles follow after input actions are unified across clients.</p>
        </section>
      </main>
    </div>
  );
}
