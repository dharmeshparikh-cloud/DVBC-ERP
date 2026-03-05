/**
 * useHROnboarding.js - React Query hooks for HR Onboarding (Legacy)
 * 
 * Handles employee creation, manager lookup, and access granting
 * for the legacy HR onboarding flow.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

// Helper to get auth headers
const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

// Helper to safely extract array from API response
const extractArray = (data) => {
  if (Array.isArray(data)) return data;
  if (data?.items && Array.isArray(data.items)) return data.items;
  return [];
};

// ============================================
// QUERY HOOKS - GET Requests
// ============================================

/**
 * Fetch all employees (for manager dropdown)
 */
export const useAllEmployees = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'all'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees/all`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 300000, // 5 minutes
    ...options
  });
};

/**
 * Fetch managers list (filtered for manager dropdown)
 */
export const useManagers = (options = {}) => {
  return useQuery({
    queryKey: ['employees', 'managers'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees/all`, { headers: getHeaders() });
      const allEmployees = extractArray(res.data);
      // Filter for potential managers (certain roles)
      return allEmployees.filter(emp => 
        emp.role && ['manager', 'hr_manager', 'sales_manager', 'senior_consultant', 
                     'principal_consultant', 'project_manager', 'admin', 'lead_consultant'].includes(emp.role)
      );
    },
    staleTime: 300000,
    ...options
  });
};

/**
 * Fetch suggested department based on designation
 */
export const useSuggestedDepartment = (designation, options = {}) => {
  return useQuery({
    queryKey: ['permissions', 'suggest-dept', designation],
    queryFn: async () => {
      const res = await axios.get(
        `${API}/api/permission-config/suggest-department?designation=${encodeURIComponent(designation)}`,
        { headers: getHeaders() }
      );
      return res.data;
    },
    enabled: !!designation,
    staleTime: 300000,
    ...options
  });
};

/**
 * Fetch existing employees for duplicate check
 */
export const useExistingEmployees = (searchParams, options = {}) => {
  return useQuery({
    queryKey: ['employees', 'search', searchParams],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees/all`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled: !!searchParams,
    staleTime: 300000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS - POST Requests
// ============================================

/**
 * Create employee mutation
 */
export const useCreateEmployee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (employeeData) => {
      const res = await axios.post(`${API}/api/employees`, employeeData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    }
  });
};

/**
 * Grant employee access mutation
 */
export const useGrantEmployeeAccess = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, temporaryPassword }) => {
      const res = await axios.post(
        `${API}/api/employees/${employeeId}/grant-access`,
        { temporary_password: temporaryPassword },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { employeeId }) => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId] });
    }
  });
};

/**
 * Bulk import employees mutation
 */
export const useBulkImportEmployees = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (employeesData) => {
      const results = [];
      for (const emp of employeesData) {
        try {
          const res = await axios.post(`${API}/api/employees`, emp, { headers: getHeaders() });
          results.push({ success: true, data: res.data, employee: emp });
        } catch (error) {
          results.push({ success: false, error: error.response?.data?.detail || error.message, employee: emp });
        }
      }
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    }
  });
};

/**
 * Update employee mutation
 */
export const useUpdateEmployee = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, data }) => {
      const res = await axios.patch(`${API}/api/employees/${employeeId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { employeeId }) => {
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId] });
    }
  });
};

export default {
  useAllEmployees,
  useManagers,
  useSuggestedDepartment,
  useExistingEmployees,
  useCreateEmployee,
  useGrantEmployeeAccess,
  useBulkImportEmployees,
  useUpdateEmployee
};
