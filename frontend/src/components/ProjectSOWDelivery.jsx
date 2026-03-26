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

import React, { useState, useRef, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API, AuthContext } from '../App';
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
  ListTodo, ClipboardList, User, Calendar, FileUp, Loader2,
  ThumbsUp, ThumbsDown, AlertTriangle, Eye
} from 'lucide-react';

// Manager roles that can approve NA requests
const MANAGER_ROLES = ['admin', 'hr_admin', 'principal_consultant', 'manager'];

// Status configurations
const SOW_STATUSES = {
  open: { label: 'Open', color: 'bg-zinc-100 text-zinc-700', icon: Clock },
  wip: { label: 'Work In Progress', color: 'bg-blue-100 text-blue-700', icon: Play },
  blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700', icon: AlertCircle },
  implemented: { label: 'Implemented', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  na_pending: { label: 'NA Pending Approval', color: 'bg-amber-100 text-amber-700', icon: Clock },
  not_applicable: { label: 'Not Applicable', color: 'bg-zinc-100 text-zinc-500', icon: Pause },
  reopen: { label: 'Re-Opened', color: 'bg-amber-100 text-amber-700', icon: RotateCcw }
};

// Statuses consultants can select (excludes not_applicable which needs approval)
const CONSULTANT_ALLOWED_STATUSES = ['open', 'wip', 'implemented', 'na_pending', 'reopen'];
// Statuses managers can select (includes not_applicable)
const MANAGER_ALLOWED_STATUSES = ['open', 'wip', 'implemented', 'not_applicable', 'reopen'];

const TASK_STATUSES = {
  open: { label: 'Open', color: 'bg-zinc-100 text-zinc-700' },
  wip: { label: 'WIP', color: 'bg-blue-100 text-blue-700' },
  implemented: { label: 'Implemented', color: 'bg-emerald-100 text-emerald-700' },
  blocked: { label: 'Blocked', color: 'bg-red-100 text-red-700' }
};

// Scope Card Component
const ScopeCard = ({ 
  scope, 
  tasks, 
  onStatusChange,
  onStartDateChange,
  onTaskCreate, 
  onTaskUpdate, 
  onTaskDelete,
  onAIGenerateTasks,
  onUploadProof,
  onRequestNA,
  permissions,
  isGeneratingTasks,
  uploadingTaskId,
  isManager
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [showTaskDialog, setShowTaskDialog] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: '', description: '' });
  
  const scopeTasks = tasks.filter(t => t.scope_id === scope.id);
  const completedTasks = scopeTasks.filter(t => t.status === 'delivered').length;
  const progress = scopeTasks.length > 0 ? (completedTasks / scopeTasks.length) * 100 : 0;
  
  const statusConfig = SOW_STATUSES[scope.status] || SOW_STATUSES.open;
  const StatusIcon = statusConfig.icon;
  
  // Calculate days taken
  const calculateDays = () => {
    if (!scope.start_date) return '-';
    const start = new Date(scope.start_date);
    const end = scope.end_date ? new Date(scope.end_date) : new Date();
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    return days;
  };
  
  const handleCreateTask = () => {
    if (!taskForm.title.trim()) {
      toast.error('Task title is required');
      return;
    }
    onTaskCreate(scope.id, taskForm);
    setTaskForm({ title: '', description: '' });
    setShowTaskDialog(false);
  };
  
  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  };
  
  return (
    <Card className="border border-zinc-200">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-zinc-50/50 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-medium">{scope.name}</CardTitle>
                    {scope.is_inherited && (
                      <Badge variant="outline" className="text-[10px] px-1 py-0">
                        <Lock className="w-2.5 h-2.5 mr-0.5" /> Inherited
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {scope.category_name || scope.domain}
                    {scope.assigned_consultant_name && ` • ${scope.assigned_consultant_name}`}
                  </p>
                </div>
              </div>
              
              {/* Dates & Status Row */}
              <div className="flex items-center gap-4">
                {/* Start Date */}
                <div className="text-center">
                  <p className="text-[10px] text-zinc-400 uppercase">Start</p>
                  {permissions.can_manage_tasks && !scope.start_date ? (
                    <input
                      type="date"
                      className="text-xs border rounded px-1 py-0.5 w-24"
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        e.stopPropagation();
                        onStartDateChange(scope.id, 'start_date', e.target.value);
                      }}
                    />
                  ) : (
                    <p className="text-xs font-medium">{formatDate(scope.start_date)}</p>
                  )}
                </div>
                
                {/* End Date */}
                <div className="text-center">
                  <p className="text-[10px] text-zinc-400 uppercase">End</p>
                  <p className="text-xs font-medium">
                    {scope.status === 'implemented' ? formatDate(scope.end_date) : '-'}
                  </p>
                </div>
                
                {/* Days Taken */}
                <div className="text-center w-12">
                  <p className="text-[10px] text-zinc-400 uppercase">Days</p>
                  <p className="text-xs font-medium">
                    {scope.start_date ? calculateDays() : '-'}
                  </p>
                </div>
                
                {/* Progress */}
                <div className="w-20 flex items-center gap-1">
                  <Progress value={progress} className="h-1.5 flex-1" />
                  <span className="text-[10px] text-zinc-500 w-6">{Math.round(progress)}%</span>
                </div>
                
                {/* Status */}
                <Badge className={`${statusConfig.color} text-xs min-w-[80px] justify-center`}>
                  <StatusIcon className="w-3 h-3 mr-1" />
                  {statusConfig.label}
                </Badge>
                
                {/* Status Change - Only show allowed statuses based on role */}
                {permissions.can_manage_tasks && (
                  <Select 
                    value={scope.status} 
                    onValueChange={(v) => onStatusChange(scope.id, v)}
                  >
                    <SelectTrigger className="w-8 h-8 p-0 border-none" onClick={(e) => e.stopPropagation()}>
                      <Edit2 className="w-3 h-3" />
                    </SelectTrigger>
                    <SelectContent>
                      {(isManager ? MANAGER_ALLOWED_STATUSES : CONSULTANT_ALLOWED_STATUSES).map(key => {
                        const config = SOW_STATUSES[key];
                        if (!config) return null;
                        return (
                          <SelectItem key={key} value={key}>
                            <span className={`${config.color} px-2 py-0.5 rounded text-xs`}>
                              {config.label}
                            </span>
                          </SelectItem>
                        );
                      })}
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
                  <div className="flex items-center gap-1">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-6 text-xs text-purple-600 hover:text-purple-700 hover:bg-purple-50"
                      onClick={() => onAIGenerateTasks(scope.id)}
                      disabled={isGeneratingTasks}
                    >
                      {isGeneratingTasks ? (
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      ) : (
                        <span className="mr-1">✨</span>
                      )}
                      AI Suggest
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-6 text-xs"
                      onClick={() => setShowTaskDialog(true)}
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Add Task
                    </Button>
                  </div>
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
                      onUploadProof={onUploadProof}
                      permissions={permissions}
                      isUploading={uploadingTaskId === task.id}
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

// Task Row Component with Proof Upload
const TaskRow = ({ task, onUpdate, onDelete, onUploadProof, permissions, isUploading }) => {
  const statusConfig = TASK_STATUSES[task.status] || TASK_STATUSES.open;
  const fileInputRef = useRef(null);
  
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadProof(task.id, file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  return (
    <div className="flex items-center justify-between p-2 bg-zinc-50 rounded text-sm group">
      <div className="flex items-center gap-2 flex-1">
        <ListTodo className="w-3.5 h-3.5 text-zinc-400" />
        <span className={task.status === 'implemented' ? 'line-through text-zinc-400' : ''}>
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
        
        {/* Proof upload button */}
        {permissions.can_manage_tasks && (
          <>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              className="hidden"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-zinc-400 hover:text-emerald-600"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              title="Upload proof"
            >
              {isUploading ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Upload className="w-3 h-3" />
              )}
            </Button>
          </>
        )}
        
        {/* Proof indicator */}
        {task.proofs?.length > 0 && (
          <Badge variant="outline" className="text-[10px] px-1 bg-emerald-50 text-emerald-600 border-emerald-200">
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

// Scope Table Row Component - Clean inline table view matching Sales SOW
const ScopeTableRow = ({ 
  index, 
  scope, 
  tasks,
  onStatusChange,
  onStartDateChange,
  onUploadProof,
  onUpdateDeliverables,
  uploadingTaskId,
  permissions,
  isManager,
  proofs = []
}) => {
  const [editingDeliverables, setEditingDeliverables] = useState(false);
  const [deliverables, setDeliverables] = useState(scope.deliverables || '');
  const [showProofModal, setShowProofModal] = useState(false);
  const fileInputRef = useRef(null);
  
  const scopeTasks = tasks.filter(t => t.scope_id === scope.id);
  
  // Get scope-level proofs
  const scopeProofs = proofs.filter(p => p.scope_id === scope.id && !p.task_id);
  
  // Calculate days taken
  const calculateDays = () => {
    if (!scope.start_date) return '-';
    const start = new Date(scope.start_date);
    const end = scope.end_date ? new Date(scope.end_date) : new Date();
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    return days;
  };
  
  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  };
  
  // Format date for input
  const formatDateInput = (dateStr) => {
    if (!dateStr) return '';
    return dateStr.substring(0, 10);
  };
  
  const statusConfig = SOW_STATUSES[scope.status] || SOW_STATUSES.open;
  const StatusIcon = statusConfig.icon;
  
  // Get available statuses based on role and current status
  const getAvailableStatuses = () => {
    const baseStatuses = ['open', 'wip', 'blocked', 'na_pending', 'implemented', 'reopen'];
    if (isManager) {
      return [...baseStatuses, 'not_applicable'];
    }
    return baseStatuses;
  };
  
  // Check if status change is valid
  const handleStatusChange = (newStatus) => {
    // Require proof for "implemented" status
    if (newStatus === 'implemented' && scopeProofs.length === 0) {
      toast.error('Please upload at least one proof before marking as Implemented');
      return;
    }
    // Require start date for WIP or implemented
    if ((newStatus === 'wip' || newStatus === 'implemented') && !scope.start_date) {
      toast.error('Please set a start date first');
      return;
    }
    onStatusChange(scope.id, newStatus);
  };
  
  // Handle file upload for proof
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    await onUploadProof(null, scope.id, file);
    e.target.value = ''; // Reset input
  };
  
  // Handle deliverables save
  const handleSaveDeliverables = () => {
    if (onUpdateDeliverables) {
      onUpdateDeliverables(scope.id, deliverables);
    }
    setEditingDeliverables(false);
    toast.success('Deliverables updated');
  };
  
  // Get file type icon
  const getFileIcon = (filename) => {
    const ext = filename?.split('.').pop()?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return '🖼️';
    if (['pdf'].includes(ext)) return '📄';
    if (['doc', 'docx'].includes(ext)) return '📝';
    if (['xls', 'xlsx'].includes(ext)) return '📊';
    return '📎';
  };
  
  // Check if file is an image (for preview)
  const isImageFile = (filename) => {
    const ext = filename?.split('.').pop()?.toLowerCase();
    return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
  };
  
  return (
    <>
      <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-zinc-50 group border-b border-zinc-100" data-testid={`scope-row-${scope.id}`}>
        {/* # */}
        <div className="col-span-1 text-xs text-zinc-400 font-medium">{index + 1}</div>
        
        {/* Category */}
        <div className="col-span-1">
          <Badge variant="secondary" className="text-[10px] px-1.5 whitespace-nowrap">
            {scope.category_name || scope.category || 'General'}
          </Badge>
        </div>
        
        {/* Scope Name */}
        <div className="col-span-2">
          <p className="text-sm font-medium text-zinc-800">{scope.name}</p>
          {scopeTasks.length > 0 && (
            <p className="text-[10px] text-zinc-400 mt-0.5">{scopeTasks.length} tasks</p>
          )}
        </div>
        
        {/* Deliverables - Editable */}
        <div className="col-span-2">
          {editingDeliverables ? (
            <div className="flex items-center gap-1">
              <Input
                value={deliverables}
                onChange={(e) => setDeliverables(e.target.value)}
                className="h-7 text-xs"
                placeholder="Comma-separated deliverables"
                autoFocus
              />
              <Button size="sm" className="h-7 w-7 p-0" onClick={handleSaveDeliverables}>
                <CheckCircle className="w-3 h-3" />
              </Button>
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setEditingDeliverables(false)}>
                <AlertCircle className="w-3 h-3" />
              </Button>
            </div>
          ) : (
            <div 
              className={`text-xs text-zinc-600 line-clamp-2 ${permissions.can_edit_sow ? 'cursor-pointer hover:text-zinc-900 hover:bg-zinc-100 rounded px-1 -mx-1' : ''}`}
              onClick={() => permissions.can_edit_sow && setEditingDeliverables(true)}
              title={scope.deliverables || 'Click to add deliverables'}
            >
              {scope.deliverables || <span className="text-zinc-400 italic">Click to add</span>}
            </div>
          )}
        </div>
        
        {/* Start Date */}
        <div className="col-span-1 text-center">
          {permissions.can_edit_sow ? (
            <Input
              type="date"
              value={formatDateInput(scope.start_date)}
              onChange={(e) => onStartDateChange(scope.id, 'start_date', e.target.value)}
              className="h-6 text-[10px] px-1 w-full"
            />
          ) : (
            <span className="text-xs">{formatDate(scope.start_date)}</span>
          )}
        </div>
        
        {/* End Date */}
        <div className="col-span-1 text-center">
          <span className="text-xs text-zinc-500">
            {scope.status === 'implemented' && scope.end_date ? formatDate(scope.end_date) : '-'}
          </span>
        </div>
        
        {/* Days */}
        <div className="col-span-1 text-center">
          <span className={`text-xs font-medium ${scope.status === 'implemented' ? 'text-emerald-600' : ''}`}>
            {calculateDays()}
          </span>
        </div>
        
        {/* Status */}
        <div className="col-span-1">
          <Select
            value={scope.status || 'open'}
            onValueChange={handleStatusChange}
            disabled={!permissions.can_edit_sow}
          >
            <SelectTrigger className={`h-7 text-[10px] px-2 ${statusConfig.color} border-0`}>
              <div className="flex items-center gap-1">
                <StatusIcon className="w-3 h-3" />
                <SelectValue />
              </div>
            </SelectTrigger>
            <SelectContent>
              {getAvailableStatuses().map(status => {
                const config = SOW_STATUSES[status];
                const Icon = config?.icon || Clock;
                return (
                  <SelectItem key={status} value={status} className="text-xs">
                    <div className="flex items-center gap-2">
                      <Icon className="w-3 h-3" />
                      {config?.label || status}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>
        
        {/* Actions - Proof Upload & View */}
        <div className="col-span-2 flex items-center justify-end gap-1">
          {/* View Proofs button (if proofs exist) */}
          {scopeProofs.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-6 px-2 text-[10px] bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
              onClick={() => setShowProofModal(true)}
            >
              <Eye className="w-3 h-3 mr-1" />
              View ({scopeProofs.length})
            </Button>
          )}
          
          {/* Upload proof */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls"
          />
          {permissions.can_edit_sow && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-[10px]"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingTaskId === scope.id}
            >
              {uploadingTaskId === scope.id ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <>
                  <Upload className="w-3 h-3 mr-1" />
                  Upload
                </>
              )}
            </Button>
          )}
        </div>
      </div>
      
      {/* Proof View Modal */}
      <Dialog open={showProofModal} onOpenChange={setShowProofModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Proofs for: {scope.name}
            </DialogTitle>
            <DialogDescription>
              {scopeProofs.length} proof(s) uploaded for this scope
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {scopeProofs.map((proof, idx) => (
              <div 
                key={proof.id || idx} 
                className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg border border-zinc-200"
              >
                {/* Preview for images */}
                {isImageFile(proof.file_name) && proof.file_url ? (
                  <img 
                    src={proof.file_url} 
                    alt={proof.file_name}
                    className="w-16 h-16 object-cover rounded border"
                  />
                ) : (
                  <div className="w-16 h-16 flex items-center justify-center bg-zinc-100 rounded border text-2xl">
                    {getFileIcon(proof.file_name)}
                  </div>
                )}
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{proof.file_name || 'Proof file'}</p>
                  <p className="text-xs text-zinc-500">
                    Uploaded {proof.uploaded_at ? new Date(proof.uploaded_at).toLocaleDateString() : 'recently'}
                    {proof.uploaded_by_name && ` by ${proof.uploaded_by_name}`}
                  </p>
                  {proof.notes && (
                    <p className="text-xs text-zinc-600 mt-1">{proof.notes}</p>
                  )}
                </div>
                
                <div className="flex items-center gap-2">
                  {/* View in new tab */}
                  {proof.file_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8"
                      onClick={() => window.open(proof.file_url, '_blank')}
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" />
                      View
                    </Button>
                  )}
                  {/* Download */}
                  {proof.file_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = proof.file_url;
                        link.download = proof.file_name || 'proof';
                        link.click();
                      }}
                    >
                      <Download className="w-3.5 h-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            
            {scopeProofs.length === 0 && (
              <div className="text-center py-8 text-zinc-400">
                <FileUp className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No proofs uploaded yet</p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProofModal(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

// Main Component
const ProjectSOWDelivery = ({ projectId }) => {
  const queryClient = useQueryClient();
  const { user } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('scopes');
  
  // Check if current user is a manager who can approve NA requests
  const isManager = user?.role && MANAGER_ROLES.includes(user.role);
  
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
  
  // Get scopes pending NA approval
  const pendingNAScopes = projectSow?.scopes?.filter(s => s.status === 'na_pending') || [];
  
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
  
  // Update Scope Date Mutation
  const updateScopeDateMutation = useMutation({
    mutationFn: async ({ scopeId, field, value }) => {
      await axios.patch(
        `${API}/project-sow-delivery/${projectSow.id}/scope/${scopeId}/date`,
        { field, value }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Date updated');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update date');
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
  
  // AI Generate Tasks Mutation
  const [generatingScopeId, setGeneratingScopeId] = useState(null);
  const aiGenerateTasksMutation = useMutation({
    mutationFn: async (scopeId) => {
      const response = await axios.post(
        `${API}/project-sow-delivery/${projectSow.id}/scope/${scopeId}/ai-generate-tasks`
      );
      return response.data;
    },
    onMutate: (scopeId) => {
      setGeneratingScopeId(scopeId);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success(`Generated ${data.tasks?.length || 0} AI-suggested tasks`);
      setGeneratingScopeId(null);
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to generate tasks');
      setGeneratingScopeId(null);
    }
  });
  
  // Handlers
  const handleScopeStatusChange = (scopeId, status) => {
    updateScopeMutation.mutate({ scopeId, status });
  };
  
  const handleScopeDateChange = (scopeId, field, value) => {
    updateScopeDateMutation.mutate({ scopeId, field, value });
  };
  
  const handleAIGenerateTasks = (scopeId) => {
    aiGenerateTasksMutation.mutate(scopeId);
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
  
  // NA Approval Mutation (Manager only)
  const approveNAMutation = useMutation({
    mutationFn: async ({ scopeId, approve }) => {
      const response = await axios.post(
        `${API}/project-sow-delivery/${projectSow.id}/scope/${scopeId}/approve-na?approve=${approve}`
      );
      return response.data;
    },
    onSuccess: (data, { approve }) => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success(approve ? 'Scope marked as Not Applicable' : 'NA request rejected');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to process NA request');
    }
  });
  
  const handleApproveNA = (scopeId, approve) => {
    if (window.confirm(approve 
      ? 'Are you sure you want to mark this scope as Not Applicable?' 
      : 'Are you sure you want to reject this request?'
    )) {
      approveNAMutation.mutate({ scopeId, approve });
    }
  };
  
  // Proof Upload Mutation - Supports both task and scope proofs
  const [uploadingTaskId, setUploadingTaskId] = useState(null);
  const uploadProofMutation = useMutation({
    mutationFn: async ({ taskId, scopeId, file }) => {
      // First upload file to storage
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadResponse = await axios.post(
        `${API}/storage/upload?folder=proofs`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      const fileData = uploadResponse.data.file;
      
      // Determine entity type and id based on whether taskId or scopeId is provided
      let entity_type, entity_id;
      if (taskId) {
        entity_type = 'task';
        entity_id = taskId;
      } else if (scopeId) {
        entity_type = 'scope';
        entity_id = scopeId;
      } else {
        entity_type = 'project_sow';
        entity_id = projectSow.id;
      }
      
      // Register proof with SOW
      const proofResponse = await axios.post(`${API}/project-sow-delivery/proofs`, {
        entity_type,
        entity_id,
        project_sow_id: projectSow.id,
        scope_id: scopeId || null,
        task_id: taskId || null,
        file_url: fileData.file_url,
        file_name: fileData.original_filename,
        file_type: fileData.content_type,
        file_size: fileData.size
      });
      
      return proofResponse.data;
    },
    onMutate: ({ taskId, scopeId }) => {
      setUploadingTaskId(taskId || scopeId); // Track which item is uploading
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('Proof uploaded successfully');
    },
    onSettled: () => {
      setUploadingTaskId(null);
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to upload proof');
    }
  });
  
  // SOW-level proof upload
  const [uploadingSOWProof, setUploadingSOWProof] = useState(false);
  const uploadSOWProofMutation = useMutation({
    mutationFn: async (file) => {
      // First upload file to storage
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadResponse = await axios.post(
        `${API}/storage/upload?folder=proofs`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      const fileData = uploadResponse.data.file;
      
      // Then register proof with SOW
      const proofResponse = await axios.post(`${API}/project-sow-delivery/proofs`, {
        entity_type: 'project_sow',
        entity_id: projectSow.id,
        file_url: fileData.file_url,
        file_name: fileData.original_filename,
        file_type: fileData.content_type,
        file_size: fileData.size
      });
      
      return proofResponse.data;
    },
    onMutate: () => {
      setUploadingSOWProof(true);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['project-sow', projectId]);
      toast.success('SOW proof uploaded successfully');
      setUploadingSOWProof(false);
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to upload proof');
      setUploadingSOWProof(false);
    }
  });
  
  // Handler for uploading proofs (supports task or scope level)
  const handleUploadProof = (taskId, scopeId, file) => {
    uploadProofMutation.mutate({ taskId, scopeId, file });
  };
  
  const handleUploadSOWProof = (file) => {
    uploadSOWProofMutation.mutate(file);
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
      
      {/* Pending NA Approvals Section - Only visible to managers */}
      {isManager && pendingNAScopes.length > 0 && (
        <Card className="border border-amber-200 bg-amber-50">
          <CardHeader className="py-3 border-b border-amber-200">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <CardTitle className="text-sm font-medium text-amber-800">
                Pending "Not Applicable" Approvals ({pendingNAScopes.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="py-3">
            <div className="space-y-2">
              {pendingNAScopes.map(scope => (
                <div 
                  key={scope.id} 
                  className="flex items-center justify-between p-3 bg-white rounded-lg border border-amber-100"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{scope.name}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">
                      {scope.category_name} • Requested by: {scope.na_requested_by_name || 'Consultant'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs border-red-200 text-red-600 hover:bg-red-50"
                      onClick={() => handleApproveNA(scope.id, false)}
                      disabled={approveNAMutation.isPending}
                    >
                      <ThumbsDown className="w-3 h-3 mr-1" />
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => handleApproveNA(scope.id, true)}
                      disabled={approveNAMutation.isPending}
                    >
                      <ThumbsUp className="w-3 h-3 mr-1" />
                      Approve NA
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
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
        
        {/* Scopes Tab - Table View matching Sales SOW */}
        <TabsContent value="scopes" className="mt-4">
          <Card className="border border-zinc-200">
            <CardHeader className="py-3 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <ClipboardList className="w-4 h-4" />
                  Scope of Work ({totalScopes} items)
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-zinc-50 border-b text-xs font-medium text-zinc-600">
                <div className="col-span-1">#</div>
                <div className="col-span-1">Category</div>
                <div className="col-span-2">Scope</div>
                <div className="col-span-2">Deliverables</div>
                <div className="col-span-1 text-center">Start</div>
                <div className="col-span-1 text-center">End</div>
                <div className="col-span-1 text-center">Days</div>
                <div className="col-span-1 text-center">Status</div>
                <div className="col-span-2 text-center">Actions</div>
              </div>

              {/* Table Rows */}
              {projectSow.scopes?.length === 0 ? (
                <div className="text-center py-12 text-zinc-400">
                  <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No scopes defined</p>
                </div>
              ) : (
                <div className="divide-y divide-zinc-100">
                  {projectSow.scopes?.map((scope, idx) => (
                    <ScopeTableRow
                      key={scope.id}
                      index={idx}
                      scope={scope}
                      tasks={tasks}
                      proofs={proofs}
                      onStatusChange={handleScopeStatusChange}
                      onStartDateChange={handleScopeDateChange}
                      onUploadProof={handleUploadProof}
                      uploadingTaskId={uploadingTaskId}
                      permissions={permissions}
                      isManager={isManager}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
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
            <CardHeader className="py-3 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">SOW-Level Proofs</CardTitle>
                {permissions.can_manage_tasks && (
                  <SOWProofUploader 
                    onUpload={handleUploadSOWProof} 
                    isUploading={uploadingSOWProof} 
                  />
                )}
              </div>
            </CardHeader>
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
                  {proofs.map(proof => {
                    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(
                      proof.file_name?.split('.').pop()?.toLowerCase()
                    );
                    return (
                      <div key={proof.id} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                        <div className="flex items-center gap-3">
                          {isImage && proof.file_url ? (
                            <img 
                              src={proof.file_url} 
                              alt={proof.file_name}
                              className="w-10 h-10 object-cover rounded border"
                            />
                          ) : (
                            <div className="w-10 h-10 flex items-center justify-center bg-zinc-100 rounded border">
                              <FileText className="w-5 h-5 text-emerald-500" />
                            </div>
                          )}
                          <div>
                            <p className="text-sm font-medium">{proof.file_name}</p>
                            <p className="text-xs text-zinc-500">
                              v{proof.version} • {proof.uploaded_by_name}
                              {proof.scope_id && ' • Scope proof'}
                              {proof.task_id && ' • Task proof'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {/* View Button */}
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => window.open(proof.file_url, '_blank')}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Button>
                          {/* Download Button */}
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              const link = document.createElement('a');
                              link.href = proof.file_url;
                              link.download = proof.file_name;
                              link.click();
                            }}
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// SOW Proof Uploader Component
const SOWProofUploader = ({ onUpload, isUploading }) => {
  const fileInputRef = useRef(null);
  
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        className="hidden"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif"
      />
      <Button
        variant="outline"
        size="sm"
        className="h-7 text-xs"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        {isUploading ? (
          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
        ) : (
          <Upload className="w-3 h-3 mr-1" />
        )}
        Upload Proof
      </Button>
    </>
  );
};

export default ProjectSOWDelivery;
