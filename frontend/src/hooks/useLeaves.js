/**
 * Leaves Domain Hooks
 * All leave management API operations via React Query
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
export const leaveKeys = {
  all: ['leaves'],
  lists: () => [...leaveKeys.all, 'list'],
  list: (filters) => [...leaveKeys.lists(), filters],
  my: () => [...leaveKeys.all, 'my'],
  balance: (employeeId) => [...leaveKeys.all, 'balance', employeeId],
  team: (managerId) => [...leaveKeys.all, 'team', managerId],
  pending: () => [...leaveKeys.all, 'pending'],
  calendar: (month) => [...leaveKeys.all, 'calendar', month],
  types: () => [...leaveKeys.all, 'types'],
};

/**
 * Fetch all leaves (admin/HR view)
 */
export const useLeaves = (filters = {}) => {
  return useQuery({
    queryKey: leaveKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      if (filters.leave_type) params.append('leave_type', filters.leave_type);
      if (filters.from_date) params.append('from_date', filters.from_date);
      if (filters.to_date) params.append('to_date', filters.to_date);
      
      const { data } = await axios.get(`${API}/api/leaves?${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch my leaves (employee view)
 */
export const useMyLeaves = () => {
  return useQuery({
    queryKey: leaveKeys.my(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/my/leaves`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch leave balance
 */
export const useLeaveBalance = (employeeId) => {
  return useQuery({
    queryKey: leaveKeys.balance(employeeId),
    queryFn: async () => {
      const endpoint = employeeId 
        ? `${API}/api/leaves/balance/${employeeId}`
        : `${API}/api/my/leave-balance`;
      const { data } = await axios.get(endpoint, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch team leaves (manager view)
 */
export const useTeamLeaves = (managerId, filters = {}) => {
  return useQuery({
    queryKey: [...leaveKeys.team(managerId), filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.month) params.append('month', filters.month);
      
      const { data } = await axios.get(`${API}/api/leaves/team/${managerId}?${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    enabled: !!managerId,
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch pending leave approvals
 */
export const usePendingLeaveApprovals = () => {
  return useQuery({
    queryKey: leaveKeys.pending(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leaves/pending`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 1 * 60 * 1000,
  });
};

/**
 * Fetch leave calendar for a month
 */
export const useLeaveCalendar = (month) => {
  return useQuery({
    queryKey: leaveKeys.calendar(month),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leaves/calendar?month=${month}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!month,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch leave types
 */
export const useLeaveTypes = () => {
  return useQuery({
    queryKey: leaveKeys.types(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/leave-types`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 30 * 60 * 1000, // Leave types rarely change
  });
};

/**
 * Apply for leave
 */
export const useApplyLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leaveData) => {
      const { data } = await axios.post(`${API}/api/leaves`, leaveData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      invalidateCache.leaves();
    },
  });
};

/**
 * Update leave request
 */
export const useUpdateLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ leaveId, updates }) => {
      const { data } = await axios.put(`${API}/api/leaves/${leaveId}`, updates, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
};

/**
 * Cancel leave request
 */
export const useCancelLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leaveId) => {
      const { data } = await axios.post(`${API}/api/leaves/${leaveId}/cancel`, {}, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      invalidateCache.leaves();
    },
  });
};

/**
 * Approve leave
 */
export const useApproveLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ leaveId, remarks }) => {
      const { data } = await axios.post(`${API}/api/leaves/${leaveId}/approve`, 
        { remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      invalidateCache.approvals();
      invalidateCache.leaves();
    },
  });
};

/**
 * Reject leave
 */
export const useRejectLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ leaveId, reason }) => {
      const { data } = await axios.post(`${API}/api/leaves/${leaveId}/reject`, 
        { reason },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      invalidateCache.approvals();
      invalidateCache.leaves();
    },
  });
};

/**
 * Delete leave request
 */
export const useDeleteLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leaveId) => {
      await axios.delete(`${API}/api/leaves/${leaveId}`, {
        headers: getAuthHeaders(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
};

export default {
  useLeaves,
  useMyLeaves,
  useLeaveBalance,
  useTeamLeaves,
  usePendingLeaveApprovals,
  useLeaveCalendar,
  useLeaveTypes,
  useApplyLeave,
  useUpdateLeave,
  useCancelLeave,
  useApproveLeave,
  useRejectLeave,
  useDeleteLeave,
};
