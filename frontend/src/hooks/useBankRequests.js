/**
 * useBankRequests.js - React Query hooks for Bank Details Change Requests
 * 
 * Handles employee bank details change requests.
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
  if (data?.requests) return data.requests;
  return [];
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch my bank change requests
 */
export const useMyBankRequests = (options = {}) => {
  return useQuery({
    queryKey: ['bank-requests', 'my'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/bank-change-requests`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch current bank details
 */
export const useMyBankDetails = (options = {}) => {
  return useQuery({
    queryKey: ['bank-details', 'my'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/bank-details`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Submit bank change request
 */
export const useSubmitBankChangeRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (bankData) => {
      const res = await axios.post(`${API}/api/my/bank-change-request`, bankData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bank-requests'] });
    }
  });
};

/**
 * Upload bank proof document
 */
export const useUploadBankProof = () => {
  return useMutation({
    mutationFn: async ({ requestId, file }) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await axios.post(`${API}/api/bank-change-requests/${requestId}/upload-proof`, formData, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      return res.data;
    }
  });
};

/**
 * Validate IFSC code
 */
export const useValidateIFSC = () => {
  return useMutation({
    mutationFn: async (ifscCode) => {
      const res = await axios.get(`${API}/api/validate-ifsc/${ifscCode}`, { headers: getHeaders() });
      return res.data;
    }
  });
};

export default {
  useMyBankRequests,
  useMyBankDetails,
  useSubmitBankChangeRequest,
  useUploadBankProof,
  useValidateIFSC
};
