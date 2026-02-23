import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  Users, UserPlus, Calendar, Building2, IndianRupee,
  Clock, AlertCircle, CheckCircle2, Filter, Search,
  RefreshCw, UserMinus, ChevronRight, Eye, History
} from 'lucide-react';

const AllProjects = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [consultants, setConsultants] = useState([]);
  const [filter, setFilter] = useState('all'); // all, needs_assignment, assigned
  const [search, setSearch] = useState('');
  
  // Dialog states
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [assignmentHistory, setAssignmentHistory] = useState([]);
  
  // Form state
  const [formData, setFormData] = useState({
    consultant_id: '',
    role_in_project: 'consultant',
    meetings_committed: 0,
    notes: ''
  });

  useEffect(() => {
    fetchProjects();
    fetchConsultants();
  }, [filter]);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      let url = `${API}/projects/all/for-assignment`;
      if (filter === 'needs_assignment') {
        url += '?needs_assignment=true';
      } else if (filter === 'assigned') {
        url += '?needs_assignment=false';
      }
      
      const response = await axios.get(url);
      setProjects(response.data.projects || []);
    } catch (error) {
      console.error('Error fetching projects:', error);
      toast.error('Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  const fetchConsultants = async () => {
    try {
      const response = await axios.get(`${API}/consultants`);
      setConsultants(response.data || []);
    } catch (error) {
      console.error('Error fetching consultants:', error);
    }
  };

  const handleAssignConsultant = async (e) => {
    e.preventDefault();
    if (!selectedProject || !formData.consultant_id) return;
    
    try {
      await axios.post(`${API}/projects/${selectedProject.id}/assign-consultant`, formData);
      toast.success('Consultant assigned successfully');
      setAssignDialogOpen(false);
      setFormData({ consultant_id: '', role_in_project: 'consultant', meetings_committed: 0, notes: '' });
      fetchProjects();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign consultant');
    }
  };

  const handleUnassignConsultant = async (projectId, consultantId, consultantName) => {
    if (!window.confirm(`Remove ${consultantName} from this project?`)) return;
    
    try {
      await axios.delete(`${API}/projects/${projectId}/unassign-consultant/${consultantId}`);
      toast.success('Consultant removed from project');
      fetchProjects();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove consultant');
    }
  };

  const fetchAssignmentHistory = async (projectId) => {
    try {
      const response = await axios.get(`${API}/projects/${projectId}/assignment-history`);
      setAssignmentHistory(response.data.assignments || []);
    } catch (error) {
      toast.error('Failed to fetch assignment history');
    }
  };

  const openAssignDialog = (project) => {
    setSelectedProject(project);
    setFormData({ consultant_id: '', role_in_project: 'consultant', meetings_committed: 0, notes: '' });
    setAssignDialogOpen(true);
  };

  const openHistoryDialog = async (project) => {
    setSelectedProject(project);
    await fetchAssignmentHistory(project.id);
    setHistoryDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
      completed: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
      on_hold: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
      cancelled: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
    };
    return statusConfig[status?.toLowerCase()] || { bg: 'bg-black/5', text: 'text-black/70', border: 'border-black/10' };
  };

  const filteredProjects = projects.filter(project => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      (project.name || '').toLowerCase().includes(searchLower) ||
      (project.client_name || '').toLowerCase().includes(searchLower) ||
      (project.id || '').toLowerCase().includes(searchLower)
    );
  });

  const needsAssignmentCount = projects.filter(p => !p.has_consultants).length;

  // Get available consultants (not already assigned to selected project)
  const getAvailableConsultants = () => {
    if (!selectedProject) return consultants;
    const assignedIds = (selectedProject.consultant_assignments || [])
      .filter(a => a.is_active)
      .map(a => a.consultant_id);
    return consultants.filter(c => !assignedIds.includes(c.id));
  };

  // Check if user has permission
  const canManage = ['admin', 'principal_consultant', 'senior_consultant'].includes(user?.role);

  if (!canManage) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="p-8 text-center border-black/10">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <p className="text-black/70">Only Principal Consultants can access this page</p>
        </Card>
      </div>
    );
  }

  return (
    <div data-testid="all-projects-page">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-black mb-2">
            All Projects
          </h1>
          <p className="text-black/50">Manage consultant assignments for all projects</p>
        </div>
        
        {/* Stats Banner */}
        <div className="flex items-center gap-4">
          <div className="bg-black/5 px-4 py-2 rounded-lg border border-black/10">
            <p className="text-xs text-black/50">Total Projects</p>
            <p className="text-xl font-bold text-black">{projects.length}</p>
          </div>
          {needsAssignmentCount > 0 && (
            <div className="bg-amber-50 px-4 py-2 rounded-lg border border-amber-200">
              <p className="text-xs text-amber-600">Needs Assignment</p>
              <p className="text-xl font-bold text-amber-700">{needsAssignmentCount}</p>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-black/40" />
          <Input
            placeholder="Search by project name, client, or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 border-black/20 focus:ring-black focus:border-black"
            data-testid="project-search"
          />
        </div>
        
        {/* Filter Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
            className={filter === 'all' ? 'bg-black text-white' : 'border-black/20'}
            data-testid="filter-all"
          >
            All
          </Button>
          <Button
            variant={filter === 'needs_assignment' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('needs_assignment')}
            className={filter === 'needs_assignment' ? 'bg-amber-600 text-white' : 'border-black/20'}
            data-testid="filter-needs-assignment"
          >
            <AlertCircle className="w-4 h-4 mr-1" />
            Needs Assignment
          </Button>
          <Button
            variant={filter === 'assigned' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('assigned')}
            className={filter === 'assigned' ? 'bg-emerald-600 text-white' : 'border-black/20'}
            data-testid="filter-assigned"
          >
            <CheckCircle2 className="w-4 h-4 mr-1" />
            Assigned
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchProjects}
            className="text-black/60"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Projects List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin w-8 h-8 border-2 border-black border-t-transparent rounded-full" />
        </div>
      ) : filteredProjects.length === 0 ? (
        <Card className="border-black/10">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <Building2 className="w-12 h-12 text-black/20 mb-4" />
            <p className="text-black/50">No projects found</p>
            {filter !== 'all' && (
              <Button
                variant="link"
                onClick={() => setFilter('all')}
                className="text-black/60 mt-2"
              >
                Show all projects
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredProjects.map((project) => (
            <Card
              key={project.id}
              className={`border-black/10 hover:border-black/20 transition-colors ${
                !project.has_consultants ? 'border-l-4 border-l-amber-500' : ''
              }`}
              data-testid={`project-card-${project.id}`}
            >
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                  {/* Project Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={`${getStatusBadge(project.status).bg} ${getStatusBadge(project.status).text} ${getStatusBadge(project.status).border}`}>
                        {(project.status || 'active').toUpperCase()}
                      </Badge>
                      <span className="text-xs text-black/50 font-mono">{project.id}</span>
                      {!project.has_consultants && (
                        <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                          <AlertCircle className="w-3 h-3 mr-1" />
                          Needs Assignment
                        </Badge>
                      )}
                    </div>
                    
                    <h3 className="text-lg font-semibold text-black mb-1">
                      {project.name || project.project_name}
                    </h3>
                    <p className="text-sm text-black/60 flex items-center gap-2">
                      <Building2 className="w-4 h-4" />
                      {project.client_name}
                    </p>
                    
                    {/* Project Details */}
                    <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-black/60">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        <span>{project.start_date ? format(new Date(project.start_date), 'MMM dd, yyyy') : 'TBD'}</span>
                      </div>
                      {project.tenure_months && (
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          <span>{project.tenure_months} months</span>
                        </div>
                      )}
                      {project.project_value && (
                        <div className="flex items-center gap-1">
                          <IndianRupee className="w-4 h-4" />
                          <span>₹{project.project_value.toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Assigned Consultants */}
                  <div className="lg:w-80">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-black/50 uppercase tracking-wide">
                        Assigned Consultants
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openHistoryDialog(project)}
                        className="text-black/50 hover:text-black h-6 px-2"
                      >
                        <History className="w-3 h-3 mr-1" />
                        History
                      </Button>
                    </div>
                    
                    {project.consultant_assignments?.length > 0 ? (
                      <div className="space-y-2">
                        {project.consultant_assignments.filter(a => a.is_active).map((assignment) => (
                          <div
                            key={assignment.id}
                            className="flex items-center justify-between p-2 bg-black/5 rounded-lg"
                          >
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-black/10 flex items-center justify-center">
                                <Users className="w-4 h-4 text-black/60" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-black">
                                  {assignment.consultant_details?.full_name || assignment.consultant_name}
                                </p>
                                <p className="text-xs text-black/50">
                                  {assignment.role_in_project?.replace('_', ' ')}
                                </p>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUnassignConsultant(
                                project.id,
                                assignment.consultant_id,
                                assignment.consultant_details?.full_name || assignment.consultant_name
                              )}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50 h-8 w-8 p-0"
                              data-testid={`unassign-${assignment.consultant_id}`}
                            >
                              <UserMinus className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-4 border border-dashed border-black/10 rounded-lg">
                        <Users className="w-6 h-6 text-black/20 mx-auto mb-1" />
                        <p className="text-xs text-black/40">No consultants assigned</p>
                      </div>
                    )}
                    
                    <Button
                      onClick={() => openAssignDialog(project)}
                      size="sm"
                      className="w-full mt-3 bg-black text-white hover:bg-black/90"
                      data-testid={`assign-btn-${project.id}`}
                    >
                      <UserPlus className="w-4 h-4 mr-2" />
                      Assign Consultant
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Assign Consultant Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="border-black/10 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-black">
              Assign Consultant
            </DialogTitle>
            <DialogDescription className="text-black/50">
              {selectedProject?.name || selectedProject?.project_name}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAssignConsultant} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-black">Consultant *</Label>
              <select
                value={formData.consultant_id}
                onChange={(e) => setFormData({ ...formData, consultant_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-lg border border-black/20 bg-white focus:outline-none focus:ring-2 focus:ring-black text-sm"
                data-testid="consultant-select"
              >
                <option value="">Select a consultant</option>
                {getAvailableConsultants().map(c => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} ({c.role?.replace('_', ' ')})
                  </option>
                ))}
              </select>
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-black">Role in Project</Label>
              <select
                value={formData.role_in_project}
                onChange={(e) => setFormData({ ...formData, role_in_project: e.target.value })}
                className="w-full h-10 px-3 rounded-lg border border-black/20 bg-white focus:outline-none focus:ring-2 focus:ring-black text-sm"
              >
                <option value="lead_consultant">Lead Consultant</option>
                <option value="consultant">Consultant</option>
                <option value="support">Support</option>
              </select>
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-black">Meetings Committed</Label>
              <Input
                type="number"
                min="0"
                value={formData.meetings_committed}
                onChange={(e) => setFormData({ ...formData, meetings_committed: parseInt(e.target.value) || 0 })}
                className="border-black/20 focus:ring-black"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-black">Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-black/20 bg-white focus:outline-none focus:ring-2 focus:ring-black text-sm"
                placeholder="Optional notes..."
              />
            </div>
            
            <Button
              type="submit"
              className="w-full bg-black text-white hover:bg-black/90"
              data-testid="submit-assignment"
            >
              Assign Consultant
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Assignment History Dialog */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="border-black/10 max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-black">
              Assignment History
            </DialogTitle>
            <DialogDescription className="text-black/50">
              {selectedProject?.name || selectedProject?.project_name}
            </DialogDescription>
          </DialogHeader>
          
          {assignmentHistory.length === 0 ? (
            <div className="text-center py-8 text-black/50">
              <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No assignment history</p>
            </div>
          ) : (
            <div className="space-y-3">
              {assignmentHistory.map((assignment) => (
                <div
                  key={assignment.id}
                  className={`p-4 rounded-lg border ${
                    assignment.is_active 
                      ? 'bg-emerald-50 border-emerald-200' 
                      : 'bg-black/5 border-black/10'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-black">
                          {assignment.consultant_details?.full_name || assignment.consultant_name}
                        </p>
                        {assignment.is_active && (
                          <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>
                        )}
                        {assignment.status === 'replaced' && (
                          <Badge className="bg-amber-100 text-amber-700">Replaced</Badge>
                        )}
                      </div>
                      <p className="text-xs text-black/50 mt-1">
                        {assignment.role_in_project?.replace('_', ' ')} • 
                        Assigned by {assignment.assigned_by_name}
                      </p>
                    </div>
                  </div>
                  
                  <div className="mt-2 text-xs text-black/60">
                    <p>Assigned: {assignment.assigned_at ? format(new Date(assignment.assigned_at), 'MMM dd, yyyy HH:mm') : 'N/A'}</p>
                    {assignment.unassigned_at && (
                      <p>Unassigned: {format(new Date(assignment.unassigned_at), 'MMM dd, yyyy HH:mm')} by {assignment.unassigned_by_name}</p>
                    )}
                    {assignment.replaced_at && (
                      <p>Replaced: {format(new Date(assignment.replaced_at), 'MMM dd, yyyy HH:mm')} by {assignment.replaced_by_name}</p>
                    )}
                  </div>
                  
                  {assignment.notes && (
                    <p className="mt-2 text-sm text-black/70 italic">{assignment.notes}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AllProjects;
