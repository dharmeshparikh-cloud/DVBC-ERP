import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Progress } from '../../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  TrendingUp, TrendingDown, Users, FileText, DollarSign, Target, 
  Briefcase, Clock, CheckCircle, AlertCircle, Calendar, Award,
  Building2, BarChart3, PieChart, Activity, ArrowUpRight, ArrowDownRight,
  ChevronRight, Zap, Flame, Globe, Settings, Shield, Layers
} from 'lucide-react';
import {
  PieChart as RechartsPie, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, AreaChart, Area, RadialBarChart, RadialBar
} from 'recharts';

// Sample data for mockups
const salesData = {
  totalLeads: 234,
  conversions: 47,
  revenue: 12500000,
  meetingsThisWeek: 18,
  conversionRate: 20.1,
  trend: '+12.5%'
};

const hrData = {
  totalEmployees: 86,
  presentToday: 79,
  onLeave: 7,
  pendingApprovals: 12,
  attendanceRate: 91.8,
  trend: '+2.3%'
};

const consultingData = {
  activeProjects: 23,
  completedThisMonth: 8,
  utilization: 87,
  pendingMilestones: 15,
  clientSatisfaction: 4.6,
  trend: '+5.2%'
};

const financeData = {
  monthlyRevenue: 45000000,
  pendingInvoices: 18,
  receivables: 12500000,
  expenses: 8900000,
  profitMargin: 32,
  trend: '+8.1%'
};

const monthlyTrend = [
  { month: 'Jul', sales: 35, consulting: 28, hr: 85 },
  { month: 'Aug', sales: 42, consulting: 32, hr: 88 },
  { month: 'Sep', sales: 38, consulting: 35, hr: 86 },
  { month: 'Oct', sales: 45, consulting: 38, hr: 90 },
  { month: 'Nov', sales: 52, consulting: 42, hr: 89 },
  { month: 'Dec', sales: 47, consulting: 45, hr: 92 },
];

const projectStatus = [
  { name: 'On Track', value: 15, color: '#10b981' },
  { name: 'At Risk', value: 5, color: '#f59e0b' },
  { name: 'Delayed', value: 3, color: '#ef4444' },
];

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4'];

// ============================================
// STYLE 1: TABBED MODERN DARK
// ============================================
const StyleTabbedDark = () => {
  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-pink-500 bg-clip-text text-transparent">
              Executive Command Center
            </h1>
            <p className="text-zinc-400 mt-1">Real-time business intelligence at a glance</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></span>
              Live Data
            </Badge>
            <span className="text-sm text-zinc-500">Last updated: 2 mins ago</span>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-orange-500/20 to-orange-600/10 border-orange-500/30 backdrop-blur">
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-orange-300 text-sm font-medium">Total Revenue</p>
                  <p className="text-3xl font-bold text-white mt-1">₹4.5Cr</p>
                  <div className="flex items-center gap-1 mt-2 text-green-400 text-sm">
                    <ArrowUpRight className="w-4 h-4" />
                    <span>+12.5% from last month</span>
                  </div>
                </div>
                <div className="p-3 bg-orange-500/20 rounded-xl">
                  <DollarSign className="w-6 h-6 text-orange-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30 backdrop-blur">
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-blue-300 text-sm font-medium">Active Projects</p>
                  <p className="text-3xl font-bold text-white mt-1">23</p>
                  <div className="flex items-center gap-1 mt-2 text-green-400 text-sm">
                    <ArrowUpRight className="w-4 h-4" />
                    <span>+3 new this week</span>
                  </div>
                </div>
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <Briefcase className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 backdrop-blur">
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-emerald-300 text-sm font-medium">Team Strength</p>
                  <p className="text-3xl font-bold text-white mt-1">86</p>
                  <div className="flex items-center gap-1 mt-2 text-zinc-400 text-sm">
                    <Users className="w-4 h-4" />
                    <span>79 present today</span>
                  </div>
                </div>
                <div className="p-3 bg-emerald-500/20 rounded-xl">
                  <Users className="w-6 h-6 text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30 backdrop-blur">
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-purple-300 text-sm font-medium">Pending Actions</p>
                  <p className="text-3xl font-bold text-white mt-1">24</p>
                  <div className="flex items-center gap-1 mt-2 text-amber-400 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    <span>8 urgent approvals</span>
                  </div>
                </div>
                <div className="p-3 bg-purple-500/20 rounded-xl">
                  <Clock className="w-6 h-6 text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabbed Department View */}
        <Tabs defaultValue="sales" className="w-full">
          <TabsList className="bg-zinc-900 border border-zinc-800 p-1">
            <TabsTrigger value="sales" className="data-[state=active]:bg-orange-500 data-[state=active]:text-white">
              <BarChart3 className="w-4 h-4 mr-2" />
              Sales
            </TabsTrigger>
            <TabsTrigger value="consulting" className="data-[state=active]:bg-blue-500 data-[state=active]:text-white">
              <Briefcase className="w-4 h-4 mr-2" />
              Consulting
            </TabsTrigger>
            <TabsTrigger value="hr" className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white">
              <Users className="w-4 h-4 mr-2" />
              HR
            </TabsTrigger>
            <TabsTrigger value="finance" className="data-[state=active]:bg-purple-500 data-[state=active]:text-white">
              <DollarSign className="w-4 h-4 mr-2" />
              Finance
            </TabsTrigger>
          </TabsList>

          <TabsContent value="sales" className="mt-4">
            <div className="grid grid-cols-3 gap-4">
              <Card className="col-span-2 bg-zinc-900/50 border-zinc-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg text-zinc-100 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-orange-400" />
                    Sales Pipeline Trend
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={250}>
                    <AreaChart data={monthlyTrend}>
                      <defs>
                        <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="month" stroke="#666" />
                      <YAxis stroke="#666" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                        labelStyle={{ color: '#fff' }}
                      />
                      <Area type="monotone" dataKey="sales" stroke="#f97316" fill="url(#salesGradient)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg text-zinc-100">Key Metrics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Leads This Month</span>
                    <span className="text-xl font-bold text-white">234</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Conversion Rate</span>
                    <span className="text-xl font-bold text-green-400">20.1%</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Avg Deal Size</span>
                    <span className="text-xl font-bold text-orange-400">₹5.3L</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Hot Leads</span>
                    <span className="text-xl font-bold text-red-400">47</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="consulting" className="mt-4">
            <div className="grid grid-cols-3 gap-4">
              <Card className="col-span-2 bg-zinc-900/50 border-zinc-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg text-zinc-100 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-blue-400" />
                    Project Status Overview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-8">
                    <ResponsiveContainer width="40%" height={200}>
                      <RechartsPie>
                        <Pie
                          data={projectStatus}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          dataKey="value"
                        >
                          {projectStatus.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </RechartsPie>
                    </ResponsiveContainer>
                    <div className="space-y-3 flex-1">
                      {projectStatus.map((status, i) => (
                        <div key={i} className="flex items-center justify-between p-2 bg-zinc-800/30 rounded">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: status.color }}></div>
                            <span className="text-zinc-300">{status.name}</span>
                          </div>
                          <span className="font-bold text-white">{status.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg text-zinc-100">Consulting KPIs</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center p-4 bg-zinc-800/50 rounded-lg">
                    <p className="text-4xl font-bold text-blue-400">87%</p>
                    <p className="text-sm text-zinc-400 mt-1">Team Utilization</p>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Completed This Month</span>
                    <span className="text-xl font-bold text-green-400">8</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                    <span className="text-zinc-400">Client Satisfaction</span>
                    <span className="text-xl font-bold text-yellow-400">4.6/5</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="hr" className="mt-4">
            <div className="text-center py-12 text-zinc-500">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>HR Dashboard metrics will appear here</p>
            </div>
          </TabsContent>

          <TabsContent value="finance" className="mt-4">
            <div className="text-center py-12 text-zinc-500">
              <DollarSign className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Finance Dashboard metrics will appear here</p>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

// ============================================
// STYLE 2: CONSOLIDATED SCROLLABLE (LIGHT)
// ============================================
const StyleConsolidatedLight = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Admin Dashboard</h1>
            <p className="text-slate-500 mt-1">Unified view across all departments</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" className="gap-2">
              <Calendar className="w-4 h-4" />
              This Month
            </Button>
            <Button className="bg-slate-900 text-white gap-2">
              <FileText className="w-4 h-4" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-5 gap-4">
          {[
            { label: 'Total Revenue', value: '₹4.5Cr', change: '+12.5%', up: true, color: 'orange' },
            { label: 'Active Leads', value: '234', change: '+18', up: true, color: 'blue' },
            { label: 'Projects', value: '23', change: '+3', up: true, color: 'emerald' },
            { label: 'Team Size', value: '86', change: '+2', up: true, color: 'purple' },
            { label: 'Pending Tasks', value: '47', change: '-8', up: false, color: 'amber' },
          ].map((kpi, i) => (
            <Card key={i} className="bg-white border-slate-200 shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="pt-5">
                <p className="text-sm text-slate-500">{kpi.label}</p>
                <div className="flex items-end justify-between mt-2">
                  <p className="text-2xl font-bold text-slate-900">{kpi.value}</p>
                  <Badge className={`${kpi.up ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {kpi.change}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* SALES SECTION */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <BarChart3 className="w-5 h-5 text-orange-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">Sales Performance</h2>
            <Badge className="bg-orange-100 text-orange-700">Live</Badge>
            <Button variant="ghost" size="sm" className="ml-auto gap-1 text-orange-600">
              View Details <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="grid grid-cols-4 gap-4">
            <Card className="col-span-3 bg-white">
              <CardContent className="pt-6">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={monthlyTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" stroke="#64748b" />
                    <YAxis stroke="#64748b" />
                    <Tooltip />
                    <Bar dataKey="sales" fill="#f97316" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            
            <div className="space-y-3">
              {[
                { label: 'New Leads', value: '67', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
                { label: 'Hot Leads', value: '23', icon: Flame, color: 'text-red-600', bg: 'bg-red-50' },
                { label: 'Conversions', value: '12', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
                { label: 'Meetings', value: '34', icon: Calendar, color: 'text-purple-600', bg: 'bg-purple-50' },
              ].map((item, i) => (
                <Card key={i} className={`${item.bg} border-none`}>
                  <CardContent className="py-3 px-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <item.icon className={`w-4 h-4 ${item.color}`} />
                      <span className="text-sm text-slate-600">{item.label}</span>
                    </div>
                    <span className="font-bold text-slate-900">{item.value}</span>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>

        {/* CONSULTING SECTION */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Briefcase className="w-5 h-5 text-blue-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">Consulting Projects</h2>
            <Badge className="bg-blue-100 text-blue-700">23 Active</Badge>
            <Button variant="ghost" size="sm" className="ml-auto gap-1 text-blue-600">
              View Details <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="grid grid-cols-4 gap-4">
            <Card className="bg-white">
              <CardContent className="pt-6">
                <ResponsiveContainer width="100%" height={180}>
                  <RechartsPie>
                    <Pie
                      data={projectStatus}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={70}
                      dataKey="value"
                    >
                      {projectStatus.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </RechartsPie>
                </ResponsiveContainer>
                <div className="flex justify-center gap-4 mt-2">
                  {projectStatus.map((s, i) => (
                    <div key={i} className="flex items-center gap-1 text-xs">
                      <div className="w-2 h-2 rounded-full" style={{ background: s.color }}></div>
                      <span className="text-slate-500">{s.name}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            
            <Card className="col-span-2 bg-white">
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-600">Team Utilization</span>
                      <span className="font-medium">87%</span>
                    </div>
                    <Progress value={87} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-600">On-Time Delivery</span>
                      <span className="font-medium">92%</span>
                    </div>
                    <Progress value={92} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-600">Client Satisfaction</span>
                      <span className="font-medium">94%</span>
                    </div>
                    <Progress value={94} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-blue-600 to-blue-700 text-white">
              <CardContent className="pt-6 text-center">
                <p className="text-blue-200 text-sm">Revenue This Quarter</p>
                <p className="text-3xl font-bold mt-2">₹1.8Cr</p>
                <div className="flex items-center justify-center gap-1 mt-2 text-green-300 text-sm">
                  <ArrowUpRight className="w-4 h-4" />
                  <span>+15% vs last quarter</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* HR SECTION */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-3">
            <div className="p-2 bg-emerald-100 rounded-lg">
              <Users className="w-5 h-5 text-emerald-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900">Human Resources</h2>
            <Badge className="bg-emerald-100 text-emerald-700">86 Employees</Badge>
            <Button variant="ghost" size="sm" className="ml-auto gap-1 text-emerald-600">
              View Details <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: 'Present Today', value: '79', percent: '91.8%', color: 'emerald' },
              { label: 'On Leave', value: '7', percent: '8.2%', color: 'amber' },
              { label: 'Pending Leaves', value: '12', percent: '', color: 'blue' },
              { label: 'New Hires (MTD)', value: '3', percent: '', color: 'purple' },
              { label: 'Avg Tenure', value: '2.4y', percent: '', color: 'slate' },
            ].map((item, i) => (
              <Card key={i} className="bg-white">
                <CardContent className="pt-5 text-center">
                  <p className="text-2xl font-bold text-slate-900">{item.value}</p>
                  <p className="text-sm text-slate-500 mt-1">{item.label}</p>
                  {item.percent && (
                    <Badge className={`mt-2 bg-${item.color}-100 text-${item.color}-700`}>
                      {item.percent}
                    </Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// STYLE 3: BENTO GRID MODERN
// ============================================
const StyleBentoModern = () => {
  return (
    <div className="min-h-screen bg-zinc-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">Business Overview</h1>
            <p className="text-zinc-500">December 2025</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-zinc-900 text-white px-4 py-2">
              <Zap className="w-4 h-4 mr-2" />
              All Systems Operational
            </Badge>
          </div>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-12 gap-4 auto-rows-[140px]">
          {/* Large Revenue Card */}
          <Card className="col-span-4 row-span-2 bg-gradient-to-br from-zinc-900 to-zinc-800 text-white overflow-hidden relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/20 rounded-full blur-3xl"></div>
            <CardContent className="pt-6 h-full flex flex-col justify-between relative z-10">
              <div>
                <p className="text-zinc-400 text-sm">Total Revenue (YTD)</p>
                <p className="text-5xl font-bold mt-2">₹4.5<span className="text-2xl">Cr</span></p>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1 text-green-400">
                  <TrendingUp className="w-5 h-5" />
                  <span className="font-medium">+23.5%</span>
                </div>
                <span className="text-zinc-500 text-sm">vs last year</span>
              </div>
            </CardContent>
          </Card>

          {/* Sales Quick Stats */}
          <Card className="col-span-2 bg-orange-500 text-white">
            <CardContent className="pt-4 h-full flex flex-col justify-between">
              <BarChart3 className="w-8 h-8 opacity-80" />
              <div>
                <p className="text-3xl font-bold">234</p>
                <p className="text-orange-100 text-sm">Active Leads</p>
              </div>
            </CardContent>
          </Card>

          {/* Conversion */}
          <Card className="col-span-2 bg-white">
            <CardContent className="pt-4 h-full flex flex-col justify-between">
              <Target className="w-6 h-6 text-green-600" />
              <div>
                <p className="text-3xl font-bold text-zinc-900">20.1%</p>
                <p className="text-zinc-500 text-sm">Conversion Rate</p>
              </div>
            </CardContent>
          </Card>

          {/* Projects */}
          <Card className="col-span-4 row-span-2 bg-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-500 flex items-center gap-2">
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
                  </RechartsPie>
                </ResponsiveContainer>
                <div className="space-y-2 flex-1">
                  {projectStatus.map((s, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded" style={{ background: s.color }}></div>
                        <span className="text-sm text-zinc-600">{s.name}</span>
                      </div>
                      <span className="font-semibold">{s.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Meetings Today */}
          <Card className="col-span-2 bg-blue-600 text-white">
            <CardContent className="pt-4 h-full flex flex-col justify-between">
              <Calendar className="w-6 h-6 opacity-80" />
              <div>
                <p className="text-3xl font-bold">8</p>
                <p className="text-blue-100 text-sm">Meetings Today</p>
              </div>
            </CardContent>
          </Card>

          {/* Pending Approvals */}
          <Card className="col-span-2 bg-amber-500 text-white">
            <CardContent className="pt-4 h-full flex flex-col justify-between">
              <AlertCircle className="w-6 h-6 opacity-80" />
              <div>
                <p className="text-3xl font-bold">24</p>
                <p className="text-amber-100 text-sm">Pending Actions</p>
              </div>
            </CardContent>
          </Card>

          {/* Team Stats */}
          <Card className="col-span-3 bg-white">
            <CardContent className="pt-4 h-full">
              <div className="flex items-center justify-between h-full">
                <div>
                  <p className="text-sm text-zinc-500">Team Present</p>
                  <p className="text-4xl font-bold text-zinc-900">79<span className="text-lg text-zinc-400">/86</span></p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-emerald-500">91.8%</p>
                  <p className="text-sm text-zinc-500">Attendance</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Utilization */}
          <Card className="col-span-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white">
            <CardContent className="pt-4 h-full flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-purple-200 text-sm">Team Utilization</span>
                <Activity className="w-5 h-5 opacity-80" />
              </div>
              <div className="flex items-end gap-4">
                <p className="text-4xl font-bold">87%</p>
                <div className="flex items-center gap-1 text-green-300 text-sm mb-1">
                  <ArrowUpRight className="w-4 h-4" />
                  +5%
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Trend Chart */}
          <Card className="col-span-6 row-span-2 bg-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-500">Performance Trend (6 Months)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={monthlyTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} />
                  <Tooltip />
                  <Line type="monotone" dataKey="sales" stroke="#f97316" strokeWidth={2} dot={{ fill: '#f97316' }} />
                  <Line type="monotone" dataKey="consulting" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-6 mt-2">
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                  <span className="text-zinc-600">Sales</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  <span className="text-zinc-600">Consulting</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// Main Mockups Page
const AdminDashboardMockups = () => {
  const [activeStyle, setActiveStyle] = useState('tabbed-dark');

  const styles = [
    { id: 'tabbed-dark', name: 'Tabbed Modern Dark', description: 'Dark theme with tabbed department navigation' },
    { id: 'consolidated-light', name: 'Consolidated Light', description: 'Light scrollable view with all departments' },
    { id: 'bento-modern', name: 'Bento Grid', description: 'Modern asymmetric grid layout' },
  ];

  return (
    <div className="min-h-screen bg-zinc-900">
      {/* Style Selector */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-zinc-800 rounded-full px-2 py-1 flex gap-1 shadow-2xl border border-zinc-700">
        {styles.map((style) => (
          <button
            key={style.id}
            onClick={() => setActiveStyle(style.id)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              activeStyle === style.id
                ? 'bg-white text-zinc-900'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            {style.name}
          </button>
        ))}
      </div>

      {/* Active Style Preview */}
      <div className="pt-16">
        {activeStyle === 'tabbed-dark' && <StyleTabbedDark />}
        {activeStyle === 'consolidated-light' && <StyleConsolidatedLight />}
        {activeStyle === 'bento-modern' && <StyleBentoModern />}
      </div>
    </div>
  );
};

export default AdminDashboardMockups;
