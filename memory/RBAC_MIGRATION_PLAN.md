# RBAC Migration Plan: Hardcoded Roles → Database-Driven Authorization
## Production-Ready, Risk-Controlled Implementation

---

## EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total role checks to migrate | 248 |
| Critical endpoints (Phase 1) | 5 modules, ~25 checks |
| Estimated migration time | 4 phases over 2-3 sprints |
| Rollback capability | Per-module, instant |
| Risk level | Low (with dual-mode verification) |

---

## PHASE 0: PREPARATION (Pre-Migration)

### 0.1 Role Group Mapping

| Hardcoded Constant | RBAC Group Name | Members |
|--------------------|-----------------|---------|
| `AGREEMENT_APPROVE_ROLES` | `AGREEMENT_APPROVE_ROLES` | admin, principal_consultant |
| `PRINCIPAL_CONSULTANT_ROLES` | `PRINCIPAL_CONSULTANT_ROLES` | admin, principal_consultant |
| `MANAGER_ROLES` | `MANAGER_ROLES` | admin, manager, sr_manager, sales_manager, hr_manager, principal_consultant |
| `HR_ADMIN_ROLES` | `HR_ADMIN_ROLES` | admin, hr_manager |
| `ADMIN_ROLES` | `ADMIN_ROLES` | admin |
| `PROJECT_ROLES` | `PROJECT_ROLES` | admin, principal_consultant, senior_consultant, manager, project_manager |

### 0.2 Verification: Ensure RBAC Groups Match Hardcoded Values

```bash
# Run this before any migration
cd /app/backend && python3 -c "
from routers.deps import (
    AGREEMENT_APPROVE_ROLES, PRINCIPAL_CONSULTANT_ROLES, 
    MANAGER_ROLES, HR_ADMIN_ROLES, ADMIN_ROLES, PROJECT_ROLES
)
from routers.rbac_service import rbac

groups = {
    'AGREEMENT_APPROVE_ROLES': AGREEMENT_APPROVE_ROLES,
    'PRINCIPAL_CONSULTANT_ROLES': PRINCIPAL_CONSULTANT_ROLES,
    'MANAGER_ROLES': MANAGER_ROLES,
    'HR_ADMIN_ROLES': HR_ADMIN_ROLES,
    'ADMIN_ROLES': ADMIN_ROLES,
    'PROJECT_ROLES': PROJECT_ROLES,
}

print('Verifying RBAC groups match hardcoded constants:')
all_match = True
for name, hardcoded in groups.items():
    db_roles = rbac.get_role_group(name)
    match = set(hardcoded) == set(db_roles)
    status = '✅' if match else '❌'
    print(f'{status} {name}: hardcoded={sorted(hardcoded)}, db={sorted(db_roles)}')
    if not match:
        all_match = False

print(f'\nOverall: {\"READY TO MIGRATE\" if all_match else \"FIX MISMATCHES FIRST\"}'
)
"
```

### 0.3 Add Missing Groups to Seeder

If any groups are missing, add them to `/app/backend/routers/rbac_seeder.py`:

```python
# Add to ROLE_GROUP_DEFINITIONS in rbac_seeder.py
"AGREEMENT_APPROVE_ROLES": {
    "name": "Agreement Approval Roles",
    "description": "Roles that can approve agreements",
    "roles": ["admin", "principal_consultant"],
    "is_system": True,
    "is_critical": True,  # Marks as critical for fail-closed
},
```

---

## PHASE 1: CRITICAL ENDPOINTS (Highest Risk, Most Important)

### Migration Order by Risk

| Order | Module | Endpoint | Current Check | Risk if Wrong |
|-------|--------|----------|---------------|---------------|
| 1.1 | kickoff.py | approve_kickoff | `PRINCIPAL_CONSULTANT_ROLES` | Unauthorized project creation |
| 1.2 | agreements.py | approve_agreement | `AGREEMENT_APPROVE_ROLES` | Unauthorized contract approval |
| 1.3 | project_completion.py | complete_project | Inline list | Unauthorized project closure |
| 1.4 | project_pnl.py | export_pnl | `MANAGER_ROLES` | Financial data exposure |
| 1.5 | approvals.py | approve_request | `MANAGER_ROLES` | Unauthorized approvals |

---

### 1.1 KICKOFF APPROVAL MIGRATION

**File:** `/app/backend/routers/kickoff.py`
**Lines:** 556, 663, 1410

**BEFORE:**
```python
from .deps import get_db, SALES_EXECUTIVE_ROLES, PRINCIPAL_CONSULTANT_ROLES

# Line 663
if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:
    raise HTTPException(status_code=403, detail="Only Principal Consultant can approve...")
```

**AFTER (Dual-Mode with Verification):**
```python
from .deps import (
    get_db, SALES_EXECUTIVE_ROLES, PRINCIPAL_CONSULTANT_ROLES,
    get_role_group, has_role
)
from .rbac_migration import compare_permission_results

# Line 663 - PHASE 1: Dual-mode verification
hardcoded_allowed = current_user.role in PRINCIPAL_CONSULTANT_ROLES
rbac_allowed = has_role(current_user.role, get_role_group("PRINCIPAL_CONSULTANT_ROLES", fail_closed=True))

# Log any discrepancies during transition
compare_permission_results(
    location="kickoff.approve_kickoff_internal",
    user_role=current_user.role,
    old_result=hardcoded_allowed,
    new_result=rbac_allowed
)

# Use hardcoded during verification phase
if not hardcoded_allowed:
    raise HTTPException(status_code=403, detail="Only Principal Consultant can approve...")
```

**AFTER (Final - RBAC Only):**
```python
from .deps import get_db, require_role_group_critical

@router.post("/{request_id}/approve-internal")
async def approve_kickoff_internal(
    request_id: str,
    current_user: User = Depends(require_role_group_critical("PRINCIPAL_CONSULTANT_ROLES"))
):
    # No manual role check needed - dependency handles it with fail-closed
    ...
```

---

### 1.2 AGREEMENT APPROVAL MIGRATION

**File:** `/app/backend/routers/agreements.py`
**Lines:** 25, 287, 326

**BEFORE:**
```python
AGREEMENT_APPROVE_ROLES = ["admin", "principal_consultant"]

# Line 287
if current_user.role not in AGREEMENT_APPROVE_ROLES:
    raise HTTPException(status_code=403, ...)
```

**AFTER (Dual-Mode):**
```python
from .deps import get_role_group, has_role
from .rbac_migration import compare_permission_results

# Remove local constant, use RBAC
# AGREEMENT_APPROVE_ROLES = ["admin", "principal_consultant"]  # DEPRECATED

# Line 287
rbac_roles = get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)
if not rbac_roles:
    raise HTTPException(status_code=503, detail="Authorization service unavailable")

if not has_role(current_user.role, rbac_roles):
    raise HTTPException(status_code=403, detail="Only Admin or Principal Consultant can approve")
```

**AFTER (Final):**
```python
from .deps import require_role_group_critical

@router.post("/{agreement_id}/approve")
async def approve_agreement(
    agreement_id: str,
    current_user: User = Depends(require_role_group_critical("AGREEMENT_APPROVE_ROLES"))
):
    ...
```

---

### 1.3 PROJECT COMPLETION MIGRATION

**File:** `/app/backend/routers/project_completion.py`
**Line:** 249-254

**BEFORE:**
```python
allowed_roles = [UserRole.ADMIN, "principal_consultant", "principal_consultant"]  # BUG: duplicate
if current_user.role not in allowed_roles:
    raise HTTPException(status_code=403, ...)
```

**AFTER:**
```python
from .deps import require_role_group_critical

@router.post("/{project_id}/complete")
async def complete_project(
    project_id: str,
    request: ProjectCompletionRequest,
    current_user: User = Depends(require_role_group_critical("PROJECT_ROLES"))
):
    # Additional check for force_complete
    if request.force_complete and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can force complete")
    ...
```

---

### 1.4 PNL EXPORT MIGRATION

**File:** `/app/backend/routers/project_pnl.py`
**Lines:** 32, 167, 447

**BEFORE:**
```python
if current_user.role not in MANAGER_ROLES:
    raise HTTPException(status_code=403, ...)
```

**AFTER:**
```python
from .deps import require_role_group_critical

@router.get("/export")
async def export_pnl(
    current_user: User = Depends(require_role_group_critical("MANAGER_ROLES"))
):
    ...
```

---

### 1.5 APPROVALS MIGRATION

**File:** `/app/backend/routers/approvals.py`
**Lines:** 47, 82, 196, 245

**BEFORE:**
```python
if current_user.role not in MANAGER_ROLES:
    raise HTTPException(status_code=403, ...)
```

**AFTER:**
```python
from .deps import require_role_group_critical

@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    current_user: User = Depends(require_role_group_critical("APPROVAL_ROLES"))
):
    ...
```

---

## PHASE 2: HR & ATTENDANCE (Medium Risk)

| Module | Checks | Group |
|--------|--------|-------|
| attendance.py | 4 | HR_ADMIN_ROLES |
| ctc.py | 5 | HR_ADMIN_ROLES |
| department_access.py | 5 | HR_ADMIN_ROLES |
| users.py | ~10 | HR_ROLES, HR_ADMIN_ROLES |

---

## PHASE 3: ANALYTICS & REPORTING (Lower Risk)

| Module | Checks | Group |
|--------|--------|-------|
| analytics.py | 2 | MANAGER_ROLES |
| stats.py | ~5 | Various |
| audit_logging.py | 5 | ADMIN_ROLES |

---

## PHASE 4: SALES & CONSULTING (Lowest Risk)

| Module | Checks | Group |
|--------|--------|-------|
| leads.py | 3 | HR_ADMIN_ROLES (assignment only) |
| consultants.py | 2 | MANAGER_ROLES |
| projects.py | 4 | Various |

---

## REGRESSION TEST SUITE

### Test File: `/app/backend/tests/test_rbac_migration.py`

```python
"""
RBAC Migration Regression Tests
Run after each phase to ensure authorization still works correctly.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

BASE_URL = "http://localhost:8001/api"

# Test credentials
ADMIN_CREDS = {"employee_id": "ADMIN001", "password": "admin123"}
PC_CREDS = {"employee_id": "DVC001", "password": "test123"}  # principal_consultant
HR_CREDS = {"employee_id": "DVC037", "password": "test123"}  # hr_manager
SALES_CREDS = {"employee_id": "DVC034", "password": "test123"}  # sales_executive

async def get_token(client: AsyncClient, creds: dict) -> str:
    """Get auth token for user"""
    response = await client.post(f"{BASE_URL}/auth/login", json=creds)
    return response.json().get("access_token", "")


class TestKickoffApproval:
    """Test kickoff approval authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_approve_kickoff(self, client: AsyncClient):
        token = await get_token(client, ADMIN_CREDS)
        # Create test kickoff first, then try to approve
        # This should succeed
        pass
    
    @pytest.mark.asyncio
    async def test_principal_consultant_can_approve_kickoff(self, client: AsyncClient):
        token = await get_token(client, PC_CREDS)
        # Should succeed
        pass
    
    @pytest.mark.asyncio
    async def test_sales_executive_cannot_approve_kickoff(self, client: AsyncClient):
        token = await get_token(client, SALES_CREDS)
        # Should return 403
        pass


class TestAgreementApproval:
    """Test agreement approval authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_approve_agreement(self, client: AsyncClient):
        token = await get_token(client, ADMIN_CREDS)
        pass
    
    @pytest.mark.asyncio
    async def test_principal_consultant_can_approve_agreement(self, client: AsyncClient):
        token = await get_token(client, PC_CREDS)
        pass
    
    @pytest.mark.asyncio
    async def test_hr_manager_cannot_approve_agreement(self, client: AsyncClient):
        token = await get_token(client, HR_CREDS)
        # Should return 403
        pass


class TestProjectCompletion:
    """Test project completion authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_complete_project(self, client: AsyncClient):
        pass
    
    @pytest.mark.asyncio
    async def test_only_admin_can_force_complete(self, client: AsyncClient):
        pass


class TestPnLExport:
    """Test financial data export authorization"""
    
    @pytest.mark.asyncio
    async def test_manager_can_export_pnl(self, client: AsyncClient):
        pass
    
    @pytest.mark.asyncio
    async def test_sales_executive_cannot_export_pnl(self, client: AsyncClient):
        pass


class TestRBACFailClosed:
    """Test fail-closed behavior when RBAC service is unavailable"""
    
    @pytest.mark.asyncio
    async def test_critical_endpoint_denies_on_cache_miss(self, client: AsyncClient):
        # Simulate cache invalidation
        # Verify 503 response, not 200
        pass
```

---

## MONITORING & ALERTING

### 1. Metrics to Track

```python
# Add to /app/backend/services/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# RBAC metrics
rbac_cache_hits = Counter('rbac_cache_hits_total', 'RBAC cache hits', ['group_name'])
rbac_cache_misses = Counter('rbac_cache_misses_total', 'RBAC cache misses', ['group_name'])
rbac_fallback_events = Counter('rbac_fallback_events_total', 'RBAC fallback to defaults', ['group_name', 'location'])
rbac_authorization_failures = Counter('rbac_auth_failures_total', 'Authorization failures', ['endpoint', 'role'])
rbac_service_health = Gauge('rbac_service_healthy', 'RBAC service health (1=healthy, 0=unhealthy)')
```

### 2. Log Patterns to Monitor

```bash
# Critical alerts (PagerDuty/Slack)
grep -E "RBAC FAIL-CLOSED|RBAC_FALLBACK|Authorization service unavailable" /var/log/supervisor/backend.err.log

# Warning alerts (daily review)
grep -E "Cache miss for role group|permission_mismatches" /var/log/supervisor/backend.err.log
```

### 3. Health Check Endpoint

```python
# Add to /app/backend/routers/rbac_router.py

@router.get("/health")
async def rbac_health():
    """RBAC service health check for monitoring"""
    cache_valid = rbac.is_cache_valid()
    roles_count = len(_role_cache)
    groups_count = len(_permission_cache)
    
    healthy = cache_valid and roles_count > 0 and groups_count > 0
    
    return {
        "healthy": healthy,
        "cache_valid": cache_valid,
        "roles_cached": roles_count,
        "groups_cached": groups_count,
        "cache_age_seconds": time.time() - _cache_timestamp if _cache_timestamp else -1
    }
```

### 4. Alerting Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| `rbac_fallback_events > 0` | WARNING | Investigate RBAC service |
| `rbac_service_healthy == 0` | CRITICAL | Page on-call |
| `rbac_auth_failures` spike > 5x | WARNING | Check for misconfiguration |
| `rbac_cache_misses` > 10/min | WARNING | Check DB connectivity |

---

## ROLLOUT CHECKLIST

### Pre-Migration (Day -1)
- [ ] Run verification script to confirm RBAC groups match hardcoded
- [ ] Ensure RBAC seeder has all required groups
- [ ] Run `python -m routers.rbac_seeder` to sync
- [ ] Verify `/api/rbac/migration-status` returns HEALTHY
- [ ] Create database backup

### Phase 1: Kickoff Approval (Day 1)
- [ ] Deploy dual-mode verification code
- [ ] Monitor for permission mismatches (24 hours)
- [ ] If no mismatches, deploy final RBAC-only code
- [ ] Run regression tests
- [ ] Monitor 403 errors

### Phase 1: Agreement Approval (Day 2)
- [ ] Repeat dual-mode → final migration
- [ ] Run regression tests
- [ ] Monitor

### Phase 1: Project/PnL/Approvals (Days 3-5)
- [ ] Migrate remaining critical endpoints
- [ ] Run full regression suite
- [ ] Document any issues

### Phase 2-4 (Week 2-3)
- [ ] Migrate remaining modules
- [ ] Final regression testing
- [ ] Remove deprecated constants from deps.py

---

## ROLLBACK PROCEDURE

### Per-Module Rollback (< 5 minutes)

1. **Revert code:**
   ```bash
   git revert <commit-hash>
   sudo supervisorctl restart backend
   ```

2. **Verify:**
   ```bash
   curl $API_URL/api/health
   curl $API_URL/api/rbac/migration-status
   ```

### Full RBAC Rollback (< 15 minutes)

1. **Disable RBAC in deps.py:**
   ```python
   # Comment out RBAC imports
   # from .rbac_service import rbac, get_role_group
   
   # Use hardcoded constants directly
   def get_role_group(group_name, fail_closed=False):
       return HARDCODED_GROUPS.get(group_name, [])
   ```

2. **Restart backend:**
   ```bash
   sudo supervisorctl restart backend
   ```

3. **Verify all critical endpoints return expected results**

---

## SUCCESS CRITERIA

| Metric | Target |
|--------|--------|
| Zero fallback events after migration | 100% |
| Zero permission mismatches | 100% |
| All regression tests pass | 100% |
| No increase in 403 errors | < 5% variance |
| RBAC health check passing | 100% uptime |
