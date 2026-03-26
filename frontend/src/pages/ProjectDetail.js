/**
 * ProjectDetail.js - Project Detail Page with SOW as Primary View
 * 
 * This page serves as the main project view, defaulting to showing:
 * - SOW Delivery (Primary)
 * - Project Tasks
 * - Project Info
 * - Reschedule Requests
 * 
 * The user's request: Clicking project card should open SOW
 */

import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import PageHeader from '../components/ui/page-header';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  ArrowLeft, Calendar, Clock, Building2, IndianRupee,
  FileText, ListTodo, Users, CheckCircle2, AlertTriangle,
  CalendarClock, Send, Loader2, RefreshCcw, CheckCircle, XCircle
} from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
import { toast } from 'sonner';
import ProjectSOWDelivery from '../components/ProjectSOWDelivery';

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, token } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('sow'); // Default to SOW
  const [showRescheduleDialog, setShowRescheduleDialog] = useState(false);
  const [rescheduleForm, setRescheduleForm] = useState({
    reason: '',
    preferred_date: '',
    preferred_time: '',
    notes: ''
  });

  const headers = { Authorization: `Bearer ${token}` };

  // Fetch Project
  const { data: project, isLoading, refetch } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects/${projectId}`);
      return res.data;
    },
    staleTime: 3 * 60 * 1000,
  });

  // Fetch Reschedule Requests
  const { data: rescheduleRequests = [], refetch: refetchReschedule } = useQuery({
    queryKey: ['reschedule-requests', projectId],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects/${projectId}/reschedule-requests`, { headers });
      return res.data;
    },
    staleTime: 60 * 1000,
  });

  // Create reschedule request mutation
  const createRescheduleMutation = useMutation({
    mutationFn: async (data) => {
      const params = new URLSearchParams();
      params.append('reason', data.reason);
      if (data.preferred_date) params.append('preferred_date', data.preferred_date);
      if (data.preferred_time) params.append('preferred_time', data.preferred_time);
      if (data.notes) params.append('notes', data.notes);
      
      return axios.post(`${API}/projects/${projectId}/reschedule-requests?${params.toString()}`, {}, { headers });
    },
    onSuccess: () => {
      toast.success('Reschedule request submitted');
      setShowRescheduleDialog(false);
      setRescheduleForm({ reason: '', preferred_date: '', preferred_time: '', notes: '' });
      refetchReschedule();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  });

  const handleSubmitReschedule = () => {
    if (!rescheduleForm.reason) {
      toast.error('Please provide a reason for reschedule');
      return;
    }
    createRescheduleMutation.mutate(rescheduleForm);
  };

  // Check if user can request reschedule (consulting roles)
  const canRequestReschedule = ['principal_consultant', 'project_manager', 'senior_consultant', 'consultant', 'admin'].includes(user?.role);

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Active' },
      at_risk: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'At Risk' },
      delayed: { bg: 'bg-red-50', text: 'text-red-700', label: 'Delayed' },
      completed: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Completed' },
      on_hold: { bg: 'bg-zinc-100', text: 'text-zinc-600', label: 'On Hold' },
      cancelled: { bg: 'bg-zinc-100', text: 'text-zinc-500', label: 'Cancelled' }
    };
    return statusConfig[status?.toLowerCase()] || { bg: 'bg-zinc-100', text: 'text-zinc-600', label: status || 'Unknown' };
  };

  const getTimelineInfo = () => {
    if (!project?.end_date) return null;
    const endDate = new Date(project.end_date);
    const today = new Date();
    const daysRemaining = differenceInDays(endDate, today);
    return {
      daysRemaining,
      isOverdue: daysRemaining < 0,
      isAtRisk: daysRemaining >= 0 && daysRemaining <= 30
    };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading project...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <p className="text-zinc-500 mb-4">Project not found</p>
        <Button onClick={() => navigate('/projects')} variant="outline">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Projects
        </Button>
      </div>
    );
  }

  const timeline = getTimelineInfo();
  const statusBadge = getStatusBadge(project.status);

  return (
    <div data-testid="project-detail-page" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Button
            onClick={() => navigate('/projects')}
            variant="ghost"
            className="mb-2 -ml-3 hover:bg-zinc-100 rounded-sm text-zinc-500"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back to Projects
          </Button>
          <h1 className="text-2xl font-bold text-zinc-950" data-testid="project-title">
            {project.client_name || project.name}
          </h1>
          <p className="text-zinc-500 mt-1">
            {project.name || project.project_name}
          </p>
        </div>
        <Badge className={`${statusBadge.bg} ${statusBadge.text} px-3 py-1`}>
          {statusBadge.label}
        </Badge>
      </div>

      {/* Project Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Calendar className="w-3.5 h-3.5" />
              Start Date
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.start_date ? format(new Date(project.start_date), 'MMM dd, yyyy') : 'Not Set'}
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Clock className="w-3.5 h-3.5" />
              End Date
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.end_date ? format(new Date(project.end_date), 'MMM dd, yyyy') : 'Not Set'}
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Users className="w-3.5 h-3.5" />
              Meetings
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.total_meetings_delivered || 0} / {project.total_meetings_committed || 0}
            </div>
          </CardContent>
        </Card>
        
        <Card className={`shadow-none ${timeline?.isOverdue ? 'border-red-200 bg-red-50' : timeline?.isAtRisk ? 'border-amber-200 bg-amber-50' : 'border-zinc-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              {timeline?.isOverdue ? (
                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              ) : timeline?.isAtRisk ? (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              Timeline
            </div>
            <div className={`text-sm font-semibold ${timeline?.isOverdue ? 'text-red-700' : timeline?.isAtRisk ? 'text-amber-700' : 'text-zinc-950'}`}>
              {timeline 
                ? timeline.isOverdue 
                  ? `${Math.abs(timeline.daysRemaining)} days overdue`
                  : `${timeline.daysRemaining} days remaining`
                : 'No end date'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-zinc-100 p-1">
          <TabsTrigger value="sow" className="text-sm data-[state=active]:bg-white" data-testid="sow-tab">
            <FileText className="w-4 h-4 mr-2" />
            SOW Delivery
          </TabsTrigger>
          <TabsTrigger value="tasks" className="text-sm data-[state=active]:bg-white" data-testid="tasks-tab">
            <ListTodo className="w-4 h-4 mr-2" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="reschedule" className="text-sm data-[state=active]:bg-white" data-testid="reschedule-tab">
            <CalendarClock className="w-4 h-4 mr-2" />
            Reschedule
            {rescheduleRequests.filter(r => r.status === 'pending').length > 0 && (
              <Badge variant="destructive" className="ml-2 px-1.5 py-0 text-[10px]">
                {rescheduleRequests.filter(r => r.status === 'pending').length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="info" className="text-sm data-[state=active]:bg-white" data-testid="info-tab">
            <Building2 className="w-4 h-4 mr-2" />
            Project Info
          </TabsTrigger>
        </TabsList>

        {/* SOW Delivery Tab - Default */}
        <TabsContent value="sow" className="mt-0">
          <ProjectSOWDelivery projectId={projectId} />
        </TabsContent>

        {/* Tasks Tab - Link to full Tasks page */}
        <TabsContent value="tasks" className="mt-0">
          <Card className="border-zinc-200 shadow-none">
            <CardContent className="py-12 text-center">
              <ListTodo className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-zinc-700 mb-2">Project Tasks</h3>
              <p className="text-zinc-500 mb-6">View and manage all tasks for this project</p>
              <Button
                onClick={() => navigate(`/projects/${projectId}/tasks`)}
                className="bg-zinc-950 text-white hover:bg-zinc-800"
                data-testid="view-tasks-btn"
              >
                <ListTodo className="w-4 h-4 mr-2" />
                View Full Tasks Page
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reschedule Requests Tab */}
        <TabsContent value="reschedule" className="mt-0">
          <Card className="border-zinc-200 shadow-none">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Reschedule Requests</CardTitle>
              {canRequestReschedule && (
                <Button 
                  onClick={() => setShowRescheduleDialog(true)}
                  className="bg-amber-600 hover:bg-amber-700"
                  data-testid="request-reschedule-btn"
                >
                  <CalendarClock className="w-4 h-4 mr-2" />
                  Request Reschedule
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {rescheduleRequests.length === 0 ? (
                <div className="text-center py-12">
                  <CalendarClock className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
                  <p className="text-zinc-500">No reschedule requests yet</p>
                  {canRequestReschedule && (
                    <p className="text-zinc-400 text-sm mt-2">
                      Click "Request Reschedule" to submit a new request
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {rescheduleRequests.map((req) => (
                    <div 
                      key={req.id} 
                      className={`p-4 rounded-lg border ${
                        req.status === 'pending' ? 'border-amber-200 bg-amber-50' :
                        req.status === 'approved' ? 'border-emerald-200 bg-emerald-50' :
                        'border-red-200 bg-red-50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            {req.status === 'pending' ? (
                              <Clock className="w-4 h-4 text-amber-600" />
                            ) : req.status === 'approved' ? (
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-600" />
                            )}
                            <Badge className={
                              req.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                              req.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                              'bg-red-100 text-red-700'
                            }>
                              {req.status?.charAt(0).toUpperCase() + req.status?.slice(1)}
                            </Badge>
                            <span className="text-xs text-zinc-500">
                              {req.requested_at ? format(new Date(req.requested_at), 'dd MMM yyyy HH:mm') : ''}
                            </span>
                          </div>
                          <p className="font-medium text-zinc-800">{req.reason}</p>
                          {req.preferred_date && (
                            <p className="text-sm text-zinc-600 mt-1">
                              Preferred: {req.preferred_date} {req.preferred_time && `at ${req.preferred_time}`}
                            </p>
                          )}
                          {req.notes && (
                            <p className="text-sm text-zinc-500 mt-1">{req.notes}</p>
                          )}
                          <p className="text-xs text-zinc-400 mt-2">
                            Requested by: {req.requested_by_name}
                          </p>
                        </div>
                      </div>
                      {req.status !== 'pending' && req.response_notes && (
                        <div className="mt-3 pt-3 border-t border-zinc-200">
                          <p className="text-sm text-zinc-600">
                            <strong>Response:</strong> {req.response_notes}
                          </p>
                          <p className="text-xs text-zinc-400 mt-1">
                            Responded by: {req.responded_by_name} on {req.responded_at ? format(new Date(req.responded_at), 'dd MMM yyyy') : ''}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Project Info Tab */}
        <TabsContent value="info" className="mt-0">
          <Card className="border-zinc-200 shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Project Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Client Name</label>
                  <p className="text-sm font-medium text-zinc-950">{project.client_name || '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Project Name</label>
                  <p className="text-sm font-medium text-zinc-950">{project.name || project.project_name || '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Project ID</label>
                  <p className="text-sm font-mono text-zinc-600">{project.id}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Status</label>
                  <Badge className={`${statusBadge.bg} ${statusBadge.text} mt-1`}>{statusBadge.label}</Badge>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Tenure</label>
                  <p className="text-sm font-medium text-zinc-950">{project.tenure_months ? `${project.tenure_months} months` : '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Budget</label>
                  <p className="text-sm font-medium text-zinc-950">
                    {project.budget ? `₹${project.budget.toLocaleString('en-IN')}` : '-'}
                  </p>
                </div>
              </div>
              
              {project.notes && (
                <div className="pt-4 border-t border-zinc-200">
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Notes</label>
                  <p className="text-sm text-zinc-700 mt-1">{project.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Reschedule Request Dialog */}
      <Dialog open={showRescheduleDialog} onOpenChange={setShowRescheduleDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-amber-600" />
              Request Reschedule
            </DialogTitle>
            <DialogDescription>
              Submit a reschedule request for this project. Sales team will be notified.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="reason">Reason for Reschedule *</Label>
              <Select
                value={rescheduleForm.reason}
                onValueChange={(val) => setRescheduleForm({ ...rescheduleForm, reason: val })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select reason" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Client unavailable">Client unavailable</SelectItem>
                  <SelectItem value="Resource conflict">Resource conflict</SelectItem>
                  <SelectItem value="Scope change needed">Scope change needed</SelectItem>
                  <SelectItem value="Technical dependencies">Technical dependencies</SelectItem>
                  <SelectItem value="Client requested delay">Client requested delay</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="preferred_date">Preferred Date</Label>
                <Input
                  id="preferred_date"
                  type="date"
                  value={rescheduleForm.preferred_date}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, preferred_date: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="preferred_time">Preferred Time</Label>
                <Input
                  id="preferred_time"
                  type="time"
                  value={rescheduleForm.preferred_time}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, preferred_time: e.target.value })}
                  className="mt-1"
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="notes">Additional Notes</Label>
              <Textarea
                id="notes"
                value={rescheduleForm.notes}
                onChange={(e) => setRescheduleForm({ ...rescheduleForm, notes: e.target.value })}
                placeholder="Any additional context or requirements..."
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRescheduleDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitReschedule}
              disabled={createRescheduleMutation.isPending || !rescheduleForm.reason}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {createRescheduleMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit Request
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectDetail;
