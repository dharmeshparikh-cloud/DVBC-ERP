import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API, handleApiError } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { 
  Rocket, CheckCircle, XCircle, Clock, User, Building2, 
  CreditCard, FileText, Key, AlertTriangle, ChevronRight,
  Shield, Send, Eye, Mail, Upload, Download, Trash2, Loader2,
  CheckCircle2, XOctagon, RefreshCw
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
  const [pageError, setPageError] = useState(null);
  // Bank validation state
  const [bankValidation, setBankValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [bankProofs, setBankProofs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [showBankProofsDialog, setShowBankProofsDialog] = useState(false);
  const fileInputRef = useRef(null);
  
  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canVerifyBank = isAdmin || user?.role === 'hr_manager';
  const canUploadProof = isAdmin || isHR;

  useEffect(() => {
    fetchEmployees();
    if (isAdmin) {
      fetchPendingRequests();
    }
  }, [isAdmin]);

  const fetchEmployees = async () => {
    try {
      setPageError(null);
      const res = await axios.get(`${API}/employees`);
      // Handle both array and paginated response formats
      const data = res.data.items || res.data;
      // Filter employees who might need Go-Live
      const filtered = data.filter(emp => 
        emp.go_live_status !== 'active' || !emp.go_live_status
      );
      setEmployees(data);
    } catch (error) {
      const errorInfo = handleApiError(error, { operation: 'load employees' });
      setPageError(errorInfo);
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
      setPageError(null);
      setBankValidation(null); // Reset validation when switching employees
      const res = await axios.get(`${API}/go-live/checklist/${employeeId}`);
      setChecklist(res.data);
      setSelectedEmployee(res.data.employee);
      // Also fetch bank proofs
      fetchBankProofs(res.data.employee.id || employeeId);
    } catch (error) {
      const errorInfo = handleApiError(error, { operation: 'load Go-Live checklist' });
      setPageError(errorInfo);
    }
  };

  const handleSubmitGoLive = async () => {
    if (!selectedEmployee) return;
    
    try {
      setPageError(null);
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
      await axios.post(`${API}/go-live/bank-verify/${employeeId}`);
      toast.success('Bank details verified');
      fetchChecklist(employeeId);
    } catch (error) {
      toast.error('Failed to verify bank details');
    }
  };

  // Bank Validation Functions
  const handleValidateBankDetails = async (employeeId) => {
    setValidating(true);
    setBankValidation(null);
    try {
      const res = await axios.post(`${API}/go-live/validate-bank-details/${employeeId}`);
      setBankValidation(res.data);
      if (res.data.overall_valid) {
        toast.success('Bank details validated successfully');
      } else {
        toast.warning('Bank details validation found issues');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to validate bank details');
    } finally {
      setValidating(false);
    }
  };

  // Bank Proof Upload Functions
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !selectedEmployee) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Allowed: PDF, JPG, PNG, WEBP');
      return;
    }

    // Validate file size (5 MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File too large. Maximum size: 5 MB');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(
        `${API}/go-live/bank-proof/upload/${selectedEmployee.id}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      toast.success('Bank proof uploaded successfully');
      fetchBankProofs(selectedEmployee.id);
      fetchChecklist(selectedEmployee.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload bank proof');
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const fetchBankProofs = async (employeeId) => {
    try {
      const res = await axios.get(`${API}/go-live/bank-proof/list/${employeeId}`);
      setBankProofs(res.data.documents || []);
    } catch (error) {
      console.error('Failed to fetch bank proofs:', error);
      setBankProofs([]);
    }
  };

  const handleDownloadProof = async (employeeId, documentId, filename) => {
    try {
      const res = await axios.get(
        `${API}/go-live/bank-proof/download/${employeeId}/${documentId}`,
        { responseType: 'blob' }
      );
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Download started');
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const handleDeleteProof = async (employeeId, documentId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await axios.delete(`${API}/go-live/bank-proof/delete/${employeeId}/${documentId}`);
      toast.success('Document deleted');
      fetchBankProofs(employeeId);
      fetchChecklist(employeeId);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
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

  // Define URLs for each checklist item action
  const getChecklistActionUrl = (key, employeeId) => {
    const urlMap = {
      personal_details: `/employees?edit=${employeeId}`,
      official_email: `/employees?edit=${employeeId}&section=email`,
      department: `/employees?edit=${employeeId}&section=department`,
      reporting_manager: `/employees?edit=${employeeId}&section=manager`,
      bank_details: `/employees?edit=${employeeId}&section=bank`,
      bank_verified: null, // Handled separately with verify button
      documents: `/document-center?employee=${employeeId}`,
      portal_access: `/password-management?employee=${employeeId}`
    };
    return urlMap[key] || `/employees?edit=${employeeId}`;
  };

  const handleChecklistItemClick = (key, completed, employeeId) => {
    if (completed) return; // Don't navigate if already completed
    
    const url = getChecklistActionUrl(key, employeeId);
    if (url) {
      window.location.href = url;
    }
  };

  const ChecklistItem = ({ label, checked, icon: Icon, itemKey, employeeId, onClick }) => {
    const isClickable = !checked && onClick;
    
    return (
      <div 
        className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
          checked 
            ? isDark ? 'bg-emerald-900/20 border border-emerald-700' : 'bg-emerald-50 border border-emerald-200'
            : isDark ? 'bg-zinc-800 border border-zinc-700 hover:border-blue-500' : 'bg-zinc-50 border border-zinc-200 hover:border-blue-400'
        } ${isClickable ? 'cursor-pointer hover:shadow-md' : ''}`}
        onClick={() => isClickable && onClick()}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        data-testid={`checklist-item-${itemKey}`}
      >
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          checked ? 'bg-emerald-500 text-white' : isDark ? 'bg-zinc-700 text-zinc-400' : 'bg-zinc-200 text-zinc-400'
        }`}>
          {checked ? <CheckCircle className="w-5 h-5" /> : <Icon className="w-4 h-4" />}
        </div>
        <div className="flex-1">
          <span className={checked ? 'text-emerald-600 font-medium' : ''}>{label}</span>
          {!checked && isClickable && (
            <p className={`text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              Click to complete →
            </p>
          )}
        </div>
      </div>
    );
  };

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

        {/* Error Display */}
        {pageError && (
          <ErrorDisplay 
            error={pageError} 
            onDismiss={() => setPageError(null)}
            onRetry={() => {
              if (selectedEmployee) {
                fetchChecklist(selectedEmployee.employee_id || selectedEmployee.id);
              } else {
                fetchEmployees();
              }
            }}
          />
        )}

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
                  {getStatusBadge(checklist.employee.go_live_status)}
                </div>

                {/* Progress Summary */}
                <div className={`mb-6 p-4 rounded-lg ${isDark ? 'bg-zinc-700' : 'bg-zinc-100'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Readiness Progress</span>
                    <span className="text-sm font-bold">{checklist.summary.percentage}%</span>
                  </div>
                  <div className="w-full bg-zinc-300 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${checklist.summary.is_ready ? 'bg-emerald-500' : 'bg-amber-500'}`}
                      style={{ width: `${checklist.summary.percentage}%` }}
                    />
                  </div>
                  <p className={`text-xs mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    {checklist.summary.completed} of {checklist.summary.total} items complete
                  </p>
                </div>

                {/* Checklist Items - mapped from backend response */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                  {Object.entries(checklist.checklist).map(([key, item]) => {
                    const iconMap = {
                      User: User,
                      Building2: Building2,
                      CreditCard: CreditCard,
                      Shield: Shield,
                      FileText: FileText,
                      Key: Key,
                      Mail: User
                    };
                    const IconComponent = iconMap[item.icon] || User;
                    
                    // Special handling for bank_verified to show verify button
                    if (key === 'bank_verified') {
                      return (
                        <div key={key} className="flex items-center gap-2">
                          <div className="flex-1">
                            <ChecklistItem 
                              label={item.label}
                              checked={item.completed}
                              icon={IconComponent}
                              itemKey={key}
                              employeeId={checklist.employee.id}
                            />
                          </div>
                          {canVerifyBank && checklist.checklist.bank_details?.completed && !item.completed && (
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
                      );
                    }
                    
                    return (
                      <ChecklistItem 
                        key={key}
                        label={item.label}
                        checked={item.completed}
                        icon={IconComponent}
                      />
                    );
                  })}
                </div>

                {/* Bank Validation & Documents Section */}
                <div className={`mb-6 p-4 rounded-lg border ${isDark ? 'bg-zinc-700/50 border-zinc-600' : 'bg-blue-50/50 border-blue-200'}`}>
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-blue-500" />
                    Bank Verification
                  </h3>
                  
                  {/* Validation Actions */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleValidateBankDetails(selectedEmployee.id)}
                      disabled={validating}
                      data-testid="validate-bank-btn"
                    >
                      {validating ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4 mr-2" />
                      )}
                      Validate IFSC & Account
                    </Button>
                    
                    {canUploadProof && (
                      <>
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFileUpload}
                          accept=".pdf,.jpg,.jpeg,.png,.webp"
                          className="hidden"
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleUploadClick}
                          disabled={uploading}
                          data-testid="upload-proof-btn"
                        >
                          {uploading ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Upload className="w-4 h-4 mr-2" />
                          )}
                          Upload Bank Proof
                        </Button>
                      </>
                    )}
                    
                    {bankProofs.length > 0 && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowBankProofsDialog(true)}
                        data-testid="view-proofs-btn"
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        View Documents ({bankProofs.length})
                      </Button>
                    )}
                  </div>

                  {/* Validation Results */}
                  {bankValidation && (
                    <div className={`p-3 rounded-lg ${
                      bankValidation.overall_valid 
                        ? isDark ? 'bg-emerald-900/30' : 'bg-emerald-50'
                        : isDark ? 'bg-red-900/30' : 'bg-red-50'
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        {bankValidation.overall_valid ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <XOctagon className="w-5 h-5 text-red-500" />
                        )}
                        <span className="font-medium">
                          {bankValidation.overall_valid ? 'Validation Passed' : 'Validation Issues Found'}
                        </span>
                      </div>
                      
                      {/* IFSC Validation */}
                      {bankValidation.ifsc_validation && (
                        <div className="text-sm mb-2">
                          <span className="font-medium">IFSC: </span>
                          {bankValidation.ifsc_validation.valid ? (
                            <span className="text-emerald-600">
                              ✓ Valid - {bankValidation.ifsc_validation.bank_name}
                              {bankValidation.ifsc_validation.branch && `, ${bankValidation.ifsc_validation.branch}`}
                            </span>
                          ) : (
                            <span className="text-red-600">
                              ✗ {bankValidation.ifsc_validation.error}
                            </span>
                          )}
                        </div>
                      )}
                      
                      {/* Account Validation */}
                      {bankValidation.account_validation && (
                        <div className="text-sm">
                          <span className="font-medium">Account: </span>
                          {bankValidation.account_validation.valid ? (
                            <span className="text-emerald-600">
                              ✓ Valid format ({bankValidation.account_validation.actual_length} digits)
                            </span>
                          ) : (
                            <span className="text-red-600">
                              ✗ {bankValidation.account_validation.error}
                            </span>
                          )}
                          {bankValidation.account_validation.warning && (
                            <p className="text-amber-600 text-xs mt-1">
                              ⚠ {bankValidation.account_validation.warning}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Bank Proofs Quick View */}
                  {bankProofs.length > 0 && (
                    <div className="mt-3 text-sm">
                      <span className={isDark ? 'text-zinc-400' : 'text-zinc-600'}>
                        Uploaded: {bankProofs.map(p => p.original_filename).join(', ')}
                      </span>
                    </div>
                  )}
                </div>

                {/* Go-Live Request Info */}
                {checklist.request && (
                  <div className={`p-4 rounded-lg mb-6 border ${
                    checklist.request.status === 'approved'
                      ? isDark ? 'bg-emerald-900/30 border-emerald-700' : 'bg-emerald-50 border-emerald-200'
                      : checklist.request.status === 'rejected'
                      ? isDark ? 'bg-red-900/30 border-red-700' : 'bg-red-50 border-red-200'
                      : isDark ? 'bg-amber-900/30 border-amber-700' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <h3 className="font-medium mb-1">Go-Live Request</h3>
                    <p className="text-sm">Status: <span className="capitalize font-medium">{checklist.request.status}</span></p>
                    <p className="text-sm">Submitted by: {checklist.request.submitted_by_name}</p>
                    {checklist.request.approved_by_name && (
                      <p className="text-sm">
                        {checklist.request.status === 'approved' ? 'Approved' : 'Rejected'} by: {checklist.request.approved_by_name}
                      </p>
                    )}
                    {checklist.request.rejection_reason && (
                      <p className="text-sm text-red-600">Reason: {checklist.request.rejection_reason}</p>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {(isHR || isAdmin) && checklist.employee.go_live_status === 'not_submitted' && (
                    <Button
                      className="bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => setShowSubmitDialog(true)}
                      disabled={!checklist.summary.is_ready}
                      data-testid="submit-golive-btn"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Submit for Go-Live Approval
                    </Button>
                  )}
                  {checklist.employee.go_live_status === 'active' && (
                    <div className="flex items-center gap-2 text-emerald-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Employee is LIVE!</span>
                    </div>
                  )}
                </div>

                {/* Warning if not ready */}
                {!checklist.summary.is_ready && (
                  <div className={`mt-4 p-3 rounded-lg flex items-start gap-2 ${
                    isDark ? 'bg-amber-900/30 border border-amber-700' : 'bg-amber-50 border border-amber-200'
                  }`}>
                    <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
                    <div>
                      <p className={`font-medium ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>Not Ready for Go-Live</p>
                      <p className={`text-sm ${isDark ? 'text-amber-300' : 'text-amber-600'}`}>
                        Complete all checklist items before submitting for approval.
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

      {/* Bank Proofs Dialog */}
      <Dialog open={showBankProofsDialog} onOpenChange={setShowBankProofsDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Bank Proof Documents</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {bankProofs.length === 0 ? (
              <p className="text-center text-zinc-500">No documents uploaded yet.</p>
            ) : (
              <div className="space-y-3">
                {bankProofs.map((doc) => (
                  <div
                    key={doc.id}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-8 h-8 text-blue-500" />
                      <div>
                        <p className="font-medium text-sm">{doc.original_filename}</p>
                        <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                          {formatFileSize(doc.file_size)} • Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}
                        </p>
                        <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                          By: {doc.uploaded_by_name}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownloadProof(selectedEmployee.id, doc.id, doc.original_filename)}
                        data-testid={`download-${doc.id}`}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      {(isAdmin || user?.role === 'hr_manager') && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-500 hover:text-red-600"
                          onClick={() => handleDeleteProof(selectedEmployee.id, doc.id)}
                          data-testid={`delete-${doc.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBankProofsDialog(false)}>Close</Button>
            {canUploadProof && (
              <Button onClick={handleUploadClick}>
                <Upload className="w-4 h-4 mr-2" />
                Upload More
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GoLiveDashboard;
