"""
Reports Router - Report generation and downloads.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta
from .deps import get_db, MANAGER_ROLES, HR_ROLES, get_role_group, has_role
from .models import User
from .deps import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# Report definitions with categories
REPORT_DEFINITIONS = [
    # HR Reports
    {
        "id": "employee_attendance",
        "name": "Employee Attendance Report",
        "description": "Daily/monthly attendance summary with check-in/out times",
        "category": "HR",
        "roles": ["admin", "hr_manager", "hr_executive"],
        "icon": "Clock"
    },
    {
        "id": "leave_summary",
        "name": "Leave Summary Report",
        "description": "Leave balances and utilization by employee",
        "category": "HR",
        "roles": ["admin", "hr_manager", "hr_executive"],
        "icon": "Calendar"
    },
    {
        "id": "payroll_summary",
        "name": "Payroll Summary Report",
        "description": "Monthly payroll breakdown with deductions",
        "category": "HR",
        "roles": ["admin", "hr_manager"],
        "icon": "DollarSign"
    },
    {
        "id": "headcount",
        "name": "Headcount Report",
        "description": "Employee count by department, location, and status",
        "category": "HR",
        "roles": ["admin", "hr_manager", "hr_executive"],
        "icon": "Users"
    },
    {
        "id": "new_hires",
        "name": "New Hires Report",
        "description": "Recently onboarded employees",
        "category": "HR",
        "roles": ["admin", "hr_manager"],
        "icon": "UserPlus"
    },
    {
        "id": "exit_report",
        "name": "Exit/Attrition Report",
        "description": "Employee exits and attrition analysis",
        "category": "HR",
        "roles": ["admin", "hr_manager"],
        "icon": "UserMinus"
    },
    # Sales Reports
    {
        "id": "sales_summary",
        "name": "Sales Pipeline Report",
        "description": "Lead and deal progression summary",
        "category": "Sales",
        "roles": ["admin", "sales_manager", "manager", "sr_manager"],
        "icon": "TrendingUp"
    },
    {
        "id": "revenue_forecast",
        "name": "Revenue Forecast",
        "description": "Projected revenue by quarter",
        "category": "Sales",
        "roles": ["admin", "sales_manager", "manager", "hr_manager"],
        "icon": "BarChart"
    },
    {
        "id": "client_report",
        "name": "Client Report",
        "description": "Active clients and engagement status",
        "category": "Sales",
        "roles": ["admin", "sales_manager", "manager"],
        "icon": "Building"
    },
    # Operations Reports
    {
        "id": "project_status",
        "name": "Project Status Report",
        "description": "Active projects and their status",
        "category": "Operations",
        "roles": ["admin", "manager", "sr_manager", "principal_consultant"],
        "icon": "Briefcase"
    },
    {
        "id": "consultant_utilization",
        "name": "Consultant Utilization",
        "description": "Billable hours and utilization rates",
        "category": "Operations",
        "roles": ["admin", "manager", "sr_manager", "hr_manager"],
        "icon": "Activity"
    },
    {
        "id": "expense_report",
        "name": "Expense Report",
        "description": "Employee expenses and reimbursements",
        "category": "Operations",
        "roles": ["admin", "hr_manager", "manager"],
        "icon": "Receipt"
    },
    # Finance Reports
    {
        "id": "statutory_compliance",
        "name": "Statutory Compliance",
        "description": "PF, ESI, PT compliance status",
        "category": "Finance",
        "roles": ["admin", "hr_manager"],
        "icon": "Shield"
    },
    {
        "id": "tds_report",
        "name": "TDS Report",
        "description": "Tax deducted at source summary",
        "category": "Finance",
        "roles": ["admin", "hr_manager"],
        "icon": "FileText"
    },
]


@router.get("")
async def get_available_reports(current_user: User = Depends(get_current_user)):
    """Get list of available reports based on role"""
    available = []
    for report in REPORT_DEFINITIONS:
        if has_role(current_user.role, report["roles"]):
            available.append({
                "id": report["id"],
                "name": report["name"],
                "description": report["description"],
                "category": report["category"],
                "icon": report.get("icon", "FileText"),
                "roles": report["roles"]
            })
    return available


@router.get("/categories")
async def get_report_categories(current_user: User = Depends(get_current_user)):
    """Get available report categories"""
    return [
        {"id": "HR", "name": "HR Reports", "icon": "Users", "color": "purple"},
        {"id": "Sales", "name": "Sales Reports", "icon": "TrendingUp", "color": "blue"},
        {"id": "Operations", "name": "Operations Reports", "icon": "Briefcase", "color": "amber"},
        {"id": "Finance", "name": "Finance Reports", "icon": "DollarSign", "color": "emerald"},
    ]


@router.get("/stats")
async def get_report_stats(current_user: User = Depends(get_current_user)):
    """Get report statistics"""
    db = get_db()
    
    # Count reports by category available to user
    available_reports = [r for r in REPORT_DEFINITIONS if has_role(current_user.role, r["roles"])]
    category_counts = {}
    for r in available_reports:
        cat = r["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    return {
        "total_reports": len(available_reports),
        "by_category": category_counts,
        "last_generated": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    format: str = "json",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Generate a report"""
    db = get_db()
    
    # Find report definition
    report_def = next((r for r in REPORT_DEFINITIONS if r["id"] == report_id), None)
    if not report_def:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not has_role(current_user.role, report_def["roles"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
    
    # Generate report data based on type
    data = await generate_report_data(db, report_id, start_date, end_date)
    
    return {
        "report_id": report_id,
        "report_name": report_def["name"],
        "category": report_def["category"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.full_name,
        "data": data
    }


@router.get("/{report_id}/preview")
async def preview_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get report preview (limited data)"""
    db = get_db()
    
    report_def = next((r for r in REPORT_DEFINITIONS if r["id"] == report_id), None)
    if not report_def:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not has_role(current_user.role, report_def["roles"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
    
    # Get limited preview data
    data = await generate_report_data(db, report_id, limit=10)
    
    return {
        "report_id": report_id,
        "report_name": report_def["name"],
        "preview": True,
        "data": data
    }


async def generate_report_data(db, report_id: str, start_date: str = None, end_date: str = None, limit: int = None):
    """Generate report data based on report type"""
    
    if report_id == "employee_attendance":
        employees = await db.employees.find(
            {"is_active": True}, 
            {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
        ).to_list(limit or 100)
        
        attendance_records = await db.attendance.find({}).to_list(limit or 500)
        
        return {
            "total_employees": len(employees),
            "attendance_records": len(attendance_records),
            "employees": employees[:10] if limit else employees
        }
    
    elif report_id == "leave_summary":
        leave_balances = await db.leave_balances.find({}, {"_id": 0}).to_list(limit or 100)
        leaves = await db.leaves.find({}, {"_id": 0}).to_list(limit or 500)
        
        return {
            "total_leave_records": len(leaves),
            "balances": leave_balances[:10] if limit else leave_balances
        }
    
    elif report_id == "payroll_summary":
        payroll_records = await db.payroll.find({}, {"_id": 0}).to_list(limit or 100)
        
        total_gross = sum(p.get("gross_salary", 0) for p in payroll_records)
        total_deductions = sum(p.get("total_deductions", 0) for p in payroll_records)
        total_net = sum(p.get("net_salary", 0) for p in payroll_records)
        
        return {
            "total_records": len(payroll_records),
            "total_gross": total_gross,
            "total_deductions": total_deductions,
            "total_net": total_net,
            "records": payroll_records[:10] if limit else payroll_records
        }
    
    elif report_id == "headcount":
        employees = await db.employees.find(
            {"is_active": True},
            {"_id": 0, "department": 1, "designation": 1, "location": 1}
        ).to_list(1000)
        
        by_department = {}
        by_designation = {}
        for emp in employees:
            dept = emp.get("department", "Unknown")
            desig = emp.get("designation", "Unknown")
            by_department[dept] = by_department.get(dept, 0) + 1
            by_designation[desig] = by_designation.get(desig, 0) + 1
        
        return {
            "total_headcount": len(employees),
            "by_department": by_department,
            "by_designation": by_designation
        }
    
    elif report_id == "new_hires":
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        new_employees = await db.employees.find(
            {"created_at": {"$gte": thirty_days_ago}},
            {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1, "created_at": 1}
        ).to_list(limit or 50)
        
        return {
            "period": "Last 30 days",
            "total_new_hires": len(new_employees),
            "employees": new_employees
        }
    
    elif report_id == "sales_summary":
        leads = await db.leads.find({}, {"_id": 0, "status": 1, "value": 1}).to_list(500)
        
        status_counts = {}
        total_value = 0
        for lead in leads:
            status = lead.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            total_value += lead.get("value", 0)
        
        return {
            "total_leads": len(leads),
            "by_status": status_counts,
            "total_pipeline_value": total_value
        }
    
    elif report_id == "project_status":
        projects = await db.projects.find({}, {"_id": 0}).to_list(limit or 100)
        
        status_counts = {}
        for p in projects:
            status = p.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_projects": len(projects),
            "by_status": status_counts,
            "projects": projects[:10] if limit else projects
        }
    
    elif report_id == "expense_report":
        expenses = await db.expenses.find({}, {"_id": 0}).to_list(limit or 500)
        
        total_amount = sum(e.get("amount", 0) for e in expenses)
        approved = [e for e in expenses if e.get("status") == "approved"]
        pending = [e for e in expenses if e.get("status") == "pending"]
        
        return {
            "total_expenses": len(expenses),
            "total_amount": total_amount,
            "approved_count": len(approved),
            "pending_count": len(pending)
        }
    
    elif report_id == "consultant_utilization":
        # Calculate utilization from timesheet/attendance
        employees = await db.employees.find(
            {"is_active": True, "role": {"$in": ["consultant", "sr_consultant", "principal_consultant"]}},
            {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1}
        ).to_list(100)
        
        return {
            "total_consultants": len(employees),
            "consultants": employees
        }
    
    # Default empty data
    return {"message": "Report data not implemented yet"}


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "excel",
    current_user: User = Depends(get_current_user)
):
    """Download report in specified format"""
    report_def = next((r for r in REPORT_DEFINITIONS if r["id"] == report_id), None)
    if not report_def:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not has_role(current_user.role, report_def["roles"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "message": "Report download - requires file generation integration",
        "report_id": report_id,
        "format": format
    }


@router.get("/downloads/{report_type}")
async def get_downloadable_report(
    report_type: str,
    current_user: User = Depends(get_current_user)
):
    """Get downloadable report file"""
    return {
        "message": "Report download endpoint",
        "report_type": report_type
    }
