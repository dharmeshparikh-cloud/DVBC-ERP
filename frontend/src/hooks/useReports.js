/**
 * useReports.js - React Query hooks for Reports management
 * 
 * Handles report listing, preview, generation, and categories.
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
  if (data?.reports) return data.reports;
  return [];
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all reports
 */
export const useReportsList = (options = {}) => {
  return useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/reports`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    ...options
  });
};

/**
 * Fetch report categories
 */
export const useReportCategories = (options = {}) => {
  return useQuery({
    queryKey: ['reports', 'categories'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/reports/categories`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 30 * 60 * 1000, // 30 minutes - rarely changes
    ...options
  });
};

/**
 * Fetch report statistics
 */
export const useReportStats = (options = {}) => {
  return useQuery({
    queryKey: ['reports', 'stats'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/reports/stats`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch report preview
 */
export const useReportPreview = (reportId, options = {}) => {
  return useQuery({
    queryKey: ['reports', reportId, 'preview'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/reports/${reportId}/preview`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!reportId,
    staleTime: 1 * 60 * 1000, // 1 minute - data might change
    ...options
  });
};

/**
 * Fetch saved report configurations
 */
export const useSavedReports = (options = {}) => {
  return useQuery({
    queryKey: ['reports', 'saved'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/reports/saved`, { headers: getHeaders() });
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
 * Generate/export report
 */
export const useGenerateReport = () => {
  return useMutation({
    mutationFn: async ({ reportId, format, filters }) => {
      const res = await axios.post(
        `${API}/api/reports/${reportId}/generate`,
        { format, filters },
        { headers: getHeaders(), responseType: format === 'json' ? 'json' : 'blob' }
      );
      return res.data;
    }
  });
};

/**
 * Save report configuration
 */
export const useSaveReportConfig = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (config) => {
      const res = await axios.post(`${API}/api/reports/save`, config, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', 'saved'] });
    }
  });
};

/**
 * Delete saved report
 */
export const useDeleteSavedReport = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (reportId) => {
      const res = await axios.delete(`${API}/api/reports/saved/${reportId}`, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', 'saved'] });
    }
  });
};

/**
 * Schedule report
 */
export const useScheduleReport = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ reportId, schedule }) => {
      const res = await axios.post(`${API}/api/reports/${reportId}/schedule`, schedule, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    }
  });
};

export default {
  useReportsList,
  useReportCategories,
  useReportStats,
  useReportPreview,
  useSavedReports,
  useGenerateReport,
  useSaveReportConfig,
  useDeleteSavedReport,
  useScheduleReport
};
