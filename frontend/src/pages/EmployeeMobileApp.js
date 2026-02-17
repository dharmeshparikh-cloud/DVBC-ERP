import React, { useState, useEffect, useContext, useRef } from 'react';
import { AuthContext, API } from '../App';
import axios from 'axios';
import { 
  CheckCircle, Clock, MapPin, LogIn, LogOut, Calendar, Receipt, 
  Home, Building2, Navigation, Loader2, AlertCircle, ChevronRight,
  Plus, Camera, FileText, TrendingUp, User, Bell, Settings,
  Coffee, Sun, Moon, Briefcase, IndianRupee, CalendarDays,
  CheckCircle2, XCircle, Timer, Wallet, X, RotateCcw, Send,
  Car, Bike, Search
} from 'lucide-react';
import { toast } from 'sonner';

const EmployeeMobileApp = () => {
  const { user, logout } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('home');
  const [loading, setLoading] = useState(false);
  const [checkInStatus, setCheckInStatus] = useState(null);
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [attendanceData, setAttendanceData] = useState(null);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [showCheckInModal, setShowCheckInModal] = useState(false);
  const [showCheckOutModal, setShowCheckOutModal] = useState(false);
  const [selectedWorkLocation, setSelectedWorkLocation] = useState('in_office');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isConsultingEmployee, setIsConsultingEmployee] = useState(false);
  
  // Selfie capture states
  const [selfieData, setSelfieData] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [stream, setStream] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  
  // Justification for unknown location
  const [showJustification, setShowJustification] = useState(false);
  const [justification, setJustification] = useState('');
  const [locationValidation, setLocationValidation] = useState(null);

  // Expense form states
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [expenseForm, setExpenseForm] = useState({
    is_office_expense: true,
    client_id: '',
    client_name: '',
    project_id: '',
    project_name: '',
    notes: '',
    line_items: []
  });
  const [lineItemForm, setLineItemForm] = useState({
    category: 'local_conveyance',
    description: '',
    amount: '',
    date: new Date().toISOString().split('T')[0]
  });
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);

  // Leave form states
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  const [leaveForm, setLeaveForm] = useState({
    leave_type: 'casual',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    reason: ''
  });

  // Travel claim states (for Sales team)
  const [showTravelModal, setShowTravelModal] = useState(false);
  const [travelClaims, setTravelClaims] = useState([]);
  const [travelForm, setTravelForm] = useState({
    start_location: null,
    end_location: null,
    vehicle_type: 'car',
    is_round_trip: true,
    notes: ''
  });
  const [locationSearchQuery, setLocationSearchQuery] = useState('');
  const [locationSearchResults, setLocationSearchResults] = useState([]);
  const [searchingLocations, setSearchingLocations] = useState(false);
  const [selectingFor, setSelectingFor] = useState(null); // 'start' or 'end'

  // Check if user is Sales team (can enter manual travel claims)
  const isSalesTeam = ['admin', 'executive', 'account_manager', 'manager'].includes(user?.role);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [stream]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [attRes, leaveRes, expRes, clientsRes, projectsRes] = await Promise.all([
        axios.get(`${API}/my/attendance?month=${new Date().toISOString().slice(0, 7)}`).catch(() => ({ data: null })),
        axios.get(`${API}/my/leave-balance`).catch(() => ({ data: null })),
        axios.get(`${API}/my/expenses`).catch(() => ({ data: null })),
        axios.get(`${API}/clients`).catch(() => ({ data: [] })),
        axios.get(`${API}/projects`).catch(() => ({ data: [] }))
      ]);
      
      setAttendanceData(attRes.data);
      setLeaveBalance(leaveRes.data);
      setExpenses(expRes.data?.expenses || []);
      setClients(clientsRes.data || []);
      setProjects(projectsRes.data || []);
      
      // Check if consulting employee (can use client sites)
      const dept = attRes.data?.employee?.department?.toLowerCase() || '';
      setIsConsultingEmployee(dept.includes('consulting') || dept.includes('delivery'));
      
      const today = new Date().toISOString().split('T')[0];
      const todayRecord = attRes.data?.records?.find(r => r.date === today);
      setCheckInStatus(todayRecord);
    } catch (error) {
      console.error('Failed to fetch data');
    } finally {
      setLoading(false);
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
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${coords.latitude}&lon=${coords.longitude}`
          );
          const data = await response.json();
          coords.address = data.display_name;
        } catch (e) {}
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

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: 640, height: 480 } 
      });
      setStream(mediaStream);
      setShowCamera(true);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      }, 100);
    } catch (error) {
      toast.error('Unable to access camera. Please grant permission.');
    }
  };

  const captureSelfie = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
      setSelfieData(dataUrl);
      stopCamera();
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setShowCamera(false);
  };

  const retakeSelfie = () => {
    setSelfieData(null);
    startCamera();
  };

  const handleCheckIn = async () => {
    if (!selfieData) {
      toast.error('Please capture your selfie first');
      return;
    }
    if (!location) {
      toast.error('Please wait for location to be captured');
      return;
    }
    
    setLoading(true);
    try {
      const payload = {
        work_location: selectedWorkLocation,
        remarks: 'Mobile app check-in with selfie',
        selfie: selfieData,
        geo_location: {
          latitude: location.latitude,
          longitude: location.longitude,
          accuracy: location.accuracy,
          address: location.address
        }
      };
      
      if (justification) {
        payload.justification = justification;
      }
      
      const response = await axios.post(`${API}/my/check-in`, payload);
      
      if (response.data.approval_status === 'approved') {
        toast.success(`Check-in successful! Location: ${response.data.matched_location || 'Verified'}`);
      } else {
        toast.info('Check-in submitted for HR approval');
      }
      
      setShowCheckInModal(false);
      setSelfieData(null);
      setJustification('');
      setShowJustification(false);
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail || 'Check-in failed';
      if (detail.includes('not within 500m') || detail.includes('justification')) {
        setShowJustification(true);
        setLocationValidation({ is_valid: false, reason: detail });
        toast.error('Location not verified. Please provide justification.');
      } else {
        toast.error(detail);
      }
    } finally {
      setLoading(false);
    }
  };

  const openCheckIn = () => {
    setShowCheckInModal(true);
    setLocation(null);
    setSelfieData(null);
    setJustification('');
    setShowJustification(false);
    setSelectedWorkLocation('in_office');
    captureLocation();
  };

  // Travel reimbursement state
  const [showTravelReimbursementModal, setShowTravelReimbursementModal] = useState(false);
  const [lastTravelReimbursement, setLastTravelReimbursement] = useState(null);
  
  const handleCheckOut = async () => {
    setLoading(true);
    try {
      // Capture location for check-out
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 });
      });
      
      const geo_location = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      };
      
      const response = await axios.post(`${API}/my/check-out`, { geo_location });
      
      // Check if travel reimbursement was calculated
      if (response.data.travel_reimbursement) {
        setLastTravelReimbursement(response.data.travel_reimbursement);
        setShowTravelReimbursementModal(true);
        toast.success(`Check-out successful! Work hours: ${response.data.work_hours?.toFixed(1) || '-'} hrs`);
      } else {
        toast.success(`Check-out successful! Work hours: ${response.data.work_hours?.toFixed(1) || '-'} hrs`);
      }
      
      setShowCheckOutModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-out failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle Expense Submission
  const handleSubmitExpense = async () => {
    if (expenseForm.line_items.length === 0) {
      toast.error('Please add at least one expense item');
      return;
    }
    setLoading(true);
    try {
      // Create expense first
      const expenseRes = await axios.post(`${API}/expenses`, {
        client_id: expenseForm.client_id || null,
        client_name: expenseForm.client_name || '',
        project_id: expenseForm.project_id || null,
        project_name: expenseForm.project_name || '',
        is_office_expense: expenseForm.is_office_expense,
        notes: expenseForm.notes,
        line_items: expenseForm.line_items.map(item => ({
          category: item.category,
          description: item.description,
          amount: item.amount,
          date: item.date
        }))
      });

      const expenseId = expenseRes.data.expense_id;

      // Upload receipts for each line item that has one
      for (let i = 0; i < expenseForm.line_items.length; i++) {
        const item = expenseForm.line_items[i];
        if (item.receipt) {
          try {
            await axios.post(`${API}/expenses/${expenseId}/upload-receipt`, {
              receipt: item.receipt,
              name: `Receipt for ${item.description}`,
              line_item_index: i
            });
          } catch (receiptError) {
            console.error('Failed to upload receipt for item', i);
          }
        }
      }

      toast.success('Expense created! Submit it for approval.');
      setShowExpenseModal(false);
      resetExpenseForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    } finally {
      setLoading(false);
    }
  };

  const addLineItem = () => {
    if (!lineItemForm.description || !lineItemForm.amount) {
      toast.error('Please fill description and amount');
      return;
    }
    setExpenseForm({
      ...expenseForm,
      line_items: [...expenseForm.line_items, {
        ...lineItemForm,
        amount: parseFloat(lineItemForm.amount),
        receipt: lineItemForm.receipt || null
      }]
    });
    setLineItemForm({
      category: 'local_conveyance',
      description: '',
      amount: '',
      date: new Date().toISOString().split('T')[0],
      receipt: null
    });
  };

  const removeLineItem = (index) => {
    setExpenseForm({
      ...expenseForm,
      line_items: expenseForm.line_items.filter((_, i) => i !== index)
    });
  };

  const resetExpenseForm = () => {
    setExpenseForm({
      is_office_expense: true,
      client_id: '',
      client_name: '',
      project_id: '',
      project_name: '',
      notes: '',
      line_items: []
    });
    setLineItemForm({
      category: 'local_conveyance',
      description: '',
      amount: '',
      date: new Date().toISOString().split('T')[0],
      receipt: null
    });
  };

  const calculateExpenseTotal = () => {
    return expenseForm.line_items.reduce((sum, item) => sum + item.amount, 0);
  };

  // Handle Leave Application
  const handleSubmitLeave = async () => {
    if (!leaveForm.reason) {
      toast.error('Please provide a reason for leave');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/leave-requests`, {
        leave_type: leaveForm.leave_type + '_leave',
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        reason: leaveForm.reason
      });
      toast.success('Leave application submitted!');
      setShowLeaveModal(false);
      setLeaveForm({
        leave_type: 'casual',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        reason: ''
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply for leave');
    } finally {
      setLoading(false);
    }
  };

  // Handle location search (OpenStreetMap/Nominatim)
  const searchLocations = async (query) => {
    if (!query || query.length < 3) {
      setLocationSearchResults([]);
      return;
    }
    setSearchingLocations(true);
    try {
      const response = await axios.get(`${API}/travel/location-search?query=${encodeURIComponent(query)}`);
      setLocationSearchResults(response.data.results || []);
    } catch (error) {
      console.error('Location search failed:', error);
      setLocationSearchResults([]);
    } finally {
      setSearchingLocations(false);
    }
  };

  // Debounced location search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (locationSearchQuery.length >= 3) {
        searchLocations(locationSearchQuery);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [locationSearchQuery]);

  // Select location from search results
  const selectLocation = (loc) => {
    const locationData = {
      name: loc.name,
      address: loc.address,
      latitude: loc.latitude,
      longitude: loc.longitude
    };
    
    if (selectingFor === 'start') {
      setTravelForm({ ...travelForm, start_location: locationData });
    } else if (selectingFor === 'end') {
      setTravelForm({ ...travelForm, end_location: locationData });
    }
    
    setLocationSearchQuery('');
    setLocationSearchResults([]);
    setSelectingFor(null);
  };

  // Calculate travel distance and submit claim
  const handleSubmitTravelClaim = async () => {
    if (!travelForm.start_location || !travelForm.end_location) {
      toast.error('Please select both start and end locations');
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.post(`${API}/travel/reimbursement`, {
        start_location: travelForm.start_location,
        end_location: travelForm.end_location,
        vehicle_type: travelForm.vehicle_type,
        is_round_trip: travelForm.is_round_trip,
        travel_date: new Date().toISOString().split('T')[0],
        travel_type: 'manual',
        notes: travelForm.notes
      });
      
      toast.success(`Travel claim submitted! Distance: ${response.data.distance_km} km, Amount: ₹${response.data.final_amount}`);
      setShowTravelModal(false);
      setTravelForm({
        start_location: null,
        end_location: null,
        vehicle_type: 'car',
        is_round_trip: true,
        notes: ''
      });
      fetchTravelClaims();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit travel claim');
    } finally {
      setLoading(false);
    }
  };

  // Fetch travel claims
  const fetchTravelClaims = async () => {
    try {
      const response = await axios.get(`${API}/my/travel-reimbursements?month=${new Date().toISOString().slice(0, 7)}`);
      setTravelClaims(response.data.records || []);
    } catch (error) {
      console.error('Failed to fetch travel claims');
    }
  };

  // Use current GPS as start location
  const useCurrentLocationAsStart = () => {
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const coords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        };
        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${coords.latitude}&lon=${coords.longitude}`
          );
          const data = await response.json();
          coords.name = data.display_name?.split(',')[0] || 'Current Location';
          coords.address = data.display_name || 'Current Location';
        } catch (e) {
          coords.name = 'Current Location';
          coords.address = 'Current Location';
        }
        setTravelForm({ ...travelForm, start_location: coords });
        setLocationLoading(false);
      },
      (error) => {
        toast.error('Unable to get location');
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const greeting = () => {
    const hour = currentTime.getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  };

  // Home Tab
  const HomeTab = () => (
    <div className="space-y-4 pb-24">
      {/* Header Card with Time */}
      <div className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 rounded-3xl p-6 text-white shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-blue-200 text-sm">{greeting()}</p>
            <h1 className="text-2xl font-bold">{user?.full_name?.split(' ')[0] || 'Employee'}</h1>
          </div>
          <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
            <User className="w-6 h-6" />
          </div>
        </div>
        
        <div className="text-center py-4">
          <p className="text-4xl font-bold tracking-wider">{formatTime(currentTime)}</p>
          <p className="text-blue-200 text-sm mt-1">{formatDate(currentTime)}</p>
        </div>

        {/* Check-in Status */}
        <div className="mt-4 p-3 rounded-2xl bg-white/10 backdrop-blur">
          {checkInStatus ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    checkInStatus.check_out_time ? 'bg-zinc-500' :
                    checkInStatus.approval_status === 'approved' ? 'bg-emerald-500' :
                    checkInStatus.approval_status === 'pending_approval' ? 'bg-amber-500' : 'bg-red-500'
                  }`}>
                    {checkInStatus.check_out_time ? <CheckCircle className="w-5 h-5" /> :
                     checkInStatus.approval_status === 'approved' ? <CheckCircle className="w-5 h-5" /> :
                     checkInStatus.approval_status === 'pending_approval' ? <Clock className="w-5 h-5" /> :
                     <XCircle className="w-5 h-5" />}
                  </div>
                  <div>
                    <p className="font-medium">
                      {checkInStatus.check_out_time ? 'Day Complete' :
                       checkInStatus.approval_status === 'approved' ? 'Checked In' :
                       checkInStatus.approval_status === 'pending_approval' ? 'Pending Approval' : 'Rejected'}
                    </p>
                    <p className="text-xs text-blue-200">
                      {checkInStatus.work_location === 'in_office' ? 'Office' : 'On-Site'}
                      {checkInStatus.work_hours && ` • ${checkInStatus.work_hours.toFixed(1)} hrs`}
                    </p>
                  </div>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full ${
                  checkInStatus.check_out_time ? 'bg-zinc-500/30' :
                  checkInStatus.approval_status === 'approved' ? 'bg-emerald-500/30' :
                  checkInStatus.approval_status === 'pending_approval' ? 'bg-amber-500/30' : 'bg-red-500/30'
                }`}>
                  {checkInStatus.check_out_time ? 'Complete' :
                   checkInStatus.approval_status === 'approved' ? 'Active' :
                   checkInStatus.approval_status === 'pending_approval' ? 'Pending' : 'Rejected'}
                </span>
              </div>
              {/* Check-out button - only show if checked in and approved, not checked out yet */}
              {checkInStatus.approval_status === 'approved' && !checkInStatus.check_out_time && (
                <button 
                  onClick={() => setShowCheckOutModal(true)}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-red-500/30 rounded-xl hover:bg-red-500/40 transition text-sm"
                  data-testid="mobile-checkout-btn"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="font-medium">Check Out</span>
                </button>
              )}
            </div>
          ) : (
            <button 
              onClick={openCheckIn}
              onTouchEnd={(e) => { e.preventDefault(); openCheckIn(); }}
              className="w-full flex items-center justify-center gap-2 py-4 bg-white/20 rounded-xl hover:bg-white/30 active:bg-white/40 transition cursor-pointer touch-manipulation"
              data-testid="mobile-checkin-btn"
              style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
            >
              <Camera className="w-5 h-5" />
              <span className="font-medium">Check In with Selfie</span>
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { icon: Calendar, label: 'Leave', color: 'bg-purple-100 text-purple-600', tab: 'leave' },
          { icon: Receipt, label: 'Expense', color: 'bg-amber-100 text-amber-600', tab: 'expense' },
          { icon: Clock, label: 'Attendance', color: 'bg-blue-100 text-blue-600', tab: 'attendance' },
          { icon: FileText, label: 'Payslip', color: 'bg-emerald-100 text-emerald-600', tab: 'home' },
        ].map((item, i) => (
          <button 
            key={i}
            onClick={() => setActiveTab(item.tab)}
            onTouchEnd={(e) => { e.preventDefault(); setActiveTab(item.tab); }}
            className="flex flex-col items-center gap-2 p-4 bg-white rounded-2xl shadow-sm border border-zinc-100 active:scale-95 transition touch-manipulation cursor-pointer"
            style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
            data-testid={`quick-action-${item.tab}`}
          >
            <div className={`w-12 h-12 rounded-xl ${item.color} flex items-center justify-center`}>
              <item.icon className="w-6 h-6" />
            </div>
            <span className="text-xs font-medium text-zinc-700">{item.label}</span>
          </button>
        ))}
      </div>

      {/* Today's Summary */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
        <h3 className="font-semibold text-zinc-900 mb-3">This Month</h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-emerald-50 rounded-xl">
            <p className="text-2xl font-bold text-emerald-600">{attendanceData?.summary?.present || 0}</p>
            <p className="text-xs text-zinc-500">Present</p>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-xl">
            <p className="text-2xl font-bold text-blue-600">{(attendanceData?.records || []).filter(r => r.work_location === 'onsite').length}</p>
            <p className="text-xs text-zinc-500">On-Site</p>
          </div>
          <div className="text-center p-3 bg-purple-50 rounded-xl">
            <p className="text-2xl font-bold text-purple-600">{attendanceData?.summary?.on_leave || 0}</p>
            <p className="text-xs text-zinc-500">Leave</p>
          </div>
        </div>
      </div>

      {/* Leave Balance */}
      {leaveBalance && (
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
          <h3 className="font-semibold text-zinc-900 mb-3">Leave Balance</h3>
          <div className="space-y-3">
            {[
              { type: 'Casual', data: leaveBalance.casual, color: 'bg-blue-500' },
              { type: 'Sick', data: leaveBalance.sick, color: 'bg-red-500' },
              { type: 'Earned', data: leaveBalance.earned, color: 'bg-emerald-500' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-2 h-8 rounded-full ${item.color}`} />
                <div className="flex-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-600">{item.type}</span>
                    <span className="font-medium">{item.data?.available || 0} / {item.data?.total || 0}</span>
                  </div>
                  <div className="h-1.5 bg-zinc-100 rounded-full mt-1 overflow-hidden">
                    <div 
                      className={`h-full ${item.color} rounded-full`}
                      style={{ width: `${((item.data?.available || 0) / (item.data?.total || 1)) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-zinc-900">Recent Activity</h3>
          <ChevronRight className="w-5 h-5 text-zinc-400" />
        </div>
        <div className="space-y-3">
          {(attendanceData?.records || []).slice(0, 3).map((record, i) => (
            <div key={i} className="flex items-center gap-3 p-2 bg-zinc-50 rounded-xl">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                record.approval_status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                record.approval_status === 'pending_approval' ? 'bg-amber-100 text-amber-600' :
                record.approval_status === 'rejected' ? 'bg-red-100 text-red-600' :
                'bg-blue-100 text-blue-600'
              }`}>
                {record.approval_status === 'approved' ? <CheckCircle2 className="w-5 h-5" /> :
                 record.approval_status === 'pending_approval' ? <Clock className="w-5 h-5" /> :
                 record.approval_status === 'rejected' ? <XCircle className="w-5 h-5" /> :
                 <CheckCircle2 className="w-5 h-5" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-zinc-900">
                  {record.work_location === 'in_office' ? 'Office' : 'On-Site'}
                  {record.approval_status === 'pending_approval' && ' (Pending)'}
                </p>
                <p className="text-xs text-zinc-500">{record.date}</p>
              </div>
              {record.location_validation?.matched_location && (
                <span className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 rounded-full">
                  {record.location_validation.matched_location.split(' ')[0]}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // Attendance Tab
  const AttendanceTab = () => (
    <div className="space-y-4 pb-24">
      {/* Check-in Card */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-3xl p-6 text-white shadow-xl">
        <div className="text-center">
          <p className="text-indigo-200 text-sm mb-2">{formatDate(currentTime)}</p>
          <p className="text-5xl font-bold tracking-wider mb-4">{formatTime(currentTime)}</p>
          
          {checkInStatus ? (
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur">
              <div className={`flex items-center justify-center gap-2 mb-2 ${
                checkInStatus.approval_status === 'approved' ? 'text-emerald-300' :
                checkInStatus.approval_status === 'pending_approval' ? 'text-amber-300' : 'text-red-300'
              }`}>
                {checkInStatus.approval_status === 'approved' ? <CheckCircle className="w-5 h-5" /> :
                 checkInStatus.approval_status === 'pending_approval' ? <Clock className="w-5 h-5" /> :
                 <XCircle className="w-5 h-5" />}
                <span className="font-medium">
                  {checkInStatus.approval_status === 'approved' ? "You're Checked In" :
                   checkInStatus.approval_status === 'pending_approval' ? "Pending HR Approval" : "Check-in Rejected"}
                </span>
              </div>
              <p className="text-sm text-indigo-200">
                {checkInStatus.check_in_time ? 
                  `Since ${new Date(checkInStatus.check_in_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}` :
                  'Today'}
              </p>
              {checkInStatus.geo_location?.address && (
                <p className="text-xs text-indigo-300 mt-2 flex items-center justify-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {checkInStatus.geo_location.address.split(',').slice(0, 2).join(',')}
                </p>
              )}
              {checkInStatus.location_validation?.matched_location && (
                <p className="text-xs text-emerald-300 mt-1">
                  Verified: {checkInStatus.location_validation.matched_location}
                </p>
              )}
            </div>
          ) : (
            <button 
              onClick={openCheckIn}
              className="w-full py-4 bg-white text-indigo-700 rounded-2xl font-semibold text-lg shadow-lg hover:bg-indigo-50 transition flex items-center justify-center gap-2"
            >
              <Camera className="w-6 h-6" />
              Check In with Selfie
            </button>
          )}
        </div>
      </div>

      {/* Monthly Stats */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Office', value: (attendanceData?.records || []).filter(r => r.work_location === 'in_office' && r.approval_status === 'approved').length, icon: Building2, color: 'emerald' },
          { label: 'On-Site', value: (attendanceData?.records || []).filter(r => r.work_location === 'onsite' && r.approval_status === 'approved').length, icon: MapPin, color: 'blue' },
          { label: 'Pending', value: (attendanceData?.records || []).filter(r => r.approval_status === 'pending_approval').length, icon: Clock, color: 'amber' },
          { label: 'Leave', value: attendanceData?.summary?.on_leave || 0, icon: Calendar, color: 'purple' },
        ].map((item, i) => (
          <div key={i} className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
            <div className={`w-10 h-10 rounded-xl bg-${item.color}-100 text-${item.color}-600 flex items-center justify-center mb-2`}>
              <item.icon className="w-5 h-5" />
            </div>
            <p className="text-2xl font-bold text-zinc-900">{item.value}</p>
            <p className="text-xs text-zinc-500">{item.label}</p>
          </div>
        ))}
      </div>

      {/* Attendance History */}
      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Attendance History</h3>
        </div>
        <div className="divide-y divide-zinc-100">
          {(attendanceData?.records || []).slice(0, 10).map((record, i) => (
            <div key={i} className="flex items-center gap-3 p-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                record.approval_status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                record.approval_status === 'pending_approval' ? 'bg-amber-100 text-amber-600' :
                record.approval_status === 'rejected' ? 'bg-red-100 text-red-600' :
                'bg-blue-100 text-blue-600'
              }`}>
                {record.approval_status === 'approved' && <CheckCircle2 className="w-5 h-5" />}
                {record.approval_status === 'pending_approval' && <Clock className="w-5 h-5" />}
                {record.approval_status === 'rejected' && <XCircle className="w-5 h-5" />}
                {!record.approval_status && <CheckCircle2 className="w-5 h-5" />}
              </div>
              <div className="flex-1">
                <p className="font-medium text-zinc-900">{record.date}</p>
                <p className="text-xs text-zinc-500">
                  {record.work_location === 'in_office' ? 'Office' : 'On-Site'}
                  {record.approval_status === 'pending_approval' && ' - Pending'}
                  {record.approval_status === 'rejected' && ' - Rejected'}
                </p>
              </div>
              {record.selfie && (
                <div className="w-8 h-8 rounded-full overflow-hidden border-2 border-zinc-200">
                  <img src={record.selfie} alt="selfie" className="w-full h-full object-cover" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // Leave Tab
  const LeaveTab = () => (
    <div className="space-y-4 pb-24">
      <div className="grid grid-cols-3 gap-3">
        {leaveBalance && [
          { type: 'Casual', data: leaveBalance.casual, color: 'blue', icon: Coffee },
          { type: 'Sick', data: leaveBalance.sick, color: 'red', icon: AlertCircle },
          { type: 'Earned', data: leaveBalance.earned, color: 'emerald', icon: TrendingUp },
        ].map((item, i) => (
          <div key={i} className={`bg-gradient-to-br from-${item.color}-500 to-${item.color}-600 rounded-2xl p-4 text-white`}>
            <item.icon className="w-6 h-6 mb-2 opacity-80" />
            <p className="text-3xl font-bold">{item.data?.available || 0}</p>
            <p className="text-xs opacity-80">{item.type}</p>
          </div>
        ))}
      </div>

      <button 
        onClick={() => setShowLeaveModal(true)}
        onTouchEnd={(e) => { e.preventDefault(); setShowLeaveModal(true); }}
        className="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
        style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
        data-testid="apply-leave-btn"
      >
        <Plus className="w-5 h-5" />
        Apply for Leave
      </button>

      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Requests</h3>
        </div>
        <div className="p-8 text-center text-zinc-500">
          <Calendar className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
          <p>No recent leave requests</p>
        </div>
      </div>
    </div>
  );

  // Expense Tab
  const ExpenseTab = () => (
    <div className="space-y-4 pb-24">
      <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-3xl p-6 text-white shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-amber-100 text-sm">Total Claims</p>
            <p className="text-3xl font-bold">₹{expenses.reduce((sum, e) => sum + (e.total_amount || 0), 0).toLocaleString()}</p>
          </div>
          <Wallet className="w-12 h-12 opacity-50" />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4">
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{expenses.filter(e => e.status === 'pending').length}</p>
            <p className="text-xs opacity-80">Pending</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{expenses.filter(e => e.status === 'approved').length}</p>
            <p className="text-xs opacity-80">Approved</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{expenses.filter(e => e.status === 'reimbursed').length}</p>
            <p className="text-xs opacity-80">Paid</p>
          </div>
        </div>
      </div>

      <button 
        onClick={() => setShowExpenseModal(true)}
        onTouchEnd={(e) => { e.preventDefault(); setShowExpenseModal(true); }}
        className="w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
        style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
        data-testid="add-expense-btn"
      >
        <Plus className="w-5 h-5" />
        Add New Expense
      </button>

      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Expenses</h3>
        </div>
        {expenses.length > 0 ? (
          <div className="divide-y divide-zinc-100">
            {expenses.slice(0, 5).map((expense, i) => (
              <div key={i} className="flex items-center gap-3 p-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  expense.status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                  expense.status === 'pending' ? 'bg-amber-100 text-amber-600' :
                  expense.status === 'reimbursed' ? 'bg-blue-100 text-blue-600' :
                  'bg-red-100 text-red-600'
                }`}>
                  <Receipt className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-zinc-900">{expense.description || 'Expense'}</p>
                  <p className="text-xs text-zinc-500">{expense.expense_date || expense.created_at?.split('T')[0]}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-zinc-900">₹{(expense.total_amount || 0).toLocaleString()}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    expense.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                    expense.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                    expense.status === 'reimbursed' ? 'bg-blue-100 text-blue-700' :
                    'bg-red-100 text-red-700'
                  }`}>{expense.status}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <Receipt className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
            <p>No expenses yet</p>
          </div>
        )}
      </div>
    </div>
  );

  // Travel Tab (for Sales team)
  const TravelTab = () => (
    <div className="space-y-4 pb-24">
      <div className="bg-gradient-to-br from-teal-500 to-cyan-600 rounded-3xl p-6 text-white shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-teal-100 text-sm">Travel Claims</p>
            <p className="text-3xl font-bold">₹{travelClaims.reduce((sum, c) => sum + (c.final_amount || 0), 0).toLocaleString()}</p>
          </div>
          <Car className="w-12 h-12 opacity-50" />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4">
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{travelClaims.filter(c => c.status === 'pending').length}</p>
            <p className="text-xs opacity-80">Pending</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{travelClaims.filter(c => c.status === 'approved').length}</p>
            <p className="text-xs opacity-80">Approved</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{travelClaims.reduce((sum, c) => sum + (c.distance_km || 0), 0).toFixed(0)}</p>
            <p className="text-xs opacity-80">Total km</p>
          </div>
        </div>
      </div>

      <button 
        onClick={() => { setShowTravelModal(true); fetchTravelClaims(); }}
        onTouchEnd={(e) => { e.preventDefault(); setShowTravelModal(true); fetchTravelClaims(); }}
        className="w-full py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
        style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
        data-testid="add-travel-btn"
      >
        <Plus className="w-5 h-5" />
        New Travel Claim
      </button>

      {/* Travel Rates Info */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-100">
        <h3 className="font-semibold text-zinc-900 mb-3">Reimbursement Rates</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl">
            <Car className="w-6 h-6 text-blue-600" />
            <div>
              <p className="font-semibold text-zinc-900">₹7/km</p>
              <p className="text-xs text-zinc-500">Car</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl">
            <Bike className="w-6 h-6 text-emerald-600" />
            <div>
              <p className="font-semibold text-zinc-900">₹3/km</p>
              <p className="text-xs text-zinc-500">Two Wheeler</p>
            </div>
          </div>
        </div>
        <p className="text-xs text-zinc-500 mt-3">
          Cab/Public transport: Submit actual receipt for reimbursement
        </p>
      </div>

      {/* Recent Travel Claims */}
      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Travel Claims</h3>
        </div>
        {travelClaims.length > 0 ? (
          <div className="divide-y divide-zinc-100">
            {travelClaims.slice(0, 5).map((claim, i) => (
              <div key={i} className="flex items-center gap-3 p-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  claim.status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                  claim.status === 'pending' ? 'bg-amber-100 text-amber-600' :
                  'bg-red-100 text-red-600'
                }`}>
                  <Car className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-zinc-900 text-sm truncate">
                    {claim.start_location?.name || 'Start'} → {claim.end_location?.name || 'End'}
                  </p>
                  <p className="text-xs text-zinc-500">{claim.travel_date} • {claim.distance_km} km</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-zinc-900">₹{(claim.final_amount || 0).toLocaleString()}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    claim.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                    claim.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'
                  }`}>{claim.status}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <Car className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
            <p>No travel claims yet</p>
          </div>
        )}
      </div>
    </div>
  );

  // Check-in Modal with Selfie
  const CheckInModal = () => {
    const closeModal = () => {
      setShowCheckInModal(false);
      stopCamera();
      setSelfieData(null);
      setJustification('');
      setShowJustification(false);
      setLocation(null);
    };

    return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-end" onClick={closeModal}>
      <div className="w-full bg-white rounded-t-3xl max-h-[90vh] overflow-y-auto animate-slide-up" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white pt-4 pb-2 px-6 border-b border-zinc-100">
          <div className="w-12 h-1 bg-zinc-300 rounded-full mx-auto mb-4" />
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-zinc-900">Check In</h2>
              <p className="text-sm text-zinc-500">Selfie + Location required</p>
            </div>
            <button onClick={closeModal} className="p-2" data-testid="close-checkin-modal">
              <X className="w-6 h-6 text-zinc-400" />
            </button>
          </div>
        </div>
        
        <div className="p-6 space-y-5">
          {/* Step 1: Selfie Capture */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${selfieData ? 'bg-emerald-500 text-white' : 'bg-zinc-200 text-zinc-600'}`}>
                {selfieData ? '✓' : '1'}
              </div>
              <span className="text-sm font-medium text-zinc-700">Capture Selfie</span>
            </div>
            
            <div className="relative rounded-2xl overflow-hidden bg-zinc-900 aspect-[4/3]">
              {showCamera ? (
                <>
                  <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                  <canvas ref={canvasRef} className="hidden" />
                  <button 
                    onClick={captureSelfie}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 w-16 h-16 rounded-full bg-white border-4 border-zinc-300 flex items-center justify-center shadow-lg"
                  >
                    <div className="w-12 h-12 rounded-full bg-blue-600" />
                  </button>
                </>
              ) : selfieData ? (
                <>
                  <img src={selfieData} alt="Selfie" className="w-full h-full object-cover" />
                  <button 
                    onClick={retakeSelfie}
                    className="absolute bottom-4 right-4 px-4 py-2 bg-white/90 rounded-xl flex items-center gap-2 text-sm font-medium"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Retake
                  </button>
                  <div className="absolute top-4 left-4 px-3 py-1 bg-emerald-500 text-white rounded-full text-xs font-medium flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    Captured
                  </div>
                </>
              ) : (
                <button 
                  onClick={startCamera}
                  className="w-full h-full flex flex-col items-center justify-center text-white"
                >
                  <Camera className="w-12 h-12 mb-2 opacity-50" />
                  <span className="text-sm opacity-70">Tap to open camera</span>
                </button>
              )}
            </div>
          </div>

          {/* Step 2: Location */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${location ? 'bg-emerald-500 text-white' : 'bg-zinc-200 text-zinc-600'}`}>
                {location ? '✓' : '2'}
              </div>
              <span className="text-sm font-medium text-zinc-700">Verify Location</span>
            </div>
            
            <div className="p-4 rounded-2xl bg-zinc-50 border border-zinc-200">
              {locationLoading ? (
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  <span className="text-sm text-zinc-600">Getting your location...</span>
                </div>
              ) : location ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-emerald-600">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">Location Captured</span>
                  </div>
                  {location.address && (
                    <p className="text-xs text-zinc-600 leading-relaxed">{location.address}</p>
                  )}
                  <p className="text-xs text-zinc-400">
                    {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)} (±{Math.round(location.accuracy)}m)
                  </p>
                  <button onClick={captureLocation} className="text-xs text-blue-600 flex items-center gap-1 mt-2">
                    <Navigation className="w-3 h-3" />
                    Refresh location
                  </button>
                </div>
              ) : (
                <button onClick={captureLocation} className="flex items-center gap-2 text-blue-600">
                  <Navigation className="w-5 h-5" />
                  <span className="font-medium">Tap to get location</span>
                </button>
              )}
            </div>
          </div>

          {/* Step 3: Work Location */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-zinc-200 text-zinc-600 flex items-center justify-center text-xs font-bold">3</div>
              <span className="text-sm font-medium text-zinc-700">Select Work Location</span>
            </div>
            
            {!isConsultingEmployee && (
              <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 mb-3">
                <p className="text-xs text-blue-700">
                  <strong>Note:</strong> Client Site check-in is only available for Consulting/Delivery team members.
                </p>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: 'in_office', label: 'Office', icon: Building2, color: 'blue', desc: 'Company premises', disabled: false },
                { value: 'onsite', label: 'Client Site', icon: MapPin, color: 'emerald', desc: 'Client location', disabled: !isConsultingEmployee },
              ].map((loc) => (
                <button
                  key={loc.value}
                  onClick={() => !loc.disabled && setSelectedWorkLocation(loc.value)}
                  disabled={loc.disabled}
                  className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition ${
                    loc.disabled ? 'opacity-50 cursor-not-allowed border-zinc-200 bg-zinc-50' :
                    selectedWorkLocation === loc.value
                      ? `border-${loc.color}-500 bg-${loc.color}-50`
                      : 'border-zinc-200'
                  }`}
                  data-testid={`checkin-loc-${loc.value}`}
                >
                  <loc.icon className={`w-8 h-8 ${loc.disabled ? 'text-zinc-300' : selectedWorkLocation === loc.value ? `text-${loc.color}-600` : 'text-zinc-400'}`} />
                  <span className={`text-sm font-medium ${loc.disabled ? 'text-zinc-400' : selectedWorkLocation === loc.value ? `text-${loc.color}-700` : 'text-zinc-600'}`}>
                    {loc.label}
                  </span>
                  <span className="text-xs text-zinc-400">{loc.disabled ? 'Not available' : loc.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Justification (if location not verified) */}
          {showJustification && (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200">
              <div className="flex items-start gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">Location Not Verified</p>
                  <p className="text-xs text-amber-700 mt-1">
                    You're not within 500m of any approved location. Please provide justification for HR approval.
                  </p>
                </div>
              </div>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Explain why you're checking in from this location..."
                className="w-full p-3 rounded-xl border border-amber-200 bg-white text-sm resize-none"
                rows={3}
                data-testid="justification-input"
              />
            </div>
          )}

          {/* Submit Button */}
          <button 
            onClick={handleCheckIn}
            disabled={!selfieData || !location || loading || (showJustification && !justification)}
            className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg"
            data-testid="confirm-checkin-btn"
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> Processing...</>
            ) : (
              <><Send className="w-5 h-5" /> {showJustification ? 'Submit for Approval' : 'Check In'}</>
            )}
          </button>
          
          {!selfieData && !location && (
            <p className="text-xs text-center text-zinc-500">
              Complete all steps to check in
            </p>
          )}

          {/* Cancel Button */}
          <button 
            onClick={closeModal}
            className="w-full py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-medium mt-2"
            data-testid="cancel-checkin-btn"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
  };

  return (
    <div className="min-h-screen bg-zinc-100" style={{ maxWidth: '430px', margin: '0 auto' }}>
      {/* Status Bar Mock */}
      <div className="bg-zinc-900 text-white px-4 py-2 flex items-center justify-between text-xs">
        <span>{formatTime(currentTime).slice(0, 5)}</span>
        <div className="flex items-center gap-1">
          <div className="w-4 h-2 border border-white rounded-sm">
            <div className="w-3/4 h-full bg-white rounded-sm" />
          </div>
        </div>
      </div>

      {/* App Header */}
      <div className="bg-white px-4 py-3 flex items-center justify-between shadow-sm sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-zinc-900">DVBC Employee</h1>
            <p className="text-xs text-zinc-500">{user?.role?.replace('_', ' ')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="w-10 h-10 rounded-xl bg-zinc-100 flex items-center justify-center">
            <Bell className="w-5 h-5 text-zinc-600" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'home' && <HomeTab />}
        {activeTab === 'attendance' && <AttendanceTab />}
        {activeTab === 'leave' && <LeaveTab />}
        {activeTab === 'expense' && <ExpenseTab />}
        {activeTab === 'travel' && <TravelTab />}
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-zinc-200 px-2 py-2 flex justify-around z-[10000]" style={{ maxWidth: '430px', margin: '0 auto' }}>
        {[
          { id: 'home', icon: Home, label: 'Home' },
          { id: 'attendance', icon: Clock, label: 'Attendance' },
          { id: 'leave', icon: Calendar, label: 'Leave' },
          { id: 'expense', icon: Receipt, label: 'Expense' },
          ...(isSalesTeam ? [{ id: 'travel', icon: Car, label: 'Travel' }] : []),
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); if (tab.id === 'travel') fetchTravelClaims(); }}
            onTouchEnd={(e) => { e.preventDefault(); setActiveTab(tab.id); if (tab.id === 'travel') fetchTravelClaims(); }}
            className={`flex flex-col items-center gap-1 py-2 px-3 rounded-xl transition touch-manipulation cursor-pointer ${
              activeTab === tab.id ? 'text-blue-600 bg-blue-50' : 'text-zinc-400'
            }`}
            style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
            data-testid={`nav-${tab.id}`}
          >
            <tab.icon className="w-5 h-5" />
            <span className="text-xs font-medium">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Check-in Modal */}
      {showCheckInModal && <CheckInModal />}

      {/* Check-out Modal */}
      {showCheckOutModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowCheckOutModal(false)}>
          <div className="w-full max-w-sm bg-white rounded-3xl p-6 animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <div className="text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
                <LogOut className="w-8 h-8 text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-zinc-900">Check Out</h2>
              <p className="text-sm text-zinc-500 mt-1">Confirm you want to end your work day</p>
            </div>
            
            {checkInStatus && (
              <div className="p-4 rounded-2xl bg-zinc-50 mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-zinc-500">Check-in time</span>
                  <span className="font-medium text-zinc-900">
                    {checkInStatus.check_in_time ? new Date(checkInStatus.check_in_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '-'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Location</span>
                  <span className="font-medium text-zinc-900">
                    {checkInStatus.work_location === 'in_office' ? 'Office' : 'Client Site'}
                  </span>
                </div>
              </div>
            )}
            
            <div className="flex gap-3">
              <button 
                onClick={() => setShowCheckOutModal(false)}
                className="flex-1 py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-semibold"
              >
                Cancel
              </button>
              <button 
                onClick={handleCheckOut}
                disabled={loading}
                className="flex-1 py-3 bg-red-600 text-white rounded-2xl font-semibold flex items-center justify-center gap-2"
                data-testid="confirm-checkout-btn"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <LogOut className="w-5 h-5" />}
                Check Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Travel Reimbursement Modal - shows after check-out if applicable */}
      {showTravelReimbursementModal && lastTravelReimbursement && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowTravelReimbursementModal(false)}>
          <div className="w-full max-w-sm bg-white rounded-3xl p-6 animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <div className="text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
                <Navigation className="w-8 h-8 text-emerald-600" />
              </div>
              <h2 className="text-xl font-bold text-zinc-900">Travel Reimbursement</h2>
              <p className="text-sm text-zinc-500 mt-1">You're eligible for travel claim!</p>
            </div>
            
            <div className="space-y-3 mb-6">
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100">
                <div className="text-center">
                  <p className="text-3xl font-bold text-emerald-600">₹{lastTravelReimbursement.calculated_amount?.toLocaleString()}</p>
                  <p className="text-xs text-emerald-700 mt-1">Estimated Reimbursement</p>
                </div>
              </div>
              
              <div className="p-3 rounded-xl bg-zinc-50 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Distance</span>
                  <span className="font-medium">{lastTravelReimbursement.distance_km} km</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Rate</span>
                  <span className="font-medium">₹{lastTravelReimbursement.rate_per_km}/km ({lastTravelReimbursement.vehicle_type})</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Trip Type</span>
                  <span className="font-medium">{lastTravelReimbursement.is_round_trip ? 'Round Trip' : 'One Way'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">From</span>
                  <span className="font-medium text-right flex-1 ml-2 truncate">{lastTravelReimbursement.from_location}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">To</span>
                  <span className="font-medium text-right flex-1 ml-2 truncate">{lastTravelReimbursement.to_location}</span>
                </div>
              </div>
            </div>
            
            <p className="text-xs text-center text-zinc-500 mb-4">
              Claim this reimbursement through the Expense section
            </p>
            
            <div className="flex gap-3">
              <button 
                onClick={() => setShowTravelReimbursementModal(false)}
                className="flex-1 py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-semibold"
              >
                Close
              </button>
              <button 
                onClick={() => {
                  setShowTravelReimbursementModal(false);
                  setActiveTab('expense');
                }}
                className="flex-1 py-3 bg-emerald-600 text-white rounded-2xl font-semibold flex items-center justify-center gap-2"
              >
                <Receipt className="w-5 h-5" />
                Claim Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Expense Modal */}
      {showExpenseModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-end" onClick={() => setShowExpenseModal(false)}>
          <div className="w-full bg-white rounded-t-3xl max-h-[85vh] overflow-y-auto animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white pt-4 pb-2 px-6 border-b border-zinc-100">
              <div className="w-12 h-1 bg-zinc-300 rounded-full mx-auto mb-4" />
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-zinc-900">Add Expense</h2>
                  <p className="text-sm text-zinc-500">Submit a new expense claim</p>
                </div>
                <button onClick={() => setShowExpenseModal(false)} className="p-2">
                  <X className="w-6 h-6 text-zinc-400" />
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              {/* Expense Type Selection */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setExpenseForm({ ...expenseForm, is_office_expense: true, client_id: '', client_name: '', project_id: '', project_name: '' })}
                  className={`p-3 rounded-xl border-2 text-sm font-medium transition ${
                    expenseForm.is_office_expense 
                      ? 'border-amber-500 bg-amber-50 text-amber-700' 
                      : 'border-zinc-200 text-zinc-600'
                  }`}
                >
                  Office Expense
                </button>
                <button
                  type="button"
                  onClick={() => setExpenseForm({ ...expenseForm, is_office_expense: false })}
                  className={`p-3 rounded-xl border-2 text-sm font-medium transition ${
                    !expenseForm.is_office_expense 
                      ? 'border-amber-500 bg-amber-50 text-amber-700' 
                      : 'border-zinc-200 text-zinc-600'
                  }`}
                >
                  Client/Project
                </button>
              </div>

              {/* Client/Project Selection (if not office expense) */}
              {!expenseForm.is_office_expense && (
                <div className="space-y-3 p-3 bg-zinc-50 rounded-xl">
                  <div>
                    <label className="text-sm font-medium text-zinc-700 block mb-2">Client</label>
                    <select
                      value={expenseForm.client_id}
                      onChange={(e) => {
                        const client = clients.find(c => c.id === e.target.value);
                        setExpenseForm({
                          ...expenseForm,
                          client_id: e.target.value,
                          client_name: client?.name || ''
                        });
                      }}
                      className="w-full p-3 rounded-xl border border-zinc-200 text-sm bg-white"
                    >
                      <option value="">Select Client</option>
                      {clients.map(client => (
                        <option key={client.id} value={client.id}>{client.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-zinc-700 block mb-2">Project</label>
                    <select
                      value={expenseForm.project_id}
                      onChange={(e) => {
                        const project = projects.find(p => p.id === e.target.value);
                        setExpenseForm({
                          ...expenseForm,
                          project_id: e.target.value,
                          project_name: project?.name || ''
                        });
                      }}
                      className="w-full p-3 rounded-xl border border-zinc-200 text-sm bg-white"
                    >
                      <option value="">Select Project</option>
                      {projects.filter(p => !expenseForm.client_id || p.client_id === expenseForm.client_id).map(project => (
                        <option key={project.id} value={project.id}>{project.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Line Items Section */}
              <div className="border-t border-zinc-200 pt-4">
                <h3 className="text-sm font-semibold text-zinc-800 mb-3">Expense Items</h3>
                
                {/* Existing Items */}
                {expenseForm.line_items.length > 0 && (
                  <div className="space-y-2 mb-4">
                    {expenseForm.line_items.map((item, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-amber-50 rounded-xl">
                        <div className="flex items-center gap-3">
                          {item.receipt && (
                            <div className="w-10 h-10 rounded-lg overflow-hidden bg-zinc-100">
                              <img src={item.receipt} alt="Receipt" className="w-full h-full object-cover" />
                            </div>
                          )}
                          <div>
                            <p className="text-sm font-medium text-zinc-800">{item.description}</p>
                            <p className="text-xs text-zinc-500">{item.category} • {item.date}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-amber-600">₹{item.amount}</span>
                          <button onClick={() => removeLineItem(index)} className="p-1 text-red-500">
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                    <div className="text-right text-sm font-semibold text-zinc-800">
                      Total: ₹{calculateExpenseTotal().toLocaleString()}
                    </div>
                  </div>
                )}

                {/* Add New Item Form */}
                <div className="space-y-3 p-3 bg-zinc-50 rounded-xl">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-zinc-600 block mb-1">Category</label>
                      <select
                        value={lineItemForm.category}
                        onChange={(e) => setLineItemForm({...lineItemForm, category: e.target.value})}
                        className="w-full p-2 rounded-lg border border-zinc-200 text-sm bg-white"
                      >
                        <option value="local_conveyance">Local Conveyance</option>
                        <option value="travel">Travel</option>
                        <option value="food">Food & Meals</option>
                        <option value="accommodation">Accommodation</option>
                        <option value="communication">Communication</option>
                        <option value="office_supplies">Office Supplies</option>
                        <option value="client_entertainment">Client Entertainment</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-zinc-600 block mb-1">Date</label>
                      <input
                        type="date"
                        value={lineItemForm.date}
                        onChange={(e) => setLineItemForm({...lineItemForm, date: e.target.value})}
                        className="w-full p-2 rounded-lg border border-zinc-200 text-sm"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-zinc-600 block mb-1">Description</label>
                    <input
                      type="text"
                      value={lineItemForm.description}
                      onChange={(e) => setLineItemForm({...lineItemForm, description: e.target.value})}
                      placeholder="e.g., Cab fare to client site"
                      className="w-full p-2 rounded-lg border border-zinc-200 text-sm"
                    />
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="text-xs font-medium text-zinc-600 block mb-1">Amount (₹)</label>
                      <input
                        type="number"
                        value={lineItemForm.amount}
                        onChange={(e) => setLineItemForm({...lineItemForm, amount: e.target.value})}
                        placeholder="0"
                        className="w-full p-2 rounded-lg border border-zinc-200 text-sm"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs font-medium text-zinc-600 block mb-1">Receipt</label>
                      <label className="flex items-center justify-center gap-1 p-2 rounded-lg border border-dashed border-zinc-300 text-xs text-zinc-500 cursor-pointer hover:bg-zinc-50">
                        <Camera className="w-4 h-4" />
                        {lineItemForm.receipt ? 'Added' : 'Add'}
                        <input
                          type="file"
                          accept="image/*"
                          capture="environment"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              const reader = new FileReader();
                              reader.onloadend = () => {
                                setLineItemForm({...lineItemForm, receipt: reader.result});
                              };
                              reader.readAsDataURL(file);
                            }
                          }}
                        />
                      </label>
                    </div>
                    <button
                      type="button"
                      onClick={addLineItem}
                      className="self-end px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Notes (optional)</label>
                <textarea
                  value={expenseForm.notes}
                  onChange={(e) => setExpenseForm({...expenseForm, notes: e.target.value})}
                  placeholder="Additional details..."
                  rows={2}
                  className="w-full p-3 rounded-xl border border-zinc-200 text-sm resize-none"
                />
              </div>

              <button 
                onClick={handleSubmitExpense}
                disabled={loading || expenseForm.line_items.length === 0}
                className="w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-2xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="submit-expense-btn"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Receipt className="w-5 h-5" />}
                Create Expense ({expenseForm.line_items.length} items - ₹{calculateExpenseTotal().toLocaleString()})
              </button>

              <button 
                onClick={() => { setShowExpenseModal(false); resetExpenseForm(); }}
                className="w-full py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Apply Leave Modal */}
      {showLeaveModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-end" onClick={() => setShowLeaveModal(false)}>
          <div className="w-full bg-white rounded-t-3xl max-h-[85vh] overflow-y-auto animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white pt-4 pb-2 px-6 border-b border-zinc-100">
              <div className="w-12 h-1 bg-zinc-300 rounded-full mx-auto mb-4" />
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-zinc-900">Apply for Leave</h2>
                  <p className="text-sm text-zinc-500">Submit a leave request</p>
                </div>
                <button onClick={() => setShowLeaveModal(false)} className="p-2">
                  <X className="w-6 h-6 text-zinc-400" />
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              {/* Leave Balance Summary */}
              {leaveBalance && (
                <div className="grid grid-cols-3 gap-2 p-3 bg-zinc-50 rounded-xl">
                  <div className="text-center">
                    <p className="text-lg font-bold text-blue-600">{leaveBalance.casual?.available || 0}</p>
                    <p className="text-xs text-zinc-500">Casual</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-red-600">{leaveBalance.sick?.available || 0}</p>
                    <p className="text-xs text-zinc-500">Sick</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold text-emerald-600">{leaveBalance.earned?.available || 0}</p>
                    <p className="text-xs text-zinc-500">Earned</p>
                  </div>
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Leave Type *</label>
                <select
                  value={leaveForm.leave_type}
                  onChange={(e) => setLeaveForm({...leaveForm, leave_type: e.target.value})}
                  className="w-full p-3 rounded-xl border border-zinc-200 text-sm bg-white focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  data-testid="leave-type"
                >
                  <option value="casual">Casual Leave</option>
                  <option value="sick">Sick Leave</option>
                  <option value="earned">Earned Leave</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium text-zinc-700 block mb-2">From Date *</label>
                  <input
                    type="date"
                    value={leaveForm.start_date}
                    onChange={(e) => setLeaveForm({...leaveForm, start_date: e.target.value})}
                    className="w-full p-3 rounded-xl border border-zinc-200 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    data-testid="leave-start-date"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-zinc-700 block mb-2">To Date *</label>
                  <input
                    type="date"
                    value={leaveForm.end_date}
                    onChange={(e) => setLeaveForm({...leaveForm, end_date: e.target.value})}
                    min={leaveForm.start_date}
                    className="w-full p-3 rounded-xl border border-zinc-200 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    data-testid="leave-end-date"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Reason *</label>
                <textarea
                  value={leaveForm.reason}
                  onChange={(e) => setLeaveForm({...leaveForm, reason: e.target.value})}
                  placeholder="Please provide a reason for your leave..."
                  rows={3}
                  className="w-full p-3 rounded-xl border border-zinc-200 text-sm resize-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  data-testid="leave-reason"
                />
              </div>

              <button 
                onClick={handleSubmitLeave}
                disabled={loading || !leaveForm.reason}
                className="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="submit-leave-btn"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Calendar className="w-5 h-5" />}
                Submit Leave Request
              </button>

              <button 
                onClick={() => setShowLeaveModal(false)}
                className="w-full py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Travel Claim Modal */}
      {showTravelModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-end" onClick={() => setShowTravelModal(false)}>
          <div className="w-full bg-white rounded-t-3xl max-h-[85vh] overflow-y-auto animate-slide-up" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white pt-4 pb-2 px-6 border-b border-zinc-100">
              <div className="w-12 h-1 bg-zinc-300 rounded-full mx-auto mb-4" />
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-zinc-900">Travel Claim</h2>
                  <p className="text-sm text-zinc-500">Enter travel details for reimbursement</p>
                </div>
                <button onClick={() => setShowTravelModal(false)} className="p-2">
                  <X className="w-6 h-6 text-zinc-400" />
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              {/* Start Location */}
              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Start Location *</label>
                {travelForm.start_location ? (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-emerald-600" />
                      <div>
                        <p className="text-sm font-medium text-zinc-900">{travelForm.start_location.name}</p>
                        <p className="text-xs text-zinc-500 truncate max-w-[200px]">{travelForm.start_location.address}</p>
                      </div>
                    </div>
                    <button onClick={() => setTravelForm({ ...travelForm, start_location: null })} className="p-1 text-zinc-400">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                      <input
                        type="text"
                        value={selectingFor === 'start' ? locationSearchQuery : ''}
                        onChange={(e) => { setLocationSearchQuery(e.target.value); setSelectingFor('start'); }}
                        onFocus={() => setSelectingFor('start')}
                        placeholder="Search for a location..."
                        className="w-full pl-10 pr-4 py-3 rounded-xl border border-zinc-200 text-sm"
                        data-testid="start-location-search"
                      />
                      {searchingLocations && selectingFor === 'start' && (
                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 animate-spin" />
                      )}
                    </div>
                    
                    <button 
                      onClick={useCurrentLocationAsStart}
                      disabled={locationLoading}
                      className="w-full py-2 bg-blue-50 text-blue-600 rounded-xl text-sm font-medium flex items-center justify-center gap-2"
                    >
                      {locationLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Navigation className="w-4 h-4" />}
                      Use Current Location
                    </button>
                    
                    {/* Search Results */}
                    {selectingFor === 'start' && locationSearchResults.length > 0 && (
                      <div className="bg-white border border-zinc-200 rounded-xl shadow-lg max-h-40 overflow-y-auto">
                        {locationSearchResults.map((loc, i) => (
                          <button
                            key={i}
                            onClick={() => selectLocation(loc)}
                            className="w-full p-3 text-left border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                          >
                            <p className="text-sm font-medium text-zinc-900">{loc.name}</p>
                            <p className="text-xs text-zinc-500 truncate">{loc.address}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* End Location */}
              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">End Location *</label>
                {travelForm.end_location ? (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-emerald-600" />
                      <div>
                        <p className="text-sm font-medium text-zinc-900">{travelForm.end_location.name}</p>
                        <p className="text-xs text-zinc-500 truncate max-w-[200px]">{travelForm.end_location.address}</p>
                      </div>
                    </div>
                    <button onClick={() => setTravelForm({ ...travelForm, end_location: null })} className="p-1 text-zinc-400">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                      <input
                        type="text"
                        value={selectingFor === 'end' ? locationSearchQuery : ''}
                        onChange={(e) => { setLocationSearchQuery(e.target.value); setSelectingFor('end'); }}
                        onFocus={() => setSelectingFor('end')}
                        placeholder="Search for a location..."
                        className="w-full pl-10 pr-4 py-3 rounded-xl border border-zinc-200 text-sm"
                        data-testid="end-location-search"
                      />
                      {searchingLocations && selectingFor === 'end' && (
                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 animate-spin" />
                      )}
                    </div>
                    
                    {/* Search Results */}
                    {selectingFor === 'end' && locationSearchResults.length > 0 && (
                      <div className="bg-white border border-zinc-200 rounded-xl shadow-lg max-h-40 overflow-y-auto">
                        {locationSearchResults.map((loc, i) => (
                          <button
                            key={i}
                            onClick={() => selectLocation(loc)}
                            className="w-full p-3 text-left border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                          >
                            <p className="text-sm font-medium text-zinc-900">{loc.name}</p>
                            <p className="text-xs text-zinc-500 truncate">{loc.address}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Vehicle Type */}
              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Vehicle Type *</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'car', label: 'Car', icon: Car, rate: '₹7/km' },
                    { value: 'two_wheeler', label: 'Two Wheeler', icon: Bike, rate: '₹3/km' },
                  ].map((v) => (
                    <button
                      key={v.value}
                      onClick={() => setTravelForm({ ...travelForm, vehicle_type: v.value })}
                      className={`p-3 rounded-xl border-2 flex items-center gap-3 transition ${
                        travelForm.vehicle_type === v.value 
                          ? 'border-teal-500 bg-teal-50' 
                          : 'border-zinc-200'
                      }`}
                    >
                      <v.icon className={`w-6 h-6 ${travelForm.vehicle_type === v.value ? 'text-teal-600' : 'text-zinc-400'}`} />
                      <div className="text-left">
                        <p className={`text-sm font-medium ${travelForm.vehicle_type === v.value ? 'text-teal-700' : 'text-zinc-700'}`}>{v.label}</p>
                        <p className="text-xs text-zinc-500">{v.rate}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Round Trip Toggle */}
              <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-xl">
                <div>
                  <p className="font-medium text-zinc-900">Round Trip</p>
                  <p className="text-xs text-zinc-500">Double the distance for return journey</p>
                </div>
                <button
                  onClick={() => setTravelForm({ ...travelForm, is_round_trip: !travelForm.is_round_trip })}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    travelForm.is_round_trip ? 'bg-teal-500' : 'bg-zinc-300'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    travelForm.is_round_trip ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>

              {/* Notes */}
              <div>
                <label className="text-sm font-medium text-zinc-700 block mb-2">Notes (optional)</label>
                <textarea
                  value={travelForm.notes}
                  onChange={(e) => setTravelForm({ ...travelForm, notes: e.target.value })}
                  placeholder="Purpose of travel, client meeting details, etc."
                  rows={2}
                  className="w-full p-3 rounded-xl border border-zinc-200 text-sm resize-none"
                />
              </div>

              <button 
                onClick={handleSubmitTravelClaim}
                disabled={loading || !travelForm.start_location || !travelForm.end_location}
                className="w-full py-4 bg-gradient-to-r from-teal-500 to-cyan-500 text-white rounded-2xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                data-testid="submit-travel-btn"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Car className="w-5 h-5" />}
                Calculate & Submit Claim
              </button>

              <button 
                onClick={() => setShowTravelModal(false)}
                className="w-full py-3 bg-zinc-100 text-zinc-700 rounded-2xl font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slide-up {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
        /* Mobile touch optimization */
        button, a, [role="button"] {
          -webkit-tap-highlight-color: transparent;
          touch-action: manipulation;
        }
        .touch-manipulation {
          touch-action: manipulation;
        }
      `}</style>
    </div>
  );
};

export default EmployeeMobileApp;
