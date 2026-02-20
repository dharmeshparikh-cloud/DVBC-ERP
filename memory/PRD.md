# DVBC - NETRA: Business Management ERP

## Original Problem Statement
Build a comprehensive business management ERP with modules for Sales, HR, Consulting, and Finance. The initial focus was on "Sales to Consulting" workflow, with recent priorities shifted to enhancing HR and authentication modules.

## Core User Personas
- **System Admin**: Full system access, user management, settings
- **HR Manager**: Employee management, attendance, payroll, permissions
- **Sales Executive**: Lead management, client interactions, invoicing
- **Consultant**: Project work, timesheets, task management
- **Employee**: Self-service (attendance, leaves, expenses, salary slips)

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication

---

## Completed Work

### December 2025 - Session 2
- ✅ **Expense Approval Dashboard** (`/expense-approvals`) - Full UI for managers and HR
- ✅ **Multi-level Approval Flow**: Employee → Reporting Manager → HR/Admin
- ✅ **Payroll Integration**: Approved expenses auto-link to `payroll_reimbursements`
- ✅ **Notifications**: Sent at each approval stage
- ✅ Fixed Expense Submission Flow: Added "Submit for Approval" button
- ✅ Enhanced expense creation with proper employee/manager linking
- ✅ Verified bulk department update and "Dept"/"Special" buttons working

### December 2025 - Session 1
- ✅ Attendance System Overhaul: Rolled back geo-fencing, implemented simplified Quick Check-in
- ✅ Mobile UI Enhancement: Added Quick Check-in shortcut to mobile navigation
- ✅ Permission/Role Sync: Fixed synchronization between `users` and `employees` collections
- ✅ Sidebar Visibility Fix: Now controlled exclusively by `department_access` collection
- ✅ ID Standardization: Migrated `reporting_manager_id` to use employee codes (e.g., "EMP110")
- ✅ Data Scoping: Implemented hierarchy-based filtering for Leads module
- ✅ UI Consolidation: Merged duplicate Attendance UIs

---

## Expense Approval Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌────────────────┐
│  Employee   │────▶│ Reporting Manager│────▶│  HR/Admin   │────▶│    Payroll     │
│  Submits    │     │    Approves      │     │  Approves   │     │ Reimbursement  │
│  (pending)  │     │(manager_approved)│     │ (approved)  │     │   (pending)    │
└─────────────┘     └──────────────────┘     └─────────────┘     └────────────────┘
                              │                     │
                              ▼                     ▼
                     Notifies HR/Admin      Creates payroll_reimbursements
                                            Links to payroll period
```

**Status Flow:**
- `draft` → `pending` → `manager_approved` → `approved` → (payroll processes) → `reimbursed`

---

## Current Architecture

### Key Files
```
/app/
├── backend/
│   ├── routers/
│   │   ├── department_access.py  # Bulk update, department management
│   │   ├── expenses.py           # ENHANCED - Multi-level approval, payroll linkage
│   │   ├── leads.py              # Hierarchy-based data scoping
│   │   └── users.py              # Reporting manager logic
│   └── server.py                 # Main server (NEEDS REFACTORING)
└── frontend/
    └── src/
        ├── components/
        │   └── Layout.js          # MODIFIED - Added Expense Approvals link
        ├── pages/
        │   ├── DepartmentAccessManager.js
        │   ├── ExpenseApprovals.js   # NEW - Approval dashboard
        │   └── MyExpenses.js         # MODIFIED - Submit for Approval button
        └── App.js                    # MODIFIED - Added expense-approvals route
```

### Key Database Collections
- **employees**: `reporting_manager_id` uses employee codes (e.g., "EMP110")
- **users**: `role` synced with employee profile changes
- **department_access**: Single source of truth for sidebar visibility
- **expenses**: Multi-level approval with `approval_flow`, `current_approver`, payroll linkage
- **payroll_reimbursements**: NEW - Tracks approved expenses for payroll processing
- **notifications**: Expense notifications at each approval stage

### Key API Endpoints
- `POST /api/expenses` - Create expense with line_items
- `POST /api/expenses/{id}/submit` - Submit for approval
- `POST /api/expenses/{id}/approve` - Multi-level approve (manager then HR)
- `POST /api/expenses/{id}/reject` - Reject with reason
- `GET /api/expenses/pending-approvals` - Get expenses pending user's approval
- `GET /api/my/expenses` - Get employee's expenses

---

## Prioritized Backlog

### P0 (Critical) - None currently

### P1 (High Priority)
- Add expense reimbursements to CTC/Payroll processing view
- Mark as Reimbursed flow in Payroll

### P2 (Medium Priority)
1. **Refactor server.py** - Break into domain-specific routers (recurring 13+ sessions)
2. **Finance Module** - Payments, expenses overview, P&L reports
3. **Project P&L Dashboards** - Project profitability tracking
4. **Day 0 Onboarding Tour** - Guided tour for new users

### P3 (Low Priority)
1. **PWA Install Notification** - App install prompts
2. **PWA Branding** - Custom icons, splash screens

---

## Test Credentials
- **Admin**: admin@dvbc.com / admin123
- **HR Manager**: hr.manager@dvbc.com / hr123
- **Manager (Dhamresh Parikh)**: dp@dvbc.com / Welcome@123
- **Employee (Rahul Kumar)**: rahul.kumar@dvbc.com / Welcome@EMP001

---

## Known Technical Debt
1. `server.py` is monolithic and needs refactoring into routers
2. HTML structure warnings in DepartmentAccessManager (span inside table elements)
3. Some 404 errors for `/api/stats/consulting` and `/api/stats/hr` endpoints
4. Old expense records missing new fields (`employee_code`, `approval_flow`)
