# NETRA ERP - API Security Access Control

## Last Updated: February 22, 2026

---

## ROLE-BASED API ACCESS MATRIX

| Endpoint | Method | Previous Access | New Access | Risk Level |
|----------|--------|-----------------|------------|------------|
| `/api/agreements` | GET | Any authenticated | sales, admin, principal_consultant | HIGH → FIXED |
| `/api/agreements` | POST | Any authenticated | sales_manager, admin (with approval) | HIGH → FIXED |
| `/api/leads` | GET | Any authenticated | sales_*, admin | HIGH → FIXED |
| `/api/pricing-plans` | GET | Any authenticated | sales, admin | MEDIUM → FIXED |
| `/api/timesheets` | GET | Any authenticated | self, manager, hr, admin | MEDIUM → FIXED |

---

## ROLE CONSTANTS (deps.py)

```python
ADMIN_ROLES = ["admin"]
HR_ROLES = ["admin", "hr_manager", "hr_executive"]
SALES_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive"]
SALES_MANAGER_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"]
CONSULTING_ROLES = ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]
MANAGER_ROLES = ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"]
```

---

## SIDEBAR VISIBILITY MATRIX

| Role | My Workspace | HR | Sales | Consulting | Admin |
|------|--------------|-----|-------|------------|-------|
| admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| hr_manager | ✅ | ✅ | ❌ | ❌ | ❌ |
| hr_executive | ✅ | ✅ | ❌ | ❌ | ❌ |
| sales_manager | ✅ | ❌ | ✅ | ❌ | ❌ |
| executive | ✅ | ❌ | ✅(Guided) | ❌ | ❌ |
| consultant | ✅ | ❌ | ❌ | ✅ | ❌ |
| manager | ✅ | ❌ | ✅ | ❌ | ❌ |

---

## FIXES APPLIED

### 1. Sidebar Visibility Bug (Layout.js)
- **Issue**: Sales Executive (Rahul) was seeing HR section
- **Root Cause**: `hasReportees` flag was incorrectly enabling HR visibility
- **Fix**: Changed logic to only show HR for HR department or HR roles, excluding executives

### 2. Missing Achievement Scorecard
- **Issue**: No link to employee scorecard in sidebar
- **Fix**: Added "My Scorecard" link to My Workspace section

### 3. API Role Guards
- **Agreements**: Added role check for GET (sales, admin, principal_consultant)
- **Agreements POST**: Added role check + auto-approval flag for non-admins
- **Leads**: Added role check (sales_*, admin)
- **Pricing Plans**: Added role check (sales, admin)
- **Timesheets**: Added HR to view-all roles

---

## SECURITY CHECKLIST

- [x] Agreements endpoint secured
- [x] Leads endpoint secured
- [x] Pricing plans endpoint secured
- [x] Timesheets endpoint secured with proper scoping
- [x] Sidebar visibility fixed for Sales Executive
- [x] Achievement Scorecard linked
