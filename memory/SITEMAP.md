# NETRA ERP - Complete Site Tree
# Generated: 2026-02-22
# Total Pages: 125 unique routes

## SITE STRUCTURE OVERVIEW

```
NETRA ERP
├── Authentication
│   └── /login
│
├── Dashboard
│   └── / (Main Dashboard)
│
├── My Workspace (Self-Service)
│   ├── /my-attendance
│   ├── /my-leaves
│   ├── /my-salary-slips
│   ├── /my-expenses
│   ├── /my-drafts
│   ├── /my-details
│   ├── /my-bank-details
│   └── /my-salary
│
├── Sales Module
│   ├── /sales (Sales Dashboard)
│   ├── /sales-dashboard
│   ├── /leads
│   ├── /manager-leads
│   ├── /sales-meetings
│   ├── /follow-ups
│   ├── /targets
│   ├── /target-management
│   │
│   └── Sales Funnel
│       ├── /sales-funnel-onboarding
│       ├── /sales-funnel/pricing-plans
│       ├── /sales-funnel/quotations
│       ├── /sales-funnel/sow-list
│       ├── /sales-funnel/sow/:pricingPlanId
│       ├── /sales-funnel/sow-review/:pricingPlanId
│       ├── /sales-funnel/scope-selection/:pricingPlanId
│       ├── /sales-funnel/meeting/record
│       ├── /sales-funnel/agreements
│       ├── /sales-funnel/agreement/:agreementId
│       ├── /sales-funnel/payment-verification
│       ├── /sales-funnel/proforma-invoice
│       └── /sales-funnel/approvals
│
├── HR Module
│   ├── /hr (HR Dashboard)
│   ├── /hr-dashboard
│   ├── /employees
│   ├── /onboarding
│   ├── /attendance
│   ├── /attendance-approvals
│   ├── /attendance-leave-settings
│   ├── /hr-attendance-input
│   ├── /hr-leave-input
│   ├── /leave-management
│   ├── /payroll
│   ├── /payroll-summary-report
│   ├── /ctc-designer
│   ├── /letter-management
│   ├── /expenses
│   └── /expense-approvals
│
├── Consulting Module
│   ├── /consulting-dashboard
│   ├── /consultant-dashboard
│   ├── /projects
│   ├── /consulting/projects
│   ├── /consulting/my-projects
│   ├── /consulting/assign-team/:projectId
│   ├── /consulting/project-tasks/:sowId
│   ├── /consulting/payments
│   ├── /consulting/sow-changes
│   ├── /consulting-meetings
│   ├── /timesheets
│   ├── /gantt-chart
│   ├── /projects/:projectId/kickoff
│   ├── /projects/:projectId/payments
│   └── /projects/:projectId/tasks
│
├── Admin Module
│   ├── /admin-dashboard
│   ├── /admin-masters
│   ├── /user-management
│   ├── /role-management
│   ├── /permission-manager
│   ├── /permission-dashboard
│   ├── /employee-permissions
│   ├── /department-access
│   ├── /password-management
│   ├── /email-templates
│   ├── /email-settings
│   ├── /letterhead-settings
│   ├── /office-locations
│   ├── /security-audit
│   ├── /workflow
│   └── /downloads
│
├── Reports & Analytics
│   ├── /reports
│   ├── /performance-dashboard
│   ├── /consultant-performance
│   ├── /team-performance
│   ├── /team-workload
│   ├── /employee-scorecard
│   └── /org-chart
│
├── Communication
│   ├── /chat
│   ├── /ai-assistant
│   ├── /notifications
│   └── /meetings
│
├── Documents
│   ├── /document-center
│   ├── /document-builder
│   ├── /agreements
│   ├── /quotations
│   ├── /invoices
│   └── /sow-list
│
└── Other
    ├── /profile
    ├── /mobile-app
    ├── /tutorials
    ├── /project-roadmap
    ├── /flow-diagram
    ├── /clients
    ├── /client-onboarding
    ├── /consultants
    ├── /staffing-requests
    ├── /kickoff-requests
    ├── /go-live
    ├── /handover-alerts
    ├── /payments
    ├── /payment-verification
    ├── /travel-reimbursement
    ├── /approvals
    └── /accept-offer/:token
```

---

## COMPLETE URL LIST (125 pages)

### Authentication (1)
| URL | Description |
|-----|-------------|
| `/login` | User login page |

### Dashboard (1)
| URL | Description |
|-----|-------------|
| `/` | Main business overview dashboard |

### My Workspace (7)
| URL | Description |
|-----|-------------|
| `/my-attendance` | Personal attendance tracking |
| `/my-leaves` | Personal leave requests |
| `/my-salary-slips` | View salary slips |
| `/my-expenses` | Submit expense claims |
| `/my-drafts` | Continue saved drafts |
| `/my-details` | Personal profile & bank details |
| `/my-bank-details` | Bank account details (redirects to /my-details) |

### Sales Module (20)
| URL | Description |
|-----|-------------|
| `/sales` | Sales portal entry |
| `/sales-dashboard` | Sales KPIs and metrics |
| `/leads` | Lead management |
| `/manager-leads` | Manager lead view |
| `/sales-meetings` | Sales meetings |
| `/follow-ups` | Follow-up tasks |
| `/targets` | Sales targets |
| `/target-management` | Target configuration |
| `/sales-funnel-onboarding` | Sales onboarding flow |
| `/sales-funnel/pricing-plans` | Create pricing plans |
| `/sales-funnel/quotations` | Generate quotations |
| `/sales-funnel/sow-list` | SOW list view |
| `/sales-funnel/sow/:pricingPlanId` | SOW builder |
| `/sales-funnel/sow-review/:pricingPlanId` | SOW review |
| `/sales-funnel/scope-selection/:pricingPlanId` | Scope selection |
| `/sales-funnel/meeting/record` | Record meetings |
| `/sales-funnel/agreements` | Agreements list |
| `/sales-funnel/agreement/:agreementId` | Agreement details |
| `/sales-funnel/payment-verification` | Payment verification |
| `/sales-funnel/proforma-invoice` | Proforma invoice |

### HR Module (12)
| URL | Description |
|-----|-------------|
| `/hr` | HR portal entry |
| `/hr-dashboard` | HR metrics dashboard |
| `/employees` | Employee directory |
| `/onboarding` | Employee onboarding |
| `/attendance` | Attendance records |
| `/attendance-approvals` | Approve attendance |
| `/attendance-leave-settings` | Configure attendance |
| `/leave-management` | Leave administration |
| `/payroll` | Payroll processing |
| `/payroll-summary-report` | Payroll reports |
| `/ctc-designer` | CTC structure design |
| `/letter-management` | HR letters |

### Consulting Module (13)
| URL | Description |
|-----|-------------|
| `/consulting-dashboard` | Consulting overview |
| `/consultant-dashboard` | Individual consultant view |
| `/projects` | All projects |
| `/consulting/projects` | Consulting projects |
| `/consulting/my-projects` | My assigned projects |
| `/consulting/assign-team/:projectId` | Team assignment |
| `/consulting/project-tasks/:sowId` | Project tasks |
| `/consulting/payments` | Project payments |
| `/consulting/sow-changes` | SOW change requests |
| `/timesheets` | Time tracking |
| `/gantt-chart` | Project timeline |
| `/projects/:projectId/kickoff` | Project kickoff |
| `/projects/:projectId/tasks` | Project tasks |

### Admin Module (16)
| URL | Description |
|-----|-------------|
| `/admin-dashboard` | Admin overview |
| `/admin-masters` | Master data management |
| `/user-management` | User administration |
| `/role-management` | Role configuration |
| `/permission-manager` | Permission settings |
| `/permission-dashboard` | Permission overview |
| `/employee-permissions` | Employee access |
| `/department-access` | Department permissions |
| `/password-management` | Password policies |
| `/email-templates` | Email configuration |
| `/email-settings` | Email server settings |
| `/letterhead-settings` | Document templates |
| `/office-locations` | Office management |
| `/security-audit` | Security logs |
| `/workflow` | ERP workflow |
| `/downloads` | System downloads |

### Reports & Analytics (7)
| URL | Description |
|-----|-------------|
| `/reports` | Report center |
| `/performance-dashboard` | Performance metrics |
| `/consultant-performance` | Consultant KPIs |
| `/team-performance` | Team metrics |
| `/team-workload` | Workload analysis |
| `/employee-scorecard` | Employee scorecards |
| `/org-chart` | Organization chart |

### Communication (4)
| URL | Description |
|-----|-------------|
| `/chat` | Team chat |
| `/ai-assistant` | AI-powered assistant |
| `/notifications` | Notification center |
| `/meetings` | Meeting management |

### Documents (6)
| URL | Description |
|-----|-------------|
| `/document-center` | Document management |
| `/document-builder` | Document creation |
| `/sales-funnel/agreements` | Agreement repository |
| `/sales-funnel/quotations` | Quotation management |
| `/invoices` | Invoice management |
| `/sales-funnel/sow-list` | SOW repository |

---

## STATISTICS

| Category | Count |
|----------|-------|
| Authentication | 1 |
| Dashboard | 1 |
| My Workspace | 8 |
| Sales | 20 |
| HR | 12 |
| Consulting | 13 |
| Admin | 16 |
| Reports | 7 |
| Communication | 4 |
| Documents | 6 |
| Other | 37 |
| **TOTAL** | **125** |

---

## ROLE-BASED ACCESS MATRIX

| Module | Admin | HR | Sales | Consultant | Executive |
|--------|-------|----|----|------------|-----------|
| Dashboard | ✓ | ✓ | ✓ | ✓ | Guided |
| My Workspace | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sales | ✓ | ✗ | ✓ | ✗ | ✓ |
| HR | ✓ | ✓ | ✗ | ✗ | ✗ |
| Consulting | ✓ | ✗ | ✗ | ✓ | ✗ |
| Admin | ✓ | ✗ | ✗ | ✗ | ✗ |
| Reports | ✓ | ✓ | ✓ | ✓ | ✗ |

---

## API ENDPOINTS SUMMARY

| Category | Count |
|----------|-------|
| Auth | 8 |
| Users | 12 |
| Employees | 23 |
| Leads | 18 |
| Projects | 15 |
| Meetings | 12 |
| SOW | 20 |
| Payments | 10 |
| Reports | 8 |
| Masters | 15 |
| **Total Endpoints** | **~150** |

---

Generated by NETRA ERP Health Check System
