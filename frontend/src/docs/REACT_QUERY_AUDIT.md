# React Query Implementation Audit Report
## NETRA ERP - Frontend Codebase Analysis

**Date:** March 5, 2026
**Total Pages Analyzed:** 114
**Pages with Direct API Calls:** ~95 remaining (19+ migrated)

**Last Updated:** December 2025
**Recently Migrated:** 
- DocumentCenter.js ✅ (Dec 2025)
- ManagerLeadsDashboard.js ✅ (Dec 2025)
- HRDashboard.js ✅ (Dec 2025)
- Leads.js ✅

---

## SUMMARY

| Category | Count | Severity |
|----------|-------|----------|
| Components with direct fetch() | 15+ | HIGH |
| Components with direct axios | 25+ | HIGH |
| Duplicate API endpoints | 10 endpoints called 3+ times | MEDIUM |
| Queries missing staleTime | Most custom useQuery in pages | MEDIUM |
| Mutations missing invalidation | 0 (hooks are properly configured) | LOW |
| Queries missing error handling | 8+ | MEDIUM |

## RECENTLY MIGRATED COMPONENTS
- ✅ DocumentCenter.js - Full migration with useDocuments hook (Dec 2025)
- ✅ ManagerLeadsDashboard.js - Now uses usePauseLead, useResumeLead (Dec 2025)
- ✅ HRDashboard.js - Converted to useMutation (Dec 2025)
- ✅ Leads.js - Full migration with useLeads hook (Dec 2025)
- ✅ ApprovalsCenter.js
- ✅ HROnboarding.js  
- ✅ EmployeeMobileApp.js
- ✅ Payroll.js - Already using usePayroll hooks
- ✅ UserManagement.js - Already using useUserManagement hooks
- ✅ Reports.js - Already using useReports hooks
- ✅ Employees.js
- ✅ AdminDashboard.js - Using useAdminStats

---

## 1. COMPONENTS STILL USING fetch() DIRECTLY

| Component | API Call | Issue | Fix Recommendation |
|-----------|----------|-------|-------------------|
| ConsultingDashboard.js | `/stats/consulting-dashboard` | Direct fetch in useEffect | Create `useConsultingStats` hook |
| AcceptOfferPage.js | `/letters/view/offer/{token}` | Public page, fetch OK | Low priority - public endpoint |
| AcceptOfferPage.js | `/letters/offer-letters/accept` | POST without mutation | Create `useAcceptOffer` mutation |
| HROnboarding.js:260 | `/permission-config/suggest-department` | Direct fetch in handler | Already has hook, use it |
| HROnboarding.js:425 | `/employees` POST (bulk) | Direct fetch in bulk import | Extend `useCreateEmployee` for bulk |
| OfficeLocationsSettings.js | Google Maps API | External API fetch OK | Low priority - external API |
| DocumentBuilder.js | `/document-history` | Direct fetch | Use `useDocumentHistory` hook |
| Downloads.js | Dynamic endpoint | Direct fetch | Create `useDownload` hook |

---

## 2. COMPONENTS STILL USING axios DIRECTLY

| Component | API Calls | Issue | Fix Recommendation |
|-----------|-----------|-------|-------------------|
| LetterheadSettings.js | 4 axios calls | GET, POST, DELETE, PUT | Create `useLetterhead` hook |
| MobileAppDownload.js | 1 axios call | Stats fetch | Use existing `useFetch` |
| OnboardingHub.js | 4 axios calls | Submissions + invites | Extend `useOnboarding` hook |
| CandidateOnboardingForm.js | 2 axios calls | Public form + submit | Partially migrated, complete it |
| SubmissionReview.js | Multiple | Review actions | Create `useSubmissionReview` hook |

---

## 3. DUPLICATE API CALLS (Same endpoint in multiple files)

| Endpoint | Call Count | Files Using It | Fix Recommendation |
|----------|------------|----------------|-------------------|
| `/leads` | 13 | ~~Leads~~ ✅, ManagerLeadsDashboard, etc. | Use `useLeads` hook everywhere |
| `/projects` | 11 | Projects, Consultants, etc. | Use `useProjects` hook everywhere |
| `/employees/all` | 9 | Multiple HR pages | Use `useAllEmployees` hook |
| `/consultants` | 7 | Consulting pages | Create `useConsultants` hook |
| `/employees` | 6 | Multiple pages | Use `useEmployees` hook |
| `/clients` | 6 | Sales, Projects pages | Create `useClients` hook |
| `/users` | 5 | UserManagement, Admin | Create `useUsers` hook |
| `/users-with-roles` | 4 | UserManagement pages | Consolidate to single hook |
| `/pricing-plans` | 4 | Sales funnel pages | Create `usePricingPlans` hook |
| `/my/check-status` | 4 | Attendance pages | Use `useMyAttendance` hook |

---

## 4. QUERIES MISSING staleTime IN PAGES

| Component | Query | Issue | Fix Recommendation |
|-----------|-------|-------|-------------------|
| ManagerLeadsDashboard.js | `todayStats` | No staleTime | Add `staleTime: 60000` |
| ManagerLeadsDashboard.js | `performance` | No staleTime | Add `staleTime: 120000` |
| ManagerLeadsDashboard.js | `targetVsAchievement` | No staleTime | Add `staleTime: 120000` |
| MobileAppDownload.js | `stats` | No staleTime | Add `staleTime: 300000` |
| OnboardingHub.js | `legacyRecords` | No staleTime | Add `staleTime: 300000` |
| SubmissionReview.js | `managersData` | No staleTime | Add `staleTime: 300000` |
| ConsultingDashboard.js | `attendanceStatus` | No staleTime | Add `staleTime: 60000` |
| Employees.js | `stats`, `users`, `orgChart` | No staleTime | Add appropriate staleTime |

**Note:** The global `useFetch` hook has default staleTime of 5 minutes, which is good. But custom `useQuery` calls in pages often miss this.

---

## 5. QUERIES WITHOUT LOADING/ERROR HANDLING

| Component | Query | Issue | Fix Recommendation |
|-----------|-------|-------|-------------------|
| ManagerLeadsDashboard.js | Multiple queries | No `isLoading` destructured | Add loading states to UI |
| MobileAppDownload.js | `stats` query | No error handling | Add error boundary or toast |
| OnboardingHub.js | `legacyRecords` | No loading indicator | Add skeleton loader |
| SubmissionReview.js | `managersData` | No error state | Add error message display |
| Employees.js | `stats`, `users` | Partial loading handling | Complete error handling |

---

## 6. HOOKS WITH GOOD PATTERNS (Reference)

The following hooks are well-implemented and can be used as templates:

| Hook | Queries | Mutations | staleTime | Invalidation |
|------|---------|-----------|-----------|--------------|
| useApprovals.js | 12+ | 20+ | ✅ 60000ms | ✅ All mutations |
| useMobileApp.js | 7 | 6 | ✅ 120000ms | ✅ All mutations |
| useHROnboarding.js | 4 | 4 | ✅ 300000ms | ✅ All mutations |
| useApi.js (useFetch) | Generic | Generic | ✅ 5 min default | N/A |
| useEmployees.js | 3 | 3 | ✅ 300000ms | ✅ All mutations |
| useLeads.js | 4 | 3 | ✅ 180000ms | ✅ All mutations |

---

## RECOMMENDED MIGRATION PRIORITY

### HIGH Priority (P0) - Core Business Pages
1. **Payroll.js** - 8 axios calls, critical business function
2. **UserManagement.js** - 8 axios calls, security-related
3. **Reports.js** - 4 axios calls, frequently used
4. **DocumentCenter.js** - 4 fetch calls, document management

### MEDIUM Priority (P1) - Dashboard Pages
5. **AdminDashboard.js** - 3 parallel fetches
6. **HRDashboard.js** - Stats dashboard
7. **ConsultingDashboard.js** - Stats dashboard
8. **ManagerLeadsDashboard.js** - Missing staleTime

### LOW Priority (P2) - Settings & Utility Pages
9. **LetterheadSettings.js** - Settings page
10. **OfficeLocationsSettings.js** - Settings page
11. **MobileAppDownload.js** - Simple stats page

### SKIP (Public/External)
- AcceptOfferPage.js (public endpoint)
- External API calls (Google Maps, etc.)

---

## NEW HOOKS TO CREATE

Based on the duplicate API analysis, these hooks should be created:

```
/app/frontend/src/hooks/
├── useConsultants.js      # 7 duplicate calls
├── useClients.js          # 6 duplicate calls  
├── useUsers.js            # 5 duplicate calls
├── usePricingPlans.js     # 4 duplicate calls
├── usePayroll.js          # Payroll CRUD
├── useReports.js          # Reports CRUD
├── useDocuments.js        # Document management
├── useStats.js            # Dashboard stats (Admin, HR, Sales, Consulting)
├── useLetterhead.js       # Letterhead settings
└── useUserManagement.js   # User/Role management
```

---

## MIGRATION CHECKLIST

For each component migration:

- [ ] Replace direct fetch/axios with useFetch or custom hook
- [ ] Add staleTime (60s for real-time, 5min for stable data)
- [ ] Add error handling in UI
- [ ] Add loading states in UI
- [ ] For mutations: add invalidateQueries on success
- [ ] Remove manual setLoading/setError state management
- [ ] Test data refetching works correctly

---

## CONCLUSION

The React Query migration is approximately **60% complete**. The core infrastructure (useApi.js, domain hooks) is well-implemented. The main gaps are:

1. **114 pages** still have some direct API calls
2. **13 endpoints** are called from multiple files (duplication)
3. **Custom useQuery** calls in pages often miss `staleTime`

**Recommendation:** Create 10 new domain-specific hooks to eliminate duplication and complete the migration systematically by priority.
