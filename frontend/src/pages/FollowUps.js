import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  CalendarCheck, DollarSign, Users, Clock, AlertTriangle, 
  CheckCircle, Phone, Mail, RefreshCw, Filter
} from 'lucide-react';

const FollowUps = () => {
  const { user } = useContext(AuthContext);
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const isSales = ['admin', 'sales_manager', 'sales_executive'].includes(user?.role);
  const isConsulting = ['admin', 'consultant', 'lead_consultant', 'principal_consultant', 'manager'].includes(user?.role);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchFollowUps();
  }, [filter]);

  const fetchFollowUps = async () => {
    setLoading(true);
    try {
      // Fetch both payment reminders and lead follow-ups
      const [paymentsRes, leadsRes] = await Promise.all([
        fetch(`${API}/consulting/payments`, { headers }),
        fetch(`${API}/leads`, { headers })
      ]);

      const payments = paymentsRes.ok ? await paymentsRes.json() : [];
      const leads = leadsRes.ok ? await leadsRes.json() : [];

      // Transform payment reminders (for consultants)
      const paymentFollowUps = (Array.isArray(payments) ? payments : [])
        .filter(p => p.status === 'pending' || p.status === 'overdue')
        .map(p => ({
          id: p.id,
          type: 'payment',
          title: `Payment Due: ${p.client_name || 'Client'}`,
          description: `Project: ${p.project_name || 'N/A'} - Amount: ₹${(p.amount || 0).toLocaleString()}`,
          due_date: p.due_date,
          status: p.status,
          priority: p.status === 'overdue' ? 'high' : 'medium',
          contact: p.client_contact,
          amount: p.amount
        }));

      // Transform leads (for sales)
      const leadFollowUps = (Array.isArray(leads) ? leads : [])
        .filter(l => l.status !== 'converted' && l.status !== 'lost')
        .filter(l => l.next_follow_up)
        .map(l => ({
          id: l.id,
          type: 'lead',
          title: `Lead Follow-up: ${l.company_name || l.contact_name}`,
          description: `Status: ${l.status} - Source: ${l.source || 'N/A'}`,
          due_date: l.next_follow_up,
          status: new Date(l.next_follow_up) < new Date() ? 'overdue' : 'pending',
          priority: l.priority || 'medium',
          contact: l.contact_phone || l.contact_email,
          lead_status: l.status
        }));

      let combined = [...paymentFollowUps, ...leadFollowUps];

      // Filter based on user role
      if (isSales && !isConsulting) {
        combined = combined.filter(f => f.type === 'lead');
      } else if (isConsulting && !isSales) {
        combined = combined.filter(f => f.type === 'payment');
      }

      // Apply filter
      if (filter !== 'all') {
        combined = combined.filter(f => f.type === filter);
      }

      // Sort by due date (overdue first, then by date)
      combined.sort((a, b) => {
        if (a.status === 'overdue' && b.status !== 'overdue') return -1;
        if (b.status === 'overdue' && a.status !== 'overdue') return 1;
        return new Date(a.due_date) - new Date(b.due_date);
      });

      setFollowUps(combined);
    } catch (error) {
      console.error('Error fetching follow-ups:', error);
      toast.error('Failed to fetch follow-ups');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      overdue: 'bg-red-100 text-red-700 border-red-300',
      pending: 'bg-yellow-100 text-yellow-700 border-yellow-300',
      completed: 'bg-green-100 text-green-700 border-green-300'
    };
    return (
      <span className={`px-2 py-1 text-xs rounded-full border ${styles[status] || styles.pending}`}>
        {status?.charAt(0).toUpperCase() + status?.slice(1)}
      </span>
    );
  };

  const getPriorityBadge = (priority) => {
    const styles = {
      high: 'bg-red-500',
      medium: 'bg-yellow-500',
      low: 'bg-green-500'
    };
    return <div className={`w-2 h-2 rounded-full ${styles[priority] || styles.medium}`} />;
  };

  const filteredFollowUps = followUps.filter(f => 
    f.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    f.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const overdueCount = followUps.filter(f => f.status === 'overdue').length;
  const pendingCount = followUps.filter(f => f.status === 'pending').length;
  const paymentCount = followUps.filter(f => f.type === 'payment').length;
  const leadCount = followUps.filter(f => f.type === 'lead').length;

  return (
    <div className="p-6 space-y-6" data-testid="follow-ups-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Follow-ups</h1>
          <p className="text-zinc-600">
            {isSales && isConsulting ? 'Lead & Payment follow-ups' : 
             isSales ? 'Lead follow-ups' : 'Payment follow-ups'}
          </p>
        </div>
        <Button onClick={fetchFollowUps} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">{overdueCount}</p>
                <p className="text-sm text-zinc-600">Overdue</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">{pendingCount}</p>
                <p className="text-sm text-zinc-600">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
        {isConsulting && (
          <Card className="bg-white border-zinc-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <DollarSign className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-zinc-900">{paymentCount}</p>
                  <p className="text-sm text-zinc-600">Payment Due</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        {isSales && (
          <Card className="bg-white border-zinc-200">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Users className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-zinc-900">{leadCount}</p>
                  <p className="text-sm text-zinc-600">Lead Follow-ups</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <Input
          placeholder="Search follow-ups..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-xs bg-zinc-50 border-zinc-300"
        />
        {isSales && isConsulting && (
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 bg-zinc-50 border-zinc-300">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="payment">Payments</SelectItem>
              <SelectItem value="lead">Leads</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Follow-ups List */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarCheck className="w-5 h-5" />
            Upcoming Follow-ups ({filteredFollowUps.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-zinc-600">Loading...</div>
          ) : filteredFollowUps.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
              <p>No pending follow-ups!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredFollowUps.map(followUp => (
                <div 
                  key={followUp.id} 
                  className={`p-4 rounded-lg border flex justify-between items-center ${
                    followUp.status === 'overdue' ? 'bg-red-50 border-red-200' : 'bg-zinc-50 border-zinc-200'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    {getPriorityBadge(followUp.priority)}
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-zinc-800">{followUp.title}</p>
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          followUp.type === 'payment' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                        }`}>
                          {followUp.type === 'payment' ? 'Payment' : 'Lead'}
                        </span>
                      </div>
                      <p className="text-sm text-zinc-600">{followUp.description}</p>
                      {followUp.contact && (
                        <p className="text-xs text-zinc-500 mt-1 flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {followUp.contact}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-zinc-600">
                      {followUp.due_date ? new Date(followUp.due_date).toLocaleDateString() : 'No date'}
                    </p>
                    {getStatusBadge(followUp.status)}
                    {followUp.amount && (
                      <p className="text-sm font-medium text-blue-600 mt-1">
                        ₹{followUp.amount.toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default FollowUps;
