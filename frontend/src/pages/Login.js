import React, { useState, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  IdCard, Lock, Eye, EyeOff, ArrowRight, 
  LayoutDashboard, Users, Briefcase, BarChart3, 
  Sparkles, Shield, Zap, Globe
} from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" className="flex-shrink-0">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

const FeatureCard = ({ icon: Icon, title, description, delay }) => (
  <div 
    className="group relative p-4 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/15 transition-all duration-500 hover:scale-[1.02] hover:shadow-lg"
    style={{ animationDelay: `${delay}ms` }}
  >
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center group-hover:bg-emerald-500/30 transition-colors">
        <Icon className="w-5 h-5 text-emerald-300" />
      </div>
      <div>
        <h3 className="text-white font-semibold text-sm">{title}</h3>
        <p className="text-white/60 text-xs mt-0.5">{description}</p>
      </div>
    </div>
  </div>
);

const Login = () => {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [focusedField, setFocusedField] = useState(null);
  const { login } = useContext(AuthContext);
  const location = useLocation();

  useEffect(() => {
    const savedEmployeeId = localStorage.getItem('netra_remembered_employee_id');
    if (savedEmployeeId) {
      setEmployeeId(savedEmployeeId);
      setRememberMe(true);
    }
  }, []);

  useEffect(() => {
    if (location.state?.error) {
      toast.error(location.state.error);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + '/';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    
    // LOGIN GOVERNANCE: Validate Employee ID format
    if (employeeId.includes('@')) {
      toast.error('Please enter your Employee ID (e.g., EMP001), not email address. For email login, use Google Sign-In below.');
      return;
    }
    
    setLoading(true);
    try {
      const loginPayload = { employee_id: employeeId.toUpperCase(), password };
      const response = await axios.post(`${API}/auth/login`, loginPayload);
      
      if (rememberMe) {
        localStorage.setItem('netra_remembered_employee_id', employeeId.toUpperCase());
      } else {
        localStorage.removeItem('netra_remembered_employee_id');
      }
      
      login(response.data.access_token, response.data.user);
      
      if (response.data.requires_password_change) {
        toast.info('Please change your password on first login');
      } else {
        toast.success('Welcome back!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: LayoutDashboard, title: 'Unified Dashboard', description: 'Complete business overview at a glance' },
    { icon: Users, title: 'HR Management', description: 'Employee lifecycle & attendance' },
    { icon: Briefcase, title: 'Project Control', description: 'End-to-end project delivery' },
    { icon: BarChart3, title: 'Analytics', description: 'Data-driven business insights' },
  ];

  return (
    <div className="min-h-screen flex bg-zinc-50" data-testid="main-login-page">
      {/* Left Panel - Login Form (40%) */}
      <div className="w-full lg:w-[45%] flex flex-col justify-center px-8 sm:px-12 lg:px-16 py-12 relative">
        {/* Subtle background pattern */}
        <div className="absolute inset-0 opacity-[0.02]" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23059669' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }} />
        
        <div className="relative max-w-md mx-auto w-full">
          {/* Logo & Branding */}
          <div className="mb-10">
            <div className="flex items-center gap-3 mb-6">
              <img src={LOGO_URL} alt="D&V Logo" className="h-12 w-auto" />
            </div>
            <h1 className="text-3xl font-bold text-zinc-900 tracking-tight">
              Welcome back
            </h1>
            <p className="text-zinc-500 mt-2">
              Sign in to access your NETRA dashboard
            </p>
          </div>

          {/* Login Form */}
          <form onSubmit={handlePasswordLogin} className="space-y-5">
            {/* Employee ID Field */}
            <div className="space-y-2">
              <Label htmlFor="employeeId" className="text-sm font-medium text-zinc-700">
                Employee ID
              </Label>
              <div className={`relative transition-all duration-300 ${focusedField === 'employeeId' ? 'scale-[1.01]' : ''}`}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400">
                  <IdCard className="w-5 h-5" />
                </div>
                <Input
                  id="employeeId"
                  type="text"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  onFocus={() => setFocusedField('employeeId')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="EMP001 or CON001"
                  className="pl-12 h-12 bg-white border-zinc-200 rounded-xl text-zinc-900 placeholder:text-zinc-400 focus:border-emerald-500 focus:ring-emerald-500/20 transition-all"
                  required
                  data-testid="employee-id-input"
                />
                {employeeId.includes('@') && (
                  <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                    <span>⚠</span> Enter Employee ID, not email. For email login, use Google Sign-In.
                  </p>
                )}
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium text-zinc-700">
                  Password
                </Label>
                <button
                  type="button"
                  className="text-xs text-emerald-600 hover:text-emerald-700 font-medium transition-colors"
                  onClick={() => toast.info('Please contact HR to reset your password')}
                >
                  Forgot password?
                </button>
              </div>
              <div className={`relative transition-all duration-300 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400">
                  <Lock className="w-5 h-5" />
                </div>
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="Enter your password"
                  className="pl-12 pr-12 h-12 bg-white border-zinc-200 rounded-xl text-zinc-900 placeholder:text-zinc-400 focus:border-emerald-500 focus:ring-emerald-500/20 transition-all"
                  required
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500/20 cursor-pointer"
              />
              <label htmlFor="rememberMe" className="text-sm text-zinc-600 cursor-pointer select-none">
                Remember my Employee ID
              </label>
            </div>

            {/* Sign In Button */}
            <Button
              type="submit"
              disabled={loading || !employeeId || !password}
              className="w-full h-12 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl font-medium text-base shadow-lg shadow-zinc-900/10 hover:shadow-xl hover:shadow-zinc-900/20 transition-all duration-300 group"
              data-testid="sign-in-button"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </div>
              ) : (
                <div className="flex items-center justify-center gap-2">
                  Sign In
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 text-sm text-zinc-400 bg-zinc-50">or continue with</span>
            </div>
          </div>

          {/* Google Login */}
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            className="w-full h-12 bg-white hover:bg-zinc-50 border-zinc-200 rounded-xl font-medium text-zinc-700 hover:text-zinc-900 transition-all flex items-center justify-center gap-2"
            data-testid="google-login-button"
          >
            <GoogleIcon />
            Sign in with Google
          </Button>

          {/* Help Text */}
          <p className="text-center text-xs text-zinc-400 mt-6">
            Google login available for <span className="text-zinc-600">@dvconsulting.co.in</span> accounts
          </p>

          {/* Footer */}
          <div className="mt-12 pt-6 border-t border-zinc-200">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>© 2026 D&V Business Consulting</span>
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                <span>Secure Login</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Feature Showcase (55%) */}
      <div className="hidden lg:flex lg:w-[55%] relative overflow-hidden">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600 via-emerald-700 to-teal-800" />
        
        {/* Animated Gradient Orbs */}
        <div className="absolute top-20 right-20 w-96 h-96 bg-emerald-400/30 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 left-20 w-80 h-80 bg-teal-400/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-white/5 rounded-full blur-3xl" />
        
        {/* Grid Pattern Overlay */}
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }} />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 py-12 w-full">
          {/* Header Badge */}
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full px-4 py-2 mb-8 w-fit">
            <Sparkles className="w-4 h-4 text-emerald-300" />
            <span className="text-sm text-white/90 font-medium">Enterprise Business Platform</span>
          </div>

          {/* Main Heading */}
          <h2 className="text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
            Your Complete
            <br />
            <span className="text-emerald-300">Enterprise Solution</span>
          </h2>
          
          <p className="text-lg text-white/70 mb-10 max-w-md">
            Manage sales, HR, projects, and operations from a single powerful platform designed for modern businesses.
          </p>

          {/* Feature Cards */}
          <div className="grid grid-cols-2 gap-4 max-w-lg">
            {features.map((feature, idx) => (
              <FeatureCard key={idx} {...feature} delay={idx * 100} />
            ))}
          </div>

          {/* Stats Row */}
          <div className="flex items-center gap-8 mt-12 pt-8 border-t border-white/10">
            <div>
              <p className="text-3xl font-bold text-white">500+</p>
              <p className="text-sm text-white/60">Employees Managed</p>
            </div>
            <div className="w-px h-12 bg-white/20" />
            <div>
              <p className="text-3xl font-bold text-white">100+</p>
              <p className="text-sm text-white/60">Active Projects</p>
            </div>
            <div className="w-px h-12 bg-white/20" />
            <div>
              <p className="text-3xl font-bold text-white">99.9%</p>
              <p className="text-sm text-white/60">Uptime</p>
            </div>
          </div>

          {/* Trust Badges */}
          <div className="flex items-center gap-6 mt-8">
            <div className="flex items-center gap-2 text-white/60 text-sm">
              <Shield className="w-4 h-4 text-emerald-300" />
              <span>SOC 2 Compliant</span>
            </div>
            <div className="flex items-center gap-2 text-white/60 text-sm">
              <Zap className="w-4 h-4 text-emerald-300" />
              <span>Real-time Sync</span>
            </div>
            <div className="flex items-center gap-2 text-white/60 text-sm">
              <Globe className="w-4 h-4 text-emerald-300" />
              <span>Cloud Native</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
