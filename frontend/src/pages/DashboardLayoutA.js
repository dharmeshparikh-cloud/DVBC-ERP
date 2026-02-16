import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import {
  TrendingUp, Users, Briefcase, DollarSign, ChevronRight,
  ArrowUpRight, ArrowDownRight, Target, CheckCircle, Clock,
  Calendar, FileText, CreditCard, BarChart3, PieChart
} from 'lucide-react';

// Option A: Stacked Sections Layout
export const LayoutOptionA = () => {
  return (
    <div className="space-y-6 p-6 bg-zinc-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Executive Dashboard</h1>
          <p className="text-sm text-zinc-500">Complete business overview across all departments</p>
        </div>
        <Badge className="bg-green-100 text-green-700">Live Data</Badge>
      </div>

      {/* Top KPI Row */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: 'Total Revenue', value: '₹2.4Cr', change: '+12%', icon: DollarSign, color: 'text-green-600 bg-green-50', up: true },
          { label: 'Active Leads', value: '387', change: '+8%', icon: Users, color: 'text-blue-600 bg-blue-50', up: true },
          { label: 'Active Projects', value: '28', change: '+3', icon: Briefcase, color: 'text-purple-600 bg-purple-50', up: true },
          { label: 'Employees', value: '45', change: '92% Present', icon: Users, color: 'text-orange-600 bg-orange-50', up: true },
          { label: 'Pending Tasks', value: '12', change: '-5', icon: Clock, color: 'text-red-600 bg-red-50', up: false },
        ].map((kpi, i) => (
          <Card key={i} className="border-zinc-200 hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div className={`p-2 rounded-lg ${kpi.color}`}>
                  <kpi.icon className="w-5 h-5" />
                </div>
                <span className={`text-xs flex items-center gap-1 ${kpi.up ? 'text-green-600' : 'text-red-600'}`}>
                  {kpi.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {kpi.change}
                </span>
              </div>
              <p className="text-2xl font-bold text-zinc-900 mt-3">{kpi.value}</p>
              <p className="text-xs text-zinc-500">{kpi.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Sales Section */}
      <Card className="border-zinc-200 hover:border-orange-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-100">
              <TrendingUp className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <CardTitle className="text-base">Sales Performance</CardTitle>
              <p className="text-xs text-zinc-500">Pipeline, conversions & revenue tracking</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-orange-600 group-hover:bg-orange-50">
            View Details <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Pipeline Value</p>
              <p className="text-xl font-bold text-zinc-900">₹4.2Cr</p>
              <div className="flex gap-2 mt-2">
                <Badge variant="secondary" className="text-xs">387 Leads</Badge>
              </div>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Conversion Rate</p>
              <p className="text-xl font-bold text-zinc-900">23%</p>
              <Progress value={23} className="mt-2 h-2" />
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">This Month Revenue</p>
              <p className="text-xl font-bold text-green-600">₹45L</p>
              <span className="text-xs text-green-600">↑ 18% vs last month</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Target Achievement</p>
              <p className="text-xl font-bold text-zinc-900">78%</p>
              <Progress value={78} className="mt-2 h-2" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* HR Section */}
      <Card className="border-zinc-200 hover:border-green-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100">
              <Users className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <CardTitle className="text-base">HR & Workforce</CardTitle>
              <p className="text-xs text-zinc-500">Attendance, leaves & payroll status</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-green-600 group-hover:bg-green-50">
            View Details <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Today's Attendance</p>
              <p className="text-xl font-bold text-zinc-900">92%</p>
              <span className="text-xs text-zinc-500">41/45 present</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Pending Leaves</p>
              <p className="text-xl font-bold text-amber-600">8</p>
              <span className="text-xs text-amber-600">Require approval</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Payroll Status</p>
              <p className="text-xl font-bold text-green-600">Processed</p>
              <span className="text-xs text-zinc-500">Feb 2026</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Open Expenses</p>
              <p className="text-xl font-bold text-zinc-900">₹2.4L</p>
              <span className="text-xs text-zinc-500">12 claims pending</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Consulting Section */}
      <Card className="border-zinc-200 hover:border-blue-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <Briefcase className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-base">Consulting & Projects</CardTitle>
              <p className="text-xs text-zinc-500">Project delivery & team utilization</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-blue-600 group-hover:bg-blue-50">
            View Details <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Active Projects</p>
              <p className="text-xl font-bold text-zinc-900">28</p>
              <span className="text-xs text-green-600">5 completing this month</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Team Utilization</p>
              <p className="text-xl font-bold text-zinc-900">85%</p>
              <Progress value={85} className="mt-2 h-2" />
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Pending Deliverables</p>
              <p className="text-xl font-bold text-amber-600">14</p>
              <span className="text-xs text-amber-600">Due this week</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Client Satisfaction</p>
              <p className="text-xl font-bold text-green-600">4.6/5</p>
              <span className="text-xs text-zinc-500">Based on 45 reviews</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Finance Section */}
      <Card className="border-zinc-200 hover:border-purple-200 transition-colors cursor-pointer group">
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100">
              <CreditCard className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <CardTitle className="text-base">Finance Overview</CardTitle>
              <p className="text-xs text-zinc-500">Receivables, payments & P&L</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="text-purple-600 group-hover:bg-purple-50">
            View Details <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Receivables</p>
              <p className="text-xl font-bold text-zinc-900">₹1.8Cr</p>
              <span className="text-xs text-amber-600">₹45L overdue</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Collections (MTD)</p>
              <p className="text-xl font-bold text-green-600">₹62L</p>
              <span className="text-xs text-green-600">↑ 22% vs target</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Pending Invoices</p>
              <p className="text-xl font-bold text-zinc-900">18</p>
              <span className="text-xs text-zinc-500">Worth ₹34L</span>
            </div>
            <div className="p-4 bg-zinc-50 rounded-lg">
              <p className="text-sm text-zinc-500">Net Profit (MTD)</p>
              <p className="text-xl font-bold text-green-600">₹18L</p>
              <span className="text-xs text-zinc-500">Margin: 28%</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LayoutOptionA;
