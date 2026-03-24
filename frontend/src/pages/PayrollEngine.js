import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useTheme } from '../contexts/ThemeContext';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
  Calculator,
  Play,
  FileSpreadsheet,
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  Lock,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Download,
  Eye,
  ArrowRight,
  IndianRupee,
  Calendar,
  Building2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Upload,
  FileText,
  Send,
  Check,
  X,
  Mail,
  FileDown,
  BarChart3,
  AlertCircle,
  UserX,
  Timer
} from 'lucide-react';
import {
  useSimulatePayroll,
  useRunPayroll,
  usePayrollRegister,
  usePayrollRegisterDetails,
  useCalculationBreakdown,
  useSubmitForApproval,
  useApprovePayroll,
  useRejectPayroll
} from '../hooks/usePayrollEngine';

export default function PayrollEngine() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [activeTab, setActiveTab] = useState('test-mode');
  const [registerViewMode, setRegisterViewMode] = useState('detailed'); // 'detailed', 'table', or 'excel'
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  
  // HR Test Mode states
  const [testEmployeeId, setTestEmployeeId] = useState('');
  const [testInputs, setTestInputs] = useState({
    // LOP
    lop_days: 0,
    // Earnings
    bonus: 0,
    incentive: 0,
    overtime_hours: 0,
    arrears: 0,
    arrears_reason: '',
    // Reimbursements
    travel_reimbursement: 0,
    medical_reimbursement: 0,
    food_reimbursement: 0,
    telephone_reimbursement: 0,
    other_reimbursement: 0,
    // Deductions
    penalty: 0,
    penalty_reason: '',
    advance_recovery: 0,
    advance_reason: '',
    loan_emi: 0,
    loan_type: '',
    other_deduction: 0,
    other_deduction_name: ''
  });
  const [simulationResult, setSimulationResult] = useState(null);
  const [showAllInputs, setShowAllInputs] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  
  // Breakdown view
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [breakdownEmployee, setBreakdownEmployee] = useState(null);
  
  // Approval states
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalRemarks, setApprovalRemarks] = useState('');
  
  // Template upload states
  const [uploadPreview, setUploadPreview] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  
  // Email approval states
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [emailRecipient, setEmailRecipient] = useState('dharmesh.parikh@dvconsulting.co.in');
  const [emailMessage, setEmailMessage] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [isDownloadingExcel, setIsDownloadingExcel] = useState(false);
  
  // Mutations
  const simulateMutation = useSimulatePayroll();
  const runPayrollMutation = useRunPayroll();
  const submitMutation = useSubmitForApproval();
  const approveMutation = useApprovePayroll();
  const rejectMutation = useRejectPayroll();
  
  // Queries
  const { data: employees = [] } = useQuery({
    queryKey: ['employees-for-payroll'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000
  });
  
  const { data: registers = [], isLoading: loadingRegisters } = usePayrollRegister();
  const { data: registerDetails, isLoading: loadingDetails } = usePayrollRegisterDetails(selectedMonth);
  const { data: breakdownData } = useCalculationBreakdown(
    breakdownEmployee?.employee_id,
    selectedMonth
  );
  
  // Get current register for the selected month
  const currentRegister = (registers || []).find(r => r.month === selectedMonth);
  
  // Handle simulation
  const handleSimulate = async () => {
    if (!testEmployeeId) {
      toast.error('Please select an employee');
      return;
    }
    
    try {
      const result = await simulateMutation.mutateAsync({
        employee_id: testEmployeeId,
        month: selectedMonth,
        ...testInputs
      });
      
      setSimulationResult(result);
      if (result.success) {
        toast.success('Payroll simulated successfully');
        
        // Use comparison data from simulation result (compares with previous month's actual data)
        if (result.comparison) {
          setComparisonData(result.comparison);
        } else {
          setComparisonData(null);
        }
      } else {
        toast.error(result.error_message || 'Simulation failed');
        setComparisonData(null);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Simulation failed');
      setComparisonData(null);
    }
  };
  
  // Handle run payroll
  const handleRunPayroll = async () => {
    try {
      const result = await runPayrollMutation.mutateAsync({ month: selectedMonth });
      toast.success(`Payroll calculated for ${result.total_employees} employees`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to run payroll');
    }
  };
  
  // Handle submit for approval
  const handleSubmit = async () => {
    try {
      await submitMutation.mutateAsync({ month: selectedMonth, remarks: approvalRemarks });
      toast.success('Payroll submitted for admin approval');
      setShowApprovalDialog(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit');
    }
  };
  
  // Handle approve
  const handleApprove = async () => {
    try {
      await approveMutation.mutateAsync({ month: selectedMonth, remarks: approvalRemarks });
      toast.success('Payroll approved and locked');
      setShowApprovalDialog(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve');
    }
  };
  
  // Handle reject
  const handleReject = async () => {
    if (!approvalRemarks.trim()) {
      toast.error('Please provide rejection reason');
      return;
    }
    try {
      await rejectMutation.mutateAsync({ month: selectedMonth, reason: approvalRemarks });
      toast.success('Payroll rejected and sent back for corrections');
      setShowApprovalDialog(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject');
    }
  };
  
  // Export to Excel
  const handleExport = async () => {
    try {
      const res = await axios.get(`${API}/payroll/engine/export/${selectedMonth}`);
      const { data, columns } = res.data;
      
      // Convert to CSV
      const csvContent = [
        columns.join(','),
        ...(data || []).map(row => (columns || []).map(col => `"${row[col] || ''}"`).join(','))
      ].join('\n');
      
      // Download
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `payroll_${selectedMonth}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('Payroll exported successfully');
    } catch (err) {
      toast.error('Failed to export payroll');
    }
  };
  
  // Download Excel file directly
  const handleDownloadExcel = async () => {
    setIsDownloadingExcel(true);
    try {
      const response = await axios.get(`${API}/payroll/engine/export-excel?month=${selectedMonth}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Payroll_Register_${selectedMonth}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('Excel downloaded successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to download Excel');
    } finally {
      setIsDownloadingExcel(false);
    }
  };
  
  // Send payroll for email approval
  const handleSendForEmailApproval = async () => {
    if (!emailRecipient.trim()) {
      toast.error('Please enter recipient email');
      return;
    }
    
    setIsSendingEmail(true);
    try {
      const res = await axios.post(`${API}/payroll/engine/send-for-approval`, {
        month: selectedMonth,
        recipient_email: emailRecipient,
        cc_emails: [],
        message: emailMessage || `Please review and approve the payroll for ${selectedMonth}`
      });
      
      toast.success(res.data.message || 'Payroll sent for approval');
      setShowEmailDialog(false);
      setEmailMessage('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send email');
    } finally {
      setIsSendingEmail(false);
    }
  };
  
  // Status badge
  const getStatusBadge = (status) => {
    const styles = {
      draft: { color: 'bg-yellow-500/20 text-yellow-600', icon: Clock, label: 'Draft' },
      pending_admin_approval: { color: 'bg-blue-500/20 text-blue-600', icon: Send, label: 'Pending Approval' },
      locked: { color: 'bg-green-500/20 text-green-600', icon: Lock, label: 'Locked' },
      cancelled: { color: 'bg-red-500/20 text-red-600', icon: XCircle, label: 'Cancelled' }
    };
    const s = styles[status] || styles.draft;
    return (
      <Badge className={`${s.color} gap-1`}>
        <s.icon className="w-3 h-3" />
        {s.label}
      </Badge>
    );
  };
  
  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };
  
  return (
    <div className={`p-6 min-h-screen ${isDark ? 'bg-zinc-950' : 'bg-gray-50'}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Payroll Engine
          </h1>
          <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
            Field-level traceable payroll calculations with approval workflow
          </p>
        </div>
        
        {/* Month Selector */}
        <div className="flex items-center gap-3">
          <Label className={isDark ? 'text-zinc-300' : ''}>Month</Label>
          <Input
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className={`w-40 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
          />
        </div>
      </div>
      
      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className={`mb-6 ${isDark ? 'bg-zinc-900' : ''}`}>
          <TabsTrigger value="test-mode" data-testid="tab-test-mode">
            <Calculator className="w-4 h-4 mr-2" />
            HR Test Mode
          </TabsTrigger>
          <TabsTrigger value="template" data-testid="tab-template">
            <Upload className="w-4 h-4 mr-2" />
            Template Upload
          </TabsTrigger>
          <TabsTrigger value="run-payroll" data-testid="tab-run-payroll">
            <Play className="w-4 h-4 mr-2" />
            Run Payroll
          </TabsTrigger>
          <TabsTrigger value="register" data-testid="tab-register">
            <FileSpreadsheet className="w-4 h-4 mr-2" />
            Payroll Register
          </TabsTrigger>
          <TabsTrigger value="approval" data-testid="tab-approval">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Approval
          </TabsTrigger>
          <TabsTrigger value="penalty-dashboard" data-testid="tab-penalty-dashboard">
            <BarChart3 className="w-4 h-4 mr-2" />
            Penalty Dashboard
          </TabsTrigger>
          <TabsTrigger value="pro-rata" data-testid="tab-pro-rata">
            <Users className="w-4 h-4 mr-2" />
            Pro-rata
          </TabsTrigger>
        </TabsList>
        
        {/* ==================== HR TEST MODE ==================== */}
        <TabsContent value="test-mode">
          <div className="grid grid-cols-2 gap-6">
            {/* Input Section */}
            <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-amber-500" />
                  Simulate Payroll
                </CardTitle>
                <CardDescription>
                  Test payroll calculation with custom inputs. Changes are NOT saved.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Employee Selection */}
                <div>
                  <Label>Select Employee</Label>
                  <Select value={testEmployeeId} onValueChange={setTestEmployeeId}>
                    <SelectTrigger className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
                      <SelectValue placeholder="Choose employee..." />
                    </SelectTrigger>
                    <SelectContent>
                      {(employees || []).map(emp => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.department})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Basic Input Grid */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs">LOP Days</Label>
                    <Input
                      type="number"
                      value={testInputs.lop_days}
                      onChange={(e) => setTestInputs({...testInputs, lop_days: parseFloat(e.target.value) || 0})}
                      className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                      min={0}
                      step={0.5}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Bonus (₹)</Label>
                    <Input
                      type="number"
                      value={testInputs.bonus}
                      onChange={(e) => setTestInputs({...testInputs, bonus: parseFloat(e.target.value) || 0})}
                      className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                      min={0}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Incentive (₹)</Label>
                    <Input
                      type="number"
                      value={testInputs.incentive}
                      onChange={(e) => setTestInputs({...testInputs, incentive: parseFloat(e.target.value) || 0})}
                      className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                      min={0}
                    />
                  </div>
                </div>
                
                {/* Toggle for Advanced Inputs */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAllInputs(!showAllInputs)}
                  className="w-full justify-between text-xs"
                >
                  <span>{showAllInputs ? 'Hide' : 'Show'} All Input Fields</span>
                  {showAllInputs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </Button>
                
                {showAllInputs && (
                  <div className="space-y-4">
                    {/* Earnings Section */}
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-green-900/20 border border-green-800' : 'bg-green-50 border border-green-200'}`}>
                      <p className="text-xs font-medium text-green-600 mb-2">Additional Earnings</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-xs">Overtime Hours</Label>
                          <Input
                            type="number"
                            value={testInputs.overtime_hours}
                            onChange={(e) => setTestInputs({...testInputs, overtime_hours: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Arrears (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.arrears}
                            onChange={(e) => setTestInputs({...testInputs, arrears: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                      </div>
                      {testInputs.arrears > 0 && (
                        <div className="mt-2">
                          <Label className="text-xs">Arrears Reason</Label>
                          <Input
                            value={testInputs.arrears_reason}
                            onChange={(e) => setTestInputs({...testInputs, arrears_reason: e.target.value})}
                            placeholder="e.g., Salary revision"
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                          />
                        </div>
                      )}
                    </div>
                    
                    {/* Reimbursements Section */}
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                      <p className="text-xs font-medium text-blue-600 mb-2">Reimbursements (Non-taxable)</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-xs">Travel (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.travel_reimbursement}
                            onChange={(e) => setTestInputs({...testInputs, travel_reimbursement: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Medical (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.medical_reimbursement}
                            onChange={(e) => setTestInputs({...testInputs, medical_reimbursement: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Food/Meal (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.food_reimbursement}
                            onChange={(e) => setTestInputs({...testInputs, food_reimbursement: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Telephone (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.telephone_reimbursement}
                            onChange={(e) => setTestInputs({...testInputs, telephone_reimbursement: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div className="col-span-2">
                          <Label className="text-xs">Other Reimbursement (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.other_reimbursement}
                            onChange={(e) => setTestInputs({...testInputs, other_reimbursement: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                      </div>
                    </div>
                    
                    {/* Deductions Section */}
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
                      <p className="text-xs font-medium text-red-600 mb-2">Deductions</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-xs">Penalty (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.penalty}
                            onChange={(e) => setTestInputs({...testInputs, penalty: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Advance Recovery (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.advance_recovery}
                            onChange={(e) => setTestInputs({...testInputs, advance_recovery: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Loan EMI (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.loan_emi}
                            onChange={(e) => setTestInputs({...testInputs, loan_emi: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Loan Type</Label>
                          <Select
                            value={testInputs.loan_type}
                            onValueChange={(v) => setTestInputs({...testInputs, loan_type: v})}
                          >
                            <SelectTrigger className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}>
                              <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="personal">Personal Loan</SelectItem>
                              <SelectItem value="home">Home Loan</SelectItem>
                              <SelectItem value="vehicle">Vehicle Loan</SelectItem>
                              <SelectItem value="education">Education Loan</SelectItem>
                              <SelectItem value="other">Other</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Other Deduction (₹)</Label>
                          <Input
                            type="number"
                            value={testInputs.other_deduction}
                            onChange={(e) => setTestInputs({...testInputs, other_deduction: parseFloat(e.target.value) || 0})}
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                            min={0}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Deduction Name</Label>
                          <Input
                            value={testInputs.other_deduction_name}
                            onChange={(e) => setTestInputs({...testInputs, other_deduction_name: e.target.value})}
                            placeholder="e.g., Canteen"
                            className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                          />
                        </div>
                      </div>
                      {(testInputs.penalty > 0 || testInputs.advance_recovery > 0) && (
                        <div className="grid grid-cols-2 gap-3 mt-2">
                          {testInputs.penalty > 0 && (
                            <div>
                              <Label className="text-xs">Penalty Reason</Label>
                              <Input
                                value={testInputs.penalty_reason}
                                onChange={(e) => setTestInputs({...testInputs, penalty_reason: e.target.value})}
                                placeholder="e.g., Policy violation"
                                className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                              />
                            </div>
                          )}
                          {testInputs.advance_recovery > 0 && (
                            <div>
                              <Label className="text-xs">Advance Reason</Label>
                              <Input
                                value={testInputs.advance_reason}
                                onChange={(e) => setTestInputs({...testInputs, advance_reason: e.target.value})}
                                placeholder="e.g., Salary advance Feb"
                                className={`mt-1 h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <Button 
                  onClick={handleSimulate}
                  disabled={simulateMutation.isPending}
                  className="w-full bg-amber-600 hover:bg-amber-700"
                  data-testid="btn-simulate"
                >
                  {simulateMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Calculator className="w-4 h-4 mr-2" />
                  )}
                  Calculate Payroll
                </Button>
              </CardContent>
            </Card>
            
            {/* Result Section */}
            <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-green-500" />
                  Simulation Result
                </CardTitle>
              </CardHeader>
              <CardContent className="max-h-[75vh] overflow-y-auto">
                {simulationResult ? (
                  simulationResult.success ? (
                    <div className="space-y-4">
                      {/* Employee Info */}
                      <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                        <p className="font-medium">{simulationResult.employee_name}</p>
                        <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                          {simulationResult.employee_code} • {simulationResult.department}
                        </p>
                        <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                          Month: {simulationResult.month} ({simulationResult.days_in_month} days)
                        </p>
                      </div>
                      
                      {/* Summary Cards */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-green-900/30 border border-green-800' : 'bg-green-50 border border-green-200'}`}>
                          <p className={`text-xs ${isDark ? 'text-green-400' : 'text-green-600'}`}>Gross</p>
                          <p className="font-bold text-green-600">{formatCurrency(simulationResult.gross_monthly)}</p>
                        </div>
                        <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-red-900/30 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
                          <p className={`text-xs ${isDark ? 'text-red-400' : 'text-red-600'}`}>Deductions</p>
                          <p className="font-bold text-red-600">{formatCurrency(simulationResult.total_deductions)}</p>
                        </div>
                        <div className={`p-3 rounded-lg text-center ${isDark ? 'bg-blue-900/30 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                          <p className={`text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>Net Payable</p>
                          <p className="font-bold text-blue-600">{formatCurrency(simulationResult.net_payable)}</p>
                        </div>
                      </div>
                      
                      {/* Earnings */}
                      <div>
                        <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : ''}`}>Earnings</p>
                        <div className="space-y-1">
                          {(simulationResult?.earnings || []).map((e, i) => (
                            <div key={i} className={`flex justify-between text-sm p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
                              <span>{e.name}</span>
                              <span className="font-medium text-green-600">+{formatCurrency(e.amount)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* Deductions */}
                      <div>
                        <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : ''}`}>Deductions</p>
                        <div className="space-y-1">
                          {(simulationResult?.deductions || []).map((d, i) => (
                            <div key={i} className={`text-sm p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
                              <div className="flex justify-between">
                                <span>{d.name}</span>
                                <span className="font-medium text-red-600">-{formatCurrency(d.amount)}</span>
                              </div>
                              <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                                {d.calculation?.formula_used}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {/* LOP Highlight */}
                      {simulationResult.lop_days > 0 && (
                        <div className={`p-3 rounded-lg border-l-4 border-amber-500 ${isDark ? 'bg-amber-900/20' : 'bg-amber-50'}`}>
                          <p className={`text-xs ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>LOP Calculation</p>
                          <p className={`text-sm ${isDark ? 'text-zinc-300' : ''}`}>
                            {simulationResult.lop_days} days × ₹{(simulationResult.gross_monthly / simulationResult.days_in_month).toFixed(2)}/day
                          </p>
                        </div>
                      )}
                      
                      {/* Attendance Summary */}
                      {simulationResult.attendance_summary && (
                        <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                          <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                            Attendance Summary - {simulationResult.month}
                          </p>
                          <div className="grid grid-cols-4 gap-2 text-xs">
                            <div className={`p-2 rounded text-center ${isDark ? 'bg-zinc-700' : 'bg-white'}`}>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Days</p>
                              <p className="font-bold">{simulationResult.attendance_summary.days_in_month}</p>
                            </div>
                            <div className={`p-2 rounded text-center ${isDark ? 'bg-green-900/30' : 'bg-green-50'}`}>
                              <p className="text-green-600">Present</p>
                              <p className="font-bold text-green-600">{simulationResult.attendance_summary.present_days}</p>
                            </div>
                            <div className={`p-2 rounded text-center ${isDark ? 'bg-blue-900/30' : 'bg-blue-50'}`}>
                              <p className="text-blue-600">Leaves</p>
                              <p className="font-bold text-blue-600">{simulationResult.attendance_summary.total_leave_days}</p>
                            </div>
                            <div className={`p-2 rounded text-center ${isDark ? 'bg-amber-900/30' : 'bg-amber-50'}`}>
                              <p className="text-amber-600">Holidays</p>
                              <p className="font-bold text-amber-600">{simulationResult.attendance_summary.holidays}</p>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* TDS Details */}
                      {simulationResult.tds_details && simulationResult.tds_details.monthly_tds > 0 && (
                        <div className={`p-3 rounded-lg border-l-4 border-purple-500 ${isDark ? 'bg-purple-900/20' : 'bg-purple-50'}`}>
                          <p className={`text-xs font-medium ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
                            TDS (Income Tax) - {simulationResult.tds_details.regime?.toUpperCase()} Regime (FY 2025-26)
                          </p>
                          <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Annual CTC</p>
                              <p className="font-medium">{formatCurrency(simulationResult.gross_annual)}</p>
                            </div>
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Taxable Income</p>
                              <p className="font-medium">{formatCurrency(simulationResult.tds_details.taxable_income)}</p>
                            </div>
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Annual Tax</p>
                              <p className="font-medium text-purple-600">{formatCurrency(simulationResult.tds_details.annual_tax)}</p>
                            </div>
                          </div>
                          {simulationResult.tds_details.slab_breakdown?.length > 0 && (
                            <p className={`text-xs mt-2 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                              {simulationResult.tds_details.slab_breakdown.join(' | ')}
                            </p>
                          )}
                        </div>
                      )}
                      
                      {/* Show 87A Rebate Info when applied (zero TDS) - Finance Act 2025 */}
                      {simulationResult.tds_details && simulationResult.tds_details.monthly_tds === 0 && simulationResult.tds_details.rebate_87a > 0 && (
                        <div className={`p-3 rounded-lg border-l-4 border-green-500 ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}>
                          <p className={`text-xs font-medium flex items-center gap-2 ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                            <CheckCircle2 className="w-4 h-4" />
                            Section 87A Rebate Applied - Zero TDS (Finance Act 2025)
                          </p>
                          <div className="grid grid-cols-3 gap-2 mt-2 text-xs">
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Taxable Income</p>
                              <p className="font-medium">{formatCurrency(simulationResult.tds_details.taxable_income)}</p>
                            </div>
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Tax Before Rebate</p>
                              <p className="font-medium">{formatCurrency(simulationResult.tds_details.tax_before_rebate)}</p>
                            </div>
                            <div>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>87A Rebate</p>
                              <p className="font-medium text-green-600">-{formatCurrency(simulationResult.tds_details.rebate_87a)}</p>
                            </div>
                          </div>
                          <p className={`text-xs mt-2 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                            Taxable income ≤ ₹12,00,000 qualifies for full rebate (up to ₹60,000) under Section 87A • Zero tax up to ₹12.75L gross
                          </p>
                        </div>
                      )}
                      
                      {/* Month-over-Month Comparison - Simulation vs Previous Actual */}
                      {comparisonData && comparisonData.has_previous ? (
                        <div className={`p-3 rounded-lg border-l-4 border-cyan-500 ${isDark ? 'bg-cyan-900/20' : 'bg-cyan-50'}`}>
                          <div className="flex items-center justify-between mb-2">
                            <p className={`text-xs font-medium ${isDark ? 'text-cyan-400' : 'text-cyan-600'}`}>
                              vs Previous Month (Actual Payroll)
                            </p>
                            <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                              Comparing with {comparisonData.previous_month}
                            </span>
                          </div>
                          
                          {comparisonData.changes?.length > 0 ? (
                            <div className="space-y-2">
                              {(comparisonData?.changes || []).slice(0, 5).map((change, idx) => {
                                const isIncrease = change.difference > 0;
                                const isDeduction = change.field.toLowerCase().includes('deduction');
                                const color = isDeduction 
                                  ? (isIncrease ? 'text-red-500' : 'text-green-500')
                                  : (isIncrease ? 'text-green-500' : 'text-red-500');
                                
                                return (
                                  <div key={idx} className={`flex items-center justify-between text-sm ${isDark ? 'bg-zinc-800/50' : 'bg-white/50'} p-2 rounded`}>
                                    <span className={isDark ? 'text-zinc-300' : 'text-gray-700'}>{change.field}</span>
                                    <div className="flex items-center gap-2">
                                      <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                                        {formatCurrency(change.previous)}
                                      </span>
                                      <ArrowRight className="w-3 h-3" />
                                      <span className="font-medium">
                                        {formatCurrency(change.current)}
                                      </span>
                                      <span className={`text-xs font-medium ${color} flex items-center`}>
                                        {isIncrease ? <TrendingUp className="w-3 h-3 mr-0.5" /> : <TrendingDown className="w-3 h-3 mr-0.5" />}
                                        {change.percentage_change > 0 ? '+' : ''}{change.percentage_change}%
                                      </span>
                                    </div>
                                  </div>
                                );
                              })}
                              
                              {comparisonData.changes.length === 0 && (
                                <p className={`text-sm flex items-center gap-2 ${isDark ? 'text-cyan-300' : 'text-cyan-700'}`}>
                                  <CheckCircle2 className="w-4 h-4" />
                                  No significant changes from last month's payroll
                                </p>
                              )}
                            </div>
                          ) : (
                            <p className={`text-sm flex items-center gap-2 ${isDark ? 'text-cyan-300' : 'text-cyan-700'}`}>
                              <CheckCircle2 className="w-4 h-4" />
                              Matches previous month's payroll
                            </p>
                          )}
                        </div>
                      ) : comparisonData && !comparisonData.has_previous ? (
                        <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                          <p className={`text-xs flex items-center gap-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                            <Calendar className="w-4 h-4" />
                            {comparisonData.message || `No saved payroll for ${comparisonData.previous_month} to compare`}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <div className={`p-4 rounded-lg ${isDark ? 'bg-red-900/30 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
                      <div className="flex items-center gap-2 text-red-600">
                        <XCircle className="w-5 h-5" />
                        <p className="font-medium">Simulation Failed</p>
                      </div>
                      <p className={`mt-2 text-sm ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                        {simulationResult.error_message}
                      </p>
                    </div>
                  )
                ) : (
                  <div className={`text-center py-12 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                    <Calculator className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Select an employee and click "Calculate Payroll" to simulate</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        {/* ==================== TEMPLATE UPLOAD ==================== */}
        <TabsContent value="template">
          <div className="grid grid-cols-2 gap-6">
            {/* Download Template */}
            <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="w-5 h-5 text-blue-500" />
                  Download Template
                </CardTitle>
                <CardDescription>
                  Download payroll input template with employee data pre-filled
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                  <p className={`text-sm mb-3 ${isDark ? 'text-zinc-300' : ''}`}>
                    Template includes:
                  </p>
                  <ul className={`text-xs space-y-1 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                    <li>• Employee ID, Name, Department (read-only)</li>
                    <li>• Gross Monthly Salary (read-only)</li>
                    <li>• Attendance summary: Days, Present, Leaves, Holidays</li>
                    <li>• LOP Days, Bonus, Incentive, Overtime Hours (editable)</li>
                    <li>• Penalty, Advance Recovery, Reimbursements (editable)</li>
                  </ul>
                </div>
                
                <Button
                  onClick={async () => {
                    try {
                      const res = await axios.get(`${API}/payroll/engine/template/download?month=${selectedMonth}`);
                      const { template, columns } = res.data;
                      
                      // Convert to CSV
                      const csvContent = [
                        columns.join(','),
                        ...(template || []).map(row => (columns || []).map(col => {
                          const val = row[col];
                          return typeof val === 'string' && val.includes(',') ? `"${val}"` : val;
                        }).join(','))
                      ].join('\n');
                      
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `payroll_template_${selectedMonth}.csv`;
                      a.click();
                      window.URL.revokeObjectURL(url);
                      
                      toast.success('Template downloaded successfully');
                    } catch (err) {
                      toast.error('Failed to download template');
                    }
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  data-testid="btn-download-template"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download Template for {selectedMonth}
                </Button>
              </CardContent>
            </Card>
            
            {/* Upload Template */}
            <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5 text-green-500" />
                  Upload & Preview
                </CardTitle>
                <CardDescription>
                  Upload edited template and preview changes before applying
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className={`p-4 rounded-lg border-2 border-dashed ${isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-gray-300 bg-gray-50'}`}>
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      
                      setIsUploading(true);
                      const formData = new FormData();
                      formData.append('file', file);
                      
                      try {
                        const res = await axios.post(
                          `${API}/payroll/engine/template/upload-preview?month=${selectedMonth}`,
                          formData,
                          { headers: { 'Content-Type': 'multipart/form-data' } }
                        );
                        setUploadPreview(res.data);
                        toast.success(`Processed ${res.data.total_rows} rows`);
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Upload failed');
                      } finally {
                        setIsUploading(false);
                      }
                    }}
                    className="hidden"
                    id="template-upload"
                  />
                  <label
                    htmlFor="template-upload"
                    className={`flex flex-col items-center justify-center py-6 cursor-pointer ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}
                  >
                    {isUploading ? (
                      <Loader2 className="w-8 h-8 animate-spin mb-2" />
                    ) : (
                      <Upload className="w-8 h-8 mb-2" />
                    )}
                    <span className="text-sm">Click to upload CSV/Excel file</span>
                    <span className="text-xs mt-1">or drag and drop</span>
                  </label>
                </div>
                
                {/* Preview Results */}
                {uploadPreview && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div className={`p-2 rounded text-center ${isDark ? 'bg-green-900/30' : 'bg-green-50'}`}>
                        <p className="text-green-600 font-bold">{uploadPreview.changed_count}</p>
                        <p className={`text-xs ${isDark ? 'text-green-400' : 'text-green-600'}`}>Changed</p>
                      </div>
                      <div className={`p-2 rounded text-center ${isDark ? 'bg-zinc-700' : 'bg-gray-100'}`}>
                        <p className="font-bold">{uploadPreview.unchanged_count}</p>
                        <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>Unchanged</p>
                      </div>
                      <div className={`p-2 rounded text-center ${isDark ? 'bg-red-900/30' : 'bg-red-50'}`}>
                        <p className="text-red-600 font-bold">{uploadPreview.error_count}</p>
                        <p className={`text-xs ${isDark ? 'text-red-400' : 'text-red-600'}`}>Errors</p>
                      </div>
                    </div>
                    
                    {/* Changes List */}
                    <div className={`max-h-48 overflow-y-auto rounded-lg border ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                      {uploadPreview.preview?.filter(p => p.status === 'changed').map((item, i) => (
                        <div key={i} className={`p-2 border-b text-sm ${isDark ? 'border-zinc-700' : 'border-gray-100'}`}>
                          <p className="font-medium">{item.employee_id} - {item.employee_name}</p>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {item.changes?.map((c, j) => (
                              <span key={j} className={`text-xs px-2 py-0.5 rounded ${isDark ? 'bg-amber-900/30 text-amber-400' : 'bg-amber-100 text-amber-700'}`}>
                                {c.field}: {c.old_value} → {c.new_value}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <Button
                      onClick={async () => {
                        setIsApplying(true);
                        try {
                          const res = await axios.post(`${API}/payroll/engine/template/apply`, {
                            month: selectedMonth,
                            preview: uploadPreview.preview
                          });
                          toast.success(res.data.message);
                          setUploadPreview(null);
                        } catch (err) {
                          toast.error(err.response?.data?.detail || 'Failed to apply');
                        } finally {
                          setIsApplying(false);
                        }
                      }}
                      disabled={isApplying || uploadPreview.changed_count === 0}
                      className="w-full bg-green-600 hover:bg-green-700"
                    >
                      {isApplying ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4 mr-2" />
                      )}
                      Apply {uploadPreview.changed_count} Changes
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        {/* ==================== RUN PAYROLL ==================== */}
        <TabsContent value="run-payroll">
          <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="w-5 h-5 text-green-500" />
                Run Payroll for {selectedMonth}
              </CardTitle>
              <CardDescription>
                Calculate payroll for all active employees. Creates a draft register.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {currentRegister ? (
                <div className="space-y-4">
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <p className="font-medium">Payroll Register for {selectedMonth}</p>
                      {getStatusBadge(currentRegister.status)}
                    </div>
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Employees</p>
                        <p className="font-bold text-lg">{currentRegister.total_employees}</p>
                      </div>
                      <div>
                        <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Total Gross</p>
                        <p className="font-bold text-lg text-green-600">{formatCurrency(currentRegister.total_gross_salary)}</p>
                      </div>
                      <div>
                        <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Total Deductions</p>
                        <p className="font-bold text-lg text-red-600">{formatCurrency(currentRegister.total_deductions)}</p>
                      </div>
                      <div>
                        <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Net Payable</p>
                        <p className="font-bold text-lg text-blue-600">{formatCurrency(currentRegister.total_net_payable)}</p>
                      </div>
                    </div>
                    
                    {/* Department Summary */}
                    {currentRegister.department_summary && Object.keys(currentRegister.department_summary || {}).length > 0 && (
                      <div className="mt-4">
                        <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : ''}`}>By Department</p>
                        <div className="grid grid-cols-3 gap-2">
                          {Object.entries(currentRegister.department_summary || {}).map(([dept, data]) => (
                            <div key={dept} className={`p-2 rounded text-sm ${isDark ? 'bg-zinc-700' : 'bg-gray-50'}`}>
                              <p className="font-medium">{dept}</p>
                              <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>
                                {data.count} employees • {formatCurrency(data.net)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Errors */}
                    {currentRegister.total_errors > 0 && (
                      <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-red-900/30 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
                        <p className="text-red-600 font-medium flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4" />
                          {currentRegister.total_errors} errors found
                        </p>
                        <div className="mt-2 space-y-1">
                          {(currentRegister.errors || []).slice(0, 5).map((err, i) => (
                            <p key={i} className={`text-sm ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                              • {err.employee_name || err.employee_id}: {err.error}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {currentRegister.status === 'draft' && (
                    <div className="flex gap-3">
                      <Button 
                        onClick={handleRunPayroll}
                        disabled={runPayrollMutation.isPending}
                        variant="outline"
                      >
                        {runPayrollMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4 mr-2" />
                        )}
                        Re-run Payroll
                      </Button>
                      <Button 
                        onClick={() => setShowApprovalDialog(true)}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Submit for Approval
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Play className={`w-12 h-12 mx-auto mb-3 ${isDark ? 'text-zinc-600' : 'text-gray-400'}`} />
                  <p className={`mb-4 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                    No payroll register found for {selectedMonth}
                  </p>
                  <Button 
                    onClick={handleRunPayroll}
                    disabled={runPayrollMutation.isPending}
                    className="bg-green-600 hover:bg-green-700"
                    data-testid="btn-run-payroll"
                  >
                    {runPayrollMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    Run Payroll
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* ==================== PAYROLL REGISTER ==================== */}
        <TabsContent value="register">
          <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileSpreadsheet className="w-5 h-5 text-blue-500" />
                    Payroll Register - {selectedMonth}
                  </CardTitle>
                  <CardDescription>
                    Detailed employee-wise payroll breakdown with full traceability
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {/* View Mode Toggle - 3 options */}
                  <div className={`flex rounded-lg p-1 ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                    <button
                      onClick={() => setRegisterViewMode('table')}
                      className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                        registerViewMode === 'table' 
                          ? (isDark ? 'bg-zinc-700 text-white' : 'bg-white text-gray-900 shadow') 
                          : (isDark ? 'text-zinc-400' : 'text-gray-500')
                      }`}
                    >
                      Summary
                    </button>
                    <button
                      onClick={() => setRegisterViewMode('detailed')}
                      className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                        registerViewMode === 'detailed' 
                          ? (isDark ? 'bg-zinc-700 text-white' : 'bg-white text-gray-900 shadow') 
                          : (isDark ? 'text-zinc-400' : 'text-gray-500')
                      }`}
                    >
                      Cards
                    </button>
                    <button
                      onClick={() => setRegisterViewMode('excel')}
                      className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                        registerViewMode === 'excel' 
                          ? (isDark ? 'bg-zinc-700 text-white' : 'bg-white text-gray-900 shadow') 
                          : (isDark ? 'text-zinc-400' : 'text-gray-500')
                      }`}
                    >
                      Full Excel View
                    </button>
                  </div>
                  <Button variant="outline" onClick={handleExport} data-testid="btn-export">
                    <Download className="w-4 h-4 mr-2" />
                    Export CSV
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={handleDownloadExcel}
                    disabled={isDownloadingExcel}
                    data-testid="btn-download-excel"
                  >
                    {isDownloadingExcel ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <FileDown className="w-4 h-4 mr-2" />
                    )}
                    Download Excel
                  </Button>
                  <Button 
                    onClick={() => setShowEmailDialog(true)}
                    className="bg-blue-600 hover:bg-blue-700"
                    data-testid="btn-email-approval"
                  >
                    <Mail className="w-4 h-4 mr-2" />
                    Email for Approval
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loadingDetails ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 mx-auto animate-spin text-blue-500" />
                  <p className={`mt-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>Loading detailed register...</p>
                </div>
              ) : registerDetails?.calculations?.length > 0 ? (
                <div className="space-y-4">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-6 gap-3 mb-6">
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                      <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>Total Employees</p>
                      <p className="text-xl font-bold">{registerDetails.calculations.length}</p>
                    </div>
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-green-900/30' : 'bg-green-50'}`}>
                      <p className={`text-xs ${isDark ? 'text-green-400' : 'text-green-600'}`}>Total Gross</p>
                      <p className="text-xl font-bold text-green-600">
                        {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.gross_monthly || 0), 0))}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-red-900/30' : 'bg-red-50'}`}>
                      <p className={`text-xs ${isDark ? 'text-red-400' : 'text-red-600'}`}>Total Deductions</p>
                      <p className="text-xl font-bold text-red-600">
                        {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.total_deductions || 0), 0))}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-blue-900/30' : 'bg-blue-50'}`}>
                      <p className={`text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>Net Payable</p>
                      <p className="text-xl font-bold text-blue-600">
                        {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.net_payable || 0), 0))}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-purple-900/30' : 'bg-purple-50'}`}>
                      <p className={`text-xs ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>TDS Liability</p>
                      <p className="text-xl font-bold text-purple-600">
                        {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.tds_details?.monthly_tds || 0), 0))}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-amber-900/30' : 'bg-amber-50'}`}>
                      <p className={`text-xs ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>Total Expenses</p>
                      <p className="text-xl font-bold text-amber-600">
                        {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.reimbursements || 0), 0))}
                      </p>
                    </div>
                  </div>

                  {/* TABLE VIEW */}
                  {registerViewMode === 'table' && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className={`${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                            <th className="text-left p-2 font-semibold">Employee</th>
                            <th className="text-left p-2 font-semibold">Dept</th>
                            <th className="text-right p-2 font-semibold">Basic</th>
                            <th className="text-right p-2 font-semibold">HRA</th>
                            <th className="text-right p-2 font-semibold">Allowances</th>
                            <th className="text-right p-2 font-semibold">Gross</th>
                            <th className="text-right p-2 font-semibold">LOP</th>
                            <th className="text-right p-2 font-semibold">PF</th>
                            <th className="text-right p-2 font-semibold">PT</th>
                            <th className="text-right p-2 font-semibold">TDS</th>
                            <th className="text-right p-2 font-semibold">Expenses</th>
                            <th className="text-right p-2 font-semibold">Total Ded.</th>
                            <th className="text-right p-2 font-semibold">Net Pay</th>
                            <th className="text-center p-2 font-semibold">Attend.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(registerDetails?.calculations || []).map((calc, i) => {
                            const basic = calc.earnings?.find(e => e.key === 'basic_salary')?.amount || 0;
                            const hra = calc.earnings?.find(e => e.key === 'hra')?.amount || 0;
                            const special = calc.earnings?.find(e => e.key === 'special_allowance')?.amount || 0;
                            const lopDed = calc.deductions?.find(d => d.key === 'lop')?.amount || 0;
                            const pfDed = calc.deductions?.find(d => d.key === 'pf')?.amount || 0;
                            const ptDed = calc.deductions?.find(d => d.key === 'pt')?.amount || 0;
                            const tdsDed = calc.tds_details?.monthly_tds || 0;
                            const expenses = calc.reimbursements || 0;
                            const attendance = calc.attendance_summary || {};
                            
                            return (
                              <tr 
                                key={i} 
                                className={`border-t ${isDark ? 'border-zinc-800 hover:bg-zinc-800/50' : 'border-gray-100 hover:bg-gray-50'}`}
                              >
                                <td className="p-2">
                                  <p className="font-medium">{calc.employee_name}</p>
                                  <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>{calc.employee_code}</p>
                                </td>
                                <td className="p-2">{calc.department}</td>
                                <td className="p-2 text-right">{formatCurrency(basic)}</td>
                                <td className="p-2 text-right">{formatCurrency(hra)}</td>
                                <td className="p-2 text-right">{formatCurrency(special)}</td>
                                <td className="p-2 text-right font-medium text-green-600">{formatCurrency(calc.gross_monthly)}</td>
                                <td className="p-2 text-right text-red-600">{lopDed > 0 ? `-${formatCurrency(lopDed)}` : '-'}</td>
                                <td className="p-2 text-right text-red-600">{pfDed > 0 ? `-${formatCurrency(pfDed)}` : '-'}</td>
                                <td className="p-2 text-right text-red-600">{ptDed > 0 ? `-${formatCurrency(ptDed)}` : '-'}</td>
                                <td className="p-2 text-right text-red-600">{tdsDed > 0 ? `-${formatCurrency(tdsDed)}` : '-'}</td>
                                <td className="p-2 text-right text-amber-600">{expenses > 0 ? `+${formatCurrency(expenses)}` : '-'}</td>
                                <td className="p-2 text-right font-medium text-red-600">-{formatCurrency(calc.total_deductions)}</td>
                                <td className="p-2 text-right font-bold text-blue-600">{formatCurrency(calc.net_payable)}</td>
                                <td className="p-2 text-center">
                                  <span className={`text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                                    {attendance.present || '-'}/{attendance.working_days || '-'}
                                  </span>
                                  {(attendance.lop_days || calc.lop_days) > 0 && (
                                    <span className="text-red-500 ml-1">({attendance.lop_days || calc.lop_days} LOP)</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot>
                          <tr className={`font-bold border-t-2 ${isDark ? 'border-zinc-600 bg-zinc-800' : 'border-gray-300 bg-gray-100'}`}>
                            <td className="p-2" colSpan={5}>Total ({registerDetails.calculations.length} employees)</td>
                            <td className="p-2 text-right text-green-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.gross_monthly || 0), 0))}
                            </td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => {
                                const lop = c.deductions?.find(d => d.key === 'lop')?.amount || 0;
                                return s + lop;
                              }, 0))}
                            </td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => {
                                const pf = c.deductions?.find(d => d.key === 'pf')?.amount || 0;
                                return s + pf;
                              }, 0))}
                            </td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => {
                                const pt = c.deductions?.find(d => d.key === 'pt')?.amount || 0;
                                return s + pt;
                              }, 0))}
                            </td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.tds_details?.monthly_tds || 0), 0))}
                            </td>
                            <td className="p-2 text-right text-amber-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.reimbursements || 0), 0))}
                            </td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.total_deductions || 0), 0))}
                            </td>
                            <td className="p-2 text-right text-blue-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.net_payable || 0), 0))}
                            </td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}

                  {/* DETAILED VIEW */}
                  {registerViewMode === 'detailed' && (
                    <div className="space-y-4">
                      {(registerDetails?.calculations || []).map((calc, i) => {
                        const lopDed = calc.deductions?.find(d => d.key === 'lop');
                        const pfDed = calc.deductions?.find(d => d.key === 'pf');
                        const ptDed = calc.deductions?.find(d => d.key === 'pt');
                        const tdsDed = calc.deductions?.find(d => d.key === 'tds');
                        const attendance = calc.attendance_summary || {};
                        const tds = calc.tds_details || {};
                        
                        return (
                          <div 
                            key={i} 
                            className={`rounded-lg border ${isDark ? 'bg-zinc-800/50 border-zinc-700' : 'bg-white border-gray-200'} overflow-hidden`}
                          >
                            {/* Employee Header */}
                            <div className={`p-4 ${isDark ? 'bg-zinc-800' : 'bg-gray-50'} flex items-center justify-between`}>
                              <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isDark ? 'bg-zinc-700' : 'bg-gray-200'}`}>
                                  <span className="text-lg font-bold">{calc.employee_name?.charAt(0) || 'E'}</span>
                                </div>
                                <div>
                                  <p className="font-semibold">{calc.employee_name}</p>
                                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                                    {calc.employee_code} • {calc.department} • {calc.designation || 'Employee'}
                                  </p>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>Net Payable</p>
                                <p className="text-xl font-bold text-blue-600">{formatCurrency(calc.net_payable)}</p>
                              </div>
                            </div>

                            {/* Detailed Breakdown Grid */}
                            <div className="p-4">
                              <div className="grid grid-cols-5 gap-4">
                                
                                {/* Earnings Column */}
                                <div>
                                  <p className={`text-xs font-semibold mb-2 pb-1 border-b flex items-center gap-1 ${isDark ? 'text-green-400 border-zinc-700' : 'text-green-600 border-gray-200'}`}>
                                    EARNINGS
                                    <span className={`text-xs font-normal ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>(Rule: CTC_STRUCTURE)</span>
                                  </p>
                                  <div className="space-y-1 text-sm">
                                    {calc.earnings?.map((e, ei) => (
                                      <div key={ei} className="flex justify-between">
                                        <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>{e.name}</span>
                                        <span className="text-green-600">+{formatCurrency(Math.abs(e.amount))}</span>
                                      </div>
                                    ))}
                                    <div className={`flex justify-between font-semibold pt-1 mt-1 border-t ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                                      <span>Gross</span>
                                      <span className="text-green-600">{formatCurrency(calc.gross_monthly)}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Deductions Column */}
                                <div>
                                  <p className={`text-xs font-semibold mb-2 pb-1 border-b flex items-center gap-1 ${isDark ? 'text-red-400 border-zinc-700' : 'text-red-600 border-gray-200'}`}>
                                    DEDUCTIONS
                                    <span className={`text-xs font-normal ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>(Rules Applied)</span>
                                  </p>
                                  <div className="space-y-1 text-sm">
                                    {calc.deductions?.map((d, di) => (
                                      <div key={di} className="group">
                                        <div className="flex justify-between">
                                          <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>{d.name}</span>
                                          <span className="text-red-600">-{formatCurrency(Math.abs(d.amount))}</span>
                                        </div>
                                        {d.rule_id && (
                                          <p className={`text-xs ${isDark ? 'text-zinc-600' : 'text-gray-400'}`}>
                                            Rule: {d.rule_id}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                    <div className={`flex justify-between font-semibold pt-1 mt-1 border-t ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                                      <span>Total</span>
                                      <span className="text-red-600">-{formatCurrency(calc.total_deductions)}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Attendance Column */}
                                <div>
                                  <p className={`text-xs font-semibold mb-2 pb-1 border-b ${isDark ? 'text-cyan-400 border-zinc-700' : 'text-cyan-600 border-gray-200'}`}>
                                    ATTENDANCE
                                  </p>
                                  <div className="space-y-1 text-sm">
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Working Days</span>
                                      <span>{attendance.working_days || calc.working_days || '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Present</span>
                                      <span className="text-green-600">{attendance.present || '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Leaves</span>
                                      <span className="text-amber-600">{attendance.leaves || '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>LOP Days</span>
                                      <span className="text-red-600">{attendance.lop_days || calc.lop_days || 0}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Holidays</span>
                                      <span>{attendance.holidays || '-'}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Expenses Column */}
                                <div>
                                  <p className={`text-xs font-semibold mb-2 pb-1 border-b ${isDark ? 'text-amber-400 border-zinc-700' : 'text-amber-600 border-gray-200'}`}>
                                    EXPENSES & REIMBURSEMENTS
                                  </p>
                                  <div className="space-y-1 text-sm">
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Travel</span>
                                      <span className="text-amber-600">{calc.expense_breakdown?.travel ? `+${formatCurrency(calc.expense_breakdown.travel)}` : '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Medical</span>
                                      <span className="text-amber-600">{calc.expense_breakdown?.medical ? `+${formatCurrency(calc.expense_breakdown.medical)}` : '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Food</span>
                                      <span className="text-amber-600">{calc.expense_breakdown?.food ? `+${formatCurrency(calc.expense_breakdown.food)}` : '-'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>Other</span>
                                      <span className="text-amber-600">{calc.expense_breakdown?.other ? `+${formatCurrency(calc.expense_breakdown.other)}` : '-'}</span>
                                    </div>
                                    <div className={`flex justify-between font-semibold pt-1 mt-1 border-t ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                                      <span>Total</span>
                                      <span className="text-amber-600">+{formatCurrency(calc.reimbursements || 0)}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Compliance Column */}
                                <div>
                                  <p className={`text-xs font-semibold mb-2 pb-1 border-b ${isDark ? 'text-purple-400 border-zinc-700' : 'text-purple-600 border-gray-200'}`}>
                                    COMPLIANCE (Business Rules)
                                  </p>
                                  <div className="space-y-1 text-sm">
                                    <div className="flex justify-between">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>PF (12%)</span>
                                      <span>{pfDed ? formatCurrency(Math.abs(pfDed.amount)) : '-'}</span>
                                    </div>
                                    <p className={`text-xs ${isDark ? 'text-zinc-600' : 'text-gray-400'}`}>Rule: PF_CONTRIBUTION</p>
                                    <div className="flex justify-between mt-2">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>PT (Gujarat)</span>
                                      <span>{ptDed ? formatCurrency(Math.abs(ptDed.amount)) : '-'}</span>
                                    </div>
                                    <p className={`text-xs ${isDark ? 'text-zinc-600' : 'text-gray-400'}`}>Rule: PT_GUJARAT</p>
                                    <div className="flex justify-between mt-2">
                                      <span className={isDark ? 'text-zinc-400' : 'text-gray-600'}>TDS</span>
                                      <span>{tds.monthly_tds > 0 ? formatCurrency(tds.monthly_tds) : '₹0'}</span>
                                    </div>
                                    <p className={`text-xs ${isDark ? 'text-zinc-600' : 'text-gray-400'}`}>Rule: TDS_NEW_REGIME_87A</p>
                                    {tds.rebate_87a > 0 && (
                                      <div className={`text-xs mt-1 p-1 rounded ${isDark ? 'bg-green-900/30' : 'bg-green-50'}`}>
                                        <span className="text-green-600">87A Rebate: -{formatCurrency(tds.rebate_87a)}</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* LOP Calculation & Business Rule Reference */}
                              {lopDed && lopDed.amount > 0 && (
                                <div className={`mt-3 p-2 rounded text-xs ${isDark ? 'bg-amber-900/20' : 'bg-amber-50'}`}>
                                  <div className="flex items-center justify-between">
                                    <span className={isDark ? 'text-amber-400' : 'text-amber-600'}>
                                      <strong>LOP Calculation:</strong> {lopDed.formula || `(₹${calc.gross_monthly?.toLocaleString()} / ${attendance.working_days || 31} days) × ${attendance.lop_days || calc.lop_days || 0} LOP days = ₹${Math.abs(lopDed.amount).toLocaleString()}`}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded ${isDark ? 'bg-amber-900/50 text-amber-300' : 'bg-amber-100 text-amber-700'}`}>
                                      Rule: LOP_DEDUCTION
                                    </span>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  
                  {/* FULL EXCEL VIEW - All columns like Excel export */}
                  {registerViewMode === 'excel' && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs border-collapse">
                        <thead>
                          <tr className={`${isDark ? 'bg-zinc-800' : 'bg-gray-100'} sticky top-0`}>
                            {/* Employee Info */}
                            <th className="text-left p-2 font-semibold border-r whitespace-nowrap" style={{minWidth: '140px'}}>Employee</th>
                            <th className="text-left p-2 font-semibold whitespace-nowrap">Code</th>
                            <th className="text-left p-2 font-semibold whitespace-nowrap">Status</th>
                            <th className="text-left p-2 font-semibold border-r whitespace-nowrap">Dept</th>
                            {/* Attendance */}
                            <th className="text-center p-2 font-semibold whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">Work Days</th>
                            <th className="text-center p-2 font-semibold whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">Present</th>
                            <th className="text-center p-2 font-semibold whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">Absent</th>
                            <th className="text-center p-2 font-semibold whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">Paid Leave</th>
                            <th className="text-center p-2 font-semibold whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">LOP Days</th>
                            <th className="text-center p-2 font-semibold border-r whitespace-nowrap bg-blue-50 dark:bg-blue-900/20">Payable Days</th>
                            {/* Salary */}
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-green-50 dark:bg-green-900/20">Salary/Month</th>
                            <th className="text-right p-2 font-semibold border-r whitespace-nowrap bg-green-50 dark:bg-green-900/20">Salary/Day</th>
                            {/* Earnings */}
                            <th className="text-right p-2 font-semibold whitespace-nowrap">Basic</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap">HRA</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap">Special</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap">Incentive</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap">Arrears</th>
                            <th className="text-right p-2 font-semibold border-r whitespace-nowrap text-green-600">Gross</th>
                            {/* Deductions */}
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">LOP Ded.</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">PF</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">PT</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">TDS</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">ESI</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">Advance</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-red-50 dark:bg-red-900/20">Loan EMI</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-orange-50 dark:bg-orange-900/20">Penalty</th>
                            <th className="text-left p-2 font-semibold whitespace-nowrap bg-orange-50 dark:bg-orange-900/20">Penalty Source</th>
                            <th className="text-right p-2 font-semibold border-r whitespace-nowrap text-red-600">Total Ded.</th>
                            {/* Expenses */}
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-amber-50 dark:bg-amber-900/20">Travel</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-amber-50 dark:bg-amber-900/20">Medical</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-amber-50 dark:bg-amber-900/20">Food</th>
                            <th className="text-right p-2 font-semibold whitespace-nowrap bg-amber-50 dark:bg-amber-900/20">Other</th>
                            <th className="text-right p-2 font-semibold border-r whitespace-nowrap text-amber-600">Total Reimb.</th>
                            {/* Net */}
                            <th className="text-right p-2 font-semibold whitespace-nowrap text-blue-600" style={{minWidth: '100px'}}>Net Payable</th>
                            {/* Banking */}
                            <th className="text-left p-2 font-semibold whitespace-nowrap bg-purple-50 dark:bg-purple-900/20">Bank</th>
                            <th className="text-left p-2 font-semibold whitespace-nowrap bg-purple-50 dark:bg-purple-900/20">A/C No.</th>
                            <th className="text-left p-2 font-semibold whitespace-nowrap bg-purple-50 dark:bg-purple-900/20">IFSC</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(registerDetails?.calculations || []).map((calc, i) => {
                            // Parse all data
                            const earnings = calc.earnings || [];
                            const deductions = calc.deductions || [];
                            const attendance = calc.attendance_summary || {};
                            const expenseBreakdown = calc.expense_breakdown || {};
                            const bankDetails = calc.bank_details || {};
                            
                            const basic = (earnings || []).find(e => e.key === 'basic_salary' || e.key === 'basic')?.amount || 0;
                            const hra = (earnings || []).find(e => e.key === 'hra')?.amount || 0;
                            const special = (earnings || []).find(e => e.key === 'special_allowance')?.amount || 0;
                            const incentive = (earnings || []).find(e => e.key === 'incentive')?.amount || 0;
                            const arrears = (earnings || []).find(e => e.key === 'arrears')?.amount || 0;
                            
                            const lopDed = Math.abs((deductions || []).find(d => d.key === 'lop')?.amount || 0);
                            const pfDed = Math.abs((deductions || []).find(d => d.key === 'pf')?.amount || 0);
                            const ptDed = Math.abs((deductions || []).find(d => d.key === 'pt' || d.key === 'professional_tax')?.amount || 0);
                            const tdsDed = Math.abs(calc.tds_details?.monthly_tds || 0);
                            const esiDed = Math.abs((deductions || []).find(d => d.key === 'esi')?.amount || 0);
                            const advanceDed = Math.abs((deductions || []).find(d => d.key === 'advance_recovery')?.amount || 0);
                            const loanEmi = Math.abs((deductions || []).find(d => d.key === 'loan_emi')?.amount || 0);
                            
                            // Penalty - aggregate all penalty types
                            const penaltyItems = (deductions || []).filter(d => d.key?.includes('penalty'));
                            const totalPenalty = (penaltyItems || []).reduce((s, p) => s + Math.abs(p.amount || 0), 0);
                            const penaltySources = (penaltyItems || []).map(p => p.details || p.name || 'Manual').join(', ');
                            
                            const workingDays = attendance.working_days || calc.working_days || 22;
                            const payableDays = workingDays - (attendance.lop_days || calc.lop_days || 0);
                            const salaryPerDay = calc.gross_monthly && workingDays > 0 ? (calc.gross_monthly / workingDays) : 0;
                            
                            // Expenses
                            const travelExp = expenseBreakdown.travel || 0;
                            const medicalExp = expenseBreakdown.medical || 0;
                            const foodExp = expenseBreakdown.food || 0;
                            const otherExp = (expenseBreakdown.other || 0) + (expenseBreakdown.telephone || 0);
                            const totalReimb = calc.total_reimbursements || calc.reimbursements || (travelExp + medicalExp + foodExp + otherExp);
                            
                            // Status
                            const status = calc.exit_status ? `F&F (${calc.exit_status})` : (calc.is_active === false ? 'Inactive' : 'Active');
                            
                            return (
                              <tr 
                                key={i} 
                                className={`border-t ${isDark ? 'border-zinc-800 hover:bg-zinc-800/50' : 'border-gray-100 hover:bg-gray-50'}`}
                              >
                                {/* Employee Info */}
                                <td className="p-2 border-r">
                                  <p className="font-medium truncate" style={{maxWidth: '130px'}}>{calc.employee_name}</p>
                                </td>
                                <td className="p-2 text-xs text-gray-500">{calc.employee_code}</td>
                                <td className="p-2">
                                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                                    status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                                  }`}>{status}</span>
                                </td>
                                <td className="p-2 border-r">{calc.department}</td>
                                
                                {/* Attendance */}
                                <td className="p-2 text-center bg-blue-50/50 dark:bg-blue-900/10">{workingDays}</td>
                                <td className="p-2 text-center bg-blue-50/50 dark:bg-blue-900/10">{attendance.present_days || attendance.present || '-'}</td>
                                <td className="p-2 text-center bg-blue-50/50 dark:bg-blue-900/10">{attendance.absent_days || '-'}</td>
                                <td className="p-2 text-center bg-blue-50/50 dark:bg-blue-900/10">{attendance.paid_leave_days || '-'}</td>
                                <td className="p-2 text-center bg-blue-50/50 dark:bg-blue-900/10 text-red-600 font-medium">{attendance.lop_days || calc.lop_days || 0}</td>
                                <td className="p-2 text-center border-r bg-blue-50/50 dark:bg-blue-900/10 font-medium">{payableDays.toFixed(1)}</td>
                                
                                {/* Salary */}
                                <td className="p-2 text-right bg-green-50/50 dark:bg-green-900/10 font-medium">{formatCurrency(calc.gross_monthly)}</td>
                                <td className="p-2 text-right border-r bg-green-50/50 dark:bg-green-900/10">{formatCurrency(salaryPerDay)}</td>
                                
                                {/* Earnings */}
                                <td className="p-2 text-right">{formatCurrency(basic)}</td>
                                <td className="p-2 text-right">{formatCurrency(hra)}</td>
                                <td className="p-2 text-right">{formatCurrency(special)}</td>
                                <td className="p-2 text-right">{incentive > 0 ? formatCurrency(incentive) : '-'}</td>
                                <td className="p-2 text-right">{arrears > 0 ? formatCurrency(arrears) : '-'}</td>
                                <td className="p-2 text-right border-r font-medium text-green-600">{formatCurrency(calc.total_earnings || calc.gross_monthly)}</td>
                                
                                {/* Deductions */}
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{lopDed > 0 ? formatCurrency(lopDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{pfDed > 0 ? formatCurrency(pfDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{ptDed > 0 ? formatCurrency(ptDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{tdsDed > 0 ? formatCurrency(tdsDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{esiDed > 0 ? formatCurrency(esiDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{advanceDed > 0 ? formatCurrency(advanceDed) : '-'}</td>
                                <td className="p-2 text-right bg-red-50/50 dark:bg-red-900/10 text-red-600">{loanEmi > 0 ? formatCurrency(loanEmi) : '-'}</td>
                                <td className="p-2 text-right bg-orange-50/50 dark:bg-orange-900/10 text-orange-600 font-medium">{totalPenalty > 0 ? formatCurrency(totalPenalty) : '-'}</td>
                                <td className="p-2 text-left bg-orange-50/50 dark:bg-orange-900/10 text-xs text-orange-700 truncate" style={{maxWidth: '120px'}} title={penaltySources}>{penaltySources || '-'}</td>
                                <td className="p-2 text-right border-r font-medium text-red-600">{formatCurrency(calc.total_deductions)}</td>
                                
                                {/* Expenses */}
                                <td className="p-2 text-right bg-amber-50/50 dark:bg-amber-900/10">{travelExp > 0 ? formatCurrency(travelExp) : '-'}</td>
                                <td className="p-2 text-right bg-amber-50/50 dark:bg-amber-900/10">{medicalExp > 0 ? formatCurrency(medicalExp) : '-'}</td>
                                <td className="p-2 text-right bg-amber-50/50 dark:bg-amber-900/10">{foodExp > 0 ? formatCurrency(foodExp) : '-'}</td>
                                <td className="p-2 text-right bg-amber-50/50 dark:bg-amber-900/10">{otherExp > 0 ? formatCurrency(otherExp) : '-'}</td>
                                <td className="p-2 text-right border-r font-medium text-amber-600">{totalReimb > 0 ? formatCurrency(totalReimb) : '-'}</td>
                                
                                {/* Net */}
                                <td className="p-2 text-right font-bold text-blue-600">{formatCurrency(calc.net_payable)}</td>
                                
                                {/* Banking */}
                                <td className="p-2 bg-purple-50/50 dark:bg-purple-900/10 text-xs">{bankDetails.bank_name || '-'}</td>
                                <td className="p-2 bg-purple-50/50 dark:bg-purple-900/10 text-xs">{bankDetails.account_number || '-'}</td>
                                <td className="p-2 bg-purple-50/50 dark:bg-purple-900/10 text-xs">{bankDetails.ifsc_code || '-'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot>
                          <tr className={`font-bold border-t-2 ${isDark ? 'border-zinc-600 bg-zinc-800' : 'border-gray-300 bg-gray-100'}`}>
                            <td className="p-2" colSpan={4}>Total ({registerDetails.calculations.length} employees)</td>
                            <td colSpan={6}></td>
                            <td className="p-2 text-right text-green-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.gross_monthly || 0), 0))}
                            </td>
                            <td></td>
                            <td colSpan={5}></td>
                            <td className="p-2 text-right text-green-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.total_earnings || c.gross_monthly || 0), 0))}
                            </td>
                            <td colSpan={8}></td>
                            <td className="p-2 text-right text-orange-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => {
                                const penalties = (c.deductions || []).filter(d => d.key?.includes('penalty'));
                                return s + (penalties || []).reduce((ps, p) => ps + Math.abs(p.amount || 0), 0);
                              }, 0))}
                            </td>
                            <td></td>
                            <td className="p-2 text-right text-red-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.total_deductions || 0), 0))}
                            </td>
                            <td colSpan={4}></td>
                            <td className="p-2 text-right text-amber-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.total_reimbursements || c.reimbursements || 0), 0))}
                            </td>
                            <td className="p-2 text-right text-blue-600">
                              {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.net_payable || 0), 0))}
                            </td>
                            <td colSpan={3}></td>
                          </tr>
                        </tfoot>
                      </table>
                      
                      {/* Legend for penalty sources */}
                      <div className={`mt-4 p-3 rounded-lg text-xs ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
                        <p className="font-semibold mb-2">Penalty Sources:</p>
                        <div className="flex flex-wrap gap-4">
                          <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                            <strong>Manual</strong> - HR/Admin entered directly
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-500"></span>
                            <strong>AT002</strong> - Late Arrival Rule ({'>'}3 lates = 0.5 day LOP each)
                          </span>
                          <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                            <strong>Policy Violation</strong> - Business rule triggered
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className={`text-center py-12 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                  <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No payroll data for {selectedMonth}</p>
                  <p className="text-sm">Run payroll first to generate register</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* ==================== APPROVAL TAB ==================== */}
        <TabsContent value="approval">
          <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                Approval Workflow
              </CardTitle>
              <CardDescription>
                Payroll approval flow: Draft → HR Review → Admin Approve → Locked
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Approval History */}
              {loadingRegisters ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 mx-auto animate-spin" />
                </div>
              ) : (
                <div className="space-y-4">
                  {registers.length > 0 ? (
                    (registers || []).map((reg, i) => (
                      <div 
                        key={i}
                        className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-gray-200'}`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <Calendar className="w-5 h-5 text-blue-500" />
                            <span className="font-medium">{reg.month}</span>
                            {getStatusBadge(reg.status)}
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-blue-600">{formatCurrency(reg.total_net_payable)}</p>
                            <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                              {reg.total_employees} employees
                            </p>
                          </div>
                        </div>
                        
                        {/* Approval Actions */}
                        {reg.status === 'draft' && (
                          <Button 
                            size="sm" 
                            onClick={() => {
                              setSelectedMonth(reg.month);
                              setShowApprovalDialog(true);
                            }}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            <Send className="w-4 h-4 mr-2" />
                            Submit for Approval
                          </Button>
                        )}
                        
                        {reg.status === 'pending_admin_approval' && (
                          <div className="flex gap-2">
                            <Button 
                              size="sm"
                              onClick={() => {
                                setSelectedMonth(reg.month);
                                setShowApprovalDialog(true);
                              }}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              <Check className="w-4 h-4 mr-2" />
                              Approve
                            </Button>
                            <Button 
                              size="sm"
                              variant="destructive"
                              onClick={() => {
                                setSelectedMonth(reg.month);
                                setShowApprovalDialog(true);
                              }}
                            >
                              <X className="w-4 h-4 mr-2" />
                              Reject
                            </Button>
                          </div>
                        )}
                        
                        {reg.status === 'locked' && (
                          <p className={`text-sm flex items-center gap-2 ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                            <Lock className="w-4 h-4" />
                            Approved on {reg.approved_at ? new Date(reg.approved_at).toLocaleDateString() : 'N/A'}
                          </p>
                        )}
                        
                        {/* Approval History */}
                        {reg.approval_history?.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-dashed">
                            <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>History</p>
                            <div className="space-y-1">
                              {(reg?.approval_history || []).map((h, idx) => (
                                <p key={idx} className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                                  {h.action.toUpperCase()} by {h.by_name} • {new Date(h.at).toLocaleString()}
                                  {h.remarks && ` - "${h.remarks}"`}
                                  {h.reason && ` - Reason: "${h.reason}"`}
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className={`text-center py-12 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                      <CheckCircle2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No payroll registers found</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* ==================== PENALTY DASHBOARD ==================== */}
        <TabsContent value="penalty-dashboard">
          <PenaltyDashboard isDark={isDark} />
        </TabsContent>

        {/* ==================== PRO-RATA TAB ==================== */}
        <TabsContent value="pro-rata">
          <ProRataPanel isDark={isDark} selectedMonth={selectedMonth} />
        </TabsContent>
      </Tabs>
      
      {/* ==================== BREAKDOWN DIALOG ==================== */}
      <Dialog open={showBreakdown} onOpenChange={setShowBreakdown}>
        <DialogContent className={`max-w-2xl ${isDark ? 'bg-zinc-900 border-zinc-800' : ''}`}>
          <DialogHeader>
            <DialogTitle>Calculation Breakdown</DialogTitle>
            <DialogDescription>
              Field-level traceability for {breakdownEmployee?.employee_name}
            </DialogDescription>
          </DialogHeader>
          
          {breakdownEmployee && (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className={`p-3 rounded text-center ${isDark ? 'bg-green-900/30' : 'bg-green-50'}`}>
                  <p className="text-xs text-green-600">Gross</p>
                  <p className="font-bold text-green-600">{formatCurrency(breakdownEmployee.gross_monthly)}</p>
                </div>
                <div className={`p-3 rounded text-center ${isDark ? 'bg-red-900/30' : 'bg-red-50'}`}>
                  <p className="text-xs text-red-600">Deductions</p>
                  <p className="font-bold text-red-600">{formatCurrency(breakdownEmployee.total_deductions)}</p>
                </div>
                <div className={`p-3 rounded text-center ${isDark ? 'bg-blue-900/30' : 'bg-blue-50'}`}>
                  <p className="text-xs text-blue-600">Net Payable</p>
                  <p className="font-bold text-blue-600">{formatCurrency(breakdownEmployee.net_payable)}</p>
                </div>
              </div>
              
              {/* Breakdown Table */}
              <table className="w-full text-sm">
                <thead>
                  <tr className={`border-b ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                    <th className="text-left p-2">Component</th>
                    <th className="text-left p-2">Input</th>
                    <th className="text-left p-2">Formula</th>
                    <th className="text-right p-2">Output</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Earnings */}
                  {breakdownEmployee.earnings?.map((e, i) => (
                    <tr key={`e-${i}`} className={`border-b ${isDark ? 'border-zinc-800' : 'border-gray-100'}`}>
                      <td className="p-2 text-green-600">{e.name}</td>
                      <td className={`p-2 text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                        {Object.entries(e.calculation?.input_values || {}).map(([k, v]) => `${k}: ${v}`).join(', ')}
                      </td>
                      <td className={`p-2 text-xs font-mono ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                        {e.calculation?.formula_used}
                      </td>
                      <td className="p-2 text-right font-medium text-green-600">+{formatCurrency(e.amount)}</td>
                    </tr>
                  ))}
                  {/* Deductions */}
                  {breakdownEmployee.deductions?.map((d, i) => (
                    <tr key={`d-${i}`} className={`border-b ${isDark ? 'border-zinc-800' : 'border-gray-100'}`}>
                      <td className="p-2 text-red-600">{d.name}</td>
                      <td className={`p-2 text-xs ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                        {Object.entries(d.calculation?.input_values || {}).map(([k, v]) => `${k}: ${v}`).join(', ')}
                      </td>
                      <td className={`p-2 text-xs font-mono ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                        {d.calculation?.formula_used}
                      </td>
                      <td className="p-2 text-right font-medium text-red-600">-{formatCurrency(d.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* ==================== APPROVAL DIALOG ==================== */}
      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <DialogContent className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
          <DialogHeader>
            <DialogTitle>Payroll Approval - {selectedMonth}</DialogTitle>
            <DialogDescription>
              {currentRegister?.status === 'draft' && 'Submit payroll for admin approval'}
              {currentRegister?.status === 'pending_admin_approval' && 'Approve or reject this payroll'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {currentRegister && (
              <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Employees</p>
                    <p className="font-bold">{currentRegister.total_employees}</p>
                  </div>
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-gray-500'}>Net Payable</p>
                    <p className="font-bold text-blue-600">{formatCurrency(currentRegister.total_net_payable)}</p>
                  </div>
                </div>
              </div>
            )}
            
            <div>
              <Label>Remarks / Reason</Label>
              <Input
                value={approvalRemarks}
                onChange={(e) => setApprovalRemarks(e.target.value)}
                placeholder="Enter remarks or rejection reason..."
                className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
              />
            </div>
            
            <div className="flex gap-2 justify-end">
              {currentRegister?.status === 'draft' && (
                <Button 
                  onClick={handleSubmit}
                  disabled={submitMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {submitMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Submit for Approval
                </Button>
              )}
              
              {currentRegister?.status === 'pending_admin_approval' && (
                <>
                  <Button 
                    onClick={handleReject}
                    disabled={rejectMutation.isPending}
                    variant="destructive"
                  >
                    {rejectMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Reject
                  </Button>
                  <Button 
                    onClick={handleApprove}
                    disabled={approveMutation.isPending}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {approveMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Approve & Lock
                  </Button>
                </>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* ==================== EMAIL APPROVAL DIALOG ==================== */}
      <Dialog open={showEmailDialog} onOpenChange={setShowEmailDialog}>
        <DialogContent className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-500" />
              Send Payroll for Email Approval
            </DialogTitle>
            <DialogDescription>
              Send the payroll register as an Excel attachment for approval
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Summary */}
            {registerDetails?.calculations?.length > 0 && (
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : ''}`}>
                  Payroll Summary - {selectedMonth}
                </p>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>Employees</p>
                    <p className="font-bold">{registerDetails.calculations.length}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>Total Gross</p>
                    <p className="font-bold text-green-600">
                      {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.gross_monthly || 0), 0))}
                    </p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>Net Payable</p>
                    <p className="font-bold text-blue-600">
                      {formatCurrency((registerDetails?.calculations || []).reduce((s, c) => s + (c.net_payable || 0), 0))}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Recipient Email */}
            <div>
              <Label>Recipient Email *</Label>
              <Input
                type="email"
                value={emailRecipient}
                onChange={(e) => setEmailRecipient(e.target.value)}
                placeholder="approver@company.com"
                className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
              />
            </div>
            
            {/* Custom Message */}
            <div>
              <Label>Message (Optional)</Label>
              <Input
                value={emailMessage}
                onChange={(e) => setEmailMessage(e.target.value)}
                placeholder="Please review and approve the payroll..."
                className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
              />
            </div>
            
            {/* Info */}
            <div className={`p-3 rounded-lg border-l-4 border-blue-500 ${isDark ? 'bg-blue-900/20' : 'bg-blue-50'}`}>
              <p className={`text-xs ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
                The detailed payroll register will be attached as an Excel file (.xlsx) with all earnings, 
                deductions, attendance, and compliance data.
              </p>
            </div>
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setShowEmailDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSendForEmailApproval}
              disabled={isSendingEmail || !emailRecipient.trim()}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="btn-send-email"
            >
              {isSendingEmail ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Send for Approval
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ==================== PRO-RATA PANEL COMPONENT ====================

function ProRataPanel({ isDark, selectedMonth }) {
  const [proRataData, setProRataData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [checked, setChecked] = useState(false);

  const checkProRata = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/payroll/engine/pro-rata/check/${selectedMonth}`);
      setProRataData(res.data);
      setChecked(true);
    } catch (err) {
      console.error('Pro-rata check failed:', err);
      toast.error('Failed to check pro-rata employees');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  const proRataEmployees = proRataData?.prorata_employees || [];

  return (
    <div className="space-y-4" data-testid="pro-rata-panel">
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Calendar className={`w-5 h-5 ${isDark ? 'text-blue-400' : 'text-blue-600'}`} />
                Onboarding Pro-rata - {selectedMonth}
              </CardTitle>
              <CardDescription className="mt-1">
                Auto-detects mid-month joiners and calculates proportional salary for their first month
              </CardDescription>
            </div>
            <Button
              onClick={checkProRata}
              disabled={loading}
              variant={checked ? "outline" : "default"}
              data-testid="check-prorata-btn"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Users className="w-4 h-4 mr-2" />
              )}
              {checked ? 'Re-check' : 'Check Pro-rata'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!checked ? (
            <div className={`text-center py-12 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
              <Calendar className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p className="text-base font-medium mb-1">Pro-rata Salary Calculator</p>
              <p className="text-sm max-w-md mx-auto">
                Click "Check Pro-rata" to scan for employees who joined during {selectedMonth} and auto-calculate their proportional salary.
              </p>
              <div className={`mt-6 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'} max-w-md mx-auto text-left`}>
                <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-blue-700'}`}>How it works:</p>
                <ul className={`text-xs space-y-1 ${isDark ? 'text-zinc-400' : 'text-blue-600'}`}>
                  <li>1. Identifies employees with joining dates after the 1st of the month</li>
                  <li>2. Calculates days worked = (month end - joining date + 1)</li>
                  <li>3. Pro-rata salary = (Full Gross / Days in month) * Days worked</li>
                  <li>4. Automatically applied during payroll calculation</li>
                </ul>
              </div>
            </div>
          ) : proRataEmployees.length === 0 ? (
            <div className={`text-center py-10 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
              <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500 opacity-70" />
              <p className="font-medium">No mid-month joiners for {selectedMonth}</p>
              <p className="text-sm mt-1">All active employees have joining dates before this month or on the 1st</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${isDark ? 'bg-amber-900/20 text-amber-300' : 'bg-amber-50 text-amber-800'}`}>
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <p className="text-sm">
                  <strong>{proRataEmployees.length}</strong> mid-month joiner{proRataEmployees.length > 1 ? 's' : ''} detected.
                  Pro-rata will be automatically applied when running payroll for {selectedMonth}.
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className={`w-full text-sm ${isDark ? 'text-zinc-300' : ''}`} data-testid="prorata-table">
                  <thead>
                    <tr className={`border-b ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <th className="text-left p-3 font-medium">Employee</th>
                      <th className="text-left p-3 font-medium">Department</th>
                      <th className="text-center p-3 font-medium">Joining Date</th>
                      <th className="text-center p-3 font-medium">Days Worked</th>
                      <th className="text-center p-3 font-medium">Days in Month</th>
                      <th className="text-right p-3 font-medium">Full Gross</th>
                      <th className="text-right p-3 font-medium">Pro-rata Gross</th>
                      <th className="text-right p-3 font-medium">Difference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(proRataEmployees || []).map((emp, idx) => {
                      const diff = (emp.full_gross || 0) - (emp.prorata_gross || 0);
                      return (
                        <tr key={emp.employee_id || idx} className={`border-b ${isDark ? 'border-zinc-800 hover:bg-zinc-800/50' : 'border-zinc-100 hover:bg-zinc-50'}`}>
                          <td className="p-3">
                            <div className="font-medium">{emp.employee_name}</div>
                            <div className="text-xs text-zinc-400">{emp.employee_code}</div>
                          </td>
                          <td className="p-3 text-zinc-500">{emp.department || '-'}</td>
                          <td className="p-3 text-center">
                            <Badge variant="outline" className="text-xs">
                              {emp.joining_date}
                            </Badge>
                          </td>
                          <td className="p-3 text-center font-medium">{emp.days_worked}</td>
                          <td className="p-3 text-center text-zinc-500">{emp.days_in_month}</td>
                          <td className="p-3 text-right text-zinc-500">{formatCurrency(emp.full_gross)}</td>
                          <td className="p-3 text-right font-semibold text-blue-600 dark:text-blue-400">
                            {formatCurrency(emp.prorata_gross)}
                          </td>
                          <td className="p-3 text-right text-red-500">
                            -{formatCurrency(diff)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  {proRataEmployees.length > 0 && (
                    <tfoot>
                      <tr className={`font-bold ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                        <td className="p-3" colSpan={5}>Total Impact</td>
                        <td className="p-3 text-right">
                          {formatCurrency((proRataEmployees || []).reduce((s, e) => s + (e.full_gross || 0), 0))}
                        </td>
                        <td className="p-3 text-right text-blue-600 dark:text-blue-400">
                          {formatCurrency((proRataEmployees || []).reduce((s, e) => s + (e.prorata_gross || 0), 0))}
                        </td>
                        <td className="p-3 text-right text-red-500">
                          -{formatCurrency((proRataEmployees || []).reduce((s, e) => s + ((e.full_gross || 0) - (e.prorata_gross || 0)), 0))}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>

              {proRataEmployees.length > 0 && (proRataEmployees[0] || {}).formula && (
                <div className={`text-xs p-3 rounded-lg ${isDark ? 'bg-zinc-800 text-zinc-400' : 'bg-zinc-100 text-zinc-500'}`}>
                  <strong>Formula:</strong> {proRataEmployees[0].formula}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== PENALTY DASHBOARD COMPONENT ====================

function PenaltyDashboard({ isDark }) {
  const [monthsToShow, setMonthsToShow] = useState(6);
  
  // Fetch penalty dashboard data
  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ['penalty-dashboard', monthsToShow],
    queryFn: async () => {
      const res = await axios.get(`${API}/attendance/penalty-dashboard?months=${monthsToShow}`);
      return res.data;
    },
    staleTime: 5 * 60 * 1000
  });
  
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    );
  }
  
  if (error) {
    return (
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
        <CardContent className="py-10 text-center">
          <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-500" />
          <p className="text-red-500">Failed to load penalty dashboard</p>
          <p className="text-sm text-zinc-500">{error.message}</p>
        </CardContent>
      </Card>
    );
  }
  
  const { 
    monthly_trends = [], 
    top_violators = [], 
    department_breakdown = [],
    current_month_summary = {},
    policy_context = {}
  } = dashboardData || {};
  
  // Calculate max for chart scaling
  const maxPenalty = Math.max(...(monthly_trends || []).map(t => t.total_amount), 1);
  
  return (
    <div className="space-y-6">
      {/* Header with Policy Context */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-amber-500" />
            Penalty Analytics Dashboard
          </h2>
          <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>
            Late arrival penalties and compliance tracking
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`text-xs px-3 py-1 rounded ${isDark ? 'bg-zinc-800 text-zinc-400' : 'bg-gray-100 text-gray-600'}`}>
            <Timer className="w-3 h-3 inline mr-1" />
            Core Hours: {policy_context.core_hours_start} - {policy_context.core_hours_end}
          </div>
          <div className={`text-xs px-3 py-1 rounded ${isDark ? 'bg-zinc-800 text-zinc-400' : 'bg-gray-100 text-gray-600'}`}>
            Grace: {policy_context.grace_days_per_month} days/month | ₹{policy_context.late_penalty_per_day}/day
          </div>
          <Select value={String(monthsToShow)} onValueChange={(v) => setMonthsToShow(Number(v))}>
            <SelectTrigger className={`w-32 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3">Last 3 Months</SelectItem>
              <SelectItem value="6">Last 6 Months</SelectItem>
              <SelectItem value="12">Last 12 Months</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {/* Current Month Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className={`${isDark ? 'bg-gradient-to-br from-red-900/20 to-zinc-900 border-red-800/50' : 'bg-gradient-to-br from-red-50 to-white border-red-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-red-400' : 'text-red-600'}`}>This Month Penalties</p>
                <p className="text-2xl font-bold text-red-500">{formatCurrency(current_month_summary.total_penalty_amount)}</p>
              </div>
              <div className={`p-3 rounded-full ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <IndianRupee className="w-6 h-6 text-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className={`${isDark ? 'bg-gradient-to-br from-amber-900/20 to-zinc-900 border-amber-800/50' : 'bg-gradient-to-br from-amber-50 to-white border-amber-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>Employees Penalized</p>
                <p className="text-2xl font-bold text-amber-500">{current_month_summary.total_employees_penalized || 0}</p>
              </div>
              <div className={`p-3 rounded-full ${isDark ? 'bg-amber-900/30' : 'bg-amber-100'}`}>
                <UserX className="w-6 h-6 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className={`${isDark ? 'bg-gradient-to-br from-purple-900/20 to-zinc-900 border-purple-800/50' : 'bg-gradient-to-br from-purple-50 to-white border-purple-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>Total Penalty Days</p>
                <p className="text-2xl font-bold text-purple-500">{current_month_summary.total_penalty_days || 0}</p>
              </div>
              <div className={`p-3 rounded-full ${isDark ? 'bg-purple-900/30' : 'bg-purple-100'}`}>
                <Calendar className="w-6 h-6 text-purple-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className={`${isDark ? 'bg-gradient-to-br from-blue-900/20 to-zinc-900 border-blue-800/50' : 'bg-gradient-to-br from-blue-50 to-white border-blue-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>Avg per Employee</p>
                <p className="text-2xl font-bold text-blue-500">{formatCurrency(current_month_summary.avg_penalty_per_employee)}</p>
              </div>
              <div className={`p-3 rounded-full ${isDark ? 'bg-blue-900/30' : 'bg-blue-100'}`}>
                <TrendingUp className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Monthly Trends Chart */}
        <Card className={`col-span-2 ${isDark ? 'bg-zinc-900 border-zinc-800' : ''}`}>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              Monthly Penalty Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(monthly_trends || []).slice().reverse().map((trend, idx) => {
                const percentage = (trend.total_amount / maxPenalty) * 100;
                const isCurrentMonth = idx === monthly_trends.length - 1;
                
                return (
                  <div key={trend.month} className="flex items-center gap-3">
                    <div className="w-20 text-sm font-medium">{trend.month_name}</div>
                    <div className="flex-1 h-8 relative">
                      <div 
                        className={`h-full rounded transition-all duration-500 ${
                          isCurrentMonth 
                            ? 'bg-gradient-to-r from-red-500 to-red-400' 
                            : isDark ? 'bg-gradient-to-r from-amber-700 to-amber-600' : 'bg-gradient-to-r from-amber-400 to-amber-300'
                        }`}
                        style={{ width: `${Math.max(percentage, 2)}%` }}
                      />
                      <div className="absolute inset-0 flex items-center px-2">
                        <span className={`text-xs font-medium ${percentage > 30 ? 'text-white' : isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                          {formatCurrency(trend.total_amount)} ({trend.employee_count} emp)
                        </span>
                      </div>
                    </div>
                    <div className="w-16 text-right text-xs text-zinc-500">
                      {trend.total_days}d
                    </div>
                  </div>
                );
              })}
            </div>
            
            {monthly_trends.length === 0 && (
              <div className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                <BarChart3 className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p>No penalty data available</p>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Top Violators */}
        <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              Top Violators
            </CardTitle>
            <CardDescription>Employees with highest penalties</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(top_violators || []).slice(0, 5).map((violator, idx) => (
                <div 
                  key={violator.employee_id}
                  className={`flex items-center gap-3 p-2 rounded ${isDark ? 'bg-zinc-800/50' : 'bg-gray-50'}`}
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    idx === 0 ? 'bg-red-500 text-white' :
                    idx === 1 ? 'bg-orange-500 text-white' :
                    idx === 2 ? 'bg-amber-500 text-white' :
                    isDark ? 'bg-zinc-700 text-zinc-300' : 'bg-gray-200 text-gray-600'
                  }`}>
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{violator.employee_name}</p>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>
                      {violator.employee_code} • {violator.department}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-red-500">{formatCurrency(violator.total_penalty_amount)}</p>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-500'}`}>
                      {violator.total_penalty_days}d in {violator.months_with_penalties}mo
                    </p>
                  </div>
                </div>
              ))}
              
              {top_violators.length === 0 && (
                <div className={`text-center py-6 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                  <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500 opacity-50" />
                  <p className="text-sm">No violators found</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Department Breakdown */}
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-500" />
            Department-wise Penalty Summary (Current Month)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={`border-b ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                  <th className="text-left p-3 font-medium">Department</th>
                  <th className="text-center p-3 font-medium">Total Employees</th>
                  <th className="text-center p-3 font-medium">Penalized</th>
                  <th className="text-center p-3 font-medium">Compliance %</th>
                  <th className="text-right p-3 font-medium">Penalty Days</th>
                  <th className="text-right p-3 font-medium">Total Amount</th>
                </tr>
              </thead>
              <tbody>
                {(department_breakdown || []).map((dept) => {
                  const complianceRate = dept.total_employees > 0 
                    ? ((dept.total_employees - dept.employees_with_penalties) / dept.total_employees * 100).toFixed(0)
                    : 100;
                  
                  return (
                    <tr 
                      key={dept.department}
                      className={`border-b ${isDark ? 'border-zinc-800 hover:bg-zinc-800/50' : 'border-gray-100 hover:bg-gray-50'}`}
                    >
                      <td className="p-3 font-medium">{dept.department || 'Unassigned'}</td>
                      <td className="p-3 text-center">{dept.total_employees}</td>
                      <td className="p-3 text-center">
                        <span className={dept.employees_with_penalties > 0 ? 'text-red-500 font-medium' : ''}>
                          {dept.employees_with_penalties}
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        <Badge className={
                          complianceRate >= 90 ? 'bg-emerald-100 text-emerald-700' :
                          complianceRate >= 70 ? 'bg-amber-100 text-amber-700' :
                          'bg-red-100 text-red-700'
                        }>
                          {complianceRate}%
                        </Badge>
                      </td>
                      <td className="p-3 text-right">{dept.total_penalty_days}</td>
                      <td className="p-3 text-right font-medium text-red-500">
                        {dept.total_penalty_amount > 0 ? formatCurrency(dept.total_penalty_amount) : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {department_breakdown.length > 0 && (
                <tfoot>
                  <tr className={`font-bold ${isDark ? 'bg-zinc-800' : 'bg-gray-100'}`}>
                    <td className="p-3">Total</td>
                    <td className="p-3 text-center">{(department_breakdown || []).reduce((sum, d) => sum + d.total_employees, 0)}</td>
                    <td className="p-3 text-center text-red-500">{(department_breakdown || []).reduce((sum, d) => sum + d.employees_with_penalties, 0)}</td>
                    <td className="p-3 text-center">-</td>
                    <td className="p-3 text-right">{(department_breakdown || []).reduce((sum, d) => sum + d.total_penalty_days, 0)}</td>
                    <td className="p-3 text-right text-red-500">
                      {formatCurrency((department_breakdown || []).reduce((sum, d) => sum + d.total_penalty_amount, 0))}
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
            
            {department_breakdown.length === 0 && (
              <div className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                <Building2 className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p>No department data available</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
