import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import { Separator } from '../components/ui/separator';
import {
  UserMinus, Calculator, CheckCircle, XCircle, Clock, User, Calendar,
  Building2, Briefcase, FileText, Loader2, ChevronRight, ChevronLeft,
  IndianRupee, AlertTriangle, Banknote, Wallet, CreditCard, BadgeCheck,
  ArrowRight, Gift, CalendarDays
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../utils/roles';

// Wizard Steps
const WIZARD_STEPS = [
  { id: 1, title: 'Select Employee', icon: User, description: 'Choose employee for F&F' },
  { id: 2, title: 'Exit Details', icon: CalendarDays, description: 'Configure exit parameters' },
  { id: 3, title: 'Clearance Status', icon: BadgeCheck, description: 'Review department clearances' },
  { id: 4, title: 'Settlement Calculation', icon: Calculator, description: 'Calculate F&F amounts' },
  { id: 5, title: 'Approval & Complete', icon: CheckCircle, description: 'Approve and finalize' }
];

const ExitSettlement = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const isDark = theme === 'dark';
  
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);
  
  // Wizard state
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [exitData, setExitData] = useState({
    exit_type: 'resignation',
    last_working_date: '',
    notice_period_days: 30,
    days_served: 0,
    reason: ''
  });
  const [activeExit, setActiveExit] = useState(null);
  const [settlement, setSettlement] = useState(null);
  
  // Dialog states
  const [showClearanceDialog, setShowClearanceDialog] = useState(false);
  const [clearanceDept, setClearanceDept] = useState('');
  const [clearanceRemarks, setClearanceRemarks] = useState('');
  
  // Fetch employees
  const { data: employees = [] } = useQuery({
    queryKey: ['employees-for-fnf'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return (res.data || []).filter(e => e.is_active !== false);
    },
    staleTime: 5 * 60 * 1000
  });
  
  // Fetch existing exits
  const { data: exits = [], isLoading: loadingExits } = useQuery({
    queryKey: ['exit-settlements'],
    queryFn: async () => {
      const res = await axios.get(`${API}/exit-settlement/list`);
      return res.data || [];
    },
    staleTime: 60 * 1000
  });
  
  // Mutations
  const initiateMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/exit-settlement/initiate`, data);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('Exit process initiated');
      setActiveExit(data.exit_record);
      queryClient.invalidateQueries(['exit-settlements']);
      setCurrentStep(3);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to initiate exit')
  });
  
  const clearanceMutation = useMutation({
    mutationFn: async ({ exitId, department, status, remarks }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/clearance`, {
        department,
        status,
        remarks
      });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`${clearanceDept.toUpperCase()} clearance updated`);
      // Refresh active exit
      fetchExitDetails(activeExit.id);
      setShowClearanceDialog(false);
      setClearanceRemarks('');
      if (data.all_cleared) {
        toast.success('All clearances complete! Ready for settlement calculation.');
      }
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update clearance')
  });
  
  const calculateMutation = useMutation({
    mutationFn: async (exitId) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/calculate-settlement`);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('Settlement calculated');
      setSettlement(data.settlement);
      setCurrentStep(5);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to calculate settlement')
  });
  
  const approveMutation = useMutation({
    mutationFn: async ({ exitId, approved, remarks }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/approve-settlement`, {
        approved,
        remarks
      });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries(['exit-settlements']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Approval failed')
  });
  
  const completeMutation = useMutation({
    mutationFn: async ({ exitId, payment_reference, payment_date }) => {
      const res = await axios.post(`${API}/exit-settlement/${exitId}/complete`, {
        payment_reference,
        payment_date
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success('Settlement completed. Employee marked as inactive.');
      queryClient.invalidateQueries(['exit-settlements']);
      queryClient.invalidateQueries(['employees-for-fnf']);
      resetWizard();
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to complete')
  });
  
  // Fetch exit details
  const fetchExitDetails = async (exitId) => {
    try {
      const res = await axios.get(`${API}/exit-settlement/${exitId}`);
      setActiveExit(res.data);
    } catch (err) {
      toast.error('Failed to fetch exit details');
    }
  };
  
  // Reset wizard
  const resetWizard = () => {
    setCurrentStep(1);
    setSelectedEmployee(null);
    setActiveExit(null);
    setSettlement(null);
    setExitData({
      exit_type: 'resignation',
      last_working_date: '',
      notice_period_days: 30,
      days_served: 0,
      reason: ''
    });
  };
  
  // Continue existing exit
  const continueExit = (exit) => {
    setActiveExit(exit);
    setSelectedEmployee({ id: exit.employee_id, name: exit.employee_name });
    
    // Determine which step to show
    if (exit.status === 'initiated') {
      setCurrentStep(3); // Clearance
    } else if (exit.status === 'clearance_complete' || exit.status === 'settlement_calculated') {
      setCurrentStep(4); // Calculate
      if (exit.settlement_details) {
        setSettlement(exit.settlement_details);
        setCurrentStep(5);
      }
    } else if (exit.status === 'approved') {
      setSettlement(exit.settlement_details);
      setCurrentStep(5);
    }
  };
  
  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };
  
  // Get status badge
  const getStatusBadge = (status) => {
    const styles = {
      initiated: { color: 'bg-amber-100 text-amber-700', label: 'Clearance Pending' },
      clearance_complete: { color: 'bg-blue-100 text-blue-700', label: 'Ready for Calculation' },
      settlement_calculated: { color: 'bg-purple-100 text-purple-700', label: 'Pending Approval' },
      approved: { color: 'bg-green-100 text-green-700', label: 'Approved' },
      completed: { color: 'bg-zinc-100 text-zinc-700', label: 'Completed' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected' }
    };
    const s = styles[status] || styles.initiated;
    return <Badge className={s.color}>{s.label}</Badge>;
  };
  
  // Check if all clearances done
  const allClearancesDone = activeExit?.clearance && Object.values(activeExit.clearance).every(
    c => c.status === 'cleared'
  );

  if (!isHR && !isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-500">Access denied. HR or Admin role required.</p>
      </div>
    );
  }

  return (
    <div data-testid="exit-settlement-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <UserMinus className="w-6 h-6 text-orange-500" />
            Exit Settlement (F&F)
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Full & Final settlement wizard for employee exits
          </p>
        </div>
        
        {activeExit && (
          <Button variant="outline" onClick={resetWizard}>
            Start New F&F
          </Button>
        )}
      </div>
      
      {/* Existing Exits Quick Access */}
      {!activeExit && exits.filter(e => e.status !== 'completed').length > 0 && (
        <Card className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Continue Pending F&F</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {exits.filter(e => e.status !== 'completed').slice(0, 5).map(exit => (
                <button
                  key={exit.id}
                  onClick={() => continueExit(exit)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                    isDark 
                      ? 'border-zinc-700 hover:bg-zinc-700' 
                      : 'border-zinc-200 hover:bg-zinc-100'
                  }`}
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm font-medium">{exit.employee_name}</span>
                  {getStatusBadge(exit.status)}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Wizard Steps Indicator */}
      <div className="flex items-center justify-between">
        {WIZARD_STEPS.map((step, index) => {
          const StepIcon = step.icon;
          const isActive = currentStep === step.id;
          const isCompleted = currentStep > step.id;
          
          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center">
                <div 
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                    isCompleted 
                      ? 'bg-green-500 text-white' 
                      : isActive 
                        ? 'bg-orange-500 text-white' 
                        : isDark 
                          ? 'bg-zinc-800 text-zinc-500' 
                          : 'bg-zinc-100 text-zinc-400'
                  }`}
                >
                  {isCompleted ? <CheckCircle className="w-6 h-6" /> : <StepIcon className="w-5 h-5" />}
                </div>
                <p className={`text-xs mt-2 text-center max-w-[80px] ${
                  isActive ? (isDark ? 'text-orange-400' : 'text-orange-600') : ''
                }`}>
                  {step.title}
                </p>
              </div>
              {index < WIZARD_STEPS.length - 1 && (
                <div className={`flex-1 h-1 mx-2 rounded ${
                  isCompleted ? 'bg-green-500' : isDark ? 'bg-zinc-700' : 'bg-zinc-200'
                }`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
      
      {/* Wizard Content */}
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : ''}>
        <CardContent className="pt-6">
          
          {/* STEP 1: Select Employee */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Select Employee for F&F Settlement</h3>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Choose the employee whose exit needs to be processed
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Search Employee</Label>
                  <Select 
                    value={selectedEmployee?.id || ''} 
                    onValueChange={(id) => {
                      const emp = employees.find(e => e.id === id);
                      setSelectedEmployee(emp);
                    }}
                  >
                    <SelectTrigger className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
                      <SelectValue placeholder="Select employee..." />
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
              </div>
              
              {/* Selected Employee Preview */}
              {selectedEmployee && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-orange-100 flex items-center justify-center">
                      <User className="w-8 h-8 text-orange-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-lg">
                        {selectedEmployee.first_name} {selectedEmployee.last_name}
                      </h4>
                      <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {selectedEmployee.employee_id} • {selectedEmployee.department} • {selectedEmployee.designation}
                      </p>
                      <div className="flex gap-4 mt-2 text-xs">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Joined: {selectedEmployee.joining_date ? new Date(selectedEmployee.joining_date).toLocaleDateString() : 'N/A'}
                        </span>
                        <span className="flex items-center gap-1">
                          <IndianRupee className="w-3 h-3" />
                          CTC: {formatCurrency(selectedEmployee.ctc || 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="flex justify-end">
                <Button
                  onClick={() => setCurrentStep(2)}
                  disabled={!selectedEmployee}
                  className="bg-orange-600 hover:bg-orange-700"
                >
                  Next: Exit Details
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}
          
          {/* STEP 2: Exit Details */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Configure Exit Details</h3>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Set up the exit parameters for {selectedEmployee?.first_name} {selectedEmployee?.last_name}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Exit Type *</Label>
                  <Select 
                    value={exitData.exit_type} 
                    onValueChange={(v) => setExitData({...exitData, exit_type: v})}
                  >
                    <SelectTrigger className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="resignation">Resignation</SelectItem>
                      <SelectItem value="termination">Termination</SelectItem>
                      <SelectItem value="retirement">Retirement</SelectItem>
                      <SelectItem value="death">Death</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label>Last Working Date *</Label>
                  <Input
                    type="date"
                    value={exitData.last_working_date}
                    onChange={(e) => setExitData({...exitData, last_working_date: e.target.value})}
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                  />
                </div>
                
                <div>
                  <Label>Notice Period (Days)</Label>
                  <Input
                    type="number"
                    value={exitData.notice_period_days}
                    onChange={(e) => setExitData({...exitData, notice_period_days: parseInt(e.target.value) || 0})}
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                    min={0}
                  />
                </div>
                
                <div>
                  <Label>Days Served in Notice</Label>
                  <Input
                    type="number"
                    value={exitData.days_served}
                    onChange={(e) => setExitData({...exitData, days_served: parseInt(e.target.value) || 0})}
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                    min={0}
                    max={exitData.notice_period_days}
                  />
                  {exitData.days_served < exitData.notice_period_days && (
                    <p className="text-xs text-amber-500 mt-1">
                      {exitData.notice_period_days - exitData.days_served} days shortfall - will be recovered
                    </p>
                  )}
                </div>
                
                <div className="col-span-2">
                  <Label>Reason for Exit</Label>
                  <Textarea
                    value={exitData.reason}
                    onChange={(e) => setExitData({...exitData, reason: e.target.value})}
                    placeholder="Enter reason for exit..."
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
                    rows={3}
                  />
                </div>
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(1)}>
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => {
                    if (!exitData.last_working_date) {
                      toast.error('Please enter last working date');
                      return;
                    }
                    initiateMutation.mutate({
                      employee_id: selectedEmployee.id,
                      ...exitData
                    });
                  }}
                  disabled={initiateMutation.isPending || !exitData.last_working_date}
                  className="bg-orange-600 hover:bg-orange-700"
                >
                  {initiateMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Initiate Exit
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}
          
          {/* STEP 3: Clearance Status */}
          {currentStep === 3 && activeExit && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Department Clearances</h3>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Update clearance status for {activeExit.employee_name}
                </p>
              </div>
              
              <div className="grid grid-cols-5 gap-4">
                {Object.entries(activeExit.clearance || {}).map(([dept, data]) => {
                  const isCleared = data.status === 'cleared';
                  const isBlocked = data.status === 'blocked';
                  
                  return (
                    <div 
                      key={dept}
                      className={`p-4 rounded-lg border text-center ${
                        isCleared 
                          ? 'bg-green-50 border-green-200' 
                          : isBlocked 
                            ? 'bg-red-50 border-red-200'
                            : isDark 
                              ? 'bg-zinc-800 border-zinc-700' 
                              : 'bg-zinc-50 border-zinc-200'
                      }`}
                    >
                      <div className={`w-10 h-10 mx-auto rounded-full flex items-center justify-center mb-2 ${
                        isCleared 
                          ? 'bg-green-100' 
                          : isBlocked 
                            ? 'bg-red-100'
                            : 'bg-amber-100'
                      }`}>
                        {isCleared ? (
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        ) : isBlocked ? (
                          <XCircle className="w-5 h-5 text-red-600" />
                        ) : (
                          <Clock className="w-5 h-5 text-amber-600" />
                        )}
                      </div>
                      <p className="font-medium text-sm capitalize">{dept}</p>
                      <p className={`text-xs mt-1 ${
                        isCleared ? 'text-green-600' : isBlocked ? 'text-red-600' : 'text-amber-600'
                      }`}>
                        {isCleared ? 'Cleared' : isBlocked ? 'Blocked' : 'Pending'}
                      </p>
                      {!isCleared && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-2 text-xs"
                          onClick={() => {
                            setClearanceDept(dept);
                            setShowClearanceDialog(true);
                          }}
                        >
                          Update
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
              
              {/* Clearance Info */}
              <div className={`p-4 rounded-lg ${
                allClearancesDone 
                  ? 'bg-green-50 border border-green-200' 
                  : 'bg-amber-50 border border-amber-200'
              }`}>
                {allClearancesDone ? (
                  <p className="text-green-700 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    All clearances complete! Ready to calculate settlement.
                  </p>
                ) : (
                  <p className="text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    Complete all department clearances before calculating settlement.
                  </p>
                )}
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(2)}>
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => setCurrentStep(4)}
                  disabled={!allClearancesDone}
                  className="bg-orange-600 hover:bg-orange-700"
                >
                  Next: Calculate Settlement
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}
          
          {/* STEP 4: Settlement Calculation */}
          {currentStep === 4 && activeExit && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Calculate F&F Settlement</h3>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Calculate full and final settlement for {activeExit.employee_name}
                </p>
              </div>
              
              {/* Employee Summary */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>Employee</p>
                    <p className="font-bold">{activeExit.employee_name}</p>
                  </div>
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>Exit Type</p>
                    <p className="font-bold capitalize">{activeExit.exit_type}</p>
                  </div>
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>Last Working Day</p>
                    <p className="font-bold">{activeExit.last_working_date ? new Date(activeExit.last_working_date).toLocaleDateString() : 'N/A'}</p>
                  </div>
                  <div>
                    <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>Notice Period</p>
                    <p className="font-bold">{activeExit.notice_period_days} days ({activeExit.days_served} served)</p>
                  </div>
                </div>
              </div>
              
              {/* Settlement Components Preview */}
              <div className={`p-4 rounded-lg border-l-4 border-blue-500 ${isDark ? 'bg-blue-900/20' : 'bg-blue-50'}`}>
                <p className={`text-sm font-medium ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
                  The following will be calculated:
                </p>
                <ul className={`text-xs mt-2 space-y-1 ${isDark ? 'text-blue-300' : 'text-blue-600'}`}>
                  <li>• Gratuity (if eligible - 5+ years service)</li>
                  <li>• Leave Encashment (earned/privilege leaves)</li>
                  <li>• Notice Period Recovery/Payment</li>
                  <li>• Pending Expense Reimbursements</li>
                  <li>• Pending Loan/Advance Recovery</li>
                  <li>• Final Salary Settlement</li>
                </ul>
              </div>
              
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(3)}>
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => calculateMutation.mutate(activeExit.id)}
                  disabled={calculateMutation.isPending}
                  className="bg-orange-600 hover:bg-orange-700"
                >
                  {calculateMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Calculator className="w-4 h-4 mr-2" />
                  Calculate Settlement
                </Button>
              </div>
            </div>
          )}
          
          {/* STEP 5: Approval & Complete */}
          {currentStep === 5 && settlement && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">Settlement Summary & Approval</h3>
                <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Review and approve the settlement for {settlement.employee_name}
                </p>
              </div>
              
              {/* Tenure & Salary Info */}
              <div className={`grid grid-cols-3 gap-4 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Tenure</p>
                  <p className="font-bold">{Math.floor(settlement.tenure?.years || 0)} years {settlement.tenure?.months || 0} months</p>
                </div>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Monthly Gross</p>
                  <p className="font-bold">{formatCurrency(settlement.salary_details?.gross_monthly)}</p>
                </div>
                <div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Annual CTC</p>
                  <p className="font-bold">{formatCurrency(settlement.salary_details?.ctc_annual)}</p>
                </div>
              </div>
              
              {/* Payable Components */}
              <div className={`p-4 rounded-lg border border-green-200 ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}>
                <h4 className="font-medium text-green-700 mb-3 flex items-center gap-2">
                  <Banknote className="w-5 h-5" />
                  Payable to Employee
                </h4>
                <div className="space-y-2">
                  {settlement.payable_components?.gratuity?.eligible && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Gift className="w-4 h-4 text-green-600" />
                        Gratuity ({settlement.payable_components.gratuity.years_eligible} years)
                      </span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.gratuity.amount)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.leave_encashment?.amount > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-green-600" />
                        Leave Encashment ({settlement.payable_components.leave_encashment.days_encashed} days)
                      </span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.leave_encashment.amount)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.expense_reimbursements?.total > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Wallet className="w-4 h-4 text-green-600" />
                        Expense Reimbursements
                      </span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.expense_reimbursements.total)}</span>
                    </div>
                  )}
                  {settlement.payable_components?.notice_period_payment && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-green-600" />
                        Notice Period Payment
                      </span>
                      <span className="font-bold text-green-600">{formatCurrency(settlement.payable_components.notice_period_payment.amount)}</span>
                    </div>
                  )}
                  <Separator className="my-2" />
                  <div className="flex justify-between font-bold">
                    <span>Total Payable</span>
                    <span className="text-green-600">{formatCurrency(settlement.summary?.total_payable)}</span>
                  </div>
                </div>
              </div>
              
              {/* Recovery Components */}
              <div className={`p-4 rounded-lg border border-red-200 ${isDark ? 'bg-red-900/20' : 'bg-red-50'}`}>
                <h4 className="font-medium text-red-700 mb-3 flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  Recovery from Employee
                </h4>
                <div className="space-y-2">
                  {settlement.recovery_components?.notice_period_recovery && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-red-600" />
                        Notice Period Shortfall ({settlement.recovery_components.notice_period_recovery.shortfall_days} days)
                      </span>
                      <span className="font-bold text-red-600">-{formatCurrency(settlement.recovery_components.notice_period_recovery.amount)}</span>
                    </div>
                  )}
                  {settlement.recovery_components?.loan_recovery?.total > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-red-600" />
                        Pending Loans ({settlement.recovery_components.loan_recovery.loans?.length || 0} loans)
                      </span>
                      <span className="font-bold text-red-600">-{formatCurrency(settlement.recovery_components.loan_recovery.total)}</span>
                    </div>
                  )}
                  <Separator className="my-2" />
                  <div className="flex justify-between font-bold">
                    <span>Total Recovery</span>
                    <span className="text-red-600">-{formatCurrency(settlement.summary?.total_recovery)}</span>
                  </div>
                </div>
              </div>
              
              {/* Net Settlement */}
              <div className={`p-6 rounded-lg text-center ${
                settlement.summary?.net_settlement >= 0 
                  ? 'bg-blue-100 border-2 border-blue-300' 
                  : 'bg-amber-100 border-2 border-amber-300'
              }`}>
                <p className="text-sm font-medium text-zinc-600 mb-1">NET SETTLEMENT AMOUNT</p>
                <p className={`text-4xl font-bold ${
                  settlement.summary?.net_settlement >= 0 ? 'text-blue-600' : 'text-amber-600'
                }`}>
                  {formatCurrency(settlement.summary?.net_settlement)}
                </p>
                <p className="text-xs mt-2 text-zinc-500">
                  {settlement.summary?.net_settlement >= 0 
                    ? 'Amount payable to employee' 
                    : 'Amount recoverable from employee'}
                </p>
              </div>
              
              {/* Actions */}
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(4)}>
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Recalculate
                </Button>
                
                {activeExit?.status === 'settlement_calculated' && isAdmin && (
                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      onClick={() => approveMutation.mutate({ 
                        exitId: activeExit.id, 
                        approved: false, 
                        remarks: 'Rejected' 
                      })}
                      disabled={approveMutation.isPending}
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Reject
                    </Button>
                    <Button
                      onClick={() => approveMutation.mutate({ 
                        exitId: activeExit.id, 
                        approved: true, 
                        remarks: 'Approved' 
                      })}
                      disabled={approveMutation.isPending}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {approveMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Approve Settlement
                    </Button>
                  </div>
                )}
                
                {activeExit?.status === 'approved' && (
                  <Button
                    onClick={() => {
                      const paymentRef = prompt('Enter payment reference (e.g., NEFT123456):');
                      if (paymentRef) {
                        completeMutation.mutate({
                          exitId: activeExit.id,
                          payment_reference: paymentRef,
                          payment_date: new Date().toISOString().split('T')[0]
                        });
                      }
                    }}
                    disabled={completeMutation.isPending}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {completeMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    <Banknote className="w-4 h-4 mr-2" />
                    Mark as Paid & Complete
                  </Button>
                )}
              </div>
            </div>
          )}
          
        </CardContent>
      </Card>
      
      {/* Clearance Update Dialog */}
      <Dialog open={showClearanceDialog} onOpenChange={setShowClearanceDialog}>
        <DialogContent className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}>
          <DialogHeader>
            <DialogTitle className="capitalize">Update {clearanceDept} Clearance</DialogTitle>
            <DialogDescription>
              Mark clearance status for {activeExit?.employee_name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label>Remarks (Optional)</Label>
              <Textarea
                value={clearanceRemarks}
                onChange={(e) => setClearanceRemarks(e.target.value)}
                placeholder="Add any remarks..."
                className={`mt-1 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => setShowClearanceDialog(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => clearanceMutation.mutate({
                exitId: activeExit.id,
                department: clearanceDept,
                status: 'blocked',
                remarks: clearanceRemarks
              })}
              disabled={clearanceMutation.isPending}
            >
              <XCircle className="w-4 h-4 mr-2" />
              Block
            </Button>
            <Button
              onClick={() => clearanceMutation.mutate({
                exitId: activeExit.id,
                department: clearanceDept,
                status: 'cleared',
                remarks: clearanceRemarks
              })}
              disabled={clearanceMutation.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {clearanceMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              <CheckCircle className="w-4 h-4 mr-2" />
              Mark Cleared
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ExitSettlement;
