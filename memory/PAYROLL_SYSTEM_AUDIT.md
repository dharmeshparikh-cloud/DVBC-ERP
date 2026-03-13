# NETRA ERP - Complete Payroll System Audit Report

**Audit Date:** March 2026  
**Auditor:** System Analysis Agent  
**Status:** COMPLETE

---

## 1️⃣ PAYROLL ARCHITECTURE

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           NETRA ERP - PAYROLL ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  EMPLOYEE MASTER │────▶│   CTC DESIGNER   │────▶│   SALARY SLIP    │
│   (employees)    │     │ (ctc_structures) │     │  (salary_slips)  │
└────────┬─────────┘     └──────────────────┘     └────────▲─────────┘
         │                                                  │
         ▼                                                  │
┌──────────────────┐     ┌──────────────────┐              │
│     GO-LIVE      │────▶│  PAYROLL CONFIG  │──────────────┤
│  (go_live_req)   │     │ (payroll_config) │              │
└──────────────────┘     └──────────────────┘              │
                                                           │
┌──────────────────┐     ┌──────────────────┐     ┌────────┴─────────┐
│   ATTENDANCE     │────▶│  PAYROLL INPUTS  │────▶│ SALARY SLIP GEN  │
│   (attendance)   │     │ (payroll_inputs) │     │   /api/payroll/  │
└──────────────────┘     └──────────────────┘     │  generate-slip   │
                                                  └────────▲─────────┘
┌──────────────────┐     ┌──────────────────┐              │
│ LEAVE REQUESTS   │────▶│   LOP TRACKING   │──────────────┤
│ (leave_requests) │     │  (Calculated)    │              │
└──────────────────┘     └──────────────────┘              │
                                                           │
┌──────────────────┐     ┌──────────────────┐              │
│    EXPENSES      │────▶│  REIMBURSEMENTS  │──────────────┘
│   (expenses)     │     │(payroll_reimb.)  │
└──────────────────┘     └──────────────────┘
```

### Modules Involved in Payroll

| Module | Purpose | Collection | Integration Level |
|--------|---------|------------|------------------|
| Employee Master | Employee data source | `employees` | PRIMARY |
| CTC Designer | Salary structure definition | `ctc_structures` | PRIMARY |
| Attendance | Working days tracking | `attendance` | LINKED |
| Leave Management | Leave deductions (LOP) | `leave_requests` | LINKED |
| Expense Claims | Reimbursements | `expenses`, `payroll_reimbursements` | LINKED |
| Payroll Config | Salary components | `payroll_config` | PRIMARY |
| Payroll Inputs | Manual adjustments | `payroll_inputs` | PRIMARY |
| Salary Slips | Generated payslips | `salary_slips` | OUTPUT |

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payroll/salary-components` | GET/POST | Configure earnings/deductions |
| `/api/payroll/inputs` | GET/POST | Payroll input data per employee |
| `/api/payroll/inputs/bulk` | POST | Save multiple inputs |
| `/api/payroll/generate-slip` | POST | Generate single slip |
| `/api/payroll/generate-bulk` | POST | Generate all slips for month |
| `/api/payroll/salary-slips` | GET | Retrieve slips |
| `/api/payroll/summary-report` | GET | Department-wise report |
| `/api/payroll/linkage-summary` | GET | View attendance/leave/expense linkages |
| `/api/ctc/structures` | GET/POST | CTC design & approval |
| `/api/attendance` | GET/POST | Attendance records |
| `/api/leave-requests` | GET/POST | Leave management |
| `/api/expenses` | GET/POST | Expense claims |

---

## 2️⃣ COMPLETE PAGE INVENTORY

| Page Name | File Path | Purpose | Linked Module | Database Table | Payroll Impact |
|-----------|-----------|---------|---------------|----------------|----------------|
| Employee Master | `pages/Employees.js` | Employee data | Employee | `employees` | Source of salary, bank details |
| CTC Designer | `pages/CTCDesigner.js` | Salary structure | CTC | `ctc_structures` | Defines earnings/deductions |
| Payroll Dashboard | `pages/Payroll.js` | Run payroll, generate slips | Payroll | `payroll_inputs`, `salary_slips` | Central payroll control |
| My Salary Slips | `pages/MySalarySlips.js` | Employee self-service | Payroll | `salary_slips` | View own slips |
| Attendance | `pages/Attendance.js` | Time tracking | Attendance | `attendance` | Working days calculation |
| My Attendance | `pages/MyAttendance.js` | Self-service | Attendance | `attendance` | Personal attendance |
| HR Attendance Input | `pages/hr/HRAttendanceInput.js` | Manual entry | Attendance | `attendance` | Bulk attendance |
| Leave Management | `pages/LeaveManagement.js` | Leave tracking | Leave | `leave_requests` | LOP deductions |
| My Leaves | `pages/MyLeaves.js` | Self-service | Leave | `leave_requests` | Apply leave |
| Expense Claims | `pages/Expenses.js` | Submit expenses | Expenses | `expenses` | Reimbursements |
| My Expenses | `pages/MyExpenses.js` | Self-service | Expenses | `expenses` | Personal expenses |
| Go-Live Dashboard | `pages/GoLiveDashboard.js` | Activate employees | Go-Live | `go_live_requests` | Enables payroll |
| Payroll Summary Report | `pages/hr/PayrollSummaryReport.js` | Monthly reports | Payroll | `salary_slips` | Reporting |
| Approvals Center | `pages/ApprovalsCenter.js` | CTC approvals | Approvals | `ctc_structures` | CTC approval flow |
| Mobile App | `pages/EmployeeMobileApp.js` | Mobile check-in | Mobile | `attendance`, `expenses` | Mobile data entry |

---

## 3️⃣ DATABASE SCHEMA ANALYSIS

### Collections Used in Payroll

| Collection | Purpose | Key Fields | Payroll Link |
|------------|---------|------------|--------------|
| `employees` | Employee master | `id`, `salary`, `bank_details`, `go_live_status` | Source of truth for employee data |
| `ctc_structures` | Salary structure | `employee_id`, `annual_ctc`, `components`, `status` | Active CTC defines salary breakdown |
| `payroll_config` | Salary components | `type`, `earnings[]`, `deductions[]` | Default calculation rules |
| `payroll_inputs` | Monthly inputs | `employee_id`, `month`, `present_days`, `incentive`, `penalty` | Manual adjustments |
| `salary_slips` | Generated slips | `employee_id`, `month`, `earnings[]`, `deductions[]`, `net_salary` | Final payroll output |
| `attendance` | Daily attendance | `employee_id`, `date`, `status`, `check_in`, `check_out` | Working days calculation |
| `leave_requests` | Leave records | `employee_id`, `leave_type`, `days`, `status` | LOP deductions |
| `expenses` | Expense claims | `employee_id`, `total_amount`, `status`, `payroll_period` | Reimbursements |
| `payroll_reimbursements` | Reimbursement queue | `employee_id`, `amount`, `payroll_period`, `status` | Pending reimbursements |
| `leave_encashments` | Leave encashment | `employee_id`, `days`, `amount`, `status` | Encashment payouts |

---

## 4️⃣ FIELD-LEVEL VALIDATION ANALYSIS

### Payroll Input Fields

| Page | Field | Type | Validation | Mandatory | Payroll Impact |
|------|-------|------|------------|-----------|----------------|
| Payroll | working_days | number | 1-31 | ✅ Yes | Per-day salary calculation |
| Payroll | present_days | number | ≤ working_days | ✅ Yes | Attendance calculation |
| Payroll | absent_days | number | ≥ 0 | ✅ Yes | Absence deductions |
| Payroll | leaves | number | ≥ 0 | ✅ Yes | Leave tracking |
| Payroll | public_holidays | number | ≥ 0 | ✅ Yes | Excluded from working days |
| Payroll | incentive | number | ≥ 0 | ✅ Yes | Added to earnings |
| Payroll | incentive_reason | string | Max 200 chars | ❌ No | Documentation |
| Payroll | advance | number | ≥ 0 | ✅ Yes | Deducted from salary |
| Payroll | penalty | number | ≥ 0 | ✅ Yes | Deducted from salary |
| Payroll | overtime_hours | number | ≥ 0 | ✅ Yes | OT earnings |

### Employee Fields (Payroll-Relevant)

| Field | Type | Validation | Source | Payroll Impact |
|-------|------|------------|--------|----------------|
| salary | number | > 0 | Employee Master | Gross salary base |
| go_live_status | enum | "active" required | Go-Live | Payroll eligibility |
| bank_account_number | string | Required for disbursement | Employee | Payment routing |
| bank_name | string | Required | Employee | Bank identification |
| ifsc_code | string | 11 chars | Employee | Payment routing |
| department | string | Optional | Employee | Report grouping |

---

## 5️⃣ DATA FLOW VALIDATION

### Salary Slip Generation Logic (from `payroll.py`)

```python
# Step 1: Employee Validation
employee = await db.employees.find_one({"id": employee_id})
if go_live_status != "active":
    raise HTTPException("Employee is not Go-Live Active")

# Step 2: CTC Structure Lookup
active_ctc = await db.ctc_structures.find_one({
    "employee_id": employee_id,
    "status": "active",
    "effective_month": {"$lte": month}
})

# Step 3: Attendance Integration
att_records = await db.attendance.find({
    "employee_id": employee_id, 
    "date": {"$regex": f"^{month}"}
})
present_days = count(status in ["present", "work_from_home"])

# Step 4: Leave Integration (LOP)
lop_leave_requests = await db.leave_requests.find({
    "employee_id": employee_id,
    "status": "approved",
    "leave_type": {"$in": ["loss_of_pay", "lop"]}
})
lop_deduction = per_day_salary * lop_days

# Step 5: Expense Reimbursements
payroll_reimb_records = await db.payroll_reimbursements.find({
    "employee_id": employee_id,
    "payroll_period": month,
    "status": "pending"
})

# Step 6: Calculate Final
net_salary = total_earnings - total_deductions
```

---

## 6️⃣ INTEGRATION TEST RESULTS

### Employee → Payroll Flow

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| Employee created with salary | Can run payroll | ❌ Blocked until Go-Live | ✅ CORRECT |
| Employee Go-Live approved | Payroll enabled | ✅ Can generate slip | ✅ CORRECT |
| Employee salary = 0 | Payroll blocked | ✅ "salary not configured" | ✅ CORRECT |
| Employee bank details missing | Slip generated, warning shown | ✅ Slip created, bank fields null | ⚠️ WARNING |

### CTC → Payroll Flow

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| CTC structure approved | Used in slip | ✅ Components from CTC | ✅ CORRECT |
| No CTC, has salary | Use payroll_config defaults | ✅ Falls back to defaults | ✅ CORRECT |
| CTC pending approval | Not used | ✅ Ignored in calculation | ✅ CORRECT |

### Attendance → Payroll Flow

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| Check-in recorded | present_days updated | ✅ Auto-calculated | ✅ CORRECT |
| Manual input overrides | Payroll uses manual | ✅ Manual takes priority | ✅ CORRECT |
| No attendance records | Uses payroll_inputs | ✅ Falls back to inputs | ✅ CORRECT |

### Leave → Payroll Flow

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| LOP leave approved | Deduction calculated | ✅ per_day_salary * days | ✅ CORRECT |
| Casual leave approved | No deduction | ✅ Not deducted | ✅ CORRECT |
| Leave marked payroll_deducted | Not re-deducted | ✅ Flagged in DB | ✅ CORRECT |

### Expense → Payroll Flow

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| Expense approved, payroll_period set | Added to reimbursements | ✅ In earnings | ✅ CORRECT |
| Expense status updated | Marked "reimbursed" | ✅ Status changes | ✅ CORRECT |

---

## 7️⃣ DUPLICATE DATA SOURCE DETECTION

### Potential Duplications Identified

| Data Type | Sources | Risk Level | Recommendation |
|-----------|---------|------------|----------------|
| Employee Salary | `employees.salary` vs `ctc_structures.annual_ctc` | 🟡 MEDIUM | CTC should be source of truth |
| Attendance Days | `attendance` collection vs `payroll_inputs.present_days` | 🟢 LOW | Intentional override allowed |
| Bank Details | `employees.bank_details` vs `employees.bank_*` fields | 🟡 MEDIUM | Consolidate to bank_details object |

### Analysis

1. **Employee Salary Duplication:**
   - `employees.salary` stores monthly gross
   - `ctc_structures.annual_ctc / 12` also represents monthly
   - **Current behavior:** CTC takes priority if approved, else uses employee.salary
   - **Status:** ✅ HANDLED correctly in code

2. **Bank Details:**
   - Some employees have `bank_account_number`, `bank_name`, `ifsc_code` as top-level fields
   - Others have nested `bank_details` object
   - **Current behavior:** Payroll checks both (line 507-509)
   - **Recommendation:** Standardize to nested object

---

## 8️⃣ MOBILE APP INTEGRATION TEST

### Mobile Data Sources

| Feature | API Used | DB Table | Payroll Impact | Status |
|---------|----------|----------|----------------|--------|
| Attendance Check-in | `/api/attendance/check-in` | `attendance` | Working days | ✅ INTEGRATED |
| Leave Request | `/api/leave-requests` | `leave_requests` | LOP calculation | ✅ INTEGRATED |
| Expense Claim | `/api/expenses` | `expenses` | Reimbursements | ✅ INTEGRATED |
| Travel Claim | `/api/travel-claims` | `travel_claims` | Reimbursements | ✅ INTEGRATED |

### Test Results

| Mobile Action | Payroll Reflection | Status |
|--------------|-------------------|--------|
| Check-in via selfie | Attendance count updated | ✅ PASS |
| Submit leave via mobile | Leave request created | ✅ PASS |
| Submit expense via mobile | Expense added to queue | ✅ PASS |

---

## 9️⃣ PAYROLL CALCULATION ENGINE VERIFICATION

### Salary Slip Formula

```
GROSS SALARY = Basic + HRA + Special Allowance + Conveyance + Medical + Other Earnings

DEDUCTIONS = PF (Employee) + Professional Tax + ESI + LOP + Penalty + Advance

REIMBURSEMENTS = Approved Expenses + Travel Claims

NET SALARY = GROSS + Reimbursements - Deductions
```

### Calculation Accuracy Test

| Component | Formula | Example (CTC: 6,00,000) | Verified |
|-----------|---------|------------------------|----------|
| Basic (40%) | annual_ctc * 0.40 / 12 | ₹20,000/month | ✅ |
| HRA (50% of Basic) | basic * 0.50 | ₹10,000/month | ✅ |
| Special Allowance | Balance after other components | Variable | ✅ |
| PF (12% of Basic) | basic * 0.12 | ₹2,400/month | ✅ |
| Professional Tax | Fixed | ₹200/month | ✅ |
| LOP Deduction | (gross / working_days) * lop_days | Per day basis | ✅ |
| Overtime | (gross / 30 / 8) * hours * 1.5 | 1.5x rate | ✅ |

---

## 🔟 WORKFLOW ANALYSIS

### Current Workflow

```
1. HR Manager → CTC Designer → Create salary structure
2. Admin → Approvals Center → Approve CTC
3. HR → Go-Live Dashboard → Activate employee
4. Employee → Mobile App → Check-in daily
5. Employee → Mobile App → Submit leave/expense
6. HR → Approvals Center → Approve leave/expense
7. HR → Payroll Dashboard → Enter payroll inputs
8. HR → Payroll Dashboard → Generate salary slips
9. Admin → Payroll Reports → Review & approve
10. Finance → Bank Transfer → Disburse salaries
```

### Workflow Gaps Identified

| Issue | Impact | Priority | Fix Needed |
|-------|--------|----------|------------|
| No payroll approval workflow | Slips can be generated without review | 🟡 MEDIUM | Add approval step |
| No payroll locking | Data can change after slip generation | 🟡 MEDIUM | Add lock mechanism |
| Manual expense-to-payroll linking | HR must set payroll_period | 🟢 LOW | Auto-detect from date |

---

## 1️⃣1️⃣ ERROR PREVENTION ANALYSIS

### Validation Rules in Place

| Validation | Location | Status |
|------------|----------|--------|
| Employee must be Go-Live Active | `payroll.py:254-260` | ✅ IMPLEMENTED |
| Employee must have salary > 0 | `payroll.py:262-264` | ✅ IMPLEMENTED |
| Cannot generate own slip | `payroll.py:245-248` | ✅ IMPLEMENTED |
| Payroll inputs require all fields | `payroll.py:160-163` | ✅ IMPLEMENTED |
| Leave balance check | `leave_requests.py:99-100` | ✅ IMPLEMENTED |

### Missing Validations

| Validation Needed | Risk | Priority |
|-------------------|------|----------|
| Duplicate slip prevention | Overwrite without warning | 🟡 MEDIUM |
| Bank details required for disbursement | Payment fails | 🟡 MEDIUM |
| Attendance gaps detection | Inaccurate days | 🟢 LOW |
| Retroactive attendance check | Data integrity | 🟢 LOW |

---

## 1️⃣2️⃣ RECOMMENDATIONS

### High Priority Fixes

1. **Add Payroll Approval Flow**
   - Add `payroll_status` field: draft → submitted → approved → disbursed
   - Only approved payroll should be disbursed

2. **Add Payroll Locking**
   - Lock attendance/leave/expense changes after payroll generation
   - Allow unlock only by Admin with reason

3. **Bank Details Validation**
   - Block salary slip generation if bank details missing
   - Show warning in Go-Live checklist

### Medium Priority Improvements

4. **Standardize Bank Details Schema**
   ```javascript
   bank_details: {
     account_number: string,
     bank_name: string,
     ifsc_code: string,
     account_type: enum
   }
   ```

5. **Auto-link Expenses to Payroll Period**
   - Detect month from `expense_date`
   - Set `payroll_period` automatically

6. **Payroll Dashboard Enhancements**
   - Add "Linkage Summary" view
   - Show unlinked attendance days
   - Show pending expense approvals

### Low Priority Enhancements

7. **Attendance Gap Detection**
   - Highlight missing days in payroll inputs
   - Suggest marking as leave/absent

8. **Payroll Comparison Report**
   - Month-over-month comparison
   - Variance analysis

---

## 1️⃣3️⃣ SUMMARY SCORECARD

| Category | Score | Notes |
|----------|-------|-------|
| Data Integrity | 8/10 | Good linkage, minor duplication |
| Calculation Accuracy | 9/10 | All formulas verified |
| Module Integration | 9/10 | Well-connected modules |
| Validation Coverage | 7/10 | Missing some edge cases |
| Workflow Completeness | 7/10 | No approval/lock mechanism |
| Mobile Integration | 9/10 | Fully integrated |
| Error Prevention | 7/10 | Basic validations present |
| **Overall** | **8/10** | Production-ready with improvements |

---

## 1️⃣4️⃣ FILES ANALYZED

```
Backend:
- /app/backend/routers/payroll.py (975 lines)
- /app/backend/routers/ctc.py (564 lines)
- /app/backend/routers/attendance.py (1113 lines)
- /app/backend/routers/leave_requests.py (347 lines)
- /app/backend/routers/expenses.py (1297 lines)
- /app/backend/services/leave_balance_service.py
- /app/backend/services/ctc_history_service.py

Frontend:
- /app/frontend/src/pages/Payroll.js (590 lines)
- /app/frontend/src/pages/MySalarySlips.js
- /app/frontend/src/pages/CTCDesigner.js
- /app/frontend/src/pages/Attendance.js
- /app/frontend/src/pages/LeaveManagement.js
- /app/frontend/src/pages/Expenses.js
- /app/frontend/src/hooks/usePayroll.js

Hooks:
- /app/frontend/src/hooks/usePayroll.js
- /app/frontend/src/hooks/useAttendance.js
- /app/frontend/src/hooks/useLeaves.js
- /app/frontend/src/hooks/useExpenses.js
```

---

**Audit Complete**  
**Next Steps:** Implement high-priority recommendations before production deployment.
