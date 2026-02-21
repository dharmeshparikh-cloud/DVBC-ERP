"""
Reports Module - Generates analytical reports with Excel and PDF export
Role-based access control: Admin sees all, others see role-specific reports
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from io import BytesIO
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

router = APIRouter()

# Report definitions with role access
REPORT_DEFINITIONS = {
    # Lead Analytics
    "lead_summary": {
        "name": "Lead Summary Report",
        "description": "Overview of all leads with status and source breakdown",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    "lead_conversion_funnel": {
        "name": "Lead Conversion Funnel",
        "description": "Lead progression from new to converted",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    "lead_source_analysis": {
        "name": "Lead Source Analysis",
        "description": "Lead distribution by source channel",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    
    # Client Analytics
    "client_overview": {
        "name": "Client Overview Report",
        "description": "All clients with industry, location, and revenue",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager", "project_manager"]
    },
    "client_revenue_analysis": {
        "name": "Client Revenue Analysis",
        "description": "Revenue breakdown by client and time period",
        "category": "Finance",
        "roles": ["admin", "manager", "sales_manager"]
    },
    "client_industry_breakdown": {
        "name": "Client Industry Breakdown",
        "description": "Client distribution across industries",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    
    # Sales Pipeline
    "sales_pipeline_status": {
        "name": "Sales Pipeline Status",
        "description": "Pricing plans, quotations, and agreements status",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    "quotation_analysis": {
        "name": "Quotation Analysis",
        "description": "Quotation to agreement conversion metrics",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager"]
    },
    "agreement_status": {
        "name": "Agreement Status Report",
        "description": "All agreements with approval status",
        "category": "Sales",
        "roles": ["admin", "manager", "executive", "sales_manager", "project_manager"]
    },
    
    # HR Analytics
    "employee_directory": {
        "name": "Employee Directory",
        "description": "Complete employee list with department and designation",
        "category": "HR",
        "roles": ["admin", "hr_manager", "hr_executive", "manager"]
    },
    "employee_department_analysis": {
        "name": "Department Analysis",
        "description": "Employee distribution by department",
        "category": "HR",
        "roles": ["admin", "hr_manager", "manager"]
    },
    "leave_utilization": {
        "name": "Leave Utilization Report",
        "description": "Leave balance and usage by employee",
        "category": "HR",
        "roles": ["admin", "hr_manager"]
    },
    "expense_summary": {
        "name": "Expense Summary Report",
        "description": "All expenses with status and category breakdown",
        "category": "Finance",
        "roles": ["admin", "hr_manager", "manager"]
    },
    "expense_by_category": {
        "name": "Expense Category Analysis",
        "description": "Expense breakdown by category",
        "category": "Finance",
        "roles": ["admin", "hr_manager", "manager"]
    },
    
    # SOW & Project Analytics
    "sow_status_report": {
        "name": "SOW Status Report",
        "description": "SOW items by status and category",
        "category": "Operations",
        "roles": ["admin", "manager", "project_manager", "principal_consultant"]
    },
    "project_summary": {
        "name": "Project Summary",
        "description": "All projects with status and team allocation",
        "category": "Operations",
        "roles": ["admin", "manager", "project_manager"]
    },
    "consultant_allocation": {
        "name": "Consultant Allocation Report",
        "description": "Consultant assignments across projects",
        "category": "Operations",
        "roles": ["admin", "manager", "project_manager"]
    },
    
    # Approval Analytics
    "approval_turnaround": {
        "name": "Approval Turnaround Report",
        "description": "Average approval time by type",
        "category": "Operations",
        "roles": ["admin", "manager", "hr_manager"]
    },
    "pending_approvals": {
        "name": "Pending Approvals Summary",
        "description": "All pending approvals across modules",
        "category": "Operations",
        "roles": ["admin", "manager", "hr_manager"]
    },
}


class ReportRequest(BaseModel):
    report_id: str
    format: str = "excel"  # excel or pdf
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None


def get_report_data_functions():
    """Returns mapping of report_id to data generation function"""
    return {
        "lead_summary": generate_lead_summary,
        "lead_conversion_funnel": generate_lead_conversion_funnel,
        "lead_source_analysis": generate_lead_source_analysis,
        "client_overview": generate_client_overview,
        "client_revenue_analysis": generate_client_revenue_analysis,
        "client_industry_breakdown": generate_client_industry_breakdown,
        "sales_pipeline_status": generate_sales_pipeline_status,
        "quotation_analysis": generate_quotation_analysis,
        "agreement_status": generate_agreement_status,
        "employee_directory": generate_employee_directory,
        "employee_department_analysis": generate_employee_department_analysis,
        "leave_utilization": generate_leave_utilization,
        "expense_summary": generate_expense_summary,
        "expense_by_category": generate_expense_by_category,
        "sow_status_report": generate_sow_status_report,
        "project_summary": generate_project_summary,
        "consultant_allocation": generate_consultant_allocation,
        "approval_turnaround": generate_approval_turnaround,
        "pending_approvals": generate_pending_approvals,
    }


# ==================== REPORT DATA GENERATORS ====================

async def generate_lead_summary(db, filters=None):
    """Generate lead summary data"""
    leads = await db.leads.find({}, {"_id": 0}).to_list(1000)
    
    # Summary stats
    total = len(leads)
    by_status = {}
    by_source = {}
    
    for lead in leads:
        status = lead.get('status', 'new')
        source = lead.get('source', 'Unknown')
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
    
    # Detailed data
    rows = []
    for lead in leads:
        rows.append({
            "Company": lead.get('company', ''),
            "Contact": f"{lead.get('first_name', '')} {lead.get('last_name', '')}",
            "Email": lead.get('email', ''),
            "Phone": lead.get('phone', ''),
            "Status": lead.get('status', 'new'),
            "Source": lead.get('source', ''),
            "Score": lead.get('score', 0),
            "Created": lead.get('created_at', '')[:10] if lead.get('created_at') else ''
        })
    
    return {
        "title": "Lead Summary Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "Total Leads": total,
            "By Status": by_status,
            "By Source": by_source
        },
        "columns": ["Company", "Contact", "Email", "Phone", "Status", "Source", "Score", "Created"],
        "rows": rows
    }


async def generate_lead_conversion_funnel(db, filters=None):
    """Generate lead conversion funnel data"""
    leads = await db.leads.find({}, {"_id": 0}).to_list(1000)
    
    funnel = {
        "New": 0,
        "Contacted": 0,
        "Qualified": 0,
        "Proposal": 0,
        "Negotiation": 0,
        "Converted": 0,
        "Lost": 0
    }
    
    for lead in leads:
        status = lead.get('status', 'new').lower()
        if status in funnel:
            funnel[status.capitalize()] += 1
        elif status == 'new':
            funnel['New'] += 1
    
    rows = [{"Stage": k, "Count": v, "Percentage": f"{(v/len(leads)*100):.1f}%" if leads else "0%"} for k, v in funnel.items()]
    
    return {
        "title": "Lead Conversion Funnel",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Leads": len(leads), "Conversion Rate": f"{(funnel.get('Converted', 0)/len(leads)*100):.1f}%" if leads else "0%"},
        "columns": ["Stage", "Count", "Percentage"],
        "rows": rows
    }


async def generate_lead_source_analysis(db, filters=None):
    """Generate lead source analysis"""
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}, "avg_score": {"$avg": "$score"}}},
        {"$sort": {"count": -1}}
    ]
    results = await db.leads.aggregate(pipeline).to_list(100)
    
    rows = [{"Source": r['_id'] or 'Unknown', "Lead Count": r['count'], "Avg Score": f"{r['avg_score']:.1f}" if r['avg_score'] else "N/A"} for r in results]
    
    return {
        "title": "Lead Source Analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Sources": len(results)},
        "columns": ["Source", "Lead Count", "Avg Score"],
        "rows": rows
    }


async def generate_client_overview(db, filters=None):
    """Generate client overview"""
    clients = await db.clients.find({"is_active": True}, {"_id": 0}).to_list(500)
    
    rows = []
    for c in clients:
        total_revenue = sum(r.get('amount', 0) for r in c.get('revenue_history', []))
        rows.append({
            "Company": c.get('company_name', ''),
            "Industry": c.get('industry', ''),
            "Location": f"{c.get('city', '')}, {c.get('state', '')}",
            "Contacts": len(c.get('contacts', [])),
            "Sales Person": c.get('sales_person_name', ''),
            "Total Revenue": f"₹{total_revenue:,.0f}",
            "Start Date": c.get('business_start_date', '')[:10] if c.get('business_start_date') else ''
        })
    
    return {
        "title": "Client Overview Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Clients": len(clients)},
        "columns": ["Company", "Industry", "Location", "Contacts", "Sales Person", "Total Revenue", "Start Date"],
        "rows": rows
    }


async def generate_client_revenue_analysis(db, filters=None):
    """Generate client revenue analysis"""
    clients = await db.clients.find({"is_active": True}, {"_id": 0}).to_list(500)
    
    rows = []
    total_revenue = 0
    for c in clients:
        client_revenue = sum(r.get('amount', 0) for r in c.get('revenue_history', []))
        total_revenue += client_revenue
        if client_revenue > 0:
            rows.append({
                "Client": c.get('company_name', ''),
                "Industry": c.get('industry', ''),
                "Revenue": client_revenue,
                "Revenue (Formatted)": f"₹{client_revenue:,.0f}",
                "Records": len(c.get('revenue_history', []))
            })
    
    rows.sort(key=lambda x: x['Revenue'], reverse=True)
    for r in rows:
        r['Percentage'] = f"{(r['Revenue']/total_revenue*100):.1f}%" if total_revenue else "0%"
        del r['Revenue']
    
    return {
        "title": "Client Revenue Analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Revenue": f"₹{total_revenue:,.0f}", "Clients with Revenue": len(rows)},
        "columns": ["Client", "Industry", "Revenue (Formatted)", "Percentage", "Records"],
        "rows": rows
    }


async def generate_client_industry_breakdown(db, filters=None):
    """Generate client industry breakdown"""
    pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$industry", "count": {"$sum": 1}}}
    ]
    results = await db.clients.aggregate(pipeline).to_list(100)
    
    total = sum(r['count'] for r in results)
    rows = [{"Industry": r['_id'] or 'Unspecified', "Client Count": r['count'], "Percentage": f"{(r['count']/total*100):.1f}%" if total else "0%"} for r in results]
    rows.sort(key=lambda x: x['Client Count'], reverse=True)
    
    return {
        "title": "Client Industry Breakdown",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Industries": len(results), "Total Clients": total},
        "columns": ["Industry", "Client Count", "Percentage"],
        "rows": rows
    }


async def generate_sales_pipeline_status(db, filters=None):
    """Generate sales pipeline status"""
    pricing_plans = await db.pricing_plans.count_documents({})
    quotations = await db.quotations.count_documents({})
    agreements = await db.agreements.count_documents({})
    
    # Agreement status breakdown
    agreement_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    agreement_status = await db.agreements.aggregate(agreement_pipeline).to_list(20)
    
    rows = [
        {"Stage": "Pricing Plans", "Count": pricing_plans, "Status": "Active"},
        {"Stage": "Quotations", "Count": quotations, "Status": "Created"},
        {"Stage": "Agreements", "Count": agreements, "Status": "Total"},
    ]
    
    for s in agreement_status:
        rows.append({"Stage": f"  - {s['_id'] or 'Draft'}", "Count": s['count'], "Status": ""})
    
    return {
        "title": "Sales Pipeline Status",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Pricing Plans": pricing_plans, "Quotations": quotations, "Agreements": agreements},
        "columns": ["Stage", "Count", "Status"],
        "rows": rows
    }


async def generate_quotation_analysis(db, filters=None):
    """Generate quotation analysis"""
    quotations = await db.quotations.find({}, {"_id": 0}).to_list(500)
    
    rows = []
    total_value = 0
    for q in quotations:
        value = q.get('total_amount', 0)
        total_value += value
        rows.append({
            "Quotation ID": q.get('id', '')[:8],
            "Client": q.get('client_name', q.get('lead_name', '')),
            "Status": q.get('status', 'draft'),
            "Amount": f"₹{value:,.0f}",
            "Created": q.get('created_at', '')[:10] if q.get('created_at') else ''
        })
    
    return {
        "title": "Quotation Analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Quotations": len(quotations), "Total Value": f"₹{total_value:,.0f}"},
        "columns": ["Quotation ID", "Client", "Status", "Amount", "Created"],
        "rows": rows
    }


async def generate_agreement_status(db, filters=None):
    """Generate agreement status report"""
    agreements = await db.agreements.find({}, {"_id": 0}).to_list(500)
    
    rows = []
    for a in agreements:
        rows.append({
            "Agreement ID": a.get('id', '')[:8],
            "Client": a.get('client_name', ''),
            "Status": a.get('status', 'draft'),
            "Start Date": a.get('start_date', '')[:10] if a.get('start_date') else '',
            "Duration": f"{a.get('duration_months', 0)} months",
            "Created": a.get('created_at', '')[:10] if a.get('created_at') else ''
        })
    
    return {
        "title": "Agreement Status Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Agreements": len(agreements)},
        "columns": ["Agreement ID", "Client", "Status", "Start Date", "Duration", "Created"],
        "rows": rows
    }


async def generate_employee_directory(db, filters=None):
    """Generate employee directory"""
    employees = await db.employees.find({}, {"_id": 0}).to_list(500)
    
    rows = []
    for e in employees:
        rows.append({
            "Employee ID": e.get('employee_id', ''),
            "Name": f"{e.get('first_name', '')} {e.get('last_name', '')}",
            "Email": e.get('email', ''),
            "Department": e.get('department', ''),
            "Designation": e.get('designation', ''),
            "Type": e.get('employment_type', ''),
            "Join Date": e.get('join_date', '')[:10] if e.get('join_date') else '',
            "Has System Access": "Yes" if e.get('user_id') else "No"
        })
    
    return {
        "title": "Employee Directory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Employees": len(employees)},
        "columns": ["Employee ID", "Name", "Email", "Department", "Designation", "Type", "Join Date", "Has System Access"],
        "rows": rows
    }


async def generate_employee_department_analysis(db, filters=None):
    """Generate department analysis"""
    pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    results = await db.employees.aggregate(pipeline).to_list(100)
    
    total = sum(r['count'] for r in results)
    rows = [{"Department": r['_id'] or 'Unassigned', "Employee Count": r['count'], "Percentage": f"{(r['count']/total*100):.1f}%" if total else "0%"} for r in results]
    
    return {
        "title": "Department Analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Departments": len(results), "Total Employees": total},
        "columns": ["Department", "Employee Count", "Percentage"],
        "rows": rows
    }


async def generate_leave_utilization(db, filters=None):
    """Generate leave utilization report"""
    employees = await db.employees.find({}, {"_id": 0}).to_list(500)
    
    rows = []
    for e in employees:
        leave = e.get('leave_balance', {})
        rows.append({
            "Employee": f"{e.get('first_name', '')} {e.get('last_name', '')}",
            "Department": e.get('department', ''),
            "Casual (Bal/Used)": f"{leave.get('casual', 12)}/{leave.get('casual_used', 0)}",
            "Sick (Bal/Used)": f"{leave.get('sick', 6)}/{leave.get('sick_used', 0)}",
            "Earned (Bal/Used)": f"{leave.get('earned', 15)}/{leave.get('earned_used', 0)}",
            "Total Used": leave.get('casual_used', 0) + leave.get('sick_used', 0) + leave.get('earned_used', 0)
        })
    
    return {
        "title": "Leave Utilization Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Employees": len(employees)},
        "columns": ["Employee", "Department", "Casual (Bal/Used)", "Sick (Bal/Used)", "Earned (Bal/Used)", "Total Used"],
        "rows": rows
    }


async def generate_expense_summary(db, filters=None):
    """Generate expense summary"""
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(1000)
    
    total_amount = sum(e.get('total_amount', 0) for e in expenses)
    by_status = {}
    
    rows = []
    for e in expenses:
        status = e.get('status', 'draft')
        by_status[status] = by_status.get(status, 0) + e.get('total_amount', 0)
        
        rows.append({
            "Date": e.get('created_at', '')[:10] if e.get('created_at') else '',
            "Employee": e.get('employee_name', ''),
            "Client/Project": e.get('client_name') or e.get('project_name') or ('Office' if e.get('is_office_expense') else ''),
            "Items": len(e.get('line_items', [])),
            "Amount": f"₹{e.get('total_amount', 0):,.0f}",
            "Status": status
        })
    
    return {
        "title": "Expense Summary Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Expenses": len(expenses), "Total Amount": f"₹{total_amount:,.0f}", "By Status": {k: f"₹{v:,.0f}" for k, v in by_status.items()}},
        "columns": ["Date", "Employee", "Client/Project", "Items", "Amount", "Status"],
        "rows": rows
    }


async def generate_expense_by_category(db, filters=None):
    """Generate expense by category"""
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(1000)
    
    by_category = {}
    for e in expenses:
        for item in e.get('line_items', []):
            cat = item.get('category', 'other')
            by_category[cat] = by_category.get(cat, 0) + item.get('amount', 0)
    
    total = sum(by_category.values())
    rows = [{"Category": k.replace('_', ' ').title(), "Amount": f"₹{v:,.0f}", "Percentage": f"{(v/total*100):.1f}%" if total else "0%"} for k, v in by_category.items()]
    rows.sort(key=lambda x: float(x['Percentage'].replace('%', '')), reverse=True)
    
    return {
        "title": "Expense Category Analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Categories": len(by_category), "Total Amount": f"₹{total:,.0f}"},
        "columns": ["Category", "Amount", "Percentage"],
        "rows": rows
    }


async def generate_sow_status_report(db, filters=None):
    """Generate SOW status report"""
    sows = await db.sows.find({}, {"_id": 0}).to_list(500)
    
    by_status = {}
    by_category = {}
    total_items = 0
    
    for sow in sows:
        for item in sow.get('items', []):
            total_items += 1
            status = item.get('status', 'draft')
            category = item.get('category', 'other')
            by_status[status] = by_status.get(status, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
    
    rows = [{"Status": k.replace('_', ' ').title(), "Count": v, "Percentage": f"{(v/total_items*100):.1f}%" if total_items else "0%"} for k, v in by_status.items()]
    
    return {
        "title": "SOW Status Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total SOWs": len(sows), "Total Items": total_items, "By Category": by_category},
        "columns": ["Status", "Count", "Percentage"],
        "rows": rows
    }


async def generate_project_summary(db, filters=None):
    """Generate project summary"""
    projects = await db.projects.find({}, {"_id": 0}).to_list(500)
    
    rows = []
    for p in projects:
        rows.append({
            "Project": p.get('name', ''),
            "Client": p.get('client_name', ''),
            "Status": p.get('status', 'active'),
            "Start Date": p.get('start_date', '')[:10] if p.get('start_date') else '',
            "Team Size": len(p.get('team', [])),
            "Progress": f"{p.get('progress', 0)}%"
        })
    
    return {
        "title": "Project Summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Projects": len(projects)},
        "columns": ["Project", "Client", "Status", "Start Date", "Team Size", "Progress"],
        "rows": rows
    }


async def generate_consultant_allocation(db, filters=None):
    """Generate consultant allocation report"""
    # Get consultants from employees with consultant roles
    consultants = await db.employees.find(
        {"designation": {"$regex": "consultant", "$options": "i"}},
        {"_id": 0}
    ).to_list(200)
    
    # Get SOW assignments
    sows = await db.sows.find({}, {"_id": 0}).to_list(500)
    
    consultant_items = {}
    for sow in sows:
        for item in sow.get('items', []):
            assigned = item.get('assigned_consultant')
            if assigned:
                if assigned not in consultant_items:
                    consultant_items[assigned] = []
                consultant_items[assigned].append(item.get('title', 'Untitled'))
    
    rows = []
    for c in consultants:
        name = f"{c.get('first_name', '')} {c.get('last_name', '')}"
        assignments = consultant_items.get(c.get('id'), [])
        rows.append({
            "Consultant": name,
            "Department": c.get('department', ''),
            "Designation": c.get('designation', ''),
            "Assignments": len(assignments),
            "Items": ", ".join(assignments[:3]) + ("..." if len(assignments) > 3 else "") if assignments else "None"
        })
    
    return {
        "title": "Consultant Allocation Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Consultants": len(consultants)},
        "columns": ["Consultant", "Department", "Designation", "Assignments", "Items"],
        "rows": rows
    }


async def generate_approval_turnaround(db, filters=None):
    """Generate approval turnaround report"""
    approvals = await db.approval_requests.find({}, {"_id": 0}).to_list(1000)
    
    by_type = {}
    for a in approvals:
        atype = a.get('approval_type', 'unknown')
        if atype not in by_type:
            by_type[atype] = {"total": 0, "completed": 0, "pending": 0, "total_days": 0}
        
        by_type[atype]['total'] += 1
        if a.get('overall_status') == 'approved':
            by_type[atype]['completed'] += 1
            # Calculate turnaround if we have dates
            created = a.get('created_at')
            updated = a.get('updated_at')
            if created and updated:
                try:
                    c_date = datetime.fromisoformat(created.replace('Z', '+00:00')) if isinstance(created, str) else created
                    u_date = datetime.fromisoformat(updated.replace('Z', '+00:00')) if isinstance(updated, str) else updated
                    by_type[atype]['total_days'] += (u_date - c_date).days
                except:
                    pass
        elif a.get('overall_status') == 'pending':
            by_type[atype]['pending'] += 1
    
    rows = []
    for atype, data in by_type.items():
        avg_days = data['total_days'] / data['completed'] if data['completed'] > 0 else 0
        rows.append({
            "Approval Type": atype.replace('_', ' ').title(),
            "Total": data['total'],
            "Completed": data['completed'],
            "Pending": data['pending'],
            "Avg Turnaround": f"{avg_days:.1f} days" if avg_days else "N/A"
        })
    
    return {
        "title": "Approval Turnaround Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Approvals": sum(d['total'] for d in by_type.values())},
        "columns": ["Approval Type", "Total", "Completed", "Pending", "Avg Turnaround"],
        "rows": rows
    }


async def generate_pending_approvals(db, filters=None):
    """Generate pending approvals summary"""
    approvals = await db.approval_requests.find({"overall_status": "pending"}, {"_id": 0}).to_list(500)
    
    rows = []
    for a in approvals:
        rows.append({
            "Type": a.get('approval_type', '').replace('_', ' ').title(),
            "Reference": a.get('reference_title', ''),
            "Requester": a.get('requester_name', ''),
            "Current Level": f"{a.get('current_level', 1)}/{a.get('max_level', 1)}",
            "Created": a.get('created_at', '')[:10] if a.get('created_at') else '',
            "Days Pending": ""
        })
        
        # Calculate days pending
        if a.get('created_at'):
            try:
                created = datetime.fromisoformat(a['created_at'].replace('Z', '+00:00'))
                days = (datetime.now(timezone.utc) - created).days
                rows[-1]["Days Pending"] = f"{days} days"
            except:
                pass
    
    return {
        "title": "Pending Approvals Summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"Total Pending": len(approvals)},
        "columns": ["Type", "Reference", "Requester", "Current Level", "Created", "Days Pending"],
        "rows": rows
    }


# ==================== EXPORT FUNCTIONS ====================

def generate_excel(report_data: dict) -> bytes:
    """Generate Excel file from report data"""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Report')
    
    # Formats
    title_format = workbook.add_format({
        'bold': True, 'font_size': 16, 'font_color': '#1a1a1a',
        'bottom': 2, 'bottom_color': '#e5a522'
    })
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#1a1a1a', 'font_color': 'white',
        'border': 1, 'text_wrap': True, 'valign': 'vcenter'
    })
    cell_format = workbook.add_format({
        'border': 1, 'valign': 'vcenter'
    })
    summary_key_format = workbook.add_format({
        'bold': True, 'font_color': '#666666'
    })
    summary_value_format = workbook.add_format({
        'font_color': '#1a1a1a'
    })
    
    # Title
    worksheet.write(0, 0, report_data.get('title', 'Report'), title_format)
    worksheet.write(1, 0, f"Generated: {report_data.get('generated_at', '')[:19]}", summary_key_format)
    
    # Summary section
    row = 3
    summary = report_data.get('summary', {})
    for key, value in summary.items():
        if isinstance(value, dict):
            worksheet.write(row, 0, key, summary_key_format)
            row += 1
            for k, v in value.items():
                worksheet.write(row, 0, f"  {k}", summary_key_format)
                worksheet.write(row, 1, str(v), summary_value_format)
                row += 1
        else:
            worksheet.write(row, 0, key, summary_key_format)
            worksheet.write(row, 1, str(value), summary_value_format)
            row += 1
    
    row += 2
    
    # Headers
    columns = report_data.get('columns', [])
    for col, header in enumerate(columns):
        worksheet.write(row, col, header, header_format)
        worksheet.set_column(col, col, 18)  # Set column width
    
    row += 1
    
    # Data rows
    for data_row in report_data.get('rows', []):
        for col, header in enumerate(columns):
            value = data_row.get(header, '')
            worksheet.write(row, col, str(value), cell_format)
        row += 1
    
    workbook.close()
    output.seek(0)
    return output.getvalue()


def generate_pdf(report_data: dict) -> bytes:
    """Generate PDF file from report data"""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20
    )
    
    # Title
    elements.append(Paragraph(report_data.get('title', 'Report'), title_style))
    elements.append(Paragraph(f"Generated: {report_data.get('generated_at', '')[:19]}", subtitle_style))
    
    # Summary
    summary = report_data.get('summary', {})
    summary_text = " | ".join([f"<b>{k}:</b> {v}" for k, v in summary.items() if not isinstance(v, dict)])
    if summary_text:
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 20))
    
    # Table
    columns = report_data.get('columns', [])
    rows = report_data.get('rows', [])
    
    if columns and rows:
        table_data = [columns]
        for row in rows:
            table_data.append([str(row.get(col, ''))[:40] for col in columns])
        
        # Calculate column widths
        available_width = landscape(A4)[0] - inch
        col_width = available_width / len(columns)
        
        table = Table(table_data, colWidths=[col_width] * len(columns))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
    
    doc.build(elements)
    output.seek(0)
    return output.getvalue()
