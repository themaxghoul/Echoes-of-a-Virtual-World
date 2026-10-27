import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { GameNavigation, pushNavHistory } from '@/components/GameNavigation';

export default function ModeSelection() {
  const navigate = useNavigate();
  useEffect(() => {
    if (!localStorage.getItem('userId')) navigate('/auth', { replace: true });
    else pushNavHistory('/select-mode');
  }, [navigate]);
  const enter = (path) => {
    const userId = localStorage.getItem('userId');
    if (userId) localStorage.setItem(`eovLastRoute:${userId}`, path);
    navigate(path);
  };
  return <div className="min-h-screen bg-obsidian text-foreground">
    <GameNavigation title="Echoes of a Virtual World" showBack={false} showHome={false} showLogout />
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="font-mono text-sm text-gold">Welcome, {localStorage.getItem('characterName') || localStorage.getItem('displayName') || 'Traveler'}</p>
      <h1 className="font-cinzel text-3xl mt-3 mb-4">Return to the settlement</h1>
      <p className="text-muted-foreground mb-10">Two perspectives on the same persistent world. Your location, work and conversations stay with your server account.</p>
      <div className="grid gap-6 sm:grid-cols-2">
        <section className="border border-gold/30 bg-surface p-6 rounded-sm">
          <h2 className="font-cinzel text-xl mb-3">Explore</h2>
          <p className="text-muted-foreground mb-6">Walk the isometric landscape, discover resources, collect supplies and meet nearby Samaritans.</p>
          <Button onClick={() => enter('/play')}>Enter settlement</Button>
        </section>
        <section className="border border-slate-blue/40 bg-surface p-6 rounded-sm">
          <h2 className="font-cinzel text-xl mb-3">Converse</h2>
          <p className="text-muted-foreground mb-6">A focused text view of the people and conversations within hearing of your character.</p>
          <Button variant="outline" onClick={() => enter('/village')}>Story chat</Button>
        </section>
      </div>
      <p className="text-sm text-muted-foreground mt-8">Joining a hosted world? Set its world and authentication addresses in <button className="text-gold underline" onClick={() => navigate('/settings')}>Settings</button>, then sign in.</p>
    </main>
  </div>;
}
