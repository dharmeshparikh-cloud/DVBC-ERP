import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Checkbox } from '../../components/ui/checkbox';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Separator } from '../../components/ui/separator';
import { 
  ArrowLeft, User, GraduationCap, Briefcase, Building2, Phone, FileText,
  CheckCircle2, XCircle, AlertTriangle, Loader2, Download, ExternalLink,
  Calendar, Mail, Shield, CreditCard, Clock, Send, Edit, Check
} from 'lucide-react';
import { toast } from 'sonner';

const DEPARTMENTS = ['Sales', 'HR', 'Consulting', 'Finance', 'Admin', 'Operations'];
const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
  { value: 'part_time', label: 'Part Time' },
];

const SubmissionReview = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [submission, setSubmission] = useState(null);
  const [managers, setManagers] = useState([]);
  const [processing, setProcessing] = useState(false);
  
  // HR Assignment form
  const [hrAssignment, setHrAssignment] = useState({
    department: '',
    reporting_manager_id: '',
    reporting_manager_name: '',
    joining_date: '',
    official_email: '',
    employment_type: 'full_time',
    designation: '',
  });
  
  // Dialogs
  const [showRevisionDialog, setShowRevisionDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);
  const [revisionReason, setRevisionReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');

  // Get token from localStorage (same as App.js pattern)
  const getToken = () => localStorage.getItem('token');
  const authHeaders = { headers: { Authorization: `Bearer ${getToken()}` } };
  const canApprove = user?.role === 'hr_manager' || user?.role === 'admin';

  // Fetch submission
  const fetchSubmission = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/onboarding/submissions/${submissionId}`, authHeaders);
      setSubmission(response.data);
      
      // Pre-fill HR assignment form
      if (response.data.hr_assigned) {
        setHrAssignment({
          department: response.data.hr_assigned.department || '',
          reporting_manager_id: response.data.hr_assigned.reporting_manager_id || '',
          reporting_manager_name: response.data.hr_assigned.reporting_manager_name || '',
          joining_date: response.data.hr_assigned.joining_date || '',
          official_email: response.data.hr_assigned.official_email || '',
          employment_type: response.data.hr_assigned.employment_type || 'full_time',
          designation: response.data.hr_assigned.designation || response.data.offered_position || '',
        });
      } else if (response.data.offered_position) {
        setHrAssignment(prev => ({ ...prev, designation: response.data.offered_position }));
      }
    } catch (err) {
      console.error('Error fetching submission:', err);
      toast.error('Failed to load submission');
      navigate('/onboarding-hub');
    } finally {
      setLoading(false);
    }
  };

  // Fetch managers for dropdown
  const fetchManagers = async () => {
    try {
      const response = await axios.get(`${API}/employees/all`, authHeaders);
      const employees = response.data?.items || response.data || [];
      setManagers(employees.filter(e => 
        ['manager', 'hr_manager', 'project_manager', 'principal_consultant', 'senior_consultant', 'admin'].includes(e.role)
      ));
    } catch (err) {
      console.error('Error fetching managers:', err);
    }
  };

  useEffect(() => {
    if (token && submissionId) {
      fetchSubmission();
      fetchManagers();
    }
  }, [submissionId, token]);

  // Save HR assignment
  const handleSaveAssignment = async () => {
    try {
      setProcessing(true);
      await axios.patch(`${API}/onboarding/submissions/${submissionId}/hr-assign`, hrAssignment, authHeaders);
      toast.success('Assignment details saved');
      fetchSubmission();
    } catch (err) {
      console.error('Error saving assignment:', err);
      toast.error(err.response?.data?.detail || 'Failed to save assignment');
    } finally {
      setProcessing(false);
    }
  };

  // Verify documents
  const handleVerifyDocuments = async () => {
    try {
      setProcessing(true);
      await axios.post(`${API}/onboarding/submissions/${submissionId}/verify-documents`, {}, authHeaders);
      toast.success('Documents verified');
      fetchSubmission();
    } catch (err) {
      console.error('Error verifying documents:', err);
      toast.error(err.response?.data?.detail || 'Failed to verify documents');
    } finally {
      setProcessing(false);
    }
  };

  // Verify bank
  const handleVerifyBank = async () => {
    try {
      setProcessing(true);
      await axios.post(`${API}/onboarding/submissions/${submissionId}/verify-bank`, {}, authHeaders);
      toast.success('Bank details verified');
      fetchSubmission();
    } catch (err) {
      console.error('Error verifying bank:', err);
      toast.error(err.response?.data?.detail || 'Failed to verify bank details');
    } finally {
      setProcessing(false);
    }
  };

  // Request revision
  const handleRequestRevision = async () => {
    if (!revisionReason.trim()) {
      toast.error('Please provide a reason for revision');
      return;
    }
    try {
      setProcessing(true);
      await axios.post(`${API}/onboarding/submissions/${submissionId}/request-revision`, 
        { reason: revisionReason }, authHeaders);
      toast.success('Revision request sent to candidate');
      setShowRevisionDialog(false);
      setRevisionReason('');
      fetchSubmission();
    } catch (err) {
      console.error('Error requesting revision:', err);
      toast.error(err.response?.data?.detail || 'Failed to request revision');
    } finally {
      setProcessing(false);
    }
  };

  // Reject submission
  const handleReject = async () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    try {
      setProcessing(true);
      await axios.post(`${API}/onboarding/submissions/${submissionId}/reject`, 
        { reason: rejectReason }, authHeaders);
      toast.success('Submission rejected');
      setShowRejectDialog(false);
      setRejectReason('');
      fetchSubmission();
    } catch (err) {
      console.error('Error rejecting submission:', err);
      toast.error(err.response?.data?.detail || 'Failed to reject submission');
    } finally {
      setProcessing(false);
    }
  };

  // Complete onboarding
  const handleComplete = async () => {
    try {
      setProcessing(true);
      const response = await axios.post(`${API}/onboarding/submissions/${submissionId}/complete`, {}, authHeaders);
      toast.success(`Onboarding complete! Employee ID: ${response.data.employee_id}`);
      setShowCompleteDialog(false);
      fetchSubmission();
    } catch (err) {
      console.error('Error completing onboarding:', err);
      toast.error(err.response?.data?.detail || 'Failed to complete onboarding');
    } finally {
      setProcessing(false);
    }
  };

  // Check readiness
  const checkReadiness = () => {
    const errors = [];
    const hv = submission?.hr_verification || {};
    const ha = submission?.hr_assigned || {};
    
    if (!ha.department) errors.push('Department not assigned');
    if (!ha.reporting_manager_id) errors.push('Reporting manager not assigned');
    if (!ha.joining_date) errors.push('Joining date not set');
    if (!ha.official_email) errors.push('Official email not assigned');
    if (!hv.documents_verified) errors.push('Documents not verified');
    if (!hv.bank_verified) errors.push('Bank details not verified');
    if ((submission?.documents?.length || 0) < 2) errors.push('Minimum 2 documents required');
    
    return errors;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!submission) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
        <p>Submission not found</p>
      </div>
    );
  }

  const cd = submission.candidate_details || {};
  const bd = submission.bank_details || {};
  const ec = submission.emergency_contact || {};
  const hv = submission.hr_verification || {};
  const readinessErrors = checkReadiness();
  const isReady = readinessErrors.length === 0 && submission.status === 'submitted';

  const getStatusBadge = (status) => {
    const config = {
      invited: { color: 'bg-blue-100 text-blue-700', label: 'Invited' },
      draft: { color: 'bg-zinc-100 text-zinc-700', label: 'In Progress' },
      submitted: { color: 'bg-amber-100 text-amber-700', label: 'Pending Review' },
      revision_requested: { color: 'bg-orange-100 text-orange-700', label: 'Revision Requested' },
      completed: { color: 'bg-green-100 text-green-700', label: 'Completed' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected' },
    };
    const c = config[status] || { color: 'bg-zinc-100', label: status };
    return <Badge className={c.color}>{c.label}</Badge>;
  };

  return (
    <div className="space-y-6" data-testid="submission-review">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/onboarding-hub')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{submission.candidate_name}</h1>
            <p className="text-zinc-500 text-sm flex items-center gap-2">
              {submission.offered_position}
              {getStatusBadge(submission.status)}
            </p>
          </div>
        </div>
        {submission.employee_id_generated && (
          <Badge className="bg-green-100 text-green-700 text-lg px-4 py-2">
            Employee ID: {submission.employee_id_generated}
          </Badge>
        )}
      </div>

      {/* Completed Alert */}
      {submission.status === 'completed' && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            Onboarding completed on {new Date(submission.completed_at).toLocaleDateString()}.
            Employee ID <strong>{submission.employee_id_generated}</strong> has been generated.
          </AlertDescription>
        </Alert>
      )}

      {/* Rejected Alert */}
      {submission.status === 'rejected' && (
        <Alert className="border-red-200 bg-red-50">
          <XCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            This submission was rejected. Reason: {submission.rejection_reason}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Candidate Data */}
        <div className="lg:col-span-2 space-y-6">
          {/* Personal Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="w-4 h-4" />
                Personal Details
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-zinc-500">Full Name</Label>
                <p className="font-medium">{cd.first_name} {cd.last_name}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Date of Birth</Label>
                <p className="font-medium">{cd.date_of_birth || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{cd.phone || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Email</Label>
                <p className="font-medium">{submission.candidate_email}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Gender</Label>
                <p className="font-medium capitalize">{cd.gender || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Blood Group</Label>
                <p className="font-medium">{cd.blood_group || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">PAN Number</Label>
                <p className="font-medium font-mono">{cd.pan_number || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Aadhaar Number</Label>
                <p className="font-medium font-mono">{cd.aadhaar_number || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Current Address</Label>
                <p className="font-medium">
                  {cd.current_address?.street}, {cd.current_address?.city}, {cd.current_address?.state} - {cd.current_address?.pincode}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Education */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <GraduationCap className="w-4 h-4" />
                Education ({submission.education?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {submission.education?.length > 0 ? (
                <div className="space-y-3">
                  {submission.education.map((edu, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg">
                      <div>
                        <p className="font-medium">{edu.degree}</p>
                        <p className="text-sm text-zinc-500">{edu.institution}</p>
                      </div>
                      <div className="text-right text-sm">
                        <p>{edu.year}</p>
                        <p className="text-zinc-500">{edu.percentage}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500 text-sm">No education details provided</p>
              )}
            </CardContent>
          </Card>

          {/* Work Experience */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Briefcase className="w-4 h-4" />
                Work Experience ({submission.employment_history?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {submission.employment_history?.length > 0 ? (
                <div className="space-y-3">
                  {submission.employment_history.map((emp, i) => (
                    <div key={i} className="p-3 bg-zinc-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <p className="font-medium">{emp.designation}</p>
                        <p className="text-sm text-zinc-500">{emp.from_date} - {emp.to_date || 'Present'}</p>
                      </div>
                      <p className="text-sm text-zinc-500">{emp.company}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500 text-sm">Fresher - No work experience</p>
              )}
            </CardContent>
          </Card>

          {/* Bank Details */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <CreditCard className="w-4 h-4" />
                Bank Details
              </CardTitle>
              {hv.bank_verified ? (
                <Badge className="bg-green-100 text-green-700">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Verified
                </Badge>
              ) : canApprove && submission.status === 'submitted' ? (
                <Button size="sm" onClick={handleVerifyBank} disabled={processing}>
                  Verify Bank
                </Button>
              ) : null}
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-zinc-500">Account Holder</Label>
                <p className="font-medium">{bd.account_holder_name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Account Number</Label>
                <p className="font-medium font-mono">{bd.account_number || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">IFSC Code</Label>
                <p className="font-medium font-mono">{bd.ifsc_code || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Bank / Branch</Label>
                <p className="font-medium">{bd.bank_name} - {bd.branch || 'N/A'}</p>
              </div>
            </CardContent>
          </Card>

          {/* Emergency Contact */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Phone className="w-4 h-4" />
                Emergency Contact
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-zinc-500">Name</Label>
                <p className="font-medium">{ec.name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{ec.phone || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Relationship</Label>
                <p className="font-medium">{ec.relationship || 'N/A'}</p>
              </div>
            </CardContent>
          </Card>

          {/* Documents */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="w-4 h-4" />
                Documents ({submission.documents?.length || 0})
              </CardTitle>
              {hv.documents_verified ? (
                <Badge className="bg-green-100 text-green-700">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Verified
                </Badge>
              ) : canApprove && submission.status === 'submitted' ? (
                <Button size="sm" onClick={handleVerifyDocuments} disabled={processing}>
                  Verify All Documents
                </Button>
              ) : null}
            </CardHeader>
            <CardContent>
              {submission.documents?.length > 0 ? (
                <div className="grid grid-cols-2 gap-3">
                  {submission.documents.map(doc => (
                    <div key={doc.id} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-zinc-400" />
                        <div>
                          <p className="text-sm font-medium capitalize">{doc.type.replace('_', ' ')}</p>
                          <p className="text-xs text-zinc-500">{doc.original_filename}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-500 text-sm">No documents uploaded</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - HR Actions */}
        <div className="space-y-6">
          {/* HR Assignment */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">HR Assignment</CardTitle>
              <CardDescription>Assign department, manager, and other details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Department *</Label>
                <Select
                  value={hrAssignment.department}
                  onValueChange={(v) => setHrAssignment(prev => ({ ...prev, department: v }))}
                  disabled={submission.status === 'completed'}
                >
                  <SelectTrigger data-testid="department-select">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(d => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Reporting Manager *</Label>
                <Select
                  value={hrAssignment.reporting_manager_id}
                  onValueChange={(v) => {
                    const mgr = managers.find(m => m.id === v);
                    setHrAssignment(prev => ({
                      ...prev,
                      reporting_manager_id: v,
                      reporting_manager_name: mgr?.full_name || mgr?.first_name + ' ' + mgr?.last_name
                    }));
                  }}
                  disabled={submission.status === 'completed'}
                >
                  <SelectTrigger data-testid="manager-select">
                    <SelectValue placeholder="Select manager" />
                  </SelectTrigger>
                  <SelectContent>
                    {managers.map(m => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.full_name || `${m.first_name} ${m.last_name}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Joining Date *</Label>
                <Input
                  type="date"
                  data-testid="joining-date-input"
                  value={hrAssignment.joining_date}
                  onChange={(e) => setHrAssignment(prev => ({ ...prev, joining_date: e.target.value }))}
                  disabled={submission.status === 'completed'}
                />
              </div>

              <div>
                <Label>Official Email *</Label>
                <Input
                  type="email"
                  data-testid="official-email-input"
                  value={hrAssignment.official_email}
                  onChange={(e) => setHrAssignment(prev => ({ ...prev, official_email: e.target.value }))}
                  placeholder="name@dvconsulting.co.in"
                  disabled={submission.status === 'completed'}
                />
              </div>

              <div>
                <Label>Employment Type</Label>
                <Select
                  value={hrAssignment.employment_type}
                  onValueChange={(v) => setHrAssignment(prev => ({ ...prev, employment_type: v }))}
                  disabled={submission.status === 'completed'}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EMPLOYMENT_TYPES.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Designation</Label>
                <Input
                  value={hrAssignment.designation}
                  onChange={(e) => setHrAssignment(prev => ({ ...prev, designation: e.target.value }))}
                  disabled={submission.status === 'completed'}
                />
              </div>
            </CardContent>
            {submission.status !== 'completed' && submission.status !== 'rejected' && (
              <CardFooter>
                <Button
                  onClick={handleSaveAssignment}
                  disabled={processing}
                  className="w-full"
                  data-testid="save-assignment-btn"
                >
                  {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                  Save Assignment
                </Button>
              </CardFooter>
            )}
          </Card>

          {/* Verification Status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Verification Checklist</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Documents Verified</span>
                {hv.documents_verified ? (
                  <Badge className="bg-green-100 text-green-700">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Done
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-zinc-500">Pending</Badge>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Bank Verified</span>
                {hv.bank_verified ? (
                  <Badge className="bg-green-100 text-green-700">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Done
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-zinc-500">Pending</Badge>
                )}
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm">HR Assignment</span>
                {hrAssignment.department && hrAssignment.reporting_manager_id && hrAssignment.joining_date && hrAssignment.official_email ? (
                  <Badge className="bg-green-100 text-green-700">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Complete
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-zinc-500">Incomplete</Badge>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Documents Uploaded</span>
                <Badge variant="outline">
                  {submission.documents?.length || 0} / 2 min
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          {submission.status === 'submitted' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Readiness Check */}
                {readinessErrors.length > 0 && (
                  <Alert className="border-amber-200 bg-amber-50">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-amber-800 text-xs">
                      <strong>Cannot complete yet:</strong>
                      <ul className="list-disc ml-4 mt-1">
                        {readinessErrors.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {canApprove && (
                  <>
                    <Button
                      onClick={() => setShowCompleteDialog(true)}
                      disabled={!isReady || processing}
                      className="w-full bg-green-600 hover:bg-green-700"
                      data-testid="complete-onboarding-btn"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Complete Onboarding
                    </Button>

                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        variant="outline"
                        onClick={() => setShowRevisionDialog(true)}
                        disabled={processing}
                      >
                        <Edit className="w-4 h-4 mr-2" />
                        Request Revision
                      </Button>
                      <Button
                        variant="outline"
                        className="text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => setShowRejectDialog(true)}
                        disabled={processing}
                      >
                        <XCircle className="w-4 h-4 mr-2" />
                        Reject
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Audit Log */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Activity Log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {submission.audit_log?.slice().reverse().map((log, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <Clock className="w-3 h-3 text-zinc-400 mt-0.5" />
                    <div>
                      <p className="font-medium capitalize">{log.action.replace('_', ' ')}</p>
                      <p className="text-zinc-500">
                        {log.actor_name || 'Candidate'} • {new Date(log.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Revision Dialog */}
      <Dialog open={showRevisionDialog} onOpenChange={setShowRevisionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Revision</DialogTitle>
            <DialogDescription>
              The candidate will receive an email asking them to update their details.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Reason for Revision *</Label>
              <Textarea
                value={revisionReason}
                onChange={(e) => setRevisionReason(e.target.value)}
                placeholder="Please specify what needs to be corrected..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRevisionDialog(false)}>Cancel</Button>
            <Button onClick={handleRequestRevision} disabled={processing}>
              {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Reject Submission</DialogTitle>
            <DialogDescription>
              This action cannot be undone. The candidate will be notified.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Reason for Rejection *</Label>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Please provide a reason..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleReject} disabled={processing}>
              {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
              Reject Submission
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Dialog */}
      <Dialog open={showCompleteDialog} onOpenChange={setShowCompleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-green-600">Complete Onboarding</DialogTitle>
            <DialogDescription>
              This will generate an Employee ID and create the employee record.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription>
                <strong>Employee ID Format:</strong> DVBC followed by a sequential number (e.g., DVBC042)
              </AlertDescription>
            </Alert>
            <div className="bg-zinc-50 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">Name:</span>
                <span className="font-medium">{submission.candidate_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Department:</span>
                <span className="font-medium">{hrAssignment.department}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Designation:</span>
                <span className="font-medium">{hrAssignment.designation}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Joining Date:</span>
                <span className="font-medium">{hrAssignment.joining_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Official Email:</span>
                <span className="font-medium">{hrAssignment.official_email}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompleteDialog(false)}>Cancel</Button>
            <Button className="bg-green-600 hover:bg-green-700" onClick={handleComplete} disabled={processing}>
              {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Complete & Generate ID
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SubmissionReview;
