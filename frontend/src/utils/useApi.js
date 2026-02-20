import { useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { parseError, formatErrorForToast, ERROR_TYPES } from './errorHandler';

/**
 * Custom hook for API calls with automatic error handling
 * Provides loading state, error state, and detailed error display
 */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const clearError = useCallback(() => setError(null), []);

  const request = useCallback(async (config, context = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios(config);
      return { data: response.data, success: true };
    } catch (err) {
      const errorInfo = parseError(err, context);
      setError(errorInfo);
      
      // Show toast for errors
      const toastInfo = formatErrorForToast(errorInfo);
      
      if (errorInfo.type === ERROR_TYPES.AUTH) {
        toast.error(toastInfo.title, {
          description: toastInfo.description,
          action: {
            label: 'Login',
            onClick: () => window.location.href = '/login'
          }
        });
      } else if (errorInfo.type === ERROR_TYPES.BUSINESS_RULE) {
        toast.error(toastInfo.title, {
          description: toastInfo.description,
          duration: 8000
        });
      } else {
        toast.error(toastInfo.title, {
          description: toastInfo.description
        });
      }
      
      return { data: null, success: false, error: errorInfo };
    } finally {
      setLoading(false);
    }
  }, []);

  // Convenience methods
  const get = useCallback((url, context) => 
    request({ method: 'GET', url }, context), [request]);
  
  const post = useCallback((url, data, context) => 
    request({ method: 'POST', url, data }, context), [request]);
  
  const put = useCallback((url, data, context) => 
    request({ method: 'PUT', url, data }, context), [request]);
  
  const patch = useCallback((url, data, context) => 
    request({ method: 'PATCH', url, data }, context), [request]);
  
  const del = useCallback((url, context) => 
    request({ method: 'DELETE', url }, context), [request]);

  return {
    loading,
    error,
    clearError,
    request,
    get,
    post,
    put,
    patch,
    del
  };
}

/**
 * Setup global axios interceptors for error handling
 * Call this once in App.js
 */
export function setupAxiosInterceptors(onAuthError) {
  // Response interceptor
  axios.interceptors.response.use(
    (response) => response,
    (error) => {
      const errorInfo = parseError(error);
      
      // Handle auth errors globally
      if (errorInfo.type === ERROR_TYPES.AUTH && onAuthError) {
        onAuthError();
      }
      
      // Log errors for debugging (in development)
      if (process.env.NODE_ENV === 'development') {
        console.group('🚨 API Error');
        console.log('Type:', errorInfo.type);
        console.log('Title:', errorInfo.title);
        console.log('Message:', errorInfo.message);
        console.log('Root Cause:', errorInfo.rootCause);
        console.log('Action:', errorInfo.action);
        console.log('Technical:', errorInfo.technical);
        console.groupEnd();
      }
      
      // Attach parsed error info to the error object
      error.parsedError = errorInfo;
      
      return Promise.reject(error);
    }
  );

  // Request interceptor for logging
  axios.interceptors.request.use(
    (config) => {
      // Add timestamp for tracking
      config.metadata = { startTime: new Date() };
      return config;
    },
    (error) => Promise.reject(error)
  );
}

/**
 * Helper to handle API errors consistently
 * Use this in catch blocks when not using useApi hook
 */
export function handleApiError(error, context = {}) {
  const errorInfo = error.parsedError || parseError(error, context);
  const toastInfo = formatErrorForToast(errorInfo);
  
  toast.error(toastInfo.title, {
    description: toastInfo.description,
    duration: errorInfo.type === ERROR_TYPES.BUSINESS_RULE ? 8000 : 5000
  });
  
  return errorInfo;
}

export default useApi;
