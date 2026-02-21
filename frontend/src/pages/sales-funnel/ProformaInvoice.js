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
  Download, Printer, ArrowRight, Building2, Phone, Mail, MapPin, AlertCircle,
  History, Star
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR, numberToWords } from '../../utils/currency';
import SalesFunnelProgress from '../../components/SalesFunnelProgress';
import ViewToggle from '../../components/ViewToggle';

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
  const [viewMode, setViewMode] = useState('card');
  const [activeView, setActiveView] = useState('list'); // 'list' or 'history'
  const [agreements, setAgreements] = useState([]);
  
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
      const [invoicesRes, plansRes, leadsRes, agreementsRes] = await Promise.all([
        axios.get(`${API}/quotations`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/pricing-plans`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/leads`),
        axios.get(`${API}/agreements`).catch(() => ({ data: [] }))
      ]);
      setInvoices(invoicesRes.data);
      setPricingPlans(plansRes.data);
      setLeads(leadsRes.data);
      setAgreements(agreementsRes.data);
      
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
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map(e => e.msg || 'Validation error').join(', '));
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to create proforma invoice');
      }
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
    
    // Generate professional print-ready PDF with proper styling
    const printContent = invoiceRef.current.innerHTML;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Proforma Invoice - ${selectedInvoice?.quotation_number}</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
              margin: 0; 
              padding: 24px; 
              font-size: 11px;
              color: #18181b;
              background: white;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
            }
            .bg-white { background-color: #ffffff !important; }
            .bg-zinc-50 { background-color: #fafafa !important; }
            .bg-zinc-100 { background-color: #f4f4f5 !important; }
            .bg-zinc-900 { background-color: #18181b !important; color: white !important; }
            .bg-blue-50 { background-color: #eff6ff !important; }
            .bg-amber-50 { background-color: #fffbeb !important; }
            .bg-emerald-50 { background-color: #ecfdf5 !important; }
            .bg-emerald-500, .bg-emerald-600 { background-color: #10b981 !important; color: white !important; }
            .text-white { color: white !important; }
            .text-zinc-300, .text-zinc-400 { color: #a1a1aa !important; }
            .text-zinc-500 { color: #71717a !important; }
            .text-zinc-600 { color: #52525b !important; }
            .text-zinc-700 { color: #3f3f46 !important; }
            .text-zinc-800 { color: #27272a !important; }
            .text-zinc-900 { color: #18181b !important; }
            .text-emerald-600, .text-emerald-700 { color: #059669 !important; }
            .text-blue-600, .text-blue-700 { color: #2563eb !important; }
            .text-amber-800, .text-amber-900 { color: #92400e !important; }
            .font-bold { font-weight: 700 !important; }
            .font-semibold { font-weight: 600 !important; }
            .font-medium { font-weight: 500 !important; }
            .text-xs { font-size: 10px !important; }
            .text-sm { font-size: 11px !important; }
            .text-base { font-size: 12px !important; }
            .text-lg { font-size: 14px !important; }
            .text-xl { font-size: 16px !important; }
            .text-2xl { font-size: 18px !important; }
            .text-3xl { font-size: 22px !important; }
            .text-right { text-align: right !important; }
            .text-center { text-align: center !important; }
            .uppercase { text-transform: uppercase !important; }
            .rounded-sm { border-radius: 4px !important; }
            .rounded-full { border-radius: 9999px !important; }
            .border { border: 1px solid #e4e4e7 !important; }
            .border-t { border-top: 1px solid #e4e4e7 !important; }
            .border-b { border-bottom: 1px solid #e4e4e7 !important; }
            .border-t-2 { border-top: 2px solid #18181b !important; }
            .border-zinc-100 { border-color: #f4f4f5 !important; }
            .border-zinc-200 { border-color: #e4e4e7 !important; }
            .border-amber-200 { border-color: #fde68a !important; }
            .border-blue-500 { border-color: #3b82f6 !important; }
            .border-l-4 { border-left: 4px solid !important; }
            .p-2 { padding: 8px !important; }
            .p-3 { padding: 12px !important; }
            .p-4 { padding: 16px !important; }
            .p-6 { padding: 24px !important; }
            .px-2 { padding-left: 8px !important; padding-right: 8px !important; }
            .px-4 { padding-left: 16px !important; padding-right: 16px !important; }
            .py-1 { padding-top: 4px !important; padding-bottom: 4px !important; }
            .py-2 { padding-top: 8px !important; padding-bottom: 8px !important; }
            .py-3 { padding-top: 12px !important; padding-bottom: 12px !important; }
            .pt-2 { padding-top: 8px !important; }
            .pt-6 { padding-top: 24px !important; }
            .mb-2 { margin-bottom: 8px !important; }
            .mb-3 { margin-bottom: 12px !important; }
            .mb-8 { margin-bottom: 32px !important; }
            .mt-1 { margin-top: 4px !important; }
            .mt-2 { margin-top: 8px !important; }
            .mt-3 { margin-top: 12px !important; }
            .mt-4 { margin-top: 16px !important; }
            .gap-2 { gap: 8px !important; }
            .gap-3 { gap: 12px !important; }
            .gap-6 { gap: 24px !important; }
            .gap-8 { gap: 32px !important; }
            .space-y-2 > * + * { margin-top: 8px !important; }
            .space-y-4 > * + * { margin-top: 16px !important; }
            .space-y-6 > * + * { margin-top: 24px !important; }
            .grid { display: grid !important; }
            .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
            .grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)) !important; }
            .col-span-3 { grid-column: span 3 / span 3 !important; }
            .flex { display: flex !important; }
            .flex-shrink-0 { flex-shrink: 0 !important; }
            .items-center { align-items: center !important; }
            .items-start { align-items: flex-start !important; }
            .items-end { align-items: flex-end !important; }
            .justify-between { justify-content: space-between !important; }
            .justify-center { justify-content: center !important; }
            .justify-end { justify-content: flex-end !important; }
            .w-4 { width: 16px !important; }
            .w-5 { width: 20px !important; }
            .w-10 { width: 40px !important; }
            .w-12 { width: 48px !important; }
            .w-72 { width: 288px !important; }
            .w-full { width: 100% !important; }
            .h-4 { height: 16px !important; }
            .h-5 { height: 20px !important; }
            .h-10 { height: 40px !important; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e4e4e7; }
            th { background-color: #fafafa; font-weight: 500; color: #71717a; font-size: 10px; text-transform: uppercase; }
            .inline-flex { display: inline-flex !important; }
            .overflow-hidden { overflow: hidden !important; }
            .tracking-wide { letter-spacing: 0.025em !important; }
            
            /* Logo styling */
            .logo-container { 
              background: linear-gradient(135deg, #18181b 0%, #3f3f46 100%) !important; 
              padding: 24px !important;
              border-radius: 4px 4px 0 0 !important;
            }
            .logo-text {
              font-size: 32px !important;
              font-weight: 800 !important;
              color: white !important;
              letter-spacing: -0.02em !important;
            }
            .logo-registered {
              font-size: 14px !important;
              vertical-align: super !important;
            }
            
            /* Print-specific styles */
            @media print {
              body { 
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
              }
              .page-break { page-break-before: always; }
              .no-break { page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          <div class="invoice-content">
            ${printContent}
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    
    // Wait for content to render before printing
    setTimeout(() => {
      printWindow.print();
    }, 500);
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

  // Check if invoice is used in agreement
  const isUsedInAgreement = (invoiceId) => {
    return agreements.some(a => a.quotation_id === invoiceId);
  };

  // Group invoices by lead for history view
  const groupedByLead = invoices.reduce((acc, invoice) => {
    const key = invoice.lead_id;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(invoice);
    return acc;
  }, {});

  // Sort invoices within each group by created_at (newest first)
  Object.keys(groupedByLead).forEach(leadId => {
    groupedByLead[leadId].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  });

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

  // Get current lead ID from pricing plan
  const currentPlan = pricingPlans.find(p => p.id === pricingPlanIdFromUrl);
  const currentLeadId = currentPlan?.lead_id || leadId;

  return (
    <div className="max-w-6xl mx-auto" data-testid="proforma-invoice-page">
      {/* Progress Bar - Show when we have a pricing plan context */}
      {pricingPlanIdFromUrl && (
        <SalesFunnelProgress
          currentStep={3}
          pricingPlanId={pricingPlanIdFromUrl}
          leadId={currentLeadId}
          quotationId={currentInvoice?.id}
          sowCompleted={!!sowData}
          proformaCompleted={isProformaFinalized}
          agreementCompleted={false}
        />
      )}

      <div className="mb-6">
        {/* Flow Navigation Alert */}
        {pricingPlanIdFromUrl && !hasProformaInvoice && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800">Action Required</p>
              <p className="text-sm text-amber-700 mt-1">
                Create a Proforma Invoice for this pricing plan to proceed to the Agreement step.
              </p>
            </div>
          </div>
        )}

        {/* Success Message when Invoice is Created */}
        {pricingPlanIdFromUrl && hasProformaInvoice && !isProformaFinalized && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-sm flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-800">Proforma Invoice Created</p>
              <p className="text-sm text-blue-700 mt-1">
                Finalize the invoice to proceed to the Agreement step.
              </p>
            </div>
            <Button
              onClick={() => handleFinalize(currentInvoice.id)}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-sm"
            >
              Finalize Now
            </Button>
          </div>
        )}

        {/* Ready for Agreement */}
        {pricingPlanIdFromUrl && isProformaFinalized && (
          <div className="mb-4 p-4 bg-emerald-50 border border-emerald-200 rounded-sm flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-800">Ready for Agreement</p>
              <p className="text-sm text-emerald-700 mt-1">
                Proforma Invoice is finalized. You can now proceed to create the Agreement.
              </p>
            </div>
            <Button
              onClick={() => navigate(`/sales-funnel/agreements?quotationId=${currentInvoice.id}&leadId=${currentLeadId}`)}
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm"
            >
              <ArrowRight className="w-4 h-4 mr-2" />
              Proceed to Agreement
            </Button>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Proforma Invoice
            </h1>
            <p className="text-zinc-500">Create and manage proforma invoices for clients</p>
          </div>
          <div className="flex items-center gap-3">
            <ViewToggle viewMode={viewMode} onChange={setViewMode} />
            {/* Back Button */}
            <Button
              onClick={handleBackToFlow}
              variant="outline"
              className="rounded-sm border-zinc-300"
              data-testid="back-to-flow-btn"
            >
              <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Back to SOW
            </Button>
            
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
          All Invoices
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
      ) : activeView === 'history' ? (
        /* HISTORY VIEW - Grouped by Lead/Prospect */
        <div className="space-y-6" data-testid="history-view">
          {Object.keys(groupedByLead).map(groupLeadId => {
            const lead = leads.find(l => l.id === groupLeadId);
            const invoicesList = groupedByLead[groupLeadId];
            const selectedInvoice = invoicesList.find(inv => isUsedInAgreement(inv.id));
            
            return (
              <Card key={groupLeadId} className="border-zinc-200 shadow-none rounded-sm" data-testid={`lead-group-${groupLeadId}`}>
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
                      <div className="text-lg font-semibold text-zinc-950">{invoicesList.length}</div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-zinc-100">
                    {invoicesList.map((invoice, idx) => {
                      const isLatest = idx === 0;
                      const usedInAgreement = isUsedInAgreement(invoice.id);
                      const versionNumber = invoicesList.length - idx;
                      
                      return (
                        <div 
                          key={invoice.id} 
                          className={`p-4 ${usedInAgreement ? 'bg-emerald-50/50' : isLatest ? 'bg-blue-50/30' : ''}`}
                          data-testid={`history-item-${invoice.id}`}
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
                                <span className="font-medium text-zinc-900">{invoice.quotation_number}</span>
                                <span className="text-sm text-zinc-500 ml-2">
                                  {new Date(invoice.created_at).toLocaleDateString()}
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
                            <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(invoice.status, invoice.is_final)}`}>
                              {invoice.is_final ? 'Finalized' : invoice.status}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-4 gap-4 mb-3">
                            <div>
                              <div className="text-xs text-zinc-500">Meetings</div>
                              <div className="font-semibold">{invoice.total_meetings}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Subtotal</div>
                              <div className="font-semibold">{formatINR(invoice.subtotal)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">GST</div>
                              <div className="font-semibold">{formatINR(invoice.gst_amount)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Total</div>
                              <div className="font-semibold text-emerald-600">{formatINR(invoice.grand_total)}</div>
                            </div>
                          </div>
                          
                          <div className="flex gap-2">
                            <Button
                              onClick={() => openViewDialog(invoice)}
                              size="sm"
                              variant="outline"
                              className="rounded-sm h-8"
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              View
                            </Button>
                            {!invoice.is_final && canEdit && (
                              <Button
                                onClick={() => handleFinalize(invoice.id)}
                                size="sm"
                                variant="outline"
                                className="rounded-sm h-8"
                              >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Finalize
                              </Button>
                            )}
                            {invoice.is_final && canEdit && !usedInAgreement && (
                              <Button
                                onClick={() => navigate(`/sales-funnel/agreements?quotationId=${invoice.id}&leadId=${invoice.lead_id}`)}
                                size="sm"
                                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm h-8"
                              >
                                <Send className="w-4 h-4 mr-1" />
                                Create Agreement
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
      ) : viewMode === 'list' ? (
        /* List View */
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-zinc-50 border-b border-zinc-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Invoice #</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Client</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Meetings</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Grand Total</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {invoices.map((invoice) => (
                <tr 
                  key={invoice.id} 
                  className="hover:bg-zinc-50 cursor-pointer transition-colors"
                  onClick={() => openViewDialog(invoice)}
                  data-testid={`invoice-row-${invoice.id}`}
                >
                  <td className="px-4 py-3">
                    <span className="font-medium text-zinc-900">{invoice.quotation_number}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-600">{getLeadName(invoice.lead_id)}</td>
                  <td className="px-4 py-3 text-sm text-zinc-900 text-right font-medium">{invoice.total_meetings}</td>
                  <td className="px-4 py-3 text-sm text-emerald-600 text-right font-semibold">{formatINR(invoice.grand_total)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(invoice.status, invoice.is_final)}`}>
                      {invoice.is_final ? 'Finalized' : invoice.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex justify-end gap-2">
                      <Button
                        onClick={() => openViewDialog(invoice)}
                        size="sm"
                        variant="outline"
                        className="rounded-sm h-8"
                      >
                        <Eye className="w-3 h-3" />
                      </Button>
                      {invoice.is_final && canEdit && (
                        <Button
                          onClick={() => navigate(`/sales-funnel/agreements?quotationId=${invoice.id}&leadId=${invoice.lead_id}`)}
                          size="sm"
                          className="bg-zinc-900 text-white hover:bg-zinc-800 rounded-sm h-8"
                        >
                          <ArrowRight className="w-3 h-3" />
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
                      Plan #{plan.id.slice(-6).toUpperCase()} • {plan.project_duration_months} months ({plan.project_duration_type}) • {formatINR(plan.total_amount || plan.total_investment || calculatePlanTotals(plan).subtotal)}
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
                className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
                data-testid="create-invoice-submit"
              >
                <ArrowRight className="w-4 h-4 mr-2" />
                Save & Create Invoice
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
            {/* Header with gradient accent and Logo */}
            <div className="logo-container bg-gradient-to-r from-zinc-900 to-zinc-700 text-white p-6 rounded-t-sm">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-4">
                  {/* Company Logo/Icon */}
                  <div className="w-16 h-16 bg-white rounded-sm flex items-center justify-center shadow-lg">
                    <span className="text-3xl font-black text-zinc-900 tracking-tighter">D&V</span>
                  </div>
                  <div>
                    <h1 className="logo-text text-3xl font-bold tracking-tight">
                      D&V<span className="logo-registered text-sm align-super">®</span>
                    </h1>
                    <p className="text-zinc-300 text-sm mt-1">Business Consulting</p>
                  </div>
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
