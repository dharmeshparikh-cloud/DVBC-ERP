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
    
    // LOGIN GOVERNANCE: Validate Employee ID format
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
    { icon: LayoutDashboard, title: 'Business Dashboard', desc: 'Real-time business overview' },
    { icon: Users, title: 'HR Management', desc: 'Employee lifecycle & payroll' },
    { icon: Briefcase, title: 'Project Delivery', desc: 'End-to-end project control' },
    { icon: TrendingUp, title: 'Sales Pipeline', desc: 'Lead to closure tracking' },
    { icon: Calendar, title: 'Meeting Management', desc: 'Schedule & MOM tracking' },
    { icon: Receipt, title: 'Expense Claims', desc: 'Automated reimbursements' },
    { icon: FileText, title: 'SOW & Agreements', desc: 'Contract management' },
    { icon: BarChart3, title: 'Analytics', desc: 'Data-driven insights' },
    { icon: Building2, title: 'Client Management', desc: 'CRM & relationships' },
    { icon: UserCheck, title: 'Attendance', desc: 'Time & leave tracking' },
    { icon: ClipboardList, title: 'Approvals', desc: 'Multi-level workflows' },
    { icon: Shield, title: 'Governance', desc: 'Audit & compliance' },
  ];

  return (
    <div className="min-h-screen bg-black flex flex-col" data-testid="main-login-page">
      {/* Feature Banner - Top */}
      <div className="w-full bg-zinc-950 border-b border-zinc-800 py-6 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-6">
            <h2 className="text-white text-xl font-semibold mb-1">NETRA Enterprise Platform</h2>
            <p className="text-zinc-500 text-sm">Complete Business Management Solution</p>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-3">
            {features.map((feature, idx) => (
              <div 
                key={idx}
                className="flex flex-col items-center text-center p-2 rounded-lg hover:bg-zinc-900 transition-colors group"
              >
                <feature.icon className="w-5 h-5 text-zinc-500 group-hover:text-white transition-colors mb-1" />
                <span className="text-[10px] text-zinc-400 group-hover:text-zinc-300 font-medium leading-tight">
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
          <div className="text-center mb-8">
            <div className="flex justify-center mb-6">
              <img src={LOGO_URL} alt="D&V Logo" className="h-14 w-auto" />
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Welcome back
            </h1>
            <p className="text-zinc-500 mt-2">
              Sign in with your Employee ID
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
            <form onSubmit={handlePasswordLogin} className="space-y-5">
              {/* Employee ID Field */}
              <div className="space-y-2">
                <Label htmlFor="employeeId" className="text-sm font-medium text-zinc-300">
                  Employee ID
                </Label>
                <div className={`relative transition-all duration-300 ${focusedField === 'employeeId' ? 'scale-[1.01]' : ''}`}>
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
                    className="pl-12 h-12 bg-zinc-950 border-zinc-700 rounded-xl text-white placeholder:text-zinc-600 focus:border-zinc-500 focus:ring-zinc-500/20 transition-all"
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
                  <Label htmlFor="password" className="text-sm font-medium text-zinc-300">
                    Password
                  </Label>
                  <button
                    type="button"
                    className="text-xs text-zinc-500 hover:text-zinc-300 font-medium transition-colors"
                    onClick={() => toast.info('Please contact HR to reset your password')}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className={`relative transition-all duration-300 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
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
                    className="pl-12 pr-12 h-12 bg-zinc-950 border-zinc-700 rounded-xl text-white placeholder:text-zinc-600 focus:border-zinc-500 focus:ring-zinc-500/20 transition-all"
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
                  className="w-4 h-4 rounded border-zinc-600 bg-zinc-950 text-white focus:ring-zinc-500/20 cursor-pointer"
                />
                <label htmlFor="rememberMe" className="text-sm text-zinc-400 cursor-pointer select-none">
                  Remember my Employee ID
                </label>
              </div>

              {/* Sign In Button */}
              <Button
                type="submit"
                disabled={loading || !employeeId || !password}
                className="w-full h-12 bg-white hover:bg-zinc-200 text-black rounded-xl font-semibold text-base transition-all duration-300 group disabled:bg-zinc-700 disabled:text-zinc-500"
                data-testid="sign-in-button"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-zinc-400 border-t-black rounded-full animate-spin" />
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
            <div className="flex items-center justify-center gap-4 text-xs text-zinc-600">
              <span>© 2026 D&V Business Consulting</span>
              <span>•</span>
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
