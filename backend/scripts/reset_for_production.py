"""
NETRA ERP - Production Database Reset Script
=============================================
Clears all test/transactional data while preserving system configuration.
Creates a default admin account for production use.

Usage: python scripts/reset_for_production.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import hashlib
import uuid

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# ==================== COLLECTION CATEGORIES ====================

# TRANSACTIONAL DATA - Will be CLEARED
TRANSACTIONAL_COLLECTIONS = [
    # Users & Employees
    "users",
    "employees",
    "employee_documents",
    "employee_change_history",
    "employee_consent_log",
    "employee_consent_status",
    "employee_scorecards",
    "employee_permissions",
    "employee_attendance_policies",
    "onboarding_candidates",
    "onboarding_submissions",
    "profile_change_requests",
    "bank_change_requests",
    "field_change_requests",
    
    # Attendance & Leave
    "attendance",
    "attendance_penalties",
    "leave_requests",
    "leave_balances",
    "leave_balance_snapshots",
    "leave_encashments",
    
    # Payroll
    "payroll",
    "payroll_runs",
    "payroll_inputs",
    "payroll_reimbursements",
    "payroll_reports",
    "salary_slips",
    "salary_revision_log",
    "ctc_structures",
    
    # Sales & Leads
    "leads",
    "prospects",
    "quotations",
    "sales_meetings",
    "sales_mom",
    "sales_targets",
    "yearly_sales_targets",
    "funnel_drafts",
    
    # Consulting Projects
    "projects",
    "project_assignments",
    "project_payments",
    "enhanced_sow",
    "enhanced_sows",
    "sow",
    "sows",
    "sow_attachments",
    "sow_versions",
    "pricing_plans",
    "consultant_assignments",
    "consultant_change_requests",
    "staffing_requests",
    
    # Tasks & Approvals
    "tasks",
    "task_attachments",
    "scope_task_approvals",
    "task_approval_notifications",
    "approvals",
    "approval_requests",
    "approval_entries",
    "stage_approvals",
    "kickoff_requests",
    "kickoff_approvals",
    "modification_requests",
    
    # Meetings
    "meetings",
    "meeting_records",
    "meeting_schedules",
    "meeting_attachments",
    "follow_up_tasks",
    
    # Agreements & Payments
    "agreements",
    "agreement_payments",
    "installment_payments",
    "payment_reminders",
    "payment_verifications",
    "invoices",
    
    # Clients
    "clients",
    "client_users",
    "client_consent_requests",
    "consent_documents",
    "consent_tokens",
    
    # Documents & Letters
    "offer_letters",
    "appointment_letters",
    "drafts",
    
    # Expenses & Travel
    "expenses",
    "travel_claims",
    "travel_reimbursements",
    
    # Timesheets
    "timesheets",
    
    # Communications
    "notifications",
    "chat_messages",
    "chat_conversations",
    "ai_chat_history",
    "email_logs",
    "email_action_tokens",
    
    # Audit & Logs
    "audit_logs",
    "admin_audit_logs",
    "go_live_audit_logs",
    "permission_audit_logs",
    "security_audit_logs",
    "security_events",
    "department_access_logs",
    "documentation_logs",
    "integrity_audit_reports",
    
    # Go-Live & Onboarding
    "go_live_requests",
    "user_guidance_state",
    "help_user_progress",
    
    # OTP & Tokens
    "otp_tokens",
    
    # Role Requests
    "role_requests",
    
    # Incentives
    "incentive_eligibility",
]

# SYSTEM CONFIGURATION - Will be PRESERVED
PRESERVED_COLLECTIONS = [
    # RBAC & Permissions
    "rbac_roles",
    "rbac_departments",
    "rbac_role_groups",
    "rbac_locks",
    "roles",
    "role_permissions",
    "level_permissions_config",
    "department_access",
    "approval_configs",
    
    # System Settings
    "settings",
    "email_settings",
    "email_templates",
    "letterhead_settings",
    "letter_templates",
    
    # Master Data
    "department_config",
    "designation_department_mappings",
    "holidays",
    "public_holidays",
    "leave_policies",
    "ctc_config",
    "payroll_config",
    
    # SOW Templates
    "sow_categories",
    "sow_scope_templates",
    
    # Help System
    "help_categories",
    "help_topics",
]


async def reset_database():
    """Main reset function."""
    print("=" * 60)
    print("NETRA ERP - Production Database Reset")
    print("=" * 60)
    print(f"\nDatabase: {db_name}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("\n" + "=" * 60)
    
    # Connect to database
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get all existing collections
    existing_collections = await db.list_collection_names()
    
    cleared_collections = []
    preserved_collections = []
    skipped_collections = []
    errors = []
    
    # Phase 1: Clear transactional collections
    print("\n[PHASE 1] Clearing transactional data...")
    print("-" * 40)
    
    for coll_name in TRANSACTIONAL_COLLECTIONS:
        if coll_name in existing_collections:
            try:
                count_before = await db[coll_name].count_documents({})
                await db[coll_name].delete_many({})
                cleared_collections.append({
                    "name": coll_name,
                    "documents_cleared": count_before
                })
                print(f"  [CLEARED] {coll_name}: {count_before} documents")
            except Exception as e:
                errors.append({"collection": coll_name, "error": str(e)})
                print(f"  [ERROR] {coll_name}: {e}")
        else:
            skipped_collections.append(coll_name)
    
    # Phase 2: Verify preserved collections
    print("\n[PHASE 2] Verifying preserved configuration...")
    print("-" * 40)
    
    for coll_name in PRESERVED_COLLECTIONS:
        if coll_name in existing_collections:
            count = await db[coll_name].count_documents({})
            preserved_collections.append({
                "name": coll_name,
                "documents_retained": count
            })
            print(f"  [PRESERVED] {coll_name}: {count} documents")
        else:
            print(f"  [NOT FOUND] {coll_name}")
    
    # Phase 3: Reset auto-increment counters
    print("\n[PHASE 3] Resetting counters...")
    print("-" * 40)
    
    # Reset employee ID counter
    await db.settings.update_one(
        {"key": "employee_id_counter"},
        {"$set": {"value": 1}},
        upsert=True
    )
    print("  [RESET] Employee ID counter -> 1")
    
    # Reset client ID counter
    await db.settings.update_one(
        {"key": "client_id_counter"},
        {"$set": {"value": 98001}},
        upsert=True
    )
    print("  [RESET] Client ID counter -> 98001")
    
    # Reset lead counter
    await db.settings.update_one(
        {"key": "lead_counter"},
        {"$set": {"value": 1}},
        upsert=True
    )
    print("  [RESET] Lead counter -> 1")
    
    # Phase 4: Create default admin account
    print("\n[PHASE 4] Creating default admin account...")
    print("-" * 40)
    
    admin_user_id = str(uuid.uuid4())
    admin_employee_id = "ADMIN001"
    admin_password = "Admin@2026"  # Should be changed on first login
    password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    now = datetime.now(timezone.utc)
    
    # Create admin user
    admin_user = {
        "id": admin_user_id,
        "employee_id": admin_employee_id,
        "email": "dharmesh.parikh@dvconsulting.co.in",
        "password_hash": password_hash,
        "role": "admin",
        "department": "Administration",
        "is_active": True,
        "must_change_password": True,
        "created_at": now,
        "updated_at": now
    }
    
    await db.users.insert_one(admin_user)
    print(f"  [CREATED] Admin user: {admin_employee_id}")
    
    # Create admin employee record
    admin_employee = {
        "id": admin_user_id,
        "user_id": admin_user_id,
        "employee_id": admin_employee_id,
        "first_name": "Dharmesh",
        "last_name": "Parikh",
        "email": "dharmesh.parikh@dvconsulting.co.in",
        "phone": "",
        "role": "admin",
        "department": "Administration",
        "designation": "System Administrator",
        "status": "active",
        "employment_type": "full_time",
        "date_of_joining": now.date().isoformat(),
        "created_at": now,
        "updated_at": now,
        "go_live_status": "completed",
        "is_system_admin": True
    }
    
    await db.employees.insert_one(admin_employee)
    print(f"  [CREATED] Admin employee record")
    
    # Phase 5: Generate report
    print("\n" + "=" * 60)
    print("RESET COMPLETE - SUMMARY REPORT")
    print("=" * 60)
    
    total_cleared = sum(c["documents_cleared"] for c in cleared_collections)
    total_preserved = sum(c["documents_retained"] for c in preserved_collections)
    
    report = {
        "timestamp": now.isoformat(),
        "database": db_name,
        "summary": {
            "collections_cleared": len(cleared_collections),
            "documents_cleared": total_cleared,
            "collections_preserved": len(preserved_collections),
            "documents_preserved": total_preserved,
            "errors": len(errors)
        },
        "cleared_collections": cleared_collections,
        "preserved_collections": preserved_collections,
        "admin_account": {
            "employee_id": admin_employee_id,
            "email": "dharmesh.parikh@dvconsulting.co.in",
            "temporary_password": admin_password,
            "note": "CHANGE PASSWORD ON FIRST LOGIN"
        },
        "counters_reset": [
            "employee_id_counter -> 1",
            "client_id_counter -> 98001",
            "lead_counter -> 1"
        ],
        "errors": errors
    }
    
    print(f"\nCollections Cleared: {len(cleared_collections)}")
    print(f"Documents Removed: {total_cleared}")
    print(f"Collections Preserved: {len(preserved_collections)}")
    print(f"Documents Retained: {total_preserved}")
    print(f"Errors: {len(errors)}")
    
    print("\n" + "-" * 40)
    print("DEFAULT ADMIN CREDENTIALS")
    print("-" * 40)
    print(f"  Employee ID: {admin_employee_id}")
    print(f"  Email: dharmesh.parikh@dvconsulting.co.in")
    print(f"  Password: {admin_password}")
    print("  ** CHANGE PASSWORD ON FIRST LOGIN **")
    
    if errors:
        print("\n" + "-" * 40)
        print("ERRORS ENCOUNTERED")
        print("-" * 40)
        for err in errors:
            print(f"  {err['collection']}: {err['error']}")
    
    # Save report to file
    report_path = Path(__file__).parent.parent / "reset_report.json"
    import json
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")
    
    # Close connection
    client.close()
    
    return report


if __name__ == "__main__":
    print("\n" + "!" * 60)
    print("WARNING: This will permanently delete all transactional data!")
    print("!" * 60)
    
    confirm = input("\nType 'RESET PRODUCTION' to confirm: ")
    
    if confirm == "RESET PRODUCTION":
        asyncio.run(reset_database())
    else:
        print("\nReset cancelled.")
