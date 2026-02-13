#!/usr/bin/env python3
"""
Populate dummy data for testing the complete sales workflow
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone, timedelta
import uuid
import random

async def populate_dummy_data():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'workflow_db')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🚀 Starting dummy data population...")
    
    # Get admin user ID
    admin = await db.users.find_one({"email": "admin@company.com"}, {"_id": 0})
    if not admin:
        print("❌ Admin user not found. Please login first to create admin user.")
        return
    
    admin_id = admin['id']
    
    # Dummy leads with various stages
    leads_data = [
        {
            "id": str(uuid.uuid4()),
            "lead_owner": admin_id,
            "first_name": "Amit",
            "last_name": "Sharma",
            "company": "TechVision India Pvt Ltd",
            "contact_person": "Amit Sharma",
            "job_title": "CEO",
            "email": "amit.sharma@techvision.in",
            "phone": "+91-98765-43210",
            "street": "MG Road, Cyber Hub",
            "city": "Bangalore",
            "state": "Karnataka",
            "zip_code": "560001",
            "country": "India",
            "lead_source": "Website",
            "status": "contacted",
            "sales_status": "schedule_meeting",
            "product_interest": "Growth Consulting",
            "notes": "Interested in scaling operations. Meeting scheduled for next week.",
            "assigned_to": admin_id,
            "created_by": admin_id,
            "lead_score": 75,
            "score_breakdown": {"title_score": 40, "contact_score": 30, "engagement_score": 10},
            "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "lead_owner": admin_id,
            "first_name": "Priya",
            "last_name": "Verma",
            "company": "InnovateSoft Solutions",
            "contact_person": "Priya Verma",
            "job_title": "Director of Operations",
            "email": "priya.verma@innovatesoft.com",
            "phone": "+91-99887-76543",
            "street": "Bandra West",
            "city": "Mumbai",
            "state": "Maharashtra",
            "zip_code": "400050",
            "country": "India",
            "lead_source": "LinkedIn",
            "status": "qualified",
            "sales_status": "send_details",
            "product_interest": "Lean Consulting",
            "notes": "Looking for lean transformation services. Budget approved.",
            "assigned_to": admin_id,
            "created_by": admin_id,
            "lead_score": 65,
            "score_breakdown": {"title_score": 25, "contact_score": 20, "engagement_score": 20},
            "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "lead_owner": admin_id,
            "first_name": "Rajesh",
            "last_name": "Patel",
            "company": "Global Manufacturing Ltd",
            "contact_person": "Rajesh Patel",
            "job_title": "VP - Operations",
            "email": "rajesh.patel@globalmfg.com",
            "phone": "+91-97654-32109",
            "street": "GIDC Estate",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "zip_code": "380015",
            "country": "India",
            "lead_source": "Referral",
            "status": "proposal",
            "sales_status": "meeting_done",
            "product_interest": "Process Improvement",
            "notes": "3 meetings completed. Proposal sent. Awaiting decision.",
            "assigned_to": admin_id,
            "created_by": admin_id,
            "lead_score": 85,
            "score_breakdown": {"title_score": 35, "contact_score": 30, "engagement_score": 25},
            "created_at": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "lead_owner": admin_id,
            "first_name": "Sunita",
            "last_name": "Reddy",
            "company": "HealthTech Innovations",
            "contact_person": "Sunita Reddy",
            "job_title": "Founder & CEO",
            "email": "sunita@healthtech.in",
            "phone": "+91-98123-45678",
            "linkedin_url": "https://linkedin.com/in/sunitareddy",
            "street": "Hitech City",
            "city": "Hyderabad",
            "state": "Telangana",
            "zip_code": "500081",
            "country": "India",
            "lead_source": "RocketReach",
            "status": "new",
            "sales_status": "call_back",
            "product_interest": "Digital Transformation",
            "notes": "Initial call done. Follow up scheduled.",
            "assigned_to": admin_id,
            "created_by": admin_id,
            "lead_score": 80,
            "score_breakdown": {"title_score": 40, "contact_score": 30, "engagement_score": 5},
            "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "lead_owner": admin_id,
            "first_name": "Vikram",
            "last_name": "Singh",
            "company": "Retail Chain India",
            "contact_person": "Vikram Singh",
            "job_title": "General Manager",
            "email": "vikram.singh@retailchain.in",
            "phone": "+91-96543-21098",
            "street": "Connaught Place",
            "city": "New Delhi",
            "state": "Delhi",
            "zip_code": "110001",
            "country": "India",
            "lead_source": "Trade Show",
            "status": "contacted",
            "sales_status": "send_details",
            "product_interest": "Supply Chain Optimization",
            "notes": "Interested in inventory management consulting.",
            "assigned_to": admin_id,
            "created_by": admin_id,
            "lead_score": 45,
            "score_breakdown": {"title_score": 15, "contact_score": 20, "engagement_score": 10},
            "created_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Insert leads
    print("📋 Creating leads...")
    for lead in leads_data:
        await db.leads.update_one(
            {"email": lead["email"]},
            {"$set": lead},
            upsert=True
        )
    print(f"✓ Created {len(leads_data)} leads")
    
    # Communication logs
    lead_ids = [lead["id"] for lead in leads_data]
    communications = []
    
    for lead_id in lead_ids[:3]:  # Add communications for first 3 leads
        communications.extend([
            {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "communication_type": "call",
                "notes": "Initial discovery call. Discussed business challenges and consulting needs.",
                "outcome": "schedule_meeting",
                "created_by": admin_id,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5))).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "communication_type": "email",
                "notes": "Sent company profile and case studies.",
                "outcome": "sent",
                "created_by": admin_id,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 4))).isoformat()
            }
        ])
    
    print("📞 Creating communication logs...")
    if communications:
        await db.communication_logs.insert_many(communications)
    print(f"✓ Created {len(communications)} communication logs")
    
    # Projects
    projects_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Digital Transformation Initiative",
            "client_name": "Tech Solutions Pvt Ltd",
            "lead_id": lead_ids[0],
            "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            "status": "active",
            "total_meetings_committed": 24,
            "total_meetings_delivered": 8,
            "number_of_visits": 8,
            "assigned_team": [admin_id],
            "budget": 850000.00,
            "notes": "Phase 1: Process mapping completed. Phase 2: Implementation ongoing.",
            "created_by": admin_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lean Manufacturing Implementation",
            "client_name": "InnovateSoft Solutions",
            "lead_id": lead_ids[1],
            "start_date": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=75)).isoformat(),
            "status": "active",
            "total_meetings_committed": 36,
            "total_meetings_delivered": 4,
            "number_of_visits": 4,
            "assigned_team": [admin_id],
            "budget": 1250000.00,
            "notes": "Kick-off completed. Training sessions started.",
            "created_by": admin_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print("📊 Creating projects...")
    for project in projects_data:
        await db.projects.update_one(
            {"name": project["name"]},
            {"$set": project},
            upsert=True
        )
    print(f"✓ Created {len(projects_data)} projects")
    
    # Meetings
    meetings_data = []
    for project in projects_data:
        for i in range(project['total_meetings_delivered']):
            meetings_data.append({
                "id": str(uuid.uuid4()),
                "project_id": project["id"],
                "meeting_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 25))).isoformat(),
                "mode": random.choice(["online", "offline", "tele_call"]),
                "attendees": [admin_id],
                "duration_minutes": random.choice([60, 90, 120]),
                "notes": f"Meeting {i+1}: Progress review and next steps discussion.",
                "is_delivered": True,
                "created_by": admin_id,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 25))).isoformat()
            })
    
    print("📅 Creating meetings...")
    if meetings_data:
        await db.meetings.insert_many(meetings_data)
    print(f"✓ Created {len(meetings_data)} meetings")
    
    # Pricing Plans
    pricing_plans = [
        {
            "id": str(uuid.uuid4()),
            "lead_id": lead_ids[2],  # Rajesh Patel - in proposal stage
            "project_duration_type": "quarterly",
            "project_duration_months": 3,
            "payment_schedule": "monthly",
            "consultants": [
                {
                    "consultant_type": "principal",
                    "count": 1,
                    "meetings": 12,
                    "hours": 24,
                    "rate_per_meeting": 12500
                },
                {
                    "consultant_type": "lead",
                    "count": 2,
                    "meetings": 24,
                    "hours": 48,
                    "rate_per_meeting": 12500
                }
            ],
            "sow_items": [
                {
                    "category": "Process Optimization",
                    "sub_category": "Manufacturing",
                    "description": "Lean manufacturing implementation",
                    "deliverables": ["Process mapping", "Waste identification", "Implementation plan"]
                }
            ],
            "base_amount": 450000,
            "discount_percentage": 10,
            "gst_percentage": 18,
            "total_amount": 477900,
            "growth_consulting_plan": "1 Principal + 2 Lead Consultants, 36 meetings over 3 months",
            "growth_guarantee": "20% improvement in operational efficiency within 6 months",
            "created_by": admin_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print("💰 Creating pricing plans...")
    if pricing_plans:
        await db.pricing_plans.insert_many(pricing_plans)
    print(f"✓ Created {len(pricing_plans)} pricing plans")
    
    # Quotations
    quotations = [
        {
            "id": str(uuid.uuid4()),
            "pricing_plan_id": pricing_plans[0]["id"],
            "lead_id": lead_ids[2],
            "quotation_number": "QT-2026-0001",
            "version": 1,
            "is_final": True,
            "status": "sent",
            "base_rate_per_meeting": 12500,
            "total_meetings": 36,
            "subtotal": 450000,
            "discount_amount": 45000,
            "gst_amount": 72900,
            "grand_total": 477900,
            "notes": "Quarterly engagement with monthly billing cycle",
            "created_by": admin_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print("📄 Creating quotations...")
    if quotations:
        await db.quotations.insert_many(quotations)
    print(f"✓ Created {len(quotations)} quotations")
    
    # Agreements (pending approval)
    agreements = [
        {
            "id": str(uuid.uuid4()),
            "quotation_id": quotations[0]["id"],
            "lead_id": lead_ids[2],
            "agreement_number": "AGR-2026-0001",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "status": "pending",
            "approval_status": "pending_approval",
            "terms_and_conditions": "Standard consulting services agreement with 30-day payment terms",
            "created_by": admin_id,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print("📝 Creating agreements...")
    if agreements:
        await db.agreements.insert_many(agreements)
    print(f"✓ Created {len(agreements)} agreements (pending manager approval)")
    
    print("\n✅ Dummy data population complete!")
    print("\n📊 Summary:")
    print(f"   • {len(leads_data)} leads across different stages")
    print(f"   • {len(communications)} communication logs")
    print(f"   • {len(projects_data)} active projects")
    print(f"   • {len(meetings_data)} meetings delivered")
    print(f"   • {len(pricing_plans)} pricing plans")
    print(f"   • {len(quotations)} quotations")
    print(f"   • {len(agreements)} agreements pending approval")
    print("\n🎯 Test the complete workflow:")
    print("   1. View leads in different stages")
    print("   2. Check communication logs")
    print("   3. Review pricing plans and quotations")
    print("   4. Manager can approve/reject agreements")
    print("   5. Track project meetings and deliverables")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(populate_dummy_data())
