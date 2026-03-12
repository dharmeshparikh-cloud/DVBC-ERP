"""
Portal Access Management API Tests
Testing: Generate Portal Access & Reset Password endpoints for Go-Live Dashboard
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def admin_session():
    """Get authenticated admin session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as admin
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "ADMIN001",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")

@pytest.fixture(scope="module")
def hr_manager_session():
    """Get authenticated HR Manager session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as HR Manager
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "DVC037",
        "password": "test123"
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    pytest.skip(f"HR Manager login failed: {response.status_code} - {response.text}")


class TestPortalAccessManagementEndpoints:
    """Test Portal Access Management API endpoints"""

    def test_admin_login_success(self, admin_session):
        """Verify admin can authenticate"""
        assert admin_session is not None
        print("PASS: Admin authentication successful")

    def test_hr_manager_login_success(self, hr_manager_session):
        """Verify HR Manager can authenticate"""
        assert hr_manager_session is not None
        print("PASS: HR Manager authentication successful")
    
    def test_get_employees_list(self, admin_session):
        """Get list of employees to find test data"""
        response = admin_session.get(f"{BASE_URL}/api/employees?page_size=50")
        assert response.status_code == 200
        data = response.json()
        
        employees = data.get("items") or data
        assert isinstance(employees, list)
        assert len(employees) > 0
        print(f"PASS: Found {len(employees)} employees")
        return employees

    def test_lookup_employee_dvbc004(self, admin_session):
        """Lookup employee DVBC004 which should have user_id"""
        response = admin_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("employee_id") == "DVBC004"
        print(f"PASS: Found DVBC004 - user_id: {data.get('user_id')}, go_live_status: {data.get('go_live_status')}")
        return data


class TestGeneratePortalAccess:
    """Test POST /api/go-live/generate-portal-access/{employee_id}"""
    
    def test_generate_portal_access_not_found(self, admin_session):
        """Test with non-existent employee returns 404"""
        fake_id = str(uuid.uuid4())
        response = admin_session.post(f"{BASE_URL}/api/go-live/generate-portal-access/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
        print("PASS: Returns 404 for non-existent employee")
    
    def test_generate_portal_access_employee_already_has_access(self, admin_session):
        """Test with employee that already has user_id returns 400"""
        # DVBC004 already has user_id based on backend logs
        response = admin_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        if response.status_code != 200:
            pytest.skip("DVBC004 not found")
        
        employee = response.json()
        employee_uuid = employee.get("id")
        
        if employee.get("user_id"):
            response = admin_session.post(f"{BASE_URL}/api/go-live/generate-portal-access/{employee_uuid}")
            # Should return 400 if user already exists
            assert response.status_code == 400
            assert "already exists" in response.json().get("detail", "").lower() or "reset password" in response.json().get("detail", "").lower()
            print("PASS: Returns 400 for employee with existing portal access")
        else:
            pytest.skip("DVBC004 does not have user_id, cannot test this scenario")
    
    def test_generate_portal_access_authorization_required(self):
        """Test that unauthenticated request returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/go-live/generate-portal-access/test123")
        # Should require authentication
        assert response.status_code in [401, 403, 422]
        print("PASS: Authorization required for generate-portal-access")


class TestResetPassword:
    """Test POST /api/go-live/reset-password/{employee_id}"""
    
    def test_reset_password_not_found(self, admin_session):
        """Test with non-existent employee returns 404"""
        fake_id = str(uuid.uuid4())
        response = admin_session.post(f"{BASE_URL}/api/go-live/reset-password/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
        print("PASS: Returns 404 for non-existent employee")
    
    def test_reset_password_employee_without_portal_access(self, admin_session):
        """Test resetting password for employee without user account returns 400"""
        # Find an employee without user_id
        response = admin_session.get(f"{BASE_URL}/api/employees?page_size=100")
        if response.status_code != 200:
            pytest.skip("Cannot fetch employees")
        
        employees = response.json().get("items") or response.json()
        employee_without_user = None
        for emp in employees:
            if not emp.get("user_id"):
                employee_without_user = emp
                break
        
        if employee_without_user:
            response = admin_session.post(f"{BASE_URL}/api/go-live/reset-password/{employee_without_user['id']}")
            assert response.status_code == 400
            assert "no portal access" in response.json().get("detail", "").lower() or "generate portal access" in response.json().get("detail", "").lower()
            print(f"PASS: Returns 400 for employee without portal access (tested: {employee_without_user.get('employee_id')})")
        else:
            pytest.skip("No employee without user_id found to test")
    
    def test_reset_password_success(self, admin_session):
        """Test successful password reset for employee with user account"""
        # DVBC004 has user_id
        response = admin_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        if response.status_code != 200:
            pytest.skip("DVBC004 not found")
        
        employee = response.json()
        if not employee.get("user_id"):
            pytest.skip("DVBC004 does not have user_id")
        
        employee_uuid = employee.get("id")
        response = admin_session.post(f"{BASE_URL}/api/go-live/reset-password/{employee_uuid}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "password reset" in data["message"].lower()
        assert "employee_id" in data
        assert "temp_password" in data
        assert len(data["temp_password"]) >= 8  # Should be a secure password
        
        print(f"PASS: Password reset successful - employee_id: {data['employee_id']}, password generated: {len(data['temp_password'])} chars")
        return data
    
    def test_reset_password_by_hr_manager(self, hr_manager_session):
        """Test HR Manager can also reset password"""
        response = hr_manager_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        if response.status_code != 200:
            pytest.skip("DVBC004 not found")
        
        employee = response.json()
        if not employee.get("user_id"):
            pytest.skip("DVBC004 does not have user_id")
        
        employee_uuid = employee.get("id")
        response = hr_manager_session.post(f"{BASE_URL}/api/go-live/reset-password/{employee_uuid}")
        
        assert response.status_code == 200
        data = response.json()
        assert "temp_password" in data
        print("PASS: HR Manager can reset password")
    
    def test_reset_password_authorization_required(self):
        """Test that unauthenticated request returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/go-live/reset-password/test123")
        assert response.status_code in [401, 403, 422]
        print("PASS: Authorization required for reset-password")


class TestGoLiveChecklistUpdates:
    """Test that portal_access checklist item reflects user_id status"""
    
    def test_checklist_shows_portal_access_status(self, admin_session):
        """Verify Go-Live checklist shows portal_access status correctly"""
        # Get DVBC004 employee ID
        response = admin_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        if response.status_code != 200:
            pytest.skip("DVBC004 not found")
        
        employee = response.json()
        employee_uuid = employee.get("id")
        
        # Get Go-Live checklist
        response = admin_session.get(f"{BASE_URL}/api/go-live/checklist/{employee_uuid}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify checklist structure
        assert "checklist" in data
        assert "portal_access" in data["checklist"]
        
        portal_access = data["checklist"]["portal_access"]
        assert "completed" in portal_access
        assert "label" in portal_access
        
        # If employee has user_id, portal_access should be completed
        if employee.get("user_id"):
            assert portal_access["completed"] == True
            print("PASS: Checklist shows portal_access completed for employee with user_id")
        else:
            assert portal_access["completed"] == False
            print("PASS: Checklist shows portal_access NOT completed for employee without user_id")


class TestResponseStructure:
    """Verify API response structures match frontend expectations"""
    
    def test_reset_password_response_structure(self, admin_session):
        """Verify reset-password returns expected fields for frontend"""
        response = admin_session.get(f"{BASE_URL}/api/employees/lookup/by-code/DVBC004")
        if response.status_code != 200:
            pytest.skip("DVBC004 not found")
        
        employee = response.json()
        if not employee.get("user_id"):
            pytest.skip("DVBC004 does not have user_id")
        
        response = admin_session.post(f"{BASE_URL}/api/go-live/reset-password/{employee['id']}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Frontend expects these fields for the credentials dialog
        required_fields = ["message", "employee_id", "employee_name", "temp_password"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"PASS: Response contains all required fields: {required_fields}")


class TestPortalAccessForActiveEmployees:
    """Test portal access generation for active employees without user accounts"""
    
    def test_find_active_employee_without_user(self, admin_session):
        """Find an active employee without user_id for testing"""
        response = admin_session.get(f"{BASE_URL}/api/employees?page_size=100")
        if response.status_code != 200:
            pytest.skip("Cannot fetch employees")
        
        employees = response.json().get("items") or response.json()
        
        active_without_user = None
        for emp in employees:
            if emp.get("go_live_status") == "active" and not emp.get("user_id"):
                active_without_user = emp
                break
        
        if active_without_user:
            print(f"Found active employee without user: {active_without_user.get('employee_id')} - {active_without_user.get('first_name')} {active_without_user.get('last_name')}")
        else:
            print("INFO: No active employees without user_id found - all active employees have portal access")
        
        return active_without_user


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
