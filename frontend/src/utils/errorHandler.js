/**
 * Error Handler Utility
 * Provides detailed, user-friendly error messages with root cause analysis
 */

// Error type classifications
export const ERROR_TYPES = {
  AUTH: 'authorization',
  VALIDATION: 'validation',
  NOT_FOUND: 'not_found',
  PERMISSION: 'permission',
  SERVER: 'server',
  NETWORK: 'network',
  BUSINESS_RULE: 'business_rule',
  DEPENDENCY: 'dependency'
};

// Error code to user-friendly message mapping
const ERROR_MESSAGES = {
  // Auth errors
  401: {
    type: ERROR_TYPES.AUTH,
    title: 'Session Expired',
    message: 'Your session has expired. Please log in again.',
    action: 'Click here to login',
    actionType: 'login'
  },
  403: {
    type: ERROR_TYPES.PERMISSION,
    title: 'Access Denied',
    message: 'You don\'t have permission to perform this action.',
    action: 'Contact your administrator for access',
    actionType: 'contact'
  },
  404: {
    type: ERROR_TYPES.NOT_FOUND,
    title: 'Not Found',
    message: 'The requested resource could not be found.',
    action: 'Check if the item exists or was deleted',
    actionType: 'refresh'
  },
  422: {
    type: ERROR_TYPES.VALIDATION,
    title: 'Validation Error',
    message: 'The provided data is invalid.',
    action: 'Please check your input and try again',
    actionType: 'fix_input'
  },
  500: {
    type: ERROR_TYPES.SERVER,
    title: 'Server Error',
    message: 'An unexpected error occurred on the server.',
    action: 'Please try again or contact support',
    actionType: 'retry'
  },
  502: {
    type: ERROR_TYPES.SERVER,
    title: 'Service Unavailable',
    message: 'The server is temporarily unavailable.',
    action: 'Please try again in a few moments',
    actionType: 'retry'
  }
};

// Business rule error patterns
const BUSINESS_RULE_PATTERNS = [
  {
    pattern: /ctc.*approval.*required/i,
    title: 'CTC Approval Required',
    message: 'Employee CTC must be approved before this action.',
    action: 'Go to CTC & Payroll → Approve CTC',
    actionPath: '/ctc-designer',
    rootCause: 'The employee\'s compensation structure has not been finalized'
  },
  {
    pattern: /bank.*details.*required/i,
    title: 'Bank Details Missing',
    message: 'Bank account details are required for this employee.',
    action: 'Go to Employee Profile → Add Bank Details',
    actionPath: '/employees',
    rootCause: 'Salary disbursement requires verified bank account'
  },
  {
    pattern: /onboarding.*not.*complete/i,
    title: 'Onboarding Incomplete',
    message: 'Employee onboarding process is not complete.',
    action: 'Complete all onboarding steps first',
    actionPath: '/onboarding',
    rootCause: 'Required onboarding documents or steps are pending'
  },
  {
    pattern: /reporting.*manager.*required/i,
    title: 'Reporting Manager Not Set',
    message: 'A reporting manager must be assigned to this employee.',
    action: 'Go to Employee Profile → Set Reporting Manager',
    actionPath: '/employees',
    rootCause: 'Approval workflows require a reporting hierarchy'
  },
  {
    pattern: /department.*access.*required/i,
    title: 'Department Access Missing',
    message: 'Employee needs department access for this feature.',
    action: 'Go to Department Access Manager',
    actionPath: '/department-access',
    rootCause: 'Feature access is controlled by department permissions'
  },
  {
    pattern: /already.*exists/i,
    title: 'Duplicate Entry',
    message: 'This record already exists in the system.',
    action: 'Search for existing record instead',
    rootCause: 'Unique constraint violation - data already present'
  },
  {
    pattern: /not.*authorized/i,
    title: 'Authorization Required',
    message: 'You are not authorized to perform this action.',
    action: 'Request access from HR or Admin',
    rootCause: 'Your role does not have permission for this operation'
  },
  {
    pattern: /pending.*approval/i,
    title: 'Approval Pending',
    message: 'This item is waiting for approval.',
    action: 'Contact the approver to expedite',
    rootCause: 'Workflow is blocked waiting for higher authority approval'
  },
  {
    pattern: /employee.*not.*found/i,
    title: 'Employee Not Found',
    message: 'The employee record could not be found.',
    action: 'Verify the employee ID or check if they are active',
    rootCause: 'Employee may be inactive, terminated, or ID is incorrect'
  },
  {
    pattern: /leave.*balance.*insufficient/i,
    title: 'Insufficient Leave Balance',
    message: 'Not enough leave balance for this request.',
    action: 'Check available balance or apply for different leave type',
    rootCause: 'Requested days exceed available leave quota'
  },
  {
    pattern: /expense.*limit.*exceeded/i,
    title: 'Expense Limit Exceeded',
    message: 'The expense amount exceeds the allowed limit.',
    action: 'Split into multiple claims or get special approval',
    rootCause: 'Policy limit for this expense category exceeded'
  }
];

/**
 * Parse API error and return detailed error info
 */
export function parseError(error, context = {}) {
  const response = error.response;
  const status = response?.status;
  const data = response?.data;
  
  // Default error structure
  let errorInfo = {
    type: ERROR_TYPES.SERVER,
    title: 'Error',
    message: 'An unexpected error occurred',
    detail: null,
    rootCause: null,
    action: 'Please try again',
    actionPath: null,
    actionType: 'retry',
    technical: null,
    context: context
  };

  // Network error (no response)
  if (!response) {
    return {
      ...errorInfo,
      type: ERROR_TYPES.NETWORK,
      title: 'Connection Error',
      message: 'Unable to connect to the server',
      rootCause: 'Network issue or server is down',
      action: 'Check your internet connection and try again',
      technical: error.message
    };
  }

  // Get base error info from status code
  if (ERROR_MESSAGES[status]) {
    errorInfo = { ...errorInfo, ...ERROR_MESSAGES[status] };
  }

  // Extract detail from response
  const detail = data?.detail || data?.message || data?.error;
  if (detail) {
    errorInfo.detail = detail;
    
    // Check for business rule patterns
    for (const rule of BUSINESS_RULE_PATTERNS) {
      if (rule.pattern.test(detail)) {
        errorInfo = {
          ...errorInfo,
          type: ERROR_TYPES.BUSINESS_RULE,
          title: rule.title,
          message: rule.message,
          action: rule.action,
          actionPath: rule.actionPath,
          rootCause: rule.rootCause
        };
        break;
      }
    }
  }

  // Add context-specific information
  if (context.operation) {
    errorInfo.message = `Failed to ${context.operation}: ${errorInfo.message}`;
  }

  // Add technical details for debugging (only shown in dev mode or for admins)
  errorInfo.technical = {
    status,
    endpoint: error.config?.url,
    method: error.config?.method?.toUpperCase(),
    timestamp: new Date().toISOString(),
    requestId: response?.headers?.['x-request-id']
  };

  return errorInfo;
}

/**
 * Format error for toast display
 */
export function formatErrorForToast(errorInfo) {
  let description = errorInfo.message;
  
  if (errorInfo.rootCause) {
    description += `\n\n📍 Root Cause: ${errorInfo.rootCause}`;
  }
  
  if (errorInfo.action) {
    description += `\n\n✅ Action: ${errorInfo.action}`;
  }
  
  return {
    title: `❌ ${errorInfo.title}`,
    description,
    duration: errorInfo.type === ERROR_TYPES.BUSINESS_RULE ? 8000 : 5000
  };
}

/**
 * Get icon for error type
 */
export function getErrorIcon(type) {
  switch (type) {
    case ERROR_TYPES.AUTH:
      return '🔐';
    case ERROR_TYPES.PERMISSION:
      return '🚫';
    case ERROR_TYPES.NOT_FOUND:
      return '🔍';
    case ERROR_TYPES.VALIDATION:
      return '⚠️';
    case ERROR_TYPES.BUSINESS_RULE:
      return '📋';
    case ERROR_TYPES.DEPENDENCY:
      return '🔗';
    case ERROR_TYPES.NETWORK:
      return '📡';
    default:
      return '❌';
  }
}

/**
 * Simple helper to extract a user-readable error message from API errors.
 * Handles Pydantic validation errors (array format) and string errors.
 * 
 * @param {Object} error - The error object from axios catch block
 * @param {string} defaultMessage - Default message if extraction fails
 * @returns {string} Human-readable error message
 */
export const getApiErrorMessage = (error, defaultMessage = 'An error occurred') => {
  const detail = error?.response?.data?.detail;
  
  // Handle Pydantic validation errors (array of objects with msg property)
  if (Array.isArray(detail)) {
    const messages = detail
      .map(e => e.msg || e.message || 'Validation error')
      .filter(Boolean);
    return messages.length > 0 ? messages.join(', ') : defaultMessage;
  }
  
  // Handle string errors
  if (typeof detail === 'string') {
    return detail;
  }
  
  // Handle object errors with message property
  if (detail && typeof detail === 'object' && detail.message) {
    return detail.message;
  }
  
  // Handle error.message (network errors, etc.)
  if (error?.message) {
    return error.message;
  }
  
  return defaultMessage;
};

export default {
  parseError,
  formatErrorForToast,
  getErrorIcon,
  getApiErrorMessage,
  ERROR_TYPES
};
