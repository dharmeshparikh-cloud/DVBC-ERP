import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Briefcase, Calendar, TrendingUp, Clock, CheckCircle, Target, Users, LogIn } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../utils/currency';
import QuickCheckInModal from '../components/QuickCheckInModal';

const ConsultantDashboard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Quick Check-in state
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  const [attendanceStatus, setAttendanceStatus] = useState(null);

  useEffect(() => {
    fetchData();
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

  const fetchData = async () => {
    try {
      const [statsRes, projectsRes] = await Promise.all([
        axios.get(`${API}/consultant/dashboard-stats`),
        axios.get(`${API}/consultant/my-projects`)
      ]);
      setStats(statsRes.data);
      setProjects(projectsRes.data);
    } catch (error) {
      toast.error('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      active: 'bg-emerald-50 text-emerald-700',
      completed: 'bg-blue-50 text-blue-700',
      on_hold: 'bg-yellow-50 text-yellow-700',
      cancelled: 'bg-red-50 text-red-700'
    };
    return colors[status] || colors.active;
  };

  const getBandwidthColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div data-testid="consultant-dashboard">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          My Dashboard
        </h1>
        <p className="text-zinc-500">Welcome back, {user?.full_name}</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Active Projects</div>
              <Briefcase className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <div className="text-3xl font-semibold text-zinc-950">{stats?.active_projects || 0}</div>
            <div className="text-xs text-zinc-500 mt-1">
              of {stats?.max_projects || 8} max capacity
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings Completed</div>
              <CheckCircle className="w-5 h-5 text-emerald-500" strokeWidth={1.5} />
            </div>
            <div className="text-3xl font-semibold text-zinc-950">
              {stats?.total_meetings_completed || 0}
            </div>
            <div className="text-xs text-zinc-500 mt-1">
              of {stats?.total_meetings_committed || 0} committed
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings Pending</div>
              <Clock className="w-5 h-5 text-yellow-500" strokeWidth={1.5} />
            </div>
            <div className="text-3xl font-semibold text-yellow-600">
              {stats?.meetings_pending || 0}
            </div>
            <div className="text-xs text-zinc-500 mt-1">to be delivered</div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Project Value</div>
              <TrendingUp className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <div className="text-3xl font-semibold text-zinc-950">
              {formatINR(stats?.total_project_value || 0, false)}
            </div>
            <div className="text-xs text-zinc-500 mt-1">across all projects</div>
          </CardContent>
        </Card>
      </div>

      {/* Bandwidth Indicator */}
      <Card className="border-zinc-200 shadow-none rounded-sm mb-8">
        <CardContent className="py-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-zinc-950">Capacity Utilization</div>
            <div className="text-sm text-zinc-500">
              {stats?.total_projects || 0} / {stats?.max_projects || 8} projects
            </div>
          </div>
          <div className="h-3 bg-zinc-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${getBandwidthColor(stats?.bandwidth_percentage || 0)} transition-all`}
              style={{ width: `${stats?.bandwidth_percentage || 0}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-zinc-500">
            <span>{stats?.bandwidth_percentage || 0}% utilized</span>
            <span>{stats?.available_slots || 0} slots available</span>
          </div>
        </CardContent>
      </Card>

      {/* Projects List */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
            My Projects
          </CardTitle>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <Briefcase className="w-12 h-12 text-zinc-300 mx-auto mb-4" strokeWidth={1} />
              <p className="text-zinc-500">No projects assigned yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {projects.map((item) => (
                <div
                  key={item.assignment.id}
                  className="p-4 border border-zinc-200 rounded-sm hover:border-zinc-300 transition-colors"
                  data-testid={`project-card-${item.project.id}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-medium text-zinc-950">{item.project.name}</h3>
                      <p className="text-sm text-zinc-500">{item.project.client_name}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusColor(item.project.status)}`}>
                      {item.project.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Role</div>
                      <div className="font-medium text-zinc-950 capitalize">
                        {item.assignment.role_in_project?.replace('_', ' ') || 'Consultant'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Assigned</div>
                      <div className="font-medium text-zinc-950">
                        {new Date(item.assignment.assigned_date).toLocaleDateString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</div>
                      <div className="font-medium text-zinc-950">
                        {item.assignment.meetings_completed || 0} / {item.assignment.meetings_committed || 0}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Project Value</div>
                      <div className="font-medium text-zinc-950">
                        {formatINR(item.project.project_value || 0, false)}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-zinc-500 mb-1">
                      <span>Meetings Progress</span>
                      <span>
                        {item.assignment.meetings_committed > 0
                          ? Math.round((item.assignment.meetings_completed / item.assignment.meetings_committed) * 100)
                          : 0}%
                      </span>
                    </div>
                    <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all"
                        style={{
                          width: `${item.assignment.meetings_committed > 0
                            ? Math.min(100, (item.assignment.meetings_completed / item.assignment.meetings_committed) * 100)
                            : 0}%`
                        }}
                      />
                    </div>
                  </div>

                  {item.client && (
                    <div className="mt-3 pt-3 border-t border-zinc-100">
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <Users className="w-3 h-3" strokeWidth={1.5} />
                        <span>Contact: {item.client.first_name} {item.client.last_name}</span>
                        {item.client.email && <span>• {item.client.email}</span>}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ConsultantDashboard;
