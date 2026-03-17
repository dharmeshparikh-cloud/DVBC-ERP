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

### Session: March 17, 2026

#### P0 Completed Tasks

1. **SOW Scope Selection UI Enhancement**
   - Redesigned scope selection in MOM dialog with search & filter
   - Added status filter (All, In Progress, Not Started, Completed)
   - Selected scopes displayed as removable tags
   - Mandatory validation - cannot save MOM without selecting scope
   - "Select All Visible" and "Clear Selection" quick actions
   - Locked scopes (previously linked) cannot be removed

2. **Meeting Calendar → Planning Tool Conversion**
   - Added "Planning View Only" info banner
   - Added "Manage Meetings" button linking to Consulting Meetings
   - Removed "New Schedule" button (SSOT enforcement)
   - Updated subtitle to "(read-only)"

3. **Full-Page Meeting Detail View**
   - Created new `/meeting/:meetingId` route with `MeetingDetail.js`
   - Clean, printable layout with proper action buttons
   - **Only shows meeting details for meetings with MOM recorded/submitted**
   - Meetings without MOM show "MOM Not Yet Recorded" message with "Record MOM" button
   - Fixed Print/Close button overlap issue

4. **Bug Fixes**
   - Fixed missing `AlertCircle` import in ConsultingMeetings.js

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

### P0 - Critical
1. **Disable SSOT Breach Points**
   - Find and disable all "Add/Create Meeting" buttons across the app
   - Focus on Project Details page and mobile views

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
