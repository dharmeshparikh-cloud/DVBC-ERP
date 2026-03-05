/**
 * Employee Domain Hooks
 * All employee-related API operations via React Query
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
export const employeeKeys = {
  all: ['employees'],
  lists: () => [...employeeKeys.all, 'list'],
  list: (filters) => [...employeeKeys.lists(), filters],
  details: () => [...employeeKeys.all, 'detail'],
  detail: (id) => [...employeeKeys.details(), id],
  permissions: (id) => [...employeeKeys.all, 'permissions', id],
  leaveBalance: (id) => [...employeeKeys.all, 'leave-balance', id],
};

// ==================== QUERIES ====================

/**
 * Fetch all employees with optional filters
 */
export const useEmployees = (filters = {}) => {
  const { page = 1, pageSize = 100, department, status, search } = filters;
  
  return useQuery({
    queryKey: employeeKeys.list({ page, pageSize, department, status, search }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      if (department) params.append('department', department);
      if (status) params.append('status', status);
      if (search) params.append('search', search);
      
      const { data } = await axios.get(`${API}/api/employees?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
    keepPreviousData: true,
  });
};

/**
 * Fetch single employee by ID
 */
export const useEmployee = (id) => {
  return useQuery({
    queryKey: employeeKeys.detail(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch employee permissions
 */
export const useEmployeePermissions = (employeeId) => {
  return useQuery({
    queryKey: employeeKeys.permissions(employeeId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/${employeeId}/permissions`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!employeeId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch employee leave balance
 */
export const useEmployeeLeaveBalance = (employeeId) => {
  return useQuery({
    queryKey: employeeKeys.leaveBalance(employeeId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/${employeeId}/leave-balance`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!employeeId,
    staleTime: 5 * 60 * 1000,
  });
};

// ==================== MUTATIONS ====================

/**
 * Create new employee
 */
export const useCreateEmployee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (employeeData) => {
      const { data } = await axios.post(`${API}/api/employees`, employeeData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
};

/**
 * Update employee
 */
export const useUpdateEmployee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...employeeData }) => {
      const { data } = await axios.patch(`${API}/api/employees/${id}`, employeeData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      queryClient.invalidateQueries({ queryKey: employeeKeys.detail(variables.id) });
    },
  });
};

/**
 * Delete employee
 */
export const useDeleteEmployee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const { data } = await axios.delete(`${API}/api/employees/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
};

/**
 * Update employee permissions
 */
export const useUpdateEmployeePermissions = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, permissions }) => {
      const { data } = await axios.patch(
        `${API}/api/employees/${employeeId}/permissions`,
        permissions,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.permissions(variables.employeeId) });
    },
  });
};

/**
 * Link employee to user account
 */
export const useLinkEmployeeToUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, userId }) => {
      const { data } = await axios.post(
        `${API}/api/employees/${employeeId}/link-user?user_id=${userId}`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

/**
 * Grant employee portal access
 */
export const useGrantEmployeeAccess = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, role, password }) => {
      const { data } = await axios.post(
        `${API}/api/employees/${employeeId}/grant-access`,
        { role, password },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

/**
 * Revoke employee portal access
 */
export const useRevokeEmployeeAccess = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (employeeId) => {
      const { data } = await axios.delete(
        `${API}/api/employees/${employeeId}/revoke-access`,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

/**
 * Unlink employee from user account
 */
export const useUnlinkEmployeeFromUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (employeeId) => {
      const { data } = await axios.post(
        `${API}/api/employees/${employeeId}/unlink-user`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

/**
 * Update employee mobile access
 */
export const useUpdateMobileAccess = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, mobileEnabled }) => {
      const { data } = await axios.put(
        `${API}/api/hr/employee/${employeeId}/mobile-access`,
        { mobile_enabled: mobileEnabled },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
    },
  });
};

/**
 * Fetch all employees (simple list)
 */
export const useAllEmployees = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'all'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/all`, {
        headers: getAuthHeaders(),
      });
      return Array.isArray(data) ? data : (data?.items || []);
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch employee stats summary
 */
export const useEmployeeStats = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'stats'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/stats/summary`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch departments list
 */
export const useDepartmentsList = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'departments'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/departments/list`, {
        headers: getAuthHeaders(),
      });
      return data || [];
    },
    staleTime: 10 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch org chart hierarchy
 */
export const useOrgChart = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'org-chart'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/employees/org-chart/hierarchy`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

export default {
  useEmployees,
  useEmployee,
  useEmployeePermissions,
  useEmployeeLeaveBalance,
  useCreateEmployee,
  useUpdateEmployee,
  useDeleteEmployee,
  useUpdateEmployeePermissions,
  useLinkEmployeeToUser,
  useGrantEmployeeAccess,
  useRevokeEmployeeAccess,
  useUnlinkEmployeeFromUser,
  useUpdateMobileAccess,
  useAllEmployees,
  useEmployeeStats,
  useDepartmentsList,
  useOrgChart,
};
