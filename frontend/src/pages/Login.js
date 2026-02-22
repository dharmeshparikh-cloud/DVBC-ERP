import React, { useState, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { IdCard, Lock, LayoutDashboard, Users, Briefcase, BarChart3, Shield, Eye, EyeOff } from 'lucide-react';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" className="mr-2 flex-shrink-0">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

const Login = () => {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
      // Determine if input is an email or employee ID
      const isEmail = employeeId.includes('@');
      const loginPayload = isEmail 
        ? { email: employeeId, password }
        : { employee_id: employeeId.toUpperCase(), password };
      
      const response = await axios.post(`${API}/auth/login`, loginPayload);
      login(response.data.access_token, response.data.user);
      
      // Check if first login (password is default)
      if (response.data.requires_password_change) {
        toast.info('Please change your password on first login');
      } else {
        toast.success('Login successful');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: LayoutDashboard, label: 'Unified Dashboard', desc: 'Complete business overview' },
    { icon: Users, label: 'HR Management', desc: 'Employee & attendance tracking' },
    { icon: Briefcase, label: 'Project Control', desc: 'End-to-end project lifecycle' },
    { icon: BarChart3, label: 'Analytics & Reports', desc: 'Data-driven insights' },
  ];

  return (
    <div className="min-h-screen flex bg-white" data-testid="main-login-page">
      {/* Left Panel - Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-black p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center border border-white/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">DVBC - NETRA</h1>
              <p className="text-white/60 text-sm">Business Management Platform</p>
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Your complete<br />enterprise solution
            </h2>
            <p className="text-white/60 text-lg max-w-md">
              Manage sales, HR, projects, and operations - all from a single powerful platform designed for modern businesses.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-12">
            {features.map((feature, idx) => (
              <div key={idx} className="bg-white/5 rounded-xl p-4 border border-white/10 hover:bg-white/10 transition-colors">
                <feature.icon className="w-8 h-8 text-white/80 mb-3" />
                <h3 className="text-white font-semibold text-sm">{feature.label}</h3>
                <p className="text-white/50 text-xs mt-1">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="text-white/40 text-sm">
          © {new Date().getFullYear()} DVBC Consulting. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <Card className="w-full max-w-[440px] border border-black/10 shadow-lg rounded-2xl overflow-hidden" data-testid="login-card">
          {/* Header with Logo */}
          <div className="bg-white px-8 pt-10 pb-6 text-center border-b border-black/5">
            <img
              src={LOGO_URL}
              alt="DVBC Logo"
              className="h-16 w-auto mx-auto mb-4"
              data-testid="login-logo"
            />
            <h1 className="text-xl font-bold tracking-wide text-black" data-testid="app-name">
              DVBC - NETRA
            </h1>
            <p className="text-xs text-black/40 mt-1 tracking-widest uppercase">Business Management Platform</p>
          </div>

          <CardContent className="px-8 py-8 space-y-5 bg-white">
            {/* Employee ID/Password Login */}
            <form onSubmit={handlePasswordLogin} className="space-y-4" data-testid="password-login-form">
              <div className="space-y-2">
                <Label htmlFor="employeeId" className="text-sm font-medium text-black">Employee ID or Email</Label>
                <div className="relative">
                  <IdCard className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                  <Input
                    id="employeeId"
                    data-testid="employee-id-input"
                    type="text"
                    placeholder="EMP001 or email@domain.com"
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    required
                    className="pl-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-black">Password</Label>
                  <button
                    type="button"
                    data-testid="forgot-password-link"
                    onClick={() => toast.info('Please contact your HR administrator for password reset.')}
                    className="text-xs text-black/50 hover:text-black transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                  <Input
                    id="password"
                    data-testid="password-input"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pl-11 pr-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black/40 hover:text-black transition-colors"
                    data-testid="toggle-password-visibility"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                data-testid="submit-button"
                className="w-full bg-black text-white hover:bg-black/90 rounded-lg h-11 font-medium shadow-sm"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-black/10" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-white px-3 text-black/40">or continue with</span>
              </div>
            </div>

            {/* Google Sign-In */}
            <Button
              type="button"
              data-testid="google-login-btn"
              onClick={handleGoogleLogin}
              variant="outline"
              className="w-full border-black/20 text-black hover:bg-black/5 rounded-lg h-11 font-medium"
            >
              <GoogleIcon />
              Sign in with Google
            </Button>

            <p className="text-center text-[11px] text-black/40 leading-relaxed">
              Google login available for <span className="font-medium text-black/60">@dvconsulting.co.in</span> accounts.
              <br />First time login? Use Employee ID with default password provided by HR.
            </p>
          </CardContent>
        </Card>
      </div>

    </div>
  );
};

export default Login;
