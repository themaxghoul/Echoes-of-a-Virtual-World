import React, { useState, useEffect } from 'react';

const LoadingScreen = ({ 
  message = "Loading...", 
  showProgress = false, 
  progress = 0,
  onComplete = null,
  minDuration = 3500 
}) => {
  const [visible, setVisible] = useState(true);
  const [phase, setPhase] = useState('title'); // title, author, fadeout
  const [titleScale, setTitleScale] = useState(0.5);
  const [titleOpacity, setTitleOpacity] = useState(0);
  const [authorPhase, setAuthorPhase] = useState('hidden'); // hidden, zoomIn, pause, zoomOut

  useEffect(() => {
    // Phase 1: Title grand reveal (0-1.5s)
    const titleReveal = setTimeout(() => {
      setTitleOpacity(1);
      setTitleScale(1);
    }, 100);

    // Phase 2: Author fly-in from right (1.5s)
    const authorIn = setTimeout(() => {
      setPhase('author');
      setAuthorPhase('zoomIn');
    }, 1500);

    // Phase 3: Author pause for reading (1.8s - 3.8s = 2 seconds)
    const authorPause = setTimeout(() => {
      setAuthorPhase('pause');
    }, 1800);

    // Phase 4: Author zoom out left (3.8s)
    const authorOut = setTimeout(() => {
      setAuthorPhase('zoomOut');
    }, 3800);

    // Phase 5: Complete (4.2s)
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
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-amber-600/5 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-600/5 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '0.5s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-orange-500/3 rounded-full blur-[120px]" />
        
        {/* Floating particles */}
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-amber-400/30 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${3 + Math.random() * 4}s`
            }}
          />
        ))}
      </div>

      {/* Main content */}
      <div className="relative z-10 text-center">
        {/* Grand Title */}
        <div 
          className="transition-all duration-1000 ease-out"
          style={{
            transform: `scale(${titleScale})`,
            opacity: titleOpacity
          }}
        >
          {/* Decorative top element */}
          <div className="flex justify-center mb-4">
            <div className="w-32 h-0.5 bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
          </div>
          
          {/* Main Logo */}
          <div className="mb-6">
            <div className="w-24 h-24 mx-auto bg-gradient-to-br from-amber-500 via-orange-500 to-red-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-amber-500/30 border border-amber-400/20">
              <svg viewBox="0 0 24 24" className="w-14 h-14 text-white drop-shadow-lg" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
          </div>

          {/* Title Text - Wide and Proud */}
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-wider mb-2">
            <span className="bg-gradient-to-r from-amber-300 via-orange-400 to-amber-300 bg-clip-text text-transparent drop-shadow-2xl">
              AI VILLAGE
            </span>
          </h1>
          <h2 className="text-2xl md:text-3xl lg:text-4xl font-light tracking-[0.3em] text-amber-200/80 mb-8">
            THE ECHOES
          </h2>

          {/* Decorative bottom element */}
          <div className="flex justify-center">
            <div className="w-48 h-0.5 bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
          </div>
        </div>

        {/* Author credit - Cinematic fly-in */}
        <div 
          className={`absolute left-1/2 -translate-x-1/2 transition-all ${
            authorPhase === 'hidden' ? 'opacity-0 translate-x-[200vw] scale-0' :
            authorPhase === 'zoomIn' ? 'opacity-100 translate-x-0 scale-100' :
            authorPhase === 'pause' ? 'opacity-100 translate-x-0 scale-100' :
            authorPhase === 'zoomOut' ? 'opacity-0 -translate-x-[200vw] scale-0' : ''
          }`}
          style={{
            bottom: '25%',
            transitionDuration: authorPhase === 'zoomIn' || authorPhase === 'zoomOut' ? '400ms' : '0ms',
            transitionTimingFunction: authorPhase === 'zoomIn' ? 'cubic-bezier(0.16, 1, 0.3, 1)' : 'cubic-bezier(0.7, 0, 0.84, 0)'
          }}
        >
          <div className="px-8 py-4 bg-black/40 backdrop-blur-sm rounded-lg border border-amber-500/20">
            <p className="text-lg md:text-xl text-zinc-400 font-medium tracking-wide">
              Created by
            </p>
            <p className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              ApexForge Collective
            </p>
          </div>
        </div>

        {/* Loading indicator at bottom */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2">
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {[0, 1, 2].map(i => (
                <div 
                  key={i}
                  className="w-2 h-2 bg-amber-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            <p className="text-sm text-zinc-500">{message}</p>
          </div>
        </div>

        {/* Version */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
          <p className="text-xs text-zinc-700">v0.1.0</p>
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
      `}</style>
    </div>
  );
};

export default LoadingScreen;
