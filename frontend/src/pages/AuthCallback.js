import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

const AuthCallback = ({ onLogin }) => {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = window.location.hash;
      const sessionId = new URLSearchParams(hash.substring(1)).get('session_id');

      if (!sessionId) {
        navigate('/login', { replace: true });
        return;
      }

      try {
        const response = await axios.post(`${API}/auth/google`, { session_id: sessionId });
        const { access_token, user } = response.data;
        onLogin(access_token, user);
        // Clear hash and redirect
        window.history.replaceState(null, '', '/');
        navigate('/', { replace: true });
      } catch (error) {
        const detail = error.response?.data?.detail || 'Google authentication failed';
        navigate('/login', { replace: true, state: { error: detail } });
      }
    };

    processAuth();
  }, [navigate, onLogin]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-white">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 rounded-full animate-spin mx-auto" />
        <p className="text-sm text-zinc-500">Authenticating with Google...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
