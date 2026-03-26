import React, { useState, useContext, useMemo } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import {
  CheckCircle, XCircle, Clock, CalendarDays, Home, Coffee, MapPin,
  Building2, LogIn, Download, AlertTriangle, ChevronDown, ChevronUp,
  Edit2, Save, X, Filter, RotateCcw
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
  casual_leave: 'CL', sick_leave: 'SL', earned_leave: 'EL', loss_of_pay: 'LOP', lop: 'LOP'
};

const fmtDate = (dateStr) => {
  if (!dateStr) return '-';
  const p = dateStr.split('-');
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : dateStr;
};

const fmtTime = (t) => {
  if (!t) return '-';
  try {
    return new Date(t).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', hour12: true,
      timeZone: 'Asia/Kolkata'
    });
  } catch { return '-'; }
};

const MyAttendance = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [showSummary, setShowSummary] = useState(true);
  const [editingRow, setEditingRow] = useState(null);
  const [editData, setEditData] = useState({});
  const [regDialog, setRegDialog] = useState(false);
  const [regRecord, setRegRecord] = useState(null);
  const [regForm, setRegForm] = useState({ reason: '', check_in_time: '', check_out_time: '', status: '' });
  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterLocation, setFilterLocation] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const queryClient = useQueryClient();

  const isHRAdmin = ['admin', 'hr_admin', 'hr'].includes(user?.role);

  const { data, isLoading: loading, refetch: refetchAttendance } = useQuery({
    queryKey: ['my', 'attendance', month],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/my/attendance?month=${month}`);
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });

  const regularizeMutation = useMutation({
    mutationFn: async ({ recordId, data: regData }) => {
      const { data } = await axios.put(`${API}/attendance/${recordId}/regularize`, regData);
      return data;
    },
    onSuccess: () => {
      toast.success('Attendance regularized');
      setRegDialog(false);
      setRegRecord(null);
      queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] });
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed to regularize'),
  });

  const inlineEditMutation = useMutation({
    mutationFn: async ({ recordId, data: editFields }) => {
      const { data } = await axios.put(`${API}/attendance/${recordId}/regularize`, {
        ...editFields,
        reason: 'Inline edit by HR/Admin'
      });
      return data;
    },
    onSuccess: () => {
      toast.success('Updated');
      setEditingRow(null);
      queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] });
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Update failed'),
  });

  const today = new Date().toISOString().split('T')[0];
  const records = Array.isArray(data) ? data : data?.records || [];
  const todayRecord = records.find(r => r.date === today);
  const todayCheckedIn = !!todayRecord?.check_in_time;
  const todayCheckedOut = !!todayRecord?.check_out_time;
  const s = data?.summary || {};
  const shiftConfig = data?.shift_config || {};

  // Filtered records
  const filtered = useMemo(() => {
    let r = records;
    if (filterStatus) r = r.filter(x => x.status === filterStatus);
    if (filterLocation) r = r.filter(x => x.work_location === filterLocation);
    return r;
  }, [records, filterStatus, filterLocation]);

  const totals = useMemo(() => {
    let h = 0, ot = 0, late = 0;
    filtered.forEach(r => { h += (r.working_hours || 0); ot += (r.overtime_hours || 0); if (r.is_late) late++; });
    return { h: h.toFixed(1), ot: ot.toFixed(1), late };
  }, [filtered]);

  const downloadCSV = () => {
    if (!filtered.length) { toast.error('No records'); return; }
    const hdr = ['Date','Status','Location','Address','Leave Type','Check In','Check Out','Hours','OT','Late','Late Min','Regularized'];
    const rows = filtered.map(r => [
      fmtDate(r.date), STATUS_STYLES[r.status]?.label || '', r.work_location === 'in_office' ? 'Office' : r.work_location === 'onsite' ? 'On-Site' : r.work_location === 'wfh' ? 'WFH' : '',
      (r.location_address || '').replace(/,/g, ';'), LEAVE_TYPE_MAP[r.leave_type] || '',
      r.check_in_time ? fmtTime(r.check_in_time) : '', r.check_out_time ? fmtTime(r.check_out_time) : '',
      r.working_hours ? r.working_hours.toFixed(1) : '', r.overtime_hours ? r.overtime_hours.toFixed(1) : '0',
      r.is_late ? 'Yes' : 'No', r.late_minutes || '', r.regularized ? 'Yes' : 'No'
    ]);
    rows.push(['','','','','','','TOTAL', totals.h, totals.ot, `Late:${totals.late}`, '', '']);
    const csv = [hdr, ...rows].map(r => r.join(',')).join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `attendance_${month}.csv`; a.click(); toast.success('CSV downloaded');
  };

  const openRegularize = (r) => {
    setRegRecord(r);
    setRegForm({ reason: '', check_in_time: r.check_in_time || '', check_out_time: r.check_out_time || '', status: r.status || 'present' });
    setRegDialog(true);
  };

  const startInlineEdit = (r) => {
    setEditingRow(r.id);
    setEditData({ check_in_time: r.check_in_time || '', check_out_time: r.check_out_time || '', status: r.status || 'present' });
  };

  const saveInlineEdit = (recordId) => {
    inlineEditMutation.mutate({ recordId, data: editData });
  };

  return (
    <div data-testid="my-attendance-page">
      <MyWorkspaceNav />
      <PageHeader title="My Attendance" subtitle={`${data?.employee?.name || ''} ${data?.employee?.employee_id ? `(${data.employee.employee_id})` : ''}`}
        onRefresh={() => refetchAttendance()} loading={loading}
        actions={<>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${todayCheckedIn ? todayCheckedOut ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700' : 'bg-zinc-100 text-zinc-500'}`}>
            {todayCheckedIn ? (todayCheckedOut ? <><CheckCircle className="w-4 h-4" /><span className="text-sm font-medium">Completed</span></> : <><Clock className="w-4 h-4" /><span className="text-sm font-medium">Checked In</span></>) : <><Clock className="w-4 h-4" /><span className="text-sm">Not checked in</span></>}
          </div>
          <Button onClick={() => setShowQuickCheckIn(true)} className="bg-emerald-600 hover:bg-emerald-700" data-testid="quick-checkin-btn">
            <LogIn className="w-4 h-4 mr-2" />{todayCheckedIn ? (todayCheckedOut ? 'Re-Check In' : 'Check Out') : 'Quick Check-in'}
          </Button>
        </>}
      />

      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-4">
          <CalendarDays className="w-4 h-4 text-zinc-500" />
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200 w-44" data-testid="my-att-month" />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)} className="text-xs" data-testid="toggle-filters">
            <Filter className="w-3 h-3 mr-1" /> Filters
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowSummary(!showSummary)} className="text-xs" data-testid="toggle-summary">
            {showSummary ? <ChevronUp className="w-3 h-3 mr-1" /> : <ChevronDown className="w-3 h-3 mr-1" />}{showSummary ? 'Hide Stats' : 'Stats'}
          </Button>
          <Button variant="outline" size="sm" onClick={downloadCSV} className="text-xs" data-testid="download-csv-btn">
            <Download className="w-3 h-3 mr-1" /> CSV
          </Button>
        </div>
      </div>

      {/* Excel-like Filters */}
      {showFilters && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-zinc-50 border border-zinc-200 rounded-sm" data-testid="filter-bar">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="h-8 px-2 text-xs border border-zinc-200 rounded-sm bg-white">
            <option value="">All Status</option>
            {Object.entries(STATUS_STYLES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <select value={filterLocation} onChange={(e) => setFilterLocation(e.target.value)} className="h-8 px-2 text-xs border border-zinc-200 rounded-sm bg-white">
            <option value="">All Locations</option>
            <option value="in_office">Office</option>
            <option value="onsite">On-Site</option>
            <option value="wfh">WFH</option>
          </select>
          {(filterStatus || filterLocation) && (
            <Button variant="ghost" size="sm" onClick={() => { setFilterStatus(''); setFilterLocation(''); }} className="text-xs text-red-600 h-8">
              <X className="w-3 h-3 mr-1" /> Clear
            </Button>
          )}
          <span className="text-xs text-zinc-500 ml-auto">{filtered.length} of {records.length} records</span>
        </div>
      )}

      {/* Summary */}
      {showSummary && (
        <div className="space-y-3 mb-6">
          {shiftConfig.core_hours_start && (
            <div className="flex items-center gap-4 text-xs text-zinc-500 bg-zinc-50 border border-zinc-200 rounded-sm px-3 py-2" data-testid="shift-config-bar">
              <span>Shift: <span className="font-medium text-zinc-700">{shiftConfig.core_hours_start} - {shiftConfig.core_hours_end}</span></span>
              <span>Standard: <span className="font-medium text-zinc-700">{shiftConfig.standard_work_hours}h</span></span>
              <span>OT after: <span className="font-medium text-zinc-700">{shiftConfig.standard_work_hours}h</span></span>
            </div>
          )}
          <div className="grid grid-cols-8 gap-2">
            {[
              { icon: CheckCircle, color: 'emerald', label: 'Present', val: s.present },
              { icon: XCircle, color: 'red', label: 'Absent', val: s.absent },
              { icon: Clock, color: 'yellow', label: 'Half Day', val: s.half_day },
              { icon: Home, color: 'blue', label: 'WFH', val: s.wfh },
              { icon: Coffee, color: 'purple', label: 'Leave', val: s.on_leave },
              { icon: AlertTriangle, color: 'orange', label: 'Late', val: s.late_count },
              { icon: Clock, color: 'zinc', label: 'Total Hrs', val: s.total_hours },
              { icon: Clock, color: 'blue', label: 'Overtime', val: `${s.total_overtime || 0}h`, accent: true },
            ].map((c, i) => (
              <Card key={i} className={`border-zinc-200 shadow-none rounded-sm ${c.accent ? 'border-blue-200 bg-blue-50/30' : ''}`}>
                <CardContent className="p-3 flex items-center gap-2">
                  <c.icon className={`w-4 h-4 text-${c.color}-500`} />
                  <div><div className="text-[10px] text-zinc-500">{c.label}</div><div className={`text-lg font-semibold ${c.accent ? 'text-blue-700' : 'text-zinc-950'}`}>{c.val || 0}</div></div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : !filtered.length ? (
        <Card className="border-zinc-200 shadow-none rounded-sm"><CardContent className="flex flex-col items-center justify-center h-40">
          <CalendarDays className="w-10 h-10 text-zinc-300 mb-3" /><p className="text-zinc-500">{records.length ? 'No matching records' : 'No attendance records for this month'}</p>
        </CardContent></Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-x-auto">
          <table className="w-full text-sm" data-testid="attendance-table">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Date</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Location</th>
                <th className="text-left px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Address</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Leave</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Check In</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium whitespace-nowrap">Check Out</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Hours</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">OT</th>
                <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Late</th>
                {isHRAdmin && <th className="text-center px-3 py-2.5 text-xs uppercase tracking-wide text-zinc-500 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => {
                const st = STATUS_STYLES[r?.status] || STATUS_STYLES.present;
                const hrs = r.working_hours ? r.working_hours.toFixed(1) : '-';
                const isEditing = editingRow === r.id;
                return (
                  <tr key={r?.id || i} className={`border-t border-zinc-100 hover:bg-zinc-50 ${r?.is_late ? 'bg-orange-50/40' : ''} ${r?.regularized ? 'bg-blue-50/20' : ''}`} data-testid={`att-row-${i}`}>
                    <td className="px-3 py-2.5 text-zinc-700 font-medium whitespace-nowrap">
                      {fmtDate(r?.date)}
                      {r?.regularized && <span className="ml-1 text-[9px] text-blue-600 font-normal" title={`Regularized by ${r.regularized_by_name}`}>R</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {isEditing ? (
                        <select value={editData.status} onChange={(e) => setEditData({...editData, status: e.target.value})} className="h-7 px-1 text-xs border rounded-sm">
                          {Object.entries(STATUS_STYLES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                        </select>
                      ) : <span className={`text-xs px-2 py-0.5 rounded-sm ${st.color}`}>{st.label}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.work_location ? (
                        <span className="flex items-center justify-center gap-1 text-xs">
                          {r.work_location === 'in_office' && <><Building2 className="w-3 h-3 text-blue-600" /><span className="text-blue-700">Office</span></>}
                          {r.work_location === 'onsite' && <><MapPin className="w-3 h-3 text-emerald-600" /><span className="text-emerald-700">On-Site</span></>}
                          {r.work_location === 'wfh' && <><Home className="w-3 h-3 text-amber-600" /><span className="text-amber-700">WFH</span></>}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-left text-xs text-zinc-600 max-w-[150px]" data-testid={`att-address-${i}`}>
                      {r?.location_address ? <span className="flex items-start gap-1 truncate" title={r.location_address}><MapPin className="w-3 h-3 text-zinc-400 mt-0.5 flex-shrink-0" /><span className="truncate">{r.location_address}</span></span> : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.leave_type ? <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-medium">{LEAVE_TYPE_MAP[r.leave_type] || r.leave_type}</span> : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center whitespace-nowrap">
                      {isEditing ? (
                        <Input type="datetime-local" value={editData.check_in_time?.slice(0,16)} onChange={(e) => setEditData({...editData, check_in_time: e.target.value ? new Date(e.target.value).toISOString() : ''})} className="h-7 text-xs w-36" />
                      ) : <span className="text-zinc-600">{fmtTime(r?.check_in_time)}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center whitespace-nowrap">
                      {isEditing ? (
                        <Input type="datetime-local" value={editData.check_out_time?.slice(0,16)} onChange={(e) => setEditData({...editData, check_out_time: e.target.value ? new Date(e.target.value).toISOString() : ''})} className="h-7 text-xs w-36" />
                      ) : <span className="text-zinc-600">{fmtTime(r?.check_out_time)}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center text-zinc-700 font-medium">{hrs !== '-' ? `${hrs}h` : '-'}</td>
                    <td className="px-3 py-2.5 text-center">
                      {r.overtime_hours > 0 ? <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">{r.overtime_hours.toFixed(1)}h</span> : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {r?.is_late ? <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium" title={`Late by ${r.late_minutes || 0} min`}>{r.late_minutes ? `${r.late_minutes}m` : 'Late'}</span> : <span className="text-zinc-400">-</span>}
                    </td>
                    {isHRAdmin && (
                      <td className="px-3 py-2.5 text-center whitespace-nowrap">
                        {isEditing ? (
                          <div className="flex items-center gap-1 justify-center">
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-emerald-600" onClick={() => saveInlineEdit(r.id)} data-testid={`save-edit-${i}`}><Save className="w-3 h-3" /></Button>
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-red-600" onClick={() => setEditingRow(null)}><X className="w-3 h-3" /></Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 justify-center">
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-zinc-500 hover:text-blue-600" onClick={() => startInlineEdit(r)} title="Inline Edit" data-testid={`inline-edit-${i}`}><Edit2 className="w-3 h-3" /></Button>
                            <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-zinc-500 hover:text-amber-600" onClick={() => openRegularize(r)} title="Regularize" data-testid={`regularize-${i}`}><RotateCcw className="w-3 h-3" /></Button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-zinc-100 border-t-2 border-zinc-300">
              <tr>
                <td className="px-3 py-2.5 text-xs font-bold text-zinc-700 uppercase">Total</td>
                <td className="px-3 py-2.5 text-center text-xs font-medium text-zinc-600">{filtered.length} days</td>
                <td colSpan={4} />
                <td />
                <td className="px-3 py-2.5 text-center text-xs font-bold text-zinc-700">{totals.h}h</td>
                <td className="px-3 py-2.5 text-center text-xs font-bold text-blue-700">{parseFloat(totals.ot) > 0 ? `${totals.ot}h` : '-'}</td>
                <td className="px-3 py-2.5 text-center">{totals.late > 0 && <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">{totals.late}x</span>}</td>
                {isHRAdmin && <td />}
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Regularization Dialog */}
      <Dialog open={regDialog} onOpenChange={setRegDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><RotateCcw className="w-5 h-5 text-amber-600" /> Regularize Attendance</DialogTitle>
          </DialogHeader>
          {regRecord && (
            <div className="space-y-4">
              <div className="text-sm text-zinc-600 bg-zinc-50 p-3 rounded-sm">
                <strong>{fmtDate(regRecord.date)}</strong> - Current: {STATUS_STYLES[regRecord.status]?.label || regRecord.status}
                {regRecord.check_in_time && <>, In: {fmtTime(regRecord.check_in_time)}</>}
                {regRecord.check_out_time && <>, Out: {fmtTime(regRecord.check_out_time)}</>}
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">Reason *</Label>
                <Input value={regForm.reason} onChange={(e) => setRegForm({...regForm, reason: e.target.value})} placeholder="Forgot to check-in, system error, etc." data-testid="reg-reason" />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">Status</Label>
                <select value={regForm.status} onChange={(e) => setRegForm({...regForm, status: e.target.value})} className="w-full h-10 px-3 rounded-sm border border-zinc-200 text-sm">
                  {Object.entries(STATUS_STYLES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Correct Check-in</Label>
                  <Input type="datetime-local" value={regForm.check_in_time?.slice(0,16)} onChange={(e) => setRegForm({...regForm, check_in_time: e.target.value ? new Date(e.target.value).toISOString() : ''})} data-testid="reg-checkin" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Correct Check-out</Label>
                  <Input type="datetime-local" value={regForm.check_out_time?.slice(0,16)} onChange={(e) => setRegForm({...regForm, check_out_time: e.target.value ? new Date(e.target.value).toISOString() : ''})} data-testid="reg-checkout" />
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setRegDialog(false)} className="flex-1">Cancel</Button>
                <Button onClick={() => regularizeMutation.mutate({ recordId: regRecord.id, data: regForm })} disabled={!regForm.reason || regularizeMutation.isPending} className="flex-1 bg-amber-600 hover:bg-amber-700 text-white" data-testid="reg-submit">
                  {regularizeMutation.isPending ? 'Saving...' : 'Regularize'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <QuickCheckInModal isOpen={showQuickCheckIn} onClose={() => { setShowQuickCheckIn(false); queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] }); }} user={user} />
    </div>
  );
};

export default MyAttendance;
