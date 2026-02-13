/**
 * Format currency in Indian Rupees (₹)
 * @param {number} amount - Amount to format
 * @param {boolean} showDecimals - Whether to show decimal places (default: true)
 * @returns {string} Formatted currency string
 */
export const formatINR = (amount, showDecimals = true) => {
  if (!amount && amount !== 0) return '₹0';
  
  const formatter = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  });
  
  return formatter.format(amount);
};

/**
 * Format currency without symbol (for inputs)
 * @param {number} amount - Amount to format
 * @returns {string} Formatted number string
 */
export const formatNumber = (amount) => {
  if (!amount && amount !== 0) return '0';
  return new Intl.NumberFormat('en-IN').format(amount);
};

/**
 * Parse Indian formatted number to float
 * @param {string} value - String value to parse
 * @returns {number} Parsed number
 */
export const parseINR = (value) => {
  if (!value) return 0;
  // Remove currency symbol, commas, and whitespace
  const cleaned = value.replace(/[₹,\s]/g, '');
  return parseFloat(cleaned) || 0;
};
