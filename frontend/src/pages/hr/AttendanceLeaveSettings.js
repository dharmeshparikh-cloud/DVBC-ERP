import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Clock, Calendar, Settings, Save, RefreshCw, AlertTriangle,
  Sun, Moon, Coffee, DollarSign, Users, User,
  Plus, Edit2, Trash2, Info, Badge
} from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const AttendanceLeaveSettings = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  
  // Attendance Policy Settings
  const [attendancePolicy, setAttendancePolicy] = useState({
    working_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    non_consulting: {
      check_in: '10:00',
      check_out: '19:00'
    },
    consulting: {
      check_in: '10:30',
      check_out: '19:30'
    },
    grace_period_minutes: 30,
    grace_days_per_month: 3,
    late_penalty_amount: 100
  });

  // Consulting Roles
  const [consultingRoles, setConsultingRoles] = useState([]);
  
  // Modal state for adding/editing custom policy
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [policyForm, setPolicyForm] = useState({
    employee_id: '',
    check_in: '10:00',
    check_out: '19:00',
    grace_period_minutes: 30,
    grace_days_per_month: 3,
    reason: ''
  });

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  // Query: Fetch attendance policy
  const { data: attendancePolicyData, isLoading: loadingPolicy, refetch: refetchAttendancePolicy } = useFetch('/api/attendance/policy');

  // Query: Fetch consulting employees
  const { data: consultingData } = useFetch('/api/attendance/consulting-employees');
  const consultingEmployees = consultingData?.employees || [];
  const consultingRoleCounts = consultingData?.role_counts || {};

  // Query: Fetch custom policies
  const { data: customPoliciesData, refetch: refetchCustomPolicies } = useFetch('/api/attendance/policy/custom');
  const customPolicies = customPoliciesData?.policies || [];

  // Query: Fetch all employees
  const { data: allEmployeesData } = useFetch('/api/employees');
  // API returns { items: [], pagination: {} } so extract items array
  const allEmployees = Array.isArray(allEmployeesData) ? allEmployeesData : (allEmployeesData?.items || []);

  const loading = loadingPolicy;

  // Update local state when data is fetched
  useEffect(() => {
    if (attendancePolicyData?.policy) {
      setAttendancePolicy(attendancePolicyData.policy);
    }
    if (attendancePolicyData?.consulting_roles) {
      setConsultingRoles(attendancePolicyData.consulting_roles);
    }
  }, [attendancePolicyData]);

  useEffect(() => {
    if (consultingData?.consulting_roles) {
      setConsultingRoles(consultingData.consulting_roles);
    }
  }, [consultingData]);

  // Mutation: Save attendance policy
  const saveAttendancePolicyMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/settings/attendance-policy`, {
        policy: attendancePolicy,
        consulting_roles: consultingRoles
      }, { headers });
    },
    onSuccess: () => {
      toast.success('Attendance policy saved successfully');
      queryClient.invalidateQueries({ queryKey: ['/api/attendance/policy'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save attendance policy');
    },
    onSettled: () => setSaving(false)
  });

  const saveAttendancePolicy = () => {
    setSaving(true);
    saveAttendancePolicyMutation.mutate();
  };

  const openAddPolicyModal = () => {
    setEditingPolicy(null);
    setPolicyForm({
      employee_id: '',
      check_in: attendancePolicy.non_consulting.check_in,
      check_out: attendancePolicy.non_consulting.check_out,
      grace_period_minutes: attendancePolicy.grace_period_minutes,
      grace_days_per_month: attendancePolicy.grace_days_per_month,
      reason: ''
    });
    setShowPolicyModal(true);
  };

  const openEditPolicyModal = (policy) => {
    setEditingPolicy(policy);
    setPolicyForm({
      employee_id: policy.employee_id,
      check_in: policy.check_in,
      check_out: policy.check_out,
      grace_period_minutes: policy.grace_period_minutes,
      grace_days_per_month: policy.grace_days_per_month,
      reason: policy.reason || ''
    });
    setShowPolicyModal(true);
  };

  // Mutation: Save custom policy
  const saveCustomPolicyMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/api/attendance/policy/custom`, policyForm, { headers });
    },
    onSuccess: () => {
      toast.success(editingPolicy ? 'Custom policy updated' : 'Custom policy created');
      setShowPolicyModal(false);
      refetchCustomPolicies();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save custom policy');
    },
    onSettled: () => setSaving(false)
  });

  const saveCustomPolicy = () => {
    if (!policyForm.employee_id) {
      toast.error('Please select an employee');
      return;
    }
    setSaving(true);
    saveCustomPolicyMutation.mutate();
  };

  // Mutation: Delete custom policy
  const deleteCustomPolicyMutation = useMutation({
    mutationFn: async (employeeId) => {
      return axios.delete(`${API}/api/attendance/policy/custom/${employeeId}`, { headers });
    },
    onSuccess: () => {
      toast.success('Custom policy removed');
      refetchCustomPolicies();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete custom policy');
    }
  });

  const deleteCustomPolicy = (employeeId) => {
    if (!window.confirm('Are you sure you want to remove this custom policy? The employee will revert to default policy.')) {
      return;
    }
    deleteCustomPolicyMutation.mutate(employeeId);
  };

  // Get employees without custom policies for the dropdown
  const availableEmployees = (allEmployees || []).filter(emp => 
    !(customPolicies || []).some(p => p.employee_id === emp.id) || 
    (editingPolicy && editingPolicy.employee_id === emp.id)
  );

  const toggleWorkingDay = (day) => {
    setAttendancePolicy(prev => ({
      ...prev,
      working_days: prev.working_days.includes(day)
        ? (prev?.working_days || []).filter(d => d !== day)
        : [...prev.working_days, day]
    }));
  };

  const allDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-600" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="attendance-settings">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Attendance Settings</h1>
          <p className="text-zinc-600">Configure attendance policies, working hours, and grace periods</p>
        </div>
        <Button onClick={() => refetchAttendancePolicy()} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Attendance Policy */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-400" />
            Attendance Policy
          </CardTitle>
          <CardDescription>Configure working hours, grace periods, and penalties</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Working Days */}
          <div>
            <Label className="text-zinc-800 mb-3 block">Working Days</Label>
            <div className="flex flex-wrap gap-2">
              {(allDays || []).map(day => (
                <Button
                  key={day}
                  variant={attendancePolicy.working_days.includes(day) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => toggleWorkingDay(day)}
                  className={attendancePolicy.working_days.includes(day) 
                    ? 'bg-blue-600 hover:bg-blue-700' 
                    : 'border-zinc-300'}
                >
                  {day.slice(0, 3)}
                </Button>
              ))}
            </div>
          </div>

          {/* Working Hours */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-zinc-50 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-4">
                <Users className="w-5 h-5 text-green-400" />
                <Label className="text-zinc-800">Non-Consulting Staff</Label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-zinc-600">Check-in Time</Label>
                  <Input
                    type="time"
                    value={attendancePolicy.non_consulting.check_in}
                    onChange={(e) => setAttendancePolicy(prev => ({
                      ...prev,
                      non_consulting: { ...prev.non_consulting, check_in: e.target.value }
                    }))}
                    className="bg-zinc-100 border-zinc-300"
                  />
                </div>
                <div>
                  <Label className="text-xs text-zinc-600">Check-out Time</Label>
                  <Input
                    type="time"
                    value={attendancePolicy.non_consulting.check_out}
                    onChange={(e) => setAttendancePolicy(prev => ({
                      ...prev,
                      non_consulting: { ...prev.non_consulting, check_out: e.target.value }
                    }))}
                    className="bg-zinc-100 border-zinc-300"
                  />
                </div>
              </div>
            </div>

            <div className="bg-zinc-50 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-4">
                <Coffee className="w-5 h-5 text-purple-400" />
                <Label className="text-zinc-800">Consulting Staff</Label>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-zinc-600">Check-in Time</Label>
                  <Input
                    type="time"
                    value={attendancePolicy.consulting.check_in}
                    onChange={(e) => setAttendancePolicy(prev => ({
                      ...prev,
                      consulting: { ...prev.consulting, check_in: e.target.value }
                    }))}
                    className="bg-zinc-100 border-zinc-300"
                  />
                </div>
                <div>
                  <Label className="text-xs text-zinc-600">Check-out Time</Label>
                  <Input
                    type="time"
                    value={attendancePolicy.consulting.check_out}
                    onChange={(e) => setAttendancePolicy(prev => ({
                      ...prev,
                      consulting: { ...prev.consulting, check_out: e.target.value }
                    }))}
                    className="bg-zinc-100 border-zinc-300"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Grace Period & Penalties */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label className="text-zinc-800">Grace Period (minutes)</Label>
              <Input
                type="number"
                min="0"
                max="60"
                value={attendancePolicy.grace_period_minutes}
                onChange={(e) => setAttendancePolicy(prev => ({
                  ...prev,
                  grace_period_minutes: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-50 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Early/late tolerance before penalty</p>
            </div>
            <div>
              <Label className="text-zinc-800">Grace Days per Month</Label>
              <Input
                type="number"
                min="0"
                max="30"
                value={attendancePolicy.grace_days_per_month}
                onChange={(e) => setAttendancePolicy(prev => ({
                  ...prev,
                  grace_days_per_month: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-50 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Days allowed within grace before penalty</p>
            </div>
            <div>
              <Label className="text-zinc-800">Late Penalty Amount (₹)</Label>
              <Input
                type="number"
                min="0"
                value={attendancePolicy.late_penalty_amount}
                onChange={(e) => setAttendancePolicy(prev => ({
                  ...prev,
                  late_penalty_amount: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-50 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Per day beyond grace days</p>
            </div>
          </div>

          {/* Consulting Roles - Read Only */}
          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Badge className="w-5 h-5 text-purple-600" />
                <Label className="text-zinc-800 font-medium">Consulting Roles</Label>
              </div>
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-purple-500" />
                <span className="text-xs text-purple-600">Inherited from Employee Master</span>
              </div>
            </div>
            <p className="text-xs text-zinc-600 mb-3">These roles follow consulting timing ({attendancePolicy.consulting.check_in} - {attendancePolicy.consulting.check_out})</p>
            
            {/* Role badges */}
            <div className="flex flex-wrap gap-2 mb-3">
              {(consultingRoles || []).map(role => (
                <span 
                  key={role}
                  className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium flex items-center gap-1"
                >
                  {role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  {consultingRoleCounts[role] > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 bg-purple-200 text-purple-800 rounded-full text-xs">
                      {consultingRoleCounts[role]}
                    </span>
                  )}
                </span>
              ))}
            </div>
            
            {consultingEmployees.length > 0 && (
              <p className="text-sm text-purple-700">
                <strong>{consultingEmployees.length}</strong> employees follow consulting timing
              </p>
            )}
          </div>

          <Button onClick={saveAttendancePolicy} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
            <Save className="w-4 h-4 mr-2" />
            Save Attendance Policy
          </Button>
        </CardContent>
      </Card>

      {/* Employee-wise Custom Policies */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5 text-orange-400" />
                Employee-wise Configuration
              </CardTitle>
              <CardDescription>Set custom attendance policies for specific employees</CardDescription>
            </div>
            <Button onClick={openAddPolicyModal} className="bg-orange-500 hover:bg-orange-600">
              <Plus className="w-4 h-4 mr-2" />
              Add Custom Policy
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {customPolicies.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              <User className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
              <p className="text-sm">No custom policies configured</p>
              <p className="text-xs mt-1">All employees follow the default attendance policy</p>
            </div>
          ) : (
            <div className="space-y-3">
              {(customPolicies || []).map((policy) => (
                <div 
                  key={policy.employee_id}
                  className="p-4 bg-zinc-50 rounded-lg border border-zinc-200 hover:border-orange-300 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium text-zinc-900">{policy.employee_name}</span>
                        <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full">
                          {policy.employee_code}
                        </span>
                        {policy.department && (
                          <span className="text-xs text-zinc-500">{policy.department}</span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-zinc-500">Check-in:</span>{' '}
                          <span className="font-medium">{policy.check_in}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Check-out:</span>{' '}
                          <span className="font-medium">{policy.check_out}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Grace:</span>{' '}
                          <span className="font-medium">{policy.grace_period_minutes} min</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">Grace Days:</span>{' '}
                          <span className="font-medium">{policy.grace_days_per_month}/month</span>
                        </div>
                      </div>
                      {policy.reason && (
                        <p className="mt-2 text-xs text-zinc-600 italic">
                          Reason: {policy.reason}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2 ml-4">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => openEditPolicyModal(policy)}
                        className="h-8 px-2"
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => deleteCustomPolicy(policy.employee_id)}
                        className="h-8 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Leave Policy Notice - Link to Leave Policy Settings */}
      <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-800">Leave Policy Configuration</p>
              <p className="text-xs text-green-600">Configure leave entitlements, carry forward, and more in Business Rules</p>
            </div>
          </div>
          <a 
            href="/business-rules" 
            className="inline-flex items-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors"
          >
            <Settings className="w-4 h-4 mr-2" />
            Open Business Rules
          </a>
        </CardContent>
      </Card>

      {/* Policy Summary */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-zinc-600" />
            Current Attendance Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div>
            <h4 className="text-sm font-medium text-zinc-700 mb-2">Attendance Rules</h4>
            <ul className="text-sm text-zinc-600 space-y-1">
              <li>Working Days: {(attendancePolicy?.working_days || []).map(d => d.slice(0, 3)).join(', ')}</li>
              <li>Non-Consulting: {attendancePolicy.non_consulting.check_in} - {attendancePolicy.non_consulting.check_out}</li>
              <li>Consulting: {attendancePolicy.consulting.check_in} - {attendancePolicy.consulting.check_out}</li>
              <li>Grace: {attendancePolicy.grace_days_per_month} days/month with {attendancePolicy.grace_period_minutes} min tolerance</li>
              <li>Penalty: ₹{attendancePolicy.late_penalty_amount}/day beyond grace</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Custom Policy Modal */}
      <Dialog open={showPolicyModal} onOpenChange={setShowPolicyModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingPolicy ? 'Edit Custom Policy' : 'Add Custom Policy'}
            </DialogTitle>
            <DialogDescription>
              Set a custom attendance policy for an employee. This overrides the default policy.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Employee Selection */}
            <div>
              <Label className="mb-2 block">Employee</Label>
              {editingPolicy ? (
                <div className="px-3 py-2 bg-zinc-100 rounded-md text-sm">
                  {editingPolicy.employee_name} ({editingPolicy.employee_code})
                </div>
              ) : (
                <Select 
                  value={policyForm.employee_id} 
                  onValueChange={(value) => setPolicyForm(prev => ({ ...prev, employee_id: value }))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select an employee" />
                  </SelectTrigger>
                  <SelectContent>
                    {(availableEmployees || []).map(emp => (
                      <SelectItem key={emp.id} value={emp.id}>
                        {emp.first_name} {emp.last_name} ({emp.employee_id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Working Hours */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-2 block text-sm">Check-in Time</Label>
                <Input
                  type="time"
                  value={policyForm.check_in}
                  onChange={(e) => setPolicyForm(prev => ({ ...prev, check_in: e.target.value }))}
                />
              </div>
              <div>
                <Label className="mb-2 block text-sm">Check-out Time</Label>
                <Input
                  type="time"
                  value={policyForm.check_out}
                  onChange={(e) => setPolicyForm(prev => ({ ...prev, check_out: e.target.value }))}
                />
              </div>
            </div>

            {/* Grace Settings */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-2 block text-sm">Grace Period (min)</Label>
                <Input
                  type="number"
                  min="0"
                  max="60"
                  value={policyForm.grace_period_minutes}
                  onChange={(e) => setPolicyForm(prev => ({ ...prev, grace_period_minutes: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <Label className="mb-2 block text-sm">Grace Days/Month</Label>
                <Input
                  type="number"
                  min="0"
                  max="30"
                  value={policyForm.grace_days_per_month}
                  onChange={(e) => setPolicyForm(prev => ({ ...prev, grace_days_per_month: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>

            {/* Reason */}
            <div>
              <Label className="mb-2 block text-sm">Reason for Custom Policy</Label>
              <Input
                value={policyForm.reason}
                onChange={(e) => setPolicyForm(prev => ({ ...prev, reason: e.target.value }))}
                placeholder="e.g., Remote worker, Medical condition, etc."
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPolicyModal(false)}>
              Cancel
            </Button>
            <Button onClick={saveCustomPolicy} disabled={saving} className="bg-orange-500 hover:bg-orange-600">
              {saving ? 'Saving...' : editingPolicy ? 'Update Policy' : 'Create Policy'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AttendanceLeaveSettings;
