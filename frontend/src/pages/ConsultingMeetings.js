import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import {
  Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle,
  FileText, Send, Calendar, Trash2, ChevronDown, ChevronUp,
  ClipboardList, Mail, BarChart3, Target
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const CONSULTING_ROLES = ['admin', 'project_manager', 'consultant', 'principal_consultant',
  'lean_consultant', 'lead_consultant', 'senior_consultant', 'subject_matter_expert', 'manager'];

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low', color: 'bg-zinc-100 text-zinc-700' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'high', label: 'High', color: 'bg-red-100 text-red-700' }
];

const ConsultingMeetings = () => {
  const { user } = useContext(AuthContext);
  const [meetings, setMeetings] = useState([]);
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [sows, setSows] = useState([]);
  const [users, setUsers] = useState([]);
  const [tracking, setTracking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [momDialogOpen, setMomDialogOpen] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [expandedMeetings, setExpandedMeetings] = useState({});
  const [activeTab, setActiveTab] = useState('meetings');

  const [formData, setFormData] = useState({
    title: '', project_id: '', client_id: '', sow_id: '', meeting_date: '',
    mode: 'online', duration_minutes: '', notes: '', is_delivered: false,
    agenda: [''], attendees: [], attendee_names: []
  });

  const [momData, setMomData] = useState({
    title: '', agenda: [''], discussion_points: [''], decisions_made: [''],
    action_items: [], next_meeting_date: ''
  });

  const [newActionItem, setNewActionItem] = useState({
    description: '', assigned_to_id: '', due_date: '', priority: 'medium',
    create_follow_up_task: true, notify_reporting_manager: true
  });

  const canEdit = CONSULTING_ROLES.includes(user?.role) && user?.role !== 'manager';

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [meetingsRes, projectsRes, clientsRes, usersRes, trackingRes] = await Promise.all([
        axios.get(`${API}/meetings?meeting_type=consulting`),
        axios.get(`${API}/projects`),
        axios.get(`${API}/clients`).catch(() => ({ data: [] })),
        axios.get(`${API}/users`),
        axios.get(`${API}/consulting-meetings/tracking`).catch(() => ({ data: [] }))
      ]);
      setMeetings(meetingsRes.data);
      setProjects(projectsRes.data);
      setClients(clientsRes.data);
      setUsers(usersRes.data);
      setTracking(trackingRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/meetings`, {
        ...formData, type: 'consulting',
        meeting_date: new Date(formData.meeting_date).toISOString(),
        duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : null,
        agenda: formData.agenda.filter(a => a.trim())
      });
      toast.success('Consulting meeting created');
      setDialogOpen(false);
      setFormData({ title: '', project_id: '', client_id: '', sow_id: '', meeting_date: '', mode: 'online', duration_minutes: '', notes: '', is_delivered: false, agenda: [''], attendees: [], attendee_names: [] });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create meeting');
    }
  };

  const openMOMDialog = async (meeting) => {
    try {
      const res = await axios.get(`${API}/meetings/${meeting.id}`);
      const m = res.data;
      setSelectedMeeting(m);
      setMomData({
        title: m.title || '', agenda: m.agenda?.length ? m.agenda : [''],
        discussion_points: m.discussion_points?.length ? m.discussion_points : [''],
        decisions_made: m.decisions_made?.length ? m.decisions_made : [''],
        action_items: m.action_items || [],
        next_meeting_date: m.next_meeting_date ? m.next_meeting_date.split('T')[0] : ''
      });
      setMomDialogOpen(true);
    } catch { toast.error('Failed to load meeting'); }
  };

  const handleSaveMOM = async () => {
    try {
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/mom`, {
        ...momData,
        agenda: momData.agenda.filter(a => a.trim()),
        discussion_points: momData.discussion_points.filter(d => d.trim()),
        decisions_made: momData.decisions_made.filter(d => d.trim()),
        next_meeting_date: momData.next_meeting_date ? new Date(momData.next_meeting_date).toISOString() : null
      });
      toast.success('Consulting MOM saved');
      fetchData();
    } catch { toast.error('Failed to save MOM'); }
  };

  const handleAddActionItem = async () => {
    if (!newActionItem.description.trim()) { toast.error('Description required'); return; }
    try {
      const res = await axios.post(`${API}/meetings/${selectedMeeting.id}/action-items`, {
        ...newActionItem,
        due_date: newActionItem.due_date ? new Date(newActionItem.due_date).toISOString() : null
      });
      toast.success('Action item added');
      setMomData(prev => ({ ...prev, action_items: [...prev.action_items, res.data.action_item] }));
      setNewActionItem({ description: '', assigned_to_id: '', due_date: '', priority: 'medium', create_follow_up_task: true, notify_reporting_manager: true });
      fetchData();
    } catch { toast.error('Failed to add action item'); }
  };

  const handleUpdateActionItemStatus = async (actionItemId, status) => {
    try {
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/action-items/${actionItemId}?status=${status}`);
      setMomData(prev => ({ ...prev, action_items: prev.action_items.map(i => i.id === actionItemId ? { ...i, status } : i) }));
      toast.success('Status updated');
      fetchData();
    } catch { toast.error('Failed to update'); }
  };

  const handleSendMOM = async () => {
    try {
      const res = await axios.post(`${API}/meetings/${selectedMeeting.id}/send-mom`);
      toast.success(`MOM sent to ${res.data.client_name || res.data.client_email}`);
      fetchData();
      setMomDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send MOM');
    }
  };

  const addArrayItem = (field, setFn, data) => setFn({ ...data, [field]: [...data[field], ''] });
  const updateArrayItem = (field, idx, val, setFn, data) => {
    const arr = [...data[field]]; arr[idx] = val; setFn({ ...data, [field]: arr });
  };
  const removeArrayItem = (field, idx, setFn, data) => {
    if (data[field].length > 1) setFn({ ...data, [field]: data[field].filter((_, i) => i !== idx) });
  };

  const getModeIcon = (mode) => {
    if (mode === 'offline') return <UsersIcon className="w-4 h-4" strokeWidth={1.5} />;
    if (mode === 'tele_call') return <Phone className="w-4 h-4" strokeWidth={1.5} />;
    return <Video className="w-4 h-4" strokeWidth={1.5} />;
  };
  const getModeBadge = (mode) => ({
    online: 'bg-blue-50 text-blue-700', offline: 'bg-purple-50 text-purple-700', tele_call: 'bg-emerald-50 text-emerald-700'
  }[mode] || 'bg-blue-50 text-blue-700');

  const activeTracking = tracking.filter(t => t.status === 'active' && t.committed > 0);

  return (
    <div data-testid="consulting-meetings-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Consulting Meetings</h1>
          <p className="text-zinc-500">Manage client project meetings, MOM, and track commitments</p>
        </div>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-consulting-meeting-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> New Consulting Meeting
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Schedule Consulting Meeting</DialogTitle>
                <DialogDescription className="text-zinc-500">Link to project & client for billable tracking</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Meeting Title *</Label>
                    <Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      placeholder="e.g., Weekly Review, Deliverable Walkthrough" required className="rounded-sm border-zinc-200" data-testid="consulting-meeting-title" />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Project *</Label>
                    <select value={formData.project_id}
                      onChange={(e) => {
                        const p = projects.find(pr => pr.id === e.target.value);
                        setFormData({ ...formData, project_id: e.target.value, client_id: '', sow_id: '' });
                      }}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="consulting-meeting-project">
                      <option value="">Select project</option>
                      {projects.map(p => <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Client</Label>
                    <select value={formData.client_id} onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="consulting-meeting-client">
                      <option value="">Select client</option>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">SOW (Optional)</Label>
                    <select value={formData.sow_id} onChange={(e) => setFormData({ ...formData, sow_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="consulting-meeting-sow">
                      <option value="">Link to SOW</option>
                      {sows.map(s => <option key={s.id} value={s.id}>{s.client_name || s.id}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Date & Time *</Label>
                    <Input type="datetime-local" value={formData.meeting_date}
                      onChange={(e) => setFormData({ ...formData, meeting_date: e.target.value })} required className="rounded-sm border-zinc-200" data-testid="consulting-meeting-date" />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Mode *</Label>
                    <select value={formData.mode} onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm">
                      <option value="online">Online</option>
                      <option value="offline">In-person</option>
                      <option value="tele_call">Tele Call</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Duration (mins)</Label>
                    <Input type="number" min="0" value={formData.duration_minutes}
                      onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })} className="rounded-sm border-zinc-200" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Agenda Items</Label>
                  {formData.agenda.map((item, idx) => (
                    <div key={idx} className="flex gap-2">
                      <Input value={item} onChange={(e) => updateArrayItem('agenda', idx, e.target.value, setFormData, formData)}
                        placeholder={`Agenda item ${idx + 1}`} className="rounded-sm border-zinc-200" />
                      {formData.agenda.length > 1 && <Button type="button" onClick={() => removeArrayItem('agenda', idx, setFormData, formData)} variant="ghost" className="px-2"><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                    </div>
                  ))}
                  <Button type="button" onClick={() => addArrayItem('agenda', setFormData, formData)} variant="outline" size="sm" className="rounded-sm">
                    <Plus className="w-4 h-4 mr-1" /> Add Agenda
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Attendees</Label>
                  <select multiple value={formData.attendees}
                    onChange={(e) => {
                      const sel = Array.from(e.target.selectedOptions, o => o.value);
                      setFormData({ ...formData, attendees: sel, attendee_names: sel.map(id => users.find(u => u.id === id)?.full_name || '') });
                    }}
                    className="w-full h-24 px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm">
                    {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>)}
                  </select>
                  <p className="text-xs text-zinc-400">Hold Ctrl/Cmd to select multiple</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Notes</Label>
                  <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={2} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm" />
                </div>
                <div className="flex items-center space-x-2">
                  <input type="checkbox" id="is_delivered" checked={formData.is_delivered}
                    onChange={(e) => setFormData({ ...formData, is_delivered: e.target.checked })} className="w-4 h-4 rounded-sm border-zinc-200" />
                  <Label htmlFor="is_delivered" className="text-sm font-medium text-zinc-950">Mark as delivered (counts toward commitment)</Label>
                </div>
                <Button type="submit" data-testid="submit-consulting-meeting" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  Schedule Meeting
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-zinc-200">
        <button onClick={() => setActiveTab('meetings')} data-testid="tab-meetings"
          className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'meetings' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500 hover:text-zinc-700'}`}>
          Meetings ({meetings.length})
        </button>
        <button onClick={() => setActiveTab('tracking')} data-testid="tab-tracking"
          className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'tracking' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500 hover:text-zinc-700'}`}>
          Commitment Tracking
        </button>
      </div>

      {activeTab === 'tracking' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Total Committed</div>
                <div className="text-2xl font-semibold text-zinc-950" data-testid="tracking-total-committed">
                  {tracking.reduce((sum, t) => sum + t.committed, 0)}
                </div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Total Delivered</div>
                <div className="text-2xl font-semibold text-emerald-700" data-testid="tracking-total-delivered">
                  {tracking.reduce((sum, t) => sum + t.actual_meetings, 0)}
                </div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Active Projects</div>
                <div className="text-2xl font-semibold text-zinc-950">{activeTracking.length}</div>
              </CardContent>
            </Card>
          </div>

          {activeTracking.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-40">
                <Target className="w-10 h-10 text-zinc-300 mb-3" />
                <p className="text-zinc-500">No projects with committed meetings yet</p>
                <p className="text-xs text-zinc-400 mt-1">Set committed meetings in project settings</p>
              </CardContent>
            </Card>
          ) : (
            <div className="border border-zinc-200 rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Project</th>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Client</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Committed</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Actual</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Variance</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Completion</th>
                  </tr>
                </thead>
                <tbody>
                  {activeTracking.map(t => (
                    <tr key={t.project_id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`tracking-row-${t.project_id}`}>
                      <td className="px-4 py-3 font-medium text-zinc-950">{t.project_name}</td>
                      <td className="px-4 py-3 text-zinc-600">{t.client_name}</td>
                      <td className="px-4 py-3 text-center text-zinc-700">{t.committed}</td>
                      <td className="px-4 py-3 text-center font-medium text-zinc-950">{t.actual_meetings}</td>
                      <td className={`px-4 py-3 text-center font-medium ${t.variance >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                        {t.variance >= 0 ? '+' : ''}{t.variance}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-20 bg-zinc-200 rounded-full h-2">
                            <div className={`h-2 rounded-full ${t.completion_pct >= 100 ? 'bg-emerald-600' : t.completion_pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                              style={{ width: `${Math.min(t.completion_pct, 100)}%` }} />
                          </div>
                          <span className="text-xs text-zinc-600">{t.completion_pct}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'meetings' && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Total Meetings</div>
                <div className="text-2xl font-semibold text-zinc-950" data-testid="consulting-total-count">{meetings.length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Delivered</div>
                <div className="text-2xl font-semibold text-emerald-700">{meetings.filter(m => m.is_delivered).length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">With MOM</div>
                <div className="text-2xl font-semibold text-zinc-950">{meetings.filter(m => m.mom_generated).length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Action Items</div>
                <div className="text-2xl font-semibold text-zinc-950">
                  {meetings.reduce((sum, m) => sum + (m.action_items?.length || 0), 0)}
                </div>
              </CardContent>
            </Card>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64"><div className="text-zinc-500">Loading...</div></div>
          ) : meetings.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-64">
                <Calendar className="w-12 h-12 text-zinc-300 mb-4" />
                <p className="text-zinc-500 mb-4">No consulting meetings yet</p>
                {canEdit && (
                  <Button onClick={() => setDialogOpen(true)} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                    <Plus className="w-4 h-4 mr-2" /> Schedule First Meeting
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {meetings.map((meeting) => {
                const project = projects.find(p => p.id === meeting.project_id);
                const client = clients.find(c => c.id === meeting.client_id);
                const isExpanded = expandedMeetings[meeting.id];
                const actionItemsCount = meeting.action_items?.length || 0;
                const completedCount = meeting.action_items?.filter(a => a.status === 'completed').length || 0;

                return (
                  <Card key={meeting.id} data-testid={`consulting-meeting-card-${meeting.id}`}
                    className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className={`p-2 rounded-sm ${getModeBadge(meeting.mode)}`}>{getModeIcon(meeting.mode)}</div>
                            <div>
                              <div className="font-medium text-zinc-950">{meeting.title || project?.name || 'Meeting'}</div>
                              <div className="text-sm text-zinc-500">
                                {project?.name && <span>{project.name}</span>}
                                {client?.company_name && <span> | {client.company_name}</span>}
                                {!project && !client && <span>No project linked</span>}
                              </div>
                            </div>
                            {meeting.mom_generated && (
                              <span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-700 rounded-sm flex items-center gap-1">
                                <FileText className="w-3 h-3" /> MOM
                              </span>
                            )}
                            {meeting.mom_sent_to_client && (
                              <span className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-sm flex items-center gap-1">
                                <Mail className="w-3 h-3" /> Sent
                              </span>
                            )}
                          </div>
                          <div className="grid grid-cols-4 gap-4 mt-3">
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Date & Time</div>
                              <div className="text-sm text-zinc-950">{format(new Date(meeting.meeting_date), 'MMM dd, yyyy HH:mm')}</div>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Mode</div>
                              <div className="text-sm text-zinc-950">{meeting.mode === 'online' ? 'Online' : meeting.mode === 'offline' ? 'In-person' : 'Tele Call'}</div>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Duration</div>
                              <div className="text-sm text-zinc-950">{meeting.duration_minutes || '-'} mins</div>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Action Items</div>
                              <div className="text-sm text-zinc-950">{completedCount}/{actionItemsCount} completed</div>
                            </div>
                          </div>
                          {isExpanded && (
                            <div className="mt-4 pt-4 border-t border-zinc-200 space-y-3">
                              {meeting.agenda?.length > 0 && meeting.agenda.some(a => a) && (
                                <div>
                                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Agenda</div>
                                  <ul className="list-disc list-inside text-sm text-zinc-600">
                                    {meeting.agenda.filter(a => a).map((item, idx) => <li key={idx}>{item}</li>)}
                                  </ul>
                                </div>
                              )}
                              {meeting.attendee_names?.length > 0 && (
                                <div>
                                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Attendees</div>
                                  <div className="text-sm text-zinc-600">{meeting.attendee_names.join(', ')}</div>
                                </div>
                              )}
                              {meeting.action_items?.length > 0 && (
                                <div>
                                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">Action Items</div>
                                  <div className="space-y-2">
                                    {meeting.action_items.map(item => (
                                      <div key={item.id} className={`flex items-center justify-between p-2 rounded-sm border ${item.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-zinc-50 border-zinc-200'}`}>
                                        <div className="flex items-center gap-2">
                                          {item.status === 'completed' ? <CheckCircle className="w-4 h-4 text-green-600" /> : <Circle className="w-4 h-4 text-zinc-400" />}
                                          <span className={`text-sm ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-700'}`}>{item.description}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                          <span className="text-xs text-zinc-500">{item.assigned_to_name || 'Unassigned'}</span>
                                          <span className={`text-xs px-2 py-0.5 rounded-sm ${PRIORITY_OPTIONS.find(p => p.value === item.priority)?.color || ''}`}>{item.priority}</span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {meeting.notes && (
                                <div>
                                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Notes</div>
                                  <div className="text-sm text-zinc-600">{meeting.notes}</div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="ml-4 flex flex-col items-end gap-2">
                          {meeting.is_delivered ? (
                            <div className="flex items-center gap-2 text-emerald-600">
                              <CheckCircle className="w-5 h-5" strokeWidth={1.5} />
                              <span className="text-sm font-medium">Delivered</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-zinc-400">
                              <Circle className="w-5 h-5" strokeWidth={1.5} />
                              <span className="text-sm font-medium">Pending</span>
                            </div>
                          )}
                          <div className="flex items-center gap-2">
                            <Button onClick={() => setExpandedMeetings(prev => ({ ...prev, [meeting.id]: !prev[meeting.id] }))}
                              variant="ghost" size="sm" className="text-zinc-500">
                              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </Button>
                            {canEdit && (
                              <Button onClick={() => openMOMDialog(meeting)} variant="outline" size="sm" className="rounded-sm"
                                data-testid={`consulting-mom-btn-${meeting.id}`}>
                                <ClipboardList className="w-4 h-4 mr-1" /> MOM
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Consulting MOM Dialog - Detailed with Action Items */}
      <Dialog open={momDialogOpen} onOpenChange={setMomDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Consulting MOM</DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedMeeting?.title} - {selectedMeeting?.meeting_date ? format(new Date(selectedMeeting.meeting_date), 'MMM dd, yyyy') : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Meeting Title</Label>
              <Input value={momData.title} onChange={(e) => setMomData({ ...momData, title: e.target.value })} className="rounded-sm border-zinc-200" data-testid="consulting-mom-title" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Agenda</Label>
              {momData.agenda.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input value={item} onChange={(e) => updateArrayItem('agenda', idx, e.target.value, setMomData, momData)}
                    placeholder={`Agenda ${idx + 1}`} className="rounded-sm border-zinc-200" />
                  {momData.agenda.length > 1 && <Button onClick={() => removeArrayItem('agenda', idx, setMomData, momData)} variant="ghost" className="px-2"><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                </div>
              ))}
              <Button onClick={() => addArrayItem('agenda', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Agenda
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Discussion Points</Label>
              {momData.discussion_points.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input value={item} onChange={(e) => updateArrayItem('discussion_points', idx, e.target.value, setMomData, momData)}
                    placeholder={`Point ${idx + 1}`} className="rounded-sm border-zinc-200" />
                  {momData.discussion_points.length > 1 && <Button onClick={() => removeArrayItem('discussion_points', idx, setMomData, momData)} variant="ghost" className="px-2"><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                </div>
              ))}
              <Button onClick={() => addArrayItem('discussion_points', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Point
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Decisions Made</Label>
              {momData.decisions_made.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input value={item} onChange={(e) => updateArrayItem('decisions_made', idx, e.target.value, setMomData, momData)}
                    placeholder={`Decision ${idx + 1}`} className="rounded-sm border-zinc-200" />
                  {momData.decisions_made.length > 1 && <Button onClick={() => removeArrayItem('decisions_made', idx, setMomData, momData)} variant="ghost" className="px-2"><Trash2 className="w-4 h-4 text-red-500" /></Button>}
                </div>
              ))}
              <Button onClick={() => addArrayItem('decisions_made', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Decision
              </Button>
            </div>

            {/* Action Items Section */}
            <div className="space-y-4">
              <Label className="text-sm font-medium text-zinc-950">Action Items</Label>
              {momData.action_items.length > 0 && (
                <div className="space-y-2">
                  {momData.action_items.map(item => (
                    <div key={item.id} className={`flex items-center justify-between p-3 rounded-sm border ${item.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-zinc-50 border-zinc-200'}`}>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-700 font-medium'}`}>{item.description}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-sm ${PRIORITY_OPTIONS.find(p => p.value === item.priority)?.color || ''}`}>{item.priority}</span>
                        </div>
                        <div className="text-xs text-zinc-500 mt-1">
                          Assigned: {item.assigned_to_name || 'Unassigned'} | Due: {item.due_date ? format(new Date(item.due_date), 'MMM dd') : 'No date'}
                          {item.follow_up_task_id && <span className="ml-2 text-blue-600">Task created</span>}
                        </div>
                      </div>
                      {item.status !== 'completed' && canEdit && (
                        <Button onClick={() => handleUpdateActionItemStatus(item.id, 'completed')} variant="ghost" size="sm" className="text-green-600 hover:bg-green-50">
                          <CheckCircle className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {canEdit && (
                <div className="p-4 bg-zinc-50 rounded-sm border border-zinc-200 space-y-3">
                  <div className="text-sm font-medium text-zinc-700">Add New Action Item</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <Input value={newActionItem.description} onChange={(e) => setNewActionItem({ ...newActionItem, description: e.target.value })}
                        placeholder="Action item description..." className="rounded-sm border-zinc-200" data-testid="action-item-description" />
                    </div>
                    <select value={newActionItem.assigned_to_id} onChange={(e) => setNewActionItem({ ...newActionItem, assigned_to_id: e.target.value })}
                      className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm" data-testid="action-item-assignee">
                      <option value="">Assign to...</option>
                      {users.map(u => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                    </select>
                    <Input type="date" value={newActionItem.due_date} onChange={(e) => setNewActionItem({ ...newActionItem, due_date: e.target.value })}
                      className="rounded-sm border-zinc-200" data-testid="action-item-due-date" />
                    <select value={newActionItem.priority} onChange={(e) => setNewActionItem({ ...newActionItem, priority: e.target.value })}
                      className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm">
                      {PRIORITY_OPTIONS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 text-sm text-zinc-600">
                        <input type="checkbox" checked={newActionItem.create_follow_up_task}
                          onChange={(e) => setNewActionItem({ ...newActionItem, create_follow_up_task: e.target.checked })} className="w-4 h-4 rounded border-zinc-200" />
                        Create Task
                      </label>
                      <label className="flex items-center gap-2 text-sm text-zinc-600">
                        <input type="checkbox" checked={newActionItem.notify_reporting_manager}
                          onChange={(e) => setNewActionItem({ ...newActionItem, notify_reporting_manager: e.target.checked })} className="w-4 h-4 rounded border-zinc-200" />
                        Notify Manager
                      </label>
                    </div>
                  </div>
                  <Button onClick={handleAddActionItem} variant="outline" className="rounded-sm" data-testid="add-action-item-btn">
                    <Plus className="w-4 h-4 mr-1" /> Add Action Item
                  </Button>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Next Meeting Date</Label>
              <Input type="datetime-local" value={momData.next_meeting_date}
                onChange={(e) => setMomData({ ...momData, next_meeting_date: e.target.value })} className="rounded-sm border-zinc-200 w-64" />
            </div>

            <div className="flex justify-between pt-4 border-t border-zinc-200">
              <Button onClick={handleSaveMOM} data-testid="save-consulting-mom" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Save MOM
              </Button>
              <Button onClick={handleSendMOM} variant="outline" className="rounded-sm"
                disabled={selectedMeeting?.mom_sent_to_client} data-testid="send-mom-btn">
                <Send className="w-4 h-4 mr-2" />
                {selectedMeeting?.mom_sent_to_client ? 'MOM Sent' : 'Send to Client'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsultingMeetings;
