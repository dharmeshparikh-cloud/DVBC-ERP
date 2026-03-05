"""
Client Data Lookup Service

PURPOSE: Provides a single source of truth for client information.
Instead of copying client_name, client_email into every downstream collection,
entities should store lead_id and look up client details on read.

AUTHORITATIVE SOURCE: leads collection
REFERENCING COLLECTIONS: agreements, enhanced_sow, kickoff_requests, projects

USAGE:
- Store lead_id in downstream collections
- Call get_client_details(db, lead_id) when displaying client info
- For historical accuracy, also store client_name_at_creation for audit

BENEFITS:
- Client info updates propagate automatically
- No stale data in downstream collections
- Single place to update client information
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger("client_lookup_service")


async def get_client_details(db, lead_id: str) -> Optional[Dict]:
    """
    Get current client details from the authoritative source (leads collection).
    
    Args:
        db: Database instance
        lead_id: The lead's UUID (id field)
    
    Returns:
        Dict with client details or None if not found
    """
    try:
        lead = await db.leads.find_one(
            {"id": lead_id},
            {
                "_id": 0,
                "id": 1,
                "company": 1,
                "company_name": 1,
                "email": 1,
                "client_email": 1,
                "contact_person": 1,
                "phone": 1,
                "address": 1,
                "city": 1,
                "state": 1,
                "country": 1,
                "website": 1,
                "industry": 1,
                "gst_number": 1,
                "pan_number": 1
            }
        )
        
        if not lead:
            return None
        
        # Normalize field names
        return {
            "lead_id": lead.get("id"),
            "client_name": lead.get("company") or lead.get("company_name", ""),
            "client_email": lead.get("email") or lead.get("client_email", ""),
            "contact_person": lead.get("contact_person", ""),
            "phone": lead.get("phone", ""),
            "address": lead.get("address", ""),
            "city": lead.get("city", ""),
            "state": lead.get("state", ""),
            "country": lead.get("country", ""),
            "website": lead.get("website", ""),
            "industry": lead.get("industry", ""),
            "gst_number": lead.get("gst_number", ""),
            "pan_number": lead.get("pan_number", "")
        }
        
    except Exception as e:
        logger.error(f"Error getting client details for lead {lead_id}: {e}")
        return None


async def enrich_with_client_details(db, entity: Dict, lead_id_field: str = "lead_id") -> Dict:
    """
    Enrich an entity with current client details from lead.
    
    Args:
        db: Database instance
        entity: The entity dict to enrich
        lead_id_field: Field name containing the lead_id
    
    Returns:
        Enriched entity with client_details object
    """
    lead_id = entity.get(lead_id_field)
    
    if not lead_id:
        # No lead reference - return entity as-is
        return entity
    
    client = await get_client_details(db, lead_id)
    
    if client:
        entity["client_details"] = client
        # Also populate top-level fields for backward compatibility
        entity["client_name"] = client.get("client_name", entity.get("client_name", ""))
        entity["client_email"] = client.get("client_email", entity.get("client_email", ""))
    
    return entity


async def enrich_list_with_client_details(db, entities: List[Dict], lead_id_field: str = "lead_id") -> List[Dict]:
    """
    Enrich a list of entities with client details (batched for efficiency).
    
    Args:
        db: Database instance
        entities: List of entity dicts to enrich
        lead_id_field: Field name containing the lead_id
    
    Returns:
        List of enriched entities
    """
    # Collect unique lead_ids
    lead_ids = list(set(e.get(lead_id_field) for e in entities if e.get(lead_id_field)))
    
    if not lead_ids:
        return entities
    
    # Batch fetch all leads
    leads = await db.leads.find(
        {"id": {"$in": lead_ids}},
        {
            "_id": 0,
            "id": 1,
            "company": 1,
            "company_name": 1,
            "email": 1,
            "client_email": 1,
            "contact_person": 1,
            "phone": 1
        }
    ).to_list(None)
    
    # Build lookup map
    lead_map = {}
    for lead in leads:
        lead_map[lead["id"]] = {
            "lead_id": lead.get("id"),
            "client_name": lead.get("company") or lead.get("company_name", ""),
            "client_email": lead.get("email") or lead.get("client_email", ""),
            "contact_person": lead.get("contact_person", ""),
            "phone": lead.get("phone", "")
        }
    
    # Enrich entities
    for entity in entities:
        lead_id = entity.get(lead_id_field)
        if lead_id and lead_id in lead_map:
            entity["client_details"] = lead_map[lead_id]
            entity["client_name"] = lead_map[lead_id].get("client_name", entity.get("client_name", ""))
            entity["client_email"] = lead_map[lead_id].get("client_email", entity.get("client_email", ""))
    
    return entities


async def update_client_in_lead(db, lead_id: str, updates: Dict) -> bool:
    """
    Update client information in the authoritative source.
    This is the ONLY place client info should be updated.
    
    Args:
        db: Database instance
        lead_id: The lead's UUID
        updates: Dict of fields to update
    
    Returns:
        bool: True if successful
    """
    try:
        # Allowed update fields
        allowed_fields = [
            "company", "company_name", "email", "client_email",
            "contact_person", "phone", "address", "city", "state",
            "country", "website", "industry", "gst_number", "pan_number"
        ]
        
        # Filter to only allowed fields
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return False
        
        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.leads.update_one(
            {"id": lead_id},
            {"$set": filtered_updates}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating client for lead {lead_id}: {e}")
        return False


async def get_client_history(db, lead_id: str) -> List[Dict]:
    """
    Get historical client information from related entities.
    Useful for audit trail showing what client info was at different stages.
    """
    history = []
    
    # Get from agreements (earliest point)
    agreements = await db.agreements.find(
        {"lead_id": lead_id},
        {"_id": 0, "client_name_at_creation": 1, "client_name": 1, "created_at": 1}
    ).to_list(None)
    
    for a in agreements:
        if a.get("client_name_at_creation") or a.get("client_name"):
            history.append({
                "stage": "agreement",
                "client_name": a.get("client_name_at_creation") or a.get("client_name"),
                "timestamp": a.get("created_at")
            })
    
    # Get from projects (latest point)
    projects = await db.projects.find(
        {"lead_id": lead_id},
        {"_id": 0, "client_name_at_creation": 1, "client_name": 1, "created_at": 1}
    ).to_list(None)
    
    for p in projects:
        if p.get("client_name_at_creation") or p.get("client_name"):
            history.append({
                "stage": "project",
                "client_name": p.get("client_name_at_creation") or p.get("client_name"),
                "timestamp": p.get("created_at")
            })
    
    # Sort by timestamp
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return history


async def get_client_display_name(db, lead_id: str, fallback: str = "Unknown Client") -> str:
    """
    Get just the display name for a client.
    Lightweight version for list views.
    """
    client = await get_client_details(db, lead_id)
    if client:
        return client.get("client_name") or fallback
    return fallback


async def check_client_data_consistency(db) -> Dict:
    """
    Check for inconsistencies between stored client_name and lead source.
    Used for data integrity audits.
    
    Returns:
        Report of inconsistencies found
    """
    inconsistencies = []
    total_checked = 0
    
    try:
        # Check projects
        projects = await db.projects.find(
            {"lead_id": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "name": 1, "project_name": 1, "lead_id": 1, "client_name": 1}
        ).to_list(1000)
        
        for project in projects:
            total_checked += 1
            lead = await db.leads.find_one(
                {"id": project.get("lead_id")},
                {"_id": 0, "company": 1, "company_name": 1}
            )
            if lead:
                expected_name = lead.get("company") or lead.get("company_name", "")
                stored_name = project.get("client_name", "")
                
                # Normalize for comparison
                if stored_name and expected_name and stored_name.strip().lower() != expected_name.strip().lower():
                    inconsistencies.append({
                        "type": "project",
                        "id": project.get("id"),
                        "name": project.get("name") or project.get("project_name"),
                        "stored_client_name": stored_name,
                        "lead_source_name": expected_name,
                        "lead_id": project.get("lead_id")
                    })
        
        # Check agreements
        agreements = await db.agreements.find(
            {"lead_id": {"$exists": True, "$ne": None}},
            {"_id": 0, "id": 1, "lead_id": 1, "client_name": 1}
        ).to_list(1000)
        
        for agreement in agreements:
            total_checked += 1
            lead = await db.leads.find_one(
                {"id": agreement.get("lead_id")},
                {"_id": 0, "company": 1, "company_name": 1}
            )
            if lead:
                expected_name = lead.get("company") or lead.get("company_name", "")
                stored_name = agreement.get("client_name", "")
                
                if stored_name and expected_name and stored_name.strip().lower() != expected_name.strip().lower():
                    inconsistencies.append({
                        "type": "agreement",
                        "id": agreement.get("id"),
                        "stored_client_name": stored_name,
                        "lead_source_name": expected_name,
                        "lead_id": agreement.get("lead_id")
                    })
    
    except Exception as e:
        logger.error(f"Error in consistency check: {e}")
    
    return {
        "total_checked": total_checked,
        "inconsistencies_found": len(inconsistencies),
        "details": inconsistencies[:50]  # Limit for response size
    }


async def bulk_update_client_references(db, entity_type: str = "all") -> Dict:
    """
    Update client_name in downstream collections from lead source.
    
    Args:
        db: Database instance
        entity_type: "projects", "agreements", or "all"
    
    Returns:
        Summary of updates
    """
    results = {"updated": 0, "skipped": 0, "errors": []}
    
    try:
        collections_to_update = []
        if entity_type in ["projects", "all"]:
            collections_to_update.append(("projects", db.projects))
        if entity_type in ["agreements", "all"]:
            collections_to_update.append(("agreements", db.agreements))
        
        for coll_name, collection in collections_to_update:
            entities = await collection.find(
                {"lead_id": {"$exists": True, "$ne": None}},
                {"_id": 0, "id": 1, "lead_id": 1, "client_name": 1}
            ).to_list(1000)
            
            for entity in entities:
                lead_id = entity.get("lead_id")
                if not lead_id:
                    results["skipped"] += 1
                    continue
                
                client = await get_client_details(db, lead_id)
                if not client:
                    results["skipped"] += 1
                    continue
                
                new_client_name = client.get("client_name", "")
                old_client_name = entity.get("client_name", "")
                
                # Store original for audit
                update_fields = {
                    "client_name": new_client_name,
                    "client_name_at_creation": old_client_name or new_client_name,
                    "client_data_synced_at": datetime.now(timezone.utc).isoformat()
                }
                
                try:
                    await collection.update_one(
                        {"id": entity.get("id")},
                        {"$set": update_fields}
                    )
                    results["updated"] += 1
                except Exception as e:
                    results["errors"].append({
                        "collection": coll_name,
                        "id": entity.get("id"),
                        "error": str(e)
                    })
    
    except Exception as e:
        results["errors"].append({"error": str(e)})
    
    return results
