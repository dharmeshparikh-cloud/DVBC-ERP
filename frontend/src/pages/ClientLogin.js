import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Building2, Lock, User, Eye, EyeOff, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ClientLogin = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
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
      
      toast.success(`Welcome, ${full_name}!`);
      
      // Redirect to change password if required
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMyMDIwMjAiIGZpbGwtb3BhY2l0eT0iMC4xIj48cGF0aCBkPSJNMzYgMzRoLTJ2LTRoMnY0em0wLTZ2LTRoLTJ2NGgyek0zMCAzNGgtMnYtNGgydjR6bTAtNnYtNGgtMnY0aDJ6Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-20"></div>
      
      <div className="relative z-10 w-full max-w-md">
        {/* Back to Employee Login */}
        <button
          onClick={() => navigate('/login')}
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Employee Login</span>
        </button>

        <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur-xl shadow-2xl">
          <CardHeader className="text-center pb-2">
            {/* Logo */}
            <div className="flex justify-center mb-4">
              <img 
                src="https://dvconsulting.co.in/wp-content/uploads/2020/02/logov4-min.png" 
                alt="D&V Business Consulting" 
                className="h-16"
              />
            </div>
            
            <CardTitle className="text-2xl font-bold text-white">
              Client Portal
            </CardTitle>
            <p className="text-slate-400 text-sm mt-2">
              Access your project dashboard and documents
            </p>
          </CardHeader>

          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Client ID */}
              <div className="space-y-2">
                <Label htmlFor="client_id" className="text-slate-300">
                  Client ID
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <Input
                    id="client_id"
                    type="text"
                    placeholder="Enter your Client ID (e.g., 98000)"
                    value={formData.client_id}
                    onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                    className="pl-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500 focus:border-emerald-500 focus:ring-emerald-500/20"
                    required
                    data-testid="client-id-input"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-300">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="pl-10 pr-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500 focus:border-emerald-500 focus:ring-emerald-500/20"
                    required
                    data-testid="client-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3"
                data-testid="client-login-btn"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Signing In...
                  </div>
                ) : (
                  'Sign In to Portal'
                )}
              </Button>
            </form>

            {/* Help Text */}
            <div className="mt-6 pt-6 border-t border-slate-700">
              <div className="flex items-start gap-3 text-slate-400 text-sm">
                <Building2 className="w-5 h-5 mt-0.5 text-emerald-500" />
                <div>
                  <p className="font-medium text-slate-300">First time logging in?</p>
                  <p className="mt-1">
                    Your Client ID and temporary password were sent to your email when your project was approved.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-slate-500 text-xs mt-6">
          © {new Date().getFullYear()} D&V Business Consulting. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default ClientLogin;
