/**
 * Expenses Domain Hooks
 * All expense management API operations via React Query
 * 
 * PERFORMANCE OPTIMIZED - December 2025
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { invalidateCache } from '../lib/queryClient';

const API = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Query Keys
export const expenseKeys = {
  all: ['expenses'],
  lists: () => [...expenseKeys.all, 'list'],
  list: (filters) => [...expenseKeys.lists(), filters],
  details: () => [...expenseKeys.all, 'detail'],
  detail: (id) => [...expenseKeys.details(), id],
  my: () => [...expenseKeys.all, 'my'],
  pending: () => [...expenseKeys.all, 'pending'],
  stats: () => [...expenseKeys.all, 'stats'],
};

/**
 * Fetch all expenses (admin/manager view)
 */
export const useExpenses = (filters = {}) => {
  return useQuery({
    queryKey: expenseKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      if (filters.month) params.append('month', filters.month);
      
      const { data } = await axios.get(`${API}/api/expenses?${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch my expenses (employee view)
 */
export const useMyExpenses = () => {
  return useQuery({
    queryKey: expenseKeys.my(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/my/expenses`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch pending expenses for approval
 */
export const usePendingExpenses = () => {
  return useQuery({
    queryKey: expenseKeys.pending(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/expenses/pending`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 1 * 60 * 1000,
  });
};

/**
 * Create new expense
 */
export const useCreateExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (expenseData) => {
      const { data } = await axios.post(`${API}/api/expenses`, expenseData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all });
    },
  });
};

/**
 * Update expense
 */
export const useUpdateExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, updates }) => {
      const { data } = await axios.put(`${API}/api/expenses/${expenseId}`, updates, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all });
    },
  });
};

/**
 * Approve expense
 */
export const useApproveExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, remarks }) => {
      const { data } = await axios.post(`${API}/api/expenses/${expenseId}/approve`, 
        { remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all });
      invalidateCache.approvals();
    },
  });
};

/**
 * Reject expense
 */
export const useRejectExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, reason }) => {
      const { data } = await axios.post(`${API}/api/expenses/${expenseId}/reject`, 
        { reason },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all });
      invalidateCache.approvals();
    },
  });
};

/**
 * Delete expense
 */
export const useDeleteExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (expenseId) => {
      await axios.delete(`${API}/api/expenses/${expenseId}`, {
        headers: getAuthHeaders(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: expenseKeys.all });
    },
  });
};

export default {
  useExpenses,
  useMyExpenses,
  usePendingExpenses,
  useCreateExpense,
  useUpdateExpense,
  useApproveExpense,
  useRejectExpense,
  useDeleteExpense,
};
