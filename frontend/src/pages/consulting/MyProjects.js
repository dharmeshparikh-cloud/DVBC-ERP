import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { 
  Search, FileText, Clock, CheckCircle, AlertCircle, Loader2, Eye, 
  BarChart3, Filter, Building2, Calendar, Users, ListTodo, ArrowRight,
  DollarSign, UserCheck, Briefcase, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import ViewToggle from '../../components/ViewToggle';
import ConsultingStageNav from '../../components/ConsultingStageNav';
import { sanitizeDisplayText } from '../../utils/sanitize';

const STATUS_CONFIG = {
  pending_kickoff: { label: 'Pending Kickoff', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  active: { label: 'Active', color: 'bg-blue-100 text-blue-700', icon: BarChart3 },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  on_hold: { label: 'On Hold', color: 'bg-orange-100 text-orange-700', icon: AlertCircle },
};

const PAYMENT_FREQUENCY_LABELS = {
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
  'bi-annual': 'Bi-Annual',
  'one-time': 'One-Time'
};

const MyProjects = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [sowList, setSowList] = useState([]);
  const [leads, setLeads] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState('card');

  // Role-based access
  const isAdmin = user?.role === 'admin';
  const isManager = user?.role === 'manager' || user?.role === 'project_manager';
  const isConsultant = user?.role?.includes('consultant');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [projectsRes, sowRes, leadsRes, employeesRes] = await Promise.all([
        axios.get(`${API}/projects`).catch(() => ({ data: [] })),
        axios.get(`${API}/enhanced-sow/list?role=consulting`).catch(() => ({ data: [] })),
        axios.get(`${API}/leads`).catch(() => ({ data: [] })),
        axios.get(`${API}/employees`).catch(() => ({ data: [] }))
      ]);
      
      // Filter SOWs to only show handed-over ones
      const handedOverSOWs = (sowRes.data || []).filter(sow => sow.sales_handover_complete);
      
      // Filter projects based on role
      let filteredProjects = projectsRes.data || [];
      if (isConsultant && !isAdmin && !isManager) {
        // Consultants only see their assigned projects
        filteredProjects = filteredProjects.filter(p => 
          p.assigned_consultants?.some(c => c.user_id === user?.id)
        );
      }
      
      setProjects(filteredProjects);
      setSowList(handedOverSOWs);
      setLeads(leadsRes.data || []);
      setEmployees(employeesRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  // Get lead info for a SOW
  const getLeadInfo = (sow) => {
    return leads.find(l => l.id === sow.lead_id);
  };

  // Get project for a SOW
  const getProjectForSOW = (sow) => {
    return projects.find(p => p.sow_id === sow.id || p.pricing_plan_id === sow.pricing_plan_id);
  };

  // Get assigned consultants for a project
  const getAssignedConsultants = (project) => {
    if (!project?.assigned_consultants) return [];
    return project.assigned_consultants.map(ac => {
      const emp = employees.find(e => e.user_id === ac.user_id);
      return {
        ...ac,
        name: emp ? `${emp.first_name} ${emp.last_name}` : ac.name || 'Unknown'
      };
    });
  };

  // Calculate project status and progress
  const getProjectStatus = (sow) => {
    if (!sow.consulting_kickoff_complete) return 'pending_kickoff';
    
    const scopes = sow.scopes || [];
    const completed = scopes.filter(s => s.status === 'completed' || s.status === 'not_applicable').length;
    const total = scopes.length;
    
    if (total > 0 && completed === total) return 'completed';
    return 'active';
  };

  // Calculate progress percentage
  const getProgress = (sow) => {
    const scopes = sow.scopes || [];
    if (scopes.length === 0) return 0;
    
    const totalProgress = scopes.reduce((sum, s) => sum + (s.progress_percentage || 0), 0);
    return Math.round(totalProgress / scopes.length);
  };

  // Get scope counts by status
  const getScopeCounts = (sow) => {
    const scopes = sow.scopes || [];
    return {
      total: scopes.length,
      notStarted: scopes.filter(s => s.status === 'not_started').length,
      inProgress: scopes.filter(s => s.status === 'in_progress').length,
      completed: scopes.filter(s => s.status === 'completed').length,
      na: scopes.filter(s => s.status === 'not_applicable').length,
    };
  };

  // Filter SOWs
  const filteredSOWs = sowList.filter(sow => {
    const lead = getLeadInfo(sow);
    const status = getProjectStatus(sow);
    
    // Search filter
    const searchLower = searchQuery.toLowerCase();
    const matchesSearch = !searchQuery || 
      lead?.company?.toLowerCase().includes(searchLower) ||
      lead?.first_name?.toLowerCase().includes(searchLower) ||
      lead?.last_name?.toLowerCase().includes(searchLower);
    
    // Status filter
    const matchesStatus = statusFilter === 'all' || status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Stats
  const stats = {
    total: sowList.length,
    pendingKickoff: sowList.filter(s => getProjectStatus(s) === 'pending_kickoff').length,
    active: sowList.filter(s => getProjectStatus(s) === 'active').length,
    completed: sowList.filter(s => getProjectStatus(s) === 'completed').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div data-testid="my-projects-page">
      {/* Stage Navigation */}
      <ConsultingStageNav 
        currentStage={3} 
        completedStages={[1, 2]}
        showFullNav={true}
        onBack={() => navigate('/kickoff-requests')}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
            My Projects
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {isAdmin ? 'All consulting projects' : 
             isManager ? 'Your team\'s projects' : 
             'Your assigned projects'}
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Projects</div>
            <div className="text-2xl font-semibold text-zinc-950">{stats.total}</div>
          </CardContent>
        </Card>
        <Card className="border-yellow-200 bg-yellow-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-yellow-600 uppercase tracking-wide">Pending Kickoff</div>
            <div className="text-2xl font-semibold text-yellow-700">{stats.pendingKickoff}</div>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-blue-600 uppercase tracking-wide">Active</div>
            <div className="text-2xl font-semibold text-blue-700">{stats.active}</div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-emerald-600 uppercase tracking-wide">Completed</div>
            <div className="text-2xl font-semibold text-emerald-700">{stats.completed}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by client, company..."
            className="pl-10 rounded-sm border-zinc-200"
            data-testid="project-search-input"
          />
        </div>
        <div className="flex items-center gap-3">
          <ViewToggle viewMode={viewMode} onChange={setViewMode} />
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-zinc-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
              data-testid="status-filter"
            >
              <option value="all">All Status</option>
              <option value="pending_kickoff">Pending Kickoff</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Project List */}
      {filteredSOWs.length > 0 ? (
        viewMode === 'list' ? (
          /* List View */
          <div className="border border-zinc-200 rounded-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Project</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Company</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Team</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Scopes</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Progress</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Payment</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {filteredSOWs.map(sow => {
                  const lead = getLeadInfo(sow);
                  const project = getProjectForSOW(sow);
                  const status = getProjectStatus(sow);
                  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending_kickoff;
                  const progress = getProgress(sow);
                  const scopeCounts = getScopeCounts(sow);
                  const consultants = getAssignedConsultants(project);
                  
                  return (
                    <tr 
                      key={sow.id} 
                      className="hover:bg-zinc-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/consulting/project-tasks/${sow.id}`)}
                      data-testid={`project-row-${sow.id}`}
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium text-zinc-900">
                          {sanitizeDisplayText(lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Client')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {sanitizeDisplayText(lead?.company) || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex -space-x-2">
                          {consultants.slice(0, 3).map((c, i) => (
                            <div 
                              key={i}
                              className="w-6 h-6 rounded-full bg-zinc-200 border-2 border-white flex items-center justify-center text-[10px] font-medium"
                              title={c.name}
                            >
                              {c.name?.charAt(0)}
                            </div>
                          ))}
                          {consultants.length > 3 && (
                            <div className="w-6 h-6 rounded-full bg-zinc-300 border-2 border-white flex items-center justify-center text-[10px] font-medium">
                              +{consultants.length - 3}
                            </div>
                          )}
                          {consultants.length === 0 && (
                            <span className="text-xs text-zinc-400">Unassigned</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {scopeCounts.completed}/{scopeCounts.total}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-zinc-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${status === 'completed' ? 'bg-emerald-500' : 'bg-blue-500'}`}
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-zinc-500">{progress}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">
                        {PAYMENT_FREQUENCY_LABELS[sow.payment_frequency] || sow.payment_frequency || 'Monthly'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                          {statusConfig.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1">
                          <Button
                            onClick={() => navigate(`/sales-funnel/sow-review/${sow.pricing_plan_id}`)}
                            variant="ghost"
                            size="sm"
                            className="h-8"
                            title="View SOW"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            onClick={() => navigate(`/consulting/project-tasks/${sow.id}`)}
                            variant="ghost"
                            size="sm"
                            className="h-8"
                            title="Manage Tasks"
                          >
                            <ListTodo className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          /* Card View */
          <div className="space-y-4">
            {filteredSOWs.map(sow => {
              const lead = getLeadInfo(sow);
              const project = getProjectForSOW(sow);
              const status = getProjectStatus(sow);
              const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending_kickoff;
              const progress = getProgress(sow);
              const scopeCounts = getScopeCounts(sow);
              const consultants = getAssignedConsultants(project);
              
              return (
                <Card 
                  key={sow.id} 
                  className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                  onClick={() => navigate(`/consulting/project-tasks/${sow.id}`)}
                  data-testid={`project-card-${sow.id}`}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      {/* Left Section - Progress Ring & Project Info */}
                      <div className="flex items-start gap-4 flex-1">
                        {/* Progress Ring */}
                        <div className="w-14 h-14 rounded-sm bg-zinc-50 flex items-center justify-center flex-shrink-0">
                          <div className="relative w-12 h-12">
                            <svg className="w-12 h-12 -rotate-90">
                              <circle cx="24" cy="24" r="20" fill="none" stroke="#e4e4e7" strokeWidth="4" />
                              <circle
                                cx="24" cy="24" r="20" fill="none"
                                stroke={status === 'completed' ? '#10b981' : '#3b82f6'}
                                strokeWidth="4"
                                strokeDasharray={`${progress * 1.256} 125.6`}
                                strokeLinecap="round"
                              />
                            </svg>
                            <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-zinc-700">
                              {progress}%
                            </span>
                          </div>
                        </div>

                        {/* Project Details */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-zinc-900 truncate">
                              {sanitizeDisplayText(lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Client')}
                            </h3>
                            <span className={`text-xs px-2 py-0.5 rounded-sm flex-shrink-0 ${statusConfig.color}`}>
                              {statusConfig.label}
                            </span>
                          </div>

                          {/* Company & Key Info */}
                          <div className="flex items-center gap-4 text-sm text-zinc-500 mb-3">
                            {lead?.company && (
                              <span className="flex items-center gap-1">
                                <Building2 className="w-3.5 h-3.5" />
                                {sanitizeDisplayText(lead.company)}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <ListTodo className="w-3.5 h-3.5" />
                              {scopeCounts.completed}/{scopeCounts.total} scopes
                            </span>
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5" />
                              {sow.project_tenure_months || 12} months
                            </span>
                          </div>

                          {/* Bottom Row - Team & Payments */}
                          <div className="flex items-center justify-between">
                            {/* Assigned Team */}
                            <div className="flex items-center gap-2">
                              <Users className="w-3.5 h-3.5 text-zinc-400" />
                              <div className="flex -space-x-2">
                                {consultants.slice(0, 4).map((c, i) => (
                                  <div 
                                    key={i}
                                    className="w-6 h-6 rounded-full bg-zinc-200 border-2 border-white flex items-center justify-center text-[10px] font-medium"
                                    title={c.name}
                                  >
                                    {c.name?.charAt(0)}
                                  </div>
                                ))}
                                {consultants.length > 4 && (
                                  <div className="w-6 h-6 rounded-full bg-zinc-300 border-2 border-white flex items-center justify-center text-[10px] font-medium">
                                    +{consultants.length - 4}
                                  </div>
                                )}
                              </div>
                              {consultants.length === 0 && (
                                <span className="text-xs text-zinc-400">No team assigned</span>
                              )}
                            </div>

                            {/* Payment Info */}
                            <div className="flex items-center gap-2 text-sm text-zinc-500">
                              <DollarSign className="w-3.5 h-3.5" />
                              <span>{PAYMENT_FREQUENCY_LABELS[sow.payment_frequency] || 'Monthly'}</span>
                              {sow.total_meetings && (
                                <>
                                  <span className="text-zinc-300">•</span>
                                  <span>{sow.total_meetings} meetings</span>
                                </>
                              )}
                            </div>
                          </div>

                          {/* Scope Status Pills */}
                          <div className="flex items-center gap-2 mt-3">
                            {scopeCounts.notStarted > 0 && (
                              <span className="text-xs px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm">
                                {scopeCounts.notStarted} not started
                              </span>
                            )}
                            {scopeCounts.inProgress > 0 && (
                              <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded-sm">
                                {scopeCounts.inProgress} in progress
                              </span>
                            )}
                            {scopeCounts.completed > 0 && (
                              <span className="text-xs px-1.5 py-0.5 bg-emerald-100 text-emerald-600 rounded-sm">
                                {scopeCounts.completed} completed
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right Section - Actions */}
                      <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          onClick={() => navigate(`/sales-funnel/sow-review/${sow.pricing_plan_id}`)}
                          variant="outline"
                          size="sm"
                          className="rounded-sm"
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          View SOW
                        </Button>
                        <Button
                          onClick={() => navigate(`/consulting/project-tasks/${sow.id}`)}
                          size="sm"
                          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                        >
                          <ListTodo className="w-4 h-4 mr-1" />
                          Tasks
                          <ArrowRight className="w-4 h-4 ml-1" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      ) : (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No Projects Found</h3>
            <p className="text-zinc-500">
              {searchQuery || statusFilter !== 'all' 
                ? 'No projects match your filters' 
                : 'No projects have been assigned to you yet'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default MyProjects;
