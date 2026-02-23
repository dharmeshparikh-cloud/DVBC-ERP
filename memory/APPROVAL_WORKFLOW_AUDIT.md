# Comprehensive Approval Workflow Audit - NETRA ERP

**Date:** December 2025  
**Status:** COMPLETE

---

## Executive Summary

This audit identifies **12 distinct approval workflows** across the NETRA ERP application:
1. Agreement Approval (Principal Consultant)
2. Kickoff Request Approval (Internal + Client)
3. Leave Request Approval
4. Expense Claim Approval (Multi-level)
5. Bank Details Change Approval (HR → Admin)
6. Profile Change Request Approval
7. SOW/Scope Task Approval
8. Attendance Approval (HR)
9. CTC Structure Approval
10. Document/Communication Approval
11. Project Completion Approval
12. Generic Approval Queue

---

## 1. Agreement Approval Workflow

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Sales Funnel - Agreements |
| **Route/URL** | `/agreements`, `/sales-funnel/agreement/:id` |
| **Frontend Page** | `ManagerApprovals.js`, `Agreements.js` |
| **Action** | Approve sales agreement before sending to client |
| **Status Workflow** | `draft` → `pending_approval` → `approved` → `sent_to_client` → `signed` |
| **Who Can Approve** | `AGREEMENT_APPROVE_ROLES`: admin, principal_consultant |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO (role check on `/approve` endpoint) |
| **Auth Source** | RBAC DB (`get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)`) |
| **Dependencies** | Agreement must be in `draft` status to submit for approval |
| **Notifications** | N/A (should be added) |
| **Audit Trail** | ✅ `approved_by`, `approved_at`, `submitted_for_approval_by`, `submitted_for_approval_at` |
| **Multi-Level** | ❌ Single level (PC/Admin only) |

### API Endpoints
```
PATCH /api/agreements/{id}/submit-for-approval  → Changes to pending_approval
PATCH /api/agreements/{id}/approve              → PC/Admin approves
PATCH /api/agreements/{id}/reject               → PC/Admin rejects
GET   /api/agreements/pending-approval          → List pending for managers
```

### Source Files
- Backend: `/app/backend/routers/agreements.py` (lines 239-354)
- Frontend: `/app/frontend/src/pages/sales-funnel/ManagerApprovals.js`

---

## 2. Kickoff Request Approval (Dual-Level)

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Sales Funnel - Kickoff Requests |
| **Route/URL** | `/kickoff-requests`, `/sales-funnel/kickoff/:id` |
| **Frontend Page** | `KickoffRequests.js`, `GoLiveDashboard.js` |
| **Action** | Approve project kickoff before starting delivery |
| **Status Workflow** | `pending` → `internal_approved` → `client_approved` / `accepted` |
| **Who Can Approve** | Internal: `PRINCIPAL_CONSULTANT_ROLES` (admin, principal_consultant)<br>Client: Via email token |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | RBAC DB (`get_role_group("PRINCIPAL_CONSULTANT_ROLES", fail_closed=True)`) |
| **Dependencies** | Lead must have completed all sales stages |
| **Notifications** | ✅ Email to client, WebSocket notification to sales |
| **Audit Trail** | ✅ `internal_approved_by`, `internal_approved_at`, `client_approved_by`, `client_confirmed_start_date` |
| **Multi-Level** | ✅ **YES** - Internal (PC) then Client |

### API Endpoints
```
POST  /api/kickoff-requests                       → Create request
PATCH /api/kickoff-requests/{id}/internal-approve → PC approves internally
GET   /api/kickoff-requests/client-approve/{token}  → Client approval page
POST  /api/kickoff-requests/client-approve/{token}/confirm → Client confirms
PATCH /api/kickoff-requests/{id}/return           → PC returns for revision
PATCH /api/kickoff-requests/{id}/reject           → PC rejects
```

### Source Files
- Backend: `/app/backend/routers/kickoff.py` (lines 650-1430)
- Frontend: `/app/frontend/src/pages/KickoffRequests.js`

---

## 3. Leave Request Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | HR - Leave Management |
| **Route/URL** | `/my-leaves`, `/leave-management`, `/hr/leave-input` |
| **Frontend Page** | `MyLeaves.js`, `LeaveManagement.js`, `HRLeaveInput.js` |
| **Action** | Approve employee leave request |
| **Status Workflow** | `pending` → `approved` / `rejected` / `withdrawn` |
| **Who Can Approve** | `APPROVAL_ROLES`: admin, manager, hr_manager, principal_consultant |
| **Backend Enforced** | ⚠️ PARTIAL (rm-approve endpoint lacks strict role check) |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ⚠️ POSSIBLE (any authenticated user can call `/rm-approve`) |
| **Auth Source** | Hardcoded `APPROVAL_ROLES` constant |
| **Dependencies** | Leave request must be in `pending` status |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `rm_action_by`, `rm_action_at`, `rm_comments` |
| **Multi-Level** | ❌ Single level |

### Security Issue ⚠️
The `/leave-requests/{id}/rm-approve` endpoint does **not** verify that the current user is actually the reporting manager or has approval rights. Any authenticated user can approve leaves.

### API Endpoints
```
POST  /api/leave-requests                   → Submit leave request
POST  /api/leave-requests/{id}/rm-approve   → Approve/reject (⚠️ missing auth)
POST  /api/leave-requests/{id}/withdraw     → Employee withdraws
GET   /api/leave-requests/all               → List all (HR only)
```

### Source Files
- Backend: `/app/backend/routers/leave_requests.py` (lines 144-182)
- Frontend: `/app/frontend/src/pages/MyLeaves.js`

---

## 4. Expense Claim Approval (Multi-Level)

| Attribute | Value |
|-----------|-------|
| **Page/Module** | HR - Expenses |
| **Route/URL** | `/expenses`, `/expense-approvals`, `/my-expenses` |
| **Frontend Page** | `Expenses.js`, `ExpenseApprovals.js`, `MyExpenses.js` |
| **Action** | Approve employee expense reimbursement |
| **Status Workflow** | `draft` → `pending` → `hr_approved` → `admin_approved` / `approved` / `rejected` |
| **Who Can Approve** | Level 1: `HR_ROLES` (admin, hr_manager, hr_executive)<br>Level 2 (>₹2000): Admin only |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Hardcoded `APPROVAL_ROLES`, `HR_ROLES` constants |
| **Dependencies** | Expense must be submitted (not draft), amount threshold determines levels |
| **Notifications** | ✅ Email + WebSocket to approvers |
| **Audit Trail** | ✅ `approval_chain` array with step, approver, status, timestamps |
| **Multi-Level** | ✅ **YES** - HR → Admin for amounts > ₹2000 |

### Approval Threshold
- **< ₹2000**: Single-level (HR Manager approves directly)
- **≥ ₹2000**: Multi-level (HR Manager → Admin)

### API Endpoints
```
POST  /api/expenses/{id}/submit             → Submit for approval
POST  /api/expenses/{id}/approve            → HR/Admin approves
POST  /api/expenses/{id}/reject             → HR/Admin rejects
POST  /api/expenses/{id}/request-revision   → Request changes
GET   /api/expenses/pending                 → List pending for approver
```

### Source Files
- Backend: `/app/backend/routers/expenses.py` (lines 275-400, 615-800)
- Frontend: `/app/frontend/src/pages/ExpenseApprovals.js`

---

## 5. Bank Details Change Approval (Multi-Level)

| Attribute | Value |
|-----------|-------|
| **Page/Module** | HR - Bank Details Change Requests |
| **Route/URL** | `/bank-details-change`, `/hr/bank-change-requests` |
| **Frontend Page** | `BankDetailsChangeRequest.js`, `HRDashboard.js` |
| **Action** | Approve employee bank details change |
| **Status Workflow** | `pending` → `hr_approved` → `admin_approved` / `rejected` |
| **Who Can Approve** | Level 1: `HR_ADMIN_ROLES` (admin, hr_manager)<br>Level 2: `ADMIN_ROLES` (admin only) |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Hardcoded `HR_ADMIN_ROLES`, `ADMIN_ROLES` |
| **Dependencies** | Proof document must be uploaded |
| **Notifications** | ✅ Creates notification for next approver |
| **Audit Trail** | ✅ `hr_approved_by`, `hr_approved_at`, `admin_approved_by`, `admin_approved_at` |
| **Multi-Level** | ✅ **YES** - HR Manager → Admin |

### API Endpoints
```
POST  /api/hr/bank-change-requests/{id}/approve → HR approves (creates admin notification)
POST  /api/hr/bank-change-requests/{id}/reject  → HR rejects
GET   /api/hr/admin-bank-change-requests        → Admin sees HR-approved requests
```

### Source Files
- Backend: `/app/backend/routers/hr.py` (lines 68-180)
- Frontend: `/app/frontend/src/pages/BankDetailsChangeRequest.js`

---

## 6. Profile Change Request Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | My Details - Profile Changes |
| **Route/URL** | `/my-details`, `/hr/change-requests` |
| **Frontend Page** | `MyDetails.js`, `HRDashboard.js` |
| **Action** | Approve employee profile field changes |
| **Status Workflow** | `pending` → `approved` / `rejected` |
| **Who Can Approve** | `HR_ROLES`: admin, hr_manager, hr_executive |
| **Backend Enforced** | ⚠️ PARTIAL (approval endpoint may be missing) |
| **UI-Only** | ⚠️ POSSIBLE |
| **API Bypass Possible** | ⚠️ UNCLEAR |
| **Auth Source** | RBAC DB for listing, hardcoded for actions |
| **Dependencies** | None |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `updated_at` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
POST  /api/my/change-request      → Submit profile change
GET   /api/my/change-requests     → User's requests
GET   /api/my/pending-approvals   → Manager's pending items
```

### Source Files
- Backend: `/app/backend/routers/my.py` (lines 196-270)
- Frontend: `/app/frontend/src/pages/MyDetails.js`

---

## 7. SOW/Scope Task Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Consulting - SOW Builder |
| **Route/URL** | `/consulting/scope`, `/sales-funnel/sow-builder` |
| **Frontend Page** | `SOWBuilder.js`, `ConsultingScopeView.js`, `SOWChangeRequests.js` |
| **Action** | Approve scope changes/additions |
| **Status Workflow** | `pending` → `approved` / `rejected` / `changes_requested` |
| **Who Can Approve** | `MANAGER_ROLES`: admin, manager, sr_manager, sales_manager, hr_manager, principal_consultant |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Hardcoded `MANAGER_ROLES` |
| **Dependencies** | Scope must exist |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `actioned_by`, `actioned_at`, `action_comment` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
POST  /api/approvals                        → Create scope approval request
POST  /api/approvals/{id}/action            → Approve/reject/request changes
GET   /api/approvals/scope-tasks/pending    → List pending scope approvals
POST  /api/approvals/scope-task/{id}/action → Act on scope task
```

### Source Files
- Backend: `/app/backend/routers/approvals.py`
- Frontend: `/app/frontend/src/pages/sales-funnel/SOWBuilder.js`

---

## 8. Attendance Approval (HR)

| Attribute | Value |
|-----------|-------|
| **Page/Module** | HR - Attendance |
| **Route/URL** | `/hr/attendance-approvals`, `/hr/attendance-input` |
| **Frontend Page** | `HRAttendanceApprovals.js`, `HRAttendanceInput.js` |
| **Action** | Approve attendance corrections/adjustments |
| **Status Workflow** | `pending_approval` → `approved` / `rejected` |
| **Who Can Approve** | `HR_ROLES`: admin, hr_manager, hr_executive |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | RBAC DB (`get_role_group("HR_ROLES")`) |
| **Dependencies** | Attendance record must exist |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `approver_id`, `approval_status` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
POST  /api/attendance/hr/approve-all        → Bulk approve
```

### Source Files
- Backend: `/app/backend/routers/attendance.py`
- Frontend: `/app/frontend/src/pages/hr/HRAttendanceApprovals.js`

---

## 9. CTC Structure Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | HR - CTC Designer |
| **Route/URL** | `/ctc-designer`, `/payroll` |
| **Frontend Page** | `CTCDesigner.js`, `Payroll.js` |
| **Action** | Approve CTC structure changes |
| **Status Workflow** | `pending` → `approved` / `rejected` / `superseded` |
| **Who Can Approve** | `ADMIN_ROLES`: admin only |
| **Backend Enforced** | ✅ TRUE (admin-only endpoints) |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Hardcoded `ADMIN_ROLES` |
| **Dependencies** | Previous structure must be superseded |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `approved_by`, `approved_at`, `superseded_at` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
POST  /api/ctc/structures                   → Create structure
GET   /api/ctc/pending                      → List pending approvals
POST  /api/ctc/structures/{id}/approve      → Approve (auto if admin creates)
POST  /api/ctc/structures/{id}/reject       → Reject
```

### Source Files
- Backend: `/app/backend/routers/ctc.py` (lines 270-540)
- Frontend: `/app/frontend/src/pages/CTCDesigner.js`

---

## 10. Document/Communication Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Sales - Client Communications |
| **Route/URL** | `/agreements/:id/send` |
| **Frontend Page** | `Agreements.js` |
| **Action** | Approve sending agreements/documents to clients |
| **Status Workflow** | N/A (action gate) |
| **Who Can Approve** | `AGREEMENT_APPROVE_ROLES`: admin, principal_consultant |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | RBAC DB (`get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)`) |
| **Dependencies** | Agreement must be approved first |
| **Notifications** | ✅ Email to client |
| **Audit Trail** | ✅ `sent_at`, `sent_by` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
POST  /api/agreements/{id}/send-to-client   → PC sends to client
```

### Source Files
- Backend: `/app/backend/routers/agreements.py` (lines 402-470)

---

## 11. Chat Message Approval

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Team Chat |
| **Route/URL** | `/chat` |
| **Frontend Page** | `Chat.js` |
| **Action** | Approve restricted messages/requests |
| **Status Workflow** | `pending` → `approved` / `rejected` |
| **Who Can Approve** | Group admins, channel owners |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Dynamic (group/channel ownership) |
| **Dependencies** | User must be group admin |
| **Notifications** | ✅ Real-time via WebSocket |
| **Audit Trail** | ✅ `approved_by`, `approved_at`, `rejected_by`, `rejection_reason` |
| **Multi-Level** | ❌ Single level |

### Source Files
- Backend: `/app/backend/routers/chat.py` (lines 360-400)

---

## 12. Generic Approval Queue

| Attribute | Value |
|-----------|-------|
| **Page/Module** | Approvals Center |
| **Route/URL** | `/approvals-center` |
| **Frontend Page** | `ApprovalsCenter.js` |
| **Action** | Generic approval for various entities |
| **Status Workflow** | `pending` → `approved` / `rejected` / `changes_requested` |
| **Who Can Approve** | Assigned approver or managers |
| **Backend Enforced** | ✅ TRUE |
| **UI-Only** | ❌ FALSE |
| **API Bypass Possible** | ❌ NO |
| **Auth Source** | Dynamic (approver_id field) or `MANAGER_ROLES` |
| **Dependencies** | Approval must be assigned to user |
| **Notifications** | ❌ Not implemented |
| **Audit Trail** | ✅ `actioned_by`, `actioned_at`, `action_comment` |
| **Multi-Level** | ❌ Single level |

### API Endpoints
```
GET   /api/approvals/pending                → My pending approvals
GET   /api/approvals                        → All approvals (managers)
GET   /api/approvals/my-requests            → Requests I submitted
POST  /api/approvals/{id}/action            → Take action
```

### Source Files
- Backend: `/app/backend/routers/approvals.py`
- Frontend: `/app/frontend/src/pages/ApprovalsCenter.js`

---

## Security Issues & Recommendations

### Critical Issues

| Issue | Location | Risk | Fix Priority |
|-------|----------|------|--------------|
| Leave approval lacks auth | `/leave-requests/{id}/rm-approve` | Any user can approve leaves | 🔴 **P0** |
| Expense approval uses hardcoded roles | `expenses.py` | Breaks RBAC migration | 🟡 **P1** |
| Bank change uses hardcoded roles | `hr.py` | Breaks RBAC migration | 🟡 **P1** |
| Missing notifications | Multiple workflows | Users miss approvals | 🟢 **P2** |

### Recommended Fixes

#### 1. Fix Leave Approval Authorization (P0)
```python
# leave_requests.py - Add role check
@router.post("/{leave_id}/rm-approve")
async def rm_approve_leave(leave_id: str, data: dict = None, current_user: User = Depends(get_current_user)):
    db = get_db()
    leave = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    
    # NEW: Check if user is authorized to approve
    approval_roles = get_role_group("APPROVAL_ROLES", fail_closed=True)
    if not approval_roles or not has_role(current_user.role, approval_roles):
        # Check if user is the reporting manager
        employee = await db.employees.find_one({"id": leave["employee_id"]}, {"reporting_manager_id": 1, "_id": 0})
        if employee.get("reporting_manager_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to approve this leave")
```

#### 2. Migrate Expense Approval to RBAC (P1)
```python
# expenses.py - Replace hardcoded checks
approval_roles = get_role_group("APPROVAL_ROLES", fail_closed=True)
if not approval_roles or not has_role(current_user.role, approval_roles):
    raise HTTPException(status_code=403, detail="Not authorized to approve expenses")
```

---

## Summary Matrix

| Workflow | Multi-Level | Backend Enforced | RBAC Migrated | Notifications | Audit Trail |
|----------|-------------|------------------|---------------|---------------|-------------|
| Agreement Approval | ❌ | ✅ | ✅ | ❌ | ✅ |
| Kickoff Approval | ✅ | ✅ | ✅ | ✅ | ✅ |
| Leave Approval | ❌ | ⚠️ | ❌ | ❌ | ✅ |
| Expense Approval | ✅ | ✅ | ❌ | ✅ | ✅ |
| Bank Change | ✅ | ✅ | ❌ | ✅ | ✅ |
| Profile Change | ❌ | ⚠️ | ❌ | ❌ | ⚠️ |
| SOW/Scope | ❌ | ✅ | ❌ | ❌ | ✅ |
| Attendance | ❌ | ✅ | ✅ | ❌ | ✅ |
| CTC Structure | ❌ | ✅ | ❌ | ❌ | ✅ |
| Document Send | ❌ | ✅ | ✅ | ✅ | ✅ |
| Chat Messages | ❌ | ✅ | N/A | ✅ | ✅ |
| Generic Queue | ❌ | ✅ | ❌ | ❌ | ✅ |

---

## Frontend Pages with Approval UI

| Page | Route | Purpose |
|------|-------|---------|
| `ManagerApprovals.js` | `/sales-funnel/manager-approvals` | Agreement approvals for PC/Admin |
| `ExpenseApprovals.js` | `/expense-approvals` | Expense claim approvals |
| `ApprovalsCenter.js` | `/approvals-center` | Unified approval dashboard |
| `KickoffRequests.js` | `/kickoff-requests` | Kickoff approval workflow |
| `MyLeaves.js` | `/my-leaves` | Leave request submission |
| `LeaveManagement.js` | `/leave-management` | Leave approval for managers |
| `HRAttendanceApprovals.js` | `/hr/attendance-approvals` | Attendance corrections |
| `HRLeaveInput.js` | `/hr/leave-input` | HR direct leave application |
| `BankDetailsChangeRequest.js` | `/bank-details-change` | Bank change submission |
| `SOWChangeRequests.js` | `/consulting/sow-change-requests` | Scope change approvals |
| `CTCDesigner.js` | `/ctc-designer` | CTC structure approvals |
