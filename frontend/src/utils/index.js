/**
 * Utils Index - Central export for all utility functions
 */

// Array Safety Utilities
export { 
  ensureArray, 
  ensureObject,
  safeMap,
  safeFilter,
  safeReduce,
  safeFind,
  safeLength,
  safeFirst,
  safeLast,
  validateApiResponse,
  normalizeApiResponse,
  logTypeError 
} from './arraySafety';

// API Data Extraction
export {
  extractArray,
  extractObject,
  extractWithDefault,
  isPaginatedResponse,
  extractPagination,
  safeFilter as extractSafeFilter,
  safeMap as extractSafeMap,
  safeFind as extractSafeFind,
  safeLength as extractSafeLength
} from './apiDataExtractor';

// Safe Render Utilities
export {
  toSafeString,
  extractErrorMessage,
  isSafeToRender,
  SafeRender,
  SafeText,
  SafeNumber,
  SafeArray,
  SafeObject
} from './SafeRender';

// Error Handler
export { handleError, handleApiError } from './errorHandler';

// Sanitization
export { sanitizeDisplayText, sanitizeHtml } from './sanitize';
