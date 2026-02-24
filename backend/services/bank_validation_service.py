"""
Bank Validation Service
- IFSC code validation (format + API lookup)
- Account number format validation
- Bank proof document management
"""

import re
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# IFSC Code Format: 4 letters (bank code) + 0 + 6 alphanumeric (branch code)
IFSC_PATTERN = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')

# Common bank codes and their account number patterns
BANK_ACCOUNT_PATTERNS = {
    # State Bank of India - 11 digits
    "SBIN": {"length": [11], "pattern": r'^\d{11}$', "name": "State Bank of India"},
    # HDFC Bank - 13-14 digits
    "HDFC": {"length": [13, 14], "pattern": r'^\d{13,14}$', "name": "HDFC Bank"},
    # ICICI Bank - 12 digits
    "ICIC": {"length": [12], "pattern": r'^\d{12}$', "name": "ICICI Bank"},
    # Axis Bank - 15 digits
    "UTIB": {"length": [15], "pattern": r'^\d{15}$', "name": "Axis Bank"},
    # Kotak Mahindra Bank - 14 digits
    "KKBK": {"length": [14], "pattern": r'^\d{14}$', "name": "Kotak Mahindra Bank"},
    # Punjab National Bank - 16 digits
    "PUNB": {"length": [16], "pattern": r'^\d{16}$', "name": "Punjab National Bank"},
    # Bank of Baroda - 14 digits
    "BARB": {"length": [14], "pattern": r'^\d{14}$', "name": "Bank of Baroda"},
    # Canara Bank - 13 digits
    "CNRB": {"length": [13], "pattern": r'^\d{13}$', "name": "Canara Bank"},
    # Union Bank of India - 15 digits
    "UBIN": {"length": [15], "pattern": r'^\d{15}$', "name": "Union Bank of India"},
    # Indian Bank - 15 digits
    "IDIB": {"length": [15], "pattern": r'^\d{15}$', "name": "Indian Bank"},
    # Yes Bank - 15 digits
    "YESB": {"length": [15], "pattern": r'^\d{15}$', "name": "Yes Bank"},
    # IndusInd Bank - 12-14 digits
    "INDB": {"length": [12, 13, 14], "pattern": r'^\d{12,14}$', "name": "IndusInd Bank"},
    # Federal Bank - 14-16 digits
    "FDRL": {"length": [14, 15, 16], "pattern": r'^\d{14,16}$', "name": "Federal Bank"},
    # IDFC First Bank - 11-12 digits
    "IDFB": {"length": [11, 12], "pattern": r'^\d{11,12}$', "name": "IDFC First Bank"},
    # RBL Bank - 12 digits
    "RATN": {"length": [12], "pattern": r'^\d{12}$', "name": "RBL Bank"},
}

# Generic pattern for unknown banks (9-18 digits)
GENERIC_ACCOUNT_PATTERN = re.compile(r'^\d{9,18}$')


async def validate_ifsc(ifsc_code: str) -> Dict[str, Any]:
    """
    Validate IFSC code format and lookup bank details via Razorpay's public API.
    
    Returns:
        {
            "valid": bool,
            "format_valid": bool,
            "bank_found": bool,
            "bank_name": str or None,
            "branch": str or None,
            "city": str or None,
            "state": str or None,
            "address": str or None,
            "error": str or None
        }
    """
    result = {
        "valid": False,
        "format_valid": False,
        "bank_found": False,
        "bank_name": None,
        "branch": None,
        "city": None,
        "state": None,
        "address": None,
        "error": None
    }
    
    if not ifsc_code:
        result["error"] = "IFSC code is required"
        return result
    
    # Normalize to uppercase
    ifsc_code = ifsc_code.upper().strip()
    
    # Format validation
    if not IFSC_PATTERN.match(ifsc_code):
        result["error"] = "Invalid IFSC format. Must be 4 letters + 0 + 6 alphanumeric characters"
        return result
    
    result["format_valid"] = True
    
    # API lookup using Razorpay's free IFSC API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://ifsc.razorpay.com/{ifsc_code}")
            
            if response.status_code == 200:
                data = response.json()
                result["bank_found"] = True
                result["valid"] = True
                result["bank_name"] = data.get("BANK")
                result["branch"] = data.get("BRANCH")
                result["city"] = data.get("CITY")
                result["state"] = data.get("STATE")
                result["address"] = data.get("ADDRESS")
            elif response.status_code == 404:
                result["error"] = "IFSC code not found in database"
            else:
                result["error"] = f"API error: {response.status_code}"
                
    except httpx.TimeoutException:
        # If API times out, still mark format as valid
        result["error"] = "Bank lookup timed out. Format is valid."
        result["valid"] = result["format_valid"]
    except Exception as e:
        result["error"] = f"Lookup failed: {str(e)}"
        result["valid"] = result["format_valid"]
    
    return result


def validate_account_number(account_number: str, ifsc_code: str = None) -> Dict[str, Any]:
    """
    Validate bank account number format.
    
    If IFSC is provided, validates against bank-specific patterns.
    Otherwise, uses generic validation (9-18 digits).
    
    Returns:
        {
            "valid": bool,
            "format_valid": bool,
            "bank_code": str or None,
            "expected_length": list or None,
            "actual_length": int,
            "error": str or None,
            "warning": str or None
        }
    """
    result = {
        "valid": False,
        "format_valid": False,
        "bank_code": None,
        "expected_length": None,
        "actual_length": 0,
        "error": None,
        "warning": None
    }
    
    if not account_number:
        result["error"] = "Account number is required"
        return result
    
    # Remove spaces and normalize
    account_number = account_number.strip().replace(" ", "").replace("-", "")
    result["actual_length"] = len(account_number)
    
    # Must be all digits
    if not account_number.isdigit():
        result["error"] = "Account number must contain only digits"
        return result
    
    # Bank-specific validation if IFSC provided
    if ifsc_code:
        bank_code = ifsc_code[:4].upper()
        result["bank_code"] = bank_code
        
        if bank_code in BANK_ACCOUNT_PATTERNS:
            bank_info = BANK_ACCOUNT_PATTERNS[bank_code]
            result["expected_length"] = bank_info["length"]
            
            if re.match(bank_info["pattern"], account_number):
                result["valid"] = True
                result["format_valid"] = True
            else:
                result["error"] = f"{bank_info['name']} account numbers are typically {bank_info['length']} digits. You entered {len(account_number)} digits."
                # Still mark as format_valid if it's reasonable length
                if GENERIC_ACCOUNT_PATTERN.match(account_number):
                    result["format_valid"] = True
                    result["warning"] = "Account length doesn't match typical pattern for this bank, but format is acceptable."
        else:
            # Unknown bank - use generic validation
            result["warning"] = f"Bank code {bank_code} not in our database. Using generic validation."
            if GENERIC_ACCOUNT_PATTERN.match(account_number):
                result["valid"] = True
                result["format_valid"] = True
            else:
                result["error"] = "Account number should be 9-18 digits"
    else:
        # Generic validation without IFSC
        if GENERIC_ACCOUNT_PATTERN.match(account_number):
            result["valid"] = True
            result["format_valid"] = True
        else:
            result["error"] = "Account number should be 9-18 digits"
    
    return result


def get_bank_name_from_ifsc(ifsc_code: str) -> Optional[str]:
    """Get bank name from IFSC code prefix."""
    if not ifsc_code or len(ifsc_code) < 4:
        return None
    
    bank_code = ifsc_code[:4].upper()
    if bank_code in BANK_ACCOUNT_PATTERNS:
        return BANK_ACCOUNT_PATTERNS[bank_code]["name"]
    return None


def mask_account_number(account_number: str) -> str:
    """Mask account number for display (show last 4 digits only)."""
    if not account_number or len(account_number) < 4:
        return "****"
    return "X" * (len(account_number) - 4) + account_number[-4:]


# Allowed file types for bank proof documents
ALLOWED_BANK_PROOF_TYPES = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp'
}

MAX_BANK_PROOF_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_bank_proof_file(content_type: str, file_size: int) -> Dict[str, Any]:
    """Validate bank proof document file."""
    result = {
        "valid": False,
        "error": None
    }
    
    if content_type not in ALLOWED_BANK_PROOF_TYPES:
        result["error"] = f"Invalid file type. Allowed: PDF, JPG, PNG, WEBP"
        return result
    
    if file_size > MAX_BANK_PROOF_SIZE:
        result["error"] = f"File too large. Maximum size: 5 MB"
        return result
    
    result["valid"] = True
    return result
