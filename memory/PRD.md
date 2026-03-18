# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture where all consulting meetings, MOM, and associated expenses are recorded through a single, controlled interface.

---

## Implementation Status

### ✅ P0 Features Complete (March 18, 2026)

#### 1. Email Notification System
- **Test Email**: `/api/meeting-workflow/test-email`
- **Meeting Invite**: `/api/meeting-workflow/send-invite` - Branded email with Accept/Reject/Reschedule buttons
- **SMTP**: Gmail configured in backend/.env

#### 2. Single-Use Tokenized Links (24h expiry)
- Secure token generation using `secrets.token_urlsafe()`
- Client response page: `/meeting-response?token={token}&action={action}`
- Branded UI with D&V Business Consulting branding

#### 3. Auto-Accept Background Scheduler
- Runs every hour automatically
- Processes meetings with expired tokens (>24h)
- Admin can manually trigger: `/api/meeting-workflow/process-auto-accept`
- Status check: `/api/meeting-workflow/auto-accept-scheduler/status`

#### 4. Meeting State Machine
- 10 States: DRAFT → SCHEDULED → CONFIRMED/REJECTED/RESCHEDULED/AUTO_ACCEPTED → CONDUCTED → MOM_RECORDED → DELIVERED
- State transition API with validation and audit logging

---

### ✅ P1 Features Complete (March 18, 2026)

#### 1. Backdated Meeting Manager Approval Workflow
- **Request Approval**: `/api/meeting-workflow/request-backdated-approval`
  - Sends email notification to direct reporting manager
  - Creates audit trail with reason for late recording
- **Approve/Reject**: `/api/meeting-workflow/approve-backdated`
  - Only direct manager or admin can approve
  - Sends confirmation email to requester
- **View Pending**: `/api/meeting-workflow/pending-approvals`
  - Lists meetings awaiting approval for current user

#### 2. SSOT Breach Prevention Verified
- **Consulting Meetings page**: SSOT with Invite button, MOM recording, expense claims
- **Calendar page**: Read-only planning view with no create meeting button
- **Notice displayed**: "To create or manage consulting meetings and MOM, please use the Consulting Meetings page (Single Source of Truth)"

#### 3. Reschedule Form Improvements
- Date/time pickers for suggesting up to 3 preferred times
- Minimum date set to tomorrow
- Additional notes field for context

#### 4. Travel & Conveyance Expense Section (SSOT for Expenses)
- Appears in MOM dialog ONLY for in-person meetings (mode = 'offline')
- Fields: Start/End Location, Travel Mode, Distance, Round Trip toggle
- Calculates estimated reimbursement automatically
- SSOT badge: "SSOT for Expenses"
- Note: Only meeting scheduler can claim conveyance

---

## Meeting Workflow States

```
DRAFT → SCHEDULED → CONFIRMED → CONDUCTED → MOM_RECORDED → DELIVERED
                  ↘ REJECTED
                  ↘ RESCHEDULED → SCHEDULED
                  ↘ AUTO_ACCEPTED → CONDUCTED
                  ↘ CANCELLED

For Backdated Meetings:
DRAFT → PENDING_APPROVAL → APPROVED → CONDUCTED → MOM_RECORDED → DELIVERED
                        ↘ REJECTED
```

---

## API Endpoints Reference

### Meeting Workflow APIs
| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/meeting-workflow/test-email` | GET | Send test email | Required |
| `/api/meeting-workflow/send-invite` | POST | Send meeting invitation | Required |
| `/api/meeting-workflow/client-response` | GET | Get meeting details for token | Public |
| `/api/meeting-workflow/client-response` | POST | Submit client response | Public |
| `/api/meeting-workflow/transition-state` | POST | Transition meeting state | Required |
| `/api/meeting-workflow/process-auto-accept` | POST | Process expired tokens | Admin |
| `/api/meeting-workflow/auto-accept-scheduler/status` | GET | Scheduler status | Admin |
| `/api/meeting-workflow/meeting-states` | GET | Get all valid states | Public |
| `/api/meeting-workflow/request-backdated-approval` | POST | Request approval | Required |
| `/api/meeting-workflow/approve-backdated` | POST | Approve/reject backdated | Manager/Admin |
| `/api/meeting-workflow/pending-approvals` | GET | List pending approvals | Required |

---

## SSOT Architecture

### Single Source of Truth Entry Points
| Feature | Entry Point | Notes |
|---------|-------------|-------|
| Schedule Meeting | Consulting Meetings page | Only place to create consulting meetings |
| Record MOM | Consulting Meetings page | MOM button in actions column |
| Claim Expenses | MOM Dialog | Travel section for in-person meetings only |
| Send Invite | Consulting Meetings page | Invite button sends client notification |

### Disabled Entry Points (Breach Prevention)
- Calendar page: Read-only, no create meeting button
- Other meeting forms: Not accessible for consultants

---

## Travel & Expense Rules

| Rule | Value |
|------|-------|
| When to claim | Only during MOM recording |
| Who can claim | Only the meeting scheduler |
| Travel companions | Cannot claim separately |
| In-person only | Travel section appears only for offline meetings |
| Calculation | Based on travel mode and distance |

### Travel Modes
- Own Car: ₹X/km
- Own Bike: ₹X/km  
- Public Transit: Manual entry
- Accompanied: No claim (traveled with someone else)

---

## Files Created/Modified

### New Files (This Session)
- `/app/backend/routers/meeting_workflow.py` - Meeting workflow APIs (780+ lines)
- `/app/backend/services/meeting_notification_service.py` - Email templates
- `/app/backend/services/meeting_auto_accept_scheduler.py` - Background scheduler
- `/app/frontend/src/pages/MeetingResponse.js` - Client response branded page

### Modified Files
- `/app/backend/routers/models.py` - MeetingStatus class, workflow fields
- `/app/backend/server.py` - Router registration, scheduler startup/shutdown
- `/app/frontend/src/pages/ConsultingMeetings.js` - Invite button, Travel expense section in MOM
- `/app/frontend/src/App.js` - MeetingResponse route

---

## Testing Summary

### Test Reports
- `/app/test_reports/iteration_188.json` - Initial frontend tests
- `/app/test_reports/iteration_189.json` - P0 features verification
- `/app/backend/tests/test_backdated_approval.py` - Backend pytest

### Results
- Backend: 100% pass rate
- Frontend: 100% pass rate
- All 10 meeting states validated
- SSOT breach prevention verified

---

## Pending/Future Tasks

### P2 - Medium Priority
- Business Logic Document (PDF export)
- Refactor ConsultingMeetings.js (2400+ lines)

### Backlog
- 24h reminder emails before meetings
- Rescheduling workflow (new date selection by organizer)
- Consultant incentive system
- Internal chat system
- DVBC Marketing Hub

---

## Credentials
- **Admin:** EMP001 / admin123
- **Test Email:** dharmesh.parikh@dvconsulting.co.in

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB, aiosmtplib
- Background Tasks: asyncio scheduler

---

## Last Updated
- Date: March 18, 2026
- Status: P0 + P1 Complete
