import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { 
  Users, Calendar, Clock, DollarSign, FileText,
  UserCheck, UserX, Briefcase, CheckCircle, AlertCircle, LogIn
} from 'lucide-react';
import { Link } from 'react-router-dom';
import QuickCheckInModal from '../components/QuickCheckInModal';

const HRDashboard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Quick Check-in state
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [attendanceStatus, setAttendanceStatus] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchAttendanceStatus();
  }, []);

  const fetchAttendanceStatus = async () => {
    try {
      const res = await axios.get(`${API}/my/check-status`);
      setAttendanceStatus(res.data);
    } catch (err) {
      console.error('Failed to fetch attendance status');
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API}/stats/hr-dashboard`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch HR stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
      </div>
    );
  }

  const employees = stats?.employees || {};
  const attendance = stats?.attendance || {};
  const leaves = stats?.leaves || {};
  const payroll = stats?.payroll || {};

  return (
    <div className="space-y-6" data-testid="hr-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">HR Dashboard</h1>
          <p className="text-sm text-zinc-500">Manage employees, attendance and payroll</p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700">
          {attendance.attendance_rate || 0}% Attendance Today
        </Badge>
      </div>

      {/* Quick Attendance Card - Light Blue to Dark Blue Gradient */}
      <Card 
        className="cursor-pointer transition-all hover:shadow-lg bg-gradient-to-r from-sky-400 via-blue-500 to-blue-700 border-blue-500"
        onClick={() => setShowQuickCheckIn(true)}
        data-testid="hr-quick-attendance-card"
      >
        <CardContent className="flex items-center justify-between p-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
              <Clock className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Quick Attendance</h3>
              <p className="text-white/70 text-sm">
                {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out 
                  ? 'Completed for today' 
                  : attendanceStatus?.has_checked_in 
                    ? `Checked in at ${attendanceStatus?.check_in_time?.split('T')[1]?.slice(0,5) || '-'}` 
                    : 'Tap to check in'}
              </p>
            </div>
          </div>
          {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500 rounded-lg">
              <CheckCircle className="w-5 h-5 text-white" />
              <span className="text-white font-medium">Done</span>
            </div>
          ) : attendanceStatus?.has_checked_in ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-amber-500 rounded-lg">
              <LogIn className="w-5 h-5 text-white" />
              <span className="text-white font-medium">Check Out</span>
            </div>
          ) : (
            <button className="bg-white text-blue-600 hover:bg-white/90 h-11 px-6 font-semibold rounded-lg flex items-center gap-2">
              <LogIn className="w-5 h-5" /> Check In
            </button>
          )}
        </CardContent>
      </Card>

      {/* Quick Check-in Modal */}
      <QuickCheckInModal 
        isOpen={showQuickCheckIn} 
        onClose={() => { setShowQuickCheckIn(false); fetchAttendanceStatus(); }} 
        user={user} 
      />

      {/* Employee Overview */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Total Employees</p>
                <p className="text-3xl font-bold text-zinc-900 mt-1">{employees.total || 0}</p>
                {employees.new_this_month > 0 && (
                  <p className="text-xs text-green-600 mt-1">+{employees.new_this_month} this month</p>
                )}
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Present Today</p>
                <p className="text-3xl font-bold text-green-600 mt-1">{attendance.present_today || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <UserCheck className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">WFH Today</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">{attendance.wfh_today || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Absent Today</p>
                <p className="text-3xl font-bold text-red-600 mt-1">{attendance.absent_today || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <UserX className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Department Breakdown */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Employees by Department
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            {Object.entries(employees.by_department || {}).map(([dept, count]) => (
              <div key={dept} className="text-center p-4 bg-zinc-50 rounded-lg">
                <p className="text-2xl font-bold text-zinc-900">{count}</p>
                <p className="text-xs text-zinc-500 mt-1 truncate">{dept}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Pending Actions */}
      <div className="grid grid-cols-2 gap-4">
        {/* Pending Leaves */}
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Leave Requests
              </CardTitle>
              <Link to="/leave-management" className="text-sm text-blue-600 hover:underline">
                View All
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="font-medium text-amber-800">Pending Approval</p>
                  <p className="text-sm text-amber-600">Requires your attention</p>
                </div>
              </div>
              <Badge className="bg-amber-600 text-white text-lg px-4">
                {leaves.pending_requests || 0}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Pending Expenses */}
        <Card className="border-zinc-200">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                Expense Approvals
              </CardTitle>
              <Link to="/approvals" className="text-sm text-blue-600 hover:underline">
                View All
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-purple-800">Pending Expenses</p>
                  <p className="text-sm text-purple-600">Awaiting approval</p>
                </div>
              </div>
              <Badge className="bg-purple-600 text-white text-lg px-4">
                {stats?.expenses?.pending_approvals || 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payroll Status */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Payroll Status - {new Date().toLocaleString('default', { month: 'long' })}
            </CardTitle>
            <Link to="/payroll" className="text-sm text-blue-600 hover:underline">
              Manage Payroll
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-500">Processed vs Total Employees</span>
              <span className="font-medium">
                {payroll.processed_this_month || 0} / {employees.total || 0}
              </span>
            </div>
            <Progress 
              value={employees.total > 0 ? (payroll.processed_this_month / employees.total) * 100 : 0} 
              className="h-3"
            />
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <div>
                  <p className="text-xl font-bold text-green-600">{payroll.processed_this_month || 0}</p>
                  <p className="text-xs text-zinc-500">Processed</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-amber-50 rounded-lg">
                <AlertCircle className="w-6 h-6 text-amber-600" />
                <div>
                  <p className="text-xl font-bold text-amber-600">{payroll.pending || 0}</p>
                  <p className="text-xs text-zinc-500">Pending</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Employees', href: '/employees', icon: Users, color: 'bg-blue-600' },
          { label: 'Attendance', href: '/attendance-management', icon: Calendar, color: 'bg-green-600' },
          { label: 'Leave Management', href: '/leave-management', icon: Clock, color: 'bg-purple-600' },
          { label: 'Payroll', href: '/payroll', icon: DollarSign, color: 'bg-emerald-600' },
        ].map((action, i) => (
          <Link key={i} to={action.href}>
            <Card className="border-zinc-200 hover:border-zinc-300 transition-colors cursor-pointer">
              <CardContent className="pt-4 pb-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${action.color} flex items-center justify-center`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <span className="font-medium text-zinc-700">{action.label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default HRDashboard;
