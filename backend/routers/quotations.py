"""
Quotations Router - Quotation/Proforma Invoice creation and management.
Sends email notification when proforma is generated.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import os
from pydantic import BaseModel
from .deps import get_db, get_role_group, has_role
from .models import User
from .auth import get_current_user
from services.email_service import send_email
from services.funnel_notifications import proforma_generated_email, get_sales_manager_emails

router = APIRouter(prefix="/quotations", tags=["Quotations"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://portal-access-16.preview.emergentagent.com").replace("/api", "")


class QuotationCreate(BaseModel):
    lead_id: str
    pricing_plan_id: Optional[str] = None
    title: Optional[str] = "Quotation"
    client_name: str
    client_email: Optional[str] = ""
    line_items: Optional[List[dict]] = []
    subtotal: float = 0
    tax_rate: float = 18
    tax_amount: float = 0
    total: float = 0
    validity_days: int = 30
    notes: Optional[str] = ""


@router.post("")
async def create_quotation(
    data: QuotationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create a new quotation and send email notification"""
    db = get_db()
    
    lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    quotation_id = str(uuid.uuid4())
    quotation_number = f"QT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(days=data.validity_days)).strftime("%Y-%m-%d")
    
    quotation_doc = {
        "id": quotation_id,
        "quotation_number": quotation_number,
        "lead_id": data.lead_id,
        "pricing_plan_id": data.pricing_plan_id,
        "title": data.title,
        "client_name": data.client_name or lead.get("company", ""),
        "client_email": data.client_email or lead.get("email", ""),
        "line_items": data.line_items or [],
        "subtotal": data.subtotal,
        "tax_rate": data.tax_rate,
        "tax_amount": data.tax_amount,
        "total": data.total,
        "validity_days": data.validity_days,
        "valid_until": valid_until,
        "notes": data.notes,
        "status": "draft",
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.quotations.insert_one(quotation_doc)
    quotation_doc.pop("_id", None)
    
    # Client email from lead
    client_email = data.client_email or lead.get("email", "")
    
    # Send email notification in background
    async def send_proforma_notification():
        try:
            manager_emails = await get_sales_manager_emails(db)
            email_data = proforma_generated_email(
                lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                company=lead.get("company", "Unknown"),
                quotation_number=quotation_number,
                quotation_id=quotation_id,
                total_amount=data.total,
                currency="INR",
                valid_until=valid_until,
                items_count=len(data.line_items or []),
                payment_terms=data.notes or "As per agreement",
                salesperson_name=current_user.full_name,
                client_email=client_email,
                app_url=APP_URL
            )
            
            # Send to managers
            for email in manager_emails:
                await send_email(
                    to_email=email,
                    subject=email_data["subject"],
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
            
            # Send to client if email exists
            if client_email:
                await send_email(
                    to_email=client_email,
                    subject=f"Your Quotation #{quotation_number} from DVBC",
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
        except Exception as e:
            print(f"Failed to send proforma notification: {e}")
    
    background_tasks.add_task(send_proforma_notification)
    
    return quotation_doc


@router.get("")
async def get_quotations(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get quotations with filters"""
    db = get_db()
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if status:
        query["status"] = status
    
    quotations = await db.quotations.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return quotations


@router.patch("/{quotation_id}/finalize")
async def finalize_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """
    Finalize and lock a quotation.
    
    ACCESS: Only the creator's Reporting Manager, Sales Manager roles, or Admin can finalize.
    This ensures proper oversight before committing to client pricing.
    
    WORKFLOW:
    - Quotation must be in 'draft' status
    - Reporting Manager or Sales Manager+ approves → status: 'finalized'
    - Quotation becomes locked and valid_until date is set
    """
    db = get_db()
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft quotations can be finalized")
    
    # Get creator's employee record to find their reporting manager
    creator_id = quotation.get("created_by")
    creator_employee = await db.employees.find_one({"user_id": creator_id}, {"_id": 0})
    
    # Check authorization: Admin, Sales Manager roles, or Reporting Manager
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    manager_roles = get_role_group("SALES_MANAGER_ROLES", fail_closed=False) or ["sales_manager", "sr_manager"]
    
    is_admin = has_role(current_user.role, admin_roles)
    is_sales_manager = has_role(current_user.role, manager_roles)
    
    # Check if current user is the reporting manager of the creator
    is_reporting_manager = False
    if creator_employee and creator_employee.get("reporting_manager_id"):
        rm_id = creator_employee.get("reporting_manager_id")
        # Reporting manager can be stored as user_id or employee_id
        current_emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
        if current_emp:
            is_reporting_manager = (
                rm_id == current_user.id or 
                rm_id == current_emp.get("id") or 
                rm_id == current_emp.get("employee_id")
            )
    
    # Creator cannot finalize their own quotation (separation of duties)
    if creator_id == current_user.id and not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="You cannot finalize your own quotation. Please request approval from your Reporting Manager."
        )
    
    if not (is_admin or is_sales_manager or is_reporting_manager):
        raise HTTPException(
            status_code=403, 
            detail="Only Reporting Manager, Sales Manager, or Admin can finalize quotations"
        )
    
    valid_until = (datetime.now(timezone.utc) + timedelta(days=quotation.get("validity_days", 30))).strftime("%Y-%m-%d")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {
            "$set": {
                "status": "finalized",
                "valid_until": valid_until,
                "finalized_by": current_user.id,
                "finalized_by_name": current_user.full_name,
                "finalized_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Log audit trail
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "quotation_finalized",
        "entity_type": "quotation",
        "entity_id": quotation_id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {
            "quotation_number": quotation.get("quotation_number"),
            "total": quotation.get("total"),
            "created_by": creator_id,
            "approval_type": "admin" if is_admin else ("sales_manager" if is_sales_manager else "reporting_manager")
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Quotation finalized", "valid_until": valid_until, "finalized_by": current_user.full_name}
