# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication
- **AI**: GPT-4o via Emergent LLM Key

---

## Completed Work - February 2026

### Agreements Page Crash Fix & Validation Error Handling - February 21, 2026 ✅ (Latest)
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
