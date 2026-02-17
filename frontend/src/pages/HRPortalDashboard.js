import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { 
  Users, UserPlus, Calendar, Clock, Wallet, AlertCircle,
  CheckCircle, XCircle, TrendingUp, Briefcase, FileText,
  ArrowRight, Bell
} from 'lucide-react';

const HRPortalDashboard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [staffingRequests, setStaffingRequests] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  const isHRManager = user?.role === 'hr_manager';

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch HR stats
      const statsRes = await fetch(`${API}/stats/hr-dashboard`, { headers });
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }

      // Fetch staffing notifications for HR Manager
      if (isHRManager) {
        const notifRes = await fetch(`${API}/notifications`, { headers });
        if (notifRes.ok) {
          const notifications = await notifRes.json();
          const staffing = notifications.filter(n => n.type === 'project_staffing_required');
          setStaffingRequests(staffing.slice(0, 5));
        }
      }

      // Fetch pending approvals
      const approvalsRes = await fetch(`${API}/approvals/pending`, { headers });
      if (approvalsRes.ok) {
        const approvals = await approvalsRes.json();
        setPendingApprovals(approvals.slice(0, 5));
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  const employees = stats?.employees || {};
  const attendance = stats?.attendance || {};
  const leaves = stats?.leaves || {};
  const payroll = stats?.payroll || {};

  return (
    <div className="space-y-4 md:space-y-6" data-testid="hr-portal-dashboard">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Welcome, {user?.full_name?.split(' ')[0]}!
          </h1>
          <p className="text-xs md:text-sm text-zinc-500 dark:text-zinc-400">
            {isHRManager ? 'HR Manager Dashboard' : 'HR Executive Dashboard'}
          </p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 w-fit text-xs md:text-sm">
          {attendance.attendance_rate || 0}% Attendance Today
        </Badge>
      </div>

      {/* Key Metrics - 2 cols on mobile */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="p-3 md:pt-6 md:px-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-[10px] md:text-sm text-zinc-500 dark:text-zinc-400">Total Employees</p>
                <p className="text-xl md:text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-0.5">
                  {employees.total || 0}
                </p>
                {employees.new_this_month > 0 && (
                  <p className="text-xs text-emerald-600 mt-1">
                    +{employees.new_this_month} this month
                  </p>
                )}
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Present Today</p>
                <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {attendance.present_today || 0}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {attendance.wfh_today || 0} WFH
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Pending Leaves</p>
                <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {leaves.pending_requests || 0}
                </p>
                <p className="text-xs text-amber-600 mt-1">
                  Requires approval
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Calendar className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Payroll Pending</p>
                <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {payroll.pending || 0}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {payroll.processed_this_month || 0} processed
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                <Wallet className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Staffing Requests - HR Manager Only */}
        {isHRManager && (
          <Card className="col-span-2 border-zinc-200 dark:border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-emerald-600" />
                Staffing Requests
              </CardTitle>
              <Link to="/hr/staffing-requests">
                <Button variant="ghost" size="sm">
                  View All <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {staffingRequests.length > 0 ? (
                <div className="space-y-3">
                  {staffingRequests.map((request, idx) => (
                    <div 
                      key={request.id || idx} 
                      className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                          <Briefcase className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <p className="font-medium text-zinc-900 dark:text-zinc-100">
                            {request.metadata?.project_name || request.title}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {request.metadata?.resources_needed || 0} resources needed • Start: {request.metadata?.start_date || 'TBD'}
                          </p>
                        </div>
                      </div>
                      <Badge className={request.priority === 'high' ? 'bg-red-100 text-red-700' : 'bg-zinc-100 text-zinc-700'}>
                        {request.priority || 'normal'}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-zinc-500">
                  <Briefcase className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                  <p>No pending staffing requests</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Pending Approvals */}
        <Card className={`${isHRManager ? '' : 'col-span-2'} border-zinc-200 dark:border-zinc-800`}>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              Pending Approvals
            </CardTitle>
            <Link to="/hr/approvals">
              <Button variant="ghost" size="sm">
                View All <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {pendingApprovals.length > 0 ? (
              <div className="space-y-3">
                {pendingApprovals.map((approval, idx) => (
                  <div 
                    key={approval.id || idx} 
                    className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">
                        {approval.type?.replace('_', ' ')}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {approval.requester_name || 'Unknown'}
                      </p>
                    </div>
                    <Badge variant="outline">{approval.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-zinc-500">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                <p>No pending approvals</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Department Distribution */}
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardHeader>
            <CardTitle className="text-base">Department Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {employees.by_department && Object.keys(employees.by_department).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(employees.by_department).map(([dept, count]) => (
                  <div key={dept}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-zinc-600 dark:text-zinc-400">{dept}</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-100">{count}</span>
                    </div>
                    <Progress 
                      value={(count / (employees.total || 1)) * 100} 
                      className="h-2"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-zinc-500">
                <Users className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                <p>No department data</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            <Link to="/hr/onboarding">
              <Button variant="outline" className="w-full h-20 flex-col gap-2">
                <UserPlus className="w-5 h-5" />
                <span className="text-xs">New Employee</span>
              </Button>
            </Link>
            <Link to="/hr/leave-management">
              <Button variant="outline" className="w-full h-20 flex-col gap-2">
                <Calendar className="w-5 h-5" />
                <span className="text-xs">Manage Leaves</span>
              </Button>
            </Link>
            <Link to="/hr/attendance">
              <Button variant="outline" className="w-full h-20 flex-col gap-2">
                <Clock className="w-5 h-5" />
                <span className="text-xs">Attendance</span>
              </Button>
            </Link>
            <Link to="/hr/payroll">
              <Button variant="outline" className="w-full h-20 flex-col gap-2">
                <Wallet className="w-5 h-5" />
                <span className="text-xs">Run Payroll</span>
              </Button>
            </Link>
            {isHRManager && (
              <Link to="/hr/team-workload">
                <Button variant="outline" className="w-full h-20 flex-col gap-2">
                  <Briefcase className="w-5 h-5" />
                  <span className="text-xs">Team Workload</span>
                </Button>
              </Link>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HRPortalDashboard;
