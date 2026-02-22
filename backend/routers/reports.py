"""
Reports Router - Report generation and downloads.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from .deps import get_db, MANAGER_ROLES, HR_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("")
async def get_available_reports(current_user: User = Depends(get_current_user)):
    """Get list of available reports based on role"""
    db = get_db()
    
    reports = [
        {"id": "sales_summary", "name": "Sales Summary", "roles": ["admin", "sales_manager", "manager"]},
        {"id": "employee_attendance", "name": "Employee Attendance", "roles": ["admin", "hr_manager"]},
        {"id": "project_status", "name": "Project Status", "roles": ["admin", "principal_consultant", "manager"]},
        {"id": "revenue_forecast", "name": "Revenue Forecast", "roles": ["admin", "manager"]},
        {"id": "consultant_utilization", "name": "Consultant Utilization", "roles": ["admin", "manager"]},
    ]
    
    available = [r for r in reports if current_user.role in r["roles"]]
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
    
    report_config = {
        "sales_summary": {"roles": ["admin", "sales_manager", "manager"]},
        "employee_attendance": {"roles": ["admin", "hr_manager"]},
        "project_status": {"roles": ["admin", "principal_consultant", "manager"]},
    }
    
    if report_id not in report_config:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if current_user.role not in report_config[report_id]["roles"]:
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
