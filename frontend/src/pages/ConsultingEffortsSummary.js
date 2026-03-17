/**
 * Consulting Efforts Summary Report
 * 
 * GOVERNANCE: Reuses existing components
 * - ExpandedCardViews patterns for charts
 * - Existing card/badge components
 * - Unified API patterns from useStats
 * 
 * Features:
 * - Expandable sections with details
 * - Print option for audit
 * - All metrics: meetings, tasks, expenses, payments
 */

import React, { useState, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { format } from 'date-fns';
import {
  Printer, ChevronDown, ChevronRight, Users, Calendar, CheckCircle,
  Clock, Target, DollarSign, FileText, Building2, TrendingUp,
  AlertCircle, Filter, Download, RefreshCw, Eye, Layers, PlusCircle
} from 'lucide-react';
import { toast } from 'sonner';
import ConsultingStageNav from '../components/ConsultingStageNav';

const COLORS = ['#10b981', '#3b82f6', '#f97316', '#8b5cf6', '#ef4444', '#06b6d4'];

// Format currency helper
const formatCurrency = (val) => {
  if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
  if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
  if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
  return `₹${val}`;
};

// Expandable Section Component (reusable pattern)
const ExpandableSection = ({ title, icon: Icon, defaultOpen = false, badge, children }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <Card className="border-zinc-200 shadow-none rounded-sm print:shadow-none print:border-zinc-300">
      <CardHeader 
        className="cursor-pointer hover:bg-zinc-50 print:hover:bg-white"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isOpen ? (
              <ChevronDown className="w-5 h-5 text-zinc-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-zinc-400" />
            )}
            <Icon className="w-5 h-5 text-zinc-600" />
            <CardTitle className="text-base font-semibold text-zinc-900">{title}</CardTitle>
          </div>
          {badge && (
            <Badge variant="secondary" className="text-xs">
              {badge}
            </Badge>
          )}
        </div>
      </CardHeader>
      {isOpen && (
        <CardContent className="pt-0 border-t border-zinc-100">
          {children}
        </CardContent>
      )}
    </Card>
  );
};

// Stat Card Component - Clickable with navigation
const StatCard = ({ label, value, subValue, icon: Icon, color = 'zinc', trend, href, onClick }) => {
  const navigate = useNavigate();
  
  const handleClick = () => {
    if (onClick) onClick();
    else if (href) navigate(href);
  };
  
  return (
    <div 
      className={`p-4 rounded-sm border border-zinc-200 bg-${color}-50 ${(href || onClick) ? 'cursor-pointer hover:border-zinc-400 hover:shadow-sm transition-all' : ''}`}
      onClick={handleClick}
      data-testid={`stat-card-${label.toLowerCase().replace(/\s+/g, '-')}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500 mb-1">{label}</p>
          <p className={`text-2xl font-bold text-${color}-700`}>{value}</p>
          {subValue && <p className="text-xs text-zinc-500 mt-1">{subValue}</p>}
        </div>
        <Icon className={`w-8 h-8 text-${color}-300`} />
      </div>
      {trend && (
        <div className={`mt-2 text-xs ${trend > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
          {trend > 0 ? '+' : ''}{trend}% vs last period
        </div>
      )}
      {(href || onClick) && (
        <div className="mt-2 text-xs text-blue-600 print:hidden">Click to view details →</div>
      )}
    </div>
  );
};

const ConsultingEffortsSummary = () => {
  const { user } = useContext(AuthContext);
  const printRef = useRef();
  
  // Filters
  const [filters, setFilters] = useState({
    project_id: '',
    consultant_id: '',
    client_id: '',
    date_from: '',
    date_to: ''
  });

  // Fetch projects for filter
  const { data: projects = [] } = useQuery({
    queryKey: ['projects', 'active'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects`);
      return Array.isArray(res.data) ? res.data : [];
    }
  });

  // Fetch clients for filter
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/clients`);
      return res.data?.items || res.data || [];
    }
  });

  // Fetch consultants for filter
  const { data: consultants = [] } = useQuery({
    queryKey: ['employees', 'consultants'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return (res.data || []).filter(e => 
        ['consultant', 'senior_consultant', 'principal_consultant', 'lead_consultant'].includes(e.role)
      );
    }
  });

  // Build query params
  const queryParams = new URLSearchParams();
  if (filters.project_id) queryParams.append('project_id', filters.project_id);
  if (filters.consultant_id) queryParams.append('consultant_id', filters.consultant_id);
  if (filters.client_id) queryParams.append('client_id', filters.client_id);
  if (filters.date_from) queryParams.append('date_from', filters.date_from);
  if (filters.date_to) queryParams.append('date_to', filters.date_to);

  // Fetch summary data
  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ['consulting-efforts-summary', filters],
    queryFn: async () => {
      const res = await axios.get(`${API}/stats/consulting/efforts-summary?${queryParams.toString()}`);
      return res.data;
    },
    staleTime: 60000
  });

  // Print handler
  const handlePrint = () => {
    window.print();
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({
      project_id: '',
      consultant_id: '',
      client_id: '',
      date_from: '',
      date_to: ''
    });
  };

  // Prepare chart data
  const consultantChartData = summary?.by_consultant?.map(c => ({
    name: c.name?.split(' ')[0] || 'Unknown',
    delivered: c.delivered,
    total: c.total,
    hours: Math.round((c.total_duration || 0) / 60)
  })) || [];

  const projectChartData = summary?.by_project?.map(p => ({
    name: (p.name || 'Unknown').substring(0, 15),
    delivered: p.delivered,
    committed: p.committed,
    extra: p.extra
  })) || [];

  const paymentPieData = summary?.payments ? [
    { name: 'Received', value: summary.payments.received },
    { name: 'Pending', value: summary.payments.pending },
    { name: 'Overdue', value: summary.payments.overdue }
  ].filter(d => d.value > 0) : [];

  return (
    <div className="p-6 print:p-2">
      <ConsultingStageNav />
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6 print:mb-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 print:text-xl">Consulting Efforts Summary</h1>
          <p className="text-sm text-zinc-500">Comprehensive report for audit and manager review</p>
        </div>
        <div className="flex items-center gap-2 print:hidden">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button onClick={handlePrint} className="bg-zinc-900 text-white">
            <Printer className="w-4 h-4 mr-2" /> Print Report
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="border-zinc-200 shadow-none rounded-sm mb-6 print:hidden">
        <CardContent className="p-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-zinc-500" />
              <span className="text-sm font-medium text-zinc-700">Filters:</span>
            </div>
            
            <Select value={filters.project_id || 'all'} onValueChange={(v) => setFilters(f => ({ ...f, project_id: v === 'all' ? '' : v }))}>
              <SelectTrigger className="w-[200px] h-9 text-sm">
                <SelectValue placeholder="All Projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {projects.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.consultant_id || 'all'} onValueChange={(v) => setFilters(f => ({ ...f, consultant_id: v === 'all' ? '' : v }))}>
              <SelectTrigger className="w-[180px] h-9 text-sm">
                <SelectValue placeholder="All Consultants" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Consultants</SelectItem>
                {consultants.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.first_name} {c.last_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.client_id || 'all'} onValueChange={(v) => setFilters(f => ({ ...f, client_id: v === 'all' ? '' : v }))}>
              <SelectTrigger className="w-[180px] h-9 text-sm">
                <SelectValue placeholder="All Companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Companies</SelectItem>
                {clients.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.company_name || c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">From:</span>
              <Input 
                type="date" 
                value={filters.date_from}
                onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))}
                className="w-[130px] h-9 text-sm"
              />
              <span className="text-xs text-zinc-500">To:</span>
              <Input 
                type="date" 
                value={filters.date_to}
                onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))}
                className="w-[130px] h-9 text-sm"
              />
            </div>

            {(filters.project_id || filters.consultant_id || filters.client_id || filters.date_from || filters.date_to) && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="text-center py-12 text-zinc-500">Loading report data...</div>
      ) : !summary ? (
        <div className="text-center py-12 text-zinc-500">No data available</div>
      ) : (
        <div ref={printRef} className="space-y-6 print:space-y-4">
          
          {/* Print Header (only visible in print) */}
          <div className="hidden print:block mb-4 pb-4 border-b border-zinc-300">
            <h1 className="text-xl font-bold">Consulting Efforts Summary Report</h1>
            <p className="text-sm text-zinc-600">
              Generated: {format(new Date(), 'EEEE, MMMM dd, yyyy HH:mm')}
              {filters.date_from && ` | Period: ${filters.date_from}`}
              {filters.date_to && ` to ${filters.date_to}`}
            </p>
          </div>

          {/* Summary Stats - Clickable */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 print:grid-cols-8 print:gap-2">
            <StatCard 
              label="Total Meetings" 
              value={summary.summary?.total_meetings || 0}
              subValue={`${summary.summary?.delivered_meetings || 0} delivered`}
              icon={Calendar}
              color="blue"
              href="/consulting-meetings"
            />
            <StatCard 
              label="With Attendance" 
              value={summary.summary?.meetings_with_attendance || 0}
              subValue={`${summary.summary?.attendance_compliance_rate || 0}% compliance`}
              icon={Users}
              color="emerald"
              href="/attendance"
            />
            <StatCard 
              label="With MOM" 
              value={summary.summary?.meetings_with_mom || 0}
              subValue={`${summary.summary?.mom_sent_to_client || 0} sent`}
              icon={FileText}
              color="purple"
              href="/consulting-meetings?filter=with_mom"
            />
            <StatCard 
              label="Total Hours" 
              value={summary.duration?.total_hours || 0}
              subValue={`Avg ${summary.duration?.average_minutes || 0} mins`}
              icon={Clock}
              color="amber"
              href="/timesheets"
            />
            <StatCard 
              label="Tasks Completed" 
              value={`${summary.tasks?.completed || 0}/${summary.tasks?.total || 0}`}
              subValue={`${summary.tasks?.completion_rate || 0}% done`}
              icon={CheckCircle}
              color="emerald"
            />
            <StatCard 
              label="Timely Delivery" 
              value={`${summary.tasks?.timely_delivery_rate || 0}%`}
              subValue="On-time completion"
              icon={Target}
              color="blue"
            />
            {/* SOW Stats - Committed vs Additional */}
            <StatCard 
              label="Committed Scopes" 
              value={summary.sow?.scopes?.committed || 0}
              subValue={`${summary.sow?.scopes?.completed || 0} completed`}
              icon={Layers}
              color="indigo"
              href="/consulting/sow"
            />
            <StatCard 
              label="Additional Scopes" 
              value={summary.sow?.scopes?.additional || 0}
              subValue={`${summary.sow?.total || 0} total SOWs`}
              icon={PlusCircle}
              color="orange"
              href="/consulting/sow"
            />
          </div>

          {/* SOW Progress Card */}
          {summary.sow?.total > 0 && (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-zinc-500 mb-1">SOW Progress</p>
                      <p className="text-2xl font-bold text-indigo-700">{summary.sow?.avg_progress || 0}%</p>
                    </div>
                    <div className="w-48 bg-zinc-200 rounded-full h-3">
                      <div 
                        className="bg-indigo-500 h-3 rounded-full transition-all" 
                        style={{ width: `${summary.sow?.avg_progress || 0}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex gap-6 text-sm">
                    <div className="text-center">
                      <p className="font-bold text-emerald-600">{summary.sow?.scopes?.completed || 0}</p>
                      <p className="text-xs text-zinc-500">Completed</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-amber-600">{summary.sow?.scopes?.pending || 0}</p>
                      <p className="text-xs text-zinc-500">Pending</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-orange-600">{summary.sow?.scopes?.additional || 0}</p>
                      <p className="text-xs text-zinc-500">Additional</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Financial Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 print:grid-cols-2">
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-emerald-600" />
                  Expenses Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-zinc-500">Total</p>
                    <p className="text-lg font-bold text-zinc-900">{formatCurrency(summary.expenses?.total || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Approved</p>
                    <p className="text-lg font-bold text-emerald-600">{formatCurrency(summary.expenses?.approved || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Pending</p>
                    <p className="text-lg font-bold text-amber-600">{formatCurrency(summary.expenses?.pending || 0)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                  Payments Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-3">
                  <div>
                    <p className="text-xs text-zinc-500">Invoiced</p>
                    <p className="text-lg font-bold text-zinc-900">{formatCurrency(summary.payments?.total_invoiced || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Received</p>
                    <p className="text-lg font-bold text-emerald-600">{formatCurrency(summary.payments?.received || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Overdue</p>
                    <p className="text-lg font-bold text-red-600">{formatCurrency(summary.payments?.overdue || 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">Collection</p>
                    <p className="text-lg font-bold text-blue-600">{summary.payments?.collection_rate || 0}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Expandable Sections */}
          <ExpandableSection 
            title="Meetings by Consultant" 
            icon={Users} 
            defaultOpen={true}
            badge={`${summary.by_consultant?.length || 0} consultants`}
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
              <div className="h-64 print:h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={consultantChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                    <YAxis stroke="#6b7280" fontSize={12} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="delivered" fill="#10b981" name="Delivered" />
                    <Bar dataKey="total" fill="#3b82f6" name="Total" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-2 px-3 text-xs uppercase text-zinc-500">Consultant</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Total</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Delivered</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">MOM</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Hours</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_consultant?.map((c, idx) => (
                      <tr key={idx} className="border-b border-zinc-100">
                        <td className="py-2 px-3 font-medium">{c.name}</td>
                        <td className="py-2 px-3 text-center">{c.total}</td>
                        <td className="py-2 px-3 text-center text-emerald-600">{c.delivered}</td>
                        <td className="py-2 px-3 text-center">{c.with_mom}</td>
                        <td className="py-2 px-3 text-center">{Math.round((c.total_duration || 0) / 60)}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </ExpandableSection>

          <ExpandableSection 
            title="Meetings by Project" 
            icon={Target} 
            defaultOpen={true}
            badge={`${summary.by_project?.length || 0} projects`}
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
              <div className="h-64 print:h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={projectChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" stroke="#6b7280" fontSize={12} />
                    <YAxis dataKey="name" type="category" width={100} stroke="#6b7280" fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="committed" fill="#3b82f6" name="Committed" />
                    <Bar dataKey="delivered" fill="#10b981" name="Delivered" />
                    <Bar dataKey="extra" fill="#f97316" name="Extra" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-2 px-3 text-xs uppercase text-zinc-500">Project</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Committed</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Delivered</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Extra</th>
                      <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Hours</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_project?.map((p, idx) => (
                      <tr key={idx} className="border-b border-zinc-100">
                        <td className="py-2 px-3 font-medium">{p.name}</td>
                        <td className="py-2 px-3 text-center text-blue-600">{p.committed}</td>
                        <td className="py-2 px-3 text-center text-emerald-600">{p.delivered}</td>
                        <td className="py-2 px-3 text-center text-orange-600">{p.extra}</td>
                        <td className="py-2 px-3 text-center">{Math.round((p.total_duration || 0) / 60)}h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </ExpandableSection>

          <ExpandableSection 
            title="Meetings by Company" 
            icon={Building2}
            badge={`${summary.by_client?.length || 0} companies`}
          >
            <div className="pt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left py-2 px-3 text-xs uppercase text-zinc-500">Company</th>
                    <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Total Meetings</th>
                    <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Delivered</th>
                    <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Client Approved</th>
                    <th className="text-center py-2 px-3 text-xs uppercase text-zinc-500">Approval Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_client?.map((c, idx) => (
                    <tr key={idx} className="border-b border-zinc-100">
                      <td className="py-2 px-3 font-medium">{c.name}</td>
                      <td className="py-2 px-3 text-center">{c.total}</td>
                      <td className="py-2 px-3 text-center text-emerald-600">{c.delivered}</td>
                      <td className="py-2 px-3 text-center text-blue-600">{c.approved}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant={c.delivered > 0 && c.approved / c.delivered >= 0.8 ? 'default' : 'secondary'}>
                          {c.delivered > 0 ? Math.round(c.approved / c.delivered * 100) : 0}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ExpandableSection>

          <ExpandableSection 
            title="Payment Collection" 
            icon={DollarSign}
            badge={`${summary.payments?.collection_rate || 0}% collected`}
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
              <div className="h-64 print:h-48 flex items-center justify-center">
                {paymentPieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={paymentPieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {paymentPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatCurrency(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-zinc-500">No payment data</p>
                )}
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-zinc-50 rounded-sm">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-zinc-600">Total Invoiced</span>
                    <span className="font-bold">{formatCurrency(summary.payments?.total_invoiced || 0)}</span>
                  </div>
                  <div className="w-full bg-zinc-200 rounded-full h-2">
                    <div 
                      className="bg-emerald-500 h-2 rounded-full" 
                      style={{ width: `${summary.payments?.collection_rate || 0}%` }}
                    />
                  </div>
                </div>
                {summary.payments?.overdue > 0 && (
                  <div className="p-4 bg-red-50 rounded-sm border border-red-200">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-500" />
                      <span className="font-medium text-red-700">
                        {formatCurrency(summary.payments.overdue)} Overdue
                      </span>
                    </div>
                    <p className="text-xs text-red-600 mt-1">Requires immediate attention</p>
                  </div>
                )}
                {summary.payments?.late > 0 && (
                  <div className="p-4 bg-amber-50 rounded-sm border border-amber-200">
                    <div className="flex items-center gap-2">
                      <Clock className="w-5 h-5 text-amber-500" />
                      <span className="font-medium text-amber-700">
                        {formatCurrency(summary.payments.late)} Late Payments
                      </span>
                    </div>
                    <p className="text-xs text-amber-600 mt-1">Received after due date</p>
                  </div>
                )}
              </div>
            </div>
          </ExpandableSection>

          {/* Print Footer */}
          <div className="hidden print:block mt-8 pt-4 border-t border-zinc-300">
            <p className="text-xs text-zinc-500 text-center">
              This report was generated from NETRA ERP System. For audit purposes only.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConsultingEffortsSummary;
