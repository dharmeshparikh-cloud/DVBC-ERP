import React, { useState } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { 
  ArrowRightLeft, TrendingUp, DollarSign, Users, Clock, Check, X,
  AlertTriangle, FileText, Building2, Briefcase, ChevronRight, User
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useContext } from 'react';

const WORKFLOW_TYPES = {
  transfer: { label: 'Transfer', icon: ArrowRightLeft, color: 'bg-blue-100 text-blue-700' },
  promotion: { label: 'Promotion', icon: TrendingUp, color: 'bg-green-100 text-green-700' },
  ctc_revision: { label: 'CTC Revision', icon: DollarSign, color: 'bg-amber-100 text-amber-700' },
  hierarchy_change: { label: 'Hierarchy Change', icon: Users, color: 'bg-purple-100 text-purple-700' },
  bank_change: { label: 'Bank Change', icon: FileText, color: 'bg-orange-100 text-orange-700' }
};

const EmployeeWorkflows = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const isAdmin = user?.role === 'admin';
  
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [approvalDialog, setApprovalDialog] = useState(false);
  const [rejectDialog, setRejectDialog] = useState(false);
  const [remarks, setRemarks] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  
  // New request form state
  const [newRequestDialog, setNewRequestDialog] = useState(false);
  const [requestType, setRequestType] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [newValue, setNewValue] = useState('');
  const [changeReason, setChangeReason] = useState('');

  // Fetch pending requests
  const { data: pendingRequests = [], isLoading } = useQuery({
    queryKey: ['workflow-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/governance/pending-requests`);
      return res.data;
    },
    enabled: isAdmin
  });

  // Fetch employees for new request
  const { data: employees = [] } = useQuery({
    queryKey: ['employees-for-workflow'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return Array.isArray(res.data) ? res.data : [];
    }
  });

  // Fetch departments for transfer
  const { data: departments = [] } = useQuery({
    queryKey: ['departments-list'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/departments/list`);
      // Handle both old array response and new {data: []} format
      return Array.isArray(res.data) ? res.data : (res.data?.data || []);
    }
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/governance/requests/${requestId}/approve`, null, {
        params: { remarks }
      });
    },
    onSuccess: () => {
      toast.success('Request approved successfully');
      queryClient.invalidateQueries({ queryKey: ['workflow-requests'] });
      setApprovalDialog(false);
      setSelectedRequest(null);
      setRemarks('');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to approve request');
    }
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, reason }) => {
      return axios.post(`${API}/governance/requests/${requestId}/reject`, null, {
        params: { reason }
      });
    },
    onSuccess: () => {
      toast.success('Request rejected');
      queryClient.invalidateQueries({ queryKey: ['workflow-requests'] });
      setRejectDialog(false);
      setSelectedRequest(null);
      setRejectionReason('');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to reject request');
    }
  });

  // Create new request mutation
  const createRequestMutation = useMutation({
    mutationFn: async (data) => {
      return axios.patch(`${API}/employees/${data.employeeId}`, {
        [data.field]: data.value
      }, {
        params: { change_reason: data.reason }
      });
    },
    onSuccess: (response) => {
      const data = response.data;
      if (data.workflow_requests?.length > 0) {
        toast.success('Workflow request created and sent for approval');
      } else if (data.pending_approval) {
        toast.success('Request submitted for admin approval');
      } else {
        toast.success('Change applied successfully');
      }
      queryClient.invalidateQueries({ queryKey: ['workflow-requests'] });
      queryClient.invalidateQueries({ queryKey: ['employees-for-workflow'] });
      setNewRequestDialog(false);
      resetNewRequestForm();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create request');
    }
  });

  const resetNewRequestForm = () => {
    setRequestType('');
    setSelectedEmployee(null);
    setNewValue('');
    setChangeReason('');
  };

  const getFieldForWorkflow = (type) => {
    switch (type) {
      case 'transfer': return 'department';
      case 'promotion': return 'designation';
      case 'ctc_revision': return 'salary';
      case 'hierarchy_change': return 'reporting_manager_id';
      default: return '';
    }
  };

  const handleCreateRequest = () => {
    if (!selectedEmployee || !newValue || !changeReason) {
      toast.error('Please fill all required fields');
      return;
    }
    
    createRequestMutation.mutate({
      employeeId: selectedEmployee.id,
      field: getFieldForWorkflow(requestType),
      value: requestType === 'ctc_revision' ? parseFloat(newValue) : newValue,
      reason: changeReason
    });
  };

  const groupedRequests = pendingRequests.reduce((acc, req) => {
    const type = req.workflow_type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(req);
    return acc;
  }, {});

  const renderRequestCard = (request) => {
    const config = WORKFLOW_TYPES[request.workflow_type] || WORKFLOW_TYPES.transfer;
    const Icon = config.icon;
    
    return (
      <Card key={request.id} className="border-zinc-200 hover:border-zinc-300 transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg ${config.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-zinc-900">{request.employee_name}</h4>
                  <Badge variant="outline" className="text-xs">{request.employee_code || 'Pending ID'}</Badge>
                </div>
                <p className="text-sm text-zinc-500 mt-1">
                  {request.field}: <span className="line-through text-zinc-400">{request.current_value || 'None'}</span>
                  <ChevronRight className="h-3 w-3 inline mx-1" />
                  <span className="font-medium text-zinc-700">{request.requested_value}</span>
                </p>
                <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {request.requested_by_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(request.created_at).toLocaleDateString()}
                  </span>
                </div>
                {request.change_reason && (
                  <p className="text-xs text-zinc-500 mt-2 bg-zinc-50 p-2 rounded">
                    Reason: {request.change_reason}
                  </p>
                )}
              </div>
            </div>
            {isAdmin && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  onClick={() => {
                    setSelectedRequest(request);
                    setRejectDialog(true);
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => {
                    setSelectedRequest(request);
                    setApprovalDialog(true);
                  }}
                >
                  <Check className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-950">EMPLOYEE WORKFLOWS</h1>
          <p className="text-zinc-500">Manage transfer, promotion, CTC revision, and hierarchy change requests</p>
        </div>
        <Button 
          onClick={() => setNewRequestDialog(true)}
          className="bg-zinc-950 text-white hover:bg-zinc-800"
        >
          New Request
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(WORKFLOW_TYPES).slice(0, 4).map(([type, config]) => {
          const count = groupedRequests[type]?.length || 0;
          const Icon = config.icon;
          return (
            <Card key={type} className="border-zinc-200">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500">{config.label}</p>
                    <p className="text-2xl font-bold text-zinc-900">{count}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${config.color}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Tabs for different workflow types */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList className="bg-zinc-100">
          <TabsTrigger value="all">All Pending ({pendingRequests.length})</TabsTrigger>
          <TabsTrigger value="transfer">Transfers ({groupedRequests.transfer?.length || 0})</TabsTrigger>
          <TabsTrigger value="promotion">Promotions ({groupedRequests.promotion?.length || 0})</TabsTrigger>
          <TabsTrigger value="ctc_revision">CTC Revisions ({groupedRequests.ctc_revision?.length || 0})</TabsTrigger>
          <TabsTrigger value="hierarchy_change">Hierarchy ({groupedRequests.hierarchy_change?.length || 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {isLoading ? (
            <div className="text-center py-12 text-zinc-400">Loading...</div>
          ) : pendingRequests.length === 0 ? (
            <Card className="border-zinc-200">
              <CardContent className="py-12 text-center">
                <Clock className="h-12 w-12 text-zinc-300 mx-auto mb-4" />
                <p className="text-zinc-500">No pending workflow requests</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {pendingRequests.map(renderRequestCard)}
            </div>
          )}
        </TabsContent>

        {['transfer', 'promotion', 'ctc_revision', 'hierarchy_change'].map(type => (
          <TabsContent key={type} value={type} className="space-y-4">
            {(groupedRequests[type]?.length || 0) === 0 ? (
              <Card className="border-zinc-200">
                <CardContent className="py-12 text-center">
                  <Clock className="h-12 w-12 text-zinc-300 mx-auto mb-4" />
                  <p className="text-zinc-500">No pending {WORKFLOW_TYPES[type].label.toLowerCase()} requests</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {groupedRequests[type]?.map(renderRequestCard)}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* New Request Dialog */}
      <Dialog open={newRequestDialog} onOpenChange={setNewRequestDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Workflow Request</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Request Type Selection */}
            <div className="space-y-2">
              <Label>Request Type *</Label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(WORKFLOW_TYPES).slice(0, 4).map(([type, config]) => {
                  const Icon = config.icon;
                  return (
                    <Button
                      key={type}
                      variant={requestType === type ? 'default' : 'outline'}
                      className={`justify-start ${requestType === type ? 'bg-zinc-900' : ''}`}
                      onClick={() => {
                        setRequestType(type);
                        setNewValue('');
                      }}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      {config.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Employee Selection */}
            {requestType && (
              <div className="space-y-2">
                <Label>Select Employee *</Label>
                <select
                  value={selectedEmployee?.id || ''}
                  onChange={(e) => {
                    const emp = employees.find(emp => emp.id === e.target.value);
                    setSelectedEmployee(emp);
                  }}
                  className="w-full h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm"
                >
                  <option value="">Select an employee</option>
                  {employees.filter(e => e.go_live_status === 'active' || e.has_portal_access).map(emp => (
                    <option key={emp.id} value={emp.id}>
                      {emp.employee_id || 'Pending'} - {emp.first_name} {emp.last_name} ({emp.designation || 'No designation'})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Current Value Display */}
            {selectedEmployee && requestType && (
              <div className="bg-zinc-50 p-3 rounded-lg">
                <p className="text-sm text-zinc-500">Current {WORKFLOW_TYPES[requestType].label}</p>
                <p className="font-medium text-zinc-900">
                  {requestType === 'transfer' && (selectedEmployee.department || 'Not assigned')}
                  {requestType === 'promotion' && (selectedEmployee.designation || 'Not assigned')}
                  {requestType === 'ctc_revision' && (selectedEmployee.salary ? `₹${selectedEmployee.salary.toLocaleString()}` : 'Not set')}
                  {requestType === 'hierarchy_change' && (selectedEmployee.reporting_manager_name || 'No manager')}
                </p>
              </div>
            )}

            {/* New Value Input */}
            {selectedEmployee && requestType && (
              <div className="space-y-2">
                <Label>
                  New {WORKFLOW_TYPES[requestType].label} *
                </Label>
                {requestType === 'transfer' ? (
                  <select
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select department</option>
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                ) : requestType === 'hierarchy_change' ? (
                  <select
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    className="w-full h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select reporting manager</option>
                    {employees.filter(e => e.id !== selectedEmployee?.id).map(emp => (
                      <option key={emp.id} value={emp.id}>
                        {emp.employee_id || 'Pending'} - {emp.first_name} {emp.last_name}
                      </option>
                    ))}
                  </select>
                ) : requestType === 'ctc_revision' ? (
                  <Input
                    type="number"
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    placeholder="Enter new annual CTC"
                  />
                ) : (
                  <Input
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    placeholder={`Enter new ${requestType === 'promotion' ? 'designation' : 'value'}`}
                  />
                )}
              </div>
            )}

            {/* Change Reason */}
            {selectedEmployee && requestType && newValue && (
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Input
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  placeholder="e.g., Performance review, Restructuring, Annual increment"
                />
              </div>
            )}

            {/* Warning */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5" />
                <p className="text-xs text-amber-800">
                  This request will be sent to Admin for approval. The change will only be applied after admin approval.
                </p>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setNewRequestDialog(false);
              resetNewRequestForm();
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleCreateRequest}
              disabled={!selectedEmployee || !newValue || !changeReason || createRequestMutation.isPending}
              className="bg-zinc-950 text-white"
            >
              {createRequestMutation.isPending ? 'Submitting...' : 'Submit Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approval Dialog */}
      <Dialog open={approvalDialog} onOpenChange={setApprovalDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Approve Request</DialogTitle>
          </DialogHeader>
          {selectedRequest && (
            <div className="space-y-4">
              <div className="bg-zinc-50 p-4 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-zinc-500">Employee</span>
                  <span className="font-medium">{selectedRequest.employee_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-zinc-500">Change Type</span>
                  <Badge className={WORKFLOW_TYPES[selectedRequest.workflow_type]?.color}>
                    {WORKFLOW_TYPES[selectedRequest.workflow_type]?.label}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-zinc-500">Field</span>
                  <span className="font-medium">{selectedRequest.field}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-zinc-500">Current Value</span>
                  <span className="text-zinc-400">{selectedRequest.current_value || 'None'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-zinc-500">New Value</span>
                  <span className="font-medium text-emerald-600">{selectedRequest.requested_value}</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Approval Remarks (Optional)</Label>
                <Input
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Add any notes..."
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setApprovalDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => approveMutation.mutate({ 
                requestId: selectedRequest.id, 
                remarks 
              })}
              disabled={approveMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {approveMutation.isPending ? 'Approving...' : 'Approve & Apply Change'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialog} onOpenChange={setRejectDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reject Request</DialogTitle>
          </DialogHeader>
          {selectedRequest && (
            <div className="space-y-4">
              <div className="bg-red-50 p-4 rounded-lg">
                <p className="text-sm text-red-800">
                  You are about to reject the {WORKFLOW_TYPES[selectedRequest.workflow_type]?.label.toLowerCase()} request 
                  for <strong>{selectedRequest.employee_name}</strong>.
                </p>
              </div>
              
              <div className="space-y-2">
                <Label>Rejection Reason *</Label>
                <Input
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Explain why this request is being rejected..."
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => rejectMutation.mutate({ 
                requestId: selectedRequest.id, 
                reason: rejectionReason 
              })}
              disabled={!rejectionReason || rejectMutation.isPending}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmployeeWorkflows;
