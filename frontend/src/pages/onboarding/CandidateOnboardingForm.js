import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Checkbox } from '../../components/ui/checkbox';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Progress } from '../../components/ui/progress';
import { 
  User, Building2, Phone, FileText, AlertTriangle,
  ChevronRight, ChevronLeft, Upload, Check, Loader2, 
  Shield, CheckCircle2, Download, FileDown, Camera
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import ProfilePhotoUpload from '../../components/ProfilePhotoUpload';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Simplified 4 Steps
const STEPS = [
  { id: 'personal', title: 'Personal Details', icon: User },
  { id: 'address_bank', title: 'Address & Bank', icon: Building2 },
  { id: 'emergency_docs', title: 'Emergency & Documents', icon: Phone },
  { id: 'declaration', title: 'Declaration & Submit', icon: Shield },
];

// Validation helpers - Only phone and email
const isValidPhone = (phone) => {
  if (!phone) return false;
  const cleaned = phone.replace(/[\s-]/g, '');
  return /^\d{10}$/.test(cleaned);
};

const isValidEmail = (email) => {
  if (!email) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

const isValidPincode = (pincode) => {
  if (!pincode) return false;
  return /^\d{6}$/.test(pincode);
};

// Declaration items
const DECLARATION_ITEMS = [
  { id: 'info_true', text: 'I confirm that all information provided is true and accurate to the best of my knowledge.', type: 'do' },
  { id: 'bg_verify', text: 'I agree to background verification of my credentials and employment history.', type: 'do' },
  { id: 'confidentiality', text: 'I will maintain confidentiality of company information during and after employment.', type: 'do' },
  { id: 'policies', text: 'I agree to abide by company policies, code of conduct, and HR guidelines.', type: 'do' },
  { id: 'no_legal', text: 'I declare that I have no pending legal cases or criminal proceedings against me.', type: 'dont' },
  { id: 'no_termination', text: 'I confirm that I have not been terminated from any previous employment for misconduct.', type: 'dont' },
];

const CandidateOnboardingForm = () => {
  const { token } = useParams();
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [lastSaved, setLastSaved] = useState(null);
  const [touchedFields, setTouchedFields] = useState({});
  const formRef = useRef(null);

  // Form data - Simplified structure
  const [formData, setFormData] = useState({
    candidate_details: {
      first_name: '',
      last_name: '',
      date_of_birth: '',
      phone: '',
      email: '',
      pan_number: '',
      aadhaar_number: '',
      profile_photo_url: '',
      current_address: { street: '', city: '', state: '', pincode: '' },
      permanent_address: { street: '', city: '', state: '', pincode: '' },
    },
    bank_details: {
      account_number: '',
      ifsc_code: '',
      bank_name: '',
      branch: '',
      account_holder_name: '',
    },
    emergency_contact: {
      name: '',
      phone: '',
    },
    declarations: {},
  });

  // Query: Fetch submission data
  const { data: submission, isLoading: loading, error: fetchError } = useQuery({
    queryKey: ['onboarding-public', token],
    queryFn: async () => {
      const response = await axios.get(`${API}/onboarding/public/${token}`);
      return response.data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const error = fetchError?.response?.data?.detail || (fetchError ? 'Unable to load the form. Please check your link.' : null);

  // Pre-fill form with existing data
  useEffect(() => {
    if (!submission) return;
    
    if (submission.candidate_details) {
      setFormData(prev => ({
        ...prev,
        candidate_details: { ...prev.candidate_details, ...submission.candidate_details }
      }));
    }
    if (submission.bank_details) {
      setFormData(prev => ({
        ...prev,
        bank_details: { ...prev.bank_details, ...submission.bank_details }
      }));
    }
    if (submission.emergency_contact) {
      setFormData(prev => ({
        ...prev,
        emergency_contact: { ...prev.emergency_contact, ...submission.emergency_contact }
      }));
    }
    if (submission.declarations) {
      setFormData(prev => ({ ...prev, declarations: submission.declarations }));
    }
  }, [submission]);

  // Mutation: Save form progress
  const saveMutation = useMutation({
    mutationFn: async (data) => {
      return axios.put(`${API}/onboarding/public/${token}`, data);
    },
    onSuccess: () => {
      setLastSaved(new Date());
      queryClient.invalidateQueries({ queryKey: ['onboarding-public', token] });
    },
  });

  // Auto-save with debounce
  const debouncedSave = useCallback(
    (() => {
      let timeoutId;
      return (data) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          saveMutation.mutate(data);
        }, 2000);
      };
    })(),
    [saveMutation]
  );

  useEffect(() => {
    if (submission && !loading) {
      debouncedSave(formData);
    }
  }, [formData, submission, loading, debouncedSave]);

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (data) => {
      return axios.post(`${API}/onboarding/public/${token}/submit`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-public', token] });
    },
  });

  const handleSubmit = async () => {
    // Validate all declarations are checked
    const allDeclarationsChecked = DECLARATION_ITEMS.every(item => formData.declarations[item.id]);
    if (!allDeclarationsChecked) {
      toast.error('Please accept all declaration items');
      return;
    }

    // Validate documents
    const uploadedDocs = submission?.documents || [];
    const requiredDocs = ['pan_card', 'aadhaar', 'cv'];
    const missingDocs = requiredDocs.filter(d => !uploadedDocs.find(doc => doc.type === d));
    if (missingDocs.length > 0) {
      toast.error(`Please upload required documents: ${missingDocs.map(d => d.replace('_', ' ').toUpperCase()).join(', ')}`);
      setCurrentStep(2);
      return;
    }

    const submissionData = {
      ...formData,
      declaration: {
        signed: true,
        signed_at: new Date().toISOString(),
        items: formData.declarations,
      }
    };

    try {
      await submitMutation.mutateAsync(submissionData);
      toast.success('Form submitted successfully! Thank you!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    }
  };

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ docType, file }) => {
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);
      return axios.post(
        `${API}/onboarding/public/${token}/upload?document_type=${docType}`,
        formDataUpload,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
    },
    onSuccess: (data, variables) => {
      toast.success(`${variables.docType.replace('_', ' ')} uploaded successfully`);
      queryClient.invalidateQueries({ queryKey: ['onboarding-public', token] });
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to upload document');
    },
  });

  const handleFileUpload = async (docType, file) => {
    if (!file) return;
    setSaving(true);
    try {
      await uploadMutation.mutateAsync({ docType, file });
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

  const handleFieldBlur = (fieldPath) => {
    setTouchedFields(prev => ({ ...prev, [fieldPath]: true }));
  };

  const isFieldTouched = (fieldPath) => touchedFields[fieldPath] === true;

  // Step validation
  const validateCurrentStep = () => {
    const cd = formData.candidate_details;
    const bd = formData.bank_details;
    const ec = formData.emergency_contact;

    switch (currentStep) {
      case 0: // Personal Details
        if (!cd.first_name?.trim()) { toast.error('First Name is required'); return false; }
        if (!cd.last_name?.trim()) { toast.error('Last Name is required'); return false; }
        if (!cd.date_of_birth) { toast.error('Date of Birth is required'); return false; }
        if (!isValidPhone(cd.phone)) { toast.error('Enter valid 10-digit Phone number'); return false; }
        if (!isValidEmail(cd.email)) { toast.error('Enter valid Email address'); return false; }
        if (!cd.pan_number?.trim()) { toast.error('PAN Number is required'); return false; }
        if (!cd.aadhaar_number?.trim()) { toast.error('Aadhaar Number is required'); return false; }
        if (!cd.profile_photo_url) { toast.error('Profile Photo is required'); return false; }
        return true;

      case 1: // Address & Bank
        if (!cd.current_address?.street?.trim()) { toast.error('Current Address Street is required'); return false; }
        if (!cd.current_address?.city?.trim()) { toast.error('Current Address City is required'); return false; }
        if (!cd.current_address?.state?.trim()) { toast.error('Current Address State is required'); return false; }
        if (!isValidPincode(cd.current_address?.pincode)) { toast.error('Enter valid 6-digit Pincode for Current Address'); return false; }
        if (!cd.permanent_address?.street?.trim()) { toast.error('Permanent Address Street is required'); return false; }
        if (!cd.permanent_address?.city?.trim()) { toast.error('Permanent Address City is required'); return false; }
        if (!cd.permanent_address?.state?.trim()) { toast.error('Permanent Address State is required'); return false; }
        if (!isValidPincode(cd.permanent_address?.pincode)) { toast.error('Enter valid 6-digit Pincode for Permanent Address'); return false; }
        if (!bd.account_holder_name?.trim()) { toast.error('Account Holder Name is required'); return false; }
        if (!bd.account_number?.trim()) { toast.error('Account Number is required'); return false; }
        if (!bd.ifsc_code?.trim()) { toast.error('IFSC Code is required'); return false; }
        if (!bd.bank_name?.trim()) { toast.error('Bank Name is required'); return false; }
        if (!bd.branch?.trim()) { toast.error('Branch Name is required'); return false; }
        return true;

      case 2: // Emergency & Documents
        if (!ec.name?.trim()) { toast.error('Emergency Contact Name is required'); return false; }
        if (!isValidPhone(ec.phone)) { toast.error('Enter valid 10-digit Emergency Contact Phone'); return false; }
        const uploadedDocs = submission?.documents || [];
        const requiredDocs = ['pan_card', 'aadhaar', 'cv'];
        const missingDocs = requiredDocs.filter(d => !uploadedDocs.find(doc => doc.type === d));
        if (missingDocs.length > 0) {
          toast.error(`Please upload: ${missingDocs.map(d => d.replace('_', ' ').toUpperCase()).join(', ')}`);
          return false;
        }
        return true;

      case 3: // Declaration
        const allChecked = DECLARATION_ITEMS.every(item => formData.declarations[item.id]);
        if (!allChecked) { toast.error('Please accept all declaration items'); return false; }
        return true;

      default:
        return true;
    }
  };

  const handleNext = () => {
    if (validateCurrentStep()) {
      saveMutation.mutate(formData);
      setCurrentStep(prev => Math.min(prev + 1, STEPS.length - 1));
      window.scrollTo(0, 0);
    }
  };

  const handlePrev = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
    window.scrollTo(0, 0);
  };

  // Download blank form as PDF
  const downloadBlankForm = () => {
    const content = `
D&V BUSINESS CONSULTING - EMPLOYEE ONBOARDING FORM
====================================================

PERSONAL DETAILS
----------------
First Name: _______________________
Last Name: ________________________
Date of Birth: ____________________
Mobile Number: ____________________
Email Address: ____________________
PAN Number: _______________________
Aadhaar Number: ___________________

CURRENT ADDRESS
---------------
Street: ___________________________
City: _____________________________
State: ____________________________
Pincode: __________________________

PERMANENT ADDRESS
-----------------
Street: ___________________________
City: _____________________________
State: ____________________________
Pincode: __________________________

BANK DETAILS
------------
Account Holder Name: ______________
Account Number: ___________________
IFSC Code: ________________________
Bank Name: ________________________
Branch: ___________________________

EMERGENCY CONTACT
-----------------
Name: _____________________________
Phone: ____________________________

DOCUMENTS CHECKLIST
-------------------
[ ] PAN Card
[ ] Aadhaar Card
[ ] CV/Resume
[ ] Passport Photo

DECLARATION
-----------
[ ] I confirm that all information provided is true and accurate.
[ ] I agree to background verification.
[ ] I will maintain confidentiality of company information.
[ ] I agree to abide by company policies.
[ ] I declare that I have no pending legal cases.
[ ] I confirm no termination for misconduct from previous employment.

Signature: _________________ Date: _________________

====================================================
Please fill this form and upload at: ${window.location.href}
    `;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'DV_Onboarding_Form_Blank.txt';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Blank form downloaded!');
  };

  // Download filled form as PDF
  const downloadFilledForm = () => {
    const cd = formData.candidate_details;
    const bd = formData.bank_details;
    const ec = formData.emergency_contact;
    const docs = submission?.documents || [];

    const content = `
D&V BUSINESS CONSULTING - EMPLOYEE ONBOARDING FORM (FILLED)
============================================================

PERSONAL DETAILS
----------------
First Name: ${cd.first_name || 'N/A'}
Last Name: ${cd.last_name || 'N/A'}
Date of Birth: ${cd.date_of_birth || 'N/A'}
Mobile Number: ${cd.phone || 'N/A'}
Email Address: ${cd.email || 'N/A'}
PAN Number: ${cd.pan_number || 'N/A'}
Aadhaar Number: ${cd.aadhaar_number || 'N/A'}

CURRENT ADDRESS
---------------
Street: ${cd.current_address?.street || 'N/A'}
City: ${cd.current_address?.city || 'N/A'}
State: ${cd.current_address?.state || 'N/A'}
Pincode: ${cd.current_address?.pincode || 'N/A'}

PERMANENT ADDRESS
-----------------
Street: ${cd.permanent_address?.street || 'N/A'}
City: ${cd.permanent_address?.city || 'N/A'}
State: ${cd.permanent_address?.state || 'N/A'}
Pincode: ${cd.permanent_address?.pincode || 'N/A'}

BANK DETAILS
------------
Account Holder Name: ${bd.account_holder_name || 'N/A'}
Account Number: ${bd.account_number || 'N/A'}
IFSC Code: ${bd.ifsc_code || 'N/A'}
Bank Name: ${bd.bank_name || 'N/A'}
Branch: ${bd.branch || 'N/A'}

EMERGENCY CONTACT
-----------------
Name: ${ec.name || 'N/A'}
Phone: ${ec.phone || 'N/A'}

DOCUMENTS UPLOADED
------------------
${docs.map(d => `[✓] ${d.type.replace('_', ' ').toUpperCase()}`).join('\n') || 'No documents uploaded'}

DECLARATION
-----------
${DECLARATION_ITEMS.map(item => `[${formData.declarations[item.id] ? '✓' : ' '}] ${item.text}`).join('\n')}

============================================================
Form Generated: ${new Date().toLocaleString()}
Submission Status: ${submission?.status || 'Draft'}
    `;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DV_Onboarding_${cd.first_name || 'Form'}_${cd.last_name || ''}_Filled.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Filled form downloaded!');
  };

  // Copy same address
  const copyCurrentToPermanent = () => {
    setFormData(prev => ({
      ...prev,
      candidate_details: {
        ...prev.candidate_details,
        permanent_address: { ...prev.candidate_details.current_address }
      }
    }));
    toast.success('Address copied!');
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-amber-500 mx-auto mb-4" />
          <p className="text-neutral-600">Loading your form...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle className="text-red-600 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Error Loading Form
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-neutral-600">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Already submitted
  if (submission?.status === 'submitted') {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle className="text-green-600 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" />
              Form Already Submitted
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-neutral-600">
              Thank you! Your onboarding form has been submitted successfully.
              Our HR team will review your details and get back to you soon.
            </p>
            <Button onClick={downloadFilledForm} variant="outline" className="w-full">
              <Download className="w-4 h-4 mr-2" />
              Download Your Submitted Form
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const progress = ((currentStep + 1) / STEPS.length) * 100;
  const cd = formData.candidate_details;
  const bd = formData.bank_details;
  const ec = formData.emergency_contact;
  const uploadedDocs = submission?.documents || [];

  return (
    <div className="min-h-screen bg-neutral-50 py-8 px-4" ref={formRef}>
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">Employee Onboarding</h1>
          <p className="text-neutral-500">D&V Business Consulting</p>
          
          {/* Download buttons */}
          <div className="flex justify-center gap-3 mt-4">
            <Button variant="outline" size="sm" onClick={downloadBlankForm}>
              <FileDown className="w-4 h-4 mr-2" />
              Download Blank Form
            </Button>
            <Button variant="outline" size="sm" onClick={downloadFilledForm}>
              <Download className="w-4 h-4 mr-2" />
              Download Filled Form
            </Button>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between mb-2">
            {STEPS.map((step, idx) => (
              <div 
                key={step.id}
                className={`flex flex-col items-center ${idx <= currentStep ? 'text-amber-600' : 'text-neutral-400'}`}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-1 ${
                  idx < currentStep ? 'bg-amber-500 text-white' : 
                  idx === currentStep ? 'bg-amber-100 text-amber-600 border-2 border-amber-500' : 
                  'bg-neutral-200 text-neutral-500'
                }`}>
                  {idx < currentStep ? <Check className="w-5 h-5" /> : <step.icon className="w-5 h-5" />}
                </div>
                <span className="text-xs font-medium hidden sm:block">{step.title}</span>
              </div>
            ))}
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Auto-save indicator */}
        {lastSaved && (
          <div className="text-xs text-neutral-500 text-center mb-4">
            Auto-saved at {lastSaved.toLocaleTimeString()}
          </div>
        )}

        {/* Form Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {React.createElement(STEPS[currentStep].icon, { className: "w-5 h-5 text-amber-500" })}
              {STEPS[currentStep].title}
            </CardTitle>
            <CardDescription>Step {currentStep + 1} of {STEPS.length}</CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Step 1: Personal Details */}
            {currentStep === 0 && (
              <div className="space-y-6">
                {/* Profile Photo */}
                <div className="flex justify-center">
                  <ProfilePhotoUpload
                    currentPhotoUrl={cd.profile_photo_url}
                    onPhotoChange={(url) => updateField('candidate_details.profile_photo_url', url)}
                    uploadEndpoint={`${API}/onboarding/public/${token}/upload-photo`}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name <span className="text-red-500">*</span></Label>
                    <Input
                      id="first_name"
                      value={cd.first_name}
                      onChange={(e) => updateField('candidate_details.first_name', e.target.value)}
                      onBlur={() => handleFieldBlur('first_name')}
                      placeholder="Enter first name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name <span className="text-red-500">*</span></Label>
                    <Input
                      id="last_name"
                      value={cd.last_name}
                      onChange={(e) => updateField('candidate_details.last_name', e.target.value)}
                      placeholder="Enter last name"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="dob">Date of Birth <span className="text-red-500">*</span></Label>
                    <Input
                      id="dob"
                      type="date"
                      value={cd.date_of_birth}
                      onChange={(e) => updateField('candidate_details.date_of_birth', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Mobile Number <span className="text-red-500">*</span></Label>
                    <Input
                      id="phone"
                      value={cd.phone}
                      onChange={(e) => updateField('candidate_details.phone', e.target.value)}
                      onBlur={() => handleFieldBlur('phone')}
                      placeholder="10-digit mobile number"
                      maxLength={10}
                    />
                    {isFieldTouched('phone') && cd.phone && !isValidPhone(cd.phone) && (
                      <p className="text-xs text-red-500">Enter valid 10-digit phone number</p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email Address <span className="text-red-500">*</span></Label>
                  <Input
                    id="email"
                    type="email"
                    value={cd.email}
                    onChange={(e) => updateField('candidate_details.email', e.target.value)}
                    onBlur={() => handleFieldBlur('email')}
                    placeholder="your.email@example.com"
                  />
                  {isFieldTouched('email') && cd.email && !isValidEmail(cd.email) && (
                    <p className="text-xs text-red-500">Enter valid email address</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="pan">PAN Number <span className="text-red-500">*</span></Label>
                    <Input
                      id="pan"
                      value={cd.pan_number}
                      onChange={(e) => updateField('candidate_details.pan_number', e.target.value.toUpperCase())}
                      placeholder="ABCDE1234F"
                      maxLength={10}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="aadhaar">Aadhaar Number <span className="text-red-500">*</span></Label>
                    <Input
                      id="aadhaar"
                      value={cd.aadhaar_number}
                      onChange={(e) => updateField('candidate_details.aadhaar_number', e.target.value)}
                      placeholder="12-digit Aadhaar number"
                      maxLength={12}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Address & Bank */}
            {currentStep === 1 && (
              <div className="space-y-6">
                {/* Current Address */}
                <div>
                  <h3 className="font-semibold text-neutral-800 mb-3">Current Address</h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Street Address <span className="text-red-500">*</span></Label>
                      <Input
                        value={cd.current_address?.street || ''}
                        onChange={(e) => updateField('candidate_details.current_address.street', e.target.value)}
                        placeholder="House/Flat No., Street Name"
                      />
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>City <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.current_address?.city || ''}
                          onChange={(e) => updateField('candidate_details.current_address.city', e.target.value)}
                          placeholder="City"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>State <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.current_address?.state || ''}
                          onChange={(e) => updateField('candidate_details.current_address.state', e.target.value)}
                          placeholder="State"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Pincode <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.current_address?.pincode || ''}
                          onChange={(e) => updateField('candidate_details.current_address.pincode', e.target.value)}
                          placeholder="6-digit pincode"
                          maxLength={6}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Permanent Address */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-neutral-800">Permanent Address</h3>
                    <Button type="button" variant="ghost" size="sm" onClick={copyCurrentToPermanent}>
                      Same as Current
                    </Button>
                  </div>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Street Address <span className="text-red-500">*</span></Label>
                      <Input
                        value={cd.permanent_address?.street || ''}
                        onChange={(e) => updateField('candidate_details.permanent_address.street', e.target.value)}
                        placeholder="House/Flat No., Street Name"
                      />
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>City <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.permanent_address?.city || ''}
                          onChange={(e) => updateField('candidate_details.permanent_address.city', e.target.value)}
                          placeholder="City"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>State <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.permanent_address?.state || ''}
                          onChange={(e) => updateField('candidate_details.permanent_address.state', e.target.value)}
                          placeholder="State"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Pincode <span className="text-red-500">*</span></Label>
                        <Input
                          value={cd.permanent_address?.pincode || ''}
                          onChange={(e) => updateField('candidate_details.permanent_address.pincode', e.target.value)}
                          placeholder="6-digit pincode"
                          maxLength={6}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bank Details */}
                <div>
                  <h3 className="font-semibold text-neutral-800 mb-3">Bank Details</h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Account Holder Name <span className="text-red-500">*</span></Label>
                      <Input
                        value={bd.account_holder_name}
                        onChange={(e) => updateField('bank_details.account_holder_name', e.target.value)}
                        placeholder="Name as per bank records"
                      />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Account Number <span className="text-red-500">*</span></Label>
                        <Input
                          value={bd.account_number}
                          onChange={(e) => updateField('bank_details.account_number', e.target.value)}
                          placeholder="Bank account number"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>IFSC Code <span className="text-red-500">*</span></Label>
                        <Input
                          value={bd.ifsc_code}
                          onChange={(e) => updateField('bank_details.ifsc_code', e.target.value.toUpperCase())}
                          placeholder="IFSC Code"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Bank Name <span className="text-red-500">*</span></Label>
                        <Input
                          value={bd.bank_name}
                          onChange={(e) => updateField('bank_details.bank_name', e.target.value)}
                          placeholder="Bank name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Branch <span className="text-red-500">*</span></Label>
                        <Input
                          value={bd.branch}
                          onChange={(e) => updateField('bank_details.branch', e.target.value)}
                          placeholder="Branch name"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Emergency & Documents */}
            {currentStep === 2 && (
              <div className="space-y-6">
                {/* Emergency Contact */}
                <div>
                  <h3 className="font-semibold text-neutral-800 mb-3">Emergency Contact</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Contact Name <span className="text-red-500">*</span></Label>
                      <Input
                        value={ec.name}
                        onChange={(e) => updateField('emergency_contact.name', e.target.value)}
                        placeholder="Emergency contact name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Contact Phone <span className="text-red-500">*</span></Label>
                      <Input
                        value={ec.phone}
                        onChange={(e) => updateField('emergency_contact.phone', e.target.value)}
                        onBlur={() => handleFieldBlur('emergency_phone')}
                        placeholder="10-digit phone number"
                        maxLength={10}
                      />
                      {isFieldTouched('emergency_phone') && ec.phone && !isValidPhone(ec.phone) && (
                        <p className="text-xs text-red-500">Enter valid 10-digit phone number</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Document Upload */}
                <div>
                  <h3 className="font-semibold text-neutral-800 mb-3">Upload Documents</h3>
                  <p className="text-sm text-neutral-500 mb-4">All documents are mandatory. Accepted formats: PDF, JPG, PNG (Max 5MB)</p>
                  
                  <div className="space-y-4">
                    {[
                      { type: 'pan_card', label: 'PAN Card' },
                      { type: 'aadhaar', label: 'Aadhaar Card' },
                      { type: 'cv', label: 'CV / Resume' },
                    ].map((doc) => {
                      const uploaded = uploadedDocs.find(d => d.type === doc.type);
                      return (
                        <div key={doc.type} className="flex items-center justify-between p-4 border rounded-lg bg-neutral-50">
                          <div className="flex items-center gap-3">
                            {uploaded ? (
                              <CheckCircle2 className="w-5 h-5 text-green-500" />
                            ) : (
                              <FileText className="w-5 h-5 text-neutral-400" />
                            )}
                            <div>
                              <p className="font-medium text-neutral-800">{doc.label} <span className="text-red-500">*</span></p>
                              {uploaded && (
                                <p className="text-xs text-green-600">Uploaded successfully</p>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {uploaded && (
                              <a
                                href={uploaded.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-amber-600 hover:underline"
                              >
                                View
                              </a>
                            )}
                            <label className="cursor-pointer">
                              <input
                                type="file"
                                className="hidden"
                                accept=".pdf,.jpg,.jpeg,.png"
                                onChange={(e) => {
                                  if (e.target.files?.[0]) {
                                    handleFileUpload(doc.type, e.target.files[0]);
                                  }
                                }}
                              />
                              <span className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors">
                                <Upload className="w-4 h-4" />
                                {uploaded ? 'Replace' : 'Upload'}
                              </span>
                            </label>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Declaration */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <Alert className="bg-amber-50 border-amber-200">
                  <Shield className="w-4 h-4 text-amber-600" />
                  <AlertDescription className="text-amber-800">
                    Please read and accept all declarations to complete your submission.
                  </AlertDescription>
                </Alert>

                {/* Do's */}
                <div>
                  <h3 className="font-semibold text-green-700 mb-3 flex items-center gap-2">
                    <Check className="w-5 h-5" /> I Agree To
                  </h3>
                  <div className="space-y-3">
                    {DECLARATION_ITEMS.filter(item => item.type === 'do').map((item) => (
                      <div key={item.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-neutral-50">
                        <Checkbox
                          id={item.id}
                          checked={formData.declarations[item.id] || false}
                          onCheckedChange={(checked) => {
                            setFormData(prev => ({
                              ...prev,
                              declarations: { ...prev.declarations, [item.id]: checked }
                            }));
                          }}
                        />
                        <label htmlFor={item.id} className="text-sm text-neutral-700 cursor-pointer leading-relaxed">
                          {item.text}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Don'ts */}
                <div>
                  <h3 className="font-semibold text-red-700 mb-3 flex items-center gap-2">
                    <Shield className="w-5 h-5" /> I Declare That
                  </h3>
                  <div className="space-y-3">
                    {DECLARATION_ITEMS.filter(item => item.type === 'dont').map((item) => (
                      <div key={item.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-neutral-50">
                        <Checkbox
                          id={item.id}
                          checked={formData.declarations[item.id] || false}
                          onCheckedChange={(checked) => {
                            setFormData(prev => ({
                              ...prev,
                              declarations: { ...prev.declarations, [item.id]: checked }
                            }));
                          }}
                        />
                        <label htmlFor={item.id} className="text-sm text-neutral-700 cursor-pointer leading-relaxed">
                          {item.text}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Summary */}
                <div className="bg-neutral-100 rounded-lg p-4">
                  <h4 className="font-semibold text-neutral-800 mb-2">Submission Summary</h4>
                  <div className="text-sm text-neutral-600 space-y-1">
                    <p>Name: {cd.first_name} {cd.last_name}</p>
                    <p>Email: {cd.email}</p>
                    <p>Phone: {cd.phone}</p>
                    <p>Documents: {uploadedDocs.length} uploaded</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>

          <CardFooter className="flex justify-between">
            <Button
              variant="outline"
              onClick={handlePrev}
              disabled={currentStep === 0}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>

            {currentStep < STEPS.length - 1 ? (
              <Button onClick={handleNext} disabled={saving}>
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Next
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button 
                onClick={handleSubmit} 
                disabled={submitMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                {submitMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Submit Form
              </Button>
            )}
          </CardFooter>
        </Card>

        {/* Footer */}
        <div className="text-center mt-6 text-sm text-neutral-500">
          <p>© 2026 D&V Business Consulting. All information is kept confidential.</p>
        </div>
      </div>
    </div>
  );
};

export default CandidateOnboardingForm;
