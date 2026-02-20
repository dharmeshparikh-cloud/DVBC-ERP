import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Calendar, Users, Plus, RefreshCw, Search, CheckCircle, 
  XCircle, Clock, Gift, Briefcase, Heart
} from 'lucide-react';

const HRLeaveInput = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showApplyDialog, setShowApplyDialog] = useState(false);
  const [showCreditDialog, setShowCreditDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  // Form states
  const [leaveForm, setLeaveForm] = useState({
    employee_id: '',
    leave_type: 'casual_leave',
    start_date: '',
    end_date: '',
    is_half_day: false,
    reason: ''
  });

  const [creditForm, setCreditForm] = useState({
    leave_type: 'casual_leave',
    credit_days: 0,
    reset_used: false,
    employee_ids: []
  });

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchEmployees();
    fetchLeaveRequests();
  }, []);

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API}/employees`, { headers });
      if (res.ok) {
        const data = await res.json();
        setEmployees(data);
      }
    } catch (error) {
      console.error('Error fetching employees:', error);
    }
  };

  const fetchLeaveRequests = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/leave-requests/all`, { headers });
      if (res.ok) {
        const data = await res.json();
        setLeaveRequests(data);
      }
    } catch (error) {
      toast.error('Failed to fetch leave requests');
    } finally {
      setLoading(false);
    }
  };

  const applyLeaveForEmployee = async () => {
    if (!leaveForm.employee_id || !leaveForm.start_date) {
      toast.error('Please fill required fields');
      return;
    }

    try {
      const res = await fetch(`${API}/attendance/hr/apply-leave-for-employee`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ...leaveForm,
          end_date: leaveForm.end_date || leaveForm.start_date
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setShowApplyDialog(false);
        setLeaveForm({
          employee_id: '',
          leave_type: 'casual_leave',
          start_date: '',
          end_date: '',
          is_half_day: false,
          reason: ''
        });
        fetchLeaveRequests();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to apply leave');
      }
    } catch (error) {
      toast.error('Failed to apply leave');
    }
  };

  const bulkCreditLeaves = async () => {
    if (creditForm.credit_days <= 0) {
      toast.error('Credit days must be greater than 0');
      return;
    }

    try {
      const res = await fetch(`${API}/attendance/hr/bulk-leave-credit`, {
        method: 'POST',
        headers,
        body: JSON.stringify(creditForm)
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setShowCreditDialog(false);
        setCreditForm({
          leave_type: 'casual_leave',
          credit_days: 0,
          reset_used: false,
          employee_ids: []
        });
        fetchEmployees();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to credit leaves');
      }
    } catch (error) {
      toast.error('Failed to credit leaves');
    }
  };

  const approveLeave = async (leaveId, action) => {
    try {
      const res = await fetch(`${API}/leave-requests/${leaveId}/rm-approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ action, remarks: `${action === 'approve' ? 'Approved' : 'Rejected'} by HR` })
      });
      
      if (res.ok) {
        toast.success(`Leave ${action}d successfully`);
        fetchLeaveRequests();
      } else {
        const error = await res.json();
        toast.error(error.detail || `Failed to ${action} leave`);
      }
    } catch (error) {
      toast.error(`Failed to ${action} leave`);
    }
  };

  const filteredRequests = leaveRequests.filter(req => {
    const matchesSearch = req.employee_name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || req.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getLeaveIcon = (type) => {
    switch (type) {
      case 'casual_leave': return <Calendar className="w-4 h-4 text-blue-400" />;
      case 'sick_leave': return <Heart className="w-4 h-4 text-red-400" />;
      case 'earned_leave': return <Gift className="w-4 h-4 text-green-400" />;
      default: return <Briefcase className="w-4 h-4 text-zinc-600" />;
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      approved: 'bg-green-500/20 text-green-400 border-green-500/30',
      rejected: 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return (
      <span className={`px-2 py-1 text-xs rounded-full border ${styles[status] || styles.pending}`}>
        {status?.charAt(0).toUpperCase() + status?.slice(1)}
      </span>
    );
  };

  return (
    <div className="p-6 space-y-6" data-testid="hr-leave-input">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">HR Leave Management</h1>
          <p className="text-zinc-600">Apply leave for employees and manage leave balances</p>
        </div>
        <div className="flex gap-3">
          <Button 
            onClick={() => setShowApplyDialog(true)}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="apply-leave-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Apply Leave for Employee
          </Button>
          <Button 
            onClick={() => setShowCreditDialog(true)}
            variant="outline"
            data-testid="credit-leaves-btn"
          >
            <Gift className="w-4 h-4 mr-2" />
            Bulk Credit Leaves
          </Button>
          <Button onClick={fetchLeaveRequests} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-500/20 rounded-lg">
                <Clock className="w-6 h-6 text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">
                  {leaveRequests.filter(r => r.status === 'pending').length}
                </p>
                <p className="text-sm text-zinc-600">Pending Requests</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-500/20 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">
                  {leaveRequests.filter(r => r.status === 'approved').length}
                </p>
                <p className="text-sm text-zinc-600">Approved</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-red-500/20 rounded-lg">
                <XCircle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">
                  {leaveRequests.filter(r => r.status === 'rejected').length}
                </p>
                <p className="text-sm text-zinc-600">Rejected</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-500/20 rounded-lg">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-zinc-900">{employees.length}</p>
                <p className="text-sm text-zinc-600">Total Employees</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Leave Requests Table */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Leave Requests
            </CardTitle>
          </div>
          <div className="flex gap-3 mt-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <Input
                placeholder="Search employee..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-zinc-50 border-zinc-300"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40 bg-zinc-50 border-zinc-300">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-zinc-600">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-300">
                    <th className="text-left p-3 text-zinc-600">Employee</th>
                    <th className="text-left p-3 text-zinc-600">Leave Type</th>
                    <th className="text-left p-3 text-zinc-600">Duration</th>
                    <th className="text-center p-3 text-zinc-600">Days</th>
                    <th className="text-left p-3 text-zinc-600">Reason</th>
                    <th className="text-center p-3 text-zinc-600">Status</th>
                    <th className="text-center p-3 text-zinc-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.slice(0, 50).map(req => (
                    <tr key={req.id} className="border-b border-zinc-200 hover:bg-zinc-50/50">
                      <td className="p-3">
                        <p className="text-zinc-800 font-medium">{req.employee_name}</p>
                        <p className="text-xs text-zinc-500">{req.employee_code}</p>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {getLeaveIcon(req.leave_type)}
                          <span className="text-zinc-700">
                            {req.leave_type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-zinc-600">
                        {req.start_date?.slice(0, 10)} 
                        {req.end_date && req.end_date !== req.start_date && ` - ${req.end_date?.slice(0, 10)}`}
                      </td>
                      <td className="p-3 text-center text-zinc-800">{req.days}</td>
                      <td className="p-3 text-zinc-600 max-w-[200px] truncate">{req.reason || '-'}</td>
                      <td className="p-3 text-center">{getStatusBadge(req.status)}</td>
                      <td className="p-3 text-center">
                        {req.status === 'pending' && (
                          <div className="flex gap-2 justify-center">
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="text-green-400 border-green-500/30 hover:bg-green-500/20"
                              onClick={() => approveLeave(req.id, 'approve')}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="text-red-400 border-red-500/30 hover:bg-red-500/20"
                              onClick={() => approveLeave(req.id, 'reject')}
                            >
                              <XCircle className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                        {req.status !== 'pending' && (
                          <span className="text-xs text-zinc-500">
                            {req.approved_by_name || req.rejected_by_name || '-'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredRequests.length === 0 && (
                <div className="text-center py-8 text-zinc-600">No leave requests found</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Apply Leave Dialog */}
      <Dialog open={showApplyDialog} onOpenChange={setShowApplyDialog}>
        <DialogContent className="bg-white border-zinc-200 max-w-md">
          <DialogHeader>
            <DialogTitle>Apply Leave for Employee</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Employee *</Label>
              <Select 
                value={leaveForm.employee_id} 
                onValueChange={(v) => setLeaveForm({...leaveForm, employee_id: v})}
              >
                <SelectTrigger className="bg-zinc-50 border-zinc-300">
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.employee_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Leave Type *</Label>
              <Select 
                value={leaveForm.leave_type} 
                onValueChange={(v) => setLeaveForm({...leaveForm, leave_type: v})}
              >
                <SelectTrigger className="bg-zinc-50 border-zinc-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="casual_leave">Casual Leave</SelectItem>
                  <SelectItem value="sick_leave">Sick Leave</SelectItem>
                  <SelectItem value="earned_leave">Earned Leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Start Date *</Label>
                <Input
                  type="date"
                  value={leaveForm.start_date}
                  onChange={(e) => setLeaveForm({...leaveForm, start_date: e.target.value})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
              <div>
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={leaveForm.end_date}
                  onChange={(e) => setLeaveForm({...leaveForm, end_date: e.target.value})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="half_day"
                checked={leaveForm.is_half_day}
                onChange={(e) => setLeaveForm({...leaveForm, is_half_day: e.target.checked})}
                className="rounded border-zinc-300"
              />
              <Label htmlFor="half_day">Half Day</Label>
            </div>
            <div>
              <Label>Reason</Label>
              <Textarea
                value={leaveForm.reason}
                onChange={(e) => setLeaveForm({...leaveForm, reason: e.target.value})}
                placeholder="Enter reason..."
                className="bg-zinc-50 border-zinc-300"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApplyDialog(false)}>Cancel</Button>
            <Button onClick={applyLeaveForEmployee} className="bg-blue-600 hover:bg-blue-700">
              Apply Leave (Auto-Approved)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Credit Dialog */}
      <Dialog open={showCreditDialog} onOpenChange={setShowCreditDialog}>
        <DialogContent className="bg-white border-zinc-200 max-w-md">
          <DialogHeader>
            <DialogTitle>Bulk Credit Leaves</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Leave Type *</Label>
              <Select 
                value={creditForm.leave_type} 
                onValueChange={(v) => setCreditForm({...creditForm, leave_type: v})}
              >
                <SelectTrigger className="bg-zinc-50 border-zinc-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="casual_leave">Casual Leave</SelectItem>
                  <SelectItem value="sick_leave">Sick Leave</SelectItem>
                  <SelectItem value="earned_leave">Earned Leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Credit Days *</Label>
              <Input
                type="number"
                min="0"
                value={creditForm.credit_days}
                onChange={(e) => setCreditForm({...creditForm, credit_days: parseInt(e.target.value) || 0})}
                className="bg-zinc-50 border-zinc-300"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="reset_used"
                checked={creditForm.reset_used}
                onChange={(e) => setCreditForm({...creditForm, reset_used: e.target.checked})}
                className="rounded border-zinc-300"
              />
              <Label htmlFor="reset_used">Reset Used Count to 0</Label>
            </div>
            <p className="text-sm text-zinc-600">
              This will update leave balance for all active employees.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreditDialog(false)}>Cancel</Button>
            <Button onClick={bulkCreditLeaves} className="bg-green-600 hover:bg-green-700">
              <Gift className="w-4 h-4 mr-2" />
              Credit Leaves
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRLeaveInput;
