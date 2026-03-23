"""
Business Rules Service - Single Source of Truth for all company policies and rules.

This service provides:
1. Rule retrieval with caching
2. Rule validation and conflict detection
3. Impact analysis for rule changes
4. Integration with Payroll, Leave, Attendance modules
5. Real-time rule application

ALL modules must use this service for rule-based calculations.
DO NOT hardcode rules in other modules.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

# Cache for rules (in-memory, refreshes every 5 minutes)
_rules_cache = {}
_cache_timestamp = None
CACHE_TTL_SECONDS = 300  # 5 minutes


class BusinessRulesService:
    """
    Central service for accessing and applying business rules.
    
    Usage:
        from services.business_rules_service import get_business_rules_service
        
        rules_service = get_business_rules_service(db)
        
        # Get leave quota
        casual_leave_quota = await rules_service.get_leave_quota("casual_leave")
        
        # Get PF threshold
        pf_threshold = await rules_service.get_payroll_rule("PY003")
        
        # Apply statutory deductions
        deductions = await rules_service.calculate_statutory_deductions(basic_salary, gross_salary)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def _get_all_rules(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get all business rules with caching"""
        global _rules_cache, _cache_timestamp
        
        now = datetime.now(timezone.utc)
        
        # Check cache validity
        if not force_refresh and _cache_timestamp and _rules_cache:
            age = (now - _cache_timestamp).total_seconds()
            if age < CACHE_TTL_SECONDS:
                return _rules_cache
        
        # Fetch from database
        policies = await self.db.business_policies.find(
            {"is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        # Index by policy type and rule_id
        cache = {
            "policies": {},
            "rules_by_id": {},
            "rules_by_type": {},
            "last_updated": now.isoformat()
        }
        
        for policy in policies:
            policy_type = policy.get("policy_type")
            cache["policies"][policy_type] = policy
            
            if policy_type not in cache["rules_by_type"]:
                cache["rules_by_type"][policy_type] = []
            
            for rule in policy.get("rules", []):
                rule_id = rule.get("rule_id")
                if rule_id:
                    cache["rules_by_id"][rule_id] = {
                        **rule,
                        "policy_type": policy_type,
                        "policy_name": policy.get("name")
                    }
                    cache["rules_by_type"][policy_type].append(rule)
        
        _rules_cache = cache
        _cache_timestamp = now
        
        return cache
    
    async def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific rule by ID"""
        cache = await self._get_all_rules()
        return cache["rules_by_id"].get(rule_id)
    
    async def get_rules_by_type(self, policy_type: str) -> List[Dict[str, Any]]:
        """Get all rules for a policy type"""
        cache = await self._get_all_rules()
        return cache["rules_by_type"].get(policy_type, [])
    
    async def get_policy(self, policy_type: str) -> Optional[Dict[str, Any]]:
        """Get full policy by type"""
        cache = await self._get_all_rules()
        return cache["policies"].get(policy_type)
    
    # ==================== LEAVE RULES ====================
    
    async def get_leave_quota(self, leave_type: str) -> int:
        """Get annual leave quota for a leave type. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("leave")
        
        # Map leave types to rule categories
        for rule in rules:
            if rule.get("category") == leave_type and rule.get("is_enabled", True):
                return int(rule.get("numeric_value", 0))
        
        # Defaults if not configured
        defaults = {
            "casual_leave": 12,
            "sick_leave": 6,
            "earned_leave": 15,
            "maternity_leave": 182,
            "paternity_leave": 5,
            "bereavement_leave": 3,
            "comp_off": 0
        }
        return defaults.get(leave_type, 0)
    
    async def get_all_leave_quotas(self) -> Dict[str, int]:
        """Get all leave quotas"""
        rules = await self.get_rules_by_type("leave")
        quotas = {}
        
        for rule in rules:
            if rule.get("rule_type") == "limit" and rule.get("is_enabled", True):
                category = rule.get("category", "")
                if category and "_leave" in category or category == "comp_off":
                    quotas[category] = int(rule.get("numeric_value", 0))
        
        return quotas
    
    async def get_leave_process_rules(self) -> Dict[str, Any]:
        """Get leave process rules (notice days, max consecutive, etc.)"""
        rules = await self.get_rules_by_type("leave")
        process_rules = {}
        
        for rule in rules:
            if rule.get("category") == "process" and rule.get("is_enabled", True):
                rule_name = rule.get("rule_name", "").lower()
                if "notice" in rule_name:
                    process_rules["min_notice_days"] = int(rule.get("numeric_value", 2))
                elif "consecutive" in rule_name:
                    process_rules["max_consecutive_days"] = int(rule.get("numeric_value", 10))
            elif rule.get("category") == "calculation":
                if "sandwich" in rule.get("rule_name", "").lower():
                    process_rules["sandwich_policy"] = rule.get("value", "exclude_weekends")
                elif "lop" in rule.get("rule_name", "").lower():
                    process_rules["auto_lop"] = rule.get("is_enabled", True)
        
        return process_rules
    
    # ==================== PAYROLL RULES ====================
    
    async def get_payroll_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get specific payroll rule"""
        rule = await self.get_rule(rule_id)
        if rule and rule.get("policy_type") == "payroll":
            return rule
        return None
    
    async def get_pf_config(self) -> Dict[str, Any]:
        """Get PF configuration. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("payroll")
        
        config = {
            "threshold": 15000,
            "employee_percentage": 12,
            "employer_percentage": 12,
            "cap_amount": 15000,
            "is_enabled": True
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            rule_name = rule.get("rule_name", "").upper()
            
            if "PF THRESHOLD" in rule_name or rule.get("rule_id") == "PY003":
                config["threshold"] = rule.get("numeric_value", 15000)
            elif "PF" in rule_name and "EMPLOYEE" in rule_name:
                config["employee_percentage"] = rule.get("numeric_value", 12)
            elif "PF" in rule_name and "EMPLOYER" in rule_name:
                config["employer_percentage"] = rule.get("numeric_value", 12)
        
        return config
    
    async def get_esi_config(self) -> Dict[str, Any]:
        """Get ESI configuration. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("payroll")
        
        config = {
            "threshold": 21000,
            "employee_percentage": 0.75,
            "employer_percentage": 3.25,
            "is_enabled": True
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            if "ESI" in rule.get("rule_name", "").upper() or rule.get("rule_id") == "PY004":
                config["threshold"] = rule.get("numeric_value", 21000)
        
        return config
    
    async def get_professional_tax_slabs(self) -> List[Dict[str, Any]]:
        """Get Professional Tax slabs. SINGLE SOURCE OF TRUTH."""
        rule = await self.get_rule("PY007")
        
        if rule and rule.get("conditions"):
            slabs = []
            for slab_name, slab_data in rule.get("conditions", {}).items():
                if isinstance(slab_data, dict) and "min" in slab_data:
                    slabs.append(slab_data)
            return sorted(slabs, key=lambda x: x.get("min", 0))
        
        # Default PT slabs
        return [
            {"min": 0, "max": 15000, "tax": 0},
            {"min": 15001, "max": 25000, "tax": 150},
            {"min": 25001, "max": 999999999, "tax": 200}
        ]
    
    async def get_lop_formula(self) -> Dict[str, Any]:
        """Get LOP deduction formula. SINGLE SOURCE OF TRUTH."""
        rule = await self.get_rule("PY008")
        
        if rule and rule.get("is_enabled", True):
            return {
                "formula": rule.get("value", "basic_per_day"),
                "conditions": rule.get("conditions", {}),
                "is_enabled": True
            }
        
        return {
            "formula": "basic_per_day",
            "conditions": {"formula": "(basic_salary / working_days) * lop_days"},
            "is_enabled": True
        }
    
    async def calculate_statutory_deductions(
        self, 
        basic_salary: float, 
        gross_salary: float,
        pf_opt_in: bool = True,
        esi_opt_in: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate all statutory deductions using Business Rules.
        SINGLE SOURCE OF TRUTH for statutory calculations.
        
        Returns:
            {
                "pf_employee": float,
                "pf_employer": float,
                "esi_employee": float,
                "esi_employer": float,
                "professional_tax": float,
                "total_employee_deductions": float,
                "total_employer_contributions": float,
                "rules_applied": List[str]
            }
        """
        result = {
            "pf_employee": 0,
            "pf_employer": 0,
            "esi_employee": 0,
            "esi_employer": 0,
            "professional_tax": 0,
            "total_employee_deductions": 0,
            "total_employer_contributions": 0,
            "rules_applied": [],
            "breakdown": []
        }
        
        # PF Calculation
        if pf_opt_in:
            pf_config = await self.get_pf_config()
            if pf_config["is_enabled"] and basic_salary > 0:
                pf_base = min(basic_salary, pf_config["cap_amount"])
                result["pf_employee"] = round(pf_base * pf_config["employee_percentage"] / 100, 2)
                result["pf_employer"] = round(pf_base * pf_config["employer_percentage"] / 100, 2)
                result["rules_applied"].extend(["PY003", "PY005", "PY006"])
                result["breakdown"].append({
                    "component": "PF (Employee)",
                    "base": pf_base,
                    "rate": f"{pf_config['employee_percentage']}%",
                    "amount": result["pf_employee"]
                })
                result["breakdown"].append({
                    "component": "PF (Employer)",
                    "base": pf_base,
                    "rate": f"{pf_config['employer_percentage']}%",
                    "amount": result["pf_employer"]
                })
        
        # ESI Calculation
        if esi_opt_in:
            esi_config = await self.get_esi_config()
            if esi_config["is_enabled"] and gross_salary <= esi_config["threshold"]:
                result["esi_employee"] = round(gross_salary * esi_config["employee_percentage"] / 100, 2)
                result["esi_employer"] = round(gross_salary * esi_config["employer_percentage"] / 100, 2)
                result["rules_applied"].append("PY004")
                result["breakdown"].append({
                    "component": "ESI (Employee)",
                    "base": gross_salary,
                    "rate": f"{esi_config['employee_percentage']}%",
                    "amount": result["esi_employee"]
                })
                result["breakdown"].append({
                    "component": "ESI (Employer)",
                    "base": gross_salary,
                    "rate": f"{esi_config['employer_percentage']}%",
                    "amount": result["esi_employer"]
                })
        
        # Professional Tax
        pt_slabs = await self.get_professional_tax_slabs()
        for slab in pt_slabs:
            if slab["min"] <= gross_salary <= slab["max"]:
                result["professional_tax"] = slab.get("tax", 0)
                result["rules_applied"].append("PY007")
                result["breakdown"].append({
                    "component": "Professional Tax",
                    "base": gross_salary,
                    "slab": f"{slab['min']}-{slab['max']}",
                    "amount": result["professional_tax"]
                })
                break
        
        # Totals
        result["total_employee_deductions"] = (
            result["pf_employee"] + 
            result["esi_employee"] + 
            result["professional_tax"]
        )
        result["total_employer_contributions"] = (
            result["pf_employer"] + 
            result["esi_employer"]
        )
        
        return result
    
    async def calculate_lop_deduction(
        self,
        basic_salary: float,
        working_days: int,
        lop_days: int
    ) -> Dict[str, Any]:
        """
        Calculate LOP deduction using Business Rules.
        SINGLE SOURCE OF TRUTH for LOP calculation.
        """
        if lop_days <= 0:
            return {
                "lop_days": 0,
                "per_day_deduction": 0,
                "total_deduction": 0,
                "formula_used": "N/A",
                "rule_applied": None
            }
        
        lop_config = await self.get_lop_formula()
        
        formula = lop_config.get("formula", "basic_per_day")
        
        if formula == "basic_per_day" or "basic" in formula.lower():
            per_day = round(basic_salary / working_days, 2)
        else:
            # Default to basic per day
            per_day = round(basic_salary / working_days, 2)
        
        total = round(per_day * lop_days, 2)
        
        return {
            "lop_days": lop_days,
            "per_day_deduction": per_day,
            "total_deduction": total,
            "formula_used": formula,
            "rule_applied": "PY008"
        }
    
    # ==================== ATTENDANCE RULES ====================
    
    async def get_attendance_config(self) -> Dict[str, Any]:
        """Get attendance configuration. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("attendance")
        
        config = {
            "standard_work_hours": 9,
            "core_hours_start": "10:00",
            "core_hours_end": "17:00",
            "late_threshold_minutes": 15,
            "half_day_hours": 4,
            "full_day_hours": 8,
            "wfh_days_per_week": 2,
            "overtime_threshold_hours": 10
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            
            rule_id = rule.get("rule_id", "")
            
            if rule_id == "AT001":
                config["standard_work_hours"] = rule.get("numeric_value", 9)
            elif rule_id == "AT002":
                config["core_hours_start"] = rule.get("value", "10:00")
            elif rule_id == "AT003":
                config["core_hours_end"] = rule.get("value", "17:00")
            elif rule_id == "AT004":
                config["late_threshold_minutes"] = rule.get("numeric_value", 15)
            elif rule_id == "AT005":
                config["half_day_hours"] = rule.get("numeric_value", 4)
            elif rule_id == "AT006":
                config["full_day_hours"] = rule.get("numeric_value", 8)
            elif rule_id == "AT007":
                config["wfh_days_per_week"] = rule.get("numeric_value", 2)
            elif rule_id == "AT008":
                config["overtime_threshold_hours"] = rule.get("numeric_value", 10)
        
        return config
    
    # ==================== EXPENSE RULES ====================
    
    async def get_expense_config(self) -> Dict[str, Any]:
        """Get expense configuration. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("expense")
        
        config = {
            "self_approval_blocked": True,
            "payroll_cutoff_day": 25,
            "receipt_required_amount": 500,
            "max_single_expense": 50000,
            "monthly_expense_cap": 25000,
            "duplicate_prevention_hours": 24
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            
            rule_id = rule.get("rule_id", "")
            
            if rule_id == "EX001":
                config["self_approval_blocked"] = True
            elif rule_id == "EX002":
                config["payroll_cutoff_day"] = int(rule.get("numeric_value", 25))
            elif rule_id == "EX003":
                config["receipt_required_amount"] = rule.get("numeric_value", 500)
            elif rule_id == "EX004":
                config["max_single_expense"] = rule.get("numeric_value", 50000)
            elif rule_id == "EX005":
                config["monthly_expense_cap"] = rule.get("numeric_value", 25000)
            elif rule_id == "EX006":
                config["duplicate_prevention_hours"] = rule.get("numeric_value", 24)
        
        return config
    
    # ==================== TRAVEL RULES ====================
    
    async def get_travel_allowances(self) -> Dict[str, Any]:
        """Get travel allowances. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("travel")
        
        allowances = {
            "domestic_metro_daily": 2500,
            "domestic_non_metro_daily": 1500,
            "international_daily_usd": 100,
            "hotel_tier1": 5000,
            "hotel_tier2_3": 3000,
            "advance_request_days": 5,
            "settlement_deadline_days": 7,
            "receipt_threshold": 500
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            
            rule_id = rule.get("rule_id", "")
            
            if rule_id == "TR001":
                allowances["domestic_metro_daily"] = rule.get("numeric_value", 2500)
            elif rule_id == "TR002":
                allowances["domestic_non_metro_daily"] = rule.get("numeric_value", 1500)
            elif rule_id == "TR003":
                allowances["international_daily_usd"] = rule.get("numeric_value", 100)
            elif rule_id == "TR005":
                allowances["hotel_tier1"] = rule.get("numeric_value", 5000)
            elif rule_id == "TR006":
                allowances["hotel_tier2_3"] = rule.get("numeric_value", 3000)
            elif rule_id == "TR007":
                allowances["advance_request_days"] = rule.get("numeric_value", 5)
            elif rule_id == "TR008":
                allowances["settlement_deadline_days"] = rule.get("numeric_value", 7)
            elif rule_id == "TR009":
                allowances["receipt_threshold"] = rule.get("numeric_value", 500)
        
        return allowances
    
    # ==================== HR RULES ====================
    
    async def get_hr_config(self) -> Dict[str, Any]:
        """Get HR configuration. SINGLE SOURCE OF TRUTH."""
        rules = await self.get_rules_by_type("general")
        
        config = {
            "probation_months": 6,
            "notice_period_probation_days": 15,
            "notice_period_confirmed_days": 30,
            "notice_period_senior_days": 60,
            "annual_increment_month": 4,
            "retirement_age": 60
        }
        
        for rule in rules:
            if not rule.get("is_enabled", True):
                continue
            
            rule_id = rule.get("rule_id", "")
            
            if rule_id == "HR001":
                config["probation_months"] = rule.get("numeric_value", 6)
            elif rule_id == "HR002":
                config["notice_period_probation_days"] = rule.get("numeric_value", 15)
            elif rule_id == "HR003":
                config["notice_period_confirmed_days"] = rule.get("numeric_value", 30)
            elif rule_id == "HR004":
                config["notice_period_senior_days"] = rule.get("numeric_value", 60)
            elif rule_id == "HR005":
                config["annual_increment_month"] = rule.get("numeric_value", 4)
            elif rule_id == "HR007":
                config["retirement_age"] = rule.get("numeric_value", 60)
        
        return config
    
    # ==================== IMPACT ANALYSIS ====================
    
    async def get_rule_impact(self, rule_id: str) -> Dict[str, Any]:
        """
        Analyze the impact of changing a rule.
        Returns affected modules, calculations, and warnings.
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return {"error": "Rule not found"}
        
        impact = {
            "rule_id": rule_id,
            "rule_name": rule.get("rule_name"),
            "policy_type": rule.get("policy_type"),
            "affected_modules": [],
            "affected_calculations": [],
            "warnings": [],
            "recommendations": []
        }
        
        policy_type = rule.get("policy_type")
        category = rule.get("category", "")
        
        # Leave rules impact
        if policy_type == "leave":
            impact["affected_modules"].append("Leave Management")
            impact["affected_modules"].append("Payroll (LOP calculations)")
            impact["affected_calculations"].append("Leave balance calculations")
            if "encashment" in category:
                impact["affected_calculations"].append("F&F settlement")
                impact["warnings"].append("Changing encashment rules affects employee final settlements")
        
        # Payroll rules impact
        elif policy_type == "payroll":
            impact["affected_modules"].append("Payroll Generation")
            impact["affected_modules"].append("Salary Slip")
            impact["affected_modules"].append("CTC Calculator")
            
            if "PF" in rule.get("rule_name", "").upper():
                impact["affected_calculations"].append("PF deductions for all employees")
                impact["warnings"].append("PF changes are statutory - ensure compliance")
                impact["recommendations"].append("Verify with finance team before changing")
            elif "ESI" in rule.get("rule_name", "").upper():
                impact["affected_calculations"].append("ESI deductions for eligible employees")
                impact["warnings"].append("ESI has government-mandated thresholds")
            elif "LOP" in rule.get("rule_name", "").upper():
                impact["affected_calculations"].append("LOP deduction formula")
                impact["warnings"].append("Changes apply to future payroll runs only")
        
        # Expense rules impact
        elif policy_type == "expense":
            impact["affected_modules"].append("Expense Management")
            impact["affected_modules"].append("Expense Approvals")
            if "cutoff" in category:
                impact["affected_calculations"].append("Expense-to-payroll inclusion")
        
        # Travel rules impact
        elif policy_type == "travel":
            impact["affected_modules"].append("Travel Reimbursement")
            impact["affected_modules"].append("Expense Claims")
            impact["recommendations"].append("Communicate changes to employees before implementation")
        
        # Attendance rules impact
        elif policy_type == "attendance":
            impact["affected_modules"].append("Attendance Management")
            impact["affected_modules"].append("Time Tracking")
            if "overtime" in category:
                impact["affected_calculations"].append("Overtime pay calculations")
        
        # General HR rules impact
        elif policy_type == "general":
            impact["affected_modules"].append("Employee Onboarding")
            impact["affected_modules"].append("Exit Management")
            if "notice" in category:
                impact["affected_calculations"].append("Notice period calculations")
                impact["warnings"].append("Notice period changes may need legal review")
        
        return impact
    
    # ==================== VALIDATION ====================
    
    async def validate_rule_change(
        self, 
        rule_id: str, 
        new_value: Any
    ) -> Dict[str, Any]:
        """
        Validate a rule change before applying.
        Returns validation result with any errors or warnings.
        """
        rule = await self.get_rule(rule_id)
        if not rule:
            return {"valid": False, "error": "Rule not found"}
        
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        rule_type = rule.get("rule_type")
        
        # Validate numeric values
        if rule_type in ["limit", "threshold"] and rule.get("numeric_value") is not None:
            try:
                new_num = float(new_value)
                if new_num < 0:
                    result["errors"].append("Value cannot be negative")
                    result["valid"] = False
                
                # Specific validations
                if rule.get("rule_id") == "PY003" and new_num > 50000:
                    result["warnings"].append("PF threshold above statutory limit")
                elif rule.get("rule_id") == "PY004" and new_num > 25000:
                    result["warnings"].append("ESI threshold above statutory limit")
                    
            except (ValueError, TypeError):
                result["errors"].append("Invalid numeric value")
                result["valid"] = False
        
        return result
    
    def invalidate_cache(self):
        """Invalidate the rules cache (call after rule updates)"""
        global _rules_cache, _cache_timestamp
        _rules_cache = {}
        _cache_timestamp = None


# Factory function
_service_instance = None

def get_business_rules_service(db: AsyncIOMotorDatabase) -> BusinessRulesService:
    """Get or create the BusinessRulesService singleton"""
    global _service_instance
    if _service_instance is None or _service_instance.db != db:
        _service_instance = BusinessRulesService(db)
    return _service_instance
