# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture where all consulting meetings, MOM, and associated expenses are recorded through a single, controlled interface.

---

## Meeting Workflow Business Rules (Finalized)

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

| Transition | Who Can Do It |
|------------|---------------|
| Draft → Scheduled | Consultant |
| Scheduled → Confirmed | Client (via link) |
| Scheduled → Rejected | Client (via link) |
| Scheduled → Rescheduled | Client (via link) |
| Scheduled → Auto_Accepted | System (24h no response) |
| Confirmed → Conducted | System (auto) or Consultant |
| Conducted → MOM_Recorded | Consultant |
| MOM_Recorded → Delivered | Consultant (sends to client) |
| Confirmed → Cancelled | Client only (consultant cannot cancel) |

### PART 5: EXPENSE & CONVEYANCE RULES
| Rule | Value |
|------|-------|
| When can expense be claimed | Only during MOM recording |
| Cancelled/Rejected meetings | No expenses allowed |
| Rescheduled meetings | Fresh quota (new meeting) |
| Who can claim conveyance | Only the meeting scheduler |
| Travel companions | Added to their calendar, cannot claim separately |
| Duplicate claim detection | Blocked with clarification message |

### PART 6: UNSCHEDULED/BACKDATED MEETINGS
| Rule | Value |
|------|-------|
| Record without scheduling | NOT ALLOWED - all must be scheduled first |
| Backdated entries (>24h) | Requires Manager + Client confirmation |
| Client notification for backdated | Yes, with MOM |

### PART 7: AUDIT & COMPLIANCE
| What is logged | Details |
|----------------|---------|
| State changes | Timestamp, User, IP address |
| Notifications | All emails/SMS sent |
| Client responses | Via single-use link |
| Audit access | Role-based (Admin full, Manager team, Consultant own) |

---

## SSOT Architecture
- **Consulting Meetings page** is the sole entry point for scheduling and MOM
- All other meeting creation methods disabled
- Calendar functions as planning tool only (read-only)

---

## Form Fields

### Schedule Meeting Form
- Project* (dropdown)
- Client (auto-filled from project, read-only)
- SOW* (dropdown with refresh button)
- Meeting Purpose* (dropdown)
- Date* (date picker)
- Start Time* (time picker)
- End Time* (time picker)
- Duration (calculated, read-only)
- Mode* (Online / In-person / Tele Call)
- Agenda Items (multiple)
- Attendees (multi-select)
- Notes

### For In-Person Meetings (Travel Details)
- Travel Companions (multi-select consultants)
- Purpose of Accompanying (dropdown)
- Vehicle Type (dropdown)
- Vehicle Number (optional)
- Start Location
- End Location

**Note:** Expense claiming is NOT available during scheduling. Only during MOM recording.

---

## UI Requirements
- Add tooltip with every action
- Visual workflow indicator showing meeting states
- SOW selection mandatory with real-time refresh
- Same SOW UI in both Schedule and MOM forms
- Clear color coding for different states
- Short notice and validation warnings

---

## What's Implemented (Current State)

### Completed Features
1. **Consulting Meetings Page (SSOT)**
   - Full page with tabs: Meetings list and Commitment Tracking
   - Stats cards: Scheduled, MOM Submitted, Sent to Client, Pending Tasks
   - Advanced filters: Projects, Companies, Status, Date range
   - Meeting list with columns and MOM actions

2. **Meeting Creation Form**
   - Project selection with auto-filled client
   - SOW selection with refresh button (mandatory)
   - Meeting Purpose dropdown
   - Date/Time pickers with duration auto-calculation
   - Mode selection (Online/Offline/Tele Call)
   - Agenda items with add/remove
   - Attendees multi-select
   - Travel details for in-person meetings

3. **MOM Recording**
   - Discussion points, decisions made
   - Action items with assignments
   - SOW scope selection
   - File attachments
   - Send to client functionality

4. **How it Works Guide**
   - Meeting lifecycle explanation
   - Status meanings
   - SOW scopes explanation
   - Expense/travel rules

5. **Backend APIs**
   - Meeting CRUD operations
   - MOM save and send
   - Consulting meetings tracking endpoint

---

## Pending Implementation

### P0 - Critical (In Progress)
1. **Email Notification System**
   - Send meeting invites to clients
   - Single-use tokenized links for Accept/Reject/Reschedule
   - 24-hour auto-accept logic
   - Manager notifications

2. **Meeting State Machine**
   - Implement full state transitions
   - Track state changes in audit log
   - Enforce business rules on transitions

### P1 - High Priority
1. **Backdated Meeting Approval**
   - Manager approval workflow
   - Client confirmation for backdated MOM

2. **SSOT Breach Testing**
   - Verify all alternative meeting creation paths are disabled

### P2 - Medium Priority
1. **Business Logic Document (PDF)**
   - Generate documentation for the workflow

---

## Future Tasks/Backlog
- Refactor `ConsultingMeetings.js` into smaller components
- Refactor `backend/routers/kickoff.py`
- Refactor `frontend/src/pages/MeetingRecord.js`
- Remove orphan file: `frontend/src/pages/consulting/Meetings.js`
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System

---

## Credentials
- **Admin:** EMP001 / admin123

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB

---

## Last Updated
- Date: March 18, 2026
- Status: Consulting Meetings page fully functional
- Fixed: Added missing `/api/consulting-meetings/tracking` endpoint
