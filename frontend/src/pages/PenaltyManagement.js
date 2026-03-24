import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AuthContext } from '../App';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  AlertTriangle, Search, Filter, Plus, Trash2, Shield, 
  FileWarning, Clock, Plane, Receipt, Users, RefreshCw,
  ChevronDown, Eye, Ban, CheckCircle2, XCircle
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_ICONS = {
  attendance: Clock,
  leave: FileWarning,
  travel: Plane,
  expense: Receipt,
  general: Shield,
};

const CATEGORY_COLORS = {
  attendance: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  leave: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  travel: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  expense: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  general: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-900/30 dark:text-zinc-300',
};

export default function PenaltyManagement() {
  const { user } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('apply');
  const [categories, setCategories] = useState({});
  const [employees, setEmployees] = useState([]);
  const [monthPenalties, setMonthPenalties] = useState(null);
  const [detectedViolations, setDetectedViolations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [detectLoading, setDetectLoading] = useState(false);

  // Apply form state
  const [selectedMonth, setSelectedMonth] = useState(
    new Date().toISOString().slice(0, 7)
  );
  const [formData, setFormData] = useState({
    employee_id: '',
    violation_code: '',
    amount: '',
    description: '',
    apply_to_payroll: true,
  });
  const [selectedCategory, setSelectedCategory] = useState('');
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [showEmployeeDropdown, setShowEmployeeDropdown] = useState(false);

  // Filter state for monthly view
  const [filterCategory, setFilterCategory] = useState('all');

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  });

  // Fetch categories and employees on mount
  useEffect(() => {
    fetchCategories();
    fetchEmployees();
  }, []);

  // Fetch month penalties when month changes
  useEffect(() => {
    if (selectedMonth) fetchMonthPenalties();
  }, [selectedMonth]);

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API}/api/penalties/categories`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || {});
      }
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API}/api/employees`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setEmployees(Array.isArray(data) ? data : data.employees || []);
      }
    } catch (err) {
      console.error('Failed to fetch employees:', err);
    }
  };

  const fetchMonthPenalties = useCallback(async () => {
    if (!selectedMonth) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/penalties/month/${selectedMonth}`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setMonthPenalties(data);
      }
    } catch (err) {
      console.error('Failed to fetch month penalties:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedMonth]);

  const handleApplyPenalty = async (e) => {
    e.preventDefault();
    if (!formData.employee_id || !formData.violation_code) {
      toast.error('Please select employee and violation type');
      return;
    }

    try {
      const payload = {
        employee_id: formData.employee_id,
        month: selectedMonth,
        violation_code: formData.violation_code,
        amount: formData.amount ? parseFloat(formData.amount) : undefined,
        description: formData.description,
        apply_to_payroll: formData.apply_to_payroll,
      };

      const res = await fetch(`${API}/api/penalties/apply`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || 'Penalty applied successfully');
        setFormData({ employee_id: '', violation_code: '', amount: '', description: '', apply_to_payroll: true });
        setSelectedCategory('');
        setEmployeeSearch('');
        fetchMonthPenalties();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to apply penalty');
      }
    } catch (err) {
      toast.error('Network error');
    }
  };

  const handleRevokePenalty = async (penaltyId) => {
    if (!window.confirm('Are you sure you want to revoke this penalty?')) return;
    try {
      const res = await fetch(`${API}/api/penalties/${penaltyId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });
      if (res.ok) {
        toast.success('Penalty revoked');
        fetchMonthPenalties();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to revoke');
      }
    } catch (err) {
      toast.error('Network error');
    }
  };

  const handleAutoDetect = async () => {
    setDetectLoading(true);
    try {
      const res = await fetch(`${API}/api/penalties/auto-detect/${selectedMonth}`, {
        method: 'POST',
        headers: getHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setDetectedViolations(data.detected_violations || []);
        if ((data.detected_violations || []).length === 0) {
          toast.info('No violations detected for this month');
        } else {
          toast.success(`${data.total_detected} potential violations detected`);
          setActiveTab('auto-detect');
        }
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Auto-detection failed');
      }
    } catch (err) {
      toast.error('Network error');
    } finally {
      setDetectLoading(false);
    }
  };

  const handleApplyDetected = async (violation) => {
    try {
      const payload = {
        employee_id: violation.employee_id,
        month: selectedMonth,
        violation_code: violation.violation_code,
        description: violation.description,
        reference_id: violation.reference_id,
        apply_to_payroll: true,
      };
      const res = await fetch(`${API}/api/penalties/apply`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        toast.success(`Penalty applied for ${violation.employee_name}`);
        setDetectedViolations(prev => (prev || []).filter(v => v !== violation));
        fetchMonthPenalties();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to apply');
      }
    } catch (err) {
      toast.error('Network error');
    }
  };

  // Get violations for selected category
  const getViolationsForCategory = (catKey) => {
    const cat = categories[catKey];
    return cat ? cat.violations || [] : [];
  };

  // Get default amount for a violation code
  const getDefaultAmount = (code) => {
    for (const cat of Object.values(categories)) {
      for (const v of cat.violations || []) {
        if (v.code === code) return v.default_amount;
      }
    }
    return 0;
  };

  // Filter employees by search
  const filteredEmployees = (employees || []).filter(emp => {
    if (!employeeSearch) return true;
    const q = employeeSearch.toLowerCase();
    const name = `${emp.first_name || ''} ${emp.last_name || ''}`.toLowerCase();
    const code = (emp.employee_id || '').toLowerCase();
    return name.includes(q) || code.includes(q);
  });

  // Get selected employee name
  const getSelectedEmployeeName = () => {
    const emp = (employees || []).find(e => e.id === formData.employee_id);
    if (!emp) return '';
    return `${emp.employee_id || ''} - ${emp.first_name || ''} ${emp.last_name || ''}`;
  };

  // Get all penalties flat from month data
  const getAllPenalties = () => {
    if (!monthPenalties?.by_category) return [];
    const all = [];
    for (const [catKey, catData] of Object.entries(monthPenalties.by_category || {})) {
      for (const p of catData.penalties || []) {
        all.push({ ...p, _category: catKey });
      }
    }
    return all;
  };

  const filteredPenalties = getAllPenalties().filter(p => {
    if (filterCategory === 'all') return true;
    return p._category === filterCategory;
  });

  return (
    <div className="space-y-6" data-testid="penalty-management">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            Penalty Management
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Apply, review, and manage policy violation penalties across all categories
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Input
            type="month"
            value={selectedMonth}
            onChange={e => setSelectedMonth(e.target.value)}
            className="w-44"
            data-testid="penalty-month-picker"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleAutoDetect}
            disabled={detectLoading}
            data-testid="auto-detect-btn"
          >
            {detectLoading ? <RefreshCw className="w-4 h-4 animate-spin mr-1" /> : <Search className="w-4 h-4 mr-1" />}
            Auto-Detect
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {monthPenalties && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="penalty-summary-cards">
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Total Penalties</p>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1" data-testid="total-penalty-count">
                {monthPenalties.total_penalties || 0}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Total Amount</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1" data-testid="total-penalty-amount">
                {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(monthPenalties.total_amount || 0)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Employees Affected</p>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1" data-testid="employees-affected-count">
                {monthPenalties.employees_affected || 0}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-3 px-4">
              <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Categories Active</p>
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1">
                {Object.keys(monthPenalties.by_category || {}).length}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="apply" data-testid="tab-apply-penalty">
            <Plus className="w-4 h-4 mr-1" /> Apply Penalty
          </TabsTrigger>
          <TabsTrigger value="review" data-testid="tab-review-penalties">
            <Eye className="w-4 h-4 mr-1" /> Review ({monthPenalties?.total_penalties || 0})
          </TabsTrigger>
          <TabsTrigger value="auto-detect" data-testid="tab-auto-detect">
            <Search className="w-4 h-4 mr-1" /> Auto-Detect ({(detectedViolations || []).length})
          </TabsTrigger>
        </TabsList>

        {/* === APPLY PENALTY TAB === */}
        <TabsContent value="apply">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Apply Policy Violation Penalty</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleApplyPenalty} className="space-y-5">
                {/* Employee Selection */}
                <div className="relative">
                  <Label className="text-sm font-medium">Employee *</Label>
                  <div className="mt-1 relative">
                    <Input
                      placeholder="Search employee by name or ID..."
                      value={formData.employee_id ? getSelectedEmployeeName() : employeeSearch}
                      onChange={e => {
                        setEmployeeSearch(e.target.value);
                        setFormData(prev => ({ ...prev, employee_id: '' }));
                        setShowEmployeeDropdown(true);
                      }}
                      onFocus={() => setShowEmployeeDropdown(true)}
                      data-testid="employee-search-input"
                    />
                    {showEmployeeDropdown && employeeSearch && (
                      <div className="absolute z-50 top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg shadow-lg">
                        {filteredEmployees.length === 0 ? (
                          <p className="p-3 text-sm text-zinc-500">No employees found</p>
                        ) : (
                          (filteredEmployees || []).slice(0, 10).map(emp => (
                            <button
                              key={emp.id}
                              type="button"
                              className="w-full text-left px-3 py-2 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-sm flex justify-between"
                              onClick={() => {
                                setFormData(prev => ({ ...prev, employee_id: emp.id }));
                                setEmployeeSearch('');
                                setShowEmployeeDropdown(false);
                              }}
                              data-testid={`employee-option-${emp.employee_id}`}
                            >
                              <span className="font-medium">{emp.first_name} {emp.last_name}</span>
                              <span className="text-zinc-400">{emp.employee_id} - {emp.department || 'N/A'}</span>
                            </button>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                  {formData.employee_id && (
                    <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-400">
                      Selected: {getSelectedEmployeeName()}
                    </p>
                  )}
                </div>

                {/* Category & Violation Selection */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Penalty Category *</Label>
                    <select
                      className="mt-1 w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
                      value={selectedCategory}
                      onChange={e => {
                        setSelectedCategory(e.target.value);
                        setFormData(prev => ({ ...prev, violation_code: '', amount: '' }));
                      }}
                      data-testid="category-select"
                    >
                      <option value="">Select category...</option>
                      {Object.entries(categories || {}).map(([key, cat]) => (
                        <option key={key} value={key}>{cat.name} ({(cat.violations || []).length} types)</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Violation Type *</Label>
                    <select
                      className="mt-1 w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
                      value={formData.violation_code}
                      onChange={e => {
                        const code = e.target.value;
                        const defaultAmt = getDefaultAmount(code);
                        setFormData(prev => ({
                          ...prev,
                          violation_code: code,
                          amount: defaultAmt > 0 ? String(defaultAmt) : '',
                        }));
                      }}
                      disabled={!selectedCategory}
                      data-testid="violation-type-select"
                    >
                      <option value="">Select violation...</option>
                      {getViolationsForCategory(selectedCategory).map(v => (
                        <option key={v.code} value={v.code}>
                          {v.name} {v.default_amount > 0 ? `(Default: ${v.default_amount})` : '(Amount required)'}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Amount & Description */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Penalty Amount (INR)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="1"
                      placeholder="Enter amount or use default"
                      value={formData.amount}
                      onChange={e => setFormData(prev => ({ ...prev, amount: e.target.value }))}
                      className="mt-1"
                      data-testid="penalty-amount-input"
                    />
                    {formData.violation_code && (
                      <p className="text-xs text-zinc-500 mt-1">
                        Default: {getDefaultAmount(formData.violation_code) > 0 ? `INR ${getDefaultAmount(formData.violation_code)}` : 'No default - enter custom amount'}
                      </p>
                    )}
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Description / Reason</Label>
                    <Input
                      placeholder="Describe the violation..."
                      value={formData.description}
                      onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      className="mt-1"
                      data-testid="penalty-description-input"
                    />
                  </div>
                </div>

                {/* Apply to Payroll Toggle */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="apply-to-payroll"
                    checked={formData.apply_to_payroll}
                    onChange={e => setFormData(prev => ({ ...prev, apply_to_payroll: e.target.checked }))}
                    className="rounded"
                    data-testid="apply-to-payroll-checkbox"
                  />
                  <Label htmlFor="apply-to-payroll" className="text-sm cursor-pointer">
                    Deduct from next payroll ({selectedMonth})
                  </Label>
                </div>

                <Button type="submit" className="w-full sm:w-auto" data-testid="submit-penalty-btn">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Apply Penalty
                </Button>
              </form>

              {/* Quick Reference: All 21 Violation Types */}
              <div className="mt-8 border-t pt-6">
                <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">
                  All Violation Types ({Object.values(categories || {}).reduce((sum, cat) => sum + (cat.violations || []).length, 0)})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Object.entries(categories || {}).map(([catKey, cat]) => {
                    const Icon = CATEGORY_ICONS[catKey] || Shield;
                    return (
                      <div key={catKey} className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Icon className="w-4 h-4 text-zinc-500" />
                          <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                            {cat.name}
                          </span>
                        </div>
                        <div className="space-y-1">
                          {(cat.violations || []).map(v => (
                            <div key={v.code} className="flex justify-between text-xs">
                              <span className="text-zinc-600 dark:text-zinc-400">{v.name}</span>
                              <span className="font-medium text-zinc-800 dark:text-zinc-200">
                                {v.default_amount > 0 ? `INR ${v.default_amount}` : 'Custom'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* === REVIEW PENALTIES TAB === */}
        <TabsContent value="review">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Monthly Penalties - {selectedMonth}</CardTitle>
              <div className="flex items-center gap-2">
                <select
                  className="text-sm rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-2 py-1"
                  value={filterCategory}
                  onChange={e => setFilterCategory(e.target.value)}
                  data-testid="filter-category-select"
                >
                  <option value="all">All Categories</option>
                  {Object.entries(monthPenalties?.by_category || {}).map(([key, val]) => (
                    <option key={key} value={key}>{key} ({val.count})</option>
                  ))}
                </select>
                <Button variant="ghost" size="sm" onClick={fetchMonthPenalties} data-testid="refresh-penalties-btn">
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-zinc-400" />
                </div>
              ) : filteredPenalties.length === 0 ? (
                <div className="text-center py-10">
                  <Shield className="w-10 h-10 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
                  <p className="text-zinc-500 dark:text-zinc-400">No penalties for {selectedMonth}</p>
                  <p className="text-xs text-zinc-400 mt-1">Use "Apply Penalty" tab or "Auto-Detect" to add penalties</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" data-testid="penalties-table">
                    <thead>
                      <tr className="border-b border-zinc-200 dark:border-zinc-700">
                        <th className="text-left p-2 font-medium text-zinc-500">Employee</th>
                        <th className="text-left p-2 font-medium text-zinc-500">Category</th>
                        <th className="text-left p-2 font-medium text-zinc-500">Violation</th>
                        <th className="text-right p-2 font-medium text-zinc-500">Amount</th>
                        <th className="text-left p-2 font-medium text-zinc-500">Reason</th>
                        <th className="text-left p-2 font-medium text-zinc-500">Applied By</th>
                        <th className="text-center p-2 font-medium text-zinc-500">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(filteredPenalties || []).map((p, idx) => {
                        const catColor = CATEGORY_COLORS[p._category] || CATEGORY_COLORS.general;
                        return (
                          <tr key={p.id || idx} className="border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                            <td className="p-2">
                              <div className="font-medium text-zinc-800 dark:text-zinc-200">
                                {p.employee_name || '-'}
                              </div>
                              <div className="text-xs text-zinc-400">{p.employee_code || p.department || '-'}</div>
                            </td>
                            <td className="p-2">
                              <Badge className={`text-xs ${catColor}`}>
                                {p.category_name || p._category || '-'}
                              </Badge>
                            </td>
                            <td className="p-2 text-zinc-700 dark:text-zinc-300">
                              {p.violation_name || p.name || '-'}
                            </td>
                            <td className="p-2 text-right font-semibold text-red-600 dark:text-red-400">
                              {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(p.amount || p.penalty_amount || 0)}
                            </td>
                            <td className="p-2 text-xs text-zinc-500 max-w-[200px] truncate">
                              {p.description || p.reason || '-'}
                            </td>
                            <td className="p-2 text-xs text-zinc-500">
                              {p.created_by_name || '-'}
                            </td>
                            <td className="p-2 text-center">
                              {p.id && p._category !== 'attendance_late' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                                  onClick={() => handleRevokePenalty(p.id)}
                                  data-testid={`revoke-btn-${p.id}`}
                                >
                                  <Ban className="w-3.5 h-3.5 mr-1" /> Revoke
                                </Button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Category Breakdown */}
              {monthPenalties && Object.keys(monthPenalties.by_category || {}).length > 0 && (
                <div className="mt-6 pt-4 border-t border-zinc-200 dark:border-zinc-700">
                  <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Category Breakdown</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {Object.entries(monthPenalties.by_category || {}).map(([key, data]) => {
                      const Icon = CATEGORY_ICONS[key] || Shield;
                      return (
                        <div key={key} className="border rounded-lg p-3 border-zinc-200 dark:border-zinc-700">
                          <div className="flex items-center gap-1.5 mb-1">
                            <Icon className="w-3.5 h-3.5 text-zinc-400" />
                            <span className="text-xs font-medium text-zinc-500 capitalize">{key.replace('_', ' ')}</span>
                          </div>
                          <p className="text-lg font-bold text-zinc-900 dark:text-zinc-50">{data.count}</p>
                          <p className="text-xs text-red-500">
                            {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.total_amount || 0)}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === AUTO-DETECT TAB === */}
        <TabsContent value="auto-detect">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Auto-Detected Violations - {selectedMonth}</CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAutoDetect}
                disabled={detectLoading}
                data-testid="run-detection-btn"
              >
                {detectLoading ? <RefreshCw className="w-4 h-4 animate-spin mr-1" /> : <Search className="w-4 h-4 mr-1" />}
                Run Detection
              </Button>
            </CardHeader>
            <CardContent>
              {(detectedViolations || []).length === 0 ? (
                <div className="text-center py-10">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
                  <p className="text-zinc-500 dark:text-zinc-400">No violations detected</p>
                  <p className="text-xs text-zinc-400 mt-1">Click "Run Detection" to scan for policy violations in {selectedMonth}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-zinc-500 mb-2">
                    {(detectedViolations || []).length} potential violations found. Review and apply as needed.
                  </p>
                  {(detectedViolations || []).map((v, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 border border-amber-200 dark:border-amber-800 rounded-lg bg-amber-50/50 dark:bg-amber-900/10"
                      data-testid={`detected-violation-${idx}`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm text-zinc-800 dark:text-zinc-200">
                            {v.employee_name || 'Unknown Employee'}
                          </span>
                          <Badge variant="outline" className="text-xs">{v.employee_code}</Badge>
                          <Badge className={`text-xs ${CATEGORY_COLORS[v.violation_code?.split('_')[0]?.toLowerCase()] || CATEGORY_COLORS.general}`}>
                            {v.violation_code}
                          </Badge>
                        </div>
                        <p className="text-xs text-zinc-600 dark:text-zinc-400">{v.description}</p>
                        {v.suggested_action && (
                          <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                            Suggested: {v.suggested_action}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <Button
                          size="sm"
                          onClick={() => handleApplyDetected(v)}
                          className="bg-red-600 hover:bg-red-700 text-white"
                          data-testid={`apply-detected-${idx}`}
                        >
                          <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Apply
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDetectedViolations(prev => (prev || []).filter((_, i) => i !== idx))}
                          data-testid={`dismiss-detected-${idx}`}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
