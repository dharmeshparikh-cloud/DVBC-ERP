# DVBC Business Management ERP - Product Requirements Document

## Original Problem Statement
Build a business management application for a consulting firm with complete HR, Sales, and Consulting workflows, including:
- Dedicated portals for Sales and HR teams
- Role-based access control with granular permissions
- End-to-end sales flow: Lead → Meetings → MOM → Hot → Pricing Plan → SOW → Proforma → Agreement → Kickoff → Project
- HR module with employee onboarding, attendance, leave, payroll management
- Consulting team workload visibility for HR (operational data only)

## Core Modules

### 1. Sales Module (Complete)
- **Sales Portal**: `/sales/login` - Dedicated interface for sales team
- **Lead Management**: Full CRUD, status tracking, temperature indicators
- **Meetings & MOM**: Meeting scheduling, minutes of meeting recording
- **Pricing Plans**: Custom pricing builder
- **SOW**: Statement of Work generation with line items
- **Proforma/Quotations**: Invoice generation
- **Agreements**: Contract management with e-signatures
- **Kickoff Requests**: Project handoff to consulting

### 2. HR Module (Complete - Dec 2025)
- **HR Portal**: `/hr/login` - Dedicated interface for HR team
- **Employee Management**: Full CRUD, onboarding wizard
- **Onboarding Flow**: 5-step wizard (Personal → Employment → Documents → Bank → Review)
- **Bank Details**: Proof required, admin approval for post-onboarding changes
- **Team Workload**: HR Manager can view consultant utilization (read-only, no financials)
- **Staffing Requests**: View project staffing needs from kickoff approvals
- **Role Restrictions**: HR Executive has no consulting data access

### 3. Consulting Module (Partial)
- **Projects**: Project management with team assignment
- **Tasks**: Task tracking and Gantt charts
- **Consultant Dashboard**: Personal project view

### 4. Admin Module
- **Admin Dashboard**: Bento grid layout with KPI cards
- **Permission Manager**: Role-based access control
- **Presentation Mode**: LockableCard component for data hiding/locking

## Architecture

### Frontend (React)
```
/app/frontend/src/
├── App.js                    # Main router with Sales/HR portal routes
├── components/
│   ├── Layout.js             # Main ERP layout
│   ├── SalesLayout.js        # Sales portal layout
│   ├── HRLayout.js           # HR portal layout (NEW)
│   └── LockableCard.js       # Presentation mode component
├── pages/
│   ├── HRLogin.js            # HR portal login (NEW)
│   ├── HRPortalDashboard.js  # HR dashboard (NEW)
│   ├── HRTeamWorkload.js     # Consultant workload view (NEW)
│   ├── HRStaffingRequests.js # Staffing requests (NEW)
│   ├── HROnboarding.js       # 5-step onboarding wizard (NEW)
│   └── ... (other pages)
└── contexts/
    └── ThemeContext.js       # Dark/light theme
```

### Backend (FastAPI)
```
/app/backend/server.py
- Authentication & Authorization
- User/Employee/Consultant Management
- Sales Flow APIs
- HR APIs (Bank details approval workflow)
- Project & Task Management
- Permission System
```

### Database (MongoDB)
- Collections: users, employees, leads, meetings, pricing_plans, sow, agreements, projects, tasks, notifications, approval_requests

## Permission Matrix

| Feature | Admin | HR Manager | HR Executive | Sales |
|---------|-------|------------|--------------|-------|
| Projects (create) | ✅ | ❌ | ❌ | ❌ |
| Projects (read) | ✅ | ✅ (no financials) | ❌ | ❌ |
| Consultants (view workload) | ✅ | ✅ | ❌ | ❌ |
| Consulting Meetings | ✅ | ✅ (summary only) | ❌ | ❌ |
| Employees (bank details) | ✅ | with_proof | ❌ | ❌ |
| Leads/SOW/Agreements | ✅ | ❌ | ❌ | ✅ |

## Completed Features (Dec 2025)

### Session 1-5 (Previous)
- [x] Sales Portal with dedicated login
- [x] Full sales flow: Lead → Kickoff
- [x] Admin Dashboard with bento grid
- [x] Dark/Light theme toggle
- [x] Presentation Mode (LockableCard)
- [x] Meeting History in Kickoff Details
- [x] HR Auto-Notification on Project Creation

### Session 6 (Dec 16, 2025)
- [x] HR Portal (`/hr/login`) with dedicated layout
- [x] HR Portal Dashboard with stats and staffing requests
- [x] Team Workload page (HR Manager only, read-only)
- [x] Staffing Requests page from kickoff approvals
- [x] 5-step Onboarding Wizard
- [x] Bank Details with proof requirement
- [x] Bank Details Change Approval workflow
- [x] HR Executive role restriction (no consulting access)
- [x] API fixes: Consultants endpoint for HR Manager

### Session 7 (Current - Feb 16, 2026)
- [x] **Performance Dashboard Enhancements**
  - [x] Added Performance Dashboard to HR Portal sidebar (Team View section)
  - [x] Attendance Rate KPI card with present count
  - [x] Work Location Distribution pie chart (In Office, On-Site, WFH)
  - [x] Leave Patterns by Day bar chart (Mon-Sun)
  - [x] Department Attendance horizontal bar chart
  - [x] Attendance & Location Trends combined chart
  - [x] Financial data hidden for HR roles (Sales Team tab not visible)
- [x] **Attendance Work Location Tracking**
  - [x] Updated Attendance page with Work Location column in Daily Records
  - [x] Mark Attendance dialog with location selection buttons (In Office/On-Site/WFH)
  - [x] Location selection only shows for Present/Half Day status
  - [x] Backend attendance API updated to store work_location field
  - [x] `/api/attendance/analytics` endpoint for comprehensive attendance metrics

## Test Credentials

| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Main ERP | admin@company.com | admin123 | Admin |
| HR Portal | hr_manager@company.com | hr123 | HR Manager |
| HR Portal | lakshmi.pillai83@dvconsulting.co.in | hr123 | HR Executive |
| Sales Portal | sales@consulting.com | sales123 | Sales |

## Backlog / Future Tasks

### P1 - High Priority
- [ ] Frontend permission enforcement (dynamic UI based on roles)
- [ ] Complete meeting management logic for sales flow
- [ ] Lead status enforcement (must be "Hot" for pricing)

### P2 - Medium Priority
- [ ] Business Flow Diagram (HR → Sales → Consulting visualization)
- [ ] Apply LockableCard to Sales Dashboard
- [ ] Rich drill-down views for Admin Dashboard

### P3 - Low Priority / Tech Debt
- [ ] Refactor `server.py` into separate route files
- [ ] Fix incomplete columns in Leads list view
- [ ] Real SMTP integration for emails

### Future
- [ ] Finance Module & Project P&L Dashboards
- [ ] Consulting Phase 3 (Gantt charts, roadmaps)
- [ ] Skill matrix and capacity planning
- [ ] Training/certification tracking

## Known Issues
- Email sending is MOCKED
- Some test data created with TEST_ prefixes
