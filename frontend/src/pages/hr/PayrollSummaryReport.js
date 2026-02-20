import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { 
  FileText, Download, TrendingUp, TrendingDown, Minus, Users, 
  DollarSign, Calendar, RefreshCw, ArrowUpRight, ArrowDownRight,
  Building2, Clock, Gift, AlertTriangle
} from 'lucide-react';

const PayrollSummaryReport = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [report, setReport] = useState(null);
  const [prevReport, setPrevReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatedReports, setGeneratedReports] = useState([]);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    fetchReport();
    fetchGeneratedReports();
  }, [month]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      // Fetch current month report
      const res = await fetch(`${API}/payroll/summary-report?month=${month}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }

      // Fetch previous month for comparison
      const [year, mon] = month.split('-').map(Number);
      const prevMonth = mon === 1 
        ? `${year - 1}-12` 
        : `${year}-${String(mon - 1).padStart(2, '0')}`;
      
      const prevRes = await fetch(`${API}/payroll/summary-report?month=${prevMonth}`, { headers });
      if (prevRes.ok) {
        const prevData = await prevRes.json();
        setPrevReport(prevData);
      }
    } catch (error) {
      toast.error('Failed to fetch payroll report');
    } finally {
      setLoading(false);
    }
  };

  const fetchGeneratedReports = async () => {
    try {
      const res = await fetch(`${API}/payroll/generated-reports`, { headers });
      if (res.ok) {
        const data = await res.json();
        setGeneratedReports(data.reports || []);
      }
    } catch (error) {
      console.error('Error fetching generated reports:', error);
    }
  };

  const generateReport = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/payroll/generate-summary-report`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ month })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || 'Report generated successfully');
        fetchReport();
        fetchGeneratedReports();
      } else {
        const error = await res.json();
        toast.error(error.detail || 'Failed to generate report');
      }
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    if (!report) return;

    const headers = ['Metric', 'Current Month', 'Previous Month', 'Change'];
    const rows = [
      ['Total Employees', report.total_employees, prevReport?.total_employees || 0, calcChange(report.total_employees, prevReport?.total_employees)],
      ['Total Gross Salary', report.total_gross_salary, prevReport?.total_gross_salary || 0, calcChange(report.total_gross_salary, prevReport?.total_gross_salary)],
      ['Total Net Salary', report.total_net_salary, prevReport?.total_net_salary || 0, calcChange(report.total_net_salary, prevReport?.total_net_salary)],
      ['Total Deductions', report.total_deductions, prevReport?.total_deductions || 0, calcChange(report.total_deductions, prevReport?.total_deductions)],
      ['Total Reimbursements', report.total_reimbursements, prevReport?.total_reimbursements || 0, calcChange(report.total_reimbursements, prevReport?.total_reimbursements)],
      ['LOP Deductions', report.total_lop_deductions, prevReport?.total_lop_deductions || 0, calcChange(report.total_lop_deductions, prevReport?.total_lop_deductions)],
      ['Attendance Penalties', report.total_penalties, prevReport?.total_penalties || 0, calcChange(report.total_penalties, prevReport?.total_penalties)],
      ['Total Leave Days', report.total_leave_days, prevReport?.total_leave_days || 0, calcChange(report.total_leave_days, prevReport?.total_leave_days)],
      ['Avg Attendance %', report.avg_attendance_percent, prevReport?.avg_attendance_percent || 0, calcChange(report.avg_attendance_percent, prevReport?.avg_attendance_percent)],
    ];

    // Add department breakdown
    rows.push(['', '', '', '']);
    rows.push(['DEPARTMENT BREAKDOWN', '', '', '']);
    if (report.department_breakdown) {
      Object.entries(report.department_breakdown).forEach(([dept, data]) => {
        rows.push([`${dept} - Employees`, data.employee_count, '', '']);
        rows.push([`${dept} - Total Salary`, data.total_salary, '', '']);
      });
    }

    // Add employee details
    rows.push(['', '', '', '']);
    rows.push(['EMPLOYEE DETAILS', '', '', '']);
    rows.push(['Employee', 'Gross Salary', 'Deductions', 'Net Salary', 'Present Days', 'Leave Days', 'LOP']);
    if (report.employee_details) {
      report.employee_details.forEach(emp => {
        rows.push([
          emp.name,
          emp.gross_salary,
          emp.total_deductions,
          emp.net_salary,
          emp.present_days,
          emp.leave_days,
          emp.lop_days
        ]);
      });
    }

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `payroll_summary_${month}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  const calcChange = (current, previous) => {
    if (!previous || previous === 0) return 'N/A';
    const change = ((current - previous) / previous * 100).toFixed(1);
    return `${change > 0 ? '+' : ''}${change}%`;
  };

  const getChangeIndicator = (current, previous, inverse = false) => {
    if (!previous || previous === 0) return { icon: Minus, color: 'text-zinc-600', value: 'N/A' };
    const change = ((current - previous) / previous * 100).toFixed(1);
    const isPositive = change > 0;
    const isGood = inverse ? !isPositive : isPositive;
    
    return {
      icon: isPositive ? ArrowUpRight : ArrowDownRight,
      color: isGood ? 'text-green-400' : 'text-red-400',
      value: `${isPositive ? '+' : ''}${change}%`
    };
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value || 0);
  };

  return (
    <div className="p-6 space-y-6" data-testid="payroll-summary-report">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Payroll Summary Report</h1>
          <p className="text-zinc-600">Monthly payroll overview with comparison to previous month</p>
        </div>
        <div className="flex items-center gap-3">
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-40 bg-zinc-50 border-zinc-300"
            data-testid="month-selector"
          />
          <Button onClick={fetchReport} variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={generateReport} className="bg-blue-600 hover:bg-blue-700" disabled={loading}>
            <FileText className="w-4 h-4 mr-2" />
            Generate Report
          </Button>
          <Button onClick={downloadCSV} variant="outline" disabled={!report}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-600">Loading report data...</div>
      ) : report ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-white border-zinc-200">
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-zinc-600">Total Employees</p>
                    <p className="text-3xl font-bold text-zinc-900">{report.total_employees}</p>
                    {prevReport && (
                      <div className={`flex items-center gap-1 mt-1 text-sm ${getChangeIndicator(report.total_employees, prevReport.total_employees).color}`}>
                        {React.createElement(getChangeIndicator(report.total_employees, prevReport.total_employees).icon, { className: 'w-4 h-4' })}
                        <span>{getChangeIndicator(report.total_employees, prevReport.total_employees).value}</span>
                      </div>
                    )}
                  </div>
                  <div className="p-3 bg-blue-500/20 rounded-lg">
                    <Users className="w-6 h-6 text-blue-400" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-zinc-200">
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-zinc-600">Total Net Salary</p>
                    <p className="text-3xl font-bold text-zinc-900">{formatCurrency(report.total_net_salary)}</p>
                    {prevReport && (
                      <div className={`flex items-center gap-1 mt-1 text-sm ${getChangeIndicator(report.total_net_salary, prevReport.total_net_salary).color}`}>
                        {React.createElement(getChangeIndicator(report.total_net_salary, prevReport.total_net_salary).icon, { className: 'w-4 h-4' })}
                        <span>{getChangeIndicator(report.total_net_salary, prevReport.total_net_salary).value}</span>
                      </div>
                    )}
                  </div>
                  <div className="p-3 bg-green-500/20 rounded-lg">
                    <DollarSign className="w-6 h-6 text-green-400" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-zinc-200">
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-zinc-600">Total Deductions</p>
                    <p className="text-3xl font-bold text-zinc-900">{formatCurrency(report.total_deductions)}</p>
                    {prevReport && (
                      <div className={`flex items-center gap-1 mt-1 text-sm ${getChangeIndicator(report.total_deductions, prevReport.total_deductions, true).color}`}>
                        {React.createElement(getChangeIndicator(report.total_deductions, prevReport.total_deductions, true).icon, { className: 'w-4 h-4' })}
                        <span>{getChangeIndicator(report.total_deductions, prevReport.total_deductions, true).value}</span>
                      </div>
                    )}
                  </div>
                  <div className="p-3 bg-red-500/20 rounded-lg">
                    <TrendingDown className="w-6 h-6 text-red-400" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-zinc-200">
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-zinc-600">Avg Attendance</p>
                    <p className="text-3xl font-bold text-zinc-900">{report.avg_attendance_percent?.toFixed(1) || 0}%</p>
                    {prevReport && (
                      <div className={`flex items-center gap-1 mt-1 text-sm ${getChangeIndicator(report.avg_attendance_percent, prevReport.avg_attendance_percent).color}`}>
                        {React.createElement(getChangeIndicator(report.avg_attendance_percent, prevReport.avg_attendance_percent).icon, { className: 'w-4 h-4' })}
                        <span>{getChangeIndicator(report.avg_attendance_percent, prevReport.avg_attendance_percent).value}</span>
                      </div>
                    )}
                  </div>
                  <div className="p-3 bg-purple-500/20 rounded-lg">
                    <Clock className="w-6 h-6 text-purple-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Secondary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-white border-zinc-200">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <Gift className="w-5 h-5 text-orange-400" />
                  <div>
                    <p className="text-xs text-zinc-600">Total Reimbursements</p>
                    <p className="text-lg font-semibold text-zinc-900">{formatCurrency(report.total_reimbursements)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-white border-zinc-200">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-yellow-400" />
                  <div>
                    <p className="text-xs text-zinc-600">Total Leave Days</p>
                    <p className="text-lg font-semibold text-zinc-900">{report.total_leave_days || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-white border-zinc-200">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <TrendingDown className="w-5 h-5 text-red-400" />
                  <div>
                    <p className="text-xs text-zinc-600">LOP Deductions</p>
                    <p className="text-lg font-semibold text-zinc-900">{formatCurrency(report.total_lop_deductions)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-white border-zinc-200">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-400" />
                  <div>
                    <p className="text-xs text-zinc-600">Attendance Penalties</p>
                    <p className="text-lg font-semibold text-zinc-900">{formatCurrency(report.total_penalties)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Department Breakdown */}
          {report.department_breakdown && Object.keys(report.department_breakdown).length > 0 && (
            <Card className="bg-white border-zinc-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="w-5 h-5" />
                  Department Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {Object.entries(report.department_breakdown).map(([dept, data]) => (
                    <div key={dept} className="bg-zinc-50 p-4 rounded-lg">
                      <p className="text-sm text-zinc-600">{dept || 'Unassigned'}</p>
                      <p className="text-xl font-bold text-zinc-900">{formatCurrency(data.total_salary)}</p>
                      <p className="text-xs text-zinc-500">{data.employee_count} employees</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Employee Details Table */}
          {report.employee_details && report.employee_details.length > 0 && (
            <Card className="bg-white border-zinc-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Employee Details
                </CardTitle>
                <CardDescription>Individual payroll breakdown for {month}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-300">
                        <th className="text-left p-3 text-zinc-600">Employee</th>
                        <th className="text-left p-3 text-zinc-600">Department</th>
                        <th className="text-right p-3 text-zinc-600">Gross Salary</th>
                        <th className="text-right p-3 text-zinc-600">Deductions</th>
                        <th className="text-right p-3 text-zinc-600">Reimbursements</th>
                        <th className="text-right p-3 text-zinc-600">Net Salary</th>
                        <th className="text-center p-3 text-zinc-600">Present</th>
                        <th className="text-center p-3 text-zinc-600">Leave</th>
                        <th className="text-center p-3 text-zinc-600">LOP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.employee_details.map((emp, idx) => (
                        <tr key={idx} className="border-b border-zinc-200 hover:bg-zinc-50/50">
                          <td className="p-3">
                            <p className="text-zinc-800 font-medium">{emp.name}</p>
                            <p className="text-xs text-zinc-500">{emp.employee_code}</p>
                          </td>
                          <td className="p-3 text-zinc-600">{emp.department || '-'}</td>
                          <td className="p-3 text-right text-zinc-800">{formatCurrency(emp.gross_salary)}</td>
                          <td className="p-3 text-right text-red-400">{formatCurrency(emp.total_deductions)}</td>
                          <td className="p-3 text-right text-green-400">{formatCurrency(emp.reimbursements)}</td>
                          <td className="p-3 text-right text-zinc-900 font-medium">{formatCurrency(emp.net_salary)}</td>
                          <td className="p-3 text-center text-green-400">{emp.present_days}</td>
                          <td className="p-3 text-center text-yellow-400">{emp.leave_days}</td>
                          <td className="p-3 text-center text-red-400">{emp.lop_days}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-zinc-50/50 font-semibold">
                        <td className="p-3 text-zinc-800" colSpan={2}>Total</td>
                        <td className="p-3 text-right text-zinc-800">{formatCurrency(report.total_gross_salary)}</td>
                        <td className="p-3 text-right text-red-400">{formatCurrency(report.total_deductions)}</td>
                        <td className="p-3 text-right text-green-400">{formatCurrency(report.total_reimbursements)}</td>
                        <td className="p-3 text-right text-zinc-900">{formatCurrency(report.total_net_salary)}</td>
                        <td className="p-3" colSpan={3}></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Month Comparison */}
          {prevReport && (
            <Card className="bg-white border-zinc-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Month-over-Month Comparison
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-300">
                        <th className="text-left p-3 text-zinc-600">Metric</th>
                        <th className="text-right p-3 text-zinc-600">Previous Month</th>
                        <th className="text-right p-3 text-zinc-600">Current Month</th>
                        <th className="text-right p-3 text-zinc-600">Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: 'Total Employees', prev: prevReport.total_employees, curr: report.total_employees },
                        { label: 'Gross Salary', prev: prevReport.total_gross_salary, curr: report.total_gross_salary, currency: true },
                        { label: 'Net Salary', prev: prevReport.total_net_salary, curr: report.total_net_salary, currency: true },
                        { label: 'Deductions', prev: prevReport.total_deductions, curr: report.total_deductions, currency: true, inverse: true },
                        { label: 'Reimbursements', prev: prevReport.total_reimbursements, curr: report.total_reimbursements, currency: true },
                        { label: 'Leave Days', prev: prevReport.total_leave_days, curr: report.total_leave_days, inverse: true },
                        { label: 'Avg Attendance %', prev: prevReport.avg_attendance_percent, curr: report.avg_attendance_percent, suffix: '%' },
                      ].map((row, idx) => (
                        <tr key={idx} className="border-b border-zinc-200">
                          <td className="p-3 text-zinc-800">{row.label}</td>
                          <td className="p-3 text-right text-zinc-600">
                            {row.currency ? formatCurrency(row.prev) : `${row.prev?.toFixed?.(1) || row.prev || 0}${row.suffix || ''}`}
                          </td>
                          <td className="p-3 text-right text-zinc-800">
                            {row.currency ? formatCurrency(row.curr) : `${row.curr?.toFixed?.(1) || row.curr || 0}${row.suffix || ''}`}
                          </td>
                          <td className={`p-3 text-right ${getChangeIndicator(row.curr, row.prev, row.inverse).color}`}>
                            {calcChange(row.curr, row.prev)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card className="bg-white border-zinc-200">
          <CardContent className="py-12 text-center">
            <FileText className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-600">No payroll data available for {month}</p>
            <p className="text-sm text-zinc-500 mt-2">Generate salary slips first to see the summary report</p>
          </CardContent>
        </Card>
      )}

      {/* Generated Reports History */}
      {generatedReports.length > 0 && (
        <Card className="bg-white border-zinc-200">
          <CardHeader>
            <CardTitle>Generated Reports</CardTitle>
            <CardDescription>Previously generated payroll summary reports</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {generatedReports.slice(0, 5).map((rpt, idx) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-zinc-50 rounded-lg">
                  <div>
                    <p className="text-zinc-800 font-medium">{rpt.month}</p>
                    <p className="text-xs text-zinc-500">Generated: {new Date(rpt.generated_at).toLocaleString()}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setMonth(rpt.month)}>
                    View
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PayrollSummaryReport;
