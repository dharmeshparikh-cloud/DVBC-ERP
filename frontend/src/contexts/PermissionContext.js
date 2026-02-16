import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API } from '../App';

const PermissionContext = createContext(null);

/**
 * Permission Provider - Manages user permissions across the app
 * 
 * Features:
 * - Fetches permissions from backend
 * - Caches permissions
 * - Provides hasPermission, canAccess helpers
 * - Supports module-level and feature-level checks
 */
export const PermissionProvider = ({ children, user }) => {
  const [permissions, setPermissions] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchPermissions();
    } else {
      setPermissions(null);
      setLoading(false);
    }
  }, [user]);

  const fetchPermissions = async () => {
    try {
      const response = await fetch(`${API}/permissions/my-permissions`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPermissions(data);
      } else {
        // Default permissions based on role if API fails
        setPermissions(getDefaultPermissions(user?.role));
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
      setPermissions(getDefaultPermissions(user?.role));
    } finally {
      setLoading(false);
    }
  };

  // Default permissions fallback based on role
  const getDefaultPermissions = (role) => {
    const defaultPerms = {
      admin: {
        modules: ['sales', 'hr', 'consulting', 'finance', 'admin'],
        features: {
          leads: { view: true, create: true, edit: true, delete: true },
          meetings: { view: true, create: true, edit: true, delete: true },
          pricing_plans: { view: true, create: true, edit: true, delete: true },
          sow: { view: true, create: true, edit: true, delete: true },
          agreements: { view: true, create: true, edit: true, delete: true },
          employees: { view: true, create: true, edit: true, delete: true },
          payroll: { view: true, create: true, edit: true, delete: true },
          projects: { view: true, create: true, edit: true, delete: true },
          reports: { view: true, create: true, edit: true, delete: true },
          user_management: { view: true, create: true, edit: true, delete: true },
        }
      },
      executive: {
        modules: ['sales'],
        features: {
          leads: { view: true, create: true, edit: true, delete: false },
          meetings: { view: true, create: true, edit: true, delete: false },
          pricing_plans: { view: true, create: true, edit: false, delete: false },
          sow: { view: true, create: false, edit: false, delete: false },
          agreements: { view: true, create: false, edit: false, delete: false },
          reports: { view: true, create: false, edit: false, delete: false },
        }
      },
      account_manager: {
        modules: ['sales'],
        features: {
          leads: { view: true, create: true, edit: true, delete: false },
          meetings: { view: true, create: true, edit: true, delete: true },
          pricing_plans: { view: true, create: true, edit: true, delete: false },
          sow: { view: true, create: true, edit: true, delete: false },
          agreements: { view: true, create: true, edit: false, delete: false },
          reports: { view: true, create: false, edit: false, delete: false },
        }
      },
      manager: {
        modules: ['sales', 'hr', 'consulting'],
        features: {
          leads: { view: true, create: true, edit: true, delete: true },
          meetings: { view: true, create: true, edit: true, delete: true },
          pricing_plans: { view: true, create: true, edit: true, delete: true },
          sow: { view: true, create: true, edit: true, delete: false },
          agreements: { view: true, create: true, edit: true, delete: false },
          employees: { view: true, create: false, edit: false, delete: false },
          projects: { view: true, create: true, edit: true, delete: false },
          reports: { view: true, create: true, edit: false, delete: false },
        }
      },
      hr_manager: {
        modules: ['hr'],
        features: {
          employees: { view: true, create: true, edit: true, delete: true },
          payroll: { view: true, create: true, edit: true, delete: false },
          leave: { view: true, create: true, edit: true, delete: true },
          attendance: { view: true, create: false, edit: true, delete: false },
          reports: { view: true, create: true, edit: false, delete: false },
        }
      },
      consultant: {
        modules: ['consulting'],
        features: {
          projects: { view: true, create: false, edit: false, delete: false },
          tasks: { view: true, create: true, edit: true, delete: false },
          timesheets: { view: true, create: true, edit: true, delete: false },
        }
      },
    };

    return defaultPerms[role] || { modules: [], features: {} };
  };

  /**
   * Check if user has permission for a specific feature action
   * @param {string} feature - Feature name (e.g., 'leads', 'pricing_plans')
   * @param {string} action - Action name ('view', 'create', 'edit', 'delete')
   */
  const hasPermission = useCallback((feature, action = 'view') => {
    if (!permissions) return false;
    if (user?.role === 'admin') return true; // Admin has all permissions
    
    const featurePerms = permissions.features?.[feature];
    if (!featurePerms) return false;
    
    return featurePerms[action] === true;
  }, [permissions, user?.role]);

  /**
   * Check if user can access a module
   * @param {string} module - Module name ('sales', 'hr', 'consulting', 'admin')
   */
  const canAccessModule = useCallback((module) => {
    if (!permissions) return false;
    if (user?.role === 'admin') return true;
    
    return permissions.modules?.includes(module);
  }, [permissions, user?.role]);

  /**
   * Check multiple permissions at once
   * @param {Array} checks - Array of {feature, action} objects
   * @returns {boolean} - True if ALL checks pass
   */
  const hasAllPermissions = useCallback((checks) => {
    return checks.every(({ feature, action }) => hasPermission(feature, action));
  }, [hasPermission]);

  /**
   * Check if user has any of the specified permissions
   * @param {Array} checks - Array of {feature, action} objects
   * @returns {boolean} - True if ANY check passes
   */
  const hasAnyPermission = useCallback((checks) => {
    return checks.some(({ feature, action }) => hasPermission(feature, action));
  }, [hasPermission]);

  /**
   * Get all permissions for a feature
   * @param {string} feature - Feature name
   * @returns {Object} - {view, create, edit, delete} permissions
   */
  const getFeaturePermissions = useCallback((feature) => {
    if (!permissions) return { view: false, create: false, edit: false, delete: false };
    if (user?.role === 'admin') return { view: true, create: true, edit: true, delete: true };
    
    return permissions.features?.[feature] || { view: false, create: false, edit: false, delete: false };
  }, [permissions, user?.role]);

  // Refresh permissions
  const refreshPermissions = useCallback(() => {
    if (user) {
      setLoading(true);
      fetchPermissions();
    }
  }, [user]);

  const value = {
    permissions,
    loading,
    hasPermission,
    canAccessModule,
    hasAllPermissions,
    hasAnyPermission,
    getFeaturePermissions,
    refreshPermissions,
    isAdmin: user?.role === 'admin',
  };

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  );
};

/**
 * Hook to access permission context
 */
export const usePermissions = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    // Return default values when used outside provider
    return {
      permissions: null,
      loading: false,
      hasPermission: () => true,
      canAccessModule: () => true,
      hasAllPermissions: () => true,
      hasAnyPermission: () => true,
      getFeaturePermissions: () => ({ view: true, create: true, edit: true, delete: true }),
      refreshPermissions: () => {},
      isAdmin: false,
    };
  }
  return context;
};

/**
 * Higher-order component to protect components based on permission
 */
export const withPermission = (WrappedComponent, feature, action = 'view') => {
  return function PermissionWrapper(props) {
    const { hasPermission, loading } = usePermissions();
    
    if (loading) {
      return <div className="animate-pulse bg-zinc-200 rounded h-8 w-20"></div>;
    }
    
    if (!hasPermission(feature, action)) {
      return null;
    }
    
    return <WrappedComponent {...props} />;
  };
};

/**
 * Component to conditionally render based on permission
 */
export const PermissionGate = ({ feature, action = 'view', fallback = null, children }) => {
  const { hasPermission, loading } = usePermissions();
  
  if (loading) {
    return null;
  }
  
  if (!hasPermission(feature, action)) {
    return fallback;
  }
  
  return children;
};

export default PermissionContext;
