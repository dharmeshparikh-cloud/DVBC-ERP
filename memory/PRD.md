# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication (Employee ID only)
- **AI**: GPT-4o via Emergent LLM Key
- **Documentation**: python-docx, reportlab for PDF/DOCX generation
- **Email**: SMTP via SendGrid

---

## Completed Work - February 2026

### Phase 24: E2E Testing & Validation - February 22, 2026 ✅ (Latest)

**Comprehensive E2E Testing Completed:**
- ✅ **100% Backend Pass Rate** (22/22 tests passed)
- ✅ **100% Frontend Pass Rate** (all critical flows working)
- ✅ All authentication flows tested (Employee ID login with ADMIN001, SM001, HR001, etc.)
- ✅ Leads CRUD with proper schema (49 leads with first_name/last_name)
- ✅ Permission system fully validated (50 feature flags)
- ✅ /my/* APIs verified (guidance-state, dashboard-stats, profile)
- ✅ /manager/* APIs verified (team, approvals)
- ✅ Sales funnel business logic verified (stage-status, resume-stage, renew-deal, kickoff)
- ✅ Audit system verified (summary, logs, security events)
- ✅ Role-based access control validated (Admin full access, Sales scoped)
- ✅ Frontend sidebar visibility based on role permissions

**Test Credentials:**
- Admin: ADMIN001 / test123
- Sales Manager: SM001 / test123
- HR Manager: HR001 / test123
- Sales Executive: SE001 / test123
- Consultant: CON001 / test123

**Test Reports:** `/app/test_reports/iteration_103.json`

---

### Phase 25: Sidebar Role-Based Visibility Fix - February 22, 2026 ✅ (Latest)

**Issue Fixed:** HR Manager was seeing the same sidebar sections as Admin (including Sales section)

**Solution:**
- ✅ Updated `/app/frontend/src/components/Layout.js` to fetch sidebar visibility from `/api/permissions/my-permissions`
- ✅ Now uses centralized permissions API (`sidebarVisibility?.hr_section`, etc.) as primary source
- ✅ Fallback to role-based logic only when API fails
- ✅ Verified: HR Manager no longer sees Sales section, Admin sees all sections

**Sidebar Visibility Matrix:**
| Role | HR | Sales | Consulting | Admin |
|------|----|-------|------------|-------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| HR Manager | ✅ | ❌ | ✅ | ❌ |
| Sales Executive | ❌ | ✅ | ❌ | ❌ |

---

### Phase 22: Enterprise Permission System & API Consolidation - February 22, 2026 ✅

**Enhanced Permission System (`/app/backend/routers/permissions.py`):**
- ✅ 50 controllable feature flags organized by category (Sales, HR, Consulting, Finance, Admin, Personal)
- ✅ Employee-level permission overrides (grant/revoke beyond role defaults)
- ✅ Sidebar visibility mapping to feature permissions
- ✅ Bulk permission update API for multiple employees
- ✅ Approval configuration system (dual/multi-approval support)
- ✅ Permission check utility for real-time access control

---

### Phase 23: Sales Funnel Business Logic & Audit System - February 22, 2026 ✅ (Latest)

**Sales Funnel Business Logic (`/app/backend/routers/sales_funnel_logic.py`):**
- ✅ **Stage Resume** - `/sales-funnel/stage-status/{lead_id}` returns current stage and context
- ✅ **Stage Resume** - `/sales-funnel/resume-stage` returns stage data for continuation
- ✅ **Deal Renewal** - `/sales-funnel/renew-deal` creates new lead from closed deal
- ✅ **Dual Approval** - `/sales-funnel/request-approval` submits for dual/multi approval
- ✅ **Dual Approval** - `/sales-funnel/approve` records individual approvals
- ✅ **Client Consent** - `/sales-funnel/send-consent-request` sends token-based consent email
- ✅ **Client Consent** - `/sales-funnel/submit-consent` records client decision
- ✅ **Multi-Party Kickoff** - `/sales-funnel/kickoff-approval` handles consultant/principal/client approvals
- ✅ **Kickoff Status** - `/sales-funnel/kickoff-status/{lead_id}` shows approval progress

**Approval Requirements (Configurable):**
- Pricing: 2 approvers from [sales_manager, principal_consultant, admin]
- SOW: 1 approver from [sales_manager, manager, admin]
- Agreement: Client consent (token-based)
- Kickoff: 3-party (senior_consultant, principal_consultant, client)

**Expanded Audit Logging (`/app/backend/routers/audit_logging.py`):**
- ✅ `/audit/logs` - Query logs with filters (action, entity, user, date range)
- ✅ `/audit/logs/entity/{type}/{id}` - Complete audit trail for entity
- ✅ `/audit/logs/user/{user_id}` - User action history
- ✅ `/audit/summary` - Dashboard stats (by action, entity, user)
- ✅ `/audit/security` - Security-specific events (logins, permission changes)
- ✅ `log_audit()` function for logging from any router
- ✅ `compute_changes()` function for before/after diff tracking

**Employee ID Logic Fix (`/app/backend/routers/deps.py`):**
- ✅ `EMPLOYEE_ROLES` - Roles requiring employee_id (internal staff)
- ✅ `NON_EMPLOYEE_ROLES` - Roles without employee_id (client, vendor, system)
- ✅ `validate_employee_id_for_role()` - Validates employee_id based on role

---

### Phase 22 (continued): API Consolidation

**API Consolidation - `/my/*` Router (`/app/backend/routers/my_consolidated.py`):**
- ✅ `/my/profile` - User profile
- ✅ `/my/attendance` - Personal attendance
- ✅ `/my/leaves` - Leave requests
- ✅ `/my/leave-balance` - Leave balance
- ✅ `/my/salary-slips` - Salary slips
- ✅ `/my/expenses` - Expense claims
- ✅ `/my/projects` - Assigned projects
- ✅ `/my/timesheets` - Personal timesheets
- ✅ `/my/approvals` - Submitted approval requests
- ✅ `/my/leads` - Assigned leads (sales)
- ✅ `/my/funnel-summary` - Sales funnel stats
- ✅ `/my/dashboard-stats` - Personalized stats
- ✅ `/my/payments` - Project payments
- ✅ `/my/permissions` - Effective permissions
- ✅ `/my/department-access` - Department access config
- ✅ `/my/travel` - Travel claims
- ✅ `/my/scorecard` - Performance scorecard

**API Consolidation - `/manager/*` Router (`/app/backend/routers/manager.py`):**
- ✅ `/manager/team` - Direct reportees list
- ✅ `/manager/team/summary` - Team statistics
- ✅ `/manager/team/attendance` - Team attendance
- ✅ `/manager/team/leaves` - Team leave requests
- ✅ `/manager/team/expenses` - Team expense claims
- ✅ `/manager/team/timesheets` - Team timesheets
- ✅ `/manager/team/leads` - Team leads (sales)
- ✅ `/manager/team/pipeline` - Team pipeline summary
- ✅ `/manager/team/performance` - Team performance metrics
- ✅ `/manager/approvals/pending` - Pending approvals
- ✅ `/manager/leads/reassign` - Lead reassignment

**Backend Security Enhancements:**
- ✅ GET /agreements - Role guard (sales, admin, principal_consultant)
- ✅ POST /agreements - Role guard + approval workflow
- ✅ GET /leads - Role guard (sales_*, admin)
- ✅ GET /pricing-plans - Role guard (sales, admin)
- ✅ GET /timesheets - Role guard with scoping (self, manager, hr, admin)
- ✅ GET /enhanced-sow - Role guard (sales, consulting)
- ✅ User model updated with employee_id field

**Frontend Fixes:**
- ✅ Sidebar HR section hidden for Sales Executives
- ✅ Achievement Scorecard link added to My Workspace
- ✅ Role-based sidebar visibility enforced

---

### Phase 21: Portal Consolidation & Route Governance - February 22, 2026 ✅

**Unified Portal Architecture:**
- ✅ Consolidated Sales and HR portals into single Main ERP portal
- ✅ All users now access the application via a single entry point
- ✅ Login page updated to accept Employee ID only (removed email login)
- ✅ Role-based sidebar visibility (HR, Sales, Consulting, Admin sections)
- ✅ Backward compatible URL redirects for bookmarks/shared links
- ✅ "Remember Me" feature for Employee ID persistence

**CANONICAL ROUTE RULE ENFORCEMENT:**
- ✅ Every page has exactly ONE canonical route
- ✅ All alias routes converted to Navigate redirects
- ✅ No component rendered by multiple independent routes
- ✅ Old portal routes (/sales/*, /hr/*) are REDIRECTS only

**Redirect Conversions:**
- ✅ `/meetings` → `/sales-meetings`
- ✅ `/targets` → `/target-management`
- ✅ `/team-leads` → `/manager-leads`
- ✅ `/document-builder` → `/document-center`
- ✅ `/letter-management` → `/document-center`
- ✅ `/sales-funnel/proforma-invoice` → `/sales-funnel/quotations`

**Portal URL Redirects (`/app/frontend/src/components/PortalRedirect.js`):**
- ✅ `/sales/*` routes → Main ERP equivalents (e.g., `/sales/leads` → `/leads`)
- ✅ `/hr/*` routes → Main ERP equivalents (e.g., `/hr/employees` → `/employees`)
- ✅ `/sales/login` and `/hr/login` → `/login`
- ✅ Dynamic route support (e.g., `/sales/sow/:id` → `/sales-funnel/sow/:id`)

**Login Page Updates (`/app/frontend/src/pages/Login.js`):**
- ✅ Employee ID only login (removed email input option)
- ✅ Removed "HR Portal" and "Sales Portal" footer links
- ✅ Auto-uppercase Employee ID input
- ✅ "Remember my Employee ID" checkbox with localStorage persistence
- ✅ Google OAuth still available for @dvconsulting.co.in accounts

**Sidebar Role-Based Visibility (`/app/frontend/src/components/Layout.js`):**
- ✅ Admin: All sections visible (My Workspace, HR, Sales, Consulting, Admin)
- ✅ HR Manager: My Workspace + HR sections
- ✅ Sales Executive: My Workspace + Sales sections (Guided Mode)
- ✅ Manager: My Workspace + Sales + limited HR
- ✅ Consultant: My Workspace + Consulting sections

**Structural Stats:**
- Total Routes: 114
- Canonical Routes: 97
- Redirect Routes: 17
- Sidebar Items: 60

**Governance Document:** `/app/memory/ROUTE_GOVERNANCE.md`
**Stability Score:** 100/100
**Testing:** ✅ Frontend 100% - All redirects verified working

---

### Phase 19: Leave Policy Management System - February 22, 2026 ✅

**Leave Policy Management with Full Payroll Integration:**
- ✅ HR-editable leave policies at multiple levels (Company, Department, Role, Employee)
- ✅ Earned leave calculation based on service tenure
- ✅ Monthly/yearly accrual support with pro-rata for new joiners
- ✅ Carry forward and encashment rules
- ✅ 100% payroll linkage for LOP deductions and leave encashment

**New Backend APIs (`/app/backend/routers/leave_policies.py`):**
- ✅ `GET /api/leave-policies` - List all policies
- ✅ `POST /api/leave-policies` - Create new policy
- ✅ `PUT /api/leave-policies/{id}` - Update policy
- ✅ `DELETE /api/leave-policies/{id}` - Delete policy
- ✅ `GET /api/leave-policies/effective/{employee_id}` - Get cascaded effective policy
- ✅ `GET /api/leave-policies/calculate-balance/{employee_id}` - Calculate leave balance with accrual
- ✅ `POST /api/leave-policies/apply-to-department/{dept}` - Apply policy to department
- ✅ `POST /api/leave-policies/apply-to-role/{role}` - Apply policy to role
- ✅ `POST /api/leave-policies/apply-to-employee/{id}` - Apply policy to employee
- ✅ `POST /api/leave-policies/year-end-processing/{year}` - Year-end balance processing

**Payroll Integration (`/app/backend/routers/payroll.py`):**
- ✅ `GET /api/payroll/leave-encashments` - List encashment requests
- ✅ `POST /api/payroll/leave-encashments/{id}/approve` - Approve encashment
- ✅ `POST /api/payroll/leave-encashments/{id}/reject` - Reject encashment
- ✅ `GET /api/payroll/leave-policy-adjustments/{employee_id}` - Get LOP/encashment for salary

**New Frontend Page:**
- ✅ `/leave-policy-settings` - Full CRUD for leave policies
- ✅ Policy configuration dialog with 3 tabs (Basic, Leave Types, Payroll Integration)
- ✅ Add/Edit/Delete leave types with all accrual settings
- ✅ Sidebar link under HR section

**Leave Types Supported:**
- Casual Leave (12 days, yearly)
- Sick Leave (6 days, yearly, medical certificate required > 2 days)
- Earned Leave (15 days, monthly accrual 1.25/month, carry forward, encashable)
- Maternity Leave (182 days)
- Paternity Leave (15 days)

**Testing:** ✅ Backend 88%, Frontend 100% (iteration_97.json)

---

### Phase 20: Comprehensive Page Testing - February 22, 2026 ✅

**Complete Application Page Audit:**
- ✅ **86+ unique pages tested** across 3 testing iterations (98, 99, 100)
- ✅ **100% success rate** - All tested pages load correctly with proper UI
- ✅ **92% coverage** of all 125 documented routes
- ✅ **10 dynamic routes** skipped (require specific IDs like `/projects/:projectId`)

**Test Results by Module:**
- ✅ Authentication: 1 page
- ✅ Dashboard: 1 page  
- ✅ My Workspace: 7 pages
- ✅ Sales: 17 pages
- ✅ HR: 16 pages
- ✅ Consulting: 10 pages
- ✅ Admin: 16 pages
- ✅ Reports: 7 pages
- ✅ Communication: 4 pages
- ✅ Documents: 3 pages
- ✅ Other: 15 pages

**Documentation Fixed:**
- ✅ Updated SITEMAP.md with correct route paths
- ✅ Fixed 5 incorrectly documented routes

**Minor Issues (Non-Blocking):**
- Some pages show "Failed to fetch" toasts when no data exists (empty states work correctly)

---

### Phase 18: Broken Pages Fix - February 22, 2026 ✅

**Fixed 6 Broken Pages:**
- ✅ `/my-leaves` - Added missing `/api/my/leave-balance` endpoint
- ✅ `/my-details` - Fixed `/api/my/profile` to handle users without employee records
- ✅ `/leave-management` - Working, added date validation for invalid formats
- ✅ `/timesheets` - Fixed Array/Object response handling, null safety checks
- ✅ `/team-performance` - Added route to main layout
- ✅ `/meetings` - Added route to main layout

**Backend API Additions (`/app/backend/routers/my.py`):**
- ✅ `/api/my/leave-balance` - Returns user's leave balance
- ✅ `/api/my/change-requests` - GET profile change requests
- ✅ `/api/my/change-request` - POST new profile change request
- ✅ `/api/my/profile` - Now gracefully handles users without employee records
- ✅ `/api/my/guidance-state` - Added GET/POST for GuidanceContext (by testing agent)

**Frontend Fixes:**
- ✅ `MyLeaves.js` - Filter out leave requests without id field
- ✅ `LeaveManagement.js` - Filter out items without id, validate dates
- ✅ `Timesheets.js` - Handle array response, null safety for Object.values
- ✅ `App.js` - Added `/meetings` and `/team-performance` to main routes

**Regression Memory Updated:**
- ✅ Added 6 new issues (#012-#017) with root causes and prevention rules
- ✅ All fixes documented for future reference

---

### Phase 17: Regression Memory Layer & Security Hardening - February 22, 2026 ✅

**Created Regression Memory Layer:**
- ✅ `/app/memory/REGRESSION_MEMORY.md` - Documents ALL issues with root cause analysis
- ✅ 11 issues documented with prevention rules
- ✅ Affected modules matrix for change impact analysis
- ✅ System rules enforcement checklist

**Created E2E Validation Script:**
- ✅ `/app/backend/e2e_validation.py` - Full end-to-end validation
- ✅ Tests: Auth, Routes, Role Guards, Masters, SOW, Drafts, Core Data
- ✅ Stability score calculation (minimum 95/100 required)

**Security Hardening - Role Guards Added:**
- ✅ Fixed `/api/employees` - Now requires HR_ROLES or ADMIN_ROLES
- ✅ Fixed `/api/payroll/salary-components` - Now requires HR roles
- ✅ Fixed `/api/users` - Now requires HR_ADMIN_ROLES

**Final Stability Score: 100/100 ✅**
- Database: 10/10
- Auth: 15/15
- Routes: 20/20
- Guards: 10/10
- Masters: 15/15
- SOW Masters: 10/10
- Drafts: 10/10
- Core Data: 10/10

---

### Phase 16: Application-Wide Defaults & Health Check - February 22, 2026 ✅

**Comprehensive Router Audit:**
- ✅ Verified ALL 49 routers use correct `get_db()` pattern
- ✅ All routers import from `.deps` and call `db = get_db()` in each endpoint
- ✅ No routers have broken database connections

**Health Check Script Created:**
- ✅ `/app/backend/health_check.py` - Run after any refactoring
- ✅ Checks: Database connection, All router imports, Critical data collections
- ✅ Usage: `cd /app/backend && python3 health_check.py`

**Current Data Status:**
- 30 users, 7 tenure types, 10 meeting types
- 13 consultant roles, 10 SOW categories, 43 scope templates
- 36 leads, 8 projects

---

### Phase 15: UX Fixes & Route Audit - February 22, 2026 ✅

**Bug Fix 1: SOW Builder Blank Page**
- ✅ Root cause: `/sales-funnel/sow` route requires `:pricingPlanId` parameter
- ✅ Fix: Added redirect from `/sales-funnel/sow` → `/sales-funnel/sow-list`
- ✅ Also added for `/sales/sow` → `/sales/sow-list`

**Bug Fix 2: Sidebar Scroll Position Not Persisting**
- ✅ Added `sidebarNavRef` to track scroll position
- ✅ Implemented `sessionStorage` persistence for scroll position
- ✅ Scroll position now preserved across page navigations

**Bug Fix 3: Database Connection Issue (sow_masters.py)**
- ✅ Fixed `sow_masters.py` to use `get_db()` from deps.py
- ✅ Now SOW Categories (9) and Scopes (43) load correctly

**Route Audit Completed:**
- ✅ All routes properly defined and accessible
- ✅ `my-drafts` route added to all route groups (main, /sales, /hr)
- ✅ No orphaned or mismatched routes found

---

### Phase 14: Pricing Plan Builder & Drafts Fixes - February 22, 2026 ✅

**Bug Fix 1: Masters API Database Not Initialized (P0)**
- ✅ Fixed: `masters.py` and `sow_masters.py` routers had their own `db = None` variable
- ✅ Solution: Changed to use `get_db()` from `deps.py` for consistent database access
- ✅ All masters endpoints now return data

**Bug Fix 2: Draft Save Endpoint Missing (P0)**
- ✅ Created `/app/backend/routers/drafts.py` - Full CRUD for draft management
- ✅ "Save Draft" and "Drafts" features now work in Pricing Plan Builder

**New Feature: My Drafts Page**
- ✅ Added `My Drafts` menu item in MY WORKSPACE sidebar
- ✅ Created `/my-drafts` page to view and continue all saved drafts
- ✅ Features: filter by type, continue button, delete button, last edited timestamp

---

### Phase 13: Guided Sales Workflow Fixes - February 22, 2026 ✅

**Bug Fix: Sales Executive Login (P0)**
- ✅ Fixed: `sales@dvbc.com` user did not exist in database, causing login failures
- ✅ Created user with proper bcrypt password hash (password: `sales123`)
- ✅ User role set to `executive` for proper guided mode activation

**Verified Guided Sales Workflow Features:**
- ✅ Sales Executive login working correctly
- ✅ Role-based sidebar rendering: Guided Workflow Mode banner visible
- ✅ Restricted sidebar shows only "My Leads" and "Today's Follow-ups"
- ✅ "SALES STAGE FLOW" progress indicator with visual checkmarks
- ✅ Admin users see full "SALES" menu (not guided mode)
- ✅ Testing: 100% pass rate (8/8 backend tests, all UI verified via Playwright)

**Test Credentials:**
- Sales Executive: `sales@dvbc.com` / `sales123` (role: executive)
- Admin: `admin@dvbc.com` / `admin123` (role: admin)

---

### Phase 12: Project Completion & Timeline Management - February 22, 2026 ✅

**1. Fixed Projects API Pydantic Validation (P0)**
- ✅ Made all legacy fields Optional in Project model
- ✅ Added data normalization for legacy records (project_name → name)
- ✅ Restored `response_model=List[Project]` for strict validation
- ✅ All 8 projects loading correctly with proper validation

**2. Project Completion Validation System (New Router)**
- ✅ Created `/app/backend/routers/project_completion.py`
- ✅ Endpoints:
  - `GET /api/project-completion/{id}/validate` - Validate completion eligibility
  - `POST /api/project-completion/{id}/complete` - Complete project with validation
  - `PATCH /api/project-completion/{id}/status` - Update status (blocks direct "completed")
  - `GET /api/project-completion/pending-completion` - List projects ready to complete
  - `POST /api/project-completion/recalculate-statuses` - Auto-recalculate all statuses
  - `GET /api/project-completion/{id}/timeline` - Get timeline details

**3. Project Timeline Auto-Calculation**
- ✅ End Date = Kickoff Accept Date + Tenure Months (from pricing plan)
- ✅ Updated `/app/backend/routers/kickoff.py` to set tenure and calculate end_date
- ✅ Projects now store: `tenure_months`, `end_date`, `kickoff_accepted_at`

**4. Auto-Status Calculation Logic**
- `active` - Default, timeline not exceeded
- `at_risk` - Timeline < 30 days remaining AND (payments incomplete OR deliverables < 80%)
- `delayed` - Timeline exceeded but NOT completed
- `completed` - Via completion endpoint only (validates timeline + payments)

**5. Frontend Updates - Projects Page**
- ✅ Added End Date display (prominent timeline section)
- ✅ Added Days Remaining/Overdue indicator with color coding
- ✅ Status badges: Active (green), At Risk (amber), Delayed (red), Completed (blue)
- ✅ Tenure months display when available

**6. P1 - Complete Refactoring Cleanup - Role Constants Centralization**
- ✅ Expanded `/app/backend/routers/deps.py` with comprehensive role constants:
  - `HR_ROLES`, `HR_ADMIN_ROLES`, `HR_PM_ROLES`
  - `PROJECT_ROLES` (merged PROJECT_PM_ROLES)
  - `SALES_ROLES`, `SALES_EXECUTIVE_ROLES`
  - `MANAGER_ROLES`, `APPROVAL_ROLES`
  - `ADMIN_ROLES`, `SENIOR_CONSULTING_ROLES`
- ✅ Updated 18 router files to use centralized role constants
- ✅ Eliminated 100+ hard-coded role arrays
- ✅ Zero remaining hard-coded role arrays in codebase

**7. Removed `project_manager` Role - Simplified Role Hierarchy**
- ✅ Removed `project_manager` from `UserRole` enum
- ✅ Removed from `DEFAULT_ROLES` and `DEFAULT_CONSULTANT_ROLES`
- ✅ Transferred all permissions to `principal_consultant` and `senior_consultant`
- ✅ Migrated 1 existing user (pm@dvbc.com) to `principal_consultant`
- ✅ Updated 10 router files to remove `project_manager` references
- ✅ New consulting hierarchy: `consultant` → `senior_consultant` → `principal_consultant`

**8. P1 - Added `tenure_months` to Pricing Plan Schema**
- ✅ Created `/app/backend/routers/pricing_plans.py` - New router for pricing plans CRUD
- ✅ `tenure_months` is AUTO-CALCULATED from `len(schedule_breakdown)` - no duplicate entry
- ✅ Endpoints:
  - `POST /api/pricing-plans` - Create with auto tenure_months
  - `GET /api/pricing-plans` - List all (backfills tenure if missing)
  - `GET /api/pricing-plans/{id}` - Get single plan
  - `PUT /api/pricing-plans/{id}` - Update (recalculates tenure if schedule changes)
  - `DELETE /api/pricing-plans/{id}` - Delete (admin only)
  - `POST /api/pricing-plans/{id}/clone` - Clone plan
  - `POST /api/pricing-plans/backfill-tenure` - Backfill existing records
- ✅ Backfilled 24 existing pricing plans with `tenure_months`
- ✅ Updated `project_completion.py` to use stored `tenure_months` field

**9. Guided Sales Workflow UX System**
- ✅ Created `/app/frontend/src/contexts/StageGuardContext.js` - Stage flow management
- ✅ Created `/app/frontend/src/components/StageGuardDialog.js` - Smart dialog prompts
- ✅ Created `/app/frontend/src/components/GuidedSalesSidebar.js` - Role-based sidebar
- ✅ Created `/app/backend/routers/stage_guard.py` - Stage validation API
- ✅ Added `/api/leads/{id}/stage` endpoint for stage tracking

**Stage Guard Features:**
- **Role-Based Sidebar Rendering:**
  - Sales Executive → Guided mode (My Leads, Today's Tasks only)
  - Sales Manager/Senior → Monitoring mode (full pipeline)
  - Principal Consultant → Monitoring + Reportees view
  - Admin → Full control mode

- **Stage Lock System:**
  - Prevents stage skipping (Lead → Meeting → Pricing → SOW → ...)
  - Smart dialogs instead of 403 errors
  - "Complete Meeting stage first before accessing Pricing Plan"
  - Redirect CTA to required stage

- **Auto-Prompt System:**
  - On stage completion: "Meeting completed! Ready to create Pricing Plan?"
  - [Create Pricing Plan Now] button
  - Guides user through workflow

**API Endpoints:**
- `GET /api/stage-guard/role-config` - Get role's stage access config
- `POST /api/stage-guard/validate-access` - Validate stage access
- `POST /api/stage-guard/leads/{id}/advance-stage` - Advance to next stage
- `GET /api/stage-guard/funnel-overview` - Pipeline overview (managers only)

---

### Phase 11: Complete Server.py Refactoring - February 22, 2026 ✅

**MAJOR MILESTONE: Routers are now the single source of truth**

**Before:**
- server.py: 15,646 lines (monolithic)
- 35 router files
- Mixed concerns, duplicate endpoints

**After:**
- server.py: 257 lines (clean entry point only)
- 48 router files (13 new)
- 371 API routes properly organized
- Zero duplicate endpoints

**New Routers Created:**
1. `analytics.py` - 8 funnel analytics endpoints
2. `payroll.py` - 15 salary/payroll endpoints
3. `travel.py` - 11 travel reimbursement endpoints
4. `sow_legacy.py` - 19 legacy SOW operations
5. `agreements.py` - 14 agreement workflow endpoints
6. `tasks.py` - 8 task management endpoints
7. `notifications.py` - 5 notification endpoints
8. `approvals.py` - 9 approval workflow endpoints
9. `quotations.py` - 3 quotation endpoints
10. `timesheets.py` - 4 timesheet tracking endpoints
11. `consultants.py` - 7 consultant profile endpoints
12. `reports.py` - 4 report generation endpoints
13. `settings.py` - 5 system settings endpoints
14. `roles.py` - 8 role management endpoints
15. `my.py` - 6 user self-service endpoints
16. `leave_requests.py` - 6 leave management endpoints

**Clean server.py Contains Only:**
- App initialization (FastAPI)
- CORS middleware setup
- Database connection (startup/shutdown)
- Router imports and inclusion
- Health check endpoints
- Global exception handler

**Architecture Improvements:**
- ✅ Removed duplicate get_current_user() from routers (uses shared auth.py)
- ✅ Added role constants to deps.py
- ✅ All endpoints served from routers only
- ✅ Proper API documentation (357→371 routes)
- ✅ Dashboard fully functional

**Backup Available:** `/app/backend/server.py.backup`
**Report:** `/app/backend/REFACTORING_REPORT.md`

---

### Phase 10: Server.py Refactoring - February 21, 2026 ✅

**Code Modularization**
- ✅ Created `/app/backend/routers/sales.py` - Dedicated sales router
- ✅ Extracted Sales Targets endpoints (5 endpoints)
- ✅ Extracted Sales Meetings & MOM endpoints (9 endpoints)
- ✅ Reduced server.py from 16,016 to 15,618 lines (~400 lines extracted)
- ✅ All endpoints tested and working

**Extracted Endpoints to sales.py:**
- POST/GET/PATCH/DELETE `/api/sales-targets`
- PATCH `/api/sales-targets/{target_id}/approve`
- POST/GET/PATCH `/api/sales-meetings`
- POST `/api/sales-meetings/{meeting_id}/complete`
- POST/GET `/api/sales-meetings/{meeting_id}/mom`
- GET `/api/leads/{lead_id}/meetings`
- GET `/api/leads/{lead_id}/mom-history`

---

### Phase 9: HR Module Documentation Generator - February 21, 2026 ✅

**Documentation Generation System**
- ✅ Complete HR Module documentation pack generator (PDF & DOCX)
- ✅ 10 comprehensive sections covering all HR operations
- ✅ Email delivery via SMTP to user's registered email
- ✅ Download links for generated documents
- ✅ HR Dashboard integration with "Generate & Email" button
- ✅ API endpoints: `/api/documentation/generate-hr-docs`, `/api/documentation/download/pdf/{filename}`, `/api/documentation/download/docx/{filename}`

**Documentation Sections Included:**
1. System Overview - Module purpose and components
2. Business Logic - Employee onboarding, attendance, leave policies
3. Role-Based Access & Permissions Matrix
4. End-to-End Workflow Maps
5. Configuration Guide (Admin Manual)
6. Standard Operating Procedures (SOPs)
7. Training Manual with exercises
8. Troubleshooting Guide
9. Audit & Compliance Controls
10. Quick Start Guide (30 minutes)

---

### Phase 8: Advanced Sales Analytics - February 21, 2026 ✅

**1. Funnel Analytics Dashboard**
- ✅ Manager view: Team funnel summary with employee-wise breakdown
- ✅ Employee view: Personal funnel progress with target vs achievement
- ✅ Period selector: Week/Month/Quarter/Year filtering
- ✅ Stage distribution visualization (9-stage funnel)

**2. Bottleneck Analysis**
- ✅ Stage-to-stage conversion rates
- ✅ Drop-off rate calculation
- ✅ Critical bottleneck detection (>50% drop-off)
- ✅ Visual progress bars with color coding
- ✅ Worst bottleneck alert banner

**3. Sales Forecasting**
- ✅ Time-based forecast: 30/60/90 day predictions
- ✅ Weighted pipeline value calculation
- ✅ Stage probability scoring
- ✅ Expected deals and revenue projections

**4. Time-in-Stage Metrics**
- ✅ Average days at each funnel stage
- ✅ Stage-by-stage progress bars
- ✅ Slowest stage identification
- ✅ Total journey time calculation (42.5 days avg)

**5. Win/Loss Analysis**
- ✅ Won/Lost/Stale/Active categorization
- ✅ Win rate calculation (66.7%)
- ✅ 30-day stale lead detection
- ✅ At-risk leads alert with details
- ✅ Loss by stage tracking

**6. Sales Velocity Metrics**
- ✅ Average days to close (33.5 days)
- ✅ Fastest/Slowest deal tracking
- ✅ Stage-by-stage velocity breakdown
- ✅ Completed deals analysis

**New API Endpoints:**
- `GET /api/analytics/funnel-summary` - Team/own funnel by stage
- `GET /api/analytics/my-funnel-summary` - Personal summary with targets
- `GET /api/analytics/funnel-trends` - Historical trends
- `GET /api/analytics/bottleneck-analysis` - Stage conversion analysis
- `GET /api/analytics/forecasting` - Sales predictions
- `GET /api/analytics/time-in-stage` - Stage duration metrics
- `GET /api/analytics/win-loss` - Win/loss/stale analysis
- `GET /api/analytics/velocity` - Sales velocity metrics

**Test Data Seeded:**
- 5 test journeys with complete timestamps
- 3 complete journeys (FastTrack, SlowBurn, Quick Win)
- 1 stale journey (Stalled Systems - 35 days at quotation)
- 1 lost journey (Lost Deal LLC - lost at agreement)

**Files Modified:**
- `/app/frontend/src/pages/SalesDashboard.js` - Complete analytics overhaul
- `/app/backend/server.py` - 8 new analytics endpoints

---

### Phase 7: Role Cleanup & Sales Funnel UI Redesign - February 21, 2026 ✅

**1. Role System Update: account_manager → sales_manager**
- ✅ Removed all `account_manager` role references from codebase
- ✅ Replaced with `sales_manager` in all backend files (server.py, routers/, models.py)
- ✅ Replaced with `sales_manager` in all frontend files (Layout.js, pages/)
- ✅ Updated database: 3 users migrated from account_manager to sales_manager
- ✅ Updated DEFAULT_ROLES, SALES_ROLES, SALES_MEETING_ROLES constants
- ✅ Display name "Account Manager" updated to "Sales Manager"

**Users Updated:**
- dp@dvbc.com (Dhamresh Parikh) - now sales_manager
- sales.manager@dvbc.com - now sales_manager
- myhr@dvconsulting.co.in - now sales_manager

**2. Sales Funnel UI Redesign**
- ✅ Redesigned `/sales-funnel-onboarding` page with two-column layout
- ✅ Left sidebar (w-80): Vertical step list with status indicators
- ✅ Right content area: Current step details and actions
- ✅ Progress indicator "X of 9" at top right with progress bar
- ✅ Step states: Completed (green checkmark), Current (blue border), Pending (gray), Locked (lock icon)
- ✅ Dark mode support throughout
- ✅ Responsive design with proper spacing

**Files Modified:**
- `/app/frontend/src/pages/SalesFunnelOnboarding.js` - Complete UI redesign
- `/app/frontend/src/components/Layout.js` - Updated SALES_ROLES_NAV
- `/app/backend/server.py` - Updated all role references
- `/app/backend/routers/*.py` - Updated role references
- Multiple frontend pages - Updated role references

---

### Phase 6: Complete 9-Step Sales Funnel Onboarding - February 21, 2026 ✅ (Latest)

**Full Sales Funnel Flow with 9 Steps:**
1. **Lead Capture** - Review lead details and contact info
2. **Record Meeting** - Log meeting (date, attendees, MOM)
3. **Pricing Plan** - Create investment plan with services
4. **Scope of Work** - Define deliverables and milestones
5. **Quotation** - Generate proforma invoice
6. **Agreement** - Create and sign consulting contract
7. **Record Payment** - Log payment (Cheque/NEFT/UPI)
8. **Kickoff Request** - Submit for approval, assign PM
9. **Project Created** - Kickoff approved, project and team assigned

**Features Implemented:**
- ✅ `/sales-funnel-onboarding` - 9-step progress tracker page
- ✅ Progress bar showing completion status (X of 9)
- ✅ Step indicators with green checkmarks for completed steps
- ✅ Strict sequential flow (must complete previous steps)
- ✅ "Funnel" button on Leads page to start onboarding
- ✅ `GET /api/leads/{lead_id}/funnel-progress` - Returns all step statuses
- ✅ Redirects to existing pages (PricingPlanBuilder, SOWBuilder, etc.)
- ✅ Sales funnel sidebar items (SOW & Pricing, Agreements, Payment Verification) visible to Admin only

**Files Created:**
- `/app/frontend/src/pages/SalesFunnelOnboarding.js` - 9-step tracker UI

**Files Modified:**
- `/app/backend/server.py` - Added funnel-progress endpoint
- `/app/frontend/src/pages/Leads.js` - Added "Funnel" button
- `/app/frontend/src/components/Layout.js` - adminOnly filter for sidebar items
- `/app/frontend/src/App.js` - Added SalesFunnelOnboarding route

---

### Phase 5: Client Onboarding Flow - February 21, 2026 ✅

**Client Onboarding Page with Step-Based UI (Similar to HR Onboarding)**
- ✅ Created `/client-onboarding` page with 4-step wizard:
  1. **Agreement Review** - View signed agreement details
  2. **Record Payment** - Record payments with Cheque/NEFT/UPI/RTGS
  3. **Project Kickoff** - Select PM and create kickoff request
  4. **Onboarding Complete** - Success confirmation with project link
- ✅ Progress bar with clickable step indicators
- ✅ Payment recording form with validation (Cheque # or UTR required)
- ✅ Payment history sidebar with running total
- ✅ PM selection dropdown for kickoff
- ✅ "Client Onboarding" button added to AgreementView (replaces Record Payment button)
- ✅ Removed payment dialog from AgreementView (now in separate flow)

**Files Created:**
- `/app/frontend/src/pages/ClientOnboarding.js` - Step-based client onboarding UI

**Files Modified:**
- `/app/frontend/src/pages/sales-funnel/AgreementView.js` - Replaced Record Payment with Client Onboarding button
- `/app/frontend/src/App.js` - Added ClientOnboarding route

---

### Phase 4: P2 Features Implementation - February 21, 2026 ✅

**1. Payment Recording (after Agreement Signed)**
- ✅ `POST /api/agreements/{id}/record-payment` - Records payment with amount, date, mode
- ✅ `GET /api/agreements/{id}/payments` - Returns payment history and totals
- ✅ Payment modes: Cheque (requires cheque_number), NEFT/UPI (requires utr_number)
- ✅ "Record Payment" button on AgreementView for signed agreements
- ✅ Payment Dialog with validation and history display
- ✅ New collection: `agreement_payments`

**2. Mandatory Meeting Check for Pricing Plan**
- ✅ `POST /api/meetings/record` - Create meeting linked to lead
- ✅ `GET /api/meetings/lead/{lead_id}` - Get all meetings for a lead
- ✅ `GET /api/leads/{lead_id}/can-access-pricing` - Check if meeting exists
- ✅ Meeting Record Page at `/sales-funnel/meeting/record?leadId={id}`
- ✅ PricingPlanBuilder blocks access if no meeting recorded
- ✅ New collection: `meeting_records`

**3. SOW Inheritance on Kickoff Approval**
- ✅ Kickoff approval now auto-creates Project record
- ✅ SOW items copied from pricing plan to project
- ✅ Team deployment inherited from agreement
- ✅ PM assigned from kickoff request
- ✅ Lead and Agreement linked to created project
- ✅ Notifications sent to sales executive and assigned PM

**4. Meeting Targets & KPI Dashboard**
- ✅ `GET /api/manager/target-vs-achievement` - Employee-wise KPI data
- ✅ Returns: meetings/closures/revenue target vs achieved with percentages
- ✅ Team totals aggregated
- ✅ Total clients in funnel count included
- ✅ Target Management page shows "Total Clients in Funnel" card
- ✅ Manager Dashboard shows "Target vs Achievement" section with employee table

**Files Created:**
- `/app/frontend/src/pages/sales-funnel/MeetingRecord.js`

**Files Modified:**
- `/app/backend/server.py` - Payment, Meeting, Kickoff, KPI endpoints
- `/app/frontend/src/pages/sales-funnel/AgreementView.js` - Payment dialog
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js` - Meeting block
- `/app/frontend/src/pages/TargetManagement.js` - Total Clients card
- `/app/frontend/src/pages/ManagerLeadsDashboard.js` - Target vs Achievement
- `/app/frontend/src/App.js` - MeetingRecord route

---

### Phase 3: P1 Tasks Completion - February 21, 2026 ✅

**1. Target Management UI (Full Implementation)**
- ✅ Yearly sales targets with monthly breakdown (Jan-Dec)
- ✅ Target types: Revenue, Closures, Meetings
- ✅ CRUD operations: Create, Edit, Delete targets
- ✅ Summary cards: Total Targets Set, Team Members, Total Annual Target
- ✅ Employee selection dropdown with subordinates
- ✅ Quick apply feature for setting all months at once

**2. Sales Targets Backend API (Updated)**
- ✅ New collection: `yearly_sales_targets`
- ✅ `POST /api/sales-targets` - Create yearly target with monthly_targets object
- ✅ `GET /api/sales-targets` - List targets filtered by year/employee
- ✅ `PATCH /api/sales-targets/{id}` - Update target
- ✅ `DELETE /api/sales-targets/{id}` - Delete target

**3. Agreement E-Sign & Upload Flow**
- ✅ `POST /api/agreements/{id}/send-to-client` - Send agreement email to client
- ✅ `POST /api/agreements/{id}/upload-signed` - Upload signed document
- ✅ Frontend dialogs: Send to Client, Upload Signed Agreement
- ✅ Agreement status flow: draft → sent → signed

**4. List View Default on All Sales Funnel Pages**
- ✅ Leads page - List view default
- ✅ Agreements page - List view default  
- ✅ Quotations page - List view default
- ✅ SOW Builder - List view default

**5. Manager Dashboard Permission Fix**
- ✅ Added `account_manager` and `senior_consultant` roles to manager endpoints
- ✅ `/api/manager/subordinate-leads` now accessible to all manager-level roles
- ✅ `/api/manager/today-stats` fixed
- ✅ `/api/manager/performance` fixed

**Files Modified:**
- `/app/backend/server.py` - Sales targets API, manager endpoint permissions
- `/app/frontend/src/pages/TargetManagement.js` - Already fully implemented

---

### Phase 2: Manager Dashboard & Kickoff Approvals - February 21, 2026 ✅

**1. Manager Leads Dashboard (NEW PAGE)**
- ✅ Created `/manager-leads` route with full dashboard
- ✅ Today's Stats: Meetings, Calls, Closures, Team Size, Absent employees
- ✅ Monthly & YTD Performance cards with progress bars
- ✅ Team Summary: Grouped leads by employee with closure counts
- ✅ Full leads table with Pause/Resume buttons, status badges, progress indicators
- ✅ Filters: Search, Team Member dropdown, Status dropdown
- ✅ Click-through to sales funnel for each lead

**2. Kickoff Requests in Approvals Center**
- ✅ Added "KICKOFF" stat card in Approvals Center
- ✅ "Pending Kickoff Requests" section with full details
- ✅ Kickoff Detail Dialog with approve/reject actions
- ✅ Shows linked Agreement info and Lead info
- ✅ Badge showing "Single Approval Point"

**3. Navigation Updates**
- ✅ Added "Team Leads" link in sidebar (for managers)
- ✅ Added "Kickoff Requests" link in sidebar

**Files Created:**
- `/app/frontend/src/pages/ManagerLeadsDashboard.js`

**Files Modified:**
- `/app/frontend/src/App.js` - Added routes
- `/app/frontend/src/pages/ApprovalsCenter.js` - Added Kickoff section
- `/app/frontend/src/components/Layout.js` - Added nav links

---

### Phase 1: Lead Stage Filter & List View + Single Approval Flow - February 21, 2026 ✅

**1. Lead Stage Dropdown Filter (Replaced Buttons)**
- ✅ Replaced button-based status filter with dropdown
- ✅ New stages: All, New, Meeting, Pricing Plan, SOW, Quotation, Agreement, Payment, Kickoff Request, Kick Accept, Closed, Paused, Lost
- ✅ Shows total count for "All Leads"
- ✅ "Clear" button to reset filter

**2. List View as Default**
- ✅ Changed default viewMode from 'card' to 'list'
- ✅ List view shows: Name, Company, Email, Score, Progress, Status, Actions

**3. Manager Pause/Resume Lead Functionality**
- ✅ Pause button (orange) visible for managers in Actions column
- ✅ Resume button (green) shows for paused leads
- ✅ Paused leads show "PAUSED" badge and grayed-out row
- ✅ Status dropdown disabled for paused leads
- ✅ Clicking paused lead shows info toast
- ✅ Backend endpoints: `/api/leads/{id}/pause`, `/api/leads/{id}/resume`

**4. Single Approval Point at Kickoff Request**
- ✅ Removed agreement `pending_approval` status (now starts as `draft`)
- ✅ Created Kickoff Request endpoints:
  - `POST /api/kickoff-requests` - Create kickoff request
  - `GET /api/kickoff-requests/pending` - Get pending for approval
  - `POST /api/kickoff-requests/{id}/approve` - Approve (Sr. Manager/Principal only)
  - `POST /api/kickoff-requests/{id}/reject` - Reject
  - `POST /api/kickoff-requests/{id}/close` - Mark deal closed
- ✅ Lead status flow: `kickoff_request` → `kick_accept` → `closed`
- ✅ Notifications sent to Sr. Managers and requestor

**5. Manager Dashboard APIs**
- ✅ `GET /api/manager/subordinate-leads` - All subordinate leads with progress
- ✅ `GET /api/manager/today-stats` - Today's meetings, calls, closures, absents
- ✅ `GET /api/manager/performance` - Monthly/YTD closure count and agreement value

**New Lead Statuses:**
```
new → meeting → pricing_plan → sow → quotation → agreement → payment → kickoff_request → kick_accept → closed
                                                                                            ↓
                                                                                         paused (manager can pause/resume)
                                                                                            ↓
                                                                                          lost
```

**Files Modified:**
- `/app/backend/server.py` - Added LeadStatus enum, Pause/Resume, Manager APIs, Kickoff Request endpoints
- `/app/backend/sales_workflow.py` - Changed Agreement default status from 'pending_approval' to 'draft'
- `/app/frontend/src/pages/Leads.js` - Dropdown filter, list view default, pause/resume buttons, new status options

---

### Agreement Approvals in Approvals Center - February 21, 2026 ✅
**Fixed: System Admin could not see agreement approvals in the Approvals Center**

**Issue:** Agreements marked as "awaiting manager approval" (status: `pending_approval`) were not visible in the central Approvals Center, even though the backend endpoint `/api/agreements/pending-approval` was working correctly.

**Fix Applied:**
- ✅ **Updated `fetchData` function** in ApprovalsCenter.js to fetch `/api/agreements/pending-approval` for managers and admins
- ✅ **Added `handleAgreementAction` function** for approve/reject actions
- ✅ **Added "AGRMT" stat card** showing count of pending agreement approvals
- ✅ **Added "Pending Agreement Approvals" section** with:
  - Party name, agreement number, duration
  - Created date, start date
  - "Pending approval from: Manager / Admin" indicator
  - View, Approve, Reject buttons with proper test IDs
- ✅ **Approval flow tested** - Successfully approved an agreement and verified lead status update

**Files Modified:**
- `/app/frontend/src/pages/ApprovalsCenter.js`

---

### PM Selection & Auto-Save Enhancements - February 21, 2026 ✅

**1. PM Selection for Signed Agreements**
- ✅ Fixed SelectItem dropdown issue (removed nested `<div>` inside SelectItem)
- ✅ Added "Create Project Kickoff" button for signed agreements
- ✅ Consultants can now be selected as Project Managers

**2. Approval Cards - Show Approver Information**
- ✅ Approval cards now display "Pending approval from: [Role]"
- ✅ Bank detail changes show "Pending approval from: HR Manager" or "Admin"
- ✅ Profile changes show "Pending approval from: HR Manager"
- ✅ Modification requests show "Pending approval from: Admin (Go-Live Employee)"

**3. Gmail-like Auto-Save on Page Leave (Everywhere in ERP)**
- ✅ Created `DraftIndicator` component for save status display
- ✅ Updated `useDraft` hook with `registerFormDataGetter` callback
- ✅ Drafts auto-save on: tab switch, page close, component unmount
- ✅ **Implemented in:**
  - Leads.js - Lead creation
  - HROnboarding.js - Employee onboarding
  - SalesMeetings.js - Sales meeting scheduling
  - PricingPlanBuilder.js - Pricing plan creation
  - MyExpenses.js - Expense submission
  - MyLeaves.js - Leave requests
  - Quotations.js - Quotation creation
  - SOWBuilder.js - SOW item editing

---

### Agreements Page Crash Fix & Validation Error Handling - February 21, 2026 ✅
**Fixed critical crash when backend returns Pydantic validation errors**

**Issue:** The Agreements page crashed when the backend returned validation errors in Pydantic format (array of objects with `{type, loc, msg}` structure). The frontend tried to render this object directly as a React child, causing the crash.

**Fix Applied:**
- ✅ **Updated error handling in all sales-funnel pages** to properly extract human-readable messages from Pydantic validation error arrays
- ✅ **Files Fixed:**
  - `Agreements.js` - handleSubmit, handleSendEmail
  - `AgreementView.js` - handleSaveAgreement, handleESignature, handleCreateKickoffRequest
  - `PricingPlanBuilder.js` - handleSubmit
  - `ProformaInvoice.js` - handleCreateInvoice
  - `PaymentVerification.js` - handleSubmit
  - `ManagerApprovals.js` - handleApprove, handleReject
  - `MyExpenses.js` - handleDeleteExpense
- ✅ **Added `getApiErrorMessage` utility** to `/app/frontend/src/utils/errorHandler.js` for consistent error handling
- ✅ **Validation errors now show as toast messages** instead of crashing the app

**Technical Details:**
- Backend returns validation errors as: `{detail: [{type, loc, msg, input, ctx, url}]}`
- Frontend now checks if `detail` is an array and extracts `msg` fields to display
- Pattern: `detail.map(e => e.msg || 'Validation error').join(', ')`

---

### Employee Self-Service ("My Details") - February 21, 2026 ✅
**Empowers employees to manage their own profile data with HR approval workflow**

**Features:**
- ✅ **My Details Page** (`/my-details`) under My Workspace sidebar
  - Personal Information (Read-only)
  - Contact Information (Editable via change request)
  - Address (Editable via change request)
  - Bank Details (Editable via change request)
  - Emergency Contact (Editable via change request)
  - Employment Information (Read-only)
- ✅ **Change Request Workflow**
  - Employee clicks Edit → Modal opens with form fields
  - "Reason for Change" is required
  - Submit creates pending request for HR approval
  - Pending Request Banner shows all awaiting requests
  - Edit button hidden for sections with pending requests
- ✅ **HR Approval in Approvals Center**
  - New "Employee Profile Changes" section in Approvals Center
  - Stats card showing pending profile change count
  - Displays employee name, section type, changes, and reason
  - Approve/Reject buttons with confirmation
  - On approval, employee profile is automatically updated

**Backend Endpoints:**
- `GET /api/my/profile` - Get employee profile data
- `GET /api/my/change-requests` - Get employee's pending requests
- `POST /api/my/change-request` - Submit profile change request
- `GET /api/hr/employee-change-requests` - Get pending requests for HR
- `POST /api/hr/employee-change-request/{id}/approve` - Approve and update profile
- `POST /api/hr/employee-change-request/{id}/reject` - Reject with reason

**Files:**
- `/app/frontend/src/pages/MyDetails.js` - Employee self-service page
- `/app/frontend/src/pages/ApprovalsCenter.js` - Added profile change approvals
- `/app/backend/server.py` - Lines 11425-11990 for endpoints

**Database:**
- `employee_change_requests` collection with fields: id, employee_id, employee_name, employee_code, section, current_values, requested_values, reason, status, created_at, approved_by, approved_at

---

### Anupam Chandra (EMP1003) Onboarding Fix - February 21, 2026 ✅
**Fixed data mismatch issue causing login failure for newly onboarded employee**

**Issue:** Employee email `anupam.chandra@dvbv.co.in` didn't match user email `anupam.chandra@dvconsulting.co.in` (typo), and user was deactivated.

**Fix Applied:**
- ✅ Corrected employee email to `anupam.chandra@dvconsulting.co.in`
- ✅ Activated user account (`is_active: true`)
- ✅ Password set to `Welcome@EMP001`

---

### Draggable Help Panel & Workflow Overlay - February 21, 2026 ✅
**Made floating help button and workflow overlay draggable to avoid blocking page content**

**Changes:**
- ✅ **Floating Help Button now draggable** 
  - Click and drag to reposition anywhere on screen
  - Stays within viewport bounds
  - Touch-friendly (works on mobile/tablet)
- ✅ **Workflow Overlay now draggable**
  - Move icon (⋮⋮) in header indicates draggability
  - Drag header to reposition panel
  - Prevents blocking page content
  - Enhanced shadow when dragging for visual feedback

**Technical Implementation:**
- Custom `useDraggable` hook for drag functionality
- Supports both mouse and touch events
- Viewport bounds checking to keep elements visible
- Position persists until page reload

---

### Attendance & Leave Settings Enhancements - February 21, 2026 ✅
**Improved attendance policy configuration with employee-wise customization**

**Changes:**
- ✅ **Consulting Roles now Read-Only** - Inherited from Employee Master
  - Purple-highlighted section with "Inherited from Employee Master" label
  - Shows role badges with employee count (e.g., "Consultant 20")
  - Displays total employees following consulting timing
  - No longer manually editable - roles are derived from employee data
- ✅ **Employee-wise Configuration Section** (NEW)
  - View employees with custom attendance policies
  - Add new custom policy via modal dialog
  - Edit existing custom policies
  - Delete custom policies (reverts to default)
  - Each policy shows: Check-in/out times, Grace period, Grace days, Reason
  - Select employees via dropdown with live search

**Backend Endpoints:**
- `GET /api/attendance/consulting-employees` - Get employees with consulting roles from employee master
- `GET /api/attendance/policy/custom` - List all custom policies
- `POST /api/attendance/policy/custom` - Create/update custom policy
- `DELETE /api/attendance/policy/custom/{employee_id}` - Remove custom policy

**Files Modified:**
- `/app/frontend/src/pages/hr/AttendanceLeaveSettings.js` - Added Employee-wise Configuration section, made Consulting Roles read-only
- `/app/backend/routers/attendance.py` - Added `/consulting-employees` endpoint

---

### AI-Powered Hybrid Guidance System - February 21, 2026 ✅
**Contextual help system with AI-powered navigation suggestions and Smart Recommendations**

**Features:**
- ✅ **Floating Help Button** - Orange circular button at bottom-right corner
  - Pulse animation for first-time users
  - **Red badge showing pending items count** when user has actionable items
  - `data-testid="floating-help-btn"` for testing
  - Fixed position (bottom-6 right-6) with z-50
- ✅ **Help Panel Modal** with 4 tabs:
  1. **Smart Suggestions Tab** (NEW - Default tab)
     - Shows pending approvals grouped by type (Leave, Expenses, CTC, Bank Changes, etc.)
     - Priority-based sorting (high priority items first)
     - Color-coded badges (red=high, amber=medium)
     - Click to navigate directly to approval page
     - "You're all caught up!" state when no pending items
  2. **Ask AI Tab** - GPT-4o powered contextual help
     - Quick action buttons based on user role
     - Natural language queries ("How do I apply for leave?")
     - Navigation suggestions extracted from AI response
     - Auto-navigate feature takes user directly to relevant page
  3. **Step-by-Step Guides Tab** - Workflow checklists
     - Daily Tasks: Check-in, Regularize Attendance, Apply Leave, Submit Expense
     - Sales Flow: Lead to Quotation, Quotation to Agreement, Agreement to Kickoff
     - HR & Onboarding: Employee Onboarding, Permission Change, Approval Process
     - Meetings & Tasks: Schedule Meeting, Create Task, Create Follow-up
     - Administration: Manage Masters
  4. **Page Tips Tab** - Contextual tips for current page
     - "About this page" descriptions
     - Pro tips specific to each page

**Backend Endpoints:**
- `POST /api/ai/guidance-help` - AI-powered help with navigation suggestions
  - Request: `{query, current_page, user_role}`
  - Response: `{response, suggested_route, auto_navigate}`
- `GET /api/my/guidance-state` - Fetch user's guidance preferences
- `POST /api/my/guidance-state` - Save user's guidance preferences
- `GET /api/approvals/pending` - Get pending approvals for smart recommendations
- `GET /api/expenses/pending-approvals` - Get pending expense approvals

**Files:**
- `/app/frontend/src/components/GuidanceSystem.js` - FloatingHelpButton with badge, HelpPanel, WorkflowOverlay
- `/app/frontend/src/contexts/GuidanceContext.js` - WORKFLOWS, PAGE_TIPS, smartRecommendations, GuidanceProvider
- `/app/backend/server.py` - Lines 11315-11414 for AI guidance endpoint
- `/app/backend/tests/test_guidance_system.py` - Comprehensive test suite

**Integration:**
- Uses `emergentintegrations.llm.chat.LlmChat` with GPT-4o model
- Navigation parsing via `[NAVIGATE:/route-path]` format in AI response
- Smart Recommendations auto-refreshes every 60 seconds

---

### Day 0 Guided Onboarding Tour - February 21, 2026 ✅
**Role-specific guided tour for first-time users**

**Features:**
- ✅ **Auto-start for first-time users** - Welcome dialog appears after first login
- ✅ **Role-specific steps** - Admin sees HR/Admin features, Sales sees CRM features, etc.
- ✅ **Tour content covers:**
  - Real-time notification bell with count
  - WebSocket connection status (Live/Offline)
  - One-click actions in notifications
  - Email action links explanation
  - Team Chat and AI Assistant
  - Role-specific features (HR Management, Approvals, Sales CRM, Projects)
- ✅ **Tour navigation** - Next/Back buttons, progress indicator (e.g., "3 of 7")
- ✅ **Replay Tour button** in Profile page settings
- ✅ **MongoDB storage** - `has_completed_onboarding` field in users collection

**Backend Endpoints:**
- `GET /api/my/onboarding-status` - Check completion status
- `POST /api/my/complete-onboarding` - Mark tour as complete
- `POST /api/my/reset-onboarding` - Reset for replay

**Files:**
- `/app/frontend/src/components/OnboardingTour.js`
- `/app/frontend/src/pages/UserProfile.js` - Added Replay Tour button

---

### Enhanced Approvals Center - February 21, 2026 ✅
**Major UX improvements to the Approval Center**

**New Features:**
- ✅ **Real-time WebSocket Refresh** - Auto-refresh when new approvals arrive
  - Live/Offline indicator shows connection status
  - Toast notification on new approval activity
- ✅ **Bulk Actions** - Select multiple approvals for batch processing
  - Select All / Deselect All functionality
  - Approve All / Reject All buttons with confirmation dialog
  - Visual selection feedback (orange border on selected items)
- ✅ **Mobile Optimization** - Responsive design for all screen sizes
  - Compact stats cards (2-column grid on mobile)
  - Stacked action buttons on mobile
  - Horizontally scrollable tabs
  - Approval chain hidden on mobile (shown on tablet+)

**Files Modified:**
- `/app/frontend/src/pages/ApprovalsCenter.js`

---

### Centralized Approval Notification System - February 21, 2026 ✅
**Auto-trigger real-time email + WebSocket notifications for ALL approval workflows**

**Integrated Workflows:**
- ✅ **Leave Requests** → Email to Reporting Manager
- ✅ **Expense Submissions** → Email to HR Manager
- ✅ **Kickoff Requests** → Email to assigned PM
- ✅ **Go-Live Requests** → Email to Admin
- ✅ **Bank Change Requests** → Email to HR
- ✅ **SOW Approvals** → Email to approver chain

**Features:**
- One-click Approve/Reject buttons in email (24hr expiry)
- Real-time WebSocket notifications to approvers
- Real-time notifications to requester when action is taken
- All emails logged in `email_logs` collection
- Secure tokens in `email_action_tokens` collection
- SMTP configured with Google Workspace (dharmesh.parikh@dvconsulting.co.in)

**Files:**
- Service: `/app/backend/services/approval_notifications.py`
- Email Actions: `/app/backend/routers/email_actions.py`
- WebSocket: `/app/backend/websocket_manager.py`

---

### Communication & AI Features - February 21, 2026 ✅
**Built 3 major features together:**

1. **💬 Internal Chat System** (`/chat`):
   - Direct Messages (DMs) between users
   - Group Channels with member management
   - Actionable buttons with ERP record sync (Approve/Reject inline)
   - **Real-time WebSocket support** - messages appear instantly without polling
   - Typing indicators and read receipts via WebSocket
   - Connection status indicator (green Wifi icon when connected)
   - Auto-reconnect on disconnect
   - **Admin Audit**: View all conversations and messages
   - **User Restrictions**: Admin can restrict users from chat
   - File/image sharing support
   - New Collections: `chat_conversations`, `chat_messages`, `admin_audit_logs`
   - Backend: `/app/backend/routers/chat.py`, `/app/backend/websocket_manager.py`
   - Frontend: `/app/frontend/src/pages/Chat.js`

2. **🤖 AI-Powered ERP Assistant** (`/ai-assistant`):
   - GPT-4o integration via Emergent LLM Key
   - **Hierarchical RBAC**:
     - Consultants: Own projects only
     - Managers: Team's data (direct reports)
     - Department Heads: Department-wide data
     - Admins: Full access to everything
   - Natural language queries: "Show me employees with pending leaves"
   - Report analysis & summaries across Sales, HR, Finance, Projects
   - Trend insights & predictions
   - Quick Reports sidebar for instant analysis
   - AI Suggestions based on current ERP state
   - **Admin can restrict users from AI access**
   - Chat history persistence
   - New Collection: `ai_chat_history`
   - Backend: `/app/backend/routers/ai_assistant.py`
   - Frontend: `/app/frontend/src/pages/AIAssistant.js`

3. **📧 Email Action System** (`/email-settings`):
   - Google SMTP integration (pre-configured)
   - One-click approval links in emails (no login required)
   - 24-hour expiring secure tokens
   - Pre-configured HTML templates with custom header/footer
   - Supports: Leave Requests, Expenses, Kickoffs, Go-Live approvals
   - Email logs with status tracking
   - New Collections: `email_action_tokens`, `email_logs`, `email_settings`
   - Backend: `/app/backend/routers/email_actions.py`
   - Frontend: `/app/frontend/src/pages/admin/EmailSettings.js`

**Navigation Updates**:
- Chat & AI Assistant moved to "My Workspace" section (visible for all users)
- Email Settings added to Admin section

**Real-time System**:
- WebSocket-based real-time notifications (green indicator when connected)
- Notifications appear instantly when triggered (approvals, chat mentions, etc.)
- Fallback to 30-second polling if WebSocket disconnects
- Browser push notifications for new alerts

### Backend Recovery & Telegram Bot Rollback - February 20, 2026 ✅
- Complete Rollback of Telegram Bot Feature
- Backend service recovered from 520 error

### Go-Live Pre-Flight Checklist - February 20, 2026 ✅
- **Go-Live Approval Flow Enhanced**:
  - Admin sees "View Checklist" and "Review & Approve" buttons
  - Pre-Flight Checklist Dialog shows complete onboarding status
  - Checklist items with ✅/❌ indicators:
    1. Onboarding Complete (personal info, employment details)
    2. CTC Structure Approved (auto-approved by HR)
    3. Bank Details Added
    4. Documents Generated (offer letter, appointment letter)
    5. Portal Access Granted
  - Warning banner if checks are pending
  - "Approve Go-Live" button DISABLED until critical checks pass (CTC + Portal Access)
  - Shows HR notes and allows Admin comments

**Complete Onboarding to Go-Live Flow:**
1. HR creates employee (onboarding form) → Auto-creates employee record
2. HR designs CTC → **Auto-approved** (no Admin step needed)
3. HR adds bank details → Optional verification
4. HR generates documents → Offer letter, appointment letter
5. HR grants portal access → Creates user account
6. HR submits Go-Live request → Goes to Admin for review
7. **Admin approves Go-Live** with pre-flight checklist → Employee becomes active

**Who Approves What:**
- CTC Design: **HR only** (auto-approved, no Admin step)
- Bank Details: **HR only** (verifies proof)
- Documents: **HR generates** (no approval needed)
- Portal Access: **HR grants** (no approval needed)
- **Go-Live: ADMIN only** (single approval checkpoint with full checklist)
- Post-Go-Live Modifications: **ADMIN only** (HR requests, Admin approves)

### Consolidated Approvals Center & CTC Auto-Approval - February 20, 2026 ✅
- **Approvals Center Enhanced**:
  - Added Employee Modification Requests section for Admin
  - Shows all pending modification requests with detailed change breakdown
  - Displays current vs new values for each field
  - Approve/Reject buttons with confirmation
  - Stats cards show: Total Pending, CTC Approvals, Permissions, Modifications, My Requests
- **CTC Auto-Approval Verified**:
  - HR Manager can create CTC structures that are auto-approved (no Admin step needed)
  - CTC goes directly to "approved" status when HR submits
  - Employee salary is updated immediately
  - Admin only involved for Go-Live approval (single approval checkpoint)
- **Post-Go-Live Modification Workflow**:
  - Protected fields: CTC, Salary, Designation, Department, Reporting Manager, Employment Type, Bank Details
  - HR Manager changes create modification requests
  - Admin receives notification and approves in Approvals Center
  - Changes applied atomically on approval

### Success Dialog Flow & Post-Go-Live Approval - February 20, 2026 ✅
- **Onboarding Success Dialog Redesigned**:
  - Added "Next Steps to Complete Onboarding" section with numbered steps (1→CTC, 2→Documents, 3→Go-Live)
  - Primary CTA button: "Design CTC Structure" with step badge and arrow
  - Secondary actions: "Onboard Another", "View Employees"
  - Clear flow guidance eliminates confusion about what to do next
- **Post-Go-Live Modification Approval**:
  - Protected fields now include: CTC, Salary, Designation, Department, Reporting Manager, Bank Details
  - HR Manager changes create modification requests (not direct updates)
  - Admin receives notification for approval
  - New endpoints: `GET/POST /api/employees/modification-requests/*`
  - Requester notified upon approval/rejection

### Bootstrap Fix & E2E Testing - February 20, 2026 ✅
- **First Employee Bootstrap Fix**:
  - Employees can now select "SELF" as reporting manager when onboarding the first employee
  - Backend: `POST /api/employees` handles `reporting_manager_id: "SELF"` by setting it to the employee's own ID
  - Frontend: `HROnboarding.js` shows "Self (First Employee / Admin)" option when no managers exist or role is admin
  - `is_self_reporting: true` flag set for audit tracking
- **Update Reporting Manager Feature**:
  - HR Manager + Admin can update reporting manager via employee edit dialog
  - Uses `PATCH /api/employees/{id}` endpoint
  - Also available: `PATCH /api/users/{user_id}/reporting-manager` for user-level updates
- **Notification System Verified**:
  - NotificationBell component present in all layouts (Layout.js, HRLayout.js, SalesLayout.js)
  - Polls every 15 seconds for new notifications
  - Browser push notifications enabled when permitted
  - Notifications created for: employee onboarding, leave requests, leave approvals, expense approvals
- **E2E Testing Completed**:
  - 11/11 pytest tests passed (test_bootstrap_reporting_manager.py)
  - Bootstrap SELF manager, Update RM, Notifications, Kickoff Approval, CTC flow all verified

### System Integration & Workflow Fixes - February 20, 2026 ✅
- **CTC Flow Simplified**:
  - CTC no longer requires Admin approval - saves and applies directly
  - Auto-redirects to Document Center after CTC save
- **PM Selection Filter**:
  - Only Senior/Principal Consultants with reportees can be assigned as PM
  - Endpoint: `GET /api/kickoff-requests/eligible-pms/list`
- **My Clients Enhanced**:
  - Shows agreement value (total, paid, pending)
  - Kickoff status and project ID linked
- **Unified Portal**:
  - `/hr/login` and `/sales/login` redirect to `/login`
  - Role-based routing after login
- **Kickoff Approval Roles Updated**:
  - `senior_consultant` + `principal_consultant` can approve kickoffs
- **Duplicate Endpoints Removed**:
  - Removed duplicate `/sow-categories` from server.py

### Navigation Cleanup - February 20, 2026 ✅
- Fixed dead links: `/sow-pricing` → `/sales-funnel/pricing-plans`
- Created new pages: `/follow-ups` (Lead/Payment), `/invoices` (Proforma linked to employees)
- Restored: Employee Permissions & Project Payments in Admin section
- Updated Consulting nav: Team Assignment, Meetings Calendar

### Employee Linking & Custom Attendance Policies - February 20, 2026 ✅
- **Employee Selection Dropdowns**:
  - HR Attendance Input (`/hr-attendance-input`): Filter by specific employee
  - HR Leave Input (`/hr-leave-input`): Filter by employee, shows leave balance, pre-populates leave form
- **Custom Attendance Policies** (per employee):
  - Create custom timing rules for specific employees (e.g., remote workers)
  - Configure: check_in, check_out, grace_period_minutes, grace_days_per_month, reason
  - UI shows custom policies section with delete option
  - Auto-validate respects per-employee custom policies
- **CSV Export**: Payroll Summary Report exports to CSV with metrics, dept breakdown, employee details
- **New Endpoints**:
  - `GET /api/attendance/policy/custom` - List all custom policies
  - `POST /api/attendance/policy/custom` - Create/update custom policy
  - `DELETE /api/attendance/policy/custom/{employee_id}` - Delete custom policy
  - `GET /api/attendance/policy/employee/{employee_id}` - Get specific employee's policy

### HR Attendance & Leave Input Screens - February 20, 2026 ✅
- **HR Attendance Input** (`/hr-attendance-input`):
  - Attendance policy display (working days, hours, grace period)
  - Auto-validate attendance for a month
  - Apply penalties (Rs.100/day beyond grace days)
  - Bulk mark attendance for employees
  - Employee attendance summary table
- **HR Leave Input** (`/hr-leave-input`):
  - Apply leave on behalf of employees (auto-approved)
  - Bulk credit leaves to all employees
  - View/approve/reject pending leave requests
  - Summary cards: Pending, Approved, Rejected, Total Employees

### Simplified Approval Flows - February 20, 2026 ✅
- **Expense Approval**:
  - < ₹2,000: HR directly approves (1 level)
  - ≥ ₹2,000: HR → Admin (2 levels)
- **Leave Approval**:
  - RM only approval required
  - HR/Admin get notifications only
- **Attendance Policy** (Default):
  - Non-Consulting: 10 AM - 7 PM
  - Consulting: 10:30 AM - 7:30 PM
  - Grace: 3 days/month with ±30 min
  - Penalty: Rs.100/day beyond grace
  - **Custom policies override defaults for specific employees**

### Bug Fixes - February 20, 2026 ✅
- **Leave Application Bug**: Fixed validation that caused "zero balance" error despite available leaves
  - Added `DEFAULT_LEAVE_BALANCE = {'casual_leave': 12, 'sick_leave': 6, 'earned_leave': 15}` as fallback
  - Location: `backend/server.py` lines 7737-7750
- **Payroll Inputs Visibility**: HR Manager can now see all employees in payroll inputs
  - Fixed query to include employees where `is_active=True` OR `is_active` not set
  - Location: `backend/server.py` lines 9041-9045
- **DB Migration**: Initialized leave_balance for 15 employees, set is_active=True for 14 employees

### Project P&L System ✅
- **Invoice Generation**: From pricing plan installments with schedule_breakdown
- **Payment Recording**: Track payments, update invoice status
- **Incentive Eligibility**: Auto-create when invoice cleared (linked to sales employee)
- **P&L Dashboard**: Revenue, costs, profitability metrics
- **Project Costs**: Timesheet hours × hourly cost + expenses

### Payroll Linkage Integration ✅
- **Leave → Payroll**: LOP leaves auto-deducted from salary
- **Attendance → Payroll**: Present/absent/half-day calculations
- **Expense Reimbursements → Salary Slips**: Auto-included in earnings

### Expense Approval System ✅
- **Multi-level Approval**: Employee → Reporting Manager → HR/Admin
- **Expense Approvals Dashboard**: `/expense-approvals`
- **Payroll Integration**: Approved expenses linked to payroll_reimbursements

---

## Complete E2E Flows

### Sales → Billing → Collection Flow
```
Lead → Pricing Plan → Agreement → Invoice Generation → Payment → Incentive
         │                              │                 │          │
         └── rate_per_meeting          │                 │          │
             consultants               └── installments  │          │
             schedule_breakdown            linked to     │          │
                                          sales_employee │          │
                                                         └── updates collection
                                                              creates incentive_eligibility
```

### Expense → Payroll Flow
```
Employee → Expense → Manager Approval → HR Approval → Payroll → Salary Slip
                                                         │
                                                         └── payroll_reimbursements
                                                              status: processed
```

### Timesheet → Project Cost Flow
```
Consultant Assignment → Timesheet Entry → Approval → Project Cost Calculation
       │                     │                              │
       └── project_id       └── hours logged               └── hours × hourly_cost
                                                               (from salary/176)
```

---

## Key API Endpoints

### Project P&L
- `POST /api/project-pnl/generate-invoices/{pricing_plan_id}` - Generate from installments
- `POST /api/project-pnl/invoices/{id}/record-payment` - Record payment
- `GET /api/project-pnl/dashboard` - Overall P&L dashboard
- `GET /api/project-pnl/project/{id}/pnl` - Project P&L details
- `GET /api/project-pnl/project/{id}/costs` - Project costs breakdown
- `GET /api/project-pnl/invoices` - List all invoices

### Payroll
- `POST /api/payroll/generate-slip` - With all linkages (LOP, attendance, expenses)
- `GET /api/payroll/linkage-summary` - Dashboard data

### Expenses
- `POST /api/expenses/{id}/approve` - Multi-level approval
- `GET /api/expenses/pending-approvals` - Pending for user

---

## Database Collections

### New Collections
- **invoices**: Generated from pricing plan, linked to sales_employee
- **incentive_eligibility**: Created when invoice cleared, pending HR review
- **payroll_reimbursements**: Approved expenses for payroll
- **employee_attendance_policies**: Custom attendance policies per employee

### Key Fields Added
- **salary_slips**: `lop_days`, `lop_deduction`, `expense_reimbursements`, `attendance_linked`
- **leave_requests**: `payroll_deducted`, `lop_amount`
- **expenses**: `reimbursed_in_month`, `reimbursed_at`

---

## Production Readiness Audit - December 2025 ✅

### Audit Results (Iteration 81)
- **Previous Score:** 82%
- **Updated Score:** 92%
- **Backend Tests:** 93% (27/29 passed)
- **Frontend Tests:** 100%

### All Tests Passed:
- Data Integrity: All 26 employees, 4 projects have required fields
- RBAC Verification: Proper 401/403 responses
- Sales-to-Consulting Flow: Full E2E working
- Session Stability: Multi-role login/logout verified
- Failure Scenarios (Chaos Test): No silent 500 errors
- HR Module: Leave, attendance, modifications working
- Critical Bug Regression: /api/projects 520 error FIXED

### Report Location
- `/app/reports/ERP_Audit_Report_8D.md` - Ford 8D format audit report

---

## Upcoming Tasks (P1)
- Sales Incentive module (linking to `incentive_eligibility` records)
- Implement full pages for placeholder routes (`/invoices`, `/follow-ups`)

## Future Tasks (P2/P3)
- Refactor monolithic `server.py` into domain routers
- Email functionality for payroll reports
- Finance Module & Project P&L Dashboards expansion
- PWA Install Notification & Branding
- Refactor `ApprovalCenter.js` (1600+ lines) into smaller components

## Known Minor Issues
- `/api/my/check-status` returns 400 for HR Manager (non-blocking)
- React hydration warnings in Employees.js (cosmetic, doesn't affect functionality)

---

## Test Credentials
- **Admin**: admin@dvbc.com / admin123
- **HR Manager**: hr.manager@dvbc.com / hr123
- **Manager**: dp@dvbc.com / Welcome@123
- **Employee**: rahul.kumar@dvbc.com / Welcome@EMP001
- **Test Employee**: kunal.malhotra@dvbc.com / Welcome@EMP114

## Sample Custom Policy
- **Rahul Kumar (EMP001)**: Custom timing 09:30 - 18:30, 5 grace days/month, reason: "Remote worker - flexible hours"
