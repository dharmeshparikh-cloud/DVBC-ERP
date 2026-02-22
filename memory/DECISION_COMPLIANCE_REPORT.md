# NETRA ERP - Decision Document Compliance Report

## Generated: February 22, 2026

---

## SECTION 1: DUPLICATE ROUTES ANALYSIS

### 1.1 Self-Service Routes in Wrong Portals

| Route | Document Decision | Status | Implementation Notes |
|-------|-------------------|--------|---------------------|
| /my-leaves | Keep in ALL employee portals | ✅ DONE | Available in Main ERP, portal redirects in place |
| /my-attendance | Keep in ALL employee portals | ✅ DONE | Available in Main ERP, portal redirects in place |
| /my-salary | Keep in ALL employee portals | ✅ DONE | Available as /my-salary-slips in Main ERP |
| /my-expenses | Keep in ALL employee portals | ✅ DONE | Available in Main ERP, portal redirects in place |
| /my-details | Keep in ALL employee portals | ✅ DONE | Available in Main ERP, portal redirects in place |
| /my-drafts | Inside respective Department module | ⚠️ PARTIAL | Route exists but needs module context filtering |
| /my-bank-details | Keep in ALL employee portals | ✅ DONE | Redirects to /my-details |

### 1.2 Domain-Specific Routes in Wrong Portals

| Route | Document Decision | Status | Implementation Notes |
|-------|-------------------|--------|---------------------|
| /employees | HR + Admin Only | ✅ DONE | Sidebar hidden for Sales Executive, backend role guard needed |
| /projects | Consulting + Admin | ✅ DONE | Available in Main ERP for consulting roles |
| /attendance | HR (Management), Employee (Self View) | ✅ DONE | /attendance for HR, /my-attendance for employees |
| /payroll | HR + Admin Only | ✅ DONE | Only visible to HR roles in sidebar |
| /meetings | Sales + Consulting | ✅ DONE | /sales-meetings canonical route |
| /reports | Role-filtered | ⚠️ TO DO | Reports exist but need role-based filtering implementation |
| /ctc-designer | HR + Admin Only | ✅ DONE | Only visible to HR roles in sidebar |

### 1.3 Overall Decision - Single Portal

| Decision | Status | Notes |
|----------|--------|-------|
| All users access through Main ERP only | ✅ DONE | Sales/HR portals now redirect to Main ERP |
| No separate Sales or HR portals | ✅ DONE | Portal links removed from login page |
| Role-based permissions | ✅ DONE | Sidebar visibility controlled by role |
| Dynamic navigation visibility | ✅ DONE | Layout.js implements role-based sections |

**Data Scoping Hierarchy:**
| Level | Scope | Status |
|-------|-------|--------|
| Employee | Self data only | ✅ DONE |
| Reporting Manager | Self + direct reports | ⚠️ PARTIAL - hasReportees logic exists |
| Department Head | Department level | ⚠️ TO DO - Need department head role |
| Admin | Full access | ✅ DONE |

---

## SECTION 2: SELF-SERVICE API ENDPOINTS

### API Namespace Consolidation

| User Request | Current Endpoint | Suggested Endpoint | Status | Notes |
|--------------|------------------|-------------------|--------|-------|
| My projects | /consultants/my/projects | /my/projects | ⚠️ TO DO | Need to add to /my router |
| My dashboard stats | /consultants/my/dashboard-stats | /my/dashboard-stats | ⚠️ TO DO | Need to consolidate |
| My funnel summary | /analytics/my-funnel-summary | /my/funnel-summary | ⚠️ TO DO | Need to move |
| My approval requests | /approvals/my-requests | /my/approvals | ⚠️ TO DO | Need alias |
| My department access | /department-access/my-access | /my/department-access | ⚠️ TO DO | Need alias |
| My payments | /project-payments/my-payments | /my/payments | ⚠️ TO DO | Need to consolidate |
| My permissions | /role-management/my-permissions | /my/permissions | ⚠️ TO DO | Need alias |
| My travel claims | /travel/my/travel-reimbursements | /my/travel | ⚠️ TO DO | Need to simplify |
| My team (manager) | /users/my-team | /manager/team | ⚠️ TO DO | Need new /manager router |

**My Suggestion:** Create a unified `/my` router that aggregates all personal data endpoints. Keep existing endpoints as aliases for backward compatibility, but encourage new frontend development to use `/my/*` namespace.

---

## SECTION 3: ROLE-BASED ACCESS CONTROL (Security)

### 3.1 HIGH PRIORITY Security Gaps

| Endpoint | Document Decision | Status | Implementation |
|----------|-------------------|--------|----------------|
| GET /agreements | sales, admin, principal_consultant | ✅ DONE | Role guard added in agreements.py |
| POST /agreements | sales_manager, admin (with approval) | ✅ DONE | Creates in pending_approval status for non-admin |
| GET /sow | Sales, consulting for payment view | ⚠️ TO DO | Need to add role guard to enhanced_sow.py |
| GET /leads | sales_*, admin | ✅ DONE | Role guard added in leads.py |
| GET /pricing-plans | sales, admin | ✅ DONE | Role guard added in pricing_plans.py |
| GET /timesheets | self, manager, hr, admin | ✅ DONE | Role guard added in timesheets.py |

### 3.2 Cross-Department Access Policy

| Policy | Document Decision | Status | Notes |
|--------|-------------------|--------|-------|
| Sales view HR data | Own data only | ✅ DONE | Sidebar HR hidden for Sales |
| HR view Sales data | Own data only | ⚠️ TO DO | Need backend enforcement |
| Consulting view Sales data | Project-related only | ⚠️ TO DO | Need project-based filtering |
| Salary information | Self only | ✅ DONE | /my-salary-slips is self-scoped |
| Project financials | Principal consultant only | ⚠️ TO DO | Need to restrict financial views |

---

## SECTION 4: SALES FUNNEL BUSINESS LOGIC

### 4.1 Stage Progression Rules

| Rule | Document Decision | Status | Notes |
|------|-------------------|--------|-------|
| Skip stages | No, resume from where left | ⚠️ TO DO | Need resume functionality |
| Reopen closed deal | No, renew with new project ID | ⚠️ TO DO | Need renewal workflow |
| SOW approval | Manager, Senior/Principal can add scopes | ⚠️ PARTIAL | Manager approval exists |
| Pricing approval | Sales Manager / Principal Consultant | ⚠️ PARTIAL | Need dual approval |

### 4.2 Stage Approval Matrix

| Stage | Creates | Approves | Status |
|-------|---------|----------|--------|
| Lead | Sales Exec | Auto | ✅ DONE |
| Meeting | Sales Exec | Auto | ✅ DONE |
| Pricing | Sales Exec | Manager/Principal (any 2) | ⚠️ TO DO - Need dual approval |
| SOW | Sales Exec | Manager | ✅ DONE |
| Quotation | Auto-generated | Auto | ✅ DONE |
| Agreement | Sales Exec | Client via email | ⚠️ PARTIAL - Client consent needed |
| Payment | Finance/Sales/Consultant | Role-based | ⚠️ TO DO - Complex logic needed |
| Kickoff | Lead Owner → Senior Consultant + Principal + Client | ⚠️ TO DO - Multi-party approval |
| Closed | Auto | Client notified | ⚠️ TO DO - Auto-close logic |

---

## SECTION 5: ADDITIONAL BUSINESS LOGIC

| Question | Document Decision | Status | Notes |
|----------|-------------------|--------|-------|
| Consultants see project revenue/profit | NO | ⚠️ TO DO | Need to hide financial columns |
| Managers see team salary | NO | ✅ DONE | Salary is self-only |
| Employees see org chart with salary | NO | ✅ DONE | Org chart exists without salary |
| Who can delete a lead | Admin only | ⚠️ TO DO | Need to restrict delete |
| Who can reassign leads | Manager | ⚠️ TO DO | Need reassignment endpoint |
| Track audit logs | YES | ⚠️ TO DO | Security audit exists but needs expansion |

---

## SUMMARY

### ✅ COMPLETED (12 items)
1. Single portal architecture (Main ERP only)
2. Portal redirects (/sales/*, /hr/* → Main ERP)
3. Login with Employee ID only
4. Role-based sidebar visibility
5. GET /agreements role guard
6. POST /agreements with approval workflow
7. GET /leads role guard
8. GET /pricing-plans role guard
9. GET /timesheets role guard with scoping
10. Remember Me feature
11. Achievement Scorecard link
12. Canonical route enforcement

### ⚠️ TO DO (18 items)
1. Consolidate /my/* API namespace
2. Create /manager/* router for team data
3. Add role guard to GET /sow
4. HR view Sales data enforcement
5. Consulting view project-related Sales only
6. Project financials restricted to Principal
7. Stage resume functionality
8. Deal renewal workflow
9. Dual approval for Pricing (Manager + Principal)
10. Client consent for Agreement
11. Complex payment recording logic
12. Multi-party Kickoff approval
13. Auto-close project logic
14. Hide financial columns from consultants
15. Restrict lead deletion to Admin
16. Lead reassignment endpoint
17. Expanded audit logging
18. Reports role-based filtering

### 💡 MY SUGGESTIONS

1. **API Namespace Consolidation**: Create a unified `/my` router that provides all personal data from one place. This improves developer experience and simplifies frontend.

2. **Dual Approval Pattern**: Implement a generic `require_dual_approval(roles=[...])` utility in deps.py for stages that need 2 approvers.

3. **Client Consent System**: Build a token-based consent system where clients receive email links to approve/reject agreements without needing an account.

4. **Stage Resume**: Add a `last_stage_completed` field to leads and a "Continue from here" UI button that pre-fills context.

5. **Financial Visibility Matrix**: Create a dedicated `FINANCIAL_VIEW_ROLES` constant and apply it consistently across all money-related endpoints.

6. **Audit Logging**: Implement a decorator `@audit_log(action="update", entity="lead")` that automatically logs changes with before/after values.
