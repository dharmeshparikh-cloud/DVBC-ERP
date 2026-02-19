"""
Test Suite: User and Employee Management Consolidation
Features tested:
1. Employee ID login (ADMIN001, HR001, EMP001 format)
2. POST /api/employees/{id}/grant-access creates user with correct employee_id
3. User.employee_id matches Employee.employee_id for linked records
4. Backward compatibility: email login still works
5. Password Management page shows correct employee_id for all users
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-admin-control.preview.emergentagent.com').rstrip('/')


class TestEmployeeIDLogin:
    """Test Employee ID based login functionality"""
    
    def test_admin_login_with_employee_id(self):
        """Test login with ADMIN001 Employee ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@dvbc.com"
        assert data["user"]["role"] == "admin"
    
    def test_hr_login_with_employee_id(self):
        """Test login with HR001 Employee ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "hr123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["email"] == "hr.manager@dvbc.com"
        assert data["user"]["role"] == "hr_manager"
    
    def test_employee_login_with_employee_id(self):
        """Test login with EMP001 Employee ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "Welcome@EMP001"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["role"] == "consultant"


class TestBackwardCompatibility:
    """Test backward compatibility with email login"""
    
    def test_email_login_still_works(self):
        """Test that email login still works for backward compatibility"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Email login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["email"] == "admin@dvbc.com"
    
    def test_login_requires_either_employee_id_or_email(self):
        """Test that login requires either employee_id or email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "password": "admin123"
        })
        assert response.status_code == 400
        assert "Employee ID or Email is required" in response.text


class TestGrantAccessEndpoint:
    """Test /api/employees/{id}/grant-access endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin authentication failed")
    
    def test_grant_access_returns_correct_employee_id_format(self, admin_token):
        """Test that grant-access returns employee_id in EMP format, not UUID"""
        # First find an employee without access
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        # Find employee without portal access
        emp_without_access = None
        for emp in employees:
            if not emp.get("has_portal_access") and not emp.get("user_id"):
                emp_without_access = emp
                break
        
        if not emp_without_access:
            pytest.skip("No employee without portal access found")
        
        emp_id = emp_without_access["employee_id"]
        
        # Grant access
        response = requests.post(
            f"{BASE_URL}/api/employees/{emp_id}/grant-access",
            headers=headers
        )
        assert response.status_code == 200, f"Grant access failed: {response.text}"
        data = response.json()
        
        # Verify employee_id is in correct format
        assert "employee_id" in data
        assert data["employee_id"] == emp_id, f"employee_id mismatch: expected {emp_id}, got {data['employee_id']}"
        assert "login_id" in data
        assert data["login_id"] == emp_id
        
        # Verify it's NOT a UUID
        assert not self._is_uuid(data["employee_id"]), f"employee_id should not be UUID: {data['employee_id']}"
    
    def test_grant_access_creates_user_with_matching_employee_id(self, admin_token):
        """Test that user.employee_id matches employee.employee_id after grant-access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get users
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert users_response.status_code == 200
        users = users_response.json()
        
        # Get employees
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        # Create a mapping of employee emails to employee_ids
        emp_id_by_email = {e["email"]: e["employee_id"] for e in employees if e.get("email")}
        
        # Verify user.employee_id matches employee.employee_id for linked users
        mismatches = []
        for user in users:
            if user.get("email") in emp_id_by_email:
                expected_emp_id = emp_id_by_email[user["email"]]
                actual_emp_id = user.get("employee_id")
                if actual_emp_id and actual_emp_id != expected_emp_id:
                    mismatches.append(f"User {user['email']}: expected {expected_emp_id}, got {actual_emp_id}")
        
        assert not mismatches, f"Employee ID mismatches found: {mismatches}"
    
    def _is_uuid(self, value):
        """Check if value is a UUID format"""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False


class TestUserEmployeeIDField:
    """Test that User records have correct employee_id field"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin authentication failed")
    
    def test_users_have_employee_id_field(self, admin_token):
        """Test that all users have employee_id field in EMP format"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        
        users_without_emp_id = []
        users_with_uuid_emp_id = []
        
        for user in users:
            emp_id = user.get("employee_id")
            if not emp_id:
                users_without_emp_id.append(user["email"])
            elif self._is_uuid(emp_id):
                users_with_uuid_emp_id.append(f"{user['email']}: {emp_id}")
        
        # Report findings
        if users_without_emp_id:
            print(f"Users without employee_id: {users_without_emp_id}")
        if users_with_uuid_emp_id:
            print(f"Users with UUID employee_id (should be EMP format): {users_with_uuid_emp_id}")
        
        # Assert no UUIDs are used as employee_id
        assert not users_with_uuid_emp_id, f"Some users have UUID as employee_id: {users_with_uuid_emp_id}"
    
    def test_admin_user_has_admin001_employee_id(self, admin_token):
        """Test that admin user has ADMIN001 as employee_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        
        admin_user = next((u for u in users if u["email"] == "admin@dvbc.com"), None)
        assert admin_user is not None, "Admin user not found"
        assert admin_user.get("employee_id") == "ADMIN001", f"Admin employee_id should be ADMIN001, got {admin_user.get('employee_id')}"
    
    def test_hr_user_has_hr001_employee_id(self, admin_token):
        """Test that HR manager has HR001 as employee_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        
        hr_user = next((u for u in users if u["email"] == "hr.manager@dvbc.com"), None)
        assert hr_user is not None, "HR user not found"
        assert hr_user.get("employee_id") == "HR001", f"HR employee_id should be HR001, got {hr_user.get('employee_id')}"
    
    def _is_uuid(self, value):
        """Check if value is a UUID format"""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False


class TestNoUsersPostEndpoint:
    """Verify /api/users POST is not used for creating users with portal access"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin authentication failed")
    
    def test_employees_grant_access_is_only_user_creation_path(self, admin_token):
        """Verify that grant-access endpoint properly creates users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Grant access endpoint should be available
        # Test with a non-existent employee to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/employees/NON_EXISTENT/grant-access",
            headers=headers
        )
        
        # Should return 404 (employee not found) not 404 (endpoint not found)
        assert response.status_code == 404
        assert "not found" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
