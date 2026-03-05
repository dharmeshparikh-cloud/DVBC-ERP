/**
 * useSOW.js - React Query hooks for Statement of Work management
 * 
 * Handles SOW creation, change requests, and approvals.
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
  if (data?.sows) return data.sows;
  return [];
};

// Query key factory
export const sowKeys = {
  all: ['sow'],
  list: () => [...sowKeys.all, 'list'],
  detail: (id) => [...sowKeys.all, 'detail', id],
  changeRequests: () => [...sowKeys.all, 'change-requests'],
  changeRequest: (id) => [...sowKeys.all, 'change-request', id],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all SOWs
 */
export const useSOWList = (options = {}) => {
  return useQuery({
    queryKey: sowKeys.list(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sow`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch SOW detail
 */
export const useSOWDetail = (sowId, options = {}) => {
  return useQuery({
    queryKey: sowKeys.detail(sowId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sow/${sowId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!sowId,
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch SOW change requests
 */
export const useSOWChangeRequests = (status = '', options = {}) => {
  return useQuery({
    queryKey: [...sowKeys.changeRequests(), status],
    queryFn: async () => {
      const url = status 
        ? `${API}/api/sow/change-requests?status=${status}`
        : `${API}/api/sow/change-requests`;
      const res = await axios.get(url, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch SOW change request detail
 */
export const useSOWChangeRequestDetail = (requestId, options = {}) => {
  return useQuery({
    queryKey: sowKeys.changeRequest(requestId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sow/change-requests/${requestId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!requestId,
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Create SOW
 */
export const useCreateSOW = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (sowData) => {
      const res = await axios.post(`${API}/api/sow`, sowData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sowKeys.all });
    }
  });
};

/**
 * Update SOW
 */
export const useUpdateSOW = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ sowId, data }) => {
      const res = await axios.patch(`${API}/api/sow/${sowId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { sowId }) => {
      queryClient.invalidateQueries({ queryKey: sowKeys.all });
      queryClient.invalidateQueries({ queryKey: sowKeys.detail(sowId) });
    }
  });
};

/**
 * Submit SOW change request
 */
export const useSubmitSOWChangeRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ sowId, changes, reason }) => {
      const res = await axios.post(`${API}/api/sow/${sowId}/change-request`, { changes, reason }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sowKeys.changeRequests() });
    }
  });
};

/**
 * Approve SOW change request
 */
export const useApproveSOWChangeRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(`${API}/api/sow/change-requests/${requestId}/approve`, {}, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sowKeys.all });
      queryClient.invalidateQueries({ queryKey: sowKeys.changeRequests() });
    }
  });
};

/**
 * Reject SOW change request
 */
export const useRejectSOWChangeRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(`${API}/api/sow/change-requests/${requestId}/reject`, { reason }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sowKeys.changeRequests() });
    }
  });
};

export default {
  sowKeys,
  useSOWList,
  useSOWDetail,
  useSOWChangeRequests,
  useSOWChangeRequestDetail,
  useCreateSOW,
  useUpdateSOW,
  useSubmitSOWChangeRequest,
  useApproveSOWChangeRequest,
  useRejectSOWChangeRequest
};
