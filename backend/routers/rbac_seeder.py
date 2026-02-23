"""
RBAC Seeder & Sync Script
==========================
Phase 3: Ensures all hardcoded roles from deps.py are synced to the database.

This script:
1. Reads current role definitions from deps.py (source of truth during migration)
2. Compares with database roles
3. Creates/updates any missing or outdated roles
4. Maintains backward compatibility during migration

Run: python -m routers.rbac_seeder
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ROLE DEFINITIONS ====================
# These are the canonical definitions that match deps.py
# During Phase 4, deps.py will import from rbac_service instead

ROLE_DEFINITIONS = {
    "admin": {
        "name": "Administrator",
        "description": "Full system access",
        "level": 100,
        "department": "Operations",
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": [],
        "permissions": ["*"],
    },
    "hr_manager": {
        "name": "HR Manager",
        "description": "HR department head",
        "level": 80,
        "department": "HR",
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": ["hr_executive"],
        "permissions": ["hr.*", "employees.*", "attendance.*", "leaves.*", "payroll.view"],
    },
    "hr_executive": {
        "name": "HR Executive",
        "description": "HR team member",
        "level": 40,
        "department": "HR",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["hr.view", "employees.view", "attendance.*", "leaves.view"],
    },
    "sales_manager": {
        "name": "Sales Manager",
        "description": "Sales department head",
        "level": 80,
        "department": "Sales",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["sales_executive"],
        "permissions": ["sales.*", "leads.*", "agreements.view", "quotations.*", "reports.sales"],
    },
    "sales_executive": {
        "name": "Sales Executive",
        "description": "Sales team member",
        "level": 40,
        "department": "Sales",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["leads.own", "meetings.own", "quotations.create", "agreements.create"],
    },
    "executive": {
        "name": "Executive",
        "description": "Sales Executive (legacy code)",
        "level": 40,
        "department": "Sales",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["leads.own", "meetings.own", "quotations.create", "agreements.create"],
    },
    "manager": {
        "name": "Manager",
        "description": "General manager role",
        "level": 75,
        "department": "Operations",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["team.*", "reports.*", "approvals.*"],
    },
    "sr_manager": {
        "name": "Senior Manager",
        "description": "Senior manager role",
        "level": 85,
        "department": "Operations",
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": ["manager"],
        "permissions": ["team.*", "reports.*", "approvals.*", "budget.*"],
    },
    "principal_consultant": {
        "name": "Principal Consultant",
        "description": "Senior-most consulting role, can approve kickoffs",
        "level": 90,
        "department": "Consulting",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["senior_consultant"],
        "permissions": ["consulting.*", "projects.*", "kickoff.approve", "agreements.approve", "sow.*"],
    },
    "senior_consultant": {
        "name": "Senior Consultant",
        "description": "Senior consulting role",
        "level": 70,
        "department": "Consulting",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["lead_consultant"],
        "permissions": ["consulting.*", "projects.manage", "sow.*", "meetings.*"],
    },
    "lead_consultant": {
        "name": "Lead Consultant",
        "description": "Lead consulting role",
        "level": 60,
        "department": "Consulting",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": ["consultant"],
        "permissions": ["consulting.*", "projects.view", "sow.create", "meetings.*"],
    },
    "consultant": {
        "name": "Consultant",
        "description": "Standard consulting role",
        "level": 50,
        "department": "Consulting",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["consulting.own", "projects.view", "meetings.own", "attendance.own"],
    },
    "lean_consultant": {
        "name": "Lean Consultant",
        "description": "Lean/efficiency focused consultant",
        "level": 50,
        "department": "Consulting",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["consulting.own", "projects.view", "meetings.own"],
    },
    "subject_matter_expert": {
        "name": "Subject Matter Expert",
        "description": "Domain expert consultant",
        "level": 55,
        "department": "Consulting",
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": ["consultant"],
        "permissions": ["consulting.*", "projects.view", "sow.review"],
    },
    "finance_manager": {
        "name": "Finance Manager",
        "description": "Finance department head",
        "level": 80,
        "department": "Finance",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["finance.*", "payments.*", "invoices.*", "reports.finance"],
    },
    "project_manager": {
        "name": "Project Manager",
        "description": "Manages project delivery and team coordination",
        "level": 70,
        "department": "Consulting",
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["consultant"],
        "permissions": ["projects.*", "consulting.*", "meetings.*", "attendance.team"],
    },
    "client": {
        "name": "Client",
        "description": "External client user",
        "level": 10,
        "department": "External",
        "can_approve": False,
        "can_manage_users": False,
        "is_external": True,
        "inherits_from": [],
        "permissions": ["client_portal.*"],
    },
}

# Role group definitions - these map to the constants in deps.py
ROLE_GROUP_DEFINITIONS = {
    "ADMIN_ROLES": {
        "name": "Admin Roles",
        "description": "Full system administrators",
        "roles": ["admin"],
        "is_system": True,
    },
    "HR_ROLES": {
        "name": "HR Roles",
        "description": "All HR department roles",
        "roles": ["admin", "hr_manager", "hr_executive"],
        "is_system": True,
    },
    "HR_ADMIN_ROLES": {
        "name": "HR Admin Roles",
        "description": "HR roles with admin privileges",
        "roles": ["admin", "hr_manager"],
        "is_system": True,
    },
    "SALES_ROLES": {
        "name": "Sales Roles",
        "description": "All sales department roles",
        "roles": ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive", "sales_executive"],
        "is_system": True,
    },
    "SALES_MANAGER_ROLES": {
        "name": "Sales Manager Roles",
        "description": "Sales roles with management privileges",
        "roles": ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"],
        "is_system": True,
    },
    "SALES_EXECUTIVE_ROLES": {
        "name": "Sales Executive Roles",
        "description": "Sales executive level roles",
        "roles": ["admin", "executive", "sales_executive", "sales_manager"],
        "is_system": True,
    },
    "PROJECT_ROLES": {
        "name": "Project Roles",
        "description": "Roles with project management access",
        "roles": ["admin", "principal_consultant", "senior_consultant", "manager", "project_manager"],
        "is_system": True,
    },
    "SENIOR_CONSULTING_ROLES": {
        "name": "Senior Consulting Roles",
        "description": "Senior-level consulting roles",
        "roles": ["admin", "principal_consultant", "senior_consultant"],
        "is_system": True,
    },
    "PRINCIPAL_CONSULTANT_ROLES": {
        "name": "Principal Consultant Roles",
        "description": "Principal consultant and admin only",
        "roles": ["admin", "principal_consultant"],
        "is_system": True,
    },
    "CONSULTING_ROLES": {
        "name": "Consulting Roles",
        "description": "All consulting department roles",
        "roles": ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"],
        "is_system": True,
    },
    "FINANCE_ROLES": {
        "name": "Finance Roles",
        "description": "Finance department roles",
        "roles": ["admin", "finance_manager"],
        "is_system": True,
    },
    "MANAGER_ROLES": {
        "name": "Manager Roles",
        "description": "All manager-level roles",
        "roles": ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"],
        "is_system": True,
    },
    "APPROVAL_ROLES": {
        "name": "Approval Roles",
        "description": "Roles that can approve requests",
        "roles": ["admin", "manager", "hr_manager", "principal_consultant"],
        "is_system": True,
    },
    "HR_PM_ROLES": {
        "name": "HR and PM Roles",
        "description": "HR and project management roles",
        "roles": ["admin", "hr_manager", "hr_executive", "principal_consultant"],
        "is_system": True,
    },
    "EMPLOYEE_ROLES": {
        "name": "Employee Roles",
        "description": "All internal employee roles",
        "roles": [
            "admin", "hr_manager", "hr_executive",
            "sales_manager", "manager", "sr_manager", "executive", "sales_executive",
            "consultant", "lean_consultant", "lead_consultant", "senior_consultant", 
            "principal_consultant", "subject_matter_expert", "finance_manager", "project_manager"
        ],
        "is_system": True,
    },
    "AGREEMENT_APPROVE_ROLES": {
        "name": "Agreement Approval Roles",
        "description": "Roles that can approve agreements",
        "roles": ["admin", "principal_consultant"],
        "is_system": True,
    },
}

DEPARTMENT_DEFINITIONS = [
    {"code": "HR", "name": "Human Resources", "color": "#8B5CF6"},
    {"code": "Sales", "name": "Sales & Business Development", "color": "#F59E0B"},
    {"code": "Consulting", "name": "Consulting & Delivery", "color": "#10B981"},
    {"code": "Finance", "name": "Finance & Accounts", "color": "#3B82F6"},
    {"code": "Operations", "name": "Operations & Admin", "color": "#6B7280"},
    {"code": "External", "name": "External Users", "color": "#EC4899"},
]


async def sync_roles(db) -> Dict[str, Any]:
    """Sync role definitions to database."""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0
    unchanged = 0
    
    for code, role_data in ROLE_DEFINITIONS.items():
        existing = await db.rbac_roles.find_one({"code": code})
        
        role_doc = {
            "code": code,
            **role_data,
            "is_active": True,
            "updated_at": now,
            "updated_by": "rbac_seeder"
        }
        
        if existing:
            # Check if update needed
            needs_update = False
            for key in ["name", "description", "level", "department", "can_approve", 
                       "can_manage_users", "permissions", "inherits_from"]:
                if existing.get(key) != role_data.get(key):
                    needs_update = True
                    break
            
            if needs_update:
                await db.rbac_roles.update_one(
                    {"code": code},
                    {"$set": role_doc}
                )
                updated += 1
                logger.info(f"Updated role: {code}")
            else:
                unchanged += 1
        else:
            role_doc["created_at"] = now
            role_doc["created_by"] = "rbac_seeder"
            await db.rbac_roles.insert_one(role_doc)
            created += 1
            logger.info(f"Created role: {code}")
    
    return {"created": created, "updated": updated, "unchanged": unchanged}


async def sync_role_groups(db) -> Dict[str, Any]:
    """Sync role group definitions to database."""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0
    unchanged = 0
    
    for code, group_data in ROLE_GROUP_DEFINITIONS.items():
        existing = await db.rbac_role_groups.find_one({"code": code})
        
        group_doc = {
            "code": code,
            **group_data,
            "updated_at": now,
            "updated_by": "rbac_seeder"
        }
        
        if existing:
            # Check if roles changed
            if set(existing.get("roles", [])) != set(group_data["roles"]):
                await db.rbac_role_groups.update_one(
                    {"code": code},
                    {"$set": group_doc}
                )
                updated += 1
                logger.info(f"Updated role group: {code}")
            else:
                unchanged += 1
        else:
            group_doc["created_at"] = now
            group_doc["created_by"] = "rbac_seeder"
            await db.rbac_role_groups.insert_one(group_doc)
            created += 1
            logger.info(f"Created role group: {code}")
    
    return {"created": created, "updated": updated, "unchanged": unchanged}


async def sync_departments(db) -> Dict[str, Any]:
    """Sync department definitions to database."""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0
    unchanged = 0
    
    for dept in DEPARTMENT_DEFINITIONS:
        existing = await db.rbac_departments.find_one({"code": dept["code"]})
        
        dept_doc = {
            **dept,
            "is_active": True,
            "updated_at": now,
            "updated_by": "rbac_seeder"
        }
        
        if existing:
            if existing.get("name") != dept["name"] or existing.get("color") != dept["color"]:
                await db.rbac_departments.update_one(
                    {"code": dept["code"]},
                    {"$set": dept_doc}
                )
                updated += 1
                logger.info(f"Updated department: {dept['code']}")
            else:
                unchanged += 1
        else:
            dept_doc["created_at"] = now
            dept_doc["created_by"] = "rbac_seeder"
            await db.rbac_departments.insert_one(dept_doc)
            created += 1
            logger.info(f"Created department: {dept['code']}")
    
    return {"created": created, "updated": updated, "unchanged": unchanged}


async def create_indexes(db):
    """Create database indexes for RBAC collections."""
    await db.rbac_roles.create_index("code", unique=True)
    await db.rbac_departments.create_index("code", unique=True)
    await db.rbac_role_groups.create_index("code", unique=True)
    logger.info("Created RBAC indexes")


async def run_sync():
    """Main sync function."""
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    if not mongo_url or not db_name:
        logger.error("MONGO_URL and DB_NAME environment variables required")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    logger.info("=" * 50)
    logger.info("RBAC Seeder - Starting sync")
    logger.info("=" * 50)
    
    # Create indexes
    await create_indexes(db)
    
    # Sync departments
    logger.info("\n--- Syncing Departments ---")
    dept_result = await sync_departments(db)
    logger.info(f"Departments: {dept_result}")
    
    # Sync roles
    logger.info("\n--- Syncing Roles ---")
    roles_result = await sync_roles(db)
    logger.info(f"Roles: {roles_result}")
    
    # Sync role groups
    logger.info("\n--- Syncing Role Groups ---")
    groups_result = await sync_role_groups(db)
    logger.info(f"Role Groups: {groups_result}")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("RBAC Seeder - Sync Complete")
    logger.info("=" * 50)
    logger.info(f"Departments: {dept_result['created']} created, {dept_result['updated']} updated")
    logger.info(f"Roles: {roles_result['created']} created, {roles_result['updated']} updated")
    logger.info(f"Role Groups: {groups_result['created']} created, {groups_result['updated']} updated")
    
    client.close()
    
    return {
        "departments": dept_result,
        "roles": roles_result,
        "role_groups": groups_result
    }


if __name__ == "__main__":
    asyncio.run(run_sync())
