import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Shield, Search, Download, ChevronLeft, ChevronRight, Filter } from 'lucide-react';

const EVENT_COLORS = {
  google_login_success: 'bg-emerald-100 text-emerald-800',
  password_login_success: 'bg-emerald-100 text-emerald-800',
  google_login_failed: 'bg-red-100 text-red-800',
  password_login_failed: 'bg-red-100 text-red-800',
  google_login_rejected_domain: 'bg-orange-100 text-orange-800',
  google_login_rejected_unregistered: 'bg-orange-100 text-orange-800',
  google_login_rejected_inactive: 'bg-orange-100 text-orange-800',
  otp_generated: 'bg-blue-100 text-blue-800',
  otp_request_failed: 'bg-red-100 text-red-800',
  otp_request_rejected: 'bg-orange-100 text-orange-800',
  otp_verify_failed: 'bg-red-100 text-red-800',
  password_reset_success: 'bg-emerald-100 text-emerald-800',
  password_change_success: 'bg-emerald-100 text-emerald-800',
  password_change_failed: 'bg-red-100 text-red-800',
};

const EVENT_LABELS = {
  google_login_success: 'Google Login',
  password_login_success: 'Password Login',
  google_login_failed: 'Google Login Failed',
  password_login_failed: 'Password Login Failed',
  google_login_rejected_domain: 'Domain Rejected',
  google_login_rejected_unregistered: 'Unregistered User',
  google_login_rejected_inactive: 'Inactive Account',
  otp_generated: 'OTP Generated',
  otp_request_failed: 'OTP Request Failed',
  otp_request_rejected: 'OTP Rejected',
  otp_verify_failed: 'OTP Verify Failed',
  password_reset_success: 'Password Reset',
  password_change_success: 'Password Changed',
  password_change_failed: 'Password Change Failed',
};

const SecurityAuditLog = () => {
  const { user } = useContext(AuthContext);
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [searchEmail, setSearchEmail] = useState('');
  const [filterType, setFilterType] = useState('');
  const [loading, setLoading] = useState(true);
  const limit = 25;

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ skip: page * limit, limit });
      if (searchEmail) params.append('email', searchEmail);
      if (filterType) params.append('event_type', filterType);
      const resp = await axios.get(`${API}/security-audit-logs?${params}`);
      setLogs(resp.data.logs);
      setTotal(resp.data.total);
    } catch (err) {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, [page, filterType]);

  const handleSearch = () => { setPage(0); fetchLogs(); };

  const downloadCSV = () => {
    const headers = ['Timestamp', 'Event', 'Email', 'IP Address', 'User Agent', 'Details'];
    const rows = logs.map(l => [
      new Date(l.timestamp).toLocaleString(),
      EVENT_LABELS[l.event_type] || l.event_type,
      l.email || '-',
      l.ip_address || '-',
      l.user_agent || '-',
      JSON.stringify(l.details || {}),
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security_audit_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalPages = Math.ceil(total / limit);
  const eventTypes = [...new Set(Object.keys(EVENT_LABELS))];

  if (user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center h-64" data-testid="security-audit-forbidden">
        <p className="text-zinc-500">Access restricted to administrators only.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="security-audit-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-zinc-700" />
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">Security Audit Log</h1>
        </div>
        <Button variant="outline" size="sm" onClick={downloadCSV} data-testid="download-csv-btn">
          <Download className="h-4 w-4 mr-1" /> Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card className="border-zinc-200">
        <CardContent className="pt-4 pb-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Search by Email</label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
                <Input
                  data-testid="search-email-input"
                  placeholder="user@dvconsulting.co.in"
                  value={searchEmail}
                  onChange={e => setSearchEmail(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  className="pl-9 h-9 rounded-sm border-zinc-200"
                />
              </div>
            </div>
            <div className="min-w-[180px]">
              <label className="text-xs font-medium text-zinc-500 mb-1 block">Event Type</label>
              <select
                data-testid="event-type-filter"
                value={filterType}
                onChange={e => { setFilterType(e.target.value); setPage(0); }}
                className="w-full h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
              >
                <option value="">All Events</option>
                {eventTypes.map(t => (
                  <option key={t} value={t}>{EVENT_LABELS[t]}</option>
                ))}
              </select>
            </div>
            <Button size="sm" onClick={handleSearch} className="h-9 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm" data-testid="search-btn">
              <Filter className="h-3.5 w-3.5 mr-1" /> Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Events', value: total, color: 'text-zinc-900' },
          { label: 'Successful Logins', value: logs.filter(l => l.event_type?.includes('success')).length, color: 'text-emerald-700' },
          { label: 'Failed Attempts', value: logs.filter(l => l.event_type?.includes('failed')).length, color: 'text-red-700' },
          { label: 'Rejected Access', value: logs.filter(l => l.event_type?.includes('rejected')).length, color: 'text-orange-700' },
        ].map((s, i) => (
          <Card key={i} className="border-zinc-200">
            <CardContent className="pt-3 pb-3 text-center">
              <p className="text-xs text-zinc-500">{s.label}</p>
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Logs Table */}
      <Card className="border-zinc-200">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="audit-logs-table">
              <thead>
                <tr className="border-b border-zinc-100 bg-zinc-50/50">
                  <th className="text-left p-3 font-medium text-zinc-600">Timestamp</th>
                  <th className="text-left p-3 font-medium text-zinc-600">Event</th>
                  <th className="text-left p-3 font-medium text-zinc-600">Email</th>
                  <th className="text-left p-3 font-medium text-zinc-600">IP Address</th>
                  <th className="text-left p-3 font-medium text-zinc-600">Details</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} className="p-8 text-center text-zinc-400">Loading...</td></tr>
                ) : logs.length === 0 ? (
                  <tr><td colSpan={5} className="p-8 text-center text-zinc-400">No audit logs found</td></tr>
                ) : logs.map(log => (
                  <tr key={log.id} className="border-b border-zinc-50 hover:bg-zinc-50/50 transition-colors" data-testid={`audit-log-${log.id}`}>
                    <td className="p-3 text-zinc-600 whitespace-nowrap text-xs">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <Badge variant="secondary" className={`text-xs font-medium ${EVENT_COLORS[log.event_type] || 'bg-zinc-100 text-zinc-700'}`}>
                        {EVENT_LABELS[log.event_type] || log.event_type}
                      </Badge>
                    </td>
                    <td className="p-3 text-zinc-700 font-mono text-xs">{log.email || '-'}</td>
                    <td className="p-3 text-zinc-500 font-mono text-xs">{log.ip_address || '-'}</td>
                    <td className="p-3 text-zinc-500 text-xs max-w-[200px] truncate">
                      {log.details && Object.keys(log.details).length > 0
                        ? Object.entries(log.details).filter(([k]) => k !== 'otp_code').map(([k, v]) => `${k}: ${v}`).join(', ')
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-3 border-t border-zinc-100">
              <span className="text-xs text-zinc-500">
                Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
              </span>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 0} data-testid="prev-page-btn">
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1} data-testid="next-page-btn">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SecurityAuditLog;
