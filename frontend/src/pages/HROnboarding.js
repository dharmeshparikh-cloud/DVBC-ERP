import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { 
  UserPlus, FileText, Upload, CheckCircle, AlertCircle,
  Building2, Mail, Phone, Calendar, Wallet, User,
  ChevronRight, ChevronLeft, Save
} from 'lucide-react';
import { toast } from 'sonner';

const ONBOARDING_STEPS = [
  { id: 'personal', title: 'Personal Info', icon: User },
  { id: 'employment', title: 'Employment Details', icon: Building2 },
  { id: 'documents', title: 'Documents', icon: FileText },
  { id: 'bank', title: 'Bank Details', icon: Wallet },
  { id: 'review', title: 'Review & Submit', icon: CheckCircle },
];

const DEPARTMENTS = [
  'Consulting', 'Sales', 'HR', 'Finance', 'Technology', 'Operations', 'Marketing'
];

const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
  { value: 'part_time', label: 'Part Time' },
];

const ROLES = [
  { value: 'consultant', label: 'Consultant' },
  { value: 'senior_consultant', label: 'Senior Consultant' },
  { value: 'lead_consultant', label: 'Lead Consultant' },
  { value: 'principal_consultant', label: 'Principal Consultant' },
  { value: 'project_manager', label: 'Project Manager' },
  { value: 'executive', label: 'Sales Executive' },
  { value: 'account_manager', label: 'Account Manager' },
  { value: 'hr_executive', label: 'HR Executive' },
];

const EMPLOYEE_LEVELS = [
  { value: 'executive', label: 'Executive', description: 'Entry level - basic permissions' },
  { value: 'manager', label: 'Manager', description: 'Mid level - team management permissions' },
  { value: 'leader', label: 'Leader', description: 'Senior level - strategic permissions' },
];

const HROnboarding = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [managers, setManagers] = useState([]);
  const [bankProofFile, setBankProofFile] = useState(null);
  
  // Document upload state
  const [uploadedDocs, setUploadedDocs] = useState({
    id_proof: null,
    resume: null,
    offer_letter: null,
    other: null
  });
  
  const [formData, setFormData] = useState({
    // Personal Info
    first_name: '',
    last_name: '',
    email: '',
    personal_email: '',
    phone: '',
    date_of_birth: '',
    gender: '',
    address: '',
    
    // Employment Details
    employee_id: '',
    department: '',
    designation: '',
    role: 'consultant',
    level: 'executive',  // Employee hierarchy level
    employment_type: 'full_time',
    joining_date: '',
    reporting_manager_id: '',
    
    // Documents (file references)
    documents: [],
    
    // Bank Details
    bank_account_number: '',
    bank_ifsc: '',
    bank_name: '',
    bank_branch: '',
    bank_account_holder: '',
    bank_proof_uploaded: false,
  });

  useEffect(() => {
    fetchManagers();
  }, []);

  const fetchManagers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const users = await response.json();
        // Filter for potential managers
        const managerRoles = ['manager', 'hr_manager', 'project_manager', 'principal_consultant', 'admin'];
        const potentialManagers = users.filter(u => managerRoles.includes(u.role));
        setManagers(potentialManagers);
      }
    } catch (error) {
      console.error('Failed to fetch managers:', error);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleBankProofUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      if (!validTypes.includes(file.type)) {
        toast.error('Please upload a JPG, PNG, or PDF file');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size must be less than 5MB');
        return;
      }
      
      setBankProofFile(file);
      setFormData(prev => ({ ...prev, bank_proof_uploaded: true }));
      toast.success('Bank proof uploaded successfully');
    }
  };

  // Document upload handler
  const handleDocumentUpload = (docType, e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      if (!validTypes.includes(file.type)) {
        toast.error('Please upload a JPG, PNG, or PDF file');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size must be less than 5MB');
        return;
      }
      
      setUploadedDocs(prev => ({ ...prev, [docType]: file }));
      toast.success(`${docType.replace('_', ' ')} uploaded successfully`);
    }
  };

  const validateStep = (step) => {
    switch (step) {
      case 0: // Personal Info
        if (!formData.first_name || !formData.last_name || !formData.email || !formData.phone) {
          toast.error('Please fill in all required personal information');
          return false;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
          toast.error('Please enter a valid email address');
          return false;
        }
        // Validate phone number - must be 10 digits
        const cleanPhone = formData.phone.replace(/\D/g, '');
        if (cleanPhone.length < 10) {
          toast.error('Please enter a valid 10-digit phone number');
          return false;
        }
        return true;
        
      case 1: // Employment Details
        if (!formData.employee_id || !formData.department || !formData.designation || !formData.joining_date) {
          toast.error('Please fill in all required employment details');
          return false;
        }
        if (!formData.level) {
          toast.error('Please select an employee level (Executive/Manager/Leader)');
          return false;
        }
        // Reporting manager is always required - HR Manager/Admin should be available
        if (!formData.reporting_manager_id) {
          toast.error('Please select a reporting manager');
          return false;
        }
        return true;
        
      case 2: // Documents - ID Proof, Resume, Offer Letter are mandatory
        if (!uploadedDocs.id_proof) {
          toast.error('Please upload ID Proof (Aadhar, PAN, or Passport)');
          return false;
        }
        if (!uploadedDocs.resume) {
          toast.error('Please upload Resume');
          return false;
        }
        if (!uploadedDocs.offer_letter) {
          toast.error('Please upload signed Offer Letter');
          return false;
        }
        return true;
        
      case 3: // Bank Details
        if (formData.bank_account_number || formData.bank_ifsc) {
          // If any bank detail is provided, require proof
          if (!formData.bank_proof_uploaded) {
            toast.error('Bank proof document is required when providing bank details');
            return false;
          }
          if (!formData.bank_account_number || !formData.bank_ifsc || !formData.bank_name) {
            toast.error('Please complete all bank details');
            return false;
          }
        }
        return true;
        
      default:
        return true;
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, ONBOARDING_STEPS.length - 1));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      
      // Prepare employee data
      const employeeData = {
        employee_id: formData.employee_id,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        personal_email: formData.personal_email,
        phone: formData.phone,
        date_of_birth: formData.date_of_birth,
        gender: formData.gender,
        address: formData.address,
        department: formData.department,
        designation: formData.designation,
        level: formData.level || 'executive',  // Employee permission level (mandatory)
        role: formData.role || 'consultant',   // System role
        employment_type: formData.employment_type,
        joining_date: formData.joining_date,
        reporting_manager_id: formData.reporting_manager_id,
        bank_details: formData.bank_account_number ? {
          account_number: formData.bank_account_number,
          ifsc_code: formData.bank_ifsc,
          bank_name: formData.bank_name,
          branch: formData.bank_branch,
          account_holder_name: formData.bank_account_holder,
          proof_uploaded: formData.bank_proof_uploaded,
          proof_verified: false, // Requires admin approval
        } : null,
        onboarding_status: 'pending_user_creation',
        onboarded_by: user?.id,
        onboarded_at: new Date().toISOString(),
      };

      // Create employee record
      const response = await fetch(`${API}/employees`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(employeeData)
      });

      if (response.ok) {
        const employee = await response.json();
        
        // Create user account for the employee
        const userResponse = await fetch(`${API}/users`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: formData.email,
            full_name: `${formData.first_name} ${formData.last_name}`,
            role: formData.role,
            department: formData.department,
            password: 'Welcome@123', // Temporary password
            is_active: true
          })
        });

        if (userResponse.ok) {
          const userData = await userResponse.json();
          
          // Link user to employee
          await fetch(`${API}/employees/${employee.id}/link-user`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userData.id })
          });
          
          toast.success('Employee onboarded successfully! Temporary password: Welcome@123');
          navigate('/hr/employees');
        } else {
          toast.success('Employee record created. User account creation may require admin setup.');
          navigate('/hr/employees');
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create employee');
      }
    } catch (error) {
      console.error('Onboarding error:', error);
      toast.error('An error occurred during onboarding');
    } finally {
      setLoading(false);
    }
  };

  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100;

  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Personal Info
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={formData.first_name}
                  onChange={(e) => handleInputChange('first_name', e.target.value)}
                  placeholder="Enter first name"
                  data-testid="onboard-first-name"
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name *</Label>
                <Input
                  value={formData.last_name}
                  onChange={(e) => handleInputChange('last_name', e.target.value)}
                  placeholder="Enter last name"
                  data-testid="onboard-last-name"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Work Email *</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  placeholder="work@company.com"
                  data-testid="onboard-email"
                />
              </div>
              <div className="space-y-2">
                <Label>Personal Email</Label>
                <Input
                  type="email"
                  value={formData.personal_email}
                  onChange={(e) => handleInputChange('personal_email', e.target.value)}
                  placeholder="personal@email.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Phone Number * <span className="text-xs text-zinc-400">(10 digits)</span></Label>
                <div className="flex gap-2">
                  <div className="flex items-center px-3 bg-zinc-100 border border-zinc-200 rounded-sm text-sm text-zinc-600">
                    +91
                  </div>
                  <Input
                    value={formData.phone}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 10);
                      handleInputChange('phone', value);
                    }}
                    placeholder="XXXXXXXXXX"
                    maxLength={10}
                    data-testid="onboard-phone"
                    className="flex-1"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Date of Birth</Label>
                <Input
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => handleInputChange('date_of_birth', e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Gender</Label>
                <Select value={formData.gender} onValueChange={(v) => handleInputChange('gender', v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select gender" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="male">Male</SelectItem>
                    <SelectItem value="female">Female</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Address</Label>
              <Textarea
                value={formData.address}
                onChange={(e) => handleInputChange('address', e.target.value)}
                placeholder="Enter full address"
                rows={2}
              />
            </div>
          </div>
        );

      case 1: // Employment Details
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Employee ID *</Label>
                <Input
                  value={formData.employee_id}
                  onChange={(e) => handleInputChange('employee_id', e.target.value)}
                  placeholder="EMP001"
                  data-testid="onboard-emp-id"
                />
              </div>
              <div className="space-y-2">
                <Label>Joining Date *</Label>
                <Input
                  type="date"
                  value={formData.joining_date}
                  onChange={(e) => handleInputChange('joining_date', e.target.value)}
                  data-testid="onboard-joining-date"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Department *</Label>
                <Select value={formData.department} onValueChange={(v) => handleInputChange('department', v)}>
                  <SelectTrigger data-testid="onboard-department">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(dept => (
                      <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Designation *</Label>
                <Input
                  value={formData.designation}
                  onChange={(e) => handleInputChange('designation', e.target.value)}
                  placeholder="e.g., Software Engineer"
                  data-testid="onboard-designation"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Role *</Label>
                <Select value={formData.role} onValueChange={(v) => handleInputChange('role', v)}>
                  <SelectTrigger data-testid="onboard-role">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map(role => (
                      <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Employee Level *</Label>
                <Select value={formData.level} onValueChange={(v) => handleInputChange('level', v)}>
                  <SelectTrigger data-testid="onboard-level">
                    <SelectValue placeholder="Select level" />
                  </SelectTrigger>
                  <SelectContent>
                    {EMPLOYEE_LEVELS.map(level => (
                      <SelectItem key={level.value} value={level.value}>
                        {level.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {EMPLOYEE_LEVELS.find(l => l.value === formData.level)?.description || ''}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Employment Type *</Label>
                <Select value={formData.employment_type} onValueChange={(v) => handleInputChange('employment_type', v)}>
                  <SelectTrigger data-testid="onboard-emp-type">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {EMPLOYMENT_TYPES.map(type => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Reporting Manager *</Label>
                <Select value={formData.reporting_manager_id} onValueChange={(v) => handleInputChange('reporting_manager_id', v)}>
                  <SelectTrigger data-testid="onboard-reporting-mgr">
                    <SelectValue placeholder="Select reporting manager" />
                  </SelectTrigger>
                  <SelectContent>
                    {managers.length === 0 ? (
                      <SelectItem value="" disabled>No managers available - contact admin</SelectItem>
                    ) : (
                      managers.map(mgr => (
                        <SelectItem key={mgr.id} value={mgr.id}>
                          {mgr.full_name || mgr.email} ({mgr.role?.replace('_', ' ')})
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                <p className="text-xs text-zinc-500">HR can update the reporting manager later from Employee Master</p>
              </div>
            </div>
          </div>
        );

      case 2: // Documents
        return (
          <div className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800 dark:text-blue-300">Document Upload</p>
                  <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                    ID Proof, Resume, and Offer Letter are required. You can update documents later from the Employee Master.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* ID Proof - Required */}
              <Card className={`border-dashed border-2 transition-colors ${uploadedDocs.id_proof ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' : 'border-red-300 hover:border-red-400'}`}>
                <CardContent className="pt-6 text-center">
                  <input
                    type="file"
                    id="id_proof_upload"
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={(e) => handleDocumentUpload('id_proof', e)}
                  />
                  <label htmlFor="id_proof_upload" className="cursor-pointer block">
                    {uploadedDocs.id_proof ? (
                      <CheckCircle className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                    ) : (
                      <Upload className="w-8 h-8 mx-auto text-red-400 mb-2" />
                    )}
                    <p className="font-medium">ID Proof <span className="text-red-500">*</span></p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {uploadedDocs.id_proof ? uploadedDocs.id_proof.name : 'Aadhar, PAN, Passport'}
                    </p>
                  </label>
                </CardContent>
              </Card>

              {/* Resume - Required */}
              <Card className={`border-dashed border-2 transition-colors ${uploadedDocs.resume ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' : 'border-red-300 hover:border-red-400'}`}>
                <CardContent className="pt-6 text-center">
                  <input
                    type="file"
                    id="resume_upload"
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={(e) => handleDocumentUpload('resume', e)}
                  />
                  <label htmlFor="resume_upload" className="cursor-pointer block">
                    {uploadedDocs.resume ? (
                      <CheckCircle className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                    ) : (
                      <Upload className="w-8 h-8 mx-auto text-red-400 mb-2" />
                    )}
                    <p className="font-medium">Resume <span className="text-red-500">*</span></p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {uploadedDocs.resume ? uploadedDocs.resume.name : 'PDF format preferred'}
                    </p>
                  </label>
                </CardContent>
              </Card>

              {/* Offer Letter - Required */}
              <Card className={`border-dashed border-2 transition-colors ${uploadedDocs.offer_letter ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' : 'border-red-300 hover:border-red-400'}`}>
                <CardContent className="pt-6 text-center">
                  <input
                    type="file"
                    id="offer_letter_upload"
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={(e) => handleDocumentUpload('offer_letter', e)}
                  />
                  <label htmlFor="offer_letter_upload" className="cursor-pointer block">
                    {uploadedDocs.offer_letter ? (
                      <CheckCircle className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                    ) : (
                      <Upload className="w-8 h-8 mx-auto text-red-400 mb-2" />
                    )}
                    <p className="font-medium">Offer Letter <span className="text-red-500">*</span></p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {uploadedDocs.offer_letter ? uploadedDocs.offer_letter.name : 'Signed copy'}
                    </p>
                  </label>
                </CardContent>
              </Card>

              {/* Other Documents */}
              <Card className={`border-dashed border-2 transition-colors ${uploadedDocs.other ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' : 'hover:border-emerald-500'}`}>
                <CardContent className="pt-6 text-center">
                  <input
                    type="file"
                    id="other_upload"
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={(e) => handleDocumentUpload('other', e)}
                  />
                  <label htmlFor="other_upload" className="cursor-pointer block">
                    {uploadedDocs.other ? (
                      <CheckCircle className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
                    ) : (
                      <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                    )}
                    <p className="font-medium">Other Documents</p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {uploadedDocs.other ? uploadedDocs.other.name : 'Any additional docs'}
                    </p>
                  </label>
                </CardContent>
              </Card>
            </div>
            
            <div className="flex justify-between items-center text-sm mt-4">
              <p className="text-zinc-500">
                Required: {[uploadedDocs.id_proof, uploadedDocs.resume, uploadedDocs.offer_letter].filter(d => d !== null).length}/3 uploaded
              </p>
              <p className="text-zinc-400">
                <span className="text-red-500">*</span> Required documents
              </p>
            </div>
          </div>
        );

      case 3: // Bank Details
        return (
          <div className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800 dark:text-blue-300">Bank Proof Required</p>
                  <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                    Bank details can only be saved with a valid proof document (cancelled cheque or bank statement).
                    Changes after onboarding require admin approval.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Account Number</Label>
                <Input
                  value={formData.bank_account_number}
                  onChange={(e) => handleInputChange('bank_account_number', e.target.value)}
                  placeholder="Enter account number"
                  data-testid="onboard-bank-account"
                />
              </div>
              <div className="space-y-2">
                <Label>IFSC Code</Label>
                <Input
                  value={formData.bank_ifsc}
                  onChange={(e) => handleInputChange('bank_ifsc', e.target.value.toUpperCase())}
                  placeholder="e.g., SBIN0001234"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Bank Name</Label>
                <Input
                  value={formData.bank_name}
                  onChange={(e) => handleInputChange('bank_name', e.target.value)}
                  placeholder="e.g., State Bank of India"
                />
              </div>
              <div className="space-y-2">
                <Label>Branch</Label>
                <Input
                  value={formData.bank_branch}
                  onChange={(e) => handleInputChange('bank_branch', e.target.value)}
                  placeholder="Branch name"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Account Holder Name</Label>
              <Input
                value={formData.bank_account_holder}
                onChange={(e) => handleInputChange('bank_account_holder', e.target.value)}
                placeholder="Name as per bank records"
              />
            </div>

            {/* Bank Proof Upload */}
            <div className="space-y-2">
              <Label>Bank Proof Document *</Label>
              <div className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                formData.bank_proof_uploaded 
                  ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' 
                  : 'border-zinc-300 hover:border-emerald-500'
              }`}>
                {formData.bank_proof_uploaded ? (
                  <div>
                    <CheckCircle className="w-8 h-8 mx-auto text-emerald-600 mb-2" />
                    <p className="font-medium text-emerald-700">Proof Uploaded</p>
                    <p className="text-xs text-emerald-600 mt-1">{bankProofFile?.name}</p>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2"
                      onClick={() => {
                        setBankProofFile(null);
                        setFormData(prev => ({ ...prev, bank_proof_uploaded: false }));
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                    <p className="font-medium">Upload Bank Proof</p>
                    <p className="text-xs text-zinc-500 mt-1">Cancelled cheque or bank statement (JPG, PNG, PDF - Max 5MB)</p>
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.pdf"
                      onChange={handleBankProofUpload}
                      className="hidden"
                      data-testid="bank-proof-upload"
                    />
                  </label>
                )}
              </div>
            </div>
          </div>
        );

      case 4: // Review
        return (
          <div className="space-y-6">
            {/* Personal Info Summary */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <User className="w-4 h-4" /> Personal Information
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-zinc-500">Name</p>
                  <p className="font-medium">{formData.first_name} {formData.last_name}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Email</p>
                  <p className="font-medium">{formData.email}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Phone</p>
                  <p className="font-medium">{formData.phone}</p>
                </div>
              </CardContent>
            </Card>

            {/* Employment Summary */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Building2 className="w-4 h-4" /> Employment Details
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-zinc-500">Employee ID</p>
                  <p className="font-medium">{formData.employee_id}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Department</p>
                  <p className="font-medium">{formData.department}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Designation</p>
                  <p className="font-medium">{formData.designation}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Role</p>
                  <p className="font-medium capitalize">{formData.role.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Joining Date</p>
                  <p className="font-medium">{formData.joining_date}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Employment Type</p>
                  <p className="font-medium capitalize">{formData.employment_type.replace('_', ' ')}</p>
                </div>
              </CardContent>
            </Card>

            {/* Bank Details Summary */}
            {formData.bank_account_number && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Wallet className="w-4 h-4" /> Bank Details
                    {formData.bank_proof_uploaded && (
                      <Badge className="bg-emerald-100 text-emerald-700 ml-2">Proof Uploaded</Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-zinc-500">Account Number</p>
                    <p className="font-medium">****{formData.bank_account_number.slice(-4)}</p>
                  </div>
                  <div>
                    <p className="text-zinc-500">IFSC Code</p>
                    <p className="font-medium">{formData.bank_ifsc}</p>
                  </div>
                  <div>
                    <p className="text-zinc-500">Bank Name</p>
                    <p className="font-medium">{formData.bank_name}</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-600 mt-0.5" />
                <div>
                  <p className="font-medium text-emerald-800 dark:text-emerald-300">Ready to Submit</p>
                  <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-1">
                    Review the information above. Once submitted, a user account will be created with temporary password: <strong>Welcome@123</strong>
                  </p>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="hr-onboarding">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Employee Onboarding</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Complete all steps to onboard a new employee
        </p>
      </div>

      {/* Progress */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            {ONBOARDING_STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isCompleted = idx < currentStep;
              const isCurrent = idx === currentStep;
              
              return (
                <div key={step.id} className="flex items-center">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                    isCompleted 
                      ? 'bg-emerald-600 border-emerald-600 text-white' 
                      : isCurrent 
                        ? 'border-emerald-600 text-emerald-600' 
                        : 'border-zinc-300 text-zinc-400'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      <Icon className="w-5 h-5" />
                    )}
                  </div>
                  {idx < ONBOARDING_STEPS.length - 1 && (
                    <div className={`w-16 h-0.5 mx-2 ${
                      isCompleted ? 'bg-emerald-600' : 'bg-zinc-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-xs">
            {ONBOARDING_STEPS.map((step, idx) => (
              <span 
                key={step.id}
                className={`${idx === currentStep ? 'text-emerald-600 font-medium' : 'text-zinc-500'}`}
              >
                {step.title}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Step Content */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle>{ONBOARDING_STEPS[currentStep].title}</CardTitle>
          <CardDescription>
            Step {currentStep + 1} of {ONBOARDING_STEPS.length}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {renderStepContent()}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={prevStep}
          disabled={currentStep === 0}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Previous
        </Button>

        {currentStep === ONBOARDING_STEPS.length - 1 ? (
          <Button
            onClick={handleSubmit}
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-700"
            data-testid="submit-onboarding"
          >
            {loading ? 'Creating...' : 'Complete Onboarding'}
            <CheckCircle className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          <Button onClick={nextStep} className="bg-emerald-600 hover:bg-emerald-700">
            Next
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        )}
      </div>
    </div>
  );
};

export default HROnboarding;
