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
- **Location Search**: OpenStreetMap/Nominatim integration (free, no API key)
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

## Known Issues
- Email sending is MOCKED
- Some test data created with TEST_ prefixes
- Legacy attendance records don't have work_location field (only new records will have it)
- Some performance metrics are simulated (consultant utilization, client ratings, sales data)
- Console warnings about chart dimensions (-1 width/height) - cosmetic, doesn't affect rendering
