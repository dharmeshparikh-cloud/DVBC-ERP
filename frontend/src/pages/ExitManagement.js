import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Separator } from '../components/ui/separator';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import {
  LogOut, Clock, CheckCircle, XCircle, AlertCircle, User, Calendar,
  Building2, Briefcase, FileText, Send, Loader2, ChevronRight, ChevronLeft,
  Eye, ThumbsUp, ThumbsDown, MessageSquare, Star, Calculator, IndianRupee,
  Banknote, Wallet, CreditCard, BadgeCheck, Gift, UserMinus, Plus
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../utils/roles';

// Status flow: pending → admin_approved → hr_approved → clearance → settlement_calculated → approved → completed
const STATUS_CONFIG = {
  pending: { color: 'bg-amber-100 text-amber-700', label: 'Pending Admin', icon: Clock },
  admin_approved: { color: 'bg-blue-100 text-blue-700', label: 'Pending HR', icon: AlertCircle },
  hr_approved: { color: 'bg-purple-100 text-purple-700', label: 'Clearance Phase', icon: BadgeCheck },
  clearance_complete: { color: 'bg-indigo-100 text-indigo-700', label: 'Ready for F&F', icon: Calculator },
  settlement_calculated: { color: 'bg-cyan-100 text-cyan-700', label: 'Settlement Pending', icon: Banknote },
  approved: { color: 'bg-green-100 text-green-700', label: 'Approved', icon: CheckCircle },
  completed: { color: 'bg-zinc-100 text-zinc-700', label: 'Completed', icon: CheckCircle },
  rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected', icon: XCircle },
  cancelled: { color: 'bg-zinc-100 text-zinc-500', label: 'Cancelled', icon: XCircle }
};

const ExitManagement = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const isDark = theme === 'dark';
  
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);
  const canManage = isAdmin || isHR;
  
  // State
  const [activeTab, setActiveTab] = useState('requests');
  const [filter, setFilter] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [showInitiateDialog, setShowInitiateDialog] = useState(false);
  const [showClearanceDialog, setShowClearanceDialog] = useState(false);
  const [showSettlementDialog, setShowSettlementDialog] = useState(false);
  
  const [approvalAction, setApprovalAction] = useState(null);
  const [remarks, setRemarks] = useState('');
  const [clearanceDept, setClearanceDept] = useState('');
  const [settlement, setSettlement] = useState(null);
  
  // Initiate form state
  const [initiateForm, setInitiateForm] = useState({
    employee_id: '',
    exit_type: 'resignation',
    last_working_date: '',
    notice_period_days: 30,
    days_served: 0,
    reason: ''
  });
  
  // Fetch employees for dropdown
  const { data: employees = [] } = useQuery({
    queryKey: ['employees-active'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return (res.data || []).filter(e => e.is_active !== false && e.status !== 'inactive');
    },
    staleTime: 5 * 60 * 1000
  });
  
  // Fetch exit requests
  const { data: exitData, isLoading } = useQuery({
    queryKey: ['exit-requests', filter],
    queryFn: async () => {
      const res = await axios.get(`${API}/exit/all`, {
        params: filter !== 'all' ? { status: filter } : {}
      });
      return res.data;
    },
    staleTime: 60 * 1000
  });
  
  const requests = exitData?.requests || [];
  
  // Mutations
  const initiateExitMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/exit-settlement/initiate`, data);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Exit process initiated successfully');
      queryClient.invalidateQueries(['exit-requests']);
      setShowInitiateDialog(false);
      resetInitiateForm();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to initiate exit')
  });
  
  const adminApproveMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/admin-approve`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit request approved by Admin');
      queryClient.invalidateQueries(['exit-requests']);
      closeDialogs();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const hrApproveMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/hr-approve`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit approved. Clearance phase started.');
      queryClient.invalidateQueries(['exit-requests']);
      closeDialogs();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const rejectMutation = useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      return axios.post(`${API}/exit/${requestId}/reject`, { remarks });
    },
    onSuccess: () => {
      toast.success('Exit request rejected');
      queryClient.invalidateQueries(['exit-requests']);
      closeDialogs();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Rejection failed')
  });
  
  const clearanceMutation = useMutation({
    mutationFn: async ({ exitId, department, status, remarks }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/clearance`, {
        department, status, remarks
      });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`${clearanceDept.toUpperCase()} clearance updated`);
      queryClient.invalidateQueries(['exit-requests']);
      setShowClearanceDialog(false);
      setClearanceDept('');
      setRemarks('');
      if (data.all_cleared) {
        toast.success('All clearances complete! Ready for F&F calculation.');
      }
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Clearance update failed')
  });
  
  const calculateSettlementMutation = useMutation({
    mutationFn: async (exitId) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/calculate-settlement`);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('F&F Settlement calculated');
      setSettlement(data.settlement);
      queryClient.invalidateQueries(['exit-requests']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Calculation failed')
  });
  
  const approveSettlementMutation = useMutation({
    mutationFn: async ({ exitId, approved, remarks }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/approve-settlement`, {
        approved, remarks
      });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries(['exit-requests']);
      setShowSettlementDialog(false);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const completeSettlementMutation = useMutation({
    mutationFn: async ({ exitId, payment_reference, payment_date }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/complete`, {
        payment_reference, payment_date
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success('Settlement completed. Employee marked as inactive.');
      queryClient.invalidateQueries(['exit-requests']);
      queryClient.invalidateQueries(['employees-active']);
      closeDialogs();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Completion failed')
  });
  
  // Helpers
  const closeDialogs = () => {
    setShowDetailDialog(false);
    setShowApprovalDialog(false);
    setShowSettlementDialog(false);
    setSelectedRequest(null);
    setRemarks('');
    setSettlement(null);
  };
  
  const resetInitiateForm = () => {
    setInitiateForm({
      employee_id: '',
      exit_type: 'resignation',
      last_working_date: '',
      notice_period_days: 30,
      days_served: 0,
      reason: ''
    });
  };
  
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };
  
  const getStatusBadge = (status) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    return (
      <Badge className={`${config.color} gap-1`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    );
  };
  
  const canApprove = (request) => {
    if (request.status === 'pending' && isAdmin) return true;
    if (request.status === 'admin_approved' && isHR) return true;
    return false;
  };
  
  const canManageClearance = (request) => {
    return canManage && ['hr_approved', 'initiated'].includes(request.status);
  };
  
  const canCalculateSettlement = (request) => {
    return canManage && (request.status === 'clearance_complete' || allClearancesDone(request));
  };
  
  const canApproveSettlement = (request) => {
    return isAdmin && request.status === 'settlement_calculated';
  };
  
  const canComplete = (request) => {
    return canManage && request.status === 'approved';
  };
  
  const allClearancesDone = (request) => {
    if (!request.clearance) return false;
    return Object.values(request.clearance).every(c => c.status === 'cleared');
  };
  
  // Actions
  const handleApprove = (request) => {
    setSelectedRequest(request);
    setApprovalAction('approve');
    setRemarks('');
    setShowApprovalDialog(true);
  };
  
  const handleReject = (request) => {
    setSelectedRequest(request);
    setApprovalAction('reject');
    setRemarks('');
    setShowApprovalDialog(true);
  };
  
  const submitApproval = () => {
    if (!selectedRequest) return;
    const payload = { requestId: selectedRequest.id, remarks };
    
    if (approvalAction === 'reject') {
      rejectMutation.mutate(payload);
    } else if (selectedRequest.status === 'pending' && isAdmin) {
      adminApproveMutation.mutate(payload);
    } else if (selectedRequest.status === 'admin_approved' && isHR) {
      hrApproveMutation.mutate(payload);
    }
  };
  
  const viewDetails = (request) => {
    setSelectedRequest(request);
    setShowDetailDialog(true);
  };
  
  const openSettlementView = async (request) => {
    setSelectedRequest(request);
    if (request.settlement_details) {
      setSettlement(request.settlement_details);
    }
    setShowSettlementDialog(true);
  };
  
  // Stats
  const pendingCount = requests.filter(r => r.status === 'pending').length;
  const inProgressCount = requests.filter(r => ['admin_approved', 'hr_approved', 'clearance_complete', 'settlement_calculated'].includes(r.status)).length;
  const completedCount = requests.filter(r => r.status === 'completed').length;
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }
  
  return (
    <div data-testid="exit-management-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <LogOut className="w-6 h-6 text-orange-500" />
            Exit Management & F&F Settlement
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Complete exit workflow: Resignation → Approval → Clearance → Settlement → Completion
          </p>
        </div>
        
        {canManage && (
          <Button 
            onClick={() => setShowInitiateDialog(true)}
            className="bg-orange-600 hover:bg-orange-700"
            data-testid="btn-initiate-exit"
          >
            <Plus className="w-4 h-4 mr-2" />
            Initiate Exit
          </Button>
        )}
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Pending Approval</p>
              <p className="text-xl font-bold">{pendingCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Briefcase className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>In Progress</p>
              <p className="text-xl font-bold">{inProgressCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Completed</p>
              <p className="text-xl font-bold">{completedCount}</p>
            </div>
          </div>
        </div>
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'}`}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-500/10">
              <FileText className="w-5 h-5 text-zinc-500" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Requests</p>
              <p className="text-xl font-bold">{requests.length}</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'pending', 'admin_approved', 'hr_approved', 'settlement_calculated', 'completed'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-orange-500 text-white'
                : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
            }`}
          >
            {f === 'admin_approved' ? 'Pending HR' : 
             f === 'hr_approved' ? 'Clearance' : 
             f === 'settlement_calculated' ? 'F&F Pending' :
             f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      
      {/* Requests List */}
      {requests.length === 0 ? (
        <div className={`text-center py-12 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
          <LogOut className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
          <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
            No exit requests found
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(request => (
            <Card 
              key={request.id} 
              className={`${isDark ? 'bg-zinc-800 border-zinc-700' : ''} hover:shadow-md transition-shadow`}
            >
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-full bg-orange-100">
                      <User className="w-6 h-6 text-orange-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{request.employee_name}</h3>
                      <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {request.employee_id} • {request.department}
                      </p>
                      <div className="flex items-center gap-3 mt-1 text-xs">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Submitted: {new Date(request.created_at || request.resignation_date).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          LWD: {new Date(request.last_working_day || request.last_working_date).toLocaleDateString()}
                        </span>
                        {request.exit_type && (
                          <Badge variant="outline" className="capitalize text-xs">
                            {request.exit_type}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {getStatusBadge(request.status)}
                    
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => viewDetails(request)}>
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      
                      {/* Approval Actions */}
                      {canApprove(request) && (
                        <>
                          <Button size="sm" onClick={() => handleApprove(request)} className="bg-emerald-600 hover:bg-emerald-700">
                            <ThumbsUp className="w-4 h-4 mr-1" />
                            Approve
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => handleReject(request)}>
                            <ThumbsDown className="w-4 h-4 mr-1" />
                            Reject
                          </Button>
                        </>
                      )}
                      
                      {/* Clearance Actions */}
                      {canManageClearance(request) && (
                        <Button size="sm" variant="outline" onClick={() => { setSelectedRequest(request); setShowClearanceDialog(true); }}>
                          <BadgeCheck className="w-4 h-4 mr-1" />
                          Clearances
                        </Button>
                      )}
                      
                      {/* Calculate F&F */}
                      {canCalculateSettlement(request) && !request.settlement_details && (
                        <Button 
                          size="sm" 
                          onClick={() => calculateSettlementMutation.mutate(request.id)}
                          disabled={calculateSettlementMutation.isPending}
                          className="bg-purple-600 hover:bg-purple-700"
                        >
                          {calculateSettlementMutation.isPending && <Loader2 className="w-4 h-4 mr-1 animate-spin" />}
                          <Calculator className="w-4 h-4 mr-1" />
                          Calculate F&F
                        </Button>
                      )}
                      
                      {/* View/Approve Settlement */}
                      {(request.settlement_details || request.status === 'settlement_calculated') && (
                        <Button size="sm" onClick={() => openSettlementView(request)} className="bg-cyan-600 hover:bg-cyan-700">
                          <Banknote className="w-4 h-4 mr-1" />
                          View F&F
                        </Button>
                      )}
                      
                      {/* Complete */}
                      {canComplete(request) && (
                        <Button 
                          size="sm" 
                          onClick={() => {
                            const paymentRef = prompt('Enter payment reference (e.g., NEFT123456):');
                            if (paymentRef) {
                              completeSettlementMutation.mutate({
                                exitId: request.id,
                                payment_reference: paymentRef,
                                payment_date: new Date().toISOString().split('T')[0]
                              });
                            }
                          }}
                          disabled={completeSettlementMutation.isPending}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          {completeSettlementMutation.isPending && <Loader2 className="w-4 h-4 mr-1 animate-spin" />}
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Complete
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Progress Bar */}
                {!['completed', 'rejected', 'cancelled'].includes(request.status) && (
                  <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700">
                    <div className="flex items-center justify-between text-xs">
                      {['Submitted', 'Admin', 'HR', 'Clearance', 'F&F', 'Payment'].map((step, idx) => {
                        const stepStatus = getStepStatus(request.status, idx);
                        return (
                          <React.Fragment key={step}>
                            <div className={`flex flex-col items-center ${stepStatus === 'done' ? 'text-green-600' : stepStatus === 'current' ? 'text-orange-600' : 'text-zinc-400'}`}>
                              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                                stepStatus === 'done' ? 'bg-green-100' : stepStatus === 'current' ? 'bg-orange-100' : 'bg-zinc-100'
                              }`}>
                                {stepStatus === 'done' ? <CheckCircle className="w-4 h-4" /> : <span>{idx + 1}</span>}
                              </div>
                              <span className="mt-1">{step}</span>
                            </div>
                            {idx < 5 && <div className={`flex-1 h-0.5 mx-1 ${stepStatus === 'done' ? 'bg-green-400' : 'bg-zinc-200'}`} />}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* ==================== INITIATE EXIT DIALOG ==================== */}
      <Dialog open={showInitiateDialog} onOpenChange={setShowInitiateDialog}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserMinus className="w-5 h-5 text-orange-500" />
              Initiate Exit Process
            </DialogTitle>
            <DialogDescription>
              Start the exit and F&F settlement process for an employee
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label>Select Employee *</Label>
              <Select value={initiateForm.employee_id} onValueChange={(v) => setInitiateForm({...initiateForm, employee_id: v})}>
                <SelectTrigger className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}>
                  <SelectValue placeholder="Choose employee..." />
                </SelectTrigger>
                <SelectContent>
                  {employees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.department})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Exit Type *</Label>
                <Select value={initiateForm.exit_type} onValueChange={(v) => setInitiateForm({...initiateForm, exit_type: v})}>
                  <SelectTrigger className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="resignation">Resignation</SelectItem>
                    <SelectItem value="termination">Termination</SelectItem>
                    <SelectItem value="retirement">Retirement</SelectItem>
                    <SelectItem value="death">Death</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label>Last Working Date *</Label>
                <Input
                  type="date"
                  value={initiateForm.last_working_date}
                  onChange={(e) => setInitiateForm({...initiateForm, last_working_date: e.target.value})}
                  className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Notice Period (Days)</Label>
                <Input
                  type="number"
                  value={initiateForm.notice_period_days}
                  onChange={(e) => setInitiateForm({...initiateForm, notice_period_days: parseInt(e.target.value) || 0})}
                  className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                  min={0}
                />
              </div>
              <div>
                <Label>Days Served</Label>
                <Input
                  type="number"
                  value={initiateForm.days_served}
                  onChange={(e) => setInitiateForm({...initiateForm, days_served: parseInt(e.target.value) || 0})}
                  className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                  min={0}
                  max={initiateForm.notice_period_days}
                />
              </div>
            </div>
            
            {initiateForm.days_served < initiateForm.notice_period_days && initiateForm.notice_period_days > 0 && (
              <p className="text-xs text-amber-600">
                Notice shortfall: {initiateForm.notice_period_days - initiateForm.days_served} days will be recovered from settlement
              </p>
            )}
            
            <div>
              <Label>Reason</Label>
              <Textarea
                value={initiateForm.reason}
                onChange={(e) => setInitiateForm({...initiateForm, reason: e.target.value})}
                placeholder="Reason for exit..."
                className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowInitiateDialog(false); resetInitiateForm(); }}>
              Cancel
            </Button>
            <Button
              onClick={() => initiateExitMutation.mutate(initiateForm)}
              disabled={initiateExitMutation.isPending || !initiateForm.employee_id || !initiateForm.last_working_date}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {initiateExitMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Initiate Exit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ==================== DETAIL DIALOG ==================== */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className={`max-w-2xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-500" />
              Exit Request Details
            </DialogTitle>
          </DialogHeader>
          
          {selectedRequest && (
            <div className="space-y-4 py-4">
              {/* Employee Info */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                <h4 className="font-medium mb-3">Employee Information</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><Label className="text-xs text-zinc-500">Name</Label><p>{selectedRequest.employee_name}</p></div>
                  <div><Label className="text-xs text-zinc-500">Employee ID</Label><p>{selectedRequest.employee_id}</p></div>
                  <div><Label className="text-xs text-zinc-500">Department</Label><p>{selectedRequest.department || 'N/A'}</p></div>
                  <div><Label className="text-xs text-zinc-500">Designation</Label><p>{selectedRequest.designation || 'N/A'}</p></div>
                </div>
              </div>
              
              {/* Request Info */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                <h4 className="font-medium mb-3">Exit Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><Label className="text-xs text-zinc-500">Exit Type</Label><p className="capitalize">{selectedRequest.exit_type || selectedRequest.reason?.replace('_', ' ') || 'Resignation'}</p></div>
                  <div><Label className="text-xs text-zinc-500">Status</Label><div className="mt-1">{getStatusBadge(selectedRequest.status)}</div></div>
                  <div><Label className="text-xs text-zinc-500">Resignation Date</Label><p>{new Date(selectedRequest.resignation_date || selectedRequest.created_at).toLocaleDateString()}</p></div>
                  <div><Label className="text-xs text-zinc-500">Last Working Day</Label><p>{new Date(selectedRequest.last_working_day || selectedRequest.last_working_date).toLocaleDateString()}</p></div>
                  <div><Label className="text-xs text-zinc-500">Notice Period</Label><p>{selectedRequest.notice_period_days || 30} days</p></div>
                  <div><Label className="text-xs text-zinc-500">Days Served</Label><p>{selectedRequest.days_served || 0} days</p></div>
                </div>
              </div>
              
              {/* Clearance Status */}
              {selectedRequest.clearance && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3">Clearance Status</h4>
                  <div className="grid grid-cols-5 gap-2">
                    {Object.entries(selectedRequest.clearance).map(([dept, data]) => (
                      <div key={dept} className={`p-2 rounded text-center text-xs ${
                        data.status === 'cleared' ? 'bg-green-100 text-green-700' :
                        data.status === 'blocked' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        <p className="font-medium capitalize">{dept}</p>
                        <p className="capitalize">{data.status}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Exit Interview */}
              {selectedRequest.exit_interview && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3 flex items-center gap-2"><MessageSquare className="w-4 h-4" />Exit Interview</h4>
                  <div className="space-y-2 text-sm">
                    {Object.entries(selectedRequest.exit_interview).map(([key, value]) => (
                      <div key={key} className={`p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'}`}>
                        <Label className="text-xs text-zinc-500 capitalize">{key.replace('_', ' ')}</Label>
                        <p className="mt-1">
                          {typeof value === 'number' && key.includes('rating') ? (
                            <span className="flex items-center gap-1">
                              {[...Array(5)].map((_, i) => (
                                <Star key={i} className={`w-4 h-4 ${i < value ? 'fill-amber-400 text-amber-400' : 'text-zinc-300'}`} />
                              ))}
                            </span>
                          ) : String(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Approval History */}
              {selectedRequest.approvals && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3">Approval History</h4>
                  <div className="space-y-2 text-sm">
                    {selectedRequest.approvals.admin && (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span>Admin: {selectedRequest.approvals.admin.approved_by}</span>
                        <span className="text-zinc-500">({new Date(selectedRequest.approvals.admin.approved_at).toLocaleDateString()})</span>
                      </div>
                    )}
                    {selectedRequest.approvals.hr && (
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span>HR: {selectedRequest.approvals.hr.approved_by}</span>
                        <span className="text-zinc-500">({new Date(selectedRequest.approvals.hr.approved_at).toLocaleDateString()})</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDetailDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ==================== APPROVAL DIALOG ==================== */}
      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <DialogContent className={`max-w-md ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {approvalAction === 'reject' ? <XCircle className="w-5 h-5 text-red-500" /> : <CheckCircle className="w-5 h-5 text-emerald-500" />}
              {approvalAction === 'reject' ? 'Reject' : 'Approve'} Exit Request
            </DialogTitle>
            <DialogDescription>
              {selectedRequest && <>Employee: <strong>{selectedRequest.employee_name}</strong></>}
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <Label>Remarks {approvalAction === 'reject' ? '(Required)' : '(Optional)'}</Label>
            <Textarea
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder={approvalAction === 'reject' ? 'Reason for rejection...' : 'Any comments...'}
              className={`mt-2 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
              rows={3}
            />
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApprovalDialog(false)}>Cancel</Button>
            <Button
              onClick={submitApproval}
              disabled={adminApproveMutation.isPending || hrApproveMutation.isPending || rejectMutation.isPending || (approvalAction === 'reject' && !remarks.trim())}
              className={approvalAction === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}
            >
              {(adminApproveMutation.isPending || hrApproveMutation.isPending || rejectMutation.isPending) ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : approvalAction === 'reject' ? (
                <XCircle className="w-4 h-4 mr-2" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              {approvalAction === 'reject' ? 'Reject' : 'Approve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ==================== CLEARANCE DIALOG ==================== */}
      <Dialog open={showClearanceDialog} onOpenChange={setShowClearanceDialog}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BadgeCheck className="w-5 h-5 text-purple-500" />
              Department Clearances
            </DialogTitle>
            <DialogDescription>
              {selectedRequest && <>Update clearances for {selectedRequest.employee_name}</>}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRequest?.clearance && (
            <div className="py-4 space-y-4">
              <div className="grid grid-cols-5 gap-3">
                {Object.entries(selectedRequest.clearance).map(([dept, data]) => {
                  const isCleared = data.status === 'cleared';
                  const isBlocked = data.status === 'blocked';
                  
                  return (
                    <div 
                      key={dept}
                      className={`p-3 rounded-lg border text-center cursor-pointer transition-all ${
                        clearanceDept === dept ? 'ring-2 ring-orange-500' :
                        isCleared ? 'bg-green-50 border-green-200' : 
                        isBlocked ? 'bg-red-50 border-red-200' :
                        isDark ? 'bg-zinc-900 border-zinc-700 hover:border-zinc-600' : 'bg-zinc-50 border-zinc-200 hover:border-zinc-300'
                      }`}
                      onClick={() => !isCleared && setClearanceDept(dept)}
                    >
                      <div className={`w-8 h-8 mx-auto rounded-full flex items-center justify-center mb-1 ${
                        isCleared ? 'bg-green-100' : isBlocked ? 'bg-red-100' : 'bg-amber-100'
                      }`}>
                        {isCleared ? <CheckCircle className="w-4 h-4 text-green-600" /> : 
                         isBlocked ? <XCircle className="w-4 h-4 text-red-600" /> : 
                         <Clock className="w-4 h-4 text-amber-600" />}
                      </div>
                      <p className="font-medium text-xs capitalize">{dept}</p>
                      <p className={`text-xs ${isCleared ? 'text-green-600' : isBlocked ? 'text-red-600' : 'text-amber-600'}`}>
                        {isCleared ? 'Done' : isBlocked ? 'Blocked' : 'Pending'}
                      </p>
                    </div>
                  );
                })}
              </div>
              
              {clearanceDept && (
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-50 border-zinc-200'}`}>
                  <Label className="capitalize font-medium">{clearanceDept} Clearance</Label>
                  <Textarea
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="Remarks (optional)..."
                    className={`mt-2 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                    rows={2}
                  />
                  <div className="flex gap-2 mt-3">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => clearanceMutation.mutate({ exitId: selectedRequest.id, department: clearanceDept, status: 'blocked', remarks })}
                      disabled={clearanceMutation.isPending}
                    >
                      <XCircle className="w-4 h-4 mr-1" />
                      Block
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => clearanceMutation.mutate({ exitId: selectedRequest.id, department: clearanceDept, status: 'cleared', remarks })}
                      disabled={clearanceMutation.isPending}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {clearanceMutation.isPending && <Loader2 className="w-4 h-4 mr-1 animate-spin" />}
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Mark Cleared
                    </Button>
                  </div>
                </div>
              )}
              
              {allClearancesDone(selectedRequest) && (
                <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  All clearances complete! Ready for F&F calculation.
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowClearanceDialog(false); setClearanceDept(''); setRemarks(''); }}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ==================== SETTLEMENT DIALOG ==================== */}
      <Dialog open={showSettlementDialog} onOpenChange={setShowSettlementDialog}>
        <DialogContent className={`max-w-2xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Banknote className="w-5 h-5 text-cyan-500" />
              F&F Settlement Details
            </DialogTitle>
            <DialogDescription>
              {selectedRequest && <>Full & Final settlement for {selectedRequest.employee_name}</>}
            </DialogDescription>
          </DialogHeader>
          
          {settlement ? (
            <div className="py-4 space-y-4">
              {/* Tenure & Salary */}
              <div className={`grid grid-cols-3 gap-4 p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Tenure</p>
                  <p className="font-bold">{Math.floor(settlement.tenure?.years || 0)} yrs {settlement.tenure?.months || 0} mos</p>
                </div>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Monthly Gross</p>
                  <p className="font-bold">{formatCurrency(settlement.salary_details?.gross_monthly)}</p>
                </div>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Annual CTC</p>
                  <p className="font-bold">{formatCurrency(settlement.salary_details?.ctc_annual)}</p>
                </div>
              </div>
              
              {/* Payable */}
              <div className={`p-4 rounded-lg border border-green-200 ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}>
                <h4 className="font-medium text-green-700 mb-3 flex items-center gap-2">
                  <Gift className="w-5 h-5" />
                  Payable to Employee
                </h4>
                <div className="space-y-2 text-sm">
                  {settlement.payable_components?.gratuity?.eligible && (
                    <div className="flex justify-between">
                      <span>Gratuity ({settlement.payable_components.gratuity.years_eligible} yrs)</span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.gratuity.amount)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.leave_encashment?.amount > 0 && (
                    <div className="flex justify-between">
                      <span>Leave Encashment ({settlement.payable_components.leave_encashment.days_encashed} days)</span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.leave_encashment.amount)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.expense_reimbursements?.total > 0 && (
                    <div className="flex justify-between">
                      <span>Expense Reimbursements</span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.expense_reimbursements.total)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.notice_period_payment && (
                    <div className="flex justify-between">
                      <span>Notice Period Payment</span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.notice_period_payment.amount)}</span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex justify-between font-bold">
                    <span>Total Payable</span>
                    <span className="text-green-600">{formatCurrency(settlement.summary?.total_payable)}</span>
                  </div>
                </div>
              </div>
              
              {/* Recovery */}
              <div className={`p-4 rounded-lg border border-red-200 ${isDark ? 'bg-red-900/20' : 'bg-red-50'}`}>
                <h4 className="font-medium text-red-700 mb-3 flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  Recovery from Employee
                </h4>
                <div className="space-y-2 text-sm">
                  {settlement.recovery_components?.notice_period_recovery && (
                    <div className="flex justify-between">
                      <span>Notice Shortfall ({settlement.recovery_components.notice_period_recovery.shortfall_days} days)</span>
                      <span className="font-bold text-red-600">-{formatCurrency(settlement.recovery_components.notice_period_recovery.amount)}</span>
                    </div>
                  )}
                  {settlement.recovery_components?.loan_recovery?.total > 0 && (
                    <div className="flex justify-between">
                      <span>Pending Loans</span>
                      <span className="font-bold text-red-600">-{formatCurrency(settlement.recovery_components.loan_recovery.total)}</span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex justify-between font-bold">
                    <span>Total Recovery</span>
                    <span className="text-red-600">-{formatCurrency(settlement.summary?.total_recovery)}</span>
                  </div>
                </div>
              </div>
              
              {/* Net Settlement */}
              <div className={`p-6 rounded-lg text-center ${
                settlement.summary?.net_settlement >= 0 
                  ? 'bg-blue-100 border-2 border-blue-300' 
                  : 'bg-amber-100 border-2 border-amber-300'
              }`}>
                <p className="text-sm font-medium text-zinc-600 mb-1">NET SETTLEMENT</p>
                <p className={`text-3xl font-bold ${settlement.summary?.net_settlement >= 0 ? 'text-blue-600' : 'text-amber-600'}`}>
                  {formatCurrency(settlement.summary?.net_settlement)}
                </p>
                <p className="text-xs mt-1 text-zinc-500">
                  {settlement.summary?.net_settlement >= 0 ? 'Payable to employee' : 'Recoverable from employee'}
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center">
              <Calculator className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
              <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                Settlement not yet calculated
              </p>
              {selectedRequest && canCalculateSettlement(selectedRequest) && (
                <Button
                  className="mt-4 bg-purple-600 hover:bg-purple-700"
                  onClick={() => calculateSettlementMutation.mutate(selectedRequest.id)}
                  disabled={calculateSettlementMutation.isPending}
                >
                  {calculateSettlementMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Calculator className="w-4 h-4 mr-2" />
                  Calculate F&F Settlement
                </Button>
              )}
            </div>
          )}
          
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => { setShowSettlementDialog(false); setSettlement(null); }}>
              Close
            </Button>
            
            {selectedRequest && canApproveSettlement(selectedRequest) && (
              <>
                <Button
                  variant="destructive"
                  onClick={() => approveSettlementMutation.mutate({ exitId: selectedRequest.id, approved: false, remarks: 'Rejected' })}
                  disabled={approveSettlementMutation.isPending}
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </Button>
                <Button
                  onClick={() => approveSettlementMutation.mutate({ exitId: selectedRequest.id, approved: true, remarks: 'Approved' })}
                  disabled={approveSettlementMutation.isPending}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {approveSettlementMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve Settlement
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Helper to determine step status for progress bar
const getStepStatus = (status, stepIndex) => {
  const statusSteps = {
    pending: 0,
    admin_approved: 1,
    hr_approved: 2,
    initiated: 2,
    clearance_complete: 3,
    settlement_calculated: 4,
    approved: 5,
    completed: 6
  };
  
  const currentStepIndex = statusSteps[status] ?? 0;
  
  if (stepIndex < currentStepIndex) return 'done';
  if (stepIndex === currentStepIndex) return 'current';
  return 'pending';
};

export default ExitManagement;
