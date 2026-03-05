/**
 * useUserManagement.js - React Query hooks for User & Role management
 * 
 * Handles users, roles, permissions, and RBAC operations.
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
  return [];
};

// ============================================
// QUERY HOOKS
// ============================================

/**
 * Fetch all users with their roles
 */
export const useUsersWithRoles = (options = {}) => {
  return useQuery({
    queryKey: ['users', 'with-roles'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/users-with-roles`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    ...options
  });
};

/**
 * Fetch all roles
 */
export const useRoles = (options = {}) => {
  return useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/roles`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options
  });
};

/**
 * Fetch role details with permissions
 */
export const useRoleDetails = (roleId, options = {}) => {
  return useQuery({
    queryKey: ['roles', roleId],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/roles/${roleId}`, { headers: getHeaders() });
      return res.data;
    },
    enabled: !!roleId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Fetch permission modules
 * Returns full response object with { modules: [], actions: {} } structure
 */
export const usePermissionModules = (options = {}) => {
  return useQuery({
    queryKey: ['permissions', 'modules'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/permission-modules`, { headers: getHeaders() });
      // Return full response object for backwards compatibility
      return res.data || { modules: [], actions: {} };
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - rarely changes
    ...options
  });
};

/**
 * Fetch all users (simple list)
 */
export const useUsers = (options = {}) => {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/users`, { headers: getHeaders() });
      return extractArray(res.data);
    },
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

// ============================================
// MUTATION HOOKS
// ============================================

/**
 * Register new user
 */
export const useRegisterUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (userData) => {
      const res = await axios.post(`${API}/api/auth/register`, userData, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
};

/**
 * Update user role
 */
export const useUpdateUserRole = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ userId, role }) => {
      const res = await axios.patch(`${API}/api/users/${userId}/role?role=${role}`, {}, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
};

/**
 * Create new role
 */
export const useCreateRole = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ name, description, permissions }) => {
      const res = await axios.post(`${API}/api/roles`, { name, description, permissions }, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    }
  });
};

/**
 * Update role permissions
 */
export const useUpdateRole = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ roleId, name, description, permissions }) => {
      const res = await axios.patch(`${API}/api/roles/${roleId}`, 
        { name, description, permissions }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: (_, { roleId }) => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      queryClient.invalidateQueries({ queryKey: ['roles', roleId] });
    }
  });
};

/**
 * Delete role
 */
export const useDeleteRole = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (roleId) => {
      const res = await axios.delete(`${API}/api/roles/${roleId}`, { headers: getHeaders() });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
    }
  });
};

/**
 * Toggle user active status
 */
export const useToggleUserStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ userId, isActive }) => {
      const res = await axios.patch(`${API}/api/users/${userId}/status`, 
        { is_active: isActive }, 
        { headers: getHeaders() }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    }
  });
};

export default {
  useUsersWithRoles,
  useRoles,
  useRoleDetails,
  usePermissionModules,
  useUsers,
  useRegisterUser,
  useUpdateUserRole,
  useCreateRole,
  useUpdateRole,
  useDeleteRole,
  useToggleUserStatus
};
