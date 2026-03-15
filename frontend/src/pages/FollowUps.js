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
  MessageSquare, UserCheck, ArrowRightLeft, History, Plus, Send
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

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
  const [statusFilter, setStatusFilter] = useState('open');
  const [searchTerm, setSearchTerm] = useState('');
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
  const [createForm, setCreateForm] = useState({ entity_type: 'lead', entity_id: '', lead_id: '', client_name: '', due_date: '', notes: '', priority: 'medium' });

  const isManager = ['admin', 'sales_manager', 'manager', 'principal_consultant'].includes(user?.role);

  // Fetch follow-ups from the dedicated collection
  const { data: followUps = [], isLoading, refetch } = useQuery({
    queryKey: ['follow-ups', statusFilter, filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (filter !== 'all') params.append('entity_type', filter);
      const res = await axios.get(`${API}/follow-ups?${params}`);
      return Array.isArray(res.data) ? res.data : [];
    },
  });

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
      return users.filter(u => ['executive', 'sales_executive', 'sales_manager'].includes(u.role));
    },
    enabled: isManager,
  });

  // Fetch leads for create dialog
  const { data: leads = [] } = useQuery({
    queryKey: ['leads-for-followup-create'],
    queryFn: async () => {
      const res = await axios.get(`${API}/leads`);
      return Array.isArray(res.data) ? res.data : res.data?.items || [];
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      toast.success('Follow-up created');
      setShowCreateDialog(false);
      setCreateForm({ entity_type: 'lead', entity_id: '', lead_id: '', client_name: '', due_date: '', notes: '', priority: 'medium' });
    },
  });

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
  const overdueCount = followUps.filter(f => {
    const due = new Date(f.due_date);
    return due < new Date(new Date().setHours(0, 0, 0, 0)) && f.status === 'open';
  }).length;
  const openCount = followUps.filter(f => f.status === 'open').length;
  const escalationCount = escalations?.total || 0;

  // Per-stage breakdown
  const stageCounts = useMemo(() => {
    const counts = {};
    followUps.forEach(f => {
      const type = f.entity_type || 'unknown';
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  }, [followUps]);

  // Filter and search
  const filteredFollowUps = useMemo(() => {
    let result = followUps;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      result = result.filter(f =>
        f.client_name?.toLowerCase().includes(q) ||
        f.notes?.toLowerCase().includes(q) ||
        f.last_follow_up_summary?.toLowerCase().includes(q) ||
        f.assigned_to_name?.toLowerCase().includes(q)
      );
    }
    // Sort: overdue first, then by due_date
    result.sort((a, b) => {
      const aOverdue = new Date(a.due_date) < new Date(new Date().setHours(0, 0, 0, 0));
      const bOverdue = new Date(b.due_date) < new Date(new Date().setHours(0, 0, 0, 0));
      if (aOverdue && !bOverdue) return -1;
      if (!aOverdue && bOverdue) return 1;
      return new Date(a.due_date) - new Date(b.due_date);
    });
    return result;
  }, [followUps, searchTerm]);

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

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E]">
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
        <Card className="bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E]">
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
        <Card className="bg-white dark:bg-[#1A1A1C] border-zinc-200 dark:border-[#2A2A2E]">
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
          <Card className={`border-zinc-200 dark:border-[#2A2A2E] ${escalationCount > 0 ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900/40' : 'bg-white dark:bg-[#1A1A1C]'}`}>
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
      {Object.keys(stageCounts).length > 0 && (
        <Card className={`shadow-none rounded-sm ${dk ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'}`} data-testid="stage-breakdown-card">
          <CardContent className="py-4">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">By Funnel Stage</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(ENTITY_LABELS).map(([key, label]) => {
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

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <Input placeholder="Search by client, notes..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="max-w-xs border-zinc-300 bg-white dark:bg-[#1A1A1C] dark:border-[#2A2A2E]" data-testid="follow-up-search" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32 border-zinc-300 bg-white dark:bg-[#1A1A1C] dark:border-[#2A2A2E]" data-testid="follow-up-status-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-40 border-zinc-300 bg-white dark:bg-[#1A1A1C] dark:border-[#2A2A2E]" data-testid="follow-up-type-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Stages</SelectItem>
            {Object.entries(ENTITY_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Follow-ups List */}
      <Card className={`${dk ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarCheck className="w-5 h-5" />
            Follow-ups ({filteredFollowUps.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-zinc-500">Loading...</div>
          ) : filteredFollowUps.length === 0 ? (
            <div className="text-center py-8 text-zinc-400">
              <CheckCircle className="w-10 h-10 mx-auto mb-2 text-green-400" />
              <p className="text-sm">No follow-ups found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredFollowUps.map(fu => {
                const isOverdue = new Date(fu.due_date) < new Date(new Date().setHours(0, 0, 0, 0)) && fu.status === 'open';
                return (
                  <div
                    key={fu.id}
                    data-testid={`follow-up-item-${fu.id}`}
                    className={`p-4 rounded-lg border cursor-pointer hover:shadow-sm transition-shadow ${
                      isOverdue
                        ? dk ? 'bg-red-950/20 border-red-900/30' : 'bg-red-50 border-red-200'
                        : fu.status === 'closed'
                        ? dk ? 'bg-[#131314] border-[#2A2A2E] opacity-70' : 'bg-zinc-50 border-zinc-200 opacity-70'
                        : dk ? 'bg-[#222226] border-[#2A2A2E]' : 'bg-white border-zinc-200'
                    }`}
                    onClick={() => openDetail(fu)}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-3 flex-1">
                        <div className={`w-2 h-2 rounded-full mt-2 ${fu.priority === 'high' ? 'bg-red-500' : fu.priority === 'low' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-zinc-800">{fu.client_name}</span>
                            <span className={`px-2 py-0.5 text-xs rounded font-semibold ${ENTITY_COLORS[fu.entity_type] || 'bg-zinc-100 text-zinc-600'}`} data-testid={`stage-badge-${fu.id}`}>{ENTITY_LABELS[fu.entity_type] || fu.entity_type}</span>
                            {fu.priority === 'high' && <Badge variant="destructive" className="text-[10px] px-1.5">High</Badge>}
                            {fu.status === 'closed' && <Badge variant="secondary" className="text-[10px]">Closed</Badge>}
                            {isOverdue && fu.status === 'open' && (() => {
                              const days = Math.abs(Math.floor((new Date(fu.due_date).setHours(0,0,0,0) - new Date().setHours(0,0,0,0)) / (1000*60*60*24)));
                              return days >= 2 ? <Badge variant="destructive" className="text-[10px] px-1.5">Escalated</Badge> : null;
                            })()}
                          </div>
                          <p className="text-sm text-zinc-500 mt-0.5 truncate">{fu.last_follow_up_summary || fu.notes || 'No notes'}</p>
                          <div className="flex items-center gap-3 mt-1 text-xs text-zinc-400">
                            {fu.assigned_to_name && (
                              <span className="flex items-center gap-1"><UserCheck className="w-3 h-3" />{fu.assigned_to_name}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right ml-4 shrink-0">
                        <p className={`text-xs font-medium ${isOverdue ? 'text-red-600' : 'text-zinc-500'}`}>{getDaysLabel(fu.due_date)}</p>
                        <p className="text-[10px] text-zinc-400">{new Date(fu.due_date).toLocaleDateString()}</p>
                        {fu.history?.length > 1 && (
                          <p className="text-[10px] text-zinc-400 flex items-center gap-0.5 justify-end mt-1"><History className="w-3 h-3" />{fu.history.length} updates</p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

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
              <Input data-testid="next-follow-up-date" type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)} />
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
                  {salesUsers.filter(u => u.id !== selectedFollowUp?.assigned_to).map(u => (
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
            <DialogDescription>Create a follow-up for any funnel stage.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-sm">Stage *</Label>
              <Select value={createForm.entity_type} onValueChange={(v) => setCreateForm(p => ({ ...p, entity_type: v }))}>
                <SelectTrigger data-testid="create-entity-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(ENTITY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {createForm.entity_type === 'lead' && leads.length > 0 && (
              <div className="space-y-1">
                <Label className="text-sm">Select Lead</Label>
                <Select value={createForm.entity_id} onValueChange={(v) => {
                  const lead = leads.find(l => l.id === v);
                  setCreateForm(p => ({ ...p, entity_id: v, lead_id: v, client_name: lead?.company || `${lead?.first_name} ${lead?.last_name}` }));
                }}>
                  <SelectTrigger data-testid="create-lead-select"><SelectValue placeholder="Choose a lead" /></SelectTrigger>
                  <SelectContent>
                    {leads.map(l => (
                      <SelectItem key={l.id} value={l.id}>{l.company || `${l.first_name} ${l.last_name}`}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {createForm.entity_type !== 'lead' && (
              <>
                <div className="space-y-1">
                  <Label className="text-sm">Client Name *</Label>
                  <Input data-testid="create-client-name" value={createForm.client_name} onChange={(e) => setCreateForm(p => ({ ...p, client_name: e.target.value }))} placeholder="Client/company name" />
                </div>
                <div className="space-y-1">
                  <Label className="text-sm">Entity ID</Label>
                  <Input data-testid="create-entity-id" value={createForm.entity_id} onChange={(e) => setCreateForm(p => ({ ...p, entity_id: e.target.value }))} placeholder="Optional reference ID" />
                </div>
              </>
            )}
            <div className="space-y-1">
              <Label className="text-sm">Due Date *</Label>
              <Input data-testid="create-due-date" type="date" value={createForm.due_date} onChange={(e) => setCreateForm(p => ({ ...p, due_date: e.target.value }))} />
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
                const payload = { ...createForm, due_date: new Date(createForm.due_date).toISOString() };
                if (!payload.entity_id) payload.entity_id = payload.lead_id || 'manual';
                createMutation.mutate(payload);
              }} disabled={!createForm.due_date || createMutation.isPending} className="flex-1 bg-zinc-950 text-white" data-testid="confirm-create-btn">
                {createMutation.isPending ? 'Creating...' : 'Create Follow-up'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FollowUps;
