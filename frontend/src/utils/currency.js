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

/**
 * Convert number to words in Indian format
 * @param {number} num - Number to convert
 * @returns {string} Number in words
 */
export const numberToWords = (num) => {
  if (num === 0) return 'Zero Only';
  
  const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
  
  const convertBelowHundred = (n) => {
    if (n < 20) return ones[n];
    return tens[Math.floor(n / 10)] + (n % 10 ? ' ' + ones[n % 10] : '');
  };
  
  const convertBelowThousand = (n) => {
    if (n < 100) return convertBelowHundred(n);
    return ones[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + convertBelowHundred(n % 100) : '');
  };
  
  // Handle Indian numbering system (Lakhs, Crores)
  const amount = Math.floor(num);
  const paise = Math.round((num - amount) * 100);
  
  let words = '';
  
  if (amount >= 10000000) {
    words += convertBelowThousand(Math.floor(amount / 10000000)) + ' Crore ';
  }
  if (amount >= 100000) {
    words += convertBelowHundred(Math.floor((amount % 10000000) / 100000)) + ' Lakh ';
  }
  if (amount >= 1000) {
    words += convertBelowHundred(Math.floor((amount % 100000) / 1000)) + ' Thousand ';
  }
  if (amount >= 100) {
    words += convertBelowThousand(Math.floor((amount % 1000)));
  } else if (amount > 0) {
    words += convertBelowHundred(amount);
  }
  
  words = words.trim();
  
  if (paise > 0) {
    words += ' and ' + convertBelowHundred(paise) + ' Paise';
  }
  
  return 'Indian Rupees ' + words + ' Only';
};
