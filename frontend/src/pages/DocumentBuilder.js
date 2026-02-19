import React, { useState, useEffect, useContext, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  FileText, Download, Eye, Plus, Edit, Trash2, Save, Printer,
  User, Building2, Calendar, Mail, Phone, Award, Briefcase,
  CheckCircle, AlertCircle, Copy, FileSignature, Stamp
} from 'lucide-react';
import { toast } from 'sonner';

// Document types with their default templates
const DOCUMENT_TYPES = [
  { 
    id: 'offer_letter', 
    name: 'Offer Letter', 
    icon: FileText,
    description: 'Job offer letter for new hires'
  },
  { 
    id: 'appointment_letter', 
    name: 'Appointment Letter', 
    icon: Award,
    description: 'Official appointment confirmation'
  },
  { 
    id: 'confirmation_letter', 
    name: 'Confirmation Letter', 
    icon: CheckCircle,
    description: 'Post-probation confirmation'
  },
  { 
    id: 'experience_letter', 
    name: 'Experience Letter', 
    icon: Briefcase,
    description: 'Work experience certificate'
  },
];

// Default letter templates
const DEFAULT_TEMPLATES = {
  offer_letter: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>To,</strong></p>
<p>{{employee_name}}<br/>{{employee_address}}</p>

<p><strong>Subject: Offer of Employment</strong></p>

<p>Dear {{employee_name}},</p>

<p>We are pleased to offer you the position of <strong>{{designation}}</strong> at <strong>D&V Business Consulting</strong>. We were impressed with your qualifications and believe you will be a valuable addition to our team.</p>

<p><strong>Terms of Employment:</strong></p>
<ul>
<li><strong>Position:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Joining Date:</strong> {{joining_date}}</li>
<li><strong>Annual CTC:</strong> ₹{{ctc}}</li>
<li><strong>Location:</strong> {{location}}</li>
<li><strong>Reporting To:</strong> {{reporting_manager}}</li>
</ul>

<p><strong>Probation Period:</strong> Your employment will be subject to a probation period of {{probation_months}} months.</p>

<p>This offer is contingent upon successful completion of background verification and submission of required documents.</p>

<p>Please confirm your acceptance by signing and returning this letter by {{acceptance_deadline}}.</p>

<p>We look forward to welcoming you to our team!</p>

<p>Best Regards,</p>
<p>{{hr_name}}<br/>{{hr_designation}}<br/>D&V Business Consulting</p>
</div>`,

  appointment_letter: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/APPT/{{employee_id}}</p>

<p><strong>To,</strong></p>
<p>{{employee_name}}<br/>Employee ID: {{employee_id}}</p>

<p><strong>Subject: Letter of Appointment</strong></p>

<p>Dear {{employee_name}},</p>

<p>With reference to your application and subsequent discussions, we are pleased to appoint you as <strong>{{designation}}</strong> in the <strong>{{department}}</strong> department of D&V Business Consulting, effective from <strong>{{joining_date}}</strong>.</p>

<p><strong>Terms and Conditions:</strong></p>
<ol>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Annual CTC:</strong> ₹{{ctc}}</li>
<li><strong>Probation Period:</strong> {{probation_months}} months from the date of joining</li>
<li><strong>Working Hours:</strong> {{working_hours}}</li>
<li><strong>Leave Policy:</strong> As per company policy</li>
<li><strong>Notice Period:</strong> {{notice_period}} days during probation, {{notice_period_confirmed}} days after confirmation</li>
</ol>

<p>You are required to maintain confidentiality regarding company information and adhere to all company policies and procedures.</p>

<p>We welcome you to the D&V Business Consulting family and wish you a successful career with us.</p>

<p>For D&V Business Consulting</p>
<p>{{hr_name}}<br/>{{hr_designation}}</p>

<hr style="margin-top: 40px;"/>
<p><strong>Employee Acceptance</strong></p>
<p>I accept the terms and conditions of this appointment.</p>
<p>Signature: __________________ &nbsp;&nbsp; Date: ______________</p>
<p>Name: {{employee_name}}</p>
</div>`,

  confirmation_letter: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/CONF/{{employee_id}}</p>

<p><strong>To,</strong></p>
<p>{{employee_name}}<br/>Employee ID: {{employee_id}}<br/>{{department}}</p>

<p><strong>Subject: Confirmation of Employment</strong></p>

<p>Dear {{employee_name}},</p>

<p>We are pleased to inform you that based on your performance during the probation period, your services have been confirmed with effect from <strong>{{confirmation_date}}</strong>.</p>

<p><strong>Details:</strong></p>
<ul>
<li><strong>Employee ID:</strong> {{employee_id}}</li>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Date of Joining:</strong> {{joining_date}}</li>
<li><strong>Confirmation Date:</strong> {{confirmation_date}}</li>
<li><strong>Annual CTC (Post Confirmation):</strong> ₹{{ctc}}</li>
</ul>

<p>Your notice period post confirmation will be {{notice_period_confirmed}} days as per company policy.</p>

<p>We appreciate your contributions and look forward to your continued association with D&V Business Consulting.</p>

<p>Congratulations!</p>

<p>For D&V Business Consulting</p>
<p>{{hr_name}}<br/>{{hr_designation}}</p>
</div>`,

  experience_letter: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/EXP/{{employee_id}}</p>

<p><strong>TO WHOM IT MAY CONCERN</strong></p>

<p>This is to certify that <strong>{{employee_name}}</strong> was employed with <strong>D&V Business Consulting</strong> from <strong>{{joining_date}}</strong> to <strong>{{last_working_date}}</strong>.</p>

<p><strong>Employment Details:</strong></p>
<ul>
<li><strong>Employee ID:</strong> {{employee_id}}</li>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Period of Employment:</strong> {{joining_date}} to {{last_working_date}}</li>
<li><strong>Last Drawn CTC:</strong> ₹{{ctc}} per annum</li>
</ul>

<p>During the tenure, {{employee_name}} was responsible for:</p>
<ul>
{{responsibilities}}
</ul>

<p>{{employee_name}}'s performance was {{performance_rating}} and we found them to be {{qualities}}.</p>

<p>We wish {{employee_name}} all the best in future endeavors.</p>

<p>This certificate is being issued at the request of the employee for {{purpose}}.</p>

<p>For D&V Business Consulting</p>
<p>{{hr_name}}<br/>{{hr_designation}}</p>

<p style="margin-top: 30px;"><em>This is a computer-generated document and does not require a physical signature.</em></p>
</div>`
};

const DocumentBuilder = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preSelectedEmployeeId = searchParams.get('employee');
  
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [selectedDocType, setSelectedDocType] = useState('offer_letter');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  
  // Template editing
  const [templateContent, setTemplateContent] = useState('');
  const [customValues, setCustomValues] = useState({});
  const [previewHtml, setPreviewHtml] = useState('');
  
  // Preview dialog
  const [showPreview, setShowPreview] = useState(false);
  
  // Generated documents list
  const [generatedDocs, setGeneratedDocs] = useState([]);
  
  // Template saved templates
  const [savedTemplates, setSavedTemplates] = useState({});
  
  // History tab
  const [activeTab, setActiveTab] = useState('builder');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [documentHistory, setDocumentHistory] = useState([]);
  
  const printRef = useRef();

  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canGenerate = isAdmin || isHR;

  useEffect(() => {
    fetchEmployees();
    loadSavedTemplates();
    fetchDocumentHistory();
  }, []);

  useEffect(() => {
    // Set template when doc type changes
    const saved = savedTemplates[selectedDocType];
    setTemplateContent(saved || DEFAULT_TEMPLATES[selectedDocType] || '');
  }, [selectedDocType, savedTemplates]);

  useEffect(() => {
    if (selectedEmployee && templateContent) {
      generatePreview();
    }
  }, [selectedEmployee, templateContent, customValues]);

  useEffect(() => {
    // Pre-select employee if provided in URL
    if (preSelectedEmployeeId && employees.length > 0) {
      const emp = employees.find(e => 
        e.employee_id === preSelectedEmployeeId || 
        e.id === preSelectedEmployeeId
      );
      if (emp) {
        setSelectedEmployee(emp);
      }
    }
  }, [preSelectedEmployeeId, employees]);

  const fetchEmployees = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/employees`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setEmployees(data.filter(e => e.is_active !== false));
      }
    } catch (error) {
      console.error('Failed to fetch employees:', error);
      toast.error('Failed to load employees');
    } finally {
      setLoading(false);
    }
  };

  const loadSavedTemplates = () => {
    try {
      const saved = localStorage.getItem('document_builder_templates');
      if (saved) {
        setSavedTemplates(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Failed to load saved templates:', error);
    }
  };

  const fetchDocumentHistory = async () => {
    setHistoryLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/document-history?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocumentHistory(data);
      }
    } catch (error) {
      console.error('Failed to fetch document history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  const saveTemplate = () => {
    try {
      const updated = { ...savedTemplates, [selectedDocType]: templateContent };
      setSavedTemplates(updated);
      localStorage.setItem('document_builder_templates', JSON.stringify(updated));
      toast.success('Template saved successfully');
    } catch (error) {
      toast.error('Failed to save template');
    }
  };

  const resetTemplate = () => {
    setTemplateContent(DEFAULT_TEMPLATES[selectedDocType] || '');
    toast.success('Template reset to default');
  };

  const generatePreview = () => {
    if (!selectedEmployee || !templateContent) {
      setPreviewHtml('');
      return;
    }

    let html = templateContent;
    const today = new Date();
    
    // Calculate default values
    const joiningDate = selectedEmployee.joining_date 
      ? new Date(selectedEmployee.joining_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
      : '';
    
    const probationMonths = selectedEmployee.department?.toLowerCase().includes('consult') ? 6 : 3;
    const confirmationDate = selectedEmployee.joining_date 
      ? new Date(new Date(selectedEmployee.joining_date).setMonth(new Date(selectedEmployee.joining_date).getMonth() + probationMonths)).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
      : '';

    // Replace placeholders with employee data or custom values
    const replacements = {
      date: today.toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' }),
      employee_name: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`,
      employee_id: selectedEmployee.employee_id || '',
      employee_address: selectedEmployee.address || customValues.employee_address || '[Address]',
      designation: selectedEmployee.designation || customValues.designation || '[Designation]',
      department: selectedEmployee.department || selectedEmployee.primary_department || '[Department]',
      joining_date: joiningDate || customValues.joining_date || '[Joining Date]',
      ctc: customValues.ctc || selectedEmployee.salary || '[CTC Amount]',
      location: customValues.location || 'Bangalore',
      reporting_manager: customValues.reporting_manager || '[Reporting Manager]',
      probation_months: probationMonths,
      confirmation_date: confirmationDate || customValues.confirmation_date || '[Confirmation Date]',
      acceptance_deadline: customValues.acceptance_deadline || new Date(today.setDate(today.getDate() + 7)).toLocaleDateString('en-IN'),
      hr_name: user?.full_name || 'HR Manager',
      hr_designation: 'HR Manager',
      working_hours: customValues.working_hours || '9:30 AM to 6:30 PM, Monday to Friday',
      notice_period: customValues.notice_period || '30',
      notice_period_confirmed: customValues.notice_period_confirmed || '60',
      last_working_date: customValues.last_working_date || '[Last Working Date]',
      responsibilities: customValues.responsibilities || '<li>Key responsibilities as per role</li>',
      performance_rating: customValues.performance_rating || 'satisfactory',
      qualities: customValues.qualities || 'dedicated, hardworking, and a team player',
      purpose: customValues.purpose || 'personal records',
    };

    // Replace all placeholders
    Object.entries(replacements).forEach(([key, value]) => {
      const regex = new RegExp(`{{${key}}}`, 'g');
      html = html.replace(regex, value || `[${key}]`);
    });

    setPreviewHtml(html);
  };

  const handleGenerateDocument = async () => {
    if (!selectedEmployee) {
      toast.error('Please select an employee');
      return;
    }

    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const docData = {
        document_type: selectedDocType,
        employee_id: selectedEmployee.employee_id,
        employee_name: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`,
        content: previewHtml,
        custom_values: customValues,
      };

      // Save to backend
      const response = await fetch(`${API}/document-history`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(docData)
      });

      if (response.ok) {
        const result = await response.json();
        // Add to local state with backend ID
        const newDoc = {
          id: result.id,
          document_type: selectedDocType,
          employee_id: selectedEmployee.employee_id,
          employee_name: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`,
          generated_at: new Date().toISOString(),
          generated_by_name: user?.full_name,
          content: previewHtml,
        };
        setGeneratedDocs(prev => [newDoc, ...prev]);
        setDocumentHistory(prev => [newDoc, ...prev]);
        toast.success(`${DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name} generated and saved to history`);
      } else {
        // Fallback to local storage only
        const newDoc = {
          id: Date.now(),
          document_type: selectedDocType,
          employee_id: selectedEmployee.employee_id,
          employee_name: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`,
          generated_at: new Date().toISOString(),
          generated_by_name: user?.full_name,
          content: previewHtml,
        };
        setGeneratedDocs(prev => [newDoc, ...prev]);
        toast.success(`${DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name} generated successfully`);
      }
      setShowPreview(true);
    } catch (error) {
      console.error('Failed to save document:', error);
      toast.error('Failed to generate document');
    } finally {
      setGenerating(false);
    }
  };

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>D&V Business Consulting - ${DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name}</title>
        <style>
          body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            line-height: 1.6;
          }
          .letterhead {
            text-align: center;
            border-bottom: 2px solid #f97316;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          .logo-text {
            font-size: 24px;
            font-weight: bold;
            color: #f97316;
          }
          .company-info {
            font-size: 12px;
            color: #666;
          }
          .footer {
            position: fixed;
            bottom: 20px;
            left: 40px;
            right: 40px;
            text-align: center;
            font-size: 10px;
            color: #666;
            border-top: 1px solid #ddd;
            padding-top: 10px;
          }
          @media print {
            body { margin: 20px; }
          }
        </style>
      </head>
      <body>
        <div class="letterhead">
          <div class="logo-text">D&V Business Consulting</div>
          <div class="company-info">
            Business Process Optimization | HR Consulting | Digital Transformation<br/>
            123 Business Park, Bangalore - 560001 | +91 80 1234 5678 | hr@dvbconsulting.com
          </div>
        </div>
        ${previewHtml}
        <div class="footer">
          D&V Business Consulting Pvt. Ltd. | CIN: U74999KA2020PTC123456 | www.dvbconsulting.com
        </div>
      </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  const handleDownload = () => {
    const docType = DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name || 'Document';
    const filename = `${docType.replace(/\s+/g, '_')}_${selectedEmployee?.employee_id}_${new Date().toISOString().split('T')[0]}.html`;
    
    const content = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${docType} - ${selectedEmployee?.first_name} ${selectedEmployee?.last_name}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
          .letterhead { text-align: center; border-bottom: 2px solid #f97316; padding-bottom: 20px; margin-bottom: 30px; }
          .logo-text { font-size: 24px; font-weight: bold; color: #f97316; }
          .company-info { font-size: 12px; color: #666; }
        </style>
      </head>
      <body>
        <div class="letterhead">
          <div class="logo-text">D&V Business Consulting</div>
          <div class="company-info">Business Process Optimization | HR Consulting | Digital Transformation</div>
        </div>
        ${previewHtml}
      </body>
      </html>
    `;

    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Document downloaded');
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(previewHtml);
    toast.success('Content copied to clipboard');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="document-builder">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Document Builder</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Generate customizable employment documents for employees
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/letter-management')}>
            <FileText className="w-4 h-4 mr-2" />
            Letter Templates
          </Button>
        </div>
      </div>

      {/* Document Type Selection */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Select Document Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {DOCUMENT_TYPES.map((docType) => {
              const Icon = docType.icon;
              const isSelected = selectedDocType === docType.id;
              return (
                <button
                  key={docType.id}
                  onClick={() => setSelectedDocType(docType.id)}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    isSelected 
                      ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' 
                      : 'border-zinc-200 dark:border-zinc-700 hover:border-emerald-300'
                  }`}
                  data-testid={`doc-type-${docType.id}`}
                >
                  <Icon className={`w-6 h-6 mb-2 ${isSelected ? 'text-emerald-600' : 'text-zinc-400'}`} />
                  <p className={`font-medium text-sm ${isSelected ? 'text-emerald-700 dark:text-emerald-400' : ''}`}>
                    {docType.name}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">{docType.description}</p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Configuration */}
        <div className="space-y-4">
          {/* Employee Selection */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <User className="w-4 h-4" />
                Select Employee
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Select 
                value={selectedEmployee?.id || ''} 
                onValueChange={(v) => {
                  const emp = employees.find(e => e.id === v);
                  setSelectedEmployee(emp);
                }}
              >
                <SelectTrigger data-testid="employee-select">
                  <SelectValue placeholder="Choose an employee..." />
                </SelectTrigger>
                <SelectContent>
                  {employees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-zinc-500">{emp.employee_id}</span>
                        <span>{emp.first_name} {emp.last_name}</span>
                        <Badge variant="outline" className="text-xs">{emp.department || emp.primary_department}</Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {selectedEmployee && (
                <div className="mt-4 p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg text-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-zinc-500">ID:</span>
                      <span className="ml-2 font-mono">{selectedEmployee.employee_id}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Department:</span>
                      <span className="ml-2">{selectedEmployee.department || selectedEmployee.primary_department}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Designation:</span>
                      <span className="ml-2">{selectedEmployee.designation}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Joining:</span>
                      <span className="ml-2">{selectedEmployee.joining_date?.split('T')[0]}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Custom Values */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Edit className="w-4 h-4" />
                Custom Values
              </CardTitle>
              <CardDescription className="text-xs">
                Override default values in the document
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">Annual CTC (₹)</Label>
                  <Input
                    placeholder="e.g., 800000"
                    value={customValues.ctc || ''}
                    onChange={(e) => setCustomValues(prev => ({ ...prev, ctc: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Location</Label>
                  <Input
                    placeholder="e.g., Bangalore"
                    value={customValues.location || ''}
                    onChange={(e) => setCustomValues(prev => ({ ...prev, location: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Reporting Manager</Label>
                  <Input
                    placeholder="Manager name"
                    value={customValues.reporting_manager || ''}
                    onChange={(e) => setCustomValues(prev => ({ ...prev, reporting_manager: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Notice Period (days)</Label>
                  <Input
                    placeholder="e.g., 30"
                    value={customValues.notice_period || ''}
                    onChange={(e) => setCustomValues(prev => ({ ...prev, notice_period: e.target.value }))}
                  />
                </div>
              </div>

              {(selectedDocType === 'experience_letter') && (
                <>
                  <div className="space-y-1">
                    <Label className="text-xs">Last Working Date</Label>
                    <Input
                      type="date"
                      value={customValues.last_working_date || ''}
                      onChange={(e) => setCustomValues(prev => ({ ...prev, last_working_date: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Performance Rating</Label>
                    <Select 
                      value={customValues.performance_rating || ''}
                      onValueChange={(v) => setCustomValues(prev => ({ ...prev, performance_rating: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select rating" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="excellent">Excellent</SelectItem>
                        <SelectItem value="very good">Very Good</SelectItem>
                        <SelectItem value="good">Good</SelectItem>
                        <SelectItem value="satisfactory">Satisfactory</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Template Editor */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Template Editor
                </CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={resetTemplate}>
                    Reset
                  </Button>
                  <Button size="sm" variant="outline" onClick={saveTemplate}>
                    <Save className="w-3 h-3 mr-1" />
                    Save
                  </Button>
                </div>
              </div>
              <CardDescription className="text-xs">
                Edit the HTML template. Use {`{{placeholder}}`} for dynamic values.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={templateContent}
                onChange={(e) => setTemplateContent(e.target.value)}
                className="font-mono text-xs h-64"
                placeholder="Enter HTML template..."
              />
              <div className="mt-2 flex flex-wrap gap-1">
                <Badge variant="secondary" className="text-xs">{`{{employee_name}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{employee_id}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{designation}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{department}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{joining_date}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{ctc}}`}</Badge>
                <Badge variant="secondary" className="text-xs">{`{{date}}`}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Preview */}
        <div className="space-y-4">
          <Card className="h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Eye className="w-4 h-4" />
                  Live Preview
                </CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={copyToClipboard} disabled={!previewHtml}>
                    <Copy className="w-3 h-3 mr-1" />
                    Copy
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleDownload} disabled={!previewHtml}>
                    <Download className="w-3 h-3 mr-1" />
                    Download
                  </Button>
                  <Button size="sm" variant="outline" onClick={handlePrint} disabled={!previewHtml}>
                    <Printer className="w-3 h-3 mr-1" />
                    Print
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Letterhead Preview */}
              <div className="border rounded-lg bg-white overflow-hidden">
                <div className="p-4 border-b bg-gradient-to-r from-orange-50 to-white">
                  <div className="text-center">
                    <h2 className="text-xl font-bold text-orange-500">D&V Business Consulting</h2>
                    <p className="text-xs text-zinc-500">Business Process Optimization | HR Consulting | Digital Transformation</p>
                  </div>
                </div>
                <div 
                  ref={printRef}
                  className="p-6 min-h-[400px] text-sm text-zinc-800"
                  dangerouslySetInnerHTML={{ __html: previewHtml || '<p class="text-zinc-400 italic">Select an employee to see preview...</p>' }}
                />
                <div className="p-3 border-t bg-zinc-50 text-center text-xs text-zinc-500">
                  D&V Business Consulting Pvt. Ltd. | CIN: U74999KA2020PTC123456
                </div>
              </div>

              {/* Generate Button */}
              {canGenerate && (
                <Button 
                  className="w-full mt-4 bg-emerald-600 hover:bg-emerald-700"
                  onClick={handleGenerateDocument}
                  disabled={!selectedEmployee || generating}
                  data-testid="generate-document-btn"
                >
                  {generating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FileSignature className="w-4 h-4 mr-2" />
                      Generate {DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name}
                    </>
                  )}
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Generated Documents History */}
      {generatedDocs.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Recently Generated Documents ({generatedDocs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {generatedDocs.slice(0, 5).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded">
                      <FileText className="w-4 h-4 text-emerald-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">
                        {DOCUMENT_TYPES.find(d => d.id === doc.type)?.name}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {doc.employee_name} ({doc.employee_id}) • {new Date(doc.generated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      size="sm" 
                      variant="ghost"
                      onClick={() => {
                        setPreviewHtml(doc.content);
                        setShowPreview(true);
                      }}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              Document Generated
            </DialogTitle>
            <DialogDescription>
              Your document is ready. You can print or download it.
            </DialogDescription>
          </DialogHeader>
          
          <div className="border rounded-lg bg-white overflow-hidden my-4">
            <div className="p-4 border-b bg-gradient-to-r from-orange-50 to-white">
              <div className="text-center">
                <h2 className="text-xl font-bold text-orange-500">D&V Business Consulting</h2>
                <p className="text-xs text-zinc-500">Business Process Optimization | HR Consulting</p>
              </div>
            </div>
            <div 
              className="p-6 text-sm text-zinc-800"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
            <div className="p-3 border-t bg-zinc-50 text-center text-xs text-zinc-500">
              D&V Business Consulting Pvt. Ltd.
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreview(false)}>
              Close
            </Button>
            <Button variant="outline" onClick={handleDownload}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button onClick={handlePrint} className="bg-emerald-600 hover:bg-emerald-700">
              <Printer className="w-4 h-4 mr-2" />
              Print
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DocumentBuilder;
