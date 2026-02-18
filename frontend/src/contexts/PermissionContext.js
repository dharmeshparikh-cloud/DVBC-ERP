import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';

const PermissionContext = createContext();

export const PermissionProvider = ({ children }) => {
  const { user } = useContext(AuthContext);
  const [permissions, setPermissions] = useState(null);
  const [level, setLevel] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchPermissions = useCallback(async () => {
    if (!user) {
      setPermissions(null);
      setLevel(null);
      setLoading(false);
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/role-management/my-permissions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setPermissions(response.data.permissions);
      setLevel(response.data.level);
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
      // Default to executive permissions on error
      setPermissions({
        can_view_own_data: true,
        can_edit_own_profile: true,
        can_submit_requests: true,
        can_view_team_data: false,
        can_approve_requests: false,
        can_view_reports: false,
        can_manage_team: false
      });
      setLevel('executive');
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
    return permissions[permission] === true;
  };

  const canViewTeamData = () => can('can_view_team_data');
  const canApproveRequests = () => can('can_approve_requests');
  const canViewReports = () => can('can_view_reports');
  const canManageTeam = () => can('can_manage_team');
  const canSubmitRequests = () => can('can_submit_requests');
  const canEditOwnProfile = () => can('can_edit_own_profile');

  // Check if user is manager or above
  const isManagerOrAbove = () => {
    return level === 'manager' || level === 'leader' || 
           ['admin', 'hr_manager', 'manager'].includes(user?.role);
  };

  // Check if user is leader
  const isLeader = () => {
    return level === 'leader' || ['admin', 'hr_manager'].includes(user?.role);
  };

  return (
    <PermissionContext.Provider value={{
      permissions,
      level,
      loading,
      can,
      canViewTeamData,
      canApproveRequests,
      canViewReports,
      canManageTeam,
      canSubmitRequests,
      canEditOwnProfile,
      isManagerOrAbove,
      isLeader,
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
