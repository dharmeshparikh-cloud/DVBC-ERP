# DVBC - NETRA Business Management Platform

## Original Problem Statement
Build a comprehensive business management application for a consulting organization with:
- End-to-end sales workflow
- Consulting workflow with project management
- HR & payroll modules
- Multi-level role-based permissions

## User Personas
1. **Admin** - Full system access
2. **Sales Executive** - Manage leads, meetings, quotations
3. **Sales Manager** - Team oversight, target setting, reviews
4. **Principal Consultant** - Approve targets, see all data
5. **HR Manager** - Employee management, leaves, payroll
6. **Consultant** - Project delivery, timesheets

## Core Requirements

### Sales Flow (Complete)
1. Leads captured
2. Meeting scheduling (multiple per lead, colleague accompaniment)
3. MOM (Minutes of Meeting) generation
4. Meeting status update → Hot/Warm/Cold scoring
5. Hot leads → Pricing Plan
6. SOW Picking/Building
7. Proforma Invoice
8. Agreement (client approval)
9. Kickoff Schedule
10. Hand-off to Consulting team
11. Auto-closure on kickoff acceptance

### Dashboard Metrics (Implemented Feb 2026)
- Total Meetings
- Lead to Meeting ratio
- Total Closures
- Lead to Closure ratio
- Total Deal Value
- Meeting Targets vs Achievement
- Month over Month performance
- Pie charts (Temperature, Status, Sources)
- Line/Area charts (trends)
- Team Leaderboard

### Permission Structure (Implemented Feb 2026)
- Reporting structure based (whoever has reportees sees team data)
- Admin, HR Manager, Principal Consultant see all departments
- Executive sees only own data
- Manager sets team targets (with Principal Consultant approval)

### Sales Team Performance (Implemented Feb 2026)
- Monthly targets: Meeting count, Conversions, Deal value
- Review frequency: Monthly (on or before 5th)
- Review parameters: Meeting Quality, Conversion Rate, Response Time, MOM Quality, Target Achievement
- Parameters configurable by admin

## What's Been Implemented

### Phase 1 - Consulting Flow (Completed Feb 2026)
- My Projects dashboard
- Team Assignment after kickoff
- SOW Change Requests with approval

### Phase 2 - Consulting Flow (Completed Feb 2026)
- Payment Reminders page
- Linked to pricing plan from agreements

### Phase 3 - Sales Enhancement (Completed Feb 2026)
- Enhanced Sales Dashboard with all metrics
- Sales Portal with dedicated login
- Team Performance management
- Target setting and approval workflow
- Performance review system
- Employee workspace in Sales Portal
- Auto-closure on kickoff acceptance

## Technical Architecture

### Backend
- FastAPI with async MongoDB (Motor)
- JWT authentication
- Reporting structure via `reporting_manager_id` field
- Collections: users, leads, meetings, agreements, pricing_plans, sales_targets, performance_reviews

### Frontend
- React with React Router
- Tailwind CSS + Shadcn/UI
- Recharts for visualizations
- Dual portal architecture (Main ERP + Sales Portal)

### Key API Endpoints
- `GET /stats/sales-dashboard-enhanced` - Full dashboard metrics with view_mode
- `POST/GET /sales-targets` - Target management
- `PATCH /sales-targets/:id/approve` - Principal Consultant approval
- `POST/GET /performance-reviews` - Review management
- `GET /my-team` - Get reportees with stats
- `PATCH /users/:id/reporting-manager` - Set reporting structure

## Prioritized Backlog

### P0 (Next)
- Hot status enforcement (block non-Hot from pricing)
- Configure review parameters via admin panel
- Set up reporting structure for demo

### P1
- Real email integration (SMTP)
- P&L Variance tracking
- Gantt chart visualization

### P2 (Tech Debt)
- Refactor server.py into routers
- Refactor large frontend components
- Finance module

## Credentials
- Sales Portal: `sales@consulting.com` / `sales123`
- Main ERP Admin: `admin@company.com` / `admin123`
- Main ERP Manager: `manager@company.com` / `manager123`

## URLs
- Sales Portal: `/sales/login`
- Main ERP: `/login`
