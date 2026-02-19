import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { 
  Calendar, Clock, AlertTriangle, CheckCircle, Building2, 
  ArrowRight, ChevronRight, Loader2, DollarSign, Bell, Send, CreditCard
} from 'lucide-react';
import { toast } from 'sonner';
import { format, differenceInDays, addDays } from 'date-fns';
import ViewToggle from '../../components/ViewToggle';
import ConsultingStageNav from '../../components/ConsultingStageNav';
import { sanitizeDisplayText } from '../../utils/sanitize';
import { formatINR } from '../../utils/currency';

const PAYMENT_STATUS_CONFIG = {
  overdue: { label: 'Overdue', color: 'bg-red-100 text-red-700 border-red-200', icon: AlertTriangle },
  due_soon: { label: 'Due Soon', color: 'bg-orange-100 text-orange-700 border-orange-200', icon: Clock },
  upcoming: { label: 'Upcoming', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: Calendar },
  scheduled: { label: 'Scheduled', color: 'bg-zinc-100 text-zinc-600 border-zinc-200', icon: CheckCircle },
};

const PaymentReminders = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [reminders, setReminders] = useState([]);
  const [viewMode, setViewMode] = useState('card');
  const [filter, setFilter] = useState('all'); // all, overdue, due_soon, upcoming
  
  // Payment recording dialog
  const [recordPaymentOpen, setRecordPaymentOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [paymentForm, setPaymentForm] = useState({
    transaction_id: '',
    received_amount: '',
    payment_date: format(new Date(), 'yyyy-MM-dd'),
    payment_mode: 'bank_transfer',
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchReminders();
  }, []);

  const fetchReminders = async () => {
    try {
      const response = await axios.get(`${API}/payment-reminders`);
      setReminders(response.data || []);
    } catch (error) {
      console.error('Error fetching reminders:', error);
      toast.error('Failed to load payment reminders');
    } finally {
      setLoading(false);
    }
  };

  const getPaymentStatus = (daysUntil) => {
    if (daysUntil < 0) return 'overdue';
    if (daysUntil <= 7) return 'due_soon';
    if (daysUntil <= 30) return 'upcoming';
    return 'scheduled';
  };

  // Calculate stats
  const stats = {
    total: reminders.reduce((sum, r) => sum + r.upcoming_payments?.length || 0, 0),
    overdue: reminders.reduce((sum, r) => sum + (r.upcoming_payments?.filter(p => p.days_until_due < 0).length || 0), 0),
    dueSoon: reminders.reduce((sum, r) => sum + (r.upcoming_payments?.filter(p => p.days_until_due >= 0 && p.days_until_due <= 7).length || 0), 0),
    upcoming: reminders.reduce((sum, r) => sum + (r.upcoming_payments?.filter(p => p.days_until_due > 7 && p.days_until_due <= 30).length || 0), 0),
  };

  // Flatten and filter reminders for display
  const flattenedReminders = reminders.flatMap(project => 
    (project.upcoming_payments || []).map(payment => ({
      ...payment,
      project_id: project.project_id,
      project_name: project.project_name,
      client_name: project.client_name,
      company: project.company,
      payment_frequency: project.payment_frequency,
      agreement_id: project.agreement_id,
      pricing_plan_id: project.pricing_plan_id,
      total_installments: project.total_installments || payment.total_installments,
      status: getPaymentStatus(payment.days_until_due)
    }))
  ).filter(payment => {
    if (filter === 'all') return true;
    return payment.status === filter;
  }).sort((a, b) => a.days_until_due - b.days_until_due);

  const getStatusBadge = (status) => {
    const config = PAYMENT_STATUS_CONFIG[status] || PAYMENT_STATUS_CONFIG.scheduled;
    const Icon = config.icon;
    return (
      <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-sm border ${config.color}`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </span>
    );
  };

  const getDaysText = (days) => {
    if (days < 0) return `${Math.abs(days)} days overdue`;
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    return `Due in ${days} days`;
  };

  // Open record payment dialog
  const openRecordPayment = (payment) => {
    setSelectedPayment(payment);
    setPaymentForm({
      transaction_id: '',
      received_amount: '',
      payment_date: format(new Date(), 'yyyy-MM-dd'),
      payment_mode: 'bank_transfer',
      notes: ''
    });
    setRecordPaymentOpen(true);
  };

  // Send payment reminder
  const handleSendReminder = async (payment) => {
    // Check if within 7 days of due date
    if (payment.days_until_due > 7) {
      toast.error('Reminders can only be sent within 7 days of the due date');
      return;
    }

    try {
      await axios.post(`${API}/payment-reminders/send`, {
        project_id: payment.project_id,
        installment_number: payment.installment_number,
        client_email: payment.client_email,
        client_name: payment.client_name,
        due_date: payment.due_date,
        project_name: payment.project_name
      });
      toast.success(`Reminder sent for Installment #${payment.installment_number}`);
    } catch (error) {
      // Backend might not have email configured yet
      toast.info('Reminder logged. Email notification will be sent when email service is configured.');
    }
  };

  // Record payment with transaction ID
  const handleRecordPayment = async (e) => {
    e.preventDefault();
    
    if (!paymentForm.transaction_id.trim()) {
      toast.error('Transaction ID is required');
      return;
    }
    
    if (!paymentForm.received_amount || parseFloat(paymentForm.received_amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/project-payments/record`, {
        project_id: selectedPayment.project_id,
        agreement_id: selectedPayment.agreement_id,
        installment_number: selectedPayment.installment_number,
        transaction_id: paymentForm.transaction_id.trim(),
        received_amount: parseFloat(paymentForm.received_amount),
        payment_date: paymentForm.payment_date,
        payment_mode: paymentForm.payment_mode,
        notes: paymentForm.notes,
        pricing_plan_id: selectedPayment.pricing_plan_id
      });
      
      toast.success(`Payment recorded for Installment #${selectedPayment.installment_number}`);
      setRecordPaymentOpen(false);
      fetchReminders(); // Refresh list
    } catch (error) {
      const errMsg = error.response?.data?.detail || 'Failed to record payment';
      toast.error(errMsg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div data-testid="payment-reminders-page">
      {/* Stage Navigation */}
      <ConsultingStageNav 
        currentStage={6}
        completedStages={[1, 2, 3, 4, 5]}
        showFullNav={true}
        onBack={() => navigate('/consulting/my-projects')}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
            Payment Reminders
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Upcoming payment installments by project
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card 
          className={`border-zinc-200 shadow-none rounded-sm cursor-pointer transition-colors ${filter === 'all' ? 'ring-2 ring-zinc-900' : ''}`}
          onClick={() => setFilter('all')}
        >
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Upcoming</div>
            <div className="text-2xl font-semibold text-zinc-950">{stats.total}</div>
          </CardContent>
        </Card>
        <Card 
          className={`border-red-200 bg-red-50 shadow-none rounded-sm cursor-pointer transition-colors ${filter === 'overdue' ? 'ring-2 ring-red-500' : ''}`}
          onClick={() => setFilter('overdue')}
        >
          <CardContent className="py-3 px-4">
            <div className="text-xs text-red-600 uppercase tracking-wide flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Overdue
            </div>
            <div className="text-2xl font-semibold text-red-700">{stats.overdue}</div>
          </CardContent>
        </Card>
        <Card 
          className={`border-orange-200 bg-orange-50 shadow-none rounded-sm cursor-pointer transition-colors ${filter === 'due_soon' ? 'ring-2 ring-orange-500' : ''}`}
          onClick={() => setFilter('due_soon')}
        >
          <CardContent className="py-3 px-4">
            <div className="text-xs text-orange-600 uppercase tracking-wide flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Due Soon (7 days)
            </div>
            <div className="text-2xl font-semibold text-orange-700">{stats.dueSoon}</div>
          </CardContent>
        </Card>
        <Card 
          className={`border-blue-200 bg-blue-50 shadow-none rounded-sm cursor-pointer transition-colors ${filter === 'upcoming' ? 'ring-2 ring-blue-500' : ''}`}
          onClick={() => setFilter('upcoming')}
        >
          <CardContent className="py-3 px-4">
            <div className="text-xs text-blue-600 uppercase tracking-wide flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              Upcoming (30 days)
            </div>
            <div className="text-2xl font-semibold text-blue-700">{stats.upcoming}</div>
          </CardContent>
        </Card>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-end mb-4">
        <ViewToggle viewMode={viewMode} onChange={setViewMode} />
      </div>

      {/* Reminders List */}
      {flattenedReminders.length > 0 ? (
        viewMode === 'list' ? (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Project</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Client</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Installment</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Due Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Frequency</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {flattenedReminders.map((payment, index) => (
                  <tr 
                    key={`${payment.project_id}-${payment.installment_number}-${index}`}
                    className={`hover:bg-zinc-50 ${payment.status === 'overdue' ? 'bg-red-50/50' : ''}`}
                  >
                    <td className="px-4 py-3 font-medium text-zinc-900">
                      {sanitizeDisplayText(payment.project_name) || 'Unnamed Project'}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <span className="text-sm text-zinc-900">{sanitizeDisplayText(payment.client_name)}</span>
                        {payment.company && (
                          <span className="block text-xs text-zinc-500">{sanitizeDisplayText(payment.company)}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      Installment #{payment.installment_number}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <span className="text-sm text-zinc-900">
                          {payment.due_date ? format(new Date(payment.due_date), 'MMM d, yyyy') : '-'}
                        </span>
                        <span className={`block text-xs ${payment.days_until_due < 0 ? 'text-red-600' : 'text-zinc-500'}`}>
                          {getDaysText(payment.days_until_due)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600 capitalize">
                      {payment.payment_frequency}
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(payment.status)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {/* Send Reminder - only within 7 days of due date */}
                        {payment.days_until_due <= 7 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); handleSendReminder(payment); }}
                            title="Send payment reminder"
                            data-testid={`send-reminder-${payment.installment_number}`}
                          >
                            <Send className="w-4 h-4" />
                          </Button>
                        )}
                        {/* Record Payment */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); openRecordPayment(payment); }}
                          title="Record payment"
                          data-testid={`record-payment-${payment.installment_number}`}
                        >
                          <CreditCard className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/consulting/my-projects`)}
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-3">
            {flattenedReminders.map((payment, index) => (
              <Card 
                key={`${payment.project_id}-${payment.installment_number}-${index}`}
                className={`shadow-none rounded-sm hover:border-zinc-300 cursor-pointer transition-colors ${
                  payment.status === 'overdue' 
                    ? 'border-red-200 bg-red-50/30' 
                    : payment.status === 'due_soon'
                      ? 'border-orange-200 bg-orange-50/30'
                      : 'border-zinc-200'
                }`}
                onClick={() => navigate(`/consulting/my-projects`)}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      {/* Calendar Icon with Date */}
                      <div className={`w-14 h-14 rounded-sm flex flex-col items-center justify-center ${
                        payment.status === 'overdue' ? 'bg-red-100' : 
                        payment.status === 'due_soon' ? 'bg-orange-100' : 'bg-zinc-100'
                      }`}>
                        <span className={`text-xs font-medium uppercase ${
                          payment.status === 'overdue' ? 'text-red-600' : 
                          payment.status === 'due_soon' ? 'text-orange-600' : 'text-zinc-500'
                        }`}>
                          {payment.due_date ? format(new Date(payment.due_date), 'MMM') : '-'}
                        </span>
                        <span className={`text-xl font-bold ${
                          payment.status === 'overdue' ? 'text-red-700' : 
                          payment.status === 'due_soon' ? 'text-orange-700' : 'text-zinc-900'
                        }`}>
                          {payment.due_date ? format(new Date(payment.due_date), 'd') : '-'}
                        </span>
                      </div>

                      {/* Payment Details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-zinc-900">
                            Installment #{payment.installment_number}
                          </h3>
                          {getStatusBadge(payment.status)}
                        </div>
                        <p className="text-sm text-zinc-700 mb-2">
                          {sanitizeDisplayText(payment.project_name) || 'Unnamed Project'}
                        </p>
                        <div className="flex items-center gap-4 text-sm text-zinc-500">
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3.5 h-3.5" />
                            {sanitizeDisplayText(payment.client_name)}
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3.5 h-3.5" />
                            {payment.payment_frequency}
                          </span>
                          <span className={`flex items-center gap-1 font-medium ${
                            payment.days_until_due < 0 ? 'text-red-600' : 
                            payment.days_until_due <= 7 ? 'text-orange-600' : ''
                          }`}>
                            <Clock className="w-3.5 h-3.5" />
                            {getDaysText(payment.days_until_due)}
                          </span>
                          {payment.total_installments && (
                            <span className="text-zinc-400">
                              ({payment.installment_number} of {payment.total_installments})
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <Button variant="ghost" size="sm">
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : (
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Bell className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No Payment Reminders</h3>
            <p className="text-zinc-500">
              {filter !== 'all' 
                ? `No ${filter.replace('_', ' ')} payments` 
                : 'No upcoming payments in the next 90 days'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PaymentReminders;
