# D&V Business Consulting ERP - Product Requirements Document

## Original Problem Statement
Build a comprehensive ERP system for D&V Business Consulting to manage:
- Sales funnel (Leads → Meetings → Pricing → Quotations → Agreements → Kickoffs)
- HR functions (Onboarding, Attendance, Leaves, Expenses)
- Team management and performance tracking
- Financial reporting and approvals

## Core Requirements - Completed

### 1. Single Source of Truth (SSOT) ✅
- Lead entity is the master record for company, contact, email, phone
- LeadSelector component integrated into downstream forms
- Duplicate lead detection implemented

### 2. Pricing Plan → Downstream Inheritance ✅
- Team Deployment LOCKED in Agreements (read-only from Pricing Plan)
- Rate per Meeting hidden everywhere, visible only to Admin
- SOW Auto-Generate from Team Deployment roles

### 3. Edit Protection on Approved Items ✅
**SOW Items:**
- Draft, Pending Review: Editable by Sales users
- Approved, In Progress, Completed: Locked (Lock icon) for non-admin
- Admin can edit ALL items (override)

**Agreements:**
- Draft, Pending Approval: Editable
- Approved, Signed, Sent: Locked (Lock icon) for non-admin
- Admin can edit ALL items (override)

### 4. Authentication System ✅
- Persistent UUID in user document
- Single source: `backend/routers/deps.py`

## Implementation Details

### SOW Edit Protection (SOWBuilder.js)
```javascript
// Line 217-222
const isItemEditable = (item) => {
  if (user?.role === 'admin') return true;
  const lockedStatuses = ['approved', 'completed', 'in_progress'];
  return !lockedStatuses.includes(item.status);
};
```

### Agreement Edit Protection (Agreements.js)
```javascript
// Line 401-406
const isAgreementEditable = (agreement) => {
  if (user?.role === 'admin') return true;
  const lockedStatuses = ['approved', 'signed', 'sent'];
  return !lockedStatuses.includes(agreement?.status);
};
```

### Role-Based Rate Visibility
| Form | Admin Sees | Others See |
|------|------------|------------|
| PricingPlanBuilder | Rate/Meeting, Breakup | Hidden |
| ProformaInvoice | Rate, Subtotal | Hidden |
| Agreements | Rate/Meeting | Hidden |

## Test Data Created
- Lead: `064a02cf-2af5-4ef5-ba11-b886ccf30618` (Edit Protection Testing Corp)
- Pricing Plan: `pp-1773594505087` (with team deployment)
- SOW: `c0cb6976-da92-4c14-bd3d-cff065a517dc` (5 items with various statuses)
- Quotation: `6913d321-6b97-49f8-940c-4056f0a1b87b`
- Agreements: 6 total (draft, approved, signed, sent, pending_approval)

## Test Credentials
- **Admin**: `EMP001` / `admin123` (sees all rates, can edit locked items)
- **Sales**: `EMP003` / `sales123` (rates hidden, locked items show Lock icon)

## Outstanding Issues (P2)
1. Large file: `backend/routers/kickoff.py`
2. Complex component: `frontend/src/pages/MeetingRecord.js`
3. Orphan files to review

## Future Tasks
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System
- Audit Consultant Expense Submission governance

## Last Updated
2025-12-15 - Edit Protection implemented and tested for SOW items
