/**
 * Leads Domain Hooks
 * All lead-related API operations via React Query
 * 
 * REACT QUERY ENFORCEMENT - March 2026
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
};

// ==================== QUERIES ====================

/**
 * Fetch all leads with optional filters
 */
export const useLeads = (filters = {}) => {
  const { page = 1, pageSize = 100, status, assigned_to, search } = filters;
  
  return useQuery({
    queryKey: leadKeys.list({ page, pageSize, status, assigned_to, search }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      if (status) params.append('status', status);
      if (assigned_to) params.append('assigned_to', assigned_to);
      if (search) params.append('search', search);
      
      const { data } = await axios.get(`${API}/api/leads?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
    keepPreviousData: true,
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

export default {
  useLeads,
  useLead,
  useLeadActivities,
  useLeadStage,
  useCreateLead,
  useUpdateLead,
  useDeleteLead,
  useAddLeadActivity,
  useAdvanceLeadStage,
};
