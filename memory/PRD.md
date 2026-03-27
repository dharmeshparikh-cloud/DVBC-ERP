# D&V Business Consulting - ERP System PRD

## Original Problem Statement
Establish a unified and strict governance model across the ERP. Build customized HR, Consulting, and Sales modules with a full E2E Sales Funnel (Lead Capture -> Meeting -> Pricing Plan -> SOW -> Quotation -> Agreement -> Payment -> Kickoff -> Project).

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **AI**: GPT-4o-mini via Emergent LLM Key
- **Maps**: Google Maps API (Places Autocomplete)

## What's Been Implemented

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
- `/app/frontend/src/pages/sales-funnel/AgreementView.js` - PDF template
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` - No team deployment
- `/app/frontend/src/pages/sales-funnel/PaymentVerification.js` - Prefill

## P1 - Upcoming Tasks
- Consultant Notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI
- Onboarding timeline view
