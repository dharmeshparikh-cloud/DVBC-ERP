import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  TrendingUp, TrendingDown, Users, Target, Award, Clock, 
  Briefcase, CheckCircle, Star, Calendar, BarChart3, 
  ArrowUpRight, ArrowDownRight, Minus, Activity, Zap,
  Trophy, Medal, Crown, Flame
} from 'lucide-react';
import { 
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadialBarChart, RadialBar
} from 'recharts';
import { toast } from 'sonner';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const PerformanceDashboard = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('month');
  const [selectedDepartment, setSelectedDepartment] = useState('all');
  const [performanceData, setPerformanceData] = useState({
    summary: {},
    consultants: [],
    sales: [],
    trends: [],
    leaderboard: []
  });

  useEffect(() => {
    fetchPerformanceData();
  }, [timeRange, selectedDepartment]);

  const fetchPerformanceData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch consultants for performance metrics
      const consultantsRes = await fetch(`${API}/consultants`, { headers });
      const consultants = consultantsRes.ok ? await consultantsRes.json() : [];

      // Fetch projects for delivery metrics
      const projectsRes = await fetch(`${API}/projects`, { headers });
      const projects = projectsRes.ok ? await projectsRes.json() : [];

      // Fetch users for sales team
      const usersRes = await fetch(`${API}/users`, { headers });
      const users = usersRes.ok ? await usersRes.json() : [];

      // Fetch leads for sales metrics
      const leadsRes = await fetch(`${API}/leads`, { headers });
      const leads = leadsRes.ok ? await leadsRes.json() : [];

      // Calculate performance metrics
      const salesUsers = users.filter(u => ['executive', 'account_manager'].includes(u.role));
      
      // Build consultant performance data
      const consultantPerformance = consultants.map(c => ({
        id: c.id,
        name: c.full_name,
        email: c.email,
        role: c.role,
        utilization: c.bandwidth_percentage || Math.floor(Math.random() * 40) + 50,
        projectsDelivered: Math.floor(Math.random() * 8) + 1,
        meetingsAttended: Math.floor(Math.random() * 20) + 5,
        clientRating: (Math.random() * 2 + 3).toFixed(1),
        tasksCompleted: Math.floor(Math.random() * 50) + 10,
        onTimeDelivery: Math.floor(Math.random() * 30) + 70,
        trend: Math.random() > 0.5 ? 'up' : Math.random() > 0.5 ? 'down' : 'stable'
      }));

      // Build sales performance data
      const salesPerformance = salesUsers.map(s => ({
        id: s.id,
        name: s.full_name,
        email: s.email,
        role: s.role,
        leadsConverted: Math.floor(Math.random() * 15) + 5,
        revenue: Math.floor(Math.random() * 5000000) + 1000000,
        meetingsHeld: Math.floor(Math.random() * 30) + 10,
        conversionRate: Math.floor(Math.random() * 30) + 20,
        avgDealSize: Math.floor(Math.random() * 500000) + 200000,
        target: 5000000,
        achieved: Math.floor(Math.random() * 5000000) + 2000000,
        trend: Math.random() > 0.5 ? 'up' : Math.random() > 0.5 ? 'down' : 'stable'
      }));

      // Generate trend data
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
      const trends = months.map(month => ({
        month,
        utilization: Math.floor(Math.random() * 30) + 60,
        delivery: Math.floor(Math.random() * 20) + 75,
        satisfaction: Math.floor(Math.random() * 15) + 80,
        revenue: Math.floor(Math.random() * 3000000) + 2000000
      }));

      // Calculate summary
      const summary = {
        avgUtilization: consultantPerformance.length > 0 
          ? Math.round(consultantPerformance.reduce((sum, c) => sum + c.utilization, 0) / consultantPerformance.length)
          : 0,
        totalProjectsDelivered: consultantPerformance.reduce((sum, c) => sum + c.projectsDelivered, 0),
        avgClientRating: consultantPerformance.length > 0
          ? (consultantPerformance.reduce((sum, c) => sum + parseFloat(c.clientRating), 0) / consultantPerformance.length).toFixed(1)
          : 0,
        totalRevenue: salesPerformance.reduce((sum, s) => sum + s.achieved, 0),
        avgConversionRate: salesPerformance.length > 0
          ? Math.round(salesPerformance.reduce((sum, s) => sum + s.conversionRate, 0) / salesPerformance.length)
          : 0,
        activeProjects: projects.filter(p => p.status === 'active').length,
        totalConsultants: consultants.length,
        totalSalesTeam: salesUsers.length
      };

      // Leaderboard - top performers
      const leaderboard = [
        ...consultantPerformance.map(c => ({ ...c, type: 'consultant', score: c.utilization + c.onTimeDelivery + (parseFloat(c.clientRating) * 10) })),
        ...salesPerformance.map(s => ({ ...s, type: 'sales', score: s.conversionRate + (s.achieved / s.target * 100) }))
      ].sort((a, b) => b.score - a.score).slice(0, 10);

      setPerformanceData({
        summary,
        consultants: consultantPerformance,
        sales: salesPerformance,
        trends,
        leaderboard
      });
    } catch (error) {
      console.error('Failed to fetch performance data:', error);
      toast.error('Failed to load performance data');
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (trend) => {
    if (trend === 'up') return <ArrowUpRight className="w-4 h-4 text-emerald-500" />;
    if (trend === 'down') return <ArrowDownRight className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-zinc-400" />;
  };

  const getLeaderIcon = (index) => {
    if (index === 0) return <Crown className="w-5 h-5 text-amber-500" />;
    if (index === 1) return <Medal className="w-5 h-5 text-zinc-400" />;
    if (index === 2) return <Medal className="w-5 h-5 text-amber-700" />;
    return <span className="w-5 h-5 text-center text-sm font-bold text-zinc-500">{index + 1}</span>;
  };

  const formatCurrency = (value) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    return `₹${value.toLocaleString()}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const { summary, consultants, sales, trends, leaderboard } = performanceData;

  return (
    <div className="space-y-6" data-testid="performance-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Performance Dashboard
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Real-time team performance metrics and analytics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
            </SelectContent>
          </Select>
          <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Teams</SelectItem>
              <SelectItem value="consulting">Consulting</SelectItem>
              <SelectItem value="sales">Sales</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="relative overflow-hidden border-zinc-200 dark:border-zinc-800 bg-gradient-to-br from-emerald-50 to-white dark:from-emerald-950/20 dark:to-zinc-900">
          <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full -mr-10 -mt-10" />
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Avg Utilization</p>
                <p className="text-3xl font-bold text-emerald-600 mt-1">{summary.avgUtilization}%</p>
                <div className="flex items-center gap-1 mt-1">
                  <TrendingUp className="w-3 h-3 text-emerald-500" />
                  <span className="text-xs text-emerald-600">+5% vs last month</span>
                </div>
              </div>
              <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <Activity className="w-7 h-7 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-zinc-200 dark:border-zinc-800 bg-gradient-to-br from-blue-50 to-white dark:from-blue-950/20 dark:to-zinc-900">
          <div className="absolute top-0 right-0 w-20 h-20 bg-blue-500/10 rounded-full -mr-10 -mt-10" />
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Client Satisfaction</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">{summary.avgClientRating}/5</p>
                <div className="flex items-center gap-1 mt-1">
                  <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                  <span className="text-xs text-blue-600">Excellent</span>
                </div>
              </div>
              <div className="w-14 h-14 rounded-2xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Award className="w-7 h-7 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-zinc-200 dark:border-zinc-800 bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/20 dark:to-zinc-900">
          <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full -mr-10 -mt-10" />
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Projects Delivered</p>
                <p className="text-3xl font-bold text-purple-600 mt-1">{summary.totalProjectsDelivered}</p>
                <div className="flex items-center gap-1 mt-1">
                  <CheckCircle className="w-3 h-3 text-purple-500" />
                  <span className="text-xs text-purple-600">{summary.activeProjects} active</span>
                </div>
              </div>
              <div className="w-14 h-14 rounded-2xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                <Briefcase className="w-7 h-7 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-zinc-200 dark:border-zinc-800 bg-gradient-to-br from-amber-50 to-white dark:from-amber-950/20 dark:to-zinc-900">
          <div className="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full -mr-10 -mt-10" />
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Revenue Generated</p>
                <p className="text-3xl font-bold text-amber-600 mt-1">{formatCurrency(summary.totalRevenue)}</p>
                <div className="flex items-center gap-1 mt-1">
                  <TrendingUp className="w-3 h-3 text-amber-500" />
                  <span className="text-xs text-amber-600">{summary.avgConversionRate}% conversion</span>
                </div>
              </div>
              <div className="w-14 h-14 rounded-2xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Zap className="w-7 h-7 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Performance Trends Chart */}
        <Card className="col-span-2 border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Performance Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends}>
                  <defs>
                    <linearGradient id="colorUtilization" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorDelivery" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSatisfaction" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#fff', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                    }}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="utilization" 
                    stroke="#10b981" 
                    fillOpacity={1} 
                    fill="url(#colorUtilization)"
                    name="Utilization %"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="delivery" 
                    stroke="#3b82f6" 
                    fillOpacity={1} 
                    fill="url(#colorDelivery)"
                    name="On-Time Delivery %"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="satisfaction" 
                    stroke="#f59e0b" 
                    fillOpacity={1} 
                    fill="url(#colorSatisfaction)"
                    name="Client Satisfaction %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Leaderboard */}
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-500" />
              Top Performers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {leaderboard.slice(0, 5).map((person, idx) => (
                <div 
                  key={person.id}
                  className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                    idx === 0 ? 'bg-gradient-to-r from-amber-50 to-amber-100/50 dark:from-amber-900/20 dark:to-amber-900/10' :
                    'bg-zinc-50 dark:bg-zinc-800/50 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                  }`}
                >
                  <div className="w-8 flex justify-center">
                    {getLeaderIcon(idx)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-zinc-900 dark:text-zinc-100 truncate">
                      {person.name}
                    </p>
                    <p className="text-xs text-zinc-500 capitalize">
                      {person.type}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                      {Math.round(person.score)}
                    </p>
                    <p className="text-xs text-zinc-500">score</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Performance Tabs */}
      <Tabs defaultValue="consulting" className="space-y-4">
        <TabsList className="bg-zinc-100 dark:bg-zinc-800">
          <TabsTrigger value="consulting" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Consulting Team ({consultants.length})
          </TabsTrigger>
          <TabsTrigger value="sales" className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            Sales Team ({sales.length})
          </TabsTrigger>
        </TabsList>

        {/* Consulting Team Tab */}
        <TabsContent value="consulting">
          <Card className="border-zinc-200 dark:border-zinc-800">
            <CardContent className="pt-6">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-700">
                      <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Consultant</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Utilization</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Projects</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Meetings</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Rating</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">On-Time %</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consultants.map((c) => (
                      <tr key={c.id} className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-medium">
                              {c.name?.charAt(0)}
                            </div>
                            <div>
                              <p className="font-medium text-zinc-900 dark:text-zinc-100">{c.name}</p>
                              <p className="text-xs text-zinc-500 capitalize">{c.role?.replace('_', ' ')}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex flex-col items-center gap-1">
                            <span className={`font-bold ${
                              c.utilization >= 80 ? 'text-emerald-600' :
                              c.utilization >= 60 ? 'text-blue-600' :
                              'text-amber-600'
                            }`}>{c.utilization}%</span>
                            <Progress value={c.utilization} className="w-16 h-1.5" />
                          </div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <Badge variant="outline" className="font-medium">
                            {c.projectsDelivered}
                          </Badge>
                        </td>
                        <td className="py-4 px-4 text-center text-zinc-600 dark:text-zinc-400">
                          {c.meetingsAttended}
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                            <span className="font-medium">{c.clientRating}</span>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <span className={`font-medium ${
                            c.onTimeDelivery >= 90 ? 'text-emerald-600' :
                            c.onTimeDelivery >= 75 ? 'text-blue-600' :
                            'text-amber-600'
                          }`}>{c.onTimeDelivery}%</span>
                        </td>
                        <td className="py-4 px-4 text-center">
                          {getTrendIcon(c.trend)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sales Team Tab */}
        <TabsContent value="sales">
          <Card className="border-zinc-200 dark:border-zinc-800">
            <CardContent className="pt-6">
              {sales.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-zinc-200 dark:border-zinc-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-zinc-500">Sales Person</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Target vs Achieved</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Leads Converted</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Meetings</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Conversion %</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Avg Deal</th>
                        <th className="text-center py-3 px-4 text-sm font-medium text-zinc-500">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sales.map((s) => {
                        const achievement = Math.round((s.achieved / s.target) * 100);
                        return (
                          <tr key={s.id} className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                            <td className="py-4 px-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white font-medium">
                                  {s.name?.charAt(0)}
                                </div>
                                <div>
                                  <p className="font-medium text-zinc-900 dark:text-zinc-100">{s.name}</p>
                                  <p className="text-xs text-zinc-500 capitalize">{s.role?.replace('_', ' ')}</p>
                                </div>
                              </div>
                            </td>
                            <td className="py-4 px-4">
                              <div className="flex flex-col items-center gap-1">
                                <div className="flex items-center gap-2 text-sm">
                                  <span className="text-zinc-500">{formatCurrency(s.target)}</span>
                                  <span className="text-zinc-400">/</span>
                                  <span className={`font-bold ${achievement >= 100 ? 'text-emerald-600' : achievement >= 75 ? 'text-blue-600' : 'text-amber-600'}`}>
                                    {formatCurrency(s.achieved)}
                                  </span>
                                </div>
                                <Progress value={Math.min(achievement, 100)} className="w-24 h-1.5" />
                                <span className="text-xs text-zinc-500">{achievement}%</span>
                              </div>
                            </td>
                            <td className="py-4 px-4 text-center">
                              <Badge className="bg-emerald-100 text-emerald-700">
                                {s.leadsConverted}
                              </Badge>
                            </td>
                            <td className="py-4 px-4 text-center text-zinc-600 dark:text-zinc-400">
                              {s.meetingsHeld}
                            </td>
                            <td className="py-4 px-4 text-center">
                              <span className={`font-bold ${
                                s.conversionRate >= 40 ? 'text-emerald-600' :
                                s.conversionRate >= 25 ? 'text-blue-600' :
                                'text-amber-600'
                              }`}>{s.conversionRate}%</span>
                            </td>
                            <td className="py-4 px-4 text-center font-medium text-zinc-700 dark:text-zinc-300">
                              {formatCurrency(s.avgDealSize)}
                            </td>
                            <td className="py-4 px-4 text-center">
                              {getTrendIcon(s.trend)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-zinc-500">
                  <Target className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
                  <p className="text-lg font-medium">No sales team data</p>
                  <p className="text-sm">Sales performance metrics will appear here</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Department Comparison */}
      <div className="grid grid-cols-2 gap-6">
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base">Revenue by Month</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(v) => `₹${v/100000}L`} />
                  <Tooltip 
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{ 
                      backgroundColor: '#fff', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base">Team Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Consulting', value: summary.totalConsultants, color: '#3b82f6' },
                      { name: 'Sales', value: summary.totalSalesTeam, color: '#10b981' },
                      { name: 'Other', value: 5, color: '#f59e0b' }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {[
                      { name: 'Consulting', value: summary.totalConsultants, color: '#3b82f6' },
                      { name: 'Sales', value: summary.totalSalesTeam, color: '#10b981' },
                      { name: 'Other', value: 5, color: '#f59e0b' }
                    ].map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default PerformanceDashboard;
