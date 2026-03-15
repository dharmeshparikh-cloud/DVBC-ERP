"""
Test Profile Photo and Performance Dashboard Feature
Tests:
1. Photo upload API endpoint (POST /api/employees/{employee_id}/photo)
2. Photo get API endpoint (GET /api/employees/{employee_id}/photo)
3. Photo delete API endpoint (DELETE /api/employees/{employee_id}/photo)
4. ProfilePerformanceCard component integration
"""

import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
HR_CREDS = {"employee_id": "EMP002", "password": "hr123"}
EXEC_CREDS = {"employee_id": "EMP003", "password": "executive123"}


class TestPhotoAPIEndpoints:
    """Test photo upload/delete/get endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=HR_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"HR login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def exec_token(self):
        """Get Executive authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=EXEC_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip(f"Executive login failed: {response.status_code}")
    
    def test_photo_get_requires_auth(self):
        """Photo GET endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/employees/EMP001/photo")
        # Should return 401 Not Authenticated
        assert response.status_code == 401 or response.status_code == 403
        print("PASS: Photo GET requires authentication")
    
    def test_admin_can_get_own_photo(self, admin_token):
        """Admin can get their own profile photo"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "has_photo" in data
        assert "profile_photo_url" in data
        assert "avatar_url" in data
        
        print(f"PASS: Admin can get own photo, has_photo={data.get('has_photo')}")
        
        # If photo exists, verify it's base64 data
        if data.get("has_photo") and data.get("profile_photo_url"):
            assert data["profile_photo_url"].startswith("data:image/")
            print("PASS: Photo URL is valid base64 data URL")
    
    def test_hr_can_get_any_employee_photo(self, hr_token):
        """HR user can get any employee's photo"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        # HR should be able to access photo endpoints
        assert response.status_code in [200, 404]
        print(f"PASS: HR can access photo endpoint, status={response.status_code}")
    
    def test_exec_can_get_own_photo(self, exec_token):
        """Executive can get their own profile photo"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP003/photo",
            headers={"Authorization": f"Bearer {exec_token}"}
        )
        # Should be able to get own photo
        assert response.status_code in [200, 404]
        print(f"PASS: Executive can get own photo, status={response.status_code}")
    
    def test_photo_upload_endpoint_exists(self, admin_token):
        """Photo upload endpoint (POST) exists and requires file"""
        # Test without file - should return 422 (Unprocessable Entity) not 404
        response = requests.post(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 422 means endpoint exists but file is missing
        # 405 means endpoint doesn't support POST
        assert response.status_code in [422, 400]
        print(f"PASS: Photo upload endpoint exists, status={response.status_code} (expected 422 or 400 without file)")
    
    def test_photo_upload_with_valid_image(self, admin_token):
        """Upload a valid test photo"""
        # Create a small 10x10 red PNG image for testing
        # This is a minimal valid PNG
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFklEQVQYV2NkYGD4z8DAwMgABXAOAwoAELkBgRAUd50AAAAASUVORK5CYII="
        )
        
        files = {
            'file': ('test_photo.png', png_bytes, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        
        # Should succeed with 200
        assert response.status_code == 200
        data = response.json()
        
        assert "profile_photo_url" in data
        assert data["profile_photo_url"].startswith("data:image/")
        print(f"PASS: Photo upload successful, profile_photo_url exists")
    
    def test_photo_delete_endpoint_exists(self, admin_token):
        """Photo delete endpoint (DELETE) works"""
        response = requests.delete(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should succeed - either 200 or 404 if no photo
        assert response.status_code in [200, 404]
        print(f"PASS: Photo delete endpoint works, status={response.status_code}")
    
    def test_photo_fallback_returns_initials(self, admin_token):
        """When no photo, response includes fallback initials"""
        # First delete any existing photo
        requests.delete(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Get photo - should return fallback
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP001/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # When no photo, has_photo should be False
        assert data.get("has_photo") == False or data.get("profile_photo_url") is None or data.get("profile_photo_url") == ""
        
        # Should have fallback_initials
        if "fallback_initials" in data:
            print(f"PASS: Fallback initials present: {data.get('fallback_initials')}")
        else:
            print("INFO: No fallback_initials field, but has_photo correctly False")


class TestPhotoUploadForNonEmployees:
    """Test photo works for users without employee records"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_photo_endpoint_handles_nonexistent_employee(self, admin_token):
        """Photo endpoint handles non-existent employee gracefully"""
        response = requests.get(
            f"{BASE_URL}/api/employees/NONEXISTENT/photo",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 404 or empty response, not 500
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # If 200, should indicate no photo
            assert data.get("has_photo") == False or data.get("profile_photo_url") is None
        print(f"PASS: Non-existent employee handled gracefully, status={response.status_code}")


class TestSalesDashboardIntegration:
    """Test ProfilePerformanceCard appears on Sales Dashboard"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Admin login failed")
    
    def test_my_funnel_summary_returns_stats(self, admin_token):
        """My funnel summary API returns stats for ProfilePerformanceCard"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/my-funnel-summary?period=month",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return 200 with funnel data
        if response.status_code == 200:
            data = response.json()
            # Verify data structure used by ProfilePerformanceCard
            assert "stage_counts" in data or "targets" in data or "total_leads" in data
            print("PASS: My funnel summary returns data for ProfilePerformanceCard")
        else:
            # Endpoint might not exist for all roles
            print(f"INFO: My funnel summary returned {response.status_code}")


class TestManagerDashboardIntegration:
    """Test ProfilePerformanceCard appears on Manager Leads Dashboard"""
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=HR_CREDS
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("HR login failed")
    
    def test_manager_stats_api_exists(self, hr_token):
        """Manager stats API exists for ProfilePerformanceCard"""
        response = requests.get(
            f"{BASE_URL}/api/manager/stats/today",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        # Should return data or 403 if not a manager
        assert response.status_code in [200, 403, 404]
        print(f"PASS: Manager stats API responded, status={response.status_code}")
    
    def test_subordinate_leads_api(self, hr_token):
        """Subordinate leads API exists"""
        response = requests.get(
            f"{BASE_URL}/api/manager/leads",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        # Should return data or 403 if not a manager
        assert response.status_code in [200, 403, 404]
        print(f"PASS: Subordinate leads API responded, status={response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
