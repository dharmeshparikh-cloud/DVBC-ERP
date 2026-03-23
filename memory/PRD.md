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

---

## Exit Organisation Workflow (March 23, 2026)

### Feature Overview
Complete employee resignation workflow with guided exit interview and approval chain.

### Flow
1. **Employee initiates** - Clicks "Exit Organisation" button on My Details page
2. **Step 1: Confirmation** - Reviews important information about notice period, approvals, restrictions
3. **Step 2: Exit Interview** - Answers mandatory questions (7 questions: select, rating, text types)
4. **Step 3: Review & Submit** - Reviews answers and submits exit request
5. **Admin Approval** - Request goes to Admin for first-level approval
6. **HR Approval** - After Admin approval, HR reviews and approves (F&F calculation starts)
7. **Notice Period** - 30-day notice period begins
8. **F&F Settlement** - Final & Full settlement after all clearances

### API Endpoints
| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/exit/interview-questions` | GET | Get exit interview questions | Public |
| `/api/exit/initiate` | POST | Submit exit request | Employee |
| `/api/exit/my-request` | GET | Get employee's exit request | Employee |
| `/api/exit/pending` | GET | Get pending exit requests | Admin/HR |
| `/api/exit/{id}/admin-approve` | POST | Admin approves exit | Admin |
| `/api/exit/{id}/hr-approve` | POST | HR approves and calculates F&F | HR |
| `/api/exit/{id}/update-checklist` | POST | Update exit checklist | Admin/HR |
| `/api/exit/{id}/process-fnf` | POST | Process F&F settlement | Admin/HR |
| `/api/exit/{id}/reject` | POST | Reject/Cancel exit request | Admin/HR |

### Files
- Backend: `/app/backend/routers/exit_organisation.py`
- Frontend: `/app/frontend/src/pages/MyDetails.js` (Exit Organisation section)

### Security
- Downloads restricted during notice period
- Employee status updated to exit_status
- User account deactivated after F&F completion

---

## Onboarding Data Editing Policy

### How Employees Can Edit Onboarding Data
After onboarding completion, employees can request changes to their profile information through the **My Details** page:

1. **View Data**: All onboarding data is visible on My Details page
2. **Request Changes**: Click "Edit" button on any editable section (Contact, Address, Bank Details, Emergency Contact)
3. **Provide Reason**: Must provide a reason for the change request
4. **Proof Required**: Bank detail changes require proof document (cancelled cheque/bank statement)
5. **HR Approval**: All change requests go to HR for review and approval

### Sections
| Section | Editable | Approval Required |
|---------|----------|-------------------|
| Personal Information | No (Contact HR) | - |
| Contact Information | Yes | HR |
| Address | Yes | HR |
| Bank Details | Yes | HR (with proof) |
| Emergency Contact | Yes | HR |
| Employment Information | No (Read-only) | - |

---

## CTC Designer Enhancement (March 23, 2026)

### Overview
CTC Designer now has two tabs to handle both new employees and salary revisions from a single page.

### Tabs
1. **New Employee CTC** (Default tab)
   - Shows employees with `onboarding_complete === true` but NO CTC set
   - Used by HR to set first-time CTC for newly onboarded employees
   - "Set CTC" link available from Go-Live Dashboard

2. **CTC Revision**
   - Shows employees with existing CTC (`current_ctc > 0`)
   - Used for annual salary revisions

### Go-Live Integration
- **CTC Pending Filter**: Go-Live Dashboard shows "CTC Pending" filter to see employees waiting for CTC setup
- **Auto Go-Live**: When first-time CTC is approved by Admin, employee's `go_live_status` automatically changes to "active"
- **Status Badge**: Changed from "Active" to "Go-Live Successful"

### Live Preview Feature
- CTC breakdown preview updates automatically as user types (500ms debounce)
- No need to click "Preview Breakdown" button
- Retention bonus now correctly reflected in the breakdown

### Access Control
- HR and Admin can access CTC Designer
- HR creates CTC structure → Admin approves

---

## Business Rules & Policies Page (March 23, 2026)

### Overview
Centralized page for all company policies and rules. Single source of navigation for all configurable business rules.

### Access Control
- **HR/Admin**: Full edit access (toggle rules, edit values)
- **Employees**: View-only access

### Policy Types (42 total rules)
| Type | Rules | Description |
|------|-------|-------------|
| Travel | 10 | Daily allowances, flight class, hotel limits, advance/settlement process |
| Expense | 6 | Self-approval prevention, cutoffs, receipt thresholds, limits |
| Attendance | 8 | Work hours, core hours, late thresholds, WFH days, overtime |
| Payroll | 10 | Processing dates, PF/ESI thresholds, formulas, statutory rules |
| General HR | 8 | Probation, notice periods, increment month, dress code, retirement |

### Features
- Policy cards with rule counts and effective dates
- Click to expand and see all rules
- Toggle to enable/disable individual rules
- Edit rule values (numeric, string, conditions)
- Payroll Integration section showing linkages
- CTC Component Linkage section
- Search across all rules
- Filter by policy type

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/business-rules` | GET | Get all policies |
| `/api/business-rules/types` | GET | Get policy types metadata |
| `/api/business-rules/{id}` | GET/PUT | Get/Update policy |
| `/api/business-rules/{id}/rule/{rule_id}` | PUT | Update specific rule |

### Files
- Backend: `/app/backend/routers/business_rules.py`
- Frontend: `/app/frontend/src/pages/hr/BusinessRules.js`
- Route: `/business-rules`

---

## Rule Engine with CTC Component Linkage (March 23, 2026)

### Overview
A comprehensive rule engine service that evaluates complex business conditions and links to CTC components for automatic payroll calculations.

### Features
1. **Condition Evaluation** - Parse and evaluate expressions like `basic_salary > 15000 AND department == 'Sales'`
2. **Formula Calculation** - Evaluate formulas like `basic_salary * 0.12` with context variables
3. **Statutory Deductions** - Auto-calculate PF, ESI, PT based on business rules
4. **LOP Calculation** - Calculate Loss of Pay using configurable formulas
5. **Payroll Simulation** - Full payroll simulation with all rules applied

### CTC Components Supported
| Component | Type | Taxable | Notes |
|-----------|------|---------|-------|
| basic_salary | earning | Yes | Base component (typically 40% of CTC) |
| hra | earning | Yes | 50% of basic |
| special_allowance | earning | Yes | Balancing component |
| pf_employee | deduction | - | 12% of basic (max ₹15000) |
| pf_employer | employer_contribution | - | 12% of basic |
| esi_employee | deduction | - | 0.75% of gross (if gross <= ₹21000) |
| professional_tax | deduction | - | Slab-based (max ₹200) |

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/business-rules/engine/evaluate-condition` | POST | Evaluate a condition |
| `/api/business-rules/engine/evaluate-formula` | POST | Evaluate a formula |
| `/api/business-rules/engine/calculate-statutory` | POST | Calculate statutory deductions |
| `/api/business-rules/engine/calculate-lop` | POST | Calculate LOP deduction |
| `/api/business-rules/engine/simulate-payroll` | POST | Full payroll simulation |
| `/api/business-rules/engine/ctc-components` | GET | Get all CTC components |

### Payroll Simulator UI
- Located in Business Rules page → "Payroll Simulator" button
- Input: Annual CTC, Basic %, HRA %, Working Days, Present Days, LOP Days, Expense Reimbursement
- Output: Earnings breakdown, Deductions, Employer Contributions, Net Salary
- Shows which rules were applied (PY005, PY006, PY007, etc.)

### Files
- Backend: `/app/backend/services/rule_engine.py`
- API: `/app/backend/routers/business_rules.py` (engine endpoints)
- Frontend: `/app/frontend/src/pages/hr/BusinessRules.js` (simulator dialog)

---

## Last Updated
- Date: March 23, 2026
- Status: Rule Engine with CTC Linkage & Payroll Simulator Implemented
