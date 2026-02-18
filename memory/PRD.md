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

### Session 7 (Current - Feb 16-17, 2026)
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
- [x] **Self Check-In with GPS Location Capture**
  - [x] "Check In Now" button on My Attendance page
  - [x] GPS location capture using browser geolocation API
  - [x] Reverse geocoding for address display via OpenStreetMap
  - [x] Work location selection (In Office/On-Site/WFH)
  - [x] Duplicate check-in prevention (once per day)
  - [x] `POST /api/my/check-in` endpoint stores geo_location data
  - [x] Location column in My Attendance table
- [x] **Enhanced Mobile Employee App with Geofencing**
  - [x] Mobile-optimized employee app at `/mobile`
  - [x] Mandatory selfie capture for check-in (stored as base64)
  - [x] Mandatory GPS location with address display
  - [x] Geofencing validation (500m radius using Haversine formula)
  - [x] WFH removed - only Office and Client Site options
  - [x] Consulting/Delivery employees can check in from office OR assigned client sites
  - [x] Non-consulting employees can ONLY check in from office
  - [x] Unknown location check-ins require justification
  - [x] Auto-approval for known locations, HR approval for unknown
  - [x] Check-out functionality with work hours calculation
  - [x] Admin/HR can disable employee mobile app access
- [x] **HR Attendance Approvals**
  - [x] `/hr/attendance-approvals` page to review pending check-ins
  - [x] View selfie, location, justification for each pending record
  - [x] Approve/Reject with HR remarks
  - [x] Employee notifications on approval status
- [x] **Office Locations Settings (Admin)**
  - [x] `/office-locations` page to configure geofencing locations
  - [x] Add/Edit/Delete office coordinates
  - [x] 3 offices pre-configured: Bangalore HQ, Mumbai, Delhi
- [x] **Client Geo-Coordinates**
  - [x] `PUT /api/clients/{id}/geo-coordinates` endpoint
  - [x] All existing clients updated with geo_coordinates

### Session 8 (Feb 17, 2026)
- [x] **Dark Mode Fix - Projects Page**
  - [x] Fixed hardcoded `text-zinc-950` classes with dark mode variants
  - [x] Project cards now readable in dark mode
  - [x] Border colors updated for dark mode compatibility
- [x] **Modern Login Page Redesign**
  - [x] Redesigned main ERP login (`/login`) to match HR/Sales portal aesthetics
  - [x] Split-screen layout with feature highlights on left panel
  - [x] Dark gradient background with feature cards (Unified Dashboard, HR Management, Project Control, Analytics)
  - [x] Quick links to HR Portal and Sales Portal
  - [x] Responsive design with mobile portal links
- [x] **Onboarding Flow in Main ERP**
  - [x] Added `/onboarding` route to main ERP (previously only in HR Portal)
  - [x] Added "Onboarding" link in HR section of main sidebar
  - [x] Full 5-step onboarding wizard accessible from main ERP
- [x] **Attendance Approvals in Main ERP**
  - [x] Added `/attendance-approvals` route to main ERP
  - [x] Added "Attendance Approvals" link in HR section of main sidebar
- [x] **Mobile App Access Status in Employees**
  - [x] New "Mobile App" column showing Enabled/Disabled status with phone icon
  - [x] Toggle button for Admin/HR to enable/disable mobile app access per employee
  - [x] Employee detail dialog shows mobile app status with reason if disabled
  - [x] Work location field displayed in employee details
- [x] **Mobile App Download Page**
  - [x] New `/mobile-app` page with QR code for easy employee access
  - [x] Step-by-step installation instructions for iOS (Safari) and Android (Chrome)
  - [x] "Open Mobile App" direct link button
  - [x] QR code popup accessible from Employees page for HR to share
  - [x] "Mobile App" link added to My Workspace section in sidebar
  - [x] App features showcase (Selfie Check-in, GPS, Notifications, Geofencing)
- [x] **Mobile App Usage Stats API**
  - [x] `GET /api/attendance/mobile-stats` endpoint
  - [x] Today's mobile vs desktop check-ins count
  - [x] Total mobile app users tracking
  - [x] Pending approvals count
  - [x] Weekly trend data for mobile adoption

## Test Credentials

| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Main ERP | admin@company.com | admin123 | Admin |
| HR Portal | hr.manager@company.com | hr123 | HR Manager |
| HR Portal | hr.executive@company.com | hr123 | HR Executive |
| Sales Portal | sales@consulting.com | sales123 | Sales |
| Mobile App | prakash.rao76@dvconsulting.co.in | password123 | Consultant |

## Recent Updates (February 2025)

### Auto Travel Reimbursement System (COMPLETED)
A comprehensive travel reimbursement feature for employees:

**Features:**
- **Distance Calculation**: Uses Haversine formula for accurate distance calculation
- **Per-km Rates**: ₹7/km for car, ₹3/km for two-wheeler
- **Round Trip Support**: Auto-doubles distance for return journeys
- **Location Search**: Google Geocoding API integration for accurate location search (with $200/month free credits)
- **Mobile App Integration**: Dedicated Travel tab for Sales team in `/mobile`
- **ERP Management**: HR/Admin can approve/reject/convert travel claims
- **Payroll Integration**: Approved claims can be converted to expenses
- **Auto-Prompt on Check-out**: Consultants checking out from client sites are automatically prompted to claim travel reimbursement with pre-filled locations and vehicle selection

**Components:**
- `/mobile` - Travel tab with claim submission (location search, vehicle type, round trip toggle)
- `/mobile` - Auto travel claim modal after client site check-out
- `/travel-reimbursement` - ERP page for HR/Admin to manage claims
- Backend APIs: `/api/travel/*` endpoints for CRUD operations

**Scenarios Supported:**
1. **Consultants**: Auto-calculate from attendance check-in/out locations (prompted on check-out)
2. **Sales Team**: Manual entry with location search for client meetings

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

### Session 9 (Feb 17, 2026) - ERP Workflow, Permissions & Onboarding
- [x] **High-Priority Workflow Diagrams Added**
  - [x] Leave Management, Expense Reimbursement, Invoice to Collection flows
- [x] **Lead to Delivery Workflow Corrections**
  - [x] Fixed subtitle, sales handover flow, team assignment permissions
- [x] **Team Assignment Permission Update (Database & API)**
  - [x] Only Admin, Manager, Project Manager, Principal Consultant can assign consultants
  - [x] HR roles CANNOT assign consultants
- [x] **Dark Mode UI Fix for Workflow Page**
  - [x] Updated CSS variables for proper dark/light mode contrast
- [x] **Login Page Input Fix**
  - [x] Fixed white text on white background issue
  - [x] Added explicit `text-black` class to all login input fields
- [x] **Fresh Test Environment Created**
  - [x] Cleared database and created 12 test users for all roles
- [x] **Grant System Access Feature**
  - [x] New API endpoints: `/employees/{id}/grant-access`, `/employees/{id}/revoke-access`
  - [x] Admin/HR Manager can create login credentials for employees
  - [x] Dialog in Employees page with role selection and temporary password
- [x] **Onboarding Tutorials Page**
  - [x] Created `/tutorials` page with step-by-step guides
  - [x] Added to Admin and HR navigation panels
  - [x] Includes tutorials for: Add Employee, Grant Access, Mark Attendance, Apply Leave
  - [x] Interactive progress tracking with "Mark Done" buttons
- [x] **Change Password Feature (Feb 17, 2026)**
  - [x] `ChangePasswordDialog` component with form validation
  - [x] Password strength indicator (5 levels: Very Weak to Strong)
  - [x] Password match validation and requirements display
  - [x] Integrated into Main ERP Layout (Layout.js)
  - [x] Integrated into HR Portal Layout (HRLayout.js)
  - [x] Integrated into Sales Portal Layout (SalesLayout.js)
  - [x] Backend API: `POST /api/auth/change-password`
  - [x] Security audit logging on password changes
  - [x] Full test coverage: 7 backend tests, UI verification across all portals

### Session 10 (Feb 17, 2026) - CTC Structure & Approval Workflow
- [x] **CTC Structure Designer**
  - [x] New page at `/ctc-designer` for HR/Admin to design employee CTC
  - [x] Standard Indian CTC components with automatic calculation:
    - Basic Salary (40% of CTC)
    - HRA (50% of Basic)
    - DA (10% of Basic)
    - Conveyance Allowance (₹1,600/month fixed)
    - Medical Allowance (₹1,250/month fixed)
    - Special Allowance (balance/adjusting figure)
    - PF Employer Contribution (12% of Basic)
    - Gratuity (4.81% of Basic)
    - Optional Retention Bonus (paid after vesting period, default 12 months)
  - [x] Real-time CTC breakdown preview with summary
  - [x] Employee selection with current salary display
  - [x] Effective month selector (payroll cycle: 10th to 10th)
  - [x] Stats dashboard showing pending/approved/rejected counts (Admin only)
- [x] **Admin Approval Workflow**
  - [x] HR submits CTC structure → Creates pending approval
  - [x] Admin sees pending approvals in dedicated section
  - [x] Approval dialog shows full breakdown comparison
  - [x] Admin can approve (activates CTC, updates employee salary) or reject (requires reason)
  - [x] Notifications sent to Admin on submission, HR on approval/rejection
  - [x] CTC history tracking with version control
- [x] **Configurable CTC Components (Feb 17, 2026 Enhancement)**
  - [x] Toggle switches to enable/disable components per employee
  - [x] 13 configurable components with editable values:
    - Basic Salary (40% of CTC) - REQUIRED
    - HRA (50% of Basic) - Enabled by default
    - DA (10% of Basic) - DISABLED by default
    - Conveyance Allowance (₹1600/month) - Enabled by default
    - Medical Allowance (₹1250/month) - Enabled by default
    - Special Allowance (auto-calculated balance) - REQUIRED
    - PF Employer (12% of Basic) - DISABLED by default
    - PF Employee Deduction (12% of Basic) - DISABLED by default
    - ESIC Employer (3.25% of Gross) - DISABLED by default
    - ESIC Employee Deduction (0.75% of Gross) - DISABLED by default
    - Gratuity (4.81% of Basic) - DISABLED by default
    - Retention Bonus (fixed annual) - Optional
    - Professional Tax (₹200/month) - DISABLED by default
  - [x] Component master API: `GET/POST /api/ctc/component-master`
  - [x] Dynamic calculation with `calculate_ctc_breakdown_dynamic()`
  - [x] Deductions (PF Employee, ESIC, PT) subtract from gross in preview
  - [x] Preview shows In-Hand = Gross - Deductions
- [x] **Payroll Integration**
  - [x] Salary slip generation checks for active CTC structure
  - [x] If approved CTC exists, uses its component breakdown for earnings
  - [x] Falls back to global payroll_config if no CTC structure
- [x] **Backend APIs**
  - [x] `POST /api/ctc/calculate-preview` - Preview CTC breakdown
  - [x] `POST /api/ctc/design` - Submit CTC for approval
  - [x] `GET /api/ctc/pending-approvals` - Admin pending list
  - [x] `GET /api/ctc/stats` - Admin statistics
  - [x] `POST /api/ctc/{id}/approve` - Admin approve
  - [x] `POST /api/ctc/{id}/reject` - Admin reject
  - [x] `GET /api/ctc/employee/{id}` - Get employee CTC
  - [x] `GET /api/ctc/employee/{id}/history` - CTC change history
  - [x] `DELETE /api/ctc/{id}/cancel` - Cancel pending request
  - [x] `GET /api/ctc/component-master` - Get available components
  - [x] `POST /api/ctc/component-master` - Admin update component master
- [x] **Navigation Updates**
  - [x] "CTC Designer" link added to HR section in main ERP sidebar
  - [x] "CTC Designer" link added to HR Portal Operations section

## Test Accounts (Fresh Database)

| Portal | Role | Email | Password |
|--------|------|-------|----------|
| Main ERP | Admin | admin@dvbc.com | admin123 |
| Main ERP | Manager | manager@dvbc.com | manager123 |
| Main ERP | Project Manager | pm@dvbc.com | pm123 |
| Main ERP | Principal Consultant | principal@dvbc.com | consult123 |
| Main ERP | Consultant | consultant@dvbc.com | consult123 |
| HR Portal | HR Manager | hr.manager@dvbc.com | hr123 |
| HR Portal | HR Executive | hr.exec@dvbc.com | hr123 |
| Sales Portal | Account Manager | sales.manager@dvbc.com | sales123 |

## Permission Matrix (Updated)

| Feature | Admin | Manager | Project Manager | Principal Consultant | HR Manager | HR Executive | Sales |
|---------|-------|---------|-----------------|---------------------|------------|--------------|-------|
| Assign Consultants | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Unassign Consultants | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Change Consultants | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| View Team Workload | ✅ | ✅ | ✅ | ✅ | ✅ (read-only) | ❌ | ❌ |
| Create Kickoff Request | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Accept Kickoff Request | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

**Workflow Page Summary:**
- Total 7 workflows now available at `/workflow`
- Each workflow has interactive step-by-step diagram with Play Animation feature
- Module badges (Sales, HR, Consulting, Finance) indicate which department handles each step
- System Integrations section shows automated connections between modules

## Known Issues
- Email sending is MOCKED
- Some test data created with TEST_ prefixes
- Legacy attendance records don't have work_location field (only new records will have it)
- Some performance metrics are simulated (consultant utilization, client ratings, sales data)
- Console warnings about chart dimensions (-1 width/height) - cosmetic, doesn't affect rendering
- PWA install notification with branding not implemented
- Leads list view has incomplete columns
- `LockableCard` not applied to Sales Dashboard

### Session 12 (Feb 18, 2026) - Server.py Refactoring & CTC Approval Fix
- [x] **Backend Modularization (server.py refactoring - Phase 1)**
  - [x] Created `/app/backend/routers/deps.py` - Shared dependencies (database, sanitization, JWT config)
  - [x] Created `/app/backend/routers/models.py` - Shared Pydantic models (~500 lines)
  - [x] Created `/app/backend/routers/auth.py` - Authentication endpoints (login, register, Google auth, OTP, password reset)
  - [x] Created `/app/backend/routers/leads.py` - Lead management CRUD with scoring
  - [x] Created `/app/backend/routers/projects.py` - Project management, handover alerts
  - [x] Created `/app/backend/routers/meetings.py` - Meeting management, MOM, action items
  - [x] Created `/app/backend/routers/stats.py` - Dashboard statistics (admin, sales, HR, consulting)
  - [x] Created `/app/backend/routers/security.py` - Security audit logs endpoint
  - [x] Created `/app/backend/routers/users.py` - User management, roles, reporting managers
  - [x] Created `/app/backend/routers/kickoff.py` - Kickoff request workflow
  - [x] Updated `/app/backend/routers/__init__.py` - Export all routers
  - [x] Total new modular code: ~4,800 lines across 10 router files
  - [x] Original server.py (14,076 lines) still functional with new imports ready

- [x] **Backend Modularization (Phase 2)**
  - [x] Created `/app/backend/routers/ctc.py` - CTC structure design, calculation, approval workflow
  - [x] Created `/app/backend/routers/employees.py` - Employee CRUD, documents, org structure
  - [x] Created `/app/backend/routers/attendance.py` - Attendance recording, analytics
  - [x] Created `/app/backend/routers/expenses.py` - Expense management, receipts, approvals
  - [x] Created `/app/backend/routers/hr.py` - HR-specific endpoints, bank change approvals
  - [x] Created `/app/backend/MIGRATION_GUIDE.md` - Documentation for incremental migration
  - [x] Total new modular code: ~6,666 lines across 15 router files
  - [x] All new routers compile and import successfully
  - [x] Legacy server.py still functional (14,109 lines)
  - [x] All APIs tested and working

- [x] **Backend Modularization (Phase 3 - Complete Migration)**
  - [x] Enabled 8 routers in server.py: stats, security, kickoff, ctc, employees, attendance, expenses, hr
  - [x] Removed duplicate legacy code sections:
    - CTC STRUCTURE & APPROVAL section (~574 lines removed)
    - Kickoff Request Endpoints section (~505 lines removed)
    - Security Audit Logs section (~31 lines removed)
    - EMPLOYEES MODULE section (~1,239 lines removed)
    - EXPENSE SYSTEM section (~606 lines removed)
    - ATTENDANCE MODULE section (~379 lines removed)
  - [x] **Total lines removed: ~3,334 lines**
  - [x] **server.py reduced from 14,109 to 10,782 lines (24% reduction)**
  - [x] All APIs tested and working
  - [x] Frontend CTC approval modal verified working

- [x] **Real-Time Approval Notification Badges (NEW)**
  - [x] Created `/app/frontend/src/contexts/ApprovalContext.js` - Global context for approval counts
  - [x] Polls pending approvals every 10 seconds from multiple endpoints
  - [x] Shows red animated badge on "Approvals Center" nav item with total pending count
  - [x] Shows badges on HR nav items (CTC Designer, Attendance Approvals)
  - [x] Updated `Layout.js` to use ApprovalContext and display badges
  - [x] Updated `HRLayout.js` to use ApprovalContext and display badges
  - [x] Added `ApprovalProvider` wrapper in `App.js`
  - [x] Fixed `ApprovalsCenter.js` - CTC detail dialog now shows full salary component breakdown
  - [x] Issue: Backend returns `components` as object (dict), frontend expected array
  - [x] Added handling for object-based components with `Object.values()`
  - [x] Added CTC Summary section (Gross Monthly, Deductions, In-Hand approx)
  - [x] Fixed employee info display (employee code, previous CTC, submitted by name)
  - [x] Deductions shown in red with minus sign

### Backend Router Structure (Post-Refactoring)
```
/app/backend/routers/
├── __init__.py      # Package exports
├── deps.py          # Shared dependencies (db, auth, sanitization)
├── models.py        # Pydantic models (~500 lines)
├── auth.py          # Authentication & authorization
├── leads.py         # Lead management
├── projects.py      # Project management
├── meetings.py      # Meeting & MOM management
├── stats.py         # Dashboard statistics
├── security.py      # Security audit logs
├── users.py         # User management
├── kickoff.py       # Kickoff request workflow
├── ctc.py           # CTC structure & approvals
├── employees.py     # Employee management
├── attendance.py    # Attendance tracking
├── expenses.py      # Expense management
├── hr.py            # HR-specific endpoints
├── masters.py       # Admin masters (existing)
├── sow_masters.py   # SOW masters (existing)
└── enhanced_sow.py  # Enhanced SOW (existing)
```

## UI/UX Updates (Feb 17, 2026)
- [x] **Default Theme Changed to Light**
  - ThemeContext.js now defaults to 'light' instead of system preference
  - New users and fresh sessions will see light theme
- [x] **Mobile Responsive Layout**
  - Layout.js: Sidebar hidden on mobile, accessible via hamburger menu
  - Slide-out sidebar with backdrop overlay
  - Bottom navigation bar with Home, Attendance, Leaves, Profile icons
  - Touch-friendly larger tap targets (h-10 on mobile vs h-8 on desktop)
  - HRLayout.js: Same mobile improvements applied
  - Content area has bottom padding to avoid overlap with bottom nav


### Session 11 (Feb 17, 2026) - Comprehensive Mobile Responsiveness
- [x] **Sales Portal Mobile Layout (SalesLayout.js)**
  - [x] Added hamburger menu button for mobile (displays when viewport < 768px)
  - [x] Slide-out sidebar with backdrop overlay (w-72 width)
  - [x] Bottom navigation bar with 4 items: Home, Leads, Attendance, Profile
  - [x] Mobile header with logo and "Sales" branding
  - [x] Close button in sidebar for mobile
  - [x] Auto-close sidebar on route navigation
- [x] **Admin Dashboard Mobile Layout (AdminDashboard.js)**
  - [x] Converted 12-column bento grid to responsive: `grid-cols-2 md:grid-cols-6 lg:grid-cols-12`
  - [x] Revenue card spans full width on mobile (`col-span-2`)
  - [x] All stat cards properly sized for 2-column mobile view
  - [x] Charts render with smaller dimensions on mobile (height 100-120px vs 150-180px)
  - [x] Quick Actions buttons wrap properly on mobile
  - [x] Last Updated timestamp with smaller font on mobile
- [x] **Sales Dashboard Enhanced Mobile Layout (SalesDashboardEnhanced.js)**
  - [x] KPI scorecards changed to `grid-cols-2 md:grid-cols-3 lg:grid-cols-6`
  - [x] Sales Pipeline shows 4 stages on mobile with summary text below for overflow
  - [x] Charts row changed to `grid-cols-1 md:grid-cols-3`
  - [x] Month over Month performance uses `grid-cols-1 md:grid-cols-2`
  - [x] Team Leaderboard & Quick Actions responsive
  - [x] All text sizes adjusted with `text-xs md:text-sm` patterns
- [x] **HR Portal Dashboard Mobile Layout (HRPortalDashboard.js)**
  - [x] Quick Actions buttons now have consistent height across all breakpoints
  - [x] Fixed inconsistent button styling issue (h-16 md:h-20 applied uniformly)
  - [x] Text sizing consistent across all buttons

## Mobile-First Design Pattern (Established Feb 2026)
For future development, use these responsive patterns:
```css
/* Grid patterns */
grid-cols-1 md:grid-cols-2 lg:grid-cols-4   /* Cards/stats */
grid-cols-2 md:grid-cols-3 lg:grid-cols-6   /* KPI scorecards */
grid-cols-2 md:grid-cols-6 lg:grid-cols-12  /* Bento grids */

/* Text sizing */
text-xs md:text-sm    /* Small text */
text-sm md:text-base  /* Body text */
text-xl md:text-2xl   /* Numbers/stats */
text-base md:text-lg  /* Titles */

/* Spacing */
p-3 md:p-4 lg:p-6     /* Card padding */
gap-2 md:gap-4        /* Grid gaps */
px-3 md:px-6          /* Horizontal padding */

/* Layout components must include: */
- useState for isMobile detection (window.innerWidth < 768)
- Hamburger menu button on mobile
- Slide-out sidebar with backdrop overlay
- Bottom navigation bar (4 items max)
- pb-16 md:pb-0 on main content to avoid bottom nav overlap
```


### Session 11 (continued) - PWA, Bank Details Change, New Workflows
- [x] **PWA Install Prompt with Branding**
  - [x] Created `/public/manifest.json` with DVBC branding (name, icons, theme_color: #f97316)
  - [x] Created `/public/service-worker.js` with caching strategy
  - [x] Created `PWAInstallPrompt.js` component with branded UI
  - [x] Shows install prompt after 3 seconds with "Works offline", "Quick access", "Faster load times" benefits
  - [x] 24-hour dismissal cooldown stored in localStorage
  - [x] Updated `index.html` with manifest link and apple-mobile-web-app meta tags

- [x] **Bank Details Change Approval Workflow**
  - [x] Created `BankDetailsChangeRequest.js` page for employees
  - [x] Added routes: `/my-bank-details`, `/hr/my-bank-details`, `/sales/my-bank-details`
  - [x] Added navigation links in Layout.js, HRLayout.js, SalesLayout.js
  - [x] Backend APIs:
    - `GET /api/my/profile` - Get employee profile with bank details
    - `GET /api/my/bank-change-requests` - List user's requests
    - `POST /api/my/bank-change-request` - Submit new request with proof
    - `GET /api/hr/bank-change-requests` - List pending HR requests
    - `POST /api/hr/bank-change-request/{id}/approve|reject` - HR actions
    - `GET /api/admin/bank-change-requests` - List pending admin requests
    - `POST /api/admin/bank-change-request/{id}/approve|reject` - Admin actions
  - [x] Flow: Employee submits → pending_hr → HR approves → pending_admin → Admin approves → bank_details updated

- [x] **Medium-Priority ERP Workflows (WorkflowPage.js)**
  - [x] **Client Onboarding** (8 steps): Agreement Signed → Client Creation → SPOC Setup → Access Setup → Kickoff Meeting → Team Introduction → Document Handover → Onboarding Complete
  - [x] **SOW/Change Request** (8 steps): Change Identified → Impact Analysis → CR Draft → Pricing Update → Client Approval → Agreement Amendment → Team Update → Execute Change
  - [x] **Bank Details Change** (7 steps): Employee Request → HR Review → HR Approval → Admin Review → Admin Approval → System Update → Employee Notified

## Database Schema Updates (Session 11)
- **bank_change_requests**: `{employee_id, employee_name, employee_code, current_bank_details, new_bank_details, proof_document, proof_filename, reason, status, hr_approved_by, hr_approved_at, admin_approved_by, admin_approved_at, rejection_reason, created_at, updated_at}`
  - Status values: `pending_hr`, `pending_admin`, `approved`, `rejected`

### Session 13 (Feb 18, 2026) - Enhanced Role & Permission Management System
- [x] **Employee Levels System**
  - [x] 3 hierarchy levels: Executive (entry), Manager (mid), Leader (senior)
  - [x] Default permission sets per level (10 boolean permissions)
  - [x] Admin can customize level permissions via UI
  - [x] Level stored on employee record

- [x] **Role Creation/Assignment Approval Workflow**
  - [x] HR submits role creation request → Admin approval required
  - [x] HR submits role assignment request → Admin approval required  
  - [x] Admin can approve/reject with comments
  - [x] Notifications created for admins on submission and requester on resolution
  - [x] Duplicate request prevention

- [x] **Backend APIs (`/api/role-management/*`)**
  - `GET /levels` - List employee levels (executive, manager, leader)
  - `GET /level-permissions` - Get all level permission configs
  - `GET /level-permissions/{level}` - Get specific level permissions
  - `PUT /level-permissions` - Admin update level permissions
  - `POST /role-requests` - HR create role request
  - `GET /role-requests` - List role requests
  - `GET /role-requests/pending` - Admin pending requests
  - `POST /role-requests/{id}/approve` - Approve/reject request
  - `POST /assignment-requests` - HR create assignment request
  - `GET /stats` - Role management statistics

- [x] **Frontend Updates**
  - [x] `/role-management` page with stats cards and two tabs
  - [x] Pending Requests tab - approve/reject workflow
  - [x] Level Permissions tab - view/edit permissions per level
  - [x] Navigation added to Admin section (Role Management, Permission Config)
  - [x] Onboarding form updated with Employee Level dropdown

- [x] **Server.py Refactoring Continued**
  - [x] Enabled auth, leads, projects, meetings, users routers
  - [x] Added role_management_router
  - [x] Removed ~441 lines of duplicate legacy code
  - [x] Server.py reduced from 10,782 → 10,341 lines

### Database Schema Updates (Session 13)
- **employees**: Added `level` field (executive, manager, leader)
- **role_requests**: `{id, request_type, role_id, role_name, role_description, permissions, employee_id, employee_name, employee_code, current_role, current_level, new_role_id, new_role_name, level, reason, status, submitted_by, submitted_by_name, submitted_at, reviewed_by, reviewed_by_name, reviewed_at, review_comments}`
  - request_type: `create_role` or `assign_role`
  - status: `pending`, `approved`, `rejected`
- **level_permissions_config**: `{id, permissions: {executive: {...}, manager: {...}, leader: {...}}, updated_at, updated_by}`

### Test Coverage (Session 13)
- Backend: 24/24 tests passed (pytest)
- Frontend: All Role Management features verified
- Test file: `/app/backend/tests/test_role_management_levels.py`

### Server.py Final Cleanup (Feb 18, 2026)
- [x] **Safe Micro-Cleanup Completed**
  - Removed duplicate meetings endpoints (POST, GET, GET/:id, PATCH/:id/mom, POST/:id/action-items, PATCH/:id/action-items/:id, POST/:id/send-mom)
  - Meetings router now handles all meeting CRUD
  - Kept `/consulting-meetings/tracking` endpoint (unique to server.py)
  - Kept `/follow-up-tasks` endpoint (not in router)
  - Lines removed: ~385 (48 + 335)
  - server.py: 10,341 → 9,958 lines (now under 10K!)

- [x] **Migration Plan Created**
  - Created `/app/MIGRATION_PLAN.md` with full analysis
  - Documents safe vs risky endpoints
  - Lists consulting/handoff critical endpoints that MUST stay
  - Provides future migration steps

### Consulting/Handoff Impact Analysis
**NO IMPACT on critical flows:**
- ✅ Consultant assignment/unassignment
- ✅ Kickoff meeting workflow
- ✅ Project handoff process  
- ✅ Cross-team notifications
- ✅ Approval workflows
- ✅ SOW/Agreement management

All consulting-specific endpoints remain in server.py and are NOT duplicated in routers.

### Session 13 (continued) - Offer & Appointment Letter Workflow

#### Implemented Features:
- [x] **Letter Templates System**
  - Create/Edit templates with HTML content and placeholders
  - Version history tracking with modification details
  - Default template per type (offer_letter, appointment_letter)
  - Permissions: Admin + HR Manager can create/edit

- [x] **Offer Letter Workflow**
  - HR creates offer letter for verified candidates
  - Company letterhead with D&V branding
  - Pre-filled HR signature (text or image)
  - Generates unique acceptance token/link
  - Creates approval center entry
  - Notifies admins and HR managers

- [x] **Employee Acceptance Flow**
  - Public page at `/accept-offer/{token}`
  - Displays full offer on company letterhead
  - One-click acceptance with digital signature
  - Auto-generates Employee ID (EMP009+)
  - Stamps acceptance with employee name and timestamp

- [x] **Appointment Letter Workflow**
  - Available after offer acceptance
  - Requires employee to have assigned ID
  - Similar flow to offer letter

- [x] **Company Letterhead Component**
  - Recreated D&V Business Consulting letterhead
  - Header with logo and company info
  - Footer with registered office details
  - HR signature block
  - Acceptance stamp component

#### New API Endpoints (`/api/letters/*`):
- `POST /templates` - Create template
- `GET /templates` - List templates (filter by type)
- `GET /templates/{id}` - Get template with history
- `PUT /templates/{id}` - Update template (saves history)
- `DELETE /templates/{id}` - Soft delete template
- `POST /offer-letters` - Create and send offer letter
- `GET /offer-letters` - List offer letters
- `GET /offer-letters/{id}` - Get specific offer letter
- `POST /offer-letters/accept` - Public acceptance endpoint
- `POST /appointment-letters` - Create appointment letter
- `GET /appointment-letters` - List appointment letters
- `POST /appointment-letters/accept` - Accept appointment
- `GET /view/offer/{token}` - Public view offer
- `GET /view/appointment/{token}` - Public view appointment
- `GET /stats` - Letter management statistics

#### Database Collections:
- **letter_templates**: `{id, template_type, name, subject, body_content, is_default, is_active, version, history[], created_by, created_at, updated_at}`
- **offer_letters**: `{id, candidate_id, candidate_name, candidate_email, template_id, designation, department, joining_date, salary_details, hr_signature_*, status, acceptance_token, employee_id_assigned, accepted_at, acceptance_signature}`
- **appointment_letters**: `{id, employee_id, employee_code, employee_name, template_id, hr_signature_*, status, acceptance_token, accepted_at, acceptance_signature}`
- **approval_entries**: Stores letter send/acceptance events for Approval Center

#### Test Coverage:
- Backend: 22/22 tests passed
- Test file: `/app/backend/tests/test_letter_management.py`
- Test data: Candidate John Smith accepted offer → EMP009

#### Files Created:
- `/app/backend/routers/letters.py`
- `/app/frontend/src/pages/LetterManagement.js`
- `/app/frontend/src/pages/AcceptOfferPage.js`
- `/app/frontend/src/components/CompanyLetterhead.js`

### Session 14 (Feb 18, 2026) - Stats Router Refactoring Complete

#### Stats Endpoints Migration (COMPLETED)
Successfully migrated all stats endpoints from legacy server.py to `/app/backend/routers/stats.py`:

- [x] `/api/stats/dashboard` - Main dashboard statistics
  - Returns: `total_leads`, `new_leads`, `qualified_leads`, `closed_deals`, `active_projects`
  - Matches frontend Dashboard.js expected data format
  
- [x] `/api/stats/sales-dashboard` - Sales pipeline stats
  - Returns: `pipeline`, `clients`, `quotations`, `agreements`, `kickoffs`, `revenue`, `conversion_rate`
  
- [x] `/api/stats/sales-dashboard-enhanced` - Enhanced sales metrics
  - Returns: `pipeline`, `temperature`, `meetings`, `ratios`, `closures`, `deal_value`, `targets`, `mom_performance`, `lead_sources`, `leaderboard`
  - Supports `view_mode` parameter (own/team/all)
  
- [x] `/api/stats/hr-dashboard` - HR employee/attendance/payroll stats
  - Returns: `employees`, `attendance`, `leaves`, `expenses`, `payroll`
  - Role-restricted: admin, hr_manager, hr_executive, manager only
  
- [x] `/api/stats/consulting-dashboard` - Consulting delivery stats
  - Returns: `projects`, `meetings`, `efficiency_score`, `incoming_kickoffs`, `consultant_workload`

#### Server.py Refactoring Progress:
- **Original Size:** ~14,000+ lines
- **Current Size:** 9,488 lines
- **Total Reduction:** ~4,500+ lines (32% reduction)

#### Legacy Code Removed:
- `/stats/dashboard` endpoint (lines 754-777)
- `/stats/sales-dashboard` endpoint (lines 782-852)
- `/stats/sales-dashboard-enhanced` endpoint (lines 870-1088)
- Orphan `get_consulting_dashboard_stats` function (lines 1372-1450)
- `/stats/hr-dashboard` endpoint (lines 1453-1514)
- Helper functions: `get_team_member_ids`, `can_see_all_data`

#### Test Coverage:
- Backend: 21/21 tests passed (100%)
- Frontend: All dashboard types verified (Admin, Sales, HR)
- Test file: `/app/backend/tests/test_stats_router.py`

#### Files Updated:
- `/app/backend/routers/stats.py` - Complete rewrite matching frontend expectations
- `/app/backend/server.py` - Reduced from 9,960 to 9,488 lines
- `/app/REFACTOR_MIGRATION_PLAN.md` - Created migration tracking document

### Session 15 (Feb 18, 2026) - SOW Scope Builder for Admin Masters

#### Problem Solved:
- User was unable to add custom scopes in SOW builder because no categories existed
- Custom Scope dialog showed empty category dropdown

#### Solution Implemented:
- Added **SOW Scope Builder** tab to Admin Masters page (`/admin-masters`)
- Categories Panel: Create, Edit, Delete categories with code, name, description
- Scopes Panel: Create, Edit, Delete scope templates within categories
- Category filtering: Click a category to filter scopes
- "Seed SOW Defaults" button to populate default categories and scopes
- Inline editing for both categories and scopes

#### Features:
- [x] Categories CRUD with validation
- [x] Scope Templates CRUD with category association
- [x] Seed defaults (8 categories, 41 scopes)
- [x] Category-based filtering
- [x] Edit/Delete functionality with confirmation
- [x] Status tracking (Active/Inactive)
- [x] Type tracking (Default/Custom)

#### Default Categories Created:
1. Sales (6 scopes)
2. HR (6 scopes)
3. Operations (6 scopes)
4. Training (6 scopes)
5. Analytics (5 scopes)
6. Digital Marketing (4 scopes)
7. Finance (5 scopes)
8. Strategy (4 scopes)

#### Files Updated:
- `/app/frontend/src/pages/AdminMasters.js` - Added SOW Scope Builder tab with full CRUD functionality

### Session 16 (Feb 18, 2026) - ERP Bug Fixes Batch 2

#### Issues Fixed (from ERP Bugs.docx):

1. **Leads Search & Filtering (FIXED)**
   - Added search box - filters by name, company, email, phone
   - Added timeline filter - Today, This Week, This Month, This Quarter, All Time
   - Status filter already existed, now works with search
   - Shows filtered count: "(X of Y leads)"

2. **Password Visibility Toggle (FIXED)**
   - Added Eye/EyeOff icon on Login page password field
   - Click to toggle between hidden/visible password

3. **Duplicate Mobile Number Check (FIXED)**
   - Backend validates phone numbers on employee creation
   - Returns 400 error "Employee with this phone number already exists"
   - Normalizes phone number (removes spaces, dashes)

4. **Mobile Number Limit (FIXED)**
   - Onboarding form limits phone input to 10 digits
   - Auto-strips non-numeric characters
   - Shows +91 country code prefix

5. **Receipt/Bill Upload for Expenses (FIXED)**
   - Added "Attach Receipt/Bill (optional)" section in expense form
   - Upload Image button with preview
   - Supports images and PDFs (up to 5MB)

6. **IFSC Verification (FIXED)**
   - Added "Verify" button next to IFSC code input
   - Calls Razorpay IFSC API (https://ifsc.razorpay.com/)
   - Auto-fills Bank Name and Branch Name on verification
   - Shows green "Verified" status on success

#### Test Results:
- Backend: 100% (10/10 tests passed)
- Frontend: 100% - All bug fixes verified
- Test file: `/app/backend/tests/test_bug_fixes_erp.py`

#### Files Modified:
- `/app/frontend/src/pages/Leads.js` - Search, timeline filter, useMemo
- `/app/frontend/src/pages/Login.js` - Password visibility toggle
- `/app/frontend/src/pages/HROnboarding.js` - Phone validation
- `/app/frontend/src/pages/Expenses.js` - Receipt upload
- `/app/frontend/src/pages/BankDetailsChangeRequest.js` - IFSC verification
- `/app/backend/routers/employees.py` - Duplicate phone check

#### Still Pending from ERP Bugs.docx:
- Selfie Capture Missing
- CSV Upload Missing  
- Multi-select for Role, Tenure Type, Meeting Type
- Old credentials after new link issue

### Session 17 (Feb 18, 2026) - ERP Bug Fixes Batch 3

#### Issues Fixed (from ERP Bugs.docx):

1. **CSV Upload for Leads (FIXED)**
   - Added "Import CSV" button on Leads page
   - CSV Upload dialog with:
     - Template download button
     - Drag & drop file upload area
     - Direct paste CSV data option
     - Preview table showing parsed data
     - Bulk import functionality
   - Supports columns: first_name, last_name, company, job_title, email, phone, source, notes

2. **Selfie Capture (VERIFIED WORKING)**
   - Selfie capture exists in EmployeeMobileApp.js (/mobile route)
   - Quick Attendance modal has camera capture area
   - startCamera() and captureSelfie() functions implemented
   - Camera permissions required for browser

3. **Old Credentials After New Link (VERIFIED WORKING)**
   - Portal access grants temp password: "Welcome@{employee_id}"
   - Existing user accounts are linked, not recreated
   - Password remains same unless explicitly changed
   - Login with temp password verified working

#### Test Results:
- Backend: 100% (11/11 tests passed)
- Frontend: 100% - All bug fix features verified
- Test file: `/app/backend/tests/test_csv_portal_selfie.py`

#### Files Modified:
- `/app/frontend/src/pages/Leads.js` - Added CSV upload dialog, parseCSV, handleBulkUpload

#### Remaining Issues from ERP Bugs.docx:
- Multi-select for Role, Tenure Type, Meeting Type (needs clarification)
