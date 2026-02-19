import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';
import { 
  CheckCircle, XCircle, Clock, AlertCircle, ChevronRight, 
  FileText, Calendar, User, MessageSquare, Send, DollarSign,
  Building2, CreditCard, Eye, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../contexts/ThemeContext';

const APPROVAL_TYPE_LABELS = {
  sow_item: 'SOW Item',
  agreement: 'Agreement',
  quotation: 'Quotation',
  leave_request: 'Leave Request',
  expense: 'Expense',
  client_communication: 'Client Communication',
  ctc_structure: 'CTC Structure',
  bank_change: 'Bank Details Change'
};

const ApprovalsCenter = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [ctcApprovals, setCtcApprovals] = useState([]);
  const [bankApprovals, setBankApprovals] = useState([]);
  const [goLiveApprovals, setGoLiveApprovals] = useState([]);
  const [permissionApprovals, setPermissionApprovals] = useState([]);
  const [myRequests, setMyRequests] = useState([]);
  const [allApprovals, setAllApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [actionDialog, setActionDialog] = useState(false);
  const [actionType, setActionType] = useState('');
  const [comments, setComments] = useState('');
  const [ctcDetailDialog, setCtcDetailDialog] = useState(false);
  const [selectedCtc, setSelectedCtc] = useState(null);
  const [bankDetailDialog, setBankDetailDialog] = useState(false);
  const [selectedBank, setSelectedBank] = useState(null);
  const [permissionDetailDialog, setPermissionDetailDialog] = useState(false);
  const [selectedPermission, setSelectedPermission] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const isManager = ['admin', 'manager', 'hr_manager', 'project_manager'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const requests = [
        axios.get(`${API}/approvals/pending`).catch(() => ({ data: [] })),
        axios.get(`${API}/approvals/my-requests`).catch(() => ({ data: [] }))
      ];
      
      // Fetch CTC approvals and permission change requests for admin
      if (isAdmin) {
        requests.push(axios.get(`${API}/ctc/pending-approvals`).catch(() => ({ data: [] })));
        requests.push(axios.get(`${API}/admin/bank-change-requests`).catch(() => ({ data: [] })));
        requests.push(axios.get(`${API}/go-live/pending`).catch(() => ({ data: [] })));
        requests.push(axios.get(`${API}/permission-change-requests`).catch(() => ({ data: [] })));
      }
      
      // Fetch bank approvals for HR
      if (isHR) {
        requests.push(axios.get(`${API}/hr/bank-change-requests`).catch(() => ({ data: [] })));
      }
      
      const results = await Promise.all(requests);
      
      setPendingApprovals(results[0]?.data || []);
      setMyRequests(results[1]?.data || []);
      
      if (isAdmin) {
        setCtcApprovals(results[2]?.data || []);
        setBankApprovals(results[3]?.data || []);
        setGoLiveApprovals(results[4]?.data || []);
        setPermissionApprovals((results[5]?.data || []).filter(r => r.status === 'pending'));
      } else if (isHR) {
        setBankApprovals(results[2]?.data || []);
      }
      
      // Fetch all approvals if admin/manager
      if (isManager) {
        const allRes = await axios.get(`${API}/approvals/all`).catch(() => ({ data: [] }));
        setAllApprovals(allRes.data || []);
      }
    } catch (error) {
      console.error('Error fetching approvals:', error);
      toast.error('Failed to load approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async () => {
    if (!selectedApproval) return;
    
    setActionLoading(true);
    try {
      await axios.post(`${API}/approvals/${selectedApproval.id}/action`, {
        action: actionType,
        comments: comments
      });
      
      toast.success(`Request ${actionType === 'approve' ? 'approved' : 'rejected'} successfully`);
      setActionDialog(false);
      setComments('');
      setSelectedApproval(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${actionType} request`);
    } finally {
      setActionLoading(false);
    }
  };

  const openActionDialog = (approval, action) => {
    setSelectedApproval(approval);
    setActionType(action);
    setComments('');
    setActionDialog(true);
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      approved: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      rejected: 'bg-red-100 text-red-700 border-red-200',
      escalated: 'bg-purple-100 text-purple-700 border-purple-200'
    };
    return styles[status] || 'bg-zinc-100 text-zinc-700 border-zinc-200';
  };

  const getStatusIcon = (status) => {
    const icons = {
      pending: <Clock className="w-4 h-4 text-yellow-600" />,
      approved: <CheckCircle className="w-4 h-4 text-emerald-600" />,
      rejected: <XCircle className="w-4 h-4 text-red-600" />,
      escalated: <AlertCircle className="w-4 h-4 text-purple-600" />
    };
    return icons[status] || <Clock className="w-4 h-4 text-zinc-600" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  // Calculate total pending for current user
  const totalPending = pendingApprovals.length + ctcApprovals.length + bankApprovals.length + goLiveApprovals.length + permissionApprovals.length;

  // Permission Change Action handlers
  const handlePermissionAction = async (requestId, action) => {
    setActionLoading(true);
    try {
      if (action === 'approve') {
        await axios.post(`${API}/permission-change-requests/${requestId}/approve`);
        toast.success('Permission changes approved successfully');
      } else {
        await axios.post(`${API}/permission-change-requests/${requestId}/reject`, { reason: comments || 'Rejected by Admin' });
        toast.success('Permission changes rejected');
      }
      setPermissionDetailDialog(false);
      setSelectedPermission(null);
      setComments('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} permission changes`);
    } finally {
      setActionLoading(false);
    }
  };

  // CTC Action handlers
  const handleCtcAction = async (ctcId, action) => {
    setActionLoading(true);
    try {
      if (action === 'approve') {
        await axios.post(`${API}/ctc/${ctcId}/approve`, { comments });
        toast.success('CTC structure approved successfully');
      } else {
        await axios.post(`${API}/ctc/${ctcId}/reject`, { reason: comments });
        toast.success('CTC structure rejected');
      }
      setCtcDetailDialog(false);
      setSelectedCtc(null);
      setComments('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} CTC structure`);
    } finally {
      setActionLoading(false);
    }
  };

  // Bank Change Action handlers
  const handleBankAction = async (employeeId, action) => {
    setActionLoading(true);
    try {
      const endpoint = isAdmin 
        ? `${API}/admin/bank-change-request/${employeeId}/${action}`
        : `${API}/hr/bank-change-request/${employeeId}/${action}`;
      
      await axios.post(endpoint, { reason: comments });
      toast.success(`Bank change request ${action === 'approve' ? 'approved' : 'rejected'}`);
      setBankDetailDialog(false);
      setSelectedBank(null);
      setComments('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} bank change request`);
    } finally {
      setActionLoading(false);
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
    return `₹${amount.toLocaleString('en-IN')}`;
  };

  return (
    <div data-testid="approvals-center" className={isDark ? 'text-zinc-100' : ''}>
      <div className="mb-8">
        <h1 className={`text-2xl md:text-3xl font-semibold tracking-tight mb-2 ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
          Approvals Center
        </h1>
        <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>Review and manage approval requests</p>
      </div>

      {/* Stats - Updated to include CTC and Bank approvals */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 md:gap-4 mb-6">
        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Pending</p>
                <p className="text-xl md:text-2xl font-semibold text-yellow-600">{totalPending}</p>
              </div>
              <Clock className="w-6 h-6 md:w-8 md:h-8 text-yellow-500/30" />
            </div>
          </CardContent>
        </Card>

        {isAdmin && (
          <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>CTC Approvals</p>
                  <p className="text-xl md:text-2xl font-semibold text-purple-600">{ctcApprovals.length}</p>
                </div>
                <DollarSign className="w-6 h-6 md:w-8 md:h-8 text-purple-500/30" />
              </div>
            </CardContent>
          </Card>
        )}

        {isAdmin && (
          <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Permissions</p>
                  <p className="text-xl md:text-2xl font-semibold text-indigo-600">{permissionApprovals.length}</p>
                </div>
                <User className="w-6 h-6 md:w-8 md:h-8 text-indigo-500/30" />
              </div>
            </CardContent>
          </Card>
        )}

        {(isAdmin || isHR) && (
          <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
            <CardContent className="p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Bank Changes</p>
                  <p className="text-xl md:text-2xl font-semibold text-rose-600">{bankApprovals.length}</p>
                </div>
                <Building2 className="w-6 h-6 md:w-8 md:h-8 text-rose-500/30" />
              </div>
            </CardContent>
          </Card>
        )}

        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>My Requests</p>
                <p className="text-xl md:text-2xl font-semibold text-blue-600">{myRequests.length}</p>
              </div>
              <Send className="w-6 h-6 md:w-8 md:h-8 text-blue-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Approved</p>
                <p className="text-xl md:text-2xl font-semibold text-emerald-600">
                  {myRequests.filter(r => r.overall_status === 'approved').length}
                </p>
              </div>
              <CheckCircle className="w-6 h-6 md:w-8 md:h-8 text-emerald-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg`}>
          <CardContent className="p-3 md:p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-[10px] md:text-xs uppercase ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Rejected</p>
                <p className="text-xl md:text-2xl font-semibold text-red-600">
                  {myRequests.filter(r => r.overall_status === 'rejected').length}
                </p>
              </div>
              <XCircle className="w-6 h-6 md:w-8 md:h-8 text-red-500/30" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* CTC Approvals Section - Only for Admin */}
      {isAdmin && ctcApprovals.length > 0 && (
        <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-3">
            <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <DollarSign className="w-5 h-5 text-purple-500" />
              Pending CTC Approvals ({ctcApprovals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {ctcApprovals.map((ctc, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          {ctc.employee_name || 'Unknown Employee'}
                        </span>
                        <Badge className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                          CTC Structure
                        </Badge>
                      </div>
                      <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        <span>Annual CTC: <strong className="text-purple-600">{formatCurrency(ctc.annual_ctc)}</strong></span>
                        <span className="mx-2">•</span>
                        <span>Effective: {ctc.effective_date || 'N/A'}</span>
                      </div>
                      <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Submitted by: {ctc.created_by || 'HR'} on {new Date(ctc.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setSelectedCtc(ctc); setCtcDetailDialog(true); }}
                        className={isDark ? 'border-zinc-600' : ''}
                      >
                        <Eye className="w-4 h-4 mr-1" /> View
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => { setSelectedCtc(ctc); setCtcDetailDialog(true); }}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" /> Approve
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Permission Change Requests Section - For Admin */}
      {isAdmin && permissionApprovals.length > 0 && (
        <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-3">
            <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <User className="w-5 h-5 text-indigo-500" />
              Pending Permission Changes ({permissionApprovals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {permissionApprovals.map((perm, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          {perm.employee_name} ({perm.employee_id})
                        </span>
                        <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                          Permission Change
                        </Badge>
                      </div>
                      <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        <span>Role: <strong>{perm.changes?.role || 'N/A'}</strong></span>
                        {perm.changes?.reporting_manager_id && (
                          <>
                            <span className="mx-2">•</span>
                            <span>New Manager: {perm.changes.reporting_manager_id}</span>
                          </>
                        )}
                      </div>
                      <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Requested by: {perm.requested_by_name} on {new Date(perm.created_at).toLocaleDateString()}
                        {perm.note && <span className="ml-2">• Note: {perm.note}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setSelectedPermission(perm); setPermissionDetailDialog(true); }}
                        className={isDark ? 'border-zinc-600' : ''}
                        data-testid={`view-perm-${perm.id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" /> View
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handlePermissionAction(perm.id, 'approve')}
                        className="bg-emerald-600 hover:bg-emerald-700"
                        data-testid={`approve-perm-${perm.id}`}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          const reason = prompt('Enter rejection reason:');
                          if (reason) {
                            setComments(reason);
                            handlePermissionAction(perm.id, 'reject');
                          }
                        }}
                        data-testid={`reject-perm-${perm.id}`}
                      >
                        <XCircle className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Go-Live Approvals Section - For Admin */}
      {isAdmin && goLiveApprovals.length > 0 && (
        <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-3">
            <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <Send className="w-5 h-5 text-emerald-500" />
              Pending Go-Live Approvals ({goLiveApprovals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {goLiveApprovals.map((req, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          {req.employee_name} ({req.employee_code})
                        </span>
                        <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          Go-Live
                        </Badge>
                      </div>
                      <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        <span>Department: {req.department || 'N/A'}</span>
                      </div>
                      <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Submitted by: {req.submitted_by_name} on {new Date(req.submitted_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={async () => {
                          try {
                            await axios.post(`${API}/go-live/${req.id}/approve`);
                            toast.success('Go-Live approved!');
                            fetchData();
                          } catch (error) {
                            toast.error('Failed to approve');
                          }
                        }}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={async () => {
                          const reason = prompt('Enter rejection reason:');
                          if (!reason) return;
                          try {
                            await axios.post(`${API}/go-live/${req.id}/reject`, { reason });
                            toast.success('Go-Live rejected');
                            fetchData();
                          } catch (error) {
                            toast.error('Failed to reject');
                          }
                        }}
                      >
                        <XCircle className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bank Change Approvals Section - For Admin and HR */}
      {(isAdmin || isHR) && bankApprovals.length > 0 && (
        <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
          <CardHeader className="pb-3">
            <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <Building2 className="w-5 h-5 text-rose-500" />
              Pending Bank Detail Changes ({bankApprovals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {bankApprovals.map((bank, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          {bank.employee_name || 'Unknown Employee'}
                        </span>
                        <Badge className={`${bank.status === 'pending_hr' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'} ${isDark ? 'dark:bg-amber-900/30 dark:text-amber-400' : ''}`}>
                          {bank.status === 'pending_hr' ? 'Pending HR' : 'Pending Admin'}
                        </Badge>
                      </div>
                      <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        <span>Bank: <strong>{bank.new_bank_details?.bank_name}</strong></span>
                        <span className="mx-2">•</span>
                        <span>A/C: ****{bank.new_bank_details?.account_number?.slice(-4)}</span>
                      </div>
                      <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Reason: {bank.reason || 'Not specified'}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setSelectedBank(bank); setBankDetailDialog(true); }}
                        className={isDark ? 'border-zinc-600' : ''}
                      >
                        <Eye className="w-4 h-4 mr-1" /> View
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => { setSelectedBank(bank); setBankDetailDialog(true); }}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" /> Review
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className={`flex border-b ${isDark ? 'border-zinc-700' : 'border-zinc-200'} mb-6 overflow-x-auto`}>
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-4 md:px-6 py-3 text-xs md:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'pending' 
              ? isDark ? 'border-orange-500 text-orange-400' : 'border-zinc-950 text-zinc-950'
              : isDark ? 'border-transparent text-zinc-500 hover:text-zinc-300' : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
        >
          <Clock className="w-4 h-4 inline mr-1 md:mr-2" />
          General ({pendingApprovals.length})
        </button>
        <button
          onClick={() => setActiveTab('my-requests')}
          className={`px-4 md:px-6 py-3 text-xs md:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'my-requests' 
              ? 'border-zinc-950 text-zinc-950' 
              : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
        >
          <Send className="w-4 h-4 inline mr-2" />
          My Requests ({myRequests.length})
        </button>
        {isManager && (
          <button
            onClick={() => setActiveTab('all')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'all' 
                ? 'border-zinc-950 text-zinc-950' 
                : 'border-transparent text-zinc-500 hover:text-zinc-950'
            }`}
          >
            <FileText className="w-4 h-4 inline mr-2" />
            All Approvals ({allApprovals.length})
          </button>
        )}
      </div>

      {/* Pending Approvals Tab */}
      {activeTab === 'pending' && (
        <div className="space-y-4">
          {pendingApprovals.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-12 text-center">
                <CheckCircle className="w-12 h-12 text-emerald-300 mx-auto mb-4" />
                <p className="text-zinc-500">No pending approvals. You're all caught up!</p>
              </CardContent>
            </Card>
          ) : (
            pendingApprovals.map(approval => (
              <Card key={approval.id} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                          {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                        </span>
                        {approval.is_client_facing && (
                          <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">Client Facing</span>
                        )}
                        {approval.requires_hr_approval && (
                          <span className="px-2 py-1 text-xs bg-pink-100 text-pink-700 rounded">HR Required</span>
                        )}
                      </div>
                      <h3 className="font-medium text-zinc-950 text-lg">{approval.reference_title}</h3>
                      <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
                        <span className="flex items-center gap-1">
                          <User className="w-4 h-4" />
                          {approval.requester_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {new Date(approval.created_at).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1">
                          Level {approval.current_level} of {approval.max_level}
                        </span>
                      </div>
                      
                      {/* Approval Chain */}
                      <div className="mt-4 flex items-center gap-2 text-xs">
                        {approval.approval_levels?.map((level, idx) => (
                          <React.Fragment key={idx}>
                            <div className={`flex items-center gap-1 px-2 py-1 rounded ${
                              level.status === 'approved' ? 'bg-emerald-50 text-emerald-700' :
                              level.status === 'rejected' ? 'bg-red-50 text-red-700' :
                              level.level === approval.current_level ? 'bg-yellow-50 text-yellow-700 border border-yellow-300' :
                              'bg-zinc-50 text-zinc-500'
                            }`}>
                              {getStatusIcon(level.status)}
                              <span>{level.approver_name}</span>
                              <span className="text-xs opacity-60">({level.approver_type?.replace('_', ' ')})</span>
                            </div>
                            {idx < approval.approval_levels.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-zinc-300" />
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 ml-4">
                      <Button
                        onClick={() => openActionDialog(approval, 'approve')}
                        className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </Button>
                      <Button
                        onClick={() => openActionDialog(approval, 'reject')}
                        variant="outline"
                        className="border-red-300 text-red-600 hover:bg-red-50 rounded-sm"
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* My Requests Tab */}
      {activeTab === 'my-requests' && (
        <div className="space-y-4">
          {myRequests.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-12 text-center">
                <Send className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
                <p className="text-zinc-500">You haven't submitted any approval requests yet.</p>
              </CardContent>
            </Card>
          ) : (
            myRequests.map(approval => (
              <Card key={approval.id} className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                          {approval.overall_status}
                        </span>
                        <span className="text-xs text-zinc-400">
                          {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                        </span>
                      </div>
                      <h3 className="font-medium text-zinc-950">{approval.reference_title}</h3>
                      <div className="text-xs text-zinc-500 mt-1">
                        Submitted {new Date(approval.created_at).toLocaleDateString()}
                      </div>
                      
                      {/* Approval Chain */}
                      <div className="mt-3 flex items-center gap-2 text-xs">
                        {approval.approval_levels?.map((level, idx) => (
                          <React.Fragment key={idx}>
                            <div className={`flex items-center gap-1 px-2 py-1 rounded ${
                              level.status === 'approved' ? 'bg-emerald-50 text-emerald-700' :
                              level.status === 'rejected' ? 'bg-red-50 text-red-700' :
                              level.level === approval.current_level ? 'bg-yellow-50 text-yellow-700' :
                              'bg-zinc-50 text-zinc-500'
                            }`}>
                              {getStatusIcon(level.status)}
                              <span>{level.approver_name}</span>
                            </div>
                            {idx < approval.approval_levels.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-zinc-300" />
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {getStatusIcon(approval.overall_status)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* All Approvals Tab (Admin/Manager) */}
      {activeTab === 'all' && isManager && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <th className="px-4 py-3 text-left">Request</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Requester</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Current Level</th>
                  <th className="px-4 py-3 text-left">Date</th>
                </tr>
              </thead>
              <tbody>
                {allApprovals.map(approval => (
                  <tr key={approval.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 font-medium text-zinc-900">{approval.reference_title}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{approval.requester_name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                        {approval.overall_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {approval.current_level} / {approval.max_level}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-500">
                      {new Date(approval.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {allApprovals.length === 0 && (
              <div className="text-center py-12 text-zinc-400">
                No approval requests found.
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Action Dialog */}
      <Dialog open={actionDialog} onOpenChange={setActionDialog}>
        <DialogContent className={`${isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200'} rounded-lg max-w-md`}>
          <DialogHeader>
            <DialogTitle className={`text-xl font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
              {actionType === 'approve' ? 'Approve Request' : 'Reject Request'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedApproval && (
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>{selectedApproval.reference_title}</p>
                <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Requested by {selectedApproval.requester_name}
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <label className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                Comments {actionType === 'reject' && '(required)'}
              </label>
              <Textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder={actionType === 'approve' ? 'Optional comments...' : 'Reason for rejection...'}
                rows={3}
                className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
              />
            </div>
            
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setActionDialog(false)} variant="outline" className={`flex-1 ${isDark ? 'border-zinc-600' : ''}`}>
                Cancel
              </Button>
              <Button 
                onClick={handleAction}
                disabled={actionType === 'reject' && !comments || actionLoading}
                className={`flex-1 ${
                  actionType === 'approve' 
                    ? 'bg-emerald-600 text-white hover:bg-emerald-700' 
                    : 'bg-red-600 text-white hover:bg-red-700'
                }`}
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : (actionType === 'approve' ? 'Approve' : 'Reject')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* CTC Detail Dialog */}
      <Dialog open={ctcDetailDialog} onOpenChange={setCtcDetailDialog}>
        <DialogContent className={`${isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200'} rounded-lg max-w-2xl max-h-[90vh] overflow-y-auto`}>
          <DialogHeader>
            <DialogTitle className={`text-xl font-semibold flex items-center gap-2 ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
              <DollarSign className="w-5 h-5 text-purple-500" />
              CTC Structure Approval
            </DialogTitle>
          </DialogHeader>
          {selectedCtc && (
            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Employee</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedCtc.employee_name}</p>
                    {selectedCtc.employee_code && (
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{selectedCtc.employee_code}</p>
                    )}
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Annual CTC</p>
                    <p className="font-bold text-purple-600 text-lg">{formatCurrency(selectedCtc.annual_ctc)}</p>
                    {selectedCtc.previous_ctc && (
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Previous: {formatCurrency(selectedCtc.previous_ctc)}
                      </p>
                    )}
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Effective Month</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedCtc.effective_month || selectedCtc.effective_date}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Submitted By</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedCtc.created_by_name || selectedCtc.created_by || 'HR'}</p>
                  </div>
                </div>
              </div>

              {/* CTC Components */}
              <div>
                <h4 className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Salary Components</h4>
                <div className={`border rounded-lg overflow-hidden ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <table className="w-full text-sm">
                    <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-50'}>
                      <tr>
                        <th className={`text-left px-3 py-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Component</th>
                        <th className={`text-right px-3 py-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Monthly</th>
                        <th className={`text-right px-3 py-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Annual</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Handle components as object (dictionary) from backend */}
                      {selectedCtc.components && typeof selectedCtc.components === 'object' && !Array.isArray(selectedCtc.components) && 
                        Object.values(selectedCtc.components)
                          .filter(c => c.enabled !== false)
                          .sort((a, b) => (a.is_deduction ? 1 : 0) - (b.is_deduction ? 1 : 0))
                          .map((comp, idx) => (
                        <tr key={idx} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'} ${comp.is_deduction ? 'text-red-600' : ''}`}>
                          <td className={`px-3 py-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>{comp.name}</td>
                          <td className={`text-right px-3 py-2 ${comp.is_deduction ? 'text-red-600' : ''}`}>
                            {comp.is_deduction ? '-' : ''}{formatCurrency(comp.monthly || comp.monthly_amount || 0)}
                          </td>
                          <td className={`text-right px-3 py-2 ${comp.is_deduction ? 'text-red-600' : ''}`}>
                            {comp.is_deduction ? '-' : ''}{formatCurrency(comp.annual || comp.annual_amount || 0)}
                          </td>
                        </tr>
                      ))}
                      {/* Handle components as array (legacy) */}
                      {Array.isArray(selectedCtc.components) && selectedCtc.components.filter(c => c.enabled !== false).map((comp, idx) => (
                        <tr key={idx} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'} ${comp.is_deduction ? 'text-red-600' : ''}`}>
                          <td className={`px-3 py-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>{comp.name}</td>
                          <td className={`text-right px-3 py-2 ${comp.is_deduction ? 'text-red-600' : ''}`}>
                            {comp.is_deduction ? '-' : ''}{formatCurrency(comp.monthly || comp.monthly_amount || 0)}
                          </td>
                          <td className={`text-right px-3 py-2 ${comp.is_deduction ? 'text-red-600' : ''}`}>
                            {comp.is_deduction ? '-' : ''}{formatCurrency(comp.annual || comp.annual_amount || 0)}
                          </td>
                        </tr>
                      ))}
                      {/* Show message only if no components */}
                      {(!selectedCtc.components || (typeof selectedCtc.components === 'object' && !Array.isArray(selectedCtc.components) && Object.keys(selectedCtc.components).length === 0) || (Array.isArray(selectedCtc.components) && selectedCtc.components.length === 0)) && (
                        <tr>
                          <td colSpan={3} className={`px-3 py-4 text-center ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                            No component breakdown available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* CTC Summary */}
              {selectedCtc.summary && (
                <div className={`p-3 rounded-lg ${isDark ? 'bg-purple-900/20 border border-purple-800' : 'bg-purple-50 border border-purple-200'}`}>
                  <h4 className={`text-sm font-medium mb-2 ${isDark ? 'text-purple-300' : 'text-purple-700'}`}>Summary</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Gross Monthly</p>
                      <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{formatCurrency(selectedCtc.summary.gross_monthly)}</p>
                    </div>
                    <div>
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Deductions</p>
                      <p className="font-medium text-red-600">-{formatCurrency(selectedCtc.summary.total_deductions_monthly)}</p>
                    </div>
                    <div>
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>In-Hand (Approx)</p>
                      <p className="font-bold text-emerald-600">{formatCurrency(selectedCtc.summary.in_hand_approx_monthly)}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Comments</label>
                <Textarea
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Optional comments for approval/rejection..."
                  rows={2}
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setCtcDetailDialog(false)} className={isDark ? 'border-zinc-600' : ''}>
                  Cancel
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleCtcAction(selectedCtc.id, 'reject')}
                  disabled={actionLoading}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><XCircle className="w-4 h-4 mr-1" /> Reject</>}
                </Button>
                <Button 
                  onClick={() => handleCtcAction(selectedCtc.id, 'approve')}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4 mr-1" /> Approve</>}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bank Detail Dialog */}
      <Dialog open={bankDetailDialog} onOpenChange={setBankDetailDialog}>
        <DialogContent className={`${isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200'} rounded-lg max-w-2xl max-h-[90vh] overflow-y-auto`}>
          <DialogHeader>
            <DialogTitle className={`text-xl font-semibold flex items-center gap-2 ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
              <Building2 className="w-5 h-5 text-rose-500" />
              Bank Details Change Request
            </DialogTitle>
          </DialogHeader>
          {selectedBank && (
            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Employee</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedBank.employee_name}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Status</p>
                    <Badge className={selectedBank.status === 'pending_hr' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}>
                      {selectedBank.status === 'pending_hr' ? 'Pending HR Review' : 'Pending Admin Approval'}
                    </Badge>
                  </div>
                  <div className="col-span-2">
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Reason for Change</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedBank.reason || 'Not specified'}</p>
                  </div>
                </div>
              </div>

              {/* Current vs New Bank Details */}
              <div className="grid grid-cols-2 gap-4">
                <div className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-200 bg-zinc-50'}`}>
                  <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Current Details</h4>
                  <div className="space-y-2 text-sm">
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Bank:</span> {selectedBank.current_bank_details?.bank_name || 'N/A'}</p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>A/C:</span> ****{selectedBank.current_bank_details?.account_number?.slice(-4) || '****'}</p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>IFSC:</span> {selectedBank.current_bank_details?.ifsc_code || 'N/A'}</p>
                  </div>
                </div>
                <div className={`p-4 rounded-lg border-2 border-emerald-500 ${isDark ? 'bg-emerald-900/20' : 'bg-emerald-50'}`}>
                  <h4 className="text-sm font-medium mb-3 text-emerald-600">New Details</h4>
                  <div className="space-y-2 text-sm">
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Holder:</span> <strong>{selectedBank.new_bank_details?.account_holder_name}</strong></p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Bank:</span> <strong>{selectedBank.new_bank_details?.bank_name}</strong></p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>A/C:</span> <strong>{selectedBank.new_bank_details?.account_number}</strong></p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>IFSC:</span> <strong>{selectedBank.new_bank_details?.ifsc_code}</strong></p>
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Branch:</span> {selectedBank.new_bank_details?.branch_name || 'N/A'}</p>
                  </div>
                </div>
              </div>

              {/* Proof Document */}
              {selectedBank.proof_document && (
                <div>
                  <h4 className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                    Proof Document: {selectedBank.proof_filename}
                  </h4>
                  {selectedBank.proof_document.startsWith('data:image') ? (
                    <img 
                      src={selectedBank.proof_document} 
                      alt="Proof" 
                      className="max-h-48 rounded-lg border"
                    />
                  ) : (
                    <a 
                      href={selectedBank.proof_document} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline flex items-center gap-1"
                    >
                      <FileText className="w-4 h-4" /> View Document
                    </a>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <label className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Comments</label>
                <Textarea
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Comments for approval/rejection..."
                  rows={2}
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setBankDetailDialog(false)} className={isDark ? 'border-zinc-600' : ''}>
                  Cancel
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleBankAction(selectedBank.employee_id, 'reject')}
                  disabled={actionLoading}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><XCircle className="w-4 h-4 mr-1" /> Reject</>}
                </Button>
                <Button 
                  onClick={() => handleBankAction(selectedBank.employee_id, 'approve')}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4 mr-1" /> Approve</>}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Permission Change Detail Dialog */}
      <Dialog open={permissionDetailDialog} onOpenChange={setPermissionDetailDialog}>
        <DialogContent className={`${isDark ? 'border-zinc-700 bg-zinc-900' : 'border-zinc-200'} rounded-lg max-w-2xl max-h-[90vh] overflow-y-auto`}>
          <DialogHeader>
            <DialogTitle className={`text-xl font-semibold flex items-center gap-2 ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
              <User className="w-5 h-5 text-indigo-500" />
              Permission Change Request
            </DialogTitle>
          </DialogHeader>
          {selectedPermission && (
            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Employee</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {selectedPermission.employee_name} ({selectedPermission.employee_id})
                    </p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Requested By</p>
                    <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {selectedPermission.requested_by_name}
                    </p>
                  </div>
                  {selectedPermission.note && (
                    <div className="col-span-2">
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Note</p>
                      <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>{selectedPermission.note}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Changes Requested */}
              <div className={`p-4 rounded-lg border-2 border-indigo-500 ${isDark ? 'bg-indigo-900/20' : 'bg-indigo-50'}`}>
                <h4 className="text-sm font-medium mb-3 text-indigo-600">Requested Changes</h4>
                <div className="space-y-2 text-sm">
                  {selectedPermission.changes?.role && (
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Role:</span> <strong>{selectedPermission.changes.role}</strong></p>
                  )}
                  {selectedPermission.changes?.reporting_manager_id && (
                    <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Reporting Manager:</span> <strong>{selectedPermission.changes.reporting_manager_id}</strong></p>
                  )}
                  {selectedPermission.changes?.permissions && (
                    <div>
                      <p className={`${isDark ? 'text-zinc-500' : 'text-zinc-400'} mb-1`}>Module Permissions:</p>
                      <div className="pl-2 space-y-1">
                        {Object.entries(selectedPermission.changes.permissions).map(([module, perms]) => (
                          <div key={module} className="text-xs">
                            <strong className="capitalize">{module}:</strong> {Object.entries(perms).map(([feature, actions]) => (
                              <span key={feature} className="ml-2">
                                {feature}: {Object.entries(actions).filter(([,v]) => v).map(([k]) => k).join(', ')}
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Original Values */}
              {selectedPermission.original_values && (
                <div className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-200 bg-zinc-50'}`}>
                  <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Original Values</h4>
                  <div className="space-y-2 text-sm">
                    {selectedPermission.original_values.role && (
                      <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Role:</span> {selectedPermission.original_values.role}</p>
                    )}
                    {selectedPermission.original_values.reporting_manager_id && (
                      <p><span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Reporting Manager:</span> {selectedPermission.original_values.reporting_manager_id}</p>
                    )}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>Comments</label>
                <Textarea
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Comments for approval/rejection..."
                  rows={2}
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setPermissionDetailDialog(false)} className={isDark ? 'border-zinc-600' : ''}>
                  Cancel
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handlePermissionAction(selectedPermission.id, 'reject')}
                  disabled={actionLoading}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><XCircle className="w-4 h-4 mr-1" /> Reject</>}
                </Button>
                <Button 
                  onClick={() => handlePermissionAction(selectedPermission.id, 'approve')}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4 mr-1" /> Approve</>}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApprovalsCenter;
