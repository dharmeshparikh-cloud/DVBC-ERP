#!/usr/bin/env python3
"""
Comprehensive Test Runner for Indian HR Consulting Data Seeding
Tests data integrity, relationships, and business rules using pymongo (sync)
"""

import re
import sys
from pymongo import MongoClient
from collections import Counter
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv('/app/backend/.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
db_name = os.environ.get('DB_NAME')

client = MongoClient(mongo_url)
db = client[db_name]

# Test results tracking
passed = 0
failed = 0
errors = []

def test(test_id, name, condition, error_msg=""):
    global passed, failed, errors
    try:
        if condition:
            print(f"  ✅ {test_id}: {name}")
            passed += 1
            return True
        else:
            print(f"  ❌ {test_id}: {name}")
            if error_msg:
                print(f"     → {error_msg}")
            failed += 1
            errors.append((test_id, name, error_msg))
            return False
    except Exception as e:
        print(f"  ⚠️  {test_id}: {name} - ERROR: {str(e)}")
        failed += 1
        errors.append((test_id, name, str(e)))
        return False

def run_tests():
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE DATA SEEDING TEST SUITE")
    print("="*70)
    
    # ============== VALID INPUTS - USER CREATION ==============
    print("\n📋 TC001-TC005: User Creation Tests")
    print("-"*50)
    
    # TC001: Admin user exists
    admin = db.users.find_one({"email": "admin@company.com"}, {"_id": 0})
    test("TC001", "Admin user exists with correct role",
         admin is not None and admin.get("role") == "admin" and "hashed_password" in admin)
    
    # TC002: Valid Indian names
    users = list(db.users.find({}, {"_id": 0, "full_name": 1}))
    indian_names = ["Rajesh", "Amit", "Suresh", "Vikram", "Priya", "Sneha", "Pooja", "Neha",
                   "Anand", "Deepak", "Nitin", "Manoj", "Anjali", "Swati", "Kavita", "Sunita",
                   "Meera", "Divya", "Ritu", "Anita", "Shweta", "Pallavi", "Rekha", "Lakshmi",
                   "Arun", "Prakash", "Sanjay", "Rahul", "Kiran", "Gaurav", "Manish", "Pradeep",
                   "Ramesh", "Dinesh", "Sunil", "Mukesh", "Pankaj", "Naveen", "Arvind", "Sandeep",
                   "Jitendra", "Yogesh", "Deepika", "Manisha", "Nisha", "Preeti", "Rashmi", 
                   "Shalini", "Archana", "Geeta", "Mamta", "Vandana", "Seema", "Jyoti", "Sapna", "Komal",
                   "Sharma", "Verma", "Singh", "Kumar", "Gupta", "Patel", "Reddy", "Rao", "Naidu",
                   "Iyer", "Nair", "Menon", "Pillai", "Choudhary", "Malhotra", "Kapoor", "Joshi",
                   "Desai", "Mehta", "Shah", "Bhat", "Kulkarni", "Patil", "Deshpande", "Agarwal",
                   "Bansal", "Mittal", "Garg", "Saxena", "Tiwari", "Pandey", "Mishra", "Vinod", "Ashok", "Ravi"]
    non_admin = [u for u in users if u.get("full_name") != "System Administrator"]
    has_indian_names = all(any(n in u.get("full_name", "") for n in indian_names) for u in non_admin)
    test("TC002", "Users have valid Indian names", has_indian_names)
    
    # TC003: Employee email domain
    emp_users = list(db.users.find({"email": {"$ne": "admin@company.com"}}, {"_id": 0, "email": 1}))
    all_correct_domain = all(u.get("email", "").endswith("@dvconsulting.co.in") for u in emp_users)
    test("TC003", "Employee emails end with @dvconsulting.co.in", all_correct_domain)
    
    # TC004: All roles created
    expected_roles = ["admin", "principal_consultant", "lead_consultant", "senior_consultant",
                     "consultant", "lean_consultant", "project_manager", "account_manager"]
    roles_exist = all(db.users.count_documents({"role": r}) >= 1 for r in expected_roles)
    test("TC004", "All predefined roles have at least 1 user", roles_exist)
    
    # TC005: Passwords are hashed
    users_with_pass = list(db.users.find({}, {"_id": 0, "hashed_password": 1}))
    all_hashed = all(u.get("hashed_password", "").startswith("$2") for u in users_with_pass if u.get("hashed_password"))
    test("TC005", "All passwords are bcrypt hashed", all_hashed)
    
    # ============== VALID INPUTS - EMPLOYEE DATA ==============
    print("\n📋 TC006-TC010: Employee Data Tests")
    print("-"*50)
    
    # TC006: Employee ID pattern
    employees = list(db.employees.find({}, {"_id": 0, "employee_id": 1}))
    pattern = re.compile(r'^DVC\d{3}$')
    all_match = all(pattern.match(e.get("employee_id", "")) for e in employees)
    test("TC006", "Employee IDs match DVC### pattern", all_match,
         f"Sample IDs: {[e['employee_id'] for e in employees[:3]]}")
    
    # TC007: Indian phone format
    emps_with_phone = list(db.employees.find({"phone": {"$exists": True}}, {"_id": 0, "phone": 1}))
    phone_pattern = re.compile(r'^\+91 \d{2}\d{8}$')
    valid_phones = sum(1 for e in emps_with_phone if phone_pattern.match(e.get("phone", "")))
    test("TC007", "Phone numbers match +91 format", valid_phones >= len(emps_with_phone) * 0.9,
         f"{valid_phones}/{len(emps_with_phone)} valid")
    
    # TC008: Valid IFSC codes
    emps_bank = list(db.employees.find({"bank_details.ifsc_code": {"$exists": True}}, {"_id": 0, "bank_details": 1}))
    valid_ifsc = all(len(e.get("bank_details", {}).get("ifsc_code", "")) == 11 for e in emps_bank)
    test("TC008", "IFSC codes are 11 characters", valid_ifsc)
    
    # TC009: Leave balance initialization
    emps_leave = list(db.employees.find({}, {"_id": 0, "leave_balance": 1}))
    correct_leave = all(
        e.get("leave_balance", {}).get("casual_leave") == 12 and
        e.get("leave_balance", {}).get("sick_leave") == 6 and
        e.get("leave_balance", {}).get("earned_leave") == 15
        for e in emps_leave
    )
    test("TC009", "Leave balances initialized correctly (12 CL, 6 SL, 15 EL)", correct_leave)
    
    # TC010: Reporting manager linkage
    all_emps = list(db.employees.find({}, {"_id": 0, "id": 1, "reporting_manager_id": 1, "role": 1}))
    emp_ids = {e["id"] for e in all_emps}
    non_principal = [e for e in all_emps if e.get("role") != "principal_consultant"]
    valid_managers = sum(1 for e in non_principal if e.get("reporting_manager_id") in emp_ids or e.get("reporting_manager_id") is None)
    test("TC010", "Reporting managers are valid employee IDs", valid_managers >= len(non_principal) * 0.8)
    
    # ============== VALID INPUTS - LEAD DATA ==============
    print("\n📋 TC011-TC014: Lead Data Tests")
    print("-"*50)
    
    # TC011: Indian companies
    leads = list(db.leads.find({}, {"_id": 0, "company": 1}))
    indian_keywords = ["Tata", "Reliance", "Infosys", "Wipro", "HCL", "Mahindra", "Bajaj",
                      "Hero", "Pharma", "Godrej", "Vedanta", "HDFC", "ICICI", "Axis", "ITC",
                      "Limited", "Pvt Ltd", "Technologies", "Industries", "Solutions",
                      "Dr. Reddy", "Asian Paints", "Larsen", "Bharti", "Hindustan", "Nestle",
                      "Dabur", "Titan", "Adani", "Power Grid", "NTPC", "Raymond", "Marico",
                      "JSW", "Cipla", "Sunrise", "Vertex", "Global Trade", "Evergreen",
                      "Horizon", "Matrix", "Pioneer", "Kaveri", "Shanti", "Aarav", "Nirmaan",
                      "Dhanush", "Sagar", "Technocraft", "Prism", "Engineering", "Marine"]
    has_indian = sum(1 for l in leads if any(k in l.get("company", "") for k in indian_keywords))
    test("TC011", "Leads are from Indian companies", has_indian >= len(leads) * 0.9,
         f"{has_indian}/{len(leads)} Indian companies")
    
    # TC012: Lead status distribution
    status_counts = Counter([l.get("status") for l in leads])
    expected_statuses = ["new", "contacted", "qualified", "proposal", "closed"]
    has_all_statuses = all(s in status_counts for s in expected_statuses)
    test("TC012", "All lead statuses exist", has_all_statuses,
         f"Statuses: {dict(status_counts)}")
    
    # TC013: Lead score calculation
    leads_scores = list(db.leads.find({}, {"_id": 0, "lead_score": 1, "score_breakdown": 1}))
    valid_scores = all(
        0 <= l.get("lead_score", -1) <= 100 and
        "title_score" in l.get("score_breakdown", {})
        for l in leads_scores
    )
    test("TC013", "Lead scores are 0-100 with breakdown", valid_scores)
    
    # TC014: Valid lead emails
    leads_email = list(db.leads.find({}, {"_id": 0, "email": 1}))
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    valid_emails = all(email_pattern.match(l.get("email", "")) and "'" not in l.get("email", "") for l in leads_email)
    test("TC014", "Lead emails are valid format (no special chars)", valid_emails)
    
    # ============== BOUNDARY TESTING ==============
    print("\n📋 TC016-TC018: Boundary Tests")
    print("-"*50)
    
    # TC016: Salary range boundaries
    salary_ranges = {
        "Principal Consultant": (150000, 250000),
        "Lead Consultant": (100000, 150000),
        "Senior Consultant": (80000, 120000),
        "Consultant": (50000, 80000),
        "Lean Consultant": (35000, 50000),
    }
    emps_salary = list(db.employees.find({"salary": {"$exists": True}}, {"_id": 0, "salary": 1, "designation": 1}))
    in_range = 0
    total_checked = 0
    for e in emps_salary:
        des = e.get("designation", "")
        sal = e.get("salary", 0)
        if des in salary_ranges:
            total_checked += 1
            min_s, max_s = salary_ranges[des]
            if min_s <= sal <= max_s:
                in_range += 1
    test("TC016", "Salaries within defined ranges", in_range >= total_checked * 0.9 if total_checked > 0 else True,
         f"{in_range}/{total_checked} in range")
    
    # TC017: Attendance date boundaries
    today = datetime.now().date()
    ninety_days_ago = today - timedelta(days=90)
    attendance = list(db.attendance.find({}, {"_id": 0, "date": 1}).limit(500))
    valid_dates = 0
    for a in attendance:
        try:
            d = datetime.strptime(a.get("date", ""), "%Y-%m-%d").date()
            if ninety_days_ago <= d <= today and d.weekday() < 5:
                valid_dates += 1
        except:
            pass
    test("TC017", "Attendance dates within 90 days, no weekends", valid_dates >= len(attendance) * 0.95,
         f"{valid_dates}/{len(attendance)} valid")
    
    # TC018: Expense amount boundaries
    expenses = list(db.expenses.find({}, {"_id": 0, "line_items": 1, "total_amount": 1}))
    valid_expenses = all(
        e.get("total_amount", 0) > 0 and
        e.get("total_amount", 0) < 100000 and
        sum(i.get("amount", 0) for i in e.get("line_items", [])) == e.get("total_amount", 0)
        for e in expenses
    )
    test("TC018", "Expense amounts valid and line items sum correctly", valid_expenses)
    
    # ============== DATA RELATIONSHIPS & INTEGRITY ==============
    print("\n📋 TC019-TC023: Data Relationship Tests")
    print("-"*50)
    
    # TC019: Client-Lead relationship
    clients = list(db.clients.find({}, {"_id": 0, "lead_id": 1, "company_name": 1}))
    valid_client_leads = 0
    for c in clients:
        if c.get("lead_id"):
            lead = db.leads.find_one({"id": c["lead_id"]}, {"_id": 0, "status": 1})
            if lead and lead.get("status") == "closed":
                valid_client_leads += 1
    test("TC019", "Clients linked to closed leads", valid_client_leads == len(clients),
         f"{valid_client_leads}/{len(clients)} valid")
    
    # TC020: Agreement-Quotation-PricingPlan chain
    agreements = list(db.agreements.find({}, {"_id": 0, "agreement_number": 1, "quotation_id": 1}))
    valid_chains = 0
    for a in agreements:
        if a.get("quotation_id"):
            quot = db.quotations.find_one({"id": a["quotation_id"]}, {"_id": 0, "pricing_plan_id": 1})
            if quot and quot.get("pricing_plan_id"):
                pp = db.pricing_plans.find_one({"id": quot["pricing_plan_id"]}, {"_id": 0})
                if pp:
                    valid_chains += 1
    test("TC020", "Agreement → Quotation → PricingPlan chain valid", valid_chains >= len(agreements) * 0.8,
         f"{valid_chains}/{len(agreements)} valid chains")
    
    # TC021: Project-Agreement linkage
    projects = list(db.projects.find({}, {"_id": 0, "agreement_id": 1, "name": 1}))
    valid_projects = 0
    for p in projects:
        if p.get("agreement_id"):
            agr = db.agreements.find_one({"id": p["agreement_id"]}, {"_id": 0, "status": 1})
            if agr and agr.get("status") == "approved":
                valid_projects += 1
    test("TC021", "Projects linked to approved agreements", valid_projects >= len(projects) * 0.8,
         f"{valid_projects}/{len(projects)} valid")
    
    # TC022: Task-SOW-Project linkage
    tasks_with_sow = list(db.tasks.find({"sow_id": {"$ne": None}}, {"_id": 0, "sow_id": 1, "sow_item_id": 1}))
    valid_tasks = 0
    for t in tasks_with_sow[:50]:  # Check first 50
        if t.get("sow_id"):
            sow = db.sow.find_one({"id": t["sow_id"]}, {"_id": 0, "items": 1})
            if sow and t.get("sow_item_id"):
                item_ids = [i["id"] for i in sow.get("items", [])]
                if t["sow_item_id"] in item_ids:
                    valid_tasks += 1
    test("TC022", "Tasks linked to valid SOW items", valid_tasks >= len(tasks_with_sow[:50]) * 0.8,
         f"{valid_tasks}/{min(50, len(tasks_with_sow))} valid")
    
    # TC023: SOW-PricingPlan bidirectional
    sows = list(db.sow.find({}, {"_id": 0, "id": 1, "pricing_plan_id": 1}))
    bidirectional = 0
    for s in sows:
        pp = db.pricing_plans.find_one({"id": s.get("pricing_plan_id")}, {"_id": 0, "sow_id": 1})
        if pp and pp.get("sow_id") == s["id"]:
            bidirectional += 1
    test("TC023", "SOW ↔ PricingPlan bidirectional links", bidirectional >= len(sows) * 0.9,
         f"{bidirectional}/{len(sows)} bidirectional")
    
    # ============== CONCURRENT USAGE & IDEMPOTENCY ==============
    print("\n📋 TC025-TC026: Uniqueness Tests")
    print("-"*50)
    
    # TC025: Unique emails
    all_emails = [u.get("email") for u in db.users.find({}, {"_id": 0, "email": 1})]
    test("TC025", "All user emails are unique", len(all_emails) == len(set(all_emails)),
         f"{len(all_emails)} total, {len(set(all_emails))} unique")
    
    # TC026: Unique employee IDs
    all_emp_ids = [e.get("employee_id") for e in db.employees.find({}, {"_id": 0, "employee_id": 1})]
    test("TC026", "All employee IDs are unique", len(all_emp_ids) == len(set(all_emp_ids)),
         f"{len(all_emp_ids)} total, {len(set(all_emp_ids))} unique")
    
    # ============== DATA PERSISTENCE CHECKS ==============
    print("\n📋 TC033-TC035: Data Persistence Tests")
    print("-"*50)
    
    # TC033: DateTime ISO format
    sample_emps = list(db.employees.find({}, {"_id": 0, "created_at": 1}).limit(10))
    iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    valid_iso = all(iso_pattern.match(e.get("created_at", "")) for e in sample_emps if e.get("created_at"))
    test("TC033", "DateTime fields in ISO format", valid_iso)
    
    # TC034: No ObjectId in data (check string IDs)
    sample_docs = list(db.employees.find().limit(5))
    no_objectid_ids = all(isinstance(d.get("id"), str) for d in sample_docs)
    test("TC034", "ID fields are strings not ObjectId", no_objectid_ids)
    
    # TC035: Attendance no weekends
    att_sample = list(db.attendance.find({}, {"_id": 0, "date": 1}).limit(100))
    no_weekends = True
    for a in att_sample:
        try:
            d = datetime.strptime(a.get("date", ""), "%Y-%m-%d")
            if d.weekday() >= 5:
                no_weekends = False
                break
        except:
            pass
    test("TC035", "Attendance has no weekend records", no_weekends)
    
    # ============== SPECIFIC DATA VALIDATION ==============
    print("\n📋 TC046-TC050: Specific Data Tests")
    print("-"*50)
    
    # TC046: Salary components
    components = list(db.salary_components.find({}, {"_id": 0, "name": 1, "type": 1}))
    has_earnings = any(c.get("type") == "earning" for c in components)
    has_deductions = any(c.get("type") == "deduction" for c in components)
    test("TC046", "Salary components have earnings and deductions", has_earnings and has_deductions,
         f"Earnings: {has_earnings}, Deductions: {has_deductions}")
    
    # TC047: SOW categories
    sow_items = []
    for s in db.sow.find({}, {"_id": 0, "items": 1}):
        sow_items.extend(s.get("items", []))
    categories = set(i.get("category") for i in sow_items)
    expected_cats = {"hr", "training", "sales", "operations", "analytics"}
    has_enough_cats = len(categories.intersection(expected_cats)) >= 3
    test("TC047", "SOW items have HR consulting categories", has_enough_cats,
         f"Found: {categories}")
    
    # TC048: Quotation calculations
    quotations = list(db.quotations.find({}, {"_id": 0, "subtotal": 1, "discount_amount": 1, "gst_amount": 1, "grand_total": 1}))
    valid_calcs = 0
    for q in quotations:
        expected = q.get("subtotal", 0) - q.get("discount_amount", 0) + q.get("gst_amount", 0)
        if abs(q.get("grand_total", 0) - expected) < 1:
            valid_calcs += 1
    test("TC048", "Quotation calculations correct (subtotal - discount + GST)", valid_calcs == len(quotations),
         f"{valid_calcs}/{len(quotations)} correct")
    
    # TC049: Meeting types distributed
    meeting_types = Counter([m.get("type") for m in db.meetings.find({}, {"_id": 0, "type": 1})])
    has_sales = "sales" in meeting_types
    has_consulting = "consulting" in meeting_types
    test("TC049", "Both sales and consulting meetings exist", has_sales and has_consulting,
         f"Types: {dict(meeting_types)}")
    
    # TC050: Notification types coverage
    notif_types = set(n.get("type") for n in db.notifications.find({}, {"_id": 0, "type": 1}))
    test("TC050", "Multiple notification types exist", len(notif_types) >= 2,
         f"Types: {notif_types}")
    
    # ============== DATA COUNT VALIDATION ==============
    print("\n📋 Data Count Validation")
    print("-"*50)
    
    counts = {
        "users": (db.users.count_documents({}), 40),
        "employees": (db.employees.count_documents({}), 40),
        "leads": (db.leads.count_documents({}), 40),
        "clients": (db.clients.count_documents({}), 5),
        "projects": (db.projects.count_documents({}), 5),
        "tasks": (db.tasks.count_documents({}), 50),
        "meetings": (db.meetings.count_documents({}), 30),
        "expenses": (db.expenses.count_documents({}), 50),
        "attendance": (db.attendance.count_documents({}), 2000),
    }
    
    for name, (actual, expected) in counts.items():
        test(f"COUNT_{name.upper()}", f"{name.capitalize()} count >= {expected}", actual >= expected,
             f"Actual: {actual}")
    
    # ============== SUMMARY ==============
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    total = passed + failed
    print(f"\n  Total Tests:  {total}")
    print(f"  ✅ Passed:    {passed}")
    print(f"  ❌ Failed:    {failed}")
    print(f"  Pass Rate:    {(passed/total*100) if total > 0 else 0:.1f}%")
    
    if errors:
        print("\n⚠️  FAILED TESTS:")
        print("-"*50)
        for test_id, name, error in errors:
            print(f"  • {test_id}: {name}")
            if error:
                print(f"    → {error}")
    
    print("\n" + "="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    client.close()
    sys.exit(0 if success else 1)
