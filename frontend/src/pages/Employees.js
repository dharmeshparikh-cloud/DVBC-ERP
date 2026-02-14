import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Users, Plus, Search, Building2, UserCheck, UserX, Edit2, Eye, 
  FileText, Download, Trash2, ChevronRight, ChevronDown, Link2, Unlink,
  RefreshCw, BarChart3
} from 'lucide-react';
import { toast } from 'sonner';

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

// Simple Org Chart Node Component (non-recursive rendering to avoid stack overflow)
const OrgChartNodeSimple = ({ node, level = 0, expandedNodes, toggleNode }) => {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedNodes.has(node.id);

  return (
    <div className={`${level > 0 ? 'ml-8 border-l-2 border-zinc-200 pl-4' : ''}`}>
      <div 
        className="flex items-center gap-3 py-2 px-3 rounded-sm hover:bg-zinc-50 cursor-pointer"
        onClick={() => hasChildren && toggleNode(node.id)}
      >
        {hasChildren ? (
          isExpanded ? <ChevronDown className="w-4 h-4 text-zinc-400" /> : <ChevronRight className="w-4 h-4 text-zinc-400" />
        ) : (
          <div className="w-4" />
        )}
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
      </div>
      {isExpanded && hasChildren && (
        <div className="mt-1">
          {node.children.map(child => (
            <OrgChartNodeSimple 
              key={child.id} 
              node={child} 
              level={level + 1}
              expandedNodes={expandedNodes}
              toggleNode={toggleNode}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const Employees = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('');
  const [departments, setDepartments] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeView, setActiveView] = useState('directory'); // directory, orgchart
  const [orgChart, setOrgChart] = useState([]);

  // Dialogs
  const [createDialog, setCreateDialog] = useState(false);
  const [viewDialog, setViewDialog] = useState(false);
  const [editDialog, setEditDialog] = useState(false);
  const [linkUserDialog, setLinkUserDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

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

  const isAdmin = user?.role === 'admin';
  const isHRManager = user?.role === 'hr_manager';
  const canManage = isAdmin || isHRManager;

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [empRes, deptRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/employees/departments/list`)
      ]);
      setEmployees(empRes.data || []);
      setDepartments(deptRes.data || []);
      
      // Fetch stats if HR access
      if (canManage) {
        try {
          const statsRes = await axios.get(`${API}/employees/stats/summary`);
          setStats(statsRes.data);
        } catch (e) {
          console.error('Error fetching stats:', e);
        }
      }
      
      // Fetch users for linking
      try {
        const usersRes = await axios.get(`${API}/users-with-roles`);
        setUsers(usersRes.data || []);
      } catch (e) {
        console.error('Error fetching users:', e);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load employees');
    } finally {
      setLoading(false);
    }
  };

  const fetchOrgChart = async () => {
    try {
      const res = await axios.get(`${API}/employees/org-chart/hierarchy`);
      setOrgChart(res.data || []);
    } catch (error) {
      console.error('Error fetching org chart:', error);
      toast.error('Failed to load org chart');
    }
  };

  useEffect(() => {
    if (activeView === 'orgchart') {
      fetchOrgChart();
    }
  }, [activeView]);

  const generateEmployeeId = () => {
    const count = employees.length + 1;
    return `EMP${String(count).padStart(3, '0')}`;
  };

  const handleCreateEmployee = async () => {
    if (!formData.employee_id || !formData.first_name || !formData.last_name || !formData.email) {
      toast.error('Please fill in required fields');
      return;
    }

    try {
      const payload = {
        ...formData,
        salary: formData.salary ? parseFloat(formData.salary) : null,
        joining_date: formData.joining_date ? new Date(formData.joining_date).toISOString() : null,
        bank_details: formData.bank_details.account_number ? formData.bank_details : null
      };

      await axios.post(`${API}/employees`, payload);
      toast.success('Employee created successfully');
      setCreateDialog(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create employee');
    }
  };

  const handleUpdateEmployee = async () => {
    if (!selectedEmployee) return;

    try {
      const payload = {
        ...formData,
        salary: formData.salary ? parseFloat(formData.salary) : null,
        joining_date: formData.joining_date ? new Date(formData.joining_date).toISOString() : null,
        bank_details: formData.bank_details.account_number ? formData.bank_details : null
      };

      await axios.patch(`${API}/employees/${selectedEmployee.id}`, payload);
      toast.success('Employee updated successfully');
      setEditDialog(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update employee');
    }
  };

  const handleDeleteEmployee = async (employeeId) => {
    if (!window.confirm('Are you sure you want to deactivate this employee?')) return;

    try {
      await axios.delete(`${API}/employees/${employeeId}`);
      toast.success('Employee deactivated');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to deactivate employee');
    }
  };

  const handleLinkUser = async (userId) => {
    if (!selectedEmployee) return;

    try {
      await axios.post(`${API}/employees/${selectedEmployee.id}/link-user?user_id=${userId}`);
      toast.success('Employee linked to user');
      setLinkUserDialog(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to link user');
    }
  };

  const handleUnlinkUser = async (employeeId) => {
    if (!window.confirm('Remove system access link for this employee?')) return;

    try {
      await axios.post(`${API}/employees/${employeeId}/unlink-user`);
      toast.success('User unlinked');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unlink user');
    }
  };

  const handleSyncFromUsers = async () => {
    try {
      const res = await axios.post(`${API}/employees/sync-from-users`);
      toast.success(res.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to sync employees');
    }
  };

  const resetForm = () => {
    setFormData({
      employee_id: generateEmployeeId(),
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
  };

  const openCreateDialog = () => {
    resetForm();
    setFormData(prev => ({ ...prev, employee_id: generateEmployeeId() }));
    setCreateDialog(true);
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
      }
    });
    setEditDialog(true);
  };

  const openViewDialog = async (emp) => {
    try {
      const res = await axios.get(`${API}/employees/${emp.id}`);
      setSelectedEmployee(res.data);
      setViewDialog(true);
    } catch (error) {
      toast.error('Failed to load employee details');
    }
  };

  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = !searchTerm || 
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = !filterDepartment || emp.department === filterDepartment;
    return matchesSearch && matchesDept;
  });

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="employees-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Employees
        </h1>
        <p className="text-zinc-500">Manage employee records and organizational structure</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Total Employees</p>
                  <p className="text-2xl font-semibold text-zinc-950">{stats.total_employees}</p>
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
                  <p className="text-2xl font-semibold text-emerald-600">{stats.with_user_access}</p>
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
                  <p className="text-2xl font-semibold text-amber-600">{stats.without_user_access}</p>
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
                  <p className="text-2xl font-semibold text-zinc-950">{Object.keys(stats.by_department).length}</p>
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
            <Button 
              onClick={handleSyncFromUsers}
              variant="outline"
              className="rounded-sm"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Sync from Users
            </Button>
            <Button 
              onClick={openCreateDialog}
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Employee
            </Button>
          </div>
        )}
      </div>

      {/* Directory View */}
      {activeView === 'directory' && (
        <>
          {/* Search and Filters */}
          <div className="flex items-center gap-4 mb-6">
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
            >
              <option value="">All Departments</option>
              {departments.map(dept => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>

          {/* Employees Table */}
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
                    <th className="px-4 py-3 text-left">System Access</th>
                    {canManage && <th className="px-4 py-3 text-left">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.map(emp => (
                    <tr key={emp.id} className="border-b border-zinc-100 hover:bg-zinc-50" data-testid={`employee-row-${emp.id}`}>
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
                      <td className="px-4 py-3">
                        {emp.user_id ? (
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 text-xs bg-emerald-100 text-emerald-700 rounded">{emp.role || 'Linked'}</span>
                            {canManage && (
                              <Button
                                onClick={() => handleUnlinkUser(emp.id)}
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-zinc-400 hover:text-red-500"
                                title="Unlink user"
                              >
                                <Unlink className="w-3 h-3" />
                              </Button>
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-400">No access</span>
                            {canManage && (
                              <Button
                                onClick={() => { setSelectedEmployee(emp); setLinkUserDialog(true); }}
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-zinc-400 hover:text-blue-500"
                                title="Link to user"
                              >
                                <Link2 className="w-3 h-3" />
                              </Button>
                            )}
                          </div>
                        )}
                      </td>
                      {canManage && (
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <Button onClick={() => openViewDialog(emp)} variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <Eye className="w-4 h-4 text-zinc-500" />
                            </Button>
                            <Button onClick={() => openEditDialog(emp)} variant="ghost" size="sm" className="h-8 w-8 p-0">
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
        </>
      )}

      {/* Org Chart View */}
      {activeView === 'orgchart' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="border-b border-zinc-100">
            <CardTitle className="text-base font-semibold text-zinc-950">Organizational Hierarchy</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {orgChart.length === 0 ? (
              <div className="text-center py-12 text-zinc-400">
                No organizational structure found. Set reporting managers to build the hierarchy.
              </div>
            ) : (
              <div className="space-y-2">
                {orgChart.map(node => (
                  <OrgChartNode key={node.id} node={node} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Employee Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Add New Employee</DialogTitle>
          </DialogHeader>
          <EmployeeForm 
            formData={formData} 
            setFormData={setFormData} 
            employees={employees}
            onSubmit={handleCreateEmployee}
            onCancel={() => setCreateDialog(false)}
            submitLabel="Create Employee"
          />
        </DialogContent>
      </Dialog>

      {/* Edit Employee Dialog */}
      <Dialog open={editDialog} onOpenChange={setEditDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Edit Employee</DialogTitle>
          </DialogHeader>
          <EmployeeForm 
            formData={formData} 
            setFormData={setFormData} 
            employees={employees.filter(e => e.id !== selectedEmployee?.id)}
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
                    {selectedEmployee.documents.map(doc => (
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
              {users.filter(u => !employees.some(e => e.user_id === u.id)).map(u => (
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
            {users.filter(u => !employees.some(e => e.user_id === u.id)).length === 0 && (
              <p className="text-center py-4 text-zinc-400">All users are already linked to employees.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Employee Form Component
const EmployeeForm = ({ formData, setFormData, employees, onSubmit, onCancel, submitLabel, isEdit }) => {
  return (
    <div className="space-y-6">
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

      {/* Work Info */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">Work Information</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Department</Label>
            <Input
              value={formData.department}
              onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              placeholder="Consulting"
              className="rounded-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Designation</Label>
            <Input
              value={formData.designation}
              onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
              placeholder="Senior Consultant"
              className="rounded-sm"
            />
          </div>
          <div className="col-span-2 space-y-2">
            <Label>Reporting Manager</Label>
            <select
              value={formData.reporting_manager_id}
              onChange={(e) => setFormData({ ...formData, reporting_manager_id: e.target.value })}
              className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
            >
              <option value="">No reporting manager</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} ({emp.designation || emp.employee_id})</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* HR Details */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">HR Details</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Salary (Annual)</Label>
            <Input
              type="number"
              value={formData.salary}
              onChange={(e) => setFormData({ ...formData, salary: e.target.value })}
              placeholder="1200000"
              className="rounded-sm"
            />
          </div>
        </div>
      </div>

      {/* Bank Details */}
      <div className="border-t border-zinc-100 pt-4">
        <h4 className="font-medium text-zinc-950 mb-3">Bank Details</h4>
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
            <Label>Account Number</Label>
            <Input
              value={formData.bank_details.account_number}
              onChange={(e) => setFormData({ 
                ...formData, 
                bank_details: { ...formData.bank_details, account_number: e.target.value }
              })}
              placeholder="1234567890"
              className="rounded-sm"
            />
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
            <Label>IFSC Code</Label>
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
