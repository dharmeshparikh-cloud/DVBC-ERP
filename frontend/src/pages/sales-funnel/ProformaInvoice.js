import React, { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';
import { 
  ArrowLeft, Plus, FileText, CheckCircle, Clock, Send, Users, Eye, 
  Download, Printer, ArrowRight, Building2, Phone, Mail, MapPin, AlertCircle,
  History, Star, Lock, Info
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR, numberToWords } from '../../utils/currency';
import { validateGSTIN, matchGSTINCompany } from '../../utils/gstin';
import FunnelStepperHeader from '../../components/FunnelStepperHeader';
import ViewToggle from '../../components/ViewToggle';
import PageHeader from '../../components/ui/page-header';
import { useFetch, useMutate } from '../../hooks/useApi';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import LeadSelector from '../../components/LeadSelector';
import { useFunnelEligibility, getFunnelTooltip } from '../../hooks/useFunnelEligibility';
import { ProformaInvoiceTable } from '../../components/sales';

const API = process.env.REACT_APP_BACKEND_URL;

const ProformaInvoice = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const pricingPlanIdFromUrl = searchParams.get('pricing_plan_id');
  const invoiceRef = useRef(null);
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [selectedPlanDetails, setSelectedPlanDetails] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [autoOpenHandled, setAutoOpenHandled] = useState(false);
  const [viewMode, setViewMode] = useState('list');
  
  // Check if there are eligible leads (with SOW - enforced before quotation)
  const { hasEligibleLeads, isLoading: eligibilityLoading } = useFunnelEligibility('has_sow');
  
  // Auto-switch to card view on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setViewMode('card');
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [activeView, setActiveView] = useState('list'); // 'list' or 'history'
  
  const [formData, setFormData] = useState({
    pricing_plan_id: pricingPlanIdFromUrl || '',
    lead_id: leadId || '',
    base_rate_per_meeting: 12500,
    validity_days: 30,
    payment_terms: 'ADVANCE',
    client_gstin: '',
    terms_and_conditions: '1) Payment to be paid via Bank transfer or cheques\n2) Payment refund is not permissible\n3) Any breach of information is subject to violation of agreement\n4) TDS amount to be paid regularly and submit challan to biller\n5) Disputes subject to Ahmedabad jurisdiction.'
  });

  // SSOT: Track selected lead master data for display
  const [selectedLeadMasterData, setSelectedLeadMasterData] = useState(null);

  // GSTIN validation state
  const [gstinValidation, setGstinValidation] = useState(null);

  // Validate GSTIN whenever it changes
  useEffect(() => {
    const gstin = formData.client_gstin;
    if (!gstin || gstin.length === 0) {
      setGstinValidation(null);
      return;
    }
    const result = validateGSTIN(gstin);
    if (result.valid) {
      const companyName = selectedLeadMasterData?.company || selectedLead?.company || '';
      const companyMatch = matchGSTINCompany(gstin, companyName);
      setGstinValidation({ ...result, companyMatch });
    } else {
      setGstinValidation(result);
    }
  }, [formData.client_gstin, selectedLeadMasterData, selectedLead]);

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

  // Query: Fetch invoices (quotations) using React Query - API returns paginated {data: [...]}
  const { data: invoicesData, isLoading: invoicesLoading, refetch: refetchInvoices } = useFetch('/api/quotations', {
    params: leadId ? { lead_id: leadId } : {}
  });
  const invoices = Array.isArray(invoicesData?.data) ? invoicesData.data : (Array.isArray(invoicesData) ? invoicesData : []);

  // Query: Fetch pricing plans
  const { data: pricingPlansData } = useFetch('/api/pricing-plans', {
    params: leadId ? { lead_id: leadId } : {}
  });
  const pricingPlans = Array.isArray(pricingPlansData?.data) ? pricingPlansData.data : (Array.isArray(pricingPlansData) ? pricingPlansData : []);

  // Query: Fetch leads - API returns {data: [...], total, ...}
  const { data: leadsData } = useFetch('/api/leads');
  const leads = Array.isArray(leadsData?.data) ? leadsData.data : (Array.isArray(leadsData?.items) ? leadsData.items : (Array.isArray(leadsData) ? leadsData : []));

  // Query: Fetch agreements - API returns paginated {data: [...]}
  const { data: agreementsData } = useFetch('/api/agreements');
  const agreements = Array.isArray(agreementsData?.data) ? agreementsData.data : (Array.isArray(agreementsData) ? agreementsData : []);

  // Query: Fetch SOW data if we have a pricing plan ID
  const { data: sowData } = useFetch(
    pricingPlanIdFromUrl ? `/api/enhanced-sow/by-pricing-plan/${pricingPlanIdFromUrl}` : null,
    { enabled: !!pricingPlanIdFromUrl }
  );

  const loading = invoicesLoading;

  // Auto-open dialog with pre-selected plan when coming from SOW selection
  useEffect(() => {
    if (!loading && pricingPlanIdFromUrl && !autoOpenHandled && pricingPlans.length > 0) {
      const plan = (pricingPlans || []).find(p => p.id === pricingPlanIdFromUrl);
      if (plan) {
        setSelectedPlanDetails(plan);
        const lead = (leads || []).find(l => l.id === plan.lead_id);
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

  // Check if proforma invoice exists for current pricing plan
  const currentInvoice = (invoices || []).find(inv => inv.pricing_plan_id === pricingPlanIdFromUrl);
  const hasProformaInvoice = !!currentInvoice;

  const handlePlanSelect = (planId) => {
    const plan = (pricingPlans || []).find(p => p.id === planId);
    setSelectedPlanDetails(plan);
    setFormData({ ...formData, pricing_plan_id: planId });
  };

  const handleLeadSelect = (selectedLeadId) => {
    const lead = (leads || []).find(l => l.id === selectedLeadId);
    setSelectedLead(lead);
    setFormData({ ...formData, lead_id: selectedLeadId, pricing_plan_id: '' });
    setSelectedPlanDetails(null);
  };

  // Mutation: Create proforma invoice
  const createInvoiceMutation = useMutation({
    mutationFn: async (data) => {
      if (selectedInvoice?.id) {
        // Update existing quotation
        return axios.put(`${API}/api/quotations/${selectedInvoice.id}`, data);
      }
      return axios.post(`${API}/api/quotations`, data);
    },
    onSuccess: () => {
      toast.success(selectedInvoice?.id ? 'Proforma Invoice updated successfully' : 'Proforma Invoice created successfully');
      setDialogOpen(false);
      setSelectedPlanDetails(null);
      setSelectedInvoice(null);
      queryClient.invalidateQueries({ queryKey: ['/api/quotations'] });
      refetchInvoices();
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      
      // Handle SOW_REQUIRED error - redirect to SOW Builder
      if (typeof detail === 'string' && (detail.includes('SOW_REQUIRED') || detail.includes('SOW_EMPTY'))) {
        toast.error('Scope of Work is required before creating a Quotation');
        setDialogOpen(false);
        // Get redirect URL from header or construct it
        const redirectUrl = error.response?.headers?.['x-redirect-to'];
        if (redirectUrl) {
          navigate(redirectUrl);
        } else if (formData.pricing_plan_id) {
          navigate(`/sales-funnel/sow/${formData.pricing_plan_id}?lead_id=${formData.lead_id}`);
        } else {
          navigate('/sales-funnel/sow-list');
        }
        return;
      }
      
      if (Array.isArray(detail)) {
        toast.error((detail || []).map(e => e.msg || 'Validation error').join(', '));
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to save proforma invoice');
      }
    }
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    createInvoiceMutation.mutate(formData);
  };

  // Version label — show version number for each invoice
  const getVersionLabel = (invoice) => {
    const version = invoice.version || 1;
    return `v${version}`;
  };

  const openViewDialog = (invoice) => {
    const plan = (pricingPlans || []).find(p => p.id === invoice.pricing_plan_id);
    const lead = (leads || []).find(l => l.id === invoice.lead_id);
    setSelectedInvoice(invoice);
    setSelectedPlanDetails(plan);
    setSelectedLead(lead);
    setViewDialogOpen(true);
  };

  // Generate a self-contained printable invoice HTML from data (no DOM dependency)
  const buildInvoiceHTML = (invoice, lead, plan) => {
    const fmtINR = (amt) => {
      const n = Number(amt || 0);
      return '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    const fmtDate = (d) => {
      const dt = new Date(d || new Date());
      return dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
    };
    const subtotal = invoice?.subtotal || 0;
    const taxAmt = invoice?.gst_amount || invoice?.tax_amount || 0;
    const grandTotal = invoice?.grand_total || invoice?.total || (subtotal + taxAmt);
    const halfTax = taxAmt / 2;
    const teamData = (plan?.team_deployment || plan?.consultants || []);
    const totalMeetings = invoice?.total_meetings || teamData.reduce((s, m) => s + ((m.committed_meetings || m.meetings || 0) * (m.count || 1)), 0);
    const duration = plan?.project_duration_months || 12;
    const logoUrl = window.location.origin + '/assets/dv-logo.png';
    const validUntil = invoice?.valid_until ? fmtDate(invoice.valid_until) : fmtDate(new Date(new Date(invoice?.created_at).getTime() + (invoice?.validity_days || 30)*86400000));
    const clientGstin = invoice?.client_gstin || lead?.gstin || '';

    // Extract GSTIN details for Bill To section (inline - no imports needed in HTML builder)
    const gstinStateCode = clientGstin.length === 15 ? clientGstin.substring(0, 2) : '';
    const STATE_CODES = {'01':'Jammu & Kashmir','02':'Himachal Pradesh','03':'Punjab','04':'Chandigarh','05':'Uttarakhand','06':'Haryana','07':'Delhi','08':'Rajasthan','09':'Uttar Pradesh','10':'Bihar','11':'Sikkim','12':'Arunachal Pradesh','13':'Nagaland','14':'Manipur','15':'Mizoram','16':'Tripura','17':'Meghalaya','18':'Assam','19':'West Bengal','20':'Jharkhand','21':'Odisha','22':'Chhattisgarh','23':'Madhya Pradesh','24':'Gujarat','25':'Daman & Diu','26':'Dadra & Nagar Haveli','27':'Maharashtra','28':'Andhra Pradesh','29':'Karnataka','30':'Goa','31':'Lakshadweep','32':'Kerala','33':'Tamil Nadu','34':'Puducherry','35':'Andaman & Nicobar','36':'Telangana','37':'Andhra Pradesh (New)','38':'Ladakh'};
    const gstinStateName = STATE_CODES[gstinStateCode] || '';
    const gstinPan = clientGstin.length === 15 ? clientGstin.substring(2, 12) : '';
    const PAN_TYPES = {'C':'Company','P':'Individual','H':'HUF','F':'Firm','A':'AOP','T':'Trust'};
    const gstinEntityType = gstinPan.length === 10 ? (PAN_TYPES[gstinPan[3]] || '') : '';

    // Parse terms
    const termsText = invoice?.terms_and_conditions || '1) Payment via Bank transfer or cheques only\n2) Payment refund is not permissible\n3) Breach of information subject to agreement violation\n4) TDS to be paid regularly; submit challan to biller\n5) Disputes subject to Ahmedabad jurisdiction';
    const termsLines = termsText.split('\n').map(t => t.replace(/^\d+\)\s*/, '').trim()).filter(Boolean);

    // Team rows HTML
    const teamRows = teamData.map(m => `
      <tr style="border-bottom:1px solid #f4f4f5;">
        <td style="padding:6px 0;font-weight:500;color:#09090b;">${m.role || m.consultant_type || '-'}</td>
        <td style="padding:6px 0;color:#52525b;">${m.meeting_type || m.frequency || '-'}</td>
        <td style="padding:6px 0;text-align:center;color:#3f3f46;">${m.count || 1}</td>
        <td style="padding:6px 0;text-align:center;font-weight:600;color:#09090b;">${(m.committed_meetings || m.meetings || 0) * (m.count || 1)}</td>
      </tr>
    `).join('');

    return `<!DOCTYPE html>
<html>
<head>
  <title>Proforma Invoice - ${invoice?.quotation_number || ''}</title>
  <style>
    @page { size: A4; margin: 12mm 14mm; }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; font-size:10px; color:#09090b; background:#fff; -webkit-print-color-adjust:exact!important; print-color-adjust:exact!important; }
    table { width:100%; border-collapse:collapse; }
    img { display:block; }
  </style>
</head>
<body>
  <!-- Header -->
  <div style="padding:20px 24px 16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <img src="${logoUrl}" alt="D&V" style="height:56px;width:auto;" />
      <div style="text-align:right;">
        <h2 style="font-size:16px;font-weight:900;letter-spacing:-0.025em;text-transform:uppercase;color:#09090b;">Proforma Invoice</h2>
        <p style="font-size:10px;color:#71717a;font-family:'Courier New',monospace;margin-top:2px;">${invoice?.quotation_number || ''}${(invoice?.version || 1) > 1 ? ' v' + invoice.version : ''}</p>
      </div>
    </div>
    <div style="margin-top:12px;height:1px;background:#09090b;"></div>
  </div>

  <div style="padding:0 24px 20px;">
    <!-- 3 column: Invoice Details | Bill To | From -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;font-size:10px;">
      <div>
        <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;">Invoice Details</h3>
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">No.</span><span style="font-weight:600;color:#09090b;font-family:'Courier New',monospace;">${invoice?.quotation_number || ''}</span></div>
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">Date</span><span style="color:#3f3f46;">${fmtDate(invoice?.created_at)}</span></div>
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">Terms</span><span style="font-weight:600;color:#09090b;text-transform:uppercase;">${invoice?.payment_terms || 'ADVANCE'}</span></div>
        <div style="display:flex;justify-content:space-between;"><span style="color:#a1a1aa;">Valid Until</span><span style="color:#3f3f46;">${validUntil}</span></div>
      </div>
      <div>
        <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;">Bill To</h3>
        <div style="border-left:2px solid #09090b;padding-left:12px;">
          <p style="font-weight:700;color:#09090b;font-size:12px;">${lead?.company || invoice?.client_name || 'Client'}</p>
          ${clientGstin ? `
            <p style="color:#71717a;font-family:'Courier New',monospace;margin-top:4px;">GSTIN: ${clientGstin}</p>
            ${gstinEntityType ? `<p style="color:#a1a1aa;font-size:9px;">Entity: ${gstinEntityType} | PAN: ${gstinPan}</p>` : ''}
          ` : ''}
          <p style="color:#a1a1aa;">${gstinStateName ? `State: ${gstinStateName} | Code: ${gstinStateCode}` : 'State: Gujarat | Code: 24'}</p>
        </div>
      </div>
      <div>
        <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;">From</h3>
        <p style="font-weight:700;color:#09090b;font-size:12px;">${companyDetails.name}</p>
        <p style="color:#a1a1aa;margin-top:2px;">${companyDetails.address}</p>
        <p style="color:#71717a;font-family:'Courier New',monospace;margin-top:2px;">GSTIN: ${companyDetails.gstin}</p>
        <p style="color:#a1a1aa;">State: ${companyDetails.state} | Code: ${companyDetails.stateCode}</p>
      </div>
    </div>

    <!-- Pricing Summary -->
    <div style="margin-top:16px;">
      <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;">Pricing Summary</h3>
      <table style="font-size:10px;">
        <thead>
          <tr style="border-bottom:2px solid #09090b;">
            <th style="text-align:left;padding:6px 0;font-size:9px;font-weight:700;color:#71717a;text-transform:uppercase;">Description</th>
            <th style="text-align:center;padding:6px 0;font-size:9px;font-weight:700;color:#71717a;text-transform:uppercase;">HSN/SAC</th>
            <th style="text-align:center;padding:6px 0;font-size:9px;font-weight:700;color:#71717a;text-transform:uppercase;">Period</th>
            <th style="text-align:right;padding:6px 0;font-size:9px;font-weight:700;color:#71717a;text-transform:uppercase;">Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom:1px solid #f4f4f5;">
            <td style="padding:8px 0;">
              <div style="font-weight:500;color:#09090b;">Management Consulting Services &mdash; Professional Fees</div>
              <div style="font-size:9px;color:#a1a1aa;">${duration} months engagement</div>
            </td>
            <td style="padding:8px 0;text-align:center;color:#71717a;font-family:'Courier New',monospace;">998311</td>
            <td style="padding:8px 0;text-align:center;color:#71717a;">${duration} Months</td>
            <td style="padding:8px 0;text-align:right;font-weight:600;color:#09090b;">${fmtINR(subtotal)}</td>
          </tr>
        </tbody>
      </table>
      <!-- Tax & Total -->
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid #e4e4e7;">
        <div style="display:flex;justify-content:flex-end;">
          <div style="width:224px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">Subtotal</span><span style="font-weight:500;color:#3f3f46;">${fmtINR(subtotal)}</span></div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">CGST @ 9%</span><span style="color:#52525b;">${fmtINR(halfTax)}</span></div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">SGST @ 9%</span><span style="color:#52525b;">${fmtINR(halfTax)}</span></div>
            <div style="display:flex;justify-content:space-between;padding-bottom:4px;border-bottom:1px solid #e4e4e7;"><span style="color:#a1a1aa;">Total Tax (18%)</span><span style="font-weight:500;color:#3f3f46;">${fmtINR(taxAmt)}</span></div>
            <div style="display:flex;justify-content:space-between;padding-top:4px;border-top:2px solid #09090b;">
              <span style="font-weight:900;color:#09090b;font-size:12px;">GRAND TOTAL</span>
              <span style="font-weight:900;color:#09090b;font-size:12px;">${fmtINR(grandTotal)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Amount in Words -->
    <div style="margin-top:16px;border:1px solid #e4e4e7;padding:8px 12px;">
      <p style="font-size:10px;"><span style="font-weight:600;color:#71717a;font-size:9px;text-transform:uppercase;letter-spacing:0.05em;">Amount in Words:</span><span style="color:#09090b;margin-left:8px;font-weight:500;">${numberToWords(grandTotal)}</span></p>
    </div>

    <!-- HSN/SAC Summary -->
    <div style="margin-top:16px;">
      <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:4px;">HSN/SAC Summary</h3>
      <table style="font-size:9px;">
        <thead>
          <tr style="border-bottom:1px solid #09090b;">
            <th style="padding:4px 8px;text-align:left;font-weight:700;color:#71717a;text-transform:uppercase;">HSN/SAC</th>
            <th style="padding:4px 8px;text-align:right;font-weight:700;color:#71717a;text-transform:uppercase;">Taxable Value</th>
            <th style="padding:4px 8px;text-align:center;font-weight:700;color:#71717a;text-transform:uppercase;">CGST</th>
            <th style="padding:4px 8px;text-align:right;font-weight:700;color:#71717a;text-transform:uppercase;">CGST Amt</th>
            <th style="padding:4px 8px;text-align:center;font-weight:700;color:#71717a;text-transform:uppercase;">SGST</th>
            <th style="padding:4px 8px;text-align:right;font-weight:700;color:#71717a;text-transform:uppercase;">SGST Amt</th>
            <th style="padding:4px 8px;text-align:right;font-weight:700;color:#71717a;text-transform:uppercase;">Total Tax</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding:4px 8px;font-family:'Courier New',monospace;">998311</td>
            <td style="padding:4px 8px;text-align:right;">${fmtINR(subtotal)}</td>
            <td style="padding:4px 8px;text-align:center;">9%</td>
            <td style="padding:4px 8px;text-align:right;">${fmtINR(halfTax)}</td>
            <td style="padding:4px 8px;text-align:center;">9%</td>
            <td style="padding:4px 8px;text-align:right;">${fmtINR(halfTax)}</td>
            <td style="padding:4px 8px;text-align:right;font-weight:600;">${fmtINR(taxAmt)}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Payment T&C + Bank Details -->
    <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:24px;">
      <div style="border:1px solid #d4d4d8;padding:12px;">
        <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;">Payment Terms & Conditions</h3>
        <ol style="font-size:9px;color:#52525b;list-style:none;padding:0;">
          ${termsLines.map((t, i) => `<li style="margin-bottom:3px;display:flex;gap:6px;"><span style="color:#a1a1aa;font-family:'Courier New',monospace;">${i+1}.</span><span>${t}</span></li>`).join('')}
        </ol>
      </div>
      <div style="border:1px solid #d4d4d8;padding:12px;">
        <h3 style="font-size:9px;font-weight:700;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;">Bank Details</h3>
        <div style="font-size:9px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">Bank</span><span style="font-weight:500;color:#3f3f46;font-family:'Courier New',monospace;">${companyDetails.bankName}</span></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">A/c Holder</span><span style="font-weight:500;color:#3f3f46;font-family:'Courier New',monospace;">${companyDetails.accountName}</span></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">A/c No.</span><span style="font-weight:500;color:#3f3f46;font-family:'Courier New',monospace;">${companyDetails.accountNo}</span></div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#a1a1aa;">Branch & IFSC</span><span style="font-weight:500;color:#3f3f46;font-family:'Courier New',monospace;">${companyDetails.branch} | ${companyDetails.ifscCode}</span></div>
          <div style="display:flex;justify-content:space-between;"><span style="color:#a1a1aa;">SWIFT</span><span style="font-weight:500;color:#3f3f46;font-family:'Courier New',monospace;">${companyDetails.swiftCode}</span></div>
        </div>
      </div>
    </div>

    <!-- Signature -->
    <div style="display:flex;justify-content:space-between;align-items:flex-end;padding-top:16px;margin-top:16px;border-top:1px solid #e4e4e7;">
      <p style="font-size:9px;color:#d4d4d8;text-transform:uppercase;letter-spacing:0.05em;">Computer Generated Invoice</p>
      <div style="text-align:right;">
        <p style="font-size:9px;font-weight:600;color:#3f3f46;margin-bottom:24px;">For ${companyDetails.name}</p>
        <div style="border-top:1px solid #09090b;padding-top:4px;width:160px;margin-left:auto;">
          <p style="font-size:9px;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.05em;">Authorised Signatory</p>
        </div>
      </div>
    </div>
  </div>
</body>
</html>`;
  };

  const handleDownloadPDF = (invoiceOverride, leadOverride, planOverride) => {
    const inv = invoiceOverride || selectedInvoice;
    const ld = leadOverride || selectedLead;
    const pl = planOverride || selectedPlanDetails;
    if (!inv) return;

    const html = buildInvoiceHTML(inv, ld, pl);
    const printWindow = window.open('', '_blank');
    printWindow.document.write(html);
    printWindow.document.close();

    const checkImagesAndPrint = () => {
      const imgs = printWindow.document.querySelectorAll('img');
      let allLoaded = true;
      imgs.forEach(img => { if (!img.complete) allLoaded = false; });
      if (allLoaded) {
        printWindow.print();
      } else {
        setTimeout(checkImagesAndPrint, 200);
      }
    };
    setTimeout(checkImagesAndPrint, 400);
  };

  // Standalone PDF from table row (no dialog needed)
  const handleTablePDF = (invoice) => {
    const plan = (pricingPlans || []).find(p => p.id === invoice.pricing_plan_id);
    const lead = (leads || []).find(l => l.id === invoice.lead_id);
    handleDownloadPDF(invoice, lead, plan);
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
    const lead = (leads || []).find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Unknown Lead';
  };

  const canEdit = user?.role !== 'manager';

  const calculatePlanTotals = (plan) => {
    if (!plan) return { totalMeetings: 0, subtotal: 0 };
    const teamData = plan.team_deployment?.length > 0 ? plan.team_deployment : plan.consultants;
    if (!teamData || teamData.length === 0) return { totalMeetings: 0, subtotal: 0 };
    
    const totalMeetings = (teamData || []).reduce((sum, m) => {
      const meetings = m.committed_meetings || m.meetings || 0;
      const count = m.count || 1;
      return sum + (meetings * count);
    }, 0);
    
    const subtotal = (teamData || []).reduce((sum, m) => {
      const meetings = m.committed_meetings || m.meetings || 0;
      const count = m.count || 1;
      const rate = m.rate_per_meeting || 12500;
      return sum + (meetings * count * rate);
    }, 0);
    
    return { totalMeetings, subtotal };
  };

  // Navigate back to previous step in flow
  const handleBackToFlow = () => {
    if (currentLeadId) {
      navigate(`/sales-funnel-onboarding?leadId=${currentLeadId}`);
    } else if (pricingPlanIdFromUrl) {
      navigate(`/sales-funnel/sow/${pricingPlanIdFromUrl}`);
    } else {
      navigate('/sales-funnel/pricing-plans');
    }
  };

  // Check if invoice is used in agreement
  const isUsedInAgreement = (invoiceId) => {
    return (agreements || []).some(a => a.quotation_id === invoiceId);
  };

  // Group invoices by lead for history view
  const groupedByLead = (invoices || []).reduce((acc, invoice) => {
    const key = invoice.lead_id;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(invoice);
    return acc;
  }, {});

  // Sort invoices within each group by created_at (newest first)
  Object.keys(groupedByLead || {}).forEach(leadId => {
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
  const currentPlan = (pricingPlans || []).find(p => p.id === pricingPlanIdFromUrl);
  const currentLeadId = currentPlan?.lead_id || leadId;

  return (
    <div className="max-w-6xl mx-auto" data-testid="proforma-invoice-page">
      {/* 9-Step Funnel Stepper */}
      {currentLeadId && (
        <FunnelStepperHeader leadId={currentLeadId} currentStepId="quotation" />
      )}

      <div className="mb-6">
        {/* Flow Navigation Alert - No invoice yet */}
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

        {/* Invoice created — proceed to Agreement */}
        {pricingPlanIdFromUrl && hasProformaInvoice && (
          <div className="mb-4 p-4 bg-emerald-50 border border-emerald-200 rounded-sm flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-800">Proforma Invoice Created</p>
              <p className="text-sm text-emerald-700 mt-1">
                You can now proceed to create the Agreement.
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

        <PageHeader
          title="Proforma Invoice"
          subtitle="Create and manage proforma invoices for clients"
          onRefresh={() => refetchInvoices()}
          loading={invoicesLoading}
          actions={<>
            <ViewToggle viewMode={viewMode} onChange={setViewMode} />
            <Button onClick={handleBackToFlow} variant="outline" className="rounded-sm border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800" data-testid="back-to-flow-btn">
              <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} /> Back to Funnel
            </Button>
            {canEdit && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Button 
                        onClick={() => { setSelectedPlanDetails(null); setSelectedLead(null); setDialogOpen(true); }} 
                        data-testid="create-invoice-btn" 
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={!hasEligibleLeads || eligibilityLoading}
                      >
                        <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> Create Proforma Invoice
                        {!hasEligibleLeads && !eligibilityLoading && <Info className="w-3 h-3 ml-1 text-amber-300" />}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!hasEligibleLeads && !eligibilityLoading && (
                    <TooltipContent side="bottom" className="bg-zinc-900 text-white border-zinc-700 max-w-xs">
                      <p className="text-sm">{getFunnelTooltip('has_sow')}</p>
                      <p className="text-xs text-zinc-400 mt-1">Go to SOW Builder → Define scope items first</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            )}
          </>}
        />
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
          {Object.keys(groupedByLead || {}).map(groupLeadId => {
            const lead = (leads || []).find(l => l.id === groupLeadId);
            const invoicesList = groupedByLead[groupLeadId];
            const selectedInvoice = (invoicesList || []).find(inv => isUsedInAgreement(inv.id));
            
            return (
              <Card key={groupLeadId} className="border-zinc-200 shadow-none rounded-sm" data-testid={`lead-group-${groupLeadId}`}>
                <CardHeader className="bg-zinc-50 border-b border-zinc-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Building2 className="w-5 h-5 text-zinc-500" />
                      <div>
                        <CardTitle className="text-lg font-semibold text-zinc-950">
                          {lead ? `${lead.first_name} ${lead.last_name}` : (invoicesList[0]?.client_name || 'Unknown Lead')}
                        </CardTitle>
                        <p className="text-sm text-zinc-500">{lead?.company || invoicesList[0]?.client_name || 'No company'}</p>
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
                    {(invoicesList || []).map((invoice, idx) => {
                      const isLatest = idx === 0;
                      const usedInAgreement = isUsedInAgreement(invoice.id);
                      const versionNumber = invoicesList.length - idx;
                      const hasSow = invoice.has_sow !== false; // Legacy quotations without SOW flag
                      
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
                              {!hasSow && (
                                <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-sm bg-amber-100 text-amber-700 border border-amber-200">
                                  <AlertCircle className="w-3 h-3" />
                                  No SOW
                                </span>
                              )}
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
                              {invoice.status}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-4 gap-4 mb-3">
                            <div>
                              <div className="text-xs text-zinc-500">Meetings</div>
                              <div className="font-semibold">{invoice.total_meetings || '-'}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Subtotal</div>
                              <div className="font-semibold">{formatINR(invoice.subtotal)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">GST</div>
                              <div className="font-semibold">{formatINR(invoice.gst_amount || invoice.tax_amount || 0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500">Total</div>
                              <div className="font-semibold text-emerald-600">{formatINR(invoice.grand_total || invoice.total || ((invoice.subtotal || 0) + (invoice.tax_amount || 0)))}</div>
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
                            {isLatest && canEdit && !usedInAgreement && (
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
        /* List View - Using SalesDataTable (GOVERNANCE: No manual tables) */
        <ProformaInvoiceTable
          leadId={leadId}
          onView={(invoice) => openViewDialog(invoice)}
          onEdit={(invoice) => {
            setSelectedInvoice(invoice);
            const plan = (pricingPlans || []).find(p => p.id === invoice.pricing_plan_id);
            setSelectedPlanDetails(plan);
            const lead = (leads || []).find(l => l.id === invoice.lead_id);
            setSelectedLead(lead);
            setFormData({
              pricing_plan_id: invoice.pricing_plan_id || '',
              lead_id: invoice.lead_id || '',
              base_rate_per_meeting: invoice.base_rate_per_meeting || 12500,
              validity_days: invoice.validity_days || 30,
              payment_terms: invoice.payment_terms || 'ADVANCE',
              client_gstin: invoice.client_gstin || '',
              terms_and_conditions: invoice.terms_and_conditions || ''
            });
            setDialogOpen(true);
          }}
          onDownload={(invoice) => handleTablePDF(invoice)}
          onSend={(invoice) => {
            openViewDialog(invoice);
          }}
          onPrint={(invoice) => handleTablePDF(invoice)}
          className="border border-zinc-200 rounded-sm"
        />
      ) : (
        <div className="space-y-4">
          {(invoices || []).map((invoice) => (
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
                      {invoice.status}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</div>
                    <div className="text-lg font-semibold text-zinc-950">{invoice.total_meetings || '-'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Subtotal</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(invoice.subtotal)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">GST (18%)</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(invoice.gst_amount || invoice.tax_amount || 0)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Grand Total</div>
                    <div className="text-lg font-semibold text-emerald-600">{formatINR(invoice.grand_total || invoice.total || ((invoice.subtotal || 0) + (invoice.tax_amount || 0)))}</div>
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
                  {canEdit && (
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
            {/* SSOT: Lead Selection using LeadSelector component */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                Lead / Company *
                {formData.lead_id && <Lock className="w-3 h-3 text-amber-500" />}
              </Label>
              <LeadSelector
                value={formData.lead_id}
                onChange={(leadId) => {
                  const lead = (leads || []).find(l => l.id === leadId);
                  setSelectedLead(lead);
                  setFormData({ ...formData, lead_id: leadId, pricing_plan_id: '' });
                  setSelectedPlanDetails(null);
                }}
                onMasterDataLoad={(masterData) => {
                  setSelectedLeadMasterData(masterData);
                  // Auto-populate GSTIN from lead if available and field is empty
                  if (masterData?.gstin && !formData.client_gstin) {
                    setFormData(prev => ({ ...prev, client_gstin: masterData.gstin }));
                  }
                }}
                required={true}
                placeholder="Search for a lead with pricing plan..."
                funnelStage="has_pricing_plan"
                noEligibleMessage="No leads with pricing plans found"
                disabled={!!currentLeadId}
              />
              {currentLeadId && (
                <p className="text-xs text-zinc-400 mt-1">Lead auto-selected from funnel flow</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Pricing Plan *</Label>
              <select
                value={formData.pricing_plan_id}
                onChange={(e) => handlePlanSelect(e.target.value)}
                required
                disabled={!formData.lead_id || !!pricingPlanIdFromUrl}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm disabled:bg-zinc-100 disabled:cursor-not-allowed"
                data-testid="pricing-plan-select"
              >
                <option value="">{formData.lead_id ? 'Select a pricing plan' : 'Select a lead first'}</option>
                {(pricingPlans || []).filter(p => !formData.lead_id || p.lead_id === formData.lead_id).map(plan => (
                  <option key={plan.id} value={plan.id}>
                    Plan #{plan.id.slice(-6).toUpperCase()} • {plan.project_duration_months} months ({plan.project_duration_type}) • {formatINR(plan.total_amount || plan.total_investment || calculatePlanTotals(plan).subtotal)}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Show Team Deployment from selected Pricing Plan */}
            {selectedPlanDetails && (
              <div className="border border-blue-200 rounded-sm p-4 bg-blue-50 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-blue-700">
                  <Users className="w-4 h-4" />
                  Team Deployment (from Pricing Plan)
                  <Lock className="w-3 h-3 text-amber-500" />
                </div>
                <div className="text-xs text-blue-600 mb-2">
                  Duration: {selectedPlanDetails.project_duration_months} months ({selectedPlanDetails.project_duration_type?.replace('_', ' ')})
                </div>
                
                {(selectedPlanDetails.team_deployment?.length > 0 || selectedPlanDetails.consultants?.length > 0) ? (
                  <div className="space-y-1">
                    <div className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-3'} gap-2 text-xs font-medium text-blue-600 px-2`}>
                      <div>Role</div>
                      <div>Meeting Type</div>
                      {user?.role === 'admin' && <div>Rate</div>}
                      <div className="text-center">Meetings</div>
                      {user?.role === 'admin' && <div className="text-right">Subtotal</div>}
                    </div>
                    {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants).map((member, idx) => {
                      const meetings = (member.committed_meetings || member.meetings || 0) * (member.count || 1);
                      const cost = meetings * (member.rate_per_meeting || 12500);
                      return (
                        <div key={idx} className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-3'} gap-2 text-xs px-2 py-1 bg-white rounded-sm`}>
                          <div className="truncate">{member.role || member.consultant_type}</div>
                          <div className="truncate">{member.meeting_type || '-'}</div>
                          {user?.role === 'admin' && <div>{formatINR(member.rate_per_meeting || 12500)}</div>}
                          <div className="text-center font-semibold text-blue-700">{meetings}</div>
                          {user?.role === 'admin' && <div className="text-right font-semibold text-emerald-700">{formatINR(cost)}</div>}
                        </div>
                      );
                    })}
                    <div className={`grid ${user?.role === 'admin' ? 'grid-cols-5' : 'grid-cols-3'} gap-2 text-xs font-semibold px-2 pt-2 border-t border-blue-200`}>
                      <div className={user?.role === 'admin' ? 'col-span-2' : 'col-span-1'} />
                      {user?.role === 'admin' && <div />}
                      <div className="text-center text-blue-700">{calculatePlanTotals(selectedPlanDetails).totalMeetings}</div>
                      {user?.role === 'admin' && <div className="text-right text-emerald-700">{formatINR(calculatePlanTotals(selectedPlanDetails).subtotal)}</div>}
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
              <Label className="text-sm font-medium text-zinc-950">Client GSTIN</Label>
              <div className="relative">
                <Input
                  value={formData.client_gstin}
                  onChange={(e) => setFormData({ ...formData, client_gstin: e.target.value.toUpperCase() })}
                  placeholder="e.g. 24AABCT1234F1ZP"
                  className={`rounded-sm pr-10 font-mono tracking-wider ${
                    gstinValidation?.valid ? 'border-emerald-400 focus:ring-emerald-500' :
                    gstinValidation && !gstinValidation.valid ? 'border-red-400 focus:ring-red-500' :
                    'border-zinc-200'
                  }`}
                  maxLength={15}
                  data-testid="client-gstin-input"
                />
                {gstinValidation && (
                  <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                    {gstinValidation.valid ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              {/* GSTIN Validation Details */}
              {gstinValidation && (
                <div className={`text-xs p-2.5 rounded-sm border ${
                  gstinValidation.valid ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
                }`} data-testid="gstin-validation-result">
                  {gstinValidation.valid ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-4">
                        <span className="text-emerald-700 font-medium">Valid GSTIN</span>
                        <span className="text-emerald-600">State: {gstinValidation.stateName} ({gstinValidation.stateCode})</span>
                      </div>
                      <div className="flex items-center gap-4 text-emerald-600">
                        <span>PAN: <span className="font-mono font-medium">{gstinValidation.pan}</span></span>
                      </div>
                      {gstinValidation.companyMatch && (
                        <div className={`flex items-center gap-1.5 mt-1 ${
                          gstinValidation.companyMatch.match ? 'text-emerald-700' : 'text-amber-700'
                        }`}>
                          {gstinValidation.companyMatch.match ? (
                            <CheckCircle className="w-3 h-3 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-3 h-3 flex-shrink-0" />
                          )}
                          <span>{gstinValidation.companyMatch.hint}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-red-600">
                      {gstinValidation.errors.map((err, i) => <p key={i}>{err}</p>)}
                    </div>
                  )}
                </div>
              )}
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
        <DialogContent className="border-zinc-300 rounded-none max-w-3xl max-h-[95vh] overflow-y-auto p-0">
          {/* Action Bar */}
          <div className="flex items-center justify-between px-5 py-2.5 border-b border-zinc-200 bg-white sticky top-0 z-10">
            <span className="text-xs font-medium text-zinc-500">Invoice Preview</span>
            <div className="flex gap-2">
              <Button onClick={() => handleDownloadPDF()} size="sm" variant="outline" className="rounded-none border-zinc-950 text-zinc-950 hover:bg-zinc-950 hover:text-white text-xs h-7 px-3">
                <Download className="w-3 h-3 mr-1.5" /> PDF
              </Button>
              <Button onClick={() => handleDownloadPDF()} size="sm" variant="outline" className="rounded-none border-zinc-950 text-zinc-950 hover:bg-zinc-950 hover:text-white text-xs h-7 px-3">
                <Send className="w-3 h-3 mr-1.5" /> Send
              </Button>
            </div>
          </div>
          
          {/* Printable Invoice — Compact 1-page B&W */}
          <div ref={invoiceRef} className="bg-white">
            {/* Header */}
            <div className="px-6 pt-5 pb-4">
              <div className="flex justify-between items-center">
                <img src="/assets/dv-logo.png" alt="D&V Business Consulting" className="h-16 w-auto" />
                <div className="text-right">
                  <h2 className="text-xl font-black tracking-tight text-zinc-950 uppercase">Proforma Invoice</h2>
                  <p className="text-xs text-zinc-500 font-mono mt-0.5">{selectedInvoice?.quotation_number}{selectedInvoice?.version > 1 ? ` v${selectedInvoice.version}` : ''}</p>
                </div>
              </div>
              <div className="mt-3 h-px bg-zinc-950"></div>
            </div>

            <div className="px-6 pb-5 space-y-4">
              {/* 3-col: Invoice Details | Bill To | From + Amount */}
              <div className="grid grid-cols-3 gap-6 text-xs">
                <div>
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2">Invoice Details</h3>
                  <div className="space-y-1">
                    <div className="flex justify-between"><span className="text-zinc-400">No.</span><span className="font-semibold text-zinc-950 font-mono">{selectedInvoice?.quotation_number}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Date</span><span className="text-zinc-700">{formatDate(selectedInvoice?.created_at)}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Terms</span><span className="font-semibold text-zinc-950 uppercase">{selectedInvoice?.payment_terms || 'ADVANCE'}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-400">Valid Until</span><span className="text-zinc-700">{formatDate(selectedInvoice?.valid_until || new Date(new Date(selectedInvoice?.created_at).getTime() + (selectedInvoice?.validity_days || 30)*24*60*60*1000))}</span></div>
                  </div>
                </div>
                <div>
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2">Bill To</h3>
                  <div className="border-l-2 border-zinc-950 pl-3">
                    <p className="font-bold text-zinc-950 text-sm">{selectedLead?.company || selectedInvoice?.client_name || 'Client'}</p>
                    <p className="text-zinc-600 mt-0.5">{selectedLead?.first_name} {selectedLead?.last_name}</p>
                    {selectedLead?.email && <p className="text-zinc-400 mt-0.5">{selectedLead.email}</p>}
                    {selectedLead?.phone && <p className="text-zinc-400">{selectedLead.phone}</p>}
                    {(() => {
                      const gstin = selectedInvoice?.client_gstin || selectedLead?.gstin;
                      if (!gstin) return null;
                      const gstinVal = validateGSTIN(gstin);
                      return (
                        <>
                          <p className="text-zinc-500 font-mono mt-1">GSTIN: {gstin}</p>
                          {gstinVal.valid && (
                            <p className="text-zinc-400 text-[9px]">
                              PAN: {gstinVal.pan} | Entity: {({'C':'Company','P':'Individual','H':'HUF','F':'Firm','A':'AOP','T':'Trust'})[gstinVal.pan?.[3]] || ''}
                            </p>
                          )}
                          <p className="text-zinc-400">{gstinVal.valid ? `State: ${gstinVal.stateName} | Code: ${gstinVal.stateCode}` : 'State: Gujarat | Code: 24'}</p>
                        </>
                      );
                    })()}
                    {!(selectedInvoice?.client_gstin || selectedLead?.gstin) && <p className="text-zinc-400">State: Gujarat | Code: 24</p>}
                  </div>
                </div>
                <div>
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2">From</h3>
                  <p className="font-bold text-zinc-950 text-sm">{companyDetails.name}</p>
                  <p className="text-zinc-400 mt-0.5">{companyDetails.address}</p>
                  <p className="text-zinc-500 font-mono mt-0.5">GSTIN: {companyDetails.gstin}</p>
                  <p className="text-zinc-400">State: {companyDetails.state} | Code: {companyDetails.stateCode}</p>
                </div>
              </div>

              {/* Team Deployment — compact */}
              {selectedPlanDetails && (selectedPlanDetails.team_deployment || selectedPlanDetails.consultants || []).length > 0 && (
                <div>
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1.5">Team Deployment</h3>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b-2 border-zinc-950">
                        <th className="text-left py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Role</th>
                        <th className="text-left py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Meeting Type</th>
                        <th className="text-center py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Count</th>
                        <th className="text-center py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Meetings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedPlanDetails.team_deployment || selectedPlanDetails.consultants).map((member, idx) => (
                        <tr key={idx} className="border-b border-zinc-100">
                          <td className="py-1.5 font-medium text-zinc-950">{member.role || member.consultant_type || '-'}</td>
                          <td className="py-1.5 text-zinc-600">{member.meeting_type || member.frequency || '-'}</td>
                          <td className="py-1.5 text-center text-zinc-700">{member.count || 1}</td>
                          <td className="py-1.5 text-center font-semibold text-zinc-950">{(member.committed_meetings || member.meetings || 0) * (member.count || 1)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-zinc-950">
                        <td className="py-1.5 font-bold text-zinc-950" colSpan={3}>Total</td>
                        <td className="py-1.5 text-center font-bold text-zinc-950">
                          {selectedInvoice?.total_meetings || (selectedPlanDetails.team_deployment || selectedPlanDetails.consultants || []).reduce((sum, m) => sum + ((m.committed_meetings || m.meetings || 0) * (m.count || 1)), 0)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}

              {/* Pricing Summary — single line item */}
              <div>
                <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1.5">Pricing Summary</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b-2 border-zinc-950">
                      <th className="text-left py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Description</th>
                      <th className="text-center py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">HSN/SAC</th>
                      <th className="text-center py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Period</th>
                      <th className="text-right py-1.5 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-zinc-100">
                      <td className="py-2">
                        <div className="font-medium text-zinc-950">Management Consulting Services — Professional Fees</div>
                        <div className="text-[10px] text-zinc-400">{selectedPlanDetails?.project_duration_months || 12} months engagement</div>
                      </td>
                      <td className="py-2 text-center text-zinc-500 font-mono">998311</td>
                      <td className="py-2 text-center text-zinc-500">{selectedPlanDetails?.project_duration_months || 12} Months</td>
                      <td className="py-2 text-right font-semibold text-zinc-950">{formatINR(selectedInvoice?.subtotal || 0)}</td>
                    </tr>
                  </tbody>
                </table>
                
                {/* Tax & Total — right-aligned compact */}
                <div className="mt-2 pt-2 border-t border-zinc-200">
                  <div className="flex justify-end">
                    <div className="w-56 space-y-1 text-xs">
                      <div className="flex justify-between"><span className="text-zinc-400">Subtotal</span><span className="font-medium text-zinc-700">{formatINR(selectedInvoice?.subtotal || 0)}</span></div>
                      <div className="flex justify-between"><span className="text-zinc-400">CGST @ 9%</span><span className="text-zinc-600">{formatINR((selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0) / 2)}</span></div>
                      <div className="flex justify-between"><span className="text-zinc-400">SGST @ 9%</span><span className="text-zinc-600">{formatINR((selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0) / 2)}</span></div>
                      <div className="flex justify-between pb-1 border-b border-zinc-200"><span className="text-zinc-400">Total Tax (18%)</span><span className="font-medium text-zinc-700">{formatINR(selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0)}</span></div>
                      <div className="flex justify-between pt-1 border-t-2 border-zinc-950">
                        <span className="font-black text-zinc-950 text-sm">GRAND TOTAL</span>
                        <span className="font-black text-zinc-950 text-sm">{formatINR(selectedInvoice?.grand_total || selectedInvoice?.total || ((selectedInvoice?.subtotal || 0) + (selectedInvoice?.tax_amount || 0)))}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Amount in Words */}
              <div className="border border-zinc-200 px-3 py-2">
                <p className="text-xs"><span className="font-semibold text-zinc-500 text-[9px] uppercase tracking-wider">Amount in Words:</span><span className="text-zinc-950 ml-2 font-medium">{numberToWords(selectedInvoice?.grand_total || selectedInvoice?.total || 0)}</span></p>
              </div>

              {/* HSN Summary — compact */}
              <div>
                <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1">HSN/SAC Summary</h3>
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="border-b border-zinc-950">
                      <th className="px-2 py-1 text-left font-bold text-zinc-500 uppercase">HSN/SAC</th>
                      <th className="px-2 py-1 text-right font-bold text-zinc-500 uppercase">Taxable Value</th>
                      <th className="px-2 py-1 text-center font-bold text-zinc-500 uppercase">CGST</th>
                      <th className="px-2 py-1 text-right font-bold text-zinc-500 uppercase">CGST Amt</th>
                      <th className="px-2 py-1 text-center font-bold text-zinc-500 uppercase">SGST</th>
                      <th className="px-2 py-1 text-right font-bold text-zinc-500 uppercase">SGST Amt</th>
                      <th className="px-2 py-1 text-right font-bold text-zinc-500 uppercase">Total Tax</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-2 py-1 font-mono">998311</td>
                      <td className="px-2 py-1 text-right">{formatINR(selectedInvoice?.subtotal || 0)}</td>
                      <td className="px-2 py-1 text-center">9%</td>
                      <td className="px-2 py-1 text-right">{formatINR((selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0) / 2)}</td>
                      <td className="px-2 py-1 text-center">9%</td>
                      <td className="px-2 py-1 text-right">{formatINR((selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0) / 2)}</td>
                      <td className="px-2 py-1 text-right font-semibold">{formatINR(selectedInvoice?.gst_amount || selectedInvoice?.tax_amount || 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Payment Terms & Conditions Box + Bank Details */}
              <div className="grid grid-cols-2 gap-6">
                <div className="border border-zinc-300 p-3">
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1.5">Payment Terms & Conditions</h3>
                  <ol className="text-[10px] text-zinc-600 space-y-1">
                    {(selectedInvoice?.terms_and_conditions || '1) Payment via Bank transfer or cheques only\n2) Payment refund is not permissible\n3) Breach of information subject to agreement violation\n4) TDS to be paid regularly; submit challan to biller\n5) Disputes subject to Ahmedabad jurisdiction').split('\n').map((t, i) => {
                      const cleaned = t.replace(/^\d+\)\s*/, '').trim();
                      return cleaned ? (
                        <li key={i} className="flex gap-1.5"><span className="text-zinc-400 font-mono">{i+1}.</span>{cleaned}</li>
                      ) : null;
                    })}
                  </ol>
                </div>
                <div className="border border-zinc-300 p-3">
                  <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-1.5">Bank Details</h3>
                  <div className="space-y-1 text-[10px]">
                    {[['Bank', companyDetails.bankName],['A/c Holder', companyDetails.accountName],['A/c No.', companyDetails.accountNo],['Branch & IFSC', `${companyDetails.branch} | ${companyDetails.ifscCode}`],['SWIFT', companyDetails.swiftCode]].map(([l,v],i) => (
                      <div key={i} className="flex justify-between"><span className="text-zinc-400">{l}</span><span className="font-medium text-zinc-700 font-mono">{v}</span></div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Signature — compact */}
              <div className="flex justify-between items-end pt-4 border-t border-zinc-200">
                <p className="text-[9px] text-zinc-300 uppercase tracking-wider">Computer Generated Invoice</p>
                <div className="text-right">
                  <p className="text-[10px] font-semibold text-zinc-700 mb-6">For {companyDetails.name}</p>
                  <div className="border-t border-zinc-950 pt-1 w-40">
                    <p className="text-[9px] text-zinc-400 uppercase tracking-wider">Authorised Signatory</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-3 px-5 py-3 border-t border-zinc-200">
            <Button onClick={() => setViewDialogOpen(false)} variant="outline" className="flex-1 rounded-none border-zinc-300 h-8 text-xs">Close</Button>
            {selectedInvoice?.is_final && (
              <Button onClick={() => { setViewDialogOpen(false); navigate(`/sales-funnel/agreements?quotationId=${selectedInvoice.id}&leadId=${selectedInvoice.lead_id}`); }} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-none shadow-none h-8 text-xs">
                <ArrowRight className="w-3.5 h-3.5 mr-1.5" /> Proceed to Agreement
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProformaInvoice;
