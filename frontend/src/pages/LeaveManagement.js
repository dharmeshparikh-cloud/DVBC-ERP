import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Clock, CheckCircle, XCircle, Calendar, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_STYLES = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200'
};

const LeaveManagement = () => {
  const { user } = useContext(AuthContext);
  const [myRequests, setMyRequests] = useState([]);
  const [allRequests, setAllRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('my');

  const isHR = ['admin', 'hr_manager', 'hr_executive'].includes(user?.role);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const promises = [axios.get(`${API}/leave-requests`)];
      if (isHR) promises.push(axios.get(`${API}/leave-requests/all`));
      const results = await Promise.all(promises);
      setMyRequests(results[0].data);
      if (results[1]) setAllRequests(results[1].data);
    } catch (error) {
      toast.error('Failed to fetch leave data');
    } finally {
      setLoading(false);
    }
  };

  const displayRequests = activeTab === 'all' ? allRequests : myRequests;
  const pendingCount = myRequests.filter(r => r.status === 'pending').length;
  const approvedCount = myRequests.filter(r => r.status === 'approved').length;

  return (
    <div data-testid="leave-management-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Leave Management</h1>
          <p className="text-zinc-500">Review and approve leave requests from employees</p>
        </div>
      </div>
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <Clock className="w-6 h-6 text-yellow-500" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Pending</div>
              <div className="text-2xl font-semibold text-zinc-950" data-testid="leave-pending">{pendingCount}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <CheckCircle className="w-6 h-6 text-emerald-500" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Approved</div>
              <div className="text-2xl font-semibold text-zinc-950">{approvedCount}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <XCircle className="w-6 h-6 text-red-400" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Rejected</div>
              <div className="text-2xl font-semibold text-zinc-950">{myRequests.filter(r => r.status === 'rejected').length}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      {isHR && (
        <div className="flex gap-1 mb-6 border-b border-zinc-200">
          <button onClick={() => setActiveTab('my')} data-testid="tab-my-leaves"
            className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'my' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500 hover:text-zinc-700'}`}>
            My Requests ({myRequests.length})
          </button>
          <button onClick={() => setActiveTab('all')} data-testid="tab-all-leaves"
            className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'all' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500 hover:text-zinc-700'}`}>
            All Requests ({allRequests.length})
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : displayRequests.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <Calendar className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No leave requests found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50">
              <tr>
                {activeTab === 'all' && <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Employee</th>}
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">From</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">To</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Days</th>
                <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Reason</th>
                <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {displayRequests.filter(req => req.id).map(req => (
                <tr key={req.id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`leave-row-${req.id}`}>
                  {activeTab === 'all' && <td className="px-4 py-3 font-medium text-zinc-950">{req.employee_name}</td>}
                  <td className="px-4 py-3 text-zinc-700">{req.leave_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                  <td className="px-4 py-3 text-zinc-700">{req.start_date ? (isNaN(new Date(req.start_date).getTime()) ? req.start_date : format(new Date(req.start_date), 'MMM dd, yyyy')) : '-'}</td>
                  <td className="px-4 py-3 text-zinc-700">{req.end_date ? (isNaN(new Date(req.end_date).getTime()) ? req.end_date : format(new Date(req.end_date), 'MMM dd, yyyy')) : '-'}</td>
                  <td className="px-4 py-3 text-center font-medium text-zinc-950">{req.days}</td>
                  <td className="px-4 py-3 text-zinc-600 max-w-[200px] truncate">{req.reason}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-1 rounded-sm border ${STATUS_STYLES[req.status] || STATUS_STYLES.pending}`}>
                      {req.status?.charAt(0).toUpperCase() + req.status?.slice(1)}
                    </span>
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

export default LeaveManagement;
