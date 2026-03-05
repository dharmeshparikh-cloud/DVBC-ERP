/**
 * HRManualEntry.js
 * 
 * CONSOLIDATED PAGE: Combines HRLeaveInput + HRAttendanceInput
 * 
 * Tab 1: Leave Input - Apply leave on behalf of employees, bulk credit
 * Tab 2: Attendance Input - Mark attendance, auto-validate, penalties
 * 
 * PRESERVES: All existing APIs, query keys, and business logic
 */

import React, { useState, useContext, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { 
  Calendar, Clock, Users, Search, RefreshCw, CheckCircle, XCircle,
  Plus, Edit2, Trash2, AlertTriangle, Save, Download, Upload,
  CalendarDays, Briefcase, DollarSign, FileText
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useFetch } from '../../hooks/useApi';

const API = process.env.REACT_APP_BACKEND_URL;

const LEAVE_TYPES = [
  { value: 'casual_leave', label: 'Casual Leave' },
  { value: 'sick_leave', label: 'Sick Leave' },
  { value: 'earned_leave', label: 'Earned Leave' },
  { value: 'compensatory_off', label: 'Compensatory Off' },
  { value: 'loss_of_pay', label: 'Loss of Pay' }
];

const ATTENDANCE_STATUS = [
  { value: 'present', label: 'Present', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'absent', label: 'Absent', color: 'bg-red-100 text-red-700' },
  { value: 'half_day', label: 'Half Day', color: 'bg-amber-100 text-amber-700' },
  { value: 'wfh', label: 'WFH', color: 'bg-blue-100 text-blue-700' },
  { value: 'on_leave', label: 'On Leave', color: 'bg-purple-100 text-purple-700' },
  { value: 'holiday', label: 'Holiday', color: 'bg-zinc-100 text-zinc-700' }
];

const HRManualEntry = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  
  // Determine initial tab from URL
  const getInitialTab = () => {
    const tab = searchParams.get('tab');
    if (tab) return tab;
    if (window.location.pathname.includes('hr-leave-input')) return 'leave';
    if (window.location.pathname.includes('hr-attendance-input')) return 'attendance';
    return 'leave';
  };
  
  const [activeTab, setActiveTab] = useState(getInitialTab());
  const [searchQuery, setSearchQuery] = useState('');
  
  // Leave tab states
  const [showLeaveDialog, setShowLeaveDialog] = useState(false);
  const [showBulkCreditDialog, setShowBulkCreditDialog] = useState(false);
  const [leaveForm, setLeaveForm] = useState({
    employee_id: '',
    leave_type: 'casual_leave',
    start_date: '',
    end_date: '',
    reason: ''
  });
  const [creditForm, setCreditForm] = useState({
    leave_type: 'earned_leave',
    days: 1,
    reason: '',
    employee_ids: []
  });
  
  // Attendance tab states
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showBulkAttendanceDialog, setShowBulkAttendanceDialog] = useState(false);
  const [showCustomPolicyDialog, setShowCustomPolicyDialog] = useState(false);
  const [bulkAttendance, setBulkAttendance] = useState({});
  const [customPolicyForm, setCustomPolicyForm] = useState({
    employee_id: '',
    check_in: '10:00',
    check_out: '19:00',
    grace_period_minutes: 30,
    grace_days_per_month: 3,
    reason: ''
  });
  
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  
  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canManage = isAdmin || isHR;

  // ==================== QUERIES ====================
  
  // Employees
  const { data: employeesData } = useFetch('/api/employees');
  const allEmployees = employeesData?.items || employeesData || [];
  
  // Leave requests (for leave tab)
  const { data: leaveRequestsData = [], isLoading: loadingLeaves, refetch: refetchLeaves } = useFetch('/api/leave-requests/all');
  
  // Attendance policy (for attendance tab)
  const { data: policyData } = useFetch('/api/attendance/policy');
  
  // Custom policies
  const { data: customPoliciesData, refetch: refetchCustomPolicies } = useFetch('/api/attendance/policy/custom');
  const customPolicies = customPoliciesData?.policies || [];
  
  // Monthly attendance data
  const { data: monthlyAttendance, isLoading: loadingAttendance, refetch: refetchAttendance } = useFetch(
    `/api/attendance/hr/employee-attendance-input/${selectedMonth}`,
    { enabled: activeTab === 'attendance' }
  );

  // ==================== MUTATIONS ====================
  
  // Apply leave for employee
  const applyLeaveMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/attendance/hr/apply-leave-for-employee`, {
        employee_id: leaveForm.employee_id,
        leave_type: leaveForm.leave_type,
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        reason: leaveForm.reason
      }, { headers });
    },
    onSuccess: () => {
      toast.success('Leave applied successfully');
      setShowLeaveDialog(false);
      setLeaveForm({ employee_id: '', leave_type: 'casual_leave', start_date: '', end_date: '', reason: '' });
      refetchLeaves();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to apply leave'),
  });

  // Bulk leave credit
  const bulkCreditMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/attendance/hr/bulk-leave-credit`, creditForm, { headers });
    },
    onSuccess: () => {
      toast.success('Leave credited successfully');
      setShowBulkCreditDialog(false);
      setCreditForm({ leave_type: 'earned_leave', days: 1, reason: '', employee_ids: [] });
      queryClient.invalidateQueries({ queryKey: ['/api/employees'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to credit leave'),
  });

  // Approve leave (RM approval)
  const approveLeaveeMutation = useMutation({
    mutationFn: async (leaveId) => {
      return axios.post(`${API}/api/leave-requests/${leaveId}/rm-approve`, {
        action: 'approve',
        remarks: 'Approved by HR'
      }, { headers });
    },
    onSuccess: () => {
      toast.success('Leave approved');
      refetchLeaves();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to approve'),
  });

  // Auto-validate attendance
  const autoValidateMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/attendance/auto-validate`, { month: selectedMonth }, { headers });
    },
    onSuccess: (data) => {
      toast.success(`Validated ${data.data?.validated_count || 0} records`);
      refetchAttendance();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Validation failed'),
  });

  // Apply penalties
  const applyPenaltiesMutation = useMutation({
    mutationFn: async (penalties) => {
      return axios.post(`${API}/api/attendance/apply-penalties`, { month: selectedMonth, penalties }, { headers });
    },
    onSuccess: () => {
      toast.success('Penalties applied');
      refetchAttendance();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to apply penalties'),
  });

  // Bulk mark attendance
  const bulkMarkAttendanceMutation = useMutation({
    mutationFn: async () => {
      const records = Object.entries(bulkAttendance).map(([empId, status]) => ({
        employee_id: empId,
        status
      }));
      return axios.post(`${API}/api/attendance/hr/mark-attendance-bulk`, { date: selectedDate, records }, { headers });
    },
    onSuccess: () => {
      toast.success('Attendance marked');
      setShowBulkAttendanceDialog(false);
      setBulkAttendance({});
      refetchAttendance();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to mark attendance'),
  });

  // Save custom policy
  const saveCustomPolicyMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/attendance/policy/custom`, customPolicyForm, { headers });
    },
    onSuccess: () => {
      toast.success('Custom policy saved');
      setShowCustomPolicyDialog(false);
      setCustomPolicyForm({ employee_id: '', check_in: '10:00', check_out: '19:00', grace_period_minutes: 30, grace_days_per_month: 3, reason: '' });
      refetchCustomPolicies();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to save policy'),
  });

  // Delete custom policy
  const deleteCustomPolicyMutation = useMutation({
    mutationFn: async (employeeId) => {
      return axios.delete(`${API}/api/attendance/policy/custom/${employeeId}`, { headers });
    },
    onSuccess: () => {
      toast.success('Custom policy removed');
      refetchCustomPolicies();
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to remove policy'),
  });

  // Filter employees
  const filteredEmployees = allEmployees.filter(emp => {
    if (!searchQuery) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchLower) ||
      emp.employee_id?.toLowerCase().includes(searchLower)
    );
  });

  // Filter pending leaves
  const pendingLeaves = leaveRequestsData.filter(l => l.status === 'pending' || l.rm_status === 'pending');

  if (!canManage) {
    return (
      <div className="p-6">
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-red-700">Access Denied</h2>
            <p className="text-red-600 mt-2">Only HR can access this page.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="hr-manual-entry">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            HR Manual Entry
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Manually input leave and attendance records for employees
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              placeholder="Search employees..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-[250px]"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="leave" data-testid="tab-leave">
            <Calendar className="w-4 h-4 mr-2" />
            Leave Input
          </TabsTrigger>
          <TabsTrigger value="attendance" data-testid="tab-attendance">
            <Clock className="w-4 h-4 mr-2" />
            Attendance Input
          </TabsTrigger>
        </TabsList>

        {/* ==================== LEAVE TAB ==================== */}
        <TabsContent value="leave" className="mt-6 space-y-6">
          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button onClick={() => setShowLeaveDialog(true)}>
              <Plus className="w-4 h-4 mr-2" /> Apply Leave
            </Button>
            <Button variant="outline" onClick={() => setShowBulkCreditDialog(true)}>
              <Upload className="w-4 h-4 mr-2" /> Bulk Credit
            </Button>
            <Button variant="outline" onClick={() => refetchLeaves()}>
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
          </div>

          {/* Pending Leaves */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-500" />
                Pending Leave Requests
                {pendingLeaves.length > 0 && (
                  <Badge className="bg-amber-500">{pendingLeaves.length}</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingLeaves ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-zinc-400" />
                </div>
              ) : pendingLeaves.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 text-emerald-300" />
                  <p>No pending leave requests</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingLeaves.slice(0, 10).map(leave => (
                      <TableRow key={leave.id || leave._id}>
                        <TableCell>
                          <div className="font-medium">{leave.employee_name || leave.employee_id}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {leave.leave_type?.replace(/_/g, ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">{leave.reason}</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            onClick={() => approveLeaveeMutation.mutate(leave.id || leave._id)}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" /> Approve
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ==================== ATTENDANCE TAB ==================== */}
        <TabsContent value="attendance" className="mt-6 space-y-6">
          {/* Month Selector & Actions */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Label>Month:</Label>
              <Input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="w-[180px]"
              />
            </div>
            <div className="flex items-center gap-2">
              <Label>Date:</Label>
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-[180px]"
              />
            </div>
            <div className="flex gap-2 ml-auto">
              <Button onClick={() => setShowBulkAttendanceDialog(true)}>
                <Plus className="w-4 h-4 mr-2" /> Bulk Mark
              </Button>
              <Button variant="outline" onClick={() => autoValidateMutation.mutate()}>
                <CheckCircle className="w-4 h-4 mr-2" /> Auto-Validate
              </Button>
              <Button variant="outline" onClick={() => setShowCustomPolicyDialog(true)}>
                <Briefcase className="w-4 h-4 mr-2" /> Custom Policy
              </Button>
            </div>
          </div>

          {/* Monthly Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CalendarDays className="w-5 h-5 text-blue-500" />
                Attendance Summary - {selectedMonth}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingAttendance ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-zinc-400" />
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                  <div className="text-center p-4 bg-emerald-50 rounded-lg">
                    <div className="text-2xl font-bold text-emerald-600">
                      {monthlyAttendance?.summary?.present || 0}
                    </div>
                    <div className="text-xs text-emerald-600">Present</div>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">
                      {monthlyAttendance?.summary?.absent || 0}
                    </div>
                    <div className="text-xs text-red-600">Absent</div>
                  </div>
                  <div className="text-center p-4 bg-amber-50 rounded-lg">
                    <div className="text-2xl font-bold text-amber-600">
                      {monthlyAttendance?.summary?.late || 0}
                    </div>
                    <div className="text-xs text-amber-600">Late</div>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {monthlyAttendance?.summary?.wfh || 0}
                    </div>
                    <div className="text-xs text-blue-600">WFH</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {monthlyAttendance?.summary?.on_leave || 0}
                    </div>
                    <div className="text-xs text-purple-600">On Leave</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Custom Policies */}
          {customPolicies.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Briefcase className="w-4 h-4" />
                  Custom Attendance Policies
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {customPolicies.map(policy => {
                    const emp = allEmployees.find(e => e.id === policy.employee_id || e.employee_id === policy.employee_id);
                    return (
                      <div key={policy.employee_id} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg">
                        <div>
                          <div className="font-medium text-sm">{emp?.first_name} {emp?.last_name || policy.employee_id}</div>
                          <div className="text-xs text-zinc-500">
                            {policy.check_in} - {policy.check_out} | Grace: {policy.grace_period_minutes}min
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteCustomPolicyMutation.mutate(policy.employee_id)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* ==================== DIALOGS ==================== */}
      
      {/* Apply Leave Dialog */}
      <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Apply Leave for Employee</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Employee</Label>
              <Select value={leaveForm.employee_id} onValueChange={(v) => setLeaveForm(p => ({ ...p, employee_id: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {filteredEmployees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.employee_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Leave Type</Label>
              <Select value={leaveForm.leave_type} onValueChange={(v) => setLeaveForm(p => ({ ...p, leave_type: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LEAVE_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={leaveForm.start_date}
                  onChange={(e) => setLeaveForm(p => ({ ...p, start_date: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>End Date</Label>
                <Input
                  type="date"
                  value={leaveForm.end_date}
                  onChange={(e) => setLeaveForm(p => ({ ...p, end_date: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                value={leaveForm.reason}
                onChange={(e) => setLeaveForm(p => ({ ...p, reason: e.target.value }))}
                placeholder="Reason for leave..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLeaveDialog(false)}>Cancel</Button>
            <Button onClick={() => applyLeaveMutation.mutate()}>Apply Leave</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Credit Dialog */}
      <Dialog open={showBulkCreditDialog} onOpenChange={setShowBulkCreditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Credit Leave</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Leave Type</Label>
              <Select value={creditForm.leave_type} onValueChange={(v) => setCreditForm(p => ({ ...p, leave_type: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LEAVE_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Days to Credit</Label>
              <Input
                type="number"
                min="0.5"
                step="0.5"
                value={creditForm.days}
                onChange={(e) => setCreditForm(p => ({ ...p, days: parseFloat(e.target.value) }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                value={creditForm.reason}
                onChange={(e) => setCreditForm(p => ({ ...p, reason: e.target.value }))}
                placeholder="Reason for credit..."
              />
            </div>
            <div className="space-y-2">
              <Label>Select Employees (or leave empty for all)</Label>
              <div className="max-h-[200px] overflow-y-auto border rounded-md p-2">
                {filteredEmployees.map(emp => (
                  <label key={emp.id} className="flex items-center gap-2 p-1 hover:bg-zinc-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={creditForm.employee_ids.includes(emp.id)}
                      onChange={(e) => {
                        setCreditForm(p => ({
                          ...p,
                          employee_ids: e.target.checked
                            ? [...p.employee_ids, emp.id]
                            : p.employee_ids.filter(id => id !== emp.id)
                        }));
                      }}
                    />
                    <span className="text-sm">{emp.first_name} {emp.last_name}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkCreditDialog(false)}>Cancel</Button>
            <Button onClick={() => bulkCreditMutation.mutate()}>Credit Leave</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Attendance Dialog */}
      <Dialog open={showBulkAttendanceDialog} onOpenChange={setShowBulkAttendanceDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Bulk Mark Attendance - {selectedDate}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[400px] overflow-y-auto py-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEmployees.slice(0, 50).map(emp => (
                  <TableRow key={emp.id}>
                    <TableCell>
                      <div className="font-medium text-sm">{emp.first_name} {emp.last_name}</div>
                      <div className="text-xs text-zinc-500">{emp.employee_id}</div>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={bulkAttendance[emp.id] || ''}
                        onValueChange={(v) => setBulkAttendance(p => ({ ...p, [emp.id]: v }))}
                      >
                        <SelectTrigger className="w-[150px]">
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          {ATTENDANCE_STATUS.map(status => (
                            <SelectItem key={status.value} value={status.value}>
                              {status.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkAttendanceDialog(false)}>Cancel</Button>
            <Button onClick={() => bulkMarkAttendanceMutation.mutate()}>Save Attendance</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Custom Policy Dialog */}
      <Dialog open={showCustomPolicyDialog} onOpenChange={setShowCustomPolicyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Custom Attendance Policy</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Employee</Label>
              <Select value={customPolicyForm.employee_id} onValueChange={(v) => setCustomPolicyForm(p => ({ ...p, employee_id: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {filteredEmployees.filter(emp => !customPolicies.some(p => p.employee_id === emp.id)).map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Check-in Time</Label>
                <Input
                  type="time"
                  value={customPolicyForm.check_in}
                  onChange={(e) => setCustomPolicyForm(p => ({ ...p, check_in: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Check-out Time</Label>
                <Input
                  type="time"
                  value={customPolicyForm.check_out}
                  onChange={(e) => setCustomPolicyForm(p => ({ ...p, check_out: e.target.value }))}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Grace Period (mins)</Label>
                <Input
                  type="number"
                  value={customPolicyForm.grace_period_minutes}
                  onChange={(e) => setCustomPolicyForm(p => ({ ...p, grace_period_minutes: parseInt(e.target.value) }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Grace Days/Month</Label>
                <Input
                  type="number"
                  value={customPolicyForm.grace_days_per_month}
                  onChange={(e) => setCustomPolicyForm(p => ({ ...p, grace_days_per_month: parseInt(e.target.value) }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                value={customPolicyForm.reason}
                onChange={(e) => setCustomPolicyForm(p => ({ ...p, reason: e.target.value }))}
                placeholder="Reason for custom policy..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCustomPolicyDialog(false)}>Cancel</Button>
            <Button onClick={() => saveCustomPolicyMutation.mutate()}>Save Policy</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRManualEntry;
