# D&V Business Consulting - Comprehensive Business Management Application

## Product Overview
A comprehensive business management application for D&V Business Consulting, a 50-person HR consulting organization covering HR, Marketing, Sales, Finance, and Consulting projects.

---

## Latest Update (February 15, 2026 - Evening)

### P0 FEATURES IMPLEMENTED: Task Approval Workflow & Agreement E-Signature ✅

**Two major features completed:**

#### 1. Task Approval Workflow (In ConsultingScopeView)
- **Task Management UI**: Expandable scopes with tasks list
- **Add Task Dialog**: Name, description, priority, due date, assignee
- **Task Status Management**: pending, in_progress, completed, approved
- **Parallel Approval Flow**: Manager and Client approve independently
- **Approval Status Badges**: pending, manager_approved, client_approved, fully_approved, rejected
- **Request Approval Button**: Triggers approval workflow for completed tasks

**Backend Endpoints Added:**
- `POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks` - Create task
- `PATCH /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}` - Update task
- `POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/request-approval` - Request approval
- `POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve` - Process approval
- `GET /api/enhanced-sow/{sow_id}/tasks/pending-approvals` - Get pending approvals

#### 2. Agreement Page E-Signature (In AgreementView)
- **Canvas-Based Signature Pad**: Draw signature using mouse or touch
- **Clear Button**: Reset signature canvas
- **Signer Details Form**: Full Name, Designation, Email, Date
- **Sign Agreement Flow**: Captures signature image and stores in database
- **Backend Signature Storage**: Base64 encoded signature image saved

**Backend Endpoint Added:**
- `POST /api/agreements/{agreement_id}/sign` - E-sign agreement with canvas signature

**Frontend Routes Added:**
- `/sales-funnel/agreement/:agreementId` - View agreement with e-signature
- `/sales-funnel/agreement` - Create new agreement

**Files Modified:**
- `/app/frontend/src/pages/sales-funnel/ConsultingScopeView.js` - Task management UI
- `/app/frontend/src/pages/sales-funnel/AgreementView.js` - Canvas e-signature
- `/app/frontend/src/App.js` - Added AgreementView routes
- `/app/backend/routers/enhanced_sow.py` - Task CRUD and approval APIs
- `/app/backend/server.py` - Agreement signature endpoint

**Testing Status:** 100% PASSED (Backend: 10/10, Frontend: All verified)

---

## Previous Update (February 15, 2026)

### BUG FIXES: Proforma Invoice & Sales Flow Improvements ✅

**Issues Fixed:**

1. **PDF Export Format Fixed (P0)**
   - Updated `handleDownloadPDF` function with comprehensive print CSS styles
   - Modern layout now preserved in PDF download
   - All background colors, borders, and spacing render correctly

2. **Pricing Plan ID Now Visible in Dialog (P1)**
   - Dropdown now shows format: `Plan #ABC123 • 12 months (yearly) • ₹10,00,000`
   - Easy to distinguish between multiple pricing plans

3. **Custom Scopes Now Saved to Master List (P2)**
   - Backend enhanced to save custom scopes to `sow_scope_templates` collection
   - Custom scopes have `is_custom: true` flag
   - Available for future SOW selections

4. **Added Logo to Proforma Invoice**
   - D&V® logo icon displayed in invoice header
   - Professional branding with "Business Consulting" text

5. **Added "Save and Continue" Buttons Throughout Flow**
   - Green (emerald-600) buttons with arrow icons
   - Pricing Plan Builder: "Save & Continue to Scope Selection →"
   - SOW Selection: "Save & Continue to Proforma Invoice"
   - Create Invoice Dialog: "Save & Create Invoice"

**Files Modified:**
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js`
- `/app/frontend/src/pages/sales-funnel/SalesScopeSelection.js`
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js`
- `/app/backend/routers/enhanced_sow.py`

---

## Previous Update (December 15, 2026)

### FEATURE: Renamed Quotations to Proforma Invoice + Downloadable Invoice ✅

**Changes Made:**
1. **Renamed "Quotations" to "Proforma Invoice"** throughout the app
   - Navigation sidebar updated
   - All page titles and buttons updated
   - New route: `/sales-funnel/proforma-invoice`

2. **Added "Back to Previous Flow" Navigation**
   - "Back to Scope Selection" when coming from SOW selection
   - "Back to Pricing Plans" when accessed directly

3. **Downloadable Proforma Invoice View** (matching provided PDF template)
   - D&V® header with "TAX INVOICE" label
   - Invoice details: Invoice No., Date, Payment Terms
   - Company details: Address, GSTIN, State Code, Phone
   - Buyer (Bill to) section with client details
   - Line Items Table: SI No., Description of Services, HSN/SAC, Qty, Rate, Amount
   - Tax Breakdown: Taxable Value, CGST @ 9%, SGST @ 9%
   - Grand Total with Amount in Words (Indian Rupees format)
   - HSN Summary Table
   - Terms of Delivery (5 standard terms)
   - Company's Bank Details: Bank Name, A/c Holder, A/c No., Branch & IFS, SWIFT Code
   - Footer: "This is a Computer Generated Invoice"

4. **Download PDF & Send to Client buttons** for easy sharing

**Flow Now:**
```
Pricing Plan → SOW Selection → Proforma Invoice (with Download PDF option) → Agreement
```

---

### BUG FIX: Sales Funnel SOW Selection Flow ✅ (Dec 15, 2026)

**Issue Fixed:** The sales funnel workflow was broken - after selecting scopes on the SOW Selection page, the app was incorrectly redirecting.

**Changes Made:**
1. **SalesScopeSelection.js** - Updated UI:
   - Changed to table layout with 2 scopes per row
   - Removed scope descriptions (only shows scope name)
   - Maintained "Add Custom Scope" button
   - Fixed redirection to `/sales-funnel/proforma-invoice?pricing_plan_id=...`

2. **ProformaInvoice.js** (formerly Quotations.js) - Enhanced:
   - Now reads `pricing_plan_id` from URL query params
   - Auto-opens "Create Proforma Invoice" dialog when coming from SOW Selection
   - Pre-selects the correct pricing plan

---

### SOW List Views for Sales & Consulting ✅

**1. Sales SOW List Dashboard (`/sales-funnel/sow-list`):**
- Lists all SOWs created by sales team
- Stats: Total SOWs, Draft, Handed Over, In Progress
- Search by client/company
- Status filter dropdown
- Actions per SOW:
  - Edit (navigate to scope selection)
  - View (navigate to SOW review)
  - Handover (locks SOW and sends to consulting)
  - Quotation (proceed to quotation flow)

**2. Consulting My Projects Dashboard (`/consulting/projects`):**
- Lists all projects handed over to consulting
- Stats: Total Projects, Pending Kickoff, Active, Completed
- Progress circle showing completion percentage
- Scope status breakdown (not started, in progress, completed, N/A)
- Actions per Project:
  - View Scopes (detailed scope view with Gantt/Kanban)
  - Tasks (navigate to task management)

**3. Project Tasks Page (`/consulting/project-tasks/:sowId`):**
- Task list view showing all scopes as tasks
- Per-task tracking: Status, Progress %, Days, Meetings
- File upload per task
- Two approval workflows:
  - "Send to Manager" - Internal approval
  - "Send to Client" - External approval
- Select specific scopes for approval requests

**4. Updated Navigation:**
- Sales: Added "SOW List" menu item
- Consulting: Added "My Projects" menu item

**Flow:**
```
Pricing Plan → Scope Selection → SOW List (Sales)
                                     ↓ [Handover]
                              My Projects (Consulting)
                                     ↓
                              Project Tasks (Add/Edit/Upload)
                                     ↓
                              Send for Approval (Manager/Client)
```

### Previous: Gantt Chart Library Integration ✅ (Feb 15, 2026)

**Implemented comprehensive role-based SOW (Scope of Work) workflow:**

**1. SOW Master Management (Admin)**
- 8 default categories: Sales, HR, Operations, Training, Analytics, Digital Marketing, Finance, Strategy
- 41+ pre-defined scope templates under each category
- Admin can add/edit/delete categories and scope templates
- Custom scopes auto-save to master for future use

**2. Sales Team SOW Selection (Simple View)**
- Checkbox list of scopes grouped by category
- Select multiple scopes from master data
- Add custom scopes (auto-saves to master)
- Visual selection counter showing selected scope count
- Search functionality to filter scopes
- Creates "Original Scope Snapshot" - locked, immutable record

**3. Consulting Team SOW View (Detailed)**
- See all assigned scopes (inherited from Sales)
- Can ADD new scopes (PM, Consultant, Principal Consultant roles)
- CANNOT DELETE any scopes (conflict prevention)
- Track per scope:
  - Status: Not Started | In Progress | Completed | Not Applicable
  - Progress percentage (0-100%)
  - Days spent (not hours - as per user requirement)
  - Meetings count
  - Notes
  - Attachments
- **4 View Modes:**
  - List View (grouped by category)
  - Kanban Board (columns: Not Started → In Progress → Completed → N/A)
  - Gantt Chart (timeline visualization)
  - Timeline View (milestone-based)

**4. Scope Revision Workflow**
- Revision statuses: Pending Review | Confirmed | Revised | Not Applicable
- Mandatory reason for revisions
- Client consent tracking
- Change log for audit trail

**5. Roadmap Approval Workflow**
- Submit roadmap for client approval (Monthly/Quarterly/Yearly cycles)
- Client consent document upload (email/document proof)
- Approval history tracking
- Variance report: Original vs Current scopes

**6. Conflict Prevention Features**
- Original Scope Snapshot (locked, never editable)
- Change reason mandatory for modifications
- Client consent flag for changes
- Complete audit trail (who, when, why)
- No delete policy - status changes only

**New Routes:**
- `/sales-funnel/scope-selection/:pricingPlanId` - Sales team scope selection
- `/sales-funnel/sow-review/:pricingPlanId` - Consulting team scope view

**New API Endpoints:**
- `GET /api/sow-masters/categories` - List SOW categories
- `POST /api/sow-masters/categories` - Create category
- `GET /api/sow-masters/scopes` - List scope templates
- `GET /api/sow-masters/scopes/grouped` - Get scopes grouped by category
- `POST /api/sow-masters/scopes` - Create scope template
- `POST /api/sow-masters/seed-defaults` - Seed default data
- `POST /api/enhanced-sow/:planId/sales-selection` - Create SOW from selection
- `GET /api/enhanced-sow/:sowId` - Get enhanced SOW
- `GET /api/enhanced-sow/by-pricing-plan/:planId` - Get SOW by pricing plan
- `PATCH /api/enhanced-sow/:sowId/scopes/:scopeId` - Update scope
- `POST /api/enhanced-sow/:sowId/scopes` - Add scope (consulting team)
- `POST /api/enhanced-sow/:sowId/roadmap/submit` - Submit for approval
- `POST /api/enhanced-sow/:sowId/consent-documents` - Upload consent
- `GET /api/enhanced-sow/:sowId/variance-report` - Variance report
- `GET /api/enhanced-sow/:sowId/change-log` - Full change log

---

### Previous Updates

### Custom Payments, Notes & Agreement Sections ✅ (Feb 15, 2026)

**1. Custom (Irregular) Payment Schedule:**
- New "Custom (Irregular)" option in Payment Schedule dropdown
- Users can manually define each payment with custom date, amount, description
- Validation for total matching project value

**2. Notes & Descriptions Section:**
- 4 textarea fields for notes: Pricing, Team Deployment, Payment Terms, General

**3. Agreement Sections Configuration:**
- 8 toggleable checkboxes to control agreement visibility

### Bug Fixes & Enhancements ✅
- Multiple Team Members Bug Fix (race condition)
- Dynamic Payment Count Display
- Conveyance Summary Tooltip

### Lumpsum Conveyance Feature ✅
- Changed from percentage-based to lumpsum amount
- Distributed evenly across all payment periods

### Payment Plan Breakup Feature ✅
- Top-Down Pricing Model: Total Client Investment drives all calculations
- Admin Masters Module for Tenure Types with allocation percentages

---

## Code Architecture

```
/app/
├── backend/
│   ├── .env
│   ├── models/
│   │   └── enhanced_sow.py          # NEW: Enhanced SOW models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── masters.py               # Admin Masters CRUD
│   │   ├── sow_masters.py           # NEW: SOW Categories & Scopes
│   │   └── enhanced_sow.py          # NEW: Enhanced SOW workflow
│   ├── sales_workflow.py
│   ├── requirements.txt
│   ├── server.py
│   └── tests/
│       └── test_enhanced_sow.py     # NEW: 21 test cases
└── frontend/
    └── src/
        ├── App.js                   # Updated: new routes
        ├── components/
        │   └── Layout.js
        └── pages/
            ├── AdminMasters.js
            └── sales-funnel/
                ├── SalesScopeSelection.js    # NEW: Sales team UI
                ├── ConsultingScopeView.js    # NEW: Consulting team UI
                ├── PricingPlanBuilder.js
                ├── SOWBuilder.js             # Legacy SOW (still available)
                └── ...
```

---

## Technical Stack

### Frontend
- React 18
- Tailwind CSS
- Shadcn/UI components
- date-fns for date handling

### Backend
- FastAPI
- Pydantic models
- Motor (async MongoDB driver)
- JWT authentication

### Database
- MongoDB

---

## Test Credentials

- **Admin:** admin@company.com / admin123
- **Manager:** manager@company.com / manager123
- **Executive:** executive@company.com / executive123

---

## Upcoming Tasks (P1)

1. **P&L Variance Tracking**
   - Implement logic to flag over-delivery (actual vs. committed meetings)

2. **Employee Cost Integration**
   - Integrate with HR/Payroll data to pull actual employee CTC

3. **Project P&L Dashboard**
   - Dashboard showing committed vs. actual costs and revenue

4. **SMTP Email Integration**
   - Replace mock email with real SMTP for roadmap approval notifications

---

## Future Tasks (P2)

1. **Finance Module**
   - Full P&L, invoicing, and revenue recognition

2. **Detailed Reporting**
   - Role-wise and client-wise profitability reports

3. **Rocket Reach Integration**
   - Lead enrichment from Rocket Reach API

---

## Backlog (P3)

1. Marketing Flow Module
2. Finance & Accounts Flow Module
3. **Refactor server.py** - Break monolithic file into modular FastAPI routers
4. **Refactor PricingPlanBuilder.js** - Break into smaller components

---

## Mocked Features

- **Email sending** - Currently logs to console (SMTP not integrated)

---

## 3rd Party Integrations

- **Emergent-managed Google Auth** - Domain restricted (@dvconsulting.co.in)
- **gantt-task-react** - React Gantt chart library for consulting SOW timeline visualization

---

## Key Files Reference

- `/app/backend/server.py` - Main API server
- `/app/backend/routers/masters.py` - Admin Masters module
- `/app/backend/routers/sow_masters.py` - **NEW** SOW Categories & Scopes
- `/app/backend/routers/enhanced_sow.py` - **NEW** Enhanced SOW workflow
- `/app/backend/models/enhanced_sow.py` - **NEW** Enhanced SOW data models
- `/app/frontend/src/pages/sales-funnel/SalesScopeSelection.js` - **NEW** Sales scope selection
- `/app/frontend/src/pages/sales-funnel/ConsultingScopeView.js` - **NEW** Consulting scope view
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js` - Pricing plan builder
- `/app/memory/PRD.md` - This file

---

## Test Reports

- `/app/test_reports/iteration_27.json` - Latest test report (21/21 backend tests passed)
- `/app/backend/tests/test_enhanced_sow.py` - Enhanced SOW test suite
