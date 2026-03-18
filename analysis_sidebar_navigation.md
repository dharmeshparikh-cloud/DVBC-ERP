# Sidebar Navigation Analysis by Role

## Role Definitions

### CONSULTING_ROLES_FALLBACK
- admin, consultant, senior_consultant, lead_consultant, principal_consultant, lean_consultant, project_manager

### HR_ROLES_FALLBACK  
- admin, hr_manager, hr_executive

### SALES_ROLES_FALLBACK
- admin, sales_manager, sales_executive, executive, senior_consultant, principal_consultant

### ADMIN_ROLES_FALLBACK
- admin

---

## Consultant Role Sidebar (`role === 'consultant'`)

### Dashboard
- My Dashboard (/)

### My Workspace
- My Attendance (/my-attendance)
- My Leaves (/my-leaves)
- My Salary Slips (/my-salary-slips)
- My Expenses (/my-expenses)
- My Drafts (/my-drafts)
- My Details (/my-details)
- Mobile App (/mobile-app)
- Team Chat (/chat)
- AI Assistant (/ai-assistant)

### Consulting Section (if showConsulting = true)
- My Schedule (/consulting-meetings) ← **SSOT for meetings/MOM**
- Team Calendar (/meeting-calendar) ← **Read-only view**
- My Clients (/clients)
- Meeting Requests (/consulting/additional-meeting-requests)
- Efforts Summary (/consulting/efforts-summary)
- Payments (/payments)
- Payment Follow-ups (/follow-ups)

### Bottom Links
- Notifications (/notifications)
- Support (/support)
- Settings (/settings)

---

## Reporting Manager / Principal Consultant Sidebar

### Dashboard
- Dashboard (/)

### My Workspace
- My Attendance (/my-attendance)
- My Leaves (/my-leaves)
- My Salary Slips (/my-salary-slips)
- My Expenses (/my-expenses)
- My Drafts (/my-drafts)
- My Details (/my-details)
- My Scorecard (/employee-scorecard) ← **Only for managers**
- Mobile App (/mobile-app)
- **Approvals (/approvals)** ← **Only if hasReportees=true**
- Team Chat (/chat)
- AI Assistant (/ai-assistant)

### Consulting Section (non-consultant view)
- Projects (/projects)
- Team Assignment (/consultants)
- Meetings Calendar (/meeting-calendar)
- **Consulting Meetings (MOM) (/consulting-meetings) [SSOT badge]**
- Meeting Requests (/consulting/additional-meeting-requests)
- Efforts Summary (/consulting/efforts-summary)
- Payments (/payments)
- Project Reports (/reports?category=consulting)

### Bottom Links
- Notifications (/notifications)
- Support (/support)
- Settings (/settings)

---

## ANALYSIS: Issues Found

### 1. CONFUSION: Duplicate/Similar Pages

| Issue | Pages Affected | Problem |
|-------|----------------|---------|
| **Calendar Confusion** | `/meeting-calendar` vs `/consulting-meetings` | Both show meetings but different views. User may not know which to use. |
| **Payments Duplication** | `/payments` appears in both Consulting sections | Same page, potential confusion |
| **Clients Page** | Consultant sees "My Clients", Manager sees via Projects | Different entry points for same data |

### 2. MISSED FLOWS

| Missing Feature | Who Needs It | Impact |
|-----------------|--------------|--------|
| **Backdated Approval UI** | Managers | API exists but no dedicated UI in sidebar. Must access via Approvals Center |
| **Pending Meeting Approvals** | Managers | No badge/count showing pending backdated approvals |
| **SSOT Badge Missing** | Consultants | Consultant sidebar shows "My Schedule" without SSOT badge (managers have it) |

### 3. OVERLAPPING FLOWS

| Flow | Issue |
|------|-------|
| **Meeting Creation** | Calendar page has "Manage Meetings" button that links to Consulting Meetings - creates roundabout flow |
| **Efforts Summary** | Available for both roles but consultant has no project-level view |
| **Payment Follow-ups** | Only in Consultant view, not Manager view (managers use "Lead Follow-ups" in Sales) |

### 4. INCONSISTENT NAMING

| Consultant View | Manager View | Should Be |
|-----------------|--------------|-----------|
| "My Schedule" | "Consulting Meetings (MOM)" | Should both say "Consulting Meetings" with SSOT |
| "My Clients" | (via Projects) | Manager should also see "My Clients" |
| "Team Calendar" | "Meetings Calendar" | Same page, different names |

---

## RECOMMENDATIONS

### Quick Fixes

1. **Add SSOT badge to Consultant's "My Schedule"**
   - Change: `{ name: 'My Schedule', href: '/consulting-meetings', icon: Calendar }` 
   - To: `{ name: 'Consulting Meetings', href: '/consulting-meetings', icon: Calendar, badge: 'SSOT' }`

2. **Rename for consistency**
   - Consultant: "Team Calendar" → "Meetings Calendar" (match manager view)
   - Manager: "Meetings Calendar" → "Team Calendar" (match consultant view)
   - Pick one name and use consistently

3. **Add Approvals badge count for managers**
   - Show pending backdated approvals count on Approvals link

### Structural Fixes

4. **Unify the Meeting Flow**
   ```
   CONSULTANT PATH:
   Consulting Meetings (SSOT) → Create/Record MOM → Claim Expenses
   
   MANAGER PATH:
   Consulting Meetings (SSOT) → View All → Approve Backdated → View Reports
   ```

5. **Add "Pending Approvals" indicator**
   - In sidebar for managers: Show count of pending backdated meetings

6. **Remove "Payment Follow-ups" from Consultant**
   - Or add it to Manager view too for consistency

---

## RECOMMENDED SIDEBAR STRUCTURE

### For Consultant
```
Dashboard (My Dashboard)

MY WORKSPACE
├── My Attendance
├── My Leaves
├── My Salary Slips
├── My Expenses
├── My Details
├── Mobile App
├── Team Chat
└── AI Assistant

CONSULTING
├── Consulting Meetings [SSOT] ← Primary action point
├── Team Calendar ← Read-only view
├── My Clients
├── Meeting Requests
├── Efforts Summary
└── Payments

BOTTOM
├── Notifications
├── Support
└── Settings
```

### For Manager / Principal Consultant
```
Dashboard

MY WORKSPACE
├── My Attendance
├── My Leaves
├── My Salary Slips
├── My Expenses
├── My Details
├── My Scorecard
├── Mobile App
├── Approvals (X pending) ← Show count
├── Team Chat
└── AI Assistant

CONSULTING
├── Projects
├── Team Assignment
├── Consulting Meetings (MOM) [SSOT]
├── Team Calendar
├── Meeting Requests
├── Efforts Summary
├── Payments
└── Project Reports

ADMIN (if applicable)
├── Approvals Center
└── ...

BOTTOM
├── Notifications
├── Support
└── Settings
```
