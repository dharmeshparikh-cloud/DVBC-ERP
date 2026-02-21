import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { 
  Users, TrendingUp, Calendar, Phone, CheckCircle, UserX, 
  Search, RefreshCw, Pause, Play, Eye, ChevronRight,
  Target, DollarSign, BarChart3, Clock
} from 'lucide-react';
import { toast } from 'sonner';

const ManagerLeadsDashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [subordinateLeads, setSubordinateLeads] = useState([]);
  const [subordinates, setSubordinates] = useState([]);
  const [todayStats, setTodayStats] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [targetVsAchievement, setTargetVsAchievement] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'new', label: 'New' },
    { value: 'meeting', label: 'Meeting' },
    { value: 'pricing_plan', label: 'Pricing Plan' },
    { value: 'sow', label: 'SOW' },
    { value: 'quotation', label: 'Quotation' },
    { value: 'agreement', label: 'Agreement' },
    { value: 'payment', label: 'Payment' },
    { value: 'kickoff_request', label: 'Kickoff Request' },
    { value: 'kick_accept', label: 'Kick Accept' },
    { value: 'closed', label: 'Closed' },
    { value: 'paused', label: 'Paused' },
    { value: 'lost', label: 'Lost' }
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [leadsRes, statsRes, perfRes, kpiRes] = await Promise.all([
        axios.get(`${API}/manager/subordinate-leads`),
        axios.get(`${API}/manager/today-stats`),
        axios.get(`${API}/manager/performance`),
        axios.get(`${API}/manager/target-vs-achievement`)
      ]);
      
      setSubordinateLeads(leadsRes.data.leads || []);
      setSubordinates(leadsRes.data.subordinates || []);
      setTodayStats(statsRes.data);
      setPerformance(perfRes.data);
      setTargetVsAchievement(kpiRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePauseLead = async (leadId, e) => {
    e?.stopPropagation();
    try {
      await axios.post(`${API}/leads/${leadId}/pause`);
      toast.success('Lead paused');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to pause lead');
    }
  };

  const handleResumeLead = async (leadId, e) => {
    e?.stopPropagation();
    try {
      await axios.post(`${API}/leads/${leadId}/resume`);
      toast.success('Lead resumed');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to resume lead');
    }
  };

  const handleLeadClick = (lead) => {
    if (lead.status === 'paused') {
      toast.info('This lead is paused');
      return;
    }
    navigate(`/leads?leadId=${lead.id}`);
  };

  const getStatusBadge = (status) => {
    const styles = {
      new: 'bg-zinc-100 text-zinc-700',
      meeting: 'bg-blue-100 text-blue-700',
      pricing_plan: 'bg-indigo-100 text-indigo-700',
      sow: 'bg-purple-100 text-purple-700',
      quotation: 'bg-yellow-100 text-yellow-700',
      agreement: 'bg-orange-100 text-orange-700',
      payment: 'bg-cyan-100 text-cyan-700',
      kickoff_request: 'bg-pink-100 text-pink-700',
      kick_accept: 'bg-teal-100 text-teal-700',
      closed: 'bg-emerald-100 text-emerald-700',
      paused: 'bg-amber-100 text-amber-800',
      lost: 'bg-red-100 text-red-700'
    };
    return styles[status] || styles.new;
  };

  const formatCurrency = (value) => {
    if (!value) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  // Filter leads
  const filteredLeads = subordinateLeads.filter(lead => {
    const matchesSearch = !searchQuery || 
      `${lead.first_name} ${lead.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.assigned_employee_name?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesEmployee = !selectedEmployee || 
      lead.assigned_employee_id === selectedEmployee ||
      lead.assigned_to === selectedEmployee;
    
    const matchesStatus = !selectedStatus || lead.status === selectedStatus;
    
    return matchesSearch && matchesEmployee && matchesStatus;
  });

  // Group leads by employee
  const leadsByEmployee = {};
  filteredLeads.forEach(lead => {
    const empName = lead.assigned_employee_name || 'Unassigned';
    if (!leadsByEmployee[empName]) {
      leadsByEmployee[empName] = { leads: [], closed: 0, value: 0 };
    }
    leadsByEmployee[empName].leads.push(lead);
    if (lead.status === 'closed') {
      leadsByEmployee[empName].closed++;
      leadsByEmployee[empName].value += lead.agreement_value || 0;
    }
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Team Leads Dashboard</h1>
          <p className="text-sm text-zinc-500">Monitor and manage your team's sales pipeline</p>
        </div>
        <Button onClick={fetchData} variant="outline" className="rounded-sm">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Today's Stats */}
      {todayStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Today's Meetings</p>
                  <p className="text-2xl font-semibold text-blue-600">{todayStats.today_meetings}</p>
                </div>
                <Calendar className="w-8 h-8 text-blue-500/30" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Today's Calls</p>
                  <p className="text-2xl font-semibold text-green-600">{todayStats.today_calls}</p>
                </div>
                <Phone className="w-8 h-8 text-green-500/30" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Today's Closures</p>
                  <p className="text-2xl font-semibold text-emerald-600">{todayStats.today_closures}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-emerald-500/30" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Team Size</p>
                  <p className="text-2xl font-semibold text-zinc-700">{todayStats.subordinate_count}</p>
                </div>
                <Users className="w-8 h-8 text-zinc-400/30" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Absent Today</p>
                  <p className="text-2xl font-semibold text-red-600">{todayStats.today_absent}</p>
                </div>
                <UserX className="w-8 h-8 text-red-500/30" />
              </div>
              {todayStats.absent_employees?.length > 0 && (
                <div className="mt-2 text-xs text-red-600">
                  {todayStats.absent_employees.map(e => e.name).join(', ')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Performance Cards */}
      {performance && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-600 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" /> Monthly Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-zinc-500">Closures</p>
                  <p className="text-xl font-semibold">{performance.monthly.closures}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Value</p>
                  <p className="text-xl font-semibold text-emerald-600">{formatCurrency(performance.monthly.agreement_value)}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Target</p>
                  <p className="text-xl font-semibold text-zinc-600">{formatCurrency(performance.monthly.target)}</p>
                </div>
              </div>
              {performance.monthly.target > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span>Achievement</span>
                    <span>{performance.monthly.achievement_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-emerald-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, performance.monthly.achievement_percentage)}%` }}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-zinc-600 flex items-center gap-2">
                <Target className="w-4 h-4" /> YTD Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-zinc-500">Closures</p>
                  <p className="text-xl font-semibold">{performance.ytd.closures}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Value</p>
                  <p className="text-xl font-semibold text-emerald-600">{formatCurrency(performance.ytd.agreement_value)}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Target</p>
                  <p className="text-xl font-semibold text-zinc-600">{formatCurrency(performance.ytd.target)}</p>
                </div>
              </div>
              {performance.ytd.target > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span>Achievement</span>
                    <span>{performance.ytd.achievement_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, performance.ytd.achievement_percentage)}%` }}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Target vs Achievement by Employee */}
      {targetVsAchievement && targetVsAchievement.employee_stats?.length > 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Target className="w-5 h-5 text-orange-500" />
              Target vs Achievement (Month: {targetVsAchievement.month}/{targetVsAchievement.year})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Team Totals */}
            <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-zinc-50 rounded-sm">
              <div className="text-center">
                <p className="text-xs text-zinc-500 uppercase">Meetings</p>
                <p className="text-lg font-semibold">
                  {targetVsAchievement.team_totals.meetings.achieved} / {targetVsAchievement.team_totals.meetings.target}
                </p>
                <p className={`text-xs ${targetVsAchievement.team_totals.meetings.percentage >= 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {targetVsAchievement.team_totals.meetings.percentage.toFixed(0)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-zinc-500 uppercase">Closures</p>
                <p className="text-lg font-semibold">
                  {targetVsAchievement.team_totals.closures.achieved} / {targetVsAchievement.team_totals.closures.target}
                </p>
                <p className={`text-xs ${targetVsAchievement.team_totals.closures.percentage >= 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {targetVsAchievement.team_totals.closures.percentage.toFixed(0)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-zinc-500 uppercase">Revenue</p>
                <p className="text-lg font-semibold text-emerald-600">
                  {formatCurrency(targetVsAchievement.team_totals.revenue.achieved)}
                </p>
                <p className={`text-xs ${targetVsAchievement.team_totals.revenue.percentage >= 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                  of {formatCurrency(targetVsAchievement.team_totals.revenue.target)} ({targetVsAchievement.team_totals.revenue.percentage.toFixed(0)}%)
                </p>
              </div>
            </div>

            {/* Employee-wise breakdown */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left py-2 font-medium text-zinc-600">Employee</th>
                    <th className="text-center py-2 font-medium text-zinc-600">Meetings</th>
                    <th className="text-center py-2 font-medium text-zinc-600">Closures</th>
                    <th className="text-right py-2 font-medium text-zinc-600">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {targetVsAchievement.employee_stats.filter(e => e.employee_name.trim()).map((emp, idx) => (
                    <tr key={idx} className="border-b border-zinc-100 hover:bg-zinc-50">
                      <td className="py-2 font-medium">{emp.employee_name}</td>
                      <td className="py-2 text-center">
                        <span className={emp.meetings.percentage >= 100 ? 'text-emerald-600' : ''}>
                          {emp.meetings.achieved}/{emp.meetings.target}
                        </span>
                        {emp.meetings.target > 0 && (
                          <span className="text-xs text-zinc-400 ml-1">({emp.meetings.percentage.toFixed(0)}%)</span>
                        )}
                      </td>
                      <td className="py-2 text-center">
                        <span className={emp.closures.percentage >= 100 ? 'text-emerald-600' : ''}>
                          {emp.closures.achieved}/{emp.closures.target}
                        </span>
                        {emp.closures.target > 0 && (
                          <span className="text-xs text-zinc-400 ml-1">({emp.closures.percentage.toFixed(0)}%)</span>
                        )}
                      </td>
                      <td className="py-2 text-right">
                        <span className={emp.revenue.percentage >= 100 ? 'text-emerald-600' : ''}>
                          {formatCurrency(emp.revenue.achieved)}
                        </span>
                        {emp.revenue.target > 0 && (
                          <span className="text-xs text-zinc-400 ml-1">/ {formatCurrency(emp.revenue.target)}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            placeholder="Search leads or employees..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 rounded-sm"
          />
        </div>
        <select
          value={selectedEmployee}
          onChange={(e) => setSelectedEmployee(e.target.value)}
          className="px-3 py-2 border border-zinc-200 rounded-sm bg-white text-sm"
        >
          <option value="">All Team Members</option>
          {subordinates.map(sub => (
            <option key={sub.id} value={sub.employee_id}>
              {sub.first_name} {sub.last_name}
            </option>
          ))}
        </select>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="px-3 py-2 border border-zinc-200 rounded-sm bg-white text-sm"
        >
          {statusOptions.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Team Summary */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-500" />
            Team Summary ({filteredLeads.length} leads)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(leadsByEmployee).map(([empName, data]) => (
              <div 
                key={empName}
                className="p-3 bg-zinc-50 rounded-sm border border-zinc-100 cursor-pointer hover:bg-zinc-100 transition-colors"
                onClick={() => {
                  const emp = subordinates.find(s => `${s.first_name} ${s.last_name}` === empName);
                  if (emp) setSelectedEmployee(emp.employee_id);
                }}
              >
                <p className="font-medium text-sm truncate">{empName}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
                  <span>{data.leads.length} leads</span>
                  <span className="text-emerald-600">{data.closed} closed</span>
                </div>
                {data.value > 0 && (
                  <p className="text-xs text-emerald-600 mt-1">{formatCurrency(data.value)}</p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Leads Table */}
      <Card className="border-zinc-200 shadow-none rounded-sm overflow-hidden">
        <CardHeader className="pb-2 border-b border-zinc-100">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            Team Leads ({filteredLeads.length})
          </CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-zinc-50 border-b border-zinc-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Lead</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Assigned To</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Company</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Progress</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Value</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                    No leads found matching your criteria
                  </td>
                </tr>
              ) : (
                filteredLeads.map(lead => {
                  const isPaused = lead.status === 'paused';
                  return (
                    <tr 
                      key={lead.id}
                      className={`hover:bg-zinc-50 cursor-pointer transition-colors ${isPaused ? 'opacity-60 bg-zinc-50' : ''}`}
                      onClick={() => handleLeadClick(lead)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-zinc-900">
                            {lead.first_name} {lead.last_name}
                          </span>
                          {isPaused && (
                            <Badge className="bg-amber-100 text-amber-800 text-[10px]">PAUSED</Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {lead.assigned_employee_name || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {lead.company || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={`${getStatusBadge(lead.status)} text-xs`}>
                          {lead.status?.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${lead.has_pricing_plan ? 'bg-emerald-500' : 'bg-zinc-200'}`} title="Pricing" />
                          <div className={`w-2 h-2 rounded-full ${lead.has_sow ? 'bg-emerald-500' : 'bg-zinc-200'}`} title="SOW" />
                          <div className={`w-2 h-2 rounded-full ${lead.has_agreement ? 'bg-emerald-500' : 'bg-zinc-200'}`} title="Agreement" />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {lead.agreement_value > 0 ? (
                          <span className="text-emerald-600 font-medium">{formatCurrency(lead.agreement_value)}</span>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-end gap-2">
                          {isPaused ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => handleResumeLead(lead.id, e)}
                              className="h-8 text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                              title="Resume"
                            >
                              <Play className="w-3 h-3" />
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => handlePauseLead(lead.id, e)}
                              className="h-8 text-orange-600 border-orange-200 hover:bg-orange-50"
                              title="Pause"
                            >
                              <Pause className="w-3 h-3" />
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`)}
                            className="h-8"
                            title="View Sales Funnel"
                          >
                            <Eye className="w-3 h-3 mr-1" /> View
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default ManagerLeadsDashboard;
