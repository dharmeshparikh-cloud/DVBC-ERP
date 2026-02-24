/**
 * API Response Normalizer & Safe API Utilities
 * Ensures consistent API response handling across the application
 */
import axios from 'axios';
import { toast } from 'sonner';
import { extractErrorMessage, SafeArray, SafeObject } from './SafeRender';

/**
 * Normalize API response to a consistent format
 * @param {any} response - Raw API response
 * @returns {Object} Normalized response
 */
export const normalizeResponse = (response) => {
  // Handle axios response wrapper
  const data = response?.data ?? response;
  
  // Already normalized
  if (data && typeof data === 'object' && 'success' in data && 'data' in data) {
    return data;
  }
  
  // Wrap raw data
  return {
    success: true,
    data: data,
    message: '',
    errors: null
  };
};

/**
 * Normalize error response
 * @param {any} error - Error object
 * @returns {Object} Normalized error response
 */
export const normalizeError = (error) => {
  const message = extractErrorMessage(error, 'An error occurred');
  const status = error?.response?.status || 500;
  const detail = error?.response?.data?.detail;
  
  return {
    success: false,
    data: null,
    message: message,
    status: status,
    errors: typeof detail === 'object' ? detail : null
  };
};

/**
 * Safe API call wrapper with automatic error handling
 * @param {Function} apiCall - Async function that makes the API call
 * @param {Object} options - Options for handling
 * @returns {Promise<Object>} Normalized response
 */
export const safeApiCall = async (apiCall, options = {}) => {
  const {
    showErrorToast = true,
    showSuccessToast = false,
    successMessage = 'Success',
    errorMessage = 'An error occurred',
    onSuccess = null,
    onError = null
  } = options;

  try {
    const response = await apiCall();
    const normalized = normalizeResponse(response);
    
    if (showSuccessToast && normalized.success) {
      toast.success(normalized.message || successMessage);
    }
    
    if (onSuccess) {
      onSuccess(normalized);
    }
    
    return normalized;
  } catch (error) {
    const normalized = normalizeError(error);
    
    if (showErrorToast) {
      toast.error(normalized.message || errorMessage);
    }
    
    if (onError) {
      onError(normalized);
    }
    
    return normalized;
  }
};

/**
 * Safe data extractor for API responses
 * Handles both paginated and non-paginated responses
 * @param {any} response - API response
 * @param {string} key - Optional key to extract
 * @returns {Array|Object} Extracted data
 */
export const extractData = (response, key = null) => {
  // Handle axios wrapper
  const data = response?.data ?? response;
  
  // Handle null/undefined
  if (!data) return key ? {} : [];
  
  // Handle paginated response
  if (data.items && Array.isArray(data.items)) {
    return key ? { items: data.items, pagination: data.pagination } : data.items;
  }
  
  // Handle success wrapper
  if (data.success !== undefined && data.data !== undefined) {
    return extractData(data.data, key);
  }
  
  // Handle specific key
  if (key && typeof data === 'object') {
    return data[key] ?? (Array.isArray(data) ? [] : {});
  }
  
  // Return as-is if array
  if (Array.isArray(data)) {
    return data;
  }
  
  // Return data object
  return data;
};

/**
 * Extract array from response, always returns array
 * @param {any} response - API response
 * @returns {Array}
 */
export const extractArray = (response) => {
  const data = extractData(response);
  return SafeArray(data);
};

/**
 * Extract object from response, always returns object
 * @param {any} response - API response
 * @returns {Object}
 */
export const extractObject = (response) => {
  const data = extractData(response);
  return SafeObject(data);
};

/**
 * Safe toast helpers that never render objects
 */
export const safeToast = {
  success: (message) => {
    const safeMsg = typeof message === 'string' ? message : extractErrorMessage(message, 'Success');
    toast.success(safeMsg);
  },
  
  error: (message) => {
    const safeMsg = typeof message === 'string' ? message : extractErrorMessage(message, 'An error occurred');
    toast.error(safeMsg);
  },
  
  warning: (message) => {
    const safeMsg = typeof message === 'string' ? message : extractErrorMessage(message, 'Warning');
    toast.warning(safeMsg);
  },
  
  info: (message) => {
    const safeMsg = typeof message === 'string' ? message : extractErrorMessage(message, 'Info');
    toast.info(safeMsg);
  },

  // Handle API errors specifically
  apiError: (error, defaultMessage = 'Request failed') => {
    const message = extractErrorMessage(error, defaultMessage);
    toast.error(message);
  }
};

/**
 * Create safe axios instance with response interceptors
 */
export const createSafeAxios = (baseURL) => {
  const instance = axios.create({ baseURL });
  
  // Response interceptor to normalize errors
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      // Log the full error for debugging
      console.error('API Error:', {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        data: error.response?.data
      });
      return Promise.reject(error);
    }
  );
  
  return instance;
};

export default {
  normalizeResponse,
  normalizeError,
  safeApiCall,
  extractData,
  extractArray,
  extractObject,
  safeToast
};
