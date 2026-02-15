#!/usr/bin/env python3
"""
Comprehensive Data Seeding Script for HR Consulting Management Application
Generates realistic Indian HR Consulting-related data across all modules
"""

import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to MongoDB
mongo_url = os.environ.get('MONGO_URL')
db_name = os.environ.get('DB_NAME')

# ============== INDIAN DATA CONSTANTS ==============

# Indian Names
INDIAN_FIRST_NAMES_MALE = [
    "Rajesh", "Amit", "Suresh", "Vikram", "Arun", "Prakash", "Sanjay", "Rahul",
    "Anand", "Deepak", "Nitin", "Manoj", "Ajay", "Vinod", "Ashok", "Ravi",
    "Kiran", "Gaurav", "Manish", "Pradeep", "Ramesh", "Dinesh", "Sunil", "Mukesh",
    "Pankaj", "Naveen", "Arvind", "Sandeep", "Jitendra", "Yogesh"
]

INDIAN_FIRST_NAMES_FEMALE = [
    "Priya", "Sneha", "Pooja", "Neha", "Anjali", "Swati", "Kavita", "Sunita",
    "Meera", "Divya", "Ritu", "Anita", "Shweta", "Pallavi", "Rekha", "Lakshmi",
    "Deepika", "Manisha", "Nisha", "Preeti", "Rashmi", "Shalini", "Archana", "Geeta",
    "Mamta", "Vandana", "Seema", "Jyoti", "Sapna", "Komal"
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Kumar", "Gupta", "Patel", "Reddy", "Rao",
    "Naidu", "Iyer", "Nair", "Menon", "Pillai", "Choudhary", "Malhotra", "Kapoor",
    "Joshi", "Desai", "Mehta", "Shah", "Bhat", "Kulkarni", "Patil", "Deshpande",
    "Agarwal", "Bansal", "Mittal", "Garg", "Saxena", "Tiwari", "Pandey", "Mishra"
]

# Indian Companies (Manufacturing, IT, Retail, Pharma - typical HR consulting clients)
INDIAN_COMPANIES = [
    {"name": "Tata Steel Limited", "industry": "Manufacturing", "city": "Jamshedpur", "state": "Jharkhand"},
    {"name": "Reliance Industries Ltd", "industry": "Conglomerate", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Infosys Limited", "industry": "IT Services", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Wipro Technologies", "industry": "IT Services", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "HCL Technologies", "industry": "IT Services", "city": "Noida", "state": "Uttar Pradesh"},
    {"name": "Mahindra & Mahindra", "industry": "Automotive", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Bajaj Auto Limited", "industry": "Automotive", "city": "Pune", "state": "Maharashtra"},
    {"name": "Hero MotoCorp", "industry": "Automotive", "city": "New Delhi", "state": "Delhi"},
    {"name": "Sun Pharmaceutical", "industry": "Pharmaceuticals", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Dr. Reddy's Laboratories", "industry": "Pharmaceuticals", "city": "Hyderabad", "state": "Telangana"},
    {"name": "Cipla Limited", "industry": "Pharmaceuticals", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Asian Paints Ltd", "industry": "Manufacturing", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Godrej Industries", "industry": "Conglomerate", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Larsen & Toubro", "industry": "Engineering", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "JSW Steel Limited", "industry": "Manufacturing", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Bharti Airtel", "industry": "Telecom", "city": "New Delhi", "state": "Delhi"},
    {"name": "HDFC Bank", "industry": "Banking", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "ICICI Bank", "industry": "Banking", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Axis Bank", "industry": "Banking", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "ITC Limited", "industry": "FMCG", "city": "Kolkata", "state": "West Bengal"},
    {"name": "Hindustan Unilever", "industry": "FMCG", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Nestle India", "industry": "FMCG", "city": "Gurgaon", "state": "Haryana"},
    {"name": "Dabur India", "industry": "FMCG", "city": "Ghaziabad", "state": "Uttar Pradesh"},
    {"name": "Marico Limited", "industry": "FMCG", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Titan Company", "industry": "Retail", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Raymond Limited", "industry": "Textiles", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Adani Group", "industry": "Conglomerate", "city": "Ahmedabad", "state": "Gujarat"},
    {"name": "Vedanta Limited", "industry": "Mining", "city": "New Delhi", "state": "Delhi"},
    {"name": "Power Grid Corporation", "industry": "Utilities", "city": "Gurgaon", "state": "Haryana"},
    {"name": "NTPC Limited", "industry": "Utilities", "city": "New Delhi", "state": "Delhi"},
]

# SME Companies (typical HR consulting clients)
INDIAN_SME_COMPANIES = [
    {"name": "Prism Engineering Solutions", "industry": "Engineering", "city": "Pune", "state": "Maharashtra"},
    {"name": "Vertex Technologies Pvt Ltd", "industry": "IT Services", "city": "Hyderabad", "state": "Telangana"},
    {"name": "Sunrise Manufacturing", "industry": "Manufacturing", "city": "Chennai", "state": "Tamil Nadu"},
    {"name": "Global Trade Associates", "industry": "Import/Export", "city": "Mumbai", "state": "Maharashtra"},
    {"name": "Evergreen Agro Products", "industry": "Agriculture", "city": "Nagpur", "state": "Maharashtra"},
    {"name": "Horizon Logistics India", "industry": "Logistics", "city": "Bengaluru", "state": "Karnataka"},
    {"name": "Matrix Pharmaceuticals", "industry": "Pharmaceuticals", "city": "Ahmedabad", "state": "Gujarat"},
    {"name": "Pioneer Textiles Mills", "industry": "Textiles", "city": "Coimbatore", "state": "Tamil Nadu"},
    {"name": "Kaveri Construction Co", "industry": "Construction", "city": "Hyderabad", "state": "Telangana"},
    {"name": "Shanti Paper Industries", "industry": "Manufacturing", "city": "Vapi", "state": "Gujarat"},
    {"name": "Aarav Auto Components", "industry": "Automotive", "city": "Gurgaon", "state": "Haryana"},
    {"name": "Nirmaan Infra Projects", "industry": "Infrastructure", "city": "Noida", "state": "Uttar Pradesh"},
    {"name": "Dhanush Food Processing", "industry": "Food Processing", "city": "Ludhiana", "state": "Punjab"},
    {"name": "Sagar Marine Exports", "industry": "Seafood", "city": "Kochi", "state": "Kerala"},
    {"name": "Technocraft Systems", "industry": "IT Services", "city": "Jaipur", "state": "Rajasthan"},
]

# Job Titles for HR Consulting Context
JOB_TITLES_SENIOR = [
    "Managing Director", "CEO", "Chief Executive Officer", "Director", "Vice President",
    "Chief HR Officer", "CHRO", "Chief People Officer", "Group HR Head", "President"
]

JOB_TITLES_MID = [
    "HR Director", "HR Head", "General Manager HR", "VP Human Resources", "HR Business Partner",
    "Head of Talent Acquisition", "Learning & Development Head", "Compensation & Benefits Manager",
    "Employee Relations Manager", "HR Operations Manager"
]

JOB_TITLES_JUNIOR = [
    "HR Manager", "Senior HR Executive", "Talent Acquisition Lead", "Training Manager",
    "Recruitment Manager", "HR Generalist", "HR Analyst", "Payroll Manager"
]

# HR Consulting Service Categories
HR_CONSULTING_SERVICES = {
    "hr": [
        {"title": "HR Policy Development", "deliverables": ["Employee Handbook", "Leave Policy", "Code of Conduct", "Anti-Harassment Policy"]},
        {"title": "Performance Management System", "deliverables": ["KRA Framework", "Appraisal Process", "360 Feedback Template", "PIP Guidelines"]},
        {"title": "Compensation Benchmarking", "deliverables": ["Salary Survey Analysis", "Pay Structure Design", "Variable Pay Framework", "Benefits Review"]},
        {"title": "HR Audit & Compliance", "deliverables": ["Statutory Compliance Checklist", "Gap Analysis Report", "Remediation Plan", "Audit Certificate"]},
        {"title": "Employee Engagement Survey", "deliverables": ["Survey Design", "Data Collection", "Analysis Report", "Action Plan"]},
        {"title": "HRIS Implementation Support", "deliverables": ["Requirements Document", "Vendor Evaluation", "Implementation Plan", "Training Material"]},
    ],
    "training": [
        {"title": "Leadership Development Program", "deliverables": ["Curriculum Design", "Training Modules", "Assessment Tools", "Certification Framework"]},
        {"title": "Soft Skills Training", "deliverables": ["Communication Skills Module", "Team Building Workshop", "Time Management Program", "Presentation Skills"]},
        {"title": "Technical Skills Assessment", "deliverables": ["Skills Matrix", "Gap Analysis", "Training Needs Identification", "ROI Measurement"]},
        {"title": "New Manager Training", "deliverables": ["Transition Toolkit", "Coaching Sessions", "Peer Learning Groups", "Progress Tracking"]},
        {"title": "Compliance Training", "deliverables": ["POSH Training", "Safety Training", "Ethics Workshop", "Compliance Certification"]},
    ],
    "sales": [
        {"title": "Sales Force Effectiveness", "deliverables": ["Sales Process Mapping", "Territory Design", "Incentive Structure", "CRM Implementation"]},
        {"title": "Sales Training Program", "deliverables": ["Product Knowledge Modules", "Objection Handling Guide", "Negotiation Skills", "Closing Techniques"]},
        {"title": "Channel Partner Management", "deliverables": ["Partner Onboarding SOP", "Performance Metrics", "Partner Portal Design", "Engagement Calendar"]},
    ],
    "operations": [
        {"title": "Process Optimization", "deliverables": ["Current State Mapping", "Gap Analysis", "To-Be Process Design", "Implementation Roadmap"]},
        {"title": "Quality Management System", "deliverables": ["ISO Documentation", "Quality Manual", "Audit Checklist", "Continuous Improvement Plan"]},
        {"title": "Supply Chain Consulting", "deliverables": ["Vendor Assessment", "Inventory Optimization", "Logistics Review", "Cost Reduction Plan"]},
    ],
    "analytics": [
        {"title": "HR Analytics Dashboard", "deliverables": ["KPI Definition", "Data Architecture", "Dashboard Design", "Reporting Framework"]},
        {"title": "Workforce Planning", "deliverables": ["Demand Forecasting Model", "Supply Analysis", "Succession Planning", "Talent Pipeline Review"]},
        {"title": "Attrition Analysis", "deliverables": ["Exit Interview Analysis", "Predictive Model", "Retention Strategy", "Benchmark Report"]},
    ],
    "digital_marketing": [
        {"title": "Employer Branding", "deliverables": ["EVP Development", "Career Page Design", "Social Media Strategy", "Employee Stories Campaign"]},
        {"title": "Recruitment Marketing", "deliverables": ["Job Description Optimization", "Candidate Journey Mapping", "Source Channel Analysis", "Conversion Tracking"]},
    ],
}

# Indian Cities and States
INDIAN_CITIES = [
    {"city": "Mumbai", "state": "Maharashtra"},
    {"city": "Delhi", "state": "Delhi"},
    {"city": "Bengaluru", "state": "Karnataka"},
    {"city": "Hyderabad", "state": "Telangana"},
    {"city": "Chennai", "state": "Tamil Nadu"},
    {"city": "Kolkata", "state": "West Bengal"},
    {"city": "Pune", "state": "Maharashtra"},
    {"city": "Ahmedabad", "state": "Gujarat"},
    {"city": "Jaipur", "state": "Rajasthan"},
    {"city": "Lucknow", "state": "Uttar Pradesh"},
    {"city": "Chandigarh", "state": "Chandigarh"},
    {"city": "Gurgaon", "state": "Haryana"},
    {"city": "Noida", "state": "Uttar Pradesh"},
    {"city": "Indore", "state": "Madhya Pradesh"},
    {"city": "Kochi", "state": "Kerala"},
    {"city": "Coimbatore", "state": "Tamil Nadu"},
    {"city": "Nagpur", "state": "Maharashtra"},
    {"city": "Bhopal", "state": "Madhya Pradesh"},
    {"city": "Vadodara", "state": "Gujarat"},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh"},
]

# Indian Banks for Employee Bank Details
INDIAN_BANKS = [
    "State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank",
    "Bank of Baroda", "Kotak Mahindra Bank", "IndusInd Bank", "Yes Bank", "IDFC First Bank",
    "Canara Bank", "Union Bank of India", "Bank of India", "Central Bank of India", "Indian Bank"
]

# Departments
DEPARTMENTS = ["HR", "Sales", "Operations", "Training", "Analytics", "Finance", "IT", "Marketing", "Admin"]

# Designations specific to D&V Consulting
DESIGNATIONS = [
    "Principal Consultant", "Lead Consultant", "Senior Consultant", "Consultant",
    "Lean Consultant", "Project Manager", "Account Manager", "HR Executive",
    "Training Coordinator", "Business Analyst", "Research Associate"
]

# Lead Sources
LEAD_SOURCES = [
    "LinkedIn", "Referral", "Website", "Cold Call", "Trade Show", "Conference",
    "Partner", "Social Media", "Google Ads", "Industry Association", "Networking Event"
]

# ============== HELPER FUNCTIONS ==============

def generate_indian_name(gender="random"):
    if gender == "random":
        gender = random.choice(["male", "female"])
    if gender == "male":
        first_name = random.choice(INDIAN_FIRST_NAMES_MALE)
    else:
        first_name = random.choice(INDIAN_FIRST_NAMES_FEMALE)
    last_name = random.choice(INDIAN_LAST_NAMES)
    return first_name, last_name

def generate_indian_phone():
    """Generate Indian mobile number"""
    prefixes = ["98", "99", "97", "96", "95", "94", "93", "91", "90", "88", "87", "86", "85", "84", "83", "82", "81", "80", "79", "78", "77", "76", "75", "74", "73", "72", "71", "70"]
    return f"+91 {random.choice(prefixes)}{random.randint(10000000, 99999999)}"

def generate_ifsc_code(bank_name):
    """Generate IFSC code based on bank"""
    bank_codes = {
        "State Bank of India": "SBIN",
        "HDFC Bank": "HDFC",
        "ICICI Bank": "ICIC",
        "Axis Bank": "UTIB",
        "Punjab National Bank": "PUNB",
        "Bank of Baroda": "BARB",
        "Kotak Mahindra Bank": "KKBK",
        "IndusInd Bank": "INDB",
        "Yes Bank": "YESB",
        "IDFC First Bank": "IDFB",
        "Canara Bank": "CNRB",
        "Union Bank of India": "UBIN",
        "Bank of India": "BKID",
        "Central Bank of India": "CBIN",
        "Indian Bank": "IDIB",
    }
    code = bank_codes.get(bank_name, "SBIN")
    return f"{code}000{random.randint(1000, 9999)}"

def generate_email(first_name, last_name, domain):
    """Generate email address"""
    # Clean domain - remove special characters
    clean_domain = ''.join(c for c in domain if c.isalnum() or c == '.')
    if not clean_domain.endswith('.com'):
        clean_domain = clean_domain + '.com'
    
    formats = [
        f"{first_name.lower()}.{last_name.lower()}@{clean_domain}",
        f"{first_name.lower()}{last_name.lower()[0]}@{clean_domain}",
        f"{first_name.lower()[0]}{last_name.lower()}@{clean_domain}",
    ]
    return random.choice(formats)

def random_date_between(start_date, end_date):
    """Generate random date between two dates"""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def get_password_hash(password):
    return pwd_context.hash(password)

# ============== DATA GENERATION FUNCTIONS ==============

async def seed_users(db):
    """Create users with different roles"""
    print("Seeding Users...")
    
    users = []
    
    # Admin User (already exists from handoff, but ensuring)
    admin_exists = await db.users.find_one({"email": "admin@company.com"})
    if not admin_exists:
        admin = {
            "id": str(uuid.uuid4()),
            "email": "admin@company.com",
            "full_name": "System Administrator",
            "role": "admin",
            "department": "Admin",
            "is_active": True,
            "hashed_password": get_password_hash("admin123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin)
        users.append(admin)
    
    # Create employees with user accounts
    employee_users = [
        # Principal Consultants
        {"role": "principal_consultant", "department": "Consulting", "count": 3},
        # Lead Consultants  
        {"role": "lead_consultant", "department": "Consulting", "count": 4},
        # Senior Consultants
        {"role": "senior_consultant", "department": "Consulting", "count": 5},
        # Consultants
        {"role": "consultant", "department": "Consulting", "count": 8},
        # Lean Consultants
        {"role": "lean_consultant", "department": "Consulting", "count": 6},
        # Project Managers
        {"role": "project_manager", "department": "Delivery", "count": 3},
        # Account Managers / Sales
        {"role": "account_manager", "department": "Sales", "count": 4},
        {"role": "executive", "department": "Sales", "count": 3},
        # HR Team
        {"role": "hr_manager", "department": "HR", "count": 1},
        {"role": "hr_executive", "department": "HR", "count": 2},
        # Manager role
        {"role": "manager", "department": "Operations", "count": 2},
    ]
    
    created_users = []
    for config in employee_users:
        for i in range(config["count"]):
            gender = random.choice(["male", "female"])
            first_name, last_name = generate_indian_name(gender)
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@dvconsulting.co.in"
            
            # Check if email exists
            existing = await db.users.find_one({"email": email})
            if existing:
                continue
            
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "full_name": f"{first_name} {last_name}",
                "role": config["role"],
                "department": config["department"],
                "is_active": True,
                "hashed_password": get_password_hash("password123"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
            created_users.append(user)
    
    print(f"  Created {len(created_users)} users")
    return created_users

async def seed_employees(db):
    """Create employee records linked to users"""
    print("Seeding Employees...")
    
    users = await db.users.find({"role": {"$ne": "admin"}}, {"_id": 0}).to_list(100)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    employees = []
    emp_counter = 1
    
    # First create principal consultants (they will be reporting managers)
    principal_users = [u for u in users if u["role"] == "principal_consultant"]
    other_users = [u for u in users if u["role"] != "principal_consultant"]
    
    principal_employees = []
    
    for user in principal_users:
        names = user["full_name"].split()
        first_name = names[0]
        last_name = names[-1] if len(names) > 1 else ""
        
        bank_name = random.choice(INDIAN_BANKS)
        city_data = random.choice(INDIAN_CITIES)
        joining_date = random_date_between(
            datetime(2018, 1, 1, tzinfo=timezone.utc),
            datetime(2022, 12, 31, tzinfo=timezone.utc)
        )
        
        employee = {
            "id": str(uuid.uuid4()),
            "employee_id": f"DVC{emp_counter:03d}",
            "first_name": first_name,
            "last_name": last_name,
            "email": user["email"],
            "phone": generate_indian_phone(),
            "personal_email": f"{first_name.lower()}.personal@gmail.com",
            "department": user.get("department", "Consulting"),
            "designation": "Principal Consultant",
            "employment_type": "full_time",
            "joining_date": joining_date.isoformat(),
            "reporting_manager_id": None,  # Reports to admin
            "reporting_manager_name": "System Administrator",
            "salary": random.randint(150000, 250000),
            "bank_details": {
                "account_number": str(random.randint(10000000000, 99999999999)),
                "ifsc_code": generate_ifsc_code(bank_name),
                "bank_name": bank_name,
                "branch": f"{city_data['city']} Main Branch",
                "account_holder_name": user["full_name"]
            },
            "leave_balance": {
                "casual_leave": 12,
                "sick_leave": 6,
                "earned_leave": 15,
                "used_casual": random.randint(0, 5),
                "used_sick": random.randint(0, 2),
                "used_earned": random.randint(0, 8)
            },
            "documents": [],
            "user_id": user["id"],
            "role": user["role"],
            "is_active": True,
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.employees.insert_one(employee)
        principal_employees.append(employee)
        employees.append(employee)
        emp_counter += 1
    
    # Create other employees with reporting structure
    for user in other_users:
        names = user["full_name"].split()
        first_name = names[0]
        last_name = names[-1] if len(names) > 1 else ""
        
        # Assign reporting manager based on role
        if user["role"] in ["lead_consultant", "project_manager", "hr_manager", "manager"]:
            # Report to principal consultant
            reporting_manager = random.choice(principal_employees) if principal_employees else None
        else:
            # Report to lead consultant or principal
            lead_employees = [e for e in employees if e.get("role") in ["lead_consultant", "principal_consultant"]]
            reporting_manager = random.choice(lead_employees) if lead_employees else (random.choice(principal_employees) if principal_employees else None)
        
        bank_name = random.choice(INDIAN_BANKS)
        city_data = random.choice(INDIAN_CITIES)
        
        # Salary based on role
        salary_ranges = {
            "lead_consultant": (100000, 150000),
            "senior_consultant": (80000, 120000),
            "consultant": (50000, 80000),
            "lean_consultant": (35000, 50000),
            "project_manager": (100000, 150000),
            "account_manager": (70000, 100000),
            "executive": (40000, 70000),
            "hr_manager": (80000, 120000),
            "hr_executive": (35000, 50000),
            "manager": (90000, 130000),
        }
        salary_range = salary_ranges.get(user["role"], (40000, 60000))
        
        designation_map = {
            "lead_consultant": "Lead Consultant",
            "senior_consultant": "Senior Consultant",
            "consultant": "Consultant",
            "lean_consultant": "Lean Consultant",
            "project_manager": "Project Manager",
            "account_manager": "Account Manager",
            "executive": "Sales Executive",
            "hr_manager": "HR Manager",
            "hr_executive": "HR Executive",
            "manager": "Operations Manager",
        }
        
        joining_date = random_date_between(
            datetime(2019, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 6, 30, tzinfo=timezone.utc)
        )
        
        employee = {
            "id": str(uuid.uuid4()),
            "employee_id": f"DVC{emp_counter:03d}",
            "first_name": first_name,
            "last_name": last_name,
            "email": user["email"],
            "phone": generate_indian_phone(),
            "personal_email": f"{first_name.lower()}.{last_name.lower()}@gmail.com",
            "department": user.get("department", "Consulting"),
            "designation": designation_map.get(user["role"], "Consultant"),
            "employment_type": "full_time",
            "joining_date": joining_date.isoformat(),
            "reporting_manager_id": reporting_manager["id"] if reporting_manager else None,
            "reporting_manager_name": f"{reporting_manager['first_name']} {reporting_manager['last_name']}" if reporting_manager else None,
            "salary": random.randint(*salary_range),
            "bank_details": {
                "account_number": str(random.randint(10000000000, 99999999999)),
                "ifsc_code": generate_ifsc_code(bank_name),
                "bank_name": bank_name,
                "branch": f"{city_data['city']} Branch",
                "account_holder_name": user["full_name"]
            },
            "leave_balance": {
                "casual_leave": 12,
                "sick_leave": 6,
                "earned_leave": 15,
                "used_casual": random.randint(0, 6),
                "used_sick": random.randint(0, 3),
                "used_earned": random.randint(0, 10)
            },
            "documents": [],
            "user_id": user["id"],
            "role": user["role"],
            "is_active": True,
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.employees.insert_one(employee)
        employees.append(employee)
        emp_counter += 1
    
    print(f"  Created {len(employees)} employees")
    return employees

async def seed_leads(db):
    """Create leads from Indian companies"""
    print("Seeding Leads...")
    
    sales_users = await db.users.find(
        {"role": {"$in": ["executive", "account_manager", "admin"]}},
        {"_id": 0}
    ).to_list(20)
    
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    leads = []
    
    # Large companies as leads
    for company in INDIAN_COMPANIES:
        gender = random.choice(["male", "female"])
        first_name, last_name = generate_indian_name(gender)
        job_title = random.choice(JOB_TITLES_SENIOR + JOB_TITLES_MID)
        
        # Determine lead status
        status_weights = {
            "new": 0.15,
            "contacted": 0.20,
            "qualified": 0.25,
            "proposal": 0.20,
            "agreement": 0.10,
            "closed": 0.08,
            "lost": 0.02
        }
        status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
        
        sales_person = random.choice(sales_users) if sales_users else admin_user
        
        # Generate clean company domain
        clean_company = ''.join(c for c in company["name"].lower() if c.isalnum())[:12]
        
        lead = {
            "id": str(uuid.uuid4()),
            "lead_owner": sales_person["id"],
            "first_name": first_name,
            "last_name": last_name,
            "company": company["name"],
            "contact_person": f"{first_name} {last_name}",
            "job_title": job_title,
            "email": f"{first_name.lower()}.{last_name.lower()}@{clean_company}.com",
            "phone": generate_indian_phone(),
            "linkedin_url": f"https://www.linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(1000,9999)}",
            "street": f"{random.randint(1, 500)}, {random.choice(['MG Road', 'Park Street', 'Ring Road', 'Industrial Area', 'Business Park', 'Tech Park'])}",
            "city": company["city"],
            "state": company["state"],
            "zip_code": str(random.randint(100000, 999999)),
            "country": "India",
            "lead_source": random.choice(LEAD_SOURCES),
            "status": status,
            "sales_status": random.choice(["call_back", "send_details", "schedule_meeting", "meeting_done", None]),
            "product_interest": random.choice([
                "HR Consulting", "Leadership Training", "Performance Management", 
                "Compensation Benchmarking", "HR Policy Development", "Talent Acquisition"
            ]),
            "notes": f"Key contact from {company['industry']} sector. Interested in HR transformation.",
            "assigned_to": sales_person["id"],
            "created_by": admin_user["id"],
            "lead_score": random.randint(20, 95),
            "score_breakdown": {
                "title_score": random.randint(15, 40),
                "contact_score": random.randint(10, 30),
                "engagement_score": random.randint(5, 30),
                "total": random.randint(30, 100)
            },
            "created_at": random_date_between(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime.now(timezone.utc)
            ).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "enriched_at": None
        }
        
        await db.leads.insert_one(lead)
        leads.append(lead)
    
    # SME companies as leads
    for company in INDIAN_SME_COMPANIES:
        gender = random.choice(["male", "female"])
        first_name, last_name = generate_indian_name(gender)
        job_title = random.choice(JOB_TITLES_MID + JOB_TITLES_JUNIOR)
        
        status = random.choices(
            ["new", "contacted", "qualified", "proposal", "agreement", "closed", "lost"],
            weights=[0.20, 0.25, 0.25, 0.15, 0.08, 0.05, 0.02]
        )[0]
        
        sales_person = random.choice(sales_users) if sales_users else admin_user
        
        # Generate clean company domain for SME
        clean_sme = ''.join(c for c in company["name"].lower() if c.isalnum())[:10]
        
        lead = {
            "id": str(uuid.uuid4()),
            "lead_owner": sales_person["id"],
            "first_name": first_name,
            "last_name": last_name,
            "company": company["name"],
            "contact_person": f"{first_name} {last_name}",
            "job_title": job_title,
            "email": f"{first_name.lower()}.{last_name.lower()}@{clean_sme}.com",
            "phone": generate_indian_phone(),
            "linkedin_url": f"https://www.linkedin.com/in/{first_name.lower()}{last_name.lower()}",
            "street": f"{random.choice(['Plot', 'Unit', 'Office'])} {random.randint(1, 200)}, {random.choice(['Industrial Estate', 'Business Center', 'Corporate Park'])}",
            "city": company["city"],
            "state": company["state"],
            "zip_code": str(random.randint(100000, 999999)),
            "country": "India",
            "lead_source": random.choice(LEAD_SOURCES),
            "status": status,
            "sales_status": random.choice(["call_back", "send_details", "schedule_meeting", None]),
            "product_interest": random.choice([
                "HR Policy Setup", "Training Programs", "Recruitment Support",
                "Payroll Consulting", "HR Audit", "Employee Engagement"
            ]),
            "notes": f"SME in {company['industry']}. Looking for comprehensive HR support.",
            "assigned_to": sales_person["id"],
            "created_by": admin_user["id"],
            "lead_score": random.randint(15, 80),
            "score_breakdown": {
                "title_score": random.randint(10, 25),
                "contact_score": random.randint(10, 30),
                "engagement_score": random.randint(5, 25),
                "total": random.randint(25, 80)
            },
            "created_at": random_date_between(
                datetime(2024, 3, 1, tzinfo=timezone.utc),
                datetime.now(timezone.utc)
            ).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "enriched_at": None
        }
        
        await db.leads.insert_one(lead)
        leads.append(lead)
    
    print(f"  Created {len(leads)} leads")
    return leads

async def seed_clients(db):
    """Create clients from closed leads"""
    print("Seeding Clients...")
    
    closed_leads = await db.leads.find({"status": "closed"}, {"_id": 0}).to_list(50)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    sales_users = await db.users.find({"role": {"$in": ["executive", "account_manager"]}}, {"_id": 0}).to_list(10)
    
    clients = []
    
    for lead in closed_leads:
        sales_person = random.choice(sales_users) if sales_users else admin_user
        
        # Generate multiple contacts for the client
        contacts = [
            {
                "name": lead.get("contact_person", f"{lead['first_name']} {lead['last_name']}"),
                "designation": lead.get("job_title", "HR Head"),
                "email": lead.get("email"),
                "phone": lead.get("phone"),
                "is_primary": True
            }
        ]
        
        # Add 1-2 more contacts
        for _ in range(random.randint(1, 2)):
            gender = random.choice(["male", "female"])
            fn, ln = generate_indian_name(gender)
            contacts.append({
                "name": f"{fn} {ln}",
                "designation": random.choice(["HR Manager", "Finance Head", "Admin Manager", "CEO Office"]),
                "email": f"{fn.lower()}.{ln.lower()}@{lead['company'].lower().replace(' ', '')[:8]}.com",
                "phone": generate_indian_phone(),
                "is_primary": False
            })
        
        # Revenue history
        revenue_history = []
        for year in [2023, 2024]:
            for quarter in range(1, 5):
                if year == 2024 and quarter > 3:
                    continue
                revenue_history.append({
                    "year": year,
                    "quarter": quarter,
                    "amount": random.randint(100000, 1500000),
                    "currency": "INR",
                    "notes": f"Q{quarter} {year} engagement"
                })
        
        client = {
            "id": str(uuid.uuid4()),
            "company_name": lead["company"],
            "industry": next((c["industry"] for c in INDIAN_COMPANIES + INDIAN_SME_COMPANIES if c["name"] == lead["company"]), "General"),
            "location": lead.get("city", "Mumbai"),
            "city": lead.get("city", "Mumbai"),
            "state": lead.get("state", "Maharashtra"),
            "country": "India",
            "address": lead.get("street", ""),
            "website": f"www.{lead['company'].lower().replace(' ', '').replace('&', '')[:15]}.com",
            "contacts": contacts,
            "revenue_history": revenue_history,
            "business_start_date": random_date_between(
                datetime(2022, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 6, 30, tzinfo=timezone.utc)
            ).isoformat(),
            "sales_person_id": sales_person["id"],
            "sales_person_name": sales_person["full_name"],
            "lead_id": lead["id"],
            "agreement_id": None,  # Will be linked when agreements are created
            "notes": f"Active client from {lead['company']}. Engaged for HR consulting services.",
            "is_active": True,
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.clients.insert_one(client)
        clients.append(client)
    
    print(f"  Created {len(clients)} clients")
    return clients

async def seed_pricing_plans_and_sow(db):
    """Create pricing plans, SOWs, quotations, and agreements for qualified/proposal/closed leads"""
    print("Seeding Pricing Plans, SOW, Quotations & Agreements...")
    
    qualified_leads = await db.leads.find(
        {"status": {"$in": ["qualified", "proposal", "agreement", "closed"]}},
        {"_id": 0}
    ).to_list(100)
    
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    consultants = await db.users.find({"role": {"$in": ["consultant", "senior_consultant", "lead_consultant"]}}, {"_id": 0}).to_list(20)
    
    pricing_plans = []
    sows = []
    quotations = []
    agreements = []
    
    quotation_counter = 1
    agreement_counter = 1
    
    for lead in qualified_leads:
        # Create Pricing Plan
        duration_months = random.choice([3, 6, 9, 12])
        duration_type = {3: "quarterly", 6: "half_yearly", 9: "custom", 12: "yearly"}.get(duration_months, "custom")
        
        consultant_types = ["lead", "lean", "principal"]
        consultant_allocations = []
        for ctype in random.sample(consultant_types, k=random.randint(1, 3)):
            consultant_allocations.append({
                "consultant_type": ctype,
                "count": random.randint(1, 2),
                "meetings": random.randint(4, 24),
                "hours": random.randint(20, 100),
                "rate_per_meeting": random.choice([10000, 12500, 15000, 18000])
            })
        
        total_meetings = sum(c["meetings"] for c in consultant_allocations)
        base_amount = sum(c["meetings"] * c["rate_per_meeting"] for c in consultant_allocations)
        discount = random.choice([0, 5, 10, 15])
        gst = 18
        discount_amount = base_amount * (discount / 100)
        gst_amount = (base_amount - discount_amount) * (gst / 100)
        total_amount = base_amount - discount_amount + gst_amount
        
        pricing_plan = {
            "id": str(uuid.uuid4()),
            "lead_id": lead["id"],
            "project_duration_type": duration_type,
            "project_duration_months": duration_months,
            "payment_schedule": random.choice(["monthly", "quarterly", "milestone"]),
            "consultants": consultant_allocations,
            "sow_id": None,
            "base_amount": base_amount,
            "discount_percentage": discount,
            "gst_percentage": gst,
            "total_amount": total_amount,
            "growth_consulting_plan": random.choice(["Basic", "Standard", "Premium", None]),
            "growth_guarantee": random.choice(["10% improvement", "20% efficiency gain", None]),
            "is_active": True,
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.pricing_plans.insert_one(pricing_plan)
        pricing_plans.append(pricing_plan)
        
        # Create SOW for this pricing plan
        categories = random.sample(list(HR_CONSULTING_SERVICES.keys()), k=random.randint(2, 4))
        sow_items = []
        item_order = 0
        
        for category in categories:
            services = HR_CONSULTING_SERVICES[category]
            selected_services = random.sample(services, k=min(len(services), random.randint(1, 3)))
            
            for service in selected_services:
                assigned_consultant = random.choice(consultants) if consultants else None
                
                sow_item = {
                    "id": str(uuid.uuid4()),
                    "category": category,
                    "sub_category": None,
                    "title": service["title"],
                    "description": f"Comprehensive {service['title']} service for {lead['company']}",
                    "deliverables": service["deliverables"],
                    "timeline_weeks": random.randint(2, 8),
                    "start_week": item_order * 2,
                    "order": item_order,
                    "status": random.choice(["draft", "pending_review", "approved", "in_progress"]),
                    "status_updated_by": admin_user["id"],
                    "status_updated_at": datetime.now(timezone.utc).isoformat(),
                    "approved_by": admin_user["id"] if random.random() > 0.5 else None,
                    "approved_at": datetime.now(timezone.utc).isoformat() if random.random() > 0.5 else None,
                    "rejection_reason": None,
                    "documents": [],
                    "notes": None,
                    "assigned_consultant_id": assigned_consultant["id"] if assigned_consultant else None,
                    "assigned_consultant_name": assigned_consultant["full_name"] if assigned_consultant else None,
                    "has_backend_support": random.choice([True, False]),
                    "backend_support_id": None,
                    "backend_support_name": None,
                    "backend_support_role": None
                }
                sow_items.append(sow_item)
                item_order += 1
        
        sow = {
            "id": str(uuid.uuid4()),
            "pricing_plan_id": pricing_plan["id"],
            "lead_id": lead["id"],
            "items": sow_items,
            "documents": [],
            "overall_status": random.choice(["draft", "pending_approval", "approved"]),
            "current_version": 1,
            "version_history": [{
                "version": 1,
                "changed_by": admin_user["id"],
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "change_type": "created",
                "changes": {"action": "SOW created"},
                "snapshot": sow_items
            }],
            "is_frozen": lead["status"] in ["agreement", "closed"],
            "frozen_at": datetime.now(timezone.utc).isoformat() if lead["status"] in ["agreement", "closed"] else None,
            "frozen_by": admin_user["id"] if lead["status"] in ["agreement", "closed"] else None,
            "submitted_for_approval": True,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": admin_user["id"],
            "final_approved_by": admin_user["id"] if lead["status"] in ["agreement", "closed"] else None,
            "final_approved_at": datetime.now(timezone.utc).isoformat() if lead["status"] in ["agreement", "closed"] else None,
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.sow.insert_one(sow)
        sows.append(sow)
        
        # Update pricing plan with SOW ID
        await db.pricing_plans.update_one(
            {"id": pricing_plan["id"]},
            {"$set": {"sow_id": sow["id"]}}
        )
        
        # Create Quotation for leads in proposal/agreement/closed status
        if lead["status"] in ["proposal", "agreement", "closed"]:
            quotation = {
                "id": str(uuid.uuid4()),
                "pricing_plan_id": pricing_plan["id"],
                "lead_id": lead["id"],
                "sow_id": sow["id"],
                "quotation_number": f"QUO-2024-{quotation_counter:04d}",
                "version": 1,
                "is_final": lead["status"] in ["agreement", "closed"],
                "status": "accepted" if lead["status"] in ["agreement", "closed"] else "sent",
                "base_rate_per_meeting": 12500,
                "total_meetings": total_meetings,
                "subtotal": base_amount,
                "discount_amount": discount_amount,
                "gst_amount": gst_amount,
                "grand_total": total_amount,
                "notes": f"Quotation for {lead['company']} - {', '.join(categories)} consulting",
                "is_active": True,
                "created_by": admin_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.quotations.insert_one(quotation)
            quotations.append(quotation)
            quotation_counter += 1
            
            # Create Agreement for leads in agreement/closed status
            if lead["status"] in ["agreement", "closed"]:
                start_date = random_date_between(
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2024, 9, 30, tzinfo=timezone.utc)
                )
                end_date = start_date + timedelta(days=duration_months * 30)
                
                agreement = {
                    "id": str(uuid.uuid4()),
                    "quotation_id": quotation["id"],
                    "lead_id": lead["id"],
                    "sow_id": sow["id"],
                    "pricing_plan_id": pricing_plan["id"],
                    "agreement_number": f"AGR-2024-{agreement_counter:04d}",
                    "agreement_type": "standard",
                    "party_name": lead["company"],
                    "company_section": f"Agreement between D&V Business Consulting and {lead['company']}",
                    "confidentiality_clause": "Both parties agree to maintain confidentiality of all proprietary information shared during the engagement.",
                    "nda_clause": "Non-Disclosure Agreement is in effect for a period of 2 years from the date of signing.",
                    "nca_clause": "",
                    "renewal_clause": "This agreement may be renewed upon mutual consent 30 days before expiry.",
                    "conveyance_clause": "Travel and conveyance expenses will be reimbursed at actuals with prior approval.",
                    "project_start_date": start_date.isoformat(),
                    "project_duration_months": duration_months,
                    "team_engagement": f"D&V will deploy a team of {sum(c['count'] for c in consultant_allocations)} consultants for this engagement.",
                    "payment_terms": "Net 15 days",
                    "payment_conditions": "Payment to be made via bank transfer upon receipt of invoice.",
                    "signature_section": "",
                    "sections": [],
                    "special_conditions": None,
                    "signed_date": start_date.isoformat() if lead["status"] == "closed" else None,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "status": "approved" if lead["status"] == "closed" else "pending_approval",
                    "approved_by": admin_user["id"] if lead["status"] == "closed" else None,
                    "approved_at": start_date.isoformat() if lead["status"] == "closed" else None,
                    "rejection_reason": None,
                    "terms_and_conditions": "Standard terms and conditions of D&V Business Consulting apply.",
                    "is_active": True,
                    "created_by": admin_user["id"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.agreements.insert_one(agreement)
                agreements.append(agreement)
                agreement_counter += 1
    
    print(f"  Created {len(pricing_plans)} pricing plans")
    print(f"  Created {len(sows)} SOWs")
    print(f"  Created {len(quotations)} quotations")
    print(f"  Created {len(agreements)} agreements")
    
    return pricing_plans, sows, quotations, agreements

async def seed_projects(db):
    """Create projects from approved agreements"""
    print("Seeding Projects...")
    
    approved_agreements = await db.agreements.find({"status": "approved"}, {"_id": 0}).to_list(50)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    consultants = await db.users.find({"role": {"$in": ["consultant", "senior_consultant", "lead_consultant", "principal_consultant"]}}, {"_id": 0}).to_list(30)
    
    projects = []
    
    for agreement in approved_agreements:
        # Get lead info
        lead = await db.leads.find_one({"id": agreement["lead_id"]}, {"_id": 0})
        if not lead:
            continue
        
        # Get pricing plan for meeting info
        pricing_plan = await db.pricing_plans.find_one({"id": agreement.get("pricing_plan_id")}, {"_id": 0})
        total_meetings = sum(c["meetings"] for c in (pricing_plan.get("consultants", []) if pricing_plan else [])) or random.randint(12, 48)
        
        # Assign consultants
        assigned_consultants = [c["id"] for c in random.sample(consultants, k=min(len(consultants), random.randint(2, 5)))]
        
        start_date = datetime.fromisoformat(agreement["start_date"].replace("Z", "+00:00")) if agreement.get("start_date") else datetime.now(timezone.utc)
        end_date = datetime.fromisoformat(agreement["end_date"].replace("Z", "+00:00")) if agreement.get("end_date") else start_date + timedelta(days=180)
        
        # Calculate delivered meetings based on progress
        days_elapsed = (datetime.now(timezone.utc) - start_date).days
        total_days = (end_date - start_date).days
        progress = min(1.0, days_elapsed / total_days if total_days > 0 else 0)
        delivered = int(total_meetings * progress * random.uniform(0.7, 1.1))
        
        project = {
            "id": str(uuid.uuid4()),
            "name": f"{lead['company']} - HR Consulting Engagement",
            "client_name": lead["company"],
            "lead_id": lead["id"],
            "agreement_id": agreement["id"],
            "project_type": random.choice(["online", "offline", "mixed"]),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "status": "active" if progress < 0.95 else "completed",
            "total_meetings_committed": total_meetings,
            "total_meetings_delivered": min(delivered, total_meetings),
            "number_of_visits": random.randint(2, 15) if random.random() > 0.3 else 0,
            "assigned_consultants": assigned_consultants,
            "assigned_team": assigned_consultants,
            "budget": agreement.get("pricing_plan_id") and pricing_plan.get("total_amount") or random.randint(500000, 2000000),
            "project_value": pricing_plan.get("total_amount") if pricing_plan else random.randint(500000, 2000000),
            "notes": f"Comprehensive HR consulting project for {lead['company']}",
            "created_by": admin_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.projects.insert_one(project)
        projects.append(project)
        
        # Update client with agreement_id
        await db.clients.update_one(
            {"lead_id": lead["id"]},
            {"$set": {"agreement_id": agreement["id"]}}
        )
    
    print(f"  Created {len(projects)} projects")
    return projects

async def seed_tasks(db):
    """Create tasks for projects linked to SOW items"""
    print("Seeding Tasks...")
    
    projects = await db.projects.find({}, {"_id": 0}).to_list(50)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    tasks = []
    
    for project in projects:
        # Get SOW for this project's agreement
        if not project.get("agreement_id"):
            continue
            
        agreement = await db.agreements.find_one({"id": project["agreement_id"]}, {"_id": 0})
        if not agreement or not agreement.get("sow_id"):
            continue
            
        sow = await db.sow.find_one({"id": agreement["sow_id"]}, {"_id": 0})
        if not sow:
            continue
        
        # Create tasks for each SOW item
        task_order = 0
        for sow_item in sow.get("items", []):
            # Create 2-4 tasks per SOW item
            num_tasks = random.randint(2, 4)
            
            start_date = datetime.fromisoformat(project["start_date"].replace("Z", "+00:00"))
            item_start = start_date + timedelta(weeks=sow_item.get("start_week", 0))
            
            for i in range(num_tasks):
                task_start = item_start + timedelta(days=i * 7)
                task_due = task_start + timedelta(days=random.randint(5, 14))
                
                status_weights = {
                    "to_do": 0.15,
                    "in_progress": 0.30,
                    "completed": 0.45,
                    "delayed": 0.05,
                    "blocked": 0.03,
                    "cancelled": 0.02
                }
                status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
                
                task_titles = [
                    f"Prepare {sow_item['title']} documentation",
                    f"Client meeting for {sow_item['title']}",
                    f"Review and finalize {sow_item['title']}",
                    f"Implement {sow_item['title']} recommendations",
                    f"Training session for {sow_item['title']}",
                    f"Quality check for {sow_item['title']} deliverables",
                ]
                
                task = {
                    "id": str(uuid.uuid4()),
                    "project_id": project["id"],
                    "title": random.choice(task_titles),
                    "description": f"Task related to {sow_item['title']} - {sow_item['description'][:100] if sow_item.get('description') else 'No description'}",
                    "category": sow_item.get("category", "general"),
                    "status": status,
                    "priority": random.choice(["low", "medium", "high"]),
                    "assigned_to": sow_item.get("assigned_consultant_id") or (random.choice(project.get("assigned_consultants", [])) if project.get("assigned_consultants") else None),
                    "delegated_to": None,
                    "sow_id": sow["id"],
                    "sow_item_id": sow_item["id"],
                    "sow_item_title": sow_item["title"],
                    "start_date": task_start.isoformat(),
                    "due_date": task_due.isoformat(),
                    "completed_date": task_due.isoformat() if status == "completed" else None,
                    "estimated_hours": random.randint(4, 20),
                    "actual_hours": random.randint(3, 25) if status == "completed" else None,
                    "dependencies": [],
                    "order": task_order,
                    "created_by": admin_user["id"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.tasks.insert_one(task)
                tasks.append(task)
                task_order += 1
    
    print(f"  Created {len(tasks)} tasks")
    return tasks

async def seed_meetings(db):
    """Create meetings for projects"""
    print("Seeding Meetings...")
    
    projects = await db.projects.find({}, {"_id": 0}).to_list(50)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    meetings = []
    
    for project in projects:
        # Create consulting meetings
        num_meetings = random.randint(3, 10)
        
        start_date = datetime.fromisoformat(project["start_date"].replace("Z", "+00:00"))
        
        for i in range(num_meetings):
            meeting_date = start_date + timedelta(days=i * random.randint(7, 14))
            
            # Get consultant names
            consultant_ids = project.get("assigned_consultants", [])
            attendee_names = []
            for cid in consultant_ids[:3]:
                user = await db.users.find_one({"id": cid}, {"_id": 0, "full_name": 1})
                if user:
                    attendee_names.append(user["full_name"])
            
            meeting = {
                "id": str(uuid.uuid4()),
                "type": "consulting",
                "project_id": project["id"],
                "client_id": None,
                "lead_id": project.get("lead_id"),
                "sow_id": None,
                "meeting_date": meeting_date.isoformat(),
                "mode": random.choice(["online", "offline", "tele_call"]),
                "attendees": consultant_ids[:3],
                "attendee_names": attendee_names,
                "duration_minutes": random.choice([30, 45, 60, 90, 120]),
                "notes": f"Progress review meeting for {project['name']}",
                "is_delivered": meeting_date < datetime.now(timezone.utc),
                "title": random.choice([
                    "Weekly Progress Review",
                    "Milestone Discussion",
                    "Client Feedback Session",
                    "Deliverable Presentation",
                    "Strategy Alignment Meeting",
                    "Status Update Call"
                ]),
                "agenda": [
                    "Review progress since last meeting",
                    "Discuss blockers and challenges",
                    "Plan for next milestone",
                    "Q&A session"
                ],
                "discussion_points": [
                    "Discussed project progress",
                    "Reviewed deliverables status",
                    "Identified next steps"
                ] if meeting_date < datetime.now(timezone.utc) else [],
                "decisions_made": [
                    "Agreed on timeline adjustments",
                    "Approved deliverable draft"
                ] if meeting_date < datetime.now(timezone.utc) and random.random() > 0.5 else [],
                "action_items": [],
                "next_meeting_date": (meeting_date + timedelta(days=14)).isoformat() if random.random() > 0.5 else None,
                "mom_generated": meeting_date < datetime.now(timezone.utc) and random.random() > 0.3,
                "mom_sent_to_client": meeting_date < datetime.now(timezone.utc) and random.random() > 0.5,
                "mom_sent_at": meeting_date.isoformat() if meeting_date < datetime.now(timezone.utc) and random.random() > 0.5 else None,
                "created_by": admin_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.meetings.insert_one(meeting)
            meetings.append(meeting)
    
    # Create some sales meetings
    leads = await db.leads.find({"status": {"$in": ["contacted", "qualified", "proposal"]}}, {"_id": 0}).to_list(20)
    sales_users = await db.users.find({"role": {"$in": ["executive", "account_manager"]}}, {"_id": 0}).to_list(10)
    
    for lead in leads[:10]:
        sales_person = random.choice(sales_users) if sales_users else admin_user
        meeting_date = random_date_between(
            datetime(2024, 6, 1, tzinfo=timezone.utc),
            datetime.now(timezone.utc)
        )
        
        meeting = {
            "id": str(uuid.uuid4()),
            "type": "sales",
            "project_id": None,
            "client_id": None,
            "lead_id": lead["id"],
            "sow_id": None,
            "meeting_date": meeting_date.isoformat(),
            "mode": random.choice(["online", "tele_call", "offline"]),
            "attendees": [sales_person["id"]],
            "attendee_names": [sales_person["full_name"]],
            "duration_minutes": random.choice([30, 45, 60]),
            "notes": f"Sales discussion with {lead['company']}",
            "is_delivered": meeting_date < datetime.now(timezone.utc),
            "title": random.choice([
                "Initial Discovery Call",
                "Solution Presentation",
                "Proposal Discussion",
                "Pricing Negotiation",
                "Requirements Gathering"
            ]),
            "agenda": [
                "Introduction and company overview",
                "Understanding client needs",
                "Presenting solutions",
                "Discussing next steps"
            ],
            "discussion_points": [],
            "decisions_made": [],
            "action_items": [],
            "next_meeting_date": None,
            "mom_generated": False,
            "mom_sent_to_client": False,
            "mom_sent_at": None,
            "created_by": sales_person["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.meetings.insert_one(meeting)
        meetings.append(meeting)
    
    print(f"  Created {len(meetings)} meetings")
    return meetings

async def seed_expenses(db):
    """Create expense records for employees"""
    print("Seeding Expenses...")
    
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(50)
    projects = await db.projects.find({}, {"_id": 0}).to_list(30)
    clients = await db.clients.find({}, {"_id": 0}).to_list(30)
    
    expenses = []
    
    for employee in employees:
        # Create 1-5 expense requests per employee
        num_expenses = random.randint(1, 5)
        
        for _ in range(num_expenses):
            is_office = random.random() > 0.7
            project = random.choice(projects) if projects and not is_office else None
            client = random.choice(clients) if clients and not is_office and not project else None
            
            # Generate line items
            num_items = random.randint(1, 5)
            line_items = []
            total_amount = 0
            
            expense_templates = {
                "travel": [
                    ("Flight to client location", 5000, 15000),
                    ("Train ticket", 500, 3000),
                    ("Bus fare", 200, 800),
                ],
                "local_conveyance": [
                    ("Uber/Ola rides", 200, 1500),
                    ("Auto rickshaw", 100, 500),
                    ("Metro fare", 50, 300),
                ],
                "food": [
                    ("Lunch with client", 500, 2000),
                    ("Team dinner", 1000, 5000),
                    ("Working lunch", 200, 500),
                ],
                "accommodation": [
                    ("Hotel stay", 2000, 8000),
                    ("Guest house", 1000, 3000),
                ],
                "office_supplies": [
                    ("Stationery", 200, 1000),
                    ("Printer cartridge", 500, 2000),
                ],
                "communication": [
                    ("Mobile recharge", 200, 500),
                    ("Internet bill", 500, 1500),
                ],
                "client_entertainment": [
                    ("Client dinner", 2000, 8000),
                    ("Gift items", 500, 3000),
                ],
            }
            
            categories = random.sample(list(expense_templates.keys()), k=min(num_items, len(expense_templates)))
            
            for category in categories:
                templates = expense_templates[category]
                desc, min_amt, max_amt = random.choice(templates)
                amount = random.randint(min_amt, max_amt)
                
                line_items.append({
                    "category": category,
                    "description": desc,
                    "amount": amount,
                    "date": random_date_between(
                        datetime(2024, 6, 1, tzinfo=timezone.utc),
                        datetime.now(timezone.utc)
                    ).isoformat(),
                    "receipt_url": None,
                    "receipt_data": None
                })
                total_amount += amount
            
            status_weights = {
                "draft": 0.1,
                "pending": 0.25,
                "approved": 0.45,
                "rejected": 0.1,
                "reimbursed": 0.1
            }
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            expense = {
                "id": str(uuid.uuid4()),
                "employee_id": employee["id"],
                "employee_name": f"{employee['first_name']} {employee['last_name']}",
                "client_id": client["id"] if client else None,
                "client_name": client["company_name"] if client else None,
                "project_id": project["id"] if project else None,
                "project_name": project["name"] if project else None,
                "is_office_expense": is_office,
                "line_items": line_items,
                "total_amount": total_amount,
                "currency": "INR",
                "status": status,
                "approval_request_id": None,
                "rejection_reason": "Insufficient documentation" if status == "rejected" else None,
                "reimbursed_at": datetime.now(timezone.utc).isoformat() if status == "reimbursed" else None,
                "reimbursed_by": None,
                "notes": f"Expense claim for {'office expenses' if is_office else (project['name'] if project else 'client visit')}",
                "created_by": employee.get("user_id", employee["id"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.expenses.insert_one(expense)
            expenses.append(expense)
    
    print(f"  Created {len(expenses)} expense requests")
    return expenses

async def seed_leave_requests(db):
    """Create leave requests for employees"""
    print("Seeding Leave Requests...")
    
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(50)
    
    leave_requests = []
    
    for employee in employees:
        # Create 0-3 leave requests per employee
        num_requests = random.randint(0, 3)
        
        for _ in range(num_requests):
            leave_type = random.choice(["casual_leave", "sick_leave", "earned_leave"])
            days = random.randint(1, 5)
            
            start_date = random_date_between(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime.now(timezone.utc) + timedelta(days=30)
            )
            end_date = start_date + timedelta(days=days - 1)
            
            status_weights = {
                "pending": 0.2,
                "approved": 0.65,
                "rejected": 0.15
            }
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            reasons = {
                "casual_leave": [
                    "Personal work",
                    "Family function",
                    "House shifting",
                    "Attending wedding",
                    "Personal errands"
                ],
                "sick_leave": [
                    "Fever and cold",
                    "Medical checkup",
                    "Dental appointment",
                    "Back pain",
                    "Migraine"
                ],
                "earned_leave": [
                    "Vacation trip",
                    "Family holiday",
                    "Home town visit",
                    "Wedding anniversary trip",
                    "Festival celebration"
                ]
            }
            
            leave_request = {
                "id": str(uuid.uuid4()),
                "employee_id": employee["id"],
                "employee_name": f"{employee['first_name']} {employee['last_name']}",
                "user_id": employee.get("user_id", employee["id"]),
                "leave_type": leave_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
                "reason": random.choice(reasons[leave_type]),
                "status": status,
                "approval_request_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.leave_requests.insert_one(leave_request)
            leave_requests.append(leave_request)
    
    print(f"  Created {len(leave_requests)} leave requests")
    return leave_requests

async def seed_attendance(db):
    """Create attendance records for employees"""
    print("Seeding Attendance...")
    
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(50)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    attendance_records = []
    
    # Generate attendance for the last 3 months
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc)
    
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        date_str = current_date.strftime("%Y-%m-%d")
        
        for employee in employees:
            # Random attendance status
            status_weights = {
                "present": 0.75,
                "work_from_home": 0.10,
                "absent": 0.05,
                "half_day": 0.03,
                "on_leave": 0.05,
                "holiday": 0.02
            }
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            record = {
                "id": str(uuid.uuid4()),
                "employee_id": employee["id"],
                "date": date_str,
                "status": status,
                "remarks": "" if status == "present" else random.choice([
                    "Working from home",
                    "Client visit",
                    "Medical leave",
                    "Personal work",
                    ""
                ]),
                "created_by": admin_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            attendance_records.append(record)
        
        current_date += timedelta(days=1)
    
    # Bulk insert for performance
    if attendance_records:
        await db.attendance.insert_many(attendance_records)
    
    print(f"  Created {len(attendance_records)} attendance records")
    return attendance_records

async def seed_salary_components(db):
    """Create salary components for payroll"""
    print("Seeding Salary Components...")
    
    components = [
        # Earnings
        {"name": "Basic Salary", "type": "earning", "value_type": "percentage", "value": 50, "description": "50% of CTC"},
        {"name": "HRA", "type": "earning", "value_type": "percentage", "value": 20, "description": "House Rent Allowance - 20% of CTC"},
        {"name": "Conveyance Allowance", "type": "earning", "value_type": "fixed", "value": 1600, "description": "Monthly conveyance allowance"},
        {"name": "Special Allowance", "type": "earning", "value_type": "percentage", "value": 15, "description": "Special allowance - 15% of CTC"},
        {"name": "Medical Allowance", "type": "earning", "value_type": "fixed", "value": 1250, "description": "Monthly medical allowance"},
        {"name": "LTA", "type": "earning", "value_type": "percentage", "value": 5, "description": "Leave Travel Allowance"},
        # Deductions
        {"name": "PF Employee Contribution", "type": "deduction", "value_type": "percentage", "value": 12, "description": "Provident Fund - 12% of Basic"},
        {"name": "Professional Tax", "type": "deduction", "value_type": "fixed", "value": 200, "description": "Monthly professional tax"},
        {"name": "Income Tax (TDS)", "type": "deduction", "value_type": "percentage", "value": 10, "description": "Tax Deducted at Source"},
        {"name": "ESI Employee", "type": "deduction", "value_type": "percentage", "value": 0.75, "description": "ESI Employee contribution"},
    ]
    
    for comp in components:
        comp["id"] = str(uuid.uuid4())
        comp["is_active"] = True
        comp["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.salary_components.insert_one(comp)
    
    print(f"  Created {len(components)} salary components")
    return components

async def seed_payroll_inputs(db):
    """Create payroll input records for employees"""
    print("Seeding Payroll Inputs...")
    
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(50)
    
    payroll_inputs = []
    
    # Generate payroll inputs for last 6 months
    current_date = datetime.now(timezone.utc)
    
    for month_offset in range(6):
        target_date = current_date - timedelta(days=30 * month_offset)
        year = target_date.year
        month = target_date.month
        
        for employee in employees:
            # Calculate working days (approximately)
            import calendar
            total_days = calendar.monthrange(year, month)[1]
            weekends = sum(1 for d in range(1, total_days + 1) 
                         if datetime(year, month, d).weekday() >= 5)
            working_days = total_days - weekends
            
            # Random attendance
            present_days = random.randint(int(working_days * 0.85), working_days)
            leaves = working_days - present_days
            
            payroll_input = {
                "id": str(uuid.uuid4()),
                "employee_id": employee["id"],
                "employee_name": f"{employee['first_name']} {employee['last_name']}",
                "month": month,
                "year": year,
                "working_days": working_days,
                "present_days": present_days,
                "leaves": leaves,
                "lop_days": max(0, leaves - 2),  # Loss of Pay if leaves exceed 2
                "incentive": random.choice([0, 0, 0, 2000, 5000, 10000]),
                "bonus": random.choice([0, 0, 0, 0, 5000, 10000]) if month == 10 else 0,  # Diwali bonus
                "penalty": random.choice([0, 0, 0, 500, 1000]) if random.random() > 0.9 else 0,
                "overtime_hours": random.randint(0, 20),
                "overtime_amount": random.randint(0, 5000),
                "reimbursements": random.choice([0, 0, 1000, 2000, 5000]),
                "arrears": 0,
                "remarks": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.payroll_inputs.insert_one(payroll_input)
            payroll_inputs.append(payroll_input)
    
    print(f"  Created {len(payroll_inputs)} payroll input records")
    return payroll_inputs

async def seed_communication_logs(db):
    """Create communication logs for leads"""
    print("Seeding Communication Logs...")
    
    leads = await db.leads.find({}, {"_id": 0}).to_list(50)
    sales_users = await db.users.find({"role": {"$in": ["executive", "account_manager"]}}, {"_id": 0}).to_list(10)
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0})
    
    comm_logs = []
    
    for lead in leads:
        # Create 1-5 communication logs per lead
        num_logs = random.randint(1, 5)
        
        for _ in range(num_logs):
            sales_person = random.choice(sales_users) if sales_users else admin_user
            
            comm_type = random.choice(["call", "email", "whatsapp", "sms"])
            outcomes = {
                "call": ["Discussed requirements", "Scheduled follow-up", "Not reachable", "Call back requested", "Meeting scheduled"],
                "email": ["Proposal sent", "Information shared", "Follow-up email", "Meeting invite sent", "No response"],
                "whatsapp": ["Quick query resolved", "Document shared", "Confirmed meeting", "Rescheduled", "Acknowledged"],
                "sms": ["Reminder sent", "Meeting confirmation", "Thank you note", "Follow-up reminder"],
            }
            
            log = {
                "id": str(uuid.uuid4()),
                "lead_id": lead["id"],
                "communication_type": comm_type,
                "notes": f"Communication with {lead['first_name']} {lead['last_name']} from {lead['company']}",
                "outcome": random.choice(outcomes[comm_type]),
                "created_by": sales_person["id"],
                "created_at": random_date_between(
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime.now(timezone.utc)
                ).isoformat()
            }
            
            await db.communication_logs.insert_one(log)
            comm_logs.append(log)
    
    print(f"  Created {len(comm_logs)} communication logs")
    return comm_logs

async def seed_notifications(db):
    """Create sample notifications"""
    print("Seeding Notifications...")
    
    users = await db.users.find({}, {"_id": 0}).to_list(50)
    
    notifications = []
    
    notification_templates = [
        {"type": "leave_request", "title": "Leave Request Submitted", "message": "A new leave request has been submitted for your approval."},
        {"type": "expense_approval", "title": "Expense Approval Required", "message": "An expense claim is pending your approval."},
        {"type": "task_assigned", "title": "New Task Assigned", "message": "A new task has been assigned to you."},
        {"type": "meeting_reminder", "title": "Meeting Reminder", "message": "You have a meeting scheduled in 1 hour."},
        {"type": "project_update", "title": "Project Update", "message": "There's a new update on your project."},
        {"type": "agreement_approval", "title": "Agreement Pending Approval", "message": "An agreement is pending your review and approval."},
    ]
    
    for user in users:
        # Create 2-5 notifications per user
        num_notifs = random.randint(2, 5)
        
        for _ in range(num_notifs):
            template = random.choice(notification_templates)
            
            notif = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "type": template["type"],
                "title": template["title"],
                "message": template["message"],
                "reference_type": template["type"].split("_")[0],
                "reference_id": str(uuid.uuid4()),
                "is_read": random.random() > 0.4,
                "created_at": random_date_between(
                    datetime.now(timezone.utc) - timedelta(days=30),
                    datetime.now(timezone.utc)
                ).isoformat()
            }
            
            await db.notifications.insert_one(notif)
            notifications.append(notif)
    
    print(f"  Created {len(notifications)} notifications")
    return notifications

async def main():
    """Main function to seed all data"""
    print("\n" + "="*60)
    print("Starting Indian HR Consulting Data Seeding")
    print("="*60 + "\n")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Clear existing data (optional - comment out if you want to append)
    print("Clearing existing data...")
    collections_to_clear = [
        "users", "employees", "leads", "clients", "pricing_plans", "sow", 
        "quotations", "agreements", "projects", "tasks", "meetings", 
        "expenses", "leave_requests", "attendance", "salary_components",
        "payroll_inputs", "communication_logs", "notifications",
        "consultant_profiles", "consultant_assignments", "approval_requests"
    ]
    
    for collection in collections_to_clear:
        await db[collection].delete_many({})
    print("  Cleared all collections\n")
    
    # Seed data in order
    await seed_users(db)
    await seed_employees(db)
    await seed_leads(db)
    await seed_clients(db)
    await seed_pricing_plans_and_sow(db)
    await seed_projects(db)
    await seed_tasks(db)
    await seed_meetings(db)
    await seed_expenses(db)
    await seed_leave_requests(db)
    await seed_attendance(db)
    await seed_salary_components(db)
    await seed_payroll_inputs(db)
    await seed_communication_logs(db)
    await seed_notifications(db)
    
    print("\n" + "="*60)
    print("Data Seeding Complete!")
    print("="*60)
    
    # Print summary
    print("\nData Summary:")
    print("-" * 40)
    
    summary_collections = [
        ("users", "Users"),
        ("employees", "Employees"),
        ("leads", "Leads"),
        ("clients", "Clients"),
        ("pricing_plans", "Pricing Plans"),
        ("sow", "SOWs"),
        ("quotations", "Quotations"),
        ("agreements", "Agreements"),
        ("projects", "Projects"),
        ("tasks", "Tasks"),
        ("meetings", "Meetings"),
        ("expenses", "Expense Requests"),
        ("leave_requests", "Leave Requests"),
        ("attendance", "Attendance Records"),
        ("salary_components", "Salary Components"),
        ("payroll_inputs", "Payroll Inputs"),
        ("communication_logs", "Communication Logs"),
        ("notifications", "Notifications"),
    ]
    
    for collection, name in summary_collections:
        count = await db[collection].count_documents({})
        print(f"  {name}: {count}")
    
    print("\n" + "="*60)
    print("Test Credentials:")
    print("-" * 40)
    print("  Admin: admin@company.com / admin123")
    print("  All other users: [email] / password123")
    print("="*60 + "\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
