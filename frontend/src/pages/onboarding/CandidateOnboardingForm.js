import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Progress } from '../../components/ui/progress';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { 
  User, GraduationCap, Briefcase, Building2, Phone, AlertTriangle,
  ChevronRight, ChevronLeft, Upload, Check, FileText, Loader2, 
  Shield, CheckCircle2, XCircle, Clock, Mail, Calendar, Users
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const STEPS = [
  { id: 'personal', title: 'Personal Details', icon: User },
  { id: 'education', title: 'Education', icon: GraduationCap },
  { id: 'experience', title: 'Work Experience', icon: Briefcase },
  { id: 'bank', title: 'Bank Details', icon: Building2 },
  { id: 'references', title: 'References', icon: Users },
  { id: 'emergency', title: 'Emergency Contact', icon: Phone },
  { id: 'documents', title: 'Documents', icon: FileText },
  { id: 'review', title: 'Review & Submit', icon: CheckCircle2 },
];

const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const MARITAL_STATUS = ['single', 'married', 'divorced', 'widowed'];

// Validation helpers
const isValidIndianPhone = (phone) => {
  if (!phone) return false;
  const cleaned = phone.replace(/[\s-]/g, '');
  // Indian phone: 10 digits starting with 6, 7, 8, or 9
  return /^[6-9]\d{9}$/.test(cleaned);
};

const isValidEmail = (email) => {
  if (!email) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

const isValidPAN = (pan) => {
  if (!pan) return false;
  // Indian PAN: 5 letters, 4 digits, 1 letter
  return /^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan.toUpperCase());
};

const isValidAadhaar = (aadhaar) => {
  if (!aadhaar) return false;
  const cleaned = aadhaar.replace(/[\s-]/g, '');
  // Aadhaar: 12 digits
  return /^\d{12}$/.test(cleaned);
};

const isValidPincode = (pincode) => {
  if (!pincode) return false;
  // Indian pincode: 6 digits
  return /^\d{6}$/.test(pincode);
};

const isValidIFSC = (ifsc) => {
  if (!ifsc) return false;
  // IFSC: 4 letters, 1 digit (0), 6 alphanumeric
  return /^[A-Z]{4}0[A-Z0-9]{6}$/.test(ifsc.toUpperCase());
};

const CandidateOnboardingForm = () => {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submission, setSubmission] = useState(null);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [lastSaved, setLastSaved] = useState(null);

  // Form data
  const [formData, setFormData] = useState({
    candidate_details: {
      first_name: '',
      last_name: '',
      date_of_birth: '',
      gender: '',
      blood_group: '',
      marital_status: '',
      nationality: 'Indian',
      phone: '',
      alternate_phone: '',
      pan_number: '',
      aadhaar_number: '',
      passport_number: '',
      driving_license: '',
      current_address: { street: '', city: '', state: '', pincode: '' },
      permanent_address: { street: '', city: '', state: '', pincode: '' },
    },
    education: [],
    employment_history: [],
    bank_details: {
      account_number: '',
      ifsc_code: '',
      bank_name: '',
      branch: '',
      account_holder_name: '',
    },
    professional_reference: {
      name: '',
      phone: '',
      company_name: '',
      designation: '',
    },
    personal_reference: {
      name: '',
      phone: '',
      address: '',
    },
    emergency_contact: {
      name: '',
      phone: '',
      relationship: '',
      address: '',
    },
    declaration_signed: false,
  });

  // Fetch submission data
  useEffect(() => {
    const fetchSubmission = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API}/onboarding/public/${token}`);
        setSubmission(response.data);
        
        // Pre-fill form with existing data
        if (response.data.candidate_details) {
          setFormData(prev => ({
            ...prev,
            candidate_details: { ...prev.candidate_details, ...response.data.candidate_details }
          }));
        }
        if (response.data.education?.length > 0) {
          setFormData(prev => ({ ...prev, education: response.data.education }));
        }
        if (response.data.employment_history?.length > 0) {
          setFormData(prev => ({ ...prev, employment_history: response.data.employment_history }));
        }
        if (response.data.bank_details) {
          setFormData(prev => ({
            ...prev,
            bank_details: { ...prev.bank_details, ...response.data.bank_details }
          }));
        }
        if (response.data.professional_reference) {
          setFormData(prev => ({
            ...prev,
            professional_reference: { ...prev.professional_reference, ...response.data.professional_reference }
          }));
        }
        if (response.data.personal_reference) {
          setFormData(prev => ({
            ...prev,
            personal_reference: { ...prev.personal_reference, ...response.data.personal_reference }
          }));
        }
        if (response.data.emergency_contact) {
          setFormData(prev => ({
            ...prev,
            emergency_contact: { ...prev.emergency_contact, ...response.data.emergency_contact }
          }));
        }
        if (response.data.declaration_signed) {
          setFormData(prev => ({ ...prev, declaration_signed: true }));
        }
      } catch (err) {
        console.error('Error fetching submission:', err);
        setError(err.response?.data?.detail || 'Unable to load the form. Please check your link.');
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchSubmission();
    }
  }, [token]);

  // Auto-save every 30 seconds
  useEffect(() => {
    if (!submission || submission.status === 'submitted') return;
    
    const interval = setInterval(() => {
      if (submission && submission.status !== 'submitted') {
        handleSaveInternal(true);
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [submission?.status]);

  // Internal save function to avoid dependency issues
  const handleSaveInternal = async (silent = false) => {
    if (!submission || submission.status === 'submitted') return;
    
    try {
      setSaving(true);
      await axios.post(`${API}/onboarding/public/${token}/save`, formData);
      setLastSaved(new Date());
      if (!silent) {
        toast.success('Progress saved');
      }
    } catch (err) {
      console.error('Error saving:', err);
      if (!silent) {
        toast.error('Failed to save progress');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async (silent = false) => {
    await handleSaveInternal(silent);
  };

  const handleSubmit = async () => {
    // Validate ALL required fields
    const cd = formData.candidate_details;
    const bd = formData.bank_details;
    const pr = formData.professional_reference;
    const per = formData.personal_reference;
    const ec = formData.emergency_contact;
    
    // Personal Details validation (including alternate phone)
    if (!cd.first_name || !cd.last_name || !cd.phone || !cd.alternate_phone || !cd.date_of_birth || 
        !cd.gender || !cd.blood_group || !cd.marital_status || !cd.pan_number || !cd.aadhaar_number) {
      toast.error('Please complete all personal details including alternate phone');
      setCurrentStep(0);
      return;
    }
    
    // Phone validation
    if (!isValidIndianPhone(cd.phone)) {
      toast.error('Please enter a valid 10-digit Indian phone number');
      setCurrentStep(0);
      return;
    }
    if (!isValidIndianPhone(cd.alternate_phone)) {
      toast.error('Please enter a valid 10-digit alternate phone number');
      setCurrentStep(0);
      return;
    }
    
    // PAN validation
    if (!isValidPAN(cd.pan_number)) {
      toast.error('Please enter a valid PAN number (e.g., ABCDE1234F)');
      setCurrentStep(0);
      return;
    }
    
    // Aadhaar validation
    if (!isValidAadhaar(cd.aadhaar_number)) {
      toast.error('Please enter a valid 12-digit Aadhaar number');
      setCurrentStep(0);
      return;
    }
    
    // Address validation
    if (!cd.current_address?.street || !cd.current_address?.city || 
        !cd.current_address?.state || !cd.current_address?.pincode) {
      toast.error('Please complete current address');
      setCurrentStep(0);
      return;
    }
    if (!isValidPincode(cd.current_address?.pincode)) {
      toast.error('Please enter a valid 6-digit pincode for current address');
      setCurrentStep(0);
      return;
    }
    if (!cd.permanent_address?.street || !cd.permanent_address?.city || 
        !cd.permanent_address?.state || !cd.permanent_address?.pincode) {
      toast.error('Please complete permanent address');
      setCurrentStep(0);
      return;
    }
    if (!isValidPincode(cd.permanent_address?.pincode)) {
      toast.error('Please enter a valid 6-digit pincode for permanent address');
      setCurrentStep(0);
      return;
    }
    
    // Education validation
    if (!formData.education || formData.education.length === 0) {
      toast.error('Please add at least one education qualification');
      setCurrentStep(1);
      return;
    }
    for (let i = 0; i < formData.education.length; i++) {
      const edu = formData.education[i];
      if (!edu.degree || !edu.institution || !edu.year || !edu.percentage) {
        toast.error(`Please complete all fields for education entry ${i + 1}`);
        setCurrentStep(1);
        return;
      }
    }
    
    // Bank Details validation
    if (!bd.account_holder_name || !bd.account_number || !bd.ifsc_code || !bd.bank_name || !bd.branch) {
      toast.error('Please complete all bank details');
      setCurrentStep(3);
      return;
    }
    if (!isValidIFSC(bd.ifsc_code)) {
      toast.error('Please enter a valid IFSC code (e.g., SBIN0001234)');
      setCurrentStep(3);
      return;
    }
    
    // Professional Reference validation
    if (!pr.name || !pr.phone || !pr.company_name || !pr.designation) {
      toast.error('Please complete professional reference details');
      setCurrentStep(4);
      return;
    }
    if (!isValidIndianPhone(pr.phone)) {
      toast.error('Please enter a valid phone number for professional reference');
      setCurrentStep(4);
      return;
    }
    
    // Personal Reference validation
    if (!per.name || !per.phone || !per.address) {
      toast.error('Please complete personal reference details');
      setCurrentStep(4);
      return;
    }
    if (!isValidIndianPhone(per.phone)) {
      toast.error('Please enter a valid phone number for personal reference');
      setCurrentStep(4);
      return;
    }
    
    // Emergency Contact validation
    if (!ec.name || !ec.phone || !ec.relationship) {
      toast.error('Please complete all emergency contact details');
      setCurrentStep(5);
      return;
    }
    if (!isValidIndianPhone(ec.phone)) {
      toast.error('Please enter a valid phone number for emergency contact');
      setCurrentStep(5);
      return;
    }
    
    // Documents validation
    const uploadedDocs = submission?.documents || [];
    const requiredDocs = ['pan_card', 'aadhaar'];
    const missingDocs = requiredDocs.filter(d => !uploadedDocs.find(doc => doc.type === d));
    if (missingDocs.length > 0) {
      toast.error(`Please upload required documents: ${missingDocs.join(', ')}`);
      setCurrentStep(6);
      return;
    }
    
    // Declaration validation
    if (!formData.declaration_signed) {
      toast.error('Please accept the declaration');
      setCurrentStep(7);
      return;
    }

    // Add declaration timestamp and details
    const submissionData = {
      ...formData,
      declaration: {
        signed: true,
        signed_at: new Date().toISOString(),
        text: "I hereby declare that all the information provided above is true and correct to the best of my knowledge. I understand that any false information may result in termination of my employment. I authorize D&V Business Consulting to verify this information and store my data as per company policy.",
        ip_address: "captured_by_backend"
      }
    };

    try {
      setSubmitting(true);
      await axios.post(`${API}/onboarding/public/${token}/submit`, submissionData);
      toast.success('Form submitted successfully! HR will review your details.');
      // Refresh to show submitted state
      const response = await axios.get(`${API}/onboarding/public/${token}`);
      setSubmission(response.data);
    } catch (err) {
      console.error('Error submitting:', err);
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileUpload = async (docType, file) => {
    if (!file) return;
    
    const formDataUpload = new FormData();
    formDataUpload.append('file', file);
    
    try {
      setSaving(true);
      await axios.post(
        `${API}/onboarding/public/${token}/upload?document_type=${docType}`,
        formDataUpload,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      toast.success(`${docType.replace('_', ' ')} uploaded successfully`);
      // Refresh submission to get updated documents
      const response = await axios.get(`${API}/onboarding/public/${token}`);
      setSubmission(response.data);
    } catch (err) {
      console.error('Error uploading:', err);
      toast.error(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (path, value) => {
    setFormData(prev => {
      const keys = path.split('.');
      const newData = { ...prev };
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      
      return newData;
    });
  };

  const addEducation = () => {
    setFormData(prev => ({
      ...prev,
      education: [...prev.education, { degree: '', institution: '', year: '', percentage: '' }]
    }));
  };

  const removeEducation = (index) => {
    setFormData(prev => ({
      ...prev,
      education: prev.education.filter((_, i) => i !== index)
    }));
  };

  const addEmployment = () => {
    setFormData(prev => ({
      ...prev,
      employment_history: [...prev.employment_history, {
        company: '', designation: '', from_date: '', to_date: '', reason_for_leaving: ''
      }]
    }));
  };

  const removeEmployment = (index) => {
    setFormData(prev => ({
      ...prev,
      employment_history: prev.employment_history.filter((_, i) => i !== index)
    }));
  };

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
            <CardTitle className="text-red-600">Link Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent className="text-center text-sm text-zinc-500">
            Please contact HR if you believe this is an error.
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  // Submitted state
  if (submission?.status === 'submitted') {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <CardTitle className="text-green-600">Application Submitted!</CardTitle>
            <CardDescription>
              Thank you, {submission.candidate_name}! Your onboarding details have been submitted successfully.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-zinc-50 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-500">Position</span>
                <span className="font-medium">{submission.offered_position}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Submitted On</span>
                <span className="font-medium">
                  {new Date(submission.submitted_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <Alert>
              <Clock className="h-4 w-4" />
              <AlertDescription>
                Our HR team will review your details and contact you soon.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Revision requested state
  if (submission?.status === 'revision_requested') {
    const latestRevision = submission.revision_history?.[submission.revision_history.length - 1];
    return (
      <div className="min-h-screen bg-zinc-50 p-4">
        <div className="max-w-4xl mx-auto">
          <Alert className="mb-6 border-amber-200 bg-amber-50">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800">
              <strong>Revision Requested:</strong> {latestRevision?.reason || 'Please update your details.'}
            </AlertDescription>
          </Alert>
          {/* Continue with form render below */}
        </div>
      </div>
    );
  }

  // Render form steps
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Personal Details
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="first_name">First Name *</Label>
                <Input
                  id="first_name"
                  data-testid="first-name-input"
                  value={formData.candidate_details.first_name}
                  onChange={(e) => updateField('candidate_details.first_name', e.target.value)}
                  placeholder="Enter first name"
                />
              </div>
              <div>
                <Label htmlFor="last_name">Last Name *</Label>
                <Input
                  id="last_name"
                  data-testid="last-name-input"
                  value={formData.candidate_details.last_name}
                  onChange={(e) => updateField('candidate_details.last_name', e.target.value)}
                  placeholder="Enter last name"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="dob">Date of Birth *</Label>
                <Input
                  id="dob"
                  type="date"
                  data-testid="dob-input"
                  value={formData.candidate_details.date_of_birth}
                  onChange={(e) => updateField('candidate_details.date_of_birth', e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="gender">Gender *</Label>
                <Select
                  value={formData.candidate_details.gender}
                  onValueChange={(v) => updateField('candidate_details.gender', v)}
                >
                  <SelectTrigger data-testid="gender-select">
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    {GENDER_OPTIONS.map(g => (
                      <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="blood_group">Blood Group *</Label>
                <Select
                  value={formData.candidate_details.blood_group}
                  onValueChange={(v) => updateField('candidate_details.blood_group', v)}
                >
                  <SelectTrigger data-testid="blood-group-select">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {BLOOD_GROUPS.map(bg => (
                      <SelectItem key={bg} value={bg}>{bg}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="phone">Phone * <span className="text-xs text-zinc-400">(10 digits)</span></Label>
                <Input
                  id="phone"
                  data-testid="phone-input"
                  type="tel"
                  inputMode="numeric"
                  value={formData.candidate_details.phone}
                  onChange={(e) => updateField('candidate_details.phone', e.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="9876543210"
                  maxLength={10}
                  className={formData.candidate_details.phone && !isValidIndianPhone(formData.candidate_details.phone) ? 'border-red-300 focus:border-red-500' : ''}
                />
                {formData.candidate_details.phone && !isValidIndianPhone(formData.candidate_details.phone) && (
                  <p className="text-xs text-red-500 mt-1">Enter valid 10-digit number starting with 6-9</p>
                )}
              </div>
              <div>
                <Label htmlFor="alt_phone">Alternate Phone * <span className="text-xs text-zinc-400">(10 digits)</span></Label>
                <Input
                  id="alt_phone"
                  type="tel"
                  inputMode="numeric"
                  value={formData.candidate_details.alternate_phone}
                  onChange={(e) => updateField('candidate_details.alternate_phone', e.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="9876543210"
                  maxLength={10}
                  className={formData.candidate_details.alternate_phone && !isValidIndianPhone(formData.candidate_details.alternate_phone) ? 'border-red-300 focus:border-red-500' : ''}
                />
                {formData.candidate_details.alternate_phone && !isValidIndianPhone(formData.candidate_details.alternate_phone) && (
                  <p className="text-xs text-red-500 mt-1">Enter valid 10-digit number starting with 6-9</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="pan">PAN Number * <span className="text-xs text-zinc-400">(ABCDE1234F)</span></Label>
                <Input
                  id="pan"
                  data-testid="pan-input"
                  value={formData.candidate_details.pan_number}
                  onChange={(e) => updateField('candidate_details.pan_number', e.target.value.toUpperCase())}
                  placeholder="ABCDE1234F"
                  maxLength={10}
                  className={formData.candidate_details.pan_number && !isValidPAN(formData.candidate_details.pan_number) ? 'border-red-300 focus:border-red-500' : ''}
                />
                {formData.candidate_details.pan_number && !isValidPAN(formData.candidate_details.pan_number) && (
                  <p className="text-xs text-red-500 mt-1">Enter valid PAN (5 letters, 4 digits, 1 letter)</p>
                )}
              </div>
              <div>
                <Label htmlFor="aadhaar">Aadhaar Number * <span className="text-xs text-zinc-400">(12 digits)</span></Label>
                <Input
                  id="aadhaar"
                  data-testid="aadhaar-input"
                  type="tel"
                  inputMode="numeric"
                  value={formData.candidate_details.aadhaar_number}
                  onChange={(e) => updateField('candidate_details.aadhaar_number', e.target.value.replace(/\D/g, '').slice(0, 12))}
                  placeholder="123456789012"
                  maxLength={12}
                  className={formData.candidate_details.aadhaar_number && !isValidAadhaar(formData.candidate_details.aadhaar_number) ? 'border-red-300 focus:border-red-500' : ''}
                />
                {formData.candidate_details.aadhaar_number && !isValidAadhaar(formData.candidate_details.aadhaar_number) && (
                  <p className="text-xs text-red-500 mt-1">Enter valid 12-digit Aadhaar number</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="marital">Marital Status *</Label>
                <Select
                  value={formData.candidate_details.marital_status}
                  onValueChange={(v) => updateField('candidate_details.marital_status', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {MARITAL_STATUS.map(ms => (
                      <SelectItem key={ms} value={ms} className="capitalize">{ms}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="nationality">Nationality *</Label>
                <Input
                  id="nationality"
                  value={formData.candidate_details.nationality}
                  onChange={(e) => updateField('candidate_details.nationality', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium text-sm text-zinc-700">Current Address *</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Input
                    placeholder="Street / Area *"
                    value={formData.candidate_details.current_address?.street || ''}
                    onChange={(e) => updateField('candidate_details.current_address.street', e.target.value)}
                  />
                </div>
                <Input
                  placeholder="City *"
                  value={formData.candidate_details.current_address?.city || ''}
                  onChange={(e) => updateField('candidate_details.current_address.city', e.target.value)}
                />
                <Input
                  placeholder="State *"
                  value={formData.candidate_details.current_address?.state || ''}
                  onChange={(e) => updateField('candidate_details.current_address.state', e.target.value)}
                />
                <Input
                  placeholder="Pincode *"
                  value={formData.candidate_details.current_address?.pincode || ''}
                  onChange={(e) => updateField('candidate_details.current_address.pincode', e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="font-medium text-sm text-zinc-700">Permanent Address *</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Input
                    placeholder="Street / Area *"
                    value={formData.candidate_details.permanent_address?.street || ''}
                    onChange={(e) => updateField('candidate_details.permanent_address.street', e.target.value)}
                  />
                </div>
                <Input
                  placeholder="City *"
                  value={formData.candidate_details.permanent_address?.city || ''}
                  onChange={(e) => updateField('candidate_details.permanent_address.city', e.target.value)}
                />
                <Input
                  placeholder="State *"
                  value={formData.candidate_details.permanent_address?.state || ''}
                  onChange={(e) => updateField('candidate_details.permanent_address.state', e.target.value)}
                />
                <Input
                  placeholder="Pincode *"
                  value={formData.candidate_details.permanent_address?.pincode || ''}
                  onChange={(e) => updateField('candidate_details.permanent_address.pincode', e.target.value)}
                />
              </div>
            </div>
          </div>
        );

      case 1: // Education
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-500">Add your educational qualifications</p>
              <Button variant="outline" size="sm" onClick={addEducation} data-testid="add-education-btn">
                Add Education
              </Button>
            </div>

            {formData.education.length === 0 ? (
              <div className="text-center py-12 bg-zinc-50 rounded-lg border-2 border-dashed">
                <GraduationCap className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
                <p className="text-zinc-500">No education added yet</p>
                <Button variant="outline" className="mt-4" onClick={addEducation}>
                  Add Education
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {formData.education.map((edu, index) => (
                  <Card key={index} className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 text-zinc-400 hover:text-red-500"
                      onClick={() => removeEducation(index)}
                    >
                      <XCircle className="w-4 h-4" />
                    </Button>
                    <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label>Degree / Qualification *</Label>
                        <Input
                          value={edu.degree}
                          onChange={(e) => {
                            const newEdu = [...formData.education];
                            newEdu[index].degree = e.target.value;
                            setFormData(prev => ({ ...prev, education: newEdu }));
                          }}
                          placeholder="e.g., B.Tech, MBA"
                        />
                      </div>
                      <div>
                        <Label>Institution *</Label>
                        <Input
                          value={edu.institution}
                          onChange={(e) => {
                            const newEdu = [...formData.education];
                            newEdu[index].institution = e.target.value;
                            setFormData(prev => ({ ...prev, education: newEdu }));
                          }}
                          placeholder="University / College name"
                        />
                      </div>
                      <div>
                        <Label>Year of Passing *</Label>
                        <Input
                          value={edu.year}
                          onChange={(e) => {
                            const newEdu = [...formData.education];
                            newEdu[index].year = e.target.value;
                            setFormData(prev => ({ ...prev, education: newEdu }));
                          }}
                          placeholder="2020"
                        />
                      </div>
                      <div>
                        <Label>Percentage / CGPA *</Label>
                        <Input
                          value={edu.percentage}
                          onChange={(e) => {
                            const newEdu = [...formData.education];
                            newEdu[index].percentage = e.target.value;
                            setFormData(prev => ({ ...prev, education: newEdu }));
                          }}
                          placeholder="85% or 8.5 CGPA"
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        );

      case 2: // Work Experience
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-500">Add your previous work experience (if any)</p>
              <Button variant="outline" size="sm" onClick={addEmployment} data-testid="add-experience-btn">
                Add Experience
              </Button>
            </div>

            {formData.employment_history.length === 0 ? (
              <div className="text-center py-12 bg-zinc-50 rounded-lg border-2 border-dashed">
                <Briefcase className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
                <p className="text-zinc-500">No work experience added</p>
                <p className="text-xs text-zinc-400 mt-1">Skip this step if you're a fresher</p>
              </div>
            ) : (
              <div className="space-y-4">
                {formData.employment_history.map((emp, index) => (
                  <Card key={index} className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 text-zinc-400 hover:text-red-500"
                      onClick={() => removeEmployment(index)}
                    >
                      <XCircle className="w-4 h-4" />
                    </Button>
                    <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label>Company Name</Label>
                        <Input
                          value={emp.company}
                          onChange={(e) => {
                            const newEmp = [...formData.employment_history];
                            newEmp[index].company = e.target.value;
                            setFormData(prev => ({ ...prev, employment_history: newEmp }));
                          }}
                          placeholder="Company name"
                        />
                      </div>
                      <div>
                        <Label>Designation</Label>
                        <Input
                          value={emp.designation}
                          onChange={(e) => {
                            const newEmp = [...formData.employment_history];
                            newEmp[index].designation = e.target.value;
                            setFormData(prev => ({ ...prev, employment_history: newEmp }));
                          }}
                          placeholder="Job title"
                        />
                      </div>
                      <div>
                        <Label>From Date</Label>
                        <Input
                          type="date"
                          value={emp.from_date}
                          onChange={(e) => {
                            const newEmp = [...formData.employment_history];
                            newEmp[index].from_date = e.target.value;
                            setFormData(prev => ({ ...prev, employment_history: newEmp }));
                          }}
                        />
                      </div>
                      <div>
                        <Label>To Date</Label>
                        <Input
                          type="date"
                          value={emp.to_date}
                          onChange={(e) => {
                            const newEmp = [...formData.employment_history];
                            newEmp[index].to_date = e.target.value;
                            setFormData(prev => ({ ...prev, employment_history: newEmp }));
                          }}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <Label>Reason for Leaving</Label>
                        <Input
                          value={emp.reason_for_leaving}
                          onChange={(e) => {
                            const newEmp = [...formData.employment_history];
                            newEmp[index].reason_for_leaving = e.target.value;
                            setFormData(prev => ({ ...prev, employment_history: newEmp }));
                          }}
                          placeholder="Optional"
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        );

      case 3: // Bank Details
        return (
          <div className="space-y-6">
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription>
                Your bank details are securely stored and used only for salary processing.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="acc_holder">Account Holder Name *</Label>
                <Input
                  id="acc_holder"
                  data-testid="account-holder-input"
                  value={formData.bank_details.account_holder_name}
                  onChange={(e) => updateField('bank_details.account_holder_name', e.target.value)}
                  placeholder="As per bank records"
                />
              </div>
              <div>
                <Label htmlFor="acc_num">Account Number *</Label>
                <Input
                  id="acc_num"
                  data-testid="account-number-input"
                  value={formData.bank_details.account_number}
                  onChange={(e) => updateField('bank_details.account_number', e.target.value)}
                  placeholder="Enter account number"
                />
              </div>
              <div>
                <Label htmlFor="ifsc">IFSC Code *</Label>
                <Input
                  id="ifsc"
                  data-testid="ifsc-input"
                  value={formData.bank_details.ifsc_code}
                  onChange={(e) => updateField('bank_details.ifsc_code', e.target.value.toUpperCase())}
                  placeholder="e.g., SBIN0001234"
                  maxLength={11}
                />
              </div>
              <div>
                <Label htmlFor="bank_name">Bank Name *</Label>
                <Input
                  id="bank_name"
                  value={formData.bank_details.bank_name}
                  onChange={(e) => updateField('bank_details.bank_name', e.target.value)}
                  placeholder="Bank name"
                />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="branch">Branch *</Label>
                <Input
                  id="branch"
                  value={formData.bank_details.branch}
                  onChange={(e) => updateField('bank_details.branch', e.target.value)}
                  placeholder="Branch name / location"
                />
              </div>
            </div>
          </div>
        );

      case 4: // References
        return (
          <div className="space-y-6">
            {/* Professional Reference */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  Professional Reference *
                </CardTitle>
                <CardDescription>Provide details of a professional contact who can vouch for your work</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Name *</Label>
                  <Input
                    value={formData.professional_reference.name}
                    onChange={(e) => updateField('professional_reference.name', e.target.value)}
                    placeholder="Full name"
                  />
                </div>
                <div>
                  <Label>Phone Number *</Label>
                  <Input
                    value={formData.professional_reference.phone}
                    onChange={(e) => updateField('professional_reference.phone', e.target.value)}
                    placeholder="10-digit mobile number"
                  />
                </div>
                <div>
                  <Label>Company Name *</Label>
                  <Input
                    value={formData.professional_reference.company_name}
                    onChange={(e) => updateField('professional_reference.company_name', e.target.value)}
                    placeholder="Company name"
                  />
                </div>
                <div>
                  <Label>Designation *</Label>
                  <Input
                    value={formData.professional_reference.designation}
                    onChange={(e) => updateField('professional_reference.designation', e.target.value)}
                    placeholder="Their job title"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Personal Reference */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Personal Reference *
                </CardTitle>
                <CardDescription>Provide details of a personal contact (not a family member)</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Name *</Label>
                  <Input
                    value={formData.personal_reference.name}
                    onChange={(e) => updateField('personal_reference.name', e.target.value)}
                    placeholder="Full name"
                  />
                </div>
                <div>
                  <Label>Phone Number *</Label>
                  <Input
                    value={formData.personal_reference.phone}
                    onChange={(e) => updateField('personal_reference.phone', e.target.value)}
                    placeholder="10-digit mobile number"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label>Address *</Label>
                  <Input
                    value={formData.personal_reference.address}
                    onChange={(e) => updateField('personal_reference.address', e.target.value)}
                    placeholder="Full address"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        );

      case 5: // Emergency Contact
        return (
          <div className="space-y-6">
            <Alert>
              <Phone className="h-4 w-4" />
              <AlertDescription>
                This contact will be notified in case of emergencies.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="emerg_name">Contact Name *</Label>
                <Input
                  id="emerg_name"
                  data-testid="emergency-name-input"
                  value={formData.emergency_contact.name}
                  onChange={(e) => updateField('emergency_contact.name', e.target.value)}
                  placeholder="Full name"
                />
              </div>
              <div>
                <Label htmlFor="emerg_phone">Phone Number *</Label>
                <Input
                  id="emerg_phone"
                  data-testid="emergency-phone-input"
                  value={formData.emergency_contact.phone}
                  onChange={(e) => updateField('emergency_contact.phone', e.target.value)}
                  placeholder="10-digit mobile number"
                />
              </div>
              <div>
                <Label htmlFor="emerg_rel">Relationship *</Label>
                <Input
                  id="emerg_rel"
                  value={formData.emergency_contact.relationship}
                  onChange={(e) => updateField('emergency_contact.relationship', e.target.value)}
                  placeholder="e.g., Father, Spouse, Sibling"
                />
              </div>
              <div>
                <Label htmlFor="emerg_addr">Address</Label>
                <Input
                  id="emerg_addr"
                  value={formData.emergency_contact.address}
                  onChange={(e) => updateField('emergency_contact.address', e.target.value)}
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>
        );

      case 6: // Documents
        return (
          <div className="space-y-6">
            <Alert className="border-amber-200 bg-amber-50">
              <Upload className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-amber-800">
                <strong>PAN Card and Aadhaar Card are mandatory.</strong> Upload clear scans or photos. Accepted formats: PDF, JPG, PNG (max 5 MB each).
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { type: 'pan_card', label: 'PAN Card', required: true },
                { type: 'aadhaar', label: 'Aadhaar Card', required: true },
                { type: 'photo', label: 'Passport Photo', required: false },
                { type: 'education_certificate', label: 'Education Certificate', required: false },
                { type: 'experience_letter', label: 'Experience Letter', required: false },
                { type: 'bank_passbook', label: 'Bank Passbook / Statement', required: false },
              ].map(doc => {
                const uploaded = submission?.documents?.find(d => d.type === doc.type);
                const isMissing = doc.required && !uploaded;
                return (
                  <Card key={doc.type} className={uploaded ? 'border-green-200 bg-green-50/50' : isMissing ? 'border-red-200 bg-red-50/30' : ''}>
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between mb-2">
                        <Label className="flex items-center gap-2">
                          {doc.label}
                          {doc.required && <span className="text-red-500 font-bold">*</span>}
                        </Label>
                        {uploaded && <Badge variant="outline" className="text-green-600 border-green-300">Uploaded</Badge>}
                        {isMissing && <Badge variant="outline" className="text-red-600 border-red-300">Required</Badge>}
                      </div>
                      <Input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,.webp"
                        data-testid={`upload-${doc.type}`}
                        onChange={(e) => handleFileUpload(doc.type, e.target.files[0])}
                        className="cursor-pointer"
                      />
                      {uploaded && (
                        <p className="text-xs text-green-600 mt-1">{uploaded.original_filename}</p>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        );

      case 7: // Review & Submit
        const cd = formData.candidate_details;
        const bd = formData.bank_details;
        const pr = formData.professional_reference;
        const per = formData.personal_reference;
        const ec = formData.emergency_contact;
        const uploadedDocs = submission?.documents || [];

        // Helper to show field with validation indicator
        const ReviewField = ({ label, value, required = true }) => {
          const isEmpty = !value || value === '';
          return (
            <div className={isEmpty && required ? 'text-red-600' : ''}>
              <span className="text-zinc-500">{label}:</span>{' '}
              <span className={isEmpty ? 'font-medium' : ''}>{value || (required ? '⚠ Missing' : 'N/A')}</span>
            </div>
          );
        };

        return (
          <div className="space-y-6">
            {/* Personal Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Personal Details</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <ReviewField label="First Name" value={cd.first_name} />
                <ReviewField label="Last Name" value={cd.last_name} />
                <ReviewField label="Date of Birth" value={cd.date_of_birth} />
                <ReviewField label="Gender" value={cd.gender} />
                <ReviewField label="Blood Group" value={cd.blood_group} />
                <ReviewField label="Marital Status" value={cd.marital_status} />
                <ReviewField label="Nationality" value={cd.nationality} />
                <ReviewField label="Phone" value={cd.phone} />
                <ReviewField label="Alternate Phone" value={cd.alternate_phone} />
                <ReviewField label="PAN Number" value={cd.pan_number} />
                <ReviewField label="Aadhaar Number" value={cd.aadhaar_number} />
                <ReviewField label="Passport Number" value={cd.passport_number} required={false} />
                <ReviewField label="Driving License" value={cd.driving_license} required={false} />
              </CardContent>
            </Card>

            {/* Current Address */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Current Address</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div className="col-span-2"><ReviewField label="Street/Area" value={cd.current_address?.street} /></div>
                <ReviewField label="City" value={cd.current_address?.city} />
                <ReviewField label="State" value={cd.current_address?.state} />
                <ReviewField label="Pincode" value={cd.current_address?.pincode} />
              </CardContent>
            </Card>

            {/* Permanent Address */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Permanent Address</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div className="col-span-2"><ReviewField label="Street/Area" value={cd.permanent_address?.street} /></div>
                <ReviewField label="City" value={cd.permanent_address?.city} />
                <ReviewField label="State" value={cd.permanent_address?.state} />
                <ReviewField label="Pincode" value={cd.permanent_address?.pincode} />
              </CardContent>
            </Card>

            {/* Education */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Education ({formData.education?.length || 0})</CardTitle>
              </CardHeader>
              <CardContent>
                {formData.education?.length > 0 ? (
                  <div className="space-y-3">
                    {formData.education.map((edu, idx) => (
                      <div key={idx} className="border-b pb-2 last:border-0 text-sm grid grid-cols-2 gap-2">
                        <ReviewField label="Degree" value={edu.degree} />
                        <ReviewField label="Institution" value={edu.institution} />
                        <ReviewField label="Year" value={edu.year} />
                        <ReviewField label="Percentage/CGPA" value={edu.percentage} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-red-600 text-sm">⚠ No education added (Required)</p>
                )}
              </CardContent>
            </Card>

            {/* Employment History */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Employment History ({formData.employment_history?.length || 0})</CardTitle>
              </CardHeader>
              <CardContent>
                {formData.employment_history?.length > 0 ? (
                  <div className="space-y-3">
                    {formData.employment_history.map((emp, idx) => (
                      <div key={idx} className="border-b pb-2 last:border-0 text-sm grid grid-cols-2 gap-2">
                        <ReviewField label="Company" value={emp.company} />
                        <ReviewField label="Designation" value={emp.designation} />
                        <ReviewField label="From" value={emp.from_date} />
                        <ReviewField label="To" value={emp.to_date} />
                        <div className="col-span-2"><ReviewField label="Reason for Leaving" value={emp.reason_for_leaving} required={false} /></div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-500 text-sm">No employment history (Optional for freshers)</p>
                )}
              </CardContent>
            </Card>

            {/* Bank Details */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Bank Details</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <ReviewField label="Account Holder Name" value={bd.account_holder_name} />
                <div><span className="text-zinc-500">Account Number:</span> {bd.account_number ? `****${bd.account_number.slice(-4)}` : <span className="text-red-600 font-medium">⚠ Missing</span>}</div>
                <ReviewField label="IFSC Code" value={bd.ifsc_code} />
                <ReviewField label="Bank Name" value={bd.bank_name} />
                <ReviewField label="Branch" value={bd.branch} />
              </CardContent>
            </Card>

            {/* Professional Reference */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Professional Reference</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <ReviewField label="Name" value={pr.name} />
                <ReviewField label="Phone" value={pr.phone} />
                <ReviewField label="Company Name" value={pr.company_name} />
                <ReviewField label="Designation" value={pr.designation} />
              </CardContent>
            </Card>

            {/* Personal Reference */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Personal Reference</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <ReviewField label="Name" value={per.name} />
                <ReviewField label="Phone" value={per.phone} />
                <div className="col-span-2"><ReviewField label="Address" value={per.address} /></div>
              </CardContent>
            </Card>

            {/* Emergency Contact */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Emergency Contact</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <ReviewField label="Name" value={ec.name} />
                <ReviewField label="Phone" value={ec.phone} />
                <ReviewField label="Relationship" value={ec.relationship} />
                <ReviewField label="Address" value={ec.address} required={false} />
              </CardContent>
            </Card>

            {/* Uploaded Documents */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Uploaded Documents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {/* Required Documents */}
                  <div className="flex items-center gap-2">
                    {uploadedDocs.some(d => d.type === 'pan_card') ? (
                      <Badge variant="outline" className="text-green-600 border-green-300"><Check className="w-3 h-3 mr-1" />PAN Card</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-300"><XCircle className="w-3 h-3 mr-1" />PAN Card (Required)</Badge>
                    )}
                    {uploadedDocs.some(d => d.type === 'aadhaar') ? (
                      <Badge variant="outline" className="text-green-600 border-green-300"><Check className="w-3 h-3 mr-1" />Aadhaar Card</Badge>
                    ) : (
                      <Badge variant="outline" className="text-red-600 border-red-300"><XCircle className="w-3 h-3 mr-1" />Aadhaar Card (Required)</Badge>
                    )}
                  </div>
                  {/* Optional Documents */}
                  {uploadedDocs.filter(d => !['pan_card', 'aadhaar'].includes(d.type)).length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {uploadedDocs.filter(d => !['pan_card', 'aadhaar'].includes(d.type)).map(doc => (
                        <Badge key={doc.id} variant="secondary">
                          <Check className="w-3 h-3 mr-1" />
                          {doc.type.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className={!formData.declaration_signed ? 'border-amber-200' : 'border-green-200'}>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Self Declaration *
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="bg-zinc-50 rounded-lg p-4 mb-4 text-sm text-zinc-600 leading-relaxed">
                  <p className="mb-3">By submitting this form, I declare that:</p>
                  <ol className="list-decimal ml-4 space-y-2">
                    <li>All the information provided is true, complete, and correct to the best of my knowledge and belief.</li>
                    <li>I have not withheld any material information that may affect my employment.</li>
                    <li>I understand that any false statement, misrepresentation, or omission of facts may result in rejection of my application or termination of employment.</li>
                    <li>I authorize D&V Business Consulting to verify all information provided and conduct background checks as deemed necessary.</li>
                    <li>I consent to the storage and processing of my personal data as per company policy and applicable data protection laws.</li>
                  </ol>
                </div>
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="declaration"
                    data-testid="declaration-checkbox"
                    checked={formData.declaration_signed}
                    onCheckedChange={(checked) => updateField('declaration_signed', checked)}
                  />
                  <Label htmlFor="declaration" className="text-sm leading-relaxed cursor-pointer font-medium">
                    I have read and agree to the above declaration. I confirm that all information provided is accurate.
                  </Label>
                </div>
              </CardContent>
            </Card>
          </div>
        );

      default:
        return null;
    }
  };

  // Logo URL - same as email templates
  const LOGO_URL = "https://customer-assets.emergentagent.com/job_30a69dc1-a599-4a88-9d0e-e1c06b1b2008/artifacts/tbs0jexj_1001419196.png";

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 to-zinc-100">
      {/* Header */}
      <div className="bg-white py-6 px-4 border-b-4 border-orange-500">
        <div className="max-w-4xl mx-auto text-center">
          <img
            src={LOGO_URL}
            alt="D&V Business Consulting"
            className="h-20 w-auto mx-auto mb-3"
          />
          <p className="text-zinc-600 text-sm mt-2">
            Welcome, {submission?.candidate_name}! Please complete your onboarding details.
          </p>
        </div>
      </div>

      {/* Progress */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">
              Step {currentStep + 1} of {STEPS.length}: {STEPS[currentStep].title}
            </span>
            {lastSaved && (
              <span className="text-xs text-zinc-400">
                {saving ? 'Saving...' : `Last saved ${lastSaved.toLocaleTimeString()}`}
              </span>
            )}
          </div>
          <Progress value={((currentStep + 1) / STEPS.length) * 100} className="h-2" />
          
          {/* Step indicators */}
          <div className="flex justify-between mt-4 overflow-x-auto pb-2">
            {STEPS.map((step, index) => {
              const StepIcon = step.icon;
              const isActive = index === currentStep;
              
              // Check if step is actually complete based on data
              const isStepComplete = () => {
                const cd = formData.candidate_details;
                const bd = formData.bank_details;
                const pr = formData.professional_reference;
                const per = formData.personal_reference;
                const ec = formData.emergency_contact;
                const uploadedDocs = submission?.documents || [];
                
                // Helper to check if value is non-empty
                const hasValue = (val) => val && val.toString().trim() !== '';
                
                switch (index) {
                  case 0: // Personal Details - includes validation
                    return hasValue(cd.first_name) && hasValue(cd.last_name) && 
                           isValidIndianPhone(cd.phone) && isValidIndianPhone(cd.alternate_phone) && 
                           hasValue(cd.date_of_birth) && hasValue(cd.gender) && hasValue(cd.blood_group) && hasValue(cd.marital_status) && 
                           isValidPAN(cd.pan_number) && isValidAadhaar(cd.aadhaar_number) &&
                           hasValue(cd.current_address?.street) && hasValue(cd.current_address?.city) && 
                           hasValue(cd.current_address?.state) && isValidPincode(cd.current_address?.pincode) &&
                           hasValue(cd.permanent_address?.street) && hasValue(cd.permanent_address?.city) && 
                           hasValue(cd.permanent_address?.state) && isValidPincode(cd.permanent_address?.pincode);
                  case 1: // Education - at least one complete entry
                    return formData.education && formData.education.length > 0 && 
                           formData.education.every(e => hasValue(e.degree) && hasValue(e.institution) && hasValue(e.year) && hasValue(e.percentage));
                  case 2: // Work Experience - Only green if has valid entries, gray if empty
                    if (!formData.employment_history?.length) return false; // Empty = not green
                    return formData.employment_history.every(e => hasValue(e.company) && hasValue(e.designation) && hasValue(e.from_date));
                  case 3: // Bank Details - includes IFSC validation
                    return hasValue(bd.account_holder_name) && hasValue(bd.account_number) && isValidIFSC(bd.ifsc_code) && 
                           hasValue(bd.bank_name) && hasValue(bd.branch);
                  case 4: // References - includes phone validation
                    return hasValue(pr.name) && isValidIndianPhone(pr.phone) && hasValue(pr.company_name) && hasValue(pr.designation) &&
                           hasValue(per.name) && isValidIndianPhone(per.phone) && hasValue(per.address);
                  case 5: // Emergency Contact - includes phone validation
                    return hasValue(ec.name) && isValidIndianPhone(ec.phone) && hasValue(ec.relationship);
                  case 6: // Documents - Must have PAN and Aadhaar
                    return uploadedDocs.some(d => d.type === 'pan_card') && uploadedDocs.some(d => d.type === 'aadhaar');
                  case 7: // Review & Submit
                    return formData.declaration_signed === true;
                  default:
                    return false;
                }
              };
              
              const isComplete = isStepComplete();
              
              return (
                <button
                  key={step.id}
                  onClick={() => setCurrentStep(index)}
                  className={`flex flex-col items-center gap-1 text-xs transition-colors min-w-[40px] ${
                    isActive ? 'text-black' : isComplete ? 'text-green-600' : 'text-zinc-400'
                  }`}
                >
                  <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    isActive ? 'bg-black text-white' : isComplete ? 'bg-green-100' : 'bg-zinc-100'
                  }`}>
                    {isComplete ? <Check className="w-3 h-3 sm:w-4 sm:h-4" /> : (index + 1)}
                  </div>
                  <span className="hidden md:block text-[10px] text-center leading-tight">{step.title}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Revision Alert */}
      {submission?.status === 'revision_requested' && (
        <div className="max-w-4xl mx-auto px-4 mt-4">
          <Alert className="border-amber-200 bg-amber-50">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800">
              <strong>Revision Requested:</strong>{' '}
              {submission.revision_history?.[submission.revision_history.length - 1]?.reason || 'Please update your details.'}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Form Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {React.createElement(STEPS[currentStep].icon, { className: 'w-5 h-5' })}
              {STEPS[currentStep].title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {renderStepContent()}
          </CardContent>
          <CardFooter className="flex justify-between border-t pt-6">
            <Button
              variant="outline"
              onClick={() => setCurrentStep(prev => prev - 1)}
              disabled={currentStep === 0}
              data-testid="prev-step-btn"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => handleSave(false)} disabled={saving}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                Save Progress
              </Button>

              {currentStep === STEPS.length - 1 ? (
                <Button
                  onClick={handleSubmit}
                  disabled={submitting || !formData.declaration_signed}
                  data-testid="submit-form-btn"
                  className="bg-green-600 hover:bg-green-700"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Check className="w-4 h-4 mr-1" />}
                  Submit Application
                </Button>
              ) : (
                <Button onClick={() => setCurrentStep(prev => prev + 1)} data-testid="next-step-btn">
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              )}
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
};

export default CandidateOnboardingForm;
