"""
Tests for Guided Sales Workflow feature
- Login for sales executive and admin users
- Role-based access verification
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGuidedSalesWorkflowAuth:
    """Authentication tests for guided sales workflow users"""
    
    def test_sales_executive_login_success(self):
        """Test sales@dvbc.com with password sales123 can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "sales@dvbc.com", "password": "sales123"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        
        user = data["user"]
        assert user["email"] == "sales@dvbc.com", "Email should match"
        assert user["role"] == "executive", f"Role should be 'executive', got {user['role']}"
        assert user["is_active"] == True, "User should be active"
        print(f"SUCCESS: Sales executive login works. User: {user['full_name']}, Role: {user['role']}")
    
    def test_admin_login_success(self):
        """Test admin@dvbc.com with password admin123 can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        
        user = data["user"]
        assert user["email"] == "admin@dvbc.com", "Email should match"
        assert user["role"] == "admin", f"Role should be 'admin', got {user['role']}"
        assert user["is_active"] == True, "User should be active"
        print(f"SUCCESS: Admin login works. User: {user['full_name']}, Role: {user['role']}")
    
    def test_sales_executive_invalid_password(self):
        """Test sales executive with wrong password fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "sales@dvbc.com", "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 for wrong password, got {response.status_code}"
        print("SUCCESS: Invalid password correctly rejected")
    
    def test_admin_invalid_password(self):
        """Test admin with wrong password fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 for wrong password, got {response.status_code}"
        print("SUCCESS: Invalid admin password correctly rejected")


class TestGuidedSalesWorkflowRoles:
    """Verify role-based behavior after login"""
    
    @pytest.fixture
    def sales_token(self):
        """Get sales executive auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "sales@dvbc.com", "password": "sales123"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Sales executive login failed")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_sales_executive_role_is_executive(self, sales_token):
        """Verify sales user has 'executive' role for guided mode"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["role"] == "executive", f"Sales user should have 'executive' role, got {user['role']}"
        print(f"SUCCESS: Sales user has executive role - triggers guided workflow mode")
    
    def test_admin_role_is_admin(self, admin_token):
        """Verify admin user has 'admin' role for full access"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["role"] == "admin", f"Admin user should have 'admin' role, got {user['role']}"
        print(f"SUCCESS: Admin user has admin role - full sales menu access")
    
    def test_sales_executive_can_access_leads(self, sales_token):
        """Verify sales executive can access leads endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        assert response.status_code == 200, f"Sales executive should access /api/leads, got {response.status_code}"
        print("SUCCESS: Sales executive can access leads")
    
    def test_admin_can_access_leads(self, admin_token):
        """Verify admin can access leads endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should access /api/leads, got {response.status_code}"
        print("SUCCESS: Admin can access leads")
