import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent } from '../components/ui/dialog';
import { FileText, DollarSign, TrendingUp, Download, X, Printer } from 'lucide-react';
import { toast } from 'sonner';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;

const numberToWords = (num) => {
  if (!num || num === 0) return 'Zero';
  const ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten','Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen','Eighteen','Nineteen'];
  const tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety'];
  const scales = ['','Thousand','Lakh','Crore'];
  const n = Math.round(num);
  if (n < 20) return ones[n];
  if (n < 100) return tens[Math.floor(n/10)] + (n%10 ? ' ' + ones[n%10] : '');
  if (n < 1000) return ones[Math.floor(n/100)] + ' Hundred' + (n%100 ? ' and ' + numberToWords(n%100) : '');
  if (n < 100000) return numberToWords(Math.floor(n/1000)) + ' Thousand' + (n%1000 ? ' ' + numberToWords(n%1000) : '');
  if (n < 10000000) return numberToWords(Math.floor(n/100000)) + ' Lakh' + (n%100000 ? ' ' + numberToWords(n%100000) : '');
  return numberToWords(Math.floor(n/10000000)) + ' Crore' + (n%10000000 ? ' ' + numberToWords(n%10000000) : '');
};

// Printable/Downloadable Salary Slip Component
const SalarySlipDocument = ({ slip, printRef }) => {
  const monthLabel = slip.month ? new Date(slip.month + '-01').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : slip.month;

  return (
    <div ref={printRef} className="bg-white" id="salary-slip-printable" data-testid="salary-slip-document">
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #salary-slip-printable, #salary-slip-printable * { visibility: visible; }
          #salary-slip-printable { position: absolute; left: 0; top: 0; width: 100%; }
          .no-print { display: none !important; }
        }
      `}</style>

      {/* Header */}
      <div className="border-b-2 border-zinc-800 pb-4 mb-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img src={LOGO_URL} alt="DVBC" className="h-14 w-auto" crossOrigin="anonymous" />
            <div>
              <h1 className="text-lg font-bold text-zinc-900 tracking-wide">D&V BUSINESS CONSULTING</h1>
              <p className="text-[11px] text-zinc-500">DVBC - NETRA | Business Management Platform</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold text-zinc-900 uppercase tracking-widest bg-zinc-100 px-3 py-1.5 rounded">Payslip</div>
            <div className="text-[10px] text-zinc-400 mt-1">Ref: DVBC/{slip.employee_code}/{slip.month}</div>
          </div>
        </div>
      </div>

      {/* Period Bar */}
      <div className="bg-zinc-900 text-white text-center py-2 rounded mb-5">
        <span className="text-xs font-semibold uppercase tracking-widest">Salary Statement for {monthLabel}</span>
      </div>

      {/* Employee Info Grid */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-2 mb-5 text-[12px]">
        {[
          ['Employee Name', slip.employee_name],
          ['Employee ID', slip.employee_code],
          ['Department', slip.department || '—'],
          ['Designation', slip.designation || '—'],
          ['Days in Month', slip.working_days || 30],
          ['Days Present', slip.present_days || 0],
          ['Days Absent', slip.absent_days || 0],
          ['Pay Date', new Date().toLocaleDateString('en-IN')],
        ].map(([label, value], i) => (
          <div key={i} className="flex items-center py-1 border-b border-zinc-100">
            <span className="w-32 text-zinc-500 flex-shrink-0">{label}</span>
            <span className="font-medium text-zinc-900">{value}</span>
          </div>
        ))}
      </div>

      {/* Earnings & Deductions */}
      <div className="grid grid-cols-2 gap-6 mb-5">
        {/* Earnings */}
        <div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-t px-4 py-2">
            <h3 className="text-xs font-bold uppercase tracking-widest text-emerald-800">Earnings</h3>
          </div>
          <div className="border border-t-0 border-zinc-200 rounded-b">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="text-left px-4 py-2 text-zinc-500 font-medium">Component</th>
                  <th className="text-right px-4 py-2 text-zinc-500 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {(slip.earnings || []).map((e, i) => (
                  <tr key={i} className="border-b border-zinc-50">
                    <td className="px-4 py-1.5 text-zinc-700">{e.name}</td>
                    <td className="px-4 py-1.5 text-right font-medium text-zinc-900">{fmt(e.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-emerald-50/50">
                  <td className="px-4 py-2 font-bold text-emerald-800">Total Earnings</td>
                  <td className="px-4 py-2 text-right font-bold text-emerald-800">{fmt(slip.total_earnings)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Deductions */}
        <div>
          <div className="bg-red-50 border border-red-200 rounded-t px-4 py-2">
            <h3 className="text-xs font-bold uppercase tracking-widest text-red-800">Deductions</h3>
          </div>
          <div className="border border-t-0 border-zinc-200 rounded-b">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="text-left px-4 py-2 text-zinc-500 font-medium">Component</th>
                  <th className="text-right px-4 py-2 text-zinc-500 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {(slip.deductions || []).map((d, i) => (
                  <tr key={i} className="border-b border-zinc-50">
                    <td className="px-4 py-1.5 text-zinc-700">{d.name}</td>
                    <td className="px-4 py-1.5 text-right font-medium text-zinc-900">{fmt(d.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-red-50/50">
                  <td className="px-4 py-2 font-bold text-red-800">Total Deductions</td>
                  <td className="px-4 py-2 text-right font-bold text-red-800">{fmt(slip.total_deductions)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      {/* Net Pay */}
      <div className="bg-zinc-900 rounded p-4 mb-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">Net Payable Amount</div>
            <div className="text-2xl font-bold text-white" data-testid="my-net-pay">{fmt(slip.net_salary)}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-widest text-zinc-400 mb-0.5">In Words</div>
            <div className="text-xs text-zinc-300 italic max-w-[280px]">Rupees {numberToWords(slip.net_salary)} Only</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t-2 border-zinc-200 pt-4 mt-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Employer Signature</div>
            <div className="mt-6 border-b border-zinc-300 w-40" />
            <div className="text-[10px] text-zinc-500 mt-1">D&V Business Consulting</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Employee Signature</div>
            <div className="mt-6 border-b border-zinc-300 w-40" />
            <div className="text-[10px] text-zinc-500 mt-1">{slip.employee_name}</div>
          </div>
        </div>
        <div className="bg-zinc-50 rounded p-3 mt-4">
          <p className="text-[9px] text-zinc-400 leading-relaxed text-center">
            This is a system-generated salary slip from DVBC - NETRA and does not require a physical signature.
            For any discrepancies, please contact the HR department within 7 working days of receipt.
            This document is confidential and intended solely for the named employee.
          </p>
          <p className="text-[9px] text-zinc-300 text-center mt-1">
            Generated on {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })} | D&V Business Consulting Pvt. Ltd.
          </p>
        </div>
      </div>
    </div>
  );
};

const MySalarySlips = () => {
  const [slips, setSlips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewSlip, setViewSlip] = useState(null);
  const printRef = useRef(null);

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

  const handlePrint = () => {
    const content = printRef.current;
    if (!content) return;
    const printWindow = window.open('', '_blank', 'width=800,height=1100');
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Salary Slip - ${viewSlip.employee_name} - ${viewSlip.month}</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; }
          @media print { body { padding: 12px; } }
        </style>
      </head>
      <body>${content.innerHTML}</body>
      </html>
    `);
    printWindow.document.close();
    setTimeout(() => { printWindow.print(); }, 500);
  };

  return (
    <div data-testid="my-salary-slips-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">My Salary Slips</h1>
        <p className="text-zinc-500">View and download your monthly salary statements</p>
      </div>

      {/* Summary Cards */}
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

      {/* Slips Table */}
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
          <table className="w-full text-sm" data-testid="slips-table">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Month</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Gross</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Earnings</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Deductions</th>
                <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Net Pay</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {slips.map(slip => (
                <tr key={slip.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`my-slip-${slip.month}`}>
                  <td className="px-4 py-3 font-medium text-zinc-950">
                    {slip.month ? new Date(slip.month + '-01').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : slip.month}
                  </td>
                  <td className="px-4 py-3 text-right text-zinc-700">{fmt(slip.gross_salary)}</td>
                  <td className="px-4 py-3 text-right text-emerald-700">{fmt(slip.total_earnings)}</td>
                  <td className="px-4 py-3 text-right text-red-600">{fmt(slip.total_deductions)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-zinc-950">{fmt(slip.net_salary)}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button onClick={() => setViewSlip(slip)} variant="ghost" size="sm" data-testid={`view-slip-${slip.month}`}>
                        <FileText className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Salary Slip Modal */}
      <Dialog open={!!viewSlip} onOpenChange={() => setViewSlip(null)}>
        <DialogContent className="border-zinc-200 rounded-lg max-w-3xl max-h-[92vh] overflow-y-auto p-0">
          {viewSlip && (
            <>
              {/* Action Bar */}
              <div className="sticky top-0 bg-white border-b border-zinc-200 px-6 py-3 flex items-center justify-between z-10 no-print">
                <h2 className="text-sm font-semibold text-zinc-800">
                  Salary Slip — {viewSlip.month ? new Date(viewSlip.month + '-01').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : viewSlip.month}
                </h2>
                <div className="flex items-center gap-2">
                  <Button onClick={handlePrint} variant="outline" size="sm" data-testid="download-slip-btn" className="text-xs gap-1.5">
                    <Download className="w-3.5 h-3.5" /> Download / Print
                  </Button>
                  <Button onClick={() => setViewSlip(null)} variant="ghost" size="sm">
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              {/* Slip Content */}
              <div className="p-6">
                <SalarySlipDocument slip={viewSlip} printRef={printRef} />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MySalarySlips;
