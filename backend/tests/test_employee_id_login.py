"""
Test suite for Employee ID Login System
Tests:
1. Login with Employee ID and password
2. Legacy email login still works
3. Admin password reset for employees
4. Toggle employee access (enable/disable)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from the context
ADMIN_EMPLOYEE_ID = "ADMIN001"
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"

HR_EMPLOYEE_ID = "HR001"
HR_PASSWORD = "hr123"


class TestEmployeeIDLogin:
    """Test Employee ID login functionality"""

    def test_login_with_employee_id(self):
        """Test login using Employee ID (ADMIN001)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": ADMIN_EMPLOYEE_ID,
            "password": ADMIN_PASSWORD
        })
        print(f"Employee ID Login Response: {response.status_code} - {response.text[:200]}")
        
        # Employee ID login should work
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "access_token missing from response"
        assert "user" in data, "user missing from response"
        assert data["token_type"] == "bearer"
        print(f"Login successful for Employee ID: {ADMIN_EMPLOYEE_ID}")

    def test_login_with_email_backward_compatible(self):
        """Test legacy email login still works (admin@dvbc.com)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        print(f"Email Login Response: {response.status_code} - {response.text[:200]}")
        
        # Email login should still work for backward compatibility
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "access_token missing from response"
        assert "user" in data, "user missing from response"
        print(f"Email login successful for: {ADMIN_EMAIL}")

    def test_login_without_credentials_fails(self):
        """Test login without employee_id or email fails"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "password": ADMIN_PASSWORD
        })
        print(f"No ID/Email Login Response: {response.status_code} - {response.text[:200]}")
        
        # Should fail with 400 or 422
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"

    def test_login_invalid_employee_id(self):
        """Test login with invalid employee ID fails"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "INVALID999",
            "password": "wrongpassword"
        })
        print(f"Invalid Employee ID Login Response: {response.status_code}")
        
        # Should fail with 401
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_login_wrong_password(self):
        """Test login with wrong password fails"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": ADMIN_EMPLOYEE_ID,
            "password": "wrongpassword"
        })
        print(f"Wrong Password Login Response: {response.status_code}")
        
        # Should fail with 401
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAdminPasswordManagement:
    """Test Admin/HR password management endpoints"""

    @pytest.fixture
    def admin_token(self):
        """Get admin access token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")

    def test_reset_employee_password_endpoint_exists(self, admin_token):
        """Test POST /api/auth/admin/reset-employee-password endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with a non-existent employee to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/auth/admin/reset-employee-password",
            json={
                "employee_id": "NONEXISTENT999",
                "new_password": "NewPass@123"
            },
            headers=headers
        )
        print(f"Reset Password Response: {response.status_code} - {response.text[:200]}")
        
        # Should return 404 (employee not found), not 404 (endpoint not found) or 405
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        assert "Employee not found" in response.text or "not found" in response.text.lower()
        print("Reset password endpoint works correctly")

    def test_toggle_employee_access_endpoint_exists(self, admin_token):
        """Test POST /api/auth/admin/toggle-employee-access endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with a non-existent employee to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/auth/admin/toggle-employee-access",
            json={
                "employee_id": "NONEXISTENT999",
                "is_active": False
            },
            headers=headers
        )
        print(f"Toggle Access Response: {response.status_code} - {response.text[:200]}")
        
        # Should return 404 (employee not found), not 405 or wrong endpoint
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        assert "Employee not found" in response.text or "not found" in response.text.lower()
        print("Toggle access endpoint works correctly")

    def test_reset_password_requires_auth(self):
        """Test reset password endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/auth/admin/reset-employee-password",
            json={
                "employee_id": "EMP001",
                "new_password": "NewPass@123"
            }
        )
        print(f"Unauthenticated Reset Response: {response.status_code}")
        
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_toggle_access_requires_auth(self):
        """Test toggle access endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/auth/admin/toggle-employee-access",
            json={
                "employee_id": "EMP001",
                "is_active": False
            }
        )
        print(f"Unauthenticated Toggle Response: {response.status_code}")
        
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestLoginPageFields:
    """Test login page field names and input types"""

    def test_login_accepts_employee_id_field(self):
        """Test that login accepts employee_id field"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        print(f"Employee ID field test: {response.status_code}")
        
        # Should accept employee_id field
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
        if response.status_code == 401:
            # Check it's auth failure, not validation failure
            data = response.json()
            assert "Invalid" in data.get("detail", "") or "not found" in data.get("detail", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
