# Admin Dashboard Entry Points Audit

**Date:** December 2025  
**Status:** AUDIT COMPLETE

---

## 1. All Routes Rendering Admin/Business Overview Dashboards

| Route | Component | File |
|-------|-----------|------|
| `/` (index) | Dynamic via `getDefaultDashboard()` | App.js:225 |
| `/admin-dashboard` | `<AdminDashboard />` | App.js:311 |
| `/admin-dashboard-mockups` | `<AdminDashboardMockups />` | App.js:310 |
| `/sales-dashboard` | `<SalesDashboard />` | App.js:297 |
| `/consulting-dashboard` | `<ConsultingDashboard />` | App.js:298 |
| `/hr-dashboard` | `<HRDashboard />` | App.js:299 |
| `/consultant-dashboard` | `<ConsultantDashboard />` | App.js:272 |
| `/manager-leads` | `<ManagerLeadsDashboard />` | App.js:285 |
| `/performance-dashboard` | `<PerformanceDashboard />` | App.js:322 |
| `/permission-dashboard` | `<PermissionDashboard />` | App.js:302 |
| `/go-live` | `<GoLiveDashboard />` | App.js:331 |

---

## 2. React Components (File Names)

| Component | File Path | Purpose |
|-----------|-----------|---------|
| `AdminDashboard` | `/pages/AdminDashboard.js` (28KB) | Primary admin dashboard with business overview |
| `Dashboard` | `/pages/Dashboard.js` (22KB) | Generic dashboard with domain routing |
| `SalesDashboard` | `/pages/SalesDashboard.js` (40KB) | Sales funnel analytics |
| `SalesDashboardEnhanced` | `/pages/SalesDashboardEnhanced.js` (37KB) | Alternative sales dashboard |
| `ConsultingDashboard` | `/pages/ConsultingDashboard.js` (15KB) | Consulting team overview |
| `HRDashboard` | `/pages/HRDashboard.js` (22KB) | HR metrics and employee stats |
| `ConsultantDashboard` | `/pages/ConsultantDashboard.js` (13KB) | Individual consultant view |
| `ManagerLeadsDashboard` | `/pages/ManagerLeadsDashboard.js` (27KB) | Manager-specific leads view |
| `PerformanceDashboard` | `/pages/PerformanceDashboard.js` (41KB) | Performance metrics |
| `PermissionDashboard` | `/pages/PermissionDashboard.js` (18KB) | Permission management |
| `GoLiveDashboard` | `/pages/GoLiveDashboard.js` (20KB) | Project go-live tracking |
| `HRPortalDashboard` | `/pages/HRPortalDashboard.js` (16KB) | **LEGACY** - Not routed |
| `DashboardLayoutA` | `/pages/DashboardLayoutA.js` (11KB) | **LEGACY** - Not routed |
| `AdminDashboardMockups` | `/pages/admin/AdminDashboardMockups.js` | Design mockups |

---

## 3. Conditions Used to Select Each Dashboard

### Primary Routing Logic (`App.js:174-188`):

```javascript
const getDefaultDashboard = () => {
  if (user?.role === 'consultant') {
    return <ConsultantDashboard />;           // Consultant role → ConsultantDashboard
  }
  if (isSalesUser) {                          // ['executive', 'sales_manager', 'manager']
    return <SalesDashboardEnhanced />;        // Sales roles → SalesDashboardEnhanced
  }
  if (user?.role === 'admin') {
    return <AdminDashboard />;                // Admin role → AdminDashboard
  }
  return <Dashboard />;                       // Everyone else → Dashboard (generic)
};
```

### Secondary Routing Logic (`Dashboard.js:127-136`):

```javascript
// Dashboard.js routes based on domain
if (userDomain === 'sales') return <SalesDashboard />;
if (userDomain === 'consulting') return <ConsultingDashboard />;
if (userDomain === 'hr') return <HRDashboard />;
// Otherwise shows generic stats
```

### Domain Detection (`Dashboard.js:20-38`):

| Condition | Domain |
|-----------|--------|
| Department contains 'hr' | `hr` |
| Department contains 'sales' | `sales` |
| Department contains 'consulting' | `consulting` |
| Role is `hr_manager`, `hr_executive` | `hr` |
| Role is `executive`, `sales_manager` | `sales` |
| Role contains `consultant` | `consulting` |
| Role is `admin`, `manager` | `admin` |
| Default | `general` |

---

## 4. Legacy Dashboards Still Active

| Dashboard | Status | Active Route | Notes |
|-----------|--------|--------------|-------|
| `HRPortalDashboard` | **ORPHANED** | None | Was part of old HR portal, still in codebase |
| `DashboardLayoutA` | **ORPHANED** | None | Alternative layout, never integrated |
| `AdminDashboardMockups` | **DEV ONLY** | `/admin-dashboard-mockups` | Design mockups, should be dev-only |
| `SalesDashboardEnhanced` | **ACTIVE** | Index route for sales | Duplicate of SalesDashboard |

### Duplicate Dashboard Issue:
- `SalesDashboard` - Routed at `/sales-dashboard`
- `SalesDashboardEnhanced` - Used as default for sales users at `/`

**Both exist and serve similar purposes**, creating maintenance overhead.

---

## 5. Default Dashboard for Admin Users

**Current Default:** `AdminDashboard` (via `getDefaultDashboard()`)

```javascript
// App.js:183-184
if (user?.role === 'admin') {
  return <AdminDashboard />;
}
```

**File:** `/app/frontend/src/pages/AdminDashboard.js`
**Title:** "Business Overview"
**Features:** Revenue, leads, meetings, projects, attendance, performance trend

---

## 6. Where RBAC Widget Was Added

| Dashboard | RBAC Widget | Line |
|-----------|-------------|------|
| `AdminDashboard.js` | ✅ Added | Line 162 |
| `Dashboard.js` | ✅ Added | Line 244 |
| `SalesDashboard.js` | ✅ Added | Line 145 |
| `SalesDashboardEnhanced.js` | ❌ Missing | - |
| `ConsultingDashboard.js` | ❌ Missing | - |
| `HRDashboard.js` | ❌ Missing | - |
| `ConsultantDashboard.js` | ❌ Missing | - |

---

## 7. Potential Inconsistencies

### Issue 1: Double Routing for Sales Users
- Sales user visits `/` → Gets `SalesDashboardEnhanced`
- Sales user visits `/sales-dashboard` → Gets `SalesDashboard`
- **Different dashboards for the same user type**

### Issue 2: Dashboard.js Domain Routing vs App.js Role Routing
- `App.js` routes by exact role match
- `Dashboard.js` re-routes by department and role keywords
- **Conflicting logic can cause unexpected behavior**

### Issue 3: Generic Dashboard Shows Domain Dashboards
- `Dashboard.js` for 'general' domain shows generic stats
- But it also routes to domain-specific dashboards
- **Redundant component hierarchy**

### Issue 4: Inconsistent RBAC Widget Presence
- Only 3 of 7 active dashboards have RBAC widget
- **Users see different permission information based on entry point**

### Issue 5: Orphaned Files Increasing Bundle Size
- `HRPortalDashboard.js` (16KB) - Never used
- `DashboardLayoutA.js` (11KB) - Never used
- **~27KB of dead code**

---

## Recommendations

### Canonical Admin Dashboard: `AdminDashboard.js`

This should be the **single source of truth** for admin users because:
1. It's explicitly routed for `admin` role
2. Has the most comprehensive "Business Overview"
3. Already has RBAC widget integrated
4. Named correctly for its purpose

### Step-by-Step Cleanup Plan

#### Phase 1: Add RBAC Widget to All Dashboards (Immediate)

```bash
# Files needing RBAC widget:
- ConsultingDashboard.js
- HRDashboard.js
- ConsultantDashboard.js
- SalesDashboardEnhanced.js
```

#### Phase 2: Consolidate Sales Dashboards

**Option A (Recommended):** Remove `SalesDashboardEnhanced.js`
```javascript
// App.js - Change:
if (isSalesUser) {
  return <SalesDashboard />;  // Use standard SalesDashboard
}
```

**Option B:** Merge features into one component

#### Phase 3: Remove Orphaned Files

```bash
# Safe to delete:
rm /app/frontend/src/pages/HRPortalDashboard.js
rm /app/frontend/src/pages/DashboardLayoutA.js
```

#### Phase 4: Simplify Dashboard.js

Remove the domain-based rendering from `Dashboard.js` since `App.js` already handles it:

```javascript
// Dashboard.js - Remove this block:
if (userDomain === 'sales') return <SalesDashboard />;
if (userDomain === 'consulting') return <ConsultingDashboard />;
if (userDomain === 'hr') return <HRDashboard />;
```

This creates a cleaner separation:
- `App.js` → Route selection
- `Dashboard.js` → Generic/fallback dashboard only

#### Phase 5: Restrict Dev-Only Routes

```javascript
// Only show in development
{process.env.NODE_ENV === 'development' && (
  <Route path="admin-dashboard-mockups" element={<AdminDashboardMockups />} />
)}
```

---

## Recommended Final Dashboard Architecture

| Role/Domain | Default Dashboard | Direct Route |
|-------------|-------------------|--------------|
| `admin` | `AdminDashboard` | `/admin-dashboard` |
| `consultant` | `ConsultantDashboard` | `/consultant-dashboard` |
| Sales roles | `SalesDashboard` | `/sales-dashboard` |
| HR roles | `HRDashboard` | `/hr-dashboard` |
| Consulting roles | `ConsultingDashboard` | `/consulting-dashboard` |
| Others | `Dashboard` (generic) | `/` |

### Files to Keep:
- `AdminDashboard.js` ✅
- `Dashboard.js` ✅ (simplified)
- `SalesDashboard.js` ✅
- `ConsultingDashboard.js` ✅
- `HRDashboard.js` ✅
- `ConsultantDashboard.js` ✅

### Files to Remove:
- `SalesDashboardEnhanced.js` ❌ (merge into SalesDashboard)
- `HRPortalDashboard.js` ❌ (orphaned)
- `DashboardLayoutA.js` ❌ (orphaned)
- `AdminDashboardMockups.js` ❌ (move to dev-only or delete)

### Expected Impact:
- **Bundle size reduction:** ~85KB
- **Maintenance reduction:** 4 fewer files
- **Consistency:** RBAC widget everywhere
- **Clearer routing:** Single source of truth in `App.js`
