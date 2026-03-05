/**
 * EmployeeAccessPermissions.js
 * 
 * CONSOLIDATED PAGE: Combines PasswordManagement + EmployeePermissions
 * 
 * Tab 1: Portal Access - Grant/revoke access, reset passwords
 * Tab 2: Module Permissions - RBAC per module/feature
 * Tab 3: Pending Approvals - Permission change requests
 * 
 * PRESERVES: All existing APIs, query keys, and business logic
 */

import React, { useState, useContext, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import { 
  Key, Search, Shield, UserX, UserCheck, RefreshCw, Users, Building2, GitBranch,
  Lock, Unlock, AlertTriangle, Copy, Eye, EyeOff, CheckCircle, XCircle, Clock,
  Edit, Save, ChevronRight, Send, History, User, Settings
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Module permissions structure (from EmployeePermissions.js)
const MODULES = [
  { id: 'sales', name: 'Sales', icon: Users, features: ['leads', 'proposals', 'sow', 'meetings'] },
  { id: 'consulting', name: 'Consulting', icon: GitBranch, features: ['projects', 'timeline', 'deliverables', 'team'] },
  { id: 'hr', name: 'HR', icon: User, features: ['employees', 'onboarding', 'documents', 'leave', 'attendance', 'payroll'] },
  { id: 'finance', name: 'Finance', icon: Building2, features: ['expenses', 'reimbursement', 'invoices', 'reports'] },
  { id: 'admin', name: 'Admin', icon: Shield, features: ['users', 'roles', 'permissions', 'masters', 'settings'] },
];

const ACTIONS = ['view', 'create', 'edit', 'delete'];

const getDefaultPermissions = () => {
  const defaultPerms = {};
  MODULES.forEach(mod => {
    defaultPerms[mod.id] = {};
    mod.features.forEach(feat => {
      defaultPerms[mod.id][feat] = { view: false, create: false, edit: false, delete: false };
    });
  });
  return defaultPerms;
};

const EmployeeAccessPermissions = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  
  // Determine initial tab from URL params (for backward compatibility)
  const getInitialTab = () => {
    const tab = searchParams.get('tab');
    if (tab) return tab;
    // Check if redirected from old routes
    if (window.location.pathname.includes('password-management')) return 'access';
    if (window.location.pathname.includes('employee-permissions')) return 'permissions';
    return 'access';
  };
  
  const [activeTab, setActiveTab] = useState(getInitialTab());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  
  // Access tab states
  const [resetDialog, setResetDialog] = useState(false);
  const [disableDialog, setDisableDialog] = useState(false);
  const [grantAccessDialog, setGrantAccessDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [grantAccessForm, setGrantAccessForm] = useState({ role: 'consultant', password: 'Welcome@123' });
  
  // Permissions tab states
  const [editMode, setEditMode] = useState(false);
  const [permissions, setPermissions] = useState({});
  const [originalPermissions, setOriginalPermissions] = useState({});
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalNote, setApprovalNote] = useState('');
  const [reportingManager, setReportingManager] = useState(null);
  const [assignedRole, setAssignedRole] = useState('');
  
  const isAdmin = user?.role === 'admin';
  const isHR = user?.role === 'hr_manager' || user?.department === 'HR';
  const canManage = isAdmin || isHR;

  // ==================== QUERIES ====================
  
  // Query: Employees with access data (for Access tab)
  const { data: employeesWithAccess = [], isLoading: loadingAccess, refetch: refetchAccess } = useQuery({
    queryKey: ['employees', 'with-access'],
    queryFn: async () => {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      const [empRes, usersRes] = await Promise.all([
        axios.get(`${API}/employees/all`, { headers }),
        axios.get(`${API}/users`, { headers }).catch(() => ({ data: [] })) // Fallback if users endpoint fails
      ]);
      const empData = Array.isArray(empRes.data) ? empRes.data : [];
      const userData = Array.isArray(usersRes.data) ? usersRes.data : [];
      return empData.map(emp => {
        const linkedUser = userData.find(u => u.email === emp.email || u.employee_id === emp.employee_id);
        return {
          ...emp,
          user_id: linkedUser?.id,
          has_access: !!linkedUser,
          is_active: linkedUser?.is_active ?? true,
          role: linkedUser?.role || emp.role || 'N/A',
          last_login: linkedUser?.last_login
        };
      });
    },
    enabled: canManage,
    staleTime: 2 * 60 * 1000,
  });

  // Query: Employees for permissions tab
  const { data: employeesForPerms = [], isLoading: loadingPerms } = useQuery({
    queryKey: ['employees-permissions'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      const empList = Array.isArray(res.data) ? res.data : (res.data?.items || []);
      return empList.filter(e => e.is_active !== false);
    },
    enabled: activeTab === 'permissions'
  });

  // Query: Roles
  const { data: roles = [] } = useQuery({
    queryKey: ['roles-list'],
    queryFn: async () => {
      const res = await axios.get(`${API}/roles`);
      return res.data || [];
    },
    enabled: activeTab === 'permissions'
  });

  // Query: Pending permission change requests
  const { data: pendingChanges = [] } = useQuery({
    queryKey: ['permission-change-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/permission-change-requests?status=pending`);
      return res.data || [];
    },
    enabled: activeTab === 'approvals' && canManage
  });

  // Query: Employee permissions (when employee selected)
  const { data: empPermissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['employee-permissions', selectedEmployee?.employee_id],
    queryFn: async () => {
      const res = await axios.get(`${API}/employee-permissions/${selectedEmployee.employee_id}`);
      return res.data;
    },
    enabled: !!selectedEmployee?.employee_id && activeTab === 'permissions',
    onSuccess: (data) => {
      if (data?.permissions) {
        setPermissions(data.permissions);
        setOriginalPermissions(data.permissions);
        setAssignedRole(data.role || '');
        setReportingManager(data.reporting_manager || null);
      } else {
        setPermissions(getDefaultPermissions());
        setOriginalPermissions(getDefaultPermissions());
      }
    }
  });

  // ==================== MUTATIONS ====================
  
  // Reset Password
  const resetPasswordMutation = useMutation({
    mutationFn: async ({ employeeId, password }) => {
      await axios.post(`${API}/auth/admin/reset-employee-password`, {
        employee_id: employeeId,
        new_password: password
      });
      return password;
    },
    onSuccess: (password, { firstName, lastName }) => {
      toast.success(`Password reset for ${firstName} ${lastName}`);
      setResetDialog(false);
      setNewPassword('');
      setSelectedEmployee(null);
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to reset password'),
  });

  // Toggle Access
  const toggleAccessMutation = useMutation({
    mutationFn: async ({ employeeId, isActive }) => {
      await axios.post(`${API}/auth/admin/toggle-employee-access`, {
        employee_id: employeeId,
        is_active: !isActive
      });
      return !isActive;
    },
    onSuccess: (newStatus, { firstName, lastName }) => {
      toast.success(`Access ${newStatus ? 'enabled' : 'disabled'} for ${firstName} ${lastName}`);
      setDisableDialog(false);
      setSelectedEmployee(null);
      queryClient.invalidateQueries({ queryKey: ['employees', 'with-access'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to toggle access'),
  });

  // Grant Access
  const grantAccessMutation = useMutation({
    mutationFn: async ({ employeeId, role, password }) => {
      await axios.post(`${API}/employees/${employeeId}/grant-access`, { role, password });
    },
    onSuccess: () => {
      toast.success('Portal access granted successfully');
      setGrantAccessDialog(false);
      setSelectedEmployee(null);
      queryClient.invalidateQueries({ queryKey: ['employees', 'with-access'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to grant access'),
  });

  // Save Permissions
  const savePermissionsMutation = useMutation({
    mutationFn: async () => {
      return axios.put(`${API}/employee-permissions/${selectedEmployee.employee_id}`, {
        permissions,
        role: assignedRole
      });
    },
    onSuccess: () => {
      toast.success('Permissions saved successfully');
      setEditMode(false);
      setOriginalPermissions(permissions);
      queryClient.invalidateQueries({ queryKey: ['employees-permissions'] });
      queryClient.invalidateQueries({ queryKey: ['employee-permissions'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to save permissions'),
  });

  // Submit for Approval
  const submitApprovalMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/permission-change-requests`, {
        employee_id: selectedEmployee.employee_id,
        requested_permissions: permissions,
        requested_role: assignedRole,
        notes: approvalNote
      });
    },
    onSuccess: () => {
      toast.success('Permission change request submitted for approval');
      setShowApprovalDialog(false);
      setApprovalNote('');
      setEditMode(false);
      queryClient.invalidateQueries({ queryKey: ['permission-change-requests'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to submit request'),
  });

  // Approve Request
  const approveRequestMutation = useMutation({
    mutationFn: async (requestId) => {
      return axios.post(`${API}/permission-change-requests/${requestId}/approve`);
    },
    onSuccess: () => {
      toast.success('Request approved');
      queryClient.invalidateQueries({ queryKey: ['employees-permissions'] });
      queryClient.invalidateQueries({ queryKey: ['permission-change-requests'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to approve'),
  });

  // Reject Request
  const rejectRequestMutation = useMutation({
    mutationFn: async (requestId) => {
      return axios.post(`${API}/permission-change-requests/${requestId}/reject`);
    },
    onSuccess: () => {
      toast.success('Request rejected');
      queryClient.invalidateQueries({ queryKey: ['permission-change-requests'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to reject'),
  });

  // ==================== HANDLERS ====================
  
  const generatePassword = (employeeId) => `Welcome@${employeeId}`;

  const handleResetPassword = () => {
    if (!selectedEmployee) return;
    const passwordToSet = newPassword || generatePassword(selectedEmployee.employee_id);
    resetPasswordMutation.mutate({
      employeeId: selectedEmployee.employee_id,
      password: passwordToSet,
      firstName: selectedEmployee.first_name,
      lastName: selectedEmployee.last_name
    });
  };

  const handleToggleAccess = () => {
    if (!selectedEmployee) return;
    toggleAccessMutation.mutate({
      employeeId: selectedEmployee.employee_id,
      isActive: selectedEmployee.is_active,
      firstName: selectedEmployee.first_name,
      lastName: selectedEmployee.last_name
    });
  };

  const handleGrantAccess = () => {
    if (!selectedEmployee) return;
    grantAccessMutation.mutate({
      employeeId: selectedEmployee.id,
      role: grantAccessForm.role,
      password: grantAccessForm.password
    });
  };

  const togglePermission = (moduleId, feature, action) => {
    setPermissions(prev => ({
      ...prev,
      [moduleId]: {
        ...prev[moduleId],
        [feature]: {
          ...prev[moduleId]?.[feature],
          [action]: !prev[moduleId]?.[feature]?.[action]
        }
      }
    }));
  };

  // Filter employees based on search
  const filteredAccessEmployees = employeesWithAccess.filter(emp => {
    const matchesSearch = !searchQuery || 
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = !filterDepartment || emp.department === filterDepartment;
    return matchesSearch && matchesDept;
  });

  const filteredPermEmployees = employeesForPerms.filter(emp => {
    const matchesSearch = !searchQuery || 
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const departments = [...new Set(employeesWithAccess.map(e => e.department).filter(Boolean))];

  if (!canManage) {
    return (
      <div className="p-6">
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-6 text-center">
            <Shield className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-red-700">Access Denied</h2>
            <p className="text-red-600 mt-2">Only HR Managers and Admins can access this page.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="employee-access-permissions">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Employee Access & Permissions
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Manage portal access, passwords, and module-level permissions
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
              data-testid="search-input"
            />
          </div>
          {activeTab === 'access' && (
            <select
              value={filterDepartment}
              onChange={(e) => setFilterDepartment(e.target.value)}
              className="h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm"
            >
              <option value="">All Departments</option>
              {departments.map(dept => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 max-w-md">
          <TabsTrigger value="access" data-testid="tab-access">
            <Key className="w-4 h-4 mr-2" />
            Portal Access
          </TabsTrigger>
          <TabsTrigger value="permissions" data-testid="tab-permissions">
            <Shield className="w-4 h-4 mr-2" />
            Permissions
          </TabsTrigger>
          <TabsTrigger value="approvals" data-testid="tab-approvals">
            <Clock className="w-4 h-4 mr-2" />
            Approvals
            {pendingChanges.length > 0 && (
              <Badge className="ml-2 bg-red-500">{pendingChanges.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* ==================== ACCESS TAB ==================== */}
        <TabsContent value="access" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="w-5 h-5 text-blue-500" />
                Portal Access Management
              </CardTitle>
              <CardDescription>
                Grant, revoke, or reset access for employees
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingAccess ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Access Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAccessEmployees.map(emp => (
                      <TableRow key={emp.id} data-testid={`access-row-${emp.employee_id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-zinc-200 flex items-center justify-center text-xs font-medium">
                              {emp.first_name?.charAt(0)}
                            </div>
                            <div>
                              <div className="font-medium">{emp.first_name} {emp.last_name}</div>
                              <div className="text-xs text-zinc-500">{emp.email}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{emp.employee_id}</TableCell>
                        <TableCell>{emp.department || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{emp.role}</Badge>
                        </TableCell>
                        <TableCell>
                          {emp.has_access ? (
                            emp.is_active ? (
                              <Badge className="bg-emerald-100 text-emerald-700">
                                <CheckCircle className="w-3 h-3 mr-1" /> Active
                              </Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-700">
                                <XCircle className="w-3 h-3 mr-1" /> Disabled
                              </Badge>
                            )
                          ) : (
                            <Badge className="bg-zinc-100 text-zinc-600">No Access</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {emp.has_access ? (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => { setSelectedEmployee(emp); setResetDialog(true); }}
                                  title="Reset Password"
                                >
                                  <Key className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => { setSelectedEmployee(emp); setDisableDialog(true); }}
                                  title={emp.is_active ? 'Disable Access' : 'Enable Access'}
                                >
                                  {emp.is_active ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                                </Button>
                              </>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => { setSelectedEmployee(emp); setGrantAccessDialog(true); }}
                                title="Grant Access"
                              >
                                <UserCheck className="w-4 h-4 mr-1" /> Grant
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ==================== PERMISSIONS TAB ==================== */}
        <TabsContent value="permissions" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Employee List */}
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-sm">Select Employee</CardTitle>
              </CardHeader>
              <CardContent className="p-0 max-h-[500px] overflow-y-auto">
                {loadingPerms ? (
                  <div className="p-6 text-center">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-zinc-400" />
                  </div>
                ) : (
                  <div className="divide-y">
                    {filteredPermEmployees.map(emp => (
                      <button
                        key={emp.id}
                        onClick={() => { setSelectedEmployee(emp); setEditMode(false); }}
                        className={`w-full p-3 text-left hover:bg-zinc-50 transition-colors ${
                          selectedEmployee?.id === emp.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                        }`}
                        data-testid={`perm-employee-${emp.employee_id}`}
                      >
                        <div className="font-medium text-sm">{emp.first_name} {emp.last_name}</div>
                        <div className="text-xs text-zinc-500">{emp.employee_id} • {emp.department}</div>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Permissions Editor */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-purple-500" />
                    Module Permissions
                    {selectedEmployee && (
                      <span className="text-zinc-500 font-normal text-sm">
                        - {selectedEmployee.first_name} {selectedEmployee.last_name}
                      </span>
                    )}
                  </CardTitle>
                  {selectedEmployee && (
                    <div className="flex gap-2">
                      {editMode ? (
                        <>
                          <Button variant="outline" size="sm" onClick={() => { setEditMode(false); setPermissions(originalPermissions); }}>
                            Cancel
                          </Button>
                          {isAdmin ? (
                            <Button size="sm" onClick={() => savePermissionsMutation.mutate()}>
                              <Save className="w-4 h-4 mr-1" /> Save
                            </Button>
                          ) : (
                            <Button size="sm" onClick={() => setShowApprovalDialog(true)}>
                              <Send className="w-4 h-4 mr-1" /> Submit for Approval
                            </Button>
                          )}
                        </>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                          <Edit className="w-4 h-4 mr-1" /> Edit
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {!selectedEmployee ? (
                  <div className="text-center py-12 text-zinc-500">
                    <User className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
                    <p>Select an employee to view/edit permissions</p>
                  </div>
                ) : permissionsLoading ? (
                  <div className="text-center py-12">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto text-zinc-400" />
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Role Selection */}
                    <div className="flex items-center gap-4 p-4 bg-zinc-50 rounded-lg">
                      <Label className="text-sm font-medium">Assigned Role:</Label>
                      <Select value={assignedRole} onValueChange={setAssignedRole} disabled={!editMode}>
                        <SelectTrigger className="w-[200px]">
                          <SelectValue placeholder="Select role" />
                        </SelectTrigger>
                        <SelectContent>
                          {roles.map(role => (
                            <SelectItem key={role.id || role.name} value={role.name}>
                              {role.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Module Permissions Grid */}
                    {MODULES.map(mod => {
                      const ModIcon = mod.icon;
                      return (
                        <div key={mod.id} className="border rounded-lg overflow-hidden">
                          <div className="bg-zinc-50 px-4 py-2 flex items-center gap-2 border-b">
                            <ModIcon className="w-4 h-4 text-zinc-600" />
                            <span className="font-medium text-sm">{mod.name}</span>
                          </div>
                          <div className="p-4">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="text-zinc-500">
                                  <th className="text-left py-1">Feature</th>
                                  {ACTIONS.map(action => (
                                    <th key={action} className="text-center py-1 capitalize">{action}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {mod.features.map(feature => (
                                  <tr key={feature} className="border-t">
                                    <td className="py-2 capitalize">{feature.replace(/_/g, ' ')}</td>
                                    {ACTIONS.map(action => (
                                      <td key={action} className="text-center">
                                        <Switch
                                          checked={permissions[mod.id]?.[feature]?.[action] || false}
                                          onCheckedChange={() => togglePermission(mod.id, feature, action)}
                                          disabled={!editMode}
                                          className="scale-75"
                                        />
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ==================== APPROVALS TAB ==================== */}
        <TabsContent value="approvals" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-500" />
                Pending Permission Requests
              </CardTitle>
              <CardDescription>
                Review and approve/reject permission change requests
              </CardDescription>
            </CardHeader>
            <CardContent>
              {pendingChanges.length === 0 ? (
                <div className="text-center py-12 text-zinc-500">
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 text-emerald-300" />
                  <p>No pending approval requests</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {pendingChanges.map(request => (
                    <Card key={request.id} className="border-amber-200 bg-amber-50/50">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-medium">{request.employee_name || request.employee_id}</div>
                            <div className="text-sm text-zinc-500">
                              Requested role: <Badge variant="outline">{request.requested_role}</Badge>
                            </div>
                            {request.notes && (
                              <div className="text-sm text-zinc-600 mt-2 italic">"{request.notes}"</div>
                            )}
                            <div className="text-xs text-zinc-400 mt-2">
                              Requested: {new Date(request.created_at).toLocaleDateString()}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600 border-red-300 hover:bg-red-50"
                              onClick={() => rejectRequestMutation.mutate(request.id)}
                            >
                              <XCircle className="w-4 h-4 mr-1" /> Reject
                            </Button>
                            <Button
                              size="sm"
                              className="bg-emerald-600 hover:bg-emerald-700"
                              onClick={() => approveRequestMutation.mutate(request.id)}
                            >
                              <CheckCircle className="w-4 h-4 mr-1" /> Approve
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ==================== DIALOGS ==================== */}
      
      {/* Reset Password Dialog */}
      <Dialog open={resetDialog} onOpenChange={setResetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Reset password for {selectedEmployee?.first_name} {selectedEmployee?.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>New Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder={`Default: Welcome@${selectedEmployee?.employee_id}`}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
              <p className="text-xs text-zinc-500">Leave empty to use default password</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetDialog(false)}>Cancel</Button>
            <Button onClick={handleResetPassword}>Reset Password</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Toggle Access Dialog */}
      <Dialog open={disableDialog} onOpenChange={setDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedEmployee?.is_active ? 'Disable' : 'Enable'} Access
            </DialogTitle>
            <DialogDescription>
              {selectedEmployee?.is_active 
                ? `This will prevent ${selectedEmployee?.first_name} from logging in.`
                : `This will allow ${selectedEmployee?.first_name} to log in again.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisableDialog(false)}>Cancel</Button>
            <Button 
              onClick={handleToggleAccess}
              className={selectedEmployee?.is_active ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}
            >
              {selectedEmployee?.is_active ? 'Disable Access' : 'Enable Access'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Grant Access Dialog */}
      <Dialog open={grantAccessDialog} onOpenChange={setGrantAccessDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Grant Portal Access</DialogTitle>
            <DialogDescription>
              Grant system access to {selectedEmployee?.first_name} {selectedEmployee?.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={grantAccessForm.role} onValueChange={(v) => setGrantAccessForm(p => ({ ...p, role: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="consultant">Consultant</SelectItem>
                  <SelectItem value="sales_executive">Sales Executive</SelectItem>
                  <SelectItem value="hr_executive">HR Executive</SelectItem>
                  <SelectItem value="hr_manager">HR Manager</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Initial Password</Label>
              <Input
                value={grantAccessForm.password}
                onChange={(e) => setGrantAccessForm(p => ({ ...p, password: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGrantAccessDialog(false)}>Cancel</Button>
            <Button onClick={handleGrantAccess}>Grant Access</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Submit for Approval Dialog */}
      <Dialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit for Approval</DialogTitle>
            <DialogDescription>
              Permission changes require admin approval
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Textarea
                value={approvalNote}
                onChange={(e) => setApprovalNote(e.target.value)}
                placeholder="Reason for permission change..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApprovalDialog(false)}>Cancel</Button>
            <Button onClick={() => submitApprovalMutation.mutate()}>Submit Request</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmployeeAccessPermissions;
