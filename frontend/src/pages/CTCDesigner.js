import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Calculator, IndianRupee, Building2, Calendar, Send, 
  CheckCircle, XCircle, Clock, FileText, AlertCircle,
  ChevronRight, PiggyBank, Heart, Car, Wallet, Gift, Settings,
  Plus, Minus, Edit2, Save, ToggleLeft
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Default component master (fallback)
const DEFAULT_COMPONENTS = [
  { key: "basic", name: "Basic Salary", calc_type: "percentage_of_ctc", default_value: 40, is_mandatory: true, is_earning: true, enabled_by_default: true, order: 1 },
  { key: "hra", name: "House Rent Allowance", calc_type: "percentage_of_basic", default_value: 50, is_earning: true, enabled_by_default: true, order: 2 },
  { key: "da", name: "Dearness Allowance", calc_type: "percentage_of_basic", default_value: 10, is_earning: true, enabled_by_default: false, order: 3 },
  { key: "conveyance", name: "Conveyance Allowance", calc_type: "fixed_monthly", default_value: 1600, is_earning: true, is_taxable: false, enabled_by_default: true, order: 4 },
  { key: "medical", name: "Medical Allowance", calc_type: "fixed_monthly", default_value: 1250, is_earning: true, is_taxable: false, enabled_by_default: true, order: 5 },
  { key: "special_allowance", name: "Special Allowance", calc_type: "balance", default_value: 0, is_mandatory: true, is_earning: true, enabled_by_default: true, order: 6, is_balance: true },
  { key: "pf_employer", name: "PF (Employer)", calc_type: "percentage_of_basic", default_value: 12, is_earning: false, is_deferred: true, enabled_by_default: false, order: 7 },
  { key: "pf_employee", name: "PF (Employee Deduction)", calc_type: "percentage_of_basic", default_value: 12, is_earning: false, is_deduction: true, enabled_by_default: false, order: 8 },
  { key: "esic_employer", name: "ESIC (Employer)", calc_type: "percentage_of_gross", default_value: 3.25, is_earning: false, is_deferred: true, enabled_by_default: false, order: 9 },
  { key: "esic_employee", name: "ESIC (Employee Deduction)", calc_type: "percentage_of_gross", default_value: 0.75, is_earning: false, is_deduction: true, enabled_by_default: false, order: 10 },
  { key: "gratuity", name: "Gratuity", calc_type: "percentage_of_basic", default_value: 4.81, is_earning: false, is_deferred: true, enabled_by_default: false, order: 11 },
  { key: "professional_tax", name: "Professional Tax", calc_type: "fixed_monthly", default_value: 200, is_earning: false, is_deduction: true, enabled_by_default: false, order: 12 },
];

const CTCDesigner = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const isAdmin = user?.role === 'admin';

  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [annualCTC, setAnnualCTC] = useState('');
  const [retentionBonus, setRetentionBonus] = useState('');
  const [vestingMonths, setVestingMonths] = useState(12);
  const [effectiveMonth, setEffectiveMonth] = useState('');
  const [remarks, setRemarks] = useState('');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Component configuration
  const [componentMaster, setComponentMaster] = useState([]);
  const [componentConfig, setComponentConfig] = useState([]);
  const [showComponentSettings, setShowComponentSettings] = useState(false);

  // Pending approvals (Admin only)
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [approvalDialog, setApprovalDialog] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [adminRemarks, setAdminRemarks] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  // Stats
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchEmployees();
    fetchComponentMaster();
    if (isAdmin) {
      fetchPendingApprovals();
      fetchStats();
    }
    const now = new Date();
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    setEffectiveMonth(nextMonth.toISOString().slice(0, 7));
  }, [isAdmin]);

  const fetchEmployees = async () => {
    try {
      const res = await axios.get(`${API}/employees`);
      // Include employees where is_active is true OR not set (null/undefined)
      setEmployees(res.data.filter(e => e.is_active !== false));
    } catch (err) {
      toast.error('Failed to load employees');
    }
  };

  const fetchComponentMaster = async () => {
    try {
      const res = await axios.get(`${API}/api/ctc/component-master`);
      const components = res.data.components || DEFAULT_COMPONENTS;
      setComponentMaster(components);
      // Initialize component config with enabled status
      const config = components.map(c => ({
        ...c,
        enabled: c.enabled_by_default !== false,
        value: c.default_value
      }));
      setComponentConfig(config);
    } catch (err) {
      console.error('Failed to fetch component master, using defaults');
      setComponentMaster(DEFAULT_COMPONENTS);
      const config = DEFAULT_COMPONENTS.map(c => ({
        ...c,
        enabled: c.enabled_by_default !== false,
        value: c.default_value
      }));
      setComponentConfig(config);
    }
  };

  const fetchPendingApprovals = async () => {
    try {
      const res = await axios.get(`${API}/api/ctc/pending-approvals`);
      setPendingApprovals(res.data);
    } catch (err) {
      console.error('Failed to fetch pending approvals');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API}/api/ctc/stats`);
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats');
    }
  };

  const toggleComponent = (key) => {
    const comp = componentConfig.find(c => c.key === key);
    if (comp?.is_mandatory) {
      toast.error(`${comp.name} is mandatory and cannot be disabled`);
      return;
    }
    setComponentConfig(prev => prev.map(c => 
      c.key === key ? { ...c, enabled: !c.enabled } : c
    ));
  };

  const updateComponentValue = (key, value) => {
    setComponentConfig(prev => prev.map(c => 
      c.key === key ? { ...c, value: parseFloat(value) || 0 } : c
    ));
  };

  const handlePreview = async () => {
    if (!annualCTC || parseFloat(annualCTC) <= 0) {
      toast.error('Please enter a valid Annual CTC');
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/api/ctc/calculate-preview`, {
        annual_ctc: parseFloat(annualCTC),
        retention_bonus: parseFloat(retentionBonus) || 0,
        retention_vesting_months: vestingMonths,
        component_config: componentConfig
      });
      setPreview(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to calculate preview');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedEmployee) {
      toast.error('Please select an employee');
      return;
    }
    if (!annualCTC || parseFloat(annualCTC) <= 0) {
      toast.error('Please enter a valid Annual CTC');
      return;
    }
    if (!effectiveMonth) {
      toast.error('Please select effective month');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/api/ctc/design`, {
        employee_id: selectedEmployee.id,
        annual_ctc: parseFloat(annualCTC),
        retention_bonus: parseFloat(retentionBonus) || 0,
        retention_vesting_months: vestingMonths,
        effective_month: effectiveMonth,
        component_config: componentConfig,
        remarks: remarks
      });
      toast.success('CTC structure submitted for Admin approval');
      setSelectedEmployee(null);
      setAnnualCTC('');
      setRetentionBonus('');
      setRemarks('');
      setPreview(null);
      // Reset component config
      fetchComponentMaster();
      if (isAdmin) {
        fetchPendingApprovals();
        fetchStats();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit CTC structure');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/ctc/${selectedApproval.id}/approve`, {
        remarks: adminRemarks
      });
      toast.success('CTC structure approved successfully');
      setApprovalDialog(false);
      setSelectedApproval(null);
      setAdminRemarks('');
      fetchPendingApprovals();
      fetchStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval) return;
    if (!rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/ctc/${selectedApproval.id}/reject`, {
        reason: rejectionReason
      });
      toast.success('CTC structure rejected');
      setApprovalDialog(false);
      setSelectedApproval(null);
      setRejectionReason('');
      fetchPendingApprovals();
      fetchStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const componentIcons = {
    basic: Wallet,
    hra: Building2,
    da: IndianRupee,
    conveyance: Car,
    medical: Heart,
    special_allowance: Gift,
    pf_employer: PiggyBank,
    pf_employee: PiggyBank,
    esic_employer: Heart,
    esic_employee: Heart,
    gratuity: PiggyBank,
    retention_bonus: Gift,
    professional_tax: FileText
  };

  const getCalcTypeLabel = (calc_type) => {
    switch (calc_type) {
      case 'percentage_of_ctc': return '% of CTC';
      case 'percentage_of_basic': return '% of Basic';
      case 'percentage_of_gross': return '% of Gross';
      case 'fixed_monthly': return '₹/month';
      case 'fixed_annual': return '₹/year';
      case 'balance': return 'Balance';
      default: return calc_type;
    }
  };

  return (
    <div data-testid="ctc-designer-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calculator className="w-6 h-6 text-emerald-600" />
            CTC Structure Designer
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Design and manage employee compensation structures with configurable components
          </p>
        </div>
      </div>

      {/* Stats Cards (Admin only) */}
      {isAdmin && stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <Clock className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Pending Approval</p>
                <p className="text-xl font-bold">{stats.pending}</p>
              </div>
            </div>
          </div>
          <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Active Structures</p>
                <p className="text-xl font-bold">{stats.active}</p>
              </div>
            </div>
          </div>
          <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <FileText className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Total Approved</p>
                <p className="text-xl font-bold">{stats.approved}</p>
              </div>
            </div>
          </div>
          <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Rejected</p>
                <p className="text-xl font-bold">{stats.rejected}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Left: CTC Designer Form */}
        <div className={`p-6 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <IndianRupee className="w-5 h-5 text-emerald-600" />
            Design New CTC Structure
          </h2>

          <div className="space-y-4">
            {/* Employee Selection */}
            <div>
              <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Select Employee *</Label>
              <select
                value={selectedEmployee?.id || ''}
                onChange={(e) => {
                  const emp = employees.find(emp => emp.id === e.target.value);
                  setSelectedEmployee(emp);
                  if (emp?.annual_ctc) {
                    setAnnualCTC(String(Math.round(emp.annual_ctc)));
                  } else if (emp?.salary) {
                    setAnnualCTC(String(Math.round(emp.salary * 12)));
                  }
                }}
                className={`w-full mt-1 h-10 px-3 rounded-md border text-sm ${
                  isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-300 text-zinc-900'
                }`}
                data-testid="ctc-employee-select"
              >
                <option value="">-- Select Employee --</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.department})
                  </option>
                ))}
              </select>
            </div>

            {selectedEmployee && (
              <div className={`p-3 rounded-md ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isDark ? 'bg-emerald-900 text-emerald-400' : 'bg-emerald-100 text-emerald-700'}`}>
                    {selectedEmployee.first_name?.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium">{selectedEmployee.first_name} {selectedEmployee.last_name}</p>
                    <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {selectedEmployee.designation} • {selectedEmployee.department}
                    </p>
                  </div>
                </div>
                {selectedEmployee.salary > 0 && (
                  <p className={`text-xs mt-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Current Monthly Gross: {formatCurrency(selectedEmployee.salary)}
                  </p>
                )}
              </div>
            )}

            {/* Annual CTC */}
            <div>
              <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Annual CTC (₹) *</Label>
              <Input
                type="number"
                value={annualCTC}
                onChange={(e) => setAnnualCTC(e.target.value)}
                placeholder="e.g., 1200000"
                className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : ''}`}
                data-testid="ctc-annual-input"
              />
              {annualCTC && (
                <p className={`text-xs mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  = {formatCurrency(parseFloat(annualCTC) / 12)} / month
                </p>
              )}
            </div>

            {/* Component Configuration Toggle */}
            <div className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-200 bg-zinc-50'}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <ToggleLeft className="w-4 h-4 text-blue-500" />
                  <Label className={`font-medium ${isDark ? 'text-zinc-200' : 'text-zinc-800'}`}>
                    CTC Components
                  </Label>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowComponentSettings(!showComponentSettings)}
                  className="h-7 text-xs"
                >
                  <Settings className="w-3 h-3 mr-1" />
                  {showComponentSettings ? 'Hide' : 'Configure'}
                </Button>
              </div>

              {showComponentSettings && (
                <div className="space-y-2 mt-3 max-h-64 overflow-y-auto">
                  {componentConfig.sort((a, b) => (a.order || 99) - (b.order || 99)).map(comp => {
                    const Icon = componentIcons[comp.key] || IndianRupee;
                    return (
                      <div 
                        key={comp.key}
                        className={`flex items-center justify-between p-2 rounded-md ${
                          comp.enabled 
                            ? isDark ? 'bg-zinc-700/50' : 'bg-white' 
                            : isDark ? 'bg-zinc-800/30 opacity-50' : 'bg-zinc-100 opacity-50'
                        }`}
                      >
                        <div className="flex items-center gap-2 flex-1">
                          <Switch
                            checked={comp.enabled}
                            onCheckedChange={() => toggleComponent(comp.key)}
                            disabled={comp.is_mandatory}
                            data-testid={`toggle-${comp.key}`}
                          />
                          <Icon className={`w-4 h-4 ${comp.is_deduction ? 'text-red-500' : comp.is_deferred ? 'text-amber-500' : 'text-emerald-500'}`} />
                          <span className={`text-sm ${comp.is_mandatory ? 'font-medium' : ''}`}>
                            {comp.name}
                            {comp.is_mandatory && <span className="text-[10px] ml-1 text-amber-500">(Required)</span>}
                          </span>
                        </div>
                        {!comp.is_balance && comp.enabled && (
                          <div className="flex items-center gap-1">
                            <Input
                              type="number"
                              value={comp.value}
                              onChange={(e) => updateComponentValue(comp.key, e.target.value)}
                              className={`w-20 h-7 text-xs text-right ${isDark ? 'bg-zinc-700 border-zinc-600' : ''}`}
                              disabled={comp.is_mandatory && comp.key === 'basic'}
                            />
                            <span className={`text-[10px] w-16 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                              {getCalcTypeLabel(comp.calc_type)}
                            </span>
                          </div>
                        )}
                        {comp.is_balance && (
                          <span className={`text-[10px] ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>Auto-calculated</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {!showComponentSettings && (
                <div className="flex flex-wrap gap-1.5">
                  {componentConfig.filter(c => c.enabled).map(comp => (
                    <span 
                      key={comp.key}
                      className={`text-[10px] px-2 py-0.5 rounded-full ${
                        comp.is_deduction 
                          ? 'bg-red-500/10 text-red-500' 
                          : comp.is_deferred 
                            ? 'bg-amber-500/10 text-amber-500' 
                            : 'bg-emerald-500/10 text-emerald-500'
                      }`}
                    >
                      {comp.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Retention Bonus (Optional) */}
            <div className={`p-4 rounded-md border-2 border-dashed ${isDark ? 'border-zinc-700' : 'border-zinc-300'}`}>
              <Label className={`${isDark ? 'text-zinc-300' : 'text-zinc-700'} flex items-center gap-2`}>
                <Gift className="w-4 h-4 text-purple-500" />
                Retention Bonus (Optional - Part of CTC)
              </Label>
              <div className="grid grid-cols-2 gap-3 mt-2">
                <Input
                  type="number"
                  value={retentionBonus}
                  onChange={(e) => setRetentionBonus(e.target.value)}
                  placeholder="Amount (₹)"
                  className={isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : ''}
                  data-testid="ctc-retention-input"
                />
                <select
                  value={vestingMonths}
                  onChange={(e) => setVestingMonths(parseInt(e.target.value))}
                  className={`w-full h-10 px-3 rounded-md border text-sm ${
                    isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-300'
                  }`}
                >
                  <option value={12}>Vesting: 12 months</option>
                  <option value={18}>Vesting: 18 months</option>
                  <option value={24}>Vesting: 24 months</option>
                </select>
              </div>
              <p className={`text-xs mt-2 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                Paid as lump sum after completion of vesting period
              </p>
            </div>

            {/* Effective Month */}
            <div>
              <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Effective From (Payroll Month) *</Label>
              <Input
                type="month"
                value={effectiveMonth}
                onChange={(e) => setEffectiveMonth(e.target.value)}
                className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : ''}`}
                data-testid="ctc-effective-month"
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                Payroll cycle: 10th to 10th. Salary released on 10th of next month.
              </p>
            </div>

            {/* Remarks */}
            <div>
              <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Remarks (Optional)</Label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Any notes for admin approval..."
                rows={2}
                className={`w-full mt-1 px-3 py-2 rounded-md border text-sm ${
                  isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-300'
                }`}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                onClick={handlePreview}
                variant="outline"
                disabled={loading || !annualCTC}
                className="flex-1"
                data-testid="ctc-preview-btn"
              >
                <Calculator className="w-4 h-4 mr-2" />
                {loading ? 'Calculating...' : 'Preview Breakdown'}
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting || !selectedEmployee || !annualCTC || !effectiveMonth}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="ctc-submit-btn"
              >
                <Send className="w-4 h-4 mr-2" />
                {submitting ? 'Submitting...' : 'Submit for Approval'}
              </Button>
            </div>
          </div>
        </div>

        {/* Right: Preview Panel */}
        <div className={`p-6 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            CTC Breakdown Preview
          </h2>

          {preview ? (
            <div className="space-y-4">
              {/* Summary */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>Annual CTC</p>
                    <p className="text-xl font-bold text-emerald-600">{formatCurrency(preview.summary.annual_ctc)}</p>
                  </div>
                  <div>
                    <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>Monthly Gross</p>
                    <p className="text-xl font-bold text-emerald-600">{formatCurrency(preview.summary.gross_monthly)}</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-emerald-300/30 grid grid-cols-2 gap-2">
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Deductions: <span className="font-semibold text-red-500">{formatCurrency(preview.summary.total_deductions_monthly)}/mo</span>
                  </p>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    In-Hand: <span className="font-semibold text-emerald-600">{formatCurrency(preview.summary.in_hand_approx_monthly)}/mo</span>
                  </p>
                </div>
              </div>

              {/* Components Table */}
              <div className="space-y-2">
                <h3 className={`text-sm font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  Components Breakdown
                </h3>
                <div className={`rounded-lg border overflow-hidden ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
                  <table className="w-full text-sm">
                    <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-50'}>
                      <tr>
                        <th className="text-left px-4 py-2 font-medium">Component</th>
                        <th className="text-right px-4 py-2 font-medium">Monthly</th>
                        <th className="text-right px-4 py-2 font-medium">Annual</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.values(preview.components).filter(c => c.enabled !== false).map((comp) => {
                        const Icon = componentIcons[comp.key] || IndianRupee;
                        return (
                          <tr key={comp.key} className={`border-t ${isDark ? 'border-zinc-800' : 'border-zinc-100'}`}>
                            <td className="px-4 py-2 flex items-center gap-2">
                              <Icon className={`w-4 h-4 ${comp.is_deduction ? 'text-red-500' : comp.is_deferred ? 'text-amber-500' : 'text-zinc-400'}`} />
                              <span className={comp.is_optional ? 'text-purple-500' : comp.is_deduction ? 'text-red-500' : ''}>{comp.name}</span>
                              {comp.is_deduction && <span className="text-[10px] px-1 py-0.5 rounded bg-red-500/10 text-red-500">Deduction</span>}
                              {comp.is_deferred && <span className="text-[10px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-500">Deferred</span>}
                            </td>
                            <td className={`px-4 py-2 text-right font-mono ${comp.is_deduction ? 'text-red-500' : ''}`}>
                              {comp.monthly > 0 ? (comp.is_deduction ? '-' : '') + formatCurrency(comp.monthly) : '-'}
                            </td>
                            <td className={`px-4 py-2 text-right font-mono ${comp.is_deduction ? 'text-red-500' : ''}`}>
                              {(comp.is_deduction ? '-' : '') + formatCurrency(comp.annual)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className={`font-semibold ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                      <tr className={`border-t-2 ${isDark ? 'border-zinc-700' : 'border-zinc-300'}`}>
                        <td className="px-4 py-2">Total CTC</td>
                        <td className="px-4 py-2 text-right font-mono">-</td>
                        <td className="px-4 py-2 text-right font-mono text-emerald-600">
                          {formatCurrency(preview.summary.annual_ctc)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Note */}
              <div className={`p-3 rounded-md ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  <strong>Note:</strong> Deferred components (PF Employer, Gratuity, Retention Bonus) are part of CTC but not in monthly in-hand. 
                  Deductions (PF Employee, ESIC, PT) are subtracted from gross.
                </p>
              </div>
            </div>
          ) : (
            <div className={`flex flex-col items-center justify-center py-12 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
              <Calculator className="w-12 h-12 mb-3 opacity-30" />
              <p>Enter CTC details and click "Preview Breakdown"</p>
              <p className="text-xs mt-1">Configure components using the toggle panel</p>
            </div>
          )}
        </div>
      </div>

      {/* Pending Approvals Section (Admin only) */}
      {isAdmin && pendingApprovals.length > 0 && (
        <div className={`p-6 rounded-lg border ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-500" />
            Pending CTC Approvals ({pendingApprovals.length})
          </h2>
          <div className="space-y-3">
            {pendingApprovals.map(approval => (
              <div
                key={approval.id}
                className={`p-4 rounded-lg border cursor-pointer hover:border-emerald-500 transition-colors ${
                  isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-zinc-50 border-zinc-200'
                }`}
                onClick={() => {
                  setSelectedApproval(approval);
                  setApprovalDialog(true);
                }}
                data-testid={`pending-ctc-${approval.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isDark ? 'bg-amber-900 text-amber-400' : 'bg-amber-100 text-amber-700'}`}>
                      {approval.employee_name?.charAt(0)}
                    </div>
                    <div>
                      <p className="font-medium">{approval.employee_name}</p>
                      <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                        {approval.employee_code} • {approval.department}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-emerald-600">{formatCurrency(approval.annual_ctc)}/year</p>
                    <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      Effective: {approval.effective_month}
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-zinc-400" />
                </div>
                <div className={`mt-2 pt-2 border-t flex items-center justify-between ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Submitted by {approval.created_by_name} • {new Date(approval.created_at).toLocaleDateString()}
                  </p>
                  <div className="flex gap-1">
                    {Object.values(approval.components || {}).filter(c => c.enabled !== false).length} components
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval Dialog */}
      <Dialog open={approvalDialog} onOpenChange={setApprovalDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="ctc-approval-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-600" />
              CTC Structure Approval
            </DialogTitle>
          </DialogHeader>
          
          {selectedApproval && (
            <div className="space-y-4 mt-4">
              {/* Employee Info */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold ${isDark ? 'bg-emerald-900 text-emerald-400' : 'bg-emerald-100 text-emerald-700'}`}>
                    {selectedApproval.employee_name?.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold text-lg">{selectedApproval.employee_name}</p>
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {selectedApproval.employee_code} • {selectedApproval.designation} • {selectedApproval.department}
                    </p>
                  </div>
                </div>
              </div>

              {/* CTC Summary */}
              <div className="grid grid-cols-3 gap-4">
                <div className={`p-4 rounded-lg text-center ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                  <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>Annual CTC</p>
                  <p className="text-xl font-bold text-emerald-600">{formatCurrency(selectedApproval.annual_ctc)}</p>
                </div>
                <div className={`p-4 rounded-lg text-center ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                  <p className={`text-xs ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>Monthly Gross</p>
                  <p className="text-xl font-bold text-blue-600">{formatCurrency(selectedApproval.summary?.gross_monthly || 0)}</p>
                </div>
                <div className={`p-4 rounded-lg text-center ${isDark ? 'bg-purple-900/20 border border-purple-800' : 'bg-purple-50 border border-purple-200'}`}>
                  <p className={`text-xs ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>Effective From</p>
                  <p className="text-xl font-bold text-purple-600">{selectedApproval.effective_month}</p>
                </div>
              </div>

              {selectedApproval.previous_ctc > 0 && (
                <div className={`p-3 rounded-md ${isDark ? 'bg-amber-900/20 border border-amber-800' : 'bg-amber-50 border border-amber-200'}`}>
                  <p className={`text-sm ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>
                    Previous Monthly: {formatCurrency(selectedApproval.previous_ctc)} → New Monthly: {formatCurrency(selectedApproval.summary?.gross_monthly || 0)}
                    <span className="ml-2 font-semibold">
                      ({((selectedApproval.summary?.gross_monthly / selectedApproval.previous_ctc - 1) * 100).toFixed(1)}% change)
                    </span>
                  </p>
                </div>
              )}

              {/* Components Breakdown */}
              <div className={`rounded-lg border overflow-hidden ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                <table className="w-full text-sm">
                  <thead className={isDark ? 'bg-zinc-800' : 'bg-zinc-100'}>
                    <tr>
                      <th className="text-left px-4 py-2">Component</th>
                      <th className="text-right px-4 py-2">Monthly</th>
                      <th className="text-right px-4 py-2">Annual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(selectedApproval.components || {}).filter(c => c.enabled !== false).map(comp => (
                      <tr key={comp.key} className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                        <td className="px-4 py-2">
                          {comp.name}
                          {comp.is_deduction && <span className="ml-1 text-[10px] text-red-500">(Deduction)</span>}
                          {comp.is_deferred && <span className="ml-1 text-[10px] text-amber-500">(Deferred)</span>}
                        </td>
                        <td className={`px-4 py-2 text-right font-mono ${comp.is_deduction ? 'text-red-500' : ''}`}>
                          {comp.monthly > 0 ? formatCurrency(comp.monthly) : '-'}
                        </td>
                        <td className={`px-4 py-2 text-right font-mono ${comp.is_deduction ? 'text-red-500' : ''}`}>
                          {formatCurrency(comp.annual)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {selectedApproval.remarks && (
                <div className={`p-3 rounded-md ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                  <p className={`text-xs font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>HR Remarks:</p>
                  <p className="text-sm mt-1">{selectedApproval.remarks}</p>
                </div>
              )}

              {/* Admin Actions */}
              <div className="space-y-3 pt-4 border-t">
                <div>
                  <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Admin Remarks (Optional)</Label>
                  <Input
                    value={adminRemarks}
                    onChange={(e) => setAdminRemarks(e.target.value)}
                    placeholder="Add any notes..."
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : ''}`}
                  />
                </div>
                <div>
                  <Label className={isDark ? 'text-zinc-300' : 'text-zinc-700'}>Rejection Reason (Required if rejecting)</Label>
                  <Input
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Provide reason if rejecting..."
                    className={`mt-1 ${isDark ? 'bg-zinc-800 border-zinc-700 text-zinc-100' : ''}`}
                  />
                </div>
                <div className="flex gap-3">
                  <Button
                    onClick={handleApprove}
                    disabled={submitting}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    data-testid="ctc-approve-btn"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    {submitting ? 'Processing...' : 'Approve'}
                  </Button>
                  <Button
                    onClick={handleReject}
                    disabled={submitting}
                    variant="destructive"
                    className="flex-1"
                    data-testid="ctc-reject-btn"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CTCDesigner;
