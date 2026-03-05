/**
 * usePricingPlans.js - React Query hooks for Pricing Plans
 * 
 * Handles pricing plan templates, custom plans, and SOW pricing.
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
  if (data?.plans) return data.plans;
  return [];
};

// Query key factory
export const pricingKeys = {
  all: ['pricing-plans'],
  list: () => [...pricingKeys.all, 'list'],
  detail: (id) => [...pricingKeys.all, 'detail', id],
  templates: () => [...pricingKeys.all, 'templates'],
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all pricing plans
 */
export const usePricingPlansList = (options = {}) => {
  return useQuery({
    queryKey: pricingKeys.list(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/pricing-plans`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options
  });
};

/**
 * Fetch pricing plan detail
 */
export const usePricingPlanDetail = (planId, options = {}) => {
  return useQuery({
    queryKey: pricingKeys.detail(planId),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/pricing-plans/${planId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!planId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch pricing plan templates
 */
export const usePricingTemplates = (options = {}) => {
  return useQuery({
    queryKey: pricingKeys.templates(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/pricing-plans/templates`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - rarely changes
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Create pricing plan
 */
export const useCreatePricingPlan = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (planData) => {
      const res = await axios.post(`${API}/api/pricing-plans`, planData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pricingKeys.all });
    }
  });
};

/**
 * Update pricing plan
 */
export const useUpdatePricingPlan = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ planId, data }) => {
      const res = await axios.patch(`${API}/api/pricing-plans/${planId}`, data, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: pricingKeys.all });
      queryClient.invalidateQueries({ queryKey: pricingKeys.detail(planId) });
    }
  });
};

/**
 * Delete pricing plan
 */
export const useDeletePricingPlan = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (planId) => {
      const res = await axios.delete(`${API}/api/pricing-plans/${planId}`, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pricingKeys.all });
    }
  });
};

/**
 * Clone pricing plan
 */
export const useClonePricingPlan = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ planId, newName }) => {
      const res = await axios.post(`${API}/api/pricing-plans/${planId}/clone`, { name: newName }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pricingKeys.all });
    }
  });
};

export default {
  pricingKeys,
  usePricingPlansList,
  usePricingPlanDetail,
  usePricingTemplates,
  useCreatePricingPlan,
  useUpdatePricingPlan,
  useDeletePricingPlan,
  useClonePricingPlan
};
