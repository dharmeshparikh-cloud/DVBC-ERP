/**
 * Centralized sanitization utilities for preventing XSS attacks
 * and cleaning user-facing text display
 */

/**
 * Sanitize display text by removing HTML tags and decoding HTML entities
 * Use this for displaying user-generated content safely
 * @param {string} text - The text to sanitize
 * @returns {string} - Sanitized text safe for display
 */
export const sanitizeDisplayText = (text) => {
  if (!text || typeof text !== 'string') return text;
  // Remove HTML tags
  let clean = text.replace(/<[^>]*>/g, '');
  // Decode common HTML entities
  clean = clean.replace(/&amp;/g, '&');
  clean = clean.replace(/&lt;/g, '<');
  clean = clean.replace(/&gt;/g, '>');
  clean = clean.replace(/&quot;/g, '"');
  clean = clean.replace(/&#039;/g, "'");
  clean = clean.replace(/&nbsp;/g, ' ');
  // Remove any remaining HTML entities
  clean = clean.replace(/&[^;]+;/g, '');
  return clean.trim();
};

/**
 * Sanitize text for use in URLs or query parameters
 * @param {string} text - The text to sanitize
 * @returns {string} - URL-safe text
 */
export const sanitizeForUrl = (text) => {
  if (!text || typeof text !== 'string') return text;
  return encodeURIComponent(text.trim());
};

/**
 * Truncate text to a maximum length with ellipsis
 * @param {string} text - The text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} - Truncated text with ellipsis if needed
 */
export const truncateText = (text, maxLength = 50) => {
  if (!text || typeof text !== 'string') return text;
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
};

/**
 * Sanitize and truncate text for display
 * Combines sanitization with truncation for card/list displays
 * @param {string} text - The text to process
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} - Sanitized and truncated text
 */
export const sanitizeAndTruncate = (text, maxLength = 50) => {
  return truncateText(sanitizeDisplayText(text), maxLength);
};

export default {
  sanitizeDisplayText,
  sanitizeForUrl,
  truncateText,
  sanitizeAndTruncate
};
