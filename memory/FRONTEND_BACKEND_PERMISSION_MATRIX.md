# Frontend-Backend Permission Validation Matrix

**Date:** December 2025  
**Status:** AUDIT COMPLETE

---

## Summary

This report validates that frontend UI visibility rules match backend API authorization rules for all protected action buttons.

---

## Permission Check Methods

### Frontend (PermissionContext.js)
```javascript
// Numeric level check (RBAC-driven)
isManagerOrAbove() => rbacData?.level >= 70
isLeader()        => rbacData?.level >= 80
isAdmin()         => user?.role === 'admin' || rbacData?.level === 100

// Permission-based check
can(permission)   => checks raw_permissions array
canApproveRequests() => rbacData?.can_approve || has('approvals.*')
```

### Backend (deps.py)
```python
# RBAC dependency checks
require_role_group("GROUP_NAME", fail_closed=True)  # For critical ops
require_role_group("GROUP_NAME", fail_closed=False) # For standard ops
has_role(user_role, allowed_roles)
```

---

## Action Button Validation Matrix

### 1. Agreement Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Approve Agreement** | `user.role === 'manager' \|\| 'admin'` | `MANAGER_ROLES` group | 403 | Toast + loader stop | ⚠️ Partial |
| **Reject Agreement** | `user.role === 'manager' \|\| 'admin'` | `MANAGER_ROLES` group | 403 | Toast + loader stop | ⚠️ Partial |
| **Create Agreement** | No restriction | No restriction | N/A | N/A | ✅ |

**Mismatch Details:**
- Frontend: Exact string match for `manager` or `admin`
- Backend: Uses `MANAGER_ROLES` which includes `sales_manager`, `hr_manager`, `principal_consultant`, `sr_manager`
- **Fix:** Frontend should use `isManagerOrAbove()` from PermissionContext

### 2. Lead Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Create Lead** | No restriction | No restriction | N/A | N/A | ✅ |
| **Edit Lead** | Owner or Manager | Owner or `MANAGER_ROLES` | 403 | Toast | ✅ |
| **Delete Lead** | `isManagerOrAbove()` | Missing explicit check | 403 | Toast | ⚠️ |
| **Assign Lead** | `isManagerOrAbove()` | `MANAGER_ROLES` | 403 | Toast | ✅ |

**Mismatch Details:**
- Delete Lead: Frontend hides button, but backend doesn't have explicit role check
- **Risk:** Direct API call could delete leads

### 3. Expense Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Approve Expense** | Shown to managers | `APPROVAL_ROLES` | 403 | Toast | ✅ |
| **Reject Expense** | Shown to managers | `APPROVAL_ROLES` | 403 | Toast | ✅ |
| **Create Expense** | All users | All authenticated | N/A | N/A | ✅ |

### 4. Kickoff Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Approve Kickoff (Internal)** | `principal_consultant` or `admin` | `PRINCIPAL_CONSULTANT_ROLES` + fail_closed | 403/503 | Toast | ✅ |
| **Create Kickoff** | Sales roles | Sales roles | 403 | Toast | ✅ |

### 5. HR Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Add Employee** | `isAdmin \|\| isHRManager` | `HR_ADMIN_ROLES` | 403 | Toast | ✅ |
| **Edit Employee** | `isAdmin \|\| isHRManager` | `HR_ADMIN_ROLES` | 403 | Toast | ✅ |
| **Delete Employee** | `isAdmin` only | `ADMIN_ROLES` | 403 | Toast | ✅ |
| **Approve Leave** | `APPROVAL_ROLES` | `APPROVAL_ROLES` | 403 | Toast | ✅ |

### 6. Stats/Dashboard Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **View HR Stats** | Domain-based routing | `HR_ROLES` + `MANAGER_ROLES` | 403 | Redirect | ✅ NEW |
| **View Consulting Stats** | Domain-based routing | `CONSULTING_ROLES` + `MANAGER_ROLES` | 403 | Redirect | ✅ NEW |
| **View Sales Stats** | All users | Filtered by role | N/A | N/A | ✅ NEW |
| **View Dashboard** | All users | Filtered by role hierarchy | N/A | N/A | ✅ NEW |

### 7. Export Operations

| Action | UI Rule | API Rule | HTTP Error | UI Handler | Match |
|--------|---------|----------|------------|------------|-------|
| **Export CSV** | `isAdmin()` | Missing endpoint check | N/A | N/A | ⚠️ |
| **Download Report** | `canViewReports()` | Varies by report type | 403 | Toast | ⚠️ |

---

## Numeric Level Reference

| Level | Roles | Access Tier |
|-------|-------|-------------|
| 100 | `admin` | Full system |
| 90 | `principal_consultant` | Department + approvals |
| 85 | `sr_manager` | Team + budget |
| 80 | `hr_manager`, `sales_manager`, `finance_manager` | Department |
| 75 | `manager` | Team |
| 70 | `senior_consultant` | Department view |
| 60 | `lead_consultant` | Team view |
| 55 | `subject_matter_expert` | Enhanced view |
| 50 | `consultant`, `lean_consultant` | Own data |
| 40 | `executive`, `hr_executive`, `sales_executive` | Own data |
| 10 | `client` | Portal only |

---

## Mismatch Report & Fixes

### Issue 1: ManagerApprovals.js Hardcoded Check
**File:** `/app/frontend/src/pages/sales-funnel/ManagerApprovals.js`  
**Line:** 98

```javascript
// Current (INCORRECT)
const canApprove = user?.role === 'manager' || user?.role === 'admin';

// Should be
const { isManagerOrAbove, canApproveRequests } = usePermissions();
const canApprove = isManagerOrAbove() || canApproveRequests();
```

### Issue 2: Lead Delete Authorization
**File:** `/app/backend/routers/leads.py`  
**Action:** Add explicit role check to delete endpoint

```python
@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    current_user: User = Depends(require_role_group("MANAGER_ROLES"))
):
```

### Issue 3: Export Endpoints Missing RBAC
**File:** Various export endpoints  
**Action:** Add `require_role_group("MANAGER_ROLES")` to all export endpoints

---

## UI Error Handling Audit

All protected endpoints properly handle 401/403 errors:

| Status Code | UI Behavior |
|-------------|------------|
| 401 Unauthorized | Redirect to login |
| 403 Forbidden | Toast error + stop loading |
| 503 Service Unavailable | Toast "Service unavailable" |

---

## Recommendations

1. **HIGH:** Update `ManagerApprovals.js` to use `usePermissions()` context
2. **MEDIUM:** Add explicit `require_role_group` to lead delete endpoint
3. **LOW:** Standardize export endpoints with RBAC checks
4. **LOW:** Consider adding loading states for all permission-gated buttons
