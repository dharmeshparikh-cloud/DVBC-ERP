import React from 'react';
import { Badge } from './ui/badge';
import { 
  TrendingUp, TrendingDown, Users, Calendar, CheckCircle,
  DollarSign, Target, Flame, ArrowUpRight, ArrowDownRight,
  FileText, BarChart3, Thermometer
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';

const COLORS = ['#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4', '#f59e0b'];

// Pipeline Funnel Drill-down
export const PipelineExpanded = ({ data, isDark }) => {
  const pipeline = data?.pipeline || {};
  
  const funnelData = [
    { stage: 'New', count: pipeline.new || 0, conversionRate: 100 },
    { stage: 'Contacted', count: pipeline.contacted || 0, conversionRate: pipeline.new > 0 ? Math.round((pipeline.contacted / pipeline.new) * 100) : 0 },
    { stage: 'Qualified', count: pipeline.qualified || 0, conversionRate: pipeline.contacted > 0 ? Math.round((pipeline.qualified / pipeline.contacted) * 100) : 0 },
    { stage: 'Proposal', count: pipeline.proposal || 0, conversionRate: pipeline.qualified > 0 ? Math.round((pipeline.proposal / pipeline.qualified) * 100) : 0 },
    { stage: 'Agreement', count: pipeline.agreement || 0, conversionRate: pipeline.proposal > 0 ? Math.round((pipeline.agreement / pipeline.proposal) * 100) : 0 },
    { stage: 'Closed', count: pipeline.closed || 0, conversionRate: pipeline.agreement > 0 ? Math.round((pipeline.closed / pipeline.agreement) * 100) : 0 },
  ];

  const stageColors = ['#6b7280', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#10b981'];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Sales Funnel Analysis
        </h3>
        <div className="space-y-3">
          {funnelData.map((stage, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className={`w-24 text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                {stage.stage}
              </div>
              <div className="flex-1 h-10 bg-zinc-200 dark:bg-zinc-700 rounded-lg overflow-hidden">
                <div 
                  className="h-full flex items-center justify-end pr-3 text-white font-semibold transition-all"
                  style={{ 
                    width: `${(stage.count / (pipeline.total || 1)) * 100}%`,
                    backgroundColor: stageColors[i],
                    minWidth: stage.count > 0 ? '60px' : '0'
                  }}
                >
                  {stage.count}
                </div>
              </div>
              <div className={`w-20 text-right ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                {i > 0 && `${stage.conversionRate}%`}
              </div>
            </div>
          ))}
        </div>

        {/* Conversion Metrics */}
        <div className="grid grid-cols-3 gap-4 mt-8">
          <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-orange-50'}`}>
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Overall Conversion</p>
            <p className={`text-3xl font-bold ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
              {pipeline.total > 0 ? Math.round((pipeline.closed / pipeline.total) * 100) : 0}%
            </p>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>New to Closed</p>
          </div>
          <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Avg. Deal Cycle</p>
            <p className={`text-3xl font-bold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>45</p>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>days</p>
          </div>
          <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-green-50'}`}>
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Win Rate</p>
            <p className={`text-3xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>
              {data?.ratios?.lead_to_closure || 0}%
            </p>
            <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>of proposals</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Stage Breakdown
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={funnelData.filter(d => d.count > 0)}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="count"
              label={({ stage, percent }) => `${(percent * 100).toFixed(0)}%`}
            >
              {funnelData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={stageColors[index]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
        
        <div className="space-y-2">
          {funnelData.map((stage, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: stageColors[i] }} />
                <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>{stage.stage}</span>
              </div>
              <span className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>{stage.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Temperature Distribution Drill-down
export const TemperatureExpanded = ({ data, isDark }) => {
  const temperature = data?.temperature || {};
  
  const tempData = [
    { name: 'Hot', value: temperature.hot || 0, color: '#ef4444', icon: Flame },
    { name: 'Warm', value: temperature.warm || 0, color: '#f97316', icon: Thermometer },
    { name: 'Cold', value: temperature.cold || 0, color: '#3b82f6', icon: Target },
  ];

  const total = tempData.reduce((sum, t) => sum + t.value, 0);

  // Mock trend data - would come from backend
  const trendData = [
    { month: 'Jul', hot: 32, warm: 45, cold: 28 },
    { month: 'Aug', hot: 38, warm: 42, cold: 25 },
    { month: 'Sep', hot: 35, warm: 48, cold: 30 },
    { month: 'Oct', hot: 42, warm: 40, cold: 28 },
    { month: 'Nov', hot: 45, warm: 38, cold: 22 },
    { month: 'Dec', hot: temperature.hot || 47, warm: temperature.warm || 35, cold: temperature.cold || 20 },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Temperature Trend Over Time
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
            <XAxis dataKey="month" stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="hot" stackId="1" stroke="#ef4444" fill="#ef444450" name="Hot" />
            <Area type="monotone" dataKey="warm" stackId="1" stroke="#f97316" fill="#f9731650" name="Warm" />
            <Area type="monotone" dataKey="cold" stackId="1" stroke="#3b82f6" fill="#3b82f650" name="Cold" />
          </AreaChart>
        </ResponsiveContainer>

        {/* Quick Actions */}
        <div className={`mt-6 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-red-50'}`}>
          <div className="flex items-center gap-3">
            <Flame className="w-8 h-8 text-red-500" />
            <div>
              <p className={`font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {temperature.hot || 0} Hot Leads Ready for Pricing
              </p>
              <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                Focus on these high-priority leads first
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Current Distribution
        </h3>
        
        <div className="space-y-3">
          {tempData.map((temp, i) => {
            const Icon = temp.icon;
            const percentage = total > 0 ? Math.round((temp.value / total) * 100) : 0;
            return (
              <div key={i} className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-white shadow'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon className="w-5 h-5" style={{ color: temp.color }} />
                    <span className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>{temp.name}</span>
                  </div>
                  <span className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                    {temp.value}
                  </span>
                </div>
                <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all"
                    style={{ width: `${percentage}%`, backgroundColor: temp.color }}
                  />
                </div>
                <p className={`text-xs mt-1 text-right ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                  {percentage}% of pipeline
                </p>
              </div>
            );
          })}
        </div>

        {/* Conversion by Temperature */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
          <p className={`text-sm mb-2 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Conversion by Temperature</p>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-red-500">Hot</span>
              <span className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>45%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-orange-500">Warm</span>
              <span className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>22%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-500">Cold</span>
              <span className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>8%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Meeting Stats Drill-down
export const SalesMeetingsExpanded = ({ data, isDark }) => {
  const meetings = data?.meetings || {};
  
  const meetingTypes = [
    { type: 'Discovery', count: 45, color: '#3b82f6' },
    { type: 'Demo', count: 32, color: '#8b5cf6' },
    { type: 'Proposal', count: 28, color: '#f59e0b' },
    { type: 'Negotiation', count: 18, color: '#ec4899' },
    { type: 'Closing', count: 12, color: '#10b981' },
  ];

  const weeklyMeetings = [
    { day: 'Mon', completed: 8, scheduled: 10 },
    { day: 'Tue', completed: 6, scheduled: 8 },
    { day: 'Wed', completed: 9, scheduled: 9 },
    { day: 'Thu', completed: 7, scheduled: 10 },
    { day: 'Fri', completed: 5, scheduled: 7 },
  ];

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Weekly Meeting Performance
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={weeklyMeetings}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
            <XAxis dataKey="day" stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <Tooltip />
            <Legend />
            <Bar dataKey="scheduled" fill="#94a3b8" name="Scheduled" radius={[4, 4, 0, 0]} />
            <Bar dataKey="completed" fill="#3b82f6" name="Completed" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              {meetings.total || 0}
            </p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Total</p>
          </div>
          <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-zinc-800' : 'bg-green-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-green-400' : 'text-green-600'}`}>
              {meetings.this_month || 0}
            </p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>This Month</p>
          </div>
          <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-zinc-800' : 'bg-purple-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
              {meetings.today || 0}
            </p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>Today</p>
          </div>
          <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-zinc-800' : 'bg-orange-50'}`}>
            <p className={`text-2xl font-bold ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
              {meetings.mom_completion_rate || 0}%
            </p>
            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-600'}`}>MOM Rate</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          By Meeting Type
        </h3>
        <div className="space-y-3">
          {meetingTypes.map((mt, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: mt.color }} />
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{mt.type}</span>
                  <span className={`text-sm font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>{mt.count}</span>
                </div>
                <div className="h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full"
                    style={{ width: `${(mt.count / 50) * 100}%`, backgroundColor: mt.color }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* MOM Alert */}
        {meetings.without_mom > 0 && (
          <div className={`p-4 rounded-lg ${isDark ? 'bg-amber-900/30' : 'bg-amber-50'} border ${isDark ? 'border-amber-500/30' : 'border-amber-200'}`}>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-amber-500" />
              <span className={`font-medium ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>MOM Pending</span>
            </div>
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              {meetings.without_mom || 0} meetings without MOM recorded
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// Target Achievement Drill-down
export const TargetsExpanded = ({ data, isDark }) => {
  const targets = data?.targets || {};

  const monthlyProgress = [
    { month: 'Oct', meetings: 85, conversions: 78, value: 92 },
    { month: 'Nov', meetings: 92, conversions: 85, value: 88 },
    { month: 'Dec', meetings: targets.meeting_achievement || 0, conversions: targets.conversion_target > 0 ? Math.round(targets.conversion_actual / targets.conversion_target * 100) : 0, value: targets.value_target > 0 ? Math.round(targets.value_actual / targets.value_target * 100) : 0 },
  ];

  const formatCurrency = (val) => {
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    return `₹${val}`;
  };

  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Target Achievement Trend
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={monthlyProgress}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#3f3f46' : '#e5e7eb'} />
            <XAxis dataKey="month" stroke={isDark ? '#a1a1aa' : '#6b7280'} />
            <YAxis stroke={isDark ? '#a1a1aa' : '#6b7280'} unit="%" domain={[0, 100]} />
            <Tooltip formatter={(value) => `${value}%`} />
            <Legend />
            <Line type="monotone" dataKey="meetings" stroke="#3b82f6" strokeWidth={2} dot={{ r: 5 }} name="Meetings" />
            <Line type="monotone" dataKey="conversions" stroke="#10b981" strokeWidth={2} dot={{ r: 5 }} name="Conversions" />
            <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 5 }} name="Deal Value" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          This Month's Progress
        </h3>
        
        {/* Meeting Target */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Meetings</span>
            <Badge className={targets.meeting_achievement >= 100 ? 'bg-green-500' : targets.meeting_achievement >= 75 ? 'bg-amber-500' : 'bg-red-500'}>
              {targets.meeting_achievement || 0}%
            </Badge>
          </div>
          <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            {targets.meeting_actual || 0} / {targets.meeting_target || 0}
          </p>
          <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden mt-2">
            <div 
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${Math.min(targets.meeting_achievement || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Conversion Target */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-green-50'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Conversions</span>
            <Badge className={targets.conversion_actual >= targets.conversion_target ? 'bg-green-500' : 'bg-amber-500'}>
              {targets.conversion_target > 0 ? Math.round(targets.conversion_actual / targets.conversion_target * 100) : 0}%
            </Badge>
          </div>
          <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            {targets.conversion_actual || 0} / {targets.conversion_target || 0}
          </p>
          <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden mt-2">
            <div 
              className="h-full bg-green-500 rounded-full"
              style={{ width: `${Math.min(targets.conversion_target > 0 ? (targets.conversion_actual / targets.conversion_target * 100) : 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Value Target */}
        <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-purple-50'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>Deal Value</span>
            <Badge className={targets.value_actual >= targets.value_target ? 'bg-green-500' : 'bg-amber-500'}>
              {targets.value_target > 0 ? Math.round(targets.value_actual / targets.value_target * 100) : 0}%
            </Badge>
          </div>
          <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            {formatCurrency(targets.value_actual || 0)}
          </p>
          <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
            of {formatCurrency(targets.value_target || 0)} target
          </p>
          <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden mt-2">
            <div 
              className="h-full bg-purple-500 rounded-full"
              style={{ width: `${Math.min(targets.value_target > 0 ? (targets.value_actual / targets.value_target * 100) : 0, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

// Leaderboard Drill-down
export const LeaderboardExpanded = ({ data, isDark }) => {
  const leaderboard = data?.leaderboard || [];
  
  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="col-span-2">
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Team Performance Rankings
        </h3>
        <div className={`rounded-lg border overflow-hidden ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
          <table className="w-full">
            <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-100'}>
              <tr>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Rank</th>
                <th className={`px-4 py-3 text-left text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Name</th>
                <th className={`px-4 py-3 text-center text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Leads</th>
                <th className={`px-4 py-3 text-center text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Meetings</th>
                <th className={`px-4 py-3 text-center text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Closures</th>
                <th className={`px-4 py-3 text-right text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Value</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((member, idx) => (
                <tr key={idx} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'} ${idx < 3 ? isDark ? 'bg-zinc-800/50' : 'bg-zinc-50' : ''}`}>
                  <td className="px-4 py-3">
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                      idx === 1 ? 'bg-gray-100 text-gray-700' :
                      idx === 2 ? 'bg-orange-100 text-orange-700' :
                      isDark ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-100 text-zinc-600'
                    }`}>
                      {idx + 1}
                    </span>
                  </td>
                  <td className={`px-4 py-3 font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-900'}`}>{member.name}</td>
                  <td className={`px-4 py-3 text-center ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{member.leads || 0}</td>
                  <td className={`px-4 py-3 text-center ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>{member.meetings || 0}</td>
                  <td className={`px-4 py-3 text-center ${isDark ? 'text-green-400' : 'text-green-600'} font-semibold`}>{member.closures || 0}</td>
                  <td className={`px-4 py-3 text-right ${isDark ? 'text-zinc-200' : 'text-zinc-900'} font-semibold`}>
                    ₹{((member.value || 0) / 100000).toFixed(1)}L
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          Top Performers
        </h3>
        
        {leaderboard.slice(0, 3).map((member, idx) => (
          <div key={idx} className={`p-4 rounded-lg ${
            idx === 0 ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border border-yellow-500/30' :
            idx === 1 ? 'bg-gradient-to-r from-gray-400/20 to-zinc-400/20 border border-gray-400/30' :
            'bg-gradient-to-r from-orange-500/20 to-amber-500/20 border border-orange-500/30'
          }`}>
            <div className="flex items-center gap-3">
              <span className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                idx === 0 ? 'bg-yellow-500 text-white' :
                idx === 1 ? 'bg-gray-400 text-white' :
                'bg-orange-500 text-white'
              }`}>
                {idx + 1}
              </span>
              <div className="flex-1">
                <p className={`font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{member.name}</p>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                  {member.closures} closures • ₹{((member.value || 0) / 100000).toFixed(1)}L
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default {
  PipelineExpanded,
  TemperatureExpanded,
  SalesMeetingsExpanded,
  TargetsExpanded,
  LeaderboardExpanded
};
