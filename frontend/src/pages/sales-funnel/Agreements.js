import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';
import { ArrowLeft, Plus, FileCheck, Send, Clock, CheckCircle, XCircle, Mail, Download, FileText, Trash2, Users, Eye, LayoutGrid, List, CreditCard, Lock, Info } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import ViewToggle from '../../components/ViewToggle';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import FollowUpActionButton from '../../components/FollowUpActionButton';
import PageHeader from '../../components/ui/page-header';
import LeadSelector, { LockedField } from '../../components/LeadSelector';
import { useFunnelEligibility, getFunnelTooltip } from '../../hooks/useFunnelEligibility';
import { AgreementsTable } from '../../components/sales';

const MEETING_FREQUENCIES = ['Weekly', 'Bi-weekly', 'Monthly', 'Quarterly'];
const MEETING_MODES = ['Online', 'Offline', 'Mixed'];

const DEFAULT_TEAM_ROLES = [
  'Project Manager',
  'Lead Consultant',
  'Senior Consultant',
  'Lean Consultant',
  'Principal Consultant',
  'Data Analyst',
  'Digital Marketing Manager',
  'HR Consultant',
  'Sales Trainer',
  'Operations Consultant',
  'Subject Matter Expert',
  'Account Manager'
];

const MEETING_TYPES = [
  'Monthly Review',
  'Weekly Review',
  'Online Review',
  'On-site Visit',
  'Strategy Session',
  'Training Session',
  'Progress Update',
  'Kickoff Meeting',
  'Quarterly Business Review',
  'Data Analysis Review',
  'Marketing Review',
  'HR Consultation'
];

const FREQUENCY_OPTIONS = [
  { value: '1 per week', label: '1 per week', perMonth: 4 },
  { value: '2 per week', label: '2 per week', perMonth: 8 },
  { value: '3 per week', label: '3 per week', perMonth: 12 },
  { value: '4 per week', label: '4 per week', perMonth: 16 },
  { value: '5 per week', label: '5 per week', perMonth: 20 },
  { value: '1 per month', label: '1 per month', perMonth: 1 },
  { value: '2 per month', label: '2 per month', perMonth: 2 },
  { value: '3 per month', label: '3 per month', perMonth: 3 },
  { value: '4 per month', label: '4 per month', perMonth: 4 },
  { value: 'Bi-weekly', label: 'Bi-weekly', perMonth: 2 },
  { value: '1 per quarter', label: '1 per quarter', perMonth: 0.33 },
  { value: 'As needed', label: 'As needed', perMonth: 0 },
  { value: 'On demand', label: 'On demand', perMonth: 0 }
];

// Helper function to calculate committed meetings based on frequency and tenure
const calculateCommittedMeetings = (frequency, tenureMonths) => {
  const freqOption = FREQUENCY_OPTIONS.find(f => f.value === frequency);
  if (!freqOption || freqOption.perMonth === 0) return 0;
  return Math.round(freqOption.perMonth * tenureMonths);
};

const Agreements = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const quotationId = searchParams.get('quotationId');
  const leadId = searchParams.get('leadId');
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [selectedAgreement, setSelectedAgreement] = useState(null);
  const [emailData, setEmailData] = useState({
    template_id: '',
    custom_message: '',
    cc_emails: ''
  });
  const [downloading, setDownloading] = useState({});
  const [inheritedFromPlan, setInheritedFromPlan] = useState(false);
  const [viewMode, setViewMode] = useState('list');
  
  // Check if there are eligible leads (with quotations) for creating agreements
  const { hasEligibleLeads, isLoading: eligibilityLoading } = useFunnelEligibility('has_quotation');
  
  // Auto-switch to card view on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setViewMode('card');
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  const [formData, setFormData] = useState({
    quotation_id: quotationId || '',
    lead_id: leadId || '',
    agreement_type: 'standard',
    payment_terms: 'Net 30 days from invoice date',
    special_conditions: '',
    start_date: '',
    end_date: '',
    meeting_frequency: 'Monthly',
    project_tenure_months: 12,
    team_deployment: []
  });

  // SSOT: Track selected lead master data for locked field display
  const [selectedLeadData, setSelectedLeadData] = useState(null);

  const [newTeamMember, setNewTeamMember] = useState({
    role: '',
    meeting_type: '',
    frequency: '',
    mode: 'Online',
    base_rate_per_meeting: 12500,
    meetings_per_period: 0,
    committed_meetings: 0,
    notes: ''
  });

  const [autoOpenHandled, setAutoOpenHandled] = useState(false);

  // Fetch agreements data with React Query
  const { data: agreementsData, isLoading: loading, refetch: refetchAgreements } = useQuery({
    queryKey: ['agreements-data', leadId],
    queryFn: async () => {
      // Fetch all data in parallel with individual error handling
      const [agreementsRes, quotationsRes, leadsRes, templatesRes, plansRes] = await Promise.all([
        axios.get(`${API}/agreements`, { params: { ...(leadId ? { lead_id: leadId } : {}), page_size: 500 } }).catch(() => ({ data: { data: [] } })),
        axios.get(`${API}/quotations`).catch(() => ({ data: { data: [] } })),
        axios.get(`${API}/leads`).catch(() => ({ data: { data: [] } })),
        axios.get(`${API}/email-templates`).catch(() => ({ data: { templates: [] } })),
        axios.get(`${API}/pricing-plans`).catch(() => ({ data: [] }))
      ]);
      return {
        agreements: agreementsRes.data?.data || agreementsRes.data || [],
        quotations: quotationsRes.data?.data || quotationsRes.data || [],
        leads: leadsRes.data?.data || leadsRes.data?.items || leadsRes.data || [],
        emailTemplates: templatesRes.data?.templates || templatesRes.data || [],
        pricingPlans: Array.isArray(plansRes.data?.data) ? plansRes.data.data : (Array.isArray(plansRes.data) ? plansRes.data : [])
      };
    },
    staleTime: 0, // Force fresh data on each load
  });

  const agreements = agreementsData?.agreements || [];
  const quotations = agreementsData?.quotations || [];
  const leads = agreementsData?.leads || [];
  const emailTemplates = agreementsData?.emailTemplates || [];
  const pricingPlans = agreementsData?.pricingPlans || [];

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ['agreements-data'] });
  };

  // Auto-open dialog when coming from Proforma Invoice flow
  useEffect(() => {
    if (!loading && quotationId && !autoOpenHandled && quotations.length > 0) {
      const quotation = (quotations || []).find(q => q.id === quotationId);
      if (quotation) {
        const plan = (pricingPlans || []).find(p => p.id === quotation.pricing_plan_id);
        if (plan) {
          autoPopulateFromPlan(plan, quotation);
          setDialogOpen(true);
          setAutoOpenHandled(true);
        }
      }
    }
  }, [loading, quotationId, quotations, pricingPlans, autoOpenHandled]);

  // Auto-populate team deployment from pricing plan
  const autoPopulateFromPlan = (plan, quotation) => {
    const teamData = plan.team_deployment?.length > 0 ? plan.team_deployment : plan.consultants;
    
    if (teamData && teamData.length > 0) {
      const convertedTeam = (teamData || []).map((member, idx) => ({
        id: Date.now() + idx,
        role: member.role || member.consultant_type || '',
        meeting_type: member.meeting_type || '',
        frequency: member.frequency || '',
        mode: member.mode || 'Online',
        base_rate_per_meeting: member.rate_per_meeting || 12500,
        count: member.count || 1,
        committed_meetings: (member.committed_meetings || member.meetings || 0) * (member.count || 1),
        notes: member.notes || ''
      }));
      
      setFormData(prev => ({
        ...prev,
        quotation_id: quotation.id,
        lead_id: quotation.lead_id,
        project_tenure_months: plan.project_duration_months || 12,
        meeting_frequency: plan.project_duration_type === 'monthly' ? 'Monthly' : 'Custom',
        team_deployment: convertedTeam
      }));
      setInheritedFromPlan(true);
    }
  };

  // Handle quotation selection change
  const handleQuotationSelect = (quotationId) => {
    const quotation = (quotations || []).find(q => q.id === quotationId);
    if (quotation) {
      const plan = (pricingPlans || []).find(p => p.id === quotation.pricing_plan_id);
      if (plan) {
        autoPopulateFromPlan(plan, quotation);
      }
    }
    setFormData(prev => ({ ...prev, quotation_id: quotationId }));
  };

  const addTeamMember = () => {
    if (!newTeamMember.role || !newTeamMember.meeting_type || !newTeamMember.frequency) {
      toast.error('Please fill role, meeting type, and frequency');
      return;
    }
    // Calculate committed meetings based on frequency and project tenure
    const committedMeetings = calculateCommittedMeetings(newTeamMember.frequency, formData.project_tenure_months);
    const teamMemberData = {
      ...newTeamMember,
      committed_meetings: committedMeetings,
      id: Date.now()
    };
    setFormData(prev => ({
      ...prev,
      team_deployment: [...prev.team_deployment, teamMemberData]
    }));
    setNewTeamMember({ 
      role: '', 
      meeting_type: '', 
      frequency: '', 
      mode: 'Online', 
      base_rate_per_meeting: 12500,
      meetings_per_period: 0,
      committed_meetings: 0,
      notes: '' 
    });
  };

  const removeTeamMember = (index) => {
    setFormData(prev => ({
      ...prev,
      team_deployment: (prev?.team_deployment || []).filter((_, i) => i !== index)
    }));
  };

  // Recalculate committed meetings for all team members when tenure changes
  const handleTenureChange = (newTenure) => {
    const updatedTeamDeployment = (formData?.team_deployment || []).map(member => ({
      ...member,
      committed_meetings: calculateCommittedMeetings(member.frequency, newTenure)
    }));
    setFormData(prev => ({
      ...prev,
      project_tenure_months: newTenure,
      team_deployment: updatedTeamDeployment
    }));
  };

  // Calculate total cost for team deployment
  const calculateTeamTotals = () => {
    const totalMeetings = (formData?.team_deployment || []).reduce((sum, m) => sum + (m.committed_meetings || 0), 0);
    const totalCost = (formData?.team_deployment || []).reduce((sum, m) => sum + ((m.committed_meetings || 0) * (m.base_rate_per_meeting || 12500)), 0);
    return { totalMeetings, totalCost };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/agreements`, formData);
      toast.success('Agreement created and sent for approval');
      setDialogOpen(false);
      setFormData({
        quotation_id: '',
        lead_id: '',
        agreement_type: 'standard',
        payment_terms: 'Net 30 days from invoice date',
        special_conditions: '',
        start_date: '',
        end_date: '',
        meeting_frequency: 'Monthly',
        project_tenure_months: 12,
        team_deployment: []
      });
      invalidateData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      // Handle Pydantic validation errors (array format)
      if (Array.isArray(detail)) {
        const msg = (detail || []).map(e => e.msg || e.message || 'Validation error').join(', ');
        toast.error(msg);
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to create agreement');
      }
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    if (!selectedAgreement) return;
    
    try {
      await axios.post(`${API}/agreement-email/${selectedAgreement.id}`, {
        template_id: emailData.template_id || undefined,
        custom_message: emailData.custom_message || undefined,
        cc_emails: emailData.cc_emails ? emailData.cc_emails.split(',').map(e => e.trim()) : []
      });
      toast.success('Agreement email sent to client');
      setEmailDialogOpen(false);
      setSelectedAgreement(null);
      invalidateData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msg = (detail || []).map(e => e.msg || e.message || 'Validation error').join(', ');
        toast.error(msg);
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to send email');
      }
    }
  };

  const openEmailDialog = (agreement) => {
    setSelectedAgreement(agreement);
    setEmailData({ template_id: '', custom_message: '', cc_emails: '' });
    setEmailDialogOpen(true);
  };

  const handleDownload = async (agreementId, format) => {
    setDownloading(prev => ({ ...prev, [`${agreementId}-${format}`]: true }));
    try {
      const response = await axios.get(`${API}/agreements/${agreementId}/download`, {
        params: { format },
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = format === 'pdf' ? 'Agreement.pdf' : 'Agreement.docx';
      if (contentDisposition) {
        const matches = contentDisposition.match(/filename="(.+)"/);
        if (matches) filename = matches[1];
      }
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Downloaded ${filename}`);
    } catch (error) {
      toast.error('Failed to download document');
      console.error('Download error:', error);
    } finally {
      setDownloading(prev => ({ ...prev, [`${agreementId}-${format}`]: false }));
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      draft: { bg: 'bg-zinc-100 text-zinc-600', icon: Clock },
      pending_approval: { bg: 'bg-yellow-50 text-yellow-700', icon: Clock },
      approved: { bg: 'bg-emerald-50 text-emerald-700', icon: CheckCircle },
      rejected: { bg: 'bg-red-50 text-red-700', icon: XCircle },
      sent: { bg: 'bg-blue-50 text-blue-700', icon: Send },
      signed: { bg: 'bg-purple-50 text-purple-700', icon: FileCheck }
    };
    return styles[status] || styles.draft;
  };

  const getLeadName = (leadId) => {
    const lead = (leads || []).find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Unknown Lead';
  };

  const getLeadEmail = (leadId) => {
    const lead = (leads || []).find(l => l.id === leadId);
    return lead?.email || '';
  };

  const canEdit = user?.role !== 'manager';
  
  // Check if an agreement is editable (approved/signed agreements locked unless admin)
  const isAgreementEditable = (agreement) => {
    if (user?.role === 'admin') return true;
    const lockedStatuses = ['approved', 'signed', 'sent'];
    return !lockedStatuses.includes(agreement?.status);
  };

  return (
    <div className="max-w-6xl mx-auto" data-testid="agreements-page">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/sales-funnel/quotations')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Quotations
        </Button>
        <PageHeader
          title="Agreements"
          subtitle="Create and manage client agreements"
          onRefresh={() => refetchAgreements()}
          loading={loading}
          actions={<>
            <ViewToggle viewMode={viewMode} onChange={setViewMode} />
            {canEdit && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Button 
                        onClick={() => setDialogOpen(true)} 
                        data-testid="create-agreement-btn" 
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={!hasEligibleLeads || eligibilityLoading}
                      >
                        <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> Create Agreement
                        {!hasEligibleLeads && !eligibilityLoading && <Info className="w-3 h-3 ml-1 text-amber-300" />}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!hasEligibleLeads && !eligibilityLoading && (
                    <TooltipContent side="bottom" className="bg-zinc-900 text-white border-zinc-700 max-w-xs">
                      <p className="text-sm">{getFunnelTooltip('has_quotation')}</p>
                      <p className="text-xs text-zinc-400 mt-1">Go to Quotations → Create a quotation first</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            )}
          </>}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading agreements...</div>
        </div>
      ) : agreements.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <FileCheck className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500 mb-4">No agreements found</p>
            {canEdit && quotations.length > 0 && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Create Your First Agreement
              </Button>
            )}
            {quotations.length === 0 && (
              <p className="text-sm text-zinc-400">Finalize a quotation first</p>
            )}
          </CardContent>
        </Card>
      ) : viewMode === 'list' ? (
        /* List View - Using SalesDataTable (GOVERNANCE: No manual tables) */
        <AgreementsTable
          onRowClick={(agreement) => navigate(`/sales-funnel/agreement/${agreement.id}`)}
          onDownload={(id, format) => handleDownload(id, format)}
          onSendEmail={(agreement) => {
            setSelectedAgreement(agreement);
            setEmailDialogOpen(true);
          }}
          className="border border-zinc-200 rounded-sm"
        />
      ) : (
        /* Card View */
        <div className="space-y-4">
          {(agreements || []).map((agreement) => {
            const statusInfo = getStatusBadge(agreement.status);
            const StatusIcon = statusInfo.icon;
            return (
              <Card
                key={agreement.id}
                data-testid={`agreement-card-${agreement.id}`}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                onClick={() => navigate(`/sales-funnel/agreement/${agreement.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg font-semibold text-zinc-950">
                        {agreement.agreement_number}
                      </CardTitle>
                      <p className="text-sm text-zinc-500 mt-1">
                        {getLeadName(agreement.lead_id)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-sm flex items-center gap-1 ${statusInfo.bg}`}>
                        <StatusIcon className="w-3 h-3" strokeWidth={1.5} />
                        {agreement.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Type</div>
                      <div className="text-sm font-medium text-zinc-950 capitalize">{agreement.agreement_type}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Meeting Frequency</div>
                      <div className="text-sm font-medium text-zinc-950">{agreement.meeting_frequency || 'Monthly'}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Project Tenure</div>
                      <div className="text-sm font-medium text-zinc-950">{agreement.project_tenure_months || 12} months</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Start Date</div>
                      <div className="text-sm font-medium text-zinc-950">
                        {agreement.start_date ? new Date(agreement.start_date).toLocaleDateString() : 'Not set'}
                      </div>
                    </div>
                  </div>

                  {/* Team Deployment Summary */}
                  {agreement.team_deployment && agreement.team_deployment.length > 0 && (
                    <div className="mb-4 p-3 bg-blue-50 rounded-sm">
                      <div className="text-xs text-blue-600 uppercase tracking-wide mb-2 flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        Team Deployment ({agreement.team_deployment.length} members)
                      </div>
                      <div className="space-y-1">
                        {(agreement?.team_deployment || []).slice(0, 3).map((member, idx) => (
                          <div key={idx} className="text-sm text-zinc-700">
                            {member.role}: {member.meeting_type} - {member.frequency}
                          </div>
                        ))}
                        {agreement.team_deployment.length > 3 && (
                          <div className="text-xs text-zinc-500">+{agreement.team_deployment.length - 3} more...</div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {agreement.special_conditions && (
                    <div className="mb-4 p-3 bg-zinc-50 rounded-sm">
                      <div className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Special Conditions</div>
                      <p className="text-sm text-zinc-700">{agreement.special_conditions}</p>
                    </div>
                  )}

                  <div className="flex gap-2 flex-wrap" onClick={(e) => e.stopPropagation()}>
                    <Button
                      onClick={(e) => { e.stopPropagation(); navigate(`/sales-funnel/agreement/${agreement.id}`); }}
                      size="sm"
                      variant="outline"
                      className="rounded-sm border-zinc-300 hover:bg-zinc-100"
                      data-testid={`view-agreement-${agreement.id}`}
                    >
                      <Eye className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      View
                    </Button>
                    <Button
                      onClick={(e) => { e.stopPropagation(); handleDownload(agreement.id, 'pdf'); }}
                      size="sm"
                      variant="outline"
                      disabled={downloading[`${agreement.id}-pdf`]}
                      className="rounded-sm"
                      data-testid={`download-pdf-${agreement.id}`}
                    >
                      <Download className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      {downloading[`${agreement.id}-pdf`] ? 'Downloading...' : 'PDF'}
                    </Button>
                    <Button
                      onClick={(e) => { e.stopPropagation(); handleDownload(agreement.id, 'docx'); }}
                      size="sm"
                      variant="outline"
                      disabled={downloading[`${agreement.id}-docx`]}
                      className="rounded-sm"
                      data-testid={`download-docx-${agreement.id}`}
                    >
                      <FileText className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      {downloading[`${agreement.id}-docx`] ? 'Downloading...' : 'Word'}
                    </Button>
                    
                    {agreement.status === 'approved' && canEdit && (
                      <Button
                        onClick={(e) => { e.stopPropagation(); openEmailDialog(agreement); }}
                        size="sm"
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                      >
                        <Mail className="w-4 h-4 mr-2" strokeWidth={1.5} />
                        Send to Client
                      </Button>
                    )}
                    {(agreement.status === 'approved' || agreement.status === 'signed' || agreement.status === 'sent') && (
                      <Button
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          navigate(`/sales-funnel/payment-verification?agreement_id=${agreement.id}`);
                        }}
                        size="sm"
                        variant="outline"
                        className="rounded-sm border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                        data-testid={`verify-payment-${agreement.id}`}
                      >
                        <CreditCard className="w-4 h-4 mr-2" strokeWidth={1.5} />
                        Verify Payment
                      </Button>
                    )}
                    {agreement.status === 'pending_approval' && (
                      <span className="text-sm text-yellow-600 flex items-center gap-1">
                        <Clock className="w-4 h-4" strokeWidth={1.5} />
                        Awaiting manager approval
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Agreement Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Create Agreement
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Create an agreement with team deployment structure
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* SSOT: Lead Selection using LeadSelector component */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                Lead / Company *
                {formData.lead_id && <Lock className="w-3 h-3 text-amber-500" />}
              </Label>
              <LeadSelector
                value={formData.lead_id}
                onChange={(leadId) => {
                  setFormData({ ...formData, lead_id: leadId, quotation_id: '' });
                  setInheritedFromPlan(false);
                }}
                onMasterDataLoad={(masterData) => {
                  setSelectedLeadData(masterData);
                }}
                required={true}
                placeholder="Search for a lead with quotation..."
                funnelStage="has_quotation"
                noEligibleMessage="No leads with quotations found"
              />
            </div>
            
            {/* SSOT: Display locked lead master data */}
            {selectedLeadData && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm space-y-2">
                <div className="text-xs font-medium text-amber-700 flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  Master Data (from Lead - Read Only)
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <LockedField label="Company" value={selectedLeadData.company} />
                  <LockedField label="Contact Person" value={selectedLeadData.contact_person} />
                  <LockedField label="Email" value={selectedLeadData.email} />
                  <LockedField label="Phone" value={selectedLeadData.phone} />
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Quotation *</Label>
              <select
                value={formData.quotation_id}
                onChange={(e) => handleQuotationSelect(e.target.value)}
                required
                disabled={!formData.lead_id}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm disabled:bg-zinc-100 disabled:cursor-not-allowed"
                data-testid="quotation-select"
              >
                <option value="">{formData.lead_id ? 'Select a quotation' : 'Select a lead first'}</option>
                {(quotations || []).filter(q => !formData.lead_id || q.lead_id === formData.lead_id).map(q => (
                  <option key={q.id} value={q.id}>
                    {q.quotation_number} - {formatINR(q.grand_total)}
                  </option>
                ))}
              </select>
            </div>

            {/* Inherited Team Info Banner - Removed, replaced with locked notice in team section */}

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Agreement Type</Label>
                <select
                  value={formData.agreement_type}
                  onChange={(e) => setFormData({ ...formData, agreement_type: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="standard">Standard</option>
                  <option value="nda">NDA</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Meeting Frequency *</Label>
                <select
                  value={formData.meeting_frequency}
                  onChange={(e) => setFormData({ ...formData, meeting_frequency: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  {MEETING_FREQUENCIES.map(freq => (
                    <option key={freq} value={freq}>{freq}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Project Tenure (months) *</Label>
                <Input
                  type="number"
                  min="1"
                  max="60"
                  value={formData.project_tenure_months}
                  onChange={(e) => handleTenureChange(parseInt(e.target.value) || 12)}
                  className="rounded-sm border-zinc-200"
                  data-testid="project-tenure-input"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Start Date</Label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">End Date</Label>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
            </div>

            {/* Team Deployment Section - LOCKED from Pricing Plan */}
            <div className="border border-zinc-200 rounded-sm p-4 space-y-4">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-semibold text-zinc-950 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Team Deployment Structure
                  <Lock className="w-3 h-3 text-amber-500" />
                </Label>
                {formData.team_deployment.length > 0 && (
                  <div className="text-xs text-zinc-500">
                    Total: <span className="font-semibold text-emerald-600">{calculateTeamTotals().totalMeetings}</span> meetings
                    {user?.role === 'admin' && (
                      <span className="ml-1">| <span className="font-semibold text-emerald-600">{formatINR(calculateTeamTotals().totalCost)}</span></span>
                    )}
                  </div>
                )}
              </div>
              
              {/* Locked Notice */}
              {inheritedFromPlan && formData.team_deployment.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm text-xs text-amber-700 flex items-center gap-2">
                  <Lock className="w-3 h-3" />
                  Team deployment is locked from Pricing Plan. To modify, update the Pricing Plan.
                </div>
              )}

              {/* Team Members List - Read Only (no add/remove) */}
              {formData.team_deployment.length > 0 && (
                <div className="space-y-2">
                  <div className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-4'} gap-2 text-xs font-medium text-zinc-500 px-2`}>
                    <div>Role</div>
                    <div>Meeting Type</div>
                    <div>Frequency</div>
                    <div className="text-center">Committed Meetings</div>
                    {user?.role === 'admin' && <div className="text-right">Rate/Meeting</div>}
                  </div>
                  {(formData?.team_deployment || []).map((member, index) => (
                    <div key={member.id || index} className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-4'} gap-2 items-center p-2 bg-zinc-50 border border-zinc-100 rounded-sm text-sm`} data-testid={`team-member-${index}`}>
                      <div className="font-medium truncate" title={member.role}>{member.role}</div>
                      <div className="truncate" title={member.meeting_type}>{member.meeting_type}</div>
                      <div className="truncate">{member.frequency}</div>
                      <div className="text-center font-semibold text-blue-600">{member.committed_meetings || 0}</div>
                      {user?.role === 'admin' && (
                        <div className="text-right font-semibold text-zinc-600">{formatINR(member.base_rate_per_meeting || 12500)}</div>
                      )}
                    </div>
                  ))}
                  
                  {/* Totals Row */}
                  <div className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-4'} gap-2 items-center p-2 bg-zinc-100 border border-zinc-200 rounded-sm text-sm font-semibold`}>
                    <div className="col-span-3 text-right">Total:</div>
                    <div className="text-center text-blue-700">{calculateTeamTotals().totalMeetings}</div>
                    {user?.role === 'admin' && (
                      <div className="text-right text-emerald-700">{formatINR(calculateTeamTotals().totalCost)}</div>
                    )}
                  </div>
                </div>
              )}
              
              {formData.team_deployment.length === 0 && (
                <p className="text-sm text-zinc-400 text-center py-4">
                  Select a quotation to inherit team deployment from the Pricing Plan.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Payment Terms</Label>
              <Input
                value={formData.payment_terms}
                onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Special Conditions</Label>
              <textarea
                value={formData.special_conditions}
                onChange={(e) => setFormData({ ...formData, special_conditions: e.target.value })}
                rows={3}
                placeholder="Any special terms or conditions..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Create & Submit for Approval
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Send Email Dialog */}
      <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Send Agreement to Client
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedAgreement && `Sending ${selectedAgreement.agreement_number} to ${getLeadEmail(selectedAgreement.lead_id)}`}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSendEmail} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Email Template (Optional)</Label>
              <select
                value={emailData.template_id}
                onChange={(e) => setEmailData({ ...emailData, template_id: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="">Use default template</option>
                {(emailTemplates || []).map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Custom Message (Optional)</Label>
              <textarea
                value={emailData.custom_message}
                onChange={(e) => setEmailData({ ...emailData, custom_message: e.target.value })}
                rows={4}
                placeholder="Add a personal message to the email..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">CC Emails (comma separated)</Label>
              <Input
                value={emailData.cc_emails}
                onChange={(e) => setEmailData({ ...emailData, cc_emails: e.target.value })}
                placeholder="email1@company.com, email2@company.com"
                className="rounded-sm border-zinc-200"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Mail className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Send Email
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Agreements;
