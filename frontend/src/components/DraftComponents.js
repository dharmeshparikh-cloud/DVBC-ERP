/**
 * Draft UI Components
 * 
 * Components for the Universal Auto-Save & Resume System:
 * - SaveIndicator: Shows saving status with timestamp
 * - ResumeModal: Resume/Discard/Cancel dialog
 * - LoginResumeBanner: "Continue where you left off?" banner
 * - ConflictWarning: Version conflict warning
 * - useAutoSave: Hook for easy auto-save integration
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { useDraft } from '../contexts/DraftContext';
import { useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Cloud, CloudOff, Check, Loader2, AlertTriangle, 
  FileText, ArrowRight, X, RefreshCw, Clock 
} from 'lucide-react';

// ============== Save Indicator ==============

export const SaveIndicator = ({ className = '' }) => {
  const { saveStatus, lastSaved } = useDraft();
  
  const formatTime = (date) => {
    if (!date) return '';
    return new Date(date).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  const getStatusContent = () => {
    switch (saveStatus) {
      case 'saving':
        return (
          <>
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            <span className="text-blue-600">Saving...</span>
          </>
        );
      case 'saved':
        return (
          <>
            <Check className="h-4 w-4 text-green-500" />
            <span className="text-green-600">
              Saved {lastSaved && `at ${formatTime(lastSaved)}`}
            </span>
          </>
        );
      case 'error':
        return (
          <>
            <CloudOff className="h-4 w-4 text-red-500" />
            <span className="text-red-600">Save failed</span>
          </>
        );
      default:
        return (
          <>
            <Cloud className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500">Auto-save enabled</span>
          </>
        );
    }
  };
  
  return (
    <div 
      className={`flex items-center gap-2 text-sm transition-all duration-200 ${className}`}
      data-testid="save-indicator"
    >
      {getStatusContent()}
    </div>
  );
};

// ============== Resume Modal ==============

export const ResumeModal = () => {
  const { 
    showResumeModal, 
    pendingDraft, 
    resumeDraft, 
    discardDraft, 
    cancelResume,
    getModuleName 
  } = useDraft();
  
  if (!showResumeModal || !pendingDraft) return null;
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString([], { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  return (
    <Dialog open={showResumeModal} onOpenChange={cancelResume}>
      <DialogContent className="sm:max-w-md" data-testid="resume-modal">
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
            <span className="text-sm font-medium">Module</span>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {getModuleName(pendingDraft.module)}
            </span>
          </div>
          {pendingDraft.title && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Title</span>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {pendingDraft.title}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Last saved</span>
            <span className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDate(pendingDraft.last_saved_at || pendingDraft.updated_at)}
            </span>
          </div>
          {pendingDraft.active_tab && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Tab/Step</span>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {pendingDraft.active_tab}
              </span>
            </div>
          )}
        </div>
        
        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={cancelResume}
            data-testid="resume-cancel-btn"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => discardDraft(pendingDraft.id)}
            data-testid="resume-discard-btn"
          >
            Discard
          </Button>
          <Button
            onClick={() => resumeDraft(pendingDraft)}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="resume-continue-btn"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Resume
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============== Login Resume Banner ==============

export const LoginResumeBanner = () => {
  const { 
    showLoginBanner, 
    latestDraft, 
    resumeDraft, 
    dismissLoginBanner,
    getModuleName 
  } = useDraft();
  
  if (!showLoginBanner || !latestDraft) return null;
  
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
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };
  
  return (
    <div 
      className="fixed top-16 left-0 right-0 z-50 mx-4 md:mx-auto md:max-w-2xl"
      data-testid="login-resume-banner"
    >
      <Alert className="bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 shadow-lg">
        <FileText className="h-4 w-4 text-blue-600" />
        <AlertDescription className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex-1">
            <span className="font-medium text-blue-800 dark:text-blue-200">
              Continue where you left off?
            </span>
            <span className="text-blue-600 dark:text-blue-300 ml-2 text-sm">
              {getModuleName(latestDraft.module)} • {formatDate(latestDraft.last_saved_at || latestDraft.updated_at)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={dismissLoginBanner}
              className="text-blue-600 hover:text-blue-800"
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={() => resumeDraft(latestDraft)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Resume
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
};

// ============== Conflict Warning ==============

export const ConflictWarning = ({ onRefresh, onOverwrite }) => {
  const { conflictWarning, setConflictWarning } = useDraft();
  
  if (!conflictWarning) return null;
  
  return (
    <div 
      className="fixed bottom-4 right-4 z-50 max-w-sm"
      data-testid="conflict-warning"
    >
      <Alert className="bg-yellow-50 dark:bg-yellow-900/30 border-yellow-300 shadow-lg">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <AlertDescription className="space-y-3">
          <p className="font-medium text-yellow-800 dark:text-yellow-200">
            Version Conflict Detected
          </p>
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            This draft was updated in another tab. Your version: {conflictWarning.clientVersion}, 
            Server version: {conflictWarning.serverVersion}
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setConflictWarning(null);
                onRefresh?.();
              }}
              className="text-yellow-700 border-yellow-400"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setConflictWarning(null);
                onOverwrite?.();
              }}
              className="bg-yellow-600 hover:bg-yellow-700 text-white"
            >
              Overwrite
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
};

// ============== useAutoSave Hook ==============

/**
 * Hook for easy auto-save integration in any form
 * 
 * Usage:
 * const { triggerSave, triggerImmediateSave, isLoading, error } = useAutoSave({
 *   module: 'leads',
 *   route: '/leads/new',
 *   entityId: leadId,
 *   getFormData: () => ({ ...formState }),
 *   getActiveTab: () => currentTab,
 *   onResume: (draft) => setFormState(draft.form_data)
 * });
 */
export const useAutoSave = ({
  module,
  route,
  entityId = null,
  title = '',
  getFormData,
  getActiveTab = () => null,
  getMetadata = () => ({}),
  onResume = null,
  enabled = true,
  checkOnMount = true
}) => {
  const location = useLocation();
  const { 
    autoSave, 
    saveImmediate, 
    checkForDraft, 
    currentDraft,
    saveStatus,
    completeDraft,
    pendingDraft,
    resumeDraft
  } = useDraft();
  
  const currentRoute = route || location.pathname;
  const hasCheckedRef = useRef(false);
  
  // Check for existing draft on mount
  useEffect(() => {
    if (enabled && checkOnMount && !hasCheckedRef.current && module) {
      hasCheckedRef.current = true;
      checkForDraft(module, currentRoute, entityId);
    }
  }, [enabled, checkOnMount, module, currentRoute, entityId, checkForDraft]);
  
  // Handle resume callback
  useEffect(() => {
    if (pendingDraft && onResume) {
      // This will be called when user clicks Resume in the modal
    }
  }, [pendingDraft, onResume]);
  
  // Trigger auto-save (debounced)
  const triggerSave = useCallback(() => {
    if (!enabled || !module) return;
    
    const formData = getFormData();
    if (!formData || Object.keys(formData).length === 0) return;
    
    autoSave({
      module,
      route: currentRoute,
      entity_id: entityId,
      title,
      active_tab: getActiveTab(),
      form_data: formData,
      metadata: getMetadata()
    });
  }, [enabled, module, currentRoute, entityId, title, getFormData, getActiveTab, getMetadata, autoSave]);
  
  // Trigger immediate save (for blur, tab change, route exit)
  const triggerImmediateSave = useCallback(async () => {
    if (!enabled || !module) return;
    
    const formData = getFormData();
    if (!formData || Object.keys(formData).length === 0) return;
    
    return saveImmediate({
      module,
      route: currentRoute,
      entity_id: entityId,
      title,
      active_tab: getActiveTab(),
      form_data: formData,
      metadata: getMetadata()
    });
  }, [enabled, module, currentRoute, entityId, title, getFormData, getActiveTab, getMetadata, saveImmediate]);
  
  // Handle form submission success
  const handleSubmitSuccess = useCallback(async () => {
    if (currentDraft?.id) {
      await completeDraft(currentDraft.id);
    }
  }, [currentDraft, completeDraft]);
  
  // Handle resume
  const handleResume = useCallback(() => {
    const draft = resumeDraft(pendingDraft);
    if (draft && onResume) {
      onResume(draft);
    }
    return draft;
  }, [pendingDraft, resumeDraft, onResume]);
  
  return {
    triggerSave,
    triggerImmediateSave,
    handleSubmitSuccess,
    handleResume,
    isLoading: saveStatus === 'saving',
    isSaved: saveStatus === 'saved',
    hasError: saveStatus === 'error',
    currentDraft,
    pendingDraft
  };
};

export default {
  SaveIndicator,
  ResumeModal,
  LoginResumeBanner,
  ConflictWarning,
  useAutoSave
};
