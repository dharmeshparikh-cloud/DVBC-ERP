/**
 * Draft UI Components for Universal Auto-Save & Resume System
 * 
 * These components work with the useDraft hook to provide:
 * - DraftSaveIndicator: Shows saving status with timestamp
 * - DraftResumeDialog: Resume/Discard/Cancel dialog
 * - DraftSelector: Dropdown to select from saved drafts
 */

import React from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { 
  Cloud, CloudOff, Check, Loader2, 
  FileText, RefreshCw, Clock, Trash2 
} from 'lucide-react';

// ============== Save Indicator ==============

export const DraftSaveIndicator = ({ 
  saving, 
  lastSaved, 
  saveStatus = 'idle',
  className = '' 
}) => {
  const formatTime = (date) => {
    if (!date) return '';
    const d = date instanceof Date ? date : new Date(date);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusContent = () => {
    if (saving || saveStatus === 'saving') {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          <span className="text-blue-600 dark:text-blue-400">Saving...</span>
        </>
      );
    }
    
    if (saveStatus === 'saved' || lastSaved) {
      return (
        <>
          <Check className="h-4 w-4 text-green-500" />
          <span className="text-green-600 dark:text-green-400">
            {saveStatus === 'saved' ? 'Saved' : `Saved ${formatTime(lastSaved)}`}
          </span>
        </>
      );
    }
    
    if (saveStatus === 'error') {
      return (
        <>
          <CloudOff className="h-4 w-4 text-red-500" />
          <span className="text-red-600 dark:text-red-400">Save failed</span>
        </>
      );
    }
    
    return (
      <>
        <Cloud className="h-4 w-4 text-gray-400" />
        <span className="text-gray-500 dark:text-gray-400">Auto-save enabled</span>
      </>
    );
  };

  return (
    <div 
      className={`flex items-center gap-2 text-sm transition-all duration-200 ${className}`}
      data-testid="draft-save-indicator"
    >
      {getStatusContent()}
    </div>
  );
};

// ============== Resume Dialog ==============

export const DraftResumeDialog = ({
  open,
  draft,
  onResume,
  onDiscard,
  onCancel,
  moduleName = 'Form'
}) => {
  if (!open || !draft) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  return (
    <Dialog open={open} onOpenChange={onCancel}>
      <DialogContent className="sm:max-w-md" data-testid="draft-resume-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-500" />
            Resume Previous Work?
          </DialogTitle>
          <DialogDescription>
            You have unsaved work from a previous session.
          </DialogDescription>
        </DialogHeader>
        
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Type</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {moduleName}
            </span>
          </div>
          {draft.title && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Title</span>
              <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
                {draft.title}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Last saved</span>
            <span className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDate(draft.last_saved_at || draft.updated_at)}
            </span>
          </div>
          {draft.active_tab && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Tab/Step</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {draft.active_tab}
              </span>
            </div>
          )}
        </div>
        
        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={onCancel}
            data-testid="draft-cancel-btn"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onDiscard}
            data-testid="draft-discard-btn"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Discard
          </Button>
          <Button
            onClick={onResume}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="draft-resume-btn"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Resume
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============== Draft Selector ==============

export const DraftSelector = ({
  drafts = [],
  loading = false,
  selectedId,
  onSelect,
  onDelete,
  placeholder = "Select a draft",
  className = ''
}) => {
  if (drafts.length === 0 && !loading) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString([], { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Select 
        value={selectedId || ''} 
        onValueChange={onSelect}
        disabled={loading}
      >
        <SelectTrigger className="w-[250px]" data-testid="draft-selector">
          <SelectValue placeholder={loading ? "Loading drafts..." : placeholder} />
        </SelectTrigger>
        <SelectContent>
          {drafts.map((draft) => (
            <SelectItem key={draft.id} value={draft.id}>
              <div className="flex items-center justify-between w-full">
                <span className="truncate max-w-[150px]">{draft.title || 'Untitled Draft'}</span>
                <span className="text-xs text-gray-400 ml-2">
                  {formatDate(draft.updated_at)}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      {selectedId && onDelete && (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(selectedId)}
          className="text-red-500 hover:text-red-700 hover:bg-red-50"
          data-testid="draft-delete-btn"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
};

// ============== Draft Status Badge ==============

export const DraftStatusBadge = ({ hasDraft, onClick }) => {
  if (!hasDraft) return null;
  
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700 hover:bg-amber-200 transition-colors"
      data-testid="draft-status-badge"
    >
      <FileText className="h-3 w-3" />
      Draft Available
    </button>
  );
};

export default {
  DraftSaveIndicator,
  DraftResumeDialog,
  DraftSelector,
  DraftStatusBadge
};
