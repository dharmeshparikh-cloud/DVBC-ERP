# MOM Workflow - Product Requirements Document

## Business Rules & Policies - COMPLETE ✅

### Rule Impact Simulation Feature (NEW)
Shows real-world examples with CTC impact for each rule type:

#### LIMIT Rules
- **Example 1 (Within Limit):** Employee CTC ₹8L, requests 20000 days → APPROVED
- **Example 2 (Exceeds Limit):** Employee CTC ₹12L, claims ₹75,000 vs ₹50,000 limit → REJECTED

#### THRESHOLD Rules
- **Example 1 (Below):** Expense ₹300 auto-approved (threshold ₹500)
- **Example 2 (Above):** 5 late arrivals vs 3 threshold → PENALTY (1 day LOP = ₹1,333)

#### FORMULA Rules  
- **Example 1 (PF):** Basic ₹33,333 × 12% = ₹4,000/month PF contribution
- **Example 2 (LOP):** Basic/30 × 3 LOP days = ₹4,000 deduction

#### CONDITION Rules
- **Example 1 (Met):** Manager + 5hr travel → Business class allowed
- **Example 2 (Not Met):** Developer + 5hr travel → Economy only

#### APPROVAL Rules
- **Example 1 (Correct):** Employee → Manager approval → APPROVED
- **Example 2 (Blocked):** Manager self-approve → BLOCKED → redirected to HR

### CTC Components Affected by Rule Type
| Rule Type | CTC Components |
|-----------|----------------|
| FORMULA | Basic, PF, ESI, Gross |
| LIMIT | Reimbursements, Encashment, Travel |
| THRESHOLD | LOP, Attendance Bonus, Overtime |
| CONDITION | Allowances, Grade Benefits |
| APPROVAL | Expense Reimbursements, Leave |

---

### Form Features
1. **Rule Type** - LIMIT, THRESHOLD, CONDITION, FORMULA, APPROVAL
2. **Category** - Policy-specific (8-10 per type)
3. **Applies To** - All Employees, By Dept/Role/Grade/Location/CTC
4. **Unit** - 25 options (days/year, INR, percent, etc.)
5. **Value Templates** - Formula-specific dropdowns
6. **Condition Builder** - 17 fields × 10 operators
7. **Rule Preview** - Live preview
8. **Impact Simulation** - 2 examples per rule type with CTC calculations
9. **Apply Rule & Close** - One-click save and close

---

## Login Credentials
| Role | Employee ID | Password |
|------|-------------|----------|
| Admin | EMP001 | admin123 |
| HR Manager | EMP002 | hr123 |

---

## Last Updated
- Date: March 23, 2026
- Status: Rule Impact Simulation with CTC examples - COMPLETE
