import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Calendar, CheckCircle, XCircle, Clock, Undo2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const LEAVE_TYPES = [
  { value: 'casual_leave', label: 'Casual Leave', key: 'casual' },
  { value: 'sick_leave', label: 'Sick Leave', key: 'sick' },
  { value: 'earned_leave', label: 'Earned Leave', key: 'earned' }
];

const STATUS_STYLES = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  withdrawn: 'bg-zinc-100 text-zinc-500 border-zinc-200'
};

const MyLeaves = () => {
  const [requests, setRequests] = useState([]);
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [withdrawingId, setWithdrawingId] = useState(null);
  const [formData, setFormData] = useState({ 
    leave_type: 'casual_leave', 
    start_date: '', 
    end_date: '', 
    reason: '',
    is_half_day: false,
    half_day_type: 'first_half'  // first_half or second_half
  });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [reqRes, balRes] = await Promise.all([
        axios.get(`${API}/leave-requests`),
        axios.get(`${API}/my/leave-balance`).catch(() => ({ data: null }))
      ]);
      setRequests(reqRes.data);
      setBalance(balRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/leave-requests`, {
        ...formData,
        start_date: new Date(formData.start_date).toISOString(),
        end_date: formData.is_half_day ? new Date(formData.start_date).toISOString() : new Date(formData.end_date).toISOString()
      });
      toast.success('Leave request submitted for approval');
      setDialogOpen(false);
      setFormData({ leave_type: 'casual_leave', start_date: '', end_date: '', reason: '', is_half_day: false, half_day_type: 'first_half' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleWithdraw = async (leaveId) => {
    if (!window.confirm('Are you sure you want to withdraw this leave request?')) return;
    
    setWithdrawingId(leaveId);
    try {
      await axios.post(`${API}/leave-requests/${leaveId}/withdraw`);
      toast.success('Leave request withdrawn successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to withdraw leave request');
    } finally {
      setWithdrawingId(null);
    }
  };

  const days = formData.is_half_day 
    ? 0.5 
    : (formData.start_date && formData.end_date
      ? Math.max(1, Math.ceil((new Date(formData.end_date) - new Date(formData.start_date)) / 86400000) + 1)
      : 0);

  return (
    <div data-testid="my-leaves-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">My Leaves</h1>
          <p className="text-zinc-500">Apply for leave, track status, and view balance</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="apply-leave-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" /> Apply Leave
            </Button>
          </DialogTrigger>
          <DialogContent className="border-zinc-200 rounded-sm max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Apply for Leave</DialogTitle>
              <DialogDescription className="text-zinc-500">Routed: You → Reporting Manager → HR Manager</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Leave Type</Label>
                <select value={formData.leave_type} onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="leave-type">
                  {LEAVE_TYPES.map(t => {
                    const b = balance?.[t.key];
                    return <option key={t.value} value={t.value}>{t.label} {b ? `(${b.available} available)` : ''}</option>;
                  })}
                </select>
              </div>
              
              {/* Half Day Option */}
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_half_day}
                    onChange={(e) => setFormData({ ...formData, is_half_day: e.target.checked, end_date: e.target.checked ? formData.start_date : formData.end_date })}
                    className="w-4 h-4 rounded border-zinc-300"
                    data-testid="half-day-checkbox"
                  />
                  <span className="text-sm text-zinc-700">Half Day Leave</span>
                </label>
                
                {formData.is_half_day && (
                  <select
                    value={formData.half_day_type}
                    onChange={(e) => setFormData({ ...formData, half_day_type: e.target.value })}
                    className="h-8 px-2 rounded-sm border border-zinc-200 text-sm"
                    data-testid="half-day-type"
                  >
                    <option value="first_half">First Half (Morning)</option>
                    <option value="second_half">Second Half (Afternoon)</option>
                  </select>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">{formData.is_half_day ? 'Date' : 'Start Date'}</Label>
                  <Input type="date" value={formData.start_date} onChange={(e) => setFormData({ ...formData, start_date: e.target.value, end_date: formData.is_half_day ? e.target.value : formData.end_date })}
                    required className="rounded-sm border-zinc-200" data-testid="leave-start" />
                </div>
                {!formData.is_half_day && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">End Date</Label>
                    <Input type="date" value={formData.end_date} onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      required className="rounded-sm border-zinc-200" data-testid="leave-end" />
                  </div>
                )}
              </div>
              {days > 0 && <div className="text-sm text-zinc-600 bg-zinc-50 rounded-sm p-2 border border-zinc-200">Duration: <strong>{days} day(s)</strong>{formData.is_half_day && ` (${formData.half_day_type === 'first_half' ? 'Morning' : 'Afternoon'})`}</div>}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Reason</Label>
                <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  required rows={3} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="leave-reason" />
              </div>
              <div className="p-3 bg-zinc-50 rounded-sm border border-zinc-200 text-xs text-zinc-500">
                Approval: <span className="font-medium text-zinc-700">Reporting Manager → HR Manager</span>
              </div>
              <Button type="submit" data-testid="submit-leave" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Submit</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Leave Balance */}
      {balance && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {LEAVE_TYPES.map(t => {
            const b = balance[t.key] || {};
            return (
              <Card key={t.value} className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="p-4">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">{t.label}</div>
                  <div className="flex items-end justify-between">
                    <div>
                      <span className="text-2xl font-semibold text-zinc-950" data-testid={`balance-${t.key}`}>{b.available || 0}</span>
                      <span className="text-sm text-zinc-400 ml-1">available</span>
                    </div>
                    <div className="text-xs text-zinc-500">
                      {b.used || 0} used / {b.total || 0} total
                    </div>
                  </div>
                  <div className="mt-2 w-full bg-zinc-200 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${b.available > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                      style={{ width: `${b.total ? ((b.available / b.total) * 100) : 0}%` }} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Leave Requests */}
      <div className="mb-3 text-sm font-medium text-zinc-700">My Leave Requests</div>
      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : requests.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <Calendar className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No leave requests yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50">
              <tr>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">From</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">To</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Days</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Reason</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <tr key={req.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`leave-req-${req.id}`}>
                  <td className="px-4 py-3 text-zinc-700">{req.leave_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                  <td className="px-4 py-3 text-zinc-700">{req.start_date ? format(new Date(req.start_date), 'MMM dd, yyyy') : '-'}</td>
                  <td className="px-4 py-3 text-zinc-700">{req.end_date ? format(new Date(req.end_date), 'MMM dd, yyyy') : '-'}</td>
                  <td className="px-4 py-3 text-center font-medium">{req.days}</td>
                  <td className="px-4 py-3 text-zinc-600 max-w-[200px] truncate">{req.reason}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-1 rounded-sm border ${STATUS_STYLES[req.status] || STATUS_STYLES.pending}`}>
                      {req.status?.charAt(0).toUpperCase() + req.status?.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {req.status === 'pending' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleWithdraw(req.id)}
                        disabled={withdrawingId === req.id}
                        className="text-xs h-7 px-2 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                        data-testid={`withdraw-btn-${req.id}`}
                      >
                        <Undo2 className="w-3 h-3 mr-1" />
                        {withdrawingId === req.id ? 'Withdrawing...' : 'Withdraw'}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MyLeaves;
