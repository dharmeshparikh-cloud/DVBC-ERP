# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication (Employee ID + Client ID)
- **AI**: GPT-4o via Emergent LLM Key
- **Documentation**: python-docx, reportlab for PDF/DOCX generation
- **Email**: SMTP via SendGrid

---

## Completed Work - December 2025

### Phase 46: Comprehensive Approval Logic Audit - December 2025 ✅ (Latest)

**Full Security & Logic Audit Completed:**
- Analyzed 15 distinct approval workflows across 8 modules
- Reviewed 8 backend router files totaling 5,000+ lines of code
- Documented all authorization mechanisms and security gaps

**Audit Findings:**

| Category | Count | Details |
|----------|-------|---------|
| Total Workflows | 15 | Across Sales, HR, Finance, Projects |
| Properly Enforced | 10 | Backend RBAC validation |
| UI-Only Gates (Gaps) | 3 | Security vulnerabilities identified |
| Partial Enforcement | 2 | Inconsistent authorization |
| Admin Overrides | 4 | Documented with audit trail status |

**Security Fixes Implemented:**

| Risk Level | Issue | Fix Applied |
|------------|-------|-------------|
| HIGH | Leave Encashment - Missing approval endpoint | ✅ Created full CRUD: `/encashment-requests`, `/approve`, `/reject`, `/withdraw` |
| MEDIUM | Quotation Finalization - No authorization | ✅ Added Reporting Manager/Sales Manager/Admin check, creator cannot self-approve |
| MEDIUM | Travel Approval - Overly broad roles | ✅ Restricted to HR roles and Admin only (removed sales_manager) |

**New Endpoints Created:**
- `GET /api/leave-policies/encashment-requests` - List all encashment requests (HR/Admin all, users own)
- `GET /api/leave-policies/encashment-requests/{id}` - Get single request
- `POST /api/leave-policies/encashment-requests/{id}/approve` - HR Admin approves, links to payroll
- `POST /api/leave-policies/encashment-requests/{id}/reject` - HR Admin rejects with reason
- `POST /api/leave-policies/encashment-requests/{id}/withdraw` - Owner withdraws pending request

**Authorization Changes:**
- `PATCH /api/quotations/{id}/finalize` - Now requires Reporting Manager, Sales Manager, or Admin (creator blocked)
- `POST /api/travel/reimbursements/{id}/approve` - Now requires HR_ROLES or Admin only
- `POST /api/travel/reimbursements/{id}/reject` - Now requires HR_ROLES or Admin only

**Documentation Created:**
- `/app/AUDIT_APPROVAL_LOGIC.md` - Comprehensive 400+ line audit report

**Files Modified:**
- `/app/backend/routers/leave_policies.py` - Added 5 encashment approval endpoints (~200 lines)
- `/app/backend/routers/quotations.py` - Added RBAC check to finalize endpoint
- `/app/backend/routers/travel.py` - Restricted approval to HR roles only

**Testing:**
- ✅ 12/12 RBAC regression tests pass
- ✅ All new endpoints respond correctly (curl verified)
- ✅ Backend starts without errors
- ✅ Authorization restrictions working (HR can approve, others blocked)

---

### Phase 45: Performance Optimization - December 2025 ✅

**Backend Caching:**
- Created `/app/backend/services/cache_service.py` - High-performance in-memory cache
- Stats endpoints cached: `/api/stats/dashboard`, `/api/stats/hr`
- Cache monitoring: `/api/stats/cache/stats`
- Cache invalidation: `/api/stats/cache/invalidate`

**Backend Pagination:**
- `/api/leads` - Paginated with query params (page, page_size)
- `/api/employees` - Paginated with query params
- Added `/api/leads/all` and `/api/employees/all` for unpaginated access (dropdowns)
- Response format: `{ items: [], pagination: { page, page_size, total_items, total_pages, has_next, has_prev } }`

**Frontend React Query Integration:**
- Installed `@tanstack/react-query@4`
- Created `/app/frontend/src/lib/queryClient.js` - Query client config
- Created `/app/frontend/src/hooks/useApi.js` - Custom hooks for all API calls
- 5 minute stale time for dashboard stats
- Automatic cache invalidation on mutations

**MongoDB Index Optimization (79 indexes):**
- Created `/app/backend/services/index_optimizer.py` - Comprehensive index management
- Compound indexes following ESR rule (Equality, Sort, Range)
- Partial indexes for status-based queries
- RBAC indexes: assigned_to, created_by, reporting_manager_id
- Key collections: users (5), employees (9), leads (7), projects (7), agreements (5)

**Performance Results:**
- Cache hit: ~35% faster API responses
- Pagination: Reduced payload sizes from ~50KB to ~10KB average
- Index creation: 2.57s for 79 indexes across 27 collections
- Full scan elimination for common queries

**Files Created:**
- `/app/backend/services/cache_service.py`
- `/app/backend/services/index_optimizer.py`
- `/app/frontend/src/lib/queryClient.js`
- `/app/frontend/src/hooks/useApi.js`
- `/app/memory/PERFORMANCE_OPTIMIZATION.md`

**Files Modified:**
- `/app/backend/routers/stats.py` - Added caching
- `/app/backend/routers/leads.py` - Added pagination
- `/app/backend/routers/employees.py` - Added pagination
- `/app/backend/routers/analytics.py` - Added cache import
- `/app/backend/routers/deps.py` - Added PaginationParams class
- `/app/backend/routers/performance.py` - Updated to use IndexOptimizer
- `/app/frontend/src/App.js` - Added QueryClientProvider

**Testing:**
- ✅ All backend tests pass
- ✅ 79/81 indexes created (2 skipped due to data issues)
- ✅ Pagination working (49 leads → 5 pages)
- ✅ Cache stats showing hit/miss ratios
- ✅ Dashboard loads correctly

---

### Phase 44: Dashboard Architecture Cleanup & Consolidation - December 2025 ✅

**Dashboard Audit Completed:**
- Identified 13 dashboard components, 4 orphaned/legacy files
- Documented all routing conditions and entry points
- Found duplicate sales dashboards causing inconsistencies

**Actions Taken:**

| Action | Details |
|--------|---------|
| RBAC Widget Added | ConsultingDashboard, HRDashboard, ConsultantDashboard |
| Sales Dashboard Consolidated | Removed SalesDashboardEnhanced from default routing |
| Dashboard.js Simplified | Removed redundant domain-based routing |
| Orphaned Files Deleted | HRPortalDashboard.js, DashboardLayoutA.js, SalesDashboardEnhanced.js (~65KB) |
| deps.py Refactored | Legacy constants now have fallbacks with RBAC DB integration |

**Canonical Dashboard Structure:**
- `admin` role → `AdminDashboard` (Business Overview)
- `consultant` role → `ConsultantDashboard`
- Sales roles → `SalesDashboard`
- HR roles → `HRDashboard`
- Consulting roles → `ConsultingDashboard`
- Others → `Dashboard` (generic)

**Files Modified:**
- `/app/frontend/src/App.js` - Removed unused imports, consolidated routing
- `/app/frontend/src/pages/Dashboard.js` - Removed domain routing
- `/app/frontend/src/pages/ConsultingDashboard.js` - Added RBAC widget
- `/app/frontend/src/pages/HRDashboard.js` - Added RBAC widget
- `/app/frontend/src/pages/ConsultantDashboard.js` - Added RBAC widget
- `/app/backend/routers/deps.py` - Refactored role constants with fallbacks

**Files Deleted:**
- `/app/frontend/src/pages/HRPortalDashboard.js` (16KB)
- `/app/frontend/src/pages/DashboardLayoutA.js` (11KB)
- `/app/frontend/src/pages/SalesDashboardEnhanced.js` (37KB)

**Documentation Created:**
- `/app/memory/ADMIN_DASHBOARD_AUDIT.md`

**Testing:**
- ✅ 12/12 RBAC regression tests pass
- ✅ Dashboard loads correctly after cleanup
- ✅ Frontend bundle size reduced by ~64KB

---

### Phase 43: Stats Dashboard Security Audit & RBAC Migration - December 2025 ✅

**Security Audit Completed:**
- Full audit of `/api/stats/dashboard` and related endpoints
- Identified critical data leakage vulnerabilities
- Fixed all legacy string-based role checks
- Implemented proper role hierarchy and team filtering

**Issues Fixed:**

| Endpoint | Issue | Fix |
|----------|-------|-----|
| `/api/stats/dashboard` | Binary admin check only | Three-tier access (all data / team / own) |
| `/api/stats/hr` | No authorization | Requires HR_ROLES or MANAGER_ROLES |
| `/api/stats/consulting` | No authorization | Requires CONSULTING_ROLES or MANAGER_ROLES |
| `/api/stats/sales` | Revenue leakage | Filtered by role and ownership |

**New Features:**
- Added `ALL_DATA_ACCESS_ROLES` group to RBAC service
- Implemented team hierarchy filtering for managers
- Added fail-closed authorization for sensitive stats
- **NEW: Real-time RBAC Dashboard Widget** - Shows user's current role, level, permissions, and data access scope

**RBAC Widget Features:**
- Displays role name and numeric level (e.g., "Administrator - Level 100")
- Color-coded access tier badges (Full Access, Department Lead, Manager, Team Member, Basic)
- Shows department and data access scope
- Permission indicators (Approvals, Reports, Manage Users, Team Data)
- Expandable view with security notice

**Backend RBAC Migration in projects.py:**
- Migrated consultant assignment endpoints to use RBAC service
- All 4 legacy role checks replaced with `get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=True)`

**Frontend-Backend Permission Validation:**
- Fixed `ManagerApprovals.js` to use `usePermissions()` context
- Updated lead delete endpoint with proper RBAC check
- Created comprehensive permission mismatch report

**Files Modified:**
- `/app/backend/routers/stats.py` - Full RBAC migration
- `/app/backend/routers/projects.py` - Consultant assignment RBAC
- `/app/backend/routers/rbac_service.py` - Added ALL_DATA_ACCESS_ROLES
- `/app/backend/routers/leads.py` - Delete endpoint RBAC
- `/app/frontend/src/components/RBACWidget.js` - NEW: Permission widget
- `/app/frontend/src/pages/AdminDashboard.js` - Added RBAC widget
- `/app/frontend/src/pages/SalesDashboard.js` - Added RBAC widget
- `/app/frontend/src/pages/Dashboard.js` - Added RBAC widget
- `/app/frontend/src/pages/sales-funnel/ManagerApprovals.js` - Permission context

**Documentation Created:**
- `/app/memory/STATS_DASHBOARD_AUDIT.md`
- `/app/memory/FRONTEND_BACKEND_PERMISSION_MATRIX.md`

**Testing:**
- ✅ 12/12 RBAC regression tests pass
- ✅ All stats endpoints verified via curl
- ✅ Role-based filtering confirmed
- ✅ RBAC widget visible and functional

---

## Completed Work - February 2026

### Phase 42: RBAC HR & Attendance Migration (Phase 2) - February 23, 2026 ✅ (Latest)

**Phase 2 Migration Completed (10 Modules, 77 Role Checks):**

| Module | Checks | Role Groups Used |
|--------|--------|-----------------|
| attendance.py | 15 | HR_ROLES, HR_ADMIN_ROLES |
| ctc.py | 10 | HR_ROLES, HR_ADMIN_ROLES |
| department_access.py | 7 | HR_ADMIN_ROLES |
| employees.py | 10 | HR_ROLES, HR_ADMIN_ROLES |
| users.py | 3 | HR_ADMIN_ROLES |
| permission_config.py | 7 | HR_ADMIN_ROLES |
| timesheets.py | 5 | MANAGER_ROLES, HR_ROLES |
| travel.py | 3 | HR_ADMIN_ROLES |
| leave_policies.py | 12 | HR_ROLES, HR_ADMIN_ROLES |
| leave_requests.py | 5 | HR_ROLES, MANAGER_ROLES |

**Testing:**
- ✅ 12/12 regression tests pass
- ✅ All HR endpoints verified via curl
- ✅ Zero fallback events

**Cumulative Migration Status:**
- Phase 1: 5 modules, 16 checks ✅
- Phase 2: 10 modules, 77 checks ✅
- **Total: 15 modules, 93 role checks migrated**

---

### Phase 41: RBAC Critical Endpoints Migration - February 23, 2026 ✅

**Phase 1 Migration Completed (5 Critical Modules):**

| Module | Endpoints Migrated | Role Group | Status |
|--------|-------------------|------------|--------|
| kickoff.py | return, approve-internal, reject (3) | PRINCIPAL_CONSULTANT_ROLES | ✅ |
| agreements.py | approve, reject, send-to-client (3) | AGREEMENT_APPROVE_ROLES | ✅ |
| project_completion.py | complete, pending, recalculate (3) | PROJECT_ROLES | ✅ |
| project_pnl.py | generate-invoices, record-payment, dashboard (3) | MANAGER_ROLES | ✅ |
| approvals.py | all, action, scope-task, reminders (4) | MANAGER_ROLES | ✅ |

**Key Changes:**
- All critical endpoints now use `get_role_group(name, fail_closed=True)`
- Fail-closed behavior: Returns 403 if RBAC cache unavailable
- Zero fallback events in production
- Backward compatible with existing role assignments

**Security Improvements:**
- `require_role_group_critical()` dependency added for fail-closed checks
- `/api/rbac/health` endpoint added for monitoring
- No "permit on error" paths in critical endpoints

**Testing:**
- ✅ 12/12 regression tests pass
- ✅ All migrated endpoints verified via curl
- ✅ Zero fallback events in `/api/rbac/migration-status`

**Files Modified:**
- `/app/backend/routers/kickoff.py` - 3 role checks migrated
- `/app/backend/routers/agreements.py` - 3 role checks migrated
- `/app/backend/routers/project_completion.py` - 3 role checks migrated
- `/app/backend/routers/project_pnl.py` - 3 role checks migrated
- `/app/backend/routers/approvals.py` - 4 role checks migrated

---

### Phase 40: Database-Driven RBAC System - February 23, 2026 ✅

**RBAC Phase 3 - Seeder Script:**
- ✅ Created `/app/backend/routers/rbac_seeder.py` - Syncs hardcoded roles to DB
- ✅ 17 roles, 6 departments, 16 role groups defined and synced
- ✅ Includes ROLE_DEFINITIONS, ROLE_GROUP_DEFINITIONS, DEPARTMENT_DEFINITIONS
- ✅ Idempotent sync - can run multiple times safely

**RBAC Phase 4 - Backend Integration:**
- ✅ Updated `/app/backend/routers/deps.py` to import from `rbac_service`
- ✅ Added `get_role_group()` function to fetch roles from DB
- ✅ Added `has_role()`, `has_permission()`, `can_approve()`, `is_manager()` helpers
- ✅ Added `require_role_group()` dependency for DB-driven role checks
- ✅ Added `require_permission()` dependency for permission-based access
- ✅ Added `require_approval_role()` dependency
- ✅ Backward compatible - hardcoded constants still work as fallbacks

**RBAC Phase 5 - Frontend Integration:**
- ✅ Updated `/app/frontend/src/contexts/PermissionContext.js`
- ✅ Fetches from `/api/rbac/my-permissions` (new RBAC API)
- ✅ Falls back to legacy `/api/role-management/my-permissions` if needed
- ✅ Added `rbacData` state with full role information
- ✅ Added `isAdmin()`, `canManageUsers()`, `getStageAccess()` helpers
- ✅ Converts RBAC permissions to legacy format for backward compatibility

**New API Endpoint:**
- `GET /api/rbac/migration-status` - Returns RBAC health and statistics

**Testing Results:**
- ✅ Backend: 100% (15/15 tests passed)
- ✅ Frontend: 100% (All UI tests passed)
- ✅ Test file: `/app/backend/tests/test_rbac_integration.py`

**Files Created/Modified:**
- `/app/backend/routers/rbac_seeder.py` (NEW - Phase 3)
- `/app/backend/routers/deps.py` (MODIFIED - Phase 4)
- `/app/backend/routers/rbac_router.py` (MODIFIED - migration-status endpoint)
- `/app/frontend/src/contexts/PermissionContext.js` (MODIFIED - Phase 5)

---

### Phase 39: Sales Funnel P0 Bug Fixes & Progress Indicator Enhancement - February 23, 2026 ✅

**Bug 1 - Record Meeting Button URL (P0):**
- ✅ Fixed `handleContinue()` in SalesFunnelOnboarding.js
- ✅ Changed step ID checks from `'meeting'` to `'record_meeting'`
- ✅ Changed step ID checks from `'pricing'` to `'pricing_plan'`
- ✅ Changed step ID checks from `'sow'` to `'scope_of_work'`
- ✅ Button now correctly navigates to `/sales-funnel/meeting/record?leadId=<id>`

**Bug 2 - Lead Status Auto-Update (P0):**
- ✅ Added FUNNEL_TO_STATUS_MAP in `get_lead_funnel_progress()` backend function
- ✅ Automatically updates lead status based on furthest completed funnel step

**Enhancement - Visual Progress Indicators on Leads List:**
- ✅ Added new `GET /api/leads/progress/bulk` endpoint for efficient batch progress loading
- ✅ Created `FunnelProgressIndicator` component with color-coded progress bar and tooltips
- ✅ Click-to-navigate functionality opening Sales Funnel directly from progress indicator

**Enhancement - Hide Status Column from Leads Page:**
- ✅ Removed Status dropdown column from the Leads list view
- ✅ Status is now auto-managed by funnel progression logic

**Enhancement - Clickable Dashboard Cards:**
- ✅ Sales Dashboard: Total Leads → /leads, In Progress → /leads?stage=in_progress, Completed → /projects, Conversion → /analytics
- ✅ HR Dashboard: Total Employees → /employees, Present/Absent/WFH → /attendance
- ✅ Consulting Dashboard: Active/Completed/OnHold/AtRisk Projects → /projects with filters
- ✅ Admin Dashboard: Added useNavigate hook for card interactions
- ✅ All cards now show "View X →" link hints and hover effects

**Files Modified:**
- `/app/frontend/src/pages/SalesFunnelOnboarding.js`
- `/app/frontend/src/pages/Leads.js`
- `/app/frontend/src/pages/SalesDashboard.js`
- `/app/frontend/src/pages/HRDashboard.js`
- `/app/frontend/src/pages/AdminDashboard.js`
- `/app/frontend/src/pages/ConsultingDashboard.js`
- `/app/backend/routers/leads.py`

---

### Phase 38: Access Control Fixes & E2E Kickoff Flow Testing - February 23, 2026 ✅

**Agreement Workflow Fixed:**
```
1. Sales Executive creates agreement → status: 'draft'
2. Sales Executive submits for approval → status: 'pending_approval'  
3. ONLY Principal Consultant or Admin can approve → status: 'approved'
4. Only after PC approval can agreement be sent to client
```

**New Endpoint Added:**
- `PATCH /api/agreements/{id}/submit-for-approval` - Sales submits draft for PC review

**Access Control:**
- ✅ Sales Executives CAN create agreements (status: `draft`)
- ✅ Sales Managers CANNOT approve (blocked with clear error message)
- ✅ ONLY Principal Consultant or Admin can approve/reject
- ✅ Client-facing communications require Principal Consultant approval

**E2E Kickoff Flow Tested Successfully:**
1. ✅ Create Lead (Sales Executive)
2. ✅ Record Meeting
3. ✅ Create Pricing Plan
4. ✅ Create Quotation
5. ✅ Create Agreement (Sales Executive - now allowed)
6. ✅ Approve Agreement (Reporting Manager)
7. ✅ Verify First Installment Payment
8. ✅ Create Kickoff Request
9. ✅ Principal Consultant Internal Approval → Project ID Generated (PROJ-20260223-0001)
10. ✅ Client Approval via Token Link → Client User Created (98000)
11. ✅ Client Portal Login Successful

**Test Client Credentials:**
- Client ID: `98000`
- Project: `PROJ-20260223-0001`
- Company: E2E Test Company Ltd

---

### Phase 37: All Projects Consultant Assignment UI - February 23, 2026 ✅

**New All Projects Page (Principal Consultant View):**
- ✅ Created `/all-projects` route accessible to Principal Consultant, Senior Consultant, Admin
- ✅ Shows ALL projects with assignment status indicators
- ✅ Projects needing assignment highlighted with amber left border and "Needs Assignment" badge
- ✅ Stats banner showing Total Projects and Needs Assignment counts
- ✅ Filter buttons: All, Needs Assignment, Assigned
- ✅ Search by project name, client, or ID
- ✅ Assign Consultant dialog with role selection and meeting commitment
- ✅ Assignment History dialog showing full history of assignments
- ✅ Unassign consultant functionality (preserves history)

**New Backend Endpoints:**
- `GET /api/projects/all/for-assignment` - Returns all projects with assignment details
- `POST /api/projects/{id}/assign-consultant` - Assigns a consultant to project
- `DELETE /api/projects/{id}/unassign-consultant/{consultant_id}` - Removes consultant (preserves history)
- `PATCH /api/projects/{id}/change-consultant` - Replace one consultant with another
- `GET /api/projects/{id}/assignment-history` - Full history of assignments

**Testing Results:**
- 100% backend test pass rate (13/13 tests)
- 100% frontend UI verification
- Access control verified (PC001, SC001 can access; CON001 gets 403)

---

### Phase 36: Client Portal UI Redesign - February 23, 2026 ✅

**Client Portal Light Theme Alignment:**
- ✅ **ClientLogin.js** - Completely redesigned to match main ERP Login.js
  - Black left panel with feature cards (Project Dashboard, Documents, Payments, Meeting Notes)
  - White right panel with login card and D&V logo
  - Black/white color scheme matching main ERP
  - "Back to Employee Login" navigation link
  - Remember My Client ID checkbox
  - All data-testid attributes added for testing
  
- ✅ **ClientPortal.js** - Updated to light theme
  - White background with black text
  - Black selected project in sidebar
  - Consistent card styling with black/10 borders
  - Added Change Password navigation button in header
  - All API paths fixed to use /api/ prefix
  
- ✅ **ClientChangePassword.js** - Completely redesigned
  - Matching black left panel + white right panel layout
  - Password security tips in left panel
  - D&V logo in header
  - All API paths fixed to use /api/ prefix
  - Password requirements checker with visual feedback

**Testing Results:**
- 100% test pass rate (29/29 frontend tests)
- Visual consistency verified between Client Login and Main Login
- Mobile responsiveness verified
- Form functionality working correctly

---

### Phase 35: Principal Consultant + Client Dual Approval - February 23, 2026 ✅

**Dual Approval Flow (Completely Redesigned):**

1. **Internal Approval (Principal Consultant ONLY)**
   - Only `principal_consultant` and `admin` can approve (removed Senior Consultant)
   - When approved:
     - Project ID generated: `PROJ-YYYYMMDD-XXXX` (locked, auto-generated)
     - Status: `internal_approved`
     - Sales team notified: "Project Approved"
     - Internal team email: "New Project Added"
     - Client receives approval email

2. **Client Approval (External)**
   - Client clicks secure link from email
   - Can confirm/change project start date
   - When approved:
     - Status: `approved`
     - Client user account created (ID: `98XXX` format, 5-digit)
     - Welcome email with NETRA credentials
     - All stakeholders notified

3. **Client Portal Access**
   - Client ID: 5-digit sequential starting from `98000`
   - Auto-generated password (must change on first login)
   - Admin can reset password

**New Database Models:**
- `ClientUser` - Client portal accounts
- `ProjectAssignment` - Consultant assignment with history tracking

**New Endpoints:**
- `POST /api/kickoff-requests/{id}/accept` - Principal Consultant approval
- `GET /api/kickoff-requests/client-approve/{token}` - Client approval page
- `POST /api/kickoff-requests/client-approve/{token}/confirm` - Client confirms with start date

**Status Flow:**
```
pending → internal_approved → approved → converted
```

**Email Notifications:**
1. To Client: Project approval email with confirm button
2. To Internal Team: New Project Added notification
3. To Client: Welcome email with NETRA credentials
4. To All Stakeholders: Project Activated (start date confirmed)

---

### Phase 34: Email Templates Preview & Agreement Blocking - February 23, 2026 ✅

**Email Template Previews:**
- ✅ Added `/api/test/email-preview/{template_name}` - HTML preview endpoint
- ✅ Added `/api/test/email-preview-json/{template_name}` - JSON summary endpoint  
- ✅ All 5 templates with Indian test data (TCS, Priya Sharma, etc.)
- ✅ Templates include D&V logo (2x broader - 100px height) on light gray header
- ✅ Agreement email includes: View, Download, Upload, Edit, Approve, Reject buttons
- ✅ Kickoff Accepted email includes "Edit Start Date" option
- ✅ "Approve Agreement" button added to blocking banner

**Agreement Status Blocking:**
- ✅ Modified `/api/leads/{id}/funnel-progress` to detect blocking
- ✅ New fields: `is_blocked`, `blocked_reason`, `blocked_at_step`
- ✅ Blocks progression to Payment, Kickoff, Complete if agreement is:
  - `pending`, `draft`, `review`, or `rejected`
- ✅ Frontend blocking banner with red warning
- ✅ "Review Agreement" + "Approve Agreement" buttons for quick action
- ✅ "Agreement Approval Required" disabled button on blocked steps

---

### Phase 33: Sales Funnel Email Notifications - February 23, 2026 ✅

**HTML Email Notifications at Key Milestones:**
- ✅ **MOM Filled** - When meeting with MOM is recorded
- ✅ **Proforma Generated** - When quotation is created  
- ✅ **Agreement Created** - When service agreement is created
- ✅ **Kickoff Sent** - When kickoff request is submitted for approval
- ✅ **Kickoff Accepted** - When kickoff is approved and project created

**Email Features:**
- Professional HTML templates with DVBC branding
- Includes all relevant details (amounts, dates, people)
- Client expectations and key commitments summary
- Direct links to relevant pages in NETRA
- Background tasks - non-blocking email sending

**Backend Changes:**
- NEW: `/app/backend/services/funnel_notifications.py` - Email templates
- Modified: meetings.py, quotations.py, agreements.py, kickoff.py

---

### Phase 32: Sales Funnel Training & Draft System - February 23, 2026 ✅

**Progress Checklist for New Salespeople:**
- ✅ Added `GET /api/leads/{id}/funnel-checklist` endpoint
- ✅ Returns detailed requirements checklist for each step
- ✅ Shows completion status (Done/Pending) with progress bar
- ✅ "Tips for New Salespeople" expandable section with guidance
- ✅ Required vs optional requirements marked

**Offline Meeting Attachments:**
- ✅ Added `POST /api/meetings/{id}/attachments` - Upload photo/voice files
- ✅ Added `GET /api/meetings/{id}/attachments` - List meeting attachments
- ✅ Added `GET /api/meetings/{id}/attachments/{attachment_id}/download` - Download file
- ✅ Added `DELETE /api/meetings/{id}/attachments/{attachment_id}` - Remove attachment
- ✅ Added `GET /api/meetings/lead/{id}/attachments` - All attachments for a lead
- ✅ First offline meeting requires photo/voice attachment (mandatory)
- ✅ Attachments stored with meeting and inherited downstream to kickoff

**Funnel Draft System:**
- ✅ Added `POST /api/leads/{id}/funnel-draft` - Save funnel position
- ✅ Added `GET /api/leads/{id}/funnel-draft` - Get active draft
- ✅ Added `DELETE /api/leads/{id}/funnel-draft` - Discard draft
- ✅ Added `GET /api/leads/funnel-drafts/all` - List all user's funnel drafts
- ✅ Auto-saves current step position when navigating funnel
- ✅ Resume from where left off when clicking on a lead

**Frontend Updates:**
- ✅ SalesFunnelOnboarding.js - Completion Checklist with progress bar
- ✅ SalesFunnelOnboarding.js - Tips for new salespeople (expandable)
- ✅ MeetingRecord.js - File upload UI for offline meetings
- ✅ MeetingRecord.js - Attachment preview before submission
- ✅ MeetingRecord.js - First offline meeting validation

---

### Phase 31: Sales Funnel E2E Complete - February 22, 2026 ✅

**Sales Funnel Progress Tracking:**
- ✅ Added `GET /api/leads/{id}/funnel-progress` endpoint
- ✅ Returns: completed_steps, current_step, total_steps (9), progress_percentage
- ✅ 9 stages: lead_capture → record_meeting → pricing_plan → scope_of_work → quotation → agreement → record_payment → kickoff_request → project_created

**Meeting-Lead Linkage:**
- ✅ Added `POST /api/meetings/record` - Record sales meeting with MOM
- ✅ Added `GET /api/meetings/lead/{id}` - List all meetings for a lead
- ✅ MOM (Minutes of Meeting) required before submission
- ✅ Client expectations and key commitments captured
- ✅ Meeting history shown in kickoff details with funnel summary

**Leads Page:**
- ✅ Auto-redirect to Sales Funnel after lead creation
- ✅ Lead list with Score badges, Progress, Status dropdowns
- ✅ **Funnel** button on each row to start onboarding

---

### Phase 30: Expense Approval UI Enhancements - February 22, 2026 ✅

**Enhanced Expense Approval Cards:**
- ✅ **Receipts** button - Opens dialog showing uploaded receipts
- ✅ **Send Back** dialog - For revision with comments
- ✅ **Modify Amount** dialog - Approve with modified amount
- ✅ Withdrawal capability for pending requests
- ✅ Unified ApprovalCard.js component

---

## Upcoming Tasks

### P0 - High Priority (From Audit)
1. **Create Leave Encashment Approval Endpoint** - HIGH risk gap identified in audit
2. **Add Quotation Finalization Authorization** - MEDIUM risk security gap

### P1 - Features & Fixes (From Audit)
3. **Complete RBAC Migration for Expenses/Travel** - Replace hardcoded roles with `get_role_group()`
4. **Restrict Travel Approval Scope** - Remove sales_manager from travel approvers
5. **Add Audit Trail for Admin Overrides** - Log all admin interventions
6. **Frontend React Query Migration** - Migrate remaining components to `useApi` hook
7. **Custom Report Builder Backend**: Implement backend logic for generating reports
8. **Client Dashboard Features**: Project progress, document access, payment history

### P2 - Lower Priority
9. **DVBC Marketing Hub** - Marketing dashboard and campaigns
10. **Consultant Incentive System** - Commission tracking
11. **AI Chat & Voice** - OpenAI Whisper integration
12. **Internal Chat System** - Team messaging
13. **"Day 0" Onboarding Tour** - Interactive guide
14. **Standardize Send Back vs Reject Semantics** - Consistent UX across modules
15. **Refactor kickoff.py** - Break down 1500+ line file into smaller services

---

## Test Credentials
- **Admin:** ADMIN001 / test123
- **Sales Executive:** SE001 / test123
- **HR Manager:** HR001 / password123
- **Project Manager:** PM001 / test123

---

## Key API Endpoints

### Sales Funnel
- `GET /api/leads/{id}/funnel-progress` - Get funnel completion status
- `GET /api/leads/{id}/funnel-checklist` - Get step-by-step requirements
- `POST /api/leads/{id}/funnel-draft` - Save funnel position
- `GET /api/leads/{id}/funnel-draft` - Get resume position

### Meetings
- `POST /api/meetings/record` - Record meeting with MOM
- `GET /api/meetings/lead/{id}` - List lead's meetings
- `POST /api/meetings/{id}/attachments` - Upload photo/voice
- `GET /api/meetings/{id}/attachments` - List attachments

### Kickoff
- `GET /api/kickoff-requests/{id}/details` - Full details with funnel summary

---

## Database Collections
- `leads` - Lead information
- `meetings` - Meeting records with MOM
- `meeting_attachments` - Photo/voice files for meetings
- `funnel_drafts` - User's funnel position tracking
- `pricing_plans`, `sows`, `quotations`, `agreements` - Sales documents
- `kickoff_requests` - Project kickoff approvals
