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
- **Unified 9-step stepper header** on ALL funnel pages with "Next action" guide
- Funnel progress bar shows X/9 on leads table
- Batch auto-sync for stage updates
- No manual closed_won - status managed by funnel
- Only `closed` (project created) = onboarded

### FunnelStepperHeader Component (27 Mar 2026)
- 9-step stepper with green checkmarks for completed steps
- "Next: [Step] - [What to do]" guide with Go button
- Clickable completed/current steps for navigation

### Proforma Invoice (COMPLETE - 27 Mar 2026)
- GSTIN validation + Bill To details
- PDF amounts fixed
- Lead-scoped when from funnel

### Onboarded Clients (COMPLETE - 27 Mar 2026)
- Standalone page at `/onboarded-clients`
- Only leads with completed 9-step funnel (status=closed)

### VVS Lead Fix (COMPLETE - 28 Mar 2026)
- Fixed project auto-creation order
- Fixed funnel-progress to verify project EXISTS in DB
- Fixed PaymentVerification model, SOW detection, bulk auto-sync

### Sales Dashboard Scorecard Fix (COMPLETE - 28 Mar 2026)
- **Root cause**: 3 critical data source mismatches in analytics.py
  - `meeting_records` (0 docs) -> `meetings` (44 docs)
  - `agreement_payments` (0 docs) -> `payment_verifications` (3 docs)
  - kickoff status `"accepted"` -> `["approved", "accepted", "converted"]`
- Fixed all 7 analytics endpoints (funnel-summary, my-funnel-summary, funnel-trends, bottleneck-analysis, forecasting, win-loss, velocity)
- Added follow-up stats integration to dashboard scorecards
- Admin now sees ALL leads in team view (not filtered by employee ownership)
- Frontend: Added Follow-ups card to team overview, Meetings + Follow-ups stats to ProfilePerformanceCard
- Test results: 15/15 backend tests passed, 100% frontend verified

## Credentials
| Role | Employee ID | Password |
|---|---|---|
| Admin | EMP001 | admin123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

## Key Files
- `/app/frontend/src/pages/SalesDashboard.js` - Dashboard UI with scorecards
- `/app/frontend/src/components/ProfilePerformanceCard.jsx` - Profile + stats card
- `/app/backend/routers/analytics.py` - All analytics endpoints (FIXED)
- `/app/backend/routers/leads.py` - SSOT for funnel progress
- `/app/backend/routers/kickoff.py` - Kickoff & project creation

## P1 - Upcoming Tasks
- Consultant Notifications when assigned to project/SOW

## P2 - Future/Backlog
- Refactor ConsultingMeetings.js (>2300 lines)
- Governance Dashboard UI
- Onboarding timeline view in Onboarded Clients page
