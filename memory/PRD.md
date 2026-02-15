# D&V Business Consulting - Comprehensive Business Management Application

## Product Overview
A comprehensive business management application for D&V Business Consulting, a 50-person HR consulting organization covering HR, Marketing, Sales, Finance, and Consulting projects.

---

## Latest Update (February 15, 2026)

### Team Deployment Auto-Calculation Enhancement ✅ (Latest)

**Major Feature: Automatic Meeting Calculation Based on Frequency & Tenure**
- Added `base_rate_per_meeting` input field (editable, default ₹12,500)
- Added `committed_meetings` auto-calculation based on:
  - Frequency (1-5 per week, 1-4 per month, bi-weekly, quarterly)
  - Project tenure in months
- **Calculation Logic:**
  - 5 per week × 4 weeks × tenure months = total meetings
  - 1 per week × 4 weeks × tenure months = total meetings
  - 1 per month × tenure months = total meetings
- **Example:** For 2-month project: 5/week=40, 1/week=8, 1/month=2
- Real-time preview before adding team member
- Auto-recalculation when tenure changes
- Totals row showing sum of meetings and costs
- **Files Modified:** 
  - `/app/frontend/src/pages/sales-funnel/Agreements.js`
  - `/app/backend/sales_workflow.py`

### Team Deployment Dropdowns Enhancement ✅

**UI Enhancement: Team Deployment Structure Dropdowns**
- Converted `Meeting Type` and `Frequency` inputs from free-text to dropdowns:
  - **Meeting Type Options:** Monthly Review, Weekly Review, Online Review, On-site Visit, Strategy Session, Training Session, Progress Update, Kickoff Meeting, Quarterly Business Review, Data Analysis Review, Marketing Review, HR Consultation
  - **Frequency Options:** 1-5 per week, 1-4 per month, Bi-weekly, 1 per quarter, As needed, On demand
- Ensures data consistency and improved user experience
- **File Modified:** `/app/frontend/src/pages/sales-funnel/Agreements.js`

### Team Deployment & Financial Data Separation ✅

**Major Feature: Team Deployment Structure for Kickoff Requests**
- Added Team Deployment Structure to Agreement creation:
  - Role (Project Manager, Data Analyst, Digital Marketing Manager, etc.) - Dropdown
  - Meeting Type (Monthly Review, Online Review, etc.) - Now Dropdown
  - Frequency (1 per month, Weekly, etc.) - Now Dropdown
  - Mode (Online, Offline, Mixed) - Dropdown
- PM can now review team commitments before accepting projects
- **Routes:** `/kickoff-requests` (updated), `/sales-funnel/agreements` (updated)

**Major Feature: Consulting Team Financial Data Isolation**
- Consulting team (PM, Consultants) can NO longer see:
  - Project costing/pricing
  - Profits and P&L
  - Financial values (₹)
- Replaced pricing columns with:
  - Meeting Frequency (Weekly, Bi-weekly, Monthly, Quarterly)
  - Project Tenure (months)
- Backend enforces `can_see_financials` flag based on role

**Enhanced Kickoff Request Detail Modal:**
- Overview tab: Shows project info, meeting frequency, tenure (no pricing)
- Team Deployment tab: Shows team structure with roles and meeting commitments
- Scope of Work tab: SOW items and deliverables
- Agreement tab: Agreement details (financial data hidden for consulting)

**New Model Fields:**
- Agreement: `meeting_frequency`, `project_tenure_months`, `team_deployment[]`
- KickoffRequest: `meeting_frequency`, `project_tenure_months`

**Updated API Endpoints:**
- `GET /api/kickoff-requests/{id}/details` - Now excludes pricing for PM/consulting roles
- `POST /api/agreements` - Now accepts team_deployment array

### Comprehensive Workflow Redesign ✅

**Major Feature: Domain-Specific Dashboards**
Implemented role/department-based dashboard routing:
- **Sales Dashboard**: For Executive, Account Manager roles
  - Sales Pipeline funnel visualization
  - My Clients (user-specific, not company-wide)
  - Pending Quotations, Agreements tracking
  - Revenue metrics and Kickoff Requests status
- **Consulting Dashboard**: For Consultant, Project Manager roles
  - Project delivery status (Active, Completed, At Risk)
  - Meeting delivery progress with efficiency score
  - Incoming Kickoff requests for PM
  - Consultant workload distribution
- **HR Dashboard**: For HR Manager, HR Executive roles
  - Employee stats by department
  - Today's attendance (Present, WFH, Absent)
  - Pending leave requests and expense approvals
  - Payroll processing status
- **Admin Dashboard**: For Admin, Manager roles
  - Cross-department overview (original dashboard)

**Major Feature: Kickoff Request Workflow (Sales → Consulting Handoff)**
- Sales team creates kickoff request after Agreement approval
- Assigns to specific Project Manager
- PM receives in "Kickoff Inbox" on Consulting Dashboard
- PM can Accept (creates project), Return to Sender, or Reject
- PM can edit kickoff date before accepting
- PM can view full SOW and team deployment before accepting
- Notifications sent on status changes
- **Routes:** `/kickoff-requests`
- **API Endpoints:**
  - `POST /api/kickoff-requests` - Create request
  - `GET /api/kickoff-requests` - List requests
  - `GET /api/kickoff-requests/{id}/details` - Get full details with SOW/team
  - `PUT /api/kickoff-requests/{id}` - Update kickoff date
  - `POST /api/kickoff-requests/{id}/accept` - Accept & create project
  - `POST /api/kickoff-requests/{id}/return` - Return to sender with feedback
  - `POST /api/kickoff-requests/{id}/resubmit` - Sales resubmits after revision
  - `POST /api/kickoff-requests/{id}/reject` - Reject request

**Navigation Updates:**
- Sales section: Added "Kickoff Requests" and renamed "Clients" to "My Clients"
- Consulting section: Added "Kickoff Inbox" for PM role

**New Backend APIs:**
- `GET /api/stats/sales-dashboard` - Sales-specific metrics
- `GET /api/stats/consulting-dashboard` - Consulting metrics
- `GET /api/stats/hr-dashboard` - HR metrics
- `GET /api/my-clients` - User-specific clients

### Admin Downloads Page Created ✅
Created an admin-only "Developer Resources" page with downloadable assets:
- **Route:** `/downloads`
- **Access:** Admin and Manager roles only
- **Downloads Available:**
  - API Documentation (HTML)
  - Postman Collection (JSON)
  - Feature Index (DOCX)

### API Test Suite Fixes ✅
Fixed all failing tests in the comprehensive API test suite:
- **Pass Rate:** 100% (All tests passing)
- **Coverage:** All API endpoints across 10 modules

---

## Business Flow Structure

### Comprehensive API Test Suite Created
Created a production-grade, OWASP-compliant API test suite covering all backend modules:

**Test Statistics (After Fixes):**
- **Total Tests:** 291
- **Pass Rate:** 100% (All tests now passing)
- **Coverage:** All API endpoints across 10 modules

**Test Files Created:**
- `conftest.py` - Shared fixtures, helpers, OWASP payloads
- `test_api_auth.py` - Authentication & security tests (30 tests)
- `test_api_leads.py` - Leads CRUD + security (37 tests)
- `test_api_employees.py` - Employee management tests (26 tests)
- `test_api_clients_expenses.py` - Clients & expenses tests (26 tests)
- `test_api_projects_meetings.py` - Projects & meetings tests (32 tests)
- `test_api_sales_pipeline.py` - SOW, quotations, agreements (31 tests)
- `test_api_hr_module.py` - Leave, attendance, payroll (35 tests)
- `test_api_users_roles.py` - RBAC & permissions tests (24 tests)
- `test_owasp_security.py` - Full OWASP Top 10 2021 (30 tests)
- `test_api_performance.py` - Performance benchmarks (20 tests)
- `reset_test_passwords.py` - Test user credential reset utility

**OWASP Top 10 2021 Coverage:**
- A01: Broken Access Control ✅
- A02: Cryptographic Failures ✅
- A03: Injection (SQL, NoSQL, XSS, Command) ✅
- A04: Insecure Design ✅
- A05: Security Misconfiguration ✅
- A06: Vulnerable Components ✅
- A07: Authentication Failures ✅
- A08: Software Integrity Failures ✅
- A09: Logging & Monitoring Failures ✅
- A10: SSRF ✅

---

## Original Requirements Summary

### Authentication & Roles
- Customizable role and permissions management system
- Google Auth for specific domain (@dvconsulting.co.in) alongside password-based login
- Multiple roles: Admin, Principal Consultant, Lead Consultant, Senior Consultant, Consultant, Lean Consultant, Project Manager, Account Manager, HR Manager, HR Executive, etc.

### Sales Workflow
- Lead → Pricing Plan → SOW → Quotation → Agreement → Approval pipeline
- Lead scoring and management
- Communication logs
- Email templates

### Scope of Work (SOW)
- Advanced SOW builder with spreadsheet-style inline editing
- Version history and status tracking
- Document uploads
- Consultant assignment

### Approval Workflows
- Multi-level approval system based on reporting manager hierarchy
- Leave, expense, and agreement approvals

### Employees Module
- Employee data management (personal details, HR information)
- Hierarchical organizational chart
- Bank details, salary information

### Reporting Manager Rules
- Granular permissions for managers
- Notification/action rights over direct/indirect reports
- Approval escalations
- Self-approval restrictions

### HR Module
- Leave Management with balances
- Attendance tracking
- Advanced Payroll system with customizable components
- Bulk CSV input for payroll
- Salary slip generation with PDF download

### Self-Service Workspace
- My Attendance, My Leaves, My Expenses, My Salary Slips

### Project Management
- Project tracking with deliverables
- Drag-and-drop Gantt Chart linked to SOW
- Client communication module
- Task management

### Admin & Security
- Security audit log for login and critical events
- User management

---

## Implementation Status

### Completed Features ✅

#### Authentication & Security
- [x] Password-based JWT authentication
- [x] Google OAuth 2.0 via Emergent-managed Google Auth (domain restricted)
- [x] Security audit logging for all login events
- [x] OTP-based admin password reset
- [x] Role-based access control

#### HR Module
- [x] Employee management with full CRUD
- [x] Org Chart visualization
- [x] Leave management with balances
- [x] Attendance tracking (individual and bulk)
- [x] Advanced Payroll with customizable salary components
- [x] Payroll input management (CSV import/export)
- [x] Salary slip generation with PDF download

#### Sales Pipeline
- [x] Lead management with scoring
- [x] Communication logs
- [x] Pricing plan builder
- [x] SOW builder with inline editing
- [x] Quotation generation
- [x] Agreement management
- [x] Approval workflows

#### Project Management
- [x] Project creation and tracking
- [x] Task management linked to SOW items
- [x] Gantt chart with drag-and-drop
- [x] Client communication module
- [x] Meeting management with MOM

#### Self-Service
- [x] My Workspace dashboards
- [x] Self-service leave requests
- [x] Self-service expense submissions
- [x] Salary slip viewing

#### Admin
- [x] User management
- [x] Role management
- [x] Security audit log dashboard
- [x] Notification system (in-app bell + browser push)

---

## Data Seeding (December 15, 2025)

### Indian HR Consulting Test Data Created:
- **Users**: 42 (across all roles)
- **Employees**: 41 with complete HR data
- **Leads**: 45 from major Indian companies (Tata Steel, Reliance, Infosys, etc.)
- **Clients**: 6 converted clients
- **Pricing Plans**: 30
- **SOWs**: 30 with HR consulting services
- **Quotations**: 18
- **Agreements**: 10
- **Projects**: 6 active/completed
- **Tasks**: 96 linked to SOW items
- **Meetings**: 48 (sales and consulting)
- **Expense Requests**: 120
- **Leave Requests**: 68
- **Attendance Records**: 2665 (3 months history)
- **Salary Components**: 10 (earnings + deductions)
- **Payroll Inputs**: 246 (6 months history)
- **Communication Logs**: 137
- **Notifications**: 140

### Test Credentials:
- **Admin**: admin@company.com / admin123
- **All Other Users**: [email] / password123

---

## Upcoming Tasks (P1 - High Priority)

1. **RACI Matrix for SOW**
   - Inline-editable role assignments (Responsible, Accountable, Consulted, Informed)
   - Export to PDF/Excel

2. **User Training Guide**
   - Comprehensive downloadable Word/PDF document
   - Coverage of all features, roles, and workflows

---

## Future Tasks (P2 - Medium Priority)

1. **Real Email Integration (SMTP)**
   - Replace mock email system with actual SMTP service

2. **Rocket Reach Integration**
   - Lead enrichment from Rocket Reach API

3. **Detailed Time Tracking**
   - Hourly time tracking against projects and tasks

---

## Backlog (P3)

1. Marketing Flow Module
2. Finance & Accounts Flow Module
3. **Refactor server.py** - Break monolithic file into modular FastAPI routers

---

## Technical Stack

### Frontend
- React 18
- Tailwind CSS
- Shadcn/UI components
- DHTMLX Gantt
- react-to-print, xlsx, file-saver

### Backend
- FastAPI
- Pydantic models
- Motor (async MongoDB driver)
- JWT authentication

### Database
- MongoDB

### Authentication
- Dual: JWT (password-based) + Google OAuth 2.0 (Emergent-managed)

---

## Key Files Reference

- `/app/backend/server.py` - Main API server (needs refactoring)
- `/app/backend/seed_indian_data.py` - Data seeding script
- `/app/frontend/src/pages/` - All page components
- `/app/frontend/src/components/Layout.js` - Navigation and layout

---

## Notes

- Email sending is currently MOCKED (logs to console)
- Org Chart depends on correct reporting_manager data
- The server.py file has grown large and needs modular refactoring
