/**
 * Safe utility functions to prevent "Cannot read properties of undefined" errors
 * Use these instead of direct .includes() calls on potentially undefined values
 */

/**
 * Safe includes check - works on strings, arrays, and handles undefined/null
 * @param {any} value - The value to check (can be undefined, null, string, or array)
 * @param {any} searchElement - The element to search for
 * @returns {boolean} - True if found, false otherwise
 */
export const safeIncludes = (value, searchElement) => {
  if (value === undefined || value === null) return false;
  if (typeof value === 'string') return value.includes(searchElement);
  if (Array.isArray(value)) return value.includes(searchElement);
  return false;
};

/**
 * Safe array access with default
 * @param {any} arr - The array (can be undefined)
 * @param {any} defaultValue - Default value if undefined (default: [])
 */
export const safeArray = (arr, defaultValue = []) => {
  return Array.isArray(arr) ? arr : defaultValue;
};

/**
 * Safe string access with default
 * @param {any} str - The string (can be undefined)
 * @param {any} defaultValue - Default value if undefined (default: '')
 */
export const safeString = (str, defaultValue = '') => {
  return typeof str === 'string' ? str : defaultValue;
};

/**
 * Safe object access with default
 * @param {any} obj - The object (can be undefined)
 * @param {any} defaultValue - Default value if undefined (default: {})
 */
export const safeObject = (obj, defaultValue = {}) => {
  return obj && typeof obj === 'object' && !Array.isArray(obj) ? obj : defaultValue;
};

/**
 * Safe includes check for role-based checks
 * @param {string[]} roles - Array of roles to check against
 * @param {string} userRole - The user's role (can be undefined)
 */
export const hasRole = (roles, userRole) => {
  if (!roles || !Array.isArray(roles)) return false;
  if (!userRole) return false;
  return roles.includes(userRole);
};

/**
 * Safe toLowerCase with includes
 * @param {string} str - The string to search in
 * @param {string} searchStr - The string to search for
 */
export const safeSearchIncludes = (str, searchStr) => {
  if (!str || typeof str !== 'string') return false;
  if (!searchStr || typeof searchStr !== 'string') return false;
  return str.toLowerCase().includes(searchStr.toLowerCase());
};

export default {
  safeIncludes,
  safeArray,
  safeString,
  safeObject,
  hasRole,
  safeSearchIncludes
};
