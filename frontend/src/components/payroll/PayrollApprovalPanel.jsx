/**
 * PayrollApprovalPanel - Payroll Approval Workflow UI
 * Displays payroll runs with approval status and actions
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { 
  CheckCircle, XCircle, Clock, Lock, Unlock, Send, 
  FileText, AlertTriangle, RefreshCw, ChevronRight,
  DollarSign, Users, Calendar, Shield
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API } from '../../App';

const STATUS_CONFIG = {
  draft: { label: 'Draft', color: 'bg-zinc-100 text-zinc-700', icon: FileText },
  submitted: { label: 'Submitted', color: 'bg-blue-100 text-blue-700', icon: Send },
  hr_approved: { label: 'HR Approved', color: 'bg-purple-100 text-purple-700', icon: CheckCircle },
  finance_approved: { label: 'Finance Approved', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  disbursed: { label: 'Disbursed', color: 'bg-green-100 text-green-700', icon: DollarSign },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700', icon: XCircle }
};

const formatCurrency = (v) => `₹${(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;

const PayrollApprovalPanel = ({ month, userRole, onRefresh }) => {
  const queryClient = useQueryClient();
  const [rejectDialog, setRejectDialog] = useState(false);
  const [unlockDialog, setUnlockDialog] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [unlockReason, setUnlockReason] = useState('');
  const [historyDialog, setHistoryDialog] = useState(false);

  // Fetch payroll runs
  const { data: payrollRuns = [], isLoading, refetch } = useQuery({
    queryKey: ['payroll-runs', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/payroll-run`, { params: { month } });
      return res.data;
    }
  });

  // Fetch lock status
  const { data: lockStatus } = useQuery({
    queryKey: ['payroll-lock-status', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/lock-status/${month}`);
      return res.data;
    }
  });

  // Create payroll run mutation
  const createRunMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.post(`${API}/payroll/payroll-run/create`, { month });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll run created');
      refetch();
      onRefresh?.();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to create payroll run')
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (runId) => {
      const res = await axios.post(`${API}/payroll/payroll-run/${runId}/submit`);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll submitted for approval');
      refetch();
      queryClient.invalidateQueries(['payroll-lock-status']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to submit')
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async ({ runId, comments }) => {
      const res = await axios.post(`${API}/payroll/payroll-run/${runId}/approve`, { comments });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll approved');
      refetch();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to approve')
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ runId, reason }) => {
      const res = await axios.post(`${API}/payroll/payroll-run/${runId}/reject`, { reason });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll rejected');
      setRejectDialog(false);
      setRejectReason('');
      refetch();
      queryClient.invalidateQueries(['payroll-lock-status']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to reject')
  });

  // Resubmit mutation
  const resubmitMutation = useMutation({
    mutationFn: async (runId) => {
      const res = await axios.post(`${API}/payroll/payroll-run/${runId}/resubmit`);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll resubmitted');
      refetch();
      queryClient.invalidateQueries(['payroll-lock-status']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to resubmit')
  });

  // Unlock mutation
  const unlockMutation = useMutation({
    mutationFn: async (reason) => {
      const res = await axios.post(`${API}/payroll/unlock/${month}`, { reason });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Payroll unlocked');
      setUnlockDialog(false);
      setUnlockReason('');
      refetch();
      queryClient.invalidateQueries(['payroll-lock-status']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to unlock')
  });

  const currentRun = payrollRuns.find(r => r.month === month);
  const canCreate = !currentRun && ['admin', 'hr_manager'].includes(userRole);
  const canSubmit = currentRun?.status === 'draft' && ['admin', 'hr_manager'].includes(userRole);
  const canApprove = (
    (currentRun?.status === 'submitted' && userRole && ['admin', 'hr_manager'].includes(userRole)) ||
    (currentRun?.status === 'hr_approved' && userRole && ['admin', 'finance_manager'].includes(userRole)) ||
    (currentRun?.status === 'finance_approved' && userRole === 'admin')
  );
  const canReject = currentRun && !['draft', 'rejected', 'disbursed'].includes(currentRun.status || '') && 
    userRole && ['admin', 'hr_manager', 'finance_manager'].includes(userRole);
  const canResubmit = currentRun?.status === 'rejected' && userRole && ['admin', 'hr_manager'].includes(userRole);
  const canUnlock = lockStatus?.is_locked && userRole === 'admin' && currentRun?.status !== 'disbursed';

  const handleReject = () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    rejectMutation.mutate({ runId: currentRun.id, reason: rejectReason });
  };

  const handleUnlock = () => {
    if (!unlockReason.trim()) {
      toast.error('Please provide an unlock reason');
      return;
    }
    unlockMutation.mutate(unlockReason);
  };

  const getNextApprover = (status) => {
    switch (status) {
      case 'submitted': return 'HR Manager';
      case 'hr_approved': return 'Finance Manager';
      case 'finance_approved': return 'Admin (Final)';
      default: return '';
    }
  };

  return (
    <Card className="border-zinc-200 dark:border-zinc-700">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-500" />
            Payroll Approval Workflow
          </CardTitle>
          <div className="flex items-center gap-2">
            {lockStatus?.is_locked && (
              <Badge className="bg-amber-100 text-amber-700 flex items-center gap-1">
                <Lock className="w-3 h-3" />
                Locked
              </Badge>
            )}
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin text-zinc-400" />
          </div>
        ) : !currentRun ? (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
            <p className="text-zinc-500 mb-4">No payroll run for {month}</p>
            {canCreate && (
              <Button 
                onClick={() => createRunMutation.mutate()}
                disabled={createRunMutation.isPending}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {createRunMutation.isPending ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <FileText className="w-4 h-4 mr-2" />
                )}
                Create Payroll Run
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Status Card */}
            <div className="bg-zinc-50 dark:bg-zinc-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Badge className={STATUS_CONFIG[currentRun.status]?.color || 'bg-zinc-100'}>
                    {STATUS_CONFIG[currentRun.status]?.label || currentRun.status}
                  </Badge>
                  {currentRun.status !== 'disbursed' && currentRun.status !== 'rejected' && (
                    <span className="text-sm text-zinc-500">
                      Next: {getNextApprover(currentRun.status)}
                    </span>
                  )}
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => { setSelectedRun(currentRun); setHistoryDialog(true); }}
                >
                  View History
                </Button>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-zinc-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-zinc-500 text-xs mb-1">
                    <Users className="w-3 h-3" />
                    Employees
                  </div>
                  <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                    {currentRun.employee_count}
                  </p>
                </div>
                <div className="bg-white dark:bg-zinc-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-zinc-500 text-xs mb-1">
                    <DollarSign className="w-3 h-3" />
                    Gross
                  </div>
                  <p className="text-lg font-bold text-emerald-600">
                    {formatCurrency(currentRun.total_gross)}
                  </p>
                </div>
                <div className="bg-white dark:bg-zinc-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-zinc-500 text-xs mb-1">
                    <DollarSign className="w-3 h-3" />
                    Deductions
                  </div>
                  <p className="text-lg font-bold text-red-600">
                    {formatCurrency(currentRun.total_deductions)}
                  </p>
                </div>
                <div className="bg-white dark:bg-zinc-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-zinc-500 text-xs mb-1">
                    <DollarSign className="w-3 h-3" />
                    Net Payable
                  </div>
                  <p className="text-lg font-bold text-purple-600">
                    {formatCurrency(currentRun.total_net)}
                  </p>
                </div>
              </div>

              {/* Rejection Reason */}
              {currentRun.status === 'rejected' && currentRun.rejection_reason && (
                <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-700 dark:text-red-400">Rejection Reason</p>
                      <p className="text-sm text-red-600 dark:text-red-300">{currentRun.rejection_reason}</p>
                      <p className="text-xs text-red-500 mt-1">
                        By {currentRun.rejected_by_name} on {new Date(currentRun.rejected_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2">
              {canSubmit && (
                <Button 
                  onClick={() => submitMutation.mutate(currentRun.id)}
                  disabled={submitMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {submitMutation.isPending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                  Submit for Approval
                </Button>
              )}
              {canApprove && (
                <Button 
                  onClick={() => approveMutation.mutate({ runId: currentRun.id })}
                  disabled={approveMutation.isPending}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {approveMutation.isPending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                  Approve
                </Button>
              )}
              {canReject && (
                <Button 
                  variant="outline"
                  onClick={() => setRejectDialog(true)}
                  className="border-red-200 text-red-600 hover:bg-red-50"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </Button>
              )}
              {canResubmit && (
                <Button 
                  onClick={() => resubmitMutation.mutate(currentRun.id)}
                  disabled={resubmitMutation.isPending}
                  className="bg-amber-600 hover:bg-amber-700"
                >
                  {resubmitMutation.isPending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                  Resubmit
                </Button>
              )}
              {canUnlock && (
                <Button 
                  variant="outline"
                  onClick={() => setUnlockDialog(true)}
                  className="border-amber-200 text-amber-600 hover:bg-amber-50"
                >
                  <Unlock className="w-4 h-4 mr-2" />
                  Emergency Unlock
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Reject Dialog */}
        <Dialog open={rejectDialog} onOpenChange={setRejectDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <XCircle className="w-5 h-5" />
                Reject Payroll
              </DialogTitle>
              <DialogDescription>
                Provide a reason for rejection. The payroll will be unlocked for corrections.
              </DialogDescription>
            </DialogHeader>
            <Textarea
              placeholder="Enter rejection reason..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setRejectDialog(false)}>Cancel</Button>
              <Button 
                onClick={handleReject}
                disabled={rejectMutation.isPending}
                className="bg-red-600 hover:bg-red-700"
              >
                {rejectMutation.isPending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
                Reject Payroll
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Unlock Dialog */}
        <Dialog open={unlockDialog} onOpenChange={setUnlockDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-amber-600">
                <Unlock className="w-5 h-5" />
                Emergency Unlock
              </DialogTitle>
              <DialogDescription>
                This will unlock the payroll for modifications. Provide a reason for audit trail.
              </DialogDescription>
            </DialogHeader>
            <Textarea
              placeholder="Enter unlock reason..."
              value={unlockReason}
              onChange={(e) => setUnlockReason(e.target.value)}
              rows={3}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setUnlockDialog(false)}>Cancel</Button>
              <Button 
                onClick={handleUnlock}
                disabled={unlockMutation.isPending}
                className="bg-amber-600 hover:bg-amber-700"
              >
                {unlockMutation.isPending ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
                Unlock Payroll
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* History Dialog */}
        <Dialog open={historyDialog} onOpenChange={setHistoryDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Approval History</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {selectedRun?.approval_history?.map((h, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    h.action === 'rejected' ? 'bg-red-100 text-red-600' :
                    h.action === 'emergency_unlock' ? 'bg-amber-100 text-amber-600' :
                    'bg-emerald-100 text-emerald-600'
                  }`}>
                    {h.action === 'rejected' ? <XCircle className="w-4 h-4" /> :
                     h.action === 'emergency_unlock' ? <Unlock className="w-4 h-4" /> :
                     <CheckCircle className="w-4 h-4" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-zinc-900 dark:text-zinc-100 capitalize">
                      {h.action.replace(/_/g, ' ')}
                    </p>
                    <p className="text-sm text-zinc-500">{h.by_name}</p>
                    <p className="text-xs text-zinc-400">
                      {new Date(h.at).toLocaleString()}
                    </p>
                    {(h.reason || h.comments) && (
                      <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1 italic">
                        "{h.reason || h.comments}"
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default PayrollApprovalPanel;
