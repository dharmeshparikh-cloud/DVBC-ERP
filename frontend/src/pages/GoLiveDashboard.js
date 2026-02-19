import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { 
  Rocket, CheckCircle, XCircle, Clock, User, Building2, 
  CreditCard, FileText, Key, AlertTriangle, ChevronRight,
  Shield, Send, Eye
} from 'lucide-react';

const GoLiveDashboard = () => {
  const { user } = useContext(AuthContext);
  const { isDark } = useTheme();
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [notes, setNotes] = useState('');
  const [filter, setFilter] = useState('all');
  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canVerifyBank = isAdmin || user?.role === 'hr_manager';

  useEffect(() => {
    fetchEmployees();
    if (isAdmin) {
      fetchPendingRequests();
    }
  }, [isAdmin]);

  const fetchEmployees = async () => {
    try {
      const res = await axios.get(`${API}/employees`);
      // Filter employees who might need Go-Live
      const filtered = res.data.filter(emp => 
        emp.go_live_status !== 'active' || !emp.go_live_status
      );
      setEmployees(res.data);
    } catch (error) {
      toast.error('Failed to load employees');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingRequests = async () => {
    try {
      const res = await axios.get(`${API}/go-live/pending`);
      setPendingRequests(res.data);
    } catch (error) {
      console.error('Error fetching pending requests:', error);
    }
  };

  const fetchChecklist = async (employeeId) => {
    try {
      const res = await axios.get(`${API}/go-live/checklist/${employeeId}`);
      setChecklist(res.data);
      setSelectedEmployee(res.data.employee);
    } catch (error) {
      toast.error('Failed to load checklist');
    }
  };

  const handleSubmitGoLive = async () => {
    if (!selectedEmployee) return;
    
    try {
      await axios.post(`${API}/go-live/submit/${selectedEmployee.id}`, {
        checklist: checklist?.checklist,
        notes
      });
      toast.success('Go-Live request submitted for approval');
      setShowSubmitDialog(false);
      setNotes('');
      fetchEmployees();
      fetchChecklist(selectedEmployee.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  };

  const handleApprove = async (requestId) => {
    try {
      await axios.post(`${API}/go-live/${requestId}/approve`);
      toast.success('Go-Live approved! Employee is now active.');
      fetchPendingRequests();
      fetchEmployees();
      if (selectedEmployee) {
        fetchChecklist(selectedEmployee.id);
      }
    } catch (error) {
      toast.error('Failed to approve');
    }
  };

  const handleReject = async (requestId) => {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    
    try {
      await axios.post(`${API}/go-live/${requestId}/reject`, { reason });
      toast.success('Go-Live request rejected');
      fetchPendingRequests();
    } catch (error) {
      toast.error('Failed to reject');
    }
  };

  const handleVerifyBank = async (employeeId) => {
    try {
      await axios.post(`${API}/bank-verify/${employeeId}`);
      toast.success('Bank details verified');
      fetchChecklist(employeeId);
    } catch (error) {
      toast.error('Failed to verify bank details');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-emerald-100 text-emerald-700',
      pending: 'bg-amber-100 text-amber-700',
      rejected: 'bg-red-100 text-red-700',
      not_submitted: 'bg-zinc-100 text-zinc-600'
    };
    const labels = {
      active: 'Active',
      pending: 'Pending Approval',
      rejected: 'Rejected',
      not_submitted: 'Not Submitted'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.not_submitted}`}>
        {labels[status] || 'Not Started'}
      </span>
    );
  };

  const ChecklistItem = ({ label, checked, icon: Icon }) => (
    <div className={`flex items-center gap-3 p-3 rounded-lg ${
      checked 
        ? isDark ? 'bg-emerald-900/20 border border-emerald-700' : 'bg-emerald-50 border border-emerald-200'
        : isDark ? 'bg-zinc-800 border border-zinc-700' : 'bg-zinc-50 border border-zinc-200'
    }`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
        checked ? 'bg-emerald-500 text-white' : isDark ? 'bg-zinc-700 text-zinc-400' : 'bg-zinc-200 text-zinc-400'
      }`}>
        {checked ? <CheckCircle className="w-5 h-5" /> : <Icon className="w-4 h-4" />}
      </div>
      <span className={checked ? 'text-emerald-600 font-medium' : ''}>{label}</span>
    </div>
  );

  const filteredEmployees = employees.filter(emp => {
    if (filter === 'pending') return emp.go_live_status === 'pending' || !emp.go_live_status;
    if (filter === 'active') return emp.go_live_status === 'active';
    return true;
  });

  return (
    <div className={`min-h-screen p-6 ${isDark ? 'bg-zinc-900 text-white' : 'bg-zinc-50'}`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Rocket className="w-7 h-7 text-emerald-500" />
              Employee Go-Live Dashboard
            </h1>
            <p className={`mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              Track and manage employee activation status
            </p>
          </div>
        </div>

        {/* Admin: Pending Approvals */}
        {isAdmin && pendingRequests.length > 0 && (
          <div className={`mb-6 p-4 rounded-xl border-2 border-amber-400 ${
            isDark ? 'bg-amber-900/20' : 'bg-amber-50'
          }`}>
            <h2 className="text-lg font-semibold flex items-center gap-2 text-amber-600 mb-3">
              <Clock className="w-5 h-5" />
              Pending Go-Live Approvals ({pendingRequests.length})
            </h2>
            <div className="space-y-2">
              {pendingRequests.map(req => (
                <div key={req.id} className={`flex items-center justify-between p-3 rounded-lg ${
                  isDark ? 'bg-zinc-800' : 'bg-white'
                }`}>
                  <div>
                    <p className="font-medium">{req.employee_name} ({req.employee_code})</p>
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {req.department} • Submitted by {req.submitted_by_name}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => fetchChecklist(req.employee_id)}
                      data-testid={`view-${req.id}`}
                    >
                      <Eye className="w-4 h-4 mr-1" /> View
                    </Button>
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => handleApprove(req.id)}
                      data-testid={`approve-${req.id}`}
                    >
                      <CheckCircle className="w-4 h-4 mr-1" /> Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleReject(req.id)}
                      data-testid={`reject-${req.id}`}
                    >
                      <XCircle className="w-4 h-4 mr-1" /> Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Employee List */}
          <div className={`lg:col-span-1 rounded-xl border ${
            isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'
          }`}>
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-700">
              <h2 className="font-semibold">Employees</h2>
              <div className="flex gap-2 mt-2">
                {['all', 'pending', 'active'].map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      filter === f
                        ? 'bg-emerald-500 text-white'
                        : isDark ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-100 text-zinc-600'
                    }`}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {filteredEmployees.map(emp => (
                <div
                  key={emp.id}
                  onClick={() => fetchChecklist(emp.employee_id || emp.id)}
                  className={`p-3 border-b cursor-pointer transition-colors ${
                    selectedEmployee?.id === emp.id
                      ? isDark ? 'bg-emerald-900/30' : 'bg-emerald-50'
                      : isDark ? 'hover:bg-zinc-700' : 'hover:bg-zinc-50'
                  } ${isDark ? 'border-zinc-700' : 'border-zinc-100'}`}
                  data-testid={`emp-${emp.employee_id}`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                      <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {emp.employee_id} • {emp.department || emp.primary_department}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(emp.go_live_status)}
                      <ChevronRight className="w-4 h-4 text-zinc-400" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Checklist Panel */}
          <div className={`lg:col-span-2 rounded-xl border ${
            isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'
          }`}>
            {checklist ? (
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold">{checklist.employee.name}</h2>
                    <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                      {checklist.employee.employee_id} • {checklist.employee.department} • {checklist.employee.designation}
                    </p>
                  </div>
                  {getStatusBadge(checklist.checklist.go_live_status)}
                </div>

                {/* Checklist Items */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                  <ChecklistItem 
                    label="Onboarding Complete" 
                    checked={checklist.checklist.onboarding_complete}
                    icon={User}
                  />
                  <ChecklistItem 
                    label="CTC Approved" 
                    checked={checklist.checklist.ctc_approved}
                    icon={Building2}
                  />
                  <ChecklistItem 
                    label="Bank Details Added" 
                    checked={checklist.checklist.bank_details_added}
                    icon={CreditCard}
                  />
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <ChecklistItem 
                        label="Bank Verified" 
                        checked={checklist.checklist.bank_verified}
                        icon={Shield}
                      />
                    </div>
                    {canVerifyBank && checklist.checklist.bank_details_added && !checklist.checklist.bank_verified && (
                      <Button
                        size="sm"
                        className="bg-blue-600 hover:bg-blue-700"
                        onClick={() => handleVerifyBank(checklist.employee.id)}
                        data-testid="verify-bank-btn"
                      >
                        Verify
                      </Button>
                    )}
                  </div>
                  <ChecklistItem 
                    label="Documents Generated" 
                    checked={checklist.checklist.documents_generated}
                    icon={FileText}
                  />
                  <ChecklistItem 
                    label="Portal Access Granted" 
                    checked={checklist.checklist.portal_access_granted}
                    icon={Key}
                  />
                </div>

                {/* CTC Details */}
                {checklist.ctc_details && (
                  <div className={`p-4 rounded-lg mb-6 ${
                    isDark ? 'bg-zinc-700' : 'bg-zinc-100'
                  }`}>
                    <h3 className="font-medium mb-2">CTC Details</h3>
                    <p className="text-2xl font-bold text-emerald-500">
                      ₹{(checklist.ctc_details.annual_ctc / 100000).toFixed(2)} LPA
                    </p>
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      Effective from: {checklist.ctc_details.effective_from}
                    </p>
                  </div>
                )}

                {/* Go-Live Request Info */}
                {checklist.go_live_request && (
                  <div className={`p-4 rounded-lg mb-6 border ${
                    checklist.go_live_request.status === 'approved'
                      ? 'bg-emerald-50 border-emerald-200'
                      : checklist.go_live_request.status === 'rejected'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-amber-50 border-amber-200'
                  }`}>
                    <h3 className="font-medium mb-1">Go-Live Request</h3>
                    <p className="text-sm">Status: {checklist.go_live_request.status}</p>
                    <p className="text-sm">Submitted by: {checklist.go_live_request.submitted_by_name}</p>
                    {checklist.go_live_request.approved_by_name && (
                      <p className="text-sm">
                        {checklist.go_live_request.status === 'approved' ? 'Approved' : 'Rejected'} by: {checklist.go_live_request.approved_by_name}
                      </p>
                    )}
                    {checklist.go_live_request.rejection_reason && (
                      <p className="text-sm text-red-600">Reason: {checklist.go_live_request.rejection_reason}</p>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {!isAdmin && checklist.checklist.go_live_status === 'not_submitted' && (
                    <Button
                      className="bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => setShowSubmitDialog(true)}
                      disabled={!checklist.checklist.ctc_approved || !checklist.checklist.bank_details_added}
                      data-testid="submit-golive-btn"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Submit for Go-Live Approval
                    </Button>
                  )}
                  {checklist.checklist.go_live_status === 'active' && (
                    <div className="flex items-center gap-2 text-emerald-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Employee is LIVE!</span>
                    </div>
                  )}
                </div>

                {/* Warning if not ready */}
                {(!checklist.checklist.ctc_approved || !checklist.checklist.bank_details_added) && (
                  <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-amber-700">Not Ready for Go-Live</p>
                      <p className="text-sm text-amber-600">
                        {!checklist.checklist.ctc_approved && 'CTC approval is required. '}
                        {!checklist.checklist.bank_details_added && 'Bank details are required.'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center">
                <Rocket className={`w-16 h-16 mx-auto mb-4 ${isDark ? 'text-zinc-600' : 'text-zinc-300'}`} />
                <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                  Select an employee to view Go-Live checklist
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Submit Dialog */}
      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit Go-Live Request</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="mb-4">
              Submit Go-Live request for <strong>{selectedEmployee?.name}</strong> ({selectedEmployee?.employee_id})?
            </p>
            <p className="text-sm text-zinc-500 mb-4">
              This will notify Admin for final approval. Once approved, the employee will be marked as Active.
            </p>
            <Input
              placeholder="Add notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>Cancel</Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleSubmitGoLive}>
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GoLiveDashboard;
