import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Video, Phone, Users as UsersIcon, CheckCircle, Circle } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const Meetings = () => {
  const { user } = useContext(AuthContext);
  const [meetings, setMeetings] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    project_id: '',
    meeting_date: '',
    mode: 'online',
    duration_minutes: '',
    notes: '',
    is_delivered: false,
  });

  useEffect(() => {
    fetchMeetings();
    fetchProjects();
  }, []);

  const fetchMeetings = async () => {
    try {
      const response = await axios.get(`${API}/meetings`);
      setMeetings(response.data);
    } catch (error) {
      toast.error('Failed to fetch meetings');
    } finally {
      setLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API}/projects`);
      setProjects(response.data);
    } catch (error) {
      console.error('Failed to fetch projects');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const meetingData = {
        ...formData,
        meeting_date: new Date(formData.meeting_date).toISOString(),
        duration_minutes: formData.duration_minutes
          ? parseInt(formData.duration_minutes)
          : null,
      };
      await axios.post(`${API}/meetings`, meetingData);
      toast.success('Meeting scheduled successfully');
      setDialogOpen(false);
      setFormData({
        project_id: '',
        meeting_date: '',
        mode: 'online',
        duration_minutes: '',
        notes: '',
        is_delivered: false,
      });
      fetchMeetings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to schedule meeting');
    }
  };

  const getModeIcon = (mode) => {
    switch (mode) {
      case 'online':
        return <Video className="w-4 h-4" strokeWidth={1.5} />;
      case 'offline':
        return <UsersIcon className="w-4 h-4" strokeWidth={1.5} />;
      case 'tele_call':
        return <Phone className="w-4 h-4" strokeWidth={1.5} />;
      default:
        return <Video className="w-4 h-4" strokeWidth={1.5} />;
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
            Meetings
          </h1>
          <p className="text-zinc-500">Track your client meetings and deliverables</p>
        </div>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                data-testid="add-meeting-button"
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Schedule Meeting
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
                  Schedule New Meeting
                </DialogTitle>
                <DialogDescription className="text-zinc-500">
                  Schedule a meeting and track project deliverables
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="project_id" className="text-sm font-medium text-zinc-950">
                    Project *
                  </Label>
                  <select
                    id="project_id"
                    data-testid="meeting-project"
                    value={formData.project_id}
                    onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                    required
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  >
                    <option value="">Select a project</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name} - {project.client_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="meeting_date" className="text-sm font-medium text-zinc-950">
                    Meeting Date & Time *
                  </Label>
                  <Input
                    id="meeting_date"
                    data-testid="meeting-date"
                    type="datetime-local"
                    value={formData.meeting_date}
                    onChange={(e) => setFormData({ ...formData, meeting_date: e.target.value })}
                    required
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="mode" className="text-sm font-medium text-zinc-950">
                    Meeting Mode *
                  </Label>
                  <select
                    id="mode"
                    data-testid="meeting-mode"
                    value={formData.mode}
                    onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                    required
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  >
                    <option value="online">Online</option>
                    <option value="offline">Offline (In-person)</option>
                    <option value="tele_call">Tele Call</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="duration_minutes" className="text-sm font-medium text-zinc-950">
                    Duration (minutes)
                  </Label>
                  <Input
                    id="duration_minutes"
                    data-testid="meeting-duration"
                    type="number"
                    min="0"
                    value={formData.duration_minutes}
                    onChange={(e) =>
                      setFormData({ ...formData, duration_minutes: e.target.value })
                    }
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-medium text-zinc-950">
                    Notes
                  </Label>
                  <textarea
                    id="notes"
                    data-testid="meeting-notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="is_delivered"
                    data-testid="meeting-delivered"
                    checked={formData.is_delivered}
                    onChange={(e) =>
                      setFormData({ ...formData, is_delivered: e.target.checked })
                    }
                    className="w-4 h-4 rounded-sm border-zinc-200"
                  />
                  <Label htmlFor="is_delivered" className="text-sm font-medium text-zinc-950">
                    Mark as delivered
                  </Label>
                </div>

                <Button
                  type="submit"
                  data-testid="submit-meeting-button"
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
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
            <p className="text-zinc-500 mb-4">No meetings found</p>
            {canEdit && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
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
                            {project?.name || 'Unknown Project'}
                          </div>
                          <div className="text-sm text-zinc-500">
                            {project?.client_name || 'Unknown Client'}
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 mt-3">
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                            Date & Time
                          </div>
                          <div className="text-sm text-zinc-950 data-text">
                            {format(new Date(meeting.meeting_date), 'MMM dd, yyyy HH:mm')}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                            Mode
                          </div>
                          <div className="text-sm text-zinc-950">
                            {meeting.mode === 'online'
                              ? 'Online'
                              : meeting.mode === 'offline'
                              ? 'In-person'
                              : 'Tele Call'}
                          </div>
                        </div>
                        {meeting.duration_minutes && (
                          <div>
                            <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                              Duration
                            </div>
                            <div className="text-sm text-zinc-950 data-text">
                              {meeting.duration_minutes} mins
                            </div>
                          </div>
                        )}
                      </div>
                      {meeting.notes && (
                        <div className="mt-3 pt-3 border-t border-zinc-200">
                          <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                            Notes
                          </div>
                          <div className="text-sm text-zinc-600">{meeting.notes}</div>
                        </div>
                      )}
                    </div>
                    <div className="ml-4">
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
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Meetings;
