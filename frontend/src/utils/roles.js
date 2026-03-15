/**
 * Centralized Role Helper Utilities
 * SINGLE SOURCE OF TRUTH for all frontend RBAC logic
 * 
 * Matches backend/routers/deps.py definitions exactly.
 * Use these functions for consistent RBAC checks across the application.
 * All functions handle null/undefined user objects safely.
 * 
 * MIGRATION: All pages must import from this file instead of inline role checks.
 */

// ============================================================================
// ROLE GROUPS - Exactly matching backend/routers/deps.py
// ============================================================================

export const ADMIN_ROLES = ['admin'];

export const HR_ROLES = ['admin', 'hr_manager', 'hr_executive'];

export const HR_ADMIN_ROLES = ['admin', 'hr_manager'];

export const SALES_ROLES = ['admin', 'sales_manager', 'manager', 'sr_manager', 'principal_consultant', 'executive', 'sales_executive'];

export const SALES_MANAGER_ROLES = ['admin', 'sales_manager', 'manager', 'sr_manager', 'principal_consultant'];

export const SALES_EXECUTIVE_ROLES = ['admin', 'executive', 'sales_executive', 'sales_manager'];

export const PROJECT_ROLES = ['admin', 'principal_consultant', 'senior_consultant', 'manager', 'project_manager'];

export const SENIOR_CONSULTING_ROLES = ['admin', 'principal_consultant', 'senior_consultant'];

export const PRINCIPAL_CONSULTANT_ROLES = ['admin', 'principal_consultant'];

export const CONSULTING_ROLES = ['admin', 'consultant', 'lean_consultant', 'lead_consultant', 'senior_consultant', 'principal_consultant', 'subject_matter_expert'];

export const FINANCE_ROLES = ['admin', 'finance_manager', 'finance_executive', 'accounts'];

export const MANAGER_ROLES = ['admin', 'manager', 'sr_manager', 'sales_manager', 'hr_manager', 'principal_consultant'];

export const APPROVAL_ROLES = ['admin', 'manager', 'hr_manager', 'principal_consultant'];

export const HR_PM_ROLES = ['admin', 'hr_manager', 'hr_executive', 'principal_consultant'];

export const AGREEMENT_APPROVE_ROLES = ['admin', 'principal_consultant'];

export const EMPLOYEE_ROLES = [
  'admin', 'hr_manager', 'hr_executive',
  'sales_manager', 'manager', 'sr_manager', 'executive', 'sales_executive',
  'consultant', 'lean_consultant', 'lead_consultant', 'senior_consultant', 'principal_consultant', 'subject_matter_expert',
  'finance_manager', 'finance_executive', 'accounts', 'project_manager'
];

// ============================================================================
// PRIMARY ROLE CHECKS - Single role verification
// ============================================================================

/** Check if user is admin */
export const isAdmin = (user) => user?.role === 'admin';

/** Check if user is HR (includes admin) */
export const isHR = (user) => HR_ROLES.includes(user?.role);

/** Check if user is HR Manager specifically */
export const isHRManager = (user) => user?.role === 'hr_manager';

/** Check if user is HR Executive specifically */
export const isHRExecutive = (user) => user?.role === 'hr_executive';

/** Check if user is HR Admin (admin or hr_manager only, not hr_executive) */
export const isHRAdmin = (user) => HR_ADMIN_ROLES.includes(user?.role);

/** Check if user is in Sales team */
export const isSales = (user) => SALES_ROLES.includes(user?.role);

/** Check if user is Sales Manager */
export const isSalesManager = (user) => SALES_MANAGER_ROLES.includes(user?.role);

/** Check if user is Sales Executive */
export const isSalesExecutive = (user) => SALES_EXECUTIVE_ROLES.includes(user?.role);

/** Check if user is in Consulting team */
export const isConsulting = (user) => CONSULTING_ROLES.includes(user?.role);

/** Check if user is Consultant specifically */
export const isConsultant = (user) => user?.role === 'consultant';

/** Check if user is Senior Consultant or above */
export const isSeniorConsulting = (user) => SENIOR_CONSULTING_ROLES.includes(user?.role);

/** Check if user is Senior Consultant specifically */
export const isSeniorConsultant = (user) => user?.role === 'senior_consultant';

/** Check if user is Principal Consultant or admin */
export const isPrincipalConsultant = (user) => PRINCIPAL_CONSULTANT_ROLES.includes(user?.role);

/** Check if user is Project Manager */
export const isProjectManager = (user) => user?.role === 'project_manager';

/** Check if user has project-level roles */
export const hasProjectRole = (user) => PROJECT_ROLES.includes(user?.role);

/** Check if user is in Finance team */
export const isFinance = (user) => FINANCE_ROLES.includes(user?.role);

/** Check if user is Finance Manager specifically */
export const isFinanceManager = (user) => user?.role === 'finance_manager';

/** Check if user is any Manager role */
export const isManager = (user) => MANAGER_ROLES.includes(user?.role);

/** Check if user can approve things */
export const hasApprovalRole = (user) => APPROVAL_ROLES.includes(user?.role);

/** Check if user can approve agreements */
export const canApproveAgreements = (user) => AGREEMENT_APPROVE_ROLES.includes(user?.role);

// ============================================================================
// COMBINED/CONTEXT-SPECIFIC CHECKS - For specific UI permissions
// ============================================================================

/** Check if user is Admin or HR */
export const isAdminOrHR = (user) => isAdmin(user) || isHR(user);

/** Check if user is Admin or Manager */
export const isAdminOrManager = (user) => isAdmin(user) || isManager(user);

/** Check if user is Admin or Finance */
export const isAdminOrFinance = (user) => isAdmin(user) || isFinance(user);

/** Check if user is Admin or Principal Consultant */
export const isAdminOrPrincipal = (user) => isAdmin(user) || isPrincipalConsultant(user);

/** Check if user can manage employees (HR admin functions) */
export const canManageEmployees = (user) => isHRAdmin(user);

/** Check if user can manage clients (Admin/Finance only) */
export const canManageClients = (user) => isAdmin(user) || isFinance(user);

/** Check if user can approve expenses */
export const canApproveExpenses = (user) => 
  ['admin', 'hr_manager', 'manager', 'finance_manager', 'principal_consultant'].includes(user?.role);

/** Check if user can create manual expenses (not through funnel) */
export const canCreateManualExpense = (user) => 
  ['admin', 'hr_manager', 'hr_executive', 'accounts', 'finance_manager', 'finance_executive'].includes(user?.role);

/** Check if user can view team data */
export const canViewTeamData = (user) => isManager(user);

/** Check if user can view all data (admin-level access) */
export const canViewAllData = (user) => isAdmin(user) || isPrincipalConsultant(user);

/** Check if user can edit leads */
export const canEditLeads = (user) => isSales(user);

/** Check if user can view scorecard */
export const canViewScorecard = (user) => 
  ['admin', 'hr_manager', 'hr_executive', 'manager'].includes(user?.role);

/** Check if user can manage documents */
export const canManageDocuments = (user) => isAdmin(user) || isHR(user);

/** Check if user can manage passwords */
export const canManagePasswords = (user) => isHRAdmin(user);

/** Check if user can manage attendance */
export const canManageAttendance = (user) => isHR(user);

/** Check if user can manage leave */
export const canManageLeave = (user) => isHR(user);

/** Check if user can manage payroll */
export const canManagePayroll = (user) => isHRAdmin(user);

/** Check if user can manage CTC */
export const canManageCTC = (user) => isHR(user);

/** Check if user can manage projects */
export const canManageProjects = (user) => hasProjectRole(user);

/** Check if user can manage consultants */
export const canManageConsultants = (user) => isAdmin(user) || isSeniorConsulting(user);

/** Check if user can manage staffing */
export const canManageStaffing = (user) => isHRAdmin(user);

/** Check if user can manage roles */
export const canManageRoles = (user) => isAdmin(user);

/** Check if user can view all projects */
export const canViewAllProjects = (user) => 
  ['admin', 'principal_consultant', 'senior_consultant'].includes(user?.role);

/** Check if user can manage gantt chart */
export const canManageGantt = (user) => 
  ['admin', 'project_manager', 'manager', 'principal_consultant'].includes(user?.role);

/** Check if user is consulting team (for project payment access) */
export const isConsultingTeam = (user) => 
  ['admin', 'principal_consultant', 'project_manager', 'manager', 'consultant', 'lead_consultant', 'senior_consultant'].includes(user?.role);

// ============================================================================
// SAFE GETTERS - For displaying role information
// ============================================================================

/** Get user's role safely */
export const getRole = (user) => user?.role || 'unknown';

/** Get user's department safely */
export const getDepartment = (user) => user?.department || 'General';

/** Check if user is in specific department */
export const isInDepartment = (user, dept) => 
  user?.department?.toLowerCase() === dept?.toLowerCase();

/** Check if user is in HR department (by department, not role) */
export const isHRDepartment = (user) => isInDepartment(user, 'HR');

/** Get human-readable role name */
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
    subject_matter_expert: 'Subject Matter Expert',
    project_manager: 'Project Manager',
    finance_manager: 'Finance Manager',
    finance_executive: 'Finance Executive',
    accounts: 'Accounts',
    manager: 'Manager',
    sr_manager: 'Senior Manager',
  };
  return roleNames[user?.role] || user?.role || 'Unknown';
};

// ============================================================================
// UTILITY HELPERS - Safe property access
// ============================================================================

/** Safe nested property access */
export const safeGet = (obj, path, defaultValue = '') => {
  const keys = path.split('.');
  let result = obj;
  for (const key of keys) {
    result = result?.[key];
    if (result === undefined || result === null) return defaultValue;
  }
  return result;
};

/** Ensure value is array */
export const safeArray = (arr) => Array.isArray(arr) ? arr : [];

/** Safe string with default */
export const safeString = (val, defaultVal = '-') => val || defaultVal;

/** Safe number with default */
export const safeNumber = (val, defaultVal = 0) => Number(val) || defaultVal;

// ============================================================================
// DEFAULT EXPORT - All functions and constants
// ============================================================================

export default {
  // Role Groups
  ADMIN_ROLES,
  HR_ROLES,
  HR_ADMIN_ROLES,
  SALES_ROLES,
  SALES_MANAGER_ROLES,
  SALES_EXECUTIVE_ROLES,
  PROJECT_ROLES,
  SENIOR_CONSULTING_ROLES,
  PRINCIPAL_CONSULTANT_ROLES,
  CONSULTING_ROLES,
  FINANCE_ROLES,
  MANAGER_ROLES,
  APPROVAL_ROLES,
  HR_PM_ROLES,
  AGREEMENT_APPROVE_ROLES,
  EMPLOYEE_ROLES,
  
  // Primary Checks
  isAdmin,
  isHR,
  isHRManager,
  isHRExecutive,
  isHRAdmin,
  isSales,
  isSalesManager,
  isSalesExecutive,
  isConsulting,
  isConsultant,
  isSeniorConsulting,
  isSeniorConsultant,
  isPrincipalConsultant,
  isProjectManager,
  hasProjectRole,
  isFinance,
  isFinanceManager,
  isManager,
  hasApprovalRole,
  canApproveAgreements,
  
  // Combined Checks
  isAdminOrHR,
  isAdminOrManager,
  isAdminOrFinance,
  isAdminOrPrincipal,
  canManageEmployees,
  canManageClients,
  canApproveExpenses,
  canCreateManualExpense,
  canViewTeamData,
  canViewAllData,
  canEditLeads,
  canViewScorecard,
  canManageDocuments,
  canManagePasswords,
  canManageAttendance,
  canManageLeave,
  canManagePayroll,
  canManageCTC,
  canManageProjects,
  canManageConsultants,
  canManageStaffing,
  canManageRoles,
  canViewAllProjects,
  canManageGantt,
  isConsultingTeam,
  
  // Getters
  getRole,
  getDepartment,
  isInDepartment,
  isHRDepartment,
  getRoleName,
  
  // Utilities
  safeGet,
  safeArray,
  safeString,
  safeNumber,
};
