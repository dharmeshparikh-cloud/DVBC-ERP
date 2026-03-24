# NETRA ERP - Product Requirements Document

## Latest Updates - March 24, 2026

### P0 Governance Fixes (COMPLETE) [March 24, Session 4]

**Fixes Implemented**:

1. **Fixed bare `except:` blocks in analytics.py**
   - Replaced all bare `except:` blocks with specific exception types `(ValueError, TypeError, AttributeError)`
   - Lines 855, 867, 878, 1113, 1140, 1225
   - Improves debuggability and prevents swallowing unknown errors

2. **Added `/my` endpoint for Approvals module** (`approvals.py` line 75)
   - Returns user's pending approvals they need to action
   - Returns user's submitted requests
   - Includes summary counts (pending_to_action, my_approved, my_rejected, my_pending)

3. **Added `/my` endpoint for Payroll module** (`payroll.py` line 243)
   - Returns user's salary slips with month filter support
   - Returns pending reimbursements
   - Returns leave encashments
   - Returns LOP leaves
   - Includes summary (total_slips, total_net_paid, pending_reimbursement_amount, etc.)

4. **Made `budget` mandatory for Project creation** (`models.py` line 273)
   - Changed from `Optional[float]` to `Field(..., gt=0)`
   - Projects cannot be created without budget
   - Budget must be greater than 0

5. **Added receipt validation on expense approval** (`expenses.py` line 545)
   - Defense in depth: validates receipts on both submission AND approval
   - Expenses ≥ ₹500 require receipt attachment
   - Returns governance message if receipt missing on approval attempt

**Test Report**: `/app/test_reports/iteration_212.json` - 100% pass rate (17/17 tests)

---

### Business Governance Engine (COMPLETE) [March 24, Session 3]

**Feature**: Self-auditing ERP system with comprehensive business validation across all modules.

**APIs Implemented** (`/app/backend/routers/business_governance.py`):
| Endpoint | Purpose |
|----------|---------|
| `GET /api/governance/health-score` | Business health scorecard (Sales, Cost, Team, Data) |
| `GET /api/governance/mom-sla` | MOM SLA compliance monitoring (24-hour threshold) |
| `GET /api/governance/expense-compliance` | Receipt & travel-meeting linkage compliance |
| `GET /api/governance/operational-discipline` | Team discipline metrics (attendance, tasks) |
| `GET /api/governance/leakage-alerts` | Revenue/cost leakage detection |
| `POST /api/governance/mom-sla/escalate/{id}` | Escalate MOM breach to manager |

**Expense Governance Rules** (in `expenses.py`):
- Receipt required for expenses ≥₹500
- Travel expenses flagged if no meeting linkage
- High value expenses (≥₹5,000) require admin approval
- Duplicate prevention (same date/amount)
- Consultant expenses must link to active project

---

### Smart Suggestions Feature (COMPLETE) [March 24, Session 3]

**Feature**: AI-powered recommendations that suggest next actions based on consultant's workflow data.

**Implementation**:
- Backend generates contextual suggestions in `/api/my-day/summary`
- Suggestions are prioritized: high → medium → low → info
- Maximum 5 suggestions shown, top 2 visible by default
- Each suggestion includes: icon, title, description, action button, navigation path

**Suggestion Types**:
| Priority | Suggestion | Trigger |
|----------|------------|---------|
| High | Start your day | Attendance not marked |
| High | Prepare for meeting | Meeting within 2 hours |
| High | Record MOM | Overdue MOMs exist |
| Medium | Send MOM to client | MOM recorded but not sent |
| Medium | Complete action items | Open tasks assigned |
| Medium | File travel expense | In-person meetings without expense |
| Low | Follow up on expenses | 3+ expenses pending approval |
| Low | Upcoming meeting prep | Meeting in 1-2 days |
| Info | Great week! | All meetings delivered |
| Info | Almost there! | 80%+ delivery rate |

**UI Features**:
- Purple gradient section header with sparkles icon
- Color-coded left borders by priority
- Expandable to show all suggestions
- Click to navigate to relevant page

---

### "My Day" Smart Bar for Consultants (COMPLETE) [March 24, Session 3]

**Feature**: A personalized daily workflow tracker for consultants displayed on the Consulting Meetings page.

**Implementation**:
- Backend API `/api/my-day/summary` returns all daily workflow data in single call
- Frontend component `MyDayBar.jsx` with 4 clickable action cards:
  1. **Attendance Card**: Shows check-in status, navigates to `/my-attendance`
  2. **Today Card**: Shows meeting count, navigates to `/consulting-meetings`
  3. **MOM Status Card**: Shows overdue MOMs count, navigates to `/consulting-meetings`
  4. **Expenses Card**: Shows pending expenses, navigates to `/my-expenses`
- Cards show "Done" badge when task is completed (isComplete=true)
- Contextual reminder chips shown when actions are needed (e.g., "Mark attendance")
- Greeting with user's name and date badge
- Weekly progress bar showing delivery completion percentage

**Data Returned by API**:
- attendance: { is_checked_in, check_in_time, check_out_time, needs_action }
- today: { total_meetings, meetings[], next_meeting }
- action_required: { overdue_moms, pending_client_send, missing_expenses, open_tasks, pending_expenses }
- upcoming: { count, next_3[] }
- weekly_progress: { total_meetings, delivered, mom_recorded, completion_pct }

---

### Global "Latest First" Sorting (COMPLETE) [March 24, Session 3]

**Requirement**: Apply consistent "Latest First" sorting to all major list views across the ERP.

**Implementation**:
- Created `/app/frontend/src/utils/sortUtils.js` with reusable sorting utilities:
  - `sortByLatest(items, dateField)` - Sort by single date field, descending
  - `sortByFields(items, dateFields[])` - Sort by multiple date fields with fallback
  - `sortMeetingsForDaily(meetings)` - Smart sorting: today first, then future, then past
  
**Pages Updated**:
| Page | Import | Usage |
|------|--------|-------|
| Meetings.js | sortByFields | `sortByFields(meetings, ['meeting_date', 'created_at'])` |
| Notifications.js | sortByLatest | `sortByLatest(filteredNotifications, 'created_at')` |
| Invoices.js | sortByLatest | `sortByLatest(filteredInvoices, 'created_at')` |
| LeaveManagement.js | sortByLatest | `sortByLatest(displayRequests, 'created_at')` |
| MyLeaves.js | sortByLatest | `sortByLatest(requests, 'created_at')` |
| MyExpenses.js | sortByLatest | `sortByLatest(data.expenses, 'created_at')` |
| ApprovalsCenter.js | sortByLatest | `sortByLatest(pendingApprovals, 'created_at')` |

**Note**: Several pages (Employees.js, Clients.js, AllProjects.js, Leads.js, KickoffRequests.js) already had inline sorting implemented.

---

### Previous Session Work (COMPLETE)

**Consulting Meeting Travel Expense** [March 24, Session 2]:
- Full `MeetingLocationPicker` with Google Maps integration
- Auto-created expense records on meeting submit

**Consultant Meeting Flow Fix** [March 24, Session 2]:
- Backend RBAC fix in projects.py
- Past date validation fix
- Status override for delivered meetings

**Data Governance Phase 1** [March 24, Session 2]:
- `GovernedDropdown.jsx` - Reusable dropdown with states
- `useSOWsByProject.js` - Server-filtered SOW hook
- Applied in ConsultingMeetings module

**P0 System-Level Governance Fixes** [March 24, Session 2]:
- Payroll Approval Dialog actions
- Approvals Center stale state fix
- Penalty Dashboard server-side filters

---

## Architecture

```
/app/
├── backend/
│   ├── routers/
│   │   ├── my_day.py                 # "My Day" aggregation endpoint
│   │   ├── approvals.py
│   │   ├── meetings.py
│   │   ├── penalties.py
│   │   ├── projects.py
│   │   └── users.py
│   └── tests/
│       └── test_my_day_sorting.py    # Test file for My Day and Sorting
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── MyDayBar.jsx          # Consultant's daily workflow tracker
│       │   ├── GovernedDropdown.jsx
│       │   └── MeetingLocationPicker.js
│       ├── hooks/
│       │   └── useSOWsByProject.js
│       ├── utils/
│       │   └── sortUtils.js          # Global sorting utilities
│       └── pages/
│           ├── ConsultingMeetings.js # Uses MyDayBar
│           ├── Meetings.js           # Uses sortByFields
│           ├── Notifications.js      # Uses sortByLatest
│           ├── Invoices.js           # Uses sortByLatest
│           ├── LeaveManagement.js    # Uses sortByLatest
│           ├── MyLeaves.js           # Uses sortByLatest
│           ├── MyExpenses.js         # Uses sortByLatest
│           └── ApprovalsCenter.js    # Uses sortByLatest
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/my-day/summary` | GET | Aggregates daily workflow data for logged-in user |
| `/api/employees-dropdown` | GET | Lightweight endpoint for employee dropdowns |
| `/api/meetings` | POST | Create meeting (auto-creates linked expense) |
| `/api/projects` | GET | RBAC-filtered project listing |
| `/api/project-pnl/invoices` | GET | Get invoices list |

---

## Backlog (Prioritized)

### P0 — Remaining High Priority
- **Mandate Meeting-Expense Link**: Auto-prompt users to create travel expense after "in-person" meeting is delivered
- **MOM SLA Reminder System**: Automated escalation for MOMs not recorded within 24-hour SLA
- **Make Project Value Mandatory**: Already done for `budget`, consider extending to `project_value` if needed

### P1 — Upcoming
- Data Governance Phase 2: Expand `GovernedDropdown` to Expenses and Project Management modules
- Appraisals Integration: Auto-reflect salary revisions in payroll engine

### P2 — Future
- HR Dashboard Frontend UI (backend API `/api/hr/dashboard` exists)
- Bank Details Management UI
- Salary Slip PDF generation
- Arrears resolution tracking view for HR

### P3 — Backlog
- Refactor ConsultingMeetings.js (technical debt, 2300+ lines)
- Naming standardization (forward-only approach)

---

## Key Credentials

| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales Executive | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
| Employee | EMP005 | employee123 |

---

## Testing Status

- **Iteration 212**: P0 Governance Fixes - 100% backend pass rate (17/17 tests)
- **Iteration 210**: My Day Bar & Global Sorting - 92% backend, 100% frontend pass rate
- **Iteration 209**: Consulting Meeting Travel Expense
- **Iteration 208**: Data Governance - Governed Dropdown
