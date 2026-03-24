"""
Payroll Calculation Engine - SINGLE SOURCE OF TRUTH

This engine handles:
1. Field-level traceability (input → formula → output)
2. Versioned rule application
3. LOP calculation: Gross Monthly / Actual Days in Month
4. Statutory deductions (PF, ESI, PT)
5. Simulation and bulk processing

CRITICAL: All payroll calculations MUST go through this engine.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import calendar
import uuid
import logging

logger = logging.getLogger(__name__)


class PayrollCalculationEngine:
    """
    Production-grade payroll calculation engine with full traceability.
    
    Every calculation stores:
    - input_value: Raw input data
    - formula_used: Exact formula applied
    - output_value: Calculated result
    - rule_version: Version of rule used
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.calculation_log = []  # Stores all calculations for traceability
        
    def _get_days_in_month(self, month_str: str) -> int:
        """Get actual days in month (28/29/30/31)"""
        try:
            year, month = map(int, month_str.split('-'))
            return calendar.monthrange(year, month)[1]
        except (ValueError, AttributeError):
            return 30
    
    def _log_calculation(
        self,
        component_name: str,
        input_values: Dict[str, Any],
        formula: str,
        output_value: float,
        rule_id: str = None,
        rule_version: str = "1.0"
    ) -> Dict[str, Any]:
        """Log a calculation with full traceability"""
        calc_entry = {
            "id": str(uuid.uuid4()),
            "component_name": component_name,
            "input_values": input_values,
            "formula_used": formula,
            "output_value": round(output_value, 2),
            "rule_id": rule_id,
            "rule_version": rule_version,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
        self.calculation_log.append(calc_entry)
        return calc_entry
    
    def _safe_divide(self, numerator: float, denominator: float, default: float = 0) -> float:
        """Safe division with fallback"""
        if denominator == 0:
            return default
        return numerator / denominator
    
    async def get_active_rules(self, effective_date: str = None) -> Dict[str, Any]:
        """
        Get all active payroll rules.
        Returns rules indexed by component key.
        """
        if not effective_date:
            effective_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Get from business_policies (payroll type)
        payroll_policy = await self.db.business_policies.find_one(
            {"policy_type": "payroll", "is_active": True},
            {"_id": 0}
        )
        
        rules = {}
        if payroll_policy:
            for rule in payroll_policy.get("rules", []):
                if rule.get("is_enabled", True):
                    rules[rule.get("rule_id")] = {
                        **rule,
                        "version": payroll_policy.get("version", "1.0"),
                        "effective_date": payroll_policy.get("effective_date", effective_date)
                    }
        
        # Also get versioned rules from payroll_rules collection
        versioned_rules = await self.db.payroll_rules.find(
            {
                "status": "active",
                "effective_date": {"$lte": effective_date}
            },
            {"_id": 0}
        ).sort("effective_date", -1).to_list(100)
        
        for rule in versioned_rules:
            rule_key = rule.get("component_key") or rule.get("rule_id")
            if rule_key and rule_key not in rules:
                rules[rule_key] = rule
        
        return rules
    
    async def calculate_lop(
        self,
        gross_monthly: float,
        lop_days: float,
        month: str,
        working_days: int = None
    ) -> Dict[str, Any]:
        """
        Calculate Loss of Pay deduction.
        
        Formula: (Gross Monthly / Actual Days in Month) × LOP Days
        
        Returns calculation with full traceability.
        """
        actual_days = self._get_days_in_month(month)
        
        # Use actual days in month for daily salary calculation
        daily_salary = self._safe_divide(gross_monthly, actual_days)
        lop_amount = daily_salary * lop_days
        
        formula = f"(₹{gross_monthly:,.2f} / {actual_days} days) × {lop_days} LOP days"
        
        calc = self._log_calculation(
            component_name="LOP Deduction",
            input_values={
                "gross_monthly": gross_monthly,
                "actual_days_in_month": actual_days,
                "lop_days": lop_days,
                "daily_salary": round(daily_salary, 2)
            },
            formula=formula,
            output_value=lop_amount,
            rule_id="LOP_DEDUCTION",
            rule_version="2.0"
        )
        
        return {
            "amount": round(lop_amount, 2),
            "daily_rate": round(daily_salary, 2),
            "days": lop_days,
            "calculation": calc
        }
    
    async def calculate_pf(
        self,
        basic_monthly: float,
        pf_ceiling: float = 15000
    ) -> Dict[str, Any]:
        """
        Calculate Provident Fund.
        
        Formula: min(Basic, ₹15,000) × 12%
        Both employee and employer contribute equally.
        """
        pf_base = min(basic_monthly, pf_ceiling)
        pf_percentage = 12
        pf_amount = pf_base * (pf_percentage / 100)
        
        formula = f"min(₹{basic_monthly:,.2f}, ₹{pf_ceiling:,.2f}) × {pf_percentage}%"
        
        calc = self._log_calculation(
            component_name="PF Deduction",
            input_values={
                "basic_monthly": basic_monthly,
                "pf_ceiling": pf_ceiling,
                "pf_base": pf_base,
                "pf_percentage": pf_percentage
            },
            formula=formula,
            output_value=pf_amount,
            rule_id="PF_EMPLOYEE",
            rule_version="1.0"
        )
        
        return {
            "employee_contribution": round(pf_amount, 2),
            "employer_contribution": round(pf_amount, 2),
            "pf_base": round(pf_base, 2),
            "calculation": calc
        }
    
    async def calculate_esi(
        self,
        gross_monthly: float,
        esi_ceiling: float = 21000
    ) -> Dict[str, Any]:
        """
        Calculate ESI (Employee State Insurance).
        
        Applicable only if gross <= ₹21,000
        Employee: 0.75%, Employer: 3.25%
        """
        if gross_monthly > esi_ceiling:
            return {
                "employee_contribution": 0,
                "employer_contribution": 0,
                "applicable": False,
                "reason": f"Gross ₹{gross_monthly:,.2f} exceeds ESI ceiling ₹{esi_ceiling:,.2f}"
            }
        
        employee_rate = 0.75
        employer_rate = 3.25
        
        employee_esi = gross_monthly * (employee_rate / 100)
        employer_esi = gross_monthly * (employer_rate / 100)
        
        formula = f"₹{gross_monthly:,.2f} × {employee_rate}%"
        
        calc = self._log_calculation(
            component_name="ESI Deduction",
            input_values={
                "gross_monthly": gross_monthly,
                "esi_ceiling": esi_ceiling,
                "employee_rate": employee_rate,
                "employer_rate": employer_rate
            },
            formula=formula,
            output_value=employee_esi,
            rule_id="ESI_EMPLOYEE",
            rule_version="1.0"
        )
        
        return {
            "employee_contribution": round(employee_esi, 2),
            "employer_contribution": round(employer_esi, 2),
            "applicable": True,
            "calculation": calc
        }
    
    async def calculate_professional_tax(
        self,
        gross_monthly: float,
        state: str = "Gujarat"
    ) -> Dict[str, Any]:
        """
        Calculate Professional Tax based on state slabs.
        
        Gujarat PT Slabs (default):
        - Up to ₹5,999: Nil
        - ₹6,000 to ₹8,999: ₹80
        - ₹9,000 to ₹11,999: ₹150
        - ₹12,000 and above: ₹200
        
        Maharashtra PT Slabs (for reference):
        - Up to ₹7,500: Nil
        - ₹7,501 to ₹10,000: ₹175
        - Above ₹10,000: ₹200
        """
        pt_amount = 0
        slab_used = ""
        
        if state.lower() == "gujarat":
            # Gujarat PT slabs
            if gross_monthly < 6000:
                pt_amount = 0
                slab_used = "Up to ₹5,999 - Nil"
            elif gross_monthly < 9000:
                pt_amount = 80
                slab_used = "₹6,000 to ₹8,999 - ₹80"
            elif gross_monthly < 12000:
                pt_amount = 150
                slab_used = "₹9,000 to ₹11,999 - ₹150"
            else:
                pt_amount = 200
                slab_used = "₹12,000 and above - ₹200"
        elif state.lower() == "maharashtra":
            # Maharashtra PT slabs
            if gross_monthly <= 7500:
                pt_amount = 0
                slab_used = "Up to ₹7,500 - Nil"
            elif gross_monthly <= 10000:
                pt_amount = 175
                slab_used = "₹7,501 to ₹10,000 - ₹175"
            else:
                pt_amount = 200
                slab_used = "Above ₹10,000 - ₹200 (max)"
        else:
            # Default Gujarat
            if gross_monthly >= 12000:
                pt_amount = 200
                slab_used = f"{state} - Default ₹200"
        
        formula = f"Gross ₹{gross_monthly:,.2f} → {state} Slab: {slab_used}"
        
        calc = self._log_calculation(
            component_name="Professional Tax",
            input_values={
                "gross_monthly": gross_monthly,
                "state": state,
                "slab_used": slab_used
            },
            formula=formula,
            output_value=pt_amount,
            rule_id="PROFESSIONAL_TAX_GUJARAT",
            rule_version="2.0"
        )
        
        return {
            "amount": round(pt_amount, 2),
            "state": state,
            "slab": slab_used,
            "calculation": calc
        }
    
    async def calculate_tds(
        self,
        gross_annual: float,
        regime: str = "new"
    ) -> Dict[str, Any]:
        """
        Calculate TDS (Tax Deduction at Source) based on income tax slabs.
        
        Finance Act 2025 - New Tax Regime (FY 2025-26):
        
        Tax Slabs:
        - Up to ₹4,00,000: Nil
        - ₹4,00,001 to ₹8,00,000: 5%
        - ₹8,00,001 to ₹12,00,000: 10%
        - ₹12,00,001 to ₹16,00,000: 15%
        - ₹16,00,001 to ₹20,00,000: 20%
        - ₹20,00,001 to ₹24,00,000: 25%
        - Above ₹24,00,000: 30%
        
        Standard Deduction (Section 16ia): ₹75,000
        
        Section 87A Rebate (FY 2025-26):
        - If taxable income ≤ ₹12,00,000: Full rebate up to ₹60,000
        - Effectively zero tax up to ₹12,75,000 gross income
        """
        standard_deduction = 75000
        taxable_income = max(0, gross_annual - standard_deduction)
        
        # Calculate tax based on FY 2025-26 slabs
        tax = 0
        slab_details = []
        remaining = taxable_income
        
        # Finance Act 2025 - New Tax Regime Slabs
        slabs = [
            (400000, 0, "Up to ₹4L"),
            (400000, 5, "₹4L - ₹8L @ 5%"),
            (400000, 10, "₹8L - ₹12L @ 10%"),
            (400000, 15, "₹12L - ₹16L @ 15%"),
            (400000, 20, "₹16L - ₹20L @ 20%"),
            (400000, 25, "₹20L - ₹24L @ 25%"),
            (float('inf'), 30, "Above ₹24L @ 30%")
        ]
        
        for limit, rate, desc in slabs:
            if remaining <= 0:
                break
            taxable_in_slab = min(remaining, limit)
            tax_in_slab = taxable_in_slab * (rate / 100)
            if tax_in_slab > 0:
                slab_details.append(f"{desc}: ₹{tax_in_slab:,.0f}")
            tax += tax_in_slab
            remaining -= taxable_in_slab
        
        # Section 87A Rebate - Finance Act 2025 (FY 2025-26)
        # If taxable income ≤ ₹12,00,000: Full rebate up to ₹60,000
        rebate_87a = 0
        rebate_limit = 1200000  # ₹12 Lakh threshold
        max_rebate = 60000     # Maximum rebate amount (₹60,000)
        
        tax_before_rebate = tax
        if regime == "new" and taxable_income <= rebate_limit:
            rebate_87a = min(tax, max_rebate)  # Rebate cannot exceed actual tax
            tax = max(0, tax - rebate_87a)
            if rebate_87a > 0:
                slab_details.append(f"87A Rebate: -₹{rebate_87a:,.0f}")
        
        # Add 4% health & education cess (on tax AFTER rebate)
        cess = tax * 0.04
        total_tax = tax + cess
        
        # Monthly TDS
        monthly_tds = total_tax / 12
        
        formula = f"Annual: ₹{gross_annual:,.0f} - SD ₹{standard_deduction:,.0f} = ₹{taxable_income:,.0f} taxable"
        if rebate_87a > 0:
            formula += f" | 87A Rebate: ₹{rebate_87a:,.0f} (Zero Tax)"
        
        calc = self._log_calculation(
            component_name="TDS (Income Tax)",
            input_values={
                "gross_annual": gross_annual,
                "standard_deduction": standard_deduction,
                "taxable_income": taxable_income,
                "regime": regime,
                "tax_before_rebate": round(tax_before_rebate, 2),
                "rebate_87a": round(rebate_87a, 2),
                "tax_after_rebate": round(tax, 2),
                "cess_4_percent": round(cess, 2),
                "finance_act": "2025",
                "fy": "2025-26"
            },
            formula=formula,
            output_value=monthly_tds,
            rule_id="TDS_NEW_REGIME_87A_FY2025",
            rule_version="3.0"
        )
        
        return {
            "monthly_tds": round(monthly_tds, 2),
            "annual_tax": round(total_tax, 2),
            "taxable_income": round(taxable_income, 2),
            "rebate_87a": round(rebate_87a, 2),
            "tax_before_rebate": round(tax_before_rebate, 2),
            "slab_breakdown": slab_details,
            "regime": regime,
            "finance_act": "2025",
            "calculation": calc
        }
    
    # ==================== F&F CALCULATIONS ====================
    
    async def calculate_gratuity(
        self,
        basic_monthly: float,
        da_monthly: float,
        tenure_years: float,
        tenure_months: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate Gratuity as per Payment of Gratuity Act, 1972.
        
        Formula: (Basic + DA) × 15 × Years of Service / 26
        
        Eligibility: Minimum 5 years of continuous service
        Maximum: ₹20,00,000 (as per 2019 amendment)
        """
        total_tenure_years = tenure_years + (tenure_months / 12)
        
        # Eligibility check
        eligible = total_tenure_years >= 5
        
        if not eligible:
            return {
                "amount": 0,
                "eligible": False,
                "reason": f"Minimum 5 years required. Current tenure: {total_tenure_years:.2f} years",
                "tenure_years": round(total_tenure_years, 2)
            }
        
        # Gratuity calculation
        last_drawn = basic_monthly + da_monthly
        gratuity = (last_drawn * 15 * total_tenure_years) / 26
        
        # Cap at maximum
        max_gratuity = 2000000  # ₹20 Lakhs
        final_gratuity = min(gratuity, max_gratuity)
        capped = gratuity > max_gratuity
        
        formula = f"(₹{last_drawn:,.0f} × 15 × {total_tenure_years:.2f}) / 26 = ₹{gratuity:,.2f}"
        if capped:
            formula += f" (Capped at ₹{max_gratuity:,})"
        
        calc = self._log_calculation(
            component_name="Gratuity",
            input_values={
                "basic_monthly": basic_monthly,
                "da_monthly": da_monthly,
                "last_drawn": last_drawn,
                "tenure_years": total_tenure_years
            },
            formula=formula,
            output_value=final_gratuity,
            rule_id="GRATUITY_ACT_1972",
            rule_version="1.0"
        )
        
        return {
            "amount": round(final_gratuity, 2),
            "eligible": True,
            "tenure_years": round(total_tenure_years, 2),
            "last_drawn": round(last_drawn, 2),
            "capped": capped,
            "formula": formula,
            "calculation": calc
        }
    
    async def calculate_leave_encashment(
        self,
        basic_monthly: float,
        leave_balance: Dict[str, float],
        encashment_policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate Leave Encashment based on policy.
        
        Default Policy:
        - Earned/Privilege Leave: Fully encashable
        - Casual Leave: Not encashable (lapses)
        - Sick Leave: Not encashable (lapses)
        - Compensatory Off: Encashable if policy allows
        
        Formula: (Basic / 30) × Encashable Leave Days
        """
        per_day_rate = basic_monthly / 30
        
        # Get encashment rules from policy
        encashable_types = encashment_policy.get("encashable_leave_types", ["earned", "privilege", "el", "pl"])
        max_encashable_days = encashment_policy.get("max_encashable_days", 300)  # Lifetime cap
        
        total_encashable = 0
        breakdown = {}
        
        for leave_type, balance in leave_balance.items():
            leave_type_lower = leave_type.lower()
            if any(enc_type in leave_type_lower for enc_type in encashable_types):
                encashable_days = min(balance, max_encashable_days - total_encashable)
                if encashable_days > 0:
                    breakdown[leave_type] = {
                        "balance": balance,
                        "encashable": encashable_days,
                        "amount": round(encashable_days * per_day_rate, 2)
                    }
                    total_encashable += encashable_days
            else:
                breakdown[leave_type] = {
                    "balance": balance,
                    "encashable": 0,
                    "amount": 0,
                    "reason": "Not encashable as per policy"
                }
        
        total_amount = total_encashable * per_day_rate
        
        formula = f"(₹{basic_monthly:,.0f} / 30) × {total_encashable} days = ₹{total_amount:,.2f}"
        
        calc = self._log_calculation(
            component_name="Leave Encashment",
            input_values={
                "basic_monthly": basic_monthly,
                "per_day_rate": per_day_rate,
                "leave_balance": leave_balance,
                "total_encashable_days": total_encashable
            },
            formula=formula,
            output_value=total_amount,
            rule_id="LEAVE_ENCASHMENT",
            rule_version="1.0"
        )
        
        return {
            "amount": round(total_amount, 2),
            "total_encashable_days": total_encashable,
            "per_day_rate": round(per_day_rate, 2),
            "breakdown": breakdown,
            "calculation": calc
        }
    
    async def calculate_notice_period(
        self,
        gross_monthly: float,
        notice_period_days: int,
        days_served: int,
        is_employee_resignation: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate Notice Period Recovery/Payment.
        
        If employee resigns and doesn't serve full notice:
        - Recovery = (Gross / 30) × Shortfall Days
        
        If company terminates without notice:
        - Payment = (Gross / 30) × Notice Period Days
        """
        per_day_rate = gross_monthly / 30
        shortfall_days = max(0, notice_period_days - days_served)
        
        if is_employee_resignation:
            # Employee resigned - check if notice served
            if shortfall_days > 0:
                recovery_amount = shortfall_days * per_day_rate
                return {
                    "type": "recovery",
                    "amount": round(recovery_amount, 2),
                    "notice_period_days": notice_period_days,
                    "days_served": days_served,
                    "shortfall_days": shortfall_days,
                    "per_day_rate": round(per_day_rate, 2),
                    "formula": f"(₹{gross_monthly:,.0f} / 30) × {shortfall_days} = ₹{recovery_amount:,.2f}"
                }
            else:
                return {
                    "type": "none",
                    "amount": 0,
                    "notice_period_days": notice_period_days,
                    "days_served": days_served,
                    "message": "Full notice period served"
                }
        else:
            # Company termination - pay notice period
            payment_amount = notice_period_days * per_day_rate
            return {
                "type": "payment",
                "amount": round(payment_amount, 2),
                "notice_period_days": notice_period_days,
                "per_day_rate": round(per_day_rate, 2),
                "formula": f"(₹{gross_monthly:,.0f} / 30) × {notice_period_days} = ₹{payment_amount:,.2f}"
            }
    
    async def calculate_loan_emi_schedule(
        self,
        loan_amount: float,
        tenure_months: int,
        interest_rate: float = 0  # Annual interest rate (0 for interest-free)
    ) -> Dict[str, Any]:
        """
        Calculate Loan/Advance EMI schedule for payroll deduction.
        
        Supports:
        - Interest-free advances (simple division)
        - Interest-bearing loans (EMI formula)
        
        Tenure: 1-6 months configurable
        """
        if tenure_months < 1 or tenure_months > 6:
            return {
                "error": True,
                "message": "Tenure must be between 1 and 6 months"
            }
        
        if interest_rate == 0:
            # Interest-free advance - simple division
            monthly_emi = loan_amount / tenure_months
            total_payable = loan_amount
            total_interest = 0
        else:
            # EMI calculation with interest
            monthly_rate = interest_rate / 12 / 100
            emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
            monthly_emi = emi
            total_payable = emi * tenure_months
            total_interest = total_payable - loan_amount
        
        # Generate schedule
        schedule = []
        remaining = loan_amount
        for month in range(1, tenure_months + 1):
            principal = loan_amount / tenure_months if interest_rate == 0 else monthly_emi - (remaining * (interest_rate / 12 / 100))
            interest = 0 if interest_rate == 0 else remaining * (interest_rate / 12 / 100)
            remaining = max(0, remaining - principal)
            schedule.append({
                "month": month,
                "emi": round(monthly_emi, 2),
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "remaining": round(remaining, 2)
            })
        
        return {
            "loan_amount": loan_amount,
            "tenure_months": tenure_months,
            "interest_rate": interest_rate,
            "monthly_emi": round(monthly_emi, 2),
            "total_payable": round(total_payable, 2),
            "total_interest": round(total_interest, 2),
            "schedule": schedule
        }
    
    async def fetch_approved_expenses(
        self,
        employee_id: str,
        month: str
    ) -> Dict[str, Any]:
        """
        Fetch approved expense reimbursements for an employee for a month.
        Auto-integrates with expense module.
        """
        year, mon = map(int, month.split('-'))
        start_date = f"{year}-{mon:02d}-01"
        if mon == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{mon + 1:02d}-01"
        
        # Fetch approved expenses
        expenses = await self.db.expenses.find({
            "employee_id": employee_id,
            "status": "approved",
            "submitted_date": {"$gte": start_date, "$lt": end_date}
        }, {"_id": 0}).to_list(100)
        
        # Categorize expenses
        categories = {
            "travel": 0,
            "medical": 0,
            "food": 0,
            "telephone": 0,
            "internet": 0,
            "other": 0
        }
        
        total = 0
        expense_list = []
        
        for exp in expenses:
            amount = exp.get("amount", 0)
            category = exp.get("category", "other").lower()
            
            if category in categories:
                categories[category] += amount
            else:
                categories["other"] += amount
            
            total += amount
            expense_list.append({
                "id": exp.get("id"),
                "category": category,
                "amount": amount,
                "description": exp.get("description", ""),
                "approved_date": exp.get("approved_date")
            })
        
        return {
            "total": round(total, 2),
            "categories": {k: round(v, 2) for k, v in categories.items()},
            "expense_count": len(expense_list),
            "expenses": expense_list
        }
    
    async def calculate_prorata_salary(
        self,
        gross_monthly: float,
        joining_date: str,
        month: str
    ) -> Dict[str, Any]:
        """
        Calculate pro-rata salary for mid-month joiners.
        
        Formula: (Gross / Days in Month) x Working Days
        """
        from datetime import datetime
        import calendar
        
        year, mon = map(int, month.split('-'))
        days_in_month = calendar.monthrange(year, mon)[1]
        
        # Handle different date formats
        join_str = str(joining_date)[:10]  # Take YYYY-MM-DD portion
        try:
            join_dt = datetime.strptime(join_str, "%Y-%m-%d")
        except ValueError:
            try:
                join_dt = datetime.strptime(join_str, "%d-%m-%Y")
            except ValueError:
                return {
                    "gross_monthly": gross_monthly,
                    "days_in_month": days_in_month,
                    "working_days": days_in_month,
                    "joining_date": joining_date,
                    "is_prorata": False,
                    "prorata_salary": gross_monthly,
                    "formula": "Full month salary (unparseable date)"
                }
        
        join_year, join_month, join_day = join_dt.year, join_dt.month, join_dt.day
        
        # Check if joining in this month AND not on the 1st (1st = full month)
        if join_year == year and join_month == mon and join_day > 1:
            working_days = days_in_month - join_day + 1
            prorata_salary = (gross_monthly / days_in_month) * working_days
            is_prorata = True
        else:
            working_days = days_in_month
            prorata_salary = gross_monthly
            is_prorata = False
        
        return {
            "gross_monthly": gross_monthly,
            "days_in_month": days_in_month,
            "working_days": working_days,
            "joining_date": joining_date,
            "is_prorata": is_prorata,
            "prorata_salary": round(prorata_salary, 2),
            "formula": f"(INR {gross_monthly:,.0f} / {days_in_month}) x {working_days} = INR {prorata_salary:,.2f}" if is_prorata else "Full month salary"
        }
    
    async def apply_appraisal_increment(
        self,
        employee_id: str,
        current_ctc: float,
        effective_date: str
    ) -> Dict[str, Any]:
        """
        Fetch and apply appraisal increment from appraisals collection.
        """
        # Fetch latest approved appraisal
        appraisal = await self.db.appraisals.find_one({
            "employee_id": employee_id,
            "status": "approved",
            "effective_date": {"$lte": effective_date}
        }, {"_id": 0}, sort=[("effective_date", -1)])
        
        if not appraisal:
            return {
                "has_increment": False,
                "current_ctc": current_ctc,
                "new_ctc": current_ctc,
                "message": "No approved appraisal found"
            }
        
        increment_type = appraisal.get("increment_type", "percentage")
        increment_value = appraisal.get("increment_value", 0)
        
        if increment_type == "percentage":
            increment_amount = current_ctc * (increment_value / 100)
            new_ctc = current_ctc + increment_amount
        else:
            increment_amount = increment_value
            new_ctc = current_ctc + increment_value
        
        return {
            "has_increment": True,
            "current_ctc": current_ctc,
            "new_ctc": round(new_ctc, 2),
            "increment_amount": round(increment_amount, 2),
            "increment_percentage": round((increment_amount / current_ctc) * 100, 2),
            "effective_date": appraisal.get("effective_date"),
            "appraisal_id": appraisal.get("id")
        }

    async def fetch_attendance_summary(
        self,
        employee_id: str,
        month: str
    ) -> Dict[str, Any]:
        """
        Fetch comprehensive attendance summary for an employee for a month.
        Returns present, absent, leave (by type), weekly offs, public holidays breakdown.
        """
        year, mon = map(int, month.split('-'))
        start_date = f"{year}-{mon:02d}-01"
        end_date = f"{year}-{mon:02d}-{self._get_days_in_month(month):02d}"
        
        # Fetch attendance records
        attendance_records = await self.db.attendance.find({
            "employee_id": employee_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }, {"_id": 0}).to_list(50)
        
        # Fetch approved leaves with type breakdown
        leave_records = await self.db.leave_requests.find({
            "employee_id": employee_id,
            "status": "approved",
            "$or": [
                {"start_date": {"$gte": start_date, "$lte": end_date}},
                {"end_date": {"$gte": start_date, "$lte": end_date}}
            ]
        }, {"_id": 0}).to_list(20)
        
        # Fetch public holidays
        public_holidays = await self.db.holidays.find({
            "date": {"$gte": start_date, "$lte": end_date},
            "is_active": True
        }, {"_id": 0}).to_list(20)
        
        # Count days
        days_in_month = self._get_days_in_month(month)
        present_days = len([a for a in attendance_records if a.get("status") == "present"])
        half_days = len([a for a in attendance_records if a.get("status") == "half_day"])
        wfh_days = len([a for a in attendance_records if a.get("work_location") == "wfh"])
        absent_days = len([a for a in attendance_records if a.get("status") == "absent"])
        late_arrivals = len([a for a in attendance_records if a.get("late_arrival")])
        early_departures = len([a for a in attendance_records if a.get("early_departure")])
        
        # Leave type breakdown
        leave_breakdown = {
            "casual": 0,
            "sick": 0,
            "earned": 0,
            "privilege": 0,
            "maternity": 0,
            "paternity": 0,
            "compensatory": 0,
            "lwp": 0,  # Leave Without Pay
            "other": 0
        }
        
        total_leave_days = 0
        paid_leave_days = 0
        unpaid_leave_days = 0
        
        for leave in leave_records:
            leave_days = leave.get("days", 0) or leave.get("total_days", 0)
            leave_type = leave.get("leave_type", "other").lower()
            
            total_leave_days += leave_days
            
            if leave_type in leave_breakdown:
                leave_breakdown[leave_type] += leave_days
            else:
                leave_breakdown["other"] += leave_days
            
            # Paid leaves
            if leave_type in ["casual", "sick", "earned", "privilege", "maternity", "paternity", "compensatory"]:
                paid_leave_days += leave_days
            else:
                unpaid_leave_days += leave_days
        
        # Count weekends (Saturday, Sunday) separately from public holidays
        from datetime import date
        weekly_offs = 0
        for day in range(1, days_in_month + 1):
            d = date(year, mon, day)
            if d.weekday() in [5, 6]:  # Saturday=5, Sunday=6
                weekly_offs += 1
        
        # Public holidays count
        public_holiday_count = len(public_holidays)
        public_holiday_names = [h.get("name", "Holiday") for h in public_holidays]
        
        # Calculate working days and LOP
        total_holidays = weekly_offs + public_holiday_count
        working_days = days_in_month - total_holidays
        effective_present = present_days + (half_days * 0.5) + paid_leave_days
        calculated_lop = max(0, working_days - effective_present - unpaid_leave_days)
        
        # If no attendance records, use payroll input LOP
        if len(attendance_records) == 0:
            calculated_lop = 0  # Will be taken from payroll_input
        
        return {
            "days_in_month": days_in_month,
            "working_days": working_days,
            "weekly_offs": weekly_offs,
            "public_holidays": public_holiday_count,
            "public_holiday_names": public_holiday_names,
            "total_holidays": total_holidays,
            "present_days": present_days,
            "half_days": half_days,
            "wfh_days": wfh_days,
            "absent_days": absent_days,
            "late_arrivals": late_arrivals,
            "early_departures": early_departures,
            "total_leave_days": total_leave_days,
            "paid_leave_days": paid_leave_days,
            "unpaid_leave_days": unpaid_leave_days,
            "leave_breakdown": leave_breakdown,
            "calculated_lop": calculated_lop,
            "attendance_records": len(attendance_records)
        }
    
    async def fetch_rule_based_deductions(
        self,
        employee: Dict[str, Any],
        month: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch deductions from Business Rules based on employee violations.
        e.g., Late arrival penalties, travel policy violations, etc.
        
        Sources:
        1. employee_penalties collection (manual penalties)
        2. attendance_penalties collection (HR-approved attendance penalties)
        3. payroll_inputs.penalty field (if set during penalty approval)
        4. Late arrival auto-calculation from attendance records
        """
        employee_id = employee.get("id")
        deductions = []
        
        # === SOURCE 1: Manual penalties from employee_penalties ===
        # Includes both direct penalties for this month AND arrears carried forward to this month
        penalties = await self.db.employee_penalties.find({
            "$or": [
                {"employee_id": employee_id, "month": month, "status": "active", "is_arrears": {"$ne": True}},
                {"employee_id": employee_id, "effective_month": month, "status": "active", "is_arrears": True}
            ]
        }, {"_id": 0}).to_list(50)
        
        for penalty in penalties:
            is_arrear = penalty.get("is_arrears", False)
            arrear_label = f" [ARREARS from {penalty.get('original_month', '?')}]" if is_arrear else ""
            
            calc = self._log_calculation(
                component_name=f"{penalty.get('name', 'Penalty')}{arrear_label}",
                input_values={
                    "rule_id": penalty.get("rule_id"),
                    "reason": penalty.get("reason"),
                    "violation_count": penalty.get("violation_count", 1),
                    "penalty_source": "employee_penalties",
                    "is_arrears": is_arrear,
                    "original_month": penalty.get("original_month"),
                    "effective_month": penalty.get("effective_month")
                },
                formula=f"{'Arrears: ' if is_arrear else ''}Rule-based penalty",
                output_value=penalty.get("amount", 0),
                rule_id=penalty.get("rule_id", "PENALTY"),
                rule_version="1.0"
            )
            deductions.append({
                "key": f"penalty_{penalty.get('rule_id', 'unknown')}{'_arrears' if is_arrear else ''}",
                "name": f"{penalty.get('name', 'Policy Violation Penalty')}{arrear_label}",
                "amount": round(penalty.get("amount", 0), 2),
                "details": f"{penalty.get('reason', '')}{arrear_label}",
                "penalty_source": "employee_penalties",
                "is_arrears": is_arrear,
                "original_month": penalty.get("original_month"),
                "calculation": calc
            })
        
        # === SOURCE 2: Attendance penalties (HR-approved late arrival penalties) ===
        attendance_penalties = await self.db.attendance_penalties.find({
            "employee_id": employee_id,
            "month": month
        }, {"_id": 0}).to_list(10)
        
        for att_penalty in attendance_penalties:
            penalty_amount = att_penalty.get("penalty_amount", 0)
            penalty_days = att_penalty.get("penalty_days", 0)
            
            if penalty_amount > 0:
                calc = self._log_calculation(
                    component_name="Attendance Penalty",
                    input_values={
                        "penalty_days": penalty_days,
                        "penalty_amount": penalty_amount,
                        "approved_by": att_penalty.get("approved_by_name", "HR"),
                        "approved_at": att_penalty.get("created_at"),
                        "penalty_source": "attendance_penalties"
                    },
                    formula=f"HR-approved: {penalty_days} late days × ₹100/day",
                    output_value=penalty_amount,
                    rule_id="AT012",  # Late Penalty Amount rule
                    rule_version="1.0"
                )
                deductions.append({
                    "key": "attendance_penalty",
                    "name": "Attendance Penalty (Late Arrival)",
                    "amount": round(penalty_amount, 2),
                    "details": f"{penalty_days} days beyond grace limit (approved by {att_penalty.get('approved_by_name', 'HR')})",
                    "penalty_source": "attendance_penalties",
                    "calculation": calc
                })
        
        # === SOURCE 3: Check payroll_inputs for penalty (set by /apply-penalties) ===
        payroll_input = await self.db.payroll_inputs.find_one({
            "employee_id": employee_id,
            "month": month
        }, {"_id": 0})
        
        if payroll_input:
            # Check for attendance penalty in payroll_inputs (avoid double-counting)
            if payroll_input.get("attendance_penalty_applied") and len(attendance_penalties) == 0:
                # Only add if not already added from attendance_penalties
                penalty_amount = payroll_input.get("penalty", 0)
                penalty_days = payroll_input.get("attendance_penalty_days", 0)
                
                if penalty_amount > 0:
                    calc = self._log_calculation(
                        component_name="Attendance Penalty (Payroll Input)",
                        input_values={
                            "penalty_days": penalty_days,
                            "penalty_amount": penalty_amount,
                            "approved_by": payroll_input.get("attendance_penalty_approved_by"),
                            "penalty_source": "payroll_inputs"
                        },
                        formula=f"From payroll_inputs: {penalty_days} days",
                        output_value=penalty_amount,
                        rule_id="AT012",
                        rule_version="1.0"
                    )
                    deductions.append({
                        "key": "payroll_input_penalty",
                        "name": "Attendance Penalty",
                        "amount": round(penalty_amount, 2),
                        "details": f"{penalty_days} late days beyond grace",
                        "penalty_source": "payroll_inputs",
                        "calculation": calc
                    })
        
        # === SOURCE 4: Late arrival auto-calculation (fallback if no HR approval) ===
        # Only apply if no attendance_penalties and no payroll_input penalty
        if len(attendance_penalties) == 0 and (not payroll_input or not payroll_input.get("attendance_penalty_applied")):
            late_policy = await self.db.business_policies.find_one(
                {"policy_type": "attendance", "is_active": True, "scope": "company"},
                {"_id": 0}
            )
            
            if late_policy:
                rules = {r["rule_id"]: r for r in late_policy.get("rules", [])}
                
                # Get grace days and penalty amount from SSOT
                grace_days = rules.get("AT011", {}).get("numeric_value", 3)
                late_penalty_per_day = rules.get("AT012", {}).get("numeric_value", 100)
                
                # Check late arrivals for this month
                late_count = await self.db.attendance.count_documents({
                    "employee_id": employee_id,
                    "date": {"$regex": f"^{month}"},
                    "late_arrival": True
                })
                
                if late_count > grace_days:
                    excess_late = late_count - grace_days
                    auto_penalty = excess_late * late_penalty_per_day
                    
                    calc = self._log_calculation(
                        component_name="Late Arrival Penalty (Auto)",
                        input_values={
                            "late_count": late_count,
                            "grace_days": grace_days,
                            "excess_late": excess_late,
                            "penalty_per_day": late_penalty_per_day,
                            "penalty_source": "auto_calculated"
                        },
                        formula=f"{excess_late} excess × ₹{late_penalty_per_day}/day",
                        output_value=auto_penalty,
                        rule_id="AT012",
                        rule_version=late_policy.get("version", "1.0")
                    )
                    deductions.append({
                        "key": "late_arrival_penalty_auto",
                        "name": "Late Arrival Penalty (Pending Approval)",
                        "amount": round(auto_penalty, 2),
                        "details": f"{excess_late} late arrivals above {grace_days} grace days (auto-calculated, pending HR approval)",
                        "penalty_source": "auto_calculated",
                        "requires_approval": True,
                        "calculation": calc
                    })
        
        return deductions
    
    async def calculate_earnings(
        self,
        gross_monthly: float,
        ctc_components: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate all earning components.
        Uses CTC structure if available, otherwise default breakdown.
        """
        earnings = []
        
        if ctc_components:
            # Use CTC structure components
            for key, comp in ctc_components.items():
                if not comp.get("enabled", True):
                    continue
                if comp.get("is_earning", True) and not comp.get("is_deferred"):
                    monthly = comp.get("monthly", 0)
                    if monthly > 0:
                        calc = self._log_calculation(
                            component_name=comp.get("name", key),
                            input_values={"ctc_component": key, "monthly": monthly},
                            formula=f"CTC Component: {key}",
                            output_value=monthly,
                            rule_id=f"CTC_{key.upper()}",
                            rule_version="1.0"
                        )
                        earnings.append({
                            "key": key,
                            "name": comp.get("name", key),
                            "amount": round(monthly, 2),
                            "calculation": calc
                        })
        else:
            # Default breakdown: Basic 40%, HRA 20%, Special Allowance 40%
            basic = gross_monthly * 0.40
            hra = gross_monthly * 0.20
            special = gross_monthly * 0.40
            
            earnings = [
                {
                    "key": "basic",
                    "name": "Basic Salary",
                    "amount": round(basic, 2),
                    "calculation": self._log_calculation(
                        "Basic Salary",
                        {"gross_monthly": gross_monthly, "percentage": 40},
                        f"₹{gross_monthly:,.2f} × 40%",
                        basic, "BASIC", "1.0"
                    )
                },
                {
                    "key": "hra",
                    "name": "House Rent Allowance",
                    "amount": round(hra, 2),
                    "calculation": self._log_calculation(
                        "HRA",
                        {"gross_monthly": gross_monthly, "percentage": 20},
                        f"₹{gross_monthly:,.2f} × 20%",
                        hra, "HRA", "1.0"
                    )
                },
                {
                    "key": "special_allowance",
                    "name": "Special Allowance",
                    "amount": round(special, 2),
                    "calculation": self._log_calculation(
                        "Special Allowance",
                        {"gross_monthly": gross_monthly, "percentage": 40},
                        f"₹{gross_monthly:,.2f} × 40%",
                        special, "SPECIAL_ALLOWANCE", "1.0"
                    )
                }
            ]
        
        return earnings
    
    async def run_payroll_calculation(
        self,
        employee: Dict[str, Any],
        month: str,
        payroll_input: Dict[str, Any] = None,
        ctc_structure: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run complete payroll calculation for an employee.
        
        Returns:
        - Full breakdown with field-level traceability
        - Earnings, deductions, net salary
        - All calculation logs
        """
        self.calculation_log = []  # Reset log for this calculation
        
        # Extract employee data
        employee_id = employee.get("id")
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        gross_monthly = employee.get("salary", 0) or employee.get("gross_salary", 0) or 0
        
        if gross_monthly <= 0:
            return {
                "success": False,
                "error": "MISSING_SALARY",
                "error_message": f"Gross salary not configured for {employee_name}",
                "employee_id": employee_id
            }
        
        # Get payroll inputs (defaults if not provided)
        if not payroll_input:
            payroll_input = {}
        
        # === PAYROLL INPUT FIELDS ===
        lop_days = payroll_input.get("lop_days", 0) or payroll_input.get("absent_days", 0) or 0
        incentive = payroll_input.get("incentive", 0) or 0
        bonus = payroll_input.get("bonus", 0) or 0
        overtime_hours = payroll_input.get("overtime_hours", 0) or 0
        working_days = payroll_input.get("working_days", self._get_days_in_month(month))
        
        # Arrears (previous month adjustments)
        arrears = payroll_input.get("arrears", 0) or 0
        arrears_reason = payroll_input.get("arrears_reason", "")
        
        # === AUTO-FETCH APPROVED EXPENSES FROM EXPENSES MODULE ===
        # This integrates the Expenses module with Payroll (SSOT)
        auto_expenses = await self.fetch_approved_expenses(employee_id, month)
        expense_categories = auto_expenses.get("categories", {})
        
        # Expense Reimbursements (use auto-fetched values, allow manual override)
        travel_reimbursement = payroll_input.get("travel_reimbursement") or expense_categories.get("travel", 0)
        medical_reimbursement = payroll_input.get("medical_reimbursement") or expense_categories.get("medical", 0)
        food_reimbursement = payroll_input.get("food_reimbursement") or expense_categories.get("food", 0)
        telephone_reimbursement = payroll_input.get("telephone_reimbursement") or expense_categories.get("telephone", 0)
        other_reimbursement = payroll_input.get("other_reimbursement") or payroll_input.get("expense_reimbursement") or (expense_categories.get("internet", 0) + expense_categories.get("other", 0))
        total_reimbursements = travel_reimbursement + medical_reimbursement + food_reimbursement + telephone_reimbursement + other_reimbursement
        
        # Deduction inputs
        advance_recovery = payroll_input.get("advance_recovery", 0) or payroll_input.get("advance", 0) or 0
        advance_reason = payroll_input.get("advance_reason", "")
        loan_emi = payroll_input.get("loan_emi", 0) or 0
        loan_type = payroll_input.get("loan_type", "")
        penalty = payroll_input.get("penalty", 0) or 0
        penalty_reason = payroll_input.get("penalty_reason", "")
        other_deduction = payroll_input.get("other_deduction", 0) or 0
        other_deduction_name = payroll_input.get("other_deduction_name", "Other Deduction")
        
        # Get CTC components if structure exists
        ctc_components = None
        if ctc_structure and ctc_structure.get("components"):
            ctc_components = ctc_structure["components"]
            gross_monthly = ctc_structure.get("summary", {}).get("gross_monthly", gross_monthly)
        
        # === PRO-RATA CALCULATION FOR MID-MONTH JOINERS ===
        prorata_info = {"is_prorata": False}
        joining_date = employee.get("date_of_joining") or employee.get("joining_date")
        full_gross_monthly = gross_monthly  # Store original for reference
        
        if joining_date:
            try:
                prorata_result = await self.calculate_prorata_salary(
                    gross_monthly=gross_monthly,
                    joining_date=joining_date,
                    month=month
                )
                if prorata_result.get("is_prorata"):
                    prorata_info = {
                        "is_prorata": True,
                        "joining_date": joining_date,
                        "full_gross": gross_monthly,
                        "prorata_gross": prorata_result["prorata_salary"],
                        "days_worked": prorata_result["working_days"],
                        "days_in_month": prorata_result["days_in_month"],
                        "formula": prorata_result["formula"]
                    }
                    gross_monthly = prorata_result["prorata_salary"]
                    logger.info(f"Pro-rata applied for {employee_name}: {prorata_result['formula']}")
            except Exception as e:
                logger.warning(f"Pro-rata calc failed for {employee_name}: {e}")
        
        # Calculate basic salary (for PF calculation)
        basic_monthly = gross_monthly * 0.40  # Default 40% of gross
        if ctc_components and "basic" in ctc_components:
            if prorata_info["is_prorata"]:
                # Scale basic proportionally for pro-rata
                full_basic = ctc_components["basic"].get("monthly", full_gross_monthly * 0.40)
                ratio = gross_monthly / full_gross_monthly if full_gross_monthly > 0 else 1
                basic_monthly = full_basic * ratio
            else:
                basic_monthly = ctc_components["basic"].get("monthly", basic_monthly)
        
        # === EARNINGS ===
        earnings = await self.calculate_earnings(gross_monthly, ctc_components)
        
        # Add incentive if any
        if incentive > 0:
            earnings.append({
                "key": "incentive",
                "name": "Incentive",
                "amount": round(incentive, 2),
                "calculation": self._log_calculation(
                    "Incentive",
                    {"incentive": incentive, "reason": payroll_input.get("incentive_reason", "")},
                    "Direct addition",
                    incentive, "INCENTIVE", "1.0"
                )
            })
        
        # Add bonus if any
        if bonus > 0:
            earnings.append({
                "key": "bonus",
                "name": "Bonus",
                "amount": round(bonus, 2),
                "calculation": self._log_calculation(
                    "Bonus",
                    {"bonus": bonus},
                    "Direct addition",
                    bonus, "BONUS", "1.0"
                )
            })
        
        # Add overtime if any
        if overtime_hours > 0:
            hourly_rate = gross_monthly / (working_days * 8)  # Assuming 8 hours/day
            overtime_amount = hourly_rate * 1.5 * overtime_hours  # 1.5x for overtime
            earnings.append({
                "key": "overtime",
                "name": "Overtime Pay",
                "amount": round(overtime_amount, 2),
                "calculation": self._log_calculation(
                    "Overtime Pay",
                    {"hourly_rate": round(hourly_rate, 2), "hours": overtime_hours, "multiplier": 1.5},
                    f"(₹{gross_monthly:,.2f} / {working_days * 8} hrs) × 1.5 × {overtime_hours} hrs",
                    overtime_amount, "OVERTIME", "1.0"
                )
            })
        
        # Add arrears if any
        if arrears > 0:
            earnings.append({
                "key": "arrears",
                "name": "Arrears",
                "amount": round(arrears, 2),
                "calculation": self._log_calculation(
                    "Arrears",
                    {"arrears": arrears, "reason": arrears_reason},
                    f"Previous month adjustment: {arrears_reason}" if arrears_reason else "Direct addition",
                    arrears, "ARREARS", "1.0"
                )
            })
        
        total_earnings = sum(e["amount"] for e in earnings)
        
        # === REIMBURSEMENTS (Non-taxable additions) ===
        reimbursements_breakdown = []
        
        if travel_reimbursement > 0:
            reimbursements_breakdown.append({
                "key": "travel_reimbursement",
                "name": "Travel Reimbursement",
                "amount": round(travel_reimbursement, 2),
                "calculation": self._log_calculation(
                    "Travel Reimbursement",
                    {"amount": travel_reimbursement},
                    "Non-taxable reimbursement",
                    travel_reimbursement, "TRAVEL_REIMB", "1.0"
                )
            })
        
        if medical_reimbursement > 0:
            reimbursements_breakdown.append({
                "key": "medical_reimbursement",
                "name": "Medical Reimbursement",
                "amount": round(medical_reimbursement, 2),
                "calculation": self._log_calculation(
                    "Medical Reimbursement",
                    {"amount": medical_reimbursement},
                    "Non-taxable reimbursement",
                    medical_reimbursement, "MEDICAL_REIMB", "1.0"
                )
            })
        
        if food_reimbursement > 0:
            reimbursements_breakdown.append({
                "key": "food_reimbursement",
                "name": "Food/Meal Allowance",
                "amount": round(food_reimbursement, 2),
                "calculation": self._log_calculation(
                    "Food/Meal Allowance",
                    {"amount": food_reimbursement},
                    "Non-taxable reimbursement",
                    food_reimbursement, "FOOD_REIMB", "1.0"
                )
            })
        
        if telephone_reimbursement > 0:
            reimbursements_breakdown.append({
                "key": "telephone_reimbursement",
                "name": "Telephone/Internet Reimbursement",
                "amount": round(telephone_reimbursement, 2),
                "calculation": self._log_calculation(
                    "Telephone/Internet Reimbursement",
                    {"amount": telephone_reimbursement},
                    "Non-taxable reimbursement",
                    telephone_reimbursement, "TELEPHONE_REIMB", "1.0"
                )
            })
        
        if other_reimbursement > 0:
            reimbursements_breakdown.append({
                "key": "other_reimbursement",
                "name": "Other Reimbursement",
                "amount": round(other_reimbursement, 2),
                "calculation": self._log_calculation(
                    "Other Reimbursement",
                    {"amount": other_reimbursement},
                    "Non-taxable reimbursement",
                    other_reimbursement, "OTHER_REIMB", "1.0"
                )
            })
        
        # === DEDUCTIONS ===
        deductions = []
        
        # Fetch attendance summary
        attendance_summary = await self.fetch_attendance_summary(employee_id, month)
        
        # Use attendance-calculated LOP if available and no manual LOP provided
        if lop_days == 0 and attendance_summary.get("calculated_lop", 0) > 0:
            lop_days = attendance_summary["calculated_lop"]
        
        # LOP Deduction
        if lop_days > 0:
            lop_result = await self.calculate_lop(gross_monthly, lop_days, month, working_days)
            deductions.append({
                "key": "lop",
                "name": "Loss of Pay (LOP)",
                "amount": lop_result["amount"],
                "details": f"{lop_days} days @ ₹{lop_result['daily_rate']:,.2f}/day",
                "calculation": lop_result["calculation"]
            })
        
        # PF Deduction (Employee)
        pf_result = await self.calculate_pf(basic_monthly)
        if pf_result["employee_contribution"] > 0:
            deductions.append({
                "key": "pf",
                "name": "Provident Fund (PF)",
                "amount": pf_result["employee_contribution"],
                "details": f"12% of ₹{pf_result['pf_base']:,.2f}",
                "calculation": pf_result["calculation"]
            })
        
        # ESI Deduction (if applicable)
        esi_result = await self.calculate_esi(gross_monthly)
        if esi_result.get("applicable") and esi_result["employee_contribution"] > 0:
            deductions.append({
                "key": "esi",
                "name": "ESI (Employee State Insurance)",
                "amount": esi_result["employee_contribution"],
                "details": f"0.75% of ₹{gross_monthly:,.2f}",
                "calculation": esi_result.get("calculation")
            })
        
        # Professional Tax
        pt_result = await self.calculate_professional_tax(gross_monthly)
        if pt_result["amount"] > 0:
            deductions.append({
                "key": "professional_tax",
                "name": "Professional Tax (PT)",
                "amount": pt_result["amount"],
                "details": pt_result["slab"],
                "calculation": pt_result["calculation"]
            })
        
        # TDS (Income Tax) - New Regime
        gross_annual = gross_monthly * 12
        tds_result = await self.calculate_tds(gross_annual, "new")
        if tds_result["monthly_tds"] > 0:
            deductions.append({
                "key": "tds",
                "name": "TDS (Income Tax)",
                "amount": tds_result["monthly_tds"],
                "details": f"New Regime - Annual Tax: ₹{tds_result['annual_tax']:,.0f}",
                "calculation": tds_result["calculation"]
            })
        
        # Rule-based deductions (from Business Rules)
        rule_deductions = await self.fetch_rule_based_deductions(employee, month)
        deductions.extend(rule_deductions)
        
        # Penalty deduction (manual)
        if penalty > 0:
            deductions.append({
                "key": "penalty",
                "name": "Penalty",
                "amount": round(penalty, 2),
                "details": penalty_reason,
                "calculation": self._log_calculation(
                    "Penalty",
                    {"penalty": penalty, "reason": penalty_reason},
                    f"Manual deduction: {penalty_reason}" if penalty_reason else "Direct deduction",
                    penalty, "PENALTY_MANUAL", "1.0"
                )
            })
        
        # Advance recovery
        if advance_recovery > 0:
            deductions.append({
                "key": "advance_recovery",
                "name": "Advance Recovery",
                "amount": round(advance_recovery, 2),
                "details": advance_reason,
                "calculation": self._log_calculation(
                    "Advance Recovery",
                    {"advance": advance_recovery, "reason": advance_reason},
                    f"Salary advance recovery: {advance_reason}" if advance_reason else "Direct deduction",
                    advance_recovery, "ADVANCE_RECOVERY", "1.0"
                )
            })
        
        # Loan EMI
        if loan_emi > 0:
            deductions.append({
                "key": "loan_emi",
                "name": f"Loan EMI ({loan_type})" if loan_type else "Loan EMI",
                "amount": round(loan_emi, 2),
                "details": loan_type,
                "calculation": self._log_calculation(
                    "Loan EMI",
                    {"emi": loan_emi, "loan_type": loan_type},
                    f"{loan_type} loan EMI" if loan_type else "Monthly EMI deduction",
                    loan_emi, "LOAN_EMI", "1.0"
                )
            })
        
        # Other deductions
        if other_deduction > 0:
            deductions.append({
                "key": "other_deduction",
                "name": other_deduction_name,
                "amount": round(other_deduction, 2),
                "details": other_deduction_name,
                "calculation": self._log_calculation(
                    other_deduction_name,
                    {"amount": other_deduction, "name": other_deduction_name},
                    "Other deduction",
                    other_deduction, "OTHER_DEDUCTION", "1.0"
                )
            })
        
        total_deductions = sum(d["amount"] for d in deductions)
        
        # === NET SALARY ===
        net_salary = total_earnings - total_deductions
        
        # Add reimbursements (post-tax addition)
        net_payable = net_salary + total_reimbursements
        
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "employee_code": employee.get("employee_id", ""),
            "department": employee.get("department", ""),
            "designation": employee.get("designation", "") or employee.get("role", ""),
            "location": employee.get("location", "") or employee.get("city", ""),
            "bank_account": employee.get("bank_account", ""),
            "pan_number": employee.get("pan_number", ""),
            "month": month,
            "days_in_month": self._get_days_in_month(month),
            "working_days": attendance_summary.get("working_days", working_days),
            "weekly_offs": attendance_summary.get("weekly_offs", 0),
            "public_holidays": attendance_summary.get("public_holidays", 0),
            "present_days": attendance_summary.get("present_days", 0),
            "lop_days": lop_days,
            "gross_monthly": round(gross_monthly, 2),
            "gross_annual": round(gross_monthly * 12, 2),
            "basic_monthly": round(basic_monthly, 2),
            "earnings": earnings,
            "total_earnings": round(total_earnings, 2),
            "reimbursements_breakdown": reimbursements_breakdown,
            "total_reimbursements": round(total_reimbursements, 2),
            "expense_breakdown": {
                "travel": round(travel_reimbursement, 2),
                "medical": round(medical_reimbursement, 2),
                "food": round(food_reimbursement, 2),
                "telephone": round(telephone_reimbursement, 2),
                "other": round(other_reimbursement, 2),
                "total": round(total_reimbursements, 2)
            },
            "deductions": deductions,
            "total_deductions": round(total_deductions, 2),
            "net_salary": round(net_salary, 2),
            "net_payable": round(net_payable, 2),
            "attendance_summary": attendance_summary,
            "leave_breakdown": attendance_summary.get("leave_breakdown", {}),
            "tds_details": {
                "monthly_tds": tds_result.get("monthly_tds", 0),
                "annual_tax": tds_result.get("annual_tax", 0),
                "taxable_income": tds_result.get("taxable_income", 0),
                "rebate_87a": tds_result.get("rebate_87a", 0),
                "tax_before_rebate": tds_result.get("tax_before_rebate", 0),
                "regime": tds_result.get("regime", "new"),
                "finance_act": tds_result.get("finance_act", "2025"),
                "slab_breakdown": tds_result.get("slab_breakdown", [])
            },
            "employer_contributions": {
                "pf": pf_result.get("employer_contribution", 0),
                "esi": esi_result.get("employer_contribution", 0) if esi_result.get("applicable") else 0
            },
            "prorata_info": prorata_info,
            "calculation_log": self.calculation_log,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def simulate_payroll(
        self,
        employee_id: str,
        month: str,
        simulation_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate payroll with custom inputs (HR Test Mode).
        Does not save to database.
        """
        # Fetch employee
        employee = await self.db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            return {
                "success": False,
                "error": "EMPLOYEE_NOT_FOUND",
                "error_message": f"Employee {employee_id} not found"
            }
        
        # Fetch CTC structure if exists
        ctc_structure = await self.db.ctc_structures.find_one(
            {"employee_id": employee_id, "status": "active"},
            {"_id": 0}
        )
        
        # Run calculation
        result = await self.run_payroll_calculation(
            employee=employee,
            month=month,
            payroll_input=simulation_inputs,
            ctc_structure=ctc_structure
        )
        
        result["is_simulation"] = True
        return result
    
    async def run_bulk_simulation(
        self,
        month: str,
        employee_inputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run bulk payroll simulation for multiple employees.
        
        Input format:
        [
            {"employee_id": "xxx", "lop_days": 2, "bonus": 5000},
            ...
        ]
        """
        results = []
        total_gross = 0
        total_net = 0
        errors = []
        department_summary = {}
        
        for emp_input in employee_inputs:
            employee_id = emp_input.get("employee_id")
            if not employee_id:
                continue
            
            result = await self.simulate_payroll(
                employee_id=employee_id,
                month=month,
                simulation_inputs=emp_input
            )
            
            if result.get("success"):
                results.append(result)
                total_gross += result.get("gross_monthly", 0)
                total_net += result.get("net_payable", 0)
                
                # Department summary
                dept = result.get("department", "Unknown")
                if dept not in department_summary:
                    department_summary[dept] = {
                        "count": 0,
                        "total_gross": 0,
                        "total_net": 0
                    }
                department_summary[dept]["count"] += 1
                department_summary[dept]["total_gross"] += result.get("gross_monthly", 0)
                department_summary[dept]["total_net"] += result.get("net_payable", 0)
            else:
                errors.append({
                    "employee_id": employee_id,
                    "error": result.get("error_message", "Unknown error")
                })
        
        return {
            "success": True,
            "month": month,
            "total_employees": len(results),
            "total_errors": len(errors),
            "total_gross_salary": round(total_gross, 2),
            "total_net_payable": round(total_net, 2),
            "department_summary": department_summary,
            "results": results,
            "errors": errors,
            "simulated_at": datetime.now(timezone.utc).isoformat()
        }


def get_payroll_engine(db: AsyncIOMotorDatabase) -> PayrollCalculationEngine:
    """Factory function to get payroll engine instance"""
    return PayrollCalculationEngine(db)
