import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Progress } from '../components/ui/progress';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible';
import { 
  Users, TrendingUp, Calendar, Phone, CheckCircle, UserX, 
  Search, RefreshCw, Pause, Play, Eye, ChevronRight, ChevronDown,
  Target, DollarSign, BarChart3, Clock, FileText, Download,
  MessageSquare, Send, XCircle, AlertCircle, Building2
} from 'lucide-react';
import { toast } from 'sonner';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import { 
  useSubordinateLeads, 
  useManagerTodayStats, 
  useManagerPerformance, 
  useManagerTargetVsAchievement 
} from '../hooks/useStats';
import { usePauseLead, useResumeLead } from '../hooks/useLeads';
import ProfilePerformanceCard from '../components/ProfilePerformanceCard';
import { LeadsTable } from '../components/sales';

const API = process.env.REACT_APP_BACKEND_URL;

const ManagerLeadsDashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [momSectionOpen, setMomSectionOpen] = useState(false);
  const [expandedMomEmployee, setExpandedMomEmployee] = useState(null);
  const [funnelSectionOpen, setFunnelSectionOpen] = useState(true);

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'new', label: 'New' },
    { value: 'meeting', label: 'Meeting' },
    { value: 'pricing_plan', label: 'Pricing Plan' },
    { value: 'sow', label: 'SOW' },
    { value: 'quotation', label: 'Proforma Invoice' },
    { value: 'agreement', label: 'Agreement' },
    { value: 'payment', label: 'Payment' },
    { value: 'kickoff_request', label: 'Kickoff Request' },
    { value: 'kick_accept', label: 'Kick Accept' },
    { value: 'closed', label: 'Closed' },
    { value: 'paused', label: 'Paused' },
    { value: 'lost', label: 'Lost' }
  ];

  // Funnel stages for display
  const funnelStages = [
    { id: 'lead', name: 'Lead', color: 'bg-gray-500/10 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300 border-gray-500/30' },
    { id: 'meeting', name: 'Meeting', color: 'bg-blue-500/10 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-500/30' },
    { id: 'pricing', name: 'Pricing', color: 'bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border-indigo-500/30' },
    { id: 'sow', name: 'SOW', color: 'bg-purple-500/10 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300 border-purple-500/30' },
    { id: 'quotation', name: 'Quote', color: 'bg-pink-500/10 dark:bg-pink-500/20 text-pink-700 dark:text-pink-300 border-pink-500/30' },
    { id: 'agreement', name: 'Agreement', color: 'bg-orange-500/10 dark:bg-orange-500/20 text-orange-700 dark:text-orange-300 border-orange-500/30' },
    { id: 'payment', name: 'Payment', color: 'bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30' },
    { id: 'kickoff', name: 'Kickoff', color: 'bg-cyan-500/10 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border-cyan-500/30' },
    { id: 'complete', name: 'Complete', color: 'bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30' }
  ];

  // React Query: Subordinate Leads
  const { data: subordinateLeadsData = [], isLoading: loading, refetch: refetchLeads } = useSubordinateLeads();
  const subordinateLeads = subordinateLeadsData?.leads || subordinateLeadsData || [];
  const subordinates = subordinateLeadsData?.subordinates || [];

  // React Query: Stats using hooks
  const { data: todayStats } = useManagerTodayStats();
  const { data: performance } = useManagerPerformance();
  const { data: targetVsAchievement } = useManagerTargetVsAchievement();

  // React Query: Team Funnel Data
  const { data: funnelData } = useQuery({
    queryKey: ['team-funnel-summary'],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/analytics/funnel-summary`);
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // React Query: MOM Review Data
  const { data: momReviewData, refetch: refetchMom } = useQuery({
    queryKey: ['manager-mom-review', 'month'],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/analytics/manager-mom-review?period=month`);
      return response.data;
    },
    staleTime: 3 * 60 * 1000,
    enabled: momSectionOpen, // Only fetch when section is opened
  });

  // Mutations from useLeads hook
  const pauseMutation = usePauseLead();
  const resumeMutation = useResumeLead();

  const handlePauseLead = async (leadId, e) => {
    e?.stopPropagation();
    pauseMutation.mutate(leadId, {
      onSuccess: () => {
        toast.success('Lead paused');
        queryClient.invalidateQueries({ queryKey: ['manager', 'subordinate-leads'] });
      },
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to pause lead')
    });
  };

  const handleResumeLead = async (leadId, e) => {
    e?.stopPropagation();
    resumeMutation.mutate(leadId, {
      onSuccess: () => {
        toast.success('Lead resumed');
        queryClient.invalidateQueries({ queryKey: ['manager', 'subordinate-leads'] });
      },
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to resume lead')
    });
  };

  // Generate MOM PDF Report
  const generateMomPDF = () => {
    if (!momReviewData) return;
    try {
      const doc = new jsPDF('l', 'mm', 'a4');
      const pageWidth = doc.internal.pageSize.getWidth();
      
      doc.setFontSize(16);
      doc.text('MOM Review Report - Team Performance', pageWidth / 2, 15, { align: 'center' });
      
      doc.setFontSize(10);
      doc.setTextColor(100);
      doc.text(`Generated: ${new Date().toLocaleDateString()} | Manager: ${user?.name || 'Manager'}`, pageWidth / 2, 22, { align: 'center' });
      
      // Summary
      const summary = momReviewData.overall_summary || {};
      doc.setFillColor(240, 249, 255);
      doc.roundedRect(14, 28, pageWidth - 28, 15, 2, 2, 'F');
      doc.setFontSize(9);
      doc.setTextColor(30);
      doc.text(`Team: ${summary.total_reportees || 0} | Meetings: ${summary.total_meetings || 0} | With MOM: ${summary.meetings_with_mom || 0} | Without: ${summary.meetings_without_mom || 0} | Rate: ${summary.mom_completion_rate || 0}%`, 20, 36);
      
      // Employee table
      const empData = (momReviewData.employee_summaries || []).map(emp => [
        emp.employee_code || '-',
        emp.name || '-',
        emp.total_meetings || 0,
        emp.with_mom || 0,
        emp.without_mom || 0,
        `${emp.completion_rate || 0}%`,
        emp.sent_to_client || 0
      ]);
      
      doc.autoTable({
        startY: 48,
        head: [['Emp ID', 'Name', 'Total', 'With MOM', 'Without', 'Rate', 'Sent']],
        body: empData,
        theme: 'striped',
        headStyles: { fillColor: [59, 130, 246], fontSize: 8 },
        bodyStyles: { fontSize: 7 }
      });
      
      doc.save(`MOM_Review_${new Date().toISOString().split('T')[0]}.pdf`);
      toast.success('PDF downloaded');
    } catch (error) {
      toast.error('Failed to generate PDF');
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
  const filteredLeads = (subordinateLeads || []).filter(lead => {
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
  (filteredLeads || []).forEach(lead => {
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
        <Button onClick={() => refetchLeads()} variant="outline" className="rounded-sm">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Profile Performance Card for Manager */}
      <ProfilePerformanceCard
        user={user}
        stats={{
          dealsWon: targetVsAchievement?.achievements?.total_closed || 0,
          dealsInProgress: (subordinateLeads || []).filter(l => l?.status && !['closed', 'lost', 'paused'].includes(l.status)).length,
          revenue: targetVsAchievement?.achievements?.total_revenue || 0,
          conversionRate: (subordinateLeads || []).length > 0 
            ? Math.round((targetVsAchievement?.achievements?.total_closed || 0) / subordinateLeads.length * 100) 
            : 0,
          targetAchievement: targetVsAchievement?.percentage || 0,
          teamSize: Object.keys(leadsByEmployee || {}).length,
          trend: (targetVsAchievement?.percentage || 0) >= 50 ? 'up' : 'down'
        }}
        variant="manager"
        data-testid="manager-profile-performance-card"
      />

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
                  {(todayStats.absent_employees || []).map(e => e?.name || 'Unknown').join(', ')}
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

      {/* Team Funnel Activity - Replaces standalone pages */}
      <Collapsible open={funnelSectionOpen} onOpenChange={setFunnelSectionOpen}>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CollapsibleTrigger className="w-full">
            <CardHeader className="py-3 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-600" />
                  Team Funnel Activity
                  {funnelData?.summary && (
                    <Badge variant="outline" className="ml-2">
                      {funnelData.summary.total_leads} leads
                    </Badge>
                  )}
                </CardTitle>
                {funnelSectionOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="pt-0">
              {funnelData ? (
                <div className="space-y-4">
                  {/* Funnel Stage Cards - Clickable to filter leads */}
                  <div className="grid grid-cols-9 gap-2">
                    {(funnelStages || []).map((stage, index) => {
                      const count = funnelData.stage_counts?.[stage.id] || 0;
                      return (
                        <div key={stage.id} className="text-center relative">
                          <div 
                            className={`rounded-xl py-4 px-2 border-2 ${stage.color} hover:scale-105 transition-transform cursor-pointer`}
                            onClick={() => navigate(`/leads?stage=${stage.id}`)}
                          >
                            <p className="text-2xl font-bold">{count}</p>
                            <p className="text-xs mt-1 font-medium">{stage.name}</p>
                          </div>
                          {index < 8 && (
                            <ChevronRight className="w-4 h-4 absolute -right-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-600 z-10" />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-4 gap-3 p-4 bg-zinc-500/5 dark:bg-zinc-500/10 rounded-lg">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-zinc-700 dark:text-zinc-300">{funnelData.summary?.total_leads || 0}</p>
                      <p className="text-xs text-zinc-500">Total Leads</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-600">{funnelData.summary?.in_progress || 0}</p>
                      <p className="text-xs text-zinc-500">In Progress</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-emerald-600">{funnelData.summary?.completed || 0}</p>
                      <p className="text-xs text-zinc-500">Completed</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-indigo-600">{funnelData.summary?.conversion_rate?.toFixed(1) || 0}%</p>
                      <p className="text-xs text-zinc-500">Conversion</p>
                    </div>
                  </div>

                  {/* Employee Breakdown */}
                  {funnelData.employee_breakdown?.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">By Team Member</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-zinc-200 dark:border-zinc-700">
                              <th className="text-left py-2 font-medium text-zinc-600 dark:text-zinc-400">Employee</th>
                              {(funnelStages || []).slice(0, 5).map(stage => (
                                <th key={stage.id} className="text-center py-2 font-medium text-zinc-600 dark:text-zinc-400">{stage.name}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {(funnelData?.employee_breakdown || []).slice(0, 10).map((emp, idx) => (
                              <tr key={idx} className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                                <td className="py-2 font-medium">{emp.employee_name}</td>
                                {(funnelStages || []).slice(0, 5).map(stage => (
                                  <td key={stage.id} className="py-2 text-center">
                                    <span 
                                      className={`px-2 py-0.5 rounded text-xs font-medium cursor-pointer hover:opacity-80 ${
                                        emp.stage_counts?.[stage.id] > 0 ? stage.color : 'text-zinc-400'
                                      }`}
                                      onClick={() => navigate(`/leads?stage=${stage.id}&employee=${emp.employee_id}`)}
                                    >
                                      {emp.stage_counts?.[stage.id] || 0}
                                    </span>
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Info about funnel-only creation */}
                  <div className="flex items-center gap-2 p-3 bg-blue-500/10 dark:bg-blue-500/20 rounded-lg text-sm">
                    <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0" />
                    <span className="text-zinc-600 dark:text-zinc-400">
                      All funnel items (Pricing, SOW, Quotes, Agreements) are created through <strong>Lead → Funnel</strong> only. 
                      Click on any stage to view leads at that stage.
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 text-zinc-500">Loading funnel data...</div>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

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
                  {(targetVsAchievement?.employee_stats || []).filter(e => e.employee_name.trim()).map((emp, idx) => (
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

      {/* MOM Review Section - Collapsible */}
      <Collapsible open={momSectionOpen} onOpenChange={setMomSectionOpen}>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CollapsibleTrigger className="w-full">
            <CardHeader className="py-3 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  MOM Review - Team Performance
                  {momReviewData?.overall_summary && (
                    <Badge variant="outline" className="ml-2">
                      {momReviewData.overall_summary.mom_completion_rate || 0}% Complete
                    </Badge>
                  )}
                </CardTitle>
                <div className="flex items-center gap-2">
                  {momSectionOpen && momReviewData && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        generateMomPDF();
                      }}
                      className="text-xs"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      PDF
                    </Button>
                  )}
                  {momSectionOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                </div>
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="pt-0">
              {momReviewData ? (
                <div className="space-y-4">
                  {/* MOM Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="text-center p-3 bg-zinc-500/10 dark:bg-zinc-500/20 rounded-lg">
                      <Users className="w-5 h-5 mx-auto mb-1 text-blue-600" />
                      <div className="text-xl font-bold">{momReviewData.overall_summary?.total_reportees || 0}</div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-400">Team Members</div>
                    </div>
                    <div className="text-center p-3 bg-indigo-500/10 dark:bg-indigo-500/20 rounded-lg">
                      <MessageSquare className="w-5 h-5 mx-auto mb-1 text-indigo-600" />
                      <div className="text-xl font-bold">{momReviewData.overall_summary?.total_meetings || 0}</div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-400">Total Meetings</div>
                    </div>
                    <div className="text-center p-3 bg-green-500/10 dark:bg-green-500/20 rounded-lg">
                      <CheckCircle className="w-5 h-5 mx-auto mb-1 text-green-600 dark:text-green-400" />
                      <div className="text-xl font-bold text-green-700 dark:text-green-400">{momReviewData.overall_summary?.meetings_with_mom || 0}</div>
                      <div className="text-xs text-green-600 dark:text-green-400">With MOM</div>
                    </div>
                    <div className="text-center p-3 bg-red-500/10 dark:bg-red-500/20 rounded-lg">
                      <XCircle className="w-5 h-5 mx-auto mb-1 text-red-600 dark:text-red-400" />
                      <div className="text-xl font-bold text-red-700 dark:text-red-400">{momReviewData.overall_summary?.meetings_without_mom || 0}</div>
                      <div className="text-xs text-red-600 dark:text-red-400">Pending MOM</div>
                    </div>
                    <div className="text-center p-3 bg-blue-500/10 dark:bg-blue-500/20 rounded-lg">
                      <Send className="w-5 h-5 mx-auto mb-1 text-blue-600 dark:text-blue-400" />
                      <div className="text-xl font-bold text-blue-700 dark:text-blue-400">{momReviewData.overall_summary?.mom_sent_to_client || 0}</div>
                      <div className="text-xs text-blue-600 dark:text-blue-400">Sent to Client</div>
                    </div>
                  </div>

                  {/* Completion Rate Progress */}
                  <div className="flex items-center gap-4 p-3 bg-zinc-500/10 dark:bg-zinc-500/20 rounded-lg">
                    <span className="text-sm text-zinc-600 dark:text-zinc-400">MOM Completion Rate:</span>
                    <div className="flex-1">
                      <Progress value={momReviewData.overall_summary?.mom_completion_rate || 0} className="h-2" />
                    </div>
                    <span className={`text-sm font-semibold ${
                      (momReviewData.overall_summary?.mom_completion_rate || 0) >= 80 ? 'text-green-600' :
                      (momReviewData.overall_summary?.mom_completion_rate || 0) >= 50 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {momReviewData.overall_summary?.mom_completion_rate || 0}%
                    </span>
                  </div>

                  {/* Employee MOM List */}
                  {momReviewData.employee_summaries?.length > 0 ? (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-zinc-700">Team Member Details</h4>
                      {(momReviewData?.employee_summaries || []).map((emp) => (
                        <Collapsible
                          key={emp.employee_id}
                          open={expandedMomEmployee === emp.employee_id}
                          onOpenChange={() => setExpandedMomEmployee(
                            expandedMomEmployee === emp.employee_id ? null : emp.employee_id
                          )}
                        >
                          <CollapsibleTrigger className="w-full">
                            <div className="flex items-center justify-between p-3 bg-white border rounded-lg hover:bg-zinc-50 cursor-pointer">
                              <div className="flex items-center gap-3">
                                {expandedMomEmployee === emp.employee_id ? 
                                  <ChevronDown className="w-4 h-4 text-zinc-400" /> : 
                                  <ChevronRight className="w-4 h-4 text-zinc-400" />
                                }
                                <span className="font-medium">{emp.name}</span>
                                <Badge variant="outline" className="text-xs">{emp.employee_code}</Badge>
                              </div>
                              <div className="flex items-center gap-4">
                                <span className="text-sm text-zinc-500">{emp.total_meetings} meetings</span>
                                <span className="text-sm text-green-600">{emp.with_mom} with MOM</span>
                                <span className="text-sm text-red-600">{emp.without_mom} pending</span>
                                <Badge className={`${
                                  emp.completion_rate >= 80 ? 'bg-green-100 text-green-800' :
                                  emp.completion_rate >= 50 ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                                }`}>
                                  {emp.completion_rate}%
                                </Badge>
                              </div>
                            </div>
                          </CollapsibleTrigger>
                          <CollapsibleContent>
                            <div className="ml-8 mt-2 space-y-2">
                              {emp.meetings?.map((meeting, idx) => (
                                <div 
                                  key={meeting.id || idx}
                                  className={`p-3 rounded-lg border text-sm ${
                                    meeting.has_mom ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <Building2 className="w-4 h-4 text-zinc-400" />
                                      <span className="font-medium">{meeting.company}</span>
                                      {meeting.has_mom ? (
                                        <Badge className="bg-green-100 text-green-800 text-xs">MOM Recorded</Badge>
                                      ) : (
                                        <Badge className="bg-red-100 text-red-800 text-xs">No MOM</Badge>
                                      )}
                                    </div>
                                    <span className="text-xs text-zinc-500">
                                      {meeting.meeting_date ? new Date(meeting.meeting_date).toLocaleDateString() : '-'}
                                    </span>
                                  </div>
                                  {meeting.has_mom && meeting.mom?.summary && (
                                    <div className="mt-2 p-2 bg-white rounded text-xs text-zinc-600">
                                      <strong>Summary:</strong> {meeting.mom.summary}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </CollapsibleContent>
                        </Collapsible>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-4 text-zinc-500">No meeting data found for this period</div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4 text-zinc-500">Loading MOM data...</div>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

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
          {(subordinates || []).map(sub => (
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
          {(statusOptions || []).map(opt => (
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
            {Object.entries(leadsByEmployee || {}).map(([empName, data]) => (
              <div 
                key={empName}
                className="p-3 bg-zinc-50 rounded-sm border border-zinc-100 cursor-pointer hover:bg-zinc-100 transition-colors"
                onClick={() => {
                  const emp = (subordinates || []).find(s => `${s.first_name} ${s.last_name}` === empName);
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

      {/* Leads Table - Using SalesDataTable (GOVERNANCE: No manual tables) */}
      <Card className="border-zinc-200 shadow-none rounded-sm overflow-hidden">
        <CardHeader className="pb-2 border-b border-zinc-100">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            Team Leads
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <LeadsTable
            onRowClick={(lead) => handleLeadClick(lead)}
            onPause={(lead) => handlePauseLead(lead.id)}
            onResume={(lead) => handleResumeLead(lead.id)}
            externalFilters={selectedEmployee ? { assigned_to: selectedEmployee } : {}}
            className="border-0 rounded-none"
          />
        </CardContent>
      </Card>
    </div>
  );
};

export default ManagerLeadsDashboard;
