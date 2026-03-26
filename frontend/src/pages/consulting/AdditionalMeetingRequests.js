import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Calendar, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  Users,
  Building2,
  MessageSquare,
  Plus,
  Filter,
  RefreshCw
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdditionalMeetingRequests = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionType, setActionType] = useState(null); // 'approve' or 'reject'
  const [approvalData, setApprovalData] = useState({ approved_meetings: 1, remarks: '' });
  const [rejectionReason, setRejectionReason] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newRequest, setNewRequest] = useState({
    project_id: '',
    reason: '',
    requested_meetings: 1,
    meeting_type: 'General',
    urgency: 'normal'
  });

  const isAdmin = user?.role === 'admin' || user?.role === 'principal_consultant';

  // Fetch requests
  const { data: requests = [], isLoading, refetch } = useQuery({
    queryKey: ['additional-meeting-requests', statusFilter],
    queryFn: async () => {
      const params = statusFilter !== 'all' ? `?status=${statusFilter}` : '';
      const res = await axios.get(`${API}/meeting-schedules/additional-meeting-requests${params}`);
      return res.data;
    },
    staleTime: 30000
  });

  // Fetch projects for create dialog
  const { data: projects = [] } = useQuery({
    queryKey: ['projects', 'active'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects?status=active`);
      return res.data;
    },
    staleTime: 60000
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async ({ requestId, data }) => {
      const res = await axios.post(`${API}/meeting-schedules/additional-meeting-requests/${requestId}/approve`, data);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Request approved successfully');
      queryClient.invalidateQueries(['additional-meeting-requests']);
      queryClient.invalidateQueries(['project-meeting-status']);
      setSelectedRequest(null);
      setActionType(null);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to approve request');
    }
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, data }) => {
      const res = await axios.post(`${API}/meeting-schedules/additional-meeting-requests/${requestId}/reject`, data);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Request rejected');
      queryClient.invalidateQueries(['additional-meeting-requests']);
      setSelectedRequest(null);
      setActionType(null);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to reject request');
    }
  });

  // Create request mutation
  const createMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/meeting-schedules/additional-meeting-request`, data);
      return res.data;
    },
    onSuccess: (data) => {
      if (data.approval_required) {
        toast.success('Request submitted for admin approval');
      } else {
        toast.info(data.message);
      }
      queryClient.invalidateQueries(['additional-meeting-requests']);
      setShowCreateDialog(false);
      setNewRequest({ project_id: '', reason: '', requested_meetings: 1, meeting_type: 'General', urgency: 'normal' });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create request');
    }
  });

  const handleApprove = () => {
    if (!selectedRequest) return;
    approveMutation.mutate({
      requestId: selectedRequest.id,
      data: approvalData
    });
  };

  const handleReject = () => {
    if (!selectedRequest) return;
    rejectMutation.mutate({
      requestId: selectedRequest.id,
      data: { reason: rejectionReason }
    });
  };

  const handleCreateRequest = () => {
    if (!newRequest.project_id) {
      toast.error('Please select a project');
      return;
    }
    if (!newRequest.reason) {
      toast.error('Please provide a reason');
      return;
    }
    createMutation.mutate(newRequest);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
      case 'approved':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="w-3 h-3 mr-1" />Approved</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" />Rejected</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getUrgencyBadge = (urgency) => {
    if (urgency === 'urgent') {
      return <Badge variant="destructive" className="ml-2"><AlertTriangle className="w-3 h-3 mr-1" />Urgent</Badge>;
    }
    return null;
  };

  const pendingCount = (requests || []).filter(r => r.status === 'pending').length;

  return (
    <div className="p-6 space-y-6" data-testid="additional-meeting-requests-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Additional Meeting Requests</h1>
          <p className="text-zinc-500 mt-1">
            {isAdmin ? 'Review and manage requests for additional meetings beyond project commitments' : 'Request additional meetings when project quota is exhausted'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateDialog(true)} data-testid="create-request-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Request
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className={pendingCount > 0 ? 'border-amber-200 bg-amber-50/50' : ''}>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Pending</p>
                <p className="text-2xl font-bold text-amber-600">{pendingCount}</p>
              </div>
              <Clock className="w-8 h-8 text-amber-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Approved</p>
                <p className="text-2xl font-bold text-green-600">{(requests || []).filter(r => r.status === 'approved').length}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Rejected</p>
                <p className="text-2xl font-bold text-red-600">{(requests || []).filter(r => r.status === 'rejected').length}</p>
              </div>
              <XCircle className="w-8 h-8 text-red-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Total Requests</p>
                <p className="text-2xl font-bold text-zinc-700">{requests.length}</p>
              </div>
              <Calendar className="w-8 h-8 text-zinc-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Tabs */}
      <Tabs value={statusFilter} onValueChange={setStatusFilter} className="w-full">
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="pending" className="relative">
            Pending
            {pendingCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center">
                {pendingCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="approved">Approved</TabsTrigger>
          <TabsTrigger value="rejected">Rejected</TabsTrigger>
        </TabsList>

        <TabsContent value={statusFilter} className="mt-4">
          {isLoading ? (
            <div className="text-center py-8 text-zinc-500">Loading requests...</div>
          ) : requests.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Calendar className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
                <p className="text-zinc-500">No {statusFilter !== 'all' ? statusFilter : ''} requests found</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {(requests || []).map((request) => (
                <Card key={request.id} className={`hover:shadow-md transition-shadow ${request.status === 'pending' && isAdmin ? 'border-l-4 border-l-amber-400' : ''}`} data-testid={`request-card-${request.id}`}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-zinc-400" />
                          <span className="font-semibold text-zinc-900">{request.project_name}</span>
                          {getStatusBadge(request.status)}
                          {getUrgencyBadge(request.urgency)}
                        </div>
                        <p className="text-sm text-zinc-600">{request.client_name}</p>
                        
                        <div className="flex items-center gap-6 text-sm text-zinc-500 mt-2">
                          <span className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            Requested: <strong className="text-zinc-700">{request.requested_meetings}</strong> meeting(s)
                          </span>
                          <span>Type: {request.meeting_type}</span>
                          <span>Current: {request.current_delivered}/{request.current_committed} delivered</span>
                        </div>

                        <div className="bg-zinc-50 p-3 rounded-lg mt-3">
                          <p className="text-sm text-zinc-600">
                            <MessageSquare className="w-4 h-4 inline mr-2 text-zinc-400" />
                            <strong>Reason:</strong> {request.reason || 'Not specified'}
                          </p>
                        </div>

                        <div className="text-xs text-zinc-400 mt-2">
                          Requested by {request.requested_by_name} • {new Date(request.created_at).toLocaleDateString()}
                          {request.status === 'approved' && request.approved_by_name && (
                            <span className="ml-4 text-green-600">
                              Approved by {request.approved_by_name} ({request.approved_meetings} meetings)
                            </span>
                          )}
                          {request.status === 'rejected' && request.rejected_by_name && (
                            <span className="ml-4 text-red-600">
                              Rejected by {request.rejected_by_name}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Action Buttons for Admin */}
                      {isAdmin && request.status === 'pending' && (
                        <div className="flex gap-2 ml-4">
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-green-600 border-green-200 hover:bg-green-50"
                            onClick={() => {
                              setSelectedRequest(request);
                              setApprovalData({ approved_meetings: request.requested_meetings, remarks: '' });
                              setActionType('approve');
                            }}
                            data-testid={`approve-btn-${request.id}`}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 border-red-200 hover:bg-red-50"
                            onClick={() => {
                              setSelectedRequest(request);
                              setRejectionReason('');
                              setActionType('reject');
                            }}
                            data-testid={`reject-btn-${request.id}`}
                          >
                            <XCircle className="w-4 h-4 mr-1" />
                            Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Approve Dialog */}
      <Dialog open={actionType === 'approve'} onOpenChange={() => setActionType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve Additional Meetings</DialogTitle>
            <DialogDescription>
              Approve {selectedRequest?.requested_meetings} additional meeting(s) for {selectedRequest?.project_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Number of Meetings to Approve</Label>
              <Input
                type="number"
                min="1"
                max={selectedRequest?.requested_meetings || 10}
                value={approvalData.approved_meetings}
                onChange={(e) => setApprovalData({ ...approvalData, approved_meetings: parseInt(e.target.value) || 1 })}
              />
              <p className="text-xs text-zinc-500">
                Requested: {selectedRequest?.requested_meetings} | Current commitment will increase by this amount
              </p>
            </div>
            <div className="space-y-2">
              <Label>Remarks (Optional)</Label>
              <Textarea
                placeholder="Add any notes about this approval..."
                value={approvalData.remarks}
                onChange={(e) => setApprovalData({ ...approvalData, remarks: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionType(null)}>Cancel</Button>
            <Button onClick={handleApprove} disabled={approveMutation.isPending} className="bg-green-600 hover:bg-green-700">
              {approveMutation.isPending ? 'Approving...' : 'Approve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={actionType === 'reject'} onOpenChange={() => setActionType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Request</DialogTitle>
            <DialogDescription>
              Reject the request for {selectedRequest?.requested_meetings} additional meeting(s)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Reason for Rejection</Label>
              <Textarea
                placeholder="Provide a reason for rejection..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionType(null)}>Cancel</Button>
            <Button onClick={handleReject} disabled={rejectMutation.isPending} variant="destructive">
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Request Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Request Additional Meetings</DialogTitle>
            <DialogDescription>
              Submit a request when project meeting quota is exhausted
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Project</Label>
              <Select value={newRequest.project_id} onValueChange={(v) => setNewRequest({ ...newRequest, project_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a project" />
                </SelectTrigger>
                <SelectContent>
                  {(projects || []).map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name} - {p.client_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Number of Additional Meetings</Label>
              <Input
                type="number"
                min="1"
                max="20"
                value={newRequest.requested_meetings}
                onChange={(e) => setNewRequest({ ...newRequest, requested_meetings: parseInt(e.target.value) || 1 })}
              />
            </div>
            <div className="space-y-2">
              <Label>Meeting Type</Label>
              <Select value={newRequest.meeting_type} onValueChange={(v) => setNewRequest({ ...newRequest, meeting_type: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="General">General</SelectItem>
                  <SelectItem value="Training">Training</SelectItem>
                  <SelectItem value="Review">Review</SelectItem>
                  <SelectItem value="Audit">Audit</SelectItem>
                  <SelectItem value="Support">Support</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Urgency</Label>
              <Select value={newRequest.urgency} onValueChange={(v) => setNewRequest({ ...newRequest, urgency: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Reason for Request</Label>
              <Textarea
                placeholder="Explain why additional meetings are needed..."
                value={newRequest.reason}
                onChange={(e) => setNewRequest({ ...newRequest, reason: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateRequest} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Submitting...' : 'Submit Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdditionalMeetingRequests;
