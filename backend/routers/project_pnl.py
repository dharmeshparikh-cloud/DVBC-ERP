"""
Project P&L Router - Revenue, Costs, and Profitability Tracking
Includes: Invoice Generation from Pricing Plans, Timesheet Costing, Project Expenses
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/project-pnl", tags=["Project P&L"])


# ==================== INVOICE GENERATION FROM PRICING PLAN ====================

@router.post("/generate-invoices/{pricing_plan_id}")
async def generate_invoices_from_pricing_plan(
    pricing_plan_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Generate invoices from pricing plan installments.
    Links invoices to: pricing_plan, project, client, sales_employee
    """
    db = get_db()
    
    if current_user.role not in ["admin", "sales_manager", "account_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/Sales can generate invoices")
    
    # Get pricing plan with payment schedule
    plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    payment_plan = plan.get("payment_plan", {})
    schedule_breakdown = payment_plan.get("schedule_breakdown", [])
    
    if not schedule_breakdown:
        raise HTTPException(status_code=400, detail="No payment schedule found in pricing plan")
    
    # Get linked entities
    lead = await db.leads.find_one({"id": plan.get("lead_id")}, {"_id": 0})
    project = await db.projects.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    agreement = await db.agreements.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    
    # Get sales employee who created this deal
    sales_employee_id = data.get("sales_employee_id")
    sales_employee = None
    if sales_employee_id:
        sales_employee = await db.employees.find_one({"id": sales_employee_id}, {"_id": 0})
    
    # If not provided, try to get from lead owner
    if not sales_employee and lead:
        owner_user = await db.users.find_one({"id": lead.get("owner_id")}, {"_id": 0})
        if owner_user:
            sales_employee = await db.employees.find_one({"user_id": owner_user["id"]}, {"_id": 0})
    
    client_id = lead.get("client_id") if lead else data.get("client_id")
    client_name = lead.get("company") if lead else data.get("client_name", "")
    project_id = project.get("id") if project else data.get("project_id")
    project_name = project.get("name") if project else data.get("project_name", "")
    
    # Generate invoices for each installment
    invoices_created = []
    existing_invoices = await db.invoices.find({"pricing_plan_id": pricing_plan_id}, {"_id": 0}).to_list(100)
    existing_frequencies = {inv.get("installment_frequency") for inv in existing_invoices}
    
    for idx, installment in enumerate(schedule_breakdown):
        frequency = installment.get("frequency", f"Installment {idx + 1}")
        
        # Skip if invoice already exists for this installment
        if frequency in existing_frequencies:
            continue
        
        invoice_number = f"INV-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
        
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "invoice_type": "project_installment",
            
            # Pricing Plan Linkage
            "pricing_plan_id": pricing_plan_id,
            "installment_index": idx,
            "installment_frequency": frequency,
            
            # Project Linkage
            "project_id": project_id,
            "project_name": project_name,
            
            # Client Linkage
            "client_id": client_id,
            "client_name": client_name,
            
            # Sales Employee Linkage (for incentive calculation)
            "sales_employee_id": sales_employee.get("id") if sales_employee else None,
            "sales_employee_code": sales_employee.get("employee_id") if sales_employee else None,
            "sales_employee_name": f"{sales_employee.get('first_name', '')} {sales_employee.get('last_name', '')}".strip() if sales_employee else None,
            
            # Agreement Linkage
            "agreement_id": agreement.get("id") if agreement else None,
            
            # Amount Details
            "basic_amount": installment.get("basic", 0),
            "gst_amount": installment.get("gst", 0),
            "tds_amount": installment.get("tds", 0),
            "conveyance_amount": installment.get("conveyance", 0),
            "net_amount": installment.get("net", 0),
            "total_amount": installment.get("basic", 0) + installment.get("gst", 0),
            
            # Dates
            "due_date": installment.get("due_date"),
            "invoice_date": datetime.now(timezone.utc).isoformat(),
            
            # Status
            "status": "pending",  # pending, sent, paid, overdue, cancelled
            "payment_status": "unpaid",  # unpaid, partial, paid
            "amount_paid": 0,
            "amount_due": installment.get("net", 0),
            
            # Tracking
            "created_by": current_user.id,
            "created_by_name": current_user.full_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.invoices.insert_one(invoice)
        invoices_created.append(invoice)
    
    # Update pricing plan to mark invoices generated
    await db.pricing_plans.update_one(
        {"id": pricing_plan_id},
        {"$set": {
            "invoices_generated": True,
            "invoices_generated_at": datetime.now(timezone.utc).isoformat(),
            "invoices_generated_by": current_user.id
        }}
    )
    
    return {
        "message": f"Generated {len(invoices_created)} invoices",
        "invoices_created": len(invoices_created),
        "invoices": invoices_created
    }


@router.post("/invoices/{invoice_id}/record-payment")
async def record_invoice_payment(
    invoice_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Record payment against an invoice.
    Updates invoice status and tracks for sales incentive eligibility.
    """
    db = get_db()
    
    if current_user.role not in ["admin", "sales_manager", "account_manager", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to record payments")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment_amount = data.get("amount", 0)
    payment_date = data.get("payment_date", datetime.now(timezone.utc).isoformat())
    payment_method = data.get("payment_method", "bank_transfer")
    payment_reference = data.get("reference", "")
    
    if payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")
    
    # Calculate new totals
    new_amount_paid = invoice.get("amount_paid", 0) + payment_amount
    new_amount_due = invoice.get("net_amount", 0) - new_amount_paid
    
    # Determine payment status
    if new_amount_due <= 0:
        payment_status = "paid"
        status = "paid"
    elif new_amount_paid > 0:
        payment_status = "partial"
        status = "sent"
    else:
        payment_status = "unpaid"
        status = invoice.get("status", "pending")
    
    # Create payment record
    payment_record = {
        "id": str(uuid.uuid4()),
        "invoice_id": invoice_id,
        "amount": payment_amount,
        "payment_date": payment_date,
        "payment_method": payment_method,
        "reference": payment_reference,
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update invoice
    await db.invoices.update_one(
        {"id": invoice_id},
        {
            "$set": {
                "amount_paid": new_amount_paid,
                "amount_due": max(0, new_amount_due),
                "payment_status": payment_status,
                "status": status,
                "last_payment_date": payment_date,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {"payments": payment_record}
        }
    )
    
    # If fully paid, update project revenue and check incentive eligibility
    if payment_status == "paid":
        # Update project total revenue
        if invoice.get("project_id"):
            await db.projects.update_one(
                {"id": invoice["project_id"]},
                {"$inc": {"total_revenue_collected": payment_amount}}
            )
        
        # Create incentive eligibility record for sales employee
        if invoice.get("sales_employee_id"):
            incentive_record = {
                "id": str(uuid.uuid4()),
                "type": "invoice_cleared",
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "employee_id": invoice["sales_employee_id"],
                "employee_code": invoice.get("sales_employee_code"),
                "employee_name": invoice.get("sales_employee_name"),
                "project_id": invoice.get("project_id"),
                "project_name": invoice.get("project_name"),
                "client_name": invoice.get("client_name"),
                "amount": invoice.get("net_amount", 0),
                "cleared_date": payment_date,
                "status": "pending_review",  # HR will review and approve incentive
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.incentive_eligibility.insert_one(incentive_record)
    
    return {
        "message": "Payment recorded",
        "invoice_id": invoice_id,
        "amount_paid": new_amount_paid,
        "amount_due": max(0, new_amount_due),
        "payment_status": payment_status,
        "incentive_eligible": payment_status == "paid" and invoice.get("sales_employee_id") is not None
    }


# ==================== PROJECT COST TRACKING ====================

@router.get("/project/{project_id}/costs")
async def get_project_costs(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all costs for a project:
    - Consultant costs (from timesheets)
    - Direct expenses (from expenses collection)
    """
    db = get_db()
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get consultant assignments for this project
    assignments = await db.consultant_assignments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get timesheets for this project
    timesheets = await db.timesheets.find(
        {"entries.project_id": project_id},
        {"_id": 0}
    ).to_list(500)
    
    # Calculate consultant costs from timesheets
    consultant_costs = []
    total_hours = 0
    total_consultant_cost = 0
    
    for ts in timesheets:
        user = await db.users.find_one({"id": ts.get("user_id")}, {"_id": 0, "id": 1, "full_name": 1})
        employee = await db.employees.find_one({"user_id": ts.get("user_id")}, {"_id": 0})
        
        if not employee:
            continue
        
        # Calculate hourly cost from salary
        monthly_salary = employee.get("salary", 0)
        hourly_cost = round(monthly_salary / 176, 2) if monthly_salary > 0 else 0  # 176 = 22 days * 8 hrs
        
        # Sum hours for this project from entries
        project_hours = 0
        for entry in ts.get("entries", []):
            if entry.get("project_id") == project_id:
                project_hours += entry.get("hours", 0)
        
        if project_hours > 0:
            cost = round(project_hours * hourly_cost, 2)
            consultant_costs.append({
                "employee_id": employee.get("id"),
                "employee_code": employee.get("employee_id"),
                "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
                "hours": project_hours,
                "hourly_cost": hourly_cost,
                "total_cost": cost
            })
            total_hours += project_hours
            total_consultant_cost += cost
    
    # Get project expenses
    expenses = await db.expenses.find(
        {"project_id": project_id, "status": {"$in": ["approved", "reimbursed"]}},
        {"_id": 0}
    ).to_list(200)
    
    total_expense_cost = sum(e.get("total_amount", 0) or e.get("amount", 0) for e in expenses)
    
    return {
        "project_id": project_id,
        "project_name": project.get("name"),
        "consultant_costs": {
            "total_hours": total_hours,
            "total_cost": total_consultant_cost,
            "breakdown": consultant_costs
        },
        "expense_costs": {
            "total_cost": total_expense_cost,
            "count": len(expenses),
            "expenses": expenses[:20]  # First 20 for display
        },
        "total_project_cost": round(total_consultant_cost + total_expense_cost, 2)
    }


# ==================== PROJECT P&L DASHBOARD ====================

@router.get("/project/{project_id}/pnl")
async def get_project_pnl(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Complete Project P&L with Revenue, Costs, and Profitability
    """
    db = get_db()
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get pricing plan for revenue
    pricing_plan = None
    if project.get("pricing_plan_id"):
        pricing_plan = await db.pricing_plans.find_one(
            {"id": project["pricing_plan_id"]},
            {"_id": 0}
        )
    
    # Get all invoices for this project
    invoices = await db.invoices.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(100)
    
    # Revenue calculations
    total_contract_value = pricing_plan.get("total_amount", 0) if pricing_plan else 0
    total_invoiced = sum(inv.get("net_amount", 0) for inv in invoices)
    total_collected = sum(inv.get("amount_paid", 0) for inv in invoices)
    total_pending = sum(inv.get("amount_due", 0) for inv in invoices if inv.get("payment_status") != "paid")
    
    # Get costs
    costs = await get_project_costs(project_id, current_user)
    total_cost = costs["total_project_cost"]
    consultant_cost = costs["consultant_costs"]["total_cost"]
    expense_cost = costs["expense_costs"]["total_cost"]
    
    # P&L calculations
    gross_profit = total_collected - total_cost
    gross_margin = round((gross_profit / total_collected * 100), 2) if total_collected > 0 else 0
    
    projected_profit = total_contract_value - total_cost
    projected_margin = round((projected_profit / total_contract_value * 100), 2) if total_contract_value > 0 else 0
    
    return {
        "project": {
            "id": project_id,
            "name": project.get("name"),
            "client_name": project.get("client_name"),
            "status": project.get("status")
        },
        "revenue": {
            "contract_value": total_contract_value,
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "pending_collection": total_pending,
            "invoices_count": len(invoices),
            "invoices_paid": len([i for i in invoices if i.get("payment_status") == "paid"])
        },
        "costs": {
            "total_cost": total_cost,
            "consultant_cost": consultant_cost,
            "expense_cost": expense_cost,
            "consultant_hours": costs["consultant_costs"]["total_hours"]
        },
        "profitability": {
            "gross_profit": round(gross_profit, 2),
            "gross_margin_percent": gross_margin,
            "projected_profit": round(projected_profit, 2),
            "projected_margin_percent": projected_margin
        },
        "summary": {
            "status": "profitable" if gross_profit > 0 else "loss",
            "health": "good" if gross_margin > 20 else "warning" if gross_margin > 0 else "critical"
        }
    }


@router.get("/dashboard")
async def get_pnl_dashboard(
    current_user: User = Depends(get_current_user)
):
    """
    Overall P&L Dashboard across all projects
    """
    db = get_db()
    
    if current_user.role not in ["admin", "sales_manager", "principal_consultant", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to view P&L dashboard")
    
    # Get all active projects
    projects = await db.projects.find(
        {"status": {"$in": ["active", "in_progress", "completed"]}},
        {"_id": 0}
    ).to_list(200)
    
    # Get all invoices
    all_invoices = await db.invoices.find({}, {"_id": 0}).to_list(1000)
    
    # Calculate totals
    total_contract_value = 0
    total_invoiced = sum(inv.get("net_amount", 0) for inv in all_invoices)
    total_collected = sum(inv.get("amount_paid", 0) for inv in all_invoices)
    total_pending = sum(inv.get("amount_due", 0) for inv in all_invoices if inv.get("payment_status") != "paid")
    
    # Get pricing plans for contract values
    for proj in projects:
        if proj.get("pricing_plan_id"):
            plan = await db.pricing_plans.find_one({"id": proj["pricing_plan_id"]}, {"_id": 0, "total_amount": 1})
            if plan:
                total_contract_value += plan.get("total_amount", 0)
    
    # Invoice status breakdown
    invoice_stats = {
        "total": len(all_invoices),
        "paid": len([i for i in all_invoices if i.get("payment_status") == "paid"]),
        "partial": len([i for i in all_invoices if i.get("payment_status") == "partial"]),
        "unpaid": len([i for i in all_invoices if i.get("payment_status") == "unpaid"]),
        "overdue": len([i for i in all_invoices if i.get("status") == "overdue"])
    }
    
    # Monthly revenue trend (last 6 months)
    from datetime import timedelta
    monthly_revenue = []
    for i in range(6):
        month_start = datetime.now(timezone.utc).replace(day=1) - timedelta(days=30*i)
        month_str = month_start.strftime("%Y-%m")
        month_collected = sum(
            inv.get("amount_paid", 0) for inv in all_invoices
            if inv.get("last_payment_date", "").startswith(month_str)
        )
        monthly_revenue.append({
            "month": month_str,
            "collected": month_collected
        })
    
    return {
        "summary": {
            "total_projects": len(projects),
            "total_contract_value": total_contract_value,
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_pending": total_pending,
            "collection_rate": round((total_collected / total_invoiced * 100), 2) if total_invoiced > 0 else 0
        },
        "invoice_stats": invoice_stats,
        "monthly_revenue": list(reversed(monthly_revenue)),
        "projects": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "client_name": p.get("client_name"),
                "status": p.get("status")
            } for p in projects[:20]
        ]
    }


# ==================== INVOICES LIST ====================

@router.get("/invoices")
async def get_all_invoices(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    client_id: Optional[str] = None,
    sales_employee_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all invoices with filters"""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    if project_id:
        query["project_id"] = project_id
    if client_id:
        query["client_id"] = client_id
    if sales_employee_id:
        query["sales_employee_id"] = sales_employee_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return {
        "invoices": invoices,
        "total": len(invoices),
        "total_amount": sum(inv.get("net_amount", 0) for inv in invoices),
        "total_collected": sum(inv.get("amount_paid", 0) for inv in invoices)
    }
