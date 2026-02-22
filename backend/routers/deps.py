"""
Shared dependencies for all routers.
Contains database connection, authentication, and common utilities.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
import os
import re

# ==================== ROLE CONSTANTS ====================
# Use these instead of hard-coded arrays in role checks

# Admin-level roles (full system access)
ADMIN_ROLES = ["admin"]

# HR department roles
HR_ROLES = ["admin", "hr_manager", "hr_executive"]
HR_ADMIN_ROLES = ["admin", "hr_manager"]

# Sales department roles  
SALES_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive"]
SALES_MANAGER_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"]
SALES_EXECUTIVE_ROLES = ["admin", "executive", "sales_manager"]

# Project management roles
PROJECT_ROLES = ["admin", "project_manager", "manager"]
PROJECT_PM_ROLES = ["admin", "project_manager", "principal_consultant", "senior_consultant", "manager"]

# Consulting roles
CONSULTING_ROLES = ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]
SENIOR_CONSULTING_ROLES = ["admin", "principal_consultant", "senior_consultant", "project_manager"]

# Finance roles
FINANCE_ROLES = ["admin", "finance_manager"]

# All manager-level roles
MANAGER_ROLES = ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "project_manager", "principal_consultant"]

# Approval roles (can approve various requests)
APPROVAL_ROLES = ["admin", "manager", "hr_manager", "project_manager", "principal_consultant"]

# HR + Project Manager (for attendance, etc.)
HR_PM_ROLES = ["admin", "hr_manager", "hr_executive", "project_manager"]

# Default pagination limits
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
LARGE_QUERY_SIZE = 500

# ==================== DATABASE ====================
# Database reference - set by main server
db = None

def set_db(database):
    """Set the database reference for all routers."""
    global db
    db = database

def get_db():
    """Get the database reference."""
    if db is None:
        raise RuntimeError("Database not initialized")
    return db

# JWT Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Helper function to sanitize user input (prevent XSS)
def sanitize_text(text: str) -> str:
    """Remove HTML tags and dangerous characters from text."""
    if not text or not isinstance(text, str):
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]*>', '', text)
    # Remove script-related keywords
    clean = re.sub(r'javascript:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onerror\s*=', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onclick\s*=', '', clean, flags=re.IGNORECASE)
    return clean.strip()


def clean_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove MongoDB ObjectId from document for JSON serialization.
    Removes _id and converts any ObjectId values to strings.
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [clean_mongo_doc(d) for d in doc]
    if not isinstance(doc, dict):
        return doc
    
    cleaned = {}
    for key, value in doc.items():
        if key == "_id":
            continue  # Skip MongoDB's _id field
        if isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, dict):
            cleaned[key] = clean_mongo_doc(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_mongo_doc(v) if isinstance(v, dict) else (str(v) if isinstance(v, ObjectId) else v) for v in value]
        else:
            cleaned[key] = value
    return cleaned


def clean_mongo_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean a list of MongoDB documents."""
    return [clean_mongo_doc(doc) for doc in docs]
