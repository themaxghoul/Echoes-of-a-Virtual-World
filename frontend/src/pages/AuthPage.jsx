import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Eye, EyeOff, Loader2, LogIn, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

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

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginData.username.trim()) {
      toast.error('Please enter your username');
      return;
    }

    setIsLoading(true);
    try {
      // Check if user exists
      const response = await axios.get(`${API}/users/${loginData.username.toLowerCase()}`);
      
      if (response.data) {
        // Store user data
        localStorage.setItem('userId', response.data.id);
        localStorage.setItem('username', response.data.username);
        localStorage.setItem('displayName', response.data.display_name);
        
        // Check if user has characters
        const charsRes = await axios.get(`${API}/characters/${response.data.id}`);
        
        if (charsRes.data && charsRes.data.length > 0) {
          // Has character, go to mode selection
          localStorage.setItem('currentCharacterId', charsRes.data[0].id);
          toast.success(`Welcome back, ${response.data.display_name}!`);
          navigate('/select-mode');
        } else {
          // No character, go to character creation
          toast.success('Welcome! Let\'s create your character.');
          navigate('/create-character');
        }
      }
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error('User not found. Please register first.');
      } else {
        toast.error('Failed to login. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    
    if (!registerData.username.trim() || !registerData.displayName.trim()) {
      toast.error('Please fill in all fields');
      return;
    }
    
    if (registerData.username.length < 3) {
      toast.error('Username must be at least 3 characters');
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/users`, {
        username: registerData.username.toLowerCase(),
        display_name: registerData.displayName,
        permission_level: 'basic'
      });
      
      if (response.data) {
        localStorage.setItem('userId', response.data.id);
        localStorage.setItem('username', response.data.username);
        localStorage.setItem('displayName', response.data.display_name);
        
        toast.success('Account created! Now create your character.');
        navigate('/create-character');
      }
    } catch (error) {
      if (error.response?.data?.detail?.includes('already exists')) {
        toast.error('Username already taken. Choose another.');
      } else {
        toast.error('Registration failed. Please try again.');
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
          v0.2.0 // Phase II: The Awakening
        </p>
      </div>
    </div>
  );
};

export default AuthPage;
