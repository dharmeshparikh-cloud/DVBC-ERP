"""
Script to populate test SOW data with scopes for Consulting Efforts Summary.
Creates: SOWs linked to existing projects with committed and additional scopes.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import random

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "netra_erp")

# Sample scope data
SCOPE_NAMES = [
    "Process Mapping & Documentation",
    "Gap Analysis & Recommendations",
    "Training & Knowledge Transfer",
    "System Implementation Support",
    "Change Management",
    "Performance Optimization",
    "Quality Audit",
    "Compliance Review",
    "Technology Assessment",
    "Strategic Planning Workshop"
]

SCOPE_DELIVERABLES = [
    "Process flow diagrams",
    "Analysis report",
    "Training materials",
    "Implementation guide",
    "Change management plan",
    "Performance report",
    "Audit findings",
    "Compliance checklist",
    "Technology roadmap",
    "Strategic plan document"
]


async def main():
    print("=" * 60)
    print("POPULATING TEST SOW DATA WITH SCOPES")
    print("=" * 60)
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get existing projects
        projects = await db.projects.find({}, {"_id": 0}).to_list(10)
        print(f"\nFound {len(projects)} projects")
        
        if not projects:
            print("No projects found. Please run populate_test_meetings.py first.")
            return
        
        # Get existing users
        users = await db.users.find(
            {"role": {"$in": ["consultant", "admin", "manager"]}},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1}
        ).to_list(10)
        
        created_sows = 0
        created_scopes = 0
        
        for project in projects:
            project_id = project.get("id")
            project_name = project.get("name")
            client_id = project.get("client_id")
            
            # Check if SOW exists for this project
            existing = await db.enhanced_sow.find_one({"project_id": project_id})
            if existing:
                print(f"SOW already exists for project: {project_name}")
                continue
            
            # Create SOW with scopes
            sow_id = str(uuid.uuid4())
            
            # Create 3-5 committed scopes
            num_committed = random.randint(3, 5)
            scopes = []
            
            for i in range(num_committed):
                scope_id = str(uuid.uuid4())
                scope = {
                    "id": scope_id,
                    "name": SCOPE_NAMES[i % len(SCOPE_NAMES)],
                    "description": f"Committed scope for {project_name}",
                    "deliverables": [SCOPE_DELIVERABLES[i % len(SCOPE_DELIVERABLES)]],
                    "duration_days": random.randint(5, 30),
                    "fee": random.randint(50000, 200000),
                    "status": random.choice(["not_started", "in_progress", "completed"]),
                    "progress_percentage": random.randint(0, 100),
                    "is_additional": False,  # Committed scope
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                scopes.append(scope)
                created_scopes += 1
            
            # Add 0-2 additional scopes (requested after SOW signing)
            num_additional = random.randint(0, 2)
            for i in range(num_additional):
                scope_id = str(uuid.uuid4())
                scope = {
                    "id": scope_id,
                    "name": f"Additional: {SCOPE_NAMES[(i + num_committed) % len(SCOPE_NAMES)]}",
                    "description": f"Additional scope requested after project start",
                    "deliverables": [SCOPE_DELIVERABLES[(i + num_committed) % len(SCOPE_DELIVERABLES)]],
                    "duration_days": random.randint(3, 15),
                    "fee": random.randint(30000, 100000),
                    "status": random.choice(["not_started", "in_progress"]),
                    "progress_percentage": random.randint(0, 50),
                    "is_additional": True,  # Additional scope
                    "approved_by": users[0]["id"] if users else None,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                scopes.append(scope)
                created_scopes += 1
            
            # Calculate totals
            total_fee = sum(s.get("fee", 0) for s in scopes)
            total_duration = sum(s.get("duration_days", 0) for s in scopes)
            avg_progress = sum(s.get("progress_percentage", 0) for s in scopes) / len(scopes) if scopes else 0
            completed_scopes = len([s for s in scopes if s.get("status") == "completed"])
            
            # Create SOW document
            sow = {
                "id": sow_id,
                "project_id": project_id,
                "project_name": project_name,
                "client_id": client_id,
                "client_name": project.get("client_name"),
                "sow_number": f"SOW-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}",
                "title": f"Statement of Work - {project_name}",
                "status": "active",
                "scopes": scopes,
                "total_fee": total_fee,
                "total_duration_days": total_duration,
                "progress_percentage": round(avg_progress, 1),
                "completed_scopes": completed_scopes,
                "total_scopes": len(scopes),
                "committed_scopes": num_committed,
                "additional_scopes": num_additional,
                "sales_handover_complete": True,  # Committed SOW from sales
                "handover_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 90))).isoformat(),
                "start_date": project.get("start_date"),
                "end_date": project.get("end_date"),
                "created_by": users[0]["id"] if users else None,
                "created_by_name": users[0]["full_name"] if users else "System",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.enhanced_sow.insert_one(sow)
            created_sows += 1
            
            print(f"Created SOW for: {project_name} ({num_committed} committed, {num_additional} additional scopes)")
        
        # Also link some meetings to scopes
        print("\n--- Linking Meetings to SOW Scopes ---")
        meetings = await db.meetings.find(
            {"type": "consulting", "sow_scope_ids": {"$exists": False}},
            {"_id": 0}
        ).to_list(20)
        
        linked_meetings = 0
        for meeting in meetings:
            project_id = meeting.get("project_id")
            if not project_id:
                continue
            
            # Find SOW for this project
            sow = await db.enhanced_sow.find_one({"project_id": project_id}, {"_id": 0})
            if not sow:
                continue
            
            scopes = sow.get("scopes", [])
            if not scopes:
                continue
            
            # Link 1-2 random scopes to this meeting
            num_scopes = min(random.randint(1, 2), len(scopes))
            selected_scopes = random.sample(scopes, num_scopes)
            
            scope_ids = [s["id"] for s in selected_scopes]
            scope_details = [{"id": s["id"], "name": s["name"]} for s in selected_scopes]
            
            await db.meetings.update_one(
                {"id": meeting["id"]},
                {
                    "$set": {
                        "sow_id": sow["id"],
                        "sow_scope_ids": scope_ids,
                        "sow_scopes": scope_details
                    }
                }
            )
            linked_meetings += 1
        
        print(f"Linked {linked_meetings} meetings to SOW scopes")
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST DATA POPULATION COMPLETE")
        print("=" * 60)
        print(f"SOWs created: {created_sows}")
        print(f"Scopes created: {created_scopes}")
        print(f"Meetings linked to scopes: {linked_meetings}")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
