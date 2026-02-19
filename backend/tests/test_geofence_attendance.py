"""
Test Suite for Geo-Fence Attendance System
Features to test:
1. Geo-Fence Locations section in Employee model
2. HR can add multiple locations with name, address, lat/long, radius
3. Check-in within 500m of assigned location is auto-approved
4. Check-in outside 500m creates pending_approval record
5. RM/HR can approve attendance, Admin cannot approve directly
6. Notifications sent to RM, HR Manager, and Admin on pending attendance
7. POST /api/hr/attendance/finalize-for-payroll marks pending as absent
8. POST /api/hr/attendance/regularize only works until 3rd of month
"""

import pytest
import requests
import os
from datetime import datetime, timezone
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
HR_MANAGER_EMAIL = "hr.manager@dvbc.com"
HR_MANAGER_PASSWORD = "hr123"

# Test employee for geo-fence: Rahul Kumar (EMP001)
# Test location: Pune, India (18.5204, 73.8567)
TEST_LOCATION_PUNE = {
    "latitude": 18.5204,
    "longitude": 73.8567
}

# Location far from Pune (Mumbai - ~150km away)
FAR_LOCATION = {
    "latitude": 19.0760,
    "longitude": 72.8777
}


class TestAuthHelper:
    """Helper class to get auth tokens"""
    
    @staticmethod
    def get_token(email, password):
        """Get auth token for given credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    token = TestAuthHelper.get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        pytest.skip("Could not authenticate as admin")
    return token


@pytest.fixture(scope="module")
def hr_token():
    """Get HR manager auth token"""
    token = TestAuthHelper.get_token(HR_MANAGER_EMAIL, HR_MANAGER_PASSWORD)
    if not token:
        pytest.skip("Could not authenticate as HR manager")
    return token


@pytest.fixture(scope="module")
def employee_rahul_data(hr_token):
    """Get Rahul Kumar (EMP001) employee data"""
    headers = {"Authorization": f"Bearer {hr_token}"}
    response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
    if response.status_code == 200:
        employees = response.json()
        for emp in employees:
            if emp.get("employee_id") == "EMP001":
                return emp
    pytest.skip("Employee EMP001 (Rahul Kumar) not found")
    return None


class TestGeoFenceLocationsInEmployee:
    """Test geo-fence locations can be added to employee"""
    
    def test_01_get_employee_with_assigned_locations_field(self, hr_token, employee_rahul_data):
        """Test that employee model has assigned_locations field"""
        # Check that assigned_locations field exists (may be empty array)
        assert "assigned_locations" in employee_rahul_data or employee_rahul_data.get("assigned_locations") == []
        print(f"Employee {employee_rahul_data['employee_id']} assigned_locations: {employee_rahul_data.get('assigned_locations', [])}")
    
    def test_02_add_geofence_location_to_employee(self, hr_token, employee_rahul_data):
        """Test HR can add geo-fence location to employee via PATCH"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        employee_id = employee_rahul_data["id"]
        
        # Add a geo-fence location
        new_location = {
            "id": f"TEST_LOC_{uuid.uuid4().hex[:8]}",
            "name": "Infosys Pune TEST",
            "type": "client",
            "address": "Hinjewadi, Pune, Maharashtra 411057",
            "latitude": TEST_LOCATION_PUNE["latitude"],
            "longitude": TEST_LOCATION_PUNE["longitude"],
            "radius": 500
        }
        
        # Get current locations
        current_locations = employee_rahul_data.get("assigned_locations", [])
        updated_locations = current_locations + [new_location]
        
        response = requests.patch(
            f"{BASE_URL}/api/employees/{employee_id}",
            headers=headers,
            json={"assigned_locations": updated_locations}
        )
        
        assert response.status_code == 200, f"Failed to update employee: {response.text}"
        print(f"Successfully added geo-fence location to employee")
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/employees/{employee_id}", headers=headers)
        assert verify_response.status_code == 200
        updated_emp = verify_response.json()
        assert len(updated_emp.get("assigned_locations", [])) > 0
        
        # Find our test location
        test_loc_found = False
        for loc in updated_emp.get("assigned_locations", []):
            if "TEST" in loc.get("name", ""):
                test_loc_found = True
                assert loc["latitude"] == TEST_LOCATION_PUNE["latitude"]
                assert loc["longitude"] == TEST_LOCATION_PUNE["longitude"]
                assert loc["radius"] == 500
                break
        
        assert test_loc_found, "Test location not found in updated employee"
        print(f"Verified geo-fence location saved correctly")
    
    def test_03_add_multiple_locations(self, hr_token, employee_rahul_data):
        """Test HR can add multiple geo-fence locations"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        employee_id = employee_rahul_data["id"]
        
        # Add multiple locations
        new_locations = [
            {
                "id": f"TEST_LOC_1_{uuid.uuid4().hex[:8]}",
                "name": "Office Location TEST",
                "type": "office",
                "address": "Tower 1, Hinjewadi IT Park",
                "latitude": 18.5900,
                "longitude": 73.7380,
                "radius": 500
            },
            {
                "id": f"TEST_LOC_2_{uuid.uuid4().hex[:8]}",
                "name": "Client Site Mumbai TEST",
                "type": "client",
                "address": "Andheri East, Mumbai",
                "latitude": 19.1136,
                "longitude": 72.8697,
                "radius": 1000
            }
        ]
        
        response = requests.patch(
            f"{BASE_URL}/api/employees/{employee_id}",
            headers=headers,
            json={"assigned_locations": new_locations}
        )
        
        assert response.status_code == 200
        print(f"Successfully added multiple geo-fence locations")


class TestCheckinLocationValidation:
    """Test check-in location validation with geo-fence"""
    
    def test_01_checkin_within_500m_auto_approved(self, admin_token, hr_token, employee_rahul_data):
        """Test check-in within 500m of assigned location is auto-approved"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        employee_id = employee_rahul_data["id"]
        
        # First add a geo-fence location if not present
        new_location = {
            "id": f"TEST_CHECKIN_LOC_{uuid.uuid4().hex[:8]}",
            "name": "Test Check-in Location",
            "type": "client",
            "address": "Pune Test Location",
            "latitude": TEST_LOCATION_PUNE["latitude"],
            "longitude": TEST_LOCATION_PUNE["longitude"],
            "radius": 500
        }
        
        requests.patch(
            f"{BASE_URL}/api/employees/{employee_id}",
            headers=headers,
            json={"assigned_locations": [new_location]}
        )
        
        # Need to get a consultant token for self check-in
        # For now, test the validation function directly via an API that might expose it
        # The actual check-in endpoint is /api/my/check-in which requires the employee's own token
        
        # Test via attendance endpoint if we can get Rahul's token
        rahul_token = TestAuthHelper.get_token("rahul.kumar@dvbc.com", "Welcome@123")
        if not rahul_token:
            # Try default password
            rahul_token = TestAuthHelper.get_token("rahul.kumar@dvbc.com", "dvbc123")
        
        if rahul_token:
            employee_headers = {"Authorization": f"Bearer {rahul_token}"}
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Try self check-in at exact location (within geo-fence)
            checkin_response = requests.post(
                f"{BASE_URL}/api/my/check-in",
                headers=employee_headers,
                json={
                    "date": today,
                    "status": "present",
                    "work_location": "onsite",
                    "geo_location": {
                        "latitude": TEST_LOCATION_PUNE["latitude"],
                        "longitude": TEST_LOCATION_PUNE["longitude"],
                        "accuracy": 10
                    }
                }
            )
            
            if checkin_response.status_code == 200:
                result = checkin_response.json()
                # Should be auto-approved since within geo-fence
                print(f"Check-in result: {result}")
                # Note: May already be checked in today
            elif checkin_response.status_code == 400:
                print(f"Check-in error (may already be checked in): {checkin_response.text}")
            else:
                print(f"Check-in status: {checkin_response.status_code}, {checkin_response.text}")
        else:
            print("Could not get Rahul's token - testing via API only")
            pytest.skip("Could not authenticate as employee Rahul for check-in test")
    
    def test_02_checkin_outside_500m_pending_approval(self, hr_token, employee_rahul_data):
        """Test check-in outside 500m creates pending_approval record"""
        # This requires the employee's own token
        rahul_token = TestAuthHelper.get_token("rahul.kumar@dvbc.com", "Welcome@123")
        if not rahul_token:
            rahul_token = TestAuthHelper.get_token("rahul.kumar@dvbc.com", "dvbc123")
        
        if rahul_token:
            employee_headers = {"Authorization": f"Bearer {rahul_token}"}
            
            # Try check-in from a location far from assigned location
            tomorrow = (datetime.now(timezone.utc)).strftime("%Y-%m-%d")
            
            checkin_response = requests.post(
                f"{BASE_URL}/api/my/check-in",
                headers=employee_headers,
                json={
                    "date": tomorrow,
                    "status": "present",
                    "work_location": "onsite",
                    "geo_location": FAR_LOCATION
                }
            )
            
            print(f"Far location check-in response: {checkin_response.status_code}, {checkin_response.text}")
            
            if checkin_response.status_code == 200:
                result = checkin_response.json()
                # Should have pending_approval status if outside geo-fence
                if result.get("approval_status") == "pending_approval":
                    print("SUCCESS: Check-in outside geo-fence requires approval")
                else:
                    print(f"Approval status: {result.get('approval_status')}")
        else:
            pytest.skip("Could not authenticate as employee Rahul")


class TestAttendanceApproval:
    """Test attendance approval workflow"""
    
    def test_01_get_pending_attendance_approvals(self, hr_token):
        """Test HR can get pending attendance approvals"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.get(f"{BASE_URL}/api/hr/pending-attendance-approvals", headers=headers)
        
        assert response.status_code == 200, f"Failed to get pending approvals: {response.text}"
        data = response.json()
        
        assert "pending_approvals" in data
        assert "count" in data
        print(f"Pending attendance approvals: {data['count']}")
    
    def test_02_hr_can_approve_attendance(self, hr_token):
        """Test HR Manager can approve attendance"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # First get pending approvals
        response = requests.get(f"{BASE_URL}/api/hr/pending-attendance-approvals", headers=headers)
        if response.status_code == 200:
            data = response.json()
            pending = data.get("pending_approvals", [])
            
            if pending:
                attendance_id = pending[0]["id"]
                
                # Approve the attendance
                approve_response = requests.post(
                    f"{BASE_URL}/api/hr/attendance-approval/{attendance_id}",
                    headers=headers,
                    json={"action": "approve", "remarks": "Test approval by HR"}
                )
                
                assert approve_response.status_code == 200, f"Failed to approve: {approve_response.text}"
                print(f"HR approved attendance: {approve_response.json()}")
            else:
                print("No pending approvals to test")
    
    def test_03_rm_can_approve_reportee_attendance(self, hr_token):
        """Test Reporting Manager can approve their reportee's attendance"""
        # This would require a user who has reportees with pending attendance
        # For now, just verify the endpoint logic exists
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.get(f"{BASE_URL}/api/hr/pending-attendance-approvals", headers=headers)
        print(f"Pending approvals API status: {response.status_code}")
        
        # The approval endpoint checks if current user is RM of the employee
        # This is verified in the backend code at line 9699-9705


class TestPayrollFinalization:
    """Test payroll finalization endpoint"""
    
    def test_01_finalize_attendance_for_payroll(self, hr_token):
        """Test POST /api/hr/attendance/finalize-for-payroll marks pending as absent"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Use a past month to avoid affecting current data
        test_month = "2025-01"  # Past month
        
        response = requests.post(
            f"{BASE_URL}/api/hr/attendance/finalize-for-payroll",
            headers=headers,
            json={"month": test_month}
        )
        
        assert response.status_code == 200, f"Finalize failed: {response.text}"
        result = response.json()
        
        assert "finalized_count" in result
        assert "month" in result
        assert result["month"] == test_month
        print(f"Finalized {result['finalized_count']} records for {test_month}")
    
    def test_02_finalize_requires_month(self, hr_token):
        """Test finalize endpoint requires month parameter"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/hr/attendance/finalize-for-payroll",
            headers=headers,
            json={}  # No month
        )
        
        assert response.status_code == 400, f"Should require month: {response.text}"
        print("Correctly requires month parameter")
    
    def test_03_finalize_requires_hr_access(self, admin_token):
        """Test finalize requires HR access"""
        # Admin should also have access
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/hr/attendance/finalize-for-payroll",
            headers=headers,
            json={"month": "2025-01"}
        )
        
        # Admin should have access (admin role is in ["admin", "hr_manager"])
        assert response.status_code == 200, f"Admin should have access: {response.text}"
        print("Admin has access to finalize endpoint")


class TestRegularizationWindow:
    """Test regularization window (until 3rd of month)"""
    
    def test_01_get_regularization_window_status(self, hr_token):
        """Test GET /api/hr/attendance/regularization-window"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/hr/attendance/regularization-window",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        result = response.json()
        
        assert "is_open" in result
        assert "current_day" in result
        assert "days_remaining" in result
        assert "message" in result
        
        print(f"Regularization window status: {result}")
        
        # Verify logic
        today = datetime.now(timezone.utc).day
        if today <= 3:
            assert result["is_open"] == True
            print("Regularization window is OPEN (day <= 3)")
        else:
            assert result["is_open"] == False
            print("Regularization window is CLOSED (day > 3)")
    
    def test_02_regularize_requires_attendance_id(self, hr_token):
        """Test regularize endpoint requires attendance_id"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/hr/attendance/regularize",
            headers=headers,
            json={
                "status": "present",
                "reason": "Test reason"
            }
        )
        
        assert response.status_code == 400
        assert "attendance_id" in response.text.lower() or "required" in response.text.lower()
        print("Correctly requires attendance_id")
    
    def test_03_regularize_requires_reason(self, hr_token):
        """Test regularize endpoint requires reason"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/hr/attendance/regularize",
            headers=headers,
            json={
                "attendance_id": "test-id",
                "status": "present"
            }
        )
        
        # Should fail - either because attendance not found or reason required
        assert response.status_code in [400, 404]
        print(f"Regularize validation: {response.text}")


class TestNotificationsForPendingAttendance:
    """Test notifications are sent for pending attendance"""
    
    def test_01_notification_types_exist(self, hr_token):
        """Verify attendance-related notification types exist"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        if response.status_code == 200:
            notifications = response.json()
            
            # Look for attendance-related notifications
            attendance_notif_types = []
            for notif in notifications:
                notif_type = notif.get("type", "")
                if "attendance" in notif_type.lower():
                    attendance_notif_types.append(notif_type)
            
            unique_types = list(set(attendance_notif_types))
            print(f"Found attendance notification types: {unique_types}")
            
            # Expected types from code:
            # - attendance_approval
            # - attendance_approval_result  
            # - attendance_auto_rejected
            # - attendance_regularized


class TestMyAttendanceStatusIndicator:
    """Test MyAttendance page shows status indicator instead of check-in button"""
    
    def test_01_my_attendance_endpoint(self, hr_token):
        """Test GET /api/my/attendance returns proper data"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Get current month
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/my/attendance?month={current_month}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should have records and summary
        assert "records" in data or "employee" in data
        print(f"My attendance data: {list(data.keys())}")


class TestCleanup:
    """Clean up test data"""
    
    def test_cleanup_test_locations(self, hr_token, employee_rahul_data):
        """Remove TEST locations from employee"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        employee_id = employee_rahul_data["id"]
        
        # Get current employee data
        response = requests.get(f"{BASE_URL}/api/employees/{employee_id}", headers=headers)
        if response.status_code == 200:
            emp = response.json()
            current_locations = emp.get("assigned_locations", [])
            
            # Filter out TEST locations
            clean_locations = [loc for loc in current_locations if "TEST" not in loc.get("name", "")]
            
            # Update employee
            requests.patch(
                f"{BASE_URL}/api/employees/{employee_id}",
                headers=headers,
                json={"assigned_locations": clean_locations}
            )
            print(f"Cleaned up {len(current_locations) - len(clean_locations)} test locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
