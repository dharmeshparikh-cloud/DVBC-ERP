import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../../App';
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
  Sun, Moon, Coffee, DollarSign, Users, CheckCircle, User,
  Plus, Edit2, Trash2, Info, Badge
} from 'lucide-react';

const AttendanceLeaveSettings = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
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

  // Leave Policy Settings
  const [leavePolicy, setLeavePolicy] = useState({
    casual_leave: 12,
    sick_leave: 6,
    earned_leave: 15,
    carry_forward_enabled: false,
    max_carry_forward: 5,
    probation_leave_enabled: false,
    probation_leave_days: 0
  });

  // Consulting Employees (read-only from employee master)
  const [consultingEmployees, setConsultingEmployees] = useState([]);
  const [consultingRoleCounts, setConsultingRoleCounts] = useState({});
  const [consultingRoles, setConsultingRoles] = useState([]);

  // Employee-wise Custom Policies
  const [customPolicies, setCustomPolicies] = useState([]);
  const [allEmployees, setAllEmployees] = useState([]);
  
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

  useEffect(() => {
    fetchSettings();
    fetchConsultingEmployees();
    fetchCustomPolicies();
    fetchAllEmployees();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      // Fetch attendance policy
      const attRes = await fetch(`${API}/attendance/policy`, { headers });
      if (attRes.ok) {
        const data = await attRes.json();
        if (data.policy) setAttendancePolicy(data.policy);
        if (data.consulting_roles) setConsultingRoles(data.consulting_roles);
      }

      // Fetch leave policy
      const leaveRes = await fetch(`${API}/settings/leave-policy`, { headers });
      if (leaveRes.ok) {
        const data = await leaveRes.json();
        if (data.policy) setLeavePolicy(data.policy);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchConsultingEmployees = async () => {
    try {
      const res = await fetch(`${API}/attendance/consulting-employees`, { headers });
      if (res.ok) {
        const data = await res.json();
        setConsultingEmployees(data.employees || []);
        setConsultingRoleCounts(data.role_counts || {});
        if (data.consulting_roles) setConsultingRoles(data.consulting_roles);
      }
    } catch (error) {
      console.error('Error fetching consulting employees:', error);
    }
  };

  const fetchCustomPolicies = async () => {
    try {
      const res = await fetch(`${API}/attendance/policy/custom`, { headers });
      if (res.ok) {
        const data = await res.json();
        setCustomPolicies(data.policies || []);
      }
    } catch (error) {
      console.error('Error fetching custom policies:', error);
    }
  };

  const fetchAllEmployees = async () => {
    try {
      const res = await fetch(`${API}/employees`, { headers });
      if (res.ok) {
        const data = await res.json();
        setAllEmployees(data || []);
      }
    } catch (error) {
      console.error('Error fetching employees:', error);
    }
  };

  const saveAttendancePolicy = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/settings/attendance-policy`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          policy: attendancePolicy,
          consulting_roles: consultingRoles // Keep existing roles
        })
      });
      if (res.ok) {
        toast.success('Attendance policy saved successfully');
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to save attendance policy');
      }
    } catch (error) {
      toast.error('Failed to save attendance policy');
    } finally {
      setSaving(false);
    }
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

  const saveCustomPolicy = async () => {
    if (!policyForm.employee_id) {
      toast.error('Please select an employee');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API}/attendance/policy/custom`, {
        method: 'POST',
        headers,
        body: JSON.stringify(policyForm)
      });
      if (res.ok) {
        toast.success(editingPolicy ? 'Custom policy updated' : 'Custom policy created');
        setShowPolicyModal(false);
        fetchCustomPolicies();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to save custom policy');
      }
    } catch (error) {
      toast.error('Failed to save custom policy');
    } finally {
      setSaving(false);
    }
  };

  const deleteCustomPolicy = async (employeeId) => {
    if (!window.confirm('Are you sure you want to remove this custom policy? The employee will revert to default policy.')) {
      return;
    }

    try {
      const res = await fetch(`${API}/attendance/policy/custom/${employeeId}`, {
        method: 'DELETE',
        headers
      });
      if (res.ok) {
        toast.success('Custom policy removed');
        fetchCustomPolicies();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to delete custom policy');
      }
    } catch (error) {
      toast.error('Failed to delete custom policy');
    }
  };

  // Get employees without custom policies for the dropdown
  const availableEmployees = allEmployees.filter(emp => 
    !customPolicies.some(p => p.employee_id === emp.id) || 
    (editingPolicy && editingPolicy.employee_id === emp.id)
  );

  const saveLeavePolicy = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/settings/leave-policy`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ policy: leavePolicy })
      });
      if (res.ok) {
        toast.success('Leave policy saved successfully');
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to save leave policy');
      }
    } catch (error) {
      toast.error('Failed to save leave policy');
    } finally {
      setSaving(false);
    }
  };

  const toggleWorkingDay = (day) => {
    setAttendancePolicy(prev => ({
      ...prev,
      working_days: prev.working_days.includes(day)
        ? prev.working_days.filter(d => d !== day)
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
    <div className="p-6 space-y-6" data-testid="attendance-leave-settings">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Attendance & Leave Settings</h1>
          <p className="text-zinc-600">Configure attendance policies, working hours, and leave entitlements</p>
        </div>
        <Button onClick={fetchSettings} variant="outline" size="sm">
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
              {allDays.map(day => (
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

          {/* Consulting Roles */}
          <div>
            <Label className="text-zinc-800 mb-2 block">Consulting Roles</Label>
            <p className="text-xs text-zinc-500 mb-2">These roles follow consulting timing (10:30 AM - 7:30 PM)</p>
            <Input
              value={consultingRoles.join(', ')}
              onChange={(e) => setConsultingRoles(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
              placeholder="consultant, senior_consultant, ..."
              className="bg-zinc-50 border-zinc-300"
            />
          </div>

          <Button onClick={saveAttendancePolicy} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
            <Save className="w-4 h-4 mr-2" />
            Save Attendance Policy
          </Button>
        </CardContent>
      </Card>

      {/* Leave Policy */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-green-400" />
            Leave Policy
          </CardTitle>
          <CardDescription>Configure annual leave entitlements and rules</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Leave Entitlements */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-zinc-50 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <Sun className="w-5 h-5 text-blue-400" />
                <Label className="text-zinc-800">Casual Leave</Label>
              </div>
              <Input
                type="number"
                min="0"
                value={leavePolicy.casual_leave}
                onChange={(e) => setLeavePolicy(prev => ({
                  ...prev,
                  casual_leave: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-100 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Days per year</p>
            </div>

            <div className="bg-zinc-50 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                <Label className="text-zinc-800">Sick Leave</Label>
              </div>
              <Input
                type="number"
                min="0"
                value={leavePolicy.sick_leave}
                onChange={(e) => setLeavePolicy(prev => ({
                  ...prev,
                  sick_leave: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-100 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Days per year</p>
            </div>

            <div className="bg-zinc-50 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <Label className="text-zinc-800">Earned Leave</Label>
              </div>
              <Input
                type="number"
                min="0"
                value={leavePolicy.earned_leave}
                onChange={(e) => setLeavePolicy(prev => ({
                  ...prev,
                  earned_leave: parseInt(e.target.value) || 0
                }))}
                className="bg-zinc-100 border-zinc-300"
              />
              <p className="text-xs text-zinc-500 mt-1">Days per year</p>
            </div>
          </div>

          {/* Additional Leave Rules */}
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
              <div>
                <Label className="text-zinc-800">Carry Forward Leaves</Label>
                <p className="text-xs text-zinc-500">Allow unused leaves to carry forward to next year</p>
              </div>
              <Switch
                checked={leavePolicy.carry_forward_enabled}
                onCheckedChange={(checked) => setLeavePolicy(prev => ({
                  ...prev,
                  carry_forward_enabled: checked
                }))}
              />
            </div>

            {leavePolicy.carry_forward_enabled && (
              <div className="ml-4">
                <Label className="text-zinc-800">Maximum Carry Forward Days</Label>
                <Input
                  type="number"
                  min="0"
                  value={leavePolicy.max_carry_forward}
                  onChange={(e) => setLeavePolicy(prev => ({
                    ...prev,
                    max_carry_forward: parseInt(e.target.value) || 0
                  }))}
                  className="bg-zinc-50 border-zinc-300 w-32"
                />
              </div>
            )}

            <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
              <div>
                <Label className="text-zinc-800">Probation Period Leaves</Label>
                <p className="text-xs text-zinc-500">Allow limited leaves during probation period</p>
              </div>
              <Switch
                checked={leavePolicy.probation_leave_enabled}
                onCheckedChange={(checked) => setLeavePolicy(prev => ({
                  ...prev,
                  probation_leave_enabled: checked
                }))}
              />
            </div>

            {leavePolicy.probation_leave_enabled && (
              <div className="ml-4">
                <Label className="text-zinc-800">Probation Leave Days</Label>
                <Input
                  type="number"
                  min="0"
                  value={leavePolicy.probation_leave_days}
                  onChange={(e) => setLeavePolicy(prev => ({
                    ...prev,
                    probation_leave_days: parseInt(e.target.value) || 0
                  }))}
                  className="bg-zinc-50 border-zinc-300 w-32"
                />
              </div>
            )}
          </div>

          <Button onClick={saveLeavePolicy} disabled={saving} className="bg-green-600 hover:bg-green-700">
            <Save className="w-4 h-4 mr-2" />
            Save Leave Policy
          </Button>
        </CardContent>
      </Card>

      {/* Policy Summary */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-zinc-600" />
            Current Policy Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-zinc-700 mb-2">Attendance Rules</h4>
              <ul className="text-sm text-zinc-600 space-y-1">
                <li>Working Days: {attendancePolicy.working_days.map(d => d.slice(0, 3)).join(', ')}</li>
                <li>Non-Consulting: {attendancePolicy.non_consulting.check_in} - {attendancePolicy.non_consulting.check_out}</li>
                <li>Consulting: {attendancePolicy.consulting.check_in} - {attendancePolicy.consulting.check_out}</li>
                <li>Grace: {attendancePolicy.grace_days_per_month} days/month with {attendancePolicy.grace_period_minutes} min tolerance</li>
                <li>Penalty: ₹{attendancePolicy.late_penalty_amount}/day beyond grace</li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-medium text-zinc-700 mb-2">Leave Entitlements</h4>
              <ul className="text-sm text-zinc-600 space-y-1">
                <li>Casual Leave: {leavePolicy.casual_leave} days/year</li>
                <li>Sick Leave: {leavePolicy.sick_leave} days/year</li>
                <li>Earned Leave: {leavePolicy.earned_leave} days/year</li>
                <li>Carry Forward: {leavePolicy.carry_forward_enabled ? `Up to ${leavePolicy.max_carry_forward} days` : 'Disabled'}</li>
                <li>Total Annual: {leavePolicy.casual_leave + leavePolicy.sick_leave + leavePolicy.earned_leave} days</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AttendanceLeaveSettings;
