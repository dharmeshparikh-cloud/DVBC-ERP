/**
 * Centralized IST Time Formatting Utility
 * GOVERNANCE: All time displays across the app MUST use these functions.
 * This ensures consistent IST display regardless of browser timezone.
 */

const IST_TZ = 'Asia/Kolkata';

/**
 * Format a datetime string/Date to IST time (e.g., "03:28 pm")
 */
export const fmtTimeIST = (t) => {
  if (!t) return '-';
  try {
    return new Date(t).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', hour12: true,
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};

/**
 * Format a datetime string/Date to IST 24h time (e.g., "15:28")
 */
export const fmtTime24IST = (t) => {
  if (!t) return '-';
  try {
    return new Date(t).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', hour12: false,
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};

/**
 * Format a datetime string/Date to IST date (e.g., "26/03/2026")
 */
export const fmtDateIST = (d) => {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('en-IN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};

/**
 * Format a datetime string/Date to IST short date (e.g., "26 Mar")
 */
export const fmtDateShortIST = (d) => {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short',
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};

/**
 * Format a datetime string/Date to IST full datetime (e.g., "26 Mar 2026, 03:28 pm")
 */
export const fmtDateTimeIST = (dt) => {
  if (!dt) return '-';
  try {
    return new Date(dt).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true,
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};

/**
 * Get current IST time formatted (e.g., "03:28 pm")
 */
export const nowIST = () => {
  return new Date().toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: IST_TZ
  });
};

/**
 * Format a datetime string/Date to IST weekday + date (e.g., "Thursday, 26 Mar")
 */
export const fmtWeekdayIST = (d) => {
  if (!d) return '-';
  try {
    return new Date(d || new Date()).toLocaleDateString('en-IN', {
      weekday: 'long', day: 'numeric', month: 'short',
      timeZone: IST_TZ
    });
  } catch { return '-'; }
};
