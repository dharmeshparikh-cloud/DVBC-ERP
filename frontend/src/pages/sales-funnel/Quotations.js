import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { ArrowLeft, Plus, FileText, CheckCircle, Clock, Send, Users, Eye, History, Star, Building2, Save, Cloud } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import useDraft from '../../hooks/useDraft';
import DraftIndicator from '../../components/DraftIndicator';
import DraftSelector from '../../components/DraftSelector';

// Generate draft title from quotation data
const generateQuotationDraftTitle = (data) => {
  return `Quotation - ₹${data.base_rate_per_meeting?.toLocaleString() || '0'}/meeting`;
};

const Quotations = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const pricingPlanIdFromUrl = searchParams.get('pricing_plan_id');
  
  const [quotations, setQuotations] = useState([]);
  const [pricingPlans, setPricingPlans] = useState([]);
  const [leads, setLeads] = useState([]);
  const [agreements, setAgreements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [selectedPlanDetails, setSelectedPlanDetails] = useState(null);
  const [autoOpenHandled, setAutoOpenHandled] = useState(false);
  const [activeView, setActiveView] = useState('list');
  
  // Draft support
  const {
    drafts,
    loadingDrafts,
    saving: savingDraft,
    lastSaved,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft,
    registerFormDataGetter
  } = useDraft('quotation', generateQuotationDraftTitle);
  
  const [formData, setFormData] = useState({
    pricing_plan_id: pricingPlanIdFromUrl || '',
    lead_id: leadId || '',
    base_rate_per_meeting: 12500,
    validity_days: 30,
    terms_and_conditions: 'Standard terms and conditions apply.\n\n1. Payment due within 15 days of invoice.\n2. Services subject to availability.\n3. This quotation is valid for 30 days.'
  });
  
  // Register form data getter for save-on-leave
  const formDataRef = useRef(formData);
  useEffect(() => {
    formDataRef.current = formData;
  }, [formData]);
  
  useEffect(() => {
    if (dialogOpen) {
      registerFormDataGetter(() => formDataRef.current);
    }
    return () => {
      registerFormDataGetter(null);
    };
  }, [dialogOpen, registerFormDataGetter]);
  
  // Auto-save when form data changes
  useEffect(() => {
    if (dialogOpen && formData.pricing_plan_id) {
      autoSave(formData);
    }
  }, [formData, dialogOpen, autoSave]);

  useEffect(() => {
    fetchData();
  }, [leadId]);

  // Auto-open dialog with pre-selected plan when coming from SOW selection
  useEffect(() => {
    if (!loading && pricingPlanIdFromUrl && !autoOpenHandled && pricingPlans.length > 0) {
      const plan = pricingPlans.find(p => p.id === pricingPlanIdFromUrl);
      if (plan) {
        setSelectedPlanDetails(plan);
        setFormData(prev => ({ 
          ...prev, 
          pricing_plan_id: pricingPlanIdFromUrl,
          lead_id: plan.lead_id || prev.lead_id 
        }));
        setDialogOpen(true);
        setAutoOpenHandled(true);
      }
    }
  }, [loading, pricingPlanIdFromUrl, pricingPlans, autoOpenHandled]);

  const fetchData = async () => {
    try {
      const [quotationsRes, plansRes, leadsRes, agreementsRes] = await Promise.all([
        axios.get(`${API}/quotations`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/pricing-plans`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/leads`),
        axios.get(`${API}/agreements`).catch(() => ({ data: [] }))
      ]);
      setQuotations(quotationsRes.data);
      setPricingPlans(plansRes.data);
      setLeads(leadsRes.data);
      setAgreements(agreementsRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  // When pricing plan is selected, show its details
  const handlePlanSelect = (planId) => {
    const plan = pricingPlans.find(p => p.id === planId);
    setSelectedPlanDetails(plan);
    setFormData({ ...formData, pricing_plan_id: planId });
  };
  
  // Load a saved draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      if (loadedDraft.data.pricing_plan_id) {
        const plan = pricingPlans.find(p => p.id === loadedDraft.data.pricing_plan_id);
        setSelectedPlanDetails(plan);
      }
      toast.success('Draft loaded');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/quotations`, formData);
      toast.success('Quotation created successfully');
      convertDraft();
      clearDraft();
      setDialogOpen(false);
      setSelectedPlanDetails(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create quotation');
    }
  };

  const handleFinalize = async (quotationId) => {
    try {
      await axios.patch(`${API}/quotations/${quotationId}/finalize`);
      toast.success('Quotation finalized');
      fetchData();
    } catch (error) {
      toast.error('Failed to finalize quotation');
    }
  };

  const openDetailDialog = (quotation) => {
    const plan = pricingPlans.find(p => p.id === quotation.pricing_plan_id);
    setSelectedQuotation(quotation);
    setSelectedPlanDetails(plan);
    setDetailDialogOpen(true);
  };

  const getStatusBadge = (status, isFinal) => {
    if (isFinal) return 'bg-emerald-50 text-emerald-700';
    const styles = {
      draft: 'bg-zinc-100 text-zinc-600',
      sent: 'bg-blue-50 text-blue-700',
      accepted: 'bg-emerald-50 text-emerald-700',
      rejected: 'bg-red-50 text-red-700'
    };
    return styles[status] || styles.draft;
  };

  const getLeadName = (leadId) => {
    const lead = leads.find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Unknown Lead';
  };

  const getLead = (leadId) => {
    return leads.find(l => l.id === leadId);
  };

  // Check if quotation is used in an agreement
  const isUsedInAgreement = (quotationId) => {
    return agreements.some(a => a.quotation_id === quotationId);
  };

  const canEdit = user?.role !== 'manager';

  // Calculate team totals from pricing plan
  const calculatePlanTotals = (plan) => {
    if (!plan) return { totalMeetings: 0, subtotal: 0 };
    
    // Try team_deployment first, fall back to consultants
    const teamData = plan.team_deployment?.length > 0 ? plan.team_deployment : plan.consultants;
    
    if (!teamData || teamData.length === 0) return { totalMeetings: 0, subtotal: 0 };
    
    const totalMeetings = teamData.reduce((sum, m) => {
      const meetings = m.committed_meetings || m.meetings || 0;
      const count = m.count || 1;
      return sum + (meetings * count);
    }, 0);
    
    const subtotal = teamData.reduce((sum, m) => {
      const meetings = m.committed_meetings || m.meetings || 0;
      const count = m.count || 1;
      const rate = m.rate_per_meeting || 12500;
      return sum + (meetings * count * rate);
    }, 0);
    
    return { totalMeetings, subtotal };
  };

  // Group quotations by lead for history view
  const groupedByLead = quotations.reduce((acc, quotation) => {
    const key = quotation.lead_id;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(quotation);
    return acc;
  }, {});

  // Sort quotations within each group by created_at (newest first)
  Object.keys(groupedByLead).forEach(leadId => {
    groupedByLead[leadId].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  });

  return (
    <div className="max-w-6xl mx-auto" data-testid="quotations-page">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/leads')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Leads
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Proforma Invoices / Quotations
            </h1>
            <p className="text-zinc-500">Manage proforma invoices during negotiations</p>
          </div>
          {canEdit && (
            <Button
              onClick={() => {
                setSelectedPlanDetails(null);
                setDialogOpen(true);
              }}
              data-testid="create-quotation-btn"
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create Quotation
            </Button>
          )}
        </div>
      </div>

      {/* View Toggle Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeView === 'list' ? 'default' : 'outline'}
          onClick={() => setActiveView('list')}
          className="rounded-sm"
          data-testid="list-view-tab"
        >
          <FileText className="w-4 h-4 mr-2" />
          All Quotations
        </Button>
        <Button
          variant={activeView === 'history' ? 'default' : 'outline'}
          onClick={() => setActiveView('history')}
          className="rounded-sm"
          data-testid="history-view-tab"
        >
          <History className="w-4 h-4 mr-2" />
          Negotiation History
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading quotations...</div>
        </div>
      ) : quotations.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <FileText className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500 mb-4">No quotations found</p>
            {canEdit && pricingPlans.length > 0 && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Create Your First Quotation
              </Button>
            )}
            {pricingPlans.length === 0 && (
              <p className="text-sm text-zinc-400">Create a pricing plan first</p>
            )}
          </CardContent>
        </Card>
      ) : activeView === 'list' ? (
        /* LIST VIEW - All Quotations */
        <div className="space-y-4">
          {quotations.map((quotation) => {
            const usedInAgreement = isUsedInAgreement(quotation.id);
            return (
              <Card
                key={quotation.id}
                data-testid={`quotation-card-${quotation.id}`}
                className={`border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors ${
                  usedInAgreement ? 'border-l-4 border-l-emerald-500' : ''
                }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg font-semibold text-zinc-950">
                          {quotation.quotation_number}
                        </CardTitle>
                        {usedInAgreement && (
                          <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-sm bg-emerald-100 text-emerald-700">
                            <Star className="w-3 h-3" />
                            Selected for Agreement
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-zinc-500 mt-1">
                        {getLeadName(quotation.lead_id)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(quotation.status, quotation.is_final)}`}>
                        {quotation.is_final ? 'Finalized' : quotation.status}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</div>
                      <div className="text-lg font-semibold text-zinc-950">{quotation.total_meetings}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Subtotal</div>
                      <div className="text-lg font-semibold text-zinc-950">{formatINR(quotation.subtotal)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">GST (18%)</div>
                      <div className="text-lg font-semibold text-zinc-950">{formatINR(quotation.gst_amount)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Grand Total</div>
                      <div className="text-lg font-semibold text-emerald-600">{formatINR(quotation.grand_total)}</div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => openDetailDialog(quotation)}
                      size="sm"
                      variant="outline"
                      className="rounded-sm border-zinc-200"
                      data-testid={`view-details-${quotation.id}`}
                    >
                      <Eye className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      View Team Breakdown
                    </Button>
                    {!quotation.is_final && canEdit && (
                      <Button
                        onClick={() => handleFinalize(quotation.id)}
                        size="sm"
                        variant="outline"
                        className="rounded-sm border-zinc-200"
                      >
                        <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                        Finalize
                      </Button>
                    )}
                    {quotation.is_final && canEdit && !usedInAgreement && (
                      <Button
                        onClick={() => navigate(`/sales-funnel/agreements?quotationId=${quotation.id}&leadId=${quotation.lead_id}`)}
                        size="sm"
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                      >
                        <Send className="w-4 h-4 mr-2" strokeWidth={1.5} />
                        Create Agreement
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        /* HISTORY VIEW - Grouped by Lead/Prospect */
        <div className="space-y-6">
          {Object.keys(groupedByLead).map(leadId => {
            const lead = getLead(leadId);
            const quotationsList = groupedByLead[leadId];
            const selectedQuotation = quotationsList.find(q => isUsedInAgreement(q.id));
            
            return (
              <Card key={leadId} className="border-zinc-200 shadow-none rounded-sm" data-testid={`lead-group-${leadId}`}>
                <CardHeader className="bg-zinc-50 border-b border-zinc-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Building2 className="w-5 h-5 text-zinc-500" />
                      <div>
                        <CardTitle className="text-lg font-semibold text-zinc-950">
                          {lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Lead'}
                        </CardTitle>
                        <p className="text-sm text-zinc-500">{lead?.company || 'No company'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-zinc-500 uppercase">Total Revisions</div>
                      <div className="text-lg font-semibold text-zinc-950">{quotationsList.length}</div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-zinc-100">
                    {quotationsList.map((quotation, idx) => {
                      const isLatest = idx === 0;
                      const usedInAgreement = isUsedInAgreement(quotation.id);
                      const versionNumber = quotationsList.length - idx;
                      
                      return (
                        <div 
                          key={quotation.id} 
                          className={`p-4 ${usedInAgreement ? 'bg-emerald-50/50' : isLatest ? 'bg-blue-50/30' : ''}`}
                          data-testid={`history-item-${quotation.id}`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <span className={`px-2 py-1 text-xs font-mono font-semibold rounded-sm ${
                                usedInAgreement ? 'bg-emerald-100 text-emerald-700' :
                                isLatest ? 'bg-blue-100 text-blue-700' :
                                'bg-zinc-100 text-zinc-600'
                              }`}>
                                v{versionNumber}
                              </span>
                              <div>
                                <span className="font-medium text-zinc-900">{quotation.quotation_number}</span>
                                <span className="text-sm text-zinc-500 ml-2">
                                  {new Date(quotation.created_at).toLocaleDateString()}
                                </span>
                              </div>
                              {usedInAgreement && (
                                <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-sm bg-emerald-100 text-emerald-700">
                                  <Star className="w-3 h-3" />
                                  Selected for Agreement
                                </span>
                              )}
                              {isLatest && !usedInAgreement && (
                                <span className="px-2 py-0.5 text-xs font-medium rounded-sm bg-blue-100 text-blue-700">
                                  Latest
                                </span>
                              )}
                            </div>
                            <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(quotation.status, quotation.is_final)}`}>
                              {quotation.is_final ? 'Finalized' : quotation.status}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-4 gap-4 mb-3">
                            <div>
                              <div className="text-xs text-zinc-500">Meetings</div>
                              <div className="font-semibold">{quotation.total_meetings}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Subtotal</div>
                              <div className="font-semibold">{formatINR(quotation.subtotal)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">GST</div>
                              <div className="font-semibold">{formatINR(quotation.gst_amount)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Total</div>
                              <div className="font-semibold text-emerald-600">{formatINR(quotation.grand_total)}</div>
                            </div>
                          </div>
                          
                          <div className="flex gap-2">
                            <Button
                              onClick={() => openDetailDialog(quotation)}
                              size="sm"
                              variant="outline"
                              className="rounded-sm border-zinc-200 h-8"
                            >
                              <Eye className="w-3 h-3 mr-1" />
                              View
                            </Button>
                            {quotation.is_final && canEdit && !usedInAgreement && (
                              <Button
                                onClick={() => navigate(`/sales-funnel/agreements?quotationId=${quotation.id}&leadId=${quotation.lead_id}`)}
                                size="sm"
                                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none h-8"
                              >
                                <Send className="w-3 h-3 mr-1" />
                                Use for Agreement
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Quotation Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Create Quotation
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Generate a quotation from a pricing plan
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Lead *</Label>
                <select
                  value={formData.lead_id}
                  onChange={(e) => {
                    setFormData({ ...formData, lead_id: e.target.value, pricing_plan_id: '' });
                    setSelectedPlanDetails(null);
                  }}
                  required
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="">Select a lead</option>
                  {leads.map(lead => (
                    <option key={lead.id} value={lead.id}>
                      {lead.first_name} {lead.last_name} - {lead.company}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Pricing Plan *</Label>
                <select
                  value={formData.pricing_plan_id}
                  onChange={(e) => handlePlanSelect(e.target.value)}
                  required
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="">Select a pricing plan</option>
                  {pricingPlans.filter(p => !formData.lead_id || p.lead_id === formData.lead_id).map(plan => (
                    <option key={plan.id} value={plan.id}>
                      {plan.project_duration_months} months ({plan.project_duration_type}) - {formatINR(plan.total_amount || calculatePlanTotals(plan).subtotal)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Show Team Deployment from selected Pricing Plan */}
            {selectedPlanDetails && (
              <div className="border border-blue-200 rounded-sm p-4 bg-blue-50 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-blue-700">
                  <Users className="w-4 h-4" />
                  Team Deployment (from Pricing Plan)
                </div>
                <div className="text-xs text-blue-600 mb-2">
                  Duration: {selectedPlanDetails.project_duration_months} months ({selectedPlanDetails.project_duration_type?.replace('_', ' ')})
                </div>
                
                {(selectedPlanDetails.team_deployment?.length > 0 || selectedPlanDetails.consultants?.length > 0) ? (
                  <div className="space-y-1">
                    <div className="grid grid-cols-6 gap-2 text-xs font-medium text-blue-600 px-2">
                      <div>Role</div>
                      <div>Meeting Type</div>
                      <div>Frequency</div>
                      <div>Rate</div>
                      <div>Meetings</div>
                      <div>Subtotal</div>
                    </div>
                    {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants).map((member, idx) => {
                      const meetings = (member.committed_meetings || member.meetings || 0) * (member.count || 1);
                      const cost = meetings * (member.rate_per_meeting || 12500);
                      return (
                        <div key={idx} className="grid grid-cols-6 gap-2 text-xs px-2 py-1 bg-white rounded-sm">
                          <div className="truncate">{member.role || member.consultant_type}</div>
                          <div className="truncate">{member.meeting_type || '-'}</div>
                          <div className="truncate">{member.frequency || '-'}</div>
                          <div>{formatINR(member.rate_per_meeting || 12500)}</div>
                          <div className="font-semibold text-blue-700">{meetings}</div>
                          <div className="font-semibold text-emerald-700">{formatINR(cost)}</div>
                        </div>
                      );
                    })}
                    <div className="grid grid-cols-6 gap-2 text-xs font-semibold px-2 pt-2 border-t border-blue-200">
                      <div className="col-span-4 text-right">Total:</div>
                      <div className="text-blue-700">{calculatePlanTotals(selectedPlanDetails).totalMeetings}</div>
                      <div className="text-emerald-700">{formatINR(calculatePlanTotals(selectedPlanDetails).subtotal)}</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-blue-500">No team deployment data in this pricing plan</div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Base Rate per Meeting (₹)</Label>
                <Input
                  type="number"
                  value={formData.base_rate_per_meeting}
                  onChange={(e) => setFormData({ ...formData, base_rate_per_meeting: parseFloat(e.target.value) })}
                  className="rounded-sm border-zinc-200"
                  data-testid="base-rate-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Validity (Days)</Label>
                <Input
                  type="number"
                  value={formData.validity_days}
                  onChange={(e) => setFormData({ ...formData, validity_days: parseInt(e.target.value) })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Terms & Conditions</Label>
              <textarea
                value={formData.terms_and_conditions}
                onChange={(e) => setFormData({ ...formData, terms_and_conditions: e.target.value })}
                rows={4}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              data-testid="create-quotation-submit"
            >
              Create Quotation
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Details Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {selectedQuotation?.quotation_number} - Team Breakdown
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedQuotation && getLeadName(selectedQuotation.lead_id)}
            </DialogDescription>
          </DialogHeader>
          
          {selectedPlanDetails && (
            <div className="space-y-4">
              <div className="p-3 bg-zinc-100 rounded-sm text-sm">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <span className="text-zinc-500">Duration:</span>
                    <span className="font-semibold ml-2">{selectedPlanDetails.project_duration_months} months</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Type:</span>
                    <span className="font-semibold ml-2 capitalize">{selectedPlanDetails.project_duration_type?.replace('_', ' ')}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500">Payment:</span>
                    <span className="font-semibold ml-2 capitalize">{selectedPlanDetails.payment_schedule}</span>
                  </div>
                </div>
              </div>
              
              <div className="border border-zinc-200 rounded-sm overflow-hidden">
                <div className="bg-zinc-100 px-4 py-2 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  <span className="font-medium text-sm">Team Deployment Structure</span>
                </div>
                <div className="p-4">
                  {(selectedPlanDetails.team_deployment?.length > 0 || selectedPlanDetails.consultants?.length > 0) ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-7 gap-2 text-xs font-medium text-zinc-500 px-2">
                        <div>Role</div>
                        <div>Meeting Type</div>
                        <div>Frequency</div>
                        <div>Rate</div>
                        <div>Count</div>
                        <div>Meetings</div>
                        <div>Subtotal</div>
                      </div>
                      {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants).map((member, idx) => {
                        const meetings = (member.committed_meetings || member.meetings || 0) * (member.count || 1);
                        const cost = meetings * (member.rate_per_meeting || 12500);
                        return (
                          <div key={idx} className="grid grid-cols-7 gap-2 text-sm px-2 py-2 bg-zinc-50 rounded-sm">
                            <div className="truncate font-medium">{member.role || member.consultant_type}</div>
                            <div className="truncate">{member.meeting_type || '-'}</div>
                            <div className="truncate">{member.frequency || '-'}</div>
                            <div>{formatINR(member.rate_per_meeting || 12500)}</div>
                            <div>{member.count || 1}</div>
                            <div className="font-semibold text-blue-600">{meetings}</div>
                            <div className="font-semibold text-emerald-600">{formatINR(cost)}</div>
                          </div>
                        );
                      })}
                      <div className="grid grid-cols-7 gap-2 text-sm font-semibold px-2 pt-2 border-t border-zinc-200">
                        <div className="col-span-5 text-right">Total:</div>
                        <div className="text-blue-700">{calculatePlanTotals(selectedPlanDetails).totalMeetings}</div>
                        <div className="text-emerald-700">{formatINR(calculatePlanTotals(selectedPlanDetails).subtotal)}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-zinc-500 text-center py-4">No team deployment data available</div>
                  )}
                </div>
              </div>

              {/* Quotation Summary */}
              <div className="border border-zinc-200 rounded-sm p-4">
                <h4 className="text-sm font-semibold mb-3">Quotation Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Subtotal</span>
                    <span className="font-medium">{formatINR(selectedQuotation?.subtotal)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">GST (18%)</span>
                    <span className="font-medium">{formatINR(selectedQuotation?.gst_amount)}</span>
                  </div>
                  <div className="flex justify-between border-t border-zinc-200 pt-2">
                    <span className="font-semibold">Grand Total</span>
                    <span className="font-semibold text-emerald-600">{formatINR(selectedQuotation?.grand_total)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Quotations;
