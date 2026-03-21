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
- **MeetingLocationPicker component integrated** with Google Places autocomplete
- Features:
  - Auto-complete for start/end locations
  - Travel mode buttons: Car (₹7/km), Bike (₹3/km), Transit (manual), Accompanied (no expense)
  - Round trip toggle with automatic distance doubling
  - Real-time expense calculation
  - Via locations support for multiple stops
- SSOT badge: "SSOT for Expenses"
- Note: Only meeting scheduler can claim conveyance

#### 5. Expense Creation & Payroll Integration
- **Automatic expense creation**: When MOM is saved with travel_details, expense record is created automatically
- **Duplicate prevention**: System checks for existing expense before creating new one
- **Approval workflow**:
  - < ₹2000: HR directly approves → linked to payroll
  - ≥ ₹2000: HR approves → Admin approves → linked to payroll
- **Notification system**: Employee receives notification when expense is approved with message including payroll period
- **Expense linked to payroll_reimbursements collection** for payroll processing

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
- Own Car: ₹7/km
- Own Bike: ₹3/km
- Public Transit: Manual entry with proof upload
- Accompanied: No claim (traveled with someone else)

### Expense Approval Flow
1. Employee records MOM with travel details
2. System creates expense with status "pending"
3. HR reviews and approves (for < ₹2000, final approval)
4. For ≥ ₹2000: Admin gives final approval
5. Expense linked to payroll_reimbursements
6. Employee receives notification: "Your expense of ₹X approved and linked to Y payroll"

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
- `/app/test_reports/iteration_190.json` - MeetingLocationPicker integration & expense flow verification
- `/app/test_reports/iteration_191.json` - Payroll integration fix verification
- `/app/test_reports/iteration_192.json` - Leave-Attendance-Payroll integration
- `/app/test_reports/master_qa_report.md` - **MASTER QA TEST REPORT (Full E2E)**
- `/app/backend/tests/test_backdated_approval.py` - Backend pytest
- `/app/backend/tests/test_meeting_travel_expense.py` - Travel expense tests
- `/app/backend/tests/test_payroll_expense_integration.py` - Payroll-expense integration tests

### Results
- Backend: 100% pass rate (20/20 tests)
- Frontend: 100% pass rate
- All 10 meeting states validated
- SSOT breach prevention verified
- MeetingLocationPicker integration verified
- Expense creation and approval workflow verified
- **Payroll integration fix verified**: payroll_reimbursements now created with correct internal employee ID
- **Leave-Attendance-Payroll integration verified**: Full flow working
- **Master QA Test completed**: 2 Critical, 3 High issues found and fixed

---

## Leave Management System

### Employee Self-Service
- **Apply Leave**: `POST /api/leave-requests`
  - Leave types: Casual, Sick, Earned
  - Half-day option available
  - Validates against leave balance
- **Withdraw Leave**: `POST /api/leave-requests/{id}/withdraw` (pending only)
- **View Balance**: `GET /api/my/leave-balance`

### Manager Approval Flow
1. Employee submits leave → Status: "pending"
2. Manager reviews via `GET /api/leave-requests?status=pending`
3. Manager approves/rejects via `POST /api/leave-requests/{id}/rm-approve`
4. Leave balance updated on approval

### HR Functions
- Apply leave on behalf: `POST /api/attendance/hr/apply-leave-for-employee` (auto-approved)
- View all leaves: `GET /api/leave-requests/all`
- Company stats: `GET /api/leave-requests/stats/company-wide`

## Payroll Integration

### Incentive Input
- HR/Admin enters via Payroll page → Payroll Inputs tab
- Fields: incentive amount, incentive_reason
- API: `POST /api/payroll/inputs`

### Salary Slip Generation
- Includes: Basic, HRA, Special Allowance, Incentive, Overtime
- Deductions: PF, Professional Tax, Penalty
- Links to: Leave records, Expense reimbursements
- API: `POST /api/payroll/generate-slip`

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

## Login Governance (March 21, 2026)

### Authentication Policy
- **Employee ID Login ONLY** - Email login disabled for password authentication
- **Google OAuth** - Available for @dvconsulting.co.in email accounts
- Frontend validation prevents email submission in Employee ID field
- Backend enforces login governance with clear error messages

### Employee Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales Executive | EMP003 | sales123 |
| Consultant | CON001 | consultant123 |

---

## ERP Stress Test Validations (March 21, 2026)

### Implemented Validations

| Code | Validation | Status |
|------|-----------|--------|
| I52 | Self-approval prevention (expenses, leaves) | ✅ IMPLEMENTED |
| E31 | Payroll cutoff validation (15th of month) | ✅ IMPLEMENTED |
| A4 | Lead stage progression validation | ✅ IMPLEMENTED |
| B12 | Inactive reporting manager assignment prevention | ✅ IMPLEMENTED |

### Validation Details

**I52 - Self-Approval Prevention**
- Users cannot approve their own expenses
- Users cannot approve their own leave requests
- Returns HTTP 403 with code "I52" on violation

**E31 - Payroll Cutoff Validation**
- Expenses approved after 15th of month go to next month's payroll
- Prevents retroactive payroll linkage
- Automatic period calculation

**A4 - Lead Stage Progression**
- Leads cannot skip stages to closed_won
- Must progress: new → qualified → proposal/negotiation → closed_won
- Returns HTTP 400 with code "A4" on violation

**B12 - Reporting Manager Validation**
- Cannot assign inactive/terminated employees as reporting managers
- Prevents organizational hierarchy issues

---

## Credentials
- **Admin:** admin@dvconsulting.co.in / admin123
- **HR Manager:** hr@dvconsulting.co.in / hr123
- **Sales:** sales@dvconsulting.co.in / sales123
- **Consultant:** consultant@dvconsulting.co.in / consultant123
- **Test Email:** dharmesh.parikh@dvconsulting.co.in

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB, aiosmtplib
- Background Tasks: asyncio scheduler

---

## Last Updated
- Date: March 21, 2026
- Status: Stress Test Validations Implemented (I52, E31, A4, B12)
