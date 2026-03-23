# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture where all consulting meetings, MOM, and associated expenses are recorded through a single, controlled interface.

---

## Implementation Status

### P0 Features Complete (March 18-23, 2026)

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
- 10 States: DRAFT -> SCHEDULED -> CONFIRMED/REJECTED/RESCHEDULED/AUTO_ACCEPTED -> CONDUCTED -> MOM_RECORDED -> DELIVERED
- State transition API with validation and audit logging

---

### P1 Features Complete (March 18-23, 2026)

#### 1. Backdated Meeting Manager Approval Workflow
- **Request Approval**: `/api/meeting-workflow/request-backdated-approval`
- **Approve/Reject**: `/api/meeting-workflow/approve-backdated`
- **View Pending**: `/api/meeting-workflow/pending-approvals`

#### 2. SSOT Breach Prevention Verified
- **Consulting Meetings page**: SSOT with Invite button, MOM recording, expense claims
- **Calendar page**: Read-only planning view

#### 3. Travel & Conveyance Expense Section
- Appears in MOM dialog ONLY for in-person meetings
- Auto-complete locations, travel mode buttons, real-time expense calculation
- SSOT badge: "SSOT for Expenses"

#### 4. Business Rules & Policies Page (NEW March 23, 2026)
- Centralized governance page for all company policies
- 6 policy types: Leave, Travel, Expense, Attendance, Payroll, General HR
- 54+ configurable rules
- **SOPs and Impact Analysis** added per tab with:
  - Quick tips visible as pill badges
  - Impact badges showing affected areas
  - Detailed SOP modal with checklists, warnings, and best practices
- Payroll Simulator for rule testing
- RBAC: HR/Admin edit, Employees view-only

---

## Meeting Workflow States

```
DRAFT -> SCHEDULED -> CONFIRMED -> CONDUCTED -> MOM_RECORDED -> DELIVERED
                   -> REJECTED
                   -> RESCHEDULED -> SCHEDULED
                   -> AUTO_ACCEPTED -> CONDUCTED
                   -> CANCELLED

For Backdated Meetings:
DRAFT -> PENDING_APPROVAL -> APPROVED -> CONDUCTED -> MOM_RECORDED -> DELIVERED
                          -> REJECTED
```

---

## Business Rules & SOPs (NEW)

### Policy Types with SOPs
| Type | Rules | SOP Available |
|------|-------|---------------|
| Leave | 12 | Yes - Leave Policy Configuration SOP |
| Travel | 10 | Yes - Travel Policy Configuration SOP |
| Expense | 6 | Yes - Expense Policy Configuration SOP |
| Attendance | 8 | Yes - Attendance Policy Configuration SOP |
| Payroll | 10 | Yes - Payroll Rules Configuration SOP |
| General HR | 8 | Yes - General HR Policy Configuration SOP |

### SOP Features
- **Quick Reference Card**: Shows when a specific tab is selected
  - Policy title and summary
  - Quick tips as pill badges
  - Impact badges (Critical/High/Direct/Indirect)
  - "View Full SOP" button
- **SOP Detail Modal**: Comprehensive guidance with:
  - Impact Analysis cards
  - Accordion checklists (Before/During/After changes)
  - Warnings & Cautions section (red highlighted)
  - Best Practices section (green highlighted)
- **Stats Cards**: Show SOP badge on hover with quick tips tooltip

### Architecture Constraint
**CRITICAL**: Business Rules page is for HR policy limits ONLY. 
- PF, ESI, Professional Tax, and all CTC component calculations are STRICTLY in CTC Designer
- This prevents conflicting sources of truth for statutory compliance

---

## Leave Management System

### Employee Self-Service
- **Apply Leave**: `POST /api/leave-requests`
- **Withdraw Leave**: `POST /api/leave-requests/{id}/withdraw`
- **View Balance**: `GET /api/my/leave-balance`

### Manager Approval Flow
1. Employee submits -> Status: "pending"
2. Manager approves/rejects via `POST /api/leave-requests/{id}/rm-approve`
3. Leave balance updated on approval

---

## Exit Organisation Workflow

### Flow
1. Employee initiates via "Exit Organisation" button
2. Step 1: Confirmation
3. Step 2: Exit Interview (7 mandatory questions)
4. Step 3: Review & Submit
5. Admin Approval -> HR Approval -> Notice Period -> F&F Settlement

### API Endpoints
- `GET /api/exit/interview-questions`
- `POST /api/exit/initiate`
- `POST /api/exit/{id}/admin-approve`
- `POST /api/exit/{id}/hr-approve`

---

## Pending/Future Tasks

### P2 - Medium Priority
- PDF generation for salary slips and onboarding forms
- Recurring/automated monthly payroll generation
- Bulk salary slip download

### Backlog
- Refactor ConsultingMeetings.js (2400+ lines)
- 24h reminder emails before meetings
- DVBC Marketing Hub

---

## Files Reference

### Business Rules (NEW/MODIFIED)
- `/app/frontend/src/pages/hr/BusinessRules.js` - SOPs, Impact Analysis, Quick Tips
- `/app/backend/routers/business_rules.py` - Business rules API
- `/app/backend/services/rule_engine.py` - Rule evaluation service

### Deleted Files (Cleanup)
- `/app/frontend/src/pages/hr/LeavePolicySettings.js` - Replaced by Business Rules

### Updated Links
- Settings.js -> Now links to `/business-rules`
- AttendanceLeaveSettings.js -> Now links to `/business-rules`

---

## Login Governance

### Employee Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales Executive | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
| Employee | EMP005 | Welcome@EMP005 |

---

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB, aiosmtplib
- Background Tasks: asyncio scheduler

---

## Last Updated
- Date: March 23, 2026
- Status: P0/P1 Complete - Business Rules SOPs & Impact Analysis added, LeavePolicySettings.js deleted
