/**
 * useMobileApp.js - React Query hooks for Employee Mobile App
 * 
 * Handles all mobile-specific API calls including attendance,
 * leave requests, expenses, and travel reimbursements.
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
  return [];
};

// ============================================
// QUERY HOOKS - GET Requests
// ============================================

/**
 * Fetch my attendance for current month
 */
export const useMyAttendance = (month, options = {}) => {
  return useQuery({
    queryKey: ['my', 'attendance', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/attendance?month=${month}`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 120000, // 2 minutes
    ...options
  });
};

/**
 * Fetch my leave balance
 */
export const useMyLeaveBalance = (options = {}) => {
  return useQuery({
    queryKey: ['my', 'leave-balance'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/leave-balance`, { headers: getHeaders() });
      return res.data;
    },
    staleTime: 120000,
    ...options
  });
};

/**
 * Fetch my expenses
 */
export const useMyExpenses = (options = {}) => {
  return useQuery({
    queryKey: ['my', 'expenses'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/expenses`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 120000,
    ...options
  });
};

/**
 * Fetch clients list
 */
export const useClients = (options = {}) => {
  return useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/clients`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 300000, // 5 minutes (master data)
    ...options
  });
};

/**
 * Fetch projects list
 */
export const useProjectsList = (options = {}) => {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/projects`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 300000,
    ...options
  });
};

/**
 * Fetch my assigned clients
 */
export const useMyAssignedClients = (options = {}) => {
  return useQuery({
    queryKey: ['my', 'assigned-clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/assigned-clients`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 300000,
    ...options
  });
};

/**
 * Fetch my travel reimbursements
 */
export const useMyTravelReimbursements = (month, options = {}) => {
  return useQuery({
    queryKey: ['my', 'travel-reimbursements', month],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/my/travel-reimbursements?month=${month}`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 120000,
    ...options
  });
};

/**
 * Search locations for travel
 */
export const useLocationSearch = (query, options = {}) => {
  return useQuery({
    queryKey: ['travel', 'location-search', query],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/travel/location-search?query=${encodeURIComponent(query)}`, { headers: getHeaders() });
      return res.data?.results || res.data || [];
    },
    enabled: !!query && query.length >= 3,
    staleTime: 60000,
    ...options
  });
};

/**
 * Combined dashboard data fetch (for initial load)
 */
export const useMobileDashboardData = (month, options = {}) => {
  return useQuery({
    queryKey: ['mobile', 'dashboard', month],
    queryFn: async () => {
      const [attendance, leaveBalance, expenses, clients, projects] = await Promise.all([
        axios.get(`${API}/api/my/attendance?month=${month}`, { headers: getHeaders() }).catch(() => ({ data: null })),
        axios.get(`${API}/api/my/leave-balance`, { headers: getHeaders() }).catch(() => ({ data: null })),
        axios.get(`${API}/api/my/expenses`, { headers: getHeaders() }).catch(() => ({ data: null })),
        axios.get(`${API}/api/clients`, { headers: getHeaders() }).catch(() => ({ data: [] })),
        axios.get(`${API}/api/projects`, { headers: getHeaders() }).catch(() => ({ data: [] }))
      ]);
      
      return {
        attendance: attendance.data,
        leaveBalance: leaveBalance.data,
        expenses: expenses.data,
        clients: extractArray(clients.data),
        projects: extractArray(projects.data)
      };
    },
    staleTime: 120000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS - POST Requests
// ============================================

/**
 * Check-in mutation
 */
export const useCheckIn = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload) => {
      // payload: { geo_location?, client_id?, project_id?, work_type, notes? }
      const res = await axios.post(`${API}/api/my/check-in`, payload, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] });
      queryClient.invalidateQueries({ queryKey: ['mobile', 'dashboard'] });
    }
  });
};

/**
 * Check-out mutation
 */
export const useCheckOut = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload) => {
      // payload: { geo_location? }
      const res = await axios.post(`${API}/api/my/check-out`, payload, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'attendance'] });
      queryClient.invalidateQueries({ queryKey: ['mobile', 'dashboard'] });
    }
  });
};

/**
 * Submit expense mutation
 */
export const useSubmitExpense = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (expenseData) => {
      // expenseData: { category, amount, description, expense_date, client_id?, project_id? }
      const res = await axios.post(`${API}/api/expenses`, expenseData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
      queryClient.invalidateQueries({ queryKey: ['mobile', 'dashboard'] });
    }
  });
};

/**
 * Upload expense receipt mutation
 */
export const useUploadReceipt = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ expenseId, fileData, fileName, contentType }) => {
      const res = await axios.post(
        `${API}/api/expenses/${expenseId}/upload-receipt`,
        { file_data: fileData, file_name: fileName, content_type: contentType },
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    }
  });
};

/**
 * Submit leave request mutation
 */
export const useSubmitLeaveRequest = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (leaveData) => {
      // leaveData: { leave_type, start_date, end_date, reason, is_half_day? }
      const res = await axios.post(`${API}/api/leave-requests`, leaveData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'leave-balance'] });
      queryClient.invalidateQueries({ queryKey: ['mobile', 'dashboard'] });
    }
  });
};

/**
 * Submit travel reimbursement mutation
 */
export const useSubmitTravelReimbursement = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (travelData) => {
      // travelData: { travel_date, from_location, to_location, distance_km, mode, amount, purpose, client_id?, project_id? }
      const res = await axios.post(`${API}/api/travel/reimbursement`, travelData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my', 'travel-reimbursements'] });
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    }
  });
};

export default {
  useMyAttendance,
  useMyLeaveBalance,
  useMyExpenses,
  useClients,
  useProjectsList,
  useMyAssignedClients,
  useMyTravelReimbursements,
  useLocationSearch,
  useMobileDashboardData,
  useCheckIn,
  useCheckOut,
  useSubmitExpense,
  useUploadReceipt,
  useSubmitLeaveRequest,
  useSubmitTravelReimbursement
};
