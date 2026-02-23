import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Lock, Eye, EyeOff, ShieldCheck, AlertTriangle, ArrowLeft, Shield } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

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
        `${API}/api/client-auth/change-password`,
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
    <div className="min-h-screen flex bg-white" data-testid="client-change-password-page">
      {/* Left Panel - Branding (matches main ERP) */}
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
              Secure your<br />account
            </h2>
            <p className="text-white/60 text-lg max-w-md">
              Create a strong password to protect your client portal access and project information.
            </p>
          </div>

          <div className="mt-12 bg-white/5 rounded-xl p-6 border border-white/10">
            <ShieldCheck className="w-10 h-10 text-white/80 mb-4" />
            <h3 className="text-white font-semibold">Password Security Tips</h3>
            <ul className="text-white/50 text-sm mt-3 space-y-2">
              <li>• Use at least 8 characters</li>
              <li>• Include uppercase and lowercase letters</li>
              <li>• Add numbers for extra security</li>
              <li>• Don't reuse passwords from other sites</li>
            </ul>
          </div>
        </div>

        <div className="text-white/40 text-sm">
          © {new Date().getFullYear()} DVBC Consulting. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Change Password Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-[440px]">
          {/* Back to Portal */}
          {!clientData?.must_change_password && (
            <button
              onClick={() => navigate('/client-portal')}
              className="flex items-center gap-2 text-black/50 hover:text-black mb-6 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Back to Portal</span>
            </button>
          )}

          <Card className="border border-black/10 shadow-lg rounded-2xl overflow-hidden" data-testid="change-password-card">
            {/* Header with Logo */}
            <div className="bg-white px-8 pt-10 pb-6 text-center border-b border-black/5">
              <img
                src={LOGO_URL}
                alt="DVBC Logo"
                className="h-16 w-auto mx-auto mb-4"
              />
              <h1 className="text-xl font-bold tracking-wide text-black">
                Change Password
              </h1>
              <p className="text-xs text-black/40 mt-1">
                {clientData?.must_change_password 
                  ? 'Create a new password to secure your account'
                  : 'Update your password'
                }
              </p>
            </div>

            <CardContent className="px-8 py-8 space-y-5 bg-white">
              {clientData?.must_change_password && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-amber-800 font-medium">First Login Required</p>
                    <p className="text-xs text-amber-600 mt-1">
                      You must change your temporary password before accessing the portal.
                    </p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4" data-testid="change-password-form">
                {/* Current Password */}
                <div className="space-y-2">
                  <Label htmlFor="current_password" className="text-sm font-medium text-black">
                    Current Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                    <Input
                      id="current_password"
                      data-testid="current-password-input"
                      type={showPasswords.current ? 'text' : 'password'}
                      placeholder="Enter current password"
                      value={formData.current_password}
                      onChange={(e) => setFormData({ ...formData, current_password: e.target.value })}
                      className="pl-11 pr-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => togglePasswordVisibility('current')}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black/40 hover:text-black transition-colors"
                    >
                      {showPasswords.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* New Password */}
                <div className="space-y-2">
                  <Label htmlFor="new_password" className="text-sm font-medium text-black">
                    New Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                    <Input
                      id="new_password"
                      data-testid="new-password-input"
                      type={showPasswords.new ? 'text' : 'password'}
                      placeholder="Create new password"
                      value={formData.new_password}
                      onChange={(e) => setFormData({ ...formData, new_password: e.target.value })}
                      className="pl-11 pr-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => togglePasswordVisibility('new')}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black/40 hover:text-black transition-colors"
                    >
                      {showPasswords.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  
                  {/* Password Requirements */}
                  {formData.new_password && (
                    <div className="mt-2 p-3 bg-black/5 rounded-lg space-y-1.5">
                      <p className="text-xs text-black/50 mb-2">Password requirements:</p>
                      <div className={`text-xs flex items-center gap-2 ${passwordChecks.length ? 'text-emerald-600' : 'text-black/40'}`}>
                        {passwordChecks.length ? '✓' : '○'} At least 8 characters
                      </div>
                      <div className={`text-xs flex items-center gap-2 ${passwordChecks.uppercase ? 'text-emerald-600' : 'text-black/40'}`}>
                        {passwordChecks.uppercase ? '✓' : '○'} One uppercase letter
                      </div>
                      <div className={`text-xs flex items-center gap-2 ${passwordChecks.lowercase ? 'text-emerald-600' : 'text-black/40'}`}>
                        {passwordChecks.lowercase ? '✓' : '○'} One lowercase letter
                      </div>
                      <div className={`text-xs flex items-center gap-2 ${passwordChecks.number ? 'text-emerald-600' : 'text-black/40'}`}>
                        {passwordChecks.number ? '✓' : '○'} One number
                      </div>
                    </div>
                  )}
                </div>

                {/* Confirm Password */}
                <div className="space-y-2">
                  <Label htmlFor="confirm_password" className="text-sm font-medium text-black">
                    Confirm New Password
                  </Label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-black/40" />
                    <Input
                      id="confirm_password"
                      data-testid="confirm-password-input"
                      type={showPasswords.confirm ? 'text' : 'password'}
                      placeholder="Confirm new password"
                      value={formData.confirm_password}
                      onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                      className="pl-11 pr-11 h-11 rounded-lg border-black/20 bg-white text-black placeholder:text-black/40 focus:ring-2 focus:ring-black focus:border-black"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => togglePasswordVisibility('confirm')}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-black/40 hover:text-black transition-colors"
                    >
                      {showPasswords.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {formData.confirm_password && formData.new_password !== formData.confirm_password && (
                    <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
                  )}
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  data-testid="change-password-btn"
                  disabled={loading || formData.new_password !== formData.confirm_password}
                  className="w-full bg-black text-white hover:bg-black/90 rounded-lg h-11 font-medium shadow-sm mt-2"
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
    </div>
  );
};

export default ClientChangePassword;
