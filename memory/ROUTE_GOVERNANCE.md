# NETRA ERP - Route Governance Document

## Last Updated: February 22, 2026

---

## CANONICAL ROUTE RULE (ENFORCED)

1. Every page has exactly ONE canonical route
2. Sidebar links match canonical routes exactly
3. No component rendered by multiple independent routes
4. Old portal routes (/sales/*, /hr/*) are REDIRECTS only
5. No alias routes - all converted to redirects

---

## REDIRECT MAP

| Old Route | Redirects To | Reason |
|-----------|--------------|--------|
| `/sales/*` | Strip prefix, main ERP | Portal consolidation |
| `/hr/*` | Strip prefix, main ERP | Portal consolidation |
| `/sales/login` | `/login` | Unified login |
| `/hr/login` | `/login` | Unified login |
| `/meetings` | `/sales-meetings` | Canonical route |
| `/targets` | `/target-management` | Canonical route |
| `/team-leads` | `/manager-leads` | Canonical route |
| `/document-builder` | `/document-center` | Canonical route |
| `/letter-management` | `/document-center` | Canonical route |
| `/sales-funnel/proforma-invoice` | `/sales-funnel/quotations` | Canonical route |
| `/my-bank-details` | `/my-details` | Consolidated page |
| `/sales-funnel/sow` | `/sales-funnel/sow-list` | Canonical route |

---

## ROLE VISIBILITY MATRIX

| Role | My Workspace | HR | Sales | Consulting | Admin |
|------|--------------|-----|-------|------------|-------|
| admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| hr_manager | ✅ | ✅ | ❌ | ❌ | ❌ |
| hr_executive | ✅ | ✅ | ❌ | ❌ | ❌ |
| sales_manager | ✅ | Limited | ✅ | ❌ | ❌ |
| executive | ✅ | ❌ | ✅(Guided) | ❌ | ❌ |
| consultant | ✅ | ❌ | ❌ | ✅ | ❌ |
| manager | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## STATISTICS

- Total Frontend Routes: 114
- Canonical Routes: 97
- Redirect Routes: 17
- Sidebar Navigation Items: 60
- Backend Routers: 50+

---

## DEVELOPMENT RULES

### DO NOT:
- ❌ Create duplicate route definitions
- ❌ Render same component from multiple independent routes
- ❌ Add sidebar links that don't match routes exactly
- ❌ Move backend endpoints during frontend changes
- ❌ Merge dashboards into one giant component
- ❌ Hide routes instead of guarding them

### DO:
- ✅ Use Navigate component for redirects
- ✅ Keep one canonical route per component
- ✅ Use role-based visibility in sidebar
- ✅ Follow existing naming patterns
- ✅ Run validation before completing changes
- ✅ Update this document when adding new routes

---

## VALIDATION CHECKLIST

Before any route change:
1. [ ] No duplicate route definitions
2. [ ] Sidebar links match routes
3. [ ] Redirects use Navigate with replace
4. [ ] Frontend builds successfully
5. [ ] Backend health check passes
6. [ ] Auth flow works
7. [ ] Role visibility correct
