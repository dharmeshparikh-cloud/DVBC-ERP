import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  Plus, ArrowLeft, CheckCircle, Clock, AlertCircle, 
  Users, Calendar, GripVertical, ChevronRight, Filter 
} from 'lucide-react';
import { toast } from 'sonner';
import { format, differenceInDays, addDays } from 'date-fns';

const TASK_STATUSES = [
  { value: 'to_do', label: 'To Do', color: 'bg-zinc-100 text-zinc-700' },
  { value: 'own_task', label: 'Own Task', color: 'bg-blue-100 text-blue-700' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'delegated', label: 'Delegated', color: 'bg-purple-100 text-purple-700' },
  { value: 'completed', label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'cancelled', label: 'Cancelled', color: 'bg-red-100 text-red-700' }
];

const TASK_CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'meeting', label: 'Meeting' },
  { value: 'deliverable', label: 'Deliverable' },
  { value: 'review', label: 'Review' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'admin', label: 'Administrative' },
  { value: 'client_communication', label: 'Client Communication' }
];

const PRIORITIES = [
  { value: 'low', label: 'Low', color: 'text-zinc-500' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-600' },
  { value: 'high', label: 'High', color: 'text-orange-600' },
  { value: 'urgent', label: 'Urgent', color: 'text-red-600' }
];

const ProjectTasks = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [consultants, setConsultants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [viewMode, setViewMode] = useState('list'); // list, gantt
  const [filterStatus, setFilterStatus] = useState('all');
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: 'general',
    status: 'to_do',
    priority: 'medium',
    assigned_to: '',
    start_date: '',
    due_date: '',
    estimated_hours: ''
  });

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const fetchData = async () => {
    try {
      const [projectRes, tasksRes, consultantsRes] = await Promise.all([
        axios.get(`${API}/projects/${projectId}`),
        axios.get(`${API}/tasks?project_id=${projectId}`),
        axios.get(`${API}/consultants`).catch(() => ({ data: [] }))
      ]);
      setProject(projectRes.data);
      setTasks(tasksRes.data);
      setConsultants(consultantsRes.data);
    } catch (error) {
      toast.error('Failed to fetch project data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const taskData = {
        project_id: projectId,
        ...formData,
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
        due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
        estimated_hours: formData.estimated_hours ? parseFloat(formData.estimated_hours) : null,
        assigned_to: formData.assigned_to || null
      };

      if (editingTask) {
        await axios.patch(`${API}/tasks/${editingTask.id}`, taskData);
        toast.success('Task updated successfully');
      } else {
        await axios.post(`${API}/tasks`, taskData);
        toast.success('Task created successfully');
      }
      
      setDialogOpen(false);
      setEditingTask(null);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save task');
    }
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await axios.patch(`${API}/tasks/${taskId}`, { status: newStatus });
      toast.success('Status updated');
      fetchData();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleDelete = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;
    try {
      await axios.delete(`${API}/tasks/${taskId}`);
      toast.success('Task deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const openEditDialog = (task) => {
    setEditingTask(task);
    setFormData({
      title: task.title,
      description: task.description || '',
      category: task.category || 'general',
      status: task.status || 'to_do',
      priority: task.priority || 'medium',
      assigned_to: task.assigned_to || '',
      start_date: task.start_date ? format(new Date(task.start_date), 'yyyy-MM-dd') : '',
      due_date: task.due_date ? format(new Date(task.due_date), 'yyyy-MM-dd') : '',
      estimated_hours: task.estimated_hours || ''
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      category: 'general',
      status: 'to_do',
      priority: 'medium',
      assigned_to: '',
      start_date: '',
      due_date: '',
      estimated_hours: ''
    });
  };

  const getStatusBadge = (status) => {
    const statusObj = TASK_STATUSES.find(s => s.value === status) || TASK_STATUSES[0];
    return <span className={`px-2 py-1 text-xs font-medium rounded-sm ${statusObj.color}`}>{statusObj.label}</span>;
  };

  const getPriorityIcon = (priority) => {
    const priorityObj = PRIORITIES.find(p => p.value === priority) || PRIORITIES[1];
    return <span className={`text-xs font-medium ${priorityObj.color}`}>{priorityObj.label}</span>;
  };

  const getAssigneeName = (userId) => {
    const consultant = consultants.find(c => c.id === userId);
    return consultant?.full_name || 'Unassigned';
  };

  const filteredTasks = filterStatus === 'all' 
    ? tasks 
    : tasks.filter(t => t.status === filterStatus);

  const tasksByStatus = TASK_STATUSES.reduce((acc, status) => {
    acc[status.value] = tasks.filter(t => t.status === status.value);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div data-testid="project-tasks-page">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/projects')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Projects
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              {project?.name || 'Project'} Tasks
            </h1>
            <p className="text-zinc-500">{project?.client_name}</p>
          </div>
          <Button
            onClick={() => { resetForm(); setEditingTask(null); setDialogOpen(true); }}
            data-testid="add-task-btn"
            className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          >
            <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Add Task
          </Button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        {TASK_STATUSES.slice(0, 5).map(status => (
          <Card key={status.value} className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">{status.label}</div>
              <div className="text-2xl font-semibold text-zinc-950">
                {tasksByStatus[status.value]?.length || 0}
              </div>
            </CardContent>
          </Card>
        ))}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total</div>
            <div className="text-2xl font-semibold text-zinc-950">{tasks.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* View Controls */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setViewMode('list')}
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            className={viewMode === 'list' ? 'bg-zinc-950' : ''}
          >
            List View
          </Button>
          <Button
            onClick={() => setViewMode('gantt')}
            variant={viewMode === 'gantt' ? 'default' : 'outline'}
            size="sm"
            className={viewMode === 'gantt' ? 'bg-zinc-950' : ''}
          >
            Timeline View
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-zinc-400" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
          >
            <option value="all">All Status</option>
            {TASK_STATUSES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Task List View */}
      {viewMode === 'list' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-0">
            {filteredTasks.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircle className="w-12 h-12 text-zinc-300 mx-auto mb-4" strokeWidth={1} />
                <p className="text-zinc-500 mb-4">No tasks found</p>
                <Button
                  onClick={() => { resetForm(); setDialogOpen(true); }}
                  className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  Create First Task
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-zinc-200">
                {/* Table Header */}
                <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-3 bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <div className="col-span-4">Task</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2">Assignee</div>
                  <div className="col-span-2">Due Date</div>
                  <div className="col-span-2">Actions</div>
                </div>
                
                {filteredTasks.map((task) => (
                  <div
                    key={task.id}
                    data-testid={`task-row-${task.id}`}
                    className="grid grid-cols-1 md:grid-cols-12 gap-4 px-4 py-4 hover:bg-zinc-50 transition-colors items-center"
                  >
                    <div className="col-span-4">
                      <div className="flex items-start gap-2">
                        <GripVertical className="w-4 h-4 text-zinc-300 mt-1 cursor-grab" />
                        <div>
                          <div className="font-medium text-zinc-950">{task.title}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm capitalize">
                              {task.category?.replace('_', ' ')}
                            </span>
                            {getPriorityIcon(task.priority)}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="col-span-2">
                      <select
                        value={task.status}
                        onChange={(e) => handleStatusChange(task.id, e.target.value)}
                        className="h-8 px-2 rounded-sm border border-zinc-200 bg-transparent text-sm w-full"
                      >
                        {TASK_STATUSES.map(s => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-span-2">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-zinc-400" strokeWidth={1.5} />
                        <span className="text-sm text-zinc-600 truncate">
                          {getAssigneeName(task.assigned_to)}
                        </span>
                      </div>
                    </div>
                    <div className="col-span-2">
                      {task.due_date ? (
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-zinc-400" strokeWidth={1.5} />
                          <span className={`text-sm ${
                            differenceInDays(new Date(task.due_date), new Date()) < 0 
                              ? 'text-red-600' 
                              : differenceInDays(new Date(task.due_date), new Date()) <= 3
                              ? 'text-yellow-600'
                              : 'text-zinc-600'
                          }`}>
                            {format(new Date(task.due_date), 'MMM dd')}
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-zinc-400">No due date</span>
                      )}
                    </div>
                    <div className="col-span-2 flex items-center gap-2">
                      <Button
                        onClick={() => openEditDialog(task)}
                        variant="ghost"
                        size="sm"
                        className="text-zinc-600 hover:text-zinc-950"
                      >
                        Edit
                      </Button>
                      <Button
                        onClick={() => handleDelete(task.id)}
                        variant="ghost"
                        size="sm"
                        className="text-red-600 hover:text-red-700"
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Gantt/Timeline View */}
      {viewMode === 'gantt' && (
        <GanttView 
          tasks={filteredTasks} 
          project={project}
          consultants={consultants}
          onTaskClick={openEditDialog}
        />
      )}

      {/* Add/Edit Task Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {editingTask ? 'Edit Task' : 'Create Task'}
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {editingTask ? 'Update task details' : 'Add a new task to this project'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Title *</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                placeholder="Task title"
                className="rounded-sm border-zinc-200"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Description</Label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                placeholder="Task description"
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Category</Label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                >
                  {TASK_CATEGORIES.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Priority</Label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                >
                  {PRIORITIES.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Status</Label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                >
                  {TASK_STATUSES.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Assign To</Label>
                <select
                  value={formData.assigned_to}
                  onChange={(e) => setFormData({ ...formData, assigned_to: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
                >
                  <option value="">Unassigned</option>
                  {consultants.map(c => (
                    <option key={c.id} value={c.id}>{c.full_name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Start Date</Label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Due Date</Label>
                <Input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Estimated Hours</Label>
              <Input
                type="number"
                min="0"
                step="0.5"
                value={formData.estimated_hours}
                onChange={(e) => setFormData({ ...formData, estimated_hours: e.target.value })}
                placeholder="e.g., 4"
                className="rounded-sm border-zinc-200"
              />
            </div>
            
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              {editingTask ? 'Update Task' : 'Create Task'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Simple Gantt/Timeline View Component
const GanttView = ({ tasks, project, consultants, onTaskClick }) => {
  const today = new Date();
  const projectStart = project?.start_date ? new Date(project.start_date) : addDays(today, -7);
  const projectEnd = project?.end_date ? new Date(project.end_date) : addDays(today, 30);
  
  const totalDays = Math.max(30, differenceInDays(projectEnd, projectStart) + 1);
  const dayWidth = 32;
  
  const getDayOffset = (date) => {
    if (!date) return 0;
    return Math.max(0, differenceInDays(new Date(date), projectStart));
  };
  
  const getBarWidth = (start, end) => {
    if (!start || !end) return dayWidth * 3;
    return Math.max(dayWidth, differenceInDays(new Date(end), new Date(start)) * dayWidth);
  };
  
  const getStatusColor = (status) => {
    const colors = {
      to_do: 'bg-zinc-300',
      own_task: 'bg-blue-400',
      in_progress: 'bg-yellow-400',
      delegated: 'bg-purple-400',
      completed: 'bg-emerald-400',
      cancelled: 'bg-red-300'
    };
    return colors[status] || colors.to_do;
  };
  
  // Generate day headers
  const days = [];
  for (let i = 0; i < totalDays; i++) {
    const day = addDays(projectStart, i);
    days.push(day);
  }

  const tasksWithDates = tasks.filter(t => t.start_date || t.due_date);
  const tasksWithoutDates = tasks.filter(t => !t.start_date && !t.due_date);

  return (
    <Card className="border-zinc-200 shadow-none rounded-sm overflow-hidden">
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <div style={{ minWidth: `${300 + totalDays * dayWidth}px` }}>
            {/* Header with dates */}
            <div className="flex border-b border-zinc-200 bg-zinc-50">
              <div className="w-[300px] flex-shrink-0 px-4 py-2 border-r border-zinc-200">
                <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Task</span>
              </div>
              <div className="flex">
                {days.map((day, i) => (
                  <div
                    key={i}
                    className={`flex-shrink-0 text-center py-2 border-r border-zinc-100 ${
                      format(day, 'yyyy-MM-dd') === format(today, 'yyyy-MM-dd')
                        ? 'bg-blue-50'
                        : ''
                    }`}
                    style={{ width: dayWidth }}
                  >
                    <div className="text-[10px] text-zinc-400">{format(day, 'EEE')}</div>
                    <div className="text-xs font-medium text-zinc-600">{format(day, 'd')}</div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Task rows */}
            {tasksWithDates.map((task) => (
              <div
                key={task.id}
                className="flex border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer"
                onClick={() => onTaskClick(task)}
              >
                <div className="w-[300px] flex-shrink-0 px-4 py-3 border-r border-zinc-200">
                  <div className="font-medium text-sm text-zinc-950 truncate">{task.title}</div>
                  <div className="text-xs text-zinc-500">
                    {consultants.find(c => c.id === task.assigned_to)?.full_name || 'Unassigned'}
                  </div>
                </div>
                <div className="relative flex-1 py-2" style={{ width: totalDays * dayWidth }}>
                  {/* Today line */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-blue-400 z-10"
                    style={{ left: getDayOffset(today) * dayWidth + dayWidth / 2 }}
                  />
                  {/* Task bar */}
                  <div
                    className={`absolute top-1/2 -translate-y-1/2 h-6 rounded-sm ${getStatusColor(task.status)} opacity-80 hover:opacity-100 transition-opacity`}
                    style={{
                      left: getDayOffset(task.start_date || task.due_date) * dayWidth + 2,
                      width: getBarWidth(task.start_date, task.due_date) - 4
                    }}
                  >
                    <span className="text-[10px] text-white px-2 truncate block leading-6">
                      {task.title}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            
            {/* Tasks without dates */}
            {tasksWithoutDates.length > 0 && (
              <>
                <div className="px-4 py-2 bg-zinc-100 text-xs font-medium uppercase tracking-wide text-zinc-500 border-b border-zinc-200">
                  Tasks without dates ({tasksWithoutDates.length})
                </div>
                {tasksWithoutDates.map((task) => (
                  <div
                    key={task.id}
                    className="flex border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer"
                    onClick={() => onTaskClick(task)}
                  >
                    <div className="w-[300px] flex-shrink-0 px-4 py-3 border-r border-zinc-200">
                      <div className="font-medium text-sm text-zinc-950 truncate">{task.title}</div>
                      <div className="text-xs text-zinc-500">
                        {consultants.find(c => c.id === task.assigned_to)?.full_name || 'Unassigned'}
                      </div>
                    </div>
                    <div className="flex-1 px-4 py-3 text-xs text-zinc-400">
                      No dates assigned - click to edit
                    </div>
                  </div>
                ))}
              </>
            )}
            
            {tasks.length === 0 && (
              <div className="text-center py-12 text-zinc-500">
                No tasks to display in timeline
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ProjectTasks;
