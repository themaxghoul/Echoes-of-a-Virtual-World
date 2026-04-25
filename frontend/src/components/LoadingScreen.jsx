import React, { useState, useEffect } from 'react';

const LoadingScreen = ({ 
  message = "Loading...", 
  onComplete = null,
  minDuration = 3500 
}) => {
  const [visible, setVisible] = useState(true);
  const [phase, setPhase] = useState('title');
  const [titleScale, setTitleScale] = useState(0.5);
  const [titleOpacity, setTitleOpacity] = useState(0);
  const [authorPhase, setAuthorPhase] = useState('hidden');
  const [loadProgress, setLoadProgress] = useState(0);

  useEffect(() => {
    // Animate loading bar
    const progressInterval = setInterval(() => {
      setLoadProgress(prev => {
        if (prev >= 100) return 100;
        return prev + Math.random() * 15 + 5;
      });
    }, 200);

    // Phase 1: Title grand reveal
    const titleReveal = setTimeout(() => {
      setTitleOpacity(1);
      setTitleScale(1);
    }, 100);

    // Phase 2: Author fly-in from right
    const authorIn = setTimeout(() => {
      setPhase('author');
      setAuthorPhase('zoomIn');
    }, 1500);

    // Phase 3: Author pause for reading
    const authorPause = setTimeout(() => {
      setAuthorPhase('pause');
    }, 1800);

    // Phase 4: Author zoom out left
    const authorOut = setTimeout(() => {
      setAuthorPhase('zoomOut');
    }, 3800);

    // Phase 5: Complete
    const complete = setTimeout(() => {
      if (onComplete) {
        setPhase('fadeout');
        setTimeout(() => {
          setVisible(false);
          onComplete();
        }, 500);
      }
    }, minDuration);

    return () => {
      clearInterval(progressInterval);
      clearTimeout(titleReveal);
      clearTimeout(authorIn);
      clearTimeout(authorPause);
      clearTimeout(authorOut);
      clearTimeout(complete);
    };
  }, [minDuration, onComplete]);

  if (!visible) return null;

  return (
    <div 
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0a0a0f] overflow-hidden transition-opacity duration-500 ${
        phase === 'fadeout' ? 'opacity-0' : 'opacity-100'
      }`}
    >
      {/* Dark fantasy background texture */}
      <div 
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage: `
            radial-gradient(ellipse at 50% 0%, rgba(139, 69, 19, 0.2) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, rgba(75, 0, 130, 0.15) 0%, transparent 40%),
            radial-gradient(ellipse at 20% 80%, rgba(139, 0, 0, 0.15) 0%, transparent 40%)
          `
        }}
      />
      
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(25)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              backgroundColor: i % 3 === 0 ? 'rgba(255, 170, 0, 0.4)' : i % 3 === 1 ? 'rgba(200, 100, 50, 0.3)' : 'rgba(150, 100, 200, 0.3)',
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${3 + Math.random() * 4}s`
            }}
          />
        ))}
      </div>

      {/* Main content - Upper section */}
      <div className="relative z-10 text-center flex-1 flex flex-col justify-center">
        {/* Grand Title */}
        <div 
          className="transition-all duration-1000 ease-out"
          style={{
            transform: `scale(${titleScale})`,
            opacity: titleOpacity
          }}
        >
          {/* Decorative top flourish */}
          <div className="flex justify-center mb-6">
            <svg width="200" height="20" viewBox="0 0 200 20" className="text-amber-500/50">
              <path d="M0 10 Q50 0 100 10 Q150 20 200 10" stroke="currentColor" strokeWidth="1" fill="none"/>
              <circle cx="100" cy="10" r="3" fill="currentColor"/>
              <circle cx="70" cy="8" r="2" fill="currentColor"/>
              <circle cx="130" cy="8" r="2" fill="currentColor"/>
            </svg>
          </div>
          
          {/* Main Logo */}
          <div className="mb-6">
            <div className="w-28 h-28 mx-auto bg-gradient-to-br from-amber-500 via-orange-600 to-red-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-amber-500/40 border-2 border-amber-400/30 relative">
              <div className="absolute inset-1 rounded-xl bg-gradient-to-br from-amber-400/20 to-transparent" />
              <svg viewBox="0 0 24 24" className="w-16 h-16 text-white drop-shadow-lg relative z-10" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
          </div>

          {/* Title Text - Wide and Proud */}
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-[0.15em] mb-3">
            <span 
              className="bg-gradient-to-b from-amber-200 via-amber-400 to-amber-600 bg-clip-text text-transparent drop-shadow-2xl"
              style={{ 
                textShadow: '0 0 40px rgba(255, 170, 0, 0.3)',
                fontFamily: 'Cinzel, serif'
              }}
            >
              AI VILLAGE
            </span>
          </h1>
          <h2 
            className="text-2xl md:text-3xl lg:text-4xl font-light tracking-[0.4em] text-amber-300/70 mb-6"
            style={{ fontFamily: 'Cinzel, serif' }}
          >
            THE ECHOES
          </h2>

          {/* Decorative bottom flourish */}
          <div className="flex justify-center">
            <svg width="250" height="20" viewBox="0 0 250 20" className="text-amber-500/40">
              <path d="M0 10 L80 10 M170 10 L250 10" stroke="currentColor" strokeWidth="1"/>
              <path d="M90 5 L125 15 L160 5" stroke="currentColor" strokeWidth="1" fill="none"/>
              <circle cx="125" cy="10" r="2" fill="currentColor"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Author credit - Lower middle section with action font */}
      <div 
        className={`absolute transition-all ${
          authorPhase === 'hidden' ? 'opacity-0 translate-x-[150vw] scale-75' :
          authorPhase === 'zoomIn' ? 'opacity-100 translate-x-0 scale-100' :
          authorPhase === 'pause' ? 'opacity-100 translate-x-0 scale-100' :
          authorPhase === 'zoomOut' ? 'opacity-0 -translate-x-[150vw] scale-75' : ''
        }`}
        style={{
          top: 'calc(58% + 20px)',
          left: '50%',
          transform: `translateX(-50%) ${
            authorPhase === 'hidden' ? 'translateX(150vw) scale(0.75)' :
            authorPhase === 'zoomOut' ? 'translateX(-150vw) scale(0.75)' : ''
          }`,
          transitionDuration: authorPhase === 'zoomIn' || authorPhase === 'zoomOut' ? '400ms' : '0ms',
          transitionTimingFunction: authorPhase === 'zoomIn' ? 'cubic-bezier(0.16, 1, 0.3, 1)' : 'cubic-bezier(0.7, 0, 0.84, 0)'
        }}
      >
        <div className="relative">
          {/* Slashed background effect */}
          <div 
            className="absolute inset-0 -skew-x-6 bg-gradient-to-r from-transparent via-red-900/40 to-transparent"
            style={{ transform: 'skewX(-6deg) scaleX(1.3)' }}
          />
          <div className="relative px-10 py-4">
            <p 
              className="text-lg text-zinc-400 tracking-widest uppercase mb-1"
              style={{ fontFamily: 'Cinzel, serif' }}
            >
              Created by
            </p>
            <p 
              className="text-3xl md:text-4xl font-black tracking-wider uppercase"
              style={{ 
                fontFamily: 'Impact, Haettenschweiler, Arial Narrow Bold, sans-serif',
                background: 'linear-gradient(180deg, #ffd700 0%, #ff8c00 50%, #ff4500 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
                letterSpacing: '0.1em'
              }}
            >
              APEXFORGE COLLECTIVE
            </p>
          </div>
        </div>
      </div>

      {/* RPG Loading Bar - Bottom section */}
      <div className="absolute bottom-0 left-0 right-0 pb-8 px-8">
        {/* Loading bar container with RPG frame */}
        <div className="max-w-xl mx-auto">
          {/* Ornate frame */}
          <div className="relative">
            {/* Corner decorations */}
            <div className="absolute -top-2 -left-2 w-4 h-4 border-l-2 border-t-2 border-amber-600/60" />
            <div className="absolute -top-2 -right-2 w-4 h-4 border-r-2 border-t-2 border-amber-600/60" />
            <div className="absolute -bottom-2 -left-2 w-4 h-4 border-l-2 border-b-2 border-amber-600/60" />
            <div className="absolute -bottom-2 -right-2 w-4 h-4 border-r-2 border-b-2 border-amber-600/60" />
            
            {/* Main bar background with texture */}
            <div 
              className="h-6 rounded-sm border-2 border-amber-800/60 relative overflow-hidden"
              style={{
                background: 'linear-gradient(180deg, #1a0f0a 0%, #2d1f15 50%, #1a0f0a 100%)',
                boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5), inset 0 -1px 2px rgba(255,200,100,0.1)'
              }}
            >
              {/* Inner texture pattern */}
              <div 
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: `repeating-linear-gradient(
                    90deg,
                    transparent 0px,
                    transparent 4px,
                    rgba(139, 90, 43, 0.3) 4px,
                    rgba(139, 90, 43, 0.3) 5px
                  )`
                }}
              />
              
              {/* Progress fill with glowing effect */}
              <div 
                className="h-full relative transition-all duration-200 ease-out"
                style={{ 
                  width: `${Math.min(loadProgress, 100)}%`,
                  background: 'linear-gradient(180deg, #ffd700 0%, #ff8c00 30%, #ff6600 60%, #cc4400 100%)',
                  boxShadow: '0 0 10px rgba(255, 140, 0, 0.5), inset 0 1px 2px rgba(255, 255, 200, 0.4)'
                }}
              >
                {/* Animated shine effect */}
                <div 
                  className="absolute inset-0 animate-shimmer"
                  style={{
                    background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
                    backgroundSize: '200% 100%'
                  }}
                />
                {/* Top highlight */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-b from-white/30 to-transparent" />
              </div>
              
              {/* Notch marks */}
              {[25, 50, 75].map(pos => (
                <div 
                  key={pos}
                  className="absolute top-0 bottom-0 w-px bg-amber-900/50"
                  style={{ left: `${pos}%` }}
                />
              ))}
            </div>
          </div>
          
          {/* Status text */}
          <div className="flex justify-between items-center mt-3">
            <p 
              className="text-sm text-amber-600/80 tracking-wider"
              style={{ fontFamily: 'Cinzel, serif' }}
            >
              {message}
            </p>
            <p 
              className="text-sm text-amber-500/60 font-mono"
            >
              {Math.min(Math.round(loadProgress), 100)}%
            </p>
          </div>
        </div>
        
        {/* Version at very bottom */}
        <div className="text-center mt-4">
          <p className="text-xs text-zinc-700 tracking-widest">v0.1.0</p>
        </div>
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
          50% { transform: translateY(-20px) translateX(10px); opacity: 0.6; }
        }
        .animate-float {
          animation: float 4s ease-in-out infinite;
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .animate-shimmer {
          animation: shimmer 2s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default LoadingScreen;
