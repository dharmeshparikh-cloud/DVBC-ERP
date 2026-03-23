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
  X
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
  const currentRegister = registers.find(r => r.month === selectedMonth);
  
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
        ...data.map(row => columns.map(col => `"${row[col] || ''}"`).join(','))
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
                      {employees.map(emp => (
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
                          {simulationResult.earnings.map((e, i) => (
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
                          {simulationResult.deductions.map((d, i) => (
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
                            TDS (Income Tax) - {simulationResult.tds_details.regime?.toUpperCase()} Regime
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
                              {comparisonData.changes.slice(0, 5).map((change, idx) => {
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
                        ...template.map(row => columns.map(col => {
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
                    {currentRegister.department_summary && Object.keys(currentRegister.department_summary).length > 0 && (
                      <div className="mt-4">
                        <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : ''}`}>By Department</p>
                        <div className="grid grid-cols-3 gap-2">
                          {Object.entries(currentRegister.department_summary).map(([dept, data]) => (
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
                    Detailed employee-wise payroll breakdown with traceability
                  </CardDescription>
                </div>
                <Button variant="outline" onClick={handleExport} data-testid="btn-export">
                  <Download className="w-4 h-4 mr-2" />
                  Export CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingDetails ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 mx-auto animate-spin text-blue-500" />
                  <p className={`mt-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>Loading...</p>
                </div>
              ) : registerDetails?.calculations?.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className={isDark ? 'border-zinc-700' : 'border-gray-200'}>
                        <th className="text-left p-2">Employee</th>
                        <th className="text-left p-2">Department</th>
                        <th className="text-right p-2">Gross</th>
                        <th className="text-right p-2">LOP</th>
                        <th className="text-right p-2">PF</th>
                        <th className="text-right p-2">Other Ded.</th>
                        <th className="text-right p-2">Net Payable</th>
                        <th className="text-center p-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registerDetails.calculations.map((calc, i) => {
                        const lopDed = calc.deductions?.find(d => d.key === 'lop')?.amount || 0;
                        const pfDed = calc.deductions?.find(d => d.key === 'pf')?.amount || 0;
                        const otherDed = calc.total_deductions - lopDed - pfDed;
                        
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
                            <td className="p-2 text-right text-green-600">{formatCurrency(calc.gross_monthly)}</td>
                            <td className="p-2 text-right text-red-600">{lopDed > 0 ? `-${formatCurrency(lopDed)}` : '-'}</td>
                            <td className="p-2 text-right text-red-600">{pfDed > 0 ? `-${formatCurrency(pfDed)}` : '-'}</td>
                            <td className="p-2 text-right text-red-600">{otherDed > 0 ? `-${formatCurrency(otherDed)}` : '-'}</td>
                            <td className="p-2 text-right font-medium text-blue-600">{formatCurrency(calc.net_payable)}</td>
                            <td className="p-2 text-center">
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => {
                                  setBreakdownEmployee(calc);
                                  setShowBreakdown(true);
                                }}
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot>
                      <tr className={`font-bold border-t-2 ${isDark ? 'border-zinc-600' : 'border-gray-300'}`}>
                        <td className="p-2" colSpan={2}>Total ({registerDetails.calculations.length} employees)</td>
                        <td className="p-2 text-right text-green-600">
                          {formatCurrency(registerDetails.calculations.reduce((s, c) => s + (c.gross_monthly || 0), 0))}
                        </td>
                        <td className="p-2 text-right text-red-600">
                          {formatCurrency(registerDetails.calculations.reduce((s, c) => {
                            const lop = c.deductions?.find(d => d.key === 'lop')?.amount || 0;
                            return s + lop;
                          }, 0))}
                        </td>
                        <td className="p-2 text-right text-red-600">
                          {formatCurrency(registerDetails.calculations.reduce((s, c) => {
                            const pf = c.deductions?.find(d => d.key === 'pf')?.amount || 0;
                            return s + pf;
                          }, 0))}
                        </td>
                        <td className="p-2 text-right text-red-600">-</td>
                        <td className="p-2 text-right text-blue-600">
                          {formatCurrency(registerDetails.calculations.reduce((s, c) => s + (c.net_payable || 0), 0))}
                        </td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
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
                    registers.map((reg, i) => (
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
                              {reg.approval_history.map((h, idx) => (
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
    </div>
  );
}
