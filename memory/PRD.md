# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication (Employee ID only)
- **AI**: GPT-4o via Emergent LLM Key
- **Documentation**: python-docx, reportlab for PDF/DOCX generation
- **Email**: SMTP via SendGrid

---

## Completed Work - February 2026

### Phase 35: Dual Approval Kickoff Flow - February 23, 2026 ✅ (Latest)

**Kickoff Dual Approval System:**
Kickoff requests now require BOTH approvals before project creation:
1. **Principal Consultant / Senior Consultant** approval (internal)
2. **Client** approval (via email link)

**Flow:**
1. Sales creates kickoff → Status: `pending`
2. Senior/Principal Consultant approves → Status: `consultant_approved`, email sent to client
3. Client clicks approval link in email → Status: `approved`
4. Project auto-created, consultant assigned to consulting hierarchy

**New Endpoints:**
- `POST /api/kickoff-requests/{id}/accept` - Consultant approval (updated)
- `GET /api/kickoff-requests/client-approve/{token}` - Client approval page
- `POST /api/kickoff-requests/client-approve/{token}/confirm` - Client confirms

**Model Updates:**
- `KickoffRequest` model extended with dual approval fields:
  - `consultant_approved`, `consultant_approved_by`, `consultant_approved_at`
  - `client_approved`, `client_approved_by`, `client_approved_at`
  - `client_approval_token` (for secure email links)

**Status Values:**
- `pending` - Waiting for first approval
- `consultant_approved` - Consultant approved, waiting for client
- `client_approved` - Client approved, waiting for consultant
- `approved` - Both approved, project being created
- `converted` - Project created successfully

**Approval Roles:**
- Only `senior_consultant` and `principal_consultant` can approve kickoffs (NOT PM, NOT regular consultant)
- Approval Center updated to show kickoffs only for these roles

---

### Phase 34: Email Templates Preview & Agreement Blocking - February 23, 2026 ✅

**Email Template Previews:**
- ✅ Added `/api/test/email-preview/{template_name}` - HTML preview endpoint
- ✅ Added `/api/test/email-preview-json/{template_name}` - JSON summary endpoint  
- ✅ All 5 templates with Indian test data (TCS, Priya Sharma, etc.)
- ✅ Templates include D&V logo (2x broader - 100px height) on light gray header
- ✅ Agreement email includes: View, Download, Upload, Edit, Approve, Reject buttons
- ✅ Kickoff Accepted email includes "Edit Start Date" option
- ✅ "Approve Agreement" button added to blocking banner

**Agreement Status Blocking:**
- ✅ Modified `/api/leads/{id}/funnel-progress` to detect blocking
- ✅ New fields: `is_blocked`, `blocked_reason`, `blocked_at_step`
- ✅ Blocks progression to Payment, Kickoff, Complete if agreement is:
  - `pending`, `draft`, `review`, or `rejected`
- ✅ Frontend blocking banner with red warning
- ✅ "Review Agreement" + "Approve Agreement" buttons for quick action
- ✅ "Agreement Approval Required" disabled button on blocked steps

---

### Phase 33: Sales Funnel Email Notifications - February 23, 2026 ✅

**HTML Email Notifications at Key Milestones:**
- ✅ **MOM Filled** - When meeting with MOM is recorded
- ✅ **Proforma Generated** - When quotation is created  
- ✅ **Agreement Created** - When service agreement is created
- ✅ **Kickoff Sent** - When kickoff request is submitted for approval
- ✅ **Kickoff Accepted** - When kickoff is approved and project created

**Email Features:**
- Professional HTML templates with DVBC branding
- Includes all relevant details (amounts, dates, people)
- Client expectations and key commitments summary
- Direct links to relevant pages in NETRA
- Background tasks - non-blocking email sending

**Backend Changes:**
- NEW: `/app/backend/services/funnel_notifications.py` - Email templates
- Modified: meetings.py, quotations.py, agreements.py, kickoff.py

---

### Phase 32: Sales Funnel Training & Draft System - February 23, 2026 ✅

**Progress Checklist for New Salespeople:**
- ✅ Added `GET /api/leads/{id}/funnel-checklist` endpoint
- ✅ Returns detailed requirements checklist for each step
- ✅ Shows completion status (Done/Pending) with progress bar
- ✅ "Tips for New Salespeople" expandable section with guidance
- ✅ Required vs optional requirements marked

**Offline Meeting Attachments:**
- ✅ Added `POST /api/meetings/{id}/attachments` - Upload photo/voice files
- ✅ Added `GET /api/meetings/{id}/attachments` - List meeting attachments
- ✅ Added `GET /api/meetings/{id}/attachments/{attachment_id}/download` - Download file
- ✅ Added `DELETE /api/meetings/{id}/attachments/{attachment_id}` - Remove attachment
- ✅ Added `GET /api/meetings/lead/{id}/attachments` - All attachments for a lead
- ✅ First offline meeting requires photo/voice attachment (mandatory)
- ✅ Attachments stored with meeting and inherited downstream to kickoff

**Funnel Draft System:**
- ✅ Added `POST /api/leads/{id}/funnel-draft` - Save funnel position
- ✅ Added `GET /api/leads/{id}/funnel-draft` - Get active draft
- ✅ Added `DELETE /api/leads/{id}/funnel-draft` - Discard draft
- ✅ Added `GET /api/leads/funnel-drafts/all` - List all user's funnel drafts
- ✅ Auto-saves current step position when navigating funnel
- ✅ Resume from where left off when clicking on a lead

**Frontend Updates:**
- ✅ SalesFunnelOnboarding.js - Completion Checklist with progress bar
- ✅ SalesFunnelOnboarding.js - Tips for new salespeople (expandable)
- ✅ MeetingRecord.js - File upload UI for offline meetings
- ✅ MeetingRecord.js - Attachment preview before submission
- ✅ MeetingRecord.js - First offline meeting validation

---

### Phase 31: Sales Funnel E2E Complete - February 22, 2026 ✅

**Sales Funnel Progress Tracking:**
- ✅ Added `GET /api/leads/{id}/funnel-progress` endpoint
- ✅ Returns: completed_steps, current_step, total_steps (9), progress_percentage
- ✅ 9 stages: lead_capture → record_meeting → pricing_plan → scope_of_work → quotation → agreement → record_payment → kickoff_request → project_created

**Meeting-Lead Linkage:**
- ✅ Added `POST /api/meetings/record` - Record sales meeting with MOM
- ✅ Added `GET /api/meetings/lead/{id}` - List all meetings for a lead
- ✅ MOM (Minutes of Meeting) required before submission
- ✅ Client expectations and key commitments captured
- ✅ Meeting history shown in kickoff details with funnel summary

**Leads Page:**
- ✅ Auto-redirect to Sales Funnel after lead creation
- ✅ Lead list with Score badges, Progress, Status dropdowns
- ✅ **Funnel** button on each row to start onboarding

---

### Phase 30: Expense Approval UI Enhancements - February 22, 2026 ✅

**Enhanced Expense Approval Cards:**
- ✅ **Receipts** button - Opens dialog showing uploaded receipts
- ✅ **Send Back** dialog - For revision with comments
- ✅ **Modify Amount** dialog - Approve with modified amount
- ✅ Withdrawal capability for pending requests
- ✅ Unified ApprovalCard.js component

---

## Upcoming Tasks

### P0 - High Priority
1. **DVBC Marketing Hub** - Build marketing dashboard and campaign management

### P1 - Medium Priority  
2. **Full Performance Analysis** - Database optimization and API response times
3. **Consultant Incentive System** - Commission tracking and payouts

### P2 - Lower Priority
4. **Internal Chat System** - Team messaging
5. **AI Assistant** - GPT-powered help
6. **"Day 0" Onboarding Tour** - Interactive guide for new users

---

## Test Credentials
- **Admin:** ADMIN001 / test123
- **Sales Executive:** SE001 / test123
- **HR Manager:** HR001 / password123
- **Project Manager:** PM001 / test123

---

## Key API Endpoints

### Sales Funnel
- `GET /api/leads/{id}/funnel-progress` - Get funnel completion status
- `GET /api/leads/{id}/funnel-checklist` - Get step-by-step requirements
- `POST /api/leads/{id}/funnel-draft` - Save funnel position
- `GET /api/leads/{id}/funnel-draft` - Get resume position

### Meetings
- `POST /api/meetings/record` - Record meeting with MOM
- `GET /api/meetings/lead/{id}` - List lead's meetings
- `POST /api/meetings/{id}/attachments` - Upload photo/voice
- `GET /api/meetings/{id}/attachments` - List attachments

### Kickoff
- `GET /api/kickoff-requests/{id}/details` - Full details with funnel summary

---

## Database Collections
- `leads` - Lead information
- `meetings` - Meeting records with MOM
- `meeting_attachments` - Photo/voice files for meetings
- `funnel_drafts` - User's funnel position tracking
- `pricing_plans`, `sows`, `quotations`, `agreements` - Sales documents
- `kickoff_requests` - Project kickoff approvals
