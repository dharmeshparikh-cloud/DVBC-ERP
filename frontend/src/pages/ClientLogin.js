import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Building2, Lock, IdCard, Eye, EyeOff, ArrowLeft, LayoutDashboard, FileText, CreditCard, MessageSquare, Shield } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const ClientLogin = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    password: ''
  });

  // Load remembered Client ID on mount
  useEffect(() => {
    const savedClientId = localStorage.getItem('client_remembered_id');
    if (savedClientId) {
      setFormData(prev => ({ ...prev, client_id: savedClientId }));
      setRememberMe(true);
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/api/client-auth/login`, formData);
      const { access_token, client_id, full_name, company_name, must_change_password, project_ids } = response.data;
      
      // Store client token and data
      localStorage.setItem('client_token', access_token);
      localStorage.setItem('client_data', JSON.stringify({
        client_id,
        full_name,
        company_name,
        must_change_password,
        project_ids
      }));

      if (rememberMe) {
        localStorage.setItem('client_remembered_id', client_id);
      } else {
        localStorage.removeItem('client_remembered_id');
      }
      
      toast.success(`Welcome, ${full_name}!`);
      
      if (must_change_password) {
        navigate('/client-portal/change-password');
      } else {
        navigate('/client-portal');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed. Please check your credentials.';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: LayoutDashboard, label: 'Project Dashboard', desc: 'Real-time project status' },
    { icon: FileText, label: 'Documents', desc: 'SOW, Agreements, Invoices' },
    { icon: CreditCard, label: 'Payments', desc: 'History & upcoming dues' },
    { icon: MessageSquare, label: 'Meeting Notes', desc: 'MOM from consultants' },
  ];

  return (
    <div className="min-h-screen flex bg-white" data-testid="client-login-page">
      {/* Left Panel - Features (matches main ERP style) */}
      <div className="hidden lg:flex lg:w-1/2 bg-black p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center border border-white/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">DVBC - NETRA</h1>
              <p className="text-white/60 text-sm">Client Portal</p>
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Track your<br />project progress
            </h2>
            <p className="text-white/60 text-lg max-w-md">
              Access your project dashboard, documents, and communicate with your consultant team.
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
        <div className="w-full max-w-[440px]">
          {/* Back to Employee Login */}
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 text-black/50 hover:text-black mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Employee Login</span>
          </button>

          <Card className="border border-black/10 shadow-lg rounded-2xl overflow-hidden" data-testid="client-login-card">
            {/* Header with Logo */}
            <div className="bg-white px-8 pt-10 pb-6 text-center border-b border-black/5">
              <img
                src={LOGO_URL}
                alt="DVBC Logo"
                className="h-16 w-auto mx-auto mb-4"
                data-testid="client-login-logo"
              />
              <h1 className="text-xl font-bold tracking-wide text-black">
                Client Portal
              </h1>
              <p className="text-xs text-black/40 mt-1 tracking-widest uppercase">Sign in to your account</p>
            </div>

            <CardContent className="px-8 py-8 space-y-5 bg-white">
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="client-login-form">
                {/* Client ID */}
                <div className="space-y-2">
                  <Label htmlFor="client_id" className="text-sm font-medium text-black">Client ID</Label>
                  <div className="relative">
                    <IdCard className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                    <Input
                      id="client_id"
                      data-testid="client-id-input"
                      type="text"
                      placeholder="98000"
                      value={formData.client_id}
                      onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                      required
                      className="pl-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password" className="text-sm font-medium text-black">Password</Label>
                    <button
                      type="button"
                      onClick={() => toast.info('Please contact your account manager for password reset.')}
                      className="text-xs text-black/50 hover:text-black transition-colors"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                    <Input
                      id="password"
                      data-testid="client-password-input"
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                      className="pl-11 pr-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black/40 hover:text-black transition-colors"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="rememberClient"
                    data-testid="client-remember-me"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-black/20 text-black focus:ring-black focus:ring-offset-0 cursor-pointer"
                  />
                  <Label htmlFor="rememberClient" className="text-sm text-black/60 cursor-pointer select-none">
                    Remember my Client ID
                  </Label>
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  data-testid="client-login-btn"
                  className="w-full bg-black text-white hover:bg-black/90 rounded-lg h-11 font-medium shadow-sm"
                  disabled={loading}
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Signing In...
                    </div>
                  ) : (
                    'Sign In'
                  )}
                </Button>
              </form>

              {/* Help Text */}
              <div className="pt-6 border-t border-black/10">
                <div className="flex items-start gap-3 text-black/60 text-sm">
                  <Building2 className="w-5 h-5 mt-0.5 text-black/40 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-black/70">First time logging in?</p>
                    <p className="mt-1 text-black/50 text-xs">
                      Your Client ID and temporary password were sent to your email when your project was approved.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Mobile Footer */}
          <p className="lg:hidden text-center text-black/40 text-xs mt-6">
            © {new Date().getFullYear()} D&V Business Consulting
          </p>
        </div>
      </div>
    </div>
  );
};

export default ClientLogin;
