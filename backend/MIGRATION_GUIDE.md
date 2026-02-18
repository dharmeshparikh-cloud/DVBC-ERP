# Server.py Migration Guide

## Overview
This document outlines how to migrate from the monolithic `server.py` (14,100+ lines) to the modular router structure.

## Current State
- **server.py**: 14,109 lines (includes all legacy endpoints)
- **New routers**: 6,666 lines across 15 router files

## Router Files Created

| Router | Description | Lines | Endpoints |
|--------|-------------|-------|-----------|
| deps.py | Shared dependencies | 45 | - |
| models.py | Pydantic models | 510 | - |
| auth.py | Authentication | 220 | 8 |
| leads.py | Lead management | 170 | 7 |
| projects.py | Project management | 150 | 4 |
| meetings.py | Meeting & MOM | 300 | 8 |
| stats.py | Dashboard stats | 200 | 5 |
| security.py | Audit logs | 45 | 1 |
| users.py | User management | 180 | 6 |
| kickoff.py | Kickoff workflow | 350 | 9 |
| ctc.py | CTC structure | 400 | 12 |
| employees.py | Employee management | 350 | 14 |
| attendance.py | Attendance | 200 | 6 |
| expenses.py | Expense management | 350 | 12 |
| hr.py | HR endpoints | 300 | 8 |

## Migration Steps

### Phase 1: Enable Routers (Low Risk)
Uncomment router includes in server.py. Both old and new will work (duplicate routes).

```python
# In server.py, change from:
# api_router.include_router(ctc_router.router)

# To:
api_router.include_router(ctc_router.router)
```

### Phase 2: Remove Legacy Code (Higher Risk)
After verifying new routers work, remove corresponding legacy code.

#### CTC Router Migration
**Lines to remove from server.py**: 12245-12817 (~570 lines)
- DEFAULT_CTC_COMPONENTS constant
- get_ctc_component_master() function
- calculate_ctc_breakdown_dynamic() function
- calculate_ctc_breakdown() function
- All @api_router endpoints starting with /ctc/

**Endpoints covered**:
- GET /ctc/component-master
- POST /ctc/component-master
- POST /ctc/calculate-preview
- POST /ctc/design
- GET /ctc/pending-approvals
- GET /ctc/all
- GET /ctc/employee/{employee_id}
- GET /ctc/employee/{employee_id}/history
- POST /ctc/{ctc_id}/approve
- POST /ctc/{ctc_id}/reject
- DELETE /ctc/{ctc_id}/cancel
- GET /ctc/stats

#### Employees Router Migration
**Lines to remove from server.py**: 8912-9760 (~850 lines)
**Endpoints covered**:
- GET /employees
- GET /employees/consultants
- POST /employees
- POST /employees/{employee_id}/grant-access
- DELETE /employees/{employee_id}/revoke-access
- GET /employees/{employee_id}
- PATCH /employees/{employee_id}
- DELETE /employees/{employee_id}
- POST /employees/{employee_id}/documents
- GET /employees/{employee_id}/documents/{document_id}
- DELETE /employees/{employee_id}/documents/{document_id}
- GET /employees/org-chart/hierarchy
- GET /employees/{employee_id}/subordinates
- GET /employees/departments/list
- GET /employees/stats/summary

#### HR Router Migration
**Lines to remove from server.py**: 13158-13220, 13907-14063 (~220 lines)
**Endpoints covered**:
- GET /hr/pending-attendance-approvals
- POST /hr/attendance-approval/{attendance_id}
- GET /hr/bank-change-requests
- POST /hr/bank-change-request/{request_id}/approve
- POST /hr/bank-change-request/{request_id}/reject
- GET /admin/bank-change-requests
- POST /admin/bank-change-request/{request_id}/approve
- POST /admin/bank-change-request/{request_id}/reject

## Testing Checklist

Before removing any legacy code:
1. [ ] Login as admin works
2. [ ] CTC approval modal shows components
3. [ ] Employee list loads
4. [ ] Attendance check-in works
5. [ ] Bank change requests work
6. [ ] All dashboard stats load

## Rollback Plan
If issues occur after enabling new routers:
1. Comment out the new router includes in server.py
2. Restart backend with `sudo supervisorctl restart backend`
3. Legacy endpoints will continue to work

## Estimated Size Reduction
After full migration:
- Current: 14,109 lines
- Removable: ~3,000-4,000 lines
- Final: ~10,000-11,000 lines (plus modular routers)

## Notes
- The new routers use `router_deps.get_db()` for database access
- All routers follow the same pattern for auth with `Depends(get_current_user)`
- Pydantic models are shared via `routers/models.py`
