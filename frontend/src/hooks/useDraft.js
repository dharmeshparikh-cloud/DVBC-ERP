import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '../App';

/**
 * Custom hook for managing drafts with auto-save functionality
 * @param {string} draftType - Type of draft (e.g., 'onboarding', 'lead', 'meeting')
 * @param {Function} generateTitle - Function to generate title from form data
 * @param {number} autoSaveDelay - Delay in ms for auto-save (default: 3000ms)
 */
const useDraft = (draftType, generateTitle, autoSaveDelay = 3000) => {
  const [draftId, setDraftId] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [loadingDrafts, setLoadingDrafts] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const autoSaveTimerRef = useRef(null);
  const lastDataRef = useRef(null);

  // Fetch all drafts of this type
  const fetchDrafts = useCallback(async () => {
    setLoadingDrafts(true);
    try {
      const response = await axios.get(`${API}/drafts`, {
        params: { draft_type: draftType }
      });
      setDrafts(response.data || []);
    } catch (error) {
      console.error('Failed to fetch drafts:', error);
    } finally {
      setLoadingDrafts(false);
    }
  }, [draftType]);

  // Load drafts on mount
  useEffect(() => {
    fetchDrafts();
  }, [fetchDrafts]);

  // Load a specific draft
  const loadDraft = useCallback(async (id) => {
    try {
      const response = await axios.get(`${API}/drafts/${id}`);
      setDraftId(id);
      setLastSaved(new Date(response.data.updated_at));
      return response.data;
    } catch (error) {
      toast.error('Failed to load draft');
      return null;
    }
  }, []);

  // Save draft (create or update)
  const saveDraft = useCallback(async (formData, step = 0, metadata = {}, showToast = true) => {
    // Don't save if data hasn't changed
    const dataString = JSON.stringify(formData);
    if (lastDataRef.current === dataString && draftId) {
      return draftId;
    }
    lastDataRef.current = dataString;

    setSaving(true);
    try {
      const title = generateTitle ? generateTitle(formData) : `${draftType} Draft`;
      const draftData = {
        draft_type: draftType,
        title,
        data: formData,
        step,
        metadata
      };

      let response;
      if (draftId) {
        // Update existing draft
        response = await axios.put(`${API}/drafts/${draftId}`, draftData);
      } else {
        // Create new draft
        response = await axios.post(`${API}/drafts`, draftData);
        setDraftId(response.data.draft?.id);
      }
      
      setLastSaved(new Date());
      if (showToast) {
        toast.success('Draft saved', { duration: 2000 });
      }
      return response.data.draft?.id || draftId;
    } catch (error) {
      console.error('Failed to save draft:', error);
      if (showToast) {
        toast.error('Failed to save draft');
      }
      return null;
    } finally {
      setSaving(false);
    }
  }, [draftId, draftType, generateTitle]);

  // Auto-save with debounce
  const autoSave = useCallback((formData, step = 0, metadata = {}) => {
    // Clear existing timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    
    // Set new timer
    autoSaveTimerRef.current = setTimeout(() => {
      saveDraft(formData, step, metadata, false); // Silent save (no toast)
    }, autoSaveDelay);
  }, [saveDraft, autoSaveDelay]);

  // Delete a draft
  const deleteDraft = useCallback(async (id = draftId) => {
    if (!id) return;
    
    try {
      await axios.delete(`${API}/drafts/${id}`);
      if (id === draftId) {
        setDraftId(null);
        setLastSaved(null);
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

  // Mark draft as converted (when actual record is created)
  const convertDraft = useCallback(async () => {
    if (!draftId) return;
    
    try {
      await axios.post(`${API}/drafts/${draftId}/convert`);
      setDraftId(null);
      setLastSaved(null);
      lastDataRef.current = null;
    } catch (error) {
      console.error('Failed to mark draft as converted:', error);
    }
  }, [draftId]);

  // Clear current draft (start fresh)
  const clearDraft = useCallback(() => {
    setDraftId(null);
    setLastSaved(null);
    lastDataRef.current = null;
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  }, []);

  // Register a callback to get current form data for save-on-leave
  const formDataGetterRef = useRef(null);
  const registerFormDataGetter = useCallback((getter) => {
    formDataGetterRef.current = getter;
  }, []);

  // Save on page leave (beforeunload)
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      // Only save if we have a draft ID and form data getter
      if (formDataGetterRef.current && lastDataRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          // Use sendBeacon for reliable save on page unload
          const title = generateTitle ? generateTitle(formData) : `${draftType} Draft`;
          const draftData = {
            draft_type: draftType,
            title,
            data: formData,
            step: 0,
            metadata: {}
          };
          
          // Try sendBeacon first (more reliable for unload)
          const blob = new Blob([JSON.stringify(draftData)], { type: 'application/json' });
          const endpoint = draftId ? `${API}/drafts/${draftId}` : `${API}/drafts`;
          
          // Note: sendBeacon only works with POST, so this is best effort
          navigator.sendBeacon && navigator.sendBeacon(endpoint, blob);
        }
      }
    };

    // Handle visibility change (user switching tabs)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden' && formDataGetterRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          saveDraft(formData, 0, {}, false); // Silent save
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [draftId, draftType, generateTitle, saveDraft]);

  // Cleanup on unmount - save final state
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
      // Save on unmount if there's data
      if (formDataGetterRef.current) {
        const formData = formDataGetterRef.current();
        if (formData && Object.keys(formData).length > 0) {
          saveDraft(formData, 0, {}, false);
        }
      }
    };
  }, [saveDraft]);

  return {
    draftId,
    drafts,
    loadingDrafts,
    saving,
    lastSaved,
    fetchDrafts,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft,
    setDraftId,
    registerFormDataGetter
  };
};

export default useDraft;
