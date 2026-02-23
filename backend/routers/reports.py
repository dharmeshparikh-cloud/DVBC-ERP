"""
Reports Router - Report generation and downloads.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from .deps import get_db, MANAGER_ROLES, HR_ROLES, get_role_group, has_role
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


def get_report_roles_from_rbac(report_type: str) -> list:
    """Get roles for a report type using RBAC service"""
    report_group_mapping = {
        "sales_summary": "SALES_MANAGER_ROLES",
        "employee_attendance": "HR_ADMIN_ROLES",
        "project_status": "PROJECT_ROLES",
        "revenue_forecast": "MANAGER_ROLES",
        "consultant_utilization": "MANAGER_ROLES",
    }
    group_name = report_group_mapping.get(report_type, "ADMIN_ROLES")
    return get_role_group(group_name, fail_closed=False) or ["admin"]


@router.get("")
async def get_available_reports(current_user: User = Depends(get_current_user)):
    """Get list of available reports based on role"""
    db = get_db()
    
    # RBAC Migration: Dynamic role resolution
    reports = [
        {"id": "sales_summary", "name": "Sales Summary", "roles": get_report_roles_from_rbac("sales_summary")},
        {"id": "employee_attendance", "name": "Employee Attendance", "roles": get_report_roles_from_rbac("employee_attendance")},
        {"id": "project_status", "name": "Project Status", "roles": get_report_roles_from_rbac("project_status")},
        {"id": "revenue_forecast", "name": "Revenue Forecast", "roles": get_report_roles_from_rbac("revenue_forecast")},
        {"id": "consultant_utilization", "name": "Consultant Utilization", "roles": get_report_roles_from_rbac("consultant_utilization")},
    ]
    
    available = [r for r in reports if has_role(current_user.role, r["roles"])]
    return available


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
    
    # RBAC Migration: Use database-driven role check
    report_config = {
        "sales_summary": {"roles": get_report_roles_from_rbac("sales_summary")},
        "employee_attendance": {"roles": get_report_roles_from_rbac("employee_attendance")},
        "project_status": {"roles": get_report_roles_from_rbac("project_status")},
    }
    
    if report_id not in report_config:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not has_role(current_user.role, report_config[report_id]["roles"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
    
    # Basic report data
    if report_id == "sales_summary":
        leads = await db.leads.count_documents({})
        agreements = await db.agreements.count_documents({"status": "signed"})
        return {
            "report_id": report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "total_leads": leads,
                "signed_agreements": agreements
            }
        }
    elif report_id == "employee_attendance":
        employees = await db.employees.count_documents({"is_active": True})
        return {
            "report_id": report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "total_employees": employees
            }
        }
    elif report_id == "project_status":
        projects = await db.projects.find({}, {"_id": 0, "status": 1}).to_list(1000)
        status_counts = {}
        for p in projects:
            status = p.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        return {
            "report_id": report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "total_projects": len(projects),
                "by_status": status_counts
            }
        }
    
    return {"report_id": report_id, "data": {}}


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "excel",
    current_user: User = Depends(get_current_user)
):
    """Download report in specified format"""
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
