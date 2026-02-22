/**
 * DraftContext - Universal Auto-Save & Resume System
 * 
 * Provides system-wide draft persistence for all editable pages.
 * 
 * Features:
 * - Auto-save on field change (debounced ~1.5 sec)
 * - Resume flow with modal (Resume/Discard/Cancel)
 * - Global resume on login ("Continue where you left off?")
 * - Auto-delete on submission/stage completion
 * - Version conflict detection
 * - Audit logging
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';

const DraftContext = createContext();

// Module name mapping for display
const MODULE_NAMES = {
  sales: 'Sales',
  hr: 'HR',
  leads: 'Leads',
  projects: 'Projects',
  consulting: 'Consulting',
  travel: 'Travel',
  expenses: 'Expenses',
  agreements: 'Agreements',
  sow: 'Statement of Work',
  pricing: 'Pricing Plan',
  quotation: 'Quotation',
  onboarding: 'Onboarding',
  employees: 'Employee',
  leaves: 'Leave Request',
  attendance: 'Attendance',
  payroll: 'Payroll',
  general: 'Form'
};

export const DraftProvider = ({ children }) => {
  const { user } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();
  
  // State
  const [currentDraft, setCurrentDraft] = useState(null);
  const [saveStatus, setSaveStatus] = useState('idle'); // idle, saving, saved, error
  const [lastSaved, setLastSaved] = useState(null);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [pendingDraft, setPendingDraft] = useState(null);
  const [showLoginBanner, setShowLoginBanner] = useState(false);
  const [latestDraft, setLatestDraft] = useState(null);
  const [conflictWarning, setConflictWarning] = useState(null);
  
  // Refs
  const saveTimeoutRef = useRef(null);
  const versionRef = useRef(1);
  const isInitializedRef = useRef(false);
  
  // Get token
  const getToken = useCallback(() => localStorage.getItem('token'), []);
  
  // ============== API Functions ==============
  
  /**
   * Check if draft exists for current page
   */
  const checkForDraft = useCallback(async (module, route, entityId = null) => {
    if (!user) return null;
    
    try {
      const token = getToken();
      const params = new URLSearchParams({ module, route });
      if (entityId) params.append('entity_id', entityId);
      
      const response = await fetch(`${API}/drafts/check?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.has_draft) {
          setPendingDraft(data.draft);
          setShowResumeModal(true);
          return data.draft;
        }
      }
      return null;
    } catch (error) {
      console.error('Error checking for draft:', error);
      return null;
    }
  }, [user, getToken]);
  
  /**
   * Save draft (create or update)
   */
  const saveDraft = useCallback(async (draftData) => {
    if (!user) return null;
    
    setSaveStatus('saving');
    
    try {
      const token = getToken();
      const response = await fetch(`${API}/drafts`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(draftData)
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentDraft(data.draft);
        versionRef.current = data.draft.version;
        setLastSaved(new Date());
        setSaveStatus('saved');
        
        // Reset to idle after 2 seconds
        setTimeout(() => setSaveStatus('idle'), 2000);
        
        return data.draft;
      } else {
        setSaveStatus('error');
        return null;
      }
    } catch (error) {
      console.error('Error saving draft:', error);
      setSaveStatus('error');
      return null;
    }
  }, [user, getToken]);
  
  /**
   * Auto-save with debounce (1.5 seconds)
   */
  const autoSave = useCallback((draftData) => {
    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Set new timeout
    saveTimeoutRef.current = setTimeout(() => {
      saveDraft(draftData);
    }, 1500);
  }, [saveDraft]);
  
  /**
   * Immediate save (for blur, tab change, route exit)
   */
  const saveImmediate = useCallback(async (draftData) => {
    // Clear any pending auto-save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    return saveDraft(draftData);
  }, [saveDraft]);
  
  /**
   * Discard draft
   */
  const discardDraft = useCallback(async (draftId) => {
    if (!draftId) {
      draftId = currentDraft?.id || pendingDraft?.id;
    }
    if (!draftId) return;
    
    try {
      const token = getToken();
      await fetch(`${API}/drafts/${draftId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setCurrentDraft(null);
      setPendingDraft(null);
      setShowResumeModal(false);
      versionRef.current = 1;
    } catch (error) {
      console.error('Error discarding draft:', error);
    }
  }, [currentDraft, pendingDraft, getToken]);
  
  /**
   * Complete draft (after successful submission)
   */
  const completeDraft = useCallback(async (draftId) => {
    if (!draftId) {
      draftId = currentDraft?.id;
    }
    if (!draftId) return;
    
    try {
      const token = getToken();
      await fetch(`${API}/drafts/${draftId}/convert`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setCurrentDraft(null);
      versionRef.current = 1;
    } catch (error) {
      console.error('Error completing draft:', error);
    }
  }, [currentDraft, getToken]);
  
  /**
   * Complete drafts by entity (after entity closure)
   */
  const completeDraftByEntity = useCallback(async (module, entityId, route = null) => {
    try {
      const token = getToken();
      const params = new URLSearchParams({ module, entity_id: entityId });
      if (route) params.append('route', route);
      
      await fetch(`${API}/drafts/complete-by-entity?${params}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (currentDraft?.entity_id === entityId) {
        setCurrentDraft(null);
        versionRef.current = 1;
      }
    } catch (error) {
      console.error('Error completing draft by entity:', error);
    }
  }, [currentDraft, getToken]);
  
  /**
   * Check for version conflicts
   */
  const checkVersion = useCallback(async (draftId) => {
    if (!draftId) return { in_sync: true };
    
    try {
      const token = getToken();
      const response = await fetch(
        `${API}/drafts/version-check/${draftId}?client_version=${versionRef.current}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (response.ok) {
        const data = await response.json();
        if (data.has_conflict) {
          setConflictWarning({
            serverVersion: data.server_version,
            clientVersion: data.client_version,
            lastSavedAt: data.last_saved_at
          });
        }
        return data;
      }
      return { in_sync: true };
    } catch (error) {
      console.error('Error checking version:', error);
      return { in_sync: true };
    }
  }, [getToken]);
  
  /**
   * Get latest draft for login banner
   */
  const checkLatestDraft = useCallback(async () => {
    if (!user) return;
    
    try {
      const token = getToken();
      const response = await fetch(`${API}/drafts/latest`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.has_draft) {
          setLatestDraft(data.draft);
          setShowLoginBanner(true);
        }
      }
    } catch (error) {
      console.error('Error checking latest draft:', error);
    }
  }, [user, getToken]);
  
  /**
   * Resume from draft
   */
  const resumeDraft = useCallback((draft) => {
    if (!draft) {
      draft = pendingDraft || latestDraft;
    }
    if (!draft) return;
    
    setCurrentDraft(draft);
    versionRef.current = draft.version || 1;
    setShowResumeModal(false);
    setShowLoginBanner(false);
    
    // Navigate to the draft's route if different
    if (draft.route && draft.route !== location.pathname) {
      navigate(draft.route);
    }
    
    return draft;
  }, [pendingDraft, latestDraft, location.pathname, navigate]);
  
  /**
   * Cancel resume (close modal without action)
   */
  const cancelResume = useCallback(() => {
    setShowResumeModal(false);
    setPendingDraft(null);
  }, []);
  
  /**
   * Dismiss login banner
   */
  const dismissLoginBanner = useCallback(() => {
    setShowLoginBanner(false);
    setLatestDraft(null);
  }, []);
  
  // Check for latest draft on login
  useEffect(() => {
    if (user && !isInitializedRef.current) {
      isInitializedRef.current = true;
      checkLatestDraft();
    }
  }, [user, checkLatestDraft]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);
  
  // Context value
  const value = {
    // State
    currentDraft,
    saveStatus,
    lastSaved,
    showResumeModal,
    pendingDraft,
    showLoginBanner,
    latestDraft,
    conflictWarning,
    
    // Functions
    checkForDraft,
    saveDraft,
    autoSave,
    saveImmediate,
    discardDraft,
    completeDraft,
    completeDraftByEntity,
    checkVersion,
    resumeDraft,
    cancelResume,
    dismissLoginBanner,
    
    // Setters
    setCurrentDraft,
    setConflictWarning,
    
    // Helpers
    getModuleName: (module) => MODULE_NAMES[module] || module,
  };
  
  return (
    <DraftContext.Provider value={value}>
      {children}
    </DraftContext.Provider>
  );
};

export const useDraft = () => {
  const context = useContext(DraftContext);
  if (!context) {
    throw new Error('useDraft must be used within a DraftProvider');
  }
  return context;
};

export default DraftContext;
