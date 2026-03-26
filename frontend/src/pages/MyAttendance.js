import React, { useState, useContext, useMemo } from 'react';
import axios from 'axios';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  CheckCircle, XCircle, Clock, CalendarDays, Home, Coffee, MapPin,
  Building2, LogIn, Download, AlertTriangle, ChevronDown, ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';
import PageHeader from '../components/ui/page-header';
import QuickCheckInModal from '../components/QuickCheckInModal';
import MyWorkspaceNav from '../components/MyWorkspaceNav';

const STATUS_STYLES = {
  present: { label: 'Present', color: 'bg-emerald-100 text-emerald-700' },
  absent: { label: 'Absent', color: 'bg-red-100 text-red-700' },
  half_day: { label: 'Half Day', color: 'bg-yellow-100 text-yellow-700' },
  work_from_home: { label: 'WFH', color: 'bg-blue-100 text-blue-700' },
  on_leave: { label: 'On Leave', color: 'bg-purple-100 text-purple-700' },
  holiday: { label: 'Holiday', color: 'bg-zinc-100 text-zinc-700' }
};

const LEAVE_TYPE_MAP = {
  casual_leave: 'CL',
  sick_leave: 'SL',
  earned_leave: 'EL',
  loss_of_pay: 'LOP',
  lop: 'LOP'
};

const formatDateDDMMYYYY = (dateStr) => {
  if (!dateStr) return '-';
  const parts = dateStr.split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return dateStr;
};

const formatTime = (timeStr) => {
  if (!timeStr) return '-';
  try {
    return new Date(timeStr).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch { return '-'; }
};

const MyAttendance = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [showSummary, setShowSummary] = useState(true);
  const queryClient = useQueryClient();

  const { data, isLoading: loading, refetch: refetchAttendance } = useQuery({
    queryKey: ['my', 'attendance', month],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/my/attendance?month=${month}`);
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });

  const today = new Date().toISOString().split('T')[0];
  const records = Array.isArray(data) ? data : data?.records || [];
  const todayRecord = records.find(r => r.date === today);
  const todayCheckedIn = !!todayRecord?.check_in_time;
  const todayCheckedOut = !!todayRecord?.check_out_time;
  const s = data?.summary || {};

  // Calculate footer totals
  const totals = useMemo(() => {
    let totalHours = 0;
    let totalOvertime = 0;
    let lateCount = 0;
    records.forEach(r => {
      totalHours += (r.working_hours || 0);
      totalOvertime += (r.overtime_hours || 0);
      if (r.is_late) lateCount++;
    });
    return { totalHours: totalHours.toFixed(1), totalOvertime: totalOvertime.toFixed(1), lateCount };
  }, [records]);

  const shiftConfig = data?.shift_config || {};

  // CSV download
  const downloadCSV = () => {
    if (!records.length) { toast.error('No records to export'); return; }
    const headers = ['Date', 'Status', 'Location', 'Address', 'Leave Type', 'Check In', 'Check Out', 'Hours', 'Overtime', 'Late', 'Late Minutes'];
    const rows = records.map(r => {
      const ci = r.check_in_time ? new Date(r.check_in_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '';
      const co = r.check_out_time ? new Date(r.check_out_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '';
      const loc = r.work_location === 'in_office' ? 'Office' : r.work_location === 'onsite' ? 'On-Site' : r.work_location === 'wfh' ? 'WFH' : '';
      return [
        formatDateDDMMYYYY(r.date),
        STATUS_STYLES[r.status]?.label || r.status || '',
        loc,
        (r.location_address || '').replace(/,/g, ';'),
        LEAVE_TYPE_MAP[r.leave_type] || '',
        ci, co,
        r.working_hours ? r.working_hours.toFixed(1) : '',
        r.overtime_hours ? r.overtime_hours.toFixed(1) : '0',
        r.is_late ? 'Yes' : 'No',
        r.late_minutes || ''
      ];
    });
    // Footer
    rows.push(['', '', '', '', '', '', 'TOTAL', totals.totalHours, totals.totalOvertime, `Late: ${totals.lateCount}`, '']);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance_${month}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  return (
    <div data-testid="my-attendance-page">
      <MyWorkspaceNav />
      <PageHeader
        title="My Attendance"
        subtitle={`${data?.employee?.name || ''} ${data?.employee?.employee_id ? `(${data.employee.employee_id})` : ''}`}
        onRefresh={() => refetchAttendance()}
        loading={loading}
        actions={
          <>
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                todayCheckedIn
                  ? todayCheckedOut
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-blue-100 text-blue-700'
                  : 'bg-zinc-100 text-zinc-500'
              }`}
            >
              {todayCheckedIn ? (
                todayCheckedOut ? (
                  <><CheckCircle className="w-4 h-4" /> <span className="text-sm font-medium">Completed</span></>
                ) : (
                  <><Clock className="w-4 h-4" /> <span className="text-sm font-medium">Checked In</span></>
                )
              ) : (
                <><Clock className="w-4 h-4" /> <span className="text-sm">Not checked in</span></>
              )}
            </div>
            <Button onClick={() => setShowQuickCheckIn(true)} className="bg-emerald-600 hover:bg-emerald-700" data-testid="quick-checkin-btn">
              <LogIn className="w-4 h-4 mr-2" />
              {todayCheckedIn ? (todayCheckedOut ? 'Re-Check In' : 'Check Out') : 'Quick Check-in'}
            </Button>
          </>
        }
      />

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <CalendarDays className="w-4 h-4 text-zinc-500" />
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200 w-44" data-testid="my-att-month" />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowSummary(!showSummary)} className="text-xs" data-testid="toggle-summary">
            {showSummary ? <ChevronUp className="w-3 h-3 mr-1" /> : <ChevronDown className="w-3 h-3 mr-1" />}
            {showSummary ? 'Hide Stats' : 'Show Stats'}
          </Button>
          <Button variant="outline" size="sm" onClick={downloadCSV} className="text-xs" data-testid="download-csv-btn">
            <Download className="w-3 h-3 mr-1" /> CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {showSummary && (
        <div className="space-y-3 mb-6">
          {/* Shift info bar */}
          {shiftConfig.core_hours_start && (
            <div className="flex items-center gap-4 text-xs text-zinc-500 bg-zinc-50 border border-zinc-200 rounded-sm px-3 py-2" data-testid="shift-config-bar">
              <span>Shift: <span className="font-medium text-zinc-700">{shiftConfig.core_hours_start} - {shiftConfig.core_hours_end}</span></span>
              <span>Standard: <span className="font-medium text-zinc-700">{shiftConfig.standard_work_hours}h</span></span>
              <span>OT after: <span className="font-medium text-zinc-700">{shiftConfig.standard_work_hours}h</span></span>
              <span>Grace: <span className="font-medium text-zinc-700">{shiftConfig.grace_period_minutes || 30}min</span></span>
            </div>
          )}
          <div className="grid grid-cols-8 gap-2">
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                <div><div className="text-[10px] text-zinc-500">Present</div><div className="text-lg font-semibold text-zinc-950" data-testid="my-present">{s.present || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-400" />
                <div><div className="text-[10px] text-zinc-500">Absent</div><div className="text-lg font-semibold text-zinc-950">{s.absent || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-yellow-500" />
                <div><div className="text-[10px] text-zinc-500">Half Day</div><div className="text-lg font-semibold text-zinc-950">{s.half_day || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <Home className="w-4 h-4 text-blue-500" />
                <div><div className="text-[10px] text-zinc-500">WFH</div><div className="text-lg font-semibold text-zinc-950">{s.wfh || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <Coffee className="w-4 h-4 text-purple-500" />
                <div><div className="text-[10px] text-zinc-500">Leave</div><div className="text-lg font-semibold text-zinc-950">{s.on_leave || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-500" />
                <div><div className="text-[10px] text-zinc-500">Late</div><div className="text-lg font-semibold text-zinc-950">{s.late_count || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-500" />
                <div><div className="text-[10px] text-zinc-500">Total Hrs</div><div className="text-lg font-semibold text-zinc-950">{s.total_hours || 0}</div></div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm border-blue-200 bg-blue-50/30">
              <CardContent className="p-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-600" />
                <div><div className="text-[10px] text-blue-600">Overtime</div><div className="text-lg font-semibold text-blue-700">{s.total_overtime || 0}h</div></div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : !records?.length ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <CalendarDays className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No attendance records for this month</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-x-auto">
          <table className="w-full text-sm" data-testid="attendance-table">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Date</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Location</th>
                <th className="text-left px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Address</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Leave Type</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Check In</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Check Out</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Hours</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">OT</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Late</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const st = STATUS_STYLES[r?.status] || STATUS_STYLES.present;
                const hours = r.working_hours ? r.working_hours.toFixed(1) : '-';
                return (
                  <tr key={r?.id || i} className={`border-t border-zinc-100 hover:bg-zinc-50 ${r?.is_late ? 'bg-orange-50/40' : ''}`} data-testid={`att-row-${i}`}>
                    <td className="px-3 py-2.5 text-zinc-700 font-medium whitespace-nowrap">{formatDateDDMMYYYY(r?.date)}</td>
                    <td className="px-3 py-2.5 text-center"><span className={`text-xs px-2 py-0.5 rounded-sm ${st.color}`}>{st.label}</span></td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.work_location ? (
                        <span className="flex items-center justify-center gap-1 text-xs">
                          {r.work_location === 'in_office' && <><Building2 className="w-3 h-3 text-blue-600" /><span className="text-blue-700">Office</span></>}
                          {r.work_location === 'onsite' && <><MapPin className="w-3 h-3 text-emerald-600" /><span className="text-emerald-700">On-Site</span></>}
                          {r.work_location === 'wfh' && <><Home className="w-3 h-3 text-amber-600" /><span className="text-amber-700">WFH</span></>}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-left text-xs text-zinc-600 max-w-[180px]" data-testid={`att-address-${i}`}>
                      {r?.location_address ? (
                        <span className="flex items-start gap-1" title={r.location_address}>
                          <MapPin className="w-3 h-3 text-zinc-400 mt-0.5 flex-shrink-0" />
                          <span className="truncate">{r.location_address}</span>
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.leave_type ? (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-medium">
                          {LEAVE_TYPE_MAP[r.leave_type] || r.leave_type}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center text-zinc-600 whitespace-nowrap">{formatTime(r?.check_in_time)}</td>
                    <td className="px-3 py-2.5 text-center text-zinc-600 whitespace-nowrap">{formatTime(r?.check_out_time)}</td>
                    <td className="px-3 py-2.5 text-center text-zinc-700 font-medium">{hours !== '-' ? `${hours}h` : '-'}</td>
                    <td className="px-3 py-2.5 text-center">
                      {r.overtime_hours && r.overtime_hours > 0 ? (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">{r.overtime_hours.toFixed(1)}h</span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.is_late ? (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium" title={`Late by ${r.late_minutes || 0} min`}>
                          {r.late_minutes ? `${r.late_minutes}m` : 'Late'}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {/* Footer with totals */}
            <tfoot className="bg-zinc-100 border-t-2 border-zinc-300">
              <tr>
                <td className="px-3 py-2.5 text-xs font-bold text-zinc-700 uppercase">Total</td>
                <td className="px-3 py-2.5 text-center text-xs font-medium text-zinc-600">{records.length} days</td>
                <td className="px-3 py-2.5" />
                <td className="px-3 py-2.5" />
                <td className="px-3 py-2.5" />
                <td className="px-3 py-2.5" />
                <td className="px-3 py-2.5" />
                <td className="px-3 py-2.5 text-center text-xs font-bold text-zinc-700">{totals.totalHours}h</td>
                <td className="px-3 py-2.5 text-center text-xs font-bold text-blue-700">{parseFloat(totals.totalOvertime) > 0 ? `${totals.totalOvertime}h` : '-'}</td>
                <td className="px-3 py-2.5 text-center">
                  {totals.lateCount > 0 && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">{totals.lateCount}x</span>
                  )}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <QuickCheckInModal
        isOpen={showQuickCheckIn}
        onClose={() => {
          setShowQuickCheckIn(false);
          queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] });
        }}
        user={user}
      />
    </div>
  );
};

export default MyAttendance;
