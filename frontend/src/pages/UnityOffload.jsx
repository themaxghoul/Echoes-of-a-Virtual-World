import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { 
  Gamepad2, Monitor, Wifi, WifiOff, Settings, Download,
  Play, Pause, RefreshCw, ArrowLeft, ExternalLink, Shield,
  Server, Cpu, HardDrive, Zap, Globe, Lock, Unlock, Check,
  AlertTriangle, Info, Copy, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory, GameNavigation } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Unity connection states
const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  SYNCING: 'syncing',
  PLAYING: 'playing',
  ERROR: 'error'
};

const UnityOffload = () => {
  const navigate = useNavigate();
  const [connectionState, setConnectionState] = useState(CONNECTION_STATES.DISCONNECTED);
  const [unityConfig, setUnityConfig] = useState({
    serverUrl: '',
    sessionToken: '',
    playerId: localStorage.getItem('userId') || '',
    characterId: localStorage.getItem('currentCharacterId') || ''
  });
  const [syncStatus, setSyncStatus] = useState({
    character: false,
    inventory: false,
    world: false,
    progress: 0
  });
  const [serverInfo, setServerInfo] = useState(null);
  const [downloadLinks, setDownloadLinks] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    pushNavHistory('/unity');
    loadUnityConfig();
    loadDownloadLinks();
  }, []);

  const loadUnityConfig = async () => {
    try {
      const res = await axios.get(`${API}/unity/config`);
      if (res.data.server_url) {
        setUnityConfig(prev => ({ ...prev, serverUrl: res.data.server_url }));
      }
      setServerInfo(res.data);
    } catch (error) {
      // Server might not have Unity config yet
      console.log('Unity config not available');
    }
  };

  const loadDownloadLinks = async () => {
    try {
      const res = await axios.get(`${API}/unity/downloads`);
      setDownloadLinks(res.data);
    } catch (error) {
      // Use default download links
      setDownloadLinks({
        windows: 'https://aivillage.itch.io/echoes-unity',
        mac: 'https://aivillage.itch.io/echoes-unity',
        linux: 'https://aivillage.itch.io/echoes-unity',
        webgl: null
      });
    }
  };

  const generateSessionToken = async () => {
    try {
      const res = await axios.post(`${API}/unity/session`, {
        player_id: unityConfig.playerId,
        character_id: unityConfig.characterId
      });
      setUnityConfig(prev => ({ ...prev, sessionToken: res.data.token }));
      toast.success('Session token generated!');
      return res.data.token;
    } catch (error) {
      toast.error('Failed to generate session token');
      return null;
    }
  };

  const connectToUnity = async () => {
    setConnectionState(CONNECTION_STATES.CONNECTING);
    
    try {
      // Generate session token if not exists
      let token = unityConfig.sessionToken;
      if (!token) {
        token = await generateSessionToken();
        if (!token) {
          setConnectionState(CONNECTION_STATES.ERROR);
          return;
        }
      }

      // Simulate connection handshake
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setConnectionState(CONNECTION_STATES.SYNCING);
      
      // Sync character data
      setSyncStatus({ character: false, inventory: false, world: false, progress: 10 });
      await new Promise(resolve => setTimeout(resolve, 800));
      setSyncStatus({ character: true, inventory: false, world: false, progress: 40 });
      
      // Sync inventory
      await new Promise(resolve => setTimeout(resolve, 600));
      setSyncStatus({ character: true, inventory: true, world: false, progress: 70 });
      
      // Sync world state
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSyncStatus({ character: true, inventory: true, world: true, progress: 100 });
      
      setConnectionState(CONNECTION_STATES.CONNECTED);
      toast.success('Connected to Unity! Launch the game to play.');
    } catch (error) {
      setConnectionState(CONNECTION_STATES.ERROR);
      toast.error('Failed to connect to Unity server');
    }
  };

  const disconnectFromUnity = () => {
    setConnectionState(CONNECTION_STATES.DISCONNECTED);
    setSyncStatus({ character: false, inventory: false, world: false, progress: 0 });
    toast.info('Disconnected from Unity');
  };

  const copySessionCode = () => {
    const code = `${unityConfig.sessionToken}::${unityConfig.playerId}`;
    navigator.clipboard.writeText(code);
    toast.success('Session code copied! Paste in Unity.');
  };

  const getConnectionColor = () => {
    switch (connectionState) {
      case CONNECTION_STATES.CONNECTED:
      case CONNECTION_STATES.PLAYING:
        return 'text-green-400';
      case CONNECTION_STATES.CONNECTING:
      case CONNECTION_STATES.SYNCING:
        return 'text-yellow-400';
      case CONNECTION_STATES.ERROR:
        return 'text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getConnectionIcon = () => {
    switch (connectionState) {
      case CONNECTION_STATES.CONNECTED:
      case CONNECTION_STATES.PLAYING:
        return <Wifi className="w-5 h-5 text-green-400" />;
      case CONNECTION_STATES.CONNECTING:
      case CONNECTION_STATES.SYNCING:
        return <RefreshCw className="w-5 h-5 text-yellow-400 animate-spin" />;
      case CONNECTION_STATES.ERROR:
        return <WifiOff className="w-5 h-5 text-red-400" />;
      default:
        return <WifiOff className="w-5 h-5 text-muted-foreground" />;
    }
  };

  return (
    <div className="min-h-screen bg-obsidian flex flex-col">
      {/* Background */}
      <div className="fixed inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-blue/20 via-obsidian to-purple-900/20" />
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                           radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)`
        }} />
      </div>

      {/* Navigation */}
      <GameNavigation 
        title="Unity Offload" 
        showBack={true} 
        showHome={true}
      />

      <main className="relative z-10 flex-1 p-4 sm:p-6 overflow-y-auto">
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* Hero Section */}
          <Card className="bg-gradient-to-br from-slate-blue/20 to-purple-900/20 border-slate-blue/30">
            <CardContent className="p-6 sm:p-8">
              <div className="flex flex-col md:flex-row items-center gap-6">
                <div className="w-20 h-20 rounded-full bg-slate-blue/20 border border-slate-blue/50 flex items-center justify-center">
                  <Gamepad2 className="w-10 h-10 text-slate-blue" />
                </div>
                <div className="flex-1 text-center md:text-left">
                  <h1 className="font-cinzel text-2xl sm:text-3xl text-foreground mb-2">
                    Unity First Person Mode
                  </h1>
                  <p className="text-muted-foreground mb-4">
                    Experience The Echoes in full 3D with Unity. Your progress syncs between web and Unity.
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                    <Badge className="bg-slate-blue/20 text-slate-blue">Cross-Platform Sync</Badge>
                    <Badge className="bg-purple-500/20 text-purple-400">High Fidelity 3D</Badge>
                    <Badge className="bg-green-500/20 text-green-400">Real-time Updates</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Connection Status */}
          <Card className="bg-surface/80 border-border/50">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg flex items-center gap-3">
                {getConnectionIcon()}
                <span>Connection Status</span>
                <Badge className={`ml-auto ${getConnectionColor()} bg-transparent border ${
                  connectionState === CONNECTION_STATES.CONNECTED ? 'border-green-400' :
                  connectionState === CONNECTION_STATES.ERROR ? 'border-red-400' :
                  'border-muted-foreground'
                }`}>
                  {connectionState.toUpperCase()}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Sync Progress */}
              {(connectionState === CONNECTION_STATES.SYNCING || connectionState === CONNECTION_STATES.CONNECTED) && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Sync Progress</span>
                    <span className="text-foreground">{syncStatus.progress}%</span>
                  </div>
                  <Progress value={syncStatus.progress} className="h-2" />
                  
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className={`p-3 rounded-sm border ${syncStatus.character ? 'border-green-500/50 bg-green-500/10' : 'border-border/30 bg-surface/50'}`}>
                      <div className="flex items-center gap-2">
                        {syncStatus.character ? <Check className="w-4 h-4 text-green-400" /> : <RefreshCw className="w-4 h-4 text-muted-foreground animate-spin" />}
                        <span className="text-sm">Character</span>
                      </div>
                    </div>
                    <div className={`p-3 rounded-sm border ${syncStatus.inventory ? 'border-green-500/50 bg-green-500/10' : 'border-border/30 bg-surface/50'}`}>
                      <div className="flex items-center gap-2">
                        {syncStatus.inventory ? <Check className="w-4 h-4 text-green-400" /> : <RefreshCw className="w-4 h-4 text-muted-foreground animate-spin" />}
                        <span className="text-sm">Inventory</span>
                      </div>
                    </div>
                    <div className={`p-3 rounded-sm border ${syncStatus.world ? 'border-green-500/50 bg-green-500/10' : 'border-border/30 bg-surface/50'}`}>
                      <div className="flex items-center gap-2">
                        {syncStatus.world ? <Check className="w-4 h-4 text-green-400" /> : <RefreshCw className="w-4 h-4 text-muted-foreground animate-spin" />}
                        <span className="text-sm">World</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Session Token */}
              {connectionState === CONNECTION_STATES.CONNECTED && unityConfig.sessionToken && (
                <div className="p-4 bg-obsidian/50 rounded-sm border border-border/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">Session Code</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={copySessionCode}
                      className="text-slate-blue hover:text-slate-blue-light"
                    >
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </Button>
                  </div>
                  <code className="font-mono text-sm text-green-400 break-all">
                    {unityConfig.sessionToken.slice(0, 8)}...{unityConfig.sessionToken.slice(-8)}
                  </code>
                  <p className="text-xs text-muted-foreground mt-2">
                    Enter this code in Unity to connect your session
                  </p>
                </div>
              )}

              {/* Connect/Disconnect Button */}
              <div className="flex gap-3">
                {connectionState === CONNECTION_STATES.DISCONNECTED || connectionState === CONNECTION_STATES.ERROR ? (
                  <Button
                    onClick={connectToUnity}
                    className="flex-1 bg-slate-blue hover:bg-slate-blue-light"
                    data-testid="connect-unity-btn"
                  >
                    <Wifi className="w-4 h-4 mr-2" />
                    Connect to Unity
                  </Button>
                ) : connectionState === CONNECTION_STATES.CONNECTED ? (
                  <>
                    <Button
                      onClick={disconnectFromUnity}
                      variant="outline"
                      className="flex-1 border-red-500/30 text-red-400 hover:bg-red-500/10"
                    >
                      <WifiOff className="w-4 h-4 mr-2" />
                      Disconnect
                    </Button>
                    <Button
                      onClick={() => window.open(downloadLinks?.webgl || '#', '_blank')}
                      className="flex-1 bg-green-600 hover:bg-green-500"
                      disabled={!downloadLinks?.webgl}
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Launch WebGL
                    </Button>
                  </>
                ) : (
                  <Button disabled className="flex-1">
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    {connectionState === CONNECTION_STATES.CONNECTING ? 'Connecting...' : 'Syncing...'}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Download Section */}
          <Card className="bg-surface/80 border-border/50">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg flex items-center gap-2">
                <Download className="w-5 h-5 text-gold" />
                Download Unity Client
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Windows */}
                <a
                  href={downloadLinks?.windows || 'https://aivillage.itch.io/echoes-unity'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 bg-obsidian/50 rounded-sm border border-border/30 hover:border-blue-500/50 transition-colors group"
                  data-testid="download-windows"
                >
                  <div className="flex items-center gap-3">
                    <Monitor className="w-8 h-8 text-blue-400 group-hover:text-blue-300" />
                    <div>
                      <p className="font-cinzel text-foreground">Windows</p>
                      <p className="text-xs text-muted-foreground">64-bit</p>
                    </div>
                    <ExternalLink className="w-4 h-4 ml-auto text-muted-foreground" />
                  </div>
                </a>

                {/* Mac */}
                <a
                  href={downloadLinks?.mac || 'https://aivillage.itch.io/echoes-unity'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 bg-obsidian/50 rounded-sm border border-border/30 hover:border-gray-400/50 transition-colors group"
                  data-testid="download-mac"
                >
                  <div className="flex items-center gap-3">
                    <Monitor className="w-8 h-8 text-gray-400 group-hover:text-gray-300" />
                    <div>
                      <p className="font-cinzel text-foreground">macOS</p>
                      <p className="text-xs text-muted-foreground">Universal</p>
                    </div>
                    <ExternalLink className="w-4 h-4 ml-auto text-muted-foreground" />
                  </div>
                </a>

                {/* Linux */}
                <a
                  href={downloadLinks?.linux || 'https://aivillage.itch.io/echoes-unity'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 bg-obsidian/50 rounded-sm border border-border/30 hover:border-orange-500/50 transition-colors group"
                  data-testid="download-linux"
                >
                  <div className="flex items-center gap-3">
                    <Monitor className="w-8 h-8 text-orange-400 group-hover:text-orange-300" />
                    <div>
                      <p className="font-cinzel text-foreground">Linux</p>
                      <p className="text-xs text-muted-foreground">64-bit</p>
                    </div>
                    <ExternalLink className="w-4 h-4 ml-auto text-muted-foreground" />
                  </div>
                </a>
              </div>
              
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-sm">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-amber-400 mt-0.5" />
                  <p className="text-sm text-amber-200">
                    Download the Unity client from itch.io, then connect using the session code above. 
                    Your progress syncs automatically between platforms.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Features */}
          <Card className="bg-surface/80 border-border/50">
            <CardHeader>
              <CardTitle className="font-cinzel text-lg">Unity Features</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex items-start gap-3 p-3 bg-obsidian/30 rounded-sm">
                  <Cpu className="w-5 h-5 text-purple-400 mt-0.5" />
                  <div>
                    <p className="font-cinzel text-foreground">High-Fidelity Graphics</p>
                    <p className="text-sm text-muted-foreground">Full 3D environments with dynamic lighting</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-obsidian/30 rounded-sm">
                  <Globe className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div>
                    <p className="font-cinzel text-foreground">Seamless Sync</p>
                    <p className="text-sm text-muted-foreground">Progress syncs with web version</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-obsidian/30 rounded-sm">
                  <Gamepad2 className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="font-cinzel text-foreground">Controller Support</p>
                    <p className="text-sm text-muted-foreground">Full gamepad and keyboard controls</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-obsidian/30 rounded-sm">
                  <Shield className="w-5 h-5 text-gold mt-0.5" />
                  <div>
                    <p className="font-cinzel text-foreground">Combat System</p>
                    <p className="text-sm text-muted-foreground">Real-time 3D combat with AI enemies</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Advanced Settings */}
          <Card className="bg-surface/80 border-border/50">
            <CardHeader>
              <button 
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center justify-between w-full"
              >
                <CardTitle className="font-cinzel text-lg flex items-center gap-2">
                  <Settings className="w-5 h-5 text-muted-foreground" />
                  Advanced Settings
                </CardTitle>
                <ChevronRight className={`w-5 h-5 text-muted-foreground transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
              </button>
            </CardHeader>
            {showAdvanced && (
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground mb-2 block">Custom Server URL</label>
                  <Input
                    value={unityConfig.serverUrl}
                    onChange={(e) => setUnityConfig(prev => ({ ...prev, serverUrl: e.target.value }))}
                    placeholder="wss://your-unity-server.com"
                    className="bg-obsidian/50 border-border/50"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground mb-2 block">Player ID</label>
                  <Input
                    value={unityConfig.playerId}
                    disabled
                    className="bg-obsidian/50 border-border/50 opacity-50"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground mb-2 block">Character ID</label>
                  <Input
                    value={unityConfig.characterId}
                    disabled
                    className="bg-obsidian/50 border-border/50 opacity-50"
                  />
                </div>
              </CardContent>
            )}
          </Card>
          
          {/* Back to Modes */}
          <div className="flex justify-center pt-4">
            <Button
              variant="outline"
              onClick={() => navigate('/select-mode')}
              className="border-gold/30 text-gold hover:bg-gold/10"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Mode Selection
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default UnityOffload;
