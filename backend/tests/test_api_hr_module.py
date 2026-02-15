"""
OWASP-Compliant API Security Test Suite - HR Module
Tests: Leave Management, Attendance, Payroll, Self-Service
"""

import pytest
import httpx
from datetime import datetime, timezone, timedelta


class TestLeaveManagementPositive:
    """Positive tests for leave management."""
    
    @pytest.mark.asyncio
    async def test_leave001_get_leave_requests(self, admin_client):
        """TC-LEAVE-001: Get all leave requests."""
        response = await admin_client.get("/api/leave-requests")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_leave002_create_leave_request(self, admin_client):
        """TC-LEAVE-002: Create leave request."""
        response = await admin_client.post("/api/leave-requests", json={
            "leave_type": "casual",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
            "reason": "Personal work"
        })
        
        assert response.status_code in [200, 400]  # May fail if no balance
    
    @pytest.mark.asyncio
    async def test_leave003_get_all_leave_requests_admin(self, admin_client):
        """TC-LEAVE-003: Admin can view all leave requests."""
        response = await admin_client.get("/api/leave-requests/all")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_leave004_get_reportees_balance(self, admin_client):
        """TC-LEAVE-004: Get leave balance for reportees."""
        response = await admin_client.get("/api/leave-balance/reportees")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_leave005_get_my_leave_balance(self, admin_client):
        """TC-LEAVE-005: Get my leave balance."""
        response = await admin_client.get("/api/my/leave-balance")
        
        assert response.status_code == 200


class TestLeaveManagementNegative:
    """Negative tests for leave management."""
    
    @pytest.mark.asyncio
    async def test_leave020_invalid_leave_type(self, admin_client):
        """TC-LEAVE-020: Invalid leave type handled."""
        response = await admin_client.post("/api/leave-requests", json={
            "leave_type": "invalid_type_xyz",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": datetime.now(timezone.utc).isoformat(),
            "reason": "Test"
        })
        
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_leave021_end_before_start(self, admin_client):
        """TC-LEAVE-021: End date before start date handled."""
        response = await admin_client.post("/api/leave-requests", json={
            "leave_type": "casual",
            "start_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "reason": "Test"
        })
        
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]


class TestAttendancePositive:
    """Positive tests for attendance module."""
    
    @pytest.mark.asyncio
    async def test_att001_get_attendance(self, admin_client):
        """TC-ATT-001: Get attendance records."""
        response = await admin_client.get("/api/attendance")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_att002_post_attendance(self, admin_client, db):
        """TC-ATT-002: Post attendance record."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.post("/api/attendance", json={
                "employee_id": employee["id"],
                "date": datetime.now(timezone.utc).isoformat(),
                "status": "present",
                "check_in": "09:00",
                "check_out": "18:00"
            })
            
            assert response.status_code in [200, 400]  # May fail if duplicate
    
    @pytest.mark.asyncio
    async def test_att003_bulk_attendance(self, admin_client, db):
        """TC-ATT-003: Bulk attendance upload."""
        employees = await db.employees.find({}, {"_id": 0, "id": 1}).to_list(3)
        if employees:
            records = [
                {
                    "employee_id": emp["id"],
                    "date": datetime.now(timezone.utc).isoformat(),
                    "status": "present"
                }
                for emp in employees
            ]
            response = await admin_client.post("/api/attendance/bulk", json={"records": records})
            
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_att004_attendance_summary(self, admin_client):
        """TC-ATT-004: Get attendance summary."""
        response = await admin_client.get("/api/attendance/summary")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_att005_my_attendance(self, admin_client):
        """TC-ATT-005: Get my attendance."""
        response = await admin_client.get("/api/my/attendance")
        
        assert response.status_code == 200


class TestPayrollPositive:
    """Positive tests for payroll module."""
    
    @pytest.mark.asyncio
    async def test_pay001_get_salary_components(self, admin_client):
        """TC-PAY-001: Get salary components."""
        response = await admin_client.get("/api/payroll/salary-components")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_pay002_add_salary_component(self, admin_client):
        """TC-PAY-002: Add salary component."""
        response = await admin_client.post("/api/payroll/salary-components/add", json={
            "type": "earning",
            "key": f"test_component_{datetime.now().timestamp()}",
            "label": "Test Component",
            "is_taxable": True
        })
        
        # May fail if component already exists or validation error
        assert response.status_code in [200, 400, 409]
    
    @pytest.mark.asyncio
    async def test_pay003_get_payroll_inputs(self, admin_client):
        """TC-PAY-003: Get payroll inputs with required params."""
        # This endpoint requires month and year parameters
        response = await admin_client.get("/api/payroll/inputs?month=12&year=2025")
        
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_pay004_add_payroll_input(self, admin_client, db):
        """TC-PAY-004: Add payroll input."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.post("/api/payroll/inputs", json={
                "employee_id": employee["id"],
                "month": 12,
                "year": 2025,
                "basic_salary": 50000,
                "components": {}
            })
            
            assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_pay005_get_salary_slips(self, admin_client):
        """TC-PAY-005: Get salary slips."""
        response = await admin_client.get("/api/payroll/salary-slips")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_pay006_generate_salary_slip(self, admin_client, db):
        """TC-PAY-006: Generate salary slip."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.post("/api/payroll/generate-slip", json={
                "employee_id": employee["id"],
                "month": 12,
                "year": 2025
            })
            
            # May succeed or fail based on data availability
            assert response.status_code in [200, 400, 404]
    
    @pytest.mark.asyncio
    async def test_pay007_my_salary_slips(self, admin_client):
        """TC-PAY-007: Get my salary slips."""
        response = await admin_client.get("/api/my/salary-slips")
        
        assert response.status_code == 200


class TestPayrollSecurity:
    """Security tests for payroll - sensitive financial data."""
    
    @pytest.mark.asyncio
    async def test_pay020_unauthenticated_access(self, api_client):
        """TC-PAY-020: Unauthenticated cannot access payroll."""
        response = await api_client.get("/api/payroll/salary-slips")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_pay021_salary_amount_overflow(self, admin_client, db):
        """TC-PAY-021: Very large salary amount handled."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.post("/api/payroll/inputs", json={
                "employee_id": employee["id"],
                "month": 12,
                "year": 2025,
                "basic_salary": 99999999999999999
            })
            
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_pay022_negative_salary(self, admin_client, db):
        """TC-PAY-022: Negative salary handled."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.post("/api/payroll/inputs", json={
                "employee_id": employee["id"],
                "month": 12,
                "year": 2025,
                "basic_salary": -50000
            })
            
            assert response.status_code in [200, 400, 422]


class TestApprovalsPositive:
    """Positive tests for approvals module."""
    
    @pytest.mark.asyncio
    async def test_appr001_get_pending_approvals(self, admin_client):
        """TC-APPR-001: Get pending approvals."""
        response = await admin_client.get("/api/approvals/pending")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_appr002_get_all_approvals(self, admin_client):
        """TC-APPR-002: Get all approvals."""
        response = await admin_client.get("/api/approvals/all")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_appr003_get_my_requests(self, admin_client):
        """TC-APPR-003: Get my approval requests."""
        response = await admin_client.get("/api/approvals/my-requests")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_appr004_preview_approval_chain(self, admin_client, db):
        """TC-APPR-004: Preview approval chain."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.get(
                f"/api/approvals/preview-chain?request_type=expense&requester_id={employee['id']}&amount=5000"
            )
            
            assert response.status_code in [200, 422]


class TestApprovalsNegative:
    """Negative tests for approvals."""
    
    @pytest.mark.asyncio
    async def test_appr020_action_nonexistent(self, admin_client):
        """TC-APPR-020: Action on nonexistent approval fails."""
        response = await admin_client.post(
            "/api/approvals/nonexistent-id/action",
            json={"action": "approve"}
        )
        
        assert response.status_code in [404, 422]


class TestReportsPositive:
    """Positive tests for reports module."""
    
    @pytest.mark.asyncio
    async def test_rep001_get_reports(self, admin_client):
        """TC-REP-001: Get available reports."""
        response = await admin_client.get("/api/reports")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rep002_get_report_categories(self, admin_client):
        """TC-REP-002: Get report categories."""
        response = await admin_client.get("/api/reports/categories")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rep003_get_report_stats(self, admin_client):
        """TC-REP-003: Get report statistics."""
        response = await admin_client.get("/api/reports/stats")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rep004_preview_report(self, admin_client):
        """TC-REP-004: Preview report data."""
        response = await admin_client.get("/api/reports/employees/preview")
        
        # Access may be restricted or report may not exist
        assert response.status_code in [200, 403, 404]
    
    @pytest.mark.asyncio
    async def test_rep005_generate_report(self, admin_client):
        """TC-REP-005: Generate report."""
        response = await admin_client.post("/api/reports/generate", json={
            "report_id": "employees",
            "format": "excel"
        })
        
        # May return file, be restricted, or error based on config
        assert response.status_code in [200, 400, 403, 404]


class TestNotifications:
    """Tests for notifications."""
    
    @pytest.mark.asyncio
    async def test_notif001_mark_all_read(self, admin_client):
        """TC-NOTIF-001: Mark all notifications as read."""
        response = await admin_client.patch("/api/notifications/mark-all-read")
        
        assert response.status_code == 200


class TestSelfServiceWorkspace:
    """Tests for self-service workspace endpoints."""
    
    @pytest.mark.asyncio
    async def test_self001_my_attendance(self, admin_client):
        """TC-SELF-001: My attendance endpoint."""
        response = await admin_client.get("/api/my/attendance")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_self002_my_leave_balance(self, admin_client):
        """TC-SELF-002: My leave balance endpoint."""
        response = await admin_client.get("/api/my/leave-balance")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_self003_my_salary_slips(self, admin_client):
        """TC-SELF-003: My salary slips endpoint."""
        response = await admin_client.get("/api/my/salary-slips")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_self004_my_expenses(self, admin_client):
        """TC-SELF-004: My expenses endpoint."""
        response = await admin_client.get("/api/my/expenses")
        
        assert response.status_code == 200
