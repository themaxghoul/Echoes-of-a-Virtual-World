import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Bell, X, MessageCircle, Users, Swords, 
  Gift, AlertTriangle, Check, Trash2, Settings
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const NOTIFICATION_TYPES = {
  message: { icon: MessageCircle, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  guild: { icon: Users, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  combat: { icon: Swords, color: 'text-red-400', bg: 'bg-red-500/20' },
  gift: { icon: Gift, color: 'text-gold', bg: 'bg-gold/20' },
  system: { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
};

// Request browser notification permission
const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    return false;
  }
  
  if (Notification.permission === 'granted') {
    return true;
  }
  
  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  
  return false;
};

// Send browser notification
const sendBrowserNotification = (title, body, icon = '/favicon.ico') => {
  if (Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon,
      badge: icon,
      tag: 'ai-village',
    });
  }
};

const NotificationCenter = ({ userId, isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [browserPermission, setBrowserPermission] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Load notifications
  const loadNotifications = useCallback(async () => {
    if (!userId) return;
    
    setLoading(true);
    try {
      const res = await axios.get(`${API}/notifications/${userId}`);
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (error) {
      // If endpoint doesn't exist, use localStorage
      const stored = JSON.parse(localStorage.getItem(`notifications_${userId}`) || '[]');
      setNotifications(stored);
      setUnreadCount(stored.filter(n => !n.read).length);
    }
    setLoading(false);
  }, [userId]);
  
  useEffect(() => {
    loadNotifications();
    
    // Check browser notification permission
    if ('Notification' in window) {
      setBrowserPermission(Notification.permission === 'granted');
    }
  }, [loadNotifications]);
  
  const markAsRead = async (notificationId) => {
    setNotifications(prev => 
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
    
    // Save to localStorage
    const updated = notifications.map(n => 
      n.id === notificationId ? { ...n, read: true } : n
    );
    localStorage.setItem(`notifications_${userId}`, JSON.stringify(updated));
  };
  
  const markAllAsRead = () => {
    const updated = notifications.map(n => ({ ...n, read: true }));
    setNotifications(updated);
    setUnreadCount(0);
    localStorage.setItem(`notifications_${userId}`, JSON.stringify(updated));
    toast.success('All notifications marked as read');
  };
  
  const deleteNotification = (notificationId) => {
    const updated = notifications.filter(n => n.id !== notificationId);
    setNotifications(updated);
    localStorage.setItem(`notifications_${userId}`, JSON.stringify(updated));
  };
  
  const enableBrowserNotifications = async () => {
    const granted = await requestNotificationPermission();
    setBrowserPermission(granted);
    if (granted) {
      toast.success('Browser notifications enabled');
      sendBrowserNotification('Notifications Enabled', 'You will now receive notifications from AI Village');
    } else {
      toast.error('Browser notifications blocked');
    }
  };
  
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };
  
  if (!isOpen) return null;
  
  return (
    <Card className="fixed top-16 right-4 w-96 max-h-[80vh] bg-surface/95 backdrop-blur-sm border-gold/30 rounded-sm shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-border/30 flex items-center justify-between bg-obsidian/50">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-gold" />
          <span className="font-cinzel text-gold">Notifications</span>
          {unreadCount > 0 && (
            <Badge className="bg-red-500 text-white text-xs">{unreadCount}</Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={markAllAsRead} className="text-xs">
              <Check className="w-3 h-3 mr-1" />
              Read All
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {/* Browser notification toggle */}
      {!browserPermission && (
        <div className="p-3 border-b border-border/30 bg-yellow-500/10">
          <Button 
            onClick={enableBrowserNotifications}
            size="sm"
            className="w-full bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30"
          >
            <Bell className="w-4 h-4 mr-2" />
            Enable Browser Notifications
          </Button>
        </div>
      )}
      
      {/* Notification List */}
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No notifications yet
          </div>
        ) : (
          <div className="divide-y divide-border/20">
            {notifications.map(notif => {
              const typeInfo = NOTIFICATION_TYPES[notif.type] || NOTIFICATION_TYPES.system;
              const Icon = typeInfo.icon;
              
              return (
                <div 
                  key={notif.id}
                  className={`p-3 hover:bg-white/5 transition-colors ${!notif.read ? 'bg-gold/5' : ''}`}
                  onClick={() => markAsRead(notif.id)}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-full ${typeInfo.bg} flex items-center justify-center flex-shrink-0`}>
                      <Icon className={`w-4 h-4 ${typeInfo.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-medium ${!notif.read ? 'text-foreground' : 'text-muted-foreground'}`}>
                          {notif.title}
                        </span>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="w-6 h-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteNotification(notif.id);
                          }}
                        >
                          <Trash2 className="w-3 h-3 text-muted-foreground" />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{notif.message}</p>
                      <span className="text-xs text-muted-foreground/50">{formatTime(notif.timestamp)}</span>
                    </div>
                    {!notif.read && (
                      <div className="w-2 h-2 rounded-full bg-gold flex-shrink-0 mt-2" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </Card>
  );
};

export default NotificationCenter;

// Notification Bell Button component
export const NotificationBell = ({ userId, onClick }) => {
  const [unreadCount, setUnreadCount] = useState(0);
  
  useEffect(() => {
    if (!userId) return;
    const stored = JSON.parse(localStorage.getItem(`notifications_${userId}`) || '[]');
    setUnreadCount(stored.filter(n => !n.read).length);
  }, [userId]);
  
  return (
    <Button 
      variant="ghost" 
      size="icon" 
      onClick={onClick}
      className="relative"
    >
      <Bell className="w-5 h-5 text-foreground" />
      {unreadCount > 0 && (
        <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </Button>
  );
};

// Helper to add notification
export const addNotification = (userId, notification) => {
  const stored = JSON.parse(localStorage.getItem(`notifications_${userId}`) || '[]');
  const newNotif = {
    id: Date.now().toString(),
    ...notification,
    read: false,
    timestamp: new Date().toISOString(),
  };
  stored.unshift(newNotif);
  localStorage.setItem(`notifications_${userId}`, JSON.stringify(stored.slice(0, 50)));
  
  // Send browser notification if permitted
  if (Notification.permission === 'granted') {
    sendBrowserNotification(notification.title, notification.message);
  }
  
  return newNotif;
};
