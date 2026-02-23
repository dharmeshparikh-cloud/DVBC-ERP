import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Lock, Eye, EyeOff, ShieldCheck, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ClientChangePassword = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [clientData, setClientData] = useState(null);

  useEffect(() => {
    const data = localStorage.getItem('client_data');
    const token = localStorage.getItem('client_token');
    
    if (!token || !data) {
      navigate('/client-login');
      return;
    }
    
    setClientData(JSON.parse(data));
  }, [navigate]);

  const validatePassword = (password) => {
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*]/.test(password)
    };
    return checks;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.new_password !== formData.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }

    const checks = validatePassword(formData.new_password);
    if (!checks.length) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem('client_token');
      await axios.post(
        `${API}/client-auth/change-password`,
        {
          current_password: formData.current_password,
          new_password: formData.new_password
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Update local storage
      const data = JSON.parse(localStorage.getItem('client_data'));
      data.must_change_password = false;
      localStorage.setItem('client_data', JSON.stringify(data));
      
      toast.success('Password changed successfully!');
      navigate('/client-portal');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to change password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const togglePasswordVisibility = (field) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const passwordChecks = validatePassword(formData.new_password);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="border-slate-700/50 bg-slate-800/50 backdrop-blur-xl shadow-2xl">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center">
                <ShieldCheck className="w-8 h-8 text-amber-400" />
              </div>
            </div>
            
            <CardTitle className="text-2xl font-bold text-white">
              Change Password
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              {clientData?.must_change_password 
                ? 'Please create a new password to secure your account'
                : 'Update your password'
              }
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-6">
            {clientData?.must_change_password && (
              <div className="mb-6 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
                <div>
                  <p className="text-sm text-amber-300 font-medium">First Login</p>
                  <p className="text-xs text-amber-400/80 mt-1">
                    You must change your temporary password before accessing the portal.
                  </p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Current Password */}
              <div className="space-y-2">
                <Label htmlFor="current_password" className="text-slate-300">
                  Current Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <Input
                    id="current_password"
                    type={showPasswords.current ? 'text' : 'password'}
                    placeholder="Enter current password"
                    value={formData.current_password}
                    onChange={(e) => setFormData({ ...formData, current_password: e.target.value })}
                    className="pl-10 pr-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('current')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPasswords.current ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div className="space-y-2">
                <Label htmlFor="new_password" className="text-slate-300">
                  New Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <Input
                    id="new_password"
                    type={showPasswords.new ? 'text' : 'password'}
                    placeholder="Create new password"
                    value={formData.new_password}
                    onChange={(e) => setFormData({ ...formData, new_password: e.target.value })}
                    className="pl-10 pr-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('new')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPasswords.new ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                
                {/* Password Requirements */}
                {formData.new_password && (
                  <div className="mt-2 p-3 bg-slate-900/50 rounded-lg space-y-1.5">
                    <p className="text-xs text-slate-400 mb-2">Password requirements:</p>
                    <div className={`text-xs flex items-center gap-2 ${passwordChecks.length ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {passwordChecks.length ? '✓' : '○'} At least 8 characters
                    </div>
                    <div className={`text-xs flex items-center gap-2 ${passwordChecks.uppercase ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {passwordChecks.uppercase ? '✓' : '○'} One uppercase letter
                    </div>
                    <div className={`text-xs flex items-center gap-2 ${passwordChecks.lowercase ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {passwordChecks.lowercase ? '✓' : '○'} One lowercase letter
                    </div>
                    <div className={`text-xs flex items-center gap-2 ${passwordChecks.number ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {passwordChecks.number ? '✓' : '○'} One number
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirm_password" className="text-slate-300">
                  Confirm New Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <Input
                    id="confirm_password"
                    type={showPasswords.confirm ? 'text' : 'password'}
                    placeholder="Confirm new password"
                    value={formData.confirm_password}
                    onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                    className="pl-10 pr-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('confirm')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPasswords.confirm ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {formData.confirm_password && formData.new_password !== formData.confirm_password && (
                  <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
                )}
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={loading || formData.new_password !== formData.confirm_password}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 mt-6"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Changing Password...
                  </div>
                ) : (
                  'Change Password'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ClientChangePassword;
