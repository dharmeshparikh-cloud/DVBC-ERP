# DVBC - NETRA: Business Management ERP

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication (Employee ID + Client ID)
- **AI**: GPT-4o via Emergent LLM Key
- **Documentation**: python-docx, reportlab for PDF/DOCX generation
- **Email**: SMTP via SendGrid

---

## Completed Work - February 2026

### Phase 38: Access Control Fixes & E2E Kickoff Flow Testing - February 23, 2026 ✅ (Latest)

**Access Control Fixes:**
- ✅ **Sales Executives CAN create agreements** (previously only managers)
- ✅ **Reporting Managers can approve agreements** (manager, sr_manager, sales_manager, principal_consultant, admin)
- ✅ **Client-facing communications require Principal Consultant approval**
  - Send-to-client endpoint now requires PC or Admin role
  - Error message: "Only Principal Consultant can send client-facing communications"

**E2E Kickoff Flow Tested Successfully:**
1. ✅ Create Lead (Sales Executive)
2. ✅ Record Meeting
3. ✅ Create Pricing Plan
4. ✅ Create Quotation
5. ✅ Create Agreement (Sales Executive - now allowed)
6. ✅ Approve Agreement (Reporting Manager)
7. ✅ Verify First Installment Payment
8. ✅ Create Kickoff Request
9. ✅ Principal Consultant Internal Approval → Project ID Generated (PROJ-20260223-0001)
10. ✅ Client Approval via Token Link → Client User Created (98000)
11. ✅ Client Portal Login Successful

**Test Client Credentials:**
- Client ID: `98000`
- Project: `PROJ-20260223-0001`
- Company: E2E Test Company Ltd

---

### Phase 37: All Projects Consultant Assignment UI - February 23, 2026 ✅

**New All Projects Page (Principal Consultant View):**
- ✅ Created `/all-projects` route accessible to Principal Consultant, Senior Consultant, Admin
- ✅ Shows ALL projects with assignment status indicators
- ✅ Projects needing assignment highlighted with amber left border and "Needs Assignment" badge
- ✅ Stats banner showing Total Projects and Needs Assignment counts
- ✅ Filter buttons: All, Needs Assignment, Assigned
- ✅ Search by project name, client, or ID
- ✅ Assign Consultant dialog with role selection and meeting commitment
- ✅ Assignment History dialog showing full history of assignments
- ✅ Unassign consultant functionality (preserves history)

**New Backend Endpoints:**
- `GET /api/projects/all/for-assignment` - Returns all projects with assignment details
- `POST /api/projects/{id}/assign-consultant` - Assigns a consultant to project
- `DELETE /api/projects/{id}/unassign-consultant/{consultant_id}` - Removes consultant (preserves history)
- `PATCH /api/projects/{id}/change-consultant` - Replace one consultant with another
- `GET /api/projects/{id}/assignment-history` - Full history of assignments

**Testing Results:**
- 100% backend test pass rate (13/13 tests)
- 100% frontend UI verification
- Access control verified (PC001, SC001 can access; CON001 gets 403)

---

### Phase 36: Client Portal UI Redesign - February 23, 2026 ✅

**Client Portal Light Theme Alignment:**
- ✅ **ClientLogin.js** - Completely redesigned to match main ERP Login.js
  - Black left panel with feature cards (Project Dashboard, Documents, Payments, Meeting Notes)
  - White right panel with login card and D&V logo
  - Black/white color scheme matching main ERP
  - "Back to Employee Login" navigation link
  - Remember My Client ID checkbox
  - All data-testid attributes added for testing
  
- ✅ **ClientPortal.js** - Updated to light theme
  - White background with black text
  - Black selected project in sidebar
  - Consistent card styling with black/10 borders
  - Added Change Password navigation button in header
  - All API paths fixed to use /api/ prefix
  
- ✅ **ClientChangePassword.js** - Completely redesigned
  - Matching black left panel + white right panel layout
  - Password security tips in left panel
  - D&V logo in header
  - All API paths fixed to use /api/ prefix
  - Password requirements checker with visual feedback

**Testing Results:**
- 100% test pass rate (29/29 frontend tests)
- Visual consistency verified between Client Login and Main Login
- Mobile responsiveness verified
- Form functionality working correctly

---

### Phase 35: Principal Consultant + Client Dual Approval - February 23, 2026 ✅

**Dual Approval Flow (Completely Redesigned):**

1. **Internal Approval (Principal Consultant ONLY)**
   - Only `principal_consultant` and `admin` can approve (removed Senior Consultant)
   - When approved:
     - Project ID generated: `PROJ-YYYYMMDD-XXXX` (locked, auto-generated)
     - Status: `internal_approved`
     - Sales team notified: "Project Approved"
     - Internal team email: "New Project Added"
     - Client receives approval email

2. **Client Approval (External)**
   - Client clicks secure link from email
   - Can confirm/change project start date
   - When approved:
     - Status: `approved`
     - Client user account created (ID: `98XXX` format, 5-digit)
     - Welcome email with NETRA credentials
     - All stakeholders notified

3. **Client Portal Access**
   - Client ID: 5-digit sequential starting from `98000`
   - Auto-generated password (must change on first login)
   - Admin can reset password

**New Database Models:**
- `ClientUser` - Client portal accounts
- `ProjectAssignment` - Consultant assignment with history tracking

**New Endpoints:**
- `POST /api/kickoff-requests/{id}/accept` - Principal Consultant approval
- `GET /api/kickoff-requests/client-approve/{token}` - Client approval page
- `POST /api/kickoff-requests/client-approve/{token}/confirm` - Client confirms with start date

**Status Flow:**
```
pending → internal_approved → approved → converted
```

**Email Notifications:**
1. To Client: Project approval email with confirm button
2. To Internal Team: New Project Added notification
3. To Client: Welcome email with NETRA credentials
4. To All Stakeholders: Project Activated (start date confirmed)

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
