/**
 * useClients.js - React Query hooks for Client management
 * 
 * Handles client listing, details, and CRUD operations.
 * Eliminates duplicate /clients API calls across 6+ files.
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
  if (data?.clients) return data.clients;
  return [];
};

// Query key factory
export const clientKeys = {
  all: ['clients'],
  list: () => [...clientKeys.all, 'list'],
  detail: (id) => [...clientKeys.all, 'detail', id],
  contacts: (id) => [...clientKeys.all, id, 'contacts'],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all clients
 */
export const useClientsList = (options = {}) => {
  return useQuery({
    queryKey: clientKeys.list(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/clients`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options
  });
};

/**
 * Fetch client details
 */
export const useClientDetails = (clientId, options = {}) => {
  return useQuery({
    queryKey: clientKeys.detail(clientId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/clients/${clientId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!clientId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch client contacts
 */
export const useClientContacts = (clientId, options = {}) => {
  return useQuery({
    queryKey: clientKeys.contacts(clientId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/clients/${clientId}/contacts`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Create client
 */
export const useCreateClient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (clientData) => {
      const res = await axios.post(`${API}/api/clients`, clientData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: clientKeys.all });
    }
  });
};

/**
 * Update client
 */
export const useUpdateClient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ clientId, data }) => {
      const res = await axios.patch(`${API}/api/clients/${clientId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { clientId }) => {
      queryClient.invalidateQueries({ queryKey: clientKeys.all });
      queryClient.invalidateQueries({ queryKey: clientKeys.detail(clientId) });
    }
  });
};

/**
 * Delete client
 */
export const useDeleteClient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (clientId) => {
      const res = await axios.delete(`${API}/api/clients/${clientId}`, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: clientKeys.all });
    }
  });
};

/**
 * Add client contact
 */
export const useAddClientContact = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ clientId, contact }) => {
      const res = await axios.post(`${API}/api/clients/${clientId}/contacts`, contact, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { clientId }) => {
      queryClient.invalidateQueries({ queryKey: clientKeys.contacts(clientId) });
    }
  });
};

export default {
  clientKeys,
  useClientsList,
  useClientDetails,
  useClientContacts,
  useCreateClient,
  useUpdateClient,
  useDeleteClient,
  useAddClientContact
};
