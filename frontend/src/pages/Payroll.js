import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { DollarSign, FileText, RefreshCw, Users as UsersIcon, Plus, Trash2, Save, Table2, Settings, Receipt } from 'lucide-react';
import { toast } from 'sonner';

const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;

const Payroll = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [slips, setSlips] = useState([]);
  const [components, setComponents] = useState(null);
  const [payrollInputs, setPayrollInputs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [addCompDialog, setAddCompDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [viewSlip, setViewSlip] = useState(null);
  const [activeTab, setActiveTab] = useState('slips');
  const [savingInputs, setSavingInputs] = useState(false);
  const [newComp, setNewComp] = useState({ type: 'earnings', name: '', calcType: 'fixed', value: '' });

  const isHR = ['admin', 'hr_manager'].includes(user?.role);

  useEffect(() => { fetchData(); }, [month]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [empRes, slipsRes, compRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/payroll/salary-slips?month=${month}`),
        axios.get(`${API}/payroll/salary-components`)
      ]);
      setEmployees(empRes.data.filter(e => e.salary > 0));
      setSlips(slipsRes.data);
      setComponents(compRes.data);
      if (isHR) {
        const inputRes = await axios.get(`${API}/payroll/inputs?month=${month}`);
        setPayrollInputs(inputRes.data);
      }
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      if (selectedEmployee === 'all') {
        const res = await axios.post(`${API}/payroll/generate-bulk`, { month });
        toast.success(`Generated ${res.data.count} salary slips`);
      } else {
        await axios.post(`${API}/payroll/generate-slip`, { employee_id: selectedEmployee, month });
        toast.success('Salary slip generated');
      }
      setGenerateDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate');
    }
  };

  // --- Salary Component Management ---
  const addComponent = async () => {
    if (!newComp.name || !newComp.value) return toast.error('Name and value required');
    try {
      const payload = { type: newComp.type, name: newComp.name, key: newComp.name.toLowerCase().replace(/\s+/g, '_') };
      if (newComp.calcType === 'percentage') payload.percentage = parseFloat(newComp.value);
      else payload.fixed = parseFloat(newComp.value);
      await axios.post(`${API}/payroll/salary-components/add`, payload);
      toast.success(`${newComp.name} added`);
      setAddCompDialog(false);
      setNewComp({ type: 'earnings', name: '', calcType: 'fixed', value: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add');
    }
  };

  const removeComponent = async (type, key, name) => {
    if (!window.confirm(`Remove "${name}" from ${type}?`)) return;
    try {
      await axios.delete(`${API}/payroll/salary-components/${type}/${key}`);
      toast.success(`${name} removed`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove');
    }
  };

  // --- Payroll Input Table ---
  const updateInput = (empId, field, value) => {
    setPayrollInputs(prev => prev.map(p =>
      p.employee_id === empId ? { ...p, [field]: value } : p
    ));
  };

  const saveAllInputs = async () => {
    setSavingInputs(true);
    try {
      await axios.post(`${API}/payroll/inputs/bulk`, { month, inputs: payrollInputs });
      toast.success('Payroll inputs saved');
    } catch (err) {
      toast.error('Failed to save inputs');
    } finally {
      setSavingInputs(false);
    }
  };

  const saveSingleInput = async (input) => {
    try {
      await axios.post(`${API}/payroll/inputs`, { ...input, month });
      toast.success('Saved');
    } catch (err) {
      toast.error('Failed to save');
    }
  };

  const totalPayout = slips.reduce((s, sl) => s + (sl.net_salary || 0), 0);

  const tabs = [
    { id: 'slips', label: 'Salary Slips', icon: FileText },
    { id: 'inputs', label: 'Payroll Inputs', icon: Table2 },
    { id: 'components', label: 'Components', icon: Settings },
  ];

  return (
    <div data-testid="payroll-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-1">Payroll</h1>
          <p className="text-zinc-500 text-sm">Manage salary components, payroll inputs, and generate slips</p>
        </div>
        {isHR && (
          <div className="flex gap-2">
            <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="generate-slip-btn">
                  <RefreshCw className="w-4 h-4 mr-2" /> Generate Slips
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-md">
                <DialogHeader>
                  <DialogTitle>Generate Salary Slips</DialogTitle>
                  <DialogDescription>Select employee or generate for all</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div><Label>Month</Label><Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200" /></div>
                  <div>
                    <Label>Employee</Label>
                    <select value={selectedEmployee} onChange={(e) => setSelectedEmployee(e.target.value)} className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm" data-testid="payroll-emp-select">
                      <option value="">Select...</option>
                      <option value="all">All Employees (Bulk)</option>
                      {employees.map(e => (<option key={e.id} value={e.id}>{e.employee_id} - {e.first_name} {e.last_name} ({fmt(e.salary)})</option>))}
                    </select>
                  </div>
                  <Button onClick={handleGenerate} disabled={!selectedEmployee} className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm" data-testid="confirm-generate">Generate</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        {[
          { icon: FileText, label: 'Slips Generated', value: slips.length, tid: 'payroll-slip-count' },
          { icon: DollarSign, label: 'Total Payout', value: fmt(totalPayout) },
          { icon: UsersIcon, label: 'Active Employees', value: employees.length },
        ].map((s, i) => (
          <Card key={i} className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <s.icon className="w-5 h-5 text-zinc-300" />
              <div>
                <div className="text-[10px] uppercase tracking-widest text-zinc-500">{s.label}</div>
                <div className="text-xl font-semibold text-zinc-950" data-testid={s.tid}>{s.value}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs + Month */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex gap-0.5 bg-zinc-100 rounded-sm p-0.5">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} data-testid={`tab-${t.id}`}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
                activeTab === t.id ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'
              }`}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>
        <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200 w-40 h-8 text-xs" data-testid="payroll-month" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : activeTab === 'components' ? (
        /* ========== COMPONENTS TAB ========== */
        <div className="space-y-4">
          {isHR && (
            <div className="flex justify-end">
              <Dialog open={addCompDialog} onOpenChange={setAddCompDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-xs gap-1" data-testid="add-component-btn"><Plus className="w-3.5 h-3.5" /> Add Component</Button>
                </DialogTrigger>
                <DialogContent className="max-w-sm">
                  <DialogHeader><DialogTitle>Add Salary Component</DialogTitle></DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs">Type</Label>
                      <select value={newComp.type} onChange={e => setNewComp({ ...newComp, type: e.target.value })} className="w-full h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm" data-testid="comp-type-select">
                        <option value="earnings">Earning</option>
                        <option value="deductions">Deduction</option>
                      </select>
                    </div>
                    <div><Label className="text-xs">Name</Label><Input value={newComp.name} onChange={e => setNewComp({ ...newComp, name: e.target.value })} placeholder="e.g. Bonus" className="h-9" data-testid="comp-name-input" /></div>
                    <div>
                      <Label className="text-xs">Calculation</Label>
                      <select value={newComp.calcType} onChange={e => setNewComp({ ...newComp, calcType: e.target.value })} className="w-full h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm">
                        <option value="fixed">Fixed Amount (₹)</option>
                        <option value="percentage">% of CTC</option>
                      </select>
                    </div>
                    <div><Label className="text-xs">{newComp.calcType === 'percentage' ? 'Percentage' : 'Amount (₹)'}</Label><Input type="number" value={newComp.value} onChange={e => setNewComp({ ...newComp, value: e.target.value })} className="h-9" data-testid="comp-value-input" /></div>
                    <Button onClick={addComponent} className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm h-9" data-testid="save-component-btn">Add Component</Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
          <div className="grid grid-cols-2 gap-5">
            {['earnings', 'deductions'].map(type => (
              <Card key={type} className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="p-4">
                  <h3 className={`text-xs font-bold uppercase tracking-widest mb-3 ${type === 'earnings' ? 'text-emerald-700' : 'text-red-700'}`}>{type}</h3>
                  <div className="space-y-1.5">
                    {(components?.[type] || []).map((c, i) => (
                      <div key={i} className={`flex items-center justify-between px-3 py-2 rounded-sm text-sm ${type === 'earnings' ? 'bg-emerald-50 border border-emerald-100' : 'bg-red-50 border border-red-100'}`}>
                        <span className="text-zinc-700">{c.name}</span>
                        <div className="flex items-center gap-2">
                          <span className={`font-medium text-xs ${type === 'earnings' ? 'text-emerald-700' : 'text-red-700'}`}>
                            {c.percentage ? `${c.percentage}% of CTC` : fmt(c.fixed)}
                          </span>
                          {isHR && !c.is_default && (
                            <button onClick={() => removeComponent(type, c.key, c.name)} className="text-zinc-400 hover:text-red-500 transition-colors" data-testid={`remove-${c.key}`}>
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : activeTab === 'inputs' ? (
        /* ========== PAYROLL INPUTS TAB ========== */
        <div className="space-y-3">
          {isHR && (
            <div className="flex justify-end">
              <Button onClick={saveAllInputs} disabled={savingInputs} size="sm" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm text-xs gap-1" data-testid="save-all-inputs">
                <Save className="w-3.5 h-3.5" /> {savingInputs ? 'Saving...' : 'Save All'}
              </Button>
            </div>
          )}
          <div className="border border-zinc-200 rounded-sm overflow-x-auto">
            <table className="w-full text-[11px]" data-testid="payroll-inputs-table">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="text-left px-2 py-2 font-medium text-zinc-600 sticky left-0 bg-zinc-50 min-w-[140px]">Employee</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">Working Days</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">Present</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">Absent</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">Holidays</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">Leaves</th>
                  <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[55px]">OT Hrs</th>
                  <th className="text-right px-2 py-2 font-medium text-emerald-700 min-w-[80px]">Incentive</th>
                  <th className="text-left px-2 py-2 font-medium text-emerald-700 min-w-[100px]">Reason</th>
                  <th className="text-right px-2 py-2 font-medium text-amber-700 min-w-[80px]">Advance</th>
                  <th className="text-left px-2 py-2 font-medium text-amber-700 min-w-[100px]">Reason</th>
                  <th className="text-right px-2 py-2 font-medium text-red-700 min-w-[80px]">Penalty</th>
                  <th className="text-left px-2 py-2 font-medium text-red-700 min-w-[100px]">Reason</th>
                  <th className="text-left px-2 py-2 font-medium text-zinc-600 min-w-[100px]">Remarks</th>
                  {isHR && <th className="text-center px-2 py-2 font-medium text-zinc-600 min-w-[40px]"></th>}
                </tr>
              </thead>
              <tbody>
                {payrollInputs.map(inp => (
                  <tr key={inp.employee_id} className="border-t border-zinc-100 hover:bg-zinc-50/50" data-testid={`input-row-${inp.employee_id}`}>
                    <td className="px-2 py-1.5 sticky left-0 bg-white">
                      <div className="font-medium text-zinc-900 text-xs">{inp.name}</div>
                      <div className="text-[10px] text-zinc-400">{inp.emp_code} | {inp.department || '-'}</div>
                    </td>
                    {['working_days', 'present_days', 'absent_days', 'public_holidays', 'leaves', 'overtime_hours'].map(f => (
                      <td key={f} className="px-1 py-1">
                        <input type="number" value={inp[f] || 0} onChange={e => updateInput(inp.employee_id, f, parseInt(e.target.value) || 0)}
                          className="w-full h-7 px-1.5 text-center text-[11px] rounded border border-zinc-200 bg-white focus:ring-1 focus:ring-zinc-400 focus:border-zinc-400"
                          disabled={!isHR} data-testid={`${f}-${inp.employee_id}`} />
                      </td>
                    ))}
                    <td className="px-1 py-1">
                      <input type="number" value={inp.incentive || 0} onChange={e => updateInput(inp.employee_id, 'incentive', parseFloat(e.target.value) || 0)}
                        className="w-full h-7 px-1.5 text-right text-[11px] rounded border border-emerald-200 bg-emerald-50/30 focus:ring-1 focus:ring-emerald-300"
                        disabled={!isHR} />
                    </td>
                    <td className="px-1 py-1">
                      <input type="text" value={inp.incentive_reason || ''} onChange={e => updateInput(inp.employee_id, 'incentive_reason', e.target.value)}
                        className="w-full h-7 px-1.5 text-[11px] rounded border border-zinc-200 bg-white" disabled={!isHR} placeholder="—" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="number" value={inp.advance || 0} onChange={e => updateInput(inp.employee_id, 'advance', parseFloat(e.target.value) || 0)}
                        className="w-full h-7 px-1.5 text-right text-[11px] rounded border border-amber-200 bg-amber-50/30 focus:ring-1 focus:ring-amber-300"
                        disabled={!isHR} />
                    </td>
                    <td className="px-1 py-1">
                      <input type="text" value={inp.advance_reason || ''} onChange={e => updateInput(inp.employee_id, 'advance_reason', e.target.value)}
                        className="w-full h-7 px-1.5 text-[11px] rounded border border-zinc-200 bg-white" disabled={!isHR} placeholder="—" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="number" value={inp.penalty || 0} onChange={e => updateInput(inp.employee_id, 'penalty', parseFloat(e.target.value) || 0)}
                        className="w-full h-7 px-1.5 text-right text-[11px] rounded border border-red-200 bg-red-50/30 focus:ring-1 focus:ring-red-300"
                        disabled={!isHR} />
                    </td>
                    <td className="px-1 py-1">
                      <input type="text" value={inp.penalty_reason || ''} onChange={e => updateInput(inp.employee_id, 'penalty_reason', e.target.value)}
                        className="w-full h-7 px-1.5 text-[11px] rounded border border-zinc-200 bg-white" disabled={!isHR} placeholder="—" />
                    </td>
                    <td className="px-1 py-1">
                      <input type="text" value={inp.remarks || ''} onChange={e => updateInput(inp.employee_id, 'remarks', e.target.value)}
                        className="w-full h-7 px-1.5 text-[11px] rounded border border-zinc-200 bg-white" disabled={!isHR} placeholder="—" />
                    </td>
                    {isHR && (
                      <td className="px-1 py-1 text-center">
                        <button onClick={() => saveSingleInput(inp)} className="text-zinc-400 hover:text-zinc-900 transition-colors" title="Save row">
                          <Save className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {payrollInputs.length === 0 && (
            <div className="text-center py-8 text-zinc-400 text-sm">No active employees found</div>
          )}
        </div>
      ) : (
        /* ========== SALARY SLIPS TAB ========== */
        <>
          {slips.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-40">
                <FileText className="w-10 h-10 text-zinc-300 mb-3" />
                <p className="text-zinc-500">No salary slips for {month}</p>
                {isHR && <p className="text-xs text-zinc-400 mt-1">Fill Payroll Inputs first, then Generate Slips</p>}
              </CardContent>
            </Card>
          ) : (
            <div className="border border-zinc-200 rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Emp ID</th>
                    <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Name</th>
                    <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Dept</th>
                    <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Gross</th>
                    <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Earnings</th>
                    <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Deductions</th>
                    <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">Net Pay</th>
                    <th className="text-center px-4 py-2.5 text-[10px] uppercase tracking-widest text-zinc-500 font-medium">View</th>
                  </tr>
                </thead>
                <tbody>
                  {slips.map(slip => (
                    <tr key={slip.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`slip-row-${slip.id}`}>
                      <td className="px-4 py-2.5 text-zinc-500 font-mono text-xs">{slip.employee_code}</td>
                      <td className="px-4 py-2.5 font-medium text-zinc-900 text-xs">{slip.employee_name}</td>
                      <td className="px-4 py-2.5 text-zinc-500 text-xs">{slip.department || '-'}</td>
                      <td className="px-4 py-2.5 text-right text-zinc-700 text-xs">{fmt(slip.gross_salary)}</td>
                      <td className="px-4 py-2.5 text-right text-emerald-700 text-xs">{fmt(slip.total_earnings)}</td>
                      <td className="px-4 py-2.5 text-right text-red-600 text-xs">{fmt(slip.total_deductions)}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-zinc-950 text-xs">{fmt(slip.net_salary)}</td>
                      <td className="px-4 py-2.5 text-center">
                        <Button onClick={() => setViewSlip(slip)} variant="ghost" size="sm" data-testid={`view-slip-${slip.id}`}><FileText className="w-3.5 h-3.5" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Slip View Dialog (kept simple) */}
      <Dialog open={!!viewSlip} onOpenChange={() => setViewSlip(null)}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          {viewSlip && (
            <>
              <DialogHeader>
                <DialogTitle>Salary Slip — {viewSlip.month}</DialogTitle>
                <DialogDescription>{viewSlip.employee_name} ({viewSlip.employee_code})</DialogDescription>
              </DialogHeader>
              <div className="space-y-4" data-testid="salary-slip-detail">
                <div className="grid grid-cols-2 gap-2 text-sm border border-zinc-200 rounded-sm p-4">
                  <div><span className="text-zinc-500">Gross:</span> <span className="font-medium">{fmt(viewSlip.gross_salary)}</span></div>
                  <div><span className="text-zinc-500">Present:</span> <span className="font-medium">{viewSlip.present_days} days</span></div>
                  <div><span className="text-zinc-500">Absent:</span> <span className="font-medium">{viewSlip.absent_days} days</span></div>
                  <div><span className="text-zinc-500">Working Days:</span> <span className="font-medium">{viewSlip.working_days || 30}</span></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {['earnings', 'deductions'].map(type => (
                    <div key={type} className="border border-zinc-200 rounded-sm p-4">
                      <h4 className={`text-xs font-bold uppercase tracking-widest mb-2 ${type === 'earnings' ? 'text-emerald-700' : 'text-red-700'}`}>{type}</h4>
                      {(viewSlip[type] || []).map((c, i) => (
                        <div key={i} className="flex justify-between text-sm py-1 border-b border-zinc-50 last:border-0">
                          <span className="text-zinc-600">{c.name}</span>
                          <span className="font-medium">{fmt(c.amount)}</span>
                        </div>
                      ))}
                      <div className={`flex justify-between text-sm py-2 mt-1 border-t-2 border-zinc-200 font-bold ${type === 'earnings' ? 'text-emerald-700' : 'text-red-700'}`}>
                        <span>Total</span><span>{fmt(type === 'earnings' ? viewSlip.total_earnings : viewSlip.total_deductions)}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="bg-zinc-900 rounded-sm p-4 text-center">
                  <div className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">Net Pay</div>
                  <div className="text-2xl font-bold text-white" data-testid="net-pay">{fmt(viewSlip.net_salary)}</div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Payroll;
