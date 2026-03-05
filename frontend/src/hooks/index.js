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
export * from './useApprovals';
export * from './useMobileApp';
export * from './useHROnboarding';

// New hooks (March 2026 - Duplicate elimination)
export * from './usePayroll';
export * from './useUserManagement';
export * from './useReports';
export * from './useClients';
export * from './useConsultants';
export * from './useStats';
export * from './useDocuments';
export * from './useLetterhead';
export * from './useSecurityAudit';
export * from './useBankRequests';
export * from './usePricingPlans';
export * from './useSOW';
export * from './useMeetings';

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
export { clientKeys } from './useClients';
export { consultantKeys } from './useConsultants';
export { statsKeys } from './useStats';
export { documentKeys } from './useDocuments';
