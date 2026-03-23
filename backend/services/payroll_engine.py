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
        
        lop_days = payroll_input.get("lop_days", 0) or payroll_input.get("absent_days", 0) or 0
        incentive = payroll_input.get("incentive", 0) or 0
        bonus = payroll_input.get("bonus", 0) or 0
        reimbursements = payroll_input.get("expense_reimbursement", 0) or payroll_input.get("reimbursements", 0) or 0
        advance = payroll_input.get("advance", 0) or 0
        penalty = payroll_input.get("penalty", 0) or 0
        overtime_hours = payroll_input.get("overtime_hours", 0) or 0
        working_days = payroll_input.get("working_days", self._get_days_in_month(month))
        
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
        
        total_earnings = sum(e["amount"] for e in earnings)
        
        # === DEDUCTIONS ===
        deductions = []
        
        # LOP Deduction
        if lop_days > 0:
            lop_result = await self.calculate_lop(gross_monthly, lop_days, month, working_days)
            deductions.append({
                "key": "lop",
                "name": "Loss of Pay",
                "amount": lop_result["amount"],
                "details": f"{lop_days} days @ ₹{lop_result['daily_rate']:,.2f}/day",
                "calculation": lop_result["calculation"]
            })
        
        # PF Deduction (Employee)
        pf_result = await self.calculate_pf(basic_monthly)
        if pf_result["employee_contribution"] > 0:
            deductions.append({
                "key": "pf",
                "name": "Provident Fund",
                "amount": pf_result["employee_contribution"],
                "details": f"12% of ₹{pf_result['pf_base']:,.2f}",
                "calculation": pf_result["calculation"]
            })
        
        # ESI Deduction (if applicable)
        esi_result = await self.calculate_esi(gross_monthly)
        if esi_result.get("applicable") and esi_result["employee_contribution"] > 0:
            deductions.append({
                "key": "esi",
                "name": "ESI",
                "amount": esi_result["employee_contribution"],
                "details": f"0.75% of ₹{gross_monthly:,.2f}",
                "calculation": esi_result.get("calculation")
            })
        
        # Professional Tax
        pt_result = await self.calculate_professional_tax(gross_monthly)
        if pt_result["amount"] > 0:
            deductions.append({
                "key": "professional_tax",
                "name": "Professional Tax",
                "amount": pt_result["amount"],
                "details": pt_result["slab"],
                "calculation": pt_result["calculation"]
            })
        
        # Penalty deduction
        if penalty > 0:
            deductions.append({
                "key": "penalty",
                "name": "Penalty",
                "amount": round(penalty, 2),
                "details": payroll_input.get("penalty_reason", ""),
                "calculation": self._log_calculation(
                    "Penalty",
                    {"penalty": penalty, "reason": payroll_input.get("penalty_reason", "")},
                    "Direct deduction",
                    penalty, "PENALTY", "1.0"
                )
            })
        
        # Advance recovery
        if advance > 0:
            deductions.append({
                "key": "advance_recovery",
                "name": "Advance Recovery",
                "amount": round(advance, 2),
                "details": payroll_input.get("advance_reason", ""),
                "calculation": self._log_calculation(
                    "Advance Recovery",
                    {"advance": advance, "reason": payroll_input.get("advance_reason", "")},
                    "Direct deduction",
                    advance, "ADVANCE_RECOVERY", "1.0"
                )
            })
        
        total_deductions = sum(d["amount"] for d in deductions)
        
        # === NET SALARY ===
        net_salary = total_earnings - total_deductions
        
        # Add reimbursements (post-tax addition)
        total_reimbursements = reimbursements
        net_payable = net_salary + total_reimbursements
        
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "employee_code": employee.get("employee_id", ""),
            "department": employee.get("department", ""),
            "designation": employee.get("designation", ""),
            "month": month,
            "days_in_month": self._get_days_in_month(month),
            "working_days": working_days,
            "lop_days": lop_days,
            "gross_monthly": round(gross_monthly, 2),
            "basic_monthly": round(basic_monthly, 2),
            "earnings": earnings,
            "total_earnings": round(total_earnings, 2),
            "deductions": deductions,
            "total_deductions": round(total_deductions, 2),
            "net_salary": round(net_salary, 2),
            "reimbursements": round(total_reimbursements, 2),
            "net_payable": round(net_payable, 2),
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
