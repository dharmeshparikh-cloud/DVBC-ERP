/**
 * React Query Configuration
 * Provides caching, background refetching, and optimistic updates
 * 
 * PERFORMANCE OPTIMIZED - December 2025
 * Target metrics:
 * - Page load < 1.5 seconds
 * - API response < 200 ms
 * - Form submission < 300 ms
 * - Instant workflow sync
 */

import { QueryClient } from '@tanstack/react-query';

// Configure QueryClient with performance-optimized defaults
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache data for 2 minutes (balance between freshness and performance)
      staleTime: 2 * 60 * 1000, // 120000ms
      // Keep unused data in cache for 10 minutes
      gcTime: 10 * 60 * 1000,
      // Retry failed requests once (faster failure)
      retry: 1,
      // Don't refetch on window focus (reduces unnecessary API calls)
      refetchOnWindowFocus: false,
      // Refetch on reconnect for data freshness
      refetchOnReconnect: true,
      // Refetch on mount only if data is stale
      refetchOnMount: true,
      // Network mode for offline support
      networkMode: 'offlineFirst',
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
      // Network mode
      networkMode: 'offlineFirst',
    },
  },
});

// Query keys for consistent cache management
export const queryKeys = {
  // Dashboard stats - grouped for efficient invalidation
  dashboardStats: ['dashboard', 'stats'],
  hrStats: ['hr', 'stats'],
  salesStats: ['sales', 'stats'],
  consultingStats: ['consulting', 'stats'],
  adminStats: ['admin', 'stats'],
  
  // Lists with pagination
  employees: (filters = {}) => ['employees', 'list', filters],
  employeesAll: ['employees', 'all'],
  leads: (filters = {}) => ['leads', 'list', filters],
  projects: (filters = {}) => ['projects', 'list', filters],
  expenses: (filters = {}) => ['expenses', filters],
  agreements: (filters = {}) => ['agreements', filters],
  kickoffRequests: (filters = {}) => ['kickoff-requests', filters],
  encashmentRequests: (filters = {}) => ['encashment-requests', filters],
  travelReimbursements: (filters = {}) => ['travel-reimbursements', filters],
  
  // Onboarding - critical for HR workflow
  onboardingSubmissions: (filters = {}) => ['onboarding', 'submissions', filters],
  onboardingSubmission: (id) => ['onboarding', 'submission', id],
  goLiveEmployees: (filters = {}) => ['go-live', 'employees', filters],
  
  // Single items
  employee: (id) => ['employees', 'detail', id],
  lead: (id) => ['leads', 'detail', id],
  project: (id) => ['projects', 'detail', id],
  agreement: (id) => ['agreements', 'detail', id],
  
  // Attendance & Leaves
  attendance: (filters = {}) => ['attendance', filters],
  myAttendance: ['attendance', 'my'],
  leaves: (filters = {}) => ['leaves', filters],
  myLeaves: ['leaves', 'my'],
  leaveBalance: (employeeId) => ['leaves', 'balance', employeeId],
  
  // Payroll
  salarySlips: (month) => ['payroll', 'slips', month],
  salaryComponents: ['payroll', 'components'],
  payrollInputs: (month) => ['payroll', 'inputs', month],
  
  // Documents
  documents: (filters = {}) => ['documents', filters],
  documentTemplates: ['documents', 'templates'],
  
  // Analytics
  funnelSummary: (period) => ['analytics', 'funnel', period],
  bottleneckAnalysis: (period) => ['analytics', 'bottleneck', period],
  forecasting: (period) => ['analytics', 'forecasting', period],
  
  // User permissions
  userPermissions: ['user', 'permissions'],
  
  // Notifications
  notifications: ['notifications'],
  
  // Approvals
  pendingApprovals: ['approvals', 'pending'],
  approvalCounts: ['approvals', 'counts'],
};

// ===========================================
// CACHE INVALIDATION HELPERS
// Optimized for workflow synchronization
// ===========================================

export const invalidateCache = {
  // Invalidate all dashboard stats (when critical data changes)
  dashboardStats: () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['sales', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['consulting', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['approvals', 'counts'] });
  },
  
  // HR Module - Employee workflow
  employees: () => {
    queryClient.invalidateQueries({ queryKey: ['employees'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
  },
  
  employee: (id) => {
    queryClient.invalidateQueries({ queryKey: ['employees', 'detail', id] });
    queryClient.invalidateQueries({ queryKey: ['employees', 'list'] });
    queryClient.invalidateQueries({ queryKey: ['employees', 'all'] });
  },
  
  // Onboarding workflow - Critical for HR
  onboarding: () => {
    queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    queryClient.invalidateQueries({ queryKey: ['go-live'] });
    queryClient.invalidateQueries({ queryKey: ['employees'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
  },
  
  onboardingSubmission: (id) => {
    queryClient.invalidateQueries({ queryKey: ['onboarding', 'submission', id] });
    queryClient.invalidateQueries({ queryKey: ['onboarding', 'submissions'] });
  },
  
  goLive: () => {
    queryClient.invalidateQueries({ queryKey: ['go-live'] });
    queryClient.invalidateQueries({ queryKey: ['employees'] });
  },
  
  // Attendance & Leaves
  attendance: () => {
    queryClient.invalidateQueries({ queryKey: ['attendance'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
  },
  
  leaves: () => {
    queryClient.invalidateQueries({ queryKey: ['leaves'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['approvals'] });
  },
  
  // Payroll
  payroll: () => {
    queryClient.invalidateQueries({ queryKey: ['payroll'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
  },
  
  // Sales workflow
  leads: () => {
    queryClient.invalidateQueries({ queryKey: ['leads'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'funnel'] });
    queryClient.invalidateQueries({ queryKey: ['sales', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  },
  
  lead: (id) => {
    queryClient.invalidateQueries({ queryKey: ['leads', 'detail', id] });
    queryClient.invalidateQueries({ queryKey: ['leads', 'list'] });
  },
  
  // Projects
  projects: () => {
    queryClient.invalidateQueries({ queryKey: ['projects'] });
    queryClient.invalidateQueries({ queryKey: ['consulting', 'stats'] });
  },
  
  project: (id) => {
    queryClient.invalidateQueries({ queryKey: ['projects', 'detail', id] });
    queryClient.invalidateQueries({ queryKey: ['projects', 'list'] });
  },
  
  // Expenses
  expenses: () => {
    queryClient.invalidateQueries({ queryKey: ['expenses'] });
    queryClient.invalidateQueries({ queryKey: ['approvals'] });
  },
  
  // Agreements & Kickoffs
  agreements: () => {
    queryClient.invalidateQueries({ queryKey: ['agreements'] });
  },
  
  kickoffs: () => {
    queryClient.invalidateQueries({ queryKey: ['kickoff-requests'] });
  },
  
  // Notifications
  notifications: () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  },
  
  // Documents
  documents: () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
  },
  
  // Approvals - all types
  approvals: () => {
    queryClient.invalidateQueries({ queryKey: ['approvals'] });
    queryClient.invalidateQueries({ queryKey: ['hr', 'stats'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  },
  
  // Full cache clear (use sparingly)
  all: () => {
    queryClient.invalidateQueries();
  },
};

// ===========================================
// PREFETCH HELPERS
// For background data loading
// ===========================================

export const prefetchQueries = {
  // Prefetch employee data when HR page is about to open
  hrModule: async () => {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: queryKeys.employeesAll,
        staleTime: 2 * 60 * 1000,
      }),
      queryClient.prefetchQuery({
        queryKey: queryKeys.hrStats,
        staleTime: 2 * 60 * 1000,
      }),
    ]);
  },
  
  // Prefetch onboarding data
  onboarding: async () => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.onboardingSubmissions({}),
      staleTime: 2 * 60 * 1000,
    });
  },
  
  // Prefetch dashboard stats
  dashboard: async () => {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: queryKeys.dashboardStats,
        staleTime: 2 * 60 * 1000,
      }),
      queryClient.prefetchQuery({
        queryKey: queryKeys.pendingApprovals,
        staleTime: 1 * 60 * 1000,
      }),
    ]);
  },
};

// ===========================================
// OPTIMISTIC UPDATE HELPERS
// For instant UI feedback
// ===========================================

export const optimisticUpdate = {
  // Update employee in cache before API call completes
  updateEmployee: (employeeId, updates) => {
    queryClient.setQueryData(queryKeys.employee(employeeId), (old) => {
      if (!old) return old;
      return { ...old, ...updates };
    });
  },
  
  // Update lead status optimistically
  updateLeadStatus: (leadId, newStatus) => {
    queryClient.setQueryData(queryKeys.lead(leadId), (old) => {
      if (!old) return old;
      return { ...old, status: newStatus };
    });
  },
  
  // Add new item to list optimistically
  addToList: (queryKey, newItem) => {
    queryClient.setQueryData(queryKey, (old) => {
      if (!old) return [newItem];
      if (Array.isArray(old)) return [newItem, ...old];
      if (old.items) return { ...old, items: [newItem, ...old.items] };
      return old;
    });
  },
  
  // Remove item from list optimistically
  removeFromList: (queryKey, itemId) => {
    queryClient.setQueryData(queryKey, (old) => {
      if (!old) return old;
      if (Array.isArray(old)) return old.filter(item => item.id !== itemId);
      if (old.items) return { ...old, items: old.items.filter(item => item.id !== itemId) };
      return old;
    });
  },
};

export { QueryClientProvider } from '@tanstack/react-query';
