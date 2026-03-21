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
  FileText, Calendar, Receipt, Shield, TrendingUp,
  Building2, UserCheck, ClipboardList
} from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

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

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    
    if (employeeId.includes('@')) {
      toast.error('Please enter your Employee ID (e.g., EMP001), not email address.');
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
    { icon: LayoutDashboard, title: 'Dashboard' },
    { icon: Users, title: 'HR' },
    { icon: Briefcase, title: 'Projects' },
    { icon: TrendingUp, title: 'Sales' },
    { icon: Calendar, title: 'Meetings' },
    { icon: Receipt, title: 'Expenses' },
    { icon: FileText, title: 'SOW' },
    { icon: BarChart3, title: 'Analytics' },
    { icon: Building2, title: 'Clients' },
    { icon: UserCheck, title: 'Attendance' },
    { icon: ClipboardList, title: 'Approvals' },
    { icon: Shield, title: 'Governance' },
  ];

  return (
    <div className="min-h-screen relative overflow-hidden" data-testid="main-login-page">
      {/* Animated Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-zinc-900 to-neutral-900" />
      
      {/* Decorative Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        {/* Large gradient orbs */}
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-orange-400/5 rounded-full blur-3xl" />
        
        {/* Grid pattern */}
        <div 
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '60px 60px'
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Feature Banner - Top */}
        <div className="w-full bg-black/40 backdrop-blur-xl border-b border-white/10 py-5 px-4">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-4">
              <h2 className="text-white text-lg font-semibold tracking-wide">NETRA Enterprise Platform</h2>
              <p className="text-zinc-400 text-xs mt-0.5">Complete Business Management Solution</p>
            </div>
            <div className="flex flex-wrap justify-center gap-6">
              {features.map((feature, idx) => (
                <div 
                  key={idx}
                  className="flex flex-col items-center gap-1.5 group cursor-default"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-orange-500/20 group-hover:border-orange-500/30 transition-all duration-300">
                    <feature.icon className="w-5 h-5 text-zinc-400 group-hover:text-orange-400 transition-colors" />
                  </div>
                  <span className="text-[10px] text-zinc-500 group-hover:text-zinc-300 font-medium transition-colors">
                    {feature.title}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content - Centered Login */}
        <div className="flex-1 flex items-center justify-center px-4 py-12">
          <div className="w-full max-w-md">
            {/* Logo Card */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center p-4 bg-white rounded-2xl shadow-2xl shadow-black/50 mb-6">
                <img src={LOGO_URL} alt="D&V Logo" className="h-12 w-auto" />
              </div>
              <h1 className="text-3xl font-bold text-white tracking-tight">
                Welcome back
              </h1>
              <p className="text-zinc-400 mt-2">
                Sign in with your Employee ID
              </p>
            </div>

            {/* Login Card */}
            <div className="bg-white/[0.08] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-2xl shadow-black/40">
              {/* Subtle inner glow */}
              <div className="absolute inset-0 rounded-3xl bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />
              
              <form onSubmit={handlePasswordLogin} className="space-y-5 relative">
                {/* Employee ID Field */}
                <div className="space-y-2">
                  <Label htmlFor="employeeId" className="text-sm font-medium text-zinc-300">
                    Employee ID
                  </Label>
                  <div className={`relative transition-all duration-300 ${focusedField === 'employeeId' ? 'scale-[1.02]' : ''}`}>
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">
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
                      className="pl-12 h-13 bg-black/40 border-white/10 rounded-xl text-white placeholder:text-zinc-600 focus:border-orange-500/50 focus:ring-orange-500/20 focus:bg-black/60 transition-all text-base"
                      required
                      data-testid="employee-id-input"
                    />
                  </div>
                  {employeeId.includes('@') && (
                    <p className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                      <span>⚠</span> Enter Employee ID, not email address.
                    </p>
                  )}
                </div>

                {/* Password Field */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password" className="text-sm font-medium text-zinc-300">
                      Password
                    </Label>
                    <button
                      type="button"
                      className="text-xs text-zinc-500 hover:text-orange-400 font-medium transition-colors"
                      onClick={() => toast.info('Please contact HR to reset your password')}
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className={`relative transition-all duration-300 ${focusedField === 'password' ? 'scale-[1.02]' : ''}`}>
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">
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
                      className="pl-12 pr-12 h-13 bg-black/40 border-white/10 rounded-xl text-white placeholder:text-zinc-600 focus:border-orange-500/50 focus:ring-orange-500/20 focus:bg-black/60 transition-all text-base"
                      required
                      data-testid="password-input"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
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
                    className="w-4 h-4 rounded border-zinc-600 bg-black/40 text-orange-500 focus:ring-orange-500/20 cursor-pointer"
                  />
                  <label htmlFor="rememberMe" className="text-sm text-zinc-400 cursor-pointer select-none">
                    Remember my Employee ID
                  </label>
                </div>

                {/* Sign In Button */}
                <Button
                  type="submit"
                  disabled={loading || !employeeId || !password}
                  className="w-full h-13 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-xl font-semibold text-base shadow-lg shadow-orange-500/25 hover:shadow-xl hover:shadow-orange-500/30 transition-all duration-300 group disabled:from-zinc-700 disabled:to-zinc-700 disabled:text-zinc-500 disabled:shadow-none"
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
            </div>

            {/* Footer */}
            <div className="mt-8 text-center">
              <div className="flex items-center justify-center gap-4 text-xs text-zinc-500">
                <span>© 2026 D&V Business Consulting</span>
                <span className="text-zinc-700">•</span>
                <div className="flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  <span>Secure Login</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
