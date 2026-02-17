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
- `server.py` is monolithic and needs refactoring

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
