import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import axios from 'axios';
import { 
  CheckCircle, Clock, MapPin, LogIn, LogOut, Calendar, Receipt, 
  Home, Building2, Navigation, Loader2, AlertCircle, ChevronRight,
  Plus, Camera, FileText, TrendingUp, User, Bell, Settings,
  Coffee, Sun, Moon, Briefcase, IndianRupee, CalendarDays,
  CheckCircle2, XCircle, Timer, Wallet
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
  const [selectedWorkLocation, setSelectedWorkLocation] = useState('in_office');
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [attRes, leaveRes, expRes] = await Promise.all([
        axios.get(`${API}/my/attendance?month=${new Date().toISOString().slice(0, 7)}`).catch(() => ({ data: null })),
        axios.get(`${API}/my/leave-balance`).catch(() => ({ data: null })),
        axios.get(`${API}/my/expenses`).catch(() => ({ data: null }))
      ]);
      
      setAttendanceData(attRes.data);
      setLeaveBalance(leaveRes.data);
      setExpenses(expRes.data?.expenses || []);
      
      // Check if already checked in today
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
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleCheckIn = async () => {
    if (!location) {
      captureLocation();
      return;
    }
    
    setLoading(true);
    try {
      await axios.post(`${API}/my/check-in`, {
        work_location: selectedWorkLocation,
        remarks: 'Mobile app check-in',
        geo_location: {
          latitude: location.latitude,
          longitude: location.longitude,
          accuracy: location.accuracy,
          address: location.address
        }
      });
      toast.success('Check-in successful!');
      setShowCheckInModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
    } finally {
      setLoading(false);
    }
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
    <div className="space-y-4 pb-20">
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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-medium">Checked In</p>
                  <p className="text-xs text-blue-200">
                    {checkInStatus.work_location === 'in_office' ? 'Office' : 
                     checkInStatus.work_location === 'onsite' ? 'On-Site' : 'WFH'}
                  </p>
                </div>
              </div>
              <span className="text-xs bg-emerald-500/30 px-3 py-1 rounded-full">Active</span>
            </div>
          ) : (
            <button 
              onClick={() => { setShowCheckInModal(true); captureLocation(); }}
              className="w-full flex items-center justify-center gap-2 py-2 bg-white/20 rounded-xl hover:bg-white/30 transition"
            >
              <LogIn className="w-5 h-5" />
              <span className="font-medium">Tap to Check In</span>
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
            className="flex flex-col items-center gap-2 p-4 bg-white rounded-2xl shadow-sm border border-zinc-100"
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
          <div className="text-center p-3 bg-amber-50 rounded-xl">
            <p className="text-2xl font-bold text-amber-600">{attendanceData?.summary?.wfh || 0}</p>
            <p className="text-xs text-zinc-500">WFH</p>
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
                record.status === 'present' ? 'bg-emerald-100 text-emerald-600' :
                record.status === 'work_from_home' ? 'bg-blue-100 text-blue-600' :
                'bg-purple-100 text-purple-600'
              }`}>
                {record.status === 'present' ? <CheckCircle2 className="w-5 h-5" /> :
                 record.status === 'work_from_home' ? <Home className="w-5 h-5" /> :
                 <Calendar className="w-5 h-5" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-zinc-900">
                  {record.status === 'present' ? 'Present' :
                   record.status === 'work_from_home' ? 'Work from Home' :
                   record.status === 'on_leave' ? 'On Leave' : record.status}
                </p>
                <p className="text-xs text-zinc-500">{record.date}</p>
              </div>
              {record.work_location && (
                <span className="text-xs px-2 py-1 bg-zinc-200 rounded-full text-zinc-600">
                  {record.work_location === 'in_office' ? 'Office' :
                   record.work_location === 'onsite' ? 'On-Site' : 'WFH'}
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
    <div className="space-y-4 pb-20">
      {/* Check-in Card */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-3xl p-6 text-white shadow-xl">
        <div className="text-center">
          <p className="text-indigo-200 text-sm mb-2">{formatDate(currentTime)}</p>
          <p className="text-5xl font-bold tracking-wider mb-4">{formatTime(currentTime)}</p>
          
          {checkInStatus ? (
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur">
              <div className="flex items-center justify-center gap-2 text-emerald-300 mb-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">You're Checked In</span>
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
            </div>
          ) : (
            <button 
              onClick={() => { setShowCheckInModal(true); captureLocation(); }}
              className="w-full py-4 bg-white text-indigo-700 rounded-2xl font-semibold text-lg shadow-lg hover:bg-indigo-50 transition flex items-center justify-center gap-2"
            >
              <LogIn className="w-6 h-6" />
              Check In Now
            </button>
          )}
        </div>
      </div>

      {/* Monthly Stats */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Present', value: attendanceData?.summary?.present || 0, icon: CheckCircle2, color: 'emerald' },
          { label: 'WFH', value: attendanceData?.summary?.wfh || 0, icon: Home, color: 'blue' },
          { label: 'Half Day', value: attendanceData?.summary?.half_day || 0, icon: Timer, color: 'amber' },
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
                record.status === 'present' ? 'bg-emerald-100 text-emerald-600' :
                record.status === 'work_from_home' ? 'bg-blue-100 text-blue-600' :
                record.status === 'absent' ? 'bg-red-100 text-red-600' :
                'bg-purple-100 text-purple-600'
              }`}>
                {record.status === 'present' && <CheckCircle2 className="w-5 h-5" />}
                {record.status === 'work_from_home' && <Home className="w-5 h-5" />}
                {record.status === 'absent' && <XCircle className="w-5 h-5" />}
                {record.status === 'on_leave' && <Calendar className="w-5 h-5" />}
                {record.status === 'half_day' && <Timer className="w-5 h-5" />}
              </div>
              <div className="flex-1">
                <p className="font-medium text-zinc-900">{record.date}</p>
                <p className="text-xs text-zinc-500 capitalize">{record.status?.replace('_', ' ')}</p>
              </div>
              {record.work_location && (
                <div className="flex items-center gap-1 text-xs text-zinc-500">
                  {record.work_location === 'in_office' && <Building2 className="w-3 h-3" />}
                  {record.work_location === 'onsite' && <MapPin className="w-3 h-3" />}
                  {record.work_location === 'wfh' && <Home className="w-3 h-3" />}
                  <span>{record.work_location === 'in_office' ? 'Office' : record.work_location === 'onsite' ? 'Site' : 'WFH'}</span>
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
    <div className="space-y-4 pb-20">
      {/* Leave Balance Cards */}
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

      {/* Apply Leave Button */}
      <button className="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2">
        <Plus className="w-5 h-5" />
        Apply for Leave
      </button>

      {/* Leave Requests */}
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
    <div className="space-y-4 pb-20">
      {/* Expense Summary */}
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

      {/* Add Expense Button */}
      <button className="w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2">
        <Camera className="w-5 h-5" />
        Add New Expense
      </button>

      {/* Expense List */}
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

  // Check-in Modal
  const CheckInModal = () => (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div className="w-full bg-white rounded-t-3xl p-6 animate-slide-up">
        <div className="w-12 h-1 bg-zinc-300 rounded-full mx-auto mb-6" />
        
        <h2 className="text-xl font-bold text-zinc-900 mb-2">Check In</h2>
        <p className="text-sm text-zinc-500 mb-6">Confirm your work location to check in</p>

        {/* Location Status */}
        <div className="p-4 rounded-2xl bg-zinc-50 mb-6">
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
                <p className="text-xs text-zinc-500 leading-relaxed">{location.address}</p>
              )}
              <p className="text-xs text-zinc-400">
                {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)} (±{Math.round(location.accuracy)}m)
              </p>
            </div>
          ) : (
            <button 
              onClick={captureLocation}
              className="flex items-center gap-2 text-blue-600"
            >
              <Navigation className="w-5 h-5" />
              <span className="font-medium">Tap to get location</span>
            </button>
          )}
        </div>

        {/* Work Location Selection */}
        <p className="text-sm font-medium text-zinc-700 mb-3">Where are you working from?</p>
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { value: 'in_office', label: 'Office', icon: Building2, color: 'blue' },
            { value: 'onsite', label: 'On-Site', icon: MapPin, color: 'emerald' },
            { value: 'wfh', label: 'Home', icon: Home, color: 'amber' },
          ].map((loc) => (
            <button
              key={loc.value}
              onClick={() => setSelectedWorkLocation(loc.value)}
              className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition ${
                selectedWorkLocation === loc.value
                  ? `border-${loc.color}-500 bg-${loc.color}-50`
                  : 'border-zinc-200'
              }`}
            >
              <loc.icon className={`w-8 h-8 ${selectedWorkLocation === loc.value ? `text-${loc.color}-600` : 'text-zinc-400'}`} />
              <span className={`text-sm font-medium ${selectedWorkLocation === loc.value ? `text-${loc.color}-700` : 'text-zinc-600'}`}>
                {loc.label}
              </span>
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button 
            onClick={() => setShowCheckInModal(false)}
            className="flex-1 py-4 bg-zinc-100 text-zinc-700 rounded-2xl font-semibold"
          >
            Cancel
          </button>
          <button 
            onClick={handleCheckIn}
            disabled={!location || loading}
            className="flex-1 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle className="w-5 h-5" />}
            Check In
          </button>
        </div>
      </div>
    </div>
  );

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
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-zinc-200 px-4 py-2 flex justify-around" style={{ maxWidth: '430px', margin: '0 auto' }}>
        {[
          { id: 'home', icon: Home, label: 'Home' },
          { id: 'attendance', icon: Clock, label: 'Attendance' },
          { id: 'leave', icon: Calendar, label: 'Leave' },
          { id: 'expense', icon: Receipt, label: 'Expense' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex flex-col items-center gap-1 py-2 px-4 rounded-xl transition ${
              activeTab === tab.id ? 'text-blue-600 bg-blue-50' : 'text-zinc-400'
            }`}
          >
            <tab.icon className="w-6 h-6" />
            <span className="text-xs font-medium">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Check-in Modal */}
      {showCheckInModal && <CheckInModal />}

      <style>{`
        @keyframes slide-up {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default EmployeeMobileApp;
