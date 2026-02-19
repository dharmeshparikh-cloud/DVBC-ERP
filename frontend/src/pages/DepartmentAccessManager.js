import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { toast } from 'sonner';
import { 
  Users, Building2, Shield, TrendingUp, Briefcase, DollarSign, 
  Search, Plus, X, Check, ChevronDown, ChevronRight, Edit2, 
  UserPlus, Settings, Eye, EyeOff
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Department icons and colors
const DEPT_CONFIG = {
  Sales: { icon: TrendingUp, color: 'bg-orange-500', textColor: 'text-orange-600', bgLight: 'bg-orange-50' },
  HR: { icon: Users, color: 'bg-green-500', textColor: 'text-green-600', bgLight: 'bg-green-50' },
  Consulting: { icon: Briefcase, color: 'bg-purple-500', textColor: 'text-purple-600', bgLight: 'bg-purple-50' },
  Finance: { icon: DollarSign, color: 'bg-blue-500', textColor: 'text-blue-600', bgLight: 'bg-blue-50' },
  Admin: { icon: Shield, color: 'bg-red-500', textColor: 'text-red-600', bgLight: 'bg-red-50' }
};

const DepartmentAccessManager = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [filteredEmployees, setFilteredEmployees] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('all');
  const [loading, setLoading] = useState(true);
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
  
  // Bulk edit state
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkDialog, setBulkDialog] = useState(false);
  const [bulkForm, setBulkForm] = useState({ add: [], remove: [] });

  const token = localStorage.getItem('token');
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    filterEmployees();
  }, [searchQuery, selectedDept, employees]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch stats
      const statsRes = await fetch(`${API_URL}/api/department-access/stats`, { headers });
      if (statsRes.ok) setStats(await statsRes.json());

      // Fetch departments config
      const deptRes = await fetch(`${API_URL}/api/department-access/departments`, { headers });
      if (deptRes.ok) {
        const data = await deptRes.json();
        setDepartments(data.departments);
      }

      // Fetch all employees
      const empRes = await fetch(`${API_URL}/api/employees`, { headers });
      if (empRes.ok) {
        const data = await empRes.json();
        setEmployees(data);
        setFilteredEmployees(data);
      }
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
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
        e.department === selectedDept
      );
    }
    
    setFilteredEmployees(filtered);
  };

  const openEditDialog = async (employee) => {
    try {
      const res = await fetch(`${API_URL}/api/department-access/employee/${employee.id}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setSelectedEmployee(data);
        setEditForm({
          departments: data.departments || [],
          primary_department: data.primary_department || '',
          custom_page_access: data.custom_page_access || [],
          restricted_pages: data.restricted_pages || []
        });
        setEditDialog(true);
      }
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

  const saveEmployeeAccess = async () => {
    if (!editForm.departments.length) {
      toast.error('Select at least one department');
      return;
    }
    if (!editForm.primary_department || !editForm.departments.includes(editForm.primary_department)) {
      toast.error('Select a valid primary department');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/department-access/employee/${selectedEmployee.employee_id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(editForm)
      });
      
      if (res.ok) {
        toast.success('Department access updated');
        setEditDialog(false);
        fetchData();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to update');
      }
    } catch (error) {
      toast.error('Failed to update access');
    }
  };

  const handleBulkUpdate = async () => {
    if (!selectedIds.length) {
      toast.error('Select employees first');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/department-access/bulk-update`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          employee_ids: selectedIds,
          add_departments: bulkForm.add,
          remove_departments: bulkForm.remove
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(`Updated ${data.updated_count} employees`);
        setBulkDialog(false);
        setBulkMode(false);
        setSelectedIds([]);
        setBulkForm({ add: [], remove: [] });
        fetchData();
      } else {
        toast.error('Bulk update failed');
      }
    } catch (error) {
      toast.error('Bulk update failed');
    }
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
            <Button onClick={() => setBulkDialog(true)} disabled={!selectedIds.length}>
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
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => openEditDialog(emp)}
                        >
                          <Settings className="w-4 h-4 mr-1" /> Edit Access
                        </Button>
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
            <Button onClick={handleBulkUpdate}>Apply to {selectedIds.length} Employees</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DepartmentAccessManager;
