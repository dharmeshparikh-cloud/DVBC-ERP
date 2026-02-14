import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  ArrowLeft, Calendar, Users, Clock, MapPin, Link as LinkIcon, 
  CheckCircle, Lock, Plus, Trash2, FileText, AlertTriangle,
  Video, Building, Phone
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { formatINR } from '../utils/currency';

const SOW_CATEGORIES = [
  { value: 'sales', label: 'Sales' },
  { value: 'hr', label: 'HR' },
  { value: 'operations', label: 'Operations' },
  { value: 'training', label: 'Training' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'digital_marketing', label: 'Digital Marketing' }
];

const KickoffMeeting = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [project, setProject] = useState(null);
  const [agreement, setAgreement] = useState(null);
  const [quotation, setQuotation] = useState(null);
  const [pricingPlan, setPricingPlan] = useState(null);
  const [lead, setLead] = useState(null);
  const [kickoffMeeting, setKickoffMeeting] = useState(null);
  const [sowEntries, setSowEntries] = useState([]);
  const [consultants, setConsultants] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [sowDialogOpen, setSowDialogOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  
  const [meetingForm, setMeetingForm] = useState({
    meeting_date: '',
    meeting_time: '',
    meeting_mode: 'online',
    location: '',
    meeting_link: '',
    agenda: '',
    principal_consultant_id: '',
    attendee_ids: []
  });
  
  const [sowItemForm, setSowItemForm] = useState({
    title: '',
    description: '',
    deliverables: [''],
    timeline_weeks: ''
  });

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      // Get project
      const projectRes = await axios.get(`${API}/projects/${projectId}`);
      setProject(projectRes.data);
      
      // Get kickoff meeting if exists
      const meetingRes = await axios.get(`${API}/kickoff-meetings?project_id=${projectId}`);
      if (meetingRes.data.length > 0) {
        setKickoffMeeting(meetingRes.data[0]);
        
        // Get full meeting details with SOW
        const detailRes = await axios.get(`${API}/kickoff-meetings/${meetingRes.data[0].id}`);
        setAgreement(detailRes.data.agreement);
        setQuotation(detailRes.data.quotation);
        setPricingPlan(detailRes.data.pricing_plan);
        setLead(detailRes.data.lead);
        setSowEntries(detailRes.data.sow || []);
      } else {
        // Get agreement from project
        if (projectRes.data.agreement_id) {
          const agreementRes = await axios.get(`${API}/agreements/${projectRes.data.agreement_id}`);
          setAgreement(agreementRes.data);
        }
      }
      
      // Get SOW entries
      const sowRes = await axios.get(`${API}/projects/${projectId}/sow`);
      setSowEntries(sowRes.data || []);
      
      // Get consultants for dropdown
      const consultantsRes = await axios.get(`${API}/consultants`);
      setConsultants(consultantsRes.data || []);
      
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleMeeting = async (e) => {
    e.preventDefault();
    
    if (!meetingForm.principal_consultant_id) {
      toast.error('Please select a Principal Consultant');
      return;
    }
    
    try {
      const meetingData = {
        project_id: projectId,
        agreement_id: agreement?.id || project?.agreement_id,
        meeting_date: new Date(meetingForm.meeting_date).toISOString(),
        meeting_time: meetingForm.meeting_time,
        meeting_mode: meetingForm.meeting_mode,
        location: meetingForm.location || null,
        meeting_link: meetingForm.meeting_link || null,
        agenda: meetingForm.agenda || null,
        principal_consultant_id: meetingForm.principal_consultant_id,
        attendee_ids: meetingForm.attendee_ids
      };
      
      await axios.post(`${API}/kickoff-meetings`, meetingData);
      toast.success('Kick-off meeting scheduled! SOW has been frozen.');
      setScheduleDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to schedule meeting');
    }
  };

  const handleCreateSOWCategory = async (category) => {
    try {
      await axios.post(`${API}/projects/${projectId}/sow`, {
        project_id: projectId,
        agreement_id: agreement?.id,
        category: category,
        items: []
      });
      toast.success(`${category} SOW created`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create SOW');
    }
  };

  const handleAddSOWItem = async (sowId) => {
    if (!sowItemForm.title.trim()) {
      toast.error('Title is required');
      return;
    }
    
    try {
      await axios.post(`${API}/projects/${projectId}/sow/${sowId}/items`, {
        title: sowItemForm.title,
        description: sowItemForm.description,
        deliverables: sowItemForm.deliverables.filter(d => d.trim()),
        timeline_weeks: sowItemForm.timeline_weeks ? parseInt(sowItemForm.timeline_weeks) : null
      });
      toast.success('SOW item added');
      setSowDialogOpen(false);
      resetSOWForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add SOW item');
    }
  };

  const handleDeleteSOWItem = async (sowId, itemId) => {
    if (!window.confirm('Delete this SOW item?')) return;
    
    try {
      await axios.delete(`${API}/projects/${projectId}/sow/${sowId}/items/${itemId}`);
      toast.success('SOW item deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete item');
    }
  };

  const handleCompleteMeeting = async () => {
    try {
      await axios.patch(`${API}/kickoff-meetings/${kickoffMeeting.id}/complete`);
      toast.success('Meeting marked as completed');
      fetchData();
    } catch (error) {
      toast.error('Failed to complete meeting');
    }
  };

  const resetSOWForm = () => {
    setSowItemForm({
      title: '',
      description: '',
      deliverables: [''],
      timeline_weeks: ''
    });
  };

  const addDeliverable = () => {
    setSowItemForm({
      ...sowItemForm,
      deliverables: [...sowItemForm.deliverables, '']
    });
  };

  const updateDeliverable = (index, value) => {
    const newDeliverables = [...sowItemForm.deliverables];
    newDeliverables[index] = value;
    setSowItemForm({ ...sowItemForm, deliverables: newDeliverables });
  };

  const removeDeliverable = (index) => {
    setSowItemForm({
      ...sowItemForm,
      deliverables: sowItemForm.deliverables.filter((_, i) => i !== index)
    });
  };

  const isFrozen = kickoffMeeting?.sow_frozen || sowEntries.some(s => s.is_frozen);
  const canEditSOW = !isFrozen || user?.role === 'admin';

  const getMeetingModeIcon = (mode) => {
    switch(mode) {
      case 'online': return <Video className="w-4 h-4" />;
      case 'offline': return <Building className="w-4 h-4" />;
      default: return <Phone className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div data-testid="kickoff-meeting-page">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/projects')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Projects
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Kick-off Meeting
            </h1>
            <p className="text-zinc-500">{project?.name} - {project?.client_name}</p>
          </div>
          {!kickoffMeeting && (
            <Button
              onClick={() => setScheduleDialogOpen(true)}
              data-testid="schedule-kickoff-btn"
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Calendar className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Schedule Kick-off
            </Button>
          )}
        </div>
      </div>

      {/* SOW Freeze Alert */}
      {isFrozen && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-center gap-3">
          <Lock className="w-5 h-5 text-amber-600" />
          <div>
            <div className="font-medium text-amber-800">SOW is Frozen</div>
            <div className="text-sm text-amber-600">
              Kick-off meeting has been scheduled. {user?.role === 'admin' ? 'As Admin, you can still edit.' : 'Only Admin can modify the SOW.'}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Meeting Details */}
        <div className="lg:col-span-1 space-y-6">
          {/* Meeting Card */}
          {kickoffMeeting ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-500 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  Meeting Scheduled
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
                  <div>
                    <div className="font-medium">{format(new Date(kickoffMeeting.meeting_date), 'EEEE, MMMM d, yyyy')}</div>
                    {kickoffMeeting.meeting_time && (
                      <div className="text-sm text-zinc-500">{kickoffMeeting.meeting_time}</div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  {getMeetingModeIcon(kickoffMeeting.meeting_mode)}
                  <span className="capitalize">{kickoffMeeting.meeting_mode}</span>
                </div>
                
                {kickoffMeeting.location && (
                  <div className="flex items-center gap-3">
                    <MapPin className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
                    <span>{kickoffMeeting.location}</span>
                  </div>
                )}
                
                {kickoffMeeting.meeting_link && (
                  <div className="flex items-center gap-3">
                    <LinkIcon className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
                    <a href={kickoffMeeting.meeting_link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate">
                      {kickoffMeeting.meeting_link}
                    </a>
                  </div>
                )}
                
                {/* Attendees */}
                <div className="pt-3 border-t border-zinc-200">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-3">Attendees</div>
                  <div className="space-y-2">
                    {kickoffMeeting.attendees?.map((attendee, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium">{attendee.name}</div>
                          <div className="text-xs text-zinc-500 capitalize">{attendee.role.replace('_', ' ')}</div>
                        </div>
                        {attendee.is_required && (
                          <span className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm">Required</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                
                {kickoffMeeting.status !== 'completed' && (
                  <Button
                    onClick={handleCompleteMeeting}
                    className="w-full bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark as Completed
                  </Button>
                )}
                
                {kickoffMeeting.status === 'completed' && (
                  <div className="p-3 bg-emerald-50 text-emerald-700 rounded-sm text-center text-sm font-medium">
                    Meeting Completed
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="py-8 text-center">
                <Calendar className="w-12 h-12 text-zinc-300 mx-auto mb-4" strokeWidth={1} />
                <p className="text-zinc-500 mb-4">No kick-off meeting scheduled</p>
                <Button
                  onClick={() => setScheduleDialogOpen(true)}
                  className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  Schedule Meeting
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Agreement Summary Card */}
          {agreement && (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-500">
                  Agreement Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Agreement #</span>
                  <span className="font-medium">{agreement.agreement_number}</span>
                </div>
                {quotation && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Total Value</span>
                      <span className="font-medium">{formatINR(quotation.final_amount || quotation.total_amount)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Duration</span>
                      <span className="font-medium">{quotation.duration_months} months</span>
                    </div>
                  </>
                )}
                {lead && (
                  <div className="pt-3 border-t border-zinc-200">
                    <div className="text-zinc-500 mb-1">Client</div>
                    <div className="font-medium">{lead.first_name} {lead.last_name}</div>
                    <div className="text-zinc-500">{lead.company}</div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - SOW */}
        <div className="lg:col-span-2">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg font-semibold uppercase tracking-tight text-zinc-950">
                Scope of Work (SOW)
              </CardTitle>
              {isFrozen && <Lock className="w-4 h-4 text-amber-500" />}
            </CardHeader>
            <CardContent>
              {/* Category Tabs/Sections */}
              <div className="space-y-6">
                {SOW_CATEGORIES.map(category => {
                  const sowEntry = sowEntries.find(s => s.category === category.value);
                  
                  return (
                    <div key={category.value} className="border border-zinc-200 rounded-sm">
                      <div className="flex items-center justify-between px-4 py-3 bg-zinc-50">
                        <h3 className="font-medium text-zinc-950">{category.label}</h3>
                        <div className="flex items-center gap-2">
                          {sowEntry?.is_frozen && <Lock className="w-3 h-3 text-amber-500" />}
                          {sowEntry ? (
                            <span className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 rounded-sm">
                              {sowEntry.items?.length || 0} items
                            </span>
                          ) : (
                            canEditSOW && (
                              <Button
                                onClick={() => handleCreateSOWCategory(category.value)}
                                variant="ghost"
                                size="sm"
                                className="text-xs"
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                Add Category
                              </Button>
                            )
                          )}
                        </div>
                      </div>
                      
                      {sowEntry && (
                        <div className="p-4">
                          {sowEntry.items?.length === 0 ? (
                            <div className="text-center py-4 text-zinc-400 text-sm">
                              No scope items defined
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {sowEntry.items?.map((item, idx) => (
                                <div key={item.id} className="p-3 border border-zinc-100 rounded-sm">
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <div className="font-medium text-zinc-950">{idx + 1}. {item.title}</div>
                                      {item.description && (
                                        <div className="text-sm text-zinc-500 mt-1">{item.description}</div>
                                      )}
                                      {item.deliverables?.length > 0 && (
                                        <div className="mt-2">
                                          <div className="text-xs uppercase tracking-wide text-zinc-400 mb-1">Deliverables</div>
                                          <ul className="text-sm text-zinc-600 list-disc list-inside">
                                            {item.deliverables.map((d, i) => (
                                              <li key={i}>{d}</li>
                                            ))}
                                          </ul>
                                        </div>
                                      )}
                                      {item.timeline_weeks && (
                                        <div className="mt-2 text-xs text-zinc-500">
                                          Timeline: {item.timeline_weeks} weeks
                                        </div>
                                      )}
                                    </div>
                                    {canEditSOW && (
                                      <Button
                                        onClick={() => handleDeleteSOWItem(sowEntry.id, item.id)}
                                        variant="ghost"
                                        size="sm"
                                        className="text-red-500 hover:text-red-700"
                                      >
                                        <Trash2 className="w-4 h-4" />
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {canEditSOW && (
                            <Button
                              onClick={() => {
                                setSelectedCategory(sowEntry);
                                setSowDialogOpen(true);
                              }}
                              variant="outline"
                              size="sm"
                              className="mt-3 w-full rounded-sm"
                            >
                              <Plus className="w-4 h-4 mr-2" />
                              Add Scope Item
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Schedule Meeting Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Schedule Kick-off Meeting
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              <AlertTriangle className="w-4 h-4 inline mr-1 text-amber-500" />
              Scheduling will freeze the SOW. Ensure all scope items are added before scheduling.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleScheduleMeeting} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={meetingForm.meeting_date}
                  onChange={(e) => setMeetingForm({ ...meetingForm, meeting_date: e.target.value })}
                  required
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <Label>Time</Label>
                <Input
                  type="time"
                  value={meetingForm.meeting_time}
                  onChange={(e) => setMeetingForm({ ...meetingForm, meeting_time: e.target.value })}
                  className="rounded-sm"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Meeting Mode</Label>
              <select
                value={meetingForm.meeting_mode}
                onChange={(e) => setMeetingForm({ ...meetingForm, meeting_mode: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="online">Online</option>
                <option value="offline">Offline</option>
                <option value="mixed">Mixed (Hybrid)</option>
              </select>
            </div>
            
            {meetingForm.meeting_mode === 'online' || meetingForm.meeting_mode === 'mixed' ? (
              <div className="space-y-2">
                <Label>Meeting Link</Label>
                <Input
                  type="url"
                  value={meetingForm.meeting_link}
                  onChange={(e) => setMeetingForm({ ...meetingForm, meeting_link: e.target.value })}
                  placeholder="https://meet.google.com/..."
                  className="rounded-sm"
                />
              </div>
            ) : null}
            
            {meetingForm.meeting_mode === 'offline' || meetingForm.meeting_mode === 'mixed' ? (
              <div className="space-y-2">
                <Label>Location</Label>
                <Input
                  value={meetingForm.location}
                  onChange={(e) => setMeetingForm({ ...meetingForm, location: e.target.value })}
                  placeholder="Meeting location"
                  className="rounded-sm"
                />
              </div>
            ) : null}
            
            <div className="space-y-2">
              <Label>Principal Consultant *</Label>
              <select
                value={meetingForm.principal_consultant_id}
                onChange={(e) => setMeetingForm({ ...meetingForm, principal_consultant_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="">Select Principal Consultant</option>
                {consultants.map(c => (
                  <option key={c.id} value={c.id}>{c.full_name}</option>
                ))}
              </select>
            </div>
            
            <div className="space-y-2">
              <Label>Additional Consultants</Label>
              <select
                multiple
                value={meetingForm.attendee_ids}
                onChange={(e) => setMeetingForm({ 
                  ...meetingForm, 
                  attendee_ids: Array.from(e.target.selectedOptions, option => option.value)
                })}
                className="w-full h-24 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                {consultants
                  .filter(c => c.id !== meetingForm.principal_consultant_id)
                  .map(c => (
                    <option key={c.id} value={c.id}>{c.full_name}</option>
                  ))
                }
              </select>
              <p className="text-xs text-zinc-400">Hold Ctrl/Cmd to select multiple</p>
            </div>
            
            <div className="space-y-2">
              <Label>Agenda</Label>
              <textarea
                value={meetingForm.agenda}
                onChange={(e) => setMeetingForm({ ...meetingForm, agenda: e.target.value })}
                rows={3}
                placeholder="Meeting agenda..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950"
              />
            </div>
            
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Calendar className="w-4 h-4 mr-2" />
              Schedule & Freeze SOW
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add SOW Item Dialog */}
      <Dialog open={sowDialogOpen} onOpenChange={setSowDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Add Scope Item
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedCategory?.category && SOW_CATEGORIES.find(c => c.value === selectedCategory.category)?.label} Category
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Title *</Label>
              <Input
                value={sowItemForm.title}
                onChange={(e) => setSowItemForm({ ...sowItemForm, title: e.target.value })}
                placeholder="Scope item title"
                className="rounded-sm"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                value={sowItemForm.description}
                onChange={(e) => setSowItemForm({ ...sowItemForm, description: e.target.value })}
                rows={3}
                placeholder="Detailed description..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Deliverables</Label>
              {sowItemForm.deliverables.map((d, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={d}
                    onChange={(e) => updateDeliverable(idx, e.target.value)}
                    placeholder={`Deliverable ${idx + 1}`}
                    className="rounded-sm"
                  />
                  {sowItemForm.deliverables.length > 1 && (
                    <Button
                      type="button"
                      onClick={() => removeDeliverable(idx)}
                      variant="ghost"
                      size="sm"
                      className="text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                onClick={addDeliverable}
                variant="outline"
                size="sm"
                className="rounded-sm"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Deliverable
              </Button>
            </div>
            
            <div className="space-y-2">
              <Label>Timeline (weeks)</Label>
              <Input
                type="number"
                min="1"
                value={sowItemForm.timeline_weeks}
                onChange={(e) => setSowItemForm({ ...sowItemForm, timeline_weeks: e.target.value })}
                placeholder="e.g., 4"
                className="rounded-sm"
              />
            </div>
            
            <Button
              onClick={() => handleAddSOWItem(selectedCategory?.id)}
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Add Scope Item
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KickoffMeeting;
