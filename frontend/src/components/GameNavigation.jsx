// Navigation component with back button for all pages
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { 
  ArrowLeft, Home, User, Settings, LogOut, 
  Gamepad2, MessageSquare, DollarSign
} from 'lucide-react';

// Navigation history stack
const NAV_HISTORY_KEY = 'ai_village_nav_history';

export const getNavHistory = () => {
  try {
    const history = localStorage.getItem(NAV_HISTORY_KEY);
    return history ? JSON.parse(history) : [];
  } catch {
    return [];
  }
};

export const pushNavHistory = (path) => {
  const history = getNavHistory();
  // Don't add duplicates consecutively
  if (history[history.length - 1] !== path) {
    history.push(path);
    // Keep max 20 entries
    if (history.length > 20) history.shift();
    localStorage.setItem(NAV_HISTORY_KEY, JSON.stringify(history));
  }
};

export const popNavHistory = () => {
  const history = getNavHistory();
  history.pop(); // Remove current
  const prev = history.pop(); // Get previous
  localStorage.setItem(NAV_HISTORY_KEY, JSON.stringify(history));
  return prev;
};

export const clearNavHistory = () => {
  localStorage.removeItem(NAV_HISTORY_KEY);
};

// Page titles for breadcrumb
const PAGE_TITLES = {
  '/': 'Home',
  '/auth': 'Login',
  '/create-character': 'Create Character',
  '/select-mode': 'Mode Selection',
  '/village': 'Story Mode',
  '/play': 'First Person',
  '/play-classic': 'Classic View',
  '/building': 'Building',
  '/trading': 'Trading',
  '/guilds': 'Guilds',
  '/inventory': 'Inventory',
  '/quests': 'Quests',
  '/profile': 'Profile',
  '/earnings': 'Earnings Hub',
  '/dataspace': 'Dataspace'
};

export const GameNavigation = ({ 
  showBack = true, 
  showHome = true,
  showProfile = false,
  showLogout = false,
  title = null,
  className = ''
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleBack = () => {
    const prevPath = popNavHistory();
    if (prevPath && prevPath !== location.pathname) {
      navigate(prevPath);
    } else {
      // Default fallback paths
      const fallbacks = {
        '/play': '/select-mode',
        '/village': '/select-mode',
        '/building': '/select-mode',
        '/trading': '/select-mode',
        '/guilds': '/select-mode',
        '/inventory': '/select-mode',
        '/quests': '/select-mode',
        '/profile': '/select-mode',
        '/earnings': '/select-mode',
        '/dataspace': '/select-mode',
        '/create-character': '/auth',
        '/select-mode': '/auth'
      };
      navigate(fallbacks[location.pathname] || '/select-mode');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('userId');
    localStorage.removeItem('username');
    localStorage.removeItem('displayName');
    localStorage.removeItem('currentCharacterId');
    localStorage.removeItem('gameMode');
    clearNavHistory();
    navigate('/auth');
  };

  const pageTitle = title || PAGE_TITLES[location.pathname] || 'AI Village';

  return (
    <nav className={`flex items-center justify-between p-4 bg-obsidian/80 backdrop-blur-sm border-b border-border/30 ${className}`}>
      <div className="flex items-center gap-3">
        {showBack && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBack}
            className="rounded-sm hover:bg-gold/10"
            data-testid="nav-back-btn"
          >
            <ArrowLeft className="w-5 h-5 text-gold" />
          </Button>
        )}
        
        {showHome && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/select-mode')}
            className="rounded-sm hover:bg-slate-blue/10"
            data-testid="nav-home-btn"
          >
            <Home className="w-5 h-5 text-slate-blue" />
          </Button>
        )}
        
        <span className="font-cinzel text-lg text-foreground">{pageTitle}</span>
      </div>
      
      <div className="flex items-center gap-2">
        {showProfile && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/profile')}
            className="rounded-sm"
            data-testid="nav-profile-btn"
          >
            <User className="w-5 h-5 text-muted-foreground" />
          </Button>
        )}
        
        {showLogout && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="rounded-sm text-red-400 hover:text-red-300 hover:bg-red-400/10"
            data-testid="nav-logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        )}
      </div>
    </nav>
  );
};

// Quick action bar for game modes
export const GameModeBar = ({ currentMode = 'story' }) => {
  const navigate = useNavigate();
  
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-obsidian/90 backdrop-blur-sm border-t border-border/30 p-2 flex justify-center gap-2 z-50">
      <Button
        variant={currentMode === 'story' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => navigate('/village')}
        className={`rounded-sm ${currentMode === 'story' ? 'bg-gold text-black' : ''}`}
      >
        <MessageSquare className="w-4 h-4 mr-1" />
        Story
      </Button>
      <Button
        variant={currentMode === 'firstperson' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => navigate('/play')}
        className={`rounded-sm ${currentMode === 'firstperson' ? 'bg-slate-blue text-white' : ''}`}
      >
        <Gamepad2 className="w-4 h-4 mr-1" />
        3D View
      </Button>
      <Button
        variant={currentMode === 'earnings' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => navigate('/earnings')}
        className={`rounded-sm ${currentMode === 'earnings' ? 'bg-green-600 text-white' : ''}`}
      >
        <DollarSign className="w-4 h-4 mr-1" />
        Earn
      </Button>
    </div>
  );
};

export default GameNavigation;
