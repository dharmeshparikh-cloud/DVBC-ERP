import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Building2, Lock, IdCard, Eye, EyeOff, ArrowLeft, LayoutDashboard, FileText, CreditCard, MessageSquare } from 'lucide-react';

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/client-auth/login`, formData);
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

  return (
    <div className="min-h-screen bg-zinc-50 flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-zinc-900 flex-col justify-between p-12">
        <div>
          <img src={LOGO_URL} alt="D&V Business Consulting" className="h-12 mb-8" />
          <h1 className="text-4xl font-bold text-white mb-4">
            DVBC - NETRA
          </h1>
          <p className="text-lg text-zinc-400">
            Client Portal
          </p>
        </div>
        
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-white">
            Track your project progress
          </h2>
          <p className="text-zinc-400 text-lg">
            Access your project dashboard, documents, and communicate with your consultant.
          </p>
          
          <div className="grid grid-cols-2 gap-4 mt-8">
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <LayoutDashboard className="w-8 h-8 text-amber-500 mb-3" />
              <h3 className="font-medium text-white">Project Dashboard</h3>
              <p className="text-sm text-zinc-500 mt-1">Real-time project status</p>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <FileText className="w-8 h-8 text-emerald-500 mb-3" />
              <h3 className="font-medium text-white">Documents</h3>
              <p className="text-sm text-zinc-500 mt-1">SOW, Agreements, Invoices</p>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <CreditCard className="w-8 h-8 text-blue-500 mb-3" />
              <h3 className="font-medium text-white">Payments</h3>
              <p className="text-sm text-zinc-500 mt-1">History & upcoming dues</p>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <MessageSquare className="w-8 h-8 text-purple-500 mb-3" />
              <h3 className="font-medium text-white">Meeting Notes</h3>
              <p className="text-sm text-zinc-500 mt-1">MOM from consultants</p>
            </div>
          </div>
        </div>
        
        <p className="text-zinc-600 text-sm">
          © {new Date().getFullYear()} D&V Business Consulting. All rights reserved.
        </p>
      </div>
      
      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Back to Employee Login */}
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 text-zinc-500 hover:text-zinc-800 mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Employee Login</span>
          </button>

          <Card className="border-zinc-200 shadow-lg">
            <CardContent className="pt-8 pb-8">
              {/* Mobile Logo */}
              <div className="lg:hidden flex justify-center mb-6">
                <img src={LOGO_URL} alt="D&V" className="h-12" />
              </div>
              
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-zinc-800">
                  Client Portal
                </h2>
                <p className="text-zinc-500 text-sm mt-2">
                  Sign in to access your project dashboard
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Client ID */}
                <div className="space-y-2">
                  <Label htmlFor="client_id" className="text-zinc-700">
                    Client ID
                  </Label>
                  <div className="relative">
                    <IdCard className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400" />
                    <Input
                      id="client_id"
                      type="text"
                      placeholder="Enter your Client ID (e.g., 98000)"
                      value={formData.client_id}
                      onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                      className="pl-10 border-zinc-300 focus:border-amber-500 focus:ring-amber-500/20"
                      required
                      data-testid="client-id-input"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-zinc-700">
                    Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="pl-10 pr-10 border-zinc-300 focus:border-amber-500 focus:ring-amber-500/20"
                      required
                      data-testid="client-password-input"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-300 text-amber-600 focus:ring-amber-500"
                  />
                  <Label htmlFor="remember" className="text-sm text-zinc-600 cursor-pointer">
                    Remember my Client ID
                  </Label>
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold py-3"
                  data-testid="client-login-btn"
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
              <div className="mt-6 pt-6 border-t border-zinc-200">
                <div className="flex items-start gap-3 text-zinc-600 text-sm">
                  <Building2 className="w-5 h-5 mt-0.5 text-amber-600 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-zinc-700">First time logging in?</p>
                    <p className="mt-1 text-zinc-500">
                      Your Client ID and temporary password were sent to your email when your project was approved.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Mobile Footer */}
          <p className="lg:hidden text-center text-zinc-400 text-xs mt-6">
            © {new Date().getFullYear()} D&V Business Consulting
          </p>
        </div>
      </div>
    </div>
  );
};

export default ClientLogin;
