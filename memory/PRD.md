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
- **Key Collections:** users, employees, leads, meetings, expenses, projects, pricing_plans, kickoff_requests, additional_meeting_requests

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
  - Returns committed, delivered, remaining counts
  - Flags: `can_deliver_meeting`, `needs_approval`
- **Additional Meeting Request System:**
  - Create request when limit exceeded
  - Admin/Principal Consultant approval workflow
  - Auto-increment project commitment on approval
  - Notification system for requests

### Phase 4: Consulting Travel Expenses (Completed - March 2026)
- Travel details capture in meeting delivery flow
- MeetingLocationPicker integration for consulting meetings
- Auto-expense creation on meeting completion with travel data
- Duplicate prevention for consulting meeting expenses

### Phase 5: Frontend UI for Additional Meeting Requests (Completed - March 2026)
- **New Page:** `/consulting/additional-meeting-requests`
  - Stats cards: Pending, Approved, Rejected, Total
  - Filter tabs: All, Pending, Approved, Rejected
  - Request cards with project info, status badges
  - Approve/Reject buttons for admin users
  - Create new request dialog
- **Dashboard Widget:** `ProjectMeetingQuotaWidget`
  - Shows project-wise meeting quota (delivered/committed)
  - Progress bars with color-coded status
  - "Request Additional Meetings" quick action
  - Integrated into Consulting Dashboard
- **Navigation:** Added "Meeting Requests" item in Consulting sidebar section

## Key APIs

### Expense Management
- `POST /api/expenses` - Create expense (with duplicate prevention)
- `GET /api/my/expenses` - User's own expenses
- `GET /api/expenses/report/monthly-meeting-expenses` - Monthly report

### Meeting Management
- `POST /api/meetings/{lead_id}/mom` - Record sales meeting with MOM
- `POST /api/meeting-schedules/meetings/{id}/complete-and-send` - Complete consulting meeting

### Additional Meeting Requests
- `POST /api/meeting-schedules/additional-meeting-request` - Request additional meetings
- `GET /api/meeting-schedules/additional-meeting-requests` - List requests
- `POST /api/meeting-schedules/additional-meeting-requests/{id}/approve` - Approve request
- `POST /api/meeting-schedules/additional-meeting-requests/{id}/reject` - Reject request
- `GET /api/meeting-schedules/project/{project_id}/meeting-status` - Project meeting status

## Database Schema

### expenses collection
```javascript
{
  meeting_id: "uuid",        // For duplicate prevention
  lead_id: "uuid",           // Optional lead linkage
  project_id: "uuid",        // Optional project linkage
  expense_type: "meeting_expense" | "consulting_meeting_expense"
}
```

### additional_meeting_requests collection
```javascript
{
  id: "uuid",
  project_id: "uuid",
  project_name: "string",
  client_name: "string",
  requested_by: "uuid",
  requested_by_name: "string",
  reason: "string",
  requested_meetings: number,
  meeting_type: "string",
  urgency: "normal" | "urgent",
  current_committed: number,
  current_delivered: number,
  status: "pending" | "approved" | "rejected",
  approved_meetings: number,
  approved_by: "uuid",
  approved_at: "datetime"
}
```

## Test Credentials
- **Admin:** EMP001 / admin123
- **HR Manager:** EMP002 / admin123
- **Sales Executive:** EMP003 / admin123

## Remaining Backlog

### P1 - Important
- Consultant Expense Submission governance

### P2 - Future
- Refactor `backend/routers/kickoff.py` (large file)
- Refactor `frontend/src/pages/MeetingRecord.js` (complex component)
- Remove orphan file: `frontend/src/pages/consulting/Meetings.js`
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System

## Testing
- Test reports: `/app/test_reports/iteration_181.json`, `/app/test_reports/iteration_182.json`
- Backend: 100% pass rate (10 tests)
- Frontend: 100% pass rate (All UI features verified)
