/**
 * useApprovals.js - React Query hooks for Approval Center
 * 
 * Handles all approval-related API calls with proper caching and invalidation.
 * Role-based queries are conditionally enabled based on user permissions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

// Helper to get auth headers
const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

// Helper to safely extract array from API response
const extractArray = (data) => {
  if (Array.isArray(data)) return data;
  if (data?.items && Array.isArray(data.items)) return data.items;
  if (data?.requests && Array.isArray(data.requests)) return data.requests;
  return [];
};

// ============================================
// QUERY HOOKS - GET Requests
// ============================================

/**
 * Fetch pending approvals for current user
 */
export const usePendingApprovals = (options = {}) => {
  return useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/approvals/pending`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 60000, // 1 minute
    ...options
  });
};

/**
 * Fetch user's own requests
 */
export const useMyRequests = (options = {}) => {
  return useQuery({
    queryKey: ['approvals', 'my-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/approvals/my-requests`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch all approvals (for managers)
 */
export const useAllApprovals = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['approvals', 'all'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/approvals/all`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch CTC pending approvals (Admin only)
 */
export const useCtcApprovals = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['ctc', 'pending-approvals'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/ctc/pending-approvals`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch Go-Live pending requests (Admin only)
 */
export const useGoLivePending = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['go-live', 'pending'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/go-live/pending`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch Go-Live checklist for an employee
 */
export const useGoLiveChecklist = (employeeId, options = {}) => {
  return useQuery({
    queryKey: ['go-live', 'checklist', employeeId],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/go-live/checklist/${employeeId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!employeeId,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch permission change requests (Admin only)
 */
export const usePermissionRequests = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['permissions', 'pending-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/permission-change-requests`, { headers: getHeaders() });
      return extractArray(res.data).filter(r => r.status === 'pending');
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch employee modification requests (Admin only)
 */
export const useModificationRequests = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['employees', 'modification-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees/modification-requests/pending`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch bank change requests (HR only)
 */
export const useBankChangeRequests = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['hr', 'bank-change-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/hr/bank-change-requests`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch employee change requests (HR only)
 */
export const useEmployeeChangeRequests = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['hr', 'employee-change-requests'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/hr/employee-change-requests`, { headers: getHeaders() });
      return extractArray(res.data).filter(r => r.status === 'pending');
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch agreement approvals (Manager/Admin)
 */
export const useAgreementApprovals = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['agreements', 'pending-approval'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/agreements/pending-approval`, { headers: getHeaders() });
      const data = extractArray(res.data);
      return (data || []).map(item => item.agreement || item);
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch kickoff approvals (SC/PC/Admin)
 */
export const useKickoffApprovals = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['kickoff', 'pending-approvals'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sales-funnel/pending-kickoff-approvals`, { headers: getHeaders() });
      const data = res.data?.requests || extractArray(res.data);
      return Array.isArray(data) ? data : [];
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch expense approvals (Manager/HR)
 */
export const useExpenseApprovals = (enabled = false, options = {}) => {
  return useQuery({
    queryKey: ['expenses', 'pending-approvals'],
    queryFn: async () => {
      try {
        const res = await axios.get(`${API}/api/expenses/pending-approvals`, { headers: getHeaders() });
        return extractArray(res.data).filter(e => 
          e.status === 'pending' || e.status === 'manager_approved'
        );
      } catch {
        const res = await axios.get(`${API}/api/expenses`, { headers: getHeaders() });
        return extractArray(res.data).filter(e => 
          e.status === 'pending' || e.status === 'manager_approved'
        );
      }
    },
    enabled,
    staleTime: 60000,
    ...options
  });
};

/**
 * Fetch expense receipts
 */
export const useExpenseReceipts = (expenseId, options = {}) => {
  return useQuery({
    queryKey: ['expenses', expenseId, 'receipts'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/expenses/${expenseId}/receipts`, { headers: getHeaders() });
      return res.data?.receipts || res.data || [];
    },
    enabled: !!expenseId,
    staleTime: 60000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS - POST/PATCH/DELETE Requests
// ============================================

/**
 * Generic approval action mutation
 */
export const useApprovalAction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ approvalId, action, comments }) => {
      const res = await axios.post(
        `${API}/api/approvals/${approvalId}/action`,
        { action, comments },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Agreement approval mutation
 */
export const useApproveAgreement = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (agreementId) => {
      const res = await axios.patch(
        `${API}/api/agreements/${agreementId}/approve`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agreements'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Agreement rejection mutation
 */
export const useRejectAgreement = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ agreementId, reason }) => {
      const res = await axios.patch(
        `${API}/api/agreements/${agreementId}/reject`,
        { rejection_reason: reason },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agreements'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Kickoff approval mutation
 */
export const useApproveKickoff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(
        `${API}/api/sales-funnel/approve-kickoff/${requestId}`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kickoff'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Kickoff rejection mutation
 */
export const useRejectKickoff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(
        `${API}/api/sales-funnel/reject-kickoff/${requestId}?reason=${encodeURIComponent(reason)}`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kickoff'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Expense approval mutation
 */
export const useApproveExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, remarks }) => {
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/approve`,
        { remarks },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Expense rejection mutation
 */
export const useRejectExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, reason }) => {
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/reject`,
        { reason },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Expense send-back mutation
 */
export const useSendBackExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, comments }) => {
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/send-back`,
        { comments },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
    }
  });
};

/**
 * Expense partial approval mutation
 */
export const usePartialApproveExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, approvedAmount, modificationReason }) => {
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/approve-with-modification`,
        { approved_amount: parseFloat(approvedAmount), modification_reason: modificationReason },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
    }
  });
};

/**
 * Upload expense receipt mutation
 */
export const useUploadExpenseReceipt = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, file }) => {
      const reader = new FileReader();
      const base64 = await new Promise((resolve, reject) => {
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/upload-receipt`,
        { file_data: base64, file_name: file.name, content_type: file.type },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { expenseId }) => {
      queryClient.invalidateQueries({ queryKey: ['expenses', expenseId, 'receipts'] });
    }
  });
};

/**
 * Delete expense receipt mutation
 */
export const useDeleteExpenseReceipt = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, receiptId }) => {
      const res = await axios.delete(
        `${API}/api/expenses/${expenseId}/receipts/${receiptId}`,
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { expenseId }) => {
      queryClient.invalidateQueries({ queryKey: ['expenses', expenseId, 'receipts'] });
    }
  });
};

/**
 * Permission request approval mutation
 */
export const useApprovePermissionRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(
        `${API}/api/permission-change-requests/${requestId}/approve`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Permission request rejection mutation
 */
export const useRejectPermissionRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(
        `${API}/api/permission-change-requests/${requestId}/reject`,
        { reason: reason || 'Rejected by Admin' },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * CTC approval mutation
 */
export const useApproveCTC = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ ctcId, comments }) => {
      const res = await axios.post(
        `${API}/api/ctc/${ctcId}/approve`,
        { comments },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ctc'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * CTC rejection mutation
 */
export const useRejectCTC = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ ctcId, reason }) => {
      const res = await axios.post(
        `${API}/api/ctc/${ctcId}/reject`,
        { reason },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ctc'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Bank change request action mutation
 */
export const useBankChangeAction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, action, reason }) => {
      const endpoint = action === 'approve' 
        ? `${API}/api/hr/bank-change-request/${requestId}/approve`
        : `${API}/api/hr/bank-change-request/${requestId}/reject`;
      const res = await axios.post(endpoint, { reason }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr', 'bank-change-requests'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Profile change request approval mutation
 */
export const useApproveProfileChange = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(
        `${API}/api/hr/employee-change-request/${requestId}/approve`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr', 'employee-change-requests'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Profile change request rejection mutation
 */
export const useRejectProfileChange = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(
        `${API}/api/hr/employee-change-request/${requestId}/reject`,
        { reason: reason || 'Rejected by HR' },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hr', 'employee-change-requests'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Go-Live approval mutation
 */
export const useApproveGoLive = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(
        `${API}/api/go-live/${requestId}/approve`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['go-live'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Go-Live rejection mutation
 */
export const useRejectGoLive = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(
        `${API}/api/go-live/${requestId}/reject`,
        { reason: reason || 'Rejected by Admin' },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['go-live'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Modification request approval mutation
 */
export const useApproveModificationRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (requestId) => {
      const res = await axios.post(
        `${API}/api/employees/modification-requests/${requestId}/approve`,
        {},
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', 'modification-requests'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Modification request rejection mutation
 */
export const useRejectModificationRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ requestId, reason }) => {
      const res = await axios.post(
        `${API}/api/employees/modification-requests/${requestId}/reject`,
        { reason },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', 'modification-requests'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

/**
 * Bulk approval action mutation
 */
export const useBulkApprovalAction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ ids, action, comments }) => {
      const results = await Promise.all(
        (ids || []).map(id => 
          axios.post(
            `${API}/api/approvals/${id}/action`,
            { action, comments },
            { headers: getHeaders() }
          ).catch(err => ({ error: true, id, message: err.message }))
        )
      );
      return results;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    }
  });
};

export default {
  usePendingApprovals,
  useMyRequests,
  useAllApprovals,
  useCtcApprovals,
  useGoLivePending,
  useGoLiveChecklist,
  usePermissionRequests,
  useModificationRequests,
  useBankChangeRequests,
  useEmployeeChangeRequests,
  useAgreementApprovals,
  useKickoffApprovals,
  useExpenseApprovals,
  useExpenseReceipts,
  useApprovalAction,
  useApproveAgreement,
  useRejectAgreement,
  useApproveKickoff,
  useRejectKickoff,
  useApproveExpense,
  useRejectExpense,
  useSendBackExpense,
  usePartialApproveExpense,
  useUploadExpenseReceipt,
  useDeleteExpenseReceipt,
  useApprovePermissionRequest,
  useRejectPermissionRequest,
  useApproveCTC,
  useRejectCTC,
  useBankChangeAction,
  useApproveProfileChange,
  useRejectProfileChange,
  useApproveGoLive,
  useRejectGoLive,
  useApproveModificationRequest,
  useRejectModificationRequest,
  useBulkApprovalAction
};
