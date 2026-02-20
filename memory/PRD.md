# DVBC - NETRA: Business Management ERP

## Original Problem Statement
Build a comprehensive business management ERP with modules for Sales, HR, Consulting, and Finance. The initial focus was on "Sales to Consulting" workflow, with recent priorities shifted to enhancing HR and authentication modules.

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication

---

## Completed Work

### December 2025 - Session 2

#### Payroll Linkage Integration ✅
- **Leave → Payroll**: LOP leaves auto-deducted from salary with `per_day_salary × LOP_days`
- **Attendance → Payroll**: Present/absent/half-day counts auto-calculated from attendance records
- **Expense Reimbursements → Salary Slips**: Approved expenses included in earnings, status updated to "reimbursed"

#### Expense Approval System ✅
- **Expense Approvals Dashboard** (`/expense-approvals`) - Full UI for managers and HR
- **Multi-level Approval Flow**: Employee → Reporting Manager → HR/Admin
- **Payroll Integration**: Approved expenses auto-link to `payroll_reimbursements`

#### Previous Fixes ✅
- Bulk department update and "Dept"/"Special" buttons verified working
- Fixed Expense Submission Flow with "Submit for Approval" button

### December 2025 - Session 1
- Attendance System Overhaul: Simplified Quick Check-in
- ID Standardization: `reporting_manager_id` uses employee codes
- Sidebar Visibility: Controlled by `department_access` collection
- Data Scoping: Hierarchy-based filtering for Leads

---

## Complete Workflow Flows

### Expense Approval & Reimbursement Flow
```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌────────────────┐     ┌─────────────┐
│  Employee   │────▶│ Reporting Manager│────▶│  HR/Admin   │────▶│    Payroll     │────▶│ Salary Slip │
│  Submits    │     │    Approves      │     │  Approves   │     │ Reimbursement  │     │ Generated   │
│  (pending)  │     │(manager_approved)│     │ (approved)  │     │   (pending)    │     │(reimbursed) │
└─────────────┘     └──────────────────┘     └─────────────┘     └────────────────┘     └─────────────┘
```

### Salary Slip Generation with Linkages
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SALARY SLIP GENERATION                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  INPUTS:                                                                         │
│    ├── CTC Structure (approved components)                                       │
│    ├── Attendance Records (present/absent/half-day)                              │
│    ├── Leave Requests (LOP leaves for deduction)                                 │
│    ├── Expense Reimbursements (from payroll_reimbursements)                      │
│    └── Payroll Inputs (incentives, overtime, advances, penalties)                │
│                                                                                  │
│  OUTPUTS:                                                                        │
│    ├── Earnings (Basic, HRA, Allowances, Reimbursements, Incentives)            │
│    ├── Deductions (PF, ESIC, PT, LOP, Advances, Penalties)                       │
│    └── Net Salary                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key API Endpoints

### Payroll Linkage APIs
- `GET /api/payroll/linkage-summary?month=YYYY-MM` - Linkage dashboard data
- `GET /api/payroll/pending-reimbursements` - Pending expense reimbursements
- `POST /api/payroll/generate-slip` - Generate with all linkages
- `POST /api/payroll/generate-bulk` - Bulk generation for all employees

### Expense APIs
- `POST /api/expenses` - Create with line_items
- `POST /api/expenses/{id}/submit` - Submit for approval
- `POST /api/expenses/{id}/approve` - Multi-level approve
- `GET /api/expenses/pending-approvals` - Pending for user

---

## Database Schema Updates

### Salary Slips (Enhanced)
```javascript
{
  // ... existing fields ...
  lop_days: Number,                    // LOP days count
  lop_deduction: Number,               // LOP deduction amount
  expense_reimbursements: Array,       // List of reimbursed expenses
  expense_reimbursement_total: Number, // Total reimbursement
  attendance_linked: Boolean,          // Attendance data used
  leave_requests_linked: Boolean,      // Leave data used
  payroll_reimbursements_linked: Boolean // Expense data used
}
```

### Leave Requests (Enhanced)
```javascript
{
  // ... existing fields ...
  payroll_deducted: Boolean,   // Deducted from salary
  payroll_month: String,       // Which month's payroll
  lop_amount: Number           // Deduction amount
}
```

### Expenses (Enhanced)
```javascript
{
  // ... existing fields ...
  status: "reimbursed",
  reimbursed_at: DateTime,
  reimbursed_in_month: "2026-02"
}
```

---

## Prioritized Backlog

### P1 (High Priority)
- Timesheets → Project Billing/Invoicing linkage
- Bank Details → Salary Disbursement/NEFT file generation

### P2 (Medium Priority)
1. **Refactor server.py** - Break into domain-specific routers
2. **Finance Module** - Complete P&L reports
3. **Performance → Salary Increment** linkage

### P3 (Low Priority)
1. PWA Install Notification
2. Day 0 Onboarding Tour

---

## Test Credentials
- **Admin**: admin@dvbc.com / admin123
- **HR Manager**: hr.manager@dvbc.com / hr123
- **Manager (Dhamresh Parikh)**: dp@dvbc.com / Welcome@123
- **Employee (Rahul Kumar)**: rahul.kumar@dvbc.com / Welcome@EMP001
