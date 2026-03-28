# D&V Business Consulting - ERP System PRD

## Original Problem Statement
Establish a unified and strict governance model across the ERP. Build customized HR, Consulting, and Sales modules with a full E2E Sales Funnel (Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project).

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-4o-mini via Emergent LLM Key
- **Maps**: Google Maps API (Places Autocomplete)

## What's Been Implemented

### Mobile App Attendance Status Fix (28 Mar 2026)
- **Fixed**: Mobile app was showing "Rejected" for valid check-ins
- **Root Cause**: App was checking `approval_status` field which didn't exist on normal check-ins
- **Solution**: Added helper functions `isCheckInApproved()` and `isCheckInPending()` that:
  - Check `approval_status` if it exists
  - Fallback to `status === 'present' || status === 'half_day'` for approval
- **Files Updated**: `/app/frontend/src/pages/EmployeeMobileApp.js`

### Button Uniformity & Duplicate Fix (28 Mar 2026)
- **Fixed duplicate "Record Meeting" buttons** on Sales Funnel Step 2
  - Removed duplicate button from content area
  - Single "Record Meeting" button now appears in footer area only
  - When step is completed: Shows "Next Step" (outlined) + "Record Meeting" (primary blue)
- **Standardized button styling across sales funnel pages**:
  - Previous/Back buttons: Ghost variant with zinc colors
  - Continue/Next buttons: Emerald green when step completed, Blue when pending
  - Primary action buttons: Blue (Record Meeting) or Emerald (Proceed to Pricing)
- **Improved navigation flow**:
  - "Back to Funnel" button text when navigating from funnel context
  - "Back to Leads" when no funnel context
  - All back buttons consistent with `hover:bg-zinc-100 text-zinc-600` styling

### Sales Funnel (COMPLETE)
- 9-step funnel: Lead -> Meeting -> Pricing -> SOW -> Proforma Invoice -> Agreement -> Payment -> Kickoff -> Project
- Unified 9-step stepper header on ALL funnel pages
- Funnel progress bar shows X/9 on leads table
- Batch auto-sync for stage updates

### Sales Dashboard Scorecard Fix (28 Mar 2026)
- Fixed 3 critical data source mismatches in analytics.py
- All 7 analytics endpoints now use correct collections
- Follow-up stats integrated into dashboard

### Funnel Blocker Overhaul (28 Mar 2026)
- **Removed all hard blockers** EXCEPT "First installment not verified -> Cannot create kickoff"
- Agreement no longer requires PC/Admin approval — immediately `active` on creation
- Kickoff no longer requires PC internal approval or client email confirmation
- Kickoff auto-creates project immediately on submit (if first installment verified)

### Kickoff Auto-Create Project (28 Mar 2026)
- Project ID format changed to `PR-DDMMYY-XXX` (e.g., PR-270326-001)
- On kickoff submit: auto-generate project, create client user, set lead to `closed`
- No dual approval flow — single-step project creation

### Agreement Revamp (28 Mar 2026)
- Complete rewrite of AgreementView as professional PDF-printable HTML template
- **All data inherited**: Lead info, SOW (category + deliverables), Team Deployment (role, meeting type, count, meetings — no rate per meeting), Payment Schedule (basic, GST, net, due date), Total Investment, Project Duration, Start/End dates
- **Legal clauses**: NDA (24 months), NCA (24 months), Anti-Poaching (24 months), IP, Liability, Termination, Dispute Resolution, Governing Law, Force Majeure, Entire Agreement
- **Signature blocks**: Both parties (D&V + Client)
- **Download .docx**: Browser-compatible Word export for editing
- **Print/PDF**: Direct browser print
- Logo centered on top, no headers/footers

### Agreement Email with Attachments (28 Mar 2026)
- **Send via Email button** on Agreement view page with dynamic recipient dialog
- Backend generates PDF (via `weasyprint`) and DOCX attachments with:
  - Company logo at the top
  - All agreement sections (Scope, Team, Investment, Terms)
  - **Consultant Undertaking & Obligations** section (from DV_Consultant_Obligations.docx) before signatures
  - Signature blocks for both parties
- Professional email template with agreement summary
- Dynamic recipient selection (email + name) from frontend dialog
- API endpoint: `POST /api/agreements/{id}/send-email` with body `{recipient_email, recipient_name}`
- **Key Payment Terms** (7 clauses): Fees & Taxes, Advance/Milestone, Payment Timeline (7 days), Delay & Suspension (18% p.a.), Non-Refundable, Discontinue Terms (30 days notice), Other Expenses
- **Due Date column** in payment schedule (calculated from start date + duration)
- **Date format**: DD-MM-YYYY throughout
- **Total row** in payment schedule (Basic, GST @18%, Net Amount)

### Agreements Management Page (28 Mar 2026)
- **New page at `/agreements`** with table view: Agreement No, Client Name, Start Date, End Date, Version, Actions
- **Navigation**: Under Sales dropdown in sidebar
- **Actions**: View, Edit, Download (PDF/DOCX), Sync from Funnel
- **Versioning**: 
  - Version badge (v1, v2, v3...) with history dropdown
  - Auto-increment on sync or edit
  - Full version history stored with timestamps and change logs
- **Auto-sync triggers**: When Pricing Plan, SOW, or Team data changes → Agreement auto-updates + version++
- **RBAC**: Admin + Sales roles only | Consultant: 403 Forbidden
- **Funnel page update**: Shows read-only preview with "View in Agreements Management" link
- **API endpoints**:
  - `GET /api/agreements/management/list` - Table data
  - `POST /api/agreements/{id}/sync` - Manual sync from funnel
  - `PUT /api/agreements/{id}/edit` - Edit metadata (creates new version)
  - `GET /api/agreements/{id}/versions` - Version history

### Proforma Invoice Updates (28 Mar 2026)
- Removed Team Deployment block from PDF
- Bill To shows client company name + GSTIN only (no personal details)

### Start Date Validation (28 Mar 2026)
- PricingPlanBuilder: start_date cannot be < today
- MeetingRecord: meeting_date cannot be < today
- Kickoff: expected_start_date cannot be < today (backend)
- Agreement: start_date cannot be < today (backend)

### Payment Verification Prefill (28 Mar 2026)
- First installment amount prefilled from pricing plan schedule_breakdown
- Inherited via /agreements/{id}/full endpoint

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/backend/routers/kickoff.py` - Auto project creation
- `/app/backend/routers/agreements.py` - Simplified + /full endpoint
- `/app/backend/routers/leads.py` - No agreement blocking
- `/app/backend/routers/analytics.py` - Fixed analytics
- `/app/frontend/src/pages/SalesFunnelOnboarding.js` - Main funnel page with unified button layout
- `/app/frontend/src/pages/sales-funnel/AgreementView.js` - PDF template
- `/app/frontend/src/pages/sales-funnel/MeetingRecord.js` - Standardized back & proceed buttons
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js` - Context-aware back navigation
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` - No team deployment
- `/app/frontend/src/pages/sales-funnel/PaymentVerification.js` - Prefill

### Onboarding Reminder Email Fix (28 Mar 2026)
- **Fixed**: Reminder email generated broken link (`/onboarding/{token}` instead of `/onboarding/candidate/{token}`)
- **Root Cause**: URL path mismatch — invite used `/onboarding/candidate/{token}` matching frontend route, but reminder omitted `/candidate/` segment
- **Fix**: Updated `send_onboarding_reminder` in `onboarding.py` line 1658

### Onboarding Excel Download/Upload (28 Mar 2026)
- **Download Blank Form**: Generates `.xlsx` with Section/Field/Value columns (22 fields, empty values)
- **Download Filled Form**: Generates `.xlsx` pre-filled with current form data
- **Upload Filled Excel**: Parses uploaded `.xlsx`, auto-fills matching fields, triggers auto-save
- **Library**: SheetJS (xlsx v0.18.5)
- **File**: `/app/frontend/src/pages/onboarding/CandidateOnboardingForm.js`

### Role Selection During Onboarding Completion (28 Mar 2026)
- **Role dropdown in Complete Onboarding dialog**: HR selects system role (Employee, Consultant, Executive, HR Manager, etc.) before generating Employee ID
- **Role threaded through full chain**: Complete endpoint → employee record → Go-Live request → user account creation
- **Default**: Falls back to "employee" if no role selected

### CTC Approval Gate & Role Permissions (28 Mar 2026)
- **CTC now requires Admin approval**: `POST /api/ctc/design` sets status to `pending` (was auto-approved)
- **CTC Approval Dialog**: Enhanced with Employee Details section (name, code, department, designation, submitted by), CTC Overview (annual, previous, change %, effective month), salary components table, summary, and approve/reject with comments
- **Go-Live approval opened to HR**: `approve/reject_go_live_request` now allows `hr_manager` role (was Admin-only)
- **Go-Live visible to HR**: Pending Go-Live section and data query now available to HR roles in Approvals Center
- **Admin notification**: Admins get notified when new CTC structures are pending approval
- **Document View**: Added `GET /api/onboarding/public/{token}/documents/{document_id}` endpoint to serve uploaded docs
- **Frontend View link**: Now points to the backend serving endpoint instead of broken `uploaded.url`
- **Thank You page**: Enhanced with candidate name, position, submission date, document count, status badge, and "What Happens Next?" steps
- **Upload error handling**: Added client-side file size (5MB) and type validation before upload
- **Submit redirect**: Added `justSubmitted` state to force Thank You page display immediately after submission
- **Declaration fix**: Backend now sets `declaration_signed = True` when `declaration.signed` is present in submit data
- **Auto Go-Live**: Completing onboarding now auto-creates a Go-Live request in the Approvals Center

## P1 - Upcoming Tasks
- Consultant Notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI
- Onboarding timeline view
