import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { 
  Briefcase, Users, Calendar, CheckCircle, Clock, 
  AlertTriangle, TrendingUp, ArrowRight, Inbox, BarChart3, LogIn
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import QuickCheckInModal from '../components/QuickCheckInModal';

const ConsultingDashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
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
      const response = await fetch(`${API}/stats/consulting-dashboard`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch consulting stats:', error);
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

  const projects = stats?.projects || {};
  const meetings = stats?.meetings || {};
  const efficiency = stats?.efficiency_score || 0;

  const getEfficiencyColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getEfficiencyBg = (score) => {
    if (score >= 80) return 'bg-green-100';
    if (score >= 60) return 'bg-amber-100';
    return 'bg-red-100';
  };

  return (
    <div className="space-y-6" data-testid="consulting-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Consulting Dashboard</h1>
          <p className="text-sm text-zinc-500">Track project delivery and team efficiency</p>
        </div>
        <div className={`px-4 py-2 rounded-lg ${getEfficiencyBg(efficiency)}`}>
          <span className={`text-2xl font-bold ${getEfficiencyColor(efficiency)}`}>
            {efficiency}%
          </span>
          <span className="text-sm text-zinc-600 ml-2">Efficiency Score</span>
        </div>
      </div>

      {/* Quick Attendance Card - Light Blue to Dark Blue Gradient */}
      <Card 
        className="cursor-pointer transition-all hover:shadow-lg bg-gradient-to-r from-sky-400 via-blue-500 to-blue-700 border-blue-500"
        onClick={() => setShowQuickCheckIn(true)}
        data-testid="consulting-quick-attendance-card"
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
            <Button className="bg-white text-blue-600 hover:bg-white/90 h-11 px-6 font-semibold">
              <LogIn className="w-5 h-5 mr-2" /> Check In
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Quick Check-in Modal */}
      <QuickCheckInModal 
        isOpen={showQuickCheckIn} 
        onClose={() => { setShowQuickCheckIn(false); fetchAttendanceStatus(); }} 
        user={user} 
      />

      {/* Incoming Kickoffs Alert - For Project Managers */}
      {stats?.incoming_kickoffs > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <Link to="/kickoff-requests" className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                  <Inbox className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-semibold text-orange-800">Incoming Kickoff Requests</p>
                  <p className="text-sm text-orange-600">New projects waiting for your acceptance</p>
                </div>
              </div>
              <Badge className="bg-orange-600 text-white text-lg px-4 py-1">
                {stats?.incoming_kickoffs}
              </Badge>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Project Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card 
          className="border-zinc-200 cursor-pointer hover:shadow-md hover:border-blue-300 transition-all"
          onClick={() => navigate('/projects')}
          data-testid="active-projects-card"
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Active Projects</p>
                <p className="text-3xl font-bold text-zinc-900 mt-1">{projects.active || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Briefcase className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-blue-600 mt-2 flex items-center gap-1">
              View projects <ArrowRight className="w-3 h-3" />
            </p>
          </CardContent>
        </Card>

        <Card 
          className="border-zinc-200 cursor-pointer hover:shadow-md hover:border-green-300 transition-all"
          onClick={() => navigate('/projects?status=completed')}
          data-testid="completed-projects-card"
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Completed</p>
                <p className="text-3xl font-bold text-green-600 mt-1">{projects.completed || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
              View completed <ArrowRight className="w-3 h-3" />
            </p>
          </CardContent>
        </Card>

        <Card 
          className="border-zinc-200 cursor-pointer hover:shadow-md hover:border-amber-300 transition-all"
          onClick={() => navigate('/projects?status=on_hold')}
          data-testid="onhold-projects-card"
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">On Hold</p>
                <p className="text-3xl font-bold text-amber-600 mt-1">{projects.on_hold || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600" />
              </div>
            </div>
            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
              View on hold <ArrowRight className="w-3 h-3" />
            </p>
          </CardContent>
        </Card>

        <Card 
          className="border-zinc-200 cursor-pointer hover:shadow-md hover:border-red-300 transition-all"
          onClick={() => navigate('/projects?status=at_risk')}
          data-testid="atrisk-projects-card"
        >
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">At Risk</p>
                <p className="text-3xl font-bold text-red-600 mt-1">{projects.at_risk || 0}</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
            <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
              View at risk <ArrowRight className="w-3 h-3" />
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Meetings Delivery */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Meeting Delivery Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-500">Delivered vs Committed</span>
              <span className="font-medium">
                {meetings.delivered || 0} / {meetings.committed || 0}
              </span>
            </div>
            <Progress 
              value={meetings.committed > 0 ? (meetings.delivered / meetings.committed) * 100 : 0} 
              className="h-3"
            />
            <div className="grid grid-cols-3 gap-4 pt-2">
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{meetings.delivered || 0}</p>
                <p className="text-xs text-zinc-500">Delivered</p>
              </div>
              <div className="text-center p-3 bg-amber-50 rounded-lg">
                <p className="text-2xl font-bold text-amber-600">{meetings.pending || 0}</p>
                <p className="text-xs text-zinc-500">Pending</p>
              </div>
              <div className="text-center p-3 bg-zinc-100 rounded-lg">
                <p className="text-2xl font-bold text-zinc-700">{meetings.committed || 0}</p>
                <p className="text-xs text-zinc-500">Committed</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Consultant Workload */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4" />
            Team Workload
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
            <div>
              <p className="text-sm text-zinc-500">Average Projects per Consultant</p>
              <p className="text-3xl font-bold text-zinc-900">{stats?.consultant_workload?.average || 0}</p>
            </div>
            <div className="w-24 h-24">
              <div className="relative w-full h-full flex items-center justify-center">
                <svg className="w-full h-full" viewBox="0 0 100 100">
                  <circle
                    cx="50" cy="50" r="40"
                    fill="none"
                    stroke="#e4e4e7"
                    strokeWidth="8"
                  />
                  <circle
                    cx="50" cy="50" r="40"
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="8"
                    strokeDasharray={`${(stats?.consultant_workload?.average || 0) / 8 * 251.2} 251.2`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <span className="absolute text-sm font-medium">/8 max</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'View Projects', href: '/projects', icon: Briefcase, color: 'bg-blue-600' },
          { label: 'Schedule Meeting', href: '/meetings', icon: Calendar, color: 'bg-purple-600' },
          { label: 'Gantt Chart', href: '/gantt-chart', icon: BarChart3, color: 'bg-indigo-600' },
          { label: 'Performance', href: '/performance', icon: TrendingUp, color: 'bg-green-600' },
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

export default ConsultingDashboard;
