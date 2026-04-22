import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Sparkles, Compass, BookOpen } from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setTimeout(() => setIsLoaded(true), 100);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background Image */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1746472603784-23c90049ca14?crop=entropy&cs=srgb&fm=jpg&q=85')`,
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian/60 via-obsidian/40 to-obsidian" />
        <div className="absolute inset-0 hero-glow" />
      </div>

      {/* Noise Overlay */}
      <div className="absolute inset-0 noise-overlay pointer-events-none" />

      {/* Content */}
      <div className={`relative z-10 min-h-screen flex flex-col items-center justify-center px-6 transition-all duration-1000 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        {/* Logo/Title */}
        <div className="text-center mb-12">
          <h1 className="font-cinzel text-5xl sm:text-6xl lg:text-7xl font-bold tracking-wider mb-4">
            <span className="text-gold-gradient">AI Village</span>
          </h1>
          <p className="font-cinzel text-xl sm:text-2xl text-gold/80 tracking-[0.3em] uppercase">
            The Echoes
          </p>
        </div>

        {/* Tagline */}
        <p className="font-manrope text-lg sm:text-xl text-muted-foreground text-center max-w-2xl mb-16 leading-relaxed">
          Step into a world that learns alongside you. Build relationships, explore mysteries, 
          and shape the destiny of a village that remembers every choice you make.
        </p>

        {/* Main CTA */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <Button
            data-testid="enter-world-btn"
            onClick={() => navigate('/auth')}
            className="group bg-gold text-black font-cinzel font-bold text-lg uppercase tracking-widest px-12 py-6 hover:bg-gold-light transition-all duration-300 shadow-[0_0_30px_rgba(212,175,55,0.3)] hover:shadow-[0_0_50px_rgba(212,175,55,0.5)] rounded-sm"
          >
            <Sparkles className="w-5 h-5 mr-3 group-hover:animate-pulse" />
            Enter The Echoes
          </Button>
        </div>

        {/* Secondary Actions */}
        <div className="flex flex-wrap gap-6 mt-6 justify-center">
          <button 
            data-testid="continue-journey-btn"
            onClick={async () => {
              const userId = localStorage.getItem('userId');
              const charId = localStorage.getItem('currentCharacterId');
              
              // Must have both userId and charId
              if (!userId || !charId) {
                navigate('/auth');
                return;
              }
              
              // Verify character belongs to this user
              try {
                const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/character/${charId}`);
                const char = await res.json();
                
                if (char && char.user_id === userId) {
                  navigate('/select-mode');
                } else {
                  // Character doesn't belong to this user, clear and redirect
                  localStorage.removeItem('currentCharacterId');
                  localStorage.removeItem('characterName');
                  navigate('/auth');
                }
              } catch (error) {
                // Error fetching, redirect to auth
                navigate('/auth');
              }
            }}
            className="flex items-center gap-2 text-muted-foreground hover:text-gold transition-colors duration-300 font-manrope"
          >
            <Compass className="w-4 h-4" />
            Continue Journey
          </button>
          <button 
            data-testid="view-dataspace-btn"
            onClick={() => navigate('/dataspace')}
            className="flex items-center gap-2 text-muted-foreground hover:text-slate-blue transition-colors duration-300 font-manrope"
          >
            <BookOpen className="w-4 h-4" />
            Global Dataspace
          </button>
        </div>

        {/* Features Preview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 max-w-4xl">
          {[
            { 
              title: 'Living Stories', 
              desc: 'AI-driven narratives that adapt to your choices',
              icon: '◈'
            },
            { 
              title: 'Global Memory', 
              desc: 'Every interaction shapes the world for all',
              icon: '◇'
            },
            { 
              title: 'True Companion', 
              desc: 'Not a tool, but a friend who grows with you',
              icon: '◆'
            },
          ].map((feature, i) => (
            <div 
              key={i}
              className="text-center p-6 glass rounded-sm opacity-0 animate-fade-in"
              style={{ animationDelay: `${i * 200 + 500}ms`, animationFillMode: 'forwards' }}
            >
              <div className="text-3xl text-gold mb-4">{feature.icon}</div>
              <h3 className="font-cinzel text-lg text-foreground mb-2">{feature.title}</h3>
              <p className="font-manrope text-sm text-muted-foreground">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Version Tag */}
      <div className="absolute bottom-6 left-6 font-mono text-xs text-muted-foreground/50">
        v0.1.0 // Phase I: The Awakening
      </div>
    </div>
  );
};

export default LandingPage;
