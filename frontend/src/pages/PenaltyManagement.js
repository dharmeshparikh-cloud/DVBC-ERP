import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  AlertTriangle, Search, Plus, Shield, Clock, FileWarning,
  Plane, Receipt, RefreshCw, CheckCircle2, XCircle,
  Eye, RotateCcw, Settings2, Info, Save, ArrowRight
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_ICONS = { attendance: Clock, leave: FileWarning, travel: Plane, expense: Receipt, general: Shield };
const CATEGORY_COLORS = {
  attendance: 'bg-blue-50 text-blue-700 border-blue-200',
  leave: 'bg-amber-50 text-amber-700 border-amber-200',
  travel: 'bg-purple-50 text-purple-700 border-purple-200',
  expense: 'bg-red-50 text-red-700 border-red-200',
  general: 'bg-zinc-50 text-zinc-700 border-zinc-200',
};
const STATUS_STYLES = {
  pending_review: 'bg-yellow-50 text-yellow-800 border-yellow-300',
  approved: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  rejected: 'bg-red-50 text-red-800 border-red-300',
  active: 'bg-emerald-50 text-emerald-800 border-emerald-300',
};
const SOURCE_LABELS = {
  auto_attendance: 'Auto (Check-in)',
  attendance_validation: 'Attendance Validation',
  manual: 'Manual',
};

export default function PenaltyManagement() {
  const [activeTab, setActiveTab] = useState('pending_review');
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [penalties, setPenalties] = useState([]);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState({});
  const [employees, setEmployees] = useState([]);
  const [summary, setSummary] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [selectedPenalties, setSelectedPenalties] = useState(new Set());
  const [viewPenalty, setViewPenalty] = useState(null);
  const [editPenalty, setEditPenalty] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectPenaltyId, setRejectPenaltyId] = useState(null);

  // Apply form
  const [applyForm, setApplyForm] = useState({ employee_id: '', violation_code: '', amount: '', description: '', category: '' });
  const [empSearch, setEmpSearch] = useState('');
  const [showEmpDropdown, setShowEmpDropdown] = useState(false);

  // Rule config
  const [ruleConfig, setRuleConfig] = useState([]);
  const [ruleEdits, setRuleEdits] = useState({});
  const [ruleSaving, setRuleSaving] = useState(false);
  const [rulePolicy, setRulePolicy] = useState({});

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchPenalties = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/penalties/month/${month}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setPenalties(data.penalties || []);
      setSummary(data.count_by_status || {});
    } catch (e) { console.error('Failed to load penalties', e); }
    setLoading(false);
  }, [month, token]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/penalties/categories`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setCategories(data.categories || {});
    } catch (e) { console.error('Failed to load categories', e); }
  }, [token]);

  const fetchEmployees = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/employees`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setEmployees(Array.isArray(data) ? data : data.data || []);
    } catch (e) { console.error('Failed to load employees', e); }
  }, [token]);

  const fetchRuleConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/penalties/rule-config`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setRuleConfig(data.rules || []);
      setRulePolicy({ id: data.policy_id, name: data.policy_name, last_updated: data.last_updated, updated_by: data.updated_by });
      const edits = {};
      (data.rules || []).forEach(r => { edits[r.rule_id] = r.value; });
      setRuleEdits(edits);
    } catch (e) { console.error('Failed to load rule config', e); }
  }, [token]);

  useEffect(() => { fetchPenalties(); }, [fetchPenalties]);
  useEffect(() => { fetchCategories(); fetchEmployees(); fetchRuleConfig(); }, [fetchCategories, fetchEmployees, fetchRuleConfig]);

  // Filter penalties by tab status
  const getFilteredPenalties = (status) => {
    let list = penalties.filter(p => {
      if (status === 'approved') return p.status === 'approved' || p.status === 'active';
      return p.status === status;
    });
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      list = list.filter(p => (p.employee_name || '').toLowerCase().includes(s) || (p.employee_code || '').toLowerCase().includes(s) || (p.violation_name || '').toLowerCase().includes(s));
    }
    if (filterCategory !== 'all') list = list.filter(p => p.category === filterCategory);
    return list;
  };

  const handleApprove = async (id) => {
    try {
      const res = await fetch(`${API}/api/penalties/${id}/approve`, { method: 'POST', headers });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      toast.success('Penalty approved');
      fetchPenalties();
    } catch (e) { toast.error(e.message || 'Failed to approve'); }
  };

  const handleReject = async () => {
    if (!rejectPenaltyId) return;
    try {
      const res = await fetch(`${API}/api/penalties/${rejectPenaltyId}/reject`, { method: 'POST', headers, body: JSON.stringify({ reason: rejectReason }) });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      toast.success('Penalty rejected');
      setRejectPenaltyId(null); setRejectReason('');
      fetchPenalties();
    } catch (e) { toast.error(e.message || 'Failed to reject'); }
  };

  const handleSendBack = async (id) => {
    try {
      const res = await fetch(`${API}/api/penalties/${id}/send-back`, { method: 'POST', headers, body: JSON.stringify({ reason: 'Sent back for review' }) });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      toast.success('Sent back for review');
      fetchPenalties();
    } catch (e) { toast.error(e.message || 'Failed'); }
  };

  const handleBulkAction = async (action) => {
    const ids = Array.from(selectedPenalties);
    if (ids.length === 0) return toast.info('Select penalties first');
    try {
      const res = await fetch(`${API}/api/penalties/bulk-action`, { method: 'POST', headers, body: JSON.stringify({ penalty_ids: ids, action }) });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      const data = await res.json();
      toast.success(data.message);
      setSelectedPenalties(new Set());
      fetchPenalties();
    } catch (e) { toast.error(e.message || 'Bulk action failed'); }
  };

  const handleApplyManual = async () => {
    if (!applyForm.employee_id || !applyForm.violation_code) return toast.error('Select employee and violation type');
    try {
      const res = await fetch(`${API}/api/penalties/apply`, {
        method: 'POST', headers,
        body: JSON.stringify({ ...applyForm, month, amount: parseFloat(applyForm.amount) || undefined, source: 'manual' })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      toast.success('Penalty created — appears in Pending Review');
      setApplyForm({ employee_id: '', violation_code: '', amount: '', description: '', category: '' });
      setEmpSearch('');
      fetchPenalties();
      setActiveTab('pending_review');
    } catch (e) { toast.error(e.message || 'Failed to apply penalty'); }
  };

  const handleUpdatePenalty = async () => {
    if (!editPenalty) return;
    try {
      const res = await fetch(`${API}/api/penalties/${editPenalty.id}`, { method: 'PUT', headers, body: JSON.stringify({ amount: parseFloat(editPenalty.amount), reason: editPenalty.reason }) });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      toast.success('Penalty updated');
      setEditPenalty(null);
      fetchPenalties();
    } catch (e) { toast.error(e.message || 'Failed to update'); }
  };

  const handleSaveRuleConfig = async () => {
    setRuleSaving(true);
    try {
      const res = await fetch(`${API}/api/penalties/rule-config`, {
        method: 'PUT', headers,
        body: JSON.stringify({ rules: ruleEdits })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      const data = await res.json();
      toast.success(data.message);
      fetchRuleConfig();
      fetchCategories();
    } catch (e) { toast.error(e.message || 'Failed to save rules'); }
    setRuleSaving(false);
  };

  const toggleSelect = (id) => {
    const next = new Set(selectedPenalties);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelectedPenalties(next);
  };

  const selectAll = (list) => {
    if (selectedPenalties.size === list.length) setSelectedPenalties(new Set());
    else setSelectedPenalties(new Set(list.map(p => p.id)));
  };

  const fmtINR = (n) => `₹${(n || 0).toLocaleString('en-IN')}`;

  const filteredEmps = empSearch ? employees.filter(e => `${e.first_name} ${e.last_name} ${e.employee_id}`.toLowerCase().includes(empSearch.toLowerCase())).slice(0, 8) : [];
  const violations = applyForm.category && categories[applyForm.category] ? categories[applyForm.category].violations : [];

  // Live preview calculation for rule config
  const previewCalc = () => {
    const grace = ruleEdits['AT011'] || 3;
    const amt = ruleEdits['AT012'] || 100;
    return { grace, amt, example5: Math.max(0, 5 - grace) * amt, example8: Math.max(0, 8 - grace) * amt };
  };
  const preview = previewCalc();

  // --- RENDER ---
  const PenaltyRow = ({ p, showActions, showCheckbox }) => {
    const CatIcon = CATEGORY_ICONS[p.category] || Shield;
    return (
      <tr className="border-b border-zinc-100 hover:bg-zinc-50/50 transition-colors" data-testid={`penalty-row-${p.id}`}>
        {showCheckbox && (
          <td className="px-3 py-2.5">
            <input type="checkbox" checked={selectedPenalties.has(p.id)} onChange={() => toggleSelect(p.id)} className="rounded border-zinc-300" data-testid={`penalty-checkbox-${p.id}`} />
          </td>
        )}
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-zinc-100 flex items-center justify-center"><CatIcon className="w-3.5 h-3.5 text-zinc-500" /></div>
            <div>
              <p className="text-sm font-medium text-zinc-900">{p.employee_name || '-'}</p>
              <p className="text-xs text-zinc-400 font-mono">{p.employee_code || '-'}</p>
            </div>
          </div>
        </td>
        <td className="px-3 py-2.5">
          <Badge variant="outline" className={`text-xs ${CATEGORY_COLORS[p.category] || CATEGORY_COLORS.general}`}>{p.category_name || p.category || '-'}</Badge>
        </td>
        <td className="px-3 py-2.5">
          <span className="text-sm text-zinc-700">{p.violation_name || p.name || '-'}</span>
          {p.source && p.source !== 'manual' && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-200">{SOURCE_LABELS[p.source] || p.source}</span>}
        </td>
        <td className="px-3 py-2.5 font-mono font-semibold text-sm text-zinc-900">{fmtINR(p.amount)}</td>
        <td className="px-3 py-2.5 max-w-[200px]">
          <p className="text-xs text-zinc-500 truncate" title={p.reason}>{p.reason || '-'}</p>
        </td>
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setViewPenalty(p)} data-testid={`view-penalty-${p.id}`}><Eye className="w-3.5 h-3.5" /></Button>
            {showActions && p.status === 'pending_review' && (
              <>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" onClick={() => handleApprove(p.id)} data-testid={`approve-penalty-${p.id}`}><CheckCircle2 className="w-3.5 h-3.5" /></Button>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => { setRejectPenaltyId(p.id); setRejectReason(''); }} data-testid={`reject-penalty-${p.id}`}><XCircle className="w-3.5 h-3.5" /></Button>
                <Button variant="ghost" size="sm" className="h-7 text-xs px-2 text-zinc-500" onClick={() => setEditPenalty({ ...p })} data-testid={`edit-penalty-${p.id}`}>Edit</Button>
              </>
            )}
            {(p.status === 'approved' || p.status === 'active') && (
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-amber-500 hover:bg-amber-50" onClick={() => handleSendBack(p.id)} data-testid={`sendback-penalty-${p.id}`}><RotateCcw className="w-3.5 h-3.5" /></Button>
            )}
          </div>
        </td>
      </tr>
    );
  };

  const PenaltyTable = ({ list, showActions = true, showCheckbox = false, emptyMsg }) => (
    list.length === 0 ? (
      <div className="text-center py-12 text-zinc-400" data-testid="empty-state"><AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-30" /><p>{emptyMsg || 'No penalties found'}</p></div>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full" data-testid="penalties-table">
          <thead>
            <tr className="border-b-2 border-zinc-200 text-xs text-zinc-500 uppercase tracking-wider">
              {showCheckbox && <th className="px-3 py-2 text-left w-10"><input type="checkbox" onChange={() => selectAll(list)} checked={selectedPenalties.size === list.length && list.length > 0} className="rounded border-zinc-300" /></th>}
              <th className="px-3 py-2 text-left">Employee</th>
              <th className="px-3 py-2 text-left">Category</th>
              <th className="px-3 py-2 text-left">Violation</th>
              <th className="px-3 py-2 text-left">Amount</th>
              <th className="px-3 py-2 text-left">Reason</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>{list.map(p => <PenaltyRow key={p.id} p={p} showActions={showActions} showCheckbox={showCheckbox} />)}</tbody>
        </table>
      </div>
    )
  );

  return (
    <div className="space-y-4" data-testid="penalty-compliance-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-900" data-testid="page-title">Penalty & Compliance</h1>
          <p className="text-sm text-zinc-500">Configure rules, review penalties, approve deductions</p>
        </div>
        <div className="flex items-center gap-3">
          <Input type="month" value={month} onChange={e => setMonth(e.target.value)} className="w-40 h-9 text-sm" data-testid="month-selector" />
          <Button variant="outline" size="sm" onClick={fetchPenalties} disabled={loading} data-testid="refresh-btn"><RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />Refresh</Button>
        </div>
      </div>

      {/* Scorecard */}
      <div className="grid grid-cols-4 gap-3" data-testid="summary-cards">
        <Card className="border-yellow-200 bg-yellow-50/50 cursor-pointer hover:shadow-sm transition-shadow" onClick={() => setActiveTab('pending_review')}>
          <CardContent className="p-3">
            <p className="text-xs text-yellow-600 font-medium uppercase tracking-wider">Pending Review</p>
            <p className="text-2xl font-bold text-yellow-800 mt-1" data-testid="pending-count">{summary.pending_review || 0}</p>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50/50 cursor-pointer hover:shadow-sm transition-shadow" onClick={() => setActiveTab('approved')}>
          <CardContent className="p-3">
            <p className="text-xs text-emerald-600 font-medium uppercase tracking-wider">Approved</p>
            <p className="text-2xl font-bold text-emerald-800 mt-1" data-testid="approved-count">{summary.approved || 0}</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50/50 cursor-pointer hover:shadow-sm transition-shadow" onClick={() => setActiveTab('rejected')}>
          <CardContent className="p-3">
            <p className="text-xs text-red-600 font-medium uppercase tracking-wider">Rejected</p>
            <p className="text-2xl font-bold text-red-800 mt-1" data-testid="rejected-count">{summary.rejected || 0}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-200">
          <CardContent className="p-3">
            <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Total Approved Amount</p>
            <p className="text-2xl font-bold text-zinc-900 mt-1" data-testid="total-amount">{fmtINR(penalties.filter(p => p.status === 'approved' || p.status === 'active').reduce((s, p) => s + (p.amount || 0), 0))}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters — shown on penalty tabs only */}
      {activeTab !== 'apply' && activeTab !== 'rules' && (
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-zinc-400" />
            <Input placeholder="Search employee or violation..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="pl-9 h-9 text-sm" data-testid="search-input" />
          </div>
          <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)} className="h-9 px-3 rounded-md border border-zinc-200 text-sm bg-white" data-testid="category-filter">
            <option value="all">All Categories</option>
            {Object.entries(categories).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}
          </select>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={v => { setActiveTab(v); setSelectedPenalties(new Set()); }}>
        <TabsList className="bg-zinc-100" data-testid="penalty-tabs">
          <TabsTrigger value="pending_review" data-testid="tab-pending">Pending Review ({getFilteredPenalties('pending_review').length})</TabsTrigger>
          <TabsTrigger value="approved" data-testid="tab-approved">Approved ({getFilteredPenalties('approved').length})</TabsTrigger>
          <TabsTrigger value="rejected" data-testid="tab-rejected">Rejected ({getFilteredPenalties('rejected').length})</TabsTrigger>
          <TabsTrigger value="apply" data-testid="tab-apply"><Plus className="w-3.5 h-3.5 mr-1" />Apply Manual</TabsTrigger>
          <TabsTrigger value="rules" data-testid="tab-rules"><Settings2 className="w-3.5 h-3.5 mr-1" />Rule Configuration</TabsTrigger>
        </TabsList>

        {/* Pending Review */}
        <TabsContent value="pending_review">
          {getFilteredPenalties('pending_review').length > 0 && (
            <div className="flex items-center gap-2 mb-3" data-testid="bulk-actions">
              <Button size="sm" variant="outline" className="text-emerald-600 border-emerald-200 hover:bg-emerald-50" onClick={() => handleBulkAction('approve')} data-testid="bulk-approve-btn">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />Approve Selected ({selectedPenalties.size})
              </Button>
              <Button size="sm" variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleBulkAction('reject')} data-testid="bulk-reject-btn">
                <XCircle className="w-3.5 h-3.5 mr-1" />Reject Selected
              </Button>
            </div>
          )}
          <Card>
            <CardContent className="p-0">
              <PenaltyTable list={getFilteredPenalties('pending_review')} showCheckbox showActions emptyMsg="No pending penalties for this month" />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Approved */}
        <TabsContent value="approved">
          <Card>
            <CardContent className="p-0">
              <PenaltyTable list={getFilteredPenalties('approved')} showActions emptyMsg="No approved penalties" />
            </CardContent>
          </Card>
          {getFilteredPenalties('approved').length > 0 && (
            <div className="mt-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-md flex items-start gap-2">
              <Info className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-emerald-700">Approved penalties will be deducted from payroll for <strong>{month}</strong>. Use send-back button to reverse an approval before payroll is locked.</p>
            </div>
          )}
        </TabsContent>

        {/* Rejected */}
        <TabsContent value="rejected">
          <Card>
            <CardContent className="p-0">
              <PenaltyTable list={getFilteredPenalties('rejected')} showActions={false} emptyMsg="No rejected penalties" />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Apply Manual */}
        <TabsContent value="apply">
          <Card>
            <CardHeader><CardTitle className="text-base">Apply Manual Penalty</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {/* Employee Select */}
              <div className="space-y-1.5 relative">
                <Label className="text-sm font-medium">Employee</Label>
                <Input placeholder="Search employee..." value={empSearch} onChange={e => { setEmpSearch(e.target.value); setShowEmpDropdown(true); }} onFocus={() => setShowEmpDropdown(true)} onBlur={() => setTimeout(() => setShowEmpDropdown(false), 200)} className="h-9" data-testid="employee-search" />
                {showEmpDropdown && filteredEmps.length > 0 && (
                  <div className="absolute z-50 top-full left-0 w-full bg-white border border-zinc-200 rounded-md shadow-lg max-h-48 overflow-y-auto mt-1">
                    {filteredEmps.map(e => (
                      <button key={e.id} className="w-full text-left px-3 py-2 hover:bg-zinc-50 text-sm flex justify-between" onMouseDown={() => { setApplyForm({ ...applyForm, employee_id: e.id }); setEmpSearch(`${e.first_name} ${e.last_name} (${e.employee_id})`); setShowEmpDropdown(false); }} data-testid={`emp-option-${e.id}`}>
                        <span>{e.first_name} {e.last_name}</span><span className="text-zinc-400 font-mono">{e.employee_id}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Category + Violation */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium">Category</Label>
                  <select value={applyForm.category} onChange={e => setApplyForm({ ...applyForm, category: e.target.value, violation_code: '', amount: '' })} className="w-full h-9 px-3 rounded-md border border-zinc-200 text-sm bg-white" data-testid="category-select">
                    <option value="">Select category</option>
                    {Object.entries(categories).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium">Violation Type</Label>
                  <select value={applyForm.violation_code} onChange={e => { const v = violations.find(x => x.code === e.target.value); setApplyForm({ ...applyForm, violation_code: e.target.value, amount: v?.default_amount || '' }); }} className="w-full h-9 px-3 rounded-md border border-zinc-200 text-sm bg-white" data-testid="violation-select">
                    <option value="">Select violation</option>
                    {violations.map(v => (
                      <option key={v.code} value={v.code}>{v.name} ({fmtINR(v.default_amount)}{v.amount_source === 'business_rules' ? ' - from rules' : ''})</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Amount + Description */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium">Amount</Label>
                  <Input type="number" value={applyForm.amount} onChange={e => setApplyForm({ ...applyForm, amount: e.target.value })} placeholder="Auto-fills from default" className="h-9" data-testid="amount-input" />
                  {applyForm.amount && violations.find(v => v.code === applyForm.violation_code)?.default_amount && parseFloat(applyForm.amount) !== violations.find(v => v.code === applyForm.violation_code)?.default_amount && (
                    <p className="text-xs text-amber-600 flex items-center gap-1"><Info className="w-3 h-3" />Default is {fmtINR(violations.find(v => v.code === applyForm.violation_code)?.default_amount)} per rule. You're overriding.</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium">Description / Reason</Label>
                  <Input value={applyForm.description} onChange={e => setApplyForm({ ...applyForm, description: e.target.value })} placeholder="Reason for penalty" className="h-9" data-testid="description-input" />
                </div>
              </div>

              <Button onClick={handleApplyManual} className="bg-zinc-900 hover:bg-zinc-800 text-white" data-testid="submit-penalty-btn">
                <Plus className="w-4 h-4 mr-1" />Apply Penalty
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rule Configuration */}
        <TabsContent value="rules">
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">Attendance Penalty Rules</CardTitle>
                    <p className="text-xs text-zinc-400 mt-1">
                      {rulePolicy.last_updated ? `Last updated: ${new Date(rulePolicy.last_updated).toLocaleDateString('en-IN')} by ${rulePolicy.updated_by || 'HR'}` : 'Default configuration'}
                    </p>
                  </div>
                  <Button onClick={handleSaveRuleConfig} disabled={ruleSaving} className="bg-zinc-900 text-white" data-testid="save-rules-btn">
                    <Save className="w-4 h-4 mr-1" />{ruleSaving ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {ruleConfig.map(rule => (
                    <div key={rule.rule_id} className="flex items-start gap-4 p-4 bg-zinc-50 rounded-lg border border-zinc-100" data-testid={`rule-${rule.rule_id}`}>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-zinc-400 bg-zinc-200/60 px-1.5 py-0.5 rounded">{rule.rule_id}</span>
                          <h3 className="text-sm font-semibold text-zinc-900">{rule.name}</h3>
                        </div>
                        <p className="text-xs text-zinc-500 mb-2">{rule.description}</p>
                        <p className="text-xs text-blue-600 flex items-center gap-1"><Info className="w-3 h-3" />{rule.impact}</p>
                      </div>
                      <div className="w-32">
                        <div className="flex items-center gap-1.5">
                          {rule.type === 'currency' && <span className="text-sm text-zinc-400">₹</span>}
                          <Input
                            type="number"
                            value={ruleEdits[rule.rule_id] ?? rule.value}
                            onChange={e => setRuleEdits({ ...ruleEdits, [rule.rule_id]: parseFloat(e.target.value) || 0 })}
                            className="h-9 text-right font-mono font-semibold"
                            data-testid={`rule-input-${rule.rule_id}`}
                          />
                          <span className="text-xs text-zinc-400 whitespace-nowrap">{rule.unit === '₹/day' ? '/day' : rule.unit}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Live Preview */}
            <Card className="border-blue-200 bg-blue-50/30">
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-1.5"><Info className="w-4 h-4" />Live Impact Preview</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-white rounded-lg p-3 border border-blue-100">
                    <p className="text-xs text-zinc-500 mb-1">Employee with 5 late days</p>
                    <p className="text-zinc-700">Grace: {preview.grace} days, Excess: {Math.max(0, 5 - preview.grace)} days</p>
                    <p className="text-lg font-bold text-zinc-900">{fmtINR(preview.example5)}</p>
                  </div>
                  <div className="bg-white rounded-lg p-3 border border-blue-100">
                    <p className="text-xs text-zinc-500 mb-1">Employee with 8 late days</p>
                    <p className="text-zinc-700">Grace: {preview.grace} days, Excess: {Math.max(0, 8 - preview.grace)} days</p>
                    <p className="text-lg font-bold text-zinc-900">{fmtINR(preview.example8)}</p>
                  </div>
                </div>
                <div className="mt-3 flex items-start gap-2 text-xs text-blue-700">
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <span>Changes apply to <strong>future penalties only</strong>. Existing approved penalties are not retroactively affected.</span>
                </div>
              </CardContent>
            </Card>

            {/* Cross-link */}
            <a href="/business-rules" className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-700 transition-colors" data-testid="business-rules-link">
              <ArrowRight className="w-4 h-4" />Full attendance policy & other business rules
            </a>
          </div>
        </TabsContent>
      </Tabs>

      {/* View Detail Dialog */}
      <Dialog open={!!viewPenalty} onOpenChange={() => setViewPenalty(null)}>
        <DialogContent className="max-w-lg" aria-describedby="view-penalty-desc">
          <DialogHeader><DialogTitle>Penalty Details</DialogTitle></DialogHeader>
          <p id="view-penalty-desc" className="sr-only">View details of the selected penalty record</p>
          {viewPenalty && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="text-xs text-zinc-400">Employee</Label><p className="font-medium">{viewPenalty.employee_name}</p><p className="text-xs text-zinc-400 font-mono">{viewPenalty.employee_code} | {viewPenalty.department || '-'}</p></div>
                <div><Label className="text-xs text-zinc-400">Status</Label><Badge variant="outline" className={STATUS_STYLES[viewPenalty.status]}>{viewPenalty.status?.replace('_', ' ')}</Badge></div>
                <div><Label className="text-xs text-zinc-400">Category</Label><Badge variant="outline" className={CATEGORY_COLORS[viewPenalty.category] || ''}>{viewPenalty.category_name || viewPenalty.category}</Badge></div>
                <div><Label className="text-xs text-zinc-400">Violation</Label><p>{viewPenalty.violation_name || viewPenalty.name}</p></div>
                <div><Label className="text-xs text-zinc-400">Amount</Label><p className="text-lg font-bold">{fmtINR(viewPenalty.amount)}</p></div>
                <div><Label className="text-xs text-zinc-400">Source</Label><Badge variant="outline" className="text-xs bg-zinc-50">{SOURCE_LABELS[viewPenalty.source] || viewPenalty.source || 'Manual'}</Badge></div>
                <div><Label className="text-xs text-zinc-400">Month</Label><p>{viewPenalty.month}</p></div>
                {viewPenalty.rule_reference && <div><Label className="text-xs text-zinc-400">Rule Reference</Label><p className="font-mono text-xs bg-zinc-100 px-1.5 py-0.5 rounded inline-block">{viewPenalty.rule_reference}</p></div>}
              </div>
              {/* Reason box */}
              {viewPenalty.reason && (
                <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-100">
                  <Label className="text-xs text-zinc-400 mb-1 block">Reason</Label>
                  <p className="text-zinc-700 text-sm">{viewPenalty.reason}</p>
                </div>
              )}
              {/* Grace context for attendance */}
              {viewPenalty.category === 'attendance' && viewPenalty.late_minutes && (
                <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                  <Label className="text-xs text-blue-500 mb-1 block">Attendance Context</Label>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div><span className="text-blue-400">Late by</span><p className="font-semibold text-blue-800">{viewPenalty.late_minutes} min</p></div>
                    <div><span className="text-blue-400">Late # this month</span><p className="font-semibold text-blue-800">{viewPenalty.late_count_this_month || '-'}</p></div>
                    <div><span className="text-blue-400">Grace limit</span><p className="font-semibold text-blue-800">{viewPenalty.grace_days_allowed || '-'} days</p></div>
                  </div>
                </div>
              )}
              {/* Rejection reason */}
              {viewPenalty.rejection_reason && (
                <div className="bg-red-50 p-3 rounded-lg border border-red-100">
                  <Label className="text-xs text-red-400 block">Rejection Reason</Label>
                  <p className="text-red-700">{viewPenalty.rejection_reason}</p>
                </div>
              )}
              {/* Payroll impact */}
              <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-100 flex items-start gap-2">
                <Info className="w-4 h-4 text-zinc-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-zinc-600">
                  {viewPenalty.status === 'approved' || viewPenalty.status === 'active'
                    ? <span>Will be deducted from <strong>{viewPenalty.is_arrears ? viewPenalty.effective_month : viewPenalty.month}</strong> payroll.{viewPenalty.is_arrears && <span className="text-amber-600"> (Arrears from {viewPenalty.original_month})</span>}</span>
                    : viewPenalty.status === 'pending_review'
                    ? <span>Pending approval. Will be deducted from <strong>{viewPenalty.month}</strong> payroll once approved.</span>
                    : <span>Rejected — will NOT be deducted from payroll.</span>
                  }
                </div>
              </div>
              {/* Timeline */}
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-100 text-xs text-zinc-400">
                <div><Label className="text-xs text-zinc-400">Created</Label><p>{new Date(viewPenalty.created_at).toLocaleString('en-IN')}</p><p>By: {viewPenalty.created_by_name || 'System'}</p></div>
                {viewPenalty.approved_at && <div><Label className="text-xs text-zinc-400">Approved</Label><p>{new Date(viewPenalty.approved_at).toLocaleString('en-IN')}</p><p>By: {viewPenalty.approved_by_name}</p></div>}
                {viewPenalty.rejected_at && <div><Label className="text-xs text-zinc-400">Rejected</Label><p>{new Date(viewPenalty.rejected_at).toLocaleString('en-IN')}</p><p>By: {viewPenalty.rejected_by_name}</p></div>}
              </div>
            </div>
          )}
          <DialogFooter>
            {viewPenalty?.status === 'pending_review' && (
              <div className="flex gap-2 mr-auto">
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => { handleApprove(viewPenalty.id); setViewPenalty(null); }} data-testid="dialog-approve-btn"><CheckCircle2 className="w-3.5 h-3.5 mr-1" />Approve</Button>
                <Button size="sm" variant="destructive" onClick={() => { setRejectPenaltyId(viewPenalty.id); setViewPenalty(null); }} data-testid="dialog-reject-btn"><XCircle className="w-3.5 h-3.5 mr-1" />Reject</Button>
              </div>
            )}
            <Button variant="outline" onClick={() => setViewPenalty(null)} data-testid="close-view-btn">Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editPenalty} onOpenChange={() => setEditPenalty(null)}>
        <DialogContent className="max-w-md" aria-describedby="edit-penalty-desc">
          <DialogHeader><DialogTitle>Edit Penalty</DialogTitle></DialogHeader>
          <p id="edit-penalty-desc" className="sr-only">Edit the amount and reason for this penalty</p>
          {editPenalty && (
            <div className="space-y-3">
              <p className="text-sm text-zinc-600"><span className="font-medium">{editPenalty.employee_name}</span> — {editPenalty.violation_name}</p>
              <div className="space-y-1.5">
                <Label className="text-sm">Amount</Label>
                <Input type="number" value={editPenalty.amount} onChange={e => setEditPenalty({ ...editPenalty, amount: e.target.value })} data-testid="edit-amount" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm">Reason</Label>
                <Input value={editPenalty.reason || ''} onChange={e => setEditPenalty({ ...editPenalty, reason: e.target.value })} data-testid="edit-reason" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditPenalty(null)}>Cancel</Button>
            <Button onClick={handleUpdatePenalty} className="bg-zinc-900 text-white" data-testid="save-edit-btn">Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Reason Dialog */}
      <Dialog open={!!rejectPenaltyId} onOpenChange={() => setRejectPenaltyId(null)}>
        <DialogContent className="max-w-md" aria-describedby="reject-penalty-desc">
          <DialogHeader><DialogTitle>Reject Penalty</DialogTitle></DialogHeader>
          <p id="reject-penalty-desc" className="sr-only">Provide a reason for rejecting this penalty</p>
          <div className="space-y-3">
            <Label className="text-sm">Reason for rejection (optional)</Label>
            <Input value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Enter reason..." data-testid="reject-reason-input" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectPenaltyId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleReject} data-testid="confirm-reject-btn">Reject</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
