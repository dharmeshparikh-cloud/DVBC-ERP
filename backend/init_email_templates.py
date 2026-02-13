#!/usr/bin/env python3
"""
Initialize default email notification templates in the database
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
import uuid

async def initialize_default_templates():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'workflow_db')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check if templates already exist
    existing_count = await db.email_notification_templates.count_documents({})
    
    if existing_count > 0:
        print(f"✓ {existing_count} email templates already exist. Skipping initialization.")
        return
    
    # Default templates
    templates = [
        {
            "id": str(uuid.uuid4()),
            "name": "Professional Agreement Notification",
            "subject": "Agreement for Consulting Services - {agreement_number}",
            "body": """Dear {client_first_name},

Thank you for choosing our consulting services. We are pleased to share the agreement for your upcoming project.

**Agreement Details:**
- Agreement Number: {agreement_number}
- Company: {company_name}
- Total Amount: {total_amount}
- Project Start Date: {start_date}

Please review the attached agreement document. If you have any questions or need clarification, feel free to reach out.

To proceed, kindly review and sign the agreement at your earliest convenience.

Looking forward to a successful partnership!

Best regards,
{salesperson_name}
{salesperson_email}
""",
            "template_type": "agreement_notification",
            "variables": ["client_first_name", "agreement_number", "company_name", "total_amount", "start_date", "salesperson_name", "salesperson_email"],
            "created_by": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Formal Agreement with Terms",
            "subject": "Consulting Services Agreement - {company_name}",
            "body": """Dear {client_name},

Greetings from DVBC Consulting!

We are delighted to formalize our partnership through this consulting services agreement.

**Project Overview:**
- Agreement Reference: {agreement_number}
- Quotation Reference: {quotation_number}
- Total Project Value: {total_amount} ({total_amount_words})
- Engagement Period: {start_date} to {end_date}

The attached agreement outlines:
• Scope of work and deliverables
• Team deployment details
• Payment schedule and terms
• Project milestones

Please take a moment to review the agreement. Should you have any questions or require modifications, I'm here to assist.

Once you're satisfied, we request you to sign and return the agreement to initiate the project.

We're excited to contribute to {company_name}'s growth journey!

Warm regards,

{salesperson_name}
Consulting Services Team
{salesperson_email}
""",
            "template_type": "agreement_notification",
            "variables": ["client_name", "company_name", "agreement_number", "quotation_number", "total_amount", "total_amount_words", "start_date", "end_date", "salesperson_name", "salesperson_email"],
            "created_by": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Quick Agreement Notification",
            "subject": "Your Agreement is Ready - {agreement_number}",
            "body": """Hi {client_first_name},

Your consulting services agreement ({agreement_number}) is ready!

📄 Agreement Amount: {total_amount}
📅 Start Date: {start_date}

Please find the agreement attached. Review and let me know if you have any questions.

Thanks!
{salesperson_name}
""",
            "template_type": "agreement_notification",
            "variables": ["client_first_name", "agreement_number", "total_amount", "start_date", "salesperson_name"],
            "created_by": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Insert templates
    result = await db.email_notification_templates.insert_many(templates)
    
    print(f"✓ Initialized {len(result.inserted_ids)} default email templates")
    print("Templates:")
    for template in templates:
        print(f"  - {template['name']}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(initialize_default_templates())
