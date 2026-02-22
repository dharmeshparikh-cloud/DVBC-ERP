# NETRA ERP - Regression Memory Layer
# Last Updated: 2026-02-22
# Purpose: Prevent recurring issues by documenting root causes and prevention rules

## CRITICAL RULES (MUST FOLLOW)

### Rule 1: Database Connection Pattern
```
ALWAYS use: from .deps import get_db
ALWAYS call: db = get_db() at start of each endpoint function
NEVER use: local db = None in routers
NEVER use: def set_db() in individual routers
```

### Rule 2: No Hardcoded Roles
```
ALWAYS use: Role constants from deps.py (MANAGER_ROLES, HR_ROLES, etc.)
NEVER use: Inline strings like 'admin', 'manager' in authorization checks
ALWAYS update: deps.py when adding new roles
```

### Rule 3: Route Definitions
```
ALWAYS define: Routes in ALL route groups (main "/", "/sales", "/hr")
ALWAYS add: Redirect for parameter-required routes (e.g., /sow -> /sow-list)
ALWAYS test: Route accessibility after adding new routes
```

### Rule 4: Stage Flow Validation
```
ALWAYS use: validateStageAccess(user, projectId, targetStage)
ALWAYS enforce: Backward validation (can't skip stages)
ALWAYS show: Helpful dialogs instead of 403 errors
```

---

## DOCUMENTED ISSUES

### Issue #001: Masters API Database Not Initialized
```
ROOT CAUSE: masters.py had local "db = None" that shadowed deps import
WHAT FAILED: GET /api/masters/tenure-types returned 500 error
WHY IT FAILED: Local db variable was never set, remained None
WHICH LAYER: DB / API
PATTERN TYPE: Database initialization pattern violation
PREVENTION RULE: Always import get_db from deps, call db = get_db() per endpoint
TEST CASE CREATED: health_check.py - Router imports test
AUTO-FIX APPLIED: Yes - Converted to get_db() pattern
```

### Issue #002: SOW Masters API Database Not Initialized
```
ROOT CAUSE: sow_masters.py had local "db = None" with its own set_db()
WHAT FAILED: GET /api/sow-masters/categories returned 500 error
WHY IT FAILED: server.py only called router_deps.set_db(), not sow_masters.set_db()
WHICH LAYER: DB / API
PATTERN TYPE: Database initialization pattern violation
PREVENTION RULE: Never create router-specific set_db() functions
TEST CASE CREATED: health_check.py - Router imports test
AUTO-FIX APPLIED: Yes - Converted to get_db() pattern
```

### Issue #003: Drafts API Endpoint Missing
```
ROOT CAUSE: No /api/drafts router existed
WHAT FAILED: "Failed to save draft" error in Pricing Plan Builder
WHY IT FAILED: Frontend expected endpoint that didn't exist
WHICH LAYER: API
PATTERN TYPE: Missing endpoint
PREVENTION RULE: Create backend endpoint before frontend integration
TEST CASE CREATED: Curl test for POST /api/drafts
AUTO-FIX APPLIED: Yes - Created drafts.py router
```

### Issue #004: Sales Executive User Not Created
```
ROOT CAUSE: Test user sales@dvbc.com didn't exist in database
WHAT FAILED: Login failed for sales executive role testing
WHY IT FAILED: User was referenced in documentation but never created
WHICH LAYER: DB
PATTERN TYPE: Missing test data
PREVENTION RULE: Always verify test users exist before testing
TEST CASE CREATED: health_check.py - Users collection test
AUTO-FIX APPLIED: Yes - Created user with bcrypt password
```

### Issue #005: Route Not Matching
```
ROOT CAUSE: Route defined in nested group but not in main "/" routes
WHAT FAILED: /my-drafts showed "No routes matched"
WHY IT FAILED: Route only added to /sales and /hr, not main routes
WHICH LAYER: ROUTE
PATTERN TYPE: Incomplete route definition
PREVENTION RULE: Add routes to ALL THREE groups (/, /sales, /hr)
TEST CASE CREATED: Route audit script
AUTO-FIX APPLIED: Yes - Added to all route groups
```

### Issue #006: SOW Builder Blank Page
```
ROOT CAUSE: /sales-funnel/sow route requires :pricingPlanId parameter
WHAT FAILED: Accessing /sales-funnel/sow showed blank page
WHY IT FAILED: No fallback route for missing parameter
WHICH LAYER: ROUTE
PATTERN TYPE: Missing fallback route
PREVENTION RULE: Add redirect for parameter-required routes
TEST CASE CREATED: Redirect validation test
AUTO-FIX APPLIED: Yes - Added redirect to /sow-list
```

### Issue #007: Sidebar Scroll Position Not Persisting
```
ROOT CAUSE: No scroll position storage mechanism
WHAT FAILED: Sidebar jumped to top after navigation
WHY IT FAILED: React re-renders reset scroll position
WHICH LAYER: UI
PATTERN TYPE: UX state persistence
PREVENTION RULE: Use sessionStorage for scroll position
TEST CASE CREATED: Scroll persistence validation
AUTO-FIX APPLIED: Yes - Added sidebarNavRef with sessionStorage
```

### Issue #008: Hardcoded Role Strings
```
ROOT CAUSE: Role checks used inline strings instead of constants
WHAT FAILED: Role-based access inconsistent across routers
WHY IT FAILED: Copy-paste led to typos and missing roles
WHICH LAYER: AUTH
PATTERN TYPE: Hardcoded values
PREVENTION RULE: Always use ROLE constants from deps.py
TEST CASE CREATED: Grep audit for hardcoded roles
AUTO-FIX APPLIED: Yes - Propagated role constants to all routers
```

### Issue #009: Missing Role Guards on /api/employees
```
ROOT CAUSE: GET /api/employees had no role check
WHAT FAILED: Sales executive could access all employee data
WHY IT FAILED: Role guard was never implemented
WHICH LAYER: AUTH / API
PATTERN TYPE: Missing authorization
PREVENTION RULE: All sensitive endpoints MUST have role guards
TEST CASE CREATED: e2e_validation.py - Role guards test
AUTO-FIX APPLIED: Yes - Added HR_ROLES + ADMIN_ROLES check
```

### Issue #010: Missing Role Guards on /api/payroll/salary-components
```
ROOT CAUSE: GET /api/payroll/salary-components had no role check
WHAT FAILED: Any user could view salary structure
WHY IT FAILED: Role guard was only on POST, not GET
WHICH LAYER: AUTH / API
PATTERN TYPE: Missing authorization
PREVENTION RULE: Both GET and POST on sensitive data need guards
TEST CASE CREATED: e2e_validation.py - Role guards test
AUTO-FIX APPLIED: Yes - Added HR_ADMIN_ROLES + HR_ROLES check
```

### Issue #011: Missing Role Guards on /api/users
```
ROOT CAUSE: GET /api/users had no role check
WHAT FAILED: Any user could view all user accounts
WHY IT FAILED: Role guard was never implemented
WHICH LAYER: AUTH / API
PATTERN TYPE: Missing authorization
PREVENTION RULE: User management endpoints require Admin/HR roles
TEST CASE CREATED: e2e_validation.py - Role guards test
AUTO-FIX APPLIED: Yes - Added HR_ADMIN_ROLES check
```

### Issue #012: Missing /my/leave-balance Endpoint
```
ROOT CAUSE: Frontend MyLeaves.js called /api/my/leave-balance but no such endpoint existed
WHAT FAILED: /my-leaves page was blank
WHY IT FAILED: API returned 404, component errored silently
WHICH LAYER: API
PATTERN TYPE: Missing endpoint
PREVENTION RULE: Verify all frontend API calls have corresponding backend endpoints
TEST CASE CREATED: Curl test for /api/my/leave-balance
AUTO-FIX APPLIED: Yes - Added /my/leave-balance endpoint to my.py
```

### Issue #013: /my/profile Returns 404 for Users Without Employee Record
```
ROOT CAUSE: /my/profile raised HTTPException if no employee record found
WHAT FAILED: /my-details showed "Unable to load profile" error toast
WHY IT FAILED: Admin users don't always have employee records
WHICH LAYER: API
PATTERN TYPE: Missing fallback handling
PREVENTION RULE: User-facing profile endpoints must gracefully handle missing data
TEST CASE CREATED: Test profile endpoint with admin user
AUTO-FIX APPLIED: Yes - Return user data with no_employee_record flag
```

### Issue #014: Leave Requests with Undefined ID Break React Keys
```
ROOT CAUSE: Leave requests from Telegram had no 'id' field
WHAT FAILED: MyLeaves.js threw "Each child should have unique key" React warning
WHY IT FAILED: map() used req.id for key but id was undefined
WHICH LAYER: FRONTEND
PATTERN TYPE: Missing null check
PREVENTION RULE: Filter array items with .filter(item => item.id) before map()
TEST CASE CREATED: None (visual test)
AUTO-FIX APPLIED: Yes - Added .filter(req => req.id) before .map()
```

### Issue #015: Timesheets API Returns Array Instead of Expected Object
```
ROOT CAUSE: /api/timesheets returns array, frontend expected object with .entries property
WHAT FAILED: Timesheets page crashed with "Cannot convert undefined or null to object"
WHY IT FAILED: Array.entries() is a function, not an object property
WHICH LAYER: FRONTEND
PATTERN TYPE: API response shape mismatch
PREVENTION RULE: Always check API response shape (Array.isArray) before accessing properties
TEST CASE CREATED: None (visual test)
AUTO-FIX APPLIED: Yes - Added Array.isArray check to extract first element
```

### Issue #016: Routes /meetings and /team-performance Not in Main Layout
```
ROOT CAUSE: Routes were defined in /sales nested route but not in main "/" routes
WHAT FAILED: Direct navigation to /meetings showed "No routes matched"
WHY IT FAILED: Routes only existed under /sales parent path
WHICH LAYER: ROUTE
PATTERN TYPE: Incomplete route definition
PREVENTION RULE: Add routes to ALL route groups (/, /sales, /hr) when needed
TEST CASE CREATED: Route audit script
AUTO-FIX APPLIED: Yes - Added routes to main route group in App.js
```

---

## PREVENTION CHECKLIST

Before marking any task complete:

- [ ] Run health_check.py (must pass 100%)
- [ ] Run E2E simulation for all roles
- [ ] Validate route accessibility
- [ ] Validate role guards
- [ ] Validate sidebar visibility
- [ ] Validate DB state transitions
- [ ] Validate API response codes
- [ ] Validate flow restrictions
- [ ] Validate edge cases (null, empty, refresh, back button)
- [ ] Validate unauthorized role access
- [ ] Validate mobile responsiveness
- [ ] Architecture risk summary provided

---

## SYSTEM RULES (Enforced)

1. Every fix must include root cause and prevention rule
2. Every change must run full E2E simulation for all roles
3. No hardcoded roles - use deps.py constants
4. No department-based authorization - use role-based
5. All stage flows must enforce backward validation
6. Recurring issues become permanent system rules
7. Task not complete unless stability score ≥ 95/100
8. Report architecture risk summary before finishing

---

## AFFECTED MODULES MATRIX

When modifying these files, check ALL listed dependencies:

| File Modified | Check These Modules |
|--------------|---------------------|
| deps.py | ALL routers, auth, permissions |
| auth.py | Login, Registration, All protected routes |
| Layout.js | Sidebar, Navigation, All pages |
| App.js | ALL routes, Role guards, Redirects |
| server.py | ALL router registrations |
| Any router | Related frontend pages |

---

## RECURRING ISSUES FROM FORK HISTORY

| Issue | Occurrences | Status | Permanent Rule |
|-------|-------------|--------|----------------|
| Monolithic server.py | 20+ | RESOLVED | Router modularization enforced |
| Hardcoded roles | 100+ | RESOLVED | Role constants in deps.py |
| db = None pattern | 2 | RESOLVED | get_db() pattern enforced |
| Missing routes | 3 | RESOLVED | Triple route group rule |
| Missing test users | 1 | RESOLVED | Test user verification |

---

## VALIDATION FUNCTIONS

```python
# Stage Access Validation
def validateStageAccess(user, projectId, targetStage):
    """
    Validates if user can access a specific stage.
    Returns: (allowed: bool, reason: str, redirect_to: str)
    """
    # 1. Check user role permissions
    # 2. Check project exists
    # 3. Check current stage progress
    # 4. Validate no stages skipped
    # 5. Return result with helpful message
    pass

# Route Guard
def routeGuard(user, path):
    """
    Validates if user can access a route.
    Returns: (allowed: bool, redirect_to: str)
    """
    pass

# Role Guard
def roleGuard(user, required_roles):
    """
    Validates if user has required role.
    Returns: bool
    """
    return user.role in required_roles
```

---

## HEALTH CHECK COMMANDS

```bash
# Full health check
cd /app/backend && python3 health_check.py

# Router pattern audit
grep -r "db = None" /app/backend/routers/*.py | grep -v deps.py

# Hardcoded role audit
grep -rn "'admin'\|'manager'\|'hr_manager'" /app/backend/routers/*.py

# Route definition audit
grep -n "path=\"" /app/frontend/src/App.js | wc -l

# API endpoint test
curl -s $API_URL/api/health | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

---

## SCORE CALCULATION

Stability Score = Sum of:
- Database connectivity: 10 points
- Router imports: 20 points (0.4 per router)
- API endpoints: 20 points
- Route accessibility: 15 points
- Role guards: 10 points
- UI rendering: 10 points
- Flow restrictions: 10 points
- Edge cases: 5 points

Minimum required: 95/100
