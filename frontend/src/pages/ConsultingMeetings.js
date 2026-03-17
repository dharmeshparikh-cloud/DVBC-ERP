import React, { useState, useContext, useMemo } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import PageHeader from '../components/ui/page-header';
import MeetingLocationPicker from '../components/MeetingLocationPicker';
import {
  Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle,
  FileText, Send, Calendar, Trash2, ChevronDown, ChevronUp,
  ClipboardList, Mail, BarChart3, Target, Car, MapPin, DollarSign,
  Filter, Building2, CalendarDays, Paperclip, Upload, X, List, LayoutGrid,
  Printer, Eye, Clock, User, Hash, Layers, AlertCircle, Search, CheckSquare
} from 'lucide-react';
import { toast } from 'sonner';
import { format, startOfMonth, endOfMonth, isWithinInterval, parseISO } from 'date-fns';

// Travel modes with expense rates
const TRAVEL_MODES = [
  { id: 'DRIVING', label: 'Car', rate: 7 },
  { id: 'TWO_WHEELER', label: 'Bike', rate: 3 },
  { id: 'TRANSIT', label: 'Transit', rate: 0 },
  { id: 'ACCOMPANIED', label: 'Accompanied', rate: 0 }
];

const CONSULTING_ROLES = ['admin', 'project_manager', 'consultant', 'principal_consultant',
  'lean_consultant', 'lead_consultant', 'senior_consultant', 'subject_matter_expert', 'manager'];

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low', color: 'bg-zinc-100 text-zinc-700' },
  { value: 'medium', label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'high', label: 'High', color: 'bg-red-100 text-red-700' }
];

const ConsultingMeetings = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [sows, setSows] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [momDialogOpen, setMomDialogOpen] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [expandedMeetings, setExpandedMeetings] = useState({});
  const [activeTab, setActiveTab] = useState('meetings');
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'card'
  const [detailDialogOpen, setDetailDialogOpen] = useState(false); // Meeting detail view

  // Filter state
  const [filters, setFilters] = useState({
    project_id: 'all', // Project filter (auto-sets date range)
    client_id: 'all',
    month: 'all', // Format: 'YYYY-MM' or 'all'
    status: 'all', // 'all', 'pending', 'delivered', 'with_mom'
    date_from: '', // Start date filter
    date_to: '' // End date filter
  });

  // MOM Attachments state
  const [momAttachments, setMomAttachments] = useState([]);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);

  // Travel expense state
  const [addTravelExpense, setAddTravelExpense] = useState(false);
  const [travelData, setTravelData] = useState({
    start_location: '',
    end_location: '',
    travel_mode: 'DRIVING',
    distance_km: 0,
    is_round_trip: true,
    transit_amount: 0
  });

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

  // SOW Scopes state for meeting linkage
  const [availableScopes, setAvailableScopes] = useState([]);
  const [selectedScopeIds, setSelectedScopeIds] = useState([]);
  const [loadingScopes, setLoadingScopes] = useState(false);
  
  // Scope filter state for large scope lists
  const [scopeSearchQuery, setScopeSearchQuery] = useState('');
  const [scopeStatusFilter, setScopeStatusFilter] = useState('all'); // all, in_progress, not_started, completed

  const canEdit = CONSULTING_ROLES.includes(user?.role) && user?.role !== 'manager';

  // Check if user can record MOM for this meeting (must be in project team)
  const canRecordMOM = (meeting) => {
    if (!meeting || !user) return false;
    // Admin and Principal Consultant can always record
    if (['admin', 'principal_consultant'].includes(user.role)) return true;
    // Check if user is in project team
    const projectTeam = meeting.project_team || [];
    return projectTeam.some(t => t.user_id === user.id || t.employee_id === user.employee_id);
  };

  // Check if meeting is offline (can claim travel)
  const isOfflineMeeting = (meeting) => {
    return meeting?.mode === 'offline' || meeting?.mode === 'client_site';
  };

  // Calculate travel expense amount
  const calculateTravelExpense = () => {
    if (travelData.travel_mode === 'ACCOMPANIED') return 0;
    if (travelData.travel_mode === 'TRANSIT') return parseFloat(travelData.transit_amount) || 0;
    
    const rate = TRAVEL_MODES.find(m => m.id === travelData.travel_mode)?.rate || 0;
    const distance = parseFloat(travelData.distance_km) || 0;
    const multiplier = travelData.is_round_trip ? 2 : 1;
    return distance * multiplier * rate;
  };

  // React Query: Meetings
  const { data: meetings = [], isLoading: loading, refetch: refetchMeetings } = useQuery({
    queryKey: ['meetings', 'consulting'],
    queryFn: async () => {
      const res = await axios.get(`${API}/meetings?meeting_type=consulting`);
      return res.data || [];
    },
    staleTime: 2 * 60 * 1000,
  });

  // React Query: Projects
  const { data: projects = [] } = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: Clients
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/clients`);
      // API returns {items: [], total, skip, limit} - extract items array
      const data = res.data;
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: Users
  const { data: users = [] } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await axios.get(`${API}/users`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: Tracking
  const { data: tracking = [] } = useQuery({
    queryKey: ['consulting-meetings', 'tracking'],
    queryFn: async () => {
      const res = await axios.get(`${API}/consulting-meetings/tracking`);
      return res.data || [];
    },
    staleTime: 2 * 60 * 1000,
  });

  // Filtered meetings with memoization
  const filteredMeetings = useMemo(() => {
    let result = [...meetings];
    
    // Filter by project
    if (filters.project_id !== 'all') {
      result = result.filter(m => m.project_id === filters.project_id);
    }
    
    // Filter by client
    if (filters.client_id !== 'all') {
      result = result.filter(m => m.client_id === filters.client_id);
    }
    
    // Filter by month
    if (filters.month !== 'all') {
      const [year, month] = filters.month.split('-').map(Number);
      const monthStart = startOfMonth(new Date(year, month - 1));
      const monthEnd = endOfMonth(new Date(year, month - 1));
      result = result.filter(m => {
        try {
          const meetingDate = parseISO(m.meeting_date);
          return isWithinInterval(meetingDate, { start: monthStart, end: monthEnd });
        } catch {
          return false;
        }
      });
    }
    
    // Filter by status
    if (filters.status !== 'all') {
      if (filters.status === 'pending') {
        result = result.filter(m => !m.is_delivered);
      } else if (filters.status === 'delivered') {
        result = result.filter(m => m.is_delivered);
      } else if (filters.status === 'with_mom') {
        result = result.filter(m => m.mom_generated);
      }
    }

    // Filter by date range
    if (filters.date_from) {
      const fromDate = new Date(filters.date_from);
      fromDate.setHours(0, 0, 0, 0);
      result = result.filter(m => {
        try {
          const meetingDate = new Date(m.meeting_date);
          return meetingDate >= fromDate;
        } catch {
          return false;
        }
      });
    }
    if (filters.date_to) {
      const toDate = new Date(filters.date_to);
      toDate.setHours(23, 59, 59, 999);
      result = result.filter(m => {
        try {
          const meetingDate = new Date(m.meeting_date);
          return meetingDate <= toDate;
        } catch {
          return false;
        }
      });
    }
    
    // Sort by date descending
    result.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date));
    
    return result;
  }, [meetings, filters]);

  // Get unique clients from meetings
  const uniqueClients = useMemo(() => {
    const clientMap = new Map();
    meetings.forEach(m => {
      if (m.client_id) {
        const client = clients.find(c => c.id === m.client_id);
        if (client) {
          clientMap.set(m.client_id, client.company_name || client.name || 'Unknown');
        }
      }
    });
    return Array.from(clientMap.entries()).map(([id, name]) => ({ id, name }));
  }, [meetings, clients]);

  // Get unique projects from meetings with date range
  const uniqueProjects = useMemo(() => {
    const projectMap = new Map();
    meetings.forEach(m => {
      if (m.project_id) {
        const project = projects.find(p => p.id === m.project_id);
        if (project && !projectMap.has(m.project_id)) {
          projectMap.set(m.project_id, {
            id: m.project_id,
            name: project.name || project.project_name || m.project_name || 'Unknown Project',
            client_name: m.client_name || project.client_name || '',
            start_date: project.start_date,
            end_date: project.end_date
          });
        }
      }
    });
    return Array.from(projectMap.values());
  }, [meetings, projects]);

  // Handle project filter change - auto-set date range
  const handleProjectFilterChange = (projectId) => {
    if (projectId === 'all') {
      setFilters(f => ({ ...f, project_id: 'all', date_from: '', date_to: '' }));
    } else {
      const project = uniqueProjects.find(p => p.id === projectId);
      if (project) {
        const dateFrom = project.start_date ? format(new Date(project.start_date), 'yyyy-MM-dd') : '';
        const dateTo = project.end_date ? format(new Date(project.end_date), 'yyyy-MM-dd') : '';
        setFilters(f => ({ ...f, project_id: projectId, date_from: dateFrom, date_to: dateTo }));
      }
    }
  };

  // Get unique months from meetings
  const uniqueMonths = useMemo(() => {
    const monthSet = new Set();
    meetings.forEach(m => {
      try {
        const date = parseISO(m.meeting_date);
        monthSet.add(format(date, 'yyyy-MM'));
      } catch {}
    });
    return Array.from(monthSet).sort().reverse().map(m => ({
      value: m,
      label: format(parseISO(m + '-01'), 'MMMM yyyy')
    }));
  }, [meetings]);

  // Handle file upload for MOM attachments
  const handleAttachmentUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    
    setUploadingAttachment(true);
    try {
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      
      const res = await axios.post(`${API}/upload/meeting-attachments`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const uploadedFiles = res.data?.files || res.data || [];
      setMomAttachments(prev => [...prev, ...uploadedFiles.map(f => ({
        name: f.filename || f.name,
        url: f.url || f.path,
        size: f.size
      }))]);
      toast.success(`${files.length} file(s) uploaded`);
    } catch (error) {
      // If upload endpoint doesn't exist, store locally for now
      const localFiles = files.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type,
        local: true
      }));
      setMomAttachments(prev => [...prev, ...localFiles]);
      toast.info('Files attached (will be uploaded on save)');
    } finally {
      setUploadingAttachment(false);
    }
  };

  const removeAttachment = (index) => {
    setMomAttachments(prev => prev.filter((_, i) => i !== index));
  };

  // Mutation: Create Meeting
  const createMeetingMutation = useMutation({
    mutationFn: async (data) => {
      await axios.post(`${API}/meetings`, {
        ...data, type: 'consulting',
        meeting_date: new Date(data.meeting_date).toISOString(),
        duration_minutes: data.duration_minutes ? parseInt(data.duration_minutes) : null,
        agenda: data.agenda.filter(a => a.trim())
      });
    },
    onSuccess: () => {
      toast.success('Consulting meeting created');
      setDialogOpen(false);
      setFormData({ title: '', project_id: '', client_id: '', sow_id: '', meeting_date: '', mode: 'online', duration_minutes: '', notes: '', is_delivered: false, agenda: [''], attendees: [], attendee_names: [] });
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create meeting');
    },
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    createMeetingMutation.mutate(formData);
  };

  // Open meeting detail view (printable)
  const openMeetingDetail = async (meeting) => {
    try {
      const res = await axios.get(`${API}/meetings/${meeting.id}`);
      setSelectedMeeting(res.data);
      setDetailDialogOpen(true);
    } catch { toast.error('Failed to load meeting details'); }
  };

  // Get meeting series number (count of meetings for same project before this one)
  const getMeetingSeriesNumber = (meeting) => {
    const projectMeetings = meetings
      .filter(m => m.project_id === meeting.project_id)
      .sort((a, b) => new Date(a.meeting_date) - new Date(b.meeting_date));
    return projectMeetings.findIndex(m => m.id === meeting.id) + 1;
  };

  // Get project stats
  const getProjectStats = (meeting) => {
    const project = projects.find(p => p.id === meeting.project_id);
    if (!project) return { committed: 0, delivered: 0, pending: 0 };
    const committed = project.total_meetings_committed || 0;
    const delivered = project.total_meetings_delivered || 0;
    return { committed, delivered, pending: committed - delivered };
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
      // Reset and load existing attachments
      setMomAttachments(m.mom_attachments || []);
      // Load existing scope selections
      setSelectedScopeIds(m.sow_scope_ids || []);
      // Reset scope filters
      setScopeSearchQuery('');
      setScopeStatusFilter('all');
      
      // Fetch available scopes for this project (committed from sales + additional)
      if (m.project_id) {
        setLoadingScopes(true);
        try {
          const sowRes = await axios.get(`${API}/enhanced-sow/project/${m.project_id}/scopes-for-meeting`);
          if (sowRes.data?.has_sow) {
            setAvailableScopes(sowRes.data.scopes || []);
          } else {
            setAvailableScopes([]);
            // Show info message if no SOW
            if (sowRes.data?.message) {
              toast.info(sowRes.data.message);
            }
          }
        } catch {
          setAvailableScopes([]);
        }
        setLoadingScopes(false);
      } else {
        setAvailableScopes([]);
        toast.warning('No project linked to this meeting. SOW scopes cannot be selected.');
      }
      
      setMomDialogOpen(true);
    } catch { toast.error('Failed to load meeting'); }
  };

  const handleSaveMOM = async () => {
    // Validation: At least one scope must be selected if project has SOW
    if (selectedMeeting?.project_id && availableScopes.length > 0 && selectedScopeIds.length === 0) {
      toast.error('Please select at least one SOW scope. This is mandatory for MOM.');
      return;
    }
    
    try {
      // Prepare scope details for denormalization
      const scopeDetails = availableScopes
        .filter(s => selectedScopeIds.includes(s.id))
        .map(s => ({ id: s.id, name: s.name }));
      
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/mom`, {
        ...momData,
        agenda: momData.agenda.filter(a => a.trim()),
        discussion_points: momData.discussion_points.filter(d => d.trim()),
        decisions_made: momData.decisions_made.filter(d => d.trim()),
        next_meeting_date: momData.next_meeting_date ? new Date(momData.next_meeting_date).toISOString() : null,
        mom_attachments: momAttachments,
        sow_scope_ids: selectedScopeIds,
        sow_scopes: scopeDetails
      });
      toast.success('Consulting MOM saved');
      // Reset scope filters
      setScopeSearchQuery('');
      setScopeStatusFilter('all');
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
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
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
    } catch { toast.error('Failed to add action item'); }
  };

  const handleUpdateActionItemStatus = async (actionItemId, status) => {
    try {
      await axios.patch(`${API}/meetings/${selectedMeeting.id}/action-items/${actionItemId}?status=${status}`);
      setMomData(prev => ({ ...prev, action_items: prev.action_items.map(i => i.id === actionItemId ? { ...i, status } : i) }));
      toast.success('Status updated');
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
    } catch { toast.error('Failed to update'); }
  };

  const handleSendMOM = async () => {
    try {
      const res = await axios.post(`${API}/meetings/${selectedMeeting.id}/send-mom`);
      toast.success(`MOM sent to ${res.data.client_name || res.data.client_email}`);
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
      setMomDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send MOM');
    }
  };

  // Complete meeting and auto-send MOM
  const handleCompleteMeeting = async () => {
    if (!selectedMeeting?.mom_generated) {
      toast.error('Please save MOM first before completing the meeting');
      return;
    }
    try {
      const res = await axios.post(`${API}/meeting-schedules/meetings/${selectedMeeting.id}/complete-and-send`);
      toast.success(`Meeting completed! MOM sent to ${res.data.mom_sent?.sent_to || 'client'}`);
      if (res.data.next_meeting) {
        toast.info(`Next recurring meeting scheduled for ${res.data.next_meeting.meeting_date?.slice(0, 10)}`);
      }
      queryClient.invalidateQueries({ queryKey: ['meetings', 'consulting'] });
      setMomDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete meeting');
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
      <PageHeader
        title="Consulting Meetings"
        subtitle="Manage client project meetings, MOM, and track commitments"
        onRefresh={() => refetchMeetings()}
        loading={loading}
        actions={canEdit && (
          <Button onClick={() => setDialogOpen(true)} data-testid="add-consulting-meeting-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
            <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> New Consulting Meeting
          </Button>
        )}
      />
      {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
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
          {/* Filters */}
          <Card className="border-zinc-200 shadow-none rounded-sm mb-6">
            <CardContent className="p-4">
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-zinc-500" />
                  <span className="text-sm font-medium text-zinc-700">Filters:</span>
                </div>
                
                {/* Project Filter (Company) - Auto-sets date range */}
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-zinc-400" />
                  <Select value={filters.project_id} onValueChange={handleProjectFilterChange}>
                    <SelectTrigger className="w-[200px] h-9 text-sm">
                      <SelectValue placeholder="All Projects (Company)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Projects</SelectItem>
                      {uniqueProjects.map(p => (
                        <SelectItem key={p.id} value={p.id}>
                          <div className="flex flex-col">
                            <span>{p.name}</span>
                            {p.client_name && <span className="text-xs text-zinc-400">{p.client_name}</span>}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Client Filter (Contact/Owner) */}
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-zinc-400" />
                  <Select value={filters.client_id} onValueChange={(v) => setFilters(f => ({ ...f, client_id: v }))}>
                    <SelectTrigger className="w-[180px] h-9 text-sm">
                      <SelectValue placeholder="All Companies" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Companies</SelectItem>
                      {uniqueClients.map(c => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Status Filter */}
                <div className="flex items-center gap-2">
                  <Select value={filters.status} onValueChange={(v) => setFilters(f => ({ ...f, status: v }))}>
                    <SelectTrigger className="w-[140px] h-9 text-sm">
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="delivered">Delivered</SelectItem>
                      <SelectItem value="with_mom">With MOM</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Date Range Filter (Project Duration) */}
                <div className="flex items-center gap-2 border-l border-zinc-200 pl-4">
                  <span className="text-xs text-zinc-500 font-medium">Duration:</span>
                  <Input 
                    type="date" 
                    value={filters.date_from}
                    onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))}
                    className="w-[130px] h-9 text-sm"
                    title="Project Start Date"
                  />
                  <span className="text-xs text-zinc-400">to</span>
                  <Input 
                    type="date" 
                    value={filters.date_to}
                    onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))}
                    className="w-[130px] h-9 text-sm"
                    title="Project End Date"
                  />
                </div>

                {/* View Toggle */}
                <div className="flex items-center gap-1 ml-auto border border-zinc-200 rounded-sm p-1">
                  <Button 
                    variant={viewMode === 'list' ? 'secondary' : 'ghost'} 
                    size="sm" 
                    className="h-7 px-2"
                    onClick={() => setViewMode('list')}
                  >
                    <List className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant={viewMode === 'card' ? 'secondary' : 'ghost'} 
                    size="sm" 
                    className="h-7 px-2"
                    onClick={() => setViewMode('card')}
                  >
                    <LayoutGrid className="w-4 h-4" />
                  </Button>
                </div>

                {/* Clear Filters */}
                {(filters.project_id !== 'all' || filters.client_id !== 'all' || filters.status !== 'all' || filters.date_from || filters.date_to) && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-zinc-500 h-9"
                    onClick={() => setFilters({ project_id: 'all', client_id: 'all', month: 'all', status: 'all', date_from: '', date_to: '' })}
                  >
                    <X className="w-4 h-4 mr-1" /> Clear
                  </Button>
                )}
              </div>
              
              {/* Filter Summary */}
              {(filters.project_id !== 'all' || filters.client_id !== 'all' || filters.status !== 'all' || filters.date_from || filters.date_to) && (
                <div className="mt-3 pt-3 border-t border-zinc-100 flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-zinc-500">Showing {filteredMeetings.length} of {meetings.length} meetings</span>
                  {filters.project_id !== 'all' && (
                    <Badge variant="secondary" className="text-xs bg-blue-50 text-blue-700">
                      Project: {uniqueProjects.find(p => p.id === filters.project_id)?.name}
                    </Badge>
                  )}
                  {filters.client_id !== 'all' && (
                    <Badge variant="secondary" className="text-xs">
                      Company: {uniqueClients.find(c => c.id === filters.client_id)?.name}
                    </Badge>
                  )}
                  {filters.status !== 'all' && (
                    <Badge variant="secondary" className="text-xs capitalize">
                      {filters.status.replace('_', ' ')}
                    </Badge>
                  )}
                  {(filters.date_from || filters.date_to) && (
                    <Badge variant="secondary" className="text-xs bg-amber-50 text-amber-700">
                      Duration: {filters.date_from ? format(new Date(filters.date_from), 'MMM dd') : '...'} - {filters.date_to ? format(new Date(filters.date_to), 'MMM dd, yyyy') : '...'}
                    </Badge>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Total Meetings</div>
                <div className="text-2xl font-semibold text-zinc-950" data-testid="consulting-total-count">{filteredMeetings.length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Delivered</div>
                <div className="text-2xl font-semibold text-emerald-700">{filteredMeetings.filter(m => m.is_delivered).length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">With MOM</div>
                <div className="text-2xl font-semibold text-zinc-950">{filteredMeetings.filter(m => m.mom_generated).length}</div>
              </CardContent>
            </Card>
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Action Items</div>
                <div className="text-2xl font-semibold text-zinc-950">
                  {filteredMeetings.reduce((sum, m) => sum + (m.action_items?.length || 0), 0)}
                </div>
              </CardContent>
            </Card>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64"><div className="text-zinc-500">Loading...</div></div>
          ) : filteredMeetings.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="flex flex-col items-center justify-center h-64">
                <Calendar className="w-12 h-12 text-zinc-300 mb-4" />
                <p className="text-zinc-500 mb-4">
                  {meetings.length === 0 ? 'No consulting meetings yet' : 'No meetings match your filters'}
                </p>
                {canEdit && meetings.length === 0 && (
                  <Button onClick={() => setDialogOpen(true)} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                    <Plus className="w-4 h-4 mr-2" /> Schedule First Meeting
                  </Button>
                )}
                {meetings.length > 0 && (
                  <Button variant="outline" onClick={() => setFilters({ client_id: 'all', month: 'all', status: 'all' })}>
                    Clear Filters
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : viewMode === 'list' ? (
            /* List View */
            <div className="border border-zinc-200 rounded-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50">
                  <tr>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Meeting / Project</th>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Company</th>
                    <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Date</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Mode</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                    <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">MOM</th>
                    <th className="text-right px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMeetings.map((meeting, idx) => {
                    const project = projects.find(p => p.id === meeting.project_id);
                    const client = clients.find(c => c.id === meeting.client_id);
                    // Company name (client is the company)
                    const companyName = meeting.client_name || client?.company_name || client?.name || '-';
                    const projectName = meeting.project_name || project?.name || '-';
                    
                    return (
                      <tr 
                        key={meeting.id} 
                        className="border-t border-zinc-100 hover:bg-zinc-50 cursor-pointer" 
                        data-testid={`meeting-row-${meeting.id}`}
                        onClick={() => openMeetingDetail(meeting)}
                      >
                        <td className="px-4 py-3">
                          <div className="font-medium text-zinc-950 hover:text-blue-600">{meeting.title || projectName || 'Meeting'}</div>
                          <div className="text-xs text-zinc-500">{projectName}</div>
                        </td>
                        <td className="px-4 py-3 text-zinc-600">{companyName}</td>
                        <td className="px-4 py-3 text-zinc-700">
                          <div>{format(new Date(meeting.meeting_date), 'EEE, MMM dd, yyyy')}</div>
                          <div className="text-xs text-zinc-400">{format(new Date(meeting.meeting_date), 'HH:mm')}</div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Badge variant="outline" className="text-xs">
                            {meeting.mode === 'online' ? 'Online' : meeting.mode === 'offline' ? 'In-person' : 'Call'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {meeting.is_delivered ? (
                            <Badge className="bg-emerald-100 text-emerald-700 text-xs">Delivered</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs text-amber-600 border-amber-200">Pending</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {meeting.mom_generated ? (
                            <div className="flex items-center justify-center gap-1">
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                              {meeting.mom_sent_to_client && <Mail className="w-4 h-4 text-blue-500" />}
                            </div>
                          ) : (
                            <Circle className="w-4 h-4 text-zinc-300 mx-auto" />
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {!meeting.is_delivered && canRecordMOM(meeting) && (
                              <Button size="sm" variant="outline" onClick={() => openMOMDialog(meeting)}>
                                <FileText className="w-3 h-3 mr-1" /> MOM
                              </Button>
                            )}
                            <Button size="sm" variant="ghost" onClick={() => setExpandedMeetings(prev => ({ ...prev, [meeting.id]: !prev[meeting.id] }))}>
                              {expandedMeetings[meeting.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            /* Card View */
            <div className="space-y-3">
              {filteredMeetings.map((meeting) => {
                const project = projects.find(p => p.id === meeting.project_id);
                const client = clients.find(c => c.id === meeting.client_id);
                const clientName = meeting.client_name || client?.company_name || client?.name || '';
                const projectName = meeting.project_name || project?.name || '';
                const isExpanded = expandedMeetings[meeting.id];
                const actionItemsCount = meeting.action_items?.length || 0;
                const completedCount = meeting.action_items?.filter(a => a.status === 'completed').length || 0;

                return (
                  <Card key={meeting.id} data-testid={`consulting-meeting-card-${meeting.id}`}
                    className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                    onClick={() => openMeetingDetail(meeting)}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className={`p-2 rounded-sm ${getModeBadge(meeting.mode)}`}>{getModeIcon(meeting.mode)}</div>
                            <div>
                              <div className="font-medium text-zinc-950">{meeting.title || projectName || 'Meeting'}</div>
                              <div className="text-sm text-zinc-500">
                                {projectName && <span>{projectName}</span>}
                                {clientName && <span> | {clientName}</span>}
                                {!projectName && !clientName && <span>No project linked</span>}
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
                              <div className="text-sm text-zinc-950">{format(new Date(meeting.meeting_date), 'EEE, MMM dd, yyyy HH:mm')}</div>
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

            {/* SOW Scope Selection - Mandatory with search & filter for large lists */}
            {selectedMeeting?.project_id && (
              <div className="space-y-3 p-4 bg-indigo-50 border border-indigo-200 rounded-sm">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium text-indigo-900 flex items-center gap-2">
                    <Layers className="w-4 h-4" />
                    Link Meeting to SOW Scopes <span className="text-red-500">*</span>
                  </Label>
                  {availableScopes.length > 0 && (
                    <span className="text-xs text-indigo-600">
                      {selectedScopeIds.length} of {availableScopes.length} selected
                    </span>
                  )}
                </div>
                
                {loadingScopes ? (
                  <p className="text-sm text-zinc-500">Loading scopes from project SOW...</p>
                ) : availableScopes.length === 0 ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm">
                    <p className="text-sm text-amber-800">
                      No SOW scopes available for this project. 
                    </p>
                    <p className="text-xs text-amber-600 mt-1">
                      SOW with scopes must be created from sales team (Committed SOW) or added as additional scope.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Mandatory notice */}
                    <div className="p-2 bg-red-50 border border-red-200 rounded-sm">
                      <p className="text-xs text-red-700 flex items-center gap-2">
                        <AlertCircle className="w-3 h-3" />
                        <span><strong>Mandatory:</strong> At least one scope must be selected to save MOM</span>
                      </p>
                    </div>

                    {/* Selected Scopes Tags */}
                    {selectedScopeIds.length > 0 && (
                      <div className="flex flex-wrap gap-2 p-2 bg-white border border-indigo-200 rounded-sm">
                        {selectedScopeIds.map(scopeId => {
                          const scope = availableScopes.find(s => s.id === scopeId);
                          const wasAlreadyLinked = (selectedMeeting?.sow_scope_ids || []).includes(scopeId);
                          if (!scope) return null;
                          return (
                            <Badge 
                              key={scopeId} 
                              variant="secondary" 
                              className={`text-xs py-1 px-2 flex items-center gap-1 ${scope.is_additional ? 'bg-orange-100 text-orange-800' : 'bg-indigo-100 text-indigo-800'}`}
                            >
                              <CheckSquare className="w-3 h-3" />
                              {scope.name.length > 30 ? scope.name.substring(0, 30) + '...' : scope.name}
                              {!wasAlreadyLinked && (
                                <button
                                  type="button"
                                  onClick={() => setSelectedScopeIds(prev => prev.filter(id => id !== scopeId))}
                                  className="ml-1 hover:text-red-600"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              )}
                              {wasAlreadyLinked && <span className="ml-1 text-xs opacity-60">(locked)</span>}
                            </Badge>
                          );
                        })}
                      </div>
                    )}

                    {/* Search & Filter Bar */}
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                        <Input
                          placeholder="Search scopes..."
                          value={scopeSearchQuery}
                          onChange={(e) => setScopeSearchQuery(e.target.value)}
                          className="pl-8 h-9 text-sm bg-white"
                          data-testid="scope-search-input"
                        />
                        {scopeSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setScopeSearchQuery('')}
                            className="absolute right-2 top-1/2 -translate-y-1/2"
                          >
                            <X className="w-4 h-4 text-zinc-400 hover:text-zinc-600" />
                          </button>
                        )}
                      </div>
                      <Select value={scopeStatusFilter} onValueChange={setScopeStatusFilter}>
                        <SelectTrigger className="w-[140px] h-9 text-sm bg-white">
                          <SelectValue placeholder="All Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Status</SelectItem>
                          <SelectItem value="in_progress">In Progress</SelectItem>
                          <SelectItem value="not_started">Not Started</SelectItem>
                          <SelectItem value="completed">Completed</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Filtered Scopes List */}
                    <div className="max-h-48 overflow-y-auto border border-indigo-200 rounded-sm bg-white">
                      {(() => {
                        // Filter scopes based on search and status
                        const filteredScopes = availableScopes.filter(scope => {
                          const matchesSearch = !scopeSearchQuery || 
                            scope.name.toLowerCase().includes(scopeSearchQuery.toLowerCase()) ||
                            (scope.description || '').toLowerCase().includes(scopeSearchQuery.toLowerCase());
                          const matchesStatus = scopeStatusFilter === 'all' || scope.status === scopeStatusFilter;
                          return matchesSearch && matchesStatus;
                        });

                        if (filteredScopes.length === 0) {
                          return (
                            <div className="p-4 text-center text-sm text-zinc-500">
                              No scopes match your filter criteria
                            </div>
                          );
                        }

                        // Group by committed vs additional
                        const committedScopes = filteredScopes.filter(s => !s.is_additional);
                        const additionalScopes = filteredScopes.filter(s => s.is_additional);

                        return (
                          <div className="divide-y divide-zinc-100">
                            {/* Committed Scopes */}
                            {committedScopes.length > 0 && (
                              <div>
                                <div className="px-3 py-2 bg-indigo-50 border-b border-indigo-100 sticky top-0">
                                  <span className="text-xs font-semibold text-indigo-800 uppercase tracking-wide">
                                    Committed Scopes ({committedScopes.length})
                                  </span>
                                </div>
                                {committedScopes.map(scope => {
                                  const isSelected = selectedScopeIds.includes(scope.id);
                                  const wasAlreadyLinked = (selectedMeeting?.sow_scope_ids || []).includes(scope.id);
                                  return (
                                    <label
                                      key={scope.id}
                                      className={`flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-zinc-50 transition-colors ${isSelected ? 'bg-indigo-50' : ''}`}
                                    >
                                      <Checkbox
                                        checked={isSelected}
                                        disabled={wasAlreadyLinked}
                                        onCheckedChange={(checked) => {
                                          if (checked) {
                                            setSelectedScopeIds(prev => [...prev, scope.id]);
                                          } else if (!wasAlreadyLinked) {
                                            setSelectedScopeIds(prev => prev.filter(id => id !== scope.id));
                                          }
                                        }}
                                      />
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          <span className="text-sm font-medium text-zinc-900 truncate">{scope.name}</span>
                                          {wasAlreadyLinked && <Badge className="text-xs bg-indigo-100 text-indigo-700 flex-shrink-0">Linked</Badge>}
                                        </div>
                                        <div className="flex items-center gap-3 mt-0.5 text-xs text-zinc-500">
                                          <span className={`px-1.5 py-0.5 rounded ${
                                            scope.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                                            scope.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                            'bg-zinc-100 text-zinc-600'
                                          }`}>
                                            {scope.status?.replace('_', ' ')}
                                          </span>
                                          <span>{scope.progress_percentage || 0}% done</span>
                                        </div>
                                      </div>
                                    </label>
                                  );
                                })}
                              </div>
                            )}

                            {/* Additional Scopes */}
                            {additionalScopes.length > 0 && (
                              <div>
                                <div className="px-3 py-2 bg-orange-50 border-b border-orange-100 sticky top-0">
                                  <span className="text-xs font-semibold text-orange-800 uppercase tracking-wide">
                                    Additional Scopes ({additionalScopes.length})
                                  </span>
                                </div>
                                {additionalScopes.map(scope => {
                                  const isSelected = selectedScopeIds.includes(scope.id);
                                  const wasAlreadyLinked = (selectedMeeting?.sow_scope_ids || []).includes(scope.id);
                                  return (
                                    <label
                                      key={scope.id}
                                      className={`flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-zinc-50 transition-colors ${isSelected ? 'bg-orange-50' : ''}`}
                                    >
                                      <Checkbox
                                        checked={isSelected}
                                        disabled={wasAlreadyLinked}
                                        onCheckedChange={(checked) => {
                                          if (checked) {
                                            setSelectedScopeIds(prev => [...prev, scope.id]);
                                          } else if (!wasAlreadyLinked) {
                                            setSelectedScopeIds(prev => prev.filter(id => id !== scope.id));
                                          }
                                        }}
                                      />
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          <span className="text-sm font-medium text-zinc-900 truncate">{scope.name}</span>
                                          <Badge variant="outline" className="text-xs text-orange-600 border-orange-300 flex-shrink-0">Additional</Badge>
                                          {wasAlreadyLinked && <Badge className="text-xs bg-orange-100 text-orange-700 flex-shrink-0">Linked</Badge>}
                                        </div>
                                        <div className="flex items-center gap-3 mt-0.5 text-xs text-zinc-500">
                                          <span className={`px-1.5 py-0.5 rounded ${
                                            scope.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                                            scope.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                                            'bg-zinc-100 text-zinc-600'
                                          }`}>
                                            {scope.status?.replace('_', ' ')}
                                          </span>
                                          <span>{scope.progress_percentage || 0}% done</span>
                                        </div>
                                      </div>
                                    </label>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </div>

                    {/* Quick actions */}
                    <div className="flex items-center justify-between pt-2 border-t border-indigo-200">
                      <div className="text-xs text-indigo-600">
                        {scopeSearchQuery || scopeStatusFilter !== 'all' ? 
                          `Showing filtered results` : 
                          `${availableScopes.length} total scopes`}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7"
                          onClick={() => {
                            // Select all visible (filtered) scopes that aren't already linked
                            const filteredScopes = availableScopes.filter(scope => {
                              const matchesSearch = !scopeSearchQuery || 
                                scope.name.toLowerCase().includes(scopeSearchQuery.toLowerCase());
                              const matchesStatus = scopeStatusFilter === 'all' || scope.status === scopeStatusFilter;
                              return matchesSearch && matchesStatus;
                            });
                            const newIds = filteredScopes.map(s => s.id).filter(id => !selectedScopeIds.includes(id));
                            setSelectedScopeIds(prev => [...prev, ...newIds]);
                          }}
                        >
                          Select All Visible
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7 text-red-600 hover:text-red-700"
                          onClick={() => {
                            // Clear all except already linked scopes
                            const alreadyLinked = selectedMeeting?.sow_scope_ids || [];
                            setSelectedScopeIds(alreadyLinked);
                          }}
                        >
                          Clear Selection
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
            
            {!selectedMeeting?.project_id && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm">
                <p className="text-sm text-amber-800 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  No project linked to this meeting
                </p>
                <p className="text-xs text-amber-600 mt-1">
                  Meeting must be linked to a project to select SOW scopes.
                </p>
              </div>
            )}

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

            {/* Document Attachments Section */}
            <div className="space-y-3">
              <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                Attachments (Optional)
              </Label>
              
              {/* Uploaded files list */}
              {momAttachments.length > 0 && (
                <div className="space-y-2">
                  {momAttachments.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-zinc-50 rounded-sm border border-zinc-200">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-zinc-500" />
                        <span className="text-sm text-zinc-700">{file.name || file.filename}</span>
                        {file.size && (
                          <span className="text-xs text-zinc-400">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        )}
                      </div>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => removeAttachment(idx)}
                        className="h-6 w-6 p-0 text-red-500 hover:bg-red-50"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Upload button */}
              <div className="flex items-center gap-2">
                <label className="cursor-pointer">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.png,.jpg,.jpeg"
                    onChange={handleAttachmentUpload}
                    className="hidden"
                    data-testid="mom-attachment-input"
                  />
                  <div className="flex items-center gap-2 px-3 py-2 border border-dashed border-zinc-300 rounded-sm hover:border-zinc-400 hover:bg-zinc-50 transition-colors">
                    <Upload className="w-4 h-4 text-zinc-500" />
                    <span className="text-sm text-zinc-600">
                      {uploadingAttachment ? 'Uploading...' : 'Attach Documents'}
                    </span>
                  </div>
                </label>
                <span className="text-xs text-zinc-400">
                  PDF, Word, Excel, Images (max 20MB each)
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Next Meeting Date</Label>
              <Input type="datetime-local" value={momData.next_meeting_date}
                onChange={(e) => setMomData({ ...momData, next_meeting_date: e.target.value })} className="rounded-sm border-zinc-200 w-64" />
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-zinc-200">
              <Button onClick={handleSaveMOM} data-testid="save-consulting-mom" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Save MOM
              </Button>
              <div className="flex gap-2">
                <Button onClick={handleSendMOM} variant="outline" className="rounded-sm"
                  disabled={selectedMeeting?.mom_sent_to_client} data-testid="send-mom-btn">
                  <Send className="w-4 h-4 mr-2" />
                  {selectedMeeting?.mom_sent_to_client ? 'MOM Sent' : 'Send to Client'}
                </Button>
                {!selectedMeeting?.is_delivered && selectedMeeting?.mom_generated && (
                  <Button 
                    onClick={handleCompleteMeeting} 
                    className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm"
                    data-testid="complete-meeting-btn"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Complete & Send MOM
                  </Button>
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Meeting Detail Dialog - Printable View */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-4xl max-h-[95vh] overflow-y-auto print:max-w-none print:max-h-none print:overflow-visible">
          <DialogHeader className="print:mb-4">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
                Meeting Details
              </DialogTitle>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => window.print()}
                className="print:hidden"
              >
                <Printer className="w-4 h-4 mr-2" /> Print
              </Button>
            </div>
            <DialogDescription className="text-zinc-500">
              Complete meeting record with MOM and action items
            </DialogDescription>
          </DialogHeader>

          {selectedMeeting && (
            <div className="space-y-6 print:space-y-4">
              {/* Meeting Header Info */}
              <div className="bg-zinc-50 p-4 rounded-sm border border-zinc-200 print:bg-white">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-zinc-950">{selectedMeeting.title || 'Meeting'}</h2>
                    <p className="text-sm text-zinc-600">{selectedMeeting.project_name || projects.find(p => p.id === selectedMeeting.project_id)?.name}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant="outline" className="mb-2">
                      <Hash className="w-3 h-3 mr-1" />
                      Meeting #{getMeetingSeriesNumber(selectedMeeting)}
                    </Badge>
                    <div className="text-xs text-zinc-500">
                      {selectedMeeting.is_delivered ? (
                        <Badge className="bg-emerald-100 text-emerald-700">Delivered</Badge>
                      ) : (
                        <Badge variant="outline" className="text-amber-600 border-amber-200">Pending</Badge>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Company</div>
                    <div className="font-medium text-zinc-800">
                      {selectedMeeting.client_name || clients.find(c => c.id === selectedMeeting.client_id)?.company_name || '-'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Date & Time</div>
                    <div className="font-medium text-zinc-800">
                      {format(new Date(selectedMeeting.meeting_date), 'EEEE, MMM dd, yyyy')}
                      <span className="text-zinc-500 ml-2">{format(new Date(selectedMeeting.meeting_date), 'HH:mm')}</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Mode</div>
                    <div className="font-medium text-zinc-800">
                      {selectedMeeting.mode === 'online' ? 'Online' : selectedMeeting.mode === 'offline' ? 'In-person' : 'Tele Call'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Duration</div>
                    <div className="font-medium text-zinc-800">{selectedMeeting.duration_minutes || '-'} mins</div>
                  </div>
                </div>
              </div>

              {/* Project Meeting Progress */}
              <div className="bg-blue-50 p-4 rounded-sm border border-blue-200">
                <div className="text-xs uppercase tracking-wide text-blue-700 mb-2 font-medium">Project Meeting Progress</div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-800">{getProjectStats(selectedMeeting).committed}</div>
                    <div className="text-xs text-blue-600">Committed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-700">{getProjectStats(selectedMeeting).delivered}</div>
                    <div className="text-xs text-emerald-600">Completed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-amber-700">{getProjectStats(selectedMeeting).pending}</div>
                    <div className="text-xs text-amber-600">Pending</div>
                  </div>
                </div>
              </div>

              {/* Consultant Details */}
              <div className="border border-zinc-200 rounded-sm p-4">
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2 font-medium">Consultant Details</div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-zinc-500">Created By</div>
                    <div className="font-medium text-zinc-800">{selectedMeeting.created_by_name || 'System'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500">Attendees</div>
                    <div className="font-medium text-zinc-800">
                      {selectedMeeting.attendee_names?.length > 0 
                        ? selectedMeeting.attendee_names.join(', ') 
                        : '-'}
                    </div>
                  </div>
                </div>
              </div>

              {/* MOM Content */}
              {selectedMeeting.mom_generated && (
                <div className="border border-zinc-200 rounded-sm p-4 space-y-4">
                  <div className="flex items-center gap-2 text-emerald-700">
                    <FileText className="w-5 h-5" />
                    <span className="text-sm font-semibold uppercase tracking-wide">Minutes of Meeting</span>
                    {selectedMeeting.mom_sent_to_client && (
                      <Badge className="bg-blue-100 text-blue-700 ml-2">
                        <Mail className="w-3 h-3 mr-1" /> Sent to Client
                      </Badge>
                    )}
                  </div>

                  {selectedMeeting.agenda?.length > 0 && selectedMeeting.agenda.some(a => a) && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">Agenda</div>
                      <ul className="list-disc list-inside text-sm text-zinc-700 space-y-1">
                        {selectedMeeting.agenda.filter(a => a).map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedMeeting.discussion_points?.length > 0 && selectedMeeting.discussion_points.some(d => d) && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">Discussion Points</div>
                      <ul className="list-disc list-inside text-sm text-zinc-700 space-y-1">
                        {selectedMeeting.discussion_points.filter(d => d).map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedMeeting.decisions_made?.length > 0 && selectedMeeting.decisions_made.some(d => d) && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-2">Decisions Made</div>
                      <ul className="list-disc list-inside text-sm text-zinc-700 space-y-1">
                        {selectedMeeting.decisions_made.filter(d => d).map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Action Items */}
              {selectedMeeting.action_items?.length > 0 && (
                <div className="border border-zinc-200 rounded-sm p-4">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-3 font-medium">
                    Action Items ({selectedMeeting.action_items.length})
                  </div>
                  <div className="space-y-2">
                    {selectedMeeting.action_items.map((item, idx) => (
                      <div 
                        key={item.id || idx} 
                        className={`flex items-start justify-between p-3 rounded-sm border ${
                          item.status === 'completed' ? 'bg-emerald-50 border-emerald-200' : 'bg-zinc-50 border-zinc-200'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {item.status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-emerald-600 mt-0.5" />
                          ) : (
                            <Circle className="w-5 h-5 text-zinc-400 mt-0.5" />
                          )}
                          <div>
                            <div className={`text-sm ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-700'}`}>
                              {item.description}
                            </div>
                            <div className="text-xs text-zinc-500 mt-1">
                              Assigned: {item.assigned_to_name || 'Unassigned'} | 
                              Due: {item.due_date ? format(new Date(item.due_date), 'MMM dd, yyyy') : 'No date'}
                            </div>
                          </div>
                        </div>
                        <Badge variant="outline" className={`text-xs ${
                          item.priority === 'high' ? 'border-red-300 text-red-700' :
                          item.priority === 'medium' ? 'border-yellow-300 text-yellow-700' :
                          'border-zinc-300 text-zinc-600'
                        }`}>
                          {item.priority}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Attachments */}
              {selectedMeeting.mom_attachments?.length > 0 && (
                <div className="border border-zinc-200 rounded-sm p-4">
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-3 font-medium">
                    Attachments ({selectedMeeting.mom_attachments.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedMeeting.mom_attachments.map((file, idx) => (
                      <div key={idx} className="flex items-center gap-2 px-3 py-2 bg-zinc-50 rounded-sm border border-zinc-200">
                        <Paperclip className="w-4 h-4 text-zinc-500" />
                        <span className="text-sm text-zinc-700">{file.name || file.filename}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Next Meeting */}
              {selectedMeeting.next_meeting_date && (
                <div className="bg-amber-50 p-4 rounded-sm border border-amber-200">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-amber-700" />
                    <span className="text-sm font-medium text-amber-800">
                      Next Meeting: {format(new Date(selectedMeeting.next_meeting_date), 'EEEE, MMM dd, yyyy HH:mm')}
                    </span>
                  </div>
                </div>
              )}

              {/* Actions - Hidden in Print */}
              <div className="flex justify-end gap-2 pt-4 border-t border-zinc-200 print:hidden">
                <Button variant="outline" onClick={() => setDetailDialogOpen(false)}>
                  Close
                </Button>
                {canEdit && !selectedMeeting.is_delivered && (
                  <Button onClick={() => { setDetailDialogOpen(false); openMOMDialog(selectedMeeting); }}>
                    <FileText className="w-4 h-4 mr-2" /> Edit MOM
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsultingMeetings;
