import React, { useState, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" className="mr-2">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

const Login = () => {
  const [showPasswordLogin, setShowPasswordLogin] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);
  const location = useLocation();

  useEffect(() => {
    if (location.state?.error) {
      toast.error(location.state.error);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      login(response.data.access_token, response.data.user);
      toast.success('Login successful');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white grid-background p-6">
      <Card className="w-full max-w-md border-zinc-200 shadow-none rounded-sm" data-testid="login-card">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-semibold tracking-tight uppercase text-zinc-950">
            DVB Consulting
          </CardTitle>
          <CardDescription className="text-zinc-500">
            Business Management Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Google Sign-In - Primary */}
          <Button
            type="button"
            data-testid="google-login-btn"
            onClick={handleGoogleLogin}
            className="w-full bg-white text-zinc-700 border border-zinc-300 hover:bg-zinc-50 rounded-sm shadow-none h-11 font-medium"
          >
            <GoogleIcon />
            Sign in with Google
          </Button>

          <p className="text-center text-xs text-zinc-400">
            Use your <span className="font-medium text-zinc-600">@dvconsulting.co.in</span> Google Workspace account
          </p>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-zinc-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <button
                type="button"
                data-testid="toggle-admin-login"
                onClick={() => setShowPasswordLogin(!showPasswordLogin)}
                className="bg-white px-2 text-zinc-400 hover:text-zinc-600 transition-colors"
              >
                {showPasswordLogin ? 'Hide admin login' : 'Admin login'}
              </button>
            </div>
          </div>

          {/* Admin Password Login - Secondary/Fallback */}
          {showPasswordLogin && (
            <form onSubmit={handlePasswordLogin} className="space-y-3 pt-1" data-testid="admin-login-form">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-xs font-medium text-zinc-600">
                  Admin Email
                </Label>
                <Input
                  id="email"
                  data-testid="email-input"
                  type="email"
                  placeholder="admin@dvconsulting.co.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="rounded-sm border-zinc-200 bg-transparent focus:ring-1 focus:ring-zinc-950 h-9"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-xs font-medium text-zinc-600">
                    Password
                  </Label>
                  <button
                    type="button"
                    data-testid="forgot-password-link"
                    onClick={() => toast.info('Contact another admin or use OTP reset from the Security Audit panel.')}
                    className="text-xs text-zinc-400 hover:text-zinc-700 transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
                <Input
                  id="password"
                  data-testid="password-input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="rounded-sm border-zinc-200 bg-transparent focus:ring-1 focus:ring-zinc-950 h-9"
                />
              </div>

              <Button
                type="submit"
                data-testid="submit-button"
                className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none h-9"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
