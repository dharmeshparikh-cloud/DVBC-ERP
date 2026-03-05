/**
 * usePayroll.js - React Query hooks for Payroll management
 * 
 * Handles salary slips, components, inputs, and bulk generation.
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
  return [];
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch salary slips for a month
 */
export const useSalarySlips = (month, options = {}) => {
  return useQuery({
    queryKey: ['payroll', 'salary-slips', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/payroll/salary-slips?month=${month}`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled: !!month,
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options
  });
};

/**
 * Fetch salary components (earnings/deductions structure)
 */
export const useSalaryComponents = (options = {}) => {
  return useQuery({
    queryKey: ['payroll', 'salary-components'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/payroll/salary-components`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - rarely changes
    ...options
  });
};

/**
 * Fetch payroll inputs for a month (attendance, deductions, etc.)
 */
export const usePayrollInputs = (month, options = {}) => {
  return useQuery({
    queryKey: ['payroll', 'inputs', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/payroll/inputs?month=${month}`, { headers: getHeaders() });
      return res.data?.inputs || res.data || [];
    },
    enabled: !!month,
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch all employees for payroll processing
 */
export const usePayrollEmployees = (options = {}) => {
  return useQuery({
    queryKey: ['payroll', 'employees'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees/all`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Generate salary slip for single employee
 */
export const useGenerateSalarySlip = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ employeeId, month }) => {
      const res = await axios.post(`${API}/api/payroll/generate-slip`, 
        { employee_id: employeeId, month }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { month }) => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'salary-slips', month] });
    }
  });
};

/**
 * Generate salary slips in bulk
 */
export const useGenerateBulkSalarySlips = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ month }) => {
      const res = await axios.post(`${API}/api/payroll/generate-bulk`, 
        { month }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { month }) => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'salary-slips', month] });
    }
  });
};

/**
 * Add salary component
 */
export const useAddSalaryComponent = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload) => {
      const res = await axios.post(`${API}/api/payroll/salary-components/add`, 
        payload, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'salary-components'] });
    }
  });
};

/**
 * Delete salary component
 */
export const useDeleteSalaryComponent = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ type, key }) => {
      const res = await axios.delete(`${API}/api/payroll/salary-components/${type}/${key}`, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'salary-components'] });
    }
  });
};

/**
 * Save payroll input for single employee
 */
export const useSavePayrollInput = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ input, month }) => {
      const res = await axios.post(`${API}/api/payroll/inputs`, 
        { ...input, month }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { month }) => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'inputs', month] });
    }
  });
};

/**
 * Save payroll inputs in bulk
 */
export const useSaveBulkPayrollInputs = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ month, inputs }) => {
      const res = await axios.post(`${API}/api/payroll/inputs/bulk`, 
        { month, inputs }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { month }) => {
      queryClient.invalidateQueries({ queryKey: ['payroll', 'inputs', month] });
    }
  });
};

export default {
  useSalarySlips,
  useSalaryComponents,
  usePayrollInputs,
  usePayrollEmployees,
  useGenerateSalarySlip,
  useGenerateBulkSalarySlips,
  useAddSalaryComponent,
  useDeleteSalaryComponent,
  useSavePayrollInput,
  useSaveBulkPayrollInputs
};
