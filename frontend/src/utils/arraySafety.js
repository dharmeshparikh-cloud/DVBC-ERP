/**
 * Array Safety Utilities for ERP
 * Prevents runtime errors like "filter is not a function"
 * 
 * Usage:
 *   import { ensureArray, safeArrayOp, logTypeError } from '../utils/arraySafety';
 *   
 *   const items = ensureArray(apiResponse.data, 'EmployeeList');
 *   const filtered = safeArrayOp(data, 'filter', item => item.active);
 */

const DEBUG_MODE = process.env.NODE_ENV === 'development';

/**
 * Logs type errors to console for debugging
 * @param {string} context - Where the error occurred
 * @param {string} expected - Expected type
 * @param {any} received - Actual value received
 */
export const logTypeError = (context, expected, received) => {
  if (DEBUG_MODE) {
    const receivedType = received === null ? 'null' 
      : received === undefined ? 'undefined'
      : Array.isArray(received) ? 'array'
      : typeof received;
    
    console.warn(
      `[Array Safety] Type mismatch in ${context}:\n` +
      `  Expected: ${expected}\n` +
      `  Received: ${receivedType}\n` +
      `  Value:`, received
    );
    
    // Log stack trace for debugging
    console.trace(`[Array Safety] Call stack for ${context}`);
  }
};

/**
 * Ensures a value is always an array
 * @param {any} value - Value to check
 * @param {string} context - Context for debugging (e.g., 'EmployeeList', 'LeadResponse')
 * @returns {Array} - Always returns an array
 */
export const ensureArray = (value, context = 'unknown') => {
  // Already an array
  if (Array.isArray(value)) {
    return value;
  }
  
  // Null or undefined
  if (value === null || value === undefined) {
    if (DEBUG_MODE && context !== 'unknown') {
      console.debug(`[Array Safety] ${context}: Received ${value}, returning empty array`);
    }
    return [];
  }
  
  // Object with array-like properties (paginated response)
  if (typeof value === 'object') {
    // Common API response patterns
    const arrayKeys = ['items', 'results', 'data', 'records', 'list', 'rows', 'entries'];
    
    for (const key of arrayKeys) {
      if (Array.isArray(value[key])) {
        if (DEBUG_MODE) {
          console.debug(`[Array Safety] ${context}: Extracted array from .${key}`);
        }
        return value[key];
      }
    }
    
    // Log unexpected object
    logTypeError(context, 'array', value);
    return [];
  }
  
  // Log unexpected type
  logTypeError(context, 'array', value);
  return [];
};

/**
 * Ensures a value is an object (not null, not array)
 * @param {any} value - Value to check
 * @param {string} context - Context for debugging
 * @returns {Object} - Always returns an object
 */
export const ensureObject = (value, context = 'unknown') => {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value;
  }
  
  if (value !== null && value !== undefined) {
    logTypeError(context, 'object', value);
  }
  
  return {};
};

/**
 * Safely performs array operations with type checking
 * @param {any} data - Data to operate on
 * @param {string} operation - Array method name ('map', 'filter', 'reduce', 'find', 'some', 'every')
 * @param {Function} callback - Callback function for the operation
 * @param {any} initialValue - Initial value for reduce
 * @param {string} context - Context for debugging
 * @returns {any} - Result of the operation
 */
export const safeArrayOp = (data, operation, callback, initialValue = undefined, context = 'unknown') => {
  const arr = ensureArray(data, context);
  
  switch (operation) {
    case 'map':
      return arr.map(callback);
    case 'filter':
      return arr.filter(callback);
    case 'reduce':
      return initialValue !== undefined 
        ? arr.reduce(callback, initialValue)
        : arr.reduce(callback);
    case 'find':
      return arr.find(callback);
    case 'some':
      return arr.some(callback);
    case 'every':
      return arr.every(callback);
    case 'forEach':
      arr.forEach(callback);
      return undefined;
    default:
      console.warn(`[Array Safety] Unknown operation: ${operation}`);
      return arr;
  }
};

/**
 * Safe map that handles non-arrays
 */
export const safeMap = (data, mapper, context = 'unknown') => 
  ensureArray(data, context).map(mapper);

/**
 * Safe filter that handles non-arrays
 */
export const safeFilter = (data, predicate, context = 'unknown') => 
  ensureArray(data, context).filter(predicate);

/**
 * Safe reduce that handles non-arrays
 */
export const safeReduce = (data, reducer, initial, context = 'unknown') => 
  ensureArray(data, context).reduce(reducer, initial);

/**
 * Safe find that handles non-arrays
 */
export const safeFind = (data, predicate, context = 'unknown') => 
  ensureArray(data, context).find(predicate);

/**
 * Safe length getter
 */
export const safeLength = (data, context = 'unknown') => 
  ensureArray(data, context).length;

/**
 * Safe first element getter
 */
export const safeFirst = (data, context = 'unknown') => 
  ensureArray(data, context)[0];

/**
 * Safe last element getter
 */
export const safeLast = (data, context = 'unknown') => {
  const arr = ensureArray(data, context);
  return arr[arr.length - 1];
};

/**
 * Validates API response structure and logs issues
 * @param {any} response - API response
 * @param {string} endpoint - API endpoint name
 * @param {Object} expectedSchema - Expected schema { data: 'array', count: 'number' }
 * @returns {boolean} - Whether response matches expected schema
 */
export const validateApiResponse = (response, endpoint, expectedSchema) => {
  if (!DEBUG_MODE) return true;
  
  const issues = [];
  
  for (const [key, expectedType] of Object.entries(expectedSchema)) {
    const value = response?.[key];
    const actualType = value === null ? 'null'
      : value === undefined ? 'undefined'
      : Array.isArray(value) ? 'array'
      : typeof value;
    
    if (expectedType === 'array' && !Array.isArray(value)) {
      issues.push(`${key}: expected array, got ${actualType}`);
    } else if (expectedType !== 'array' && actualType !== expectedType) {
      issues.push(`${key}: expected ${expectedType}, got ${actualType}`);
    }
  }
  
  if (issues.length > 0) {
    console.warn(
      `[API Response] Schema violation for ${endpoint}:\n` +
      issues.map(i => `  - ${i}`).join('\n'),
      '\nReceived:', response
    );
    return false;
  }
  
  return true;
};

/**
 * Wraps API response for safe consumption
 * @param {any} response - Raw API response
 * @param {string} context - Context for debugging
 * @returns {Object} - Normalized response with guaranteed structure
 */
export const normalizeApiResponse = (response, context = 'unknown') => {
  // Handle axios response
  const data = response?.data ?? response;
  
  return {
    success: data?.success ?? true,
    data: ensureArray(data, context),
    message: data?.message ?? null,
    pagination: {
      page: data?.page ?? data?.pagination?.page ?? 1,
      limit: data?.limit ?? data?.pagination?.limit ?? 10,
      total: data?.total ?? data?.pagination?.total ?? 0,
    },
    raw: data,
  };
};

export default {
  ensureArray,
  ensureObject,
  safeArrayOp,
  safeMap,
  safeFilter,
  safeReduce,
  safeFind,
  safeLength,
  safeFirst,
  safeLast,
  validateApiResponse,
  normalizeApiResponse,
  logTypeError,
};
