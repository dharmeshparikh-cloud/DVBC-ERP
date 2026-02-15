import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Send, Inbox, CheckCircle, XCircle, Clock, Plus,
  Building2, Calendar, DollarSign, Users, ArrowRight
} from 'lucide-react';

const KickoffRequests = () => {
  const { user } = useContext(AuthContext);
  const [requests, setRequests] = useState([]);
  const [agreements, setAgreements] = useState([]);
  const [projectManagers, setProjectManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState({
    agreement_id: '',
    client_name: '',
    project_name: '',
    project_type: 'mixed',
    total_meetings: 0,
    project_value: '',
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
      const response = await fetch(`${API}/api/kickoff-requests`, {
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
      const response = await fetch(`${API}/api/agreements?status=approved`, {
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
      const response = await fetch(`${API}/api/users?role=project_manager`, {
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

  const handleAgreementSelect = (agreementId) => {
    const agreement = agreements.find(a => a.id === agreementId);
    if (agreement) {
      setFormData(prev => ({
        ...prev,
        agreement_id: agreementId,
        client_name: agreement.client_name || '',
        project_name: `${agreement.client_name || 'Client'} - Project`,
        project_value: agreement.total_value || ''
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
        project_value: parseFloat(formData.project_value) || null,
        expected_start_date: formData.expected_start_date ? new Date(formData.expected_start_date).toISOString() : null
      };

      const response = await fetch(`${API}/api/kickoff-requests`, {
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
          project_type: 'mixed', total_meetings: 0, project_value: '',
          expected_start_date: '', assigned_pm_id: '', assigned_pm_name: '', notes: ''
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

  const handleAccept = async (requestId) => {
    try {
      const response = await fetch(`${API}/api/kickoff-requests/${requestId}/accept`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        toast.success('Project created successfully');
        fetchRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to accept request');
      }
    } catch (error) {
      toast.error('Failed to accept request');
    }
  };

  const handleReject = async (requestId) => {
    try {
      const response = await fetch(`${API}/api/kickoff-requests/${requestId}/reject`, {
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
      rejected: 'bg-red-100 text-red-700'
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
  const processedRequests = requests.filter(r => r.status !== 'pending');

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
        {isSalesRole && (
          <Button onClick={() => setShowCreateDialog(true)} data-testid="create-kickoff-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Kickoff Request
          </Button>
        )}
      </div>

      {/* Pending Requests */}
      {pendingRequests.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Inbox className="w-5 h-5" />
            Pending Requests ({pendingRequests.length})
          </h2>
          <div className="grid gap-4">
            {pendingRequests.map((request) => (
              <Card key={request.id} className="border-amber-200 bg-amber-50/50">
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
                          <span>{request.total_meetings || 0} meetings</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <DollarSign className="w-4 h-4 text-zinc-400" />
                          <span>₹{((request.project_value || 0) / 100000).toFixed(1)}L</span>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-500 mt-2">
                        Requested by: {request.requested_by_name || 'Unknown'} • 
                        {new Date(request.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {isPMRole && (
                      <div className="flex gap-2 ml-4">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handleReject(request.id)}
                          className="text-red-600 hover:bg-red-50"
                        >
                          <XCircle className="w-4 h-4 mr-1" />
                          Reject
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={() => handleAccept(request.id)}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Accept & Create Project
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Processed Requests */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Clock className="w-5 h-5" />
          History
        </h2>
        {processedRequests.length === 0 ? (
          <Card className="border-zinc-200">
            <CardContent className="py-8 text-center text-zinc-500">
              No processed requests yet
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {processedRequests.map((request) => (
              <Card key={request.id} className="border-zinc-200">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-zinc-900">{request.project_name}</h3>
                        {getStatusBadge(request.status)}
                      </div>
                      <p className="text-sm text-zinc-500 mt-1">
                        {request.client_name} • {new Date(request.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {request.status === 'converted' && request.project_id && (
                      <Button variant="outline" size="sm" asChild>
                        <a href={`/projects`}>
                          View Project <ArrowRight className="w-4 h-4 ml-1" />
                        </a>
                      </Button>
                    )}
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
                      {agreement.client_name || agreement.id} - {agreement.title || 'Agreement'}
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
                <Label>Total Meetings</Label>
                <Input 
                  type="number"
                  value={formData.total_meetings}
                  onChange={(e) => setFormData({...formData, total_meetings: e.target.value})}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Project Value (₹)</Label>
                <Input 
                  type="number"
                  value={formData.project_value}
                  onChange={(e) => setFormData({...formData, project_value: e.target.value})}
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
    </div>
  );
};

export default KickoffRequests;
