# Employee Data Linkage - How 1 Employee Connects to All Functions

## The 3 Identity Keys

Every employee has **3 identifiers** that link them across all modules:

```
┌─────────────────────────────────────────────────────────────┐
│                    EMPLOYEE RECORD                          │
├─────────────────────────────────────────────────────────────┤
│  id: "uuid-abc-123"         ← Internal system ID            │
│  employee_id: "EMP001"      ← HR display code               │
│  user_id: "uuid-xyz-789"    ← Login account (if granted)    │
└─────────────────────────────────────────────────────────────┘
```

## Complete Data Flow Diagram

```
                                    ┌──────────────────┐
                                    │  HR ONBOARDING   │
                                    │  (Entry Point)   │
                                    └────────┬─────────┘
                                             │ Creates
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                              EMPLOYEES COLLECTION                               │
│  {                                                                              │
│    id: "uuid-abc-123",           ← Primary Key (used everywhere)               │
│    employee_id: "EMP001",        ← HR Code (for display)                       │
│    user_id: null → "uuid-xyz",   ← Linked when portal access granted           │
│    full_name: "John Doe",                                                      │
│    email: "john@company.com",                                                  │
│    department: "Consulting",                                                   │
│    designation: "Senior Consultant",                                           │
│    role: "consultant",           ← System role for permissions                 │
│    level: "manager",             ← Executive/Manager/Leader                    │
│    reporting_manager_id: "uuid-mgr-456",                                       │
│    ...                                                                         │
│  }                                                                              │
└────────────────────────────────────────────────────────────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
              ▼                              ▼                              ▼
    ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
    │  GRANT ACCESS   │           │  HR FUNCTIONS   │           │ SALES/CONSULTING│
    │  (Portal Login) │           │                 │           │                 │
    └────────┬────────┘           └────────┬────────┘           └────────┬────────┘
             │                             │                             │
             ▼                             │                             │
┌────────────────────────┐                 │                             │
│    USERS COLLECTION    │                 │                             │
│  {                     │                 │                             │
│    id: "uuid-xyz-789", │◄────────────────┼─────────────────────────────┘
│    email: "john@...",  │                 │         user_id links
│    role: "consultant", │                 │
│    employee_id: "EMP001"│                │
│  }                     │                 │
└────────────────────────┘                 │
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
```

## Module-by-Module Linkage

### 1. HR Module Links (via `employee_id` or `id`)

| Collection | Link Field | Purpose |
|------------|------------|---------|
| `attendance` | `employee_id` | Daily attendance records |
| `leave_requests` | `employee_id` | Leave applications |
| `salary_slips` | `employee_id` | Monthly payslips |
| `ctc_structures` | `employee_id` | CTC design & approval |
| `expenses` | `employee_id` | Expense claims |
| `bank_change_requests` | `employee_id` | Bank detail changes |
| `employee_documents` | `employee_id` | Uploaded documents |
| `timesheets` | `employee_id` | Time logs |
| `travel_claims` | `employee_id` | Travel reimbursements |

### 2. Sales Module Links (via `user_id` or `created_by`)

| Collection | Link Field | Purpose |
|------------|------------|---------|
| `leads` | `created_by`, `assigned_to` | Lead ownership |
| `meetings` | `created_by`, `assigned_to` | Meeting scheduling |
| `pricing_plans` | `created_by` | Who created the plan |
| `sow` | `created_by` | SOW authorship |
| `quotations` | `created_by` | Quote generation |
| `agreements` | `created_by`, `signed_by_user_id` | Agreement tracking |
| `kickoff_requests` | `created_by` | Handoff initiator |

### 3. Consulting Module Links (via `consultant_id` or `user_id`)

| Collection | Link Field | Purpose |
|------------|------------|---------|
| `project_assignments` | `consultant_id` | Project team membership |
| `project_tasks` | `assigned_to` | Task ownership |
| `sow_items` | `assigned_consultant_id` | SOW item assignment |
| `timesheets` | `user_id` | Time entries |
| `consulting_meetings` | `participants[]` | Meeting attendance |

### 4. Admin/System Links

| Collection | Link Field | Purpose |
|------------|------------|---------|
| `notifications` | `user_id` | Personal notifications |
| `approval_requests` | `submitted_by`, `approved_by` | Approval workflow |
| `security_logs` | `user_id` | Audit trail |
| `role_requests` | `employee_id`, `submitted_by` | Role changes |

---

## Sync Mechanism: How Data Stays Connected

### Step 1: Employee Created (HR Onboarding)
```javascript
// HR creates employee
{
  id: "emp-uuid-001",           // Generated
  employee_id: "EMP001",        // Auto-generated
  user_id: null,                // No login yet
  full_name: "John Doe",
  department: "Consulting",
  role: "consultant"
}
```

### Step 2: Portal Access Granted
```javascript
// HR grants access → Creates USER record
// employees.user_id is updated to link them

// User record created:
{
  id: "user-uuid-001",
  email: "john@company.com",
  employee_id: "EMP001",        // Cross-reference
  role: "consultant"
}

// Employee record updated:
{
  id: "emp-uuid-001",
  user_id: "user-uuid-001"      // NOW LINKED!
}
```

### Step 3: All Future Actions Use These IDs
```javascript
// Attendance (uses employee_id):
{ employee_id: "emp-uuid-001", date: "2025-02-18", status: "present" }

// Leave Request (uses user context):
{ employee_id: "emp-uuid-001", user_id: "user-uuid-001", days: 2 }

// Project Assignment (uses consultant_id = user.id):
{ project_id: "proj-001", consultant_id: "user-uuid-001" }

// Notification (uses user_id):
{ user_id: "user-uuid-001", message: "You've been assigned..." }
```

---

## Visual: One Employee Across All Functions

```
                         JOHN DOE (EMP001)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐         ┌────▼────┐
   │   HR    │          │  SYSTEM   │         │  WORK   │
   │ Records │          │  Access   │         │ Output  │
   └────┬────┘          └─────┬─────┘         └────┬────┘
        │                     │                    │
   ┌────┴────────────┐   ┌────┴────────┐    ┌─────┴─────────┐
   │ • Attendance    │   │ • Login     │    │ • Projects    │
   │ • Leaves        │   │ • Notifs    │    │ • Tasks       │
   │ • Salary Slips  │   │ • Approvals │    │ • Timesheets  │
   │ • CTC           │   │ • Audit Log │    │ • Meetings    │
   │ • Expenses      │   │ • Permissions│   │ • SOW Items   │
   │ • Bank Details  │   │             │    │               │
   │ • Documents     │   │             │    │               │
   └─────────────────┘   └─────────────┘    └───────────────┘
        │                     │                    │
        └─────────────────────┼────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   LINKED VIA:     │
                    │ • employee_id     │
                    │ • user_id         │
                    │ • id (primary)    │
                    └───────────────────┘
```

---

## API Queries - How System Finds Employee Data

### Get Everything for One Employee:
```python
# 1. Get employee base record
employee = db.employees.find_one({"id": employee_id})

# 2. Get their user account (if exists)
user = db.users.find_one({"id": employee["user_id"]})

# 3. Get HR data (using employee.id)
attendance = db.attendance.find({"employee_id": employee_id})
leaves = db.leave_requests.find({"employee_id": employee_id})
salary_slips = db.salary_slips.find({"employee_id": employee_id})
ctc = db.ctc_structures.find_one({"employee_id": employee_id, "status": "active"})
expenses = db.expenses.find({"employee_id": employee_id})

# 4. Get work data (using user.id if they have portal access)
if employee.get("user_id"):
    projects = db.project_assignments.find({"consultant_id": employee["user_id"]})
    tasks = db.project_tasks.find({"assigned_to": employee["user_id"]})
    timesheets = db.timesheets.find({"user_id": employee["user_id"]})
    notifications = db.notifications.find({"user_id": employee["user_id"]})
```

---

## Department Handoff Sync

### Sales → Consulting (Project Handoff)
```
Sales Person (EMP002) creates Lead
         │
         ▼
Lead → Pricing → SOW → Agreement → Kickoff Request
         │                              │
         │                              ▼
         │                    Consulting PM accepts
         │                              │
         │                              ▼
         │                    Project Created
         │                              │
         │                              ▼
         └──────────────────► Consultant (EMP001) Assigned
                                        │
                              project_assignments:
                              {
                                project_id: "proj-001",
                                consultant_id: "user-uuid-001"  ← John's user.id
                              }
```

### HR → Finance (Payroll Sync)
```
HR Manager approves CTC for EMP001
         │
         ▼
ctc_structures: { employee_id: "emp-uuid-001", status: "active", ... }
         │
         ▼
Monthly Payroll Runs
         │
         ▼
salary_slips: { employee_id: "emp-uuid-001", month: "Feb 2025", ... }
         │
         ▼
Employee can view at /my-salary-slips (filtered by their employee_id)
```

---

## Key Takeaways

1. **Single Source of Truth**: `employees` collection is the master record
2. **Two-Way Link**: `employees.user_id` ↔ `users.employee_id` 
3. **All HR data**: Uses `employee_id` (the internal UUID, not EMP001)
4. **All work data**: Uses `user_id` (the login account ID)
5. **Sync happens automatically**: When you grant portal access, the link is established
6. **Department handoff**: Through shared IDs in `created_by`, `assigned_to`, `consultant_id`
