/**
 * API Data Extraction Utilities
 * Handles both paginated and non-paginated API responses safely
 * 
 * Usage:
 *   import { extractArray, extractObject } from '../utils/apiDataExtractor';
 *   
 *   const employees = extractArray(response.data);  // Always returns array
 *   const employee = extractObject(response.data);  // Always returns object
 */

/**
 * Safely extracts an array from API response
 * Handles: arrays, paginated responses {items: []}, and null/undefined
 * 
 * @param {any} data - API response data
 * @param {string} [key] - Optional key if data is nested (e.g., 'items', 'results')
 * @returns {Array} - Always returns an array
 */
export const extractArray = (data, key = null) => {
  // Handle null/undefined
  if (data === null || data === undefined) {
    return [];
  }

  // If key is specified, extract from that key first
  if (key && typeof data === 'object' && !Array.isArray(data)) {
    const extracted = data[key];
    return Array.isArray(extracted) ? extracted : [];
  }

  // Direct array
  if (Array.isArray(data)) {
    return data;
  }

  // Paginated response patterns
  if (typeof data === 'object') {
    // Common pagination patterns
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.results)) return data.results;
    if (Array.isArray(data.data)) return data.data;
    if (Array.isArray(data.records)) return data.records;
    if (Array.isArray(data.list)) return data.list;
    if (Array.isArray(data.rows)) return data.rows;
  }

  // Fallback - return empty array
  return [];
};

/**
 * Safely extracts an object from API response
 * 
 * @param {any} data - API response data
 * @returns {Object} - Always returns an object
 */
export const extractObject = (data) => {
  if (data === null || data === undefined) {
    return {};
  }

  if (typeof data === 'object' && !Array.isArray(data)) {
    return data;
  }

  return {};
};

/**
 * Safely extracts a value with a default fallback
 * 
 * @param {any} data - API response data
 * @param {any} defaultValue - Default value if data is null/undefined
 * @returns {any} - Data or default value
 */
export const extractWithDefault = (data, defaultValue) => {
  return data ?? defaultValue;
};

/**
 * Checks if response has pagination metadata
 * 
 * @param {any} data - API response data
 * @returns {boolean}
 */
export const isPaginatedResponse = (data) => {
  if (!data || typeof data !== 'object') return false;
  return 'items' in data && ('pagination' in data || 'total' in data || 'page' in data);
};

/**
 * Extracts pagination info from response
 * 
 * @param {any} data - API response data
 * @returns {Object} - Pagination info
 */
export const extractPagination = (data) => {
  if (!data || typeof data !== 'object') {
    return { page: 1, limit: 10, total: 0, pages: 1 };
  }

  return {
    page: data.pagination?.page || data.page || 1,
    limit: data.pagination?.limit || data.limit || data.page_size || 10,
    total: data.pagination?.total || data.total || 0,
    pages: data.pagination?.pages || data.pages || 1
  };
};

/**
 * Safe array filter that handles non-arrays
 * 
 * @param {any} data - Data to filter
 * @param {Function} predicate - Filter function
 * @returns {Array}
 */
export const safeFilter = (data, predicate) => {
  const arr = extractArray(data);
  return arr.filter(predicate);
};

/**
 * Safe array map that handles non-arrays
 * 
 * @param {any} data - Data to map
 * @param {Function} mapper - Map function
 * @returns {Array}
 */
export const safeMap = (data, mapper) => {
  const arr = extractArray(data);
  return arr.map(mapper);
};

/**
 * Safe array find that handles non-arrays
 * 
 * @param {any} data - Data to search
 * @param {Function} predicate - Find function
 * @returns {any}
 */
export const safeFind = (data, predicate) => {
  const arr = extractArray(data);
  return arr.find(predicate);
};

/**
 * Safe length getter that handles non-arrays
 * 
 * @param {any} data - Data to check length
 * @returns {number}
 */
export const safeLength = (data) => {
  const arr = extractArray(data);
  return arr.length;
};

export default {
  extractArray,
  extractObject,
  extractWithDefault,
  isPaginatedResponse,
  extractPagination,
  safeFilter,
  safeMap,
  safeFind,
  safeLength
};
