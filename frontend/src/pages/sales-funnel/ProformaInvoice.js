import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { 
  ArrowLeft, Plus, FileText, CheckCircle, Clock, Send, Users, Eye, 
  Download, Printer, ArrowRight, Building2, Phone, Mail, MapPin, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR, numberToWords } from '../../utils/currency';
import SalesFunnelProgress from '../../components/SalesFunnelProgress';

const ProformaInvoice = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const pricingPlanIdFromUrl = searchParams.get('pricing_plan_id');
  const invoiceRef = useRef(null);
  
  const [invoices, setInvoices] = useState([]);
  const [pricingPlans, setPricingPlans] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [sowData, setSowData] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [selectedPlanDetails, setSelectedPlanDetails] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [autoOpenHandled, setAutoOpenHandled] = useState(false);
  
  const [formData, setFormData] = useState({
    pricing_plan_id: pricingPlanIdFromUrl || '',
    lead_id: leadId || '',
    base_rate_per_meeting: 12500,
    validity_days: 30,
    payment_terms: 'ADVANCE',
    terms_and_conditions: '1) Payment to be paid via Bank transfer or cheques\n2) Payment refund is not permissible\n3) Any breach of information is subject to violation of agreement\n4) TDS amount to be paid regularly and submit challan to biller\n5) Disputes subject to Ahmedabad jurisdiction.'
  });

  // Company details (can be moved to config)
  const companyDetails = {
    name: 'D & V Business Consulting',
    address: '626, Iconic Shyamal, Shyamal Cross Road, Ahmedabad - 380015.',
    gstin: '24ASLPP4013H1ZV',
    state: 'Gujarat',
    stateCode: '24',
    phone: '+91-9824009829',
    bankName: 'ICICI Bank',
    accountName: 'D & V Business Consulting',
    accountNo: '034405500698',
    branch: 'VASNA',
    ifscCode: 'ICIC0000344',
    swiftCode: 'ICICINBBCTS'
  };

  useEffect(() => {
    fetchData();
  }, [leadId]);

  // Auto-open dialog with pre-selected plan when coming from SOW selection
  useEffect(() => {
    if (!loading && pricingPlanIdFromUrl && !autoOpenHandled && pricingPlans.length > 0) {
      const plan = pricingPlans.find(p => p.id === pricingPlanIdFromUrl);
      if (plan) {
        setSelectedPlanDetails(plan);
        const lead = leads.find(l => l.id === plan.lead_id);
        setSelectedLead(lead);
        setFormData(prev => ({ 
          ...prev, 
          pricing_plan_id: pricingPlanIdFromUrl,
          lead_id: plan.lead_id || prev.lead_id 
        }));
        setDialogOpen(true);
        setAutoOpenHandled(true);
      }
    }
  }, [loading, pricingPlanIdFromUrl, pricingPlans, autoOpenHandled, leads]);

  const fetchData = async () => {
    try {
      const [invoicesRes, plansRes, leadsRes] = await Promise.all([
        axios.get(`${API}/quotations`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/pricing-plans`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/leads`)
      ]);
      setInvoices(invoicesRes.data);
      setPricingPlans(plansRes.data);
      setLeads(leadsRes.data);
      
      // Fetch SOW data if we have a pricing plan ID
      if (pricingPlanIdFromUrl) {
        try {
          const sowRes = await axios.get(`${API}/enhanced-sow/${pricingPlanIdFromUrl}`);
          setSowData(sowRes.data);
        } catch (e) {
          // SOW might not exist yet
          setSowData(null);
        }
      }
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  // Check if proforma invoice exists for current pricing plan
  const currentInvoice = invoices.find(inv => inv.pricing_plan_id === pricingPlanIdFromUrl);
  const hasProformaInvoice = !!currentInvoice;
  const isProformaFinalized = currentInvoice?.is_final || false;

  const handlePlanSelect = (planId) => {
    const plan = pricingPlans.find(p => p.id === planId);
    setSelectedPlanDetails(plan);
    setFormData({ ...formData, pricing_plan_id: planId });
  };

  const handleLeadSelect = (selectedLeadId) => {
    const lead = leads.find(l => l.id === selectedLeadId);
    setSelectedLead(lead);
    setFormData({ ...formData, lead_id: selectedLeadId, pricing_plan_id: '' });
    setSelectedPlanDetails(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/quotations`, formData);
      toast.success('Proforma Invoice created successfully');
      setDialogOpen(false);
      setSelectedPlanDetails(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create proforma invoice');
    }
  };

  const handleFinalize = async (invoiceId) => {
    try {
      await axios.patch(`${API}/quotations/${invoiceId}/finalize`);
      toast.success('Proforma Invoice finalized');
      fetchData();
    } catch (error) {
      toast.error('Failed to finalize proforma invoice');
    }
  };

  const openViewDialog = (invoice) => {
    const plan = pricingPlans.find(p => p.id === invoice.pricing_plan_id);
    const lead = leads.find(l => l.id === invoice.lead_id);
    setSelectedInvoice(invoice);
    setSelectedPlanDetails(plan);
    setSelectedLead(lead);
    setViewDialogOpen(true);
  };

  const handleDownloadPDF = () => {
    if (!invoiceRef.current) return;
    
    // Use browser print functionality for PDF generation
    const printContent = invoiceRef.current.innerHTML;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Proforma Invoice - ${selectedInvoice?.quotation_number}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; font-size: 12px; }
            .invoice-container { max-width: 800px; margin: 0 auto; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { border: 1px solid #000; padding: 6px 8px; text-align: left; }
            th { background-color: #f0f0f0; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .font-bold { font-weight: bold; }
            .border-none { border: none !important; }
            .header { display: flex; justify-content: space-between; margin-bottom: 20px; }
            .company-name { font-size: 24px; font-weight: bold; color: #000; }
            .section-title { background-color: #f0f0f0; padding: 8px; font-weight: bold; margin: 15px 0 5px 0; }
            @media print { body { -webkit-print-color-adjust: exact; } }
          </style>
        </head>
        <body>${printContent}</body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
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

  const canEdit = user?.role !== 'manager';

  const calculatePlanTotals = (plan) => {
    if (!plan) return { totalMeetings: 0, subtotal: 0 };
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

  // Navigate back to previous step in flow
  const handleBackToFlow = () => {
    if (pricingPlanIdFromUrl) {
      navigate(`/sales-funnel/scope-selection/${pricingPlanIdFromUrl}`);
    } else {
      navigate('/sales-funnel/pricing-plans');
    }
  };

  // Format date for invoice
  const formatDate = (date) => {
    const d = new Date(date || new Date());
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
  };

  // Generate invoice number
  const generateInvoiceNumber = () => {
    const year = new Date().getFullYear();
    const nextYear = year + 1;
    return `${year}-${nextYear.toString().slice(-2)}/PI-${Math.floor(Math.random() * 9000) + 1000}`;
  };

  return (
    <div className="max-w-6xl mx-auto" data-testid="proforma-invoice-page">
      <div className="mb-6">
        <Button
          onClick={handleBackToFlow}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
          data-testid="back-to-flow-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to {pricingPlanIdFromUrl ? 'Scope Selection' : 'Pricing Plans'}
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Proforma Invoice
            </h1>
            <p className="text-zinc-500">Create and manage proforma invoices for clients</p>
          </div>
          {canEdit && (
            <Button
              onClick={() => {
                setSelectedPlanDetails(null);
                setSelectedLead(null);
                setDialogOpen(true);
              }}
              data-testid="create-invoice-btn"
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create Proforma Invoice
            </Button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading proforma invoices...</div>
        </div>
      ) : invoices.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <FileText className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500 mb-4">No proforma invoices found</p>
            {canEdit && pricingPlans.length > 0 && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Create Your First Proforma Invoice
              </Button>
            )}
            {pricingPlans.length === 0 && (
              <p className="text-sm text-zinc-400">Create a pricing plan first</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {invoices.map((invoice) => (
            <Card
              key={invoice.id}
              data-testid={`invoice-card-${invoice.id}`}
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg font-semibold text-zinc-950">
                      {invoice.quotation_number}
                    </CardTitle>
                    <p className="text-sm text-zinc-500 mt-1">
                      {getLeadName(invoice.lead_id)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(invoice.status, invoice.is_final)}`}>
                      {invoice.is_final ? 'Finalized' : invoice.status}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</div>
                    <div className="text-lg font-semibold text-zinc-950">{invoice.total_meetings}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Subtotal</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(invoice.subtotal)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">GST (18%)</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(invoice.gst_amount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Grand Total</div>
                    <div className="text-lg font-semibold text-emerald-600">{formatINR(invoice.grand_total)}</div>
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button
                    onClick={() => openViewDialog(invoice)}
                    size="sm"
                    variant="outline"
                    className="rounded-sm border-zinc-200"
                    data-testid={`view-invoice-${invoice.id}`}
                  >
                    <Eye className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    View Invoice
                  </Button>
                  {!invoice.is_final && canEdit && (
                    <Button
                      onClick={() => handleFinalize(invoice.id)}
                      size="sm"
                      variant="outline"
                      className="rounded-sm border-zinc-200"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Finalize
                    </Button>
                  )}
                  {invoice.is_final && canEdit && (
                    <Button
                      onClick={() => navigate(`/sales-funnel/agreements?quotationId=${invoice.id}&leadId=${invoice.lead_id}`)}
                      size="sm"
                      className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                    >
                      <ArrowRight className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Proceed to Agreement
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Proforma Invoice Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Create Proforma Invoice
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Generate a proforma invoice from a pricing plan
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Lead *</Label>
                <select
                  value={formData.lead_id}
                  onChange={(e) => handleLeadSelect(e.target.value)}
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
                <Label className="text-sm font-medium text-zinc-950">Payment Terms</Label>
                <select
                  value={formData.payment_terms}
                  onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="ADVANCE">Advance</option>
                  <option value="NET_15">Net 15 Days</option>
                  <option value="NET_30">Net 30 Days</option>
                  <option value="NET_45">Net 45 Days</option>
                </select>
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
              <Label className="text-sm font-medium text-zinc-950">Terms of Delivery</Label>
              <textarea
                value={formData.terms_and_conditions}
                onChange={(e) => setFormData({ ...formData, terms_and_conditions: e.target.value })}
                rows={4}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                onClick={() => setDialogOpen(false)}
                variant="outline"
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                data-testid="create-invoice-submit"
              >
                Create Proforma Invoice
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Proforma Invoice Dialog - Downloadable Format */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-4xl max-h-[95vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
                Proforma Invoice
              </DialogTitle>
              <div className="flex gap-2">
                <Button
                  onClick={handleDownloadPDF}
                  size="sm"
                  variant="outline"
                  className="rounded-sm"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
                <Button
                  onClick={handleDownloadPDF}
                  size="sm"
                  variant="outline"
                  className="rounded-sm"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Send to Client
                </Button>
              </div>
            </div>
          </DialogHeader>
          
          {/* Printable Invoice Content - Modern Layout */}
          <div ref={invoiceRef} className="bg-white">
            {/* Header with gradient accent */}
            <div className="bg-gradient-to-r from-zinc-900 to-zinc-700 text-white p-6 rounded-t-sm">
              <div className="flex justify-between items-start">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">D&V®</h1>
                  <p className="text-zinc-300 text-sm mt-1">Business Consulting</p>
                </div>
                <div className="text-right">
                  <div className="bg-white/10 backdrop-blur px-4 py-2 rounded-sm">
                    <h2 className="text-lg font-bold">PROFORMA INVOICE</h2>
                    <p className="text-zinc-300 text-xs">{selectedInvoice?.quotation_number}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Invoice Meta & Company Info */}
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-4">
                  <div className="bg-zinc-50 rounded-sm p-4">
                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">Invoice Details</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Invoice No.</span>
                        <span className="font-semibold">{selectedInvoice?.quotation_number}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Date</span>
                        <span>{formatDate(selectedInvoice?.created_at)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Payment Terms</span>
                        <span className="font-medium text-emerald-600">ADVANCE</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Valid Until</span>
                        <span>{formatDate(new Date(new Date(selectedInvoice?.created_at).getTime() + 30*24*60*60*1000))}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Buyer Details */}
                  <div className="bg-blue-50 rounded-sm p-4 border-l-4 border-blue-500">
                    <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-3">Bill To</h3>
                    <div className="text-sm">
                      <p className="font-bold text-zinc-900 text-base">{selectedLead?.company || 'Client Company'}</p>
                      <p className="text-zinc-600 mt-1">{selectedLead?.first_name} {selectedLead?.last_name}</p>
                      <p className="text-zinc-500 text-xs mt-2">{selectedLead?.address || 'Address not provided'}</p>
                      {selectedLead?.gstin && <p className="text-zinc-600 text-xs mt-1">GSTIN: {selectedLead.gstin}</p>}
                      <p className="text-zinc-500 text-xs">State: Gujarat, Code: 24</p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  {/* Company Details */}
                  <div className="bg-zinc-50 rounded-sm p-4">
                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">From</h3>
                    <div className="text-sm">
                      <p className="font-bold text-zinc-900">{companyDetails.name}</p>
                      <p className="text-zinc-600 text-xs mt-2">{companyDetails.address}</p>
                      <p className="text-zinc-600 text-xs mt-1">GSTIN: {companyDetails.gstin}</p>
                      <p className="text-zinc-600 text-xs">State: {companyDetails.state}, Code: {companyDetails.stateCode}</p>
                      <p className="text-zinc-600 text-xs mt-1">{companyDetails.phone}</p>
                    </div>
                  </div>
                  
                  {/* Quick Summary Card */}
                  <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-sm p-4 text-white">
                    <h3 className="text-xs font-semibold uppercase tracking-wide opacity-80 mb-2">Amount Due</h3>
                    <p className="text-3xl font-bold">{formatINR(selectedInvoice?.grand_total || 0)}</p>
                    <p className="text-xs opacity-70 mt-1">Including 18% GST</p>
                  </div>
                </div>
              </div>

              {/* Project Overview */}
              <div className="bg-zinc-900 text-white rounded-sm p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">Project Duration</h3>
                    <p className="text-zinc-400 text-sm">{selectedPlanDetails?.project_duration_type?.replace('_', ' ')?.toUpperCase() || 'CUSTOM'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold">{selectedPlanDetails?.project_duration_months || 12}</p>
                    <p className="text-zinc-400 text-xs">MONTHS</p>
                  </div>
                </div>
              </div>

              {/* Team Deployment Structure */}
              {selectedPlanDetails && (selectedPlanDetails.team_deployment || selectedPlanDetails.consultants || []).length > 0 && (
                <div className="border border-zinc-200 rounded-sm overflow-hidden">
                  <div className="bg-zinc-100 px-4 py-3 border-b border-zinc-200">
                    <h3 className="font-semibold text-zinc-800 flex items-center gap-2">
                      <Users className="w-4 h-4" />
                      Team Deployment Structure
                    </h3>
                    <p className="text-xs text-zinc-500 mt-1">Consultant allocation for the project duration</p>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-4 gap-3 mb-3">
                      <div className="text-xs font-semibold text-zinc-500 uppercase">Role</div>
                      <div className="text-xs font-semibold text-zinc-500 uppercase">Meeting Type</div>
                      <div className="text-xs font-semibold text-zinc-500 uppercase">Frequency</div>
                      <div className="text-xs font-semibold text-zinc-500 uppercase text-center">Meetings</div>
                    </div>
                    {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants).map((member, idx) => {
                      const meetings = (member.committed_meetings || member.meetings || 0) * (member.count || 1);
                      return (
                        <div key={idx} className="grid grid-cols-4 gap-3 py-3 border-t border-zinc-100 items-center">
                          <div>
                            <span className="inline-flex items-center px-2 py-1 bg-zinc-100 text-zinc-700 text-xs font-medium rounded-sm">
                              {member.role || member.consultant_type}
                            </span>
                          </div>
                          <div className="text-sm text-zinc-600">{member.meeting_type || '-'}</div>
                          <div className="text-sm text-zinc-600">{member.frequency || '-'}</div>
                          <div className="text-center">
                            <span className="inline-flex items-center justify-center w-10 h-10 bg-blue-50 text-blue-700 font-bold rounded-full text-sm">
                              {meetings}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                    <div className="grid grid-cols-4 gap-3 py-3 border-t-2 border-zinc-200 bg-zinc-50 -mx-4 px-4 mt-3">
                      <div className="col-span-3 text-right font-semibold text-zinc-700">Total Meetings</div>
                      <div className="text-center">
                        <span className="inline-flex items-center justify-center w-12 h-10 bg-zinc-900 text-white font-bold rounded-sm text-sm">
                          {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants || []).reduce((sum, m) => {
                            const meetings = (m.committed_meetings || m.meetings || 0) * (m.count || 1);
                            return sum + meetings;
                          }, 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Pricing Breakdown */}
              <div className="border border-zinc-200 rounded-sm overflow-hidden">
                <div className="bg-zinc-100 px-4 py-3 border-b border-zinc-200">
                  <h3 className="font-semibold text-zinc-800">Pricing Summary</h3>
                </div>
                <div className="p-4">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-200">
                        <th className="text-left py-2 text-zinc-500 font-medium">Description</th>
                        <th className="text-center py-2 text-zinc-500 font-medium">HSN/SAC</th>
                        <th className="text-center py-2 text-zinc-500 font-medium">Period</th>
                        <th className="text-right py-2 text-zinc-500 font-medium">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-zinc-100">
                        <td className="py-3">
                          <div className="font-medium text-zinc-900">Professional Fees - Consulting Services</div>
                          <div className="text-xs text-zinc-500">{selectedPlanDetails?.project_duration_months || 12} months engagement</div>
                        </td>
                        <td className="py-3 text-center text-zinc-600">998311</td>
                        <td className="py-3 text-center text-zinc-600">{selectedPlanDetails?.project_duration_months || 12} Months</td>
                        <td className="py-3 text-right font-semibold">{formatINR(selectedInvoice?.subtotal || 0)}</td>
                      </tr>
                    </tbody>
                  </table>
                  
                  {/* Tax & Total Section */}
                  <div className="mt-4 pt-4 border-t border-zinc-200">
                    <div className="flex justify-end">
                      <div className="w-72 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-zinc-500">Subtotal</span>
                          <span className="font-medium">{formatINR(selectedInvoice?.subtotal || 0)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-zinc-500">CGST @ 9%</span>
                          <span>{formatINR((selectedInvoice?.gst_amount || 0) / 2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-zinc-500">SGST @ 9%</span>
                          <span>{formatINR((selectedInvoice?.gst_amount || 0) / 2)}</span>
                        </div>
                        <div className="flex justify-between text-sm pt-2 border-t border-zinc-200">
                          <span className="text-zinc-500">Total Tax (18%)</span>
                          <span className="font-medium">{formatINR(selectedInvoice?.gst_amount || 0)}</span>
                        </div>
                        <div className="flex justify-between text-lg pt-2 border-t-2 border-zinc-900">
                          <span className="font-bold">Grand Total</span>
                          <span className="font-bold text-emerald-600">{formatINR(selectedInvoice?.grand_total || 0)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Amount in Words */}
              <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
                <p className="text-sm">
                  <span className="font-semibold text-amber-800">Amount in Words:</span>
                  <span className="text-amber-900 ml-2">{numberToWords(selectedInvoice?.grand_total || 0)}</span>
                </p>
              </div>

              {/* HSN Summary */}
              <div className="border border-zinc-200 rounded-sm overflow-hidden">
                <div className="bg-zinc-100 px-4 py-2 border-b border-zinc-200">
                  <h3 className="font-medium text-zinc-700 text-sm">HSN/SAC Summary</h3>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-zinc-50">
                      <th className="px-4 py-2 text-left font-medium text-zinc-600">HSN/SAC</th>
                      <th className="px-4 py-2 text-right font-medium text-zinc-600">Taxable Value</th>
                      <th className="px-4 py-2 text-center font-medium text-zinc-600">CGST Rate</th>
                      <th className="px-4 py-2 text-right font-medium text-zinc-600">CGST Amt</th>
                      <th className="px-4 py-2 text-center font-medium text-zinc-600">SGST Rate</th>
                      <th className="px-4 py-2 text-right font-medium text-zinc-600">SGST Amt</th>
                      <th className="px-4 py-2 text-right font-medium text-zinc-600">Total Tax</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-4 py-2">998311</td>
                      <td className="px-4 py-2 text-right">{formatINR(selectedInvoice?.subtotal || 0)}</td>
                      <td className="px-4 py-2 text-center">9%</td>
                      <td className="px-4 py-2 text-right">{formatINR((selectedInvoice?.gst_amount || 0) / 2)}</td>
                      <td className="px-4 py-2 text-center">9%</td>
                      <td className="px-4 py-2 text-right">{formatINR((selectedInvoice?.gst_amount || 0) / 2)}</td>
                      <td className="px-4 py-2 text-right font-medium">{formatINR(selectedInvoice?.gst_amount || 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Terms & Bank Details */}
              <div className="grid grid-cols-2 gap-6">
                <div className="border border-zinc-200 rounded-sm p-4">
                  <h4 className="text-sm font-semibold text-zinc-800 mb-3">Terms of Delivery</h4>
                  <ol className="text-xs text-zinc-600 space-y-2">
                    <li className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-medium">1</span>
                      <span>Payment to be paid via Bank transfer or cheques</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-medium">2</span>
                      <span>Payment refund is not permissible</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-medium">3</span>
                      <span>Any breach of information is subject to violation of agreement</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-medium">4</span>
                      <span>TDS amount to be paid regularly and submit challan to biller</span>
                    </li>
                    <li className="flex gap-2">
                      <span className="flex-shrink-0 w-5 h-5 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-medium">5</span>
                      <span>Disputes subject to Ahmedabad jurisdiction</span>
                    </li>
                  </ol>
                </div>
                
                <div className="border border-zinc-200 rounded-sm p-4 bg-zinc-50">
                  <h4 className="text-sm font-semibold text-zinc-800 mb-3">Bank Details</h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-zinc-200">
                      <span className="text-zinc-500">Bank Name</span>
                      <span className="font-medium">{companyDetails.bankName}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-zinc-200">
                      <span className="text-zinc-500">Account Holder</span>
                      <span className="font-medium">{companyDetails.accountName}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-zinc-200">
                      <span className="text-zinc-500">Account No.</span>
                      <span className="font-medium font-mono">{companyDetails.accountNo}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-zinc-200">
                      <span className="text-zinc-500">Branch & IFSC</span>
                      <span className="font-medium">{companyDetails.branch} | {companyDetails.ifscCode}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-zinc-500">SWIFT Code</span>
                      <span className="font-medium font-mono">{companyDetails.swiftCode}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Signature Section */}
              <div className="flex justify-between items-end pt-6 border-t border-zinc-200">
                <div>
                  <p className="text-xs text-zinc-400">This is a Computer Generated Invoice</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-zinc-700 mb-8">For {companyDetails.name}</p>
                  <div className="border-t border-zinc-300 pt-2">
                    <p className="text-xs text-zinc-500">Authorised Signatory</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-3 mt-4">
            <Button
              onClick={() => setViewDialogOpen(false)}
              variant="outline"
              className="flex-1 rounded-sm"
            >
              Close
            </Button>
            {selectedInvoice?.is_final && (
              <Button
                onClick={() => {
                  setViewDialogOpen(false);
                  navigate(`/sales-funnel/agreements?quotationId=${selectedInvoice.id}&leadId=${selectedInvoice.lead_id}`);
                }}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <ArrowRight className="w-4 h-4 mr-2" />
                Proceed to Agreement
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProformaInvoice;
