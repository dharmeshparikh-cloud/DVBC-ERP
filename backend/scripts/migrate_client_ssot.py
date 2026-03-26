"""
Migration Script: SSOT Client Fields Sync
==========================================
Syncs all client fields (name, email, phone, address, gstin) from Lead to Quotations and Agreements.

This script:
1. Updates all quotations to have client fields from their linked lead
2. Updates all agreements to have client fields from their linked lead
3. Adds has_sow flag to quotations based on SOW existence
4. Generates a report of changes made

Run with: python scripts/migrate_client_ssot.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "erp_db")


async def get_client_fields_from_lead(lead):
    """Extract SSOT client fields from a lead document."""
    company = lead.get("company", "") or ""
    first_name = lead.get("first_name", "") or ""
    last_name = lead.get("last_name", "") or ""
    
    client_name = company if company else f"{first_name} {last_name}".strip()
    
    return {
        "client_name": client_name,
        "client_email": lead.get("email", "") or "",
        "client_phone": lead.get("phone", "") or lead.get("mobile", "") or "",
        "client_address": lead.get("address", "") or lead.get("company_address", "") or "",
        "client_gstin": lead.get("gstin", "") or lead.get("gst_number", "") or ""
    }


async def check_sow_exists(db, pricing_plan_id):
    """Check if SOW exists with at least 1 scope item for a pricing plan."""
    if not pricing_plan_id:
        return False, None
    
    # Check enhanced_sow collection
    sow = await db.enhanced_sow.find_one(
        {"pricing_plan_id": pricing_plan_id},
        {"_id": 0, "id": 1, "scopes": 1}
    )
    if sow:
        scopes = sow.get("scopes") or []
        if len(scopes) > 0:
            return True, sow.get("id")
    
    # Check legacy sow collection
    legacy_sow = await db.sow.find_one(
        {"pricing_plan_id": pricing_plan_id},
        {"_id": 0, "id": 1, "items": 1}
    )
    if legacy_sow:
        items = legacy_sow.get("items") or []
        if len(items) > 0:
            return True, legacy_sow.get("id")
    
    return False, None


async def migrate_quotations(db):
    """Migrate quotations to use SSOT client fields and add has_sow flag."""
    print("\n=== Migrating Quotations ===")
    
    quotations = await db.quotations.find({}, {"_id": 0}).to_list(None)
    print(f"Found {len(quotations)} quotations to process")
    
    updated_count = 0
    sow_added_count = 0
    errors = []
    
    for quotation in quotations:
        try:
            lead_id = quotation.get("lead_id")
            pricing_plan_id = quotation.get("pricing_plan_id")
            
            if not lead_id:
                errors.append(f"Quotation {quotation.get('id')}: No lead_id")
                continue
            
            # Get lead
            lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
            if not lead:
                errors.append(f"Quotation {quotation.get('id')}: Lead {lead_id} not found")
                continue
            
            # Get SSOT client fields
            client_fields = await get_client_fields_from_lead(lead)
            
            # Check SOW existence
            has_sow, sow_id = await check_sow_exists(db, pricing_plan_id)
            
            # Build update
            update_data = {
                **client_fields,
                "has_sow": has_sow,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if sow_id:
                update_data["sow_id"] = sow_id
            
            # Check if any field changed
            fields_changed = False
            for key, value in client_fields.items():
                if quotation.get(key) != value:
                    fields_changed = True
                    break
            
            if quotation.get("has_sow") != has_sow:
                sow_added_count += 1
            
            if fields_changed or quotation.get("has_sow") is None:
                await db.quotations.update_one(
                    {"id": quotation.get("id")},
                    {"$set": update_data}
                )
                updated_count += 1
        
        except Exception as e:
            errors.append(f"Quotation {quotation.get('id')}: {str(e)}")
    
    print(f"  Updated: {updated_count} quotations")
    print(f"  SOW flags added: {sow_added_count}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"    - {err}")
    
    return updated_count, errors


async def migrate_agreements(db):
    """Migrate agreements to use SSOT client fields."""
    print("\n=== Migrating Agreements ===")
    
    agreements = await db.agreements.find({}, {"_id": 0}).to_list(None)
    print(f"Found {len(agreements)} agreements to process")
    
    updated_count = 0
    errors = []
    
    for agreement in agreements:
        try:
            lead_id = agreement.get("lead_id")
            
            if not lead_id:
                errors.append(f"Agreement {agreement.get('id')}: No lead_id")
                continue
            
            # Get lead
            lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
            if not lead:
                errors.append(f"Agreement {agreement.get('id')}: Lead {lead_id} not found")
                continue
            
            # Get SSOT client fields
            client_fields = await get_client_fields_from_lead(lead)
            
            # Build update
            update_data = {
                **client_fields,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if any field changed
            fields_changed = False
            for key, value in client_fields.items():
                if agreement.get(key) != value:
                    fields_changed = True
                    break
            
            if fields_changed:
                await db.agreements.update_one(
                    {"id": agreement.get("id")},
                    {"$set": update_data}
                )
                updated_count += 1
        
        except Exception as e:
            errors.append(f"Agreement {agreement.get('id')}: {str(e)}")
    
    print(f"  Updated: {updated_count} agreements")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"    - {err}")
    
    return updated_count, errors


async def main():
    """Main migration function."""
    print("=" * 60)
    print("SSOT Client Fields Migration")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Test connection
        await db.command("ping")
        print(f"\nConnected to MongoDB: {DB_NAME}")
        
        # Run migrations
        q_count, q_errors = await migrate_quotations(db)
        a_count, a_errors = await migrate_agreements(db)
        
        # Summary
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Quotations updated: {q_count}")
        print(f"Agreements updated: {a_count}")
        print(f"Total errors: {len(q_errors) + len(a_errors)}")
        print(f"Completed at: {datetime.now().isoformat()}")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
