import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Calendar, Users, IndianRupee, ListTodo, UserPlus, PlayCircle } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import ProjectConsultantAssignment from '../components/ProjectConsultantAssignment';

const Projects = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    client_name: '',
    start_date: '',
    end_date: '',
    total_meetings_committed: 0,
    budget: '',
    notes: '',
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API}/projects`);
      setProjects(response.data);
    } catch (error) {
      toast.error('Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const projectData = {
        ...formData,
        start_date: new Date(formData.start_date).toISOString(),
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
        total_meetings_committed: parseInt(formData.total_meetings_committed) || 0,
        budget: formData.budget ? parseFloat(formData.budget) : null,
      };
      await axios.post(`${API}/projects`, projectData);
      toast.success('Project created successfully');
      setDialogOpen(false);
      setFormData({
        name: '',
        client_name: '',
        start_date: '',
        end_date: '',
        total_meetings_committed: 0,
        budget: '',
        notes: '',
      });
      fetchProjects();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create project');
    }
  };

  const canEdit = user?.role !== 'manager';

  return (
    <div data-testid="projects-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 dark:text-zinc-100 mb-2">
            Projects
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400">Track your consulting projects and deliverables</p>
        </div>
        {/* Projects can only be created via Kickoff Request handover from Sales team */}
        {false && canEdit && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                data-testid="add-project-button"
                className="bg-zinc-950 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Create Project
              </Button>
            </DialogTrigger>
            <DialogContent className="border-zinc-200 dark:border-zinc-700 dark:bg-zinc-900 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950 dark:text-zinc-100">
                  Create New Project
                </DialogTitle>
                <DialogDescription className="text-zinc-500 dark:text-zinc-400">
                  Set up a new consulting project with client details
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                    Project Name *
                  </Label>
                  <Input
                    id="name"
                    data-testid="project-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="client_name" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                    Client Name *
                  </Label>
                  <Input
                    id="client_name"
                    data-testid="project-client"
                    value={formData.client_name}
                    onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                    required
                    className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="start_date" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                      Start Date *
                    </Label>
                    <Input
                      id="start_date"
                      data-testid="project-start-date"
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                      required
                      className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end_date" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                      End Date
                    </Label>
                    <Input
                      id="end_date"
                      data-testid="project-end-date"
                      type="date"
                      value={formData.end_date}
                      onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label
                      htmlFor="total_meetings_committed"
                      className="text-sm font-medium text-zinc-950 dark:text-zinc-100"
                    >
                      Meetings Committed
                    </Label>
                    <Input
                      id="total_meetings_committed"
                      data-testid="project-meetings-committed"
                      type="number"
                      min="0"
                      value={formData.total_meetings_committed}
                      onChange={(e) =>
                        setFormData({ ...formData, total_meetings_committed: e.target.value })
                      }
                      className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="budget" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                      Budget (₹)
                    </Label>
                    <Input
                      id="budget"
                      data-testid="project-budget"
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.budget}
                      onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                      className="rounded-sm border-zinc-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-medium text-zinc-950 dark:text-zinc-100">
                    Notes
                  </Label>
                  <textarea
                    id="notes"
                    data-testid="project-notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 dark:border-zinc-700 bg-transparent dark:bg-zinc-800 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-950 dark:focus:ring-zinc-400 text-sm"
                  />
                </div>

                <Button
                  type="submit"
                  data-testid="submit-project-button"
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 rounded-sm shadow-none"
                >
                  Create Project
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading projects...</div>
        </div>
      ) : projects.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <p className="text-zinc-500 mb-2">No projects found</p>
            <p className="text-sm text-zinc-400 text-center max-w-md">
              Projects are created via Kickoff Request handover from Sales team. 
              Go to Kickoff Requests to accept pending requests and create projects.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {projects.map((project) => (
            <Card
              key={project.id}
              data-testid={`project-card-${project.id}`}
              className="border-zinc-200 dark:border-zinc-700 dark:bg-zinc-900 shadow-none rounded-sm hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg font-semibold text-zinc-950 dark:text-zinc-100">
                      {project.name}
                    </CardTitle>
                    <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{project.client_name}</div>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-sm ${
                      project.status === 'active'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-zinc-100 text-zinc-600'
                    }`}
                  >
                    {project.status}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-1">
                      <Calendar className="w-3 h-3" strokeWidth={1.5} />
                      Start Date
                    </div>
                    <div className="text-sm font-medium text-zinc-950 dark:text-zinc-100 data-text">
                      {format(new Date(project.start_date), 'MMM dd, yyyy')}
                    </div>
                  </div>
                  {project.budget && (
                    <div>
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500 mb-1">
                        <IndianRupee className="w-3 h-3" strokeWidth={1.5} />
                        Budget
                      </div>
                      <div className="text-sm font-medium text-zinc-950 dark:text-zinc-100 data-text">
                        ₹{project.budget.toLocaleString('en-IN')}
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-700">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                      Committed
                    </div>
                    <div className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 data-text">
                      {project.total_meetings_committed}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                      Delivered
                    </div>
                    <div className="text-lg font-semibold text-emerald-600 data-text">
                      {project.total_meetings_delivered}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Visits</div>
                    <div className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 data-text">
                      {project.number_of_visits}
                    </div>
                  </div>
                </div>

                {project.notes && (
                  <div className="pt-3 border-t border-zinc-200 dark:border-zinc-700">
                    <div className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-1">Notes</div>
                    <div className="text-sm text-zinc-600 dark:text-zinc-300">{project.notes}</div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-4 border-t border-zinc-200 dark:border-zinc-700 flex flex-wrap gap-2">
                  <Button
                    onClick={() => navigate(`/projects/${project.id}/kickoff`)}
                    size="sm"
                    className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                    data-testid={`kickoff-btn-${project.id}`}
                  >
                    <PlayCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Kick-off
                  </Button>
                  <Button
                    onClick={() => navigate(`/projects/${project.id}/tasks`)}
                    size="sm"
                    variant="outline"
                    className="rounded-sm"
                  >
                    <ListTodo className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Tasks
                  </Button>
                  {canEdit && (
                    <Button
                      onClick={() => {
                        setSelectedProject(project);
                        setAssignDialogOpen(true);
                      }}
                      size="sm"
                      variant="outline"
                      className="rounded-sm"
                    >
                      <UserPlus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Assign Consultant
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Assign Consultant Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Manage Consultants
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedProject?.name}
            </DialogDescription>
          </DialogHeader>
          {selectedProject && (
            <ProjectConsultantAssignment
              projectId={selectedProject.id}
              projectStartDate={selectedProject.start_date}
              onUpdate={() => fetchProjects()}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Projects;
