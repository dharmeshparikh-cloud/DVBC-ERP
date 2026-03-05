# HR Module UX Refactor - Pre-Change Audit
## Date: December 2025

---

## 1. PAGE MAPPING TABLE

| Page | Route | API Endpoints Used | React Query Keys | Workflow Stage | Dependent Modules |
|------|-------|-------------------|------------------|----------------|-------------------|
| Employees.js | /employees | GET /api/employees, GET /api/employees/all | ['employees'] | N/A | Payroll, Attendance |
| OnboardingHub.js | /onboarding-hub | GET /api/onboarding/submissions, POST /api/onboarding/invite | ['onboarding-submissions'] | invited → submitted | Go-Live |
| SubmissionReview.js | /onboarding/review/:id | GET /api/onboarding/submissions/:id, POST /api/onboarding/submissions/:id/* | ['onboarding-submission', id] | submitted → completed | Employees |
| HROnboarding.js | /onboarding | GET /api/onboarding-candidates | ['onboarding', 'candidates'] | Legacy flow | - |
| GoLiveDashboard.js | /go-live | GET /api/employees, GET /api/go-live/* | ['employees', 'go-live'] | pending → active | Employees |
| EmployeeWorkflows.js | /employee-workflows | GET /api/governance/* | ['governance'] | Consent tracking | Employees |
| HRDashboard.js | / (HR users) | GET /api/stats/hr | ['stats', 'hr'] | N/A | All HR |
| LeaveManagement.js | /leave-management | GET /api/leave-requests | ['leaves'] | N/A | Attendance |
| Attendance.js | /attendance | GET /api/attendance/* | ['attendance'] | N/A | Payroll |
| Payroll.js | /payroll | GET /api/payroll/* | ['payroll'] | N/A | Employees |

---

## 2. ONBOARDING STATUS MAPPING

### Backend Statuses (from /app/backend/routers/onboarding.py):

| Backend Status | Description | Next Status | UI Stage Name |
|----------------|-------------|-------------|---------------|
| `invited` | Email sent to candidate | draft | Invited |
| `draft` | Candidate started form | submitted | Documents Pending |
| `submitted` | Form submitted for review | approved/revision_requested | Under Review |
| `revision_requested` | HR requested changes | submitted | Revision Requested |
| `approved` | Documents verified | completed | Go-Live Pending |
| `completed` | Employee created | N/A | Active |
| `rejected` | Candidate rejected | N/A | Rejected |

### Employee Go-Live Statuses (from /app/backend/routers/go_live.py):

| Status | Description |
|--------|-------------|
| `not_submitted` | Default for new employees |
| `pending` | Go-Live request submitted |
| `active` | Approved and activated |

---

## 3. REACT QUERY HOOKS INVENTORY

| Hook File | Exported Hooks | Query Keys |
|-----------|----------------|------------|
| useOnboarding.js | useOnboardingSubmissions, useOnboardingSubmission, useGoLiveRequests, useOnboardingStats | onboardingKeys.* |
| useEmployees.js | useEmployees, useAllEmployees, useEmployee, useDepartmentsList | employeeKeys.* |
| useHROnboarding.js | useCandidates, useCandidate | Legacy hooks |
| useAttendance.js | useAttendance, useMyAttendance | attendanceKeys.* |
| useLeaves.js | useLeaves, useMyLeaves, useLeaveBalance | leaveKeys.* |
| usePayroll.js | usePayroll, usePayrollSummary | payrollKeys.* |

---

## 4. NAVIGATION STRUCTURE (CURRENT)

```
HR Section:
├── Employees
├── Onboarding Hub [New]
├── Legacy Onboarding
├── Go-Live Dashboard
├── Employee Workflows [New]
├── Employee Permissions
├── Password Management
├── Document Center
├── Leave & Attendance
├── HR Leave Input
├── HR Attendance Input
├── Attendance & Leave Settings
├── Leave Policy Management
├── CTC & Payroll
├── Payroll Summary Report
└── HR Reports
```

Total: 16 items (TOO MANY)

---

## 5. PROPOSED PIPELINE STAGE MAPPING

| UI Stage | Backend Status(es) | Source Collection | API Endpoint |
|----------|-------------------|-------------------|--------------|
| Invited | `invited` | onboarding_submissions | GET /api/onboarding/submissions?status=invited |
| Documents Pending | `draft` | onboarding_submissions | GET /api/onboarding/submissions?status=draft |
| Under Review | `submitted`, `revision_requested` | onboarding_submissions | GET /api/onboarding/submissions?status=submitted |
| Go-Live Pending | `approved` + go_live_status=`pending` | onboarding_submissions + employees | GET /api/go-live/pending |
| Active | `completed` + go_live_status=`active` | employees | GET /api/employees?status=active |

---

## 6. UNCHANGED ITEMS (MUST PRESERVE)

### API Contracts:
- POST /api/onboarding/invite
- GET /api/onboarding/submissions
- POST /api/onboarding/submissions/:id/complete
- GET /api/go-live/checklist/:id
- POST /api/go-live/submit/:id
- POST /api/go-live/approve/:id

### Workflow Logic:
- Employee ID generation (from onboarding.py)
- Document verification flow
- Bank verification flow
- Go-Live approval flow

### Permissions:
- HR roles: hr_manager, hr_executive, hr_admin
- Admin only: go-live approval
- All HR: view onboarding

---

## 7. IMPLEMENTATION CHECKLIST

- [ ] Create NewJoinerPipeline.js page
- [ ] Add "Pending Onboardings" widget to HRDashboard
- [ ] Add "New Joiners" filter to Employees page
- [ ] Archive Legacy Onboarding from nav (keep route)
- [ ] Reorganize HR menu into sub-sections
- [ ] Verify all React Query keys unchanged
- [ ] Run regression tests

---

## 8. RISK ASSESSMENT

| Risk | Mitigation |
|------|------------|
| Breaking existing workflows | Visual-only pipeline, no new status changes |
| API contract changes | None - all reads from existing endpoints |
| Permission issues | Reuse existing permission checks |
| Cache invalidation | Use existing invalidateCache patterns |
