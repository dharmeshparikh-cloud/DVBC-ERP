import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { 
  X, Camera, MapPin, Building2, Briefcase, LogIn, LogOut, 
  CheckCircle, Loader2, Navigation, RotateCcw, AlertCircle,
  Clock, Send, User
} from 'lucide-react';
import { toast } from 'sonner';

const WORK_LOCATIONS = [
  { value: 'in_office', label: 'Office', icon: Building2, color: 'blue' },
  { value: 'onsite', label: 'Client Site', icon: MapPin, color: 'emerald' },
];

const QuickCheckInModal = ({ isOpen, onClose, user }) => {
  // Attendance status
  const [checkInStatus, setCheckInStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Check-in form states
  const [selectedWorkLocation, setSelectedWorkLocation] = useState('in_office');
  const [selfieData, setSelfieData] = useState(null);
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [stream, setStream] = useState(null);
  
  // Client selection for On-Site
  const [assignedClients, setAssignedClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [loadingClients, setLoadingClients] = useState(false);
  
  // Check if user can do onsite
  const [canDoOnsite, setCanDoOnsite] = useState(false);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchAttendanceStatus();
      fetchAssignedClients();
      captureLocation();
    }
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isOpen]);

  const fetchAttendanceStatus = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/my/check-status`);
      setCheckInStatus(res.data);
      
      // Check if user can do onsite based on department/role
      const attRes = await axios.get(`${API}/my/attendance?month=${new Date().toISOString().slice(0, 7)}`);
      const dept = attRes.data?.employee?.department?.toLowerCase() || '';
      const role = user?.role?.toLowerCase() || '';
      setCanDoOnsite(
        dept.includes('consulting') || 
        dept.includes('delivery') || 
        dept.includes('sales') ||
        ['admin', 'executive', 'account_manager', 'manager'].includes(role)
      );
    } catch (error) {
      console.error('Failed to fetch status');
    } finally {
      setLoading(false);
    }
  };

  const fetchAssignedClients = async () => {
    setLoadingClients(true);
    try {
      const res = await axios.get(`${API}/my/assigned-clients`);
      setAssignedClients(res.data.clients || []);
    } catch (e) {
      setAssignedClients([]);
    } finally {
      setLoadingClients(false);
    }
  };

  const captureLocation = () => {
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const coords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        };
        try {
          const res = await axios.get(`${API}/search-location?query=${coords.latitude},${coords.longitude}`);
          if (res.data.results?.length > 0) {
            coords.address = res.data.results[0].address;
          }
        } catch (e) {
          coords.address = `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`;
        }
        setLocation(coords);
        setLocationLoading(false);
      },
      (error) => {
        toast.error('Unable to get location. Please enable GPS.');
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const startCamera = useCallback(async () => {
    try {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } 
      });
      setStream(mediaStream);
      setCameraActive(true);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          videoRef.current.play().catch(e => console.log('Video play error:', e));
        }
      }, 100);
    } catch (err) {
      toast.error('Unable to access camera. Please grant permission.');
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
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0) {
      toast.error('Camera not ready');
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    setSelfieData(canvas.toDataURL('image/jpeg', 0.7));
    stopCamera();
    toast.success('Selfie captured!');
  }, [stopCamera]);

  const handleCheckIn = async () => {
    if (!selfieData) {
      toast.error('Please capture your selfie first');
      return;
    }
    if (!location) {
      toast.error('Please wait for location to be captured');
      return;
    }
    if (selectedWorkLocation === 'onsite' && !selectedClient) {
      toast.error('Please select a client for On-Site check-in');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        work_location: selectedWorkLocation,
        remarks: 'Quick check-in from dashboard',
        selfie: selfieData,
        geo_location: {
          latitude: location.latitude,
          longitude: location.longitude,
          accuracy: location.accuracy,
          address: location.address
        }
      };

      if (selectedWorkLocation === 'onsite' && selectedClient) {
        payload.client_id = selectedClient.id;
        payload.client_name = selectedClient.client_name;
        payload.project_id = selectedClient.project_id || '';
        payload.project_name = selectedClient.project_name || '';
      }

      await axios.post(`${API}/my/check-in`, payload);
      toast.success('Check-in successful!');
      fetchAttendanceStatus();
      resetForm();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCheckOut = async () => {
    setSubmitting(true);
    try {
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 });
      });
      
      const geo_location = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      };

      const response = await axios.post(`${API}/my/check-out`, { geo_location });
      toast.success(`Check-out successful! Work hours: ${response.data.work_hours?.toFixed(1) || '-'} hrs`);
      
      // If travel reimbursement available, notify
      if (response.data.travel_reimbursement) {
        toast.info(`Travel claim available: ${response.data.travel_reimbursement.distance_km} km. Go to Attendance page to claim.`);
      }
      
      fetchAttendanceStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-out failed');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setSelfieData(null);
    setSelectedWorkLocation('in_office');
    setSelectedClient(null);
    stopCamera();
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  const hasCheckedIn = checkInStatus?.has_checked_in;
  const hasCheckedOut = checkInStatus?.has_checked_out;
  const currentTime = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="quick-checkin-modal">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-black text-white px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Quick Attendance</h2>
              <p className="text-white/60 text-sm">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short' })}</p>
            </div>
          </div>
          <button onClick={handleClose} className="p-2 hover:bg-white/10 rounded-lg transition">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-black" />
            </div>
          ) : hasCheckedIn && hasCheckedOut ? (
            /* Already completed today */
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-10 h-10 text-emerald-600" />
              </div>
              <h3 className="text-2xl font-bold text-black mb-2">All Done!</h3>
              <p className="text-black/60">You've completed your attendance for today.</p>
              <div className="mt-6 p-4 bg-black/5 rounded-xl">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-black/50">Check-in</p>
                    <p className="font-semibold text-emerald-600">{checkInStatus?.check_in_time?.split('T')[1]?.slice(0,5) || '-'}</p>
                  </div>
                  <div>
                    <p className="text-black/50">Check-out</p>
                    <p className="font-semibold text-red-600">{checkInStatus?.check_out_time?.split('T')[1]?.slice(0,5) || '-'}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : hasCheckedIn ? (
            /* Ready to check out */
            <div className="text-center py-8">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <LogIn className="w-10 h-10 text-emerald-600" />
              </div>
              <h3 className="text-2xl font-bold text-black mb-2">You're Checked In</h3>
              <p className="text-black/60 mb-2">Since {checkInStatus?.check_in_time?.split('T')[1]?.slice(0,5) || '-'}</p>
              {checkInStatus?.work_location && (
                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                  checkInStatus.work_location === 'onsite' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'
                }`}>
                  {checkInStatus.work_location === 'onsite' ? <MapPin className="w-4 h-4" /> : <Building2 className="w-4 h-4" />}
                  {checkInStatus.work_location === 'onsite' ? 'Client Site' : 'Office'}
                </span>
              )}
              
              <div className="mt-8">
                <p className="text-black/50 text-sm mb-4">Current time: {currentTime}</p>
                <Button
                  onClick={handleCheckOut}
                  disabled={submitting}
                  className="w-full max-w-xs mx-auto bg-red-600 hover:bg-red-700 text-white h-14 text-lg rounded-xl"
                  data-testid="quick-checkout-btn"
                >
                  {submitting ? (
                    <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
                  ) : (
                    <><LogOut className="w-5 h-5 mr-2" /> Check Out Now</>
                  )}
                </Button>
              </div>
            </div>
          ) : (
            /* Check-in form */
            <div className="space-y-6">
              {/* User Info */}
              <div className="flex items-center gap-4 p-4 bg-black/5 rounded-xl">
                <div className="w-12 h-12 bg-black text-white rounded-full flex items-center justify-center font-bold text-lg">
                  {user?.full_name?.charAt(0) || 'U'}
                </div>
                <div>
                  <p className="font-semibold text-black">{user?.full_name}</p>
                  <p className="text-sm text-black/50">{user?.email}</p>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-2xl font-bold text-black">{currentTime}</p>
                  <p className="text-xs text-black/50">Current time</p>
                </div>
              </div>

              {/* Work Location */}
              <div>
                <label className="block text-sm font-medium text-black mb-3">Where are you working today?</label>
                <div className="grid grid-cols-2 gap-3">
                  {WORK_LOCATIONS.map((loc) => {
                    const Icon = loc.icon;
                    const isSelected = selectedWorkLocation === loc.value;
                    const isDisabled = loc.value === 'onsite' && !canDoOnsite;
                    return (
                      <button
                        key={loc.value}
                        onClick={() => {
                          if (!isDisabled) {
                            setSelectedWorkLocation(loc.value);
                            setSelectedClient(null);
                          }
                        }}
                        disabled={isDisabled}
                        className={`flex items-center gap-3 p-4 rounded-xl border-2 transition ${
                          isDisabled ? 'opacity-50 cursor-not-allowed border-black/10' :
                          isSelected ? `border-${loc.color}-500 bg-${loc.color}-50` : 'border-black/10 hover:border-black/30'
                        }`}
                        data-testid={`quick-loc-${loc.value}`}
                      >
                        <Icon className={`w-6 h-6 ${isSelected ? `text-${loc.color}-600` : 'text-black/40'}`} />
                        <span className={`font-medium ${isSelected ? `text-${loc.color}-700` : 'text-black/70'}`}>{loc.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Client Selection for On-Site */}
              {selectedWorkLocation === 'onsite' && (
                <div>
                  <label className="block text-sm font-medium text-black mb-3 flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-emerald-600" /> Select Client
                  </label>
                  {loadingClients ? (
                    <div className="flex items-center gap-2 p-4 bg-black/5 rounded-xl">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="text-black/50">Loading clients...</span>
                    </div>
                  ) : assignedClients.length > 0 ? (
                    <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto">
                      {assignedClients.map((client) => (
                        <button
                          key={client.id}
                          onClick={() => setSelectedClient(client)}
                          className={`flex items-center gap-3 p-3 rounded-xl border-2 transition text-left ${
                            selectedClient?.id === client.id 
                              ? 'border-emerald-500 bg-emerald-50' 
                              : 'border-black/10 hover:border-black/30'
                          }`}
                        >
                          <Briefcase className={`w-5 h-5 ${selectedClient?.id === client.id ? 'text-emerald-600' : 'text-black/40'}`} />
                          <div>
                            <p className={`font-medium ${selectedClient?.id === client.id ? 'text-emerald-700' : 'text-black/70'}`}>
                              {client.client_name}
                            </p>
                            {client.project_name && (
                              <p className="text-xs text-black/50">{client.project_name}</p>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-center">
                      <p className="text-amber-700 text-sm">No assigned clients. Contact your manager.</p>
                    </div>
                  )}
                </div>
              )}

              {/* Selfie Capture */}
              <div>
                <label className="block text-sm font-medium text-black mb-3 flex items-center gap-2">
                  <Camera className="w-4 h-4" /> Selfie Verification
                </label>
                <div className="border-2 border-dashed border-black/20 rounded-xl p-4 bg-black/5">
                  {selfieData ? (
                    <div className="relative">
                      <img src={selfieData} alt="Selfie" className="w-full h-48 object-cover rounded-lg" />
                      <button
                        onClick={() => { setSelfieData(null); startCamera(); }}
                        className="absolute top-2 right-2 px-3 py-1 bg-black/70 text-white text-xs rounded-lg flex items-center gap-1"
                      >
                        <RotateCcw className="w-3 h-3" /> Retake
                      </button>
                      <div className="absolute bottom-2 left-2 px-2 py-1 bg-emerald-500 text-white text-xs rounded flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Captured
                      </div>
                    </div>
                  ) : cameraActive ? (
                    <div className="space-y-3">
                      <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                      </div>
                      <div className="flex gap-2">
                        <Button onClick={captureSelfie} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white">
                          <Camera className="w-4 h-4 mr-2" /> Capture
                        </Button>
                        <Button onClick={stopCamera} variant="outline" className="flex-1">
                          <X className="w-4 h-4 mr-2" /> Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button onClick={startCamera} variant="outline" className="w-full h-32 border-2 border-dashed" data-testid="quick-start-camera">
                      <div className="text-center">
                        <Camera className="w-8 h-8 mx-auto mb-2 text-black/40" />
                        <span className="text-black/60">Tap to capture selfie</span>
                      </div>
                    </Button>
                  )}
                  <canvas ref={canvasRef} className="hidden" />
                </div>
              </div>

              {/* GPS Location */}
              <div>
                <label className="block text-sm font-medium text-black mb-3 flex items-center gap-2">
                  <MapPin className="w-4 h-4" /> GPS Location
                </label>
                <div className="border border-black/20 rounded-xl p-4 bg-black/5">
                  {location ? (
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <CheckCircle className="w-5 h-5 text-emerald-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-emerald-700">Location Captured</p>
                        <p className="text-xs text-black/50 truncate">{location.address}</p>
                      </div>
                      <button onClick={captureLocation} className="text-xs text-black/50 hover:text-black flex items-center gap-1">
                        <Navigation className="w-3 h-3" /> Refresh
                      </button>
                    </div>
                  ) : locationLoading ? (
                    <div className="flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin text-black/50" />
                      <span className="text-black/50">Getting your location...</span>
                    </div>
                  ) : (
                    <Button onClick={captureLocation} variant="outline" className="w-full">
                      <Navigation className="w-4 h-4 mr-2" /> Capture GPS Location
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer - Check-in Button */}
        {!loading && !hasCheckedIn && (
          <div className="border-t border-black/10 p-6 bg-white">
            <Button
              onClick={handleCheckIn}
              disabled={submitting || !selfieData || !location || (selectedWorkLocation === 'onsite' && !selectedClient)}
              className="w-full bg-black hover:bg-black/90 text-white h-14 text-lg rounded-xl disabled:opacity-50"
              data-testid="quick-checkin-submit"
            >
              {submitting ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
              ) : (
                <><Send className="w-5 h-5 mr-2" /> Check In Now</>
              )}
            </Button>
            {(!selfieData || !location || (selectedWorkLocation === 'onsite' && !selectedClient)) && (
              <p className="text-center text-xs text-black/50 mt-2">
                {!selfieData && 'Capture selfie'} {!selfieData && !location && ' • '} {!location && 'Get location'}
                {selectedWorkLocation === 'onsite' && !selectedClient && ' • Select client'}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default QuickCheckInModal;
