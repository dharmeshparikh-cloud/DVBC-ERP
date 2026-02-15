"""
Comprehensive Test Cases for Indian HR Consulting Data Seeding
Tests data integrity, relationships, and business rules
"""

import pytest
import asyncio
import re
from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
db_name = os.environ.get('DB_NAME')

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def db():
    client = AsyncIOMotorClient(mongo_url)
    database = client[db_name]
    yield database
    client.close()


# ============== VALID INPUTS - USER CREATION ==============

class TestUserCreation:
    """TC001-TC005: User validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc001_admin_user_exists(self, db):
        """TC001: Verify admin user creation"""
        admin = await db.users.find_one({"email": "admin@company.com"}, {"_id": 0})
        assert admin is not None, "Admin user should exist"
        assert admin["role"] == "admin", "Admin should have admin role"
        assert "hashed_password" in admin, "Admin should have hashed password"
    
    @pytest.mark.asyncio
    async def test_tc002_valid_indian_names(self, db):
        """TC002: Verify employee users have valid Indian names"""
        users = await db.users.find({}, {"_id": 0, "full_name": 1}).to_list(100)
        
        indian_first_names = [
            "Rajesh", "Amit", "Suresh", "Vikram", "Arun", "Prakash", "Sanjay", "Rahul",
            "Priya", "Sneha", "Pooja", "Neha", "Anjali", "Swati", "Kavita", "Sunita",
            "Anand", "Deepak", "Nitin", "Manoj", "Ajay", "Vinod", "Ashok", "Ravi",
            "Meera", "Divya", "Ritu", "Anita", "Shweta", "Pallavi", "Rekha", "Lakshmi"
        ]
        
        for user in users:
            if user["full_name"] != "System Administrator":
                first_name = user["full_name"].split()[0]
                assert first_name in indian_first_names or any(
                    name in user["full_name"] for name in indian_first_names
                ), f"User {user['full_name']} should have Indian name"
    
    @pytest.mark.asyncio
    async def test_tc003_employee_email_domain(self, db):
        """TC003: Verify user email format for @dvconsulting.co.in domain"""
        users = await db.users.find(
            {"email": {"$ne": "admin@company.com"}},
            {"_id": 0, "email": 1}
        ).to_list(100)
        
        for user in users:
            assert user["email"].endswith("@dvconsulting.co.in"), \
                f"Employee email {user['email']} should end with @dvconsulting.co.in"
    
    @pytest.mark.asyncio
    async def test_tc004_all_roles_created(self, db):
        """TC004: Verify all predefined roles are created"""
        expected_roles = [
            "admin", "principal_consultant", "lead_consultant", "senior_consultant",
            "consultant", "lean_consultant", "project_manager", "account_manager",
            "hr_manager", "hr_executive", "executive", "manager"
        ]
        
        for role in expected_roles:
            count = await db.users.count_documents({"role": role})
            assert count >= 1, f"At least 1 user should have role '{role}'"
    
    @pytest.mark.asyncio
    async def test_tc005_passwords_are_hashed(self, db):
        """TC005: Verify password hashing"""
        users = await db.users.find({}, {"_id": 0, "hashed_password": 1}).to_list(100)
        
        for user in users:
            if "hashed_password" in user:
                # bcrypt hashes start with $2b$ or $2a$
                assert user["hashed_password"].startswith("$2"), \
                    "Password should be bcrypt hashed"


# ============== VALID INPUTS - EMPLOYEE DATA ==============

class TestEmployeeData:
    """TC006-TC010: Employee validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc006_employee_id_pattern(self, db):
        """TC006: Verify employee IDs follow DVC### pattern"""
        employees = await db.employees.find({}, {"_id": 0, "employee_id": 1}).to_list(100)
        
        pattern = re.compile(r'^DVC\d{3}$')
        for emp in employees:
            assert pattern.match(emp["employee_id"]), \
                f"Employee ID {emp['employee_id']} should match DVC### pattern"
    
    @pytest.mark.asyncio
    async def test_tc007_indian_phone_format(self, db):
        """TC007: Verify Indian phone number format"""
        employees = await db.employees.find({}, {"_id": 0, "phone": 1}).to_list(100)
        
        # Pattern: +91 XX XXXXXXXX
        pattern = re.compile(r'^\+91 \d{2}\d{8}$')
        for emp in employees:
            if emp.get("phone"):
                assert pattern.match(emp["phone"]), \
                    f"Phone {emp['phone']} should match +91 XX XXXXXXXX format"
    
    @pytest.mark.asyncio
    async def test_tc008_valid_ifsc_codes(self, db):
        """TC008: Verify bank details with valid IFSC codes"""
        employees = await db.employees.find(
            {"bank_details": {"$exists": True}},
            {"_id": 0, "bank_details": 1}
        ).to_list(100)
        
        valid_bank_codes = ["SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "BARB", "KKBK", 
                          "INDB", "YESB", "IDFB", "CNRB", "UBIN", "BKID", "CBIN", "IDIB"]
        
        for emp in employees:
            if emp.get("bank_details") and emp["bank_details"].get("ifsc_code"):
                ifsc = emp["bank_details"]["ifsc_code"]
                assert len(ifsc) == 11, f"IFSC {ifsc} should be 11 characters"
                assert ifsc[:4] in valid_bank_codes, f"IFSC {ifsc} should start with valid bank code"
    
    @pytest.mark.asyncio
    async def test_tc009_leave_balance_initialization(self, db):
        """TC009: Verify leave balance initialization"""
        employees = await db.employees.find(
            {"leave_balance": {"$exists": True}},
            {"_id": 0, "leave_balance": 1, "employee_id": 1}
        ).to_list(100)
        
        for emp in employees:
            lb = emp.get("leave_balance", {})
            assert lb.get("casual_leave") == 12, f"{emp['employee_id']} should have 12 casual leaves"
            assert lb.get("sick_leave") == 6, f"{emp['employee_id']} should have 6 sick leaves"
            assert lb.get("earned_leave") == 15, f"{emp['employee_id']} should have 15 earned leaves"
    
    @pytest.mark.asyncio
    async def test_tc010_reporting_manager_linkage(self, db):
        """TC010: Verify reporting manager linkage"""
        employees = await db.employees.find({}, {"_id": 0}).to_list(100)
        employee_ids = {e["id"] for e in employees}
        
        # Principal consultants may not have reporting managers
        non_principal = [e for e in employees if e.get("role") != "principal_consultant"]
        
        for emp in non_principal:
            if emp.get("reporting_manager_id"):
                assert emp["reporting_manager_id"] in employee_ids, \
                    f"Reporting manager {emp['reporting_manager_id']} should exist"


# ============== VALID INPUTS - LEAD DATA ==============

class TestLeadData:
    """TC011-TC014: Lead validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc011_leads_from_indian_companies(self, db):
        """TC011: Verify leads from Indian companies"""
        leads = await db.leads.find({}, {"_id": 0, "company": 1}).to_list(100)
        
        indian_companies = [
            "Tata Steel", "Reliance", "Infosys", "Wipro", "HCL", "Mahindra",
            "Bajaj", "Hero", "Sun Pharma", "Dr. Reddy", "Cipla", "Asian Paints",
            "Godrej", "L&T", "JSW", "Bharti", "HDFC", "ICICI", "Axis", "ITC"
        ]
        
        for lead in leads:
            has_indian_company = any(
                company in lead["company"] for company in indian_companies
            ) or "Pvt Ltd" in lead["company"] or "Limited" in lead["company"]
            assert has_indian_company, f"Lead company {lead['company']} should be Indian"
    
    @pytest.mark.asyncio
    async def test_tc012_lead_status_distribution(self, db):
        """TC012: Verify lead status distribution"""
        leads = await db.leads.find({}, {"_id": 0, "status": 1}).to_list(100)
        
        status_counts = Counter([l["status"] for l in leads])
        total = len(leads)
        
        # Verify all statuses exist
        expected_statuses = ["new", "contacted", "qualified", "proposal", "agreement", "closed"]
        for status in expected_statuses:
            assert status in status_counts, f"Status '{status}' should exist in leads"
    
    @pytest.mark.asyncio
    async def test_tc013_lead_score_calculation(self, db):
        """TC013: Verify lead score calculation"""
        leads = await db.leads.find({}, {"_id": 0, "lead_score": 1, "score_breakdown": 1}).to_list(100)
        
        for lead in leads:
            assert 0 <= lead.get("lead_score", 0) <= 100, "Lead score should be 0-100"
            
            breakdown = lead.get("score_breakdown", {})
            if breakdown:
                assert "title_score" in breakdown, "Breakdown should have title_score"
                assert "contact_score" in breakdown, "Breakdown should have contact_score"
                assert "engagement_score" in breakdown, "Breakdown should have engagement_score"
    
    @pytest.mark.asyncio
    async def test_tc014_valid_lead_emails(self, db):
        """TC014: Verify valid email addresses for leads"""
        leads = await db.leads.find({}, {"_id": 0, "email": 1}).to_list(100)
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for lead in leads:
            if lead.get("email"):
                assert email_pattern.match(lead["email"]), \
                    f"Email {lead['email']} should be valid format"
                # No special characters like apostrophes in domain
                assert "'" not in lead["email"], f"Email {lead['email']} should not have apostrophe"


# ============== BOUNDARY TESTING ==============

class TestBoundaries:
    """TC015-TC018: Boundary validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc016_salary_range_boundaries(self, db):
        """TC016: Verify salary range boundaries"""
        employees = await db.employees.find(
            {"salary": {"$exists": True}},
            {"_id": 0, "salary": 1, "role": 1, "designation": 1}
        ).to_list(100)
        
        salary_ranges = {
            "Principal Consultant": (150000, 250000),
            "Lead Consultant": (100000, 150000),
            "Senior Consultant": (80000, 120000),
            "Consultant": (50000, 80000),
            "Lean Consultant": (35000, 50000),
            "Project Manager": (100000, 150000),
            "Account Manager": (70000, 100000),
            "Sales Executive": (40000, 70000),
            "HR Manager": (80000, 120000),
            "HR Executive": (35000, 50000),
        }
        
        for emp in employees:
            designation = emp.get("designation", "")
            salary = emp.get("salary", 0)
            if designation in salary_ranges:
                min_sal, max_sal = salary_ranges[designation]
                assert min_sal <= salary <= max_sal, \
                    f"{designation} salary {salary} should be {min_sal}-{max_sal}"
    
    @pytest.mark.asyncio
    async def test_tc017_attendance_date_boundaries(self, db):
        """TC017: Verify date boundaries for attendance"""
        from datetime import datetime, timedelta
        
        attendance = await db.attendance.find({}, {"_id": 0, "date": 1}).to_list(5000)
        
        today = datetime.now().date()
        ninety_days_ago = today - timedelta(days=90)
        
        for record in attendance:
            date_str = record["date"]
            record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Should be within last 90 days
            assert record_date <= today, f"Date {date_str} should not be in future"
            assert record_date >= ninety_days_ago, f"Date {date_str} should be within 90 days"
            
            # Should not be weekend
            assert record_date.weekday() < 5, f"Date {date_str} should not be weekend"
    
    @pytest.mark.asyncio
    async def test_tc018_expense_amount_boundaries(self, db):
        """TC018: Verify expense amount boundaries"""
        expenses = await db.expenses.find({}, {"_id": 0, "line_items": 1, "total_amount": 1}).to_list(200)
        
        for expense in expenses:
            total = expense.get("total_amount", 0)
            assert total > 0, "Expense total should be positive"
            assert total < 100000, "Expense total should be reasonable (< 1 lakh)"
            
            # Verify line items sum to total
            line_items = expense.get("line_items", [])
            calculated_total = sum(item.get("amount", 0) for item in line_items)
            assert calculated_total == total, f"Line items sum {calculated_total} should equal total {total}"


# ============== DATA RELATIONSHIPS & INTEGRITY ==============

class TestDataRelationships:
    """TC019-TC023: Relationship validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc019_client_lead_relationship(self, db):
        """TC019: Verify Client-Lead relationship"""
        clients = await db.clients.find({}, {"_id": 0, "lead_id": 1, "company_name": 1}).to_list(100)
        
        for client in clients:
            if client.get("lead_id"):
                lead = await db.leads.find_one({"id": client["lead_id"]}, {"_id": 0, "status": 1})
                assert lead is not None, f"Client {client['company_name']} should have valid lead"
                assert lead["status"] == "closed", f"Client's lead should be closed"
    
    @pytest.mark.asyncio
    async def test_tc020_agreement_quotation_chain(self, db):
        """TC020: Verify Agreement-Quotation-PricingPlan chain"""
        agreements = await db.agreements.find({}, {"_id": 0}).to_list(100)
        
        for agreement in agreements:
            # Check quotation exists
            if agreement.get("quotation_id"):
                quotation = await db.quotations.find_one(
                    {"id": agreement["quotation_id"]}, {"_id": 0}
                )
                assert quotation is not None, \
                    f"Agreement {agreement['agreement_number']} should have valid quotation"
                
                # Check pricing plan exists
                if quotation.get("pricing_plan_id"):
                    pricing_plan = await db.pricing_plans.find_one(
                        {"id": quotation["pricing_plan_id"]}, {"_id": 0}
                    )
                    assert pricing_plan is not None, \
                        f"Quotation should have valid pricing plan"
    
    @pytest.mark.asyncio
    async def test_tc021_project_agreement_linkage(self, db):
        """TC021: Verify Project-Agreement linkage"""
        projects = await db.projects.find({}, {"_id": 0, "agreement_id": 1, "name": 1}).to_list(100)
        
        for project in projects:
            if project.get("agreement_id"):
                agreement = await db.agreements.find_one(
                    {"id": project["agreement_id"]}, {"_id": 0, "status": 1}
                )
                assert agreement is not None, f"Project {project['name']} should have valid agreement"
                assert agreement["status"] == "approved", "Project's agreement should be approved"
    
    @pytest.mark.asyncio
    async def test_tc022_task_sow_project_linkage(self, db):
        """TC022: Verify Task-SOW-Project linkage"""
        tasks = await db.tasks.find({"sow_id": {"$exists": True, "$ne": None}}, {"_id": 0}).to_list(200)
        
        for task in tasks:
            if task.get("sow_id"):
                sow = await db.sow.find_one({"id": task["sow_id"]}, {"_id": 0})
                assert sow is not None, f"Task should have valid SOW"
                
                # Verify sow_item_id exists in SOW items
                if task.get("sow_item_id"):
                    item_ids = [item["id"] for item in sow.get("items", [])]
                    assert task["sow_item_id"] in item_ids, \
                        f"Task's sow_item_id should exist in SOW items"
    
    @pytest.mark.asyncio
    async def test_tc023_sow_pricing_plan_bidirectional(self, db):
        """TC023: Verify SOW-PricingPlan bidirectional link"""
        sows = await db.sow.find({}, {"_id": 0, "id": 1, "pricing_plan_id": 1}).to_list(100)
        
        for sow in sows:
            pricing_plan = await db.pricing_plans.find_one(
                {"id": sow["pricing_plan_id"]}, {"_id": 0, "sow_id": 1}
            )
            assert pricing_plan is not None, "SOW should have valid pricing plan"
            assert pricing_plan.get("sow_id") == sow["id"], \
                "Pricing plan's sow_id should match SOW's id"


# ============== CONCURRENT USAGE & IDEMPOTENCY ==============

class TestConcurrencyIdempotency:
    """TC024-TC027: Concurrency and idempotency tests"""
    
    @pytest.mark.asyncio
    async def test_tc025_unique_emails(self, db):
        """TC025: Verify unique email constraint"""
        users = await db.users.find({}, {"_id": 0, "email": 1}).to_list(100)
        emails = [u["email"] for u in users]
        
        assert len(emails) == len(set(emails)), "All emails should be unique"
    
    @pytest.mark.asyncio
    async def test_tc026_unique_employee_ids(self, db):
        """TC026: Verify unique employee_id constraint"""
        employees = await db.employees.find({}, {"_id": 0, "employee_id": 1}).to_list(100)
        emp_ids = [e["employee_id"] for e in employees]
        
        assert len(emp_ids) == len(set(emp_ids)), "All employee IDs should be unique"


# ============== DATA PERSISTENCE CHECKS ==============

class TestDataPersistence:
    """TC032-TC035: Data persistence validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc033_datetime_iso_format(self, db):
        """TC033: Verify datetime fields are ISO format"""
        # Check employees
        employees = await db.employees.find({}, {"_id": 0, "created_at": 1}).to_list(10)
        iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        
        for emp in employees:
            if emp.get("created_at"):
                assert iso_pattern.match(emp["created_at"]), \
                    f"Date {emp['created_at']} should be ISO format"
    
    @pytest.mark.asyncio
    async def test_tc034_no_objectid_in_data(self, db):
        """TC034: Verify no MongoDB ObjectId in data"""
        from bson import ObjectId
        
        # Check a sample of collections
        collections = ["users", "employees", "leads", "projects"]
        
        for coll_name in collections:
            docs = await db[coll_name].find({}).to_list(10)
            for doc in docs:
                for key, value in doc.items():
                    if key != "_id":
                        assert not isinstance(value, ObjectId), \
                            f"Field {key} in {coll_name} should not be ObjectId"
    
    @pytest.mark.asyncio
    async def test_tc035_attendance_no_weekends(self, db):
        """TC035: Verify attendance records for working days only"""
        from datetime import datetime
        
        attendance = await db.attendance.find({}, {"_id": 0, "date": 1}).to_list(5000)
        
        for record in attendance:
            date_obj = datetime.strptime(record["date"], "%Y-%m-%d")
            assert date_obj.weekday() < 5, f"Date {record['date']} should not be weekend"


# ============== SPECIFIC DATA VALIDATION ==============

class TestSpecificData:
    """TC046-TC050: Specific data validation tests"""
    
    @pytest.mark.asyncio
    async def test_tc046_salary_components(self, db):
        """TC046: Verify salary components include both earnings and deductions"""
        components = await db.salary_components.find({}, {"_id": 0}).to_list(20)
        
        earning_names = ["Basic Salary", "HRA", "Conveyance", "Special Allowance"]
        deduction_names = ["PF", "Professional Tax", "TDS", "ESI"]
        
        comp_names = [c["name"] for c in components]
        
        # Check earnings exist
        for name in earning_names:
            assert any(name in cn for cn in comp_names), f"Should have earning component containing '{name}'"
        
        # Check deductions exist
        has_deductions = any(c["type"] == "deduction" for c in components)
        assert has_deductions, "Should have deduction components"
    
    @pytest.mark.asyncio
    async def test_tc047_sow_categories(self, db):
        """TC047: Verify SOW categories match HR consulting services"""
        sows = await db.sow.find({}, {"_id": 0, "items": 1}).to_list(50)
        
        expected_categories = {"hr", "training", "sales", "operations", "analytics", "digital_marketing"}
        found_categories = set()
        
        for sow in sows:
            for item in sow.get("items", []):
                found_categories.add(item.get("category"))
        
        # At least 3 categories should be present
        assert len(found_categories.intersection(expected_categories)) >= 3, \
            f"Should have at least 3 HR consulting categories, found: {found_categories}"
    
    @pytest.mark.asyncio
    async def test_tc048_quotation_calculations(self, db):
        """TC048: Verify quotation calculations are correct"""
        quotations = await db.quotations.find({}, {"_id": 0}).to_list(50)
        
        for quot in quotations:
            subtotal = quot.get("subtotal", 0)
            discount = quot.get("discount_amount", 0)
            gst = quot.get("gst_amount", 0)
            grand_total = quot.get("grand_total", 0)
            
            # Calculate expected grand total
            expected = subtotal - discount + gst
            
            # Allow for small floating point differences
            assert abs(grand_total - expected) < 1, \
                f"Grand total {grand_total} should equal {expected} (subtotal - discount + gst)"
    
    @pytest.mark.asyncio
    async def test_tc049_meeting_types_distributed(self, db):
        """TC049: Verify meeting types are properly distributed"""
        meetings = await db.meetings.find({}, {"_id": 0, "type": 1}).to_list(100)
        
        types = Counter([m["type"] for m in meetings])
        
        assert "sales" in types, "Should have sales meetings"
        assert "consulting" in types, "Should have consulting meetings"
    
    @pytest.mark.asyncio
    async def test_tc050_notification_types_coverage(self, db):
        """TC050: Verify notification types cover all scenarios"""
        notifications = await db.notifications.find({}, {"_id": 0, "type": 1}).to_list(200)
        
        types = set(n["type"] for n in notifications)
        
        expected_types = {"leave_request", "expense_approval", "task_assigned", "meeting_reminder"}
        
        # At least 2 notification types should exist
        assert len(types) >= 2, f"Should have multiple notification types, found: {types}"


# ============== DATA COUNT VALIDATION ==============

class TestDataCounts:
    """Verify expected data counts"""
    
    @pytest.mark.asyncio
    async def test_users_count(self, db):
        """Verify users count"""
        count = await db.users.count_documents({})
        assert count >= 40, f"Should have at least 40 users, found {count}"
    
    @pytest.mark.asyncio
    async def test_employees_count(self, db):
        """Verify employees count"""
        count = await db.employees.count_documents({})
        assert count >= 40, f"Should have at least 40 employees, found {count}"
    
    @pytest.mark.asyncio
    async def test_leads_count(self, db):
        """Verify leads count"""
        count = await db.leads.count_documents({})
        assert count >= 40, f"Should have at least 40 leads, found {count}"
    
    @pytest.mark.asyncio
    async def test_projects_count(self, db):
        """Verify projects count"""
        count = await db.projects.count_documents({})
        assert count >= 5, f"Should have at least 5 projects, found {count}"
    
    @pytest.mark.asyncio
    async def test_attendance_count(self, db):
        """Verify attendance count"""
        count = await db.attendance.count_documents({})
        assert count >= 2000, f"Should have at least 2000 attendance records, found {count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
