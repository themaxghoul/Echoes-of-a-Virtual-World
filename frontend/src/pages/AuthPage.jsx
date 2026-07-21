import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Eye, EyeOff, Loader2, LogIn, UserPlus, Shield, ArrowLeft, Lock } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { clearNavHistory } from '@/components/GameNavigation';

// Social login icons (using simple SVG paths)
const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

const AppleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
  </svg>
);

const FacebookIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#1877F2">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const XIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [socialLoading, setSocialLoading] = useState(null);
  
  // Login state
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  
  // Register state
  const [registerData, setRegisterData] = useState({
    username: '',
    displayName: '',
    password: '',
    confirmPassword: ''
  });

  // Clear nav history on auth page & check for errors from OAuth
  useEffect(() => {
    clearNavHistory();
    
    // Check for error state from OAuth callback
    if (location.state?.error) {
      toast.error(location.state.error);
    }
  }, [location]);

  // Google OAuth login handler
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const handleGoogleLogin = () => {
    setSocialLoading('google');
    const redirectUrl = window.location.origin + '/auth';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  // Coming soon handlers for other social logins
  const handleSocialComingSoon = (provider) => {
    toast.info(`${provider} login coming soon!`, {
      description: 'This feature is under development.'
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginData.username.trim()) {
      toast.error('Please enter your username');
      return;
    }
    if (!loginData.password.trim()) {
      toast.error('Please enter your password');
      return;
    }

    setIsLoading(true);
    try {
      // Use the proper login endpoint with password
      const response = await axios.post(`${API}/auth/login`, {
        username: loginData.username.toLowerCase(),
        password: loginData.password
      });
      
      if (response.data && response.data.user) {
        const user = response.data.user;
        
        // Store user data
        localStorage.setItem('userId', user.id);
        localStorage.setItem('username', user.username);
        localStorage.setItem('displayName', user.display_name);
        localStorage.setItem('isTranscendent', user.is_transcendent ? 'true' : 'false');
        localStorage.setItem('permissionLevel', user.permission_level || 'basic');
        
        // Record login stats
        try {
          await axios.post(`${API}/users/track-login`, { user_id: user.id });
        } catch (e) {
          console.log('Stats tracking skipped');
        }
        
        // Check if user has characters
        const charsRes = await axios.get(`${API}/characters/${user.id}`);
        
        if (charsRes.data && charsRes.data.length > 0) {
          // Has character, go to mode selection
          const mainChar = charsRes.data[0];
          localStorage.setItem('currentCharacterId', mainChar.id);
          localStorage.setItem('characterName', mainChar.name);
          toast.success(`Welcome back, ${user.display_name}!`);
          navigate('/select-mode');
        } else {
          // No character, go to character creation
          toast.success('Welcome! Let\'s create your character.');
          navigate('/create-character');
        }
      }
    } catch (error) {
      if (error.response?.status === 401) {
        toast.error('Invalid password. Please try again.');
      } else if (error.response?.status === 404) {
        toast.error('User not found. Please register first.');
      } else {
        toast.error(error.response?.data?.detail || 'Login failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    
    if (!registerData.username.trim() || !registerData.displayName.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    if (registerData.username.length < 3) {
      toast.error('Username must be at least 3 characters');
      return;
    }

    if (!registerData.password || registerData.password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/auth/register`, {
        username: registerData.username.toLowerCase(),
        display_name: registerData.displayName,
        password: registerData.password
      });
      
      if (response.data && response.data.user) {
        const user = response.data.user;
        
        localStorage.setItem('userId', user.id);
        localStorage.setItem('username', user.username);
        localStorage.setItem('displayName', user.display_name);
        localStorage.setItem('isTranscendent', 'false');
        localStorage.setItem('permissionLevel', 'basic');
        
        toast.success('Account created! Now create your character.');
        navigate('/create-character');
      }
    } catch (error) {
      if (error.response?.data?.detail?.includes('already exists')) {
        toast.error('Username already taken. Choose another.');
      } else {
        toast.error(error.response?.data?.detail || 'Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian flex items-center justify-center px-4">
      {/* Background */}
      <div 
        className="fixed inset-0 bg-cover bg-center opacity-30"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1746472603784-23c90049ca14?w=1920&q=80')`,
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/80 to-obsidian" />
      </div>

      {/* Back to Landing */}
      <Button
        variant="ghost"
        onClick={() => navigate('/')}
        className="absolute top-4 left-4 z-20 text-muted-foreground hover:text-gold"
        data-testid="back-to-landing"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back
      </Button>

      {/* Content */}
      <div className="relative z-10 w-full max-w-md">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="font-cinzel text-4xl sm:text-5xl font-bold mb-2">
            <span className="text-gold-gradient">AI Village</span>
          </h1>
          <p className="font-cinzel text-lg text-gold/80 tracking-[0.2em]">THE ECHOES</p>
        </div>

        {/* Auth Card */}
        <Card className="bg-surface/90 backdrop-blur-sm border-border/50 rounded-sm">
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-obsidian/50 rounded-t-sm">
              <TabsTrigger 
                value="login" 
                className="font-cinzel data-[state=active]:bg-gold data-[state=active]:text-black rounded-sm"
              >
                Login
              </TabsTrigger>
              <TabsTrigger 
                value="register"
                className="font-cinzel data-[state=active]:bg-gold data-[state=active]:text-black rounded-sm"
              >
                Register
              </TabsTrigger>
            </TabsList>

            {/* Login Tab */}
            <TabsContent value="login" className="p-6">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Username</Label>
                  <Input
                    data-testid="login-username"
                    value={loginData.username}
                    onChange={(e) => setLoginData(prev => ({ ...prev, username: e.target.value }))}
                    placeholder="Enter your username"
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Password</Label>
                  <div className="relative">
                    <Input
                      data-testid="login-password"
                      type={showPassword ? 'text' : 'password'}
                      value={loginData.password}
                      onChange={(e) => setLoginData(prev => ({ ...prev, password: e.target.value }))}
                      placeholder="Enter your password"
                      className="bg-obsidian border-border/50 rounded-sm mt-1 pr-10"
                      disabled={isLoading}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <Eye className="w-4 h-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>

                <Button
                  data-testid="login-submit"
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gold text-black hover:bg-gold-light font-cinzel rounded-sm py-6"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  ) : (
                    <LogIn className="w-5 h-5 mr-2" />
                  )}
                  Enter The Echoes
                </Button>
              </form>
              
              {/* Social Login Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border/30" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-surface px-2 text-muted-foreground">Or continue with</span>
                </div>
              </div>
              
              {/* Social Login Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleGoogleLogin}
                  disabled={socialLoading === 'google'}
                  className="border-border/50 hover:bg-white/10 rounded-sm py-5"
                  data-testid="google-login-btn"
                >
                  {socialLoading === 'google' ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <GoogleIcon />
                  )}
                  <span className="ml-2 text-sm">Google</span>
                </Button>
                
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleSocialComingSoon('Apple')}
                  className="border-border/50 hover:bg-white/10 rounded-sm py-5 relative"
                  data-testid="apple-login-btn"
                >
                  <AppleIcon />
                  <span className="ml-2 text-sm">Apple</span>
                  <span className="absolute -top-2 -right-2 text-[10px] bg-slate-blue px-1.5 py-0.5 rounded-full">Soon</span>
                </Button>
                
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleSocialComingSoon('Facebook')}
                  className="border-border/50 hover:bg-white/10 rounded-sm py-5 relative"
                  data-testid="facebook-login-btn"
                >
                  <FacebookIcon />
                  <span className="ml-2 text-sm">Facebook</span>
                  <span className="absolute -top-2 -right-2 text-[10px] bg-slate-blue px-1.5 py-0.5 rounded-full">Soon</span>
                </Button>
                
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleSocialComingSoon('X')}
                  className="border-border/50 hover:bg-white/10 rounded-sm py-5 relative"
                  data-testid="x-login-btn"
                >
                  <XIcon />
                  <span className="ml-2 text-sm">X</span>
                  <span className="absolute -top-2 -right-2 text-[10px] bg-slate-blue px-1.5 py-0.5 rounded-full">Soon</span>
                </Button>
              </div>
              
              {/* Special Account Note */}
              <div className="mt-4 p-3 bg-gold/5 border border-gold/20 rounded-sm">
                <div className="flex items-center gap-2 text-gold text-xs">
                  <Shield className="w-4 h-4" />
                  <span className="font-cinzel">Sirix-1 Admin Account</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Reserved admin login: <code className="text-gold">sirix_1</code>
                </p>
              </div>
            </TabsContent>

            {/* Register Tab */}
            <TabsContent value="register" className="p-6">
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Username</Label>
                  <Input
                    data-testid="register-username"
                    value={registerData.username}
                    onChange={(e) => setRegisterData(prev => ({ ...prev, username: e.target.value }))}
                    placeholder="Choose a unique username"
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Display Name</Label>
                  <Input
                    data-testid="register-displayname"
                    value={registerData.displayName}
                    onChange={(e) => setRegisterData(prev => ({ ...prev, displayName: e.target.value }))}
                    placeholder="How others will see you"
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Password</Label>
                  <div className="relative">
                    <Input
                      data-testid="register-password"
                      type={showPassword ? 'text' : 'password'}
                      value={registerData.password}
                      onChange={(e) => setRegisterData(prev => ({ ...prev, password: e.target.value }))}
                      placeholder="Create a password (min 6 chars)"
                      className="bg-obsidian border-border/50 rounded-sm mt-1 pr-10"
                      disabled={isLoading}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <Eye className="w-4 h-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>

                <div>
                  <Label className="font-manrope text-sm text-muted-foreground">Confirm Password</Label>
                  <Input
                    data-testid="register-confirm-password"
                    type={showPassword ? 'text' : 'password'}
                    value={registerData.confirmPassword}
                    onChange={(e) => setRegisterData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                    placeholder="Confirm your password"
                    className="bg-obsidian border-border/50 rounded-sm mt-1"
                    disabled={isLoading}
                  />
                </div>

                <Button
                  data-testid="register-submit"
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-slate-blue text-white hover:bg-slate-blue-light font-cinzel rounded-sm py-6"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  ) : (
                    <UserPlus className="w-5 h-5 mr-2" />
                  )}
                  Create Account
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </Card>

        {/* Footer */}
        <p className="text-center mt-6 font-mono text-xs text-muted-foreground/50">
          v0.1.0 // Early Access
        </p>
      </div>
    </div>
  );
};

export default AuthPage;
