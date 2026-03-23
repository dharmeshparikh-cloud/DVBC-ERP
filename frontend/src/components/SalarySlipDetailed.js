import React, { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useTheme } from '../contexts/ThemeContext';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
  FileText,
  Download,
  Building2,
  User,
  Calendar,
  IndianRupee,
  Clock,
  Printer,
  ChevronDown,
  ChevronUp,
  Calculator,
  Info,
  CheckCircle2,
  AlertTriangle,
  Loader2
} from 'lucide-react';

export default function SalarySlipDetailed({ employeeId, month, onClose }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [showBreakdown, setShowBreakdown] = useState(false);
  const printRef = useRef(null);
  
  // Fetch calculation data
  const { data: calculation, isLoading, error } = useQuery({
    queryKey: ['salary-slip-detail', employeeId, month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/engine/breakdown/${employeeId}/${month}`);
      return res.data;
    },
    enabled: !!employeeId && !!month
  });
  
  // Fetch employee details
  const { data: employee } = useQuery({
    queryKey: ['employee-detail', employeeId],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/${employeeId}`);
      return res.data;
    },
    enabled: !!employeeId
  });
  
  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };
  
  // Format date
  const formatMonth = (monthStr) => {
    const [year, mon] = monthStr.split('-');
    const date = new Date(year, parseInt(mon) - 1);
    return date.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  };
  
  // Print handler
  const handlePrint = () => {
    const printContent = printRef.current;
    const originalContents = document.body.innerHTML;
    document.body.innerHTML = printContent.innerHTML;
    window.print();
    document.body.innerHTML = originalContents;
    window.location.reload();
  };
  
  // Download as PDF (using print to PDF)
  const handleDownload = () => {
    toast.info('Use browser Print → Save as PDF');
    handlePrint();
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }
  
  if (error || !calculation) {
    return (
      <div className={`p-6 text-center ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
        <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-amber-500" />
        <p>No salary slip available for this month</p>
      </div>
    );
  }
  
  const fullCalc = calculation.full_calculation || {};
  const earnings = fullCalc.earnings || [];
  const deductions = fullCalc.deductions || [];
  
  return (
    <div className="space-y-4">
      {/* Action Buttons */}
      <div className="flex gap-2 justify-end no-print">
        <Button variant="outline" onClick={handlePrint}>
          <Printer className="w-4 h-4 mr-2" />
          Print
        </Button>
        <Button onClick={handleDownload} className="bg-blue-600 hover:bg-blue-700">
          <Download className="w-4 h-4 mr-2" />
          Download PDF
        </Button>
      </div>
      
      {/* Salary Slip Content - Printable */}
      <div ref={printRef}>
        <Card className={`${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white'} print:bg-white print:border-gray-300`}>
          {/* Header */}
          <CardHeader className="border-b pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-lg ${isDark ? 'bg-blue-900/30' : 'bg-blue-100'}`}>
                  <Building2 className="w-8 h-8 text-blue-600" />
                </div>
                <div>
                  <h1 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    NETRA ERP Consulting
                  </h1>
                  <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                    Salary Slip for {formatMonth(month)}
                  </p>
                </div>
              </div>
              <Badge className="bg-green-500/20 text-green-600">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                Generated
              </Badge>
            </div>
          </CardHeader>
          
          <CardContent className="pt-6 space-y-6">
            {/* Employee Information */}
            <div className={`grid grid-cols-2 gap-6 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Employee Name</p>
                    <p className="font-semibold">{calculation.employee_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Employee ID</p>
                    <p className="font-medium">{fullCalc.employee_code || '-'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Department</p>
                    <p className="font-medium">{fullCalc.department || '-'}</p>
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Pay Period</p>
                    <p className="font-semibold">{formatMonth(month)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Days in Month / LOP Days</p>
                    <p className="font-medium">{fullCalc.days_in_month || 30} / {fullCalc.lop_days || 0}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <IndianRupee className="w-4 h-4 text-blue-500" />
                  <div>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>Gross Monthly</p>
                    <p className="font-medium">{formatCurrency(fullCalc.gross_monthly)}</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Earnings & Deductions Table */}
            <div className="grid grid-cols-2 gap-6">
              {/* Earnings */}
              <div>
                <h3 className={`font-semibold mb-3 flex items-center gap-2 ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                  <ChevronUp className="w-4 h-4" />
                  Earnings
                </h3>
                <div className={`rounded-lg border ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className={`border-b ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-gray-200 bg-gray-50'}`}>
                        <th className="text-left p-2 font-medium">Component</th>
                        <th className="text-right p-2 font-medium">Amount (₹)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {earnings.map((e, i) => (
                        <tr key={i} className={`border-b ${isDark ? 'border-zinc-800' : 'border-gray-100'}`}>
                          <td className="p-2">{e.name}</td>
                          <td className="p-2 text-right font-medium text-green-600">
                            {formatCurrency(e.amount)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className={`font-bold ${isDark ? 'bg-green-900/20' : 'bg-green-50'}`}>
                        <td className="p-2">Total Earnings</td>
                        <td className="p-2 text-right text-green-600">
                          {formatCurrency(fullCalc.total_earnings)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
              
              {/* Deductions */}
              <div>
                <h3 className={`font-semibold mb-3 flex items-center gap-2 ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                  <ChevronDown className="w-4 h-4" />
                  Deductions
                </h3>
                <div className={`rounded-lg border ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className={`border-b ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-gray-200 bg-gray-50'}`}>
                        <th className="text-left p-2 font-medium">Component</th>
                        <th className="text-right p-2 font-medium">Amount (₹)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deductions.length > 0 ? deductions.map((d, i) => (
                        <tr key={i} className={`border-b ${isDark ? 'border-zinc-800' : 'border-gray-100'}`}>
                          <td className="p-2">{d.name}</td>
                          <td className="p-2 text-right font-medium text-red-600">
                            {formatCurrency(d.amount)}
                          </td>
                        </tr>
                      )) : (
                        <tr>
                          <td colSpan={2} className={`p-2 text-center ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                            No deductions
                          </td>
                        </tr>
                      )}
                    </tbody>
                    <tfoot>
                      <tr className={`font-bold ${isDark ? 'bg-red-900/20' : 'bg-red-50'}`}>
                        <td className="p-2">Total Deductions</td>
                        <td className="p-2 text-right text-red-600">
                          {formatCurrency(fullCalc.total_deductions)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </div>
            
            {/* Net Salary Summary */}
            <div className={`p-4 rounded-lg border-2 ${isDark ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-300'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-600'}`}>Net Salary (Take Home)</p>
                  <p className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {formatCurrency(fullCalc.net_salary)}
                  </p>
                </div>
                {fullCalc.reimbursements > 0 && (
                  <div className="text-right">
                    <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>+ Reimbursements</p>
                    <p className="font-bold text-green-600">{formatCurrency(fullCalc.reimbursements)}</p>
                    <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
                      Net Payable: {formatCurrency(fullCalc.net_payable)}
                    </p>
                  </div>
                )}
              </div>
            </div>
            
            {/* Employer Contributions */}
            {fullCalc.employer_contributions && (
              <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
                <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                  Employer Contributions (Not part of take-home)
                </p>
                <div className="flex gap-4 text-sm">
                  <span>PF: {formatCurrency(fullCalc.employer_contributions.pf)}</span>
                  {fullCalc.employer_contributions.esi > 0 && (
                    <span>ESI: {formatCurrency(fullCalc.employer_contributions.esi)}</span>
                  )}
                </div>
              </div>
            )}
            
            {/* Calculation Breakdown Toggle */}
            <div className="no-print">
              <Button
                variant="ghost"
                onClick={() => setShowBreakdown(!showBreakdown)}
                className="w-full justify-between"
              >
                <span className="flex items-center gap-2">
                  <Calculator className="w-4 h-4" />
                  View Calculation Breakdown (Traceability)
                </span>
                {showBreakdown ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
              
              {showBreakdown && (
                <div className={`mt-4 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-gray-50'}`}>
                  <h4 className={`font-medium mb-3 flex items-center gap-2 ${isDark ? 'text-zinc-300' : ''}`}>
                    <Info className="w-4 h-4 text-blue-500" />
                    Field-Level Calculation Audit
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className={`border-b ${isDark ? 'border-zinc-700' : 'border-gray-200'}`}>
                          <th className="text-left p-2">Component</th>
                          <th className="text-left p-2">Input Values</th>
                          <th className="text-left p-2">Formula Applied</th>
                          <th className="text-right p-2">Output</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calculation.breakdown?.map((row, i) => (
                          <tr key={i} className={`border-b ${isDark ? 'border-zinc-800' : 'border-gray-100'}`}>
                            <td className={`p-2 ${row.type === 'Earning' ? 'text-green-600' : 'text-red-600'}`}>
                              {row.component}
                            </td>
                            <td className={`p-2 ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                              {Object.entries(row.input_values || {}).map(([k, v]) => (
                                <span key={k} className="block">{k}: {typeof v === 'number' ? v.toLocaleString('en-IN') : v}</span>
                              ))}
                            </td>
                            <td className={`p-2 font-mono ${isDark ? 'text-zinc-400' : 'text-gray-500'}`}>
                              {row.formula}
                            </td>
                            <td className={`p-2 text-right font-medium ${row.type === 'Earning' ? 'text-green-600' : 'text-red-600'}`}>
                              {formatCurrency(row.output)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
            
            {/* Footer */}
            <Separator />
            <div className={`text-xs text-center ${isDark ? 'text-zinc-500' : 'text-gray-400'}`}>
              <p>This is a computer-generated salary slip and does not require a signature.</p>
              <p>Generated on {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}</p>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Print Styles */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; }
          * { color: black !important; }
        }
      `}</style>
    </div>
  );
}
