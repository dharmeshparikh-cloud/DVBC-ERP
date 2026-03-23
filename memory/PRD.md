# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture.

---

## Implementation Status

### P0 Features Complete

#### Business Rules & Policies (STRESS TESTED - March 23, 2026)
- **54 rules** across 6 policy types (Leave, Travel, Expense, Attendance, Payroll, General HR)
- **Rule Types**: LIMIT, THRESHOLD, CONDITION, FORMULA, APPROVAL
- **SOPs**: Detailed Standard Operating Procedures with Impact Analysis per policy type
- **Payroll Simulator**: Real-time calculation preview
- **RBAC**: HR/Admin can edit, Employees view-only

**Display Features (QA Verified):**
- Time values: `10:00 (10 AM)` format
- Formulas: `basic_salary * 0.12` visible
- WHEN/THEN Slabs: `WHEN ₹0 - ₹15,000 THEN ₹0 | WHEN ₹15,001 - ₹25,000 THEN ₹150`
- AND Conditions: `friday = casual AND client meeting = formal`
- Numeric with units: `12 days/year`, `2,500 INR/day`

---

### Rule Counts by Policy Type
| Policy | Rules | Types |
|--------|-------|-------|
| Leave | 12 | LV001-LV012 |
| Travel | 10 | TR001-TR010 |
| Expense | 6 | EX001-EX006 |
| Attendance | 8 | AT001-AT008 |
| Payroll | 10 | PY001-PY010 |
| General HR | 8 | HR001-HR008 |

---

### Meeting Workflow States
```
DRAFT -> SCHEDULED -> CONFIRMED -> CONDUCTED -> MOM_RECORDED -> DELIVERED
                   -> REJECTED
                   -> RESCHEDULED -> SCHEDULED
                   -> AUTO_ACCEPTED -> CONDUCTED
```

---

### Architecture Constraint (CRITICAL)
**Business Rules page = HR policy limits ONLY**
- PF, ESI, Professional Tax calculations are STRICTLY in CTC Designer
- This prevents conflicting sources of truth

---

## Files Reference

### Business Rules (Updated)
- `/app/frontend/src/pages/hr/BusinessRules.js` - SOPs, formatRuleValue(), formatConditions()
- `/app/backend/routers/business_rules.py` - Rule data and CRUD APIs
- `/app/backend/services/rule_engine.py` - Evaluation service

### Deleted
- `/app/frontend/src/pages/hr/LeavePolicySettings.js` - Replaced by Business Rules

---

## Login Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |
| Employee | EMP005 | Welcome@EMP005 |

---

## Tech Stack
- Frontend: React, Tanstack Query, Tailwind CSS, Shadcn/UI
- Backend: FastAPI, MongoDB
- Test Reports: `/app/test_reports/`

---

## Pending Tasks

### P2 - Upcoming
- PDF generation for salary slips
- Recurring payroll automation
- Bulk salary slip download

### Backlog
- Refactor ConsultingMeetings.js (2400+ lines)
- 24h reminder emails
- DVBC Marketing Hub

---

## Last Updated
- Date: March 23, 2026
- Status: Business Rules STRESS TESTED - All 54 rules verified
- Test Report: `/app/test_reports/iteration_197.json`
