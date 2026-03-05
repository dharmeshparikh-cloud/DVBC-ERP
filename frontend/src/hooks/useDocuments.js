/**
 * useDocuments.js - React Query hooks for Document management
 * 
 * Handles document templates, history, and generation.
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
  if (data?.documents) return data.documents;
  return [];
};

// Query key factory
export const documentKeys = {
  all: ['documents'],
  templates: () => [...documentKeys.all, 'templates'],
  history: (filters) => [...documentKeys.all, 'history', filters],
  detail: (id) => [...documentKeys.all, 'detail', id],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch document templates
 */
export const useDocumentTemplates = (options = {}) => {
  return useQuery({
    queryKey: documentKeys.templates(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/document-templates`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - templates rarely change
    ...options
  });
};

/**
 * Fetch document history
 */
export const useDocumentHistory = (filters = {}, options = {}) => {
  const queryParams = new URLSearchParams();
  if (filters.limit) queryParams.set('limit', filters.limit);
  if (filters.type) queryParams.set('type', filters.type);
  if (filters.employee_id) queryParams.set('employee_id', filters.employee_id);
  
  return useQuery({
    queryKey: documentKeys.history(filters),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/document-history?${queryParams}`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch document detail
 */
export const useDocumentDetail = (documentId, options = {}) => {
  return useQuery({
    queryKey: documentKeys.detail(documentId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/document-history/${documentId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!documentId,
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Generate document
 */
export const useGenerateDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ type, employeeId, data }) => {
      const res = await axios.post(`${API}/api/document-history`, 
        { document_type: type, employee_id: employeeId, ...data },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    }
  });
};

/**
 * Download document
 */
export const useDownloadDocument = () => {
  return useMutation({
    mutationFn: async ({ documentId, format }) => {
      const res = await axios.get(
        `${API}/api/document-history/${documentId}/download?format=${format}`,
        { headers: getHeaders(), responseType: 'blob' }
      );
      return res.data;
    }
  });
};

/**
 * Send document via email
 */
export const useSendDocumentEmail = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ documentId, emailData }) => {
      const res = await axios.post(
        `${API}/api/document-history/${documentId}/send-email`,
        emailData,
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { documentId }) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.detail(documentId) });
    }
  });
};

/**
 * Delete document
 */
export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (documentId) => {
      const res = await axios.delete(`${API}/api/document-history/${documentId}`, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    }
  });
};

export default {
  documentKeys,
  useDocumentTemplates,
  useDocumentHistory,
  useDocumentDetail,
  useGenerateDocument,
  useDownloadDocument,
  useSendDocumentEmail,
  useDeleteDocument
};
