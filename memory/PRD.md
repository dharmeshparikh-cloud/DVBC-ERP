# DVBC - NETRA: Business Management ERP

## Original Problem Statement
Build a comprehensive business management ERP with modules for Sales, HR, Consulting, and Finance. The initial focus was on "Sales to Consulting" workflow, with recent priorities shifted to enhancing HR and authentication modules.

## Core User Personas
- **System Admin**: Full system access, user management, settings
- **HR Manager**: Employee management, attendance, payroll, permissions
- **Sales Executive**: Lead management, client interactions, invoicing
- **Consultant**: Project work, timesheets, task management
- **Employee**: Self-service (attendance, leaves, expenses, salary slips)

## Tech Stack
- **Frontend**: React with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Auth**: JWT-based authentication

---

## Completed Work

### December 2025 - Session 1
- ✅ Attendance System Overhaul: Rolled back geo-fencing, implemented simplified Quick Check-in
- ✅ Mobile UI Enhancement: Added Quick Check-in shortcut to mobile navigation
- ✅ Permission/Role Sync: Fixed synchronization between `users` and `employees` collections
- ✅ Sidebar Visibility Fix: Now controlled exclusively by `department_access` collection
- ✅ ID Standardization: Migrated `reporting_manager_id` to use employee codes (e.g., "EMP110")
- ✅ Data Scoping: Implemented hierarchy-based filtering for Leads module
- ✅ UI Consolidation: Merged duplicate Attendance UIs
- ✅ Bulk HR Operations: Verified working (dialog, department selection, apply action)
- ✅ "Dept" Button: Verified working in Department Access Manager

---

## Current Architecture

### Key Files
```
/app/
├── backend/
│   ├── routers/
│   │   ├── department_access.py  # Bulk update, department management
│   │   ├── leads.py              # Hierarchy-based data scoping
│   │   └── users.py              # Reporting manager logic
│   └── server.py                 # Main server (NEEDS REFACTORING)
└── frontend/
    └── src/
        ├── layouts/
        │   ├── HRLayout.js       # Mobile check-in button
        │   ├── Layout.js         # Sidebar logic, mobile check-in
        │   └── SalesLayout.js    # Mobile check-in button
        ├── pages/
        │   └── DepartmentAccessManager.js  # Bulk update UI
        └── utils/
            └── constants.js      # Department page lists
```

### Key Database Collections
- **employees**: `reporting_manager_id` uses employee codes (e.g., "EMP110")
- **users**: `role` synced with employee profile changes
- **department_access**: Single source of truth for sidebar visibility

### Key API Endpoints
- `PUT /api/department-access/bulk-update` - Bulk department changes
- `GET /api/leads` - Hierarchy-based data scoping
- `PATCH /api/users/{user_id}/reporting-manager` - Uses employee codes

---

## Prioritized Backlog

### P0 (Critical) - None currently

### P1 (High Priority)
- None currently

### P2 (Medium Priority)
1. **Refactor server.py** - Break into domain-specific routers (recurring 13+ sessions)
2. **Finance Module** - Payments, expenses, P&L reports
3. **Project P&L Dashboards** - Project profitability tracking
4. **Day 0 Onboarding Tour** - Guided tour for new users

### P3 (Low Priority)
1. **PWA Install Notification** - App install prompts
2. **PWA Branding** - Custom icons, splash screens

---

## Test Credentials
- **Admin**: admin@dvbc.com / admin123
- **HR Manager**: hr.manager@dvbc.com / hr123
- **Manager**: dp@dvbc.com / Welcome@123
- **Employee**: rahul.kumar@dvbc.com / Welcome@EMP001

---

## Known Technical Debt
1. `server.py` is monolithic and needs refactoring into routers
2. HTML structure warnings in DepartmentAccessManager (span inside table elements)
3. Some 404 errors for `/api/stats/consulting` and `/api/stats/hr` endpoints
