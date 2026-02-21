import React, { useState, useEffect, useContext, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle, Calendar, Trash2, ChevronDown, ChevronUp, FileText, FolderOpen } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import useDraft from '../hooks/useDraft';
import DraftSelector, { DraftIndicator } from '../components/DraftSelector';

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
  const [showDraftSelector, setShowDraftSelector] = useState(false);

  // Draft system for meetings
  const generateMeetingDraftTitle = useCallback((data) => {
    if (data.title) return data.title;
    const lead = leads.find(l => l.id === data.lead_id);
    return lead ? `Meeting with ${lead.company || lead.first_name}` : 'New Meeting Draft';
  }, [leads]);

  const {
    draftId,
    drafts,
    loadingDrafts,
    saving: savingDraft,
    lastSaved,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft
  } = useDraft('sales_meeting', generateMeetingDraftTitle);

  const [formData, setFormData] = useState({
    title: '', meeting_date: '', meeting_time: '10:00', meeting_type: 'discovery',
    mode: 'online', duration_minutes: '60', notes: '', lead_id: '', 
    attendees: [], attendee_names: [], agenda: ['']
  });

  // Update form with auto-save
  const updateFormData = (field, value) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      if (dialogOpen) autoSave(updated);
      return updated;
    });
  };

  // Load draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      setShowDraftSelector(false);
      setDialogOpen(true);
      toast.success('Draft loaded');
    }
  };

  // New meeting
  const handleNewMeeting = () => {
    clearDraft();
    setFormData({
      title: '', meeting_date: '', meeting_time: '10:00', meeting_type: 'discovery',
      mode: 'online', duration_minutes: '60', notes: '', lead_id: '', 
      attendees: [], attendee_names: [], agenda: ['']
    });
    setShowDraftSelector(false);
    setDialogOpen(true);
  };

  const [momData, setMomData] = useState({
    summary: '', discussion_points: [''], 
    action_items: [{ task: '', owner: '', due_date: '' }],
    next_steps: '', client_feedback: '', lead_temperature_update: ''
  });

  const canEdit = SALES_ROLES.includes(user?.role);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [meetingsRes, leadsRes, usersRes] = await Promise.all([
        axios.get(`${API}/sales-meetings`).catch(() => ({ data: [] })),
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
      await axios.post(`${API}/sales-meetings`, {
        lead_id: formData.lead_id,
        title: formData.title,
        meeting_type: formData.meeting_type || 'discovery',
        scheduled_date: formData.meeting_date,
        scheduled_time: formData.meeting_time || '10:00',
        duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : 60,
        location: formData.mode === 'online' ? 'Google Meet' : formData.mode === 'offline' ? 'Client Office' : 'Phone Call',
        attendees: formData.attendees || [],
        agenda: formData.agenda?.filter(a => a.trim()).join('\n') || '',
        notes: formData.notes
      });
      toast.success('Sales meeting scheduled');
      setDialogOpen(false);
      await convertDraft();
      setFormData({ title: '', meeting_date: '', meeting_time: '10:00', meeting_type: 'discovery', mode: 'online', duration_minutes: '60', notes: '', lead_id: '', attendees: [], attendee_names: [], agenda: [''] });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create meeting');
    }
  };

  const openMOMDialog = async (meeting) => {
    try {
      setSelectedMeeting(meeting);
      // Try to get existing MOM
      try {
        const momRes = await axios.get(`${API}/sales-meetings/${meeting.id}/mom`);
        const m = momRes.data;
        setMomData({
          summary: m.summary || '',
          discussion_points: m.discussion_points || [''],
          action_items: m.action_items || [{ task: '', owner: '', due_date: '' }],
          next_steps: m.next_steps || '',
          client_feedback: m.client_feedback || '',
          lead_temperature_update: m.lead_temperature_update || ''
        });
      } catch {
        // No existing MOM, start fresh
        setMomData({
          summary: '',
          discussion_points: [''],
          action_items: [{ task: '', owner: '', due_date: '' }],
          next_steps: '',
          client_feedback: '',
          lead_temperature_update: ''
        });
      }
      setMomDialogOpen(true);
    } catch { toast.error('Failed to load meeting'); }
  };

  const handleSaveMOM = async () => {
    try {
      await axios.post(`${API}/sales-meetings/${selectedMeeting.id}/mom`, {
        meeting_id: selectedMeeting.id,
        summary: momData.summary,
        discussion_points: momData.discussion_points?.filter(d => d.trim()) || [],
        action_items: momData.action_items?.filter(a => a.task?.trim()) || [],
        next_steps: momData.next_steps,
        client_feedback: momData.client_feedback,
        lead_temperature_update: momData.lead_temperature_update
      });
      toast.success('MOM saved & meeting completed');
      setMomDialogOpen(false);
      fetchData();
    } catch (error) { 
      toast.error(error.response?.data?.detail || 'Failed to save MOM'); 
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

  return (
    <div data-testid="sales-meetings-page">
      {/* Draft Selector */}
      <DraftSelector
        drafts={drafts}
        loading={loadingDrafts}
        onSelect={handleLoadDraft}
        onDelete={deleteDraft}
        onNewDraft={handleNewMeeting}
        isOpen={showDraftSelector}
        onClose={() => setShowDraftSelector(false)}
        title="Meeting Drafts"
        description="Continue editing a meeting or start a new one"
      />

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Sales Meetings</h1>
          <p className="text-zinc-500">Track sales meetings, calls, and follow-ups with leads</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Drafts Button */}
          {drafts.length > 0 && (
            <Button variant="outline" onClick={() => setShowDraftSelector(true)} className="gap-2">
              <FolderOpen className="w-4 h-4" /> Drafts ({drafts.length})
            </Button>
          )}
          
          {canEdit && (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="add-sales-meeting-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> New Sales Meeting
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950 flex items-center justify-between">
                    <span>Schedule Sales Meeting</span>
                    <DraftIndicator saving={savingDraft} lastSaved={lastSaved} onSave={() => saveDraft(formData)} />
                  </DialogTitle>
                  <DialogDescription className="text-zinc-500">Quick meeting setup for sales activities</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Meeting Title *</Label>
                      <Input value={formData.title} onChange={(e) => updateFormData('title', e.target.value)}
                        placeholder="e.g., Discovery Call, Follow-up" required className="rounded-sm border-zinc-200" data-testid="sales-meeting-title" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Lead</Label>
                      <select value={formData.lead_id} onChange={(e) => updateFormData('lead_id', e.target.value)}
                        className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="sales-meeting-lead">
                        <option value="">Select lead (optional)</option>
                        {leads.map(l => <option key={l.id} value={l.id}>{l.first_name} {l.last_name} - {l.company}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Date & Time *</Label>
                      <Input type="datetime-local" value={formData.meeting_date} onChange={(e) => updateFormData('meeting_date', e.target.value)}
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
            <div className="text-2xl font-semibold text-zinc-950">{meetings.filter(m => m.mom_id || m.mom_generated).length}</div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">This Month</div>
            <div className="text-2xl font-semibold text-zinc-950">
              {meetings.filter(m => { 
                const dateStr = m.scheduled_date || m.meeting_date;
                if (!dateStr) return false;
                const d = new Date(dateStr); 
                const now = new Date(); 
                return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear(); 
              }).length}
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
            const meetingDate = meeting.scheduled_date || meeting.meeting_date;
            const meetingTime = meeting.scheduled_time || '';
            const meetingMode = meeting.location?.toLowerCase().includes('meet') || meeting.location?.toLowerCase().includes('zoom') ? 'online' : 
                               meeting.location?.toLowerCase().includes('phone') ? 'tele_call' : (meeting.mode || 'offline');
            return (
              <Card key={meeting.id} data-testid={`sales-meeting-card-${meeting.id}`} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-sm ${getModeBadge(meetingMode)}`}>{getModeIcon(meetingMode)}</div>
                        <div>
                          <div className="font-medium text-zinc-950">{meeting.title || 'Sales Meeting'}</div>
                          <div className="text-sm text-zinc-500">
                            {meeting.lead_name || (lead ? `${lead.first_name} ${lead.last_name}` : 'No lead linked')}
                            {meeting.company && ` - ${meeting.company}`}
                          </div>
                        </div>
                        {(meeting.mom_id || meeting.mom_generated) && (
                          <span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-700 rounded-sm flex items-center gap-1">
                            <FileText className="w-3 h-3" /> MOM
                          </span>
                        )}
                        {meeting.status && (
                          <span className={`text-xs px-2 py-1 rounded-sm ${
                            meeting.status === 'completed' ? 'bg-green-50 text-green-700' :
                            meeting.status === 'scheduled' ? 'bg-blue-50 text-blue-700' :
                            'bg-zinc-100 text-zinc-600'
                          }`}>
                            {meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-4 gap-4 mt-3">
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Date</div>
                          <div className="text-sm text-zinc-950">
                            {meetingDate ? format(new Date(meetingDate), 'MMM dd, yyyy') : '-'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Time</div>
                          <div className="text-sm text-zinc-950">{meetingTime || '-'}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Location</div>
                          <div className="text-sm text-zinc-950">{meeting.location || meetingMode}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Duration</div>
                          <div className="text-sm text-zinc-950">{meeting.duration_minutes || '-'} mins</div>
                        </div>
                      </div>
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-zinc-200 space-y-3">
                          {meeting.agenda && (
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Agenda</div>
                              <div className="text-sm text-zinc-600 whitespace-pre-line">{meeting.agenda}</div>
                            </div>
                          )}
                          {meeting.meeting_type && (
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Meeting Type</div>
                              <div className="text-sm text-zinc-600 capitalize">{meeting.meeting_type}</div>
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

      {/* Sales MOM Dialog - New Structure */}
      <Dialog open={momDialogOpen} onOpenChange={setMomDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Meeting Minutes (MOM)</DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedMeeting?.title} - {selectedMeeting?.scheduled_date || selectedMeeting?.meeting_date || ''}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5">
            {/* Summary */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Meeting Summary *</Label>
              <textarea 
                value={momData.summary || ''} 
                onChange={(e) => setMomData({ ...momData, summary: e.target.value })}
                placeholder="Brief summary of the meeting..."
                rows={3}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 text-sm resize-none"
                data-testid="mom-summary"
              />
            </div>

            {/* Discussion Points */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Key Discussion Points</Label>
              {(momData.discussion_points || ['']).map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input 
                    value={item || ''} 
                    onChange={(e) => {
                      const arr = [...(momData.discussion_points || [''])];
                      arr[idx] = e.target.value;
                      setMomData({ ...momData, discussion_points: arr });
                    }}
                    placeholder={`Point ${idx + 1}`} 
                    className="rounded-sm border-zinc-200" 
                  />
                  {(momData.discussion_points || []).length > 1 && (
                    <Button 
                      onClick={() => setMomData({ ...momData, discussion_points: momData.discussion_points.filter((_, i) => i !== idx) })} 
                      variant="ghost" 
                      className="px-2"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
              <Button 
                onClick={() => setMomData({ ...momData, discussion_points: [...(momData.discussion_points || []), ''] })} 
                variant="outline" 
                size="sm" 
                className="rounded-sm"
              >
                <Plus className="w-4 h-4 mr-1" /> Add Point
              </Button>
            </div>

            {/* Client Feedback */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Client Feedback</Label>
              <Input 
                value={momData.client_feedback || ''} 
                onChange={(e) => setMomData({ ...momData, client_feedback: e.target.value })}
                placeholder="What did the client say?"
                className="rounded-sm border-zinc-200"
              />
            </div>

            {/* Next Steps */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Next Steps</Label>
              <Input 
                value={momData.next_steps || ''} 
                onChange={(e) => setMomData({ ...momData, next_steps: e.target.value })}
                placeholder="What's the next action?"
                className="rounded-sm border-zinc-200"
              />
            </div>

            {/* Lead Temperature */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Update Lead Temperature</Label>
              <select 
                value={momData.lead_temperature_update || ''} 
                onChange={(e) => setMomData({ ...momData, lead_temperature_update: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
              >
                <option value="">No change</option>
                <option value="cold">Cold - Low interest</option>
                <option value="warm">Warm - Interested</option>
                <option value="hot">Hot - Ready to proceed</option>
              </select>
            </div>

            <div className="flex justify-end pt-4 border-t border-zinc-200">
              <Button 
                onClick={handleSaveMOM} 
                data-testid="save-sales-mom" 
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Save MOM & Complete Meeting
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SalesMeetings;
