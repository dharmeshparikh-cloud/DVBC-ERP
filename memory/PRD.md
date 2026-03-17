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

## Business Logic Document
Full documentation at: `/app/memory/CONSULTING_EXPENSE_BUSINESS_LOGIC.md`

## Key APIs

### Meeting Management
- `POST /api/meeting-schedules/meetings/{id}/complete-and-send` - Complete MOM with RBAC
- `GET /api/meeting-schedules/project/{project_id}/meeting-status` - Meeting quota status

### Expense Management
- `POST /api/expenses` - Create expense with governance
- `GET /api/my/expenses` - User's own expenses

### Additional Meeting Requests
- `POST /api/meeting-schedules/additional-meeting-request` - Request additional meetings
- `POST /api/meeting-schedules/additional-meeting-requests/{id}/approve` - Approve request

## Test Credentials
- **Admin:** EMP001 / admin123
- **HR Manager:** EMP002 / admin123
- **Sales Executive:** EMP003 / admin123

## Testing
- `/app/test_reports/iteration_183.json` - Latest test results
- Backend: 100% pass rate (11 tests)
- Frontend: 100% pass rate after bug fix
- Test file: `/app/backend/tests/test_consultant_expense_governance.py`

## Remaining Backlog

### P2 - Future
- Meeting Calendar planning feature (month/week plans with manager approval)
- Refactor `backend/routers/kickoff.py` (large file)
- Refactor `frontend/src/pages/MeetingRecord.js` (complex component)
- Build DVBC Marketing Hub
- Implement Consultant Incentive System
- Implement Internal Chat System
