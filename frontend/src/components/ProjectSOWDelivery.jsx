/**
 * ProjectSOWDelivery.jsx - SOW Delivery Tab for Project Detail
 * 
 * This component provides the delivery layer UI for SOW execution:
 * - View PROJECT_SOW (inherited from SOW_MASTER)
 * - Manage scopes with status tracking
 * - Create and manage tasks under scopes
 * - Upload proofs for SOW and tasks
 * 
 * Architecture:
 * - SOW_MASTER (enhanced_sow) = Sales owned, locked after kickoff
 * - PROJECT_SOW = Delivery owned, PM customizable
 * - TASKS = Execution units under scopes
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { Progress } from './ui/progress';
import { toast } from 'sonner';
import { 
  FileText, Plus, CheckCircle, Clock, AlertCircle, 
  ChevronDown, ChevronRight, Upload, Download, Trash2,
  Edit2, Play, Pause, RotateCcw, Lock, Unlock,
  ListTodo, ClipboardList, User, Calendar, FileUp, Loader2
} from 'lucide-react';

// Status configurations
const SOW_STATUSES = {
  open: { label: 'Open', color: 'bg-zinc-100 text-zinc-700', icon: Clock },
  wip: { label: 'Work In Progress', color: 'bg-blue-100 text-blue-700', icon: Play },
  delivered: { label: 'Delivered', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  not_applicable: { label: 'Not Applicable', color: 'bg-zinc-100 text-zinc-500', icon: Pause },
  reopen: { label: 'Re-Opened', color: 'bg-amber-100 text-amber-700', icon: RotateCcw }
};

const TASK_STATUSES = {
  open: { label: 'Open', color: 'bg-zinc-100 text-zinc-700' },
  wip: { label: 'WIP', color: 'bg-blue-100 text-blue-700' },
  delivered: { label: 'Delivered', color: 'bg-emerald-100 text-emerald-700' },
  blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700' }
};

// Scope Card Component
const ScopeCard = ({ 
  scope, 
  tasks, 
  onStatusChange, 
  onTaskCreate, 
  onTaskUpdate, 
  onTaskDelete,
  permissions 
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [showTaskDialog, setShowTaskDialog] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: '', description: '' });
  
  const scopeTasks = tasks.filter(t => t.scope_id === scope.id);
  const completedTasks = scopeTasks.filter(t => t.status === 'delivered').length;
  const progress = scopeTasks.length > 0 ? (completedTasks / scopeTasks.length) * 100 : 0;
  
  const statusConfig = SOW_STATUSES[scope.status] || SOW_STATUSES.open;
  const StatusIcon = statusConfig.icon;
  
  const handleCreateTask = () => {
    if (!taskForm.title.trim()) {
      toast.error('Task title is required');
      return;
    }
    onTaskCreate(scope.id, taskForm);
    setTaskForm({ title: '', description: '' });
    setShowTaskDialog(false);
  };
  
  return (
    <Card className="border border-zinc-200">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-zinc-50/50 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <div>
                  <CardTitle className="text-sm font-medium">{scope.name}</CardTitle>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {scope.category_name || scope.domain} • {scope.timeline_weeks || '?'} weeks
                    {scope.assigned_consultant_name && ` • ${scope.assigned_consultant_name}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Progress */}
                <div className="w-24 flex items-center gap-2">
                  <Progress value={progress} className="h-1.5" />
                  <span className="text-xs text-zinc-500 w-8">{Math.round(progress)}%</span>
                </div>
                
                {/* Status */}
                <Badge className={`${statusConfig.color} text-xs`}>
                  <StatusIcon className="w-3 h-3 mr-1" />
                  {statusConfig.label}
                </Badge>
                
                {/* Status Change */}
                {permissions.can_manage_tasks && (
                  <Select 
                    value={scope.status} 
                    onValueChange={(v) => onStatusChange(scope.id, v)}
                  >
                    <SelectTrigger className="w-8 h-8 p-0 border-none">
                      <Edit2 className="w-3 h-3" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(SOW_STATUSES).map(([key, config]) => (
                        <SelectItem key={key} value={key}>
                          <span className={`${config.color} px-2 py-0.5 rounded text-xs`}>
                            {config.label}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0 pb-3">
            {/* Description */}
            {scope.description && (
              <p className="text-sm text-zinc-600 mb-3 pl-7">{scope.description}</p>
            )}
            
            {/* Deliverables */}
            {scope.deliverables?.length > 0 && (
              <div className="pl-7 mb-3">
                <p className="text-xs font-medium text-zinc-500 mb-1">DELIVERABLES</p>
                <ul className="text-sm text-zinc-600 space-y-0.5">
                  {scope.deliverables.map((d, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="w-1 h-1 bg-zinc-400 rounded-full" />
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Tasks */}
            <div className="pl-7">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-zinc-500">
                  TASKS ({scopeTasks.length})
                </p>
                {permissions.can_manage_tasks && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 text-xs"
                    onClick={() => setShowTaskDialog(true)}
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    Add Task
                  </Button>
                )}
              </div>
              
              {scopeTasks.length === 0 ? (
                <p className="text-xs text-zinc-400 italic">No tasks yet</p>
              ) : (
                <div className="space-y-1">
                  {scopeTasks.map(task => (
                    <TaskRow 
                      key={task.id} 
                      task={task} 
                      onUpdate={onTaskUpdate}
                      onDelete={onTaskDelete}
                      permissions={permissions}
                    />
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
      
      {/* Add Task Dialog */}
      <Dialog open={showTaskDialog} onOpenChange={setShowTaskDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Task to {scope.name}</DialogTitle>
            <DialogDescription>
              Create a new task under this scope item
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="task-title">Title *</Label>
              <Input
                id="task-title"
                value={taskForm.title}
                onChange={(e) => setTaskForm(p => ({ ...p, title: e.target.value }))}
                placeholder="e.g., Review policy document"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="task-desc">Description</Label>
              <Textarea
                id="task-desc"
                value={taskForm.description}
                onChange={(e) => setTaskForm(p => ({ ...p, description: e.target.value }))}
                placeholder="Optional details..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTaskDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateTask}>Create Task</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

// Task Row Component
const TaskRow = ({ task, onUpdate, onDelete, permissions }) => {
  const statusConfig = TASK_STATUSES[task.status] || TASK_STATUSES.open;
  
  return (
    <div className="flex items-center justify-between p-2 bg-zinc-50 rounded text-sm group">
      <div className="flex items-center gap-2 flex-1">
        <ListTodo className="w-3.5 h-3.5 text-zinc-400" />
        <span className={task.status === 'delivered' ? 'line-through text-zinc-400' : ''}>
          {task.title}
        </span>
        {task.is_ai_generated && (
          <Badge variant="outline" className="text-[10px] px-1 py-0 bg-purple-50 text-purple-600 border-purple-200">
            AI
          </Badge>
        )}
      </div>
      
      <div className="flex items-center gap-2">
        {task.assigned_to_name && (
          <span className="text-xs text-zinc-500 flex items-center gap-1">
            <User className="w-3 h-3" />
            {task.assigned_to_name}
          </span>
        )}
        
        {/* Status Badge & Change */}
        {permissions.can_manage_tasks ? (
          <Select 
            value={task.status} 
            onValueChange={(v) => onUpdate(task.id, { status: v })}
          >
            <SelectTrigger className="h-6 w-auto border-none p-0">
              <Badge className={`${statusConfig.color} text-[10px]`}>
                {statusConfig.label}
              </Badge>
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TASK_STATUSES).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  <span className={`${config.color} px-2 py-0.5 rounded text-xs`}>
                    {config.label}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Badge className={`${statusConfig.color} text-[10px]`}>
            {statusConfig.label}
          </Badge>
        )}
        
        {/* Proof indicator */}
        {task.proofs?.length > 0 && (
          <Badge variant="outline" className="text-[10px] px-1">
            <FileUp className="w-2.5 h-2.5 mr-0.5" />
            {task.proofs.length}
          </Badge>
        )}
        
        {/* Delete */}
        {permissions.can_edit_sow && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
            onClick={() => onDelete(task.id)}
          >
            <Trash2 className="w-3 h-3 text-red-500" />
          </Button>
        )}
      </div>
    </div>
  );
};

// Main Component
const ProjectSOWDelivery = ({ projectId }) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('scopes');
  
  // Fetch PROJECT_SOW
  const { data, isLoading, error } = useQuery({
    queryKey: ['project-sow', projectId],
    queryFn: async () => {
      const response = await axios.get(`${API}/project-sow-delivery/project/${projectId}`);
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
  
  const projectSow = data?.project_sow;
  const tasks = data?.tasks || [];
  const proofs = data?.proofs || [];
  const permissions = data?.permissions || {};
  
  // Mutations
  const updateScopeMutation = useMutation({
    mutationFn: async ({ scopeId, status }) => {
      await axios.patch(
        `${API}/project-sow-delivery/${projectSow.id}/scope/${scopeId}/status?status=${status}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Scope status updated');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update status');
    }
  });
  
  const createTaskMutation = useMutation({
    mutationFn: async ({ scopeId, taskData }) => {
      await axios.post(`${API}/project-sow-delivery/${projectSow.id}/tasks`, {
        scope_id: scopeId,
        title: taskData.title,
        description: taskData.description
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Task created');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create task');
    }
  });
  
  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, updates }) => {
      await axios.patch(`${API}/project-sow-delivery/${projectSow.id}/tasks/${taskId}`, updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Task updated');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update task');
    }
  });
  
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId) => {
      await axios.delete(`${API}/project-sow-delivery/${projectSow.id}/tasks/${taskId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Task deleted');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to delete task');
    }
  });
  
  // Handlers
  const handleScopeStatusChange = (scopeId, status) => {
    updateScopeMutation.mutate({ scopeId, status });
  };
  
  const handleTaskCreate = (scopeId, taskData) => {
    createTaskMutation.mutate({ scopeId, taskData });
  };
  
  const handleTaskUpdate = (taskId, updates) => {
    updateTaskMutation.mutate({ taskId, updates });
  };
  
  const handleTaskDelete = (taskId) => {
    if (window.confirm('Delete this task?')) {
      deleteTaskMutation.mutate(taskId);
    }
  };
  
  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }
  
  // No PROJECT_SOW yet
  if (!projectSow) {
    return (
      <Card className="border border-zinc-200">
        <CardContent className="py-12 text-center">
          <FileText className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
          <h3 className="text-lg font-medium text-zinc-900 mb-2">No SOW Delivery Created</h3>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            {data?.sow_master_exists ? (
              <>SOW Master exists. Complete the kickoff process to create the delivery layer.</>
            ) : (
              <>No SOW is linked to this project yet. Create SOW in the Sales funnel first.</>
            )}
          </p>
        </CardContent>
      </Card>
    );
  }
  
  // Calculate stats
  const totalScopes = projectSow.scopes?.length || 0;
  const completedScopes = projectSow.scopes?.filter(s => s.status === 'delivered').length || 0;
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'delivered').length;
  const overallProgress = totalScopes > 0 ? (completedScopes / totalScopes) * 100 : 0;
  
  const overallStatusConfig = SOW_STATUSES[projectSow.status] || SOW_STATUSES.open;
  const OverallStatusIcon = overallStatusConfig.icon;
  
  return (
    <div className="space-y-4">
      {/* Header Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider">Overall Status</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge className={`${overallStatusConfig.color}`}>
                    <OverallStatusIcon className="w-3 h-3 mr-1" />
                    {overallStatusConfig.label}
                  </Badge>
                </div>
              </div>
              {projectSow.reopen_count > 0 && (
                <Badge variant="outline" className="text-amber-600">
                  Re-opened {projectSow.reopen_count}x
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card className="border border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Scopes</p>
            <p className="text-2xl font-semibold mt-1">
              {completedScopes}/{totalScopes}
            </p>
            <Progress value={(completedScopes / totalScopes) * 100 || 0} className="h-1.5 mt-2" />
          </CardContent>
        </Card>
        
        <Card className="border border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Tasks</p>
            <p className="text-2xl font-semibold mt-1">
              {completedTasks}/{totalTasks}
            </p>
            <Progress value={(completedTasks / totalTasks) * 100 || 0} className="h-1.5 mt-2" />
          </CardContent>
        </Card>
        
        <Card className="border border-zinc-200">
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Proofs Uploaded</p>
            <p className="text-2xl font-semibold mt-1">{proofs.length}</p>
            <p className="text-xs text-zinc-400 mt-1">SOW-level evidence</p>
          </CardContent>
        </Card>
      </div>
      
      {/* SOW Master Lock Info */}
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-50 rounded-lg text-xs text-zinc-500">
        <Lock className="w-3.5 h-3.5" />
        <span>
          SOW Master is <strong>locked</strong>. This is a delivery copy created from kickoff.
          Original SOW cannot be modified.
        </span>
      </div>
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-zinc-100">
          <TabsTrigger value="scopes" className="text-xs">
            <ClipboardList className="w-3.5 h-3.5 mr-1.5" />
            Scopes ({totalScopes})
          </TabsTrigger>
          <TabsTrigger value="all-tasks" className="text-xs">
            <ListTodo className="w-3.5 h-3.5 mr-1.5" />
            All Tasks ({totalTasks})
          </TabsTrigger>
          <TabsTrigger value="proofs" className="text-xs">
            <FileUp className="w-3.5 h-3.5 mr-1.5" />
            Proofs ({proofs.length})
          </TabsTrigger>
        </TabsList>
        
        {/* Scopes Tab */}
        <TabsContent value="scopes" className="mt-4 space-y-3">
          {projectSow.scopes?.map(scope => (
            <ScopeCard
              key={scope.id}
              scope={scope}
              tasks={tasks}
              onStatusChange={handleScopeStatusChange}
              onTaskCreate={handleTaskCreate}
              onTaskUpdate={handleTaskUpdate}
              onTaskDelete={handleTaskDelete}
              permissions={permissions}
            />
          ))}
        </TabsContent>
        
        {/* All Tasks Tab */}
        <TabsContent value="all-tasks" className="mt-4">
          <Card className="border border-zinc-200">
            <CardContent className="py-4">
              {tasks.length === 0 ? (
                <p className="text-center text-zinc-400 py-8">No tasks created yet</p>
              ) : (
                <div className="space-y-2">
                  {tasks.map(task => {
                    const scope = projectSow.scopes?.find(s => s.id === task.scope_id);
                    return (
                      <div key={task.id} className="flex items-center gap-3 p-2 hover:bg-zinc-50 rounded">
                        <div className="flex-1">
                          <p className="text-sm font-medium">{task.title}</p>
                          <p className="text-xs text-zinc-500">
                            {scope?.name || 'General'} • {task.assigned_to_name || 'Unassigned'}
                          </p>
                        </div>
                        <Badge className={TASK_STATUSES[task.status]?.color || 'bg-zinc-100'}>
                          {TASK_STATUSES[task.status]?.label || task.status}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Proofs Tab */}
        <TabsContent value="proofs" className="mt-4">
          <Card className="border border-zinc-200">
            <CardContent className="py-4">
              {proofs.length === 0 ? (
                <div className="text-center py-8">
                  <FileUp className="w-8 h-8 mx-auto text-zinc-300 mb-2" />
                  <p className="text-zinc-400">No proofs uploaded yet</p>
                  <p className="text-xs text-zinc-400 mt-1">
                    Upload evidence for SOW or individual tasks
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {proofs.map(proof => (
                    <div key={proof.id} className="flex items-center justify-between p-2 bg-zinc-50 rounded">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-zinc-400" />
                        <div>
                          <p className="text-sm">{proof.file_name}</p>
                          <p className="text-xs text-zinc-500">
                            v{proof.version} • {proof.uploaded_by_name}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <a href={proof.file_url} target="_blank" rel="noopener noreferrer">
                          <Download className="w-4 h-4" />
                        </a>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ProjectSOWDelivery;
