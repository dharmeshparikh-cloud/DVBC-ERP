/**
 * Project Status Action Controller
 * 
 * Controls which actions are available based on project/SOW status.
 * When a project is "completed", most modification actions should be disabled.
 * 
 * Usage:
 *   import { isActionAllowed, getDisabledReason } from '../utils/projectActions';
 *   
 *   const canEdit = isActionAllowed(project.status, 'edit_task');
 *   const reason = getDisabledReason(project.status, 'edit_task');
 */

// Project statuses
export const PROJECT_STATUS = {
  PENDING_KICKOFF: 'pending_kickoff',
  ACTIVE: 'active',
  COMPLETED: 'completed',
  ON_HOLD: 'on_hold',
  CANCELLED: 'cancelled',
};

// Action types
export const ACTIONS = {
  // Kickoff actions
  CREATE_KICKOFF: 'create_kickoff',
  EDIT_KICKOFF: 'edit_kickoff',
  
  // Team actions
  ASSIGN_CONSULTANT: 'assign_consultant',
  REMOVE_CONSULTANT: 'remove_consultant',
  CHANGE_TEAM: 'change_team',
  
  // Task actions
  CREATE_TASK: 'create_task',
  EDIT_TASK: 'edit_task',
  DELETE_TASK: 'delete_task',
  CHANGE_TASK_STATUS: 'change_task_status',
  ASSIGN_TASK: 'assign_task',
  
  // SOW actions
  CREATE_SCOPE: 'create_scope',
  EDIT_SCOPE: 'edit_scope',
  DELETE_SCOPE: 'delete_scope',
  CREATE_CHANGE_REQUEST: 'create_change_request',
  
  // Document actions
  UPLOAD_DOCUMENT: 'upload_document',
  DELETE_DOCUMENT: 'delete_document',
  
  // Payment actions
  CREATE_PAYMENT: 'create_payment',
  SEND_REMINDER: 'send_reminder',
  
  // View-only (always allowed)
  VIEW_DETAILS: 'view_details',
  VIEW_HISTORY: 'view_history',
  DOWNLOAD_DOCUMENT: 'download_document',
  EXPORT_DATA: 'export_data',
};

// Define which actions are allowed for each status
const ACTION_PERMISSIONS = {
  [PROJECT_STATUS.PENDING_KICKOFF]: {
    allowed: [
      ACTIONS.CREATE_KICKOFF,
      ACTIONS.EDIT_KICKOFF,
      ACTIONS.VIEW_DETAILS,
      ACTIONS.VIEW_HISTORY,
      ACTIONS.DOWNLOAD_DOCUMENT,
      ACTIONS.EXPORT_DATA,
    ],
    message: 'Project is pending kickoff approval',
  },
  
  [PROJECT_STATUS.ACTIVE]: {
    allowed: 'all', // All actions allowed
    message: null,
  },
  
  [PROJECT_STATUS.COMPLETED]: {
    allowed: [
      // Only view-only actions
      ACTIONS.VIEW_DETAILS,
      ACTIONS.VIEW_HISTORY,
      ACTIONS.DOWNLOAD_DOCUMENT,
      ACTIONS.EXPORT_DATA,
    ],
    message: 'Project is completed. Only viewing is allowed.',
  },
  
  [PROJECT_STATUS.ON_HOLD]: {
    allowed: [
      ACTIONS.VIEW_DETAILS,
      ACTIONS.VIEW_HISTORY,
      ACTIONS.DOWNLOAD_DOCUMENT,
      ACTIONS.EXPORT_DATA,
      // Some limited actions
      ACTIONS.CREATE_CHANGE_REQUEST,
    ],
    message: 'Project is on hold',
  },
  
  [PROJECT_STATUS.CANCELLED]: {
    allowed: [
      ACTIONS.VIEW_DETAILS,
      ACTIONS.VIEW_HISTORY,
      ACTIONS.DOWNLOAD_DOCUMENT,
      ACTIONS.EXPORT_DATA,
    ],
    message: 'Project has been cancelled',
  },
};

/**
 * Check if an action is allowed for a given project status
 * @param {string} status - Project status
 * @param {string} action - Action to check (from ACTIONS)
 * @returns {boolean} - Whether the action is allowed
 */
export const isActionAllowed = (status, action) => {
  // Default to allowed if status is unknown (fail-open for backwards compatibility)
  if (!status || !ACTION_PERMISSIONS[status]) {
    return true;
  }
  
  const permissions = ACTION_PERMISSIONS[status];
  
  // If all actions allowed
  if (permissions.allowed === 'all') {
    return true;
  }
  
  // Check if action is in allowed list
  return Array.isArray(permissions.allowed) && permissions.allowed.includes(action);
};

/**
 * Get the reason why an action is disabled
 * @param {string} status - Project status
 * @param {string} action - Action being attempted
 * @returns {string|null} - Reason message or null if allowed
 */
export const getDisabledReason = (status, action) => {
  if (isActionAllowed(status, action)) {
    return null;
  }
  
  return ACTION_PERMISSIONS[status]?.message || 'Action not allowed for current project status';
};

/**
 * Check if project is in a read-only state
 * @param {string} status - Project status
 * @returns {boolean}
 */
export const isProjectReadOnly = (status) => {
  return status === PROJECT_STATUS.COMPLETED || status === PROJECT_STATUS.CANCELLED;
};

/**
 * Check if project is in an editable state
 * @param {string} status - Project status
 * @returns {boolean}
 */
export const isProjectEditable = (status) => {
  return status === PROJECT_STATUS.ACTIVE;
};

/**
 * Get button props with disabled state based on project status
 * @param {string} status - Project status
 * @param {string} action - Action type
 * @returns {object} - Props to spread on button { disabled, title }
 */
export const getActionButtonProps = (status, action) => {
  const allowed = isActionAllowed(status, action);
  const reason = getDisabledReason(status, action);
  
  return {
    disabled: !allowed,
    title: reason || undefined,
    'data-disabled-reason': reason || undefined,
  };
};

/**
 * Higher-order component props generator for action buttons
 * Adds visual indication and tooltip for disabled state
 */
export const withProjectStatusCheck = (status, action, additionalDisabled = false) => {
  const statusDisabled = !isActionAllowed(status, action);
  const reason = getDisabledReason(status, action);
  
  return {
    disabled: statusDisabled || additionalDisabled,
    title: statusDisabled ? reason : undefined,
    className: statusDisabled ? 'opacity-50 cursor-not-allowed' : '',
  };
};

export default {
  PROJECT_STATUS,
  ACTIONS,
  isActionAllowed,
  getDisabledReason,
  isProjectReadOnly,
  isProjectEditable,
  getActionButtonProps,
  withProjectStatusCheck,
};
