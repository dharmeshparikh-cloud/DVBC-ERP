/**
 * Centralized Role Helper Utilities
 * 
 * Use these functions for consistent RBAC checks across the application.
 * All functions handle null/undefined user objects safely.
 */

// Role Groups
export const ADMIN_ROLES = ['admin'];
export const HR_ROLES = ['hr_manager', 'hr_executive', 'admin'];
export const SALES_ROLES = ['executive', 'sales_manager', 'sales_executive', 'admin'];
export const CONSULTING_ROLES = ['consultant', 'senior_consultant', 'lead_consultant', 'principal_consultant', 'lean_consultant', 'project_manager'];
export const FINANCE_ROLES = ['finance_manager', 'finance_executive', 'accounts', 'admin'];
export const MANAGER_ROLES = ['admin', 'manager', 'hr_manager', 'sales_manager', 'principal_consultant', 'project_manager'];

// Primary Role Checks
export const isAdmin = (user) => user?.role === 'admin';

export const isHR = (user) => HR_ROLES.includes(user?.role);

export const isHRManager = (user) => user?.role === 'hr_manager';

export const isSales = (user) => SALES_ROLES.includes(user?.role);

export const isSalesManager = (user) => user?.role === 'sales_manager';

export const isSalesExecutive = (user) => user?.role === 'executive' || user?.role === 'sales_executive';

export const isConsulting = (user) => CONSULTING_ROLES.includes(user?.role);

export const isConsultant = (user) => user?.role === 'consultant';

export const isSeniorConsultant = (user) => user?.role === 'senior_consultant';

export const isPrincipalConsultant = (user) => user?.role === 'principal_consultant';

export const isProjectManager = (user) => user?.role === 'project_manager';

export const isFinance = (user) => FINANCE_ROLES.includes(user?.role);

export const isManager = (user) => MANAGER_ROLES.includes(user?.role);

// Combined Checks
export const isHROrAdmin = (user) => isAdmin(user) || isHR(user);

export const isManagerOrAdmin = (user) => isAdmin(user) || isManager(user);

export const canApproveExpenses = (user) => 
  ['admin', 'hr_manager', 'manager', 'finance_manager'].includes(user?.role);

export const canCreateManualExpense = (user) => 
  ['admin', 'hr_manager', 'hr_executive', 'accounts', 'finance_manager', 'finance_executive'].includes(user?.role);

export const canViewTeamData = (user) => isManager(user);

export const canViewAllData = (user) => isAdmin(user) || isPrincipalConsultant(user);

export const canEditLeads = (user) => isSales(user) && !isManager(user) || isAdmin(user);

export const canViewScorecard = (user) => 
  ['admin', 'hr_manager', 'hr_executive', 'manager'].includes(user?.role);

// Safe Role Getter
export const getRole = (user) => user?.role || 'unknown';

export const getRoleName = (user) => {
  const roleNames = {
    admin: 'Administrator',
    hr_manager: 'HR Manager',
    hr_executive: 'HR Executive',
    sales_manager: 'Sales Manager',
    executive: 'Sales Executive',
    sales_executive: 'Sales Executive',
    consultant: 'Consultant',
    senior_consultant: 'Senior Consultant',
    lead_consultant: 'Lead Consultant',
    principal_consultant: 'Principal Consultant',
    lean_consultant: 'Lean Consultant',
    project_manager: 'Project Manager',
    finance_manager: 'Finance Manager',
    finance_executive: 'Finance Executive',
    accounts: 'Accounts',
    manager: 'Manager',
  };
  return roleNames[user?.role] || user?.role || 'Unknown';
};

// Department Checks
export const getDepartment = (user) => user?.department || 'General';

export const isInDepartment = (user, dept) => 
  user?.department?.toLowerCase() === dept?.toLowerCase();

// Safe Property Access Helpers
export const safeGet = (obj, path, defaultValue = '') => {
  const keys = path.split('.');
  let result = obj;
  for (const key of keys) {
    result = result?.[key];
    if (result === undefined || result === null) return defaultValue;
  }
  return result;
};

export const safeArray = (arr) => Array.isArray(arr) ? arr : [];

export const safeString = (val, defaultVal = '-') => val || defaultVal;

export const safeNumber = (val, defaultVal = 0) => Number(val) || defaultVal;

export default {
  isAdmin,
  isHR,
  isHRManager,
  isSales,
  isSalesManager,
  isSalesExecutive,
  isConsulting,
  isConsultant,
  isSeniorConsultant,
  isPrincipalConsultant,
  isProjectManager,
  isFinance,
  isManager,
  isHROrAdmin,
  isManagerOrAdmin,
  canApproveExpenses,
  canCreateManualExpense,
  canViewTeamData,
  canViewAllData,
  canEditLeads,
  canViewScorecard,
  getRole,
  getRoleName,
  getDepartment,
  isInDepartment,
  safeGet,
  safeArray,
  safeString,
  safeNumber,
  ADMIN_ROLES,
  HR_ROLES,
  SALES_ROLES,
  CONSULTING_ROLES,
  FINANCE_ROLES,
  MANAGER_ROLES,
};
