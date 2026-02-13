import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { ArrowLeft, Send, Edit, CheckCircle, XCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import { format } from 'date-fns';

const AgreementManager = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [agreements, setAgreements] = useState([]);
  const [emailTemplates, setEmailTemplates] = useState([]);
  const [selectedAgreement, setSelectedAgreement] = useState(null);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [emailData, setEmailData] = useState({
    template_id: '',
    subject: '',
    body: '',
    recipient_email: '',
    cc_emails: []
  });

  useEffect(() => {
    fetchAgreements();
    fetchEmailTemplates();
  }, [leadId]);

  const fetchAgreements = async () => {
    try {
      const params = leadId ? { lead_id: leadId } : {};
      const response = await axios.get(`${API}/agreements`, { params });
      setAgreements(response.data);
    } catch (error) {
      toast.error('Failed to fetch agreements');
    }
  };

  const fetchEmailTemplates = async () => {
    try {
      const response = await axios.get(`${API}/email-notification-templates?template_type=agreement_notification`);
      setEmailTemplates(response.data);
    } catch (error) {
      console.error('Failed to fetch email templates');
    }
  };

  const openSendDialog = async (agreement) => {
    setSelectedAgreement(agreement);
    
    // Fetch lead details to pre-fill email
    try {
      const leadResponse = await axios.get(`${API}/leads/${agreement.lead_id}`);
      const lead = leadResponse.data;
      
      setEmailData({
        template_id: emailTemplates[0]?.id || '',
        subject: emailTemplates[0]?.subject || '',
        body: emailTemplates[0]?.body || '',
        recipient_email: lead.email || '',
        cc_emails: []
      });
      
      setSendDialogOpen(true);
    } catch (error) {
      toast.error('Failed to load lead details');
    }
  };

  const handleTemplateChange = (templateId) => {
    const template = emailTemplates.find(t => t.id === templateId);
    if (template) {
      setEmailData({
        ...emailData,
        template_id: templateId,
        subject: template.subject,
        body: template.body
      });
    }
  };

  const handleSendEmail = async () => {
    if (!emailData.recipient_email) {
      toast.error('Recipient email is required');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        agreement_id: selectedAgreement.id,
        email_template_id: emailData.template_id,
        custom_subject: emailData.subject,
        custom_body: emailData.body,
        recipient_email: emailData.recipient_email,
        cc_emails: emailData.cc_emails.filter(e => e)
      };

      const response = await axios.post(
        `${API}/agreements/${selectedAgreement.id}/send-email`,
        payload
      );

      if (response.data.success) {
        toast.success(`Agreement sent to ${emailData.recipient_email}`);
        setSendDialogOpen(false);
        fetchAgreements();
      } else {
        toast.error(response.data.message || 'Failed to send email');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send agreement email');
    } finally {
      setLoading(false);
    }
  };

  const getApprovalStatusBadge = (status) => {
    const badges = {
      pending_approval: { color: 'bg-yellow-50 text-yellow-700 border-yellow-200', icon: Clock, label: 'Pending Approval' },
      approved: { color: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: CheckCircle, label: 'Approved' },
      rejected: { color: 'bg-red-50 text-red-700 border-red-200', icon: XCircle, label: 'Rejected' }
    };
    return badges[status] || badges.pending_approval;
  };

  return (
    <div className=\"max-w-7xl mx-auto\" data-testid=\"agreement-manager\">
      <div className=\"mb-6\">
        <Button
          onClick={() => navigate('/leads')}
          variant=\"ghost\"
          className=\"mb-4 hover:bg-zinc-100 rounded-sm\"
        >
          <ArrowLeft className=\"w-4 h-4 mr-2\" strokeWidth={1.5} />
          Back to Leads
        </Button>
        <h1 className=\"text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2\">
          Agreements
        </h1>
        <p className=\"text-zinc-500\">Manage and send agreements to clients</p>
      </div>

      {agreements.length === 0 ? (
        <Card className=\"border-zinc-200 shadow-none rounded-sm\">
          <CardContent className=\"flex flex-col items-center justify-center h-64\">
            <p className=\"text-zinc-500 mb-4\">No agreements found</p>
          </CardContent>
        </Card>
      ) : (
        <div className=\"grid grid-cols-1 gap-4\">
          {agreements.map((agreement) => {
            const badge = getApprovalStatusBadge(agreement.approval_status);
            const StatusIcon = badge.icon;
            
            return (
              <Card
                key={agreement.id}
                className=\"border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors\"
              >
                <CardHeader>
                  <div className=\"flex items-start justify-between\">
                    <div className=\"flex-1\">
                      <CardTitle className=\"text-lg font-semibold text-zinc-950\">
                        {agreement.agreement_number}
                      </CardTitle>
                      <div className=\"text-sm text-zinc-500 mt-1\">
                        Created: {format(new Date(agreement.created_at), 'dd MMM yyyy, HH:mm')}
                      </div>
                    </div>
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-sm border ${badge.color}`}>
                      <StatusIcon className=\"w-4 h-4\" strokeWidth={1.5} />
                      <span className=\"text-sm font-medium\">{badge.label}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className=\"space-y-4\">
                  <div className=\"grid grid-cols-2 md:grid-cols-4 gap-4\">
                    <div>
                      <div className=\"text-xs uppercase tracking-wide text-zinc-500 mb-1\">
                        Start Date
                      </div>
                      <div className=\"text-sm font-medium text-zinc-950\">
                        {format(new Date(agreement.start_date), 'dd MMM yyyy')}
                      </div>
                    </div>
                    {agreement.end_date && (
                      <div>
                        <div className=\"text-xs uppercase tracking-wide text-zinc-500 mb-1\">
                          End Date
                        </div>
                        <div className=\"text-sm font-medium text-zinc-950\">
                          {format(new Date(agreement.end_date), 'dd MMM yyyy')}
                        </div>
                      </div>
                    )}
                    <div>
                      <div className=\"text-xs uppercase tracking-wide text-zinc-500 mb-1\">
                        Status
                      </div>
                      <div className=\"text-sm font-medium text-zinc-950 capitalize\">
                        {agreement.status}
                      </div>
                    </div>
                    {agreement.approved_by && (
                      <div>
                        <div className=\"text-xs uppercase tracking-wide text-zinc-500 mb-1\">
                          Approved By
                        </div>
                        <div className=\"text-sm font-medium text-zinc-950\">
                          {agreement.approved_by}
                        </div>
                      </div>
                    )}
                  </div>

                  {agreement.rejection_reason && (
                    <div className=\"p-3 bg-red-50 border border-red-200 rounded-sm\">
                      <div className=\"text-xs uppercase tracking-wide text-red-600 mb-1\">
                        Rejection Reason
                      </div>
                      <div className=\"text-sm text-red-700\">{agreement.rejection_reason}</div>
                    </div>
                  )}

                  {user?.role !== 'manager' && agreement.approval_status === 'pending_approval' && (
                    <div className=\"flex gap-3 pt-3 border-t border-zinc-200\">
                      <Button
                        onClick={() => openSendDialog(agreement)}
                        className=\"flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none\"
                      >
                        <Send className=\"w-4 h-4 mr-2\" strokeWidth={1.5} />
                        Send to Client
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Send Email Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent className=\"border-zinc-200 rounded-sm max-w-4xl max-h-[90vh] overflow-y-auto\">
          <DialogHeader>
            <DialogTitle className=\"text-xl font-semibold uppercase text-zinc-950\">
              Send Agreement to Client
            </DialogTitle>
            <DialogDescription className=\"text-zinc-500\">
              Choose a template and customize the email before sending
            </DialogDescription>
          </DialogHeader>
          
          <div className=\"space-y-4\">
            {/* Template Selection */}
            <div className=\"space-y-2\">
              <Label className=\"text-sm font-medium text-zinc-950\">Email Template</Label>
              <select
                value={emailData.template_id}
                onChange={(e) => handleTemplateChange(e.target.value)}
                className=\"w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm\"
              >
                <option value=\"\">Select a template</option>
                {emailTemplates.map(template => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Recipient Email */}
            <div className=\"space-y-2\">
              <Label className=\"text-sm font-medium text-zinc-950\">To (Client Email) *</Label>
              <Input
                type=\"email\"
                value={emailData.recipient_email}
                onChange={(e) => setEmailData({ ...emailData, recipient_email: e.target.value })}
                placeholder=\"client@company.com\"
                required
                className=\"rounded-sm border-zinc-200\"
              />
            </div>

            {/* Subject */}
            <div className=\"space-y-2\">
              <div className=\"flex items-center justify-between\">
                <Label className=\"text-sm font-medium text-zinc-950\">Subject *</Label>
                <span className=\"text-xs text-zinc-500\">
                  <Edit className=\"w-3 h-3 inline mr-1\" strokeWidth={1.5} />
                  Editable
                </span>
              </div>
              <Input
                value={emailData.subject}
                onChange={(e) => setEmailData({ ...emailData, subject: e.target.value })}
                placeholder=\"Email subject\"
                required
                className=\"rounded-sm border-zinc-200\"
              />
            </div>

            {/* Body */}
            <div className=\"space-y-2\">
              <div className=\"flex items-center justify-between\">
                <Label className=\"text-sm font-medium text-zinc-950\">Email Body *</Label>
                <span className=\"text-xs text-zinc-500\">
                  <Edit className=\"w-3 h-3 inline mr-1\" strokeWidth={1.5} />
                  Editable
                </span>
              </div>
              <textarea
                value={emailData.body}
                onChange={(e) => setEmailData({ ...emailData, body: e.target.value })}
                rows={12}
                placeholder=\"Email content\"
                required
                className=\"w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm font-mono\"
              />
              <p className=\"text-xs text-zinc-500\">
                Variables like {'{client_name}'}, {'{agreement_number}'}, {'{total_amount}'} will be automatically replaced
              </p>
            </div>

            {/* Action Buttons */}
            <div className=\"flex gap-3 pt-4 border-t border-zinc-200\">
              <Button
                onClick={() => setSendDialogOpen(false)}
                variant=\"outline\"
                className=\"flex-1 rounded-sm border-zinc-200\"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendEmail}
                disabled={loading || !emailData.recipient_email}
                className=\"flex-1 bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none\"
              >
                <Send className=\"w-4 h-4 mr-2\" strokeWidth={1.5} />
                {loading ? 'Sending...' : 'Send Agreement'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AgreementManager;
