# Business Management Application - PRD

## Original Problem Statement
A comprehensive business management application for a 50-person consulting organization covering HR, Marketing, Sales, Finance, and Consulting project workflows.

## Application Name: DVBC - NETRA

## Core Requirements
- **Authentication**: Dual login — Google OAuth (domain-restricted to @dvconsulting.co.in) + Email/Password (admin-created accounts)
- **Sales Workflow**: Lead → Pricing Plan → **SOW** → Quotation → Agreement (with SOW) → Approval → Project → Kick-off
- **SOW Management**: Sales creates SOW after Pricing Plan, with version tracking and freeze after kick-off
- **Agreement Structure**: Party Info, NDA, NCA, Renewal, Conveyance, SOW, Project Details, Team, Pricing, Payment Terms, Signature
- **Currency**: Indian Rupees (₹)
- **No Deletion**: Soft delete only - all versions preserved
- **Integrations**: Rocket Reach for lead generation (pending)

## User Personas & Roles (13 Roles - Customizable)

### System Roles (Cannot be deleted)
1. **Admin**: Full system access, manage users/roles/permissions, edit frozen SOW
2. **Manager**: View/download access, approve agreements, handover alerts
3. **Executive**: Sales team - create leads, SOW, quotations, agreements
4. **Consultant**: View SOW, update progress/status on assigned items
5. **Project Manager**: Audit, approve, authorize SOW for client
6. **Principal Consultant**: Freeze SOW, lead kick-off meetings

### Custom Roles (Can be deleted/modified)
7-13: Lean Consultant, Lead Consultant, Senior Consultant, HR Executive, HR Manager, Account Manager, Subject Matter Expert

## Authentication System (Feb 15, 2026)
- **Dual Login**: Email/Password (primary, all users) + Google OAuth (secondary, @dvconsulting.co.in only)
- **Domain Restriction**: Google login restricted to dvconsulting.co.in Google Workspace accounts
- **Pre-Registered Only**: Google email must match existing employee record in DB
- **Admin Password Fallback**: Admin can always login via email/password
- **OTP Password Reset**: Admin-only, 6-digit OTP with 10-min expiry
- **Change Password**: Logged-in users can change their password
- **Security Audit Log**: All auth events logged (login success/failure, OTP, password changes) with IP, user agent, timestamps
- **Admin Audit Report**: Filterable table with Export CSV

## Implemented Features

### Authentication & Security (Feb 15, 2026) ✅
- Google OAuth via Emergent Auth with domain restriction
- Email/Password login for all users
- Admin OTP password reset
- Security Audit Log with search, filter, export
- All auth events tracked with IP address

### Approval Workflow Engine ✅
- Approvals Center with pending/my-requests/all tabs
- Multi-level approval chain based on reporting manager hierarchy
- Leave Request System auto-routed to manager → HR

### Role & Permissions Management ✅
- 13 customizable roles with RBAC
- User Management page with role assignment

### Sales Workflow ✅
- Lead management with scoring
- Pricing Plan Builder
- SOW Builder with version history
- Quotations with approval workflow
- Agreements with templates
- Manager Approvals

### HR Module ✅
- Employee Management
- Org Chart (visual hierarchy)
- Leave Management with approval
- Attendance tracking (manual/Excel)
- Payroll with salary components
- Expense Management with approval

### My Workspace (Self-Service) ✅
- My Attendance, My Leaves, My Salary Slips, My Expenses

### Meetings & MOM ✅
- Sales Meetings and Consulting Meetings (separate modules)
- Consulting MOMs linked to SOWs with commitment tracking

### Consulting ✅
- Project Roadmap (Table/Kanban views)
- Consultant Performance reviews

### Reports & Documents ✅
- Comprehensive reporting with Excel/PDF download
- Feature Index Word document generation

## Upcoming Tasks (P1)
- RACI Matrix for SOW
- Drag-and-Drop Gantt Chart

## Future Tasks (P2)
- Real Email Integration (SMTP)
- Rocket Reach Integration
- Detailed Time Tracking
- Project Stage Tracking
- Quarterly Activity Reports

## Backlog (P3)
- Marketing Flow Module
- Finance & Accounts Flow Module
- Salary Slip PDF Download
- Server.py refactoring into modular routers

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **Authentication**: JWT + Google OAuth (Emergent Auth)
- **Document Generation**: python-docx

## Key API Endpoints
- `/api/auth/login` - Email/password login
- `/api/auth/google` - Google OAuth login
- `/api/auth/admin/request-otp` - Generate OTP for admin
- `/api/auth/admin/reset-password` - Reset password with OTP
- `/api/auth/change-password` - Change password (logged in)
- `/api/security-audit-logs` - Security audit logs (admin only)

## Test Credentials
- Admin: admin@company.com / admin123
- Manager: manager@company.com / manager123
- Executive: executive@company.com / executive123
