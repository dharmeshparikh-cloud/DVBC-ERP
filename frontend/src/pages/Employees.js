import React, { useState, useEffect, useContext, useMemo } from 'react';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Users, Plus, Search, Building2, UserCheck, UserX, Edit2, Eye, 
  FileText, Download, Trash2, Link2, Unlink, Lock, Key,
  BarChart3, Mail, Phone, Briefcase, Smartphone, MapPin, QrCode,
  AlertTriangle, ShieldAlert
} from 'lucide-react';
import { toast } from 'sonner';
import ViewToggle from '../components/ViewToggle';
import MobileAppWidget from '../components/MobileAppWidget';
import PageHeader from '../components/ui/page-header';
import { useQueryClient } from '@tanstack/react-query';
import {
  useAllEmployees,
  useDepartmentsList,
  useEmployeeStats,
  useOrgChart,
  useEmployee,
  useUpdateEmployee,
  useDeleteEmployee,
  useLinkEmployeeToUser,
  useGrantEmployeeAccess,
  useRevokeEmployeeAccess,
  useUnlinkEmployeeFromUser,
  useUpdateMobileAccess
} from '../hooks/useEmployees';
import { useUsersWithRoles } from '../hooks/useUserManagement';
import { isAdmin as checkIsAdmin, isHRManager as checkIsHRManager, canManageEmployees } from '../utils/roles';

const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
  { value: 'part_time', label: 'Part Time' }
];

const DOCUMENT_TYPES = [
  { value: 'id_proof', label: 'ID Proof' },
  { value: 'offer_letter', label: 'Offer Letter' },
  { value: 'resume', label: 'Resume' },
  { value: 'contract', label: 'Contract' },
  { value: 'other', label: 'Other' }
];

const Employees = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  const [filterJoinDate, setFilterJoinDate] = useState(''); // New Joiners filter
  const [activeView, setActiveView] = useState('directory'); // directory, orgchart
  const [viewMode, setViewMode] = useState('list'); // list, card (for directory tab)
  
  // Auto-switch to card view on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setViewMode('card');
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Dialogs
  const [viewDialog, setViewDialog] = useState(false);
  const [editDialog, setEditDialog] = useState(false);
  const [linkUserDialog, setLinkUserDialog] = useState(false);
  const [grantAccessDialog, setGrantAccessDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [urlEditSection, setUrlEditSection] = useState(null); // Track section to highlight from URL
  
  // Grant access form
  const [accessFormData, setAccessFormData] = useState({
    role: 'consultant',
    password: 'Welcome@123'
  });

  // Form data
  const [formData, setFormData] = useState({
    employee_id: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    personal_email: '',
    department: '',
    designation: '',
    employment_type: 'full_time',
    joining_date: '',
    reporting_manager_id: '',
    salary: '',
    bank_details: {
      account_number: '',
      ifsc_code: '',
      bank_name: '',
      branch: '',
      account_holder_name: ''
    }
  });

  const isAdmin = checkIsAdmin(user);
  const isHRManager = checkIsHRManager(user);
  const canManage = canManageEmployees(user);

  // React Query: Fetch employees and departments using hooks
  const { data: employeesRaw = [], isLoading: empLoading, refetch: refetchEmployees } = useAllEmployees();
  const { data: departmentsData } = useDepartmentsList();
  const departments = Array.isArray(departmentsData) ? departmentsData : [];
  const { data: stats } = useEmployeeStats();
  const { data: usersWithRoles = [] } = useUsersWithRoles();
  const { data: orgChart } = useOrgChart({ enabled: activeView === 'orgchart' });
  
  // Wrap employees in expected format
  const employees = useMemo(() => employeesRaw, [employeesRaw]);
  const loading = empLoading;

  // React Query: Mutations
  const updateEmployeeMutation = useUpdateEmployee();
  const deleteEmployeeMutation = useDeleteEmployee();
  const linkUserMutation = useLinkEmployeeToUser();
  const grantAccessMutation = useGrantEmployeeAccess();
  const revokeAccessMutation = useRevokeEmployeeAccess();
  const unlinkUserMutation = useUnlinkEmployeeFromUser();
  const updateMobileAccessMutation = useUpdateMobileAccess();

  // Handle URL parameters for editing (from Go-Live Dashboard)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const editId = params.get('edit');
    const section = params.get('section');
    
    if (editId && employees.length > 0) {
      const emp = (employees || []).find(e => e.id === editId || e.employee_id === editId);
      if (emp) {
        setSelectedEmployee(emp);
        setEditDialog(true);
        setUrlEditSection(section); // Store which section to highlight
        // Clear URL params after handling
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  }, [employees]);

  const handleUpdateEmployee = () => {
    if (!selectedEmployee) return;

    const payload = {
      id: selectedEmployee.id,
      ...formData,
      salary: formData.salary ? parseFloat(formData.salary) : null,
      joining_date: formData.joining_date ? new Date(formData.joining_date).toISOString() : null,
      bank_details: formData.bank_details.account_number ? formData.bank_details : null
    };

    updateEmployeeMutation.mutate(payload, {
      onSuccess: () => {
        toast.success('Employee updated successfully');
        setEditDialog(false);
        setSelectedEmployee(null);
      },
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to update employee')
    });
  };

  const handleDeleteEmployee = (employeeId) => {
    if (!window.confirm('Are you sure you want to delete this employee?')) return;

    deleteEmployeeMutation.mutate(employeeId, {
      onSuccess: () => toast.success('Employee deleted successfully'),
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to delete employee')
    });
  };

  const handleLinkUser = (userId) => {
    linkUserMutation.mutate({ employeeId: selectedEmployee.id, userId }, {
      onSuccess: () => {
        toast.success('User linked successfully');
        setLinkUserDialog(false);
      },
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to link user')
    });
  };

  const handleGrantAccess = () => {
    grantAccessMutation.mutate({
      employeeId: selectedEmployee.id,
      role: accessFormData.role,
      password: accessFormData.password
    }, {
      onSuccess: (data) => {
        toast.success(`Portal access granted! User ID: ${data.user?.employee_id || selectedEmployee.employee_id}`);
        setGrantAccessDialog(false);
      },
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to grant access')
    });
  };

  const handleRevokeAccess = (employeeId) => {
    if (!window.confirm('Are you sure you want to revoke portal access?')) return;

    revokeAccessMutation.mutate(employeeId, {
      onSuccess: () => toast.success('Access revoked'),
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to revoke access')
    });
  };

  const handleUnlinkUser = (employeeId) => {
    if (!window.confirm('Unlink this employee from their user account?')) return;

    unlinkUserMutation.mutate(employeeId, {
      onSuccess: () => toast.success('User unlinked'),
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to unlink user')
    });
  };

  const handleToggleMobileAccess = (employeeId, currentEnabled) => {
    const newEnabled = !currentEnabled;

    updateMobileAccessMutation.mutate({ employeeId, mobileEnabled: newEnabled }, {
      onSuccess: () => toast.success(`Mobile access ${newEnabled ? 'enabled' : 'disabled'}`),
      onError: (error) => toast.error(error.response?.data?.detail || 'Failed to update mobile access')
    });
  };

  const openEditDialog = (emp) => {
    setSelectedEmployee(emp);
    setFormData({
      employee_id: emp.employee_id,
      first_name: emp.first_name,
      last_name: emp.last_name,
      email: emp.email,
      phone: emp.phone || '',
      personal_email: emp.personal_email || '',
      department: emp.department || '',
      designation: emp.designation || '',
      employment_type: emp.employment_type || 'full_time',
      joining_date: emp.joining_date ? emp.joining_date.split('T')[0] : '',
      reporting_manager_id: emp.reporting_manager_id || '',
      salary: emp.salary || '',
      bank_details: emp.bank_details || {
        account_number: '',
        ifsc_code: '',
        bank_name: '',
        branch: '',
        account_holder_name: ''
      },
      // Governance fields - used to determine if employee is protected
      onboarding_status: emp.onboarding_status,
      has_portal_access: emp.has_portal_access,
      go_live_status: emp.go_live_status
    });
    setEditDialog(true);
  };

  const openViewDialog = (emp) => {
    // Use cached employee data directly, full details can be fetched if needed
    setSelectedEmployee(emp);
    setViewDialog(true);
  };

  const filteredEmployees = (employees || []).filter(emp => {
    const matchesSearch = !searchTerm || 
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = !filterDepartment || emp.department === filterDepartment;
    
    // New Joiners filter by joining date
    let matchesJoinDate = true;
    if (filterJoinDate) {
      const joiningDate = new Date(emp.joining_date || emp.created_at);
      const today = new Date();
      const daysAgo = new Date();
      
      switch (filterJoinDate) {
        case '7':
          daysAgo.setDate(today.getDate() - 7);
          matchesJoinDate = joiningDate >= daysAgo;
          break;
        case '30':
          daysAgo.setDate(today.getDate() - 30);
          matchesJoinDate = joiningDate >= daysAgo;
          break;
        case '90':
          daysAgo.setDate(today.getDate() - 90);
          matchesJoinDate = joiningDate >= daysAgo;
          break;
        default:
          matchesJoinDate = true;
      }
    }
    
    return matchesSearch && matchesDept && matchesJoinDate;
  });

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="employees-page">
      <PageHeader title="Employees" subtitle="Manage employee records and organizational structure" onRefresh={() => refetchEmployees()} loading={empLoading} />

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Total Employees</p>
                  <p className="text-2xl font-semibold text-zinc-950">{stats.total || stats.active || 0}</p>
                </div>
                <Users className="w-8 h-8 text-zinc-300" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">With System Access</p>
                  <p className="text-2xl font-semibold text-emerald-600">{stats.with_portal_access || 0}</p>
                </div>
                <UserCheck className="w-8 h-8 text-emerald-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">No System Access</p>
                  <p className="text-2xl font-semibold text-amber-600">{stats.without_portal_access || 0}</p>
                </div>
                <UserX className="w-8 h-8 text-amber-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Departments</p>
                  <p className="text-2xl font-semibold text-zinc-950">{Object.keys(stats.by_department || {}).length}</p>
                </div>
                <Building2 className="w-8 h-8 text-zinc-300" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* View Tabs and Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex border-b border-zinc-200">
          <button
            onClick={() => setActiveView('directory')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeView === 'directory' 
                ? 'border-zinc-950 text-zinc-950' 
                : 'border-transparent text-zinc-500 hover:text-zinc-950'
            }`}
            data-testid="tab-directory"
          >
            <Users className="w-4 h-4 inline mr-2" />
            Directory ({employees.length})
          </button>
          <button
            onClick={() => setActiveView('orgchart')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeView === 'orgchart' 
                ? 'border-zinc-950 text-zinc-950' 
                : 'border-transparent text-zinc-500 hover:text-zinc-950'
            }`}
            data-testid="tab-orgchart"
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            Org Chart
          </button>
        </div>
        
        {canManage && (
          <div className="flex items-center gap-2">
            <MobileAppWidget compact />
          </div>
        )}
      </div>

      {/* Directory View */}
      {activeView === 'directory' && (
        <>
          {/* Search and Filters */}
          <div className="flex items-center justify-between mb-6 gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search employees..."
                  className="pl-10 rounded-sm"
                />
              </div>
              <select
                value={filterDepartment}
                onChange={(e) => setFilterDepartment(e.target.value)}
                className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                data-testid="filter-department"
              >
                <option value="">All Departments</option>
                {(departments || []).map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
              <select
                value={filterJoinDate}
                onChange={(e) => setFilterJoinDate(e.target.value)}
                className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                data-testid="filter-join-date"
              >
                <option value="">All Joining Dates</option>
                <option value="7">Last 7 Days</option>
                <option value="30">Last 30 Days</option>
                <option value="90">Last 90 Days</option>
              </select>
              {filterJoinDate && (
                <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded">
                  New Joiners: {filteredEmployees.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <ViewToggle viewMode={viewMode} onChange={setViewMode} />
            </div>
          </div>

          {/* Employees Display */}
          {viewMode === 'list' ? (
            /* List View (Table) */
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-0">
                <table className="w-full">
                  <thead>
                    <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                      <th className="px-4 py-3 text-left">Employee</th>
                      <th className="px-4 py-3 text-left">ID</th>
                      <th className="px-4 py-3 text-left">Department</th>
                      <th className="px-4 py-3 text-left">Designation</th>
                      <th className="px-4 py-3 text-left">Type</th>
                      <th className="px-4 py-3 text-left">Mobile App</th>
                      <th className="px-4 py-3 text-left">System Access</th>
                      {canManage && <th className="px-4 py-3 text-left">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {(filteredEmployees || []).map(emp => (
                      <tr key={emp.id} className="border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer" onClick={() => openViewDialog(emp)} data-testid={`employee-row-${emp.id}`}>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-zinc-200 flex items-center justify-center text-xs font-medium text-zinc-600">
                              {emp.first_name?.charAt(0)?.toUpperCase()}
                            </div>
                            <div>
                              <span className="font-medium text-zinc-900">{emp.first_name} {emp.last_name}</span>
                              <div className="text-xs text-zinc-500">{emp.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-zinc-600">{emp.employee_id}</td>
                        <td className="px-4 py-3 text-sm text-zinc-600">{emp.department || '-'}</td>
                        <td className="px-4 py-3 text-sm text-zinc-600">{emp.designation || '-'}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 text-xs rounded ${
                            emp.employment_type === 'full_time' ? 'bg-blue-100 text-blue-700' :
                            emp.employment_type === 'contract' ? 'bg-amber-100 text-amber-700' :
                            emp.employment_type === 'intern' ? 'bg-purple-100 text-purple-700' :
                            'bg-zinc-100 text-zinc-700'
                          }`}>
                            {emp.employment_type?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-1.5">
                            <Smartphone className={`w-3.5 h-3.5 ${emp.mobile_app_disabled ? 'text-red-400' : 'text-emerald-500'}`} />
                            <span className={`text-xs ${emp.mobile_app_disabled ? 'text-red-600' : 'text-emerald-600'}`}>
                              {emp.mobile_app_disabled ? 'Disabled' : 'Enabled'}
                            </span>
                            {canManage && (
                              <Button
                                onClick={() => handleToggleMobileAccess(emp.id, emp.mobile_app_disabled)}
                                variant="ghost"
                                size="sm"
                                className={`h-5 px-1.5 text-[10px] ml-1 ${emp.mobile_app_disabled ? 'text-emerald-600 hover:bg-emerald-50' : 'text-red-600 hover:bg-red-50'}`}
                                title={emp.mobile_app_disabled ? 'Enable mobile access' : 'Disable mobile access'}
                              >
                                {emp.mobile_app_disabled ? 'Enable' : 'Disable'}
                              </Button>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          {emp.user_id ? (
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-1 text-xs bg-emerald-100 text-emerald-700 rounded">{emp.role || 'Active'}</span>
                              {canManage && (
                                <Button
                                  onClick={() => handleRevokeAccess(emp.id)}
                                  variant="destructive"
                                  size="sm"
                                  className="h-6 px-2 bg-red-500 hover:bg-red-600 text-white"
                                  title="Revoke all system access"
                                  data-testid={`revoke-access-${emp.employee_id}`}
                                >
                                  <UserX className="w-3 h-3 mr-1" />
                                  <span className="text-xs">Revoke</span>
                                </Button>
                              )}
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-zinc-400">No access</span>
                              {canManage && (
                                <Button
                                  onClick={() => { setSelectedEmployee(emp); setGrantAccessDialog(true); }}
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-600"
                                  title="Grant system access"
                                >
                                  <UserCheck className="w-3 h-3 mr-1" />
                                  <span className="text-xs">Grant Access</span>
                                </Button>
                              )}
                            </div>
                          )}
                        </td>
                        {canManage && (
                          <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1">
                              <Button onClick={() => openViewDialog(emp)} variant="ghost" size="sm" className="h-8 w-8 p-0">
                                <Eye className="w-4 h-4 text-zinc-500" />
                              </Button>
                              <Button onClick={() => openEditDialog(emp)} variant="ghost" size="sm" className="h-8 w-8 p-0" data-testid={`edit-emp-${emp.employee_id}`}>
                                <Edit2 className="w-4 h-4 text-zinc-500" />
                              </Button>
                              {isAdmin && (
                                <Button onClick={() => handleDeleteEmployee(emp.id)} variant="ghost" size="sm" className="h-8 w-8 p-0">
                                  <Trash2 className="w-4 h-4 text-red-500" />
                                </Button>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredEmployees.length === 0 && (
                  <div className="text-center py-12 text-zinc-400">
                    {employees.length === 0 ? 'No employees yet. Click "Sync from Users" or "Add Employee" to get started.' : 'No employees match your search.'}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            /* Card View */
            filteredEmployees.length === 0 ? (
              <Card className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="text-center py-12 text-zinc-400">
                  {employees.length === 0 ? 'No employees yet. Click "Sync from Users" or "Add Employee" to get started.' : 'No employees match your search.'}
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(filteredEmployees || []).map(emp => (
                  <Card 
                    key={emp.id} 
                    className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                    onClick={() => openViewDialog(emp)}
                    data-testid={`employee-card-${emp.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-full bg-zinc-200 flex items-center justify-center text-lg font-medium text-zinc-600 flex-shrink-0">
                          {emp.first_name?.charAt(0)?.toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className="font-medium text-zinc-900 truncate">{emp.first_name} {emp.last_name}</h3>
                            <span className={`px-2 py-0.5 text-xs rounded flex-shrink-0 ${
                              emp.employment_type === 'full_time' ? 'bg-blue-100 text-blue-700' :
                              emp.employment_type === 'contract' ? 'bg-amber-100 text-amber-700' :
                              emp.employment_type === 'intern' ? 'bg-purple-100 text-purple-700' :
                              'bg-zinc-100 text-zinc-700'
                            }`}>
                              {emp.employment_type?.replace('_', ' ')}
                            </span>
                          </div>
                          <p className="text-sm text-zinc-600 mb-2">{emp.designation || 'No designation'}</p>
                          <div className="space-y-1 text-sm text-zinc-500">
                            {emp.department && (
                              <div className="flex items-center gap-2">
                                <Building2 className="w-3.5 h-3.5" />
                                <span className="truncate">{emp.department}</span>
                              </div>
                            )}
                            <div className="flex items-center gap-2">
                              <Mail className="w-3.5 h-3.5" />
                              <span className="truncate">{emp.email}</span>
                            </div>
                            {emp.phone && (
                              <div className="flex items-center gap-2">
                                <Phone className="w-3.5 h-3.5" />
                                <span>{emp.phone}</span>
                              </div>
                            )}
                          </div>
                          <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-100">
                            <span className="text-xs text-zinc-400">{emp.employee_id}</span>
                            {emp.user_id ? (
                              <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded">{emp.role || 'System Access'}</span>
                            ) : (
                              <span className="text-xs text-zinc-400">No access</span>
                            )}
                          </div>
                        </div>
                      </div>
                      {canManage && (
                        <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-zinc-100" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center gap-1">
                            <Button onClick={() => openViewDialog(emp)} variant="ghost" size="sm" className="h-8 px-2">
                              <Eye className="w-4 h-4 text-zinc-500" />
                            </Button>
                            <Button onClick={() => openEditDialog(emp)} variant="ghost" size="sm" className="h-8 px-2">
                              <Edit2 className="w-4 h-4 text-zinc-500" />
                            </Button>
                          </div>
                          {emp.user_id ? (
                            <Button 
                              onClick={() => handleRevokeAccess(emp.id)} 
                              variant="destructive" 
                              size="sm" 
                              className="h-7 px-2 bg-red-500 hover:bg-red-600 text-white" 
                              title="Revoke system access"
                              data-testid={`card-revoke-${emp.employee_id}`}
                            >
                              <UserX className="w-3.5 h-3.5 mr-1" />
                              <span className="text-xs">Revoke Access</span>
                            </Button>
                          ) : (
                            <Button onClick={() => { setSelectedEmployee(emp); setGrantAccessDialog(true); }} variant="ghost" size="sm" className="h-8 px-2 bg-emerald-50 hover:bg-emerald-100" title="Grant system access">
                              <UserCheck className="w-4 h-4 text-emerald-600" />
                            </Button>
                          )}
                          {isAdmin && (
                            <Button onClick={() => handleDeleteEmployee(emp.id)} variant="ghost" size="sm" className="h-8 px-2">
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )
          )}
        </>
      )}

      {/* Org Chart View */}
      {activeView === 'orgchart' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="border-b border-zinc-100">
            <CardTitle className="text-base font-semibold text-zinc-950">Organizational Hierarchy</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {!orgChart || orgChart.length === 0 ? (
              <div className="text-center py-12 text-zinc-400">
                No organizational structure found. Set reporting managers to build the hierarchy.
              </div>
            ) : (
              <div className="space-y-2">
                {(orgChart || []).map(node => (
                  <div key={node.id} className="p-3 border border-zinc-200 rounded-sm">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-zinc-200 flex items-center justify-center text-sm font-medium text-zinc-600">
                        {node.name?.charAt(0)?.toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium text-zinc-900">{node.name}</div>
                        <div className="text-xs text-zinc-500">{node.designation || 'No designation'} • {node.department || 'No dept'}</div>
                      </div>
                      {node.has_user_access && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded">System Access</span>
                      )}
                      {node.children?.length > 0 && (
                        <span className="ml-auto text-xs text-zinc-400">{node.children.length} direct report(s)</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Edit Employee Dialog */}
      <Dialog open={editDialog} onOpenChange={setEditDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Edit Employee</DialogTitle>
          </DialogHeader>
          <EmployeeForm 
            formData={formData} 
            setFormData={setFormData} 
            employees={(employees || []).filter(e => e.id !== selectedEmployee?.id)}
            onSubmit={handleUpdateEmployee}
            onCancel={() => setEditDialog(false)}
            submitLabel="Update Employee"
            isEdit
          />
        </DialogContent>
      </Dialog>

      {/* View Employee Dialog */}
      <Dialog open={viewDialog} onOpenChange={setViewDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Employee Details</DialogTitle>
          </DialogHeader>
          {selectedEmployee && (
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-zinc-500">Employee ID</Label>
                  <p className="font-medium">{selectedEmployee.employee_id}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Name</Label>
                  <p className="font-medium">{selectedEmployee.first_name} {selectedEmployee.last_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Email</Label>
                  <p className="font-medium">{selectedEmployee.email}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Phone</Label>
                  <p className="font-medium">{selectedEmployee.phone || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Department</Label>
                  <p className="font-medium">{selectedEmployee.department || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Designation</Label>
                  <p className="font-medium">{selectedEmployee.designation || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Employment Type</Label>
                  <p className="font-medium capitalize">{selectedEmployee.employment_type?.replace('_', ' ')}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Joining Date</Label>
                  <p className="font-medium">{selectedEmployee.joining_date ? new Date(selectedEmployee.joining_date).toLocaleDateString() : '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Reporting Manager</Label>
                  <p className="font-medium">{selectedEmployee.reporting_manager_name || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">System Role</Label>
                  <p className="font-medium">{selectedEmployee.role || 'No system access'}</p>
                </div>
              </div>

              {/* Mobile App Access */}
              <div className="border-t border-zinc-100 pt-4">
                <h4 className="font-medium text-zinc-950 mb-3">Mobile App Access</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-zinc-500">Status</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Smartphone className={`w-4 h-4 ${selectedEmployee.mobile_app_disabled ? 'text-red-500' : 'text-emerald-500'}`} />
                      <span className={`font-medium ${selectedEmployee.mobile_app_disabled ? 'text-red-600' : 'text-emerald-600'}`}>
                        {selectedEmployee.mobile_app_disabled ? 'Disabled' : 'Enabled'}
                      </span>
                    </div>
                  </div>
                  {selectedEmployee.mobile_app_disabled && selectedEmployee.mobile_app_disabled_reason && (
                    <div>
                      <Label className="text-xs text-zinc-500">Reason</Label>
                      <p className="font-medium text-red-600">{selectedEmployee.mobile_app_disabled_reason}</p>
                    </div>
                  )}
                  {selectedEmployee.work_location && (
                    <div>
                      <Label className="text-xs text-zinc-500">Current Work Location</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <MapPin className="w-4 h-4 text-zinc-400" />
                        <span className="font-medium capitalize">{selectedEmployee.work_location?.replace('_', ' ') || '-'}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* HR Details (if visible) */}
              {selectedEmployee.salary !== undefined && (
                <div className="border-t border-zinc-100 pt-4">
                  <h4 className="font-medium text-zinc-950 mb-3">HR Details</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-zinc-500">Salary</Label>
                      <p className="font-medium">{selectedEmployee.salary ? `₹${selectedEmployee.salary.toLocaleString()}` : '-'}</p>
                    </div>
                    {selectedEmployee.bank_details && (
                      <>
                        <div>
                          <Label className="text-xs text-zinc-500">Bank Name</Label>
                          <p className="font-medium">{selectedEmployee.bank_details.bank_name || '-'}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-zinc-500">Account Number</Label>
                          <p className="font-medium">{selectedEmployee.bank_details.account_number || '-'}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-zinc-500">IFSC Code</Label>
                          <p className="font-medium">{selectedEmployee.bank_details.ifsc_code || '-'}</p>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Leave Balance */}
              {selectedEmployee.leave_balance && (
                <div className="border-t border-zinc-100 pt-4">
                  <h4 className="font-medium text-zinc-950 mb-3">Leave Balance</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-zinc-50 rounded-sm">
                      <p className="text-xs text-zinc-500">Casual Leave</p>
                      <p className="text-lg font-semibold">{selectedEmployee.leave_balance.casual_leave - selectedEmployee.leave_balance.used_casual}/{selectedEmployee.leave_balance.casual_leave}</p>
                    </div>
                    <div className="text-center p-3 bg-zinc-50 rounded-sm">
                      <p className="text-xs text-zinc-500">Sick Leave</p>
                      <p className="text-lg font-semibold">{selectedEmployee.leave_balance.sick_leave - selectedEmployee.leave_balance.used_sick}/{selectedEmployee.leave_balance.sick_leave}</p>
                    </div>
                    <div className="text-center p-3 bg-zinc-50 rounded-sm">
                      <p className="text-xs text-zinc-500">Earned Leave</p>
                      <p className="text-lg font-semibold">{selectedEmployee.leave_balance.earned_leave - selectedEmployee.leave_balance.used_earned}/{selectedEmployee.leave_balance.earned_leave}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Documents */}
              {selectedEmployee.documents?.length > 0 && (
                <div className="border-t border-zinc-100 pt-4">
                  <h4 className="font-medium text-zinc-950 mb-3">Documents</h4>
                  <div className="space-y-2">
                    {(selectedEmployee?.documents || []).map(doc => (
                      <div key={doc.id} className="flex items-center justify-between p-2 bg-zinc-50 rounded-sm">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-zinc-400" />
                          <span className="text-sm">{doc.original_filename}</span>
                          <span className="text-xs text-zinc-400">({doc.document_type})</span>
                        </div>
                        <Button variant="ghost" size="sm" className="h-6 p-0">
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Link User Dialog */}
      <Dialog open={linkUserDialog} onOpenChange={setLinkUserDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Link to User Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-zinc-600">
              Select a user account to give <strong>{selectedEmployee?.first_name} {selectedEmployee?.last_name}</strong> system access.
            </p>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {(usersWithRoles || []).filter(u => !(employees || []).some(e => e.user_id === u.id)).map(u => (
                <div 
                  key={u.id}
                  onClick={() => handleLinkUser(u.id)}
                  className="flex items-center justify-between p-3 border border-zinc-200 rounded-sm hover:bg-zinc-50 cursor-pointer"
                >
                  <div>
                    <p className="font-medium text-zinc-900">{u.full_name}</p>
                    <p className="text-xs text-zinc-500">{u.email} • {u.role}</p>
                  </div>
                  <Link2 className="w-4 h-4 text-zinc-400" />
                </div>
              ))}
            </div>
            {(usersWithRoles || []).filter(u => !(employees || []).some(e => e.user_id === u.id)).length === 0 && (
              <p className="text-center py-4 text-zinc-400">All users are already linked to employees.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Grant System Access Dialog */}
      <Dialog open={grantAccessDialog} onOpenChange={setGrantAccessDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Grant System Access</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-zinc-600">
              Create login credentials for <strong>{selectedEmployee?.first_name} {selectedEmployee?.last_name}</strong>
            </p>
            
            <div className="p-3 bg-zinc-50 rounded-sm border border-zinc-200">
              <p className="text-sm"><span className="text-zinc-500">Email:</span> <strong>{selectedEmployee?.email}</strong></p>
            </div>

            <div className="space-y-2">
              <Label className="text-black">Role *</Label>
              <select
                value={accessFormData.role}
                onChange={(e) => setAccessFormData({ ...accessFormData, role: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm text-black"
              >
                <option value="consultant">Consultant</option>
                <option value="senior_consultant">Senior Consultant</option>
                <option value="lead_consultant">Lead Consultant</option>
                <option value="principal_consultant">Principal Consultant</option>
                <option value="project_manager">Project Manager</option>
                <option value="hr_executive">HR Executive</option>
                <option value="hr_manager">HR Manager</option>
                <option value="sales_manager">Sales Manager</option>
                <option value="executive">Sales Executive</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label className="text-black">Temporary Password *</Label>
              <Input
                type="text"
                value={accessFormData.password}
                onChange={(e) => setAccessFormData({ ...accessFormData, password: e.target.value })}
                placeholder="Welcome@123"
                className="rounded-sm text-black"
              />
              <p className="text-xs text-zinc-500">Employee should change this password after first login.</p>
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button variant="outline" onClick={() => setGrantAccessDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleGrantAccess} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                <UserCheck className="w-4 h-4 mr-2" />
                Grant Access
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Employee Form Component
const EmployeeForm = ({ formData, setFormData, employees, onSubmit, onCancel, submitLabel, isEdit }) => {
  // Check if employee is onboarded/go-live (protected mode)
  const isProtectedEmployee = isEdit && (formData.onboarding_status === 'completed' || formData.has_portal_access || formData.go_live_status === 'active');
  
  return (
    <div className="space-y-6">
      {/* Governance Warning for Onboarded Employees */}
      {isProtectedEmployee && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">Protected Employee Record</p>
              <p className="mt-1 text-amber-700">This employee has completed onboarding. Some fields are locked and require specific workflows:</p>
              <ul className="mt-2 space-y-1 text-amber-700 text-xs">
                <li>• <strong>Salary/CTC:</strong> Use CTC Designer to modify compensation</li>
                <li>• <strong>Department:</strong> Use Transfer workflow</li>
                <li>• <strong>Designation:</strong> Use Promotion workflow</li>
                <li>• <strong>Reporting Manager:</strong> Use Hierarchy Change request</li>
              </ul>
            </div>
          </div>
        </div>
      )}
      
      {/* Basic Info */}
      <div>
        <h4 className="font-medium text-zinc-950 mb-3">Basic Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Employee ID *</Label>
            <Input
              value={formData.employee_id}
              onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
              placeholder="EMP001"
              className="rounded-sm"
              disabled={isEdit}
            />
          </div>
          <div className="space-y-2">
            <Label>Employment Type</Label>
            <select
              value={formData.employment_type}
              onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
              className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
            >
              {EMPLOYMENT_TYPES.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>First Name *</Label>
            <Input
              value={formData.first_name}
              onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              placeholder="John"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Last Name *</Label>
            <Input
              value={formData.last_name}
              onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              placeholder="Doe"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Work Email *</Label>
            <Input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="john@company.com"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Phone</Label>
            <Input
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+91 98765 43210"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Personal Email</Label>
            <Input
              type="email"
              value={formData.personal_email}
              onChange={(e) => setFormData({ ...formData, personal_email: e.target.value })}
              placeholder="john.personal@gmail.com"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Joining Date</Label>
            <Input
              type="date"
              value={formData.joining_date}
              onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })}
              className="rounded-sm"
            />
          </div>
        </div>
      </div>

      {/* Work Info - LOCKED FIELDS */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">
          Work Information
          {isProtectedEmployee && <span className="ml-2 text-xs font-normal text-amber-600">(Requires workflow)</span>}
        </h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              Department
              {isProtectedEmployee && <Lock className="h-3 w-3 text-amber-600" />}
            </Label>
            <Input
              value={formData.department}
              onChange={(e) => !isProtectedEmployee && setFormData({ ...formData, department: e.target.value })}
              placeholder="Consulting"
              className={`rounded-sm ${isProtectedEmployee ? 'bg-zinc-100 cursor-not-allowed' : ''}`}
              disabled={isProtectedEmployee}
              title={isProtectedEmployee ? 'Use Transfer workflow to change department' : ''}
            />
            {isProtectedEmployee && (
              <p className="text-xs text-amber-600">Use Transfer workflow</p>
            )}
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              Designation
              {isProtectedEmployee && <Lock className="h-3 w-3 text-amber-600" />}
            </Label>
            <Input
              value={formData.designation}
              onChange={(e) => !isProtectedEmployee && setFormData({ ...formData, designation: e.target.value })}
              placeholder="Senior Consultant"
              className={`rounded-sm ${isProtectedEmployee ? 'bg-zinc-100 cursor-not-allowed' : ''}`}
              disabled={isProtectedEmployee}
              title={isProtectedEmployee ? 'Use Promotion workflow to change designation' : ''}
            />
            {isProtectedEmployee && (
              <p className="text-xs text-amber-600">Use Promotion workflow</p>
            )}
          </div>
          <div className="col-span-2 space-y-2">
            <Label className="flex items-center gap-2">
              Reporting Manager
              {isProtectedEmployee && <Lock className="h-3 w-3 text-amber-600" />}
            </Label>
            <select
              value={formData.reporting_manager_id}
              onChange={(e) => !isProtectedEmployee && setFormData({ ...formData, reporting_manager_id: e.target.value })}
              className={`w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm ${isProtectedEmployee ? 'bg-zinc-100 cursor-not-allowed' : ''}`}
              disabled={isProtectedEmployee}
              title={isProtectedEmployee ? 'Use Hierarchy Change workflow to change reporting manager' : ''}
            >
              <option value="">No reporting manager</option>
              {(employees || []).map(emp => (
                <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} ({emp.designation || emp.employee_id})</option>
              ))}
            </select>
            {isProtectedEmployee && (
              <p className="text-xs text-amber-600">Use Hierarchy Change workflow</p>
            )}
          </div>
        </div>
      </div>

      {/* HR Details - SALARY IS LOCKED */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">
          HR Details
          {isProtectedEmployee && <span className="ml-2 text-xs font-normal text-amber-600">(Use CTC Designer)</span>}
        </h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              Salary (Annual)
              {isProtectedEmployee && <Lock className="h-3 w-3 text-red-600" />}
            </Label>
            <div className="relative">
              <Input
                type="number"
                value={formData.salary}
                onChange={(e) => !isProtectedEmployee && setFormData({ ...formData, salary: e.target.value })}
                placeholder="1200000"
                className={`rounded-sm ${isProtectedEmployee ? 'bg-zinc-100 cursor-not-allowed pr-20' : ''}`}
                disabled={isProtectedEmployee}
                title={isProtectedEmployee ? 'Salary must be changed via CTC Designer' : ''}
              />
              {isProtectedEmployee && (
                <div className="absolute right-2 top-1/2 -translate-y-1/2">
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">LOCKED</span>
                </div>
              )}
            </div>
            {isProtectedEmployee && (
              <p className="text-xs text-red-600 font-medium">
                Salary changes must go through CTC Designer → Admin Approval → Auto-sync
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bank Details - REQUIRES APPROVAL */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">
          Bank Details
          {isProtectedEmployee && <span className="ml-2 text-xs font-normal text-orange-600">(Requires Admin approval)</span>}
        </h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Account Holder Name</Label>
            <Input
              value={formData.bank_details.account_holder_name}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, account_holder_name: e.target.value }
              })}
              placeholder="John Doe"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              Account Number
              {isProtectedEmployee && <ShieldAlert className="h-3 w-3 text-orange-600" />}
            </Label>
            <Input
              value={formData.bank_details.account_number}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, account_number: e.target.value }
              })}
              placeholder="1234567890"
              className="rounded-sm"
            />
            {isProtectedEmployee && (
              <p className="text-xs text-orange-600">Changes require Admin approval</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Bank Name</Label>
            <Input
              value={formData.bank_details.bank_name}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, bank_name: e.target.value }
              })}
              placeholder="HDFC Bank"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              IFSC Code
              {isProtectedEmployee && <ShieldAlert className="h-3 w-3 text-orange-600" />}
            </Label>
            <Input
              value={formData.bank_details.ifsc_code}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, ifsc_code: e.target.value }
              })}
              placeholder="HDFC0001234"
              className="rounded-sm"
            />
          </div>
          <div className="col-span-2 space-y-2">
            <Label>Branch</Label>
            <Input
              value={formData.bank_details.branch}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, branch: e.target.value }
              })}
              placeholder="Mumbai - Andheri West"
              className="rounded-sm"
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-zinc-100">
        <Button onClick={onCancel} variant="outline" className="flex-1 rounded-sm">
          Cancel
        </Button>
        <Button onClick={onSubmit} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
          {submitLabel}
        </Button>
      </div>
    </div>
  );
};

export default Employees;
