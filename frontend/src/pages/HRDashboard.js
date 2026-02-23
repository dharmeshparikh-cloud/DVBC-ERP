import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { 
  Users, Calendar, Clock, DollarSign, FileText,
  UserCheck, UserX, Briefcase, CheckCircle, AlertCircle, LogIn, Book, Download, Mail, ArrowRight
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import QuickCheckInModal from '../components/QuickCheckInModal';

const HRDashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Quick Check-in state
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [attendanceStatus, setAttendanceStatus] = useState(null);
  
  // Documentation generation state
  const [generatingDocs, setGeneratingDocs] = useState(false);
  const [docResult, setDocResult] = useState(null);

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

  const generateDocumentation = async (emailTo = null) => {
    setGeneratingDocs(true);
    try {
      let url = `${API}/documentation/generate-hr-docs`;
      if (emailTo) {
        url += `?email_to=${encodeURIComponent(emailTo)}`;
      }
      const response = await axios.post(url);
      setDocResult(response.data);
      if (response.data.email_status === 'sent') {
        toast.success('Documentation generated and emailed successfully!');
      } else {
        toast.success('Documentation generated successfully!');
      }
    } catch (error) {
      console.error('Failed to generate documentation:', error);
      toast.error('Failed to generate documentation');
    } finally {
      setGeneratingDocs(false);
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
    <div className="space-y-4 md:space-y-6" data-testid="hr-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-100">HR Dashboard</h1>
          <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400">Manage employees, attendance and payroll</p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 w-fit">
          {attendance.attendance_rate || 0}% Attendance Today
        </Badge>
      </div>

      {/* Quick Attendance Card - Light Blue to Dark Blue Gradient */}
      <Card 
        className="cursor-pointer transition-all hover:shadow-lg bg-gradient-to-r from-sky-400 via-blue-500 to-blue-700 border-blue-500"
        onClick={() => setShowQuickCheckIn(true)}
        data-testid="hr-quick-attendance-card"
      >
        <CardContent className="flex items-center justify-between p-4 md:p-5">
          <div className="flex items-center gap-3 md:gap-4">
            <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
              <Clock className="w-5 h-5 md:w-6 md:h-6 text-white" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base md:text-lg font-bold text-white">Quick Attendance</h3>
              <p className="text-white/70 text-xs md:text-sm truncate">
                {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out 
                  ? 'Completed for today' 
                  : attendanceStatus?.has_checked_in 
                    ? `Checked in at ${attendanceStatus?.check_in_time?.split('T')[1]?.slice(0,5) || '-'}` 
                    : 'Tap to check in'}
              </p>
            </div>
          </div>
          {attendanceStatus?.has_checked_in && attendanceStatus?.has_checked_out ? (
            <div className="flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-emerald-500 rounded-lg flex-shrink-0">
              <CheckCircle className="w-4 h-4 md:w-5 md:h-5 text-white" />
              <span className="text-white font-medium text-sm md:text-base">Done</span>
            </div>
          ) : attendanceStatus?.has_checked_in ? (
            <div className="flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-amber-500 rounded-lg flex-shrink-0">
              <LogIn className="w-4 h-4 md:w-5 md:h-5 text-white" />
              <span className="text-white font-medium text-sm md:text-base hidden sm:inline">Check Out</span>
              <span className="text-white font-medium text-sm sm:hidden">Out</span>
            </div>
          ) : (
            <button className="bg-white text-blue-600 hover:bg-white/90 h-9 md:h-11 px-4 md:px-6 font-semibold rounded-lg flex items-center gap-1.5 md:gap-2 text-sm md:text-base flex-shrink-0">
              <LogIn className="w-4 h-4 md:w-5 md:h-5" /> <span className="hidden sm:inline">Check In</span><span className="sm:hidden">In</span>
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

      {/* Employee Overview - 2 cols on mobile, 4 cols on desktop */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="p-4 md:pt-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400 truncate">Total Employees</p>
                <p className="text-2xl md:text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-0.5 md:mt-1">{employees.total || 0}</p>
                {employees.new_this_month > 0 && (
                  <p className="text-[10px] md:text-xs text-green-600 mt-0.5 md:mt-1">+{employees.new_this_month} this month</p>
                )}
              </div>
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                <Users className="w-5 h-5 md:w-6 md:h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="p-4 md:pt-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400 truncate">Present Today</p>
                <p className="text-2xl md:text-3xl font-bold text-green-600 mt-0.5 md:mt-1">{attendance.present_today || 0}</p>
              </div>
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                <UserCheck className="w-5 h-5 md:w-6 md:h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="p-4 md:pt-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400 truncate">WFH Today</p>
                <p className="text-2xl md:text-3xl font-bold text-blue-600 mt-0.5 md:mt-1">{attendance.wfh_today || 0}</p>
              </div>
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                <Briefcase className="w-5 h-5 md:w-6 md:h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="p-4 md:pt-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400 truncate">Absent Today</p>
                <p className="text-2xl md:text-3xl font-bold text-red-600 mt-0.5 md:mt-1">{attendance.absent_today || 0}</p>
              </div>
              <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
                <UserX className="w-5 h-5 md:w-6 md:h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Department Breakdown */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader className="pb-2 px-4 md:px-6">
          <CardTitle className="text-sm md:text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Employees by Department
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 md:px-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 md:gap-4">
            {Object.entries(employees.by_department || {}).map(([dept, count]) => (
              <div key={dept} className="text-center p-3 md:p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
                <p className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-100">{count}</p>
                <p className="text-[10px] md:text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 md:mt-1 truncate">{dept}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Pending Actions - Stack on mobile */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
        {/* Pending Leaves */}
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader className="pb-2 px-4 md:px-6">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm md:text-base flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Leave Requests
              </CardTitle>
              <Link to="/leave-management" className="text-xs md:text-sm text-blue-600 hover:underline">
                View All
              </Link>
            </div>
          </CardHeader>
          <CardContent className="px-4 md:px-6">
            <div className="flex items-center justify-between p-3 md:p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
              <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
                <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-amber-100 dark:bg-amber-800 flex items-center justify-center flex-shrink-0">
                  <Clock className="w-4 h-4 md:w-5 md:h-5 text-amber-600" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-amber-800 dark:text-amber-300 text-sm md:text-base">Pending Approval</p>
                  <p className="text-xs md:text-sm text-amber-600 dark:text-amber-400 truncate">Requires your attention</p>
                </div>
              </div>
              <Badge className="bg-amber-600 text-white text-base md:text-lg px-3 md:px-4 flex-shrink-0">
                {leaves.pending_requests || 0}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Pending Expenses */}
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader className="pb-2 px-4 md:px-6">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm md:text-base flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                Expense Approvals
              </CardTitle>
              <Link to="/approvals" className="text-xs md:text-sm text-blue-600 hover:underline">
                View All
              </Link>
            </div>
          </CardHeader>
          <CardContent className="px-4 md:px-6">
            <div className="flex items-center justify-between p-3 md:p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
                <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-purple-100 dark:bg-purple-800 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-4 h-4 md:w-5 md:h-5 text-purple-600" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-purple-800 dark:text-purple-300 text-sm md:text-base">Pending Expenses</p>
                  <p className="text-xs md:text-sm text-purple-600 dark:text-purple-400 truncate">Awaiting approval</p>
                </div>
              </div>
              <Badge className="bg-purple-600 text-white text-base md:text-lg px-3 md:px-4 flex-shrink-0">
                {stats?.expenses?.pending_approvals || 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payroll Status */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader className="pb-2 px-4 md:px-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <CardTitle className="text-sm md:text-base flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Payroll - {new Date().toLocaleString('default', { month: 'short' })}
            </CardTitle>
            <Link to="/payroll" className="text-xs md:text-sm text-blue-600 hover:underline">
              Manage Payroll
            </Link>
          </div>
        </CardHeader>
        <CardContent className="px-4 md:px-6">
          <div className="space-y-3 md:space-y-4">
            <div className="flex items-center justify-between text-xs md:text-sm">
              <span className="text-zinc-500 dark:text-zinc-400">Processed vs Total</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {payroll.processed_this_month || 0} / {employees.total || 0}
              </span>
            </div>
            <Progress 
              value={employees.total > 0 ? (payroll.processed_this_month / employees.total) * 100 : 0} 
              className="h-2 md:h-3"
            />
            <div className="grid grid-cols-2 gap-2 md:gap-4 pt-1 md:pt-2">
              <div className="flex items-center gap-2 md:gap-3 p-2.5 md:p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <CheckCircle className="w-5 h-5 md:w-6 md:h-6 text-green-600 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-lg md:text-xl font-bold text-green-600">{payroll.processed_this_month || 0}</p>
                  <p className="text-[10px] md:text-xs text-zinc-500 dark:text-zinc-400">Processed</p>
                </div>
              </div>
              <div className="flex items-center gap-2 md:gap-3 p-2.5 md:p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <AlertCircle className="w-5 h-5 md:w-6 md:h-6 text-amber-600 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-lg md:text-xl font-bold text-amber-600">{payroll.pending || 0}</p>
                  <p className="text-[10px] md:text-xs text-zinc-500 dark:text-zinc-400">Pending</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* HR Documentation Card */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader className="pb-2 px-4 md:px-6">
          <CardTitle className="text-sm md:text-base flex items-center gap-2">
            <Book className="w-4 h-4" />
            HR Module Documentation
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 md:px-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Generate complete HR module documentation pack (PDF & DOCX) covering business logic, workflows, SOPs, and training materials.
              </p>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <button
                onClick={() => generateDocumentation(user?.email)}
                disabled={generatingDocs}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
                data-testid="generate-docs-email-btn"
              >
                {generatingDocs ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Mail className="w-4 h-4" />
                )}
                {generatingDocs ? 'Generating...' : 'Generate & Email'}
              </button>
            </div>
          </div>
          
          {/* Download links when docs are ready */}
          {docResult && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-2">
                Documentation ready! {docResult.email_status === 'sent' && '(Emailed to your address)'}
              </p>
              <div className="flex gap-2">
                <a
                  href={`${API}${docResult.pdf_download_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium"
                >
                  <Download className="w-3 h-3" /> PDF
                </a>
                <a
                  href={`${API}${docResult.docx_download_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium"
                >
                  <Download className="w-3 h-3" /> DOCX
                </a>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions - 2x2 on mobile */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4">
        {[
          { label: 'Employees', href: '/employees', icon: Users, color: 'bg-blue-600' },
          { label: 'Attendance', href: '/attendance-management', icon: Calendar, color: 'bg-green-600' },
          { label: 'Leave Management', href: '/leave-management', icon: Clock, color: 'bg-purple-600' },
          { label: 'Payroll', href: '/payroll', icon: DollarSign, color: 'bg-emerald-600' },
        ].map((action, i) => (
          <Link key={i} to={action.href}>
            <Card className="border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors cursor-pointer">
              <CardContent className="p-3 md:pt-4 md:pb-4 flex items-center gap-2 md:gap-3">
                <div className={`w-8 h-8 md:w-10 md:h-10 rounded-lg ${action.color} flex items-center justify-center flex-shrink-0`}>
                  <action.icon className="w-4 h-4 md:w-5 md:h-5 text-white" />
                </div>
                <span className="font-medium text-zinc-700 dark:text-zinc-300 text-sm md:text-base truncate">{action.label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default HRDashboard;
