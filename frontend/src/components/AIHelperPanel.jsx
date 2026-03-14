import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Smartphone, Wifi, Battery, Bell, Vibrate, MapPin, 
  RotateCw, Clipboard, Moon, AlertTriangle, Check, X,
  Zap, Signal
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CAPABILITY_ICONS = {
  geolocation_approximate: MapPin,
  vibration: Vibrate,
  notification: Bell,
  orientation: RotateCw,
  battery: Battery,
  network: Wifi,
  wake_lock: Moon,
  clipboard: Clipboard
};

const AIHelperPanel = ({ userId, onClose }) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [capabilities, setCapabilities] = useState({});
  const [permissions, setPermissions] = useState({});
  const [deviceData, setDeviceData] = useState({});
  const [loading, setLoading] = useState(true);
  
  // Detect mobile device
  useEffect(() => {
    const checkMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    setIsMobile(checkMobile);
  }, []);
  
  // Load AI Helper status
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const [statusRes, capsRes] = await Promise.all([
          axios.get(`${API}/ai-helper/status?user_id=${userId}`),
          axios.get(`${API}/ai-helper/capabilities?user_id=${userId}&is_mobile=${isMobile}`)
        ]);
        
        setIsEnabled(statusRes.data.enabled);
        if (capsRes.data.available) {
          setCapabilities(capsRes.data.capabilities);
        }
      } catch (error) {
        console.error('Failed to load AI Helper status:', error);
      } finally {
        setLoading(false);
      }
    };
    
    if (userId) loadStatus();
  }, [userId, isMobile]);
  
  // Request capability access
  const requestAccess = async (capability) => {
    try {
      const res = await axios.post(`${API}/ai-helper/request-access`, {
        user_id: userId,
        device_type: isMobile ? 'mobile' : 'desktop',
        is_mobile: isMobile,
        capability: capability,
        action: 'request'
      });
      
      if (res.data.status === 'granted') {
        setPermissions(prev => ({ ...prev, [capability]: true }));
        toast.success(`${capability} access granted`);
      } else if (res.data.status === 'permission_required') {
        // Handle browser permission request
        await handleBrowserPermission(capability);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Access request failed');
    }
  };
  
  // Handle browser-level permissions
  const handleBrowserPermission = async (capability) => {
    try {
      switch (capability) {
        case 'notification':
          const notifPerm = await Notification.requestPermission();
          if (notifPerm === 'granted') {
            setPermissions(prev => ({ ...prev, notification: true }));
            toast.success('Notifications enabled');
          }
          break;
          
        case 'geolocation_approximate':
          // Request with low accuracy (approximate only)
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              // We only use timezone, never precise coords
              const offset = new Date().getTimezoneOffset() / -60;
              setDeviceData(prev => ({ ...prev, timezone_offset: offset }));
              setPermissions(prev => ({ ...prev, geolocation_approximate: true }));
              toast.success('Approximate location access granted');
            },
            (err) => {
              toast.error('Location access denied');
            },
            { enableHighAccuracy: false, maximumAge: 300000 } // Low accuracy, cache for 5 min
          );
          break;
          
        case 'clipboard':
          // Clipboard permission is implicit on user action
          setPermissions(prev => ({ ...prev, clipboard: true }));
          toast.success('Clipboard access ready');
          break;
          
        default:
          setPermissions(prev => ({ ...prev, [capability]: true }));
      }
    } catch (error) {
      console.error('Permission error:', error);
      toast.error('Permission denied');
    }
  };
  
  // Execute AI Helper commands
  const executeCommand = useCallback(async (commandType, payload = {}) => {
    try {
      const res = await axios.post(`${API}/ai-helper/execute`, {
        user_id: userId,
        command_type: commandType,
        payload: payload
      });
      
      // Handle frontend execution
      if (res.data.status === 'execute') {
        switch (res.data.command) {
          case 'vibrate':
            if (navigator.vibrate) {
              navigator.vibrate(res.data.pattern);
              toast.success(`Vibration: ${res.data.pattern_name}`);
            }
            break;
            
          case 'notification':
            if (Notification.permission === 'granted') {
              new Notification(res.data.title, {
                body: res.data.body,
                icon: res.data.icon,
                tag: res.data.tag
              });
            }
            break;
            
          case 'wake_lock':
            if ('wakeLock' in navigator) {
              if (res.data.action === 'request') {
                const lock = await navigator.wakeLock.request('screen');
                setDeviceData(prev => ({ ...prev, wakeLock: lock }));
                toast.success('Screen will stay on');
              }
            }
            break;
            
          case 'clipboard_write':
            await navigator.clipboard.writeText(res.data.data);
            toast.success('Copied to clipboard');
            break;
        }
      } else if (res.data.status === 'query') {
        // Query device data
        switch (res.data.command) {
          case 'battery':
            if ('getBattery' in navigator) {
              const battery = await navigator.getBattery();
              setDeviceData(prev => ({
                ...prev,
                battery: {
                  level: Math.round(battery.level * 100),
                  charging: battery.charging
                }
              }));
            }
            break;
            
          case 'network':
            if (navigator.connection) {
              setDeviceData(prev => ({
                ...prev,
                network: {
                  type: navigator.connection.type,
                  effectiveType: navigator.connection.effectiveType,
                  downlink: navigator.connection.downlink
                }
              }));
            }
            break;
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Command failed');
    }
  }, [userId]);
  
  if (loading) {
    return (
      <Card className="bg-surface/95 border-gold/30 p-4 rounded-sm">
        <div className="text-center text-muted-foreground">Loading AI Helper...</div>
      </Card>
    );
  }
  
  if (!isEnabled) {
    return (
      <Card className="bg-surface/95 border-red-500/30 p-4 rounded-sm">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-400" />
          <div>
            <div className="font-cinzel text-foreground">AI Helper Restricted</div>
            <div className="text-xs text-muted-foreground">
              This test feature is currently available only to Sirix-1
            </div>
          </div>
        </div>
      </Card>
    );
  }
  
  return (
    <Card className="bg-surface/95 border-gold/50 rounded-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-gold/20 to-purple-500/20 p-4 border-b border-border/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gold/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-gold" />
            </div>
            <div>
              <h3 className="font-cinzel text-lg text-gold">AI Helper</h3>
              <div className="flex items-center gap-2">
                <Badge className="bg-yellow-500/20 text-yellow-400 text-xs">TEST FEATURE</Badge>
                <Badge className={`${isMobile ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'} text-xs`}>
                  <Smartphone className="w-3 h-3 mr-1" />
                  {isMobile ? 'Mobile' : 'Desktop'}
                </Badge>
              </div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>
      
      {/* Capabilities */}
      <div className="p-4 space-y-4">
        <div className="text-sm text-muted-foreground mb-2">
          Device capabilities available for enhanced gameplay:
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(capabilities).map(([capId, capData]) => {
            const Icon = CAPABILITY_ICONS[capId] || Signal;
            const hasPermission = permissions[capId];
            
            return (
              <div 
                key={capId}
                className={`p-3 rounded-sm border transition-all ${
                  hasPermission 
                    ? 'bg-green-500/10 border-green-500/30' 
                    : 'bg-surface/50 border-border/30 hover:border-gold/30'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`w-4 h-4 ${hasPermission ? 'text-green-400' : 'text-muted-foreground'}`} />
                  <span className="text-sm font-medium capitalize">
                    {capId.replace(/_/g, ' ')}
                  </span>
                  {hasPermission && <Check className="w-3 h-3 text-green-400 ml-auto" />}
                </div>
                <p className="text-xs text-muted-foreground mb-2">{capData.description}</p>
                
                {!hasPermission ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full text-xs"
                    onClick={() => requestAccess(capId)}
                  >
                    {capData.requires_permission ? 'Request Permission' : 'Enable'}
                  </Button>
                ) : (
                  <div className="flex gap-1">
                    {capId === 'vibration' && (
                      <>
                        <Button size="sm" variant="ghost" className="flex-1 text-xs"
                          onClick={() => executeCommand('vibrate', { pattern: 'alert' })}>
                          Alert
                        </Button>
                        <Button size="sm" variant="ghost" className="flex-1 text-xs"
                          onClick={() => executeCommand('vibrate', { pattern: 'heartbeat' })}>
                          Pulse
                        </Button>
                      </>
                    )}
                    {capId === 'notification' && (
                      <Button size="sm" variant="ghost" className="flex-1 text-xs"
                        onClick={() => executeCommand('notify', { 
                          title: 'AI Village', 
                          body: 'Test notification from AI Helper' 
                        })}>
                        Test Notify
                      </Button>
                    )}
                    {capId === 'battery' && (
                      <Button size="sm" variant="ghost" className="flex-1 text-xs"
                        onClick={() => executeCommand('query_battery')}>
                        Check Battery
                      </Button>
                    )}
                    {capId === 'network' && (
                      <Button size="sm" variant="ghost" className="flex-1 text-xs"
                        onClick={() => executeCommand('query_network')}>
                        Check Network
                      </Button>
                    )}
                    {capId === 'wake_lock' && (
                      <Button size="sm" variant="ghost" className="flex-1 text-xs"
                        onClick={() => executeCommand('wake_lock', { action: 'request' })}>
                        Keep Awake
                      </Button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {/* Device Data Display */}
        {Object.keys(deviceData).length > 0 && (
          <div className="mt-4 p-3 bg-obsidian/50 rounded-sm border border-border/30">
            <div className="text-xs font-mono text-gold mb-2">Device Data:</div>
            <div className="space-y-1 text-xs font-mono text-foreground/80">
              {deviceData.battery && (
                <div className="flex items-center gap-2">
                  <Battery className="w-3 h-3" />
                  <span>{deviceData.battery.level}% {deviceData.battery.charging ? '(Charging)' : ''}</span>
                </div>
              )}
              {deviceData.network && (
                <div className="flex items-center gap-2">
                  <Wifi className="w-3 h-3" />
                  <span>{deviceData.network.effectiveType || deviceData.network.type || 'Unknown'}</span>
                </div>
              )}
              {deviceData.timezone_offset !== undefined && (
                <div className="flex items-center gap-2">
                  <MapPin className="w-3 h-3" />
                  <span>UTC{deviceData.timezone_offset >= 0 ? '+' : ''}{deviceData.timezone_offset}</span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Privacy Notice */}
        <div className="text-xs text-muted-foreground p-2 bg-yellow-500/5 rounded-sm border border-yellow-500/20">
          <AlertTriangle className="w-3 h-3 inline mr-1 text-yellow-500" />
          Privacy: Location uses APPROXIMATE data only (timezone/region). Precise coordinates are never collected.
        </div>
      </div>
    </Card>
  );
};

export default AIHelperPanel;
