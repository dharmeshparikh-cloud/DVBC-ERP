import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { 
  Calendar, Clock, Video, Users, MapPin, 
  CheckCircle, XCircle, RefreshCw, Loader2,
  Building2, FileText, CalendarPlus, AlertCircle
} from 'lucide-react';
import { format, parseISO } from 'date-fns';

const API = process.env.REACT_APP_BACKEND_URL;

const MeetingResponse = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const token = searchParams.get('token');
  const initialAction = searchParams.get('action');
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [responseData, setResponseData] = useState(null);
  const [selectedAction, setSelectedAction] = useState(initialAction);
  const [notes, setNotes] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  useEffect(() => {
    if (!token) {
      setError('Invalid link. No token provided.');
      setLoading(false);
      return;
    }

    // Fetch meeting details
    const fetchMeetingDetails = async () => {
      try {
        const res = await axios.get(`${API}/api/meeting-workflow/client-response`, {
          params: { token, action: initialAction || 'accept' }
        });
        setResponseData(res.data);
        
        if (res.data.status === 'already_responded') {
          setSubmitted(true);
          setSubmitResult({
            type: res.data.previous_response,
            message: res.data.message
          });
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load meeting details');
      } finally {
        setLoading(false);
      }
    };

    fetchMeetingDetails();
  }, [token, initialAction]);

  const handleSubmitResponse = async () => {
    if (!token || !selectedAction) return;
    
    setSubmitting(true);
    try {
      const res = await axios.post(
        `${API}/api/meeting-workflow/client-response`,
        { notes: notes || null },
        { params: { token, action: selectedAction } }
      );
      
      setSubmitted(true);
      setSubmitResult({
        type: res.data.response_type,
        message: res.data.message,
        newState: res.data.new_state
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit response');
    } finally {
      setSubmitting(false);
    }
  };

  const getModeIcon = (mode) => {
    switch (mode) {
      case 'online': return <Video className="w-4 h-4" />;
      case 'offline': return <Users className="w-4 h-4" />;
      case 'tele_call': return <MapPin className="w-4 h-4" />;
      default: return <Calendar className="w-4 h-4" />;
    }
  };

  const getModeLabel = (mode) => {
    switch (mode) {
      case 'online': return 'Video Conference';
      case 'offline': return 'In-Person Meeting';
      case 'tele_call': return 'Phone Call';
      default: return 'Meeting';
    }
  };

  const formatDate = (dateStr) => {
    try {
      return format(parseISO(dateStr), 'EEEE, MMMM d, yyyy');
    } catch {
      return dateStr;
    }
  };

  const formatTime = (dateStr) => {
    try {
      return format(parseISO(dateStr), 'h:mm a');
    } catch {
      return '';
    }
  };

  // Generate Google Calendar link
  const getCalendarLink = () => {
    if (!responseData?.meeting) return null;
    const { meeting } = responseData;
    
    try {
      const startDate = parseISO(meeting.meeting_date);
      const endDate = new Date(startDate.getTime() + (meeting.duration_minutes || 60) * 60000);
      
      const formatForCalendar = (date) => date.toISOString().replace(/-|:|\.\d+/g, '').slice(0, 15) + 'Z';
      
      return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(meeting.title || 'Consulting Meeting')}&dates=${formatForCalendar(startDate)}/${formatForCalendar(endDate)}&details=${encodeURIComponent('Meeting with D&V Business Consulting')}`;
    } catch {
      return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-emerald-600 mx-auto mb-4" />
          <p className="text-zinc-600">Loading meeting details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full shadow-lg">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-red-600" />
            </div>
            <h2 className="text-xl font-semibold text-zinc-900 mb-2">Unable to Load Meeting</h2>
            <p className="text-zinc-600 mb-6">{error}</p>
            <p className="text-sm text-zinc-500">
              If you believe this is an error, please contact the meeting organizer.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (responseData?.status === 'expired') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 to-yellow-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full shadow-lg">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Clock className="w-8 h-8 text-amber-600" />
            </div>
            <h2 className="text-xl font-semibold text-zinc-900 mb-2">Link Expired</h2>
            <p className="text-zinc-600 mb-4">{responseData.message}</p>
            <div className="text-sm text-zinc-500 bg-zinc-50 rounded-lg p-4">
              <p className="font-medium">{responseData.meeting?.title}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Submitted state
  if (submitted && submitResult) {
    const resultConfig = {
      'ACCEPTED': { 
        bg: 'from-emerald-50 to-teal-50', 
        icon: CheckCircle, 
        iconColor: 'text-emerald-600',
        iconBg: 'bg-emerald-100',
        title: 'Meeting Confirmed!'
      },
      'REJECTED': { 
        bg: 'from-red-50 to-orange-50', 
        icon: XCircle, 
        iconColor: 'text-red-600',
        iconBg: 'bg-red-100',
        title: 'Meeting Declined'
      },
      'RESCHEDULED': { 
        bg: 'from-amber-50 to-yellow-50', 
        icon: RefreshCw, 
        iconColor: 'text-amber-600',
        iconBg: 'bg-amber-100',
        title: 'Reschedule Requested'
      }
    };
    
    const config = resultConfig[submitResult.type] || resultConfig['ACCEPTED'];
    const Icon = config.icon;
    const calendarLink = getCalendarLink();

    return (
      <div className={`min-h-screen bg-gradient-to-br ${config.bg} flex items-center justify-center p-4`}>
        <Card className="max-w-md w-full shadow-lg">
          <CardContent className="p-8 text-center">
            <div className={`w-20 h-20 ${config.iconBg} rounded-full flex items-center justify-center mx-auto mb-6`}>
              <Icon className={`w-10 h-10 ${config.iconColor}`} />
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 mb-2">{config.title}</h2>
            <p className="text-zinc-600 mb-6">{submitResult.message}</p>
            
            {responseData?.meeting && (
              <div className="bg-zinc-50 rounded-lg p-4 mb-6 text-left">
                <p className="font-medium text-zinc-900">{responseData.meeting.title}</p>
                <p className="text-sm text-zinc-600 mt-1">
                  {formatDate(responseData.meeting.meeting_date)} at {formatTime(responseData.meeting.meeting_date)}
                </p>
              </div>
            )}
            
            {submitResult.type === 'ACCEPTED' && calendarLink && (
              <a 
                href={calendarLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                <CalendarPlus className="w-5 h-5" />
                Add to Google Calendar
              </a>
            )}
            
            <p className="text-xs text-zinc-400 mt-6">
              © {new Date().getFullYear()} D&V Business Consulting
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Response selection UI
  const meeting = responseData?.meeting;

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Building2 className="w-4 h-4" />
            D&V Business Consulting
          </div>
          <h1 className="text-3xl font-bold text-zinc-900">Meeting Invitation</h1>
          <p className="text-zinc-600 mt-2">Please respond to this meeting request</p>
        </div>

        {/* Meeting Details Card */}
        <Card className="shadow-lg mb-6">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-zinc-900">
                  {meeting?.title || 'Consulting Meeting'}
                </h2>
                <p className="text-zinc-600 mt-1">{meeting?.project_name}</p>
              </div>
              <Badge variant="outline" className="flex items-center gap-1">
                {getModeIcon(meeting?.mode)}
                {getModeLabel(meeting?.mode)}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-6">
              <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
                <Calendar className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Date</p>
                  <p className="font-medium text-zinc-900">
                    {meeting?.meeting_date ? formatDate(meeting.meeting_date) : 'TBD'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
                <Clock className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="text-xs text-zinc-500 uppercase">Time</p>
                  <p className="font-medium text-zinc-900">
                    {meeting?.meeting_date ? formatTime(meeting.meeting_date) : 'TBD'}
                    {meeting?.duration_minutes && ` (${meeting.duration_minutes} min)`}
                  </p>
                </div>
              </div>
            </div>

            {meeting?.agenda && meeting.agenda.length > 0 && meeting.agenda.some(a => a) && (
              <div className="mt-6 p-4 bg-emerald-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-emerald-700" />
                  <span className="font-medium text-emerald-800">Agenda</span>
                </div>
                <ul className="list-disc list-inside text-zinc-700 space-y-1">
                  {meeting.agenda.filter(a => a).map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-sm text-zinc-500 mt-4">
              Scheduled by: <span className="font-medium">{meeting?.scheduled_by_name || 'Consultant'}</span>
            </p>
          </CardContent>
        </Card>

        {/* Response Actions */}
        <Card className="shadow-lg">
          <CardContent className="p-6">
            <h3 className="font-semibold text-zinc-900 mb-4">Your Response</h3>
            
            <div className="grid grid-cols-3 gap-3 mb-6">
              <button
                onClick={() => setSelectedAction('accept')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedAction === 'accept' 
                    ? 'border-emerald-500 bg-emerald-50' 
                    : 'border-zinc-200 hover:border-emerald-300'
                }`}
              >
                <CheckCircle className={`w-8 h-8 mx-auto mb-2 ${
                  selectedAction === 'accept' ? 'text-emerald-600' : 'text-zinc-400'
                }`} />
                <span className={`font-medium ${
                  selectedAction === 'accept' ? 'text-emerald-700' : 'text-zinc-600'
                }`}>Accept</span>
              </button>
              
              <button
                onClick={() => setSelectedAction('reject')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedAction === 'reject' 
                    ? 'border-red-500 bg-red-50' 
                    : 'border-zinc-200 hover:border-red-300'
                }`}
              >
                <XCircle className={`w-8 h-8 mx-auto mb-2 ${
                  selectedAction === 'reject' ? 'text-red-600' : 'text-zinc-400'
                }`} />
                <span className={`font-medium ${
                  selectedAction === 'reject' ? 'text-red-700' : 'text-zinc-600'
                }`}>Decline</span>
              </button>
              
              <button
                onClick={() => setSelectedAction('reschedule')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedAction === 'reschedule' 
                    ? 'border-amber-500 bg-amber-50' 
                    : 'border-zinc-200 hover:border-amber-300'
                }`}
              >
                <RefreshCw className={`w-8 h-8 mx-auto mb-2 ${
                  selectedAction === 'reschedule' ? 'text-amber-600' : 'text-zinc-400'
                }`} />
                <span className={`font-medium ${
                  selectedAction === 'reschedule' ? 'text-amber-700' : 'text-zinc-600'
                }`}>Reschedule</span>
              </button>
            </div>

            {(selectedAction === 'reject' || selectedAction === 'reschedule') && (
              <div className="mb-6">
                <Label className="text-sm font-medium text-zinc-700">
                  {selectedAction === 'reschedule' ? 'Preferred times or notes (optional)' : 'Reason for declining (optional)'}
                </Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={selectedAction === 'reschedule' 
                    ? 'e.g., I would prefer Monday morning or Tuesday afternoon...'
                    : 'e.g., I have a conflict at this time...'
                  }
                  className="mt-2"
                  rows={3}
                />
              </div>
            )}

            <Button
              onClick={handleSubmitResponse}
              disabled={!selectedAction || submitting}
              className={`w-full py-6 text-lg font-medium ${
                selectedAction === 'accept' ? 'bg-emerald-600 hover:bg-emerald-700' :
                selectedAction === 'reject' ? 'bg-red-600 hover:bg-red-700' :
                selectedAction === 'reschedule' ? 'bg-amber-600 hover:bg-amber-700' :
                'bg-zinc-400'
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  {selectedAction === 'accept' && 'Confirm Attendance'}
                  {selectedAction === 'reject' && 'Decline Meeting'}
                  {selectedAction === 'reschedule' && 'Request Reschedule'}
                  {!selectedAction && 'Select Your Response'}
                </>
              )}
            </Button>

            <p className="text-xs text-center text-zinc-500 mt-4">
              This link will expire in 24 hours. If no response is received, the meeting will be automatically accepted.
            </p>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-zinc-500">
          <p>© {new Date().getFullYear()} D&V Business Consulting Pvt. Ltd.</p>
          <p className="mt-1">All rights reserved.</p>
        </div>
      </div>
    </div>
  );
};

export default MeetingResponse;
