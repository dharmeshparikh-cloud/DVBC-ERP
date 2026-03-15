# D&V Business Consulting ERP - Product Requirements Document

## Original Problem Statement
Build a comprehensive ERP system for D&V Business Consulting to manage:
- Sales funnel (Leads → Meetings → Pricing → Quotations → Agreements → Kickoffs)
- HR functions (Onboarding, Attendance, Leaves, Expenses)
- Team management and performance tracking
- Financial reporting and approvals

## User Personas
- **Admin**: Full system access
- **Sales Manager/Principal Consultant**: Lead management, team oversight
- **Sales Executive**: Lead creation, meeting scheduling
- **HR Manager**: Employee onboarding, attendance management
- **Consultants**: Client meetings, expense claims

## Core Requirements

### 1. Single Source of Truth (SSOT) - COMPLETED ✅
- **Lead** entity is the master record for company, contact, email, phone
- All downstream forms (Meeting, Quotation, Agreement) start by selecting a Lead
- Master fields are auto-filled and read-only in downstream forms
- Duplicate lead detection (by email, phone, company name)

**Implementation Status:**
- Backend SSOT endpoints: `/api/leads/ssot/search`, `/api/leads/ssot/master-data/{lead_id}`, `/api/leads/ssot/check-duplicates`
- LeadSelector component integrated into:
  - ProformaInvoice.js (Quotations route)
  - Agreements.js
- Quotations.js file exists but not used in routing

### 2. Authentication System - COMPLETED ✅
- Persistent UUID stored in user document (`id` field)
- Single source of truth: `backend/routers/deps.py` → `get_current_user_from_token()`
- All 57+ backend files standardized to use deps.py

### 3. Profile Performance Dashboard - COMPLETED ✅
- ProfilePerformanceCard integrated into Sales and Manager dashboards
- ProfilePhotoUpload component for HR onboarding
- Photo storage and retrieval via `/api/employees/{id}/photo-upload`

### 4. UI Testability - COMPLETED ✅
- `data-testid` attributes added to all interactive elements
- Audit documented in UI_AUDIT.md

## Completed Work (December 2025)

### Session 1:
- Fixed "Lead Not Found" bug (non-persistent UUID issue)
- Standardized backend authentication across ~57 files
- Completed UI audit with data-testid attributes
- Verified 3 critical flows: Kickoff→Client, Expense→Reimbursement, Follow-up escalation

### Session 2 (Current):
- **SSOT Frontend Integration** - COMPLETED
  - ProformaInvoice.js: LeadSelector integrated (lines 867-907)
  - Agreements.js: LeadSelector integrated (lines 679-733)
  - Pricing Plan/Quotation dropdowns disabled until lead is selected
  - Master data displayed in amber card with lock icon
- **MOM PDF Download** - VERIFIED WORKING
  - Accessible from Business Overview → "View Full MOM Report & Download PDF"
  - ManagerMOMReview.js page with Download PDF button functional

## Outstanding Issues (P2)
1. Large file needs refactoring: `backend/routers/kickoff.py`
2. Complex component needs refactoring: `frontend/src/pages/MeetingRecord.js`
3. Orphan file to remove: `frontend/src/pages/consulting/Meetings.js`
4. Orphan file not used in routing: `frontend/src/pages/sales-funnel/Quotations.js`

## Future Tasks (P2)
1. Build DVBC Marketing Hub
2. Implement Consultant Incentive System
3. Implement Internal Chat System
4. Audit Consultant Expense Submission governance

## Technical Architecture

### Backend Structure
```
backend/
├── routers/
│   ├── deps.py         # Auth dependency (SINGLE SOURCE)
│   ├── auth.py         # Login/logout endpoints
│   ├── leads.py        # Lead management + SSOT endpoints
│   ├── employees.py    # Employee + photo management
│   └── [others]        # All import from deps.py
└── models/
    └── user.py         # User model with persistent id
```

### Frontend Structure
```
frontend/src/
├── components/
│   ├── LeadSelector.jsx      # SSOT lead selection
│   ├── dashboard/
│   │   ├── ProfilePerformanceCard.jsx
│   │   └── ProfilePhotoUpload.jsx
│   └── ui/                   # Shadcn components
├── pages/
│   ├── sales-funnel/
│   │   ├── ProformaInvoice.js   # /sales-funnel/quotations
│   │   ├── Agreements.js
│   │   └── [others]
│   └── ManagerMOMReview.js      # MOM PDF download
└── hooks/
    └── useApi.js
```

## Test Credentials
- Admin: `EMP001` / `admin123`
- HR Manager: `EMP002` / `hr123`
- Sales Executive: `EMP003` / `sales123`

## Last Updated
2025-12-15 - SSOT Integration Complete, MOM PDF Verified
