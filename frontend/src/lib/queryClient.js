/**
 * React Query Configuration
 * Provides caching, background refetching, and optimistic updates
 * 
 * REACT QUERY ENFORCEMENT - March 2026
 * This is the MANDATORY data layer for all API communication.
 * Direct axios/fetch in components is NOT allowed.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Configure QueryClient with optimal defaults
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache data for 5 minutes (minimum staleTime per rule)
      staleTime: 5 * 60 * 1000, // 300000ms
      // Keep unused data in cache for 30 minutes
      cacheTime: 30 * 60 * 1000,
      // Retry failed requests 2 times (per enforcement rule)
      retry: 2,
      // Don't refetch on window focus (per enforcement rule)
      refetchOnWindowFocus: false,
      // Refetch on reconnect
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});

// Query keys for consistent cache management
export const queryKeys = {
  // Dashboard stats
  dashboardStats: ['dashboard', 'stats'],
  hrStats: ['hr', 'stats'],
  salesStats: ['sales', 'stats'],
  consultingStats: ['consulting', 'stats'],
  
  // Lists with pagination
  employees: (filters = {}) => ['employees', filters],
  leads: (filters = {}) => ['leads', filters],
  projects: (filters = {}) => ['projects', filters],
  expenses: (filters = {}) => ['expenses', filters],
  agreements: (filters = {}) => ['agreements', filters],
  kickoffRequests: (filters = {}) => ['kickoff-requests', filters],
  encashmentRequests: (filters = {}) => ['encashment-requests', filters],
  travelReimbursements: (filters = {}) => ['travel-reimbursements', filters],
  
  // Single items
  employee: (id) => ['employee', id],
  lead: (id) => ['lead', id],
  project: (id) => ['project', id],
  agreement: (id) => ['agreement', id],
  
  // Analytics
  funnelSummary: (period) => ['analytics', 'funnel', period],
  bottleneckAnalysis: (period) => ['analytics', 'bottleneck', period],
  forecasting: (period) => ['analytics', 'forecasting', period],
  
  // User permissions
  userPermissions: ['user', 'permissions'],
  
  // Notifications
  notifications: ['notifications'],
};

// Cache invalidation helpers
export const invalidateCache = {
  // Invalidate all dashboard stats
  dashboardStats: () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['sales', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['consulting', 'stats'] });
  },
  
  // Invalidate employee-related caches
  employees: () => {
    queryClient.invalidateQueries({ queryKey: ['employees'] });
  },
  
  // Invalidate lead-related caches
  leads: () => {
    queryClient.invalidateQueries({ queryKey: ['leads'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'funnel'] });
  },
  
  // Invalidate project-related caches
  projects: () => {
    queryClient.invalidateQueries({ queryKey: ['projects'] });
    queryClient.invalidateQueries({ queryKey: ['consulting', 'stats'] });
  },
  
  // Invalidate expense-related caches
  expenses: () => {
    queryClient.invalidateQueries({ queryKey: ['expenses'] });
  },
  
  // Invalidate agreement-related caches
  agreements: () => {
    queryClient.invalidateQueries({ queryKey: ['agreements'] });
  },
  
  // Invalidate kickoff-related caches
  kickoffs: () => {
    queryClient.invalidateQueries({ queryKey: ['kickoff-requests'] });
  },
  
  // Invalidate notifications
  notifications: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  },
  
  // Invalidate all caches
  all: () => {
    queryClient.invalidateQueries();
  },
};

export { QueryClientProvider };
