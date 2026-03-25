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

// ==================== PROJECTS ====================

export const useProjects = (filters = {}) => {
  const { page = 1, pageSize = 100, status, clientId } = filters;
  
  return useQuery({
    queryKey: queryKeys.projects({ page, pageSize, status, clientId }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('skip', (page - 1) * pageSize);
      params.append('limit', pageSize);
      if (status) params.append('status', status);
      if (clientId) params.append('client_id', clientId);
      
      const { data } = await axios.get(`${API}/api/projects?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    keepPreviousData: true,
    staleTime: 3 * 60 * 1000,
  });
};

export const useProject = (id) => {
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
  });
};

// ==================== EXPENSES ====================

export const useExpenses = (filters = {}) => {
  const { status, category, employeeId } = filters;
  
  return useQuery({
    queryKey: ['expenses', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (category) params.append('category', category);
      if (employeeId) params.append('employee_id', employeeId);
      
      const { data } = await axios.get(`${API}/api/expenses?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes for expenses
  });
};

export const usePendingApprovals = () => {
  return useQuery({
    queryKey: ['expenses', 'pending-approvals'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/expenses/pending-approvals`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useExpenseCategories = () => {
  return useQuery({
    queryKey: ['expenses', 'categories'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/expenses/categories`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 30 * 60 * 1000, // Categories rarely change
  });
};

// ==================== EXPENSE MUTATIONS ====================

export const useApproveExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, remarks }) => {
      const { data } = await axios.post(`${API}/api/expenses/${id}/approve`, { remarks }, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      invalidateCache.dashboardStats();
    },
  });
};

export const useRejectExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, reason }) => {
      const { data } = await axios.post(`${API}/api/expenses/${id}/reject`, { reason }, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
    },
  });
};

export const useSendBackExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, comments }) => {
      const { data } = await axios.post(`${API}/api/expenses/${id}/send-back`, { comments }, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
    },
  });
};

// ==================== KICKOFF REQUESTS ====================

export const useKickoffRequests = (filters = {}) => {
  const { status } = filters;
  
  return useQuery({
    queryKey: ['kickoff-requests', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      
      const { data } = await axios.get(`${API}/api/kickoff-requests?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const usePendingKickoffs = () => {
  return useQuery({
    queryKey: ['kickoff-requests', 'pending'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/kickoff-requests?status=pending`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

// ==================== AGREEMENTS ====================

export const useAgreements = (filters = {}) => {
  const { status, leadId } = filters;
  
  return useQuery({
    queryKey: ['agreements', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (leadId) params.append('lead_id', leadId);
      
      const { data } = await axios.get(`${API}/api/agreements?${params}`, {
        headers: getAuthHeaders(),
      });
      return Array.isArray(data) ? data : (data?.data || []);
    },
    staleTime: 3 * 60 * 1000,
  });
};

export const useAgreement = (id) => {
  return useQuery({
    queryKey: ['agreement', id],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/agreements/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
  });
};

// ==================== NOTIFICATIONS ====================

export const useNotifications = () => {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/notifications`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute for notifications
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useMarkNotificationRead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      await axios.patch(`${API}/api/notifications/${id}/read`, {}, {
        headers: getAuthHeaders(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
};

// ==================== LEAVE ENCASHMENT ====================

export const useEncashmentRequests = (filters = {}) => {
  const { status, employeeId } = filters;
  
  return useQuery({
    queryKey: ['encashment-requests', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (employeeId) params.append('employee_id', employeeId);
      
      const { data } = await axios.get(`${API}/api/leave-policies/encashment-requests?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useApproveEncashment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, remarks }) => {
      const { data } = await axios.post(`${API}/api/leave-policies/encashment-requests/${id}/approve`, { remarks }, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['encashment-requests'] });
      invalidateCache.dashboardStats();
    },
  });
};

export const useRejectEncashment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, reason }) => {
      const { data } = await axios.post(`${API}/api/leave-policies/encashment-requests/${id}/reject`, { reason }, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['encashment-requests'] });
    },
  });
};

// ==================== TRAVEL REIMBURSEMENTS ====================

export const useTravelReimbursements = (filters = {}) => {
  const { status } = filters;
  
  return useQuery({
    queryKey: ['travel-reimbursements', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      
      const { data } = await axios.get(`${API}/api/travel/reimbursements?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useApproveTravelReimbursement = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const { data } = await axios.post(`${API}/api/travel/reimbursements/${id}/approve`, {}, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['travel-reimbursements'] });
      invalidateCache.dashboardStats();
    },
  });
};

// ==================== GENERIC FETCH HOOK ====================

/**
 * Generic hook for fetching data from any endpoint
 * Use this for endpoints not covered by specific hooks
 */
export const useFetch = (endpoint, options = {}) => {
  const { 
    enabled = true, 
    staleTime = 5 * 60 * 1000,
    params = {}
  } = options;
  
  const queryString = Object.keys(params || {}).length > 0 
    ? '?' + new URLSearchParams(params).toString() 
    : '';
  
  return useQuery({
    queryKey: [endpoint, params],
    queryFn: async () => {
      const { data } = await axios.get(`${API}${endpoint}${queryString}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled,
    staleTime,
  });
};

/**
 * Generic mutation hook for any endpoint
 */
export const useMutate = (endpoint, options = {}) => {
  const { method = 'post', onSuccess } = options;
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (body = {}) => {
      const axiosMethod = axios[method.toLowerCase()];
      const { data } = await axiosMethod(`${API}${endpoint}`, body, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      if (onSuccess) {
        onSuccess(data, variables, queryClient);
      }
    },
  });
};
