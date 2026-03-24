"""
Business Governance Router - ERP Self-Auditing System

Provides:
1. MOM SLA Monitoring & Escalation
2. Expense Compliance Dashboard
3. Operational Discipline Metrics
4. Anomaly Detection
5. Leakage Prevention Alerts
6. Automated Governance Triggers
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .deps import get_db, get_current_user
from .models import User
import uuid

router = APIRouter(prefix="/governance", tags=["Business Governance"])


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

MOM_SLA_HOURS = 24  # MOM must be recorded within 24 hours of meeting
EXPENSE_RECEIPT_THRESHOLD = 500  # Receipt required for expenses >= this amount
STALE_LEAD_DAYS = 14  # Lead is stale if no activity for this many days
HIGH_VALUE_EXPENSE_THRESHOLD = 5000  # Requires admin approval


# ═══════════════════════════════════════════════════════════════════
# GOVERNANCE TRIGGERS & AUTOMATION HELPERS
# ═══════════════════════════════════════════════════════════════════

async def create_expense_prompt_notification(
    db, 
    user_id: str, 
    meeting_id: str, 
    meeting_title: str,
    client_name: str = None,
    meeting_date: str = None
):
    """
    Create a notification prompting user to file travel expense after in-person meeting delivery.
    Called automatically when a meeting is marked as delivered.
    """
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "expense_prompt",
        "title": "File Travel Expense",
        "message": f"You delivered an in-person meeting '{meeting_title}'{' with ' + client_name if client_name else ''}. Don't forget to file your travel expense!",
        "entity_type": "meeting",
        "entity_id": meeting_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "priority": "medium",
        "action_required": True,
        "action_path": "/my-expenses",
        "action_label": "File Expense",
        "metadata": {
            "meeting_date": meeting_date,
            "auto_generated": True,
            "governance_rule": "meeting_expense_link"
        }
    }
    await db.notifications.insert_one(notification)
    return notification["id"]


async def create_mom_sla_reminder(
    db,
    user_id: str,
    meeting_id: str,
    meeting_title: str,
    hours_overdue: float,
    escalate_to_manager: bool = False,
    manager_id: str = None
):
    """
    Create MOM SLA reminder notification for overdue meetings.
    Optionally escalates to manager.
    """
    now = datetime.now(timezone.utc)
    
    # Main notification to meeting owner
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "mom_sla_reminder",
        "title": "⚠️ MOM Overdue - Action Required",
        "message": f"Meeting '{meeting_title}' is {int(hours_overdue)} hours past the 24-hour MOM deadline. Please record MOM immediately.",
        "entity_type": "meeting",
        "entity_id": meeting_id,
        "read": False,
        "created_at": now.isoformat(),
        "priority": "high",
        "action_required": True,
        "action_path": "/consulting-meetings",
        "action_label": "Record MOM",
        "metadata": {
            "hours_overdue": round(hours_overdue, 1),
            "sla_breach": True,
            "governance_rule": "mom_sla_24h"
        }
    }
    await db.notifications.insert_one(notification)
    
    # Manager escalation if requested
    if escalate_to_manager and manager_id:
        escalation = {
            "id": str(uuid.uuid4()),
            "user_id": manager_id,
            "type": "mom_sla_escalation",
            "title": "🔴 Team MOM SLA Breach",
            "message": f"Meeting '{meeting_title}' has breached the 24-hour MOM SLA by {int(hours_overdue)} hours. Team member requires follow-up.",
            "entity_type": "meeting",
            "entity_id": meeting_id,
            "read": False,
            "created_at": now.isoformat(),
            "priority": "high",
            "action_required": True,
            "action_path": "/consulting-meetings",
            "action_label": "Review",
            "metadata": {
                "hours_overdue": round(hours_overdue, 1),
                "escalation": True,
                "original_owner_id": user_id,
                "governance_rule": "mom_sla_24h"
            }
        }
        await db.notifications.insert_one(escalation)
        
        # Mark meeting as escalated
        await db.meetings.update_one(
            {"id": meeting_id},
            {"$set": {
                "mom_sla_escalated": True,
                "mom_sla_escalated_at": now.isoformat()
            }}
        )
    
    return notification["id"]


# ═══════════════════════════════════════════════════════════════════
# AUTOMATED MOM SLA REMINDER SYSTEM
# ═══════════════════════════════════════════════════════════════════

@router.post("/mom-sla/run-reminders")
async def run_mom_sla_reminders(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Run automated MOM SLA reminder system.
    Scans for overdue meetings and sends notifications:
    - 24-36 hours overdue: Reminder to meeting owner
    - >36 hours overdue: Escalation to reporting manager
    
    Can be called manually or by a scheduler.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Get all meetings without MOM that are past SLA
    meetings = await db.meetings.find(
        {
            "status": {"$nin": ["cancelled", "CANCELLED"]},
            "mom_generated": {"$ne": True}
        },
        {"_id": 0}
    ).to_list(500)
    
    reminders_sent = 0
    escalations_sent = 0
    skipped = 0
    
    for m in meetings:
        meeting_date = m.get("meeting_date")
        if not meeting_date:
            continue
            
        try:
            if isinstance(meeting_date, str):
                m_dt = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
            else:
                m_dt = meeting_date if meeting_date.tzinfo else meeting_date.replace(tzinfo=timezone.utc)
            
            # Only check past meetings
            if m_dt > now:
                continue
            
            hours_since = (now - m_dt).total_seconds() / 3600
            
            # Skip if within SLA
            if hours_since <= MOM_SLA_HOURS:
                continue
            
            # Check if already notified recently (within 12 hours)
            last_reminder = m.get("last_mom_reminder_at")
            if last_reminder:
                try:
                    last_dt = datetime.fromisoformat(str(last_reminder).replace("Z", "+00:00"))
                    if (now - last_dt).total_seconds() < 12 * 3600:
                        skipped += 1
                        continue
                except (ValueError, TypeError, AttributeError):
                    pass
            
            meeting_owner = m.get("created_by") or m.get("scheduled_by")
            if not meeting_owner:
                continue
            
            hours_overdue = hours_since - MOM_SLA_HOURS
            
            # Determine if escalation needed (>36 hours = 12 hours past SLA)
            needs_escalation = hours_overdue > 12 and not m.get("mom_sla_escalated")
            
            # Get manager for escalation
            manager_id = None
            if needs_escalation:
                employee = await db.employees.find_one({"user_id": meeting_owner}, {"_id": 0, "reporting_manager_id": 1})
                if employee:
                    manager_id = employee.get("reporting_manager_id")
            
            # Create reminder
            await create_mom_sla_reminder(
                db=db,
                user_id=meeting_owner,
                meeting_id=m.get("id"),
                meeting_title=m.get("title", "Meeting"),
                hours_overdue=hours_overdue,
                escalate_to_manager=needs_escalation,
                manager_id=manager_id
            )
            
            # Update meeting with last reminder time
            await db.meetings.update_one(
                {"id": m.get("id")},
                {"$set": {"last_mom_reminder_at": now.isoformat()}}
            )
            
            reminders_sent += 1
            if needs_escalation:
                escalations_sent += 1
                
        except Exception as e:
            print(f"Error processing meeting {m.get('id')}: {e}")
            continue
    
    return {
        "message": "MOM SLA reminder system executed",
        "reminders_sent": reminders_sent,
        "escalations_sent": escalations_sent,
        "skipped_recent": skipped,
        "executed_at": now.isoformat()
    }


@router.get("/mom-sla/pending-reminders")
async def get_pending_mom_reminders(current_user: User = Depends(get_current_user)):
    """
    Get list of meetings that would receive reminders if run-reminders is called.
    Useful for preview before running automated reminders.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    meetings = await db.meetings.find(
        {
            "status": {"$nin": ["cancelled", "CANCELLED"]},
            "mom_generated": {"$ne": True}
        },
        {"_id": 0}
    ).to_list(500)
    
    pending = []
    
    for m in meetings:
        meeting_date = m.get("meeting_date")
        if not meeting_date:
            continue
            
        try:
            if isinstance(meeting_date, str):
                m_dt = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
            else:
                m_dt = meeting_date if meeting_date.tzinfo else meeting_date.replace(tzinfo=timezone.utc)
            
            if m_dt > now:
                continue
            
            hours_since = (now - m_dt).total_seconds() / 3600
            
            if hours_since <= MOM_SLA_HOURS:
                continue
            
            hours_overdue = hours_since - MOM_SLA_HOURS
            
            pending.append({
                "meeting_id": m.get("id"),
                "title": m.get("title"),
                "meeting_date": meeting_date,
                "created_by": m.get("created_by"),
                "project_name": m.get("project_name"),
                "client_name": m.get("client_name"),
                "hours_overdue": round(hours_overdue, 1),
                "would_escalate": hours_overdue > 12 and not m.get("mom_sla_escalated"),
                "last_reminder_at": m.get("last_mom_reminder_at"),
                "already_escalated": m.get("mom_sla_escalated", False)
            })
                
        except Exception:
            continue
    
    # Sort by hours overdue (most urgent first)
    pending.sort(key=lambda x: -x.get("hours_overdue", 0))
    
    return {
        "count": len(pending),
        "would_escalate": len([p for p in pending if p.get("would_escalate")]),
        "pending_meetings": pending[:50]
    }


# ═══════════════════════════════════════════════════════════════════
# MOM SLA MONITORING & ESCALATION
# ═══════════════════════════════════════════════════════════════════

@router.get("/mom-sla")
async def get_mom_sla_status(current_user: User = Depends(get_current_user)):
    """
    Get MOM SLA compliance status.
    Returns meetings that are:
    - Overdue (past SLA)
    - At risk (approaching SLA)
    - Compliant (MOM recorded on time)
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Get all meetings that need MOM
    meetings = await db.meetings.find(
        {"status": {"$nin": ["cancelled", "CANCELLED"]}},
        {"_id": 0}
    ).to_list(1000)
    
    overdue = []
    at_risk = []
    compliant = []
    
    for m in meetings:
        meeting_date = m.get("meeting_date")
        if not meeting_date:
            continue
            
        try:
            if isinstance(meeting_date, str):
                m_dt = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
            else:
                m_dt = meeting_date if meeting_date.tzinfo else meeting_date.replace(tzinfo=timezone.utc)
            
            # Only check past meetings
            if m_dt > now:
                continue
            
            has_mom = m.get("mom_generated", False)
            hours_since = (now - m_dt).total_seconds() / 3600
            
            meeting_info = {
                "id": m.get("id"),
                "title": m.get("title"),
                "meeting_date": meeting_date,
                "project_name": m.get("project_name"),
                "client_name": m.get("client_name"),
                "scheduled_by": m.get("scheduled_by_name"),
                "hours_since_meeting": round(hours_since, 1),
                "has_mom": has_mom
            }
            
            if has_mom:
                compliant.append(meeting_info)
            elif hours_since > MOM_SLA_HOURS:
                meeting_info["breach_hours"] = round(hours_since - MOM_SLA_HOURS, 1)
                overdue.append(meeting_info)
            elif hours_since > MOM_SLA_HOURS * 0.75:  # 75% of SLA = at risk
                meeting_info["hours_remaining"] = round(MOM_SLA_HOURS - hours_since, 1)
                at_risk.append(meeting_info)
                
        except Exception:
            continue
    
    # Sort by urgency
    overdue.sort(key=lambda x: -x.get("breach_hours", 0))
    at_risk.sort(key=lambda x: x.get("hours_remaining", 0))
    
    total_past = len(overdue) + len(at_risk) + len(compliant)
    compliance_rate = (len(compliant) / total_past * 100) if total_past > 0 else 100
    
    return {
        "sla_hours": MOM_SLA_HOURS,
        "summary": {
            "total_past_meetings": total_past,
            "overdue": len(overdue),
            "at_risk": len(at_risk),
            "compliant": len(compliant),
            "compliance_rate": round(compliance_rate, 1)
        },
        "overdue_meetings": overdue[:20],  # Top 20
        "at_risk_meetings": at_risk[:10],
        "recent_compliant": compliant[:5]
    }


@router.post("/mom-sla/escalate/{meeting_id}")
async def escalate_mom_sla(meeting_id: str, current_user: User = Depends(get_current_user)):
    """
    Manually escalate a MOM SLA breach to the manager.
    Creates notification and marks meeting for escalation.
    """
    db = get_db()
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if meeting.get("mom_generated"):
        raise HTTPException(status_code=400, detail="MOM already recorded for this meeting")
    
    now = datetime.now(timezone.utc)
    
    # Mark as escalated
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "mom_escalated": True,
            "mom_escalated_at": now.isoformat(),
            "mom_escalated_by": current_user.id
        }}
    )
    
    # Create notification for meeting owner
    scheduled_by = meeting.get("scheduled_by") or meeting.get("created_by")
    if scheduled_by:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": scheduled_by,
            "type": "mom_sla_escalation",
            "title": "MOM SLA Escalation",
            "message": f"MOM for meeting '{meeting.get('title')}' is overdue. Please record MOM immediately.",
            "entity_type": "meeting",
            "entity_id": meeting_id,
            "is_read": False,
            "created_at": now.isoformat(),
            "priority": "high"
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Escalation sent", "meeting_id": meeting_id}


# ═══════════════════════════════════════════════════════════════════
# EXPENSE COMPLIANCE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@router.get("/expense-compliance")
async def get_expense_compliance(current_user: User = Depends(get_current_user)):
    """
    Get expense compliance metrics:
    - Receipt compliance rate
    - Meeting linkage rate
    - Approval turnaround
    - Anomalies
    """
    db = get_db()
    
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(500)
    
    total = len(expenses)
    if total == 0:
        return {"message": "No expense data"}
    
    # Receipt compliance
    with_receipt = 0
    needs_receipt = 0
    for e in expenses:
        amount = e.get("total_amount") or e.get("amount", 0)
        receipts = e.get("receipts") or e.get("attachments") or []
        has_receipt = bool(receipts)
        
        if amount >= EXPENSE_RECEIPT_THRESHOLD:
            needs_receipt += 1
            if has_receipt:
                with_receipt += 1
    
    receipt_compliance = (with_receipt / needs_receipt * 100) if needs_receipt > 0 else 100
    
    # Travel-meeting linkage
    travel_keywords = ['travel', 'conveyance', 'transport', 'cab', 'fuel']
    travel_expenses = [e for e in expenses if any(kw in (e.get("category") or "").lower() for kw in travel_keywords)]
    travel_with_meeting = len([e for e in travel_expenses if e.get("meeting_id")])
    travel_linkage = (travel_with_meeting / len(travel_expenses) * 100) if travel_expenses else 100
    
    # Status breakdown
    status_counts = {}
    for e in expenses:
        status = e.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Pending age analysis
    pending_expenses = [e for e in expenses if e.get("status") == "pending"]
    old_pending = 0
    for e in pending_expenses:
        created = e.get("created_at")
        if created:
            try:
                created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - created_dt).days > 7:
                    old_pending += 1
            except (ValueError, TypeError, AttributeError):
                pass
    
    # Anomaly detection
    amounts = [e.get("total_amount") or e.get("amount", 0) for e in expenses]
    if len(amounts) >= 3:
        avg = sum(amounts) / len(amounts)
        std = (sum((x - avg) ** 2 for x in amounts) / len(amounts)) ** 0.5
        anomalies = [
            {
                "id": e.get("id"),
                "amount": e.get("total_amount") or e.get("amount", 0),
                "category": e.get("category"),
                "employee_name": e.get("employee_name"),
                "deviation_sigma": round(abs((e.get("total_amount") or e.get("amount", 0)) - avg) / std, 1) if std > 0 else 0
            }
            for e in expenses
            if std > 0 and abs((e.get("total_amount") or e.get("amount", 0)) - avg) > 2 * std
        ]
    else:
        anomalies = []
    
    return {
        "total_expenses": total,
        "compliance": {
            "receipt_compliance_rate": round(receipt_compliance, 1),
            "expenses_needing_receipt": needs_receipt,
            "expenses_with_receipt": with_receipt,
            "travel_meeting_linkage_rate": round(travel_linkage, 1),
            "travel_expenses": len(travel_expenses),
            "travel_with_meeting": travel_with_meeting
        },
        "status_breakdown": status_counts,
        "pending_analysis": {
            "total_pending": len(pending_expenses),
            "pending_over_7_days": old_pending
        },
        "anomalies": anomalies[:10]
    }


# ═══════════════════════════════════════════════════════════════════
# OPERATIONAL DISCIPLINE METRICS
# ═══════════════════════════════════════════════════════════════════

@router.get("/operational-discipline")
async def get_operational_discipline(current_user: User = Depends(get_current_user)):
    """
    Get operational discipline metrics across the organization.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Attendance metrics
    today = now.strftime("%Y-%m-%d")
    attendance_today = await db.attendance.count_documents({"date": today})
    late_checkins = await db.attendance.count_documents({"date": today, "is_late": True})
    
    # Meeting discipline
    meetings = await db.meetings.find(
        {"status": {"$nin": ["cancelled", "CANCELLED"]}},
        {"_id": 0, "meeting_date": 1, "mom_generated": 1, "is_delivered": 1, "mom_sent_to_client": 1}
    ).to_list(500)
    
    past_meetings = []
    for m in meetings:
        md = m.get("meeting_date")
        if md:
            try:
                if isinstance(md, str):
                    m_dt = datetime.fromisoformat(md.replace("Z", "+00:00"))
                else:
                    m_dt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
                if m_dt < now:
                    past_meetings.append(m)
            except Exception:
                pass
    
    mom_recorded = len([m for m in past_meetings if m.get("mom_generated")])
    delivered = len([m for m in past_meetings if m.get("is_delivered")])
    mom_sent = len([m for m in past_meetings if m.get("mom_sent_to_client")])
    
    # Task/action item completion
    action_items = await db.meetings.aggregate([
        {"$unwind": {"path": "$action_items", "preserveNullAndEmptyArrays": False}},
        {"$group": {
            "_id": "$action_items.status",
            "count": {"$sum": 1}
        }}
    ]).to_list(10)
    
    task_status = {item["_id"]: item["count"] for item in action_items}
    
    # Pending approvals
    pending_approvals = await db.expenses.count_documents({"status": "pending"})
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    
    return {
        "date": today,
        "attendance": {
            "records_today": attendance_today,
            "late_checkins": late_checkins
        },
        "meetings": {
            "total_past": len(past_meetings),
            "mom_recorded": mom_recorded,
            "mom_rate": round(mom_recorded / len(past_meetings) * 100, 1) if past_meetings else 0,
            "delivered": delivered,
            "delivery_rate": round(delivered / len(past_meetings) * 100, 1) if past_meetings else 0,
            "mom_sent_to_client": mom_sent,
            "client_comm_rate": round(mom_sent / mom_recorded * 100, 1) if mom_recorded > 0 else 0
        },
        "tasks": task_status,
        "pending_approvals": {
            "expenses": pending_approvals,
            "leaves": pending_leaves
        }
    }


# ═══════════════════════════════════════════════════════════════════
# BUSINESS HEALTH SCORE
# ═══════════════════════════════════════════════════════════════════

@router.get("/health-score")
async def get_business_health_score(current_user: User = Depends(get_current_user)):
    """
    Calculate overall business health score.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    scores = {}
    
    # 1. Sales Efficiency (MOM completion, delivery rate)
    meetings = await db.meetings.find(
        {"status": {"$nin": ["cancelled", "CANCELLED"]}},
        {"_id": 0}
    ).to_list(500)
    
    past_meetings = []
    for m in meetings:
        md = m.get("meeting_date")
        if md:
            try:
                if isinstance(md, str):
                    m_dt = datetime.fromisoformat(md.replace("Z", "+00:00"))
                else:
                    m_dt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
                if m_dt < now:
                    past_meetings.append(m)
            except Exception:
                pass
    
    if past_meetings:
        mom_rate = len([m for m in past_meetings if m.get("mom_generated")]) / len(past_meetings)
        delivery_rate = len([m for m in past_meetings if m.get("is_delivered")]) / len(past_meetings)
        # Score is weighted average: 50% MOM rate + 50% delivery rate, scaled to 100
        scores["sales_efficiency"] = round((mom_rate * 0.5 + delivery_rate * 0.5) * 100, 1)
    else:
        scores["sales_efficiency"] = 50  # Neutral
    
    # 2. Cost Control (receipt compliance, approval turnaround)
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(500)
    if expenses:
        travel_kw = ['travel', 'conveyance', 'transport']
        travel_exp = [e for e in expenses if any(kw in (e.get("category") or "").lower() for kw in travel_kw)]
        linked = len([e for e in travel_exp if e.get("meeting_id")])
        linkage_rate = linked / len(travel_exp) if travel_exp else 1
        
        with_receipt = len([e for e in expenses if e.get("receipts") or e.get("attachments")])
        receipt_rate = with_receipt / len(expenses)
        
        # Score is weighted average: 50% linkage + 50% receipt, scaled to 100
        scores["cost_control"] = round((linkage_rate * 0.5 + receipt_rate * 0.5) * 100, 1)
    else:
        scores["cost_control"] = 70
    
    # 3. Team Discipline
    scores["team_discipline"] = 75  # Default based on attendance
    
    # 4. Data Reliability
    projects = await db.projects.find({}, {"_id": 0, "project_manager": 1, "value": 1}).to_list(100)
    if projects:
        has_pm = len([p for p in projects if p.get("project_manager")])
        has_value = len([p for p in projects if p.get("value")])
        scores["data_reliability"] = round(((has_pm + has_value) / (len(projects) * 2)) * 100, 1)
    else:
        scores["data_reliability"] = 80
    
    # Overall score
    weights = {
        "sales_efficiency": 0.30,
        "cost_control": 0.25,
        "team_discipline": 0.20,
        "data_reliability": 0.25
    }
    
    overall = sum(scores.get(k, 50) * w for k, w in weights.items())
    
    return {
        "scores": scores,
        "overall": round(overall, 1),
        "status": "healthy" if overall >= 70 else "attention_needed" if overall >= 50 else "critical",
        "calculated_at": now.isoformat()
    }


# ═══════════════════════════════════════════════════════════════════
# LEAKAGE PREVENTION ALERTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/leakage-alerts")
async def get_leakage_alerts(current_user: User = Depends(get_current_user)):
    """
    Identify potential revenue and cost leakage areas.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    alerts = []
    
    # Revenue leakage: Delivered meetings not invoiced
    meetings = await db.meetings.find(
        {"is_delivered": True},
        {"_id": 0, "id": 1, "title": 1, "project_id": 1, "client_name": 1}
    ).to_list(100)
    
    # Check if these have related invoices
    delivered_project_ids = set(m.get("project_id") for m in meetings if m.get("project_id"))
    invoiced_projects = set()
    
    invoices = await db.invoices.find(
        {"project_id": {"$in": list(delivered_project_ids)}},
        {"_id": 0, "project_id": 1}
    ).to_list(500)
    invoiced_projects = set(i.get("project_id") for i in invoices)
    
    uninvoiced = delivered_project_ids - invoiced_projects
    if uninvoiced:
        alerts.append({
            "type": "revenue_leakage",
            "severity": "high",
            "title": "Uninvoiced Delivered Work",
            "message": f"{len(uninvoiced)} project(s) have delivered meetings but no invoices",
            "count": len(uninvoiced),
            "action": "Review and generate invoices"
        })
    
    # Cost leakage: Travel without meeting
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(500)
    travel_kw = ['travel', 'conveyance', 'transport', 'cab']
    unlinked_travel = [
        e for e in expenses 
        if any(kw in (e.get("category") or "").lower() for kw in travel_kw)
        and not e.get("meeting_id")
    ]
    
    if unlinked_travel:
        total_unlinked = sum(e.get("total_amount") or e.get("amount", 0) for e in unlinked_travel)
        alerts.append({
            "type": "cost_leakage",
            "severity": "medium",
            "title": "Unlinked Travel Expenses",
            "message": f"{len(unlinked_travel)} travel expense(s) worth ₹{total_unlinked:,.0f} without meeting linkage",
            "count": len(unlinked_travel),
            "amount": total_unlinked,
            "action": "Review and link to meetings or mark as unjustified"
        })
    
    # Communication gap: MOM not sent
    mom_not_sent = await db.meetings.count_documents({
        "mom_generated": True,
        "mom_sent_to_client": {"$ne": True}
    })
    
    if mom_not_sent > 0:
        alerts.append({
            "type": "communication_gap",
            "severity": "medium",
            "title": "MOMs Not Sent to Client",
            "message": f"{mom_not_sent} meeting(s) have MOM recorded but not shared with client",
            "count": mom_not_sent,
            "action": "Send pending MOMs to clients"
        })
    
    # Stale leads
    stale_threshold = now - timedelta(days=STALE_LEAD_DAYS)
    stale_leads = await db.leads.count_documents({
        "status": {"$nin": ["converted", "won", "lost", "closed_won", "closed_lost"]},
        "updated_at": {"$lt": stale_threshold.isoformat()}
    })
    
    if stale_leads > 0:
        alerts.append({
            "type": "opportunity_loss",
            "severity": "high",
            "title": "Stale Leads",
            "message": f"{stale_leads} lead(s) have no activity in {STALE_LEAD_DAYS}+ days",
            "count": stale_leads,
            "action": "Follow up or close stale leads"
        })
    
    return {
        "total_alerts": len(alerts),
        "critical": len([a for a in alerts if a["severity"] == "high"]),
        "medium": len([a for a in alerts if a["severity"] == "medium"]),
        "alerts": alerts
    }
