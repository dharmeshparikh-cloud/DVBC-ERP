import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { 
  Target, DollarSign, Users, Calendar, Save, Plus, 
  Edit2, Trash2, RefreshCw, TrendingUp, BarChart3
} from 'lucide-react';
import { toast } from 'sonner';

const TargetManagement = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState(null);
  const [formData, setFormData] = useState({
    employee_id: '',
    year: new Date().getFullYear(),
    monthly_targets: {
      '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0,
      '7': 0, '8': 0, '9': 0, '10': 0, '11': 0, '12': 0
    },
    target_type: 'revenue' // revenue, closures, meetings
  });

  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];

  // React Query: Targets
  const { data: targets = [], isLoading: loadingTargets } = useQuery({
    queryKey: ['sales-targets', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`${API}/sales-targets?year=${selectedYear}`);
      const targetsData = res.data?.items || res.data || [];
      return Array.isArray(targetsData) ? targetsData : [];
    },
    staleTime: 2 * 60 * 1000,
  });

  // React Query: Subordinates
  const { data: subordinates = [] } = useQuery({
    queryKey: ['manager', 'subordinate-leads'],
    queryFn: async () => {
      const res = await axios.get(`${API}/manager/subordinate-leads`);
      const subData = res.data?.subordinates || res.data?.items || [];
      return Array.isArray(subData) ? subData : [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: KPI Data
  const { data: kpiData } = useQuery({
    queryKey: ['manager', 'target-vs-achievement', selectedYear],
    queryFn: async () => {
      const res = await axios.get(`${API}/manager/target-vs-achievement?year=${selectedYear}`);
      return res.data || {};
    },
    staleTime: 2 * 60 * 1000,
  });
  const totalClients = kpiData?.total_clients || 0;
  const loading = loadingTargets;

  // Mutation: Save Target
  const saveMutation = useMutation({
    mutationFn: async (data) => {
      if (editingTarget) {
        await axios.patch(`${API}/sales-targets/${editingTarget.id}`, data);
      } else {
        await axios.post(`${API}/sales-targets`, data);
      }
    },
    onSuccess: () => {
      toast.success(editingTarget ? 'Target updated successfully' : 'Target created successfully');
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['sales-targets'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save target');
    },
  });

  // Mutation: Delete Target
  const deleteMutation = useMutation({
    mutationFn: async (targetId) => {
      await axios.delete(`${API}/sales-targets/${targetId}`);
    },
    onSuccess: () => {
      toast.success('Target deleted');
      queryClient.invalidateQueries({ queryKey: ['sales-targets'] });
    },
    onError: () => {
      toast.error('Failed to delete target');
    },
  });

  const handleOpenDialog = (target = null) => {
    if (target) {
      setEditingTarget(target);
      setFormData({
        employee_id: target.employee_id,
        year: target.year,
        monthly_targets: target.monthly_targets || {},
        target_type: target.target_type || 'revenue'
      });
    } else {
      setEditingTarget(null);
      setFormData({
        employee_id: '',
        year: selectedYear,
        monthly_targets: {
          '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0,
          '7': 0, '8': 0, '9': 0, '10': 0, '11': 0, '12': 0
        },
        target_type: 'revenue'
      });
    }
    setDialogOpen(true);
  };

  const handleMonthChange = (month, value) => {
    setFormData(prev => ({
      ...prev,
      monthly_targets: {
        ...prev.monthly_targets,
        [month]: parseFloat(value) || 0
      }
    }));
  };

  const handleApplyToAll = (value) => {
    const newTargets = {};
    for (let i = 1; i <= 12; i++) {
      newTargets[i.toString()] = parseFloat(value) || 0;
    }
    setFormData(prev => ({
      ...prev,
      monthly_targets: newTargets
    }));
  };

  const handleSave = async () => {
    if (!formData.employee_id) {
      toast.error('Please select an employee');
      return;
    }
    saveMutation.mutate(formData);
  };

  const handleDelete = async (targetId) => {
    if (!confirm('Are you sure you want to delete this target?')) return;
    deleteMutation.mutate(targetId);
  };

  const formatCurrency = (value) => {
    if (!value) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  const getYearTotal = (target) => {
    if (!target.monthly_targets) return 0;
    return Object.values(target.monthly_targets).reduce((sum, val) => sum + (val || 0), 0);
  };

  const getEmployeeName = (empId) => {
    const emp = subordinates.find(s => s.employee_id === empId || s.id === empId);
    return emp ? `${emp.first_name} ${emp.last_name}` : empId;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6" data-testid="target-management-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900" data-testid="target-management-title">Target Management</h1>
          <p className="text-sm text-zinc-500">Set and manage monthly sales targets for your team</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="px-3 py-2 border border-zinc-200 rounded-sm bg-white text-sm"
            data-testid="year-selector"
          >
            {[2024, 2025, 2026, 2027].map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
          <Button onClick={() => handleOpenDialog()} className="bg-zinc-950 hover:bg-zinc-800 rounded-sm" data-testid="add-target-btn">
            <Plus className="w-4 h-4 mr-2" /> Add Target
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="summary-cards">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Targets Set</p>
                <p className="text-2xl font-semibold text-zinc-900">{targets.length}</p>
              </div>
              <Target className="w-8 h-8 text-blue-500/30" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Team Members</p>
                <p className="text-2xl font-semibold text-zinc-900">{subordinates.length}</p>
              </div>
              <Users className="w-8 h-8 text-emerald-500/30" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Clients in Funnel</p>
                <p className="text-2xl font-semibold text-blue-600">{totalClients}</p>
              </div>
              <BarChart3 className="w-8 h-8 text-blue-500/30" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Total Annual Target</p>
                <p className="text-2xl font-semibold text-emerald-600">
                  {formatCurrency(targets.filter(t => t.target_type === 'revenue').reduce((sum, t) => sum + getYearTotal(t), 0))}
                </p>
              </div>
              <DollarSign className="w-8 h-8 text-emerald-500/30" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Targets Table */}
      <Card className="border-zinc-200 shadow-none rounded-sm overflow-hidden">
        <CardHeader className="pb-2 border-b border-zinc-100">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            {selectedYear} Sales Targets
          </CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-zinc-50 border-b border-zinc-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase sticky left-0 bg-zinc-50">Employee</th>
                {months.map((month, idx) => (
                  <th key={idx} className="text-center px-2 py-3 text-xs font-medium text-zinc-500 uppercase min-w-[70px]">
                    {month}
                  </th>
                ))}
                <th className="text-center px-4 py-3 text-xs font-medium text-zinc-500 uppercase bg-emerald-50">Total</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-zinc-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {targets.length === 0 ? (
                <tr>
                  <td colSpan={15} className="px-4 py-8 text-center text-zinc-500">
                    No targets set for {selectedYear}. Click "Add Target" to get started.
                  </td>
                </tr>
              ) : (
                targets.map(target => (
                  <tr key={target.id} className="hover:bg-zinc-50">
                    <td className="px-4 py-3 font-medium text-zinc-900 sticky left-0 bg-white">
                      {getEmployeeName(target.employee_id)}
                      <Badge className="ml-2 text-[10px]" variant="outline">
                        {target.target_type}
                      </Badge>
                    </td>
                    {months.map((_, idx) => (
                      <td key={idx} className="text-center px-2 py-3 text-sm text-zinc-600">
                        {target.target_type === 'revenue' 
                          ? formatCurrency(target.monthly_targets?.[idx + 1] || 0).replace('₹', '')
                          : target.monthly_targets?.[idx + 1] || 0
                        }
                      </td>
                    ))}
                    <td className="text-center px-4 py-3 font-semibold text-emerald-600 bg-emerald-50/50">
                      {target.target_type === 'revenue'
                        ? formatCurrency(getYearTotal(target))
                        : getYearTotal(target)
                      }
                    </td>
                    <td className="text-center px-4 py-3">
                      <div className="flex justify-center gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenDialog(target)}
                          className="h-8 w-8 p-0"
                        >
                          <Edit2 className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDelete(target.id)}
                          className="h-8 w-8 p-0 text-red-600 border-red-200 hover:bg-red-50"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add/Edit Target Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-blue-500" />
              {editingTarget ? 'Edit Target' : 'Add New Target'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Employee & Type Selection */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Employee</Label>
                <select
                  value={formData.employee_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, employee_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-zinc-200 rounded-sm bg-white text-sm mt-1"
                  disabled={editingTarget}
                >
                  <option value="">Select Employee</option>
                  {subordinates.map(sub => (
                    <option key={sub.id} value={sub.employee_id}>
                      {sub.first_name} {sub.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Target Type</Label>
                <select
                  value={formData.target_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, target_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-zinc-200 rounded-sm bg-white text-sm mt-1"
                >
                  <option value="revenue">Revenue (₹)</option>
                  <option value="closures">Closures (Count)</option>
                  <option value="meetings">Meetings (Count)</option>
                </select>
              </div>
            </div>

            {/* Quick Apply */}
            <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-sm">
              <Label className="text-sm whitespace-nowrap">Quick Apply:</Label>
              <Input
                type="number"
                placeholder="Enter value"
                className="w-32 rounded-sm"
                onChange={(e) => {}}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleApplyToAll(e.target.value);
                    toast.success('Applied to all months');
                  }
                }}
              />
              <span className="text-xs text-zinc-500">Press Enter to apply to all months</span>
            </div>

            {/* Monthly Targets Grid */}
            <div>
              <Label className="mb-3 block">Monthly Targets</Label>
              <div className="grid grid-cols-4 gap-3">
                {months.map((month, idx) => (
                  <div key={idx} className="space-y-1">
                    <Label className="text-xs text-zinc-500">{month}</Label>
                    <Input
                      type="number"
                      value={formData.monthly_targets[(idx + 1).toString()] || ''}
                      onChange={(e) => handleMonthChange((idx + 1).toString(), e.target.value)}
                      className="rounded-sm"
                      placeholder="0"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Total */}
            <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-sm">
              <span className="font-medium text-emerald-800">Annual Total</span>
              <span className="text-2xl font-semibold text-emerald-600">
                {formData.target_type === 'revenue'
                  ? formatCurrency(Object.values(formData.monthly_targets).reduce((sum, val) => sum + (val || 0), 0))
                  : Object.values(formData.monthly_targets).reduce((sum, val) => sum + (val || 0), 0)
                }
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} className="bg-zinc-950 hover:bg-zinc-800">
              <Save className="w-4 h-4 mr-2" />
              {editingTarget ? 'Update Target' : 'Save Target'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TargetManagement;
