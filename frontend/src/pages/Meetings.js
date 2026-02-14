import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { 
  Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle, 
  FileText, Send, Clock, AlertCircle, Calendar, Trash2, Edit2,
  ChevronDown, ChevronUp, ClipboardList, Mail
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low', color: 'bg-zinc-100 text-zinc-700' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'high', label: 'High', color: 'bg-red-100 text-red-700' }
];

const Meetings = () => {
  const { user } = useContext(AuthContext);
  const [meetings, setMeetings] = useState([]);
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [momDialogOpen, setMomDialogOpen] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [expandedMeetings, setExpandedMeetings] = useState({});
  
  const [formData, setFormData] = useState({
    project_id: '',
    client_id: '',
    lead_id: '',
    meeting_date: '',
    mode: 'online',
    duration_minutes: '',
    notes: '',
    is_delivered: false,
    title: '',
    agenda: [''],
    attendees: [],
    attendee_names: []
  });
  
  const [momData, setMomData] = useState({
    title: '',
    agenda: [''],
    discussion_points: [''],
    decisions_made: [''],
    action_items: [],
    next_meeting_date: ''
  });
  
  const [newActionItem, setNewActionItem] = useState({
    description: '',
    assigned_to_id: '',
    due_date: '',
    priority: 'medium',
    create_follow_up_task: true,
    notify_reporting_manager: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [meetingsRes, projectsRes, clientsRes, leadsRes, usersRes] = await Promise.all([
        axios.get(`${API}/meetings`),
        axios.get(`${API}/projects`),
        axios.get(`${API}/clients`).catch(() => ({ data: [] })),
        axios.get(`${API}/leads`),
        axios.get(`${API}/users`)
      ]);
      
      setMeetings(meetingsRes.data);
      setProjects(projectsRes.data);
      setClients(clientsRes.data);
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
      const meetingData = {
        ...formData,
        meeting_date: new Date(formData.meeting_date).toISOString(),
        duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : null,
        agenda: formData.agenda.filter(a => a.trim())
      };
      
      await axios.post(`${API}/meetings`, meetingData);
      toast.success('Meeting scheduled successfully');
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to schedule meeting');
    }
  };

  const resetForm = () => {
    setFormData({
      project_id: '',
      client_id: '',
      lead_id: '',
      meeting_date: '',
      mode: 'online',
      duration_minutes: '',
      notes: '',
      is_delivered: false,
      title: '',
      agenda: [''],
      attendees: [],
      attendee_names: []
    });
  };

  const openMOMDialog = async (meeting) => {
    try {
      const res = await axios.get(`${API}/meetings/${meeting.id}`);
      const meetingData = res.data;
      
      setSelectedMeeting(meetingData);
      setMomData({
        title: meetingData.title || '',
        agenda: meetingData.agenda?.length ? meetingData.agenda : [''],
        discussion_points: meetingData.discussion_points?.length ? meetingData.discussion_points : [''],
        decisions_made: meetingData.decisions_made?.length ? meetingData.decisions_made : [''],
        action_items: meetingData.action_items || [],
        next_meeting_date: meetingData.next_meeting_date ? meetingData.next_meeting_date.split('T')[0] : ''
      });
      setMomDialogOpen(true);
    } catch (error) {
      toast.error('Failed to load meeting details');
    }
  };

  const handleSaveMOM = async () => {
    try {
      const momPayload = {
        ...momData,
        agenda: momData.agenda.filter(a => a.trim()),
        discussion_points: momData.discussion_points.filter(d => d.trim()),
        decisions_made: momData.decisions_made.filter(d => d.trim()),
        next_meeting_date: momData.next_meeting_date ? new Date(momData.next_meeting_date).toISOString() : null
      };
      
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/mom`, momPayload);
      toast.success('Minutes of Meeting saved');
      fetchData();
    } catch (error) {
      toast.error('Failed to save MOM');
    }
  };

  const handleAddActionItem = async () => {
    if (!newActionItem.description.trim()) {
      toast.error('Action item description is required');
      return;
    }
    
    try {
      const payload = {
        ...newActionItem,
        due_date: newActionItem.due_date ? new Date(newActionItem.due_date).toISOString() : null
      };
      
      const res = await axios.post(`${API}/meetings/${selectedMeeting.id}/action-items`, payload);
      
      toast.success('Action item added');
      
      // Update local state
      setMomData(prev => ({
        ...prev,
        action_items: [...prev.action_items, res.data.action_item]
      }));
      
      // Reset form
      setNewActionItem({
        description: '',
        assigned_to_id: '',
        due_date: '',
        priority: 'medium',
        create_follow_up_task: true,
        notify_reporting_manager: true
      });
      
      fetchData();
    } catch (error) {
      toast.error('Failed to add action item');
    }
  };

  const handleUpdateActionItemStatus = async (actionItemId, status) => {
    try {
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/action-items/${actionItemId}?status=${status}`);
      
      // Update local state
      setMomData(prev => ({
        ...prev,
        action_items: prev.action_items.map(item =>
          item.id === actionItemId ? { ...item, status } : item
        )
      }));
      
      toast.success('Status updated');
      fetchData();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleSendMOMToClient = async () => {
    try {
      const res = await axios.post(`${API}/meetings/${selectedMeeting.id}/send-mom`);
      toast.success(`MOM sent to ${res.data.client_name || res.data.client_email}`);
      fetchData();
      setMomDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send MOM');
    }
  };

  const toggleExpanded = (meetingId) => {
    setExpandedMeetings(prev => ({ ...prev, [meetingId]: !prev[meetingId] }));
  };

  const addArrayItem = (field, setFn, data) => {
    setFn({ ...data, [field]: [...data[field], ''] });
  };

  const updateArrayItem = (field, index, value, setFn, data) => {
    const updated = [...data[field]];
    updated[index] = value;
    setFn({ ...data, [field]: updated });
  };

  const removeArrayItem = (field, index, setFn, data) => {
    if (data[field].length > 1) {
      setFn({ ...data, [field]: data[field].filter((_, i) => i !== index) });
    }
  };

  const getModeIcon = (mode) => {
    switch (mode) {
      case 'online': return <Video className="w-4 h-4" strokeWidth={1.5} />;
      case 'offline': return <UsersIcon className="w-4 h-4" strokeWidth={1.5} />;
      case 'tele_call': return <Phone className="w-4 h-4" strokeWidth={1.5} />;
      default: return <Video className="w-4 h-4" strokeWidth={1.5} />;
    }
  };

  const getModeBadge = (mode) => {
    const badges = {
      online: 'bg-blue-50 text-blue-700',
      offline: 'bg-purple-50 text-purple-700',
      tele_call: 'bg-emerald-50 text-emerald-700',
    };
    return badges[mode] || badges.online;
  };

  const canEdit = user?.role !== 'manager';

  return (
    <div data-testid="meetings-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Meetings & MOM
          </h1>
          <p className="text-zinc-500">Track meetings, create Minutes of Meeting, and manage action items</p>
        </div>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-meeting-button" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Schedule Meeting
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Schedule New Meeting</DialogTitle>
                <DialogDescription className="text-zinc-500">Schedule a meeting with agenda items</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Meeting Title *</Label>
                    <Input
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      placeholder="e.g., Weekly Sync, Project Kickoff"
                      required
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Project *</Label>
                    <select
                      value={formData.project_id}
                      onChange={(e) => {
                        const project = projects.find(p => p.id === e.target.value);
                        setFormData({ 
                          ...formData, 
                          project_id: e.target.value,
                          lead_id: project?.lead_id || ''
                        });
                      }}
                      required
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                    >
                      <option value="">Select a project</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name} - {project.client_name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Client (Optional)</Label>
                    <select
                      value={formData.client_id}
                      onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                    >
                      <option value="">Select client</option>
                      {clients.map((client) => (
                        <option key={client.id} value={client.id}>{client.company_name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Lead (Optional)</Label>
                    <select
                      value={formData.lead_id}
                      onChange={(e) => setFormData({ ...formData, lead_id: e.target.value })}
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                    >
                      <option value="">Select lead</option>
                      {leads.map((lead) => (
                        <option key={lead.id} value={lead.id}>
                          {lead.first_name} {lead.last_name} - {lead.company}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Date & Time *</Label>
                    <Input
                      type="datetime-local"
                      value={formData.meeting_date}
                      onChange={(e) => setFormData({ ...formData, meeting_date: e.target.value })}
                      required
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Mode *</Label>
                    <select
                      value={formData.mode}
                      onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                      required
                      className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                    >
                      <option value="online">Online</option>
                      <option value="offline">Offline (In-person)</option>
                      <option value="tele_call">Tele Call</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Duration (mins)</Label>
                    <Input
                      type="number"
                      min="0"
                      value={formData.duration_minutes}
                      onChange={(e) => setFormData({ ...formData, duration_minutes: e.target.value })}
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                {/* Agenda Items */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Agenda Items</Label>
                  {formData.agenda.map((item, idx) => (
                    <div key={idx} className="flex gap-2">
                      <Input
                        value={item}
                        onChange={(e) => updateArrayItem('agenda', idx, e.target.value, setFormData, formData)}
                        placeholder={`Agenda item ${idx + 1}`}
                        className="rounded-sm border-zinc-200"
                      />
                      {formData.agenda.length > 1 && (
                        <Button type="button" onClick={() => removeArrayItem('agenda', idx, setFormData, formData)} variant="ghost" className="px-2">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      )}
                    </div>
                  ))}
                  <Button type="button" onClick={() => addArrayItem('agenda', setFormData, formData)} variant="outline" size="sm" className="rounded-sm">
                    <Plus className="w-4 h-4 mr-1" /> Add Agenda Item
                  </Button>
                </div>

                {/* Attendees */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Attendees</Label>
                  <select
                    multiple
                    value={formData.attendees}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions, option => option.value);
                      const selectedNames = selected.map(id => {
                        const u = users.find(usr => usr.id === id);
                        return u?.full_name || '';
                      });
                      setFormData({ ...formData, attendees: selected, attendee_names: selectedNames });
                    }}
                    className="w-full h-24 px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm"
                  >
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
                    ))}
                  </select>
                  <p className="text-xs text-zinc-400">Hold Ctrl/Cmd to select multiple</p>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium text-zinc-950">Notes</Label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="is_delivered"
                    checked={formData.is_delivered}
                    onChange={(e) => setFormData({ ...formData, is_delivered: e.target.checked })}
                    className="w-4 h-4 rounded-sm border-zinc-200"
                  />
                  <Label htmlFor="is_delivered" className="text-sm font-medium text-zinc-950">Mark as delivered</Label>
                </div>

                <Button type="submit" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  Schedule Meeting
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading meetings...</div>
        </div>
      ) : meetings.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Calendar className="w-12 h-12 text-zinc-300 mb-4" />
            <p className="text-zinc-500 mb-4">No meetings found</p>
            {canEdit && (
              <Button onClick={() => setDialogOpen(true)} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Schedule Your First Meeting
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {meetings.map((meeting) => {
            const project = projects.find((p) => p.id === meeting.project_id);
            const isExpanded = expandedMeetings[meeting.id];
            const actionItemsCount = meeting.action_items?.length || 0;
            const completedCount = meeting.action_items?.filter(a => a.status === 'completed').length || 0;
            
            return (
              <Card
                key={meeting.id}
                data-testid={`meeting-card-${meeting.id}`}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-sm ${getModeBadge(meeting.mode)}`}>
                          {getModeIcon(meeting.mode)}
                        </div>
                        <div>
                          <div className="font-medium text-zinc-950">
                            {meeting.title || project?.name || 'Meeting'}
                          </div>
                          <div className="text-sm text-zinc-500">
                            {project?.client_name || 'Unknown Client'}
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

                      {/* Expandable Section */}
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-zinc-200 space-y-3">
                          {meeting.agenda?.length > 0 && (
                            <div>
                              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Agenda</div>
                              <ul className="list-disc list-inside text-sm text-zinc-600">
                                {meeting.agenda.map((item, idx) => <li key={idx}>{item}</li>)}
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
                                {meeting.action_items.map((item) => (
                                  <div key={item.id} className={`flex items-center justify-between p-2 rounded-sm border ${item.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-zinc-50 border-zinc-200'}`}>
                                    <div className="flex items-center gap-2">
                                      {item.status === 'completed' ? (
                                        <CheckCircle className="w-4 h-4 text-green-600" />
                                      ) : (
                                        <Circle className="w-4 h-4 text-zinc-400" />
                                      )}
                                      <span className={`text-sm ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-700'}`}>
                                        {item.description}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs text-zinc-500">{item.assigned_to_name || 'Unassigned'}</span>
                                      <span className={`text-xs px-2 py-0.5 rounded-sm ${PRIORITY_OPTIONS.find(p => p.value === item.priority)?.color || ''}`}>
                                        {item.priority}
                                      </span>
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
                        <Button
                          onClick={() => toggleExpanded(meeting.id)}
                          variant="ghost"
                          size="sm"
                          className="text-zinc-500"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </Button>
                        {canEdit && (
                          <Button
                            onClick={() => openMOMDialog(meeting)}
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            data-testid={`mom-btn-${meeting.id}`}
                          >
                            <ClipboardList className="w-4 h-4 mr-1" />
                            MOM
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

      {/* MOM Dialog */}
      <Dialog open={momDialogOpen} onOpenChange={setMomDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Minutes of Meeting
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedMeeting?.title || 'Meeting'} - {selectedMeeting?.meeting_date ? format(new Date(selectedMeeting.meeting_date), 'MMM dd, yyyy') : ''}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Meeting Title */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Meeting Title</Label>
              <Input
                value={momData.title}
                onChange={(e) => setMomData({ ...momData, title: e.target.value })}
                placeholder="Enter meeting title"
                className="rounded-sm border-zinc-200"
              />
            </div>
            
            {/* Agenda */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Agenda</Label>
              {momData.agenda.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={item}
                    onChange={(e) => updateArrayItem('agenda', idx, e.target.value, setMomData, momData)}
                    placeholder={`Agenda item ${idx + 1}`}
                    className="rounded-sm border-zinc-200"
                  />
                  {momData.agenda.length > 1 && (
                    <Button onClick={() => removeArrayItem('agenda', idx, setMomData, momData)} variant="ghost" className="px-2">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
              <Button onClick={() => addArrayItem('agenda', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Agenda
              </Button>
            </div>
            
            {/* Discussion Points */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Discussion Points</Label>
              {momData.discussion_points.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={item}
                    onChange={(e) => updateArrayItem('discussion_points', idx, e.target.value, setMomData, momData)}
                    placeholder={`Discussion point ${idx + 1}`}
                    className="rounded-sm border-zinc-200"
                  />
                  {momData.discussion_points.length > 1 && (
                    <Button onClick={() => removeArrayItem('discussion_points', idx, setMomData, momData)} variant="ghost" className="px-2">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
              <Button onClick={() => addArrayItem('discussion_points', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Discussion Point
              </Button>
            </div>
            
            {/* Decisions Made */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Decisions Made</Label>
              {momData.decisions_made.map((item, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={item}
                    onChange={(e) => updateArrayItem('decisions_made', idx, e.target.value, setMomData, momData)}
                    placeholder={`Decision ${idx + 1}`}
                    className="rounded-sm border-zinc-200"
                  />
                  {momData.decisions_made.length > 1 && (
                    <Button onClick={() => removeArrayItem('decisions_made', idx, setMomData, momData)} variant="ghost" className="px-2">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
              <Button onClick={() => addArrayItem('decisions_made', setMomData, momData)} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Decision
              </Button>
            </div>
            
            {/* Action Items */}
            <div className="space-y-4">
              <Label className="text-sm font-medium text-zinc-950">Action Items</Label>
              
              {/* Existing Action Items */}
              {momData.action_items.length > 0 && (
                <div className="space-y-2">
                  {momData.action_items.map((item) => (
                    <div key={item.id} className={`flex items-center justify-between p-3 rounded-sm border ${item.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-zinc-50 border-zinc-200'}`}>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-700 font-medium'}`}>
                            {item.description}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-sm ${PRIORITY_OPTIONS.find(p => p.value === item.priority)?.color || ''}`}>
                            {item.priority}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500 mt-1">
                          Assigned to: {item.assigned_to_name || 'Unassigned'} | Due: {item.due_date ? format(new Date(item.due_date), 'MMM dd') : 'No date'}
                          {item.follow_up_task_id && <span className="ml-2 text-blue-600">Follow-up task created</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {item.status !== 'completed' && (
                          <Button
                            onClick={() => handleUpdateActionItemStatus(item.id, 'completed')}
                            variant="ghost"
                            size="sm"
                            className="text-green-600 hover:bg-green-50"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Add New Action Item */}
              <div className="p-4 bg-zinc-50 rounded-sm border border-zinc-200 space-y-3">
                <div className="text-sm font-medium text-zinc-700">Add New Action Item</div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <Input
                      value={newActionItem.description}
                      onChange={(e) => setNewActionItem({ ...newActionItem, description: e.target.value })}
                      placeholder="Action item description..."
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <select
                    value={newActionItem.assigned_to_id}
                    onChange={(e) => setNewActionItem({ ...newActionItem, assigned_to_id: e.target.value })}
                    className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Assign to...</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.full_name}</option>
                    ))}
                  </select>
                  <Input
                    type="date"
                    value={newActionItem.due_date}
                    onChange={(e) => setNewActionItem({ ...newActionItem, due_date: e.target.value })}
                    className="rounded-sm border-zinc-200"
                  />
                  <select
                    value={newActionItem.priority}
                    onChange={(e) => setNewActionItem({ ...newActionItem, priority: e.target.value })}
                    className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    {PRIORITY_OPTIONS.map((p) => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm text-zinc-600">
                      <input
                        type="checkbox"
                        checked={newActionItem.create_follow_up_task}
                        onChange={(e) => setNewActionItem({ ...newActionItem, create_follow_up_task: e.target.checked })}
                        className="w-4 h-4 rounded border-zinc-200"
                      />
                      Create Task
                    </label>
                    <label className="flex items-center gap-2 text-sm text-zinc-600">
                      <input
                        type="checkbox"
                        checked={newActionItem.notify_reporting_manager}
                        onChange={(e) => setNewActionItem({ ...newActionItem, notify_reporting_manager: e.target.checked })}
                        className="w-4 h-4 rounded border-zinc-200"
                      />
                      Notify Manager
                    </label>
                  </div>
                </div>
                <Button onClick={handleAddActionItem} variant="outline" className="rounded-sm">
                  <Plus className="w-4 h-4 mr-1" /> Add Action Item
                </Button>
              </div>
            </div>
            
            {/* Next Meeting */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Next Meeting Date</Label>
              <Input
                type="datetime-local"
                value={momData.next_meeting_date}
                onChange={(e) => setMomData({ ...momData, next_meeting_date: e.target.value })}
                className="rounded-sm border-zinc-200 w-64"
              />
            </div>
            
            {/* Actions */}
            <div className="flex justify-between pt-4 border-t border-zinc-200">
              <Button onClick={handleSaveMOM} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Save MOM
              </Button>
              <Button 
                onClick={handleSendMOMToClient} 
                variant="outline" 
                className="rounded-sm"
                disabled={selectedMeeting?.mom_sent_to_client}
              >
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

export default Meetings;
