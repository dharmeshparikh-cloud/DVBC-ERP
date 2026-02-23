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
from .deps import get_db
from .models import User
from .auth import get_current_user
from services.email_service import send_email
from services.funnel_notifications import proforma_generated_email, get_sales_manager_emails

router = APIRouter(prefix="/quotations", tags=["Quotations"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lead-record-mgmt.preview.emergentagent.com").replace("/api", "")


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
    """Finalize and lock a quotation"""
    db = get_db()
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft quotations can be finalized")
    
    from datetime import timedelta
    valid_until = (datetime.now(timezone.utc) + timedelta(days=quotation.get("validity_days", 30))).strftime("%Y-%m-%d")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {
            "$set": {
                "status": "finalized",
                "valid_until": valid_until,
                "finalized_by": current_user.id,
                "finalized_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Quotation finalized", "valid_until": valid_until}
