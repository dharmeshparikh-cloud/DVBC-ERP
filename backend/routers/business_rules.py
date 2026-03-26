"""
Business Rules Router - Centralized policy and rule management
All company policies accessible from one place:
- Leave Policies
- Travel Policies  
- Expense Policies
- Attendance Rules
- Payroll Rules
- General HR Policies

HR/Admin: Full edit access
Employees: View-only access
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, date
from utils.timezone import today_ist, current_month_ist, now_ist
import uuid
from pydantic import BaseModel
from .deps import get_db, HR_ADMIN_ROLES, HR_ROLES, get_role_group, has_role
from .models import User
from .deps import get_current_user

router = APIRouter(prefix="/business-rules", tags=["Business Rules"])


# ==================== MODELS ====================

class PolicyRuleConfig(BaseModel):
    """Configuration for a policy rule"""
    rule_id: str
    rule_name: str
    rule_type: str  # 'limit', 'approval', 'condition', 'formula', 'threshold'
    category: Optional[str] = None  # Category within policy type
    value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None  # Unit for numeric value (e.g., 'days/year', 'INR', 'percent')
    is_enabled: bool = True
    conditions: Optional[dict] = None
    description: str = ""
    payroll_impact: Optional[str] = None  # How this rule affects payroll
    disbursement_link: Optional[str] = None  # Link to disbursement module


class PolicyCreate(BaseModel):
    """Create/Update a policy"""
    name: str
    policy_type: str  # 'leave', 'travel', 'expense', 'attendance', 'payroll', 'general'
    description: Optional[str] = ""
    scope: str  # 'company', 'department', 'role', 'employee'
    scope_value: Optional[str] = None
    rules: List[dict] = []
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    ctc_linkage: Optional[dict] = None  # Link to CTC components
    payroll_integration: Optional[dict] = None


# ==================== DEFAULT POLICIES ====================

DEFAULT_TRAVEL_POLICY = {
    "name": "Standard Travel Policy",
    "policy_type": "travel",
    "description": "Company travel and reimbursement policy",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "TR001",
            "rule_name": "Daily Allowance - Domestic Metro",
            "rule_type": "limit",
            "category": "daily_allowance",
            "numeric_value": 2500,
            "unit": "INR/day",
            "applies_to": "domestic_metro",
            "description": "Per day allowance for domestic metro cities",
            "is_enabled": True
        },
        {
            "rule_id": "TR002",
            "rule_name": "Daily Allowance - Domestic Non-Metro",
            "rule_type": "limit",
            "category": "daily_allowance",
            "numeric_value": 1500,
            "unit": "INR/day",
            "applies_to": "domestic_non_metro",
            "description": "Per day allowance for domestic non-metro cities",
            "is_enabled": True
        },
        {
            "rule_id": "TR003",
            "rule_name": "Daily Allowance - International",
            "rule_type": "limit",
            "category": "daily_allowance",
            "numeric_value": 100,
            "unit": "USD/day",
            "applies_to": "international",
            "description": "Per day allowance for international travel",
            "is_enabled": True
        },
        {
            "rule_id": "TR004",
            "rule_name": "Flight Class - Domestic",
            "rule_type": "condition",
            "category": "transport",
            "value": "economy",
            "conditions": {"travel_hours": ">4", "override": "business_for_senior"},
            "description": "Economy class for domestic, business for >4 hours senior staff",
            "is_enabled": True
        },
        {
            "rule_id": "TR005",
            "rule_name": "Hotel Limit - Tier 1 Cities",
            "rule_type": "limit",
            "category": "accommodation",
            "numeric_value": 5000,
            "unit": "INR/night",
            "applies_to": "tier1_cities",
            "description": "Maximum hotel cost per night in Tier 1 cities",
            "is_enabled": True
        },
        {
            "rule_id": "TR006",
            "rule_name": "Hotel Limit - Tier 2/3 Cities",
            "rule_type": "limit",
            "category": "accommodation",
            "numeric_value": 3000,
            "unit": "INR/night",
            "applies_to": "tier2_tier3_cities",
            "description": "Maximum hotel cost per night in Tier 2/3 cities",
            "is_enabled": True
        },
        {
            "rule_id": "TR007",
            "rule_name": "Advance Request Days",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 5,
            "unit": "days",
            "description": "Minimum days before travel to request advance",
            "is_enabled": True
        },
        {
            "rule_id": "TR008",
            "rule_name": "Settlement Deadline",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 7,
            "unit": "days",
            "description": "Days after travel to submit expense settlement",
            "is_enabled": True
        },
        {
            "rule_id": "TR009",
            "rule_name": "Receipt Required Threshold",
            "rule_type": "threshold",
            "category": "documentation",
            "numeric_value": 500,
            "unit": "INR",
            "description": "Minimum amount requiring receipt/bill",
            "is_enabled": True
        },
        {
            "rule_id": "TR010",
            "rule_name": "Approval Hierarchy",
            "rule_type": "approval",
            "category": "process",
            "value": "manager->hr",
            "conditions": {"amount_threshold": 50000, "escalate_to": "admin"},
            "description": "Manager approval, HR for >50k, Admin for exceptions",
            "is_enabled": True
        }
    ],
    "payroll_integration": {
        "reimbursement_component": "travel_reimbursement",
        "auto_add_to_payroll": True,
        "deduction_for_policy_violation": True
    }
}

DEFAULT_EXPENSE_POLICY = {
    "name": "Standard Expense Policy",
    "policy_type": "expense",
    "description": "Company expense reimbursement policy",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "EX001",
            "rule_name": "Self-Approval Prevention",
            "rule_type": "condition",
            "category": "approval",
            "value": "self_approval_blocked",
            "description": "Employee cannot approve their own expenses",
            "is_enabled": True
        },
        {
            "rule_id": "EX002",
            "rule_name": "Payroll Cutoff",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 25,
            "unit": "day_of_month",
            "description": "Expenses submitted after 25th processed in next month",
            "is_enabled": True
        },
        {
            "rule_id": "EX003",
            "rule_name": "Receipt Required Amount",
            "rule_type": "threshold",
            "category": "documentation",
            "numeric_value": 500,
            "unit": "INR",
            "description": "Receipts mandatory for expenses above this amount",
            "is_enabled": True
        },
        {
            "rule_id": "EX004",
            "rule_name": "Maximum Single Expense",
            "rule_type": "limit",
            "category": "limit",
            "numeric_value": 50000,
            "unit": "INR",
            "conditions": {"requires_additional_approval": "admin"},
            "description": "Single expenses above 50k need admin approval",
            "is_enabled": True
        },
        {
            "rule_id": "EX005",
            "rule_name": "Monthly Expense Cap",
            "rule_type": "limit",
            "category": "limit",
            "numeric_value": 25000,
            "unit": "INR/month",
            "description": "Maximum monthly expense per employee without escalation",
            "is_enabled": True
        },
        {
            "rule_id": "EX006",
            "rule_name": "Duplicate Prevention Window",
            "rule_type": "threshold",
            "category": "validation",
            "numeric_value": 24,
            "unit": "hours",
            "description": "Block duplicate expense within 24 hours",
            "is_enabled": True
        }
    ],
    "payroll_integration": {
        "component": "expense_reimbursement",
        "auto_include": True
    }
}

DEFAULT_ATTENDANCE_POLICY = {
    "name": "Standard Attendance Policy",
    "policy_type": "attendance",
    "description": "Company attendance and work hours policy",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "AT001",
            "rule_name": "Standard Work Hours",
            "rule_type": "threshold",
            "category": "hours",
            "numeric_value": 9,
            "unit": "hours/day",
            "description": "Standard work day hours (including lunch)",
            "is_enabled": True
        },
        {
            "rule_id": "AT002",
            "rule_name": "Core Hours Start",
            "rule_type": "threshold",
            "category": "timing",
            "numeric_value": 10,
            "unit": "AM",
            "value": "10:00",
            "description": "Core hours start time (mandatory presence)",
            "is_enabled": True
        },
        {
            "rule_id": "AT003",
            "rule_name": "Core Hours End",
            "rule_type": "threshold",
            "category": "timing",
            "numeric_value": 19,
            "unit": "PM (7:00)",
            "value": "19:00",
            "description": "Core hours end time (mandatory presence)",
            "is_enabled": True
        },
        {
            "rule_id": "AT004",
            "rule_name": "Late Threshold",
            "rule_type": "threshold",
            "category": "timing",
            "numeric_value": 15,
            "unit": "minutes",
            "description": "Minutes after which arrival is marked late",
            "is_enabled": True
        },
        {
            "rule_id": "AT005",
            "rule_name": "Half Day Threshold",
            "rule_type": "threshold",
            "category": "hours",
            "numeric_value": 4,
            "unit": "hours",
            "description": "Minimum hours for half day attendance",
            "is_enabled": True
        },
        {
            "rule_id": "AT006",
            "rule_name": "Full Day Threshold",
            "rule_type": "threshold",
            "category": "hours",
            "numeric_value": 8,
            "unit": "hours",
            "description": "Minimum hours for full day attendance",
            "is_enabled": True
        },
        {
            "rule_id": "AT007",
            "rule_name": "Work From Home Days",
            "rule_type": "limit",
            "category": "wfh",
            "numeric_value": 2,
            "unit": "days/week",
            "description": "Maximum WFH days per week",
            "is_enabled": True
        },
        {
            "rule_id": "AT008",
            "rule_name": "Overtime Threshold",
            "rule_type": "threshold",
            "category": "hours",
            "numeric_value": 10,
            "unit": "hours",
            "description": "Hours after which overtime kicks in",
            "is_enabled": True
        },
        {
            "rule_id": "AT009",
            "rule_name": "Working Days",
            "rule_type": "config",
            "category": "schedule",
            "value": "Mon,Tue,Wed,Thu,Fri,Sat",
            "list_value": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "description": "Company working days (comma separated)",
            "is_enabled": True
        },
        {
            "rule_id": "AT010",
            "rule_name": "Grace Period Minutes",
            "rule_type": "threshold",
            "category": "timing",
            "numeric_value": 30,
            "unit": "minutes",
            "description": "Grace period for late arrivals before penalty",
            "is_enabled": True
        },
        {
            "rule_id": "AT011",
            "rule_name": "Grace Days Per Month",
            "rule_type": "limit",
            "category": "timing",
            "numeric_value": 3,
            "unit": "days/month",
            "description": "Number of grace late days allowed per month",
            "is_enabled": True
        },
        {
            "rule_id": "AT012",
            "rule_name": "Late Penalty Amount",
            "rule_type": "penalty",
            "category": "penalty",
            "numeric_value": 100,
            "unit": "INR/day",
            "description": "Penalty amount per late day beyond grace limit",
            "is_enabled": True
        }
    ],
    "payroll_integration": {
        "lop_deduction": True,
        "overtime_component": "overtime_allowance",
        "calculation_basis": "basic_salary"
    }
}

DEFAULT_PAYROLL_RULES = {
    "name": "Standard Payroll Rules",
    "policy_type": "payroll",
    "description": "Payroll processing rules and thresholds",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "PY001",
            "rule_name": "Payroll Processing Date",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 28,
            "unit": "day_of_month",
            "description": "Day of month for salary processing",
            "is_enabled": True
        },
        {
            "rule_id": "PY002",
            "rule_name": "Input Cutoff Date",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 25,
            "unit": "day_of_month",
            "description": "Last day to submit attendance/expense inputs",
            "is_enabled": True
        },
        {
            "rule_id": "PY003",
            "rule_name": "PF Threshold",
            "rule_type": "threshold",
            "category": "statutory",
            "numeric_value": 15000,
            "unit": "INR/month",
            "description": "Basic salary threshold for mandatory PF",
            "is_enabled": True
        },
        {
            "rule_id": "PY004",
            "rule_name": "ESI Threshold",
            "rule_type": "threshold",
            "category": "statutory",
            "numeric_value": 21000,
            "unit": "INR/month",
            "description": "Gross salary threshold for ESI eligibility",
            "is_enabled": True
        },
        {
            "rule_id": "PY005",
            "rule_name": "PF Employee Contribution",
            "rule_type": "formula",
            "category": "statutory",
            "numeric_value": 12,
            "unit": "percent",
            "value": "basic_salary * 0.12",
            "description": "Employee PF contribution percentage",
            "is_enabled": True
        },
        {
            "rule_id": "PY006",
            "rule_name": "PF Employer Contribution",
            "rule_type": "formula",
            "category": "statutory",
            "numeric_value": 12,
            "unit": "percent",
            "value": "basic_salary * 0.12",
            "description": "Employer PF contribution percentage",
            "is_enabled": True
        },
        {
            "rule_id": "PY007",
            "rule_name": "Professional Tax",
            "rule_type": "formula",
            "category": "statutory",
            "value": "slab_based",
            "conditions": {
                "slab1": {"min": 0, "max": 15000, "tax": 0},
                "slab2": {"min": 15001, "max": 25000, "tax": 150},
                "slab3": {"min": 25001, "max": 999999999, "tax": 200}
            },
            "description": "Professional tax slab (varies by state)",
            "is_enabled": True
        },
        {
            "rule_id": "PY008",
            "rule_name": "LOP Deduction Formula",
            "rule_type": "formula",
            "category": "deduction",
            "value": "basic_per_day",
            "conditions": {"formula": "(basic_salary / working_days) * lop_days"},
            "description": "Loss of Pay calculation formula",
            "is_enabled": True
        },
        {
            "rule_id": "PY009",
            "rule_name": "Bonus Calculation",
            "rule_type": "formula",
            "category": "earning",
            "value": "percentage_of_basic",
            "numeric_value": 8.33,
            "unit": "percent",
            "description": "Statutory bonus calculation (8.33% of basic)",
            "is_enabled": True
        },
        {
            "rule_id": "PY010",
            "rule_name": "Gratuity Eligibility",
            "rule_type": "threshold",
            "category": "statutory",
            "numeric_value": 5,
            "unit": "years",
            "description": "Minimum service years for gratuity",
            "is_enabled": True
        }
    ],
    "ctc_linkage": {
        "basic_salary": "base_component",
        "hra": "percentage_of_basic",
        "special_allowance": "balancing_component"
    }
}

DEFAULT_GENERAL_HR_POLICY = {
    "name": "General HR Policies",
    "policy_type": "general",
    "description": "General HR guidelines and policies",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "HR001",
            "rule_name": "Probation Period",
            "rule_type": "threshold",
            "category": "employment",
            "numeric_value": 6,
            "unit": "months",
            "description": "Standard probation period for new employees",
            "is_enabled": True
        },
        {
            "rule_id": "HR002",
            "rule_name": "Notice Period - Probation",
            "rule_type": "threshold",
            "category": "separation",
            "numeric_value": 15,
            "unit": "days",
            "description": "Notice period during probation",
            "is_enabled": True
        },
        {
            "rule_id": "HR003",
            "rule_name": "Notice Period - Confirmed",
            "rule_type": "threshold",
            "category": "separation",
            "numeric_value": 30,
            "unit": "days",
            "description": "Notice period after confirmation",
            "is_enabled": True
        },
        {
            "rule_id": "HR004",
            "rule_name": "Notice Period - Senior",
            "rule_type": "threshold",
            "category": "separation",
            "numeric_value": 60,
            "unit": "days",
            "conditions": {"applies_to": "manager_and_above"},
            "description": "Notice period for managers and above",
            "is_enabled": True
        },
        {
            "rule_id": "HR005",
            "rule_name": "Annual Increment Month",
            "rule_type": "threshold",
            "category": "compensation",
            "value": "April",
            "numeric_value": 4,
            "unit": "(April)",
            "description": "Month for annual salary revision (Financial year start)",
            "is_enabled": True
        },
        {
            "rule_id": "HR006",
            "rule_name": "Dress Code",
            "rule_type": "condition",
            "category": "workplace",
            "value": "business_casual",
            "conditions": {"friday": "casual", "client_meeting": "formal"},
            "description": "Workplace dress code policy",
            "is_enabled": True
        },
        {
            "rule_id": "HR007",
            "rule_name": "Retirement Age",
            "rule_type": "threshold",
            "category": "employment",
            "numeric_value": 60,
            "unit": "years",
            "description": "Standard retirement age",
            "is_enabled": True
        },
        {
            "rule_id": "HR008",
            "rule_name": "Background Verification",
            "rule_type": "condition",
            "category": "onboarding",
            "value": "mandatory",
            "description": "BGV mandatory for all new hires",
            "is_enabled": True
        }
    ]
}

DEFAULT_LEAVE_POLICY = {
    "name": "Standard Leave Policy",
    "policy_type": "leave",
    "description": "Company leave policy with quotas and rules",
    "scope": "company",
    "scope_value": None,
    "rules": [
        {
            "rule_id": "LV001",
            "rule_name": "Casual Leave Quota",
            "rule_type": "limit",
            "category": "casual_leave",
            "numeric_value": 12,
            "unit": "days/year",
            "description": "Annual casual leave entitlement",
            "is_enabled": True,
            "leave_type": "casual_leave"
        },
        {
            "rule_id": "LV002",
            "rule_name": "Sick Leave Quota",
            "rule_type": "limit",
            "category": "sick_leave",
            "numeric_value": 6,
            "unit": "days/year",
            "description": "Annual sick leave entitlement",
            "is_enabled": True,
            "leave_type": "sick_leave"
        },
        {
            "rule_id": "LV003",
            "rule_name": "Earned Leave Quota",
            "rule_type": "limit",
            "category": "earned_leave",
            "numeric_value": 15,
            "unit": "days/year",
            "description": "Annual earned/privilege leave entitlement",
            "is_enabled": True,
            "leave_type": "earned_leave",
            "conditions": {"accrual_rate": "1.25 days/month", "carry_forward": True, "max_accumulation": 45}
        },
        {
            "rule_id": "LV004",
            "rule_name": "Maternity Leave",
            "rule_type": "limit",
            "category": "maternity_leave",
            "numeric_value": 182,
            "unit": "days",
            "description": "Maternity leave as per Maternity Benefit Act",
            "is_enabled": True,
            "leave_type": "maternity_leave",
            "conditions": {"eligibility": "female_employees", "min_tenure_days": 80}
        },
        {
            "rule_id": "LV005",
            "rule_name": "Paternity Leave",
            "rule_type": "limit",
            "category": "paternity_leave",
            "numeric_value": 5,
            "unit": "days",
            "description": "Paternity leave for new fathers",
            "is_enabled": True,
            "leave_type": "paternity_leave",
            "conditions": {"eligibility": "male_employees"}
        },
        {
            "rule_id": "LV006",
            "rule_name": "Bereavement Leave",
            "rule_type": "limit",
            "category": "bereavement_leave",
            "numeric_value": 3,
            "unit": "days",
            "description": "Leave for family bereavement",
            "is_enabled": True,
            "leave_type": "bereavement_leave"
        },
        {
            "rule_id": "LV007",
            "rule_name": "Compensatory Off",
            "rule_type": "condition",
            "category": "comp_off",
            "value": "1:1",
            "description": "Comp off for working on holidays/weekends",
            "is_enabled": True,
            "leave_type": "comp_off",
            "conditions": {"validity_days": 30, "requires_approval": True}
        },
        {
            "rule_id": "LV008",
            "rule_name": "Minimum Notice Days",
            "rule_type": "threshold",
            "category": "process",
            "numeric_value": 2,
            "unit": "days",
            "description": "Minimum days in advance to apply for leave",
            "is_enabled": True,
            "conditions": {"exception": "sick_leave", "emergency": "0 days"}
        },
        {
            "rule_id": "LV009",
            "rule_name": "Max Consecutive Leave",
            "rule_type": "limit",
            "category": "process",
            "numeric_value": 10,
            "unit": "days",
            "description": "Maximum consecutive leave days without special approval",
            "is_enabled": True,
            "conditions": {"requires_additional_approval": "hr_manager"}
        },
        {
            "rule_id": "LV010",
            "rule_name": "Sandwich Policy",
            "rule_type": "condition",
            "category": "calculation",
            "value": "exclude_weekends",
            "description": "Weekends between leaves are not counted as leave",
            "is_enabled": True
        },
        {
            "rule_id": "LV011",
            "rule_name": "Leave Encashment",
            "rule_type": "formula",
            "category": "encashment",
            "value": "basic_per_day",
            "numeric_value": 50,
            "unit": "percent_of_balance",
            "description": "Maximum 50% of earned leave balance can be encashed",
            "is_enabled": True,
            "conditions": {"min_balance_required": 15, "max_encashable": 15, "timing": "annual"}
        },
        {
            "rule_id": "LV012",
            "rule_name": "LOP After Quota Exhausted",
            "rule_type": "condition",
            "category": "calculation",
            "value": "auto_convert_to_lop",
            "description": "Auto convert to LOP when leave quota exhausted",
            "is_enabled": True
        }
    ],
    "payroll_integration": {
        "lop_component": "lop_deduction",
        "encashment_component": "leave_encashment",
        "include_in_fnf": True
    }
}


# ==================== API ENDPOINTS ====================

@router.get("")
async def get_all_policies(
    policy_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """Get all business policies. All employees can view, HR/Admin can edit."""
    db = get_db()
    
    query = {}
    if policy_type:
        query["policy_type"] = policy_type
    if is_active is not None:
        query["is_active"] = is_active
    
    policies = await db.business_policies.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Initialize default policies if none exist
    if not policies:
        await initialize_default_policies(db, current_user.id)
        policies = await db.business_policies.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return policies


@router.get("/types")
async def get_policy_types(current_user: User = Depends(get_current_user)):
    """Get all policy types with their categories"""
    return {
        "policy_types": [
            {"id": "leave", "name": "Leave Policies", "icon": "Calendar", "description": "Leave types, quotas, and rules"},
            {"id": "travel", "name": "Travel Policies", "icon": "Plane", "description": "Travel allowances and reimbursements"},
            {"id": "expense", "name": "Expense Policies", "icon": "Receipt", "description": "Expense limits and approval rules"},
            {"id": "attendance", "name": "Attendance Policies", "icon": "Clock", "description": "Work hours and attendance rules"},
            {"id": "payroll", "name": "Payroll Rules", "icon": "DollarSign", "description": "Salary processing and statutory rules"},
            {"id": "general", "name": "General HR Policies", "icon": "FileText", "description": "Employment terms and conditions"}
        ],
        "rule_types": [
            {"id": "limit", "name": "Limit/Cap", "description": "Maximum allowed value"},
            {"id": "threshold", "name": "Threshold", "description": "Minimum required value"},
            {"id": "condition", "name": "Condition", "description": "Conditional rule"},
            {"id": "formula", "name": "Formula", "description": "Calculation formula"},
            {"id": "approval", "name": "Approval Flow", "description": "Approval hierarchy"}
        ]
    }


@router.get("/{policy_id}")
async def get_policy(policy_id: str, current_user: User = Depends(get_current_user)):
    """Get a single policy by ID"""
    db = get_db()
    policy = await db.business_policies.find_one({"id": policy_id}, {"_id": 0})
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return policy


@router.post("")
async def create_policy(policy_data: PolicyCreate, current_user: User = Depends(get_current_user)):
    """Create a new policy. HR/Admin only."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can create policies")
    
    db = get_db()
    
    policy = policy_data.dict()
    policy["id"] = str(uuid.uuid4())
    policy["created_at"] = datetime.now(timezone.utc).isoformat()
    policy["created_by"] = current_user.id
    policy["created_by_name"] = current_user.full_name
    policy["updated_at"] = policy["created_at"]
    policy["effective_from"] = policy["effective_from"].isoformat() if isinstance(policy["effective_from"], date) else policy["effective_from"]
    if policy.get("effective_to"):
        policy["effective_to"] = policy["effective_to"].isoformat() if isinstance(policy["effective_to"], date) else policy["effective_to"]
    
    await db.business_policies.insert_one(policy)
    
    # Log audit
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "policy_created",
        "entity_type": "business_policy",
        "entity_id": policy["id"],
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {"policy_name": policy["name"], "policy_type": policy["policy_type"]},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Policy created successfully", "policy_id": policy["id"]}


@router.put("/{policy_id}")
async def update_policy(policy_id: str, policy_data: dict, current_user: User = Depends(get_current_user)):
    """Update a policy. HR/Admin only."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can update policies")
    
    db = get_db()
    
    existing = await db.business_policies.find_one({"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Update fields
    update_data = {k: v for k, v in policy_data.items() if k not in ["id", "created_at", "created_by"]}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user.id
    update_data["updated_by_name"] = current_user.full_name
    
    await db.business_policies.update_one(
        {"id": policy_id},
        {"$set": update_data}
    )
    
    # Log audit
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "policy_updated",
        "entity_type": "business_policy",
        "entity_id": policy_id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {"updated_fields": list(update_data.keys())},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Policy updated successfully"}


@router.put("/{policy_id}/rule/{rule_id}")
async def update_policy_rule(policy_id: str, rule_id: str, rule_data: dict, current_user: User = Depends(get_current_user)):
    """Update a specific rule within a policy. HR/Admin only."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can update rules")
    
    db = get_db()
    
    policy = await db.business_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Find and update the rule
    rules = policy.get("rules", [])
    rule_updated = False
    for i, rule in enumerate(rules):
        if rule.get("rule_id") == rule_id:
            rules[i] = {**rule, **rule_data, "rule_id": rule_id}
            rule_updated = True
            break
    
    if not rule_updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.business_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "rules": rules,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }}
    )
    
    return {"message": "Rule updated successfully"}


@router.post("/{policy_id}/rule")
async def add_new_rule(policy_id: str, rule_data: dict, current_user: User = Depends(get_current_user)):
    """Add a new rule to a policy. HR/Admin only."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can add rules")
    
    db = get_db()
    
    policy = await db.business_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Generate rule ID if not provided
    if not rule_data.get("rule_id"):
        policy_type = policy.get("policy_type", "GN").upper()[:2]
        existing_rules = policy.get("rules", [])
        next_num = len(existing_rules) + 1
        rule_data["rule_id"] = f"{policy_type}{str(next_num).zfill(3)}"
    
    # Check if rule_id already exists
    rules = policy.get("rules", [])
    if any(r.get("rule_id") == rule_data.get("rule_id") for r in rules):
        raise HTTPException(status_code=400, detail="Rule ID already exists")
    
    # Add default fields
    rule_data.setdefault("is_enabled", True)
    rule_data.setdefault("rule_type", "limit")
    rule_data.setdefault("description", "")
    
    # Append new rule
    rules.append(rule_data)
    
    await db.business_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "rules": rules,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }}
    )
    
    return {"message": "Rule added successfully", "rule_id": rule_data["rule_id"]}


@router.delete("/{policy_id}/rule/{rule_id}")
async def delete_rule(policy_id: str, rule_id: str, current_user: User = Depends(get_current_user)):
    """Delete a rule from a policy. HR/Admin only."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can delete rules")
    
    db = get_db()
    
    policy = await db.business_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    rules = policy.get("rules", [])
    original_count = len(rules)
    rules = [r for r in rules if r.get("rule_id") != rule_id]
    
    if len(rules) == original_count:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.business_policies.update_one(
        {"id": policy_id},
        {"$set": {
            "rules": rules,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }}
    )
    
    return {"message": "Rule deleted successfully"}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str, current_user: User = Depends(get_current_user)):
    """Delete a policy. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete policies")
    
    db = get_db()
    
    result = await db.business_policies.delete_one({"id": policy_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {"message": "Policy deleted successfully"}


# ==================== ATTENDANCE POLICY CONFIGURATION ====================

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DEFAULT_WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

class AttendanceConfigUpdate(BaseModel):
    """Update attendance configuration"""
    working_days: Optional[List[str]] = None  # ["Monday", "Tuesday", ...]
    core_hours_start: Optional[str] = None  # "10:00"
    core_hours_end: Optional[str] = None  # "19:00"
    grace_period_minutes: Optional[int] = None
    grace_days_per_month: Optional[int] = None
    late_penalty_amount: Optional[float] = None
    wfh_days_per_week: Optional[int] = None


@router.get("/attendance/config")
async def get_attendance_config(current_user: User = Depends(get_current_user)):
    """
    Get current attendance policy configuration (company-wide).
    Returns the structured configuration from Business Rules SSOT.
    """
    db = get_db()
    
    # Get company-wide attendance policy
    attendance_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    
    if not attendance_policy:
        raise HTTPException(status_code=404, detail="Attendance policy not configured. Initialize default policies first.")
    
    # Extract rules into structured format
    rules = {r["rule_id"]: r for r in attendance_policy.get("rules", [])}
    
    config = {
        "policy_id": attendance_policy.get("id"),
        "policy_name": attendance_policy.get("name"),
        "working_days": rules.get("AT009", {}).get("list_value", DEFAULT_WORKING_DAYS),
        "working_days_short": rules.get("AT009", {}).get("value", "Mon,Tue,Wed,Thu,Fri,Sat"),
        "core_hours_start": rules.get("AT002", {}).get("value", "10:00"),
        "core_hours_end": rules.get("AT003", {}).get("value", "19:00"),
        "standard_work_hours": rules.get("AT001", {}).get("numeric_value", 9),
        "late_threshold_minutes": rules.get("AT004", {}).get("numeric_value", 15),
        "half_day_hours": rules.get("AT005", {}).get("numeric_value", 4),
        "full_day_hours": rules.get("AT006", {}).get("numeric_value", 8),
        "wfh_days_per_week": rules.get("AT007", {}).get("numeric_value", 2),
        "overtime_threshold_hours": rules.get("AT008", {}).get("numeric_value", 10),
        "grace_period_minutes": rules.get("AT010", {}).get("numeric_value", 30),
        "grace_days_per_month": rules.get("AT011", {}).get("numeric_value", 3),
        "late_penalty_amount": rules.get("AT012", {}).get("numeric_value", 100),
        "all_weekdays": WEEKDAYS,
        "updated_at": attendance_policy.get("updated_at"),
        "updated_by_name": attendance_policy.get("updated_by_name")
    }
    
    return config


@router.put("/attendance/config")
async def update_attendance_config(config: AttendanceConfigUpdate, current_user: User = Depends(get_current_user)):
    """
    Update company-wide attendance configuration.
    HR/Admin only. Updates the relevant rules in Business Rules SSOT.
    """
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can update attendance configuration")
    
    db = get_db()
    
    # Get existing attendance policy
    attendance_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    
    if not attendance_policy:
        raise HTTPException(status_code=404, detail="Attendance policy not found")
    
    # Update rules based on config
    rules = attendance_policy.get("rules", [])
    updated_rules = []
    changes = []
    
    for rule in rules:
        rule_id = rule.get("rule_id")
        updated_rule = {**rule}
        
        # AT002: Core Hours Start
        if rule_id == "AT002" and config.core_hours_start:
            old_val = rule.get("value")
            updated_rule["value"] = config.core_hours_start
            updated_rule["numeric_value"] = int(config.core_hours_start.split(":")[0])
            if old_val != config.core_hours_start:
                changes.append(f"Core Hours Start: {old_val} → {config.core_hours_start}")
        
        # AT003: Core Hours End
        if rule_id == "AT003" and config.core_hours_end:
            old_val = rule.get("value")
            updated_rule["value"] = config.core_hours_end
            updated_rule["numeric_value"] = int(config.core_hours_end.split(":")[0])
            if old_val != config.core_hours_end:
                changes.append(f"Core Hours End: {old_val} → {config.core_hours_end}")
        
        # AT007: WFH Days
        if rule_id == "AT007" and config.wfh_days_per_week is not None:
            old_val = rule.get("numeric_value")
            updated_rule["numeric_value"] = config.wfh_days_per_week
            if old_val != config.wfh_days_per_week:
                changes.append(f"WFH Days: {old_val} → {config.wfh_days_per_week}")
        
        # AT009: Working Days
        if rule_id == "AT009" and config.working_days:
            old_val = rule.get("list_value", [])
            short_names = [d[:3] for d in config.working_days]
            updated_rule["list_value"] = config.working_days
            updated_rule["value"] = ",".join(short_names)
            if old_val != config.working_days:
                changes.append(f"Working Days: {len(old_val)} days → {len(config.working_days)} days")
        
        # AT010: Grace Period Minutes
        if rule_id == "AT010" and config.grace_period_minutes is not None:
            old_val = rule.get("numeric_value")
            updated_rule["numeric_value"] = config.grace_period_minutes
            if old_val != config.grace_period_minutes:
                changes.append(f"Grace Period: {old_val} → {config.grace_period_minutes} mins")
        
        # AT011: Grace Days Per Month
        if rule_id == "AT011" and config.grace_days_per_month is not None:
            old_val = rule.get("numeric_value")
            updated_rule["numeric_value"] = config.grace_days_per_month
            if old_val != config.grace_days_per_month:
                changes.append(f"Grace Days: {old_val} → {config.grace_days_per_month}/month")
        
        # AT012: Late Penalty Amount
        if rule_id == "AT012" and config.late_penalty_amount is not None:
            old_val = rule.get("numeric_value")
            updated_rule["numeric_value"] = config.late_penalty_amount
            if old_val != config.late_penalty_amount:
                changes.append(f"Late Penalty: ₹{old_val} → ₹{config.late_penalty_amount}")
        
        updated_rules.append(updated_rule)
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.business_policies.update_one(
        {"id": attendance_policy["id"]},
        {"$set": {
            "rules": updated_rules,
            "updated_at": now,
            "updated_by": current_user.id,
            "updated_by_name": current_user.full_name
        }}
    )
    
    # Audit log
    if changes:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "attendance_config_updated",
            "entity_type": "business_policy",
            "entity_id": attendance_policy["id"],
            "user_id": current_user.id,
            "user_name": current_user.full_name,
            "details": {"changes": changes},
            "created_at": now
        })
    
    return {
        "message": "Attendance configuration updated successfully",
        "changes": changes
    }


@router.get("/attendance/overrides")
async def get_attendance_overrides(current_user: User = Depends(get_current_user)):
    """
    Get all role-wise and employee-wise attendance policy overrides.
    """
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles + hr_roles):
        raise HTTPException(status_code=403, detail="Only HR/Admin can view overrides")
    
    db = get_db()
    
    # Get role-specific overrides
    role_overrides = await db.business_policies.find(
        {"policy_type": "attendance", "scope": "role", "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    # Get employee-specific overrides
    employee_overrides = await db.business_policies.find(
        {"policy_type": "attendance", "scope": "employee", "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    # Get employee details for employee overrides
    for override in employee_overrides:
        emp_id = override.get("scope_value")
        if emp_id:
            employee = await db.employees.find_one(
                {"id": emp_id},
                {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
            )
            if employee:
                override["employee_code"] = employee.get("employee_id")
                override["employee_name"] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
                override["department"] = employee.get("department")
    
    return {
        "role_overrides": role_overrides,
        "employee_overrides": employee_overrides,
        "total_role_overrides": len(role_overrides),
        "total_employee_overrides": len(employee_overrides)
    }


@router.post("/attendance/override")
async def create_attendance_override(data: dict, current_user: User = Depends(get_current_user)):
    """
    Create a role-wise or employee-wise attendance policy override.
    
    Body: {
        "scope": "role" | "employee",
        "scope_value": "consultant" | "EMP001",
        "name": "Consultant Attendance Policy",
        "working_days": ["Monday", "Tuesday", ...],
        "core_hours_start": "10:30",
        "core_hours_end": "19:30",
        "reason": "Flexible schedule for consulting roles"
    }
    """
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can create overrides")
    
    db = get_db()
    
    scope = data.get("scope")  # "role" or "employee"
    scope_value = data.get("scope_value")  # role name or employee ID
    
    if scope not in ["role", "employee"]:
        raise HTTPException(status_code=400, detail="scope must be 'role' or 'employee'")
    
    if not scope_value:
        raise HTTPException(status_code=400, detail="scope_value is required")
    
    # Validate scope_value
    if scope == "employee":
        employee = await db.employees.find_one({"id": scope_value}, {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1})
        if not employee:
            # Try by employee_id code
            employee = await db.employees.find_one({"employee_id": scope_value}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1})
            if employee:
                scope_value = employee["id"]  # Use internal ID
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check for existing override
    existing = await db.business_policies.find_one({
        "policy_type": "attendance",
        "scope": scope,
        "scope_value": scope_value,
        "is_active": True
    })
    
    if existing:
        raise HTTPException(status_code=400, detail=f"An override already exists for this {scope}. Delete it first or update it.")
    
    # Get company policy as base
    company_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    
    if not company_policy:
        raise HTTPException(status_code=404, detail="Company attendance policy not found")
    
    # Build override rules - copy from company and modify
    base_rules = {r["rule_id"]: r for r in company_policy.get("rules", [])}
    override_rules = []
    
    for rule_id, rule in base_rules.items():
        updated_rule = {**rule}
        
        # Apply overrides
        if rule_id == "AT002" and data.get("core_hours_start"):
            updated_rule["value"] = data["core_hours_start"]
            updated_rule["numeric_value"] = int(data["core_hours_start"].split(":")[0])
        
        if rule_id == "AT003" and data.get("core_hours_end"):
            updated_rule["value"] = data["core_hours_end"]
            updated_rule["numeric_value"] = int(data["core_hours_end"].split(":")[0])
        
        if rule_id == "AT009" and data.get("working_days"):
            short_names = [d[:3] for d in data["working_days"]]
            updated_rule["list_value"] = data["working_days"]
            updated_rule["value"] = ",".join(short_names)
        
        if rule_id == "AT010" and data.get("grace_period_minutes") is not None:
            updated_rule["numeric_value"] = data["grace_period_minutes"]
        
        if rule_id == "AT011" and data.get("grace_days_per_month") is not None:
            updated_rule["numeric_value"] = data["grace_days_per_month"]
        
        if rule_id == "AT007" and data.get("wfh_days_per_week") is not None:
            updated_rule["numeric_value"] = data["wfh_days_per_week"]
        
        override_rules.append(updated_rule)
    
    now = datetime.now(timezone.utc).isoformat()
    today = today_ist()
    
    policy_name = data.get("name", f"Attendance Policy - {scope.title()}: {scope_value}")
    
    override_policy = {
        "id": str(uuid.uuid4()),
        "name": policy_name,
        "policy_type": "attendance",
        "description": data.get("reason", f"Custom attendance policy for {scope}: {scope_value}"),
        "scope": scope,
        "scope_value": scope_value,
        "rules": override_rules,
        "is_active": True,
        "effective_from": today,
        "created_at": now,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "updated_at": now,
        "base_policy_id": company_policy.get("id")
    }
    
    await db.business_policies.insert_one(override_policy)
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "attendance_override_created",
        "entity_type": "business_policy",
        "entity_id": override_policy["id"],
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {"scope": scope, "scope_value": scope_value, "name": policy_name},
        "created_at": now
    })
    
    return {
        "message": f"Attendance override created for {scope}: {scope_value}",
        "policy_id": override_policy["id"]
    }


@router.delete("/attendance/override/{policy_id}")
async def delete_attendance_override(policy_id: str, current_user: User = Depends(get_current_user)):
    """Delete an attendance policy override (reverts to company default)."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can delete overrides")
    
    db = get_db()
    
    # Ensure it's an override (not company policy)
    policy = await db.business_policies.find_one({"id": policy_id}, {"_id": 0})
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if policy.get("scope") == "company":
        raise HTTPException(status_code=400, detail="Cannot delete company-wide policy through this endpoint")
    
    result = await db.business_policies.delete_one({"id": policy_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {
        "message": f"Override deleted. {policy.get('scope')}: {policy.get('scope_value')} will use company defaults."
    }


@router.get("/effective/{policy_type}/{employee_id}")
async def get_effective_policy(policy_type: str, employee_id: str, current_user: User = Depends(get_current_user)):
    """Get the effective policy for an employee based on hierarchy"""
    db = get_db()
    
    # Get employee details
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        # Try by employee_id code
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Policy hierarchy: Employee > Role > Department > Company
    today = today_ist()
    
    # Try employee-specific
    policy = await db.business_policies.find_one({
        "policy_type": policy_type,
        "scope": "employee",
        "scope_value": employee.get("id"),
        "is_active": True,
        "effective_from": {"$lte": today}
    }, {"_id": 0})
    
    # Try role-specific
    if not policy and employee.get("designation"):
        policy = await db.business_policies.find_one({
            "policy_type": policy_type,
            "scope": "role",
            "scope_value": employee["designation"],
            "is_active": True,
            "effective_from": {"$lte": today}
        }, {"_id": 0})
    
    # Try department-specific
    if not policy and employee.get("department"):
        policy = await db.business_policies.find_one({
            "policy_type": policy_type,
            "scope": "department",
            "scope_value": employee["department"],
            "is_active": True,
            "effective_from": {"$lte": today}
        }, {"_id": 0})
    
    # Fall back to company-wide
    if not policy:
        policy = await db.business_policies.find_one({
            "policy_type": policy_type,
            "scope": "company",
            "is_active": True,
            "effective_from": {"$lte": today}
        }, {"_id": 0})
    
    if not policy:
        raise HTTPException(status_code=404, detail=f"No active {policy_type} policy found")
    
    return policy


async def initialize_default_policies(db, user_id: str):
    """Initialize default policies if none exist"""
    now = datetime.now(timezone.utc).isoformat()
    today = today_ist()
    
    defaults = [
        DEFAULT_TRAVEL_POLICY,
        DEFAULT_EXPENSE_POLICY,
        DEFAULT_ATTENDANCE_POLICY,
        DEFAULT_PAYROLL_RULES,
        DEFAULT_GENERAL_HR_POLICY,
        DEFAULT_LEAVE_POLICY
    ]
    
    for default in defaults:
        existing = await db.business_policies.find_one({
            "policy_type": default["policy_type"],
            "scope": "company"
        })
        
        if not existing:
            policy = {**default}
            policy["id"] = str(uuid.uuid4())
            policy["created_at"] = now
            policy["created_by"] = user_id
            policy["updated_at"] = now
            policy["effective_from"] = today
            policy["is_active"] = True
            await db.business_policies.insert_one(policy)



# ==================== RULE ENGINE ENDPOINTS ====================

@router.post("/engine/evaluate-condition")
async def evaluate_condition(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate a condition expression with given context.
    
    Body: {
        "condition": "basic_salary > 15000 AND department == 'Sales'",
        "context": {"basic_salary": 20000, "department": "Sales"}
    }
    """
    from services.rule_engine import create_rule_engine
    
    condition = data.get("condition", "")
    context = data.get("context", {})
    
    if not condition:
        raise HTTPException(status_code=400, detail="Condition is required")
    
    try:
        engine = create_rule_engine(context)
        result, explanation = engine.evaluate_condition(condition)
        
        return {
            "condition": condition,
            "result": result,
            "explanation": explanation,
            "context_used": context
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/engine/evaluate-formula")
async def evaluate_formula(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate a formula expression with given context.
    
    Body: {
        "formula": "basic_salary * 0.12",
        "context": {"basic_salary": 20000}
    }
    """
    from services.rule_engine import create_rule_engine
    
    formula = data.get("formula", "")
    context = data.get("context", {})
    
    if not formula:
        raise HTTPException(status_code=400, detail="Formula is required")
    
    try:
        engine = create_rule_engine(context)
        result, explanation = engine.evaluate_formula(formula)
        
        return {
            "formula": formula,
            "result": result,
            "explanation": explanation,
            "context_used": context
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/engine/calculate-statutory")
async def calculate_statutory_deductions(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate statutory deductions (PF, ESI, PT) based on payroll rules.
    
    Body: {
        "basic_salary": 25000,
        "gross_salary": 50000,
        "employee_id": "EMP001" (optional)
    }
    """
    from services.rule_engine import create_rule_engine
    
    db = get_db()
    
    employee_data = {
        "basic_salary": data.get("basic_salary", 0),
        "gross_salary": data.get("gross_salary", 0),
        "department": data.get("department", ""),
        "designation": data.get("designation", ""),
    }
    
    # Get payroll rules
    payroll_policy = await db.business_policies.find_one(
        {"policy_type": "payroll", "is_active": True},
        {"_id": 0}
    )
    
    if not payroll_policy:
        raise HTTPException(status_code=404, detail="No active payroll policy found")
    
    try:
        engine = create_rule_engine(employee_data)
        statutory = engine.apply_statutory_rules(employee_data, payroll_policy.get("rules", []))
        
        return {
            "input": employee_data,
            "statutory_deductions": statutory,
            "policy_used": payroll_policy.get("name")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/engine/calculate-lop")
async def calculate_lop_deduction(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate Loss of Pay deduction.
    
    Body: {
        "basic_salary": 25000,
        "working_days": 26,
        "lop_days": 2
    }
    """
    from services.rule_engine import create_rule_engine
    
    db = get_db()
    
    employee_data = {
        "basic_salary": data.get("basic_salary", 0),
        "gross_salary": data.get("gross_salary", data.get("basic_salary", 0)),
        "working_days": data.get("working_days", 26),
        "lop_days": data.get("lop_days", 0),
    }
    
    # Get payroll rules
    payroll_policy = await db.business_policies.find_one(
        {"policy_type": "payroll", "is_active": True},
        {"_id": 0}
    )
    
    rules = payroll_policy.get("rules", []) if payroll_policy else []
    
    try:
        engine = create_rule_engine(employee_data)
        lop_result = engine.calculate_lop_deduction(employee_data, rules)
        
        return {
            "input": employee_data,
            "lop_deduction": lop_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/engine/ctc-components")
async def get_ctc_components(current_user: User = Depends(get_current_user)):
    """Get all available CTC components with their properties"""
    from services.rule_engine import RuleEngine
    
    components = []
    for key, info in RuleEngine.CTC_COMPONENTS.items():
        components.append({
            "key": key,
            "name": key.replace("_", " ").title(),
            **info
        })
    
    # Group by type
    grouped = {
        "earnings": [c for c in components if c.get("type") == "earning"],
        "deductions": [c for c in components if c.get("type") == "deduction"],
        "employer_contributions": [c for c in components if c.get("type") == "employer_contribution"],
        "reimbursements": [c for c in components if c.get("type") == "reimbursement"],
    }
    
    return {
        "components": components,
        "grouped": grouped,
        "total_count": len(components)
    }


@router.post("/engine/simulate-payroll")
async def simulate_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Simulate payroll calculation with all rules applied.
    
    Body: {
        "annual_ctc": 600000,
        "basic_percentage": 40,
        "hra_percentage": 50,
        "working_days": 26,
        "present_days": 24,
        "lop_days": 2,
        "expense_reimbursement": 5000
    }
    """
    from services.rule_engine import (
        create_rule_engine, calculate_basic_salary, 
        calculate_hra, calculate_pf, calculate_esi
    )
    
    db = get_db()
    
    # Extract inputs
    annual_ctc = data.get("annual_ctc", 600000)
    basic_pct = data.get("basic_percentage", 40)
    hra_pct = data.get("hra_percentage", 50)
    working_days = data.get("working_days", 26)
    present_days = data.get("present_days", working_days)
    lop_days = data.get("lop_days", 0)
    expense_reimbursement = data.get("expense_reimbursement", 0)
    
    # Calculate base components
    monthly_ctc = annual_ctc / 12
    basic_salary = calculate_basic_salary(annual_ctc, basic_pct)
    hra = calculate_hra(basic_salary, hra_pct)
    
    # Calculate gross (before special allowance balancing)
    initial_gross = basic_salary + hra
    special_allowance = round(monthly_ctc - initial_gross, 2)
    if special_allowance < 0:
        special_allowance = 0
    
    gross_salary = basic_salary + hra + special_allowance
    
    # Get payroll policy
    payroll_policy = await db.business_policies.find_one(
        {"policy_type": "payroll", "is_active": True},
        {"_id": 0}
    )
    
    # Calculate statutory deductions
    employee_data = {
        "basic_salary": basic_salary,
        "gross_salary": gross_salary,
        "working_days": working_days,
        "lop_days": lop_days,
        "annual_ctc": annual_ctc
    }
    
    engine = create_rule_engine(employee_data)
    rules = payroll_policy.get("rules", []) if payroll_policy else []
    
    statutory = engine.apply_statutory_rules(employee_data, rules)
    lop = engine.calculate_lop_deduction(employee_data, rules)
    
    # Calculate net salary
    total_earnings = gross_salary + expense_reimbursement
    total_deductions = statutory["total_deductions"] + lop["total_deduction"]
    net_salary = round(total_earnings - total_deductions, 2)
    
    return {
        "input": {
            "annual_ctc": annual_ctc,
            "basic_percentage": basic_pct,
            "hra_percentage": hra_pct,
            "working_days": working_days,
            "present_days": present_days,
            "lop_days": lop_days,
            "expense_reimbursement": expense_reimbursement
        },
        "earnings": {
            "basic_salary": basic_salary,
            "hra": hra,
            "special_allowance": special_allowance,
            "gross_salary": gross_salary,
            "expense_reimbursement": expense_reimbursement,
            "total_earnings": total_earnings
        },
        "deductions": {
            "pf_employee": statutory["pf_employee"],
            "esi_employee": statutory["esi_employee"],
            "professional_tax": statutory["professional_tax"],
            "lop_deduction": lop["total_deduction"],
            "total_deductions": total_deductions
        },
        "employer_contributions": {
            "pf_employer": statutory["pf_employer"],
            "esi_employer": statutory["esi_employer"],
            "total": statutory["total_employer_contribution"]
        },
        "summary": {
            "gross_salary": gross_salary,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "cost_to_company_monthly": round(gross_salary + statutory["total_employer_contribution"], 2)
        },
        "rules_applied": statutory["rules_applied"],
        "breakdown": statutory["breakdown"] + [lop] if lop["total_deduction"] > 0 else statutory["breakdown"]
    }
