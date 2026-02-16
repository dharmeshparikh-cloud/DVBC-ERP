import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Send, Inbox, CheckCircle, XCircle, Clock, Plus, Eye, Edit2,
  Building2, Calendar, Users, ArrowRight, FileText,
  RotateCcw, CalendarCheck, MessageSquare, ChevronRight, AlertCircle,
  Briefcase, UserCheck
} from 'lucide-react';
import ViewToggle from '../components/ViewToggle';

// Helper function to sanitize display text (strip HTML tags)
const sanitizeDisplayText = (text) => {
  if (!text || typeof text !== 'string') return text;
  return text.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, '');
};

const KickoffRequests = () => {
  const { user } = useContext(AuthContext);
  const [requests, setRequests] = useState([]);
  const [agreements, setAgreements] = useState([]);
  const [projectManagers, setProjectManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('card');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showReturnDialog, setShowReturnDialog] = useState(false);
  const [showEditDateDialog, setShowEditDateDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  const [returnNotes, setReturnNotes] = useState('');
  const [editDate, setEditDate] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [formData, setFormData] = useState({
    agreement_id: '',
    client_name: '',
    project_name: '',
    project_type: 'mixed',
    total_meetings: 0,
    meeting_frequency: 'Monthly',
    project_tenure_months: 12,
    expected_start_date: '',
    assigned_pm_id: '',
    assigned_pm_name: '',
    notes: ''
  });

  const isSalesRole = ['executive', 'account_manager', 'admin', 'manager'].includes(user?.role);
  const isPMRole = ['project_manager', 'admin', 'manager'].includes(user?.role);

  useEffect(() => {
    fetchRequests();
    if (isSalesRole) {
      fetchAgreements();
      fetchProjectManagers();
    }
  }, []);

  const fetchRequests = async () => {
    try {
      const response = await fetch(`${API}/kickoff-requests`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRequests(data);
      }
    } catch (error) {
      console.error('Failed to fetch kickoff requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgreements = async () => {
    try {
      const response = await fetch(`${API}/agreements?status=approved`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAgreements(data);
      }
    } catch (error) {
      console.error('Failed to fetch agreements:', error);
    }
  };

  const fetchProjectManagers = async () => {
    try {
      const response = await fetch(`${API}/users?role=project_manager`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setProjectManagers(data);
      }
    } catch (error) {
      console.error('Failed to fetch PMs:', error);
    }
  };

  const fetchRequestDetails = async (requestId) => {
    setLoadingDetails(true);
    try {
      const response = await fetch(`${API}/kickoff-requests/${requestId}/details`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDetailData(data);
      } else {
        toast.error('Failed to fetch request details');
      }
    } catch (error) {
      toast.error('Failed to fetch request details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleViewDetails = async (request) => {
    setSelectedRequest(request);
    setShowDetailDialog(true);
    await fetchRequestDetails(request.id);
  };

  const handleAgreementSelect = (agreementId) => {
    const agreement = agreements.find(a => a.id === agreementId);
    if (agreement) {
      setFormData(prev => ({
        ...prev,
        agreement_id: agreementId,
        client_name: agreement.client_name || agreement.party_name || '',
        project_name: `${agreement.client_name || agreement.party_name || 'Client'} - Project`,
        meeting_frequency: agreement.meeting_frequency || 'Monthly',
        project_tenure_months: agreement.project_tenure_months || 12
      }));
    }
  };

  const handlePMSelect = (pmId) => {
    const pm = projectManagers.find(p => p.id === pmId);
    setFormData(prev => ({
      ...prev,
      assigned_pm_id: pmId,
      assigned_pm_name: pm?.full_name || ''
    }));
  };

  const handleCreateKickoff = async () => {
    if (!formData.agreement_id || !formData.project_name) {
      toast.error('Please fill required fields');
      return;
    }

    try {
      const payload = {
        ...formData,
        total_meetings: parseInt(formData.total_meetings) || 0,
        project_tenure_months: parseInt(formData.project_tenure_months) || 12,
        expected_start_date: formData.expected_start_date ? new Date(formData.expected_start_date).toISOString() : null
      };

      const response = await fetch(`${API}/kickoff-requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        toast.success('Kickoff request sent successfully');
        setShowCreateDialog(false);
        setFormData({
          agreement_id: '', client_name: '', project_name: '',
          project_type: 'mixed', total_meetings: 0, meeting_frequency: 'Monthly',
          project_tenure_months: 12, expected_start_date: '', assigned_pm_id: '', 
          assigned_pm_name: '', notes: ''
        });
        fetchRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create kickoff request');
      }
    } catch (error) {
      toast.error('Failed to create kickoff request');
    }
  };

  const handleEditDate = async () => {
    if (!selectedRequest) return;
    
    try {
      const payload = {
        expected_start_date: editDate ? new Date(editDate).toISOString() : null,
        notes: editNotes || selectedRequest.notes
      };
      
      const response = await fetch(`${API}/kickoff-requests/${selectedRequest.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        toast.success('Kickoff date updated successfully');
        setShowEditDateDialog(false);
        setEditDate('');
        setEditNotes('');
        fetchRequests();
        if (showDetailDialog) {
          fetchRequestDetails(selectedRequest.id);
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update kickoff date');
      }
    } catch (error) {
      toast.error('Failed to update kickoff date');
    }
  };

  const handleAccept = async (requestId) => {
    try {
      const response = await fetch(`${API}/kickoff-requests/${requestId}/accept`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        toast.success('Project created successfully');
        setShowDetailDialog(false);
        fetchRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to accept request');
      }
    } catch (error) {
      toast.error('Failed to accept request');
    }
  };

  const handleReturn = async () => {
    if (!selectedRequest || !returnReason.trim()) {
      toast.error('Please provide a reason for returning');
      return;
    }

    try {
      const response = await fetch(`${API}/kickoff-requests/${selectedRequest.id}/return`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          reason: returnReason,
          return_notes: returnNotes
        })
      });

      if (response.ok) {
        toast.success('Request returned to sender');
        setShowReturnDialog(false);
        setShowDetailDialog(false);
        setReturnReason('');
        setReturnNotes('');
        fetchRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to return request');
      }
    } catch (error) {
      toast.error('Failed to return request');
    }
  };

  const handleResubmit = async (requestId) => {
    try {
      const response = await fetch(`${API}/kickoff-requests/${requestId}/resubmit`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        toast.success('Request resubmitted successfully');
        fetchRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to resubmit request');
      }
    } catch (error) {
      toast.error('Failed to resubmit request');
    }
  };

  const handleReject = async (requestId) => {
    try {
      const response = await fetch(`${API}/kickoff-requests/${requestId}/reject`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        toast.success('Request rejected');
        fetchRequests();
      } else {
        toast.error('Failed to reject request');
      }
    } catch (error) {
      toast.error('Failed to reject request');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-700',
      accepted: 'bg-green-100 text-green-700',
      converted: 'bg-blue-100 text-blue-700',
      rejected: 'bg-red-100 text-red-700',
      returned: 'bg-orange-100 text-orange-700'
    };
    return <Badge className={styles[status] || 'bg-zinc-100'}>{status}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
      </div>
    );
  }

  const pendingRequests = requests.filter(r => r.status === 'pending');
  const returnedRequests = requests.filter(r => r.status === 'returned');
  const processedRequests = requests.filter(r => !['pending', 'returned'].includes(r.status));

  return (
    <div className="space-y-6" data-testid="kickoff-requests-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Kickoff Requests</h1>
          <p className="text-sm text-zinc-500">
            {isSalesRole && isPMRole 
              ? 'Send and manage project handoffs' 
              : isSalesRole 
                ? 'Send project handoffs to consulting team'
                : 'Receive and accept incoming projects'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ViewToggle viewMode={viewMode} onChange={setViewMode} />
          {isSalesRole && (
            <Button onClick={() => setShowCreateDialog(true)} data-testid="create-kickoff-btn">
              <Plus className="w-4 h-4 mr-2" />
              New Kickoff Request
            </Button>
          )}
        </div>
      </div>

      {/* Returned Requests (for Sales) */}
      {isSalesRole && returnedRequests.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2 text-orange-600">
            <RotateCcw className="w-5 h-5" />
            Returned for Revision ({returnedRequests.length})
          </h2>
          {viewMode === 'list' ? (
            <div className="border border-orange-200 rounded-sm overflow-hidden">
              <table className="w-full">
                <thead className="bg-orange-50 border-b border-orange-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Project</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Client</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Start Date</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Return Reason</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Status</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-orange-600 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-orange-100">
                  {returnedRequests.map((request) => (
                    <tr 
                      key={request.id} 
                      className="hover:bg-orange-50/50 cursor-pointer transition-colors"
                      onClick={() => handleViewDetails(request)}
                      data-testid={`returned-request-row-${request.id}`}
                    >
                      <td className="px-4 py-3 font-medium text-zinc-900">{request.project_name}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{request.client_name}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {request.expected_start_date ? new Date(request.expected_start_date).toLocaleDateString() : 'TBD'}
                      </td>
                      <td className="px-4 py-3 text-sm text-orange-700">{request.return_reason || '-'}</td>
                      <td className="px-4 py-3">{getStatusBadge(request.status)}</td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" onClick={() => handleViewDetails(request)} className="h-8">
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button size="sm" onClick={() => handleResubmit(request.id)} className="bg-orange-600 hover:bg-orange-700 h-8">
                            <Send className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid gap-4">
              {returnedRequests.map((request) => (
                <Card key={request.id} className="border-orange-200 bg-orange-50/50 cursor-pointer hover:border-orange-300 transition-colors" onClick={() => handleViewDetails(request)} data-testid={`returned-request-${request.id}`}>
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-zinc-900">{request.project_name}</h3>
                          {getStatusBadge(request.status)}
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-zinc-400" />
                            <span>{request.client_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-zinc-400" />
                            <span>{request.expected_start_date ? new Date(request.expected_start_date).toLocaleDateString() : 'TBD'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Users className="w-4 h-4 text-zinc-400" />
                            <span>{request.meeting_frequency || 'Monthly'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Briefcase className="w-4 h-4 text-zinc-400" />
                            <span>{request.project_tenure_months || 12} months</span>
                          </div>
                        </div>
                        {request.return_reason && (
                          <div className="mt-3 p-3 bg-orange-100 rounded-md">
                            <p className="text-sm text-orange-800">
                              <strong>Return Reason:</strong> {request.return_reason}
                            </p>
                            {request.return_notes && (
                              <p className="text-sm text-orange-700 mt-1">{request.return_notes}</p>
                            )}
                            <p className="text-xs text-orange-600 mt-1">
                              Returned by: {sanitizeDisplayText(request.returned_by_name) || 'PM'} on {new Date(request.returned_at).toLocaleDateString()}
                            </p>
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2 ml-4" onClick={(e) => e.stopPropagation()}>
                        <Button variant="outline" size="sm" onClick={() => handleViewDetails(request)}>
                          <Eye className="w-4 h-4 mr-1" />
                          View Details
                        </Button>
                        <Button size="sm" onClick={() => handleResubmit(request.id)} className="bg-orange-600 hover:bg-orange-700" data-testid={`resubmit-btn-${request.id}`}>
                          <Send className="w-4 h-4 mr-1" />
                          Resubmit
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pending Requests */}
      {pendingRequests.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Inbox className="w-5 h-5" />
            Pending Requests ({pendingRequests.length})
          </h2>
          {viewMode === 'list' ? (
            <div className="border border-amber-200 rounded-sm overflow-hidden">
              <table className="w-full">
                <thead className="bg-amber-50 border-b border-amber-200">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Project</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Client</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Start Date</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Frequency</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Requested By</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Status</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-amber-700 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-amber-100">
                  {pendingRequests.map((request) => (
                    <tr 
                      key={request.id} 
                      className="hover:bg-amber-50/50 cursor-pointer transition-colors"
                      onClick={() => handleViewDetails(request)}
                      data-testid={`pending-request-row-${request.id}`}
                    >
                      <td className="px-4 py-3 font-medium text-zinc-900">{request.project_name}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{request.client_name}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {request.expected_start_date ? new Date(request.expected_start_date).toLocaleDateString() : 'TBD'}
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{request.meeting_frequency || 'Monthly'}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{request.requested_by_name || 'Unknown'}</td>
                      <td className="px-4 py-3">{getStatusBadge(request.status)}</td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <Button variant="outline" size="sm" onClick={() => handleViewDetails(request)} className="h-8" data-testid={`view-details-btn-${request.id}`}>
                          <Eye className="w-4 h-4 mr-1" />
                          {isPMRole ? 'Review' : 'View'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid gap-4">
              {pendingRequests.map((request) => (
                <Card key={request.id} className="border-amber-200 bg-amber-50/50 cursor-pointer hover:border-amber-300 transition-colors" onClick={() => handleViewDetails(request)} data-testid={`pending-request-${request.id}`}>
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-zinc-900">{request.project_name}</h3>
                          {getStatusBadge(request.status)}
                        </div>
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-zinc-400" />
                            <span>{request.client_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-zinc-400" />
                            <span>{request.expected_start_date ? new Date(request.expected_start_date).toLocaleDateString() : 'TBD'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Users className="w-4 h-4 text-zinc-400" />
                            <span>{request.meeting_frequency || 'Monthly'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Briefcase className="w-4 h-4 text-zinc-400" />
                            <span>{request.project_tenure_months || 12} months</span>
                          </div>
                        </div>
                        <p className="text-xs text-zinc-500 mt-2">
                          Requested by: {request.requested_by_name || 'Unknown'} • 
                          {new Date(request.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4" onClick={(e) => e.stopPropagation()}>
                        {isPMRole && (
                          <Button variant="outline" size="sm" onClick={() => handleViewDetails(request)} data-testid={`view-details-btn-${request.id}`}>
                            <Eye className="w-4 h-4 mr-1" />
                            Review
                          </Button>
                        )}
                        {!isPMRole && (
                          <Button variant="outline" size="sm" onClick={() => handleViewDetails(request)}>
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Processed Requests - Kickoff Status */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Kickoff Status History
        </h2>
        {processedRequests.length === 0 ? (
          <Card className="border-zinc-200">
            <CardContent className="py-8 text-center text-zinc-500">
              No processed requests yet
            </CardContent>
          </Card>
        ) : viewMode === 'list' ? (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Project</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Client</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Created</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Accepted</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {processedRequests.map((request) => (
                  <tr 
                    key={request.id} 
                    className="hover:bg-zinc-50 cursor-pointer transition-colors"
                    onClick={() => handleViewDetails(request)}
                    data-testid={`processed-request-row-${request.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-zinc-900">{request.project_name}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{request.client_name}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{new Date(request.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-sm text-green-600">
                      {request.accepted_at ? new Date(request.accepted_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(request.status)}</td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => handleViewDetails(request)} className="h-8">
                          <Eye className="w-4 h-4" />
                        </Button>
                        {request.status === 'converted' && request.project_id && (
                          <Button variant="outline" size="sm" asChild className="h-8">
                            <a href={`/projects`}>
                              View Project <ArrowRight className="w-4 h-4 ml-1" />
                            </a>
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid gap-4">
            {processedRequests.map((request) => (
              <Card key={request.id} className="border-zinc-200 cursor-pointer hover:border-zinc-300 transition-colors" onClick={() => handleViewDetails(request)} data-testid={`processed-request-${request.id}`}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-zinc-900">{request.project_name}</h3>
                        {getStatusBadge(request.status)}
                      </div>
                      <p className="text-sm text-zinc-500 mt-1">
                        {request.client_name} • {new Date(request.created_at).toLocaleDateString()}
                        {request.accepted_at && (
                          <span className="text-green-600 ml-2">
                            • Accepted: {new Date(request.accepted_at).toLocaleDateString()}
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" onClick={() => handleViewDetails(request)}>
                        <Eye className="w-4 h-4" />
                      </Button>
                      {request.status === 'converted' && request.project_id && (
                        <Button variant="outline" size="sm" asChild>
                          <a href={`/projects`}>
                            View Project <ArrowRight className="w-4 h-4 ml-1" />
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Kickoff Request</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Agreement *</Label>
              <Select value={formData.agreement_id} onValueChange={handleAgreementSelect}>
                <SelectTrigger>
                  <SelectValue placeholder="Select approved agreement" />
                </SelectTrigger>
                <SelectContent>
                  {agreements.map((agreement) => (
                    <SelectItem key={agreement.id} value={agreement.id}>
                      {agreement.party_name || agreement.client_name || agreement.id} - {agreement.agreement_number || 'Agreement'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Client Name</Label>
                <Input 
                  value={formData.client_name}
                  onChange={(e) => setFormData({...formData, client_name: e.target.value})}
                  placeholder="Client name"
                />
              </div>
              <div className="space-y-2">
                <Label>Project Name *</Label>
                <Input 
                  value={formData.project_name}
                  onChange={(e) => setFormData({...formData, project_name: e.target.value})}
                  placeholder="Project name"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Project Type</Label>
                <Select value={formData.project_type} onValueChange={(v) => setFormData({...formData, project_type: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="online">Online</SelectItem>
                    <SelectItem value="offline">Offline</SelectItem>
                    <SelectItem value="mixed">Mixed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Meeting Frequency</Label>
                <Select value={formData.meeting_frequency} onValueChange={(v) => setFormData({...formData, meeting_frequency: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Weekly">Weekly</SelectItem>
                    <SelectItem value="Bi-weekly">Bi-weekly</SelectItem>
                    <SelectItem value="Monthly">Monthly</SelectItem>
                    <SelectItem value="Quarterly">Quarterly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Project Tenure (months)</Label>
                <Input 
                  type="number"
                  min="1"
                  max="60"
                  value={formData.project_tenure_months}
                  onChange={(e) => setFormData({...formData, project_tenure_months: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Expected Start Date</Label>
                <Input 
                  type="date"
                  value={formData.expected_start_date}
                  onChange={(e) => setFormData({...formData, expected_start_date: e.target.value})}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Assign to Project Manager</Label>
              <Select value={formData.assigned_pm_id} onValueChange={handlePMSelect}>
                <SelectTrigger>
                  <SelectValue placeholder="Select PM (optional)" />
                </SelectTrigger>
                <SelectContent>
                  {projectManagers.map((pm) => (
                    <SelectItem key={pm.id} value={pm.id}>
                      {pm.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea 
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Any additional notes for the PM..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateKickoff}>
              <Send className="w-4 h-4 mr-2" />
              Send Kickoff Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail View Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Kickoff Request Details</span>
              {selectedRequest && getStatusBadge(selectedRequest.status)}
            </DialogTitle>
            <DialogDescription>
              Review the scope of work and team deployment before accepting
            </DialogDescription>
          </DialogHeader>
          
          {loadingDetails ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
            </div>
          ) : detailData ? (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="w-full justify-start">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="team">Team Deployment</TabsTrigger>
                <TabsTrigger value="sow">Scope of Work</TabsTrigger>
                <TabsTrigger value="agreement">Agreement</TabsTrigger>
              </TabsList>
              
              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Project Information</CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-zinc-500 text-xs">Project Name</Label>
                      <p className="font-medium">{detailData.kickoff_request?.project_name}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Client</Label>
                      <p className="font-medium">{detailData.kickoff_request?.client_name}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Project Type</Label>
                      <p className="font-medium capitalize">{detailData.kickoff_request?.project_type}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Meeting Frequency</Label>
                      <p className="font-medium">{detailData.kickoff_request?.meeting_frequency || detailData.agreement?.meeting_frequency || 'Monthly'}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Project Tenure</Label>
                      <p className="font-medium">{detailData.kickoff_request?.project_tenure_months || detailData.agreement?.project_tenure_months || 12} months</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Expected Start Date</Label>
                      <p className="font-medium flex items-center gap-2">
                        {detailData.kickoff_request?.expected_start_date 
                          ? new Date(detailData.kickoff_request.expected_start_date).toLocaleDateString()
                          : 'Not set'}
                        {isPMRole && selectedRequest?.status === 'pending' && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => {
                              setEditDate(detailData.kickoff_request?.expected_start_date?.split('T')[0] || '');
                              setEditNotes(detailData.kickoff_request?.notes || '');
                              setShowEditDateDialog(true);
                            }}
                            className="h-6 px-2"
                            data-testid="edit-date-btn"
                          >
                            <Edit2 className="w-3 h-3" />
                          </Button>
                        )}
                      </p>
                    </div>
                    <div className="col-span-2">
                      <Label className="text-zinc-500 text-xs">Notes</Label>
                      <p className="text-sm">{detailData.kickoff_request?.notes || 'No notes'}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Requested By</Label>
                      <p className="font-medium">{detailData.kickoff_request?.requested_by_name}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Request Date</Label>
                      <p className="font-medium">
                        {detailData.kickoff_request?.created_at 
                          ? new Date(detailData.kickoff_request.created_at).toLocaleDateString()
                          : '-'}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {detailData.lead && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Client Information</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-zinc-500 text-xs">Contact Name</Label>
                        <p className="font-medium">{detailData.lead.first_name} {detailData.lead.last_name}</p>
                      </div>
                      <div>
                        <Label className="text-zinc-500 text-xs">Company</Label>
                        <p className="font-medium">{detailData.lead.company}</p>
                      </div>
                      <div>
                        <Label className="text-zinc-500 text-xs">Email</Label>
                        <p className="font-medium">{detailData.lead.email || '-'}</p>
                      </div>
                      <div>
                        <Label className="text-zinc-500 text-xs">Phone</Label>
                        <p className="font-medium">{detailData.lead.phone || '-'}</p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Team Deployment Tab */}
              <TabsContent value="team" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <UserCheck className="w-5 h-5" />
                      Team Deployment Structure
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {detailData.team_deployment && detailData.team_deployment.length > 0 ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-4 gap-4 text-sm font-medium text-zinc-500 border-b pb-2">
                          <div>Role</div>
                          <div>Meeting Type</div>
                          <div>Frequency</div>
                          <div>Mode</div>
                        </div>
                        {detailData.team_deployment.map((member, i) => (
                          <div key={i} className="grid grid-cols-4 gap-4 text-sm py-2 border-b border-zinc-100">
                            <div className="font-medium">{member.role}</div>
                            <div>{member.meeting_type}</div>
                            <div>{member.frequency}</div>
                            <div className="capitalize">{member.mode}</div>
                          </div>
                        ))}
                      </div>
                    ) : detailData.agreement?.team_deployment && detailData.agreement.team_deployment.length > 0 ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-4 gap-4 text-sm font-medium text-zinc-500 border-b pb-2">
                          <div>Role</div>
                          <div>Meeting Type</div>
                          <div>Frequency</div>
                          <div>Mode</div>
                        </div>
                        {detailData.agreement.team_deployment.map((member, i) => (
                          <div key={i} className="grid grid-cols-4 gap-4 text-sm py-2 border-b border-zinc-100">
                            <div className="font-medium">{member.role}</div>
                            <div>{member.meeting_type}</div>
                            <div>{member.frequency}</div>
                            <div className="capitalize">{member.mode}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-zinc-500">
                        <Users className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                        <p>No team deployment structure defined</p>
                        <p className="text-sm">Team members will be assigned after project creation</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Meeting Summary */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Meeting Schedule Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-zinc-500 text-xs">Meeting Frequency</Label>
                      <p className="font-medium text-lg">{detailData.agreement?.meeting_frequency || detailData.kickoff_request?.meeting_frequency || 'Monthly'}</p>
                    </div>
                    <div>
                      <Label className="text-zinc-500 text-xs">Project Duration</Label>
                      <p className="font-medium text-lg">{detailData.agreement?.project_tenure_months || detailData.kickoff_request?.project_tenure_months || 12} months</p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* SOW Tab */}
              <TabsContent value="sow" className="space-y-4">
                {detailData.sow?.items?.length > 0 ? (
                  <div className="space-y-3">
                    {detailData.sow.items.map((item, index) => (
                      <Card key={item.id || index}>
                        <CardContent className="pt-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant="secondary" className="text-xs">{item.category}</Badge>
                                <span className="font-medium">{item.title}</span>
                              </div>
                              {item.description && (
                                <p className="text-sm text-zinc-600 mb-2">{item.description}</p>
                              )}
                              {item.deliverables?.length > 0 && (
                                <div className="mt-2">
                                  <Label className="text-xs text-zinc-500">Deliverables:</Label>
                                  <ul className="list-disc list-inside text-sm text-zinc-600">
                                    {item.deliverables.map((d, i) => (
                                      <li key={i}>{d}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                            <div className="text-right text-sm">
                              {item.timeline_weeks && (
                                <p className="text-zinc-500">{item.timeline_weeks} weeks</p>
                              )}
                              <Badge className="mt-1" variant={item.status === 'approved' ? 'default' : 'secondary'}>
                                {item.status}
                              </Badge>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-zinc-500">
                      <FileText className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                      No SOW items found
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Agreement Tab */}
              <TabsContent value="agreement" className="space-y-4">
                {detailData.agreement ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Agreement Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-zinc-500 text-xs">Agreement Number</Label>
                          <p className="font-medium">{detailData.agreement.agreement_number}</p>
                        </div>
                        <div>
                          <Label className="text-zinc-500 text-xs">Status</Label>
                          <Badge>{detailData.agreement.status}</Badge>
                        </div>
                        <div>
                          <Label className="text-zinc-500 text-xs">Party Name</Label>
                          <p className="font-medium">{detailData.agreement.party_name || '-'}</p>
                        </div>
                        <div>
                          <Label className="text-zinc-500 text-xs">Project Duration</Label>
                          <p className="font-medium">{detailData.agreement.project_duration_months || detailData.agreement.project_tenure_months || '-'} months</p>
                        </div>
                        <div>
                          <Label className="text-zinc-500 text-xs">Start Date</Label>
                          <p className="font-medium">
                            {detailData.agreement.project_start_date 
                              ? new Date(detailData.agreement.project_start_date).toLocaleDateString()
                              : detailData.agreement.start_date 
                                ? new Date(detailData.agreement.start_date).toLocaleDateString()
                                : '-'}
                          </p>
                        </div>
                        <div>
                          <Label className="text-zinc-500 text-xs">Meeting Frequency</Label>
                          <p className="font-medium">{detailData.agreement.meeting_frequency || 'Monthly'}</p>
                        </div>
                      </div>
                      
                      {detailData.agreement.team_engagement && (
                        <div>
                          <Label className="text-zinc-500 text-xs">Team Engagement</Label>
                          <p className="text-sm mt-1">{detailData.agreement.team_engagement}</p>
                        </div>
                      )}
                      
                      {detailData.agreement.special_conditions && (
                        <div>
                          <Label className="text-zinc-500 text-xs">Special Conditions</Label>
                          <p className="text-sm mt-1">{detailData.agreement.special_conditions}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-zinc-500">
                      <FileText className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                      Agreement details not available
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              No details available
            </div>
          )}

          {/* Action Buttons for PM */}
          {isPMRole && selectedRequest?.status === 'pending' && (
            <DialogFooter className="mt-6 gap-2 sm:gap-0">
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowReturnDialog(true);
                }}
                className="text-orange-600 hover:bg-orange-50"
                data-testid="return-to-sender-btn"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Return to Sender
              </Button>
              <Button 
                onClick={() => handleAccept(selectedRequest.id)}
                className="bg-green-600 hover:bg-green-700"
                data-testid="accept-and-create-btn"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Accept & Create Project
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Date Dialog */}
      <Dialog open={showEditDateDialog} onOpenChange={setShowEditDateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Kickoff Date</DialogTitle>
            <DialogDescription>
              Adjust the expected start date for this project
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Expected Start Date</Label>
              <Input 
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                data-testid="edit-date-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Textarea 
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Add any notes about the date change..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleEditDate} data-testid="save-date-btn">
              <CalendarCheck className="w-4 h-4 mr-2" />
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Return Dialog */}
      <Dialog open={showReturnDialog} onOpenChange={setShowReturnDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Return Request to Sender</DialogTitle>
            <DialogDescription>
              Provide feedback for the sales team to address before resubmitting
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Reason for Return *</Label>
              <Select value={returnReason} onValueChange={setReturnReason}>
                <SelectTrigger data-testid="return-reason-select">
                  <SelectValue placeholder="Select a reason" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="incomplete_sow">Incomplete SOW</SelectItem>
                  <SelectItem value="missing_details">Missing Project Details</SelectItem>
                  <SelectItem value="unrealistic_timeline">Unrealistic Timeline</SelectItem>
                  <SelectItem value="resource_conflict">Resource Conflict</SelectItem>
                  <SelectItem value="team_deployment_unclear">Team Deployment Unclear</SelectItem>
                  <SelectItem value="clarification_needed">Clarification Needed</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Additional Notes</Label>
              <Textarea 
                value={returnNotes}
                onChange={(e) => setReturnNotes(e.target.value)}
                placeholder="Provide specific feedback for the sales team..."
                rows={4}
                data-testid="return-notes-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReturnDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleReturn}
              className="bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-return-btn"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Return Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KickoffRequests;
