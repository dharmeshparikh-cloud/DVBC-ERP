import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Calendar, CheckCircle, XCircle, Clock, Undo2, Save, Cloud } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import useDraft from '../hooks/useDraft';
import DraftIndicator from '../components/DraftIndicator';
import DraftSelector from '../components/DraftSelector';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../components/ui/page-header';
import MyWorkspaceNav from '../components/MyWorkspaceNav';
import { sortByLatest } from '../utils/sortUtils';
import { GovernedDropdown } from '../components/GovernedDropdown';

const LEAVE_TYPES = [
  { value: 'casual_leave', label: 'Casual Leave', key: 'casual' },
  { value: 'sick_leave', label: 'Sick Leave', key: 'sick' },
  { value: 'earned_leave', label: 'Earned Leave', key: 'earned' }
];

const STATUS_STYLES = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  withdrawn: 'bg-zinc-100 text-zinc-500 border-zinc-200'
};

// Generate draft title from leave data
const generateLeaveDraftTitle = (data) => {
  const type = LEAVE_TYPES.find(t => t.value === data.leave_type)?.label || 'Leave';
  const date = data.start_date ? format(new Date(data.start_date), 'MMM d') : 'No date';
  return `${type} - ${date}`;
};

const MyLeaves = () => {
  const queryClient = useQueryClient();
  const [leaveFilter, setLeaveFilter] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [withdrawingId, setWithdrawingId] = useState(null);
  
  // Draft support
  const {
    drafts,
    loadingDrafts,
    saving: savingDraft,
    lastSaved,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft,
    registerFormDataGetter
  } = useDraft('leave', generateLeaveDraftTitle);
  
  const [formData, setFormData] = useState({ 
    leave_type: 'casual_leave', 
    start_date: '', 
    end_date: '', 
    reason: '',
    is_half_day: false,
    half_day_type: 'first_half'
  });
  
  // Register form data getter for save-on-leave
  const formDataRef = useRef(formData);
  useEffect(() => {
    formDataRef.current = formData;
  }, [formData]);
  
  useEffect(() => {
    if (dialogOpen) {
      registerFormDataGetter(() => formDataRef.current);
    }
    return () => {
      registerFormDataGetter(null);
    };
  }, [dialogOpen, registerFormDataGetter]);
  
  // Auto-save when form data changes
  useEffect(() => {
    if (dialogOpen && (formData.start_date || formData.reason)) {
      autoSave(formData);
    }
  }, [formData, dialogOpen, autoSave]);

  // Fetch leave data with React Query
  const { data: leaveData, isLoading: loading, refetch: refetchLeaves } = useQuery({
    queryKey: ['my-leaves'],
    queryFn: async () => {
      const [reqRes, balRes] = await Promise.all([
        axios.get(`${API}/leave-requests`),
        axios.get(`${API}/my/leave-balance`).catch(() => ({ data: null }))
      ]);
      return {
        requests: reqRes.data || [],
        balance: balRes.data
      };
    },
    staleTime: 2 * 60 * 1000,
  });

  const requests = leaveData?.requests || [];
  const balance = leaveData?.balance;

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ['my-leaves'] });
  };
  
  // Load a saved draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      toast.success('Draft loaded');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/leave-requests`, {
        ...formData,
        start_date: new Date(formData.start_date).toISOString(),
        end_date: formData.is_half_day ? new Date(formData.start_date).toISOString() : new Date(formData.end_date).toISOString()
      });
      toast.success('Leave request submitted for approval');
      convertDraft();
      clearDraft();
      setDialogOpen(false);
      setFormData({ leave_type: 'casual_leave', start_date: '', end_date: '', reason: '', is_half_day: false, half_day_type: 'first_half' });
      invalidateData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleWithdraw = async (leaveId) => {
    if (!window.confirm('Are you sure you want to withdraw this leave request?')) return;
    
    setWithdrawingId(leaveId);
    try {
      await axios.post(`${API}/leave-requests/${leaveId}/withdraw`);
      toast.success('Leave request withdrawn successfully');
      invalidateData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to withdraw leave request');
    } finally {
      setWithdrawingId(null);
    }
  };

  const days = formData.is_half_day 
    ? 0.5 
    : (formData.start_date && formData.end_date
      ? Math.max(1, Math.ceil((new Date(formData.end_date) - new Date(formData.start_date)) / 86400000) + 1)
      : 0);

  return (
    <div data-testid="my-leaves-page">
      <MyWorkspaceNav />
      <PageHeader
        title="My Leaves"
        subtitle="Apply for leave, track status, and view balance"
        onRefresh={() => refetchLeaves()}
        loading={loading}
        actions={
          <Button onClick={() => setDialogOpen(true)} data-testid="apply-leave-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
            <Plus className="w-4 h-4 mr-2" /> Apply Leave
          </Button>
        }
      />
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="border-zinc-200 rounded-sm max-w-md">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <div>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Apply for Leave</DialogTitle>
                  <DialogDescription className="text-zinc-500">Routed: You → Reporting Manager → HR Manager</DialogDescription>
                </div>
                <DraftIndicator saving={savingDraft} lastSaved={lastSaved} onSave={() => saveDraft(formData)} />
              </div>
            </DialogHeader>
            
            {/* Draft Selector */}
            {drafts.length > 0 && (
              <DraftSelector 
                drafts={drafts}
                onLoadDraft={handleLoadDraft}
                onDeleteDraft={deleteDraft}
                loadingDrafts={loadingDrafts}
              />
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Leave Balance Summary */}
              {balance && (
                <div className="grid grid-cols-3 gap-2 p-2 bg-zinc-50 rounded-sm border border-zinc-200" data-testid="leave-balance-bar">
                  {LEAVE_TYPES.map(t => {
                    const b = balance[t.key];
                    if (!b) return null;
                    const willUse = formData.leave_type === t.value ? days : 0;
                    const afterApply = b.available - willUse;
                    return (
                      <div key={t.value} className={`text-center p-1.5 rounded-sm ${formData.leave_type === t.value ? 'bg-white border border-zinc-300' : ''}`}>
                        <div className="text-[10px] text-zinc-500">{t.label}</div>
                        <div className="text-sm font-bold text-zinc-800">{b.available}<span className="text-[10px] font-normal text-zinc-400">/{b.total}</span></div>
                        {willUse > 0 && (
                          <div className={`text-[10px] font-medium mt-0.5 ${afterApply < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                            After: {afterApply} left
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Leave Type</Label>
                <GovernedDropdown
                  value={formData.leave_type}
                  onChange={(val) => setFormData({ ...formData, leave_type: val })}
                  options={LEAVE_TYPES.map(t => {
                    const b = balance?.[t.key];
                    return { 
                      id: t.value, 
                      name: `${t.label}${b ? ` (${b.available} available)` : ''}` 
                    };
                  })}
                  placeholder="Select Leave Type"
                  data-testid="leave-type"
                  valueKey="id"
                  labelKey="name"
                />
              </div>
              
              {/* Half Day Option */}
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_half_day}
                    onChange={(e) => setFormData({ ...formData, is_half_day: e.target.checked, end_date: e.target.checked ? formData.start_date : formData.end_date })}
                    className="w-4 h-4 rounded border-zinc-300"
                    data-testid="half-day-checkbox"
                  />
                  <span className="text-sm text-zinc-700">Half Day Leave</span>
                </label>
                
                {formData.is_half_day && (
                  <GovernedDropdown
                    value={formData.half_day_type}
                    onChange={(val) => setFormData({ ...formData, half_day_type: val })}
                    options={[
                      { id: 'first_half', name: 'First Half (Morning)' },
                      { id: 'second_half', name: 'Second Half (Afternoon)' }
                    ]}
                    placeholder="Select Half"
                    data-testid="half-day-type"
                    valueKey="id"
                    labelKey="name"
                    className="h-8"
                  />
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">{formData.is_half_day ? 'Date' : 'Start Date'}</Label>
                  <Input type="date" value={formData.start_date} onChange={(e) => setFormData({ ...formData, start_date: e.target.value, end_date: formData.is_half_day ? e.target.value : formData.end_date })}
                    required className="rounded-sm border-zinc-200" data-testid="leave-start" />
                </div>
                {!formData.is_half_day && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">End Date</Label>
                    <Input type="date" value={formData.end_date} onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      required className="rounded-sm border-zinc-200" data-testid="leave-end" />
                  </div>
                )}
              </div>
              {days > 0 && <div className="text-sm text-zinc-600 bg-zinc-50 rounded-sm p-2 border border-zinc-200">Duration: <strong>{days} day(s)</strong>{formData.is_half_day && ` (${formData.half_day_type === 'first_half' ? 'Morning' : 'Afternoon'})`}</div>}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Reason</Label>
                <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  required rows={3} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="leave-reason" />
              </div>
              <div className="p-3 bg-zinc-50 rounded-sm border border-zinc-200 text-xs text-zinc-500">
                Approval: <span className="font-medium text-zinc-700">Reporting Manager → HR Manager</span>
              </div>
              <Button type="submit" data-testid="submit-leave" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Submit</Button>
            </form>
          </DialogContent>
        </Dialog>

      {/* Leave Balance */}
      {balance && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {LEAVE_TYPES.map(t => {
            const b = balance[t.key] || {};
            return (
              <Card key={t.value} className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="p-4">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">{t.label}</div>
                  <div className="flex items-end justify-between">
                    <div>
                      <span className="text-2xl font-semibold text-zinc-950" data-testid={`balance-${t.key}`}>{b.available || 0}</span>
                      <span className="text-sm text-zinc-400 ml-1">available</span>
                    </div>
                    <div className="text-xs text-zinc-500">
                      {b.used || 0} used / {b.total || 0} total
                    </div>
                  </div>
                  <div className="mt-2 w-full bg-zinc-200 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${b.available > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                      style={{ width: `${b.total ? ((b.available / b.total) * 100) : 0}%` }} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Leave Requests */}
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-medium text-zinc-700">My Leave Requests</div>
        <div className="flex gap-1 p-1 bg-zinc-100 rounded-sm" data-testid="leave-filter-tabs">
          {[{ key: '', label: 'All' }, { key: 'pending', label: 'Pending' }, { key: 'approved', label: 'Approved' }, { key: 'rejected', label: 'Rejected' }, { key: 'withdrawn', label: 'Withdrawn' }].map(tab => (
            <button key={tab.key} onClick={() => setLeaveFilter(tab.key)}
              className={`px-2.5 py-1 text-xs font-medium rounded-sm transition-colors ${leaveFilter === tab.key ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'}`}>
              {tab.label}
              <span className="ml-1 text-[10px] text-zinc-400">
                {tab.key === '' ? requests.length : requests.filter(r => r.status === tab.key).length}
              </span>
            </button>
          ))}
        </div>
      </div>
      {(() => {
        const filteredReqs = leaveFilter ? requests.filter(r => r.status === leaveFilter) : requests;
        return loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : filteredReqs.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <Calendar className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No leave requests yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">From</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">To</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Days</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Reason</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Approval Trail</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {sortByLatest(filteredReqs || [], 'created_at').filter(req => req.id).map(req => {
                const fmtDate = (d) => {
                  if (!d) return '-';
                  try {
                    const dt = new Date(d);
                    if (isNaN(dt.getTime())) return d;
                    return `${String(dt.getDate()).padStart(2,'0')}/${String(dt.getMonth()+1).padStart(2,'0')}/${dt.getFullYear()}`;
                  } catch { return d; }
                };
                return (
                <tr key={req.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`leave-req-${req.id}`}>
                  <td className="px-4 py-3 text-zinc-700">{req.leave_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                  <td className="px-4 py-3 text-zinc-700">{fmtDate(req.start_date)}</td>
                  <td className="px-4 py-3 text-zinc-700">{fmtDate(req.end_date)}</td>
                  <td className="px-4 py-3 text-center font-medium">{req.days}</td>
                  <td className="px-4 py-3 text-zinc-600 max-w-[200px] truncate">{req.reason}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-1 rounded-sm border ${STATUS_STYLES[req.status] || STATUS_STYLES.pending}`}>
                      {req.status?.charAt(0).toUpperCase() + req.status?.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    <div className="space-y-0.5">
                      {req.reporting_manager_name && (
                        <div>RM: <span className="font-medium text-zinc-700">{req.reporting_manager_name}</span>
                          {req.rm_action && <span className={`ml-1 ${req.rm_action === 'approve' ? 'text-emerald-600' : 'text-red-600'}`}>({req.rm_action}d)</span>}
                        </div>
                      )}
                      {req.rm_action_at && <div className="text-[10px] text-zinc-400">{fmtDate(req.rm_action_at)}</div>}
                      {req.rm_comments && <div className="text-[10px] italic text-zinc-400">"{req.rm_comments}"</div>}
                      {!req.reporting_manager_name && <span className="text-zinc-400">Pending assignment</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {req.status === 'pending' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleWithdraw(req.id)}
                        disabled={withdrawingId === req.id}
                        className="text-xs h-7 px-2 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                        data-testid={`withdraw-btn-${req.id}`}
                      >
                        <Undo2 className="w-3 h-3 mr-1" />
                        {withdrawingId === req.id ? 'Withdrawing...' : 'Withdraw'}
                      </Button>
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
      })()}
    </div>
  );
};

export default MyLeaves;
