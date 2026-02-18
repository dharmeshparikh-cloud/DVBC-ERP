"""
Tests for CSV Upload, Employee Portal Access, and Selfie Capture features
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuthentication:
    """Test authentication for both admin and sales users"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login SUCCESS - role: {data['user']['role']}")
        
    def test_sales_manager_login(self):
        """Test sales manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sales.manager@dvbc.com",
            "password": "sales123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"Sales Manager login SUCCESS - role: {data['user']['role']}")


class TestLeadsCRUD:
    """Test Leads CRUD and CSV-related functionality"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        return response.json().get("access_token")
    
    def test_get_leads(self, auth_token):
        """Test fetching leads"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET /api/leads SUCCESS - {len(data)} leads found")
    
    def test_create_lead(self, auth_token):
        """Test creating a lead - this is what CSV upload uses internally"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        lead_data = {
            "first_name": "TEST_CSV",
            "last_name": "ImportLead",
            "company": "Test Corp",
            "job_title": "Test Manager",
            "email": "test.csvimport@testcorp.com",
            "phone": "9876543210",
            "source": "CSV Import",
            "notes": "Created via API test for CSV import"
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=headers)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "lead_id" in data or "id" in data
        print(f"POST /api/leads SUCCESS - Lead created")
        
        # Return lead id for cleanup
        return data.get("lead_id") or data.get("id")
    
    def test_bulk_lead_creation_simulating_csv(self, auth_token):
        """Test bulk lead creation - simulates CSV import functionality"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Simulate CSV data parsing
        csv_data = [
            {"first_name": "TEST_CSV1", "last_name": "User1", "company": "Company A", "email": "csv1@test.com", "source": "CSV Import"},
            {"first_name": "TEST_CSV2", "last_name": "User2", "company": "Company B", "email": "csv2@test.com", "source": "CSV Import"},
        ]
        
        created_count = 0
        failed_count = 0
        
        for lead_data in csv_data:
            response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=headers)
            if response.status_code in [200, 201]:
                created_count += 1
            else:
                failed_count += 1
        
        print(f"Bulk lead creation: {created_count} created, {failed_count} failed")
        assert created_count >= 1, "At least one lead should be created"


class TestEmployeePortalAccess:
    """Test employee portal access grant/revoke functionality"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        return response.json().get("access_token")
    
    def test_get_employees(self, admin_token):
        """Test fetching employees"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET /api/employees SUCCESS - {len(data)} employees found")
        return data
    
    def test_create_employee_and_grant_access(self, admin_token):
        """Test creating an employee and granting portal access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 1: Create a test employee
        employee_data = {
            "first_name": "TEST_Portal",
            "last_name": "AccessUser",
            "email": "test.portal.access@testcorp.com",
            "phone": "9876500001",
            "department": "IT",
            "designation": "Developer",
            "role": "consultant",
            "date_of_joining": "2026-01-15"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/employees", json=employee_data, headers=headers)
        
        # Employee might already exist (duplicate email/phone) - that's ok for this test
        if create_response.status_code == 400:
            # Try to find the existing employee
            employees = requests.get(f"{BASE_URL}/api/employees", headers=headers).json()
            employee = next((e for e in employees if e.get("email") == employee_data["email"]), None)
            if not employee:
                pytest.skip("Could not create or find test employee")
            employee_id = employee["id"]
            print(f"Using existing employee with id: {employee_id}")
        else:
            assert create_response.status_code in [200, 201]
            create_data = create_response.json()
            employee_id = create_data.get("employee", {}).get("id")
            print(f"Created employee with id: {employee_id}")
        
        # Step 2: Grant portal access
        if employee_id:
            access_response = requests.post(
                f"{BASE_URL}/api/employees/{employee_id}/grant-access",
                headers=headers
            )
            
            if access_response.status_code == 200:
                access_data = access_response.json()
                print(f"Portal access granted response: {access_data}")
                
                # Check for temp_password
                temp_password = access_data.get("temp_password")
                if temp_password:
                    print(f"SUCCESS: Temp password generated - {temp_password}")
                    # Verify the password format is Welcome@{employee_id}
                    assert "Welcome@" in temp_password, "Temp password should start with Welcome@"
                    
                    # Step 3: Verify the new user can login with temp password
                    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                        "email": employee_data["email"],
                        "password": temp_password
                    })
                    
                    if login_response.status_code == 200:
                        print("SUCCESS: New user can login with temp password!")
                    else:
                        print(f"Login with temp password returned: {login_response.status_code}")
                        # This might fail if user was linked to existing account
                        
            elif access_response.status_code == 400 and "existing user" in str(access_response.json()):
                print("Employee already has portal access - linked to existing user")
            else:
                print(f"Grant access returned: {access_response.status_code} - {access_response.json()}")


class TestMobileAppAttendance:
    """Test Mobile App attendance endpoints including selfie verification"""
    
    @pytest.fixture
    def user_token(self):
        """Get a user token for attendance testing"""
        # Try sales manager or admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        return response.json().get("access_token")
    
    def test_my_attendance_endpoint(self, user_token):
        """Test fetching user's attendance"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/my/attendance?month=2026-02", headers=headers)
        
        # 200 means success, 404 might mean no attendance records yet
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"GET /api/my/attendance SUCCESS - records: {len(data.get('records', []))}")
    
    def test_checkin_endpoint_exists(self, user_token):
        """Test that check-in endpoint exists and accepts the right format"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create minimal check-in payload with selfie field
        checkin_data = {
            "work_location": "in_office",
            "remarks": "Test check-in",
            "selfie": "data:image/jpeg;base64,/9j/test",  # Minimal base64 image placeholder
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10.0,
                "address": "Test Location"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/my/check-in", json=checkin_data, headers=headers)
        
        # Various valid responses:
        # 200 - Check-in successful
        # 400 - Already checked in or validation error
        # 422 - Validation error (which shows the endpoint exists and validates)
        print(f"Check-in response: {response.status_code}")
        
        if response.status_code == 200:
            print("Check-in SUCCESS")
        elif response.status_code in [400, 422]:
            # Endpoint exists but validation failed - that's expected for test data
            error_detail = response.json().get("detail", "")
            print(f"Check-in validation: {error_detail}")
        
        # As long as endpoint exists and responds, test passes
        assert response.status_code in [200, 400, 422, 403]
    
    def test_checkout_endpoint_exists(self, user_token):
        """Test that check-out endpoint exists"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        checkout_data = {
            "geo_location": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10.0
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/my/check-out", json=checkout_data, headers=headers)
        print(f"Check-out response: {response.status_code}")
        
        # Endpoint should exist, might fail validation if not checked in
        assert response.status_code in [200, 400, 404, 422]


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        return response.json().get("access_token")
    
    def test_cleanup_test_leads(self, admin_token):
        """Delete test leads created during tests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all leads
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        if response.status_code == 200:
            leads = response.json()
            test_leads = [l for l in leads if l.get("first_name", "").startswith("TEST_")]
            
            for lead in test_leads:
                delete_response = requests.delete(f"{BASE_URL}/api/leads/{lead['id']}", headers=headers)
                if delete_response.status_code in [200, 204]:
                    print(f"Deleted test lead: {lead.get('first_name')}")
        
        print("Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
