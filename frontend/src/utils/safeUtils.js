/**
 * Safe Utility Functions - GLOBAL SAFETY LAYER
 * Prevents ALL runtime crashes from undefined/null array/object operations
 * 
 * ZERO-CRASH GUARANTEE: Every iteration method must use these wrappers
 */

/**
 * Ensures value is always a safe array
 * @param {any} data - Any value (undefined, null, object, string, etc.)
 * @returns {Array} - Always returns a valid array
 */
export const safeArray = (data) => {
  if (Array.isArray(data)) return data;
  return [];
};

/**
 * Ensures value is always a safe object (not null, not array)
 * @param {any} data - Any value
 * @returns {Object} - Always returns a valid object
 */
export const safeObject = (data) => {
  if (data && typeof data === 'object' && !Array.isArray(data)) return data;
  return {};
};

/**
 * Safe Object.entries - never crashes on undefined/null
 * @param {any} data - Any value
 * @returns {Array} - Always returns array of [key, value] pairs
 */
export const safeEntries = (data) => {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return Object.entries(data);
  }
  return [];
};

/**
 * Safe Object.keys - never crashes on undefined/null
 * @param {any} data - Any value
 * @returns {Array} - Always returns array of keys
 */
export const safeKeys = (data) => {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return Object.keys(data);
  }
  return [];
};

/**
 * Safe Object.values - never crashes on undefined/null
 * @param {any} data - Any value
 * @returns {Array} - Always returns array of values
 */
export const safeValues = (data) => {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return Object.values(data);
  }
  return [];
};

/**
 * Safe string coercion
 * @param {any} val - Any value
 * @returns {string} - Always returns a string
 */
export const safeString = (val) => {
  if (typeof val === 'string') return val;
  if (val === null || val === undefined) return '';
  return String(val);
};

/**
 * Safe number coercion
 * @param {any} val - Any value
 * @returns {number} - Always returns a valid number (0 for NaN)
 */
export const safeNumber = (val) => {
  if (typeof val === 'number' && !isNaN(val)) return val;
  if (typeof val === 'string') {
    const parsed = parseFloat(val);
    return isNaN(parsed) ? 0 : parsed;
  }
  return 0;
};

/**
 * Safe includes check - works on strings, arrays, handles undefined/null
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
 * Safe includes check for role-based checks
 * @param {string[]} roles - Array of roles
 * @param {string} userRole - The user's role
 * @returns {boolean}
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
 * @returns {boolean}
 */
export const safeSearchIncludes = (str, searchStr) => {
  if (!str || typeof str !== 'string') return false;
  if (!searchStr || typeof searchStr !== 'string') return false;
  return str.toLowerCase().includes(searchStr.toLowerCase());
};

/**
 * Safe nested property access
 * @param {any} obj - Root object
 * @param {string} path - Dot-separated path like 'data.items.list'
 * @param {any} defaultValue - Default if path doesn't exist
 * @returns {any}
 */
export const safeGet = (obj, path, defaultValue = undefined) => {
  if (!obj || !path) return defaultValue;
  const keys = path.split('.');
  let result = obj;
  for (const key of keys) {
    if (result === null || result === undefined) return defaultValue;
    result = result[key];
  }
  return result === undefined || result === null ? defaultValue : result;
};

export default {
  safeArray,
  safeObject,
  safeEntries,
  safeKeys,
  safeValues,
  safeString,
  safeNumber,
  safeIncludes,
  hasRole,
  safeSearchIncludes,
  safeGet,
};
