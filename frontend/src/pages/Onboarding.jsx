import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, Coins, Cpu, Sword, Sparkles, Hammer, Leaf, Eye, Compass, Heart, Globe, Zap, Check } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const Onboarding = () => {
  const navigate = useNavigate();
  const [paths, setPaths] = useState({});
  const [introSteps, setIntroSteps] = useState([]);
  const [virtualVerseInfo, setVirtualVerseInfo] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedPath, setSelectedPath] = useState(null);
  const [userStatus, setUserStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [pathsRes, stepsRes, verseRes, statusRes] = await Promise.all([
        fetch(`${API}/api/player-direction/paths`),
        fetch(`${API}/api/player-direction/intro-steps`),
        fetch(`${API}/api/player-direction/virtual-verse`),
        fetch(`${API}/api/player-direction/user/${userId}/status`)
      ]);
      
      if (pathsRes.ok) setPaths((await pathsRes.json()).paths || {});
      if (stepsRes.ok) setIntroSteps((await stepsRes.json()).steps || []);
      if (verseRes.ok) setVirtualVerseInfo(await verseRes.json());
      if (statusRes.ok) {
        const status = await statusRes.json();
        setUserStatus(status);
        if (status.has_chosen_path && status.intro_completed) {
          navigate('/select-mode');
        } else if (status.has_chosen_path) {
          setSelectedPath(status.path_id);
          setCurrentStep(status.intro_step || 3);
        }
      }
    } catch (err) {
      console.error('Failed to fetch onboarding data:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectPath = async (pathId) => {
    try {
      const res = await fetch(`${API}/api/player-direction/select-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: userId, 
          path_id: pathId,
          skip_intro: false
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setSelectedPath(pathId);
        toast.success(`Welcome, ${data.path_name}! Bonuses applied.`);
        setCurrentStep(3);
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to select path');
      }
    } catch (err) {
      toast.error('Failed to select path');
    }
  };

  const progressIntro = async () => {
    try {
      const res = await fetch(`${API}/api/player-direction/intro/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, step: currentStep })
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.intro_completed) {
          toast.success('Welcome to the Virtual Verse!');
          navigate('/select-mode');
        } else {
          setCurrentStep(data.next_step);
        }
      }
    } catch (err) {
      console.error('Failed to progress intro:', err);
      setCurrentStep(currentStep + 1);
    }
  };

  const skipIntro = async () => {
    try {
      await fetch(`${API}/api/player-direction/intro/skip?user_id=${userId}`, { method: 'POST' });
      toast.info('Introduction skipped. You can review tutorials anytime.');
      navigate('/select-mode');
    } catch (err) {
      navigate('/select-mode');
    }
  };

  const pathIcons = {
    merchant_prince: Coins,
    warrior_champion: Sword,
    arcane_scholar: Sparkles,
    master_artisan: Hammer,
    nature_guardian: Leaf,
    shadow_operative: Eye,
    tech_pioneer: Cpu,
    free_spirit: Compass
  };

  const currentStepData = introSteps[currentStep - 1] || {};

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-pulse text-purple-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-pink-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Progress Bar */}
        <div className="fixed top-0 left-0 right-0 h-1 bg-zinc-800 z-50">
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
            style={{ width: `${(currentStep / introSteps.length) * 100}%` }}
          />
        </div>

        {/* Skip Button */}
        {currentStep > 2 && (
          <button
            onClick={skipIntro}
            className="fixed top-6 right-6 px-4 py-2 bg-zinc-800/80 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors z-50"
            data-testid="skip-intro-btn"
          >
            Skip Introduction
          </button>
        )}

        {/* Main Content */}
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-4xl">
            {/* Step 1: Welcome */}
            {currentStep === 1 && (
              <div className="text-center animate-fade-in">
                <div className="w-24 h-24 mx-auto mb-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center">
                  <Globe className="w-12 h-12" />
                </div>
                <h1 className="text-4xl md:text-5xl font-bold mb-4">
                  Welcome to the <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Virtual Verse</span>
                </h1>
                <p className="text-xl text-zinc-300 max-w-2xl mx-auto mb-8">
                  You've arrived in a world where AI and humans work together. This isn't just a game—it's a glimpse into a future where technology serves humanity.
                </p>
                <button
                  onClick={progressIntro}
                  className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-semibold text-lg hover:opacity-90 transition-opacity flex items-center gap-2 mx-auto"
                  data-testid="continue-btn"
                >
                  Begin Your Journey
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Step 2: Path Selection */}
            {currentStep === 2 && (
              <div className="animate-fade-in">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold mb-2">Choose Your Path</h2>
                  <p className="text-zinc-400">Each path offers unique advantages, but you're never locked in. The Virtual Verse rewards those who adapt.</p>
                </div>
                
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  {Object.entries(paths).map(([key, path]) => {
                    const IconComponent = pathIcons[key] || Compass;
                    const isSelected = selectedPath === key;
                    
                    return (
                      <div
                        key={key}
                        onClick={() => setSelectedPath(key)}
                        className={`bg-zinc-900/50 border rounded-xl p-5 cursor-pointer transition-all ${
                          isSelected 
                            ? 'border-purple-500 bg-purple-500/10 scale-105' 
                            : 'border-zinc-800 hover:border-zinc-700'
                        }`}
                        data-testid={`path-${key}`}
                      >
                        <div 
                          className="w-12 h-12 rounded-lg flex items-center justify-center mb-3"
                          style={{ backgroundColor: `${path.color}20` }}
                        >
                          <IconComponent className="w-6 h-6" style={{ color: path.color }} />
                        </div>
                        <h3 className="font-semibold mb-1">{path.name}</h3>
                        <p className="text-xs text-zinc-400 mb-3 line-clamp-2">{path.description}</p>
                        <div className="text-xs text-zinc-500">{path.recommended_for}</div>
                        
                        {isSelected && (
                          <div className="mt-3 pt-3 border-t border-zinc-800">
                            <div className="text-xs text-zinc-400 mb-2">Starting Bonuses:</div>
                            <div className="flex flex-wrap gap-1">
                              {path.starting_bonuses?.gold && (
                                <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs">
                                  {path.starting_bonuses.gold} Gold
                                </span>
                              )}
                              {path.starting_bonuses?.compute_power && (
                                <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-xs">
                                  {path.starting_bonuses.compute_power} Compute
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                
                <div className="flex justify-center">
                  <button
                    onClick={() => selectedPath && selectPath(selectedPath)}
                    disabled={!selectedPath}
                    className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-semibold text-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    data-testid="confirm-path-btn"
                  >
                    Confirm Path
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}

            {/* Steps 3-7: Information Steps */}
            {currentStep >= 3 && currentStep <= 7 && (
              <div className="max-w-2xl mx-auto animate-fade-in">
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8 mb-8">
                  <div className="text-sm text-purple-400 font-medium mb-2">Step {currentStep} of {introSteps.length}</div>
                  <h2 className="text-2xl font-bold mb-4">{currentStepData.title}</h2>
                  <p className="text-zinc-300 leading-relaxed">{currentStepData.content}</p>
                  
                  {/* Step-specific visuals */}
                  {currentStep === 3 && (
                    <div className="mt-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Heart className="w-8 h-8 text-purple-400" />
                        <div>
                          <div className="font-medium">AI Partnership</div>
                          <div className="text-sm text-zinc-400">Build trust with your AI companion for better earnings</div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {currentStep === 4 && (
                    <div className="mt-6 grid grid-cols-2 gap-4">
                      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                        <Coins className="w-6 h-6 text-amber-400 mb-2" />
                        <div className="font-medium">Gold</div>
                        <div className="text-xs text-zinc-400">In-game currency for purchases</div>
                      </div>
                      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                        <Zap className="w-6 h-6 text-green-400 mb-2" />
                        <div className="font-medium">VE$</div>
                        <div className="text-xs text-zinc-400">Real value, withdrawable</div>
                      </div>
                    </div>
                  )}
                  
                  {currentStep === 5 && (
                    <div className="mt-6 p-4 bg-zinc-800/50 rounded-xl">
                      <div className="text-sm text-zinc-400 mb-2">Building System</div>
                      <div className="grid grid-cols-4 gap-2">
                        {['Residential', 'Commercial', 'Industrial', 'Civic'].map(cat => (
                          <div key={cat} className="p-2 bg-zinc-700/50 rounded text-center text-xs">{cat}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {currentStep === 6 && virtualVerseInfo && (
                    <div className="mt-6">
                      <div className="text-sm text-zinc-400 mb-3">World Scale Progression</div>
                      <div className="space-y-2">
                        {virtualVerseInfo.scale_progression?.slice(0, 3).map((scale, i) => (
                          <div key={i} className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${scale.unlocked ? 'bg-green-500' : 'bg-zinc-700'}`} />
                            <span className={scale.unlocked ? 'text-white' : 'text-zinc-500'}>
                              {scale.name} ({scale.size} Earth)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="flex justify-between">
                  {currentStep > 3 && (
                    <button
                      onClick={() => setCurrentStep(currentStep - 1)}
                      className="px-6 py-3 bg-zinc-800 rounded-xl font-medium hover:bg-zinc-700 flex items-center gap-2"
                    >
                      <ChevronLeft className="w-5 h-5" />
                      Back
                    </button>
                  )}
                  <button
                    onClick={progressIntro}
                    className="px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-medium hover:opacity-90 flex items-center gap-2 ml-auto"
                    data-testid="next-step-btn"
                  >
                    {currentStep === 7 ? 'Enter the Virtual Verse' : 'Continue'}
                    {currentStep === 7 ? <Check className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Step Indicators */}
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex gap-2">
          {introSteps.map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-all ${
                i + 1 === currentStep 
                  ? 'w-6 bg-purple-500' 
                  : i + 1 < currentStep 
                    ? 'bg-purple-500/50' 
                    : 'bg-zinc-700'
              }`}
            />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

export default Onboarding;
