# NETRA ERP - Product Requirements Document

## Payroll Engine - COMPLETE ✅ (March 23, 2026)

Production-grade payroll calculation system with field-level traceability.

### Key Features Implemented

#### 1. Payroll Calculation Engine
- **LOP Formula**: `(Gross Monthly / Actual Days in Month) × LOP Days`
  - March: 31 days, February: 28/29 days, April: 30 days
- **PF Calculation**: `min(Basic, ₹15,000) × 12%` (employee + employer)
- **ESI**: 0.75% employee + 3.25% employer (if gross ≤ ₹21,000)
- **Professional Tax**: Maharashtra slabs (₹0/₹175/₹200)
- **Earnings**: Basic (40%), HRA (20%), Special Allowance (40%)

#### 2. Field-Level Traceability
Every calculation stores:
- `input_values`: Raw input data
- `formula_used`: Exact formula applied
- `output_value`: Calculated result
- `rule_version`: Version of rule used

#### 3. HR Test Mode (Simulation)
- Select employee from dropdown
- Enter LOP days, bonus, incentive, penalty, overtime, reimbursements
- Click "Calculate Payroll" to simulate
- View breakdown with formulas (NOT saved to database)

#### 4. Run Payroll
- Calculates payroll for all active employees
- Creates draft payroll register
- Shows department-wise summary
- Flags errors for employees with missing data

#### 5. Approval Workflow
```
Draft → HR Manager Submit → Admin Approve → Locked
```
- HR Manager creates and submits
- Admin approves/rejects
- Locked payroll cannot be edited (adjustment entries only)

#### 6. Payroll Register
- Employee-wise breakdown with all components
- Export to CSV/Excel
- View calculation breakdown for each employee

### APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/payroll/engine/simulate` | POST | HR Test Mode simulation |
| `/api/payroll/engine/run` | POST | Run payroll for month |
| `/api/payroll/engine/register` | GET | Get payroll registers |
| `/api/payroll/engine/register/{month}/details` | GET | Detailed register |
| `/api/payroll/engine/breakdown/{emp}/{month}` | GET | Calculation breakdown |
| `/api/payroll/engine/submit-for-approval` | POST | HR submits for approval |
| `/api/payroll/engine/approve` | POST | Admin approves |
| `/api/payroll/engine/export/{month}` | GET | Export data |

### Files
- Backend Engine: `/app/backend/services/payroll_engine.py`
- Backend Router: `/app/backend/routers/payroll_engine_router.py`
- Frontend Page: `/app/frontend/src/pages/PayrollEngine.js`
- Frontend Hooks: `/app/frontend/src/hooks/usePayrollEngine.js`

---

## Business Rules & Policies - COMPLETE ✅

### Test My Rule Feature (March 23, 2026)
Interactive employee-based rule testing with auto-fill:

#### Employee Selection Dropdown
- Quick Select dropdown showing all active employees
- Format: `EMP_ID - Name (Department, ₹Annual CTC/yr)`
- Auto-fills: Employee Name, CTC, Basic Salary, Department, Role, Grade, Location
- Option to "Enter manually" for custom testing

#### Auto-Calculated Fields
- Basic Salary = 40% of Annual CTC (auto-calculated)
- LOP Daily Rate = Gross CTC Monthly / Actual Days in Month

### Rule Impact Simulation Feature
Shows real-world examples with CTC impact for each rule type:

#### FORMULA Rules  
- **Example 1 (PF):** Basic ₹33,333 × 12% = ₹4,000/month PF contribution
- **Example 2 (LOP):** Gross CTC/31 × 3 LOP days = ₹6,290 deduction (Uses Actual Days)

---

## Login Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |
| Sales | EMP003 | sales123 |
| Consultant | EMP004 | consultant123 |

---

## Test Reports
- `/app/test_reports/iteration_199.json` - Payroll Engine (18 tests passed)
- `/app/test_reports/iteration_198.json` - Business Rules CRUD
- `/app/test_reports/iteration_197.json` - Rule Stress Test (54 rules)

---

## Last Updated
- Date: March 23, 2026
- Status: Payroll Engine with Field-Level Traceability - COMPLETE
