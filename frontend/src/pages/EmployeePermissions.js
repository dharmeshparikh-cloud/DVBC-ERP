import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import { 
  Search, User, Users, Shield, Building2, GitBranch, Settings,
  CheckCircle, XCircle, Clock, AlertTriangle, Eye, Edit, Save,
  ChevronRight, Lock, Unlock, RefreshCw, Send, History
} from 'lucide-react';
import { toast } from 'sonner';

// Module permissions structure
const MODULES = [
  { id: 'sales', name: 'Sales', icon: Users, features: ['leads', 'proposals', 'sow', 'meetings'] },
  { id: 'consulting', name: 'Consulting', icon: GitBranch, features: ['projects', 'timeline', 'deliverables', 'team'] },
  { id: 'hr', name: 'HR', icon: User, features: ['employees', 'onboarding', 'documents', 'leave', 'attendance', 'payroll'] },
  { id: 'finance', name: 'Finance', icon: Building2, features: ['expenses', 'reimbursement', 'invoices', 'reports'] },
  { id: 'admin', name: 'Admin', icon: Shield, features: ['users', 'roles', 'permissions', 'masters', 'settings'] },
];

const ACTIONS = ['view', 'create', 'edit', 'delete'];

const EmployeePermissions = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  const [departments, setDepartments] = useState([]);
  
  // Permission editing
  const [editMode, setEditMode] = useState(false);
  const [permissions, setPermissions] = useState({});
  const [originalPermissions, setOriginalPermissions] = useState({});
  const [pendingChanges, setPendingChanges] = useState([]);
  
  // Dialogs
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalNote, setApprovalNote] = useState('');
  
  // Reporting manager selection
  const [reportingManager, setReportingManager] = useState(null);
  const [assignedRole, setAssignedRole] = useState('');
  
  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);
  const canEdit = isAdmin || isHR;

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedEmployee) {
      fetchEmployeePermissions(selectedEmployee.employee_id);
    }
  }, [selectedEmployee]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [employeesRes, rolesRes] = await Promise.all([
        fetch(`${API}/employees`, { headers }),
        fetch(`${API}/roles`, { headers }).catch(() => ({ ok: false }))
      ]);

      if (employeesRes.ok) {
        const data = await employeesRes.json();
        setEmployees(data.filter(e => e.is_active !== false));
        
        // Extract unique departments
        const depts = [...new Set(data.map(e => e.department).filter(Boolean))];
        setDepartments(depts);
      }

      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        setRoles(rolesData);
      }

      // Fetch pending permission changes
      await fetchPendingChanges();
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployeePermissions = async (employeeId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/employee-permissions/${employeeId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setPermissions(data.permissions || {});
        setOriginalPermissions(data.permissions || {});
        setReportingManager(data.reporting_manager_id);
        setAssignedRole(data.role || '');
      } else {
        // Initialize with default permissions
        const defaultPerms = {};
        MODULES.forEach(mod => {
          defaultPerms[mod.id] = {};
          mod.features.forEach(feat => {
            defaultPerms[mod.id][feat] = { view: false, create: false, edit: false, delete: false };
          });
        });
        setPermissions(defaultPerms);
        setOriginalPermissions(defaultPerms);
      }
    } catch (error) {
      console.error('Error fetching permissions:', error);
    }
  };

  const fetchPendingChanges = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/permission-change-requests?status=pending`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPendingChanges(data);
      }
    } catch (error) {
      console.error('Error fetching pending changes:', error);
    }
  };

  const handlePermissionChange = (moduleId, feature, action, value) => {
    setPermissions(prev => ({
      ...prev,
      [moduleId]: {
        ...prev[moduleId],
        [feature]: {
          ...prev[moduleId]?.[feature],
          [action]: value
        }
      }
    }));
  };

  const handleSavePermissions = async () => {
    if (!selectedEmployee) return;

    // Check if there are actual changes
    const hasChanges = JSON.stringify(permissions) !== JSON.stringify(originalPermissions) ||
                       reportingManager !== selectedEmployee.reporting_manager_id ||
                       assignedRole !== selectedEmployee.role;

    if (!hasChanges) {
      toast.info('No changes to save');
      return;
    }

    if (isAdmin) {
      // Admin can save directly
      await savePermissionsDirect();
    } else {
      // HR needs admin approval
      setShowApprovalDialog(true);
    }
  };

  const savePermissionsDirect = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/employee-permissions/${selectedEmployee.employee_id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          permissions,
          reporting_manager_id: reportingManager,
          role: assignedRole
        })
      });

      if (response.ok) {
        toast.success('Permissions updated successfully');
        setEditMode(false);
        setOriginalPermissions(permissions);
        fetchData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save permissions');
      }
    } catch (error) {
      toast.error('Error saving permissions');
    }
  };

  const submitForApproval = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/permission-change-requests`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          employee_id: selectedEmployee.employee_id,
          employee_name: `${selectedEmployee.first_name} ${selectedEmployee.last_name}`,
          requested_by: user.email,
          requested_by_name: user.full_name,
          changes: {
            permissions,
            reporting_manager_id: reportingManager,
            role: assignedRole
          },
          original_values: {
            permissions: originalPermissions,
            reporting_manager_id: selectedEmployee.reporting_manager_id,
            role: selectedEmployee.role
          },
          note: approvalNote
        })
      });

      if (response.ok) {
        toast.success('Permission change request submitted for admin approval');
        setShowApprovalDialog(false);
        setApprovalNote('');
        setEditMode(false);
        fetchPendingChanges();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit request');
      }
    } catch (error) {
      toast.error('Error submitting request');
    }
  };

  const handleApproveRequest = async (requestId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/permission-change-requests/${requestId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Permission change approved and applied');
        fetchData();
        fetchPendingChanges();
      } else {
        toast.error('Failed to approve request');
      }
    } catch (error) {
      toast.error('Error approving request');
    }
  };

  const handleRejectRequest = async (requestId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/permission-change-requests/${requestId}/reject`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Permission change request rejected');
        fetchPendingChanges();
      } else {
        toast.error('Failed to reject request');
      }
    } catch (error) {
      toast.error('Error rejecting request');
    }
  };

  // Filter employees
  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = searchQuery === '' ||
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = filterDepartment === '' || emp.department === filterDepartment;
    return matchesSearch && matchesDept;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="employee-permissions">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Shield className="w-6 h-6 text-orange-500" />
            Employee Access Management
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Configure permissions, roles, and reporting hierarchy for employees
          </p>
        </div>
        {!isAdmin && (
          <Badge variant="outline" className="text-orange-600 border-orange-300">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Changes require Admin approval
          </Badge>
        )}
      </div>

      {/* Pending Approvals (Admin only) */}
      {isAdmin && pendingChanges.length > 0 && (
        <Card className="border-amber-200 bg-amber-50 dark:bg-amber-900/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-amber-700">
              <Clock className="w-4 h-4" />
              Pending Approval Requests ({pendingChanges.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {pendingChanges.slice(0, 3).map(req => (
              <div key={req.id} className="flex items-center justify-between p-3 bg-white dark:bg-zinc-800 rounded-lg">
                <div>
                  <p className="font-medium">{req.employee_name}</p>
                  <p className="text-xs text-zinc-500">
                    Requested by {req.requested_by_name} • {new Date(req.created_at).toLocaleDateString()}
                  </p>
                  {req.note && <p className="text-xs text-zinc-600 mt-1">Note: {req.note}</p>}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleRejectRequest(req.id)}>
                    <XCircle className="w-4 h-4 mr-1 text-red-500" />
                    Reject
                  </Button>
                  <Button size="sm" onClick={() => handleApproveRequest(req.id)} className="bg-emerald-600 hover:bg-emerald-700">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    Approve
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Employee List */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Select Employee</CardTitle>
            <div className="space-y-2 mt-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  placeholder="Search by name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={filterDepartment || 'all'} onValueChange={(v) => setFilterDepartment(v === 'all' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="All Departments" />
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
          <CardContent className="max-h-[500px] overflow-y-auto space-y-1 pt-0">
            {filteredEmployees.map(emp => (
              <button
                key={emp.id}
                onClick={() => {
                  setSelectedEmployee(emp);
                  setEditMode(false);
                }}
                className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                  selectedEmployee?.id === emp.id
                    ? 'bg-orange-50 dark:bg-orange-900/20 border border-orange-200'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-800'
                }`}
                data-testid={`emp-select-${emp.employee_id}`}
              >
                <div className="w-10 h-10 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-sm font-medium">
                  {emp.first_name?.charAt(0)?.toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{emp.first_name} {emp.last_name}</p>
                  <p className="text-xs text-zinc-500 font-mono">{emp.employee_id}</p>
                </div>
                {emp.user_id ? (
                  <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-700">
                    <Unlock className="w-3 h-3 mr-1" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs">
                    <Lock className="w-3 h-3 mr-1" />
                    No Access
                  </Badge>
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Permission Editor */}
        <Card className="lg:col-span-2">
          {selectedEmployee ? (
            <>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <User className="w-4 h-4" />
                      {selectedEmployee.first_name} {selectedEmployee.last_name}
                    </CardTitle>
                    <CardDescription>
                      {selectedEmployee.employee_id} • {selectedEmployee.department} • {selectedEmployee.designation}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!editMode ? (
                      <Button variant="outline" onClick={() => setEditMode(true)} disabled={!canEdit}>
                        <Edit className="w-4 h-4 mr-2" />
                        Edit Permissions
                      </Button>
                    ) : (
                      <>
                        <Button variant="outline" onClick={() => {
                          setEditMode(false);
                          setPermissions(originalPermissions);
                        }}>
                          Cancel
                        </Button>
                        <Button onClick={handleSavePermissions} className="bg-orange-600 hover:bg-orange-700">
                          {isAdmin ? (
                            <>
                              <Save className="w-4 h-4 mr-2" />
                              Save Changes
                            </>
                          ) : (
                            <>
                              <Send className="w-4 h-4 mr-2" />
                              Submit for Approval
                            </>
                          )}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Role & Reporting Manager */}
                <div className="grid grid-cols-2 gap-4 p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                  <div className="space-y-2">
                    <Label>Assigned Role</Label>
                    <Select 
                      value={assignedRole} 
                      onValueChange={setAssignedRole}
                      disabled={!editMode}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="hr_manager">HR Manager</SelectItem>
                        <SelectItem value="hr_executive">HR Executive</SelectItem>
                        <SelectItem value="account_manager">Account Manager</SelectItem>
                        <SelectItem value="sales_executive">Sales Executive</SelectItem>
                        <SelectItem value="consultant">Consultant</SelectItem>
                        <SelectItem value="senior_consultant">Senior Consultant</SelectItem>
                        <SelectItem value="project_manager">Project Manager</SelectItem>
                        <SelectItem value="delivery_lead">Delivery Lead</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Reporting Manager</Label>
                    <Select 
                      value={reportingManager || ''} 
                      onValueChange={setReportingManager}
                      disabled={!editMode}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select manager" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">None</SelectItem>
                        {employees
                          .filter(e => e.id !== selectedEmployee.id)
                          .map(emp => (
                            <SelectItem key={emp.id} value={emp.employee_id}>
                              {emp.first_name} {emp.last_name} ({emp.employee_id})
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Module Permissions */}
                <div className="space-y-4">
                  <h3 className="font-medium text-sm flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    Module Permissions
                  </h3>
                  
                  {MODULES.map(module => (
                    <div key={module.id} className="border rounded-lg overflow-hidden">
                      <div className="p-3 bg-zinc-50 dark:bg-zinc-800 flex items-center gap-2">
                        <module.icon className="w-4 h-4 text-orange-500" />
                        <span className="font-medium">{module.name}</span>
                      </div>
                      <div className="p-3">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-xs text-zinc-500 uppercase">
                              <th className="text-left py-2">Feature</th>
                              {ACTIONS.map(action => (
                                <th key={action} className="text-center py-2 w-20">{action}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {module.features.map(feature => (
                              <tr key={feature} className="border-t border-zinc-100">
                                <td className="py-2 capitalize">{feature.replace('_', ' ')}</td>
                                {ACTIONS.map(action => (
                                  <td key={action} className="text-center py-2">
                                    <Switch
                                      checked={permissions[module.id]?.[feature]?.[action] || false}
                                      onCheckedChange={(checked) => handlePermissionChange(module.id, feature, action, checked)}
                                      disabled={!editMode}
                                      className="data-[state=checked]:bg-orange-500"
                                    />
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </>
          ) : (
            <CardContent className="flex flex-col items-center justify-center py-16 text-zinc-500">
              <User className="w-12 h-12 mb-4 text-zinc-300" />
              <p className="font-medium">Select an Employee</p>
              <p className="text-sm">Choose an employee from the list to view and manage their permissions</p>
            </CardContent>
          )}
        </Card>
      </div>

      {/* Approval Request Dialog */}
      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-orange-500" />
              Submit for Admin Approval
            </DialogTitle>
            <DialogDescription>
              Your permission changes will be sent to an Admin for review and approval.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg text-sm">
              <p><strong>Employee:</strong> {selectedEmployee?.first_name} {selectedEmployee?.last_name}</p>
              <p><strong>Employee ID:</strong> {selectedEmployee?.employee_id}</p>
            </div>
            <div className="space-y-2">
              <Label>Note for Admin (Optional)</Label>
              <Textarea
                placeholder="Explain why these permission changes are needed..."
                value={approvalNote}
                onChange={(e) => setApprovalNote(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApprovalDialog(false)}>Cancel</Button>
            <Button onClick={submitForApproval} className="bg-orange-600 hover:bg-orange-700">
              <Send className="w-4 h-4 mr-2" />
              Submit Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmployeePermissions;
