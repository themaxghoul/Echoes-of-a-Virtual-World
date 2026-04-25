import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

const LoadingScreen = ({ 
  message = "Loading...", 
  showProgress = false, 
  progress = 0,
  onComplete = null,
  minDuration = 2000 
}) => {
  const [visible, setVisible] = useState(true);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (onComplete) {
        setFadeOut(true);
        setTimeout(() => {
          setVisible(false);
          onComplete();
        }, 500);
      }
    }, minDuration);

    return () => clearTimeout(timer);
  }, [minDuration, onComplete]);

  if (!visible) return null;

  return (
    <div 
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0a0a0f] transition-opacity duration-500 ${
        fadeOut ? 'opacity-0' : 'opacity-100'
      }`}
    >
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-amber-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      <div className="relative z-10 text-center">
        {/* Logo/Brand */}
        <div className="mb-8">
          <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-amber-500 via-orange-500 to-red-500 rounded-2xl flex items-center justify-center shadow-lg shadow-amber-500/20">
            <svg viewBox="0 0 24 24" className="w-12 h-12 text-white" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
            AI Village: The Echoes
          </h1>
        </div>

        {/* Loading indicator */}
        <div className="mb-6">
          <Loader2 className="w-8 h-8 mx-auto text-amber-400 animate-spin mb-3" />
          <p className="text-zinc-400 text-sm">{message}</p>
        </div>

        {/* Progress bar (optional) */}
        {showProgress && (
          <div className="w-64 mx-auto mb-8">
            <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-zinc-500 mt-2">{progress}%</p>
          </div>
        )}

        {/* Branding */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <p className="text-sm text-zinc-500 font-medium tracking-wider">
            Created by <span className="text-amber-400">ApexForge Collective</span>
          </p>
          <p className="text-xs text-zinc-600 mt-1">v0.1.0</p>
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;
