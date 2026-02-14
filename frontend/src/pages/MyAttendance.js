import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { CheckCircle, XCircle, Clock, CalendarDays, Home, Coffee } from 'lucide-react';
import { toast } from 'sonner';

const STATUS_STYLES = {
  present: { label: 'Present', color: 'bg-emerald-100 text-emerald-700' },
  absent: { label: 'Absent', color: 'bg-red-100 text-red-700' },
  half_day: { label: 'Half Day', color: 'bg-yellow-100 text-yellow-700' },
  work_from_home: { label: 'WFH', color: 'bg-blue-100 text-blue-700' },
  on_leave: { label: 'On Leave', color: 'bg-purple-100 text-purple-700' },
  holiday: { label: 'Holiday', color: 'bg-zinc-100 text-zinc-700' }
};

const MyAttendance = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));

  useEffect(() => { fetchData(); }, [month]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/my/attendance?month=${month}`);
      setData(res.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to fetch attendance');
    } finally {
      setLoading(false);
    }
  };

  const s = data?.summary || {};

  return (
    <div data-testid="my-attendance-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">My Attendance</h1>
        <p className="text-zinc-500">{data?.employee?.name || ''} {data?.employee?.employee_id ? `(${data.employee.employee_id})` : ''}</p>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <CalendarDays className="w-4 h-4 text-zinc-500" />
        <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-sm border-zinc-200 w-44" data-testid="my-att-month" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <div><div className="text-xs text-zinc-500">Present</div><div className="text-xl font-semibold text-zinc-950" data-testid="my-present">{s.present || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            <div><div className="text-xs text-zinc-500">Absent</div><div className="text-xl font-semibold text-zinc-950">{s.absent || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-500" />
            <div><div className="text-xs text-zinc-500">Half Day</div><div className="text-xl font-semibold text-zinc-950">{s.half_day || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Home className="w-5 h-5 text-blue-500" />
            <div><div className="text-xs text-zinc-500">WFH</div><div className="text-xl font-semibold text-zinc-950">{s.wfh || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Coffee className="w-5 h-5 text-purple-500" />
            <div><div className="text-xs text-zinc-500">Leave</div><div className="text-xl font-semibold text-zinc-950">{s.on_leave || 0}</div></div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : !data?.records?.length ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <CalendarDays className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No attendance records for this month</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Date</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Remarks</th>
              </tr>
            </thead>
            <tbody>
              {data.records.map((r, i) => {
                const st = STATUS_STYLES[r.status] || STATUS_STYLES.present;
                return (
                  <tr key={r.id || i} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 text-zinc-700 font-medium">{r.date}</td>
                    <td className="px-4 py-3 text-center"><span className={`text-xs px-2 py-1 rounded-sm ${st.color}`}>{st.label}</span></td>
                    <td className="px-4 py-3 text-zinc-600">{r.remarks || '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MyAttendance;
