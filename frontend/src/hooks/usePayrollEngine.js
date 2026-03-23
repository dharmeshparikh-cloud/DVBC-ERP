import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API } from '../App';

// ==================== PAYROLL ENGINE HOOKS ====================

// Simulate payroll for single employee (HR Test Mode)
export function useSimulatePayroll() {
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/simulate`, data);
      return res.data;
    }
  });
}

// Bulk simulation
export function useBulkSimulate() {
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/simulate-bulk`, data);
      return res.data;
    }
  });
}

// Run payroll (creates draft)
export function useRunPayroll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/run`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['payroll-register']);
    }
  });
}

// Get payroll register
export function usePayrollRegister(month) {
  return useQuery({
    queryKey: ['payroll-register', month],
    queryFn: async () => {
      const params = month ? `?month=${month}` : '';
      const res = await axios.get(`${API}/payroll/engine/register${params}`);
      return res.data;
    },
    staleTime: 60 * 1000
  });
}

// Get register details with all calculations
export function usePayrollRegisterDetails(month) {
  return useQuery({
    queryKey: ['payroll-register-details', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/engine/register/${month}/details`);
      return res.data;
    },
    enabled: !!month,
    staleTime: 60 * 1000
  });
}

// Get calculation breakdown
export function useCalculationBreakdown(employeeId, month) {
  return useQuery({
    queryKey: ['payroll-breakdown', employeeId, month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/engine/breakdown/${employeeId}/${month}`);
      return res.data;
    },
    enabled: !!employeeId && !!month,
    staleTime: 60 * 1000
  });
}

// Get comparison (before/after)
export function usePayrollComparison(employeeId, month) {
  return useQuery({
    queryKey: ['payroll-comparison', employeeId, month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/engine/comparison/${employeeId}/${month}`);
      return res.data;
    },
    enabled: !!employeeId && !!month,
    staleTime: 60 * 1000
  });
}

// Submit for approval
export function useSubmitForApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/submit-for-approval`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['payroll-register']);
    }
  });
}

// Approve payroll (Admin)
export function useApprovePayroll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/approve`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['payroll-register']);
    }
  });
}

// Reject payroll (Admin)
export function useRejectPayroll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/payroll/engine/reject`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['payroll-register']);
    }
  });
}

// Export payroll data
export function useExportPayroll(month) {
  return useQuery({
    queryKey: ['payroll-export', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/payroll/engine/export/${month}`);
      return res.data;
    },
    enabled: false  // Manual trigger only
  });
}
