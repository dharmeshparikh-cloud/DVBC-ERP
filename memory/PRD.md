# NETRA ERP - Product Requirements Document

## Original Problem Statement
Build a comprehensive ERP system for D&V Business Consulting with features including:
- Sales funnel management (Lead → Meeting → Pricing → Quotation → SOW → Agreement → Project)
- Consulting project management with meeting tracking
- Expense management and approval workflow
- Meeting expense tracking with travel reimbursement
- Team deployment and resource allocation
- Payroll integration

## Core Architecture

### Backend
- **Framework:** FastAPI with async MongoDB
- **Database:** MongoDB (netra_erp)
- **Authentication:** JWT-based with role-based access control (RBAC)
- **Key Collections:** users, employees, leads, meetings, expenses, projects, pricing_plans, kickoff_requests, additional_meeting_requests, consultant_assignments

### Frontend
- **Framework:** React with React Query for data fetching
- **UI Library:** Shadcn/UI components
- **State Management:** React Query + Context
- **Routing:** React Router v6

## Implemented Features

### Phase 1: Sales Funnel SSOT (Completed)
- Lead as master record for company data
- LeadSelector component for downstream forms
- Funnel stage gating (can't skip stages)
- Dynamic button disabling with tooltips

### Phase 2: Expense Duplicate Prevention (Completed - March 2026)
- **Meeting-based duplicate check:** Same meeting_id cannot have multiple expenses
- **Value-based duplicate check:** Same user + date + amount (±1) blocks duplicate
- Fields added: `meeting_id`, `lead_id` stored in expense documents

### Phase 3: Meeting Limit Validation (Completed - March 2026)
- **Project Meeting Status API:** `/api/meeting-schedules/project/{project_id}/meeting-status`
- **Additional Meeting Request System** with approval workflow
- Auto-increment project commitment on approval

### Phase 4: Consulting Travel Expenses (Completed - March 2026)
- Travel details capture in meeting delivery flow
- MeetingLocationPicker integration for consulting meetings
- Auto-expense creation with `pending` status on MOM completion

### Phase 5: Frontend UI for Additional Meeting Requests (Completed - March 2026)
- Admin panel to view/approve/reject requests
- Dashboard Widget showing project meeting quotas

### Phase 6: Consultant Expense Governance (Completed - March 2026)
- **RBAC for MOM Recording:**
  - Admin/Principal Consultant can always record
  - Others must be assigned to project (consultant_assignments)
  - User's role must match pricing plan team_deployment
- **Travel Expense Governance:**
  - Only offline/client_site meetings can claim travel
  - Online meetings - travel section hidden
  - Expense auto-created with `pending` status (no draft)
- **Approval Flow:** Consultant → HR → Admin
- **Edit Rules:** Creator can edit until approved
- **Sidebar Cleanup:** Removed duplicate "Project Expenses" link

### Phase 7: Consulting Meetings UI Enhancements (Completed - March 2026)
- **Project Filter with Auto-Date Range:** Dropdown to filter by project; auto-fills Duration fields with project's start/end dates
- **Company Column:** Renamed from "Client" to "Company" for clarity (Client = Contact/Owner, Project = Company name)
- **Date with Day Name:** Shows "Mon, Apr 13, 2026" format
- **Printable Meeting Detail:** Click meeting row → opens dialog with Print button
  - Meeting # series number (e.g., "Meeting #4")
  - Project Meeting Progress (Committed/Completed/Pending stats)
  - Company field, consultant details, MOM content, action items
- **Filter Summary Badges:** Blue badge for Project, Amber badge for Duration range
- **Document Attachments:** Upload PDFs, Word docs, Excel, Images to MOM
- **Status Filter:** Filter by Pending/Delivered/With MOM
- **View Toggle:** Switch between List view and Card view
- **File Upload API:** `/api/upload/meeting-attachments` for MOM documents
- **Test Data:** 23 consulting meetings across 5 projects and 5 companies
- **Testing:** 100% frontend pass rate (14/14 features verified)

### Phase 8: Consulting Efforts Summary & Attendance Governance (Completed - March 2026)
- **Attendance Validation:** No attendance = No MOM = No expenses (strict governance rule)
- **Meeting Attendance API:** `/api/attendance/meeting/{meeting_id}` for marking attendance
- **Duration Calculation:** Auto-calculated from start_time and end_time
- **Consulting Efforts Summary Report:** Comprehensive report page at `/consulting/efforts-summary`
  - Stats cards: Total Meetings, With Attendance, With MOM, Total Hours, Tasks, Timely Delivery
  - Expenses Summary: Total, Approved, Pending
  - Payments Summary: Invoiced, Received, Overdue, Late, Collection Rate
  - Expandable sections: By Consultant, By Project, By Company, Payment Collection
  - Print option for audit
  - Filters: Project, Consultant, Company, Date range
- **Project Handoff Summary API:** `/api/stats/consulting/project/{project_id}/handoff-summary`
- **Testing:** 100% backend and 100% frontend pass rate

## Business Logic Document
Full documentation at: `/app/memory/CONSULTING_EXPENSE_BUSINESS_LOGIC.md`

## Key APIs

### Meeting Management
- `POST /api/meeting-schedules/meetings/{id}/complete-and-send` - Complete MOM with RBAC + Attendance validation
- `GET /api/meeting-schedules/project/{project_id}/meeting-status` - Meeting quota status

### Meeting Attendance (SSOT: Unified Attendance System)
- `POST /api/attendance/meeting/{meeting_id}` - Mark meeting attendance (required for MOM/expenses)
- `GET /api/attendance/meeting/{meeting_id}` - Get attendance record for meeting
- `GET /api/attendance/meeting/project/{project_id}` - Get all meeting attendance for project

### Expense Management
- `POST /api/expenses` - Create expense with governance
- `GET /api/my/expenses` - User's own expenses

### Consulting Reports
- `GET /api/stats/consulting/efforts-summary` - Comprehensive efforts report with filters
- `GET /api/stats/consulting/project/{project_id}/handoff-summary` - Project handoff for audit

### Additional Meeting Requests
- `POST /api/meeting-schedules/additional-meeting-request` - Request additional meetings
- `POST /api/meeting-schedules/additional-meeting-requests/{id}/approve` - Approve request

### File Upload
- `POST /api/upload/meeting-attachments` - Upload documents for MOM (PDF, Word, Excel, Images)
- `GET /api/meetings/documents/{file_id}/download` - Download uploaded MOM document

## Test Credentials
- **Admin:** EMP001 / admin123
- **HR Manager:** EMP002 / admin123
- **Sales Executive:** EMP003 / admin123

## Testing
- `/app/test_reports/iteration_184.json` - Latest test results (Consulting Meetings UI)
- Backend: 91% pass rate (10/11 tests)
- Frontend: 100% pass rate
- Test file: `/app/backend/tests/test_consulting_meetings_filters.py`

## Remaining Backlog

### P0 - Upcoming (Per User Request)
- Implement Calendar as a Planning Tool (reschedule feature testing)
- Disable SSOT breach points (remove "Add Meeting" from Project Details, Calendar, Mobile App)
- Enforce project linkage on Mobile App expense submissions
- Create Business Logic PDF document

### P2 - Future
- Meeting Calendar planning feature (month/week plans with manager approval)
- Refactor `backend/routers/kickoff.py` (large file)
- Refactor `frontend/src/pages/MeetingRecord.js` (complex component)
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System
