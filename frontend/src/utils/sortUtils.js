/**
 * sortUtils.js - Global "Latest First" sorting utilities
 * 
 * Centralized sorting for ERP-wide consistency.
 * All list renders should use these to ensure latest-on-top ordering.
 * ADDITIVE — no existing code modified.
 */

/**
 * Sort array by date field, latest first (descending).
 * Handles missing/null dates gracefully.
 */
export const sortByLatest = (items, dateField = 'created_at') => {
  if (!Array.isArray(items)) return [];
  return [...items].sort((a, b) => {
    const da = new Date(a[dateField] || 0);
    const db = new Date(b[dateField] || 0);
    return db - da;
  });
};

/**
 * Sort by multiple fields with priority.
 * E.g., sortByFields(items, ['meeting_date', 'created_at']) 
 * tries meeting_date first, falls back to created_at
 */
export const sortByFields = (items, dateFields = ['created_at']) => {
  if (!Array.isArray(items)) return [];
  return [...items].sort((a, b) => {
    for (const field of dateFields) {
      const da = a[field] ? new Date(a[field]) : null;
      const db = b[field] ? new Date(b[field]) : null;
      if (da && db && da.getTime() !== db.getTime()) return db - da;
      if (da && !db) return -1;
      if (!da && db) return 1;
    }
    return 0;
  });
};

/**
 * Sort meetings: today first, then future, then past.
 * Within each group, sorted by time ascending (soonest first for today/future).
 */
export const sortMeetingsForDaily = (meetings) => {
  if (!Array.isArray(meetings)) return [];
  const now = new Date();
  const today = now.toISOString().split('T')[0];
  
  return [...meetings].sort((a, b) => {
    const dateA = (a.meeting_date || '').split('T')[0];
    const dateB = (b.meeting_date || '').split('T')[0];
    const isToday_A = dateA === today;
    const isToday_B = dateB === today;
    const isFuture_A = dateA > today;
    const isFuture_B = dateB > today;
    
    // Today first
    if (isToday_A && !isToday_B) return -1;
    if (!isToday_A && isToday_B) return 1;
    
    // Future next (ascending — soonest first)
    if (isFuture_A && isFuture_B) return new Date(a.meeting_date) - new Date(b.meeting_date);
    if (isFuture_A && !isFuture_B) return -1;
    if (!isFuture_A && isFuture_B) return 1;
    
    // Past last (descending — most recent first)
    return new Date(b.meeting_date) - new Date(a.meeting_date);
  });
};
