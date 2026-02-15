import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { 
  ArrowRight, Search, FileText, Clock, CheckCircle, 
  AlertCircle, Loader2, Eye, BarChart3, Filter,
  Building2, Calendar, Users, ListTodo, Send, Ban
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_CONFIG = {
  pending_kickoff: { label: 'Pending Kickoff', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  active: { label: 'Active', color: 'bg-blue-100 text-blue-700', icon: BarChart3 },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  on_hold: { label: 'On Hold', color: 'bg-orange-100 text-orange-700', icon: Ban },
};

const ConsultingSOWList = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [sowList, setSowList] = useState([]);
  const [leads, setLeads] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [sowRes, leadsRes] = await Promise.all([
        axios.get(`${API}/enhanced-sow/list?role=consulting`).catch(() => ({ data: [] })),
        axios.get(`${API}/leads`)
      ]);
      
      // Filter to only show handed-over SOWs for consulting
      const handedOverSOWs = (sowRes.data || []).filter(sow => sow.sales_handover_complete);
      setSowList(handedOverSOWs);
      setLeads(leadsRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load project list');
    } finally {
      setLoading(false);
    }
  };

  // Get lead info for a SOW
  const getLeadInfo = (sow) => {
    return leads.find(l => l.id === sow.lead_id);
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
    <div data-testid="consulting-sow-list-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          My Projects
        </h1>
        <p className="text-zinc-500">
          Manage and track all consulting projects and scopes
        </p>
      </div>

      {/* Stats */}
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

      {/* Project List */}
      {filteredSOWs.length > 0 ? (
        <div className="space-y-3">
          {filteredSOWs.map(sow => {
            const lead = getLeadInfo(sow);
            const status = getProjectStatus(sow);
            const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending_kickoff;
            const progress = getProgress(sow);
            const scopeCounts = getScopeCounts(sow);
            
            return (
              <Card 
                key={sow.id} 
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
                data-testid={`project-card-${sow.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      <div className="w-12 h-12 rounded-sm bg-zinc-100 flex items-center justify-center">
                        <div className="relative w-10 h-10">
                          <svg className="w-10 h-10 -rotate-90">
                            <circle
                              cx="20"
                              cy="20"
                              r="16"
                              fill="none"
                              stroke="#e4e4e7"
                              strokeWidth="4"
                            />
                            <circle
                              cx="20"
                              cy="20"
                              r="16"
                              fill="none"
                              stroke={status === 'completed' ? '#10b981' : '#3b82f6'}
                              strokeWidth="4"
                              strokeDasharray={`${progress} 100`}
                              strokeLinecap="round"
                            />
                          </svg>
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-zinc-700">
                            {progress}%
                          </span>
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-zinc-900">
                            {lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Client'}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                            {statusConfig.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-zinc-500">
                          {lead?.company && (
                            <span className="flex items-center gap-1">
                              <Building2 className="w-3.5 h-3.5" />
                              {lead.company}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <ListTodo className="w-3.5 h-3.5" />
                            {scopeCounts.completed}/{scopeCounts.total} scopes
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {sow.sales_handover_at 
                              ? format(new Date(sow.sales_handover_at), 'MMM d, yyyy') 
                              : 'N/A'}
                          </span>
                        </div>
                        {/* Mini scope status */}
                        <div className="flex items-center gap-2 mt-2">
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
                          {scopeCounts.na > 0 && (
                            <span className="text-xs px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded-sm">
                              {scopeCounts.na} N/A
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => navigate(`/sales-funnel/sow-review/${sow.pricing_plan_id}`)}
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        data-testid={`view-scopes-${sow.id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View Scopes
                      </Button>
                      <Button
                        onClick={() => navigate(`/consulting/project-tasks/${sow.id}`)}
                        size="sm"
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                        data-testid={`manage-tasks-${sow.id}`}
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
      ) : (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No Projects Found</h3>
            <p className="text-zinc-500">
              {searchQuery || statusFilter !== 'all' 
                ? 'No projects match your filters' 
                : 'No projects have been handed over yet'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ConsultingSOWList;
