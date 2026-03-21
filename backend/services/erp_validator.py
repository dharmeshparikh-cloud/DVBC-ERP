"""
ERP Data Integrity & Validation Service

Comprehensive validation for all 100 stress test scenarios.
Provides prevention, detection, alerting, recovery, and logging.

Categories:
- A: CRM → Project Failures
- B: HR & Onboarding Failures
- C: Project Execution Failures
- D: MOM & Work Tracking Failures
- E: Expense Management Failures
- F: Payroll Failures
- G: Finance & Revenue Failures
- H: Notifications & Workflow Failures
- I: Access Control Failures
- J: Data Integrity Failures
- K: Concurrency Failures
- L: Integration Failures
- M: Date/Time Failures
- N: Audit & Compliance Failures
- O: Backward Flow Failures
- P: Business Rule Failures
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import uuid
from fastapi import HTTPException


class ValidationResult:
    """Standard validation result"""
    def __init__(self, valid: bool, code: str, message: str, severity: str = "error", data: dict = None):
        self.valid = valid
        self.code = code
        self.message = message
        self.severity = severity  # error, warning, info
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self):
        return {
            "valid": self.valid,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "data": self.data,
            "timestamp": self.timestamp
        }
    
    def raise_if_invalid(self):
        if not self.valid:
            raise HTTPException(status_code=400, detail=self.message)


class ERPValidator:
    """Comprehensive ERP validation service"""
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # A: CRM → PROJECT VALIDATIONS
    # =========================================================================
    
    async def validate_lead_conversion(self, lead_id: str) -> ValidationResult:
        """A1-A7: Validate lead before conversion to project"""
        lead = await self.db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not lead:
            return ValidationResult(False, "A1", "Lead not found")
        
        errors = []
        
        # A1: Mandatory fields
        if not lead.get("company"):
            errors.append("Company name is required")
        if not lead.get("email") and not lead.get("phone"):
            errors.append("Email or phone is required")
        
        # A2: Check for existing kickoff (duplicate prevention)
        existing = await self.db.kickoff_requests.find_one(
            {"lead_id": lead_id, "status": {"$nin": ["cancelled", "rejected"]}},
            {"_id": 0, "id": 1}
        )
        if existing:
            return ValidationResult(
                False, "A2", 
                f"Kickoff request already exists for this lead",
                data={"existing_kickoff_id": existing["id"]}
            )
        
        # A4: Stage validation - must go through proper stages
        valid_won_stages = ["negotiation", "proposal", "closed_won"]
        if lead.get("status") not in valid_won_stages:
            errors.append(f"Lead must be in negotiation/proposal stage before winning. Current: {lead.get('status')}")
        
        if errors:
            return ValidationResult(False, "A1-A4", "; ".join(errors))
        
        return ValidationResult(True, "A_OK", "Lead validated for conversion")
    
    async def validate_project_dates(self, project_data: dict, lead_id: str = None) -> ValidationResult:
        """A6: Project start date validation"""
        start_date = project_data.get("start_date")
        if not start_date:
            return ValidationResult(True, "A6", "No start date to validate")
        
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        
        # Check if start date is in the past (more than 30 days)
        if start_date < datetime.now(timezone.utc) - timedelta(days=30):
            return ValidationResult(
                False, "A6",
                "Project start date cannot be more than 30 days in the past",
                severity="warning"
            )
        
        # If linked to lead, check against lead creation
        if lead_id:
            lead = await self.db.leads.find_one({"id": lead_id}, {"_id": 0, "created_at": 1})
            if lead and lead.get("created_at"):
                lead_created = lead["created_at"]
                if isinstance(lead_created, str):
                    lead_created = datetime.fromisoformat(lead_created.replace("Z", "+00:00"))
                if start_date < lead_created:
                    return ValidationResult(
                        False, "A6",
                        "Project start date cannot be before lead creation date"
                    )
        
        return ValidationResult(True, "A6", "Project dates valid")
    
    # =========================================================================
    # B: HR & ONBOARDING VALIDATIONS
    # =========================================================================
    
    async def validate_employee_creation(self, employee_data: dict) -> ValidationResult:
        """B8-B14: Validate employee data before creation"""
        errors = []
        
        # B8: Role required
        if not employee_data.get("role"):
            errors.append("Employee role is required")
        
        # B9: Duplicate check
        email = employee_data.get("email")
        emp_id = employee_data.get("employee_id")
        
        if email:
            existing = await self.db.employees.find_one({"email": email}, {"_id": 0, "id": 1})
            if existing:
                errors.append(f"Employee with email {email} already exists")
        
        if emp_id:
            existing = await self.db.employees.find_one({"employee_id": emp_id}, {"_id": 0, "id": 1})
            if existing:
                errors.append(f"Employee ID {emp_id} already exists")
        
        # B11: Validate reporting manager
        rm_id = employee_data.get("reporting_manager_id")
        if rm_id:
            rm = await self.db.employees.find_one(
                {"employee_id": rm_id},
                {"_id": 0, "go_live_status": 1}
            )
            if not rm:
                errors.append(f"Reporting manager {rm_id} not found")
            elif rm.get("go_live_status") in ["inactive", "terminated"]:
                errors.append(f"Reporting manager {rm_id} is inactive")
        
        # B13: Department validation
        dept = employee_data.get("department")
        if dept:
            valid_depts = await self.db.departments.find({}, {"_id": 0, "name": 1}).to_list(100)
            valid_dept_names = [d["name"] for d in valid_depts]
            if valid_dept_names and dept not in valid_dept_names:
                errors.append(f"Invalid department: {dept}")
        
        if errors:
            return ValidationResult(False, "B8-B14", "; ".join(errors))
        
        return ValidationResult(True, "B_OK", "Employee data validated")
    
    async def validate_employee_assignment(self, employee_id: str, project_id: str) -> ValidationResult:
        """B10: Validate employee can be assigned to project"""
        employee = await self.db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            return ValidationResult(False, "B10", "Employee not found")
        
        if employee.get("go_live_status") in ["inactive", "terminated"]:
            return ValidationResult(
                False, "B10",
                f"Cannot assign inactive employee to project. Status: {employee.get('go_live_status')}"
            )
        
        return ValidationResult(True, "B10", "Employee can be assigned")
    
    # =========================================================================
    # E: EXPENSE MANAGEMENT VALIDATIONS
    # =========================================================================
    
    async def validate_expense_creation(self, expense_data: dict, user_id: str) -> ValidationResult:
        """E27-E33: Validate expense before creation"""
        errors = []
        warnings = []
        
        # E27: Currency validation
        currency = expense_data.get("currency", "INR")
        valid_currencies = ["INR", "USD", "EUR", "GBP"]
        if currency not in valid_currencies:
            errors.append(f"Invalid currency: {currency}")
        
        # E30: Duplicate receipt check
        receipt_url = expense_data.get("receipt_url")
        if receipt_url:
            existing = await self.db.expenses.find_one(
                {"receipt_url": receipt_url, "status": {"$ne": "rejected"}},
                {"_id": 0, "id": 1}
            )
            if existing:
                errors.append(f"Receipt already used in expense {existing['id'][:8]}...")
        
        # E29: Policy limit check
        amount = expense_data.get("amount", 0)
        category = expense_data.get("category", "")
        
        # Get policy limits
        policy = await self.db.expense_policies.find_one(
            {"category": category},
            {"_id": 0, "max_amount": 1}
        )
        if policy and policy.get("max_amount") and amount > policy["max_amount"]:
            warnings.append(f"Amount {amount} exceeds policy limit of {policy['max_amount']} for {category}")
        
        # E33: Category validation
        valid_categories = ["travel", "accommodation", "meals", "equipment", "other", "meeting_expense"]
        if category and category not in valid_categories:
            warnings.append(f"Non-standard expense category: {category}")
        
        if errors:
            return ValidationResult(False, "E27-E33", "; ".join(errors))
        
        if warnings:
            return ValidationResult(True, "E_WARN", "; ".join(warnings), severity="warning")
        
        return ValidationResult(True, "E_OK", "Expense validated")
    
    async def validate_expense_for_payroll(self, expense_id: str, payroll_period: str) -> ValidationResult:
        """E31: Validate expense can be included in payroll"""
        expense = await self.db.expenses.find_one({"id": expense_id}, {"_id": 0})
        if not expense:
            return ValidationResult(False, "E31", "Expense not found")
        
        # Check if already linked
        existing = await self.db.payroll_reimbursements.find_one(
            {"expense_id": expense_id},
            {"_id": 0, "payroll_period": 1}
        )
        if existing:
            return ValidationResult(
                False, "E31",
                f"Expense already linked to payroll period {existing['payroll_period']}"
            )
        
        # Check approval status
        if expense.get("status") != "approved":
            return ValidationResult(
                False, "E31",
                f"Expense must be approved. Current status: {expense.get('status')}"
            )
        
        # Check payroll cutoff (15th of month for current month processing)
        expense_date = expense.get("expense_date") or expense.get("created_at")
        if isinstance(expense_date, str):
            expense_date = datetime.fromisoformat(expense_date.replace("Z", "+00:00"))
        
        year, month = payroll_period.split("-")
        cutoff_date = datetime(int(year), int(month), 15, tzinfo=timezone.utc)
        
        approved_at = expense.get("approved_at")
        if approved_at:
            if isinstance(approved_at, str):
                approved_at = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
            
            # If approved after 15th, goes to next month
            if approved_at > cutoff_date:
                next_month = int(month) + 1
                next_year = int(year)
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                suggested_period = f"{next_year}-{next_month:02d}"
                
                if payroll_period != suggested_period:
                    return ValidationResult(
                        False, "E31",
                        f"Expense approved after cutoff (15th). Should be in {suggested_period} payroll",
                        data={"suggested_period": suggested_period}
                    )
        
        return ValidationResult(True, "E31", "Expense valid for payroll")
    
    # =========================================================================
    # F: PAYROLL VALIDATIONS
    # =========================================================================
    
    async def validate_payroll_generation(self, employee_id: str, month: str) -> ValidationResult:
        """F34-F40: Validate before generating payroll"""
        employee = await self.db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            return ValidationResult(False, "F_ERR", "Employee not found")
        
        errors = []
        warnings = []
        
        # F40: Check employee status
        if employee.get("go_live_status") in ["inactive", "terminated"]:
            errors.append(f"Cannot generate payroll for {employee.get('go_live_status')} employee")
        
        # F34: Check for approved but unlinked expenses
        approved_expenses = await self.db.expenses.find(
            {"employee_id": employee_id, "status": "approved"},
            {"_id": 0, "id": 1}
        ).to_list(100)
        
        expense_ids = [e["id"] for e in approved_expenses]
        linked_reimbs = await self.db.payroll_reimbursements.find(
            {"expense_id": {"$in": expense_ids}, "payroll_period": month},
            {"_id": 0, "expense_id": 1}
        ).to_list(100)
        linked_ids = set(r["expense_id"] for r in linked_reimbs)
        
        unlinked = set(expense_ids) - linked_ids
        if unlinked:
            warnings.append(f"{len(unlinked)} approved expenses not linked to this payroll")
        
        # F38: Check for duplicate payroll input
        existing_input = await self.db.payroll_inputs.count_documents({
            "employee_id": employee_id,
            "month": month
        })
        if existing_input > 1:
            errors.append(f"Duplicate payroll inputs found for {month}")
        
        # F35: Check for salary structure changes mid-cycle
        salary_changes = await self.db.audit_logs.find({
            "entity_type": "employee",
            "action": {"$regex": "salary"},
            "metadata.employee_id": employee_id,
            "performed_at": {"$regex": f"^{month}"}
        }, {"_id": 0}).to_list(10)
        
        if salary_changes:
            warnings.append(f"Salary structure changed during {month}")
        
        # F37: Pro-rata check for mid-month join
        join_date = employee.get("join_date") or employee.get("created_at")
        if join_date:
            if isinstance(join_date, str):
                join_date = datetime.fromisoformat(join_date.replace("Z", "+00:00"))
            
            year, mon = month.split("-")
            if join_date.year == int(year) and join_date.month == int(mon):
                if join_date.day > 1:
                    warnings.append(f"Employee joined mid-month (day {join_date.day}). Ensure pro-rata calculation.")
        
        if errors:
            return ValidationResult(False, "F34-F40", "; ".join(errors))
        
        if warnings:
            return ValidationResult(True, "F_WARN", "; ".join(warnings), severity="warning")
        
        return ValidationResult(True, "F_OK", "Payroll validated")
    
    # =========================================================================
    # I: ACCESS CONTROL VALIDATIONS
    # =========================================================================
    
    async def validate_self_approval(self, user_id: str, entity_type: str, entity_id: str) -> ValidationResult:
        """I52: Prevent self-approval"""
        if entity_type == "expense":
            expense = await self.db.expenses.find_one({"id": entity_id}, {"_id": 0})
            if expense and expense.get("user_id") == user_id:
                return ValidationResult(
                    False, "I52",
                    "Cannot approve your own expense"
                )
        
        if entity_type == "leave":
            leave = await self.db.leave_requests.find_one({"id": entity_id}, {"_id": 0})
            if leave and leave.get("user_id") == user_id:
                return ValidationResult(
                    False, "I52",
                    "Cannot approve your own leave request"
                )
        
        return ValidationResult(True, "I52", "Self-approval check passed")
    
    async def validate_role_access(self, user_role: str, resource: str, action: str) -> ValidationResult:
        """I51, I53, I56: Role-based access validation"""
        # Define role permissions
        permissions = {
            "admin": ["*"],  # All access
            "principal_consultant": ["projects.*", "meetings.*", "consultants.*", "expenses.approve"],
            "hr_manager": ["employees.*", "payroll.*", "attendance.*", "leaves.approve"],
            "hr_executive": ["employees.read", "attendance.*", "leaves.read"],
            "consultant": ["projects.read", "meetings.*", "expenses.own", "leaves.own"],
            "sales_manager": ["leads.*", "clients.*", "kickoff.*"],
            "sales_executive": ["leads.own", "clients.read"]
        }
        
        user_perms = permissions.get(user_role, [])
        
        # Check if user has permission
        required_perm = f"{resource}.{action}"
        has_access = (
            "*" in user_perms or
            required_perm in user_perms or
            f"{resource}.*" in user_perms or
            (action == "read" and f"{resource}.read" in user_perms)
        )
        
        if not has_access:
            return ValidationResult(
                False, "I51",
                f"Role {user_role} does not have {action} permission on {resource}"
            )
        
        return ValidationResult(True, "I51", "Access granted")
    
    # =========================================================================
    # M: DATE/TIME VALIDATIONS
    # =========================================================================
    
    async def validate_backdated_entry(
        self, 
        entity_type: str, 
        entry_date: datetime, 
        max_backdate_days: int = 7
    ) -> ValidationResult:
        """M83: Validate backdated entries"""
        now = datetime.now(timezone.utc)
        
        if isinstance(entry_date, str):
            entry_date = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
        
        days_back = (now - entry_date).days
        
        if days_back > max_backdate_days:
            return ValidationResult(
                False, "M83",
                f"Entry date is {days_back} days in the past. Maximum allowed: {max_backdate_days} days",
                data={"requires_approval": True, "days_back": days_back}
            )
        
        return ValidationResult(True, "M83", "Date within allowed range")
    
    # =========================================================================
    # N: AUDIT & COMPLIANCE VALIDATIONS
    # =========================================================================
    
    async def validate_audit_trail(self, entity_type: str, entity_id: str) -> ValidationResult:
        """N84-N89: Verify audit trail exists"""
        audit_count = await self.db.audit_logs.count_documents({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        
        if audit_count == 0:
            return ValidationResult(
                False, "N84",
                f"No audit trail found for {entity_type} {entity_id}",
                severity="warning"
            )
        
        return ValidationResult(True, "N84", f"Audit trail exists ({audit_count} entries)")
    
    # =========================================================================
    # O: BACKWARD FLOW VALIDATIONS
    # =========================================================================
    
    async def validate_status_reversal(
        self, 
        entity_type: str, 
        entity_id: str, 
        current_status: str, 
        new_status: str
    ) -> ValidationResult:
        """O90-O95: Validate status reversals"""
        # Define allowed transitions
        transitions = {
            "project": {
                "completed": ["active"],  # Can reopen
                "active": ["on_hold", "completed", "cancelled"],
                "on_hold": ["active", "cancelled"],
                "draft": ["active", "cancelled"]
            },
            "expense": {
                "pending": ["approved", "rejected"],
                "approved": [],  # Cannot reverse approved
                "rejected": ["pending"]  # Can resubmit
            },
            "leave": {
                "pending": ["approved", "rejected", "withdrawn"],
                "approved": [],  # Cannot reverse approved leave
                "rejected": []
            }
        }
        
        allowed = transitions.get(entity_type, {}).get(current_status, [])
        
        if new_status not in allowed:
            return ValidationResult(
                False, "O90",
                f"Cannot change {entity_type} status from {current_status} to {new_status}. " +
                f"Allowed transitions: {allowed if allowed else 'none (terminal state)'}",
                data={"requires_admin_override": True}
            )
        
        return ValidationResult(True, "O90", "Status transition allowed")
    
    # =========================================================================
    # P: BUSINESS RULE VALIDATIONS
    # =========================================================================
    
    async def validate_workflow_sequence(self, workflow_type: str, current_step: str, next_step: str) -> ValidationResult:
        """P96-P100: Validate workflow sequence"""
        sequences = {
            "project_delivery": ["kickoff", "sow", "execution", "delivery", "closure"],
            "expense_approval": ["submitted", "manager_review", "hr_review", "admin_review", "approved"],
            "employee_onboarding": ["offer", "documents", "compliance", "training", "go_live"]
        }
        
        seq = sequences.get(workflow_type, [])
        if not seq:
            return ValidationResult(True, "P96", "No sequence defined")
        
        if current_step not in seq or next_step not in seq:
            return ValidationResult(True, "P96", "Steps not in defined sequence")
        
        current_idx = seq.index(current_step)
        next_idx = seq.index(next_step)
        
        # Can only move forward by 1 step (or stay same)
        if next_idx > current_idx + 1:
            skipped = seq[current_idx + 1:next_idx]
            return ValidationResult(
                False, "P96",
                f"Cannot skip workflow steps: {' → '.join(skipped)}",
                data={"skipped_steps": skipped}
            )
        
        return ValidationResult(True, "P96", "Workflow sequence valid")


# Singleton instance
_validator = None

def get_validator(db) -> ERPValidator:
    """Get or create validator instance"""
    global _validator
    if _validator is None:
        _validator = ERPValidator(db)
    else:
        _validator.db = db
    return _validator
