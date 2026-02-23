import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';

const PermissionContext = createContext();

export const PermissionProvider = ({ children }) => {
  const { user } = useContext(AuthContext);
  const [permissions, setPermissions] = useState(null);
  const [rbacData, setRbacData] = useState(null);
  const [level, setLevel] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchPermissions = useCallback(async () => {
    if (!user) {
      setPermissions(null);
      setRbacData(null);
      setLevel(null);
      setLoading(false);
      return;
    }

    try {
      const token = localStorage.getItem('token');
      
      // Fetch from new RBAC API (Phase 5 - Database-driven permissions)
      const rbacResponse = await axios.get(`${API}/rbac/my-permissions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const rbac = rbacResponse.data;
      setRbacData(rbac);
      setLevel(rbac.level);
      
      // Convert RBAC permissions to legacy format for backward compatibility
      const perms = rbac.permissions || [];
      const hasPermission = (perm) => {
        if (perms.includes('*')) return true;
        if (perms.includes(perm)) return true;
        // Check wildcard patterns (e.g., "hr.*" matches "hr.view")
        return perms.some(p => p.endsWith('.*') && perm.startsWith(p.slice(0, -2)));
      };
      
      setPermissions({
        can_view_own_data: true,
        can_edit_own_profile: true,
        can_submit_requests: true,
        can_view_team_data: rbac.level >= 70 || hasPermission('team.view'),
        can_approve_requests: rbac.can_approve || hasPermission('approvals.*'),
        can_view_reports: rbac.level >= 60 || hasPermission('reports.*'),
        can_manage_team: rbac.can_manage_users || hasPermission('team.manage'),
        can_manage_users: rbac.can_manage_users,
        can_access_financials: hasPermission('finance.*') || hasPermission('payments.*'),
        // New RBAC-specific permissions
        raw_permissions: perms,
        stage_access: rbac.stage_access,
        department: rbac.department,
        role_name: rbac.role_name
      });
    } catch (error) {
      console.error('Failed to fetch RBAC permissions:', error);
      // Try legacy endpoint as fallback
      try {
        const token = localStorage.getItem('token');
        const legacyResponse = await axios.get(`${API}/role-management/my-permissions`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setPermissions(legacyResponse.data.permissions);
        setLevel(legacyResponse.data.level);
      } catch (legacyError) {
        // Default to basic permissions on error
        setPermissions({
          can_view_own_data: true,
          can_edit_own_profile: true,
          can_submit_requests: true,
          can_view_team_data: false,
          can_approve_requests: false,
          can_view_reports: false,
          can_manage_team: false
        });
        setLevel(50);
      }
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions, user]);

  // Permission check functions
  const can = (permission) => {
    if (!permissions) return false;
    
    // Check raw RBAC permissions first
    if (permissions.raw_permissions) {
      const perms = permissions.raw_permissions;
      if (perms.includes('*')) return true;
      if (perms.includes(permission)) return true;
      // Check wildcard patterns
      if (perms.some(p => p.endsWith('.*') && permission.startsWith(p.slice(0, -2)))) {
        return true;
      }
    }
    
    // Fall back to boolean permissions
    return permissions[permission] === true;
  };

  const canViewTeamData = () => can('can_view_team_data') || can('team.view');
  const canApproveRequests = () => can('can_approve_requests') || can('approvals.*') || rbacData?.can_approve;
  const canViewReports = () => can('can_view_reports') || can('reports.*');
  const canManageTeam = () => can('can_manage_team') || can('team.manage');
  const canSubmitRequests = () => can('can_submit_requests');
  const canEditOwnProfile = () => can('can_edit_own_profile');
  const canManageUsers = () => can('can_manage_users') || rbacData?.can_manage_users;

  // Check if user is manager or above (using RBAC level)
  const isManagerOrAbove = () => {
    if (rbacData?.level >= 70) return true;
    return level === 'manager' || level === 'leader' || 
           ['admin', 'hr_manager', 'manager', 'sr_manager', 'principal_consultant'].includes(user?.role);
  };

  // Check if user is leader (high-level access)
  const isLeader = () => {
    if (rbacData?.level >= 80) return true;
    return level === 'leader' || ['admin', 'hr_manager', 'principal_consultant'].includes(user?.role);
  };

  // Check if user is admin
  const isAdmin = () => {
    return user?.role === 'admin' || rbacData?.level === 100;
  };

  // Get stage access for sales funnel
  const getStageAccess = () => {
    return rbacData?.stage_access || permissions?.stage_access || {
      mode: 'guided',
      visible_stages: ['LEAD', 'MEETING', 'PRICING'],
      can_skip_stages: false
    };
  };

  return (
    <PermissionContext.Provider value={{
      permissions,
      rbacData,
      level,
      loading,
      can,
      canViewTeamData,
      canApproveRequests,
      canViewReports,
      canManageTeam,
      canSubmitRequests,
      canEditOwnProfile,
      canManageUsers,
      isManagerOrAbove,
      isLeader,
      isAdmin,
      getStageAccess,
      refreshPermissions: fetchPermissions
    }}>
      {children}
    </PermissionContext.Provider>
  );
};

export const usePermissions = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissions must be used within a PermissionProvider');
  }
  return context;
};

export default PermissionContext;
