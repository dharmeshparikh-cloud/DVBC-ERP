import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { 
  ArrowLeft, DollarSign, Calendar, CheckCircle, Clock, User,
  Building2, AlertCircle, Bell, Send, CreditCard
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';

const ProjectPaymentDetails = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [paymentData, setPaymentData] = useState(null);
  const [installmentPayments, setInstallmentPayments] = useState([]);
  const [activeTab, setActiveTab] = useState('payments');
  const [reminderEligibility, setReminderEligibility] = useState({});
  
  // Modal states
  const [showRecordPaymentDialog, setShowRecordPaymentDialog] = useState(false);
  const [selectedInstallment, setSelectedInstallment] = useState(null);
  const [transactionId, setTransactionId] = useState('');
  const [amountReceived, setAmountReceived] = useState('');
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);
  const [remarks, setRemarks] = useState('');
  const [sendingReminder, setSendingReminder] = useState({});
  const [recordingPayment, setRecordingPayment] = useState(false);

  // Check if user is from consulting team
  const isConsultingTeam = ['admin', 'principal_consultant', 'project_manager', 'manager', 'consultant', 'lead_consultant', 'senior_consultant'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      // Fetch payment data
      const paymentRes = await axios.get(`${API}/project-payments/project/${projectId}`);
      setPaymentData(paymentRes.data);

      // Fetch recorded installment payments
      try {
        const installmentsRes = await axios.get(`${API}/project-payments/installment-payments/${projectId}`);
        setInstallmentPayments(installmentsRes.data.payments || []);
      } catch (e) {
        console.log('No installment payments found');
      }

      // Check reminder eligibility for each installment
      if (paymentRes.data.payment_schedule) {
        const eligibilityChecks = {};
        for (const item of paymentRes.data.payment_schedule) {
          try {
            const eligRes = await axios.get(
              `${API}/project-payments/check-reminder-eligibility/${projectId}/${item.installment_number}`
            );
            eligibilityChecks[item.installment_number] = eligRes.data;
          } catch (e) {
            eligibilityChecks[item.installment_number] = { eligible: false };
          }
        }
        setReminderEligibility(eligibilityChecks);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load payment data');
    } finally {
      setLoading(false);
    }
  };

  const handleSendReminder = async (installmentNumber) => {
    setSendingReminder(prev => ({ ...prev, [installmentNumber]: true }));
    try {
      await axios.post(`${API}/project-payments/send-reminder`, {
        project_id: projectId,
        installment_number: installmentNumber
      });
      toast.success(`Payment reminder sent for installment #${installmentNumber}`);
      // Refresh eligibility
      const eligRes = await axios.get(
        `${API}/project-payments/check-reminder-eligibility/${projectId}/${installmentNumber}`
      );
      setReminderEligibility(prev => ({ ...prev, [installmentNumber]: eligRes.data }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reminder');
    } finally {
      setSendingReminder(prev => ({ ...prev, [installmentNumber]: false }));
    }
  };

  const openRecordPaymentDialog = (installment) => {
    setSelectedInstallment(installment);
    setAmountReceived(installment.net || '');
    setTransactionId('');
    setRemarks('');
    setPaymentDate(new Date().toISOString().split('T')[0]);
    setShowRecordPaymentDialog(true);
  };

  const handleRecordPayment = async () => {
    if (!transactionId.trim()) {
      toast.error('Please enter transaction ID');
      return;
    }
    if (!amountReceived || parseFloat(amountReceived) <= 0) {
      toast.error('Please enter valid amount');
      return;
    }

    setRecordingPayment(true);
    try {
      await axios.post(`${API}/project-payments/record-payment`, {
        project_id: projectId,
        installment_number: selectedInstallment.installment_number,
        transaction_id: transactionId,
        amount_received: parseFloat(amountReceived),
        payment_date: paymentDate,
        remarks: remarks
      });
      toast.success(`Payment recorded for installment #${selectedInstallment.installment_number}`);
      setShowRecordPaymentDialog(false);
      fetchData(); // Refresh data
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setRecordingPayment(false);
    }
  };

  // Check if installment has been paid
  const getInstallmentPayment = (installmentNumber) => {
    return installmentPayments.find(p => p.installment_number === installmentNumber);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (!paymentData) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertCircle className="w-12 h-12 text-zinc-300 mb-4" />
        <p className="text-zinc-500">Payment data not found</p>
        <Button onClick={() => navigate(-1)} variant="outline" className="mt-4">
          Go Back
        </Button>
      </div>
    );
  }

  // Role-based visibility flags from API
  const canViewAmounts = paymentData.can_view_amounts;
  const isConsultantView = paymentData.is_consultant_view;

  return (
    <div data-testid="project-payment-details">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/payments')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
          data-testid="back-to-payments-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Payments
        </Button>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              {paymentData.project_name}
            </h1>
            <p className="text-zinc-500 flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              {paymentData.client_name}
            </p>
          </div>
          {/* Only show total value to users with amount visibility */}
          {canViewAmounts && paymentData.total_value && (
            <div className="text-right">
              <div className="text-sm text-zinc-500">Total Project Value</div>
              <div className="text-2xl font-bold text-zinc-900">{formatINR(paymentData.total_value)}</div>
            </div>
          )}
        </div>
      </div>

      {/* First Advance Payment - Only visible to admin/principal_consultant */}
      {paymentData.first_advance_payment && canViewAmounts && (
        <Card className={`mb-6 border-2 shadow-none rounded-sm ${
          paymentData.first_advance_payment?.received 
            ? 'border-emerald-200 bg-emerald-50/50' 
            : 'border-amber-200 bg-amber-50/50'
        }`} data-testid="first-advance-payment-card">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              {paymentData.first_advance_payment?.received ? (
                <CheckCircle className="w-8 h-8 text-emerald-600" />
              ) : (
                <Clock className="w-8 h-8 text-amber-600" />
              )}
              <div className="flex-1">
                <h3 className={`font-semibold text-lg ${
                  paymentData.first_advance_payment?.received ? 'text-emerald-900' : 'text-amber-900'
                }`}>
                  First Advance Payment {paymentData.first_advance_payment?.received ? '- Received' : '- Pending'}
                </h3>
                
                {paymentData.first_advance_payment?.received && (
                  <div className="mt-3 grid grid-cols-4 gap-4">
                    <div>
                      <div className="text-xs text-emerald-600 uppercase tracking-wide">Amount</div>
                      <div className="font-semibold text-emerald-900">
                        {formatINR(paymentData.first_advance_payment.amount)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-emerald-600 uppercase tracking-wide">Transaction ID</div>
                      <div className="font-medium text-emerald-900">
                        {paymentData.first_advance_payment.transaction_id}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-emerald-600 uppercase tracking-wide">Payment Date</div>
                      <div className="font-medium text-emerald-900">
                        {new Date(paymentData.first_advance_payment.payment_date).toLocaleDateString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-emerald-600 uppercase tracking-wide">Verified By</div>
                      <div className="font-medium text-emerald-900">
                        {paymentData.first_advance_payment.verified_by || 'Sales Team'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs - Only Payment Schedule and Consultant Breakdown */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeTab === 'payments' ? 'default' : 'outline'}
          onClick={() => setActiveTab('payments')}
          className="rounded-sm"
          data-testid="payment-schedule-tab"
        >
          <DollarSign className="w-4 h-4 mr-2" />
          Payment Schedule
        </Button>
        <Button
          variant={activeTab === 'consultants' ? 'default' : 'outline'}
          onClick={() => setActiveTab('consultants')}
          className="rounded-sm"
          data-testid="consultant-breakdown-tab"
        >
          <User className="w-4 h-4 mr-2" />
          Consultant Breakdown
        </Button>
      </div>

      {/* Payment Schedule Tab */}
      {activeTab === 'payments' && (
        <Card className="border-zinc-200 shadow-none rounded-sm" data-testid="payment-schedule-content">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
              {isConsultantView ? 'Upcoming Payment Dates' : `Payment Schedule (${paymentData.payment_frequency})`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {paymentData.payment_schedule.length === 0 ? (
              <div className="text-center py-8 text-zinc-500">
                No payment schedule defined in pricing plan
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-zinc-200">
                      <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">#</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Frequency</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Due Date</th>
                      {/* Only show amount columns if user can view amounts */}
                      {canViewAmounts && (
                        <>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Basic</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">GST</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">TDS</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Net</th>
                        </>
                      )}
                      <th className="text-center py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Status</th>
                      {isConsultingTeam && (
                        <th className="text-center py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Actions</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {paymentData.payment_schedule.map((item, idx) => {
                      const eligibility = reminderEligibility[item.installment_number] || {};
                      const recordedPayment = getInstallmentPayment(item.installment_number);
                      const isReminderEnabled = eligibility.eligible && !recordedPayment;
                      const canRecordPayment = isConsultingTeam && !recordedPayment && item.status !== 'received';
                      
                      return (
                        <tr key={idx} className="border-b border-zinc-100">
                          <td className="py-3 px-4 text-zinc-600">{item.installment_number}</td>
                          <td className="py-3 px-4 font-medium text-zinc-900">{item.frequency}</td>
                          <td className="py-3 px-4 text-zinc-600">
                            {item.due_date ? new Date(item.due_date).toLocaleDateString() : 'TBD'}
                            {eligibility.days_until_due !== undefined && eligibility.days_until_due >= 0 && eligibility.days_until_due <= 7 && !recordedPayment && (
                              <span className="ml-2 text-xs text-amber-600 font-medium">
                                ({eligibility.days_until_due === 0 ? 'Due today' : `${eligibility.days_until_due}d left`})
                              </span>
                            )}
                          </td>
                          {/* Only show amount values if user can view amounts */}
                          {canViewAmounts && (
                            <>
                              <td className="py-3 px-4 text-right text-zinc-600">{formatINR(item.basic)}</td>
                              <td className="py-3 px-4 text-right text-zinc-600">{formatINR(item.gst)}</td>
                              <td className="py-3 px-4 text-right text-zinc-600">{formatINR(item.tds)}</td>
                              <td className="py-3 px-4 text-right font-semibold text-zinc-900">{formatINR(item.net)}</td>
                            </>
                          )}
                          <td className="py-3 px-4 text-center">
                            {recordedPayment ? (
                              <div className="flex flex-col items-center">
                                <span className="px-2 py-1 rounded-sm text-xs font-medium bg-emerald-100 text-emerald-700">
                                  received
                                </span>
                                <span className="text-xs text-zinc-500 mt-1">
                                  {recordedPayment.transaction_id}
                                </span>
                              </div>
                            ) : (
                              <span className={`px-2 py-1 rounded-sm text-xs font-medium ${
                                item.status === 'received' ? 'bg-emerald-100 text-emerald-700' :
                                item.status === 'overdue' ? 'bg-red-100 text-red-700' :
                                'bg-amber-100 text-amber-700'
                              }`}>
                                {item.status}
                              </span>
                            )}
                          </td>
                          {isConsultingTeam && (
                            <td className="py-3 px-4">
                              <div className="flex items-center justify-center gap-2">
                                {/* Send Reminder Button */}
                                <Button
                                  size="sm"
                                  variant={isReminderEnabled ? "default" : "outline"}
                                  className={`rounded-sm h-8 px-2 ${
                                    isReminderEnabled 
                                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white' 
                                      : 'text-zinc-400 cursor-not-allowed'
                                  }`}
                                  disabled={!isReminderEnabled || sendingReminder[item.installment_number]}
                                  onClick={() => isReminderEnabled && handleSendReminder(item.installment_number)}
                                  title={
                                    recordedPayment ? 'Payment already received' :
                                    !eligibility.within_reminder_window ? `Reminder available ${eligibility.days_until_due > 7 ? 'in ' + (eligibility.days_until_due - 7) + ' days' : 'when due date is within 7 days'}` :
                                    'Send payment reminder to client'
                                  }
                                  data-testid={`send-reminder-btn-${item.installment_number}`}
                                >
                                  {sendingReminder[item.installment_number] ? (
                                    <span className="animate-spin">⏳</span>
                                  ) : (
                                    <>
                                      <Bell className="w-3 h-3 mr-1" />
                                      Remind
                                    </>
                                  )}
                                </Button>
                                
                                {/* Record Payment Button */}
                                {canRecordPayment && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="rounded-sm h-8 px-2"
                                    onClick={() => openRecordPaymentDialog(item)}
                                    data-testid={`record-payment-btn-${item.installment_number}`}
                                  >
                                    <CreditCard className="w-3 h-3 mr-1" />
                                    Record
                                  </Button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Consultant Breakdown Tab */}
      {activeTab === 'consultants' && (
        <Card className="border-zinc-200 shadow-none rounded-sm" data-testid="consultant-breakdown-content">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
              Assigned Consultants
            </CardTitle>
          </CardHeader>
          <CardContent>
            {paymentData.consultant_breakdown.length === 0 ? (
              <div className="text-center py-8 text-zinc-500">
                No consultants assigned yet
              </div>
            ) : (
              <div className="space-y-4">
                {paymentData.consultant_breakdown.map((consultant, idx) => (
                  <div key={idx} className="p-4 border border-zinc-200 rounded-sm" data-testid={`consultant-card-${idx}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold text-zinc-900">{consultant.consultant_name}</h4>
                        <div className="text-sm text-zinc-500">
                          {consultant.employee_id} | {consultant.role_in_project}
                        </div>
                        <div className="text-sm text-zinc-500 mt-1">
                          Assigned: {new Date(consultant.assigned_date).toLocaleDateString()}
                        </div>
                      </div>
                      {/* Only show payment info if user can view amounts */}
                      {canViewAmounts && consultant.payment_info && (
                        <div className="text-right">
                          <div className="text-sm text-zinc-500">Rate per Meeting</div>
                          <div className="font-semibold text-zinc-900">
                            {formatINR(consultant.payment_info.rate_per_meeting)}
                          </div>
                          <div className="text-sm text-zinc-500 mt-2">
                            {consultant.payment_info.committed_meetings} meetings committed
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Record Payment Dialog */}
      <Dialog open={showRecordPaymentDialog} onOpenChange={setShowRecordPaymentDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Record Payment - Installment #{selectedInstallment?.installment_number}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="bg-zinc-50 p-3 rounded-sm">
              <div className="text-sm text-zinc-500">Installment</div>
              <div className="font-medium">{selectedInstallment?.frequency}</div>
              {canViewAmounts && (
                <>
                  <div className="text-sm text-zinc-500 mt-2">Expected Amount</div>
                  <div className="font-semibold">{formatINR(selectedInstallment?.net || 0)}</div>
                </>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="transaction_id">Transaction ID *</Label>
              <Input
                id="transaction_id"
                placeholder="Enter transaction ID (e.g., NEFT-123456)"
                value={transactionId}
                onChange={(e) => setTransactionId(e.target.value)}
                data-testid="transaction-id-input"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="amount_received">Amount Received (₹) *</Label>
              <Input
                id="amount_received"
                type="number"
                placeholder="Enter amount received"
                value={amountReceived}
                onChange={(e) => setAmountReceived(e.target.value)}
                data-testid="amount-received-input"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="payment_date">Payment Date</Label>
              <Input
                id="payment_date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                data-testid="payment-date-input"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="remarks">Remarks (Optional)</Label>
              <Input
                id="remarks"
                placeholder="Any additional notes"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                data-testid="remarks-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRecordPaymentDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleRecordPayment} 
              disabled={recordingPayment}
              data-testid="confirm-record-payment-btn"
            >
              {recordingPayment ? 'Recording...' : 'Record Payment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectPaymentDetails;
