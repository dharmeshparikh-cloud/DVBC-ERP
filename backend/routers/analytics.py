"""
Analytics Router - Sales funnel analytics, bottleneck analysis, forecasting, velocity metrics
Extracted from server.py for better modularity and load performance.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from routers.deps import get_db, oauth2_scheme, SECRET_KEY, ALGORITHM
from routers.models import User
from jose import JWTError, jwt

router = APIRouter(tags=["Analytics"])


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = get_db()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return User(**user)


@router.get("/analytics/funnel-summary")
async def get_funnel_summary(
    period: str = "month",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get funnel stage summary with employee-wise breakdown.
    For managers: sees all subordinates
    For employees: sees only their own data
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Calculate date range based on period
    if start_date and end_date:
        date_start = start_date
        date_end = end_date
    elif period == "week":
        date_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        date_end = now.strftime("%Y-%m-%d")
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        date_start = datetime(now.year, quarter_month, 1).strftime("%Y-%m-%d")
        date_end = now.strftime("%Y-%m-%d")
    elif period == "year":
        date_start = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
        date_end = now.strftime("%Y-%m-%d")
    else:  # month
        date_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
        date_end = now.strftime("%Y-%m-%d")
    
    # Determine access level
    is_manager = current_user.role in ["admin", "manager", "sr_manager", "principal_consultant", "sales_manager"]
    
    # Get employee info
    user_employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    # Build employee filter
    employee_ids = []
    employee_map = {}
    
    if is_manager and not employee_id:
        if current_user.role == "admin":
            subordinates = await db.employees.find(
                {"is_active": True},
                {"_id": 0, "user_id": 1, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1}
            ).to_list(500)
        elif user_employee:
            manager_id = user_employee.get("employee_id") or user_employee.get("id")
            subordinates = await db.employees.find(
                {"$or": [
                    {"reporting_manager_id": manager_id}, 
                    {"reporting_manager_id": user_employee.get("id")}
                ], "is_active": True},
                {"_id": 0, "user_id": 1, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1}
            ).to_list(100)
        else:
            subordinates = []
        
        for sub in subordinates:
            emp_id = sub.get("user_id") or sub.get("id")
            employee_ids.append(emp_id)
            employee_map[emp_id] = f"{sub.get('first_name', '')} {sub.get('last_name', '')}".strip()
    elif employee_id:
        employee_ids = [employee_id]
        emp = await db.employees.find_one({"$or": [{"user_id": employee_id}, {"id": employee_id}]}, {"_id": 0})
        if emp:
            employee_map[employee_id] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
    else:
        if user_employee:
            emp_id = user_employee.get("user_id") or user_employee.get("id")
            employee_ids = [emp_id, current_user.id]
            employee_map[emp_id] = f"{user_employee.get('first_name', '')} {user_employee.get('last_name', '')}".strip()
        else:
            employee_ids = [current_user.id]
            employee_map[current_user.id] = current_user.full_name
    
    # Define funnel stages
    funnel_stages = [
        {"id": "lead", "name": "Lead Capture", "order": 1},
        {"id": "meeting", "name": "Meeting", "order": 2},
        {"id": "pricing", "name": "Pricing Plan", "order": 3},
        {"id": "sow", "name": "SOW", "order": 4},
        {"id": "quotation", "name": "Quotation", "order": 5},
        {"id": "agreement", "name": "Agreement", "order": 6},
        {"id": "payment", "name": "Payment", "order": 7},
        {"id": "kickoff", "name": "Kickoff", "order": 8},
        {"id": "complete", "name": "Project Created", "order": 9}
    ]
    
    # Get all leads for the employees in date range
    lead_query = {"created_at": {"$gte": date_start, "$lte": date_end + "T23:59:59"}}
    if employee_ids:
        lead_query["$or"] = [
            {"created_by": {"$in": employee_ids}},
            {"assigned_to": {"$in": employee_ids}}
        ]
    
    leads = await db.leads.find(lead_query, {"_id": 0, "id": 1, "created_by": 1, "assigned_to": 1, "status": 1}).to_list(1000)
    lead_ids = [l["id"] for l in leads]
    
    # Get progress for all leads
    stage_counts = {stage["id"]: 0 for stage in funnel_stages}
    employee_stage_counts = {emp_id: {stage["id"]: 0 for stage in funnel_stages} for emp_id in employee_ids}
    
    # Count leads at each stage
    for lead in leads:
        lead_id = lead["id"]
        emp_id = lead.get("assigned_to") or lead.get("created_by")
        
        # Determine current stage
        current_stage = "lead"
        
        meeting = await db.meeting_records.find_one({"lead_id": lead_id})
        if meeting:
            current_stage = "meeting"
        
        pricing = await db.pricing_plans.find_one({"lead_id": lead_id})
        if pricing:
            current_stage = "pricing"
            
            sow = await db.enhanced_sow.find_one({"$or": [
                {"pricing_plan_id": pricing.get("id")},
                {"lead_id": lead_id}
            ]})
            if sow:
                current_stage = "sow"
        
        quotation = await db.quotations.find_one({"lead_id": lead_id})
        if quotation:
            current_stage = "quotation"
        
        agreement = await db.agreements.find_one({"lead_id": lead_id})
        if agreement:
            if agreement.get("status") == "signed":
                current_stage = "agreement"
            else:
                current_stage = "quotation"
        
        if agreement:
            payment = await db.agreement_payments.find_one({"agreement_id": agreement.get("id")})
            if payment:
                current_stage = "payment"
        
        kickoff = await db.kickoff_requests.find_one({"lead_id": lead_id})
        if kickoff:
            if kickoff.get("status") == "accepted":
                current_stage = "complete"
            else:
                current_stage = "kickoff"
        
        stage_counts[current_stage] += 1
        if emp_id in employee_stage_counts:
            employee_stage_counts[emp_id][current_stage] += 1
    
    # Build employee breakdown
    employee_breakdown = []
    for emp_id, stages in employee_stage_counts.items():
        total = sum(stages.values())
        employee_breakdown.append({
            "employee_id": emp_id,
            "employee_name": employee_map.get(emp_id, "Unknown"),
            "stages": stages,
            "total_leads": total,
            "conversion_rate": round((stages.get("complete", 0) / total * 100) if total > 0 else 0, 1)
        })
    
    employee_breakdown.sort(key=lambda x: x["total_leads"], reverse=True)
    
    total_leads = sum(stage_counts.values())
    completed = stage_counts.get("complete", 0)
    
    return {
        "period": period,
        "date_range": {"start": date_start, "end": date_end},
        "summary": {
            "total_leads": total_leads,
            "completed": completed,
            "conversion_rate": round((completed / total_leads * 100) if total_leads > 0 else 0, 1),
            "in_progress": total_leads - completed
        },
        "stage_counts": stage_counts,
        "funnel_stages": funnel_stages,
        "employee_breakdown": employee_breakdown if is_manager else [],
        "is_manager_view": is_manager
    }


@router.get("/analytics/my-funnel-summary")
async def get_my_funnel_summary(
    period: str = "month",
    current_user: User = Depends(get_current_user)
):
    """Get employee's own funnel summary with target vs achievement"""
    db = get_db()
    now = datetime.now(timezone.utc)
    
    user_employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    emp_id = user_employee.get("employee_id") or user_employee.get("id") if user_employee else current_user.id
    user_id = user_employee.get("user_id") or current_user.id if user_employee else current_user.id
    
    if period == "week":
        date_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        date_start = datetime(now.year, quarter_month, 1).strftime("%Y-%m-%d")
    elif period == "year":
        date_start = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
    else:  # month
        date_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
    
    date_end = now.strftime("%Y-%m-%d")
    
    my_leads = await db.leads.find({
        "$or": [
            {"created_by": {"$in": [user_id, emp_id, current_user.id]}},
            {"assigned_to": {"$in": [user_id, emp_id, current_user.id]}}
        ],
        "created_at": {"$gte": date_start}
    }, {"_id": 0, "id": 1, "status": 1}).to_list(500)
    
    lead_ids = [l["id"] for l in my_leads]
    
    stage_counts = {
        "lead": 0, "meeting": 0, "pricing": 0, "sow": 0,
        "quotation": 0, "agreement": 0, "payment": 0, "kickoff": 0, "complete": 0
    }
    
    for lead in my_leads:
        lead_id = lead["id"]
        stage = "lead"
        
        if await db.meeting_records.find_one({"lead_id": lead_id}):
            stage = "meeting"
        if await db.pricing_plans.find_one({"lead_id": lead_id}):
            stage = "pricing"
        if await db.enhanced_sow.find_one({"lead_id": lead_id}):
            stage = "sow"
        if await db.quotations.find_one({"lead_id": lead_id}):
            stage = "quotation"
        agreement = await db.agreements.find_one({"lead_id": lead_id})
        if agreement and agreement.get("status") == "signed":
            stage = "agreement"
        if agreement:
            if await db.agreement_payments.find_one({"agreement_id": agreement.get("id")}):
                stage = "payment"
        kickoff = await db.kickoff_requests.find_one({"lead_id": lead_id})
        if kickoff:
            stage = "kickoff" if kickoff.get("status") != "accepted" else "complete"
        
        stage_counts[stage] += 1
    
    # Get targets
    targets = await db.yearly_sales_targets.find({
        "employee_id": emp_id,
        "year": now.year
    }, {"_id": 0}).to_list(10)
    
    meeting_target = 0
    closure_target = 0
    revenue_target = 0
    
    for t in targets:
        monthly = t.get("monthly_targets", {}).get(str(now.month), 0)
        if t.get("target_type") == "meetings":
            meeting_target = monthly
        elif t.get("target_type") == "closures":
            closure_target = monthly
        elif t.get("target_type") == "revenue":
            revenue_target = monthly
    
    month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
    meetings_achieved = await db.meeting_records.count_documents({
        "created_by": {"$in": [user_id, emp_id, current_user.id]},
        "meeting_date": {"$gte": month_start}
    })
    
    closures_achieved = stage_counts.get("complete", 0)
    
    revenue_achieved = 0
    completed_agreements = await db.agreements.find({
        "lead_id": {"$in": lead_ids},
        "status": "signed"
    }, {"_id": 0, "total_value": 1}).to_list(100)
    for agr in completed_agreements:
        revenue_achieved += agr.get("total_value", 0)
    
    return {
        "period": period,
        "date_range": {"start": date_start, "end": date_end},
        "total_leads": len(my_leads),
        "stage_counts": stage_counts,
        "targets": {
            "meetings": {
                "target": meeting_target,
                "achieved": meetings_achieved,
                "percentage": round((meetings_achieved / meeting_target * 100) if meeting_target > 0 else 0, 1)
            },
            "closures": {
                "target": closure_target,
                "achieved": closures_achieved,
                "percentage": round((closures_achieved / closure_target * 100) if closure_target > 0 else 0, 1)
            },
            "revenue": {
                "target": revenue_target,
                "achieved": revenue_achieved,
                "percentage": round((revenue_achieved / revenue_target * 100) if revenue_target > 0 else 0, 1)
            }
        },
        "conversion_rate": round((closures_achieved / len(my_leads) * 100) if len(my_leads) > 0 else 0, 1)
    }


@router.get("/analytics/funnel-trends")
async def get_funnel_trends(
    period: str = "month",
    current_user: User = Depends(get_current_user)
):
    """Get month-over-month funnel trends for manager view"""
    db = get_db()
    is_manager = current_user.role in ["admin", "manager", "sr_manager", "principal_consultant", "sales_manager"]
    
    if not is_manager:
        raise HTTPException(status_code=403, detail="Only managers can view trends")
    
    now = datetime.now(timezone.utc)
    trends = []
    
    for i in range(6):
        if period == "month":
            target_date = now - timedelta(days=30 * i)
            month_start = datetime(target_date.year, target_date.month, 1)
            if target_date.month == 12:
                month_end = datetime(target_date.year + 1, 1, 1)
            else:
                month_end = datetime(target_date.year, target_date.month + 1, 1)
            label = month_start.strftime("%b %Y")
        elif period == "week":
            target_date = now - timedelta(weeks=i)
            week_start = target_date - timedelta(days=target_date.weekday())
            week_end = week_start + timedelta(days=7)
            month_start = week_start
            month_end = week_end
            label = f"Week {week_start.strftime('%d %b')}"
        else:
            continue
        
        leads_created = await db.leads.count_documents({
            "created_at": {"$gte": month_start.isoformat(), "$lt": month_end.isoformat()}
        })
        
        completed = await db.kickoff_requests.count_documents({
            "status": "accepted",
            "updated_at": {"$gte": month_start.isoformat(), "$lt": month_end.isoformat()}
        })
        
        meetings = await db.meeting_records.count_documents({
            "meeting_date": {"$gte": month_start.strftime("%Y-%m-%d"), "$lt": month_end.strftime("%Y-%m-%d")}
        })
        
        trends.append({
            "period": label,
            "leads_created": leads_created,
            "completed": completed,
            "meetings": meetings,
            "conversion_rate": round((completed / leads_created * 100) if leads_created > 0 else 0, 1)
        })
    
    trends.reverse()
    
    return {
        "period_type": period,
        "trends": trends
    }


@router.get("/analytics/bottleneck-analysis")
async def get_bottleneck_analysis(
    current_user: User = Depends(get_current_user)
):
    """
    Analyze funnel bottlenecks - where leads are dropping off.
    Shows conversion rates between each stage and identifies problem areas.
    """
    db = get_db()
    
    all_leads = await db.leads.find(
        {"status": {"$nin": ["lost"]}},
        {"_id": 0, "id": 1, "created_at": 1}
    ).to_list(1000)
    
    lead_ids = [l["id"] for l in all_leads]
    total_leads = len(all_leads)
    
    if total_leads == 0:
        return {"message": "No leads to analyze", "stages": []}
    
    stage_data = []
    
    # Stage 1: Lead
    stage_data.append({
        "stage": "lead",
        "name": "Lead Capture",
        "count": total_leads,
        "percentage": 100.0
    })
    
    # Stage 2: Meeting
    meeting_leads = set()
    meetings = await db.meeting_records.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1}
    ).to_list(1000)
    for m in meetings:
        meeting_leads.add(m.get("lead_id"))
    meeting_count = len(meeting_leads)
    stage_data.append({
        "stage": "meeting",
        "name": "Meeting Recorded",
        "count": meeting_count,
        "percentage": round((meeting_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 3: Pricing Plan
    pricing_leads = set()
    pricing = await db.pricing_plans.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1, "id": 1}
    ).to_list(1000)
    pricing_map = {}
    for p in pricing:
        pricing_leads.add(p.get("lead_id"))
        pricing_map[p.get("lead_id")] = p.get("id")
    pricing_count = len(pricing_leads)
    stage_data.append({
        "stage": "pricing",
        "name": "Pricing Plan",
        "count": pricing_count,
        "percentage": round((pricing_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 4: SOW
    sow_leads = set()
    sow = await db.enhanced_sow.find(
        {"$or": [
            {"lead_id": {"$in": lead_ids}},
            {"pricing_plan_id": {"$in": list(pricing_map.values())}}
        ]},
        {"_id": 0, "lead_id": 1}
    ).to_list(1000)
    for s in sow:
        if s.get("lead_id"):
            sow_leads.add(s.get("lead_id"))
    sow_count = len(sow_leads)
    stage_data.append({
        "stage": "sow",
        "name": "Scope of Work",
        "count": sow_count,
        "percentage": round((sow_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 5: Quotation
    quotation_leads = set()
    quotations = await db.quotations.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1}
    ).to_list(1000)
    for q in quotations:
        quotation_leads.add(q.get("lead_id"))
    quotation_count = len(quotation_leads)
    stage_data.append({
        "stage": "quotation",
        "name": "Quotation Sent",
        "count": quotation_count,
        "percentage": round((quotation_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 6: Agreement Created
    agreement_leads = set()
    agreement_map = {}
    agreements = await db.agreements.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1, "id": 1, "status": 1}
    ).to_list(1000)
    for a in agreements:
        agreement_leads.add(a.get("lead_id"))
        agreement_map[a.get("lead_id")] = {"id": a.get("id"), "status": a.get("status")}
    agreement_count = len(agreement_leads)
    stage_data.append({
        "stage": "agreement",
        "name": "Agreement Created",
        "count": agreement_count,
        "percentage": round((agreement_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 7: Agreement Signed
    signed_leads = set()
    for lead_id, agr in agreement_map.items():
        if agr.get("status") == "signed":
            signed_leads.add(lead_id)
    signed_count = len(signed_leads)
    stage_data.append({
        "stage": "signed",
        "name": "Agreement Signed",
        "count": signed_count,
        "percentage": round((signed_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 8: Payment Received
    payment_leads = set()
    agreement_ids = [v["id"] for v in agreement_map.values()]
    payments = await db.agreement_payments.find(
        {"agreement_id": {"$in": agreement_ids}},
        {"_id": 0, "agreement_id": 1}
    ).to_list(1000)
    paid_agreement_ids = set(p.get("agreement_id") for p in payments)
    for lead_id, agr in agreement_map.items():
        if agr.get("id") in paid_agreement_ids:
            payment_leads.add(lead_id)
    payment_count = len(payment_leads)
    stage_data.append({
        "stage": "payment",
        "name": "Payment Received",
        "count": payment_count,
        "percentage": round((payment_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 9: Kickoff Requested
    kickoff_leads = set()
    kickoff_accepted_leads = set()
    kickoffs = await db.kickoff_requests.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1, "status": 1}
    ).to_list(1000)
    for k in kickoffs:
        kickoff_leads.add(k.get("lead_id"))
        if k.get("status") == "accepted":
            kickoff_accepted_leads.add(k.get("lead_id"))
    kickoff_count = len(kickoff_leads)
    stage_data.append({
        "stage": "kickoff",
        "name": "Kickoff Requested",
        "count": kickoff_count,
        "percentage": round((kickoff_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Stage 10: Project Created
    complete_count = len(kickoff_accepted_leads)
    stage_data.append({
        "stage": "complete",
        "name": "Project Created",
        "count": complete_count,
        "percentage": round((complete_count / total_leads) * 100, 1) if total_leads > 0 else 0
    })
    
    # Calculate drop-off rates
    bottlenecks = []
    for i in range(1, len(stage_data)):
        prev = stage_data[i - 1]
        curr = stage_data[i]
        
        if prev["count"] > 0:
            conversion_rate = round((curr["count"] / prev["count"]) * 100, 1)
            drop_off_rate = round(100 - conversion_rate, 1)
            drop_off_count = prev["count"] - curr["count"]
        else:
            conversion_rate = 0
            drop_off_rate = 0
            drop_off_count = 0
        
        bottlenecks.append({
            "from_stage": prev["stage"],
            "from_name": prev["name"],
            "to_stage": curr["stage"],
            "to_name": curr["name"],
            "conversion_rate": conversion_rate,
            "drop_off_rate": drop_off_rate,
            "drop_off_count": drop_off_count,
            "is_bottleneck": drop_off_rate > 50 and drop_off_count > 2
        })
    
    worst_bottleneck = max(bottlenecks, key=lambda x: x["drop_off_rate"]) if bottlenecks else None
    
    return {
        "total_leads": total_leads,
        "completed": complete_count,
        "overall_conversion": round((complete_count / total_leads) * 100, 1) if total_leads > 0 else 0,
        "stages": stage_data,
        "bottlenecks": bottlenecks,
        "worst_bottleneck": worst_bottleneck,
        "insights": [
            f"Your worst bottleneck is at '{worst_bottleneck['from_name']} → {worst_bottleneck['to_name']}' with {worst_bottleneck['drop_off_rate']}% drop-off" if worst_bottleneck and worst_bottleneck['drop_off_rate'] > 30 else None,
            f"Overall funnel conversion: {round((complete_count / total_leads) * 100, 1)}%" if total_leads > 0 else None,
            f"{complete_count} out of {total_leads} leads converted to projects" if total_leads > 0 else None
        ]
    }


@router.get("/analytics/forecasting")
async def get_sales_forecasting(
    current_user: User = Depends(get_current_user)
):
    """
    Predict future closures based on current funnel and historical conversion rates.
    Uses weighted probability based on stage position.
    """
    db = get_db()
    
    stage_probabilities = {
        "lead": 0.05, "meeting": 0.15, "pricing": 0.25, "sow": 0.35,
        "quotation": 0.50, "agreement": 0.65, "signed": 0.85,
        "payment": 0.95, "kickoff": 0.98, "complete": 1.0
    }
    
    agreements = await db.agreements.find(
        {"total_value": {"$exists": True, "$gt": 0}},
        {"_id": 0, "total_value": 1}
    ).to_list(100)
    
    if agreements:
        avg_deal_value = sum(a.get("total_value", 0) for a in agreements) / len(agreements)
    else:
        avg_deal_value = 300000
    
    all_leads = await db.leads.find(
        {"status": {"$nin": ["lost", "closed"]}},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    
    lead_ids = [l["id"] for l in all_leads]
    total_leads = len(all_leads)
    
    stage_counts = {
        "lead": 0, "meeting": 0, "pricing": 0, "sow": 0,
        "quotation": 0, "agreement": 0, "signed": 0,
        "payment": 0, "kickoff": 0, "complete": 0
    }
    
    # Build lookup sets
    meeting_leads = set()
    meetings = await db.meeting_records.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1}).to_list(1000)
    for m in meetings:
        meeting_leads.add(m.get("lead_id"))
    
    pricing_leads = set()
    pricing_map = {}
    pricing = await db.pricing_plans.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "id": 1}).to_list(1000)
    for p in pricing:
        pricing_leads.add(p.get("lead_id"))
        pricing_map[p.get("lead_id")] = p.get("id")
    
    sow_leads = set()
    sow = await db.enhanced_sow.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1}).to_list(1000)
    for s in sow:
        if s.get("lead_id"):
            sow_leads.add(s.get("lead_id"))
    
    quotation_leads = set()
    quotations = await db.quotations.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1}).to_list(1000)
    for q in quotations:
        quotation_leads.add(q.get("lead_id"))
    
    agreement_map = {}
    agreements_db = await db.agreements.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0, "lead_id": 1, "id": 1, "status": 1, "total_value": 1}
    ).to_list(1000)
    for a in agreements_db:
        agreement_map[a.get("lead_id")] = a
    
    agreement_ids = [a.get("id") for a in agreements_db]
    paid_agreements = set()
    payments = await db.agreement_payments.find({"agreement_id": {"$in": agreement_ids}}, {"_id": 0, "agreement_id": 1}).to_list(1000)
    for p in payments:
        paid_agreements.add(p.get("agreement_id"))
    
    kickoff_map = {}
    kickoffs = await db.kickoff_requests.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "status": 1}).to_list(1000)
    for k in kickoffs:
        kickoff_map[k.get("lead_id")] = k.get("status")
    
    for lead_id in lead_ids:
        if lead_id in kickoff_map and kickoff_map[lead_id] == "accepted":
            stage_counts["complete"] += 1
        elif lead_id in kickoff_map:
            stage_counts["kickoff"] += 1
        elif lead_id in agreement_map and agreement_map[lead_id].get("id") in paid_agreements:
            stage_counts["payment"] += 1
        elif lead_id in agreement_map and agreement_map[lead_id].get("status") == "signed":
            stage_counts["signed"] += 1
        elif lead_id in agreement_map:
            stage_counts["agreement"] += 1
        elif lead_id in quotation_leads:
            stage_counts["quotation"] += 1
        elif lead_id in sow_leads:
            stage_counts["sow"] += 1
        elif lead_id in pricing_leads:
            stage_counts["pricing"] += 1
        elif lead_id in meeting_leads:
            stage_counts["meeting"] += 1
        else:
            stage_counts["lead"] += 1
    
    pipeline_forecast = []
    total_weighted_deals = 0
    total_weighted_value = 0
    
    for stage, count in stage_counts.items():
        if stage == "complete":
            continue
        
        probability = stage_probabilities.get(stage, 0)
        stage_value = avg_deal_value
        weighted_deals = count * probability
        weighted_value = count * stage_value * probability
        
        total_weighted_deals += weighted_deals
        total_weighted_value += weighted_value
        
        pipeline_forecast.append({
            "stage": stage,
            "count": count,
            "probability": round(probability * 100, 0),
            "weighted_deals": round(weighted_deals, 1),
            "weighted_value": round(weighted_value, 0)
        })
    
    forecast_30_days = {
        "deals": round(stage_counts.get("kickoff", 0) * 0.98 + 
                      stage_counts.get("payment", 0) * 0.70 + 
                      stage_counts.get("signed", 0) * 0.40, 1),
        "value": round((stage_counts.get("kickoff", 0) * 0.98 + 
                       stage_counts.get("payment", 0) * 0.70 + 
                       stage_counts.get("signed", 0) * 0.40) * avg_deal_value, 0)
    }
    
    forecast_60_days = {
        "deals": round(forecast_30_days["deals"] + 
                      stage_counts.get("agreement", 0) * 0.50 + 
                      stage_counts.get("quotation", 0) * 0.30, 1),
        "value": round((forecast_30_days["deals"] + 
                       stage_counts.get("agreement", 0) * 0.50 + 
                       stage_counts.get("quotation", 0) * 0.30) * avg_deal_value, 0)
    }
    
    forecast_90_days = {
        "deals": round(forecast_60_days["deals"] + 
                      stage_counts.get("sow", 0) * 0.25 + 
                      stage_counts.get("pricing", 0) * 0.15, 1),
        "value": round((forecast_60_days["deals"] + 
                       stage_counts.get("sow", 0) * 0.25 + 
                       stage_counts.get("pricing", 0) * 0.15) * avg_deal_value, 0)
    }
    
    return {
        "total_pipeline": total_leads - stage_counts.get("complete", 0),
        "already_closed": stage_counts.get("complete", 0),
        "avg_deal_value": round(avg_deal_value, 0),
        "stage_distribution": stage_counts,
        "pipeline_forecast": pipeline_forecast,
        "weighted_summary": {
            "expected_deals": round(total_weighted_deals, 1),
            "expected_value": round(total_weighted_value, 0)
        },
        "time_based_forecast": {
            "30_days": forecast_30_days,
            "60_days": forecast_60_days,
            "90_days": forecast_90_days
        },
        "insights": [
            f"Expected {round(total_weighted_deals, 1)} deals worth {round(total_weighted_value/100000, 1)}L from current pipeline",
            f"High-probability deals (payment/kickoff): {stage_counts.get('payment', 0) + stage_counts.get('kickoff', 0)}",
            f"Average deal value: {round(avg_deal_value/100000, 2)}L"
        ]
    }


@router.get("/analytics/time-in-stage")
async def get_time_in_stage_analytics(
    current_user: User = Depends(get_current_user)
):
    """
    Calculate average time leads spend at each funnel stage.
    """
    from dateutil import parser as date_parser
    db = get_db()
    
    leads = await db.leads.find(
        {"stage_timestamps": {"$exists": True}},
        {"_id": 0, "id": 1, "stage_timestamps": 1, "company": 1, "status": 1}
    ).to_list(500)
    
    leads_without_timestamps = await db.leads.find(
        {"stage_timestamps": {"$exists": False}},
        {"_id": 0, "id": 1, "created_at": 1, "company": 1}
    ).to_list(500)
    
    stage_order = ["lead", "meeting", "pricing", "sow", "quotation", "agreement", "signed", "payment", "kickoff", "complete"]
    stage_durations = {stage: [] for stage in stage_order[:-1]}
    
    for lead in leads:
        timestamps = lead.get("stage_timestamps", {})
        
        for i in range(len(stage_order) - 1):
            current_stage = stage_order[i]
            next_stage = stage_order[i + 1]
            
            current_ts = timestamps.get(current_stage)
            next_ts = timestamps.get(next_stage)
            
            if current_ts and next_ts:
                try:
                    current_dt = date_parser.parse(current_ts) if isinstance(current_ts, str) else current_ts
                    next_dt = date_parser.parse(next_ts) if isinstance(next_ts, str) else next_ts
                    days = (next_dt - current_dt).days
                    if days >= 0:
                        stage_durations[current_stage].append(days)
                except:
                    pass
    
    for lead in leads_without_timestamps:
        lead_id = lead.get("id")
        lead_created = lead.get("created_at")
        
        if not lead_created:
            continue
        
        try:
            lead_dt = date_parser.parse(lead_created) if isinstance(lead_created, str) else lead_created
        except:
            continue
        
        meeting = await db.meeting_records.find_one({"lead_id": lead_id}, {"_id": 0, "created_at": 1, "meeting_date": 1})
        if meeting:
            try:
                meeting_ts = meeting.get("created_at") or meeting.get("meeting_date")
                meeting_dt = date_parser.parse(meeting_ts) if isinstance(meeting_ts, str) else meeting_ts
                days = (meeting_dt - lead_dt).days
                if days >= 0:
                    stage_durations["lead"].append(days)
            except:
                pass
    
    stage_analytics = []
    for stage in stage_order[:-1]:
        durations = stage_durations.get(stage, [])
        if durations:
            avg_days = round(sum(durations) / len(durations), 1)
            min_days = min(durations)
            max_days = max(durations)
            count = len(durations)
        else:
            avg_days = None
            min_days = None
            max_days = None
            count = 0
        
        is_slow = avg_days is not None and avg_days > 7
        
        stage_analytics.append({
            "stage": stage,
            "name": stage.replace("_", " ").title(),
            "avg_days": avg_days,
            "min_days": min_days,
            "max_days": max_days,
            "sample_count": count,
            "is_slow": is_slow,
            "benchmark": 7
        })
    
    total_avg = sum(s["avg_days"] for s in stage_analytics if s["avg_days"] is not None)
    stages_with_data = sum(1 for s in stage_analytics if s["avg_days"] is not None)
    slowest = max([s for s in stage_analytics if s["avg_days"] is not None], key=lambda x: x["avg_days"], default=None)
    
    return {
        "stages": stage_analytics,
        "total_leads_analyzed": len(leads) + len(leads_without_timestamps),
        "leads_with_timestamps": len(leads),
        "overall_metrics": {
            "avg_total_days": round(total_avg, 1) if total_avg else None,
            "stages_with_data": stages_with_data,
            "slowest_stage": slowest["stage"] if slowest else None,
            "slowest_stage_days": slowest["avg_days"] if slowest else None
        },
        "insights": [
            f"Average total journey time: {round(total_avg, 0)} days" if total_avg else "Insufficient data for total time",
            f"Slowest stage: {slowest['name']} ({slowest['avg_days']} days)" if slowest else None,
            f"Data from {len(leads)} leads with full timestamps"
        ]
    }


@router.get("/analytics/win-loss")
async def get_win_loss_analysis(
    current_user: User = Depends(get_current_user)
):
    """
    Analyze won vs lost deals by stage.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    
    all_leads = await db.leads.find({}, {"_id": 0}).to_list(1000)
    lead_ids = [l["id"] for l in all_leads]
    
    won_leads = []
    lost_leads = []
    stale_leads = []
    active_leads = []
    
    meetings = {m["lead_id"]: m for m in await db.meeting_records.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "created_at": 1}).to_list(1000)}
    pricing = {p["lead_id"]: p for p in await db.pricing_plans.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "id": 1}).to_list(1000)}
    sows = {s["lead_id"]: s for s in await db.enhanced_sow.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1}).to_list(1000)}
    quotations = {q["lead_id"]: q for q in await db.quotations.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1}).to_list(1000)}
    agreements = {a["lead_id"]: a for a in await db.agreements.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "status": 1}).to_list(1000)}
    kickoffs = {k["lead_id"]: k for k in await db.kickoff_requests.find({"lead_id": {"$in": lead_ids}}, {"_id": 0, "lead_id": 1, "status": 1}).to_list(1000)}
    
    lost_at_stage = {
        "lead": 0, "meeting": 0, "pricing": 0, "sow": 0,
        "quotation": 0, "agreement": 0, "signed": 0, "payment": 0, "kickoff": 0
    }
    stale_at_stage = {
        "lead": 0, "meeting": 0, "pricing": 0, "sow": 0,
        "quotation": 0, "agreement": 0, "signed": 0, "payment": 0, "kickoff": 0
    }
    
    for lead in all_leads:
        lead_id = lead.get("id")
        status = lead.get("status", "")
        updated_at = lead.get("updated_at", "")
        lost_reason = lead.get("lost_reason")
        
        current_stage = "lead"
        if lead_id in meetings:
            current_stage = "meeting"
        if lead_id in pricing:
            current_stage = "pricing"
        if lead_id in sows:
            current_stage = "sow"
        if lead_id in quotations:
            current_stage = "quotation"
        if lead_id in agreements:
            agr = agreements[lead_id]
            current_stage = "agreement"
            if agr.get("status") == "signed":
                current_stage = "signed"
        if lead_id in kickoffs:
            kf = kickoffs[lead_id]
            current_stage = "kickoff"
            if kf.get("status") == "accepted":
                won_leads.append({
                    "lead_id": lead_id,
                    "company": lead.get("company") or lead.get("last_name"),
                    "final_stage": "complete"
                })
                continue
        
        if status == "lost":
            lost_leads.append({
                "lead_id": lead_id,
                "company": lead.get("company") or lead.get("last_name"),
                "lost_at_stage": current_stage,
                "reason": lost_reason or "Not specified"
            })
            lost_at_stage[current_stage] += 1
        elif updated_at and updated_at < thirty_days_ago:
            stale_leads.append({
                "lead_id": lead_id,
                "company": lead.get("company") or lead.get("last_name"),
                "stale_at_stage": current_stage,
                "last_update": updated_at
            })
            stale_at_stage[current_stage] += 1
        else:
            active_leads.append({
                "lead_id": lead_id,
                "company": lead.get("company") or lead.get("last_name"),
                "current_stage": current_stage
            })
    
    total_leads = len(all_leads)
    total_won = len(won_leads)
    total_lost = len(lost_leads)
    total_stale = len(stale_leads)
    total_active = len(active_leads)
    
    closed_leads = total_won + total_lost
    win_rate = round((total_won / closed_leads * 100) if closed_leads > 0 else 0, 1)
    
    worst_loss_stage = max(lost_at_stage.items(), key=lambda x: x[1]) if any(lost_at_stage.values()) else (None, 0)
    worst_stale_stage = max(stale_at_stage.items(), key=lambda x: x[1]) if any(stale_at_stage.values()) else (None, 0)
    
    return {
        "summary": {
            "total_leads": total_leads,
            "won": total_won,
            "lost": total_lost,
            "stale_30_days": total_stale,
            "active": total_active,
            "win_rate": win_rate
        },
        "lost_at_stage": lost_at_stage,
        "stale_at_stage": stale_at_stage,
        "lost_leads": lost_leads[:10],
        "stale_leads": stale_leads[:10],
        "insights": [
            f"Win rate: {win_rate}% ({total_won} won, {total_lost} lost)",
            f"Most losses at: {worst_loss_stage[0]} stage ({worst_loss_stage[1]} leads)" if worst_loss_stage[0] else None,
            f"Most stale at: {worst_stale_stage[0]} stage ({worst_stale_stage[1]} leads)" if worst_stale_stage[0] else None,
            f"{total_stale} leads haven't progressed in 30+ days" if total_stale > 0 else None
        ],
        "at_risk": {
            "count": total_stale,
            "leads": stale_leads[:5]
        }
    }


@router.get("/analytics/velocity")
async def get_velocity_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Calculate sales velocity metrics.
    """
    from dateutil import parser as date_parser
    db = get_db()
    
    kickoffs = await db.kickoff_requests.find(
        {"status": "accepted"},
        {"_id": 0, "lead_id": 1, "created_at": 1, "updated_at": 1}
    ).to_list(500)
    
    completed_lead_ids = [k["lead_id"] for k in kickoffs]
    
    completed_leads = await db.leads.find(
        {"id": {"$in": completed_lead_ids}},
        {"_id": 0, "id": 1, "created_at": 1, "stage_timestamps": 1, "company": 1}
    ).to_list(500)
    
    velocities = []
    stage_velocities = {
        "lead_to_meeting": [], "meeting_to_pricing": [], "pricing_to_sow": [],
        "sow_to_quotation": [], "quotation_to_agreement": [], "agreement_to_signed": [],
        "signed_to_payment": [], "payment_to_kickoff": [], "kickoff_to_complete": []
    }
    
    for lead in completed_leads:
        lead_id = lead.get("id")
        lead_created = lead.get("created_at")
        stage_ts = lead.get("stage_timestamps", {})
        
        kickoff = next((k for k in kickoffs if k["lead_id"] == lead_id), None)
        if not kickoff:
            continue
        
        kickoff_date = kickoff.get("updated_at") or kickoff.get("created_at")
        
        if not lead_created or not kickoff_date:
            continue
        
        try:
            lead_dt = date_parser.parse(lead_created) if isinstance(lead_created, str) else lead_created
            kickoff_dt = date_parser.parse(kickoff_date) if isinstance(kickoff_date, str) else kickoff_date
            total_days = (kickoff_dt - lead_dt).days
            
            if total_days >= 0:
                velocities.append({
                    "lead_id": lead_id,
                    "company": lead.get("company"),
                    "days": total_days,
                    "lead_date": lead_created,
                    "close_date": kickoff_date
                })
        except:
            continue
        
        if stage_ts:
            stage_pairs = [
                ("lead", "meeting", "lead_to_meeting"),
                ("meeting", "pricing", "meeting_to_pricing"),
                ("pricing", "sow", "pricing_to_sow"),
                ("sow", "quotation", "sow_to_quotation"),
                ("quotation", "agreement", "quotation_to_agreement"),
                ("agreement", "signed", "agreement_to_signed"),
                ("signed", "payment", "signed_to_payment"),
                ("payment", "kickoff", "payment_to_kickoff"),
                ("kickoff", "complete", "kickoff_to_complete")
            ]
            
            for from_stage, to_stage, key in stage_pairs:
                from_ts = stage_ts.get(from_stage)
                to_ts = stage_ts.get(to_stage)
                
                if from_ts and to_ts:
                    try:
                        from_dt = date_parser.parse(from_ts) if isinstance(from_ts, str) else from_ts
                        to_dt = date_parser.parse(to_ts) if isinstance(to_ts, str) else to_ts
                        days = (to_dt - from_dt).days
                        if days >= 0:
                            stage_velocities[key].append(days)
                    except:
                        pass
    
    avg_total = round(sum(v["days"] for v in velocities) / len(velocities), 1) if velocities else None
    min_total = min(v["days"] for v in velocities) if velocities else None
    max_total = max(v["days"] for v in velocities) if velocities else None
    
    stage_velocity_summary = []
    for key, days_list in stage_velocities.items():
        if days_list:
            stage_velocity_summary.append({
                "stage": key.replace("_to_", " → ").title(),
                "avg_days": round(sum(days_list) / len(days_list), 1),
                "count": len(days_list)
            })
    
    return {
        "total_completed_deals": len(velocities),
        "overall_velocity": {
            "avg_days": avg_total,
            "min_days": min_total,
            "max_days": max_total
        },
        "stage_velocities": stage_velocity_summary,
        "recent_deals": sorted(velocities, key=lambda x: x["days"])[:10],
        "insights": [
            f"Average time to close: {avg_total} days" if avg_total else "No completed deals to analyze",
            f"Fastest deal: {min_total} days" if min_total else None,
            f"Slowest deal: {max_total} days" if max_total else None
        ]
    }
