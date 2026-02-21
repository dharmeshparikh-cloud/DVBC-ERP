import React, { useState, useEffect, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { 
  FileText, CreditCard, UserCheck, Rocket, CheckCircle, 
  ChevronRight, ChevronLeft, IndianRupee, Calendar,
  Building2, Receipt, Banknote, Wallet, Clock,
  ArrowLeft, Users, FileCheck, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

// Client Onboarding Steps
const ONBOARDING_STEPS = [
  { id: 'agreement', title: 'Agreement Review', icon: FileText, description: 'Review signed agreement details' },
  { id: 'payment', title: 'Record Payment', icon: CreditCard, description: 'Record client payment details' },
  { id: 'kickoff', title: 'Project Kickoff', icon: Rocket, description: 'Select PM and create kickoff request' },
  { id: 'complete', title: 'Onboarding Complete', icon: CheckCircle, description: 'Client onboarding finished' },
];

const ClientOnboarding = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const agreementId = searchParams.get('agreementId');
  const leadId = searchParams.get('leadId');

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [agreement, setAgreement] = useState(null);
  const [lead, setLead] = useState(null);
  const [payments, setPayments] = useState([]);
  const [consultants, setConsultants] = useState([]);
  const [kickoffRequest, setKickoffRequest] = useState(null);

  // Payment Form
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_mode: '',
    cheque_number: '',
    utr_number: '',
    remarks: ''
  });
  const [recordingPayment, setRecordingPayment] = useState(false);

  // Kickoff Form
  const [kickoffForm, setKickoffForm] = useState({
    assigned_pm_id: '',
    project_name: '',
    expected_start_date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  const [creatingKickoff, setCreatingKickoff] = useState(false);

  useEffect(() => {
    if (agreementId) {
      fetchData();
    }
  }, [agreementId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [agrRes, paymentsRes, consultantsRes] = await Promise.all([
        axios.get(`${API}/agreements/${agreementId}/full`),
        axios.get(`${API}/agreements/${agreementId}/payments`),
        axios.get(`${API}/consultants`)
      ]);
      
      setAgreement(agrRes.data);
      setPayments(paymentsRes.data.payments || []);
      setConsultants(consultantsRes.data || []);
      
      // Set initial kickoff form values
      setKickoffForm(prev => ({
        ...prev,
        project_name: agrRes.data.client_name ? `${agrRes.data.client_name} Project` : ''
      }));
      
      // Fetch lead if available
      if (agrRes.data.lead_id) {
        const leadRes = await axios.get(`${API}/leads/${agrRes.data.lead_id}`);
        setLead(leadRes.data);
        setKickoffForm(prev => ({
          ...prev,
          project_name: leadRes.data.company ? `${leadRes.data.company} Project` : prev.project_name
        }));
      }

      // Check for existing kickoff request
      try {
        const kickoffRes = await axios.get(`${API}/kickoff-requests?agreement_id=${agreementId}`);
        if (kickoffRes.data?.length > 0) {
          setKickoffRequest(kickoffRes.data[0]);
          // If kickoff already created, jump to complete step
          if (kickoffRes.data[0].status === 'accepted') {
            setCurrentStep(3);
          }
        }
      } catch (e) {
        // No kickoff request yet
      }
      
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordPayment = async () => {
    if (!paymentForm.amount || !paymentForm.payment_mode || !paymentForm.payment_date) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (paymentForm.payment_mode === 'Cheque' && !paymentForm.cheque_number) {
      toast.error('Cheque number is required');
      return;
    }

    if (['NEFT', 'RTGS', 'UPI'].includes(paymentForm.payment_mode) && !paymentForm.utr_number) {
      toast.error('UTR/Reference number is required');
      return;
    }

    setRecordingPayment(true);
    try {
      await axios.post(`${API}/agreements/${agreementId}/record-payment`, {
        amount: parseFloat(paymentForm.amount),
        payment_date: paymentForm.payment_date,
        payment_mode: paymentForm.payment_mode,
        cheque_number: paymentForm.cheque_number || null,
        utr_number: paymentForm.utr_number || null,
        remarks: paymentForm.remarks || null
      });

      toast.success('Payment recorded successfully');
      
      // Reset form and refresh
      setPaymentForm({
        amount: '',
        payment_date: new Date().toISOString().split('T')[0],
        payment_mode: '',
        cheque_number: '',
        utr_number: '',
        remarks: ''
      });
      
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setRecordingPayment(false);
    }
  };

  const handleCreateKickoff = async () => {
    if (!kickoffForm.assigned_pm_id || !kickoffForm.project_name) {
      toast.error('Please select a PM and enter project name');
      return;
    }

    setCreatingKickoff(true);
    try {
      const selectedPM = consultants.find(c => c.id === kickoffForm.assigned_pm_id || c.employee_id === kickoffForm.assigned_pm_id);
      
      await axios.post(`${API}/kickoff-requests`, {
        agreement_id: agreementId,
        lead_id: lead?.id || agreement?.lead_id,
        project_name: kickoffForm.project_name,
        client_name: lead?.company || agreement?.client_name,
        assigned_pm_id: kickoffForm.assigned_pm_id,
        assigned_pm_name: selectedPM ? `${selectedPM.first_name} ${selectedPM.last_name}` : '',
        expected_start_date: kickoffForm.expected_start_date,
        notes: kickoffForm.notes
      });

      toast.success('Kickoff request created successfully! Awaiting approval.');
      await fetchData();
      setCurrentStep(3);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create kickoff request');
    } finally {
      setCreatingKickoff(false);
    }
  };

  const agreementValue = agreement?.total_value || agreement?.grand_total || 0;
  const totalPaid = payments.reduce((sum, p) => sum + (p.amount || 0), 0);
  const remaining = agreementValue - totalPaid;
  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100;

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (!agreement) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Agreement Not Found</h2>
        <p className="text-zinc-500 mb-6">The agreement could not be loaded.</p>
        <Button onClick={() => navigate('/sales-funnel/agreements')}>
          Go to Agreements
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="client-onboarding-page">
      {/* Header */}
      <div className="mb-8">
        <Button
          onClick={() => navigate(`/sales-funnel/agreement/${agreementId}`)}
          variant="ghost"
          className="hover:bg-zinc-100 rounded-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Agreement
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 mb-2">
          Client Onboarding
        </h1>
        <p className="text-zinc-500">
          Complete all steps to onboard {lead?.company || agreement?.client_name || 'the client'}
        </p>
      </div>

      {/* Progress Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-500">Onboarding Progress</span>
          <span className="text-sm font-medium">{currentStep + 1} of {ONBOARDING_STEPS.length}</span>
        </div>
        <Progress value={progress} className="h-2" />
        
        {/* Step Indicators */}
        <div className="flex justify-between mt-4">
          {ONBOARDING_STEPS.map((step, index) => {
            const StepIcon = step.icon;
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;
            
            return (
              <div 
                key={step.id}
                className={`flex flex-col items-center cursor-pointer ${
                  index <= currentStep ? 'opacity-100' : 'opacity-40'
                }`}
                onClick={() => index <= currentStep && setCurrentStep(index)}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
                  isCompleted ? 'bg-emerald-500 text-white' :
                  isCurrent ? 'bg-blue-500 text-white' :
                  'bg-zinc-200 text-zinc-500'
                }`}>
                  {isCompleted ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    <StepIcon className="w-5 h-5" />
                  )}
                </div>
                <span className={`text-xs font-medium text-center ${
                  isCurrent ? 'text-blue-600' : 'text-zinc-500'
                }`}>
                  {step.title}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardHeader className="border-b border-zinc-100">
          <div className="flex items-center gap-3">
            {React.createElement(ONBOARDING_STEPS[currentStep].icon, {
              className: 'w-6 h-6 text-blue-500'
            })}
            <div>
              <CardTitle>{ONBOARDING_STEPS[currentStep].title}</CardTitle>
              <CardDescription>{ONBOARDING_STEPS[currentStep].description}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {/* Step 0: Agreement Review */}
          {currentStep === 0 && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-zinc-50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase">Agreement #</p>
                  <p className="font-semibold">{agreement?.agreement_number}</p>
                </div>
                <div className="p-4 bg-zinc-50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase">Client</p>
                  <p className="font-semibold">{lead?.company || agreement?.client_name || 'N/A'}</p>
                </div>
                <div className="p-4 bg-zinc-50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase">Agreement Value</p>
                  <p className="font-semibold text-emerald-600">{formatCurrency(agreementValue)}</p>
                </div>
                <div className="p-4 bg-zinc-50 rounded-lg">
                  <p className="text-xs text-zinc-500 uppercase">Status</p>
                  <span className={`inline-flex px-2 py-1 text-xs rounded ${
                    agreement?.status === 'signed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {agreement?.status?.charAt(0).toUpperCase() + agreement?.status?.slice(1)}
                  </span>
                </div>
              </div>

              {agreement?.status !== 'signed' && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-center gap-2 text-amber-700">
                    <AlertCircle className="w-5 h-5" />
                    <p>Agreement must be signed before proceeding with onboarding.</p>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <Button 
                  onClick={() => setCurrentStep(1)}
                  disabled={agreement?.status !== 'signed'}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Continue to Payment
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 1: Payment Recording */}
          {currentStep === 1 && (
            <div className="space-y-6">
              {/* Payment Progress */}
              <div className="p-4 bg-emerald-50 rounded-lg">
                <div className="flex justify-between items-end mb-2">
                  <div>
                    <p className="text-sm text-zinc-500">Total Paid</p>
                    <p className="text-2xl font-semibold text-emerald-600">{formatCurrency(totalPaid)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-zinc-500">Remaining</p>
                    <p className="text-xl font-medium text-zinc-700">{formatCurrency(remaining)}</p>
                  </div>
                </div>
                <div className="h-3 bg-emerald-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${Math.min(100, (totalPaid / agreementValue) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Payment Form */}
                <div className="space-y-4">
                  <h3 className="font-medium flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-green-500" />
                    Record New Payment
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Amount (₹) *</Label>
                      <div className="relative">
                        <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                        <Input
                          type="number"
                          value={paymentForm.amount}
                          onChange={(e) => setPaymentForm({...paymentForm, amount: e.target.value})}
                          placeholder="0.00"
                          className="pl-9 rounded-sm"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Payment Date *</Label>
                      <Input
                        type="date"
                        value={paymentForm.payment_date}
                        onChange={(e) => setPaymentForm({...paymentForm, payment_date: e.target.value})}
                        className="rounded-sm"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Payment Mode *</Label>
                    <Select
                      value={paymentForm.payment_mode}
                      onValueChange={(value) => setPaymentForm({
                        ...paymentForm, 
                        payment_mode: value, 
                        cheque_number: '', 
                        utr_number: ''
                      })}
                    >
                      <SelectTrigger className="rounded-sm">
                        <SelectValue placeholder="Select payment mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Cheque">
                          <div className="flex items-center gap-2">
                            <Receipt className="w-4 h-4" /> Cheque
                          </div>
                        </SelectItem>
                        <SelectItem value="NEFT">
                          <div className="flex items-center gap-2">
                            <Banknote className="w-4 h-4" /> NEFT
                          </div>
                        </SelectItem>
                        <SelectItem value="RTGS">
                          <div className="flex items-center gap-2">
                            <Banknote className="w-4 h-4" /> RTGS
                          </div>
                        </SelectItem>
                        <SelectItem value="UPI">
                          <div className="flex items-center gap-2">
                            <Wallet className="w-4 h-4" /> UPI
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {paymentForm.payment_mode === 'Cheque' && (
                    <div className="space-y-2">
                      <Label>Cheque Number *</Label>
                      <Input
                        value={paymentForm.cheque_number}
                        onChange={(e) => setPaymentForm({...paymentForm, cheque_number: e.target.value})}
                        placeholder="Enter cheque number"
                        className="rounded-sm"
                      />
                    </div>
                  )}

                  {['NEFT', 'RTGS', 'UPI'].includes(paymentForm.payment_mode) && (
                    <div className="space-y-2">
                      <Label>UTR / Reference Number *</Label>
                      <Input
                        value={paymentForm.utr_number}
                        onChange={(e) => setPaymentForm({...paymentForm, utr_number: e.target.value})}
                        placeholder="Enter UTR or reference number"
                        className="rounded-sm"
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label>Remarks (Optional)</Label>
                    <Textarea
                      value={paymentForm.remarks}
                      onChange={(e) => setPaymentForm({...paymentForm, remarks: e.target.value})}
                      placeholder="Any additional notes..."
                      rows={2}
                      className="rounded-sm"
                    />
                  </div>

                  <Button
                    onClick={handleRecordPayment}
                    disabled={recordingPayment || !paymentForm.amount || !paymentForm.payment_mode}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {recordingPayment ? 'Recording...' : 'Record Payment'}
                  </Button>
                </div>

                {/* Payment History */}
                <div className="space-y-4">
                  <h3 className="font-medium flex items-center gap-2">
                    <Clock className="w-5 h-5 text-blue-500" />
                    Payment History ({payments.length})
                  </h3>
                  
                  {payments.length === 0 ? (
                    <div className="text-center py-8 text-zinc-400 border border-dashed border-zinc-200 rounded-lg">
                      <CreditCard className="w-10 h-10 mx-auto mb-2 opacity-50" />
                      <p>No payments recorded yet</p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {payments.map((payment, index) => (
                        <div
                          key={payment.id || index}
                          className="p-3 bg-zinc-50 rounded-lg border border-zinc-100"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-semibold text-emerald-600">{formatCurrency(payment.amount)}</p>
                              <p className="text-xs text-zinc-500">
                                {new Date(payment.payment_date).toLocaleDateString('en-IN')}
                              </p>
                            </div>
                            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                              {payment.payment_mode}
                            </span>
                          </div>
                          {payment.cheque_number && (
                            <p className="text-xs text-zinc-500 mt-1">Cheque #: {payment.cheque_number}</p>
                          )}
                          {payment.utr_number && (
                            <p className="text-xs text-zinc-500 mt-1">UTR: {payment.utr_number}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between pt-4 border-t">
                <Button variant="outline" onClick={() => setCurrentStep(0)}>
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button 
                  onClick={() => setCurrentStep(2)}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Continue to Kickoff
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: Project Kickoff */}
          {currentStep === 2 && (
            <div className="space-y-6">
              {kickoffRequest ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold mb-2">Kickoff Request Created</h3>
                  <p className="text-zinc-500 mb-4">
                    Status: <span className={`font-medium ${
                      kickoffRequest.status === 'accepted' ? 'text-emerald-600' : 
                      kickoffRequest.status === 'rejected' ? 'text-red-600' : 'text-amber-600'
                    }`}>
                      {kickoffRequest.status?.charAt(0).toUpperCase() + kickoffRequest.status?.slice(1)}
                    </span>
                  </p>
                  {kickoffRequest.status === 'pending' && (
                    <p className="text-sm text-zinc-400">
                      Awaiting approval from Sr. Manager / Principal Consultant
                    </p>
                  )}
                  {kickoffRequest.status === 'accepted' && (
                    <Button 
                      onClick={() => setCurrentStep(3)}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      View Completion Status
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </Button>
                  )}
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Project Name *</Label>
                        <Input
                          value={kickoffForm.project_name}
                          onChange={(e) => setKickoffForm({...kickoffForm, project_name: e.target.value})}
                          placeholder="Enter project name"
                          className="rounded-sm"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Assign Project Manager *</Label>
                        <Select
                          value={kickoffForm.assigned_pm_id}
                          onValueChange={(value) => setKickoffForm({...kickoffForm, assigned_pm_id: value})}
                        >
                          <SelectTrigger className="rounded-sm">
                            <SelectValue placeholder="Select PM" />
                          </SelectTrigger>
                          <SelectContent>
                            {consultants.map(c => (
                              <SelectItem key={c.id || c.employee_id} value={c.id || c.employee_id}>
                                {c.first_name} {c.last_name} - {c.role || c.designation}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label>Expected Start Date</Label>
                        <Input
                          type="date"
                          value={kickoffForm.expected_start_date}
                          onChange={(e) => setKickoffForm({...kickoffForm, expected_start_date: e.target.value})}
                          className="rounded-sm"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Notes (Optional)</Label>
                        <Textarea
                          value={kickoffForm.notes}
                          onChange={(e) => setKickoffForm({...kickoffForm, notes: e.target.value})}
                          placeholder="Any special instructions..."
                          rows={3}
                          className="rounded-sm"
                        />
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="p-4 bg-blue-50 rounded-lg">
                        <h4 className="font-medium text-blue-800 mb-3 flex items-center gap-2">
                          <FileCheck className="w-5 h-5" />
                          What happens next?
                        </h4>
                        <ul className="text-sm text-blue-700 space-y-2">
                          <li className="flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            Kickoff request will be sent for approval
                          </li>
                          <li className="flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            Sr. Manager/Principal will review and approve
                          </li>
                          <li className="flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            Project will be auto-created with SOW items
                          </li>
                          <li className="flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            Assigned PM will receive notification
                          </li>
                        </ul>
                      </div>

                      <div className="p-4 bg-zinc-50 rounded-lg">
                        <h4 className="font-medium text-zinc-700 mb-2">Payment Summary</h4>
                        <div className="text-sm space-y-1">
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Agreement Value:</span>
                            <span className="font-medium">{formatCurrency(agreementValue)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-zinc-500">Total Paid:</span>
                            <span className="font-medium text-emerald-600">{formatCurrency(totalPaid)}</span>
                          </div>
                          <div className="flex justify-between border-t pt-1 mt-1">
                            <span className="text-zinc-500">Remaining:</span>
                            <span className="font-medium">{formatCurrency(remaining)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between pt-4 border-t">
                    <Button variant="outline" onClick={() => setCurrentStep(1)}>
                      <ChevronLeft className="w-4 h-4 mr-2" />
                      Back
                    </Button>
                    <Button 
                      onClick={handleCreateKickoff}
                      disabled={creatingKickoff || !kickoffForm.assigned_pm_id || !kickoffForm.project_name}
                      className="bg-orange-500 hover:bg-orange-600"
                    >
                      {creatingKickoff ? 'Creating...' : 'Create Kickoff Request'}
                      <Rocket className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 3: Complete */}
          {currentStep === 3 && (
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-emerald-600" />
              </div>
              <h2 className="text-2xl font-semibold text-zinc-800 mb-2">
                Client Onboarding Complete!
              </h2>
              <p className="text-zinc-500 mb-8 max-w-md mx-auto">
                {lead?.company || agreement?.client_name} has been successfully onboarded. 
                The project has been created and the assigned PM has been notified.
              </p>
              
              <div className="flex justify-center gap-4">
                <Button
                  variant="outline"
                  onClick={() => navigate('/sales-funnel/agreements')}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Back to Agreements
                </Button>
                <Button
                  onClick={() => kickoffRequest?.project_id && navigate(`/projects/${kickoffRequest.project_id}`)}
                  disabled={!kickoffRequest?.project_id}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  View Project
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ClientOnboarding;
