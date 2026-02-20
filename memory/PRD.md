# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication

---

## Completed Work - December 2025

### Project P&L System ✅ (Latest)
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

### Key Fields Added
- **salary_slips**: `lop_days`, `lop_deduction`, `expense_reimbursements`, `attendance_linked`
- **leave_requests**: `payroll_deducted`, `lop_amount`
- **expenses**: `reimbursed_in_month`, `reimbursed_at`

---

## Upcoming: HR Incentive Module
- Review incentive_eligibility records
- Define incentive criteria/slabs
- Approve and add to payroll
- Link to cleared invoices and sales performance

---

## Test Credentials
- **Admin**: admin@dvbc.com / admin123
- **HR Manager**: hr.manager@dvbc.com / hr123
- **Manager**: dp@dvbc.com / Welcome@123
- **Employee**: rahul.kumar@dvbc.com / Welcome@EMP001
