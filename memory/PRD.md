# D&V Business Consulting ERP - Product Requirements Document

## Original Problem Statement
Build a comprehensive ERP system for D&V Business Consulting to manage:
- Sales funnel (Leads → Meetings → Pricing → Quotations → Agreements → Kickoffs)
- HR functions (Onboarding, Attendance, Leaves, Expenses)
- Team management and performance tracking
- Financial reporting and approvals

## User Personas
- **Admin**: Full system access, sees all rates and financial data
- **Sales Manager/Principal Consultant**: Lead management, team oversight (no rate visibility)
- **Sales Executive**: Lead creation, meeting scheduling (no rate visibility)
- **HR Manager**: Employee onboarding, attendance management
- **Consultants**: Client meetings, expense claims

## Core Requirements

### 1. Single Source of Truth (SSOT) - COMPLETED ✅
- **Lead** entity is the master record for company, contact, email, phone
- All downstream forms (Meeting, Quotation, Agreement) start by selecting a Lead
- Master fields are auto-filled and read-only in downstream forms
- Duplicate lead detection (by email, phone, company name)

### 2. Pricing Plan → Downstream Inheritance - COMPLETED ✅
- **Team Deployment LOCKED in Agreements** - Read-only from Pricing Plan
- **Rate per Meeting** - Hidden everywhere, visible only to Admin
- **SOW Auto-Suggest** - Categories based on team roles from Pricing Plan

### 3. Authentication System - COMPLETED ✅
- Persistent UUID stored in user document (`id` field)
- Single source of truth: `backend/routers/deps.py` → `get_current_user_from_token()`

## Implementation Status

### Session 1 Completed:
- Fixed "Lead Not Found" bug (non-persistent UUID issue)
- Standardized backend authentication across ~57 files
- Completed UI audit with data-testid attributes
- Verified 3 critical flows: Kickoff→Client, Expense→Reimbursement, Follow-up

### Session 2 Completed:
1. **SSOT Frontend Integration**
   - LeadSelector integrated into ProformaInvoice.js and Agreements.js
   - Pricing Plan/Quotation dropdowns disabled until lead is selected

2. **Locked Team Deployment in Agreements**
   - Team deployment section is read-only
   - Shows Lock icon and "locked from Pricing Plan" notice
   - No add/remove buttons visible

3. **Role-Based Rate Visibility**
   | Form | Admin | Non-Admin |
   |------|-------|-----------|
   | PricingPlanBuilder | Sees Rate/Meeting, Breakup (₹) | Hidden |
   | ProformaInvoice | Sees Rate, Subtotal | Hidden |
   | Agreements | Sees Rate/Meeting | Hidden |

4. **SOW Auto-Generate Feature**
   - "Auto-Generate from Team Deployment" button added
   - Maps team roles to SOW categories automatically
   - Creates pre-filled SOW items with descriptions

5. **MOM PDF Download** - VERIFIED WORKING

## Role-to-Category Mapping (SOW)
```javascript
{
  'Lead Consultant': 'sales',
  'Principal Consultant': 'sales',
  'HR Consultant': 'hr',
  'Operations Consultant': 'operations',
  'Training Consultant': 'training',
  'Analytics Consultant': 'analytics',
  'Digital Marketing Consultant': 'digital_marketing'
}
```

## Outstanding Issues (P2)
1. Large file: `backend/routers/kickoff.py`
2. Complex component: `frontend/src/pages/MeetingRecord.js`
3. Orphan file: `frontend/src/pages/consulting/Meetings.js`
4. Unused file: `frontend/src/pages/sales-funnel/Quotations.js`

## Future Tasks (P2)
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System
- Audit Consultant Expense Submission governance

## Technical Architecture

### Key Files Modified This Session
```
frontend/src/pages/sales-funnel/
├── Agreements.js          # Locked team deployment, role-based rates
├── ProformaInvoice.js     # Role-based rate visibility
├── PricingPlanBuilder.js  # Role-based columns
└── SOWBuilder.js          # Auto-generate from team
```

## Test Credentials
- **Admin**: `EMP001` / `admin123` (sees all rates)
- **Sales**: `EMP003` / `sales123` (rates hidden)
- **HR Manager**: `EMP002` / `hr123`

## Last Updated
2025-12-15 - SSOT Complete, Pricing Plan inheritance implemented, Role-based rate visibility
