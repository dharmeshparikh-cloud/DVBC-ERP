"""
AI-Powered ERP Assistant Router
- Report Analysis & Summaries
- Natural Language Queries
- Trend Insights & Predictions
- Actionable Suggestions
- Hierarchical Role-Based Access Control (RBAC)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import uuid
import os
import json
import logging

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

logger = logging.getLogger(__name__)


# Pydantic Models
class AIQueryRequest(BaseModel):
    query: str
    context: Optional[str] = None  # e.g., "sales", "hr", "finance"
    session_id: Optional[str] = None

class AIQueryResponse(BaseModel):
    response: str
    data: Optional[Dict[str, Any]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[str]] = None
    query_type: str  # analysis, query, insight, action

class ReportAnalysisRequest(BaseModel):
    report_type: str  # sales, hr, finance, attendance, etc.
    date_range: Optional[Dict[str, str]] = None  # {start: "2026-01-01", end: "2026-02-20"}
    filters: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    role: str  # user or assistant
    content: str
    timestamp: datetime = None


def get_db():
    from server import db
    return db


# ==================== RBAC HELPERS ====================

async def get_user_access_level(db, user_id: str) -> dict:
    """
    Determine user's access level based on role hierarchy:
    - admin: Full access to everything
    - department_head: Department-wide access
    - manager: Team's data (direct reports)
    - consultant/employee: Own data only
    """
    user = await db.users.find_one({"id": user_id})
    if not user:
        return {"level": "none", "user": None}
    
    role = user.get("role", "").lower()
    department = user.get("department", "")
    
    # Check if user is restricted from AI
    if user.get("ai_restricted", False):
        return {"level": "restricted", "user": user, "reason": "AI access has been restricted by admin"}
    
    # Admin has full access
    if role == "admin":
        return {
            "level": "admin",
            "user": user,
            "can_access": ["all"],
            "filter": None
        }
    
    # Check if user is a department head
    employee = await db.employees.find_one({"email": user.get("email")})
    is_department_head = employee.get("is_department_head", False) if employee else False
    
    # Get direct reports for managers
    direct_reports = []
    if employee:
        reports = await db.employees.find({"reporting_manager_id": employee.get("id")}).to_list(100)
        direct_reports = [r.get("id") for r in reports]
    
    if is_department_head:
        return {
            "level": "department_head",
            "user": user,
            "department": department,
            "can_access": [department.lower()],
            "filter": {"department": department}
        }
    
    if direct_reports:
        return {
            "level": "manager",
            "user": user,
            "department": department,
            "team_ids": direct_reports + [employee.get("id")] if employee else direct_reports,
            "can_access": ["team"],
            "filter": {"team_ids": direct_reports}
        }
    
    # Regular employee/consultant - own data only
    return {
        "level": "employee",
        "user": user,
        "employee_id": employee.get("id") if employee else None,
        "department": department,
        "can_access": ["self"],
        "filter": {"employee_id": employee.get("id") if employee else user_id}
    }


async def get_filtered_erp_context(db, context_type: str, access: dict, date_range: dict = None) -> dict:
    """Gather ERP data filtered by user's access level"""
    data = {}
    level = access.get("level")
    
    if level == "restricted":
        return {"error": access.get("reason", "Access restricted")}
    
    now = datetime.now(timezone.utc)
    start_date = datetime.fromisoformat(date_range["start"]) if date_range and date_range.get("start") else now - timedelta(days=30)
    end_date = datetime.fromisoformat(date_range["end"]) if date_range and date_range.get("end") else now
    
    # Build access info for AI context
    data["_access_info"] = {
        "level": level,
        "message": _get_access_message(level, access)
    }
    
    # SALES DATA
    if context_type in ["sales", "all"]:
        if level == "admin" or (level == "department_head" and access.get("department", "").lower() == "sales"):
            # Full sales access
            leads = await db.leads.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(1000)
            agreements = await db.agreements.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(1000)
        elif level == "manager" and access.get("department", "").lower() == "sales":
            # Team's sales only
            team_ids = access.get("team_ids", [])
            leads = await db.leads.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "$or": [{"assigned_to": {"$in": team_ids}}, {"created_by": {"$in": team_ids}}]
            }).to_list(1000)
            agreements = await db.agreements.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "created_by": {"$in": team_ids}
            }).to_list(1000)
        elif level == "employee" and access.get("department", "").lower() == "sales":
            # Own sales only
            emp_id = access.get("employee_id")
            leads = await db.leads.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "$or": [{"assigned_to": emp_id}, {"created_by": emp_id}]
            }).to_list(1000)
            agreements = await db.agreements.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "created_by": emp_id
            }).to_list(1000)
        else:
            # No sales access for non-sales users (except admin)
            leads = []
            agreements = []
            if context_type == "sales":
                data["sales"] = {"message": "You don't have access to sales data"}
        
        if leads or agreements or level == "admin":
            total_leads = len(leads)
            won_leads = len([l for l in leads if l.get("status") == "Won"])
            conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
            total_revenue = sum(a.get("total_value", 0) for a in agreements)
            
            data["sales"] = {
                "total_leads": total_leads,
                "won_leads": won_leads,
                "conversion_rate": round(conversion_rate, 1),
                "total_revenue": total_revenue,
                "access_level": level
            }
    
    # HR DATA
    if context_type in ["hr", "all"]:
        if level == "admin" or (level == "department_head" and access.get("department", "").lower() == "hr"):
            # Full HR access
            employees = await db.employees.find({"is_active": True}).to_list(1000)
            leave_requests = await db.leave_requests.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(1000)
        elif level == "manager":
            # Team's HR data
            team_ids = access.get("team_ids", [])
            employees = await db.employees.find({"id": {"$in": team_ids}, "is_active": True}).to_list(100)
            leave_requests = await db.leave_requests.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "employee_id": {"$in": team_ids}
            }).to_list(1000)
        elif level == "department_head":
            # Department HR data
            dept = access.get("department")
            employees = await db.employees.find({"department": dept, "is_active": True}).to_list(1000)
            emp_ids = [e.get("id") for e in employees]
            leave_requests = await db.leave_requests.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "employee_id": {"$in": emp_ids}
            }).to_list(1000)
        else:
            # Own HR data only
            emp_id = access.get("employee_id")
            employees = await db.employees.find({"id": emp_id}).to_list(1)
            leave_requests = await db.leave_requests.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "employee_id": emp_id
            }).to_list(100)
        
        total_employees = len(employees)
        pending_leaves = len([l for l in leave_requests if l.get("status") == "pending"])
        approved_leaves = len([l for l in leave_requests if l.get("status") == "approved"])
        
        data["hr"] = {
            "total_employees": total_employees,
            "pending_leave_requests": pending_leaves,
            "approved_leaves": approved_leaves,
            "access_level": level
        }
    
    # FINANCE DATA (Restricted - Admin and Finance dept only)
    if context_type in ["finance", "all"]:
        if level == "admin" or (level == "department_head" and access.get("department", "").lower() == "finance"):
            expenses = await db.expenses.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(1000)
            payments = await db.project_payments.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(1000)
            
            data["finance"] = {
                "total_expenses": sum(e.get("amount", 0) for e in expenses),
                "pending_expenses": sum(e.get("amount", 0) for e in expenses if e.get("status") == "pending"),
                "total_collected": sum(p.get("amount", 0) for p in payments if p.get("status") == "verified"),
                "access_level": level
            }
        elif level == "employee":
            # Own expenses only
            emp_id = access.get("employee_id")
            expenses = await db.expenses.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "employee_id": emp_id
            }).to_list(100)
            
            data["finance"] = {
                "my_expenses": sum(e.get("amount", 0) for e in expenses),
                "my_pending": sum(e.get("amount", 0) for e in expenses if e.get("status") == "pending"),
                "access_level": "self_only"
            }
        else:
            data["finance"] = {"message": "Finance data is restricted to Finance department and Admin"}
    
    # PROJECTS/CONSULTING DATA
    if context_type in ["projects", "consulting", "all"]:
        if level == "admin":
            projects = await db.projects.find({}).to_list(1000)
        elif level == "department_head" and access.get("department", "").lower() == "consulting":
            projects = await db.projects.find({}).to_list(1000)
        elif level == "manager":
            team_ids = access.get("team_ids", [])
            projects = await db.projects.find({
                "$or": [{"pm_id": {"$in": team_ids}}, {"team_members": {"$in": team_ids}}]
            }).to_list(100)
        else:
            # Own projects only
            emp_id = access.get("employee_id")
            projects = await db.projects.find({
                "$or": [{"pm_id": emp_id}, {"team_members": emp_id}]
            }).to_list(50)
        
        active_projects = len([p for p in projects if p.get("status") in ["active", "in_progress"]])
        
        data["projects"] = {
            "total_projects": len(projects),
            "active_projects": active_projects,
            "access_level": level
        }
    
    return data


def _get_access_message(level: str, access: dict) -> str:
    """Generate a message explaining the user's access level"""
    if level == "admin":
        return "You have full access to all ERP data."
    elif level == "department_head":
        return f"You have access to all {access.get('department', 'department')} data."
    elif level == "manager":
        return "You have access to your team's data (direct reports)."
    elif level == "employee":
        return "You have access to your own data only."
    else:
        return "Limited access."


async def get_erp_context(db, context_type: str, date_range: dict = None) -> dict:
    """Gather relevant ERP data for AI context"""
    data = {}
    
    now = datetime.now(timezone.utc)
    start_date = datetime.fromisoformat(date_range["start"]) if date_range and date_range.get("start") else now - timedelta(days=30)
    end_date = datetime.fromisoformat(date_range["end"]) if date_range and date_range.get("end") else now
    
    if context_type in ["sales", "all"]:
        # Sales data
        leads = await db.leads.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(1000)
        
        total_leads = len(leads)
        won_leads = len([l for l in leads if l.get("status") == "Won"])
        conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Revenue from agreements
        agreements = await db.agreements.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(1000)
        total_revenue = sum(a.get("total_value", 0) for a in agreements)
        
        data["sales"] = {
            "total_leads": total_leads,
            "won_leads": won_leads,
            "conversion_rate": round(conversion_rate, 1),
            "total_revenue": total_revenue,
            "leads_by_status": {},
            "top_sources": []
        }
        
        # Group by status
        for lead in leads:
            status = lead.get("status", "Unknown")
            data["sales"]["leads_by_status"][status] = data["sales"]["leads_by_status"].get(status, 0) + 1
    
    if context_type in ["hr", "all"]:
        # HR data
        employees = await db.employees.find({"is_active": True}).to_list(1000)
        total_employees = len(employees)
        
        # Leave requests
        leave_requests = await db.leave_requests.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(1000)
        
        pending_leaves = len([l for l in leave_requests if l.get("status") == "pending"])
        approved_leaves = len([l for l in leave_requests if l.get("status") == "approved"])
        
        # Attendance
        attendance = await db.attendance.find({
            "date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}
        }).to_list(10000)
        
        present_days = len([a for a in attendance if a.get("status") == "present"])
        total_records = len(attendance)
        attendance_rate = (present_days / total_records * 100) if total_records > 0 else 0
        
        data["hr"] = {
            "total_employees": total_employees,
            "pending_leave_requests": pending_leaves,
            "approved_leaves": approved_leaves,
            "attendance_rate": round(attendance_rate, 1),
            "employees_by_department": {}
        }
        
        # Group by department
        for emp in employees:
            dept = emp.get("department", "Unknown")
            data["hr"]["employees_by_department"][dept] = data["hr"]["employees_by_department"].get(dept, 0) + 1
    
    if context_type in ["finance", "all"]:
        # Finance data
        expenses = await db.expenses.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(1000)
        
        total_expenses = sum(e.get("amount", 0) for e in expenses)
        pending_expenses = sum(e.get("amount", 0) for e in expenses if e.get("status") == "pending")
        approved_expenses = sum(e.get("amount", 0) for e in expenses if e.get("status") == "approved")
        
        # Payments
        payments = await db.project_payments.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(1000)
        
        total_collected = sum(p.get("amount", 0) for p in payments if p.get("status") == "verified")
        
        data["finance"] = {
            "total_expenses": total_expenses,
            "pending_expenses": pending_expenses,
            "approved_expenses": approved_expenses,
            "total_collected": total_collected
        }
    
    if context_type in ["projects", "all"]:
        # Project data
        projects = await db.projects.find({}).to_list(1000)
        active_projects = len([p for p in projects if p.get("status") in ["active", "in_progress"]])
        
        # Kickoff requests
        kickoffs = await db.kickoff_requests.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(100)
        
        data["projects"] = {
            "total_projects": len(projects),
            "active_projects": active_projects,
            "pending_kickoffs": len([k for k in kickoffs if k.get("status") == "pending"]),
            "approved_kickoffs": len([k for k in kickoffs if k.get("status") == "approved"])
        }
    
    return data


async def query_ai(prompt: str, session_id: str, system_context: str = None) -> str:
    """Query the AI model with ERP context"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        system_message = """You are NETRA AI, an intelligent assistant for the DVBC Business Management ERP system.
Your role is to:
1. Analyze business data and provide insights
2. Answer questions about HR, Sales, Finance, and Projects
3. Identify trends and patterns
4. Suggest actionable improvements
5. Help users understand their data better

Always be concise, professional, and data-driven in your responses.
When showing numbers, format them nicely (e.g., ₹4.5 Cr instead of 45000000).
Provide actionable suggestions when appropriate."""
        
        if system_context:
            system_message += f"\n\nCurrent ERP Data Context:\n{system_context}"
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
        
    except Exception as e:
        logger.error(f"AI query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")


# ==================== ENDPOINTS ====================

@router.post("/query", response_model=dict)
async def ai_query(
    request: AIQueryRequest,
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Process a natural language query about ERP data with RBAC"""
    # Check user access level
    access = await get_user_access_level(db, user_id)
    
    if access.get("level") == "restricted":
        raise HTTPException(status_code=403, detail=access.get("reason", "AI access restricted"))
    
    if access.get("level") == "none":
        raise HTTPException(status_code=404, detail="User not found")
    
    session_id = request.session_id or f"erp_ai_{user_id}_{datetime.now().strftime('%Y%m%d')}"
    
    # Get RBAC-filtered ERP context
    context_type = request.context or "all"
    erp_data = await get_filtered_erp_context(db, context_type, access)
    
    # Format context for AI with access level info
    context_str = json.dumps(erp_data, indent=2, default=str)
    
    # Query AI
    response = await query_ai(request.query, session_id, context_str)
    
    # Save chat history
    chat_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_id": session_id,
        "query": request.query,
        "response": response,
        "context": context_type,
        "access_level": access.get("level"),
        "created_at": datetime.now(timezone.utc)
    }
    await db.ai_chat_history.insert_one(chat_entry)
    
    # Determine query type
    query_lower = request.query.lower()
    if any(word in query_lower for word in ["analyze", "summary", "report", "performance"]):
        query_type = "analysis"
    elif any(word in query_lower for word in ["show", "list", "find", "get", "how many"]):
        query_type = "query"
    elif any(word in query_lower for word in ["trend", "predict", "forecast", "why"]):
        query_type = "insight"
    else:
        query_type = "general"
    
    return {
        "response": response,
        "query_type": query_type,
        "session_id": session_id,
        "access_level": access.get("level"),
        "data": erp_data if query_type in ["analysis", "query"] else None
    }


@router.post("/analyze-report", response_model=dict)
async def analyze_report(
    request: ReportAnalysisRequest,
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Generate AI analysis for a specific report type"""
    session_id = f"report_analysis_{user_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    # Get data for the report type
    erp_data = await get_erp_context(db, request.report_type, request.date_range)
    
    # Create analysis prompt
    prompt = f"""Analyze the following {request.report_type} data and provide:
1. Key highlights and metrics
2. Notable trends or patterns
3. Areas of concern (if any)
4. Actionable recommendations

Data:
{json.dumps(erp_data, indent=2, default=str)}

Please format your response in clear sections with bullet points."""
    
    response = await query_ai(prompt, session_id)
    
    return {
        "analysis": response,
        "report_type": request.report_type,
        "data": erp_data,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/suggestions", response_model=dict)
async def get_ai_suggestions(
    user_id: str = Query(...),
    context: str = Query("all"),
    db=Depends(get_db)
):
    """Get AI-powered suggestions based on current ERP state"""
    session_id = f"suggestions_{user_id}_{datetime.now().strftime('%Y%m%d')}"
    
    # Get current ERP context
    erp_data = await get_erp_context(db, context)
    
    prompt = f"""Based on the current ERP data, provide 3-5 actionable suggestions to improve business operations.
Focus on:
- Immediate actions that can be taken today
- Bottlenecks that need attention
- Opportunities for improvement

Current Data:
{json.dumps(erp_data, indent=2, default=str)}

Format each suggestion as a brief, actionable item."""
    
    response = await query_ai(prompt, session_id)
    
    # Parse suggestions into list
    suggestions = [s.strip() for s in response.split("\n") if s.strip() and (s.strip().startswith("-") or s.strip()[0].isdigit())]
    
    return {
        "suggestions": suggestions,
        "raw_response": response,
        "context": context
    }


@router.get("/chat-history")
async def get_chat_history(
    user_id: str = Query(...),
    session_id: Optional[str] = None,
    limit: int = Query(20, le=100),
    db=Depends(get_db)
):
    """Get AI chat history for a user"""
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    
    history = await db.ai_chat_history.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    result = []
    for h in history:
        h["id"] = h.get("id", str(h["_id"]))
        if "_id" in h:
            del h["_id"]
        result.append(h)
    
    return result


@router.post("/quick-insights", response_model=dict)
async def get_quick_insights(
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Get quick AI-generated insights for the dashboard"""
    # Get snapshot of key metrics
    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)
    
    # Quick stats
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    pending_expenses = await db.expenses.count_documents({"status": "pending"})
    active_leads = await db.leads.count_documents({"status": {"$in": ["New", "Contacted", "Qualified"]}})
    
    # Recent activities
    recent_agreements = await db.agreements.count_documents({
        "created_at": {"$gte": last_week}
    })
    
    insights = []
    
    if pending_leaves > 5:
        insights.append({
            "type": "warning",
            "icon": "calendar",
            "message": f"{pending_leaves} leave requests pending approval",
            "action": "Review in Leave Management"
        })
    
    if pending_expenses > 3:
        insights.append({
            "type": "info",
            "icon": "receipt",
            "message": f"₹{pending_expenses:,} in expenses awaiting approval",
            "action": "Go to Expense Approvals"
        })
    
    if active_leads > 10:
        insights.append({
            "type": "success",
            "icon": "trending-up",
            "message": f"{active_leads} active leads in pipeline",
            "action": "View Sales Dashboard"
        })
    
    if recent_agreements > 0:
        insights.append({
            "type": "success",
            "icon": "file-check",
            "message": f"{recent_agreements} new agreements this week",
            "action": "View Agreements"
        })
    
    return {
        "insights": insights,
        "generated_at": now.isoformat()
    }


@router.delete("/chat-history")
async def clear_chat_history(
    user_id: str = Query(...),
    session_id: Optional[str] = None,
    db=Depends(get_db)
):
    """Clear AI chat history"""
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    
    result = await db.ai_chat_history.delete_many(query)
    return {"deleted": result.deleted_count}
