"""
Quotations Router - Quotation/Proforma Invoice creation and management.
Sends email notification when proforma is generated.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from utils.timezone import today_ist, current_month_ist, now_ist
import uuid
import os
from pydantic import BaseModel
from .deps import get_db, get_role_group, has_role
from .models import User
from .deps import get_current_user
from services.email_service import send_email
from services.funnel_notifications import proforma_generated_email, get_sales_manager_emails

router = APIRouter(prefix="/quotations", tags=["Quotations"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://unified-erp-gov.preview.emergentagent.com").replace("/api", "")


class QuotationCreate(BaseModel):
    lead_id: str
    pricing_plan_id: Optional[str] = None
    title: Optional[str] = "Quotation"
    client_name: Optional[str] = None
    client_email: Optional[str] = ""
    client_gstin: Optional[str] = ""
    line_items: Optional[List[dict]] = []
    subtotal: Optional[float] = 0
    tax_rate: float = 18
    tax_amount: Optional[float] = 0
    total: Optional[float] = 0
    validity_days: int = 30
    notes: Optional[str] = ""
    payment_terms: Optional[str] = ""
    terms_and_conditions: Optional[str] = ""
    base_rate_per_meeting: Optional[float] = 12500


@router.post("")
async def create_quotation(
    data: QuotationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new quotation and send email notification.
    
    FUNNEL PREREQUISITES:
    1. Pricing Plan must exist for this lead
    2. SOW must exist with at least 1 scope item
    """
    db = get_db()
    
    lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # FUNNEL VALIDATION 1: Check if pricing plan exists for this lead
    pricing_plan = await db.pricing_plans.find_one({"lead_id": data.lead_id}, {"_id": 0})
    if not pricing_plan:
        raise HTTPException(
            status_code=400,
            detail="Cannot create quotation: A Pricing Plan must be created first. Please complete the Pricing step in the sales funnel."
        )
    
    # If pricing_plan_id specified, use that plan; otherwise use any plan for the lead
    if data.pricing_plan_id:
        specific_plan = await db.pricing_plans.find_one({"id": data.pricing_plan_id}, {"_id": 0})
        if specific_plan:
            pricing_plan = specific_plan
    
    # FUNNEL VALIDATION 2: Check if SOW exists with at least 1 scope item
    sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan.get("id")}, {"_id": 0})
    if not sow:
        # Also check legacy sow collection
        sow = await db.sow.find_one({"pricing_plan_id": pricing_plan.get("id")}, {"_id": 0})
    
    if not sow:
        raise HTTPException(
            status_code=400,
            detail="SOW_REQUIRED: Cannot create quotation without Scope of Work. Please define at least one scope item in the SOW Builder first.",
            headers={"X-Redirect-To": f"/sales-funnel/sow/{pricing_plan.get('id')}?lead_id={data.lead_id}"}
        )
    
    # Check if SOW has at least 1 scope item
    sow_scopes = sow.get("scopes") or sow.get("items") or []
    if len(sow_scopes) == 0:
        raise HTTPException(
            status_code=400,
            detail="SOW_EMPTY: SOW exists but has no scope items. Please add at least one scope item before creating a quotation.",
            headers={"X-Redirect-To": f"/sales-funnel/sow/{pricing_plan.get('id')}?lead_id={data.lead_id}"}
        )
    
    # Auto-calculate financial fields from pricing plan if not provided
    subtotal = data.subtotal
    total_meetings = 0
    team_data = pricing_plan.get("team_deployment") or pricing_plan.get("consultants") or []
    
    if (subtotal == 0 or subtotal is None) and team_data:
        base_rate = data.base_rate_per_meeting or 12500
        for member in team_data:
            meetings = (member.get("committed_meetings") or member.get("meetings") or 0) * (member.get("count") or 1)
            rate = member.get("rate_per_meeting") or base_rate
            subtotal += meetings * rate
            total_meetings += meetings
    
    if subtotal == 0:
        subtotal = pricing_plan.get("total_amount") or pricing_plan.get("total_investment") or 0
    
    tax_amount = data.tax_amount if data.tax_amount else round(subtotal * (data.tax_rate / 100), 2)
    grand_total = subtotal + tax_amount
    
    # SSOT: Client fields ALWAYS come from Lead
    client_name = lead.get("company", "") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    quotation_id = str(uuid.uuid4())
    quotation_number = f"QT-{now_ist().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    valid_until = (datetime.now(timezone.utc) + timedelta(days=data.validity_days)).strftime("%Y-%m-%d")
    
    # SSOT: All client fields from Lead
    client_email = lead.get("email", "")
    client_phone = lead.get("phone", "") or lead.get("mobile", "")
    client_address = lead.get("address", "") or lead.get("company_address", "")
    client_gstin = lead.get("gstin", "") or lead.get("gst_number", "")
    
    quotation_doc = {
        "id": quotation_id,
        "quotation_number": quotation_number,
        "lead_id": data.lead_id,
        "pricing_plan_id": data.pricing_plan_id or pricing_plan.get("id"),
        "sow_id": sow.get("id"),  # Link to SOW for traceability
        "has_sow": True,  # Flag for frontend badge
        "title": data.title,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": client_phone,
        "client_address": client_address,
        "client_gstin": client_gstin,
        "line_items": data.line_items or [],
        "subtotal": subtotal,
        "tax_rate": data.tax_rate,
        "tax_amount": tax_amount,
        "gst_amount": tax_amount,
        "total": grand_total,
        "grand_total": grand_total,
        "total_meetings": total_meetings,
        "validity_days": data.validity_days,
        "valid_until": valid_until,
        "notes": data.notes,
        "payment_terms": data.payment_terms or "ADVANCE",
        "terms_and_conditions": data.terms_and_conditions or "",
        "status": "draft",
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.quotations.insert_one(quotation_doc)
    quotation_doc.pop("_id", None)
    
    # Client email from Lead (SSOT)
    # Already set from lead above
    
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



@router.put("/{quotation_id}")
async def update_quotation(quotation_id: str, data: QuotationCreate, current_user: User = Depends(get_current_user)):
    """Update an existing quotation."""
    db = get_db()
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") == "finalized":
        raise HTTPException(status_code=400, detail="Cannot edit a finalized quotation")
    
    lead = await db.leads.find_one({"id": data.lead_id or quotation.get("lead_id")}, {"_id": 0})
    
    # Recalculate from pricing plan
    pricing_plan = None
    pp_id = data.pricing_plan_id or quotation.get("pricing_plan_id")
    if pp_id:
        pricing_plan = await db.pricing_plans.find_one({"id": pp_id}, {"_id": 0})
    if not pricing_plan:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": data.lead_id or quotation.get("lead_id")}, {"_id": 0})
    
    team_data = (pricing_plan or {}).get("team_deployment") or (pricing_plan or {}).get("consultants") or []
    total_meetings = 0
    calculated_subtotal = 0
    for member in team_data:
        meetings = (member.get("committed_meetings") or member.get("meetings") or 0) * (member.get("count") or 1)
        rate = member.get("rate_per_meeting") or data.base_rate_per_meeting or 12500
        calculated_subtotal += meetings * rate
        total_meetings += meetings
    
    subtotal = data.subtotal if data.subtotal else (calculated_subtotal or quotation.get("subtotal", 0))
    tax_rate = data.tax_rate or quotation.get("tax_rate", 18)
    tax_amount = data.tax_amount if data.tax_amount else round(subtotal * (tax_rate / 100), 2)
    grand_total = subtotal + tax_amount
    
    client_name = data.client_name or (lead or {}).get("company", "") or quotation.get("client_name", "")
    
    update_data = {
        "lead_id": data.lead_id or quotation.get("lead_id"),
        "pricing_plan_id": pp_id,
        "client_name": client_name,
        "client_email": data.client_email or (lead or {}).get("email", "") or quotation.get("client_email", ""),
        "client_gstin": data.client_gstin or (lead or {}).get("gstin", "") or quotation.get("client_gstin", ""),
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "gst_amount": tax_amount,
        "total": grand_total,
        "grand_total": grand_total,
        "total_meetings": total_meetings,
        "validity_days": data.validity_days,
        "payment_terms": data.payment_terms or quotation.get("payment_terms", ""),
        "terms_and_conditions": data.terms_and_conditions or quotation.get("terms_and_conditions", ""),
        "base_rate_per_meeting": data.base_rate_per_meeting,
        "version": (quotation.get("version") or 1) + 1,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_data})
    updated = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    return updated



@router.get("")
async def get_quotations(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search in title, client name"),
    created_from: Optional[str] = Query(None, description="Created date from (YYYY-MM-DD)"),
    created_to: Optional[str] = Query(None, description="Created date to (YYYY-MM-DD)"),
    value_min: Optional[float] = Query(None, description="Minimum quotation value"),
    value_max: Optional[float] = Query(None, description="Maximum quotation value"),
    sort_field: Optional[str] = Query("created_at", description="Sort field"),
    sort_direction: Optional[str] = Query("desc", description="Sort direction (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get quotations with filters, sorting, and pagination.
    
    SALES DATATABLE API - Supports Excel-like filtering.
    """
    db = get_db()
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if status:
        query["status"] = status
    
    # Text search
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"title": search_regex},
            {"client_name": search_regex},
            {"company_name": search_regex}
        ]
    
    # Date range
    if created_from or created_to:
        date_query = {}
        if created_from:
            date_query["$gte"] = datetime.fromisoformat(created_from + "T00:00:00")
        if created_to:
            date_query["$lte"] = datetime.fromisoformat(created_to + "T23:59:59")
        query["created_at"] = date_query
    
    # Value range
    if value_min is not None or value_max is not None:
        value_query = {}
        if value_min is not None:
            value_query["$gte"] = value_min
        if value_max is not None:
            value_query["$lte"] = value_max
        query["total_value"] = value_query
    
    # Sorting
    sort_order = -1 if sort_direction == "desc" else 1
    valid_sort_fields = ["created_at", "total_value", "status", "valid_until"]
    if sort_field not in valid_sort_fields:
        sort_field = "created_at"
    
    # Pagination
    skip = (page - 1) * page_size
    
    # Get total and paginated data
    total = await db.quotations.count_documents(query)
    quotations = await db.quotations.find(query, {"_id": 0}).sort(sort_field, sort_order).skip(skip).limit(page_size).to_list(page_size)
    
    # Enrich quotations with has_sow flag for legacy records
    for quotation in quotations:
        if "has_sow" not in quotation:
            # Check if SOW exists for this quotation's pricing plan
            pricing_plan_id = quotation.get("pricing_plan_id")
            if pricing_plan_id:
                sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0, "id": 1, "scopes": 1})
                if not sow:
                    sow = await db.sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0, "id": 1, "items": 1})
                
                if sow:
                    scope_count = len(sow.get("scopes") or sow.get("items") or [])
                    quotation["has_sow"] = scope_count > 0
                    quotation["sow_id"] = sow.get("id")
                else:
                    quotation["has_sow"] = False
            else:
                quotation["has_sow"] = False
    
    return {
        "data": quotations,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
    }


@router.patch("/{quotation_id}/recalculate")
async def recalculate_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Recalculate quotation financials from linked pricing plan.
    Fixes old quotations that were created before auto-calculation was added."""
    db = get_db()
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Find pricing plan
    pricing_plan_id = quotation.get("pricing_plan_id")
    lead_id = quotation.get("lead_id")
    
    pricing_plan = None
    if pricing_plan_id:
        pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not pricing_plan and lead_id:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    
    if not pricing_plan:
        raise HTTPException(status_code=404, detail="No pricing plan found for recalculation")
    
    team_data = pricing_plan.get("team_deployment") or pricing_plan.get("consultants") or []
    total_meetings = 0
    calculated_subtotal = 0
    
    for member in team_data:
        meetings = (member.get("committed_meetings") or member.get("meetings") or 0) * (member.get("count") or 1)
        rate = member.get("rate_per_meeting") or member.get("default_rate") or 12500
        calculated_subtotal += meetings * rate
        total_meetings += meetings
    
    subtotal = quotation.get("subtotal") or calculated_subtotal or pricing_plan.get("total_amount") or pricing_plan.get("total_investment") or 0
    tax_rate = quotation.get("tax_rate") or 18
    tax_amount = quotation.get("tax_amount") or round(subtotal * (tax_rate / 100), 2)
    grand_total = subtotal + tax_amount
    
    update_data = {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "gst_amount": tax_amount,
        "total": grand_total,
        "grand_total": grand_total,
        "total_meetings": total_meetings,
        "pricing_plan_id": pricing_plan.get("id"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_data})
    
    updated = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    return updated



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
