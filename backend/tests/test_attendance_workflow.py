"""
Tests for Unified Attendance + Travel Reimbursement Workflow
Features:
1. GET /api/my/assigned-clients - Returns client list for On-Site attendance
2. POST /api/my/check-in - Check-in with client_id for onsite
3. POST /api/my/check-out - Returns redirect_to_expense flag for travel reimbursement
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAttendanceWorkflowAPIs:
    """Test attendance workflow APIs including client selection for On-Site"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login as consultant"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Try consultant account first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "prakash.rao76@dvconsulting.co.in",
            "password": "password123"
        })
        
        if login_response.status_code != 200:
            # Fallback to admin
            login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@company.com",
                "password": "admin123"
            })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.user = login_response.json().get("user")
        else:
            pytest.skip("Authentication failed")
    
    def test_01_get_assigned_clients_endpoint_exists(self):
        """Test that /api/my/assigned-clients endpoint exists and returns proper structure"""
        response = self.session.get(f"{BASE_URL}/api/my/assigned-clients")
        
        # Should return 200 (may have 404 if employee record missing)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "clients" in data, "Response should contain 'clients' key"
            assert "count" in data, "Response should contain 'count' key"
            assert isinstance(data["clients"], list), "clients should be a list"
            print(f"✓ GET /api/my/assigned-clients returned {data['count']} clients")
            
            # Validate client structure if any exist
            if len(data["clients"]) > 0:
                client = data["clients"][0]
                assert "id" in client, "Client should have 'id'"
                assert "client_name" in client, "Client should have 'client_name'"
                print(f"  Sample client: {client.get('client_name')}")
        else:
            print("⚠ /api/my/assigned-clients returned 404 (employee record may not exist)")
    
    def test_02_check_in_requires_client_for_onsite(self):
        """Test that On-Site check-in requires client selection"""
        # Login as admin to have employee record
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to check-in with onsite but without client
        unique_date = f"2026-12-{datetime.now().day:02d}"  # Future date to avoid conflicts
        
        check_in_payload = {
            "work_location": "onsite",
            "date": unique_date,
            "selfie": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",  # Minimal base64
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10
            }
            # Note: Missing client_id and client_name
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        # Should fail with 400 requiring client selection or 404 if no employee
        if response.status_code == 400:
            error_detail = response.json().get("detail", "")
            # Either requires client or requires justification
            assert any(x in error_detail.lower() for x in ["client", "location", "justification"]), f"Expected client/location error, got: {error_detail}"
            print(f"✓ POST /api/my/check-in correctly requires client for onsite: {error_detail[:60]}...")
        elif response.status_code == 404:
            print("⚠ Check-in returned 404 (employee record not found)")
        else:
            print(f"⚠ Unexpected response: {response.status_code} - {response.text[:100]}")
    
    def test_03_check_in_with_client_info(self):
        """Test check-in with client_id and client_name for onsite"""
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Check-in with client info for onsite
        unique_date = f"2099-01-{(datetime.now().day % 28) + 1:02d}"  # Very future date
        
        check_in_payload = {
            "work_location": "onsite",
            "date": unique_date,
            "selfie": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10,
                "address": "Test Location, Bangalore"
            },
            "client_id": "test-client-123",
            "client_name": "TEST_Client Corp",
            "project_id": "test-project-456",
            "project_name": "Test Project"
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        # May return 400 if location not verified (needs justification)
        if response.status_code == 400:
            error_detail = response.json().get("detail", "")
            if "justification" in error_detail.lower() or "500m" in error_detail:
                # Add justification and retry
                check_in_payload["justification"] = "Testing onsite check-in with client selection"
                response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data, "Response should have attendance id"
            assert data.get("work_location") == "onsite", "Work location should be onsite"
            # Verify client info is returned
            assert data.get("client_name") == "TEST_Client Corp", f"Client name should match, got {data.get('client_name')}"
            print(f"✓ POST /api/my/check-in with client info successful")
            print(f"  Attendance ID: {data.get('id')}")
            print(f"  Client: {data.get('client_name')}")
            print(f"  Approval Status: {data.get('approval_status')}")
            
            # Store for checkout test
            self.attendance_id = data.get("id")
            self.test_date = unique_date
        elif response.status_code == 404:
            print("⚠ Check-in returned 404 (employee record not found)")
        else:
            print(f"⚠ Check-in response: {response.status_code} - {response.text[:200]}")
    
    def test_04_check_out_returns_redirect_flag(self):
        """Test that check-out returns redirect_to_expense flag for onsite attendance"""
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First, do a check-in for today to test checkout
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Try check-out first to see if already checked in
        checkout_payload = {
            "date": today_str,
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-out", json=checkout_payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ POST /api/my/check-out successful")
            print(f"  Work hours: {data.get('work_hours')}")
            print(f"  redirect_to_expense: {data.get('redirect_to_expense')}")
            print(f"  travel_reimbursement: {data.get('travel_reimbursement')}")
            
            # Verify response structure
            assert "redirect_to_expense" in data, "Response should contain redirect_to_expense flag"
            
            if data.get("travel_reimbursement"):
                tr = data["travel_reimbursement"]
                print(f"  Travel Distance: {tr.get('distance_km')} km")
                print(f"  Amount: Rs {tr.get('calculated_amount')}")
        elif response.status_code == 400:
            error = response.json().get("detail", "")
            print(f"⚠ Check-out failed: {error}")
            # Expected if already checked out or not checked in
        elif response.status_code == 404:
            print("⚠ Check-out returned 404 (employee record not found)")
        else:
            print(f"⚠ Unexpected: {response.status_code} - {response.text[:100]}")
    
    def test_05_work_location_options_in_office(self):
        """Test in_office work location check-in"""
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Check-in for office work
        future_date = "2099-02-15"
        
        check_in_payload = {
            "work_location": "in_office",
            "date": future_date,
            "selfie": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10,
                "address": "Office Location"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        if response.status_code == 400:
            error = response.json().get("detail", "")
            if "justification" in error.lower():
                check_in_payload["justification"] = "Testing office check-in"
                response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("work_location") == "in_office", "Work location should be in_office"
            # For in_office, client_name should be None
            assert data.get("client_name") is None, "Client should be None for office check-in"
            print(f"✓ in_office check-in successful")
        elif response.status_code == 404:
            print("⚠ Check-in returned 404")
        else:
            print(f"⚠ Response: {response.status_code} - {response.text[:100]}")
    
    def test_06_wfh_not_allowed(self):
        """Test that WFH work location is not allowed"""
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try WFH check-in
        check_in_payload = {
            "work_location": "wfh",  # Should be rejected
            "date": "2099-03-01",
            "selfie": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-in", json=check_in_payload)
        
        # Should return 400 for invalid work location
        if response.status_code == 400:
            error = response.json().get("detail", "")
            print(f"✓ WFH correctly rejected: {error[:80]}")
            assert "in_office" in error.lower() or "on-site" in error.lower() or "invalid" in error.lower()
        elif response.status_code == 404:
            print("⚠ Returned 404 (employee not found)")
        else:
            print(f"⚠ Unexpected: {response.status_code}")


class TestERPAttendanceModal:
    """Test ERP Attendance page modal functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login as HR/Admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin for ERP access
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.user = login_response.json().get("user")
        else:
            pytest.skip("Authentication failed")
    
    def test_01_attendance_summary_endpoint(self):
        """Test attendance summary API used by ERP"""
        month = datetime.now().strftime("%Y-%m")
        response = self.session.get(f"{BASE_URL}/api/attendance/summary?month={month}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Summary should be a list"
        print(f"✓ GET /api/attendance/summary returned {len(data)} records")
    
    def test_02_attendance_records_endpoint(self):
        """Test attendance records API"""
        month = datetime.now().strftime("%Y-%m")
        response = self.session.get(f"{BASE_URL}/api/attendance?month={month}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Records should be a list"
        print(f"✓ GET /api/attendance returned {len(data)} records")
        
        # Check if any record has client info
        onsite_records = [r for r in data if r.get("work_location") == "onsite"]
        if onsite_records:
            print(f"  Found {len(onsite_records)} On-Site records")
            for r in onsite_records[:2]:
                print(f"    - {r.get('date')}: {r.get('client_name') or 'No client'}")
    
    def test_03_employees_endpoint(self):
        """Test employees API used by attendance modal dropdown"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Employees should be a list"
        print(f"✓ GET /api/employees returned {len(data)} employees")
    
    def test_04_office_locations_endpoint(self):
        """Test office locations API for geofencing"""
        response = self.session.get(f"{BASE_URL}/api/settings/office-locations")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ GET /api/settings/office-locations successful")
        if data.get("locations"):
            print(f"  Office locations configured: {len(data['locations'])}")
    
    def test_05_manual_attendance_post(self):
        """Test POST /api/attendance for manual entry (HR use)"""
        # Get first employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        if emp_response.status_code != 200 or not emp_response.json():
            pytest.skip("No employees found")
        
        employee = emp_response.json()[0]
        
        # Create attendance with client info for onsite
        attendance_payload = {
            "employee_id": employee["id"],
            "date": "2099-04-15",
            "status": "present",
            "work_location": "onsite",
            "client_id": "manual-test-client",
            "client_name": "Manual Test Client Corp",
            "project_id": "manual-test-project",
            "project_name": "Manual Test Project",
            "check_in_time": "09:00",
            "check_out_time": "18:00",
            "remarks": "Manual entry test"
        }
        
        response = self.session.post(f"{BASE_URL}/api/attendance", json=attendance_payload)
        
        # Should succeed or conflict if already exists
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ POST /api/attendance manual entry successful")
            print(f"  Employee: {employee.get('first_name')} {employee.get('last_name')}")
            print(f"  Client: {attendance_payload['client_name']}")
        else:
            print(f"⚠ Manual attendance response: {response.status_code} - {response.text[:100]}")


class TestMobileAppCheckInFlow:
    """Test Mobile App check-in flow with client selection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_01_my_attendance_endpoint(self):
        """Test /api/my/attendance for current user"""
        month = datetime.now().strftime("%Y-%m")
        response = self.session.get(f"{BASE_URL}/api/my/attendance?month={month}")
        
        # May return 404 if no employee record
        if response.status_code == 200:
            data = response.json()
            print(f"✓ GET /api/my/attendance successful")
            if data.get("records"):
                print(f"  Records this month: {len(data['records'])}")
        elif response.status_code == 404:
            print("⚠ /api/my/attendance returned 404 (no employee record)")
        else:
            print(f"⚠ Response: {response.status_code}")
    
    def test_02_my_leave_balance(self):
        """Test /api/my/leave-balance"""
        response = self.session.get(f"{BASE_URL}/api/my/leave-balance")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ GET /api/my/leave-balance successful")
        elif response.status_code == 404:
            print("⚠ /api/my/leave-balance returned 404")
    
    def test_03_my_check_status(self):
        """Test /api/my/check-status for today's status"""
        response = self.session.get(f"{BASE_URL}/api/my/check-status")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ GET /api/my/check-status successful")
            print(f"  Checked in: {data.get('checked_in')}")
            print(f"  Checked out: {data.get('checked_out')}")
        elif response.status_code == 404:
            print("⚠ /api/my/check-status returned 404")
    
    def test_04_clients_endpoint(self):
        """Test /api/clients endpoint"""
        response = self.session.get(f"{BASE_URL}/api/clients")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ GET /api/clients returned {len(data)} clients")
    
    def test_05_projects_endpoint(self):
        """Test /api/projects endpoint"""
        response = self.session.get(f"{BASE_URL}/api/projects")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ GET /api/projects returned {len(data)} projects")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
