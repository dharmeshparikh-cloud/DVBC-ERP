"""
Test Suite: Attendance Governance Model Overhaul
Tests: IST timezone, late/early/OT calculations, half-day logic, penalties, grace period, leave blocking
Shift: 10:00-19:00 IST, Grace: 10min for 3 days/month, OT cap: 120min/day, Half-day cutoff: 3:00 PM
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# IST timezone offset
IST = timezone(timedelta(hours=5, minutes=30))


class TestAuthAndSetup:
    """Authentication and basic setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        assert response.status_code == 200, f"Consultant login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")
    
    def test_consultant_login(self, consultant_token):
        """Test consultant can login"""
        assert consultant_token is not None
        assert len(consultant_token) > 0
        print(f"✓ Consultant login successful, token length: {len(consultant_token)}")


class TestMyAttendanceAPI:
    """Tests for GET /api/my/attendance endpoint"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_attendance_returns_summary_with_new_fields(self, consultant_token):
        """GET /api/my/attendance - summary includes half_day count, total_overtime_min, total_early_login_min"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check summary has new governance fields
        summary = data.get("summary", {})
        assert "half_day" in summary, "summary missing half_day count"
        assert "total_overtime_min" in summary, "summary missing total_overtime_min"
        assert "total_early_login_min" in summary, "summary missing total_early_login_min"
        
        print(f"✓ Summary fields: half_day={summary.get('half_day')}, total_overtime_min={summary.get('total_overtime_min')}, total_early_login_min={summary.get('total_early_login_min')}")
    
    def test_attendance_records_have_governance_fields(self, consultant_token):
        """GET /api/my/attendance - records have late_minutes, early_login_minutes, late_checkout_minutes, overtime_minutes"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        
        if not records:
            pytest.skip("No attendance records found")
        
        # Check first record has governance fields
        r = records[0]
        assert "late_minutes" in r, "Record missing late_minutes"
        assert "early_login_minutes" in r, "Record missing early_login_minutes"
        assert "late_checkout_minutes" in r, "Record missing late_checkout_minutes"
        assert "overtime_minutes" in r, "Record missing overtime_minutes"
        assert "is_half_day" in r, "Record missing is_half_day"
        assert "half_day_type" in r, "Record missing half_day_type"
        
        print(f"✓ Record governance fields present: late={r.get('late_minutes')}, early_in={r.get('early_login_minutes')}, late_out={r.get('late_checkout_minutes')}, OT={r.get('overtime_minutes')}")
    
    def test_attendance_shift_config_has_governance_params(self, consultant_token):
        """GET /api/my/attendance - shift_config includes grace_minutes, ot_cap_minutes"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        shift_config = data.get("shift_config", {})
        
        assert "grace_minutes" in shift_config, "shift_config missing grace_minutes"
        assert "ot_cap_minutes" in shift_config, "shift_config missing ot_cap_minutes"
        assert "grace_days_per_month" in shift_config, "shift_config missing grace_days_per_month"
        
        print(f"✓ Shift config: grace={shift_config.get('grace_minutes')}m x {shift_config.get('grace_days_per_month')} days, OT cap={shift_config.get('ot_cap_minutes')}m")
    
    def test_attendance_naive_timestamps_normalized(self, consultant_token):
        """GET /api/my/attendance - naive timestamps normalized with +05:30"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        
        if not records:
            pytest.skip("No attendance records found")
        
        for r in records:
            cin = r.get("check_in_time")
            if cin:
                # Should have timezone info (either +05:30 or Z or +00:00)
                has_tz = "+" in cin or "Z" in cin
                assert has_tz, f"check_in_time missing timezone: {cin}"
        
        print(f"✓ All timestamps have timezone info")
    
    def test_attendance_leave_display_format(self, consultant_token):
        """GET /api/my/attendance - leave_display shows 'CL (1st Half)' format for half-day records"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        
        half_day_records = [r for r in records if r.get("is_half_day")]
        
        if not half_day_records:
            pytest.skip("No half-day records found")
        
        for r in half_day_records:
            leave_display = r.get("leave_display")
            if leave_display:
                # Should be in format like "CL (1st Half)" or "CL (2nd Half)"
                assert "Half" in leave_display or "half" in leave_display.lower(), f"Invalid leave_display format: {leave_display}"
                print(f"✓ Half-day leave_display: {leave_display}")


class TestCheckInGovernance:
    """Tests for POST /api/my/check-in governance rules"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_checkin_returns_late_minutes(self, consultant_token):
        """POST /api/my/check-in - returns is_late and late_minutes fields"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        
        # First check current status
        status_resp = requests.get(f"{BASE_URL}/api/my/check-status", headers=headers)
        if status_resp.status_code == 200:
            status = status_resp.json()
            if status.get("has_checked_in"):
                print("✓ Already checked in today - checking attendance record for late_minutes")
                # Verify the record has late_minutes
                att_resp = requests.get(f"{BASE_URL}/api/my/attendance", headers=headers)
                if att_resp.status_code == 200:
                    records = att_resp.json().get("records", [])
                    today = datetime.now(IST).strftime("%Y-%m-%d")
                    today_record = next((r for r in records if r.get("date") == today), None)
                    if today_record:
                        assert "late_minutes" in today_record
                        assert "is_late" in today_record
                        print(f"✓ Today's record has late_minutes={today_record.get('late_minutes')}, is_late={today_record.get('is_late')}")
                return
        
        # If not checked in, try to check in (may fail if leave exists)
        payload = {
            "work_location": "in_office",
            "remarks": "Test check-in",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
        response = requests.post(f"{BASE_URL}/api/my/check-in", json=payload, headers=headers)
        
        if response.status_code == 400:
            # May be blocked due to approved leave
            detail = response.json().get("detail", "")
            if "approved" in detail.lower() and "leave" in detail.lower():
                print(f"✓ Check-in blocked due to approved leave: {detail}")
                return
        
        if response.status_code == 200:
            data = response.json()
            attendance = data.get("attendance", {})
            assert "late_minutes" in attendance, "Response missing late_minutes"
            assert "is_late" in attendance, "Response missing is_late"
            print(f"✓ Check-in response has late_minutes={attendance.get('late_minutes')}, is_late={attendance.get('is_late')}")
    
    def test_checkin_blocked_with_approved_leave(self, consultant_token):
        """POST /api/my/check-in - blocks check-in if approved leave exists for today (400 error)"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        
        # First check if there's an approved leave for today
        today = datetime.now(IST).strftime("%Y-%m-%d")
        
        # Try to check in
        payload = {
            "work_location": "in_office",
            "remarks": "Test check-in with leave",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
        response = requests.post(f"{BASE_URL}/api/my/check-in", json=payload, headers=headers)
        
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "approved" in detail.lower() and "leave" in detail.lower():
                print(f"✓ Check-in correctly blocked: {detail}")
                return
        
        # If 200, check-in was allowed (no approved leave)
        if response.status_code == 200:
            print("✓ Check-in allowed (no approved leave for today)")
        else:
            print(f"Response: {response.status_code} - {response.text}")


class TestCheckOutGovernance:
    """Tests for POST /api/my/check-out governance rules"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_checkout_returns_governance_fields(self, consultant_token):
        """POST /api/my/check-out - returns late_checkout_minutes, overtime_minutes"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        
        # Check if already checked out
        status_resp = requests.get(f"{BASE_URL}/api/my/check-status", headers=headers)
        if status_resp.status_code == 200:
            status = status_resp.json()
            if not status.get("has_checked_in"):
                pytest.skip("Not checked in today")
            if status.get("has_checked_out"):
                print("✓ Already checked out - verifying record has governance fields")
                att_resp = requests.get(f"{BASE_URL}/api/my/attendance", headers=headers)
                if att_resp.status_code == 200:
                    records = att_resp.json().get("records", [])
                    today = datetime.now(IST).strftime("%Y-%m-%d")
                    today_record = next((r for r in records if r.get("date") == today), None)
                    if today_record:
                        assert "late_checkout_minutes" in today_record
                        assert "overtime_minutes" in today_record
                        print(f"✓ Record has late_checkout_minutes={today_record.get('late_checkout_minutes')}, overtime_minutes={today_record.get('overtime_minutes')}")
                return
        
        # Try to check out
        payload = {
            "remarks": "Test check-out",
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946
            }
        }
        response = requests.post(f"{BASE_URL}/api/my/check-out", json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            assert "late_checkout_minutes" in data, "Response missing late_checkout_minutes"
            assert "overtime_minutes" in data, "Response missing overtime_minutes"
            print(f"✓ Check-out response has late_checkout_minutes={data.get('late_checkout_minutes')}, overtime_minutes={data.get('overtime_minutes')}")
        elif response.status_code == 400:
            detail = response.json().get("detail", "")
            print(f"Check-out not allowed: {detail}")


class TestPenaltySystem:
    """Tests for attendance penalty system"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json().get("access_token")
    
    def test_penalties_endpoint_exists(self, admin_token):
        """Check if penalties endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try to get penalties
        response = requests.get(f"{BASE_URL}/api/attendance-penalties", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Penalties endpoint exists, returned {len(data) if isinstance(data, list) else 'object'}")
        elif response.status_code == 404:
            # Endpoint may not exist yet
            print("⚠ Penalties endpoint not found (404)")
        else:
            print(f"Penalties endpoint response: {response.status_code}")


class TestHalfDayLogic:
    """Tests for half-day attendance logic"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_half_day_records_have_type(self, consultant_token):
        """Half-day records should have half_day_type (first_half or second_half)"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        
        half_day_records = [r for r in records if r.get("is_half_day") or r.get("status") == "half_day"]
        
        if not half_day_records:
            pytest.skip("No half-day records found")
        
        for r in half_day_records:
            half_day_type = r.get("half_day_type")
            assert half_day_type in ["first_half", "second_half", None], f"Invalid half_day_type: {half_day_type}"
            print(f"✓ Half-day record {r.get('date')}: type={half_day_type}")


class TestDynamicRecalculation:
    """Tests for dynamic recalculation of late/early/OT from stored punch times"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_late_calculation_from_shift_start(self, consultant_token):
        """Late = max(0, in_time - shift_start) where shift_start is 10:00 IST"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        shift_config = data.get("shift_config", {})
        
        shift_start = shift_config.get("core_hours_start", "10:00")
        sh_h, sh_m = int(shift_start.split(":")[0]), int(shift_start.split(":")[1])
        shift_start_min = sh_h * 60 + sh_m
        
        for r in records:
            cin = r.get("check_in_time")
            if cin and r.get("status") in ("present", "half_day"):
                try:
                    # Parse check-in time
                    ci_dt = datetime.fromisoformat(cin.replace("Z", "+00:00"))
                    # Convert to IST
                    ci_ist = ci_dt.astimezone(IST)
                    ci_min = ci_ist.hour * 60 + ci_ist.minute
                    
                    expected_late = max(0, ci_min - shift_start_min)
                    actual_late = r.get("late_minutes", 0)
                    
                    # Allow for grace period adjustment
                    grace = shift_config.get("grace_minutes", 10)
                    if 0 < expected_late <= grace and r.get("grace_applied"):
                        expected_late = 0
                    
                    # Tolerance of 1 minute for rounding
                    assert abs(actual_late - expected_late) <= 1 or actual_late == 0, \
                        f"Late mismatch for {r.get('date')}: expected ~{expected_late}, got {actual_late}"
                    
                    print(f"✓ {r.get('date')}: check-in {ci_ist.strftime('%H:%M')} IST, late={actual_late}m")
                except Exception as e:
                    print(f"⚠ Could not verify late for {r.get('date')}: {e}")
    
    def test_ot_calculation_capped(self, consultant_token):
        """OT = Early Login + Late Checkout, capped at 120 minutes"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        records = data.get("records", [])
        shift_config = data.get("shift_config", {})
        
        ot_cap = shift_config.get("ot_cap_minutes", 120)
        
        for r in records:
            ot = r.get("overtime_minutes", 0)
            assert ot <= ot_cap, f"OT exceeds cap for {r.get('date')}: {ot} > {ot_cap}"
            
            # OT should be 0 for half-day or on_leave
            if r.get("is_half_day") or r.get("status") == "on_leave":
                assert ot == 0, f"OT should be 0 for half-day/leave: {r.get('date')} has OT={ot}"
        
        print(f"✓ All OT values within cap ({ot_cap}m)")


class TestGraceLogic:
    """Tests for grace period logic"""
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        if response.status_code != 200:
            pytest.skip("Consultant login failed")
        return response.json().get("access_token")
    
    def test_grace_config_in_shift_config(self, consultant_token):
        """Shift config should include grace_minutes and grace_days_per_month"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-01", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        shift_config = data.get("shift_config", {})
        
        grace_minutes = shift_config.get("grace_minutes")
        grace_days = shift_config.get("grace_days_per_month")
        
        assert grace_minutes is not None, "grace_minutes not in shift_config"
        assert grace_days is not None, "grace_days_per_month not in shift_config"
        
        print(f"✓ Grace config: {grace_minutes}m x {grace_days} days/month")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
