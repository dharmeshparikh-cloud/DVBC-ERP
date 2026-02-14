import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle, Calendar, Trash2, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const SALES_ROLES = ['admin', 'executive', 'account_manager'];

const SalesMeetings = () => {
  const { user } = useContext(AuthContext);
  const [meetings, setMeetings] = useState([]);
  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [momDialogOpen, setMomDialogOpen] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [expandedMeetings, setExpandedMeetings] = useState({});

  const [formData, setFormData] = useState({
    title: '', meeting_date: '', mode: 'online', duration_minutes: '',
    notes: '', lead_id: '', attendees: [], attendee_names: [], agenda: ['']
  });

  const [momData, setMomData] = useState({
    title: '', agenda: [''], discussion_points: [''], decisions_made: [''],
    next_meeting_date: ''
  });

  const canEdit = SALES_ROLES.includes(user?.role);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [meetingsRes, leadsRes, usersRes] = await Promise.all([
        axios.get(`${API}/meetings?meeting_type=sales`),
        axios.get(`${API}/leads`),
        axios.get(`${API}/users`)
      ]);
      setMeetings(meetingsRes.data);
      setLeads(leadsRes.data);
      setUsers(usersRes.data);
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
        ...formData,
        type: 'sales',
        meeting_date: new Date(formData.meeting_date).toISOString(),
        duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : null,
        agenda: formData.agenda.filter(a => a.trim())
      });
      toast.success('Sales meeting created');
      setDialogOpen(false);
      setFormData({ title: '', meeting_date: '', mode: 'online', duration_minutes: '', notes: '', lead_id: '', attendees: [], attendee_names: [], agenda: [''] });
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
      toast.success('Sales MOM saved');
      setMomDialogOpen(false);
      fetchData();
    } catch { toast.error('Failed to save MOM'); }
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

  return (
    <div data-testid="sales-meetings-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Sales Meetings</h1>
          <p className="text-zinc-500">Track sales meetings, calls, and follow-ups with leads</p>
        </div>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-sales-meeting-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> New Sales Meeting
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Schedule Sales Meeting</DialogTitle>
                <DialogDescription className="text-zinc-500">Quick meeting setup for sales activities</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Meeting Title *</Label>
                    <Input value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      placeholder="e.g., Discovery Call, Follow-up" required className="rounded-sm border-zinc-200" data-testid="sales-meeting-title" />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Lead</Label>
                    <select value={formData.lead_id} onChange={(e) => setFormData({ ...formData, lead_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="sales-meeting-lead">
                      <option value="">Select lead (optional)</option>
                      {leads.map(l => <option key={l.id} value={l.id}>{l.first_name} {l.last_name} - {l.company}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Date & Time *</Label>
                    <Input type="datetime-local" value={formData.meeting_date} onChange={(e) => setFormData({ ...formData, meeting_date: e.target.value })}
                      required className="rounded-sm border-zinc-200" data-testid="sales-meeting-date" />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Mode *</Label>
                    <select value={formData.mode} onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="sales-meeting-mode">
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
                      {formData.agenda.length > 1 && (
                        <Button type="button" onClick={() => removeArrayItem('agenda', idx, setFormData, formData)} variant="ghost" className="px-2">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      )}
                    </div>
                  ))}
                  <Button type="button" onClick={() => addArrayItem('agenda', setFormData, formData)} variant="outline" size="sm" className="rounded-sm">
                    <Plus className="w-4 h-4 mr-1" /> Add Agenda
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Notes</Label>
                  <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={2} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="sales-meeting-notes" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Attendees</Label>
                  <select multiple value={formData.attendees}
                    onChange={(e) => {
                      const sel = Array.from(e.target.selectedOptions, o => o.value);
                      setFormData({ ...formData, attendees: sel, attendee_names: sel.map(id => users.find(u => u.id === id)?.full_name || '') });
                    }}
                    className="w-full h-20 px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm">
                    {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>)}
                  </select>
                  <p className="text-xs text-zinc-400">Hold Ctrl/Cmd to select multiple</p>
                </div>
                <Button type="submit" data-testid="submit-sales-meeting" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  Schedule Meeting
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Total Meetings</div>
            <div className="text-2xl font-semibold text-zinc-950" data-testid="sales-total-count">{meetings.length}</div>
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
            <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">This Month</div>
            <div className="text-2xl font-semibold text-zinc-950">
              {meetings.filter(m => { const d = new Date(m.meeting_date); const now = new Date(); return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear(); }).length}
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
            <p className="text-zinc-500 mb-4">No sales meetings yet</p>
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
            const lead = leads.find(l => l.id === meeting.lead_id);
            const isExpanded = expandedMeetings[meeting.id];
            return (
              <Card key={meeting.id} data-testid={`sales-meeting-card-${meeting.id}`} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-sm ${getModeBadge(meeting.mode)}`}>{getModeIcon(meeting.mode)}</div>
                        <div>
                          <div className="font-medium text-zinc-950">{meeting.title || 'Sales Meeting'}</div>
                          <div className="text-sm text-zinc-500">{lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'No lead linked'}</div>
                        </div>
                        {meeting.mom_generated && (
                          <span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-700 rounded-sm flex items-center gap-1">
                            <FileText className="w-3 h-3" /> MOM
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-4 mt-3">
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
                          {meeting.discussion_points?.length > 0 && meeting.discussion_points.some(d => d) && (
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Discussion Points</div>
                              <ul className="list-disc list-inside text-sm text-zinc-600">
                                {meeting.discussion_points.filter(d => d).map((item, idx) => <li key={idx}>{item}</li>)}
                              </ul>
                            </div>
                          )}
                          {meeting.decisions_made?.length > 0 && meeting.decisions_made.some(d => d) && (
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Decisions</div>
                              <ul className="list-disc list-inside text-sm text-zinc-600">
                                {meeting.decisions_made.filter(d => d).map((item, idx) => <li key={idx}>{item}</li>)}
                              </ul>
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
                    <div className="ml-4 flex items-center gap-2">
                      <Button onClick={() => setExpandedMeetings(prev => ({ ...prev, [meeting.id]: !prev[meeting.id] }))}
                        variant="ghost" size="sm" className="text-zinc-500">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </Button>
                      {canEdit && (
                        <Button onClick={() => openMOMDialog(meeting)} variant="outline" size="sm" className="rounded-sm" data-testid={`sales-mom-btn-${meeting.id}`}>
                          <FileText className="w-4 h-4 mr-1" /> MOM
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Sales MOM Dialog - Simplified */}
      <Dialog open={momDialogOpen} onOpenChange={setMomDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Sales MOM</DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedMeeting?.title} - {selectedMeeting?.meeting_date ? format(new Date(selectedMeeting.meeting_date), 'MMM dd, yyyy') : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Meeting Title</Label>
              <Input value={momData.title} onChange={(e) => setMomData({ ...momData, title: e.target.value })}
                className="rounded-sm border-zinc-200" data-testid="sales-mom-title" />
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
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Next Meeting Date</Label>
              <Input type="datetime-local" value={momData.next_meeting_date}
                onChange={(e) => setMomData({ ...momData, next_meeting_date: e.target.value })} className="rounded-sm border-zinc-200 w-64" />
            </div>
            <div className="flex justify-end pt-4 border-t border-zinc-200">
              <Button onClick={handleSaveMOM} data-testid="save-sales-mom" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">Save MOM</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SalesMeetings;
