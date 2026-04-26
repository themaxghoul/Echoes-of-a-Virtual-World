import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * AuthCallback Component
 * Handles OAuth callback from Emergent Auth (Google login)
 * Processes session_id from URL fragment and establishes user session
 * 
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
const AuthCallback = () => {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processOAuthCallback = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.substring(1)); // Remove the #
        const sessionId = params.get('session_id');

        if (!sessionId) {
          console.error('No session_id found in callback');
          navigate('/auth');
          return;
        }

        // Exchange session_id for user data via backend
        const response = await axios.post(`${API}/auth/google/callback`, {
          session_id: sessionId
        }, {
          withCredentials: true // Important for cookie handling
        });

        if (response.data && response.data.user) {
          const user = response.data.user;
          
          // Store user data in localStorage
          localStorage.setItem('userId', user.user_id || user.id);
          localStorage.setItem('username', user.username);
          localStorage.setItem('displayName', user.display_name || user.name);
          localStorage.setItem('isTranscendent', user.is_transcendent ? 'true' : 'false');
          localStorage.setItem('permissionLevel', user.permission_level || 'basic');
          localStorage.setItem('authMethod', 'google');
          
          if (user.picture) {
            localStorage.setItem('profilePicture', user.picture);
          }

          // Clear the hash from URL
          window.history.replaceState(null, '', window.location.pathname);

          // Check if user has characters
          try {
            const charsRes = await axios.get(`${API}/characters/${user.user_id || user.id}`);
            
            if (charsRes.data && charsRes.data.length > 0) {
              const mainChar = charsRes.data[0];
              localStorage.setItem('currentCharacterId', mainChar.id);
              localStorage.setItem('characterName', mainChar.name);
              navigate('/select-mode', { state: { user } });
            } else {
              navigate('/create-character', { state: { user } });
            }
          } catch (charError) {
            // No characters, go to creation
            navigate('/create-character', { state: { user } });
          }
        } else {
          throw new Error('Invalid response from server');
        }
      } catch (error) {
        console.error('OAuth callback error:', error);
        navigate('/auth', { 
          state: { error: 'Authentication failed. Please try again.' } 
        });
      }
    };

    processOAuthCallback();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-obsidian flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-gold animate-spin mx-auto mb-4" />
        <p className="font-cinzel text-lg text-gold">Authenticating...</p>
        <p className="text-sm text-muted-foreground mt-2">Please wait while we verify your account</p>
      </div>
    </div>
  );
};

export default AuthCallback;
