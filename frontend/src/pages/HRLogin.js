import React, { useState, useContext, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { Users, Lock, Mail, UserCheck, ClipboardList, Calendar, Wallet } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

// HR roles that can access the HR Portal
const HR_ROLES = ['hr_manager', 'hr_executive'];

const HRLogin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // If already logged in with an HR role, redirect to HR portal
    if (user && HR_ROLES.includes(user.role)) {
      navigate('/hr');
    } else if (user) {
      // Logged in but not an HR role - redirect to main app
      toast.error('Access denied. HR Portal is for HR team only.');
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
      
      // Check if user has an HR role
      if (!HR_ROLES.includes(userData.role)) {
        toast.error('Access denied. HR Portal is for HR team only.');
        setLoading(false);
        return;
      }
      
      login(response.data.access_token, userData);
      toast.success('Welcome to HR Portal!');
      navigate('/hr');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Users, label: 'Employee Management', desc: 'Onboard & manage staff' },
    { icon: UserCheck, label: 'Attendance Tracking', desc: 'Monitor team presence' },
    { icon: Calendar, label: 'Leave Management', desc: 'Approve time-off requests' },
    { icon: Wallet, label: 'Payroll Processing', desc: 'Manage compensation' },
  ];

  return (
    <div className="min-h-screen flex bg-white" data-testid="hr-login-page">
      {/* Left Panel - Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-black p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center border border-white/20">
              <Users className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">DVBC HR Portal</h1>
              <p className="text-white/60 text-sm">People Operations Hub</p>
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Empower your<br />workforce management
            </h2>
            <p className="text-white/60 text-lg max-w-md">
              Complete HR toolkit - from onboarding to payroll, streamline all people operations in one place.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-12">
            {features.map((feature, idx) => (
              <div key={idx} className="bg-white/5 rounded-xl p-4 border border-white/10 hover:bg-white/10 transition-colors">
                <feature.icon className="w-8 h-8 text-white/80 mb-2" />
                <h3 className="text-white font-semibold">{feature.label}</h3>
                <p className="text-white/50 text-sm">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="text-white/40 text-sm">
          © {new Date().getFullYear()} DVBC Consulting. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
        <Card className="w-full max-w-md border border-black/10 shadow-lg rounded-2xl">
          <CardContent className="p-8 bg-white">
            <div className="text-center mb-8">
              <img 
                src={LOGO_URL} 
                alt="DVBC Logo" 
                className="h-16 mx-auto mb-4 object-contain"
              />
              <h2 className="text-2xl font-bold text-black">HR Portal Login</h2>
              <p className="text-black/50 mt-1">Access your HR dashboard</p>
            </div>

            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-black">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-black/40" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="hr@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10 border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-black focus:border-black"
                    required
                    data-testid="hr-email-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-black">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-black/40" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-black focus:border-black"
                    required
                    data-testid="hr-password-input"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-black hover:bg-black/90 text-white"
                disabled={loading}
                data-testid="hr-login-submit"
              >
                {loading ? 'Signing in...' : 'Sign in to HR Portal'}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-black/50">
                Not an HR team member?{' '}
                <a href="/login" className="text-black font-medium hover:underline">
                  Go to main login
                </a>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default HRLogin;
