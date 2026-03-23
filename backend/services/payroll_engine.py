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
        state: str = "Maharashtra"
    ) -> Dict[str, Any]:
        """
        Calculate Professional Tax based on state slabs.
        Default: Maharashtra slabs.
        """
        # Maharashtra PT slabs
        pt_amount = 0
        slab_used = ""
        
        if gross_monthly <= 7500:
            pt_amount = 0
            slab_used = "Up to ₹7,500 - Nil"
        elif gross_monthly <= 10000:
            pt_amount = 175
            slab_used = "₹7,501 to ₹10,000 - ₹175"
        else:
            pt_amount = 200
            slab_used = "Above ₹10,000 - ₹200 (max)"
        
        formula = f"Gross ₹{gross_monthly:,.2f} → Slab: {slab_used}"
        
        calc = self._log_calculation(
            component_name="Professional Tax",
            input_values={
                "gross_monthly": gross_monthly,
                "state": state,
                "slab_used": slab_used
            },
            formula=formula,
            output_value=pt_amount,
            rule_id="PROFESSIONAL_TAX",
            rule_version="1.0"
        )
        
        return {
            "amount": round(pt_amount, 2),
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
        """
        employee_id = employee.get("id")
        deductions = []
        
        # Fetch any penalty records for this employee/month
        penalties = await self.db.employee_penalties.find({
            "employee_id": employee_id,
            "month": month,
            "status": "active"
        }, {"_id": 0}).to_list(20)
        
        for penalty in penalties:
            calc = self._log_calculation(
                component_name=penalty.get("name", "Penalty"),
                input_values={
                    "rule_id": penalty.get("rule_id"),
                    "reason": penalty.get("reason"),
                    "violation_count": penalty.get("violation_count", 1)
                },
                formula=penalty.get("formula", "Rule-based penalty"),
                output_value=penalty.get("amount", 0),
                rule_id=penalty.get("rule_id", "PENALTY"),
                rule_version="1.0"
            )
            deductions.append({
                "key": f"penalty_{penalty.get('rule_id', 'unknown')}",
                "name": penalty.get("name", "Policy Violation Penalty"),
                "amount": round(penalty.get("amount", 0), 2),
                "details": penalty.get("reason", ""),
                "calculation": calc
            })
        
        # Fetch late arrival deductions from attendance rules
        late_policy = await self.db.business_policies.find_one(
            {"policy_type": "attendance", "is_active": True},
            {"_id": 0}
        )
        
        if late_policy:
            late_rule = next(
                (r for r in late_policy.get("rules", []) 
                 if r.get("rule_id") == "AT002" and r.get("is_enabled", True)),
                None
            )
            if late_rule:
                # Check late arrivals for this month
                late_threshold = late_rule.get("numeric_value", 3)
                late_count = await self.db.attendance.count_documents({
                    "employee_id": employee_id,
                    "date": {"$regex": f"^{month}"},
                    "late_arrival": True
                })
                
                if late_count > late_threshold:
                    excess_late = late_count - late_threshold
                    gross = employee.get("salary", 0) or employee.get("gross_salary", 0)
                    daily_rate = gross / self._get_days_in_month(month)
                    penalty_amount = daily_rate * 0.5 * excess_late  # Half day LOP per excess late
                    
                    calc = self._log_calculation(
                        component_name="Late Arrival Penalty",
                        input_values={
                            "late_count": late_count,
                            "threshold": late_threshold,
                            "excess_late": excess_late,
                            "daily_rate": round(daily_rate, 2),
                            "penalty_per_late": "0.5 day LOP"
                        },
                        formula=f"{excess_late} excess × ₹{daily_rate:,.2f} × 0.5",
                        output_value=penalty_amount,
                        rule_id="AT002",
                        rule_version=late_policy.get("version", "1.0")
                    )
                    deductions.append({
                        "key": "late_arrival_penalty",
                        "name": "Late Arrival Penalty (Rule: AT002)",
                        "amount": round(penalty_amount, 2),
                        "details": f"{excess_late} late arrivals above threshold of {late_threshold}",
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
        
        # Expense Reimbursements (breakdown)
        travel_reimbursement = payroll_input.get("travel_reimbursement", 0) or 0
        medical_reimbursement = payroll_input.get("medical_reimbursement", 0) or 0
        food_reimbursement = payroll_input.get("food_reimbursement", 0) or 0
        telephone_reimbursement = payroll_input.get("telephone_reimbursement", 0) or 0
        other_reimbursement = payroll_input.get("other_reimbursement", 0) or payroll_input.get("expense_reimbursement", 0) or payroll_input.get("reimbursements", 0) or 0
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
        
        # Calculate basic salary (for PF calculation)
        basic_monthly = gross_monthly * 0.40  # Default 40% of gross
        if ctc_components and "basic" in ctc_components:
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
