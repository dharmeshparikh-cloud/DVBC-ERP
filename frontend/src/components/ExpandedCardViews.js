import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { 
  TrendingUp, TrendingDown, DollarSign, Users, Calendar, CheckCircle,
  Briefcase, Clock, ArrowUpRight, ArrowDownRight, Building2, Target,
  Flame, AlertCircle, FileText, BarChart3
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#f59e0b'];

// Revenue Drill-down Component
export const RevenueExpanded = ({ data, isDark }) => {
  const monthlyRevenue = [
    { month: 'Jul', revenue: 3200000, target: 3000000 },
    { month: 'Aug', revenue: 3800000, target: 3500000 },
    { month: 'Sep', revenue: 4100000, target: 4000000 },
    { month: 'Oct', revenue: 3900000, target: 4000000 },
    { month: 'Nov', revenue: 4500000, target: 4500000 },
    { month: 'Dec', revenue: 4800000, target: 5000000 },
  ];

  const revenueByDept = [
    { name: 'Consulting', value: 25000000, percent: 55.5 },
    { name: 'Training', value: 12000000, percent: 26.7 },
    { name: 'Support', value: 8000000, percent: 17.8 },
  ];

  const formatCurrency = (val) => {
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    return `₹${val}`;
  };

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      {/* Main Chart */}
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Monthly Revenue vs Target
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={monthlyRevenue}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
            <XAxis dataKey="month" stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} tickFormatter={formatCurrency} />
            <Tooltip 
              formatter={(value) => formatCurrency(value)}
              contentStyle={{ 
                backgroundColor: isDark ? '#18181b' : '#fff',
                border: isDark ? '1px solid #3f3f46' : '1px solid #e5e7eb'
              }}
            />
            <Legend />
            <Bar dataKey="revenue" fill="#10b981" name="Revenue" radius={[4, 4, 0, 0]} />
            <Bar dataKey="target" fill="#3b82f6" name="Target" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        {/* YoY Comparison */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50'}>
            <CardContent className="pt-4">
              <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>vs Last Year</p>
              <p className="text-2xl font-bold text-green-500 flex items-center gap-1">
                <ArrowUpRight className="w-5 h-5" />
                +23.5%
              </p>
            </CardContent>
          </Card>
          <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50'}>
            <CardContent className="pt-4">
              <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>vs Target</p>
              <p className="text-2xl font-bold text-amber-500 flex items-center gap-1">
                <ArrowDownRight className="w-5 h-5" />
                -4.2%
              </p>
            </CardContent>
          </Card>
          <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50'}>
            <CardContent className="pt-4">
              <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Avg Deal Size</p>
              <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>₹5.3L</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Sidebar Stats */}
      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Revenue by Department
        </h3>
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={revenueByDept}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="value"
            >
              {revenueByDept.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatCurrency(value)} />
          </PieChart>
        </ResponsiveContainer>
        
        <div className="space-y-2">
          {revenueByDept.map((dept, i) => (
            <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${
              isDark ? 'bg-zinc-800' : 'bg-zinc-100'
            }`}>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS[i] }} />
                <span className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>{dept.name}</span>
              </div>
              <div className="text-right">
                <p className={`font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {formatCurrency(dept.value)}
                </p>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                  {dept.percent}%
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Active Leads Drill-down Component
export const LeadsExpanded = ({ data, isDark }) => {
  const leadsByStatus = [
    { status: 'New', count: 120, color: '#6b7280' },
    { status: 'Contacted', count: 85, color: '#3b82f6' },
    { status: 'Qualified', count: 64, color: '#8b5cf6' },
    { status: 'Proposal', count: 42, color: '#f59e0b' },
    { status: 'Negotiation', count: 28, color: '#ec4899' },
    { status: 'Closed', count: 25, color: '#10b981' },
  ];

  const leadsBySource = [
    { source: 'Website', count: 145, percent: 39.7 },
    { source: 'Referral', count: 98, percent: 26.8 },
    { source: 'LinkedIn', count: 65, percent: 17.8 },
    { source: 'Events', count: 42, percent: 11.5 },
    { source: 'Cold Call', count: 14, percent: 3.8 },
  ];

  const recentLeads = [
    { name: 'Acme Corp', source: 'Website', status: 'New', value: '₹12L', time: '2h ago' },
    { name: 'TechStart Inc', source: 'Referral', status: 'Contacted', value: '₹8L', time: '4h ago' },
    { name: 'Global Solutions', source: 'LinkedIn', status: 'Qualified', value: '₹25L', time: '1d ago' },
    { name: 'InnovateCo', source: 'Events', status: 'Proposal', value: '₹15L', time: '2d ago' },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      {/* Funnel */}
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Lead Conversion Funnel
        </h3>
        <div className="space-y-2">
          {leadsByStatus.map((stage, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className={`w-24 text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                {stage.status}
              </div>
              <div className="flex-1 h-10 bg-zinc-200 dark:bg-zinc-700 rounded-lg overflow-hidden">
                <div 
                  className="h-full flex items-center justify-end pr-3 text-white font-semibold"
                  style={{ 
                    width: `${(stage.count / 120) * 100}%`,
                    backgroundColor: stage.color 
                  }}
                >
                  {stage.count}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Leads Table */}
        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Recent Leads
        </h3>
        <div className={`rounded-lg border overflow-hidden ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
          <table className="w-full">
            <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-100'}>
              <tr>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Company</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Source</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Status</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Value</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Added</th>
              </tr>
            </thead>
            <tbody>
              {recentLeads.map((lead, i) => (
                <tr key={i} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <td className={`px-4 py-3 ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{lead.name}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{lead.source}</td>
                  <td className="px-4 py-3">
                    <Badge variant="secondary" className="text-xs">{lead.status}</Badge>
                  </td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{lead.value}</td>
                  <td className={`px-4 py-3 text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>{lead.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <div>
          <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Leads by Source
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={leadsBySource}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
                dataKey="count"
              >
                {leadsBySource.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {leadsBySource.map((src, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                  <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>{src.source}</span>
                </div>
                <span className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>{src.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Stats */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-orange-50'}`}>
          <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>This Week</p>
          <p className={`text-3xl font-bold ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>+28</p>
          <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>new leads added</p>
        </div>
      </div>
    </div>
  );
};

// Meetings Today Drill-down Component
export const MeetingsExpanded = ({ data, isDark }) => {
  const todaysMeetings = [
    { time: '09:00 AM', title: 'Discovery Call - Acme Corp', attendees: 3, status: 'completed', type: 'Sales' },
    { time: '10:30 AM', title: 'Project Review - TechStart', attendees: 5, status: 'completed', type: 'Consulting' },
    { time: '02:00 PM', title: 'Proposal Discussion - Global', attendees: 4, status: 'ongoing', type: 'Sales' },
    { time: '03:30 PM', title: 'Team Standup', attendees: 8, status: 'upcoming', type: 'Internal' },
    { time: '04:30 PM', title: 'Client Demo - InnovateCo', attendees: 6, status: 'upcoming', type: 'Sales' },
  ];

  const weeklyStats = [
    { day: 'Mon', meetings: 6 },
    { day: 'Tue', meetings: 8 },
    { day: 'Wed', meetings: 5 },
    { day: 'Thu', meetings: 9 },
    { day: 'Fri', meetings: 4 },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      {/* Today's Schedule */}
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Today's Schedule
        </h3>
        <div className="space-y-3">
          {todaysMeetings.map((meeting, i) => (
            <div 
              key={i}
              className={`flex items-center gap-4 p-4 rounded-lg border ${
                meeting.status === 'ongoing' 
                  ? 'border-blue-500 bg-blue-500/10' 
                  : isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200 bg-white'
              }`}
            >
              <div className={`text-sm font-mono ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                {meeting.time}
              </div>
              <div className="flex-1">
                <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {meeting.title}
                </p>
                <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                  {meeting.attendees} attendees • {meeting.type}
                </p>
              </div>
              <Badge 
                className={
                  meeting.status === 'completed' ? 'bg-green-100 text-green-700' :
                  meeting.status === 'ongoing' ? 'bg-blue-100 text-blue-700' :
                  'bg-zinc-100 text-zinc-700'
                }
              >
                {meeting.status}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Weekly Overview */}
      <div className="space-y-6">
        <div>
          <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            This Week
          </h3>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={weeklyStats}>
              <XAxis dataKey="day" stroke={isDark ? '#a1a1aa' : '#6b7280'} fontSize={12} />
              <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} fontSize={12} />
              <Tooltip />
              <Bar dataKey="meetings" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>32</p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>This Week</p>
          </div>
          <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-green-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>89%</p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Attendance</p>
          </div>
          <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-purple-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>45m</p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Avg Duration</p>
          </div>
          <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-amber-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>12</p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>With MOM</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Project Health Drill-down Component
export const ProjectsExpanded = ({ data, isDark }) => {
  const projects = [
    { name: 'Digital Transformation - ACME', progress: 75, status: 'on-track', team: 5, deadline: 'Jan 15' },
    { name: 'ERP Implementation - TechCo', progress: 45, status: 'at-risk', team: 8, deadline: 'Feb 28' },
    { name: 'Cloud Migration - GlobalInc', progress: 90, status: 'on-track', team: 4, deadline: 'Dec 30' },
    { name: 'Security Audit - FinServ', progress: 30, status: 'delayed', team: 3, deadline: 'Dec 20' },
    { name: 'Process Optimization - ManuCo', progress: 60, status: 'on-track', team: 6, deadline: 'Jan 31' },
  ];

  const utilizationByTeam = [
    { team: 'Dev Team', utilization: 92 },
    { team: 'Consulting', utilization: 87 },
    { team: 'Support', utilization: 78 },
    { team: 'Design', utilization: 85 },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      {/* Projects List */}
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Active Projects
        </h3>
        <div className="space-y-3">
          {projects.map((project, i) => (
            <div 
              key={i}
              className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200 bg-white'}`}
            >
              <div className="flex items-center justify-between mb-2">
                <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {project.name}
                </p>
                <Badge 
                  className={
                    project.status === 'on-track' ? 'bg-green-100 text-green-700' :
                    project.status === 'at-risk' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'
                  }
                >
                  {project.status.replace('-', ' ')}
                </Badge>
              </div>
              <div className="flex items-center gap-4 mb-2">
                <div className="flex-1 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${
                      project.status === 'on-track' ? 'bg-green-500' :
                      project.status === 'at-risk' ? 'bg-amber-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${project.progress}%` }}
                  />
                </div>
                <span className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  {project.progress}%
                </span>
              </div>
              <div className={`flex items-center gap-4 text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                <span><Users className="w-4 h-4 inline mr-1" />{project.team} members</span>
                <span><Calendar className="w-4 h-4 inline mr-1" />Due {project.deadline}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Team Utilization */}
      <div className="space-y-6">
        <div>
          <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Team Utilization
          </h3>
          <div className="space-y-4">
            {utilizationByTeam.map((team, i) => (
              <div key={i}>
                <div className="flex justify-between mb-1">
                  <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{team.team}</span>
                  <span className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                    {team.utilization}%
                  </span>
                </div>
                <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${
                      team.utilization >= 90 ? 'bg-green-500' :
                      team.utilization >= 80 ? 'bg-blue-500' : 'bg-amber-500'
                    }`}
                    style={{ width: `${team.utilization}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Summary Stats */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-green-50'}`}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>15</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>On Track</p>
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>5</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>At Risk</p>
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-red-400' : 'text-red-600'}`}>3</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Delayed</p>
            </div>
            <div>
              <p className={`text-2xl font-bold ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>8</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Completed</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Team Attendance Drill-down Component
export const AttendanceExpanded = ({ data, isDark }) => {
  const attendanceData = [
    { day: 'Mon', present: 82, absent: 4 },
    { day: 'Tue', present: 80, absent: 6 },
    { day: 'Wed', present: 79, absent: 7 },
    { day: 'Thu', present: 81, absent: 5 },
    { day: 'Fri', present: 78, absent: 8 },
  ];

  const leaveTypes = [
    { type: 'Sick Leave', count: 3, color: '#ef4444' },
    { type: 'Casual Leave', count: 2, color: '#f59e0b' },
    { type: 'Work From Home', count: 2, color: '#3b82f6' },
  ];

  const onLeaveToday = [
    { name: 'John Smith', type: 'Sick Leave', duration: '1 day' },
    { name: 'Sarah Johnson', type: 'Casual Leave', duration: '2 days' },
    { name: 'Mike Brown', type: 'WFH', duration: '1 day' },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      {/* Attendance Chart */}
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Weekly Attendance Trend
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={attendanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
            <XAxis dataKey="day" stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="present" stackId="1" stroke="#10b981" fill="#10b98150" name="Present" />
            <Area type="monotone" dataKey="absent" stackId="1" stroke="#ef4444" fill="#ef444450" name="Absent" />
          </AreaChart>
        </ResponsiveContainer>

        {/* On Leave Table */}
        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          On Leave Today
        </h3>
        <div className={`rounded-lg border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
          <table className="w-full">
            <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-100'}>
              <tr>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Employee</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Leave Type</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {onLeaveToday.map((person, i) => (
                <tr key={i} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <td className={`px-4 py-3 ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{person.name}</td>
                  <td className="px-4 py-3"><Badge variant="secondary">{person.type}</Badge></td>
                  <td className={`px-4 py-3 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{person.duration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <div>
          <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Leave Distribution
          </h3>
          <div className="space-y-3">
            {leaveTypes.map((leave, i) => (
              <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${
                isDark ? 'bg-zinc-800' : 'bg-zinc-100'
              }`}>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded" style={{ backgroundColor: leave.color }} />
                  <span className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>{leave.type}</span>
                </div>
                <span className={`font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{leave.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Attendance Rate Card */}
        <div className={`p-4 rounded-lg text-center ${isDark ? 'bg-emerald-900/30' : 'bg-emerald-50'}`}>
          <p className={`text-4xl font-bold ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>91.8%</p>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Overall Attendance Rate</p>
          <div className="flex items-center justify-center gap-1 mt-2 text-green-500 text-sm">
            <ArrowUpRight className="w-4 h-4" />
            <span>+2.3% from last week</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default {
  RevenueExpanded,
  LeadsExpanded,
  MeetingsExpanded,
  ProjectsExpanded,
  AttendanceExpanded
};
