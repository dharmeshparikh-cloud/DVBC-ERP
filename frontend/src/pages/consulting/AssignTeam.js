import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  Users, UserPlus, Search, CheckCircle, Loader2, ArrowRight, 
  Building2, Calendar, DollarSign, FileText, Trash2, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import ConsultingStageNav from '../../components/ConsultingStageNav';
import { sanitizeDisplayText } from '../../utils/sanitize';

const CONSULTANT_ROLES = [
  { value: 'lead_consultant', label: 'Lead Consultant' },
  { value: 'senior_consultant', label: 'Senior Consultant' },
  { value: 'consultant', label: 'Consultant' },
  { value: 'subject_matter_expert', label: 'Subject Matter Expert' },
];

const AssignTeam = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [project, setProject] = useState(null);
  const [kickoffRequest, setKickoffRequest] = useState(null);
  const [consultants, setConsultants] = useState([]);
  const [assignedTeam, setAssignedTeam] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedConsultant, setSelectedConsultant] = useState(null);
  const [selectedRole, setSelectedRole] = useState('consultant');

  const isPM = user?.role === 'project_manager' || user?.role === 'admin' || user?.role === 'manager';

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      const [projectRes, consultantsRes, kickoffRes] = await Promise.all([
        axios.get(`${API}/projects/${projectId}`).catch(() => ({ data: null })),
        axios.get(`${API}/employees/consultants`).catch(() => ({ data: [] })),
        axios.get(`${API}/kickoff-requests`).catch(() => ({ data: [] }))
      ]);
      
      setProject(projectRes.data);
      setConsultants(consultantsRes.data || []);
      
      // Find the kickoff request for this project
      const relatedKickoff = (kickoffRes.data || []).find(k => 
        k.project_id === projectId || k.id === projectRes.data?.kickoff_request_id
      );
      setKickoffRequest(relatedKickoff);
      
      // Load existing assignments
      if (projectRes.data?.assigned_consultants) {
        setAssignedTeam(projectRes.data.assigned_consultants);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddConsultant = () => {
    if (!selectedConsultant) {
      toast.error('Please select a consultant');
      return;
    }

    // Check if already assigned
    if (assignedTeam.find(t => t.user_id === selectedConsultant.user_id)) {
      toast.error('This consultant is already assigned');
      return;
    }

    const newMember = {
      user_id: selectedConsultant.user_id,
      name: `${selectedConsultant.first_name} ${selectedConsultant.last_name}`,
      email: selectedConsultant.email,
      role: selectedRole,
      department: selectedConsultant.department,
      assigned_at: new Date().toISOString()
    };

    setAssignedTeam([...assignedTeam, newMember]);
    setShowAddDialog(false);
    setSelectedConsultant(null);
    setSelectedRole('consultant');
    toast.success(`${newMember.name} added to team`);
  };

  const handleRemoveConsultant = (userId) => {
    setAssignedTeam(assignedTeam.filter(t => t.user_id !== userId));
    toast.success('Consultant removed from team');
  };

  const handleSaveAndContinue = async () => {
    if (assignedTeam.length === 0) {
      toast.error('Please assign at least one consultant');
      return;
    }

    setSaving(true);
    try {
      // Save each consultant assignment
      for (const member of assignedTeam) {
        await axios.post(`${API}/projects/${projectId}/assign-consultant`, {
          consultant_id: member.user_id,
          role: member.role
        }).catch(() => {}); // Ignore if already assigned
      }

      toast.success('Team assigned successfully');
      navigate('/consulting/my-projects');
    } catch (error) {
      console.error('Error saving team:', error);
      toast.error('Failed to save team assignments');
    } finally {
      setSaving(false);
    }
  };

  // Filter consultants for search
  const filteredConsultants = consultants.filter(c => {
    const searchLower = searchQuery.toLowerCase();
    const fullName = `${c.first_name} ${c.last_name}`.toLowerCase();
    return fullName.includes(searchLower) || c.email?.toLowerCase().includes(searchLower);
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertCircle className="w-16 h-16 text-zinc-300 mb-4" />
        <h3 className="text-lg font-medium text-zinc-700">Project Not Found</h3>
        <p className="text-zinc-500 mb-4">The project you're looking for doesn't exist.</p>
        <Button onClick={() => navigate('/kickoff-requests')}>
          Back to Kickoff Requests
        </Button>
      </div>
    );
  }

  return (
    <div data-testid="assign-team-page">
      {/* Stage Navigation */}
      <ConsultingStageNav 
        currentStage={2}
        projectId={projectId}
        projectName={project?.name || kickoffRequest?.project_name}
        completedStages={[1]}
        showFullNav={true}
      />

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
          Assign Consulting Team
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Select consultants to work on this project
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Project Summary */}
        <Card className="border-zinc-200 shadow-none rounded-sm lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-medium">Project Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-xs text-zinc-500 uppercase tracking-wide">Client</Label>
              <p className="font-medium text-zinc-900">
                {sanitizeDisplayText(kickoffRequest?.client_name || project?.name || 'Unknown')}
              </p>
            </div>
            <div>
              <Label className="text-xs text-zinc-500 uppercase tracking-wide">Project</Label>
              <p className="text-sm text-zinc-700">
                {sanitizeDisplayText(kickoffRequest?.project_name || project?.name)}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div>
                <Label className="text-xs text-zinc-500 uppercase tracking-wide">Duration</Label>
                <p className="text-sm text-zinc-700 flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {kickoffRequest?.project_tenure_months || 12} months
                </p>
              </div>
              <div>
                <Label className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</Label>
                <p className="text-sm text-zinc-700">
                  {kickoffRequest?.meeting_frequency || 'Monthly'}
                </p>
              </div>
            </div>
            {kickoffRequest?.total_meetings > 0 && (
              <div>
                <Label className="text-xs text-zinc-500 uppercase tracking-wide">Total Meetings</Label>
                <p className="text-sm text-zinc-700">{kickoffRequest.total_meetings}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Team Assignment */}
        <Card className="border-zinc-200 shadow-none rounded-sm lg:col-span-2">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-base font-medium">Assigned Team ({assignedTeam.length})</CardTitle>
            {isPM && (
              <Button onClick={() => setShowAddDialog(true)} size="sm" data-testid="add-consultant-btn">
                <UserPlus className="w-4 h-4 mr-1" />
                Add Consultant
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {assignedTeam.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-zinc-300 mx-auto mb-3" />
                <p className="text-zinc-500">No consultants assigned yet</p>
                <p className="text-sm text-zinc-400">Click "Add Consultant" to build your team</p>
              </div>
            ) : (
              <div className="space-y-3">
                {assignedTeam.map((member, index) => (
                  <div 
                    key={member.user_id || index}
                    className="flex items-center justify-between p-3 bg-zinc-50 rounded-sm"
                    data-testid={`team-member-${member.user_id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-zinc-200 flex items-center justify-center text-sm font-medium text-zinc-600">
                        {member.name?.charAt(0)?.toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-zinc-900">{sanitizeDisplayText(member.name)}</p>
                        <p className="text-xs text-zinc-500">{member.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-xs">
                        {CONSULTANT_ROLES.find(r => r.value === member.role)?.label || member.role}
                      </Badge>
                      {isPM && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveConsultant(member.user_id)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3 mt-6">
        <Button
          variant="outline"
          onClick={() => navigate('/kickoff-requests')}
        >
          Back to Kickoff Requests
        </Button>
        <Button
          onClick={handleSaveAndContinue}
          disabled={assignedTeam.length === 0 || saving}
          className="bg-zinc-950 text-white hover:bg-zinc-800"
          data-testid="save-team-btn"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              Save & Continue
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </div>

      {/* Add Consultant Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Consultant</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search consultants..."
                className="pl-10"
              />
            </div>

            {/* Consultant List */}
            <div className="max-h-60 overflow-y-auto space-y-2">
              {filteredConsultants.map(consultant => {
                const isSelected = selectedConsultant?.user_id === consultant.user_id;
                const isAssigned = assignedTeam.find(t => t.user_id === consultant.user_id);
                
                return (
                  <button
                    key={consultant.id}
                    onClick={() => !isAssigned && setSelectedConsultant(consultant)}
                    disabled={isAssigned}
                    className={`w-full flex items-center gap-3 p-3 rounded-sm text-left transition-colors ${
                      isSelected 
                        ? 'bg-zinc-900 text-white' 
                        : isAssigned 
                          ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                          : 'hover:bg-zinc-100'
                    }`}
                    data-testid={`consultant-option-${consultant.id}`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                      isSelected ? 'bg-white text-zinc-900' : 'bg-zinc-200 text-zinc-600'
                    }`}>
                      {consultant.first_name?.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium truncate ${isSelected ? 'text-white' : ''}`}>
                        {consultant.first_name} {consultant.last_name}
                      </p>
                      <p className={`text-xs truncate ${isSelected ? 'text-zinc-300' : 'text-zinc-500'}`}>
                        {consultant.designation || consultant.department}
                      </p>
                    </div>
                    {isAssigned && (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    )}
                  </button>
                );
              })}
              {filteredConsultants.length === 0 && (
                <p className="text-center text-zinc-500 py-4">No consultants found</p>
              )}
            </div>

            {/* Role Selection */}
            {selectedConsultant && (
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={selectedRole} onValueChange={setSelectedRole}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CONSULTANT_ROLES.map(role => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleAddConsultant}
              disabled={!selectedConsultant}
            >
              Add to Team
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AssignTeam;
