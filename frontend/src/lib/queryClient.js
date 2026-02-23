/**
 * React Query Configuration
 * Provides caching, background refetching, and optimistic updates
 * 
 * Performance Optimization: December 2025
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Configure QueryClient with optimal defaults
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache data for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Keep unused data in cache for 30 minutes
      cacheTime: 30 * 60 * 1000,
      // Retry failed requests 1 time
      retry: 1,
      // Don't refetch on window focus (reduces API calls)
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
  
  // Single items
  employee: (id) => ['employee', id],
  lead: (id) => ['lead', id],
  project: (id) => ['project', id],
  
  // Analytics
  funnelSummary: (period) => ['analytics', 'funnel', period],
  bottleneckAnalysis: (period) => ['analytics', 'bottleneck', period],
  forecasting: (period) => ['analytics', 'forecasting', period],
  
  // User permissions
  userPermissions: ['user', 'permissions'],
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
  
  // Invalidate all caches
  all: () => {
    queryClient.invalidateQueries();
  },
};

export { QueryClientProvider };
