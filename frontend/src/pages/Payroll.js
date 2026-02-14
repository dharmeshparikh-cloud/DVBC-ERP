import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { DollarSign, FileText, Download, Settings, RefreshCw, Users as UsersIcon } from 'lucide-react';
import { toast } from 'sonner';

const Payroll = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [slips, setSlips] = useState([]);
  const [components, setComponents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [viewSlip, setViewSlip] = useState(null);
  const [activeTab, setActiveTab] = useState('slips');

  const isHR = ['admin', 'hr_manager'].includes(user?.role);

  useEffect(() => { fetchData(); }, [month]);

  const fetchData = async () => {
    try {
      const [empRes, slipsRes, compRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/payroll/salary-slips?month=${month}`),
        axios.get(`${API}/payroll/salary-components`)
      ]);
      setEmployees(empRes.data.filter(e => e.salary > 0));
      setSlips(slipsRes.data);
      setComponents(compRes.data);
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

  const formatCurrency = (v) => `₹${(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;

  const totalPayout = slips.reduce((s, sl) => s + (sl.net_salary || 0), 0);

  return (
    <div data-testid="payroll-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Payroll</h1>
          <p className="text-zinc-500">Manage salary components, generate and download salary slips</p>
        </div>
        {isHR && (
          <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="generate-slip-btn">
                <RefreshCw className="w-4 h-4 mr-2" /> Generate Slips
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-md">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Generate Salary Slips</DialogTitle>
                <DialogDescription className="text-zinc-500">Select employee or generate for all</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Month</Label>
                  <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Employee</Label>
                  <select value={selectedEmployee} onChange={(e) => setSelectedEmployee(e.target.value)}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="payroll-emp-select">
                    <option value="">Select...</option>
                    <option value="all">All Employees (Bulk)</option>
                    {employees.map(e => (
                      <option key={e.id} value={e.id}>{e.employee_id} - {e.first_name} {e.last_name} ({formatCurrency(e.salary)})</option>
                    ))}
                  </select>
                </div>
                <Button onClick={handleGenerate} disabled={!selectedEmployee}
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="confirm-generate">
                  Generate
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <FileText className="w-6 h-6 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Slips Generated</div>
              <div className="text-2xl font-semibold text-zinc-950" data-testid="payroll-slip-count">{slips.length}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <DollarSign className="w-6 h-6 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Total Payout</div>
              <div className="text-2xl font-semibold text-zinc-950">{formatCurrency(totalPayout)}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <UsersIcon className="w-6 h-6 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Employees (With Salary)</div>
              <div className="text-2xl font-semibold text-zinc-950">{employees.length}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Month Picker + Tabs */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-1 border-b border-zinc-200">
          <button onClick={() => setActiveTab('slips')} data-testid="tab-slips"
            className={`px-4 py-2 text-sm font-medium ${activeTab === 'slips' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>
            Salary Slips
          </button>
          <button onClick={() => setActiveTab('components')} data-testid="tab-components"
            className={`px-4 py-2 text-sm font-medium ${activeTab === 'components' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>
            Salary Components
          </button>
        </div>
        <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
          className="rounded-sm border-zinc-200 w-44" data-testid="payroll-month" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : activeTab === 'components' ? (
        <div className="grid grid-cols-2 gap-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-700 mb-3">Earnings</h3>
              <div className="space-y-2">
                {components?.earnings?.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-emerald-50 rounded-sm border border-emerald-100">
                    <span className="text-sm text-zinc-700">{c.name}</span>
                    <span className="text-sm font-medium text-emerald-700">
                      {c.percentage ? `${c.percentage}% of CTC` : formatCurrency(c.fixed)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-700 mb-3">Deductions</h3>
              <div className="space-y-2">
                {components?.deductions?.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-red-50 rounded-sm border border-red-100">
                    <span className="text-sm text-zinc-700">{c.name}</span>
                    <span className="text-sm font-medium text-red-700">
                      {c.percentage ? `${c.percentage}% of CTC` : formatCurrency(c.fixed)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <>
          {slips.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-40">
                <FileText className="w-10 h-10 text-zinc-300 mb-3" />
                <p className="text-zinc-500">No salary slips for {month}</p>
                {isHR && <p className="text-xs text-zinc-400 mt-1">Click "Generate Slips" to create</p>}
              </CardContent>
            </Card>
          ) : (
            <div className="border border-zinc-200 rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Emp ID</th>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Name</th>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Department</th>
                    <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Gross</th>
                    <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Earnings</th>
                    <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Deductions</th>
                    <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Net Pay</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {slips.map(slip => (
                    <tr key={slip.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`slip-row-${slip.id}`}>
                      <td className="px-4 py-3 text-zinc-600 font-mono text-xs">{slip.employee_code}</td>
                      <td className="px-4 py-3 font-medium text-zinc-950">{slip.employee_name}</td>
                      <td className="px-4 py-3 text-zinc-600">{slip.department || '-'}</td>
                      <td className="px-4 py-3 text-right text-zinc-700">{formatCurrency(slip.gross_salary)}</td>
                      <td className="px-4 py-3 text-right text-emerald-700">{formatCurrency(slip.total_earnings)}</td>
                      <td className="px-4 py-3 text-right text-red-600">{formatCurrency(slip.total_deductions)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-zinc-950">{formatCurrency(slip.net_salary)}</td>
                      <td className="px-4 py-3 text-center">
                        <Button onClick={() => setViewSlip(slip)} variant="ghost" size="sm" className="text-zinc-600" data-testid={`view-slip-${slip.id}`}>
                          <FileText className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Salary Slip View Dialog */}
      <Dialog open={!!viewSlip} onOpenChange={() => setViewSlip(null)}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          {viewSlip && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Salary Slip</DialogTitle>
                <DialogDescription className="text-zinc-500">{viewSlip.month} | {viewSlip.employee_name}</DialogDescription>
              </DialogHeader>
              <div className="space-y-4" id="salary-slip-content" data-testid="salary-slip-detail">
                {/* Header */}
                <div className="border border-zinc-200 rounded-sm p-4">
                  <div className="text-center mb-4">
                    <div className="text-lg font-bold text-zinc-950">D&V Business Consulting</div>
                    <div className="text-xs text-zinc-500">Salary Slip for {viewSlip.month}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-zinc-500">Name:</span> <span className="font-medium">{viewSlip.employee_name}</span></div>
                    <div><span className="text-zinc-500">Emp ID:</span> <span className="font-medium">{viewSlip.employee_code}</span></div>
                    <div><span className="text-zinc-500">Department:</span> <span className="font-medium">{viewSlip.department || '-'}</span></div>
                    <div><span className="text-zinc-500">Designation:</span> <span className="font-medium">{viewSlip.designation || '-'}</span></div>
                    <div><span className="text-zinc-500">Days Present:</span> <span className="font-medium">{viewSlip.present_days}</span></div>
                    <div><span className="text-zinc-500">Days Absent:</span> <span className="font-medium">{viewSlip.absent_days}</span></div>
                  </div>
                </div>
                {/* Earnings & Deductions */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="border border-zinc-200 rounded-sm p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-3">Earnings</h4>
                    {viewSlip.earnings?.map((e, i) => (
                      <div key={i} className="flex justify-between text-sm py-1 border-b border-zinc-100 last:border-0">
                        <span className="text-zinc-600">{e.name}</span>
                        <span className="font-medium text-zinc-950">{formatCurrency(e.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm py-2 mt-2 border-t-2 border-zinc-200 font-semibold">
                      <span className="text-emerald-700">Total Earnings</span>
                      <span className="text-emerald-700">{formatCurrency(viewSlip.total_earnings)}</span>
                    </div>
                  </div>
                  <div className="border border-zinc-200 rounded-sm p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-red-600 mb-3">Deductions</h4>
                    {viewSlip.deductions?.map((d, i) => (
                      <div key={i} className="flex justify-between text-sm py-1 border-b border-zinc-100 last:border-0">
                        <span className="text-zinc-600">{d.name}</span>
                        <span className="font-medium text-zinc-950">{formatCurrency(d.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm py-2 mt-2 border-t-2 border-zinc-200 font-semibold">
                      <span className="text-red-600">Total Deductions</span>
                      <span className="text-red-600">{formatCurrency(viewSlip.total_deductions)}</span>
                    </div>
                  </div>
                </div>
                {/* Net Pay */}
                <div className="border-2 border-zinc-950 rounded-sm p-4 text-center">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Net Pay</div>
                  <div className="text-3xl font-bold text-zinc-950" data-testid="net-pay">{formatCurrency(viewSlip.net_salary)}</div>
                </div>
                {/* Bank Details */}
                {viewSlip.bank_details && (
                  <div className="border border-zinc-200 rounded-sm p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-2">Bank Details</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><span className="text-zinc-500">Account:</span> <span className="font-medium">{viewSlip.bank_details.account_number || '-'}</span></div>
                      <div><span className="text-zinc-500">IFSC:</span> <span className="font-medium">{viewSlip.bank_details.ifsc_code || '-'}</span></div>
                      <div><span className="text-zinc-500">Bank:</span> <span className="font-medium">{viewSlip.bank_details.bank_name || '-'}</span></div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Payroll;
