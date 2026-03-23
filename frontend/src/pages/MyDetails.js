import React, { useState, useContext, useRef } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  User, Mail, Phone, MapPin, Building2, Briefcase, Calendar,
  CreditCard, Edit2, Save, X, Clock, CheckCircle, AlertCircle,
  FileText, Upload, Send, UserCog, Shield, Search, Loader2, Trash2, Eye,
  LogOut, Star, MessageSquare
} from 'lucide-react';
import MyWorkspaceNav from '../components/MyWorkspaceNav';

const MyDetails = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const fileInputRef = useRef(null);
  const queryClient = useQueryClient();

  const [saving, setSaving] = useState(false);
  
  // Edit states
  const [editSection, setEditSection] = useState(null);
  const [editData, setEditData] = useState({});
  const [changeReason, setChangeReason] = useState('');
  
  // Bank document upload states
  const [proofFile, setProofFile] = useState(null);
  const [proofPreview, setProofPreview] = useState(null);
  const [verifyingIfsc, setVerifyingIfsc] = useState(false);
  const [ifscVerified, setIfscVerified] = useState(false);

  // React Query: Profile
  const { data: profile, isLoading: loading } = useQuery({
    queryKey: ['my', 'profile'],
    queryFn: async () => {
      const res = await axios.get(`${API}/my/profile`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // React Query: Pending Requests
  const { data: pendingRequests = [] } = useQuery({
    queryKey: ['my', 'change-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/my/change-requests`);
      return res.data || [];
    },
    staleTime: 2 * 60 * 1000,
  });

  // Exit Organisation States
  const [showExitDialog, setShowExitDialog] = useState(false);
  const [exitStep, setExitStep] = useState(1); // 1: Confirm, 2: Interview, 3: Submit
  const [exitResponses, setExitResponses] = useState({});
  const [submittingExit, setSubmittingExit] = useState(false);

  // Query: Exit Interview Questions
  const { data: exitQuestions = [] } = useQuery({
    queryKey: ['exit', 'interview-questions'],
    queryFn: async () => {
      const res = await axios.get(`${API}/exit/interview-questions`);
      return res.data?.questions || [];
    },
    enabled: showExitDialog,
  });

  // Query: My Exit Request (if any)
  const { data: myExitRequest } = useQuery({
    queryKey: ['exit', 'my-request'],
    queryFn: async () => {
      const res = await axios.get(`${API}/exit/my-request`);
      return res.data?.request;
    },
    staleTime: 30 * 1000,
  });

  // Submit Exit Request Mutation
  const submitExitMutation = useMutation({
    mutationFn: async (data) => {
      return axios.post(`${API}/exit/initiate`, data);
    },
    onSuccess: (res) => {
      toast.success('Exit request submitted successfully');
      setShowExitDialog(false);
      setExitStep(1);
      setExitResponses({});
      queryClient.invalidateQueries({ queryKey: ['exit', 'my-request'] });
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to submit exit request');
    },
  });

  const handleExitSubmit = async () => {
    // Validate all required questions answered
    const requiredQuestions = exitQuestions.filter(q => q.type !== 'text');
    for (const q of requiredQuestions) {
      if (!exitResponses[q.id]) {
        toast.error(`Please answer: ${q.question}`);
        return;
      }
    }
    
    setSubmittingExit(true);
    try {
      await submitExitMutation.mutateAsync({
        interview_responses: exitResponses
      });
    } finally {
      setSubmittingExit(false);
    }
  };

  const openEditDialog = (section, data) => {
    setEditSection(section);
    setEditData({ ...data });
    setChangeReason('');
  };

  const closeEditDialog = () => {
    setEditSection(null);
    setEditData({});
    setChangeReason('');
    setProofFile(null);
    setProofPreview(null);
    setIfscVerified(false);
  };

  // IFSC Verification
  const verifyIfsc = async (ifscCode) => {
    if (!ifscCode || ifscCode.length !== 11) return;
    
    const ifscPattern = /^[A-Z]{4}0[A-Z0-9]{6}$/;
    if (!ifscPattern.test(ifscCode.toUpperCase())) {
      toast.error('Invalid IFSC code format');
      return;
    }
    
    setVerifyingIfsc(true);
    try {
      const response = await axios.get(`https://ifsc.razorpay.com/${ifscCode.toUpperCase()}`);
      if (response.data) {
        setEditData(prev => ({
          ...prev,
          bank_name: response.data.BANK || prev.bank_name,
          branch: response.data.BRANCH || prev.branch,
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

  // Handle bank proof file
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size must be less than 5MB');
        return;
      }
      setProofFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setProofPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const removeFile = () => {
    setProofFile(null);
    setProofPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const submitChangeRequest = async () => {
    if (!changeReason.trim()) {
      toast.error('Please provide a reason for the change');
      return;
    }

    // Bank section requires proof document
    if (editSection === 'bank' && !proofFile) {
      toast.error('Please upload a cancelled cheque or bank statement as proof');
      return;
    }

    setSaving(true);
    try {
      let requestData = {
        section: editSection,
        changes: editData,
        reason: changeReason
      };

      // If bank section, include proof document
      if (editSection === 'bank' && proofFile) {
        const reader = new FileReader();
        reader.readAsDataURL(proofFile);
        await new Promise((resolve) => {
          reader.onloadend = async () => {
            requestData.proof_document = reader.result;
            requestData.proof_filename = proofFile.name;
            resolve();
          };
        });
      }

      await axios.post(`${API}/my/change-request`, requestData);
      toast.success('Change request submitted for HR approval');
      closeEditDialog();
      queryClient.invalidateQueries({ queryKey: ['my', 'change-requests'] });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit change request');
    } finally {
      setSaving(false);
    }
  };

  const getSectionIcon = (section) => {
    switch (section) {
      case 'personal': return User;
      case 'contact': return Phone;
      case 'address': return MapPin;
      case 'bank': return CreditCard;
      case 'emergency': return Shield;
      default: return FileText;
    }
  };

  const hasPendingRequest = (section) => {
    return pendingRequests.some(r => r.section === section && r.status === 'pending');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
        <p className="text-zinc-500">Unable to load profile</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`} data-testid="my-details-page">
      <MyWorkspaceNav />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="my-details-title">
            <UserCog className="w-6 h-6 text-orange-500" />
            My Details
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            View and request changes to your profile information
          </p>
        </div>
      </div>

      {/* Pending Requests Banner */}
      {pendingRequests.length > 0 && (
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-amber-900/20 border-amber-700' : 'bg-amber-50 border-amber-200'}`} data-testid="pending-requests-banner">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-amber-500" />
            <span className={`font-medium ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
              Pending Change Requests
            </span>
          </div>
          <div className="space-y-2">
            {pendingRequests.filter(r => r.status === 'pending').map(req => {
              const Icon = getSectionIcon(req.section);
              return (
                <div key={req.id} className={`flex items-center gap-2 text-sm ${isDark ? 'text-amber-200' : 'text-amber-600'}`} data-testid={`pending-request-${req.id}`}>
                  <Icon className="w-4 h-4" />
                  <span className="capitalize">{req.section.replace('_', ' ')}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-amber-200 text-amber-800">
                    Awaiting HR Approval
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="details-grid">
        {/* Personal Information */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="w-5 h-5 text-blue-500" />
                Personal Information
              </CardTitle>
              <CardDescription>Basic personal details (Read-only)</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Full Name</Label>
                <p className="font-medium">{profile.first_name} {profile.last_name}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Employee ID</Label>
                <p className="font-medium">{profile.employee_id}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Date of Birth</Label>
                <p className="font-medium">{profile.date_of_birth || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Gender</Label>
                <p className="font-medium capitalize">{profile.gender || 'Not set'}</p>
              </div>
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              To change personal details, contact HR directly.
            </p>
          </CardContent>
        </Card>

        {/* Contact Information */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Phone className="w-5 h-5 text-green-500" />
                Contact Information
              </CardTitle>
              <CardDescription>Phone and email details</CardDescription>
            </div>
            {!hasPendingRequest('contact') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('contact', {
                  personal_email: profile.personal_email,
                  phone: profile.phone,
                  alternate_phone: profile.alternate_phone
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Work Email</Label>
                <p className="font-medium">{profile.email}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Personal Email</Label>
                <p className="font-medium">{profile.personal_email || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{profile.phone || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Alternate Phone</Label>
                <p className="font-medium">{profile.alternate_phone || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('contact') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Address */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MapPin className="w-5 h-5 text-red-500" />
                Address
              </CardTitle>
              <CardDescription>Current and permanent address</CardDescription>
            </div>
            {!hasPendingRequest('address') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('address', {
                  current_address: profile.current_address || '',
                  permanent_address: profile.permanent_address || '',
                  city: profile.city || '',
                  state: profile.state || '',
                  pincode: profile.pincode || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs text-zinc-500">Current Address</Label>
              <p className="font-medium">{profile.current_address || 'Not set'}</p>
            </div>
            <div>
              <Label className="text-xs text-zinc-500">Permanent Address</Label>
              <p className="font-medium">{profile.permanent_address || 'Not set'}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">City</Label>
                <p className="font-medium">{profile.city || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">State</Label>
                <p className="font-medium">{profile.state || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Pincode</Label>
                <p className="font-medium">{profile.pincode || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('address') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Bank Details */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <CreditCard className="w-5 h-5 text-purple-500" />
                Bank Details
              </CardTitle>
              <CardDescription>Salary account information</CardDescription>
            </div>
            {!hasPendingRequest('bank') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('bank', {
                  bank_name: profile.bank_name || profile.bank_details?.bank_name || '',
                  account_number: profile.account_number || profile.bank_details?.account_number || '',
                  ifsc_code: profile.ifsc_code || profile.bank_details?.ifsc_code || '',
                  branch: profile.bank_branch || profile.bank_details?.branch || profile.bank_details?.branch_name || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Bank Name</Label>
                <p className="font-medium">{profile.bank_name || profile.bank_details?.bank_name || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Branch</Label>
                <p className="font-medium">{profile.bank_branch || profile.bank_details?.branch || profile.bank_details?.branch_name || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Account Number</Label>
                <p className="font-medium">
                  {(profile.account_number || profile.bank_details?.account_number)
                    ? `****${(profile.account_number || profile.bank_details?.account_number).slice(-4)}` 
                    : 'Not set'
                  }
                </p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">IFSC Code</Label>
                <p className="font-medium">{profile.ifsc_code || profile.bank_details?.ifsc_code || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('bank') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Emergency Contact */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className="w-5 h-5 text-orange-500" />
                Emergency Contact
              </CardTitle>
              <CardDescription>Emergency contact details</CardDescription>
            </div>
            {!hasPendingRequest('emergency') && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openEditDialog('emergency', {
                  emergency_contact_name: profile.emergency_contact_name || '',
                  emergency_contact_phone: profile.emergency_contact_phone || '',
                  emergency_contact_relation: profile.emergency_contact_relation || ''
                })}
              >
                <Edit2 className="w-4 h-4 mr-1" /> Edit
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Contact Name</Label>
                <p className="font-medium">{profile.emergency_contact_name || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Relation</Label>
                <p className="font-medium capitalize">{profile.emergency_contact_relation || 'Not set'}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{profile.emergency_contact_phone || 'Not set'}</p>
              </div>
            </div>
            {hasPendingRequest('emergency') && (
              <p className="text-xs text-amber-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Change request pending approval
              </p>
            )}
          </CardContent>
        </Card>

        {/* Employment Information (Read-only) */}
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="w-5 h-5 text-teal-500" />
              Employment Information
            </CardTitle>
            <CardDescription>Job details (Read-only)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-zinc-500">Department</Label>
                <p className="font-medium">{profile.department || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Designation</Label>
                <p className="font-medium">{profile.designation || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Date of Joining</Label>
                <p className="font-medium">{profile.date_of_joining || 'Not set'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Reporting Manager</Label>
                <p className="font-medium">{profile.reporting_manager_name || 'Not set'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Exit Organisation Section */}
      <Card className={`${isDark ? 'bg-zinc-800 border-zinc-700' : ''} border-red-200`}>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <LogOut className="w-5 h-5 text-red-500" />
            Exit Organisation
          </CardTitle>
          <CardDescription>Initiate resignation process</CardDescription>
        </CardHeader>
        <CardContent>
          {myExitRequest ? (
            <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-amber-500" />
                <span className="font-medium">Exit Request Status: {myExitRequest.status?.replace('_', ' ').toUpperCase()}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <Label className="text-xs text-zinc-500">Resignation Date</Label>
                  <p>{myExitRequest.resignation_date ? new Date(myExitRequest.resignation_date).toLocaleDateString() : 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Last Working Day</Label>
                  <p>{myExitRequest.last_working_day ? new Date(myExitRequest.last_working_day).toLocaleDateString() : 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Reason</Label>
                  <p className="capitalize">{myExitRequest.reason?.replace('_', ' ') || 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Notice Period</Label>
                  <p>{myExitRequest.notice_period_days || 30} days</p>
                </div>
              </div>
              {myExitRequest.status === 'pending' && (
                <p className="text-xs text-amber-600 mt-3 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Waiting for Admin approval
                </p>
              )}
              {myExitRequest.status === 'admin_approved' && (
                <p className="text-xs text-blue-600 mt-3 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Admin approved. Waiting for HR approval
                </p>
              )}
              {myExitRequest.status === 'hr_approved' && (
                <p className="text-xs text-green-600 mt-3 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Approved. Notice period in progress
                </p>
              )}
            </div>
          ) : (
            <div>
              <p className={`text-sm mb-4 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                If you wish to resign from your position, you can initiate the exit process here. 
                This will start a 30-day notice period after approval.
              </p>
              <Button 
                variant="destructive"
                onClick={() => setShowExitDialog(true)}
                data-testid="exit-organisation-btn"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Exit Organisation
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exit Organisation Dialog */}
      <Dialog open={showExitDialog} onOpenChange={setShowExitDialog}>
        <DialogContent className={`max-w-2xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <LogOut className="w-5 h-5" />
              Exit Organisation - Step {exitStep} of 3
            </DialogTitle>
            <DialogDescription>
              {exitStep === 1 && "Please confirm you want to initiate the resignation process."}
              {exitStep === 2 && "Complete the mandatory exit interview questions."}
              {exitStep === 3 && "Review and submit your exit request."}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            {/* Step 1: Confirmation */}
            {exitStep === 1 && (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg border ${isDark ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'}`}>
                  <h4 className="font-medium text-red-600 mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Important Information
                  </h4>
                  <ul className={`text-sm space-y-2 ${isDark ? 'text-zinc-300' : 'text-zinc-600'}`}>
                    <li>• This will initiate a <strong>30-day notice period</strong> after approval.</li>
                    <li>• Your resignation will require <strong>Admin and HR approval</strong>.</li>
                    <li>• During the notice period, certain <strong>downloads will be restricted</strong>.</li>
                    <li>• You will need to complete an <strong>exit interview</strong> and handover process.</li>
                    <li>• Final & Full Settlement (F&F) will be calculated after all clearances.</li>
                  </ul>
                </div>
                <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-100'}`}>
                  <p className="text-sm">
                    By proceeding, you confirm that you understand the above and wish to resign from your position at {profile?.department || 'the organization'}.
                  </p>
                </div>
              </div>
            )}

            {/* Step 2: Exit Interview */}
            {exitStep === 2 && (
              <div className="space-y-4">
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                  Please answer the following questions honestly. Your feedback helps us improve.
                </p>
                {exitQuestions.map((q) => (
                  <div key={q.id} className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                    <Label className="font-medium flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-orange-500" />
                      {q.question}
                      {q.type !== 'text' && <span className="text-red-500">*</span>}
                    </Label>
                    
                    {q.type === 'select' && (
                      <Select
                        value={exitResponses[q.id] || ''}
                        onValueChange={(val) => setExitResponses({...exitResponses, [q.id]: val})}
                      >
                        <SelectTrigger className="mt-2">
                          <SelectValue placeholder="Select an option" />
                        </SelectTrigger>
                        <SelectContent>
                          {q.options.map(opt => (
                            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    
                    {q.type === 'rating' && (
                      <div className="flex gap-2 mt-2">
                        {[1, 2, 3, 4, 5].map(num => (
                          <button
                            key={num}
                            type="button"
                            onClick={() => setExitResponses({...exitResponses, [q.id]: num})}
                            className={`w-10 h-10 rounded-full border-2 flex items-center justify-center transition-colors
                              ${exitResponses[q.id] >= num 
                                ? 'bg-orange-500 border-orange-500 text-white' 
                                : isDark ? 'border-zinc-600 text-zinc-400' : 'border-zinc-300 text-zinc-500'
                              }`}
                          >
                            {num <= (exitResponses[q.id] || 0) ? (
                              <Star className="w-5 h-5 fill-current" />
                            ) : (
                              <Star className="w-5 h-5" />
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                    
                    {q.type === 'text' && (
                      <Textarea
                        className="mt-2"
                        placeholder="Your feedback (optional)"
                        value={exitResponses[q.id] || ''}
                        onChange={(e) => setExitResponses({...exitResponses, [q.id]: e.target.value})}
                        rows={3}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Step 3: Review & Submit */}
            {exitStep === 3 && (
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <h4 className="font-medium mb-3">Review Your Exit Request</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <Label className="text-xs text-zinc-500">Employee</Label>
                      <p>{profile?.first_name} {profile?.last_name} ({profile?.employee_id})</p>
                    </div>
                    <div>
                      <Label className="text-xs text-zinc-500">Department</Label>
                      <p>{profile?.department || 'N/A'}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-zinc-500">Primary Reason</Label>
                      <p className="capitalize">{exitResponses['reason']?.replace('_', ' ') || 'Not selected'}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-zinc-500">Notice Period</Label>
                      <p>30 days</p>
                    </div>
                  </div>
                </div>
                
                <div className={`p-3 rounded-lg border ${isDark ? 'bg-amber-900/20 border-amber-700' : 'bg-amber-50 border-amber-200'}`}>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    By submitting, your resignation request will be sent for Admin approval, followed by HR approval. 
                    You will be notified of the status updates.
                  </p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="flex gap-2">
            {exitStep > 1 && (
              <Button variant="outline" onClick={() => setExitStep(exitStep - 1)}>
                Back
              </Button>
            )}
            <Button variant="outline" onClick={() => { setShowExitDialog(false); setExitStep(1); setExitResponses({}); }}>
              Cancel
            </Button>
            
            {exitStep < 3 ? (
              <Button 
                onClick={() => setExitStep(exitStep + 1)}
                className="bg-orange-500 hover:bg-orange-600"
              >
                Continue
              </Button>
            ) : (
              <Button 
                onClick={handleExitSubmit}
                disabled={submittingExit}
                className="bg-red-600 hover:bg-red-700"
                data-testid="submit-exit-request-btn"
              >
                {submittingExit ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Submit Exit Request
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editSection} onOpenChange={() => closeEditDialog()}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editSection && React.createElement(getSectionIcon(editSection), { className: 'w-5 h-5 text-orange-500' })}
              Edit {editSection?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </DialogTitle>
            <DialogDescription>
              Your changes will be submitted for HR approval
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Contact Section */}
            {editSection === 'contact' && (
              <>
                <div>
                  <Label>Personal Email</Label>
                  <Input
                    type="email"
                    value={editData.personal_email || ''}
                    onChange={e => setEditData({...editData, personal_email: e.target.value})}
                    placeholder="personal@email.com"
                  />
                </div>
                <div>
                  <Label>Phone Number</Label>
                  <Input
                    value={editData.phone || ''}
                    onChange={e => setEditData({...editData, phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
                <div>
                  <Label>Alternate Phone</Label>
                  <Input
                    value={editData.alternate_phone || ''}
                    onChange={e => setEditData({...editData, alternate_phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
              </>
            )}

            {/* Address Section */}
            {editSection === 'address' && (
              <>
                <div>
                  <Label>Current Address</Label>
                  <Textarea
                    value={editData.current_address || ''}
                    onChange={e => setEditData({...editData, current_address: e.target.value})}
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Permanent Address</Label>
                  <Textarea
                    value={editData.permanent_address || ''}
                    onChange={e => setEditData({...editData, permanent_address: e.target.value})}
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label>City</Label>
                    <Input
                      value={editData.city || ''}
                      onChange={e => setEditData({...editData, city: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>State</Label>
                    <Input
                      value={editData.state || ''}
                      onChange={e => setEditData({...editData, state: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Pincode</Label>
                    <Input
                      value={editData.pincode || ''}
                      onChange={e => setEditData({...editData, pincode: e.target.value})}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Bank Section */}
            {editSection === 'bank' && (
              <>
                <div className={`p-3 rounded-lg mb-2 ${isDark ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
                  <p className="text-xs text-blue-600 dark:text-blue-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    Bank changes require proof document (cancelled cheque / bank statement)
                  </p>
                </div>
                
                <div>
                  <Label>IFSC Code</Label>
                  <div className="flex gap-2">
                    <Input
                      value={editData.ifsc_code || ''}
                      onChange={e => setEditData({...editData, ifsc_code: e.target.value.toUpperCase()})}
                      placeholder="HDFC0001234"
                      maxLength={11}
                      className="flex-1"
                    />
                    <Button 
                      type="button"
                      variant="outline" 
                      size="sm"
                      onClick={() => verifyIfsc(editData.ifsc_code)}
                      disabled={verifyingIfsc || !editData.ifsc_code || editData.ifsc_code.length !== 11}
                    >
                      {verifyingIfsc ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      {verifyingIfsc ? 'Verifying' : 'Verify'}
                    </Button>
                  </div>
                  {ifscVerified && (
                    <p className="text-xs text-emerald-600 mt-1 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> IFSC Verified
                    </p>
                  )}
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Bank Name</Label>
                    <Input
                      value={editData.bank_name || ''}
                      onChange={e => setEditData({...editData, bank_name: e.target.value})}
                      placeholder="HDFC Bank"
                    />
                  </div>
                  <div>
                    <Label>Branch</Label>
                    <Input
                      value={editData.branch || ''}
                      onChange={e => setEditData({...editData, branch: e.target.value})}
                      placeholder="Mumbai Main Branch"
                    />
                  </div>
                </div>
                
                <div>
                  <Label>Account Number</Label>
                  <Input
                    value={editData.account_number || ''}
                    onChange={e => setEditData({...editData, account_number: e.target.value})}
                    placeholder="1234567890123"
                  />
                </div>
                
                <div>
                  <Label>Confirm Account Number</Label>
                  <Input
                    value={editData.confirm_account_number || ''}
                    onChange={e => setEditData({...editData, confirm_account_number: e.target.value})}
                    placeholder="Re-enter account number"
                  />
                  {editData.account_number && editData.confirm_account_number && 
                   editData.account_number !== editData.confirm_account_number && (
                    <p className="text-xs text-red-500 mt-1">Account numbers do not match</p>
                  )}
                </div>

                {/* Proof Document Upload */}
                <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <Label className="text-orange-600 flex items-center gap-1 mb-2">
                    <Upload className="w-4 h-4" /> Proof Document *
                  </Label>
                  <p className="text-xs text-zinc-500 mb-2">Upload cancelled cheque or bank statement (Max 5MB)</p>
                  
                  {!proofFile ? (
                    <div
                      className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors
                        ${isDark ? 'border-zinc-700 hover:border-zinc-500' : 'border-zinc-300 hover:border-zinc-400'}`}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="w-8 h-8 mx-auto mb-2 text-zinc-400" />
                      <p className="text-sm text-zinc-500">Click to upload</p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*,.pdf"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                    </div>
                  ) : (
                    <div className={`relative rounded-lg overflow-hidden border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      {proofPreview && proofFile.type.startsWith('image/') ? (
                        <img src={proofPreview} alt="Proof" className="w-full h-32 object-cover" />
                      ) : (
                        <div className="p-4 flex items-center gap-3">
                          <FileText className="w-8 h-8 text-orange-500" />
                          <span className="text-sm truncate">{proofFile.name}</span>
                        </div>
                      )}
                      <div className="absolute top-2 right-2 flex gap-1">
                        {proofPreview && proofFile.type.startsWith('image/') && (
                          <Button size="sm" variant="secondary" onClick={() => window.open(proofPreview, '_blank')}>
                            <Eye className="w-3 h-3" />
                          </Button>
                        )}
                        <Button size="sm" variant="destructive" onClick={removeFile}>
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Emergency Contact Section */}
            {editSection === 'emergency' && (
              <>
                <div>
                  <Label>Contact Name</Label>
                  <Input
                    value={editData.emergency_contact_name || ''}
                    onChange={e => setEditData({...editData, emergency_contact_name: e.target.value})}
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <Label>Relation</Label>
                  <Input
                    value={editData.emergency_contact_relation || ''}
                    onChange={e => setEditData({...editData, emergency_contact_relation: e.target.value})}
                    placeholder="Spouse / Parent / Sibling"
                  />
                </div>
                <div>
                  <Label>Phone Number</Label>
                  <Input
                    value={editData.emergency_contact_phone || ''}
                    onChange={e => setEditData({...editData, emergency_contact_phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>
              </>
            )}

            {/* Reason for change */}
            <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
              <Label className="text-orange-600">Reason for Change *</Label>
              <Textarea
                value={changeReason}
                onChange={e => setChangeReason(e.target.value)}
                placeholder="Please provide a reason for this change request..."
                rows={2}
                className="mt-2"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog}>
              Cancel
            </Button>
            <Button 
              onClick={submitChangeRequest}
              disabled={saving}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {saving ? 'Submitting...' : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit for Approval
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyDetails;
