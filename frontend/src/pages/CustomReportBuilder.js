import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import { 
  FileSpreadsheet, Download, Eye, Filter, Database, 
  Users, Briefcase, DollarSign, Calendar, CheckCircle,
  ChevronDown, ChevronRight, Columns, Settings, FileText,
  Table, BarChart3, PieChart, ArrowRight, Sparkles, X
} from 'lucide-react';
import { toast } from 'sonner';

// Data sources available based on role
const DATA_SOURCES = {
  leads: {
    name: 'Leads',
    icon: Users,
    color: 'bg-blue-500',
    roles: ['admin', 'sales_manager', 'sales_executive', 'principal_consultant'],
    fields: [
      { key: 'first_name', label: 'First Name', type: 'text' },
      { key: 'last_name', label: 'Last Name', type: 'text' },
      { key: 'email', label: 'Email', type: 'text' },
      { key: 'phone', label: 'Phone', type: 'text' },
      { key: 'company', label: 'Company', type: 'text' },
      { key: 'job_title', label: 'Job Title', type: 'text' },
      { key: 'status', label: 'Status', type: 'select', options: ['new', 'contacted', 'qualified', 'proposal', 'agreement', 'closed', 'lost'] },
      { key: 'lead_score', label: 'Lead Score', type: 'number' },
      { key: 'source', label: 'Source', type: 'text' },
      { key: 'created_at', label: 'Created Date', type: 'date' },
      { key: 'assigned_to', label: 'Assigned To', type: 'text' },
    ]
  },
  employees: {
    name: 'Employees',
    icon: Users,
    color: 'bg-purple-500',
    roles: ['admin', 'hr_manager'],
    fields: [
      { key: 'employee_id', label: 'Employee ID', type: 'text' },
      { key: 'first_name', label: 'First Name', type: 'text' },
      { key: 'last_name', label: 'Last Name', type: 'text' },
      { key: 'email', label: 'Email', type: 'text' },
      { key: 'phone', label: 'Phone', type: 'text' },
      { key: 'department', label: 'Department', type: 'select', options: ['Sales', 'HR', 'Consulting', 'Finance', 'Operations'] },
      { key: 'designation', label: 'Designation', type: 'text' },
      { key: 'date_of_joining', label: 'Date of Joining', type: 'date' },
      { key: 'reporting_manager', label: 'Reporting Manager', type: 'text' },
      { key: 'is_active', label: 'Active Status', type: 'boolean' },
      { key: 'salary', label: 'Salary', type: 'number' },
    ]
  },
  projects: {
    name: 'Projects',
    icon: Briefcase,
    color: 'bg-emerald-500',
    roles: ['admin', 'principal_consultant', 'consultant', 'manager'],
    fields: [
      { key: 'project_id', label: 'Project ID', type: 'text' },
      { key: 'name', label: 'Project Name', type: 'text' },
      { key: 'client_name', label: 'Client Name', type: 'text' },
      { key: 'status', label: 'Status', type: 'select', options: ['active', 'completed', 'on_hold', 'at_risk'] },
      { key: 'start_date', label: 'Start Date', type: 'date' },
      { key: 'end_date', label: 'End Date', type: 'date' },
      { key: 'budget', label: 'Budget', type: 'number' },
      { key: 'progress', label: 'Progress %', type: 'number' },
      { key: 'assigned_consultant', label: 'Assigned Consultant', type: 'text' },
      { key: 'department', label: 'Department', type: 'text' },
    ]
  },
  attendance: {
    name: 'Attendance',
    icon: Calendar,
    color: 'bg-amber-500',
    roles: ['admin', 'hr_manager'],
    fields: [
      { key: 'employee_id', label: 'Employee ID', type: 'text' },
      { key: 'employee_name', label: 'Employee Name', type: 'text' },
      { key: 'date', label: 'Date', type: 'date' },
      { key: 'check_in', label: 'Check In Time', type: 'time' },
      { key: 'check_out', label: 'Check Out Time', type: 'time' },
      { key: 'status', label: 'Status', type: 'select', options: ['present', 'absent', 'wfh', 'half_day', 'leave'] },
      { key: 'work_hours', label: 'Work Hours', type: 'number' },
      { key: 'department', label: 'Department', type: 'text' },
    ]
  },
  agreements: {
    name: 'Agreements',
    icon: FileText,
    color: 'bg-indigo-500',
    roles: ['admin', 'sales_manager', 'principal_consultant'],
    fields: [
      { key: 'agreement_number', label: 'Agreement Number', type: 'text' },
      { key: 'client_name', label: 'Client Name', type: 'text' },
      { key: 'total_value', label: 'Total Value', type: 'number' },
      { key: 'status', label: 'Status', type: 'select', options: ['draft', 'pending_approval', 'approved', 'signed', 'rejected'] },
      { key: 'created_date', label: 'Created Date', type: 'date' },
      { key: 'valid_until', label: 'Valid Until', type: 'date' },
      { key: 'created_by', label: 'Created By', type: 'text' },
    ]
  },
  payments: {
    name: 'Payments',
    icon: DollarSign,
    color: 'bg-green-500',
    roles: ['admin', 'finance_manager'],
    fields: [
      { key: 'payment_id', label: 'Payment ID', type: 'text' },
      { key: 'project_name', label: 'Project Name', type: 'text' },
      { key: 'client_name', label: 'Client Name', type: 'text' },
      { key: 'amount', label: 'Amount', type: 'number' },
      { key: 'payment_date', label: 'Payment Date', type: 'date' },
      { key: 'payment_mode', label: 'Payment Mode', type: 'select', options: ['bank_transfer', 'cheque', 'cash', 'upi'] },
      { key: 'status', label: 'Status', type: 'select', options: ['pending', 'received', 'overdue'] },
    ]
  }
};

const CustomReportBuilder = () => {
  const { user } = useContext(AuthContext);
  const [step, setStep] = useState(1); // 1: Source, 2: Fields, 3: Filters, 4: Preview
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedFields, setSelectedFields] = useState([]);
  const [filters, setFilters] = useState([]);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportName, setReportName] = useState('');

  // Get available sources based on user role
  const availableSources = Object.entries(DATA_SOURCES).filter(([key, source]) => 
    source.roles.includes(user?.role)
  );

  // Handle source selection
  const handleSourceSelect = (sourceKey) => {
    setSelectedSource(sourceKey);
    setSelectedFields([]);
    setFilters([]);
    setStep(2);
  };

  // Toggle field selection
  const toggleField = (fieldKey) => {
    setSelectedFields(prev => 
      prev.includes(fieldKey) 
        ? prev.filter(f => f !== fieldKey)
        : [...prev, fieldKey]
    );
  };

  // Select all fields
  const selectAllFields = () => {
    if (selectedSource) {
      setSelectedFields(DATA_SOURCES[selectedSource].fields.map(f => f.key));
    }
  };

  // Clear all fields
  const clearAllFields = () => {
    setSelectedFields([]);
  };

  // Add filter
  const addFilter = () => {
    setFilters(prev => [...prev, { field: '', operator: 'equals', value: '' }]);
  };

  // Update filter
  const updateFilter = (index, key, value) => {
    setFilters(prev => prev.map((f, i) => i === index ? { ...f, [key]: value } : f));
  };

  // Remove filter
  const removeFilter = (index) => {
    setFilters(prev => prev.filter((_, i) => i !== index));
  };

  // Generate preview
  const generatePreview = async () => {
    if (!selectedSource || selectedFields.length === 0) {
      toast.error('Please select at least one field');
      return;
    }
    
    setLoading(true);
    // Simulate API call - in production this would call the backend
    setTimeout(() => {
      const mockData = generateMockData();
      setPreviewData(mockData);
      setStep(4);
      setLoading(false);
    }, 1000);
  };

  // Generate mock data for preview
  const generateMockData = () => {
    const source = DATA_SOURCES[selectedSource];
    const rows = [];
    for (let i = 0; i < 5; i++) {
      const row = {};
      selectedFields.forEach(fieldKey => {
        const field = source.fields.find(f => f.key === fieldKey);
        if (field) {
          switch (field.type) {
            case 'number':
              row[fieldKey] = Math.floor(Math.random() * 100000);
              break;
            case 'date':
              row[fieldKey] = new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
              break;
            case 'boolean':
              row[fieldKey] = Math.random() > 0.5;
              break;
            case 'select':
              row[fieldKey] = field.options[Math.floor(Math.random() * field.options.length)];
              break;
            default:
              row[fieldKey] = `Sample ${field.label} ${i + 1}`;
          }
        }
      });
      rows.push(row);
    }
    return rows;
  };

  // Download report
  const downloadReport = (format) => {
    toast.success(`Downloading report as ${format.toUpperCase()}...`);
    // In production, this would call the backend API to generate the file
  };

  // Render step indicator
  const StepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {[1, 2, 3, 4].map((s, i) => (
        <React.Fragment key={s}>
          <div 
            className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all cursor-pointer
              ${step >= s ? 'bg-orange-500 text-white' : 'bg-zinc-100 text-zinc-400'}`}
            onClick={() => s < step && setStep(s)}
          >
            {s}
          </div>
          {i < 3 && (
            <div className={`w-16 h-1 mx-2 rounded ${step > s ? 'bg-orange-500' : 'bg-zinc-200'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  return (
    <div className="space-y-6" data-testid="custom-report-builder">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Custom Report Builder</h1>
          <p className="text-sm text-zinc-500">Create custom reports with the data you need</p>
        </div>
        <Badge className="bg-orange-100 text-orange-700 px-3 py-1">
          <Sparkles className="w-4 h-4 mr-1" />
          {availableSources.length} Data Sources Available
        </Badge>
      </div>

      {/* Step Indicator */}
      <StepIndicator />

      {/* Step 1: Select Data Source */}
      {step === 1 && (
        <Card className="border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5 text-orange-500" />
              Select Data Source
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {availableSources.map(([key, source]) => {
                const Icon = source.icon;
                return (
                  <div
                    key={key}
                    onClick={() => handleSourceSelect(key)}
                    className={`p-6 rounded-xl border-2 cursor-pointer transition-all hover:shadow-lg
                      ${selectedSource === key 
                        ? 'border-orange-500 bg-orange-50' 
                        : 'border-zinc-200 hover:border-orange-300'}`}
                    data-testid={`source-${key}`}
                  >
                    <div className={`w-12 h-12 rounded-lg ${source.color} flex items-center justify-center mb-3`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-semibold text-zinc-900">{source.name}</h3>
                    <p className="text-sm text-zinc-500 mt-1">{source.fields.length} fields available</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Select Fields */}
      {step === 2 && selectedSource && (
        <Card className="border-zinc-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Columns className="w-5 h-5 text-orange-500" />
                Select Fields to Include
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={selectAllFields}>
                  Select All
                </Button>
                <Button variant="outline" size="sm" onClick={clearAllFields}>
                  Clear All
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {DATA_SOURCES[selectedSource].fields.map((field) => (
                <div
                  key={field.key}
                  onClick={() => toggleField(field.key)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all
                    ${selectedFields.includes(field.key)
                      ? 'border-orange-500 bg-orange-50 text-orange-700'
                      : 'border-zinc-200 hover:border-orange-300'}`}
                  data-testid={`field-${field.key}`}
                >
                  <div className="flex items-center gap-2">
                    <Checkbox 
                      checked={selectedFields.includes(field.key)}
                      className="pointer-events-none"
                    />
                    <span className="font-medium text-sm">{field.label}</span>
                  </div>
                  <span className="text-xs text-zinc-400 ml-6">{field.type}</span>
                </div>
              ))}
            </div>
            
            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button 
                onClick={() => setStep(3)}
                disabled={selectedFields.length === 0}
                className="bg-orange-500 hover:bg-orange-600"
              >
                Next: Add Filters <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Add Filters */}
      {step === 3 && (
        <Card className="border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-orange-500" />
              Add Filters (Optional)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Date Range */}
            <div className="mb-6 p-4 bg-zinc-50 rounded-lg">
              <Label className="font-semibold mb-3 block">Date Range</Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-zinc-500">From</Label>
                  <Input 
                    type="date" 
                    value={dateRange.start}
                    onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">To</Label>
                  <Input 
                    type="date" 
                    value={dateRange.end}
                    onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                  />
                </div>
              </div>
            </div>

            {/* Custom Filters */}
            <div className="space-y-3">
              {filters.map((filter, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
                  <select
                    value={filter.field}
                    onChange={(e) => updateFilter(index, 'field', e.target.value)}
                    className="flex-1 px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="">Select Field</option>
                    {selectedFields.map(fieldKey => {
                      const field = DATA_SOURCES[selectedSource].fields.find(f => f.key === fieldKey);
                      return <option key={fieldKey} value={fieldKey}>{field?.label}</option>;
                    })}
                  </select>
                  <select
                    value={filter.operator}
                    onChange={(e) => updateFilter(index, 'operator', e.target.value)}
                    className="w-32 px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="equals">Equals</option>
                    <option value="contains">Contains</option>
                    <option value="greater_than">Greater Than</option>
                    <option value="less_than">Less Than</option>
                  </select>
                  <Input
                    value={filter.value}
                    onChange={(e) => updateFilter(index, 'value', e.target.value)}
                    placeholder="Value"
                    className="flex-1"
                  />
                  <Button variant="ghost" size="sm" onClick={() => removeFilter(index)}>
                    <X className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              ))}
              
              <Button variant="outline" onClick={addFilter} className="w-full">
                + Add Filter
              </Button>
            </div>

            {/* Report Name */}
            <div className="mt-6">
              <Label className="font-semibold mb-2 block">Report Name</Label>
              <Input
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="e.g., Monthly Sales Report"
              />
            </div>
            
            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button 
                onClick={generatePreview}
                disabled={loading}
                className="bg-orange-500 hover:bg-orange-600"
              >
                {loading ? 'Generating...' : 'Generate Preview'}
                <Eye className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Preview & Download */}
      {step === 4 && previewData && (
        <Card className="border-zinc-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Table className="w-5 h-5 text-orange-500" />
                Report Preview
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => downloadReport('csv')}>
                  <Download className="w-4 h-4 mr-1" /> CSV
                </Button>
                <Button variant="outline" onClick={() => downloadReport('excel')}>
                  <FileSpreadsheet className="w-4 h-4 mr-1" /> Excel
                </Button>
                <Button variant="outline" onClick={() => downloadReport('pdf')}>
                  <FileText className="w-4 h-4 mr-1" /> PDF
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-blue-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-blue-700">{selectedFields.length}</p>
                <p className="text-sm text-blue-600">Fields Selected</p>
              </div>
              <div className="p-4 bg-emerald-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-emerald-700">{previewData.length}</p>
                <p className="text-sm text-emerald-600">Sample Records</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-purple-700">{filters.length}</p>
                <p className="text-sm text-purple-600">Filters Applied</p>
              </div>
            </div>

            {/* Data Table */}
            <div className="border rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-50">
                    <tr>
                      {selectedFields.map(fieldKey => {
                        const field = DATA_SOURCES[selectedSource].fields.find(f => f.key === fieldKey);
                        return (
                          <th key={fieldKey} className="px-4 py-3 text-left font-medium text-zinc-600">
                            {field?.label}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {previewData.map((row, index) => (
                      <tr key={index} className="hover:bg-zinc-50">
                        {selectedFields.map(fieldKey => (
                          <td key={fieldKey} className="px-4 py-3 text-zinc-700">
                            {typeof row[fieldKey] === 'boolean' 
                              ? (row[fieldKey] ? '✓ Yes' : '✗ No')
                              : typeof row[fieldKey] === 'number'
                                ? row[fieldKey].toLocaleString()
                                : row[fieldKey]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <p className="text-xs text-zinc-400 mt-3 text-center">
              Showing 5 sample records. Full report will include all matching data.
            </p>
            
            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={() => setStep(3)}>
                Back to Filters
              </Button>
              <Button 
                onClick={() => {
                  setStep(1);
                  setSelectedSource(null);
                  setSelectedFields([]);
                  setFilters([]);
                  setPreviewData(null);
                  setReportName('');
                  toast.success('Ready to create a new report');
                }}
                className="bg-orange-500 hover:bg-orange-600"
              >
                Create New Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Stats Sidebar */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-orange-500" />
            Your Report Access
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {availableSources.map(([key, source]) => {
              const Icon = source.icon;
              return (
                <div key={key} className="flex items-center gap-2 p-2 bg-zinc-50 rounded-lg">
                  <div className={`w-8 h-8 rounded ${source.color} flex items-center justify-center`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-xs font-medium">{source.name}</p>
                    <p className="text-[10px] text-zinc-400">{source.fields.length} fields</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CustomReportBuilder;
