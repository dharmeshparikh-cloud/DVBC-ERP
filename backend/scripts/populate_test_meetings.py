"""
Script to populate test data for Consulting Meetings flow.
Creates: Clients, Projects, and 20 Consulting Meetings with varied data.
Tests the full flow from kickoff to payment.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import random

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "netra_erp")

# Test data configuration
TEST_CLIENTS = [
    {"name": "Acme Manufacturing Ltd", "industry": "Manufacturing", "city": "Mumbai"},
    {"name": "TechSoft Solutions Pvt Ltd", "industry": "IT Services", "city": "Bangalore"},
    {"name": "Global Retail Corp", "industry": "Retail", "city": "Delhi"},
    {"name": "HealthCare Plus", "industry": "Healthcare", "city": "Chennai"},
    {"name": "FinServe India", "industry": "Financial Services", "city": "Hyderabad"}
]

TEST_PROJECTS = [
    {"name": "Digital Transformation Initiative", "type": "consulting"},
    {"name": "Process Optimization Program", "type": "consulting"},
    {"name": "Quality Management System", "type": "consulting"},
    {"name": "ERP Implementation", "type": "consulting"},
    {"name": "Supply Chain Enhancement", "type": "consulting"}
]

MEETING_TITLES = [
    "Kickoff Meeting",
    "Requirements Gathering",
    "Process Analysis Review",
    "Solution Design Workshop",
    "Implementation Planning",
    "Progress Review",
    "Weekly Status Update",
    "Training Session",
    "UAT Review",
    "Go-Live Planning"
]

AGENDA_ITEMS = [
    "Review project milestones",
    "Discuss key deliverables",
    "Address open issues",
    "Plan next steps",
    "Resource allocation discussion",
    "Budget review",
    "Timeline adjustments",
    "Risk assessment",
    "Stakeholder feedback",
    "Change request review"
]

DISCUSSION_POINTS = [
    "Client expressed satisfaction with progress",
    "Need to address resource constraints",
    "Timeline is on track",
    "Budget utilization at 60%",
    "Team collaboration is effective",
    "Technical challenges being addressed",
    "Quality metrics are positive",
    "Stakeholder engagement improving"
]

DECISIONS_MADE = [
    "Approved phase 2 timeline",
    "Additional resources approved",
    "Scope change accepted",
    "Budget extension granted",
    "Training schedule finalized",
    "Go-live date confirmed"
]


async def get_existing_users(db):
    """Get existing consultants from the database."""
    users = await db.users.find(
        {"role": {"$in": ["consultant", "lead_consultant", "senior_consultant", 
                         "principal_consultant", "admin", "manager"]}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "employee_id": 1}
    ).to_list(20)
    return users


async def create_test_clients(db):
    """Create test clients if they don't exist."""
    created_clients = []
    
    for client_data in TEST_CLIENTS:
        # Check if client exists
        existing = await db.clients.find_one({"company_name": client_data["name"]})
        if existing:
            created_clients.append(existing)
            continue
        
        client_id = str(uuid.uuid4())
        client = {
            "id": client_id,
            "company_name": client_data["name"],
            "name": client_data["name"],
            "industry": client_data["industry"],
            "city": client_data["city"],
            "state": "Maharashtra" if client_data["city"] == "Mumbai" else "Karnataka",
            "country": "India",
            "status": "active",
            "contacts": [{
                "id": str(uuid.uuid4()),
                "name": f"John Doe - {client_data['name'][:10]}",
                "email": f"contact@{client_data['name'].lower().replace(' ', '').replace('.', '')[:15]}.com",
                "phone": f"98765{random.randint(10000, 99999)}",
                "designation": "Project Manager",
                "is_primary": True
            }],
            "contract_value": random.randint(500000, 5000000),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.clients.insert_one(client)
        created_clients.append(client)
        print(f"Created client: {client['company_name']}")
    
    return created_clients


async def create_test_projects(db, clients, users):
    """Create test projects linked to clients."""
    created_projects = []
    
    for i, project_data in enumerate(TEST_PROJECTS):
        client = clients[i % len(clients)]
        
        # Check if project exists
        existing = await db.projects.find_one({
            "name": project_data["name"],
            "client_id": client["id"]
        })
        if existing:
            created_projects.append(existing)
            continue
        
        project_id = str(uuid.uuid4())
        assigned_consultant = users[i % len(users)] if users else None
        
        project = {
            "id": project_id,
            "name": project_data["name"],
            "type": project_data["type"],
            "client_id": client["id"],
            "client_name": client["company_name"],
            "status": "active",
            "start_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 180))).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(30, 180))).isoformat(),
            "total_meetings_committed": random.randint(10, 30),
            "total_meetings_delivered": 0,  # Will be updated as meetings are delivered
            "total_value": random.randint(1000000, 10000000),
            "billing_type": "milestone",
            "assigned_consultant_id": assigned_consultant["id"] if assigned_consultant else None,
            "assigned_consultant_name": assigned_consultant["full_name"] if assigned_consultant else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.projects.insert_one(project)
        created_projects.append(project)
        print(f"Created project: {project['name']} for {client['company_name']}")
    
    return created_projects


async def create_test_meetings(db, projects, clients, users, count=20):
    """Create test consulting meetings."""
    created_meetings = []
    modes = ["online", "offline", "tele_call"]
    
    for i in range(count):
        project = projects[i % len(projects)]
        client = next((c for c in clients if c["id"] == project["client_id"]), clients[0])
        
        # Generate meeting date (spread across last 3 months to future 1 month)
        days_offset = random.randint(-90, 30)
        meeting_date = datetime.now(timezone.utc) + timedelta(days=days_offset)
        
        # Determine if meeting is delivered (past meetings)
        is_delivered = days_offset < -7  # Meetings older than a week are delivered
        is_past = days_offset < 0
        
        meeting_id = str(uuid.uuid4())
        mode = random.choice(modes)
        
        # Select random consultant
        consultant = random.choice(users) if users else None
        
        # Generate MOM data for delivered meetings
        has_mom = is_delivered and random.random() > 0.2  # 80% of delivered have MOM
        
        meeting = {
            "id": meeting_id,
            "type": "consulting",
            "title": f"{random.choice(MEETING_TITLES)} - {project['name'][:20]}",
            "project_id": project["id"],
            "project_name": project["name"],
            "client_id": client["id"],
            "client_name": client["company_name"],
            "sow_id": None,
            "meeting_date": meeting_date.isoformat(),
            "mode": mode,
            "duration_minutes": random.choice([30, 45, 60, 90, 120]),
            "attendees": [consultant["id"]] if consultant else [],
            "attendee_names": [consultant["full_name"]] if consultant else [],
            "notes": f"Consulting meeting #{i+1} for {project['name']}",
            "is_delivered": is_delivered,
            "delivered_at": meeting_date.isoformat() if is_delivered else None,
            "delivered_by": consultant["id"] if is_delivered and consultant else None,
            # MOM fields
            "mom_generated": has_mom,
            "mom": f"Meeting minutes for {project['name']}" if has_mom else None,
            "agenda": random.sample(AGENDA_ITEMS, k=random.randint(2, 5)),
            "discussion_points": random.sample(DISCUSSION_POINTS, k=random.randint(2, 4)) if has_mom else [],
            "decisions_made": random.sample(DECISIONS_MADE, k=random.randint(1, 3)) if has_mom else [],
            "action_items": [],
            "next_meeting_date": (meeting_date + timedelta(days=7)).isoformat() if has_mom else None,
            "mom_sent_to_client": has_mom and random.random() > 0.3,
            "mom_sent_at": meeting_date.isoformat() if has_mom and random.random() > 0.3 else None,
            # Travel details for offline meetings
            "travel_details": {
                "start_location": "Office",
                "end_location": client["city"],
                "travel_mode": random.choice(["DRIVING", "TWO_WHEELER", "TRANSIT"]),
                "distance_km": random.randint(5, 50),
                "is_round_trip": True
            } if mode == "offline" else None,
            # Expense details
            "expense_id": None,
            "expense_amount": random.randint(500, 3000) if mode == "offline" and is_delivered else None,
            # Project team (for RBAC)
            "project_team": [
                {"user_id": consultant["id"], "employee_id": consultant.get("employee_id")}
            ] if consultant else [],
            # Metadata
            "created_by": consultant["id"] if consultant else None,
            "created_by_name": consultant["full_name"] if consultant else "System",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.meetings.insert_one(meeting)
        created_meetings.append(meeting)
        
        # Update project delivered count for delivered meetings
        if is_delivered:
            await db.projects.update_one(
                {"id": project["id"]},
                {"$inc": {"total_meetings_delivered": 1}}
            )
        
        status = "DELIVERED" if is_delivered else ("SCHEDULED" if not is_past else "PENDING")
        print(f"Created meeting #{i+1}: {meeting['title'][:40]} [{status}] [{mode.upper()}]")
    
    return created_meetings


async def create_consultant_assignments(db, projects, users):
    """Create consultant assignments for projects."""
    for project in projects:
        for user in users[:3]:  # Assign first 3 consultants to each project
            existing = await db.consultant_assignments.find_one({
                "project_id": project["id"],
                "consultant_id": user["id"]
            })
            if existing:
                continue
            
            assignment = {
                "id": str(uuid.uuid4()),
                "project_id": project["id"],
                "consultant_id": user["id"],
                "consultant_name": user["full_name"],
                "role": user.get("role", "consultant"),
                "is_active": True,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.consultant_assignments.insert_one(assignment)
    print(f"Created consultant assignments for {len(projects)} projects")


async def main():
    """Main function to populate test data."""
    print("=" * 60)
    print("POPULATING TEST DATA FOR CONSULTING MEETINGS")
    print("=" * 60)
    
    # Connect to database
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get existing users
        users = await get_existing_users(db)
        print(f"\nFound {len(users)} existing consultants/managers")
        
        if not users:
            print("WARNING: No consultants found. Creating without user assignments.")
        
        # Create test clients
        print("\n--- Creating Test Clients ---")
        clients = await create_test_clients(db)
        
        # Create test projects
        print("\n--- Creating Test Projects ---")
        projects = await create_test_projects(db, clients, users)
        
        # Create consultant assignments
        print("\n--- Creating Consultant Assignments ---")
        if users:
            await create_consultant_assignments(db, projects, users)
        
        # Create 20 test meetings
        print("\n--- Creating 20 Test Meetings ---")
        meetings = await create_test_meetings(db, projects, clients, users, count=20)
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST DATA POPULATION COMPLETE")
        print("=" * 60)
        print(f"Clients created/found: {len(clients)}")
        print(f"Projects created/found: {len(projects)}")
        print(f"Meetings created: {len(meetings)}")
        print(f"  - Delivered: {sum(1 for m in meetings if m['is_delivered'])}")
        print(f"  - With MOM: {sum(1 for m in meetings if m['mom_generated'])}")
        print(f"  - Offline: {sum(1 for m in meetings if m['mode'] == 'offline')}")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
