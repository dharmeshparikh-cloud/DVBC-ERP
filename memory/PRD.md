# MOM Workflow - Product Requirements Document

## Original Problem Statement
Build a robust and governed expense tracking and meeting management system for consulting teams, enforcing a "Single Source of Truth" (SSOT) architecture.

---

## Implementation Status - March 23, 2026

### Business Rules & Policies - FULLY COMPLETE ✅

**54 rules across 6 policy types with comprehensive governance**

#### Features Implemented:
1. **Policy Cards** - Click to expand/collapse, show rule counts, active status
2. **Add New Rule** - Full CRUD operations (Create, Read, Update, Delete)
3. **Rule Types** - LIMIT, THRESHOLD, CONDITION, FORMULA, APPROVAL with dropdown selector
4. **Unit Support** - All numeric values have required units (days/year, INR, percent, etc.)
5. **Form Validation** - Required fields marked with *, validation before save

#### SOP Documentation (200+ words per policy):
- **Impact Analysis** - 3 impact cards per policy showing affected areas
- **Payroll & Disbursement Linkage** - Shows Affects, Disbursement timing, CTC Components
- **Checklists** - 5 expandable sections:
  - Critical Rules (Payroll Linked)
  - Before Making Changes
  - Configuration Steps
  - Testing & Verification
  - Post-Change Actions
- **Detailed SOP Documentation** - 200+ word comprehensive guide with:
  - Overview
  - Rule Categories explained
  - Configuration Process
  - Payroll Integration Points
  - Best Practices
- **Warnings & Cautions** - Red highlighted warnings
- **Best Practices** - Green highlighted recommendations

---

### Rule Counts by Policy Type
| Policy | Rules | SOP Words |
|--------|-------|-----------|
| Leave | 12 | 400+ |
| Travel | 10 | 350+ |
| Expense | 6 | 300+ |
| Attendance | 8 | 350+ |
| Payroll | 10 | 400+ |
| General HR | 8 | 300+ |
| **Total** | **54** | **2000+** |

---

### API Endpoints

#### Business Rules
- `GET /api/business-rules` - Get all policies
- `GET /api/business-rules/types` - Get policy types
- `POST /api/business-rules/{policy_id}/rule` - **NEW: Add new rule**
- `PUT /api/business-rules/{policy_id}/rule/{rule_id}` - Update rule
- `DELETE /api/business-rules/{policy_id}/rule/{rule_id}` - **NEW: Delete rule**

#### Payroll Simulator
- `POST /api/business-rules/simulate/payroll` - Calculate salary with rules

---

### Architecture Constraint (CRITICAL)
**Business Rules page = HR policy limits ONLY**
- PF, ESI, Professional Tax calculations are STRICTLY in CTC Designer
- This prevents conflicting sources of truth for statutory compliance

---

### Files Modified
- `/app/frontend/src/pages/hr/BusinessRules.js` - Comprehensive SOPs, Add/Delete rule UI
- `/app/backend/routers/business_rules.py` - Add/Delete rule endpoints, model updates
- `/app/backend/tests/test_business_rules_add_rule.py` - New test file

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
- `/app/test_reports/iteration_198.json` - All tests passed (100%)
  - Backend: 23 tests passed
  - Frontend: All features verified

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
- Status: Business Rules with 200+ word SOPs, Add/Edit/Delete rules - COMPLETE
