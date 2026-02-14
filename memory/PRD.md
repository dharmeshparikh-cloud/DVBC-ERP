# Business Management Application - PRD

## Original Problem Statement
A comprehensive business management application for a 50-person consulting organization covering HR, Marketing, Sales, Finance, and Consulting project workflows.

## Core Requirements
- **Authentication**: Email-based login with roles (Admin, Manager, Executive, Consultant, Project Manager, Principal Consultant)
- **Sales Workflow**: Lead → Pricing Plan → **SOW** → Quotation → Agreement (with SOW) → Approval → Project → Kick-off
- **SOW Management**: Sales creates SOW after Pricing Plan, with version tracking and freeze after kick-off
- **Agreement Structure**: Party Info, NDA, NCA, Renewal, Conveyance, SOW, Project Details, Team, Pricing, Payment Terms, Signature
- **Currency**: Indian Rupees (₹)
- **No Deletion**: Soft delete only - all versions preserved
- **Integrations**: Rocket Reach for lead generation (pending)

## User Personas
1. **Admin**: Full system access, can edit frozen SOW, manage user roles
2. **Manager**: View/download access, approve/reject agreements, view handover alerts
3. **Executive/Sales**: Create leads, pricing plans, SOW, quotations, agreements
4. **Consultant**: View assigned projects and tasks
5. **Project Manager**: Manage projects and consultant assignments
6. **Principal Consultant**: Lead kick-off meetings, freeze SOW, senior consultant role

## Implemented Features (as of Feb 14, 2026)

### Authentication & Roles ✅
- JWT-based email/password authentication
- Six user roles with role-based permissions
- Consultant-specific dashboard and navigation

### SOW (Scope of Work) - Sales Flow (Phase 4) ✅
- **New Sales Workflow**: Lead → Pricing Plan → SOW → Quotation → Agreement
- **SOW Categories**: Sales, HR, Operations, Training, Analytics, Digital Marketing
- **SOW Items**: Title, Description, Deliverables list, Timeline (weeks)
- **Version Tracking**:
  - Every add/edit creates a new version
  - Full snapshot stored at each version
  - View any historical version
  - Changes highlighted with before/after values
- **SOW Builder UI**: List view table, Add/Edit dialogs, Version History
- **SOW Enhancements (Feb 14, 2026) ✅**:
  - List view displaying all SOW items in table format
  - Inline status dropdown for each item (Draft, Pending Review, Approved, Rejected, In Progress, Completed)
  - Manager approval workflow with approve/reject buttons
  - Document upload functionality (SOW-level and per-item)
  - Attached documents section with download capability
  - Overall status tracking (Draft, Pending Approval, Partially Approved, Approved, Complete)
  - Stats cards showing item counts by status
- **SOW Documents Per Item (Feb 14, 2026) ✅**:
  - Removed separate "Attached Documents" section at page top
  - Documents now attached per SOW line item (in Docs column)
  - Documents dialog shows per-item attachments with upload/download
  - Auto-email notification to manager and client when item marked as Completed
  - Notifications stored in database (email sending is MOCKED - queue stored but not sent)

### User Profile & Rights Configuration (Phase 4) ✅
- **User Profile Page**: View/edit name, email, phone, department, designation, bio
- **Role Badge**: Visual indicator of user role
- **My Permissions**: View role-based permissions per module
- **Account Info**: User ID, Status, Member Since
- **Admin Rights Management**: Configure permissions per role (to be enhanced for HR module)

### Agreement with SOW (Phase 4) ✅
- **Agreement Sections**: 
  - Party Information
  - Agreement Between D&V Business Consulting
  - Confidentiality
  - NDA (Non-Disclosure Agreement)
  - NCA (Non-Compete Agreement)
  - Renewal Terms
  - Conveyance
  - SOW (tabular format)
  - Project Details (start date, duration)
  - Team Engagement
  - Pricing Plan
  - Payment Terms & Conditions
  - Signatures
- **Export**: Full agreement data for PDF/Word generation
- **SOW Table**: Category, Title, Description, Deliverables, Timeline

### Kick-off Meeting & SOW Freeze (Phase 3) ✅
- **Kick-off Meeting Scheduling**: By Principal Consultant after agreement approval
- **Meeting Details**: Date, Time, Mode, Location/Link, Attendees, Agenda
- **SOW Freeze**: When kick-off scheduled, SOW becomes frozen
- **Admin Override**: Only Admin can edit frozen SOW
- **Notifications**: Sales team notified when kick-off scheduled

### Task Management System (Phase 2) ✅
- **Task Creation**: Title, Description, Category (7 types), Status (6 types), Priority, Assignee, Dates, Hours
- **Task List View**: Status counts, inline status change, badges, due date urgency
- **Timeline/Gantt View**: Visual timeline, color-coded by status
- **Task CRUD APIs**: Full CRUD with delegate and reorder

### Handover Alerts (Phase 2) ✅
- **15-day deadline tracking** from agreement approval
- **Color-coded urgency levels**:
  - Overdue (red): Past 15 days
  - Critical (orange): 0-3 days remaining
  - Warning (yellow): 4-7 days remaining
  - On Track (green): 8+ days remaining
- **Status indicators**:
  - Project Created (checkmark)
  - Consultants Assigned (count)
- **Action buttons**:
  - Create Project (if not created)
  - Assign Consultants (if project exists)
  - View Tasks

### Consultant Management Module (Phase 1) ✅
- **Consultant user role** with separate login and dashboard
- **Consultant List View** (Admin/Manager) with:
  - Name, email, department
  - Project count and capacity (bandwidth)
  - Meetings completed/committed
  - Total project value
  - Visual bandwidth indicator
- **Consultant Creation** (Admin only)
- **Consultant Dashboard** showing:
  - Active projects, meetings stats
  - Capacity utilization
  - Assigned projects list
- **Bandwidth limits**:
  - Mixed (online + offline): 8 projects
  - Online only: 12 projects
  - Offline only: 6 projects

### Project Assignment System ✅
- Assign consultants to projects
- Change consultant (before project start)
- Admin can change start date
- Unassign consultants
- Track meetings per assignment
- **NEW**: Tasks button on project cards → Task Management
- **NEW**: Assign Consultant button → Consultant assignment dialog

### Lead Management ✅
- Create, view, edit leads
- Automated lead scoring (based on job title, contact info, engagement)
- Lead status tracking (new, contacted, qualified, proposal, agreement, closed, lost)
- High-priority leads display on dashboard

### Sales Funnel (Complete) ✅
1. **Pricing Plans**: Create plans with consultant allocation, duration, discounts
2. **Quotations**: Generate from pricing plans, finalize for agreement creation
3. **Agreements**: Create from quotations, submit for approval
4. **Manager Approvals**: View pending approvals, approve/reject agreements

### Navigation ✅
- Dashboard with clickable stats and quick actions
- Leads management page with "Start Sales Flow" button
- Projects and Meetings modules
- Email Templates
- Sales Funnel section (Pricing Plans, Quotations, Agreements)
- Management section:
  - Approvals (managers/admins)
  - Consultants (managers/admins)
  - **Handover Alerts** (managers/admins/project managers)
- Pending approvals alert on dashboard for managers

### UI/UX ✅
- Black and white theme
- Company logo in sidebar (without text)
- Responsive design
- Data displayed in Indian Rupees (₹)
- Clickable dashboard stat cards with navigation
- "Start Sales Flow" button on lead cards

## Pending/Future Features

### P0 (Critical)
- None at this time - SOW Page enhancements COMPLETED Feb 14, 2026

### P1 (High Priority) - Remaining Phase 2 Items
- Drag-and-drop task reordering in Gantt view (react-gantt-timeline library)
- Agreement Export to Word/PDF
- SOW Monthly Roadmap & RACI Matrix conversion
- Meeting Form with MOM (Minutes of Meeting)
- Project Summary Updates by consultant
- Meetings tracking: Completed vs Committed

### P2 (Medium Priority)
- Quarterly Activity Reports
- Project Stage Tracking
- Rocket Reach integration for lead enrichment
- Email sending for agreements (requires SMTP credentials)
- Detailed Time Tracking module (visits, meeting modes)
- Custom Reporting module

### P3 (Low Priority/Backlog)
- HR Workflow Module
- Marketing Flow Module
- Finance & Accounts Module
- Consulting Project Delivery & Payment Tracking
- Bulk lead import from Rocket Reach

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **Authentication**: JWT

## Test Credentials
- Admin: admin@company.com / admin123
- Manager: manager@company.com / manager123
- Executive: executive@company.com / executive123
- Consultant: rajiv.kumar@company.com / consultant123
- Consultant: priya.sharma@company.com / consultant123

## Known Limitations
- Email sending is MOCKED - requires SMTP credentials for production use
- Rocket Reach integration not yet implemented
- Gantt timeline uses custom implementation (react-gantt-timeline installed but not fully integrated)
