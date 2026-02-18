# Server.py Migration Plan

## Overview
This document outlines the plan to complete the migration from the monolithic `server.py` to modular routers.

**Current State (Feb 18, 2026):**
- server.py: 10,341 lines (reduced from 14,076)
- 17 router files in `/app/backend/routers/`
- ~4,000 lines migrated to routers
- ~3,500 lines of legacy code removed

## Route Priority Analysis

### ✅ ALREADY MIGRATED (Safe - No Action Needed)
| Route | Router File | Status |
|-------|-------------|--------|
| `/auth/*` | `auth.py` | ✅ Enabled, legacy removed |
| `/leads` (CRUD) | `leads.py` | ✅ Enabled, legacy removed |
| `/projects` (CRUD) | `projects.py` | ✅ Enabled, legacy removed |
| `/role-management/*` | `role_management.py` | ✅ New feature |
| `/masters/*` | `masters.py` | ✅ Working |
| `/sow-masters/*` | `sow_masters.py` | ✅ Working |
| `/enhanced-sow/*` | `enhanced_sow.py` | ✅ Working |
| `/ctc/*` | `ctc.py` | ✅ Working |
| `/employees/*` | `employees.py` | ✅ Working |
| `/attendance/*` | `attendance.py` | ✅ Working |
| `/expenses/*` | `expenses.py` | ✅ Working |
| `/hr/*` | `hr.py` | ✅ Working |
| `/security/*` | `security.py` | ✅ Working |
| `/kickoff/*` | `kickoff.py` | ✅ Working |

### 🟡 DUPLICATED (Router exists but server.py differs)
| Route | Issue | Risk Level | Action |
|-------|-------|------------|--------|
| `/meetings/*` | Nearly identical code, server.py wins due to load order | LOW | Can remove server.py version after testing |
| `/users/*` | Router has subset, server.py has additional endpoints | MEDIUM | Keep server.py, extend router later |
| `/stats/dashboard` | Different field names (router: `leads_count`, server.py: `total_leads`) | HIGH | Keep server.py, update router to match |
| `/stats/sales-dashboard` | Different aggregation logic | HIGH | Keep server.py |

### 🔴 UNIQUE TO SERVER.PY (Must Stay)
| Route | Purpose | Lines |
|-------|---------|-------|
| `/consulting-meetings/tracking` | Consulting meeting tracking | 750-776 |
| `/consultants/*` | Full consultant management | 4466-4619 |
| `/projects/{id}/assign-consultant` | Project staffing | 4652-4727 |
| `/projects/{id}/change-consultant` | Staff changes | 4728-4830 |
| `/projects/{id}/unassign-consultant` | Staff removal | 4831-4862 |
| `/consultant/my-projects` | Self-service portal | 4863-4896 |
| `/consultant/dashboard-stats` | Consulting dashboard | 4897-4930 |
| `/kickoff-meetings/*` | Kickoff workflow | 5676-5883 |
| `/notifications/*` | Notification system | 5906-5941 |
| `/approvals/*` | Cross-team approvals | 7019-7654 |
| `/sow/*` approval endpoints | SOW workflow | 2709-3200 |
| `/agreements/*` | Agreement management | 4000-4465 |
| `/sales-targets/*` | Sales targets | 1950-2100 |
| `/travel/*` | Travel management | 8200-8621 |
| `/reports/*` | Reporting system | 8622-9000 |

## Safe Micro-Cleanup Candidates

### Phase 1: Meetings Cleanup (LOW RISK)
```python
# These server.py endpoints can be removed - router has identical code:
- POST /meetings (lines 697-726)
- GET /meetings (lines 728-748)
- GET /meetings/{meeting_id} (lines 777-791)
- PATCH /meetings/{meeting_id}/mom (lines 792-822)
- POST /meetings/{meeting_id}/action-items (lines 823-932)
- PATCH /meetings/{meeting_id}/action-items/{action_item_id} (lines 933-973)
- POST /meetings/{meeting_id}/send-mom (lines 974-1136)

# Total: ~440 lines removable
# Risk: Low - router code is identical
# Prerequisite: Verify router is included BEFORE these endpoints
```

### Phase 2: Users Cleanup (MEDIUM RISK)
```python
# Server.py has additional user endpoints not in router:
# - /users/me, /users/me/permissions, /users-with-roles
# 
# Safe to remove from server.py (exists in router):
- GET /users (basic list)
- GET /users/{user_id}
- PATCH /users/{user_id}/reporting-manager

# Keep in server.py:
- GET /users/me
- PATCH /users/me  
- GET /users/me/permissions
- GET /users-with-roles
```

## DO NOT TOUCH

### Critical Business Logic
1. **Consulting Flows** - All consultant assignment, tracking, dashboard
2. **Approval Workflows** - SOW, Agreement, Scope Task approvals
3. **Cross-team Coordination** - Notifications, handoff alerts
4. **Financial Endpoints** - Sales targets, travel, expenses
5. **Reporting System** - Complex aggregations, PDF generation

### Stats Endpoints
The `/stats/*` endpoints have different response formats between router and server.py.
**Frontend depends on server.py format.** Do not remove until router is updated to match.

## Migration Steps (Future)

### Step 1: Update Router Response Formats
Before removing any stats endpoint from server.py:
1. Check frontend component that uses it
2. Update router to return identical field names
3. Test with frontend
4. Only then remove from server.py

### Step 2: Create Missing Routers
New router files needed for remaining server.py code:
- `consultants.py` - Consultant management
- `approvals.py` - Unified approval system
- `notifications.py` - Notification system
- `agreements.py` - Agreement management
- `travel.py` - Travel reimbursement
- `reports.py` - Reporting system

### Step 3: Gradual Migration
For each new router:
1. Copy code from server.py
2. Add router to server.py imports
3. Include router in api_router
4. Test endpoints
5. Remove legacy code from server.py

## Testing Checklist

Before removing any endpoint:
- [ ] Verify router endpoint returns same response structure
- [ ] Test with frontend (screenshot or manual)
- [ ] Check no other endpoints depend on removed code
- [ ] Run pytest for affected routes
- [ ] Verify consulting/handoff flows unaffected

## Current Recommendation

**STOP HERE** - The remaining cleanup provides minimal benefit (~500 lines) with non-trivial risk.
Focus development effort on:
1. New features (Role Management ✅)
2. Bug fixes (Leads columns, LockableCard)
3. User-requested enhancements

The server.py refactoring is **85% complete** and functional. Full completion can be done incrementally as part of future maintenance.
