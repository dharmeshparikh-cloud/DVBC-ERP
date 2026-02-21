"""
Test Onboarding Tour Feature
Tests for: 
- GET /api/my/onboarding-status - Check onboarding completion status
- POST /api/my/complete-onboarding - Mark tour as completed  
- POST /api/my/reset-onboarding - Reset tour for replay
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
EMPLOYEE_EMAIL = "rahul.kumar@dvbc.com"
EMPLOYEE_PASSWORD = "Welcome@EMP001"


@pytest.fixture
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture
def employee_token():
    """Get employee auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYEE_EMAIL,
        "password": EMPLOYEE_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Employee login failed: {response.status_code} - {response.text}")


class TestOnboardingStatus:
    """Test onboarding status endpoint"""
    
    def test_get_onboarding_status_admin(self, admin_token):
        """Test getting onboarding status for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_completed_onboarding" in data
        assert isinstance(data["has_completed_onboarding"], bool)
        print(f"Admin onboarding status: {data['has_completed_onboarding']}")
    
    def test_get_onboarding_status_employee(self, employee_token):
        """Test getting onboarding status for employee user"""
        response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_completed_onboarding" in data
        assert isinstance(data["has_completed_onboarding"], bool)
        print(f"Employee onboarding status: {data['has_completed_onboarding']}")
    
    def test_get_onboarding_status_unauthorized(self):
        """Test unauthorized access returns 401"""
        response = requests.get(f"{BASE_URL}/api/my/onboarding-status")
        assert response.status_code == 401


class TestCompleteOnboarding:
    """Test complete onboarding endpoint"""
    
    def test_complete_onboarding_admin(self, admin_token):
        """Test marking onboarding as complete for admin"""
        response = requests.post(
            f"{BASE_URL}/api/my/complete-onboarding",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed_onboarding"] == True
        assert "message" in data
        print(f"Complete onboarding response: {data}")
        
        # Verify status changed
        status_response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_response.status_code == 200
        assert status_response.json()["has_completed_onboarding"] == True
    
    def test_complete_onboarding_employee(self, employee_token):
        """Test marking onboarding as complete for employee"""
        response = requests.post(
            f"{BASE_URL}/api/my/complete-onboarding",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed_onboarding"] == True
        print(f"Employee complete onboarding response: {data}")


class TestResetOnboarding:
    """Test reset onboarding endpoint"""
    
    def test_reset_onboarding_admin(self, admin_token):
        """Test resetting onboarding for admin"""
        response = requests.post(
            f"{BASE_URL}/api/my/reset-onboarding",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed_onboarding"] == False
        assert "message" in data
        print(f"Reset onboarding response: {data}")
        
        # Verify status changed to false
        status_response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_response.status_code == 200
        assert status_response.json()["has_completed_onboarding"] == False
    
    def test_reset_onboarding_employee(self, employee_token):
        """Test resetting onboarding for employee"""
        response = requests.post(
            f"{BASE_URL}/api/my/reset-onboarding",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed_onboarding"] == False
        print(f"Employee reset onboarding response: {data}")


class TestOnboardingWorkflow:
    """Test complete onboarding workflow: reset -> check -> complete -> check"""
    
    def test_full_onboarding_workflow(self, employee_token):
        """Test the full onboarding flow: reset -> status (false) -> complete -> status (true)"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Step 1: Reset onboarding
        reset_response = requests.post(
            f"{BASE_URL}/api/my/reset-onboarding",
            headers=headers
        )
        assert reset_response.status_code == 200
        print("Step 1: Reset onboarding - PASSED")
        
        # Step 2: Check status is false
        status1_response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers=headers
        )
        assert status1_response.status_code == 200
        assert status1_response.json()["has_completed_onboarding"] == False
        print("Step 2: Status is False after reset - PASSED")
        
        # Step 3: Complete onboarding
        complete_response = requests.post(
            f"{BASE_URL}/api/my/complete-onboarding",
            headers=headers
        )
        assert complete_response.status_code == 200
        print("Step 3: Complete onboarding - PASSED")
        
        # Step 4: Check status is true
        status2_response = requests.get(
            f"{BASE_URL}/api/my/onboarding-status",
            headers=headers
        )
        assert status2_response.status_code == 200
        assert status2_response.json()["has_completed_onboarding"] == True
        print("Step 4: Status is True after completion - PASSED")
        
        print("Full onboarding workflow test PASSED")
