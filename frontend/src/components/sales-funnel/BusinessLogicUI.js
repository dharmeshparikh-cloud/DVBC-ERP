/**
 * Sales Funnel Business Logic UI Components
 * 
 * Components:
 * 1. StageResumeBar - "Continue from where you left off" banner for leads
 * 2. KickoffRequestPanel - Admin approval for kickoff requests to consulting team
 * 3. ConsultantSelector - Select senior_consultant/principal_consultant for kickoff
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { API } from '../../App';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { toast } from 'sonner';
import { 
  Play, ArrowRight, Clock, CheckCircle2, XCircle, 
  Send, Shield, Users, Loader2, RefreshCw, Rocket,
  UserCheck, AlertTriangle
} from 'lucide-react';

// ============== 1. STAGE RESUME BAR ==============

export const StageResumeBar = ({ leadId, onResume }) => {
  const navigate = useNavigate();
  const [stageStatus, setStageStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resuming, setResuming] = useState(false);

  const fetchStageStatus = useCallback(async () => {
    if (!leadId) {
      setLoading(false);
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/stage-status/${leadId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStageStatus(data);
      }
    } catch (error) {
      console.error('Error fetching stage status:', error);
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => {
    fetchStageStatus();
  }, [fetchStageStatus]);

  const handleResume = async () => {
    setResuming(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/resume-stage`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ lead_id: leadId })
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success('Resuming from last stage');
        
        // Navigate to the appropriate page based on stage
        const stageRoutes = {
          'lead': `/leads/${leadId}`,
          'meeting': `/sales-funnel/meetings?leadId=${leadId}`,
          'pricing': `/sales-funnel/pricing-plans?leadId=${leadId}`,
          'quotation': `/sales-funnel/quotations?leadId=${leadId}`,
          'sow': `/sales-funnel/sow/${leadId}`,
          'agreement': `/sales-funnel/agreements?leadId=${leadId}`,
          'payment': `/sales-funnel/payments?leadId=${leadId}`,
          'kickoff': `/sales-funnel/kickoff?leadId=${leadId}`
        };
        
        if (onResume) {
          onResume(data);
        } else if (stageRoutes[data.current_stage]) {
          navigate(stageRoutes[data.current_stage]);
        }
      }
    } catch (error) {
      toast.error('Failed to resume stage');
    } finally {
      setResuming(false);
    }
  };

  if (loading || !stageStatus) return null;
  
  // Don't show if at first stage or completed
  if (stageStatus.current_stage === 'lead' || stageStatus.current_stage === 'complete') {
    return null;
  }

  const stageLabels = {
    'lead': 'Lead Entry',
    'meeting': 'Meeting',
    'pricing': 'Pricing Plan',
    'quotation': 'Quotation',
    'sow': 'Statement of Work',
    'agreement': 'Agreement',
    'payment': 'Payment',
    'kickoff': 'Kickoff',
    'complete': 'Completed'
  };

  const currentStageLabel = stageLabels[stageStatus.current_stage] || stageStatus.current_stage;
  const nextStageLabel = stageLabels[stageStatus.next_stage] || stageStatus.next_stage;

  return (
    <Alert className="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800" data-testid="stage-resume-bar">
      <Play className="h-4 w-4 text-blue-600" />
      <AlertTitle className="text-blue-800 dark:text-blue-200">Continue where you left off</AlertTitle>
      <AlertDescription className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-2">
        <div className="flex items-center gap-2 text-sm">
          <Badge variant="outline" className="bg-white dark:bg-gray-800">
            {currentStageLabel}
          </Badge>
          <ArrowRight className="h-4 w-4 text-gray-400" />
          <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-800 dark:text-blue-200">
            {nextStageLabel}
          </Badge>
          {stageStatus.completion_percentage && (
            <span className="text-gray-500 ml-2">
              ({stageStatus.completion_percentage}% complete)
            </span>
          )}
        </div>
        <Button
          size="sm"
          onClick={handleResume}
          disabled={resuming}
          className="bg-blue-600 hover:bg-blue-700"
          data-testid="resume-stage-btn"
        >
          {resuming ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-2" />
          )}
          Resume
        </Button>
      </AlertDescription>
    </Alert>
  );
};

// ============== 2. KICKOFF REQUEST PANEL ==============
// Admin approval required when sending kickoff to consulting team

export const KickoffRequestPanel = ({ 
  leadId,
  agreementId,
  onKickoffCreated,
  isAdmin = false
}) => {
  const [consultants, setConsultants] = useState([]);
  const [selectedConsultant, setSelectedConsultant] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [showDialog, setShowDialog] = useState(false);

  // Fetch Senior Consultants and Principal Consultants only
  const fetchConsultants = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/consulting-team`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setConsultants(data.consultants || []);
      }
    } catch (error) {
      console.error('Error fetching consultants:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch pending kickoff requests (for admin)
  const fetchPendingRequests = useCallback(async () => {
    if (!isAdmin) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/pending-kickoff-approvals`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPendingRequests(data.requests || []);
      }
    } catch (error) {
      console.error('Error fetching pending requests:', error);
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchConsultants();
    fetchPendingRequests();
  }, [fetchConsultants, fetchPendingRequests]);

  const handleSubmitKickoff = async () => {
    if (!selectedConsultant) {
      toast.error('Please select a consultant');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/request-kickoff`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          lead_id: leadId,
          agreement_id: agreementId,
          assigned_consultant_id: selectedConsultant,
          notes: notes
        })
      });
      
      if (response.ok) {
        toast.success('Kickoff request submitted for admin approval');
        setShowDialog(false);
        setSelectedConsultant('');
        setNotes('');
        onKickoffCreated?.();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit');
      }
    } catch (error) {
      toast.error('Failed to submit kickoff request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveKickoff = async (requestId) => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/approve-kickoff/${requestId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Kickoff request approved');
        fetchPendingRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to approve');
      }
    } catch (error) {
      toast.error('Failed to approve');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectKickoff = async (requestId) => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/reject-kickoff/${requestId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Kickoff request rejected');
        fetchPendingRequests();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to reject');
      }
    } catch (error) {
      toast.error('Failed to reject');
    } finally {
      setSubmitting(false);
    }
  };

  const getRoleLabel = (role) => {
    const labels = {
      'senior_consultant': 'Senior Consultant',
      'principal_consultant': 'Principal Consultant'
    };
    return labels[role] || role;
  };

  // Admin view - show pending approvals
  if (isAdmin && pendingRequests.length > 0) {
    return (
      <Card data-testid="kickoff-approval-panel">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-orange-600" />
            Pending Kickoff Approvals
          </CardTitle>
          <CardDescription>
            Review and approve kickoff requests to consulting team
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {pendingRequests.map((req) => (
            <div key={req.id} className="p-3 border rounded-lg bg-orange-50 dark:bg-orange-900/20">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{req.lead_company || 'Lead'}</p>
                  <p className="text-sm text-gray-600">
                    Assign to: <span className="font-medium">{req.consultant_name}</span>
                    <Badge className="ml-2" variant="outline">{getRoleLabel(req.consultant_role)}</Badge>
                  </p>
                  {req.notes && (
                    <p className="text-sm text-gray-500 mt-1">{req.notes}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Requested by {req.requested_by_name} • {new Date(req.requested_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRejectKickoff(req.id)}
                    disabled={submitting}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    <XCircle className="h-4 w-4 mr-1" />
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleApproveKickoff(req.id)}
                    disabled={submitting}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                    Approve
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  // Sales user view - create kickoff request
  return (
    <>
      <Button
        onClick={() => setShowDialog(true)}
        className="bg-purple-600 hover:bg-purple-700"
        data-testid="create-kickoff-btn"
      >
        <Rocket className="h-4 w-4 mr-2" />
        Create Kickoff Request
      </Button>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Rocket className="h-5 w-5 text-purple-600" />
              Create Kickoff Request
            </DialogTitle>
            <DialogDescription>
              Select a consultant from the consulting team. Admin approval is required.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Alert className="bg-amber-50 border-amber-200">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-amber-800">
                This request requires Admin approval before the kickoff meeting is scheduled.
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label>Assign to Consultant *</Label>
              <Select value={selectedConsultant} onValueChange={setSelectedConsultant}>
                <SelectTrigger data-testid="consultant-selector">
                  <SelectValue placeholder={loading ? "Loading..." : "Select consultant"} />
                </SelectTrigger>
                <SelectContent>
                  {consultants.map((consultant) => (
                    <SelectItem key={consultant.id} value={consultant.id}>
                      <div className="flex items-center gap-2">
                        <UserCheck className="h-4 w-4 text-purple-500" />
                        <span>{consultant.full_name}</span>
                        <Badge variant="outline" className="ml-2 text-xs">
                          {getRoleLabel(consultant.role)}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {consultants.length === 0 && !loading && (
                <p className="text-sm text-red-500">No Senior/Principal Consultants available</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any notes for the kickoff meeting..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitKickoff} 
              disabled={submitting || !selectedConsultant}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Submit for Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

// ============== EXPORTS ==============

export default {
  StageResumeBar,
  KickoffRequestPanel
};
