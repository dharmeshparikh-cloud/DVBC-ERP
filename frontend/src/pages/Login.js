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
    <div className="min-h-screen bg-neutral-950 flex flex-col" data-testid="main-login-page">
      {/* Feature Banner - Top */}
      <div className="w-full bg-neutral-900 border-b border-neutral-800 py-6 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-5">
            <h2 className="text-white text-xl font-semibold tracking-wide">NETRA Enterprise Platform</h2>
            <p className="text-neutral-500 text-sm mt-1">Complete Business Management Solution</p>
          </div>
          <div className="flex flex-wrap justify-center gap-5">
            {features.map((feature, idx) => (
              <div 
                key={idx}
                className="flex flex-col items-center gap-2 group cursor-default"
              >
                <div className="w-11 h-11 rounded-lg bg-neutral-800 border border-neutral-700 flex items-center justify-center group-hover:bg-amber-500/10 group-hover:border-amber-500/40 transition-all duration-200">
                  <feature.icon className="w-5 h-5 text-neutral-500 group-hover:text-amber-500 transition-colors" />
                </div>
                <span className="text-[11px] text-neutral-600 group-hover:text-neutral-400 font-medium transition-colors">
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
          {/* Logo & Branding */}
          <div className="text-center mb-10">
            <div className="inline-block p-5 bg-white rounded-2xl shadow-lg mb-6">
              <img src={LOGO_URL} alt="D&V Logo" className="h-12 w-auto" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Welcome back
            </h1>
            <p className="text-neutral-500 mt-2 text-base">
              Sign in with your Employee ID
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-8">
            <form onSubmit={handlePasswordLogin} className="space-y-6">
              {/* Employee ID Field */}
              <div className="space-y-2">
                <Label htmlFor="employeeId" className="text-sm font-medium text-neutral-300">
                  Employee ID
                </Label>
                <div className={`relative transition-all duration-200 ${focusedField === 'employeeId' ? 'scale-[1.01]' : ''}`}>
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600">
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
                    className="pl-12 h-12 bg-neutral-950 border-neutral-700 rounded-xl text-white placeholder:text-neutral-600 focus:border-amber-500 focus:ring-amber-500/20 transition-all"
                    required
                    data-testid="employee-id-input"
                  />
                </div>
                {employeeId.includes('@') && (
                  <p className="text-xs text-amber-500 mt-1 flex items-center gap-1">
                    <span>⚠</span> Enter Employee ID, not email address.
                  </p>
                )}
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-neutral-300">
                    Password
                  </Label>
                  <button
                    type="button"
                    className="text-xs text-neutral-500 hover:text-amber-500 font-medium transition-colors"
                    onClick={() => toast.info('Please contact HR to reset your password')}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className={`relative transition-all duration-200 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600">
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
                    className="pl-12 pr-12 h-12 bg-neutral-950 border-neutral-700 rounded-xl text-white placeholder:text-neutral-600 focus:border-amber-500 focus:ring-amber-500/20 transition-all"
                    required
                    data-testid="password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-600 hover:text-neutral-400 transition-colors"
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
                  className="w-4 h-4 rounded border-neutral-600 bg-neutral-950 text-amber-500 focus:ring-amber-500/20 cursor-pointer"
                />
                <label htmlFor="rememberMe" className="text-sm text-neutral-500 cursor-pointer select-none">
                  Remember my Employee ID
                </label>
              </div>

              {/* Sign In Button */}
              <Button
                type="submit"
                disabled={loading || !employeeId || !password}
                className="w-full h-12 bg-amber-500 hover:bg-amber-400 text-neutral-950 rounded-xl font-semibold text-base transition-all duration-200 group disabled:bg-neutral-800 disabled:text-neutral-600"
                data-testid="sign-in-button"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-neutral-700 border-t-neutral-950 rounded-full animate-spin" />
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
          <div className="mt-10 text-center">
            <div className="flex items-center justify-center gap-4 text-xs text-neutral-600">
              <span>© 2026 D&V Business Consulting</span>
              <span className="text-neutral-800">•</span>
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                <span>Secure Login</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
