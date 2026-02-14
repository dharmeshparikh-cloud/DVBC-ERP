import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { FileText, DollarSign, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

const MySalarySlips = () => {
  const [slips, setSlips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewSlip, setViewSlip] = useState(null);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/my/salary-slips`);
      setSlips(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to fetch salary slips');
    } finally {
      setLoading(false);
    }
  };

  const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;

  return (
    <div data-testid="my-salary-slips-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">My Salary Slips</h1>
        <p className="text-zinc-500">View all your monthly salary statements</p>
      </div>

      {/* Summary */}
      {slips.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <FileText className="w-6 h-6 text-zinc-300" />
              <div>
                <div className="text-xs uppercase tracking-wide text-zinc-500">Total Slips</div>
                <div className="text-2xl font-semibold text-zinc-950" data-testid="total-slips">{slips.length}</div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <DollarSign className="w-6 h-6 text-zinc-300" />
              <div>
                <div className="text-xs uppercase tracking-wide text-zinc-500">Latest Net Pay</div>
                <div className="text-2xl font-semibold text-zinc-950">{fmt(slips[0]?.net_salary)}</div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4 flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-zinc-300" />
              <div>
                <div className="text-xs uppercase tracking-wide text-zinc-500">Total Earned (YTD)</div>
                <div className="text-2xl font-semibold text-zinc-950">{fmt(slips.reduce((s, sl) => s + (sl.net_salary || 0), 0))}</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : slips.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <FileText className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No salary slips available yet</p>
            <p className="text-xs text-zinc-400 mt-1">Salary slips will appear here after payroll is processed</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Month</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Gross</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Earnings</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Deductions</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Net Pay</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Days Present</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">View</th>
              </tr>
            </thead>
            <tbody>
              {slips.map(slip => (
                <tr key={slip.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`my-slip-${slip.month}`}>
                  <td className="px-4 py-3 font-medium text-zinc-950">{slip.month}</td>
                  <td className="px-4 py-3 text-right text-zinc-700">{fmt(slip.gross_salary)}</td>
                  <td className="px-4 py-3 text-right text-emerald-700">{fmt(slip.total_earnings)}</td>
                  <td className="px-4 py-3 text-right text-red-600">{fmt(slip.total_deductions)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-zinc-950">{fmt(slip.net_salary)}</td>
                  <td className="px-4 py-3 text-center text-zinc-700">{slip.present_days || 0}</td>
                  <td className="px-4 py-3 text-center">
                    <Button onClick={() => setViewSlip(slip)} variant="ghost" size="sm" data-testid={`view-slip-${slip.month}`}>
                      <FileText className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Salary Slip Detail */}
      <Dialog open={!!viewSlip} onOpenChange={() => setViewSlip(null)}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          {viewSlip && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Salary Slip — {viewSlip.month}</DialogTitle>
                <DialogDescription className="text-zinc-500">{viewSlip.employee_name} ({viewSlip.employee_code})</DialogDescription>
              </DialogHeader>
              <div className="space-y-4" data-testid="slip-detail">
                <div className="border border-zinc-200 rounded-sm p-4">
                  <div className="text-center mb-3">
                    <div className="text-lg font-bold text-zinc-950">D&V Business Consulting</div>
                    <div className="text-xs text-zinc-500">Salary Slip for {viewSlip.month}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-zinc-500">Name:</span> <span className="font-medium">{viewSlip.employee_name}</span></div>
                    <div><span className="text-zinc-500">Emp ID:</span> <span className="font-medium">{viewSlip.employee_code}</span></div>
                    <div><span className="text-zinc-500">Department:</span> <span className="font-medium">{viewSlip.department || '-'}</span></div>
                    <div><span className="text-zinc-500">Designation:</span> <span className="font-medium">{viewSlip.designation || '-'}</span></div>
                    <div><span className="text-zinc-500">Present:</span> <span className="font-medium">{viewSlip.present_days} days</span></div>
                    <div><span className="text-zinc-500">Absent:</span> <span className="font-medium">{viewSlip.absent_days} days</span></div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="border border-zinc-200 rounded-sm p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-3">Earnings</h4>
                    {viewSlip.earnings?.map((e, i) => (
                      <div key={i} className="flex justify-between text-sm py-1 border-b border-zinc-100 last:border-0">
                        <span className="text-zinc-600">{e.name}</span>
                        <span className="font-medium text-zinc-950">{fmt(e.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm py-2 mt-2 border-t-2 border-zinc-200 font-semibold">
                      <span className="text-emerald-700">Total Earnings</span>
                      <span className="text-emerald-700">{fmt(viewSlip.total_earnings)}</span>
                    </div>
                  </div>
                  <div className="border border-zinc-200 rounded-sm p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-red-600 mb-3">Deductions</h4>
                    {viewSlip.deductions?.map((d, i) => (
                      <div key={i} className="flex justify-between text-sm py-1 border-b border-zinc-100 last:border-0">
                        <span className="text-zinc-600">{d.name}</span>
                        <span className="font-medium text-zinc-950">{fmt(d.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm py-2 mt-2 border-t-2 border-zinc-200 font-semibold">
                      <span className="text-red-600">Total Deductions</span>
                      <span className="text-red-600">{fmt(viewSlip.total_deductions)}</span>
                    </div>
                  </div>
                </div>
                <div className="border-2 border-zinc-950 rounded-sm p-4 text-center">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Net Pay</div>
                  <div className="text-3xl font-bold text-zinc-950" data-testid="my-net-pay">{fmt(viewSlip.net_salary)}</div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MySalarySlips;
