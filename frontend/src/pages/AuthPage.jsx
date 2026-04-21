import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Eye, EyeOff, Loader2, LogIn, UserPlus, Shield, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { clearNavHistory } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AuthPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  // Login state
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  
  // Register state
  const [registerData, setRegisterData] = useState({
    username: '',
    displayName: '',
    password: '',
    confirmPassword: ''
  });

  // Clear nav history on auth page
  useEffect(() => {
    clearNavHistory();
  }, []);

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
          v0.3.0 // Pre-Release for itch.io
        </p>
      </div>
    </div>
  );
};

export default AuthPage;
