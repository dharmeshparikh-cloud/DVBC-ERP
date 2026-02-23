# RBAC Fallback Behavior Analysis - Security Audit
## Critical Endpoint Analysis

---

## EXECUTIVE SUMMARY

| Finding | Severity | Status |
|---------|----------|--------|
| **PERMIT ON ERROR PATH FOUND** | 🔴 CRITICAL | In `has_role()` function |
| Hardcoded role arrays bypassed in some endpoints | 🟡 MEDIUM | Mixed usage |
| Some endpoints don't use RBAC service at all | 🟡 MEDIUM | Direct string comparison |

---

## 1. CRITICAL FINDING: PERMIT ON ERROR IN `has_role()`

### Location: `/app/backend/routers/rbac_service.py` (lines 504-511)

```python
def has_role(self, user_role: str, required_roles: List[str]) -> bool:
    """Check if user role is in required roles list"""
    if not user_role:
        return False  # ✅ GOOD: Deny if no role
    # Admin always has access
    if user_role == "admin":
        return True   # ⚠️ RISK: Hardcoded admin bypass
    return user_role in required_roles  # ✅ Simple list check
```

**RISK ASSESSMENT:**
- If `required_roles` list is empty (DB lookup failure), non-admin users are denied ✅
- BUT: The `get_role_group()` function has a fallback that returns defaults

### Fallback Chain Analysis:

```
deps.py::require_roles(allowed_roles)
    └── deps.py::has_role(user_role, allowed_roles)
        └── rbac_service.py::rbac.has_role(user_role, allowed_roles)
            └── Simple list check: user_role in allowed_roles
```

**VERDICT:** ✅ **FAIL-CLOSED** for `require_roles()`
- If allowed_roles is passed directly, it uses that list
- No DB lookup occurs in this path

---

## 2. CRITICAL FINDING: `get_role_group()` HAS FAIL-OPEN BEHAVIOR

### Location: `/app/backend/routers/rbac_service.py` (lines 471-491)

```python
def get_role_group(self, group_name: str) -> List[str]:
    # First check cache (from database)
    if group_name in _permission_cache:
        return _permission_cache[group_name]
    
    # ⚠️ FAIL-OPEN: Falls back to hardcoded defaults
    if group_name in DEFAULT_ROLE_GROUPS:
        log_fallback_event(...)  # Only logs, doesn't deny
        return DEFAULT_ROLE_GROUPS[group_name]  # ⚠️ RETURNS DATA
    
    # Unknown group - returns empty
    logger.error(f"RBAC: Unknown role group '{group_name}' requested")
    return []  # ✅ This would deny, but only for unknown groups
```

**VERDICT:** 🟡 **FAIL-OPEN TO DEFAULTS**
- Known groups fall back to hardcoded arrays (PERMIT)
- Only unknown groups return empty (DENY)

---

## 3. ENDPOINT-BY-ENDPOINT ANALYSIS

### 3.1 Lead Status Change

**File:** `/app/backend/routers/leads.py`
**Authorization:** Lines 138, 201, 309

```python
# Line 138 - Lead assignment
if current_user.role not in ['admin', 'hr_manager']:
    raise HTTPException(status_code=403, ...)

# Uses hardcoded array, NOT RBAC service
```

**RBAC DB Failure Behavior:**
- ✅ **FAIL-CLOSED**: Direct string comparison, no DB dependency
- ⚠️ **NOT USING RBAC**: This bypasses the entire RBAC system

---

### 3.2 Agreement Approve

**File:** `/app/backend/routers/agreements.py`
**Authorization:** Lines 25, 287, 326

```python
# Line 25 - Constant definition
AGREEMENT_APPROVE_ROLES = ["admin", "principal_consultant"]  # Hardcoded

# Line 287 - Approval check
if current_user.role not in AGREEMENT_APPROVE_ROLES:
    raise HTTPException(status_code=403, ...)
```

**RBAC DB Failure Behavior:**
- ✅ **FAIL-CLOSED**: Uses hardcoded constant from this file, not deps.py
- ⚠️ **NOT USING RBAC**: This bypasses the RBAC service entirely

---

### 3.3 Kickoff Approve (Internal)

**File:** `/app/backend/routers/kickoff.py`
**Authorization:** Lines 556, 663, 1410

```python
# Line 26 - Import
from .deps import get_db, SALES_EXECUTIVE_ROLES, PRINCIPAL_CONSULTANT_ROLES

# Line 663 - Approval check
if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:
    raise HTTPException(status_code=403, ...)
```

**PRINCIPAL_CONSULTANT_ROLES in deps.py:**
```python
PRINCIPAL_CONSULTANT_ROLES = ["admin", "principal_consultant"]
```

**RBAC DB Failure Behavior:**
- ✅ **FAIL-CLOSED**: Uses hardcoded constant from deps.py
- ⚠️ **NOT USING RBAC**: Does not call `get_role_group("PRINCIPAL_CONSULTANT_ROLES")`

---

### 3.4 Project Close/Complete

**File:** `/app/backend/routers/project_completion.py`
**Authorization:** Line 249-254

```python
allowed_roles = [UserRole.ADMIN, "principal_consultant", "principal_consultant"]  # Duplicate!
if current_user.role not in allowed_roles:
    raise HTTPException(status_code=403, ...)
```

**RBAC DB Failure Behavior:**
- ✅ **FAIL-CLOSED**: Hardcoded list in function
- ⚠️ **BUG**: "principal_consultant" is duplicated in list
- ⚠️ **NOT USING RBAC**: Direct string comparison

---

### 3.5 Payments/Export (PnL)

**File:** `/app/backend/routers/project_pnl.py`
**Authorization:** Lines 32, 167, 447

```python
if current_user.role not in MANAGER_ROLES:
    raise HTTPException(status_code=403, ...)
```

**MANAGER_ROLES in deps.py:**
```python
MANAGER_ROLES = ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"]
```

**RBAC DB Failure Behavior:**
- ✅ **FAIL-CLOSED**: Uses hardcoded constant from deps.py
- ⚠️ **NOT USING RBAC**: Does not call `get_role_group("MANAGER_ROLES")`

---

## 4. SUMMARY TABLE

| Endpoint | File:Line | Auth Method | DB Failure | Using RBAC? |
|----------|-----------|-------------|------------|-------------|
| Lead assign | leads.py:138 | Hardcoded list | ✅ DENY | ❌ NO |
| Agreement approve | agreements.py:287 | Local constant | ✅ DENY | ❌ NO |
| Kickoff approve | kickoff.py:663 | deps.py constant | ✅ DENY | ❌ NO |
| Project complete | project_completion.py:250 | Inline list | ✅ DENY | ❌ NO |
| PnL export | project_pnl.py:32 | deps.py constant | ✅ DENY | ❌ NO |

---

## 5. THE REAL RISK: `require_role_group()` IS FAIL-OPEN

### Location: `/app/backend/routers/deps.py` (lines 222-243)

```python
def require_role_group(group_name: str):
    async def role_checker(current_user = Depends(get_current_user_from_token)):
        allowed_roles = get_role_group(group_name)  # ⚠️ This can fallback to defaults
        if not allowed_roles:
            # Only triggers for UNKNOWN groups
            raise HTTPException(status_code=500, detail="Role configuration error")
        # If fallback to defaults, this will permit based on hardcoded list
        if not has_role(current_user.role, allowed_roles):
            raise HTTPException(status_code=403, ...)
```

**IF `get_role_group()` FALLS BACK:**
- It returns `DEFAULT_ROLE_GROUPS[group_name]` (hardcoded)
- The permission check continues with hardcoded values
- **THIS IS FAIL-OPEN TO DEFAULTS, NOT FAIL-CLOSED**

---

## 6. CRITICAL FIXES REQUIRED

### Fix 1: Make `get_role_group()` Fail-Closed

```python
# CURRENT (FAIL-OPEN):
def get_role_group(self, group_name: str) -> List[str]:
    if group_name in _permission_cache:
        return _permission_cache[group_name]
    if group_name in DEFAULT_ROLE_GROUPS:
        log_fallback_event(...)
        return DEFAULT_ROLE_GROUPS[group_name]  # ⚠️ PERMITS
    return []

# RECOMMENDED (FAIL-CLOSED):
def get_role_group(self, group_name: str, fail_closed: bool = True) -> List[str]:
    if group_name in _permission_cache:
        return _permission_cache[group_name]
    
    # Log the fallback attempt
    log_fallback_event(...)
    
    if fail_closed:
        logger.critical(f"RBAC FAIL-CLOSED: Group '{group_name}' not in cache")
        raise RBACUnavailableError(f"Role group '{group_name}' unavailable")
    
    # Only fall back if explicitly allowed
    return DEFAULT_ROLE_GROUPS.get(group_name, [])
```

### Fix 2: Add Health Check Before Critical Operations

```python
async def require_rbac_healthy():
    """Dependency that ensures RBAC service is operational"""
    if not rbac.is_cache_valid():
        logger.critical("RBAC cache invalid - denying access")
        raise HTTPException(
            status_code=503,
            detail="Authorization service temporarily unavailable"
        )
```

### Fix 3: Migrate Critical Endpoints to RBAC Service

```python
# BEFORE (bypasses RBAC):
if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:

# AFTER (uses RBAC with fail-closed):
if not rbac.has_role(current_user.role, rbac.get_role_group("PRINCIPAL_CONSULTANT_ROLES")):
```

---

## 7. IMMEDIATE ACTION ITEMS

| Priority | Action | Risk if Not Done |
|----------|--------|------------------|
| 🔴 P0 | Add `fail_closed` mode to `get_role_group()` | Potential unauthorized access on DB failure |
| 🔴 P0 | Add RBAC health check to critical endpoints | Silent permission failures |
| 🟡 P1 | Migrate all hardcoded role checks to RBAC | Inconsistent authorization |
| 🟡 P1 | Fix duplicate in project_completion.py | Code smell, not security risk |
| 🟢 P2 | Add audit logging for all fallback events | Forensics capability |

---

## 8. VERIFICATION COMMANDS

```bash
# Check for hardcoded role comparisons (should migrate to RBAC):
grep -rn "current_user.role not in \[" backend/routers/

# Check for role constants usage (should use get_role_group):
grep -rn "from .deps import.*ROLES" backend/routers/

# Check fallback events in logs:
grep "RBAC fallback" /var/log/supervisor/backend.err.log
```

---

## 9. CONCLUSION

**Current State:** 🟡 **PARTIALLY SECURE**

- Critical endpoints use hardcoded constants (bypass RBAC entirely)
- If those constants were migrated to `require_role_group()`, they would be FAIL-OPEN to defaults
- No "permit on error" exists for current critical paths (they don't use RBAC)
- BUT: Any new code using `require_role_group()` would be fail-open

**Recommendation:** Before migrating more endpoints to RBAC, implement fail-closed mode in `get_role_group()`.
