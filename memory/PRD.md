# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture.

---

## Implementation Status - March 23, 2026

### Business Rules & Policies - FULLY COMPLETE ✅

**54 rules across 6 policy types with comprehensive governance**

#### Rule Form Features (NEW):
1. **Rule ID** - Auto-generated based on policy type (LV013, TR011, etc.)
2. **Rule Type Dropdown** - LIMIT, THRESHOLD, CONDITION, FORMULA, APPROVAL
3. **Category Dropdown** - Policy-specific categories:
   - Leave: Quota, Accrual, Carry Forward, Encashment, Special Leave, Sandwich, Approval, Restrictions
   - Travel: Daily Allowance, Accommodation, Flight, Train, Cab, Own Vehicle, Advance, Settlement, International
   - Expense: Approval Limits, Documentation, Meals & Entertainment, Office Supplies, Communication, Professional Dev, Compliance, Cutoff
   - Attendance: Work Hours, Core Hours, Flexibility, WFH, Overtime, Comp-off, Late Penalty, Absent Penalty, Shift
   - Payroll: Processing Date, Statutory PF/ESI/PT/TDS, LOP Deduction, Bonus, Reimbursement, Disbursement
   - General: Probation, Notice Period, Termination, Increment, Promotion, Confirmation, Retirement, Workplace

4. **Applies To Dropdown** - Rule scope options:
   - All Employees
   - By Department (12 departments)
   - By Role (10 roles)
   - By Grade (L1-L9)
   - By Employment Type (8 types)
   - By Location (12 locations including Metro/Non-Metro)
   - By Experience (6 ranges)
   - By CTC Range (6 bands)
   - Custom Employee Group

5. **Unit Dropdown** - 25 unit options (days/year, INR, percent, etc.)

6. **Value Type Templates** - Based on rule type:
   - LIMIT: max_per_claim, max_per_day, max_per_month, cap_ceiling
   - THRESHOLD: trigger_above/below, require_approval_above, auto_approve_below
   - CONDITION: if_then, and_condition, or_condition, when_equals, mandatory, prohibited
   - FORMULA: basic_salary * 0.12, LOP formula, Pro-rata, slab_based
   - APPROVAL: auto_approve, manager/HR/finance approval, two_level, no_self_approval

7. **Condition Builder** - For CONDITION type rules:
   - Field selector (17 fields: department, role, salary, travel_hours, etc.)
   - Operator selector (10 operators: ==, !=, >, <, in, contains, etc.)
   - Value input

8. **Rule Preview** - Live preview showing rule name, value, and scope

---

### SOP Documentation (200+ words per policy):
- Impact Analysis - 3 impact cards per policy
- Payroll & Disbursement Linkage - Shows Affects, Disbursement timing, CTC Components
- 5 expandable checklist sections with 20+ items each
- Detailed SOP Documentation - 200+ words
- Warnings & Cautions - Red highlighted
- Best Practices - Green highlighted

---

## Rule Counts by Policy Type
| Policy | Rules | Categories |
|--------|-------|------------|
| Leave | 12 | 8 |
| Travel | 10 | 10 |
| Expense | 6 | 8 |
| Attendance | 8 | 9 |
| Payroll | 10 | 9 |
| General HR | 8 | 8 |
| **Total** | **54** | **52** |

---

## API Endpoints

### Business Rules
- `GET /api/business-rules` - Get all policies
- `GET /api/business-rules/types` - Get policy types
- `POST /api/business-rules/{policy_id}/rule` - Add new rule
- `PUT /api/business-rules/{policy_id}/rule/{rule_id}` - Update rule
- `DELETE /api/business-rules/{policy_id}/rule/{rule_id}` - Delete rule

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

## Test Reports
- `/app/test_reports/iteration_198.json` - All tests passed

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
- Status: Enhanced Rule Form with comprehensive dropdowns - COMPLETE
