import React, { useState, useEffect, useRef, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  ArrowLeft, Download, FileText, Users, Calendar, Building2, 
  MapPin, Phone, Mail, Plus, Trash2, Edit2, Check, X,
  FileSignature, Send, Loader2, CheckCircle, ArrowRight, UserCheck, Rocket, Upload
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR, numberToWords } from '../../utils/currency';
import SalesFunnelProgress from '../../components/SalesFunnelProgress';

const AgreementView = () => {
  const { agreementId } = useParams();
  const [searchParams] = useSearchParams();
  const quotationId = searchParams.get('quotationId');
  const pricingPlanId = searchParams.get('pricing_plan_id');
  
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const agreementRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [agreement, setAgreement] = useState(null);
  const [quotation, setQuotation] = useState(null);
  const [pricingPlan, setPricingPlan] = useState(null);
  const [sow, setSow] = useState(null);
  const [lead, setLead] = useState(null);
  
  // Milestones
  const [milestones, setMilestones] = useState([]);
  const [newMilestone, setNewMilestone] = useState({ description: '', amount: '', due_date: '' });
  
  // E-signature
  const [signatureDialogOpen, setSignatureDialogOpen] = useState(false);
  const [signatureData, setSignatureData] = useState({
    signer_name: '',
    signer_designation: '',
    signer_email: '',
    signature_date: new Date().toISOString().split('T')[0],
    signature_image: null
  });
  const [saving, setSaving] = useState(false);
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);

  // PM Selection for Kickoff
  const [pmSelectionDialogOpen, setPmSelectionDialogOpen] = useState(false);
  const [consultants, setConsultants] = useState([]);
  const [selectedPmId, setSelectedPmId] = useState('');
  const [kickoffNotes, setKickoffNotes] = useState('');
  const [creatingKickoff, setCreatingKickoff] = useState(false);

  // Upload Signed Agreement
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Send to Client
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [clientEmail, setClientEmail] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);

  useEffect(() => {
    if (agreementId) {
      fetchAgreementData();
    } else if (quotationId || pricingPlanId) {
      fetchDataForNewAgreement();
    }
    // Fetch consultants for PM selection
    fetchConsultants();
  }, [agreementId, quotationId, pricingPlanId]);

  const fetchConsultants = async () => {
    try {
      const response = await axios.get(`${API}/employees/consultants`);
      setConsultants(response.data);
    } catch (error) {
      console.error('Failed to fetch consultants:', error);
    }
  };

  const fetchAgreementData = async () => {
    try {
      const response = await axios.get(`${API}/agreements/${agreementId}/full`);
      setAgreement(response.data.agreement);
      setQuotation(response.data.quotation);
      setPricingPlan(response.data.pricing_plan);
      setSow(response.data.sow);
      setLead(response.data.lead);
      setMilestones(response.data.agreement?.milestones || []);
    } catch (error) {
      toast.error('Failed to load agreement');
    } finally {
      setLoading(false);
    }
  };

  const fetchDataForNewAgreement = async () => {
    try {
      const [quotationsRes, plansRes, leadsRes] = await Promise.all([
        axios.get(`${API}/quotations`),
        axios.get(`${API}/pricing-plans`),
        axios.get(`${API}/leads`)
      ]);

      // Find relevant data
      let targetQuotation = null;
      let targetPlan = null;
      let targetLead = null;
      let targetSow = null;

      if (quotationId) {
        targetQuotation = quotationsRes.data.find(q => q.id === quotationId);
        if (targetQuotation) {
          targetPlan = plansRes.data.find(p => p.id === targetQuotation.pricing_plan_id);
          targetLead = leadsRes.data.find(l => l.id === targetQuotation.lead_id);
        }
      } else if (pricingPlanId) {
        targetPlan = plansRes.data.find(p => p.id === pricingPlanId);
        if (targetPlan) {
          targetLead = leadsRes.data.find(l => l.id === targetPlan.lead_id);
          // Find quotation for this plan
          targetQuotation = quotationsRes.data.find(q => q.pricing_plan_id === pricingPlanId);
        }
      }

      // Fetch SOW if exists
      if (targetPlan?.sow_id) {
        try {
          const sowRes = await axios.get(`${API}/enhanced-sow/${targetPlan.sow_id}`);
          targetSow = sowRes.data;
        } catch (e) {
          console.log('SOW not found');
        }
      }

      setQuotation(targetQuotation);
      setPricingPlan(targetPlan);
      setLead(targetLead);
      setSow(targetSow);
      
      // Initialize default milestones based on payment schedule
      if (targetPlan?.payment_plan?.installments) {
        const defaultMilestones = targetPlan.payment_plan.installments.map((inst, idx) => ({
          id: `milestone-${idx + 1}`,
          description: inst.description || `Milestone ${idx + 1}`,
          amount: inst.amount || 0,
          due_date: inst.due_date || '',
          status: 'pending'
        }));
        setMilestones(defaultMilestones);
      }
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const addMilestone = () => {
    if (!newMilestone.description || !newMilestone.amount) {
      toast.error('Please fill milestone description and amount');
      return;
    }
    setMilestones([...milestones, {
      id: `milestone-${Date.now()}`,
      ...newMilestone,
      amount: parseFloat(newMilestone.amount),
      status: 'pending'
    }]);
    setNewMilestone({ description: '', amount: '', due_date: '' });
  };

  const removeMilestone = (index) => {
    setMilestones(milestones.filter((_, i) => i !== index));
  };

  const handleSaveAgreement = async () => {
    setSaving(true);
    try {
      const agreementData = {
        quotation_id: quotation?.id,
        lead_id: lead?.id,
        agreement_type: 'standard',
        payment_terms: 'As per milestone schedule',
        start_date: pricingPlan?.payment_plan?.start_date,
        end_date: null,
        meeting_frequency: pricingPlan?.project_duration_type || 'Monthly',
        project_tenure_months: pricingPlan?.project_duration_months || 12,
        team_deployment: pricingPlan?.team_deployment || [],
        milestones: milestones,
        special_conditions: ''
      };

      if (agreementId) {
        await axios.put(`${API}/agreements/${agreementId}`, agreementData);
        toast.success('Agreement updated');
      } else {
        const response = await axios.post(`${API}/agreements`, agreementData);
        toast.success('Agreement created');
        navigate(`/sales-funnel/agreement/${response.data.id}`);
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msg = detail.map(e => e.msg || e.message || 'Validation error').join(', ');
        toast.error(msg);
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to save agreement');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!agreementRef.current) return;
    
    const printContent = agreementRef.current.innerHTML;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Agreement - ${agreement?.agreement_number || 'Draft'}</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
              margin: 40px; 
              font-size: 11px;
              color: #18181b;
              line-height: 1.6;
            }
            h1 { font-size: 24px; margin-bottom: 20px; text-align: center; }
            h2 { font-size: 14px; margin: 20px 0 10px; border-bottom: 1px solid #e4e4e7; padding-bottom: 5px; }
            h3 { font-size: 12px; margin: 15px 0 8px; }
            p { margin: 8px 0; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { border: 1px solid #d4d4d8; padding: 8px; text-align: left; font-size: 10px; }
            th { background-color: #f4f4f5; font-weight: 600; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .font-bold { font-weight: 700; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #e4e4e7; border-radius: 4px; }
            .header { text-align: center; margin-bottom: 30px; }
            .logo { font-size: 28px; font-weight: 800; }
            .parties { display: flex; justify-content: space-between; margin: 20px 0; }
            .party-box { width: 48%; padding: 15px; background: #fafafa; border-radius: 4px; }
            .signature-box { margin-top: 40px; display: flex; justify-content: space-between; }
            .signature-line { width: 200px; border-top: 1px solid #18181b; margin-top: 50px; padding-top: 5px; text-align: center; }
            @media print {
              body { margin: 20px; }
              .page-break { page-break-before: always; }
            }
          </style>
        </head>
        <body>${printContent}</body>
      </html>
    `);
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 500);
  };

  // Canvas signature functions
  const startDrawing = (e) => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.beginPath();
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX || e.touches?.[0]?.clientX) - rect.left;
    const y = (e.clientY || e.touches?.[0]?.clientY) - rect.top;
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasSignature(true);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
    setSignatureData(prev => ({ ...prev, signature_image: null }));
  };

  const getSignatureImage = () => {
    if (!canvasRef.current || !hasSignature) return null;
    return canvasRef.current.toDataURL('image/png');
  };

  const initCanvas = () => {
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx.strokeStyle = '#18181b';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
    }
  };

  // Initialize canvas when dialog opens
  useEffect(() => {
    if (signatureDialogOpen) {
      setTimeout(initCanvas, 100);
    }
  }, [signatureDialogOpen]);

  const handleESignature = async () => {
    if (!signatureData.signer_name || !signatureData.signer_email) {
      toast.error('Please fill signer name and email');
      return;
    }

    if (!hasSignature) {
      toast.error('Please draw your signature');
      return;
    }
    
    setSaving(true);
    try {
      const signatureImage = getSignatureImage();
      await axios.post(`${API}/agreements/${agreementId}/sign`, {
        ...signatureData,
        signature_image: signatureImage,
        signed_at: new Date().toISOString()
      });
      toast.success('Agreement signed successfully! Now select a Project Manager for kickoff.');
      setSignatureDialogOpen(false);
      await fetchAgreementData();
      // Open PM selection dialog after successful signing
      setPmSelectionDialogOpen(true);
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msg = detail.map(e => e.msg || e.message || 'Validation error').join(', ');
        toast.error(msg);
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to sign agreement');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCreateKickoffRequest = async () => {
    if (!selectedPmId) {
      toast.error('Please select a consultant to assign as Project Manager');
      return;
    }

    setCreatingKickoff(true);
    try {
      const selectedConsultant = consultants.find(c => c.id === selectedPmId || c.user_id === selectedPmId);
      
      const kickoffData = {
        agreement_id: agreementId,
        client_name: lead?.company || '',
        project_name: `${lead?.company || 'Project'} - Consulting Engagement`,
        project_type: 'mixed',
        total_meetings: pricingPlan?.team_deployment?.reduce((sum, m) => sum + (m.committed_meetings || 0), 0) || 0,
        meeting_frequency: agreement?.meeting_frequency || pricingPlan?.project_duration_type || 'Monthly',
        project_tenure_months: agreement?.project_tenure_months || pricingPlan?.project_duration_months || 12,
        expected_start_date: pricingPlan?.payment_plan?.start_date || null,
        assigned_pm_id: selectedConsultant?.user_id || selectedPmId,
        assigned_pm_name: selectedConsultant ? `${selectedConsultant.first_name || ''} ${selectedConsultant.last_name || ''}`.trim() : '',
        notes: kickoffNotes || `Kickoff request created from Agreement ${agreement?.agreement_number}`
      };

      const response = await axios.post(`${API}/kickoff-requests`, kickoffData);
      
      toast.success('Kickoff request created successfully!');
      setPmSelectionDialogOpen(false);
      
      // Navigate to the kickoff requests page
      navigate('/kickoff-requests');
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        const msg = detail.map(e => e.msg || e.message || 'Validation error').join(', ');
        toast.error(msg);
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to create kickoff request');
      }
    } finally {
      setCreatingKickoff(false);
    }
  };

  // Upload signed agreement document
  const handleUploadSignedAgreement = async () => {
    if (!uploadFile) {
      toast.error('Please select a file to upload');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('agreement_id', agreementId);

      await axios.post(`${API}/agreements/${agreementId}/upload-signed`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success('Signed agreement uploaded successfully');
      setUploadDialogOpen(false);
      setUploadFile(null);
      await fetchAgreementData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  // Send agreement to client via email
  const handleSendToClient = async () => {
    if (!clientEmail) {
      toast.error('Please enter client email');
      return;
    }

    setSendingEmail(true);
    try {
      await axios.post(`${API}/agreements/${agreementId}/send-to-client`, {
        client_email: clientEmail,
        client_name: lead?.first_name || 'Client'
      });

      toast.success('Agreement sent to client successfully');
      setSendDialogOpen(false);
      
      // Update agreement status to 'sent'
      await fetchAgreementData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send agreement');
    } finally {
      setSendingEmail(false);
    }
  };

  // Record payment for agreement
  const handleRecordPayment = async () => {
    if (!paymentData.amount || !paymentData.payment_mode || !paymentData.payment_date) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (paymentData.payment_mode === 'Cheque' && !paymentData.cheque_number) {
      toast.error('Cheque number is required');
      return;
    }

    if (['NEFT', 'UPI'].includes(paymentData.payment_mode) && !paymentData.utr_number) {
      toast.error('UTR number is required');
      return;
    }

    setRecordingPayment(true);
    try {
      await axios.post(`${API}/agreements/${agreementId}/record-payment`, {
        amount: parseFloat(paymentData.amount),
        payment_date: paymentData.payment_date,
        payment_mode: paymentData.payment_mode,
        cheque_number: paymentData.cheque_number || null,
        utr_number: paymentData.utr_number || null,
        remarks: paymentData.remarks || null
      });

      toast.success('Payment recorded successfully');
      setPaymentDialogOpen(false);
      setPaymentData({
        amount: '',
        payment_date: new Date().toISOString().split('T')[0],
        payment_mode: '',
        cheque_number: '',
        utr_number: '',
        remarks: ''
      });
      await fetchAgreementData();
      await fetchPayments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setRecordingPayment(false);
    }
  };

  // Fetch payments for this agreement
  const fetchPayments = async () => {
    try {
      const res = await axios.get(`${API}/agreements/${agreementId}/payments`);
      setAgreementPayments(res.data.payments || []);
    } catch (error) {
      console.error('Error fetching payments:', error);
    }
  };

  // Fetch payments when agreement is loaded
  useEffect(() => {
    if (agreementId && agreement?.status === 'signed') {
      fetchPayments();
    }
  }, [agreementId, agreement?.status]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  };

  // Calculate totals
  const totalAmount = quotation?.grand_total || 
    (pricingPlan?.total_investment || pricingPlan?.total_amount || 0);
  const gstAmount = totalAmount * 0.18;
  const grandTotal = totalAmount + gstAmount;
  const milestoneTotalAmount = milestones.reduce((sum, m) => sum + (m.amount || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto" data-testid="agreement-view-page">
      {/* Progress Bar */}
      <SalesFunnelProgress
        currentStep={4}
        pricingPlanId={pricingPlanId || pricingPlan?.id}
        leadId={lead?.id}
        sowCompleted={!!sow}
        proformaCompleted={!!quotation}
        agreementCompleted={agreement?.status === 'signed'}
      />

      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/sales-funnel/proforma-invoice')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Proforma Invoice
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              {agreementId ? 'Agreement' : 'Create Agreement'}
            </h1>
            <p className="text-zinc-500">
              {agreement?.agreement_number || 'Draft Agreement'} • {lead?.company || 'Client'}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={handleDownloadPDF}
              variant="outline"
              className="rounded-sm"
            >
              <Download className="w-4 h-4 mr-2" />
              Download PDF
            </Button>
            
            {/* Send to Client button - available for draft/created agreements */}
            {agreement && !['signed', 'sent'].includes(agreement.status) && (
              <Button
                onClick={() => {
                  setClientEmail(lead?.email || '');
                  setSendDialogOpen(true);
                }}
                variant="outline"
                className="rounded-sm border-blue-200 text-blue-600 hover:bg-blue-50"
              >
                <Send className="w-4 h-4 mr-2" />
                Send to Client
              </Button>
            )}

            {/* Upload Signed Agreement - for sent agreements */}
            {agreement?.status === 'sent' && (
              <Button
                onClick={() => setUploadDialogOpen(true)}
                variant="outline"
                className="rounded-sm border-emerald-200 text-emerald-600 hover:bg-emerald-50"
              >
                <FileText className="w-4 h-4 mr-2" />
                Upload Signed Copy
              </Button>
            )}

            {agreement?.status !== 'signed' && (
              <Button
                onClick={() => setSignatureDialogOpen(true)}
                className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
              >
                <FileSignature className="w-4 h-4 mr-2" />
                E-Sign Agreement
              </Button>
            )}
            {agreement?.status === 'signed' && (
              <Button
                onClick={() => setPmSelectionDialogOpen(true)}
                className="bg-orange-500 text-white hover:bg-orange-600 rounded-sm shadow-none"
                data-testid="create-kickoff-from-signed-btn"
              >
                <UserCheck className="w-4 h-4 mr-2" />
                Create Project Kickoff
              </Button>
            )}
            
            {/* Record Payment Button - for signed agreements */}
            {agreement?.status === 'signed' && (
              <Button
                onClick={() => setPaymentDialogOpen(true)}
                className="bg-green-600 text-white hover:bg-green-700 rounded-sm shadow-none"
                data-testid="record-payment-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Record Payment
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Agreement Content */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardContent className="p-0">
          <div ref={agreementRef} className="p-8 bg-white">
            {/* Agreement Header */}
            <div className="text-center mb-8 border-b border-zinc-200 pb-6">
              <div className="flex justify-center items-center gap-3 mb-4">
                <div className="w-14 h-14 bg-zinc-900 rounded-sm flex items-center justify-center">
                  <span className="text-2xl font-black text-white tracking-tighter">D&V</span>
                </div>
                <div className="text-left">
                  <h1 className="text-2xl font-bold text-zinc-900">D&V®</h1>
                  <p className="text-zinc-500 text-sm">Business Consulting</p>
                </div>
              </div>
              <h2 className="text-xl font-semibold text-zinc-800 mt-4">CONSULTING SERVICES AGREEMENT</h2>
              <p className="text-zinc-500 text-sm mt-2">
                Agreement No: {agreement?.agreement_number || 'AGR-DRAFT'}
              </p>
            </div>

            {/* Parties Section */}
            <div className="grid grid-cols-2 gap-6 mb-8">
              {/* First Party */}
              <div className="p-4 bg-zinc-50 rounded-sm">
                <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-3 flex items-center gap-2">
                  <Building2 className="w-4 h-4" /> First Party (Consultant)
                </h3>
                <p className="font-semibold text-zinc-900">D & V Business Consulting</p>
                <p className="text-sm text-zinc-600 flex items-center gap-1 mt-1">
                  <MapPin className="w-3 h-3" />
                  626, Iconic Shyamal, Shyamal Cross Road, Ahmedabad - 380015
                </p>
                <p className="text-sm text-zinc-600">Gujarat, India</p>
                <p className="text-sm text-zinc-600 flex items-center gap-1 mt-1">
                  <Phone className="w-3 h-3" /> +91-9824009829
                </p>
                <p className="text-sm text-zinc-500 mt-2">GSTIN: 24ASLPP4013H1ZV</p>
              </div>

              {/* Second Party */}
              <div className="p-4 bg-blue-50 rounded-sm">
                <h3 className="text-xs uppercase tracking-wider text-blue-600 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4" /> Second Party (Client)
                </h3>
                <p className="font-semibold text-zinc-900">{lead?.company || 'Client Company'}</p>
                <p className="text-sm text-zinc-600 mt-1">
                  {lead?.first_name} {lead?.last_name}
                </p>
                <p className="text-sm text-zinc-600 flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {lead?.address || 'Address not provided'}
                </p>
                <p className="text-sm text-zinc-600">{lead?.city || 'City'}, {lead?.state || 'State'}</p>
                <p className="text-sm text-zinc-600 flex items-center gap-1 mt-1">
                  <Mail className="w-3 h-3" /> {lead?.email}
                </p>
                {lead?.gstin && (
                  <p className="text-sm text-zinc-500 mt-2">GSTIN: {lead.gstin}</p>
                )}
              </div>
            </div>

            {/* Agreement Date & Duration */}
            <div className="grid grid-cols-3 gap-4 mb-8 p-4 bg-amber-50 border border-amber-200 rounded-sm">
              <div>
                <p className="text-xs uppercase text-amber-700">Agreement Date</p>
                <p className="font-semibold text-zinc-900">{formatDate(agreement?.created_at || new Date())}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-amber-700">Project Start Date</p>
                <p className="font-semibold text-zinc-900">{formatDate(pricingPlan?.payment_plan?.start_date)}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-amber-700">Project Duration</p>
                <p className="font-semibold text-zinc-900">{pricingPlan?.project_duration_months || 12} Months</p>
              </div>
            </div>

            {/* Whereas Clauses */}
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-zinc-800 mb-3 border-b pb-2">WHEREAS:</h3>
              <ol className="list-decimal list-inside space-y-2 text-sm text-zinc-700">
                <li>The First Party is engaged in the business of providing consulting services in the areas of Human Resources, Operations, Marketing, Sales, and Business Strategy.</li>
                <li>The Second Party desires to engage the First Party to provide certain consulting services as described herein.</li>
                <li>The First Party agrees to provide such services subject to the terms and conditions set forth in this Agreement.</li>
              </ol>
            </div>

            {/* Pricing Summary */}
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-zinc-800 mb-3 border-b pb-2">PRICING SUMMARY</h3>
              <div className="bg-zinc-50 p-4 rounded-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-zinc-500">Consulting Fees (Before Tax)</p>
                    <p className="text-lg font-bold text-zinc-900">{formatINR(totalAmount)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">GST @ 18%</p>
                    <p className="text-lg font-bold text-zinc-900">{formatINR(gstAmount)}</p>
                  </div>
                </div>
                <div className="border-t border-zinc-200 mt-4 pt-4">
                  <div className="flex justify-between items-center">
                    <p className="text-sm font-semibold text-zinc-700">Grand Total</p>
                    <p className="text-2xl font-bold text-emerald-600">{formatINR(grandTotal)}</p>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    ({numberToWords(grandTotal)} Only)
                  </p>
                </div>
              </div>
            </div>

            {/* Team Deployment Structure */}
            {pricingPlan?.team_deployment && pricingPlan.team_deployment.length > 0 && (
              <div className="mb-8">
                <h3 className="text-sm font-semibold text-zinc-800 mb-3 border-b pb-2">TEAM DEPLOYMENT STRUCTURE</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-zinc-100">
                      <th className="p-2 text-left">Role</th>
                      <th className="p-2 text-left">Meeting Type</th>
                      <th className="p-2 text-left">Frequency</th>
                      <th className="p-2 text-center">Count</th>
                      <th className="p-2 text-center">Meetings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pricingPlan.team_deployment.map((member, idx) => (
                      <tr key={idx} className="border-b border-zinc-100">
                        <td className="p-2 font-medium">{member.role}</td>
                        <td className="p-2">{member.meeting_type}</td>
                        <td className="p-2">{member.frequency}</td>
                        <td className="p-2 text-center">{member.count || 1}</td>
                        <td className="p-2 text-center font-semibold">{member.committed_meetings || member.meetings || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Scope of Work Summary */}
            {sow?.scopes && sow.scopes.length > 0 && (
              <div className="mb-8">
                <h3 className="text-sm font-semibold text-zinc-800 mb-3 border-b pb-2">SCOPE OF WORK SUMMARY</h3>
                <div className="grid grid-cols-2 gap-2">
                  {sow.scopes.slice(0, 10).map((scope, idx) => (
                    <div key={idx} className="p-2 bg-zinc-50 rounded-sm text-sm">
                      <span className="text-zinc-500 mr-2">{idx + 1}.</span>
                      {scope.name}
                    </div>
                  ))}
                  {sow.scopes.length > 10 && (
                    <div className="p-2 text-zinc-500 text-sm">
                      + {sow.scopes.length - 10} more scopes...
                    </div>
                  )}
                </div>
                <p className="text-xs text-zinc-500 mt-2 italic">
                  * Detailed Scope of Work attached as Annexure 1
                </p>
              </div>
            )}

            {/* Milestones Table */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-3 border-b pb-2">
                <h3 className="text-sm font-semibold text-zinc-800">PAYMENT MILESTONES</h3>
                {!agreement?.status?.includes('signed') && (
                  <span className="text-xs text-zinc-500">(Editable)</span>
                )}
              </div>
              
              <table className="w-full text-sm mb-4">
                <thead>
                  <tr className="bg-zinc-100">
                    <th className="p-2 text-left w-12">#</th>
                    <th className="p-2 text-left">Milestone Description</th>
                    <th className="p-2 text-right w-32">Amount (₹)</th>
                    <th className="p-2 text-center w-32">Due Date</th>
                    {!agreement?.status?.includes('signed') && (
                      <th className="p-2 text-center w-16"></th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {milestones.map((milestone, idx) => (
                    <tr key={milestone.id} className="border-b border-zinc-100">
                      <td className="p-2">{idx + 1}</td>
                      <td className="p-2">{milestone.description}</td>
                      <td className="p-2 text-right font-medium">{formatINR(milestone.amount)}</td>
                      <td className="p-2 text-center">{formatDate(milestone.due_date)}</td>
                      {!agreement?.status?.includes('signed') && (
                        <td className="p-2 text-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeMilestone(idx)}
                            className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                  <tr className="bg-emerald-50 font-semibold">
                    <td className="p-2" colSpan={2}>Total</td>
                    <td className="p-2 text-right text-emerald-700">{formatINR(milestoneTotalAmount)}</td>
                    <td className="p-2" colSpan={agreement?.status?.includes('signed') ? 1 : 2}></td>
                  </tr>
                </tbody>
              </table>

              {/* Add Milestone Form */}
              {!agreement?.status?.includes('signed') && (
                <div className="flex gap-2 items-end p-3 bg-zinc-50 rounded-sm">
                  <div className="flex-1">
                    <Label className="text-xs text-zinc-500">Description</Label>
                    <Input
                      value={newMilestone.description}
                      onChange={(e) => setNewMilestone({...newMilestone, description: e.target.value})}
                      placeholder="e.g., Initial Payment"
                      className="h-9 text-sm rounded-sm"
                    />
                  </div>
                  <div className="w-32">
                    <Label className="text-xs text-zinc-500">Amount (₹)</Label>
                    <Input
                      type="number"
                      value={newMilestone.amount}
                      onChange={(e) => setNewMilestone({...newMilestone, amount: e.target.value})}
                      placeholder="0"
                      className="h-9 text-sm rounded-sm"
                    />
                  </div>
                  <div className="w-36">
                    <Label className="text-xs text-zinc-500">Due Date</Label>
                    <Input
                      type="date"
                      value={newMilestone.due_date}
                      onChange={(e) => setNewMilestone({...newMilestone, due_date: e.target.value})}
                      className="h-9 text-sm rounded-sm"
                    />
                  </div>
                  <Button onClick={addMilestone} size="sm" className="h-9">
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Terms & Conditions */}
            <div className="mb-8">
              <h3 className="text-sm font-semibold text-zinc-800 mb-3 border-b pb-2">TERMS & CONDITIONS</h3>
              <ol className="list-decimal list-inside space-y-2 text-sm text-zinc-700">
                <li>All payments to be made via bank transfer or cheques.</li>
                <li>Payment refund is not permissible once the engagement has commenced.</li>
                <li>Any breach of confidential information is subject to violation of this agreement.</li>
                <li>TDS amount to be deducted as per applicable rates and challans to be submitted to the consultant.</li>
                <li>All disputes shall be subject to Ahmedabad jurisdiction.</li>
                <li>This agreement may be terminated by either party with 30 days written notice.</li>
                <li>Any modifications to the scope of work must be agreed upon in writing.</li>
              </ol>
            </div>

            {/* Bank Details */}
            <div className="mb-8 p-4 bg-blue-50 rounded-sm">
              <h3 className="text-sm font-semibold text-blue-800 mb-3">COMPANY BANK DETAILS</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-zinc-500">Account Holder</p>
                  <p className="font-medium">D & V Business Consulting</p>
                </div>
                <div>
                  <p className="text-zinc-500">Bank Name</p>
                  <p className="font-medium">ICICI Bank</p>
                </div>
                <div>
                  <p className="text-zinc-500">Account Number</p>
                  <p className="font-medium">034405500698</p>
                </div>
                <div>
                  <p className="text-zinc-500">IFSC Code</p>
                  <p className="font-medium">ICIC0000344</p>
                </div>
              </div>
            </div>

            {/* Signatures */}
            <div className="grid grid-cols-2 gap-8 mt-12 pt-8 border-t border-zinc-200">
              <div className="text-center">
                <div className="h-16 border-b border-zinc-300 mb-2"></div>
                <p className="font-medium text-zinc-900">For D & V Business Consulting</p>
                <p className="text-sm text-zinc-500">Authorized Signatory</p>
              </div>
              <div className="text-center">
                <div className="h-16 border-b border-zinc-300 mb-2">
                  {agreement?.client_signature && (
                    <div className="flex flex-col items-center justify-end h-full pb-2">
                      <CheckCircle className="w-6 h-6 text-emerald-500 mb-1" />
                      <span className="text-xs text-emerald-600">Signed</span>
                    </div>
                  )}
                </div>
                <p className="font-medium text-zinc-900">For {lead?.company || 'Client'}</p>
                <p className="text-sm text-zinc-500">
                  {agreement?.client_signature?.signer_name || 'Authorized Signatory'}
                </p>
                {agreement?.client_signature?.signed_at && (
                  <p className="text-xs text-zinc-400">
                    Signed on: {formatDate(agreement.client_signature.signed_at)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 mt-6">
        <Button
          onClick={() => navigate('/sales-funnel/proforma-invoice')}
          variant="outline"
          className="rounded-sm"
        >
          Cancel
        </Button>
        <Button
          onClick={handleSaveAgreement}
          disabled={saving}
          className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <ArrowRight className="w-4 h-4 mr-2" />
              {agreementId ? 'Save Agreement' : 'Save & Create Agreement'}
            </>
          )}
        </Button>
      </div>

      {/* E-Signature Dialog */}
      <Dialog open={signatureDialogOpen} onOpenChange={setSignatureDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950 flex items-center gap-2">
              <FileSignature className="w-5 h-5" />
              E-Sign Agreement
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Add your digital signature to this agreement
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm font-medium">Full Name *</Label>
                <Input
                  value={signatureData.signer_name}
                  onChange={(e) => setSignatureData({...signatureData, signer_name: e.target.value})}
                  placeholder="Enter your full name"
                  className="rounded-sm"
                  data-testid="signer-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">Designation</Label>
                <Input
                  value={signatureData.signer_designation}
                  onChange={(e) => setSignatureData({...signatureData, signer_designation: e.target.value})}
                  placeholder="e.g., Director, CEO"
                  className="rounded-sm"
                  data-testid="signer-designation-input"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-sm font-medium">Email *</Label>
                <Input
                  type="email"
                  value={signatureData.signer_email}
                  onChange={(e) => setSignatureData({...signatureData, signer_email: e.target.value})}
                  placeholder="your@email.com"
                  className="rounded-sm"
                  data-testid="signer-email-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">Date</Label>
                <Input
                  type="date"
                  value={signatureData.signature_date}
                  onChange={(e) => setSignatureData({...signatureData, signature_date: e.target.value})}
                  className="rounded-sm"
                  data-testid="signature-date-input"
                />
              </div>
            </div>
            
            {/* Canvas Signature Pad */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">Draw Your Signature *</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={clearSignature}
                  className="text-xs text-zinc-500 hover:text-zinc-900"
                  data-testid="clear-signature-btn"
                >
                  <X className="w-3 h-3 mr-1" /> Clear
                </Button>
              </div>
              <div className="border-2 border-dashed border-zinc-300 rounded-sm bg-white">
                <canvas
                  ref={canvasRef}
                  width={460}
                  height={120}
                  className="w-full cursor-crosshair touch-none"
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                  onTouchStart={startDrawing}
                  onTouchMove={draw}
                  onTouchEnd={stopDrawing}
                  data-testid="signature-canvas"
                />
              </div>
              <p className="text-xs text-zinc-500 text-center">
                {hasSignature ? 'Signature captured' : 'Draw your signature above using mouse or touch'}
              </p>
            </div>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm text-sm text-amber-800">
              By clicking "Sign Agreement", you acknowledge that this constitutes your electronic signature and consent to this agreement.
            </div>
            
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setSignatureDialogOpen(false);
                  clearSignature();
                }}
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button
                onClick={handleESignature}
                disabled={saving || !hasSignature || !signatureData.signer_name || !signatureData.signer_email}
                className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm disabled:opacity-50"
                data-testid="sign-agreement-btn"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Sign Agreement
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* PM Selection Dialog for Kickoff */}
      <Dialog open={pmSelectionDialogOpen} onOpenChange={setPmSelectionDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-zinc-950 flex items-center gap-2">
              <Rocket className="w-5 h-5 text-emerald-600" />
              Create Kickoff Request
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Agreement signed! Now assign a consultant as Project Manager to kickoff the project.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Success Banner */}
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-sm flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              <div>
                <p className="text-sm font-medium text-emerald-800">Agreement Signed Successfully!</p>
                <p className="text-xs text-emerald-600">{agreement?.agreement_number}</p>
              </div>
            </div>

            {/* Project Summary */}
            <div className="p-3 bg-zinc-50 rounded-sm space-y-2">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-zinc-500">Client:</span>
                  <span className="ml-2 font-medium">{lead?.company}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Duration:</span>
                  <span className="ml-2 font-medium">{agreement?.project_tenure_months || pricingPlan?.project_duration_months || 12} months</span>
                </div>
                <div>
                  <span className="text-zinc-500">Frequency:</span>
                  <span className="ml-2 font-medium">{agreement?.meeting_frequency || 'Monthly'}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Team Size:</span>
                  <span className="ml-2 font-medium">{agreement?.team_deployment?.length || pricingPlan?.team_deployment?.length || 0} members</span>
                </div>
              </div>
            </div>

            {/* PM Selection */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                <UserCheck className="w-4 h-4" />
                Select Consultant as Project Manager *
              </Label>
              <Select value={selectedPmId} onValueChange={setSelectedPmId}>
                <SelectTrigger className="rounded-sm" data-testid="pm-select">
                  <SelectValue placeholder="Select a consultant" />
                </SelectTrigger>
                <SelectContent>
                  {consultants.length === 0 ? (
                    <SelectItem value="no-consultants" disabled>No consultants available</SelectItem>
                  ) : (
                    consultants.map((consultant) => (
                      <SelectItem 
                        key={consultant.id || consultant.user_id} 
                        value={consultant.user_id || consultant.id}
                      >
                        {consultant.first_name} {consultant.last_name} - {consultant.designation || 'Consultant'}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-zinc-500">
                The selected consultant will be assigned as the Project Manager for this engagement.
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Notes (Optional)</Label>
              <textarea
                value={kickoffNotes}
                onChange={(e) => setKickoffNotes(e.target.value)}
                placeholder="Add any special instructions or notes for the consulting team..."
                rows={3}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                data-testid="kickoff-notes-input"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => {
                setPmSelectionDialogOpen(false);
                navigate('/sales-funnel/agreements');
              }}
              className="rounded-sm"
            >
              Skip for Now
            </Button>
            <Button
              onClick={handleCreateKickoffRequest}
              disabled={!selectedPmId || creatingKickoff}
              className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm"
              data-testid="create-kickoff-btn"
            >
              {creatingKickoff ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Rocket className="w-4 h-4 mr-2" />
              )}
              Create Kickoff Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Signed Agreement Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-500" />
              Upload Signed Agreement
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-zinc-600">
              Upload the signed agreement document received from the client.
            </p>
            <div className="border-2 border-dashed border-zinc-200 rounded-lg p-6 text-center">
              <input
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="hidden"
                id="signed-agreement-file"
              />
              <label htmlFor="signed-agreement-file" className="cursor-pointer">
                <FileText className="w-10 h-10 text-zinc-400 mx-auto mb-2" />
                <p className="text-sm text-zinc-600">
                  {uploadFile ? uploadFile.name : 'Click to select file'}
                </p>
                <p className="text-xs text-zinc-400 mt-1">PDF, DOC, DOCX, PNG, JPG</p>
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleUploadSignedAgreement}
              disabled={!uploadFile || uploading}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send to Client Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-500" />
              Send Agreement to Client
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-zinc-600">
              Send this agreement to the client for review and signature.
            </p>
            <div className="space-y-2">
              <Label>Client Email</Label>
              <Input
                type="email"
                value={clientEmail}
                onChange={(e) => setClientEmail(e.target.value)}
                placeholder="client@company.com"
                className="rounded-sm"
              />
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              <p className="font-medium">Email Preview:</p>
              <p className="mt-1">Subject: Agreement for Review - {agreement?.agreement_number}</p>
              <p className="mt-1">The client will receive a professional email with the agreement PDF attached.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSendDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSendToClient}
              disabled={!clientEmail || sendingEmail}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {sendingEmail ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Email
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Record Payment Dialog */}
      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-green-500" />
              Record Payment
            </DialogTitle>
            <DialogDescription>
              Record a payment received for this agreement
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Amount (₹) *</Label>
                <Input
                  type="number"
                  value={paymentData.amount}
                  onChange={(e) => setPaymentData({...paymentData, amount: e.target.value})}
                  placeholder="0.00"
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <Label>Payment Date *</Label>
                <Input
                  type="date"
                  value={paymentData.payment_date}
                  onChange={(e) => setPaymentData({...paymentData, payment_date: e.target.value})}
                  className="rounded-sm"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Payment Mode *</Label>
              <Select
                value={paymentData.payment_mode}
                onValueChange={(value) => setPaymentData({...paymentData, payment_mode: value, cheque_number: '', utr_number: ''})}
              >
                <SelectTrigger className="rounded-sm">
                  <SelectValue placeholder="Select payment mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Cheque">Cheque</SelectItem>
                  <SelectItem value="NEFT">NEFT</SelectItem>
                  <SelectItem value="UPI">UPI</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {paymentData.payment_mode === 'Cheque' && (
              <div className="space-y-2">
                <Label>Cheque Number *</Label>
                <Input
                  value={paymentData.cheque_number}
                  onChange={(e) => setPaymentData({...paymentData, cheque_number: e.target.value})}
                  placeholder="Enter cheque number"
                  className="rounded-sm"
                />
              </div>
            )}

            {['NEFT', 'UPI'].includes(paymentData.payment_mode) && (
              <div className="space-y-2">
                <Label>UTR Number *</Label>
                <Input
                  value={paymentData.utr_number}
                  onChange={(e) => setPaymentData({...paymentData, utr_number: e.target.value})}
                  placeholder="Enter UTR number"
                  className="rounded-sm"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label>Remarks (Optional)</Label>
              <Input
                value={paymentData.remarks}
                onChange={(e) => setPaymentData({...paymentData, remarks: e.target.value})}
                placeholder="Any additional notes"
                className="rounded-sm"
              />
            </div>

            {/* Existing Payments */}
            {agreementPayments.length > 0 && (
              <div className="border-t pt-4 mt-4">
                <h4 className="text-sm font-medium text-zinc-700 mb-2">Payment History</h4>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {agreementPayments.map((p, idx) => (
                    <div key={idx} className="flex justify-between text-sm p-2 bg-zinc-50 rounded">
                      <span>{new Date(p.payment_date).toLocaleDateString('en-IN')} - {p.payment_mode}</span>
                      <span className="font-medium">₹{p.amount?.toLocaleString('en-IN')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordPayment}
              disabled={recordingPayment}
              className="bg-green-600 hover:bg-green-700"
            >
              {recordingPayment ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Recording...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Record Payment
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AgreementView;
