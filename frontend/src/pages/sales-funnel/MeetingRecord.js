import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { 
  ArrowLeft, Calendar, Users, Clock, Video, MapPin, Plus, Trash2, 
  Save, CheckCircle, FileText, AlertCircle, ChevronRight, Eye,
  MessageSquare, Target, Handshake, ListChecks, Upload, Image, Mic,
  Download, X, File
} from 'lucide-react';
import { toast } from 'sonner';

const MeetingRecord = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const fileInputRef = useRef(null);
  
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  const [meetings, setMeetings] = useState([]);
  const [showMOMDialog, setShowMOMDialog] = useState(false);
  const [showViewMOMDialog, setShowViewMOMDialog] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState([]); // For new meeting
  
  // Meeting basic info
  const [formData, setFormData] = useState({
    meeting_date: new Date().toISOString().split('T')[0],
    meeting_time: '10:00',
    meeting_type: 'Online',
    attendees: [''],
    title: ''
  });

  // MOM (Minutes of Meeting) data
  const [momData, setMomData] = useState({
    notes: '',
    mom: '',
    discussion_points: [''],
    decisions_made: [''],
    client_expectations: [''],
    key_commitments: [''],
    action_items: [''],
    next_steps: ''
  });

  // Check if this is the first offline meeting
  const isFirstOfflineMeeting = () => {
    const offlineMeetings = meetings.filter(m => 
      m.meeting_type?.toLowerCase() === 'offline' || m.mode === 'offline'
    );
    return offlineMeetings.length === 0 && formData.meeting_type === 'Offline';
  };

  useEffect(() => {
    if (leadId) {
      fetchLead();
      fetchMeetings();
    } else {
      toast.error('No lead ID provided');
      navigate('/leads');
    }
  }, [leadId]);

  const fetchLead = async () => {
    try {
      const response = await axios.get(`${API}/leads/${leadId}`);
      setLead(response.data);
    } catch (error) {
      toast.error('Failed to fetch lead');
      navigate('/leads');
    }
  };

  const fetchMeetings = async () => {
    try {
      const response = await axios.get(`${API}/meetings/lead/${leadId}`);
      setMeetings(response.data || []);
    } catch (error) {
      console.error('Error fetching meetings:', error);
      setMeetings([]);
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

  // MOM list handlers
  const handleAddListItem = (field) => {
    setMomData(prev => ({
      ...prev,
      [field]: [...prev[field], '']
    }));
  };

  const handleRemoveListItem = (field, index) => {
    setMomData(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const handleListItemChange = (field, index, value) => {
    setMomData(prev => ({
      ...prev,
      [field]: prev[field].map((item, i) => i === index ? value : item)
    }));
  };

  // File upload handlers for offline meetings
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/webp', 'image/heic',
      'audio/mpeg', 'audio/wav', 'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/x-m4a'
    ];
    
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        toast.error(`Invalid file type: ${file.name}. Only photos and voice files allowed.`);
        continue;
      }
      if (file.size > 20 * 1024 * 1024) {
        toast.error(`File too large: ${file.name}. Maximum 20MB allowed.`);
        continue;
      }
      
      // Add to pending attachments
      const attachmentType = file.type.startsWith('image/') ? 'photo' : 'voice';
      setPendingAttachments(prev => [...prev, {
        file,
        name: file.name,
        type: attachmentType,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null
      }]);
    }
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removePendingAttachment = (index) => {
    setPendingAttachments(prev => {
      const newList = [...prev];
      if (newList[index].preview) {
        URL.revokeObjectURL(newList[index].preview);
      }
      newList.splice(index, 1);
      return newList;
    });
  };

  const uploadAttachmentsToMeeting = async (meetingId) => {
    for (const attachment of pendingAttachments) {
      const formDataUpload = new FormData();
      formDataUpload.append('file', attachment.file);
      formDataUpload.append('attachment_type', attachment.type);
      
      try {
        await axios.post(`${API}/meetings/${meetingId}/attachments`, formDataUpload, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } catch (error) {
        console.error('Failed to upload attachment:', error);
        toast.error(`Failed to upload ${attachment.name}`);
      }
    }
    setPendingAttachments([]);
  };

  // Open MOM dialog - validate basic fields first
  const handleOpenMOMDialog = () => {
    if (!formData.meeting_date || !formData.meeting_time) {
      toast.error('Please fill meeting date and time first');
      return;
    }
    
    // Check if first offline meeting requires attachment
    if (isFirstOfflineMeeting() && pendingAttachments.length === 0) {
      toast.error('Photo or voice attachment is required for first offline meeting');
      return;
    }
    
    setShowMOMDialog(true);
  };

  // Submit meeting with MOM
  const handleSubmitMeeting = async () => {
    // Validate MOM is filled
    if (!momData.mom.trim()) {
      toast.error('Minutes of Meeting (MOM) summary is required');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        lead_id: leadId,
        meeting_date: formData.meeting_date,
        meeting_time: formData.meeting_time,
        meeting_type: formData.meeting_type,
        title: formData.title || `Meeting with ${lead?.company || 'Client'}`,
        attendees: formData.attendees.filter(a => a.trim()),
        // MOM data
        notes: momData.notes,
        mom: momData.mom,
        discussion_points: momData.discussion_points.filter(d => d.trim()),
        decisions_made: momData.decisions_made.filter(d => d.trim()),
        client_expectations: momData.client_expectations.filter(c => c.trim()),
        key_commitments: momData.key_commitments.filter(k => k.trim()),
        action_items: momData.action_items.filter(a => a.trim()),
        next_steps: momData.next_steps
      };

      const response = await axios.post(`${API}/meetings/record`, payload);
      const meetingId = response.data.meeting_id;

      // Upload pending attachments if any
      if (pendingAttachments.length > 0 && meetingId) {
        toast.info('Uploading attachments...');
        await uploadAttachmentsToMeeting(meetingId);
      }

      toast.success('Meeting recorded with MOM successfully!');
      setShowMOMDialog(false);
      
      // Reset forms
      setFormData({
        meeting_date: new Date().toISOString().split('T')[0],
        meeting_time: '10:00',
        meeting_type: 'Online',
        attendees: [''],
        title: ''
      });
      setMomData({
        notes: '',
        mom: '',
        discussion_points: [''],
        decisions_made: [''],
        client_expectations: [''],
        key_commitments: [''],
        action_items: [''],
        next_steps: ''
      });
      
      // Refresh meetings list
      await fetchMeetings();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record meeting');
    } finally {
      setLoading(false);
    }
  };

  const handleViewMOM = (meeting) => {
    setSelectedMeeting(meeting);
    setShowViewMOMDialog(true);
  };

  const handleProceedToPricing = () => {
    navigate(`/sales-funnel/pricing-plans?leadId=${leadId}`);
  };

  return (
    <div className="max-w-5xl mx-auto" data-testid="meeting-record-page">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate(`/sales-funnel-onboarding?leadId=${leadId}`)}
          variant="ghost"
          className="hover:bg-zinc-100 rounded-sm mb-4"
          data-testid="back-to-funnel-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Sales Funnel
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Record Meeting
        </h1>
        {lead && (
          <p className="text-zinc-500">
            For: <span className="font-medium text-zinc-700">{lead.first_name} {lead.last_name}</span> - {lead.company}
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
            <CardDescription>
              Fill meeting details, then add Minutes of Meeting (MOM) to submit
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Meeting Title</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                placeholder={`Meeting with ${lead?.company || 'Client'}`}
                className="rounded-sm"
                data-testid="meeting-title-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Meeting Date *</Label>
                <Input
                  type="date"
                  value={formData.meeting_date}
                  onChange={(e) => setFormData({...formData, meeting_date: e.target.value})}
                  className="rounded-sm"
                  data-testid="meeting-date-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Meeting Time *</Label>
                <Input
                  type="time"
                  value={formData.meeting_time}
                  onChange={(e) => setFormData({...formData, meeting_time: e.target.value})}
                  className="rounded-sm"
                  data-testid="meeting-time-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Meeting Type *</Label>
              <Select
                value={formData.meeting_type}
                onValueChange={(value) => setFormData({...formData, meeting_type: value})}
              >
                <SelectTrigger className="rounded-sm" data-testid="meeting-type-select">
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
                <span className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Attendees
                </span>
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
                    data-testid={`attendee-input-${index}`}
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

            {/* MOM Required Notice */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Minutes of Meeting Required</p>
                  <p className="text-xs text-amber-600 mt-1">
                    You must fill MOM details before submitting the meeting. Click the button below to add MOM.
                  </p>
                </div>
              </div>
            </div>

            <Button
              onClick={handleOpenMOMDialog}
              className="w-full bg-blue-600 hover:bg-blue-700"
              data-testid="fill-mom-btn"
            >
              <FileText className="w-4 h-4 mr-2" />
              Fill MOM & Submit Meeting
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
            <CardDescription>
              All meetings recorded for this lead with MOM
            </CardDescription>
          </CardHeader>
          <CardContent>
            {meetings.length === 0 ? (
              <div className="text-center py-8 text-zinc-400">
                <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No meetings recorded yet</p>
                <p className="text-xs mt-1">Record your first meeting to proceed</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {meetings.map((meeting, index) => (
                  <div
                    key={meeting.id || index}
                    className="p-4 border border-zinc-100 rounded-lg hover:bg-zinc-50 cursor-pointer transition-colors"
                    onClick={() => handleViewMOM(meeting)}
                    data-testid={`meeting-card-${index}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {meeting.meeting_type === 'Online' || meeting.mode === 'online' ? (
                          <Video className="w-4 h-4 text-blue-500" />
                        ) : (
                          <MapPin className="w-4 h-4 text-orange-500" />
                        )}
                        <span className="font-medium text-sm">
                          {meeting.title || `Meeting ${index + 1}`}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        MOM Filled
                      </Badge>
                    </div>
                    
                    <div className="flex items-center gap-4 text-xs text-zinc-500 mb-2">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(meeting.meeting_date).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        })}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {meeting.meeting_time || new Date(meeting.meeting_date).toLocaleTimeString('en-IN', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                    
                    {meeting.attendees?.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-zinc-500 mb-2">
                        <Users className="w-3 h-3" />
                        {meeting.attendees.slice(0, 3).join(', ')}
                        {meeting.attendees.length > 3 && ` +${meeting.attendees.length - 3} more`}
                      </div>
                    )}
                    
                    {meeting.mom && (
                      <p className="text-xs text-zinc-600 line-clamp-2 bg-zinc-50 p-2 rounded mt-2">
                        <strong>MOM:</strong> {meeting.mom}
                      </p>
                    )}

                    <div className="flex items-center justify-end mt-2">
                      <Button variant="ghost" size="sm" className="text-xs h-7">
                        <Eye className="w-3 h-3 mr-1" />
                        View Details
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {meetings.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <Button
                  onClick={handleProceedToPricing}
                  className="w-full bg-green-600 hover:bg-green-700"
                  data-testid="proceed-to-pricing-btn"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Proceed to Pricing Plan
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* MOM Dialog */}
      <Dialog open={showMOMDialog} onOpenChange={setShowMOMDialog}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              Minutes of Meeting (MOM)
            </DialogTitle>
            <DialogDescription>
              Fill in the meeting details. MOM summary is required before submission.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-4">
            {/* Meeting Notes */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-zinc-500" />
                Meeting Notes
              </Label>
              <Textarea
                value={momData.notes}
                onChange={(e) => setMomData({...momData, notes: e.target.value})}
                placeholder="General notes from the meeting..."
                rows={3}
                className="rounded-sm"
                data-testid="mom-notes-input"
              />
            </div>

            {/* MOM Summary - Required */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-red-500" />
                MOM Summary *
                <Badge variant="destructive" className="text-xs">Required</Badge>
              </Label>
              <Textarea
                value={momData.mom}
                onChange={(e) => setMomData({...momData, mom: e.target.value})}
                placeholder="Summarize the key outcomes, action items, and next steps from this meeting..."
                rows={4}
                className="rounded-sm border-red-200 focus:border-red-400"
                data-testid="mom-summary-input"
              />
            </div>

            {/* Discussion Points */}
            <div className="space-y-2">
              <Label className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <ListChecks className="w-4 h-4 text-zinc-500" />
                  Discussion Points
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleAddListItem('discussion_points')} className="h-7">
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </Label>
              {momData.discussion_points.map((point, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={point}
                    onChange={(e) => handleListItemChange('discussion_points', index, e.target.value)}
                    placeholder="What was discussed..."
                    className="rounded-sm"
                  />
                  {momData.discussion_points.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => handleRemoveListItem('discussion_points', index)} className="text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Decisions Made */}
            <div className="space-y-2">
              <Label className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  Decisions Made
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleAddListItem('decisions_made')} className="h-7">
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </Label>
              {momData.decisions_made.map((decision, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={decision}
                    onChange={(e) => handleListItemChange('decisions_made', index, e.target.value)}
                    placeholder="Decision or agreement reached..."
                    className="rounded-sm"
                  />
                  {momData.decisions_made.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => handleRemoveListItem('decisions_made', index)} className="text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Client Expectations */}
            <div className="space-y-2">
              <Label className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-amber-500" />
                  Client Expectations & Concerns
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleAddListItem('client_expectations')} className="h-7">
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </Label>
              {momData.client_expectations.map((expectation, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={expectation}
                    onChange={(e) => handleListItemChange('client_expectations', index, e.target.value)}
                    placeholder="Client's expectation or concern..."
                    className="rounded-sm"
                  />
                  {momData.client_expectations.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => handleRemoveListItem('client_expectations', index)} className="text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Key Commitments */}
            <div className="space-y-2">
              <Label className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Handshake className="w-4 h-4 text-blue-500" />
                  Key Commitments Made
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleAddListItem('key_commitments')} className="h-7">
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </Label>
              {momData.key_commitments.map((commitment, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={commitment}
                    onChange={(e) => handleListItemChange('key_commitments', index, e.target.value)}
                    placeholder="Commitment or promise made to client..."
                    className="rounded-sm"
                  />
                  {momData.key_commitments.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => handleRemoveListItem('key_commitments', index)} className="text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Next Steps */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <ChevronRight className="w-4 h-4 text-zinc-500" />
                Next Steps
              </Label>
              <Textarea
                value={momData.next_steps}
                onChange={(e) => setMomData({...momData, next_steps: e.target.value})}
                placeholder="What are the next steps after this meeting..."
                rows={2}
                className="rounded-sm"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowMOMDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitMeeting} 
              disabled={loading || !momData.mom.trim()}
              className="bg-green-600 hover:bg-green-700"
              data-testid="submit-meeting-btn"
            >
              {loading ? (
                <>Saving...</>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Submit Meeting with MOM
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View MOM Dialog */}
      <Dialog open={showViewMOMDialog} onOpenChange={setShowViewMOMDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-500" />
              Meeting Details
            </DialogTitle>
            <DialogDescription>
              {selectedMeeting?.title || 'Meeting'} - {selectedMeeting?.meeting_date && new Date(selectedMeeting.meeting_date).toLocaleDateString()}
            </DialogDescription>
          </DialogHeader>

          {selectedMeeting && (
            <div className="space-y-4 py-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4 p-3 bg-zinc-50 rounded-lg">
                <div>
                  <p className="text-xs text-zinc-500">Date & Time</p>
                  <p className="font-medium">
                    {new Date(selectedMeeting.meeting_date).toLocaleDateString()} at {selectedMeeting.meeting_time || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500">Type</p>
                  <p className="font-medium">{selectedMeeting.meeting_type || selectedMeeting.mode}</p>
                </div>
                {selectedMeeting.attendees?.length > 0 && (
                  <div className="col-span-2">
                    <p className="text-xs text-zinc-500">Attendees</p>
                    <p className="font-medium">{selectedMeeting.attendees.join(', ')}</p>
                  </div>
                )}
              </div>

              {/* MOM Summary */}
              {selectedMeeting.mom && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs text-blue-600 font-medium mb-1">MOM Summary</p>
                  <p className="text-sm text-blue-900">{selectedMeeting.mom}</p>
                </div>
              )}

              {/* Notes */}
              {selectedMeeting.notes && (
                <div>
                  <p className="text-xs text-zinc-500 mb-1">Meeting Notes</p>
                  <p className="text-sm bg-zinc-50 p-2 rounded">{selectedMeeting.notes}</p>
                </div>
              )}

              {/* Discussion Points */}
              {selectedMeeting.discussion_points?.length > 0 && selectedMeeting.discussion_points.some(d => d) && (
                <div>
                  <p className="text-xs text-zinc-500 mb-1">Discussion Points</p>
                  <ul className="text-sm space-y-1">
                    {selectedMeeting.discussion_points.filter(d => d).map((point, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-zinc-400">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Client Expectations */}
              {selectedMeeting.client_expectations?.length > 0 && selectedMeeting.client_expectations.some(c => c) && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-600 font-medium mb-1">Client Expectations</p>
                  <ul className="text-sm space-y-1">
                    {selectedMeeting.client_expectations.filter(c => c).map((exp, i) => (
                      <li key={i} className="flex items-start gap-2 text-amber-900">
                        <Target className="w-3 h-3 mt-1 text-amber-500" />
                        {exp}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Key Commitments */}
              {selectedMeeting.key_commitments?.length > 0 && selectedMeeting.key_commitments.some(k => k) && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-xs text-green-600 font-medium mb-1">Key Commitments</p>
                  <ul className="text-sm space-y-1">
                    {selectedMeeting.key_commitments.filter(k => k).map((com, i) => (
                      <li key={i} className="flex items-start gap-2 text-green-900">
                        <Handshake className="w-3 h-3 mt-1 text-green-500" />
                        {com}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {selectedMeeting.next_steps && (
                <div>
                  <p className="text-xs text-zinc-500 mb-1">Next Steps</p>
                  <p className="text-sm bg-zinc-50 p-2 rounded">{selectedMeeting.next_steps}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowViewMOMDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MeetingRecord;
