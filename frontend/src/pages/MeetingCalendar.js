import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import {
  Calendar, ChevronLeft, ChevronRight, Clock, Users, Video, Phone,
  MapPin, CheckCircle, Circle, AlertTriangle, Plus, RefreshCw,
  LayoutGrid, List, Bell, BellOff, Settings, Send, Mail
} from 'lucide-react';
import { toast } from 'sonner';
import { format, addDays, startOfWeek, isSameDay, parseISO, isToday } from 'date-fns';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const MODE_CONFIG = {
  online: { icon: Video, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Online' },
  offline: { icon: MapPin, color: 'text-purple-600', bg: 'bg-purple-50', label: 'In-Person' },
  tele_call: { icon: Phone, color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Phone Call' }
};

const MeetingCalendar = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [weekOffset, setWeekOffset] = useState(0);
  const [viewMode, setViewMode] = useState('week');
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [selectedConsultants, setSelectedConsultants] = useState([]);
  
  const [scheduleForm, setScheduleForm] = useState({
    project_id: '',
    consultant_id: '',
    schedule_type: 'fixed_day',
    day: 'monday',
    time: '10:00',
    interval_days: 7,
    duration_minutes: 60
  });

  // Fetch week calendar
  const { data: calendarData, isLoading: loadingCalendar, refetch: refetchCalendar } = useQuery({
    queryKey: ['meeting-calendar', 'week', weekOffset, selectedConsultants],
    queryFn: async () => {
      const consultantParam = selectedConsultants.length > 0 
        ? `&consultant_ids=${selectedConsultants.join(',')}`
        : '';
      const res = await axios.get(`${API}/meeting-schedules/calendar/week?week_offset=${weekOffset}${consultantParam}`);
      return res.data;
    },
    staleTime: 60 * 1000,
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['meeting-schedules', 'stats'],
    queryFn: async () => {
      const res = await axios.get(`${API}/meeting-schedules/stats/overview`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Fetch conflicts
  const { data: conflictsData } = useQuery({
    queryKey: ['meeting-schedules', 'conflicts'],
    queryFn: async () => {
      const res = await axios.get(`${API}/meeting-schedules/conflicts/all`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Fetch notification preferences
  const { data: notifPrefs, refetch: refetchPrefs } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: async () => {
      const res = await axios.get(`${API}/meeting-schedules/notifications/preferences`);
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  // Fetch projects
  const { data: projects = [] } = useQuery({
    queryKey: ['projects', 'active'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects?status=active`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // Fetch consultants
  const { data: consultants = [] } = useQuery({
    queryKey: ['users', 'consultants'],
    queryFn: async () => {
      const res = await axios.get(`${API}/users`);
      return (res.data || []).filter(u => 
        ['consultant', 'principal_consultant', 'senior_consultant', 'lead_consultant', 'lean_consultant'].includes(u.role)
      );
    },
    staleTime: 5 * 60 * 1000,
  });

  // Create schedule mutation
  const createScheduleMutation = useMutation({
    mutationFn: async (data) => {
      const config = data.schedule_type === 'fixed_day'
        ? { day: data.day, time: data.time, duration_minutes: data.duration_minutes }
        : { interval_days: data.interval_days, preferred_time: data.time, duration_minutes: data.duration_minutes };
      
      return axios.post(`${API}/meeting-schedules`, {
        project_id: data.project_id,
        consultant_id: data.consultant_id,
        schedule_type: data.schedule_type,
        config
      });
    },
    onSuccess: () => {
      toast.success('Recurring schedule created');
      queryClient.invalidateQueries(['meeting-schedules']);
      setShowScheduleDialog(false);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create schedule');
    }
  });

  // Update notification preferences
  const updatePrefsMutation = useMutation({
    mutationFn: async (prefs) => {
      return axios.put(`${API}/meeting-schedules/notifications/preferences`, prefs);
    },
    onSuccess: () => {
      toast.success('Notification preferences saved');
      refetchPrefs();
    },
    onError: () => {
      toast.error('Failed to save preferences');
    }
  });

  // Send test notification
  const testNotificationMutation = useMutation({
    mutationFn: async () => {
      return axios.post(`${API}/meeting-schedules/notifications/test`);
    },
    onSuccess: (res) => {
      toast.success(`Test email sent to ${res.data.sent_to}`);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to send test');
    }
  });

  // Get dates for current week
  const getWeekDates = () => {
    if (!calendarData?.week_start) return [];
    const start = parseISO(calendarData.week_start);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  };

  const weekDates = getWeekDates();
  const today = new Date();

  // Get meetings for a specific date
  const getMeetingsForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return calendarData?.calendar?.[dateStr] || [];
  };

  const meetingReminders = notifPrefs?.meeting_reminders || {};

  return (
    <div className="p-6 space-y-6 bg-zinc-50 min-h-screen" data-testid="meeting-calendar-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Meeting Calendar</h1>
          <p className="text-zinc-500 text-sm">Team schedule & recurring meetings</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettingsDialog(true)}
            className="border-zinc-200 bg-white hover:bg-zinc-50"
            data-testid="notification-settings-btn"
          >
            {meetingReminders.enabled !== false ? (
              <Bell className="w-4 h-4 mr-1 text-emerald-600" />
            ) : (
              <BellOff className="w-4 h-4 mr-1 text-zinc-400" />
            )}
            Reminders
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchCalendar()}
            className="border-zinc-200 bg-white hover:bg-zinc-50"
            data-testid="refresh-calendar-btn"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Dialog open={showScheduleDialog} onOpenChange={setShowScheduleDialog}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 shadow-sm" data-testid="create-schedule-btn">
                <Plus className="w-4 h-4 mr-1" />
                New Schedule
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-white border-zinc-200 max-w-md">
              <DialogHeader>
                <DialogTitle className="text-zinc-900">Create Recurring Schedule</DialogTitle>
                <DialogDescription className="text-zinc-500">
                  Set up automatic recurring meetings for a project.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-zinc-700 text-sm font-medium">Project</Label>
                  <select
                    value={scheduleForm.project_id}
                    onChange={(e) => setScheduleForm({...scheduleForm, project_id: e.target.value})}
                    className="w-full mt-1.5 p-2.5 bg-white border border-zinc-200 rounded-lg text-zinc-900 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    data-testid="schedule-project-select"
                  >
                    <option value="">Select project...</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <Label className="text-zinc-700 text-sm font-medium">Consultant</Label>
                  <select
                    value={scheduleForm.consultant_id}
                    onChange={(e) => setScheduleForm({...scheduleForm, consultant_id: e.target.value})}
                    className="w-full mt-1.5 p-2.5 bg-white border border-zinc-200 rounded-lg text-zinc-900 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    data-testid="schedule-consultant-select"
                  >
                    <option value="">Select consultant...</option>
                    {consultants.map(c => (
                      <option key={c.id} value={c.id}>{c.full_name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <Label className="text-zinc-700 text-sm font-medium">Schedule Type</Label>
                  <div className="flex gap-2 mt-1.5">
                    <button
                      type="button"
                      onClick={() => setScheduleForm({...scheduleForm, schedule_type: 'fixed_day'})}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        scheduleForm.schedule_type === 'fixed_day' 
                          ? 'bg-emerald-600 text-white shadow-sm' 
                          : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                      }`}
                    >
                      Fixed Day
                    </button>
                    <button
                      type="button"
                      onClick={() => setScheduleForm({...scheduleForm, schedule_type: 'interval'})}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        scheduleForm.schedule_type === 'interval' 
                          ? 'bg-emerald-600 text-white shadow-sm' 
                          : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                      }`}
                    >
                      Interval Based
                    </button>
                  </div>
                </div>
                
                {scheduleForm.schedule_type === 'fixed_day' ? (
                  <div>
                    <Label className="text-zinc-700 text-sm font-medium">Day of Week</Label>
                    <select
                      value={scheduleForm.day}
                      onChange={(e) => setScheduleForm({...scheduleForm, day: e.target.value})}
                      className="w-full mt-1.5 p-2.5 bg-white border border-zinc-200 rounded-lg text-zinc-900 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                      data-testid="schedule-day-select"
                    >
                      {WEEKDAYS.map(day => (
                        <option key={day} value={day.toLowerCase()}>{day}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <Label className="text-zinc-700 text-sm font-medium">Repeat Every (days)</Label>
                    <Input
                      type="number"
                      min="1"
                      max="30"
                      value={scheduleForm.interval_days}
                      onChange={(e) => setScheduleForm({...scheduleForm, interval_days: parseInt(e.target.value)})}
                      className="mt-1.5 bg-white border-zinc-200"
                      data-testid="schedule-interval-input"
                    />
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-zinc-700 text-sm font-medium">Time</Label>
                    <Input
                      type="time"
                      value={scheduleForm.time}
                      onChange={(e) => setScheduleForm({...scheduleForm, time: e.target.value})}
                      className="mt-1.5 bg-white border-zinc-200"
                      data-testid="schedule-time-input"
                    />
                  </div>
                  <div>
                    <Label className="text-zinc-700 text-sm font-medium">Duration (mins)</Label>
                    <Input
                      type="number"
                      min="15"
                      max="240"
                      step="15"
                      value={scheduleForm.duration_minutes}
                      onChange={(e) => setScheduleForm({...scheduleForm, duration_minutes: parseInt(e.target.value)})}
                      className="mt-1.5 bg-white border-zinc-200"
                      data-testid="schedule-duration-input"
                    />
                  </div>
                </div>
                
                <Button
                  onClick={() => createScheduleMutation.mutate(scheduleForm)}
                  disabled={!scheduleForm.project_id || !scheduleForm.consultant_id || createScheduleMutation.isPending}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 shadow-sm"
                  data-testid="submit-schedule-btn"
                >
                  {createScheduleMutation.isPending ? 'Creating...' : 'Create Schedule'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-medium tracking-wide">Active Schedules</p>
                <p className="text-2xl font-bold text-zinc-900 mt-1">{stats?.active_schedules || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
                <RefreshCw className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-medium tracking-wide">This Week</p>
                <p className="text-2xl font-bold text-zinc-900 mt-1">{stats?.meetings_this_week || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-medium tracking-wide">Delivered</p>
                <p className="text-2xl font-bold text-emerald-600 mt-1">{stats?.delivered_this_week || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-medium tracking-wide">Pending MOM</p>
                <p className="text-2xl font-bold text-amber-600 mt-1">{stats?.pending_mom || 0}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center">
                <Bell className="w-5 h-5 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase font-medium tracking-wide">Conflicts</p>
                <p className={`text-2xl font-bold mt-1 ${(conflictsData?.total_conflicts || 0) > 0 ? 'text-red-600' : 'text-zinc-900'}`}>
                  {conflictsData?.total_conflicts || 0}
                </p>
              </div>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${(conflictsData?.total_conflicts || 0) > 0 ? 'bg-red-50' : 'bg-zinc-100'}`}>
                <AlertTriangle className={`w-5 h-5 ${(conflictsData?.total_conflicts || 0) > 0 ? 'text-red-600' : 'text-zinc-400'}`} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Calendar Card */}
      <Card className="bg-white border-zinc-200 shadow-sm overflow-hidden">
        <CardHeader className="border-b border-zinc-100 bg-zinc-50/50 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setWeekOffset(prev => prev - 1)}
                className="p-2 rounded-lg hover:bg-zinc-200 transition-colors"
                data-testid="prev-week-btn"
              >
                <ChevronLeft className="w-5 h-5 text-zinc-600" />
              </button>
              <div className="text-center min-w-[200px]">
                <CardTitle className="text-lg font-semibold text-zinc-900">
                  {calendarData?.week_start && calendarData?.week_end ? (
                    `${format(parseISO(calendarData.week_start), 'MMM d')} - ${format(parseISO(calendarData.week_end), 'MMM d, yyyy')}`
                  ) : 'Loading...'}
                </CardTitle>
                {weekOffset !== 0 && (
                  <button
                    onClick={() => setWeekOffset(0)}
                    className="text-xs text-emerald-600 hover:underline font-medium"
                  >
                    Go to current week
                  </button>
                )}
              </div>
              <button
                onClick={() => setWeekOffset(prev => prev + 1)}
                className="p-2 rounded-lg hover:bg-zinc-200 transition-colors"
                data-testid="next-week-btn"
              >
                <ChevronRight className="w-5 h-5 text-zinc-600" />
              </button>
            </div>
            <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-lg">
              <button
                onClick={() => setViewMode('week')}
                className={`p-2 rounded-md transition-all ${viewMode === 'week' ? 'bg-white shadow-sm text-emerald-600' : 'text-zinc-500 hover:text-zinc-700'}`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md transition-all ${viewMode === 'list' ? 'bg-white shadow-sm text-emerald-600' : 'text-zinc-500 hover:text-zinc-700'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingCalendar ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
          ) : viewMode === 'week' ? (
            /* Week Grid View */
            <div className="grid grid-cols-7">
              {/* Header */}
              {WEEKDAYS.map((day, idx) => {
                const date = weekDates[idx];
                const isCurrentDay = date && isSameDay(date, today);
                return (
                  <div
                    key={day}
                    className={`text-center py-3 border-b border-r last:border-r-0 ${isCurrentDay ? 'bg-emerald-50' : 'bg-zinc-50'}`}
                  >
                    <p className="text-xs text-zinc-500 uppercase font-medium">{day.slice(0, 3)}</p>
                    <p className={`text-xl font-semibold mt-0.5 ${isCurrentDay ? 'text-emerald-600' : 'text-zinc-900'}`}>
                      {date ? format(date, 'd') : '-'}
                    </p>
                  </div>
                );
              })}
              
              {/* Day cells */}
              {weekDates.map((date, idx) => {
                const meetings = getMeetingsForDate(date);
                const isCurrentDay = isSameDay(date, today);
                return (
                  <div
                    key={idx}
                    className={`min-h-[220px] p-2 border-r last:border-r-0 ${
                      isCurrentDay ? 'bg-emerald-50/30' : 'bg-white'
                    }`}
                    data-testid={`calendar-day-${format(date, 'yyyy-MM-dd')}`}
                  >
                    {meetings.length === 0 ? (
                      <p className="text-xs text-zinc-400 text-center py-16">No meetings</p>
                    ) : (
                      <div className="space-y-2">
                        {meetings.map((meeting, mIdx) => {
                          const modeConfig = MODE_CONFIG[meeting.mode] || MODE_CONFIG.online;
                          const ModeIcon = modeConfig.icon;
                          return (
                            <div
                              key={mIdx}
                              className={`p-2.5 rounded-lg text-xs cursor-pointer transition-all hover:shadow-md border ${
                                meeting.has_conflict
                                  ? 'bg-red-50 border-red-200'
                                  : meeting.is_delivered
                                  ? 'bg-emerald-50 border-emerald-200'
                                  : 'bg-white border-zinc-200 hover:border-zinc-300'
                              }`}
                              title={meeting.title}
                            >
                              <div className="flex items-center gap-1.5 text-zinc-500 mb-1.5">
                                <Clock className="w-3 h-3" />
                                <span className="font-medium">{meeting.time}</span>
                                <span className={`${modeConfig.bg} ${modeConfig.color} p-0.5 rounded`}>
                                  <ModeIcon className="w-3 h-3" />
                                </span>
                                {meeting.is_recurring && (
                                  <span className="bg-blue-50 text-blue-600 p-0.5 rounded">
                                    <RefreshCw className="w-3 h-3" />
                                  </span>
                                )}
                              </div>
                              <p className="text-zinc-900 font-medium truncate">{meeting.title}</p>
                              <div className="flex items-center gap-1 mt-1.5 text-zinc-500">
                                <Users className="w-3 h-3" />
                                <span className="truncate text-[11px]">{meeting.attendees?.slice(0, 2).join(', ') || 'TBD'}</span>
                              </div>
                              {meeting.is_delivered ? (
                                <span className="inline-flex items-center gap-1 text-emerald-600 mt-1.5 text-[11px] font-medium">
                                  <CheckCircle className="w-3 h-3" /> Completed
                                </span>
                              ) : meeting.has_conflict ? (
                                <span className="inline-flex items-center gap-1 text-red-600 mt-1.5 text-[11px] font-medium">
                                  <AlertTriangle className="w-3 h-3" /> Conflict
                                </span>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* List View */
            <div className="p-4 space-y-4">
              {weekDates.map((date, idx) => {
                const meetings = getMeetingsForDate(date);
                const isCurrentDay = isSameDay(date, today);
                if (meetings.length === 0) return null;
                
                return (
                  <div key={idx}>
                    <div className={`flex items-center gap-2 mb-3 pb-2 border-b border-zinc-100 ${isCurrentDay ? 'text-emerald-600' : 'text-zinc-700'}`}>
                      <Calendar className="w-4 h-4" />
                      <span className="font-semibold">{format(date, 'EEEE, MMMM d')}</span>
                      {isCurrentDay && <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Today</span>}
                    </div>
                    <div className="space-y-2 ml-6">
                      {meetings.map((meeting, mIdx) => {
                        const modeConfig = MODE_CONFIG[meeting.mode] || MODE_CONFIG.online;
                        const ModeIcon = modeConfig.icon;
                        return (
                          <div
                            key={mIdx}
                            className={`p-4 rounded-lg border transition-all hover:shadow-sm ${
                              meeting.has_conflict
                                ? 'bg-red-50 border-red-200'
                                : meeting.is_delivered
                                ? 'bg-emerald-50 border-emerald-200'
                                : 'bg-white border-zinc-200'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2 text-zinc-600">
                                  <Clock className="w-4 h-4" />
                                  <span className="font-medium">{meeting.time}</span>
                                  <span className="text-zinc-400">•</span>
                                  <span className="text-zinc-500">{meeting.duration || 60} min</span>
                                </div>
                                <span className="text-zinc-900 font-semibold">{meeting.title}</span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className={`${modeConfig.bg} ${modeConfig.color} px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1`}>
                                  <ModeIcon className="w-3 h-3" />
                                  {modeConfig.label}
                                </span>
                                {meeting.is_recurring && (
                                  <span className="bg-blue-50 text-blue-600 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                                    <RefreshCw className="w-3 h-3" /> Recurring
                                  </span>
                                )}
                                {meeting.is_delivered ? (
                                  <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                                    <CheckCircle className="w-3 h-3" /> Completed
                                  </span>
                                ) : meeting.mom_generated ? (
                                  <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded-full text-xs font-medium">MOM Ready</span>
                                ) : (
                                  <span className="bg-zinc-100 text-zinc-600 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                                    <Circle className="w-3 h-3" /> Pending
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 mt-2 text-sm text-zinc-500">
                              <Users className="w-3 h-3" />
                              <span>{meeting.attendees?.join(', ') || 'No attendees'}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
              {calendarData?.total_meetings === 0 && (
                <div className="text-center py-16 text-zinc-400">
                  <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
                  <p className="font-medium">No meetings scheduled for this week</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Conflicts Alert */}
      {conflictsData?.total_conflicts > 0 && (
        <Card className="bg-red-50 border-red-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-700 flex items-center gap-2 text-base">
              <AlertTriangle className="w-5 h-5" />
              Scheduling Conflicts Detected
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(conflictsData?.conflicts || []).slice(0, 5).map((conflict, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-white rounded-lg border border-red-100 text-sm">
                  <span className="font-medium text-zinc-900">{conflict?.consultant_name || 'Unknown'}</span>
                  <span className="text-red-600">has overlapping meetings:</span>
                  <span className="text-zinc-600">{conflict?.meeting_1?.title || 'Meeting 1'} ↔ {conflict?.meeting_2?.title || 'Meeting 2'}</span>
                  <span className="text-red-500 text-xs bg-red-100 px-2 py-0.5 rounded">({conflict?.overlap_minutes || 0} min overlap)</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notification Settings Dialog */}
      <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
        <DialogContent className="bg-white border-zinc-200 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-zinc-900 flex items-center gap-2">
              <Bell className="w-5 h-5 text-emerald-600" />
              Notification Settings
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Configure your meeting reminder preferences.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 mt-4">
            {/* Master Toggle */}
            <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
              <div>
                <p className="font-medium text-zinc-900">Meeting Reminders</p>
                <p className="text-sm text-zinc-500">Receive email reminders before meetings</p>
              </div>
              <Switch
                checked={meetingReminders.enabled !== false}
                onCheckedChange={(checked) => {
                  updatePrefsMutation.mutate({
                    meeting_reminders: { ...meetingReminders, enabled: checked }
                  });
                }}
              />
            </div>
            
            {meetingReminders.enabled !== false && (
              <>
                {/* 24h Reminder */}
                <div className="flex items-center justify-between px-4">
                  <div>
                    <p className="font-medium text-zinc-700">24 hours before</p>
                    <p className="text-sm text-zinc-500">Reminder one day ahead</p>
                  </div>
                  <Switch
                    checked={meetingReminders.remind_24h !== false}
                    onCheckedChange={(checked) => {
                      updatePrefsMutation.mutate({
                        meeting_reminders: { ...meetingReminders, remind_24h: checked }
                      });
                    }}
                  />
                </div>
                
                {/* 1h Reminder */}
                <div className="flex items-center justify-between px-4">
                  <div>
                    <p className="font-medium text-zinc-700">1 hour before</p>
                    <p className="text-sm text-zinc-500">Last-minute reminder</p>
                  </div>
                  <Switch
                    checked={meetingReminders.remind_1h !== false}
                    onCheckedChange={(checked) => {
                      updatePrefsMutation.mutate({
                        meeting_reminders: { ...meetingReminders, remind_1h: checked }
                      });
                    }}
                  />
                </div>

                {/* Email Toggle */}
                <div className="flex items-center justify-between px-4">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-zinc-400" />
                    <div>
                      <p className="font-medium text-zinc-700">Email notifications</p>
                      <p className="text-sm text-zinc-500">Receive reminders via email</p>
                    </div>
                  </div>
                  <Switch
                    checked={meetingReminders.email !== false}
                    onCheckedChange={(checked) => {
                      updatePrefsMutation.mutate({
                        meeting_reminders: { ...meetingReminders, email: checked }
                      });
                    }}
                  />
                </div>
              </>
            )}
            
            <div className="pt-4 border-t border-zinc-100">
              <Button
                variant="outline"
                size="sm"
                onClick={() => testNotificationMutation.mutate()}
                disabled={testNotificationMutation.isPending}
                className="w-full"
              >
                <Send className="w-4 h-4 mr-2" />
                {testNotificationMutation.isPending ? 'Sending...' : 'Send Test Reminder'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MeetingCalendar;
