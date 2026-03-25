import React, { useState, useContext, useMemo } from 'react';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  CalendarCheck, DollarSign, Users, Clock, AlertTriangle,
  CheckCircle, Phone, RefreshCw, ChevronRight, X,
  MessageSquare, UserCheck, ArrowRightLeft, History, Plus, Send, Mail,
  ChevronDown, LayoutList, Users2
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { isManager as checkIsManager } from '../utils/roles';
import { FollowUpsTable } from '../components/sales';
import { cn } from '../lib/utils';

const ENTITY_LABELS = {
  lead: 'Lead',
  meeting: 'Meeting',
  pricing_plan: 'Pricing',
  sow: 'SOW',
  quotation: 'Quotation',
  agreement: 'Agreement',
  payment: 'Payment',
  kickoff: 'Kickoff',
  project: 'Project',
};

const ENTITY_COLORS = {
  lead: 'bg-purple-100 text-purple-700',
  meeting: 'bg-green-100 text-green-700',
  pricing_plan: 'bg-amber-100 text-amber-700',
  sow: 'bg-teal-100 text-teal-700',
  quotation: 'bg-cyan-100 text-cyan-700',
  agreement: 'bg-orange-100 text-orange-700',
  payment: 'bg-blue-100 text-blue-700',
  kickoff: 'bg-pink-100 text-pink-700',
  project: 'bg-emerald-100 text-emerald-700',
};

const FollowUps = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const dk = theme === 'dark';
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedFollowUp, setSelectedFollowUp] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [updateNotes, setUpdateNotes] = useState('');
  const [updateOutcome, setUpdateOutcome] = useState('');
  const [closeNotes, setCloseNotes] = useState('');
  const [closeOutcome, setCloseOutcome] = useState('');
  const [nextDate, setNextDate] = useState('');
  const [nextNotes, setNextNotes] = useState('');
  const [nextPriority, setNextPriority] = useState('medium');
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const [showNextDialog, setShowNextDialog] = useState(false);
  const [showReassignDialog, setShowReassignDialog] = useState(false);
  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignReason, setReassignReason] = useState('');
  const [transferAll, setTransferAll] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState({ entity_type: 'lead', entity_id: '', lead_id: '', client_name: '', due_date: '', due_time: '', notes: '', priority: 'medium' });
  const [viewMode, setViewMode] = useState('grouped'); // 'table' | 'grouped'
  const [expandedClients, setExpandedClients] = useState(new Set());
  
  // Email state
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [emailData, setEmailData] = useState({ subject: '', body: '', recipient_email: '', follow_up_id: '' });
  const [sendingEmail, setSendingEmail] = useState(false);

  const isManager = checkIsManager(user);

  // Fetch follow-ups from the dedicated collection (for stats)
  const { data: followUpsRaw = { data: [] }, isLoading, refetch } = useQuery({
    queryKey: ['follow-ups', statusFilter, filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all' && statusFilter !== 'escalated') params.append('status', statusFilter);
      if (filter !== 'all') params.append('entity_type', filter);
      params.append('page_size', '500');
      const res = await axios.get(`${API}/follow-ups?${params}`);
      return res.data;
    },
  });
  const followUps = Array.isArray(followUpsRaw) ? followUpsRaw : (followUpsRaw?.data || []);

  // Fetch escalations for managers
  const { data: escalations } = useQuery({
    queryKey: ['follow-up-escalations'],
    queryFn: async () => {
      const res = await axios.get(`${API}/follow-ups/escalations`);
      return res.data;
    },
    enabled: isManager,
  });

  // Fetch sales team users for reassignment
  const { data: salesUsers = [] } = useQuery({
    queryKey: ['sales-users-for-reassign'],
    queryFn: async () => {
      const res = await axios.get(`${API}/users`);
      const users = Array.isArray(res.data) ? res.data : res.data?.items || [];
      return (users || []).filter(u => ['executive', 'sales_executive', 'sales_manager'].includes(u.role));
    },
    enabled: isManager,
  });

  // Fetch leads for create dialog
  const { data: leads = [] } = useQuery({
    queryKey: ['leads-for-followup-create'],
    queryFn: async () => {
      const res = await axios.get(`${API}/leads?page_size=500`);
      return Array.isArray(res.data) ? res.data : res.data?.data || res.data?.items || [];
    },
    enabled: showCreateDialog,
  });

  // Mutations
  const addUpdateMutation = useMutation({
    mutationFn: async ({ id, notes, outcome }) => {
      const res = await axios.put(`${API}/follow-ups/${id}/update`, { notes, outcome });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      queryClient.invalidateQueries({ queryKey: ['follow-up-detail'] });
      toast.success('Update added');
      setUpdateNotes('');
      setUpdateOutcome('');
      refreshDetail();
    },
  });

  const closeMutation = useMutation({
    mutationFn: async ({ id, notes, outcome }) => {
      const res = await axios.put(`${API}/follow-ups/${id}/close`, { notes, outcome });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      toast.success('Follow-up closed');
      setShowCloseDialog(false);
      setCloseNotes('');
      setCloseOutcome('');
      setDetailOpen(false);
    },
  });

  const scheduleNextMutation = useMutation({
    mutationFn: async ({ id, due_date, notes, priority }) => {
      const res = await axios.post(`${API}/follow-ups/${id}/schedule-next`, { due_date, notes, priority });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      toast.success('Next follow-up scheduled');
      setShowNextDialog(false);
      setNextDate('');
      setNextNotes('');
      setDetailOpen(false);
    },
  });

  const reassignMutation = useMutation({
    mutationFn: async ({ id, new_owner_id, reason, transfer_all_stages }) => {
      const res = await axios.post(`${API}/follow-ups/${id}/reassign`, { new_owner_id, reason, transfer_all_stages });
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      toast.success(data.message || 'Reassigned successfully');
      setShowReassignDialog(false);
      setReassignUserId('');
      setReassignReason('');
      setDetailOpen(false);
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/follow-ups`, data);
      return res.data;
    },
    onSuccess: async (data) => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      toast.success('Follow-up created');
      setShowCreateDialog(false);
      setCreateForm({ entity_type: 'lead', entity_id: '', lead_id: '', client_name: '', due_date: '', due_time: '', notes: '', priority: 'medium' });
      
      // Fetch email template and show Send Email dialog
      if (data?.id) {
        try {
          const templateRes = await axios.get(`${API}/follow-ups/${data.id}/email-template`);
          setEmailData({
            follow_up_id: data.id,
            subject: templateRes.data.subject || '',
            body: templateRes.data.body || '',
            recipient_email: templateRes.data.recipient_email || '',
            client_name: templateRes.data.client_name || '',
            company: templateRes.data.company || '',
            notes: data.notes || '',
            schedule_display: templateRes.data.schedule_display || '',
          });
          setShowEmailDialog(true);
        } catch {
          // Email template not available, just skip
        }
      }
    },
  });
  
  // Send email handler
  const handleSendEmail = async () => {
    if (!emailData.follow_up_id || !emailData.recipient_email) return;
    setSendingEmail(true);
    try {
      const res = await axios.post(`${API}/follow-ups/${emailData.follow_up_id}/send-email`, {
        subject: emailData.subject,
        body: emailData.body,
        recipient_email: emailData.recipient_email,
      });
      toast.success(res.data.message || 'Email sent');
      setShowEmailDialog(false);
      setEmailData({ subject: '', body: '', recipient_email: '', follow_up_id: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  const refreshDetail = async () => {
    if (!selectedFollowUp) return;
    try {
      const res = await axios.get(`${API}/follow-ups/${selectedFollowUp.id}`);
      setSelectedFollowUp(res.data);
    } catch { /* ignore */ }
  };

  const openDetail = (fu) => {
    setSelectedFollowUp(fu);
    setDetailOpen(true);
    setUpdateNotes('');
    setUpdateOutcome('');
  };

  // Stats
  const overdueCount = (followUps || []).filter(f => {
    const due = new Date(f.due_date);
    return due < new Date(new Date().setHours(0, 0, 0, 0)) && f.status === 'open';
  }).length;
  const openCount = (followUps || []).filter(f => f.status === 'open').length;
  const escalationCount = escalations?.total || 0;

  // Per-stage breakdown
  const stageCounts = useMemo(() => {
    const counts = {};
    (followUps || []).forEach(f => {
      const type = f.entity_type || 'unknown';
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  }, [followUps]);

  // Filter and search - still used for stats
  const filteredFollowUps = followUps;

  // Grouped by client
  const clientGroups = useMemo(() => {
    const groups = {};
    (followUps || []).forEach(fu => {
      const key = fu.client_name || 'Unknown';
      if (!groups[key]) groups[key] = { client: key, items: [], openCount: 0, closedCount: 0 };
      groups[key].items.push(fu);
      if (fu.status === 'open') groups[key].openCount++;
      else groups[key].closedCount++;
    });
    // Sort: clients with open items first, then by name
    return Object.values(groups).sort((a, b) => {
      if (a.openCount > 0 && b.openCount === 0) return -1;
      if (a.openCount === 0 && b.openCount > 0) return 1;
      return a.client.localeCompare(b.client);
    });
  }, [followUps]);

  // Auto-expand clients with open follow-ups on first load
  useMemo(() => {
    const openClients = clientGroups.filter(g => g.openCount > 0).map(g => g.client);
    if (openClients.length > 0 && expandedClients.size === 0) {
      setExpandedClients(new Set(openClients));
    }
  }, [clientGroups]);

  const toggleClient = (client) => {
    setExpandedClients(prev => {
      const next = new Set(prev);
      if (next.has(client)) next.delete(client);
      else next.add(client);
      return next;
    });
  };

  const getDaysLabel = (dateStr) => {
    const due = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    due.setHours(0, 0, 0, 0);
    const diff = Math.floor((due - today) / (1000 * 60 * 60 * 24));
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    return `In ${diff} days`;
  };

  return (
    <div className="p-6 space-y-6" data-testid="follow-ups-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">Follow-ups</h1>
          <p className="text-zinc-500 text-sm">Track and manage client follow-ups across all funnel stages</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button onClick={() => setShowCreateDialog(true)} size="sm" className="bg-zinc-950 text-white hover:bg-zinc-800" data-testid="create-follow-up-btn">
            <Plus className="w-4 h-4 mr-1" /> New Follow-up
          </Button>
          <Button onClick={refetch} variant="outline" size="sm" data-testid="refresh-follow-ups-btn">
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards - Click to filter */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card 
          className={`bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E] cursor-pointer hover:shadow-md transition-shadow ${statusFilter === 'overdue' ? 'ring-2 ring-red-400' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'overdue' ? 'open' : 'overdue')}
        >
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-100 dark:bg-red-950/30 rounded-lg"><AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" /></div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white" data-testid="overdue-count">{overdueCount}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Overdue</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={`bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E] cursor-pointer hover:shadow-md transition-shadow ${statusFilter === 'open' ? 'ring-2 ring-yellow-400' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'open' ? 'all' : 'open')}
        >
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-yellow-100 dark:bg-yellow-950/30 rounded-lg"><Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" /></div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white" data-testid="open-count">{openCount}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Open</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={`bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E] cursor-pointer hover:shadow-md transition-shadow ${statusFilter === 'all' ? 'ring-2 ring-green-400' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          <CardContent className="pt-5 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-green-100 dark:bg-emerald-950/30 rounded-lg"><CheckCircle className="w-5 h-5 text-green-600 dark:text-emerald-400" /></div>
              <div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">{followUps.length}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>
        {isManager && (
          <Card 
            className={`border-zinc-200 dark:border-[#2A2A2E] cursor-pointer hover:shadow-md transition-shadow ${escalationCount > 0 ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900/40' : 'bg-white dark:bg-[#1A1A1C]'} ${statusFilter === 'escalated' ? 'ring-2 ring-red-500' : ''}`}
            onClick={() => setStatusFilter(statusFilter === 'escalated' ? 'open' : 'escalated')}
          >
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-lg ${escalationCount > 0 ? 'bg-red-200 dark:bg-red-950/40' : 'bg-zinc-100 dark:bg-[#2A2A2E]'}`}>
                  <AlertTriangle className={`w-5 h-5 ${escalationCount > 0 ? 'text-red-700 dark:text-red-400' : 'text-zinc-500 dark:text-zinc-400'}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-white" data-testid="escalation-count">{escalationCount}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Escalations (2d+)</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Stage Breakdown */}
      {Object.keys(stageCounts || {}).length > 0 && (
        <Card className={`shadow-none rounded-sm ${dk ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'}`} data-testid="stage-breakdown-card">
          <CardContent className="py-4">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">By Funnel Stage</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(ENTITY_LABELS || {}).map(([key, label]) => {
                const count = stageCounts[key] || 0;
                if (count === 0) return null;
                return (
                  <button
                    key={key}
                    onClick={() => setFilter(filter === key ? 'all' : key)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                      filter === key
                        ? 'ring-2 ring-zinc-400 shadow-sm'
                        : 'hover:shadow-sm'
                    } ${ENTITY_COLORS[key] || 'bg-zinc-100 text-zinc-600'}`}
                    data-testid={`stage-count-${key}`}
                  >
                    <span>{label}</span>
                    <span className="font-bold">{count}</span>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Escalation Alert for Managers */}
      {isManager && escalationCount > 0 && (
        <Card className={dk ? 'border-red-900/40 bg-red-950/20' : 'border-red-300 bg-red-50'}>
          <CardContent className="py-4">
            <div className="flex items-center gap-3 mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span className="font-semibold text-red-800">Escalated Follow-ups ({escalationCount})</span>
              <span className="text-xs text-red-600">Overdue by 2+ days — requires manager action</span>
            </div>
            <div className="space-y-2">
              {(escalations?.items || []).slice(0, 5).map(esc => (
                <div key={esc.id} className={`flex items-center justify-between p-3 rounded border cursor-pointer ${dk ? 'bg-[#222226] border-[#2A2A2E] hover:bg-[#2A2A2E]' : 'bg-white border-red-200 hover:bg-red-50'}`} onClick={() => openDetail(esc)} data-testid={`escalation-item-${esc.id}`}>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <div>
                      <span className="font-medium text-zinc-800 text-sm">{esc.client_name}</span>
                      <span className={`ml-2 px-2 py-0.5 text-xs rounded font-semibold ${ENTITY_COLORS[esc.entity_type] || 'bg-zinc-100 text-zinc-600'}`}>{ENTITY_LABELS[esc.entity_type]}</span>
                    </div>
                    <span className="text-xs text-zinc-500">Assigned: {esc.assigned_to_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive" className="text-xs">{esc.days_overdue}d overdue</Badge>
                    <ChevronRight className="w-4 h-4 text-zinc-400" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters + View Toggle */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 flex-wrap">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32 border-zinc-300 bg-white dark:bg-[#1A1A1C] dark:border-[#2A2A2E]" data-testid="follow-up-status-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
              <SelectItem value="overdue">Overdue</SelectItem>
              {isManager && <SelectItem value="escalated">Escalated</SelectItem>}
            </SelectContent>
          </Select>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 border-zinc-300 bg-white dark:bg-[#1A1A1C] dark:border-[#2A2A2E]" data-testid="follow-up-type-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Stages</SelectItem>
              {Object.entries(ENTITY_LABELS || {}).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-1 bg-zinc-100 dark:bg-[#222226] rounded-md p-0.5" data-testid="view-mode-toggle">
          <button
            onClick={() => setViewMode('grouped')}
            className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all",
              viewMode === 'grouped' ? 'bg-white dark:bg-[#1A1A1C] shadow-sm text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-700'
            )}
            data-testid="view-mode-grouped"
          >
            <Users2 className="w-3.5 h-3.5" /> By Client
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all",
              viewMode === 'table' ? 'bg-white dark:bg-[#1A1A1C] shadow-sm text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-700'
            )}
            data-testid="view-mode-table"
          >
            <LayoutList className="w-3.5 h-3.5" /> Table
          </button>
        </div>
      </div>

      {/* Follow-ups View */}
      {viewMode === 'table' ? (
        <FollowUpsTable
          onRowClick={(fu) => openDetail(fu)}
          onComplete={(fu) => {
            setSelectedFollowUp(fu);
            setShowCloseDialog(true);
          }}
          onReschedule={(fu) => {
            setSelectedFollowUp(fu);
            setShowNextDialog(true);
          }}
          externalFilters={{
            ...(statusFilter && statusFilter !== 'all' && statusFilter !== 'escalated' && statusFilter !== 'overdue' ? { status: statusFilter } : {}),
            ...(statusFilter === 'overdue' ? { overdue_only: true } : {}),
            ...(filter !== 'all' ? { entity_type: filter } : {}),
          }}
          className="border border-zinc-200 rounded-sm"
        />
      ) : (
        <div className="space-y-3" data-testid="grouped-follow-ups">
          {clientGroups.length === 0 && (
            <Card className={dk ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'}>
              <CardContent className="py-12 text-center">
                <p className="text-zinc-400 text-sm">No follow-ups found.</p>
              </CardContent>
            </Card>
          )}
          {clientGroups.map(group => {
            const isOpen = expandedClients.has(group.client);
            return (
              <Card key={group.client} className={cn("overflow-hidden transition-shadow", dk ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200', isOpen && 'shadow-sm')} data-testid={`client-group-${group.client}`}>
                {/* Client Header */}
                <button
                  onClick={() => toggleClient(group.client)}
                  className={cn("w-full flex items-center justify-between px-5 py-3.5 text-left transition-colors",
                    isOpen ? (dk ? 'bg-[#222226]' : 'bg-zinc-50') : 'hover:bg-zinc-50 dark:hover:bg-[#222226]'
                  )}
                  data-testid={`client-toggle-${group.client}`}
                >
                  <div className="flex items-center gap-3">
                    <ChevronDown className={cn("w-4 h-4 text-zinc-400 transition-transform", isOpen ? '' : '-rotate-90')} />
                    <span className="font-semibold text-zinc-900 dark:text-white text-sm">{group.client}</span>
                    <span className="text-xs text-zinc-400">({group.items.length} follow-up{group.items.length !== 1 ? 's' : ''})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {group.openCount > 0 && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium border border-amber-200">{group.openCount} open</span>
                    )}
                    {group.closedCount > 0 && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-500 font-medium border border-zinc-200">{group.closedCount} closed</span>
                    )}
                  </div>
                </button>
                {/* Expanded Rows */}
                {isOpen && (
                  <div className="border-t border-zinc-100 dark:border-[#2A2A2E]">
                    {/* Compact Header Row */}
                    <div className={cn("grid grid-cols-12 gap-2 px-5 py-2 text-[10px] font-semibold uppercase tracking-wider",
                      dk ? 'text-zinc-500 bg-[#1A1A1C]' : 'text-zinc-400 bg-zinc-50/50'
                    )}>
                      <div className="col-span-2">Type</div>
                      <div className="col-span-3">Notes</div>
                      <div className="col-span-2">Due Date</div>
                      <div className="col-span-1">Priority</div>
                      <div className="col-span-1">Client</div>
                      <div className="col-span-1">Status</div>
                      <div className="col-span-2 text-right">Actions</div>
                    </div>
                    {group.items
                      .sort((a, b) => (a.status === 'open' ? -1 : 1) - (b.status === 'open' ? -1 : 1) || new Date(a.due_date) - new Date(b.due_date))
                      .map(fu => {
                        const dueDate = fu.due_date ? new Date(fu.due_date) : null;
                        const today = new Date(); today.setHours(0,0,0,0);
                        const isOverdue = dueDate && dueDate < today && fu.status === 'open';
                        const isDueToday = dueDate && dueDate.toDateString() === today.toDateString();
                        const clientAction = (fu.history || []).filter(h => h.action?.startsWith('client_')).pop();
                        const priorityColors = { high: 'bg-red-50 text-red-700', medium: 'bg-yellow-50 text-yellow-700', low: 'bg-green-50 text-green-700' };

                        return (
                          <div
                            key={fu.id}
                            onClick={() => openDetail(fu)}
                            className={cn("grid grid-cols-12 gap-2 px-5 py-2.5 items-center cursor-pointer border-t transition-colors text-sm",
                              dk ? 'border-[#2A2A2E] hover:bg-[#222226]' : 'border-zinc-100 hover:bg-zinc-50',
                              fu.status === 'closed' && 'opacity-60'
                            )}
                            data-testid={`followup-row-${fu.id}`}
                          >
                            <div className="col-span-2">
                              <span className={cn("text-[11px] px-2 py-0.5 rounded font-medium capitalize", ENTITY_COLORS[fu.entity_type] || 'bg-zinc-100 text-zinc-600')}>
                                {ENTITY_LABELS[fu.entity_type] || fu.entity_type}
                              </span>
                            </div>
                            <div className="col-span-3">
                              <span className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-1">{fu.notes || '-'}</span>
                            </div>
                            <div className="col-span-2">
                              <span className={cn("text-xs px-2 py-0.5 rounded",
                                isOverdue && "bg-red-50 text-red-700 font-medium",
                                isDueToday && !isOverdue && "bg-yellow-50 text-yellow-700",
                                !isOverdue && !isDueToday && "text-zinc-600"
                              )}>
                                {dueDate ? dueDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '-'}
                              </span>
                            </div>
                            <div className="col-span-1">
                              <span className={cn("text-[11px] px-2 py-0.5 rounded capitalize", priorityColors[fu.priority] || priorityColors.medium)}>
                                {fu.priority || 'Medium'}
                              </span>
                            </div>
                            <div className="col-span-1">
                              {clientAction?.action === 'client_closed' ? (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700 font-medium">Confirmed</span>
                              ) : clientAction?.action === 'client_reschedule' ? (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium">Reschedule</span>
                              ) : (
                                <span className="text-[10px] text-zinc-400">—</span>
                              )}
                            </div>
                            <div className="col-span-1">
                              <span className={cn("text-[11px] px-2 py-0.5 rounded capitalize",
                                fu.status === 'open' ? 'bg-blue-50 text-blue-700' : 'bg-zinc-100 text-zinc-500'
                              )}>
                                {fu.status || 'Open'}
                              </span>
                            </div>
                            <div className="col-span-2 flex justify-end gap-1">
                              {fu.status !== 'closed' && (
                                <>
                                  <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-green-600 hover:bg-green-50" onClick={(e) => { e.stopPropagation(); setSelectedFollowUp(fu); setShowCloseDialog(true); }} data-testid={`complete-btn-${fu.id}`}>
                                    <CheckCircle className="w-3 h-3 mr-1" /> Close
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px] text-zinc-500 hover:bg-zinc-100" onClick={(e) => { e.stopPropagation(); setSelectedFollowUp(fu); setShowNextDialog(true); }} data-testid={`reschedule-btn-${fu.id}`}>
                                    <RefreshCw className="w-3 h-3 mr-1" /> Next
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span>{selectedFollowUp?.client_name}</span>
              <span className={`px-2 py-0.5 text-xs rounded ${ENTITY_COLORS[selectedFollowUp?.entity_type] || ''}`}>{ENTITY_LABELS[selectedFollowUp?.entity_type]}</span>
            </DialogTitle>
            <DialogDescription>
              {selectedFollowUp?.status === 'open' ? 'Due: ' : 'Was due: '}{selectedFollowUp?.due_date ? new Date(selectedFollowUp.due_date).toLocaleDateString() : ''} — {selectedFollowUp?.status === 'open' ? getDaysLabel(selectedFollowUp?.due_date || '') : 'Closed'}
            </DialogDescription>
          </DialogHeader>

          {selectedFollowUp && (
            <div className="space-y-5">
              {/* Stage Banner */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${ENTITY_COLORS[selectedFollowUp.entity_type] || 'bg-zinc-100 text-zinc-600'}`} data-testid="detail-stage-banner">
                <CalendarCheck className="w-4 h-4" />
                <span className="font-semibold text-sm">Funnel Stage: {ENTITY_LABELS[selectedFollowUp.entity_type] || selectedFollowUp.entity_type}</span>
              </div>

              {/* Lead Info (linked lead details) */}
              {selectedFollowUp.lead_id && (
                <div className="p-3 rounded-lg border border-blue-200 bg-blue-50" data-testid="follow-up-lead-info">
                  <p className="text-xs font-medium text-blue-600 mb-1">Linked Lead</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-zinc-900">{selectedFollowUp.client_name || 'Unknown'}</p>
                      {selectedFollowUp.lead_email && <p className="text-xs text-zinc-500">{selectedFollowUp.lead_email}</p>}
                    </div>
                    <Button variant="outline" size="sm" className="text-xs h-7 border-blue-300 text-blue-700" onClick={() => { setDetailOpen(false); window.location.href = `/sales-funnel-onboarding?leadId=${selectedFollowUp.lead_id}`; }}>
                      View Pipeline
                    </Button>
                  </div>
                </div>
              )}

              {/* Current Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-zinc-400">Priority:</span> <span className={`ml-1 font-medium ${selectedFollowUp.priority === 'high' ? 'text-red-600' : selectedFollowUp.priority === 'low' ? 'text-green-600' : 'text-yellow-600'}`}>{selectedFollowUp.priority}</span></div>
                <div><span className="text-zinc-400">Assigned to:</span> <span className="ml-1">{selectedFollowUp.assigned_to_name}</span></div>
                <div><span className="text-zinc-400">Created by:</span> <span className="ml-1">{selectedFollowUp.created_by_name}</span></div>
                <div><span className="text-zinc-400">Status:</span> <Badge variant={selectedFollowUp.status === 'open' ? 'default' : 'secondary'} className="ml-1 text-xs">{selectedFollowUp.status}</Badge>
                  {selectedFollowUp.status === 'open' && (() => {
                    const due = new Date(selectedFollowUp.due_date);
                    const today = new Date(); today.setHours(0,0,0,0); due.setHours(0,0,0,0);
                    const days = Math.floor((today - due) / (1000*60*60*24));
                    if (days >= 2) return <Badge variant="destructive" className="ml-1 text-xs">Escalated</Badge>;
                    if (days >= 1) return <Badge variant="outline" className="ml-1 text-xs text-red-500 border-red-300">Overdue</Badge>;
                    if (days === 0) return <Badge variant="outline" className="ml-1 text-xs text-yellow-600 border-yellow-300">Due Today</Badge>;
                    return null;
                  })()}
                </div>
                <div><span className="text-zinc-400">Due Date:</span> <span className="ml-1 font-medium">{selectedFollowUp.due_date ? new Date(selectedFollowUp.due_date).toLocaleDateString() : 'N/A'}</span></div>
                {selectedFollowUp.created_at && <div><span className="text-zinc-400">Created:</span> <span className="ml-1">{new Date(selectedFollowUp.created_at).toLocaleDateString()}</span></div>}
              </div>

              {selectedFollowUp.last_follow_up_summary && (
                <div className={`p-3 rounded-lg border ${dk ? 'bg-[#0F0F10] border-[#2A2A2E]' : 'bg-zinc-50 border-zinc-200'}`}>
                  <p className="text-xs text-zinc-400 mb-1">Last Summary</p>
                  <p className="text-sm text-zinc-700">{selectedFollowUp.last_follow_up_summary}</p>
                </div>
              )}

              {/* Add Update (open only) */}
              {selectedFollowUp.status === 'open' && (
                <div className="space-y-3 p-4 border border-zinc-200 rounded-lg">
                  <Label className="text-sm font-medium">Add Update</Label>
                  <textarea data-testid="follow-up-update-notes" value={updateNotes} onChange={(e) => setUpdateNotes(e.target.value)} placeholder="What happened? E.g., 'Client asked for revised pricing...'" rows={2} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm" />
                  <Input data-testid="follow-up-update-outcome" value={updateOutcome} onChange={(e) => setUpdateOutcome(e.target.value)} placeholder="Outcome (e.g., client interested, needs time)" className="border-zinc-200" />
                  <Button onClick={() => addUpdateMutation.mutate({ id: selectedFollowUp.id, notes: updateNotes, outcome: updateOutcome })} disabled={!updateNotes || addUpdateMutation.isPending} size="sm" data-testid="submit-follow-up-update">
                    <Send className="w-3 h-3 mr-1" /> {addUpdateMutation.isPending ? 'Saving...' : 'Add Update'}
                  </Button>
                </div>
              )}

              {/* History */}
              <div>
                <h4 className="text-sm font-semibold text-zinc-700 mb-3 flex items-center gap-1"><History className="w-4 h-4" /> History ({selectedFollowUp.history?.length || 0})</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {(selectedFollowUp.history || []).slice().reverse().map((entry, idx) => (
                    <div key={idx} className="flex gap-3 p-3 bg-zinc-50 rounded border border-zinc-100">
                      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${entry.action === 'closed' ? 'bg-green-500' : entry.action === 'reassigned' ? 'bg-orange-500' : entry.action === 'created' ? 'bg-blue-500' : 'bg-zinc-400'}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 text-xs text-zinc-400">
                          <span className="font-medium text-zinc-600">{entry.by}</span>
                          <span>{entry.action}</span>
                          <span>{new Date(entry.date).toLocaleString()}</span>
                        </div>
                        {entry.notes && <p className="text-sm text-zinc-700 mt-0.5">{entry.notes}</p>}
                        {entry.outcome && <p className="text-xs text-zinc-500 mt-0.5">Outcome: {entry.outcome}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons (open only) */}
              {selectedFollowUp.status === 'open' && (
                <div className="flex gap-2 flex-wrap pt-2 border-t border-zinc-200">
                  <Button onClick={() => setShowCloseDialog(true)} variant="outline" size="sm" className="text-green-700 border-green-300 hover:bg-green-50" data-testid="close-follow-up-btn">
                    <CheckCircle className="w-3.5 h-3.5 mr-1" /> Close Follow-up
                  </Button>
                  <Button onClick={() => setShowNextDialog(true)} size="sm" className="bg-zinc-950 text-white hover:bg-zinc-800" data-testid="schedule-next-btn">
                    <CalendarCheck className="w-3.5 h-3.5 mr-1" /> Close & Schedule Next
                  </Button>
                  {isManager && (
                    <Button onClick={() => setShowReassignDialog(true)} variant="outline" size="sm" className="text-orange-700 border-orange-300 hover:bg-orange-50" data-testid="reassign-follow-up-btn">
                      <ArrowRightLeft className="w-3.5 h-3.5 mr-1" /> Reassign
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Close Dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Close Follow-up</DialogTitle>
            <DialogDescription>Add a closing summary for this follow-up.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <textarea data-testid="close-notes" value={closeNotes} onChange={(e) => setCloseNotes(e.target.value)} placeholder="Closing summary..." rows={3} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm" />
            <Input data-testid="close-outcome" value={closeOutcome} onChange={(e) => setCloseOutcome(e.target.value)} placeholder="Outcome (e.g., deal closed, client not interested)" />
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowCloseDialog(false)} className="flex-1">Cancel</Button>
              <Button onClick={() => closeMutation.mutate({ id: selectedFollowUp?.id, notes: closeNotes, outcome: closeOutcome })} disabled={!closeNotes || closeMutation.isPending} className="flex-1 bg-green-600 hover:bg-green-700 text-white" data-testid="confirm-close-btn">
                {closeMutation.isPending ? 'Closing...' : 'Close Follow-up'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Schedule Next Dialog */}
      <Dialog open={showNextDialog} onOpenChange={setShowNextDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule Next Follow-up</DialogTitle>
            <DialogDescription>Close this follow-up and schedule the next one.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-sm">Next Follow-up Date *</Label>
              <Input data-testid="next-follow-up-date" type="date" value={nextDate} min={new Date().toISOString().split('T')[0]} onChange={(e) => setNextDate(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Notes</Label>
              <textarea data-testid="next-follow-up-notes" value={nextNotes} onChange={(e) => setNextNotes(e.target.value)} placeholder="What to follow up on..." rows={2} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm" />
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Priority</Label>
              <Select value={nextPriority} onValueChange={setNextPriority}>
                <SelectTrigger data-testid="next-follow-up-priority"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowNextDialog(false)} className="flex-1">Cancel</Button>
              <Button onClick={() => scheduleNextMutation.mutate({ id: selectedFollowUp?.id, due_date: new Date(nextDate).toISOString(), notes: nextNotes, priority: nextPriority })} disabled={!nextDate || scheduleNextMutation.isPending} className="flex-1 bg-zinc-950 text-white" data-testid="confirm-schedule-next-btn">
                {scheduleNextMutation.isPending ? 'Scheduling...' : 'Schedule Next'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reassign Dialog */}
      <Dialog open={showReassignDialog} onOpenChange={setShowReassignDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reassign Follow-up</DialogTitle>
            <DialogDescription>Transfer this follow-up to another sales person.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-sm">Assign To *</Label>
              <Select value={reassignUserId} onValueChange={setReassignUserId}>
                <SelectTrigger data-testid="reassign-user-select"><SelectValue placeholder="Select sales person" /></SelectTrigger>
                <SelectContent>
                  {(salesUsers || []).filter(u => u.id !== selectedFollowUp?.assigned_to).map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.role})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Reason</Label>
              <Input data-testid="reassign-reason" value={reassignReason} onChange={(e) => setReassignReason(e.target.value)} placeholder="Reason for reassignment" />
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={transferAll} onChange={(e) => setTransferAll(e.target.checked)} className="rounded" data-testid="transfer-all-checkbox" />
              <span>Transfer entire lead ownership (all funnel stages)</span>
            </label>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowReassignDialog(false)} className="flex-1">Cancel</Button>
              <Button onClick={() => reassignMutation.mutate({ id: selectedFollowUp?.id, new_owner_id: reassignUserId, reason: reassignReason, transfer_all_stages: transferAll })} disabled={!reassignUserId || reassignMutation.isPending} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white" data-testid="confirm-reassign-btn">
                {reassignMutation.isPending ? 'Reassigning...' : 'Reassign'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Follow-up Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>New Follow-up</DialogTitle>
            <DialogDescription>Create a follow-up linked to a lead.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {/* Lead Selection - Always required */}
            <div className="space-y-1">
              <Label className="text-sm font-medium">Select Lead *</Label>
              <Select value={createForm.lead_id || ''} onValueChange={(v) => {
                const lead = (leads || []).find(l => l.id === v);
                setCreateForm(p => ({ ...p, lead_id: v, entity_id: v, client_name: lead?.company || `${lead?.first_name} ${lead?.last_name}` }));
              }}>
                <SelectTrigger data-testid="create-lead-select"><SelectValue placeholder="Choose a lead" /></SelectTrigger>
                <SelectContent>
                  {(leads || []).map(l => (
                    <SelectItem key={l.id} value={l.id}>{l.company || `${l.first_name} ${l.last_name}`}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Stage *</Label>
              <Select value={createForm.entity_type} onValueChange={(v) => setCreateForm(p => ({ ...p, entity_type: v }))}>
                <SelectTrigger data-testid="create-entity-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(ENTITY_LABELS || {}).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-sm">Due Date *</Label>
                <Input data-testid="create-due-date" type="date" value={createForm.due_date} min={new Date().toISOString().split('T')[0]} onChange={(e) => setCreateForm(p => ({ ...p, due_date: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <Label className="text-sm">Time</Label>
                <Input data-testid="create-due-time" type="time" value={createForm.due_time || ''} onChange={(e) => setCreateForm(p => ({ ...p, due_time: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Notes</Label>
              <textarea data-testid="create-notes" value={createForm.notes} onChange={(e) => setCreateForm(p => ({ ...p, notes: e.target.value }))} placeholder="Follow-up details..." rows={2} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm" />
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Priority</Label>
              <Select value={createForm.priority} onValueChange={(v) => setCreateForm(p => ({ ...p, priority: v }))}>
                <SelectTrigger data-testid="create-priority"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowCreateDialog(false)} className="flex-1">Cancel</Button>
              <Button onClick={() => {
                let dueDateStr = createForm.due_date;
                if (createForm.due_time) {
                  dueDateStr = `${createForm.due_date}T${createForm.due_time}`;
                }
                const payload = { ...createForm, due_date: new Date(dueDateStr).toISOString() };
                delete payload.due_time;
                if (!payload.entity_id) payload.entity_id = payload.lead_id || 'manual';
                createMutation.mutate(payload);
              }} disabled={!createForm.due_date || !createForm.lead_id || createMutation.isPending} className="flex-1 bg-zinc-950 text-white" data-testid="confirm-create-btn">
                {createMutation.isPending ? 'Creating...' : 'Create Follow-up'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Send Email Dialog */}
      <Dialog open={showEmailDialog} onOpenChange={(open) => { setShowEmailDialog(open); if (!open) setEmailData({ subject: '', body: '', recipient_email: '', follow_up_id: '' }); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Mail className="w-5 h-5" /> Send Follow-up Email</DialogTitle>
            <DialogDescription>Choose a template and customize before sending. Includes action buttons for client response.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {/* Template Selection */}
            <div className="space-y-1">
              <Label className="text-sm font-medium">Choose Template</Label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'formal', label: 'Formal', desc: 'Professional follow-up' },
                  { id: 'meeting', label: 'Meeting', desc: 'Post-meeting recap' },
                  { id: 'reminder', label: 'Reminder', desc: 'Gentle nudge' },
                ].map(t => (
                  <button key={t.id} onClick={() => {
                    const baseUrl = process.env.REACT_APP_BACKEND_URL;
                    const fuId = emailData.follow_up_id;
                    const closeLink = `${baseUrl}/api/follow-ups/${fuId}/client-action?action=close`;
                    const rescheduleLink = `${baseUrl}/api/follow-ups/${fuId}/client-action?action=reschedule`;
                    const clientName = emailData.client_name || 'Sir/Madam';
                    const senderName = user?.full_name || 'Our Team';
                    const company = emailData.company || '';
                    const schedule = emailData.schedule_display || '';
                    const scheduleText = schedule ? `\nScheduled: ${schedule}\n` : '';
                    
                    const templates = {
                      formal: {
                        subject: `Follow-up: ${company || 'Our Discussion'}`,
                        body: `Dear ${clientName},\n\nI hope this email finds you well. I wanted to follow up on our recent discussion${company ? ` regarding ${company}` : ''}.\n\n${emailData.notes || 'Please find below the details of our follow-up schedule.'}${scheduleText}\n\nWe look forward to hearing from you at your earliest convenience.\n\nBest regards,\n${senderName}`
                      },
                      meeting: {
                        subject: `Meeting Follow-up: ${company || 'Next Steps'}`,
                        body: `Dear ${clientName},\n\nThank you for taking the time to meet with us. Here is a brief recap of our discussion and the agreed next steps:\n\n${emailData.notes || '- Review the proposal\n- Schedule a follow-up call\n- Share feedback'}${scheduleText}\n\nPlease let us know if you have any questions.\n\nWarm regards,\n${senderName}`
                      },
                      reminder: {
                        subject: `Gentle Reminder: ${company || 'Pending Follow-up'}`,
                        body: `Dear ${clientName},\n\nI hope you are doing well. This is a gentle reminder regarding our pending discussion${company ? ` about ${company}` : ''}.\n\n${emailData.notes || 'We would appreciate your feedback at your earliest convenience.'}${scheduleText}\n\nLooking forward to your response.\n\nBest regards,\n${senderName}`
                      },
                    };
                    const tmpl = templates[t.id];
                    setEmailData(p => ({ ...p, subject: tmpl.subject, body: tmpl.body }));
                  }} className={`p-2 rounded border text-left hover:bg-zinc-50 transition-colors ${emailData.subject?.includes(t.id === 'formal' ? 'Our Discussion' : t.id === 'meeting' ? 'Next Steps' : 'Pending') ? 'border-blue-400 bg-blue-50' : 'border-zinc-200'}`} data-testid={`template-${t.id}`}>
                    <p className="text-xs font-medium text-zinc-900">{t.label}</p>
                    <p className="text-[10px] text-zinc-500">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-sm font-medium">To *</Label>
              <Input data-testid="email-to" value={emailData.recipient_email} onChange={(e) => setEmailData(p => ({ ...p, recipient_email: e.target.value }))} placeholder="client@example.com" />
            </div>
            <div className="space-y-1">
              <Label className="text-sm font-medium">Subject</Label>
              <Input data-testid="email-subject" value={emailData.subject} onChange={(e) => setEmailData(p => ({ ...p, subject: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <Label className="text-sm font-medium">Message</Label>
              <textarea data-testid="email-body" value={emailData.body} onChange={(e) => setEmailData(p => ({ ...p, body: e.target.value }))} rows={10} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm resize-y font-mono" />
            </div>
            <div className="p-2 bg-blue-50 rounded border border-blue-200 text-xs text-blue-700">
              <p className="font-medium mb-1">CTA Buttons Included:</p>
              <p>The email includes "Confirm & Close" and "Reschedule" links. When the client clicks them, the action is logged automatically in the follow-up history.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowEmailDialog(false)} className="flex-1">Skip</Button>
              <Button onClick={handleSendEmail} disabled={!emailData.recipient_email || sendingEmail} className="flex-1 bg-blue-600 text-white hover:bg-blue-700" data-testid="send-email-btn">
                <Send className="w-4 h-4 mr-2" />
                {sendingEmail ? 'Sending...' : 'Send Email'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FollowUps;
