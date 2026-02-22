"""
Comprehensive E2E Test Data Setup for NETRA ERP
Creates test data for all 50 features
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from passlib.context import CryptContext
import uuid
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to MongoDB
client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = client["test_database"]


def generate_id():
    return str(uuid.uuid4())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def create_test_users():
    """Create test users for different roles"""
    users = [
        # Admin
        {"employee_id": "ADMIN001", "email": "admin@dvbc.com", "full_name": "System Admin", "role": "admin", "department": "Admin"},
        # HR
        {"employee_id": "HR001", "email": "hr.manager@dvbc.com", "full_name": "HR Manager", "role": "hr_manager", "department": "HR"},
        {"employee_id": "HRE001", "email": "hr.exec@dvbc.com", "full_name": "HR Executive", "role": "hr_executive", "department": "HR"},
        # Sales
        {"employee_id": "SM001", "email": "sales.manager@dvbc.com", "full_name": "Sales Manager", "role": "sales_manager", "department": "Sales"},
        {"employee_id": "SE001", "email": "sales.exec1@dvbc.com", "full_name": "Rahul Kumar", "role": "sales_executive", "department": "Sales", "reporting_manager_id": "SM001"},
        {"employee_id": "SE002", "email": "sales.exec2@dvbc.com", "full_name": "Priya Sharma", "role": "sales_executive", "department": "Sales", "reporting_manager_id": "SM001"},
        # Consulting
        {"employee_id": "PC001", "email": "principal@dvbc.com", "full_name": "Principal Consultant", "role": "principal_consultant", "department": "Consulting"},
        {"employee_id": "SC001", "email": "senior.consultant@dvbc.com", "full_name": "Senior Consultant", "role": "senior_consultant", "department": "Consulting", "reporting_manager_id": "PC001"},
        {"employee_id": "CON001", "email": "consultant1@dvbc.com", "full_name": "Consultant One", "role": "consultant", "department": "Consulting", "reporting_manager_id": "SC001"},
        # Manager
        {"employee_id": "MGR001", "email": "general.manager@dvbc.com", "full_name": "General Manager", "role": "manager", "department": "Management"},
        # Finance
        {"employee_id": "FIN001", "email": "finance@dvbc.com", "full_name": "Finance Manager", "role": "finance_manager", "department": "Finance"},
    ]
    
    for user in users:
        user["id"] = generate_id()
        user["hashed_password"] = pwd_context.hash("test123")
        user["is_active"] = True
        user["created_at"] = now_iso()
        user["updated_at"] = now_iso()
        
        # Upsert user
        db.users.update_one(
            {"employee_id": user["employee_id"]},
            {"$set": user},
            upsert=True
        )
    
    print(f"Created/Updated {len(users)} test users")
    return users


def create_test_employees():
    """Create employee records"""
    users = list(db.users.find({}, {"_id": 0}))
    
    for user in users:
        employee = {
            "id": generate_id(),
            "employee_id": user["employee_id"],
            "user_id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "department": user["department"],
            "reporting_manager_id": user.get("reporting_manager_id"),
            "designation": user["role"].replace("_", " ").title(),
            "joining_date": "2024-01-15",
            "status": "active",
            "created_at": now_iso()
        }
        
        db.employees.update_one(
            {"employee_id": employee["employee_id"]},
            {"$set": employee},
            upsert=True
        )
    
    print(f"Created/Updated {len(users)} employee records")


def create_test_leads():
    """Create test leads for sales funnel testing"""
    sales_users = list(db.users.find({"role": {"$in": ["sales_executive", "sales_manager"]}}, {"_id": 0}))
    
    leads = [
        {"company": "TechCorp India", "first_name": "Amit", "last_name": "Patel", "email": "amit@techcorp.in", "estimated_value": 500000, "current_stage": "lead", "status": "new"},
        {"company": "Global Solutions", "first_name": "Sunita", "last_name": "Rao", "email": "sunita@globalsol.com", "estimated_value": 750000, "current_stage": "meeting", "status": "contacted"},
        {"company": "Innovate Labs", "first_name": "Vikram", "last_name": "Singh", "email": "vikram@innovate.io", "estimated_value": 1200000, "current_stage": "pricing", "status": "qualified"},
        {"company": "DataDriven Inc", "first_name": "Neha", "last_name": "Gupta", "email": "neha@datadriven.com", "estimated_value": 900000, "current_stage": "sow", "status": "proposal"},
        {"company": "CloudFirst", "first_name": "Raj", "last_name": "Malhotra", "email": "raj@cloudfirst.in", "estimated_value": 2000000, "current_stage": "agreement", "status": "negotiation"},
        {"company": "SmartBiz Solutions", "first_name": "Ananya", "last_name": "Das", "email": "ananya@smartbiz.com", "estimated_value": 450000, "current_stage": "payment", "status": "won"},
        {"company": "FutureTech", "first_name": "Kiran", "last_name": "Kumar", "email": "kiran@futuretech.in", "estimated_value": 1500000, "current_stage": "kickoff", "status": "won"},
        {"company": "Legacy Systems", "first_name": "Meera", "last_name": "Iyer", "email": "meera@legacy.com", "estimated_value": 300000, "current_stage": "complete", "status": "closed_won"},
        {"company": "Failed Deal Corp", "first_name": "Test", "last_name": "User", "email": "test@failed.com", "estimated_value": 100000, "current_stage": "lead", "status": "closed_lost"},
    ]
    
    for i, lead in enumerate(leads):
        assigned_to = sales_users[i % len(sales_users)]
        lead["id"] = generate_id()
        lead["assigned_to"] = assigned_to["id"]
        lead["created_by"] = assigned_to["id"]
        lead["source"] = "website"
        lead["stage_history"] = [{"stage": lead["current_stage"], "entered_at": now_iso()}]
        lead["created_at"] = now_iso()
        lead["updated_at"] = now_iso()
        
        db.leads.update_one(
            {"company": lead["company"]},
            {"$set": lead},
            upsert=True
        )
    
    print(f"Created/Updated {len(leads)} test leads")


def create_test_pricing_plans():
    """Create test pricing plans"""
    leads = list(db.leads.find({"current_stage": {"$in": ["pricing", "sow", "agreement", "payment", "kickoff", "complete"]}}, {"_id": 0}))
    
    for lead in leads:
        plan = {
            "id": generate_id(),
            "lead_id": lead["id"],
            "plan_name": f"Plan for {lead['company']}",
            "base_price": lead["estimated_value"],
            "discount_percentage": 10,
            "final_price": lead["estimated_value"] * 0.9,
            "payment_plan": {
                "type": "monthly",
                "installments": 12,
                "schedule_breakdown": [{"month": i+1, "amount": lead["estimated_value"] * 0.9 / 12} for i in range(12)]
            },
            "status": "approved" if lead["current_stage"] in ["sow", "agreement", "payment", "kickoff", "complete"] else "pending",
            "created_by": lead["assigned_to"],
            "created_at": now_iso()
        }
        
        db.pricing_plans.update_one(
            {"lead_id": lead["id"]},
            {"$set": plan},
            upsert=True
        )
    
    print(f"Created/Updated {len(leads)} pricing plans")


def create_test_sows():
    """Create test SOWs"""
    leads = list(db.leads.find({"current_stage": {"$in": ["sow", "agreement", "payment", "kickoff", "complete"]}}, {"_id": 0}))
    
    for lead in leads:
        sow = {
            "id": generate_id(),
            "lead_id": lead["id"],
            "client_name": lead["company"],
            "project_title": f"Digital Transformation for {lead['company']}",
            "scopes": [
                {"id": generate_id(), "title": "Phase 1 - Assessment", "description": "Current state analysis", "duration_days": 30, "price": lead["estimated_value"] * 0.2},
                {"id": generate_id(), "title": "Phase 2 - Implementation", "description": "Solution deployment", "duration_days": 60, "price": lead["estimated_value"] * 0.5},
                {"id": generate_id(), "title": "Phase 3 - Training", "description": "User training and handover", "duration_days": 15, "price": lead["estimated_value"] * 0.3},
            ],
            "total_value": lead["estimated_value"],
            "start_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=135)).isoformat(),
            "status": "approved" if lead["current_stage"] in ["agreement", "payment", "kickoff", "complete"] else "draft",
            "sales_handover_complete": lead["current_stage"] in ["payment", "kickoff", "complete"],
            "created_by": lead["assigned_to"],
            "created_at": now_iso()
        }
        
        db.enhanced_sow.update_one(
            {"lead_id": lead["id"]},
            {"$set": sow},
            upsert=True
        )
    
    print(f"Created/Updated {len(leads)} SOWs")


def create_test_agreements():
    """Create test agreements"""
    leads = list(db.leads.find({"current_stage": {"$in": ["agreement", "payment", "kickoff", "complete"]}}, {"_id": 0}))
    
    for lead in leads:
        agreement = {
            "id": generate_id(),
            "agreement_number": f"AGR-{datetime.now().strftime('%Y%m%d')}-{lead['id'][:4].upper()}",
            "lead_id": lead["id"],
            "title": f"Service Agreement - {lead['company']}",
            "client_name": lead["company"],
            "client_email": lead["contact_email"],
            "client_phone": "+91-9876543210",
            "total_value": lead["estimated_value"],
            "payment_terms": "Net 30",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "duration_months": 12,
            "status": "signed" if lead["current_stage"] in ["payment", "kickoff", "complete"] else "draft",
            "consent_status": "client_approved" if lead["current_stage"] in ["payment", "kickoff", "complete"] else "pending",
            "payments": [],
            "total_paid": 0,
            "created_by": lead["assigned_to"],
            "created_at": now_iso()
        }
        
        db.agreements.update_one(
            {"lead_id": lead["id"]},
            {"$set": agreement},
            upsert=True
        )
    
    print(f"Created/Updated {len(leads)} agreements")


def create_test_projects():
    """Create test consulting projects"""
    leads = list(db.leads.find({"current_stage": {"$in": ["kickoff", "complete"]}}, {"_id": 0}))
    consultants = list(db.users.find({"role": {"$in": ["consultant", "senior_consultant", "principal_consultant"]}}, {"_id": 0}))
    
    for i, lead in enumerate(leads):
        project = {
            "id": generate_id(),
            "lead_id": lead["id"],
            "project_name": f"Project - {lead['company']}",
            "client_name": lead["company"],
            "status": "completed" if lead["current_stage"] == "complete" else "active",
            "start_date": now_iso(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "budget": lead["estimated_value"],
            "consultant_id": consultants[i % len(consultants)]["id"],
            "team_members": [
                {"user_id": consultants[j % len(consultants)]["id"], "role": "consultant"}
                for j in range(2)
            ],
            "created_at": now_iso()
        }
        
        db.projects.update_one(
            {"lead_id": lead["id"]},
            {"$set": project},
            upsert=True
        )
    
    print(f"Created/Updated {len(leads)} projects")


def create_test_timesheets():
    """Create test timesheets"""
    consultants = list(db.users.find({"role": {"$in": ["consultant", "senior_consultant"]}}, {"_id": 0}))
    projects = list(db.projects.find({}, {"_id": 0}))
    
    if not projects:
        print("No projects found for timesheets")
        return
    
    for consultant in consultants:
        for day_offset in range(7):
            date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            timesheet = {
                "id": generate_id(),
                "employee_id": consultant["id"],
                "project_id": projects[0]["id"],
                "date": date,
                "hours": 8,
                "description": f"Development work on {date}",
                "status": "approved" if day_offset > 3 else "submitted",
                "created_at": now_iso()
            }
            
            db.timesheets.update_one(
                {"employee_id": consultant["id"], "date": date},
                {"$set": timesheet},
                upsert=True
            )
    
    print(f"Created timesheets for {len(consultants)} consultants")


def create_test_leave_requests():
    """Create test leave requests"""
    employees = list(db.employees.find({}, {"_id": 0}).limit(5))
    
    for emp in employees:
        leave = {
            "id": generate_id(),
            "employee_id": emp["employee_id"],
            "user_id": emp.get("user_id"),
            "leave_type": "casual",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d"),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=12)).strftime("%Y-%m-%d"),
            "days": 3,
            "reason": "Personal work",
            "status": "pending",
            "created_at": now_iso()
        }
        
        db.leave_requests.update_one(
            {"employee_id": emp["employee_id"], "start_date": leave["start_date"]},
            {"$set": leave},
            upsert=True
        )
    
    print(f"Created leave requests for {len(employees)} employees")


def create_test_expenses():
    """Create test expense claims"""
    employees = list(db.employees.find({}, {"_id": 0}).limit(5))
    
    for emp in employees:
        expense = {
            "id": generate_id(),
            "employee_id": emp["employee_id"],
            "submitted_by": emp.get("user_id"),
            "expense_type": "travel",
            "amount": 5000,
            "description": "Client meeting travel",
            "date": now_iso(),
            "status": "pending",
            "created_at": now_iso()
        }
        
        db.expenses.update_one(
            {"employee_id": emp["employee_id"], "description": expense["description"]},
            {"$set": expense},
            upsert=True
        )
    
    print(f"Created expense claims for {len(employees)} employees")


def create_test_attendance():
    """Create test attendance records"""
    employees = list(db.employees.find({}, {"_id": 0}))
    now = datetime.now(timezone.utc)
    
    for emp in employees:
        for day in range(5):
            date = (now - timedelta(days=day)).strftime("%Y-%m-%d")
            attendance = {
                "id": generate_id(),
                "employee_id": emp["employee_id"],
                "user_id": emp.get("user_id"),
                "date": date,
                "month": now.month,
                "year": now.year,
                "check_in": f"{date}T09:00:00Z",
                "check_out": f"{date}T18:00:00Z",
                "status": "present",
                "created_at": now_iso()
            }
            
            db.attendance.update_one(
                {"employee_id": emp["employee_id"], "date": date},
                {"$set": attendance},
                upsert=True
            )
    
    print(f"Created attendance for {len(employees)} employees")


def create_test_approval_requests():
    """Create test approval requests for dual approval"""
    pricing_plans = list(db.pricing_plans.find({"status": "pending"}, {"_id": 0}))
    
    for plan in pricing_plans:
        approval = {
            "id": generate_id(),
            "entity_type": "pricing",
            "entity_id": plan["id"],
            "required_approvers": 2,
            "allowed_roles": ["sales_manager", "principal_consultant", "admin"],
            "status": "pending",
            "approvals": [],
            "requested_by": plan.get("created_by"),
            "requested_at": now_iso()
        }
        
        db.approval_requests.update_one(
            {"entity_id": plan["id"]},
            {"$set": approval},
            upsert=True
        )
    
    print(f"Created approval requests for {len(pricing_plans)} pricing plans")


def create_test_audit_logs():
    """Create sample audit logs"""
    users = list(db.users.find({}, {"_id": 0}).limit(5))
    
    actions = [
        ("user.login", "user"),
        ("lead.create", "lead"),
        ("lead.update", "lead"),
        ("agreement.create", "agreement"),
        ("permission.grant", "permission"),
    ]
    
    for user in users:
        for action, entity_type in actions:
            log = {
                "id": generate_id(),
                "action": action,
                "entity_type": entity_type,
                "entity_id": generate_id(),
                "performed_by": user["id"],
                "performed_at": now_iso(),
                "changes": {"field": "value"},
                "metadata": {"ip_address": "192.168.1.1"}
            }
            db.audit_logs.insert_one(log)
    
    print(f"Created {len(users) * len(actions)} audit logs")


def main():
    print("=" * 50)
    print("NETRA ERP - Creating Comprehensive Test Data")
    print("=" * 50)
    
    # Create data in order
    create_test_users()
    create_test_employees()
    create_test_leads()
    create_test_pricing_plans()
    create_test_sows()
    create_test_agreements()
    create_test_projects()
    create_test_timesheets()
    create_test_leave_requests()
    create_test_expenses()
    create_test_attendance()
    create_test_approval_requests()
    create_test_audit_logs()
    
    print("=" * 50)
    print("Test data creation complete!")
    print("=" * 50)
    
    # Print summary
    print("\nData Summary:")
    print(f"  Users: {db.users.count_documents({})}")
    print(f"  Employees: {db.employees.count_documents({})}")
    print(f"  Leads: {db.leads.count_documents({})}")
    print(f"  Pricing Plans: {db.pricing_plans.count_documents({})}")
    print(f"  SOWs: {db.enhanced_sow.count_documents({})}")
    print(f"  Agreements: {db.agreements.count_documents({})}")
    print(f"  Projects: {db.projects.count_documents({})}")
    print(f"  Timesheets: {db.timesheets.count_documents({})}")
    print(f"  Leave Requests: {db.leave_requests.count_documents({})}")
    print(f"  Expenses: {db.expenses.count_documents({})}")
    print(f"  Attendance: {db.attendance.count_documents({})}")
    print(f"  Approval Requests: {db.approval_requests.count_documents({})}")
    print(f"  Audit Logs: {db.audit_logs.count_documents({})}")


if __name__ == "__main__":
    main()
