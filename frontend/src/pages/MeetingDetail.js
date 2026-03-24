import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import PageHeader from '../components/ui/page-header';
import {
  ArrowLeft, Printer, FileText, Mail, Calendar, Clock, User, Users,
  MapPin, Video, Phone, CheckCircle, Circle, Hash, Layers, CheckSquare,
  AlertCircle, Paperclip, Edit, Building2
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const MeetingDetail = () => {
  const { meetingId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);

  // Fetch meeting details
  const { data: meeting, isLoading, error } = useQuery({
    queryKey: ['meeting-detail', meetingId],
    queryFn: async () => {
      const res = await axios.get(`${API}/meetings/${meetingId}`);
      return res.data;
    },
    enabled: !!meetingId,
  });

  // Fetch all meetings for series number calculation
  const { data: allMeetings = [] } = useQuery({
    queryKey: ['meetings', 'consulting'],
    queryFn: async () => {
      const res = await axios.get(`${API}/meetings?meeting_type=consulting`);
      return res.data || [];
    },
  });

  // Fetch projects for stats
  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects`);
      return res.data || [];
    },
  });

  const getMeetingSeriesNumber = () => {
    if (!meeting) return 1;
    const projectMeetings = allMeetings
      .filter(m => m.project_id === meeting.project_id)
      .sort((a, b) => new Date(a.meeting_date) - new Date(b.meeting_date));
    return (projectMeetings || []).findIndex(m => m.id === meeting.id) + 1;
  };

  const getProjectStats = () => {
    if (!meeting) return { committed: 0, delivered: 0, pending: 0 };
    const project = (projects || []).find(p => p.id === meeting.project_id);
    if (!project) return { committed: 0, delivered: 0, pending: 0 };
    const committed = project.total_meetings_committed || 0;
    const delivered = project.total_meetings_delivered || 0;
    return { committed, delivered, pending: committed - delivered };
  };

  const getModeIcon = (mode) => {
    if (mode === 'offline' || mode === 'in-person') return <MapPin className="w-5 h-5" />;
    if (mode === 'tele_call') return <Phone className="w-5 h-5" />;
    return <Video className="w-5 h-5" />;
  };

  const getModeLabel = (mode) => {
    if (mode === 'offline' || mode === 'in-person') return 'In-Person';
    if (mode === 'tele_call') return 'Tele Call';
    return 'Online';
  };

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-screen">
        <div className="text-zinc-500">Loading meeting details...</div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-red-800">Meeting Not Found</h2>
            <p className="text-red-600 mt-2">The requested meeting could not be found.</p>
            <Button onClick={() => navigate('/consulting-meetings')} className="mt-4">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Meetings
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Only show meeting details if MOM is recorded/submitted
  if (!meeting.mom_generated && !meeting.is_delivered) {
    return (
      <div className="p-6">
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-6 text-center">
            <FileText className="w-12 h-12 text-amber-500 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-amber-800">MOM Not Yet Recorded</h2>
            <p className="text-amber-600 mt-2">
              Minutes of Meeting have not been recorded for this meeting yet.
            </p>
            <p className="text-amber-600 text-sm mt-1">
              Please record the MOM first to view the complete meeting details.
            </p>
            <div className="flex justify-center gap-3 mt-4">
              <Button variant="outline" onClick={() => navigate('/consulting-meetings')}>
                <ArrowLeft className="w-4 h-4 mr-2" /> Back to Meetings
              </Button>
              <Button onClick={() => navigate(`/consulting-meetings?edit=${meetingId}`)}>
                <Edit className="w-4 h-4 mr-2" /> Record MOM
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = getProjectStats();
  const seriesNumber = getMeetingSeriesNumber();

  return (
    <div className="min-h-screen bg-zinc-50 print:bg-white" data-testid="meeting-detail-page">
      {/* Header - Hidden in Print */}
      <div className="print:hidden">
        <PageHeader
          title="Meeting Details"
          subtitle="Complete meeting record with MOM and action items"
          actions={
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => navigate('/consulting-meetings')}>
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <Button variant="outline" onClick={handlePrint}>
                <Printer className="w-4 h-4 mr-2" /> Print
              </Button>
              {!meeting.is_delivered && (
                <Button onClick={() => navigate(`/consulting-meetings?edit=${meetingId}`)}>
                  <Edit className="w-4 h-4 mr-2" /> Edit MOM
                </Button>
              )}
            </div>
          }
        />
      </div>

      {/* Print Header */}
      <div className="hidden print:block p-6 border-b border-zinc-200">
        <h1 className="text-2xl font-bold text-zinc-900">Meeting Details</h1>
        <p className="text-sm text-zinc-500">Printed on {format(new Date(), 'MMMM dd, yyyy HH:mm')}</p>
      </div>

      <div className="p-6 max-w-5xl mx-auto space-y-6 print:p-4 print:max-w-none">
        {/* Meeting Header Card */}
        <Card className="border-zinc-200 shadow-sm print:shadow-none print:border">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-zinc-900">{meeting.title || 'Meeting'}</h1>
                <p className="text-lg text-zinc-600 mt-1">{meeting.project_name}</p>
              </div>
              <div className="text-right space-y-2">
                <Badge variant="outline" className="text-base px-3 py-1">
                  <Hash className="w-4 h-4 mr-1" />
                  Meeting #{seriesNumber}
                </Badge>
                <div>
                  {meeting.is_delivered ? (
                    <Badge className="bg-emerald-100 text-emerald-700 text-sm">
                      <CheckCircle className="w-4 h-4 mr-1" /> Delivered
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-amber-600 border-amber-300 text-sm">
                      <Circle className="w-4 h-4 mr-1" /> Pending
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-2">
                  <Building2 className="w-4 h-4" /> Company
                </div>
                <div className="font-semibold text-zinc-800 text-lg">{meeting.client_name || '-'}</div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-2">
                  <Calendar className="w-4 h-4" /> Date & Time
                </div>
                <div className="font-semibold text-zinc-800">
                  {format(new Date(meeting.meeting_date), 'EEEE, MMM dd, yyyy')}
                </div>
                <div className="text-zinc-600">{format(new Date(meeting.meeting_date), 'HH:mm')}</div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-2">
                  {getModeIcon(meeting.mode)} Mode
                </div>
                <div className="font-semibold text-zinc-800">{getModeLabel(meeting.mode)}</div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-2">
                  <Clock className="w-4 h-4" /> Duration
                </div>
                <div className="font-semibold text-zinc-800">{meeting.duration_minutes || '-'} mins</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Project Meeting Progress */}
        <Card className="border-blue-200 bg-blue-50 shadow-sm print:shadow-none">
          <CardContent className="p-6">
            <div className="text-xs uppercase tracking-wide text-blue-700 mb-4 font-semibold">
              Project Meeting Progress
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="text-center p-4 bg-white rounded-lg border border-blue-200">
                <div className="text-3xl font-bold text-blue-800">{stats.committed}</div>
                <div className="text-sm text-blue-600 mt-1">Committed</div>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-emerald-200">
                <div className="text-3xl font-bold text-emerald-700">{stats.delivered}</div>
                <div className="text-sm text-emerald-600 mt-1">Completed</div>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-amber-200">
                <div className="text-3xl font-bold text-amber-700">{stats.pending}</div>
                <div className="text-sm text-amber-600 mt-1">Pending</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Consultant & Attendees */}
        <Card className="border-zinc-200 shadow-sm print:shadow-none">
          <CardContent className="p-6">
            <div className="text-xs uppercase tracking-wide text-zinc-500 mb-4 font-semibold flex items-center gap-2">
              <Users className="w-4 h-4" /> Consultant & Attendees
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <div className="text-sm text-zinc-500 mb-1">Created By</div>
                <div className="font-medium text-zinc-800 text-lg">{meeting.created_by_name || 'System'}</div>
              </div>
              <div>
                <div className="text-sm text-zinc-500 mb-1">Attendees</div>
                <div className="font-medium text-zinc-800">
                  {meeting.attendee_names?.length > 0 
                    ? meeting.attendee_names.join(', ') 
                    : '-'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Linked SOW Scopes */}
        {(meeting.sow_scopes?.length > 0 || meeting.sow_scope_ids?.length > 0) && (
          <Card className="border-indigo-200 bg-indigo-50 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="text-xs uppercase tracking-wide text-indigo-700 mb-4 font-semibold flex items-center gap-2">
                <Layers className="w-4 h-4" />
                Linked SOW Scopes ({meeting.sow_scopes?.length || meeting.sow_scope_ids?.length || 0})
              </div>
              <div className="flex flex-wrap gap-3">
                {meeting.sow_scopes?.map((scope, idx) => (
                  <Badge key={scope.id || idx} className="bg-white text-indigo-800 border border-indigo-200 px-4 py-2 text-sm">
                    <CheckSquare className="w-4 h-4 mr-2" />
                    {scope.name}
                  </Badge>
                ))}
                {!meeting.sow_scopes?.length && meeting.sow_scope_ids?.map((scopeId, idx) => (
                  <Badge key={scopeId} variant="outline" className="text-indigo-700 border-indigo-300 px-4 py-2">
                    Scope #{idx + 1}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Agenda */}
        {meeting.agenda?.length > 0 && (meeting?.agenda || []).some(a => a) && (
          <Card className="border-zinc-200 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-4 font-semibold">Agenda</div>
              <ul className="space-y-2">
                {(meeting?.agenda || []).filter(a => a).map((item, idx) => (
                  <li key={idx} className="flex items-start gap-3 text-zinc-700">
                    <span className="w-6 h-6 rounded-full bg-zinc-200 text-zinc-600 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* MOM Content */}
        {meeting.mom_generated ? (
          <Card className="border-emerald-200 shadow-sm print:shadow-none">
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-700">
                  <FileText className="w-5 h-5" />
                  <span className="text-sm font-semibold uppercase tracking-wide">Minutes of Meeting</span>
                </div>
                {meeting.mom_sent_to_client && (
                  <Badge className="bg-blue-100 text-blue-700">
                    <Mail className="w-4 h-4 mr-1" /> Sent to Client
                  </Badge>
                )}
              </div>

              {meeting.discussion_points?.length > 0 && (meeting?.discussion_points || []).some(d => d) && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-3 font-semibold">Discussion Points</div>
                  <ul className="space-y-2">
                    {(meeting?.discussion_points || []).filter(d => d).map((item, idx) => (
                      <li key={idx} className="flex items-start gap-3 text-zinc-700 bg-zinc-50 p-3 rounded-lg">
                        <CheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {meeting.decisions_made?.length > 0 && (meeting?.decisions_made || []).some(d => d) && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-zinc-500 mb-3 font-semibold">Decisions Made</div>
                  <ul className="space-y-2">
                    {(meeting?.decisions_made || []).filter(d => d).map((item, idx) => (
                      <li key={idx} className="flex items-start gap-3 text-zinc-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                        <CheckSquare className="w-4 h-4 text-emerald-700 mt-0.5 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card className="border-amber-200 bg-amber-50 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 text-amber-700">
                <AlertCircle className="w-6 h-6" />
                <div>
                  <div className="font-semibold">MOM Not Yet Recorded</div>
                  <p className="text-sm text-amber-600 mt-1">
                    Minutes of Meeting have not been recorded for this meeting yet.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Items */}
        {meeting.action_items?.length > 0 && (
          <Card className="border-zinc-200 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-4 font-semibold">
                Action Items ({meeting.action_items.length})
              </div>
              <div className="space-y-3">
                {(meeting?.action_items || []).map((item, idx) => (
                  <div 
                    key={item.id || idx} 
                    className={`flex items-start justify-between p-4 rounded-lg border ${
                      item.status === 'completed' 
                        ? 'bg-emerald-50 border-emerald-200' 
                        : 'bg-zinc-50 border-zinc-200'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      {item.status === 'completed' ? (
                        <CheckCircle className="w-6 h-6 text-emerald-600 mt-0.5" />
                      ) : (
                        <Circle className="w-6 h-6 text-zinc-400 mt-0.5" />
                      )}
                      <div>
                        <div className={`font-medium ${item.status === 'completed' ? 'line-through text-zinc-400' : 'text-zinc-800'}`}>
                          {item.description}
                        </div>
                        <div className="text-sm text-zinc-500 mt-2 flex items-center gap-4">
                          <span className="flex items-center gap-1">
                            <User className="w-4 h-4" />
                            {item.assigned_to_name || 'Unassigned'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {item.due_date ? format(new Date(item.due_date), 'MMM dd, yyyy') : 'No due date'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Badge variant="outline" className={`text-sm px-3 py-1 ${
                      item.priority === 'high' ? 'border-red-300 text-red-700 bg-red-50' :
                      item.priority === 'medium' ? 'border-yellow-300 text-yellow-700 bg-yellow-50' :
                      'border-zinc-300 text-zinc-600'
                    }`}>
                      {item.priority}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Attachments */}
        {meeting.mom_attachments?.length > 0 && (
          <Card className="border-zinc-200 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-4 font-semibold">
                Attachments ({meeting.mom_attachments.length})
              </div>
              <div className="flex flex-wrap gap-3">
                {(meeting?.mom_attachments || []).map((file, idx) => (
                  <div key={idx} className="flex items-center gap-3 px-4 py-3 bg-zinc-50 rounded-lg border border-zinc-200">
                    <Paperclip className="w-5 h-5 text-zinc-500" />
                    <span className="text-sm font-medium text-zinc-700">{file.name || file.filename}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Notes */}
        {meeting.notes && (
          <Card className="border-zinc-200 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="text-xs uppercase tracking-wide text-zinc-500 mb-4 font-semibold">Notes</div>
              <p className="text-zinc-700 whitespace-pre-wrap leading-relaxed">{meeting.notes}</p>
            </CardContent>
          </Card>
        )}

        {/* Next Meeting */}
        {meeting.next_meeting_date && (
          <Card className="border-amber-200 bg-amber-50 shadow-sm print:shadow-none">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <Calendar className="w-6 h-6 text-amber-700" />
                <div>
                  <div className="text-xs uppercase tracking-wide text-amber-600 mb-1">Next Meeting Scheduled</div>
                  <div className="font-semibold text-amber-800 text-lg">
                    {format(new Date(meeting.next_meeting_date), 'EEEE, MMMM dd, yyyy')} at {format(new Date(meeting.next_meeting_date), 'HH:mm')}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer Actions - Hidden in Print */}
        <div className="flex justify-between items-center pt-6 border-t border-zinc-200 print:hidden">
          <Button variant="outline" onClick={() => navigate('/consulting-meetings')}>
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Meetings
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handlePrint}>
              <Printer className="w-4 h-4 mr-2" /> Print
            </Button>
            {!meeting.is_delivered && (
              <Link to={`/consulting-meetings`}>
                <Button>
                  <Edit className="w-4 h-4 mr-2" /> Edit MOM
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MeetingDetail;
