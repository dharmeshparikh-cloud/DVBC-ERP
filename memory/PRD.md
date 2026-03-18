# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture where all consulting meetings, MOM, and associated expenses are recorded through a single, controlled interface.

## Core Requirements

### SSOT Architecture
- **Consulting Meetings page** is the sole entry point for recording MOM and expenses
- All other meeting creation methods disabled
- Calendar functions as planning tool only (read-only)

### Governance & Business Logic
- Prevent duplicate expense submissions
- Enforce meeting quotas based on project's pricing_plan
- Implement approval workflow for meetings exceeding quota
- Link SOW scopes to meetings with validation
- Enforce attendance validation for in-person meetings before MOM submission

### UI/UX Requirements
- Advanced filters (client, project, date range) on Consulting Meetings page
- Full-page meeting detail view (printable)
- File attachment capabilities for MOMs
- SOW scope selection with search/filter for large scope lists

---

## What's Been Implemented

### Session: March 18, 2026

#### On-Screen Clarifications for User Confusion (All 7 Items)

1. **Meeting Lifecycle Terminology**
   - Renamed confusing labels: "Delivered" → "MOM Submitted", "Pending" → "Awaiting MOM"
   - Added visual lifecycle flow: Schedule → Conduct → Record MOM → Send to Client
   - Removed duplicate stats (With MOM = Delivered)

2. **Committed Meetings Explanation**
   - Added tooltip and Help Guide section explaining "Committed" = total meetings quota from SOW
   - Example provided: "If contract says 22 meetings over 6 months, Committed = 22"

3. **SOW Scopes Clarification**
   - Committed Scopes = deliverables from original SOW (sales handoff)
   - Additional Scopes = change requests added after project start
   - "Why locked?" explanation: maintains audit trail

4. **Navigation Guide**
   - Added "How it Works" button in header
   - Comprehensive dialog explaining where to go for each task
   - Quick Actions section showing button functions

5. **Action Buttons Clarity**
   - Added View (eye) icon for meetings with MOM
   - Tooltips on hover explaining each button
   - MOM button shows "Edit" if MOM already recorded

6. **Expense Tracking Location**
   - Added Travel Expenses section in Help Guide
   - Navigation path: My Workspace → My Expenses

7. **Attendance Validation Rule**
   - Added In-Person Meeting Rule section
   - Clear explanation: must mark attendance before MOM submission
   - Navigation path: My Workspace → My Attendance

#### UI Improvements
- Stats cards with tooltips: Scheduled, MOM Submitted, Sent to Client, Pending Tasks
- Single "MOM Status" column (merged from Status + MOM columns)
- Help icons (?) indicating hover for more info

---

## Architecture

### Frontend Routes
- `/consulting-meetings` - Main SSOT page for managing meetings
- `/meeting/:meetingId` - Full-page meeting detail view
- `/meeting-calendar` - Planning-only calendar view
- `/consulting/efforts-summary` - Reporting dashboard

### Key Files
- `frontend/src/pages/ConsultingMeetings.js` - SSOT meeting management
- `frontend/src/pages/MeetingDetail.js` - Full-page meeting view (NEW)
- `frontend/src/pages/MeetingCalendar.js` - Planning tool (MODIFIED)
- `backend/routers/enhanced_sow.py` - SOW scope management API

### API Endpoints
- `GET /api/enhanced-sow/project/{project_id}/scopes-for-meeting` - Filtered scopes for meeting
- `PUT /api/meeting-schedules/meetings/{id}/complete-and-send` - Save MOM with scopes
- `GET /api/meetings/{id}` - Get meeting details

---

## Pending Tasks

### P0 - SSOT Enforcement (Completed)

1. **Generic `/meetings` route** → Already redirects to `/leads` (existing design)
2. **Meeting Calendar** → Converted to planning-only view (New Schedule disabled)
3. **Consulting Dashboard** → Quick action link updated to `/consulting-meetings`
4. **Consulting Meetings** → Remains the SSOT for all consulting MOM

**Meeting Creation Points After SSOT:**
- `/consulting-meetings` - Consulting project meetings (SSOT)
- `/sales-funnel/meeting/record` - Sales meetings (separate workflow)
- `/kickoff-meeting` - Project initiation (one-time, NOT counted in quota)

**Kickoff vs Committed Meetings:**
- Kickoff meetings are NOT counted in the committed quota
- Only consulting meetings (`type: "consulting"`) count towards `total_meetings_committed`
- Kickoff is a pre-requisite to start the project, separate from consulting delivery

### P1 - High Priority
1. **Create Business Logic Document**
   - Generate PDF outlining expense/meeting management system

### Future/Backlog
1. Refactor `backend/routers/kickoff.py` (large file)
2. Refactor `frontend/src/pages/MeetingRecord.js` (complex component)
3. Remove orphan file: `frontend/src/pages/consulting/Meetings.js`
4. Build DVBC Marketing Hub
5. Implement Consultant Incentive System
6. Implement Internal Chat System

---

## Test Credentials
- **Admin:** EMP001 / admin123

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB
- No third-party integrations added this session
