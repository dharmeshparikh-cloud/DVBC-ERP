# SALES MODULE GOVERNANCE AUDIT REPORT
**Date**: March 24, 2026
**Scope**: Sales Module Only (Leads, Meetings, Follow-ups, Quotations, SOW, Pipeline)

---

## 1. SALES TABLE INVENTORY

| File | Tables | .map() Count | Issues |
|------|--------|--------------|--------|
| `Leads.js` | 1 (CSV preview) | 10+ | Manual table, frontend filtering |
| `Meetings.js` | 0 (cards) | 8 | No table, card-based rendering |
| `FollowUps.js` | 0 (list) | 7 | List rendering, no DataTable |
| `ManagerLeadsDashboard.js` | 2 | 8 | Manual tables, hardcoded |
| `SalesDashboard.js` | 1 | 9 | Manual table with .map() |
| `sales-funnel/Agreements.js` | 1 | 12 | Manual table |
| `sales-funnel/AgreementView.js` | 2 | 7 | Manual tables |
| `sales-funnel/PricingPlanBuilder.js` | 1 | 15 | Manual table |
| `sales-funnel/ProformaInvoice.js` | 3 | 8 | Multiple manual tables |
| `sales-funnel/SalesSOWList.js` | 1 | 2 | Manual table |
| `sales-funnel/SOWBuilder.js` | 1 | 20 | Manual table |
| `sales-funnel/Quotations.js` | 0 (cards) | 6 | Card rendering |

---

## 2. DUPLICATE HOOKS DETECTED

| Hook | File | Purpose | Duplicate Risk |
|------|------|---------|----------------|
| `useLeads` | `hooks/useLeads.js` | Lead CRUD | ⚠️ Partial pagination |
| `useMeetings` | `hooks/useMeetings.js` | Meeting list | ⚠️ Basic filters only |
| `useSOW` | `hooks/useSOW.js` | SOW CRUD | ❌ No pagination |
| `useSalesPortal` | `hooks/useSalesPortal.js` | Portal data | ⚠️ Overlaps with leads |
| `usePricingPlans` | `hooks/usePricingPlans.js` | Pricing | ❌ No filters |
| `useSOWsByProject` | `hooks/useSOWsByProject.js` | Project SOWs | ✅ OK |

---

## 3. API FILTER/PAGINATION STATUS

| API | Endpoint | Pagination | Filters | Sort | Status |
|-----|----------|------------|---------|------|--------|
| Leads | `/api/leads` | ✅ page/page_size | ⚠️ Basic | ✅ created_at DESC | Partial |
| Meetings | `/api/meetings` | ❌ to_list(100) | ⚠️ Basic | ✅ meeting_date DESC | NEEDS WORK |
| Follow-ups | `/api/follow-ups` | ❌ to_list(500) | ⚠️ Basic | ✅ due_date ASC | NEEDS WORK |
| Quotations | `/api/quotations` | ❌ to_list(500) | ⚠️ Basic | ✅ created_at DESC | NEEDS WORK |
| Sales | `/api/sales/*` | ❌ to_list(500) | ⚠️ Basic | ✅ Various | NEEDS WORK |

---

## 4. CRITICAL ISSUES

### 4.1 Manual Tables (MUST FIX)
```
❌ Leads.js:1007 - <table> with manual .map()
❌ ManagerLeadsDashboard.js:502,595 - Manual tables
❌ SalesDashboard.js:431 - Manual table
❌ sales-funnel/Agreements.js - Manual table
❌ sales-funnel/ProformaInvoice.js - 3 manual tables
❌ sales-funnel/SalesSOWList.js - Manual table
```

### 4.2 Missing Server-Side Pagination
```
❌ meetings.py - .to_list(100) hardcoded
❌ follow_ups.py - .to_list(500) hardcoded
❌ quotations.py - .to_list(500) hardcoded
❌ sales.py - .to_list(500) hardcoded
```

### 4.3 Frontend Filtering (Performance Risk)
```
❌ Leads.js - selectedStatus filter in frontend
❌ FollowUps.js - entityFilter in frontend
❌ Meetings.js - status filter in frontend
```

### 4.4 Missing RBAC Enforcement
```
⚠️ meetings.py - Basic user check, no team-based access
⚠️ follow_ups.py - No RBAC validation
⚠️ quotations.py - Basic access check
```

---

## 5. MONGO INDEXES (OK)

✅ Leads indexes exist:
- `id` (unique)
- `assigned_to`
- `status`
- `company`
- `created_at`
- Compound: `assigned_to + status`, `status + created_at`

✅ Meetings indexes exist:
- `id` (unique)
- `lead_id`
- `meeting_date`
- Compound: `lead_id + meeting_date`

⚠️ Missing indexes:
- `follow_ups.assigned_to`
- `follow_ups.due_date`
- `quotations.lead_id`
- `quotations.status`

---

## 6. PERFORMANCE RISKS

| Risk | Impact | Priority |
|------|--------|----------|
| 10k+ leads without server pagination | HIGH | P0 |
| Frontend filtering large datasets | MEDIUM | P0 |
| No debounce on filters | MEDIUM | P1 |
| Duplicate API calls | LOW | P2 |

---

## 7. PHASE 2 REQUIREMENTS

### SalesDataTable Component Must Have:
1. Column filters (Excel-style dropdown)
2. Global search
3. Sorting (ASC/DESC)
4. Multi-filter (AND logic)
5. Server-side pagination
6. Filter chips
7. Clear filters
8. Sticky header
9. Debounce (300ms)

### Sales-Specific:
1. Pipeline stage filters
2. Deal value range
3. Assigned salesperson filter
4. Lead source filter
5. Last activity date filter
6. Quick views (My Leads, Today Follow-ups, Hot Deals, Stuck Deals)
7. Color coding (Red=overdue, Yellow=due, Green=progressing)

---

## 8. MIGRATION PLAN

### Phase 2: Create SalesDataTable
- [ ] Create `/app/frontend/src/components/sales/SalesDataTable.jsx`
- [ ] Implement all filter types
- [ ] Add server-side pagination

### Phase 3: Backend API Updates
- [ ] Add standardized filter/sort/page to all sales APIs
- [ ] Add missing indexes
- [ ] Enforce RBAC

### Phase 4: Migration
- [ ] Replace Leads.js table
- [ ] Replace ManagerLeadsDashboard.js tables
- [ ] Replace SalesDashboard.js table
- [ ] Replace sales-funnel/*.js tables

---

**AUDIT COMPLETE - READY FOR PHASE 2**
