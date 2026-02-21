import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ArrowLeft, Calendar, Users, Clock, Video, MapPin, Plus, Trash2, Save, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const MeetingRecord = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  const [meetings, setMeetings] = useState([]);
  
  const [formData, setFormData] = useState({
    meeting_date: new Date().toISOString().split('T')[0],
    meeting_time: '10:00',
    meeting_type: 'Online',
    attendees: [''],
    notes: '',
    mom: ''
  });

  useEffect(() => {
    if (leadId) {
      fetchLead();
      fetchMeetings();
    }
  }, [leadId]);

  const fetchLead = async () => {
    try {
      const response = await axios.get(`${API}/leads/${leadId}`);
      setLead(response.data);
    } catch (error) {
      toast.error('Failed to fetch lead');
    }
  };

  const fetchMeetings = async () => {
    try {
      const response = await axios.get(`${API}/meetings/lead/${leadId}`);
      setMeetings(response.data || []);
    } catch (error) {
      console.error('Error fetching meetings:', error);
    }
  };

  const handleAddAttendee = () => {
    setFormData(prev => ({
      ...prev,
      attendees: [...prev.attendees, '']
    }));
  };

  const handleRemoveAttendee = (index) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.filter((_, i) => i !== index)
    }));
  };

  const handleAttendeeChange = (index, value) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.map((a, i) => i === index ? value : a)
    }));
  };

  const handleSubmit = async () => {
    if (!formData.meeting_date || !formData.meeting_time || !formData.meeting_type) {
      toast.error('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/meetings/record`, {
        lead_id: leadId,
        meeting_date: formData.meeting_date,
        meeting_time: formData.meeting_time,
        meeting_type: formData.meeting_type,
        attendees: formData.attendees.filter(a => a.trim()),
        notes: formData.notes,
        mom: formData.mom
      });

      toast.success('Meeting recorded successfully');
      
      // Reset form
      setFormData({
        meeting_date: new Date().toISOString().split('T')[0],
        meeting_time: '10:00',
        meeting_type: 'Online',
        attendees: [''],
        notes: '',
        mom: ''
      });
      
      // Refresh meetings list
      await fetchMeetings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record meeting');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto" data-testid="meeting-record-page">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/leads')}
          variant="ghost"
          className="hover:bg-zinc-100 rounded-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Leads
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Record Meeting
        </h1>
        {lead && (
          <p className="text-zinc-500">
            For: {lead.first_name} {lead.last_name} - {lead.company}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Meeting Form */}
        <Card className="border-zinc-200 shadow-none">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="w-5 h-5 text-blue-500" />
              New Meeting
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Meeting Date *</Label>
                <Input
                  type="date"
                  value={formData.meeting_date}
                  onChange={(e) => setFormData({...formData, meeting_date: e.target.value})}
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <Label>Meeting Time *</Label>
                <Input
                  type="time"
                  value={formData.meeting_time}
                  onChange={(e) => setFormData({...formData, meeting_time: e.target.value})}
                  className="rounded-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Meeting Type *</Label>
              <Select
                value={formData.meeting_type}
                onValueChange={(value) => setFormData({...formData, meeting_type: value})}
              >
                <SelectTrigger className="rounded-sm">
                  <SelectValue placeholder="Select meeting type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Online">
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4" />
                      Online
                    </div>
                  </SelectItem>
                  <SelectItem value="Offline">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      Offline
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center justify-between">
                Attendees
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleAddAttendee}
                  className="h-7 text-xs"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Add
                </Button>
              </Label>
              {formData.attendees.map((attendee, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={attendee}
                    onChange={(e) => handleAttendeeChange(index, e.target.value)}
                    placeholder="Attendee name"
                    className="rounded-sm"
                  />
                  {formData.attendees.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveAttendee(index)}
                      className="text-red-500 hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <Label>Meeting Notes</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Key discussion points..."
                rows={3}
                className="rounded-sm"
              />
            </div>

            <div className="space-y-2">
              <Label>Minutes of Meeting (MOM)</Label>
              <Textarea
                value={formData.mom}
                onChange={(e) => setFormData({...formData, mom: e.target.value})}
                placeholder="Action items and decisions..."
                rows={4}
                className="rounded-sm"
              />
            </div>

            <Button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700"
            >
              {loading ? (
                <>Saving...</>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Meeting
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Meeting History */}
        <Card className="border-zinc-200 shadow-none">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock className="w-5 h-5 text-green-500" />
              Meeting History ({meetings.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {meetings.length === 0 ? (
              <div className="text-center py-8 text-zinc-400">
                <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No meetings recorded yet</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {meetings.map((meeting, index) => (
                  <div
                    key={meeting.id || index}
                    className="p-3 border border-zinc-100 rounded-lg hover:bg-zinc-50"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {meeting.meeting_type === 'Online' ? (
                          <Video className="w-4 h-4 text-blue-500" />
                        ) : (
                          <MapPin className="w-4 h-4 text-orange-500" />
                        )}
                        <span className="font-medium text-sm">
                          {new Date(meeting.meeting_date).toLocaleDateString('en-IN', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric'
                          })}
                        </span>
                        <span className="text-xs text-zinc-400">
                          {meeting.meeting_time}
                        </span>
                      </div>
                      <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                        {meeting.meeting_type}
                      </span>
                    </div>
                    
                    {meeting.attendees?.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-zinc-500 mb-2">
                        <Users className="w-3 h-3" />
                        {meeting.attendees.join(', ')}
                      </div>
                    )}
                    
                    {meeting.notes && (
                      <p className="text-xs text-zinc-600 line-clamp-2">{meeting.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {meetings.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <Button
                  onClick={() => navigate(`/sales-funnel/pricing?leadId=${leadId}`)}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Proceed to Pricing Plan
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MeetingRecord;
