import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  ArrowLeft, DollarSign, Calendar, CheckCircle, Clock, User,
  Building2, AlertCircle, Bell, Send
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';

const ProjectPaymentDetails = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [paymentData, setPaymentData] = useState(null);
  const [activeTab, setActiveTab] = useState('payments');

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      // Fetch payment data
      const paymentRes = await axios.get(`${API}/project-payments/project/${projectId}`);
      setPaymentData(paymentRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load payment data');
    } finally {
      setLoading(false);
    }
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
                    </tr>
                  </thead>
                  <tbody>
                    {paymentData.payment_schedule.map((item, idx) => (
                      <tr key={idx} className="border-b border-zinc-100">
                        <td className="py-3 px-4 text-zinc-600">{item.installment_number}</td>
                        <td className="py-3 px-4 font-medium text-zinc-900">{item.frequency}</td>
                        <td className="py-3 px-4 text-zinc-600">
                          {item.due_date ? new Date(item.due_date).toLocaleDateString() : 'TBD'}
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
                          <span className={`px-2 py-1 rounded-sm text-xs font-medium ${
                            item.status === 'received' ? 'bg-emerald-100 text-emerald-700' :
                            item.status === 'overdue' ? 'bg-red-100 text-red-700' :
                            'bg-amber-100 text-amber-700'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
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
    </div>
  );
};

export default ProjectPaymentDetails;
