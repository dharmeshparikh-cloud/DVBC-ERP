/**
 * useMeetings.js - React Query hooks for Meetings management
 * 
 * Handles meeting records, scheduling, and updates.
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
  if (data?.meetings) return data.meetings;
  return [];
};

// Query key factory
export const meetingKeys = {
  all: ['meetings'],
  list: (filters) => [...meetingKeys.all, 'list', filters],
  detail: (id) => [...meetingKeys.all, 'detail', id],
  lead: (leadId) => [...meetingKeys.all, 'lead', leadId],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch meetings list
 */
export const useMeetingsList = (filters = {}, options = {}) => {
  return useQuery({
    queryKey: meetingKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.date) params.set('date', filters.date);
      if (filters.lead_id) params.set('lead_id', filters.lead_id);
      
      const res = await axios.get(`${API}/api/meetings?${params}`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch meeting detail
 */
export const useMeetingDetail = (meetingId, options = {}) => {
  return useQuery({
    queryKey: meetingKeys.detail(meetingId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/meetings/${meetingId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!meetingId,
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch meetings for a lead
 */
export const useLeadMeetings = (leadId, options = {}) => {
  return useQuery({
    queryKey: meetingKeys.lead(leadId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/leads/${leadId}/meetings`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled: !!leadId,
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Create meeting
 */
export const useCreateMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (meetingData) => {
      const res = await axios.post(`${API}/api/meetings`, meetingData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: meetingKeys.all });
      if (variables.lead_id) {
        queryClient.invalidateQueries({ queryKey: meetingKeys.lead(variables.lead_id) });
        queryClient.invalidateQueries({ queryKey: ['leads'] });
      }
    }
  });
};

/**
 * Update meeting
 */
export const useUpdateMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ meetingId, data }) => {
      const res = await axios.patch(`${API}/api/meetings/${meetingId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { meetingId }) => {
      queryClient.invalidateQueries({ queryKey: meetingKeys.all });
      queryClient.invalidateQueries({ queryKey: meetingKeys.detail(meetingId) });
    }
  });
};

/**
 * Complete meeting with outcome
 */
export const useCompleteMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ meetingId, outcome, notes, nextSteps }) => {
      const res = await axios.post(`${API}/api/meetings/${meetingId}/complete`, 
        { outcome, notes, next_steps: nextSteps }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { meetingId }) => {
      queryClient.invalidateQueries({ queryKey: meetingKeys.all });
      queryClient.invalidateQueries({ queryKey: meetingKeys.detail(meetingId) });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    }
  });
};

/**
 * Cancel meeting
 */
export const useCancelMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ meetingId, reason }) => {
      const res = await axios.post(`${API}/api/meetings/${meetingId}/cancel`, { reason }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: meetingKeys.all });
    }
  });
};

/**
 * Reschedule meeting
 */
export const useRescheduleMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ meetingId, newDate, reason }) => {
      const res = await axios.post(`${API}/api/meetings/${meetingId}/reschedule`, 
        { new_date: newDate, reason }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { meetingId }) => {
      queryClient.invalidateQueries({ queryKey: meetingKeys.all });
      queryClient.invalidateQueries({ queryKey: meetingKeys.detail(meetingId) });
    }
  });
};

export default {
  meetingKeys,
  useMeetingsList,
  useMeetingDetail,
  useLeadMeetings,
  useCreateMeeting,
  useUpdateMeeting,
  useCompleteMeeting,
  useCancelMeeting,
  useRescheduleMeeting
};
