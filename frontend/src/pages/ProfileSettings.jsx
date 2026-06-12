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
  Key, History, AlertCircle, Link, Unlink, Lock
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import PixelAvatar from '@/components/PixelAvatar';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Social login icons
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

const ProfileSettings = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [options, setOptions] = useState(null);
  const [profile, setProfile] = useState({
    display_name: '',
    username: '',
    email: '',
    bio: '',
    chat_color: 'default',
    pixel_avatar_url: null,
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
    auth_method: 'password',
    linked_accounts: {
      google: null,
      apple: null,
      facebook: null,
      x: null
    }
  });
  
  // Account settings state
  const [newUsername, setNewUsername] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [changingUsername, setChangingUsername] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [showLegacyNames, setShowLegacyNames] = useState(false);
  const [linkingAccount, setLinkingAccount] = useState(null);
  const [ownedCosmetics, setOwnedCosmetics] = useState([]);
  const [avatarFrame, setAvatarFrame] = useState(null);

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
      try {
        const cosRes = await axios.get(`${API}/cosmetics/owned/${userId}`);
        setOwnedCosmetics(cosRes.data.owned || []);
        setAvatarFrame(cosRes.data.equipped?.frame || null);
      } catch (e) { /* cosmetics optional */ }
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
                
                {/* Pixel Avatar */}
                <div>
                  <Label className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Pixel Avatar
                  </Label>
                  <div className="mt-2 flex items-center gap-4 p-3 bg-obsidian/50 rounded-lg border border-border/30">
                    <PixelAvatar dataUrl={profile.pixel_avatar_url} frame={avatarFrame} size={64} testId="settings-pixel-avatar" />
                    <div className="flex-1">
                      <p className="text-sm">
                        {profile.pixel_avatar_url ? 'Your designed 64×64 logo avatar' : 'No avatar yet — design your unique 64×64 pixel logo'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">Profile pictures have been replaced by designable pixel avatars.</p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => navigate('/avatar-studio')}
                      className="border-gold/30 text-gold hover:bg-gold/10 shrink-0"
                      data-testid="open-avatar-studio-btn"
                    >
                      <Sparkles className="w-4 h-4 mr-2" />
                      {profile.pixel_avatar_url ? 'Edit in Studio' : 'Design Avatar'}
                    </Button>
                  </div>
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

            {/* Linked Login Methods */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Link className="w-5 h-5" />
                Linked Login Methods
              </h3>
              
              <p className="text-sm text-muted-foreground mb-4">
                Connect additional login methods to your account for easier access.
              </p>
              
              <div className="space-y-3">
                {/* Google */}
                <div className="flex items-center justify-between p-4 bg-obsidian/50 rounded-lg border border-border/30">
                  <div className="flex items-center gap-3">
                    <GoogleIcon />
                    <div>
                      <p className="font-medium">Google</p>
                      <p className="text-xs text-muted-foreground">
                        {profile.linked_accounts?.google || profile.auth_method === 'google' 
                          ? profile.email || 'Connected' 
                          : 'Not connected'}
                      </p>
                    </div>
                  </div>
                  {profile.linked_accounts?.google || profile.auth_method === 'google' ? (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                      <Check className="w-3 h-3 mr-1" />
                      Linked
                    </Badge>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const redirectUrl = window.location.origin + '/settings';
                        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}&link_account=${userId}`;
                      }}
                      className="border-border/50"
                      data-testid="link-google-btn"
                    >
                      <Link className="w-4 h-4 mr-1" />
                      Link
                    </Button>
                  )}
                </div>
                
                {/* Apple - Coming Soon */}
                <div className="flex items-center justify-between p-4 bg-obsidian/50 rounded-lg border border-border/30 opacity-60">
                  <div className="flex items-center gap-3">
                    <AppleIcon />
                    <div>
                      <p className="font-medium">Apple</p>
                      <p className="text-xs text-muted-foreground">Not connected</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-slate-blue">Coming Soon</Badge>
                </div>
                
                {/* Facebook - Coming Soon */}
                <div className="flex items-center justify-between p-4 bg-obsidian/50 rounded-lg border border-border/30 opacity-60">
                  <div className="flex items-center gap-3">
                    <FacebookIcon />
                    <div>
                      <p className="font-medium">Facebook</p>
                      <p className="text-xs text-muted-foreground">Not connected</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-slate-blue">Coming Soon</Badge>
                </div>
                
                {/* X (Twitter) - Coming Soon */}
                <div className="flex items-center justify-between p-4 bg-obsidian/50 rounded-lg border border-border/30 opacity-60">
                  <div className="flex items-center gap-3">
                    <XIcon />
                    <div>
                      <p className="font-medium">X (Twitter)</p>
                      <p className="text-xs text-muted-foreground">Not connected</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-slate-blue">Coming Soon</Badge>
                </div>
              </div>
              
              {/* Set Primary Login Method */}
              {(profile.auth_method === 'google' || profile.linked_accounts?.google) && (
                <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-sm text-blue-400 flex items-center gap-2">
                    <Lock className="w-4 h-4" />
                    Primary login: <span className="font-medium capitalize">{profile.auth_method}</span>
                  </p>
                </div>
              )}
            </Card>
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

              {/* Premium colors from the VE$ Boutique */}
              {options?.premium_chat_colors && (
                <div className="mt-6">
                  <p className="text-sm text-gold mb-3 flex items-center gap-2">
                    <Crown className="w-4 h-4" /> Premium Colors (VE$ Boutique)
                  </p>
                  <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
                    {Object.entries(options.premium_chat_colors).map(([name, hex]) => {
                      const owned = ownedCosmetics.includes(`color_${name}`);
                      return (
                        <div
                          key={name}
                          className={`relative p-3 rounded-lg transition-all border-2 ${
                            profile.chat_color === name
                              ? 'border-white scale-105'
                              : 'border-transparent hover:border-white/30'
                          } ${owned ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}
                          onClick={() => {
                            if (owned) updateField('chat_color', name);
                            else { toast.info('Unlock this color in the VE$ Boutique'); navigate('/boutique'); }
                          }}
                          data-testid={`premium-color-${name}`}
                        >
                          <div className="w-full h-8 rounded mb-2" style={{ backgroundColor: hex }} />
                          <div className="text-xs text-center capitalize">{name.replace(/_/g, ' ')}</div>
                          {!owned && <Lock className="absolute top-2 right-2 w-3.5 h-3.5 text-white/70" />}
                          {profile.chat_color === name && (
                            <Check className="w-4 h-4 mx-auto mt-1 text-gold" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Preview */}
              <div className="mt-6 p-4 bg-black/30 rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Preview:</p>
                <div className="flex items-center gap-2">
                  <span 
                    className="font-medium"
                    style={{ color: options?.chat_colors?.[profile.chat_color] || options?.premium_chat_colors?.[profile.chat_color] || '#FFFFFF' }}
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
