import React, { useState, useContext, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Calendar, Mail, Shield, CreditCard, Clock, Send, Edit, Check, Printer, Upload
} from 'lucide-react';
import { toast } from 'sonner';

const DEPARTMENTS = ['Sales', 'HR', 'Consulting', 'Finance', 'Admin', 'Operations'];
const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
  { value: 'part_time', label: 'Part Time' },
];

const DOCUMENT_TYPES = [
  { value: 'pan_card', label: 'PAN Card' },
  { value: 'aadhaar_card', label: 'Aadhaar Card' },
  { value: 'passport_photo', label: 'Passport Photo' },
  { value: 'education_certificate', label: 'Education Certificate' },
  { value: 'experience_certificate', label: 'Experience Certificate' },
  { value: 'offer_letter', label: 'Previous Offer Letter' },
  { value: 'relieving_letter', label: 'Relieving Letter' },
  { value: 'salary_slip', label: 'Salary Slip' },
  { value: 'bank_statement', label: 'Bank Statement' },
  { value: 'other', label: 'Other Document' },
];

// HR Document Upload Component
const HRDocumentUpload = ({ submissionId, onUploadComplete, authHeaders }) => {
  const [uploading, setUploading] = useState(false);
  const [selectedType, setSelectedType] = useState('');
  const fileInputRef = React.useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !selectedType) {
      toast.error('Please select a document type first');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      await axios.post(
        `${API}/onboarding/submissions/${submissionId}/upload-document?document_type=${selectedType}`,
        formData,
        { 
          ...authHeaders,
          headers: { 
            ...authHeaders.headers,
            'Content-Type': 'multipart/form-data' 
          }
        }
      );
      toast.success(`${selectedType.replace('_', ' ')} uploaded successfully`);
      setSelectedType('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      onUploadComplete();
    } catch (err) {
      console.error('Upload error:', err);
      toast.error(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Select value={selectedType} onValueChange={setSelectedType}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Document type" />
        </SelectTrigger>
        <SelectContent>
          {DOCUMENT_TYPES.map(dt => (
            <SelectItem key={dt.value} value={dt.value}>{dt.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileSelect}
        accept=".pdf,.jpg,.jpeg,.png"
      />
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => fileInputRef.current?.click()}
        disabled={!selectedType || uploading}
      >
        {uploading ? (
          <Loader2 className="w-4 h-4 animate-spin mr-1" />
        ) : (
          <Upload className="w-4 h-4 mr-1" />
        )}
        Upload
      </Button>
    </div>
  );
};

const SubmissionReview = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  
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

  // Edit dialogs
  const [editBankDialog, setEditBankDialog] = useState(false);
  const [editEmergencyDialog, setEditEmergencyDialog] = useState(false);
  const [editPersonalDialog, setEditPersonalDialog] = useState(false);
  const [editProfRefDialog, setEditProfRefDialog] = useState(false);
  const [editPerRefDialog, setEditPerRefDialog] = useState(false);
  
  // Edit form data
  const [editBankData, setEditBankData] = useState({});
  const [editEmergencyData, setEditEmergencyData] = useState({});
  const [editPersonalData, setEditPersonalData] = useState({});
  const [editProfRefData, setEditProfRefData] = useState({});
  const [editPerRefData, setEditPerRefData] = useState({});

  // Get token from localStorage (same as App.js pattern)
  const getToken = () => localStorage.getItem('token');
  const authHeaders = { headers: { Authorization: `Bearer ${getToken()}` } };
  const canApprove = user?.role === 'hr_manager' || user?.role === 'admin';

  // Fetch submission using React Query
  const { data: submission, isLoading: loading, refetch: refetchSubmission } = useQuery({
    queryKey: ['onboarding-submission', submissionId],
    queryFn: async () => {
      const response = await axios.get(`${API}/onboarding/submissions/${submissionId}`, authHeaders);
      return response.data;
    },
    enabled: !!submissionId && !!user,
    staleTime: 2 * 60 * 1000,
    onError: () => {
      toast.error('Failed to load submission');
      navigate('/onboarding-hub');
    },
    onSuccess: (data) => {
      // Pre-fill HR assignment form
      if (data.hr_assigned) {
        setHrAssignment({
          department: data.hr_assigned.department || '',
          reporting_manager_id: data.hr_assigned.reporting_manager_id || '',
          reporting_manager_name: data.hr_assigned.reporting_manager_name || '',
          joining_date: data.hr_assigned.joining_date || '',
          official_email: data.hr_assigned.official_email || '',
          employment_type: data.hr_assigned.employment_type || 'full_time',
          designation: data.hr_assigned.designation || data.offered_position || '',
        });
      } else if (data.offered_position) {
        setHrAssignment(prev => ({ ...prev, designation: data.offered_position }));
      }
    }
  });

  // Fetch managers using React Query
  const { data: managersData = [] } = useQuery({
    queryKey: ['employees', 'managers'],
    queryFn: async () => {
      const response = await axios.get(`${API}/employees/all`, authHeaders);
      const employees = response.data?.items || response.data || [];
      return Array.isArray(employees) ? employees.filter(e => 
        ['manager', 'hr_manager', 'project_manager', 'principal_consultant', 'senior_consultant', 'admin'].includes(e.role)
      ) : [];
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000
  });

  const managers = managersData;

  // Mutation for saving HR assignment
  const saveAssignmentMutation = useMutation({
    mutationFn: async (data) => {
      await axios.patch(`${API}/onboarding/submissions/${submissionId}/hr-assign`, data, authHeaders);
    },
    onSuccess: () => {
      toast.success('Assignment details saved');
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to save assignment')
  });

  const handleSaveAssignment = () => {
    saveAssignmentMutation.mutate(hrAssignment);
  };

  // Mutation for verifying documents
  const verifyDocumentsMutation = useMutation({
    mutationFn: async () => {
      await axios.post(`${API}/onboarding/submissions/${submissionId}/verify-documents`, {}, authHeaders);
    },
    onSuccess: () => {
      toast.success('Documents verified');
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to verify documents')
  });

  const handleVerifyDocuments = () => {
    verifyDocumentsMutation.mutate();
  };

  // Mutation for verifying bank
  const verifyBankMutation = useMutation({
    mutationFn: async () => {
      await axios.post(`${API}/onboarding/submissions/${submissionId}/verify-bank`, {}, authHeaders);
    },
    onSuccess: () => {
      toast.success('Bank details verified');
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to verify bank details')
  });

  const handleVerifyBank = () => {
    verifyBankMutation.mutate();
  };

  // Mutation for requesting revision
  const requestRevisionMutation = useMutation({
    mutationFn: async (reason) => {
      await axios.post(`${API}/onboarding/submissions/${submissionId}/request-revision`, 
        { reason }, authHeaders);
    },
    onSuccess: () => {
      toast.success('Revision request sent to candidate');
      setShowRevisionDialog(false);
      setRevisionReason('');
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to request revision')
  });

  const handleRequestRevision = () => {
    if (!revisionReason.trim()) {
      toast.error('Please provide a reason for revision');
      return;
    }
    requestRevisionMutation.mutate(revisionReason);
  };

  // Mutation for rejecting submission
  const rejectMutation = useMutation({
    mutationFn: async (reason) => {
      await axios.post(`${API}/onboarding/submissions/${submissionId}/reject`, 
        { reason }, authHeaders);
    },
    onSuccess: () => {
      toast.success('Submission rejected');
      setShowRejectDialog(false);
      setRejectReason('');
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to reject submission')
  });

  const handleReject = () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    rejectMutation.mutate(rejectReason);
  };

  // Mutation for completing onboarding
  const completeMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API}/onboarding/submissions/${submissionId}/complete`, {}, authHeaders);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Onboarding complete! Employee ID: ${data.employee_id}`);
      setShowCompleteDialog(false);
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to complete onboarding')
  });

  const handleComplete = () => {
    completeMutation.mutate();
  };

  // Mutation for updating sections
  const updateSectionMutation = useMutation({
    mutationFn: async ({ section, data }) => {
      await axios.patch(`${API}/onboarding/submissions/${submissionId}/update-section`, 
        { section, data }, authHeaders);
    },
    onSuccess: (_, { section }) => {
      toast.success(`${section.replace('_', ' ')} updated successfully`);
      // Close all edit dialogs
      setEditBankDialog(false);
      setEditEmergencyDialog(false);
      setEditPersonalDialog(false);
      setEditProfRefDialog(false);
      setEditPerRefDialog(false);
      queryClient.invalidateQueries({ queryKey: ['onboarding-submission', submissionId] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update')
  });

  const handleUpdateSection = (section, data) => {
    updateSectionMutation.mutate({ section, data });
  };

  // Open edit dialogs with current data
  const openEditBank = () => {
    const bd = submission?.bank_details || {};
    setEditBankData({
      account_holder_name: bd.account_holder_name || '',
      account_number: bd.account_number || '',
      ifsc_code: bd.ifsc_code || '',
      bank_name: bd.bank_name || '',
      branch: bd.branch || ''
    });
    setEditBankDialog(true);
  };

  const openEditEmergency = () => {
    const ec = submission?.emergency_contact || {};
    setEditEmergencyData({
      name: ec.name || '',
      phone: ec.phone || '',
      relationship: ec.relationship || ''
    });
    setEditEmergencyDialog(true);
  };

  const openEditPersonal = () => {
    const cd = submission?.candidate_details || {};
    setEditPersonalData({
      first_name: cd.first_name || '',
      last_name: cd.last_name || '',
      date_of_birth: cd.date_of_birth || '',
      phone: cd.phone || '',
      alternate_phone: cd.alternate_phone || '',
      gender: cd.gender || '',
      blood_group: cd.blood_group || '',
      marital_status: cd.marital_status || '',
      nationality: cd.nationality || 'Indian',
      pan_number: cd.pan_number || '',
      aadhaar_number: cd.aadhaar_number || '',
      passport_number: cd.passport_number || '',
      current_address: cd.current_address || {},
      permanent_address: cd.permanent_address || {}
    });
    setEditPersonalDialog(true);
  };

  const openEditProfRef = () => {
    const pr = submission?.professional_reference || {};
    setEditProfRefData({
      name: pr.name || '',
      phone: pr.phone || '',
      company_name: pr.company_name || '',
      designation: pr.designation || ''
    });
    setEditProfRefDialog(true);
  };

  const openEditPerRef = () => {
    const per = submission?.personal_reference || {};
    setEditPerRefData({
      name: per.name || '',
      phone: per.phone || '',
      address: per.address || ''
    });
    setEditPerRefDialog(true);
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

  // Print onboarding form
  const handlePrint = () => {
    const cd = submission.candidate_details || {};
    const bd = submission.bank_details || {};
    const ec = submission.emergency_contact || {};
    const pr = submission.professional_reference || {};
    const per = submission.personal_reference || {};
    const ha = submission.hr_assigned || {};
    
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Onboarding Form - ${submission.candidate_name}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; font-size: 12px; color: #333; }
          .header { text-align: center; border-bottom: 2px solid #f97316; padding-bottom: 15px; margin-bottom: 20px; }
          .header h1 { margin: 0; font-size: 18px; color: #000; }
          .header p { margin: 5px 0 0; color: #666; font-size: 11px; }
          .section { margin-bottom: 20px; page-break-inside: avoid; }
          .section-title { background: #f5f5f5; padding: 8px 12px; font-weight: bold; font-size: 13px; margin-bottom: 10px; border-left: 3px solid #f97316; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; }
          .field { margin-bottom: 8px; }
          .field-label { font-size: 10px; color: #666; text-transform: uppercase; }
          .field-value { font-weight: 500; }
          table { width: 100%; border-collapse: collapse; font-size: 11px; }
          th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
          th { background: #f5f5f5; font-weight: 600; }
          .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 10px; color: #666; }
          .signature-box { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px; }
          .signature { border-top: 1px solid #333; padding-top: 5px; text-align: center; }
          .status-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 10px; font-weight: 600; }
          .status-completed { background: #dcfce7; color: #166534; }
          .status-pending { background: #fef3c7; color: #92400e; }
          @media print { body { padding: 0; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>D&V Business Consulting</h1>
          <p>Employee Onboarding Form</p>
        </div>
        
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
          <div><strong>Candidate:</strong> ${submission.candidate_name}</div>
          <div><strong>Position:</strong> ${submission.offered_position}</div>
          <div><span class="status-badge ${submission.status === 'completed' ? 'status-completed' : 'status-pending'}">${submission.status?.toUpperCase()}</span></div>
        </div>
        
        ${submission.employee_id_generated ? `<div style="background:#dcfce7;padding:10px;margin-bottom:15px;border-radius:4px;"><strong>Employee ID:</strong> ${submission.employee_id_generated}</div>` : ''}
        
        <div class="section">
          <div class="section-title">Personal Details</div>
          <div class="grid">
            <div class="field"><div class="field-label">Full Name</div><div class="field-value">${cd.first_name || ''} ${cd.last_name || ''}</div></div>
            <div class="field"><div class="field-label">Date of Birth</div><div class="field-value">${cd.date_of_birth || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Gender</div><div class="field-value">${cd.gender || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Blood Group</div><div class="field-value">${cd.blood_group || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Marital Status</div><div class="field-value">${cd.marital_status || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Nationality</div><div class="field-value">${cd.nationality || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Phone</div><div class="field-value">${cd.phone || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Alternate Phone</div><div class="field-value">${cd.alternate_phone || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Email</div><div class="field-value">${submission.candidate_email}</div></div>
            <div class="field"><div class="field-label">PAN Number</div><div class="field-value">${cd.pan_number || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Aadhaar Number</div><div class="field-value">${cd.aadhaar_number || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Passport</div><div class="field-value">${cd.passport_number || 'N/A'}</div></div>
          </div>
          <div class="field" style="margin-top:10px;"><div class="field-label">Current Address</div><div class="field-value">${cd.current_address?.street || ''}, ${cd.current_address?.city || ''}, ${cd.current_address?.state || ''} - ${cd.current_address?.pincode || ''}</div></div>
          <div class="field"><div class="field-label">Permanent Address</div><div class="field-value">${cd.permanent_address?.street || ''}, ${cd.permanent_address?.city || ''}, ${cd.permanent_address?.state || ''} - ${cd.permanent_address?.pincode || ''}</div></div>
        </div>
        
        <div class="section">
          <div class="section-title">Education</div>
          <table>
            <thead><tr><th>Degree</th><th>Institution</th><th>Year</th><th>%/CGPA</th></tr></thead>
            <tbody>
              ${(submission.education || []).map(e => `<tr><td>${e.degree}</td><td>${e.institution}</td><td>${e.year}</td><td>${e.percentage}</td></tr>`).join('')}
              ${(submission.education || []).length === 0 ? '<tr><td colspan="4" style="text-align:center;color:#999;">No education details</td></tr>' : ''}
            </tbody>
          </table>
        </div>
        
        <div class="section">
          <div class="section-title">Work Experience</div>
          <table>
            <thead><tr><th>Company</th><th>Designation</th><th>From</th><th>To</th><th>Reason for Leaving</th></tr></thead>
            <tbody>
              ${(submission.employment_history || []).map(e => `<tr><td>${e.company}</td><td>${e.designation}</td><td>${e.from_date}</td><td>${e.to_date || 'Present'}</td><td>${e.reason_for_leaving || '-'}</td></tr>`).join('')}
              ${(submission.employment_history || []).length === 0 ? '<tr><td colspan="5" style="text-align:center;color:#999;">No work experience</td></tr>' : ''}
            </tbody>
          </table>
        </div>
        
        <div class="section">
          <div class="section-title">Bank Details</div>
          <div class="grid">
            <div class="field"><div class="field-label">Account Holder</div><div class="field-value">${bd.account_holder_name || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Account Number</div><div class="field-value">${bd.account_number || 'N/A'}</div></div>
            <div class="field"><div class="field-label">IFSC Code</div><div class="field-value">${bd.ifsc_code || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Bank / Branch</div><div class="field-value">${bd.bank_name || ''} - ${bd.branch || 'N/A'}</div></div>
          </div>
        </div>
        
        <div class="section">
          <div class="section-title">References</div>
          <div class="grid">
            <div>
              <strong style="font-size:11px;">Professional Reference</strong>
              <div class="field"><div class="field-label">Name</div><div class="field-value">${pr.name || 'N/A'}</div></div>
              <div class="field"><div class="field-label">Phone</div><div class="field-value">${pr.phone || 'N/A'}</div></div>
              <div class="field"><div class="field-label">Company</div><div class="field-value">${pr.company_name || 'N/A'}</div></div>
              <div class="field"><div class="field-label">Designation</div><div class="field-value">${pr.designation || 'N/A'}</div></div>
            </div>
            <div>
              <strong style="font-size:11px;">Personal Reference</strong>
              <div class="field"><div class="field-label">Name</div><div class="field-value">${per.name || 'N/A'}</div></div>
              <div class="field"><div class="field-label">Phone</div><div class="field-value">${per.phone || 'N/A'}</div></div>
              <div class="field"><div class="field-label">Address</div><div class="field-value">${per.address || 'N/A'}</div></div>
            </div>
          </div>
        </div>
        
        <div class="section">
          <div class="section-title">Emergency Contact</div>
          <div class="grid">
            <div class="field"><div class="field-label">Name</div><div class="field-value">${ec.name || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Phone</div><div class="field-value">${ec.phone || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Relationship</div><div class="field-value">${ec.relationship || 'N/A'}</div></div>
          </div>
        </div>
        
        ${ha.department ? `
        <div class="section">
          <div class="section-title">HR Assignment (Internal)</div>
          <div class="grid">
            <div class="field"><div class="field-label">Department</div><div class="field-value">${ha.department || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Designation</div><div class="field-value">${ha.designation || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Joining Date</div><div class="field-value">${ha.joining_date || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Official Email</div><div class="field-value">${ha.official_email || 'N/A'}</div></div>
            <div class="field"><div class="field-label">Reporting Manager</div><div class="field-value">${ha.reporting_manager_name || 'N/A'}</div></div>
          </div>
        </div>
        ` : ''}
        
        <div class="section">
          <div class="section-title">Documents Uploaded</div>
          <ul style="margin:0;padding-left:20px;">
            ${(submission.documents || []).map(d => `<li>${d.type?.replace(/_/g, ' ')} - ${d.filename}</li>`).join('')}
            ${(submission.documents || []).length === 0 ? '<li style="color:#999;">No documents uploaded</li>' : ''}
          </ul>
        </div>
        
        <div class="signature-box">
          <div>
            <div class="signature">Employee Signature</div>
          </div>
          <div>
            <div class="signature">HR Signature</div>
          </div>
        </div>
        
        <div class="footer">
          <p>Generated on: ${new Date().toLocaleString()} | D&V Business Consulting - NETRA ERP</p>
        </div>
      </body>
      </html>
    `;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 250);
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
  const pr = submission.professional_reference || {};
  const per = submission.personal_reference || {};
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
            <div className="text-zinc-500 text-sm flex items-center gap-2">
              <span>{submission.offered_position}</span>
              {getStatusBadge(submission.status)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handlePrint} data-testid="print-btn">
            <Printer className="w-4 h-4 mr-2" />
            Print Form
          </Button>
          {submission.employee_id_generated && (
            <Badge className="bg-green-100 text-green-700 text-lg px-4 py-2">
              Employee ID: {submission.employee_id_generated}
            </Badge>
          )}
        </div>
      </div>

      {/* Completed Alert with Go-Live link */}
      {submission.status === 'completed' && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800 flex items-center justify-between">
            <span>
              Onboarding completed on {new Date(submission.completed_at).toLocaleDateString()}.
              Employee ID <strong>{submission.employee_id_generated}</strong> has been generated.
            </span>
            <Button 
              size="sm" 
              variant="outline" 
              className="ml-4 border-green-300 text-green-700 hover:bg-green-100"
              onClick={() => navigate('/go-live')}
            >
              Go to Go-Live Dashboard →
            </Button>
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
                <Label className="text-xs text-zinc-500">Alternate Phone</Label>
                <p className="font-medium">{cd.alternate_phone || 'N/A'}</p>
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
                <Label className="text-xs text-zinc-500">Marital Status</Label>
                <p className="font-medium capitalize">{cd.marital_status || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Nationality</Label>
                <p className="font-medium">{cd.nationality || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">PAN Number</Label>
                <p className="font-medium font-mono">{cd.pan_number || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Aadhaar Number</Label>
                <p className="font-medium font-mono">{cd.aadhaar_number || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Passport Number</Label>
                <p className="font-medium">{cd.passport_number || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Current Address</Label>
                <p className="font-medium">
                  {cd.current_address?.street ? `${cd.current_address.street}, ${cd.current_address?.city}, ${cd.current_address?.state} - ${cd.current_address?.pincode}` : 'N/A'}
                </p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Permanent Address</Label>
                <p className="font-medium">
                  {cd.permanent_address?.street ? `${cd.permanent_address.street}, ${cd.permanent_address?.city}, ${cd.permanent_address?.state} - ${cd.permanent_address?.pincode}` : 'N/A'}
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

          {/* Professional Reference */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Briefcase className="w-4 h-4" />
                Professional Reference
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-zinc-500">Name</Label>
                <p className="font-medium">{pr.name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{pr.phone || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Company</Label>
                <p className="font-medium">{pr.company_name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Designation</Label>
                <p className="font-medium">{pr.designation || 'N/A'}</p>
              </div>
            </CardContent>
          </Card>

          {/* Personal Reference */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="w-4 h-4" />
                Personal Reference
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-zinc-500">Name</Label>
                <p className="font-medium">{per.name || 'N/A'}</p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500">Phone</Label>
                <p className="font-medium">{per.phone || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-zinc-500">Address</Label>
                <p className="font-medium">{per.address || 'N/A'}</p>
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
              {/* Only show Verified badge if documents exist AND are verified */}
              {hv.documents_verified && (submission.documents?.length || 0) > 0 ? (
                <Badge className="bg-green-100 text-green-700">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Verified
                </Badge>
              ) : (submission.documents?.length || 0) === 0 ? (
                <Badge className="bg-amber-100 text-amber-700">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  No Documents
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
                <div className="text-center py-4">
                  <p className="text-zinc-500 text-sm mb-3">No documents uploaded by candidate</p>
                  {canApprove && (
                    <HRDocumentUpload 
                      submissionId={submissionId} 
                      onUploadComplete={refetchSubmission}
                      authHeaders={authHeaders}
                    />
                  )}
                </div>
              )}
              
              {/* HR Document Upload Section - always visible for HR */}
              {canApprove && (submission.documents?.length || 0) > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm font-medium mb-2">Upload Additional Documents</p>
                  <HRDocumentUpload 
                    submissionId={submissionId} 
                    onUploadComplete={refetchSubmission}
                    authHeaders={authHeaders}
                  />
                </div>
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
