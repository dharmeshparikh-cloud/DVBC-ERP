/**
 * Hooks Index
 * Central export for all React Query hooks
 * 
 * REACT QUERY ENFORCEMENT - March 2026
 * All API calls MUST use these hooks. Direct axios/fetch in components is NOT allowed.
 */

// Domain-specific hooks
export * from './useEmployees';
export * from './useLeads';
export * from './useOnboarding';
export * from './useChat';
export * from './useProjects';

// Generic hooks (useFetch, useMutate for custom endpoints)
export * from './useApi';

// Utility hooks
export { useDraft } from './useDraft';
export { useSalesPortal } from './useSalesPortal';
export { useToast } from './use-toast';

// Re-export query keys for direct access
export { employeeKeys } from './useEmployees';
export { leadKeys } from './useLeads';
export { onboardingKeys } from './useOnboarding';
export { chatKeys } from './useChat';
export { projectKeys } from './useProjects';
