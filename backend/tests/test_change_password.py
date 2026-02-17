"""
Test suite for Change Password feature
Tests the /api/auth/change-password endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERS = {
    "admin": {"email": "admin@dvbc.com", "password": "admin123"},
    "hr_manager": {"email": "hr.manager@dvbc.com", "password": "hr123"},
    "sales_manager": {"email": "sales.manager@dvbc.com", "password": "sales123"}
}


@pytest.fixture
def get_token():
    """Helper to get auth token for a user"""
    def _get_token(user_key):
        user = TEST_USERS.get(user_key)
        if not user:
            pytest.skip(f"User {user_key} not found in test credentials")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed for {user_key}")
        return response.json().get("access_token")
    return _get_token


class TestChangePasswordAPI:
    """Tests for /api/auth/change-password endpoint"""
    
    def test_change_password_without_auth(self):
        """Test that change password requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "test", "new_password": "newtest"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401
        print("PASS: Change password requires authentication")
    
    def test_change_password_wrong_current(self, get_token):
        """Test change password with wrong current password"""
        token = get_token("admin")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "wrongpassword", "new_password": "newpass123"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Current password is incorrect" in data.get("detail", "")
        print("PASS: Wrong current password returns correct error")
    
    def test_change_password_too_short(self, get_token):
        """Test change password with new password too short"""
        token = get_token("admin")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "abc"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "at least 6 characters" in data.get("detail", "")
        print("PASS: Short password validation working")
    
    def test_change_password_missing_fields(self, get_token):
        """Test change password with missing fields"""
        token = get_token("admin")
        
        # Missing new_password
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "admin123"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        assert response.status_code == 422  # Validation error
        print("PASS: Missing fields validation working")
    
    def test_change_password_success_flow(self, get_token):
        """Test full change password flow - change and change back"""
        # Get token with original password
        admin = TEST_USERS["admin"]
        
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": admin["email"], "password": admin["password"]},
            headers={"Content-Type": "application/json"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        
        # Change to new password
        new_password = "admin123temp"
        change_resp = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": admin["password"], "new_password": new_password},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        assert change_resp.status_code == 200
        data = change_resp.json()
        assert data.get("message") == "Password changed successfully"
        print("PASS: Password changed successfully")
        
        # Verify old password no longer works
        old_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": admin["email"], "password": admin["password"]},
            headers={"Content-Type": "application/json"}
        )
        assert old_login.status_code == 401
        print("PASS: Old password no longer works")
        
        # Verify new password works
        new_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": admin["email"], "password": new_password},
            headers={"Content-Type": "application/json"}
        )
        assert new_login.status_code == 200
        new_token = new_login.json().get("access_token")
        print("PASS: New password works")
        
        # Change back to original password
        revert_resp = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": new_password, "new_password": admin["password"]},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {new_token}"
            }
        )
        
        assert revert_resp.status_code == 200
        print("PASS: Password reverted to original")
        
        # Verify original password works again
        final_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": admin["email"], "password": admin["password"]},
            headers={"Content-Type": "application/json"}
        )
        assert final_login.status_code == 200
        print("PASS: Original password works again - Full flow verified")


class TestChangePasswordForDifferentRoles:
    """Test change password works for different user roles"""
    
    def test_hr_manager_can_change_password(self, get_token):
        """Test HR Manager can use change password"""
        token = get_token("hr_manager")
        
        # Just test that the endpoint is accessible with correct auth
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "newpass123"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        # Should get 400 (wrong password) not 403 (forbidden)
        assert response.status_code == 400
        print("PASS: HR Manager can access change password endpoint")
    
    def test_sales_manager_can_change_password(self, get_token):
        """Test Sales Manager can use change password"""
        token = get_token("sales_manager")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "newpass123"},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        # Should get 400 (wrong password) not 403 (forbidden)
        assert response.status_code == 400
        print("PASS: Sales Manager can access change password endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
