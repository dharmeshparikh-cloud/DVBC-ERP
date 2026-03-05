/**
 * useConsultants.js - React Query hooks for Consultant management
 * 
 * Handles consultant listing, assignments, and availability.
 * Eliminates duplicate /consultants API calls across 7+ files.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

const extractArray = (data) => {
  if (Array.isArray(data)) return data;
  if (data?.items) return data.items;
  if (data?.consultants) return data.consultants;
  return [];
};

// Query key factory
export const consultantKeys = {
  all: ['consultants'],
  list: () => [...consultantKeys.all, 'list'],
  detail: (id) => [...consultantKeys.all, 'detail', id],
  availability: () => [...consultantKeys.all, 'availability'],
  assignments: (id) => [...consultantKeys.all, id, 'assignments'],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all consultants
 */
export const useConsultantsList = (options = {}) => {
  return useQuery({
    queryKey: consultantKeys.list(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/consultants`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options
  });
};

/**
 * Fetch consultant details
 */
export const useConsultantDetails = (consultantId, options = {}) => {
  return useQuery({
    queryKey: consultantKeys.detail(consultantId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/consultants/${consultantId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!consultantId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch consultant availability
 */
export const useConsultantAvailability = (options = {}) => {
  return useQuery({
    queryKey: consultantKeys.availability(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/consultants/availability`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes - availability changes frequently
    ...options
  });
};

/**
 * Fetch consultant assignments
 */
export const useConsultantAssignments = (consultantId, options = {}) => {
  return useQuery({
    queryKey: consultantKeys.assignments(consultantId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/consultants/${consultantId}/assignments`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled: !!consultantId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch available consultants for assignment
 */
export const useAvailableConsultants = (projectId, options = {}) => {
  return useQuery({
    queryKey: ['consultants', 'available', projectId],
    queryFn: async () => {
      const url = projectId 
        ? `${API}/api/consultants/available?project_id=${projectId}`
        : `${API}/api/consultants/available`;
      const res = await axios.get(url, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Assign consultant to project
 */
export const useAssignConsultant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ projectId, consultantId, role, allocation }) => {
      const res = await axios.post(`${API}/api/projects/${projectId}/assign`, 
        { consultant_id: consultantId, role, allocation_percentage: allocation },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { consultantId }) => {
      queryClient.invalidateQueries({ queryKey: consultantKeys.all });
      queryClient.invalidateQueries({ queryKey: consultantKeys.assignments(consultantId) });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });
};

/**
 * Update consultant assignment
 */
export const useUpdateAssignment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ assignmentId, data }) => {
      const res = await axios.patch(`${API}/api/assignments/${assignmentId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: consultantKeys.all });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });
};

/**
 * Remove consultant from project
 */
export const useRemoveConsultant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ projectId, consultantId }) => {
      const res = await axios.delete(`${API}/api/projects/${projectId}/consultants/${consultantId}`, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { consultantId }) => {
      queryClient.invalidateQueries({ queryKey: consultantKeys.all });
      queryClient.invalidateQueries({ queryKey: consultantKeys.assignments(consultantId) });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    }
  });
};

export default {
  consultantKeys,
  useConsultantsList,
  useConsultantDetails,
  useConsultantAvailability,
  useConsultantAssignments,
  useAvailableConsultants,
  useAssignConsultant,
  useUpdateAssignment,
  useRemoveConsultant
};
