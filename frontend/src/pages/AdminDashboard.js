import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Link, useNavigate } from 'react-router-dom';
import LockableCard from '../components/LockableCard';
import QuickCheckInModal from '../components/QuickCheckInModal';
import { 
  RevenueExpanded, LeadsExpanded, MeetingsExpanded, 
  ProjectsExpanded, AttendanceExpanded 
} from '../components/ExpandedCardViews';
import {
  TrendingUp, TrendingDown, Users, FileText, DollarSign, Target,
  Briefcase, Clock, CheckCircle, AlertCircle, Calendar, Award,
  Building2, BarChart3, PieChart, Activity, ArrowUpRight, ArrowDownRight,
  ChevronRight, Zap, Flame, RefreshCw, LogIn, ArrowRight
} from 'lucide-react';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts';

const AdminDashboard = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const navigate = useNavigate();
  const isDark = theme === 'dark';
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    sales: null,
    hr: null,
    consulting: null,
    finance: null
  });
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  // Quick Check-in Modal state
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [attendanceStatus, setAttendanceStatus] = useState(null);

  useEffect(() => {
    fetchAllStats();
    fetchAttendanceStatus();
  }, []);

  const fetchAttendanceStatus = async () => {
    try {
      const res = await axios.get(`${API}/my/check-status`);
      setAttendanceStatus(res.data);
    } catch (err) {
      console.error('Failed to fetch attendance status');
    }
  };

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
    <div className="space-y-4 md:space-y-6" data-testid="admin-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className={`text-xl md:text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Business Overview
          </h1>
          <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>December 2025</p>
        </div>
        <div className="flex items-center gap-2 md:gap-3 flex-wrap">
          <Badge className={`px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm ${isDark ? 'bg-zinc-800 text-zinc-200' : 'bg-zinc-900 text-white'}`}>
            <Zap className="w-3 h-3 md:w-4 md:h-4 mr-1 md:mr-2" />
            All Systems Operational
          </Badge>
          <Button
            onClick={fetchAllStats}
            variant="outline"
            size="sm"
            className={`gap-1 md:gap-2 text-xs md:text-sm ${isDark ? 'border-zinc-700 text-zinc-300 hover:bg-zinc-800' : ''}`}
          >
            <RefreshCw className="w-3 h-3 md:w-4 md:h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Quick Attendance Card - Light Blue to Dark Blue Gradient */}
      <Card 
        className={`cursor-pointer transition-all hover:shadow-lg ${
          isDark 
            ? 'bg-gradient-to-r from-blue-400 via-blue-500 to-blue-700 border-blue-600' 
            : 'bg-gradient-to-r from-sky-400 via-blue-500 to-blue-700 border-blue-500'
        }`}
        onClick={() => setShowQuickCheckIn(true)}
        data-testid="admin-quick-attendance-card"
      >
        <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 md:p-5 gap-3">
          <div className="flex items-center gap-3 md:gap-4">
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center bg-white/20`}>
              <Clock className="w-5 h-5 md:w-6 md:h-6 text-white" />
            </div>
            <div>
              <h3 className="text-base md:text-lg font-bold text-white">Quick Attendance</h3>
              <p className="text-white/70 text-xs md:text-sm">
                {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out 
                  ? 'Completed for today' 
                  : attendanceStatus?.has_checked_in 
                    ? `Checked in at ${attendanceStatus?.check_in_time?.split('T')[1]?.slice(0,5) || '-'}` 
                    : 'Tap to check in'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out ? (
              <div className="flex items-center gap-2 px-3 md:px-4 py-2 bg-emerald-500 rounded-lg">
                <CheckCircle className="w-4 h-4 md:w-5 md:h-5 text-white" />
                <span className="text-white font-medium text-sm">Done</span>
              </div>
            ) : attendanceStatus?.has_checked_in ? (
              <div className="flex items-center gap-2 px-3 md:px-4 py-2 bg-amber-500 rounded-lg">
                <LogIn className="w-4 h-4 md:w-5 md:h-5 text-white" />
                <span className="text-white font-medium text-sm">Check Out</span>
              </div>
            ) : (
              <Button className="bg-white text-blue-600 hover:bg-white/90 h-10 md:h-11 px-4 md:px-6 font-semibold text-sm w-full sm:w-auto">
                <LogIn className="w-4 h-4 md:w-5 md:h-5 mr-2" /> Check In
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Check-in Modal */}
      <QuickCheckInModal 
        isOpen={showQuickCheckIn} 
        onClose={() => { setShowQuickCheckIn(false); fetchAttendanceStatus(); }} 
        user={user} 
      />

      {/* Mobile-Responsive Bento Grid */}
      <div className="grid grid-cols-2 md:grid-cols-6 lg:grid-cols-12 gap-3 md:gap-4">
        
        {/* Large Revenue Card - With Lock Controls - Green to Yellow Gradient */}
        <LockableCard 
          className={`col-span-2 md:col-span-3 lg:col-span-4 row-span-1 md:row-span-2 overflow-hidden relative ${
            isDark 
              ? 'bg-gradient-to-br from-emerald-700 via-emerald-600 to-yellow-500 border-emerald-600' 
              : 'bg-gradient-to-br from-emerald-600 via-emerald-500 to-yellow-400 border-emerald-500'
          } text-white`}
          cardId="total-revenue"
          isDark={isDark}
          title="Total Revenue (YTD)"
          expandedContent={<RevenueExpanded data={stats} isDark={isDark} />}
          lockedValues={{ revenue: stats.finance?.revenue }}
        >
          <CardContent className="pt-4 md:pt-6 h-full flex flex-col justify-between relative z-10">
            <div className="absolute top-0 right-0 w-24 md:w-32 h-24 md:h-32 bg-yellow-300/30 rounded-full blur-3xl"></div>
            <div className="relative">
              <p className="text-white/80 text-xs md:text-sm font-medium">Total Revenue (YTD)</p>
              <p className="text-3xl md:text-5xl font-bold mt-1 md:mt-2 text-white">
                {formatCurrency(stats.finance?.revenue || 45000000).replace('₹', '')}
              </p>
            </div>
            <div className="flex items-center gap-2 md:gap-4 relative mt-2">
              <div className="flex items-center gap-1 text-yellow-200">
                <TrendingUp className="w-4 h-4 md:w-5 md:h-5" />
                <span className="font-medium text-sm md:text-base">+23.5%</span>
              </div>
              <span className="text-white/60 text-xs md:text-sm hidden sm:inline">vs last year</span>
            </div>
            <Link to="/reports?category=finance" className="text-yellow-100 text-xs md:text-sm flex items-center gap-1 hover:text-white transition-colors relative mt-2 md:mt-0">
              View Financial Reports <ChevronRight className="w-3 h-3 md:w-4 md:h-4" />
            </Link>
          </CardContent>
        </LockableCard>

        {/* Sales Quick Stats - Active Leads */}
        <LockableCard 
          className="col-span-1 md:col-span-2 bg-gradient-to-br from-orange-500 to-amber-600 text-white border-orange-600"
          cardId="active-leads"
          isDark={isDark}
          title="Active Leads"
          expandedContent={<LeadsExpanded data={stats} isDark={isDark} />}
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <BarChart3 className="w-6 h-6 md:w-8 md:h-8 opacity-80" />
            <div>
              <p className="text-2xl md:text-3xl font-bold">{salesPipeline.total || 234}</p>
              <p className="text-orange-100 text-xs md:text-sm">Active Leads</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Conversion Rate */}
        <LockableCard 
          className={`col-span-1 md:col-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-zinc-50 border-zinc-200'}`}
          cardId="conversion-rate"
          isDark={isDark}
          title="Conversion Rate"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <Target className={`w-5 h-5 md:w-6 md:h-6 ${isDark ? 'text-green-400' : 'text-green-600'}`} />
            <div>
              <p className={`text-2xl md:text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.ratios?.lead_to_closure || 20.1}%
              </p>
              <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Conversion Rate</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Project Health Pie */}
        <LockableCard 
          className={`col-span-2 md:col-span-3 lg:col-span-4 row-span-1 md:row-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-slate-50 border-zinc-200'}`}
          cardId="project-health"
          isDark={isDark}
          title="Project Health"
          expandedContent={<ProjectsExpanded data={stats} isDark={isDark} />}
        >
          <CardHeader className="pb-1 md:pb-2 px-3 md:px-6">
            <CardTitle className={`text-xs md:text-sm font-medium flex items-center gap-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              <Briefcase className="w-3 h-3 md:w-4 md:h-4" />
              Project Health
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 md:px-6">
            <div className="flex flex-col md:flex-row items-center gap-2 md:gap-6">
              <ResponsiveContainer width="100%" height={100} className="md:hidden">
                <RechartsPie>
                  <Pie
                    data={projectStatus}
                    cx="50%"
                    cy="50%"
                    innerRadius={25}
                    outerRadius={40}
                    dataKey="value"
                  >
                    {projectStatus.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
              <ResponsiveContainer width="50%" height={150} className="hidden md:block">
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
              <div className="space-y-1 md:space-y-2 flex-1 w-full">
                {projectStatus.map((s, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 md:w-3 md:h-3 rounded" style={{ background: s.color }}></div>
                      <span className={`text-xs md:text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{s.name}</span>
                    </div>
                    <span className={`font-semibold text-sm md:text-base ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <Link to="/projects" className={`text-xs md:text-sm flex items-center gap-1 mt-2 ${isDark ? 'text-blue-400' : 'text-blue-600'} hover:underline`}>
              View All Projects <ChevronRight className="w-3 h-3 md:w-4 md:h-4" />
            </Link>
          </CardContent>
        </LockableCard>

        {/* Meetings Today */}
        <LockableCard 
          className="col-span-1 md:col-span-2 bg-gradient-to-br from-blue-500 to-indigo-600 text-white border-blue-700"
          cardId="meetings-today"
          isDark={isDark}
          title="Meetings Today"
          expandedContent={<MeetingsExpanded data={stats} isDark={isDark} />}
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <Calendar className="w-5 h-5 md:w-6 md:h-6 opacity-80" />
            <div>
              <p className="text-2xl md:text-3xl font-bold">{stats.sales?.meetings?.today || 8}</p>
              <p className="text-blue-100 text-xs md:text-sm">Meetings Today</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Pending Approvals */}
        <LockableCard 
          className="col-span-1 md:col-span-2 bg-gradient-to-br from-amber-400 to-orange-500 text-white border-amber-600"
          cardId="pending-approvals"
          isDark={isDark}
          title="Pending Actions"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <AlertCircle className="w-5 h-5 md:w-6 md:h-6 opacity-80" />
            <div>
              <p className="text-2xl md:text-3xl font-bold">{hrStats.pendingApprovals || 24}</p>
              <p className="text-amber-100 text-xs md:text-sm">Pending Actions</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Team Present */}
        <LockableCard 
          className={`col-span-1 md:col-span-3 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-emerald-50 border-zinc-200'}`}
          cardId="team-present"
          isDark={isDark}
          title="Team Attendance"
          expandedContent={<AttendanceExpanded data={stats} isDark={isDark} />}
        >
          <CardContent className="pt-3 md:pt-4 h-full min-h-[100px] md:min-h-[140px]">
            <div className="flex items-center justify-between h-full">
              <div>
                <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Team Present</p>
                <p className={`text-2xl md:text-4xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {hrStats.presentToday || 79}
                  <span className={`text-sm md:text-lg ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    /{hrStats.totalEmployees || 86}
                  </span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xl md:text-3xl font-bold text-emerald-500">
                  {hrStats.attendanceRate || 91.8}%
                </p>
                <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Attendance</p>
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Utilization */}
        <LockableCard 
          className="col-span-1 md:col-span-3 bg-gradient-to-r from-purple-500 via-fuchsia-500 to-pink-500 text-white border-purple-700"
          cardId="team-utilization"
          isDark={isDark}
          title="Team Utilization"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <div className="flex items-center justify-between">
              <span className="text-purple-200 text-xs md:text-sm">Team Utilization</span>
              <Activity className="w-4 h-4 md:w-5 md:h-5 opacity-80" />
            </div>
            <div className="flex items-end gap-2 md:gap-4">
              <p className="text-2xl md:text-4xl font-bold">{consultingStats.utilization || 87}%</p>
              <div className="flex items-center gap-1 text-green-300 text-xs md:text-sm mb-1">
                <ArrowUpRight className="w-3 h-3 md:w-4 md:h-4" />
                +5%
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Performance Trend Chart */}
        <LockableCard 
          className={`col-span-2 md:col-span-6 row-span-1 md:row-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-blue-50 border-zinc-200'}`}
          cardId="performance-trend"
          isDark={isDark}
          title="Performance Trend"
        >
          <CardHeader className="pb-1 md:pb-2 px-3 md:px-6">
            <CardTitle className={`text-xs md:text-sm font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              Performance Trend (6 Months)
            </CardTitle>
          </CardHeader>
          <CardContent className="px-3 md:px-6">
            <ResponsiveContainer width="100%" height={120} className="md:hidden">
              <LineChart data={monthlyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
                <XAxis dataKey="month" stroke={isDark ? '#71717a' : '#9ca3af'} fontSize={10} />
                <YAxis stroke={isDark ? '#71717a' : '#9ca3af'} fontSize={10} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: isDark ? '#18181b' : '#fff',
                    border: isDark ? '1px solid #3f3f46' : '1px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '10px'
                  }}
                  labelStyle={{ color: isDark ? '#fff' : '#000' }}
                />
                <Line type="monotone" dataKey="sales" stroke="#f97316" strokeWidth={2} dot={{ r: 2 }} name="Sales" />
                <Line type="monotone" dataKey="consulting" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} name="Projects" />
              </LineChart>
            </ResponsiveContainer>
            <ResponsiveContainer width="100%" height={180} className="hidden md:block">
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
            <div className="flex justify-center gap-4 md:gap-6 mt-2">
              <div className="flex items-center gap-1 md:gap-2 text-xs md:text-sm">
                <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-orange-500"></div>
                <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>Sales</span>
              </div>
              <div className="flex items-center gap-1 md:gap-2 text-xs md:text-sm">
                <div className="w-2 h-2 md:w-3 md:h-3 rounded-full bg-blue-500"></div>
                <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>Projects</span>
              </div>
            </div>
          </CardContent>
        </LockableCard>

        {/* Hot Leads */}
        <LockableCard 
          className={`col-span-1 md:col-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-red-50 border-zinc-200'}`}
          cardId="hot-leads"
          isDark={isDark}
          title="Hot Leads"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <Flame className="w-5 h-5 md:w-6 md:h-6 text-red-500" />
            <div>
              <p className={`text-2xl md:text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.temperature?.hot || 47}
              </p>
              <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Hot Leads</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* Closed Deals */}
        <LockableCard 
          className={`col-span-1 md:col-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-green-50 border-zinc-200'}`}
          cardId="closed-deals"
          isDark={isDark}
          title="Closed This Month"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <CheckCircle className="w-5 h-5 md:w-6 md:h-6 text-green-500" />
            <div>
              <p className={`text-2xl md:text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {stats.sales?.closures?.this_month || 12}
              </p>
              <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Closed This Month</p>
            </div>
          </CardContent>
        </LockableCard>

        {/* On Leave */}
        <LockableCard 
          className={`col-span-1 md:col-span-2 ${isDark ? 'bg-gradient-to-br from-zinc-800 to-zinc-900 border-zinc-700' : 'bg-gradient-to-br from-white to-amber-50 border-zinc-200'}`}
          cardId="on-leave"
          isDark={isDark}
          title="On Leave Today"
        >
          <CardContent className="pt-3 md:pt-4 h-full flex flex-col justify-between min-h-[100px] md:min-h-[140px]">
            <Users className={`w-5 h-5 md:w-6 md:h-6 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
            <div>
              <p className={`text-2xl md:text-3xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {hrStats.onLeave || 7}
              </p>
              <p className={`text-xs md:text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>On Leave Today</p>
            </div>
          </CardContent>
        </LockableCard>
      </div>

      {/* Quick Actions */}
      <div className={`p-3 md:p-4 rounded-lg ${isDark ? 'bg-zinc-800/50 border border-zinc-700' : 'bg-zinc-100'}`}>
        <h3 className={`text-xs md:text-sm font-medium mb-2 md:mb-3 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Quick Actions</h3>
        <div className="flex gap-2 md:gap-3 flex-wrap">
          <Link to="/leads">
            <Button variant="outline" size="sm" className={`gap-1 md:gap-2 text-xs md:text-sm ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Users className="w-3 h-3 md:w-4 md:h-4" /> View Leads
            </Button>
          </Link>
          <Link to="/projects">
            <Button variant="outline" size="sm" className={`gap-1 md:gap-2 text-xs md:text-sm ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Briefcase className="w-3 h-3 md:w-4 md:h-4" /> View Projects
            </Button>
          </Link>
          <Link to="/approvals">
            <Button variant="outline" size="sm" className={`gap-1 md:gap-2 text-xs md:text-sm ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <Clock className="w-3 h-3 md:w-4 md:h-4" /> Approvals
            </Button>
          </Link>
          <Link to="/reports">
            <Button variant="outline" size="sm" className={`gap-1 md:gap-2 text-xs md:text-sm ${isDark ? 'border-zinc-600 text-zinc-300 hover:bg-zinc-700' : ''}`}>
              <BarChart3 className="w-3 h-3 md:w-4 md:h-4" /> Reports
            </Button>
          </Link>
        </div>
      </div>

      {/* Last Updated */}
      <p className={`text-[10px] md:text-xs text-center ${isDark ? 'text-zinc-600' : 'text-zinc-400'}`}>
        Last updated: {lastUpdated.toLocaleTimeString()}
      </p>
    </div>
  );
};

export default AdminDashboard;
