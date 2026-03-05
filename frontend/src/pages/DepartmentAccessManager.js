import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { 
  Users, Building2, Shield, TrendingUp, Briefcase, DollarSign, 
  Search, Plus, X, Check, ChevronDown, ChevronRight, Edit2, 
  UserPlus, Settings, Eye, EyeOff, Clock, Key, AlertTriangle,
  Calendar, Lock, Unlock
} from 'lucide-react';
import { useFetch } from '../hooks/useApi';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Department icons and colors
const DEPT_CONFIG = {
  Sales: { icon: TrendingUp, color: 'bg-orange-500', textColor: 'text-orange-600', bgLight: 'bg-orange-50' },
  HR: { icon: Users, color: 'bg-green-500', textColor: 'text-green-600', bgLight: 'bg-green-50' },
  Consulting: { icon: Briefcase, color: 'bg-purple-500', textColor: 'text-purple-600', bgLight: 'bg-purple-50' },
  Finance: { icon: DollarSign, color: 'bg-blue-500', textColor: 'text-blue-600', bgLight: 'bg-blue-50' },
  Admin: { icon: Shield, color: 'bg-red-500', textColor: 'text-red-600', bgLight: 'bg-red-50' },
  Marketing: { icon: TrendingUp, color: 'bg-pink-500', textColor: 'text-pink-600', bgLight: 'bg-pink-50' },
};

const DepartmentAccessManager = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [filteredEmployees, setFilteredEmployees] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('all');
  const [departments, setDepartments] = useState({});
  
  // Edit dialog state
  const [editDialog, setEditDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [editForm, setEditForm] = useState({
    departments: [],
    primary_department: '',
    custom_page_access: [],
    restricted_pages: []
  });
  
  // Special Permissions dialog state
  const [specialDialog, setSpecialDialog] = useState(false);
  const [specialForm, setSpecialForm] = useState({
    additional_departments: [],
    additional_pages: [],
    restricted_pages: [],
    temporary_role: '',
    temporary_role_expiry: '',
    can_approve_for_departments: [],
    notes: ''
  });
  
  // Bulk edit state
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkDialog, setBulkDialog] = useState(false);
  const [bulkForm, setBulkForm] = useState({ add: [], remove: [] });

  const token = localStorage.getItem('token');
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  // Query: Fetch stats
  const { data: stats, refetch: refetchStats } = useFetch('/api/department-access/stats');

  // Query: Fetch configured departments
  const { data: configDeptData } = useFetch('/api/permission-config/departments');
  const configuredDepts = configDeptData?.departments || [];

  // Query: Fetch employees
  const { data: employeesData, isLoading: loading, refetch: refetchEmployees } = useFetch('/api/employees');
  // API returns { items: [], pagination: {} } so extract items array
  const employees = Array.isArray(employeesData) ? employeesData : (employeesData?.items || []);

  // Update departments config when loaded
  useEffect(() => {
    if (configuredDepts.length > 0) {
      const deptObj = {};
      configuredDepts.forEach(d => {
        deptObj[d.name] = {
          icon: DEPT_CONFIG[d.name]?.icon || Building2,
          color: `bg-[${d.color}]`,
          textColor: `text-[${d.color}]`,
          bgLight: 'bg-gray-50'
        };
      });
      setDepartments(deptObj);
    }
  }, [configuredDepts]);

  // Filter employees when search or department changes
  useEffect(() => {
    filterEmployees();
  }, [searchQuery, selectedDept, employees]);

  const refetchAll = () => {
    refetchStats();
    refetchEmployees();
  };

  const filterEmployees = () => {
    let filtered = employees;
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(e => 
        `${e.first_name} ${e.last_name}`.toLowerCase().includes(query) ||
        e.employee_id?.toLowerCase().includes(query) ||
        e.email?.toLowerCase().includes(query)
      );
    }
    
    if (selectedDept !== 'all') {
      filtered = filtered.filter(e => 
        e.departments?.includes(selectedDept) ||
        e.primary_department === selectedDept ||
        e.department === selectedDept ||
        e.additional_departments?.includes(selectedDept)
      );
    }
    
    setFilteredEmployees(filtered);
  };

  const openEditDialog = async (employee) => {
    try {
      const res = await axios.get(`${API_URL}/api/department-access/employee/${employee.id}`, { headers });
      setSelectedEmployee(res.data);
      setEditForm({
        departments: res.data.departments || [],
        primary_department: res.data.primary_department || '',
        custom_page_access: res.data.custom_page_access || [],
        restricted_pages: res.data.restricted_pages || []
      });
      setEditDialog(true);
    } catch (error) {
      toast.error('Failed to load employee access');
    }
  };

  const toggleDepartment = (dept) => {
    const current = editForm.departments;
    if (current.includes(dept)) {
      // Remove department
      if (current.length <= 1) {
        toast.error('Employee must have at least one department');
        return;
      }
      const newDepts = current.filter(d => d !== dept);
      setEditForm({
        ...editForm,
        departments: newDepts,
        primary_department: editForm.primary_department === dept ? newDepts[0] : editForm.primary_department
      });
    } else {
      // Add department
      setEditForm({
        ...editForm,
        departments: [...current, dept]
      });
    }
  };

  // Mutation: Save employee access
  const saveEmployeeAccessMutation = useMutation({
    mutationFn: async () => {
      return axios.put(`${API_URL}/api/department-access/employee/${selectedEmployee.employee_id}`, editForm, { headers });
    },
    onSuccess: () => {
      toast.success('Department access updated');
      setEditDialog(false);
      refetchAll();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  });

  const saveEmployeeAccess = () => {
    if (!editForm.departments.length) {
      toast.error('Select at least one department');
      return;
    }
    if (!editForm.primary_department || !editForm.departments.includes(editForm.primary_department)) {
      toast.error('Select a valid primary department');
      return;
    }
    saveEmployeeAccessMutation.mutate();
  };

  // Special Permissions Functions
  const openSpecialDialog = async (employee) => {
    try {
      const res = await axios.get(`${API_URL}/api/permission-config/employee/${employee.id}/special-permissions`, { headers });
      setSelectedEmployee(res.data);
      setSpecialForm({
        additional_departments: res.data.additional_departments || [],
        additional_pages: res.data.additional_pages || [],
        restricted_pages: res.data.restricted_pages || [],
        temporary_role: res.data.temporary_role || '',
        temporary_role_expiry: res.data.temporary_role_expiry || '',
        can_approve_for_departments: res.data.can_approve_for_departments || [],
        notes: res.data.permission_notes || ''
      });
      setSpecialDialog(true);
    } catch (error) {
      toast.error('Failed to load special permissions');
    }
  };

  // Mutation: Save special permissions
  const saveSpecialPermissionsMutation = useMutation({
    mutationFn: async () => {
      return axios.put(`${API_URL}/api/permission-config/employee/${selectedEmployee.employee_id}/special-permissions`, {
        additional_departments: specialForm.additional_departments,
        additional_pages: specialForm.additional_pages,
        restricted_pages: specialForm.restricted_pages,
        temporary_role: specialForm.temporary_role || null,
        temporary_role_expiry: specialForm.temporary_role_expiry || null,
        can_approve_for_departments: specialForm.can_approve_for_departments,
        notes: specialForm.notes,
        special_permissions: []
      }, { headers });
    },
    onSuccess: () => {
      toast.success('Special permissions updated');
      setSpecialDialog(false);
      refetchAll();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  });

  const saveSpecialPermissions = () => {
    saveSpecialPermissionsMutation.mutate();
  };

  // Mutation: Grant temporary access
  const grantTemporaryAccessMutation = useMutation({
    mutationFn: async ({ employeeId, department, reason, days }) => {
      return axios.post(
        `${API_URL}/api/permission-config/employee/${employeeId}/grant-temporary-access?department=${department}&reason=${encodeURIComponent(reason)}&expiry_days=${days}`,
        {},
        { headers }
      );
    },
    onSuccess: (response) => {
      toast.success(response.data.message);
      refetchAll();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to grant access');
    }
  });

  const grantTemporaryAccess = (employeeId, department, reason, days) => {
    grantTemporaryAccessMutation.mutate({ employeeId, department, reason, days });
  };

  // Mutation: Bulk update
  const bulkUpdateMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API_URL}/api/department-access/bulk-update`, {
        employee_ids: selectedIds,
        add_departments: bulkForm.add,
        remove_departments: bulkForm.remove
      }, { headers });
    },
    onSuccess: (response) => {
      toast.success(response.data.message);
      setBulkDialog(false);
      setSelectedIds([]);
      setBulkMode(false);
      refetchAll();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  });

  const handleBulkUpdate = () => {
    if (!selectedIds.length) {
      toast.error('Select employees first');
      return;
    }
    bulkUpdateMutation.mutate();
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredEmployees.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredEmployees.map(e => e.id));
    }
  };

  const DeptBadge = ({ dept, isPrimary = false }) => {
    const config = DEPT_CONFIG[dept] || { icon: Building2, color: 'bg-gray-500', textColor: 'text-gray-600' };
    const Icon = config.icon;
    return (
      <Badge 
        variant="outline" 
        className={`${isPrimary ? config.color + ' text-white' : config.bgLight + ' ' + config.textColor} flex items-center gap-1`}
      >
        <Icon className="w-3 h-3" />
        {dept}
        {isPrimary && <span className="text-xs">(Primary)</span>}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Department Access Manager</h1>
          <p className="text-muted-foreground">Manage employee department access and permissions</p>
        </div>
        {bulkMode ? (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setBulkMode(false); setSelectedIds([]); }}>
              Cancel
            </Button>
            <Button 
              onClick={() => setBulkDialog(true)} 
              disabled={!selectedIds.length}
              data-testid="bulk-update-btn"
            >
              Update {selectedIds.length} Selected
            </Button>
          </div>
        ) : (
          <Button onClick={() => setBulkMode(true)}>
            <Edit2 className="w-4 h-4 mr-2" /> Bulk Edit
          </Button>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {Object.entries(DEPT_CONFIG).map(([dept, config]) => {
            const Icon = config.icon;
            const count = stats.by_department?.[dept] || 0;
            return (
              <Card 
                key={dept} 
                className={`cursor-pointer transition-all ${selectedDept === dept ? 'ring-2 ring-primary' : ''}`}
                onClick={() => setSelectedDept(selectedDept === dept ? 'all' : dept)}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.color}`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{count}</p>
                    <p className="text-xs text-muted-foreground">{dept}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Additional Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Total Employees</p>
              <p className="text-2xl font-bold">{stats.total_employees}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">With Portal Access</p>
              <p className="text-2xl font-bold text-green-600">{stats.with_portal_access}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Without Portal Access</p>
              <p className="text-2xl font-bold text-orange-600">{stats.without_portal_access}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Multi-Department</p>
              <p className="text-2xl font-bold text-purple-600">{stats.multi_department_employees}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, ID, or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button 
            variant={selectedDept === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedDept('all')}
          >
            All ({employees.length})
          </Button>
          {Object.keys(DEPT_CONFIG).map(dept => (
            <Button
              key={dept}
              variant={selectedDept === dept ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedDept(dept)}
            >
              {dept}
            </Button>
          ))}
        </div>
      </div>

      {/* Employee Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">
            Employees ({filteredEmployees.length})
            {selectedDept !== 'all' && <span className="text-muted-foreground"> in {selectedDept}</span>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  {bulkMode && (
                    <th className="p-2 text-left">
                      <Checkbox 
                        checked={selectedIds.length === filteredEmployees.length && filteredEmployees.length > 0}
                        onCheckedChange={toggleSelectAll}
                      />
                    </th>
                  )}
                  <th className="p-2 text-left font-medium">Employee</th>
                  <th className="p-2 text-left font-medium">Designation</th>
                  <th className="p-2 text-left font-medium">Departments</th>
                  <th className="p-2 text-left font-medium">Level</th>
                  <th className="p-2 text-left font-medium">Portal</th>
                  <th className="p-2 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp) => {
                  const depts = emp.departments || (emp.department ? [emp.department] : []);
                  const primaryDept = emp.primary_department || emp.department;
                  const hasSpecialPerms = emp.additional_departments?.length > 0 || emp.temporary_role;
                  return (
                    <tr key={emp.id} className="border-b hover:bg-muted/50">
                      {bulkMode && (
                        <td className="p-2">
                          <Checkbox 
                            checked={selectedIds.includes(emp.id)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setSelectedIds([...selectedIds, emp.id]);
                              } else {
                                setSelectedIds(selectedIds.filter(id => id !== emp.id));
                              }
                            }}
                          />
                        </td>
                      )}
                      <td className="p-2">
                        <div>
                          <p className="font-medium">{emp.first_name} {emp.last_name}</p>
                          <p className="text-xs text-muted-foreground">{emp.employee_id}</p>
                        </div>
                      </td>
                      <td className="p-2 text-sm">{emp.designation || '-'}</td>
                      <td className="p-2">
                        <div className="flex flex-wrap gap-1">
                          {depts.length > 0 ? (
                            depts.map(d => (
                              <DeptBadge key={d} dept={d} isPrimary={d === primaryDept} />
                            ))
                          ) : (
                            <Badge variant="outline" className="text-muted-foreground">None</Badge>
                          )}
                          {emp.additional_departments?.map(d => (
                            <Badge key={`add-${d}`} variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
                              +{d}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="p-2">
                        <Badge variant="outline" className="capitalize">
                          {emp.level || 'executive'}
                        </Badge>
                      </td>
                      <td className="p-2">
                        {emp.user_id ? (
                          <Badge className="bg-green-100 text-green-700">Active</Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground">No Access</Badge>
                        )}
                      </td>
                      <td className="p-2">
                        <div className="flex gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => openEditDialog(emp)}
                          >
                            <Settings className="w-4 h-4 mr-1" /> Dept
                          </Button>
                          <Button 
                            variant={hasSpecialPerms ? "default" : "ghost"}
                            size="sm"
                            onClick={() => openSpecialDialog(emp)}
                            className={hasSpecialPerms ? "bg-yellow-500 hover:bg-yellow-600" : ""}
                          >
                            <Key className="w-4 h-4 mr-1" /> Special
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredEmployees.length === 0 && (
                  <tr>
                    <td colSpan={bulkMode ? 7 : 6} className="p-8 text-center text-muted-foreground">
                      No employees found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Employee Access Dialog */}
      <Dialog open={editDialog} onOpenChange={setEditDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Department Access</DialogTitle>
          </DialogHeader>
          {selectedEmployee && (
            <div className="space-y-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{selectedEmployee.full_name}</p>
                <p className="text-sm text-muted-foreground">{selectedEmployee.employee_code}</p>
              </div>

              {/* Department Selection */}
              <div>
                <label className="text-sm font-medium mb-2 block">Departments</label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(DEPT_CONFIG).map(([dept, config]) => {
                    const Icon = config.icon;
                    const isSelected = editForm.departments.includes(dept);
                    const isPrimary = editForm.primary_department === dept;
                    return (
                      <div 
                        key={dept}
                        className={`p-3 border rounded-lg cursor-pointer transition-all ${
                          isSelected ? config.bgLight + ' border-2 ' + config.textColor : 'hover:bg-muted'
                        }`}
                        onClick={() => toggleDepartment(dept)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className={`w-4 h-4 ${isSelected ? config.textColor : ''}`} />
                            <span className={isSelected ? 'font-medium' : ''}>{dept}</span>
                          </div>
                          {isSelected && <Check className="w-4 h-4" />}
                        </div>
                        {isSelected && (
                          <Button
                            variant={isPrimary ? "default" : "ghost"}
                            size="sm"
                            className="mt-2 w-full text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditForm({ ...editForm, primary_department: dept });
                            }}
                          >
                            {isPrimary ? 'Primary' : 'Set as Primary'}
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Current Access Summary */}
              <div className="p-3 bg-muted/50 rounded-lg text-sm">
                <p className="font-medium mb-1">Access Summary:</p>
                <p>Departments: {editForm.departments.join(', ') || 'None'}</p>
                <p>Primary: {editForm.primary_department || 'Not set'}</p>
                <p>Level: {selectedEmployee.level || 'executive'}</p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog(false)}>Cancel</Button>
            <Button onClick={saveEmployeeAccess}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Edit Dialog */}
      <Dialog open={bulkDialog} onOpenChange={setBulkDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Update Department Access</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Updating {selectedIds.length} employees
            </p>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Add Departments</label>
              <div className="flex flex-wrap gap-2">
                {Object.keys(DEPT_CONFIG).map(dept => (
                  <Button
                    key={dept}
                    variant={bulkForm.add.includes(dept) ? 'default' : 'outline'}
                    size="sm"
                    data-testid={`add-dept-${dept.toLowerCase()}`}
                    onClick={() => {
                      if (bulkForm.add.includes(dept)) {
                        setBulkForm({ ...bulkForm, add: bulkForm.add.filter(d => d !== dept) });
                      } else {
                        setBulkForm({ 
                          ...bulkForm, 
                          add: [...bulkForm.add, dept],
                          remove: bulkForm.remove.filter(d => d !== dept)
                        });
                      }
                    }}
                  >
                    <Plus className="w-3 h-3 mr-1" /> {dept}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Remove Departments</label>
              <div className="flex flex-wrap gap-2">
                {Object.keys(DEPT_CONFIG).map(dept => (
                  <Button
                    key={dept}
                    variant={bulkForm.remove.includes(dept) ? 'destructive' : 'outline'}
                    size="sm"
                    onClick={() => {
                      if (bulkForm.remove.includes(dept)) {
                        setBulkForm({ ...bulkForm, remove: bulkForm.remove.filter(d => d !== dept) });
                      } else {
                        setBulkForm({ 
                          ...bulkForm, 
                          remove: [...bulkForm.remove, dept],
                          add: bulkForm.add.filter(d => d !== dept)
                        });
                      }
                    }}
                  >
                    <X className="w-3 h-3 mr-1" /> {dept}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkDialog(false)}>Cancel</Button>
            <Button 
              onClick={handleBulkUpdate}
              data-testid="bulk-apply-btn"
              disabled={bulkForm.add.length === 0 && bulkForm.remove.length === 0}
            >
              Apply to {selectedIds.length} Employees
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Special Permissions Dialog */}
      <Dialog open={specialDialog} onOpenChange={setSpecialDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="w-5 h-5 text-yellow-600" />
              Special Permissions
            </DialogTitle>
          </DialogHeader>
          {selectedEmployee && (
            <div className="space-y-6">
              {/* Employee Info */}
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{selectedEmployee.employee_name}</p>
                <p className="text-sm text-muted-foreground">
                  {selectedEmployee.employee_code} • {selectedEmployee.designation} • Primary: {selectedEmployee.primary_department}
                </p>
              </div>

              {/* Info Box */}
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm">
                <p className="font-medium text-yellow-800 flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> Use Case
                </p>
                <p className="text-yellow-700 mt-1">
                  Grant additional access when an employee needs to work across departments. 
                  Example: A Sales person temporarily acting as Marketing Manager.
                </p>
              </div>

              <Tabs defaultValue="departments" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="departments">Extra Departments</TabsTrigger>
                  <TabsTrigger value="approvals">Approval Rights</TabsTrigger>
                  <TabsTrigger value="temporary">Temporary Role</TabsTrigger>
                </TabsList>

                {/* Additional Departments Tab */}
                <TabsContent value="departments" className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium mb-2 block">
                      Additional Department Access
                    </Label>
                    <p className="text-xs text-muted-foreground mb-3">
                      Grant access to pages from other departments beyond their primary assignment
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(DEPT_CONFIG).map(([dept, config]) => {
                        const Icon = config.icon;
                        const isBase = selectedEmployee.base_departments?.includes(dept);
                        const isAdditional = specialForm.additional_departments.includes(dept);
                        return (
                          <div 
                            key={dept}
                            className={`p-3 border rounded-lg cursor-pointer transition-all ${
                              isBase ? 'bg-gray-100 cursor-not-allowed' :
                              isAdditional ? 'bg-yellow-50 border-yellow-400' : 'hover:bg-muted'
                            }`}
                            onClick={() => {
                              if (isBase) return; // Can't toggle base departments
                              if (isAdditional) {
                                setSpecialForm({
                                  ...specialForm,
                                  additional_departments: specialForm.additional_departments.filter(d => d !== dept)
                                });
                              } else {
                                setSpecialForm({
                                  ...specialForm,
                                  additional_departments: [...specialForm.additional_departments, dept]
                                });
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Icon className={`w-4 h-4 ${isAdditional ? 'text-yellow-600' : ''}`} />
                                <span>{dept}</span>
                              </div>
                              {isBase && <Badge variant="outline" className="text-xs">Base</Badge>}
                              {isAdditional && <Check className="w-4 h-4 text-yellow-600" />}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </TabsContent>

                {/* Approval Rights Tab */}
                <TabsContent value="approvals" className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium mb-2 block">
                      Can Approve For Departments
                    </Label>
                    <p className="text-xs text-muted-foreground mb-3">
                      Allow this employee to approve leaves/expenses for other departments
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(DEPT_CONFIG).map(([dept, config]) => {
                        const Icon = config.icon;
                        const canApprove = specialForm.can_approve_for_departments.includes(dept);
                        return (
                          <div 
                            key={dept}
                            className={`p-3 border rounded-lg cursor-pointer transition-all ${
                              canApprove ? 'bg-green-50 border-green-400' : 'hover:bg-muted'
                            }`}
                            onClick={() => {
                              if (canApprove) {
                                setSpecialForm({
                                  ...specialForm,
                                  can_approve_for_departments: specialForm.can_approve_for_departments.filter(d => d !== dept)
                                });
                              } else {
                                setSpecialForm({
                                  ...specialForm,
                                  can_approve_for_departments: [...specialForm.can_approve_for_departments, dept]
                                });
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Icon className={`w-4 h-4 ${canApprove ? 'text-green-600' : ''}`} />
                                <span>{dept}</span>
                              </div>
                              {canApprove && <Check className="w-4 h-4 text-green-600" />}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </TabsContent>

                {/* Temporary Role Tab */}
                <TabsContent value="temporary" className="space-y-4">
                  <div className="space-y-4">
                    <div>
                      <Label>Temporary Role Override</Label>
                      <p className="text-xs text-muted-foreground mb-2">
                        Temporarily change this employee's role (e.g., acting manager)
                      </p>
                      <Select 
                        value={specialForm.temporary_role} 
                        onValueChange={(v) => setSpecialForm({...specialForm, temporary_role: v})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select temporary role (optional)" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">No temporary role</SelectItem>
                          <SelectItem value="manager">Acting Manager</SelectItem>
                          <SelectItem value="lead_consultant">Acting Lead Consultant</SelectItem>
                          <SelectItem value="project_manager">Acting Project Manager</SelectItem>
                          <SelectItem value="hr_manager">Acting HR Manager</SelectItem>
                          <SelectItem value="sales_manager">Acting Sales Manager</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {specialForm.temporary_role && (
                      <div>
                        <Label>Expiry Date</Label>
                        <Input
                          type="date"
                          value={specialForm.temporary_role_expiry?.split('T')[0] || ''}
                          onChange={(e) => setSpecialForm({
                            ...specialForm,
                            temporary_role_expiry: e.target.value ? new Date(e.target.value).toISOString() : ''
                          })}
                          min={new Date().toISOString().split('T')[0]}
                        />
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>

              {/* Notes */}
              <div>
                <Label>Permission Notes</Label>
                <Textarea
                  placeholder="Document why these special permissions were granted..."
                  value={specialForm.notes}
                  onChange={(e) => setSpecialForm({...specialForm, notes: e.target.value})}
                  rows={2}
                />
              </div>

              {/* Summary */}
              <div className="p-3 bg-muted/50 rounded-lg text-sm">
                <p className="font-medium mb-1">Effective Access Summary:</p>
                <p>Base Departments: {selectedEmployee.base_departments?.join(', ') || 'None'}</p>
                <p>Additional: {specialForm.additional_departments.join(', ') || 'None'}</p>
                <p>Can Approve For: {specialForm.can_approve_for_departments.join(', ') || 'Own department only'}</p>
                {specialForm.temporary_role && (
                  <p className="text-yellow-700">Temporary Role: {specialForm.temporary_role}</p>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSpecialDialog(false)}>Cancel</Button>
            <Button onClick={saveSpecialPermissions}>Save Special Permissions</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DepartmentAccessManager;
