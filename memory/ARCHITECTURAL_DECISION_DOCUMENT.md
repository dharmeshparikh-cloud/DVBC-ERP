# NETRA ERP - Architectural Decision Document
**Prepared for:** Dharmesh Parikh (dharmesh.parikh@dvconsulting.co.in)
**Date:** February 22, 2026
**Document Type:** Technical Review & Business Impact Analysis

---

## SECTION 1: DUPLICATE ROUTES ANALYSIS

### Current State
42 routes are defined in multiple parent groups. This means the same page is accessible via multiple URLs.

### Specific Examples with Business Logic Impact

#### Example 1: `/my-leaves` (Employee Leave Requests)

**Current State:**
```
URL 1: /my-leaves (Main ERP)
URL 2: /sales/my-leaves (Sales Portal)
URL 3: /hr/my-leaves (HR Portal)
```

**Business Logic Question:**
- Should a Sales Executive accessing the Sales Portal see their personal leave requests?
- Or should they be redirected to the main ERP for personal HR matters?

**Option A: Keep Duplicates (Current)**
- Pros: Users can access personal data from any portal without switching
- Cons: Inconsistent URLs, analytics tracking issues, SEO problems
- Business Impact: User convenience vs URL consistency

**Option B: Remove from Sales/HR, Keep Only in Main**
- Pros: Clean URL structure, single source of truth
- Cons: Sales users must navigate to main ERP for leave requests
- Business Impact: One extra click for users in specialized portals

**Recommendation:** 
- KEEP in Main ERP (`/my-leaves`)
- REMOVE from Sales Portal (Sales is for revenue, not HR)
- KEEP in HR Portal (HR staff need quick access to their own leaves)

---

#### Example 2: `/leads` (Sales Leads)

**Current State:**
```
URL 1: /leads (Main ERP)
URL 2: /sales/leads (Sales Portal - CORRECT LOCATION)
```

**Business Logic Question:**
- Should non-sales employees (HR, Consultants) see leads in Main ERP?
- Or is this strictly a Sales domain function?

**Option A: Keep in Both**
- Pros: Admins can view leads from main dashboard
- Cons: HR employees might accidentally access sales data

**Option B: Remove from Main, Keep Only in Sales**
- Pros: Clean domain separation (Leads = Sales only)
- Cons: Admins need to switch to Sales portal to view leads

**Recommendation:**
- KEEP in Sales Portal (`/sales/leads`) - Primary location
- KEEP in Main ERP (`/leads`) - For admin cross-department view
- ADD role guard: Only show to users with sales_view permission

---

#### Example 3: `/employees` (Employee Directory)

**Current State:**
```
URL 1: /employees (Main ERP)
URL 2: /hr/employees (HR Portal)
```

**Business Logic Question:**
- Is employee directory an HR-only function?
- Or should all employees see the directory?

**Option A: Keep in Both**
- Pros: All employees can find colleagues
- Cons: Duplicate maintenance

**Option B: Remove from HR, Keep in Main**
- Pros: Single URL
- Cons: HR loses quick access from their portal

**Recommendation:**
- KEEP in Main ERP (`/employees`) - Company directory for all
- KEEP in HR Portal (`/hr/employees`) - HR needs this for their workflow
- DIFFERENT DATA: Main shows basic info, HR shows full records

---

### DECISION TABLE: Duplicate Routes

| Route | Main ERP | Sales Portal | HR Portal | Consulting | Reason |
|-------|----------|--------------|-----------|------------|--------|
| `/my-leaves` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | Personal HR in Main/HR only |
| `/my-attendance` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | Personal HR in Main/HR only |
| `/my-salary` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | Sensitive - Main/HR only |
| `/my-expenses` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ✅ KEEP | Consultants submit expenses |
| `/my-details` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | Personal HR in Main/HR only |
| `/leads` | ✅ KEEP | ✅ KEEP | ❌ REMOVE | ❌ REMOVE | Sales domain |
| `/employees` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | HR domain |
| `/projects` | ✅ KEEP | ❌ REMOVE | ❌ REMOVE | ✅ KEEP | Consulting domain |
| `/attendance` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | HR domain |
| `/payroll` | ✅ KEEP | ❌ REMOVE | ✅ KEEP | ❌ REMOVE | HR domain |
| `/meetings` | ✅ KEEP | ✅ KEEP | ❌ REMOVE | ✅ KEEP | Sales & Consulting |
| `/reports` | ✅ KEEP | ✅ KEEP | ✅ KEEP | ✅ KEEP | All need reports |

**YOUR INPUT NEEDED:**
- [ ] Agree with above recommendations?
- [ ] Any routes that should be accessible from ALL portals?
- [ ] Should we show different data based on portal context?

---

## SECTION 2: SELF-SERVICE ENDPOINTS CONSOLIDATION

### Current State
Self-service endpoints (user's own data) are scattered across 9 different routers.

### Specific Examples

#### Current Fragmentation:

| What User Wants | Current Endpoint | Current Router | Should Be |
|----------------|------------------|----------------|-----------|
| My projects | `/consultants/my/projects` | consultants.py | `/my/projects` |
| My dashboard stats | `/consultants/my/dashboard-stats` | consultants.py | `/my/dashboard-stats` |
| My funnel summary | `/analytics/my-funnel-summary` | analytics.py | `/my/funnel-summary` |
| My approval requests | `/approvals/my-requests` | approvals.py | `/my/approval-requests` |
| My department access | `/department-access/my-access` | department_access.py | `/my/department-access` |
| My payments | `/project-payments/my-payments` | project_payments.py | `/my/payments` |
| My permissions | `/role-management/my-permissions` | role_management.py | `/my/permissions` |
| My travel claims | `/travel/my/travel-reimbursements` | travel.py | `/my/travel-reimbursements` |
| My team members | `/users/my-team` | users.py | `/my/team` |

#### Business Logic Questions:

**Q1: Should a consultant's projects be under `/consultants/my/projects` or `/my/projects`?**

Option A: Keep `/consultants/my/projects`
- Pros: Clear that this is consultant-specific functionality
- Cons: Inconsistent with other self-service endpoints

Option B: Move to `/my/projects`
- Pros: All "my" data in one place, consistent API
- Cons: Loses the consultant context

**Recommendation:** Keep current paths but ADD aliases in `/my` router
```python
# In my.py - aliases for consistency
@router.get("/projects")
async def get_my_projects():
    # Delegates to consultants router
    return await get_consultant_projects(current_user)
```

---

**Q2: Should `/my-team` (users I manage) be self-service or manager function?**

Current: `/users/my-team` - Returns subordinates for managers

**Business Logic:**
- This is NOT self-service (viewing own data)
- This is MANAGER function (viewing team data)
- Should this be `/manager/team` instead of `/my/team`?

**Recommendation:** 
- Rename to `/manager/my-team` - Clearer intent
- Keep in users.py but add manager role guard

---

### DECISION TABLE: Self-Service Consolidation

| Endpoint | Keep Current? | Add /my Alias? | Rename? | Role Required |
|----------|---------------|----------------|---------|---------------|
| `/consultants/my/projects` | ✅ Yes | ✅ Add `/my/consulting-projects` | No | consultant |
| `/consultants/my/dashboard-stats` | ✅ Yes | ❌ No | No | consultant |
| `/analytics/my-funnel-summary` | ✅ Yes | ✅ Add `/my/sales-summary` | No | sales roles |
| `/approvals/my-requests` | ✅ Yes | ✅ Add `/my/approvals` | No | any |
| `/department-access/my-access` | ✅ Yes | ❌ No | No | any |
| `/project-payments/my-payments` | ✅ Yes | ✅ Add `/my/project-payments` | No | consultant |
| `/role-management/my-permissions` | ✅ Yes | ✅ Add `/my/permissions` | No | any |
| `/travel/my/travel-reimbursements` | ✅ Yes | ✅ Add `/my/travel` | No | any |
| `/users/my-team` | ❌ No | ❌ No | ✅ `/manager/team` | manager |

**YOUR INPUT NEEDED:**
- [ ] Agree with keeping current endpoints + adding aliases?
- [ ] Should we MOVE endpoints (breaking change) or ADD aliases (non-breaking)?
- [ ] Is `/users/my-team` correctly named or should it be `/manager/team`?

---

## SECTION 3: ROLE GUARDS ANALYSIS

### Current State
29 routers have endpoints without proper role authorization checks.

### Critical Security Gaps

#### HIGH PRIORITY (Sensitive Data Exposed)

**1. agreements.py - 10 endpoints unguarded**
```
Endpoints without role check:
- GET /agreements - Lists all agreements (should be sales/admin only)
- GET /agreements/{id} - View agreement details
- POST /agreements - Create agreement
- PUT /agreements/{id} - Update agreement
- DELETE /agreements/{id} - Delete agreement
```

**Business Logic Question:**
- Can a consultant view sales agreements?
- Can HR view client agreements?

**Current Risk:** ANY authenticated user can view/edit ALL agreements
**Recommendation:** Add role guard - Only `sales_manager`, `admin`, `principal_consultant`

---

**2. sow_legacy.py - 13 endpoints unguarded**
```
Endpoints without role check:
- GET /sow - Lists all SOWs
- POST /sow - Create SOW
- PUT /sow/{id} - Update SOW
```

**Business Logic Question:**
- Who should create/view SOWs?
- Sales creates, Consulting reviews, Client approves?

**Current Risk:** ANY authenticated user can view/edit ALL SOWs
**Recommendation:** 
- Create: `sales_executive`, `sales_manager`, `admin`
- View: Add `consulting_manager`, `principal_consultant`
- Approve: `principal_consultant`, `client`

---

**3. leads.py - 3 endpoints unguarded**
```
Endpoints without role check:
- GET /leads - Lists all leads
- GET /leads/{id} - View lead details
```

**Business Logic Question:**
- Should consultants see sales leads?
- Should HR see sales leads?

**Current Risk:** ANY authenticated user can view ALL leads
**Recommendation:** Add role guard - Only `sales_*`, `admin`

---

#### MEDIUM PRIORITY (Operational Data)

**4. pricing_plans.py - 4 endpoints unguarded**
- GET /pricing-plans - Lists all pricing plans
- Risk: Consultants/HR can see client pricing

**5. meetings.py - 4 endpoints unguarded**
- GET /meetings - Lists all meetings
- Risk: Cross-department meeting visibility

**6. timesheets.py - 1 endpoint unguarded**
- GET /timesheets - Lists all timesheets
- Risk: Employees see other employees' timesheets

---

### DECISION TABLE: Role Guards

| Router | Endpoint | Current Access | Recommended Access | Risk Level |
|--------|----------|----------------|-------------------|------------|
| agreements.py | GET /agreements | Any auth user | sales, admin, principal_consultant | 🔴 HIGH |
| agreements.py | POST /agreements | Any auth user | sales_manager, admin | 🔴 HIGH |
| sow_legacy.py | GET /sow | Any auth user | sales, consulting, admin | 🔴 HIGH |
| sow_legacy.py | POST /sow | Any auth user | sales, admin | 🔴 HIGH |
| leads.py | GET /leads | Any auth user | sales_*, admin | 🔴 HIGH |
| pricing_plans.py | GET /pricing-plans | Any auth user | sales, admin | 🟡 MEDIUM |
| meetings.py | GET /meetings | Any auth user | creator, attendees, admin | 🟡 MEDIUM |
| timesheets.py | GET /timesheets | Any auth user | self, manager, hr, admin | 🟡 MEDIUM |

**YOUR INPUT NEEDED:**
- [ ] Confirm recommended access levels for each router
- [ ] Any endpoints that should remain open to all authenticated users?
- [ ] Should we implement "view own data only" or "view department data" patterns?

---

## SECTION 4: BUSINESS LOGIC QUESTIONS

### Sales Funnel Flow
```
Lead → Meeting → Pricing → SOW → Quotation → Agreement → Payment → Kickoff → Closed
```

**Q1: Can a sales executive skip stages?**
- Current: Backend has stage guard, but frontend doesn't enforce
- Should we block skipping entirely or allow with manager approval?

**Q2: Who can approve stage transitions?**
| Stage | Who Creates | Who Approves | Who Can Skip |
|-------|-------------|--------------|--------------|
| Lead | Sales Exec | Auto | - |
| Meeting | Sales Exec | Auto | - |
| Pricing | Sales Exec | Sales Manager? | Manager |
| SOW | Sales Exec | Principal Consultant | Admin |
| Quotation | Auto-generated | Auto | - |
| Agreement | Sales Exec | Client | Admin |
| Payment | Finance | Auto-verified | Admin |
| Kickoff | Consulting | PM | Admin |

**Q3: Can a deal be reopened after closure?**
- Current: No restriction
- Should closed deals be immutable?

---

### HR Permissions
**Q4: Can HR view sales data?**
- Current: Yes (no restriction)
- Recommended: No (unless admin)

**Q5: Can Sales view HR data?**
- Current: Yes (no restriction)  
- Recommended: Only own data

**Q6: Who can view salary information?**
- Current: Any authenticated user
- Recommended: Self, Manager (for team), HR, Admin

---

### Consulting Permissions
**Q7: Can consultants see project financials?**
- Current: Yes
- Recommended: Only Principal Consultants

**Q8: Who assigns consultants to projects?**
- Current: Anyone
- Recommended: PM, Consulting Manager, Admin

---

## SECTION 5: RECOMMENDED ACTION PLAN

### Phase 1: Critical Security (Do First)
1. Add role guards to agreements.py (10 endpoints)
2. Add role guards to sow_legacy.py (13 endpoints)
3. Add role guards to leads.py (3 endpoints)

### Phase 2: Route Cleanup
1. Remove `/my-*` routes from Sales portal (keep in Main/HR)
2. Remove `/leads` from HR portal
3. Remove `/employees` from Sales/Consulting portals

### Phase 3: API Consolidation
1. Add `/my/*` aliases for self-service endpoints
2. Rename `/users/my-team` to `/manager/team`
3. Document canonical URLs in API docs

### Phase 4: Stage Enforcement
1. Add frontend stage validation
2. Implement manager approval for stage skipping
3. Audit trail for all stage transitions

---

## RESPONSE FORM

Please fill and return:

**1. Duplicate Routes:**
- [ ] Proceed with recommended removals
- [ ] Keep all duplicates (user convenience)
- [ ] Custom: ________________________________

**2. Self-Service Consolidation:**
- [ ] Add aliases only (non-breaking)
- [ ] Move endpoints (breaking change)
- [ ] Keep current structure
- [ ] Custom: ________________________________

**3. Role Guards:**
- [ ] Implement all recommended guards
- [ ] Implement HIGH priority only
- [ ] Provide custom access matrix
- [ ] Custom: ________________________________

**4. Stage Enforcement:**
- [ ] Block all stage skipping
- [ ] Allow skipping with manager approval
- [ ] Allow skipping with admin approval only
- [ ] Custom: ________________________________

**5. Cross-Department Access:**
- Sales can view HR data: [ ] Yes [ ] No [ ] Own only
- HR can view Sales data: [ ] Yes [ ] No [ ] Own only
- Consulting can view Sales data: [ ] Yes [ ] No [ ] Project-related only
- Salary visible to: [ ] Self only [ ] Self + Manager [ ] Self + Manager + HR

**Additional Comments:**
_____________________________________________
_____________________________________________
_____________________________________________

---

**Please return to:** Agent via chat or email
**Deadline:** Before next implementation phase

