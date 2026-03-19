# DV Consulting Hub - Business Logic Document

**Version:** 1.0  
**Date:** March 19, 2026  
**Document Type:** Technical & Business Process Documentation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [User Roles & Access Control](#3-user-roles--access-control)
4. [Core Business Flows](#4-core-business-flows)
5. [Module Documentation](#5-module-documentation)
6. [Data Models](#6-data-models)
7. [Integration Points](#7-integration-points)
8. [Audit & Compliance](#8-audit--compliance)

---

## 1. Executive Summary

### 1.1 Purpose
The DV Consulting Hub is an enterprise resource planning (ERP) system designed for consulting organizations. It manages the complete lifecycle from lead acquisition through project delivery, HR management, and financial closure.

### 1.2 Key Capabilities
- **CRM & Lead Management** - Funnel-based lead tracking with stage progression
- **Project Management** - Kickoff workflow, SOW management, consultant assignments
- **HR & Payroll** - Employee onboarding, attendance, leave management, salary processing
- **Expense Management** - Travel expense claims with approval workflow
- **Meeting Management** - Scheduling, MOM recording, client communication

### 1.3 SSOT (Single Source of Truth) Architecture
The system enforces SSOT principles where:
- **Consulting Meetings Page** is the sole entry point for meeting MOM and expenses
- **Payroll Module** is the sole source for salary calculations
- **Kickoff Workflow** is the governance gateway for project creation

---

## 2. System Architecture

### 2.1 Technology Stack
```
Frontend: React 18 + Vite + TailwindCSS + Shadcn/UI
Backend: FastAPI (Python 3.11)
Database: MongoDB
Authentication: JWT-based with role hierarchy
```

### 2.2 Module Structure
```
/app
├── backend/
│   ├── routers/           # API endpoints by domain
│   │   ├── leads.py       # CRM
│   │   ├── kickoff.py     # Project kickoff workflow
│   │   ├── projects.py    # Project management
│   │   ├── meetings.py    # Meeting & MOM
│   │   ├── expenses.py    # Expense management
│   │   ├── payroll.py     # Payroll processing
│   │   ├── leave_requests.py  # Leave management
│   │   └── audit_logging.py   # Audit trail
│   └── services/          # Business logic services
├── frontend/
│   └── src/pages/         # UI components
└── documentation/         # This document
```

---

## 3. User Roles & Access Control

### 3.1 Role Hierarchy
```
Admin (Full Access)
├── Principal Consultant (Project Approval, Team Management)
├── HR Manager (Employee Management, Payroll)
├── Finance Manager (Payments, Receivables)
├── Sales Manager (Lead Management, Kickoff Requests)
│   └── Sales Executive (Lead Creation, Funnel Management)
└── Consultant (Project Work, MOM, Expenses)
```

### 3.2 RBAC Configuration
| Role | Lead | Project | HR | Payroll | Expense | Meeting |
|------|------|---------|----|---------|---------|---------| 
| Admin | Full | Full | Full | Full | Full | Full |
| Principal | Read | Full | Read | Read | Approve | Full |
| HR Manager | - | Read | Full | Full | Approve | Read |
| Sales Manager | Full | Read | - | - | Own | Read |
| Consultant | - | Assigned | - | Own | Own | Assigned |

### 3.3 Fail-Closed Authorization
Critical operations use fail-closed RBAC:
- If role configuration fails to load, access is DENIED
- Explicit role mapping required for sensitive operations
- Audit logging for all access control decisions

---

## 4. Core Business Flows

### 4.1 Lead to Project Flow
```
[Sales Executive]          [Principal Consultant]        [Client]
     │                            │                         │
     ▼                            │                         │
  Create Lead                     │                         │
     │                            │                         │
     ▼                            │                         │
  Qualify Lead                    │                         │
     │                            │                         │
     ▼                            │                         │
  Create Kickoff Request ────────►│                         │
     │                            ▼                         │
     │                    Internal Approval                 │
     │                            │                         │
     │                            ▼                         │
     │                    Project ID Generated              │
     │                            │                         │
     │                            ▼                         │
     │                    Client Email Sent ───────────────►│
     │                            │                         ▼
     │                            │                   Client Approval
     │                            │                         │
     │                            │◄────────────────────────┘
     │                            ▼
     │                    Project Activated
     │                            │
     │                            ▼
     │                    Assign Consultant
     │                            │
     └────────────────────────────┘
```

### 4.2 Meeting & Expense Flow (SSOT)
```
[Consultant]                [HR/Admin]              [Payroll]
     │                          │                       │
     ▼                          │                       │
 Schedule Meeting               │                       │
     │                          │                       │
     ▼                          │                       │
 Conduct Meeting                │                       │
     │                          │                       │
     ▼                          │                       │
 Record MOM                     │                       │
 (In-person = Travel Expense)   │                       │
     │                          │                       │
     ▼                          │                       │
 Expense Created ──────────────►│                       │
 (Auto from MOM)                ▼                       │
                          HR Approval                   │
                               │                        │
                               ▼                        │
                    (If > ₹2000: Admin Approval)        │
                               │                        │
                               ▼                        │
                    Expense Approved ──────────────────►│
                               │                        ▼
                               │              payroll_reimbursements
                               │                        │
                               │                        ▼
                               │              Salary Slip Generated
                               │                        │
                               └────────────────────────┘
```

### 4.3 Leave & Attendance Flow
```
[Employee]              [Reporting Manager]           [Payroll]
     │                         │                          │
     ▼                         │                          │
 Apply Leave                   │                          │
     │                         │                          │
     ▼                         │                          │
 Pending ─────────────────────►│                          │
     │                         ▼                          │
     │                  Approve/Reject                    │
     │                         │                          │
     │◄────────────────────────┘                          │
     ▼                                                    │
 Leave Balance Updated                                    │
     │                                                    │
     ▼                                                    │
 Attendance Marked (on_leave)                             │
     │                                                    │
     └───────────────────────────────────────────────────►│
                                                          ▼
                                              LOP Days Calculated
                                                          │
                                                          ▼
                                              Salary Deduction Applied
```

---

## 5. Module Documentation

### 5.1 CRM Module

#### Lead Stages
| Stage | Description | Next Actions |
|-------|-------------|--------------|
| new_inquiry | Initial contact | Qualify or archive |
| qualification | Evaluating fit | Schedule discovery |
| discovery | Understanding needs | Create proposal |
| proposal | Proposal sent | Negotiate or lose |
| negotiation | Terms discussion | Close or lose |
| closed_won | Deal won | Create kickoff |
| closed_lost | Deal lost | Archive |

#### Key APIs
- `POST /api/leads` - Create lead
- `PATCH /api/leads/{id}` - Update lead/stage
- `GET /api/leads/funnel-stats` - Pipeline analytics

### 5.2 Project Management

#### Project States
| Status | Description | Transitions |
|--------|-------------|-------------|
| draft | Initial creation | → active |
| active | Work in progress | → on_hold, completed |
| on_hold | Temporarily paused | → active, cancelled |
| completed | Successfully delivered | (terminal) |
| cancelled | Terminated early | (terminal) |

#### Consultant Assignment
- Assignments tracked in `consultant_assignments` collection
- History preserved for audit (deactivate old, create new)
- Auto-sync from project `team_members` array

#### Key APIs
- `POST /api/kickoff-requests` - Initiate project
- `POST /api/projects/{id}/sync-assignments` - Sync team
- `GET /api/projects/{id}/assignment-history` - Audit trail

### 5.3 Meeting Management

#### Meeting Types
| Type | Mode | Expense Eligible |
|------|------|------------------|
| Consulting | Online | No |
| Consulting | Offline (In-person) | Yes |
| Sales | Any | Based on policy |

#### MOM (Minutes of Meeting)
Required fields:
- Agenda items
- Discussion points
- Decisions made
- Action items (with assignee, due date)
- SOW scope linkage (if applicable)

#### Travel Expense (SSOT)
For in-person meetings:
- Start/End location (Google Places autocomplete)
- Travel mode (Car ₹7/km, Bike ₹3/km, Transit manual)
- Round trip toggle (doubles distance)
- Auto-calculated expense amount

### 5.4 Expense Management

#### Expense Categories
| Category | Description | Approval Flow |
|----------|-------------|---------------|
| travel | Meeting travel | HR → (Admin if >₹2000) |
| accommodation | Stay expenses | HR → Admin |
| meals | Food expenses | HR |
| equipment | Tools/hardware | HR → Admin |
| other | Miscellaneous | HR |

#### Duplicate Prevention
- Meeting expenses: One expense per meeting_id
- System checks before creation
- Rejected expenses allow re-submission

### 5.5 Payroll Module

#### Salary Components
| Component | Type | Calculation |
|-----------|------|-------------|
| Basic | Earning | 50% of gross |
| HRA | Earning | 20% of gross |
| Special Allowance | Earning | 30% of gross |
| Incentive | Earning | Manual input |
| PF | Deduction | 12% of basic |
| Professional Tax | Deduction | Fixed ₹200 |
| LOP | Deduction | (Daily rate × LOP days) |

#### Payroll Inputs
Monthly inputs per employee:
- Working days, Present days, Absent days
- Incentive amount & reason
- Penalty amount & reason
- Advance deduction
- Overtime hours

#### Reimbursement Integration
```
expenses (approved) 
    → payroll_reimbursements (pending)
        → salary_slips (included in net pay)
```

### 5.6 Leave Management

#### Leave Types
| Type | Annual Quota | Carry Forward |
|------|--------------|---------------|
| Casual Leave | 12 days | No |
| Sick Leave | 6 days | No |
| Earned Leave | 15 days | Yes (max 30) |
| Loss of Pay | Unlimited | N/A |

#### Approval Flow
1. Employee applies → Status: `pending`
2. Reporting Manager reviews
3. Approve → Balance updated, Status: `approved`
4. Reject → Status: `rejected` with reason

---

## 6. Data Models

### 6.1 Core Collections
```javascript
// Employee
{
  id: UUID,
  employee_id: "EMP001",  // Display code
  user_id: UUID,          // Links to users collection
  first_name: String,
  last_name: String,
  department: String,
  designation: String,
  reporting_manager_id: String,
  go_live_status: "active" | "pending" | "terminated",
  salary: Number,
  leave_balance: {
    casual_leave: Number,
    sick_leave: Number,
    earned_leave: Number,
    used_casual: Number,
    used_sick: Number,
    used_earned: Number
  }
}

// Meeting
{
  id: UUID,
  type: "consulting" | "sales",
  mode: "online" | "offline",
  project_id: UUID,
  title: String,
  meeting_date: DateTime,
  status: String,
  organizer_id: UUID,      // NEW: Added for audit
  organizer_name: String,  // Denormalized
  mom_generated: Boolean,
  travel_details: {...},   // For offline meetings
  expense_id: UUID         // Links to expense
}

// Expense
{
  id: UUID,
  employee_id: UUID,       // Internal employee ID (not code)
  category: String,
  amount: Number,
  status: "pending" | "approved" | "rejected",
  meeting_id: UUID,        // Links to meeting (if travel)
  travel_details: {...},
  approved_by: UUID,
  approval_history: [...]
}

// Payroll Reimbursement
{
  id: UUID,
  employee_id: UUID,       // MUST be internal ID for payroll matching
  employee_code: String,   // Display reference
  expense_id: UUID,
  amount: Number,
  payroll_period: "YYYY-MM",
  status: "pending" | "processed"
}
```

### 6.2 ID Conventions
| Collection | ID Format | Example |
|------------|-----------|---------|
| Users | UUID | `848612a5-7093-4b41-...` |
| Employees | Code | `EMP001`, `CON001` |
| Projects | PROJ-DATE-SEQ | `PROJ-20260319-0001` |
| Clients | 5-digit | `98001` |

---

## 7. Integration Points

### 7.1 External Services
| Service | Purpose | Status |
|---------|---------|--------|
| Google Maps API | Location autocomplete, distance calculation | Active |
| Email Service | Notifications, client communication | Active |
| WebSocket | Real-time updates | Active |

### 7.2 Internal Integration Matrix
```
CRM ──────► Kickoff ──────► Projects
                              │
                              ├──► Meetings ──► Expenses
                              │
                              └──► SOW ──────► Finance
                              
HR ───────► Employees ──────► Attendance
                              │
                              ├──► Leave
                              │
                              └──► Payroll ──► Salary Slips
```

---

## 8. Audit & Compliance

### 8.1 Audit Logging
All critical actions logged with:
- Action type (e.g., `leave.approve`, `expense.reject`)
- Entity type and ID
- Before/after state
- Performer ID and timestamp
- Request metadata (IP, user-agent)

### 8.2 Audited Actions
| Module | Actions Logged |
|--------|----------------|
| Leave | request, approve, reject, withdraw |
| Expense | create, hr_approve, admin_approve, reject |
| Payroll | input_update, salary_slip_generate |
| Meeting | mom_update |
| Project | create, assignments_sync |

### 8.3 Data Retention
- Audit logs: Permanent
- Archived data: `archived_expenses`, `archived_*`
- Active data: Soft delete preferred

### 8.4 Access Audit Endpoint
```
GET /api/audit/logs?action=expense&limit=100
Authorization: Bearer {admin_token}
```

---

## Appendix A: API Quick Reference

### Authentication
```
POST /api/auth/login
Body: { "employee_id": "EMP001", "password": "..." }
Response: { "access_token": "...", "user": {...} }
```

### Common Patterns
```
# List with filters
GET /api/{resource}?status=pending&limit=50

# Create
POST /api/{resource}
Body: { ... }

# Update
PATCH /api/{resource}/{id}
Body: { field: newValue }

# Action
POST /api/{resource}/{id}/{action}
Body: { action_data }
```

---

## Appendix B: Environment Variables

| Variable | Purpose |
|----------|---------|
| MONGO_URL | Database connection |
| DB_NAME | Database name |
| JWT_SECRET | Token signing |
| REACT_APP_BACKEND_URL | API base URL |
| REACT_APP_GOOGLE_MAPS_API_KEY | Maps integration |

---

**Document End**

*This document is auto-generated and reflects the system state as of March 19, 2026.*
