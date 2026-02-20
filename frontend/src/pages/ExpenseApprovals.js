import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  CheckCircle, XCircle, Clock, DollarSign, User, Calendar,
  FileText, AlertCircle, ChevronRight, Building2, Briefcase
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_CONFIG = {
  pending: { label: 'Pending Manager', color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: Clock },
  manager_approved: { label: 'Pending HR', color: 'bg-blue-100 text-blue-800 border-blue-200', icon: User },
  approved: { label: 'Approved', color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800 border-red-200', icon: XCircle },
  reimbursed: { label: 'Reimbursed', color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: DollarSign }
};

const ExpenseApprovals = () => {
  const { user } = useContext(AuthContext);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [actionDialog, setActionDialog] = useState({ open: false, type: null });
  const [remarks, setRemarks] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  const [stats, setStats] = useState({ pending: 0, manager_approved: 0, approved: 0, rejected: 0 });

  const isHRAdmin = ['admin', 'hr_manager'].includes(user?.role);

  useEffect(() => {
    fetchExpenses();
  }, []);

  const fetchExpenses = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API}/expenses/pending-approvals`);
      const data = res.data || [];
      setExpenses(data);
      
      // Calculate stats
      const newStats = { pending: 0, manager_approved: 0, approved: 0, rejected: 0 };
      data.forEach(e => {
        if (newStats[e.status] !== undefined) newStats[e.status]++;
      });
      setStats(newStats);
    } catch (error) {
      // Fallback to regular expenses endpoint
      try {
        const res = await axios.get(`${API}/expenses`);
        const data = res.data || [];
        setExpenses(data);
        
        const newStats = { pending: 0, manager_approved: 0, approved: 0, rejected: 0 };
        data.forEach(e => {
          if (newStats[e.status] !== undefined) newStats[e.status]++;
        });
        setStats(newStats);
      } catch (err) {
        toast.error('Failed to load expenses');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedExpense) return;
    
    try {
      const res = await axios.post(`${API}/expenses/${selectedExpense.id}/approve`, {
        remarks: remarks
      });
      toast.success(res.data.message || 'Expense approved');
      setActionDialog({ open: false, type: null });
      setSelectedExpense(null);
      setRemarks('');
      fetchExpenses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleReject = async () => {
    if (!selectedExpense || !rejectReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    
    try {
      await axios.post(`${API}/expenses/${selectedExpense.id}/reject`, {
        reason: rejectReason
      });
      toast.success('Expense rejected');
      setActionDialog({ open: false, type: null });
      setSelectedExpense(null);
      setRejectReason('');
      fetchExpenses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const openApproveDialog = (expense) => {
    setSelectedExpense(expense);
    setActionDialog({ open: true, type: 'approve' });
  };

  const openRejectDialog = (expense) => {
    setSelectedExpense(expense);
    setActionDialog({ open: true, type: 'reject' });
  };

  const filteredExpenses = expenses.filter(e => {
    if (activeTab === 'pending') return e.status === 'pending';
    if (activeTab === 'hr_pending') return e.status === 'manager_approved';
    if (activeTab === 'approved') return e.status === 'approved';
    if (activeTab === 'rejected') return e.status === 'rejected';
    return true;
  });

  const canApprove = (expense) => {
    if (expense.status === 'pending') {
      // Manager approval - check if current user is the approver
      return expense.current_approver_id === user?.id || 
             ['admin', 'hr_manager', 'manager'].includes(user?.role);
    }
    if (expense.status === 'manager_approved') {
      // HR approval
      return isHRAdmin;
    }
    return false;
  };

  const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN')}`;

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="expense-approvals-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Expense Approvals</h1>
        <p className="text-muted-foreground">Review and approve employee expense claims</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="cursor-pointer hover:border-yellow-400 transition-colors" onClick={() => setActiveTab('pending')}>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-100">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.pending}</p>
              <p className="text-xs text-muted-foreground">Pending Manager</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="cursor-pointer hover:border-blue-400 transition-colors" onClick={() => setActiveTab('hr_pending')}>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <User className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.manager_approved}</p>
              <p className="text-xs text-muted-foreground">Pending HR</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="cursor-pointer hover:border-green-400 transition-colors" onClick={() => setActiveTab('approved')}>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.approved}</p>
              <p className="text-xs text-muted-foreground">Approved</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="cursor-pointer hover:border-red-400 transition-colors" onClick={() => setActiveTab('rejected')}>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-100">
              <XCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.rejected}</p>
              <p className="text-xs text-muted-foreground">Rejected</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="pending">Pending Manager ({stats.pending})</TabsTrigger>
          {isHRAdmin && (
            <TabsTrigger value="hr_pending">Pending HR ({stats.manager_approved})</TabsTrigger>
          )}
          <TabsTrigger value="approved">Approved ({stats.approved})</TabsTrigger>
          <TabsTrigger value="rejected">Rejected ({stats.rejected})</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredExpenses.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center h-40">
                <FileText className="w-10 h-10 text-muted-foreground mb-2" />
                <p className="text-muted-foreground">No expenses in this category</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredExpenses.map(expense => {
                const statusConfig = STATUS_CONFIG[expense.status] || STATUS_CONFIG.pending;
                const StatusIcon = statusConfig.icon;
                
                return (
                  <Card key={expense.id} className="hover:border-primary/50 transition-colors" data-testid={`expense-card-${expense.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                              <User className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-semibold">{expense.employee_name || 'Employee'}</p>
                              <p className="text-xs text-muted-foreground">{expense.employee_code || ''}</p>
                            </div>
                            <Badge className={`${statusConfig.color} border`}>
                              <StatusIcon className="w-3 h-3 mr-1" />
                              {statusConfig.label}
                            </Badge>
                          </div>
                          
                          <div className="ml-13 space-y-2">
                            <p className="text-sm text-muted-foreground">
                              {expense.is_office_expense ? 'Office Expense' : (expense.client_name || expense.project_name || 'Expense')}
                              {expense.notes && ` • ${expense.notes}`}
                            </p>
                            
                            {/* Line Items */}
                            {expense.line_items?.length > 0 && (
                              <div className="bg-muted/50 rounded-lg p-3 space-y-1">
                                {expense.line_items.map((item, idx) => (
                                  <div key={idx} className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">
                                      {item.category}: {item.description}
                                    </span>
                                    <span className="font-medium">{fmt(item.amount)}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* Approval Flow */}
                            {expense.approval_flow?.length > 0 && (
                              <div className="flex items-center gap-2 text-xs">
                                {expense.approval_flow.map((step, idx) => (
                                  <React.Fragment key={idx}>
                                    <div className={`flex items-center gap-1 px-2 py-1 rounded ${
                                      step.status === 'approved' ? 'bg-green-100 text-green-700' :
                                      step.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                      'bg-gray-100 text-gray-600'
                                    }`}>
                                      {step.status === 'approved' ? <CheckCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                                      <span>{step.approver}</span>
                                    </div>
                                    {idx < expense.approval_flow.length - 1 && (
                                      <ChevronRight className="w-3 h-3 text-muted-foreground" />
                                    )}
                                  </React.Fragment>
                                ))}
                              </div>
                            )}
                            
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {expense.created_at ? format(new Date(expense.created_at), 'MMM dd, yyyy') : '-'}
                              </span>
                              {expense.payroll_period && (
                                <span className="flex items-center gap-1">
                                  <Briefcase className="w-3 h-3" />
                                  Payroll: {expense.payroll_period}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-end gap-2">
                          <p className="text-xl font-bold">{fmt(expense.total_amount || expense.amount)}</p>
                          
                          {canApprove(expense) && (
                            <div className="flex gap-2">
                              <Button 
                                size="sm" 
                                variant="outline"
                                className="text-red-600 hover:bg-red-50"
                                onClick={() => openRejectDialog(expense)}
                                data-testid={`reject-btn-${expense.id}`}
                              >
                                <XCircle className="w-4 h-4 mr-1" /> Reject
                              </Button>
                              <Button 
                                size="sm"
                                className="bg-green-600 hover:bg-green-700"
                                onClick={() => openApproveDialog(expense)}
                                data-testid={`approve-btn-${expense.id}`}
                              >
                                <CheckCircle className="w-4 h-4 mr-1" /> Approve
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Approve Dialog */}
      <Dialog open={actionDialog.open && actionDialog.type === 'approve'} onOpenChange={(open) => !open && setActionDialog({ open: false, type: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              Approve Expense
            </DialogTitle>
            <DialogDescription>
              {selectedExpense?.status === 'pending' 
                ? 'This will approve and forward to HR for final approval.'
                : 'This will fully approve and link to payroll for reimbursement.'}
            </DialogDescription>
          </DialogHeader>
          
          {selectedExpense && (
            <div className="space-y-4">
              <div className="bg-muted p-3 rounded-lg">
                <p className="font-medium">{selectedExpense.employee_name}</p>
                <p className="text-sm text-muted-foreground">{selectedExpense.notes}</p>
                <p className="text-lg font-bold mt-2">{fmt(selectedExpense.total_amount || selectedExpense.amount)}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium">Remarks (Optional)</label>
                <Textarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Add any comments..."
                  rows={2}
                />
              </div>
              
              {selectedExpense.status === 'manager_approved' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
                  <p className="font-medium text-blue-800">Payroll Linkage</p>
                  <p className="text-blue-600">This expense will be added to {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })} payroll for reimbursement.</p>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionDialog({ open: false, type: null })}>Cancel</Button>
            <Button className="bg-green-600 hover:bg-green-700" onClick={handleApprove} data-testid="confirm-approve-btn">
              <CheckCircle className="w-4 h-4 mr-1" /> 
              {selectedExpense?.status === 'pending' ? 'Approve & Forward to HR' : 'Approve for Payroll'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={actionDialog.open && actionDialog.type === 'reject'} onOpenChange={(open) => !open && setActionDialog({ open: false, type: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-red-600" />
              Reject Expense
            </DialogTitle>
            <DialogDescription>
              The employee will be notified and can resubmit with corrections.
            </DialogDescription>
          </DialogHeader>
          
          {selectedExpense && (
            <div className="space-y-4">
              <div className="bg-muted p-3 rounded-lg">
                <p className="font-medium">{selectedExpense.employee_name}</p>
                <p className="text-sm text-muted-foreground">{selectedExpense.notes}</p>
                <p className="text-lg font-bold mt-2">{fmt(selectedExpense.total_amount || selectedExpense.amount)}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium">Rejection Reason <span className="text-red-500">*</span></label>
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Please provide a reason for rejection..."
                  rows={3}
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionDialog({ open: false, type: null })}>Cancel</Button>
            <Button variant="destructive" onClick={handleReject} data-testid="confirm-reject-btn">
              <XCircle className="w-4 h-4 mr-1" /> Reject Expense
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ExpenseApprovals;
