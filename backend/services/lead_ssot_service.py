"""
Lead SSOT (Single Source of Truth) Service

Provides centralized lead data access and duplicate detection
for all downstream forms (Meetings, Pricing, SOW, Agreements, etc.)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

# Lead Source Options (dropdown values)
LEAD_SOURCES = [
    {"id": "website", "label": "Website", "icon": "globe"},
    {"id": "referral", "label": "Referral", "icon": "users"},
    {"id": "linkedin", "label": "LinkedIn", "icon": "linkedin"},
    {"id": "cold_call", "label": "Cold Call", "icon": "phone"},
    {"id": "email_campaign", "label": "Email Campaign", "icon": "mail"},
    {"id": "trade_show", "label": "Trade Show/Event", "icon": "calendar"},
    {"id": "partner", "label": "Partner", "icon": "handshake"},
    {"id": "advertisement", "label": "Advertisement", "icon": "megaphone"},
    {"id": "social_media", "label": "Social Media", "icon": "share"},
    {"id": "existing_client", "label": "Existing Client", "icon": "repeat"},
    {"id": "word_of_mouth", "label": "Word of Mouth", "icon": "message-circle"},
    {"id": "other", "label": "Other", "icon": "more-horizontal"},
]

# Master fields that come from Lead
LEAD_MASTER_FIELDS = [
    "company",
    "contact_person", 
    "email",
    "phone",
    "city",
    "state",
    "country",
    "industry",
    "lead_source",
    "assigned_to",
    "first_name",
    "last_name",
]

# Forms that must use Lead as SSOT
DOWNSTREAM_FORMS = [
    "meeting",
    "pricing_plan",
    "quotation", 
    "sow",
    "agreement",
    "payment_verification",
    "kickoff_request",
    "client",
    "project",
]


async def check_duplicate_lead(
    db: AsyncIOMotorDatabase,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    exclude_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check for duplicate leads based on email, phone, or company name.
    Returns duplicate info if found.
    """
    duplicates = []
    
    if email:
        query = {"email": {"$regex": f"^{email}$", "$options": "i"}}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        existing = await db.leads.find_one(query, {"_id": 0, "id": 1, "company": 1, "email": 1, "phone": 1, "first_name": 1, "last_name": 1})
        if existing:
            duplicates.append({
                "type": "email",
                "field": "email",
                "value": email,
                "existing_lead": existing
            })
    
    if phone:
        # Normalize phone for comparison (remove non-digits)
        phone_normalized = ''.join(filter(str.isdigit, phone))
        if len(phone_normalized) >= 10:
            query = {
                "$or": [
                    {"phone": phone},
                    {"phone": {"$regex": phone_normalized[-10:]}}  # Match last 10 digits
                ]
            }
            if exclude_id:
                query["id"] = {"$ne": exclude_id}
            existing = await db.leads.find_one(query, {"_id": 0, "id": 1, "company": 1, "email": 1, "phone": 1, "first_name": 1, "last_name": 1})
            if existing and not any(d["type"] == "email" and d["existing_lead"]["id"] == existing["id"] for d in duplicates):
                duplicates.append({
                    "type": "phone",
                    "field": "phone", 
                    "value": phone,
                    "existing_lead": existing
                })
    
    if company:
        # Fuzzy match on company name
        query = {"company": {"$regex": f"^{company}$", "$options": "i"}}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        existing = await db.leads.find_one(query, {"_id": 0, "id": 1, "company": 1, "email": 1, "phone": 1, "first_name": 1, "last_name": 1})
        if existing and not any(d["existing_lead"]["id"] == existing["id"] for d in duplicates):
            duplicates.append({
                "type": "company",
                "field": "company",
                "value": company,
                "existing_lead": existing
            })
    
    return {
        "has_duplicates": len(duplicates) > 0,
        "duplicates": duplicates,
        "count": len(duplicates)
    }


async def get_lead_master_data(
    db: AsyncIOMotorDatabase,
    lead_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get master field data from a lead for auto-filling downstream forms.
    """
    lead = await db.leads.find_one(
        {"id": lead_id},
        {
            "_id": 0,
            "id": 1,
            "company": 1,
            "contact_person": 1,
            "first_name": 1,
            "last_name": 1,
            "email": 1,
            "phone": 1,
            "city": 1,
            "state": 1,
            "country": 1,
            "industry": 1,
            "lead_source": 1,
            "source": 1,
            "assigned_to": 1,
            "status": 1,
            "created_by": 1,
            "gstin": 1,
            "gst_number": 1
        }
    )
    
    if not lead:
        return None
    
    # Format contact person name if not explicitly set
    contact_person = lead.get("contact_person")
    if not contact_person:
        first = lead.get("first_name", "")
        last = lead.get("last_name", "")
        contact_person = f"{first} {last}".strip()
    
    return {
        "lead_id": lead["id"],
        "company": lead.get("company", ""),
        "contact_person": contact_person,
        "email": lead.get("email", ""),
        "phone": lead.get("phone", ""),
        "city": lead.get("city", ""),
        "state": lead.get("state", ""),
        "country": lead.get("country", ""),
        "industry": lead.get("industry", ""),
        "lead_source": lead.get("lead_source") or lead.get("source", ""),
        "assigned_to": lead.get("assigned_to", ""),
        "status": lead.get("status", ""),
        "gstin": lead.get("gstin") or lead.get("gst_number", ""),
        # Computed fields
        "client_name": lead.get("company", ""),
        "client_email": lead.get("email", ""),
        "client_phone": lead.get("phone", ""),
    }


async def search_leads_for_dropdown(
    db: AsyncIOMotorDatabase,
    query: str,
    user_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search leads for dropdown selector.
    Returns minimal data needed for selection.
    """
    search_filter = {
        "$or": [
            {"company": {"$regex": query, "$options": "i"}},
            {"first_name": {"$regex": query, "$options": "i"}},
            {"last_name": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}},
        ]
    }
    
    # Filter by user's accessible leads (assigned or created by)
    search_filter["$or"].append({"assigned_to": user_id})
    search_filter["$or"].append({"created_by": user_id})
    
    cursor = db.leads.find(
        search_filter,
        {
            "_id": 0,
            "id": 1,
            "company": 1,
            "first_name": 1,
            "last_name": 1,
            "email": 1,
            "phone": 1,
            "status": 1,
            "city": 1
        }
    ).sort("updated_at", -1).limit(limit)
    
    leads = await cursor.to_list(length=limit)
    
    return [
        {
            "id": lead["id"],
            "label": f"{lead.get('company', 'Unknown')} - {lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "company": lead.get("company", ""),
            "contact": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "email": lead.get("email", ""),
            "phone": lead.get("phone", ""),
            "status": lead.get("status", ""),
            "city": lead.get("city", "")
        }
        for lead in leads
    ]


def get_ssot_report() -> Dict[str, Any]:
    """
    Generate report of SSOT implementation.
    """
    return {
        "master_entity": "Lead",
        "master_fields": LEAD_MASTER_FIELDS,
        "locked_fields_in_downstream": [
            "company / client_name",
            "contact_person",
            "email / client_email", 
            "phone / client_phone",
            "city",
            "industry",
            "lead_source",
            "assigned_to / salesperson"
        ],
        "downstream_forms_updated": DOWNSTREAM_FORMS,
        "tables_referencing_lead_id": [
            "meetings",
            "pricing_plans",
            "quotations",
            "sow_documents",
            "agreements",
            "payment_verifications",
            "kickoff_requests",
            "projects",
            "client_users"
        ],
        "duplicate_detection_fields": [
            "email",
            "phone", 
            "company"
        ],
        "lead_sources": LEAD_SOURCES
    }
