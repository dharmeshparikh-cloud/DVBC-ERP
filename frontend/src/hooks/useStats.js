/**
 * useStats.js - React Query hooks for Dashboard Statistics
 * 
 * Consolidated stats fetching for Admin, HR, Sales, and Consulting dashboards.
 * Eliminates duplicate stats API calls across dashboard pages.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

// Query key factory
export const statsKeys = {
  all: ['stats'],
  admin: () => [...statsKeys.all, 'admin'],
  hr: () => [...statsKeys.all, 'hr'],
  sales: () => [...statsKeys.all, 'sales'],
  consulting: () => [...statsKeys.all, 'consulting'],
  manager: () => [...statsKeys.all, 'manager'],
};

// ============================================
// ADMIN STATS
// ============================================

/**
 * Fetch admin dashboard stats (combined)
 */
export const useAdminStats = (options = {}) => {
  return useQuery({
    queryKey: statsKeys.admin(),
    queryFn: async () => {
      const [salesRes, hrRes, consultingRes] = await Promise.all([
        axios.get(`${API}/api/stats/sales-dashboard-enhanced?view_mode=team`, { headers: getHeaders() }).catch(() => ({ data: null })),
        axios.get(`${API}/api/stats/hr`, { headers: getHeaders() }).catch(() => ({ data: null })),
        axios.get(`${API}/api/stats/consulting`, { headers: getHeaders() }).catch(() => ({ data: null }))
      ]);
      
      return {
        sales: salesRes.data,
        hr: hrRes.data,
        consulting: consultingRes.data
      };
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options
  });
};

// ============================================
// HR STATS
// ============================================

/**
 * Fetch HR dashboard stats
 */
export const useHRStats = (options = {}) => {
  return useQuery({
    queryKey: statsKeys.hr(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/hr-dashboard`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch HR overview stats
 */
export const useHROverviewStats = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.hr(), 'overview'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/hr`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// SALES STATS
// ============================================

/**
 * Fetch sales dashboard stats
 */
export const useSalesStats = (viewMode = 'personal', options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.sales(), viewMode],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/sales-dashboard-enhanced?view_mode=${viewMode}`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch sales funnel stats
 */
export const useSalesFunnelStats = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.sales(), 'funnel'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/sales-funnel`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// CONSULTING STATS
// ============================================

/**
 * Fetch consulting dashboard stats
 */
export const useConsultingStats = (options = {}) => {
  return useQuery({
    queryKey: statsKeys.consulting(),
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/consulting-dashboard`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch consulting overview
 */
export const useConsultingOverview = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.consulting(), 'overview'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/stats/consulting`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// MANAGER STATS
// ============================================

/**
 * Fetch manager today stats
 */
export const useManagerTodayStats = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.manager(), 'today'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/manager/today-stats`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute - real-time data
    ...options
  });
};

/**
 * Fetch manager performance stats
 */
export const useManagerPerformance = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.manager(), 'performance'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/manager/performance`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch manager target vs achievement
 */
export const useManagerTargetVsAchievement = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.manager(), 'target-achievement'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/manager/target-vs-achievement`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch subordinate leads
 */
export const useSubordinateLeads = (options = {}) => {
  return useQuery({
    queryKey: [...statsKeys.manager(), 'subordinate-leads'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/manager/subordinate-leads`, { headers: getHeaders() });
      return res.data?.leads || res.data || [];
    },
    staleTime: 2 * 60 * 1000,
    ...options
  });
};

// ============================================
// MOBILE STATS
// ============================================

/**
 * Fetch mobile app stats
 */
export const useMobileStats = (options = {}) => {
  return useQuery({
    queryKey: ['stats', 'mobile'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/attendance/mobile-stats`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

export default {
  statsKeys,
  useAdminStats,
  useHRStats,
  useHROverviewStats,
  useSalesStats,
  useSalesFunnelStats,
  useConsultingStats,
  useConsultingOverview,
  useManagerTodayStats,
  useManagerPerformance,
  useManagerTargetVsAchievement,
  useSubordinateLeads,
  useMobileStats
};
