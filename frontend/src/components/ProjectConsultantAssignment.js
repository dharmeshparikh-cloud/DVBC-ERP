import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { UserPlus, UserMinus, Users, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const ProjectConsultantAssignment = ({ projectId, projectStartDate, onUpdate }) => {
  const [consultants, setConsultants] = useState([]);
  const [assignedConsultants, setAssignedConsultants] = useState([]);
  const [availableConsultants, setAvailableConsultants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [changeDialogOpen, setChangeDialogOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [formData, setFormData] = useState({
    consultant_id: '',
    role_in_project: 'consultant',
    meetings_committed: 0,
    notes: ''
  });

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      const [consultantsRes] = await Promise.all([
        axios.get(`${API}/consultants`)
      ]);
      
      const allConsultants = consultantsRes.data;
      setConsultants(allConsultants);
      
      // Filter assigned consultants for this project
      const assigned = allConsultants.filter(c => 
        c.assignments?.some(a => a.project_id === projectId && a.is_active)
      ).map(c => ({
        ...c,
        assignment: c.assignments?.find(a => a.project_id === projectId && a.is_active)
      }));
      
      setAssignedConsultants(assigned);
      
      // Filter available consultants (with available slots and not already assigned)
      const available = allConsultants.filter(c => 
        c.stats?.available_slots > 0 &&
        !c.assignments?.some(a => a.project_id === projectId && a.is_active)
      );
      
      setAvailableConsultants(available);
    } catch (error) {
      toast.error('Failed to fetch consultants');
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/projects/${projectId}/assign-consultant`, formData);
      toast.success('Consultant assigned successfully');
      setAssignDialogOpen(false);
      setFormData({ consultant_id: '', role_in_project: 'consultant', meetings_committed: 0, notes: '' });
      fetchData();
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign consultant');
    }
  };

  const handleUnassign = async (consultantId) => {
    if (!window.confirm('Are you sure you want to remove this consultant from the project?')) return;
    
    try {
      await axios.delete(`${API}/projects/${projectId}/unassign-consultant/${consultantId}`);
      toast.success('Consultant removed from project');
      fetchData();
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove consultant');
    }
  };

  const handleChange = async (e) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    
    try {
      await axios.patch(`${API}/projects/${projectId}/change-consultant`, null, {
        params: {
          old_consultant_id: selectedAssignment.id,
          new_consultant_id: formData.consultant_id
        }
      });
      toast.success('Consultant changed successfully');
      setChangeDialogOpen(false);
      setSelectedAssignment(null);
      setFormData({ consultant_id: '', role_in_project: 'consultant', meetings_committed: 0, notes: '' });
      fetchData();
      if (onUpdate) onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change consultant');
    }
  };

  const openChangeDialog = (consultant) => {
    setSelectedAssignment(consultant);
    setFormData({ consultant_id: '', role_in_project: 'consultant', meetings_committed: 0, notes: '' });
    setChangeDialogOpen(true);
  };

  const canModify = () => {
    if (!projectStartDate) return true;
    const startDate = new Date(projectStartDate);
    return startDate > new Date();
  };

  if (loading) {
    return <div className="text-zinc-500 text-sm">Loading consultants...</div>;
  }

  return (
    <div className="space-y-4" data-testid="project-consultant-assignment">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium uppercase tracking-wide text-zinc-950">
          Assigned Consultants ({assignedConsultants.length})
        </h3>
        <Button
          onClick={() => setAssignDialogOpen(true)}
          size="sm"
          disabled={availableConsultants.length === 0}
          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
        >
          <UserPlus className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Assign Consultant
        </Button>
      </div>

      {assignedConsultants.length === 0 ? (
        <div className="text-center py-6 border border-dashed border-zinc-200 rounded-sm">
          <Users className="w-8 h-8 text-zinc-300 mx-auto mb-2" strokeWidth={1} />
          <p className="text-sm text-zinc-500">No consultants assigned yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {assignedConsultants.map((consultant) => (
            <div
              key={consultant.id}
              className="flex items-center justify-between p-3 border border-zinc-200 rounded-sm"
            >
              <div className="flex-1">
                <div className="font-medium text-zinc-950">{consultant.full_name}</div>
                <div className="text-xs text-zinc-500">
                  {consultant.assignment?.role_in_project?.replace('_', ' ') || 'Consultant'} •
                  Meetings: {consultant.assignment?.meetings_completed || 0}/{consultant.assignment?.meetings_committed || 0}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {canModify() && (
                  <>
                    <Button
                      onClick={() => openChangeDialog(consultant)}
                      size="sm"
                      variant="ghost"
                      className="text-zinc-600 hover:text-zinc-950"
                    >
                      <RefreshCw className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                    <Button
                      onClick={() => handleUnassign(consultant.id)}
                      size="sm"
                      variant="ghost"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <UserMinus className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!canModify() && (
        <p className="text-xs text-yellow-600 bg-yellow-50 p-2 rounded-sm">
          Project has started. Only admins can modify consultant assignments.
        </p>
      )}

      {/* Assign Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Assign Consultant
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Select a consultant with available capacity
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAssign} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Consultant *</Label>
              <select
                value={formData.consultant_id}
                onChange={(e) => setFormData({ ...formData, consultant_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="">Select a consultant</option>
                {availableConsultants.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} ({c.stats?.available_slots} slots available)
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Role in Project</Label>
              <select
                value={formData.role_in_project}
                onChange={(e) => setFormData({ ...formData, role_in_project: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="lead_consultant">Lead Consultant</option>
                <option value="consultant">Consultant</option>
                <option value="support">Support</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Meetings Committed</Label>
              <Input
                type="number"
                min="0"
                value={formData.meetings_committed}
                onChange={(e) => setFormData({ ...formData, meetings_committed: parseInt(e.target.value) || 0 })}
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Notes</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Assign Consultant
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Change Consultant Dialog */}
      <Dialog open={changeDialogOpen} onOpenChange={setChangeDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Change Consultant
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Replace {selectedAssignment?.full_name} with another consultant
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChange} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">New Consultant *</Label>
              <select
                value={formData.consultant_id}
                onChange={(e) => setFormData({ ...formData, consultant_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="">Select a consultant</option>
                {availableConsultants.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} ({c.stats?.available_slots} slots available)
                  </option>
                ))}
              </select>
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Change Consultant
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectConsultantAssignment;
