# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture where all consulting meetings, MOM, and associated expenses are recorded through a single, controlled interface.

---

## Current Implementation Status: ✅ P0 Complete

### P0 Features Implemented (March 18, 2026)

#### 1. Email Notification System ✅
- **Test Email Endpoint**: `/api/meeting-workflow/test-email` - Verify SMTP configuration
- **Meeting Invite Endpoint**: `/api/meeting-workflow/send-invite` - Sends branded email to clients
- **Email Templates**: Professional HTML templates with D&V Business Consulting branding
- **SMTP Integration**: Using Gmail SMTP configured in backend/.env

#### 2. Single-Use Tokenized Links ✅
- **Token Generation**: Secure 32-byte tokens using `secrets.token_urlsafe()`
- **Token Expiry**: 24 hours from creation
- **Single-Use**: Token marked as used after first response
- **Client Response Endpoint**: `/api/meeting-workflow/client-response` (GET/POST)
- **Branded Response Page**: `/meeting-response?token={token}&action={action}`

#### 3. Auto-Accept Logic ✅
- **Process Endpoint**: `/api/meeting-workflow/process-auto-accept` (Admin only)
- **Logic**: Meetings with expired tokens (>24h) are auto-accepted
- **Status Update**: SCHEDULED → AUTO_ACCEPTED
- **Note**: Requires scheduled task/cron job in production

#### 4. Meeting State Machine ✅
- **10 States Implemented**:
  - DRAFT → SCHEDULED
  - SCHEDULED → CONFIRMED / REJECTED / RESCHEDULED / AUTO_ACCEPTED / CANCELLED
  - CONFIRMED → CONDUCTED / CANCELLED
  - AUTO_ACCEPTED → CONDUCTED / CANCELLED
  - RESCHEDULED → SCHEDULED / CANCELLED
  - CONDUCTED → MOM_RECORDED
  - MOM_RECORDED → DELIVERED

- **State Transition Endpoint**: `/api/meeting-workflow/transition-state`
- **Audit Logging**: All state changes logged with timestamp, user, and reason

#### 5. Frontend Integration ✅
- **Invite Button**: Added to Consulting Meetings list (green "Invite" button)
- **Status Badges**: Shows "Awaiting Response", "Confirmed", "Declined" states
- **Client Response Page**: Branded page with Accept/Decline/Reschedule options
- **Google Calendar Integration**: "Add to Calendar" link after acceptance

---

## Meeting Workflow Business Rules

### PART 1: SCHEDULING RULES
| Rule | Value |
|------|-------|
| Who can schedule | Any consultant assigned to the project |
| Minimum notice | 24 hours before meeting time |
| Short notice (<24h) | Allowed but flagged |
| Past date scheduling | NOT ALLOWED - all meetings must be scheduled first |

### PART 2: NOTIFICATION FLOW
| Event | Recipients |
|-------|------------|
| Meeting Scheduled | Client + Reporting Manager + All Attendees |
| Notification Timing | Immediate + 24h reminder |
| Client Response Options | Accept / Reject / Request Reschedule |
| If Rejected | Auto-cancelled, consultant + manager notified |
| If No Response | Auto-accepted (within 24h link expiry) |

### PART 3: SINGLE-USE LINK MECHANISM
- **Link Actions:** Accept / Reject / Reschedule with Notes + Preferred Times
- **Link Expiry:** 24 hours with expiring rule tooltip
- **After Response:** Confirmation page + Add to Calendar option

### PART 4: MEETING STATES
```
DRAFT → SCHEDULED → CONFIRMED → CONDUCTED → MOM_RECORDED → DELIVERED
                  ↘ REJECTED
                  ↘ RESCHEDULED → SCHEDULED
                  ↘ AUTO_ACCEPTED → CONDUCTED
                  ↘ CANCELLED
```

### PART 5: EXPENSE & CONVEYANCE RULES
| Rule | Value |
|------|-------|
| When can expense be claimed | Only during MOM recording |
| Cancelled/Rejected meetings | No expenses allowed |
| Rescheduled meetings | Fresh quota (new meeting) |
| Who can claim conveyance | Only the meeting scheduler |
| Travel companions | Added to their calendar, cannot claim separately |

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
| `/api/meeting-workflow/meeting-states` | GET | Get all valid states | Public |

### Consulting Meetings APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/meetings` | GET | List all meetings |
| `/api/meetings/{id}` | GET | Get meeting details |
| `/api/meetings/{id}/send-mom` | POST | Send MOM to client |
| `/api/consulting-meetings/tracking` | GET | Get project tracking stats |

---

## Pending Implementation

### P1 - High Priority (Next)
1. **Backdated Meeting Approval**
   - Flag meetings >24h old as requiring approval
   - Manager approval workflow with notifications
   - Approval endpoint and UI

2. **SSOT Breach Testing**
   - Verify consultants can't create meetings elsewhere
   - Test calendar read-only mode

### P2 - Medium Priority
1. **Business Logic Document (PDF)**
   - Generate documentation for the workflow
   - Export as PDF for stakeholders

---

## Future Tasks/Backlog
- Refactor `ConsultingMeetings.js` into smaller components (1500+ lines)
- Implement scheduled cron job for auto-accept processing
- Add reminder emails (24h before meeting)
- Implement rescheduling workflow (new date selection)
- Refactor `backend/routers/kickoff.py`
- Refactor `frontend/src/pages/MeetingRecord.js`
- Remove orphan file: `frontend/src/pages/consulting/Meetings.js`
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System

---

## Files Created/Modified (This Session)

### New Files
- `/app/backend/routers/meeting_workflow.py` - Meeting workflow API router
- `/app/backend/services/meeting_notification_service.py` - Email notification service
- `/app/frontend/src/pages/MeetingResponse.js` - Client response branded page

### Modified Files
- `/app/backend/routers/models.py` - Added MeetingStatus class and workflow fields to Meeting model
- `/app/backend/server.py` - Registered meeting_workflow router, added consulting-meetings/tracking endpoint
- `/app/frontend/src/pages/ConsultingMeetings.js` - Added Invite button and handleSendInvite function
- `/app/frontend/src/App.js` - Added MeetingResponse route

---

## Credentials
- **Admin:** EMP001 / admin123
- **Test Email:** dharmesh.parikh@dvconsulting.co.in

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB, aiosmtplib
- Email: Gmail SMTP

---

## Testing Summary

### Test Report: /app/test_reports/iteration_189.json
- **Backend**: 93% pass rate (14/15 tests)
- **Frontend**: 100% pass rate
- **State Machine**: All 7 transitions validated
- **Email**: Test emails sent successfully

---

## Last Updated
- Date: March 18, 2026
- Status: P0 Complete - Email Notification System, Single-Use Tokens, Auto-Accept Logic, Meeting State Machine
