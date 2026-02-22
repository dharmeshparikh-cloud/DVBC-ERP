import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '../App';

/**
 * Enhanced useDraft hook with Universal Auto-Save & Resume functionality
 * 
 * Features:
 * - Auto-save on field change (debounced, default 1.5 sec)
 * - Save on tab change, blur, visibility change, and route exit
 * - Resume flow with check for existing drafts
 * - Auto-delete on submission/stage completion
 * - Version conflict detection
 * - RBAC compliance (employee-scoped)
 * 
 * @param {string} draftType - Type of draft (e.g., 'onboarding', 'lead', 'meeting')
 * @param {Function} generateTitle - Function to generate title from form data
 * @param {number} autoSaveDelay - Delay in ms for auto-save (default: 1500ms)
 * @param {string} entityId - Optional entity ID to filter drafts
 * @param {Object} options - Additional options { module, checkOnMount, onResume }
 */
const useDraft = (
  draftType, 
  generateTitle, 
  autoSaveDelay = 1500, 
  entityId = null,
  options = {}
) => {
  const location = useLocation();
  const { 
    module = draftType, 
    checkOnMount = false,
    onResume = null 
  } = options;
  
  const [draftId, setDraftId] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [loadingDrafts, setLoadingDrafts] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [saveStatus, setSaveStatus] = useState('idle'); // idle, saving, saved, error
  const [pendingDraft, setPendingDraft] = useState(null);
  const [showResumePrompt, setShowResumePrompt] = useState(false);
  const [version, setVersion] = useState(1);
  
  const autoSaveTimerRef = useRef(null);
  const lastDataRef = useRef(null);
  const formDataGetterRef = useRef(null);
  const activeTabRef = useRef(null);
  const hasCheckedRef = useRef(false);

  const currentRoute = location.pathname;

  // ============== Check for Existing Draft ==============
  
  const checkForDraft = useCallback(async () => {
    try {
      const params = new URLSearchParams({ 
        module, 
        route: currentRoute 
      });
      if (entityId) params.append('entity_id', entityId);
      
      const response = await axios.get(`${API}/drafts/check?${params}`);
      
      if (response.data.has_draft) {
        setPendingDraft(response.data.draft);
        setShowResumePrompt(true);
        return response.data.draft;
      }
      return null;
    } catch (error) {
      console.error('Error checking for draft:', error);
      return null;
    }
  }, [module, currentRoute, entityId]);

  // Check on mount if enabled
  useEffect(() => {
    if (checkOnMount && !hasCheckedRef.current) {
      hasCheckedRef.current = true;
      checkForDraft();
    }
  }, [checkOnMount, checkForDraft]);

  // ============== Fetch Drafts ==============

  const fetchDrafts = useCallback(async () => {
    setLoadingDrafts(true);
    try {
      const params = { draft_type: draftType };
      if (entityId) params.entity_id = entityId;
      if (module) params.module = module;
      
      const response = await axios.get(`${API}/drafts`, { params });
      setDrafts(response.data || []);
    } catch (error) {
      console.error('Failed to fetch drafts:', error);
    } finally {
      setLoadingDrafts(false);
    }
  }, [draftType, entityId, module]);

  useEffect(() => {
    fetchDrafts();
  }, [fetchDrafts]);

  // ============== Load Draft ==============

  const loadDraft = useCallback(async (id) => {
    try {
      const response = await axios.get(`${API}/drafts/${id}`);
      const draft = response.data;
      setDraftId(id);
      setVersion(draft.version || 1);
      setLastSaved(new Date(draft.updated_at || draft.last_saved_at));
      return draft;
    } catch (error) {
      toast.error('Failed to load draft');
      return null;
    }
  }, []);

  // ============== Save Draft ==============

  const saveDraft = useCallback(async (formData, step = 0, metadata = {}, showToast = true) => {
    // Don't save if data hasn't changed
    const dataString = JSON.stringify(formData);
    if (lastDataRef.current === dataString && draftId) {
      return draftId;
    }
    lastDataRef.current = dataString;

    setSaving(true);
    setSaveStatus('saving');
    
    try {
      const title = generateTitle ? generateTitle(formData) : `${draftType} Draft`;
      const draftData = {
        module,
        draft_type: draftType,
        title,
        route: currentRoute,
        active_tab: activeTabRef.current,
        step,
        form_data: formData,
        data: formData, // Backward compatibility
        metadata,
        entity_id: entityId
      };

      let response;
      if (draftId) {
        response = await axios.put(`${API}/drafts/${draftId}`, draftData);
      } else {
        response = await axios.post(`${API}/drafts`, draftData);
        setDraftId(response.data.draft?.id);
      }
      
      const newVersion = response.data.draft?.version || version + 1;
      setVersion(newVersion);
      setLastSaved(new Date());
      setSaveStatus('saved');
      
      // Reset to idle after 2 seconds
      setTimeout(() => setSaveStatus('idle'), 2000);
      
      if (showToast) {
        toast.success('Draft saved', { duration: 2000 });
      }
      return response.data.draft?.id || draftId;
    } catch (error) {
      console.error('Failed to save draft:', error);
      setSaveStatus('error');
      if (showToast) {
        toast.error('Failed to save draft');
      }
      return null;
    } finally {
      setSaving(false);
    }
  }, [draftId, draftType, module, currentRoute, generateTitle, entityId, version]);

  // ============== Auto-Save ==============

  const autoSave = useCallback((formData, step = 0, metadata = {}) => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    
    autoSaveTimerRef.current = setTimeout(() => {
      saveDraft(formData, step, metadata, false);
    }, autoSaveDelay);
  }, [saveDraft, autoSaveDelay]);

  // ============== Set Active Tab ==============

  const setActiveTab = useCallback((tab) => {
    activeTabRef.current = tab;
    // Trigger immediate save on tab change
    if (formDataGetterRef.current) {
      const formData = formDataGetterRef.current();
      if (formData && Object.keys(formData).length > 0) {
        saveDraft(formData, 0, {}, false);
      }
    }
  }, [saveDraft]);

  // ============== Delete Draft ==============

  const deleteDraft = useCallback(async (id = draftId) => {
    if (!id) return;
    
    try {
      await axios.delete(`${API}/drafts/${id}`);
      if (id === draftId) {
        setDraftId(null);
        setLastSaved(null);
        setVersion(1);
        lastDataRef.current = null;
      }
      setDrafts(prev => prev.filter(d => d.id !== id));
      toast.success('Draft deleted');
      return true;
    } catch (error) {
      toast.error('Failed to delete draft');
      return false;
    }
  }, [draftId]);

  // ============== Convert/Complete Draft ==============

  const convertDraft = useCallback(async () => {
    if (!draftId) return;
    
    try {
      await axios.post(`${API}/drafts/${draftId}/convert`);
      setDraftId(null);
      setLastSaved(null);
      setVersion(1);
      lastDataRef.current = null;
    } catch (error) {
      console.error('Failed to mark draft as converted:', error);
    }
  }, [draftId]);

  // Complete drafts by entity
  const completeDraftByEntity = useCallback(async (entityIdToComplete) => {
    try {
      const params = new URLSearchParams({ 
        module, 
        entity_id: entityIdToComplete || entityId 
      });
      await axios.post(`${API}/drafts/complete-by-entity?${params}`);
      
      if (entityIdToComplete === entityId) {
        setDraftId(null);
        setLastSaved(null);
        setVersion(1);
        lastDataRef.current = null;
      }
    } catch (error) {
      console.error('Error completing draft by entity:', error);
    }
  }, [module, entityId]);

  // ============== Resume Flow ==============

  const resumeDraft = useCallback(async (draft = pendingDraft) => {
    if (!draft) return null;
    
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft && onResume) {
      onResume(loadedDraft);
    }
    
    setShowResumePrompt(false);
    setPendingDraft(null);
    return loadedDraft;
  }, [pendingDraft, loadDraft, onResume]);

  const discardPendingDraft = useCallback(async () => {
    if (pendingDraft) {
      await deleteDraft(pendingDraft.id);
    }
    setShowResumePrompt(false);
    setPendingDraft(null);
  }, [pendingDraft, deleteDraft]);

  const cancelResume = useCallback(() => {
    setShowResumePrompt(false);
    setPendingDraft(null);
  }, []);

  // ============== Clear Draft ==============

  const clearDraft = useCallback(() => {
    setDraftId(null);
    setLastSaved(null);
    setVersion(1);
    lastDataRef.current = null;
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  }, []);

  // ============== Register Form Data Getter ==============

  const registerFormDataGetter = useCallback((getter) => {
    formDataGetterRef.current = getter;
  }, []);

  // ============== Version Check ==============

  const checkVersion = useCallback(async () => {
    if (!draftId) return { in_sync: true };
    
    try {
      const response = await axios.get(
        `${API}/drafts/version-check/${draftId}?client_version=${version}`
      );
      return response.data;
    } catch (error) {
      console.error('Error checking version:', error);
      return { in_sync: true };
    }
  }, [draftId, version]);

  // ============== Event Handlers ==============

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (formDataGetterRef.current && lastDataRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          const title = generateTitle ? generateTitle(formData) : `${draftType} Draft`;
          const draftData = {
            module,
            draft_type: draftType,
            title,
            route: currentRoute,
            active_tab: activeTabRef.current,
            form_data: formData,
            data: formData,
            entity_id: entityId
          };
          
          const blob = new Blob([JSON.stringify(draftData)], { type: 'application/json' });
          const endpoint = draftId ? `${API}/drafts/${draftId}` : `${API}/drafts`;
          navigator.sendBeacon && navigator.sendBeacon(endpoint, blob);
        }
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden' && formDataGetterRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          saveDraft(formData, 0, {}, false);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [draftId, draftType, module, currentRoute, generateTitle, entityId, saveDraft]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      if (formDataGetterRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          saveDraft(formData, 0, {}, false);
        }
      }
    };
  }, [saveDraft]);

  return {
    // State
    draftId,
    drafts,
    loadingDrafts,
    saving,
    lastSaved,
    saveStatus,
    version,
    pendingDraft,
    showResumePrompt,
    
    // Core Functions
    fetchDrafts,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft,
    setDraftId,
    
    // Enhanced Functions
    checkForDraft,
    setActiveTab,
    completeDraftByEntity,
    checkVersion,
    registerFormDataGetter,
    
    // Resume Functions
    resumeDraft,
    discardPendingDraft,
    cancelResume,
  };
};

export default useDraft;
