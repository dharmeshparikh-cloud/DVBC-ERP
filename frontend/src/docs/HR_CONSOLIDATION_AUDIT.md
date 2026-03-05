# HR Module Consolidation - Dependency & Workflow Audit
## Date: December 2025

---

## 1. LEAVE SETTINGS AUDIT

### Current State: TWO SEPARATE PAGES

#### Page A: `AttendanceLeaveSettings.js` (`/attendance-leave-settings`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Global attendance timing + Basic leave quotas |
| **APIs Used** | `/api/attendance/policy`, `/api/settings/leave-policy`, `/api/attendance/consulting-employees`, `/api/attendance/policy/custom` |
| **Collections** | `settings` (type: attendance_policy), `employee_attendance_policies` |
| **Query Keys** | `['/api/attendance/policy']`, `['/api/settings/leave-policy']` |
| **Features** | Working hours config, Grace period, Late penalty, Consulting timing, Custom attendance policies, Basic leave quotas (CL/SL/EL) |

#### Page B: `LeavePolicySettings.js` (`/leave-policy-settings`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Advanced scope-based leave policies with hierarchy |
| **APIs Used** | `/api/leave-policies`, `/api/masters/departments`, `/api/employees` |
| **Collections** | `leave_policies` (separate collection!) |
| **Query Keys** | `['leave-policies']`, `['masters', 'departments']` |
| **Features** | Scope-based policies (Company/Department/Role/Employee), Leave types with quotas, Carry forward, Encashment, Pro-rata, Accrual |

### OVERLAP ANALYSIS
| Feature | AttendanceLeaveSettings | LeavePolicySettings |
|---------|------------------------|---------------------|
| Casual Leave Quota | ✅ (basic: 12 days) | ✅ (per policy scope) |
| Sick Leave Quota | ✅ (basic: 6 days) | ✅ (per policy scope) |
| Earned Leave Quota | ✅ (basic: 15 days) | ✅ (per policy scope) |
| Carry Forward | ✅ (global toggle) | ✅ (per leave type) |
| Attendance Config | ✅ | ❌ |
| Department Scope | ❌ | ✅ |
| Role Scope | ❌ | ✅ |
| Encashment | ❌ | ✅ |
| Accrual Types | ❌ | ✅ |

### CONSOLIDATION DECISION: KEEP SEPARATE (Renamed)
- **AttendanceLeaveSettings** → Rename to "Attendance Settings" (remove leave section)
- **LeavePolicySettings** → Keep as "Leave Policy Settings" (already comprehensive)
- Move basic leave quotas from AttendanceLeaveSettings to LeavePolicySettings default policy

---

## 2. PERMISSION MANAGEMENT AUDIT

### Current State: THREE PLACES

#### Page A: `EmployeePermissions.js` (`/employee-permissions`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Module-level RBAC (Sales/HR/Finance/Admin features) |
| **APIs Used** | `/api/employees/all`, `/api/roles`, `/api/permission-change-requests`, `/api/employee-permissions/{id}` |
| **Collections** | `employees`, `roles`, `permission_change_requests`, `employee_permissions` |
| **Query Keys** | `['employees-permissions']`, `['roles-list']`, `['permission-change-requests']` |
| **Features** | View/Create/Edit/Delete per module feature, Approval workflow for changes |

#### Page B: `PasswordManagement.js` (`/password-management`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Portal access + Password management |
| **APIs Used** | `/api/employees/all`, `/api/users-with-roles`, `/api/auth/admin/reset-employee-password`, `/api/auth/admin/toggle-employee-access`, `/api/employees/{id}/grant-access` |
| **Collections** | `employees`, `users` |
| **Query Keys** | `['employees', 'with-access']` |
| **Features** | Reset password, Enable/Disable access, Grant new access |

#### Page C: `Employees.js` (inline buttons)
| Feature | Location |
|---------|----------|
| Grant Access | Edit dialog |
| Revoke Access | Action buttons |
| Link to User | Action buttons |

### OVERLAP ANALYSIS
| Feature | EmployeePermissions | PasswordManagement | Employees.js |
|---------|--------------------|--------------------|--------------|
| View all employees | ✅ | ✅ | ✅ |
| Grant portal access | ❌ | ✅ | ✅ |
| Revoke portal access | ❌ | ✅ | ✅ |
| Reset password | ❌ | ✅ | ❌ |
| Module permissions | ✅ | ❌ | ❌ |
| Permission approval | ✅ | ❌ | ❌ |

### CONSOLIDATION DECISION: MERGE INTO ONE PAGE
- Create `EmployeeAccessPermissions.js` with tabs:
  - Tab 1: Portal Access (from PasswordManagement)
  - Tab 2: Module Permissions (from EmployeePermissions)
  - Tab 3: Pending Approvals (from EmployeePermissions)
- Keep Employees.js buttons as quick actions (link to consolidated page)

---

## 3. HR INPUT AUDIT

### Current State: TWO SEPARATE PAGES

#### Page A: `HRLeaveInput.js` (`/hr-leave-input`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Apply leave on behalf of employees, Bulk credit |
| **APIs Used** | `/api/employees`, `/api/leave-requests/all`, `/api/attendance/hr/apply-leave-for-employee`, `/api/attendance/hr/bulk-leave-credit`, `/api/leave-requests/{id}/rm-approve` |
| **Collections** | `employees`, `leave_requests` |
| **Query Keys** | `['/api/employees']`, `['/api/leave-requests/all']` |

#### Page B: `HRAttendanceInput.js` (`/hr-attendance-input`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Mark attendance, Auto-validate, Apply penalties |
| **APIs Used** | `/api/attendance/policy`, `/api/employees`, `/api/attendance/policy/custom`, `/api/attendance/hr/employee-attendance-input/{month}`, `/api/attendance/auto-validate`, `/api/attendance/apply-penalties`, `/api/attendance/hr/mark-attendance-bulk` |
| **Collections** | `employees`, `attendance`, `employee_attendance_policies` |
| **Query Keys** | `['/api/attendance/policy']`, `['/api/employees']` |

### OVERLAP ANALYSIS
| Feature | HRLeaveInput | HRAttendanceInput |
|---------|-------------|-------------------|
| Employee selection | ✅ | ✅ |
| Date selection | ✅ | ✅ |
| Bulk operations | ✅ | ✅ |
| Approval actions | ✅ | ❌ |
| Penalty management | ❌ | ✅ |
| Custom policies | ❌ | ✅ |

### CONSOLIDATION DECISION: MERGE INTO TABBED PAGE
- Create `HRManualEntry.js` with tabs:
  - Tab 1: Leave Input (from HRLeaveInput)
  - Tab 2: Attendance Input (from HRAttendanceInput)
  - Shared employee selector header

---

## 4. EMPLOYEE WORKFLOWS RENAME

### Current: `EmployeeWorkflows.js` (`/employee-workflows`)
| Aspect | Details |
|--------|---------|
| **Purpose** | Handle Transfer, Promotion, CTC Revision, Hierarchy Change, Bank Change |
| **APIs Used** | `/api/governance/pending-requests`, `/api/employees/all`, `/api/employees/departments/list`, `/api/governance/requests/{id}/approve`, `/api/governance/requests/{id}/reject` |
| **Collections** | `governance_requests`, `employees` |

### RENAME DECISION
- Rename to "Employee Change Requests" for clarity
- Route unchanged: `/employee-workflows`
- Only UI label change in navigation

---

## 5. IMPLEMENTATION PLAN

### Step 1: Create Audit Document ✅
This document

### Step 2: Update AttendanceLeaveSettings
- Remove leave policy section (lines dealing with `leavePolicy` state)
- Rename page title to "Attendance Settings"
- Keep attendance timing, grace periods, consulting config, custom policies

### Step 3: Create EmployeeAccessPermissions.js
- Tabbed interface combining PasswordManagement + EmployeePermissions
- Preserve all existing API calls
- Preserve all React Query keys

### Step 4: Create HRManualEntry.js
- Tabbed interface combining HRLeaveInput + HRAttendanceInput
- Shared employee selector
- Preserve all existing API calls

### Step 5: Update Navigation
- Change "Employee Permissions" → "Employee Access & Permissions" (new route)
- Change "Password Management" → redirect to new page (keep old route working)
- Change "Employee Workflows" → "Employee Change Requests" (label only)
- Change "Attendance & Leave Settings" → "Attendance Settings" (label only)
- Change "HR Leave Input" + "HR Attendance Input" → "HR Manual Entry" (new route)
- Keep all old routes as aliases/redirects

### Step 6: Preserve Old Routes
All existing routes must continue working:
- `/employee-permissions` → New tabbed page (Permissions tab)
- `/password-management` → New tabbed page (Access tab)
- `/attendance-leave-settings` → Same page (renamed)
- `/hr-leave-input` → New tabbed page (Leave tab)
- `/hr-attendance-input` → New tabbed page (Attendance tab)

---

## 6. DATA INTEGRITY CHECKS

### Collections NOT Modified
- `employees` ✅
- `users` ✅
- `roles` ✅
- `leave_policies` ✅
- `leave_requests` ✅
- `attendance` ✅
- `employee_attendance_policies` ✅
- `employee_permissions` ✅
- `permission_change_requests` ✅
- `governance_requests` ✅
- `settings` ✅

### API Endpoints NOT Modified
All endpoints listed above remain unchanged.

### Payroll Integration
- Leave policy encashment formulas → Unchanged (in `leave_policies` collection)
- LOP deduction → Unchanged (uses leave balance from `leave_requests`)
- Attendance penalties → Unchanged (uses `attendance` collection)

---

## 7. RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Old bookmarks break | Keep old routes as redirects |
| Query cache issues | Use same query keys in consolidated pages |
| Permission checks fail | Copy exact permission logic from original pages |
| Data not loading | Preserve exact API call patterns |

---

## 8. TESTING CHECKLIST

- [ ] AttendanceSettings saves attendance policy
- [ ] LeavePolicySettings manages all leave policies
- [ ] EmployeeAccessPermissions - Access tab grants/revokes access
- [ ] EmployeeAccessPermissions - Access tab resets password
- [ ] EmployeeAccessPermissions - Permissions tab edits module permissions
- [ ] EmployeeAccessPermissions - Approvals tab approves/rejects
- [ ] HRManualEntry - Leave tab applies leave for employee
- [ ] HRManualEntry - Attendance tab marks bulk attendance
- [ ] Old routes redirect correctly
- [ ] Payroll integration unchanged
