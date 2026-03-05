/**
 * useLetterhead.js - React Query hooks for Letterhead Settings
 * 
 * Handles letterhead templates and customization.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch letterhead settings
 */
export const useLetterheadSettings = (options = {}) => {
  return useQuery({
    queryKey: ['letterhead', 'settings'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/letterhead/settings`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - rarely changes
    ...options
  });
};

/**
 * Fetch letterhead templates
 */
export const useLetterheadTemplates = (options = {}) => {
  return useQuery({
    queryKey: ['letterhead', 'templates'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/letterhead/templates`, { headers: getHeaders() });
      return res.data?.templates || res.data || [];
    },
    staleTime: 10 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Update letterhead settings
 */
export const useUpdateLetterhead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (settings) => {
      const res = await axios.put(`${API}/api/letterhead/settings`, settings, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['letterhead'] });
    }
  });
};

/**
 * Upload letterhead logo
 */
export const useUploadLetterheadLogo = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ file, type }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', type);
      
      const res = await axios.post(`${API}/api/letterhead/upload-logo`, formData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['letterhead'] });
    }
  });
};

/**
 * Preview letterhead
 */
export const usePreviewLetterhead = () => {
  return useMutation({
    mutationFn: async (settings) => {
      const res = await axios.post(`${API}/api/letterhead/preview`, settings, { 
        headers: getHeaders(),
        responseType: 'blob'
      });
      return res.data;
    }
  });
};

export default {
  useLetterheadSettings,
  useLetterheadTemplates,
  useUpdateLetterhead,
  useUploadLetterheadLogo,
  usePreviewLetterhead
};
