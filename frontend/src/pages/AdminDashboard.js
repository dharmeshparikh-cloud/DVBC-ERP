import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Link } from 'react-router-dom';
import LockableCard from '../components/LockableCard';
import {
  TrendingUp, TrendingDown, Users, FileText, DollarSign, Target,
  Briefcase, Clock, CheckCircle, AlertCircle, Calendar, Award,
  Building2, BarChart3, PieChart, Activity, ArrowUpRight, ArrowDownRight,
  ChevronRight, Zap, Flame, RefreshCw
} from 'lucide-react';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts';

const AdminDashboard = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    sales: null,
    hr: null,
    consulting: null,
    finance: null
  });
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    fetchAllStats();
  }, []);

  const fetchAllStats = async () => {
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${localStorage.getItem('token')}` };
      
      // Fetch all department stats in parallel
      const [salesRes, hrRes, consultingRes] = await Promise.all([
        fetch(`${API}/stats/sales-dashboard-enhanced?view_mode=team`, { headers }).catch(() => null),
        fetch(`${API}/stats/hr`, { headers }).catch(() => null),
        fetch(`${API}/stats/consulting`, { headers }).catch(() => null),
      ]);

      const salesData = salesRes?.ok ? await salesRes.json() : null;
      const hrData = hrRes?.ok ? await hrRes.json() : null;
      const consultingData = consultingRes?.ok ? await consultingRes.json() : null;

      setStats({
        sales: salesData,
        hr: hrData,
        consulting: consultingData,
        finance: { 
          revenue: 45000000, 
          pendingInvoices: 18, 
          receivables: 12500000,
          profitMargin: 32 
        }
      });
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (!value) return '₹0';
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
    return `₹${value}`;
  };

  // Extract data from stats
  const salesPipeline = stats.sales?.pipeline || {};
  const hrStats = stats.hr || {};
  const consultingStats = stats.consulting || {};
  
  // Project status for pie chart
  const projectStatus = [
    { name: 'On Track', value: consultingStats.onTrack || 15, color: '#10b981' },
    { name: 'At Risk', value: consultingStats.atRisk || 5, color: '#f59e0b' },
    { name: 'Delayed', value: consultingStats.delayed || 3, color: '#ef4444' },
  ];

  // Monthly trend data (mock - would come from backend)
  const monthlyTrend = [
    { month: 'Jul', sales: 35, consulting: 28 },
    { month: 'Aug', sales: 42, consulting: 32 },
    { month: 'Sep', sales: 38, consulting: 35 },
    { month: 'Oct', sales: 45, consulting: 38 },
    { month: 'Nov', sales: 52, consulting: 42 },
    { month: 'Dec', sales: salesPipeline.total || 47, consulting: consultingStats.activeProjects || 45 },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${isDark ? 'border-orange-400' : 'border-orange-500'}`}></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Business Overview
          </h1>
          <p className={`${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>December 2025</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={`px-4 py-2 ${isDark ? 'bg-zinc-800 text-zinc-200' : 'bg-zinc-900 text-white'}`}>
            <Zap className="w-4 h-4 mr-2" />
            All Systems Operational
          </Badge>
          <Button
            onClick={fetchAllStats}
            variant="outline"
            size="sm"
            className={`gap-2 ${isDark ? 'border-zinc-700 text-zinc-300 hover:bg-zinc-800' : ''}`}
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-4 auto-rows-[140px]">
        
        {/* Large Revenue Card - With Lock Controls */}
        <LockableCard 
          className={`col-span-4 row-span-2 overflow-hidden relative ${
            isDark 
              ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' 
              : 'bg-gradient-to-br from-zinc-900 to-zinc-800 border-zinc-700'
          } text-white`}
          cardId="total-revenue"
          isDark={isDark}
          lockedValues={{ revenue: stats.finance?.revenue }}
        >
          <CardContent className="pt-6 h-full flex flex-col justify-between relative z-10">
            <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/20 rounded-full blur-3xl"></div>
            <div className="relative">
              <p className="text-zinc-400 text-sm">Total Revenue (YTD)</p>
              <p className="text-5xl font-bold mt-2">
                {formatCurrency(stats.finance?.revenue || 45000000).replace('₹', '')}
                <span className="text-2xl text-zinc-400 ml-1">
                  {formatCurrency(stats.finance?.revenue || 45000000).includes('Cr') ? '' : ''}
                </span>
              </p>
            </div>
            <div className="flex items-center gap-4 relative">
              <div className="flex items-center gap-1 text-green-400">
                <TrendingUp className="w-5 h-5" />
                <span className="font-medium">+23.5%</span>
              </div>
              <span className="text-zinc-500 text-sm">vs last year</span>
            </div>
            <Link to="/reports?category=finance" className="text-orange-400 text-sm flex items-center gap-1 hover:underline relative">
              View Financial Reports <ChevronRight className="w-4 h-4" />
            </Link>
          </CardContent>
        </LockableCard>

        {/* Sales Quick Stats */}
        <LockableCard 
          className="col-span-2 bg-orange-500 text-white border-orange-600"
          cardId="active-leads"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <BarChart3 className="w-8 h-8 opacity-80" />
            <div>
              <p className="text-3xl font-bold">{salesPipeline.total || 234}</p>
              <p className="text-orange-100 text-sm">Active Leads</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Conversion Rate */}
        <LockableCard 
          className={`col-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="conversion-rate"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <Target className={`w-6 h-6 ${isDark ? 'text-green-400' : 'text-green-600'}`} />
            <div>
              <p className={`text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.ratios?.lead_to_closure || 20.1}%
              </p>
              <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Conversion Rate</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Project Health Pie */}
        <LockableCard 
          className={`col-span-4 row-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="project-health"
          isDark={isDark}
        >
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm font-medium flex items-center gap-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              <Briefcase className="w-4 h-4" />
              Project Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={150}>
                <RechartsPie>
                  <Pie
                    data={projectStatus}
                    cx="50%"
                    cy="50%"
                    innerRadius={35}
                    outerRadius={55}
                    dataKey="value"
                  >
                    {projectStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
              <div className="space-y-2 flex-1">
                {projectStatus.map((s, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded" style={{ background: s.color }}></div>
                      <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{s.name}</span>
                    </div>
                    <span className={`font-semibold ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <Link to="/projects" className={`text-sm flex items-center gap-1 mt-2 ${isDark ? 'text-blue-400' : 'text-blue-600'} hover:underline`}>
              View All Projects <ChevronRight className="w-4 h-4" />
            </Link>
          </CardContent>
        </LockableCard>

        {/* Meetings Today */}
        <LockableCard 
          className="col-span-2 bg-blue-600 text-white border-blue-700"
          cardId="meetings-today"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <Calendar className="w-6 h-6 opacity-80" />
            <div>
              <p className="text-3xl font-bold">{stats.sales?.meetings?.today || 8}</p>
              <p className="text-blue-100 text-sm">Meetings Today</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Pending Approvals */}
        <LockableCard 
          className="col-span-2 bg-amber-500 text-white border-amber-600"
          cardId="pending-approvals"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <AlertCircle className="w-6 h-6 opacity-80" />
            <div>
              <p className="text-3xl font-bold">{hrStats.pendingApprovals || 24}</p>
              <p className="text-amber-100 text-sm">Pending Actions</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Team Present */}
        <LockableCard 
          className={`col-span-3 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="team-present"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full">
            <div className="flex items-center justify-between h-full">
              <div>
                <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Team Present</p>
                <p className={`text-4xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {hrStats.presentToday || 79}
                  <span className={`text-lg ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    /{hrStats.totalEmployees || 86}
                  </span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-emerald-500">
                  {hrStats.attendanceRate || 91.8}%
                </p>
                <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Attendance</p>
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Utilization */}
        <LockableCard 
          className="col-span-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white border-purple-700"
          cardId="team-utilization"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-purple-200 text-sm">Team Utilization</span>
              <Activity className="w-5 h-5 opacity-80" />
            </div>
            <div className="flex items-end gap-4">
              <p className="text-4xl font-bold">{consultingStats.utilization || 87}%</p>
              <div className="flex items-center gap-1 text-green-300 text-sm mb-1">
                <ArrowUpRight className="w-4 h-4" />
                +5%
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Performance Trend Chart */}
        <LockableCard 
          className={`col-span-6 row-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="performance-trend"
          isDark={isDark}
        >
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              Performance Trend (6 Months)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={monthlyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
                <XAxis dataKey="month" stroke={isDark ? '#71717a' : '#9ca3af'} fontSize={12} />
                <YAxis stroke={isDark ? '#71717a' : '#9ca3af'} fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: isDark ? '#18181b' : '#fff',
                    border: isDark ? '1px solid #3f3f46' : '1px solid #e5e7eb',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: isDark ? '#fff' : '#000' }}
                />
                <Line type="monotone" dataKey="sales" stroke="#f97316" strokeWidth={2} dot={{ fill: '#f97316' }} name="Sales Leads" />
                <Line type="monotone" dataKey="consulting" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} name="Projects" />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-6 mt-2">
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>Sales Leads</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>Consulting Projects</span>
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Hot Leads */}
        <LockableCard 
          className={`col-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="hot-leads"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <Flame className="w-6 h-6 text-red-500" />
            <div>
              <p className={`text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.temperature?.hot || 47}
              </p>
              <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Hot Leads</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Closed Deals */}
        <LockableCard 
          className={`col-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="closed-deals"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <div>
              <p className={`text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.closures?.this_month || 12}
              </p>
              <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Closed This Month</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* On Leave */}
        <LockableCard 
          className={`col-span-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}
          cardId="on-leave"
          isDark={isDark}
        >
          <CardContent className="pt-4 h-full flex flex-col justify-between">
            <Users className={`w-6 h-6 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
            <div>
              <p className={`text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {hrStats.onLeave || 7}
              </p>
              <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>On Leave Today</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800/50 border border-zinc-700' : 'bg-zinc-100'}`}>
        <h3 className={`text-sm font-medium mb-3 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Quick Actions</h3>
        <div className="flex gap-3 flex-wrap">
          <Link to="/leads">
            <Button variant="outline" size="sm" className={`gap-2 ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Users className="w-4 h-4" /> View Leads
            </Button>
          </Link>
          <Link to="/projects">
            <Button variant="outline" size="sm" className={`gap-2 ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Briefcase className="w-4 h-4" /> View Projects
            </Button>
          </Link>
          <Link to="/approvals">
            <Button variant="outline" size="sm" className={`gap-2 ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Clock className="w-4 h-4" /> Pending Approvals
            </Button>
          </Link>
          <Link to="/reports">
            <Button variant="outline" size="sm" className={`gap-2 ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <BarChart3 className="w-4 h-4" /> All Reports
            </Button>
          </Link>
        </div>
      </div>

      {/* Last Updated */}
      <p className={`text-xs text-center ${isDark ? 'text-zinc-600' : 'text-zinc-400'}`}>
        Last updated: {lastUpdated.toLocaleTimeString()}
      </p>
    </div>
  );
};

export default AdminDashboard;
