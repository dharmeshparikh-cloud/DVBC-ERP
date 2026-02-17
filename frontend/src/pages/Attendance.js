import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Upload, CheckCircle, XCircle, Clock, CalendarDays, Building2, MapPin, Home, Camera, Navigation, Loader2, LogIn, LogOut, AlertCircle, Car, Bike, RotateCcw, Send, X, Briefcase } from 'lucide-react';
import { toast } from 'sonner';

const STATUSES = [
  { value: 'present', label: 'Present', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'absent', label: 'Absent', color: 'bg-red-100 text-red-700' },
  { value: 'half_day', label: 'Half Day', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'work_from_home', label: 'WFH', color: 'bg-blue-100 text-blue-700' },
  { value: 'on_leave', label: 'On Leave', color: 'bg-purple-100 text-purple-700' },
  { value: 'holiday', label: 'Holiday', color: 'bg-zinc-100 text-zinc-700' }
];

const WORK_LOCATIONS = [
  { value: 'in_office', label: 'In', icon: Building2, color: 'blue' },
  { value: 'onsite', label: 'On-Site', icon: MapPin, color: 'emerald' },
  { value: 'wfh', label: 'Work', icon: Home, color: 'amber' }
];

const Attendance = () => {
  const { user } = useContext(AuthContext);
  const [employees, setEmployees] = useState([]);
  const [summary, setSummary] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [formData, setFormData] = useState({ 
    employee_id: '', 
    date: new Date().toISOString().split('T')[0], 
    status: 'present', 
    work_location: 'in_office', 
    remarks: '',
    check_in_time: '',
    check_out_time: '',
    client_id: '',
    client_name: '',
    project_id: '',
    project_name: ''
  });
  const [uploadText, setUploadText] = useState('');
  
  // Advanced attendance states (like mobile app)
  const [selfieData, setSelfieData] = useState(null);
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationVerified, setLocationVerified] = useState(false);
  const [officeLocations, setOfficeLocations] = useState([]);
  const [cameraActive, setCameraActive] = useState(false);
  const [stream, setStream] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  // Client/Project selection for On-Site
  const [assignedClients, setAssignedClients] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);
  
  // Travel Reimbursement Modal
  const [showTravelModal, setShowTravelModal] = useState(false);
  const [travelData, setTravelData] = useState(null);
  const [travelVehicle, setTravelVehicle] = useState('car');
  const [submittingTravel, setSubmittingTravel] = useState(false);

  const isHR = ['admin', 'hr_manager', 'hr_executive'].includes(user?.role);

  useEffect(() => { fetchData(); fetchOfficeLocations(); }, [month]);
  
  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [stream]);

  const fetchData = async () => {
    try {
      const [empRes, summaryRes, recordsRes] = await Promise.all([
        axios.get(`${API}/employees`),
        axios.get(`${API}/attendance/summary?month=${month}`),
        axios.get(`${API}/attendance?month=${month}`)
      ]);
      setEmployees(empRes.data);
      setSummary(summaryRes.data);
      setRecords(recordsRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const fetchOfficeLocations = async () => {
    try {
      const res = await axios.get(`${API}/settings/office-locations`);
      setOfficeLocations(res.data.locations || []);
    } catch (e) {
      setOfficeLocations([{ name: 'Main Office', latitude: 12.9716, longitude: 77.5946, radius: 500 }]);
    }
  };
  
  // Fetch assigned clients when On-Site is selected
  const fetchAssignedClients = async () => {
    setLoadingClients(true);
    try {
      const res = await axios.get(`${API}/my/assigned-clients`);
      setAssignedClients(res.data.clients || []);
    } catch (e) {
      // Fallback: fetch all clients
      try {
        const clientsRes = await axios.get(`${API}/clients`);
        setAssignedClients(clientsRes.data.map(c => ({
          id: c.id,
          client_name: c.company_name,
          project_name: null
        })));
      } catch (e2) {
        setAssignedClients([]);
      }
    } finally {
      setLoadingClients(false);
    }
  };

  // Camera functions - Fixed implementation
  const startCamera = useCallback(async () => {
    try {
      // First stop any existing stream
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } 
      });
      
      setStream(mediaStream);
      setCameraActive(true);
      
      // Wait for next render cycle then attach stream
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          videoRef.current.play().catch(e => console.log('Video play error:', e));
        }
      }, 100);
      
    } catch (err) {
      console.error('Camera error:', err);
      toast.error('Unable to access camera. Please grant camera permission.');
    }
  }, [stream]);

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, [stream]);

  const captureSelfie = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) {
      toast.error('Camera not ready');
      return;
    }
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Ensure video has dimensions
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      toast.error('Camera not ready. Please wait.');
      return;
    }
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
    setSelfieData(dataUrl);
    stopCamera();
    toast.success('Selfie captured!');
  }, [stopCamera]);

  // Location functions
  const captureLocation = () => {
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const coords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        };
        
        // Reverse geocode to get address
        try {
          const res = await axios.get(`${API}/travel/location-search?query=${coords.latitude},${coords.longitude}`);
          if (res.data.results?.length > 0) {
            coords.address = res.data.results[0].address;
          }
        } catch (e) {
          coords.address = `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`;
        }
        
        setLocation(coords);
        
        // Check geo-fencing (for in_office)
        if (formData.work_location === 'in_office' && officeLocations.length > 0) {
          const isInRange = officeLocations.some(office => {
            const distance = calculateDistance(coords.latitude, coords.longitude, office.latitude, office.longitude);
            return distance <= (office.radius || 500);
          });
          setLocationVerified(isInRange);
          if (!isInRange) {
            toast.warning('You are outside office geo-fence (500m radius)');
          } else {
            toast.success('Location verified - within office premises');
          }
        } else {
          setLocationVerified(true);
          toast.success('Location captured');
        }
        
        setLocationLoading(false);
      },
      (error) => {
        toast.error('Unable to get location. Please enable GPS.');
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  // Haversine formula for distance calculation
  const calculateDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371000; // Earth's radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate client selection for onsite
    if (formData.work_location === 'onsite' && !formData.client_name) {
      toast.error('Please select a client for On-Site attendance');
      return;
    }
    
    // Build payload
    const payload = {
      ...formData,
      geo_location: location,
      selfie: selfieData
    };
    
    try {
      await axios.post(`${API}/attendance`, payload);
      toast.success('Attendance recorded');
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record attendance');
    }
  };

  const resetForm = () => {
    setFormData({ 
      employee_id: '', 
      date: new Date().toISOString().split('T')[0], 
      status: 'present', 
      work_location: 'in_office', 
      remarks: '',
      check_in_time: '',
      check_out_time: '',
      client_id: '',
      client_name: '',
      project_id: '',
      project_name: ''
    });
    setSelfieData(null);
    setLocation(null);
    setLocationVerified(false);
    stopCamera();
  };
  
  // Handle work location change - fetch clients if onsite
  const handleWorkLocationChange = (value) => {
    setFormData({ ...formData, work_location: value, client_id: '', client_name: '', project_id: '', project_name: '' });
    setLocation(null);
    setLocationVerified(false);
    
    if (value === 'onsite') {
      fetchAssignedClients();
    }
  };
  
  // Handle client selection
  const handleClientSelect = (clientId) => {
    const client = assignedClients.find(c => c.id === clientId);
    if (client) {
      setFormData({
        ...formData,
        client_id: client.id,
        client_name: client.client_name,
        project_id: client.project_id || '',
        project_name: client.project_name || ''
      });
    }
  };
  
  // Submit Travel Reimbursement
  const handleSubmitTravelClaim = async () => {
    if (!travelData) return;
    
    setSubmittingTravel(true);
    try {
      const rate = travelVehicle === 'car' ? 7 : 3;
      const amount = Math.round(travelData.distance_km * rate);
      
      await axios.post(`${API}/travel/reimbursement`, {
        start_location: {
          name: travelData.from_location,
          address: travelData.from_location,
          latitude: travelData.office_lat,
          longitude: travelData.office_lon
        },
        end_location: {
          name: travelData.to_location,
          address: travelData.to_location,
          latitude: travelData.client_lat,
          longitude: travelData.client_lon
        },
        vehicle_type: travelVehicle,
        is_round_trip: true,
        travel_type: 'attendance',
        attendance_id: travelData.attendance_id,
        travel_date: new Date().toISOString().split('T')[0],
        client_id: travelData.client_id,
        client_name: travelData.client_name,
        project_id: travelData.project_id,
        notes: `Travel to client site: ${travelData.client_name || travelData.to_location}`
      });
      
      toast.success(`Travel claim submitted! Amount: Rs ${amount}`);
      setShowTravelModal(false);
      setTravelData(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit travel claim');
    } finally {
      setSubmittingTravel(false);
    }
  };

  const handleBulkUpload = async () => {
    try {
      const lines = uploadText.trim().split('\n');
      const records = lines.slice(1).map(line => {
        const cols = line.split(',').map(c => c.trim());
        return { employee_id: cols[0], date: cols[1], status: cols[2] || 'present', remarks: cols[3] || '' };
      }).filter(r => r.employee_id && r.date);
      if (records.length === 0) { toast.error('No valid records found'); return; }
      const res = await axios.post(`${API}/attendance/bulk`, records);
      toast.success(`${res.data.created} created, ${res.data.updated} updated`);
      setUploadDialogOpen(false);
      setUploadText('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    }
  };

  const getStatusBadge = (status) => {
    const s = STATUSES.find(st => st.value === status);
    return s ? s.color : 'bg-zinc-100 text-zinc-700';
  };

  const totalPresent = summary.reduce((s, r) => s + r.present, 0);
  const totalAbsent = summary.reduce((s, r) => s + r.absent, 0);

  return (
    <div data-testid="attendance-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Attendance</h1>
          <p className="text-zinc-500">Track employee attendance with manual entry or Excel upload</p>
        </div>
        {isHR && (
          <div className="flex gap-2">
            <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-sm" data-testid="upload-attendance-btn">
                  <Upload className="w-4 h-4 mr-2" /> Bulk Upload
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Bulk Upload</DialogTitle>
                  <DialogDescription className="text-zinc-500">Paste CSV data: employee_id, date (YYYY-MM-DD), status, remarks</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="p-2 bg-zinc-50 rounded-sm border border-zinc-200 text-xs font-mono text-zinc-600">
                    employee_id,date,status,remarks<br/>
                    EMP001,{month}-01,present,<br/>
                    EMP002,{month}-01,absent,Sick
                  </div>
                  <textarea value={uploadText} onChange={(e) => setUploadText(e.target.value)}
                    rows={8} className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent text-sm font-mono"
                    placeholder="Paste CSV data here..." data-testid="upload-csv-input" />
                  <Button onClick={handleBulkUpload} className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="process-upload-btn">
                    Process Upload
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) { resetForm(); stopCamera(); } }}>
              <DialogTrigger asChild>
                <Button className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="add-attendance-btn">
                  <Plus className="w-4 h-4 mr-2" /> Mark Attendance
                </Button>
              </DialogTrigger>
              <DialogContent className="border-zinc-200 rounded-sm max-w-lg max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Mark Attendance</DialogTitle>
                  <DialogDescription className="text-zinc-500">Record attendance with selfie and location verification</DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Employee Selection */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Employee</Label>
                    <select value={formData.employee_id} onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                      required className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="att-employee-select">
                      <option value="">Select employee</option>
                      {employees.map(e => <option key={e.id} value={e.id}>{e.employee_id} - {e.first_name} {e.last_name}</option>)}
                    </select>
                  </div>
                  
                  {/* Date and Status */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Date</Label>
                      <Input type="date" value={formData.date} onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                        required className="rounded-sm border-zinc-200" data-testid="att-date" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Status</Label>
                      <select value={formData.status} onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                        className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm" data-testid="att-status">
                        {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                      </select>
                    </div>
                  </div>
                  
                  {/* Work Location - only show when status is present or half_day */}
                  {['present', 'half_day'].includes(formData.status) && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950">Work Location</Label>
                      <div className="grid grid-cols-3 gap-2">
                        {WORK_LOCATIONS.map(loc => {
                          const Icon = loc.icon;
                          const isSelected = formData.work_location === loc.value;
                          return (
                            <button
                              key={loc.value}
                              type="button"
                              onClick={() => handleWorkLocationChange(loc.value)}
                              className={`flex flex-col items-center gap-1 p-3 rounded-md border transition-all ${
                                isSelected
                                  ? `border-${loc.color}-500 bg-${loc.color}-50 ring-2 ring-${loc.color}-200` 
                                  : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                              }`}
                              data-testid={`att-location-${loc.value}`}
                            >
                              <Icon className={`w-5 h-5 ${isSelected ? `text-${loc.color}-600` : 'text-zinc-500'}`} />
                              <span className="text-xs font-medium text-zinc-700">{loc.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  {/* Client Selection for On-Site */}
                  {formData.work_location === 'onsite' && ['present', 'half_day'].includes(formData.status) && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-emerald-600" /> Select Client
                      </Label>
                      {loadingClients ? (
                        <div className="flex items-center gap-2 p-3 bg-zinc-50 rounded-md">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-sm text-zinc-500">Loading clients...</span>
                        </div>
                      ) : assignedClients.length > 0 ? (
                        <select 
                          value={formData.client_id} 
                          onChange={(e) => handleClientSelect(e.target.value)}
                          required
                          className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                          data-testid="att-client-select"
                        >
                          <option value="">Select client</option>
                          {assignedClients.map(c => (
                            <option key={c.id} value={c.id}>
                              {c.client_name} {c.project_name ? `(${c.project_name})` : ''}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-md">
                          <p className="text-sm text-amber-700">No assigned clients found. Enter manually:</p>
                          <Input 
                            value={formData.client_name}
                            onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                            placeholder="Enter client name"
                            className="mt-2 rounded-sm border-zinc-200"
                          />
                        </div>
                      )}
                      {formData.client_name && (
                        <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-md">
                          <p className="text-sm text-emerald-700 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4" />
                            Selected: <strong>{formData.client_name}</strong>
                            {formData.project_name && <span className="text-emerald-600">({formData.project_name})</span>}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Check-in / Check-out Times - Auto-stamped on button click */}
                  {['present', 'half_day'].includes(formData.status) && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                          <LogIn className="w-4 h-4 text-emerald-600" /> Check-In Time
                        </Label>
                        {formData.check_in_time ? (
                          <div className="flex items-center gap-2 h-10 px-3 rounded-sm border border-emerald-200 bg-emerald-50">
                            <CheckCircle className="w-4 h-4 text-emerald-600" />
                            <span className="text-sm font-medium text-emerald-700">{formData.check_in_time}</span>
                          </div>
                        ) : (
                          <Button 
                            type="button" 
                            onClick={() => setFormData({ ...formData, check_in_time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) })}
                            variant="outline"
                            className="w-full h-10 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                            data-testid="punch-in-btn"
                          >
                            <LogIn className="w-4 h-4 mr-2" /> Punch In Now
                          </Button>
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                          <LogOut className="w-4 h-4 text-red-600" /> Check-Out Time
                        </Label>
                        {formData.check_out_time ? (
                          <div className="flex items-center gap-2 h-10 px-3 rounded-sm border border-red-200 bg-red-50">
                            <CheckCircle className="w-4 h-4 text-red-600" />
                            <span className="text-sm font-medium text-red-700">{formData.check_out_time}</span>
                          </div>
                        ) : (
                          <Button 
                            type="button" 
                            onClick={() => setFormData({ ...formData, check_out_time: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) })}
                            variant="outline"
                            className="w-full h-10 border-red-300 text-red-700 hover:bg-red-50"
                            disabled={!formData.check_in_time}
                            data-testid="punch-out-btn"
                          >
                            <LogOut className="w-4 h-4 mr-2" /> Punch Out Now
                          </Button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Selfie & Location - Always show for present/half_day */}
                  {['present', 'half_day'].includes(formData.status) && (
                    <>
                      {/* Selfie Capture - FIXED IMPLEMENTATION */}
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                          <Camera className="w-4 h-4" /> Selfie Verification
                        </Label>
                        <div className="border border-zinc-200 rounded-md p-3 bg-zinc-50">
                          {selfieData ? (
                            <div className="relative">
                              <img src={selfieData} alt="Selfie" className="w-full h-40 object-cover rounded-md" />
                              <button
                                type="button"
                                onClick={() => { setSelfieData(null); startCamera(); }}
                                className="absolute top-2 right-2 px-2 py-1 bg-zinc-900/70 text-white text-xs rounded flex items-center gap-1"
                              >
                                <RotateCcw className="w-3 h-3" /> Retake
                              </button>
                              <div className="absolute bottom-2 left-2 px-2 py-1 bg-emerald-500 text-white text-xs rounded flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" /> Captured
                              </div>
                            </div>
                          ) : cameraActive ? (
                            <div className="space-y-2">
                              <div className="relative rounded-md overflow-hidden bg-black aspect-video">
                                <video 
                                  ref={videoRef} 
                                  autoPlay 
                                  playsInline 
                                  muted 
                                  className="w-full h-full object-cover"
                                />
                              </div>
                              <div className="flex gap-2">
                                <Button type="button" onClick={captureSelfie} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white">
                                  <Camera className="w-4 h-4 mr-2" /> Capture
                                </Button>
                                <Button type="button" onClick={stopCamera} variant="outline" className="flex-1">
                                  <X className="w-4 h-4 mr-2" /> Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <Button type="button" onClick={startCamera} variant="outline" className="w-full" data-testid="start-camera-btn">
                              <Camera className="w-4 h-4 mr-2" /> Start Camera
                            </Button>
                          )}
                          <canvas ref={canvasRef} className="hidden" />
                        </div>
                      </div>

                      {/* GPS Location */}
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                          <MapPin className="w-4 h-4" /> GPS Location
                          {formData.work_location === 'in_office' && (
                            <span className="text-xs text-amber-600 font-normal">(Geo-fencing: 500m radius)</span>
                          )}
                        </Label>
                        <div className="border border-zinc-200 rounded-md p-3 bg-zinc-50">
                          {location ? (
                            <div className="space-y-2">
                              <div className={`flex items-center gap-2 p-2 rounded ${locationVerified ? 'bg-emerald-100' : 'bg-amber-100'}`}>
                                {locationVerified ? (
                                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                                ) : (
                                  <AlertCircle className="w-4 h-4 text-amber-600" />
                                )}
                                <span className={`text-xs font-medium ${locationVerified ? 'text-emerald-700' : 'text-amber-700'}`}>
                                  {locationVerified ? 'Location Verified' : 'Outside Geo-fence'}
                                </span>
                              </div>
                              <p className="text-xs text-zinc-600 truncate">{location.address}</p>
                              <p className="text-[10px] text-zinc-400">
                                {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)} ({location.accuracy?.toFixed(0)}m)
                              </p>
                              <Button type="button" onClick={captureLocation} variant="outline" size="sm" className="w-full text-xs">
                                <Navigation className="w-3 h-3 mr-1" /> Recapture Location
                              </Button>
                            </div>
                          ) : (
                            <Button 
                              type="button" 
                              onClick={captureLocation} 
                              variant="outline" 
                              className="w-full"
                              disabled={locationLoading}
                              data-testid="capture-location-btn"
                            >
                              {locationLoading ? (
                                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Getting Location...</>
                              ) : (
                                <><Navigation className="w-4 h-4 mr-2" /> Capture GPS Location</>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Remarks */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Remarks</Label>
                    <Input value={formData.remarks} onChange={(e) => setFormData({ ...formData, remarks: e.target.value })}
                      className="rounded-sm border-zinc-200" placeholder="Optional notes" />
                  </div>
                  
                  <Button type="submit" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none" data-testid="submit-attendance">
                    Save Attendance
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {/* Month picker + Stats */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <CalendarDays className="w-4 h-4 text-zinc-500" />
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
            className="rounded-sm border-zinc-200 w-44" data-testid="month-picker" />
        </div>
        <Card className="border-zinc-200 shadow-none rounded-sm flex-1">
          <CardContent className="p-3 flex items-center gap-6">
            <div className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-500" /><span className="text-sm text-zinc-700">Present: <strong>{totalPresent}</strong></span></div>
            <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-red-400" /><span className="text-sm text-zinc-700">Absent: <strong>{totalAbsent}</strong></span></div>
            <div className="flex items-center gap-2"><Clock className="w-4 h-4 text-yellow-500" /><span className="text-sm text-zinc-700">Records: <strong>{records.length}</strong></span></div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-zinc-200">
        <button onClick={() => setActiveTab('summary')} data-testid="tab-att-summary"
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'summary' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>Summary</button>
        <button onClick={() => setActiveTab('records')} data-testid="tab-att-records"
          className={`px-4 py-2 text-sm font-medium ${activeTab === 'records' ? 'border-b-2 border-zinc-950 text-zinc-950' : 'text-zinc-500'}`}>Daily Records</button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : activeTab === 'summary' ? (
        summary.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <CalendarDays className="w-10 h-10 text-zinc-300 mb-3" />
              <p className="text-zinc-500">No attendance data for this month</p>
            </CardContent>
          </Card>
        ) : (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Emp ID</th>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Name</th>
                  <th className="text-left px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Department</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Present</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Absent</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Half Day</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">WFH</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Leave</th>
                  <th className="text-center px-4 py-3 text-xs uppercase tracking-wide text-zinc-500 font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {summary.map(row => (
                  <tr key={row.employee_id} className="border-t border-zinc-100 hover:bg-zinc-50" data-testid={`att-summary-${row.employee_id}`}>
                    <td className="px-4 py-3 text-zinc-600 font-mono text-xs">{row.emp_code}</td>
                    <td className="px-4 py-3 font-medium text-zinc-950">{row.name}</td>
                    <td className="px-4 py-3 text-zinc-600">{row.department || '-'}</td>
                    <td className="px-4 py-3 text-center text-emerald-700 font-medium">{row.present}</td>
                    <td className="px-4 py-3 text-center text-red-600 font-medium">{row.absent}</td>
                    <td className="px-4 py-3 text-center text-yellow-600">{row.half_day}</td>
                    <td className="px-4 py-3 text-center text-blue-600">{row.wfh}</td>
                    <td className="px-4 py-3 text-center text-purple-600">{row.on_leave}</td>
                    <td className="px-4 py-3 text-center font-medium text-zinc-950">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        records.length === 0 ? (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <p className="text-zinc-500">No daily records for this month</p>
            </CardContent>
          </Card>
        ) : (
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="text-left px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Date</th>
                  <th className="text-left px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Employee</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Status</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Location</th>
                  <th className="text-left px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Client</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-emerald-600 font-medium">Check-In</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-red-600 font-medium">Check-Out</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Hours</th>
                  <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium">Selfie</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r, idx) => (
                  <tr key={r.id || idx} className="border-t border-zinc-100 hover:bg-zinc-50">
                    <td className="px-3 py-2 text-zinc-700 text-xs">{r.date}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-zinc-900 text-xs">{r.employee_name || r.employee_id}</div>
                      <div className="text-[10px] text-zinc-400">{r.employee_id}</div>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`text-xs px-2 py-1 rounded-sm ${getStatusBadge(r.status)}`}>
                        {STATUSES.find(s => s.value === r.status)?.label || r.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {['present', 'half_day'].includes(r.status) ? (
                        <span className="flex items-center justify-center gap-1 text-xs">
                          {r.work_location === 'in_office' && <><Building2 className="w-3 h-3 text-blue-600" /><span className="text-blue-700">Office</span></>}
                          {r.work_location === 'onsite' && <><MapPin className="w-3 h-3 text-emerald-600" /><span className="text-emerald-700">On-Site</span></>}
                          {r.work_location === 'wfh' && <><Home className="w-3 h-3 text-amber-600" /><span className="text-amber-700">WFH</span></>}
                          {!r.work_location && <span className="text-zinc-400">-</span>}
                        </span>
                      ) : <span className="text-zinc-400">-</span>}
                    </td>
                    <td className="px-3 py-2">
                      {r.client_name ? (
                        <span className="text-xs text-emerald-700 font-medium">{r.client_name}</span>
                      ) : (
                        <span className="text-zinc-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {r.check_in_time ? (
                        <span className="text-xs text-emerald-700 font-medium">{r.check_in_time.split('T')[1]?.slice(0,5) || r.check_in_time}</span>
                      ) : (
                        <span className="text-zinc-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {r.check_out_time ? (
                        <span className="text-xs text-red-600 font-medium">{r.check_out_time.split('T')[1]?.slice(0,5) || r.check_out_time}</span>
                      ) : (
                        <span className="text-zinc-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {r.work_hours ? (
                        <span className="text-xs text-zinc-700 font-medium">{r.work_hours.toFixed(1)}h</span>
                      ) : (
                        <span className="text-zinc-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {r.selfie ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                          <CheckCircle className="w-3 h-3" />
                        </span>
                      ) : (
                        <span className="text-zinc-400 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      
      {/* Travel Reimbursement Modal */}
      {showTravelModal && travelData && (
        <Dialog open={showTravelModal} onOpenChange={setShowTravelModal}>
          <DialogContent className="border-zinc-200 rounded-sm max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl font-semibold text-zinc-950 flex items-center gap-2">
                <Car className="w-5 h-5 text-teal-600" /> Travel Reimbursement
              </DialogTitle>
              <DialogDescription className="text-zinc-500">
                Claim travel expense for your client visit
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Trip Summary */}
              <div className="p-4 bg-teal-50 border border-teal-200 rounded-md">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-teal-700">Distance (Round Trip)</span>
                  <span className="font-bold text-teal-900">{travelData.distance_km} km</span>
                </div>
                <div className="text-xs text-teal-600">
                  <p><strong>From:</strong> {travelData.from_location}</p>
                  <p><strong>To:</strong> {travelData.client_name || travelData.to_location}</p>
                </div>
              </div>
              
              {/* Vehicle Selection */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Select Vehicle</Label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setTravelVehicle('car')}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition ${
                      travelVehicle === 'car' ? 'border-blue-500 bg-blue-50' : 'border-zinc-200'
                    }`}
                  >
                    <Car className={`w-6 h-6 ${travelVehicle === 'car' ? 'text-blue-600' : 'text-zinc-400'}`} />
                    <div className="text-left">
                      <p className="font-medium text-zinc-900">Car</p>
                      <p className="text-xs text-zinc-500">Rs 7/km</p>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setTravelVehicle('two_wheeler')}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition ${
                      travelVehicle === 'two_wheeler' ? 'border-emerald-500 bg-emerald-50' : 'border-zinc-200'
                    }`}
                  >
                    <Bike className={`w-6 h-6 ${travelVehicle === 'two_wheeler' ? 'text-emerald-600' : 'text-zinc-400'}`} />
                    <div className="text-left">
                      <p className="font-medium text-zinc-900">Two Wheeler</p>
                      <p className="text-xs text-zinc-500">Rs 3/km</p>
                    </div>
                  </button>
                </div>
              </div>
              
              {/* Amount Preview */}
              <div className="p-4 bg-zinc-100 rounded-md">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-600">Estimated Amount</span>
                  <span className="text-2xl font-bold text-zinc-900">
                    Rs {Math.round(travelData.distance_km * (travelVehicle === 'car' ? 7 : 3))}
                  </span>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  onClick={() => { setShowTravelModal(false); setTravelData(null); }}
                  className="flex-1"
                >
                  Skip
                </Button>
                <Button 
                  onClick={handleSubmitTravelClaim}
                  disabled={submittingTravel}
                  className="flex-1 bg-teal-600 hover:bg-teal-700 text-white"
                >
                  {submittingTravel ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting...</>
                  ) : (
                    <><Send className="w-4 h-4 mr-2" /> Submit Claim</>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default Attendance;
