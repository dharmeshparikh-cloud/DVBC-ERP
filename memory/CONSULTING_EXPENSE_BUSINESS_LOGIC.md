# NETRA ERP - Consulting Meeting & Expense Business Logic
## Version 1.0 | March 2026

---

# TABLE OF CONTENTS

1. Executive Summary
2. System Architecture Overview
3. Meeting Management
4. Expense Management
5. RBAC & Governance Rules
6. Data Flow Diagrams
7. DO's and DON'Ts
8. API Reference
9. Troubleshooting

---

# 1. EXECUTIVE SUMMARY

## Purpose
This document defines the end-to-end business logic for consulting meeting recording and expense management in NETRA ERP. It establishes the Single Source of Truth (SSOT) architecture and governance rules.

## Key Principles
- **Single Source of Truth**: All consulting meetings must be created/managed from the Consulting Meetings page
- **Role-Based Access**: Users can only record MOM if assigned to project AND role matches team deployment
- **Automatic Expense Linkage**: Travel expenses are auto-linked to meetings (prevents duplicates)
- **Governance First**: All operations follow approval workflows

---

# 2. SYSTEM ARCHITECTURE OVERVIEW

## Data Hierarchy

```
Pricing Plan (Sales Phase)
    └── team_deployment[]
        ├── role: "Principal Consultant"
        ├── count: 1
        └── committed_meetings: 2

            ↓ (Kickoff Approval)

Project (Consulting Phase)
    ├── consultant_assignments[]
    │   ├── consultant_id
    │   ├── role
    │   └── is_active
    │
    └── meetings[]
        ├── meeting_id
        ├── mom_generated
        ├── is_delivered
        └── expense_id (linked)

            ↓ (MOM + Travel)

Expense
    ├── expense_id
    ├── meeting_id (REQUIRED - prevents duplicates)
    ├── project_id
    ├── status: pending → HR_approved → admin_approved → reimbursed
    └── travel_details{}
```

## Collections Involved

| Collection | Purpose |
|------------|---------|
| `projects` | Project master data |
| `consultant_assignments` | Who is assigned to which project |
| `meetings` | Meeting records with MOM |
| `expenses` | Travel expenses linked to meetings |
| `pricing_plans` | Team deployment roles |
| `additional_meeting_requests` | Requests for exceeding meeting quota |

---

# 3. MEETING MANAGEMENT

## 3.1 Meeting Creation Rules

### ALLOWED Entry Points
| Entry Point | Allowed? | Reason |
|-------------|----------|--------|
| Consulting Meetings Page | ✅ YES | SSOT - Primary entry |
| Meeting Schedules (Recurring) | ✅ YES | Auto-generated from schedules |

### DISABLED Entry Points
| Entry Point | Status | Reason |
|-------------|--------|--------|
| Meeting Calendar | ❌ DISABLED | Calendar is for planning only |
| Project Details → Meetings Tab | ❌ READ-ONLY | Prevents orphan meetings |
| Mobile App | ❌ DISABLED | Force web for governance |

## 3.2 MOM Recording Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    MOM RECORDING FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User opens Consulting Meetings page                      │
│     └── System shows only assigned project meetings          │
│                                                              │
│  2. User clicks "Record MOM" on a meeting                    │
│     └── RBAC Check:                                          │
│         ├── Is user assigned to project? (consultant_assignments)
│         └── Does user's role match team_deployment?          │
│                                                              │
│  3. User fills MOM details                                   │
│     └── Discussion points, action items, decisions           │
│                                                              │
│  4. For OFFLINE meetings only:                               │
│     └── Travel section appears (checkbox)                    │
│         ├── Start/End location                               │
│         ├── Travel mode (Car/Bike/Transit/Accompanied)       │
│         ├── Distance                                         │
│         └── Round trip toggle                                │
│                                                              │
│  5. User clicks "Complete & Send MOM"                        │
│     └── System checks:                                       │
│         ├── Meeting quota remaining?                         │
│         ├── If exceeded → Need approved additional request   │
│         └── MOM filled?                                      │
│                                                              │
│  6. On success:                                              │
│     ├── MOM email sent to client (NO expense details)        │
│     ├── Meeting marked as delivered                          │
│     ├── Project meeting count incremented                    │
│     └── If travel added → Expense auto-created (pending)     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 3.3 Meeting Types & Travel Eligibility

| Meeting Mode | Can Claim Travel? | Travel Section UI |
|--------------|-------------------|-------------------|
| `offline` | ✅ YES | Shown with checkbox |
| `client_site` | ✅ YES | Shown with checkbox |
| `in_person` | ✅ YES | Shown with checkbox |
| `online` | ❌ NO | Hidden completely |
| `virtual` | ❌ NO | Hidden completely |
| `phone` | ❌ NO | Hidden completely |

---

# 4. EXPENSE MANAGEMENT

## 4.1 Expense Creation Rules

### Sources of Expense Creation
| Source | Auto/Manual | Status Created |
|--------|-------------|----------------|
| Consulting MOM with travel | Auto | `pending` |
| Sales MOM with travel | Auto | `pending` |
| My Expenses (Office only) | Manual | `draft` → `pending` on submit |

### Duplicate Prevention
```
RULE 1: One meeting = One expense
├── Check: expenses.find({ meeting_id: X, status: != "rejected" })
└── If exists: Block creation

RULE 2: Similar expense check
├── Check: Same user + Same date + Amount within ±₹1
└── If exists: Block creation
```

## 4.2 Expense Approval Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   EXPENSE APPROVAL FLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Consultant submits expense                                  │
│            │                                                 │
│            ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ Status: PENDING │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │   HR REVIEW     │ ← HR Manager reviews                   │
│  └────────┬────────┘                                        │
│           │                                                  │
│     ┌─────┴─────┐                                           │
│     ▼           ▼                                            │
│ [Approve]   [Reject]                                        │
│     │           │                                            │
│     ▼           ▼                                            │
│ HR_APPROVED  REJECTED                                        │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │  ADMIN REVIEW   │ ← Admin final approval                 │
│  └────────┬────────┘                                        │
│           │                                                  │
│     ┌─────┴─────┐                                           │
│     ▼           ▼                                            │
│ [Approve]   [Reject]                                        │
│     │           │                                            │
│     ▼           ▼                                            │
│ APPROVED    REJECTED                                         │
│     │                                                        │
│     ▼                                                        │
│ ┌──────────────────┐                                        │
│ │ PAYROLL LINKAGE  │ ← Linked to payroll period             │
│ └──────────────────┘                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 4.3 Expense Edit Rules

| Status | Who Can Edit? | What Can Be Edited? |
|--------|---------------|---------------------|
| `pending` | Creator only | All fields |
| `hr_approved` | ❌ No one | Locked |
| `approved` | ❌ No one | Locked |
| `rejected` | Creator (resubmit) | All fields |
| `reimbursed` | ❌ No one | Locked |

## 4.4 Travel Expense Rates

| Mode | Rate | Calculation |
|------|------|-------------|
| Car (DRIVING) | ₹7/km | distance × rate × (2 if round trip) |
| Bike (TWO_WHEELER) | ₹3/km | distance × rate × (2 if round trip) |
| Transit | Manual entry | User enters actual amount |
| Accompanied | ₹0 | No expense created |

---

# 5. RBAC & GOVERNANCE RULES

## 5.1 Who Can Record MOM?

```
CHECK 1: Is user Admin or Principal Consultant?
├── YES → ALLOWED (override)
└── NO → Continue to Check 2

CHECK 2: Is user assigned to project?
├── Query: consultant_assignments.find({
│           project_id: X,
│           consultant_id: user.id,
│           is_active: true
│         })
├── NOT FOUND → DENIED ("You are not assigned to this project")
└── FOUND → Continue to Check 3

CHECK 3: Does user's role match team_deployment?
├── Get pricing_plan.team_deployment for project
├── Normalize roles (lowercase, replace spaces with _)
├── Check if user.role matches any deployment role
├── NO MATCH → DENIED ("Your role is not in team deployment")
└── MATCH → ALLOWED
```

## 5.2 Who Can View Project Expenses?

| Role | Access Level |
|------|--------------|
| Admin | View ALL project expenses |
| Principal Consultant | View ALL project expenses |
| Project Manager | View assigned project expenses |
| Other Consultants | View own expenses only |

## 5.3 Meeting Quota Governance

```
BEFORE marking meeting as delivered:

1. Get project.total_meetings_committed
2. Get project.total_meetings_delivered
3. Calculate remaining = committed - delivered

IF remaining > 0:
   └── ALLOW delivery

IF remaining <= 0:
   └── Check for approved additional_meeting_requests
       ├── FOUND unused approved request → ALLOW (mark request as used)
       └── NOT FOUND → DENY ("Meeting limit exceeded. Submit additional request.")
```

---

# 6. DATA FLOW DIAGRAMS

## 6.1 End-to-End Flow

```
SALES PHASE                          CONSULTING PHASE
═══════════                          ═════════════════

Lead Created                         
     │                               
     ▼                               
Pricing Plan                         
├── team_deployment                  
│   ├── Principal (2 meetings)       
│   ├── Senior (6 meetings)          
│   └── Consultant (4 meetings)      
     │                               
     ▼                               
Quotation → SOW → Agreement          
     │                               
     ▼                               
Kickoff Request ─────────────────►   Project Created
                                     ├── consultant_assignments (empty)
                                     ├── total_meetings_committed: 12
                                     └── total_meetings_delivered: 0
                                          │
                                          ▼
                                     Admin assigns consultants
                                     ├── Add Principal Consultant
                                     ├── Add Senior Consultant
                                     └── Add Consultant
                                          │
                                          ▼
                                     Meeting Schedule Created
                                     └── Recurring meetings generated
                                          │
                                          ▼
                                     Consultant Records MOM
                                     ├── RBAC validated
                                     ├── MOM filled
                                     └── Travel added (if offline)
                                          │
                                          ▼
                                     Complete & Send MOM
                                     ├── Email sent (no expense)
                                     ├── Meeting count +1
                                     └── Expense created (pending)
                                          │
                                          ▼
                                     HR Approval → Admin Approval
                                          │
                                          ▼
                                     Payroll Linkage
```

## 6.2 Meeting Calendar vs Consulting Meetings

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  MEETING CALENDAR (Planning Only)         CONSULTING MEETINGS (SSOT)   │
│  ════════════════════════════════         ══════════════════════════   │
│                                                                        │
│  Purpose: Monthly/Weekly planning         Purpose: Record actual MOM   │
│                                                                        │
│  Features:                                Features:                    │
│  ✅ View assigned projects                ✅ View scheduled meetings   │
│  ✅ Create month plan                     ✅ Record MOM                │
│  ✅ Reschedule plan items                 ✅ Add travel expenses       │
│  ✅ Manager approval for plan             ✅ Complete & send MOM       │
│  ✅ Efficiency tracking                   ✅ Meeting quota check       │
│                                                                        │
│  ❌ Create actual meetings                ✅ Create actual meetings    │
│  ❌ Record MOM                            ✅ RBAC enforced             │
│  ❌ Add expenses                          ✅ Auto expense creation     │
│                                                                        │
│  No linkage to:                           Linked to:                   │
│  - Meetings collection                    - Projects                   │
│  - Expenses collection                    - Meetings                   │
│  - Pricing plan                           - Expenses                   │
│                                           - Pricing plan               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 7. DO's and DON'Ts

## 7.1 For Consultants

### ✅ DO's
- Record MOM immediately after meeting
- Add travel details for offline meetings before completing MOM
- Check meeting quota before scheduling additional meetings
- Use Consulting Meetings page as the ONLY source for meeting management
- Verify you're assigned to project before attempting MOM

### ❌ DON'Ts
- Don't create meetings from Meeting Calendar
- Don't create meetings from Project Details page
- Don't submit duplicate expenses for same meeting
- Don't claim travel for online/virtual meetings
- Don't wait too long to record MOM (client expects timely updates)

## 7.2 For Project Managers / Principal Consultants

### ✅ DO's
- Assign consultants to projects before meetings start
- Ensure team_deployment roles match assigned consultant roles
- Monitor meeting quota usage
- Approve additional meeting requests promptly
- Review consultant expenses regularly

### ❌ DON'Ts
- Don't assign consultants whose roles aren't in team_deployment
- Don't ignore additional meeting requests
- Don't bypass RBAC checks
- Don't approve expenses without proper documentation

## 7.3 For HR / Admin

### ✅ DO's
- Review expense details including travel route
- Verify expense amount matches travel mode rates
- Check if meeting is linked to expense
- Approve/reject within reasonable timeframe
- Link approved expenses to correct payroll period

### ❌ DON'Ts
- Don't approve expenses without meeting linkage
- Don't modify expense amounts without documentation
- Don't process duplicate expense claims
- Don't approve travel for online meetings

## 7.4 For System Administrators

### ✅ DO's
- Maintain team_deployment in pricing plans
- Keep consultant_assignments up to date
- Monitor meeting quota across projects
- Audit expense creation patterns
- Backup data regularly

### ❌ DON'Ts
- Don't delete meeting records
- Don't manually modify expense status
- Don't bypass approval workflows
- Don't change pricing plan after project starts

---

# 8. API REFERENCE

## 8.1 Meeting APIs

| Endpoint | Method | Purpose | RBAC |
|----------|--------|---------|------|
| `/api/consulting/meetings` | GET | List meetings | Assigned consultants |
| `/api/meeting-schedules/meetings/{id}/complete-and-send` | POST | Complete MOM | Assigned + Role match |
| `/api/meeting-schedules/project/{id}/meeting-status` | GET | Get quota status | All consulting roles |
| `/api/meeting-schedules/additional-meeting-request` | POST | Request more meetings | All consulting roles |

## 8.2 Expense APIs

| Endpoint | Method | Purpose | RBAC |
|----------|--------|---------|------|
| `/api/expenses` | POST | Create expense | Auto from MOM |
| `/api/my/expenses` | GET | My expenses | Own expenses |
| `/api/expenses/{id}` | PUT | Edit expense | Creator only (if pending) |
| `/api/expenses/{id}/submit` | POST | Submit for approval | Creator only |

## 8.3 Request/Response Examples

### Complete MOM with Travel
```json
POST /api/meeting-schedules/meetings/{meeting_id}/complete-and-send

Request:
{
  "travel_details": {
    "start_location": "Mumbai Office",
    "end_location": "Client Site, Pune",
    "travel_mode": "DRIVING",
    "distance_km": 150,
    "is_round_trip": true
  }
}

Response:
{
  "success": true,
  "meeting_id": "uuid",
  "is_delivered": true,
  "mom_sent": true,
  "expense_created": "expense-uuid"
}
```

---

# 9. TROUBLESHOOTING

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "You are not assigned to this project" | User not in consultant_assignments | Admin must assign user to project |
| "Your role is not in team deployment" | Role mismatch | Check pricing plan team_deployment |
| "Meeting limit exceeded" | All committed meetings used | Submit additional meeting request |
| "Expense already exists for this meeting" | Duplicate prevention | Check existing expense for meeting |
| Travel section not showing | Meeting is online type | Travel only for offline meetings |

## Audit Queries

### Check consultant assignments
```javascript
db.consultant_assignments.find({ project_id: "X", is_active: true })
```

### Check meeting quota
```javascript
db.projects.findOne({ id: "X" }, { total_meetings_committed: 1, total_meetings_delivered: 1 })
```

### Find duplicate expenses
```javascript
db.expenses.aggregate([
  { $group: { _id: "$meeting_id", count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
])
```

---

# DOCUMENT CONTROL

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | March 2026 | System | Initial release |

---

**END OF DOCUMENT**
