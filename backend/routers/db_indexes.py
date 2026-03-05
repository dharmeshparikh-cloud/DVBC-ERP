"""
Database Index Management for Performance Optimization
======================================================

This module ensures all critical indexes exist for optimal query performance.
Run on application startup to ensure indexes are in place.

Target Performance:
- Page load < 1.5 seconds
- API response < 200 ms
- Form submission < 300 ms
- Database queries < 100 ms
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


# Index definitions: (collection, index_spec, options)
HR_INDEXES: List[Tuple[str, list, dict]] = [
    # Employees collection - most frequently queried
    ("employees", [("employee_id", 1)], {"unique": True, "background": True}),
    ("employees", [("id", 1)], {"unique": True, "background": True}),
    ("employees", [("user_id", 1)], {"background": True}),
    ("employees", [("email", 1)], {"background": True}),
    ("employees", [("department", 1)], {"background": True}),
    ("employees", [("designation", 1)], {"background": True}),
    ("employees", [("reporting_manager_id", 1)], {"background": True}),
    ("employees", [("status", 1)], {"background": True}),
    ("employees", [("is_active", 1)], {"background": True}),
    ("employees", [("created_at", -1)], {"background": True}),
    # Compound indexes for common queries
    ("employees", [("department", 1), ("status", 1)], {"background": True}),
    ("employees", [("department", 1), ("is_active", 1)], {"background": True}),
    ("employees", [("reporting_manager_id", 1), ("is_active", 1)], {"background": True}),
    
    # Attendance collection
    ("attendance", [("employee_id", 1), ("date", -1)], {"background": True}),
    ("attendance", [("date", -1)], {"background": True}),
    ("attendance", [("status", 1)], {"background": True}),
    ("attendance", [("employee_id", 1), ("status", 1), ("date", -1)], {"background": True}),
    
    # Leaves collection
    ("leaves", [("employee_id", 1)], {"background": True}),
    ("leaves", [("status", 1)], {"background": True}),
    ("leaves", [("leave_type", 1)], {"background": True}),
    ("leaves", [("employee_id", 1), ("status", 1)], {"background": True}),
    ("leaves", [("created_at", -1)], {"background": True}),
    ("leaves", [("approver_id", 1), ("status", 1)], {"background": True}),
    
    # Onboarding submissions
    ("onboarding_submissions", [("id", 1)], {"unique": True, "background": True}),
    ("onboarding_submissions", [("token", 1)], {"unique": True, "background": True}),
    ("onboarding_submissions", [("status", 1)], {"background": True}),
    ("onboarding_submissions", [("candidate_email", 1)], {"background": True}),
    ("onboarding_submissions", [("created_at", -1)], {"background": True}),
    ("onboarding_submissions", [("status", 1), ("created_at", -1)], {"background": True}),
    
    # Go-live employees
    ("go_live_employees", [("id", 1)], {"unique": True, "background": True}),
    ("go_live_employees", [("employee_id", 1)], {"background": True}),
    ("go_live_employees", [("status", 1)], {"background": True}),
    ("go_live_employees", [("created_at", -1)], {"background": True}),
    
    # Payroll
    ("salary_slips", [("employee_id", 1), ("month", -1)], {"background": True}),
    ("salary_slips", [("month", -1)], {"background": True}),
    ("payroll_inputs", [("month", 1)], {"background": True}),
    
    # Users collection
    ("users", [("id", 1)], {"unique": True, "background": True}),
    ("users", [("employee_id", 1)], {"unique": True, "sparse": True, "background": True}),
    ("users", [("email", 1)], {"background": True}),
    ("users", [("role", 1)], {"background": True}),
]

SALES_INDEXES: List[Tuple[str, list, dict]] = [
    # Leads collection
    ("leads", [("id", 1)], {"unique": True, "background": True}),
    ("leads", [("assigned_to", 1)], {"background": True}),
    ("leads", [("status", 1)], {"background": True}),
    ("leads", [("company", 1)], {"background": True}),
    ("leads", [("created_at", -1)], {"background": True}),
    ("leads", [("assigned_to", 1), ("status", 1)], {"background": True}),
    ("leads", [("status", 1), ("created_at", -1)], {"background": True}),
    
    # Meetings
    ("meetings", [("id", 1)], {"unique": True, "background": True}),
    ("meetings", [("lead_id", 1)], {"background": True}),
    ("meetings", [("meeting_date", -1)], {"background": True}),
    ("meetings", [("lead_id", 1), ("meeting_date", -1)], {"background": True}),
    
    # Pricing plans
    ("pricing_plans", [("id", 1)], {"unique": True, "background": True}),
    ("pricing_plans", [("lead_id", 1)], {"background": True}),
    
    # SOWs
    ("sows", [("id", 1)], {"unique": True, "background": True}),
    ("sows", [("lead_id", 1)], {"background": True}),
    ("enhanced_sows", [("id", 1)], {"unique": True, "background": True}),
    ("enhanced_sows", [("lead_id", 1)], {"background": True}),
    
    # Quotations
    ("quotations", [("id", 1)], {"unique": True, "background": True}),
    ("quotations", [("lead_id", 1)], {"background": True}),
    
    # Agreements
    ("agreements", [("id", 1)], {"unique": True, "background": True}),
    ("agreements", [("lead_id", 1)], {"background": True}),
    ("agreements", [("status", 1)], {"background": True}),
    
    # Kickoff requests
    ("kickoff_requests", [("id", 1)], {"unique": True, "background": True}),
    ("kickoff_requests", [("lead_id", 1)], {"background": True}),
    ("kickoff_requests", [("status", 1)], {"background": True}),
]

CONSULTING_INDEXES: List[Tuple[str, list, dict]] = [
    # Projects
    ("projects", [("id", 1)], {"unique": True, "background": True}),
    ("projects", [("client_id", 1)], {"background": True}),
    ("projects", [("status", 1)], {"background": True}),
    ("projects", [("project_manager_id", 1)], {"background": True}),
    ("projects", [("created_at", -1)], {"background": True}),
    
    # Consultants
    ("consultants", [("id", 1)], {"unique": True, "background": True}),
    ("consultants", [("employee_id", 1)], {"background": True}),
    ("consultants", [("project_id", 1)], {"background": True}),
    
    # Tasks
    ("tasks", [("id", 1)], {"unique": True, "background": True}),
    ("tasks", [("project_id", 1)], {"background": True}),
    ("tasks", [("assigned_to", 1)], {"background": True}),
    ("tasks", [("status", 1)], {"background": True}),
]

SYSTEM_INDEXES: List[Tuple[str, list, dict]] = [
    # Notifications
    ("notifications", [("user_id", 1), ("read", 1)], {"background": True}),
    ("notifications", [("created_at", -1)], {"background": True}),
    
    # Documents
    ("document_history", [("id", 1)], {"unique": True, "background": True}),
    ("document_history", [("employee_id", 1)], {"background": True}),
    ("document_history", [("document_type", 1)], {"background": True}),
    ("document_history", [("created_at", -1)], {"background": True}),
    
    # Expenses
    ("expenses", [("id", 1)], {"unique": True, "background": True}),
    ("expenses", [("employee_id", 1)], {"background": True}),
    ("expenses", [("status", 1)], {"background": True}),
    ("expenses", [("approver_id", 1), ("status", 1)], {"background": True}),
    
    # Audit logs
    ("audit_logs", [("created_at", -1)], {"background": True}),
    ("audit_logs", [("user_id", 1)], {"background": True}),
    ("audit_logs", [("action", 1)], {"background": True}),
]

ALL_INDEXES = HR_INDEXES + SALES_INDEXES + CONSULTING_INDEXES + SYSTEM_INDEXES


async def ensure_indexes(db) -> dict:
    """
    Ensure all indexes exist in the database.
    Returns statistics about index creation.
    """
    stats = {
        "created": 0,
        "existing": 0,
        "errors": []
    }
    
    for collection_name, index_spec, options in ALL_INDEXES:
        try:
            collection = db[collection_name]
            # Check if collection exists (to avoid creating empty collections)
            collections = await db.list_collection_names()
            if collection_name not in collections:
                logger.debug(f"Skipping index for non-existent collection: {collection_name}")
                continue
            
            # Create index (will be a no-op if already exists)
            await collection.create_index(index_spec, **options)
            stats["created"] += 1
            logger.debug(f"Index ensured: {collection_name} - {index_spec}")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                stats["existing"] += 1
            else:
                error_msg = f"Failed to create index {collection_name}.{index_spec}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg)
    
    logger.info(f"Index sync complete: {stats['created']} created, {stats['existing']} existing, {len(stats['errors'])} errors")
    return stats


async def get_index_stats(db) -> dict:
    """
    Get statistics about current indexes in all collections.
    """
    stats = {}
    collections = await db.list_collection_names()
    
    for coll_name in collections:
        try:
            indexes = await db[coll_name].index_information()
            stats[coll_name] = {
                "index_count": len(indexes),
                "indexes": list(indexes.keys())
            }
        except Exception as e:
            stats[coll_name] = {"error": str(e)}
    
    return stats


async def analyze_slow_queries(db, threshold_ms: int = 100) -> list:
    """
    Analyze potentially slow queries based on collection scan indicators.
    Returns recommendations for index improvements.
    """
    recommendations = []
    
    # Collections that typically have slow queries without proper indexes
    critical_collections = [
        "employees", "leads", "attendance", "leaves", 
        "onboarding_submissions", "projects", "expenses"
    ]
    
    for coll_name in critical_collections:
        try:
            collection = db[coll_name]
            indexes = await collection.index_information()
            
            # Check for missing common indexes
            index_keys = set()
            for idx in indexes.values():
                if "key" in idx:
                    index_keys.update(k[0] for k in idx["key"])
            
            # Recommend indexes for common query patterns
            common_fields = {
                "employees": ["department", "status", "reporting_manager_id", "is_active"],
                "leads": ["assigned_to", "status", "company"],
                "attendance": ["employee_id", "date", "status"],
                "leaves": ["employee_id", "status", "approver_id"],
                "onboarding_submissions": ["status", "candidate_email"],
                "projects": ["client_id", "status", "project_manager_id"],
                "expenses": ["employee_id", "status", "approver_id"]
            }
            
            missing = []
            for field in common_fields.get(coll_name, []):
                if field not in index_keys:
                    missing.append(field)
            
            if missing:
                recommendations.append({
                    "collection": coll_name,
                    "missing_indexes": missing,
                    "recommendation": f"Add indexes on: {', '.join(missing)}"
                })
                
        except Exception as e:
            logger.error(f"Error analyzing {coll_name}: {e}")
    
    return recommendations
