"""
Test Enhanced Attendance System with Geofencing
Features tested:
1. Office locations are configured (3 offices: Bangalore, Mumbai, Delhi)
2. Clients have geo_coordinates field populated
3. POST /api/my/check-in requires selfie (reject without selfie)
4. POST /api/my/check-in requires GPS location (reject without location)
5. POST /api/my/check-in rejects WFH work_location
6. Non-consulting employee cannot select 'onsite' work location
7. Check-in from approved location (within 500m) is auto-approved
8. Check-in from unknown location requires justification
9. Check-in from unknown location creates pending approval for HR
10. GET /api/hr/pending-attendance-approvals returns pending records
11. POST /api/hr/attendance-approval/{id} can approve/reject attendance
12. POST /api/my/check-out records check-out time and calculates work hours
13. PUT /api/hr/employee/{id}/mobile-access can disable employee app access
14. Disabled employee cannot check-in via mobile app
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
HR_EMAIL = "hr.manager@company.com"
HR_PASSWORD = "hr123"
CONSULTANT_EMAIL = "prakash.rao76@dvconsulting.co.in"  # Consulting dept
CONSULTANT_PASSWORD = "password123"
HR_EMPLOYEE_EMAIL = "prakash.patil68@dvconsulting.co.in"  # HR dept employee
HR_EMPLOYEE_PASSWORD = "password123"

# Office coordinates (Bangalore HQ)
BANGALORE_LAT = 12.9716
BANGALORE_LON = 77.6412

# Unknown location (far from any office)
UNKNOWN_LAT = 13.5000
UNKNOWN_LON = 78.5000

# Sample selfie base64
SAMPLE_SELFIE = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="

# Generate unique test offset to avoid conflicts with previous runs
import random
TEST_DATE_OFFSET = random.randint(300, 500)


class TestOfficeLocationsConfig:
    """Test 1: Office locations are configured"""
    
    def test_office_locations_exist(self, admin_token):
        """Verify 3 office locations are configured: Bangalore, Mumbai, Delhi"""
        response = requests.get(
            f"{BASE_URL}/api/settings/office-locations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get office locations: {response.text}"
        
        data = response.json()
        locations = data.get("locations", [])
        
        # Should have 3 offices
        assert len(locations) >= 3, f"Expected at least 3 offices, found {len(locations)}"
        
        # Check for Bangalore
        bangalore = next((loc for loc in locations if "Bangalore" in loc.get("name", "")), None)
        assert bangalore is not None, "Bangalore office not found"
        assert bangalore.get("latitude") == 12.9716
        assert bangalore.get("longitude") == 77.6412
        
        # Check for Mumbai
        mumbai = next((loc for loc in locations if "Mumbai" in loc.get("name", "")), None)
        assert mumbai is not None, "Mumbai office not found"
        
        # Check for Delhi
        delhi = next((loc for loc in locations if "Delhi" in loc.get("name", "")), None)
        assert delhi is not None, "Delhi office not found"
        
        print(f"✅ Test 1 PASSED: {len(locations)} office locations configured")


class TestClientGeoCoordinates:
    """Test 2: Clients have geo_coordinates field populated"""
    
    def test_clients_have_geo_coordinates(self, admin_token):
        """Verify clients have geo_coordinates populated"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get clients: {response.text}"
        
        clients = response.json()
        assert len(clients) > 0, "No clients found"
        
        # Check how many clients have geo_coordinates
        clients_with_coords = [c for c in clients if c.get("geo_coordinates")]
        assert len(clients_with_coords) > 0, "No clients have geo_coordinates"
        
        # Validate geo_coordinates structure
        sample_client = clients_with_coords[0]
        geo = sample_client["geo_coordinates"]
        assert "latitude" in geo, "Missing latitude in geo_coordinates"
        assert "longitude" in geo, "Missing longitude in geo_coordinates"
        
        print(f"✅ Test 2 PASSED: {len(clients_with_coords)}/{len(clients)} clients have geo_coordinates")


class TestCheckInSelfieRequired:
    """Test 3: POST /api/my/check-in requires selfie (reject without selfie)"""
    
    def test_checkin_without_selfie_rejected(self, consultant_token):
        """Verify check-in without selfie is rejected"""
        # Use unique date to avoid duplicate check-in issues
        test_date = (datetime.now() + timedelta(days=TEST_DATE_OFFSET)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
                # No selfie provided
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "selfie" in response.json().get("detail", "").lower(), f"Error message should mention selfie: {response.text}"
        
        print("✅ Test 3 PASSED: Check-in without selfie is rejected")


class TestCheckInGPSRequired:
    """Test 4: POST /api/my/check-in requires GPS location (reject without location)"""
    
    def test_checkin_without_gps_rejected(self, consultant_token):
        """Verify check-in without GPS location is rejected"""
        test_date = (datetime.now() + timedelta(days=TEST_DATE_OFFSET+1)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE
                # No geo_location provided
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "").lower()
        assert "gps" in detail or "location" in detail, f"Error message should mention GPS/location: {response.text}"
        
        print("✅ Test 4 PASSED: Check-in without GPS location is rejected")


class TestCheckInWFHRejected:
    """Test 5: POST /api/my/check-in rejects WFH work_location"""
    
    def test_wfh_work_location_rejected(self, consultant_token):
        """Verify WFH work_location is rejected"""
        test_date = (datetime.now() + timedelta(days=TEST_DATE_OFFSET+2)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "wfh",  # WFH should be rejected
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "").lower()
        assert "office" in detail or "onsite" in detail or "invalid" in detail, f"Error should indicate only Office/On-Site allowed: {response.text}"
        
        print("✅ Test 5 PASSED: WFH work_location is rejected")


class TestNonConsultingOnsiteRejected:
    """Test 6: Non-consulting employee cannot select 'onsite' work location"""
    
    def test_non_consulting_cannot_use_onsite(self, hr_employee_token):
        """Verify non-consulting employee cannot select onsite"""
        test_date = (datetime.now() + timedelta(days=TEST_DATE_OFFSET+3)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {hr_employee_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "onsite",  # Non-consulting trying onsite
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "").lower()
        assert "consulting" in detail or "delivery" in detail, f"Error should mention Consulting/Delivery only: {response.text}"
        
        print("✅ Test 6 PASSED: Non-consulting employee cannot use 'onsite' work_location")


class TestAutoApprovalWithinGeofence:
    """Test 7: Check-in from approved location (within 500m) is auto-approved"""
    
    def test_checkin_at_office_auto_approved(self, consultant_token, cleanup_attendance):
        """Verify check-in within 500m of office is auto-approved"""
        test_date = (datetime.now() + timedelta(days=TEST_DATE_OFFSET+10)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {
                    "latitude": BANGALORE_LAT,  # Exactly at office
                    "longitude": BANGALORE_LON,
                    "accuracy": 10
                }
            }
        )
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("approval_status") == "approved", f"Expected auto-approved, got {data.get('approval_status')}"
        assert "Bangalore" in data.get("matched_location", ""), f"Should match Bangalore office: {data}"
        
        # Store for cleanup
        cleanup_attendance.append({"id": data.get("id"), "date": test_date})
        
        print("✅ Test 7 PASSED: Check-in at approved location is auto-approved")


class TestUnknownLocationRequiresJustification:
    """Test 8: Check-in from unknown location requires justification"""
    
    def test_unknown_location_without_justification_rejected(self, consultant_token):
        """Verify check-in from unknown location without justification is rejected"""
        test_date = (datetime.now() + timedelta(days=201)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {
                    "latitude": UNKNOWN_LAT,  # Far from any office (>500m)
                    "longitude": UNKNOWN_LON
                }
                # No justification
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "").lower()
        assert "justification" in detail or "approved location" in detail, f"Error should require justification: {response.text}"
        
        print("✅ Test 8 PASSED: Unknown location without justification is rejected")


class TestUnknownLocationCreatesPendingApproval:
    """Test 9: Check-in from unknown location creates pending approval for HR"""
    
    def test_unknown_location_with_justification_creates_pending(self, consultant_token, cleanup_attendance):
        """Verify check-in with justification creates pending approval"""
        test_date = (datetime.now() + timedelta(days=202)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {
                    "latitude": UNKNOWN_LAT,
                    "longitude": UNKNOWN_LON
                },
                "justification": "Client meeting at offsite location"
            }
        )
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("approval_status") == "pending_approval", f"Expected pending_approval, got {data.get('approval_status')}"
        
        cleanup_attendance.append({"id": data.get("id"), "date": test_date})
        
        print("✅ Test 9 PASSED: Unknown location with justification creates pending approval")


class TestHRPendingApprovalsEndpoint:
    """Test 10: GET /api/hr/pending-attendance-approvals returns pending records"""
    
    def test_hr_can_view_pending_approvals(self, hr_token):
        """Verify HR can view pending attendance approvals"""
        response = requests.get(
            f"{BASE_URL}/api/hr/pending-attendance-approvals",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get pending approvals: {response.text}"
        
        data = response.json()
        assert "pending_approvals" in data, "Response should have pending_approvals field"
        assert "count" in data, "Response should have count field"
        
        print(f"✅ Test 10 PASSED: HR can view pending approvals (count: {data.get('count', 0)})")
    
    def test_non_hr_cannot_view_pending_approvals(self, consultant_token):
        """Verify non-HR cannot view pending approvals"""
        response = requests.get(
            f"{BASE_URL}/api/hr/pending-attendance-approvals",
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        
        print("✅ Test 10b PASSED: Non-HR cannot view pending approvals")


class TestHRAttendanceApproval:
    """Test 11: POST /api/hr/attendance-approval/{id} can approve/reject attendance"""
    
    def test_hr_can_approve_attendance(self, hr_token, consultant_token, cleanup_attendance):
        """Verify HR can approve pending attendance"""
        # First create a pending attendance record
        test_date = (datetime.now() + timedelta(days=203)).strftime("%Y-%m-%d")
        
        checkin_response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": UNKNOWN_LAT, "longitude": UNKNOWN_LON},
                "justification": "Working from remote client site"
            }
        )
        
        assert checkin_response.status_code == 200, f"Failed to create check-in: {checkin_response.text}"
        attendance_id = checkin_response.json().get("id")
        cleanup_attendance.append({"id": attendance_id, "date": test_date})
        
        # Now HR approves it
        approval_response = requests.post(
            f"{BASE_URL}/api/hr/attendance-approval/{attendance_id}",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"action": "approve", "remarks": "Approved by test"}
        )
        
        assert approval_response.status_code == 200, f"Failed to approve: {approval_response.text}"
        assert "approved" in approval_response.json().get("message", "").lower()
        
        print("✅ Test 11 PASSED: HR can approve attendance")
    
    def test_hr_can_reject_attendance(self, hr_token, consultant_token, cleanup_attendance):
        """Verify HR can reject pending attendance"""
        test_date = (datetime.now() + timedelta(days=204)).strftime("%Y-%m-%d")
        
        checkin_response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": UNKNOWN_LAT, "longitude": UNKNOWN_LON},
                "justification": "Emergency work from home"
            }
        )
        
        assert checkin_response.status_code == 200
        attendance_id = checkin_response.json().get("id")
        cleanup_attendance.append({"id": attendance_id, "date": test_date})
        
        # HR rejects it
        rejection_response = requests.post(
            f"{BASE_URL}/api/hr/attendance-approval/{attendance_id}",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"action": "reject", "remarks": "Not a valid reason"}
        )
        
        assert rejection_response.status_code == 200
        assert "rejected" in rejection_response.json().get("message", "").lower()
        
        print("✅ Test 11b PASSED: HR can reject attendance")


class TestCheckOut:
    """Test 12: POST /api/my/check-out records check-out time and calculates work hours"""
    
    def test_checkout_records_time_and_hours(self, consultant_token, cleanup_attendance):
        """Verify check-out records time and calculates work hours"""
        test_date = (datetime.now() + timedelta(days=205)).strftime("%Y-%m-%d")
        
        # First check in
        checkin_response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
            }
        )
        
        assert checkin_response.status_code == 200, f"Check-in failed: {checkin_response.text}"
        attendance_id = checkin_response.json().get("id")
        cleanup_attendance.append({"id": attendance_id, "date": test_date})
        
        # Wait a bit before checkout
        time.sleep(1)
        
        # Now check out
        checkout_response = requests.post(
            f"{BASE_URL}/api/my/check-out",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
            }
        )
        
        assert checkout_response.status_code == 200, f"Check-out failed: {checkout_response.text}"
        
        data = checkout_response.json()
        assert "check_out_time" in data, "Response should have check_out_time"
        assert "work_hours" in data, "Response should have work_hours"
        assert data["work_hours"] is not None, "work_hours should be calculated"
        
        print(f"✅ Test 12 PASSED: Check-out recorded with work_hours={data['work_hours']}")
    
    def test_checkout_without_checkin_rejected(self, consultant_token):
        """Verify check-out without check-in is rejected"""
        test_date = (datetime.now() + timedelta(days=206)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/my/check-out",
            headers={"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"},
            json={"date": test_date}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "check in first" in response.json().get("detail", "").lower()
        
        print("✅ Test 12b PASSED: Check-out without check-in is rejected")


class TestMobileAccessToggle:
    """Test 13: PUT /api/hr/employee/{id}/mobile-access can disable employee app access"""
    
    def test_hr_can_disable_mobile_access(self, hr_token, admin_token):
        """Verify HR can disable employee mobile app access"""
        # Get an employee ID
        employees_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert employees_response.status_code == 200
        employees = employees_response.json()
        
        # Find an employee (not the test consultant)
        test_employee = next((e for e in employees if e.get("email") != CONSULTANT_EMAIL), None)
        assert test_employee, "No employee found for testing"
        
        employee_id = test_employee["id"]
        
        # Disable mobile access
        response = requests.put(
            f"{BASE_URL}/api/hr/employee/{employee_id}/mobile-access",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"disabled": True, "reason": "Test - security concern"}
        )
        
        assert response.status_code == 200, f"Failed to disable access: {response.text}"
        
        # Re-enable for cleanup
        requests.put(
            f"{BASE_URL}/api/hr/employee/{employee_id}/mobile-access",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"disabled": False}
        )
        
        print("✅ Test 13 PASSED: HR can disable/enable mobile app access")


class TestDisabledEmployeeCannotCheckin:
    """Test 14: Disabled employee cannot check-in via mobile app"""
    
    def test_disabled_employee_checkin_blocked(self, admin_token, hr_token):
        """Verify disabled employee cannot check-in"""
        # Use HR employee for this test
        hr_employee_token = get_token(HR_EMPLOYEE_EMAIL, HR_EMPLOYEE_PASSWORD)
        
        # Get HR employee ID
        employees_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        employees = employees_response.json()
        hr_emp = next((e for e in employees if e.get("email") == HR_EMPLOYEE_EMAIL), None)
        
        if not hr_emp:
            pytest.skip("HR employee not found")
        
        employee_id = hr_emp["id"]
        
        # Disable mobile access
        disable_response = requests.put(
            f"{BASE_URL}/api/hr/employee/{employee_id}/mobile-access",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"disabled": True, "reason": "Test - verification"}
        )
        assert disable_response.status_code == 200
        
        # Now try to check-in as the disabled employee
        test_date = (datetime.now() + timedelta(days=207)).strftime("%Y-%m-%d")
        checkin_response = requests.post(
            f"{BASE_URL}/api/my/check-in",
            headers={"Authorization": f"Bearer {hr_employee_token}", "Content-Type": "application/json"},
            json={
                "date": test_date,
                "work_location": "in_office",
                "selfie": SAMPLE_SELFIE,
                "geo_location": {"latitude": BANGALORE_LAT, "longitude": BANGALORE_LON}
            }
        )
        
        # Should be blocked
        assert checkin_response.status_code == 403, f"Expected 403 for disabled employee, got {checkin_response.status_code}: {checkin_response.text}"
        assert "disabled" in checkin_response.json().get("detail", "").lower()
        
        # Re-enable for cleanup
        requests.put(
            f"{BASE_URL}/api/hr/employee/{employee_id}/mobile-access",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"disabled": False}
        )
        
        print("✅ Test 14 PASSED: Disabled employee cannot check-in")


# =========== Helper Functions ===========

def get_token(email: str, password: str) -> str:
    """Get authentication token for a user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        headers={"Content-Type": "application/json"},
        json={"email": email, "password": password}
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed for {email}: {response.text}")
    return response.json()["access_token"]


# =========== Fixtures ===========

@pytest.fixture(scope="module")
def admin_token():
    """Get admin token"""
    return get_token(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def hr_token():
    """Get HR manager token"""
    return get_token(HR_EMAIL, HR_PASSWORD)


@pytest.fixture(scope="module")
def consultant_token():
    """Get consultant token"""
    return get_token(CONSULTANT_EMAIL, CONSULTANT_PASSWORD)


@pytest.fixture(scope="module")
def hr_employee_token():
    """Get HR employee token (non-consulting)"""
    return get_token(HR_EMPLOYEE_EMAIL, HR_EMPLOYEE_PASSWORD)


@pytest.fixture(scope="function")
def cleanup_attendance(admin_token):
    """Track attendance records created during tests for cleanup"""
    records = []
    yield records
    # Cleanup not strictly needed as we use future dates


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
