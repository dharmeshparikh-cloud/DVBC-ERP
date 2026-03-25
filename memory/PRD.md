# NETRA ERP - Product Requirements Document

## Latest Updates - March 25, 2026

### P2 - Saved Views & Export to CSV for SalesDataTable (Session 11 continued)
- **Saved Views Feature**:
  - Added `useSavedViews` hook that persists custom views to localStorage per table
  - Created `SaveViewDialog` component showing view name input, "Set as default" checkbox, and summary of what will be saved (filters, sort, page size)
  - Dropdown menu in table header shows saved views with star indicator for default, delete option, and "Save Current View" button
  - Views are restored on page load if marked as default
- **Export to CSV Feature**:
  - Created `ExportDialog` component with two export options: "Current Page" or "All Matching Records"
  - Shows record counts for each option and list of columns that will be exported
  - Fetches all data from API when exporting all records (up to 10,000)
  - CSV includes BOM for proper Excel compatibility
- **Testing**: 100% frontend pass rate on Leads and Follow-ups pages (iteration_225.json)

### P1 - Funnel Checklist Alignment & Governance Linting (Session 11 continued)
- **Funnel Checklists Aligned**: Updated backend `/api/leads/{id}/funnel-checklist` endpoint to match actual mandatory fields:
  - **SOW**: SOW created + scope item with title (required), category/timeline/consultant (optional)
  - **Quotation**: Lead selected + pricing plan linked + quotation number (required), payment terms/validity (optional)
  - **Agreement**: Lead with quotation + quotation linked + agreement type (required), start date (optional), signed status (required for completion)
- **Governance Linting Implemented (Phase 5)**:
  - Created `/app/frontend/scripts/check-sales-governance.js` - automated checker for sales table governance
  - Created `/app/frontend/docs/GOVERNANCE.md` - comprehensive documentation of governance rules
  - Created `/app/frontend/eslint.config.mjs` - ESLint flat config for the project
  - Added `yarn governance:check` npm script to run the checker
  - All primary sales listing pages now use SalesDataTable variants

### P0 Bug Fixes - MeetingRecord.js Crash & DraftSelector (Session 11)
- **MeetingRecord.js Crash Fixed**: The page was crashing with a TypeError due to `.some()` being called on string values instead of arrays. The MOM form fields (discussion_points, decisions_made, etc.) had been converted from arrays to simple textareas, but the auto-save logic still expected arrays.
  - **Fix Applied**: 
    1. Simplified `momData` state to use string fields only (notes, mom, price_discussion, next_steps, action_items)
    2. Removed `.some()` calls from auto-save `hasContent` check
    3. Removed unused list handler functions (handleAddListItem, handleRemoveListItem, handleListItemChange)
- **DraftSelector Component Verified**: The refactored component supporting both dialog and inline modes is working correctly on Quotations and PricingPlanBuilder pages.
- **Testing**: 100% frontend test pass rate verified via testing agent (iteration_224.json)

### AI-Powered Note Suggestions (Session 10)
- **Backend**: Created `/api/ai/suggest` endpoint using GPT-5.2 via emergentintegrations library. Supports context types: `mom`, `notes`, `follow_up`, `discussion_points`, `next_steps`, `email_body`, `action_items`, `client_expectations`, `key_commitments`.
- **Frontend**: Created reusable `AISuggestButton` component. Integrated into MeetingRecord (MOM Notes, MOM Summary, Next Steps), FollowUps (Create notes, Update notes, Close summary).
- **Funnel Checklist Fix**: Updated all 9 step checklists to match actual mandatory fields (e.g., Pricing Plan now requires "team member added", "total investment > 0", "payment start date" instead of incorrect "project type selected").

### P0 Bug Fixes - Email CTA Flow (Session 9)
- **Reschedule CTA Page**: Built a branded client-facing reschedule form with date/time picker, current schedule display, optional message field, and form submission. Replaced the previous instant confirmation behavior.
- **Close Confirmation Page**: Added the scheduled follow-up date/time display to the "Confirmed!" page so clients see what they've agreed to.
- **Email Logo Size**: Increased logo from 48-52px to 64px (max-width: 240px) across email template, action pages, and reschedule page.
- **CTA Status Tracking**: Verified that both `client_closed` and `client_reschedule` actions are correctly logged in follow-up history with proper attribution ("Client via email"). Reschedule submissions store `client_preferred_date`, `client_preferred_time`, and `client_response` fields.
- **Bug Fix**: Fixed missing `_build_reschedule_page` function (was called but never defined, causing runtime error). Fixed `Request` import from fastapi (was imported inside function body after being used as type hint).

### P1 Enhancements - Lead Reassignment, Follow-up Email, Lead Integration (Session 8)
- **Lead Reassignment**: Single-lead reassign (any role) + Bulk migration (admin/manager only). Transfers all associated data (meetings, pricing, SOW, quotations, agreements, follow-ups). Activity log tracks all transfers with reason.
- **Follow-up Email Trigger**: 3 templates (Formal, Meeting, Reminder) with CTA links (Close Follow-up, Reschedule). Client responses auto-logged in follow-up history. Template includes client name, company, follow-up notes.
- **Follow-up ↔ Lead Integration**: Lead dropdown always required when creating follow-up. Linked Lead banner in detail dialog with "View Pipeline" button. Client Response column in FollowUpsTable showing Confirmed/Reschedule/—. Backend enriches follow-ups with lead email and company.

### Bug Fixes - Leads, Follow-ups, Pricing (Session 8 continued)
- **Follow-up Create**: Lead dropdown always visible and required (removed free-text client name), added time field
- **Edit Lead**: Fixed by populating all form fields including source/notes/follow-up, stripping invalid fields on submit
- **Funnel column**: Fixed FUNNEL_STAGES to map to actual DB statuses (new→New Lead, contacted→Meeting, qualified→Pricing/SOW, proposal→Quotation, agreement→Agreement, closed→Complete)
- **Backend auto-sync**: Leads list API now auto-syncs lead status with funnel progress on each list fetch
- **Discount field**: Fixed prefilled 0 (shows empty, placeholder "0"), fixed float precision (Math.round for accurate %)
- **Pricing Save button**: Added validation messages below button ("Add at least one team member" / "Enter total investment" / "Select start date")
- **Add Lead dialog**: Lead Source now a governed dropdown (Website, Referral, LinkedIn, etc.), removed LinkedIn URL field
- **Actions stopPropagation**: Fixed action column click not triggering row navigation

### Bug Fixes - Leads Page (Session 8)
- Fixed "View Pipeline" action: now navigates to `/sales-funnel-onboarding?leadId=X` (was pointing to non-existent route)
- Fixed "Edit Lead" action: added missing `editLead` state, dialog now pre-fills with lead data
- Fixed lead row click: navigates to funnel onboarding page (was going directly to pricing)
- Added **Funnel Progress column** to LeadsTable showing visual progress bar with stage label and step count (e.g., "Lead 1/9")
- Fixed `stopPropagation` on actions column to prevent row click interference

### Sales Module Governance System (COMPLETE) [March 24, Session 6]

**Excel-like SalesDataTable Component** (`/app/frontend/src/components/sales/`):
- Column filters (Excel-style dropdown, text, number range, date range)
- Global search with 300ms debounce
- Sorting (ASC/DESC) with visual indicators
- Multi-filter support (AND logic)
- Server-side pagination
- Filter chips with clear functionality
- Sticky header
- Color coding (Red=overdue, Yellow=due, Green=progressing)
- Quick views (My Leads, Today Follow-ups, Hot Deals, Stuck Deals)

**Specialized Sales Tables Created**:
| Component | Purpose |
|-----------|---------|
| `SalesDataTable.jsx` | Core reusable component |
| `LeadsTable.jsx` | Lead management with pipeline filters |
| `MeetingsTable.jsx` | Meeting tracking with MOM status |
| `FollowUpsTable.jsx` | Follow-up management with priority colors |
| `QuotationsTable.jsx` | Quotation tracking with value filters |

**Backend API Enhancements** (Standardized Response Format):
```json
{ "data": [], "total": N, "page": N, "page_size": N, "total_pages": N }
```

| API | New Filters Added |
|-----|-------------------|
| `/api/leads` | search, deal_value_min/max, created_from/to, days_since_activity |
| `/api/meetings` | date_from/to, search, status, assigned_to |
| `/api/follow-ups` | due_date=TODAY, priority, due_from/to |
| `/api/quotations` | value_min/max, created_from/to, search |

**Database Indexes Added**:
- `follow_ups.assigned_to`, `follow_ups.due_date`, `follow_ups.status`
- `quotations.status`, `quotations.created_at`, `quotations.total_value`

**Phase 4: Migration Complete** [March 25, Session 7-8]:
| Page | Before | After |
|------|--------|-------|
| `Leads.js` (List view) | Manual `<table>` with `.map()` | `LeadsTable` (SalesDataTable) with Funnel column |
| `ManagerLeadsDashboard.js` | Manual leads table | `LeadsTable` with external filters |
| `Agreements.js` | Manual list/card | `AgreementsTable` (SalesDataTable) |
| `ProformaInvoice.js` | Manual list | `ProformaInvoiceTable` (SalesDataTable) |
| `SalesSOWList.js` | Manual `<table>` | `SOWTable` (SalesDataTable) |
| `FollowUps.js` | Card-based `.map()` list | `FollowUpsTable` (SalesDataTable) |

**Bug Fixes** [March 25, Session 8]:
- Leads page: View Pipeline, Edit Lead actions, row click navigation, Funnel column added
- Agreements API: standardized to paginated response
- Enhanced SOW API: standardized to paginated response  
- SOWTable: fixed endpoint from `/api/sow` to `/api/enhanced-sow/list`

---

### Data Governance Phase 2 (COMPLETE) [March 24, Session 5]

**GovernedDropdown expanded to all modules:**

| Module | Dropdowns Governed | Status |
|--------|-------------------|--------|
| **MyExpenses** | Category (line items) | ✅ |
| **Leads** | Stage filter, Industry | ✅ |
| **Payroll** | Employee, Component Type, Calculation Type | ✅ |
| **MyLeaves** | Leave Type, Half Day Type | ✅ |

**New Normalized Hooks** (`useSOWsByProject.js`):
- `useNormalizedEmployees` - Employee dropdown data
- `useNormalizedClients` - Client dropdown data  
- `useExpenseCategories` - Expense category options
- `useLeaveTypes` - Leave type options
- `useIndustryOptions` - Industry dropdown options
- `useLeadSources` - Lead source options
- `useLeadStatusOptions` - Lead status filter options
- `useProjectStatusOptions` - Project status options

**Test Report**: `/app/test_reports/iteration_214.json` - 100% frontend pass rate

---

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

6. **MOM SLA Reminder System** (`business_governance.py`)
   - `POST /api/governance/mom-sla/run-reminders` - Automated reminder system
   - Creates high-priority notifications for meetings past 24-hour MOM SLA
   - Escalates to reporting manager for meetings >36 hours overdue
   - Skips recently notified meetings (within 12 hours) to prevent spam
   - `GET /api/governance/mom-sla/pending-reminders` - Preview endpoint

7. **Meeting-Expense Link Auto-Prompt** (`meetings.py`, `business_governance.py`)
   - Auto-prompts users to file travel expense after in-person meeting
   - Triggers on meeting creation (if mode=offline without travel_details)
   - Triggers on MOM recording (if in-person meeting has no expense)
   - Creates `expense_prompt` notification with action path to /my-expenses

**Test Reports**: 
- `/app/test_reports/iteration_212.json` - P0 Fixes (100% pass)
- `/app/test_reports/iteration_213.json` - MOM SLA & Expense Link (100% pass)

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

### P0 — All Complete
All P0 governance fixes and email CTA flow fixes have been implemented and tested.

### P1 — Upcoming
- Phase 5: Strict Sales Governance — Linting rules to prevent manual tables in sales module
- Phase 7: Full Sales Module E2E Test — Comprehensive test suite for entire sales module
- Appraisals Integration: Auto-reflect salary revisions in payroll engine

### P2 — Future
- Phase 8: Advanced Sales Features (Saved Views, Export to CSV for SalesDataTable)
- HR Dashboard Frontend UI (backend API `/api/hr/dashboard` exists)
- Bank Details Management UI
- Salary Slip PDF generation
- Arrears resolution tracking view for HR

### P3 — Backlog
- Refactor ConsultingMeetings.js (technical debt, 2300+ lines)
- Governance Dashboard UI (frontend page for `/api/governance/*` endpoints)
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

- **Iteration 222**: P0 Email CTA Fixes - 100% backend + frontend pass (Reschedule page, Close confirmation, Logo size, Status tracking)
- **Iteration 216**: Phase 4 Migration (Leads.js, ManagerLeadsDashboard.js) - 100% frontend pass
- **Iteration 215**: Sales Module Governance APIs - 100% backend pass (35/35 tests)
- **Iteration 214**: Data Governance Phase 2 - 100% frontend pass rate (GovernedDropdown across all modules)
- **Iteration 213**: MOM SLA Reminder & Meeting-Expense Link - 100% backend pass rate (12/12 tests)
- **Iteration 212**: P0 Governance Fixes - 100% backend pass rate (17/17 tests)
- **Iteration 210**: My Day Bar & Global Sorting - 92% backend, 100% frontend pass rate
- **Iteration 209**: Consulting Meeting Travel Expense
- **Iteration 208**: Data Governance - Governed Dropdown
