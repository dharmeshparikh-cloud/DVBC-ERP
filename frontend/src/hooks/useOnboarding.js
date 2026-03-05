/**
 * Onboarding Domain Hooks
 * All candidate onboarding API operations via React Query
 * 
 * PERFORMANCE OPTIMIZED - December 2025
 * - Reduced staleTime for faster updates
 * - Optimistic updates for instant UI feedback
 * - Comprehensive cache invalidation for workflow sync
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { invalidateCache } from '../lib/queryClient';

const API = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Query Keys - Structured for efficient invalidation
export const onboardingKeys = {
  all: ['onboarding'],
  candidates: () => [...onboardingKeys.all, 'candidates'],
  candidateList: (filters) => [...onboardingKeys.candidates(), 'list', filters],
  candidate: (id) => [...onboardingKeys.candidates(), 'detail', id],
  documents: (candidateId) => [...onboardingKeys.all, 'documents', candidateId],
  submissions: () => [...onboardingKeys.all, 'submissions'],
  submissionList: (filters) => [...onboardingKeys.submissions(), 'list', filters],
  submission: (id) => [...onboardingKeys.submissions(), 'detail', id],
  goLive: () => [...onboardingKeys.all, 'go-live'],
  goLiveList: (filters) => [...onboardingKeys.goLive(), 'list', filters],
  stats: () => [...onboardingKeys.all, 'stats'],
};

// ==================== QUERIES ====================

/**
 * Fetch onboarding candidates with filters
 */
export const useOnboardingCandidates = (filters = {}) => {
  const { status, search, page = 1, pageSize = 50 } = filters;
  
  return useQuery({
    queryKey: onboardingKeys.candidateList({ status, search, page, pageSize }),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (search) params.append('search', search);
      params.append('page', page);
      params.append('page_size', pageSize);
      
      const { data } = await axios.get(`${API}/api/onboarding-candidates?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes for faster updates
    gcTime: 10 * 60 * 1000,
    keepPreviousData: true,
  });
};

/**
 * Fetch onboarding submissions (new flow)
 */
export const useOnboardingSubmissions = (filters = {}) => {
  const { status, search } = filters;
  
  return useQuery({
    queryKey: onboardingKeys.submissionList(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (search) params.append('search', search);
      
      const { data } = await axios.get(`${API}/api/onboarding/submissions?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
};

/**
 * Fetch single submission by ID
 */
export const useOnboardingSubmission = (id) => {
  return useQuery({
    queryKey: onboardingKeys.submission(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/onboarding/submissions/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute - more frequent updates for active review
  });
};

/**
 * Fetch single candidate by ID
 */
export const useOnboardingCandidate = (id) => {
  return useQuery({
    queryKey: onboardingKeys.candidate(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/onboarding-candidates/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch candidate documents
 */
export const useCandidateDocuments = (candidateId) => {
  return useQuery({
    queryKey: onboardingKeys.documents(candidateId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/onboarding-candidates/${candidateId}/documents`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!candidateId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch go-live requests
 */
export const useGoLiveRequests = (filters = {}) => {
  const { status, page = 1, pageSize = 50 } = filters;
  
  return useQuery({
    queryKey: onboardingKeys.goLiveList({ status, page, pageSize }),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      params.append('page', page);
      params.append('page_size', pageSize);
      
      const { data } = await axios.get(`${API}/api/go-live/requests?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch onboarding stats
 */
export const useOnboardingStats = () => {
  return useQuery({
    queryKey: onboardingKeys.stats(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/onboarding/stats`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

// ==================== MUTATIONS ====================

/**
 * Create onboarding candidate
 */
export const useCreateCandidate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (candidateData) => {
      const { data } = await axios.post(`${API}/api/onboarding-candidates`, candidateData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidates() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.stats() });
    },
  });
};

/**
 * Update onboarding candidate
 */
export const useUpdateCandidate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...candidateData }) => {
      const { data } = await axios.patch(`${API}/api/onboarding-candidates/${id}`, candidateData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidates() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidate(variables.id) });
    },
  });
};

/**
 * Submit candidate for verification
 */
export const useSubmitForVerification = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (candidateId) => {
      const { data } = await axios.post(
        `${API}/api/onboarding-candidates/${candidateId}/submit-for-verification`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, candidateId) => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidates() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidate(candidateId) });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.stats() });
    },
  });
};

/**
 * Verify candidate (HR action)
 */
export const useVerifyCandidate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ candidateId, action, remarks }) => {
      const { data } = await axios.post(
        `${API}/api/onboarding-candidates/${candidateId}/verify`,
        { action, remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidates() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidate(variables.candidateId) });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.stats() });
    },
  });
};

/**
 * Initiate go-live request
 */
export const useInitiateGoLive = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (candidateId) => {
      const { data } = await axios.post(
        `${API}/api/go-live/initiate/${candidateId}`,
        {},
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidates() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.goLive() });
    },
  });
};

/**
 * Approve go-live request (generates employee_id)
 * CRITICAL: Invalidates all related caches for instant workflow sync
 */
export const useApproveGoLive = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      const { data } = await axios.post(
        `${API}/api/go-live/approve/${requestId}`,
        { remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      // Comprehensive invalidation for workflow sync
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all });
      queryClient.invalidateQueries({ queryKey: ['employees'] });
      queryClient.invalidateQueries({ queryKey: ['go-live'] });
      // Also invalidate HR stats and dashboard
      invalidateCache.dashboardStats();
    },
  });
};

/**
 * Reject go-live request
 */
export const useRejectGoLive = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, remarks }) => {
      const { data } = await axios.post(
        `${API}/api/go-live/reject/${requestId}`,
        { remarks },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.goLive() });
    },
  });
};

/**
 * Upload candidate document
 */
export const useUploadDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ candidateId, formData }) => {
      const { data } = await axios.post(
        `${API}/api/onboarding-candidates/${candidateId}/documents`,
        formData,
        { 
          headers: { 
            ...getAuthHeaders(),
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.documents(variables.candidateId) });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.candidate(variables.candidateId) });
    },
  });
};

export default {
  useOnboardingCandidates,
  useOnboardingCandidate,
  useCandidateDocuments,
  useGoLiveRequests,
  useOnboardingStats,
  useCreateCandidate,
  useUpdateCandidate,
  useSubmitForVerification,
  useVerifyCandidate,
  useInitiateGoLive,
  useApproveGoLive,
  useRejectGoLive,
  useUploadDocument,
};
