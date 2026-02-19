# DVBC Business Management ERP - Product Requirements Document

## Last Updated: February 2025

## Permission System: SIMPLIFIED (Feb 2025) - ✅ VERIFIED WORKING (Feb 19, 2026)
**Only 2 things matter for permissions:**
1. **Department** → What pages you can see
2. **Has Reportees** → Auto-detected (if someone reports to you → team management)

**Additional controls:**
- `is_view_only` → Can view but not create/edit
- `Special Permissions` → Admin/HR only for cross-department access

**Removed:**
- ~~Role~~ → No longer used for permissions (removed from onboarding)
- ~~Level~~ → No longer used for permissions (removed from onboarding)

**Onboarding Changes (Feb 2025):**
- Employee ID auto-generates with EMP prefix (EMP001, EMP002, etc.)
- All Step 1 and Step 2 fields are mandatory
- Added "View Only Access" checkbox
- Reporting Manager shows "(Determines team access)" helper text

**API Response (/api/my-access) - NEW FIELDS:**
- `has_reportees: boolean` - Auto-detected from org chart
- `reportee_count: integer` - Number of direct reports
- `is_view_only: boolean` - View-only flag
- `can_edit: boolean` - Inverse of is_view_only
- `can_manage_team: boolean` - Equals has_reportees

**Testing Status (Feb 19, 2026):**
- Backend: 100% (12/12 tests passed)
- Frontend: 100% (All features verified via Playwright)
- Test report: /app/test_reports/iteration_58.json

## DBAC System Status: ✅ VERIFIED WORKING (Feb 2025)
- All login flows tested and working
- Department-based navigation filtering working correctly
- Admin Masters Departments tab functional
- 100% backend tests passing (14/14)
- 100% frontend tests passing

## Recent Updates (Feb 19, 2025)
1. **Multi-Department Employee Onboarding** - HR can now assign multiple departments to an employee during onboarding
2. **Proforma Invoice History View** - Negotiation history grouped by lead for tracking revisions
3. **Payment Reminder & Transaction Recording** - Send reminders and record payments with transaction IDs
4. **Department-based Permission Refactoring** - Started migration from role-based to department-based permission checks
5. **E2E Sales Flow Tested** - Complete flow from onboarding to kickoff verified with test employee "Dharmesh Parikh"

## E2E Test Employee (Feb 19, 2025)
- **Name:** Dharmesh Parikh
- **Employee ID:** EMP009
- **Email:** dharmesh.parikh@dvconsulting.co.in
- **Password:** Welcome@EMP009
- **Department:** Sales
- **Designation:** Sales Manager
- **Level:** Manager
- **Sales Activity:** 1 Lead (HOT), 1 Pricing Plan, 1 SOW, 1 Quotation, 1 Agreement

## Original Problem Statement
Build a business management application for a consulting firm with complete HR, Sales, and Consulting workflows, including:
- Dedicated portals for Sales and HR teams
- **Department-based access control** (Department determines page access, not role)
- Multi-department support for cross-functional employees
- **Employee-level special permissions** for temporary cross-functional roles
- End-to-end sales flow: Lead → Meetings → MOM → Hot → Pricing Plan → SOW → Proforma → Agreement → Kickoff → Project
- HR module with employee onboarding, attendance, leave, payroll management
- Consulting team workload visibility for HR (operational data only)

## Access Control Architecture (Feb 2025)

### 3-Tier Permission System
```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: DEPARTMENT → Which PAGES can I see?                    │
│  (Sales, HR, Consulting, Finance, Admin, Marketing, etc.)       │
├─────────────────────────────────────────────────────────────────┤
│  TIER 2: LEVEL → How MUCH can I do within those pages?          │
│  (Executive: view/create, Manager: +approve, Leader: +config)   │
├─────────────────────────────────────────────────────────────────┤
│  TIER 3: SPECIAL PERMISSIONS → Individual exceptions            │
│  (Additional departments, approval rights, temporary roles)     │
└─────────────────────────────────────────────────────────────────┘
```

### Department-Based Access
**Primary Change**: Page access is now determined by `department` field, not `role`.

| Department | Pages/Modules Accessible |
|------------|--------------------------|
| **Sales** | Leads, Meetings, Pricing, SOW, Quotations, Proforma, Agreements, Kickoff |
| **HR** | Employees, Attendance, Leaves, Payroll, CTC, Onboarding, Staffing |
| **Consulting** | Projects, Tasks, Timesheets, SOW Execution, Payments |
| **Finance** | Payments, Expenses, Financial Reports |
| **Admin** | Full access to all pages (*) |
| **Marketing** | (Configurable via Admin Masters) |

### Multi-Department Support
- Employees can have **multiple departments** for cross-functional roles
- One **primary department** (determines default view)
- Admin/HR can grant **additional department access**
- Custom page exceptions (grant/restrict specific pages)

### Employee-Level Special Permissions (NEW)
For cases like: "Sales employee temporarily working as Marketing Manager"

| Permission Type | Description | Use Case |
|-----------------|-------------|----------|
| **Additional Departments** | Grant access to other department pages | Cross-functional projects |
| **Approval Rights** | Allow approving leaves/expenses for other depts | Acting manager |
| **Temporary Role** | Override role with expiry date | Acting position |
| **Restricted Pages** | Block specific pages | Compliance/security |

### Employee Data Fields
```javascript
{
  // Base Access
  department: "Sales",           // Legacy field
  departments: ["Sales"],        // Base department array
  primary_department: "Sales",   // Primary department
  
  // Permission Level
  level: "manager",              // executive/manager/leader
  role: "account_manager",       // Job title (legacy)
  
  // Special Permissions
  additional_departments: ["Marketing"],  // Extra dept access
  additional_pages: [],                   // Extra page access
  restricted_pages: [],                   // Blocked pages
  temporary_role: "hr_manager",           // Temp role override
  temporary_role_expiry: "2025-03-01",    // When temp role ends
  can_approve_for_departments: ["Sales"], // Approval rights
  special_permissions: [],                // Audit trail
  permission_notes: "Acting Marketing Manager during Q1"
}
```

### Department Access Manager UI
- Location: `/department-access` (Admin) and `/hr/department-access` (HR Manager)
- Features:
  - View employees by department
  - Grant/remove department access
  - Set primary department
  - Bulk edit department access
  - Stats: employees per department, multi-department count

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

### Session 9 (Feb 18, 2026)
- [x] **Payment Verification Step (Sales-to-Consulting Handoff)**
  - [x] New `/sales-funnel/payment-verification` page for verifying first installment payments
  - [x] Payment verification required before kickoff request creation
  - [x] 3-step flow: Agreement Signed → Verify Payment → Create Kickoff Request
  - [x] Backend `/api/payments/*` endpoints for payment CRUD
  - [x] Automatic SOW handover to Consulting when payment is verified
  - [x] SOW-to-Project linking via `agreement_id`
  - [x] "Verify Payment" button added to Agreements page
  - [x] Payment eligibility check in Kickoff Requests page
  - [x] Clear error messages when payment not verified
  - [x] **Expected Amount locked** - Fetched from pricing plan first installment (read-only)
- [x] **Kickoff Request Form Improvements**
  - [x] **Project Type locked** - Fetched from pricing plan (read-only)
  - [x] **Meeting Frequency locked** - Fetched from pricing plan team deployment (read-only)
  - [x] **Project Tenure locked** - Fetched from pricing plan duration (read-only)
  - [x] Fields show "(from pricing plan)" label to indicate source
- [x] **Projects Page - No Direct Creation**
  - [x] Removed "Create Project" button from Projects page
  - [x] Projects can ONLY be created via Kickoff Request handover from Sales team
  - [x] Empty state message updated to explain this workflow
- [x] **Assign Consultant Page Verified Working**
  - [x] `/consulting/assign-team/:projectId` page confirmed working
  - [x] Shows project details, duration, meetings
  - [x] Add Consultant functionality available
- [x] **Consultant Assignment Notifications**
  - [x] Notification sent to assigned consultant when assigned to project
  - [x] Notification sent to reporting manager when their reportee is assigned
- [x] **Project Payments Page**
  - [x] New `/payments` page showing all project payments
  - [x] Summary cards: Total Received, Total Value, Active Projects, Upcoming Amount
  - [x] My Projects tab with payment status per project
  - [x] Upcoming Payments tab for Admin/PM/Principal Consultant
  - [x] Navigation link added under Consulting and Admin sections
- [x] **Project Payment Details Page**
  - [x] `/projects/:projectId/payments` detailed payment view
  - [x] First Advance Payment status with transaction details
  - [x] Payment Schedule tab (from pricing plan)
  - [x] Consultant Breakdown tab with assigned consultants
  - [x] Inherited SOW tab (view-only for consultants, editable for PM/Admin)
  - [x] SOW History tab for tracking changes (PM/Admin only)
- [x] **Backend APIs for Project Payments**
  - [x] `GET /api/project-payments/project/{project_id}` - Full payment details
  - [x] `GET /api/project-payments/my-payments` - User's projects payments
  - [x] `GET /api/project-payments/upcoming` - Upcoming payment schedule
- [x] **SOW History Tracking**
  - [x] `GET /api/enhanced-sow/{sow_id}/history` - Complete SOW change history
  - [x] `GET /api/enhanced-sow/project/{project_id}/sow` - Inherited SOW for project
  - [x] Access control: View-only for consultants, Edit for PM/Admin
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
- [ ] Admin approval workflow for employee record edits
- [ ] Download button for documents uploaded during onboarding
- [ ] Frontend permission enforcement (dynamic UI based on roles)
- [ ] Complete meeting management logic for sales flow
- [ ] Lead status enforcement (must be "Hot" for pricing)

### P2 - Medium Priority
- [ ] Business Flow Diagram (HR → Sales → Consulting visualization)
- [ ] Apply LockableCard to Sales Dashboard
- [ ] Rich drill-down views for Admin Dashboard

### P3 - Low Priority / Tech Debt
- [ ] Refactor `server.py` into separate route files (ongoing - partial refactor done)
- [ ] Fix incomplete columns in Leads list view
- [ ] Real SMTP integration for emails
- [ ] Refactor HROnboarding.js into smaller step-specific sub-components

### Future
- [ ] Finance Module & Project P&L Dashboards
- [ ] Consulting Phase 3 (Gantt charts, roadmaps)
- [ ] Skill matrix and capacity planning
- [ ] Training/certification tracking

### Session 10 (Feb 19, 2026) - Document Center (Unified Document Management)
- [x] **Unified Document Center** (Merged Letter Management + Document Builder)
  - [x] Created single `/document-center` page replacing both `/letter-management` and `/document-builder`
  - [x] All documents now linked by **employee_id** (not candidate_id)
  - [x] Employee selection pulls from onboarding data (department, reporting manager, designation, etc.)
  - [x] 3 Main Tabs: Generate, History, Templates
  - [x] Stats dashboard showing document counts by type
- [x] **Generate Tab Features:**
  - [x] 4 document types: Offer, Appointment, Confirmation, Experience Letter
  - [x] Employee selection dropdown with employee_id + department badges
  - [x] Auto-fills data from employee record (department, designation, reporting manager, joining date)
  - [x] Custom values override (CTC, Location, Notice Period, etc.)
  - [x] Live preview with D&V Business Consulting letterhead
  - [x] Print and Download functionality
- [x] **History Tab Features:**
  - [x] Complete audit trail of all generated documents
  - [x] Search by employee name or employee_id
  - [x] Filter by document type
  - [x] View, Download, Send Email actions for each document
  - [x] Status tracking (generated, sent)
- [x] **Templates Tab Features:**
  - [x] Default templates for all 4 document types
  - [x] Create custom templates with placeholders
  - [x] Backend storage for templates (`document_templates` collection)
  - [x] "Use Template" button to apply template
- [x] **Backend APIs Added:**
  - [x] `POST/GET/PUT/DELETE /api/document-templates` - Template CRUD
  - [x] `POST /api/document-history/{id}/send-email` - Email document to employee
- [x] **Navigation Updates:**
  - [x] Removed separate "Letter Management" and "Document Builder" links
  - [x] Single "Document Center" link in HR section
  - [x] Backward compatible routes (`/letter-management`, `/document-builder` redirect to `/document-center`)
- [x] **Login Enhancement:**
  - [x] Login now accepts both Employee ID and Email
  - [x] Smart detection based on @ character

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


### Session 18 (Feb 18, 2026) - Level-Based Permission System Complete

#### Features Implemented:

1. **Level-Based Permission System (COMPLETED)**
   - [x] Fixed `PermissionContext.js` - corrected API endpoint from `/api/roles/my-permissions` to `/api/role-management/my-permissions`
   - [x] Fixed `PermissionContext.js` - changed `isAuthenticated` to `user` check (AuthContext doesn't export isAuthenticated)
   - [x] Added `PermissionProvider` wrapper in `App.js` around the application
   - [x] Integrated `usePermissions()` hook in `Layout.js` for dynamic navigation visibility
   - [x] HR items now filtered based on permissions (requiresTeamView, requiresApproval, requiresReports)

2. **Left Panel Navigation (FIXED)**
   - [x] Sidebar scrolling works correctly (overflow-y-auto)
   - [x] Navigation links work without blank pages
   - [x] Section expand/collapse functionality working
   - [x] Mobile responsive design intact

#### Permission System Logic:
```javascript
// Visibility rules in Layout.js
const showHR = HR_ROLES.includes(role) || canManageTeam();
const showSales = SALES_ROLES_NAV.includes(role);
const showAdmin = ADMIN_ROLES.includes(role) || isLeader();

// HR items filtered by:
// - requiresTeamView: needs canViewTeamData() permission
// - requiresApproval: needs canApproveRequests() permission  
// - requiresReports: needs canViewReports() permission
```

#### Files Modified:
- `/app/frontend/src/contexts/PermissionContext.js` - Fixed API endpoint and user check
- `/app/frontend/src/App.js` - Added PermissionProvider wrapper
- `/app/frontend/src/components/Layout.js` - Integrated usePermissions() hook

#### Test Results:
- Backend: 100% (24/24 tests passed)
- Frontend: 100% - All navigation and permission tests passed
- Test file: `/app/test_reports/iteration_51.json`

#### Permission Behavior by Role:
| Role | My Workspace | HR | Sales | Admin |
|------|-------------|-----|-------|-------|

### Permission Dashboard Feature (Feb 18, 2026)

#### New Page: `/permission-dashboard`
Admin-only dashboard for managing employee permission levels across the organization.

**Features:**
1. **Stats Overview Cards**
   - Count of Executives, Managers, Leaders
   - Count of employees without assigned level

2. **Level Permission Matrix**
   - Visual grid showing all 10 permissions across 3 levels
   - Edit button to customize permissions for each level
   - Inline editing with Save/Cancel

3. **Employee Permission Levels**
   - Searchable list of all employees
   - Filter by level (All/Executive/Manager/Leader)
   - Each employee row expandable to:
     - Change level with one click (Executive/Manager/Leader buttons)
     - View current permissions based on level

**Files Created:**
- `/app/frontend/src/pages/PermissionDashboard.js` - New dashboard page

**Files Modified:**
- `/app/frontend/src/App.js` - Added import and route
- `/app/frontend/src/components/Layout.js` - Added nav link in Admin section

**API Endpoints Used:**
- `GET /api/role-management/stats` - Level statistics
- `GET /api/role-management/level-permissions` - Permission matrix
- `PATCH /api/employees/{id}` - Update employee level
- `PUT /api/role-management/level-permissions` - Update level permissions

### Withdraw Applied Leaves Feature (Feb 18, 2026)

#### Feature: `/my-leaves` - Withdraw Pending Leave Requests

**Backend Changes:**
- Added `POST /api/leave-requests/{leave_id}/withdraw` endpoint
- Only the requester can withdraw their own leave requests
- Only "pending" status leaves can be withdrawn
- Updates both `leave_requests` and `approval_requests` collections
- Sends notification to managers about withdrawal

**Frontend Changes:**
- Added "Action" column to leave requests table
- "Withdraw" button appears only for pending requests
- Confirmation dialog before withdrawal
- Loading state during withdrawal
- New "withdrawn" status style (grey badge)

**Files Modified:**
- `/app/backend/server.py` - Added withdraw endpoint
- `/app/frontend/src/pages/MyLeaves.js` - Added withdraw UI

**Test Results:**
- API tested: Create leave → Withdraw → Verify status changed to "withdrawn"
- Error handling: Cannot withdraw already withdrawn/approved/rejected requests

### Bug Fixes & Features - Session 19 (Feb 18, 2026)

Based on user-provided documents: `Bugs 3.docx`, `ERP Bugs 2.docx`, `HR PORTAL 2.0.docx`

#### 1. Enhanced Staffing Requests System (NEW)
**Endpoint:** `POST/GET /api/staffing-requests`

**Fields included:**
- Requester info (name, employee_id, email, reporting_manager)
- Project name & Purpose/Justification
- Budget range
- Timeline/Start date
- Location
- Work mode (office/client_site/remote)
- Skills required (array)
- Experience years
- Headcount
- Priority (low/normal/high/urgent)
- Status (pending_approval/approved/rejected/fulfilled)

**Admin Approval Flow:**
- `POST /api/staffing-requests/{id}/approve` - Admin only
- `POST /api/staffing-requests/{id}/reject` - Admin only with reason

**Files Modified:**
- `/app/backend/server.py` - Added staffing request endpoints
- `/app/frontend/src/pages/HRStaffingRequests.js` - Complete rewrite with form

#### 2. Half-Day Leave Option (NEW)
- Added `is_half_day` checkbox in Apply Leave dialog
- Added `half_day_type` dropdown (First Half/Second Half)
- Backend calculates days as 0.5 for half-day leaves
- Displayed in leave request list

**Files Modified:**
- `/app/backend/server.py` - Updated LeaveRequestCreate model
- `/app/frontend/src/pages/MyLeaves.js` - Added half-day UI

#### 3. Removed Duplicate Buttons
- ❌ Removed "Apply Leave" from LeaveManagement.js (HR page)
  - Employees should use My Leaves page instead

**Files Modified:**
- `/app/frontend/src/pages/LeaveManagement.js` - Removed dialog and form

#### Bug Fixes Status from Documents:

| Bug/Feature | Status | Notes |
|-------------|--------|-------|
| Staffing request with proper fields | ✅ DONE | Budget, timeline, location, etc. |
| Half-day leave option | ✅ DONE | First/Second half selection |

#### 4. Half-Day Leave Linked to Payroll (COMPLETE)
**Backend Changes:**
- Payroll now auto-calculates approved leaves for the month
- Half-day leaves tracked separately (`half_day_leaves` field)
- If no manual override, uses auto-calculated leave counts
- Salary slip includes `half_day_leaves` field

**Files Modified:**
- `/app/backend/server.py` - Updated salary slip generation

#### 5. Employee ID Linking System (COMPLETE)
**New API Endpoints:**

1. `GET /api/employees/stats/summary`
   - Total, Active, Terminated counts
   - **NEW**: With/Without Portal Access counts
   - By department, role, and level

2. `GET /api/employees/lookup/by-code/{emp_code}`
   - Lookup employee by employee code (e.g., EMP001)

3. `GET /api/employees/{id}/timeline`
   - Complete employee journey from hiring to present
   - Events: hired, access_granted, offer_letter, leave_request, expense, project_assignment, salary_slip, terminated

4. `GET /api/employees/{id}/linked-records`
   - Count of all records linked to employee:
   - attendance, leave_requests, expenses, salary_slips, documents, project_assignments, offer_letters, approval_requests, notifications, staffing_requests

**New Frontend Page: Employee Scorecard** (`/employee-scorecard`)
- Stats: Total, Active, With Access, Without Access, Terminated
- By Level distribution
- Employee Directory table with search
- Click employee to view:
  - Complete journey timeline with icons
  - Linked records summary

**Files Created:**
- `/app/frontend/src/pages/EmployeeScorecard.js`

**Files Modified:**
- `/app/backend/routers/employees.py` - Added timeline and linked-records endpoints
- `/app/frontend/src/App.js` - Added route
- `/app/frontend/src/components/Layout.js` - Added nav link

#### 6. Bug Fixes (Feb 18, 2026)

**Lead Status Change - FIXED**
- Added PATCH `/api/leads/{lead_id}` endpoint
- Status dropdown in both Card and List views
- Status change history tracked

**Timesheets Page - CREATED**
- New page: `/timesheets`
- Week-by-week timesheet entry
- Hours dropdown (0-10 in 0.5 increments)
- Daily totals and project totals
- Save Draft / Submit for Approval
- Backend endpoints for CRUD operations

**Files Created:**
- `/app/frontend/src/pages/Timesheets.js`

**Files Modified:**
- `/app/backend/server.py` - Added timesheet + lead PATCH endpoints
- `/app/frontend/src/pages/Leads.js` - Added status dropdown
- `/app/frontend/src/App.js` - Added Timesheets route

---

### Consultant Lifecycle Flow Analysis

| Step | Feature | Status | Notes |
|------|---------|--------|-------|
| 1 | HR Onboarding | ✅ DONE | Employee creation with all fields |
| 2 | Portal Access | ✅ DONE | Create user account, link to employee |
| 3 | Project Assignment | ✅ DONE | AssignTeam.js, backend endpoints |
| 4 | Access Assigned Projects | ✅ DONE | /consultant/my-projects |
| 5 | View SOW | ✅ DONE | ConsultingSOWList.js |
| 6 | Task Creation | ✅ DONE | ConsultingProjectTasks.js |
| 7 | Task linked to SOW | ✅ DONE | Tasks have sow_id |
| 8 | Mark Task Status | ✅ DONE | Task status updates |
| 9 | Timesheet Entry | ✅ DONE | New Timesheets page |
| 10 | Performance Review | 🟡 PARTIAL | Performance dashboard exists |
| 11 | Termination | 🟡 PARTIAL | Employee status can be updated |

**Gaps Identified:**
- Performance review not fully integrated with termination flow
- No explicit "Terminate Employee" button with workflow




| Remove duplicate Apply Leave button | ✅ DONE | From Leave Management |
| SOW scope checkbox (not dropdown) | 🔶 PENDING | Need to implement |
| Lead status change | 🔶 PENDING | Upper panel issue |
| Blank pages (Timesheets, Assign Team) | 🔶 PENDING | Need investigation |
| Proforma Invoice listing | 🔶 PENDING | Against prospects |
| Employee scorecards | 🔶 PENDING | Total, with/without access |


- UI verified: Withdraw button only shows for pending requests




| Admin | ✅ | ✅ | ✅ | ✅ |
| HR Manager | ✅ | ✅ | ❌ | ✅ |
| HR Executive | ✅ | ✅ | ❌ | ❌ |
| Sales Manager | ✅ | ❌ | ✅ | ❌ |
| Consultant | ✅ | ❌ | ❌ | ❌ |


### Session 13 (Feb 18, 2026) - Role-Based Payment Visibility & UI Improvements

#### Role-Based Payment Visibility (COMPLETED)

Implemented comprehensive role-based visibility for the Project Payments module:

**Backend Changes (`/app/backend/routers/project_payments.py`):**
- Modified `get_project_payments()` endpoint:
  - Added `can_view_amounts` flag (True for Admin/Principal Consultant only)
  - Added `is_consultant_view` flag for UI customization
  - Amounts hidden for Consultant and Reporting Manager roles
  - First payment details hidden for Consultant view
  - Schedule skips received payments for Consultant
- Modified `get_my_payments()` endpoint:
  - Added consultant names to project cards
  - Total value and payment amounts hidden for non-admin roles
  - Returns `can_view_amounts` flag

**Frontend Changes:**
- `ProjectPayments.js`:
  - Summary cards now role-aware (no amount cards for consultants)
  - Description text changes based on role
  - First Payment shows status only (not amount) for consultants
  - Consultant names displayed in project cards
  - "Upcoming Payments" tab hidden for non-admin roles
- `ProjectPaymentDetails.js`:
  - Removed "Inherited SOW" tab (per user request)
  - Total Project Value hidden for consultants
  - First Advance Payment card hidden for consultants
  - Payment Schedule table hides amount columns for consultants
  - "Amounts hidden" indicator shown for restricted views
  - Title changes to "Upcoming Payment Dates" for consultant view

**Visibility Matrix:**

| Feature | Admin | Principal Consultant | Manager | Consultant |
|---------|-------|---------------------|---------|------------|
| Total Project Value | ✅ | ✅ | ❌ | ❌ |
| First Payment Amount | ✅ | ✅ | ❌ | ❌ |
| Payment Schedule Amounts | ✅ | ✅ | ❌ | ❌ |
| Consultant Names | ✅ | ✅ | ✅ | ✅ |
| First Payment Received Status | ✅ | ✅ | ✅ | ✅ |
| Upcoming Payment Dates | ✅ | ✅ | ✅ | ✅ |
| Inherited SOW Tab | ❌ | ❌ | ❌ | ❌ |

**Test Results:** All 5 feature tests passed (iteration_53.json)
- Admin sees full amounts and first payment details
- Consultant sees dates only, no amounts, no first payment card
- Inherited SOW tab removed from all views
- Consultant names visible in project cards

**Files Modified:**
- `/app/backend/routers/project_payments.py`
- `/app/frontend/src/pages/ProjectPayments.js`
- `/app/frontend/src/pages/ProjectPaymentDetails.js`

**Test Credentials:**
- Admin: admin@dvbc.com / admin123
- Consultant: consultant@dvbc.com / consultant123


### Session 14 (Feb 18, 2026) - Payment Reminders, Record Payments, and Bug Fixes

#### Payment Reminder System (COMPLETED)

**Backend (`/app/backend/routers/project_payments.py`):**
- `POST /api/project-payments/send-reminder` - Send payment reminder to client
  - Only allowed for consulting team roles
  - Only enabled within 7 days of due date
  - Creates reminder record in `payment_reminders` collection
  - Creates notifications for Finance, Sales, Admin, Reporting Manager, HR
  - Email sending is MOCKED (records to DB only)
  
- `POST /api/project-payments/record-payment` - Record payment with transaction ID
  - Only allowed for consulting team
  - Validates project_id and installment_number
  - Creates record in `installment_payments` collection
  - Notifies Finance, Sales, Admin, Reporting Manager, HR for incentive calculation
  
- `GET /api/project-payments/check-reminder-eligibility/{project_id}/{installment_number}`
  - Returns whether reminder can be sent
  - Returns days until due date

**Frontend (`/app/frontend/src/pages/ProjectPaymentDetails.js`):**
- Added "Actions" column to Payment Schedule table
- "Remind" button - greyed out until within 7 days, green when active
- "Record" button - opens dialog to enter transaction ID
- Hidden for already-received payments
- Available to all consulting team members (including consultants)

#### UI Fixes (COMPLETED)

- Removed "Amounts hidden" indicator from Payment Schedule header
- Consultant view now shows "Upcoming Payment Dates" without the indicator
- Clean UI with only relevant data shown

#### P0 - Project Status Auto-Active (COMPLETED)

**Modified `/app/backend/routers/kickoff.py`:**
- When kickoff request is accepted, project is automatically created with `status="active"`
- Previously defaulted to no explicit status

#### P2 - Reset Temp Password (COMPLETED)

**Added `/app/backend/routers/employees.py`:**
- `POST /api/employees/{id}/reset-temp-password`
  - Only Admin/HR Manager can call
  - Resets password to `Welcome@{employee_id}`
  - Re-activates user if deactivated
  - Useful for users who forgot password or HR needs to resend credentials

#### Proforma Invoice History (EXISTING)

- Already implemented in ProformaInvoice.js
- Shows multiple invoices per lead with version indicators
- "Proceed to Agreement" button only on finalized invoices

**Files Modified:**
- `/app/backend/routers/project_payments.py`
- `/app/backend/routers/employees.py`
- `/app/backend/routers/kickoff.py`
- `/app/frontend/src/pages/ProjectPaymentDetails.js`
- `/app/frontend/src/pages/sales-funnel/Quotations.js`

**Test Results:** iteration_54.json - 94% backend (1 test data issue), 100% frontend

**Credentials:**
- Admin: admin@dvbc.com / admin123
- Consultant: consultant@dvbc.com / consultant123

**MOCKED:** Email sending for payment reminders - records to DB only, no actual email sent


---
## Bug Fixes (Feb 19, 2026)

### Employees Page Issues - FIXED
1. **Scorecards not showing values** - ✅ FIXED
   - Changed field mapping from `with_user_access` to `with_portal_access`
   - Changed field mapping from `without_user_access` to `without_portal_access`
   - Now shows: Total Employees (10), With System Access (3), No System Access (5), Departments (3)

2. **Multiple employee entry points** - ✅ FIXED
   - REMOVED "Add Employee" button and dialog
   - REMOVED "Sync from Users" button (was showing "Method Not Allowed" error)
   - Now only ONE entry point: "Onboard New Employee" button → redirects to /onboarding page
   - This ensures all employees go through the standard onboarding workflow

3. **Permission sync across ERP** - ✅ VERIFIED WORKING
   - `/api/department-access/my-access` returns correct permission flags
   - `has_reportees`, `is_view_only`, `can_edit`, `can_manage_team` all functioning
   - Department-based page access working correctly

---
## Employee ID Login System (Feb 19, 2026) - ✅ IMPLEMENTED

### Login System Changes
1. **Login with Employee ID** instead of email
   - Login field shows "Employee ID" with placeholder "EMP001"
   - Input auto-converts to uppercase
   - Backend supports both `employee_id` and `email` for backward compatibility

2. **Pattern-based Password**
   - Format: `Welcome@{EmployeeID}` (e.g., `Welcome@EMP001`)
   - Auto-generated during onboarding

3. **Predefined Admin Credentials**
   - `ADMIN001` / `admin123` - System Admin
   - `HR001` / `hr123` - HR Manager
   - `MGR001` / `manager123` - Manager

### Password Management Page (`/password-management`)
- **Access**: Admin and HR Managers only
- **Features**:
  - View all employees with their access status
  - Reset employee passwords (pattern-based default)
  - Enable/Disable employee access (except Admin accounts)
  - Search by Employee ID, name, or email
- **Stats Cards**: Total Employees, With Access, Disabled, No Access

### Post-Onboarding Success Popup
- Shows employee details (name, ID, department, etc.)
- Displays login credentials (Employee ID + generated password)
- Shows reporting manager information
- Copy buttons for credentials
- Mock email notification (simulated)

### API Endpoints
- `POST /api/auth/login` - Updated to accept `employee_id` or `email`
- `POST /api/auth/admin/reset-employee-password` - Reset password (Admin/HR only)
- `POST /api/auth/admin/toggle-employee-access` - Enable/Disable access (Admin/HR only)

### Testing Status
- Backend: 100% (10/10 tests passed)
- Frontend: 100% (All UI verifications passed)
- Test report: `/app/test_reports/iteration_60.json`

### Mock/Simulated Features
- **Email Notifications**: Console.log only, no actual emails sent

---
## User & Employee Architecture - CONSOLIDATED (Feb 19, 2026)

### Data Model Relationship

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│           EMPLOYEES                 │     │              USERS                  │
│         (HR Master Data)            │     │       (Authentication Only)         │
├─────────────────────────────────────┤     ├─────────────────────────────────────┤
│ id: UUID (internal)                 │     │ id: UUID (internal)                 │
│ employee_id: "EMP001" ◄─────────────┼────►│ employee_id: "EMP001" (LOGIN KEY)   │
│ email: "john@dvbc.com"              │     │ email: "john@dvbc.com"              │
│ first_name, last_name               │     │ full_name                           │
│ department, designation             │     │ role, department                    │
│ salary, bank_details                │     │ hashed_password                     │
│ user_id: UUID (links to users.id)   │     │ is_active                           │
│ has_portal_access: Boolean          │     │ requires_password_change            │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
                 │                                          │
                 │  LINK: employees.user_id = users.id      │
                 │  KEY:  employees.employee_id = users.employee_id
                 └──────────────────────────────────────────┘
```

### Key Points
1. **Employee ID is the human-readable key** (EMP001, HR001, ADMIN001)
2. **User.employee_id stores the same format** - NOT UUID
3. **Login uses employee_id** (e.g., EMP001 + password)
4. **One employee → One user** (when portal access granted)
5. **Employee can exist without user** (no portal access)

### Endpoint Consolidation

| Before (Removed/Deprecated) | After (Consolidated) |
|-----------------------------|----------------------|
| POST /api/users | ❌ REMOVED - Use grant-access |
| POST /api/employees/{id}/link-user | ❌ REMOVED - grant-access handles this |

| Active Endpoints | Purpose |
|------------------|---------|
| POST /api/employees | Create employee (HR master) |
| POST /api/employees/{id}/grant-access | Create user + link (single endpoint) |
| POST /api/auth/admin/reset-employee-password | Reset password by employee_id |
| POST /api/auth/admin/toggle-employee-access | Enable/Disable access |

### Login Flow
```
1. User enters: EMP001 + password
2. Backend searches: users.employee_id = "EMP001"
3. If not found, searches: employees.employee_id = "EMP001" → users.email
4. Verifies password hash
5. Returns JWT token
```

### Password Format
- Pattern: `Welcome@{employee_id}` (e.g., Welcome@EMP001)
- Auto-generated during onboarding
- User should change on first login

### Predefined Admin Accounts
| Employee ID | Email | Role |
|-------------|-------|------|
| ADMIN001 | admin@dvbc.com | admin |
| HR001 | hr.manager@dvbc.com | hr_manager |
| MGR001 | manager@dvbc.com | manager |

---
## E2E Flow Verification - Employee ID Linkage (Feb 19, 2026)

### Sales Process Flow
```
Lead → Pricing Plan → Quotation → Proforma Invoice → Agreement → Project
  ↓         ↓            ↓              ↓               ↓           ↓
created_by  created_by   created_by    created_by      created_by  created_by
  ↓         ↓            ↓              ↓               ↓           ↓
user.id → user.employee_id (ADMIN001, USR001, EMP009, etc.)
```

### Consulting Process Flow
```
Project → Consultant Assignment → Tasks → Timesheet → Deliverables
   ↓              ↓                 ↓        ↓            ↓
created_by   consultant_id     assigned_to  user_id    created_by
   ↓              ↓                 ↓        ↓            ↓
user.id → user.employee_id (CON001, PC001, SC001, etc.)
```

### Verification Results
- ✅ All 18 users have valid employee_id format
- ✅ All leads reference valid created_by → user.employee_id
- ✅ All quotations reference valid created_by → user.employee_id
- ✅ All agreements reference valid created_by → user.employee_id
- ✅ All projects reference valid created_by → user.employee_id
- ✅ Consultant assignments link to user.employee_id (CON001)

### Key Collections Audited
| Collection | Field | Links To | Status |
|------------|-------|----------|--------|
| leads | created_by | users.id → users.employee_id | ✅ Valid |
| quotations | created_by | users.id → users.employee_id | ✅ Valid |
| agreements | created_by | users.id → users.employee_id | ✅ Valid |
| proforma_invoices | created_by | users.id → users.employee_id | ✅ Valid |
| projects | created_by, assigned_consultants | users.id → users.employee_id | ✅ Valid |
| consultant_assignments | consultant_id | users.id → users.employee_id | ✅ Valid |

### No Orphaned References Found
All `created_by` and assignment fields properly reference existing users with valid employee_id.

---
## E2E Onboarding & Flow Test - COMPLETE (Feb 19, 2026)

### Test Scenario
Created new employee EMP011 (E2ETest SalesRep) via HR onboarding and verified complete data flow.

### Results Summary
| Test | Status | Details |
|------|--------|---------|
| Employee Creation | ✅ PASS | EMP011 created with Sales department |
| Portal Access Grant | ✅ PASS | User created with Welcome@EMP011 password |
| Employee ID Login | ✅ PASS | Login works, returns correct user data |
| Department Sidebar | ✅ PASS | Sales menu items visible |
| Leads Access | ✅ PASS | Can view 16 leads |
| Lead Creation | ✅ PASS | Created "E2E Test Company Pvt Ltd" |
| Employee ID Linkage | ✅ PASS | lead.created_by → user.id → user.employee_id = EMP011 |
| Sales Flow | ✅ PASS | Start Sales Flow → Pricing Plan page works |
| Password Management | ✅ PASS | EMP011 visible in admin list |

### Data Integrity Verified
```
Lead: E2E Test Company Pvt Ltd
├── created_by: e93f64e5-0239-4430-9281-c4421ef683eb (user.id)
└── User: e2e.sales.rep@dvbc.com
    ├── id: e93f64e5-0239-4430-9281-c4421ef683eb
    ├── employee_id: EMP011 ✅
    └── Employee Record: E2ETest SalesRep ✅
```

### Test Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| New Employee | EMP011 | Welcome@EMP011 |
| Admin | ADMIN001 | admin123 |
| HR Manager | HR001 | hr123 |

### Backend Tests Created
- `/app/backend/tests/test_e2e_onboarding_flow.py`
- Test report: `/app/test_reports/iteration_62.json`

---
## Onboarding Enhancements (Feb 19, 2026)

### New Features Added

1. **CSV Bulk Import (Step 0 - Quick Import)**
   - Download CSV template with all required fields
   - Download Master File (export all existing employees)
   - Upload CSV for bulk onboarding
   - Auto-generates employee_id and password for each employee
   - Shows preview before processing
   - Download results with credentials

2. **All Fields Mandatory**
   - Personal Info: First Name, Last Name, Work Email, Personal Email, Phone, Gender, DOB, Address
   - Employment Details: Employee ID (auto), Joining Date, Designation, Department, Employment Type, Reporting Manager

3. **Admin Approval for Post-Onboarding Changes**
   - Protected fields: bank_details, salary, designation, department, employment_type
   - HR can submit modification request
   - Only Admin can approve/reject changes
   - Direct updates still allowed for Admin role

4. **Document Upload with Download Option**
   - Photo, ID Proof, Education Certificate, Experience Letter
   - Upload shows green checkmark when done
   - Download button appears after upload
   - Delete option to remove uploaded document

### Onboarding Steps (6 total)
1. Quick Import (CSV)
2. Personal Info
3. Employment Details
4. Documents
5. Bank Details
6. Review & Submit

### CSV Template Fields
```csv
first_name,last_name,email,personal_email,phone,date_of_birth,gender,address,designation,department,employment_type,joining_date
```

### Modification Approval Flow
```
HR Updates Employee → Protected Field Change Detected → Modification Request Created
                                    ↓
                    Admin Reviews → Approve/Reject → Employee Record Updated/Unchanged
```
