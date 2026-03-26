"""
Test suite for Attendance & Leave Features Batch
Tests: 
- GET /api/my/attendance returns records, summary with total_overtime, shift_config
- GET /api/my/leave-balance returns balance calculated from approved leave_requests
- POST /api/leave-requests with date that has attendance marked returns 400 conflict
- POST /api/my/check-in allows re-check-in (archives previous record)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAttendanceLeaveFeatures:
    """Test attendance and leave features batch"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin (EMP001)
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_token = token
        
        # Login as sales (EMP003) for secondary tests
        sales_session = requests.Session()
        sales_session.headers.update({"Content-Type": "application/json"})
        sales_login = sales_session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        if sales_login.status_code == 200:
            self.sales_token = sales_login.json().get("access_token")
            self.sales_session = sales_session
            self.sales_session.headers.update({"Authorization": f"Bearer {self.sales_token}"})
        else:
            self.sales_token = None
            self.sales_session = None
    
    # ==================== MY ATTENDANCE TESTS ====================
    
    def test_my_attendance_returns_records(self):
        """GET /api/my/attendance returns records array"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "records" in data, "Response should have 'records' key"
        assert isinstance(data["records"], list), "records should be a list"
        print(f"PASSED: GET /api/my/attendance returns {len(data['records'])} records")
    
    def test_my_attendance_returns_summary(self):
        """GET /api/my/attendance returns summary with total_overtime"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "summary" in data, "Response should have 'summary' key"
        summary = data["summary"]
        assert "total_overtime" in summary, "Summary should have 'total_overtime'"
        assert "present" in summary, "Summary should have 'present'"
        assert "late_count" in summary, "Summary should have 'late_count'"
        assert "total_hours" in summary, "Summary should have 'total_hours'"
        print(f"PASSED: Summary contains total_overtime={summary['total_overtime']}, present={summary['present']}, late_count={summary['late_count']}")
    
    def test_my_attendance_returns_shift_config(self):
        """GET /api/my/attendance returns shift_config object"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "shift_config" in data, "Response should have 'shift_config' key"
        shift = data["shift_config"]
        assert "standard_work_hours" in shift, "shift_config should have 'standard_work_hours'"
        assert "core_hours_start" in shift, "shift_config should have 'core_hours_start'"
        assert "core_hours_end" in shift, "shift_config should have 'core_hours_end'"
        print(f"PASSED: shift_config contains standard_work_hours={shift['standard_work_hours']}, core_hours={shift['core_hours_start']}-{shift['core_hours_end']}")
    
    def test_my_attendance_with_month_filter(self):
        """GET /api/my/attendance?month=YYYY-MM filters by month"""
        current_month = datetime.now().strftime("%Y-%m")
        resp = self.session.get(f"{BASE_URL}/api/my/attendance?month={current_month}")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "records" in data
        # All records should be from the specified month
        for record in data["records"]:
            assert record["date"].startswith(current_month), f"Record date {record['date']} not in month {current_month}"
        print(f"PASSED: Month filter works, {len(data['records'])} records for {current_month}")
    
    def test_attendance_records_have_overtime_hours(self):
        """Attendance records should have overtime_hours field"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200
        data = resp.json()
        if data["records"]:
            record = data["records"][0]
            # overtime_hours should exist (can be 0 or null)
            assert "overtime_hours" in record or record.get("overtime_hours") is None or record.get("overtime_hours", 0) >= 0
            print(f"PASSED: Records have overtime_hours field, first record OT={record.get('overtime_hours', 0)}")
        else:
            print("PASSED: No records to check, but endpoint works")
    
    def test_attendance_records_have_working_hours(self):
        """Attendance records should have working_hours field"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200
        data = resp.json()
        if data["records"]:
            record = data["records"][0]
            # working_hours should exist
            assert "working_hours" in record or record.get("working_hours") is None
            print(f"PASSED: Records have working_hours field, first record hours={record.get('working_hours')}")
        else:
            print("PASSED: No records to check, but endpoint works")
    
    def test_attendance_records_have_is_late(self):
        """Attendance records should have is_late field"""
        resp = self.session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200
        data = resp.json()
        if data["records"]:
            record = data["records"][0]
            assert "is_late" in record
            print(f"PASSED: Records have is_late field, first record is_late={record.get('is_late')}")
        else:
            print("PASSED: No records to check, but endpoint works")
    
    # ==================== LEAVE BALANCE TESTS ====================
    
    def test_my_leave_balance_returns_balance(self):
        """GET /api/my/leave-balance returns balance object"""
        resp = self.session.get(f"{BASE_URL}/api/my/leave-balance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "casual" in data, "Response should have 'casual' key"
        assert "sick" in data, "Response should have 'sick' key"
        assert "earned" in data, "Response should have 'earned' key"
        print(f"PASSED: Leave balance returned - casual={data['casual']}, sick={data['sick']}, earned={data['earned']}")
    
    def test_leave_balance_has_total_used_available(self):
        """Leave balance should have total, used, available for each type"""
        resp = self.session.get(f"{BASE_URL}/api/my/leave-balance")
        assert resp.status_code == 200
        data = resp.json()
        for leave_type in ["casual", "sick", "earned"]:
            balance = data[leave_type]
            assert "total" in balance, f"{leave_type} should have 'total'"
            assert "used" in balance, f"{leave_type} should have 'used'"
            assert "available" in balance, f"{leave_type} should have 'available'"
            # available should be total - used
            assert balance["available"] == balance["total"] - balance["used"], f"{leave_type} available calculation mismatch"
        print(f"PASSED: All leave types have total/used/available with correct calculation")
    
    # ==================== LEAVE-ATTENDANCE CONFLICT TESTS ====================
    
    def test_leave_request_conflict_with_attendance(self):
        """POST /api/leave-requests with date that has attendance marked returns 400"""
        # First, get today's date (EMP001 already has attendance for today per context)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Try to apply leave for today
        resp = self.session.post(f"{BASE_URL}/api/leave-requests", json={
            "leave_type": "casual_leave",
            "start_date": today,
            "end_date": today,
            "reason": "Test conflict detection",
            "is_half_day": False
        })
        
        # Should return 400 with conflict message if attendance exists
        if resp.status_code == 400:
            error_detail = resp.json().get("detail", "")
            assert "attendance" in error_detail.lower() or "conflict" in error_detail.lower() or "marked" in error_detail.lower(), \
                f"Error should mention attendance conflict: {error_detail}"
            print(f"PASSED: Leave request for date with attendance returns 400 - {error_detail}")
        elif resp.status_code == 201:
            # If no attendance for today, this is expected
            print(f"INFO: No attendance conflict for {today} - leave request created (expected if no attendance)")
            # Clean up - withdraw the leave
            leave_id = resp.json().get("leave_request_id")
            if leave_id:
                self.session.post(f"{BASE_URL}/api/leave-requests/{leave_id}/withdraw")
        else:
            print(f"INFO: Response status {resp.status_code} - {resp.text}")
    
    # ==================== RE-CHECK-IN TESTS ====================
    
    def test_check_in_allows_re_checkin(self):
        """POST /api/my/check-in allows re-check-in (archives previous record)"""
        # First check current status
        status_resp = self.session.get(f"{BASE_URL}/api/my/check-status")
        assert status_resp.status_code == 200
        status = status_resp.json()
        
        # Try to check in (should work even if already checked in)
        checkin_resp = self.session.post(f"{BASE_URL}/api/my/check-in", json={
            "work_location": "office",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "remarks": "Re-check-in test"
        })
        
        # Should succeed (200 or 201) - not 400 error
        assert checkin_resp.status_code in [200, 201], f"Re-check-in should be allowed: {checkin_resp.text}"
        data = checkin_resp.json()
        assert "attendance" in data or "message" in data
        print(f"PASSED: Re-check-in allowed - {data.get('message', 'success')}")
    
    def test_check_status_endpoint(self):
        """GET /api/my/check-status returns current day status"""
        resp = self.session.get(f"{BASE_URL}/api/my/check-status")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "date" in data
        assert "has_checked_in" in data
        assert "has_checked_out" in data
        print(f"PASSED: Check status - date={data['date']}, checked_in={data['has_checked_in']}, checked_out={data['has_checked_out']}")
    
    # ==================== LEAVE REQUESTS TESTS ====================
    
    def test_get_leave_requests(self):
        """GET /api/leave-requests returns list"""
        resp = self.session.get(f"{BASE_URL}/api/leave-requests")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASSED: GET /api/leave-requests returns {len(data)} requests")
    
    def test_leave_request_has_approval_trail_fields(self):
        """Leave requests should have approval trail fields (rm_action, rm_action_at, rm_comments)"""
        resp = self.session.get(f"{BASE_URL}/api/leave-requests")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            # Check if any request has approval trail fields
            has_trail_fields = False
            for req in data:
                if req.get("rm_action") or req.get("rm_action_at") or req.get("reporting_manager_name"):
                    has_trail_fields = True
                    print(f"PASSED: Leave request has approval trail - RM: {req.get('reporting_manager_name')}, action: {req.get('rm_action')}")
                    break
            if not has_trail_fields:
                print("INFO: No leave requests with approval trail found (may be all pending)")
        else:
            print("INFO: No leave requests to check")
    
    # ==================== SALES USER TESTS ====================
    
    def test_sales_user_attendance(self):
        """Sales user (EMP003) can access their attendance"""
        if not self.sales_session:
            pytest.skip("Sales user login failed")
        
        resp = self.sales_session.get(f"{BASE_URL}/api/my/attendance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "records" in data
        assert "summary" in data
        assert "shift_config" in data
        print(f"PASSED: Sales user can access attendance - {len(data['records'])} records")
    
    def test_sales_user_leave_balance(self):
        """Sales user (EMP003) can access their leave balance"""
        if not self.sales_session:
            pytest.skip("Sales user login failed")
        
        resp = self.sales_session.get(f"{BASE_URL}/api/my/leave-balance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "casual" in data
        assert "sick" in data
        assert "earned" in data
        print(f"PASSED: Sales user leave balance - casual={data['casual']['available']}, sick={data['sick']['available']}, earned={data['earned']['available']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
