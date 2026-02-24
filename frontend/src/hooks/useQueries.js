/**
 * React Query Custom Hooks
 * Centralized data fetching with caching, background refetch, and error handling
 * 
 * Performance Optimization: February 2026
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '../App';
import { queryKeys, invalidateCache } from '../lib/queryClient';

// ============== DASHBOARD QUERIES ==============

/**
 * Fetch main dashboard stats
 */
export function useDashboardStats(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/stats/dashboard`);
      return data;
    },
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes for stats
  });
}

/**
 * Fetch HR dashboard stats
 */
export function useHRStats(enabled = true) {
  return useQuery({
    queryKey: queryKeys.hrStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/hr/stats`);
      return data;
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch Sales dashboard stats
 */
export function useSalesStats(enabled = true) {
  return useQuery({
    queryKey: queryKeys.salesStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/sales/stats`);
      return data;
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch Consulting dashboard stats
 */
export function useConsultingStats(enabled = true) {
  return useQuery({
    queryKey: queryKeys.consultingStats,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/consulting/stats`);
      return data;
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

// ============== EMPLOYEE QUERIES ==============

/**
 * Fetch employees list with filters
 */
export function useEmployees(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.employees(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.department) params.append('department', filters.department);
      if (filters.status) params.append('status', filters.status);
      if (filters.search) params.append('search', filters.search);
      if (filters.page) params.append('page', filters.page);
      if (filters.limit) params.append('limit', filters.limit);
      
      const { data } = await axios.get(`${API}/employees?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch single employee
 */
export function useEmployee(id, enabled = true) {
  return useQuery({
    queryKey: queryKeys.employee(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/employees/${id}`);
      return data;
    },
    enabled: enabled && !!id,
  });
}

// ============== LEADS QUERIES ==============

/**
 * Fetch leads list with filters
 */
export function useLeads(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.leads(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.priority) params.append('priority', filters.priority);
      if (filters.assigned_to) params.append('assigned_to', filters.assigned_to);
      if (filters.search) params.append('search', filters.search);
      
      const { data } = await axios.get(`${API}/leads?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch single lead
 */
export function useLead(id, enabled = true) {
  return useQuery({
    queryKey: queryKeys.lead(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/leads/${id}`);
      return data;
    },
    enabled: enabled && !!id,
  });
}

/**
 * Fetch high priority leads (top 3)
 */
export function useHighPriorityLeads(enabled = true) {
  return useQuery({
    queryKey: ['leads', 'high-priority'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/leads`);
      return data
        .sort((a, b) => (b.lead_score || 0) - (a.lead_score || 0))
        .slice(0, 3);
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

// ============== PROJECTS QUERIES ==============

/**
 * Fetch projects list
 */
export function useProjects(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.projects(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.client_id) params.append('client_id', filters.client_id);
      
      const { data } = await axios.get(`${API}/projects?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch single project
 */
export function useProject(id, enabled = true) {
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/projects/${id}`);
      return data;
    },
    enabled: enabled && !!id,
  });
}

// ============== APPROVALS QUERIES ==============

/**
 * Fetch pending approvals count
 */
export function usePendingApprovalsCount(enabled = true) {
  return useQuery({
    queryKey: ['approvals', 'pending', 'count'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/approvals?status=pending`);
      return data.length;
    },
    enabled,
    staleTime: 1 * 60 * 1000, // 1 minute for approvals
  });
}

/**
 * Fetch approvals list
 */
export function useApprovals(status = 'pending', enabled = true) {
  return useQuery({
    queryKey: ['approvals', status],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/approvals?status=${status}`);
      return data;
    },
    enabled,
  });
}

// ============== ATTENDANCE QUERIES ==============

/**
 * Fetch current user's attendance status
 */
export function useMyAttendanceStatus(enabled = true) {
  return useQuery({
    queryKey: ['my', 'attendance-status'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/my/check-status`);
      return data;
    },
    enabled,
    staleTime: 30 * 1000, // 30 seconds for attendance
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Fetch attendance records
 */
export function useAttendanceRecords(filters = {}, enabled = true) {
  return useQuery({
    queryKey: ['attendance', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      if (filters.date) params.append('date', filters.date);
      if (filters.month) params.append('month', filters.month);
      
      const { data } = await axios.get(`${API}/attendance?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

// ============== SECURITY AUDIT QUERIES ==============

/**
 * Fetch security audit logs
 */
export function useSecurityAuditLogs(limit = 8, enabled = true) {
  return useQuery({
    queryKey: ['security-audit-logs', limit],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/security-audit-logs?limit=${limit}`);
      const logs = data.logs || [];
      const failedCount = logs.filter(l => l.event_type?.includes('failed') || l.event_type?.includes('rejected')).length;
      const successCount = logs.filter(l => l.event_type?.includes('success')).length;
      return { logs, total: data.total, failedCount, successCount };
    },
    enabled,
    staleTime: 2 * 60 * 1000,
  });
}

// ============== EXPENSES QUERIES ==============

/**
 * Fetch expenses list
 */
export function useExpenses(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.expenses(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      
      const { data } = await axios.get(`${API}/expenses?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

// ============== AGREEMENTS QUERIES ==============

/**
 * Fetch agreements list
 */
export function useAgreements(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.agreements(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.client_id) params.append('client_id', filters.client_id);
      
      const { data } = await axios.get(`${API}/agreements?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch single agreement
 */
export function useAgreement(id, enabled = true) {
  return useQuery({
    queryKey: queryKeys.agreement(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/agreements/${id}`);
      return data;
    },
    enabled: enabled && !!id,
  });
}

// ============== KICKOFF QUERIES ==============

/**
 * Fetch kickoff requests
 */
export function useKickoffRequests(filters = {}, enabled = true) {
  return useQuery({
    queryKey: queryKeys.kickoffRequests(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      
      const { data } = await axios.get(`${API}/kickoff?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

// ============== ONBOARDING QUERIES ==============

/**
 * Fetch onboarding submissions
 */
export function useOnboardingSubmissions(filters = {}, enabled = true) {
  return useQuery({
    queryKey: ['onboarding', 'submissions', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      
      const { data } = await axios.get(`${API}/onboarding/submissions?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch single onboarding submission
 */
export function useOnboardingSubmission(id, enabled = true) {
  return useQuery({
    queryKey: ['onboarding', 'submission', id],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/onboarding/submissions/${id}`);
      return data;
    },
    enabled: enabled && !!id,
  });
}

// ============== GO-LIVE QUERIES ==============

/**
 * Fetch go-live requests
 */
export function useGoLiveRequests(filters = {}, enabled = true) {
  return useQuery({
    queryKey: ['go-live', 'requests', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      
      const { data } = await axios.get(`${API}/go-live/pending?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

// ============== LEAVES QUERIES ==============

/**
 * Fetch leaves list
 */
export function useLeaves(filters = {}, enabled = true) {
  return useQuery({
    queryKey: ['leaves', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.employee_id) params.append('employee_id', filters.employee_id);
      
      const { data } = await axios.get(`${API}/leaves?${params.toString()}`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch my leaves
 */
export function useMyLeaves(enabled = true) {
  return useQuery({
    queryKey: ['my', 'leaves'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/my/leaves`);
      return data;
    },
    enabled,
  });
}

/**
 * Fetch leave balance
 */
export function useLeaveBalance(employeeId, enabled = true) {
  return useQuery({
    queryKey: ['leave-balance', employeeId],
    queryFn: async () => {
      const url = employeeId ? `${API}/leaves/balance/${employeeId}` : `${API}/my/leave-balance`;
      const { data } = await axios.get(url);
      return data;
    },
    enabled,
  });
}

// ============== MASTERS QUERIES ==============

/**
 * Fetch departments
 */
export function useDepartments(enabled = true) {
  return useQuery({
    queryKey: ['masters', 'departments'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/masters/departments`);
      return data;
    },
    enabled,
    staleTime: 30 * 60 * 1000, // 30 minutes for masters
  });
}

/**
 * Fetch designations
 */
export function useDesignations(enabled = true) {
  return useQuery({
    queryKey: ['masters', 'designations'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/masters/designations`);
      return data;
    },
    enabled,
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch locations
 */
export function useLocations(enabled = true) {
  return useQuery({
    queryKey: ['masters', 'locations'],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/masters/locations`);
      return data;
    },
    enabled,
    staleTime: 30 * 60 * 1000,
  });
}

// ============== NOTIFICATIONS QUERIES ==============

/**
 * Fetch notifications
 */
export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: async () => {
      const { data } = await axios.get(`${API}/notifications`);
      return data;
    },
    enabled,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

// ============== MUTATION HOOKS ==============

/**
 * Generic mutation with cache invalidation
 */
export function useApiMutation(mutationFn, options = {}) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn,
    onSuccess: (data, variables, context) => {
      if (options.successMessage) {
        toast.success(options.successMessage);
      }
      if (options.invalidateKeys) {
        options.invalidateKeys.forEach(key => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }
      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
    onError: (error, variables, context) => {
      const message = error.response?.data?.detail || error.message || 'An error occurred';
      toast.error(options.errorMessage || message);
      if (options.onError) {
        options.onError(error, variables, context);
      }
    },
  });
}

/**
 * Create employee mutation
 */
export function useCreateEmployee() {
  return useApiMutation(
    async (employeeData) => {
      const { data } = await axios.post(`${API}/employees`, employeeData);
      return data;
    },
    {
      successMessage: 'Employee created successfully',
      invalidateKeys: [['employees']],
    }
  );
}

/**
 * Update employee mutation
 */
export function useUpdateEmployee() {
  return useApiMutation(
    async ({ id, ...employeeData }) => {
      const { data } = await axios.put(`${API}/employees/${id}`, employeeData);
      return data;
    },
    {
      successMessage: 'Employee updated successfully',
      invalidateKeys: [['employees']],
    }
  );
}

/**
 * Check-in mutation
 */
export function useCheckIn() {
  return useApiMutation(
    async (checkInData) => {
      const { data } = await axios.post(`${API}/attendance/check-in`, checkInData);
      return data;
    },
    {
      successMessage: 'Checked in successfully',
      invalidateKeys: [['my', 'attendance-status'], ['attendance']],
    }
  );
}

/**
 * Check-out mutation
 */
export function useCheckOut() {
  return useApiMutation(
    async (checkOutData) => {
      const { data } = await axios.post(`${API}/attendance/check-out`, checkOutData);
      return data;
    },
    {
      successMessage: 'Checked out successfully',
      invalidateKeys: [['my', 'attendance-status'], ['attendance']],
    }
  );
}

/**
 * Create lead mutation
 */
export function useCreateLead() {
  return useApiMutation(
    async (leadData) => {
      const { data } = await axios.post(`${API}/leads`, leadData);
      return data;
    },
    {
      successMessage: 'Lead created successfully',
      invalidateKeys: [['leads'], ['dashboard', 'stats']],
    }
  );
}

/**
 * Update lead mutation
 */
export function useUpdateLead() {
  return useApiMutation(
    async ({ id, ...leadData }) => {
      const { data } = await axios.put(`${API}/leads/${id}`, leadData);
      return data;
    },
    {
      successMessage: 'Lead updated successfully',
      invalidateKeys: [['leads']],
    }
  );
}

/**
 * Apply leave mutation
 */
export function useApplyLeave() {
  return useApiMutation(
    async (leaveData) => {
      const { data } = await axios.post(`${API}/leaves`, leaveData);
      return data;
    },
    {
      successMessage: 'Leave application submitted',
      invalidateKeys: [['leaves'], ['my', 'leaves']],
    }
  );
}

/**
 * Approve leave mutation
 */
export function useApproveLeave() {
  return useApiMutation(
    async ({ id, ...approvalData }) => {
      const { data } = await axios.patch(`${API}/leaves/${id}/approve`, approvalData);
      return data;
    },
    {
      successMessage: 'Leave approved',
      invalidateKeys: [['leaves'], ['approvals']],
    }
  );
}

// Export cache invalidation helpers
export { invalidateCache };
