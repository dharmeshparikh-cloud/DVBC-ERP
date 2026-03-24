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
  Receipt, Shield, Zap, Clock, FileCheck, 
  Bell, GitBranch, Layers, UserCircle
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
    { 
      icon: LayoutDashboard, 
      title: 'Unified Dashboard', 
      desc: 'Complete business overview at a glance'
    },
    { 
      icon: Users, 
      title: 'HR Management', 
      desc: 'Employee lifecycle, payroll & attendance'
    },
    { 
      icon: Briefcase, 
      title: 'Project Control', 
      desc: 'End-to-end project delivery tracking'
    },
    { 
      icon: BarChart3, 
      title: 'Sales Pipeline', 
      desc: 'Lead to closure with full visibility'
    },
    { 
      icon: Receipt, 
      title: 'Expense & Claims', 
      desc: 'Automated approvals & reimbursements'
    },
    { 
      icon: FileCheck, 
      title: 'SOW & Contracts', 
      desc: 'Digital agreement management'
    },
  ];

  const highlights = [
    { icon: Shield, text: 'Enterprise Security' },
    { icon: Zap, text: 'Real-time Sync' },
    { icon: Clock, text: '24/7 Availability' },
    { icon: Bell, text: 'Smart Notifications' },
    { icon: GitBranch, text: 'Workflow Automation' },
    { icon: Layers, text: 'Multi-level Approvals' },
  ];

  const DEMO_ACCOUNTS = [
    { id: 'EMP001', password: 'admin123', role: 'Admin', color: 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100' },
    { id: 'EMP002', password: 'hr123', role: 'HR Manager', color: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100' },
    { id: 'EMP003', password: 'sales123', role: 'Sales Executive', color: 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100' },
    { id: 'EMP004', password: 'consultant123', role: 'Consultant', color: 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100' },
    { id: 'EMP005', password: 'employee123', role: 'Employee', color: 'bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100' },
  ];

  const handleQuickLogin = (account) => {
    setEmployeeId(account.id);
    setPassword(account.password);
  };

  return (
    <div className="min-h-screen flex" data-testid="main-login-page">
      {/* Left Side - Features */}
      <div className="hidden lg:flex lg:w-[55%] bg-neutral-950 flex-col justify-between p-12 relative overflow-hidden">
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-neutral-900 via-neutral-950 to-black opacity-80" />
        
        {/* Content */}
        <div className="relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-2 mb-8">
            <Zap className="w-4 h-4 text-amber-500" />
            <span className="text-amber-500 text-sm font-medium">Enterprise Business Platform</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl lg:text-5xl font-bold text-white leading-tight mb-4">
            No Guesswork. <span className="text-amber-500">Just Systems.</span>
          </h1>
          
          <p className="text-neutral-300 text-base lg:text-lg mb-12 whitespace-nowrap">
            SOP-Based Workflows<span className="mx-2 text-amber-500/60">|</span>Real-Time Visibility<span className="mx-2 text-amber-500/60">|</span>Full Control<span className="mx-2 text-amber-500/60">|</span>Zero Chaos
          </p>

          {/* Feature Grid - 6 boxes */}
          <div className="grid grid-cols-2 gap-4 mb-12">
            {(features || []).map((feature, idx) => (
              <div 
                key={idx}
                className="bg-neutral-900/80 border border-neutral-800 rounded-xl p-5 hover:border-amber-500/30 hover:bg-neutral-900 transition-all duration-300 group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-amber-500/20 transition-colors">
                    <feature.icon className="w-5 h-5 text-amber-500" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold mb-1">{feature.title}</h3>
                    <p className="text-neutral-500 text-sm leading-relaxed">{feature.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom highlights */}
        <div className="relative z-10">
          <div className="flex flex-wrap gap-4">
            {(highlights || []).map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 text-neutral-500">
                <item.icon className="w-4 h-4 text-amber-500/70" />
                <span className="text-sm">{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-[45%] bg-white flex flex-col justify-center px-8 lg:px-16 py-12">
        <div className="max-w-md mx-auto w-full">
          {/* Logo */}
          <div className="mb-10">
            <img src={LOGO_URL} alt="D&V Logo" className="h-12 w-auto" />
          </div>

          {/* Welcome Text */}
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-neutral-900 mb-2">Welcome back</h2>
            <p className="text-neutral-500">Sign in to access your NETRA dashboard</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handlePasswordLogin} className="space-y-6">
            {/* Employee ID Field */}
            <div className="space-y-2">
              <Label htmlFor="employeeId" className="text-sm font-medium text-neutral-700">
                Employee ID
              </Label>
              <div className={`relative transition-all duration-200 ${focusedField === 'employeeId' ? 'scale-[1.01]' : ''}`}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400">
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
                  className="pl-12 h-12 bg-neutral-50 border-neutral-200 rounded-xl text-neutral-900 placeholder:text-neutral-400 focus:border-amber-500 focus:ring-amber-500/20 transition-all"
                  required
                  data-testid="employee-id-input"
                />
              </div>
              {employeeId.includes('@') && (
                <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                  <span>⚠</span> Enter Employee ID, not email address.
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium text-neutral-700">
                  Password
                </Label>
                <button
                  type="button"
                  className="text-sm text-amber-600 hover:text-amber-700 font-medium transition-colors"
                  onClick={() => toast.info('Please contact HR to reset your password')}
                >
                  Forgot password?
                </button>
              </div>
              <div className={`relative transition-all duration-200 ${focusedField === 'password' ? 'scale-[1.01]' : ''}`}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400">
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
                  className="pl-12 pr-12 h-12 bg-neutral-50 border-neutral-200 rounded-xl text-neutral-900 placeholder:text-neutral-400 focus:border-amber-500 focus:ring-amber-500/20 transition-all"
                  required
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors"
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
                className="w-4 h-4 rounded border-neutral-300 bg-white text-amber-500 focus:ring-amber-500/20 cursor-pointer"
              />
              <label htmlFor="rememberMe" className="text-sm text-neutral-600 cursor-pointer select-none">
                Remember my Employee ID
              </label>
            </div>

            {/* Sign In Button */}
            <Button
              type="submit"
              disabled={loading || !employeeId || !password}
              className="w-full h-12 bg-neutral-900 hover:bg-neutral-800 text-white rounded-xl font-semibold text-base transition-all duration-200 group disabled:bg-neutral-300 disabled:text-neutral-500"
              data-testid="sign-in-button"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-neutral-400 border-t-white rounded-full animate-spin" />
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

          {/* Quick Login - Demo Accounts */}
          <div className="mt-6" data-testid="quick-login-section">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-px flex-1 bg-neutral-200" />
              <span className="text-xs text-neutral-400 font-medium uppercase tracking-wider">Quick Access</span>
              <div className="h-px flex-1 bg-neutral-200" />
            </div>
            <div className="flex flex-wrap gap-2">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.id}
                  type="button"
                  onClick={() => handleQuickLogin(account)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all duration-200 ${account.color}`}
                  data-testid={`quick-login-${account.id.toLowerCase()}`}
                >
                  <UserCircle className="w-3.5 h-3.5" />
                  {account.role}
                  <span className="opacity-60">({account.id})</span>
                </button>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-12 pt-8 border-t border-neutral-200">
            <div className="flex items-center justify-between text-xs text-neutral-400">
              <span>© 2026 D&V Business Consulting</span>
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                <span>Secure Login</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Feature Banner - shown only on small screens */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-neutral-900 border-t border-neutral-800 p-4">
        <div className="flex items-center justify-center gap-6 text-xs">
          <div className="flex items-center gap-1.5 text-neutral-400">
            <Shield className="w-3.5 h-3.5 text-amber-500" />
            <span>Enterprise Security</span>
          </div>
          <div className="flex items-center gap-1.5 text-neutral-400">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>Real-time Sync</span>
          </div>
          <div className="flex items-center gap-1.5 text-neutral-400">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span>24/7 Available</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
