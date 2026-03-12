"""
ERP Integrity Monitor Service
Automatic periodic audit for employee lifecycle consistency

Usage:
    from services.integrity_monitor import IntegrityMonitor
    
    # Run audit
    report = await IntegrityMonitor.run_audit()
    
    # Schedule periodic checks
    IntegrityMonitor.schedule_daily_audit()
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class IntegrityMonitor:
    """
    Monitors ERP data integrity and lifecycle consistency.
    """
    
    LIFECYCLE_RULES = {
        "active_requires_employee_id": True,
        "active_requires_user_id": True,
        "employee_id_must_be_unique": True,
        "onboarding_before_go_live": True
    }
    
    @classmethod
    async def run_audit(cls, db) -> Dict[str, Any]:
        """
        Run comprehensive integrity audit on employee data.
        
        Returns:
            Dictionary containing audit results and anomalies
        """
        audit_start = datetime.now(timezone.utc)
        report = {
            "audit_timestamp": audit_start.isoformat(),
            "status": "completed",
            "summary": {},
            "anomalies": [],
            "recommendations": []
        }
        
        try:
            # Get all employees
            employees = await db.employees.find({}, {"_id": 0}).to_list(10000)
            
            # Basic counts
            total = len(employees)
            with_user_id = sum(1 for e in employees if e.get('user_id'))
            with_employee_id = sum(1 for e in employees if e.get('employee_id'))
            active_count = sum(1 for e in employees if e.get('go_live_status') == 'active')
            
            report["summary"] = {
                "total_employees": total,
                "with_portal_access": with_user_id,
                "with_employee_id": with_employee_id,
                "active_employees": active_count,
                "pending_onboarding": sum(1 for e in employees if e.get('go_live_status') in ['pending', 'not_submitted', None])
            }
            
            # Check for anomalies
            anomalies = []
            
            # Rule 1: Active employees must have employee_id
            active_no_empid = [e for e in employees if e.get('go_live_status') == 'active' and not e.get('employee_id')]
            if active_no_empid:
                anomalies.append({
                    "type": "ACTIVE_WITHOUT_EMPLOYEE_ID",
                    "severity": "CRITICAL",
                    "count": len(active_no_empid),
                    "affected_records": [
                        {"id": e.get("id"), "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()}
                        for e in active_no_empid[:10]
                    ]
                })
            
            # Rule 2: Active employees must have user_id
            active_no_userid = [e for e in employees if e.get('go_live_status') == 'active' and not e.get('user_id')]
            if active_no_userid:
                anomalies.append({
                    "type": "ACTIVE_WITHOUT_USER_ID",
                    "severity": "CRITICAL",
                    "count": len(active_no_userid),
                    "affected_records": [
                        {"id": e.get("id"), "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()}
                        for e in active_no_userid[:10]
                    ]
                })
            
            # Rule 3: user_id without employee_id
            userid_no_empid = [e for e in employees if e.get('user_id') and not e.get('employee_id')]
            if userid_no_empid:
                anomalies.append({
                    "type": "USER_WITHOUT_EMPLOYEE_ID",
                    "severity": "HIGH",
                    "count": len(userid_no_empid),
                    "affected_records": [
                        {"id": e.get("id"), "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()}
                        for e in userid_no_empid[:10]
                    ]
                })
            
            # Rule 4: Check for duplicate employee_ids
            employee_ids = [e.get('employee_id') for e in employees if e.get('employee_id')]
            duplicates = set([x for x in employee_ids if employee_ids.count(x) > 1])
            if duplicates:
                anomalies.append({
                    "type": "DUPLICATE_EMPLOYEE_ID",
                    "severity": "CRITICAL",
                    "count": len(duplicates),
                    "affected_records": list(duplicates)[:10]
                })
            
            # Rule 5: Check for duplicate emails
            emails = [e.get('email') for e in employees if e.get('email')]
            dup_emails = set([x for x in emails if emails.count(x) > 1])
            if dup_emails:
                anomalies.append({
                    "type": "DUPLICATE_EMAIL",
                    "severity": "HIGH",
                    "count": len(dup_emails),
                    "affected_records": list(dup_emails)[:10]
                })
            
            report["anomalies"] = anomalies
            
            # Generate recommendations
            if anomalies:
                report["recommendations"] = cls._generate_recommendations(anomalies)
            
            # Risk level
            critical_count = sum(1 for a in anomalies if a["severity"] == "CRITICAL")
            high_count = sum(1 for a in anomalies if a["severity"] == "HIGH")
            
            if critical_count > 0:
                report["risk_level"] = "CRITICAL"
            elif high_count > 0:
                report["risk_level"] = "HIGH"
            elif anomalies:
                report["risk_level"] = "MEDIUM"
            else:
                report["risk_level"] = "LOW"
            
            logger.info(f"Integrity audit completed: {len(anomalies)} anomalies found, risk level: {report['risk_level']}")
            
        except Exception as e:
            report["status"] = "error"
            report["error"] = str(e)
            logger.error(f"Integrity audit failed: {e}")
        
        return report
    
    @classmethod
    def _generate_recommendations(cls, anomalies: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on anomalies."""
        recommendations = []
        
        for anomaly in anomalies:
            atype = anomaly["type"]
            
            if atype == "ACTIVE_WITHOUT_EMPLOYEE_ID":
                recommendations.append(
                    "CRITICAL: Generate employee IDs for active employees missing this field. "
                    "Use the employee ID generation utility or manually assign IDs."
                )
            elif atype == "ACTIVE_WITHOUT_USER_ID":
                recommendations.append(
                    "CRITICAL: Generate portal access for active employees without user accounts. "
                    "Use the 'Generate Portal Access' feature in Go-Live Dashboard."
                )
            elif atype == "USER_WITHOUT_EMPLOYEE_ID":
                recommendations.append(
                    "HIGH: Review employees with portal access but no employee ID. "
                    "This may indicate incomplete onboarding."
                )
            elif atype == "DUPLICATE_EMPLOYEE_ID":
                recommendations.append(
                    "CRITICAL: Resolve duplicate employee IDs immediately. "
                    "This causes data integrity issues across the system."
                )
            elif atype == "DUPLICATE_EMAIL":
                recommendations.append(
                    "HIGH: Investigate duplicate email addresses. "
                    "May indicate duplicate employee records or data entry errors."
                )
        
        return recommendations
    
    @classmethod
    async def repair_records(cls, db, repair_type: str = "all") -> Dict[str, Any]:
        """
        Attempt to repair inconsistent records.
        
        Args:
            db: Database connection
            repair_type: Type of repair ('all', 'missing_employee_id', 'missing_user_id')
            
        Returns:
            Dictionary with repair results
        """
        results = {
            "repairs_attempted": 0,
            "repairs_successful": 0,
            "repairs_failed": 0,
            "details": []
        }
        
        # Note: Actual repairs should be done carefully with human oversight
        # This method provides guidance rather than automatic fixes
        
        employees = await db.employees.find({}, {"_id": 0}).to_list(10000)
        
        for emp in employees:
            go_live = emp.get('go_live_status')
            
            # Log records that need attention
            if go_live == 'active':
                if not emp.get('employee_id'):
                    results["details"].append({
                        "id": emp.get("id"),
                        "issue": "MISSING_EMPLOYEE_ID",
                        "action": "REQUIRES_MANUAL_ASSIGNMENT",
                        "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    })
                
                if not emp.get('user_id'):
                    results["details"].append({
                        "id": emp.get("id"),
                        "issue": "MISSING_USER_ID",
                        "action": "USE_GENERATE_PORTAL_ACCESS",
                        "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
                    })
        
        results["repairs_attempted"] = len(results["details"])
        
        return results
    
    @classmethod
    async def validate_lifecycle_transition(
        cls, 
        db, 
        employee_id: str, 
        new_status: str
    ) -> Dict[str, Any]:
        """
        Validate if a lifecycle transition is allowed.
        
        Args:
            db: Database connection
            employee_id: Employee UUID
            new_status: Target go_live_status
            
        Returns:
            Dictionary with validation result and any blocking issues
        """
        result = {
            "valid": True,
            "blocking_issues": [],
            "warnings": []
        }
        
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        
        if not employee:
            result["valid"] = False
            result["blocking_issues"].append("Employee not found")
            return result
        
        current_status = employee.get('go_live_status', 'not_submitted')
        
        # Validate transition to 'active'
        if new_status == 'active':
            # Must have employee_id
            if not employee.get('employee_id'):
                result["valid"] = False
                result["blocking_issues"].append("Employee ID must be assigned before activation")
            
            # Should have user_id (warning if not)
            if not employee.get('user_id'):
                result["warnings"].append("User account will be created during activation")
            
            # Check if Go-Live request exists and is approved
            go_live_request = await db.go_live_requests.find_one({
                "employee_id": employee_id,
                "status": "approved"
            })
            if not go_live_request:
                result["valid"] = False
                result["blocking_issues"].append("Go-Live request must be approved before activation")
        
        return result


# Cache invalidation helper
class CacheInvalidationHelper:
    """
    Helper to ensure cache is invalidated on lifecycle changes.
    """
    
    CACHE_PATTERNS_TO_INVALIDATE = [
        "list:employees",
        "stats:employees",
        "stats:dashboard",
        "list:go-live"
    ]
    
    @classmethod
    def invalidate_employee_caches(cls, cache):
        """Invalidate all employee-related caches."""
        for pattern in cls.CACHE_PATTERNS_TO_INVALIDATE:
            cache.invalidate_pattern(pattern)
    
    @classmethod
    def invalidate_on_lifecycle_change(cls, cache, employee_id: str):
        """Invalidate caches when an employee's lifecycle state changes."""
        cls.invalidate_employee_caches(cache)
        # Also invalidate any employee-specific caches
        cache.invalidate(f"employee:{employee_id}")
        cache.invalidate(f"checklist:{employee_id}")
