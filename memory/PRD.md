# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication

---

## Completed Work - February 2026

### Success Dialog Flow & Post-Go-Live Approval - February 20, 2026 ✅ (Latest)
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

## Upcoming Tasks (P1)
- Sales Incentive module (linking to `incentive_eligibility` records)
- Implement full pages for placeholder routes (`/invoices`, `/follow-ups`)

## Future Tasks (P2/P3)
- Refactor monolithic `server.py` into domain routers
- Email functionality for payroll reports
- Finance Module & Project P&L Dashboards expansion
- Day 0 guided onboarding tour
- PWA Install Notification & Branding

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
