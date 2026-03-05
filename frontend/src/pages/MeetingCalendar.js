import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import {
  Calendar, ChevronLeft, ChevronRight, Clock, Users, Video, Phone,
  MapPin, CheckCircle, Circle, AlertTriangle, Plus, RefreshCw,
  LayoutGrid, List, Filter, Settings, Bell
} from 'lucide-react';
import { toast } from 'sonner';
import { format, addDays, startOfWeek, isSameDay, parseISO } from 'date-fns';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const MODE_ICONS = {
  online: <Video className="w-3 h-3" />,
  offline: <MapPin className="w-3 h-3" />,
  tele_call: <Phone className="w-3 h-3" />
};

const MeetingCalendar = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [weekOffset, setWeekOffset] = useState(0);
  const [viewMode, setViewMode] = useState('week'); // 'week' | 'list'
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
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

  // Fetch projects for schedule creation
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

  return (
    <div className="p-6 space-y-6" data-testid="meeting-calendar-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Meeting Calendar</h1>
          <p className="text-zinc-400 text-sm">Team schedule & recurring meetings</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchCalendar()}
            className="border-zinc-700"
            data-testid="refresh-calendar-btn"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
          <Dialog open={showScheduleDialog} onOpenChange={setShowScheduleDialog}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" data-testid="create-schedule-btn">
                <Plus className="w-4 h-4 mr-1" />
                New Schedule
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-zinc-900 border-zinc-800 max-w-md">
              <DialogHeader>
                <DialogTitle className="text-zinc-100">Create Recurring Schedule</DialogTitle>
                <DialogDescription className="text-zinc-400">
                  Set up automatic recurring meetings for a project.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label className="text-zinc-300">Project</Label>
                  <select
                    value={scheduleForm.project_id}
                    onChange={(e) => setScheduleForm({...scheduleForm, project_id: e.target.value})}
                    className="w-full mt-1 p-2 bg-zinc-800 border border-zinc-700 rounded text-zinc-100"
                    data-testid="schedule-project-select"
                  >
                    <option value="">Select project...</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.name} - {p.client_name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <Label className="text-zinc-300">Consultant</Label>
                  <select
                    value={scheduleForm.consultant_id}
                    onChange={(e) => setScheduleForm({...scheduleForm, consultant_id: e.target.value})}
                    className="w-full mt-1 p-2 bg-zinc-800 border border-zinc-700 rounded text-zinc-100"
                    data-testid="schedule-consultant-select"
                  >
                    <option value="">Select consultant...</option>
                    {consultants.map(c => (
                      <option key={c.id} value={c.id}>{c.full_name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <Label className="text-zinc-300">Schedule Type</Label>
                  <div className="flex gap-2 mt-1">
                    <Button
                      type="button"
                      variant={scheduleForm.schedule_type === 'fixed_day' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setScheduleForm({...scheduleForm, schedule_type: 'fixed_day'})}
                      className={scheduleForm.schedule_type === 'fixed_day' ? 'bg-emerald-600' : 'border-zinc-700'}
                    >
                      Fixed Day
                    </Button>
                    <Button
                      type="button"
                      variant={scheduleForm.schedule_type === 'interval' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setScheduleForm({...scheduleForm, schedule_type: 'interval'})}
                      className={scheduleForm.schedule_type === 'interval' ? 'bg-emerald-600' : 'border-zinc-700'}
                    >
                      Interval Based
                    </Button>
                  </div>
                </div>
                
                {scheduleForm.schedule_type === 'fixed_day' ? (
                  <div>
                    <Label className="text-zinc-300">Day of Week</Label>
                    <select
                      value={scheduleForm.day}
                      onChange={(e) => setScheduleForm({...scheduleForm, day: e.target.value})}
                      className="w-full mt-1 p-2 bg-zinc-800 border border-zinc-700 rounded text-zinc-100"
                      data-testid="schedule-day-select"
                    >
                      {WEEKDAYS.map(day => (
                        <option key={day} value={day.toLowerCase()}>{day}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <Label className="text-zinc-300">Repeat Every (days)</Label>
                    <Input
                      type="number"
                      min="1"
                      max="30"
                      value={scheduleForm.interval_days}
                      onChange={(e) => setScheduleForm({...scheduleForm, interval_days: parseInt(e.target.value)})}
                      className="bg-zinc-800 border-zinc-700 text-zinc-100"
                      data-testid="schedule-interval-input"
                    />
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-zinc-300">Time</Label>
                    <Input
                      type="time"
                      value={scheduleForm.time}
                      onChange={(e) => setScheduleForm({...scheduleForm, time: e.target.value})}
                      className="bg-zinc-800 border-zinc-700 text-zinc-100"
                      data-testid="schedule-time-input"
                    />
                  </div>
                  <div>
                    <Label className="text-zinc-300">Duration (mins)</Label>
                    <Input
                      type="number"
                      min="15"
                      max="240"
                      step="15"
                      value={scheduleForm.duration_minutes}
                      onChange={(e) => setScheduleForm({...scheduleForm, duration_minutes: parseInt(e.target.value)})}
                      className="bg-zinc-800 border-zinc-700 text-zinc-100"
                      data-testid="schedule-duration-input"
                    />
                  </div>
                </div>
                
                <Button
                  onClick={() => createScheduleMutation.mutate(scheduleForm)}
                  disabled={!scheduleForm.project_id || !scheduleForm.consultant_id || createScheduleMutation.isPending}
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
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
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Active Schedules</p>
                <p className="text-2xl font-bold text-zinc-100">{stats?.active_schedules || 0}</p>
              </div>
              <RefreshCw className="w-8 h-8 text-emerald-500/30" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">This Week</p>
                <p className="text-2xl font-bold text-zinc-100">{stats?.meetings_this_week || 0}</p>
              </div>
              <Calendar className="w-8 h-8 text-blue-500/30" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Delivered</p>
                <p className="text-2xl font-bold text-emerald-400">{stats?.delivered_this_week || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-500/30" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Pending MOM</p>
                <p className="text-2xl font-bold text-amber-400">{stats?.pending_mom || 0}</p>
              </div>
              <Bell className="w-8 h-8 text-amber-500/30" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase">Conflicts</p>
                <p className={`text-2xl font-bold ${(conflictsData?.total_conflicts || 0) > 0 ? 'text-red-400' : 'text-zinc-100'}`}>
                  {conflictsData?.total_conflicts || 0}
                </p>
              </div>
              <AlertTriangle className={`w-8 h-8 ${(conflictsData?.total_conflicts || 0) > 0 ? 'text-red-500/30' : 'text-zinc-700'}`} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Week Navigation */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setWeekOffset(prev => prev - 1)}
                className="text-zinc-400 hover:text-zinc-100"
                data-testid="prev-week-btn"
              >
                <ChevronLeft className="w-5 h-5" />
              </Button>
              <div className="text-center">
                <CardTitle className="text-lg text-zinc-100">
                  {calendarData?.week_start && calendarData?.week_end ? (
                    `${format(parseISO(calendarData.week_start), 'MMM d')} - ${format(parseISO(calendarData.week_end), 'MMM d, yyyy')}`
                  ) : 'Loading...'}
                </CardTitle>
                {weekOffset !== 0 && (
                  <button
                    onClick={() => setWeekOffset(0)}
                    className="text-xs text-emerald-400 hover:underline"
                  >
                    Go to current week
                  </button>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setWeekOffset(prev => prev + 1)}
                className="text-zinc-400 hover:text-zinc-100"
                data-testid="next-week-btn"
              >
                <ChevronRight className="w-5 h-5" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === 'week' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('week')}
                className={viewMode === 'week' ? 'bg-emerald-600' : 'border-zinc-700'}
              >
                <LayoutGrid className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('list')}
                className={viewMode === 'list' ? 'bg-emerald-600' : 'border-zinc-700'}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loadingCalendar ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
            </div>
          ) : viewMode === 'week' ? (
            /* Week Grid View */
            <div className="grid grid-cols-7 gap-2">
              {/* Header */}
              {WEEKDAYS.map((day, idx) => {
                const date = weekDates[idx];
                const isToday = date && isSameDay(date, today);
                return (
                  <div
                    key={day}
                    className={`text-center p-2 rounded-t-lg ${isToday ? 'bg-emerald-600/20' : 'bg-zinc-800/50'}`}
                  >
                    <p className="text-xs text-zinc-500 uppercase">{day.slice(0, 3)}</p>
                    <p className={`text-lg font-semibold ${isToday ? 'text-emerald-400' : 'text-zinc-300'}`}>
                      {date ? format(date, 'd') : '-'}
                    </p>
                  </div>
                );
              })}
              
              {/* Day cells */}
              {weekDates.map((date, idx) => {
                const meetings = getMeetingsForDate(date);
                const isToday = isSameDay(date, today);
                return (
                  <div
                    key={idx}
                    className={`min-h-[200px] p-2 rounded-b-lg border ${
                      isToday ? 'border-emerald-600/50 bg-emerald-600/5' : 'border-zinc-800 bg-zinc-900/30'
                    }`}
                    data-testid={`calendar-day-${format(date, 'yyyy-MM-dd')}`}
                  >
                    {meetings.length === 0 ? (
                      <p className="text-xs text-zinc-600 text-center py-8">No meetings</p>
                    ) : (
                      <div className="space-y-2">
                        {meetings.map((meeting, mIdx) => (
                          <div
                            key={mIdx}
                            className={`p-2 rounded text-xs cursor-pointer transition-all hover:scale-[1.02] ${
                              meeting.has_conflict
                                ? 'bg-red-900/30 border border-red-700'
                                : meeting.is_delivered
                                ? 'bg-emerald-900/30 border border-emerald-700'
                                : 'bg-zinc-800 border border-zinc-700'
                            }`}
                            title={meeting.title}
                          >
                            <div className="flex items-center gap-1 text-zinc-400 mb-1">
                              <Clock className="w-3 h-3" />
                              <span>{meeting.time}</span>
                              {MODE_ICONS[meeting.mode]}
                              {meeting.is_recurring && <RefreshCw className="w-3 h-3 text-blue-400" />}
                            </div>
                            <p className="text-zinc-200 font-medium truncate">{meeting.title}</p>
                            <div className="flex items-center gap-1 mt-1 text-zinc-500">
                              <Users className="w-3 h-3" />
                              <span className="truncate">{meeting.attendees?.join(', ') || 'TBD'}</span>
                            </div>
                            {meeting.is_delivered ? (
                              <span className="inline-flex items-center gap-1 text-emerald-400 mt-1">
                                <CheckCircle className="w-3 h-3" /> Done
                              </span>
                            ) : meeting.has_conflict ? (
                              <span className="inline-flex items-center gap-1 text-red-400 mt-1">
                                <AlertTriangle className="w-3 h-3" /> Conflict
                              </span>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* List View */
            <div className="space-y-4">
              {weekDates.map((date, idx) => {
                const meetings = getMeetingsForDate(date);
                const isToday = isSameDay(date, today);
                if (meetings.length === 0) return null;
                
                return (
                  <div key={idx} className="border-l-2 border-zinc-700 pl-4">
                    <div className={`flex items-center gap-2 mb-2 ${isToday ? 'text-emerald-400' : 'text-zinc-300'}`}>
                      <Calendar className="w-4 h-4" />
                      <span className="font-semibold">{format(date, 'EEEE, MMM d')}</span>
                      {isToday && <span className="text-xs bg-emerald-600/30 px-2 py-0.5 rounded">Today</span>}
                    </div>
                    <div className="space-y-2 ml-6">
                      {meetings.map((meeting, mIdx) => (
                        <div
                          key={mIdx}
                          className={`p-3 rounded border ${
                            meeting.has_conflict
                              ? 'bg-red-900/20 border-red-800'
                              : meeting.is_delivered
                              ? 'bg-emerald-900/20 border-emerald-800'
                              : 'bg-zinc-800/50 border-zinc-700'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-1 text-zinc-400">
                                <Clock className="w-4 h-4" />
                                <span>{meeting.time}</span>
                              </div>
                              <span className="text-zinc-300 font-medium">{meeting.title}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              {MODE_ICONS[meeting.mode]}
                              {meeting.is_recurring && (
                                <span className="text-xs text-blue-400 flex items-center gap-1">
                                  <RefreshCw className="w-3 h-3" /> Recurring
                                </span>
                              )}
                              {meeting.is_delivered ? (
                                <span className="text-xs text-emerald-400 flex items-center gap-1">
                                  <CheckCircle className="w-3 h-3" /> Completed
                                </span>
                              ) : meeting.mom_generated ? (
                                <span className="text-xs text-amber-400">MOM Ready</span>
                              ) : (
                                <span className="text-xs text-zinc-500 flex items-center gap-1">
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
                      ))}
                    </div>
                  </div>
                );
              })}
              {calendarData?.total_meetings === 0 && (
                <div className="text-center py-12 text-zinc-500">
                  <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
                  <p>No meetings scheduled for this week</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Conflicts Alert */}
      {conflictsData?.total_conflicts > 0 && (
        <Card className="bg-red-900/20 border-red-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-400 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Scheduling Conflicts Detected
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {conflictsData.conflicts?.slice(0, 5).map((conflict, idx) => (
                <div key={idx} className="flex items-center gap-4 p-2 bg-red-900/30 rounded text-sm">
                  <span className="text-zinc-300">{conflict.consultant_name}</span>
                  <span className="text-red-400">has overlapping meetings:</span>
                  <span className="text-zinc-400">{conflict.meeting_1?.title} ↔ {conflict.meeting_2?.title}</span>
                  <span className="text-red-300 text-xs">({conflict.overlap_minutes} min overlap)</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default MeetingCalendar;
