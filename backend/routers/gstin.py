"""
GSTIN Validation Router - Validates GSTIN format and extracts details.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
from .deps import get_db, get_current_user
from .models import User

router = APIRouter(prefix="/gstin", tags=["GSTIN"])

STATE_CODE_MAP = {
    '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
    '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
    '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
    '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
    '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
    '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
    '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
    '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
    '25': 'Daman & Diu', '26': 'Dadra & Nagar Haveli', '27': 'Maharashtra',
    '28': 'Andhra Pradesh', '29': 'Karnataka', '30': 'Goa',
    '31': 'Lakshadweep', '32': 'Kerala', '33': 'Tamil Nadu',
    '34': 'Puducherry', '35': 'Andaman & Nicobar', '36': 'Telangana',
    '37': 'Andhra Pradesh (New)', '38': 'Ladakh', '97': 'Other Territory',
}

GSTIN_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

PAN_ENTITY_TYPES = {
    'C': 'Company', 'P': 'Individual', 'H': 'HUF',
    'F': 'Firm', 'A': 'AOP', 'T': 'Trust',
    'B': 'BOI', 'L': 'Local Authority', 'J': 'Artificial Juridical Person',
    'G': 'Government',
}


class GSTINValidateRequest(BaseModel):
    gstin: str
    company_name: Optional[str] = None
    lead_id: Optional[str] = None


@router.post("/validate")
async def validate_gstin(
    data: GSTINValidateRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate GSTIN format, extract state/PAN, and cross-check company name."""
    gstin = data.gstin.upper().strip()

    result = {
        "gstin": gstin,
        "valid": False,
        "state_code": "",
        "state_name": "",
        "pan": "",
        "entity_type": "",
        "entity_type_label": "",
        "company_match": None,
        "errors": [],
    }

    if len(gstin) != 15:
        result["errors"].append(f"Must be 15 characters (currently {len(gstin)})")
        return result

    if not GSTIN_REGEX.match(gstin):
        result["errors"].append("Invalid GSTIN format")
        return result

    state_code = gstin[:2]
    state_name = STATE_CODE_MAP.get(state_code)
    if not state_name:
        result["errors"].append(f"Invalid state code: {state_code}")
        return result

    pan = gstin[2:12]
    entity_char = pan[3]
    entity_label = PAN_ENTITY_TYPES.get(entity_char, 'Unknown')

    result.update({
        "valid": True,
        "state_code": state_code,
        "state_name": state_name,
        "pan": pan,
        "entity_type": entity_char,
        "entity_type_label": entity_label,
    })

    # Cross-check company name if provided
    company_name = data.company_name
    if not company_name and data.lead_id:
        db = get_db()
        lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0, "company": 1})
        if lead:
            company_name = lead.get("company", "")

    if company_name:
        pan_name_chars = pan[:5].upper()
        company_clean = re.sub(r'[^A-Z]', '', company_name.upper())

        if entity_char == 'P':
            result["company_match"] = {
                "match": False,
                "hint": "This is a personal PAN, not a company GSTIN"
            }
        elif entity_char in ('C', 'F', 'H', 'A', 'T'):
            if company_clean.startswith(pan_name_chars):
                result["company_match"] = {
                    "match": True,
                    "hint": f"Company name matches PAN entity: {pan_name_chars}"
                }
            elif company_clean[:3] == pan_name_chars[:3]:
                result["company_match"] = {
                    "match": True,
                    "hint": f"Partial match on entity name"
                }
            else:
                result["company_match"] = {
                    "match": False,
                    "hint": f"PAN entity \"{pan_name_chars}\" doesn't match company \"{company_clean[:5]}\""
                }

    return result
