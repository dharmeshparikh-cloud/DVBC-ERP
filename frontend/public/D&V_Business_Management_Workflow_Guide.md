# D&V Business Management Application
# Complete Workflow Guide

---

## Table of Contents
1. [Application Overview](#1-application-overview)
2. [User Roles & Access Control](#2-user-roles--access-control)
3. [Department Workflows](#3-department-workflows)
   - [Sales Department Flow](#31-sales-department-flow)
   - [Consulting Department Flow](#32-consulting-department-flow)
   - [HR Department Flow](#33-hr-department-flow)
4. [End-to-End Process Flow](#4-end-to-end-process-flow)
5. [Feature Details by Module](#5-feature-details-by-module)
6. [Connectivity Analysis & Issues](#6-connectivity-analysis--issues)
7. [Duplication & Overlap Analysis](#7-duplication--overlap-analysis)
8. [Recommendations](#8-recommendations)

---

## 1. Application Overview

D&V Business Consulting Management Application is a comprehensive business management system designed for a 50-person HR consulting organization. The application covers:

- **HR Management** - Employee records, attendance, leave, payroll
- **Sales Management** - Lead tracking, pricing plans, quotations, agreements
- **Consulting Management** - Project scopes, task management, approvals
- **Finance** - Invoicing, payment tracking, expense management

### Technology Stack
- **Frontend:** React 18 + Tailwind CSS + Shadcn/UI
- **Backend:** FastAPI + Python
- **Database:** MongoDB
- **Authentication:** JWT + Emergent-managed Google Auth (domain-restricted)

---

## 2. User Roles & Access Control

### System Roles

| Role | Department | Access Level |
|------|------------|--------------|
| **Admin** | All | Full system access, all modules |
| **Manager** | All | View/Download access, approve agreements |
| **Executive** | Sales | Create leads, SOW, quotations |
| **Account Manager** | Sales | Client accounts and sales |
| **Project Manager** | Consulting | Audit, approve, authorize SOW |
| **Principal Consultant** | Consulting | Freeze authority, scope management |
| **Lead Consultant** | Consulting | Team oversight, scope updates |
| **Senior Consultant** | Consulting | Advanced permissions |
| **Consultant** | Consulting | View SOW, update progress/status |
| **Lean Consultant** | Consulting | Junior consultant role |
| **HR Manager** | HR | HR team manager |
| **HR Executive** | HR | HR team member |
| **Subject Matter Expert** | Consulting | Domain expert |

### Role-Based Navigation Access

```
ADMIN / MANAGER:
  All sections visible (HR, Sales, Consulting, Admin)

SALES ROLES (Executive, Account Manager):
  - Sales section
  - My Workspace

CONSULTING ROLES (PM, Consultants):
  - Consulting section
  - My Workspace

HR ROLES (HR Manager, HR Executive):
  - HR section
  - My Workspace
```

---

## 3. Department Workflows

### 3.1 Sales Department Flow

```
                    SALES WORKFLOW
                    ==============

[LEAD CAPTURE]
      |
      v
[PRICING PLAN BUILDER]
      |
      | - Enter Total Client Investment (Top-Down)
      | - Add Team Deployment Structure
      | - Configure Payment Schedule
      | - Set Project Duration
      |
      v
[SOW SCOPE SELECTION]
      |
      | - Select scopes from master categories
      | - Add custom scopes if needed
      | - Custom scopes auto-save to master
      |
      v
[PROFORMA INVOICE]
      |
      | - Auto-generated from pricing plan
      | - PDF download available
      | - GST/TDS calculations
      | - Send to client
      |
      v
[AGREEMENT CREATION]
      |
      | - Auto-populated from pricing plan
      | - Team deployment inherited
      | - Editable milestones
      | - E-signature via canvas
      | - PDF download
      |
      v
[HANDOVER TO CONSULTING]
      |
      | - Kickoff Request creation
      | - Assign Project Manager
      | - Lock sales SOW
```

#### Key Sales Pages:
1. `/leads` - Lead Management
2. `/sales-funnel/pricing-plans` - Pricing Plan Builder
3. `/sales-funnel/scope-selection/:id` - SOW Scope Selection
4. `/sales-funnel/proforma-invoice` - Proforma Invoice
5. `/sales-funnel/agreements` - Agreement List
6. `/sales-funnel/agreement/:id` - Agreement Detail & E-Sign

---

### 3.2 Consulting Department Flow

```
                CONSULTING WORKFLOW
                ===================

[RECEIVE KICKOFF REQUEST]
      |
      v
[MY PROJECTS DASHBOARD]
      |
      | - View handed-over projects
      | - Check scope status breakdown
      | - Progress tracking
      |
      v
[PROJECT SCOPE VIEW]
      |
      | - List View (grouped by category)
      | - Kanban Board
      | - Gantt Chart (timeline)
      | - Timeline View
      |
      v
[SCOPE MANAGEMENT]
      |
      | - Update status (Not Started/In Progress/Completed/N/A)
      | - Track progress percentage
      | - Log days spent
      | - Record meetings count
      | - Add attachments
      | - Add notes
      |
      v
[TASK MANAGEMENT]
      |
      | - Create tasks within scopes
      | - Assign to team members
      | - Set priority & due dates
      |
      v
[APPROVAL WORKFLOW]
      |
      | - Request Approval (parallel)
      |    |
      |    +---> Manager Approval
      |    |
      |    +---> Client Approval
      |
      v
[ROADMAP SUBMISSION]
      |
      | - Submit for client approval
      | - Monthly/Quarterly/Yearly cycles
      | - Client consent tracking
```

#### Key Consulting Pages:
1. `/consulting/projects` - My Projects Dashboard
2. `/sales-funnel/sow-review/:id` - Project Scope View
3. `/consulting/project-tasks/:id` - Task Management
4. `/project-roadmap` - Project Roadmap

---

### 3.3 HR Department Flow

```
                    HR WORKFLOW
                    ===========

[EMPLOYEE MANAGEMENT]
      |
      +---> Employee Records
      |        | - Personal details
      |        | - Role assignment
      |        | - Department assignment
      |        | - Reporting structure
      |
      +---> Org Chart
      |        | - Hierarchical view
      |        | - Reporting relationships
      |
      +---> Attendance
      |        | - Check-in/out tracking
      |        | - Attendance reports
      |
      +---> Leave Management
      |        | - Leave requests
      |        | - Approval workflow
      |        | - Balance tracking
      |
      +---> Payroll
             | - Salary slip generation
             | - Deductions/allowances
```

#### Key HR Pages:
1. `/employees` - Employee Management
2. `/org-chart` - Organization Chart
3. `/attendance` - Attendance Tracking
4. `/leave-management` - Leave Management
5. `/payroll` - Payroll Management

---

## 4. End-to-End Process Flow

### Complete Business Cycle: Lead to Project Completion

```
PHASE 1: LEAD ACQUISITION
=========================
Sales Executive logs in
       |
       v
Creates new lead in /leads
       |
       | - Client details
       | - Company info
       | - Contact information
       | - Lead score auto-calculated
       |
       v
Lead status: NEW


PHASE 2: PRICING & PROPOSAL
===========================
Sales Executive navigates to
/sales-funnel/pricing-plans
       |
       v
Creates Pricing Plan
       |
       | - Total Client Investment (Top-Down)
       | - Team Deployment Structure:
       |     - Role selection
       |     - Tenure type (allocation %)
       |     - Meeting type & frequency
       |     - Rate per meeting (auto-calculated)
       | - Payment Schedule:
       |     - Monthly/Quarterly/Custom
       |     - GST/TDS configuration
       |     - Conveyance (lumpsum)
       |
       v
Clicks "Save & Continue to Scope Selection"


PHASE 3: SCOPE OF WORK DEFINITION
=================================
Redirected to
/sales-funnel/scope-selection/:pricingPlanId
       |
       v
Select Scopes from Master
       |
       | - 8 default categories:
       |     Sales, HR, Operations, Training,
       |     Analytics, Digital Marketing,
       |     Finance, Strategy
       | - 41+ pre-defined scope templates
       | - Can add custom scopes
       |
       v
Clicks "Save & Continue to Proforma Invoice"


PHASE 4: PROFORMA INVOICE
=========================
Redirected to
/sales-funnel/proforma-invoice
       |
       v
Auto-populated Invoice Created
       |
       | - Team deployment from pricing plan
       | - Total meetings calculated
       | - GST @ 18% (CGST 9% + SGST 9%)
       | - TDS deduction if applicable
       | - Amount in words (Indian Rupees)
       |
       v
Options:
       | - View Invoice (detailed view)
       | - Download PDF
       | - Send to Client
       |
       v
Click "Finalize" to lock invoice


PHASE 5: AGREEMENT GENERATION
=============================
Click "Proceed to Agreement"
       |
       v
Navigate to
/sales-funnel/agreements
       |
       v
Agreement Auto-Created
       |
       | - Client & consultant details
       | - Team deployment structure
       | - Pricing summary
       | - Payment milestones (editable)
       | - Terms & conditions
       |
       v
Navigate to Agreement Detail
/sales-funnel/agreement/:agreementId
       |
       | Features:
       | - PDF download
       | - E-Signature (canvas-based)
       | - Signer details capture
       |
       v
Client signs agreement


PHASE 6: HANDOVER TO CONSULTING
===============================
Sales creates Kickoff Request
/kickoff-requests
       |
       v
Assign Project Manager
       |
       v
PM receives notification


PHASE 7: PROJECT EXECUTION (CONSULTING)
=======================================
PM/Consultant logs in
       |
       v
Navigate to /consulting/projects
       |
       v
View handed-over project
       |
       | - Progress circle
       | - Scope status breakdown
       |
       v
Click "View Scopes"
       |
       v
Navigate to
/sales-funnel/sow-review/:pricingPlanId
       |
       v
4 View Modes Available:
       |
       +---> LIST VIEW
       |       | - Grouped by category
       |       | - Expandable tasks
       |       | - Status badges
       |
       +---> KANBAN BOARD
       |       | - Not Started column
       |       | - In Progress column
       |       | - Completed column
       |       | - N/A column
       |
       +---> GANTT CHART
       |       | - Timeline visualization
       |       | - Drag to update dates
       |       | - Progress tracking
       |
       +---> TIMELINE VIEW
               | - Milestone-based view
               | - Status indicators


PHASE 8: TASK MANAGEMENT
========================
Within Project Scope View
       |
       v
Expand scope to see tasks
       |
       v
Click "+" to add task
       |
       | - Task name
       | - Description
       | - Priority (Low/Medium/High)
       | - Due date
       | - Assignee
       |
       v
Update task status:
       | - Pending
       | - In Progress
       | - Completed


PHASE 9: APPROVAL WORKFLOW
==========================
Task marked as "Completed"
       |
       v
Click "Request Approval"
       |
       v
PARALLEL APPROVAL INITIATED:
       |
       +---> Manager receives request
       |       | - Can view task details
       |       | - Approve/Reject button
       |
       +---> Client receives notification
               | - Can approve via portal
               | - Or email response
       |
       v
Both approvals required:
       | - Manager Approved
       | - Client Approved
       |
       v
Task Status: "Fully Approved"


PHASE 10: PROJECT COMPLETION
============================
All scopes completed
       |
       v
Submit Roadmap for Approval
       |
       | - Select approval cycle
       | - Monthly/Quarterly/Yearly
       |
       v
Client approval received
       |
       v
Project marked complete
```

---

## 5. Feature Details by Module

### 5.1 Lead Management (`/leads`)
- Create/Edit/Delete leads
- Lead scoring (auto-calculated)
- Status tracking (New → Contacted → Qualified → Proposal → Agreement → Closed)
- Assign to sales team members
- LinkedIn URL capture
- Company & contact details

### 5.2 Pricing Plan Builder (`/sales-funnel/pricing-plans`)
**Top-Down Pricing Model:**
- Total Client Investment as primary input
- Auto-allocation to team members based on tenure type percentages
- Team deployment structure with:
  - Role selection (from master)
  - Tenure type (determines allocation %)
  - Meeting type
  - Mode (Online/Offline/Mixed)
  - Count (number of consultants)
  - Committed meetings (auto-calculated)
  - Rate per meeting (auto-calculated)

**Payment Configuration:**
- Project duration (Monthly/Quarterly/Half-Yearly/Yearly/Custom)
- Payment schedule (Monthly/Quarterly/Milestone/Upfront/Custom)
- GST @ 18% (configurable)
- TDS (configurable percentage)
- Conveyance (lumpsum amount)

**Additional Features:**
- Section notes (Pricing, Team, Payment, General)
- Agreement sections toggles (8 checkboxes)
- Payment schedule breakdown preview

### 5.3 SOW Scope Selection (`/sales-funnel/scope-selection/:id`)
- Master scopes organized by 8 categories
- Checkbox selection (2 scopes per row)
- Select all category option
- Search functionality
- Custom scope addition (auto-saves to master)
- Visual selection counter

### 5.4 Proforma Invoice (`/sales-funnel/proforma-invoice`)
- Professional invoice template
- Company branding (D&V logo)
- Invoice details (number, date, payment terms)
- Buyer/Client details section
- Team deployment breakdown
- Pricing summary with GST split
- HSN/SAC code (998311)
- Amount in words
- Bank details
- Terms of delivery
- PDF download
- Send to client functionality

### 5.5 Agreement Management (`/sales-funnel/agreements`)
- Auto-populated from pricing plan
- Team deployment inherited
- Project tenure configuration
- Editable payment milestones table
- Canvas-based E-signature:
  - Draw signature with mouse/touch
  - Clear button
  - Signer details (name, designation, email, date)
- PDF download
- Word document download

### 5.6 Consulting Project View (`/sales-funnel/sow-review/:id`)
- **List View:**
  - Grouped by category
  - Expandable scope items
  - Task management per scope
  - Status badges
  - Progress percentage
  
- **Kanban Board:**
  - 4 columns (Not Started, In Progress, Completed, N/A)
  - Drag-and-drop (visual only)
  
- **Gantt Chart:**
  - Interactive timeline (gantt-task-react library)
  - Day/Week/Month view modes
  - Drag to update dates
  - Click to edit scope
  - Color-coded by status
  
- **Timeline View:**
  - Milestone-based visualization
  - Status indicators

### 5.7 Task Management (within ConsultingScopeView)
- Create tasks within scopes
- Task properties:
  - Name & description
  - Priority (Low/Medium/High)
  - Due date
  - Assignee
- Status workflow: Pending → In Progress → Completed → Approved
- Attachment support
- Parallel approval workflow:
  - Manager approval
  - Client approval
  - Both required for "Fully Approved" status

---

## 6. Connectivity Analysis & Issues

### 6.1 Working Connections (OK)
| From | To | Connection Type |
|------|-----|-----------------|
| Lead | Pricing Plan | `lead_id` reference |
| Pricing Plan | SOW Selection | Route navigation |
| SOW Selection | Proforma Invoice | Route navigation + `pricing_plan_id` |
| Proforma Invoice | Agreement | `quotation_id` reference |
| Agreement | AgreementView | Route navigation (NEEDS FIX) |
| SOW | Consulting Projects | `sales_handover_complete` flag |

### 6.2 Connectivity Issues Identified

**ISSUE 1: Missing "View" Button on Agreements List**
- **Location:** `/app/frontend/src/pages/sales-funnel/Agreements.js`
- **Problem:** No direct navigation from agreements list to detailed agreement view
- **Impact:** Users cannot easily access the E-signature page
- **Fix Required:** Add "View" button linking to `/sales-funnel/agreement/:agreementId`

**ISSUE 2: Back Navigation Inconsistency**
- **Location:** AgreementView.js
- **Problem:** Back button goes to `/sales-funnel/proforma-invoice` regardless of entry point
- **Impact:** Confusing navigation experience
- **Suggestion:** Implement context-aware back navigation

**ISSUE 3: Kickoff Request Flow Gap**
- **Location:** Between Agreements and Consulting
- **Problem:** After agreement is signed, there's no automated kickoff request creation
- **Impact:** Manual process required for handover
- **Suggestion:** Auto-create kickoff request on agreement signature

### 6.3 Data Flow Issues

**ISSUE 4: SOW ID Reference**
- **Problem:** Multiple ID references (`sow.id` vs `pricingPlanId`)
- **Impact:** Confusion in routing between sales and consulting views
- **Current State:** Working but fragile

**ISSUE 5: Agreement-SOW Link**
- **Problem:** Agreement doesn't store direct SOW reference
- **Impact:** Need to traverse through pricing plan to get SOW data
- **Suggestion:** Add `sow_id` directly to Agreement schema

---

## 7. Duplication & Overlap Analysis

### 7.1 Identified Duplications

**DUPLICATION 1: Team Deployment Entry**
| Location 1 | Location 2 | Overlap |
|------------|------------|---------|
| Pricing Plan Builder | Agreement Dialog | Both allow team deployment entry |
| **Resolution:** Agreement should only inherit, not re-enter |

**DUPLICATION 2: Payment Terms Configuration**
| Location 1 | Location 2 | Overlap |
|------------|------------|---------|
| Pricing Plan Builder (payment schedule) | Agreement (payment milestones) | Both configure payments |
| **Resolution:** Agreement milestones should auto-populate from pricing plan |

**DUPLICATION 3: Client Information**
| Location 1 | Location 2 | Location 3 | Overlap |
|------------|------------|------------|---------|
| Lead | Proforma Invoice (buyer) | Agreement (second party) | Same client data entered multiple places |
| **Resolution:** Single source of truth from Lead record |

### 7.2 Functional Overlap

**OVERLAP 1: Project View Pages**
- `/sales-funnel/sow-review/:pricingPlanId` - Consulting team uses this
- `/consulting/project-tasks/:sowId` - Also for consulting
- **Analysis:** Different purposes - one for scope tracking, one for task management
- **Status:** OK - Complementary functionality

**OVERLAP 2: Meeting Tracking**
- Consulting Meetings (`/consulting-meetings`)
- Meetings count in scope tracking
- MOM (Minutes of Meeting) feature
- **Analysis:** Multiple meeting-related features
- **Status:** Could be consolidated but currently serves different purposes

**OVERLAP 3: Approval Workflows**
- Agreement approval (Manager)
- Task approval (Manager + Client parallel)
- Roadmap approval (Client)
- **Analysis:** Three different approval systems
- **Status:** OK - Different business purposes

### 7.3 Code-Level Duplications

**FILE DUPLICATION 1: Quotations vs Proforma Invoice**
- `/app/frontend/src/pages/sales-funnel/Quotations.js` exists
- `/app/frontend/src/pages/sales-funnel/ProformaInvoice.js` exists
- **Status:** Quotations.js is legacy, ProformaInvoice.js is current
- **Action:** Remove Quotations.js after confirming no references

**FILE SIZE CONCERN 1: ConsultingScopeView.js**
- **Size:** Very large component (1500+ lines)
- **Contains:** List view, Kanban, Gantt, Timeline, Task dialogs
- **Recommendation:** Break into sub-components

**FILE SIZE CONCERN 2: PricingPlanBuilder.js**
- **Size:** Large component (1400+ lines)
- **Contains:** Multiple forms, team deployment, payment configuration
- **Recommendation:** Extract into smaller components

**FILE SIZE CONCERN 3: server.py**
- **Size:** Monolithic backend file
- **Contains:** All API endpoints
- **Recommendation:** Split into router modules (partially done with `/routers/`)

---

## 8. Recommendations

### 8.1 High Priority Fixes

1. **Add "View" button to Agreements list**
   - File: `Agreements.js`
   - Action: Add button to navigate to `/sales-funnel/agreement/:id`

2. **Auto-populate Agreement milestones**
   - Currently: Manual entry
   - Needed: Inherit from Pricing Plan payment schedule

3. **Kickoff Request automation**
   - Trigger: On Agreement signature
   - Action: Auto-create kickoff request

### 8.2 Code Refactoring Priorities

1. **Break down ConsultingScopeView.js**
   - Extract: `ScopeListView.js`
   - Extract: `ScopeKanbanBoard.js`
   - Extract: `ScopeGanttChart.js`
   - Extract: `TaskManagementDialog.js`
   - Extract: `ApprovalWorkflowDialog.js`

2. **Break down PricingPlanBuilder.js**
   - Extract: `TeamDeploymentForm.js`
   - Extract: `PaymentScheduleConfig.js`
   - Extract: `PricingSummaryCard.js`

3. **Refactor server.py**
   - Create: `/routers/agreements.py`
   - Create: `/routers/tasks.py`
   - Create: `/routers/approvals.py`

### 8.3 Feature Enhancement Suggestions

1. **Email Notifications (Currently Mocked)**
   - Integrate SMTP for real email delivery
   - Triggers: Approval requests, Agreement sent, Kickoff created

2. **P&L Tracking**
   - Compare committed vs actual meetings
   - Flag over-delivery

3. **Dashboard Consolidation**
   - Sales Dashboard (exists but basic)
   - Consulting Dashboard (exists but basic)
   - Executive Overview dashboard

### 8.4 Data Model Improvements

1. **Add direct SOW reference to Agreement**
   ```
   Agreement {
     ...existing fields,
     sow_id: string  // Direct reference
   }
   ```

2. **Normalize Client data**
   - Single `Client` collection
   - Reference from Lead, Agreement, Project

3. **Activity Log consolidation**
   - Unified audit trail across all modules

---

## Appendix: Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@company.com | admin123 |
| Manager | manager@company.com | manager123 |
| Executive | executive@company.com | executive123 |

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Application:** D&V Business Consulting Management System

