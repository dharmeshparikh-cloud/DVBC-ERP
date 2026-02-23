/**
 * Custom React Query hooks for API data fetching
 * Provides caching, loading states, and error handling
 * 
 * Performance Optimization: December 2025
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { queryKeys, invalidateCache } from '../lib/queryClient';

// Get API base URL from environment
const API = process.env.REACT_APP_BACKEND_URL;

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ==================== DASHBOARD STATS ====================

export const useDashboardStats = () => {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/stats/dashboard`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useHRStats = () => {
  return useQuery({
    queryKey: queryKeys.hrStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/stats/hr`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useSalesStats = () => {
  return useQuery({
    queryKey: queryKeys.salesStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/stats/sales`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useConsultingStats = () => {
  return useQuery({
    queryKey: queryKeys.consultingStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/stats/consulting`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

// ==================== EMPLOYEES ====================

export const useEmployees = (filters = {}) => {
  const { page = 1, pageSize = 100, department, status } = filters;
  
  return useQuery({
    queryKey: queryKeys.employees({ page, pageSize, department, status }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      if (department) params.append('department', department);
      if (status) params.append('status', status);
      
      const { data } = await axios.get(`${API}/api/employees?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    keepPreviousData: true, // Keep showing old data while fetching new page
    staleTime: 5 * 60 * 1000,
  });
};

export const useEmployee = (id) => {
  return useQuery({
    queryKey: queryKeys.employee(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
  });
};

// ==================== LEADS ====================

export const useLeads = (filters = {}) => {
  const { page = 1, pageSize = 100, status, assignedTo } = filters;
  
  return useQuery({
    queryKey: queryKeys.leads({ page, pageSize, status, assignedTo }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      if (status) params.append('status', status);
      if (assignedTo) params.append('assigned_to', assignedTo);
      
      const { data } = await axios.get(`${API}/api/leads?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    keepPreviousData: true,
    staleTime: 3 * 60 * 1000, // 3 minutes for leads
  });
};

export const useLead = (id) => {
  return useQuery({
    queryKey: queryKeys.lead(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leads/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
  });
};

// ==================== ANALYTICS ====================

export const useFunnelSummary = (period = 'month') => {
  return useQuery({
    queryKey: queryKeys.funnelSummary(period),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/analytics/funnel-summary?period=${period}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 3 * 60 * 1000,
  });
};

export const useBottleneckAnalysis = (period = 'month') => {
  return useQuery({
    queryKey: queryKeys.bottleneckAnalysis(period),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/analytics/bottleneck-analysis?period=${period}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 3 * 60 * 1000,
  });
};

// ==================== MUTATIONS ====================

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
      invalidateCache.leads();
      invalidateCache.dashboardStats();
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, data: leadData }) => {
      const { data } = await axios.put(`${API}/api/leads/${id}`, leadData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lead(variables.id) });
      invalidateCache.leads();
    },
  });
};

export const useDeleteLead = () => {
  return useMutation({
    mutationFn: async (id) => {
      await axios.delete(`${API}/api/leads/${id}`, {
        headers: getAuthHeaders(),
      });
    },
    onSuccess: () => {
      invalidateCache.leads();
      invalidateCache.dashboardStats();
    },
  });
};

// ==================== USER PERMISSIONS ====================

export const useUserPermissions = () => {
  return useQuery({
    queryKey: queryKeys.userPermissions,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/rbac/my-permissions`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};
