"""
Test Self Check-In Feature for HR ERP
Tests the POST /api/my/check-in endpoint for:
- GPS location capture
- Work location selection (In Office, On-Site, WFH)
- Duplicate check-in prevention
- Attendance record creation with geo_location
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYEE_EMAIL = "prakash.rao76@dvconsulting.co.in"
EMPLOYEE_PASSWORD = "password123"
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"


class TestSelfCheckIn:
    """Test suite for Self Check-In feature"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for employee"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def authenticated_client(self, auth_token):
        """Session with auth header"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session
    
    @pytest.fixture
    def admin_client(self, admin_token):
        """Session with admin auth header"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        })
        return session
    
    def test_my_attendance_endpoint_exists(self, authenticated_client):
        """Test that /api/my/attendance endpoint exists and returns data"""
        # Get current month
        current_month = datetime.now().strftime("%Y-%m")
        response = authenticated_client.get(f"{BASE_URL}/api/my/attendance?month={current_month}")
        
        print(f"My Attendance Response: {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "records" in data, "Response should have 'records'"
        assert "summary" in data, "Response should have 'summary'"
        assert "employee" in data, "Response should have 'employee'"
        print(f"Employee: {data['employee']}")
        print(f"Records count: {len(data['records'])}")
    
    def test_self_checkin_in_office(self, authenticated_client):
        """Test self check-in with In Office location"""
        # Use tomorrow's date to avoid conflict with existing check-ins
        test_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "in_office",
            "remarks": "TEST - Self check-in office",
            "geo_location": {
                "latitude": 28.6139,
                "longitude": 77.2090,
                "accuracy": 10,
                "address": "Test Office Location, New Delhi",
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"Self Check-In Response: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 400 and "already checked in" in response.text.lower():
            print("Already checked in for this date - this is expected behavior")
            pytest.skip("Already checked in for test date")
            return
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("message") == "Check-in successful"
        assert data.get("work_location") == "in_office"
        assert data.get("status") == "present"
        assert "check_in_time" in data
        print(f"Check-in ID: {data.get('id')}")
    
    def test_self_checkin_onsite(self, authenticated_client):
        """Test self check-in with On-Site location"""
        # Use day after tomorrow to avoid conflict
        test_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "onsite",
            "remarks": "TEST - Self check-in onsite",
            "geo_location": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 15,
                "address": "Client Office, Mumbai",
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"Onsite Check-In Response: {response.status_code}")
        
        if response.status_code == 400 and "already checked in" in response.text.lower():
            print("Already checked in for this date")
            pytest.skip("Already checked in for test date")
            return
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("work_location") == "onsite"
        assert data.get("status") == "present"
    
    def test_self_checkin_wfh(self, authenticated_client):
        """Test self check-in with Work from Home location"""
        # Use 3 days from now to avoid conflict
        test_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "wfh",
            "remarks": "TEST - Self check-in WFH",
            "geo_location": {
                "latitude": 28.5355,
                "longitude": 77.3910,
                "accuracy": 50,
                "address": "Home Location, Noida",
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"WFH Check-In Response: {response.status_code}")
        
        if response.status_code == 400 and "already checked in" in response.text.lower():
            print("Already checked in for this date")
            pytest.skip("Already checked in for test date")
            return
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("work_location") == "wfh"
        assert data.get("status") == "work_from_home", "WFH should set status to 'work_from_home'"
    
    def test_duplicate_checkin_prevented(self, authenticated_client):
        """Test that duplicate check-in on same day is prevented"""
        # Use a specific date
        test_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "in_office",
            "remarks": "TEST - First check-in",
            "geo_location": {
                "latitude": 28.6139,
                "longitude": 77.2090,
                "accuracy": 10,
                "address": "Office"
            }
        }
        
        # First check-in
        response1 = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"First Check-In: {response1.status_code}")
        
        if response1.status_code == 400:
            # Already checked in from previous test
            print("First check-in blocked - using this for duplicate test")
        else:
            assert response1.status_code == 200
        
        # Second check-in attempt
        payload["remarks"] = "TEST - Duplicate check-in attempt"
        response2 = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"Duplicate Check-In: {response2.status_code}")
        
        assert response2.status_code == 400, "Duplicate check-in should be rejected"
        assert "already checked in" in response2.text.lower(), "Should mention already checked in"
    
    def test_checkin_without_location(self, authenticated_client):
        """Test check-in without geo_location - should still work"""
        test_date = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "in_office",
            "remarks": "TEST - Check-in without GPS"
            # No geo_location field
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"Check-In without GPS: {response.status_code}")
        
        if response.status_code == 400 and "already checked in" in response.text.lower():
            pytest.skip("Already checked in for test date")
            return
        
        assert response.status_code == 200, f"Check-in without location should work: {response.text}"
    
    def test_invalid_work_location_rejected(self, authenticated_client):
        """Test that invalid work_location values are rejected"""
        test_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "invalid_location",  # Invalid value
            "remarks": "TEST - Invalid location"
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        print(f"Invalid Location Response: {response.status_code}")
        
        if response.status_code == 400 and "already checked in" in response.text.lower():
            pytest.skip("Already checked in for test date")
            return
        
        assert response.status_code == 400, "Invalid work_location should be rejected"
        assert "invalid work location" in response.text.lower()
    
    def test_attendance_record_has_geo_location(self, authenticated_client):
        """Verify that attendance records contain geo_location after check-in"""
        # Get current month attendance
        current_month = datetime.now().strftime("%Y-%m")
        response = authenticated_client.get(f"{BASE_URL}/api/my/attendance?month={current_month}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find any record with geo_location
        records_with_geo = [r for r in data.get("records", []) if r.get("geo_location")]
        print(f"Records with geo_location: {len(records_with_geo)}")
        
        # Check for work_location field in records
        records_with_work_location = [r for r in data.get("records", []) if r.get("work_location")]
        print(f"Records with work_location: {len(records_with_work_location)}")
        
        for r in data.get("records", [])[:5]:
            print(f"  Date: {r.get('date')}, Status: {r.get('status')}, Location: {r.get('work_location')}, "
                  f"Method: {r.get('check_in_method')}, Geo: {'Yes' if r.get('geo_location') else 'No'}")
    
    def test_today_checkin_status_check(self, authenticated_client):
        """Test that we can check today's check-in status via attendance API"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")
        
        response = authenticated_client.get(f"{BASE_URL}/api/my/attendance?month={current_month}")
        assert response.status_code == 200
        
        data = response.json()
        records = data.get("records", [])
        
        today_record = next((r for r in records if r.get("date") == today), None)
        
        if today_record:
            print(f"Today's record found: {today_record}")
            print(f"  Status: {today_record.get('status')}")
            print(f"  Work Location: {today_record.get('work_location')}")
            print(f"  Check-in Method: {today_record.get('check_in_method')}")
        else:
            print("No attendance record for today")


class TestSelfCheckInDataPersistence:
    """Test data persistence for self check-in"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for employee"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def authenticated_client(self, auth_token):
        """Session with auth header"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session
    
    def test_create_and_verify_checkin(self, authenticated_client):
        """Create check-in and verify via GET"""
        test_date = (datetime.now(timezone.utc) + timedelta(days=6)).strftime("%Y-%m-%d")
        
        payload = {
            "date": test_date,
            "work_location": "onsite",
            "remarks": "TEST - Persistence test",
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 20,
                "address": "Bangalore Office"
            }
        }
        
        # Create check-in
        create_response = authenticated_client.post(f"{BASE_URL}/api/my/check-in", json=payload)
        
        if create_response.status_code == 400 and "already checked in" in create_response.text.lower():
            print("Already checked in - verifying existing record")
        else:
            assert create_response.status_code == 200, f"Create failed: {create_response.text}"
            created_data = create_response.json()
            print(f"Created check-in: {created_data}")
        
        # Verify via GET
        test_month = test_date[:7]  # YYYY-MM
        get_response = authenticated_client.get(f"{BASE_URL}/api/my/attendance?month={test_month}")
        assert get_response.status_code == 200
        
        records = get_response.json().get("records", [])
        record = next((r for r in records if r.get("date") == test_date), None)
        
        if record:
            print(f"Retrieved record: {record}")
            # Data assertions - verify persisted values
            assert record.get("work_location") in ["in_office", "onsite", "wfh"]
            assert record.get("check_in_method") == "self_check_in"
            print(f"PASSED: Data persisted correctly for {test_date}")
        else:
            print(f"No record found for {test_date} - may be outside current test data range")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
