# Stats Dashboard Security Audit Report

**Date:** December 2025  
**Scope:** `/api/stats/dashboard` endpoint and related stats endpoints  
**Status:** 🔴 CRITICAL ISSUES FOUND

---

## Executive Summary

The `/stats/dashboard` endpoint has **critical security vulnerabilities** that allow data leakage and bypass RBAC controls. The endpoint was not migrated during the RBAC refactor and still uses legacy string-based role checks.

---

## 1. Authorization Logic Audit

### Current State (PROBLEMATIC)

```python
# Line 18-24 of stats.py
@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    query = {}
    if current_user.role != UserRole.ADMIN:  # ❌ LEGACY STRING CHECK
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
```

### Issues Found:

| Issue | Severity | Description |
|-------|----------|-------------|
| **Legacy Role Check** | 🔴 CRITICAL | Uses `current_user.role != UserRole.ADMIN` instead of RBAC service |
| **Binary Access Model** | 🔴 CRITICAL | Only Admin vs Non-Admin, no role hierarchy |
| **Missing RBAC Integration** | 🔴 HIGH | Does not use `require_role_group()` or `has_role()` |
| **No Fail-Closed** | 🟡 MEDIUM | Endpoint accessible even if RBAC service fails |

---

## 2. Data Scope Per Role Analysis

### Current Behavior (INCORRECT):

| Role | Current Access | Expected Access |
|------|----------------|-----------------|
| `admin` | All company data | ✅ All company data |
| `principal_consultant` | Only own data | ❌ Should see team + department data |
| `hr_manager` | Only own data | ❌ Should see all employee-related data |
| `sales_manager` | Only own data | ❌ Should see all sales team data |
| `manager` | Only own data | ❌ Should see team data |
| `executive` | Only own data | ✅ Correct |
| `consultant` | Only own data | ✅ Correct |

### Critical Gap:
**Non-admin managers cannot see their team's statistics**, breaking dashboard usability for middle management.

---

## 3. Company-Wide Statistics Access

### Vulnerability: Data Leakage via Aggregations

The `/stats/hr` endpoint at **lines 52-79** exposes company-wide statistics to ALL authenticated users:

```python
@router.get("/hr")
async def get_hr_stats(current_user: User = Depends(get_current_user)):
    # ❌ NO ROLE CHECK - Any user sees total employee count
    total_employees = await db.employees.count_documents({"is_active": True})
    # ... returns company-wide HR metrics
```

### Affected Endpoints:

| Endpoint | Vulnerability |
|----------|--------------|
| `GET /stats/hr` | Exposes total employees, pending leaves, expenses to all users |
| `GET /stats/consulting` | Exposes total projects, consultants count to all users |
| `GET /stats/sales` | Partially protected, but leaks total revenue via unfiltered aggregation |

---

## 4. Numeric Role Level Compatibility

### Issue: Mixing String Checks with Numeric Levels

The RBAC service defines numeric levels:
```python
# From rbac_service.py
"admin": level=100
"principal_consultant": level=90
"hr_manager": level=80
"manager": level=75
```

But stats.py uses string comparisons:
```python
if current_user.role != UserRole.ADMIN:  # ❌ Ignores level hierarchy
```

### Frontend Expectation:
```javascript
// PermissionContext.js line 121
const isManagerOrAbove = () => {
    if (rbacData?.level >= 70) return true;  // ✅ Uses numeric level
```

**MISMATCH:** Frontend shows data based on level >= 70, backend only allows exact `admin` role.

---

## 5. Legacy String-Based Role Checks

### Files Still Using Legacy Checks:

| File | Line | Legacy Pattern |
|------|------|----------------|
| `stats.py` | 23 | `current_user.role != UserRole.ADMIN` |
| `stats.py` | 32 | `current_user.role != UserRole.ADMIN` |
| `stats.py` | 163 | `user.role in ALL_DATA_ACCESS_ROLES` |
| `stats.py` | 259 | `can_see_all_data(current_user)` |
| `stats.py` | 543 | `has_role(current_user.role, hr_roles)` (partially migrated) |

---

## 6. Query Filter Analysis

### Missing Ownership/Hierarchy Filters:

**Problem:** When non-admin users access stats, the query filters are inconsistent:

```python
# Line 87-91 - Correct pattern but wrong role check
sales_manager_roles = get_role_group("SALES_MANAGER_ROLES", fail_closed=False)
if not has_role(current_user.role, sales_manager_roles):
    query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
```

**Missing:** Reporting hierarchy filter. Managers should see their direct reports' data.

### Required Filter Pattern:
```python
# Should include team hierarchy
if is_manager and not is_all_data_role:
    team_ids = await get_team_member_ids(current_user.id)
    query['$or'] = [
        {"assigned_to": current_user.id},
        {"created_by": current_user.id},
        {"assigned_to": {"$in": team_ids}}  # Team filter
    ]
```

---

## 7. Performance Risks

### Large Aggregation Concerns:

| Endpoint | Risk | Impact |
|----------|------|--------|
| `GET /stats/sales-dashboard-enhanced` | 6+ month MoM aggregation | High DB load |
| Leaderboard pipeline | Scans all closed leads | O(n) performance |
| Revenue aggregation | Unindexed aggregation on `agreements` | Slow on large datasets |

### Mitigation Needed:
- Add collection indexes on `status`, `created_at`, `assigned_to`
- Consider materialized views or caching for dashboard stats
- Limit MoM data to last 3 months by default

---

## 8. Data Leakage Scenarios

### Scenario 1: HR Metrics Exposure
- **Actor:** Any authenticated user (e.g., `executive`)
- **Action:** `GET /api/stats/hr`
- **Result:** Sees total employees, pending leaves, expense counts
- **Risk:** Competitive intelligence leak

### Scenario 2: Revenue Exposure
- **Actor:** Non-sales consultant
- **Action:** `GET /api/stats/sales`
- **Result:** Sees `total_revenue` from signed agreements
- **Risk:** Financial data exposure

### Scenario 3: Project Count Leak
- **Actor:** Any authenticated user
- **Action:** `GET /api/stats/consulting`
- **Result:** Sees total projects, consultant count
- **Risk:** Business metrics exposure

---

## Required Fixes

### Fix 1: Migrate `/stats/dashboard` to RBAC

```python
from .deps import get_role_group, has_role, require_role_group

@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    db = get_db()
    
    # Use RBAC service for role checks
    all_data_roles = get_role_group("ALL_DATA_ACCESS_ROLES", fail_closed=False) or ["admin", "hr_manager", "principal_consultant"]
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or []
    
    query = {}
    if not has_role(current_user.role, all_data_roles):
        if has_role(current_user.role, manager_roles):
            # Managers see their team's data
            team_ids = await get_team_member_ids(current_user.id)
            team_ids.append(current_user.id)
            query['$or'] = [
                {"assigned_to": {"$in": team_ids}},
                {"created_by": {"$in": team_ids}}
            ]
        else:
            # Regular users see only their own data
            query['$or'] = [
                {"assigned_to": current_user.id},
                {"created_by": current_user.id}
            ]
```

### Fix 2: Protect HR Stats Endpoint

```python
@router.get("/hr")
async def get_hr_stats(current_user: User = Depends(get_current_user)):
    db = get_db()
    
    # RBAC check for HR access
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or []
    
    if not hr_roles or (not has_role(current_user.role, hr_roles) and not has_role(current_user.role, manager_roles)):
        raise HTTPException(status_code=403, detail="HR or Manager access required")
```

### Fix 3: Protect Consulting Stats

```python
@router.get("/consulting")
async def get_consulting_stats(current_user: User = Depends(get_current_user)):
    db = get_db()
    
    # Only consulting team and managers can see consulting stats
    consulting_roles = get_role_group("CONSULTING_ROLES", fail_closed=False) or []
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or []
    
    if not has_role(current_user.role, consulting_roles + manager_roles):
        raise HTTPException(status_code=403, detail="Consulting or Manager access required")
```

### Fix 4: Add ALL_DATA_ACCESS_ROLES to RBAC

```python
# In rbac_service.py DEFAULT_ROLE_GROUPS
"ALL_DATA_ACCESS_ROLES": ["admin", "hr_manager", "principal_consultant"],
```

---

## Frontend-Backend Permission Matrix

### Action Button Validation:

| Button | UI Rule | API Rule | Match? |
|--------|---------|----------|--------|
| Approve Agreement | `user.role === 'manager' \|\| 'admin'` | `MANAGER_ROLES` check | ⚠️ Partial |
| Create Lead | No restriction | No restriction | ✅ |
| Delete Lead | `isManagerOrAbove()` | Missing check | ❌ |
| Export Data | `isAdmin()` | Missing endpoint | ❌ |
| Approve Expense | `APPROVAL_ROLES` | `APPROVAL_ROLES` | ✅ |
| Approve Kickoff | `principal_consultant` | `PRINCIPAL_CONSULTANT_ROLES` | ✅ |

### Mismatch Details:

1. **Delete Lead**: Frontend hides button for non-managers, but backend may not enforce this
2. **Export Data**: Frontend has export buttons without corresponding RBAC-protected endpoints
3. **Approve Agreement**: Frontend uses exact string match, backend uses `MANAGER_ROLES` which includes more roles

---

## Expected Behavior Per Role

| Role | Dashboard Data | HR Stats | Sales Stats | Consulting Stats |
|------|---------------|----------|-------------|------------------|
| `admin` | All | All | All | All |
| `hr_manager` | All employees | All | Own | - |
| `principal_consultant` | Department | View | Team | All |
| `sales_manager` | Team | - | Team | - |
| `manager` | Team | View | Team | View |
| `executive` | Own | - | Own | - |
| `consultant` | Own | - | - | Own |

---

## Implementation Priority

1. 🔴 **P0**: Fix `/stats/hr` and `/stats/consulting` authorization (data leakage)
2. 🔴 **P0**: Add `ALL_DATA_ACCESS_ROLES` to RBAC service
3. 🟡 **P1**: Migrate `/stats/dashboard` to use RBAC hierarchy
4. 🟡 **P1**: Add team hierarchy filters for managers
5. 🟢 **P2**: Add performance indexes for stats aggregations
