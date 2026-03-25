/**
 * Sales Components Index
 * 
 * GOVERNANCE: All sales tables MUST use SalesDataTable
 * DO NOT use manual <table> with .map() rendering
 */

// Core DataTable
export { SalesDataTable, FILTER_TYPES, STATUS_COLORS, QUICK_VIEWS, getStatusColor } from './SalesDataTable';

// Specialized Sales Tables
export { LeadsTable } from './LeadsTable';
export { MeetingsTable } from './MeetingsTable';
export { FollowUpsTable } from './FollowUpsTable';
export { QuotationsTable } from './QuotationsTable';
