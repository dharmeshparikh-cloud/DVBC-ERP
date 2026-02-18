import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  DollarSign, Calendar, CheckCircle, Clock, AlertCircle, 
  ArrowRight, Building2, User, TrendingUp, Eye
} from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';

const ProjectPayments = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [myPayments, setMyPayments] = useState({ payments: [], total_projects: 0 });
  const [upcomingPayments, setUpcomingPayments] = useState({ payments: [], total_upcoming: 0 });
  const [activeTab, setActiveTab] = useState('overview');

  // Check if user can view all payments (Admin, Principal Consultant, PM)
  const canViewAllPayments = ['admin', 'principal_consultant', 'project_manager', 'manager'].includes(user?.role);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      // Fetch my payments
      const myPaymentsRes = await axios.get(`${API}/project-payments/my-payments`);
      setMyPayments(myPaymentsRes.data);

      // Fetch upcoming payments (only for authorized roles)
      if (canViewAllPayments) {
        try {
          const upcomingRes = await axios.get(`${API}/project-payments/upcoming`);
          setUpcomingPayments(upcomingRes.data);
        } catch (e) {
          console.log('Cannot fetch upcoming payments');
        }
      }
    } catch (error) {
      console.error('Failed to fetch payments:', error);
      toast.error('Failed to load payment data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'received': return 'text-emerald-600 bg-emerald-50';
      case 'pending': return 'text-amber-600 bg-amber-50';
      case 'overdue': return 'text-red-600 bg-red-50';
      default: return 'text-zinc-600 bg-zinc-50';
    }
  };

  // Calculate totals
  const totalReceived = myPayments.payments
    .filter(p => p.first_payment_received)
    .reduce((sum, p) => sum + (p.first_payment_amount || 0), 0);
  
  const totalValue = myPayments.payments
    .reduce((sum, p) => sum + (p.total_value || 0), 0);
  
  const totalUpcoming = upcomingPayments.payments
    .reduce((sum, p) => sum + (p.amount || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading payments...</div>
      </div>
    );
  }

  return (
    <div data-testid="project-payments-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Project Payments
        </h1>
        <p className="text-zinc-500">
          Track payment schedules and received amounts for your projects
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-emerald-100 text-sm uppercase tracking-wide">Total Received</p>
                <p className="text-2xl font-bold mt-1">{formatINR(totalReceived)}</p>
              </div>
              <CheckCircle className="w-10 h-10 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm uppercase tracking-wide">Total Project Value</p>
                <p className="text-2xl font-bold mt-1">{formatINR(totalValue)}</p>
              </div>
              <TrendingUp className="w-10 h-10 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-amber-100 text-sm uppercase tracking-wide">Active Projects</p>
                <p className="text-2xl font-bold mt-1">{myPayments.total_projects}</p>
              </div>
              <Building2 className="w-10 h-10 opacity-50" />
            </div>
          </CardContent>
        </Card>

        {canViewAllPayments && (
          <Card className="border-zinc-200 shadow-none rounded-sm bg-gradient-to-br from-purple-500 to-purple-600 text-white">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm uppercase tracking-wide">Upcoming Amount</p>
                  <p className="text-2xl font-bold mt-1">{formatINR(totalUpcoming)}</p>
                </div>
                <Calendar className="w-10 h-10 opacity-50" />
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeTab === 'overview' ? 'default' : 'outline'}
          onClick={() => setActiveTab('overview')}
          className="rounded-sm"
        >
          My Projects
        </Button>
        {canViewAllPayments && (
          <Button
            variant={activeTab === 'upcoming' ? 'default' : 'outline'}
            onClick={() => setActiveTab('upcoming')}
            className="rounded-sm"
          >
            Upcoming Payments
          </Button>
        )}
      </div>

      {/* My Projects Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {myPayments.payments.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <DollarSign className="w-12 h-12 text-zinc-300 mb-4" />
                <p className="text-zinc-500">No project payments found</p>
                <p className="text-sm text-zinc-400 mt-1">Projects will appear here once assigned</p>
              </CardContent>
            </Card>
          ) : (
            myPayments.payments.map((payment) => (
              <Card 
                key={payment.project_id} 
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
              >
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-zinc-900">
                          {payment.project_name}
                        </h3>
                        <span className={`px-2 py-1 rounded-sm text-xs font-medium ${
                          payment.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-100 text-zinc-700'
                        }`}>
                          {payment.status}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm text-zinc-500 mb-4">
                        <span className="flex items-center gap-1">
                          <Building2 className="w-4 h-4" />
                          {payment.client_name}
                        </span>
                        {payment.start_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            Started: {new Date(payment.start_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div className="p-3 bg-zinc-50 rounded-sm">
                          <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Value</div>
                          <div className="text-lg font-semibold text-zinc-900 mt-1">
                            {formatINR(payment.total_value)}
                          </div>
                        </div>
                        <div className={`p-3 rounded-sm ${payment.first_payment_received ? 'bg-emerald-50' : 'bg-amber-50'}`}>
                          <div className={`text-xs uppercase tracking-wide ${payment.first_payment_received ? 'text-emerald-600' : 'text-amber-600'}`}>
                            First Payment
                          </div>
                          <div className={`text-lg font-semibold mt-1 ${payment.first_payment_received ? 'text-emerald-700' : 'text-amber-700'}`}>
                            {payment.first_payment_received 
                              ? formatINR(payment.first_payment_amount) 
                              : 'Pending'}
                          </div>
                        </div>
                        <div className="p-3 bg-blue-50 rounded-sm">
                          <div className="text-xs text-blue-600 uppercase tracking-wide">Upcoming</div>
                          <div className="text-lg font-semibold text-blue-700 mt-1">
                            {payment.upcoming_payments_count} payments
                          </div>
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/projects/${payment.project_id}/payments`)}
                      className="rounded-sm"
                    >
                      <Eye className="w-4 h-4 mr-2" />
                      View Details
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Upcoming Payments Tab */}
      {activeTab === 'upcoming' && canViewAllPayments && (
        <div className="space-y-4">
          {upcomingPayments.payments.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Calendar className="w-12 h-12 text-zinc-300 mb-4" />
                <p className="text-zinc-500">No upcoming payments scheduled</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
                  Upcoming Payment Schedule
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-zinc-200">
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Project</th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Client</th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Installment</th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Due Date</th>
                        <th className="text-right py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Amount</th>
                        <th className="text-center py-3 px-4 text-xs font-semibold text-zinc-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {upcomingPayments.payments.map((payment, idx) => (
                        <tr 
                          key={idx} 
                          className="border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer"
                          onClick={() => navigate(`/projects/${payment.project_id}/payments`)}
                        >
                          <td className="py-3 px-4">
                            <div className="font-medium text-zinc-900">{payment.project_name}</div>
                          </td>
                          <td className="py-3 px-4 text-zinc-600">{payment.client_name}</td>
                          <td className="py-3 px-4 text-zinc-600">{payment.frequency}</td>
                          <td className="py-3 px-4 text-zinc-600">
                            {payment.due_date ? new Date(payment.due_date).toLocaleDateString() : 'TBD'}
                          </td>
                          <td className="py-3 px-4 text-right font-medium text-zinc-900">
                            {formatINR(payment.amount)}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className={`px-2 py-1 rounded-sm text-xs font-medium ${getStatusColor(payment.status)}`}>
                              {payment.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectPayments;
