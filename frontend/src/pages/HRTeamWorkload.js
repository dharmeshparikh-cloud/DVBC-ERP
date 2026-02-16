import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Input } from '../components/ui/input';
import { 
  Users, Briefcase, Search, Calendar, Clock, 
  TrendingUp, AlertCircle, CheckCircle, User,
  Building2, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const HRTeamWorkload = () => {
  const { user } = useContext(AuthContext);
  const [consultants, setConsultants] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  // Allow Admin and HR Manager access
  const hasAccess = ['admin', 'hr_manager'].includes(user?.role);

  useEffect(() => {
    if (!hasAccess) {
      toast.error('Access denied. This page is for Admin and HR Managers only.');
      return;
    }
    fetchTeamData();
  }, [user]);

  const fetchTeamData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // Fetch consultants with their project assignments
      const consultantsRes = await fetch(`${API}/consultants`, { headers });
      if (consultantsRes.ok) {
        const data = await consultantsRes.json();
        setConsultants(data);
      }

      // Fetch active projects
      const projectsRes = await fetch(`${API}/projects?status=active`, { headers });
      if (projectsRes.ok) {
        const data = await projectsRes.json();
        setProjects(data);
      }
    } catch (error) {
      console.error('Failed to fetch team data:', error);
      toast.error('Failed to load team workload data');
    } finally {
      setLoading(false);
    }
  };

  const getBandwidthColor = (percentage) => {
    if (percentage >= 90) return 'text-red-600 bg-red-100';
    if (percentage >= 70) return 'text-amber-600 bg-amber-100';
    return 'text-emerald-600 bg-emerald-100';
  };

  const getBandwidthProgressColor = (percentage) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  const filteredConsultants = consultants.filter(c => {
    const matchesSearch = c.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         c.email?.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterStatus === 'all') return matchesSearch;
    if (filterStatus === 'available') return matchesSearch && (c.bandwidth_percentage || 0) < 70;
    if (filterStatus === 'busy') return matchesSearch && (c.bandwidth_percentage || 0) >= 70 && (c.bandwidth_percentage || 0) < 90;
    if (filterStatus === 'overloaded') return matchesSearch && (c.bandwidth_percentage || 0) >= 90;
    return matchesSearch;
  });

  // Calculate summary stats
  const totalConsultants = consultants.length;
  const availableCount = consultants.filter(c => (c.bandwidth_percentage || 0) < 70).length;
  const busyCount = consultants.filter(c => (c.bandwidth_percentage || 0) >= 70 && (c.bandwidth_percentage || 0) < 90).length;
  const overloadedCount = consultants.filter(c => (c.bandwidth_percentage || 0) >= 90).length;
  const avgUtilization = totalConsultants > 0 
    ? Math.round(consultants.reduce((sum, c) => sum + (c.bandwidth_percentage || 0), 0) / totalConsultants)
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (user?.role !== 'hr_manager') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Access Denied</h2>
          <p className="text-zinc-500 mt-2">This page is only accessible to HR Managers</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="hr-team-workload">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Team Workload</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Monitor consultant assignments and availability (Read-Only View)
          </p>
        </div>
        <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
          {avgUtilization}% Avg Utilization
        </Badge>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Total Consultants</p>
                <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {totalConsultants}
                </p>
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
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Available</p>
                <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                  {availableCount}
                </p>
                <p className="text-xs text-zinc-500 mt-1">&lt;70% utilized</p>
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
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Busy</p>
                <p className="text-3xl font-bold text-amber-600 dark:text-amber-400 mt-1">
                  {busyCount}
                </p>
                <p className="text-xs text-zinc-500 mt-1">70-90% utilized</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Clock className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Overloaded</p>
                <p className="text-3xl font-bold text-red-600 dark:text-red-400 mt-1">
                  {overloadedCount}
                </p>
                <p className="text-xs text-zinc-500 mt-1">&gt;90% utilized</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="Search consultants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="workload-search"
              />
            </div>
            <div className="flex gap-2">
              {['all', 'available', 'busy', 'overloaded'].map((status) => (
                <Button
                  key={status}
                  variant={filterStatus === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterStatus(status)}
                  className={filterStatus === status ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Consultant List */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-5 h-5" />
            Consultant Workload ({filteredConsultants.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredConsultants.length > 0 ? (
            <div className="space-y-4">
              {filteredConsultants.map((consultant) => {
                const bandwidth = consultant.bandwidth_percentage || 0;
                const projectCount = consultant.active_projects?.length || consultant.projects_count || 0;
                
                return (
                  <div
                    key={consultant.id}
                    className="flex items-center gap-4 p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg"
                    data-testid={`consultant-row-${consultant.id}`}
                  >
                    {/* Avatar */}
                    <div className="w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center">
                      <User className="w-6 h-6 text-zinc-500" />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-zinc-900 dark:text-zinc-100">
                          {consultant.full_name}
                        </p>
                        <Badge variant="outline" className="text-xs capitalize">
                          {consultant.role?.replace('_', ' ') || 'Consultant'}
                        </Badge>
                      </div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">
                        {consultant.email}
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Briefcase className="w-3 h-3" />
                          {projectCount} project{projectCount !== 1 ? 's' : ''}
                        </span>
                        {consultant.department && (
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3 h-3" />
                            {consultant.department}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Bandwidth */}
                    <div className="w-48">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-zinc-500">Utilization</span>
                        <span className={`text-sm font-medium px-2 py-0.5 rounded ${getBandwidthColor(bandwidth)}`}>
                          {bandwidth}%
                        </span>
                      </div>
                      <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${getBandwidthProgressColor(bandwidth)} transition-all`}
                          style={{ width: `${Math.min(bandwidth, 100)}%` }}
                        />
                      </div>
                    </div>

                    {/* Status Badge */}
                    <Badge className={
                      bandwidth >= 90 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                      bandwidth >= 70 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                      'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                    }>
                      {bandwidth >= 90 ? 'Overloaded' : bandwidth >= 70 ? 'Busy' : 'Available'}
                    </Badge>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-zinc-500">
              <Users className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
              <p className="text-lg font-medium">No consultants found</p>
              <p className="text-sm mt-1">Try adjusting your search or filter criteria</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Projects Summary */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Briefcase className="w-5 h-5" />
            Active Projects ({projects.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {projects.length > 0 ? (
            <div className="grid grid-cols-2 gap-4">
              {projects.slice(0, 6).map((project) => (
                <div
                  key={project.id}
                  className="flex items-center gap-3 p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg"
                >
                  <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Briefcase className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                      {project.name}
                    </p>
                    <p className="text-xs text-zinc-500 truncate">
                      {project.client_name}
                    </p>
                  </div>
                  <Badge variant="outline" className="capitalize">
                    {project.status || 'active'}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              <Briefcase className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
              <p>No active projects</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Banner */}
      <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
          <div>
            <p className="font-medium text-emerald-800 dark:text-emerald-300">Read-Only View</p>
            <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-1">
              This view shows consultant workload and project assignments for staffing planning purposes.
              Financial data (project values, rates) is not displayed. Contact the Project Manager for assignment changes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HRTeamWorkload;
