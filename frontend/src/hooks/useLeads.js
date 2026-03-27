/**
 * Leads Domain Hooks
 * All lead-related API operations via React Query
 * 
 * REACT QUERY ENFORCEMENT - March 2026
 * MIGRATION COMPLETE - December 2025
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Query Keys
export const leadKeys = {
  all: ['leads'],
  lists: () => [...leadKeys.all, 'list'],
  list: (filters) => [...leadKeys.lists(), filters],
  details: () => [...leadKeys.all, 'detail'],
  detail: (id) => [...leadKeys.details(), id],
  activities: (id) => [...leadKeys.all, 'activities', id],
  stage: (id) => [...leadKeys.all, 'stage', id],
  progress: (id) => [...leadKeys.all, 'progress', id],
  progressBulk: () => [...leadKeys.all, 'progress', 'bulk'],
  suggestions: (id) => [...leadKeys.all, 'suggestions', id],
};

// ==================== QUERIES ====================

/**
 * Fetch all leads with optional filters
 * Returns: { data: Lead[], total: number, page: number, page_size: number, total_pages: number }
 */
export const useLeads = (filters = {}) => {
  const { page = 1, pageSize = 100, status, assigned_to, search } = filters;
  
  return useQuery({
    queryKey: leadKeys.list({ page, pageSize, status, assigned_to, search }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      params.append('exclude_onboarded', 'true');
      if (status) params.append('status', status);
      if (assigned_to) params.append('assigned_to', assigned_to);
      if (search) params.append('search', search);
      
      const { data } = await axios.get(`${API}/api/leads?${params}`, {
        headers: getAuthHeaders(),
      });
      
      // Handle both new paginated format and legacy array format
      if (Array.isArray(data)) {
        // Legacy format - wrap in pagination structure
        return { data, total: data.length, page, page_size: pageSize, total_pages: 1 };
      }
      // New paginated format
      return data;
    },
    staleTime: 5 * 60 * 1000,
    keepPreviousData: true,
    // Select function to extract just the data array for backward compatibility
    select: (response) => response?.data || response || [],
  });
};

/**
 * Fetch single lead by ID
 */
export const useLead = (id) => {
  return useQuery({
    queryKey: leadKeys.detail(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch lead activities
 */
export const useLeadActivities = (leadId) => {
  return useQuery({
    queryKey: leadKeys.activities(leadId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${leadId}/activities`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!leadId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch lead stage info
 */
export const useLeadStage = (leadId) => {
  return useQuery({
    queryKey: leadKeys.stage(leadId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${leadId}/stage`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!leadId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch lead progress for a single lead
 */
export const useLeadProgress = (leadId) => {
  return useQuery({
    queryKey: leadKeys.progress(leadId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${leadId}/progress`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!leadId,
    staleTime: 3 * 60 * 1000,
  });
};

/**
 * Fetch bulk lead progress for all leads
 */
export const useBulkLeadProgress = () => {
  return useQuery({
    queryKey: leadKeys.progressBulk(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/progress/bulk`, {
        headers: getAuthHeaders(),
      });
      return data || {};
    },
    staleTime: 3 * 60 * 1000,
  });
};

/**
 * Fetch lead suggestions for high-scoring leads
 */
export const useLeadSuggestions = (leadId, enabled = true) => {
  return useQuery({
    queryKey: leadKeys.suggestions(leadId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${leadId}/suggestions`, {
        headers: getAuthHeaders(),
      });
      return data?.suggestions || [];
    },
    enabled: !!leadId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes for suggestions
    retry: false, // Don't retry on failure for suggestions
  });
};

// ==================== MUTATIONS ====================

/**
 * Create new lead
 */
export const useCreateLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leadData) => {
      const { data } = await axios.post(`${API}/api/leads`, leadData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'funnel'] });
    },
  });
};

/**
 * Update lead
 */
export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...leadData }) => {
      const { data } = await axios.patch(`${API}/api/leads/${id}`, leadData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(variables.id) });
    },
  });
};

/**
 * Delete lead
 */
export const useDeleteLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const { data } = await axios.delete(`${API}/api/leads/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
    },
  });
};

/**
 * Add lead activity
 */
export const useAddLeadActivity = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ leadId, activity }) => {
      const { data } = await axios.post(
        `${API}/api/leads/${leadId}/activities`,
        activity,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.activities(variables.leadId) });
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(variables.leadId) });
    },
  });
};

/**
 * Advance lead stage
 */
export const useAdvanceLeadStage = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ leadId, stageData }) => {
      const { data } = await axios.post(
        `${API}/api/leads/${leadId}/advance-stage`,
        stageData,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(variables.leadId) });
      queryClient.invalidateQueries({ queryKey: leadKeys.stage(variables.leadId) });
    },
  });
};

/**
 * Pause lead
 */
export const usePauseLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leadId) => {
      const { data } = await axios.post(
        `${API}/api/leads/${leadId}/pause`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: leadKeys.progressBulk() });
    },
  });
};

/**
 * Resume lead
 */
export const useResumeLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leadId) => {
      const { data } = await axios.post(
        `${API}/api/leads/${leadId}/resume`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: leadKeys.progressBulk() });
    },
  });
};

/**
 * Bulk create leads (for CSV import)
 */
export const useBulkCreateLeads = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leadsArray) => {
      const results = { success: 0, failed: 0 };
      for (const leadData of leadsArray) {
        try {
          await axios.post(`${API}/api/leads`, leadData, {
            headers: getAuthHeaders(),
          });
          results.success++;
        } catch {
          results.failed++;
        }
      }
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.all });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'funnel'] });
    },
  });
};

export default {
  useLeads,
  useLead,
  useLeadActivities,
  useLeadStage,
  useLeadProgress,
  useBulkLeadProgress,
  useLeadSuggestions,
  useCreateLead,
  useUpdateLead,
  useDeleteLead,
  useAddLeadActivity,
  useAdvanceLeadStage,
  usePauseLead,
  useResumeLead,
  useBulkCreateLeads,
};
