# ERP Data Architecture Audit - Multiple Sources of Truth Analysis
## Date: December 2025

---

## EXECUTIVE SUMMARY

This audit identifies **8 critical data ownership issues** and **5 moderate duplications** across the ERP system. The most severe issues involve Employee/User data synchronization and denormalized project/client information.

### Risk Severity Legend
- 🔴 **CRITICAL**: Data frequently out of sync, causes bugs
- 🟠 **HIGH**: Potential for inconsistency, requires vigilance  
- 🟡 **MODERATE**: Denormalization for performance, acceptable with care
- 🟢 **LOW**: Intentional design, well-managed

---

## 1. EMPLOYEE vs USER DATA (🔴 CRITICAL)

### Problem
Employee identity data is stored in **TWO collections** with overlapping but inconsistent fields.

### Collections
| Field | `employees` | `users` | Authoritative Source |
|-------|-------------|---------|---------------------|
| email | ✅ | ✅ | `employees` |
| full_name | first_name + last_name | full_name | `employees` |
| role | ✅ | ✅ | **CONFLICT** |
| department | ✅ | ✅ | **CONFLICT** |
| designation | ✅ | ✅ | `employees` |
| reporting_manager_id | ✅ | ✅ | `employees` |
| level | ✅ | ✅ | **CONFLICT** |
| is_active | ✅ | ✅ | **CONFLICT** |

### Conflict Scenarios
1. **Role change in `employees` doesn't update `users`** → User has old permissions
2. **Department change in `employees` doesn't update `users`** → Wrong access controls
3. **Employee deactivated but user remains active** → Security risk

### Current Sync Points
- `grant_access()` in employees.py copies fields to users
- No automatic sync on employee updates
- No event-driven propagation

### RECOMMENDATION
```
AUTHORITATIVE: employees collection
DERIVED: users collection (auth-only copy)

Solution:
1. Remove business fields from users (keep only: id, email, hashed_password, is_active)
2. Create get_employee_for_auth() that joins employees + users
3. Add MongoDB change stream or event triggers for sync
```

---

## 2. LEAVE BALANCE DATA (🔴 CRITICAL)

### Problem
Leave balances are stored in **multiple places** with different calculation methods.

### Locations
| Location | Purpose | Update Trigger |
|----------|---------|----------------|
| `employees.leave_balance` | Embedded balance | Manual update |
| `leave_balance_snapshots` | Year-end snapshots | Annual job |
| `leave_requests` | Calculated from approved | On approval |
| `leave_policies` | Entitled amounts | Policy config |

### Conflict Scenarios
1. `employees.leave_balance.used_casual` ≠ SUM(approved casual leaves)
2. Year-end carry forward not reflected in employee balance
3. Policy change doesn't recalculate existing balances

### RECOMMENDATION
```
AUTHORITATIVE: 
- Entitled: leave_policies (scope-based)
- Used: CALCULATED from leave_requests (approved only)

REMOVE:
- employees.leave_balance (denormalized, gets stale)

CREATE:
- Real-time calculation function: get_leave_balance(employee_id)
- Caches result with TTL
```

---

## 3. CLIENT/LEAD DATA (🟠 HIGH)

### Problem
Client information is copied into multiple collections when deals progress.

### Data Flow
```
leads.company, leads.email
    ↓ (copied on agreement creation)
agreements.client_name, agreements.client_email
    ↓ (copied on SOW creation)
enhanced_sow.client_name, enhanced_sow.client_email
    ↓ (copied on kickoff)
kickoff_requests.client_name
    ↓ (copied on project creation)
projects.client_name, projects.client_email
```

### Conflict Scenarios
1. Client email updated in lead, but old email in project
2. Company name corrected in lead, agreements show old name
3. No way to bulk update client info across entities

### RECOMMENDATION
```
AUTHORITATIVE: leads collection (single client record)

Solution:
1. Store only lead_id in downstream collections
2. Create client_details view/lookup function
3. For historical accuracy, keep client_name_at_creation for audit
```

---

## 4. PROJECT ASSIGNMENT DATA (🟠 HIGH)

### Problem
Project team membership stored in multiple places.

### Locations
| Collection | Field | Purpose |
|------------|-------|---------|
| `projects` | `team` (embedded array) | Quick access |
| `consultant_assignments` | Separate docs | Detailed tracking |
| `timesheets` | `project_id`, `employee_id` | Work logs |

### Conflict Scenarios
1. Employee removed from project.team but assignment record exists
2. Assignment end_date passed but still in project.team
3. Timesheet submitted for project user not assigned to

### RECOMMENDATION
```
AUTHORITATIVE: consultant_assignments collection

Solution:
1. Remove projects.team (derive from assignments)
2. Add is_active, start_date, end_date to assignments
3. Validate timesheets against active assignments
```

---

## 5. CTC/SALARY DATA (🟠 HIGH)

### Problem
Salary information stored in multiple places with different update cycles.

### Locations
| Collection | Field | When Updated |
|------------|-------|--------------|
| `employees` | `current_ctc`, `annual_ctc` | On CTC change |
| `ctc_structures` | Full breakdown | On structure creation |
| `salary_slips` | Monthly calculation | Monthly payroll |
| `onboarding_submissions` | `offered_ctc` | During onboarding |

### Conflict Scenarios
1. `employees.current_ctc` ≠ latest `ctc_structures` amount
2. Salary slip uses old structure after CTC revision
3. Onboarding CTC not transferred to employee record

### RECOMMENDATION
```
AUTHORITATIVE: ctc_structures collection (versioned)

Solution:
1. employees.current_ctc becomes calculated field
2. Add effective_date to ctc_structures for versioning
3. Salary slip references structure_id, not raw values
```

---

## 6. ATTENDANCE POLICY DATA (🟡 MODERATE)

### Problem
Attendance rules stored at multiple levels.

### Locations
| Location | Scope | Priority |
|----------|-------|----------|
| `settings` (attendance_policy) | Company-wide | Default |
| `employee_attendance_policies` | Per-employee | Override |
| `employees` (consulting role check) | Implicit | Conditional |

### Assessment
This is **acceptable denormalization** for performance. The cascade is:
1. Check employee_attendance_policies first
2. Fall back to global settings
3. Apply consulting modifier if applicable

### Status: 🟢 ACCEPTABLE (with documentation)

---

## 7. ROLE/PERMISSION DATA (🟡 MODERATE)

### Problem
Role definitions in multiple collections.

### Locations
| Collection | Purpose |
|------------|---------|
| `roles` | Legacy role definitions |
| `rbac_roles` | New RBAC system |
| `rbac_role_groups` | Role groupings |
| `employee_permissions` | Per-employee overrides |

### Assessment
This appears to be a **migration in progress** from legacy to RBAC. Both systems currently active.

### RECOMMENDATION
```
Complete RBAC migration:
1. Migrate all legacy roles to rbac_roles
2. Remove roles collection
3. Update all has_role() calls to use RBAC service
```

---

## 8. ONBOARDING → EMPLOYEE TRANSITION (🟡 MODERATE)

### Problem
Candidate data copied from onboarding to employee on completion.

### Data Flow
```
onboarding_submissions
    ↓ (copied on go-live approval)
employees (new record created)
```

### Fields Copied
- Personal info (name, email, phone, DOB, etc.)
- Bank details
- Document URLs
- Address info

### Assessment
This is **intentional and correct** - onboarding is a staging area. However:
- No backward link from employee to onboarding_submission
- If onboarding data corrected after go-live, employee not updated

### RECOMMENDATION
```
Add reference field:
employees.onboarding_submission_id → links back to source

For audit: Keep onboarding_submission as historical record
```

---

## 9. DOCUMENT/FILE REFERENCES (🟡 MODERATE)

### Problem
Document URLs stored in multiple collections.

### Locations
- `employees.documents[]` - Employee documents
- `onboarding_submissions.documents` - Onboarding uploads
- `agreements.document_url` - Signed agreements
- `enhanced_sow.attachment_url` - SOW attachments
- `projects.documents[]` - Project files

### Assessment
Documents are entity-specific. This is **acceptable** as long as:
- URLs are absolute (not relative)
- File storage has consistent naming
- Orphan cleanup job exists

### Status: 🟢 ACCEPTABLE (verify cleanup job exists)

---

## 10. NOTIFICATION DATA (🟢 LOW)

### Problem
Notifications reference multiple entity types.

### Fields
```
notifications.entity_type = "lead" | "project" | "employee" | etc.
notifications.entity_id = UUID of referenced entity
```

### Assessment
This is **correct polymorphic design**. Entity data not duplicated.

### Status: 🟢 ACCEPTABLE

---

## PRIORITY ACTION ITEMS

### P0 - CRITICAL (Fix within 2 sprints)
1. **Employee ↔ User Sync**: Add event-driven sync or merge collections
2. **Leave Balance**: Move to calculated-on-read pattern

### P1 - HIGH (Fix within 1 month)
3. **Client Data**: Add lead_id references, reduce copying
4. **Project Team**: Single source in consultant_assignments
5. **CTC Versioning**: Add effective_date to structures

### P2 - MODERATE (Backlog)
6. **RBAC Migration**: Complete and remove legacy roles
7. **Onboarding Link**: Add backward reference field

---

## IMPLEMENTATION NOTES

### Safe Refactoring Pattern
```python
# Phase 1: Add new field/collection alongside old
# Phase 2: Update all writes to populate both
# Phase 3: Update all reads to prefer new source
# Phase 4: Migration script for historical data
# Phase 5: Remove old field/collection
```

### Testing Requirements
- Unit tests for each sync operation
- Integration tests for data consistency
- Regression tests for dependent modules

---

## APPENDIX: Collection Relationships

```
┌─────────────┐     ┌─────────────┐
│  employees  │────→│    users    │ (auth copy)
└─────────────┘     └─────────────┘
       │
       ├───→ leave_requests
       ├───→ attendance
       ├───→ ctc_structures
       └───→ consultant_assignments ───→ projects ───→ leads (client)
                                              │
                                              └───→ agreements
                                              └───→ enhanced_sow
                                              └───→ kickoff_requests
```

---

## SIGN-OFF

Audit performed: December 2025
Next review: Q1 2026 (after P0 fixes)
