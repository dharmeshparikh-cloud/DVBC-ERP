import React, { useState, useContext, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { Mail, Lock, TrendingUp, Users, FileText, DollarSign } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

// Sales-related roles that can access the Sales Portal
const SALES_ROLES = ['executive', 'account_manager', 'manager'];

const SalesLogin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // If already logged in with a sales role, redirect to sales dashboard
    if (user && SALES_ROLES.includes(user.role)) {
      navigate('/sales');
    } else if (user) {
      // Logged in but not a sales role - redirect to main app
      toast.error('Access denied. Sales Portal is for sales team only.');
      navigate('/');
    }
  }, [user, navigate]);

  useEffect(() => {
    if (location.state?.error) {
      toast.error(location.state.error);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const userData = response.data.user;
      
      // Check if user has a sales role
      if (!SALES_ROLES.includes(userData.role)) {
        toast.error('Access denied. Sales Portal is for sales team only.');
        setLoading(false);
        return;
      }
      
      login(response.data.access_token, userData);
      toast.success('Welcome to Sales Portal!');
      navigate('/sales');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Users, label: 'Lead Management', desc: 'Track and convert leads' },
    { icon: DollarSign, label: 'Pricing Plans', desc: 'Create custom pricing' },
    { icon: FileText, label: 'SOW Builder', desc: 'Generate statements of work' },
    { icon: TrendingUp, label: 'Sales Reports', desc: 'Track performance metrics' },
  ];

  return (
    <div className="min-h-screen flex bg-white">
      {/* Left Panel - Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-black p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center border border-white/20">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">DVBC Sales Portal</h1>
              <p className="text-white/60 text-sm">Streamlined Sales Management</p>
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Everything you need<br />to close more deals
            </h2>
            <p className="text-white/60 text-lg max-w-md">
              Access your complete sales toolkit - from lead capture to agreement signing, all in one place.
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
          © {new Date().getFullYear()} D&V Business Consulting. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <Card className="w-full max-w-[420px] border border-black/10 shadow-lg rounded-2xl overflow-hidden" data-testid="sales-login-card">
          {/* Header with Logo */}
          <div className="bg-white px-8 pt-10 pb-6 text-center border-b border-black/5">
            <img
              src={LOGO_URL}
              alt="DVBC Logo"
              className="h-14 w-auto mx-auto mb-4"
              data-testid="sales-login-logo"
            />
            <h1 className="text-xl font-bold text-black" data-testid="sales-app-name">
              Sales Portal
            </h1>
            <p className="text-xs text-black/40 mt-1">Sign in to access sales tools</p>
          </div>

          <CardContent className="px-8 py-8 space-y-5 bg-white">
            {/* Login Form */}
            <form onSubmit={handlePasswordLogin} className="space-y-4" data-testid="sales-login-form">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-black">Email Address</Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                  <Input
                    id="email"
                    data-testid="sales-email-input"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="pl-11 h-11 rounded-lg border-black/20 bg-white focus:ring-2 focus:ring-black focus:border-black"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-black">Password</Label>
                  <button
                    type="button"
                    data-testid="sales-forgot-password-link"
                    onClick={() => toast.info('Please contact your administrator for password reset.')}
                    className="text-xs text-black/50 hover:text-black transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                  <Input
                    id="password"
                    data-testid="sales-password-input"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pl-11 h-11 rounded-lg border-black/20 bg-white focus:ring-2 focus:ring-black focus:border-black"
                  />
                </div>
              </div>

              <Button
                type="submit"
                data-testid="sales-submit-button"
                className="w-full bg-black text-white hover:bg-black/90 rounded-lg h-11 font-medium text-sm shadow-sm"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In to Sales Portal'}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-black/10"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-white text-black/40">Sales team access only</span>
              </div>
            </div>

            {/* Info */}
            <p className="text-center text-xs text-black/50">
              Need an account? Contact your administrator.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SalesLogin;
