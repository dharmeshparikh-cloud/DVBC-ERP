"""
Governance Audit Report Generator

Generates comprehensive reports for:
1. Data inheritance diagram
2. Edit permission matrix
3. Sync propagation mapping
4. Duplicate risk report
5. Field change audit trail
"""

import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import json

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "netra")


async def generate_full_governance_report():
    """Generate comprehensive governance audit report."""
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {}
    }
    
    print("=" * 70)
    print("NETRA ERP - GOVERNANCE AUDIT REPORT")
    print("=" * 70)
    print(f"Generated: {report['generated_at']}")
    print()
    
    # ========== SECTION 1: DATA INHERITANCE DIAGRAM ==========
    print("SECTION 1: DATA INHERITANCE DIAGRAM")
    print("-" * 70)
    
    inheritance = {
        "employee_master": {
            "description": "Single source of truth for all employee data",
            "collection": "employees",
            "primary_key": "id",
            "unique_fields": ["employee_id", "email"],
            "inherited_from": {
                "department": "Onboarding → Locked post Go-Live → Transfer workflow",
                "designation": "Onboarding → Locked post Go-Live → Promotion workflow",
                "salary": "CTC Designer → Locked → CTC Revision workflow",
                "reporting_manager": "Onboarding → Hierarchy Change workflow"
            }
        },
        "ctc_structures": {
            "description": "CTC breakdown and salary components",
            "inherits_to": "employees.salary, employees.annual_ctc",
            "workflow": "CTC Designer → Admin Approval → Auto-sync to employee"
        },
        "onboarding_submissions": {
            "description": "Initial employee data capture",
            "inherits_to": "employees (on completion)",
            "workflow": "Candidate form → HR review → Employee creation"
        }
    }
    
    print(json.dumps(inheritance, indent=2))
    report["sections"]["data_inheritance"] = inheritance
    
    # ========== SECTION 2: EDIT PERMISSION MATRIX ==========
    print()
    print("SECTION 2: EDIT PERMISSION MATRIX")
    print("-" * 70)
    
    from routers.employee_governance import FIELD_PERMISSIONS
    
    permission_matrix = {
        "locked_fields": [],
        "hr_editable": [],
        "admin_only": [],
        "requires_approval": [],
        "workflow_required": {}
    }
    
    for field, config in FIELD_PERMISSIONS.items():
        if config.get("immutable") or config.get("locked"):
            permission_matrix["locked_fields"].append(field)
            if config.get("workflow"):
                permission_matrix["workflow_required"][field] = config["workflow"]
        elif "admin" in config.get("edit_roles", []) and len(config.get("edit_roles", [])) == 1:
            permission_matrix["admin_only"].append(field)
        elif config.get("requires_approval"):
            permission_matrix["requires_approval"].append(field)
        elif any(r in config.get("edit_roles", []) for r in ["hr_manager", "hr_executive"]):
            permission_matrix["hr_editable"].append(field)
    
    print(f"Locked fields (workflow required): {len(permission_matrix['locked_fields'])}")
    for f in permission_matrix["locked_fields"]:
        workflow = permission_matrix["workflow_required"].get(f, "N/A")
        print(f"  - {f} → {workflow}")
    
    print(f"\nAdmin only: {permission_matrix['admin_only']}")
    print(f"Requires approval: {permission_matrix['requires_approval']}")
    print(f"HR editable: {permission_matrix['hr_editable'][:10]}...")
    
    report["sections"]["permission_matrix"] = permission_matrix
    
    # ========== SECTION 3: SYNC PROPAGATION MAPPING ==========
    print()
    print("SECTION 3: SYNC PROPAGATION MAPPING")
    print("-" * 70)
    
    sync_mapping = {
        "salary": {
            "source": "ctc_structures (annual_ctc)",
            "destinations": ["employees.salary", "employees.annual_ctc"],
            "sync_trigger": "CTC approval or manual sync",
            "apis": ["POST /api/governance/sync-salary/{id}", "POST /api/ctc/{id}/approve"],
            "dashboards": ["HR Dashboard", "Payroll", "Employee Details"]
        },
        "department": {
            "source": "employees",
            "references": ["users.department (legacy)", "onboarding_submissions.hr_assigned.department"],
            "note": "department_access router keeps users.department in sync",
            "apis": ["PATCH /api/employees/{id}", "POST /api/department-access/grant"]
        },
        "employee_id": {
            "source": "Generated at Go-Live approval",
            "destinations": ["employees.employee_id", "users.employee_id"],
            "sync_trigger": "Go-Live approval",
            "apis": ["POST /api/go-live/{id}/approve"]
        }
    }
    
    print(json.dumps(sync_mapping, indent=2))
    report["sections"]["sync_mapping"] = sync_mapping
    
    # ========== SECTION 4: DUPLICATE RISK REPORT ==========
    print()
    print("SECTION 4: DUPLICATE RISK REPORT")
    print("-" * 70)
    
    # Check duplicate employee_ids
    pipeline = [
        {"$match": {"employee_id": {"$ne": None}}},
        {"$group": {"_id": "$employee_id", "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dup_emp_ids = await db.employees.aggregate(pipeline).to_list(100)
    
    # Check duplicate emails
    pipeline = [
        {"$match": {"email": {"$ne": None}}},
        {"$group": {"_id": "$email", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dup_emails = await db.employees.aggregate(pipeline).to_list(100)
    
    # Check employees without employee_id
    no_id = await db.employees.count_documents({
        "is_active": True,
        "$or": [{"employee_id": None}, {"employee_id": ""}, {"employee_id": {"$exists": False}}]
    })
    
    # Check circular reporting
    employees = await db.employees.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "employee_id": 1, "reporting_manager_id": 1}
    ).to_list(1000)
    
    emp_map = {e["id"]: e for e in employees}
    circular = []
    for emp in employees:
        chain = set()
        current = emp
        while current:
            if current["id"] in chain:
                circular.append(emp["employee_id"])
                break
            chain.add(current["id"])
            manager_id = current.get("reporting_manager_id")
            current = emp_map.get(manager_id) if manager_id else None
    
    duplicate_report = {
        "duplicate_employee_ids": [{"id": d["_id"], "count": d["count"]} for d in dup_emp_ids],
        "duplicate_emails": [{"email": d["_id"], "count": d["count"]} for d in dup_emails],
        "employees_without_id": no_id,
        "circular_reporting_chains": circular,
        "risk_level": "HIGH" if (dup_emp_ids or dup_emails or circular) else "LOW"
    }
    
    print(f"Duplicate employee_ids: {len(dup_emp_ids)}")
    print(f"Duplicate emails: {len(dup_emails)}")
    print(f"Employees without ID: {no_id}")
    print(f"Circular reporting: {len(circular)}")
    print(f"Risk Level: {duplicate_report['risk_level']}")
    
    report["sections"]["duplicate_risk"] = duplicate_report
    
    # ========== SECTION 5: AUDIT TRAIL SUMMARY ==========
    print()
    print("SECTION 5: AUDIT TRAIL SUMMARY")
    print("-" * 70)
    
    total_changes = await db.employee_change_history.count_documents({})
    
    # Changes by field
    pipeline = [
        {"$group": {"_id": "$field", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_field = await db.employee_change_history.aggregate(pipeline).to_list(10)
    
    # Recent changes
    recent = await db.employee_change_history.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(5).to_list(5)
    
    audit_summary = {
        "total_change_records": total_changes,
        "changes_by_field": {d["_id"]: d["count"] for d in by_field},
        "recent_changes": recent
    }
    
    print(f"Total change records: {total_changes}")
    print(f"Changes by field: {audit_summary['changes_by_field']}")
    
    report["sections"]["audit_summary"] = audit_summary
    
    # ========== SECTION 6: CONSENT STATUS ==========
    print()
    print("SECTION 6: CONSENT STATUS")
    print("-" * 70)
    
    total_consent_docs = await db.consent_documents.count_documents({"is_active": True})
    total_consents = await db.employee_consent_log.count_documents({})
    pending_consents = await db.employee_consent_status.count_documents({"all_consents_complete": False})
    
    consent_status = {
        "active_consent_documents": total_consent_docs,
        "total_consent_records": total_consents,
        "employees_pending_consent": pending_consents
    }
    
    print(f"Active consent documents: {total_consent_docs}")
    print(f"Total consent records: {total_consents}")
    print(f"Employees pending consent: {pending_consents}")
    
    report["sections"]["consent_status"] = consent_status
    
    # ========== FINAL SUMMARY ==========
    print()
    print("=" * 70)
    print("GOVERNANCE AUDIT SUMMARY")
    print("=" * 70)
    
    total_employees = await db.employees.count_documents({})
    active_employees = await db.employees.count_documents({"is_active": True})
    
    summary = {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "data_integrity_issues": len(dup_emp_ids) + len(dup_emails) + len(circular),
        "audit_trail_records": total_changes,
        "consent_compliance": "COMPLETE" if pending_consents == 0 else f"{pending_consents} PENDING"
    }
    
    print(f"Total employees: {total_employees}")
    print(f"Active employees: {active_employees}")
    print(f"Data integrity issues: {summary['data_integrity_issues']}")
    print(f"Audit trail records: {summary['audit_trail_records']}")
    print(f"Consent compliance: {summary['consent_compliance']}")
    
    report["summary"] = summary
    
    # Save report
    report_path = "/app/governance_audit_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print()
    print(f"Full report saved to: {report_path}")
    
    client.close()
    return report


if __name__ == "__main__":
    asyncio.run(generate_full_governance_report())
