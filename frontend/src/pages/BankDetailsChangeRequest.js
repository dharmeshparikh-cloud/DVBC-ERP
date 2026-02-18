import React, { useState, useEffect, useContext, useRef } from 'react';
import { API, AuthContext } from '../App';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import {
  Building2, CreditCard, Upload, FileText, CheckCircle, XCircle,
  Clock, AlertCircle, Info, Trash2, Eye, Loader2, Shield, User, Search
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const BankDetailsChangeRequest = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const fileInputRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [verifyingIfsc, setVerifyingIfsc] = useState(false);
  const [ifscVerified, setIfscVerified] = useState(false);
  const [employee, setEmployee] = useState(null);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [formData, setFormData] = useState({
    account_holder_name: '',
    account_number: '',
    confirm_account_number: '',
    bank_name: '',
    ifsc_code: '',
    branch_name: '',
    reason: ''
  });
  const [proofFile, setProofFile] = useState(null);
  const [proofPreview, setProofPreview] = useState(null);

  useEffect(() => {
    fetchEmployeeData();
    fetchPendingRequests();
  }, []);

  // IFSC verification function
  const verifyIFSC = async (ifscCode) => {
    if (!ifscCode || ifscCode.length !== 11) return;
    
    const ifscPattern = /^[A-Z]{4}0[A-Z0-9]{6}$/;
    if (!ifscPattern.test(ifscCode.toUpperCase())) {
      toast.error('Invalid IFSC code format');
      return;
    }
    
    setVerifyingIfsc(true);
    try {
      // Using Razorpay's IFSC API (free, no auth required)
      const response = await axios.get(`https://ifsc.razorpay.com/${ifscCode.toUpperCase()}`);
      if (response.data) {
        setFormData(prev => ({
          ...prev,
          bank_name: response.data.BANK || prev.bank_name,
          branch_name: response.data.BRANCH || prev.branch_name,
          ifsc_code: ifscCode.toUpperCase()
        }));
        setIfscVerified(true);
        toast.success(`Verified: ${response.data.BANK} - ${response.data.BRANCH}`);
      }
    } catch (error) {
      setIfscVerified(false);
      if (error.response?.status === 404) {
        toast.error('Invalid IFSC code. Please check and try again.');
      } else {
        toast.error('Could not verify IFSC. Please enter bank details manually.');
      }
    } finally {
      setVerifyingIfsc(false);
    }
  };

  const fetchEmployeeData = async () => {
    try {
      const token = localStorage.getItem('token');
      // Get employee data linked to current user
      const response = await axios.get(`${API}/my/profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmployee(response.data);
      
      // Pre-fill form with existing bank details
      if (response.data?.bank_details) {
        const bd = response.data.bank_details;
        setFormData(prev => ({
          ...prev,
          account_holder_name: bd.account_holder_name || '',
          account_number: bd.account_number || '',
          confirm_account_number: bd.account_number || '',
          bank_name: bd.bank_name || '',
          ifsc_code: bd.ifsc_code || '',
          branch_name: bd.branch_name || ''
        }));
      }
    } catch (error) {
      console.error('Error fetching employee data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingRequests = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/my/bank-change-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPendingRequests(response.data || []);
    } catch (error) {
      console.error('Error fetching pending requests:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size must be less than 5MB');
        return;
      }
      
      setProofFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setProofPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeFile = () => {
    setProofFile(null);
    setProofPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validateForm = () => {
    if (!formData.account_holder_name.trim()) {
      toast.error('Account holder name is required');
      return false;
    }
    if (!formData.account_number.trim()) {
      toast.error('Account number is required');
      return false;
    }
    if (formData.account_number !== formData.confirm_account_number) {
      toast.error('Account numbers do not match');
      return false;
    }
    if (!formData.bank_name.trim()) {
      toast.error('Bank name is required');
      return false;
    }
    if (!formData.ifsc_code.trim()) {
      toast.error('IFSC code is required');
      return false;
    }
    if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(formData.ifsc_code.toUpperCase())) {
      toast.error('Invalid IFSC code format');
      return false;
    }
    if (!proofFile) {
      toast.error('Please upload a proof document (cancelled cheque or bank statement)');
      return false;
    }
    if (!formData.reason.trim()) {
      toast.error('Please provide a reason for the change');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      
      // Convert proof to base64
      const reader = new FileReader();
      reader.readAsDataURL(proofFile);
      reader.onloadend = async () => {
        const base64Proof = reader.result;
        
        const requestData = {
          new_bank_details: {
            account_holder_name: formData.account_holder_name,
            account_number: formData.account_number,
            bank_name: formData.bank_name,
            ifsc_code: formData.ifsc_code.toUpperCase(),
            branch_name: formData.branch_name
          },
          proof_document: base64Proof,
          proof_filename: proofFile.name,
          reason: formData.reason
        };
        
        await axios.post(
          `${API}/my/bank-change-request`,
          requestData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        toast.success('Bank details change request submitted successfully');
        fetchPendingRequests();
        
        // Reset form
        setProofFile(null);
        setProofPreview(null);
        setFormData(prev => ({ ...prev, reason: '' }));
        
        setSubmitting(false);
      };
    } catch (error) {
      console.error('Error submitting request:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit request');
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending_hr: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-400', label: 'Pending HR Approval' },
      pending_admin: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-400', label: 'Pending Admin Approval' },
      approved: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400', label: 'Approved' },
      rejected: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400', label: 'Rejected' }
    };
    const style = styles[status] || styles.pending_hr;
    return (
      <Badge className={`${style.bg} ${style.text}`}>
        {status === 'pending_hr' && <Clock className="w-3 h-3 mr-1" />}
        {status === 'pending_admin' && <Shield className="w-3 h-3 mr-1" />}
        {status === 'approved' && <CheckCircle className="w-3 h-3 mr-1" />}
        {status === 'rejected' && <XCircle className="w-3 h-3 mr-1" />}
        {style.label}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="bank-details-change-page">
      {/* Header */}
      <div>
        <h1 className={`text-xl md:text-2xl font-bold flex items-center gap-3 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          <Building2 className="w-6 h-6 md:w-7 md:h-7 text-orange-500" />
          Bank Details
        </h1>
        <p className={`text-sm md:text-base mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          View and request changes to your bank account details
        </p>
      </div>

      {/* Current Bank Details */}
      <Card className={isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200'}>
        <CardHeader className="pb-3">
          <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <CreditCard className="w-5 h-5 text-blue-500" />
            Current Bank Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          {employee?.bank_details?.account_number ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Account Holder</p>
                <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                  {employee.bank_details.account_holder_name || '-'}
                </p>
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Account Number</p>
                <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                  ****{employee.bank_details.account_number?.slice(-4) || '****'}
                </p>
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Bank Name</p>
                <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                  {employee.bank_details.bank_name || '-'}
                </p>
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>IFSC Code</p>
                <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                  {employee.bank_details.ifsc_code || '-'}
                </p>
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Branch</p>
                <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                  {employee.bank_details.branch_name || '-'}
                </p>
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Status</p>
                <Badge className="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Verified
                </Badge>
              </div>
            </div>
          ) : (
            <div className={`flex items-center gap-3 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
              <AlertCircle className="w-5 h-5 text-amber-500" />
              <p className={`text-sm ${isDark ? 'text-zinc-300' : 'text-zinc-600'}`}>
                No bank details on file. Please submit your bank details below.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Requests */}
      {pendingRequests.length > 0 && (
        <Card className={isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200'}>
          <CardHeader className="pb-3">
            <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
              <Clock className="w-5 h-5 text-amber-500" />
              Pending Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingRequests.map((req, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-200 bg-zinc-50'}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                        {req.new_bank_details?.bank_name} - ****{req.new_bank_details?.account_number?.slice(-4)}
                      </p>
                      <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                        Submitted: {new Date(req.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {getStatusBadge(req.status)}
                  </div>
                  {req.reason && (
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                      Reason: {req.reason}
                    </p>
                  )}
                  {req.rejection_reason && (
                    <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-sm text-red-700 dark:text-red-400">
                      Rejection reason: {req.rejection_reason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Request Change Form */}
      <Card className={isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200'}>
        <CardHeader>
          <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <FileText className="w-5 h-5 text-orange-500" />
            {employee?.bank_details?.account_number ? 'Request Bank Details Change' : 'Submit Bank Details'}
          </CardTitle>
          <CardDescription className={isDark ? 'text-zinc-400' : ''}>
            {employee?.bank_details?.account_number 
              ? 'Submit a request to update your bank account details. Requires HR and Admin approval.'
              : 'Submit your bank account details for salary payments.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Approval Flow Info */}
          <div className={`flex items-start gap-3 p-4 rounded-lg mb-6 ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
            <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className={`font-medium mb-1 ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>Approval Workflow</p>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className={isDark ? 'text-zinc-300' : 'text-zinc-600'}>You Submit</span>
                <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>→</span>
                <span className={isDark ? 'text-zinc-300' : 'text-zinc-600'}>HR Reviews</span>
                <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>→</span>
                <span className={isDark ? 'text-zinc-300' : 'text-zinc-600'}>Admin Approves</span>
                <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>→</span>
                <span className="text-green-600 dark:text-green-400 font-medium">Details Updated</span>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="account_holder_name">Account Holder Name *</Label>
                <Input
                  id="account_holder_name"
                  name="account_holder_name"
                  value={formData.account_holder_name}
                  onChange={handleInputChange}
                  placeholder="As per bank records"
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bank_name">Bank Name *</Label>
                <Input
                  id="bank_name"
                  name="bank_name"
                  value={formData.bank_name}
                  onChange={handleInputChange}
                  placeholder="e.g., HDFC Bank"
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="account_number">Account Number *</Label>
                <Input
                  id="account_number"
                  name="account_number"
                  value={formData.account_number}
                  onChange={handleInputChange}
                  placeholder="Enter account number"
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_account_number">Confirm Account Number *</Label>
                <Input
                  id="confirm_account_number"
                  name="confirm_account_number"
                  value={formData.confirm_account_number}
                  onChange={handleInputChange}
                  placeholder="Re-enter account number"
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ifsc_code">IFSC Code *</Label>
                <Input
                  id="ifsc_code"
                  name="ifsc_code"
                  value={formData.ifsc_code}
                  onChange={handleInputChange}
                  placeholder="e.g., HDFC0001234"
                  className={`uppercase ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="branch_name">Branch Name</Label>
                <Input
                  id="branch_name"
                  name="branch_name"
                  value={formData.branch_name}
                  onChange={handleInputChange}
                  placeholder="e.g., Koramangala"
                  className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                />
              </div>
            </div>

            {/* Proof Upload */}
            <div className="space-y-2">
              <Label>Proof Document * (Cancelled Cheque or Bank Statement)</Label>
              <div className={`border-2 border-dashed rounded-lg p-4 text-center ${
                isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-300 bg-zinc-50'
              }`}>
                {proofPreview ? (
                  <div className="space-y-3">
                    {proofFile?.type?.startsWith('image/') ? (
                      <img 
                        src={proofPreview} 
                        alt="Proof preview" 
                        className="max-h-40 mx-auto rounded-lg"
                      />
                    ) : (
                      <div className="flex items-center justify-center gap-2">
                        <FileText className="w-8 h-8 text-blue-500" />
                        <span className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>{proofFile?.name}</span>
                      </div>
                    )}
                    <Button 
                      type="button"
                      variant="outline" 
                      size="sm"
                      onClick={removeFile}
                      className="text-red-500 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Remove
                    </Button>
                  </div>
                ) : (
                  <div 
                    className="cursor-pointer py-4"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className={`w-8 h-8 mx-auto mb-2 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      Click to upload or drag and drop
                    </p>
                    <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                      PNG, JPG, PDF up to 5MB
                    </p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>
            </div>

            {/* Reason */}
            <div className="space-y-2">
              <Label htmlFor="reason">Reason for Change *</Label>
              <Textarea
                id="reason"
                name="reason"
                value={formData.reason}
                onChange={handleInputChange}
                placeholder="Explain why you need to change your bank details..."
                rows={3}
                className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
              />
            </div>

            <Button 
              type="submit" 
              disabled={submitting}
              className="w-full md:w-auto bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Submit Request
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default BankDetailsChangeRequest;
