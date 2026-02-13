import React, { useState, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('executive');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        const response = await axios.post(`${API}/auth/login`, { email, password });
        login(response.data.access_token, response.data.user);
        toast.success('Login successful');
      } else {
        await axios.post(`${API}/auth/register`, {
          email,
          password,
          full_name: fullName,
          role,
        });
        toast.success('Registration successful. Please login.');
        setIsLogin(true);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white grid-background p-6">
      <Card className="w-full max-w-md border-zinc-200 shadow-none rounded-sm" data-testid="login-card">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-semibold tracking-tight uppercase text-zinc-950">
            {isLogin ? 'Sign In' : 'Create Account'}
          </CardTitle>
          <CardDescription className="text-zinc-500">
            {isLogin ? 'Enter your credentials to access your account' : 'Register a new account'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="fullName" className="text-sm font-medium text-zinc-950">
                  Full Name
                </Label>
                <Input
                  id="fullName"
                  data-testid="fullname-input"
                  type="text"
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  className="rounded-sm border-zinc-200 bg-transparent focus:ring-1 focus:ring-zinc-950"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-zinc-950">
                Email
              </Label>
              <Input
                id="email"
                data-testid="email-input"
                type="email"
                placeholder="john@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="rounded-sm border-zinc-200 bg-transparent focus:ring-1 focus:ring-zinc-950"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-zinc-950">
                Password
              </Label>
              <Input
                id="password"
                data-testid="password-input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="rounded-sm border-zinc-200 bg-transparent focus:ring-1 focus:ring-zinc-950"
              />
            </div>

            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="role" className="text-sm font-medium text-zinc-950">
                  Role
                </Label>
                <select
                  id="role"
                  data-testid="role-select"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="executive">Executive</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            )}

            <Button
              type="submit"
              data-testid="submit-button"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              disabled={loading}
            >
              {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
            </Button>

            <div className="text-center text-sm">
              <button
                type="button"
                data-testid="toggle-auth-button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-zinc-600 hover:text-zinc-950 transition-colors"
              >
                {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
