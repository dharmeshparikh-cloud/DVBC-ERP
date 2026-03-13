import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../App';
import { Lock } from 'lucide-react';

/**
 * Role-based route guard.
 * allowedRoles: array of role strings that can access this page.
 * allowedDepts: array of department strings (optional).
 * If user's role or dept matches, children render. Otherwise, redirect or show denied.
 */
const RoleGuard = ({ allowedRoles = [], allowedDepts = [], children }) => {
  const { user } = useContext(AuthContext);
  const role = user?.role?.toLowerCase() || '';
  const dept = user?.department?.toLowerCase() || '';

  // Admin always has access
  if (role === 'admin') return children;

  // Check role match
  if (allowedRoles.length > 0 && allowedRoles.includes(role)) return children;

  // Check department match
  if (allowedDepts.length > 0 && allowedDepts.some(d => dept.includes(d.toLowerCase()))) return children;

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4" data-testid="access-denied">
      <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <Lock className="w-8 h-8 text-red-500" />
      </div>
      <h2 className="text-xl font-semibold text-zinc-900 mb-2">Access Restricted</h2>
      <p className="text-sm text-zinc-500 max-w-md">
        You don't have permission to view this page. Contact your administrator if you believe this is an error.
      </p>
    </div>
  );
};

export default RoleGuard;
