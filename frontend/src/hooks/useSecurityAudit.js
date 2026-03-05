/**
 * useSecurityAudit.js - React Query hooks for Security Audit Logs
 * 
 * Handles audit log viewing and filtering.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

const extractArray = (data) => {
  if (Array.isArray(data)) return data;
  if (data?.items) return data.items;
  if (data?.logs) return data.logs;
  return [];
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch audit logs with filters
 */
export const useAuditLogs = (filters = {}, options = {}) => {
  const queryParams = new URLSearchParams();
  if (filters.action) queryParams.set('action', filters.action);
  if (filters.user_id) queryParams.set('user_id', filters.user_id);
  if (filters.entity_type) queryParams.set('entity_type', filters.entity_type);
  if (filters.start_date) queryParams.set('start_date', filters.start_date);
  if (filters.end_date) queryParams.set('end_date', filters.end_date);
  if (filters.limit) queryParams.set('limit', filters.limit);
  if (filters.skip) queryParams.set('skip', filters.skip);
  
  return useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/audit-logs?${queryParams}`, { headers: getHeaders() });
      return {
        logs: extractArray(res.data),
        total: res.data?.total || 0,
        pagination: res.data?.pagination || {}
      };
    },
    staleTime: 1 * 60 * 1000, // 1 minute - frequently updated
    ...options
  });
};

/**
 * Fetch audit log stats
 */
export const useAuditStats = (options = {}) => {
  return useQuery({
    queryKey: ['audit-logs', 'stats'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/audit-logs/stats`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch audit action types
 */
export const useAuditActionTypes = (options = {}) => {
  return useQuery({
    queryKey: ['audit-logs', 'action-types'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/audit-logs/action-types`, { headers: getHeaders() });
      return res.data?.actions || res.data || [];
    },
    staleTime: 30 * 60 * 1000, // 30 minutes - rarely changes
    ...options
  });
};

export default {
  useAuditLogs,
  useAuditStats,
  useAuditActionTypes
};
