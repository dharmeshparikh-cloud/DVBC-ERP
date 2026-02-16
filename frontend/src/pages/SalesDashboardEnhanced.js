import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { 
  TrendingUp, Users, FileText, CheckCircle, Clock, Flame,
  DollarSign, Target, ArrowRight, Send, Building2, BarChart3,
  Calendar, Award, TrendingDown, Thermometer, PieChart
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { 
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, Area, AreaChart
} from 'recharts';

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#f59e0b', '#ec4899'];

const SalesDashboardEnhanced = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const location = useLocation();
  const isSalesPortal = location.pathname.startsWith('/sales');
  
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('own');

  useEffect(() => {
    fetchStats();
  }, [viewMode]);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API}/stats/sales-dashboard-enhanced?view_mode=${viewMode}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch sales stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
    return `₹${value}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  const pipeline = stats?.pipeline || {};
  const temperature = stats?.temperature || {};
  const meetings = stats?.meetings || {};
  const ratios = stats?.ratios || {};
  const closures = stats?.closures || {};
  const targets = stats?.targets || {};
  const momData = stats?.mom_performance || [];
  const leadSources = stats?.lead_sources || [];
  const leaderboard = stats?.leaderboard || [];

  // Prepare pie chart data for lead status
  const statusPieData = [
    { name: 'New', value: pipeline.new || 0 },
    { name: 'Contacted', value: pipeline.contacted || 0 },
    { name: 'Qualified', value: pipeline.qualified || 0 },
    { name: 'Proposal', value: pipeline.proposal || 0 },
    { name: 'Agreement', value: pipeline.agreement || 0 },
    { name: 'Closed', value: pipeline.closed || 0 },
  ].filter(d => d.value > 0);

  // Temperature pie data
  const tempPieData = [
    { name: 'Hot', value: temperature.hot || 0, color: '#ef4444' },
    { name: 'Warm', value: temperature.warm || 0, color: '#f97316' },
    { name: 'Cold', value: temperature.cold || 0, color: '#3b82f6' },
  ].filter(d => d.value > 0);

  // Source pie data
  const sourcePieData = leadSources.slice(0, 6).map((s, i) => ({
    name: s.source || 'Unknown',
    value: s.count,
    color: COLORS[i % COLORS.length]
  }));

  return (
    <div className="space-y-6" data-testid="sales-dashboard-enhanced">
      {/* Header with View Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>Sales Dashboard</h1>
          <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>Track your pipeline, conversions and revenue</p>
        </div>
        <div className="flex items-center gap-3">
          {stats?.has_team && (
            <div className={`flex rounded-lg p-1 ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
              <button
                onClick={() => setViewMode('own')}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  viewMode === 'own' 
                    ? isDark ? 'bg-zinc-700 shadow text-zinc-100' : 'bg-white shadow text-zinc-900'
                    : isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                My Data
              </button>
              <button
                onClick={() => setViewMode('team')}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  viewMode === 'team' 
                    ? isDark ? 'bg-zinc-700 shadow text-zinc-100' : 'bg-white shadow text-zinc-900'
                    : isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                Team Data
              </button>
            </div>
          )}
          <Badge className={`text-sm px-3 py-1 ${isDark ? 'bg-orange-500/20 text-orange-400' : 'bg-orange-100 text-orange-700'}`}>
            {ratios.lead_to_closure || 0}% Conversion
          </Badge>
        </div>
      </div>

      {/* KPI Scorecards Row */}
      <div className="grid grid-cols-6 gap-4">
        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-orange-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-orange-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Leads</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{pipeline.total || 0}</p>
              </div>
              <Users className="w-8 h-8 text-orange-500 opacity-80" />
            </div>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-blue-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-blue-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Meetings</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{meetings.total || 0}</p>
              </div>
              <Calendar className="w-8 h-8 text-blue-500 opacity-80" />
            </div>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{meetings.this_month || 0} this month</p>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-green-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-green-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Closures</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{closures.total || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500 opacity-80" />
            </div>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{closures.this_month || 0} this month</p>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-purple-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-purple-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Deal Value</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{formatCurrency(stats?.deal_value?.total || 0)}</p>
              </div>
              <DollarSign className="w-8 h-8 text-purple-500 opacity-80" />
            </div>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-cyan-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-cyan-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Lead→Meeting</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{ratios.lead_to_meeting || 0}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-cyan-500 opacity-80" />
            </div>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-gradient-to-br from-rose-500/20 to-zinc-800' : 'border-zinc-200 bg-gradient-to-br from-rose-50 to-white'}`}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs uppercase tracking-wide ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Lead→Closure</p>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{ratios.lead_to_closure || 0}%</p>
              </div>
              <Target className="w-8 h-8 text-rose-500 opacity-80" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Funnel */}
      <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
        <CardHeader className="pb-2">
          <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <Target className="w-4 h-4" />
            Sales Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-7 gap-2">
            {[
              { label: 'New', count: pipeline.new, color: isDark ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-700' },
              { label: 'Contacted', count: pipeline.contacted, color: isDark ? 'bg-blue-900/50 text-blue-300' : 'bg-blue-100 text-blue-700' },
              { label: 'Qualified', count: pipeline.qualified, color: isDark ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700' },
              { label: 'Proposal', count: pipeline.proposal, color: isDark ? 'bg-purple-900/50 text-purple-300' : 'bg-purple-100 text-purple-700' },
              { label: 'Agreement', count: pipeline.agreement, color: isDark ? 'bg-amber-900/50 text-amber-300' : 'bg-amber-100 text-amber-700' },
              { label: 'Closed', count: pipeline.closed, color: isDark ? 'bg-green-900/50 text-green-300' : 'bg-green-100 text-green-700' },
              { label: 'Total', count: pipeline.total, color: isDark ? 'bg-zinc-600 text-white' : 'bg-zinc-900 text-white' },
            ].map((stage, i) => (
              <div key={i} className="text-center">
                <div className={`rounded-lg py-3 px-2 ${stage.color}`}>
                  <p className="text-2xl font-bold">{stage.count || 0}</p>
                  <p className="text-xs mt-1">{stage.label}</p>
                </div>
                {i < 6 && (
                  <ArrowRight className={`w-4 h-4 mx-auto mt-2 ${isDark ? 'text-zinc-600' : 'text-zinc-300'}`} />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-4">
        {/* Lead Temperature Pie */}
        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <Thermometer className="w-4 h-4" />
              Lead Temperature
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={tempPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {tempPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 mt-2">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Hot ({temperature.hot || 0})</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                <span className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Warm ({temperature.warm || 0})</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Cold ({temperature.cold || 0})</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Lead Status Distribution */}
        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <PieChart className="w-4 h-4" />
              Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={statusPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {statusPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend 
                    layout="horizontal" 
                    verticalAlign="bottom" 
                    align="center"
                    wrapperStyle={{ fontSize: '10px', color: isDark ? '#a1a1aa' : '#52525b' }}
                  />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Lead Sources */}
        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-2">
            <CardTitle className={`text-sm flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <BarChart3 className="w-4 h-4" />
              Lead Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={sourcePieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {sourcePieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend 
                    layout="horizontal" 
                    verticalAlign="bottom" 
                    align="center"
                    wrapperStyle={{ fontSize: '10px', color: isDark ? '#a1a1aa' : '#52525b' }}
                  />
                </RechartsPie>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Targets vs Achievement */}
      <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
        <CardHeader className="pb-2">
          <CardTitle className={`text-sm flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <Target className="w-4 h-4" />
            Targets vs Achievement (This Month)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-6">
            {/* Meeting Target */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Meetings</span>
                <span className={`text-sm font-medium ${isDark ? 'text-zinc-200' : ''}`}>
                  {targets.meeting_actual || 0} / {targets.meeting_target || 0}
                </span>
              </div>
              <Progress 
                value={targets.meeting_achievement || 0} 
                className={`h-3 ${isDark ? 'bg-zinc-700' : 'bg-zinc-100'}`}
              />
              <p className={`text-xs text-right ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                {targets.meeting_achievement || 0}% achieved
              </p>
            </div>

            {/* Conversion Target */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-zinc-600">Conversions</span>
                <span className="text-sm font-medium">
                  {targets.conversion_actual || 0} / {targets.conversion_target || 0}
                </span>
              </div>
              <Progress 
                value={targets.conversion_target > 0 ? (targets.conversion_actual / targets.conversion_target * 100) : 0} 
                className="h-3 bg-zinc-100"
              />
              <p className="text-xs text-zinc-500 text-right">
                {targets.conversion_target > 0 ? Math.round(targets.conversion_actual / targets.conversion_target * 100) : 0}% achieved
              </p>
            </div>

            {/* Value Target */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-zinc-600">Deal Value</span>
                <span className="text-sm font-medium">
                  {formatCurrency(targets.value_actual || 0)} / {formatCurrency(targets.value_target || 0)}
                </span>
              </div>
              <Progress 
                value={targets.value_target > 0 ? (targets.value_actual / targets.value_target * 100) : 0} 
                className="h-3 bg-zinc-100"
              />
              <p className="text-xs text-zinc-500 text-right">
                {targets.value_target > 0 ? Math.round(targets.value_actual / targets.value_target * 100) : 0}% achieved
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Month over Month Performance */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Monthly Performance Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={momData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Area 
                    type="monotone" 
                    dataKey="leads" 
                    stackId="1"
                    stroke="#f97316" 
                    fill="#fed7aa" 
                    name="Leads"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="meetings" 
                    stackId="2"
                    stroke="#3b82f6" 
                    fill="#bfdbfe" 
                    name="Meetings"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="closures" 
                    stackId="3"
                    stroke="#10b981" 
                    fill="#a7f3d0" 
                    name="Closures"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Conversion Rate Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={momData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Line 
                    type="monotone" 
                    dataKey="conversion_rate" 
                    stroke="#8b5cf6" 
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    name="Conversion Rate"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Team Leaderboard & Quick Actions */}
      <div className="grid grid-cols-3 gap-4">
        {/* Leaderboard */}
        {viewMode !== 'own' && leaderboard.length > 0 && (
          <Card className="border-zinc-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Award className="w-4 h-4" />
                Team Leaderboard
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {leaderboard.slice(0, 5).map((member, idx) => (
                  <div key={member.user_id} className="flex items-center justify-between py-2 border-b border-zinc-100 last:border-0">
                    <div className="flex items-center gap-2">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                        idx === 1 ? 'bg-gray-100 text-gray-700' :
                        idx === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-zinc-50 text-zinc-600'
                      }`}>
                        {idx + 1}
                      </span>
                      <span className="text-sm text-zinc-700">{member.name}</span>
                    </div>
                    <Badge variant="secondary" className="bg-green-50 text-green-700">
                      {member.closures} closures
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* MOM Completion */}
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileText className="w-4 h-4" />
              MOM Completion
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-4">
              <div className="relative inline-flex items-center justify-center">
                <svg className="w-24 h-24">
                  <circle
                    className="text-zinc-100"
                    strokeWidth="8"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="48"
                    cy="48"
                  />
                  <circle
                    className="text-orange-500"
                    strokeWidth="8"
                    strokeDasharray={251.2}
                    strokeDashoffset={251.2 - (251.2 * (meetings.mom_completion_rate || 0)) / 100}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="48"
                    cy="48"
                    transform="rotate(-90 48 48)"
                  />
                </svg>
                <span className="absolute text-xl font-bold text-zinc-900">
                  {meetings.mom_completion_rate || 0}%
                </span>
              </div>
              <p className="text-sm text-zinc-500 mt-2">
                {meetings.with_mom || 0} of {meetings.total || 0} meetings
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              <Link to={isSalesPortal ? "/sales/leads" : "/leads"}>
                <Button variant="outline" className="w-full h-16 flex flex-col items-center justify-center gap-1 hover:bg-orange-50 hover:border-orange-200">
                  <Users className="w-5 h-5 text-orange-500" />
                  <span className="text-xs">New Lead</span>
                </Button>
              </Link>
              <Link to={isSalesPortal ? "/sales/meetings" : "/sales-meetings"}>
                <Button variant="outline" className="w-full h-16 flex flex-col items-center justify-center gap-1 hover:bg-blue-50 hover:border-blue-200">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  <span className="text-xs">Schedule Meeting</span>
                </Button>
              </Link>
              <Link to={isSalesPortal ? "/sales/quotations" : "/sales-funnel/quotations"}>
                <Button variant="outline" className="w-full h-16 flex flex-col items-center justify-center gap-1 hover:bg-purple-50 hover:border-purple-200">
                  <FileText className="w-5 h-5 text-purple-500" />
                  <span className="text-xs">Quotation</span>
                </Button>
              </Link>
              <Link to={isSalesPortal ? "/sales/kickoff-requests" : "/kickoff-requests"}>
                <Button variant="outline" className="w-full h-16 flex flex-col items-center justify-center gap-1 hover:bg-green-50 hover:border-green-200">
                  <Send className="w-5 h-5 text-green-500" />
                  <span className="text-xs">Send Kickoff</span>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Kickoffs Alert */}
      {stats?.kickoffs_pending > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-orange-600" />
                <span className="text-sm text-orange-800">
                  <strong>{stats.kickoffs_pending}</strong> kickoff requests pending PM acceptance
                </span>
              </div>
              <Link to={isSalesPortal ? "/sales/kickoff-requests" : "/kickoff-requests"}>
                <Button size="sm" variant="outline" className="border-orange-300 text-orange-700 hover:bg-orange-100">
                  View All
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SalesDashboardEnhanced;
