import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CheckCircle, XCircle, Clock, CalendarDays, Home, Coffee, MapPin, Building2, LogIn } from 'lucide-react';
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

const MyAttendance = () => {
  const { user } = useContext(AuthContext);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const queryClient = useQueryClient();

  // React Query: My Attendance
  const { data, isLoading: loading, refetch: refetchAttendance } = useQuery({
    queryKey: ['my', 'attendance', month],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/my/attendance?month=${month}`);
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Check today's status
  const today = new Date().toISOString().split('T')[0];
  const records = Array.isArray(data) ? data : data?.records || [];
  const todayRecord = records.find(r => r.date === today);
  const todayCheckedIn = !!todayRecord?.check_in_time || !!todayRecord?.check_in;
  const todayCheckedOut = !!todayRecord?.check_out_time || !!todayRecord?.check_out;

  const s = data?.summary || {};
  const todayFormatted = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

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
                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' 
                    : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400'
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
            {!todayCheckedOut && (
              <Button onClick={() => setShowQuickCheckIn(true)} className="bg-emerald-600 hover:bg-emerald-700" data-testid="quick-checkin-btn">
                <LogIn className="w-4 h-4 mr-2" />
                {todayCheckedIn ? 'Check Out' : 'Quick Check-in'}
              </Button>
            )}
          </>
        }
      />

      <div className="flex items-center gap-4 mb-6">
        <CalendarDays className="w-4 h-4 text-zinc-500" />
        <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200 dark:border-zinc-700 w-44" data-testid="my-att-month" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <div><div className="text-xs text-zinc-500 dark:text-zinc-400">Present</div><div className="text-xl font-semibold text-zinc-950 dark:text-zinc-100" data-testid="my-present">{s.present || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            <div><div className="text-xs text-zinc-500 dark:text-zinc-400">Absent</div><div className="text-xl font-semibold text-zinc-950 dark:text-zinc-100">{s.absent || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-500" />
            <div><div className="text-xs text-zinc-500 dark:text-zinc-400">Half Day</div><div className="text-xl font-semibold text-zinc-950 dark:text-zinc-100">{s.half_day || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Home className="w-5 h-5 text-blue-500" />
            <div><div className="text-xs text-zinc-500 dark:text-zinc-400">WFH</div><div className="text-xl font-semibold text-zinc-950 dark:text-zinc-100">{s.wfh || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Coffee className="w-5 h-5 text-purple-500" />
            <div><div className="text-xs text-zinc-500 dark:text-zinc-400">Leave</div><div className="text-xl font-semibold text-zinc-950 dark:text-zinc-100">{s.on_leave || 0}</div></div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500 dark:text-zinc-400">Loading...</div></div>
      ) : !records?.length ? (
        <Card className="border-zinc-200 dark:border-zinc-700 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <CalendarDays className="w-10 h-10 text-zinc-300 dark:text-zinc-600 mb-3" />
            <p className="text-zinc-500 dark:text-zinc-400">No attendance records for this month</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 dark:border-zinc-700 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 dark:bg-zinc-800">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Date</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Status</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Location</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Address</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Check In</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Check Out</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 font-medium">Hours</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const st = STATUS_STYLES[r?.status] || STATUS_STYLES.present;
                const checkInTime = r?.check_in_time || r?.check_in;
                const checkOutTime = r?.check_out_time || r?.check_out;
                const checkIn = checkInTime ? new Date(checkInTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '-';
                const checkOut = checkOutTime ? new Date(checkOutTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '-';
                return (
                  <tr key={r?.id || i} className="border-t border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                    <td className="px-4 py-3 text-zinc-700 dark:text-zinc-300 font-medium">{r?.date}</td>
                    <td className="px-4 py-3 text-center"><span className={`text-xs px-2 py-1 rounded-sm ${st.color}`}>{st.label}</span></td>
                    <td className="px-4 py-3 text-center">
                      {r?.work_location ? (
                        <span className="flex items-center justify-center gap-1 text-xs">
                          {r.work_location === 'in_office' && <><Building2 className="w-3 h-3 text-blue-600" /><span className="text-blue-700 dark:text-blue-400">Office</span></>}
                          {r.work_location === 'onsite' && <><MapPin className="w-3 h-3 text-emerald-600" /><span className="text-emerald-700 dark:text-emerald-400">On-Site</span></>}
                          {r.work_location === 'wfh' && <><Home className="w-3 h-3 text-amber-600" /><span className="text-amber-700 dark:text-amber-400">WFH</span></>}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-left text-xs text-zinc-600 dark:text-zinc-400 max-w-[200px]" data-testid={`att-address-${i}`}>
                      {r?.location_address ? (
                        <span className="flex items-start gap-1" title={r.location_address}>
                          <MapPin className="w-3 h-3 text-zinc-400 mt-0.5 flex-shrink-0" />
                          <span className="truncate">{r.location_address}</span>
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-4 py-3 text-center text-zinc-600 dark:text-zinc-400">{checkIn}</td>
                    <td className="px-4 py-3 text-center text-zinc-600 dark:text-zinc-400">{checkOut}</td>
                    <td className="px-4 py-3 text-center text-zinc-600 dark:text-zinc-400">{r.work_hours ? `${r.work_hours.toFixed(1)}h` : '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Quick Check-in Modal - Single UI for all attendance */}
      <QuickCheckInModal 
        isOpen={showQuickCheckIn} 
        onClose={() => {
          setShowQuickCheckIn(false);
          queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] }); // Refresh data after check-in/out
        }} 
        user={user} 
      />
    </div>
  );
};

export default MyAttendance;
