import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { 
  Calendar, Clock, Users, CheckCircle, XCircle, AlertTriangle, 
  RefreshCw, Filter, Search, DollarSign, Settings, UserCog, Trash2
} from 'lucide-react';

const HRAttendanceInput = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [employees, setEmployees] = useState([]);
  const [allEmployees, setAllEmployees] = useState([]);
  const [validationResults, setValidationResults] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [customPolicies, setCustomPolicies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [bulkDate, setBulkDate] = useState(new Date().toISOString().slice(0, 10));
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('all');
  
  // Custom policy dialog
  const [showPolicyDialog, setShowPolicyDialog] = useState(false);
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
    fetchPolicy();
    fetchAllEmployees();
    fetchCustomPolicies();
  }, []);

  useEffect(() => {
    fetchAttendanceInput();
  }, [month, selectedEmployeeId]);

  const fetchPolicy = async () => {
    try {
      const res = await fetch(`${API}/attendance/policy`, { headers });
      if (res.ok) {
        const data = await res.json();
        setPolicy(data.policy);
      }
    } catch (error) {
      console.error('Error fetching policy:', error);
    }
  };

  const fetchAllEmployees = async () => {
    try {
      const res = await fetch(`${API}/employees`, { headers });
      if (res.ok) {
        const data = await res.json();
        setAllEmployees(data);
      }
    } catch (error) {
      console.error('Error fetching employees:', error);
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

  const fetchAttendanceInput = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/attendance/hr/employee-attendance-input/${month}`, { headers });
      if (res.ok) {
        const data = await res.json();
        let empList = data.employees || [];
        
        // Filter by selected employee if not 'all'
        if (selectedEmployeeId && selectedEmployeeId !== 'all') {
          empList = empList.filter(e => e.employee_id === selectedEmployeeId);
        }
        
        setEmployees(empList);
      }
    } catch (error) {
      toast.error('Failed to fetch attendance data');
    } finally {
      setLoading(false);
    }
  };

  const runAutoValidation = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/attendance/auto-validate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ month })
      });
      if (res.ok) {
        const data = await res.json();
        
        // Filter results if specific employee selected
        if (selectedEmployeeId && selectedEmployeeId !== 'all') {
          data.employees = data.employees.filter(e => e.employee_id === selectedEmployeeId);
          data.summary = {
            total_employees: data.employees.length,
            clean: data.employees.filter(e => e.status === 'clean').length,
            penalty_pending: data.employees.filter(e => e.status === 'penalty_pending').length,
            total_pending_penalties: data.employees.reduce((sum, e) => sum + e.pending_penalty_amount, 0)
          };
        }
        
        setValidationResults(data);
        toast.success(`Validation complete: ${data.summary.clean} clean, ${data.summary.penalty_pending} with penalties`);
      }
    } catch (error) {
      toast.error('Failed to run validation');
    } finally {
      setLoading(false);
    }
  };

  const applyPenalties = async () => {
    if (!validationResults) return;
    
    const penaltiesToApply = validationResults.employees
      .filter(e => e.pending_penalty_amount > 0)
      .map(e => ({
        employee_id: e.employee_id,
        penalty_amount: e.pending_penalty_amount,
        penalty_days: e.penalty_days
      }));

    if (penaltiesToApply.length === 0) {
      toast.info('No penalties to apply');
      return;
    }

    try {
      const res = await fetch(`${API}/attendance/apply-penalties`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ month, penalties: penaltiesToApply })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setValidationResults(null);
      }
    } catch (error) {
      toast.error('Failed to apply penalties');
    }
  };

  const markBulkAttendance = async (status) => {
    if (selectedEmployees.length === 0) {
      toast.warning('Select employees first');
      return;
    }

    const records = selectedEmployees.map(empId => ({
      employee_id: empId,
      status,
      check_in: status === 'present' ? `${bulkDate}T10:00:00Z` : null,
      check_out: status === 'present' ? `${bulkDate}T19:00:00Z` : null
    }));

    try {
      const res = await fetch(`${API}/attendance/hr/mark-attendance-bulk`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ date: bulkDate, records })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setSelectedEmployees([]);
        fetchAttendanceInput();
      }
    } catch (error) {
      toast.error('Failed to mark attendance');
    }
  };

  const saveCustomPolicy = async () => {
    if (!policyForm.employee_id) {
      toast.error('Please select an employee');
      return;
    }

    try {
      const res = await fetch(`${API}/attendance/policy/custom`, {
        method: 'POST',
        headers,
        body: JSON.stringify(policyForm)
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setShowPolicyDialog(false);
        setPolicyForm({
          employee_id: '',
          check_in: '10:00',
          check_out: '19:00',
          grace_period_minutes: 30,
          grace_days_per_month: 3,
          reason: ''
        });
        fetchCustomPolicies();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to save policy');
      }
    } catch (error) {
      toast.error('Failed to save custom policy');
    }
  };

  const deleteCustomPolicy = async (employeeId) => {
    if (!confirm('Delete custom policy? Employee will revert to default timing.')) return;

    try {
      const res = await fetch(`${API}/attendance/policy/custom/${employeeId}`, {
        method: 'DELETE',
        headers
      });
      if (res.ok) {
        toast.success('Custom policy deleted');
        fetchCustomPolicies();
      }
    } catch (error) {
      toast.error('Failed to delete policy');
    }
  };

  const toggleEmployeeSelection = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  const selectAll = () => {
    setSelectedEmployees(filteredEmployees.map(e => e.employee_id));
  };

  const deselectAll = () => {
    setSelectedEmployees([]);
  };

  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = emp.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          emp.employee_code?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = departmentFilter === 'all' || emp.department === departmentFilter;
    return matchesSearch && matchesDept;
  });

  const departments = [...new Set(employees.map(e => e.department).filter(Boolean))];

  return (
    <div className="p-6 space-y-6" data-testid="hr-attendance-input">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">HR Attendance Input</h1>
          <p className="text-zinc-600">Manage attendance, validate policies, and apply penalties</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedEmployeeId} onValueChange={setSelectedEmployeeId}>
            <SelectTrigger className="w-52 bg-zinc-50 border-zinc-300" data-testid="employee-selector">
              <SelectValue placeholder="All Employees" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Employees</SelectItem>
              {allEmployees.map(emp => (
                <SelectItem key={emp.id} value={emp.id}>
                  {emp.first_name} {emp.last_name} ({emp.employee_id})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-40 bg-zinc-50 border-zinc-300"
            data-testid="month-selector"
          />
          <Button onClick={fetchAttendanceInput} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Policy Summary */}
      {policy && (
        <Card className="bg-white border-zinc-200">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-500" />
                Attendance Policy
              </CardTitle>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowPolicyDialog(true)}
                data-testid="add-custom-policy-btn"
              >
                <UserCog className="w-4 h-4 mr-2" />
                Add Custom Policy
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-zinc-600">Working Days:</span>
                <p className="text-zinc-800 font-medium">{policy.working_days?.join(', ')}</p>
              </div>
              <div>
                <span className="text-zinc-600">Non-Consulting:</span>
                <p className="text-zinc-800 font-medium">{policy.non_consulting?.check_in} - {policy.non_consulting?.check_out}</p>
              </div>
              <div>
                <span className="text-zinc-600">Consulting:</span>
                <p className="text-zinc-800 font-medium">{policy.consulting?.check_in} - {policy.consulting?.check_out}</p>
              </div>
              <div>
                <span className="text-zinc-600">Grace Period:</span>
                <p className="text-zinc-800 font-medium">{policy.grace_days_per_month} days/month, {policy.grace_period_minutes} min</p>
              </div>
            </div>
            
            {/* Custom Policies List */}
            {customPolicies.length > 0 && (
              <div className="mt-4 pt-4 border-t border-zinc-200">
                <h4 className="text-sm font-medium text-zinc-700 mb-2 flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Custom Employee Policies ({customPolicies.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {customPolicies.map(cp => (
                    <div key={cp.employee_id} className="bg-blue-50 p-3 rounded-lg flex justify-between items-center">
                      <div>
                        <p className="text-zinc-800 font-medium text-sm">{cp.employee_name}</p>
                        <p className="text-xs text-zinc-600">
                          {cp.check_in} - {cp.check_out} | Grace: {cp.grace_days_per_month}d
                        </p>
                        {cp.reason && <p className="text-xs text-blue-600 mt-1">{cp.reason}</p>}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteCustomPolicy(cp.employee_id)}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Actions Row */}
      <div className="flex flex-wrap gap-4">
        <Card className="bg-white border-zinc-200 flex-1 min-w-[300px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Auto-Validate Attendance</CardTitle>
            <CardDescription>Run policy validation for the selected month</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button 
              onClick={runAutoValidation} 
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="validate-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Validate {month}
            </Button>
            {validationResults && validationResults.summary.penalty_pending > 0 && (
              <Button 
                onClick={applyPenalties}
                className="bg-orange-600 hover:bg-orange-700"
                data-testid="apply-penalties-btn"
              >
                <DollarSign className="w-4 h-4 mr-2" />
                Apply Penalties (Rs.{validationResults.summary.total_pending_penalties})
              </Button>
            )}
          </CardContent>
        </Card>

        <Card className="bg-white border-zinc-200 flex-1 min-w-[300px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Bulk Mark Attendance</CardTitle>
            <CardDescription>Mark attendance for selected employees</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2 items-center">
            <Input
              type="date"
              value={bulkDate}
              onChange={(e) => setBulkDate(e.target.value)}
              className="w-40 bg-zinc-50 border-zinc-300"
            />
            <Button 
              onClick={() => markBulkAttendance('present')}
              className="bg-green-600 hover:bg-green-700"
              disabled={selectedEmployees.length === 0}
              data-testid="mark-present-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Present ({selectedEmployees.length})
            </Button>
            <Button 
              onClick={() => markBulkAttendance('absent')}
              variant="destructive"
              disabled={selectedEmployees.length === 0}
            >
              <XCircle className="w-4 h-4 mr-2" />
              Absent
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Validation Results */}
      {validationResults && (
        <Card className="bg-white border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Validation Results - {validationResults.month}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="bg-zinc-100 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-zinc-900">{validationResults.summary.total_employees}</p>
                <p className="text-xs text-zinc-600">Total Employees</p>
              </div>
              <div className="bg-green-100 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-600">{validationResults.summary.clean}</p>
                <p className="text-xs text-zinc-600">Clean (No Penalty)</p>
              </div>
              <div className="bg-orange-100 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-orange-600">{validationResults.summary.penalty_pending}</p>
                <p className="text-xs text-zinc-600">Penalty Pending</p>
              </div>
              <div className="bg-red-100 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-600">Rs.{validationResults.summary.total_pending_penalties}</p>
                <p className="text-xs text-zinc-600">Total Penalties</p>
              </div>
            </div>
            
            {validationResults.employees.filter(e => e.status === 'penalty_pending').length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-zinc-700 mb-2">Employees with Penalties:</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {validationResults.employees
                    .filter(e => e.status === 'penalty_pending')
                    .map(emp => (
                      <div key={emp.employee_id} className="bg-zinc-50 p-3 rounded-lg flex justify-between items-center">
                        <div>
                          <p className="text-zinc-800 font-medium">{emp.name}</p>
                          <p className="text-xs text-zinc-600">
                            {emp.employee_code} | Policy: {emp.policy_times} | Grace used: {emp.grace_days_used}/{emp.grace_days_allowed} | 
                            Penalty days: {emp.penalty_days}
                            {emp.has_custom_policy && <span className="ml-2 text-blue-600">(Custom Policy)</span>}
                          </p>
                        </div>
                        <span className="text-orange-600 font-bold">Rs.{emp.pending_penalty_amount}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Employee List */}
      <Card className="bg-white border-zinc-200">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Employee Attendance Summary - {month}
            </CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={selectAll}>Select All</Button>
              <Button variant="outline" size="sm" onClick={deselectAll}>Deselect All</Button>
            </div>
          </div>
          <div className="flex gap-3 mt-3">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <Input
                placeholder="Search employee..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-zinc-50 border-zinc-300"
              />
            </div>
            <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
              <SelectTrigger className="w-40 bg-zinc-50 border-zinc-300">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map(dept => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-zinc-600">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200">
                    <th className="text-left p-3 text-zinc-600">
                      <input 
                        type="checkbox"
                        checked={selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0}
                        onChange={() => selectedEmployees.length === filteredEmployees.length ? deselectAll() : selectAll()}
                        className="rounded border-zinc-300"
                      />
                    </th>
                    <th className="text-left p-3 text-zinc-600">Employee</th>
                    <th className="text-left p-3 text-zinc-600">Department</th>
                    <th className="text-center p-3 text-zinc-600">Present</th>
                    <th className="text-center p-3 text-zinc-600">Absent</th>
                    <th className="text-center p-3 text-zinc-600">Half Day</th>
                    <th className="text-center p-3 text-zinc-600">WFH</th>
                    <th className="text-center p-3 text-zinc-600">Leaves</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.map(emp => (
                    <tr key={emp.employee_id} className="border-b border-zinc-100 hover:bg-zinc-50">
                      <td className="p-3">
                        <input 
                          type="checkbox"
                          checked={selectedEmployees.includes(emp.employee_id)}
                          onChange={() => toggleEmployeeSelection(emp.employee_id)}
                          className="rounded border-zinc-300"
                        />
                      </td>
                      <td className="p-3">
                        <p className="text-zinc-800 font-medium">{emp.name}</p>
                        <p className="text-xs text-zinc-500">{emp.employee_code}</p>
                      </td>
                      <td className="p-3 text-zinc-600">{emp.department || '-'}</td>
                      <td className="p-3 text-center text-green-600 font-medium">{emp.present_days}</td>
                      <td className="p-3 text-center text-red-600 font-medium">{emp.absent_days}</td>
                      <td className="p-3 text-center text-yellow-600 font-medium">{emp.half_days}</td>
                      <td className="p-3 text-center text-blue-600 font-medium">{emp.wfh_days}</td>
                      <td className="p-3 text-center text-purple-600 font-medium">{emp.approved_leaves}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredEmployees.length === 0 && (
                <div className="text-center py-8 text-zinc-600">No employees found</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Custom Policy Dialog */}
      <Dialog open={showPolicyDialog} onOpenChange={setShowPolicyDialog}>
        <DialogContent className="bg-white border-zinc-200 max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserCog className="w-5 h-5" />
              Set Custom Attendance Policy
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Employee *</Label>
              <Select 
                value={policyForm.employee_id} 
                onValueChange={(v) => setPolicyForm({...policyForm, employee_id: v})}
              >
                <SelectTrigger className="bg-zinc-50 border-zinc-300" data-testid="policy-employee-select">
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {allEmployees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.employee_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Check-in Time *</Label>
                <Input
                  type="time"
                  value={policyForm.check_in}
                  onChange={(e) => setPolicyForm({...policyForm, check_in: e.target.value})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
              <div>
                <Label>Check-out Time *</Label>
                <Input
                  type="time"
                  value={policyForm.check_out}
                  onChange={(e) => setPolicyForm({...policyForm, check_out: e.target.value})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Grace Period (minutes)</Label>
                <Input
                  type="number"
                  min="0"
                  max="60"
                  value={policyForm.grace_period_minutes}
                  onChange={(e) => setPolicyForm({...policyForm, grace_period_minutes: parseInt(e.target.value) || 30})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
              <div>
                <Label>Grace Days/Month</Label>
                <Input
                  type="number"
                  min="0"
                  max="10"
                  value={policyForm.grace_days_per_month}
                  onChange={(e) => setPolicyForm({...policyForm, grace_days_per_month: parseInt(e.target.value) || 3})}
                  className="bg-zinc-50 border-zinc-300"
                />
              </div>
            </div>
            <div>
              <Label>Reason for Custom Policy</Label>
              <Input
                value={policyForm.reason}
                onChange={(e) => setPolicyForm({...policyForm, reason: e.target.value})}
                placeholder="e.g., Part-time, Remote worker, Medical accommodation"
                className="bg-zinc-50 border-zinc-300"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPolicyDialog(false)}>Cancel</Button>
            <Button onClick={saveCustomPolicy} className="bg-blue-600 hover:bg-blue-700" data-testid="save-policy-btn">
              Save Custom Policy
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRAttendanceInput;
