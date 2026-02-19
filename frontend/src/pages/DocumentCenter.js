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
  FileText, Download, Eye, Plus, Edit, Trash2, Save, Printer, Send,
  User, Building2, Calendar, Mail, Phone, Award, Briefcase, Clock,
  CheckCircle, AlertCircle, Copy, FileSignature, History, Search,
  Filter, RefreshCw, MoreVertical, Archive, X
} from 'lucide-react';
import { toast } from 'sonner';

// Document types configuration
const DOCUMENT_TYPES = [
  { 
    id: 'offer_letter', 
    name: 'Offer Letter', 
    icon: FileText,
    color: 'blue',
    description: 'Job offer for new hires'
  },
  { 
    id: 'appointment_letter', 
    name: 'Appointment Letter', 
    icon: Award,
    color: 'purple',
    description: 'Official appointment confirmation'
  },
  { 
    id: 'confirmation_letter', 
    name: 'Confirmation Letter', 
    icon: CheckCircle,
    color: 'green',
    description: 'Post-probation confirmation'
  },
  { 
    id: 'experience_letter', 
    name: 'Experience Letter', 
    icon: Briefcase,
    color: 'orange',
    description: 'Work experience certificate'
  },
];

// Default templates for each document type
const DEFAULT_TEMPLATES = {
  offer_letter: {
    name: 'Standard Offer Letter',
    subject: 'Job Offer - {{designation}} at D&V Business Consulting',
    content: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>To,</strong><br/>{{employee_name}}<br/>{{email}}</p>

<p><strong>Subject: Offer of Employment - {{designation}}</strong></p>

<p>Dear {{employee_name}},</p>

<p>We are pleased to offer you the position of <strong>{{designation}}</strong> in the <strong>{{department}}</strong> department at D&V Business Consulting.</p>

<p><strong>Terms of Employment:</strong></p>
<ul>
<li><strong>Position:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Reporting To:</strong> {{reporting_manager}}</li>
<li><strong>Joining Date:</strong> {{joining_date}}</li>
<li><strong>Annual CTC:</strong> ₹{{ctc}}</li>
<li><strong>Location:</strong> {{location}}</li>
</ul>

<p><strong>Probation Period:</strong> {{probation_months}} months from date of joining.</p>

<p>This offer is contingent upon successful background verification and submission of required documents.</p>

<p>Please confirm your acceptance by {{acceptance_deadline}}.</p>

<p>We look forward to welcoming you!</p>

<p>Best Regards,<br/>{{hr_name}}<br/>HR Manager<br/>D&V Business Consulting</p>
</div>`
  },
  appointment_letter: {
    name: 'Standard Appointment Letter',
    subject: 'Letter of Appointment - {{employee_id}}',
    content: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/APPT/{{employee_id}}</p>

<p><strong>To,</strong><br/>{{employee_name}}<br/>Employee ID: {{employee_id}}</p>

<p><strong>Subject: Letter of Appointment</strong></p>

<p>Dear {{employee_name}},</p>

<p>We are pleased to appoint you as <strong>{{designation}}</strong> in the <strong>{{department}}</strong> department, effective from <strong>{{joining_date}}</strong>.</p>

<p><strong>Terms and Conditions:</strong></p>
<ol>
<li><strong>Employee ID:</strong> {{employee_id}}</li>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Reporting To:</strong> {{reporting_manager}}</li>
<li><strong>Annual CTC:</strong> ₹{{ctc}}</li>
<li><strong>Probation Period:</strong> {{probation_months}} months</li>
<li><strong>Notice Period:</strong> {{notice_period}} days</li>
</ol>

<p>Welcome to the D&V Business Consulting family!</p>

<p>For D&V Business Consulting<br/>{{hr_name}}<br/>HR Manager</p>

<hr style="margin-top: 40px;"/>
<p><strong>Employee Acceptance</strong></p>
<p>I accept the terms and conditions of this appointment.</p>
<p>Signature: __________________ Date: ______________</p>
</div>`
  },
  confirmation_letter: {
    name: 'Standard Confirmation Letter',
    subject: 'Confirmation of Employment - {{employee_id}}',
    content: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/CONF/{{employee_id}}</p>

<p><strong>To,</strong><br/>{{employee_name}}<br/>Employee ID: {{employee_id}}<br/>{{department}}</p>

<p><strong>Subject: Confirmation of Employment</strong></p>

<p>Dear {{employee_name}},</p>

<p>We are pleased to confirm your services with effect from <strong>{{confirmation_date}}</strong>, based on your satisfactory performance during the probation period.</p>

<p><strong>Details:</strong></p>
<ul>
<li><strong>Employee ID:</strong> {{employee_id}}</li>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Date of Joining:</strong> {{joining_date}}</li>
<li><strong>Confirmation Date:</strong> {{confirmation_date}}</li>
<li><strong>Revised CTC:</strong> ₹{{ctc}}</li>
</ul>

<p>Congratulations! We look forward to your continued contributions.</p>

<p>For D&V Business Consulting<br/>{{hr_name}}<br/>HR Manager</p>
</div>`
  },
  experience_letter: {
    name: 'Standard Experience Letter',
    subject: 'Experience Certificate - {{employee_name}}',
    content: `<div style="font-family: Arial, sans-serif; line-height: 1.6;">
<p><strong>Date:</strong> {{date}}</p>
<p><strong>Ref No:</strong> DVBC/EXP/{{employee_id}}</p>

<p><strong>TO WHOM IT MAY CONCERN</strong></p>

<p>This is to certify that <strong>{{employee_name}}</strong> (Employee ID: {{employee_id}}) was employed with D&V Business Consulting from <strong>{{joining_date}}</strong> to <strong>{{last_working_date}}</strong>.</p>

<p><strong>Employment Details:</strong></p>
<ul>
<li><strong>Designation:</strong> {{designation}}</li>
<li><strong>Department:</strong> {{department}}</li>
<li><strong>Last Drawn CTC:</strong> ₹{{ctc}} per annum</li>
</ul>

<p>During the tenure, {{employee_name}} demonstrated {{qualities}} and performed their duties satisfactorily.</p>

<p>We wish {{employee_name}} all the best in future endeavors.</p>

<p>For D&V Business Consulting<br/>{{hr_name}}<br/>HR Manager</p>

<p style="margin-top: 20px; font-size: 11px; color: #666;"><em>This is a computer-generated document.</em></p>
</div>`
  }
};

const DocumentCenter = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preSelectedEmployeeId = searchParams.get('employee');
  
  // Main state
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('generate');
  const [employees, setEmployees] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [documentHistory, setDocumentHistory] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_type: {} });
  
  // Generator state
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [selectedDocType, setSelectedDocType] = useState('offer_letter');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [customValues, setCustomValues] = useState({});
  const [previewHtml, setPreviewHtml] = useState('');
  const [generating, setGenerating] = useState(false);
  
  // Dialogs
  const [showPreview, setShowPreview] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [showSendEmailDialog, setShowSendEmailDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [selectedDocForEmail, setSelectedDocForEmail] = useState(null);
  
  // Template form
  const [templateForm, setTemplateForm] = useState({
    document_type: 'offer_letter',
    name: '',
    subject: '',
    content: ''
  });
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDocType, setFilterDocType] = useState('all');
  
  const printRef = useRef();

  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canManage = isAdmin || isHR;

  useEffect(() => {
    fetchAllData();
  }, []);

  useEffect(() => {
    if (selectedDocType && !selectedTemplate) {
      // Set default template content
      const defaultTpl = DEFAULT_TEMPLATES[selectedDocType];
      if (defaultTpl) {
        setTemplateForm(prev => ({
          ...prev,
          content: defaultTpl.content,
          subject: defaultTpl.subject
        }));
      }
    }
  }, [selectedDocType]);

  useEffect(() => {
    if (selectedEmployee) {
      generatePreview();
    }
  }, [selectedEmployee, selectedDocType, selectedTemplate, customValues]);

  useEffect(() => {
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

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [employeesRes, templatesRes, historyRes] = await Promise.all([
        fetch(`${API}/employees`, { headers }),
        fetch(`${API}/document-templates`, { headers }).catch(() => ({ ok: false })),
        fetch(`${API}/document-history?limit=100`, { headers })
      ]);

      if (employeesRes.ok) {
        const data = await employeesRes.json();
        setEmployees(data.filter(e => e.is_active !== false));
      }

      if (templatesRes.ok) {
        const data = await templatesRes.json();
        setTemplates(data);
      }

      if (historyRes.ok) {
        const data = await historyRes.json();
        setDocumentHistory(data);
        
        // Calculate stats
        const statsByType = {};
        data.forEach(doc => {
          statsByType[doc.document_type] = (statsByType[doc.document_type] || 0) + 1;
        });
        setStats({ total: data.length, by_type: statsByType });
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const generatePreview = () => {
    if (!selectedEmployee) {
      setPreviewHtml('');
      return;
    }

    // Get template content
    let templateContent = selectedTemplate?.content || DEFAULT_TEMPLATES[selectedDocType]?.content || '';
    
    const today = new Date();
    const joiningDate = selectedEmployee.joining_date 
      ? new Date(selectedEmployee.joining_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
      : '';
    
    const probationMonths = selectedEmployee.department?.toLowerCase().includes('consult') ? 6 : 3;
    const confirmationDate = selectedEmployee.joining_date 
      ? new Date(new Date(selectedEmployee.joining_date).setMonth(new Date(selectedEmployee.joining_date).getMonth() + probationMonths)).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
      : '';

    // Build replacements from employee data + custom values
    const replacements = {
      date: today.toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' }),
      employee_name: `${selectedEmployee.first_name || ''} ${selectedEmployee.last_name || ''}`.trim(),
      employee_id: selectedEmployee.employee_id || '',
      email: selectedEmployee.email || selectedEmployee.personal_email || '',
      phone: selectedEmployee.phone || selectedEmployee.contact_number || '',
      designation: selectedEmployee.designation || customValues.designation || '[Designation]',
      department: selectedEmployee.department || selectedEmployee.primary_department || '[Department]',
      reporting_manager: selectedEmployee.reporting_manager_name || customValues.reporting_manager || '[Reporting Manager]',
      joining_date: joiningDate || customValues.joining_date || '[Joining Date]',
      ctc: customValues.ctc || selectedEmployee.ctc || selectedEmployee.salary || '[CTC]',
      location: customValues.location || selectedEmployee.work_location || 'Bangalore',
      probation_months: probationMonths,
      confirmation_date: confirmationDate || customValues.confirmation_date || '[Confirmation Date]',
      acceptance_deadline: customValues.acceptance_deadline || new Date(today.setDate(today.getDate() + 7)).toLocaleDateString('en-IN'),
      hr_name: user?.full_name || 'HR Manager',
      notice_period: customValues.notice_period || '30',
      last_working_date: customValues.last_working_date || '[Last Working Date]',
      qualities: customValues.qualities || 'professionalism, dedication, and teamwork',
      ...customValues
    };

    // Replace all placeholders
    let html = templateContent;
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
        template_id: selectedTemplate?.id || null,
      };

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
        toast.success(`${DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name} generated and saved!`);
        
        // Refresh history
        fetchAllData();
        setShowPreview(true);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to generate document');
      }
    } catch (error) {
      console.error('Error generating document:', error);
      toast.error('Failed to generate document');
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateForm.name || !templateForm.content) {
      toast.error('Please fill in template name and content');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const url = editingTemplate 
        ? `${API}/document-templates/${editingTemplate.id}`
        : `${API}/document-templates`;
      
      const response = await fetch(url, {
        method: editingTemplate ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(templateForm)
      });

      if (response.ok) {
        toast.success(`Template ${editingTemplate ? 'updated' : 'created'} successfully`);
        setShowTemplateDialog(false);
        setEditingTemplate(null);
        setTemplateForm({ document_type: 'offer_letter', name: '', subject: '', content: '' });
        fetchAllData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save template');
      }
    } catch (error) {
      toast.error('Error saving template');
    }
  };

  const handleSendEmail = async () => {
    if (!selectedDocForEmail) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/document-history/${selectedDocForEmail.id}/send-email`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          to_email: selectedDocForEmail.employee_email || selectedEmployee?.email
        })
      });

      if (response.ok) {
        toast.success('Document sent via email!');
        setShowSendEmailDialog(false);
        setSelectedDocForEmail(null);
        fetchAllData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to send email');
      }
    } catch (error) {
      toast.error('Error sending email');
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
          body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
          .letterhead { text-align: center; border-bottom: 2px solid #f97316; padding-bottom: 20px; margin-bottom: 30px; }
          .logo-text { font-size: 24px; font-weight: bold; color: #f97316; }
          .company-info { font-size: 12px; color: #666; }
          .footer { position: fixed; bottom: 20px; left: 40px; right: 40px; text-align: center; font-size: 10px; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }
          @media print { body { margin: 20px; } }
        </style>
      </head>
      <body>
        <div class="letterhead">
          <div class="logo-text">D&V Business Consulting</div>
          <div class="company-info">Business Process Optimization | HR Consulting | Digital Transformation<br/>
          123 Business Park, Bangalore - 560001 | +91 80 1234 5678 | hr@dvbconsulting.com</div>
        </div>
        ${previewHtml}
        <div class="footer">D&V Business Consulting Pvt. Ltd. | CIN: U74999KA2020PTC123456</div>
      </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  const handleDownload = (doc = null) => {
    const content = doc?.content || previewHtml;
    const docType = doc?.document_type || selectedDocType;
    const empId = doc?.employee_id || selectedEmployee?.employee_id;
    const typeName = DOCUMENT_TYPES.find(d => d.id === docType)?.name || 'Document';
    const filename = `${typeName.replace(/\s+/g, '_')}_${empId}_${new Date().toISOString().split('T')[0]}.html`;
    
    const htmlContent = `<!DOCTYPE html><html><head><title>${typeName}</title>
      <style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.6;}
      .letterhead{text-align:center;border-bottom:2px solid #f97316;padding-bottom:20px;margin-bottom:30px;}
      .logo-text{font-size:24px;font-weight:bold;color:#f97316;}</style>
      </head><body>
      <div class="letterhead"><div class="logo-text">D&V Business Consulting</div></div>
      ${content}</body></html>`;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Document downloaded');
  };

  // Filter documents
  const filteredHistory = documentHistory.filter(doc => {
    const matchesSearch = searchQuery === '' || 
      doc.employee_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.employee_id?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterDocType === 'all' || doc.document_type === filterDocType;
    return matchesSearch && matchesType;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500">Loading Document Center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="document-center">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <FileText className="w-6 h-6 text-orange-500" />
            Document Center
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Generate, manage, and track all employee documents
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setShowTemplateDialog(true)} variant="outline">
            <Plus className="w-4 h-4 mr-2" />
            New Template
          </Button>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
                <FileText className="w-5 h-5 text-zinc-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-xs text-zinc-500">Total Documents</p>
              </div>
            </div>
          </CardContent>
        </Card>
        {DOCUMENT_TYPES.map(docType => (
          <Card key={docType.id}>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-${docType.color}-100 dark:bg-${docType.color}-900/30`}>
                  <docType.icon className={`w-5 h-5 text-${docType.color}-600`} />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.by_type[docType.id] || 0}</p>
                  <p className="text-xs text-zinc-500 truncate">{docType.name.split(' ')[0]}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-lg grid-cols-3">
          <TabsTrigger value="generate" data-testid="generate-tab">
            <FileSignature className="w-4 h-4 mr-2" />
            Generate
          </TabsTrigger>
          <TabsTrigger value="history" data-testid="history-tab">
            <History className="w-4 h-4 mr-2" />
            History ({documentHistory.length})
          </TabsTrigger>
          <TabsTrigger value="templates" data-testid="templates-tab">
            <FileText className="w-4 h-4 mr-2" />
            Templates
          </TabsTrigger>
        </TabsList>

        {/* Generate Tab */}
        <TabsContent value="generate" className="space-y-6 mt-4">
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
                          ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20' 
                          : 'border-zinc-200 dark:border-zinc-700 hover:border-orange-300'
                      }`}
                      data-testid={`doc-type-${docType.id}`}
                    >
                      <Icon className={`w-6 h-6 mb-2 ${isSelected ? 'text-orange-600' : 'text-zinc-400'}`} />
                      <p className={`font-medium text-sm ${isSelected ? 'text-orange-700 dark:text-orange-400' : ''}`}>
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
                    <div className="mt-4 p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg text-sm space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-zinc-500">Employee ID:</span>
                          <span className="ml-2 font-mono font-medium">{selectedEmployee.employee_id}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Email:</span>
                          <span className="ml-2">{selectedEmployee.email || selectedEmployee.personal_email}</span>
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
                          <span className="text-zinc-500">Reporting To:</span>
                          <span className="ml-2">{selectedEmployee.reporting_manager_name || '-'}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Joining:</span>
                          <span className="ml-2">{selectedEmployee.joining_date?.split('T')[0] || '-'}</span>
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
                  <CardDescription className="text-xs">Override auto-filled values</CardDescription>
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
                      <Label className="text-xs">Notice Period (days)</Label>
                      <Input
                        placeholder="e.g., 30"
                        value={customValues.notice_period || ''}
                        onChange={(e) => setCustomValues(prev => ({ ...prev, notice_period: e.target.value }))}
                      />
                    </div>
                    {selectedDocType === 'experience_letter' && (
                      <div className="space-y-1">
                        <Label className="text-xs">Last Working Date</Label>
                        <Input
                          type="date"
                          value={customValues.last_working_date || ''}
                          onChange={(e) => setCustomValues(prev => ({ ...prev, last_working_date: e.target.value }))}
                        />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Panel - Preview */}
            <Card className="h-fit">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    Live Preview
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleDownload()} disabled={!previewHtml}>
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
                <div className="border rounded-lg bg-white overflow-hidden max-h-[500px] overflow-y-auto">
                  <div className="p-4 border-b bg-gradient-to-r from-orange-50 to-white sticky top-0">
                    <div className="text-center">
                      <h2 className="text-xl font-bold text-orange-500">D&V Business Consulting</h2>
                      <p className="text-xs text-zinc-500">Business Process Optimization | HR Consulting</p>
                    </div>
                  </div>
                  <div 
                    ref={printRef}
                    className="p-6 min-h-[300px] text-sm text-zinc-800"
                    dangerouslySetInnerHTML={{ __html: previewHtml || '<p class="text-zinc-400 italic">Select an employee to see preview...</p>' }}
                  />
                  <div className="p-3 border-t bg-zinc-50 text-center text-xs text-zinc-500 sticky bottom-0">
                    D&V Business Consulting Pvt. Ltd. | CIN: U74999KA2020PTC123456
                  </div>
                </div>

                {/* Generate Button */}
                {canManage && (
                  <Button 
                    className="w-full mt-4 bg-orange-600 hover:bg-orange-700"
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
                        Generate & Save {DOCUMENT_TYPES.find(d => d.id === selectedDocType)?.name}
                      </>
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-4 mt-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="Search by name or employee ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filterDocType} onValueChange={setFilterDocType}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {DOCUMENT_TYPES.map(dt => (
                  <SelectItem key={dt.id} value={dt.id}>{dt.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon" onClick={fetchAllData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>

          {/* Documents List */}
          <Card>
            <CardContent className="pt-4">
              {filteredHistory.length === 0 ? (
                <div className="text-center py-12 text-zinc-500">
                  <FileText className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
                  <p className="font-medium">No documents found</p>
                  <p className="text-sm">Generate documents from the Generate tab</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredHistory.map((doc) => {
                    const docTypeInfo = DOCUMENT_TYPES.find(d => d.id === doc.document_type);
                    const Icon = docTypeInfo?.icon || FileText;
                    return (
                      <div key={doc.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                        <div className="flex items-center gap-4">
                          <div className={`p-3 rounded-lg bg-${docTypeInfo?.color || 'zinc'}-100 dark:bg-${docTypeInfo?.color || 'zinc'}-900/30`}>
                            <Icon className={`w-5 h-5 text-${docTypeInfo?.color || 'zinc'}-600`} />
                          </div>
                          <div>
                            <p className="font-medium">{docTypeInfo?.name || doc.document_type}</p>
                            <p className="text-sm text-zinc-600 dark:text-zinc-400">
                              {doc.employee_name} <span className="text-zinc-400 font-mono">({doc.employee_id})</span>
                            </p>
                            <p className="text-xs text-zinc-500 mt-1">
                              Generated by {doc.generated_by_name} • {new Date(doc.generated_at).toLocaleDateString('en-IN', { 
                                day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={doc.status === 'sent' ? 'default' : 'secondary'} className="text-xs">
                            {doc.status || 'Generated'}
                          </Badge>
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => {
                              setPreviewHtml(doc.content);
                              setSelectedDocType(doc.document_type);
                              setShowPreview(true);
                            }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleDownload(doc)}>
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => {
                              setSelectedDocForEmail(doc);
                              setShowSendEmailDialog(true);
                            }}
                          >
                            <Send className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-zinc-500">Manage reusable document templates</p>
            {canManage && (
              <Button onClick={() => {
                setEditingTemplate(null);
                setTemplateForm({ document_type: 'offer_letter', name: '', subject: '', content: '' });
                setShowTemplateDialog(true);
              }}>
                <Plus className="w-4 h-4 mr-2" />
                Create Template
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Default Templates */}
            {DOCUMENT_TYPES.map(docType => {
              const defaultTpl = DEFAULT_TEMPLATES[docType.id];
              const Icon = docType.icon;
              return (
                <Card key={docType.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Icon className={`w-4 h-4 text-${docType.color}-600`} />
                        {docType.name}
                      </CardTitle>
                      <Badge variant="secondary">Default</Badge>
                    </div>
                    <CardDescription className="text-xs">{defaultTpl?.name}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-zinc-500 mb-3">Subject: {defaultTpl?.subject}</p>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="w-full"
                      onClick={() => {
                        setSelectedDocType(docType.id);
                        setActiveTab('generate');
                      }}
                    >
                      Use Template
                    </Button>
                  </CardContent>
                </Card>
              );
            })}

            {/* Custom Templates */}
            {templates.map(tpl => {
              const docTypeInfo = DOCUMENT_TYPES.find(d => d.id === tpl.document_type);
              const Icon = docTypeInfo?.icon || FileText;
              return (
                <Card key={tpl.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Icon className={`w-4 h-4 text-${docTypeInfo?.color || 'zinc'}-600`} />
                        {tpl.name}
                      </CardTitle>
                      <Badge>Custom</Badge>
                    </div>
                    <CardDescription className="text-xs">{docTypeInfo?.name}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-zinc-500 mb-3">Subject: {tpl.subject}</p>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="flex-1"
                        onClick={() => {
                          setSelectedTemplate(tpl);
                          setSelectedDocType(tpl.document_type);
                          setActiveTab('generate');
                        }}
                      >
                        Use
                      </Button>
                      {canManage && (
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => {
                            setEditingTemplate(tpl);
                            setTemplateForm({
                              document_type: tpl.document_type,
                              name: tpl.name,
                              subject: tpl.subject,
                              content: tpl.content
                            });
                            setShowTemplateDialog(true);
                          }}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              Document Preview
            </DialogTitle>
          </DialogHeader>
          
          <div className="border rounded-lg bg-white overflow-hidden my-4">
            <div className="p-4 border-b bg-gradient-to-r from-orange-50 to-white">
              <div className="text-center">
                <h2 className="text-xl font-bold text-orange-500">D&V Business Consulting</h2>
                <p className="text-xs text-zinc-500">Business Process Optimization | HR Consulting</p>
              </div>
            </div>
            <div className="p-6 text-sm text-zinc-800" dangerouslySetInnerHTML={{ __html: previewHtml }} />
            <div className="p-3 border-t bg-zinc-50 text-center text-xs text-zinc-500">
              D&V Business Consulting Pvt. Ltd.
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreview(false)}>Close</Button>
            <Button variant="outline" onClick={() => handleDownload()}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button onClick={handlePrint} className="bg-orange-600 hover:bg-orange-700">
              <Printer className="w-4 h-4 mr-2" />
              Print
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Template' : 'Create New Template'}</DialogTitle>
            <DialogDescription>Create reusable templates with placeholders like {`{{employee_name}}`}</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Document Type</Label>
                <Select value={templateForm.document_type} onValueChange={(v) => setTemplateForm(prev => ({ ...prev, document_type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DOCUMENT_TYPES.map(dt => (
                      <SelectItem key={dt.id} value={dt.id}>{dt.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Template Name</Label>
                <Input
                  placeholder="e.g., Standard Offer Letter"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email Subject</Label>
              <Input
                placeholder="e.g., Job Offer - {{designation}} at D&V"
                value={templateForm.subject}
                onChange={(e) => setTemplateForm(prev => ({ ...prev, subject: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Content (HTML with placeholders)</Label>
              <Textarea
                className="font-mono text-xs h-64"
                placeholder="<div>Dear {{employee_name}},...</div>"
                value={templateForm.content}
                onChange={(e) => setTemplateForm(prev => ({ ...prev, content: e.target.value }))}
              />
            </div>
            <div className="flex flex-wrap gap-1">
              <span className="text-xs text-zinc-500 mr-2">Placeholders:</span>
              {['employee_name', 'employee_id', 'email', 'designation', 'department', 'reporting_manager', 'joining_date', 'ctc', 'location', 'date'].map(p => (
                <Badge key={p} variant="secondary" className="text-xs cursor-pointer" onClick={() => {
                  setTemplateForm(prev => ({ ...prev, content: prev.content + `{{${p}}}` }));
                }}>
                  {`{{${p}}}`}
                </Badge>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveTemplate} className="bg-orange-600 hover:bg-orange-700">
              <Save className="w-4 h-4 mr-2" />
              {editingTemplate ? 'Update' : 'Create'} Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Email Dialog */}
      <Dialog open={showSendEmailDialog} onOpenChange={setShowSendEmailDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-600" />
              Send Document via Email
            </DialogTitle>
            <DialogDescription>
              Send this document to the employee's email address
            </DialogDescription>
          </DialogHeader>
          
          {selectedDocForEmail && (
            <div className="py-4 space-y-3">
              <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg text-sm">
                <p><strong>Document:</strong> {DOCUMENT_TYPES.find(d => d.id === selectedDocForEmail.document_type)?.name}</p>
                <p><strong>Employee:</strong> {selectedDocForEmail.employee_name} ({selectedDocForEmail.employee_id})</p>
                <p><strong>Email:</strong> {selectedDocForEmail.employee_email || 'Will use employee email from records'}</p>
              </div>
              <p className="text-sm text-zinc-500">
                The document will be sent as an HTML email with the company letterhead.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSendEmailDialog(false)}>Cancel</Button>
            <Button onClick={handleSendEmail} className="bg-blue-600 hover:bg-blue-700">
              <Send className="w-4 h-4 mr-2" />
              Send Email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DocumentCenter;
