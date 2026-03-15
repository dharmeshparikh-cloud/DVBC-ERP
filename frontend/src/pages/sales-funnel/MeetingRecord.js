import React, { useState, useContext, useRef, useEffect, useCallback } from 'react';
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
  Download, X, File, RefreshCw, Rocket, Route
} from 'lucide-react';
import { toast } from 'sonner';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import FollowUpActionButton from '../../components/FollowUpActionButton';
import MeetingLocationPicker from '../../components/MeetingLocationPicker';

// Draft storage key prefix
const DRAFT_KEY_PREFIX = 'mom_draft_';
const DRAFT_EXPIRY_DAYS = 2;

const MeetingRecord = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  const fileInputRef = useRef(null);
  const existingMeetingFileInputRef = useRef(null);  // For uploading to existing meetings
  
  const [loading, setLoading] = useState(false);
  const [showMOMDialog, setShowMOMDialog] = useState(false);
  const [showViewMOMDialog, setShowViewMOMDialog] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [hasDraft, setHasDraft] = useState(false);
  const [lastSavedDraft, setLastSavedDraft] = useState(null);
  
  // Meeting basic info
  const [formData, setFormData] = useState({
    meeting_date: new Date().toISOString().split('T')[0],
    meeting_time: '10:00',
    meeting_type: 'Online',
    attendees: [''],
    title: ''
  });

  // Travel data for offline meetings
  const [travelData, setTravelData] = useState({
    startLocation: '',
    startLocationData: null,
    endLocation: '',
    endLocationData: null,
    viaLocations: [],
    isRoundTrip: false,
    travelMode: 'DRIVING',
    distance: null,
    duration: null,
    totalKm: 0,
    startTime: '',
    endTime: ''
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

  // ===== Draft Auto-Save Logic =====
  const getDraftKey = useCallback(() => `${DRAFT_KEY_PREFIX}${leadId}`, [leadId]);
  
  // Load draft on mount
  useEffect(() => {
    if (!leadId) return;
    
    const draftKey = getDraftKey();
    const savedDraft = localStorage.getItem(draftKey);
    
    if (savedDraft) {
      try {
        const { data, timestamp } = JSON.parse(savedDraft);
        const savedDate = new Date(timestamp);
        const now = new Date();
        const daysDiff = (now - savedDate) / (1000 * 60 * 60 * 24);
        
        // Check if draft is within expiry period (2 days)
        if (daysDiff <= DRAFT_EXPIRY_DAYS) {
          setHasDraft(true);
          setLastSavedDraft(savedDate);
        } else {
          // Draft expired, remove it
          localStorage.removeItem(draftKey);
        }
      } catch (e) {
        localStorage.removeItem(draftKey);
      }
    }
  }, [leadId, getDraftKey]);
  
  // Auto-save draft when MOM data changes (debounced)
  useEffect(() => {
    if (!leadId || !showMOMDialog) return;
    
    // Only save if there's meaningful content
    const hasContent = momData.mom.trim() || momData.notes.trim() || 
                       momData.discussion_points.some(p => p.trim()) ||
                       momData.client_expectations.some(p => p.trim());
    
    if (!hasContent) return;
    
    const saveTimer = setTimeout(() => {
      const draftKey = getDraftKey();
      const draftData = {
        data: { formData, momData },
        timestamp: new Date().toISOString()
      };
      localStorage.setItem(draftKey, JSON.stringify(draftData));
      setLastSavedDraft(new Date());
      setHasDraft(true);
    }, 2000); // Debounce 2 seconds
    
    return () => clearTimeout(saveTimer);
  }, [momData, formData, leadId, showMOMDialog, getDraftKey]);
  
  // Restore draft
  const handleRestoreDraft = () => {
    const draftKey = getDraftKey();
    const savedDraft = localStorage.getItem(draftKey);
    
    if (savedDraft) {
      try {
        const { data } = JSON.parse(savedDraft);
        if (data.formData) setFormData(data.formData);
        if (data.momData) setMomData(data.momData);
        toast.success('Draft restored successfully');
      } catch (e) {
        toast.error('Failed to restore draft');
      }
    }
  };
  
  // Clear draft
  const handleClearDraft = () => {
    const draftKey = getDraftKey();
    localStorage.removeItem(draftKey);
    setHasDraft(false);
    setLastSavedDraft(null);
    toast.info('Draft cleared');
  };
  
  // Clear draft after successful submission
  const clearDraftAfterSubmit = () => {
    const draftKey = getDraftKey();
    localStorage.removeItem(draftKey);
    setHasDraft(false);
    setLastSavedDraft(null);
  };

  // Fetch lead and meetings with React Query
  const { data: meetingData, refetch: refetchMeetings } = useQuery({
    queryKey: ['meeting-records', leadId],
    queryFn: async () => {
      const [leadRes, meetingsRes] = await Promise.all([
        axios.get(`${API}/leads/${leadId}`),
        // Correct endpoint: /api/meetings/lead/{lead_id}
        axios.get(`${API}/meetings/lead/${leadId}`).catch(() => ({ data: [] }))
      ]);
      return {
        lead: leadRes.data,
        meetings: meetingsRes.data || []
      };
    },
    enabled: !!leadId,
    staleTime: 2 * 60 * 1000,
  });

  const lead = meetingData?.lead;
  const meetings = meetingData?.meetings || [];

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ['meeting-records', leadId] });
    refetchMeetings();
  };

  // Check if this is the first offline meeting
  const isFirstOfflineMeeting = () => {
    const offlineMeetings = meetings.filter(m => 
      m.meeting_type?.toLowerCase() === 'offline' || m.mode === 'offline'
    );
    return offlineMeetings.length === 0 && formData.meeting_type === 'Offline';
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

  // Handle file upload for EXISTING meeting cards
  const handleExistingMeetingFileSelect = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length || !selectedMeeting) return;
    
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm'];
    
    setUploadingFile(true);
    
    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        toast.error(`Invalid file type: ${file.name}. Only photos and voice files allowed.`);
        continue;
      }
      if (file.size > 20 * 1024 * 1024) {
        toast.error(`File too large: ${file.name}. Maximum 20MB allowed.`);
        continue;
      }
      
      const attachmentType = file.type.startsWith('image/') ? 'photo' : 'voice';
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);
      formDataUpload.append('attachment_type', attachmentType);
      
      try {
        await axios.post(`${API}/meetings/${selectedMeeting.id}/attachments`, formDataUpload, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast.success(`Uploaded ${file.name} successfully`);
      } catch (error) {
        console.error('Failed to upload attachment:', error);
        toast.error(`Failed to upload ${file.name}`);
      }
    }
    
    setUploadingFile(false);
    setSelectedMeeting(null);
    invalidateData();
    
    // Reset input
    if (existingMeetingFileInputRef.current) {
      existingMeetingFileInputRef.current.value = '';
    }
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
        next_steps: momData.next_steps,
        // Travel data for offline meetings
        ...(formData.meeting_type === 'Offline' && travelData.startLocation ? {
          travel_details: {
            start_location: travelData.startLocation,
            start_location_data: travelData.startLocationData,
            end_location: travelData.endLocation,
            end_location_data: travelData.endLocationData,
            via_locations: travelData.viaLocations,
            is_round_trip: travelData.isRoundTrip,
            travel_mode: travelData.travelMode,
            // Send ONE-WAY distance, backend will calculate round trip if needed
            distance_km: travelData.distance ? (travelData.distance.value / 1000) : 0,
            duration_seconds: travelData.duration?.value || 0,
            travel_start_time: travelData.startTime,
            travel_end_time: travelData.endTime,
            // Transit-specific fields
            transit_amount: travelData.transitAmount || 0,
            // Accompanied by
            accompanied_by: travelData.accompaniedBy || null
          }
        } : {})
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
      
      // Clear draft after successful submission
      clearDraftAfterSubmit();
      
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
      
      // Reset travel data
      setTravelData({
        startLocation: '',
        startLocationData: null,
        endLocation: '',
        endLocationData: null,
        viaLocations: [],
        isRoundTrip: false,
        travelMode: 'DRIVING',
        distance: null,
        duration: null,
        totalKm: 0,
        startTime: '',
        endTime: ''
      });
      
      // Refresh meetings list
      await invalidateData();
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

            {/* Travel Details for Offline Meetings */}
            {formData.meeting_type === 'Offline' && (
              <MeetingLocationPicker
                value={travelData}
                onChange={setTravelData}
                meetingType={formData.meeting_type}
                data-testid="meeting-location-picker"
              />
            )}

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

            {/* File Upload for Offline Meetings */}
            {formData.meeting_type === 'Offline' && (
              <div className="space-y-3">
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="flex items-start gap-2">
                    <Upload className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-800">
                        {isFirstOfflineMeeting() ? 'Attachment Required' : 'Add Attachments'}
                      </p>
                      <p className="text-xs text-blue-600 mt-1">
                        {isFirstOfflineMeeting() 
                          ? 'First offline meeting requires photo or voice recording as proof.' 
                          : 'You can optionally add photos or voice recordings from the meeting.'}
                      </p>
                    </div>
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,audio/*"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1"
                    data-testid="upload-photo-btn"
                  >
                    <Image className="w-4 h-4 mr-2" />
                    Add Photo
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1"
                    data-testid="upload-voice-btn"
                  >
                    <Mic className="w-4 h-4 mr-2" />
                    Add Voice
                  </Button>
                </div>

                {/* Pending Attachments Preview */}
                {pendingAttachments.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-zinc-500">Attachments to upload:</p>
                    {pendingAttachments.map((attachment, index) => (
                      <div 
                        key={index}
                        className="flex items-center gap-2 p-2 bg-zinc-50 rounded border border-zinc-200"
                      >
                        {attachment.type === 'photo' ? (
                          <Image className="w-4 h-4 text-blue-500" />
                        ) : (
                          <Mic className="w-4 h-4 text-purple-500" />
                        )}
                        <span className="text-sm flex-1 truncate">{attachment.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {attachment.type}
                        </Badge>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removePendingAttachment(index)}
                          className="h-6 w-6 p-0 text-red-500 hover:bg-red-50"
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

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
                      <Badge 
                        variant="outline" 
                        className="text-xs border-green-400 text-green-600 dark:border-green-500 dark:text-green-400"
                        style={{ backgroundColor: 'var(--green-bg, rgba(34, 197, 94, 0.15))' }}
                      >
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
                      <p className="text-xs text-zinc-600 line-clamp-2 bg-zinc-50 dark:bg-zinc-800 p-2 rounded mt-2">
                        <strong>MOM:</strong> {meeting.mom}
                      </p>
                    )}

                    {/* Attachment indicator */}
                    {meeting.has_attachments && (
                      <div className="flex items-center gap-1 text-xs text-emerald-600 mt-2">
                        <Image className="w-3 h-3" />
                        <span>Has attachments</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-xs h-7"
                          onClick={() => handleViewMOM(meeting)}
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          View
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-xs h-7 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950"
                          disabled={uploadingFile}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedMeeting(meeting);
                            existingMeetingFileInputRef.current?.click();
                          }}
                        >
                          <Upload className="w-3 h-3 mr-1" />
                          {uploadingFile && selectedMeeting?.id === meeting.id ? 'Uploading...' : 'Upload'}
                        </Button>
                      </div>
                      <FollowUpActionButton 
                        entityType="meeting" 
                        entityId={meeting.id} 
                        clientName={lead?.company || 'Client'} 
                        variant="ghost"
                        size="sm"
                        className="text-xs h-7"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {meetings.length > 0 && (
              <div className="mt-6 pt-4 border-t-2 border-green-200">
                {/* Prominent Call to Action */}
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 rounded-lg p-4 border border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-2 mb-3">
                    <Rocket className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-semibold text-green-800 dark:text-green-300">
                      Ready to Proceed!
                    </span>
                    <Badge className="bg-green-600 text-white text-xs">
                      {meetings.length} Meeting{meetings.length > 1 ? 's' : ''} Recorded
                    </Badge>
                  </div>
                  <p className="text-xs text-green-700 dark:text-green-400 mb-4">
                    You have recorded {meetings.length} meeting{meetings.length > 1 ? 's' : ''}. Proceed to create pricing plan for the client.
                  </p>
                  <Button
                    onClick={handleProceedToPricing}
                    size="lg"
                    className="w-full bg-green-600 hover:bg-green-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 h-12 text-base font-semibold"
                    data-testid="proceed-to-pricing-btn"
                  >
                    <Rocket className="w-5 h-5 mr-2" />
                    Proceed to Pricing Plan
                    <ChevronRight className="w-5 h-5 ml-2" />
                  </Button>
                </div>
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

          {/* Draft indicator and restore option */}
          {hasDraft && (
            <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-amber-600" />
                <span className="text-sm text-amber-800 dark:text-amber-300">
                  Draft saved {lastSavedDraft ? new Date(lastSavedDraft).toLocaleString() : 'recently'}
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRestoreDraft}
                  className="text-xs h-7 border-amber-300 text-amber-700 hover:bg-amber-100"
                >
                  Restore Draft
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearDraft}
                  className="text-xs h-7 text-zinc-500 hover:text-red-600"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}

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
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg dark:bg-green-950/30 dark:border-green-800">
                  <p className="text-xs text-green-600 font-medium mb-1 dark:text-green-400">Key Commitments</p>
                  <ul className="text-sm space-y-1">
                    {selectedMeeting.key_commitments.filter(k => k).map((com, i) => (
                      <li key={i} className="flex items-start gap-2 text-green-900 dark:text-green-300">
                        <Handshake className="w-3 h-3 mt-1 text-green-500" />
                        {com}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Travel Details for Offline Meetings */}
              {selectedMeeting.travel_details && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg dark:bg-blue-950/30 dark:border-blue-800">
                  <p className="text-xs text-blue-600 font-medium mb-3 dark:text-blue-400 flex items-center gap-2">
                    <Route className="w-4 h-4" />
                    Travel Details (Offline Meeting)
                  </p>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-green-600 mt-0.5" />
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400">From:</span>
                        <span className="ml-2 font-medium text-zinc-800 dark:text-zinc-200">{selectedMeeting.travel_details.start_location}</span>
                      </div>
                    </div>
                    {selectedMeeting.travel_details.via_locations?.length > 0 && (
                      <div className="flex items-start gap-2 pl-6">
                        <span className="text-zinc-400">↓</span>
                        <div className="text-zinc-600 dark:text-zinc-300">
                          Via: {selectedMeeting.travel_details.via_locations.map(v => v.address).join(' → ')}
                        </div>
                      </div>
                    )}
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-red-600 mt-0.5" />
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400">To:</span>
                        <span className="ml-2 font-medium text-zinc-800 dark:text-zinc-200">{selectedMeeting.travel_details.end_location}</span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700 grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400 text-xs">Mode:</span>
                        <span className="ml-2 font-medium text-zinc-800 dark:text-zinc-200">{selectedMeeting.travel_details.travel_mode}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400 text-xs">Round Trip:</span>
                        <span className="ml-2 font-medium text-zinc-800 dark:text-zinc-200">{selectedMeeting.travel_details.is_round_trip ? 'Yes' : 'No'}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400 text-xs">Distance:</span>
                        <span className="ml-2 font-bold text-green-700 dark:text-green-400">
                          {selectedMeeting.travel_details.distance_km} km
                          {selectedMeeting.travel_details.is_round_trip && ` (${(selectedMeeting.travel_details.distance_km * 2).toFixed(1)} km round trip)`}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-500 dark:text-zinc-400 text-xs">Travel Time:</span>
                        <span className="ml-2 font-medium text-zinc-800 dark:text-zinc-200">
                          {selectedMeeting.travel_details.travel_start_time} - {selectedMeeting.travel_details.travel_end_time}
                        </span>
                      </div>
                    </div>
                  </div>
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

      {/* Hidden file input for uploading to existing meetings */}
      <input
        ref={existingMeetingFileInputRef}
        type="file"
        accept="image/*,audio/*"
        multiple
        onChange={handleExistingMeetingFileSelect}
        className="hidden"
        data-testid="existing-meeting-file-input"
      />
    </div>
  );
};

export default MeetingRecord;
