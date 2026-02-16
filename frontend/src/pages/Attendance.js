import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Upload, CheckCircle, XCircle, Clock, CalendarDays, Building2, MapPin, Home } from 'lucide-react';
import { toast } from 'sonner';

const STATUSES = [
  { value: 'present', label: 'Present', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'absent', label: 'Absent', color: 'bg-red-100 text-red-700' },
  { value: 'half_day', label: 'Half Day', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'work_from_home', label: 'WFH', color: 'bg-blue-100 text-blue-700' },
  { value: 'on_leave', label: 'On Leave', color: 'bg-purple-100 text-purple-700' },
  { value: 'holiday', label: 'Holiday', color: 'bg-zinc-100 text-zinc-700' }
];

const WORK_LOCATIONS = [
  { value: 'in_office', label: 'In Office', icon: '🏢', color: 'bg-blue-100 text-blue-700' },
  { value: 'onsite', label: 'On-Site (Client Location)', icon: '📍', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'wfh', label: 'Work from Home', icon: '🏠', color: 'bg-amber-100 text-amber-700' }
];

const Attendance = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [summary, setSummary] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [formData, setFormData] = useState({ employee_id: '', date: '', status: 'present', work_location: 'in_office', remarks: '' });
  const [uploadText, setUploadText] = useState('');

  const isHR = ['admin', 'hr_manager', 'hr_executive'].includes(user?.role);

  useEffect(() => { fetchData(); }, [month]);

  const fetchData = async () => {
    try {
      const [empRes, summaryRes, recordsRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/attendance/summary?month=${month}`),
        axios.get(`${API}/attendance?month=${month}`)
      ]);
      setEmployees(empRes.data);
      setSummary(summaryRes.data);
      setRecords(recordsRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/attendance`, formData);
      toast.success('Attendance recorded');
      setDialogOpen(false);
      setFormData({ employee_id: '', date: '', status: 'present', work_location: 'in_office', remarks: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record attendance');
    }
  };

  const handleBulkUpload = async () => {
    try {
      const lines = uploadText.trim().split('\n');
      const records = lines.slice(1).map(line => {
        const cols = line.split(',').map(c => c.trim());
        return { employee_id: cols[0], date: cols[1], status: cols[2] || 'present', remarks: cols[3] || '' };
      }).filter(r => r.employee_id && r.date);
      if (records.length === 0) { toast.error('No valid records found'); return; }
      const res = await axios.post(`${API}/attendance/bulk`, records);
      toast.success(`${res.data.created} created, ${res.data.updated} updated`);
      setUploadDialogOpen(false);
      setUploadText('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    }
  };

  const getStatusBadge = (status) => {
    const s = STATUSES.find(st => st.value === status);
    return s ? s.color : 'bg-zinc-100 text-zinc-700';
  };

  const totalPresent = summary.reduce((s, r) => s + r.present, 0);
  const totalAbsent = summary.reduce((s, r) => s + r.absent, 0);

  return (
    <div data-testid="attendance-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Attendance</h1>
          <p className="text-zinc-500">Track employee attendance with manual entry or Excel upload</p>
        </div>
        {isHR && (
          <div className="flex gap-2">
            <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-sm" data-testid="upload-attendance-btn">
                  <Upload className="w-4 h-4 mr-2" /> Bulk Upload
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Bulk Upload</DialogTitle>
                  <DialogDescription className="text-zinc-500">Paste CSV data: employee_id, date (YYYY-MM-DD), status, remarks</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="p-2 bg-zinc-50 rounded-sm border border-zinc-200 text-xs font-mono text-zinc-600">
                    employee_id,date,status,remarks<br/>
                    EMP001,{month}-01,present,<br/>
                    EMP002,{month}-01,absent,Sick
                  </div>
                  <textarea value={uploadText} onChange={(e) => setUploadText(e.target.value)}
                    rows={8} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm font-mono"
                    placeholder="Paste CSV data here..." data-testid="upload-csv-input" />
                  <Button onClick={handleBulkUpload} className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="process-upload-btn">
                    Process Upload
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="add-attendance-btn">
                  <Plus className="w-4 h-4 mr-2" /> Mark Attendance
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Mark Attendance</DialogTitle>
                  <DialogDescription className="text-zinc-500">Record attendance for an employee</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Employee</Label>
                    <select value={formData.employee_id} onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="att-employee-select">
                      <option value="">Select employee</option>
                      {employees.map(e => <option key={e.id} value={e.id}>{e.employee_id} - {e.first_name} {e.last_name}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Date</Label>
                      <Input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                        required className="rounded-sm border-zinc-200" data-testid="att-date" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Status</Label>
                      <select value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                        className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="att-status">
                        {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                      </select>
                    </div>
                  </div>
                  {/* Work Location - only show when status is present or half_day */}
                  {['present', 'half_day'].includes(formData.status) && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Work Location</Label>
                      <div className="grid grid-cols-3 gap-2">
                        {WORK_LOCATIONS.map(loc => (
                          <button
                            key={loc.value}
                            type="button"
                            onClick={() => setFormData({ ...formData, work_location: loc.value })}
                            className={`flex flex-col items-center gap-1 p-3 rounded-md border transition-all ${
                              formData.work_location === loc.value 
                                ? 'border-emerald-500 bg-emerald-50 ring-2 ring-emerald-200' 
                                : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                            }`}
                            data-testid={`att-location-${loc.value}`}
                          >
                            {loc.value === 'in_office' && <Building2 className="w-5 h-5 text-blue-600" />}
                            {loc.value === 'onsite' && <MapPin className="w-5 h-5 text-emerald-600" />}
                            {loc.value === 'wfh' && <Home className="w-5 h-5 text-amber-600" />}
                            <span className="text-xs font-medium text-zinc-700">{loc.label.split(' ')[0]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Remarks</Label>
                    <Input value={formData.remarks} onChange={(e) => setFormData({ ...formData, remarks: e.target.value })}
                      className="rounded-sm border-zinc-200" placeholder="Optional" />
                  </div>
                  <Button type="submit" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="submit-attendance">
                    Save Attendance
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Month picker + Stats */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <CalendarDays className="w-4 h-4 text-zinc-500" />
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
            className="rounded-sm border-zinc-200 w-44" data-testid="month-picker" />
        </div>
        <Card className="border-zinc-200 shadow-none rounded-sm flex-1">
          <CardContent className="p-3 flex items-center gap-6">
            <div className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-500" /><span className="text-sm text-zinc-700">Present: <strong>{totalPresent}</strong></span></div>
            <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-red-400" /><span className="text-sm text-zinc-700">Absent: <strong>{totalAbsent}</strong></span></div>
            <div className="flex items-center gap-2"><Clock className="w-4 h-4 text-yellow-500" /><span className="text-sm text-zinc-700">Records: <strong>{records.length}</strong></span></div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-zinc-200">
        <button onClick={() => setActiveTab('summary')} data-testid="tab-att-summary"
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'summary' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>Summary</button>
        <button onClick={() => setActiveTab('records')} data-testid="tab-att-records"
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'records' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>Daily Records</button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : activeTab === 'summary' ? (
        summary.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <CalendarDays className="w-10 h-10 text-zinc-300 mb-3" />
              <p className="text-zinc-500">No attendance data for this month</p>
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
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Present</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Absent</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Half Day</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">WFH</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Leave</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {summary.map(row => (
                  <tr key={row.employee_id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`att-summary-${row.employee_id}`}>
                    <td className="px-4 py-3 text-zinc-600 font-mono text-xs">{row.emp_code}</td>
                    <td className="px-4 py-3 font-medium text-zinc-950">{row.name}</td>
                    <td className="px-4 py-3 text-zinc-600">{row.department || '-'}</td>
                    <td className="px-4 py-3 text-center text-emerald-700 font-medium">{row.present}</td>
                    <td className="px-4 py-3 text-center text-red-600 font-medium">{row.absent}</td>
                    <td className="px-4 py-3 text-center text-yellow-600">{row.half_day}</td>
                    <td className="px-4 py-3 text-center text-blue-600">{row.wfh}</td>
                    <td className="px-4 py-3 text-center text-purple-600">{row.on_leave}</td>
                    <td className="px-4 py-3 text-center font-medium text-zinc-950">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        records.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <p className="text-zinc-500">No daily records for this month</p>
            </CardContent>
          </Card>
        ) : (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Employee ID</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Remarks</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r, idx) => (
                  <tr key={r.id || idx} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 text-zinc-700">{r.date}</td>
                    <td className="px-4 py-3 text-zinc-700 font-mono text-xs">{r.employee_id}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-1 rounded-sm ${getStatusBadge(r.status)}`}>
                        {STATUSES.find(s => s.value === r.status)?.label || r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">{r.remarks || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
};

export default Attendance;
