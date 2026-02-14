#!/usr/bin/env python3
"""
Populate the database with dummy data for testing the sales funnel.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'sales_funnel_db')

async def main():
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Check if admin user exists
    admin = await db.users.find_one({"email": "admin@company.com"})
    if not admin:
        print("Admin user not found. Please run init_db.py first.")
        return
    
    admin_id = admin['id']
    print(f"Using admin user: {admin['full_name']} ({admin_id})")
    
    # Get existing leads
    leads = await db.leads.find({}, {"_id": 0}).to_list(100)
    if not leads:
        print("No leads found. Creating sample leads...")
        sample_leads = [
            {
                "id": str(uuid.uuid4()),
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "company": "TechSolutions Pvt Ltd",
                "job_title": "CEO",
                "email": "rajesh@techsolutions.in",
                "phone": "+91 9876543210",
                "linkedin_url": "https://linkedin.com/in/rajeshkumar",
                "source": "Referral",
                "status": "qualified",
                "notes": "Interested in lean consulting",
                "lead_score": 85,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "first_name": "Priya",
                "last_name": "Sharma",
                "company": "Growth Enterprises",
                "job_title": "Managing Director",
                "email": "priya@growthenterprises.com",
                "phone": "+91 9988776655",
                "linkedin_url": "https://linkedin.com/in/priyasharma",
                "source": "Website",
                "status": "proposal",
                "notes": "Looking for HR consulting",
                "lead_score": 78,
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.leads.insert_many(sample_leads)
        leads = sample_leads
        print(f"Created {len(sample_leads)} sample leads")
    
    print(f"Found {len(leads)} leads")
    
    # Create pricing plans for leads without them
    for lead in leads[:2]:  # Process first 2 leads
        lead_id = lead['id']
        
        # Check if pricing plan exists
        existing_plan = await db.pricing_plans.find_one({"lead_id": lead_id})
        if existing_plan:
            print(f"  Pricing plan already exists for {lead['first_name']} {lead['last_name']}")
            continue
        
        # Create a pricing plan
        pricing_plan = {
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "project_duration_type": "quarterly",
            "project_duration_months": 3,
            "payment_schedule": "monthly",
            "consultants": [
                {
                    "consultant_type": "principal",
                    "count": 1,
                    "meetings": 12,
                    "hours": 24,
                    "rate_per_meeting": 15000
                },
                {
                    "consultant_type": "lead",
                    "count": 2,
                    "meetings": 24,
                    "hours": 48,
                    "rate_per_meeting": 12500
                }
            ],
            "sow_items": [],
            "discount_percentage": 10,
            "gst_percentage": 18,
            "growth_consulting_plan": "Monthly reviews with executive team",
            "growth_guarantee": "15% improvement in operational efficiency",
            "created_by": admin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.pricing_plans.insert_one(pricing_plan)
        print(f"  Created pricing plan for {lead['first_name']} {lead['last_name']}")
        
        # Create a quotation from the pricing plan
        total_meetings = sum(c['meetings'] for c in pricing_plan['consultants'])
        subtotal = sum(c['meetings'] * c['rate_per_meeting'] for c in pricing_plan['consultants'])
        discount = subtotal * (pricing_plan['discount_percentage'] / 100)
        after_discount = subtotal - discount
        gst = after_discount * (pricing_plan['gst_percentage'] / 100)
        grand_total = after_discount + gst
        
        count = await db.quotations.count_documents({})
        quotation = {
            "id": str(uuid.uuid4()),
            "pricing_plan_id": pricing_plan['id'],
            "lead_id": lead_id,
            "quotation_number": f"QT-{datetime.now().year}-{count + 1:04d}",
            "version": 1,
            "is_final": True,
            "status": "sent",
            "base_rate_per_meeting": 12500,
            "total_meetings": total_meetings,
            "subtotal": subtotal,
            "discount_amount": discount,
            "gst_amount": gst,
            "grand_total": grand_total,
            "validity_days": 30,
            "terms_and_conditions": "Standard terms and conditions apply.",
            "created_by": admin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quotations.insert_one(quotation)
        print(f"  Created quotation {quotation['quotation_number']} - Total: ₹{grand_total:,.2f}")
        
        # Create an agreement for the first lead (pending approval)
        if lead == leads[0]:
            agr_count = await db.agreements.count_documents({})
            agreement = {
                "id": str(uuid.uuid4()),
                "quotation_id": quotation['id'],
                "lead_id": lead_id,
                "agreement_number": f"AGR-{datetime.now().year}-{agr_count + 1:04d}",
                "agreement_type": "standard",
                "payment_terms": "Net 30 days from invoice date",
                "special_conditions": "Quarterly performance review meetings included",
                "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=97)).isoformat(),
                "status": "pending_approval",
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.agreements.insert_one(agreement)
            print(f"  Created agreement {agreement['agreement_number']} (Pending Approval)")
    
    print("\n✅ Dummy data population complete!")
    print("\nSummary:")
    leads_count = await db.leads.count_documents({})
    plans_count = await db.pricing_plans.count_documents({})
    quotes_count = await db.quotations.count_documents({})
    agreements_count = await db.agreements.count_documents({})
    pending_count = await db.agreements.count_documents({"status": "pending_approval"})
    
    print(f"  - Leads: {leads_count}")
    print(f"  - Pricing Plans: {plans_count}")
    print(f"  - Quotations: {quotes_count}")
    print(f"  - Agreements: {agreements_count}")
    print(f"  - Pending Approvals: {pending_count}")

if __name__ == "__main__":
    asyncio.run(main())
