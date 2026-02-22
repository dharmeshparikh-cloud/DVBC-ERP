/**
 * Sales Funnel Business Logic UI Components
 * 
 * Three integrated components:
 * 1. StageResumeBar - "Continue from where you left off" banner
 * 2. DualApprovalPanel - Submit and track dual/multi approvals for pricing
 * 3. ClientConsentPanel - Send and track client consent for agreements
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { API } from '../../App';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Input } from '../ui/input';
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
  DialogTrigger,
} from '../ui/dialog';
import { toast } from 'sonner';
import { 
  Play, ArrowRight, Clock, CheckCircle2, XCircle, AlertTriangle,
  Send, Mail, Shield, Users, FileCheck, Loader2, RefreshCw,
  ThumbsUp, ThumbsDown, Eye, ExternalLink
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
    <Alert className="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
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

// ============== 2. DUAL APPROVAL PANEL ==============

export const DualApprovalPanel = ({ 
  entityType, // 'pricing' or 'sow'
  entityId, 
  onApprovalComplete,
  compact = false 
}) => {
  const [approvalStatus, setApprovalStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');

  const fetchApprovalStatus = useCallback(async () => {
    if (!entityId) {
      setLoading(false);
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${API}/sales-funnel/approval-status?entity_type=${entityType}&entity_id=${entityId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        setApprovalStatus(data);
      }
    } catch (error) {
      console.error('Error fetching approval status:', error);
    } finally {
      setLoading(false);
    }
  }, [entityType, entityId]);

  useEffect(() => {
    fetchApprovalStatus();
  }, [fetchApprovalStatus]);

  const handleSubmitForApproval = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/request-approval`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityId,
          approval_notes: approvalNotes
        })
      });
      
      if (response.ok) {
        toast.success('Submitted for approval');
        setShowSubmitDialog(false);
        fetchApprovalStatus();
        onApprovalComplete?.();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit');
      }
    } catch (error) {
      toast.error('Failed to submit for approval');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/submit-approval`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityId,
          decision: 'approved',
          comments: approvalNotes
        })
      });
      
      if (response.ok) {
        toast.success('Approval submitted');
        fetchApprovalStatus();
        onApprovalComplete?.();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to approve');
      }
    } catch (error) {
      toast.error('Failed to submit approval');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading approval status...
      </div>
    );
  }

  // Compact view for inline display
  if (compact) {
    return (
      <div className="flex items-center gap-2" data-testid="dual-approval-compact">
        {!approvalStatus?.submitted ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowSubmitDialog(true)}
            className="gap-1"
          >
            <Shield className="h-3 w-3" />
            Submit for Approval
          </Button>
        ) : approvalStatus?.status === 'pending' ? (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
            <Clock className="h-3 w-3 mr-1" />
            {approvalStatus.approvals_received}/{approvalStatus.approvals_required} Approvals
          </Badge>
        ) : approvalStatus?.status === 'approved' ? (
          <Badge className="bg-green-100 text-green-700">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Approved
          </Badge>
        ) : (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Rejected
          </Badge>
        )}

        {/* Submit Dialog */}
        <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Submit for Dual Approval</DialogTitle>
              <DialogDescription>
                This {entityType} requires approval from 2 authorized personnel before proceeding.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Notes (Optional)</Label>
                <Textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="Add any notes for the approvers..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmitForApproval} disabled={submitting}>
                {submitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Submit
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Full panel view
  return (
    <Card data-testid="dual-approval-panel">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-600" />
          Dual Approval Required
        </CardTitle>
        <CardDescription>
          {entityType === 'pricing' ? 'Pricing plans' : 'Statements of Work'} require approval from 2 authorized personnel
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              !approvalStatus?.submitted ? 'bg-gray-200' :
              approvalStatus?.status === 'approved' ? 'bg-green-100' :
              approvalStatus?.status === 'rejected' ? 'bg-red-100' : 'bg-yellow-100'
            }`}>
              {!approvalStatus?.submitted ? (
                <Clock className="h-5 w-5 text-gray-500" />
              ) : approvalStatus?.status === 'approved' ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : approvalStatus?.status === 'rejected' ? (
                <XCircle className="h-5 w-5 text-red-600" />
              ) : (
                <Clock className="h-5 w-5 text-yellow-600" />
              )}
            </div>
            <div>
              <p className="font-medium">
                {!approvalStatus?.submitted ? 'Not Submitted' :
                 approvalStatus?.status === 'approved' ? 'Approved' :
                 approvalStatus?.status === 'rejected' ? 'Rejected' : 'Pending Approval'}
              </p>
              {approvalStatus?.submitted && approvalStatus?.status === 'pending' && (
                <p className="text-sm text-gray-500">
                  {approvalStatus.approvals_received} of {approvalStatus.approvals_required} approvals received
                </p>
              )}
            </div>
          </div>
          
          {!approvalStatus?.submitted ? (
            <Button onClick={() => setShowSubmitDialog(true)} data-testid="submit-for-approval-btn">
              <Send className="h-4 w-4 mr-2" />
              Submit for Approval
            </Button>
          ) : approvalStatus?.can_approve && approvalStatus?.status === 'pending' ? (
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleApprove} disabled={submitting}>
                <ThumbsUp className="h-4 w-4 mr-1" />
                Approve
              </Button>
            </div>
          ) : null}
        </div>

        {/* Approvers List */}
        {approvalStatus?.approvers && approvalStatus.approvers.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Approval History</p>
            <div className="space-y-2">
              {approvalStatus.approvers.map((approver, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-gray-400" />
                    <span className="text-sm">{approver.name || approver.email}</span>
                  </div>
                  <Badge variant={approver.decision === 'approved' ? 'default' : 'destructive'}>
                    {approver.decision}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit Dialog */}
        <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Submit for Dual Approval</DialogTitle>
              <DialogDescription>
                This {entityType} requires approval from 2 authorized personnel (Sales Manager, Principal Consultant, or Admin) before proceeding.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Notes for Approvers (Optional)</Label>
                <Textarea
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  placeholder="Add any notes or context for the approvers..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmitForApproval} disabled={submitting}>
                {submitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                Submit for Approval
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

// ============== 3. CLIENT CONSENT PANEL ==============

export const ClientConsentPanel = ({ 
  agreementId, 
  clientEmail: initialEmail,
  onConsentReceived,
  compact = false 
}) => {
  const [consentStatus, setConsentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showSendDialog, setShowSendDialog] = useState(false);
  const [clientEmail, setClientEmail] = useState(initialEmail || '');
  const [message, setMessage] = useState('');

  const fetchConsentStatus = useCallback(async () => {
    if (!agreementId) {
      setLoading(false);
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${API}/sales-funnel/consent-status/${agreementId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        setConsentStatus(data);
      }
    } catch (error) {
      console.error('Error fetching consent status:', error);
    } finally {
      setLoading(false);
    }
  }, [agreementId]);

  useEffect(() => {
    fetchConsentStatus();
  }, [fetchConsentStatus]);

  useEffect(() => {
    if (initialEmail) setClientEmail(initialEmail);
  }, [initialEmail]);

  const handleSendConsent = async () => {
    if (!clientEmail) {
      toast.error('Please enter client email');
      return;
    }
    
    setSending(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/sales-funnel/send-consent-request`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          agreement_id: agreementId,
          client_email: clientEmail,
          message: message || undefined
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success('Consent request sent to client');
        setShowSendDialog(false);
        fetchConsentStatus();
        
        // Show the consent token (in dev/demo mode)
        if (data.consent_token) {
          toast.info(`Demo: Token is ${data.consent_token.substring(0, 8)}...`, { duration: 10000 });
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to send');
      }
    } catch (error) {
      toast.error('Failed to send consent request');
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading consent status...
      </div>
    );
  }

  // Compact view
  if (compact) {
    return (
      <div className="flex items-center gap-2" data-testid="client-consent-compact">
        {!consentStatus?.sent ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowSendDialog(true)}
            className="gap-1"
          >
            <Mail className="h-3 w-3" />
            Request Consent
          </Button>
        ) : consentStatus?.status === 'pending' ? (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
            <Clock className="h-3 w-3 mr-1" />
            Awaiting Response
          </Badge>
        ) : consentStatus?.status === 'approved' ? (
          <Badge className="bg-green-100 text-green-700">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Consent Received
          </Badge>
        ) : (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Declined
          </Badge>
        )}

        {/* Send Dialog */}
        <Dialog open={showSendDialog} onOpenChange={setShowSendDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Request Client Consent</DialogTitle>
              <DialogDescription>
                Send a consent request to the client for this agreement. They will receive an email with a secure link.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Client Email *</Label>
                <Input
                  type="email"
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                  placeholder="client@company.com"
                />
              </div>
              <div>
                <Label>Custom Message (Optional)</Label>
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Add a personal message to include in the email..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowSendDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSendConsent} disabled={sending || !clientEmail}>
                {sending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                Send Request
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Full panel view
  return (
    <Card data-testid="client-consent-panel">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileCheck className="h-5 w-5 text-purple-600" />
          Client Consent
        </CardTitle>
        <CardDescription>
          Request and track client consent for this agreement
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              !consentStatus?.sent ? 'bg-gray-200' :
              consentStatus?.status === 'approved' ? 'bg-green-100' :
              consentStatus?.status === 'rejected' ? 'bg-red-100' : 'bg-yellow-100'
            }`}>
              {!consentStatus?.sent ? (
                <Mail className="h-5 w-5 text-gray-500" />
              ) : consentStatus?.status === 'approved' ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : consentStatus?.status === 'rejected' ? (
                <XCircle className="h-5 w-5 text-red-600" />
              ) : (
                <Clock className="h-5 w-5 text-yellow-600" />
              )}
            </div>
            <div>
              <p className="font-medium">
                {!consentStatus?.sent ? 'Not Sent' :
                 consentStatus?.status === 'approved' ? 'Consent Received' :
                 consentStatus?.status === 'rejected' ? 'Declined by Client' : 'Awaiting Response'}
              </p>
              {consentStatus?.sent_at && (
                <p className="text-sm text-gray-500">
                  Sent to {consentStatus.client_email} on {new Date(consentStatus.sent_at).toLocaleDateString()}
                </p>
              )}
              {consentStatus?.expires_at && consentStatus?.status === 'pending' && (
                <p className="text-xs text-orange-600">
                  Expires: {new Date(consentStatus.expires_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
          
          {!consentStatus?.sent || consentStatus?.status === 'rejected' ? (
            <Button onClick={() => setShowSendDialog(true)} data-testid="send-consent-btn">
              <Mail className="h-4 w-4 mr-2" />
              {consentStatus?.status === 'rejected' ? 'Resend' : 'Send Request'}
            </Button>
          ) : consentStatus?.status === 'pending' ? (
            <Button variant="outline" onClick={fetchConsentStatus}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          ) : null}
        </div>

        {/* Consent Details */}
        {consentStatus?.status === 'approved' && consentStatus?.client_name && (
          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Approved by: {consentStatus.client_name}
            </p>
            {consentStatus.approved_at && (
              <p className="text-xs text-green-600 dark:text-green-400">
                {new Date(consentStatus.approved_at).toLocaleString()}
              </p>
            )}
            {consentStatus.client_signature && (
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                Digital signature on file
              </p>
            )}
          </div>
        )}

        {/* Send Dialog */}
        <Dialog open={showSendDialog} onOpenChange={setShowSendDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Request Client Consent</DialogTitle>
              <DialogDescription>
                The client will receive an email with a secure link to review and approve/decline this agreement.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Client Email *</Label>
                <Input
                  type="email"
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                  placeholder="client@company.com"
                />
              </div>
              <div>
                <Label>Custom Message (Optional)</Label>
                <Textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Add a personal message to include in the consent request email..."
                  rows={3}
                />
              </div>
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  The consent link will expire in 7 days. The client can approve or decline with optional comments.
                </AlertDescription>
              </Alert>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowSendDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSendConsent} disabled={sending || !clientEmail}>
                {sending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                Send Consent Request
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

// ============== EXPORT ==============

export default {
  StageResumeBar,
  DualApprovalPanel,
  ClientConsentPanel
};
