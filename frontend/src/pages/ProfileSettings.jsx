import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, User, Palette, MessageSquare, Shield, Save,
  RefreshCw, Eye, EyeOff, Check, Sparkles, Crown, AtSign,
  Key, Image, History, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ProfileSettings = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [options, setOptions] = useState(null);
  const [profile, setProfile] = useState({
    display_name: '',
    username: '',
    bio: '',
    chat_color: 'default',
    profile_picture: '',
    profile_logo: '',
    model_preset: 'human_male',
    model_colors: {
      skin_color: '#E8BEAC',
      hair_color: '#4A3728',
      eye_color: '#634E34',
      accent_color: '#FFD700'
    },
    title_display: '',
    status_message: '',
    show_online: true,
    allow_whispers: true,
    legacy_usernames: [],
    auth_method: 'password'
  });
  
  // Account settings state
  const [newUsername, setNewUsername] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [changingUsername, setChangingUsername] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [showLegacyNames, setShowLegacyNames] = useState(false);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [optionsRes, profileRes] = await Promise.all([
        axios.get(`${API}/profile/customization-options`),
        axios.get(`${API}/profile/customization/${userId}`)
      ]);
      setOptions(optionsRes.data);
      setProfile(profileRes.data);
    } catch (error) {
      console.error('Failed to load profile:', error);
      toast.error('Failed to load profile settings');
    }
    setLoading(false);
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/profile/customization/${userId}`, profile);
      toast.success('Profile saved!');
      // Update localStorage display name
      localStorage.setItem('displayName', profile.display_name);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save profile');
    }
    setSaving(false);
  };

  const updateField = (field, value) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  const updateModelColor = (field, value) => {
    setProfile(prev => ({
      ...prev,
      model_colors: { ...prev.model_colors, [field]: value }
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-gold animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <User className="w-6 h-6" />
                Profile Settings
              </h1>
              <p className="text-sm text-muted-foreground">Customize your appearance and preferences</p>
            </div>
          </div>
          
          <Button 
            onClick={saveProfile} 
            disabled={saving}
            className="bg-gold text-black hover:bg-gold-light"
            data-testid="save-profile-btn"
          >
            {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="bg-surface/50">
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="account">Account</TabsTrigger>
            <TabsTrigger value="appearance">Appearance</TabsTrigger>
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="privacy">Privacy</TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile" className="space-y-6">
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4">Basic Information</h3>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="display_name">Display Name</Label>
                  <Input
                    id="display_name"
                    value={profile.display_name}
                    onChange={(e) => updateField('display_name', e.target.value)}
                    placeholder="Your display name"
                    maxLength={30}
                    className="mt-1"
                    data-testid="display-name-input"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {profile.display_name?.length || 0}/30 characters
                  </p>
                </div>
                
                {/* Profile Logo / Avatar URL */}
                <div>
                  <Label htmlFor="profile_logo" className="flex items-center gap-2">
                    <Image className="w-4 h-4" />
                    Profile Logo URL
                  </Label>
                  <Input
                    id="profile_logo"
                    value={profile.profile_logo || profile.profile_picture || ''}
                    onChange={(e) => {
                      updateField('profile_logo', e.target.value);
                      updateField('profile_picture', e.target.value);
                    }}
                    placeholder="https://example.com/your-logo.png"
                    className="mt-1"
                    data-testid="profile-logo-input"
                  />
                  {(profile.profile_logo || profile.profile_picture) && (
                    <div className="mt-3 flex items-center gap-4">
                      <img 
                        src={profile.profile_logo || profile.profile_picture} 
                        alt="Profile preview"
                        className="w-16 h-16 rounded-full object-cover border-2 border-gold/30"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                      <p className="text-xs text-muted-foreground">Preview of your profile logo</p>
                    </div>
                  )}
                </div>

                <div>
                  <Label htmlFor="status">Status Message</Label>
                  <Input
                    id="status"
                    value={profile.status_message}
                    onChange={(e) => updateField('status_message', e.target.value)}
                    placeholder="What's on your mind?"
                    maxLength={100}
                    className="mt-1"
                    data-testid="status-input"
                  />
                </div>

                <div>
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={profile.bio}
                    onChange={(e) => updateField('bio', e.target.value)}
                    placeholder="Tell others about yourself..."
                    maxLength={500}
                    rows={4}
                    className="mt-1"
                    data-testid="bio-input"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {profile.bio?.length || 0}/500 characters
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Account Tab - Username, Password, Legacy Names */}
          <TabsContent value="account" className="space-y-6">
            {/* Current Account Info */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <AtSign className="w-5 h-5" />
                Account Details
              </h3>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-obsidian/50 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Current Username</p>
                    <p className="font-medium text-lg">@{profile.username || localStorage.getItem('username')}</p>
                  </div>
                  <Badge variant="outline" className="border-gold/30 text-gold">
                    {profile.auth_method === 'google' ? 'Google Account' : 'Password Account'}
                  </Badge>
                </div>
                
                {/* Legacy Names (if any) */}
                {profile.legacy_usernames && profile.legacy_usernames.length > 0 && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <button 
                      onClick={() => setShowLegacyNames(!showLegacyNames)}
                      className="w-full flex items-center justify-between text-left"
                    >
                      <div className="flex items-center gap-2">
                        <History className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-medium text-amber-400">
                          Previous Usernames ({profile.legacy_usernames.length})
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {showLegacyNames ? 'Hide' : 'Show'}
                      </span>
                    </button>
                    {showLegacyNames && (
                      <div className="mt-3 space-y-2">
                        {profile.legacy_usernames.map((legacy, i) => (
                          <div key={i} className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">@{legacy.username || legacy}</span>
                            <span className="text-xs text-muted-foreground/60">
                              {legacy.changed_at ? new Date(legacy.changed_at).toLocaleDateString() : ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>

            {/* Change Username */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <AtSign className="w-5 h-5" />
                Change Username
              </h3>
              
              <div className="space-y-4">
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5" />
                    <p className="text-xs text-muted-foreground">
                      Your old username will be saved as a "legacy name" visible on your expanded profile.
                      Other players can see your username history.
                    </p>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="new_username">New Username</Label>
                  <Input
                    id="new_username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                    placeholder="Enter new username"
                    maxLength={30}
                    className="mt-1"
                    data-testid="new-username-input"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Lowercase letters, numbers, and underscores only
                  </p>
                </div>
                
                {profile.auth_method !== 'google' && (
                  <div>
                    <Label htmlFor="confirm_password">Confirm Current Password</Label>
                    <Input
                      id="confirm_password"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Enter current password to confirm"
                      className="mt-1"
                    />
                  </div>
                )}
                
                <Button
                  onClick={async () => {
                    if (!newUsername || newUsername.length < 3) {
                      toast.error('Username must be at least 3 characters');
                      return;
                    }
                    setChangingUsername(true);
                    try {
                      await axios.post(`${API}/auth/username/change`, {
                        user_id: userId,
                        new_username: newUsername,
                        password: currentPassword || undefined
                      });
                      toast.success('Username changed successfully!');
                      localStorage.setItem('username', newUsername);
                      setNewUsername('');
                      setCurrentPassword('');
                      loadData(); // Refresh profile
                    } catch (error) {
                      toast.error(error.response?.data?.detail || 'Failed to change username');
                    }
                    setChangingUsername(false);
                  }}
                  disabled={changingUsername || !newUsername}
                  className="bg-slate-blue hover:bg-slate-blue-light"
                  data-testid="change-username-btn"
                >
                  {changingUsername ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <AtSign className="w-4 h-4 mr-2" />
                  )}
                  Change Username
                </Button>
              </div>
            </Card>

            {/* Change Password (only for password-based accounts) */}
            {profile.auth_method !== 'google' && (
              <Card className="p-6 bg-surface/50 border-border/30">
                <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                  <Key className="w-5 h-5" />
                  Change Password
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="current_pw">Current Password</Label>
                    <Input
                      id="current_pw"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Enter current password"
                      className="mt-1"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="new_pw">New Password</Label>
                    <Input
                      id="new_pw"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password (min 6 characters)"
                      className="mt-1"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="confirm_new_pw">Confirm New Password</Label>
                    <Input
                      id="confirm_new_pw"
                      type="password"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="mt-1"
                    />
                  </div>
                  
                  <Button
                    onClick={async () => {
                      if (newPassword.length < 6) {
                        toast.error('Password must be at least 6 characters');
                        return;
                      }
                      if (newPassword !== confirmNewPassword) {
                        toast.error('Passwords do not match');
                        return;
                      }
                      setChangingPassword(true);
                      try {
                        await axios.post(`${API}/auth/password/change`, {
                          user_id: userId,
                          current_password: currentPassword,
                          new_password: newPassword
                        });
                        toast.success('Password changed successfully!');
                        setCurrentPassword('');
                        setNewPassword('');
                        setConfirmNewPassword('');
                      } catch (error) {
                        toast.error(error.response?.data?.detail || 'Failed to change password');
                      }
                      setChangingPassword(false);
                    }}
                    disabled={changingPassword || !currentPassword || !newPassword}
                    className="bg-slate-blue hover:bg-slate-blue-light"
                    data-testid="change-password-btn"
                  >
                    {changingPassword ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Key className="w-4 h-4 mr-2" />
                    )}
                    Change Password
                  </Button>
                </div>
              </Card>
            )}
          </TabsContent>

          {/* Appearance Tab */}
          <TabsContent value="appearance" className="space-y-6">
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4">Character Model</h3>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {options?.model_presets && Object.entries(options.model_presets).map(([key, preset]) => (
                  <Card
                    key={key}
                    className={`p-4 cursor-pointer transition-all ${
                      profile.model_preset === key 
                        ? 'border-gold bg-gold/10' 
                        : 'border-border/30 hover:border-gold/50'
                    }`}
                    onClick={() => updateField('model_preset', key)}
                    data-testid={`model-${key}`}
                  >
                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-gradient-to-br from-gold/20 to-gold/5 flex items-center justify-center">
                        <User className="w-6 h-6 text-gold" />
                      </div>
                      <div className="font-medium text-sm capitalize">{key.replace(/_/g, ' ')}</div>
                      <div className="text-xs text-muted-foreground">{preset.base}</div>
                    </div>
                    {profile.model_preset === key && (
                      <Check className="absolute top-2 right-2 w-4 h-4 text-gold" />
                    )}
                  </Card>
                ))}
              </div>

              <h4 className="font-medium mb-3">Model Colors</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['skin_color', 'hair_color', 'eye_color', 'accent_color'].map(colorField => (
                  <div key={colorField}>
                    <Label className="text-sm capitalize">{colorField.replace(/_/g, ' ')}</Label>
                    <div className="flex gap-2 mt-1">
                      <input
                        type="color"
                        value={profile.model_colors?.[colorField] || '#FFFFFF'}
                        onChange={(e) => updateModelColor(colorField, e.target.value)}
                        className="w-10 h-10 rounded border border-border/30 cursor-pointer"
                      />
                      <Input
                        value={profile.model_colors?.[colorField] || ''}
                        onChange={(e) => updateModelColor(colorField, e.target.value)}
                        placeholder="#FFFFFF"
                        className="flex-1"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Crown className="w-5 h-5" />
                Title Display
              </h3>
              <Input
                value={profile.title_display || ''}
                onChange={(e) => updateField('title_display', e.target.value)}
                placeholder="e.g., Champion, Dragon Slayer"
              />
              <p className="text-xs text-muted-foreground mt-1">
                This title will be shown next to your name
              </p>
            </Card>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="space-y-6">
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Palette className="w-5 h-5" />
                Chat Color
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Choose a color for your chat messages
              </p>
              
              <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
                {options?.chat_colors && Object.entries(options.chat_colors).map(([name, hex]) => (
                  <div
                    key={name}
                    className={`p-3 rounded-lg cursor-pointer transition-all border-2 ${
                      profile.chat_color === name 
                        ? 'border-white scale-105' 
                        : 'border-transparent hover:border-white/30'
                    }`}
                    onClick={() => updateField('chat_color', name)}
                    data-testid={`chat-color-${name}`}
                  >
                    <div 
                      className="w-full h-8 rounded mb-2"
                      style={{ backgroundColor: hex }}
                    />
                    <div className="text-xs text-center capitalize">{name}</div>
                    {profile.chat_color === name && (
                      <Check className="w-4 h-4 mx-auto mt-1 text-gold" />
                    )}
                  </div>
                ))}
              </div>

              {/* Preview */}
              <div className="mt-6 p-4 bg-black/30 rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Preview:</p>
                <div className="flex items-center gap-2">
                  <span 
                    className="font-medium"
                    style={{ color: options?.chat_colors?.[profile.chat_color] || '#FFFFFF' }}
                  >
                    {profile.display_name || 'YourName'}
                  </span>
                  <span className="text-muted-foreground">:</span>
                  <span>Hello, world!</span>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Privacy Tab */}
          <TabsContent value="privacy" className="space-y-6">
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Privacy Settings
              </h3>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Show Online Status</Label>
                    <p className="text-sm text-muted-foreground">
                      Let others see when you're online
                    </p>
                  </div>
                  <Switch
                    checked={profile.show_online}
                    onCheckedChange={(checked) => updateField('show_online', checked)}
                    data-testid="show-online-switch"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Allow Whispers</Label>
                    <p className="text-sm text-muted-foreground">
                      Let other players send you direct messages
                    </p>
                  </div>
                  <Switch
                    checked={profile.allow_whispers}
                    onCheckedChange={(checked) => updateField('allow_whispers', checked)}
                    data-testid="allow-whispers-switch"
                  />
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ProfileSettings;
