import React, { useState, useEffect, useContext, useMemo } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Progress } from '../../components/ui/progress';
import { 
  ArrowLeft, Plus, Check, X, CheckCircle, AlertCircle, Clock,
  FileText, Upload, Download, Eye, Edit2, Save, Send,
  Calendar, BarChart3, Columns3, History, Loader2, XCircle,
  ChevronRight, Paperclip, MessageSquare, Ban
} from 'lucide-react';
import { toast } from 'sonner';
import { format, differenceInDays, addWeeks, startOfWeek } from 'date-fns';

const STATUS_CONFIG = {
  not_started: { label: 'Not Started', color: 'bg-zinc-100 text-zinc-700', icon: Clock },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: BarChart3 },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  not_applicable: { label: 'Not Applicable', color: 'bg-orange-100 text-orange-700', icon: Ban }
};

const REVISION_STATUS_CONFIG = {
  pending_review: { label: 'Pending Review', color: 'bg-yellow-100 text-yellow-700' },
  confirmed: { label: 'Confirmed', color: 'bg-emerald-100 text-emerald-700' },
  revised: { label: 'Revised', color: 'bg-blue-100 text-blue-700' },
  not_applicable: { label: 'Not Applicable', color: 'bg-orange-100 text-orange-700' }
};

const ConsultingScopeView = () => {
  const { pricingPlanId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [sow, setSow] = useState(null);
  const [lead, setLead] = useState(null);
  const [categories, setCategories] = useState([]);
  
  // View mode
  const [viewMode, setViewMode] = useState('list'); // list, kanban, gantt, timeline
  
  // Dialogs
  const [editScopeDialog, setEditScopeDialog] = useState(false);
  const [addScopeDialog, setAddScopeDialog] = useState(false);
  const [attachmentDialog, setAttachmentDialog] = useState(false);
  const [changeLogDialog, setChangeLogDialog] = useState(false);
  const [roadmapSubmitDialog, setRoadmapSubmitDialog] = useState(false);
  
  // Selected scope for editing
  const [selectedScope, setSelectedScope] = useState(null);
  const [scopeEdits, setScopeEdits] = useState({});
  
  // New scope data
  const [newScope, setNewScope] = useState({ name: '', category_id: '', description: '', timeline_weeks: '' });
  
  // Roadmap submit data
  const [roadmapData, setRoadmapData] = useState({ approval_cycle: 'monthly', period_label: '' });
  
  // Role checks
  const consultingRoles = ['consultant', 'lean_consultant', 'lead_consultant', 'senior_consultant', 'principal_consultant', 'subject_matter_expert', 'project_manager'];
  const canAddScopesRoles = ['project_manager', 'consultant', 'principal_consultant', 'admin'];
  
  const isConsultingTeam = consultingRoles.includes(user?.role) || user?.role === 'admin';
  const canAddScopes = canAddScopesRoles.includes(user?.role);

  useEffect(() => {
    fetchData();
  }, [pricingPlanId]);

  const fetchData = async () => {
    try {
      const [sowRes, catsRes] = await Promise.all([
        axios.get(`${API}/enhanced-sow/by-pricing-plan/${pricingPlanId}`, {
          params: { current_user_role: user?.role }
        }),
        axios.get(`${API}/sow-masters/categories`)
      ]);
      
      setSow(sowRes.data);
      setCategories(catsRes.data || []);
      
      // Fetch lead info
      if (sowRes.data?.lead_id) {
        try {
          const leadsRes = await axios.get(`${API}/leads`);
          const leadData = leadsRes.data.find(l => l.id === sowRes.data.lead_id);
          setLead(leadData);
        } catch (err) {
          console.error('Error fetching lead:', err);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load SOW data');
    } finally {
      setLoading(false);
    }
  };

  const openEditDialog = (scope) => {
    setSelectedScope(scope);
    setScopeEdits({
      status: scope.status,
      progress_percentage: scope.progress_percentage || 0,
      days_spent: scope.days_spent || 0,
      meetings_count: scope.meetings_count || 0,
      notes: scope.notes || '',
      revision_status: scope.revision_status,
      revision_reason: scope.revision_reason || '',
      client_consent_for_revision: scope.client_consent_for_revision || false
    });
    setEditScopeDialog(true);
  };

  const saveScope = async () => {
    if (!selectedScope) return;
    
    try {
      await axios.patch(
        `${API}/enhanced-sow/${sow.id}/scopes/${selectedScope.id}`,
        scopeEdits,
        {
          params: {
            current_user_id: user?.id,
            current_user_name: user?.full_name || user?.email,
            current_user_role: user?.role
          }
        }
      );
      
      toast.success('Scope updated successfully');
      setEditScopeDialog(false);
      setSelectedScope(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update scope');
    }
  };

  const addNewScope = async () => {
    if (!newScope.name || !newScope.category_id) {
      toast.error('Please fill in scope name and select a category');
      return;
    }
    
    try {
      await axios.post(
        `${API}/enhanced-sow/${sow.id}/scopes`,
        newScope,
        {
          params: {
            current_user_id: user?.id,
            current_user_name: user?.full_name || user?.email,
            current_user_role: user?.role
          }
        }
      );
      
      toast.success('Scope added successfully');
      setAddScopeDialog(false);
      setNewScope({ name: '', category_id: '', description: '', timeline_weeks: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add scope');
    }
  };

  const submitRoadmap = async () => {
    if (!roadmapData.period_label) {
      toast.error('Please enter the period label');
      return;
    }
    
    try {
      await axios.post(
        `${API}/enhanced-sow/${sow.id}/roadmap/submit`,
        roadmapData,
        {
          params: {
            current_user_id: user?.id,
            current_user_name: user?.full_name || user?.email
          }
        }
      );
      
      toast.success('Roadmap submitted for client approval');
      setRoadmapSubmitDialog(false);
      setRoadmapData({ approval_cycle: 'monthly', period_label: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit roadmap');
    }
  };

  // Computed stats
  const stats = useMemo(() => {
    if (!sow?.scopes) return { total: 0, notStarted: 0, inProgress: 0, completed: 0, notApplicable: 0 };
    
    return {
      total: sow.scopes.length,
      notStarted: sow.scopes.filter(s => s.status === 'not_started').length,
      inProgress: sow.scopes.filter(s => s.status === 'in_progress').length,
      completed: sow.scopes.filter(s => s.status === 'completed').length,
      notApplicable: sow.scopes.filter(s => s.status === 'not_applicable').length
    };
  }, [sow?.scopes]);

  // Group scopes by category for list view
  const scopesByCategory = useMemo(() => {
    if (!sow?.scopes) return [];
    
    const grouped = {};
    sow.scopes.forEach(scope => {
      const catCode = scope.category_code || 'other';
      if (!grouped[catCode]) {
        grouped[catCode] = {
          category_code: catCode,
          category_name: scope.category_name || 'Other',
          scopes: []
        };
      }
      grouped[catCode].scopes.push(scope);
    });
    
    return Object.values(grouped);
  }, [sow?.scopes]);

  // Kanban columns
  const kanbanColumns = useMemo(() => {
    if (!sow?.scopes) return [];
    
    return [
      { id: 'not_started', title: 'Not Started', scopes: sow.scopes.filter(s => s.status === 'not_started') },
      { id: 'in_progress', title: 'In Progress', scopes: sow.scopes.filter(s => s.status === 'in_progress') },
      { id: 'completed', title: 'Completed', scopes: sow.scopes.filter(s => s.status === 'completed') },
      { id: 'not_applicable', title: 'Not Applicable', scopes: sow.scopes.filter(s => s.status === 'not_applicable') }
    ];
  }, [sow?.scopes]);

  // Gantt data
  const ganttData = useMemo(() => {
    if (!sow?.scopes) return { scopes: [], maxWeeks: 12 };
    
    const scopesWithTimeline = sow.scopes.filter(s => s.timeline_weeks);
    const maxWeeks = Math.max(...scopesWithTimeline.map(s => (s.start_week || 1) + (s.timeline_weeks || 1)), 12);
    
    return {
      scopes: scopesWithTimeline.map((s, idx) => ({
        ...s,
        startWeek: idx * 2 + 1, // Stagger for demo
        endWeek: (idx * 2 + 1) + (s.timeline_weeks || 2)
      })),
      maxWeeks
    };
  }, [sow?.scopes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!sow) {
    return (
      <div data-testid="consulting-scope-view-page">
        <Button onClick={() => navigate('/sales-funnel/pricing-plans')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back
        </Button>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <XCircle className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">SOW Not Found</h3>
            <p className="text-zinc-500">No Scope of Work exists for this pricing plan.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div data-testid="consulting-scope-view-page">
      {/* Header */}
      <div className="mb-6">
        <Button onClick={() => navigate('/sales-funnel/pricing-plans')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Pricing Plans
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Project Scope
            </h1>
            <p className="text-zinc-500">
              {lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Project Scope of Work'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {canAddScopes && (
              <Button
                onClick={() => setAddScopeDialog(true)}
                variant="outline"
                className="rounded-sm"
                data-testid="add-scope-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Scope
              </Button>
            )}
            <Button
              onClick={() => setChangeLogDialog(true)}
              variant="outline"
              className="rounded-sm"
            >
              <History className="w-4 h-4 mr-2" />
              Change Log
            </Button>
            <Button
              onClick={() => setRoadmapSubmitDialog(true)}
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              data-testid="submit-roadmap-btn"
            >
              <Send className="w-4 h-4 mr-2" />
              Submit for Approval
            </Button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Scopes</div>
            <div className="text-2xl font-semibold text-zinc-950">{stats.total}</div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 bg-zinc-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Not Started</div>
            <div className="text-2xl font-semibold text-zinc-700">{stats.notStarted}</div>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-blue-600 uppercase tracking-wide">In Progress</div>
            <div className="text-2xl font-semibold text-blue-700">{stats.inProgress}</div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-emerald-600 uppercase tracking-wide">Completed</div>
            <div className="text-2xl font-semibold text-emerald-700">{stats.completed}</div>
          </CardContent>
        </Card>
        <Card className="border-orange-200 bg-orange-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-orange-600 uppercase tracking-wide">N/A</div>
            <div className="text-2xl font-semibold text-orange-700">{stats.notApplicable}</div>
          </CardContent>
        </Card>
      </div>

      {/* View Toggle */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex bg-zinc-100 rounded-sm p-1">
          {[
            { id: 'list', icon: FileText, label: 'List' },
            { id: 'kanban', icon: Columns3, label: 'Kanban' },
            { id: 'gantt', icon: BarChart3, label: 'Gantt' },
            { id: 'timeline', icon: Calendar, label: 'Timeline' }
          ].map(view => (
            <button
              key={view.id}
              onClick={() => setViewMode(view.id)}
              className={`px-3 py-1.5 text-sm rounded-sm transition-colors flex items-center gap-1.5 ${
                viewMode === view.id ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
              }`}
              data-testid={`view-${view.id}-btn`}
            >
              <view.icon className="w-4 h-4" />
              {view.label}
            </button>
          ))}
        </div>
      </div>

      {/* List View */}
      {viewMode === 'list' && (
        <div className="space-y-4">
          {scopesByCategory.map(group => (
            <Card key={group.category_code} className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-2 bg-zinc-50">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-700">
                  {group.category_name} ({group.scopes.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-zinc-100">
                  {group.scopes.map(scope => {
                    const statusConfig = STATUS_CONFIG[scope.status] || STATUS_CONFIG.not_started;
                    const revisionConfig = REVISION_STATUS_CONFIG[scope.revision_status] || REVISION_STATUS_CONFIG.pending_review;
                    const StatusIcon = statusConfig.icon;
                    
                    return (
                      <div 
                        key={scope.id} 
                        className="p-4 hover:bg-zinc-50 transition-colors"
                        data-testid={`scope-item-${scope.id}`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-zinc-900">{scope.name}</span>
                              {scope.source === 'consulting_added' && (
                                <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-sm">
                                  Added by Consulting
                                </span>
                              )}
                            </div>
                            {scope.description && (
                              <p className="text-sm text-zinc-500 mb-2">{scope.description}</p>
                            )}
                            <div className="flex items-center gap-4 text-xs text-zinc-500">
                              <span className={`px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                                {statusConfig.label}
                              </span>
                              <span className={`px-2 py-0.5 rounded-sm ${revisionConfig.color}`}>
                                {revisionConfig.label}
                              </span>
                              {scope.progress_percentage > 0 && (
                                <span className="flex items-center gap-1">
                                  <Progress value={scope.progress_percentage} className="w-16 h-1.5" />
                                  {scope.progress_percentage}%
                                </span>
                              )}
                              {scope.days_spent > 0 && <span>{scope.days_spent} days</span>}
                              {scope.meetings_count > 0 && <span>{scope.meetings_count} meetings</span>}
                              {scope.attachments?.length > 0 && (
                                <span className="flex items-center gap-1 text-blue-600">
                                  <Paperclip className="w-3 h-3" />
                                  {scope.attachments.length}
                                </span>
                              )}
                            </div>
                          </div>
                          <Button
                            onClick={() => openEditDialog(scope)}
                            variant="ghost"
                            size="sm"
                            className="text-zinc-500 hover:text-zinc-900"
                            data-testid={`edit-scope-${scope.id}`}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Kanban View */}
      {viewMode === 'kanban' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {kanbanColumns.map(column => {
            const statusConfig = STATUS_CONFIG[column.id] || STATUS_CONFIG.not_started;
            return (
              <div key={column.id} className="space-y-2">
                <div className={`px-3 py-2 rounded-sm ${statusConfig.color} font-medium text-sm`}>
                  {column.title} ({column.scopes.length})
                </div>
                <div className="space-y-2 min-h-[200px]">
                  {column.scopes.map(scope => (
                    <Card 
                      key={scope.id} 
                      className="border-zinc-200 shadow-none rounded-sm cursor-pointer hover:border-zinc-300"
                      onClick={() => openEditDialog(scope)}
                    >
                      <CardContent className="p-3">
                        <div className="font-medium text-sm text-zinc-900 mb-1">{scope.name}</div>
                        <div className="text-xs text-zinc-500">{scope.category_name}</div>
                        {scope.progress_percentage > 0 && (
                          <Progress value={scope.progress_percentage} className="mt-2 h-1.5" />
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Gantt View */}
      {viewMode === 'gantt' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 overflow-x-auto">
            <div className="min-w-[1000px]">
              {/* Header */}
              <div className="flex border-b border-zinc-200 bg-zinc-50">
                <div className="w-64 px-4 py-2 font-medium text-xs uppercase tracking-wide text-zinc-500 border-r border-zinc-200">
                  Scope
                </div>
                <div className="flex-1 flex">
                  {Array.from({ length: ganttData.maxWeeks }, (_, i) => (
                    <div key={i} className="flex-1 px-1 py-2 text-center text-xs text-zinc-500 border-r border-zinc-100">
                      W{i + 1}
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Rows */}
              {ganttData.scopes.length > 0 ? (
                ganttData.scopes.map(scope => {
                  const statusConfig = STATUS_CONFIG[scope.status] || STATUS_CONFIG.not_started;
                  return (
                    <div key={scope.id} className="flex border-b border-zinc-100 hover:bg-zinc-50">
                      <div className="w-64 px-4 py-3 border-r border-zinc-200">
                        <div className="font-medium text-sm text-zinc-900 truncate">{scope.name}</div>
                        <div className="text-xs text-zinc-500">{scope.category_name}</div>
                      </div>
                      <div className="flex-1 flex relative py-2">
                        {Array.from({ length: ganttData.maxWeeks }, (_, i) => (
                          <div key={i} className="flex-1 border-r border-zinc-50" />
                        ))}
                        <div
                          className={`absolute h-6 rounded-sm top-1/2 -translate-y-1/2 ${
                            scope.status === 'completed' ? 'bg-emerald-500' :
                            scope.status === 'in_progress' ? 'bg-blue-500' :
                            scope.status === 'not_applicable' ? 'bg-orange-400' :
                            'bg-zinc-400'
                          }`}
                          style={{
                            left: `${((scope.startWeek - 1) / ganttData.maxWeeks) * 100}%`,
                            width: `${((scope.endWeek - scope.startWeek + 1) / ganttData.maxWeeks) * 100}%`,
                            minWidth: '30px'
                          }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-zinc-400">
                  No scopes with timeline data. Update scope timelines to see the Gantt chart.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline View */}
      {viewMode === 'timeline' && (
        <div className="space-y-4">
          {scopesByCategory.map(group => (
            <Card key={group.category_code} className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-700">
                  {group.category_name}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative pl-6 border-l-2 border-zinc-200 space-y-4">
                  {group.scopes.map((scope, idx) => {
                    const statusConfig = STATUS_CONFIG[scope.status] || STATUS_CONFIG.not_started;
                    const StatusIcon = statusConfig.icon;
                    
                    return (
                      <div key={scope.id} className="relative">
                        <div className={`absolute -left-[29px] w-4 h-4 rounded-full ${
                          scope.status === 'completed' ? 'bg-emerald-500' :
                          scope.status === 'in_progress' ? 'bg-blue-500' :
                          scope.status === 'not_applicable' ? 'bg-orange-400' :
                          'bg-zinc-300'
                        }`} />
                        <div 
                          className="p-3 bg-zinc-50 rounded-sm hover:bg-zinc-100 cursor-pointer transition-colors"
                          onClick={() => openEditDialog(scope)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium text-zinc-900">{scope.name}</div>
                            <span className={`text-xs px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                              {statusConfig.label}
                            </span>
                          </div>
                          {scope.timeline_weeks && (
                            <div className="text-xs text-zinc-500 mt-1">
                              Duration: {scope.timeline_weeks} weeks
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Scope Dialog */}
      <Dialog open={editScopeDialog} onOpenChange={setEditScopeDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Update Scope
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedScope?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto">
            {/* Status */}
            <div className="space-y-2">
              <Label>Status</Label>
              <select
                value={scopeEdits.status || 'not_started'}
                onChange={(e) => setScopeEdits({ ...scopeEdits, status: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="not_applicable">Not Applicable</option>
              </select>
            </div>
            
            {/* Progress */}
            <div className="space-y-2">
              <Label>Progress (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={scopeEdits.progress_percentage || 0}
                onChange={(e) => setScopeEdits({ ...scopeEdits, progress_percentage: parseInt(e.target.value) || 0 })}
                className="rounded-sm"
              />
            </div>
            
            {/* Days Spent */}
            <div className="space-y-2">
              <Label>Days Spent</Label>
              <Input
                type="number"
                min="0"
                value={scopeEdits.days_spent || 0}
                onChange={(e) => setScopeEdits({ ...scopeEdits, days_spent: parseInt(e.target.value) || 0 })}
                className="rounded-sm"
              />
            </div>
            
            {/* Meetings Count */}
            <div className="space-y-2">
              <Label>Meetings Count</Label>
              <Input
                type="number"
                min="0"
                value={scopeEdits.meetings_count || 0}
                onChange={(e) => setScopeEdits({ ...scopeEdits, meetings_count: parseInt(e.target.value) || 0 })}
                className="rounded-sm"
              />
            </div>
            
            {/* Revision Status */}
            <div className="space-y-2">
              <Label>Scope Review Status</Label>
              <select
                value={scopeEdits.revision_status || 'pending_review'}
                onChange={(e) => setScopeEdits({ ...scopeEdits, revision_status: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="pending_review">Pending Review</option>
                <option value="confirmed">Confirmed (Accurate)</option>
                <option value="revised">Revised (Changed with client consent)</option>
                <option value="not_applicable">Not Applicable</option>
              </select>
            </div>
            
            {/* Revision Reason */}
            {(scopeEdits.revision_status === 'revised' || scopeEdits.revision_status === 'not_applicable') && (
              <div className="space-y-2">
                <Label>Revision Reason *</Label>
                <textarea
                  value={scopeEdits.revision_reason || ''}
                  onChange={(e) => setScopeEdits({ ...scopeEdits, revision_reason: e.target.value })}
                  rows={2}
                  placeholder="Explain why this scope was revised or marked N/A..."
                  className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
                />
              </div>
            )}
            
            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes</Label>
              <textarea
                value={scopeEdits.notes || ''}
                onChange={(e) => setScopeEdits({ ...scopeEdits, notes: e.target.value })}
                rows={3}
                placeholder="Add notes about this scope..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
            </div>
            
            <div className="flex gap-3 pt-2">
              <Button 
                onClick={() => setEditScopeDialog(false)} 
                variant="outline" 
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button 
                onClick={saveScope}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Scope Dialog */}
      <Dialog open={addScopeDialog} onOpenChange={setAddScopeDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Add New Scope
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              This scope will be marked as "Added by Consulting Team"
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Category *</Label>
              <select
                value={newScope.category_id}
                onChange={(e) => setNewScope({ ...newScope, category_id: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="">Select category...</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Scope Name *</Label>
              <Input
                value={newScope.name}
                onChange={(e) => setNewScope({ ...newScope, name: e.target.value })}
                placeholder="Enter scope name..."
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                value={newScope.description}
                onChange={(e) => setNewScope({ ...newScope, description: e.target.value })}
                rows={2}
                placeholder="Brief description..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
            </div>
            <div className="space-y-2">
              <Label>Timeline (weeks)</Label>
              <Input
                type="number"
                min="1"
                value={newScope.timeline_weeks}
                onChange={(e) => setNewScope({ ...newScope, timeline_weeks: e.target.value })}
                placeholder="Estimated weeks..."
                className="rounded-sm"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button 
                onClick={() => setAddScopeDialog(false)} 
                variant="outline" 
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button 
                onClick={addNewScope}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Scope
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Roadmap Submit Dialog */}
      <Dialog open={roadmapSubmitDialog} onOpenChange={setRoadmapSubmitDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Submit Roadmap for Approval
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Request client approval for the current project roadmap
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Approval Cycle</Label>
              <select
                value={roadmapData.approval_cycle}
                onChange={(e) => setRoadmapData({ ...roadmapData, approval_cycle: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Period Label *</Label>
              <Input
                value={roadmapData.period_label}
                onChange={(e) => setRoadmapData({ ...roadmapData, period_label: e.target.value })}
                placeholder="e.g., January 2026, Q1 2026"
                className="rounded-sm"
              />
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-3">
              <div className="text-sm text-blue-700">
                <strong>Note:</strong> Client will receive an email notification requesting approval.
                Upload client consent document after receiving approval.
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <Button 
                onClick={() => setRoadmapSubmitDialog(false)} 
                variant="outline" 
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button 
                onClick={submitRoadmap}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Send className="w-4 h-4 mr-2" />
                Submit for Approval
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Log Dialog */}
      <Dialog open={changeLogDialog} onOpenChange={setChangeLogDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Change Log
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Complete history of all changes made to scopes
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {sow?.scopes?.flatMap(scope => 
              (scope.change_log || []).map(change => ({
                ...change,
                scope_name: scope.name
              }))
            ).sort((a, b) => new Date(b.changed_at) - new Date(a.changed_at)).slice(0, 50).map(change => (
              <div key={change.id} className="p-3 bg-zinc-50 rounded-sm border border-zinc-200">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-medium text-zinc-900 text-sm">{change.scope_name}</div>
                  <div className="text-xs text-zinc-500">
                    {format(new Date(change.changed_at), 'MMM d, yyyy HH:mm')}
                  </div>
                </div>
                <div className="text-xs text-zinc-500">
                  <span className="text-zinc-700">{change.changed_by_name}</span> • {change.change_type?.replace(/_/g, ' ')}
                </div>
                {change.reason && (
                  <div className="text-xs text-zinc-600 mt-1 italic">
                    Reason: {change.reason}
                  </div>
                )}
              </div>
            ))}
            {(!sow?.scopes || sow.scopes.every(s => !s.change_log?.length)) && (
              <div className="text-center py-8 text-zinc-400">
                No changes recorded yet
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsultingScopeView;
