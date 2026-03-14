import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Send, Eye, Clock, CheckCircle, XCircle, Settings,
  BarChart3, Users, TrendingUp, AlertTriangle, Calendar,
  RefreshCw, Mail, Shield, Briefcase, DollarSign
} from 'lucide-react';
import { toast } from 'sonner';

const CEOReportDashboard = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [showPreview, setShowPreview] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [editRecipient, setEditRecipient] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  // Fetch report data
  const { data: reportData, isLoading: loadingData, refetch: refetchData } = useQuery({
    queryKey: ['ceo-report-data'],
    queryFn: async () => {
      const res = await axios.get(`${API}/ceo-report/data`);
      return res.data;
    },
    staleTime: 60 * 1000,
  });

  // Fetch config
  const { data: config, refetch: refetchConfig } = useQuery({
    queryKey: ['ceo-report-config'],
    queryFn: async () => {
      const res = await axios.get(`${API}/ceo-report/config`);
      return res.data;
    },
  });

  // Fetch logs
  const { data: logsData } = useQuery({
    queryKey: ['ceo-report-logs'],
    queryFn: async () => {
      const res = await axios.get(`${API}/ceo-report/logs`);
      return res.data?.logs || [];
    },
  });
  const logs = logsData || [];

  // Send report mutation
  const sendMutation = useMutation({
    mutationFn: async () => {
      const res = await axios.post(`${API}/ceo-report/trigger`);
      return res.data;
    },
    onSuccess: (data) => {
      if (data.status === 'sent') {
        toast.success('CEO Report sent successfully!');
      } else {
        toast.error(`Failed: ${data.details?.failure_message || 'Unknown error'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['ceo-report-logs'] });
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to send report');
    },
  });

  // Update config mutation
  const configMutation = useMutation({
    mutationFn: async (updates) => {
      const res = await axios.put(`${API}/ceo-report/config`, updates);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Configuration updated');
      refetchConfig();
      setShowSettings(false);
    },
  });

  // Preview
  const handlePreview = async () => {
    try {
      const res = await axios.get(`${API}/ceo-report/preview`, { responseType: 'text' });
      setPreviewHtml(typeof res.data === 'string' ? res.data : JSON.stringify(res.data));
      setShowPreview(true);
    } catch {
      toast.error('Failed to load preview');
    }
  };

  const sa = reportData?.sales_activity || {};
  const ph = reportData?.pipeline_health || {};
  const esc = reportData?.escalations || {};
  const con = reportData?.consulting || {};
  const pay = reportData?.payments || {};
  const rev = reportData?.revenue || {};
  const sh = reportData?.system_health || {};

  if (loadingData) {
    return <div className="flex items-center justify-center h-64" data-testid="ceo-report-loading"><RefreshCw className="w-6 h-6 animate-spin text-zinc-400" /></div>;
  }

  return (
    <div className="space-y-6" data-testid="ceo-report-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900" data-testid="ceo-report-title">CEO Control Tower</h1>
          <p className="text-zinc-500 text-sm">Daily Business Intelligence Report &mdash; {reportData?.date || 'Today'}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetchData()} data-testid="ceo-refresh-btn">
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handlePreview} data-testid="ceo-preview-btn">
            <Eye className="w-3.5 h-3.5 mr-1" /> Preview Email
          </Button>
          <Button variant="outline" size="sm" onClick={() => { setEditRecipient(config?.recipient || ''); setShowSettings(!showSettings); }} data-testid="ceo-settings-btn">
            <Settings className="w-3.5 h-3.5 mr-1" /> Settings
          </Button>
          <Button size="sm" className="bg-zinc-950 text-white hover:bg-zinc-800" onClick={() => sendMutation.mutate()} disabled={sendMutation.isPending} data-testid="ceo-send-btn">
            <Send className="w-3.5 h-3.5 mr-1" /> {sendMutation.isPending ? 'Sending...' : 'Send Now'}
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <Card className="border-zinc-200 shadow-none rounded-sm" data-testid="ceo-settings-panel">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Recipient Email</Label>
                <Input value={editRecipient} onChange={(e) => setEditRecipient(e.target.value)} placeholder="email@example.com" data-testid="ceo-recipient-input" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">SMTP Status</Label>
                <div className="flex items-center gap-2 h-10">
                  {config?.smtp_status === 'configured' ? (
                    <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Connected: {config?.smtp_user}</Badge>
                  ) : (
                    <Badge className="bg-red-100 text-red-700 border-red-200">SMTP Not Configured</Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={() => configMutation.mutate({ recipient: editRecipient })} disabled={configMutation.isPending} data-testid="ceo-save-config-btn">
                  Save
                </Button>
                <span className="text-xs text-zinc-400">Schedule: {config?.schedule_time || '23:59'} IST daily</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Row 1: Sales */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <KPICard icon={TrendingUp} label="New Leads" value={sa.new_leads} color="text-blue-600" bg="bg-blue-50" />
        <KPICard icon={Calendar} label="Meetings" value={sa.meetings} color="text-indigo-600" bg="bg-indigo-50" />
        <KPICard icon={CheckCircle} label="Follow-ups Done" value={sa.followups_done} color="text-emerald-600" bg="bg-emerald-50" />
        <KPICard icon={AlertTriangle} label="Follow-ups Missed" value={sa.followups_missed} color="text-red-600" bg="bg-red-50" />
        <KPICard icon={Send} label="Proposals Sent" value={sa.proposals_sent} color="text-violet-600" bg="bg-violet-50" />
      </div>

      {/* KPI Row 2: Pipeline + Revenue */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard icon={CheckCircle} label="Closed Won" value={sa.closed_won} color="text-emerald-600" bg="bg-emerald-50" />
        <KPICard icon={XCircle} label="Closed Lost" value={sa.closed_lost} color="text-red-600" bg="bg-red-50" />
        <KPICard icon={DollarSign} label="Today Revenue" value={`${(rev.today_revenue || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}`} color="text-emerald-700" bg="bg-emerald-50" />
        <KPICard icon={DollarSign} label="MTD Revenue" value={`${(rev.mtd_revenue || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}`} color="text-blue-700" bg="bg-blue-50" />
      </div>

      {/* Middle Section: Pipeline + Escalations + Consulting */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Pipeline */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Pipeline Health</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="space-y-2">
              {(ph.stages || []).map((s, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-zinc-600">{s.stage}</span>
                  <span className="font-semibold text-zinc-900 tabular-nums">{s.count}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-zinc-100 flex justify-between text-xs">
              <span className="text-zinc-500">Conversion Rate</span>
              <span className="font-semibold text-zinc-900">{ph.conversion_rate || 0}%</span>
            </div>
          </CardContent>
        </Card>

        {/* Escalations */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2 text-red-600"><AlertTriangle className="w-4 h-4" /> Escalations ({esc.count || 0})</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {(esc.items || []).length === 0 ? (
              <p className="text-xs text-zinc-400">No escalations</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {(esc.items || []).slice(0, 8).map((e, i) => (
                  <div key={i} className="p-2 bg-red-50 rounded border-l-2 border-red-400 text-xs">
                    <div className="font-medium text-zinc-800">{e.client_name}</div>
                    <div className="text-zinc-500">{e.entity_type} &middot; {e.assigned_to_name} &middot; <span className="text-red-600 font-medium">{e.days_overdue}d overdue</span></div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Consulting + Payments */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Briefcase className="w-4 h-4" /> Operations</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div><div className="text-lg font-semibold text-zinc-900">{con.active || 0}</div><div className="text-[10px] text-zinc-500 uppercase">Active</div></div>
              <div><div className="text-lg font-semibold text-red-600">{con.at_risk || 0}</div><div className="text-[10px] text-zinc-500 uppercase">At Risk</div></div>
              <div><div className="text-lg font-semibold text-emerald-600">{con.completed || 0}</div><div className="text-[10px] text-zinc-500 uppercase">Done</div></div>
            </div>
            <div className="border-t border-zinc-100 pt-3 space-y-1.5 text-xs">
              <div className="flex justify-between"><span className="text-zinc-500">Outstanding Payments</span><span className="font-semibold">{pay.outstanding || 0}</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">Received Today</span><span className="font-semibold text-emerald-600">{pay.received_today || 0}</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">Overdue 15d+</span><span className="font-semibold text-red-600">{pay.overdue_15_days || 0}</span></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health + Team Productivity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Shield className="w-4 h-4" /> System Health</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div><div className="text-lg font-semibold">{sh.active_users || 0}</div><div className="text-[10px] text-zinc-500 uppercase">Active Users</div></div>
              <div><div className="text-lg font-semibold">{sh.meetings_logged_today || 0}</div><div className="text-[10px] text-zinc-500 uppercase">Meetings Today</div></div>
              <div><div className="text-lg font-semibold">{sh.followups_tomorrow || 0}</div><div className="text-[10px] text-zinc-500 uppercase">Follow-ups Tomorrow</div></div>
            </div>
            {sh.anomalies?.leads_without_followups > 0 && (
              <div className="mt-3 p-2 bg-red-50 border-l-2 border-red-400 rounded text-xs text-red-700">
                <AlertTriangle className="w-3 h-3 inline mr-1" />
                <strong>{sh.anomalies.leads_without_followups}</strong> active leads have no scheduled follow-ups
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium flex items-center gap-2"><Users className="w-4 h-4" /> Team Productivity</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {(reportData?.team_productivity?.team || []).length === 0 ? (
              <p className="text-xs text-zinc-400">No activity recorded today</p>
            ) : (
              <div className="space-y-1.5">
                {(reportData?.team_productivity?.team || []).slice(0, 5).map((t, i) => (
                  <div key={i} className={`flex items-center justify-between p-2 rounded text-xs ${i === 0 ? 'bg-emerald-50' : 'bg-zinc-50'}`}>
                    <span><span className="font-semibold text-zinc-700">#{i + 1}</span> {t.name} <span className="text-zinc-400">({t.role})</span></span>
                    <span className="tabular-nums text-zinc-600">M:{t.meetings} F:{t.followups_done} Score:{t.score}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delivery Logs */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2"><Mail className="w-4 h-4" /> Delivery History</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {logs.length === 0 ? (
            <p className="text-xs text-zinc-400">No reports sent yet</p>
          ) : (
            <div className="space-y-1.5">
              {logs.slice(0, 10).map((log, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-zinc-50 rounded text-xs" data-testid={`delivery-log-${i}`}>
                  <div className="flex items-center gap-2">
                    {log.delivery_status === 'sent' ? (
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-500" />
                    )}
                    <span className="text-zinc-600">{new Date(log.date).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-400">{log.records_included} records</span>
                    {log.delivery_status === 'sent' ? (
                      <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Delivered</Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700 text-[10px]">{log.failure_message?.substring(0, 40) || 'Failed'}</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Email Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowPreview(false)}>
          <div className="bg-white rounded-lg w-[90vw] max-w-[850px] max-h-[85vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold text-zinc-900">Email Preview</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowPreview(false)}>Close</Button>
            </div>
            <div className="flex-1 overflow-auto p-1">
              <iframe title="CEO Report Preview" srcDoc={previewHtml} className="w-full h-full min-h-[600px] border-0" sandbox="" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// KPI Card component
const KPICard = ({ icon: Icon, label, value, color, bg }) => (
  <Card className="border-zinc-200 shadow-none rounded-sm">
    <CardContent className="p-3 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</div>
        <div className="text-lg font-semibold text-zinc-900 tabular-nums">{value ?? 0}</div>
      </div>
    </CardContent>
  </Card>
);

export default CEOReportDashboard;
