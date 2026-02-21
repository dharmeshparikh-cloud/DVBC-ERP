import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  ArrowLeft, ArrowRight, CreditCard, IndianRupee, Calendar, 
  FileText, Building2, CheckCircle, Plus, Clock, Receipt,
  Banknote, Wallet
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import SalesFunnelProgress from '../../components/SalesFunnelProgress';

const PaymentRecording = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const agreementId = searchParams.get('agreementId');
  const leadId = searchParams.get('leadId');
  
  const [loading, setLoading] = useState(true);
  const [agreement, setAgreement] = useState(null);
  const [lead, setLead] = useState(null);
  const [payments, setPayments] = useState([]);
  const [recording, setRecording] = useState(false);
  
  const [formData, setFormData] = useState({
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_mode: '',
    cheque_number: '',
    utr_number: '',
    remarks: ''
  });

  useEffect(() => {
    if (agreementId) {
      fetchData();
    }
  }, [agreementId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [agrRes, paymentsRes] = await Promise.all([
        axios.get(`${API}/agreements/${agreementId}`),
        axios.get(`${API}/agreements/${agreementId}/payments`)
      ]);
      
      setAgreement(agrRes.data);
      setPayments(paymentsRes.data.payments || []);
      
      // Fetch lead if available
      if (agrRes.data.lead_id) {
        const leadRes = await axios.get(`${API}/leads/${agrRes.data.lead_id}`);
        setLead(leadRes.data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load agreement data');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordPayment = async () => {
    if (!formData.amount || !formData.payment_mode || !formData.payment_date) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (formData.payment_mode === 'Cheque' && !formData.cheque_number) {
      toast.error('Cheque number is required for Cheque payments');
      return;
    }

    if (['NEFT', 'UPI', 'RTGS'].includes(formData.payment_mode) && !formData.utr_number) {
      toast.error('UTR number is required for online transfers');
      return;
    }

    setRecording(true);
    try {
      await axios.post(`${API}/agreements/${agreementId}/record-payment`, {
        amount: parseFloat(formData.amount),
        payment_date: formData.payment_date,
        payment_mode: formData.payment_mode,
        cheque_number: formData.cheque_number || null,
        utr_number: formData.utr_number || null,
        remarks: formData.remarks || null
      });

      toast.success('Payment recorded successfully');
      
      // Reset form
      setFormData({
        amount: '',
        payment_date: new Date().toISOString().split('T')[0],
        payment_mode: '',
        cheque_number: '',
        utr_number: '',
        remarks: ''
      });
      
      // Refresh payments
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setRecording(false);
    }
  };

  const agreementValue = agreement?.total_value || agreement?.grand_total || 0;
  const totalPaid = payments.reduce((sum, p) => sum + (p.amount || 0), 0);
  const remaining = agreementValue - totalPaid;
  const paymentProgress = agreementValue > 0 ? (totalPaid / agreementValue) * 100 : 0;

  const handleProceedToKickoff = () => {
    navigate(`/sales-funnel/agreement/${agreementId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="payment-recording-page">
      {/* Sales Funnel Progress */}
      {lead && (
        <div className="mb-6">
          <SalesFunnelProgress 
            leadId={lead.id} 
            currentStep="payment"
            showNavigation={false}
          />
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate(`/sales-funnel/agreement/${agreementId}`)}
          variant="ghost"
          className="hover:bg-zinc-100 rounded-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Agreement
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 mb-2">
          Payment Recording
        </h1>
        <p className="text-zinc-500">
          Record payments for Agreement #{agreement?.agreement_number}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Agreement Info & Payment Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agreement Summary Card */}
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-500" />
                Agreement Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Agreement #</p>
                  <p className="font-medium">{agreement?.agreement_number}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Client</p>
                  <p className="font-medium">{lead?.company || agreement?.client_name || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Agreement Value</p>
                  <p className="font-semibold text-emerald-600">{formatINR(agreementValue)}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Status</p>
                  <span className={`inline-flex px-2 py-1 text-xs rounded ${
                    agreement?.status === 'signed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {agreement?.status?.charAt(0).toUpperCase() + agreement?.status?.slice(1)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Payment Progress */}
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="pt-6">
              <div className="flex justify-between items-end mb-2">
                <div>
                  <p className="text-sm text-zinc-500">Payment Progress</p>
                  <p className="text-2xl font-semibold text-emerald-600">{formatINR(totalPaid)}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-zinc-500">Remaining</p>
                  <p className="text-xl font-medium text-zinc-700">{formatINR(remaining)}</p>
                </div>
              </div>
              <div className="h-3 bg-zinc-100 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, paymentProgress)}%` }}
                />
              </div>
              <p className="text-xs text-zinc-500 mt-1 text-right">
                {paymentProgress.toFixed(1)}% of {formatINR(agreementValue)}
              </p>
            </CardContent>
          </Card>

          {/* Payment Form */}
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Plus className="w-5 h-5 text-green-500" />
                Record New Payment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Amount (₹) *</Label>
                  <div className="relative">
                    <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                    <Input
                      type="number"
                      value={formData.amount}
                      onChange={(e) => setFormData({...formData, amount: e.target.value})}
                      placeholder="0.00"
                      className="pl-9 rounded-sm"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Payment Date *</Label>
                  <Input
                    type="date"
                    value={formData.payment_date}
                    onChange={(e) => setFormData({...formData, payment_date: e.target.value})}
                    className="rounded-sm"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Payment Mode *</Label>
                <Select
                  value={formData.payment_mode}
                  onValueChange={(value) => setFormData({
                    ...formData, 
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
                        <Receipt className="w-4 h-4" />
                        Cheque
                      </div>
                    </SelectItem>
                    <SelectItem value="NEFT">
                      <div className="flex items-center gap-2">
                        <Banknote className="w-4 h-4" />
                        NEFT
                      </div>
                    </SelectItem>
                    <SelectItem value="RTGS">
                      <div className="flex items-center gap-2">
                        <Banknote className="w-4 h-4" />
                        RTGS
                      </div>
                    </SelectItem>
                    <SelectItem value="UPI">
                      <div className="flex items-center gap-2">
                        <Wallet className="w-4 h-4" />
                        UPI
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formData.payment_mode === 'Cheque' && (
                <div className="space-y-2">
                  <Label>Cheque Number *</Label>
                  <Input
                    value={formData.cheque_number}
                    onChange={(e) => setFormData({...formData, cheque_number: e.target.value})}
                    placeholder="Enter cheque number"
                    className="rounded-sm"
                  />
                </div>
              )}

              {['NEFT', 'RTGS', 'UPI'].includes(formData.payment_mode) && (
                <div className="space-y-2">
                  <Label>UTR / Reference Number *</Label>
                  <Input
                    value={formData.utr_number}
                    onChange={(e) => setFormData({...formData, utr_number: e.target.value})}
                    placeholder="Enter UTR or reference number"
                    className="rounded-sm"
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label>Remarks (Optional)</Label>
                <Textarea
                  value={formData.remarks}
                  onChange={(e) => setFormData({...formData, remarks: e.target.value})}
                  placeholder="Any additional notes about this payment..."
                  rows={2}
                  className="rounded-sm"
                />
              </div>

              <Button
                onClick={handleRecordPayment}
                disabled={recording || !formData.amount || !formData.payment_mode}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                {recording ? (
                  'Recording...'
                ) : (
                  <>
                    <CreditCard className="w-4 h-4 mr-2" />
                    Record Payment
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Payment History & Actions */}
        <div className="space-y-6">
          {/* Payment History */}
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-500" />
                Payment History ({payments.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {payments.length === 0 ? (
                <div className="text-center py-8 text-zinc-400">
                  <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No payments recorded yet</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto">
                  {payments.map((payment, index) => (
                    <div
                      key={payment.id || index}
                      className="p-3 bg-zinc-50 rounded-lg border border-zinc-100"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-semibold text-emerald-600">
                            {formatINR(payment.amount)}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {new Date(payment.payment_date).toLocaleDateString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric'
                            })}
                          </p>
                        </div>
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          {payment.payment_mode}
                        </span>
                      </div>
                      {payment.cheque_number && (
                        <p className="text-xs text-zinc-500">
                          Cheque #: {payment.cheque_number}
                        </p>
                      )}
                      {payment.utr_number && (
                        <p className="text-xs text-zinc-500">
                          UTR: {payment.utr_number}
                        </p>
                      )}
                      {payment.remarks && (
                        <p className="text-xs text-zinc-600 mt-1 italic">
                          {payment.remarks}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Next Step Action */}
          <Card className="border-orange-200 bg-orange-50 shadow-none rounded-sm">
            <CardContent className="pt-6">
              <div className="text-center">
                <CheckCircle className="w-10 h-10 text-orange-500 mx-auto mb-3" />
                <h3 className="font-semibold text-zinc-800 mb-2">Ready for Kickoff?</h3>
                <p className="text-sm text-zinc-600 mb-4">
                  After recording payments, proceed to create the project kickoff request.
                </p>
                <Button
                  onClick={handleProceedToKickoff}
                  className="w-full bg-orange-500 hover:bg-orange-600"
                >
                  Proceed to Kickoff
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PaymentRecording;
