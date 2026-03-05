import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Badge } from '../../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';
import {
  Calendar, Plus, Edit2, Trash2, Building2, Users, User, Briefcase,
  Clock, Calculator, DollarSign, FileText, CheckCircle, Settings,
  ChevronRight, Loader2, Save, Copy, TrendingUp, AlertCircle, PieChart
} from 'lucide-react';

const LEAVE_TYPES = [
  { value: 'casual_leave', label: 'Casual Leave', color: 'blue' },
  { value: 'sick_leave', label: 'Sick Leave', color: 'red' },
  { value: 'earned_leave', label: 'Earned Leave', color: 'green' },
  { value: 'maternity_leave', label: 'Maternity Leave', color: 'pink' },
  { value: 'paternity_leave', label: 'Paternity Leave', color: 'purple' },
  { value: 'bereavement_leave', label: 'Bereavement Leave', color: 'gray' },
  { value: 'compensatory_off', label: 'Compensatory Off', color: 'orange' }
];

const SCOPE_ICONS = {
  company: Building2,
  department: Users,
  role: Briefcase,
  employee: User
};

const LeavePolicySettings = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  
  // Dialog states
  const [showPolicyDialog, setShowPolicyDialog] = useState(false);
  const [showLeaveTypeDialog, setShowLeaveTypeDialog] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [editingLeaveType, setEditingLeaveType] = useState(null);
  
  // Form states
  const [policyForm, setPolicyForm] = useState({
    name: '',
    description: '',
    scope: 'company',
    scope_value: null,
    effective_from: new Date().toISOString().split('T')[0],
    is_active: true,
    leave_types: [],
    payroll_integration: {
      lop_deduction_formula: 'basic_per_day',
      encashment_formula: 'basic_per_day',
      include_in_full_final: true,
      auto_adjust_salary: true
    }
  });
  
  const [leaveTypeForm, setLeaveTypeForm] = useState({
    leave_type: 'casual_leave',
    annual_quota: 12,
    accrual_type: 'yearly',
    accrual_rate: null,
    carry_forward: false,
    max_carry_forward: null,
    encashment_allowed: false,
    encashment_max_days: null,
    min_service_months: 0,
    pro_rata_for_new_joiners: true,
    can_be_negative: false,
    requires_medical_certificate: false,
    medical_certificate_threshold: 2,
    max_consecutive_days: null,
    advance_notice_days: 0,
    description: ''
  });

  // Fetch policies using React Query
  const { data: policies = [], isLoading: policiesLoading, refetch: refetchPolicies } = useQuery({
    queryKey: ['leave-policies'],
    queryFn: async () => {
      const response = await axios.get(`${API}/leave-policies`);
      return response.data || [];
    },
    staleTime: 3 * 60 * 1000,
    onError: () => toast.error('Failed to fetch policies')
  });

  // Fetch departments
  const { data: departments = [] } = useQuery({
    queryKey: ['masters', 'departments'],
    queryFn: async () => {
      const response = await axios.get(`${API}/masters/departments`);
      return response.data || [];
    },
    staleTime: 10 * 60 * 1000
  });

  // Fetch employees
  const { data: employeesData = [] } = useQuery({
    queryKey: ['employees', 'all'],
    queryFn: async () => {
      const response = await axios.get(`${API}/employees`);
      return Array.isArray(response.data) ? response.data : [];
    },
    staleTime: 5 * 60 * 1000
  });

  // Fetch company-wide leave stats
  const { data: leaveStats } = useQuery({
    queryKey: ['leave-stats', 'company-wide'],
    queryFn: async () => {
      const response = await axios.get(`${API}/leave-requests/stats/company-wide`);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    retry: false
  });

  const employees = Array.isArray(employeesData) ? employeesData : [];
  
  // Extract unique roles from employees
  const roles = [...new Set(employees.map(e => e.designation).filter(Boolean))];
  
  const loading = policiesLoading;

  const openNewPolicy = () => {
    setPolicyForm({
      name: '',
      description: '',
      scope: 'company',
      scope_value: null,
      effective_from: new Date().toISOString().split('T')[0],
      is_active: true,
      leave_types: [],
      payroll_integration: {
        lop_deduction_formula: 'basic_per_day',
        encashment_formula: 'basic_per_day',
        include_in_full_final: true,
        auto_adjust_salary: true
      }
    });
    setEditingPolicy(null);
    setShowPolicyDialog(true);
  };

  const openEditPolicy = (policy) => {
    setPolicyForm({
      ...policy,
      effective_from: policy.effective_from?.split('T')[0] || new Date().toISOString().split('T')[0]
    });
    setEditingPolicy(policy);
    setShowPolicyDialog(true);
  };

  const duplicatePolicy = (policy) => {
    setPolicyForm({
      ...policy,
      name: `${policy.name} (Copy)`,
      effective_from: new Date().toISOString().split('T')[0]
    });
    setEditingPolicy(null);
    setShowPolicyDialog(true);
  };

  // Mutation for saving policy
  const savePolicyMutation = useMutation({
    mutationFn: async ({ isEdit, id, data }) => {
      if (isEdit) {
        const response = await axios.put(`${API}/leave-policies/${id}`, data);
        return response.data;
      } else {
        const response = await axios.post(`${API}/leave-policies`, data);
        return response.data;
      }
    },
    onSuccess: (_, { isEdit }) => {
      toast.success(isEdit ? 'Policy updated' : 'Policy created');
      setShowPolicyDialog(false);
      queryClient.invalidateQueries({ queryKey: ['leave-policies'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save policy');
    }
  });

  const savePolicy = () => {
    if (!policyForm.name) {
      toast.error('Policy name is required');
      return;
    }
    savePolicyMutation.mutate({
      isEdit: !!editingPolicy,
      id: editingPolicy?.id,
      data: policyForm
    });
  };

  const saving = savePolicyMutation.isPending;

  // Mutation for deleting policy
  const deletePolicyMutation = useMutation({
    mutationFn: async (policyId) => {
      await axios.delete(`${API}/leave-policies/${policyId}`);
    },
    onSuccess: () => {
      toast.success('Policy deleted');
      queryClient.invalidateQueries({ queryKey: ['leave-policies'] });
    },
    onError: () => {
      toast.error('Failed to delete policy');
    }
  });

  const deletePolicy = (policyId) => {
    if (!window.confirm('Are you sure you want to delete this policy?')) return;
    deletePolicyMutation.mutate(policyId);
  };

  const openAddLeaveType = () => {
    setLeaveTypeForm({
      leave_type: 'casual_leave',
      annual_quota: 12,
      accrual_type: 'yearly',
      accrual_rate: null,
      carry_forward: false,
      max_carry_forward: null,
      encashment_allowed: false,
      encashment_max_days: null,
      min_service_months: 0,
      pro_rata_for_new_joiners: true,
      can_be_negative: false,
      requires_medical_certificate: false,
      medical_certificate_threshold: 2,
      max_consecutive_days: null,
      advance_notice_days: 0,
      description: ''
    });
    setEditingLeaveType(null);
    setShowLeaveTypeDialog(true);
  };

  const openEditLeaveType = (lt, index) => {
    setLeaveTypeForm(lt);
    setEditingLeaveType(index);
    setShowLeaveTypeDialog(true);
  };

  const saveLeaveType = () => {
    const updatedTypes = [...policyForm.leave_types];
    if (editingLeaveType !== null) {
      updatedTypes[editingLeaveType] = leaveTypeForm;
    } else {
      updatedTypes.push(leaveTypeForm);
    }
    setPolicyForm({ ...policyForm, leave_types: updatedTypes });
    setShowLeaveTypeDialog(false);
  };

  const removeLeaveType = (index) => {
    const updatedTypes = policyForm.leave_types.filter((_, i) => i !== index);
    setPolicyForm({ ...policyForm, leave_types: updatedTypes });
  };

  const getScopeLabel = (scope, value) => {
    if (scope === 'company') return 'All Employees';
    if (scope === 'department') return value || 'Department';
    if (scope === 'role') return value || 'Role';
    if (scope === 'employee') {
      const emp = employees.find(e => e.id === value);
      return emp ? `${emp.first_name} ${emp.last_name}` : value;
    }
    return value;
  };

  const getLeaveTypeLabel = (value) => {
    return LEAVE_TYPES.find(t => t.value === value)?.label || value;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="leave-policy-settings">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-orange-500" />
            Leave Policy Management
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Configure leave policies by company, department, role, or individual employee
          </p>
        </div>
        <Button onClick={openNewPolicy} className="bg-orange-500 hover:bg-orange-600" data-testid="create-policy-btn">
          <Plus className="w-4 h-4 mr-2" /> Create Policy
        </Button>
      </div>

      {/* Quick Stats Banner */}
      {leaveStats && (
        <Card className="bg-gradient-to-r from-orange-50 via-amber-50 to-yellow-50 border-orange-200" data-testid="leave-stats-banner">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <PieChart className="w-5 h-5 text-orange-600" />
                <h3 className="font-semibold text-orange-800">Company-Wide Leave Utilization</h3>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4 text-zinc-500" />
                  <span className="text-zinc-600">{leaveStats.total_employees} employees</span>
                </div>
                {leaveStats.pending_requests > 0 && (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="w-4 h-4 text-amber-500" />
                    <span className="text-amber-700">{leaveStats.pending_requests} pending</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-4 h-4 text-zinc-500" />
                  <span className="text-zinc-600">{leaveStats.requests_this_month} this month</span>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              {leaveStats.leave_types && Object.entries(leaveStats.leave_types).map(([key, stats]) => {
                const colorMap = {
                  casual_leave: { bg: 'bg-blue-500', light: 'bg-blue-100', text: 'text-blue-700' },
                  sick_leave: { bg: 'bg-red-500', light: 'bg-red-100', text: 'text-red-700' },
                  earned_leave: { bg: 'bg-emerald-500', light: 'bg-emerald-100', text: 'text-emerald-700' }
                };
                const colors = colorMap[key] || { bg: 'bg-zinc-500', light: 'bg-zinc-100', text: 'text-zinc-700' };
                
                return (
                  <div key={key} className="bg-white rounded-lg p-3 border border-zinc-100 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-sm font-medium ${colors.text}`}>{stats.label}</span>
                      <span className={`text-lg font-bold ${colors.text}`}>{stats.utilization_percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${colors.bg} transition-all duration-500`}
                        style={{ width: `${Math.min(stats.utilization_percent, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-zinc-500">
                      <span>{stats.total_used} used</span>
                      <span>{stats.total_available} available</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Policy Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {policies.map(policy => {
          const ScopeIcon = SCOPE_ICONS[policy.scope] || Building2;
          return (
            <Card key={policy.id} className="border-zinc-200 hover:shadow-md transition-shadow" data-testid={`policy-${policy.id}`}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${policy.is_active ? 'bg-orange-100' : 'bg-zinc-100'}`}>
                      <ScopeIcon className={`w-5 h-5 ${policy.is_active ? 'text-orange-600' : 'text-zinc-400'}`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{policy.name}</CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <Badge variant={policy.is_active ? 'default' : 'secondary'} className="text-xs">
                          {policy.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <span className="text-xs text-zinc-500">
                          {getScopeLabel(policy.scope, policy.scope_value)}
                        </span>
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => duplicatePolicy(policy)} title="Duplicate">
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => openEditPolicy(policy)} data-testid={`edit-policy-${policy.id}`}>
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => deletePolicy(policy.id)} className="text-red-500 hover:text-red-700">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-xs text-zinc-500">
                    Effective from: {policy.effective_from?.split('T')[0]}
                  </div>
                  
                  {/* Leave Types Summary */}
                  <div className="flex flex-wrap gap-2">
                    {policy.leave_types?.slice(0, 5).map((lt, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        {getLeaveTypeLabel(lt.leave_type)}: {lt.annual_quota}d
                      </Badge>
                    ))}
                    {policy.leave_types?.length > 5 && (
                      <Badge variant="outline" className="text-xs">
                        +{policy.leave_types.length - 5} more
                      </Badge>
                    )}
                  </div>
                  
                  {/* Payroll Integration Status */}
                  {policy.payroll_integration?.auto_adjust_salary && (
                    <div className="flex items-center gap-2 text-xs text-emerald-600">
                      <DollarSign className="w-3 h-3" />
                      Payroll Integration Active
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
        
        {policies.length === 0 && (
          <Card className="col-span-2 border-dashed border-2 border-zinc-300">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Calendar className="w-12 h-12 text-zinc-300 mb-4" />
              <p className="text-zinc-500 mb-4">No leave policies configured</p>
              <Button onClick={openNewPolicy} variant="outline">
                <Plus className="w-4 h-4 mr-2" /> Create Your First Policy
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Policy Dialog */}
      <Dialog open={showPolicyDialog} onOpenChange={setShowPolicyDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-orange-500" />
              {editingPolicy ? 'Edit Leave Policy' : 'Create Leave Policy'}
            </DialogTitle>
            <DialogDescription>
              Configure leave entitlements, accrual rules, and payroll integration
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="basic" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="basic">Basic Info</TabsTrigger>
              <TabsTrigger value="leave-types">Leave Types ({policyForm.leave_types?.length || 0})</TabsTrigger>
              <TabsTrigger value="payroll">Payroll Integration</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Policy Name *</Label>
                  <Input
                    value={policyForm.name}
                    onChange={e => setPolicyForm({ ...policyForm, name: e.target.value })}
                    placeholder="e.g., Standard Leave Policy"
                    data-testid="policy-name-input"
                  />
                </div>
                
                <div className="col-span-2">
                  <Label>Description</Label>
                  <Input
                    value={policyForm.description}
                    onChange={e => setPolicyForm({ ...policyForm, description: e.target.value })}
                    placeholder="Brief description of this policy"
                  />
                </div>
                
                <div>
                  <Label>Apply To *</Label>
                  <Select
                    value={policyForm.scope}
                    onValueChange={v => setPolicyForm({ ...policyForm, scope: v, scope_value: null })}
                  >
                    <SelectTrigger data-testid="scope-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="company">All Employees (Company-wide)</SelectItem>
                      <SelectItem value="department">Specific Department</SelectItem>
                      <SelectItem value="role">Specific Role/Designation</SelectItem>
                      <SelectItem value="employee">Specific Employee</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {policyForm.scope === 'department' && (
                  <div>
                    <Label>Department</Label>
                    <Select
                      value={policyForm.scope_value || ''}
                      onValueChange={v => setPolicyForm({ ...policyForm, scope_value: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        {departments.map(d => (
                          <SelectItem key={d.id || d.name} value={d.name}>{d.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                
                {policyForm.scope === 'role' && (
                  <div>
                    <Label>Role/Designation</Label>
                    <Select
                      value={policyForm.scope_value || ''}
                      onValueChange={v => setPolicyForm({ ...policyForm, scope_value: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map(r => (
                          <SelectItem key={r} value={r}>{r}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                
                {policyForm.scope === 'employee' && (
                  <div>
                    <Label>Employee</Label>
                    <Select
                      value={policyForm.scope_value || ''}
                      onValueChange={v => setPolicyForm({ ...policyForm, scope_value: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select employee" />
                      </SelectTrigger>
                      <SelectContent>
                        {employees.map(e => (
                          <SelectItem key={e.id} value={e.id}>
                            {e.first_name} {e.last_name} ({e.employee_id || e.id?.slice(0,8)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                
                <div>
                  <Label>Effective From *</Label>
                  <Input
                    type="date"
                    value={policyForm.effective_from}
                    onChange={e => setPolicyForm({ ...policyForm, effective_from: e.target.value })}
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <Switch
                    checked={policyForm.is_active}
                    onCheckedChange={v => setPolicyForm({ ...policyForm, is_active: v })}
                  />
                  <Label>Active Policy</Label>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="leave-types" className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-zinc-500">Configure leave types and their entitlements</p>
                <Button variant="outline" size="sm" onClick={openAddLeaveType} data-testid="add-leave-type-btn">
                  <Plus className="w-4 h-4 mr-2" /> Add Leave Type
                </Button>
              </div>
              
              <div className="space-y-3">
                {policyForm.leave_types?.map((lt, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg bg-zinc-50">
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="font-medium">{getLeaveTypeLabel(lt.leave_type)}</div>
                        <div className="text-xs text-zinc-500 flex items-center gap-2">
                          <span>{lt.annual_quota} days/year</span>
                          <span>•</span>
                          <span>{lt.accrual_type === 'monthly' ? 'Monthly accrual' : 'Yearly credit'}</span>
                          {lt.carry_forward && <Badge variant="outline" className="text-xs">Carry Forward</Badge>}
                          {lt.encashment_allowed && <Badge variant="outline" className="text-xs">Encashable</Badge>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditLeaveType(lt, index)}>
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => removeLeaveType(index)} className="text-red-500">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                
                {(!policyForm.leave_types || policyForm.leave_types.length === 0) && (
                  <div className="text-center py-8 text-zinc-400">
                    No leave types configured. Click "Add Leave Type" to begin.
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="payroll" className="space-y-4 mt-4">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center gap-2 text-blue-700 font-medium mb-2">
                  <DollarSign className="w-4 h-4" />
                  Payroll Integration
                </div>
                <p className="text-sm text-blue-600">
                  These settings control how leave affects salary calculations (LOP deductions, leave encashment)
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>LOP Deduction Formula</Label>
                  <Select
                    value={policyForm.payroll_integration?.lop_deduction_formula || 'basic_per_day'}
                    onValueChange={v => setPolicyForm({
                      ...policyForm,
                      payroll_integration: { ...policyForm.payroll_integration, lop_deduction_formula: v }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic_per_day">Basic Salary / 30 days</SelectItem>
                      <SelectItem value="gross_per_day">Gross Salary / 30 days</SelectItem>
                      <SelectItem value="fixed">Fixed Amount</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label>Encashment Formula</Label>
                  <Select
                    value={policyForm.payroll_integration?.encashment_formula || 'basic_per_day'}
                    onValueChange={v => setPolicyForm({
                      ...policyForm,
                      payroll_integration: { ...policyForm.payroll_integration, encashment_formula: v }
                    })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic_per_day">Basic Salary / 30 days</SelectItem>
                      <SelectItem value="gross_per_day">Gross Salary / 30 days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-center gap-2">
                  <Switch
                    checked={policyForm.payroll_integration?.auto_adjust_salary ?? true}
                    onCheckedChange={v => setPolicyForm({
                      ...policyForm,
                      payroll_integration: { ...policyForm.payroll_integration, auto_adjust_salary: v }
                    })}
                  />
                  <Label>Auto-adjust salary for LOP</Label>
                </div>
                
                <div className="flex items-center gap-2">
                  <Switch
                    checked={policyForm.payroll_integration?.include_in_full_final ?? true}
                    onCheckedChange={v => setPolicyForm({
                      ...policyForm,
                      payroll_integration: { ...policyForm.payroll_integration, include_in_full_final: v }
                    })}
                  />
                  <Label>Include in Full & Final Settlement</Label>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowPolicyDialog(false)}>Cancel</Button>
            <Button onClick={savePolicy} disabled={saving} className="bg-orange-500 hover:bg-orange-600" data-testid="save-policy-btn">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              {editingPolicy ? 'Update Policy' : 'Create Policy'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Leave Type Dialog */}
      <Dialog open={showLeaveTypeDialog} onOpenChange={setShowLeaveTypeDialog}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingLeaveType !== null ? 'Edit Leave Type' : 'Add Leave Type'}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4 py-4">
            <div>
              <Label>Leave Type *</Label>
              <Select
                value={leaveTypeForm.leave_type}
                onValueChange={v => setLeaveTypeForm({ ...leaveTypeForm, leave_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LEAVE_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Annual Quota (Days) *</Label>
              <Input
                type="number"
                value={leaveTypeForm.annual_quota}
                onChange={e => setLeaveTypeForm({ ...leaveTypeForm, annual_quota: parseFloat(e.target.value) || 0 })}
              />
            </div>
            
            <div>
              <Label>Accrual Type</Label>
              <Select
                value={leaveTypeForm.accrual_type}
                onValueChange={v => setLeaveTypeForm({ ...leaveTypeForm, accrual_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="yearly">Yearly (Credit at year start)</SelectItem>
                  <SelectItem value="monthly">Monthly (Accrue per month)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {leaveTypeForm.accrual_type === 'monthly' && (
              <div>
                <Label>Accrual Rate (Days/Month)</Label>
                <Input
                  type="number"
                  step="0.25"
                  value={leaveTypeForm.accrual_rate || ''}
                  onChange={e => setLeaveTypeForm({ ...leaveTypeForm, accrual_rate: parseFloat(e.target.value) || null })}
                  placeholder={`Auto: ${(leaveTypeForm.annual_quota / 12).toFixed(2)}`}
                />
              </div>
            )}
            
            <div>
              <Label>Min Service Required (Months)</Label>
              <Input
                type="number"
                value={leaveTypeForm.min_service_months}
                onChange={e => setLeaveTypeForm({ ...leaveTypeForm, min_service_months: parseInt(e.target.value) || 0 })}
              />
            </div>
            
            <div>
              <Label>Advance Notice (Days)</Label>
              <Input
                type="number"
                value={leaveTypeForm.advance_notice_days}
                onChange={e => setLeaveTypeForm({ ...leaveTypeForm, advance_notice_days: parseInt(e.target.value) || 0 })}
              />
            </div>
            
            <div className="col-span-2 space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Carry Forward</Label>
                  <p className="text-xs text-zinc-500">Allow unused leave to carry to next year</p>
                </div>
                <Switch
                  checked={leaveTypeForm.carry_forward}
                  onCheckedChange={v => setLeaveTypeForm({ ...leaveTypeForm, carry_forward: v })}
                />
              </div>
              
              {leaveTypeForm.carry_forward && (
                <div>
                  <Label>Max Carry Forward Days</Label>
                  <Input
                    type="number"
                    value={leaveTypeForm.max_carry_forward || ''}
                    onChange={e => setLeaveTypeForm({ ...leaveTypeForm, max_carry_forward: parseFloat(e.target.value) || null })}
                    placeholder="Leave empty for unlimited"
                  />
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <div>
                  <Label>Encashment Allowed</Label>
                  <p className="text-xs text-zinc-500">Allow leave to be encashed in payroll</p>
                </div>
                <Switch
                  checked={leaveTypeForm.encashment_allowed}
                  onCheckedChange={v => setLeaveTypeForm({ ...leaveTypeForm, encashment_allowed: v })}
                />
              </div>
              
              {leaveTypeForm.encashment_allowed && (
                <div>
                  <Label>Max Encashment Days</Label>
                  <Input
                    type="number"
                    value={leaveTypeForm.encashment_max_days || ''}
                    onChange={e => setLeaveTypeForm({ ...leaveTypeForm, encashment_max_days: parseFloat(e.target.value) || null })}
                    placeholder="Leave empty for no limit"
                  />
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <div>
                  <Label>Pro-rata for New Joiners</Label>
                  <p className="text-xs text-zinc-500">Calculate proportionally based on joining date</p>
                </div>
                <Switch
                  checked={leaveTypeForm.pro_rata_for_new_joiners}
                  onCheckedChange={v => setLeaveTypeForm({ ...leaveTypeForm, pro_rata_for_new_joiners: v })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <Label>Can Go Negative (LOP)</Label>
                  <p className="text-xs text-zinc-500">Allow negative balance, deduct from salary</p>
                </div>
                <Switch
                  checked={leaveTypeForm.can_be_negative}
                  onCheckedChange={v => setLeaveTypeForm({ ...leaveTypeForm, can_be_negative: v })}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <Label>Medical Certificate Required</Label>
                  <p className="text-xs text-zinc-500">For sick leave exceeding threshold</p>
                </div>
                <Switch
                  checked={leaveTypeForm.requires_medical_certificate}
                  onCheckedChange={v => setLeaveTypeForm({ ...leaveTypeForm, requires_medical_certificate: v })}
                />
              </div>
              
              {leaveTypeForm.requires_medical_certificate && (
                <div>
                  <Label>Certificate Threshold (Days)</Label>
                  <Input
                    type="number"
                    value={leaveTypeForm.medical_certificate_threshold}
                    onChange={e => setLeaveTypeForm({ ...leaveTypeForm, medical_certificate_threshold: parseInt(e.target.value) || 2 })}
                  />
                </div>
              )}
            </div>
            
            <div className="col-span-2">
              <Label>Description</Label>
              <Input
                value={leaveTypeForm.description}
                onChange={e => setLeaveTypeForm({ ...leaveTypeForm, description: e.target.value })}
                placeholder="Brief description for employees"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLeaveTypeDialog(false)}>Cancel</Button>
            <Button onClick={saveLeaveType} className="bg-orange-500 hover:bg-orange-600">
              {editingLeaveType !== null ? 'Update' : 'Add'} Leave Type
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LeavePolicySettings;
