"""
Daily Integrity Audit Scheduler
================================

Automated scheduled job that runs daily integrity audits on the ERP system.
Detects lifecycle inconsistencies, duplicate records, and data anomalies.

Features:
- Scheduled daily execution (configurable time)
- Comprehensive employee lifecycle validation
- Duplicate detection
- Anomaly reporting
- Alert notifications for administrators

Usage:
    from services.integrity_scheduler import IntegrityScheduler
    
    # Start the scheduler
    scheduler = IntegrityScheduler(db)
    await scheduler.start()
    
    # Manual trigger
    report = await scheduler.run_audit_now()
"""

import asyncio
import logging
from datetime import datetime, timezone, time as dt_time
from typing import Dict, Any, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class IntegrityScheduler:
    """
    Scheduled integrity audit service.
    Runs daily checks on employee data consistency.
    """
    
    # Default schedule: 2:00 AM daily
    DEFAULT_HOUR = 2
    DEFAULT_MINUTE = 0
    
    def __init__(self, db, hour: int = None, minute: int = None):
        """
        Initialize the scheduler.
        
        Args:
            db: MongoDB database connection
            hour: Hour to run audit (0-23)
            minute: Minute to run audit (0-59)
        """
        self.db = db
        self.hour = hour if hour is not None else self.DEFAULT_HOUR
        self.minute = minute if minute is not None else self.DEFAULT_MINUTE
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._last_report: Optional[Dict] = None
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Integrity scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Integrity scheduler started. Daily audit at {self.hour:02d}:{self.minute:02d} UTC")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Integrity scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Calculate seconds until next scheduled run
                now = datetime.now(timezone.utc)
                target = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
                
                if target <= now:
                    # Already past today's time, schedule for tomorrow
                    target = target.replace(day=target.day + 1)
                
                wait_seconds = (target - now).total_seconds()
                logger.info(f"Next integrity audit scheduled in {wait_seconds/3600:.1f} hours")
                
                await asyncio.sleep(wait_seconds)
                
                # Run the audit
                if self._running:
                    await self.run_audit_now()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retrying
    
    async def run_audit_now(self) -> Dict[str, Any]:
        """
        Run integrity audit immediately.
        
        Returns:
            Audit report dictionary
        """
        logger.info("Starting scheduled integrity audit...")
        start_time = datetime.now(timezone.utc)
        
        report = {
            "audit_id": f"audit_{start_time.strftime('%Y%m%d_%H%M%S')}",
            "timestamp": start_time.isoformat(),
            "type": "scheduled",
            "status": "completed",
            "summary": {},
            "checks": {},
            "anomalies": [],
            "critical_issues": [],
            "recommendations": []
        }
        
        try:
            # Run all checks
            employees = await self.db.employees.find({}, {"_id": 0}).to_list(10000)
            users = await self.db.users.find({}, {"_id": 0}).to_list(10000)
            
            # Summary counts
            report["summary"] = {
                "total_employees": len(employees),
                "total_users": len(users),
                "employees_with_user": sum(1 for e in employees if e.get("user_id")),
                "active_employees": sum(1 for e in employees if e.get("go_live_status") == "active"),
                "pending_go_live": sum(1 for e in employees if e.get("go_live_status") == "pending")
            }
            
            # Check 1: Lifecycle Consistency
            check1 = await self._check_lifecycle_consistency(employees)
            report["checks"]["lifecycle_consistency"] = check1
            report["anomalies"].extend(check1.get("anomalies", []))
            
            # Check 2: Duplicate Records
            check2 = await self._check_duplicates(employees)
            report["checks"]["duplicate_records"] = check2
            report["anomalies"].extend(check2.get("anomalies", []))
            
            # Check 3: Missing Employee IDs
            check3 = await self._check_missing_employee_ids(employees)
            report["checks"]["missing_employee_ids"] = check3
            report["anomalies"].extend(check3.get("anomalies", []))
            
            # Check 4: User Account Mismatches
            check4 = await self._check_user_mismatches(employees, users)
            report["checks"]["user_mismatches"] = check4
            report["anomalies"].extend(check4.get("anomalies", []))
            
            # Check 5: Incomplete Onboarding
            check5 = await self._check_incomplete_onboarding(employees)
            report["checks"]["incomplete_onboarding"] = check5
            report["anomalies"].extend(check5.get("anomalies", []))
            
            # Identify critical issues
            for anomaly in report["anomalies"]:
                if anomaly.get("severity") == "CRITICAL":
                    report["critical_issues"].append(anomaly)
            
            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(report["anomalies"])
            
            # Calculate overall health
            critical_count = len(report["critical_issues"])
            total_anomalies = len(report["anomalies"])
            
            if critical_count > 0:
                report["health_status"] = "CRITICAL"
            elif total_anomalies > 5:
                report["health_status"] = "WARNING"
            elif total_anomalies > 0:
                report["health_status"] = "MINOR_ISSUES"
            else:
                report["health_status"] = "HEALTHY"
            
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            report["duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Store report
            self._last_run = start_time
            self._last_report = report
            
            # Save to database
            await self.db.integrity_audit_reports.insert_one({
                **report,
                "_id": None  # Let MongoDB generate ID
            })
            
            # Send alerts if critical issues found
            if report["critical_issues"]:
                await self._send_admin_alerts(report)
            
            logger.info(f"Integrity audit completed. Status: {report['health_status']}, "
                       f"Anomalies: {total_anomalies}, Critical: {critical_count}")
            
        except Exception as e:
            report["status"] = "error"
            report["error"] = str(e)
            logger.error(f"Integrity audit failed: {e}")
        
        return report
    
    async def _check_lifecycle_consistency(self, employees: List[Dict]) -> Dict:
        """Check employee lifecycle state consistency."""
        result = {
            "check_name": "Lifecycle Consistency",
            "passed": True,
            "anomalies": []
        }
        
        for emp in employees:
            go_live = emp.get("go_live_status")
            emp_id = emp.get("employee_id")
            user_id = emp.get("user_id")
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            uuid = emp.get("id", "")
            
            # Rule: Active employees must have employee_id
            if go_live == "active" and not emp_id:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "ACTIVE_WITHOUT_EMPLOYEE_ID",
                    "severity": "CRITICAL",
                    "employee_uuid": uuid,
                    "employee_name": name,
                    "description": f"Active employee '{name}' has no employee_id"
                })
            
            # Rule: Active employees must have user_id
            if go_live == "active" and not user_id:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "ACTIVE_WITHOUT_USER_ID",
                    "severity": "HIGH",
                    "employee_uuid": uuid,
                    "employee_name": name,
                    "description": f"Active employee '{name}' has no portal access"
                })
        
        return result
    
    async def _check_duplicates(self, employees: List[Dict]) -> Dict:
        """Check for duplicate employee records."""
        result = {
            "check_name": "Duplicate Records",
            "passed": True,
            "anomalies": []
        }
        
        # Check duplicate emails
        emails = [e.get("email") for e in employees if e.get("email")]
        email_counts = Counter(emails)
        for email, count in email_counts.items():
            if count > 1:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "DUPLICATE_EMAIL",
                    "severity": "HIGH",
                    "value": email,
                    "count": count,
                    "description": f"Email '{email}' appears {count} times"
                })
        
        # Check duplicate employee_ids
        emp_ids = [e.get("employee_id") for e in employees if e.get("employee_id")]
        id_counts = Counter(emp_ids)
        for emp_id, count in id_counts.items():
            if count > 1:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "DUPLICATE_EMPLOYEE_ID",
                    "severity": "CRITICAL",
                    "value": emp_id,
                    "count": count,
                    "description": f"Employee ID '{emp_id}' appears {count} times"
                })
        
        return result
    
    async def _check_missing_employee_ids(self, employees: List[Dict]) -> Dict:
        """Check for employees that should have IDs but don't."""
        result = {
            "check_name": "Missing Employee IDs",
            "passed": True,
            "anomalies": []
        }
        
        for emp in employees:
            # If employee is active or has user_id, they should have employee_id
            go_live = emp.get("go_live_status")
            user_id = emp.get("user_id")
            emp_id = emp.get("employee_id")
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            if (go_live == "active" or user_id) and not emp_id:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "MISSING_EMPLOYEE_ID",
                    "severity": "HIGH",
                    "employee_uuid": emp.get("id"),
                    "employee_name": name,
                    "has_user_id": bool(user_id),
                    "go_live_status": go_live,
                    "description": f"Employee '{name}' is missing employee_id"
                })
        
        return result
    
    async def _check_user_mismatches(self, employees: List[Dict], users: List[Dict]) -> Dict:
        """Check for mismatches between employee and user records."""
        result = {
            "check_name": "User Account Mismatches",
            "passed": True,
            "anomalies": []
        }
        
        # Build user lookup
        user_by_id = {u.get("id"): u for u in users}
        user_by_emp_id = {u.get("employee_id"): u for u in users if u.get("employee_id")}
        
        for emp in employees:
            user_id = emp.get("user_id")
            emp_id = emp.get("employee_id")
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            # If employee has user_id, verify user exists
            if user_id and user_id not in user_by_id:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "ORPHAN_USER_ID",
                    "severity": "HIGH",
                    "employee_uuid": emp.get("id"),
                    "employee_name": name,
                    "user_id": user_id,
                    "description": f"Employee '{name}' references non-existent user {user_id}"
                })
            
            # If employee has employee_id, check for matching user
            if emp_id and user_id:
                user = user_by_id.get(user_id)
                if user and user.get("employee_id") != emp_id:
                    result["passed"] = False
                    result["anomalies"].append({
                        "type": "EMPLOYEE_ID_MISMATCH",
                        "severity": "MEDIUM",
                        "employee_uuid": emp.get("id"),
                        "employee_name": name,
                        "employee_id": emp_id,
                        "user_employee_id": user.get("employee_id"),
                        "description": f"Employee ID mismatch for '{name}'"
                    })
        
        return result
    
    async def _check_incomplete_onboarding(self, employees: List[Dict]) -> Dict:
        """Check for incomplete onboarding states."""
        result = {
            "check_name": "Incomplete Onboarding",
            "passed": True,
            "anomalies": []
        }
        
        for emp in employees:
            go_live = emp.get("go_live_status")
            onboarding = emp.get("onboarding_status")
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            # Active but onboarding not completed
            if go_live == "active" and onboarding not in ["completed", None]:
                result["passed"] = False
                result["anomalies"].append({
                    "type": "INCOMPLETE_ONBOARDING",
                    "severity": "MEDIUM",
                    "employee_uuid": emp.get("id"),
                    "employee_name": name,
                    "onboarding_status": onboarding,
                    "go_live_status": go_live,
                    "description": f"Active employee '{name}' has incomplete onboarding"
                })
        
        return result
    
    def _generate_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on anomalies."""
        recommendations = []
        
        anomaly_types = set(a.get("type") for a in anomalies)
        
        if "ACTIVE_WITHOUT_EMPLOYEE_ID" in anomaly_types:
            recommendations.append(
                "CRITICAL: Assign employee IDs to all active employees. "
                "Run the employee ID generation utility or manually assign IDs."
            )
        
        if "ACTIVE_WITHOUT_USER_ID" in anomaly_types:
            recommendations.append(
                "HIGH: Generate portal access for active employees without user accounts. "
                "Use Go-Live Dashboard → Portal Access Management → Generate Portal Access."
            )
        
        if "DUPLICATE_EMPLOYEE_ID" in anomaly_types:
            recommendations.append(
                "CRITICAL: Resolve duplicate employee IDs immediately. "
                "This causes data integrity issues across payroll, attendance, and reporting."
            )
        
        if "DUPLICATE_EMAIL" in anomaly_types:
            recommendations.append(
                "HIGH: Investigate duplicate email addresses. "
                "May indicate duplicate employee records requiring merge or deletion."
            )
        
        if "ORPHAN_USER_ID" in anomaly_types:
            recommendations.append(
                "HIGH: Fix orphan user references. "
                "Either recreate missing user records or clear invalid user_id links."
            )
        
        if not anomalies:
            recommendations.append("System is healthy. No action required.")
        
        return recommendations
    
    async def _send_admin_alerts(self, report: Dict):
        """Send alerts to administrators for critical issues."""
        try:
            # Get admin users
            admins = await self.db.users.find(
                {"role": "admin", "is_active": True},
                {"_id": 0, "id": 1, "email": 1}
            ).to_list(100)
            
            # Create notifications
            now = datetime.now(timezone.utc).isoformat()
            critical_count = len(report.get("critical_issues", []))
            
            for admin in admins:
                await self.db.notifications.insert_one({
                    "id": f"alert_{now}_{admin['id']}",
                    "user_id": admin["id"],
                    "type": "integrity_alert",
                    "title": f"⚠️ Data Integrity Alert: {critical_count} Critical Issues",
                    "message": f"Daily integrity audit found {critical_count} critical issues requiring attention. "
                              f"Review the audit report for details.",
                    "reference_type": "integrity_audit",
                    "reference_id": report.get("audit_id"),
                    "is_read": False,
                    "priority": "high",
                    "created_at": now
                })
            
            logger.info(f"Sent integrity alerts to {len(admins)} administrators")
            
        except Exception as e:
            logger.error(f"Failed to send admin alerts: {e}")
    
    def get_last_report(self) -> Optional[Dict]:
        """Get the last audit report."""
        return self._last_report
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            "running": self._running,
            "schedule": f"{self.hour:02d}:{self.minute:02d} UTC daily",
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_health_status": self._last_report.get("health_status") if self._last_report else None
        }


# Singleton instance
_scheduler_instance: Optional[IntegrityScheduler] = None


def get_integrity_scheduler(db=None) -> IntegrityScheduler:
    """Get or create the integrity scheduler singleton."""
    global _scheduler_instance
    if _scheduler_instance is None and db is not None:
        _scheduler_instance = IntegrityScheduler(db)
    return _scheduler_instance
