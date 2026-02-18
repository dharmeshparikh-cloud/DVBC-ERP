import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  ArrowLeft, ArrowRight, CheckCircle, CreditCard, DollarSign, 
  FileText, Clock, AlertCircle, Send, Receipt, Banknote
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';

const PAYMENT_MODES = [
  { value: 'bank_transfer', label: 'Bank Transfer / NEFT / RTGS' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'upi', label: 'UPI' },
  { value: 'cash', label: 'Cash' },
  { value: 'dd', label: 'Demand Draft' }
];

const PaymentVerification = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [searchParams] = useSearchParams();
  const agreementIdParam = searchParams.get('agreement_id');
  
  const [agreements, setAgreements] = useState([]);
  const [selectedAgreement, setSelectedAgreement] = useState(null);
  const [eligibilityStatus, setEligibilityStatus] = useState(null);
  const [quotationDetails, setQuotationDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showVerifyDialog, setShowVerifyDialog] = useState(false);
  
  const [formData, setFormData] = useState({
    agreement_id: '',
    installment_number: 1,
    expected_amount: 0,
    received_amount: 0,
    transaction_id: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_mode: 'bank_transfer',
    bank_reference: '',
    notes: ''
  });

  useEffect(() => {
    fetchAgreements();
  }, []);

  useEffect(() => {
    if (agreementIdParam) {
      setFormData(prev => ({ ...prev, agreement_id: agreementIdParam }));
      handleAgreementSelect(agreementIdParam);
    }
  }, [agreementIdParam, agreements]);

  const fetchAgreements = async () => {
    try {
      // Fetch signed/approved agreements that may need payment verification
      const response = await axios.get(`${API}/agreements`, {
        params: { status: 'approved' }
      });
      const approvedAgreements = response.data.filter(a => 
        ['approved', 'signed', 'sent'].includes(a.status)
      );
      setAgreements(approvedAgreements);
    } catch (error) {
      console.error('Failed to fetch agreements:', error);
      toast.error('Failed to load agreements');
    } finally {
      setLoading(false);
    }
  };

  const handleAgreementSelect = async (agreementId) => {
    const agreement = agreements.find(a => a.id === agreementId);
    if (!agreement) return;
    
    setSelectedAgreement(agreement);
    setFormData(prev => ({ ...prev, agreement_id: agreementId }));
    
    try {
      // Check eligibility status
      const eligibilityRes = await axios.get(`${API}/payments/check-eligibility/${agreementId}`);
      setEligibilityStatus(eligibilityRes.data);
      
      // Fetch quotation details for expected amount
      if (agreement.quotation_id) {
        const quotationsRes = await axios.get(`${API}/quotations`);
        const quotation = quotationsRes.data.find(q => q.id === agreement.quotation_id);
        if (quotation) {
          setQuotationDetails(quotation);
          // Calculate first installment amount (typically 30-50% advance)
          const advancePercentage = 0.30; // 30% advance
          const expectedAmount = Math.round(quotation.grand_total * advancePercentage);
          setFormData(prev => ({ 
            ...prev, 
            expected_amount: expectedAmount,
            received_amount: expectedAmount
          }));
        }
      }
    } catch (error) {
      console.error('Failed to check eligibility:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.transaction_id.trim()) {
      toast.error('Transaction ID is required');
      return;
    }
    
    if (formData.received_amount <= 0) {
      toast.error('Received amount must be greater than 0');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        payment_date: new Date(formData.payment_date).toISOString(),
        pricing_plan_id: selectedAgreement?.pricing_plan_id || quotationDetails?.pricing_plan_id
      };
      
      await axios.post(`${API}/payments/verify-installment`, payload);
      toast.success('Payment verified successfully! SOW has been handed over to Consulting.');
      setShowVerifyDialog(false);
      
      // Refresh eligibility status
      const eligibilityRes = await axios.get(`${API}/payments/check-eligibility/${formData.agreement_id}`);
      setEligibilityStatus(eligibilityRes.data);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify payment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleProceedToKickoff = () => {
    navigate(`/sales-funnel/kickoff-requests?agreement_id=${selectedAgreement.id}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto" data-testid="payment-verification-page">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/sales-funnel/agreements')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Agreements
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Payment Verification
            </h1>
            <p className="text-zinc-500">
              Verify first installment payment before initiating project kickoff
            </p>
          </div>
        </div>
      </div>

      {/* Flow Info Banner */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-sm">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900">Payment Verification Flow</h3>
            <p className="text-sm text-blue-700 mt-1">
              Before creating a kickoff request, you must verify that the first installment (advance payment) 
              has been received. This automatically hands over the SOW to the Consulting team.
            </p>
            <div className="mt-3 flex items-center gap-2 text-sm text-blue-800">
              <span className="px-2 py-1 bg-blue-100 rounded-sm">1. Agreement Signed</span>
              <ArrowRight className="w-4 h-4" />
              <span className="px-2 py-1 bg-blue-100 rounded-sm font-medium">2. Verify Payment</span>
              <ArrowRight className="w-4 h-4" />
              <span className="px-2 py-1 bg-blue-100 rounded-sm">3. Create Kickoff Request</span>
            </div>
          </div>
        </div>
      </div>

      {/* Agreement Selection */}
      <Card className="border-zinc-200 shadow-none rounded-sm mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
            Select Agreement
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Agreement *</Label>
              <Select 
                value={formData.agreement_id} 
                onValueChange={handleAgreementSelect}
              >
                <SelectTrigger data-testid="agreement-select">
                  <SelectValue placeholder="Select an approved agreement" />
                </SelectTrigger>
                <SelectContent>
                  {agreements.map((agreement) => (
                    <SelectItem key={agreement.id} value={agreement.id}>
                      {agreement.agreement_number} - {agreement.party_name || agreement.client_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedAgreement && (
              <div className="grid grid-cols-3 gap-4 p-4 bg-zinc-50 rounded-sm">
                <div>
                  <div className="text-xs text-zinc-500 uppercase tracking-wide">Agreement #</div>
                  <div className="font-medium">{selectedAgreement.agreement_number}</div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 uppercase tracking-wide">Client</div>
                  <div className="font-medium">{selectedAgreement.party_name || selectedAgreement.client_name}</div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 uppercase tracking-wide">Status</div>
                  <div className="font-medium capitalize">{selectedAgreement.status}</div>
                </div>
                {quotationDetails && (
                  <>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Value</div>
                      <div className="font-medium text-emerald-600">{formatINR(quotationDetails.grand_total)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Duration</div>
                      <div className="font-medium">{selectedAgreement.project_tenure_months || 12} months</div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Eligibility Status */}
      {selectedAgreement && eligibilityStatus && (
        <Card className={`border-2 shadow-none rounded-sm mb-6 ${
          eligibilityStatus.is_eligible 
            ? 'border-emerald-200 bg-emerald-50/50' 
            : 'border-amber-200 bg-amber-50/50'
        }`}>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              {eligibilityStatus.is_eligible ? (
                <CheckCircle className="w-8 h-8 text-emerald-600" />
              ) : (
                <Clock className="w-8 h-8 text-amber-600" />
              )}
              <div className="flex-1">
                <h3 className={`font-semibold text-lg ${
                  eligibilityStatus.is_eligible ? 'text-emerald-900' : 'text-amber-900'
                }`}>
                  {eligibilityStatus.is_eligible 
                    ? 'Payment Verified - Ready for Kickoff!' 
                    : 'Payment Verification Required'}
                </h3>
                
                {eligibilityStatus.is_eligible ? (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center gap-2 text-emerald-700">
                      <Receipt className="w-4 h-4" />
                      <span>Transaction ID: <strong>{eligibilityStatus.first_installment_transaction_id}</strong></span>
                    </div>
                    <div className="flex items-center gap-2 text-emerald-700">
                      <Banknote className="w-4 h-4" />
                      <span>Amount Received: <strong>{formatINR(eligibilityStatus.first_installment_amount)}</strong></span>
                    </div>
                    {eligibilityStatus.sow_handover_complete && (
                      <div className="flex items-center gap-2 text-emerald-700">
                        <CheckCircle className="w-4 h-4" />
                        <span>SOW handed over to Consulting team</span>
                      </div>
                    )}
                    <div className="mt-4">
                      <Button 
                        onClick={handleProceedToKickoff}
                        className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm"
                        data-testid="proceed-kickoff-btn"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Create Kickoff Request
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3">
                    <p className="text-amber-700 mb-4">
                      First installment payment has not been verified yet. Please record the advance payment 
                      received from the client to proceed with the project kickoff.
                    </p>
                    <Button 
                      onClick={() => setShowVerifyDialog(true)}
                      className="bg-amber-600 text-white hover:bg-amber-700 rounded-sm"
                      data-testid="verify-payment-btn"
                    >
                      <CreditCard className="w-4 h-4 mr-2" />
                      Verify First Installment
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agreements without selection prompt */}
      {!selectedAgreement && agreements.length === 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="w-12 h-12 text-zinc-300 mb-4" />
            <p className="text-zinc-500">No approved agreements found</p>
            <p className="text-sm text-zinc-400 mt-1">Agreements must be approved before payment verification</p>
          </CardContent>
        </Card>
      )}

      {/* Payment Verification Dialog */}
      <Dialog open={showVerifyDialog} onOpenChange={setShowVerifyDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Verify First Installment
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Enter the payment details received from the client. This will enable SOW handover to Consulting.
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-sm">
              <div className="text-sm text-blue-700">
                <strong>Agreement:</strong> {selectedAgreement?.agreement_number}
                {quotationDetails && (
                  <span className="ml-2">| <strong>Total:</strong> {formatINR(quotationDetails.grand_total)}</span>
                )}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Expected Amount (₹) *</Label>
                <Input
                  type="number"
                  value={formData.expected_amount}
                  onChange={(e) => setFormData({ ...formData, expected_amount: parseFloat(e.target.value) || 0 })}
                  className="rounded-sm"
                  data-testid="expected-amount-input"
                />
                <p className="text-xs text-zinc-400">Typically 30% of total value</p>
              </div>
              <div className="space-y-2">
                <Label>Received Amount (₹) *</Label>
                <Input
                  type="number"
                  value={formData.received_amount}
                  onChange={(e) => setFormData({ ...formData, received_amount: parseFloat(e.target.value) || 0 })}
                  className="rounded-sm"
                  required
                  data-testid="received-amount-input"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Transaction ID / UTR Number *</Label>
              <Input
                value={formData.transaction_id}
                onChange={(e) => setFormData({ ...formData, transaction_id: e.target.value })}
                placeholder="Enter transaction reference number"
                className="rounded-sm"
                required
                data-testid="transaction-id-input"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Payment Date *</Label>
                <Input
                  type="date"
                  value={formData.payment_date}
                  onChange={(e) => setFormData({ ...formData, payment_date: e.target.value })}
                  className="rounded-sm"
                  required
                  data-testid="payment-date-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Payment Mode *</Label>
                <Select 
                  value={formData.payment_mode} 
                  onValueChange={(v) => setFormData({ ...formData, payment_mode: v })}
                >
                  <SelectTrigger data-testid="payment-mode-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PAYMENT_MODES.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Bank Reference / Cheque Number (Optional)</Label>
              <Input
                value={formData.bank_reference}
                onChange={(e) => setFormData({ ...formData, bank_reference: e.target.value })}
                placeholder="Bank reference or cheque number"
                className="rounded-sm"
                data-testid="bank-reference-input"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={2}
                placeholder="Any additional notes..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                data-testid="payment-notes-input"
              />
            </div>
            
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5" />
                <div className="text-sm text-amber-700">
                  <strong>Important:</strong> Verifying this payment will:
                  <ul className="list-disc list-inside mt-1">
                    <li>Mark the first installment as received</li>
                    <li>Hand over the SOW to the Consulting team</li>
                    <li>Enable kickoff request creation</li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowVerifyDialog(false)}
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting}
                className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm"
                data-testid="submit-payment-btn"
              >
                {submitting ? 'Verifying...' : 'Verify Payment'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PaymentVerification;
