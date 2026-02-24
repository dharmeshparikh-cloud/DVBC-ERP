/**
 * SafeRender - Global utility to safely render any value in JSX
 * Prevents "Objects are not valid as a React child" errors
 */
import React from 'react';

/**
 * Safely converts any value to a renderable string
 * @param {any} value - The value to convert
 * @param {string} fallback - Fallback text for null/undefined
 * @returns {string} - Safe string representation
 */
export const toSafeString = (value, fallback = '-') => {
  if (value === null || value === undefined) {
    return fallback;
  }
  
  if (typeof value === 'string') {
    return value;
  }
  
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  
  if (value instanceof Date) {
    return value.toISOString();
  }
  
  if (Array.isArray(value)) {
    return value.map(item => toSafeString(item, fallback)).join(', ');
  }
  
  if (typeof value === 'object') {
    // Check for common error object patterns
    if (value.message) return String(value.message);
    if (value.msg) return String(value.msg);
    if (value.detail) return String(value.detail);
    if (value.error) return String(value.error);
    
    // For other objects, stringify safely
    try {
      return JSON.stringify(value);
    } catch {
      return '[Object]';
    }
  }
  
  return String(value);
};

/**
 * Extract error message from any error object/response
 * @param {any} error - Error object, API response, or string
 * @param {string} defaultMessage - Default message if extraction fails
 * @returns {string} - Human-readable error message
 */
export const extractErrorMessage = (error, defaultMessage = 'An error occurred') => {
  if (!error) return defaultMessage;
  
  // String error
  if (typeof error === 'string') return error;
  
  // Axios error response
  if (error.response?.data) {
    const data = error.response.data;
    if (typeof data === 'string') return data;
    if (data.detail) {
      // Handle Pydantic validation errors (array of objects)
      if (Array.isArray(data.detail)) {
        return data.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ');
      }
      return String(data.detail);
    }
    if (data.message) return String(data.message);
    if (data.msg) return String(data.msg);
    if (data.error) return String(data.error);
  }
  
  // Direct error object
  if (error.detail) {
    if (Array.isArray(error.detail)) {
      return error.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ');
    }
    return String(error.detail);
  }
  if (error.message) return String(error.message);
  if (error.msg) return String(error.msg);
  if (error.error) return String(error.error);
  
  // Fallback
  if (typeof error === 'object') {
    try {
      const str = JSON.stringify(error);
      if (str !== '{}') return str;
    } catch {
      // ignore
    }
  }
  
  return defaultMessage;
};

/**
 * Check if a value is safe to render directly in JSX
 * @param {any} value - Value to check
 * @returns {boolean}
 */
export const isSafeToRender = (value) => {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return true;
  if (typeof value === 'number') return true;
  if (typeof value === 'boolean') return true;
  if (React.isValidElement(value)) return true;
  return false;
};

/**
 * SafeRender Component - Safely renders any value
 * @param {Object} props
 * @param {any} props.value - Value to render
 * @param {string} props.fallback - Fallback for null/undefined
 * @param {string} props.className - Optional className
 * @param {boolean} props.asCode - Render objects as code block
 */
export const SafeRender = ({ 
  value, 
  fallback = '-', 
  className = '',
  asCode = false 
}) => {
  // Null/undefined
  if (value === null || value === undefined) {
    return <span className={className}>{fallback}</span>;
  }
  
  // Already safe types
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className={className}>{String(value)}</span>;
  }
  
  // React element
  if (React.isValidElement(value)) {
    return value;
  }
  
  // Date
  if (value instanceof Date) {
    return <span className={className}>{value.toLocaleDateString()}</span>;
  }
  
  // Array
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className={className}>{fallback}</span>;
    return (
      <span className={className}>
        {value.map((item, i) => (
          <React.Fragment key={i}>
            {i > 0 && ', '}
            <SafeRender value={item} fallback={fallback} />
          </React.Fragment>
        ))}
      </span>
    );
  }
  
  // Object - extract meaningful content
  if (typeof value === 'object') {
    // Error objects
    if (value.message || value.msg || value.detail || value.error) {
      const msg = value.message || value.msg || value.detail || value.error;
      return <SafeRender value={msg} fallback={fallback} className={className} />;
    }
    
    // Render as code if requested
    if (asCode) {
      return (
        <pre className={`text-xs bg-zinc-100 dark:bg-zinc-800 p-2 rounded overflow-auto ${className}`}>
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    
    // Default: stringify
    try {
      const str = JSON.stringify(value);
      if (str === '{}') return <span className={className}>{fallback}</span>;
      return <span className={className}>{str}</span>;
    } catch {
      return <span className={className}>[Object]</span>;
    }
  }
  
  // Fallback
  return <span className={className}>{String(value)}</span>;
};

/**
 * SafeText - Simpler version that just returns a string
 * Use in places where you need a string, not a component
 */
export const SafeText = (value, fallback = '-') => toSafeString(value, fallback);

/**
 * SafeNumber - Safely extract and format a number
 */
export const SafeNumber = (value, fallback = 0) => {
  if (value === null || value === undefined) return fallback;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const num = parseFloat(value);
    return isNaN(num) ? fallback : num;
  }
  return fallback;
};

/**
 * SafeArray - Ensure value is always an array
 */
export const SafeArray = (value) => {
  if (Array.isArray(value)) return value;
  if (value === null || value === undefined) return [];
  return [value];
};

/**
 * SafeObject - Ensure value is always an object
 */
export const SafeObject = (value) => {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value;
  return {};
};

export default SafeRender;
