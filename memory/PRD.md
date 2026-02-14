# Business Management Application - PRD

## Original Problem Statement
A comprehensive business management application for a 50-person consulting organization covering HR, Marketing, Sales, Finance, and Consulting project workflows.

## Core Requirements
- **Authentication**: Email-based login with roles (Admin, Manager, Executive, Consultant, Project Manager, Principal Consultant)
- **Sales Workflow**: Lead → Pricing Plan → Quotation → Agreement → Manager Approval → Client Email
- **Sales → Consulting Handover**: Kick-off Meeting with SOW freeze and team alignment
- **Currency**: Indian Rupees (₹)
- **Time Tracking**: Project start date, visits, meetings (committed vs delivered), meeting modes
- **Task Management**: Project tasks with categories and statuses
- **Handover Alerts**: 15-day deadline tracking from agreement approval
- **Integrations**: Rocket Reach for lead generation (pending)

## User Personas
1. **Admin**: Full system access, can create/edit/delete all data, can edit frozen SOW
2. **Manager**: View/download access, can approve/reject agreements, view handover alerts
3. **Executive**: Edit/view access to leads, quotations, agreements
4. **Consultant**: View assigned projects and tasks
5. **Project Manager**: Manage projects and consultant assignments
6. **Principal Consultant**: Leads kick-off meetings, senior consultant role

## Implemented Features (as of Feb 14, 2026)

### Authentication & Roles ✅
- JWT-based email/password authentication
- Six user roles: Admin, Manager, Executive, Consultant, Project Manager, Principal Consultant
- Role-based access control throughout the app
- Consultant-specific dashboard and navigation

### Kick-off Meeting & SOW Management (Phase 3) ✅
- **Kick-off Meeting Scheduling**:
  - Scheduled by Principal Consultant after agreement approval
  - Meeting details: Date, Time, Mode (Online/Offline/Mixed), Location/Link
  - Attendees: Principal Consultant (required), Sales Executive (auto-added), Client Contact (auto-added), Additional Consultants
  - Agenda field for meeting topics
  - Sales team notified when kick-off is scheduled

- **Scope of Work (SOW) Management**:
  - 6 Categories: Sales, HR, Operations, Training, Analytics, Digital Marketing
  - Each category can have multiple scope items
  - Scope items include: Title, Description, Deliverables, Timeline (weeks)
  - SOW displayed in Kick-off Meeting page for alignment

- **SOW Freeze Logic**:
  - SOW is editable until kick-off meeting is scheduled
  - When kick-off is scheduled, SOW becomes FROZEN
  - Only Admin can edit frozen SOW (ensures no unauthorized changes)
  - Prevents mismatch between Sales commitments and Consulting delivery

- **Communication Flow**:
  - Sales → Consulting handover tracked through kick-off meeting
  - Notifications sent to Sales Executive when kick-off scheduled
  - Meeting attendees include both Sales and Consulting team members

### Task Management System (Phase 2) ✅
- **Task Creation** with full details:
  - Title, Description
  - 7 Categories: General, Meeting, Deliverable, Review, Follow Up, Admin, Client Communication
  - 6 Statuses: To Do, Own Task, In Progress, Delegated, Completed, Cancelled
  - Priority: Low, Medium, High, Urgent
  - Assignee (from consultants list)
  - Start Date, Due Date
  - Estimated Hours
- **Task List View** with:
  - Status counts summary (To Do, Own Task, In Progress, Delegated, Completed, Total)
  - Inline status dropdown for quick updates
  - Category and priority badges
  - Due date with color-coded urgency
  - Edit and Delete actions
- **Timeline/Gantt View**:
  - Visual timeline showing tasks with date bars
  - Color-coded by status
  - Today marker
  - Click to edit tasks
- **Task CRUD APIs**: Create, Read, Update, Delete, Delegate, Reorder

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
- None at this time

### P1 (High Priority) - Remaining Phase 2 Items
- Drag-and-drop task reordering in Gantt view (react-gantt-timeline library)
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
