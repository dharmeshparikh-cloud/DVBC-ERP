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
  ArrowLeft, Plus, Check, X, CheckCircle, Clock,
  FileText, Upload, Download, Eye, Edit2, Save, Send,
  Loader2, XCircle, Paperclip, ListTodo, User, Users,
  Calendar, BarChart3, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_CONFIG = {
  not_started: { label: 'Not Started', color: 'bg-zinc-100 text-zinc-700' },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700' },
  not_applicable: { label: 'N/A', color: 'bg-orange-100 text-orange-700' },
};

const APPROVAL_STATUS = {
  pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-700' },
  approved: { label: 'Approved', color: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700' },
};

const ConsultingProjectTasks = () => {
  const { sowId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [sow, setSow] = useState(null);
  const [lead, setLead] = useState(null);
  const [employees, setEmployees] = useState([]);
  
  // Dialogs
  const [addTaskDialog, setAddTaskDialog] = useState(false);
  const [editTaskDialog, setEditTaskDialog] = useState(false);
  const [uploadDialog, setUploadDialog] = useState(false);
  const [approvalDialog, setApprovalDialog] = useState(false);
  
  // Task data
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskEdits, setTaskEdits] = useState({});
  const [newTask, setNewTask] = useState({
    name: '', description: '', scope_id: '', assigned_to: '',
    due_date: '', priority: 'medium'
  });
  
  // Approval data
  const [approvalType, setApprovalType] = useState('manager'); // manager or client
  const [approvalData, setApprovalData] = useState({ notes: '', scope_ids: [] });
  
  // Upload data
  const [uploadData, setUploadData] = useState({ file: null, description: '' });

  useEffect(() => {
    fetchData();
  }, [sowId]);

  const fetchData = async () => {
    try {
      const [sowRes, leadsRes, employeesRes] = await Promise.all([
        axios.get(`${API}/enhanced-sow/${sowId}`, {
          params: { current_user_role: user?.role }
        }),
        axios.get(`${API}/leads`),
        axios.get(`${API}/employees`).catch(() => ({ data: [] }))
      ]);
      
      setSow(sowRes.data);
      setEmployees(employeesRes.data || []);
      
      if (sowRes.data?.lead_id) {
        const leadData = leadsRes.data.find(l => l.id === sowRes.data.lead_id);
        setLead(leadData);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  // Get tasks from SOW (scopes act as main tasks)
  const tasks = useMemo(() => {
    if (!sow?.scopes) return [];
    return sow.scopes.map(scope => ({
      ...scope,
      subtasks: scope.subtasks || []
    }));
  }, [sow?.scopes]);

  // Group tasks by status
  const tasksByStatus = useMemo(() => {
    return {
      not_started: tasks.filter(t => t.status === 'not_started'),
      in_progress: tasks.filter(t => t.status === 'in_progress'),
      completed: tasks.filter(t => t.status === 'completed'),
      not_applicable: tasks.filter(t => t.status === 'not_applicable'),
    };
  }, [tasks]);

  // Stats
  const stats = useMemo(() => ({
    total: tasks.length,
    notStarted: tasksByStatus.not_started.length,
    inProgress: tasksByStatus.in_progress.length,
    completed: tasksByStatus.completed.length,
    avgProgress: tasks.length > 0 
      ? Math.round(tasks.reduce((sum, t) => sum + (t.progress_percentage || 0), 0) / tasks.length)
      : 0
  }), [tasks, tasksByStatus]);

  const openEditTask = (task) => {
    setSelectedTask(task);
    setTaskEdits({
      status: task.status,
      progress_percentage: task.progress_percentage || 0,
      days_spent: task.days_spent || 0,
      meetings_count: task.meetings_count || 0,
      notes: task.notes || ''
    });
    setEditTaskDialog(true);
  };

  const saveTask = async () => {
    if (!selectedTask) return;
    
    try {
      await axios.patch(
        `${API}/enhanced-sow/${sow.id}/scopes/${selectedTask.id}`,
        taskEdits,
        {
          params: {
            current_user_id: user?.id,
            current_user_name: user?.full_name || user?.email,
            current_user_role: user?.role
          }
        }
      );
      
      toast.success('Task updated successfully');
      setEditTaskDialog(false);
      setSelectedTask(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update task');
    }
  };

  const handleFileUpload = async () => {
    if (!uploadData.file || !selectedTask) return;
    
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target.result.split(',')[1];
        
        await axios.post(
          `${API}/enhanced-sow/${sow.id}/scopes/${selectedTask.id}/attachments`,
          {
            filename: uploadData.file.name,
            file_data: base64,
            description: uploadData.description
          },
          {
            params: {
              current_user_id: user?.id,
              current_user_name: user?.full_name || user?.email
            }
          }
        );
        
        toast.success('File uploaded successfully');
        setUploadDialog(false);
        setUploadData({ file: null, description: '' });
        fetchData();
      };
      reader.readAsDataURL(uploadData.file);
    } catch (error) {
      toast.error('Failed to upload file');
    }
  };

  const sendForApproval = async () => {
    if (approvalData.scope_ids.length === 0) {
      toast.error('Please select at least one scope');
      return;
    }
    
    try {
      const endpoint = approvalType === 'manager' 
        ? `${API}/enhanced-sow/${sow.id}/request-manager-approval`
        : `${API}/enhanced-sow/${sow.id}/roadmap/submit`;
      
      await axios.post(endpoint, {
        scope_ids: approvalData.scope_ids,
        notes: approvalData.notes,
        approval_cycle: 'monthly',
        period_label: format(new Date(), 'MMMM yyyy')
      }, {
        params: {
          current_user_id: user?.id,
          current_user_name: user?.full_name || user?.email
        }
      });
      
      toast.success(`Sent for ${approvalType === 'manager' ? 'manager' : 'client'} approval`);
      setApprovalDialog(false);
      setApprovalData({ notes: '', scope_ids: [] });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send for approval');
    }
  };

  const toggleScopeForApproval = (scopeId) => {
    const newIds = approvalData.scope_ids.includes(scopeId)
      ? approvalData.scope_ids.filter(id => id !== scopeId)
      : [...approvalData.scope_ids, scopeId];
    setApprovalData({ ...approvalData, scope_ids: newIds });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!sow) {
    return (
      <div data-testid="project-tasks-page">
        <Button onClick={() => navigate(-1)} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <XCircle className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">Project Not Found</h3>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div data-testid="project-tasks-page">
      {/* Header */}
      <div className="mb-6">
        <Button onClick={() => navigate('/consulting/projects')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Projects
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Project Tasks
            </h1>
            <p className="text-zinc-500">
              {lead ? `${lead.company} - ${lead.first_name} ${lead.last_name}` : 'Project Tasks'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={() => {
                setApprovalType('manager');
                setApprovalDialog(true);
              }}
              variant="outline"
              className="rounded-sm"
              data-testid="send-manager-approval-btn"
            >
              <User className="w-4 h-4 mr-2" />
              Send to Manager
            </Button>
            <Button
              onClick={() => {
                setApprovalType('client');
                setApprovalDialog(true);
              }}
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              data-testid="send-client-approval-btn"
            >
              <Send className="w-4 h-4 mr-2" />
              Send to Client
            </Button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Tasks</div>
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
        <Card className="border-indigo-200 bg-indigo-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-indigo-600 uppercase tracking-wide">Avg Progress</div>
            <div className="text-2xl font-semibold text-indigo-700">{stats.avgProgress}%</div>
          </CardContent>
        </Card>
      </div>

      {/* Task List */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardHeader className="border-b border-zinc-100">
          <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-700">
            Scope Tasks ({tasks.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-zinc-100">
            {tasks.map(task => {
              const statusConfig = STATUS_CONFIG[task.status] || STATUS_CONFIG.not_started;
              
              return (
                <div 
                  key={task.id}
                  className="p-4 hover:bg-zinc-50 transition-colors"
                  data-testid={`task-row-${task.id}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-zinc-900">{task.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                          {statusConfig.label}
                        </span>
                        {task.source === 'consulting_added' && (
                          <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-sm">
                            Added
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-zinc-500 mb-2">
                        {task.category_name}
                        {task.description && ` • ${task.description}`}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <BarChart3 className="w-3.5 h-3.5" />
                          {task.progress_percentage || 0}%
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {task.days_spent || 0} days
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3.5 h-3.5" />
                          {task.meetings_count || 0} meetings
                        </span>
                        {task.attachments?.length > 0 && (
                          <span className="flex items-center gap-1 text-blue-600">
                            <Paperclip className="w-3.5 h-3.5" />
                            {task.attachments.length} files
                          </span>
                        )}
                      </div>
                      {/* Progress bar */}
                      <div className="mt-2">
                        <Progress value={task.progress_percentage || 0} className="h-1.5" />
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => {
                          setSelectedTask(task);
                          setUploadDialog(true);
                        }}
                        variant="ghost"
                        size="sm"
                        className="text-zinc-500 hover:text-zinc-900"
                        data-testid={`upload-${task.id}`}
                      >
                        <Upload className="w-4 h-4" />
                      </Button>
                      <Button
                        onClick={() => openEditTask(task)}
                        variant="ghost"
                        size="sm"
                        className="text-zinc-500 hover:text-zinc-900"
                        data-testid={`edit-task-${task.id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Edit Task Dialog */}
      <Dialog open={editTaskDialog} onOpenChange={setEditTaskDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Update Task
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedTask?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <select
                value={taskEdits.status || 'not_started'}
                onChange={(e) => setTaskEdits({ ...taskEdits, status: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="not_applicable">Not Applicable</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Progress (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={taskEdits.progress_percentage || 0}
                onChange={(e) => setTaskEdits({ ...taskEdits, progress_percentage: parseInt(e.target.value) || 0 })}
                className="rounded-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Days Spent</Label>
                <Input
                  type="number"
                  min="0"
                  value={taskEdits.days_spent || 0}
                  onChange={(e) => setTaskEdits({ ...taskEdits, days_spent: parseInt(e.target.value) || 0 })}
                  className="rounded-sm"
                />
              </div>
              <div className="space-y-2">
                <Label>Meetings</Label>
                <Input
                  type="number"
                  min="0"
                  value={taskEdits.meetings_count || 0}
                  onChange={(e) => setTaskEdits({ ...taskEdits, meetings_count: parseInt(e.target.value) || 0 })}
                  className="rounded-sm"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <textarea
                value={taskEdits.notes || ''}
                onChange={(e) => setTaskEdits({ ...taskEdits, notes: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button onClick={() => setEditTaskDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={saveTask} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                <Save className="w-4 h-4 mr-2" />
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog open={uploadDialog} onOpenChange={setUploadDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Upload Attachment
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedTask?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>File</Label>
              <Input
                type="file"
                onChange={(e) => setUploadData({ ...uploadData, file: e.target.files[0] })}
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={uploadData.description}
                onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                placeholder="Brief description..."
                className="rounded-sm"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button onClick={() => setUploadDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button 
                onClick={handleFileUpload} 
                disabled={!uploadData.file}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Approval Dialog */}
      <Dialog open={approvalDialog} onOpenChange={setApprovalDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Send for {approvalType === 'manager' ? 'Manager' : 'Client'} Approval
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Select scopes to include in the approval request
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              {tasks.map(task => (
                <div 
                  key={task.id}
                  onClick={() => toggleScopeForApproval(task.id)}
                  className={`p-3 rounded-sm border cursor-pointer transition-colors ${
                    approvalData.scope_ids.includes(task.id)
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-zinc-200 hover:border-zinc-300'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-5 h-5 rounded-sm border flex items-center justify-center ${
                      approvalData.scope_ids.includes(task.id)
                        ? 'bg-blue-500 border-blue-500'
                        : 'border-zinc-300'
                    }`}>
                      {approvalData.scope_ids.includes(task.id) && (
                        <Check className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm text-zinc-900">{task.name}</div>
                      <div className="text-xs text-zinc-500">
                        {task.progress_percentage || 0}% complete • {task.status}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <textarea
                value={approvalData.notes}
                onChange={(e) => setApprovalData({ ...approvalData, notes: e.target.value })}
                rows={3}
                placeholder={`Add notes for ${approvalType === 'manager' ? 'your manager' : 'the client'}...`}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
              />
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-3">
              <div className="text-sm text-blue-700">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                {approvalType === 'manager' 
                  ? 'Your reporting manager will be notified for approval.' 
                  : 'Client will receive a notification to review and approve.'}
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <Button onClick={() => setApprovalDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button 
                onClick={sendForApproval}
                disabled={approvalData.scope_ids.length === 0}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Send className="w-4 h-4 mr-2" />
                Send ({approvalData.scope_ids.length} scopes)
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsultingProjectTasks;
