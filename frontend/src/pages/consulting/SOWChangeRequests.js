import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  FileEdit, Clock, CheckCircle, XCircle, AlertCircle, Loader2, 
  Plus, Eye, Building2, User, Calendar, MessageSquare, ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import ViewToggle from '../../components/ViewToggle';
import ConsultingStageNav from '../../components/ConsultingStageNav';
import { sanitizeDisplayText } from '../../utils/sanitize';

const STATUS_CONFIG = {
  pending: { label: 'Pending RM', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  pending_client: { label: 'Pending Client', color: 'bg-blue-100 text-blue-700', icon: Clock },
  rm_approved: { label: 'RM Approved', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  client_approved: { label: 'Client Approved', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  applied: { label: 'Applied', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700', icon: XCircle },
};

const CHANGE_TYPES = [
  { value: 'add_scope', label: 'Add New Scope' },
  { value: 'modify_scope', label: 'Modify Existing Scope' },
  { value: 'add_task', label: 'Add Task to Scope' },
  { value: 'update_task', label: 'Update Task' },
];

const SOWChangeRequests = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [viewMode, setViewMode] = useState('card');
  const [activeTab, setActiveTab] = useState('my-requests');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [sows, setSows] = useState([]);
  
  // Form state
  const [formData, setFormData] = useState({
    sow_id: '',
    change_type: 'add_scope',
    title: '',
    description: '',
    requires_client_approval: false,
    proposed_changes: {}
  });
  const [submitting, setSubmitting] = useState(false);

  const isPM = user?.role === 'project_manager' || user?.role === 'manager' || user?.role === 'admin';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [requestsRes, pendingRes, sowsRes] = await Promise.all([
        axios.get(`${API}/sow-change-requests`).catch(() => ({ data: [] })),
        isPM ? axios.get(`${API}/sow-change-requests/pending`).catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
        axios.get(`${API}/enhanced-sow/list?role=consulting`).catch(() => ({ data: [] }))
      ]);
      
      setRequests(requestsRes.data || []);
      setPendingRequests(pendingRes.data || []);
      setSows((sowsRes.data || []).filter(s => s.sales_handover_complete));
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRequest = async () => {
    if (!formData.sow_id || !formData.title || !formData.description) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/sow-change-requests`, formData);
      toast.success('Change request submitted');
      setShowCreateDialog(false);
      setFormData({
        sow_id: '',
        change_type: 'add_scope',
        title: '',
        description: '',
        requires_client_approval: false,
        proposed_changes: {}
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (requestId, comments = '') => {
    try {
      await axios.post(`${API}/sow-change-requests/${requestId}/approve?approval_type=rm&comments=${encodeURIComponent(comments)}`);
      toast.success('Request approved');
      setShowDetailDialog(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to approve request');
    }
  };

  const handleReject = async (requestId, reason) => {
    if (!reason) {
      toast.error('Please provide a rejection reason');
      return;
    }
    try {
      await axios.post(`${API}/sow-change-requests/${requestId}/reject?rejection_reason=${encodeURIComponent(reason)}`);
      toast.success('Request rejected');
      setShowDetailDialog(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to reject request');
    }
  };

  const getStatusBadge = (status) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    return (
      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-sm ${config.color}`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  const displayRequests = activeTab === 'pending' ? pendingRequests : requests;

  return (
    <div data-testid="sow-change-requests-page">
      {/* Stage Navigation */}
      <ConsultingStageNav 
        currentStage={4}
        completedStages={[1, 2, 3]}
        showFullNav={true}
        onBack={() => navigate('/consulting/my-projects')}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
            SOW Change Requests
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Request and manage changes to project scopes
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} data-testid="new-change-request-btn">
          <Plus className="w-4 h-4 mr-2" />
          New Change Request
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="my-requests">My Requests ({requests.length})</TabsTrigger>
          {isPM && (
            <TabsTrigger value="pending">Pending Approval ({pendingRequests.length})</TabsTrigger>
          )}
        </TabsList>
      </Tabs>

      {/* Filters */}
      <div className="flex items-center justify-end mb-4">
        <ViewToggle viewMode={viewMode} onChange={setViewMode} />
      </div>

      {/* Requests List */}
      {displayRequests.length > 0 ? (
        viewMode === 'list' ? (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Title</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Requested By</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {displayRequests.map(req => (
                  <tr 
                    key={req.id} 
                    className="hover:bg-zinc-50 cursor-pointer"
                    onClick={() => { setSelectedRequest(req); setShowDetailDialog(true); }}
                  >
                    <td className="px-4 py-3 font-medium text-zinc-900">{sanitizeDisplayText(req.title)}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {CHANGE_TYPES.find(t => t.value === req.change_type)?.label || req.change_type}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{sanitizeDisplayText(req.requested_by_name)}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {req.created_at ? format(new Date(req.created_at), 'MMM d, yyyy') : '-'}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(req.status)}</td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" onClick={() => { setSelectedRequest(req); setShowDetailDialog(true); }}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-3">
            {displayRequests.map(req => (
              <Card 
                key={req.id}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 cursor-pointer"
                onClick={() => { setSelectedRequest(req); setShowDetailDialog(true); }}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium text-zinc-900">{sanitizeDisplayText(req.title)}</h3>
                        {getStatusBadge(req.status)}
                      </div>
                      <p className="text-sm text-zinc-600 mb-3 line-clamp-2">
                        {sanitizeDisplayText(req.description)}
                      </p>
                      <div className="flex items-center gap-4 text-sm text-zinc-500">
                        <span className="flex items-center gap-1">
                          <FileEdit className="w-3.5 h-3.5" />
                          {CHANGE_TYPES.find(t => t.value === req.change_type)?.label}
                        </span>
                        <span className="flex items-center gap-1">
                          <User className="w-3.5 h-3.5" />
                          {sanitizeDisplayText(req.requested_by_name)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {req.created_at ? format(new Date(req.created_at), 'MMM d, yyyy') : '-'}
                        </span>
                        {req.requires_client_approval && (
                          <Badge variant="outline" className="text-xs">Requires Client Approval</Badge>
                        )}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setSelectedRequest(req); setShowDetailDialog(true); }}>
                      <Eye className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : (
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileEdit className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No Change Requests</h3>
            <p className="text-zinc-500 mb-4">
              {activeTab === 'pending' ? 'No requests pending approval' : 'Create a change request to modify project scopes'}
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Request
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New SOW Change Request</DialogTitle>
            <DialogDescription>
              Request changes to project scopes. Your request will be reviewed by the Reporting Manager.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Project *</Label>
              <Select value={formData.sow_id} onValueChange={(v) => setFormData({...formData, sow_id: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a project" />
                </SelectTrigger>
                <SelectContent>
                  {sows.map(sow => (
                    <SelectItem key={sow.id} value={sow.id}>
                      {sow.client_name || sow.lead_name || 'Project'} - {sow.scopes?.length || 0} scopes
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Change Type *</Label>
              <Select value={formData.change_type} onValueChange={(v) => setFormData({...formData, change_type: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHANGE_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Title *</Label>
              <Input 
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                placeholder="Brief title for the change"
              />
            </div>
            <div className="space-y-2">
              <Label>Description *</Label>
              <Textarea 
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                placeholder="Describe the change in detail..."
                rows={4}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="client-approval"
                checked={formData.requires_client_approval}
                onChange={(e) => setFormData({...formData, requires_client_approval: e.target.checked})}
                className="rounded border-zinc-300"
              />
              <Label htmlFor="client-approval" className="text-sm font-normal cursor-pointer">
                Requires client approval
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateRequest} disabled={submitting}>
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{sanitizeDisplayText(selectedRequest?.title)}</DialogTitle>
          </DialogHeader>
          {selectedRequest && (
            <div className="space-y-4 py-4">
              <div className="flex items-center gap-2">
                {getStatusBadge(selectedRequest.status)}
                <Badge variant="outline">
                  {CHANGE_TYPES.find(t => t.value === selectedRequest.change_type)?.label}
                </Badge>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Description</Label>
                <p className="text-sm text-zinc-700 mt-1">{sanitizeDisplayText(selectedRequest.description)}</p>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <Label className="text-xs text-zinc-500">Requested By</Label>
                  <p className="text-zinc-700">{sanitizeDisplayText(selectedRequest.requested_by_name)}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Date</Label>
                  <p className="text-zinc-700">
                    {selectedRequest.created_at ? format(new Date(selectedRequest.created_at), 'MMM d, yyyy h:mm a') : '-'}
                  </p>
                </div>
              </div>
              {selectedRequest.rm_approval && (
                <div className="p-3 bg-zinc-50 rounded-sm">
                  <Label className="text-xs text-zinc-500">RM Approval</Label>
                  <p className="text-sm text-zinc-700">
                    {selectedRequest.rm_approval.approved_by_name || selectedRequest.rm_approval.rejected_by_name}
                    {selectedRequest.rm_approval.approved_at && ` on ${format(new Date(selectedRequest.rm_approval.approved_at), 'MMM d, yyyy')}`}
                    {selectedRequest.rm_approval.rejected_at && ` on ${format(new Date(selectedRequest.rm_approval.rejected_at), 'MMM d, yyyy')}`}
                  </p>
                  {selectedRequest.rm_approval.reason && (
                    <p className="text-sm text-red-600 mt-1">Reason: {selectedRequest.rm_approval.reason}</p>
                  )}
                </div>
              )}
              {isPM && selectedRequest.status === 'pending' && (
                <div className="flex gap-2 pt-4 border-t">
                  <Button 
                    variant="outline" 
                    className="flex-1 text-red-600 border-red-200 hover:bg-red-50"
                    onClick={() => {
                      const reason = prompt('Please provide a rejection reason:');
                      if (reason) handleReject(selectedRequest.id, reason);
                    }}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </Button>
                  <Button 
                    className="flex-1"
                    onClick={() => handleApprove(selectedRequest.id)}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SOWChangeRequests;
