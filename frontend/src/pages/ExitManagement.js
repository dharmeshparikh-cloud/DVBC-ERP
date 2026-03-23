import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  LogOut, Clock, CheckCircle, XCircle, AlertCircle, User, Calendar,
  Building2, Briefcase, FileText, Send, Loader2, ChevronRight,
  Eye, ThumbsUp, ThumbsDown, MessageSquare, Star
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../utils/roles';

const ExitManagement = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const isDark = theme === 'dark';
  
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);
  
  // State
  const [filter, setFilter] = useState('pending');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalAction, setApprovalAction] = useState(null);
  const [remarks, setRemarks] = useState('');
  
  // Fetch exit requests
  const { data: exitData, isLoading } = useQuery({
    queryKey: ['exit-requests', filter],
    queryFn: async () => {
      const res = await axios.get(`${API}/exit/all`, {
        params: filter !== 'all' ? { status: filter } : {}
      });
      return res.data;
    },
    staleTime: 60 * 1000
  });
  
  const requests = exitData?.requests || [];
  
  // Mutations
  const adminApproveMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/admin-approve`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit request approved by Admin');
      queryClient.invalidateQueries(['exit-requests']);
      setShowApprovalDialog(false);
      setSelectedRequest(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const hrApproveMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/hr-approve`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit request approved by HR. F&F calculation initiated.');
      queryClient.invalidateQueries(['exit-requests']);
      setShowApprovalDialog(false);
      setSelectedRequest(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/reject`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit request rejected');
      queryClient.invalidateQueries(['exit-requests']);
      setShowApprovalDialog(false);
      setSelectedRequest(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Rejection failed')
  });
  
  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-700',
      admin_approved: 'bg-blue-100 text-blue-700',
      hr_approved: 'bg-emerald-100 text-emerald-700',
      in_progress: 'bg-purple-100 text-purple-700',
      completed: 'bg-zinc-100 text-zinc-700',
      rejected: 'bg-red-100 text-red-700',
      cancelled: 'bg-zinc-100 text-zinc-500'
    };
    const labels = {
      pending: 'Pending Admin',
      admin_approved: 'Pending HR',
      hr_approved: 'Notice Period',
      in_progress: 'F&F In Progress',
      completed: 'Completed',
      rejected: 'Rejected',
      cancelled: 'Cancelled'
    };
    return (
      <Badge className={styles[status] || styles.pending}>
        {labels[status] || status}
      </Badge>
    );
  };
  
  const handleApprove = (request) => {
    setSelectedRequest(request);
    setApprovalAction('approve');
    setRemarks('');
    setShowApprovalDialog(true);
  };
  
  const handleReject = (request) => {
    setSelectedRequest(request);
    setApprovalAction('reject');
    setRemarks('');
    setShowApprovalDialog(true);
  };
  
  const submitApproval = () => {
    if (!selectedRequest) return;
    
    const payload = { requestId: selectedRequest.id, remarks };
    
    if (approvalAction === 'reject') {
      rejectMutation.mutate(payload);
    } else if (selectedRequest.status === 'pending' && isAdmin) {
      adminApproveMutation.mutate(payload);
    } else if (selectedRequest.status === 'admin_approved' && isHR) {
      hrApproveMutation.mutate(payload);
    }
  };
  
  const viewDetails = (request) => {
    setSelectedRequest(request);
    setShowDetailDialog(true);
  };
  
  const canApprove = (request) => {
    if (request.status === 'pending' && isAdmin) return true;
    if (request.status === 'admin_approved' && isHR) return true;
    return false;
  };
  
  // Stats
  const pendingCount = requests.filter(r => r.status === 'pending').length;
  const adminApprovedCount = requests.filter(r => r.status === 'admin_approved').length;
  const inProgressCount = requests.filter(r => ['hr_approved', 'in_progress'].includes(r.status)).length;
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-500" />
      </div>
    );
  }
  
  return (
    <div data-testid="exit-management-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <LogOut className="w-6 h-6 text-red-500" />
          Exit Management
        </h1>
        <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          Manage employee resignation requests and F&F settlements
        </p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Pending Admin</p>
              <p className="text-xl font-bold">{pendingCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <AlertCircle className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Pending HR</p>
              <p className="text-xl font-bold">{adminApprovedCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10">
              <Briefcase className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>In Progress</p>
              <p className="text-xl font-bold">{inProgressCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-500/10">
              <FileText className="w-5 h-5 text-zinc-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Requests</p>
              <p className="text-xl font-bold">{requests.length}</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex gap-2">
        {['pending', 'admin_approved', 'hr_approved', 'completed', 'all'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-red-500 text-white'
                : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
            }`}
          >
            {f === 'admin_approved' ? 'Pending HR' : f === 'hr_approved' ? 'In Notice' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Requests List */}
      {requests.length === 0 ? (
        <div className={`text-center py-12 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
          <LogOut className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
          <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
            No exit requests found
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(request => (
            <Card 
              key={request.id} 
              className={`${isDark ? 'bg-zinc-800 border-zinc-700' : ''} hover:shadow-md transition-shadow`}
            >
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-full bg-red-100">
                      <User className="w-6 h-6 text-red-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{request.employee_name}</h3>
                      <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {request.employee_id} • {request.department}
                      </p>
                      <div className="flex items-center gap-3 mt-1 text-xs">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Resignation: {new Date(request.resignation_date).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          LWD: {new Date(request.last_working_day).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {getStatusBadge(request.status)}
                    
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => viewDetails(request)}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      
                      {canApprove(request) && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleApprove(request)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            <ThumbsUp className="w-4 h-4 mr-1" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleReject(request)}
                          >
                            <ThumbsDown className="w-4 h-4 mr-1" />
                            Reject
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className={`max-w-2xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-red-500" />
              Exit Request Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedRequest && (
            <div className="space-y-4 py-4">
              {/* Employee Info */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                <h4 className="font-medium mb-3">Employee Information</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <Label className="text-xs text-zinc-500">Name</Label>
                    <p>{selectedRequest.employee_name}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Employee ID</Label>
                    <p>{selectedRequest.employee_id}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Department</Label>
                    <p>{selectedRequest.department || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Designation</Label>
                    <p>{selectedRequest.designation || 'N/A'}</p>
                  </div>
                </div>
              </div>
              
              {/* Request Info */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                <h4 className="font-medium mb-3">Request Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <Label className="text-xs text-zinc-500">Primary Reason</Label>
                    <p className="capitalize">{selectedRequest.reason?.replace('_', ' ') || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Status</Label>
                    <div className="mt-1">{getStatusBadge(selectedRequest.status)}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Resignation Date</Label>
                    <p>{new Date(selectedRequest.resignation_date).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Last Working Day</Label>
                    <p>{new Date(selectedRequest.last_working_day).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Notice Period</Label>
                    <p>{selectedRequest.notice_period_days || 30} days</p>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Submitted On</Label>
                    <p>{new Date(selectedRequest.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </div>
              
              {/* Exit Interview Responses */}
              {selectedRequest.exit_interview && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Exit Interview Responses
                  </h4>
                  <div className="space-y-3 text-sm">
                    {Object.entries(selectedRequest.exit_interview).map(([key, value]) => (
                      <div key={key} className={`p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'}`}>
                        <Label className="text-xs text-zinc-500 capitalize">{key.replace('_', ' ')}</Label>
                        <p className="mt-1">
                          {typeof value === 'number' && key.includes('rating') ? (
                            <span className="flex items-center gap-1">
                              {[...Array(5)].map((_, i) => (
                                <Star key={i} className={`w-4 h-4 ${i < value ? 'fill-amber-400 text-amber-400' : 'text-zinc-300'}`} />
                              ))}
                            </span>
                          ) : (
                            String(value)
                          )}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Approval History */}
              {selectedRequest.approvals && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3">Approval History</h4>
                  <div className="space-y-2 text-sm">
                    {selectedRequest.approvals.admin && (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span>Admin: {selectedRequest.approvals.admin.approved_by}</span>
                        <span className="text-zinc-500">
                          ({new Date(selectedRequest.approvals.admin.approved_at).toLocaleDateString()})
                        </span>
                      </div>
                    )}
                    {selectedRequest.approvals.hr && (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span>HR: {selectedRequest.approvals.hr.approved_by}</span>
                        <span className="text-zinc-500">
                          ({new Date(selectedRequest.approvals.hr.approved_at).toLocaleDateString()})
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDetailDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Approval Dialog */}
      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <DialogContent className={`max-w-md ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {approvalAction === 'reject' ? (
                <XCircle className="w-5 h-5 text-red-500" />
              ) : (
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              )}
              {approvalAction === 'reject' ? 'Reject' : 'Approve'} Exit Request
            </DialogTitle>
            <DialogDescription>
              {selectedRequest && (
                <>Employee: <strong>{selectedRequest.employee_name}</strong></>
              )}
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <Label>Remarks (Optional)</Label>
            <Textarea
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder={approvalAction === 'reject' ? 'Reason for rejection...' : 'Any comments...'}
              className={`mt-2 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
              rows={3}
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApprovalDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={submitApproval}
              disabled={adminApproveMutation.isPending || hrApproveMutation.isPending || rejectMutation.isPending}
              className={approvalAction === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}
            >
              {(adminApproveMutation.isPending || hrApproveMutation.isPending || rejectMutation.isPending) ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : approvalAction === 'reject' ? (
                <XCircle className="w-4 h-4 mr-2" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              {approvalAction === 'reject' ? 'Reject' : 'Approve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ExitManagement;
