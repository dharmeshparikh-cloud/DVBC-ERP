# Employee to Domain Access - Complete Flow Analysis

## Your Question: Sales Manager Example

When you create a **Sales Manager** with:
- Department: "Sales"
- Reporting Manager: Selected
- Role: "account_manager" or "executive"
- Designation: "Sales Manager"

### Does this automatically give Sales page access? 

**NO - Not automatically!** There are **2 steps**:

---

## Step-by-Step: What Actually Happens

### STEP 1: HR Creates Employee (Onboarding)
```
HR fills form:
├── Department: "Sales"
├── Designation: "Sales Manager"  
├── Role: "account_manager"        ← THIS IS THE KEY!
├── Reporting Manager: [Selected]
├── Level: "manager"
└── [Submit]

Result: Employee record created
BUT: No login credentials yet = CANNOT ACCESS SYSTEM
```

### STEP 2: Grant Portal Access (REQUIRED!)
```
HR Manager clicks "Grant Access" button on employee
├── System creates USER record
├── Links user.id to employee.user_id
├── Sets user.role = employee.role ("account_manager")
├── Generates temp password: Welcome@EMP001
└── Employee can now LOGIN

Result: NOW they can access Sales pages!
```

---

## How Role → Page Access Works

```javascript
// In Layout.js - Line 20 & 39
const SALES_ROLES_NAV = ['admin', 'executive', 'account_manager', 'manager'];
const showSales = SALES_ROLES_NAV.includes(user.role);

// If user.role = "account_manager" → showSales = true → Sales nav visible
```

### Role to Domain Mapping:

| Role Selected in Onboarding | Pages They See |
|----------------------------|----------------|
| `executive` | Sales (Leads, SOW, Agreements, etc.) |
| `account_manager` | Sales (Leads, SOW, Agreements, etc.) |
| `consultant` | Consulting (Projects, Tasks, My Projects) |
| `project_manager` | Consulting + Admin |
| `principal_consultant` | Consulting + Admin |
| `hr_executive` | HR (Employees, Attendance, Leaves) |
| `hr_manager` | HR + some Admin |

---

## Complete Flow: Sales Manager from Hire to Deal Close

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HIRING & SETUP                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. HR ONBOARDING                                                        │
│     ├── Personal Details (Name, Email, Phone)                           │
│     ├── Employment: Department="Sales", Role="account_manager"          │
│     ├── Designation="Sales Manager", Reporting Manager=CEO              │
│     ├── Level="manager"                                                  │
│     ├── Documents (Aadhaar, PAN)                                        │
│     └── Bank Details                                                     │
│                                                                          │
│     OUTPUT: employees collection record                                  │
│     { id: "emp-001", role: "account_manager", user_id: NULL }          │
│                                                                          │
│  2. GRANT PORTAL ACCESS                                                  │
│     ├── HR Manager clicks "Grant Access"                                │
│     ├── Role selection confirmed: "account_manager"                     │
│     └── Temp password generated                                          │
│                                                                          │
│     OUTPUT: users collection record                                      │
│     { id: "user-001", role: "account_manager" }                         │
│     employees.user_id = "user-001" ← LINKED!                            │
│                                                                          │
│  3. CTC DESIGN & APPROVAL                                               │
│     ├── HR designs salary structure                                     │
│     └── Admin approves                                                   │
│                                                                          │
│     OUTPUT: ctc_structures { employee_id: "emp-001", status: "active" } │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DAILY OPERATIONS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  4. LOGIN & ACCESS                                                       │
│     ├── Employee logs in with temp password                             │
│     ├── Changes password                                                │
│     └── Sees: My Workspace + Sales pages (because role=account_manager) │
│                                                                          │
│  5. DAILY HR LINKS (Auto-connected via employee_id)                     │
│     ├── Attendance: Mark daily (attendance.employee_id)                 │
│     ├── Leaves: Apply leave (leave_requests.employee_id)                │
│     ├── Expenses: Submit claims (expenses.employee_id)                  │
│     └── Salary: View slips (salary_slips.employee_id)                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SALES WORK FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  6. CREATE LEAD                                                          │
│     ├── Sales Manager creates lead                                       │
│     └── leads.created_by = user.id ("user-001")                         │
│                                                                          │
│  7. MEETINGS & MOM                                                       │
│     ├── Schedule meetings with lead                                     │
│     └── meetings.created_by = user.id                                   │
│                                                                          │
│  8. PRICING PLAN                                                         │
│     ├── Build pricing for lead                                          │
│     └── pricing_plans.created_by = user.id                              │
│                                                                          │
│  9. SOW (Statement of Work)                                             │
│     ├── Create scope items                                              │
│     └── sow.created_by = user.id                                        │
│                                                                          │
│  10. QUOTATION                                                           │
│      ├── Generate quote                                                  │
│      └── quotations.created_by = user.id                                │
│                                                                          │
│  11. PROFORMA INVOICE                                                    │
│      └── Create invoice                                                  │
│                                                                          │
│  12. AGREEMENT                                                           │
│      ├── Create agreement                                                │
│      └── agreements.created_by = user.id                                │
│                                                                          │
│  13. PAYMENT VERIFICATION                                                │
│      ├── Verify first installment                                       │
│      └── payments.verified_by = user.id                                 │
│                                                                          │
│  14. KICKOFF REQUEST                                                     │
│      ├── Create handoff to consulting                                   │
│      └── kickoff_requests.created_by = user.id                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    HANDOFF TO CONSULTING                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  15. CONSULTING ACCEPTS KICKOFF                                          │
│      ├── PM/Principal Consultant accepts                                │
│      ├── Project created with status="active"                           │
│      └── SOW inherited to project                                        │
│                                                                          │
│  16. CONSULTANT ASSIGNMENT                                               │
│      ├── PM assigns consultants                                         │
│      └── project_assignments.consultant_id = consultant's user.id       │
│                                                                          │
│  17. NOTIFICATIONS                                                       │
│      ├── Sales Manager notified of acceptance                           │
│      └── notifications.user_id = "user-001"                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FINANCE LINKS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PAYROLL (Monthly - Auto-linked)                                        │
│  ├── salary_slips generated using CTC structure                         │
│  ├── Leaves deducted from salary                                        │
│  └── Expenses added to reimbursement                                    │
│                                                                          │
│  PAYMENT TRACKING                                                        │
│  ├── Sales Manager's deals tracked                                      │
│  ├── Project payments linked to agreement                               │
│  └── Reminders sent (Sales notified)                                    │
│                                                                          │
│  APPROVALS                                                               │
│  ├── Leave approvals (to reporting manager)                             │
│  ├── Expense approvals (to reporting manager)                           │
│  └── Visible in Approvals Center                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## GAPS IDENTIFIED

### Current Gaps in the System:

| Gap | Impact | Status |
|-----|--------|--------|
| **Role not editable after Grant Access** | If wrong role assigned, need to revoke and re-grant | GAP |
| **No HR Manager role in onboarding dropdown** | HR Manager must be created via Admin Masters or direct DB | GAP |
| **No 'manager' role in dropdown** | General Manager role not selectable | GAP |
| **Department doesn't auto-filter pages** | Only ROLE matters, not department | BY DESIGN |
| **Sales incentive not linked to closed deals** | Payment tracking exists but no incentive calculation | GAP |

### Missing Roles in Onboarding Form:
```javascript
// Current roles in HROnboarding.js:
const ROLES = [
  'consultant', 'senior_consultant', 'lead_consultant', 
  'principal_consultant', 'project_manager',
  'executive', 'account_manager',   // ← Sales roles
  'hr_executive'                     // ← Only HR Executive, no HR Manager!
];

// MISSING:
// - 'hr_manager'
// - 'manager'
// - 'admin'
```

---

## Summary: What Links What

```
┌─────────────────────────────────────────────────────────────┐
│              EMPLOYEE "Sales Manager"                        │
│              Role: account_manager                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LINKED BY employee_id:          LINKED BY user_id:         │
│  ├── attendance                  ├── leads.created_by       │
│  ├── leave_requests              ├── leads.assigned_to      │
│  ├── salary_slips                ├── meetings.created_by    │
│  ├── ctc_structures              ├── pricing_plans          │
│  ├── expenses                    ├── sow.created_by         │
│  ├── bank_change_requests        ├── quotations             │
│  ├── employee_documents          ├── agreements             │
│  └── travel_claims               ├── kickoff_requests       │
│                                  └── notifications           │
│                                                              │
│  PAGE ACCESS (by role):                                      │
│  ├── My Workspace (all roles)                               │
│  ├── Sales section (because account_manager in SALES_ROLES) │
│  └── NOT HR, NOT Admin (unless role changes)                │
│                                                              │
│  APPROVAL CHAIN (by reporting_manager_id):                  │
│  └── Leaves/Expenses → Reporting Manager → Admin            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Answer to Your Question:

1. **Does department input affect page access?** NO - Only ROLE determines page access
2. **Does role selection affect page access?** YES - This is the KEY
3. **Is designation used for access?** NO - Display only
4. **Is reporting manager used?** YES - For approval chains, not page access
5. **Auto-linked to Payroll?** YES - via employee_id after CTC approved
6. **Auto-linked to Attendance?** YES - via employee_id
7. **Auto-linked to Leaves?** YES - via employee_id
8. **Auto-linked to Finance?** YES - via deals they create (user_id)
9. **Auto-linked to Consulting?** YES - via kickoff they create (user_id)
