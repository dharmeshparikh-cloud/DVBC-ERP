/**
 * Attendance Domain Hooks
 * All attendance management API operations via React Query
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
export const attendanceKeys = {
  all: ['attendance'],
  lists: () => [...attendanceKeys.all, 'list'],
  list: (filters) => [...attendanceKeys.lists(), filters],
  my: () => [...attendanceKeys.all, 'my'],
  myToday: () => [...attendanceKeys.my(), 'today'],
  myMonth: (month) => [...attendanceKeys.my(), 'month', month],
  team: (managerId) => [...attendanceKeys.all, 'team', managerId],
  pending: () => [...attendanceKeys.all, 'pending'],
  stats: () => [...attendanceKeys.all, 'stats'],
};

/**
 * Fetch all attendance records (admin/HR view)
 */
export const useAttendance = (filters = {}) => {
  return useQuery({
    queryKey: attendanceKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.date) params.append('date', filters.date);
      if (filters.month) params.append('month', filters.month);
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      if (filters.department) params.append('department', filters.department);
      
      const { data } = await axios.get(`${API}/api/attendance?${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch my attendance (employee view)
 */
export const useMyAttendance = (month) => {
  return useQuery({
    queryKey: attendanceKeys.myMonth(month),
    queryFn: async () => {
      const params = month ? `?month=${month}` : '';
      const { data } = await axios.get(`${API}/api/my/attendance${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Check my attendance status for today
 */
export const useMyAttendanceStatus = () => {
  return useQuery({
    queryKey: attendanceKeys.myToday(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/my/check-status`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 1 * 60 * 1000, // Refresh more frequently
  });
};

/**
 * Fetch team attendance (manager view)
 */
export const useTeamAttendance = (managerId, filters = {}) => {
  return useQuery({
    queryKey: [...attendanceKeys.team(managerId), filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.date) params.append('date', filters.date);
      if (filters.month) params.append('month', filters.month);
      
      const { data } = await axios.get(`${API}/api/attendance/team/${managerId}?${params}`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    enabled: !!managerId,
    staleTime: 2 * 60 * 1000,
  });
};

/**
 * Fetch pending attendance approvals
 */
export const usePendingAttendanceApprovals = () => {
  return useQuery({
    queryKey: attendanceKeys.pending(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/attendance/pending-approvals`, {
        headers: getAuthHeaders(),
      });
      return data?.items || data || [];
    },
    staleTime: 1 * 60 * 1000,
  });
};

/**
 * Check in
 */
export const useCheckIn = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (checkInData = {}) => {
      const { data } = await axios.post(`${API}/api/attendance/check-in`, checkInData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.my() });
      queryClient.invalidateQueries({ queryKey: attendanceKeys.myToday() });
      invalidateCache.attendance();
    },
  });
};

/**
 * Check out
 */
export const useCheckOut = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (checkOutData = {}) => {
      const { data } = await axios.post(`${API}/api/attendance/check-out`, checkOutData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.my() });
      queryClient.invalidateQueries({ queryKey: attendanceKeys.myToday() });
      invalidateCache.attendance();
    },
  });
};

/**
 * Request regularization
 */
export const useRequestRegularization = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (regularizationData) => {
      const { data } = await axios.post(`${API}/api/attendance/regularization`, regularizationData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.my() });
    },
  });
};

/**
 * Approve regularization
 */
export const useApproveRegularization = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      const { data } = await axios.post(`${API}/api/attendance/regularization/${requestId}/approve`, 
        { remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
      invalidateCache.approvals();
    },
  });
};

/**
 * Reject regularization
 */
export const useRejectRegularization = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const { data } = await axios.post(`${API}/api/attendance/regularization/${requestId}/reject`, 
        { reason },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
      invalidateCache.approvals();
    },
  });
};

/**
 * Bulk update attendance (HR only)
 */
export const useBulkUpdateAttendance = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (updates) => {
      const { data } = await axios.post(`${API}/api/attendance/bulk-update`, updates, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
      invalidateCache.attendance();
    },
  });
};

export default {
  useAttendance,
  useMyAttendance,
  useMyAttendanceStatus,
  useTeamAttendance,
  usePendingAttendanceApprovals,
  useCheckIn,
  useCheckOut,
  useRequestRegularization,
  useApproveRegularization,
  useRejectRegularization,
  useBulkUpdateAttendance,
};
