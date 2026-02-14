# Business Management Application - PRD

## Original Problem Statement
A comprehensive business management application for a 50-person consulting organization covering HR, Marketing, Sales, Finance, and Consulting project workflows.

## Core Requirements
- **Authentication**: Email-based login with customizable roles
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
7. **Lean Consultant**: Junior consultant role
8. **Lead Consultant**: Lead consultant with team oversight
9. **Senior Consultant**: Senior consultant with advanced permissions
10. **HR Executive**: HR team member
11. **HR Manager**: HR team manager with user management
12. **Account Manager**: Handles client accounts and sales
13. **Subject Matter Expert**: Domain expert for consulting

## Role-Based SOW Access Control
- **Sales Team** (create/edit SOW): Admin, Executive, Account Manager
- **Consulting Team** (view/update status): Consultant, Lean Consultant, Lead Consultant, Senior Consultant, Principal Consultant, Subject Matter Expert
- **PM/Audit Team** (approve/authorize): Admin, Project Manager, Manager

## Implemented Features

### Role & Permissions Management Module (Feb 14, 2026) ✅ NEW
- **User Management Page**: Integrated Users and Roles tabs
- **Users Tab**:
  - List all users with name, email, department, role, status
  - Admin can change user roles via dropdown
  - Add User dialog for creating new users
  - Search and filter by role
- **Roles Tab**:
  - Display all 13 roles as cards
  - System badge for protected roles
  - User count per role
  - Create Role dialog (custom roles only)
  - Permissions button opens configuration dialog
  - Delete button (custom roles only)
- **Permissions Dialog**:
  - Configure module access per role
  - 10 modules: Leads, Pricing Plans, SOW, Quotations, Agreements, Projects, Tasks, Consultants, Users, Reports
  - Toggle actions: Create, Read, Update, Delete, + special actions (Freeze, Approve, Authorize Client, etc.)
  - Save permissions to database
- **APIs**:
  - `GET /api/roles` - List all roles
  - `POST /api/roles` - Create custom role
  - `GET /api/roles/{role_id}` - Get role with permissions
  - `PATCH /api/roles/{role_id}` - Update role/permissions
  - `DELETE /api/roles/{role_id}` - Delete custom role
  - `GET /api/users-with-roles` - Users with role info
  - `PATCH /api/users/{user_id}/role` - Change user role
  - `GET /api/permission-modules` - Available modules/actions
  - `GET /api/roles/categories/sow` - SOW access categories

### SOW Role-Based Segregation (Feb 14, 2026) ✅ NEW
- **Sales Team Features**: Add New Row button, Edit/Delete buttons, Submit for Approval
- **Consulting Team Features**: Status dropdown (can update progress), View documents
- **PM Team Features**: Approve/Reject buttons for pending items, Approve All button
- Dynamic UI based on user role category

### Authentication & Roles ✅
- JWT-based email/password authentication
- 13 customizable user roles
- Consultant-specific dashboard and navigation

### SOW (Scope of Work) - Sales Flow ✅
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
- **SOW Inline Editing & Roadmap (Feb 14, 2026) ✅**:
  - Spreadsheet-style inline editing - add rows directly in table
  - Single consultant assignment per SOW item
  - Backend support team assignment (optional per line) with role selection
  - Start week field for scheduling items
  - Roadmap view - Monthly breakdown of SOW items
  - Gantt chart view - Timeline visualization with horizontal bars
  - Bulk item deletion with version tracking
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

### Pending/Future Features

### P0 (Critical)
- **Two-Step SOW Approval Workflow**: Checkboxes to select items → Submit for Manager Approval → Manager Approves → Authorize for Client

### P1 (High Priority)
- SOW linkages with consultant performance and project roadmap
- Drag-and-drop task reordering in Gantt view (react-gantt-timeline library)
- Agreement Export to Word/PDF
- SOW Monthly Roadmap & RACI Matrix conversion
- Meeting Form with MOM (Minutes of Meeting)

### P2 (Medium Priority)
- Quarterly Activity Reports
- Project Stage Tracking
- Rocket Reach integration for lead enrichment
- Email sending for agreements (requires SMTP credentials)
- Detailed Time Tracking module

### P3 (Low Priority/Backlog)
- HR Workflow Module
- Marketing Flow Module
- Finance & Accounts Module

## Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI, Pydantic, Motor (async MongoDB)
- **Database**: MongoDB
- **Authentication**: JWT with customizable role-based permissions

## Test Credentials
- Admin: admin@company.com / admin123
- Manager: manager@company.com / manager123
- Executive: executive@company.com / executive123

## Known Limitations
- Email sending is MOCKED - requires SMTP credentials for production use
- Rocket Reach integration not yet implemented
