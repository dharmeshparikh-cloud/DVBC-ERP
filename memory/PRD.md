# Business Management Application - PRD

## Original Problem Statement
A comprehensive business management application for a 50-person consulting organization covering HR, Marketing, Sales, Finance, and Consulting project workflows.

## Core Requirements
- **Authentication**: Email-based login with three roles (Admin, Manager, Executive)
- **Sales Workflow**: Lead → Pricing Plan → Quotation → Agreement → Manager Approval → Client Email
- **Currency**: Indian Rupees (₹)
- **Time Tracking**: Project start date, visits, meetings (committed vs delivered), meeting modes
- **Integrations**: Rocket Reach for lead generation (pending)

## User Personas
1. **Admin**: Full system access, can create/edit/delete all data
2. **Manager**: View/download access, can approve/reject agreements
3. **Executive**: Edit/view access to leads, quotations, agreements

## Implemented Features (as of Feb 14, 2026)

### Authentication & Roles ✅
- JWT-based email/password authentication
- Three predefined user roles (Admin, Manager, Executive)
- Role-based access control throughout the app

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
- Management section (Approvals - visible to managers/admins only)
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

### P1 (High Priority)
- Rocket Reach integration for lead enrichment
- Email sending for agreements (requires SMTP credentials)
- Detailed Time Tracking module (visits, meeting modes)

### P2 (Medium Priority)
- Custom Reporting module
- HR Workflow Module
- Marketing Flow Module
- Finance & Accounts Module

### P3 (Low Priority/Backlog)
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

## Known Limitations
- Email sending is MOCKED - requires SMTP credentials for production use
- Rocket Reach integration not yet implemented
