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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { 
  UserPlus, FileText, Upload, CheckCircle, AlertCircle,
  Building2, Mail, Phone, Calendar, Wallet, User,
  ChevronRight, ChevronLeft, Save, X, Plus, Copy, Key, UserCheck
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
  'Sales', 'HR', 'Consulting', 'Finance', 'Admin'
];

const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
  { value: 'part_time', label: 'Part Time' },
];

// Roles are now secondary - Department determines page access
const ROLES = [
  // Consulting roles
  { value: 'consultant', label: 'Consultant', department: 'Consulting' },
  { value: 'senior_consultant', label: 'Senior Consultant', department: 'Consulting' },
  { value: 'lead_consultant', label: 'Lead Consultant', department: 'Consulting' },
  { value: 'principal_consultant', label: 'Principal Consultant', department: 'Consulting' },
  { value: 'project_manager', label: 'Project Manager', department: 'Consulting' },
  { value: 'subject_matter_expert', label: 'Subject Matter Expert', department: 'Consulting' },
  // Sales roles
  { value: 'executive', label: 'Sales Executive', department: 'Sales' },
  { value: 'account_manager', label: 'Account Manager', department: 'Sales' },
  // HR roles
  { value: 'hr_executive', label: 'HR Executive', department: 'HR' },
  { value: 'hr_manager', label: 'HR Manager', department: 'HR' },
  // Admin/General roles
  { value: 'manager', label: 'Manager', department: 'Admin' },
  { value: 'admin', label: 'Administrator', department: 'Admin' },
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
  const [suggestedDept, setSuggestedDept] = useState(null);
  const [deptSuggestionLoading, setDeptSuggestionLoading] = useState(false);
  
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
    department: '',           // Primary department (legacy, kept for compatibility)
    departments: [],          // Multi-department array
    primary_department: '',   // Explicitly marked primary
    designation: '',
    employment_type: 'full_time',
    joining_date: '',
    reporting_manager_id: '',
    is_view_only: false,      // View-only flag (simplified permission)
    
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
    generateEmployeeId();
  }, []);

  // Auto-generate Employee ID with EMP prefix
  const generateEmployeeId = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/employees`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const employees = await response.json();
        // Find the highest EMP number
        let maxNum = 0;
        employees.forEach(emp => {
          const match = emp.employee_id?.match(/EMP(\d+)/i);
          if (match) {
            const num = parseInt(match[1], 10);
            if (num > maxNum) maxNum = num;
          }
        });
        // Generate next number with padding
        const nextNum = maxNum + 1;
        const newEmployeeId = `EMP${String(nextNum).padStart(3, '0')}`;
        setFormData(prev => ({ ...prev, employee_id: newEmployeeId }));
      }
    } catch (error) {
      console.error('Failed to generate employee ID:', error);
      // Default fallback
      setFormData(prev => ({ ...prev, employee_id: `EMP${Date.now().toString().slice(-4)}` }));
    }
  };

  const fetchManagers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const users = await response.json();
        // Filter for potential managers - anyone can be a manager now
        setManagers(users.filter(u => u.is_active !== false));
      }
    } catch (error) {
      console.error('Failed to fetch managers:', error);
    }
  };

  // Auto-suggest department based on designation
  const suggestDepartmentFromDesignation = async (designation) => {
    if (!designation || designation.length < 3) {
      setSuggestedDept(null);
      return;
    }
    
    setDeptSuggestionLoading(true);
    try {
      const res = await fetch(`${API}/permission-config/suggest-department?designation=${encodeURIComponent(designation)}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestedDept(data);
        
        // Auto-fill if high confidence and department not already set
        if (data.suggested_department && data.confidence >= 0.7 && !formData.department) {
          setFormData(prev => ({ ...prev, department: data.suggested_department }));
          // Also auto-select matching role
          const matchingRole = ROLES.find(r => r.department === data.suggested_department);
          if (matchingRole) {
            setFormData(prev => ({ ...prev, role: matchingRole.value }));
          }
        }
      }
    } catch (error) {
      console.error('Failed to suggest department:', error);
    } finally {
      setDeptSuggestionLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Debounced designation change handler
  const handleDesignationChange = (value) => {
    handleInputChange('designation', value);
    // Debounce the API call
    clearTimeout(window.designationTimeout);
    window.designationTimeout = setTimeout(() => {
      suggestDepartmentFromDesignation(value);
    }, 500);
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

  const validateStep = (step) => {
    switch (step) {
      case 0: // Personal Info - ALL MANDATORY
        if (!formData.first_name?.trim()) {
          toast.error('First Name is required');
          return false;
        }
        if (!formData.last_name?.trim()) {
          toast.error('Last Name is required');
          return false;
        }
        if (!formData.email?.trim()) {
          toast.error('Work Email is required');
          return false;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
          toast.error('Please enter a valid email address');
          return false;
        }
        if (!formData.phone?.trim()) {
          toast.error('Phone Number is required');
          return false;
        }
        // Validate phone number - must be 10 digits
        const cleanPhone = formData.phone.replace(/\D/g, '');
        if (cleanPhone.length < 10) {
          toast.error('Please enter a valid 10-digit phone number');
          return false;
        }
        if (!formData.gender) {
          toast.error('Gender is required');
          return false;
        }
        return true;
        
      case 1: // Employment Details - ALL MANDATORY
        if (!formData.employee_id?.trim()) {
          toast.error('Employee ID is required');
          return false;
        }
        if (!formData.employee_id.toUpperCase().startsWith('EMP')) {
          toast.error('Employee ID must start with "EMP"');
          return false;
        }
        if (!formData.designation?.trim()) {
          toast.error('Designation is required');
          return false;
        }
        if (!formData.joining_date) {
          toast.error('Joining Date is required');
          return false;
        }
        if (!formData.departments || formData.departments.length === 0) {
          toast.error('Please select at least one department');
          return false;
        }
        if (!formData.employment_type) {
          toast.error('Employment Type is required');
          return false;
        }
        if (!formData.reporting_manager_id) {
          toast.error('Reporting Manager is required');
          return false;
        }
        return true;
        
      case 2: // Documents
        // Documents are optional but recommended
        return true;
        
      case 3: // Bank Details - Optional but if provided, all required
        if (formData.bank_account_number || formData.bank_ifsc) {
          if (!formData.bank_account_number?.trim()) {
            toast.error('Bank Account Number is required');
            return false;
          }
          if (!formData.bank_ifsc?.trim()) {
            toast.error('Bank IFSC Code is required');
            return false;
          }
          if (!formData.bank_name?.trim()) {
            toast.error('Bank Name is required');
            return false;
          }
          if (!formData.bank_proof_uploaded) {
            toast.error('Bank proof document is required when providing bank details');
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
      
      // Generate password based on Employee ID pattern: Welcome@EMP001
      const generatedPassword = `Welcome@${formData.employee_id}`;
      
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
        department: formData.primary_department || formData.departments[0], // Legacy field
        departments: formData.departments,  // Multi-department array
        primary_department: formData.primary_department || formData.departments[0],
        designation: formData.designation,
        // SIMPLIFIED: No role/level - just is_view_only flag
        is_view_only: formData.is_view_only || false,
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
        onboarding_status: 'completed',
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
        
        // Get reporting manager details
        const reportingManager = managers.find(m => m.id === formData.reporting_manager_id);
        
        // Create user account for the employee with pattern-based password
        const userResponse = await fetch(`${API}/users`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: formData.email,
            full_name: `${formData.first_name} ${formData.last_name}`,
            department: formData.primary_department || formData.departments[0],
            departments: formData.departments,
            primary_department: formData.primary_department || formData.departments[0],
            is_view_only: formData.is_view_only || false,
            employee_id: formData.employee_id, // Store employee_id in user for login
            password: generatedPassword,
            requires_password_change: true, // Flag for first login
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
          
          // Show success popup with all details
          setOnboardingSuccess({
            employee: {
              id: formData.employee_id,
              name: `${formData.first_name} ${formData.last_name}`,
              email: formData.email,
              department: formData.departments.join(', '),
              designation: formData.designation,
              joiningDate: formData.joining_date,
            },
            credentials: {
              loginId: formData.employee_id,
              password: generatedPassword,
            },
            reportingManager: reportingManager ? {
              name: reportingManager.full_name,
              email: reportingManager.email,
              department: reportingManager.department,
            } : null,
          });
          setShowSuccessDialog(true);
          
          // Simulate email notification (mock)
          console.log('📧 Mock Email Sent to:', formData.email, '- Welcome email with credentials');
          console.log('📧 Mock Email Sent to HR/Admin - New employee onboarded notification');
          
        } else {
          toast.success('Employee record created. User account creation may require admin setup.');
          navigate('/employees');
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
                <Label>Gender *</Label>
                <Select value={formData.gender} onValueChange={(v) => handleInputChange('gender', v)}>
                  <SelectTrigger data-testid="onboard-gender">
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
                <Label>Employee ID * <span className="text-xs text-green-600">(Auto-generated)</span></Label>
                <Input
                  value={formData.employee_id}
                  readOnly
                  className="bg-zinc-50 font-mono"
                  data-testid="onboard-emp-id"
                />
                <p className="text-xs text-muted-foreground">
                  Auto-generated with EMP prefix
                </p>
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

            {/* Designation Field - Auto-suggests department */}
            <div className="space-y-2">
              <Label>Designation * <span className="text-xs text-blue-600">(Auto-suggests department)</span></Label>
              <div className="relative">
                <Input
                  value={formData.designation}
                  onChange={(e) => handleDesignationChange(e.target.value)}
                  placeholder="e.g., Sales Manager, HR Executive, Consultant"
                  data-testid="onboard-designation"
                />
                {deptSuggestionLoading && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
              </div>
              {suggestedDept?.suggested_department && !deptSuggestionLoading && (
                <p className="text-xs text-green-600">
                  ✓ Suggested department: {suggestedDept.suggested_department} based on designation
                </p>
              )}
            </div>

            {/* Multi-Department Selection */}
            <div className="space-y-3">
              <Label>Departments * <span className="text-xs text-blue-600">(Multi-select - determines page access)</span></Label>
              
              {/* Selected Departments Display */}
              <div className="flex flex-wrap gap-2 min-h-[36px] p-2 border rounded-md bg-zinc-50">
                {formData.departments.length === 0 ? (
                  <span className="text-sm text-zinc-400">No departments selected</span>
                ) : (
                  formData.departments.map((dept) => (
                    <Badge 
                      key={dept} 
                      variant={dept === formData.primary_department ? "default" : "secondary"}
                      className="flex items-center gap-1 px-2 py-1"
                    >
                      {dept}
                      {dept === formData.primary_department && (
                        <span className="text-[10px] ml-1 opacity-75">(Primary)</span>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          const newDepts = formData.departments.filter(d => d !== dept);
                          const newPrimary = dept === formData.primary_department 
                            ? (newDepts[0] || '') 
                            : formData.primary_department;
                          setFormData({
                            ...formData,
                            departments: newDepts,
                            primary_department: newPrimary,
                            department: newPrimary // Keep legacy field in sync
                          });
                        }}
                        className="ml-1 hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </Badge>
                  ))
                )}
              </div>

              {/* Add Department Dropdown */}
              <div className="flex gap-2">
                <Select 
                  value="" 
                  onValueChange={(v) => {
                    if (v && !formData.departments.includes(v)) {
                      const newDepts = [...formData.departments, v];
                      const newPrimary = formData.primary_department || v;
                      setFormData({
                        ...formData,
                        departments: newDepts,
                        primary_department: newPrimary,
                        department: newPrimary // Keep legacy field in sync
                      });
                      // Auto-select a matching role for primary dept
                      if (!formData.primary_department) {
                        const matchingRole = ROLES.find(r => r.department === v);
                        if (matchingRole) {
                          handleInputChange('role', matchingRole.value);
                        }
                      }
                    }
                  }}
                >
                  <SelectTrigger data-testid="onboard-department-add" className="flex-1">
                    <SelectValue placeholder="Add department..." />
                  </SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.filter(dept => !formData.departments.includes(dept)).map(dept => (
                      <SelectItem key={dept} value={dept}>
                        <div className="flex items-center gap-2">
                          <Plus className="w-3 h-3" />
                          {dept}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Primary Department Selection */}
              {formData.departments.length > 1 && (
                <div className="flex items-center gap-2">
                  <Label className="text-xs text-muted-foreground whitespace-nowrap">Primary:</Label>
                  <Select 
                    value={formData.primary_department} 
                    onValueChange={(v) => {
                      setFormData({
                        ...formData,
                        primary_department: v,
                        department: v // Keep legacy field in sync
                      });
                      // Auto-select a matching role
                      const matchingRole = ROLES.find(r => r.department === v);
                      if (matchingRole) {
                        handleInputChange('role', matchingRole.value);
                      }
                    }}
                  >
                    <SelectTrigger className="h-8 text-xs" data-testid="onboard-primary-department">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {formData.departments.map(dept => (
                        <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <p className="text-xs text-muted-foreground">
                Employee will see pages from: {formData.departments.length > 0 ? formData.departments.join(', ') : '...'}
              </p>

              {/* Department Suggestion */}
              {suggestedDept?.suggested_department && !formData.departments.includes(suggestedDept.suggested_department) && (
                <div className="flex items-center gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded-md">
                  <span className="text-xs text-yellow-700">
                    Suggested: <strong>{suggestedDept.suggested_department}</strong> ({suggestedDept.reason})
                  </span>
                  <button 
                    type="button"
                    className="text-xs text-yellow-700 underline"
                    onClick={() => {
                      const newDepts = formData.departments.includes(suggestedDept.suggested_department)
                        ? formData.departments
                        : [...formData.departments, suggestedDept.suggested_department];
                      const newPrimary = formData.primary_department || suggestedDept.suggested_department;
                      setFormData({
                        ...formData,
                        departments: newDepts,
                        primary_department: newPrimary,
                        department: newPrimary
                      });
                      const matchingRole = ROLES.find(r => r.department === suggestedDept.suggested_department);
                      if (matchingRole && !formData.primary_department) {
                        handleInputChange('role', matchingRole.value);
                      }
                    }}
                  >
                    Add
                  </button>
                </div>
              )}
            </div>

            {/* Simplified - No Role/Level dropdowns */}
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
                <Label>Reporting Manager * <span className="text-xs text-blue-600">(Determines team access)</span></Label>
                <Select value={formData.reporting_manager_id} onValueChange={(v) => handleInputChange('reporting_manager_id', v)}>
                  <SelectTrigger data-testid="onboard-reporting-mgr">
                    <SelectValue placeholder="Select reporting manager" />
                  </SelectTrigger>
                  <SelectContent>
                    {managers.map(mgr => (
                      <SelectItem key={mgr.id} value={mgr.id}>{mgr.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  This person will gain team approval rights for this employee
                </p>
              </div>
            </div>

            {/* View Only Toggle */}
            <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-md">
              <input
                type="checkbox"
                id="is_view_only"
                checked={formData.is_view_only || false}
                onChange={(e) => handleInputChange('is_view_only', e.target.checked)}
                className="w-4 h-4 rounded border-zinc-300"
                data-testid="onboard-view-only"
              />
              <div>
                <Label htmlFor="is_view_only" className="cursor-pointer">View Only Access</Label>
                <p className="text-xs text-muted-foreground">
                  Employee can view data but cannot create or edit records
                </p>
              </div>
            </div>
          </div>
        );

      case 2: // Documents
        return (
          <div className="space-y-4">
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800 dark:text-amber-300">Document Upload</p>
                  <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                    Document upload is optional at this stage. You can add documents later from the employee profile.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Card className="border-dashed border-2 hover:border-emerald-500 cursor-pointer transition-colors">
                <CardContent className="pt-6 text-center">
                  <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                  <p className="font-medium">ID Proof</p>
                  <p className="text-xs text-zinc-500 mt-1">Aadhar, PAN, Passport</p>
                </CardContent>
              </Card>

              <Card className="border-dashed border-2 hover:border-emerald-500 cursor-pointer transition-colors">
                <CardContent className="pt-6 text-center">
                  <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                  <p className="font-medium">Resume</p>
                  <p className="text-xs text-zinc-500 mt-1">PDF format preferred</p>
                </CardContent>
              </Card>

              <Card className="border-dashed border-2 hover:border-emerald-500 cursor-pointer transition-colors">
                <CardContent className="pt-6 text-center">
                  <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                  <p className="font-medium">Offer Letter</p>
                  <p className="text-xs text-zinc-500 mt-1">Signed copy</p>
                </CardContent>
              </Card>

              <Card className="border-dashed border-2 hover:border-emerald-500 cursor-pointer transition-colors">
                <CardContent className="pt-6 text-center">
                  <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
                  <p className="font-medium">Other Documents</p>
                  <p className="text-xs text-zinc-500 mt-1">Any additional docs</p>
                </CardContent>
              </Card>
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
                <div className="col-span-2">
                  <p className="text-zinc-500">Departments</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {formData.departments.map(dept => (
                      <Badge 
                        key={dept} 
                        variant={dept === formData.primary_department ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {dept}
                        {dept === formData.primary_department && <span className="ml-1 opacity-75">(Primary)</span>}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-zinc-500">Designation</p>
                  <p className="font-medium">{formData.designation}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Joining Date</p>
                  <p className="font-medium">{formData.joining_date}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Employment Type</p>
                  <p className="font-medium capitalize">{formData.employment_type.replace('_', ' ')}</p>
                </div>
                <div>
                  <p className="text-zinc-500">Access Type</p>
                  <p className="font-medium">
                    {formData.is_view_only ? (
                      <Badge variant="secondary">View Only</Badge>
                    ) : (
                      <Badge variant="default">Full Access</Badge>
                    )}
                  </p>
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
