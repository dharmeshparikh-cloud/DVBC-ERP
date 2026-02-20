import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { 
  Calendar, Clock, Users, CheckCircle, XCircle, AlertTriangle, 
  RefreshCw, Download, Upload, Filter, Search, DollarSign
} from 'lucide-react';

const HRAttendanceInput = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [employees, setEmployees] = useState([]);
  const [validationResults, setValidationResults] = useState(null);
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bulkDate, setBulkDate] = useState(new Date().toISOString().slice(0, 10));
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchPolicy();
    fetchAttendanceInput();
  }, [month]);

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

  const fetchAttendanceInput = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/attendance/hr/employee-attendance-input/${month}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setEmployees(data.employees || []);
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
          <h1 className="text-2xl font-bold text-zinc-100">HR Attendance Input</h1>
          <p className="text-zinc-400">Manage attendance, validate policies, and apply penalties</p>
        </div>
        <div className="flex items-center gap-3">
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-40 bg-zinc-800 border-zinc-700"
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
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" />
              Attendance Policy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-zinc-400">Working Days:</span>
                <p className="text-zinc-200">{policy.working_days?.join(', ')}</p>
              </div>
              <div>
                <span className="text-zinc-400">Non-Consulting:</span>
                <p className="text-zinc-200">{policy.non_consulting?.check_in} - {policy.non_consulting?.check_out}</p>
              </div>
              <div>
                <span className="text-zinc-400">Consulting:</span>
                <p className="text-zinc-200">{policy.consulting?.check_in} - {policy.consulting?.check_out}</p>
              </div>
              <div>
                <span className="text-zinc-400">Grace Period:</span>
                <p className="text-zinc-200">{policy.grace_days_per_month} days/month, {policy.grace_period_minutes} min</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions Row */}
      <div className="flex flex-wrap gap-4">
        <Card className="bg-zinc-900 border-zinc-800 flex-1 min-w-[300px]">
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

        <Card className="bg-zinc-900 border-zinc-800 flex-1 min-w-[300px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Bulk Mark Attendance</CardTitle>
            <CardDescription>Mark attendance for selected employees</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2 items-center">
            <Input
              type="date"
              value={bulkDate}
              onChange={(e) => setBulkDate(e.target.value)}
              className="w-40 bg-zinc-800 border-zinc-700"
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
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              Validation Results - {validationResults.month}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4 mb-4">
              <div className="bg-zinc-800 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-zinc-100">{validationResults.summary.total_employees}</p>
                <p className="text-xs text-zinc-400">Total Employees</p>
              </div>
              <div className="bg-green-900/30 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-400">{validationResults.summary.clean}</p>
                <p className="text-xs text-zinc-400">Clean (No Penalty)</p>
              </div>
              <div className="bg-orange-900/30 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-orange-400">{validationResults.summary.penalty_pending}</p>
                <p className="text-xs text-zinc-400">Penalty Pending</p>
              </div>
              <div className="bg-red-900/30 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-400">Rs.{validationResults.summary.total_pending_penalties}</p>
                <p className="text-xs text-zinc-400">Total Penalties</p>
              </div>
            </div>
            
            {validationResults.employees.filter(e => e.status === 'penalty_pending').length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-zinc-300 mb-2">Employees with Penalties:</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {validationResults.employees
                    .filter(e => e.status === 'penalty_pending')
                    .map(emp => (
                      <div key={emp.employee_id} className="bg-zinc-800 p-3 rounded-lg flex justify-between items-center">
                        <div>
                          <p className="text-zinc-200 font-medium">{emp.name}</p>
                          <p className="text-xs text-zinc-400">
                            {emp.employee_code} | Grace used: {emp.grace_days_used}/{policy?.grace_days_per_month || 3} | 
                            Penalty days: {emp.penalty_days}
                          </p>
                        </div>
                        <span className="text-orange-400 font-bold">Rs.{emp.pending_penalty_amount}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Employee List */}
      <Card className="bg-zinc-900 border-zinc-800">
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
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="Search employee..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-zinc-800 border-zinc-700"
              />
            </div>
            <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
              <SelectTrigger className="w-40 bg-zinc-800 border-zinc-700">
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
            <div className="text-center py-8 text-zinc-400">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-700">
                    <th className="text-left p-3 text-zinc-400">
                      <input 
                        type="checkbox"
                        checked={selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0}
                        onChange={() => selectedEmployees.length === filteredEmployees.length ? deselectAll() : selectAll()}
                        className="rounded border-zinc-600"
                      />
                    </th>
                    <th className="text-left p-3 text-zinc-400">Employee</th>
                    <th className="text-left p-3 text-zinc-400">Department</th>
                    <th className="text-center p-3 text-zinc-400">Present</th>
                    <th className="text-center p-3 text-zinc-400">Absent</th>
                    <th className="text-center p-3 text-zinc-400">Half Day</th>
                    <th className="text-center p-3 text-zinc-400">WFH</th>
                    <th className="text-center p-3 text-zinc-400">Leaves</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.map(emp => (
                    <tr key={emp.employee_id} className="border-b border-zinc-800 hover:bg-zinc-800/50">
                      <td className="p-3">
                        <input 
                          type="checkbox"
                          checked={selectedEmployees.includes(emp.employee_id)}
                          onChange={() => toggleEmployeeSelection(emp.employee_id)}
                          className="rounded border-zinc-600"
                        />
                      </td>
                      <td className="p-3">
                        <p className="text-zinc-200 font-medium">{emp.name}</p>
                        <p className="text-xs text-zinc-500">{emp.employee_code}</p>
                      </td>
                      <td className="p-3 text-zinc-400">{emp.department || '-'}</td>
                      <td className="p-3 text-center text-green-400">{emp.present_days}</td>
                      <td className="p-3 text-center text-red-400">{emp.absent_days}</td>
                      <td className="p-3 text-center text-yellow-400">{emp.half_days}</td>
                      <td className="p-3 text-center text-blue-400">{emp.wfh_days}</td>
                      <td className="p-3 text-center text-purple-400">{emp.approved_leaves}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredEmployees.length === 0 && (
                <div className="text-center py-8 text-zinc-400">No employees found</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default HRAttendanceInput;
