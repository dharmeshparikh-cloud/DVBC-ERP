"""
Rule Engine Service - Complex condition evaluation with CTC component linkage

Supports:
- Conditional rules (if-then-else)
- Formula-based calculations
- CTC component references
- Threshold comparisons
- Multi-condition logic (AND, OR)
- Variable substitution
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import re
import operator
from decimal import Decimal, InvalidOperation


class RuleEngineError(Exception):
    """Custom exception for rule engine errors"""
    pass


class RuleEngine:
    """
    Rule Engine for evaluating complex business rules with CTC linkage.
    
    Supports operators: >, <, >=, <=, ==, !=, AND, OR, IN, NOT IN
    Supports functions: MIN, MAX, ROUND, FLOOR, CEIL, IF, PERCENTAGE
    """
    
    # Operator mapping
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne,
        'AND': lambda a, b: a and b,
        'OR': lambda a, b: a or b,
    }
    
    # CTC Component mappings
    CTC_COMPONENTS = {
        'basic_salary': {'type': 'earning', 'taxable': True, 'is_base': True},
        'hra': {'type': 'earning', 'taxable': True, 'calc': 'percentage_of_basic', 'default_percent': 50},
        'conveyance_allowance': {'type': 'earning', 'taxable': False, 'max_exempt': 1600},
        'medical_allowance': {'type': 'earning', 'taxable': False, 'max_exempt': 1250},
        'special_allowance': {'type': 'earning', 'taxable': True, 'is_balance': True},
        'lta': {'type': 'earning', 'taxable': False},
        'bonus': {'type': 'earning', 'taxable': True},
        'overtime': {'type': 'earning', 'taxable': True},
        'incentive': {'type': 'earning', 'taxable': True},
        'retention_bonus': {'type': 'earning', 'taxable': True, 'is_deferred': True},
        'pf_employee': {'type': 'deduction', 'statutory': True},
        'pf_employer': {'type': 'employer_contribution', 'statutory': True},
        'esi_employee': {'type': 'deduction', 'statutory': True},
        'esi_employer': {'type': 'employer_contribution', 'statutory': True},
        'professional_tax': {'type': 'deduction', 'statutory': True},
        'tds': {'type': 'deduction', 'statutory': True},
        'lop_deduction': {'type': 'deduction'},
        'expense_reimbursement': {'type': 'reimbursement'},
        'travel_reimbursement': {'type': 'reimbursement'},
    }
    
    def __init__(self, context: Dict[str, Any] = None):
        """
        Initialize rule engine with context variables.
        
        Context can include:
        - Employee data (salary, department, designation, tenure)
        - CTC components (basic_salary, hra, etc.)
        - Attendance data (working_days, present_days, lop_days)
        - Policy values
        """
        self.context = context or {}
        self.evaluation_log = []
    
    def set_context(self, key: str, value: Any):
        """Set a context variable"""
        self.context[key] = value
    
    def update_context(self, data: Dict[str, Any]):
        """Update multiple context variables"""
        self.context.update(data)
    
    def evaluate_condition(self, condition: str) -> Tuple[bool, str]:
        """
        Evaluate a condition string and return (result, explanation).
        
        Examples:
        - "basic_salary > 15000"
        - "department == 'Sales' AND tenure >= 12"
        - "gross_salary <= 21000"
        """
        try:
            # Replace variables with context values
            evaluated_condition = self._substitute_variables(condition)
            
            # Parse and evaluate
            result = self._parse_condition(condition)
            
            explanation = f"Condition '{condition}' evaluated to {result}"
            self.evaluation_log.append({
                'type': 'condition',
                'expression': condition,
                'result': result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return result, explanation
            
        except Exception as e:
            raise RuleEngineError(f"Error evaluating condition '{condition}': {str(e)}")
    
    def evaluate_formula(self, formula: str) -> Tuple[float, str]:
        """
        Evaluate a formula string and return (result, explanation).
        
        Examples:
        - "basic_salary * 0.12"
        - "ROUND(annual_ctc / 12, 2)"
        - "MIN(basic_salary * 0.5, 50000)"
        - "IF(basic_salary > 15000, basic_salary * 0.12, 0)"
        """
        try:
            # Substitute variables
            substituted = self._substitute_variables(formula)
            
            # Evaluate the formula
            result = self._safe_eval(substituted)
            
            explanation = f"Formula '{formula}' = {result}"
            self.evaluation_log.append({
                'type': 'formula',
                'expression': formula,
                'result': result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return float(result), explanation
            
        except Exception as e:
            raise RuleEngineError(f"Error evaluating formula '{formula}': {str(e)}")
    
    def evaluate_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a complete rule with conditions, formula, and CTC linkage.
        
        Rule structure:
        {
            "rule_id": "PY005",
            "rule_type": "formula",
            "conditions": {"basic_salary": ">15000"},
            "formula": "basic_salary * 0.12",
            "ctc_component": "pf_employee",
            "is_enabled": True
        }
        """
        result = {
            'rule_id': rule.get('rule_id'),
            'rule_name': rule.get('rule_name'),
            'is_enabled': rule.get('is_enabled', True),
            'condition_met': True,
            'calculated_value': None,
            'applied': False,
            'explanation': []
        }
        
        if not rule.get('is_enabled', True):
            result['explanation'].append('Rule is disabled')
            return result
        
        # Evaluate conditions if present
        if rule.get('conditions'):
            conditions = rule['conditions']
            
            if isinstance(conditions, dict):
                # Simple key-value conditions
                for key, condition_value in conditions.items():
                    if isinstance(condition_value, str) and condition_value.startswith(('>', '<', '=', '!')):
                        # Parse operator condition
                        condition_str = f"{key} {condition_value}"
                        met, explanation = self.evaluate_condition(condition_str)
                        result['explanation'].append(explanation)
                        if not met:
                            result['condition_met'] = False
                    elif key == 'applies_to':
                        # Check if applies to current role/department
                        applies = self._check_applies_to(condition_value)
                        result['condition_met'] = applies
                        result['explanation'].append(f"Applies to {condition_value}: {applies}")
                    else:
                        # Direct equality check
                        context_value = self.context.get(key)
                        met = context_value == condition_value
                        result['condition_met'] = met
                        result['explanation'].append(f"{key} == {condition_value}: {met}")
            
            elif isinstance(conditions, str):
                # Full condition string
                met, explanation = self.evaluate_condition(conditions)
                result['condition_met'] = met
                result['explanation'].append(explanation)
        
        # Evaluate formula/value if condition is met
        if result['condition_met']:
            rule_type = rule.get('rule_type', 'threshold')
            
            if rule_type == 'formula' and rule.get('value'):
                value, explanation = self.evaluate_formula(rule['value'])
                result['calculated_value'] = value
                result['explanation'].append(explanation)
                result['applied'] = True
                
            elif rule_type == 'limit' and rule.get('numeric_value') is not None:
                # Limit rule - return the limit value
                result['calculated_value'] = rule['numeric_value']
                result['applied'] = True
                result['explanation'].append(f"Limit applied: {rule['numeric_value']} {rule.get('unit', '')}")
                
            elif rule_type == 'threshold' and rule.get('numeric_value') is not None:
                # Threshold rule - check against threshold
                result['calculated_value'] = rule['numeric_value']
                result['applied'] = True
                result['explanation'].append(f"Threshold: {rule['numeric_value']} {rule.get('unit', '')}")
                
            elif rule.get('numeric_value') is not None:
                result['calculated_value'] = rule['numeric_value']
                result['applied'] = True
        
        return result
    
    def calculate_ctc_component(self, component_key: str, rules: List[Dict], ctc_data: Dict) -> Dict[str, Any]:
        """
        Calculate a CTC component value based on rules.
        
        Args:
            component_key: The CTC component (e.g., 'pf_employee', 'hra')
            rules: List of rules that may apply to this component
            ctc_data: Current CTC data (annual_ctc, basic_salary, etc.)
        
        Returns:
            {
                'component': 'pf_employee',
                'annual': 21600,
                'monthly': 1800,
                'rules_applied': ['PY005'],
                'explanation': [...]
            }
        """
        self.update_context(ctc_data)
        
        result = {
            'component': component_key,
            'annual': 0,
            'monthly': 0,
            'rules_applied': [],
            'explanation': []
        }
        
        component_info = self.CTC_COMPONENTS.get(component_key, {})
        
        # Find applicable rules for this component
        applicable_rules = [
            r for r in rules 
            if r.get('ctc_component') == component_key or 
               r.get('category') == component_key or
               component_key in str(r.get('value', ''))
        ]
        
        for rule in applicable_rules:
            rule_result = self.evaluate_rule(rule)
            
            if rule_result['applied'] and rule_result['calculated_value'] is not None:
                result['annual'] = rule_result['calculated_value']
                result['rules_applied'].append(rule['rule_id'])
                result['explanation'].extend(rule_result['explanation'])
        
        # Calculate monthly if annual is set
        if result['annual'] > 0:
            result['monthly'] = round(result['annual'] / 12, 2)
        
        return result
    
    def apply_statutory_rules(self, employee_data: Dict, payroll_rules: List[Dict]) -> Dict[str, Any]:
        """
        Apply all statutory rules (PF, ESI, PT, etc.) to calculate deductions.
        
        Returns calculated statutory components.
        """
        self.update_context(employee_data)
        
        statutory = {
            'pf_employee': 0,
            'pf_employer': 0,
            'esi_employee': 0,
            'esi_employer': 0,
            'professional_tax': 0,
            'total_deductions': 0,
            'total_employer_contribution': 0,
            'rules_applied': [],
            'breakdown': []
        }
        
        basic_salary = employee_data.get('basic_salary', 0)
        gross_salary = employee_data.get('gross_salary', 0)
        
        for rule in payroll_rules:
            if not rule.get('is_enabled', True):
                continue
            
            category = rule.get('category', '')
            rule_id = rule.get('rule_id', '')
            
            if category == 'statutory':
                rule_result = self.evaluate_rule(rule)
                
                if 'PF' in rule.get('rule_name', '').upper() and 'Employee' in rule.get('rule_name', ''):
                    # PF Employee contribution
                    if rule_result['condition_met'] or basic_salary > 15000:
                        pf = round(min(basic_salary, 15000) * 0.12, 2)
                        statutory['pf_employee'] = pf
                        statutory['breakdown'].append({
                            'component': 'PF (Employee)',
                            'amount': pf,
                            'rule': rule_id
                        })
                        statutory['rules_applied'].append(rule_id)
                
                elif 'PF' in rule.get('rule_name', '').upper() and 'Employer' in rule.get('rule_name', ''):
                    # PF Employer contribution
                    if statutory['pf_employee'] > 0:
                        pf_er = round(min(basic_salary, 15000) * 0.12, 2)
                        statutory['pf_employer'] = pf_er
                        statutory['breakdown'].append({
                            'component': 'PF (Employer)',
                            'amount': pf_er,
                            'rule': rule_id
                        })
                        statutory['rules_applied'].append(rule_id)
                
                elif 'ESI' in rule.get('rule_name', '').upper():
                    # ESI - applicable if gross <= 21000
                    threshold = rule.get('numeric_value', 21000)
                    if gross_salary <= threshold:
                        esi_ee = round(gross_salary * 0.0075, 2)
                        esi_er = round(gross_salary * 0.0325, 2)
                        statutory['esi_employee'] = esi_ee
                        statutory['esi_employer'] = esi_er
                        statutory['breakdown'].append({
                            'component': 'ESI (Employee)',
                            'amount': esi_ee,
                            'rule': rule_id
                        })
                        statutory['breakdown'].append({
                            'component': 'ESI (Employer)',
                            'amount': esi_er,
                            'rule': rule_id
                        })
                        statutory['rules_applied'].append(rule_id)
                
                elif 'Professional Tax' in rule.get('rule_name', ''):
                    # Professional Tax - slab based
                    conditions = rule.get('conditions', {})
                    pt = 0
                    if isinstance(conditions, dict):
                        for slab_name, slab in conditions.items():
                            if isinstance(slab, dict) and 'min' in slab and 'max' in slab:
                                if slab['min'] <= gross_salary <= slab['max']:
                                    pt = slab.get('tax', 0)
                                    break
                    if pt == 0 and gross_salary > 25000:
                        pt = 200  # Default max PT
                    statutory['professional_tax'] = pt
                    statutory['breakdown'].append({
                        'component': 'Professional Tax',
                        'amount': pt,
                        'rule': rule_id
                    })
                    statutory['rules_applied'].append(rule_id)
        
        statutory['total_deductions'] = (
            statutory['pf_employee'] + 
            statutory['esi_employee'] + 
            statutory['professional_tax']
        )
        statutory['total_employer_contribution'] = (
            statutory['pf_employer'] + 
            statutory['esi_employer']
        )
        
        return statutory
    
    def calculate_lop_deduction(self, employee_data: Dict, lop_rules: List[Dict]) -> Dict[str, Any]:
        """
        Calculate Loss of Pay deduction based on rules.
        """
        self.update_context(employee_data)
        
        basic_salary = employee_data.get('basic_salary', 0)
        working_days = employee_data.get('working_days', 30)
        lop_days = employee_data.get('lop_days', 0)
        
        result = {
            'lop_days': lop_days,
            'per_day_deduction': 0,
            'total_deduction': 0,
            'formula_used': 'basic_per_day',
            'explanation': []
        }
        
        if lop_days <= 0:
            result['explanation'].append('No LOP days')
            return result
        
        # Find LOP deduction rule
        lop_rule = next((r for r in lop_rules if 'LOP' in r.get('rule_name', '').upper()), None)
        
        if lop_rule:
            formula = lop_rule.get('value', 'basic_per_day')
            
            if formula == 'basic_per_day' or 'basic' in formula.lower():
                per_day = round(basic_salary / working_days, 2)
                result['per_day_deduction'] = per_day
                result['formula_used'] = 'basic_per_day'
            elif formula == 'gross_per_day' or 'gross' in formula.lower():
                gross = employee_data.get('gross_salary', basic_salary)
                per_day = round(gross / working_days, 2)
                result['per_day_deduction'] = per_day
                result['formula_used'] = 'gross_per_day'
            else:
                # Custom formula
                self.set_context('working_days', working_days)
                self.set_context('lop_days', lop_days)
                per_day, _ = self.evaluate_formula(formula)
                result['per_day_deduction'] = per_day
                result['formula_used'] = formula
        else:
            # Default: basic per day
            per_day = round(basic_salary / working_days, 2)
            result['per_day_deduction'] = per_day
        
        result['total_deduction'] = round(result['per_day_deduction'] * lop_days, 2)
        result['explanation'].append(
            f"LOP Deduction: {lop_days} days × ₹{result['per_day_deduction']} = ₹{result['total_deduction']}"
        )
        
        return result
    
    def _substitute_variables(self, expression: str) -> str:
        """Replace variable names with their context values"""
        result = expression
        
        # Find all potential variable names (words not in quotes)
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expression)
        
        for var in variables:
            if var in self.context:
                value = self.context[var]
                if isinstance(value, str):
                    result = result.replace(var, f"'{value}'")
                else:
                    result = result.replace(var, str(value))
        
        return result
    
    def _parse_condition(self, condition: str) -> bool:
        """Parse and evaluate a condition string"""
        # Handle AND/OR
        if ' AND ' in condition.upper():
            parts = re.split(r'\s+AND\s+', condition, flags=re.IGNORECASE)
            return all(self._parse_condition(p.strip()) for p in parts)
        
        if ' OR ' in condition.upper():
            parts = re.split(r'\s+OR\s+', condition, flags=re.IGNORECASE)
            return any(self._parse_condition(p.strip()) for p in parts)
        
        # Parse comparison operators
        for op_str in ['>=', '<=', '!=', '==', '>', '<']:
            if op_str in condition:
                parts = condition.split(op_str)
                if len(parts) == 2:
                    left = self._get_value(parts[0].strip())
                    right = self._get_value(parts[1].strip())
                    op_func = self.OPERATORS.get(op_str)
                    if op_func:
                        return op_func(left, right)
        
        # Boolean context variable
        if condition in self.context:
            return bool(self.context[condition])
        
        return False
    
    def _get_value(self, expr: str) -> Any:
        """Get the value of an expression (variable or literal)"""
        expr = expr.strip()
        
        # Check if it's a context variable
        if expr in self.context:
            return self.context[expr]
        
        # Try to parse as number
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # Remove quotes for string
        if (expr.startswith("'") and expr.endswith("'")) or \
           (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]
        
        return expr
    
    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate a mathematical expression"""
        # Define allowed functions
        safe_functions = {
            'MIN': min,
            'MAX': max,
            'ROUND': round,
            'ABS': abs,
            'FLOOR': lambda x: int(x),
            'CEIL': lambda x: int(x) + (1 if x % 1 else 0),
            'PERCENTAGE': lambda value, percent: value * percent / 100,
            'IF': lambda cond, true_val, false_val: true_val if cond else false_val,
        }
        
        # Replace function names with safe versions
        for func_name in safe_functions:
            expression = expression.replace(func_name, func_name.lower())
        
        # Build safe namespace
        safe_dict = {
            'min': min, 'max': max, 'round': round, 'abs': abs,
            'floor': lambda x: int(x),
            'ceil': lambda x: int(x) + (1 if x % 1 else 0),
            'percentage': lambda value, percent: value * percent / 100,
            '__builtins__': {}
        }
        
        try:
            result = eval(expression, safe_dict)
            return float(result)
        except Exception as e:
            raise RuleEngineError(f"Cannot evaluate expression: {expression} - {str(e)}")
    
    def _check_applies_to(self, applies_to: str) -> bool:
        """Check if rule applies to current employee based on applies_to condition"""
        if not applies_to:
            return True
        
        applies_to_lower = applies_to.lower()
        
        if 'all' in applies_to_lower:
            return True
        
        if 'manager' in applies_to_lower:
            designation = self.context.get('designation', '').lower()
            role = self.context.get('role', '').lower()
            return 'manager' in designation or 'manager' in role or role == 'admin'
        
        if 'senior' in applies_to_lower:
            tenure = self.context.get('tenure_months', 0)
            return tenure >= 24  # 2+ years
        
        # Check department
        department = self.context.get('department', '').lower()
        if department and department in applies_to_lower:
            return True
        
        return True  # Default: applies to all


# Factory function
def create_rule_engine(context: Dict[str, Any] = None) -> RuleEngine:
    """Create a new RuleEngine instance with optional context"""
    return RuleEngine(context)


# Utility functions for common calculations
def calculate_basic_salary(annual_ctc: float, basic_percentage: float = 40) -> float:
    """Calculate basic salary from CTC"""
    return round((annual_ctc * basic_percentage / 100) / 12, 2)


def calculate_hra(basic_salary: float, hra_percentage: float = 50) -> float:
    """Calculate HRA from basic salary"""
    return round(basic_salary * hra_percentage / 100, 2)


def calculate_pf(basic_salary: float, pf_percentage: float = 12, cap: float = 15000) -> Dict[str, float]:
    """Calculate PF contribution (employee and employer)"""
    pf_base = min(basic_salary, cap)
    contribution = round(pf_base * pf_percentage / 100, 2)
    return {
        'employee': contribution,
        'employer': contribution,
        'base_amount': pf_base
    }


def calculate_esi(gross_salary: float, threshold: float = 21000) -> Dict[str, float]:
    """Calculate ESI contribution if applicable"""
    if gross_salary > threshold:
        return {'employee': 0, 'employer': 0, 'applicable': False}
    
    return {
        'employee': round(gross_salary * 0.0075, 2),
        'employer': round(gross_salary * 0.0325, 2),
        'applicable': True
    }
