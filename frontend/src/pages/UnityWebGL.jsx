import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { 
  ArrowLeft, Gamepad2, Download, RefreshCw, Maximize2, Minimize2,
  Settings, Volume2, VolumeX, Loader2, AlertCircle, CheckCircle,
  Monitor, Smartphone, Tablet, Globe, Wifi, WifiOff, Upload,
  ExternalLink, Info, Play, Pause, RotateCcw
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Unity WebGL Loader states
const LOADER_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  DOWNLOADING: 'downloading',
  INITIALIZING: 'initializing',
  RUNNING: 'running',
  ERROR: 'error',
  PAUSED: 'paused'
};

const UnityWebGL = () => {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const unityInstanceRef = useRef(null);
  
  const userId = localStorage.getItem('userId');
  const characterId = localStorage.getItem('characterId');
  
  const [loaderState, setLoaderState] = useState(LOADER_STATES.IDLE);
  const [loadProgress, setLoadProgress] = useState(0);
  const [unityConfig, setUnityConfig] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState(null);
  const [buildUrl, setBuildUrl] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  
  // Performance metrics
  const [metrics, setMetrics] = useState({
    fps: 0,
    memory: 0,
    ping: 0
  });

  // Load Unity config
  useEffect(() => {
    loadUnityConfig();
  }, []);

  const loadUnityConfig = async () => {
    try {
      const [configRes, downloadRes] = await Promise.all([
        axios.get(`${API}/unity/config`),
        axios.get(`${API}/unity/downloads`)
      ]);
      
      setUnityConfig({
        ...configRes.data,
        downloads: downloadRes.data
      });
    } catch (error) {
      console.error('Failed to load Unity config:', error);
    }
  };

  // Create Unity session
  const createSession = async () => {
    if (!userId || !characterId) {
      toast.error('Please select a character first');
      return null;
    }
    
    try {
      const res = await axios.post(`${API}/unity/session?player_id=${userId}&character_id=${characterId}`);
      setSessionInfo(res.data);
      return res.data;
    } catch (error) {
      toast.error('Failed to create Unity session');
      return null;
    }
  };

  // Load Unity WebGL build
  const loadUnityBuild = async (customUrl = null) => {
    const buildPath = customUrl || buildUrl || unityConfig?.downloads?.webgl;
    
    if (!buildPath) {
      toast.error('No WebGL build URL provided');
      return;
    }
    
    setLoaderState(LOADER_STATES.LOADING);
    setError(null);
    setLoadProgress(0);
    
    try {
      // Create session first
      const session = await createSession();
      if (!session) {
        throw new Error('Failed to create session');
      }
      
      // Check if Unity loader script exists
      if (!window.createUnityInstance) {
        setLoaderState(LOADER_STATES.DOWNLOADING);
        await loadUnityLoader(buildPath);
      }
      
      setLoaderState(LOADER_STATES.INITIALIZING);
      
      // Unity build configuration
      const config = {
        dataUrl: `${buildPath}/Build/Build.data`,
        frameworkUrl: `${buildPath}/Build/Build.framework.js`,
        codeUrl: `${buildPath}/Build/Build.wasm`,
        streamingAssetsUrl: `${buildPath}/StreamingAssets`,
        companyName: "AI Village",
        productName: "The Echoes",
        productVersion: unityConfig?.downloads?.version || "1.0.0",
      };
      
      // Create Unity instance
      if (window.createUnityInstance && canvasRef.current) {
        const instance = await window.createUnityInstance(canvasRef.current, config, (progress) => {
          setLoadProgress(Math.round(progress * 100));
        });
        
        unityInstanceRef.current = instance;
        setLoaderState(LOADER_STATES.RUNNING);
        
        // Send session token to Unity
        instance.SendMessage('GameManager', 'SetSessionToken', session.token);
        instance.SendMessage('GameManager', 'SetCharacterId', characterId);
        
        // Connect session
        await axios.post(`${API}/unity/session/${session.session_id}/connect?platform=webgl&unity_version=WebGL`);
        
        toast.success('Unity WebGL loaded successfully!');
        
        // Start performance monitoring
        startPerformanceMonitoring();
      } else {
        throw new Error('Unity loader not available');
      }
    } catch (error) {
      console.error('Failed to load Unity build:', error);
      setError(error.message || 'Failed to load Unity WebGL build');
      setLoaderState(LOADER_STATES.ERROR);
    }
  };

  // Load Unity loader script
  const loadUnityLoader = (buildPath) => {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `${buildPath}/Build/Build.loader.js`;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Failed to load Unity loader'));
      document.head.appendChild(script);
    });
  };

  // Performance monitoring
  const startPerformanceMonitoring = () => {
    const interval = setInterval(() => {
      if (unityInstanceRef.current && loaderState === LOADER_STATES.RUNNING) {
        // These would normally come from Unity via SendMessage callbacks
        setMetrics(prev => ({
          fps: 60 + Math.floor(Math.random() * 10) - 5, // Simulated
          memory: Math.floor(performance?.memory?.usedJSHeapSize / 1024 / 1024) || 0,
          ping: 20 + Math.floor(Math.random() * 30) // Simulated
        }));
      } else {
        clearInterval(interval);
      }
    }, 1000);
    
    return () => clearInterval(interval);
  };

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // Mute toggle
  const toggleMute = () => {
    if (unityInstanceRef.current) {
      unityInstanceRef.current.SendMessage('AudioManager', 'SetMute', isMuted ? 0 : 1);
    }
    setIsMuted(!isMuted);
  };

  // Pause/Resume
  const togglePause = () => {
    if (unityInstanceRef.current) {
      if (loaderState === LOADER_STATES.RUNNING) {
        unityInstanceRef.current.SendMessage('GameManager', 'Pause');
        setLoaderState(LOADER_STATES.PAUSED);
      } else if (loaderState === LOADER_STATES.PAUSED) {
        unityInstanceRef.current.SendMessage('GameManager', 'Resume');
        setLoaderState(LOADER_STATES.RUNNING);
      }
    }
  };

  // Cleanup
  useEffect(() => {
    return () => {
      if (unityInstanceRef.current) {
        unityInstanceRef.current.Quit();
      }
      if (sessionInfo?.session_id) {
        axios.post(`${API}/unity/session/${sessionInfo.session_id}/disconnect`).catch(() => {});
      }
    };
  }, [sessionInfo]);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header - hidden in fullscreen */}
      {!isFullscreen && (
        <div className="bg-surface/50 border-b border-border/30 p-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={() => navigate('/select-mode')}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                  <Globe className="w-6 h-6" />
                  Unity WebGL
                </h1>
                <p className="text-sm text-muted-foreground">Play in browser • No download required</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {loaderState === LOADER_STATES.RUNNING && (
                <>
                  <Badge className="bg-green-500/20 text-green-400">
                    <Wifi className="w-3 h-3 mr-1" />
                    {metrics.ping}ms
                  </Badge>
                  <Badge className="bg-blue-500/20 text-blue-400">
                    {metrics.fps} FPS
                  </Badge>
                </>
              )}
              
              {sessionInfo && (
                <Badge className="bg-purple-500/20 text-purple-400">
                  Session: {sessionInfo.session_id.slice(0, 8)}...
                </Badge>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-4">
        {/* Build URL Input (when no webgl build configured) */}
        {!unityConfig?.downloads?.webgl && loaderState === LOADER_STATES.IDLE && (
          <Card className="p-6 bg-surface/50 border-border/30 mb-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Upload className="w-6 h-6 text-amber-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-cinzel text-lg mb-2">Load Custom WebGL Build</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Enter the URL to your Unity WebGL build folder (containing the Build/ directory)
                </p>
                <div className="flex gap-2">
                  <Input
                    placeholder="https://your-server.com/unity-build"
                    value={buildUrl}
                    onChange={(e) => setBuildUrl(e.target.value)}
                    className="flex-1"
                    data-testid="webgl-url-input"
                  />
                  <Button 
                    onClick={() => loadUnityBuild()}
                    disabled={!buildUrl}
                    className="bg-gold text-black hover:bg-gold-light"
                    data-testid="load-webgl-btn"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Load
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Unity Container */}
        <div 
          ref={containerRef}
          className="relative bg-black rounded-lg overflow-hidden"
          style={{ aspectRatio: '16/9', maxHeight: 'calc(100vh - 200px)' }}
        >
          {/* Loading States */}
          {loaderState !== LOADER_STATES.RUNNING && loaderState !== LOADER_STATES.PAUSED && (
            <div className="absolute inset-0 flex items-center justify-center bg-obsidian z-10">
              {loaderState === LOADER_STATES.IDLE && (
                <div className="text-center">
                  <Gamepad2 className="w-16 h-16 text-gold mx-auto mb-4" />
                  <h2 className="font-cinzel text-2xl text-gold mb-2">Unity WebGL</h2>
                  <p className="text-muted-foreground mb-6">Experience The Echoes in full 3D</p>
                  
                  {unityConfig?.downloads?.webgl ? (
                    <Button 
                      onClick={() => loadUnityBuild(unityConfig.downloads.webgl)}
                      className="bg-gold text-black hover:bg-gold-light px-8 py-3"
                      data-testid="start-webgl-btn"
                    >
                      <Play className="w-5 h-5 mr-2" />
                      Launch Game
                    </Button>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Enter a WebGL build URL above to start
                    </p>
                  )}
                  
                  <div className="mt-8 flex justify-center gap-8 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Monitor className="w-4 h-4" />
                      Desktop
                    </div>
                    <div className="flex items-center gap-2">
                      <Tablet className="w-4 h-4" />
                      Tablet
                    </div>
                    <div className="flex items-center gap-2 opacity-50">
                      <Smartphone className="w-4 h-4" />
                      Mobile (Limited)
                    </div>
                  </div>
                </div>
              )}
              
              {(loaderState === LOADER_STATES.LOADING || 
                loaderState === LOADER_STATES.DOWNLOADING || 
                loaderState === LOADER_STATES.INITIALIZING) && (
                <div className="text-center w-64">
                  <Loader2 className="w-12 h-12 text-gold animate-spin mx-auto mb-4" />
                  <h3 className="font-cinzel text-lg text-gold mb-2">
                    {loaderState === LOADER_STATES.DOWNLOADING && 'Downloading Assets...'}
                    {loaderState === LOADER_STATES.LOADING && 'Loading Engine...'}
                    {loaderState === LOADER_STATES.INITIALIZING && 'Initializing World...'}
                  </h3>
                  <Progress value={loadProgress} className="h-2 mb-2" />
                  <p className="text-sm text-muted-foreground">{loadProgress}%</p>
                </div>
              )}
              
              {loaderState === LOADER_STATES.ERROR && (
                <div className="text-center">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <h3 className="font-cinzel text-lg text-red-400 mb-2">Failed to Load</h3>
                  <p className="text-sm text-muted-foreground mb-4 max-w-md">{error}</p>
                  <Button 
                    onClick={() => setLoaderState(LOADER_STATES.IDLE)}
                    variant="outline"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Try Again
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Unity Canvas */}
          <canvas 
            ref={canvasRef}
            id="unity-canvas"
            className="w-full h-full"
            style={{ display: loaderState === LOADER_STATES.RUNNING || loaderState === LOADER_STATES.PAUSED ? 'block' : 'none' }}
            data-testid="unity-canvas"
          />

          {/* Paused Overlay */}
          {loaderState === LOADER_STATES.PAUSED && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
              <div className="text-center">
                <Pause className="w-16 h-16 text-gold mx-auto mb-4" />
                <h3 className="font-cinzel text-2xl text-gold">Paused</h3>
              </div>
            </div>
          )}

          {/* Controls Overlay */}
          {(loaderState === LOADER_STATES.RUNNING || loaderState === LOADER_STATES.PAUSED) && (
            <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between z-20">
              <div className="flex items-center gap-2">
                <Button 
                  variant="secondary" 
                  size="icon"
                  onClick={togglePause}
                  className="bg-black/50 hover:bg-black/70"
                >
                  {loaderState === LOADER_STATES.PAUSED ? (
                    <Play className="w-4 h-4" />
                  ) : (
                    <Pause className="w-4 h-4" />
                  )}
                </Button>
                <Button 
                  variant="secondary" 
                  size="icon"
                  onClick={toggleMute}
                  className="bg-black/50 hover:bg-black/70"
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </Button>
              </div>
              
              <div className="flex items-center gap-2">
                <Button 
                  variant="secondary" 
                  size="icon"
                  onClick={() => setShowSettings(!showSettings)}
                  className="bg-black/50 hover:bg-black/70"
                >
                  <Settings className="w-4 h-4" />
                </Button>
                <Button 
                  variant="secondary" 
                  size="icon"
                  onClick={toggleFullscreen}
                  className="bg-black/50 hover:bg-black/70"
                >
                  {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Info Cards - hidden when running */}
        {loaderState === LOADER_STATES.IDLE && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <Card className="p-4 bg-surface/50 border-border/30">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h4 className="font-medium">No Download</h4>
                  <p className="text-sm text-muted-foreground">Play directly in your browser</p>
                </div>
              </div>
            </Card>
            
            <Card className="p-4 bg-surface/50 border-border/30">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <Wifi className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h4 className="font-medium">Cross-Platform Sync</h4>
                  <p className="text-sm text-muted-foreground">Progress syncs with other clients</p>
                </div>
              </div>
            </Card>
            
            <Card className="p-4 bg-surface/50 border-border/30">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <Gamepad2 className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h4 className="font-medium">Full 3D Experience</h4>
                  <p className="text-sm text-muted-foreground">Complete game features</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Native Downloads */}
        {loaderState === LOADER_STATES.IDLE && unityConfig?.downloads && (
          <Card className="p-6 bg-surface/50 border-border/30 mt-6">
            <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
              <Download className="w-5 h-5" />
              Native Downloads
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              For the best experience, download the native client for your platform.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['windows', 'mac', 'linux'].map(platform => (
                <Button
                  key={platform}
                  variant="outline"
                  className="justify-start h-auto py-3"
                  onClick={() => window.open(unityConfig.downloads[platform], '_blank')}
                  disabled={!unityConfig.downloads[platform]}
                >
                  <Monitor className="w-5 h-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium capitalize">{platform}</div>
                    <div className="text-xs text-muted-foreground">
                      {unityConfig.downloads.requirements?.[platform]?.os || 'Available'}
                    </div>
                  </div>
                  <ExternalLink className="w-4 h-4 ml-auto" />
                </Button>
              ))}
            </div>
            
            <div className="mt-4 p-3 bg-black/20 rounded-lg flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-muted-foreground">
                <strong className="text-foreground">Version {unityConfig.downloads.version}</strong> • 
                Released {unityConfig.downloads.release_date}
                <ul className="mt-2 space-y-1 list-disc list-inside">
                  {unityConfig.downloads.changelog?.slice(0, 3).map((change, idx) => (
                    <li key={idx}>{change}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default UnityWebGL;
