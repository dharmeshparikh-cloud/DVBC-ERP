import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  Briefcase, Calendar, Users, Clock, Building2, MapPin,
  AlertCircle, CheckCircle, Eye, Plus, X, Check, DollarSign,
  User, FileText, Target
} from 'lucide-react';
import { toast } from 'sonner';

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low', color: 'bg-zinc-100 text-zinc-700' },
  { value: 'normal', label: 'Normal', color: 'bg-blue-100 text-blue-700' },
  { value: 'high', label: 'High', color: 'bg-amber-100 text-amber-700' },
  { value: 'urgent', label: 'Urgent', color: 'bg-red-100 text-red-700' }
];

const WORK_MODE_OPTIONS = [
  { value: 'office', label: 'Office' },
  { value: 'client_site', label: 'Client Site' },
  { value: 'remote', label: 'Remote' }
];

const STATUS_STYLES = {
  pending_approval: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
  fulfilled: 'bg-blue-100 text-blue-700 border-blue-200'
};

const HRStaffingRequests = () => {
  const { user } = useContext(AuthContext);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  
  const [formData, setFormData] = useState({
    project_name: '',
    purpose: '',
    budget_range: '',
    timeline: '',
    location: '',
    work_mode: 'office',
    skills_required: [],
    experience_years: '',
    headcount: 1,
    priority: 'normal',
    additional_notes: ''
  });
  const [skillInput, setSkillInput] = useState('');

  const isAdmin = user?.role === 'admin';
  const isHR = ['admin', 'hr_manager'].includes(user?.role);

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const response = await axios.get(`${API}/staffing-requests`);
      setRequests(response.data);
    } catch (error) {
      console.error('Failed to fetch staffing requests:', error);
      toast.error('Failed to load staffing requests');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRequest = async (e) => {
    e.preventDefault();
    if (!formData.project_name || !formData.purpose || !formData.timeline || !formData.location) {
      toast.error('Please fill all required fields');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/staffing-requests`, {
        ...formData,
        experience_years: formData.experience_years ? parseInt(formData.experience_years) : null,
        headcount: parseInt(formData.headcount) || 1
      });
      toast.success('Staffing request submitted for Admin approval');
      setShowCreateDialog(false);
      resetForm();
      fetchRequests();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (requestId) => {
    try {
      await axios.post(`${API}/staffing-requests/${requestId}/approve`);
      toast.success('Staffing request approved');
      fetchRequests();
      setShowDetailDialog(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleReject = async (requestId, reason = '') => {
    const rejectReason = window.prompt('Enter rejection reason (optional):');
    try {
      await axios.post(`${API}/staffing-requests/${requestId}/reject?reason=${encodeURIComponent(rejectReason || '')}`);
      toast.success('Staffing request rejected');
      fetchRequests();
      setShowDetailDialog(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const resetForm = () => {
    setFormData({
      project_name: '',
      purpose: '',
      budget_range: '',
      timeline: '',
      location: '',
      work_mode: 'office',
      skills_required: [],
      experience_years: '',
      headcount: 1,
      priority: 'normal',
      additional_notes: ''
    });
    setSkillInput('');
  };

  const addSkill = () => {
    if (skillInput.trim() && !formData.skills_required.includes(skillInput.trim())) {
      setFormData(prev => ({
        ...prev,
        skills_required: [...prev.skills_required, skillInput.trim()]
      }));
      setSkillInput('');
    }
  };

  const removeSkill = (skill) => {
    setFormData(prev => ({
      ...prev,
      skills_required: prev.skills_required.filter(s => s !== skill)
    }));
  };

  const filteredRequests = filterStatus === 'all' 
    ? requests 
    : requests.filter(r => r.status === filterStatus);

  const stats = {
    total: requests.length,
    pending: requests.filter(r => r.status === 'pending_approval').length,
    approved: requests.filter(r => r.status === 'approved').length,
    totalHeadcount: requests.filter(r => r.status === 'approved').reduce((sum, r) => sum + (r.headcount || 1), 0)
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="hr-staffing-requests">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Staffing Requests</h1>
          <p className="text-sm text-zinc-500">
            Submit and track resource staffing requests with Admin approval
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} data-testid="new-staffing-request-btn">
          <Plus className="w-4 h-4 mr-2" /> New Request
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Requests</p>
                <p className="text-2xl font-bold text-zinc-900">{stats.total}</p>
              </div>
              <FileText className="w-8 h-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Pending Approval</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Approved</p>
                <p className="text-2xl font-bold text-emerald-600">{stats.approved}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Headcount</p>
                <p className="text-2xl font-bold text-blue-600">{stats.totalHeadcount}</p>
              </div>
              <Users className="w-8 h-8 text-blue-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {['all', 'pending_approval', 'approved', 'rejected'].map(status => (
          <Button
            key={status}
            variant={filterStatus === status ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterStatus(status)}
          >
            {status === 'all' ? 'All' : status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </Button>
        ))}
      </div>

      {/* Requests List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Staffing Requests ({filteredRequests.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredRequests.length > 0 ? (
            <div className="space-y-3">
              {filteredRequests.map(request => (
                <div
                  key={request.id}
                  className="flex items-center justify-between p-4 border border-zinc-200 rounded-lg hover:bg-zinc-50 cursor-pointer"
                  onClick={() => { setSelectedRequest(request); setShowDetailDialog(true); }}
                  data-testid={`staffing-request-${request.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      request.priority === 'urgent' ? 'bg-red-100' :
                      request.priority === 'high' ? 'bg-amber-100' : 'bg-blue-100'
                    }`}>
                      <Briefcase className={`w-5 h-5 ${
                        request.priority === 'urgent' ? 'text-red-600' :
                        request.priority === 'high' ? 'text-amber-600' : 'text-blue-600'
                      }`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-zinc-900">{request.project_name}</h3>
                        <Badge className={STATUS_STYLES[request.status] || 'bg-zinc-100'}>
                          {request.status?.replace('_', ' ')}
                        </Badge>
                      </div>
                      <p className="text-sm text-zinc-500">
                        By: {request.requester_name} ({request.requester_employee_id || 'N/A'}) • {request.headcount} resource(s)
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-zinc-400">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" /> {request.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {request.timeline}
                        </span>
                        {request.budget_range && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3" /> {request.budget_range}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={PRIORITY_OPTIONS.find(p => p.value === request.priority)?.color}>
                      {request.priority}
                    </Badge>
                    <Button variant="ghost" size="sm">
                      <Eye className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-zinc-500">
              <Briefcase className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
              <p className="text-lg font-medium">No Staffing Requests</p>
              <p className="text-sm mt-1">Click "New Request" to create one</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New Staffing Request</DialogTitle>
            <DialogDescription>
              Submit a request for additional resources. Requires Admin approval.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleCreateRequest} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Project Name *</Label>
                <Input
                  value={formData.project_name}
                  onChange={e => setFormData(prev => ({ ...prev, project_name: e.target.value }))}
                  placeholder="Enter project name"
                  data-testid="staffing-project-name"
                  required
                />
              </div>
              
              <div className="col-span-2">
                <Label>Purpose / Justification *</Label>
                <textarea
                  className="w-full min-h-[80px] px-3 py-2 rounded-md border border-zinc-300 text-sm"
                  value={formData.purpose}
                  onChange={e => setFormData(prev => ({ ...prev, purpose: e.target.value }))}
                  placeholder="Why is this resource needed?"
                  data-testid="staffing-purpose"
                  required
                />
              </div>
              
              <div>
                <Label>Budget Range</Label>
                <Input
                  value={formData.budget_range}
                  onChange={e => setFormData(prev => ({ ...prev, budget_range: e.target.value }))}
                  placeholder="e.g., 5-8 LPA"
                  data-testid="staffing-budget"
                />
              </div>
              
              <div>
                <Label>Timeline / Start Date *</Label>
                <Input
                  type="date"
                  value={formData.timeline}
                  onChange={e => setFormData(prev => ({ ...prev, timeline: e.target.value }))}
                  data-testid="staffing-timeline"
                  required
                />
              </div>
              
              <div>
                <Label>Location *</Label>
                <Input
                  value={formData.location}
                  onChange={e => setFormData(prev => ({ ...prev, location: e.target.value }))}
                  placeholder="e.g., Mumbai, Bangalore"
                  data-testid="staffing-location"
                  required
                />
              </div>
              
              <div>
                <Label>Work Mode</Label>
                <select
                  className="w-full h-10 px-3 rounded-md border border-zinc-300 text-sm"
                  value={formData.work_mode}
                  onChange={e => setFormData(prev => ({ ...prev, work_mode: e.target.value }))}
                  data-testid="staffing-work-mode"
                >
                  {WORK_MODE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <Label>Experience (Years)</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.experience_years}
                  onChange={e => setFormData(prev => ({ ...prev, experience_years: e.target.value }))}
                  placeholder="e.g., 3"
                  data-testid="staffing-experience"
                />
              </div>
              
              <div>
                <Label>Headcount *</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.headcount}
                  onChange={e => setFormData(prev => ({ ...prev, headcount: e.target.value }))}
                  data-testid="staffing-headcount"
                  required
                />
              </div>
              
              <div>
                <Label>Priority</Label>
                <select
                  className="w-full h-10 px-3 rounded-md border border-zinc-300 text-sm"
                  value={formData.priority}
                  onChange={e => setFormData(prev => ({ ...prev, priority: e.target.value }))}
                  data-testid="staffing-priority"
                >
                  {PRIORITY_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              
              <div className="col-span-2">
                <Label>Required Skills</Label>
                <div className="flex gap-2">
                  <Input
                    value={skillInput}
                    onChange={e => setSkillInput(e.target.value)}
                    placeholder="Add skill and press Enter"
                    onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addSkill())}
                    data-testid="staffing-skill-input"
                  />
                  <Button type="button" variant="outline" onClick={addSkill}>Add</Button>
                </div>
                {formData.skills_required.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.skills_required.map(skill => (
                      <Badge key={skill} variant="secondary" className="flex items-center gap-1">
                        {skill}
                        <X className="w-3 h-3 cursor-pointer" onClick={() => removeSkill(skill)} />
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="col-span-2">
                <Label>Additional Notes</Label>
                <textarea
                  className="w-full min-h-[60px] px-3 py-2 rounded-md border border-zinc-300 text-sm"
                  value={formData.additional_notes}
                  onChange={e => setFormData(prev => ({ ...prev, additional_notes: e.target.value }))}
                  placeholder="Any additional information..."
                  data-testid="staffing-notes"
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting} data-testid="submit-staffing-request">
                {submitting ? 'Submitting...' : 'Submit Request'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Staffing Request Details</DialogTitle>
          </DialogHeader>
          
          {selectedRequest && (
            <div className="space-y-4">
              {/* Requester Info */}
              <div className="p-4 bg-zinc-50 rounded-lg">
                <h4 className="text-sm font-medium text-zinc-500 mb-2">Requester Information</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-zinc-400">Name</p>
                    <p className="font-medium">{selectedRequest.requester_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Employee ID</p>
                    <p className="font-medium">{selectedRequest.requester_employee_id || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Email</p>
                    <p className="font-medium">{selectedRequest.requester_email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-400">Reporting Manager</p>
                    <p className="font-medium">{selectedRequest.reporting_manager || 'N/A'}</p>
                  </div>
                </div>
              </div>
              
              {/* Request Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-zinc-400">Project Name</p>
                  <p className="font-medium">{selectedRequest.project_name}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Status</p>
                  <Badge className={STATUS_STYLES[selectedRequest.status]}>
                    {selectedRequest.status?.replace('_', ' ')}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Budget Range</p>
                  <p className="font-medium">{selectedRequest.budget_range || 'Not specified'}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Timeline</p>
                  <p className="font-medium">{selectedRequest.timeline}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Location</p>
                  <p className="font-medium">{selectedRequest.location}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Work Mode</p>
                  <p className="font-medium capitalize">{selectedRequest.work_mode?.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Experience Required</p>
                  <p className="font-medium">{selectedRequest.experience_years ? `${selectedRequest.experience_years} years` : 'Any'}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-400">Headcount</p>
                  <p className="font-medium">{selectedRequest.headcount} resource(s)</p>
                </div>
              </div>
              
              <div>
                <p className="text-xs text-zinc-400 mb-1">Purpose / Justification</p>
                <p className="text-sm bg-zinc-50 p-3 rounded">{selectedRequest.purpose}</p>
              </div>
              
              {selectedRequest.skills_required?.length > 0 && (
                <div>
                  <p className="text-xs text-zinc-400 mb-2">Required Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedRequest.skills_required.map(skill => (
                      <Badge key={skill} variant="outline">{skill}</Badge>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedRequest.additional_notes && (
                <div>
                  <p className="text-xs text-zinc-400 mb-1">Additional Notes</p>
                  <p className="text-sm text-zinc-600">{selectedRequest.additional_notes}</p>
                </div>
              )}
              
              {/* Admin Actions */}
              {isAdmin && selectedRequest.status === 'pending_approval' && (
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button 
                    variant="outline" 
                    className="text-red-600 border-red-200 hover:bg-red-50"
                    onClick={() => handleReject(selectedRequest.id)}
                    data-testid="reject-staffing-btn"
                  >
                    <X className="w-4 h-4 mr-1" /> Reject
                  </Button>
                  <Button 
                    className="bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleApprove(selectedRequest.id)}
                    data-testid="approve-staffing-btn"
                  >
                    <Check className="w-4 h-4 mr-1" /> Approve
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

export default HRStaffingRequests;
