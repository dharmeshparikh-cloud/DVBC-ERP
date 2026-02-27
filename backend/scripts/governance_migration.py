"""
Database Indexes & Integrity Migration Script
Ensures single source of truth and prevents duplicates.

Run with: python -m scripts.governance_migration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "netra")


async def run_migration():
    """Run the governance migration to add indexes and clean up duplicates."""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 60)
    print("NETRA ERP - Governance Migration")
    print("=" * 60)
    
    # ========== 1. CREATE INDEXES ==========
    print("\n1. Creating indexes for data integrity...")
    
    try:
        # Unique index on employee_id (excluding null values)
        await db.employees.create_index(
            "employee_id",
            unique=True,
            sparse=True,  # Allow multiple null values
            name="unique_employee_id"
        )
        print("   ✓ Created unique index on employees.employee_id")
    except Exception as e:
        print(f"   ! Index employees.employee_id: {e}")
    
    try:
        # Unique index on email in employees
        await db.employees.create_index(
            "email",
            unique=True,
            sparse=True,
            name="unique_employee_email"
        )
        print("   ✓ Created unique index on employees.email")
    except Exception as e:
        print(f"   ! Index employees.email: {e}")
    
    try:
        # Unique index on users
        await db.users.create_index(
            "employee_id",
            unique=True,
            sparse=True,
            name="unique_user_employee_id"
        )
        print("   ✓ Created unique index on users.employee_id")
    except Exception as e:
        print(f"   ! Index users.employee_id: {e}")
    
    try:
        # Index on employee_change_history for fast lookups
        await db.employee_change_history.create_index(
            [("employee_id", 1), ("timestamp", -1)],
            name="idx_change_history_lookup"
        )
        print("   ✓ Created index on employee_change_history")
    except Exception as e:
        print(f"   ! Index employee_change_history: {e}")
    
    try:
        # Index on consent log
        await db.employee_consent_log.create_index(
            [("employee_id", 1), ("document_type", 1)],
            name="idx_consent_log_lookup"
        )
        print("   ✓ Created index on employee_consent_log")
    except Exception as e:
        print(f"   ! Index employee_consent_log: {e}")
    
    try:
        # Index on field change requests
        await db.field_change_requests.create_index(
            [("status", 1), ("created_at", -1)],
            name="idx_field_change_requests"
        )
        print("   ✓ Created index on field_change_requests")
    except Exception as e:
        print(f"   ! Index field_change_requests: {e}")
    
    # ========== 2. CHECK FOR DUPLICATES ==========
    print("\n2. Checking for duplicate data...")
    
    # Check duplicate employee_ids
    pipeline = [
        {"$match": {"employee_id": {"$ne": None}}},
        {"$group": {"_id": "$employee_id", "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = await db.employees.aggregate(pipeline).to_list(100)
    if duplicates:
        print(f"   ⚠ Found {len(duplicates)} duplicate employee_ids:")
        for dup in duplicates:
            print(f"      - {dup['_id']}: {dup['count']} records")
    else:
        print("   ✓ No duplicate employee_ids found")
    
    # Check duplicate emails
    pipeline = [
        {"$match": {"email": {"$ne": None}}},
        {"$group": {"_id": "$email", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dup_emails = await db.employees.aggregate(pipeline).to_list(100)
    if dup_emails:
        print(f"   ⚠ Found {len(dup_emails)} duplicate emails")
    else:
        print("   ✓ No duplicate emails found")
    
    # ========== 3. CHECK CIRCULAR REPORTING ==========
    print("\n3. Checking for circular reporting chains...")
    
    employees = await db.employees.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "employee_id": 1, "full_name": 1, "reporting_manager_id": 1}
    ).to_list(1000)
    
    emp_map = {e["id"]: e for e in employees}
    circular_count = 0
    
    for emp in employees:
        chain = set()
        current = emp
        while current:
            if current["id"] in chain:
                circular_count += 1
                print(f"   ⚠ Circular chain: {emp.get('employee_id')} ({emp.get('full_name')})")
                break
            chain.add(current["id"])
            manager_id = current.get("reporting_manager_id")
            current = emp_map.get(manager_id) if manager_id else None
    
    if circular_count == 0:
        print("   ✓ No circular reporting chains found")
    
    # ========== 4. CHECK SALARY/CTC MISMATCHES ==========
    print("\n4. Checking for salary/CTC mismatches...")
    
    employees_with_ctc = await db.employees.find(
        {"ctc_structure_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "employee_id": 1, "salary": 1, "ctc_structure_id": 1}
    ).to_list(1000)
    
    mismatch_count = 0
    for emp in employees_with_ctc:
        ctc = await db.ctc_structures.find_one(
            {"id": emp["ctc_structure_id"], "status": "approved"},
            {"_id": 0, "annual_ctc": 1}
        )
        if ctc and emp.get("salary") != ctc.get("annual_ctc"):
            mismatch_count += 1
    
    if mismatch_count > 0:
        print(f"   ⚠ Found {mismatch_count} salary/CTC mismatches - run sync")
    else:
        print("   ✓ No salary/CTC mismatches")
    
    # ========== 5. INITIALIZE CONSENT DOCUMENTS ==========
    print("\n5. Initializing consent document templates...")
    
    existing_docs = await db.consent_documents.count_documents({})
    if existing_docs == 0:
        from routers.employee_consent import DEFAULT_CONSENT_DOCUMENTS
        now = datetime.now(timezone.utc).isoformat()
        
        for doc_type, doc_data in DEFAULT_CONSENT_DOCUMENTS.items():
            doc = {
                "id": str(__import__('uuid').uuid4()),
                "type": doc_type,
                **doc_data,
                "created_at": now,
                "is_active": True
            }
            await db.consent_documents.insert_one(doc)
        
        print(f"   ✓ Created {len(DEFAULT_CONSENT_DOCUMENTS)} consent document templates")
    else:
        print(f"   ✓ {existing_docs} consent documents already exist")
    
    # ========== 6. SUMMARY ==========
    print("\n" + "=" * 60)
    print("Migration Complete")
    print("=" * 60)
    
    # Stats
    total_employees = await db.employees.count_documents({})
    active_employees = await db.employees.count_documents({"is_active": True})
    pending_golive = await db.employees.count_documents({"employee_id_pending": True})
    change_history_count = await db.employee_change_history.count_documents({})
    
    print(f"""
Stats:
  - Total employees: {total_employees}
  - Active employees: {active_employees}
  - Pending Go-Live: {pending_golive}
  - Change history records: {change_history_count}
  - Duplicates found: {len(duplicates)}
  - Circular chains: {circular_count}
  - Salary mismatches: {mismatch_count}
""")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
